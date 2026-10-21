"""Read-only score facts from a matching compile report; never a music pass/fail verdict."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys

from _common import abc_units, digest, emit
from observations import read_midi
from theory import ScoreFacts


def analyze(args):
    if args.movement < 1:
        raise ValueError('movement must be positive')
    raw = Path(args.source).read_bytes()
    report_path = Path(args.compile_report).resolve()
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['status'] != 'passed' or report['source_hash'] != digest(raw):
        raise ValueError('stale or failed compile report; compile the current source again')
    # Verify all artifacts before inspecting any selected movement.
    artifacts = {}
    for item in report['artifacts']:
        if Path(item['name']).name != item['name'] or '\\' in item['name'] or '/' in item['name']:
            raise ValueError('artifact must be a local filename')
        path = (report_path.parent / item['name']).resolve()
        if path.parent != report_path.parent or digest(path.read_bytes()) != item['hash']:
            raise ValueError('compiled artifact hash mismatch')
        artifacts[item['name']] = path
    source = raw.decode('utf-8-sig')
    fmt = report['format']
    if fmt == 'abc':
        units = abc_units(source)
        if not 1 <= args.movement <= len(units):
            raise ValueError('movement outside ABC tune range')
        source = units[args.movement - 1]
        name = f'movement-{args.movement}.mid'
    else:
        if args.movement != 1 and not args.artifact:
            raise ValueError('LilyPond movement selection requires explicit --artifact; MIDI file identity is not inferred')
        midis = [n for n in artifacts if Path(n).suffix in {'.mid', '.midi'}]
        if not args.artifact and len(midis) != 1:
            raise ValueError('select --artifact from compile report MIDI artifacts')
        name = args.artifact or midis[0]
    if name not in artifacts or Path(name).suffix not in {'.mid', '.midi'}:
        raise ValueError('selected MIDI artifact missing')
    meter = tuple(int(n) for n in args.meter.split('/'))
    if len(meter) != 2 or min(meter) <= 0:
        raise ValueError('meter must be positive N/D')
    midi = read_midi(artifacts[name])
    meters = [m for t in midi['tracks'] for m in t['meters']]
    if any((m['numerator'], m['denominator']) != meter for m in meters):
        raise ValueError('variable or mismatched MIDI meter; fixed-meter measure positions unavailable')
    if not meters:
        raise ValueError('MIDI has no meter metadata; measure positions unavailable')
    pickup = float(Fraction(args.pickup))
    facts = ScoreFacts(fmt, source, digest(source.encode('utf-8')), artifacts[name], meter, pickup)
    result = facts.query(args.kind, args.first, args.last)
    if args.kind == 'notes':
        events = facts.select(args.first, args.last)
        if args.offset < 0 or not 1 <= args.limit <= 1000:
            raise ValueError('offset must be nonnegative; limit must be 1..1000')
        page = events[args.offset:args.offset+args.limit]
        result['notes'] = [{**n, **facts.position(n['start'])} for n in page]
        result['omitted_events'] = max(0, len(events)-args.offset-len(page))
        result['next_offset'] = args.offset+len(page) if result['omitted_events'] else None
    result.update(status='available', source_hash=report['source_hash'], analysis_source_hash=digest(source.encode('utf-8')),
                  artifact=name, artifact_hash=digest(artifacts[name].read_bytes()), movement=args.movement,
                  duration_quarters=max(n['start']+n['duration'] for n in facts.events))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--compile-report', required=True)
    parser.add_argument('--meter', required=True, help='Fixed meter, e.g. 4/4; mismatches are rejected')
    parser.add_argument('--pickup', default='0', help='Pickup duration in quarter notes, e.g. 1 or 1/2')
    parser.add_argument('--movement', type=int, default=1, help='ABC X: order; LilyPond identity is caller-declared')
    parser.add_argument('--artifact', help='LilyPond MIDI filename from report; required for multiple MIDI files')
    parser.add_argument('--kind', choices=['overview', 'notes', 'harmony', 'voice_leading'], default='overview')
    parser.add_argument('--first', type=int, default=1, help='First measure; pickup is measure 0')
    parser.add_argument('--last', type=int, default=8, help='Last measure, inclusive; max 65 measures per query')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=160)
    args = parser.parse_args()
    try:
        result = analyze(args)
    except Exception as error:
        # Corrupt MIDI, optional library failures and malformed reports remain structured failures.
        result = {'status': 'unavailable', 'error': f'{type(error).__name__}: {error}'}
    emit(result)
    return 0 if result['status'] == 'available' else 1


if __name__ == '__main__':
    sys.exit(main())
