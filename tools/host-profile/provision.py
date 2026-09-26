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


def provision(destination, gnu_bin=None):
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
    (destination.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--gnu-bin', type=Path)
    args = parser.parse_args()
    try:
        provision(args.destination, args.gnu_bin)
    except ValueError as error:
        parser.error(str(error))
