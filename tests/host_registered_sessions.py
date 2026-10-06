#!/usr/bin/env python3
"""Linux-only controlled session witnesses in an already private mount namespace.

Run with sudo unshare --mount --propagation private --fork. This script mounts a
private tmpfs on /run, NEVER writes a real login database, and sends only to its
own PTYs under dropped nobody credentials. Profile EOT/alerts are strict.
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
import signal
import subprocess
import tempfile
import termios
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
    parser.add_argument('--write-policy', choices=('profile', 'vendor'), default='profile',
                        help='Strict repaired profile, or explicitly retained historical vendor representation')
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
            private_bin.chmod(0o755)
            for utility in ('who', 'write', 'mesg'):
                selected = providers[utility]['path']
                shutil.copyfile(selected, private_bin / utility)
                (private_bin / utility).chmod(0o755)
                providers[utility] = dict(providers[utility], selected_from=selected,
                    path=str(private_bin / utility), realpath=str((private_bin / utility).resolve()),
                    sha256=sha(private_bin / utility))
            env = environment(str(private_bin) + ':' + args.path, directory)
            for mode in MODES:
                names = ['payload', 'denial', 'am-i', 'am-I']
                if args.write_policy == 'profile':
                    names += ['partial-eof', 'editing', 'controls', 'implicit', 'not-logged-in']
                    names += ['interrupt', 'terminate', 'utf8', 'ctype-precedence',
                              'lang-fallback', 'iexten-off', 'iexten-on', 'invalid-utf8', 'recipient-other-owner',
                              'recipient-wrong-group', 'sender-denial', 'mesg-not-owner']
                for name in names:
                    terminals = []
                    try:
                        # Index 0 is sender; index 1 is the sole recipient.
                        for _ in range(2):
                            terminals.append(open_terminal())
                        sender, recipient = [os.ttyname(t[1]).removeprefix('/dev/') for t in terminals]
                        for _, fd in terminals:
                            os.fchown(fd, account.pw_uid, tty_group)
                            os.fchmod(fd, 0o620)
                            attrs = termios.tcgetattr(fd)
                            attrs[6][termios.VERASE] = b'\x7f'
                            attrs[6][termios.VKILL] = b'\x15'
                            termios.tcsetattr(fd, termios.TCSANOW, attrs)
                        records = directory / 'sessionsx'
                        records.write_bytes(b'')
                        subprocess.run([str(Path('build/tests/host_session_records').resolve()), str(records),
                                        sender, recipient, account.pw_name], check=True, capture_output=True, timeout=5)
                        shutil.copyfile(records, '/run/utmp')
                        os.chmod('/run/utmp', 0o644)
                        if name == 'denial':
                            os.fchmod(terminals[1][1], 0o600)
                        if name == 'sender-denial':
                            os.fchmod(terminals[0][1], 0o600)
                        if name in ('recipient-other-owner', 'recipient-wrong-group'):
                            os.fchown(terminals[1][1], pwd.getpwnam('daemon').pw_uid, tty_group)
                        if name == 'mesg-not-owner':
                            os.fchown(terminals[0][1], 0, tty_group)
                            os.fchmod(terminals[0][1], 0o660)
                        if name == 'iexten-off':
                            attrs = termios.tcgetattr(terminals[0][1])
                            attrs[3] &= ~termios.IEXTEN
                            termios.tcsetattr(terminals[0][1], termios.TCSANOW, attrs)
                        if name == 'iexten-on':
                            attrs = termios.tcgetattr(terminals[0][1])
                            attrs[3] |= termios.IEXTEN
                            attrs[6][termios.VLNEXT] = b'\x16'
                            termios.tcsetattr(terminals[0][1], termios.TCSANOW, attrs)
                        case_env = dict(env)
                        if name in ('utf8', 'ctype-precedence', 'lang-fallback', 'invalid-utf8'):
                            case_env.update(LC_ALL='', LANG='en_US.UTF-8')
                            if name != 'lang-fallback':
                                case_env.update(LANG='C', LC_CTYPE='en_US.UTF-8')
                            case_env['LC_MESSAGES'] = 'C'
                        payloads = {
                            'payload': (b'CSH077 message\t\a\n\x04', b'CSH077 message\t\a\n'),
                            'partial-eof': (b'partial\x04\x04', b'partial'),
                            'editing': (b'old\x15ab\x7fc\n\x04', b'ac\n'),
                            'controls': (b'\x01\x00\v\f\t\a\n\x04', b'<0x1><0x0>\v\f\t\a\n'),
                            'implicit': (b'implicit\n\x04', b'implicit\n'),
                            'interrupt': (b'', b''),
                            'terminate': (b'', b''),
                            'utf8': ('café 日本\n\x04'.encode(), 'café 日本\n'.encode()),
                            'ctype-precedence': ('é\n\x04'.encode(), 'é\n'.encode()),
                            'lang-fallback': ('é\n\x04'.encode(), 'é\n'.encode()),
                            'iexten-off': (b'\x16x\n\x04', b'<0x16>x\n'),
                            'iexten-on': (b'\x16\x03\n\x04', b'<0x3>\n'),
                            'invalid-utf8': (b'\xff\n\x04', b''),
                            'recipient-other-owner': (b'other owner\n\x04', b'other owner\n'),
                        }
                        start = time.time()
                        if name == 'mesg-not-owner':
                            actual = invoke(binary, providers, 'mesg', ['n'], mode, directory, case_env,
                                            terminals, credentials=(account.pw_uid, tty_group))
                        elif name.startswith('am-'):
                            actual = invoke(binary, providers, 'who', ['am', name[-1]], mode, directory, env,
                                            terminals, credentials=(account.pw_uid, tty_group))
                        else:
                            operands = [account.pw_name] if name == 'implicit' else [account.pw_name, recipient]
                            if name == 'not-logged-in':
                                operands[0] = 'csh077-no-such-user'
                            extra = {}
                            if name in ('interrupt', 'terminate'):
                                extra = dict(signal_on_terminal=(b'\a\a', signal.SIGINT if name == 'interrupt' else signal.SIGTERM),
                                             signal_executable=providers['write']['path'])
                            actual = invoke(binary, providers, 'write', operands, mode,
                                            directory, case_env, terminals, credentials=(account.pw_uid, account.pw_gid if name == 'recipient-wrong-group' else tty_group),
                                            terminal_input=payloads.get(name, payloads['payload'])[0], **extra)
                        end = time.time()
                        failures = list(actual['failures'])
                        if name == 'mesg-not-owner':
                            if (actual['status'] <= 1 or not actual['stderr'] or actual['stdout'] or
                                    actual['terminal1'] or actual['terminal'] or
                                    os.fstat(terminals[0][1]).st_mode & 0o777 != 0o660):
                                failures.append('mesg permission failure contract')
                        elif name in ('denial', 'not-logged-in', 'recipient-wrong-group', 'sender-denial'):
                            if actual['status'] <= 0 or not actual['stderr'] or actual['stdout'] or actual['terminal1'] or actual['terminal']:
                                failures.append('denied recipient accepted a message or lacked diagnostic')
                        elif name.startswith('am-'):
                            expected = [[account.pw_name.encode(), sender.encode(), b'Jan', b'1', b'00:00']]
                            if [line.split() for line in actual['stdout'].splitlines()] != expected or actual['status'] or actual['stderr'] or actual['terminal1']:
                                failures.append('who am i/I did not select owned sender session')
                        else:
                            if args.write_policy == 'profile':
                                prefixes = [('Message from ' + account.pw_name + ' (' + sender + ') ['
                                    + time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t)) + '] ...\n').encode()
                                    for t in range(int(start), int(end) + 1)]
                                expected_bodies = [prefix + payloads[name][1] + b'EOT\n' for prefix in prefixes]
                                stdout = ((account.pw_name + ' is logged in more than once; writing to '
                                           + recipient + '\n').encode() if name == 'implicit' else b'')
                            else:
                                prefixes = [('\r\n\a\a\aMessage from ' + account.pw_name + '@' + socket.gethostname()
                                    + ' on ' + sender + ' at ' + time.strftime('%H:%M', time.gmtime(t)) + ' ...\r\n').encode()
                                    for t in (start, end)]
                                expected_bodies = [prefix + b'CSH077 message\t\a\r\nEOF\r\n' for prefix in prefixes]
                                stdout = b''
                            status = 0
                            if name == 'terminate':
                                status = -signal.SIGTERM if mode in ('direct', 'exec') else 128 + signal.SIGTERM
                                expected_bodies = prefixes
                            error_output = bool(actual['stderr'])
                            if name == 'invalid-utf8':
                                expected_bodies = prefixes
                                status = 1
                                error_output = not actual['stderr']
                            if actual['terminal1'] not in expected_bodies or actual['status'] != status or actual['stdout'] != stdout or error_output:
                                failures.append('message bytes/status mismatch')
                            normative = []
                            if name not in ('terminate', 'invalid-utf8') and not actual['terminal1'].endswith(b'EOT\n'):
                                normative.append('write/POSIX-EOT')
                            if actual['terminal'] != b'\a\a':
                                normative.append('write/two-sender-alerts')
                            gaps.extend(normative)
                            if args.strict_eot or args.write_policy == 'profile':
                                failures.extend(normative)
                        rows.append(dict(name='registered/' + name, mode=mode,
                                         verdict='FAIL' if failures else 'PASS', failures=failures, actual=actual,
                                         sender=sender, recipient=recipient, uid=account.pw_uid, gid=tty_group,
                                         credentials_method='setgroups([]), setgid, setuid; verified real/effective/saved IDs and empty groups before exec',
                                         environment=case_env,
                                         termios_sender=termios.tcgetattr(terminals[0][1]),
                                         recipient_owner=os.fstat(terminals[1][1]).st_uid,
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
                  binary_sha256=sha(args.binary), strict_eot=args.strict_eot, write_policy=args.write_policy,
                  qualification='strict selected session subset; not complete page qualification',
                  unqualified_conditions=sorted(set(gaps)), residual_owner='CSH-081', cases=rows,
                  fixture_directory_removed=directory is None or not directory.exists(),
                  totals=dict(passed=sum(r['verdict']=='PASS' for r in rows), failed=sum(r['verdict']=='FAIL' for r in rows)))
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(serial(report), indent=2) + '\n')
    print(json.dumps(report['totals']))
    return int(bool(report['totals']['failed']) or not rows or not report['fixture_directory_removed'])


if __name__ == '__main__':
    raise SystemExit(main())
