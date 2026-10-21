"""Experimental read-only score facts. Never a composition or pass/fail engine.

Native ABC import is checked against independently compiled MIDI. MIDI pitch
spelling is deliberately withheld. No caller-supplied Python/Scheme is evaluated
by this module; compilation is the caller's trusted-local responsibility.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import itertools
import re
import warnings

from observations import read_midi


def digest(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def midi_events(path):
    midi = read_midi(path)
    ppq = midi["ticks_per_quarter"]
    events = []
    for track in midi["tracks"]:
        if track["unclosed_notes"]:
            raise ValueError("compiled MIDI has unclosed notes")
        for n in track["notes"]:
            events.append({"part":str(track["index"]), "pitch":n["pitch"],
                "start":n["start"]/ppq, "duration":(n["end"]-n["start"])/ppq,
                "spelling":None})
    return sorted(events, key=lambda n:(n["start"], n["part"], n["pitch"]))


def stream_events(score):
    """Sounding events: tie continuations are not new attacks."""
    result = []
    parts = list(score.parts) or [score]
    for i, part in enumerate(parts):
        active = {}
        for item in part.recurse().notes:
            start = float(item.getOffsetInHierarchy(part))
            notes = item.notes if item.isChord else [item]
            for n in notes:
                tie = n.tie.type if n.tie else None
                pitch = int(n.pitch.midi)
                if tie in {"continue", "stop"} and pitch in active:
                    old = active[pitch]
                    if abs(old["start"]+old["duration"]-start)<1e-5:
                        old["duration"] += float(item.quarterLength)
                        if tie == "stop": active.pop(pitch)
                        continue
                event = {"part":str(i), "pitch":pitch, "start":start,
                    "duration":float(item.quarterLength), "spelling":n.pitch.nameWithOctave}
                result.append(event)
                if tie == "start": active[pitch] = event
    return sorted(result,key=lambda n:(n["start"],n["part"],n["pitch"]))


def agreement(a, b):
    """Ignore track layout, but retain duplicate attacks with bounded tolerance.

    MIDI articulation can shorten releases; report duration errors separately.
    Neither attack agreement nor successful compilation proves source fidelity.
    """
    remaining=list(b);matched=[];unmatched=0
    for n in sorted(a,key=lambda n:n['start']):
        options=[(abs(n['start']-other['start']),i) for i,other in enumerate(remaining)
            if n['pitch']==other['pitch'] and abs(n['start']-other['start'])<=.04]
        if not options:unmatched+=1;continue
        _,i=min(options);matched.append((n,remaining.pop(i)))
    return {"attacks_match":not unmatched and not remaining, "native_notes":len(a), "compiled_notes":len(b),
        "native_only":unmatched,"compiled_only":len(remaining),"onset_tolerance_quarters":.04,
        "duration_tolerance_quarters":.08,"durations_equal":not unmatched and not remaining and
        all(abs(x['duration']-y['duration'])<=.08 for x,y in matched)}


def group_abc_voices(source):
    """Layout-only adapter for music21's unsupported interleaved [V:] layout.

    No pitch/duration conversion. Unknown non-voice body lines reject this path.
    """
    headers=[];definitions={};voices={};body=False
    for line in source.splitlines():
        match=re.match(r'\[V:([^]]+)\](.*)',line)
        if match:
            body=True;voices.setdefault(match[1],[]).append(match[2])
        elif line.startswith('V:'):
            key=line[2:].strip().split()[0];definitions[key]=line
        elif not body:headers.append(line)
        elif line.strip():raise ValueError('unsupported body outside voice line')
    if not voices:raise ValueError('no inline voices')
    return '\n'.join(headers+[definitions.get(v,'V:'+v)+'\n'+'\n'.join(lines) for v,lines in voices.items()])


class ScoreFacts:
    def __init__(self, fmt, source, source_hash, midi_path, meter, pickup=0):
        if fmt not in {"abc", "lilypond"}: raise ValueError("unsupported format")
        if digest(source) != source_hash: raise ValueError("source hash mismatch")
        from music21 import converter, __version__
        self.events = midi_events(midi_path)
        if not self.events: raise ValueError("no sounding MIDI events")
        self.meter = tuple(meter)
        if len(self.meter)!=2 or min(self.meter)<=0: raise ValueError("invalid meter")
        self.bar_length = self.meter[0]*4/self.meter[1]
        self.pickup = float(Fraction(str(pickup)))
        if not 0<=self.pickup<self.bar_length: raise ValueError("invalid pickup")
        self.meta = {"source_hash":source_hash,"format":fmt,"music21":__version__,
            "method":"fresh compiler MIDI events; music21 interval/chord/key candidates",
            "native_abc":None,"source_line_mapping":"unavailable",
            "limitations":["MIDI tracks are not guaranteed independent notated voices",
                "MIDI releases reflect performance articulation, not always notated duration",
                "chord snapshots are not harmonic reductions; non-chord tones remain",
                "no complete theory correctness verdict; cadence/form/motif require source review"]}
        if fmt == "abc":
            try:
                with warnings.catch_warnings(record=True) as caught:
                    native = converter.parseData(source,format="abc")
                parsed = stream_events(native)
                check = agreement(parsed,self.events)
                check["warnings"] = [str(w.message)[:300] for w in caught]
                if not check['attacks_match']:
                    original_check=check
                    with warnings.catch_warnings(record=True) as caught:
                        native=converter.parseData(group_abc_voices(source),format='abc')
                    parsed=stream_events(native);check=agreement(parsed,self.events)
                    check.update(raw_interleaved_import=original_check,adapter='group voice lines; preserve musical tokens',
                        warnings=[str(w.message)[:300] for w in caught])
                # Not just matching count: exact attack multiset, durations, no warnings.
                if check["attacks_match"] and check["durations_equal"] and not caught:
                    # All downstream calculations now use source-derived parts/spelling.
                    self.events = parsed
                    self.meta["method"] = "native music21 ABC import cross-checked with fresh compiler MIDI"
                self.meta["native_abc"] = check
            except Exception as exc:
                self.meta["native_abc"] = {"error":type(exc).__name__,"usable":False}
        self.spelled = all(n["spelling"] for n in self.events)
        self.meta["pitch_spelling"] = "source-derived" if self.spelled else "unknown; do not infer enharmonic function"
        self.parts = sorted({n["part"] for n in self.events})

    def position(self, start):
        if start < self.pickup-1e-6: return {"measure":0,"quarter_in_measure":round(start,5)}
        offset = start-self.pickup
        bar = int((offset+1e-6)//self.bar_length)
        return {"measure":bar+1,"quarter_in_measure":round(offset-bar*self.bar_length,5)}

    def select(self, first, last):
        if type(first) is not int or type(last) is not int or not 0<=first<=last or last-first>64:
            raise ValueError("measure range must be nonnegative integers, at most 65 measures per page")
        lo = 0 if first==0 else self.pickup+(first-1)*self.bar_length
        hi = self.pickup+last*self.bar_length
        # Retain sustained notes crossing a requested boundary.
        return [n for n in self.events if n["start"]<hi-1e-6 and n["start"]+n["duration"]>lo+1e-6]

    def query(self, kind="overview", first=0, last=8):
        if kind not in {"overview","notes","harmony","voice_leading"}: raise ValueError("unknown analysis kind")
        events = self.select(first,last)
        out = {**self.meta,"coverage":{"first":first,"last":last,"events":len(events)},
            "kind":kind,"meter":self.meter,"pickup_quarters":self.pickup}
        if kind in {"overview","notes"}:
            out["parts"] = [{"id":p,"notes":len(ns),"range_midi":[min(n["pitch"] for n in ns),max(n["pitch"] for n in ns)],
                "monophonic":self.monophonic(ns)} for p in self.parts if (ns:=[n for n in events if n["part"]==p])]
            if kind == "notes":
                out["notes"] = [{**n,**self.position(n["start"])} for n in events[:160]]
                out["omitted_events"] = max(0,len(events)-160)
        if kind in {"overview","harmony"}:
            from music21 import chord, pitch, stream, note
            s = stream.Stream()
            for n in events:
                obj = note.Note(n["spelling"] if self.spelled else n["pitch"],quarterLength=n["duration"])
                s.insert(n["start"],obj)
            try:
                k = s.analyze("key")
                out["statistical_key_candidate"] = {"name":str(k),"correlation":round(k.correlationCoefficient,3),
                    "warning":"fragment-wide estimate, not verified local key"}
            except Exception:
                out["statistical_key_candidate"] = None
            if kind == "harmony":
                snapshots=[]
                for m in range(max(1,first),last+1):
                    for q in (0,self.bar_length/2):
                        # abc2midi staggers chord attacks by up to ~.023 quarters.
                        # Snapshot slightly after the nominal boundary; disclose it.
                        t=self.pickup+(m-1)*self.bar_length+q+.03125
                        sounding=[n for n in events if n["start"]<=t+1e-6 and n["start"]+n["duration"]>t+1e-6]
                        if not sounding: continue
                        c=chord.Chord([n["spelling"] if self.spelled else pitch.Pitch(n["pitch"]) for n in sounding])
                        item={"measure":m,"quarter_in_measure":q,"pitches_midi":sorted(n["pitch"] for n in sounding),
                            "pitch_classes":sorted({n["pitch"]%12 for n in sounding})}
                        if self.spelled: item.update(spellings=[n["spelling"] for n in sounding],chord_name_candidate=c.pitchedCommonName)
                        else: item["chord_name_candidate"]=None
                        snapshots.append(item)
                out["snapshots"] = snapshots
                out['snapshot_offset_quarters']=.03125
        if kind == "voice_leading":
            out.update(self.voice_leading(events))
        return out

    @staticmethod
    def monophonic(events):
        end=-1
        for n in sorted(events,key=lambda n:n["start"]):
            if n["start"]<end-1e-6:return False
            end=n["start"]+n["duration"]
        return True

    def voice_leading(self,events):
        from music21 import interval, note, voiceLeading
        mono={p:ns for p in self.parts if (ns:=[n for n in events if n["part"]==p]) and self.monophonic(ns)}
        candidates=[]
        for a,b in itertools.combinations(mono,2):
            previous=None
            # Include releases to break chains over rests.
            times=sorted({x for n in mono[a]+mono[b] for x in (n["start"],n["start"]+n["duration"])})
            for t in times:
                sounding=[[n for n in mono[p] if n["start"]<=t+1e-6<n["start"]+n["duration"]] for p in (a,b)]
                if not all(sounding): previous=None;continue
                pair=[ns[0] for ns in sounding]
                if previous and any(n["start"]>=t-1e-6 for n in pair):
                    old=previous[1];d1=pair[0]["pitch"]-old[0]["pitch"];d2=pair[1]["pitch"]-old[1]["pitch"]
                    old_i=abs(old[0]["pitch"]-old[1]["pitch"])%12
                    new_i=abs(pair[0]["pitch"]-pair[1]["pitch"])%12
                    if d1*d2>0 and old_i==new_i and new_i in (0,7):
                        item={"parts":[a,b],"from":self.position(previous[0]),"to":self.position(t),
                            "pitches":[[n["pitch"] for n in old],[n["pitch"] for n in pair]],
                            "kind":"7-semitone" if new_i==7 else "0-mod-12-semitone",
                            "verdict":"candidate only; source voices and style require verification"}
                        if self.spelled:
                            vl=voiceLeading.VoiceLeadingQuartet(*(note.Note(n["spelling"]) for n in (old[0],pair[0],old[1],pair[1])))
                            item["music21_parallel_fifth"]=vl.parallelFifth()
                            item["music21_parallel_octave"]=vl.parallelOctave()
                        candidates.append(item)
                previous=(t,pair)
        return {"eligible_monophonic_parts":list(mono),"excluded_polyphonic_parts":[p for p in self.parts if p not in mono],
            "parallel_candidates":candidates[:30],"candidate_count":len(candidates)}
