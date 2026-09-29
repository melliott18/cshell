#!/usr/bin/env python3
"""File-backed direct exec adapter; no transformations or status translation."""
import os
import sys

if __name__ == '__main__':
    input_name, output_name, executable, *args = sys.argv[1:]
    source = os.open(input_name, os.O_RDONLY)
    os.dup2(source, 0)
    if source != 0:
        os.close(source)
    if output_name != '-':
        output = os.open(output_name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.dup2(output, 1)
        if output != 1:
            os.close(output)
    os.execv(executable, [executable] + args)
