"""Collect tested source/binary identity; run at the repository/image root."""
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def command(*args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return dict(argv=list(args), status=p.returncode, output=p.stdout.strip())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path.cwd()
inputs = [root / 'Makefile']
for directory in ('src', 'include', 'tests'):
    inputs.extend(p for p in (root / directory).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts)
manifest = {str(p.relative_to(root)): sha(p) for p in sorted(inputs)}
identity = {
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_base': os.environ.get('EVIDENCE_SOURCE_BASE', 'daa1be1'),
    'source_note': 'Manifest identifies exact source and suite bytes. Documentation is outside this digest.',
    'source_revision': (command('git', 'rev-parse', 'HEAD') if (root / '.git').exists()
                        else os.environ.get('EVIDENCE_SOURCE_REVISION')),
    'worktree_status': (command('git', 'status', '--short') if (root / '.git').exists() else None),
    'source_manifest': manifest,
    'source_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    'binary': {'path': str(root / 'cshell'), 'realpath': str((root / 'cshell').resolve()),
               'sha256': sha(root / 'cshell')},
    'compiler': command('cc', '--version'),
    'platform': platform.platform(), 'uname': list(platform.uname()),
    'python': sys.version, 'libc': platform.libc_ver(),
    'flags': {'CPPFLAGS': '-D_POSIX_C_SOURCE=200809L -Iinclude',
              'CFLAGS': os.environ.get('EVIDENCE_CFLAGS', '-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2'),
              'LDFLAGS': os.environ.get('EVIDENCE_LDFLAGS', ''), 'LDLIBS': ''},
    'generated_suites': {str(p.relative_to(root)): sha(p)
                         for p in sorted((root / 'build/tests').glob('*.json'))},
    'helpers': {str(p): sha(p) for p in
                [Path('/bin/cat'), Path('/bin/sh'), Path('/bin/mkdir'), Path('/bin/ln'),
                 Path('/usr/bin/printf'), Path('/usr/bin/test'), Path('/bin/ps'),
                 root / 'build/tests/execute_helper', root / 'build/tests/state_builtin_helper']
                if p.exists()},
}
if sys.platform == 'darwin':
    identity['os_build'] = command('sw_vers')
    version = ctypes.CDLL(None).NSVersionOfRunTimeLibrary
    version.argtypes = [ctypes.c_char_p]
    version.restype = ctypes.c_int32
    value = version(b'System')
    identity['runtime_system_library'] = {
        'method': 'NSVersionOfRunTimeLibrary("System")', 'raw': value,
        'version': f'{value >> 16}.{(value >> 8) & 255}.{value & 255}'}
else:
    identity['os_release'] = Path('/etc/os-release').read_text()
    identity['libc_build'] = command('ldd', '--version')
print(json.dumps(identity, indent=2))
