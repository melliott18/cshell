#!/usr/bin/env python3
"""Create an opt-in PATH profile; never replace system executables."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_utility_cases import HOSTS
from host_filesystem_cases import UTILITIES


def test_provider(gnu_bin=None):
    search = str(gnu_bin) if gnu_bin else os.environ.get('PATH', os.defpath)
    path = shutil.which('gtest', path=search) if platform.system() == 'Darwin' else shutil.which('test', path=os.defpath)
    if not path:
        raise ValueError('Missing vendor test provider; Darwin requires Homebrew coreutils')
    return path


def text_overrides(text_bin, system):
    manifest = json.loads((text_bin.parent / 'manifest.json').read_text())
    expected = {'cat', 'head', 'cut', 'tsort', 'sed', 'ed', 'cmp'}
    if system == 'Linux':
        expected.add('tail')
    if set(manifest['executables']) != expected or manifest['recipe']['system'] != system:
        raise ValueError('Text provider manifest does not match this host')
    overrides = {}
    for name in expected:
        candidate = text_bin / name
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != manifest['executables'][name]['sha256']:
            raise ValueError('Text provider checksum mismatch: ' + name)
        overrides[name] = str(candidate.resolve())
    return overrides


def provision(destination, gnu_bin=None, text_bin=None):
    selected = {name: shutil.which(name, path=os.defpath) for name in dict.fromkeys(HOSTS + UTILITIES)}
    overrides = {'write': str(ROOT / 'build/host-write'),
                 'chmod': str(ROOT / 'build/host-chmod'),
                 'newgrp': str(ROOT / 'build/host-newgrp'),
                 'test': str(ROOT / 'build/host-test'), '[': str(ROOT / 'build/host-test'),
                 'ln': str(ROOT / 'build/host-ln'),
                 'mkdir': str(ROOT / 'build/host-mkdir'),
                 'mkfifo': str(ROOT / 'build/host-mkfifo'),
                 'file': str(ROOT / 'build/host-file'),
                 'printf': str(ROOT / 'build/host-printf'),
                 'pax': str(ROOT / 'build/host-pax'),
                 'cp': str(ROOT / 'build/host-cp'),
                 'rm': str(ROOT / 'build/host-rm'),
                 'touch': str(ROOT / 'build/host-touch'),
                 'readlink': str(ROOT / 'build/host-paths'),
                 'realpath': str(ROOT / 'build/host-paths')}
    overrides.update({name: str(ROOT / ('build/host-terminal-' + name))
                      for name in ('stty', 'tabs', 'tput', 'tty', 'mesg', 'who')})
    system = platform.system()
    if system == 'Darwin':
        # Homebrew's prefixed names do not change the system PATH or echo policy.
        search = str(gnu_bin) if gnu_bin else os.environ.get('PATH', os.defpath)
        overrides.update({name: shutil.which('g' + name, path=search)
                         for name in ('find', 'dd')})
    elif system == 'Linux':
        overrides['kill'] = shutil.which('busybox', path=os.defpath)
        overrides['du'] = str(ROOT / 'build/host-du')
        if not os.access('/usr/bin/du', os.X_OK):
            raise ValueError('Missing GNU du backend /usr/bin/du')
    else:
        raise ValueError('Only Darwin and Linux profiles are defined')
    if text_bin:
        overrides.update(text_overrides(text_bin, system))
    selected.update(overrides)
    for name, path in selected.items():
        if not path or not Path(path).is_file() or not os.access(path, os.X_OK):
            raise ValueError(f'Missing executable for {name}; see tools/host-profile/README.md')
    destination = destination.absolute()
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {'system': system, 'path': str(destination), 'executables': {}}
    for name, path in selected.items():
        target = destination / name
        if target.is_symlink():
            target.unlink()
        elif target.exists():
            raise ValueError(f'Refusing to replace non-symlink {target}')
        # Leave ordinary host lookup (notably the PATH-associated pwd builtin)
        # unchanged; only the declared replacements belong in the prefix.
        if name in overrides:
            target.symlink_to(path)
        manifest['executables'][name] = {
            'override': name in overrides, 'target': path, 'realpath': os.path.realpath(path),
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    if system == 'Linux':
        manifest['executables']['du']['backend'] = dict(
            path='/usr/bin/du', realpath=os.path.realpath('/usr/bin/du'),
            sha256=hashlib.sha256(Path('/usr/bin/du').read_bytes()).hexdigest(),
            environment={'POSIXLY_CORRECT': '1'})
    for program, patch in (('cp', 'cp-decline-status.patch'), ('rm', 'rm-parent-prompt.patch')):
        manifest['executables'][program]['source'] = dict(
            version='GNU coreutils 9.7', archive='tools/host-profile/vendor/coreutils/coreutils-9.7.tar.xz',
            archive_sha256=hashlib.sha256((ROOT / 'tools/host-profile/vendor/coreutils/coreutils-9.7.tar.xz').read_bytes()).hexdigest(),
            patch_sha256=hashlib.sha256((ROOT / 'tools/host-profile/vendor/coreutils' / patch).read_bytes()).hexdigest(),
            configure=['--disable-nls', '--disable-acl', '--without-selinux', '--without-libgmp'])
    for program in ('mkdir', 'mkfifo'):
        manifest['executables'][program]['source'] = dict(
            version='GNU coreutils 9.7',
            archive=manifest['executables']['cp']['source']['archive'],
            archive_sha256=manifest['executables']['cp']['source']['archive_sha256'],
            configure=manifest['executables']['cp']['source']['configure'],
            build_targets=['src/mkdir', 'src/mkfifo'],
            log='build/host-coreutils-build/creation.log',
            scope='unmodified creation utilities from the shared pinned source build')
    manifest['executables']['ln']['source'] = dict(
        version='GNU coreutils 9.7',
        archive=manifest['executables']['cp']['source']['archive'],
        archive_sha256=manifest['executables']['cp']['source']['archive_sha256'],
        configure=manifest['executables']['cp']['source']['configure'],
        build_targets=['src/ln'], log='build/host-coreutils-build/ln.log',
        scope='unmodified ln from the shared pinned source build')
    manifest['executables']['touch']['source'] = dict(
        version='GNU coreutils 9.7 + IANA tzcode 2025b',
        coreutils_archive_sha256=manifest['executables']['cp']['source']['archive_sha256'],
        tzcode_archive='tools/host-profile/vendor/tzcode/tzcode2025b.tar.gz',
        tzcode_archive_sha256=hashlib.sha256((ROOT / 'tools/host-profile/vendor/tzcode/tzcode2025b.tar.gz').read_bytes()).hexdigest(),
        build_script_sha256=hashlib.sha256((ROOT / 'tools/host-profile/build-touch.sh').read_bytes()).hexdigest(),
        tzcode_flags=['-DHAVE_TZNAME=1', '-DUSG_COMPAT=1', '-DNETBSD_INSPIRED=0'],
        configure=manifest['executables']['cp']['source']['configure'])
    manifest['executables']['file']['source'] = dict(
        version='file 5.46 + CSH-103/104 message and numeric type repairs',
        archive='tools/host-profile/vendor/file/file-5.46.tar.gz',
        archive_sha256=hashlib.sha256((ROOT / 'tools/host-profile/vendor/file/file-5.46.tar.gz').read_bytes()).hexdigest(),
        patch_sha256=hashlib.sha256((ROOT / 'tools/host-profile/vendor/file/message-formats.patch').read_bytes()).hexdigest(),
        build_script_sha256=hashlib.sha256((ROOT / 'tools/host-profile/build-file.sh').read_bytes()).hexdigest(),
        magic_database_sha256=hashlib.sha256((ROOT / 'build/host-file-install/share/misc/magic.mgc').read_bytes()).hexdigest(),
        configure=['--disable-shared', '--enable-static', '--disable-zlib', '--disable-bzlib',
                   '--disable-xzlib', '--disable-zstdlib', '--disable-lzlib'])
    backend = json.loads((ROOT / 'build/host-test-provider.h').read_text().removeprefix('#define CSH_TEST_PROVIDER ').strip())
    manifest['test_backend'] = dict(path=backend, realpath=os.path.realpath(backend),
                                    sha256=hashlib.sha256(Path(backend).read_bytes()).hexdigest())
    backend = json.loads((ROOT / 'build/host-newgrp-provider.h').read_text().removeprefix('#define CSH_NEWGRP_PROVIDER ').strip())
    manifest['newgrp_backend'] = dict(path=backend, realpath=os.path.realpath(backend),
                                      sha256=hashlib.sha256(Path(backend).read_bytes()).hexdigest())
    (destination.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--gnu-bin', type=Path)
    parser.add_argument('--text-bin', type=Path)
    parser.add_argument('--test-header', action='store_true')
    parser.add_argument('--newgrp-header', action='store_true')
    args = parser.parse_args()
    try:
        if args.test_header or args.newgrp_header:
            backend = shutil.which('newgrp', path=os.defpath) if args.newgrp_header else test_provider(args.gnu_bin)
            if not backend:
                raise ValueError('Missing newgrp provider in system path')
            macro = 'CSH_NEWGRP_PROVIDER' if args.newgrp_header else 'CSH_TEST_PROVIDER'
            content = '#define ' + macro + ' ' + json.dumps(backend) + '\n'
            args.destination.parent.mkdir(parents=True, exist_ok=True)
            if not args.destination.exists() or args.destination.read_text() != content:
                args.destination.write_text(content)
        else:
            provision(args.destination, args.gnu_bin, args.text_bin)
    except ValueError as error:
        parser.error(str(error))
