"""Keep the vendor compiled-database encoding separate from POSIX text aliases.

-C is a vendor extension. This regression protects the bundled database build;
it does not qualify compilation as a POSIX interface.
"""
import ctypes
import hashlib
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile

import smoke


def main():
    binary = Path(sys.argv[1]).resolve()
    records = []
    with tempfile.TemporaryDirectory(prefix='csh-file-types-') as directory:
        root = Path(directory)
        magic = b'0\tstring\tCSH105\tfixture\n>6\tlong\tx\tmatched\n'
        (root / 'magic').write_bytes(magic)

        def run(name, args, expected):
            for name in ('.home', '.tmp'):
                if (root / name).exists():
                    shutil.rmtree(root / name)
            status, channels, errors = smoke.capture(
                binary, dict(args=args, stdin=b'', env=dict(LC_ALL='C', TZ='UTC0', PATH=os.defpath)),
                root, 5, 65536)
            passed = (status == 0 and channels == dict(stdout=expected, stderr=b'') and
                      not errors and (root / 'magic').read_bytes() == magic)
            records.append(dict(name=name, args=args, status=status,
                                stdout_hex=channels['stdout'].hex(), stderr_hex=channels['stderr'].hex(),
                                errors=errors, passed=bool(passed)))

        run('compile-vendor-format', ['-C', '-m', 'magic'], b'')
        for length in sorted({4, ctypes.sizeof(ctypes.c_long)}):
            sample = b'CSH105' + bytes(length)
            (root / 'sample').write_bytes(sample)
            for spelling in ('magic', 'magic.mgc'):
                # libmagic auto-loads magic.mgc when asked for magic. Use a
                # different basename to force the native textual code path.
                (root / 'text').write_bytes(magic)
                selected = 'text' if spelling == 'magic' else spelling
                width = ctypes.sizeof(ctypes.c_long) if selected == 'text' else 4
                expected = b'sample: fixture' + (b' matched' if length >= width else b'') + b'\n'
                run(selected + '-' + str(length), ['-m', selected, 'sample'], expected)
                records[-1]['passed'] &= (root / 'sample').read_bytes() == sample
    for row in records:
        row['cleanup'] = not root.exists()
    result = dict(binary=str(binary), sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  c_long_bytes=ctypes.sizeof(ctypes.c_long), cases=records,
                  passed=sum(r['passed'] and r['cleanup'] for r in records))
    print(json.dumps(result, indent=2))
    return int(result['passed'] != len(records))


if __name__ == '__main__':
    raise SystemExit(main())
