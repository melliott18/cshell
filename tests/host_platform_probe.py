#!/usr/bin/env python3
"""Strict socket/chmod diagnosis on an explicitly supplied disposable Linux root.

This supplements host_utilities.py; it never qualifies a complete host profile.
"""
import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import platform
import socket
import signal
import stat
import subprocess
import sys
import tempfile
import time

from host_capability_limits import BASE
from host_platform import credential_namespace, filesystem_identity
from host_utilities import inventory, serial, sha, source_identity


def metadata(path):
    value = Path(path).stat()
    return dict(uid=value.st_uid, gid=value.st_gid, mode=oct(value.st_mode),
                socket=stat.S_ISSOCK(value.st_mode), device=value.st_dev,
                inode=value.st_ino)


def credentials():
    status = Path('/proc/self/status').read_text().splitlines()
    return dict(uid=os.getuid(), euid=os.geteuid(), gid=os.getgid(),
                egid=os.getegid(), groups=os.getgroups(),
                capabilities={line.split(':')[0]: line.split(':')[1].strip()
                              for line in status if line.startswith('Cap')},
                namespace=credential_namespace())


def command(argv):
    """One Linux watchdog owns the wrapper and its inherited process group.

    Subreaping lets this single-threaded runner wait for adopted grandchildren,
    instead of leaving them to container init after killing the wrapper. Waits
    target only this invocation's group, never unrelated children of the runner.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:  # PR_GET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'get child subreaper')
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'enable child subreaper')
    process = None
    output, errors = b'', b''
    status, timed_out = None, False
    cleanup_errors = []
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, start_new_session=True,
                                   env={'PATH': os.defpath, 'LC_ALL': 'C'})
        try:
            output, errors = process.communicate(timeout=5)
            status = process.returncode
        except subprocess.TimeoutExpired as error:
            timed_out = True
            output, errors = error.stdout or b'', error.stderr or b''
    finally:
        try:
            if process is not None:
                deadline = time.monotonic() + 2
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=max(0, deadline - time.monotonic()))
                # The wrapper has exited, so its descendants are now adopted.
                while True:
                    try:
                        pid, _ = os.waitpid(-process.pid, os.WNOHANG)
                    except ChildProcessError:
                        break
                    if not pid:
                        if time.monotonic() >= deadline:
                            raise TimeoutError('could not reap probe descendants within 2s')
                        time.sleep(0.01)
        except (OSError, subprocess.SubprocessError) as error:
            cleanup_errors.append(str(error))
        finally:
            if process is not None:
                process.stdout.close()
                process.stderr.close()
            if libc.prctl(36, previous.value, 0, 0, 0) != 0:
                cleanup_errors.append('restore child subreaper: ' + os.strerror(ctypes.get_errno()))
    result = dict(argv=argv, status=None if cleanup_errors else status,
                  stdout=output, stderr=errors)
    if timed_out:
        result['timeout_seconds'] = 5
    if cleanup_errors:
        result['cleanup_errors'] = cleanup_errors
    return serial(result)


def chmod_child(uid, target, utility):
    # Saved IDs are dropped as well. Real host accounts are never changed.
    os.setgroups([])
    os.setresgid(uid, uid, uid)
    os.setresuid(uid, uid, uid)
    result = dict(credentials=credentials(), before=metadata(target))
    if utility == 'syscall':
        try:
            os.chmod(target, 0o600)
            result['errno'] = 0
        except OSError as error:
            result['errno'] = error.errno
            result['diagnostic'] = str(error)
    else:
        # Inherit the outer watchdog's group and deadline. A second watchdog
        # here would race the privileged parent and orphan the selected utility.
        completed = subprocess.run([utility, '600', target], capture_output=True)
        result['utility'] = serial(dict(argv=[utility, '600', target],
                                        status=completed.returncode,
                                        stdout=completed.stdout, stderr=completed.stderr))
    result['after'] = metadata(target)
    print(json.dumps(result))


def chmod_matches(actual, uid, method):
    """Require measured identity, denial errno/status, and unchanged denied mode."""
    identity = actual['credentials']
    if (any(identity[key] != uid for key in ('uid', 'euid', 'gid', 'egid')) or
            identity['groups'] or int(identity['capabilities']['CapEff'], 16) != 0):
        return False
    if method == 'syscall':
        correct_status = actual['errno'] == (0 if uid == 10001 else errno.EPERM)
    else:
        utility = actual['utility']
        correct_status = (utility['status'] == (0 if uid == 10001 else 1) and
                          utility['stdout'] == {'hex': ''} and
                          bool(utility['stderr']['hex']) == (uid != 10001))
    return (correct_status and actual['before']['mode'] == oct(stat.S_IFREG | 0o400) and
            actual['after']['mode'] == oct(stat.S_IFREG | (0o600 if uid == 10001 else 0o400)) and
            all(actual[phase]['uid'] == 10001 and actual[phase]['gid'] == 10002
                for phase in ('before', 'after')))


def probe(root, search_path):
    tools = inventory(search_path)
    rows = []
    record = dict(platform=platform.platform(), filesystem=filesystem_identity(root),
                  credentials=credentials(), source_identity=source_identity(),
                  inventory=tools, python=dict(path=sys.executable, sha256=sha(sys.executable),
                                               version=sys.version),
                  limits=dict(timeout_seconds=5, socket_payload_bytes=1), cases=rows)

    def check(name, ok, actual, utility, expectation, phase='assertion'):
        rows.append(dict(name=name, verdict='PASS' if ok else 'FAIL', phase=phase,
                         expected=expectation, actual=actual, source=BASE + utility + '.html',
                         owner='CSH-064', implementation_owner='selected utility/libc/platform vendor',
                         executable=tools[utility]))

    with tempfile.TemporaryDirectory(prefix='csh-platform-', dir=root) as temporary:
        directory = Path(temporary)
        directory.chmod(0o755)
        previous = Path.cwd()
        try:
            os.chdir(directory)
            try:
                with socket.socket(socket.AF_UNIX) as server, socket.socket(socket.AF_UNIX) as client:
                    server.settimeout(5)
                    client.settimeout(5)
                    server.bind('socket')
                    try:
                        observed = metadata('socket')
                        check('socket stat type', observed['socket'], observed, 'test', 'S_ISSOCK')
                    except OSError as error:
                        check('socket stat type', False, dict(errno=error.errno, reason=str(error)),
                              'test', 'stat succeeds with S_ISSOCK')
                    for utility in ('test', '['):
                        argv = [tools[utility]['path'], '-S', 'socket'] + ([']'] if utility == '[' else [])
                        actual = command(argv)
                        check('socket predicate ' + utility,
                              actual['status'] == 0 and actual['stdout'] == {'hex': ''} and
                              actual['stderr'] == {'hex': ''}, actual, utility, 'status 0, empty output')
                    server.listen(1)
                    client.connect('socket')
                    with server.accept()[0] as peer:
                        peer.settimeout(5)
                        client.sendall(b'x')
                        payload = peer.recv(1)
                    check('socket actual transfer', payload == b'x', serial(payload), 'test', 'one byte x')
            except OSError as error:
                check('socket setup/transfer', False, dict(errno=error.errno, reason=str(error)),
                      'test', 'bind/listen/connect/accept/transfer succeeds', 'setup')
            for method in ('syscall', 'utility'):
                for uid in (10001, 10002):
                    target = directory / f'chmod-{method}-{uid}'
                    try:
                        target.write_bytes(b'private\n')
                        os.chown(target, 10001, 10002)
                        target.chmod(0o400)
                        before = metadata(target)
                        if (before['uid'], before['gid'], before['mode']) != (10001, 10002, oct(stat.S_IFREG | 0o400)):
                            raise OSError(errno.EINVAL, 'unexpected fixture metadata: ' + repr(before))
                    except OSError as error:
                        check(f'chmod {method} uid={uid}', False,
                              dict(errno=error.errno, reason=str(error)), 'chmod', 'owner=10001:10002 mode=0400', 'setup')
                        continue
                    actual = command([sys.executable, str(Path(__file__).resolve()), '_chmod-child',
                                      str(uid), str(target), 'syscall' if method == 'syscall' else tools['chmod']['path']])
                    try:
                        child = json.loads(bytes.fromhex(actual['stdout']['hex']))
                        ok = actual['status'] == 0 and actual['stderr'] == {'hex': ''} and chmod_matches(child, uid, method)
                        actual['child'] = child
                    except (ValueError, KeyError, TypeError):
                        ok = False
                    actual['parent_before'] = before
                    actual['parent_after'] = metadata(target)
                    check(f'chmod {method} uid={uid}', ok, actual, 'chmod',
                          'owner succeeds and sets 0600; non-owner denied and retains 0400; IDs/groups/capabilities measured')
        finally:
            os.chdir(previous)
    record['totals'] = dict(passed=sum(row['verdict'] == 'PASS' for row in rows),
                            failed=sum(row['verdict'] == 'FAIL' for row in rows))
    return record


def main():
    if len(sys.argv) == 5 and sys.argv[1] == '_chmod-child':
        chmod_child(int(sys.argv[2]), sys.argv[3], sys.argv[4])
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        parser.error('requires disposable Linux root; never use a real user/account fixture')
    result = probe(args.fixture_root.resolve(), args.path)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))
    return int(bool(result['totals']['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
