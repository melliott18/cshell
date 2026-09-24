#!/usr/bin/env python3
"""Script regressions for job builtins through all three invocation modes."""
import argparse
from pathlib import Path
import os
import json
import subprocess
import sys
import signal
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binary')
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    cases = [
        ('wait', 0, '', ''),
        ('kill -l 143 >&-', 1, '', 'cshell: kill: cannot write output\n'),
        ('set -o >&-', 1, '', 'cshell: set: cannot write output\n'),
        ('/bin/sleep 60 & jobs -p >&- && /bin/echo WRONG; kill -KILL %1; wait', 0, '', 'cshell: jobs: cannot write output\n'),
        ('jobs', 0, '', ''),
        ('wait %99', 127, '', 'cshell: wait: unknown job or pid: %99\n'),
        ('wait invalid', 127, '', 'cshell: wait: unknown job or pid: invalid\n'),
        ('wait 999999999999999999999999999999', 127, '', 'cshell: wait: unknown job or pid: 999999999999999999999999999999\n'),
        ('fg', 1, '', 'cshell: fg: job control unavailable\n'),
        ('bg %1', 1, '', 'cshell: bg: job control unavailable\n'),
        ('set -m', 1, '', 'cshell: set: job control unavailable\n'),
        ('set -o monitor', 1, '', 'cshell: set: job control unavailable\n'),
        ('set +m; set -b; set -o', 0, 'monitor off\nnotify on\n', ''),
        ('set +b; set +o', 0, 'set +m\nset +b\n', ''),
        ('set -z', 1, '', 'cshell: set: unsupported option: -z\n'),
        ('set -o unknown', 1, '', 'cshell: set: unsupported option: unknown\n'),
        ('jobs -z', 1, '', 'cshell: jobs: no such job: -z\n'),
        ('kill -s UNKNOWN 1', 1, '', 'cshell: kill: invalid signal\n'),
        ('kill -s', 1, '', 'cshell: kill: signal required\n'),
        ('kill -- bad', 1, '', 'cshell: kill: invalid pid: bad\n'),
        ('kill %42', 1, '', 'cshell: kill: no such job: %42\n'),
        ('kill -l 143', 0, 'TERM\n', ''),
        ('kill -l bad', 1, '', 'cshell: kill: invalid status: bad\n'),
        ('exit 31 & wait %1', 31, '', ''),
        ('exit 31 & wait %1; wait %1', 127, '', 'cshell: wait: unknown job or pid: %1\n'),
        ('exit 11 | exit 31 & wait %1', 31, '', ''),
        ('! exit 11 | exit 0 & wait %1', 1, '', ''),
        ('exit 3 & exit 7 & wait %1 %2', 7, '', ''),
        ('exit 3 & exit 7 & wait', 0, '', ''),
        ('exit 3 & (wait %1); wait %1', 3, '', 'cshell: wait: unknown job or pid: %1\n'),
        ('/usr/bin/head -c 1 & wait %1', 0, '', ''),
        ('/bin/sleep 60 & kill -TERM %1; wait %1', 128 + signal.SIGTERM, '', ''),
        ('/bin/sleep 60 | /bin/sleep 60 & kill -KILL %1; wait %1', 128 + signal.SIGKILL, '', ''),
        ('/bin/sleep 60 & kill -STOP %1; kill -CONT %1; kill -TERM %1; wait %1', 128 + signal.SIGTERM, '', ''),
        ('/bin/sleep 60 & kill -0 %1; kill -KILL %1; wait', 0, '', ''),
        ('/bin/sleep 60 & kill -KILL %/bin/sleep; wait', 0, '', ''),
        ("/bin/sleep 60 & kill -KILL '%?sleep'; wait", 0, '', ''),
        ('exit 3 & wait %1 | /usr/bin/wc -c; wait %1', 3, '       0\n' if os.uname().sysname == 'Darwin' else '0\n', 'cshell: wait: unknown job or pid: %1\n'),
    ]
    suite = {"version": 1, "name": "job builtins", "kind": "replacement", "cases": []}
    for index, (script, status, output, error) in enumerate(cases):
        for mode in ('string', 'stdin', 'file'):
            case = dict(stdin="", name=f"job case {index + 1} ({mode}): {script}",
                        expect=dict(status=status, stdout=output, stderr=error))
            if mode == 'string':
                case['args'] = ['-c', script + '\n']
            elif mode == 'stdin':
                case['stdin'] = script + '\n'
            else:
                case['setup'] = {'script': script + '\n'}
                case['args'] = ['script']
            suite['cases'].append(case)
    suite['cases'].append(dict(name="invalid options are atomic", stdin="",
        args=['-ic', 'set +m; set -bz; set -o'],
        expect=dict(status=0, stdout='monitor off\nnotify off\n',
                    stderr='cshell: set: unsupported option: -bz\n')))
    with tempfile.TemporaryDirectory(prefix='cshell-jobs-') as temp:
        path = Path(temp) / 'jobs.json'
        path.write_text(json.dumps(suite))
        subprocess.run([sys.executable, str(Path(__file__).with_name('smoke.py')),
                        binary, '--suite', str(path)], check=True, timeout=180)



if __name__ == '__main__':
    main()
