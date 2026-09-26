"""Record the tested tree from its root, including dirty source/test bytes.

EVIDENCE_REVISION supplies the base revision for Docker (which has no .git).
EVIDENCE_CFLAGS/EVIDENCE_LDFLAGS must match the make invocation for sanitizers.
"""
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import subprocess
import sys


def command(*args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    return {'argv': list(args), 'status': result.returncode, 'output': result.stdout.strip()}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path.cwd()
inputs = [root / 'Makefile']
for directory in ('src', 'include', 'tests'):
    inputs.extend(p for p in (root / directory).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts)
manifest = {str(p.relative_to(root)): sha(p) for p in sorted(inputs)}
binary = root / 'cshell'
identity = {
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'base_revision': os.environ.get('EVIDENCE_REVISION') or command('git', 'rev-parse', 'HEAD')['output'],
    'source_note': 'Tested source/test bytes are identified by the manifest, including uncommitted changes; documentation is outside this digest.',
    'source_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    'source_manifest': manifest,
    'binary': {'path': str(binary), 'realpath': str(binary.resolve()), 'sha256': sha(binary)},
    'compiler': command('cc', '--version'),
    'platform': platform.platform(), 'uname': list(platform.uname()),
    'python': sys.version, 'libc': platform.libc_ver(),
    'long_bits': ctypes.sizeof(ctypes.c_long) * 8,
    'root_login': list(pwd.getpwuid(0)),
    'flags': {'CPPFLAGS': '-D_POSIX_C_SOURCE=200809L -Iinclude',
              'CFLAGS': os.environ.get('EVIDENCE_CFLAGS', '-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2'),
              'LDFLAGS': os.environ.get('EVIDENCE_LDFLAGS', ''), 'LDLIBS': ''},
    'generated_suites': {str(p.relative_to(root)): sha(p)
                         for p in sorted((root / 'build/tests').glob('*.json'))},
    'helpers': {str(p): sha(p) for p in [Path(shutil.which(n)) for n in ('printf', 'cat', 'test', 'sh')]
                + [root / 'build/tests/execute_helper'] if p.is_file()},
}
if sys.platform == 'darwin':
    identity['os_build'] = command('sw_vers')
    identity['libsystem_note'] = 'System shared cache; identity is the macOS/Darwin build above.'
else:
    identity['os_release'] = Path('/etc/os-release').read_text()
    identity['libc_build'] = command('ldd', '--version')
print(json.dumps(identity, indent=2))
