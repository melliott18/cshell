#!/usr/bin/env python3
"""CSH-067 finite locale/pathname witnesses; no reference-shell oracle.

Byte scripts and outputs are recorded as hex. Public binary, instrumented
runtime and host capabilities are distinct records. Missing capabilities skip;
a wrong result after successful setup fails. All shell runs use smoke's bounds
and process-group cleanup. Permission fixtures are owned by the invoking user.
"""
import argparse
import errno
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import tempfile

import smoke


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, timeout=10)
        return result.stdout.decode(errors='replace').strip()
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('probe', type=Path)
    parser.add_argument('fault_binary', type=Path)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    binary, probe, fault_binary = (p.resolve() for p in
                                  (args.binary, args.probe, args.fault_binary))
    records, skips, capabilities = [], [], []

    def skip(condition, prerequisite):
        skips.append(dict(condition=condition, prerequisite=prerequisite, owner='CSH-067'))
        print(f'SKIP: {condition}: {prerequisite} (owner CSH-067)', flush=True)

    def locale_name(names, sample=None):
        for name in names:
            result = subprocess.run([str(probe), name] + ([sample.hex()] if sample else []),
                                    capture_output=True, timeout=5)
            capabilities.append(dict(locale=name, sample_hex=sample.hex() if sample else None,
                                     status=result.returncode, stdout=result.stdout.decode(errors='replace'),
                                     stderr=result.stderr.decode(errors='replace')))
            if result.returncode == 77:
                continue
            if result.returncode:
                # Installed but unusable decoder is not silently an absent locale.
                records.append(dict(name=f'host decoder {name} {sample!r}', kind='host capability',
                                    failures=[repr(result)]))
                print(f'FAIL: host decoder {name}: {result.stderr!r}', flush=True)
                return False
            return name
        return None

    def run(name, script, expected=b'', *, env=None, setup=None, stderr=b'', status=0,
            modes=('string', 'file', 'stdin'), instrumented=False, verify=None,
            operand=None):
        script = script.encode() if isinstance(script, str) else script
        expected = expected.encode() if isinstance(expected, str) else expected
        stderr = stderr.encode() if isinstance(stderr, str) else stderr
        for mode in modes:
            with tempfile.TemporaryDirectory(prefix='cshell-locale-pathname-') as tmp:
                root = Path(tmp)
                cleanup = setup(root) if setup else None
                try:
                    fixture = dict(stdin=b'', args=[], env=env or {})
                    if operand:
                        fixture['args'] = [operand]
                    elif mode == 'string':
                        fixture['args'] = [b'-c', script]
                    elif mode == 'file':
                        (root / 'script').write_bytes(script)
                        fixture['args'] = ['script']
                    else:
                        fixture['stdin'] = script
                    actual, output, failures = smoke.capture(
                        fault_binary if instrumented else binary, fixture, root, 5, 65536)
                    got = (actual, bytes(output['stdout']), bytes(output['stderr']))
                    if got != (status, expected, stderr):
                        failures.append(f'expected {(status, expected, stderr)!r}, got {got!r}')
                    if verify:
                        failures.extend(verify(root))
                    records.append(dict(name=f'{name} ({mode})',
                        kind='instrumented public runtime' if instrumented else 'public runtime',
                        script_hex=script.hex(), env=fixture['env'], operand=operand,
                        expected=dict(status=status, stdout_hex=expected.hex(), stderr_hex=stderr.hex()),
                        actual=dict(status=actual, stdout_hex=got[1].hex(), stderr_hex=got[2].hex()),
                        failures=failures))
                    print(('FAIL: ' if failures else 'PASS: ') + records[-1]['name'], flush=True)
                    for failure in failures:
                        print(' ', failure, flush=True)
                finally:
                    if cleanup:
                        cleanup()

    def paths(root):
        (root / 'tree/dir').mkdir(parents=True)
        (root / 'tree/dir/leaf').touch()
        (root / 'tree/file').touch()
        (root / 'tree/link').symlink_to('dir', target_is_directory=True)
        (root / 'tree/dangling').symlink_to('absent')
        (root / 'tree/loop').symlink_to('loop')

    run('symlink and trailing slash',
        "printf '<%s>\\n' tree/dang* tree/l*/leaf tree/*/ tree/file/* tree/loop/*\n",
        '<tree/dangling>\n<tree/link/leaf>\n<tree/dir/>\n<tree/link/>\n<tree/file/*>\n<tree/loop/*>\n', setup=paths)
    run('quoted prefix and repeated slash', "printf '<%s>\\n' 'tree/link'//* tree/dang*/\n",
        '<tree/link//leaf>\n<tree/dang*/>\n', setup=paths)

    # Check actual access denial, not just uid != 0 or requested mode bits.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'denied'
        path.mkdir(); path.chmod(0)
        try:
            try:
                os.listdir(path)
                denied = False
            except PermissionError:
                denied = True
        finally:
            path.chmod(0o700)
    capabilities.append(dict(permission_denial=denied, uid=os.getuid(), euid=os.geteuid()))
    if denied:
        def permissions(root):
            modes = {'search': 0o100, 'read': 0o400, 'blocked': 0}
            for name, mode in modes.items():
                (root / name / 'sub').mkdir(parents=True)
                (root / name / 'sub/leaf').touch()
                (root / name / 'leaf').touch()
                (root / name).chmod(mode)
            return lambda: [(root / name).chmod(0o700) for name in modes]
        run('owned read versus search permissions',
            "printf '<%s>\\n' search/sub/* search/* read/* read/*/leaf blocked/* */leaf\n",
            '<search/sub/leaf>\n<search/*>\n<read/leaf>\n<read/sub>\n<read/*/leaf>\n<blocked/*>\n<search/leaf>\n',
            setup=permissions)
        def unreadable(root):
            (root / 'unreadable').write_text(': > effect\n')
            (root / 'unreadable').chmod(0)
            return lambda: (root / 'unreadable').chmod(0o600)
        for operand in ('unreadable', './unreadable'):
            run('SH-003 unreadable ' + operand, b'', setup=unreadable, operand=operand,
                modes=('file',), status=1,
                stderr=f'cshell: {operand}: 1:1: cannot open script: {os.strerror(errno.EACCES)}\n',
                verify=lambda root: ['script executed'] if (root / 'effect').exists() else [])
    else:
        skip('owned directory/script permission witnesses', 'credentials/filesystem enforcing owner mode denial')

    def fault_paths(root):
        for name in ('fault', 'good'):
            (root / 'paths' / name).mkdir(parents=True)
            (root / 'paths' / name / 'match').touch()
    def injected(root):
        if not (root / 'injected').exists() or (root / 'injected').read_text() != 'injected\n':
            return ['directory-read failure was not injected after a matching entry']
        if (root / 'effect').exists():
            return ['failed expansion executed command/redirection']
        return []
    for error in ('EACCES', 'ENOENT'):
        run('partial readdir ' + error,
            "printf '<%s>\\n' paths/*/*; printf '<%s>\\n' paths/fault/*\n",
            '<paths/good/match>\n<paths/fault/*>\n', setup=fault_paths,
            env={'CSH_PATH_FAULT': error}, instrumented=True, verify=injected)
    run('readdir EIO project failure policy', 'printf forbidden paths/*/* > effect\n',
        setup=fault_paths, env={'CSH_PATH_FAULT': 'EIO'}, instrumented=True, status=1,
        stderr='cshell: pathname expansion I/O failed: ' + os.strerror(errno.EIO) + '\n', verify=injected)

    selected = locale_name(('csh_067.UTF-8',))
    if selected:
        env = {'LC_ALL': selected}
        def collating_paths(root):
            for name in ('a', 'A', 'ch', 'c', 'h'):
                (root / name).touch()
        run('defined multicharacter element in case removal pathname',
            "case ch in [[.ch.]]) printf 'element\\n';; esac\n"
            "v=chXch; printf '<%s>\\n' \"${v#[[.ch.]]}\" \"${v%[[.ch.]]}\" "
            "\"${v##*[[.ch.]]}\" \"${v%%[[.ch.]]*}\"\n"
            "printf '<%s>\\n' [[.ch.]]\n", 'element\n<Xch>\n<chX>\n<>\n<>\n<ch>\n',
            env=env, setup=collating_paths)
        run('defined equivalence class and quoted bracket',
            "case A in [[=a=]]) printf 'equivalent\\n';; esac\n"
            "v=Axa; printf '<%s>\\n' \"${v#[[=a=]]}\" \"${v%[[=a=]]}\"\n"
            "printf '<%s>\\n' [[=a=]] '[[=a=]]'\n", 'equivalent\n<xa>\n<Ax>\n<a>\n<A>\n<[[=a=]]>\n',
            env=env, setup=collating_paths)
    elif selected is None:
        skip('controlled collation elements/equivalence',
             'localedef -i tests/locales/csh_067 -f UTF-8 csh_067.UTF-8 (supplied Linux locale)')

    # EUC-JP SS2 and SS3 encode one character per shift+payload sequence.
    # Preserve exact bytes; never substitute UTF-8 filename failures for decoding.
    for sample in (bytes.fromhex('8eb6'), bytes.fromhex('8fa2af')):
        selected = locale_name(('ja_JP.eucJP', 'ja_JP.EUC-JP'), sample)
        if not selected:
            if selected is None:
                skip('EUC-JP single-shift ' + sample.hex(), 'installed EUC-JP locale and complete libc decoder')
            continue
        env = {'LC_ALL': selected}
        script = (b"v='" + sample + b"'; printf '<%s>\\n' " + sample + b" \\" + sample +
                  b' "' + sample + b'" $\'' + sample + b"' \"${#v}\" \"${v#?}\"\n" +
                  b"IFS='" + sample + b"'; v='a" + sample + b"b'; printf '<%s>\\n' $v\n" +
                  b"read a b < data; printf '<%s>\\n' \"$a\" \"$b\"\n")
        def data(root):
            (root / 'data').write_bytes(b'a' + sample + b'b\n')
        run('single-shift source expansion read ' + sample.hex(), script,
            (b'<' + sample + b'>\n') * 4 + b'<1>\n<>\n<a>\n<b>\n<a>\n<b>\n', env=env, setup=data)
        run('single-shift alias reusable output ' + sample.hex(),
            b"alias value='printf \"%s\\n\" " + sample + b"'\ndefinition=$(alias value)\nunalias -a\neval \"alias $definition\"\nvalue\n",
            sample + b'\n', env=env)
        # Dollar escapes are deliberately ASCII; generated byte policy is separate
        # from source character decoding and unspecified nonrepresentable escapes.
        run('single-shift dollar escape protection ' + sample.hex(),
            b"printf '<%s>\\n' $'\\x41\\101\\t*'\n", b'<AA\t*>\n', env=env)

    # Missing-name diagnostics have specified destination/nonzero status, but
    # exact English text is the application's documented message policy.
    for selected in ('C', 'fr_FR.UTF-8'):
        available = locale_name((selected,))
        if not available:
            if available is None:
                skip('application messages ' + selected, 'installed ' + selected)
            continue
        for utility in ('alias', 'unalias'):
            run(f'{utility} diagnostic language policy {selected}', utility + ' missing\n',
                status=1, stderr=f'{utility}: missing: not found\n', env={'LC_ALL': selected})

    failed = sum(bool(r['failures']) for r in records)
    document = dict(platform=platform.platform(), libc=platform.libc_ver(),
        libc_conf=command('getconf', 'GNU_LIBC_VERSION'),
        credentials=dict(uid=os.getuid(), euid=os.geteuid(), gid=os.getgid(), groups=os.getgroups()),
        available_locales=command('locale', '-a').splitlines(),
        filesystem=command('df', '-P', tempfile.gettempdir()),
        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        fault_binary_sha256=hashlib.sha256(fault_binary.read_bytes()).hexdigest(),
        definition_sha256=hashlib.sha256(Path('tests/locales/csh_067').read_bytes()).hexdigest(),
        locale_sources={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (Path('/usr/share/i18n/locales') / n for n in
                                  ('cs_CZ', 'en_US', 'ja_JP', 'iso14651_t1', 'iso14651_t1_common'))
                        if p.is_file()},
        capabilities=capabilities, skips=skips, records=records,
        totals=dict(passed=len(records)-failed, failed=failed, skipped=len(skips)))
    if args.record:
        import json
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(document, indent=2) + '\n')
    print(f'CSH-067: {len(records)-failed} passed, {failed} failed, {len(skips)} capability skips')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
