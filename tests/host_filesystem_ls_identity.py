"""CSH-117: independently measured ls inode numbers and file-type suffixes.

Private ordinary objects only. No socket/device, ACL, terminal layout, namespace
race, non-C locale or filesystem/resource exhaustion qualification is implied.
"""
import os
import re
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements

FILES = {'.hidden': b'hidden\n', 'regular': b'regular\n',
         'exec-user': b'user\n', 'exec-group': b'group\n', 'exec-other': b'other\n',
         'directory/leaf': b'preserved\n'}
MODES = {'.hidden': 0o600, 'regular': 0o600, 'exec-user': 0o700,
         'exec-group': 0o610, 'exec-other': 0o601, 'directory/leaf': 0o600,
         'directory': 0o700, 'fifo': 0o600, 'hard': 0o600}
LINKS = {'link-file': 'regular', 'link-dir': 'directory',
         'link-exec': 'exec-user', 'link-fifo': 'fifo'}
NAMES = tuple(sorted((*MODES.keys(), *LINKS.keys())))
ENTRIES = tuple(n for n in NAMES if '/' not in n)


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
                    operands = (['-d', *['identity/' + n for n in reversed(ENTRIES)]]
                                if graph == 'operands' else ['-A', 'identity'])
                    name = f'identity-{style}-' + ('inode' if inode else 'name') + f'-{follow}-{graph}'
                    yield case('ls', name, options + operands, ticket='CSH-117',
                               ls_identity=dict(style=style, inode=inode, follow=follow, graph=graph),
                               out='ls-identity')


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
            elif stat.S_ISFIFO(mode):
                suffix = '|'
            elif stat.S_ISREG(mode) and mode & 0o111:
                suffix = '*'
        display = ('identity/' if spec['graph'] == 'operands' else '') + name + suffix
        result.append(dict(name=display, inode=info['inode'] if spec['inode'] else None))
    return result


def setup(directory, row):
    if 'ls_identity' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls identity witnesses require one unprivileged identity')
    root = directory / 'identity'
    root.mkdir()
    (root / 'directory').mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
    os.link(root / 'regular', root / 'hard')
    os.mkfifo(root / 'fifo', 0o600)
    for name, mode in MODES.items():
        (root / name).chmod(mode)
    for name, target in LINKS.items():
        (root / name).symlink_to(target)
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFLNK if name in LINKS else stat.S_IFDIR if name == 'directory'
                else stat.S_IFIFO if name == 'fifo' else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls identity type/inode probe failed')
        if name in MODES and stat.S_IMODE(info['mode']) != MODES[name]:
            raise OSError('ls identity mode probe failed')
    regular, hard = (before[n] for n in ('regular', 'hard'))
    if (regular['device'], regular['inode'], regular['nlink']) != (hard['device'], hard['inode'], 2):
        raise OSError('ls identity hard-link probe failed')
    for name, target in LINKS.items():
        info = (root / name).stat()
        expected = before[target]
        if (info.st_dev, info.st_ino, info.st_mode) != (expected['device'], expected['inode'], expected['mode']):
            raise OSError('ls identity symlink referent probe failed')
        if before[name]['inode'] == expected['inode']:
            raise OSError('ls identity link/referent inodes must differ')
    return dict(before=before, entries=expected_entries(before, row['ls_identity']),
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
    root = directory / 'identity'
    after = measurements(root, NAMES)
    if after != environment['before']:
        return ['ls identity fixture metadata changed'], after
    errors = []
    for name, content in {**FILES, 'hard': FILES['regular']}.items():
        if (root / name).read_bytes() != content:
            errors.append('ls identity fixture bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / name) != target:
            errors.append('ls identity fixture link changed: ' + name)
    for name, entries in (('', ENTRIES), ('directory', ('leaf',))):
        if sorted(p.name for p in (root / name).iterdir()) != list(entries):
            errors.append('ls identity fixture entries changed: ' + name)
    return errors, after
