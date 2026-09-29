#!/usr/bin/env python3
"""Strict CSH-070 selected printf/literal echo profile, with retained identities."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import tempfile

import smoke
from host_formatted_cases import cases, additional_cases
from host_formatted_failures import io_cases, allocation_cases
from host_echo_threshold import threshold
from host_utilities import serial, sha, source_identity

ROOT = Path(__file__).resolve().parents[1]


def capture(target, fixture, parent, output_limit):
    with tempfile.TemporaryDirectory(prefix='case-', dir=parent) as temporary:
        directory = Path(temporary)
        for name in ('script', 'input'):
            if (parent / name).exists():
                (directory / name).write_bytes((parent / name).read_bytes())
        try:
            status, output, errors = smoke.capture(target, fixture, directory, 5, output_limit)
        except (OSError, subprocess.SubprocessError) as error:
            return None, dict(stdout=b'', stderr=b''), ['setup: ' + str(error)], None
        measured = None
        if (directory / 'resource.json').exists():
            measured = json.loads((directory / 'resource.json').read_text())
        return status, {k: bytes(v) for k, v in output.items()}, errors, measured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--scope', choices=('all', 'contracts'), default='all',
                        help='contracts omits existing stack/memory and exec-capacity probes')
    parser.add_argument('--sanitizer', action='store_true', help='Use instrumented providers; resource/threshold scopes run separately')
    args = parser.parse_args()
    providers = {'printf': ROOT / 'build/host-printf', 'echo': ROOT / 'build/host-echo-literal'}
    if args.sanitizer:
        providers = {name: ROOT / 'build/host-formatted-sanitizer' / name for name in providers}
    catalog_policy = 'darwin' if platform.system() == 'Darwin' else 'glibc'
    binary = ROOT / 'cshell'
    input_sources = source_identity()
    input_paths = [binary, *providers.values(), ROOT / 'build/tests/host_printf_resources',
                   ROOT / 'build/tests/host_printf_faults',
                   *sorted((ROOT / 'build/host-profile/catalogs').glob('*.cat'))]
    input_hashes = {str(path): sha(path) for path in input_paths}
    records = []
    limitations = []
    with tempfile.TemporaryDirectory(prefix='csh-formatted-') as temporary:
        directory = Path(temporary)
        prefix = directory / 'bin'
        prefix.mkdir()
        for name, path in providers.items():
            (prefix / name).symlink_to(path)
        search = str(prefix) + ':' + os.defpath
        catalogs = directory / 'catalogs'
        catalogs.mkdir()
        for lang, locale in [('fr', 'fr_FR.UTF-8'), ('de', 'de_DE.UTF-8')]:
            data = (ROOT / 'build/host-profile/catalogs' / (lang + '.cat')).read_bytes()
            for folder in (lang, locale):
                (catalogs / folder).mkdir()
                for utility in ('printf', 'echo'):
                    (catalogs / folder / ('cshell-' + utility + '.cat')).write_bytes(data)
        (catalogs / 'empty.cat').write_bytes(b'')
        (catalogs / 'invalid.cat').write_bytes(b'not a message catalog\n')
        (catalogs / 'directory.cat').mkdir()
        (catalogs / 'incomplete.cat').write_bytes((ROOT / 'build/host-profile/catalogs/incomplete.cat').read_bytes())
        selected_cases = list(cases(ROOT / 'build/host-profile/catalogs')) + list(additional_cases(catalogs, catalog_policy))
        for case in selected_cases:
            for mode in ('direct', 'exec', 'string', 'file', 'stdin'):
                fixture = dict(env=dict(PATH=search, **case['env']), args=[], stdin='')
                if args.sanitizer:
                    fixture['env'].update(ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
                script = shlex.join([case['utility']] + case['argv']) + '\n'
                target = binary
                if mode == 'direct':
                    target = prefix / case['utility']
                    fixture['args'] = case['argv']
                elif mode == 'exec':
                    fixture['args'] = ['-c', 'exec ' + script]
                elif mode == 'string':
                    fixture['args'] = ['-c', script]
                elif mode == 'file':
                    (directory / 'script').write_text(script)
                    fixture['args'] = ['script']
                else:
                    fixture['stdin'] = script
                status, output, errors, _ = capture(target, fixture, directory, 65536)
                # err(3) identifies the basename of the selected invocation path.
                program = 'printf'
                expected_err = case['stderr'].replace(b'{program}', program.encode())
                ok = (not errors and status == case['status'] and
                      output['stdout'] == case['stdout'] and output['stderr'] == expected_err)
                records.append(dict(name=case['name'], mode=mode, verdict='PASS' if ok else 'FAIL',
                                    expected=serial(dict(status=case['status'], stdout=case['stdout'], stderr=expected_err)),
                                    invocation=fixture, actual=serial(dict(status=status, **output, errors=errors))))
                if not ok:
                    print('FAIL:', case['name'], mode, serial(dict(status=status, **output, errors=errors)))
        # Private input remains unread; output failure is in the selected utility.
        for utility in providers:
            for script, expected_out, expected_err, expected_status in [
                (f'{utility} value <input; read line <&3; printf %s "$line"',
                 b'value' + (b'\n' if utility == 'echo' else b'') + b'untouched', b'', 0),
                (f'{utility} value >&-', b'', None, 1),
            ]:
                (directory / 'input').write_text('untouched\n')
                # Both descriptors refer to one open file description.
                fixture = dict(args=['-c', 'exec 3<input; ' + script.replace('<input', '<&3')],
                               stdin='', env={'PATH': search})
                status, output, errors, _ = capture(binary, fixture, directory, 65536)
                ok = (not errors and status == expected_status and output['stdout'] == expected_out and
                      (bool(output['stderr']) if expected_err is None else output['stderr'] == expected_err))
                records.append(dict(name=utility + ' stdin/closed stdout ' + script, verdict='PASS' if ok else 'FAIL',
                                    invocation=fixture, actual=serial(dict(status=status, **output, errors=errors))))
        for lang, locale, expected in [('fr', 'fr_FR.UTF-8', 'echo : erreur d’écriture\n'),
                                        ('de', 'de_DE.UTF-8', 'echo: Schreibfehler\n')]:
            fixture = dict(args=['-c', 'echo value >&-'], stdin='',
                           env=dict(PATH=search, LC_ALL=locale,
                                    NLSPATH=str(ROOT / 'build/host-profile/catalogs' / (lang + '.cat'))))
            status, output, errors, _ = capture(binary, fixture, directory, 65536)
            ok = not errors and status == 1 and not output['stdout'] and output['stderr'] == expected.encode()
            records.append(dict(name='echo catalog ' + lang, verdict='PASS' if ok else 'FAIL',
                                invocation=fixture, actual=serial(dict(status=status, **output, errors=errors))))
        if not args.sanitizer:
            records.extend(io_cases(binary, prefix))
            records.extend(allocation_cases(binary, prefix, ROOT / 'build/tests/host_printf_faults'))
        if args.scope == 'contracts':
            limitations.append(dict(scope='stack/memory and exec capacities', verdict='NOT-RUN',
                                     reason='Explicit contracts scope; previous full-profile measurements remain separate'))
        for kind in (() if args.sanitizer or args.scope == 'contracts' else ('stack', 'memory')):
            if kind == 'memory' and platform.system() != 'Linux':
                limitations.append(dict(condition='U-035/format-allocation-limits',
                                         reason='Darwin libc memory exhaustion is not supplied by Linux RLIMIT_AS',
                                         owner='CSH-079', verdict='UNQUALIFIED'))
                continue
            fixture = dict(args=[kind], stdin='', env={'PATH': search})
            status, output, errors, measured = capture(ROOT / 'build/tests/host_printf_resources', fixture,
                                                            directory, 400000)
            ok = (not errors and measured and measured['soft'] == (65536 if kind == 'stack' else 16777216) and
                  (status == 0 and output['stdout'] == b'x' * 262145 and not output['stderr'] if kind == 'stack'
                   else status == 1 and not output['stdout'] and
                   output['stderr'] == b'host_printf_resources: write or formatting error: Cannot allocate memory\n'))
            records.append(dict(name='printf resource ' + kind, verdict='PASS' if ok else 'FAIL',
                                measured=measured, invocation=fixture,
                                actual=dict(status=status, stdout_bytes=len(output['stdout']),
                                            stdout_sha256=hashlib.sha256(output['stdout']).hexdigest(),
                                            stderr_hex=output['stderr'].hex(), errors=errors)))
        stacks = (1024 * 1024, 8 * 1024 * 1024) if platform.system() == 'Linux' else (8 * 1024 * 1024,)
        if args.scope == 'contracts':
            stacks = ()
        if args.sanitizer:
            stacks = ()
            limitations.append(dict(scope='resources, exec capacities and I/O/allocation failures', verdict='NOT-RUN',
                                     reason='Run separately with normal providers/helpers; sanitizer startup changes resource/process behavior'))
        if platform.system() == 'Darwin' and not args.sanitizer:
            limitations.append(dict(condition='U-036/argument-limits', owner='CSH-079',
                                     verdict='UNQUALIFIED', reason='1 MiB stack near ARG_MAX retained stuck execs after SIGKILL; only 8 MiB selected'))
        for stack in stacks:
            for padding in (0, 4096):
                for shape in ('single', 'aggregate'):
                    result = threshold(providers['echo'], shape, padding, stack)
                    result['name'] = f'echo threshold {shape} pad={padding} stack={stack}'
                    records.append(result)
    final_sources = source_identity()
    changed_inputs = [str(path) for path in input_paths if sha(path) != input_hashes[str(path)]]
    stable = input_sources == final_sources and not changed_inputs
    records.append(dict(name='qualification input stability', verdict='PASS' if stable else 'FAIL',
                        source_changed=input_sources != final_sources, changed_inputs=changed_inputs))
    result = dict(scope=args.scope, sanitizer=args.sanitizer, catalog_failure_policy=catalog_policy, platform=platform.platform(), uname=list(platform.uname()), libc=platform.libc_ver(),
                  source_identity=input_sources, final_source_identity=final_sources, input_hashes=input_hashes, path=search, binary_sha256=sha(binary),
                  providers={name: dict(path=str(path), realpath=str(path.resolve()), sha256=sha(path),
                                       package='repository source build; see source_identity')
                             for name, path in providers.items()},
                  catalogs={str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'build/host-profile/catalogs').glob('*.cat')},
                  resource_helper_sha256=sha(ROOT / 'build/tests/host_printf_resources'),
                  allocation_helper_sha256=sha(ROOT / 'build/tests/host_printf_faults'),
                  locale_inventory=subprocess.check_output(['locale', '-a'], text=True, timeout=5),
                  compiler=subprocess.check_output(['cc', '--version'], text=True, timeout=5),
                  limits=dict(timeout_seconds=5, threshold_cap_bytes=4194304, cleanup_seconds=2),
                  temporary_directory_removed=not directory.exists(), limitations=limitations,
                  totals={v: sum(r['verdict'] == v for r in records) for v in ('PASS', 'FAIL')}, cases=records)
    if platform.system() == 'Linux':
        result['package_versions'] = subprocess.check_output(['dpkg-query', '-W', '-f=${Package} ${Version}\n'], text=True, timeout=5)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print('CSH-070:', result['totals'], 'limitations:',
          {verdict: sum(item['verdict'] == verdict for item in limitations)
           for verdict in ('UNQUALIFIED', 'NOT-RUN')})
    return int(bool(result['totals']['FAIL']))


if __name__ == '__main__':
    raise SystemExit(main())
