#!/usr/bin/env python3
"""SIG-002/U-032: deterministic blocked-wait injection in a test-only runtime."""
import os
from pathlib import Path
import signal
import sys
import tempfile
from execute import bounded_run

binary = str(Path(sys.argv[1]).resolve())
for selected in ('USR1', 'TERM', 'both'):
    for operand in ('"$p"', ''):
        with tempfile.TemporaryDirectory(prefix='cshell-wait-handshake-') as directory:
            os.mkfifo(Path(directory) / 'release')
            signals = sorted((signal.SIGUSR1, signal.SIGUSR2)) if selected == 'both' else [getattr(signal, 'SIG' + selected)]
            traps = '; '.join(f"trap 'printf \"trap:{n}:%s\\n\" \"$?\"' {n}" for n in signals)
            script = (f'{traps}; {{ read token <release; exit 23; }} & p=$!; '
                      f'wait {operand}; printf "wait:%s\\n" "$?"; '
                      'echo go >release; wait "$p"; printf "second:%s\\n" "$?"; '
                      'wait "$p" 2>/dev/null; printf "third:%s\\n" "$?"\n')
            env = dict(PATH=os.defpath, HOME=directory, TMPDIR=directory, LC_ALL='C', LANG='C', CSH_WAIT_SIGNALS=selected)
            result = bounded_run([binary, '-c', script], cwd=Path(directory), env=env, timeout=5)
            status = 128 + signals[0]
            output = ''.join(f'trap:{n}:{status}\n' for n in signals) + f'wait:{status}\nsecond:23\nthird:127\n'
            assert (result.returncode, result.stdout, result.stderr) == (0, output.encode(), b'wait-armed\n'), (selected, operand, result)
            print(f'PASS: blocked wait {selected} {operand or "all"}; second wait 23; third wait 127')
