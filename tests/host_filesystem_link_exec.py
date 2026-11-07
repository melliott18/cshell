#!/usr/bin/env python3
"""Record failure to exec the exact ln provider, separately from utility errors."""
import json
import os
from pathlib import Path
import sys


def main():
    marker = Path('.link-exec.json')
    record = dict(phase='exec', provider=sys.argv[1], uid=os.getuid(), euid=os.geteuid())
    marker.write_text(json.dumps(record) + '\n')
    try:
        os.execv(sys.argv[1], sys.argv[1:])
    except OSError as error:
        record.update(phase='exec-error', errno=error.errno)
        marker.write_text(json.dumps(record) + '\n')
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
