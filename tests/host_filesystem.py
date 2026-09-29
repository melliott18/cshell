#!/usr/bin/env python3
"""Strict CSH-072 filesystem subset; separate --audit retains vendor failures."""
import argparse
import json
import locale
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tarfile

import pty_harness

import smoke
from host_filesystem_cases import UTILITIES, cases, audit_cases, terminal_cases, setup, effect_errors
from host_platform import filesystem_identity
from host_utilities import inventory, match, sanitizer_diagnostic, serial, sha, source_identity


def stdout_matches(expected, output, directory, cwd, row):
    if isinstance(expected, bytes):
        return output == expected
    if expected == 'cwd':
        return output == os.fsencode(str(cwd.resolve()) + '\n')
    if expected.startswith('resolved-'):
        return output == os.fsencode(str(directory.resolve() / expected[9:]) + '\n')
    if expected == 'deep-leaf':
        return output == ('deep/' + 'd/' * 64 + 'é\n').encode()
    if expected == 'du-blocks':
        # st_blocks is expressed in 512-byte units; -k rounds up to KiB.
        blocks = ((directory / 'data').stat().st_blocks + 1) // 2
        return re.fullmatch(str(blocks).encode() + rb'[ \t]+data\n', output) is not None
    if expected.startswith('file-'):
        # Descriptive wording is implementation-defined; POSIX requires these
        # classification words and the operand prefix, not vendor magic text.
        name, word = (b'empty', b'empty') if expected == 'file-empty' else (b'tree', b'directory')
        return re.fullmatch(name + rb':[ \t]+[^\n]*\b' + word + rb'\b[^\n]*\n', output) is not None
    if expected == 'df-portable':
        lines = output.splitlines()
        if len(lines) != 2 or lines[0].split() != b'Filesystem 1024-blocks Used Available Capacity Mounted on'.split():
            return False
        fields = re.fullmatch(rb'(\S+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)%\s+(/[^\n]*)', lines[1])
        if not fields:
            return False
        total, used, free, percentage = map(int, fields.group(2, 3, 4, 5))
        # Allocation may race with other filesystem users. Check the normative
        # ceiling relationship, not a snapshot of mutable global free space.
        return total > 0 and (used + free <= 0 or percentage == (100 * used + used + free - 1) // (used + free))
    raise ValueError('unknown stdout oracle: ' + expected)


def stderr_matches(row, output):
    if row['stderr'] != 'dd-statistics':
        return match(row['stderr'], output)
    count, size = {'dd/copy': (2, 512), 'dd/skip': (1, 128), 'dd/swab': (2, 8)}[row['id']]
    prefix = f'{count}+0 records in\n{count}+0 records out\n'.encode()
    # Transfer-rate text is an extension, not an exact deterministic byte oracle.
    return output.startswith(prefix) and re.fullmatch(str(size).encode() + rb' bytes[^\n]*\n', output[len(prefix):]) is not None


def run_case(binary, providers, search_path, row, mode, fixture_root, utf8, timeout=5, sanitizer=False):
    record = dict(id=row['id'], mode=mode, source=row['source'], expected=serial(row), phase='setup', verdict='FAIL')
    temporary = tempfile.mkdtemp(prefix='csh-filesystem-', dir=fixture_root)
    directory = Path(temporary)
    try:
        provider = providers[row['utility']]['path']
        if not provider:
            raise OSError('required executable unavailable: ' + row['utility'])
        if row.get('utf8') and not utf8:
            raise OSError('UTF-8 locale required for deep character oracle')
        cwd = setup(directory, row)
        env = {'PATH': search_path, 'TZ': 'UTC0', 'LC_ALL': utf8 if row.get('utf8') else 'C'}
        env.update(row.get('env', {}))
        if sanitizer:
            env.update(ASAN_OPTIONS='halt_on_error=1' + (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                       UBSAN_OPTIONS='halt_on_error=1')
        argv = [row['utility'], *row['args']]
        direct = [provider, *row['args']]
        if row.get('fault') or row.get('closed_stdout'):
            action = 'signal.signal(signal.SIGXFSZ,signal.SIG_IGN)' if row.get('fault') else 'os.close(1)'
            wrapper = [sys.executable, '-c', 'import os,signal,sys; ' + action + '; os.execv(sys.argv[1],sys.argv[1:])']
            argv = wrapper + direct
            direct = argv
        script = shlex.join(argv) + '\n'
        invocation = dict(stdin='', env=env)
        executable = binary
        if mode in ('direct', 'pty-direct'):
            executable, invocation['args'] = Path(direct[0]), direct[1:]
        elif mode in ('string', 'pty-string'):
            invocation['args'] = ['-c', script]
        elif mode in ('file', 'pty-file'):
            (cwd / 'script').write_text(script)
            invocation['args'] = ['script']
        elif mode == 'stdin':
            invocation.update(args=[], stdin=script)
        else:
            raise ValueError('unknown invocation mode')
        if mode.startswith('pty-'):
            invocation.update(transport='pty', steps=[{'expect': 'data'}, {'send': row['response'] + '\n'}])
            invocation.pop('stdin')
        record.update(phase='assertion', invocation=invocation, executable=str(executable), fixture=str(directory))
        status, output, errors = smoke.capture(executable, invocation, cwd, timeout, 65536,
                                               file_size_limit=512 if row.get('fault') else None)
        output = {k: bytes(v) for k, v in output.items()}
        if mode.startswith('pty-'):
            # POSIX specifies a prompt on stderr but leaves its wording open.
            # The PTY merges streams; exact selected-vendor prompt plus effects.
            prefix = os.fsencode(provider if mode == 'pty-direct' else 'rm')
            prompt = b'remove data? ' if platform.system() == 'Darwin' else prefix + b": remove regular file 'data'? "
            if output['output'] != prompt:
                errors.append('terminal prompt mismatch')
            record['terminal_output'] = serial(output['output'])
            output = {'stdout': b'', 'stderr': b''}
        effects, observed = effect_errors(directory, row)
        errors.extend(effects)
        if not match(row['status'], status):
            errors.append('status mismatch')
        if not stdout_matches(row['stdout'], output['stdout'], directory, cwd, row):
            errors.append('stdout mismatch')
        if not stderr_matches(row, output['stderr']):
            errors.append('stderr mismatch')
        if sanitizer_diagnostic(output):
            errors.append('sanitizer diagnostic')
        record.update(actual=serial(dict(status=status, **output, effects=observed)), errors=errors,
                      verdict='FAIL' if errors else 'PASS')
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError, pty_harness.PtyUnavailable) as error:
        record.update(error=str(error), errno=getattr(error, 'errno', None))
    finally:
        try:
            shutil.rmtree(directory)
            record['cleanup'] = not directory.exists()
        except OSError as error:
            record.update(cleanup=False, cleanup_error=str(error), verdict='FAIL')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--fixture-root', type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--sanitizer', action='store_true')
    args = parser.parse_args()
    providers = inventory(args.path, UTILITIES)
    utf8 = None
    previous = locale.setlocale(locale.LC_CTYPE)
    for candidate in ('en_US.UTF-8', 'C.UTF-8', 'en_US.utf8'):
        try:
            locale.setlocale(locale.LC_CTYPE, candidate)
            if locale.nl_langinfo(locale.CODESET).lower().replace('-', '') == 'utf8':
                utf8 = candidate
                break
        except locale.Error:
            pass
    locale.setlocale(locale.LC_CTYPE, previous)
    rows = list(cases()) + list(terminal_cases()) + (list(audit_cases()) if args.audit else [])
    records = []
    for row in rows:
        for mode in row.get('modes', ('direct', 'string', 'file', 'stdin')):
            record = run_case(args.binary.resolve(), providers, args.path, row, mode, args.fixture_root, utf8, sanitizer=args.sanitizer)
            records.append(record)
            print(record['verdict'] + ': ' + row['id'] + ' (' + mode + ')', flush=True)
            if record['verdict'] != 'PASS':
                print(json.dumps(record), flush=True)
    totals = {key: sum(r['verdict'] == key for r in records) for key in ('PASS', 'FAIL')}
    result = dict(ticket='CSH-072', scope='bounded subset plus required-contract audit' if args.audit else 'bounded subset',
                  full_contracts_qualified=False, path=args.path, providers=providers, platform=platform.platform(),
                  libc=platform.libc_ver(), utf8_locale=utf8, uid=os.getuid(), gid=os.getgid(), groups=os.getgroups(),
                  filesystem=filesystem_identity(args.fixture_root),
                  limits=dict(timeout_seconds=5, output_bytes=65536, file_bytes=1048576, fault_file_bytes=512,
                              open_files=64, cpu_seconds=6, umask='077', name_max=os.pathconf(args.fixture_root, 'PC_NAME_MAX'),
                              path_max=os.pathconf(args.fixture_root, 'PC_PATH_MAX')),
                  source_identity=source_identity(), binary_sha256=sha(args.binary), totals=totals, cases=records)
    if platform.system() == 'Linux' and shutil.which('dpkg-query'):
        result['package_versions'] = subprocess.check_output(['dpkg-query', '-W', '-f=${Package} ${Version}\n'], text=True)
    if platform.system() == 'Darwin':
        result['os_build'] = subprocess.check_output(['/usr/bin/sw_vers'], text=True)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(totals))
    return int(bool(totals['FAIL']))


if __name__ == '__main__':
    raise SystemExit(main())
