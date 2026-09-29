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
from host_utility_cases import HOSTS


def provision(destination, gnu_bin=None, catalog_bin=None, cc="cc", cflags="-std=c99 -O2 -Wall -Wextra -Wpedantic", cppflags="", ldflags="", ldlibs=""):
    # A failed new setup must not leave an old passing qualification artifact.
    for filename in ('host-catalog-results.json', 'host-catalog-contract-results.json'):
        record = ROOT / 'build/tests' / filename
        if record.exists():
            record.unlink()
    selected = {name: shutil.which(name, path=os.defpath) for name in HOSTS}
    overrides = {'printf': str(ROOT / 'build/host-printf')}
    system = platform.system()
    if system == 'Darwin':
        # Homebrew's prefixed names do not change the system PATH or echo policy.
        search = str(gnu_bin) if gnu_bin else os.environ.get('PATH', os.defpath)
        overrides.update({name: shutil.which('g' + name, path=search)
                         for name in ('test', '[')})
    elif system == 'Linux':
        overrides['kill'] = shutil.which('busybox', path=os.defpath)
    else:
        raise ValueError('Only Darwin and Linux profiles are defined')
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
    config = destination.parent / 'catalog_providers.h'
    # JSON ASCII string quoting is also a C string literal for these paths.
    config.write_text(''.join('#define CATALOG_' + name.upper() + ' ' +
        json.dumps(path, ensure_ascii=True) + '\n' for name, path in catalog_providers.items()))
    adapter_binary = destination.parent / 'catalog-adapter'
    compile_command = shlex.split(cc) + shlex.split(cppflags) + shlex.split(cflags) + shlex.split(ldflags) + ['-I', str(destination.parent),
        str(ROOT / 'tools/host-profile/catalog_adapter.c'), '-o', str(adapter_binary)] + shlex.split(ldlibs)
    subprocess.run(compile_command, check=True, timeout=60)
    manifest = {'system': system, 'path': str(destination), 'executables': {}}
    for name, path in selected.items():
        target = destination / name
        if target.is_symlink():
            target.unlink()
        elif target.exists():
            raise ValueError(f'Refusing to replace non-symlink {target}')
        # Leave ordinary host lookup (notably the PATH-associated pwd builtin)
        # unchanged; only the declared replacements belong in the prefix.
        adapter = None
        if name in catalog_providers:
            adapter = adapter_binary
            target.symlink_to(adapter)
        elif name in overrides:
            target.symlink_to(path)
        manifest['executables'][name] = {
            'override': name in overrides or name in catalog_providers, 'target': str(target) if adapter else path,
            'provider': path, 'adapter': str(adapter) if adapter else None, 'realpath': os.path.realpath(adapter or path),
            'sha256': hashlib.sha256(Path(adapter or path).read_bytes()).hexdigest(),
            'provider_realpath': os.path.realpath(path),
            'provider_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'adapter_build': compile_command if adapter else None}
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
    args = parser.parse_args()
    try:
        provision(args.destination, args.gnu_bin, args.catalog_bin, args.cc, args.cflags, args.cppflags, args.ldflags, args.ldlibs)
    except ValueError as error:
        parser.error(str(error))
