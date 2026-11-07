#!/usr/bin/env python3
"""Build the pinned standalone M4 provider offline with its upstream build."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
VENDOR = Path(__file__).resolve().parent / 'vendor/m4'


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, default=ROOT)
    root = parser.parse_args().build_root.resolve()
    archive = VENDOR / 'm4-1.4.20.tar.gz'
    provenance = json.loads((VENDOR / 'provenance.json').read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != provenance['archive_sha256']:
        raise SystemExit('M4 source archive does not match pinned provenance')
    destination = root / 'build/host-m4-source'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    # The checked-in archive is authenticated above; no network or host install.
    subprocess.run(['tar', '-xzf', str(archive), '-C', str(destination)], check=True)
    source = destination / 'm4-1.4.20'
    with (VENDOR / 'cshell.patch').open('rb') as patch:
        subprocess.run(['patch', '-p1'], stdin=patch, cwd=source, check=True)
    environment = dict(os.environ, LC_ALL='C')
    requested_flags = environment.get('CFLAGS', '')
    # GNU M4/gnulib use their upstream warning policy. Keep instrumentation,
    # optimization and language flags; do not turn upstream warnings into errors.
    environment['CFLAGS'] = shlex.join(f for f in shlex.split(requested_flags)
                                      if f != '-Werror')
    # Avoid passing a parent make jobserver into subprocesses without its fds.
    environment.pop('MAKEFLAGS', None)
    environment.pop('MFLAGS', None)
    subprocess.run(['./configure', '--disable-nls', '--disable-dependency-tracking', '--with-included-regex'],
                   cwd=source, env=environment, check=True)
    for component in ('lib', 'src'):
        subprocess.run(['make', '-j2', '-C', component], cwd=source,
                       env=environment, check=True)
    executable = root / 'build/host-m4'
    shutil.copy2(source / 'src/m4', executable)
    identity = dict(gnulib_sha256=hashlib.sha256((source/'lib/libm4.a').read_bytes()).hexdigest(), included_regex=True, archive_sha256=provenance['archive_sha256'],
                    patch_sha256=hashlib.sha256((VENDOR/'cshell.patch').read_bytes()).hexdigest(),
                    requested_cflags=requested_flags, cflags=environment['CFLAGS'],
                    cc=environment.get('CC'), ldflags=environment.get('LDFLAGS'),
                    binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
    (root/'build/host-m4-build.json').write_text(json.dumps(identity,indent=2)+'\n')


if __name__ == '__main__':
    main()
