"""CSH-115: ls -s/-k accounting on a measured private object graph.

POSIX leaves the default -s unit and filesystem accounting method to the
implementation. These witnesses select -k and qualify st_blocks accounting on
the supplied filesystems, not shared extents or a portable default unit.
"""
import os
import re
import stat

from host_filesystem_cases import case
from host_filesystem_isolated import measurements as allocation_measurements

NAMES = ('empty', 'regular', 'sparse', 'hard', 'directory', 'fifo', 'symbol')
CONTENT = bytes(range(251)) * 33
SIZE = 262145


def cases():
    for order, flags in (('sk', ['-s', '-k']), ('ks', ['-k', '-s'])):
        for name in NAMES:
            yield case('ls', 'blocks-' + order + '-' + name,
                       ['-1', '-d', *flags, 'blocks/' + name], ticket='CSH-115',
                       ls_blocks=dict(names=[name], follow=False), out='ls-blocks')
        for option in ('-H', '-L'):
            yield case('ls', 'blocks-' + order + '-follow-' + option[1:],
                       ['-1', '-d', *flags, option, 'blocks/symbol'], ticket='CSH-115',
                       ls_blocks=dict(names=['symbol'], follow=True), out='ls-blocks')
        # Each displayed hard-link name has its own count; this is not du's
        # inode deduplication. Supply reversed operands to require C ordering.
        yield case('ls', 'blocks-' + order + '-multiple',
                   ['-1', '-d', *flags, *['blocks/' + n for n in reversed(NAMES)]],
                   ticket='CSH-115', ls_blocks=dict(names=sorted(NAMES), follow=False),
                   out='ls-blocks')


def measurements(root, names):
    result = allocation_measurements(root, names)
    for name, entry in result.items():
        info = (root / name).lstat()
        entry.update(uid=info.st_uid, gid=info.st_gid, mtime_ns=info.st_mtime_ns,
                     ctime_ns=info.st_ctime_ns)
    return result


def setup(directory, row):
    if not row.get('ls_blocks'):
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls block witnesses require one unprivileged identity')
    root = directory / 'blocks'
    root.mkdir()
    (root / 'empty').write_bytes(b'')
    (root / 'regular').write_bytes(CONTENT)
    with (root / 'sparse').open('wb') as stream:
        stream.seek(SIZE - 1)
        stream.write(b'X')
    os.link(root / 'regular', root / 'hard')
    (root / 'directory').mkdir()
    (root / 'directory/leaf').write_bytes(b'preserved\n')
    os.mkfifo(root / 'fifo', 0o600)
    (root / 'symbol').symlink_to('regular')
    before = measurements(root, (*NAMES, 'directory/leaf'))
    for name in NAMES:
        expected_type = {'directory': stat.S_IFDIR, 'fifo': stat.S_IFIFO,
                         'symbol': stat.S_IFLNK}.get(name, stat.S_IFREG)
        if stat.S_IFMT(before[name]['mode']) != expected_type:
            raise OSError('ls block fixture type mismatch')
    regular, hard, sparse = (before[n] for n in ('regular', 'hard', 'sparse'))
    if (regular['device'], regular['inode'], regular['nlink']) != (hard['device'], hard['inode'], 2):
        raise OSError('ls block hard-link probe failed')
    if regular['size'] != len(CONTENT) or regular['blocks'] <= 0:
        raise OSError('ls regular allocation probe failed')
    if sparse['size'] != SIZE or sparse['blocks'] <= 0:
        raise OSError('seek-created allocation probe failed')
    info = (root / 'symbol').stat()
    if (info.st_dev, info.st_ino) != (regular['device'], regular['inode']):
        raise OSError('ls block symlink probe failed')
    spec = row['ls_blocks']
    expected = [(name, (before['regular' if spec['follow'] else name]['blocks'] + 1) // 2)
                for name in spec['names']]
    return dict(before=before, expected=expected, unit_bytes=1024,
                sparse_allocation=sparse['blocks'] * 512 < SIZE,
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat st_blocks in 512-byte units; stat alias identity')


def output_matches(environment, output):
    # Column padding is unspecified; require each full line, count, name and
    # C-locale order, with no total line for -d and no extra/duplicate output.
    pattern = b''.join(rb' *' + str(count).encode() + rb' +blocks/' + name.encode() + rb'\n'
                       for name, count in environment['expected'])
    return re.fullmatch(pattern, output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'blocks'
    after = measurements(root, environment['before'])
    errors = []
    if after != environment['before']:
        return ['ls block fixture metadata changed'], after
    # No FIFO opens. Reads happen only after the allocation/identity snapshot.
    for name, content in (('empty', b''), ('regular', CONTENT), ('hard', CONTENT),
                          ('sparse', b'\0' * (SIZE - 1) + b'X'),
                          ('directory/leaf', b'preserved\n')):
        path = root / name
        if not stat.S_ISREG(path.lstat().st_mode) or path.read_bytes() != content:
            errors.append('ls block fixture bytes changed: ' + name)
    if os.readlink(root / 'symbol') != 'regular':
        errors.append('ls block symlink text changed')
    if sorted(p.name for p in root.iterdir()) != sorted(NAMES) or sorted(
            p.name for p in (root / 'directory').iterdir()) != ['leaf']:
        errors.append('ls block fixture directory entries changed')
    return errors, after
