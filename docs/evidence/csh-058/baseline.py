"""Reproduce four CSH-058 defects with final probes and pre-ticket runtime."""
import json
import os
from pathlib import Path
import shlex
import signal
import sys
import tempfile
sys.path.insert(0, str(Path('tests').resolve()))
from execute import bounded_run
from pty_harness import capture
from smoke import child_limits

binary, helper = map(lambda p: str(Path(p).resolve()), sys.argv[1:3])
h = shlex.quote(helper)
cases = [
    ('fork reset', signal.SIGTERM, 0, False,
     f"trap '' TERM; (trap - TERM; {h} probe {signal.SIGTERM})", (0, 'default:terminated\n', '')),
    ('inherited CHLD substitution', signal.SIGCHLD, 1, False,
     f'v=$({h} probe {signal.SIGCHLD}; :); printf "%s\\n" "$v"', (0, 'ignored:survived\n', '')),
    ('monitored background INT', signal.SIGINT, 0, True,
     f"trap ':' INT; {{ {{ {h} probe {signal.SIGINT}; }} & wait; wait; :; }} 2>errors", (0, 'default:terminated\n', '')),
    ('caught TTOU terminal restoration', signal.SIGTTOU, 0, True,
     f"trap ':' TTOU; {{ ( {h} probe {signal.SIGTTOU} ); }} 2>errors", (0, 'default:stopped\n', '')),
]
for name, n, inherited, terminal, script, expected in cases:
    with tempfile.TemporaryDirectory() as d:
        env = dict(PATH=os.defpath, LC_ALL='C', LANG='C', HOME=d, TMPDIR=d)
        args = ['launch', str(n), str(inherited), binary, '-c' if inherited else '-ic', script]
        if terminal:
            status, output, failures = capture(helper, dict(args=args, steps=[]), Path(d), 5, 65536, env, child_limits)
            assert not failures, failures
            stdout = bytes(output['output']).decode()
            stderr = (Path(d) / 'errors').read_text()
            if name == 'monitored background INT':
                import re
                assert re.fullmatch(r'\[1\] [1-9][0-9]*\n', stderr), stderr
                stderr = ''
        else:
            r = bounded_run([helper, *args], cwd=Path(d), env=env, timeout=5)
            status, stdout, stderr = r.returncode, r.stdout.decode(), r.stderr.decode()
        actual = (status, stdout, stderr)
        print(json.dumps(dict(case=name, expected=expected, actual=actual, baseline_failure=actual != expected)), flush=True)
        assert actual != expected, 'baseline unexpectedly passes'
