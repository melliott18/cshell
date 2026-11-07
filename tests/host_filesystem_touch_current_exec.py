#!/usr/bin/env python3
"""Prove a child-only file creation mask, then exec the exact touch provider."""
import json
import os
from pathlib import Path
import stat
import sys


def main():
    marker = Path('.touch-current-exec.json')
    record = dict(phase='setup', uid=os.getuid(), euid=os.geteuid())
    # Create a readable marker before applying even the all-bits mask.
    marker.write_text('{}\n')
    marker.chmod(0o600)
    try:
        mask_text, provider, *arguments = sys.argv[1:]
        mask = int(mask_text, 8)
        if mask not in (0o027, 0o077, 0o777) or os.getuid() != os.geteuid() or os.geteuid() == 0:
            raise ValueError('authored mask and one unprivileged identity required')
        os.umask(mask)
        record.update(provider=provider, requested_mask=mask, observed_mask=os.umask(mask))
        descriptor = os.open('.touch-create-probe', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            record['probe_mode'] = stat.S_IMODE(os.fstat(descriptor).st_mode)
        finally:
            os.close(descriptor)
            os.unlink('.touch-create-probe')
        if (record['observed_mask'], record['probe_mode']) != (mask, 0o666 & ~mask):
            raise ValueError('creation mask probe mismatch (possible inherited ACL)')
        record['phase'] = 'exec'
        marker.write_text(json.dumps(record) + '\n')
        try:
            os.execv(provider, [provider, *arguments])
        except OSError as error:
            record.update(phase='exec-error', errno=error.errno)
    except (OSError, ValueError) as error:
        record.update(phase='setup-error', error=str(error))
    marker.write_text(json.dumps(record) + '\n')
    return 125


if __name__ == '__main__':
    raise SystemExit(main())
