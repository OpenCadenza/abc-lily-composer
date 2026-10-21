"""Detect dependencies; never install software or edit configuration."""
import argparse
from importlib import metadata
from pathlib import Path
import sys

from _common import emit, executable, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=['abc', 'lilypond', 'all'], default='all')
    parser.add_argument('--analysis', action='store_true', help='Require music21 as well as the selected compilers')
    for name in ('lilypond', 'abc2midi', 'abc2abc'):
        parser.add_argument('--' + name, help='Executable path; otherwise use NAME_PATH or PATH')
    args = parser.parse_args()
    python_ok = sys.version_info >= (3, 11)
    report = {'python': {'path': sys.executable, 'version': sys.version.split()[0], 'available': python_ok},
              'tools': {}, 'setup': 'references/setup.md'}
    try:
        report['music21'] = {'available': True, 'version': metadata.version('music21')}
        import music21  # Verify import, not only distribution metadata.
    except (ImportError, metadata.PackageNotFoundError) as error:
        report['music21'] = {'available': False, 'error': str(error)}
    required = ['abc2midi', 'abc2abc'] if args.format == 'abc' else ['lilypond']
    if args.format == 'all':
        required = ['lilypond', 'abc2midi', 'abc2abc']
    # Version probes need no scratch files; using cwd avoids restricted system
    # temp cleanup on managed Windows hosts.
    for name in ('lilypond', 'abc2midi', 'abc2abc'):
        try:
            report['tools'][name] = {'available': True, **version(executable(name, getattr(args, name)), name, Path.cwd())}
        except (OSError, RuntimeError) as error:
            report['tools'][name] = {'available': False, 'error': str(error)}
    ready = python_ok and all(report['tools'][n]['available'] for n in required)
    ready = ready and (not args.analysis or report['music21']['available'])
    report.update(status='ready' if ready else 'missing_dependencies', required=required)
    emit(report)
    return 0 if ready else 1


if __name__ == '__main__':
    sys.exit(main())
