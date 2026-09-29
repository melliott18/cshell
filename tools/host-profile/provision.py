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


def test_provider(gnu_bin=None):
    search = str(gnu_bin) if gnu_bin else os.environ.get('PATH', os.defpath)
    path = shutil.which('gtest', path=search) if platform.system() == 'Darwin' else shutil.which('test', path=os.defpath)
    if not path:
        raise ValueError('Missing vendor test provider; Darwin requires Homebrew coreutils')
    return path


def provision(destination, gnu_bin=None):
    selected = {name: shutil.which(name, path=os.defpath) for name in HOSTS}
    overrides = {'printf': str(ROOT / 'build/host-printf'),
                 'test': str(ROOT / 'build/host-test'), '[': str(ROOT / 'build/host-test')}
    system = platform.system()
    if system == 'Linux':
        overrides['kill'] = shutil.which('busybox', path=os.defpath)
    elif system != 'Darwin':
        raise ValueError('Only Darwin and Linux profiles are defined')
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
    backend = json.loads((ROOT / 'build/host-test-provider.h').read_text().removeprefix('#define CSH_TEST_PROVIDER ').strip())
    manifest['test_backend'] = dict(path=backend, realpath=os.path.realpath(backend),
                                    sha256=hashlib.sha256(Path(backend).read_bytes()).hexdigest())
    (destination.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--gnu-bin', type=Path)
    parser.add_argument('--test-header', action='store_true')
    args = parser.parse_args()
    try:
        if args.test_header:
            content = '#define CSH_TEST_PROVIDER ' + json.dumps(test_provider(args.gnu_bin)) + '\n'
            args.destination.parent.mkdir(parents=True, exist_ok=True)
            if not args.destination.exists() or args.destination.read_text() != content:
                args.destination.write_text(content)
        else:
            provision(args.destination, args.gnu_bin)
    except ValueError as error:
        parser.error(str(error))
