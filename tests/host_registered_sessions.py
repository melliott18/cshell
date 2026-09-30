#!/usr/bin/env python3
"""Linux-only controlled session witnesses in an already private mount namespace.

Run with sudo unshare --mount --propagation private --fork. This script mounts a
private tmpfs on /run, NEVER writes a real login database, and sends only to its
own PTYs under dropped nobody credentials. It does not claim POSIX EOT/alerts.
"""
import argparse
import grp
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import socket
import subprocess
import tempfile
import time

from host_terminal import MODES, inventory
from host_terminal_effects import environment, invoke
from host_utilities import serial, sha, source_identity
from pty_harness import open_terminal


def isolation():
    if platform.system() != 'Linux' or os.geteuid() != 0:
        raise RuntimeError('requires Linux root in a private mount namespace')
    ours = os.readlink('/proc/self/ns/mnt')
    initial = os.readlink('/proc/1/ns/mnt')
    if ours == initial or Path('/var/run').resolve() != Path('/run'):
        raise RuntimeError('refusing shared mount namespace or nonstandard /var/run')
    # Fail closed unless every mount has private propagation, as requested by
    # unshare --propagation private; otherwise mounting /run could propagate.
    mounts = Path('/proc/self/mountinfo').read_text()
    if any(any(field.startswith(('shared:', 'master:')) for field in line.split(' - ')[0].split()[6:])
           for line in mounts.splitlines()):
        raise RuntimeError('mount propagation is not private')
    before = os.stat('/run').st_dev
    subprocess.run(['/bin/mount', '-t', 'tmpfs', '-o', 'mode=755,nosuid,nodev', 'csh077', '/run'],
                   check=True, capture_output=True, timeout=5)
    if os.stat('/run').st_dev == before:
        raise RuntimeError('private /run mount was not established')
    return dict(namespace=ours, initial_namespace=initial, run_device_before=before,
                run_device_private=os.stat('/run').st_dev, propagation='private')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--strict-eot', action='store_true', help='Require POSIX EOT and sender alerts; failing vendor audit is not waived')
    args = parser.parse_args()
    if os.getsid(0) != os.getpid():
        os.setsid()
    inputs = source_identity()
    providers, packages = inventory(args.path)
    rows, gaps, capabilities = [], [], {}
    directory = None
    mounted = False
    try:
        capabilities = isolation()
        mounted = True
        account = pwd.getpwnam('nobody')
        tty_group = grp.getgrnam('tty').gr_gid
        with tempfile.TemporaryDirectory(prefix='csh077-sessions-', dir='/tmp') as temp:
            directory = Path(temp)
            directory.chmod(0o755)
            binary = directory / 'cshell'
            shutil.copyfile(args.binary, binary)
            binary.chmod(0o755)
            private_bin = directory / 'bin'
            private_bin.mkdir(mode=0o755)
            selected_who = providers['who']['path']
            shutil.copyfile(selected_who, private_bin / 'who')
            (private_bin / 'who').chmod(0o755)
            providers['who'] = dict(providers['who'], selected_from=selected_who, path=str(private_bin / 'who'))
            env = environment(str(private_bin) + ':' + args.path, directory)
            for mode in MODES:
                for name in ('payload', 'denial', 'am-i', 'am-I'):
                    terminals = []
                    try:
                        # Index 0 is sender; index 1 is the sole recipient.
                        for _ in range(2):
                            terminals.append(open_terminal())
                        sender, recipient = [os.ttyname(t[1]).removeprefix('/dev/') for t in terminals]
                        for _, fd in terminals:
                            os.fchown(fd, account.pw_uid, tty_group)
                            os.fchmod(fd, 0o620)
                        records = directory / 'sessionsx'
                        records.write_bytes(b'')
                        subprocess.run([str(Path('build/tests/host_session_records').resolve()), str(records),
                                        sender, recipient, account.pw_name], check=True, capture_output=True, timeout=5)
                        shutil.copyfile(records, '/run/utmp')
                        os.chmod('/run/utmp', 0o644)
                        if name == 'denial':
                            os.fchmod(terminals[1][1], 0o600)
                        start = time.time()
                        if name.startswith('am-'):
                            actual = invoke(binary, providers, 'who', ['am', name[-1]], mode, directory, env,
                                            terminals, credentials=(account.pw_uid, tty_group))
                        else:
                            actual = invoke(binary, providers, 'write', [account.pw_name, recipient], mode,
                                            directory, env, terminals, credentials=(account.pw_uid, tty_group),
                                            terminal_input=b'CSH077 message\t\a\n\x04')
                        end = time.time()
                        failures = list(actual['failures'])
                        if name == 'denial':
                            if actual['status'] <= 0 or not actual['stderr'] or actual['stdout'] or actual['terminal1']:
                                failures.append('denied recipient accepted a message or lacked diagnostic')
                        elif name.startswith('am-'):
                            expected = [[account.pw_name.encode(), sender.encode(), b'Jan', b'1', b'00:00']]
                            if [line.split() for line in actual['stdout'].splitlines()] != expected or actual['status'] or actual['stderr'] or actual['terminal1']:
                                failures.append('who am i/I did not select owned sender session')
                        else:
                            # Pin the selected util-linux C-locale wire representation.
                            # This is data/greeting evidence, NOT a POSIX EOT/alert pass.
                            prefixes = [('\r\n\a\a\aMessage from ' + account.pw_name + '@' + socket.gethostname()
                                + ' on ' + sender + ' at ' + time.strftime('%H:%M', time.gmtime(t)) + ' ...\r\n').encode()
                                for t in (start, end)]
                            expected_bodies = [prefix + b'CSH077 message\t\a\r\nEOF\r\n' for prefix in prefixes]
                            if actual['terminal1'] not in expected_bodies or actual['status'] or actual['stdout'] or actual['stderr']:
                                failures.append('selected provider message bytes/status mismatch')
                            normative = []
                            if not actual['terminal1'].endswith(b'EOT\n'):
                                normative.append('write/POSIX-EOT')
                            if actual['terminal'].count(b'\a') != 2:
                                normative.append('write/two-sender-alerts')
                            gaps.extend(normative)
                            if args.strict_eot:
                                failures.extend(normative)
                        rows.append(dict(name='registered/' + name, mode=mode,
                                         verdict='FAIL' if failures else 'PASS', failures=failures, actual=actual,
                                         sender=sender, recipient=recipient, uid=account.pw_uid, gid=tty_group,
                                         credentials_method='setgroups([]), setgid, irreversible setuid before exec',
                                         record_sha256=sha(records)))
                        if failures:
                            print('FAIL:', name, mode, failures, flush=True)
                    finally:
                        for master, slave in terminals:
                            os.close(slave); os.close(master)
                        Path('/run/utmp').unlink(missing_ok=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        rows.append(dict(name='session-setup', verdict='FAIL', reason=str(error),
                         stdout=getattr(error, 'stdout', None), stderr=getattr(error, 'stderr', None)))
    finally:
        if mounted:
            try:
                subprocess.run(['/bin/umount', '/run'], check=True, capture_output=True, timeout=5)
                capabilities['private_mount_removed'] = True
            except subprocess.SubprocessError as error:
                rows.append(dict(name='mount-cleanup', verdict='FAIL', reason=str(error)))
    if source_identity() != inputs:
        rows.append(dict(name='source-stability', verdict='FAIL', reason='source changed during run'))
    report = dict(platform=platform.platform(), command=os.sys.argv, path=args.path,
                  providers=providers, packages=packages, source_identity=inputs, capabilities=capabilities,
                  binary_sha256=sha(args.binary), strict_eot=args.strict_eot,
                  qualification='selected data/denial/current-session subset only',
                  unqualified_conditions=sorted(set(gaps)), residual_owner='CSH-081', cases=rows,
                  fixture_directory_removed=directory is None or not directory.exists(),
                  totals=dict(passed=sum(r['verdict']=='PASS' for r in rows), failed=sum(r['verdict']=='FAIL' for r in rows)))
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(serial(report), indent=2) + '\n')
    print(json.dumps(report['totals']))
    return int(bool(report['totals']['failed']) or not rows or not report['fixture_directory_removed'])


if __name__ == '__main__':
    raise SystemExit(main())
