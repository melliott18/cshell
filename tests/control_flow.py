#!/usr/bin/env python3
"""Run control-flow API allocation sweeps with bounded cleanup."""
from pathlib import Path
import sys
import tempfile
from execute import bounded_run

with tempfile.TemporaryDirectory(prefix='cshell-control-') as temporary:
    result = bounded_run([str(Path(sys.argv[1]).resolve()), '--control'],
                         cwd=temporary, env=None, timeout=30)
    assert result.returncode == 0, result
    assert result.stdout == b'control flow fault checks passed\n', result
    assert all(line.startswith(b'cshell: ') for line in result.stderr.splitlines()), result
print('control flow API and allocation checks passed')
