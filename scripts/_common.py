"""Small shared I/O helpers, not an agent runtime."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def emit(data):
    # Escaped Unicode also works on legacy Windows redirected consoles.
    print(json.dumps(data, ensure_ascii=True, allow_nan=False))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def positive_seconds(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('timeout must be finite and positive')
    return value


def executable(name, override=None):
    candidate = override or os.environ.get(name.upper() + '_PATH') or name
    found = shutil.which(candidate)
    if not found:
        raise FileNotFoundError(f'{name} not found: {candidate}; see references/setup.md')
    return str(Path(found).resolve())


def run(command, cwd, timeout):
    options = {'start_new_session': True} if os.name != 'nt' else {'creationflags': subprocess.CREATE_NO_WINDOW}
    child = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, **options)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        else:
            os.killpg(child.pid, signal.SIGKILL)
        child.kill()
        stdout, stderr = child.communicate()
    return {'command': command, 'returncode': child.returncode, 'timed_out': timed_out,
            'stdout': stdout.decode('utf-8', errors='replace'), 'stderr': stderr.decode('utf-8', errors='replace')}


def version(binary, name, cwd, timeout=10):
    result = run([binary, '--version' if name == 'lilypond' else '-ver'], cwd, timeout)
    lines = (result['stdout'] + result['stderr']).strip().splitlines()
    if result['timed_out'] or not lines or result['returncode'] != 0:
        raise RuntimeError(f'{name} version probe failed: {result}')
    return {'name': name, 'path': binary, 'version': lines[0]}


def abc_units(source):
    import re
    starts = list(re.finditer(r'(?m)^X:\s*\d+[^\n]*', source))
    if not starts:
        raise ValueError('ABC requires at least one X: tune')
    preamble = source[:starts[0].start()]
    return [preamble + source[m.start():starts[i+1].start() if i+1 < len(starts) else len(source)]
            for i, m in enumerate(starts)]
