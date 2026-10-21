"""Compile native ABC/LilyPond into a fresh output directory and a hash-bound report."""
import argparse
from pathlib import Path
import re
import sys
import tempfile

from _common import abc_units, digest, emit, executable, positive_seconds, run, save, version


def compile_score(args):
    source_path = Path(args.source).resolve()
    raw = source_path.read_bytes()
    source = raw.decode('utf-8-sig')
    if not source.strip():
        raise ValueError('empty source')
    fmt = args.format or {'.abc': 'abc', '.ly': 'lilypond'}.get(source_path.suffix.lower())
    if not fmt:
        raise ValueError('specify --format abc or lilypond')
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='compile-', dir=root))
    report_path = directory / 'compile-report.json'
    report = {'status': 'failed', 'format': fmt, 'source_path': str(source_path),
              'source_hash': digest(raw), 'report_path': str(report_path), 'engines': [],
              'commands': [], 'diagnostics': [], 'artifacts': [], 'units': []}
    try:
        timeout = positive_seconds(args.timeout)
        name = 'abc2midi' if fmt == 'abc' else 'lilypond'
        binary = executable(name, getattr(args, name))
        report['engines'].append(version(binary, name, directory, timeout))
        checker = None
        if fmt == 'abc':
            # A sibling is useful for portable Windows abcMIDI distributions.
            sibling = Path(binary).with_name('abc2abc.exe' if sys.platform == 'win32' else 'abc2abc')
            checker = executable('abc2abc', args.abc2abc or (str(sibling) if sibling.is_file() else None))
            report['engines'].append(version(checker, 'abc2abc', directory, timeout))
        units = abc_units(source) if fmt == 'abc' else [source]
        failed = False
        for index, unit in enumerate(units, 1):
            filename = f'movement-{index}.abc' if fmt == 'abc' else 'score.ly'
            (directory / filename).write_text(unit, encoding='utf-8', newline='')
            report['units'].append({'movement': index, 'source': filename, 'source_hash': digest(unit.encode('utf-8'))})
            commands = [[checker, filename], [binary, filename, '-Werror', '-o', f'movement-{index}.mid']] if checker else [
                [binary, '-dno-point-and-click', '-o', 'score', filename]]
            for command in commands:
                result = run(command, directory, timeout)
                report['commands'].append({'movement': index, **result})
                failed |= result['returncode'] != 0 or result['timed_out']
                if result['timed_out']:
                    report['diagnostics'].append({'severity': 'error', 'movement': index, 'message': 'compiler timed out'})
                for line in (result['stdout'] + result['stderr']).splitlines():
                    # abc2abc echoes the source: a title containing "error" is not a diagnostic.
                    if re.search(r'^(?:%?\s*(?:fatal error|error|warning)\b|.*?:\d+(?::\d+)?:\s*(?:fatal error|error|warning)\b|(?:错误|警告)\s*[:：])', line, re.I):
                        severity = 'error' if re.search(r'error|错误|barcheck|bar check|not enough|too many beats|bar .*has', line, re.I) else 'warning'
                        report['diagnostics'].append({'severity': severity, 'movement': index, 'message': line})
                        failed |= severity == 'error'
            if fmt == 'abc' and not (directory / f'movement-{index}.mid').is_file():
                failed = True
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() in {'.mid', '.midi', '.pdf', '.svg', '.wav'} and path.is_file():
                data = path.read_bytes()
                report['artifacts'].append({'name': path.name, 'hash': digest(data), 'size': len(data)})
        required = args.require or (['midi'] if fmt == 'abc' else [])
        suffixes = {'midi': {'.mid', '.midi'}, 'pdf': {'.pdf'}}
        report['missing_artifacts'] = [kind for kind in required if not any(
            Path(a['name']).suffix in suffixes[kind] for a in report['artifacts'])]
        if not report['artifacts'] or any(a['size'] == 0 for a in report['artifacts']) or report['missing_artifacts']:
            failed = True
        if failed and not any(d['severity'] == 'error' for d in report['diagnostics']):
            report['diagnostics'].append({'severity': 'error', 'message': 'compiler failed or expected output missing; see commands'})
        report['status'] = 'failed' if failed else 'passed'
    except (OSError, ValueError, RuntimeError) as error:
        report['diagnostics'].append({'severity': 'error', 'message': str(error)})
    save(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output-dir', required=True, help='Parent for a fresh compile-* directory')
    parser.add_argument('--format', choices=['abc', 'lilypond'])
    parser.add_argument('--require', action='append', choices=['pdf', 'midi'], help='Required artifact type; repeat as needed')
    parser.add_argument('--timeout', type=float, default=90, help='Seconds per compiler process, including version probes')
    for name in ('lilypond', 'abc2midi', 'abc2abc'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    try:
        report = compile_score(args)
    except (OSError, ValueError) as error:
        report = {'status': 'failed', 'error': str(error)}
    emit(report)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
