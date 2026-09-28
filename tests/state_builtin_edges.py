#!/usr/bin/env python3
"""CSH-048 runtime edge partitions with bounded shared-runner assertions.

Fault binaries run the public main with only named syscall/allocation seams
interposed. Capability skips are explicit; no shell comparison supplies oracles.
"""
import locale
import os
from pathlib import Path
import shlex
import sys
import tempfile

import smoke

binary, fault, helper = (Path(p).resolve() for p in sys.argv[1:])
passed = failed = skipped = 0


def run(name, script, *, candidate=binary, stdout='', stderr='', status=0, env=None, setup=None, files=None):
    global passed, failed
    for mode in ('string', 'file', 'stdin'):
        fixture = dict(name=f'state-edge: {name} ({mode})', env=env or {}, setup=dict(setup or {}),
                       expect=dict(stdout=stdout, stderr=stderr, status=status, files=files or {}), stdin='', args=[])
        if mode == 'string': fixture['args'] = ['-c', script + '\n']
        elif mode == 'file':
            fixture['setup']['script'] = script + '\n'
            fixture['args'] = ['script']
        else: fixture['stdin'] = script + '\n'
        errors = smoke.run_case(candidate, fixture, 5, 65536)
        print(('FAIL' if errors else 'PASS') + ': ' + fixture['name'], flush=True)
        if errors:
            failed += 1
            print(errors, flush=True)
        else: passed += 1


# Every initialization allocation, including state updates and cwd storage.
# 99 is emitted only after initialize succeeds without reaching the next point.
for mode in ('string', 'file', 'stdin'):
    for point in range(1, 256):
        with tempfile.TemporaryDirectory(prefix='cshell-startup-') as temporary:
            directory = Path(temporary)
            case = dict(args=[], stdin='', env={'CSH_STATE_FAULT': 'startup-allocation',
                                               'CSH_STATE_FAULT_AT': str(point)})
            if mode == 'string': case['args'] = ['-c', 'printf initialized']
            elif mode == 'file':
                (directory / 'script').write_text('printf initialized\n')
                case['args'] = ['script']
            else: case['stdin'] = 'printf initialized\n'
            status, output, errors = smoke.capture(fault, case, directory, 5, 65536)
            expected = b'' if status == 99 else b'cshell: cannot initialize shell variables\n'
            expected_output = b'initialized' if status == 99 else b''
            ok = status in (1, 99) and not errors and output['stdout'] == expected_output and output['stderr'] == expected
            print(('PASS' if ok else 'FAIL') + f': state-edge: startup allocation {point} ({mode})', flush=True)
            if ok: passed += 1
            else:
                failed += 1
                print(status, output, errors, flush=True)
            if status == 99: break
    else:
        failed += 1
        print('FAIL: initialization allocation sweep did not exhaust all points')

for operation in ('times', 'ticks'):
    run(operation + ' unavailable', 'command times; echo "$?"', candidate=fault,
        stdout='2\n', stderr='cshell: times: cannot obtain process times\n', env={'CSH_STATE_FAULT': operation})
for operation, command, diagnostic in (
    ('getrlimit', 'ulimit -f', 'cannot get resource limit'),
    ('setrlimit', 'ulimit -S -f 1', 'cannot set resource limit'),
    ('read-eio', 'read value <data', 'cannot read input'),
):
    name = command.split()[0]
    run(operation, command + '; echo "$?"', candidate=fault, stdout='2\n',
        stderr=f'cshell: {name}: {diagnostic}\n', env={'CSH_STATE_FAULT': operation}, setup={'data': 'value\n'})
run('read EINTR retry', 'read value <data; printf "%s:%s\\n" "$?" "$value"', candidate=fault,
    stdout='0:value\n', env={'CSH_STATE_FAULT': 'read-eintr'}, setup={'data': 'value\n'})
run('listing interrupted partial writes', "readonly A=\"a'b\"; readonly -p", candidate=fault,
    stdout="readonly A='a'\\''b'\n", env={'CSH_STATE_FAULT': 'write-retry'})
run('listing zero write is error', 'readonly A=x; command readonly -p; echo "$?"', candidate=fault,
    stdout='1\n', stderr='cshell: readonly: cannot write output\n', env={'CSH_STATE_FAULT': 'write-zero'})
run('cd physical unavailable without e',
    'mkdir target; cd -P target; printf "%s:%s\\n" "$?" "${PWD-unset}"; : >marker',
    candidate=fault, stdout='0:unset\n', env={'CSH_STATE_FAULT': 'cwd'},
    files={'target/marker': {'type': 'file', 'content': ''}, 'marker': {'type': 'absent'}})
# Validate actual cwd/rollback independently of the unavailable getcwd wrapper.
run('cd physical unavailable with e rolls back',
    'mkdir target; cd -P -e target; echo "$?"; : >marker; test -f marker && test ! -f target/marker',
    candidate=fault, stdout='1\n', stderr='cshell: cd: cannot change directory or update directory state\n',
    env={'CSH_STATE_FAULT': 'cwd'})
run('malformed environment policy',
    f'{shlex.quote(str(helper))} malformed-environment {shlex.quote(str(binary))} -c ' + shlex.quote(
        'printf "%s:%s\\n" "$DUPLICATE" "$VALID"; '
        'case "$(export -p)" in *1bad*|*NOEQUAL*|*invalid*) exit 9;; esac'), stdout='last:okay\n')
run('over PATH_MAX imported PWD permitted normalization',
    # Use redundant slash prefix, not repeated pathname components.
    'slashes=/; n=0; while test "$n" -lt 14; do slashes=$slashes$slashes; n=$((n+1)); done; '
    f'PWD=$slashes$PWD {shlex.quote(str(binary))} -c ' + shlex.quote('test "$PWD" = "$(pwd -P)"'))

run('actual cwd beyond PATH_MAX',
    f'{shlex.quote(str(helper))} deep-directory {shlex.quote(str(binary))} -c ' + shlex.quote(
        'test "$PWD" = "$EXPECTED_CWD" || exit 9; test "$(pwd -P)" = "$EXPECTED_CWD" || exit 8; '
        'mkdir child; cd -L child || exit 7; test "$PWD" = "$EXPECTED_CWD/child" || exit 6; '
        'cd -P ..; test "$PWD" = "$EXPECTED_CWD"'))
for operation, value in (('limit-units', '7'), ('limit-unlimited', 'unlimited')):
    run(operation + ' all base resources',
        '; '.join(f'ulimit -S -{option} {value} || exit 9' for option in 'cdfnsv'),
        candidate=fault, env={'CSH_STATE_FAULT': operation})
# The harness bounds the hard file limit; raising it must fail for non-root
# processes. Kernel inheritance and units are independently observed by P cases.
if os.geteuid() == 0:
    skipped += 4
    print('SKIP: denied dot candidate, cd target/cwd and hard limit raise: root bypasses discretionary permission checks; CSH-048 requires non-root native/Docker runs')
else:
    run('dot denied first readable later',
        'saved=$PATH; chmod 000 denied/source; PATH="$PWD/denied:$PWD/allowed" . source; '
        'result=$?; PATH=$saved; printf "%s:%s\\n" "$result" "$value"; chmod 600 denied/source', stdout='0:readable\n',
        setup={'denied/source': 'value=forbidden\n', 'allowed/source': 'value=readable\n'})
    run('ulimit hard raise denied',
        'ulimit -f 1; ulimit -H -f 2; echo \"$?\"', stdout='2\n',
        stderr='cshell: ulimit: cannot set resource limit\n')
    run('cd leaves searchable unreadable cwd',
        'base=$PWD; mkdir restricted; chmod 111 restricted; cd restricted; '
        'cd "$base"; result=$?; chmod 700 "$base/restricted"; '
        'printf "%s\\n" "$result"; test "$PWD" = "$base"', stdout='0\n')
    run('cd denied preserves state',
        'base=$PWD; before=${OLDPWD-unset}; mkdir denied; chmod 000 denied; cd denied; echo "$?"; '
        'chmod 700 denied; test "$PWD" = "$base" && test "${OLDPWD-unset}" = "$before"', stdout='1\n',
        stderr='cshell: cd: cannot change directory or update directory state\n')

# XBD LC_COLLATE supplies an independent host strcoll oracle, not another shell.
original = locale.setlocale(locale.LC_COLLATE)
selected = None
try:
    for candidate in ('en_US.UTF-8', 'fr_FR.UTF-8', 'C.UTF-8'):
        try: locale.setlocale(locale.LC_COLLATE, candidate)
        except locale.Error: continue
        selected = candidate
        names = sorted(('Avar', 'avar', 'Zvar', 'zvar'), key=locale.strxfrm)
        break
finally:
    locale.setlocale(locale.LC_COLLATE, original)
if selected:
    run('set non-C collation ' + selected,
        'Avar=1; avar=2; Zvar=3; zvar=4; set >vars; '
        'while IFS= read -r line; do case $line in Avar=*|avar=*|Zvar=*|zvar=*) printf "%s\\n" "$line";; esac; done <vars',
        stdout=''.join(f"{name}='{dict(Avar=1, avar=2, Zvar=3, zvar=4)[name]}'\n" for name in names),
        env={'LC_ALL': selected})
else:
    skipped += 1
    print('SKIP: non-C set collation: no en_US.UTF-8/fr_FR.UTF-8/C.UTF-8; CSH-048 locale coverage remains required')

print(f'Result: {passed} passed, {failed} failed, {skipped} skipped', flush=True)
raise SystemExit(bool(failed))
