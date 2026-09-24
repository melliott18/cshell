#!/usr/bin/env python3
"""Bound lifecycle/fault fixtures and clean up every descendant on failure."""
import argparse
import os
from pathlib import Path
import tempfile
from execute import bounded_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('api_binary')
    parser.add_argument('fault_binary')
    args = parser.parse_args()
    api, faults = (str(Path(path).resolve()) for path in (args.api_binary, args.fault_binary))
    with tempfile.TemporaryDirectory(prefix='cshell-substitution-') as cwd:
        for command, output in (
            ([api], b'substitution ownership checks passed\n'),
            ([faults, '--substitution'], b'substitution fault checks passed\n'),
        ):
            result = bounded_run(command, cwd=Path(cwd), env=dict(os.environ, LC_ALL='C'), timeout=20)
            assert result.returncode == 0 and result.stdout == output, result
            print(output.decode(), end='')


if __name__ == '__main__':
    main()
