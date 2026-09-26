"""Run the option/PTY assertions with ASan/UBSan, explicitly excluding LSan.

Linux LeakSanitizer startup/exit is disproportionately expensive in the local
VM. Keep the unchanged five-second behavioral deadlines and record the exact
suite environment overrides instead of weakening those limits.
"""
import json
from pathlib import Path
import subprocess
import sys

status = 0
for name in ('options', 'runtime-pty'):
    source = Path('build/tests') / (name + '.json')
    suite = json.loads(source.read_text())
    for case in suite['cases']:
        case.setdefault('env', {}).update(
            ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
            UBSAN_OPTIONS='halt_on_error=1')
    target = source.with_name(name + '-asan-ubsan.json')
    target.write_text(json.dumps(suite, separators=(',', ':')) + '\n')
    result = subprocess.run([sys.executable, 'tests/smoke.py', './cshell',
                             '--suite', str(target)])
    status = status or result.returncode
raise SystemExit(status)
