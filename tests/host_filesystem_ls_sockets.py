"""CSH-118: independently measured ls inode numbers and file-type suffixes.

Private closed AF_UNIX stream/datagram endpoints only. No communication,
device, ACL, terminal, locale, race or resource-limit qualification is implied.
"""
import os
import re
import stat
import socket
import subprocess
import sys
from pathlib import Path

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements

FILES = {'regular': b'preserved\n', 'directory/leaf': b'child\n'}
MODES = {'regular': 0o600, 'directory/leaf': 0o600, 'directory': 0o700,
         'stream': 0o600, 'datagram': 0o700}
SOCKETS = ('stream', 'datagram')
LINKS = {'link-stream': 'stream', 'link-datagram': 'datagram'}
NAMES = tuple(sorted((*MODES.keys(), *LINKS.keys())))
ENTRIES = tuple(n for n in NAMES if '/' not in n)


def bind_sockets(root):
    # Relative bind names avoid sun_path limits caused by the harness temp path.
    # Only this bounded child changes cwd; both descriptors close before exec.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--bind'],
                            cwd=root, capture_output=True, timeout=3)
    if result.returncode != 0 or result.stdout != b'bound-and-closed\n' or result.stderr:
        raise OSError('private socket setup failed: ' + repr(result))
    return dict(status=result.returncode, stdout=result.stdout.hex(),
                stderr=result.stderr.hex(), endpoints=list(SOCKETS), closed_before_exec=True)


def cases():
    for style in ('plain', 'p', 'F'):
        for inode in (False, True):
            for follow in ('physical', 'H', 'L'):
                for graph in ('directory', 'operands'):
                    options = ['-1', *([] if style == 'plain' else ['-' + style]),
                               *(['-i'] if inode else []),
                               *([] if follow == 'physical' else ['-' + follow])]
                    # -d disables the default command-line directory-link
                    # dereference, making the physical inode oracle explicit.
                    operands = (['-d', *['sockets/' + n for n in reversed(ENTRIES)]]
                                if graph == 'operands' else ['-A', 'sockets'])
                    name = f'sockets-{style}-' + ('inode' if inode else 'name') + f'-{follow}-{graph}'
                    yield case('ls', name, options + operands, ticket='CSH-118',
                               ls_sockets=dict(style=style, inode=inode, follow=follow, graph=graph),
                               out='ls-sockets')


def expected_entries(before, spec):
    result = []
    follow = spec['follow'] == 'L' or (spec['follow'] == 'H' and spec['graph'] == 'operands')
    for name in ENTRIES:
        info = before[LINKS[name] if follow and name in LINKS else name]
        mode = info['mode']
        suffix = ''
        if spec['style'] in ('p', 'F') and stat.S_ISDIR(mode):
            suffix = '/'
        elif spec['style'] == 'F':
            if stat.S_ISLNK(mode):
                suffix = '@'
            elif stat.S_ISSOCK(mode):
                suffix = '='
            elif stat.S_ISREG(mode) and mode & 0o111:
                suffix = '*'
        display = ('sockets/' if spec['graph'] == 'operands' else '') + name + suffix
        result.append(dict(name=display, inode=info['inode'] if spec['inode'] else None))
    return result


def setup(directory, row):
    if 'ls_sockets' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls sockets witnesses require one unprivileged identity')
    root = directory / 'sockets'
    root.mkdir()
    (root / 'directory').mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
    binding = bind_sockets(root)
    for name, mode in MODES.items():
        (root / name).chmod(mode)
    for name, target in LINKS.items():
        (root / name).symlink_to(target)
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFLNK if name in LINKS else stat.S_IFDIR if name == 'directory'
                else stat.S_IFSOCK if name in SOCKETS else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls sockets type/inode probe failed')
        if name in MODES and stat.S_IMODE(info['mode']) != MODES[name]:
            raise OSError('ls sockets mode probe failed')
    for name, target in LINKS.items():
        info = (root / name).stat()
        expected = before[target]
        if (info.st_dev, info.st_ino, info.st_mode) != (expected['device'], expected['inode'], expected['mode']):
            raise OSError('ls sockets symlink referent probe failed')
        if before[name]['inode'] == expected['inode']:
            raise OSError('ls sockets link/referent inodes must differ')
    return dict(binding=binding, before=before, entries=expected_entries(before, row['ls_sockets']),
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat inode/type/mode and stat symlink referent identity')


def output_matches(environment, output):
    pattern = b''
    for entry in environment['entries']:
        if entry['inode'] is not None:
            pattern += b' *' + str(entry['inode']).encode() + b' +'
        pattern += re.escape(entry['name'].encode()) + b'\n'
    return re.fullmatch(pattern, output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'sockets'
    after = measurements(root, NAMES)
    if after != environment['before']:
        return ['ls sockets fixture metadata changed'], after
    errors = []
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls sockets fixture bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / name) != target:
            errors.append('ls sockets fixture link changed: ' + name)
    for name, entries in (('', ENTRIES), ('directory', ('leaf',))):
        if sorted(p.name for p in (root / name).iterdir()) != list(entries):
            errors.append('ls sockets fixture entries changed: ' + name)
    return errors, after


if __name__ == '__main__':
    if sys.argv[1:] != ['--bind']:
        raise SystemExit('expected --bind')
    for name, kind in zip(SOCKETS, (socket.SOCK_STREAM, socket.SOCK_DGRAM)):
        with socket.socket(socket.AF_UNIX, kind) as endpoint:
            endpoint.bind(name)
            if endpoint.getsockname() != name:
                raise OSError('bound socket pathname mismatch')
    print('bound-and-closed')
