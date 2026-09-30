#!/usr/bin/env python3
"""Arm a child-only kernel fault, independently probe its errno, then exec.

The marker makes loader/setup failures distinct from an exercised I/O contract.
No mounting, disk filling, account changes, or process-wide parent limits.
"""
import errno
import json
import os
import signal
import stat
import sys

MARKER = '.io-fault.json'


def save(record):
    with open(MARKER, 'w') as output:
        json.dump(record, output)


def main():
    action, provider, *arguments = sys.argv[1:]
    record = dict(action=action, provider=provider, phase='setup', pid=os.getpid())
    try:
        if action == 'broken-pipe':
            reader, writer = os.pipe()
            os.close(reader)
            os.dup2(writer, 1)
            os.close(writer)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            probe = lambda: os.write(1, b'x')
            expected = errno.EPIPE
        elif action == 'closed-input':
            os.close(0)
            probe = lambda: os.read(0, 1)
            expected = errno.EBADF
        elif action == 'closed-output':
            os.close(1)
            probe = lambda: os.write(1, b'x')
            expected = errno.EBADF
        elif action == 'file-size':
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            fd = os.open('.io-probe', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(fd, b'x' * 512)
                probe = lambda: os.write(fd, b'x')
                expected = errno.EFBIG
                try:
                    probe()
                except OSError as error:
                    record['errno'] = error.errno
                else:
                    raise RuntimeError('file-size probe unexpectedly succeeded')
            finally:
                os.close(fd)
                os.unlink('.io-probe')
        elif action == 'enospc':
            if sys.platform != 'linux':
                raise RuntimeError('virtual full device is a Linux capability')
            fd = os.open('/dev/full', os.O_WRONLY | os.O_NOFOLLOW)
            info = os.fstat(fd)
            if not stat.S_ISCHR(info.st_mode) or (os.major(info.st_rdev), os.minor(info.st_rdev)) != (1, 7):
                os.close(fd)
                raise RuntimeError('not the Linux virtual full character device')
            record['device'] = dict(path='/dev/full', major=1, minor=7)
            os.dup2(fd, 1)
            os.close(fd)
            probe = lambda: os.write(1, b'x')
            expected = errno.ENOSPC
        else:
            raise ValueError('unknown I/O fault action')
        if action != 'file-size':
            try:
                probe()
            except OSError as error:
                record['errno'] = error.errno
            else:
                raise RuntimeError('kernel error probe unexpectedly succeeded')
        if record['errno'] != expected:
            raise RuntimeError('kernel probe returned wrong errno')
        record['phase'] = 'armed'
        save(record)
        try:
            os.execv(provider, [provider, *arguments])
        except OSError as error:
            record.update(phase='exec-failure', exec_errno=error.errno)
            save(record)
            return 125
    except (OSError, ValueError, RuntimeError) as error:
        record.update(phase='setup-failure', error=str(error))
        save(record)
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
