"""Retain unpatched failures and focused sanitizer/provider regressions."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
label = sys.argv[1]
output = root / 'build/csh103-provider-checks'
output.mkdir(exist_ok=True)
records = []


def run(name, argv, cwd=root, env=None, expected=0):
    start = time.monotonic()
    log = output / (label + '-' + name + '.log')
    with log.open('wb') as stream:
        r = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    records.append(dict(name=name, argv=[str(a) for a in argv], cwd=str(cwd),
                        env=env, status=r.returncode, expected_status=expected,
                        seconds=time.monotonic()-start, log=log.name))
    (output / (label + '-provider-commands.json')).write_text(json.dumps(records, indent=2)+'\n')
    print(label, name, r.returncode, flush=True)
    if r.returncode != expected:
        raise SystemExit('unexpected status: ' + name)


flags = ['--disable-shared', '--enable-static', '--disable-zlib', '--disable-bzlib',
         '--disable-xzlib', '--disable-zstdlib', '--disable-lzlib']
for flavor in ('unpatched', 'sanitized'):
    build = root / ('build/file-' + flavor + '-build')
    build.mkdir(exist_ok=True)
    source = root / 'build/host-file-src'
    environment = None
    if flavor == 'unpatched':
        source = root / 'build/file-unpatched-src'
        source.mkdir(exist_ok=True)
        run('extract', ['tar', '-xzf', root / 'tools/host-profile/vendor/file/file-5.46.tar.gz',
                        '-C', source, '--strip-components=1'])
    else:
        environment = dict(os.environ, CFLAGS='-g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer',
                           LDFLAGS='-fsanitize=address,undefined')
        # Record only build overrides, not the caller's environment.
    build_env = environment
    # Configure inherits the host environment but retained records contain only
    # explicit build flags (no credentials or unrelated environment values).
    if environment is not None:
        build_env = dict(CFLAGS=environment['CFLAGS'], LDFLAGS=environment['LDFLAGS'],
                         PATH=os.environ['PATH'], HOME=os.environ['HOME'])
    run(flavor + '-configure', [source / 'configure', *flags], cwd=build, env=build_env)
    run(flavor + '-build', ['make', '-j4'], cwd=build, env=build_env)
    prefix = output / flavor
    prefix.mkdir(exist_ok=True)
    link = prefix / 'file'
    if link.is_symlink():
        link.unlink()
    link.symlink_to(build / 'src/file')
    search = str(prefix) + ':' + str(root / 'build/host-profile/bin') + ':' + os.defpath
    for selection in (('magic-messages', 'magic') if flavor == 'unpatched' else
                      ('magic-messages', 'magic', 'magic-strings')):
        record = output / (label + '-' + flavor + '-' + selection + '.json')
        run(flavor + '-' + selection,
            [sys.executable, 'tests/host_filesystem.py', './cshell', '--' + selection + '-only',
             '--path', search, '--record', str(record)] + (['--sanitizer'] if flavor == 'sanitized' else []),
            expected=1 if flavor == 'unpatched' else 0)
        compressed = record.with_suffix('.json.gz')
        compressed.write_bytes(gzip.compress(record.read_bytes(), mtime=0))
        record.unlink()
    if flavor == 'sanitized':
        run('sanitized-format-checks', [sys.executable, 'tests/host_file_format_checks.py', build / 'src/file'])
