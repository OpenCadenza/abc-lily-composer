"""Package a standalone Skill without knowledge snapshots or maintenance data."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from urllib.parse import unquote, urlsplit

RUNTIME = ('_common.py', 'check_environment.py', 'compile_score.py', 'analyze_score.py',
           'observations.py', 'theory.py', 'requirements.txt')


def package(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    names = ['SKILL.md', 'README.md', 'LICENSE', 'NOTICE.md', 'knowledge-source.json']
    names += ['scripts/' + name for name in RUNTIME]
    names += [p.relative_to(root).as_posix() for p in sorted((root / 'references').rglob('*.md'))]
    if not (root / 'references/github-knowledge.md').is_file():
        raise ValueError('missing GitHub knowledge instructions')
    for name in names:
        path = root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f'missing file or unsupported symlink: {name}')
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                linked = (path.parent / unquote(parsed.path)).resolve()
                if not linked.is_relative_to(root) or linked.relative_to(root).as_posix() not in names:
                    raise ValueError(f'broken or unpackaged link in {name}: {target}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            info = zipfile.ZipInfo('abc-lily-composer/' + name, (2000, 1, 1, 0, 0, 0))
            archive.writestr(info, (root / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    return {'ok': True, 'output': str(output), 'files': len(names),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.root, args.output), ensure_ascii=True))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
