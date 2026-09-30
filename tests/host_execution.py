#!/usr/bin/env python3
"""Strict, bounded host execution qualification (CSH-075); failures never waived."""
import argparse
from contextlib import contextmanager
import ctypes
import errno
import json
import os
from pathlib import Path
import platform
import selectors
import shlex
import shutil
import signal
import subprocess
import tempfile
import time

import smoke
from host_execution_cases import BASE, UTILITIES, cases, matches
from host_utilities import inventory, serial, sha, source_identity, sanitizer_diagnostic

MODES = ('direct', 'string', 'file', 'stdin')


def identity(path):
    return dict(path=str(path), realpath=os.path.realpath(path), sha256=sha(path))


def owned_process(helper, increment=0):
    process = subprocess.Popen([str(helper), 'park'], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                               start_new_session=True,
                               preexec_fn=lambda: os.nice(increment))
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(2) or process.stdout.readline() != b'ready\n':
                raise RuntimeError('owned process readiness failed')
        return process
    except BaseException:
        process.kill()
        process.wait(timeout=2)
        process.stdout.close()
        raise


@contextmanager
def adopt_descendants():
    """Reap timeout's orphaned child when timeout kills its own process group."""
    if platform.system() != 'Linux':
        yield
        return
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'read child-subreaper state')
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'enable child subreaper')
    try:
        yield
    finally:
        if libc.prctl(36, previous.value, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), 'restore child-subreaper state')


def reap_owned(pid):
    """Only wait for the recorded helper, never another invocation's children."""
    deadline = time.monotonic() + 2
    while True:
        try:
            child, _ = os.waitpid(pid, os.WNOHANG)
            if child:
                return
            # A zero return proves this is still our unreaped child.
            os.kill(pid, signal.SIGKILL)
        except (ChildProcessError, ProcessLookupError):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('could not reap owned timeout child within 2s')
        time.sleep(0.01)


def run_case(binary, helper, providers, search_path, name, mode):
    try:
        with adopt_descendants():
            return _run_case(binary, helper, providers, search_path, name, mode)
    except OSError as error:
        return dict(id=name, mode=mode, verdict='FAIL', phase='setup', reason=str(error))


def _run_case(binary, helper, providers, search_path, name, mode):
    process = None
    with tempfile.TemporaryDirectory(prefix='csh-execution-') as temporary:
        directory = Path(temporary)
        row = dict(id=name, mode=mode, verdict='FAIL', phase='setup')
        try:
            if name.startswith(('kill/probe', 'kill/deliver', 'ps/owned', 'renice/')):
                process = owned_process(helper, 4 if name.startswith("renice/") else 0)
            pid = process.pid if process else 0
            case = next(c for c in cases(str(helper), directory, pid) if c['id'] == name)
            row.update(case=serial(case), source=BASE + case['utility'] + '.html')
            provider = providers[case['utility']]['path']
            if not provider:
                row.update(phase='provider', reason='required executable missing')
                return row
            (directory / 'argument-probe').symlink_to(helper)
            (directory / 'denied').write_text('exit 0\n')
            (directory / 'host-script').write_text('printf "%s\\n" "$1"\n: >effect\n')
            before_priority = os.getpriority(os.PRIO_PROCESS, pid) if process else None
            fixture = dict(args=case['args'], stdin=case.get('stdin', b''),
                           env=dict(PATH=search_path, **case.get('env', {})))
            target = provider
            if mode != 'direct':
                # kill's intrinsic dispatch is checked as well as its external exec.
                script = ('command ' if case['utility'] == 'time' else '') + shlex.join([case['utility']] + case['args']) + '\n'
                target = binary
                if mode == 'string':
                    fixture['args'] = ['-c', script]
                elif mode == 'file':
                    (directory / 'script').write_text(script)
                    fixture['args'] = ['script']
                else:
                    # Redirection gives the invoked utility its own supplied stdin;
                    # cshell's command stream must not become the utility payload.
                    (directory / 'input').write_bytes(fixture['stdin'])
                    fixture['stdin'] = script.rstrip() + ' <input\n'
                    fixture['args'] = []
            started = time.monotonic()
            status, output, errors = smoke.capture(target, fixture, directory, 5, 65536)
            elapsed = time.monotonic() - started
            output = {k: bytes(v) for k, v in output.items()}
            if sanitizer_diagnostic(output):
                errors.append('sanitizer diagnostic')
            expected_out, actual_out = case['stdout'], output['stdout']
            if case.get('unordered'):
                expected_out, actual_out = sorted(expected_out.splitlines()), sorted(actual_out.splitlines())
            ok = (matches(case['status'], status, mode, case) and
                  matches(expected_out, actual_out, mode, case) and
                  matches(case['stderr'], output['stderr'], mode, case))
            effects = {}
            child_file = directory / 'child.pid'
            if child_file.exists():
                child_pid = int(child_file.read_text())
                reap_owned(child_pid)
                try:
                    os.kill(child_pid, 0)
                    effects['timeout_child_gone'] = False
                except ProcessLookupError:
                    effects['timeout_child_gone'] = True
                effects['timeout_child_pid'] = child_pid
                ok &= effects['timeout_child_gone']
            for path in case.get('absent', []):
                effects[path] = (directory / path).exists()
                ok &= not effects[path]
            if 'minimum_seconds' in case:
                ok &= elapsed >= case['minimum_seconds']
            if case.get('alive'):
                effects['alive'] = process.poll() is None
                ok &= effects['alive']
            if 'terminated' in case:
                try:
                    effects['owned_status'] = process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    effects['owned_status'] = None
                ok &= effects['owned_status'] == -case['terminated']
            if 'priority_delta' in case:
                # Query the kernel through a separate disposable helper. Darwin's
                # ceiling is 20; Linux's is 19. Neither utility supplies this oracle.
                control_directory = directory / 'priority-control'
                control_directory.mkdir()
                control_status, control_output, control_errors = smoke.capture(
                    helper, dict(args=['nice-ceiling'], stdin=''), control_directory, 5, 65536)
                row['priority_control'] = serial(dict(status=control_status,
                    **control_output, errors=control_errors))
                if control_status != 0 or control_output['stderr'] or control_errors:
                    raise RuntimeError('priority ceiling control failed')
                ceiling = int(control_output['stdout'])
                effects['nice_ceiling_control'] = serial(dict(status=control_status,
                    **control_output, errors=control_errors, ceiling=ceiling))
                effects['nice_before'] = before_priority
                effects['nice_after'] = os.getpriority(os.PRIO_PROCESS, pid)
                ok &= (control_status == 0 and not control_output['stderr'] and not control_errors
                       and ceiling >= before_priority
                       and effects['nice_after'] == min(ceiling, before_priority + case['priority_delta']))
            row.update(phase='assertion', verdict='PASS' if ok and not errors else 'FAIL',
                       actual=serial(dict(status=status, **output, errors=errors, effects=effects,
                                          elapsed_seconds=elapsed)), invocation=serial(fixture))
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            row.update(reason=str(error), errno=getattr(error, 'errno', None))
        finally:
            if process is not None:
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
                    row['owned_cleanup'] = dict(pid=process.pid, reaped=True)
                except (OSError, subprocess.SubprocessError) as error:
                    row.update(verdict='FAIL', cleanup_error=str(error))
                finally:
                    process.stdout.close()
        return row


def enoexec(binary, search_path):
    rows = []
    for mode in MODES[1:]:
        with tempfile.TemporaryDirectory(prefix='csh-enoexec-') as temporary:
            directory = Path(temporary)
            shadow = directory / 'shadow'
            shadow.mkdir()
            (shadow / 'sh').write_text('#!/bin/sh\nexit 93\n')
            (shadow / 'sh').chmod(0o700)
            script = directory / 'plain'
            script.write_text('printf "%s\\n" "$CSH_FALLBACK" "$1"\nexit 17\n')
            script.chmod(0o700)
            command = shlex.join([str(script), 'two words']) + '\n'
            fixture = dict(args=[], stdin='', env={'PATH': str(shadow) + ':' + search_path,
                                                   'CSH_FALLBACK': 'fallback'})
            if mode == 'string':
                fixture['args'] = ['-c', command]
            elif mode == 'file':
                (directory / 'script').write_text(command)
                fixture['args'] = ['script']
            else:
                fixture['stdin'] = command
            status, output, errors = smoke.capture(binary, fixture, directory, 5, 65536)
            ok = status == 17 and output['stdout'] == b'fallback\ntwo words\n' and not output['stderr'] and not errors
            rows.append(dict(id='sh/ENOEXEC-independent-PATH', mode=mode,
                             verdict='PASS' if ok else 'FAIL', phase='assertion',
                             actual=serial(dict(status=status, **output, errors=errors)),
                             fallback=identity('/bin/sh'), path_sh=identity(shadow / 'sh')))
    return rows


def exec_threshold(provider, utility, helper):
    """Bound a fixed aggregate argv shape using execve's independent E2BIG report.

    No shell, utility diagnostic or guessed ARG_MAX margin decides loader entry.
    A small fixed environment and 4096-byte strings avoid Linux per-string limits.
    """
    rows = []
    prefix = [provider] if utility != 'env' else [provider, '-i', str(helper), 'exit', '0']
    # env requires a helper which tolerates trailing padding arguments.
    if utility == 'env':
        prefix = [provider, '-i', str(helper), 'env']
    ceiling = 4096  # <= 16 MiB argv content plus pointer storage
    def attempt(count):
        argv = prefix + ['x' * 4095] * count
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
                process = subprocess.Popen(argv, env={'LC_ALL': 'C'}, stdin=subprocess.DEVNULL,
                                           stdout=output, stderr=diagnostic, start_new_session=True,
                                           preexec_fn=lambda: smoke.child_limits(3, 65536, 65536))
                try:
                    status = process.wait(timeout=3)
                finally:
                    smoke.kill_group(process)
                    process.wait(timeout=2)
                output.seek(0)
                diagnostic.seek(0)
                stdout, stderr = output.read(65537), diagnostic.read(65537)
            expected = 1 <= status <= 125 if utility == 'false' else status == 0
            if not expected or stdout or stderr:
                raise RuntimeError('entered utility failed control: ' + repr((status, stdout, stderr)))
            return dict(count=count, stage='entered', status=status)
        except OSError as error:
            if error.errno != errno.E2BIG:
                raise
            return dict(count=count, stage='kernel-rejected', errno=error.errno)
    low, high = 0, ceiling
    rows.extend([attempt(low), attempt(high)])
    if rows[0]['stage'] != 'entered' or rows[1]['stage'] != 'kernel-rejected':
        raise RuntimeError('aggregate boundary not bracketed within 16 MiB')
    while high - low > 1:
        middle = (low + high) // 2
        result = attempt(middle)
        rows.append(result)
        if result['stage'] == 'entered':
            low = middle
        else:
            high = middle
    return dict(id=utility + '/aggregate-exec-boundary', phase='assertion', verdict='PASS',
                source=BASE.replace('utilities/', 'functions/') + 'exec.html',
                environment={'LC_ALL': 'C'}, arg_max=os.sysconf('SC_ARG_MAX'),
                string_bytes=4096, last_success=low, first_e2big=high,
                prefix=prefix, observations=rows,
                boundary='fixed argv shape; env internal exec failure remains unqualified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('helper', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--subset', type=Path, help='Explicit case IDs; omitted cases stay unqualified')
    parser.add_argument('--clock-library', type=Path, help='Linux opt-in virtual sleep oracle')
    parser.add_argument('--controlled-identities', action='store_true', help='Disposable Linux root only')
    args = parser.parse_args()
    if args.controlled_identities and (platform.system() != 'Linux' or os.geteuid() != 0):
        parser.error('--controlled-identities requires disposable Linux root')
    if args.clock_library and platform.system() != 'Linux':
        parser.error('--clock-library requires Linux')
    binary, helper = args.binary.resolve(), args.helper.resolve()
    providers = inventory(args.path, UTILITIES)
    selected = json.loads(args.subset.read_text()) if args.subset else None
    names = [row['id'] for row in cases(str(helper), Path('.'), 0)]
    if selected is not None:
        if not isinstance(selected, list) or not selected or len(set(selected)) != len(selected) or set(selected) - set(names):
            parser.error('subset must be a nonempty unique list of known case IDs')
        names = selected
    rows = []
    for name in names:
        for mode in MODES:
            row = run_case(binary, helper, providers, args.path, name, mode)
            rows.append(row)
            print(row['verdict'] + ': ' + name + ' (' + mode + ')', flush=True)
    rows.extend(enoexec(binary, args.path))
    for utility in ('true', 'false', 'env'):
        try:
            if not providers[utility]['path']:
                raise RuntimeError('required provider missing')
            rows.append(exec_threshold(providers[utility]['path'], utility, helper))
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            rows.append(dict(id=utility + '/aggregate-exec-boundary', verdict='FAIL',
                             phase='setup', reason=str(error)))
    # Loader capability is observed separately; a successful binary under the
    # imposed descriptor bound cannot be mislabeled a fault-injection success.
    loader = []
    for utility in ('true', 'false'):
        if providers[utility]['path']:
            with tempfile.TemporaryDirectory(prefix='csh-loader-') as temporary:
                status, output, errors = smoke.capture(helper, dict(args=['loader', providers[utility]['path']], stdin=''),
                                                       Path(temporary), 5, 65536)
                loader.append(dict(utility=utility, status=status, output=serial(output), errors=errors,
                                   boundary='descriptor-limit observation; memory/process exhaustion unqualified'))
    from host_execution_controls import clock_cases, credential_cases
    if args.clock_library:
        rows.extend(clock_cases(binary, providers, args.clock_library.resolve(), args.path))
    if args.controlled_identities:
        rows.extend(credential_cases(binary, helper, providers, args.path))
    result = dict(ticket='CSH-075', platform=platform.platform(), uname=list(os.uname()),
                  path=args.path, inventory=providers, enoexec_provider=identity('/bin/sh'),
                  binary=identity(binary), helper=identity(helper), source_identity=source_identity(),
                  scope='declared subset' if selected else 'all authored assertions (not whole-page qualification)',
                  selected=names, omitted=[r['id'] for r in cases(str(helper), Path('.'), 0) if r['id'] not in names],
                  uid=os.getuid(), euid=os.geteuid(), groups=os.getgroups(),
                  limits=dict(timeout_seconds=5, output_bytes=65536, argv_bytes=16 * 1024 * 1024),
                  loader_observations=loader,
                  capabilities=dict(virtual_clock=bool(args.clock_library), controlled_identities=args.controlled_identities),
                  cases=rows,
                  totals=dict(passed=sum(r['verdict'] == 'PASS' for r in rows), failed=sum(r['verdict'] != 'PASS' for r in rows)))
    query = ['dpkg-query', '-W', '-f=${Package} ${Version}\n'] if platform.system() == 'Linux' else ['sw_vers']
    result['package_environment'] = subprocess.check_output(query, text=True, timeout=5)
    if platform.system() == 'Darwin' and shutil.which('brew'):
        result['additional_packages'] = subprocess.run(['brew', 'list', '--versions', 'coreutils'], capture_output=True, text=True, timeout=10).stdout
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print('Result: ' + json.dumps(result['totals']))
    return int(bool(result['totals']['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
