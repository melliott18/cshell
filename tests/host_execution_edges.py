#!/usr/bin/env python3
"""Independent fallback, descriptor, exec-error and time-accuracy qualification."""
import argparse
import errno
import json
import math
import os
import platform
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile
import time

import smoke
from host_execution import identity, MODES
from host_execution_cases import BASE, matches
from host_utilities import inventory, serial, source_identity, sanitizer_diagnostic

# Expectations are authored from shell semantics, never copied from /bin/sh.
FALLBACK = (
    ('quoted-parameters', 'printf "<%s>\\n" "$1" "$2" "$#"\n', b'<two words>\n<*>\n<2>\n', 0, {}),
    ('environment', 'printf "%s\\n" "$CSH_WITNESS"\n', b'kept\n', 0, {}),
    ('function-scope', 'f() { printf "%s:%s\\n" "$#" "$1"; }; f inner; printf "%s\\n" "$1"\n',
     b'1:inner\ntwo words\n', 0, {}),
    ('substitution', 'value=$(printf "one\\n\\n"); printf "<%s>\\n" "$value"\n', b'<one>\n', 0, {}),
    ('quoted-heredoc', 'read value <<\'END\'\n$CSH_WITNESS\nEND\nprintf "%s\\n" "$value"\n', b'$CSH_WITNESS\n', 0, {}),
    ('subshell-isolation', 'v=outer; (v=inner); printf "%s\\n" "$v"\n', b'outer\n', 0, {}),
    ('ordered-redirection', 'printf "owned\\n" >effect; read value <effect; printf "%s\\n" "$value"\n', b'owned\n', 0, {'effect': b'owned\n'}),
    ('exit-trap', 'trap \'printf "trap\\n"\' 0; exit 23\n', b'trap\n', 23, {}),
    ('syntax-error', 'if\n', b'', 'nonzero', {}),
)


def execute(binary, fixture, directory):
    start_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    try:
        status, output, errors = smoke.capture(binary, fixture, directory, 5, 65536)
    except (OSError, subprocess.SubprocessError) as error:
        status, output, errors = None, {'stdout': b'', 'stderr': b''}, ['setup: ' + str(error)]
    elapsed = time.monotonic() - start
    end_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = {key: bytes(value) for key, value in output.items()}
    if sanitizer_diagnostic(output):
        errors.append('sanitizer diagnostic')
    return dict(status=status, **output, errors=errors, elapsed=elapsed,
                child_user=end_usage.ru_utime - start_usage.ru_utime,
                child_sys=end_usage.ru_stime - start_usage.ru_stime)


def fixture_for(argv, mode, directory, search_path, data=b''):
    fixture = dict(args=argv[1:], stdin=data, env={'PATH': search_path, 'CSH_WITNESS': 'kept'})
    if mode == 'direct':
        return argv[0], fixture
    # Quoting the command name also makes time's redirections specified.
    script = "'" + argv[0].replace("'", "'\\''") + "' " + shlex.join(argv[1:])
    if mode == 'string':
        fixture['args'] = ['-c', script]
    elif mode == 'file':
        (directory / 'commands').write_text(script + '\n')
        fixture['args'] = ['commands']
    else:
        (directory / 'payload').write_bytes(data)
        fixture['args'] = []
        fixture['stdin'] = script + ' <payload\n'
    return None, fixture


def fallback_cases(binary, search_path):
    rows = []
    for name, source, expected, status, effects in FALLBACK:
        for mode in MODES:
            with tempfile.TemporaryDirectory(prefix='csh-fallback-') as temporary:
                directory = Path(temporary)
                script = directory / 'plain'
                script.write_text(source)
                script.chmod(0o700)
                shadow = directory / 'shadow'
                shadow.mkdir()
                (shadow / 'sh').write_text('#!/bin/sh\nexit 93\n')
                (shadow / 'sh').chmod(0o700)
                argv = ([str(script), 'two words', '*'] if mode != 'direct'
                        else ['/bin/sh', str(script), 'two words', '*'])
                target, fixture = fixture_for(argv, mode, directory, str(shadow) + ':' + search_path)
                actual = execute(target or binary, fixture, directory)
                observed = {path: (directory / path).read_bytes() if (directory / path).exists() else None
                            for path in effects}
                ok = (actual['status'] is not None and matches(status, actual['status'], mode, {}) and actual['stdout'] == expected
                      and bool(actual['stderr']) == (status == 'nonzero') and not actual['errors']
                      and observed == effects)
                rows.append(dict(id='sh/fallback-' + name, mode=mode, verdict='PASS' if ok else 'FAIL',
                                 source=BASE + 'sh.html', expected=serial(dict(stdout=expected, status=status, files=effects)),
                                 actual=serial(dict(**actual, files=observed)), invocation=serial(fixture)))
    return rows


def timing_matches(actual, measured, tick):
    """Bound reported time by inner measurements and whole-invocation usage.

    Two ticks allow display quantization and accounting updates. No fixed
    maximum elapsed time is called a utility contract; the watchdog is separate.
    """
    match = re.match(rb'\n?real ([0-9]+\.[0-9]+)\nuser ([0-9]+\.[0-9]+)\nsys ([0-9]+\.[0-9]+)\n', actual['stderr'])
    if not match or not matches('timing', actual['stderr'], 'direct', {'status': 0}):
        return False
    reported = dict(zip(('real', 'user', 'sys'), map(float, match.groups())))
    tolerance = 2 / tick
    upper = dict(real=actual['elapsed'], user=actual['child_user'], sys=actual['child_sys'])
    return all(math.isfinite(measured[key]) and measured[key] >= 0 and
               measured[key] - tolerance <= reported[key] <= upper[key] + tolerance for key in reported)


def process_and_timing_cases(binary, helper, providers, search_path):
    rows = []
    payload = bytes(range(256))
    for utility in ('env', 'nice', 'nohup', 'time'):
        for mode in MODES:
            with tempfile.TemporaryDirectory(prefix='csh-process-io-') as temporary:
                directory = Path(temporary)
                provider = providers[utility]['path']
                if not provider:
                    rows.append(dict(id=utility + '/stdin-bytes', mode=mode, verdict='FAIL', phase='provider'))
                    continue
                args = ['-p'] if utility == 'time' else []
                target, fixture = fixture_for([provider] + args + [str(helper), 'copy-input'], mode, directory, search_path, payload)
                actual = execute(target or binary, fixture, directory)
                expected_err = 'timing' if utility == 'time' else b''
                ok = (actual['status'] == 0 and actual['stdout'] == payload and not actual['errors']
                      and matches(expected_err, actual['stderr'], mode, {'status': 0})
                      and not (directory / 'nohup.out').exists())
                rows.append(dict(id=utility + '/stdin-bytes', mode=mode, verdict='PASS' if ok else 'FAIL',
                                 source=BASE + utility + '.html', actual=serial(actual)))
    for workload in ('wall', 'cpu', 'child'):
        for mode in MODES:
            with tempfile.TemporaryDirectory(prefix='csh-time-') as temporary:
                directory = Path(temporary)
                if not providers['time']['path']:
                    rows.append(dict(id='time/accuracy-' + workload, mode=mode, verdict='FAIL', phase='provider'))
                    continue
                target, fixture = fixture_for([providers['time']['path'], '-p', str(helper), 'measure', workload], mode, directory, search_path)
                actual = execute(target or binary, fixture, directory)
                try:
                    measured = json.loads((directory / 'measurement.json').read_text())
                    ok = timing_matches(actual, measured, os.sysconf('SC_CLK_TCK'))
                except (OSError, ValueError, KeyError, TypeError):
                    measured, ok = None, False
                ok &= actual['status'] == 0 and not actual['stdout'] and not actual['errors']
                rows.append(dict(id='time/accuracy-' + workload, mode=mode, verdict='PASS' if ok else 'FAIL',
                                 source=BASE + 'time.html', measured=measured,
                                 tolerance_seconds=2 / os.sysconf('SC_CLK_TCK'), actual=serial(actual)))
    return rows


def resource_cases(binary, helper, search_path):
    rows = []
    for kind, expected_errno, shell_status in (('missing', errno.ENOENT, 127), ('denied', errno.EACCES, 126), ('format', errno.ENOEXEC, 29)):
        for mode in MODES:
            with tempfile.TemporaryDirectory(prefix='csh-exec-error-') as temporary:
                directory = Path(temporary)
                target_file = directory / kind
                if kind != 'missing':
                    target_file.write_text('exit 29\n')
                    target_file.chmod(0o700 if kind == 'format' else 0o600)
                argv = [str(helper), 'exec-error', str(target_file)] if mode == 'direct' else [str(target_file)]
                target, fixture = fixture_for(argv, mode, directory, search_path)
                actual = execute(target or binary, fixture, directory)
                expected = dict(status=0, stdout=f'{expected_errno}\n'.encode(), diagnostic=False) if mode == 'direct' else dict(status=shell_status, stdout=b'', diagnostic=kind != 'format')
                ok = (actual['status'] == expected['status'] and actual['stdout'] == expected['stdout']
                      and bool(actual['stderr']) == expected['diagnostic'] and not actual['errors'])
                rows.append(dict(id='exec/' + kind, mode=mode, verdict='PASS' if ok else 'FAIL',
                                 source=BASE.replace('utilities/', 'functions/') + 'exec.html',
                                 stage='execve-return' if mode == 'direct' else 'shell-dispatch',
                                 expected=serial(expected), actual=serial(actual)))
    for mode in MODES:
        with tempfile.TemporaryDirectory(prefix='csh-fd-limit-') as temporary:
            directory = Path(temporary)
            target, fixture = fixture_for([str(helper), 'fd-exhaustion'], mode, directory, search_path)
            actual = execute(target or binary, fixture, directory)
            try:
                measured = json.loads(actual['stdout'])
            except ValueError:
                measured = None
            ok = (actual['status'] == 0 and not actual['stderr'] and not actual['errors']
                  and measured == dict(errno=errno.EMFILE, soft=32, restored=True))
            rows.append(dict(id='resource/descriptor-exhaustion', mode=mode, verdict='PASS' if ok else 'FAIL',
                             stage='helper-entered', measured=measured, actual=serial(actual)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('helper', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    binary, helper = args.binary.resolve(), args.helper.resolve()
    providers = inventory(args.path, ('env', 'nice', 'nohup', 'time'))
    rows = (fallback_cases(binary, args.path) + process_and_timing_cases(binary, helper, providers, args.path)
            + resource_cases(binary, helper, args.path))
    result = dict(ticket='CSH-075', source_identity=source_identity(), binary=identity(binary), helper=identity(helper),
                  uname=list(os.uname()), path=args.path, providers=providers, fallback=identity('/bin/sh'),
                  scope='explicit fallback programs, binary stdin handoff, bounded timing accuracy, exec errors and descriptor limit',
                  limits=dict(timeout_seconds=5, output_bytes=65536),
                  unqualified={
                      'U-040/true-exec-resources': 'Memory exhaustion and precise production loader entry are not supplied.',
                      'U-040/false-exec-resources': 'Memory exhaustion and precise production loader entry are not supplied.',
                      'U-040/kill-identities-resources': 'Prior Linux controls retained; broader identity and utility resource faults remain open.',
                      'U-040/env-ARG_MAX': 'Kernel error handoff is tested; env internal-exec E2BIG remains open.',
                      'U-040/sleep-duration': 'Finite virtual-duration boundaries retained; no duration maximum claim.',
                      'U-040/sh-host-semantics': 'Only the enumerated external /bin/sh programs are qualified.'},
                  qualification_owner='CSH-075',
                  implementation_owner='selected utility/libc/platform vendor', cases=rows,
                  totals=dict(passed=sum(r['verdict']=='PASS' for r in rows), failed=sum(r['verdict']!='PASS' for r in rows)))
    query = ['dpkg-query', '-W', '-f=${Package} ${Version}\n'] if platform.system() == 'Linux' else ['sw_vers']
    result['package_environment'] = subprocess.check_output(query, text=True, timeout=5)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    for row in rows:
        print(row['verdict'] + ': ' + row['id'] + ' (' + row['mode'] + ')')
    print(json.dumps(result['totals']))
    return int(bool(result['totals']['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
