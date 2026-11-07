#!/usr/bin/env python3
"""Build the pinned standalone Awk provider offline with its upstream build."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
VENDOR = Path(__file__).resolve().parent / 'vendor/gawk'


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, default=ROOT)
    root = parser.parse_args().build_root.resolve()
    archive = VENDOR / 'gawk-5.3.2.tar.xz'
    provenance = json.loads((VENDOR / 'provenance.json').read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != provenance['archive_sha256']:
        raise SystemExit('Awk source archive does not match pinned provenance')
    destination = root / 'build/host-awk-source'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    # The checked-in archive is authenticated above; no network or host install.
    subprocess.run(['tar', '-xf', str(archive), '-C', str(destination)], check=True)
    source = destination / 'gawk-5.3.2'
    with (VENDOR / 'cshell.patch').open('rb') as patch:
        subprocess.run(['patch', '-p1'], stdin=patch, cwd=source, check=True)
    environment = dict(os.environ, LC_ALL='C')
    requested_flags = environment.get('CFLAGS', '')
    # GNU Awk uses its upstream warning policy. Keep instrumentation,
    # optimization and language flags; do not turn upstream warnings into errors.
    environment['CFLAGS'] = shlex.join(f for f in shlex.split(requested_flags)
                                      if f != '-Werror')
    # Avoid passing a parent make jobserver into subprocesses without its fds.
    environment.pop('MAKEFLAGS', None)
    environment.pop('MFLAGS', None)
    subprocess.run(['./configure', '--disable-nls', '--disable-extensions', '--without-readline', '--without-mpfr', '--without-gmp'],
                   cwd=source, env=environment, check=True)
    subprocess.run(['make', '-j2'], cwd=source, env=environment, check=True)
    executable = root / 'build/host-awk'
    shutil.copy2(source / 'gawk', executable)
    identity = dict(archive_sha256=provenance['archive_sha256'],
                    patch_sha256=hashlib.sha256((VENDOR/'cshell.patch').read_bytes()).hexdigest(),
                    requested_cflags=requested_flags, cflags=environment['CFLAGS'],
                    cc=environment.get('CC'), ldflags=environment.get('LDFLAGS'),
                    binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
    (root/'build/host-awk-build.json').write_text(json.dumps(identity,indent=2)+'\n')


if __name__ == '__main__':
    main()
