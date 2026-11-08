#!/usr/bin/env python3
"""Create an opt-in PATH profile; never replace system executables."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from host_utility_cases import HOSTS
from build_iconv import build as build_iconv
from host_filesystem_cases import UTILITIES
from host_language_cases import UTILITIES as LANGUAGE_UTILITIES


def test_provider(gnu_bin=None):
    search = str(gnu_bin) if gnu_bin else os.environ.get('PATH', os.defpath)
    path = shutil.which('gtest', path=search) if platform.system() == 'Darwin' else shutil.which('test', path=os.defpath)
    if not path:
        raise ValueError('Missing vendor test provider; Darwin requires Homebrew coreutils')
    return path


def text_overrides(text_bin, system):
    manifest = json.loads((text_bin.parent / 'manifest.json').read_text())
    expected = {'cat', 'head', 'cut', 'tsort', 'paste', 'sed', 'ed', 'cmp',
                'expand', 'unexpand', 'fold', 'uniq', 'wc'}
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


def provision(destination, gnu_bin=None, text_bin=None, catalog_bin=None, cc="cc", cflags="-std=c99 -O2 -Wall -Wextra -Wpedantic", cppflags="", ldflags="", ldlibs=""):
    # A failed new setup must not leave an old passing qualification artifact.
    for filename in ('host-catalog-results.json', 'host-catalog-contract-results.json'):
        record = ROOT / 'build/tests' / filename
        if record.exists():
            record.unlink()
    selected = {name: shutil.which(name, path=os.defpath) for name in dict.fromkeys(HOSTS + UTILITIES + LANGUAGE_UTILITIES)}
    overrides = {'bc': str(ROOT / 'build/host-bc'),
                 'awk': str(ROOT / 'build/host-awk'),
                 'uudecode': str(ROOT / 'build/host-uudecode'),
                 'ed': str(ROOT / 'build/host-ed'),
                 'xargs': str(ROOT / 'build/host-xargs'),
                 'm4': str(ROOT / 'build/host-m4'),
                 'patch': str(ROOT / 'build/host-patch'),
                 'write': str(ROOT / 'build/host-write'),
                 'chmod': str(ROOT / 'build/host-chmod'),
                 'newgrp': str(ROOT / 'build/host-newgrp'),
                 'test': str(ROOT / 'build/host-test'), '[': str(ROOT / 'build/host-test'),
                 'ln': str(ROOT / 'build/host-ln'),
                 'ls': str(ROOT / 'build/host-ls'),
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
                         for name in ('find', 'dd', 'expr')})
    elif system == 'Linux':
        overrides['mv'] = str(ROOT / 'build/host-mv')
        overrides['kill'] = shutil.which('busybox', path=os.defpath)
        overrides['du'] = str(ROOT / 'build/host-du')
        if not os.access('/usr/bin/du', os.X_OK):
            raise ValueError('Missing GNU du backend /usr/bin/du')
    else:
        raise ValueError('Only Darwin and Linux profiles are defined')
    if text_bin:
        overrides.update(text_overrides(text_bin, system))
        # Keep the shared GNU-regex ed repair even with optional text overrides.
        overrides['ed'] = str(ROOT / 'build/host-ed')
    # Catalog programs are selected explicitly; no host install is performed.
    search = str(catalog_bin) if catalog_bin else os.environ.get('PATH', os.defpath)
    catalog_providers = {name: shutil.which(name, path=search)
                         for name in ('gettext', 'msgfmt', 'ngettext')}
    for name, path in catalog_providers.items():
        if not path:
            raise ValueError(f'Missing GNU {name}; supply gettext package or --catalog-bin')
        if destination.absolute() in Path(path).absolute().parents:
            raise ValueError('Catalog provider search must not select this profile itself')
    selected.update({name: shutil.which(name, path=os.defpath)
                     for name in ('gencat', 'iconv', 'locale', 'localedef')})
    selected.update(catalog_providers)
    selected.update(overrides)
    for name, path in selected.items():
        if not path or not Path(path).is_file() or not os.access(path, os.X_OK):
            raise ValueError(f'Missing executable for {name}; see tools/host-profile/README.md')
    destination = destination.absolute()
    destination.mkdir(parents=True, exist_ok=True)
    iconv_record = build_iconv(destination.parent, cc, cppflags, cflags, ldflags)
    config = destination.parent / 'catalog_providers.h'
    # JSON ASCII string quoting is also a C string literal for these paths.
    config.write_text(''.join('#define CATALOG_' + name.upper() + ' ' +
        json.dumps(path, ensure_ascii=True) + '\n'
        for name, path in dict(catalog_providers, locale=selected['locale'], iconv=iconv_record['path'],
                               system_iconv=selected['iconv']).items()))
    adapter_binary = destination.parent / 'catalog-adapter'
    compile_command = shlex.split(cc) + shlex.split(cppflags) + shlex.split(cflags) + shlex.split(ldflags) + ['-I', str(destination.parent),
        str(ROOT / 'tools/host-profile/catalog_adapter.c'), '-o', str(adapter_binary)] + shlex.split(ldlibs)
    subprocess.run(compile_command, check=True, timeout=60)
    locale_adapter = destination.parent / 'locale-adapter'
    locale_compile = shlex.split(cc) + shlex.split(cppflags) + shlex.split(cflags) + shlex.split(ldflags) + ['-I', str(destination.parent),
        str(ROOT / 'tools/host-profile/locale_adapter.c'), '-o', str(locale_adapter)] + shlex.split(ldlibs)
    subprocess.run(locale_compile, check=True, timeout=60)
    compiler = shlex.split(cc) + shlex.split(cppflags) + shlex.split(cflags) + shlex.split(ldflags)
    extra_adapters = {}
    for utility, source in (('gencat', 'gencat_darwin.c' if system == 'Darwin' else 'gencat_glibc.c'),
                            ('iconv', 'iconv_adapter.c')):
        binary = destination.parent / (utility + '-adapter')
        command = compiler + ['-D_DEFAULT_SOURCE', '-D_POSIX_C_SOURCE=200809L',
            '-I', str(destination.parent), '-I', str(ROOT / 'tools/host-profile/vendor/gencat-glibc'),
            str(ROOT / 'tools/host-profile' / source), '-o', str(binary)] + shlex.split(ldlibs)
        subprocess.run(command, check=True, timeout=60)
        extra_adapters[utility] = (binary, command)
    manifest = {'system': system, 'path': str(destination), 'executables': {}, 'libiconv': iconv_record}
    for name, path in selected.items():
        target = destination / name
        if target.is_symlink():
            target.unlink()
        elif target.exists():
            raise ValueError(f'Refusing to replace non-symlink {target}')
        # Leave ordinary host lookup (notably the PATH-associated pwd builtin)
        # unchanged; only the declared replacements belong in the prefix.
        adapter = None
        if name in extra_adapters:
            adapter = extra_adapters[name][0]
            target.symlink_to(adapter)
        elif name == 'locale':
            adapter = locale_adapter
            target.symlink_to(adapter)
        elif name in catalog_providers:
            adapter = adapter_binary
            target.symlink_to(adapter)
        elif name in overrides:
            target.symlink_to(path)
        primary = iconv_record['path'] if name == 'iconv' else str(adapter) if name == 'gencat' else path
        manifest['executables'][name] = {
            'override': name in overrides or adapter is not None, 'target': str(target) if adapter else path,
            'provider': primary, 'adapter': str(adapter) if adapter else None, 'realpath': os.path.realpath(adapter or path),
            'sha256': hashlib.sha256(Path(adapter or path).read_bytes()).hexdigest(),
            'provider_realpath': os.path.realpath(primary),
            'provider_sha256': hashlib.sha256(Path(primary).read_bytes()).hexdigest(),
            'system_provider': dict(path=path, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
                               if name in ('gencat', 'iconv') else None,
            'adapter_build': (extra_adapters[name][1] if name in extra_adapters else
                              locale_compile if name == 'locale' else compile_command) if adapter else None}
    manifest['gencat_sources'] = json.loads((ROOT / 'tools/host-profile/vendor/catalog-provenance.json').read_text())
    if system == 'Linux':
        manifest['executables']['du']['backend'] = dict(
            path='/usr/bin/du', realpath=os.path.realpath('/usr/bin/du'),
            sha256=hashlib.sha256(Path('/usr/bin/du').read_bytes()).hexdigest(),
            environment={'POSIXLY_CORRECT': '1'})
    coreutils_patches = [('cp', 'cp-decline-status.patch'), ('rm', 'rm-parent-prompt.patch')]
    if system == 'Linux':
        coreutils_patches.append(('mv', 'cp-decline-status.patch'))
    for program, patch in coreutils_patches:
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
    manifest['executables']['ls']['source'] = dict(
        version='GNU coreutils 9.7',
        archive=manifest['executables']['cp']['source']['archive'],
        archive_sha256=manifest['executables']['cp']['source']['archive_sha256'],
        configure=manifest['executables']['cp']['source']['configure'],
        build_targets=['src/ls'], log='build/host-coreutils-build/ls.log',
        scope='unmodified ls from the shared pinned source build')
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
    parser.add_argument('--catalog-bin', type=Path)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--cppflags', default='')
    parser.add_argument('--ldflags', default='')
    parser.add_argument('--ldlibs', default='')
    parser.add_argument('--cflags', default='-std=c99 -O2 -Wall -Wextra -Wpedantic')
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
            provision(args.destination, args.gnu_bin, args.text_bin, args.catalog_bin, args.cc, args.cflags, args.cppflags, args.ldflags, args.ldlibs)
    except ValueError as error:
        parser.error(str(error))
