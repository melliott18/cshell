#!/usr/bin/env python3
"""Reproduce CSH-070 defects against immutable pre-change provider source.

Run from the repository root (git required), then copy build/csh070-before into
/work/build in the recorded Docker image and use --run-only there. The baseline
adapter only receives an entrypoint rename for the shared resource fixture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tests'))
import smoke
from host_utilities import sha, serial

BASE = '60295934db1c971a2b3aac582f88b0f766eccce2'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-only', action='store_true')
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    tree = ROOT / 'build/csh070-before'
    if not args.run_only:
        for name in ('tools/host-profile/printf.c', 'tools/host-profile/vendor/printf.c'):
            dest = tree / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            source = subprocess.check_output(['git', 'show', BASE + ':' + name]).decode()
            if name.endswith('profile/printf.c'):
                source = source.replace('int main(int argc, char **argv)',
                                        '#ifndef HOST_PRINTF_MAIN\n#define HOST_PRINTF_MAIN main\n#endif\nint HOST_PRINTF_MAIN(int argc, char **argv)')
            dest.write_text(source)
        (tree / 'tests').mkdir(exist_ok=True)
        (tree / 'tests/host_printf_resources.c').write_bytes((ROOT / 'tests/host_printf_resources.c').read_bytes())
    for name, source in [('printf', 'tools/host-profile/printf.c'), ('host_printf_resources', 'tests/host_printf_resources.c')]:
        subprocess.run(['cc', '-std=c99', '-O2', '-o', str(tree / name), str(tree / source)], check=True)
    rows = []
    probes = [('quoted float', 'printf', ['%.1f:%s', "'A", 'after'], b'0.0:after', 1),
              ('trailing character constant', 'printf', ['%d:%s', "'Aextra", 'after'], b'65:after', 1)]
    # Do not repeat the native low-stack kernel failure discovered during exec
    # threshold work. Resource baseline reproduction uses disposable Linux only.
    if platform.system() == 'Linux':
        probes += [('stack', 'host_printf_resources', ['stack'], b'x' * 262145, 0),
                   ('memory', 'host_printf_resources', ['memory'], b'', 1)]
    for name, executable, argv, out, expected_status in probes:
        with tempfile.TemporaryDirectory(prefix='csh070-before-') as temporary:
            status, output, errors = smoke.capture(tree / executable, dict(args=argv, stdin='', env={}), Path(temporary), 5, 400000)
            diagnostic_required = name != 'stack'
            ok = status == expected_status and output['stdout'] == out and not errors and (bool(output['stderr']) if diagnostic_required else not output['stderr'])
            rows.append(dict(name=name, verdict='PASS' if ok else 'FAIL', expected_status=expected_status,
                             expected_stdout_sha256=hashlib.sha256(out).hexdigest(), diagnostic_required=diagnostic_required,
                             actual=dict(status=status, stdout_sha256=hashlib.sha256(output['stdout']).hexdigest(),
                                         stdout_bytes=len(output['stdout']), stderr_hex=output['stderr'].hex(), errors=errors)))
    result = dict(base=BASE, platform=platform.platform(),
                  files={str(p.relative_to(tree)): sha(p) for p in tree.rglob('*') if p.is_file()}, cases=rows)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print([(r['name'], r['verdict'], r['actual']['status']) for r in rows])


if __name__ == '__main__':
    main()
