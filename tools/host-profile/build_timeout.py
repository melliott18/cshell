#!/usr/bin/env python3
"""Explicit, private build of the pinned GNU timeout provider; never install it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '9.11'
URL = f'https://ftp.gnu.org/gnu/coreutils/coreutils-{VERSION}.tar.xz'
ARCHIVE_SHA256 = '394024eda0a5955217ceda9cd1201e65dc8fa3aa29c2951135a49521d57c3cc3'
PATCH = Path(__file__).with_name('timeout-preserve-signal.patch')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(archive=None, jobs=2):
    parent = ROOT / 'build' / 'host-timeout-build'
    parent.mkdir(parents=True, exist_ok=True)
    archive = archive.resolve() if archive else parent / f'coreutils-{VERSION}.tar.xz'
    if not archive.exists():
        # Download to a staging file: interrupted downloads cannot be reused.
        staging = archive.with_suffix('.download')
        subprocess.run(['curl', '--fail', '--location', '--retry', '2', URL,
                        '--output', str(staging)], check=True)
        if sha(staging) != ARCHIVE_SHA256:
            raise ValueError('download checksum mismatch')
        staging.replace(archive)
    if sha(archive) != ARCHIVE_SHA256:
        raise ValueError('coreutils archive checksum mismatch')
    source = parent / f'coreutils-{VERSION}'
    stamp = parent / 'patched-source.sha256'
    patch_hash = sha(PATCH)
    if not stamp.exists() or stamp.read_text().strip() != patch_hash:
        if source.exists():
            raise ValueError(f'unstamped/changed source in {source}; use a fresh build directory')
        # Only the exact hash-pinned upstream release archive is extracted.
        with tarfile.open(archive) as bundle:
            bundle.extractall(parent)
        subprocess.run(['patch', '-p1', '--input', str(PATCH)], cwd=source, check=True)
        stamp.write_text(patch_hash + '\n')
    output = parent / 'objects'
    output.mkdir(exist_ok=True)
    (output / 'csh-provider.mk').write_text(
        'include Makefile\ncsh-built-sources: $(BUILT_SOURCES)\n'
        'csh-print-cc:\n\t@echo $(CC)\n')
    environment = dict(os.environ, FORCE_UNSAFE_CONFIGURE='1', LC_ALL='C')
    configure = [str(source / 'configure'), '--disable-nls', '--disable-acl',
                 '--disable-xattr', '--disable-libcap', '--cache-file=config.cache']
    commands = [configure,
                ['make', f'-j{jobs}', '-f', 'csh-provider.mk', 'csh-built-sources'],
                ['make', f'-j{jobs}', 'src/timeout']]
    log_names = ('configure.log', 'headers.log', 'make.log')
    for command, name in zip(commands, log_names):
        print(f'{command[0]}: see {output / name}', flush=True)
        with (output / name).open('w') as log:
            subprocess.run(command, cwd=output, env=environment, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    executable = ROOT / 'build' / 'host-timeout'
    shutil.copy2(output / 'src' / 'timeout', executable)
    compiler = subprocess.check_output(['make', '-s', '-f', 'csh-provider.mk', 'csh-print-cc'],
                                      cwd=output, env=environment, text=True).strip()
    manifest = dict(upstream=URL, version=VERSION, archive_sha256=sha(archive),
                    patch_sha256=patch_hash, builder_sha256=sha(Path(__file__)),
                    source_sha256=sha(source / 'src' / 'timeout.c'),
                    executable_sha256=sha(executable), platform=platform.platform(),
                    compiler=compiler, commands=commands,
                    license='GPL-3.0-or-later; see retained source COPYING and gnulib licenses',
                    logs={name: sha(output / name) for name in log_names})
    (ROOT / 'build' / 'host-timeout-build.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(executable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use this verified local release archive')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    try:
        build(args.archive, args.jobs)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')
