#!/usr/bin/env python3
"""CSH-048 predicates for nondeterministic times/limits and reusable listings.

All processes use smoke.capture's resource limits, output bound, deadline and
process-group cleanup. No resource limit in the test runner itself is mutated.
"""
import argparse
from pathlib import Path
import re
import shlex
import tempfile

import smoke


def observations(helper):
    def exact(value):
        return lambda output: output == value

    def times(output):
        rows = re.findall(rb'(\d+)m(\d+\.\d{6})s', output)
        if len(rows) != 8 or not re.fullmatch(
                rb'(?:\d+m\d+\.\d{6}s \d+m\d+\.\d{6}s\n){4}', output):
            return False
        values = [int(m) * 60 + float(s) for m, s in rows]
        return (all(0 <= float(s) < 60 for _, s in rows)
                and all(values[i + 4] >= values[i] for i in range(4))
                and sum(values[6:8]) - sum(values[2:4]) >= 0.1)

    yield ('times format and accumulated children', f'times; {helper} cpu; times', times)
    yield ('set C locale order and quoting',
           "Zvar=last; Avar=\"a'b\"; Mvar=; set >vars; "
           "while IFS= read -r line; do case $line in Avar=*|Mvar=*|Zvar=*) printf '%s\\n' \"$line\";; esac; done <vars",
           exact(b"Avar='a'\\''b'\nMvar=''\nZvar='last'\n"))
    for resource in 'cdfnsv':
        yield ('ulimit query ' + resource, f'ulimit -S -{resource}; ulimit -H -{resource}',
               lambda out: bool(re.fullmatch(rb'(?:[0-9]+|unlimited)\n(?:[0-9]+|unlimited)\n', out)))
    yield ('ulimit default and inherited units',
           f'ulimit 128; ulimit; ulimit -S -f; ulimit -H -f; {helper} file-limit',
           exact(b'128\n128\n128\n65536:65536\n'))
    yield ('ulimit independent soft hard and subshell',
           'ulimit -S -f 128; ulimit -H -f 256; (ulimit -S -f 64; ulimit -S -f); '
           f'ulimit -S -f; ulimit -H -f; {helper} file-limit',
           exact(b'64\n128\n256\n65536:131072\n'))

    def inventory(output):
        lines = output.decode().splitlines()
        required = dict(c=('core', '512-byte'), d=('data', '1024-byte'),
                        f=('file', '512-byte'), n=('descriptors', 'count'),
                        s=('stack', '1024-byte'), v=('address', '1024-byte'))
        for option, (description, units) in required.items():
            matches = [line for line in lines if line.startswith('-' + option + ' ')]
            if len(matches) != 1 or description not in matches[0] or units not in matches[0] or not re.search(r': (\d+|unlimited)$', matches[0]):
                return False
        return True
    yield ('ulimit all descriptions units and values', 'ulimit -a', inventory)
    # Hash listing format is unspecified: use pathname presence and exclusions,
    # never its particular line layout, labels or ordering as a portable oracle.
    yield ('hash listing excludes builtin and function',
           'f() { :; }; hash f read; hash >empty; test ! -s empty || exit 9; '
           'hash cat; hash; hash -r; hash >empty; test ! -s empty',
           lambda out: b'/cat' in out and b'read' not in out and b' f' not in out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('helper', type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    helper = shlex.quote(str(args.helper.resolve()))
    passed = failed = 0
    for name, script, predicate in observations(helper):
        for mode in ('string', 'file', 'stdin'):
            with tempfile.TemporaryDirectory(prefix='cshell-state-') as temporary:
                directory = Path(temporary)
                fixture = {'stdin': '', 'args': [], 'env': {'TZ': 'UTC0'}}
                if mode == 'string':
                    fixture['args'] = ['-c', script + '\n']
                elif mode == 'file':
                    (directory / 'script').write_text(script + '\n')
                    fixture['args'] = ['script']
                else:
                    fixture['stdin'] = script + '\n'
                status, output, errors = smoke.capture(binary, fixture, directory, 5, 65536)
                ok = not errors and status == 0 and not output['stderr'] and predicate(bytes(output['stdout']))
                print(('PASS' if ok else 'FAIL') + f': state-observation: {name} ({mode})', flush=True)
                if not ok:
                    print(status, output, errors, flush=True)
                    failed += 1
                else:
                    passed += 1
    print(f'Result: {passed} passed, {failed} failed, 0 skipped')
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
