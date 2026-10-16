#!/usr/bin/env python3
"""Set a child-only umask, prove real creation modes, then exec the provider."""
import json
import os
import stat
import sys

MARKER = '.creation-environment.json'


def main():
    record = dict(phase='setup', pid=os.getpid(), uid=os.getuid(), euid=os.geteuid())
    def save():
        with open(MARKER, 'w') as stream:
            json.dump(record, stream)
    try:
        mask_text, provider, *arguments = sys.argv[1:]
        mask = int(mask_text, 8)
        if mask not in (0o027, 0o077, 0o777) or os.geteuid() == 0:
            raise ValueError('unprivileged identity and authored mask required')
        record.update(provider=provider, requested_mask=mask)
        os.umask(mask)
        record['observed_mask'] = os.umask(mask)
        os.mkdir('.creation-probe-dir', 0o777)
        os.mkfifo('.creation-probe-fifo', 0o666)
        record['directory_mode'] = stat.S_IMODE(os.stat('.creation-probe-dir').st_mode)
        record['fifo_mode'] = stat.S_IMODE(os.stat('.creation-probe-fifo').st_mode)
        if (record['observed_mask'], record['directory_mode'], record['fifo_mode']) != (
                mask, 0o777 & ~mask, 0o666 & ~mask):
            raise RuntimeError('creation mask probe mismatch (possible inherited ACL)')
        os.rmdir('.creation-probe-dir')
        os.unlink('.creation-probe-fifo')
        record['phase'] = 'armed'
        # Ensure the marker remains readable even with umask 0777. This explicit
        # chmod changes only the marker, never the provider's creation mask.
        fd = os.open(MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        save()
        try:
            os.execv(provider, [provider, *arguments])
        except OSError as error:
            record.update(phase='exec-failure', exec_errno=error.errno)
            save()
            return 125
    except (OSError, ValueError, RuntimeError) as error:
        record.update(phase='setup-failure', error=str(error))
        # A failure before marker creation may occur under the restrictive mask.
        os.umask(0o077)
        save()
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
