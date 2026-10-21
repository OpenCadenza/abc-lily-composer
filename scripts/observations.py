"""Read-only observations from compiled MIDI, independent of author comments.

Not a composition engine or complete counterpoint validator. Parallel candidates
are reported only across monophonic tracks; crossings, doubling and style need
manual score review. No claim that absence of candidates proves correctness.
"""
from bisect import bisect_right
import itertools
from pathlib import Path
import struct


def varlen(data,pos):
    value=0
    for _ in range(4):
        byte=data[pos];pos+=1;value=(value<<7)|(byte&127)
        if not byte&128:return value,pos
    raise ValueError("invalid MIDI variable-length quantity")


def read_midi(path):
    data=Path(path).read_bytes()
    if data[:4]!=b"MThd":raise ValueError("not MIDI")
    size=struct.unpack(">I",data[4:8])[0]
    fmt,count,division=struct.unpack(">HHH",data[8:14])
    if division&0x8000:raise ValueError("SMPTE timing unsupported")
    pos=8+size;tracks=[]
    for index in range(count):
        if data[pos:pos+4]!=b"MTrk":raise ValueError("missing track")
        length=struct.unpack(">I",data[pos+4:pos+8])[0]
        track=data[pos+8:pos+8+length];pos+=8+length
        i=0;tick=0;running=None;notes=[];active={};name="";meters=[]
        while i<len(track):
            delta,i=varlen(track,i);tick+=delta
            status=track[i]
            if status&128:i+=1
            elif running is not None:status=running
            else:raise ValueError("running status without status byte")
            if status==0xff:
                kind=track[i];i+=1;n,i=varlen(track,i);value=track[i:i+n];i+=n
                if kind==3:name=value.decode("utf-8",errors="replace")
                if kind==0x58:meters.append({"tick":tick,"numerator":value[0],"denominator":2**value[1]})
                continue
            if status in (0xf0,0xf7):
                n,i=varlen(track,i);i+=n;running=None;continue
            running=status;kind=status&0xf0;channel=status&15
            a=track[i];i+=1
            b=track[i] if kind not in (0xc0,0xd0) else None
            if b is not None:i+=1
            key=(channel,a)
            if kind==0x90 and b:
                active.setdefault(key,[]).append((tick,b))
            elif kind==0x80 or (kind==0x90 and b==0):
                if active.get(key):
                    start,velocity=active[key].pop(0)
                    notes.append({"pitch":a,"start":start,"end":tick,"velocity":velocity,"channel":channel})
        notes.sort(key=lambda n:(n["start"],n["pitch"]))
        tracks.append({"index":index,"name":name,"end_tick":tick,"meters":meters,"notes":notes,
            "unclosed_notes":sum(len(a) for a in active.values())})
    return {"format":fmt,"ticks_per_quarter":division,"tracks":tracks}


def inspect(path):
    midi=read_midi(path);musical=[t for t in midi["tracks"] if t["notes"]]
    summary={"file":str(path),"ticks_per_quarter":midi["ticks_per_quarter"],"tracks":[],"parallel_candidates":[]}
    mono=[]
    for t in musical:
        notes=t["notes"];maximum_end=-1;poly=False
        for n in notes:
            if n["start"]<maximum_end:poly=True
            maximum_end=max(maximum_end,n["end"])
        summary["tracks"].append({"index":t["index"],"name":t["name"],"notes":len(notes),
            "min_pitch":min(n["pitch"] for n in notes),"max_pitch":max(n["pitch"] for n in notes),
            "first_tick":notes[0]["start"],"last_note_end":maximum_end,"end_tick":t["end_tick"],
            "first_quarter":notes[0]["start"]/midi["ticks_per_quarter"],
            "last_note_quarter":maximum_end/midi["ticks_per_quarter"],
            "monophonic":not poly,"unclosed_notes":t["unclosed_notes"]})
        if not poly:mono.append(t)
    for a,b in itertools.combinations(mono,2):
        starts_a=[n["start"] for n in a["notes"]];starts_b=[n["start"] for n in b["notes"]]
        previous=None
        for tick in sorted(set(starts_a+starts_b)):
            ia=bisect_right(starts_a,tick)-1;ib=bisect_right(starts_b,tick)-1
            if ia<0 or ib<0:previous=None;continue
            na,nb=a["notes"][ia],b["notes"][ib]
            if na["end"]<=tick or nb["end"]<=tick:previous=None;continue
            current=(tick,na["pitch"],nb["pitch"])
            if previous:
                t0,pa,pb=previous;da=current[1]-pa;db=current[2]-pb
                old_interval=abs(pa-pb)%12;new_interval=abs(current[1]-current[2])%12
                if da*db>0 and old_interval==new_interval and new_interval in (0,7):
                    summary["parallel_candidates"].append({"tracks":[a["index"],b["index"]],
                        "ticks":[t0,tick],"pitches":[[pa,pb],[current[1],current[2]]],
                        "kind":"fifth" if new_interval==7 else "unison/octave"})
            previous=current
    return summary


