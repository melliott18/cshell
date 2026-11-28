"""CSH-119: hidden entries and dot-directory identities on a private tree."""
import os
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements
from host_filesystem_ls_identity import output_matches

FILES = {'.hidden': b'hidden\n', 'visible': b'visible\n',
         '.hidden-dir/leaf': b'private\n', 'directory/leaf': b'child\n'}
ENTRIES = ('.hidden', '.hidden-dir', '.link', 'directory', 'visible')
NAMES = ('.', '..', *ENTRIES, '.hidden-dir/leaf', 'directory/leaf')


def cases():
    for selection in ('default', 'A', 'a'):
        for reverse in (False, True):
            for rendering in ('plain', 'inode', 'F', 'p'):
                options = ['-1', *([] if selection == 'default' else ['-' + selection]),
                           *(['-r'] if reverse else []),
                           *([] if rendering == 'plain' else ['-i' if rendering == 'inode' else '-' + rendering])]
                yield case('ls', f'visibility-{selection}-{int(reverse)}-{rendering}',
                           [*options, 'visibility/listing'], ticket='CSH-119',
                           ls_visibility=dict(selection=selection, reverse=reverse, rendering=rendering),
                           out='ls-visibility')


def setup(directory, row):
    if 'ls_visibility' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls visibility requires one unprivileged identity')
    root = directory / 'visibility/listing'
    root.mkdir(parents=True)
    for name in ('.hidden-dir', 'directory'):
        (root / name).mkdir()
    for name, data in FILES.items():
        (root / name).write_bytes(data)
    (root / '.link').symlink_to('visible')
    before = measurements(root, NAMES)
    for name in NAMES:
        kind = (stat.S_IFDIR if name in ('.', '..', '.hidden-dir', 'directory')
                else stat.S_IFLNK if name == '.link' else stat.S_IFREG)
        if stat.S_IFMT(before[name]['mode']) != kind or before[name]['inode'] <= 0:
            raise OSError('ls visibility type/inode probe failed')
    if before['.']['inode'] == before['..']['inode']:
        raise OSError('private child and parent must have distinct inodes')
    spec = row['ls_visibility']
    names = list(ENTRIES)
    if spec['selection'] == 'default':
        names = [n for n in names if not n.startswith('.')]
    elif spec['selection'] == 'a':
        names += ['.', '..']
    entries = []
    for name in sorted(names, reverse=spec['reverse']):
        suffix = ''
        if spec['rendering'] in ('F', 'p') and stat.S_ISDIR(before[name]['mode']):
            suffix = '/'
        elif spec['rendering'] == 'F' and name == '.link':
            suffix = '@'
        entries.append(dict(name=name + suffix,
                            inode=before[name]['inode'] if spec['rendering'] == 'inode' else None))
    return dict(before=before, entries=entries, uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat type/inode including distinct private dot and dot-dot directories')


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'visibility/listing'
    after = measurements(root, NAMES)
    errors = []
    if after != environment['before']:
        errors.append('ls visibility metadata changed')
    for name, data in FILES.items():
        if (root / name).read_bytes() != data:
            errors.append('ls visibility bytes changed: ' + name)
    if os.readlink(root / '.link') != 'visible':
        errors.append('ls visibility link changed')
    for path, names in ((root, ENTRIES), (root.parent, ('listing',)),
                        (root / '.hidden-dir', ('leaf',)), (root / 'directory', ('leaf',))):
        if sorted(p.name for p in path.iterdir()) != sorted(names):
            errors.append('ls visibility entries changed: ' + str(path))
    return errors, after
