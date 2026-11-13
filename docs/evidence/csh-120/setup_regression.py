"""Prove cleanup after a fault inside the new graph, beyond generic setup.

Patching os.symlink unconditionally also affects the common fixture builder.
This witness lets common setup and the first recursive alias succeed, then
fails the second alias after independently observing the partially built tree.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem import run_case
from host_filesystem_ls_recursive import cases, DIRECTORIES, FILES


def main():
    records = []
    real_symlink = os.symlink
    for mode in ('direct', 'string', 'file', 'stdin'):
        observed = []
        def fail_second_alias(target, link, *args, **kwargs):
            link = Path(link)
            if link.name == '.hidden-alias' and link.parent.name == 'tree' and link.parent.parent.name == 'recursion':
                root = link.parent.parent
                assert all((root / name).is_dir() for name in DIRECTORIES)
                assert all((root / name).read_bytes() == data for name, data in FILES.items())
                assert os.readlink(root / 'tree/alias') == 'visible'
                observed.append('complete directories/files and first alias; second alias absent')
                raise OSError('injected CSH-120 second-alias setup failure')
            return real_symlink(target, link, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temporary, \
                patch('os.symlink', side_effect=fail_second_alias), \
                patch('host_filesystem.smoke.capture') as capture:
            root = Path(temporary)
            record = run_case(Path('/bin/sh'), {'ls': {'path': '/bin/ls'}},
                              os.defpath, next(cases()), mode, root, None)
            assert observed and len(observed) == 1, observed
            capture.assert_not_called()
            assert record['phase'] == 'setup' and record['verdict'] == 'FAIL', record
            assert record['error'] == 'injected CSH-120 second-alias setup failure', record
            assert record['cleanup'] and not list(root.iterdir()), record
            records.append(dict(mode=mode, partial_setup=observed[0], record=record))
    print(json.dumps(dict(passed=4, failed=0, uid=os.getuid(), cases=records), indent=2))


if __name__ == '__main__':
    main()
