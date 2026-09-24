#!/usr/bin/env python3
"""Bounded context behavior, ownership and synchronization checks."""
import argparse
import os
from pathlib import Path
import shlex
import tempfile
from execute import bounded_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binary')
    parser.add_argument('--helper', required=True)
    parser.add_argument('--api-binary', required=True)
    parser.add_argument('--fault-binary', required=True)
    args = parser.parse_args()
    binary, helper_path, api, faults = (str(Path(p).resolve()) for p in
        (args.binary, args.helper, args.api_binary, args.fault_binary))
    helper = shlex.quote(helper_path)
    checked = 0
    with tempfile.TemporaryDirectory(prefix='cshell-context-') as temporary:
        cwd = Path(temporary).resolve()
        env = dict(os.environ, PATH='/bin:/usr/bin', HOME=str(cwd))

        def run(script, status=0, output=b'', diagnostic=False):
            nonlocal checked
            result = bounded_run([binary, '-c', script], cwd=cwd, env=env, timeout=10)
            assert result.returncode == status, (script, result)
            assert result.stdout == output, (script, result)
            assert bool(result.stderr) == diagnostic, (script, result)
            checked += 1

        for first in (0, 7):
            for second in (0, 9):
                for operator in ('&&', '||'):
                    selected = (first == 0) == (operator == '&&')
                    run(f'{helper} status {first} {operator} {helper} status {second}',
                        status=second if selected else first)
        run(f'{helper} status 0 || {helper} args no && {helper} args yes', output=b'[yes]\n')
        run(f'{helper} status 7 && {helper} args no || {helper} args yes', output=b'[yes]\n')
        run(f'{helper} args one; {helper} args two\n{helper} status 11',
            status=11, output=b'[one]\n[two]\n')
        run(f'! {{ {helper} status 9; }} && ({helper} args yes)', output=b'[yes]\n')
        run(f'{{ export VALUE=brace; (export VALUE=subshell); }}; {helper} environment VALUE',
            output=b'VALUE=brace\n')
        (cwd / 'nested').mkdir()
        run(f'(cd nested); {helper} pwd', output=(str(cwd) + '\n').encode())
        run(f'{{ cd nested; }}; {helper} pwd', output=(str(cwd / 'nested') + '\n').encode())
        run(f'{{ ({helper} args inner); {helper} args outer; }} >captured; {helper} args restored',
            output=b'[restored]\n')
        assert (cwd / 'captured').read_bytes() == b'[inner]\n[outer]\n'
        run(f'{{ {{ {helper} args inner; }} >inner; {helper} args outer; }} >outer; {helper} args restored',
            output=b'[restored]\n')
        assert (cwd / 'inner').read_bytes() == b'[inner]\n'
        assert (cwd / 'outer').read_bytes() == b'[outer]\n'
        run(f'{{ cd nested; }} >created <missing || {helper} pwd',
            output=(str(cwd) + '\n').encode(), diagnostic=True)
        run(f'cd . <missing || {helper} args recovered', output=b'[recovered]\n', diagnostic=True)
        run(f'{{ cd . <missing; }} 2>errors; {helper} args after', output=b'[after]\n')
        assert b'cannot apply redirection' in (cwd / 'errors').read_bytes()
        run(f'{{ exit 13; }} >empty; {helper} args never', status=13)
        run(f'(exit 13) || {helper} args alive', output=b'[alive]\n')
        run(f'(readonly LOCK=one; LOCK=two); {helper} args alive', output=b'[alive]\n', diagnostic=True)
        run(f'{{ export 1bad; }}; {helper} args never', status=1, diagnostic=True)
        run(f'({{ export 1bad; }}); {helper} args alive', output=b'[alive]\n', diagnostic=True)
        run(f'{{ {helper} args first; {helper} args second; }} | ({helper} copy)',
            output=b'[first]\n[second]\n')
        run(f'{{ {helper} generate 8388608; }} | {{ {helper} copy; }} | {helper} count',
            output=b'8388608\n')
        run(f'{{ exit 17; }} | ({helper} status 0)')
        run(f'({helper} status 0) | {{ exit 17; }}', status=17)
        run(f'! ({helper} status 0) | {{ exit 17; }}')
        run(f'{{ cd nested; }} | {helper} copy; {helper} pwd', output=(str(cwd) + '\n').encode())
        run(f'{{ {helper} args file; }} >override | {helper} count', output=b'0\n')
        assert (cwd / 'override').read_bytes() == b'[file]\n'
        run(f'{{ {helper} copy; }} <<\'END\'\nbody\nEND\n', output=b'body\n')
        os.mkfifo(cwd / 'async-output')
        run(f'{helper} count >async-output & {helper} copy <async-output', output=b'0\n')
        (cwd / 'input').write_bytes(b'input\n')
        run(f'{helper} copy <input >async-output & {helper} copy <async-output', output=b'input\n')
        run(f'{{ {helper} status 9 && {helper} args never; }} >async-output & {helper} copy <async-output')
        run(f'{{ {helper} args yes; }} | {helper} copy >async-output & {helper} copy <async-output', output=b'[yes]\n')
        run(f'export VALUE=parent; {{ export VALUE=child; }} & {helper} environment VALUE',
            output=b'VALUE=parent\n')
        for fd in range(3, 24):
            run(f'{{ : 1>&{fd}; }} >private-test', status=1, diagnostic=True)
        run(f'{{ >forbidden; if true; then true; fi; }}', status=2, diagnostic=True)
        assert not (cwd / 'forbidden').exists()
        result = bounded_run([api, helper_path], cwd=cwd, env=env, timeout=20)
        assert result.returncode == 0 and result.stdout == b'context API checks passed\n', result
        assert result.stderr.count(b'cannot apply redirection') == 7, result
        result = bounded_run([faults, '--context'], cwd=cwd, env=env, timeout=30)
        assert result.returncode == 0 and result.stdout == b'context fault checks passed\n', result
    print(f'context fixtures passed ({checked} behavior cases, API and fault checks)')


if __name__ == '__main__':
    main()
