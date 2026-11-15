"""CSH-122: literal and -q ls rendering of authored C-locale filenames.

ASCII only: all non-NUL control characters, printable punctuation and spaces.
Sorting uses original names, before replacement; output never supplies an oracle.
"""
import os
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements
from host_filesystem_ls_identity import output_matches

DIRECTORY = 'dir\nname'
FIFO = 'fifo\tname'
EXECUTABLE = 'exec\rname'
LINK = 'link\x1bname'
FILES = {'control-' + chr(n): bytes([n]) for n in (*range(1, 32), 127)}
FILES.update({'control-?': b'literal question mark', ' space ': b'spaces',
              "quote'\"$`*?[\\": b'punctuation', EXECUTABLE: b'executable',
              DIRECTORY + '/guard': b'not listed'})
ENTRIES = tuple(sorted([n for n in FILES if '/' not in n] + [DIRECTORY, FIFO, LINK]))
NAMES = (*FILES, DIRECTORY, FIFO, LINK)


def cases():
    for graph in ('directory', 'operands'):
        for quote in (False, True):
            for style in ('plain', 'F', 'p'):
                for inode in (False, True):
                    for reverse in (False, True):
                        options = ['-1', *(['-q'] if quote else []),
                                   *([] if style == 'plain' else ['-' + style]),
                                   *(['-i'] if inode else []), *(['-r'] if reverse else [])]
                        operands = (['names'] if graph == 'directory' else
                                    ['-d', *['names/' + n for n in reversed(ENTRIES)]])
                        yield case('ls', f'names-{graph}-{int(quote)}-{style}-{int(inode)}-{int(reverse)}',
                                   options + operands, ticket='CSH-122', out='ls-names',
                                   ls_names=dict(graph=graph, quote=quote, style=style,
                                                 inode=inode, reverse=reverse))


def expected_entries(before, spec):
    entries = []
    for name in sorted(ENTRIES, reverse=spec['reverse']):
        # C-locale ASCII print is 0x20..0x7e, with tab explicitly covered by -q.
        display = ''.join('?' if ord(c) < 32 or ord(c) == 127 else c for c in name) if spec['quote'] else name
        if spec['graph'] == 'operands':
            display = 'names/' + display
        mode = before[name]['mode']
        if spec['style'] in ('F', 'p') and stat.S_ISDIR(mode):
            display += '/'
        elif spec['style'] == 'F':
            if stat.S_ISLNK(mode):
                display += '@'
            elif stat.S_ISFIFO(mode):
                display += '|'
            elif stat.S_ISREG(mode) and mode & 0o111:
                display += '*'
        entries.append(dict(name=display, inode=before[name]['inode'] if spec['inode'] else None))
    return entries


def setup(directory, row):
    if 'ls_names' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls name witnesses require one unprivileged identity')
    root = directory / 'names'
    root.mkdir()
    (root / DIRECTORY).mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
        (root / name).chmod(0o700 if name == EXECUTABLE else 0o600)
    os.mkfifo(root / FIFO, 0o600)
    (root / LINK).symlink_to(DIRECTORY)
    if sorted(os.listdir(root)) != list(ENTRIES):
        raise OSError('authored filename bytes were not preserved')
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFDIR if name == DIRECTORY else stat.S_IFIFO if name == FIFO
                else stat.S_IFLNK if name == LINK else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls name type/inode probe failed')
        if name in FILES and stat.S_IMODE(info['mode']) != (0o700 if name == EXECUTABLE else 0o600):
            raise OSError('ls name authored mode probe failed')
    target = (root / LINK).stat()
    if (target.st_dev, target.st_ino, target.st_mode) != tuple(before[DIRECTORY][k] for k in ('device', 'inode', 'mode')):
        raise OSError('ls name symlink referent probe failed')
    return dict(before=before, entries=expected_entries(before, row['ls_names']),
                uid=os.getuid(), euid=os.geteuid(),
                probe='authored ASCII names with pre-exec listdir/lstat and stat referent probes')


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'names'
    after = measurements(root, NAMES)
    errors = []
    if after != environment['before']:
        errors.append('ls name metadata changed')
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls name bytes changed: ' + name)
    if os.readlink(root / LINK) != DIRECTORY:
        errors.append('ls name symlink changed')
    if sorted(os.listdir(root)) != list(ENTRIES) or os.listdir(root / DIRECTORY) != ['guard']:
        errors.append('ls name directory entries changed')
    return errors, after
