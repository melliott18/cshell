"""Regression checks for the selected libmagic format validator.

Malformed descriptions are outside the positive POSIX qualification set. These
checks ensure that the local %%/flag repair still rejects extra arguments,
wrong types, writes through pointers and oversized numeric formats.
"""
import json
import os
from pathlib import Path
import sys
import tempfile

import smoke


def main():
    binary = Path(sys.argv[1]).resolve()
    records = []
    for kind in ('byte', 'short'):
        for message in ('%n', '%d %d', '%%:%d:%d', '%2048d', '%.2048d', '%s', '%'):
            with tempfile.TemporaryDirectory(prefix='csh-file-format-') as directory:
                root = Path(directory)
                sample = (42).to_bytes(1 if kind == 'byte' else 2, sys.byteorder) + b'trailing'
                magic = ('0\t' + kind + '\t=42\t[' + message + ']\n').encode()
                (root / 'sample').write_bytes(sample)
                (root / 'magic').write_bytes(magic)
                status, channels, errors = smoke.capture(
                    binary, {'args': ['-m', 'magic', 'sample'], 'stdin': b''}, root, 5, 65536)
                valid = (status > 0 and channels['stdout'] == b'' and channels['stderr']
                         and not errors and (root / 'sample').read_bytes() == sample
                         and (root / 'magic').read_bytes() == magic)
                records.append(dict(kind=kind, message=message, status=status,
                                    stdout_hex=channels['stdout'].hex(),
                                    stderr_hex=channels['stderr'].hex(), errors=errors,
                                    passed=bool(valid)))
            records[-1]['cleanup'] = not root.exists()
    result = dict(binary=str(binary), cases=records,
                  passed=sum(r['passed'] and r['cleanup'] for r in records))
    print(json.dumps(result, indent=2))
    return int(result['passed'] != len(records))


if __name__ == '__main__':
    raise SystemExit(main())
