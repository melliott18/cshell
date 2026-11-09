"""CSH-116: measured ls directory totals, selection and recursive sections.

Qualifies st_blocks accounting with explicit 1024-byte units on private graphs.
No provider output supplies the oracle; no shared-extent/capacity claim is made.
"""
import os
import re
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements

FILES = {'tree/empty': b'', 'tree/regular': b'allocated\n' * 1025,
         'tree/.hidden': b'hidden\n' * 2049, 'tree/child/leaf': b'leaf\n',
         'tree/child/.secret': b'secret\n' * 1025}
DIRECTORIES = ('vacant', 'tree', 'tree/child')
LINKS = {'tree/symbol': 'regular'}
NAMES = (*DIRECTORIES, *FILES, 'tree/hard', 'tree/fifo', *LINKS)
ENTRIES = {'vacant': [], 'tree': ['.hidden', 'child', 'empty', 'fifo', 'hard', 'regular', 'symbol'],
           'tree/child': ['.secret', 'leaf']}


def cases():
    for order, flags in (('sk', ['-s', '-k']), ('ks', ['-k', '-s'])):
        for hidden in (False, True):
            for follow in (False, True):
                for graph in ('empty', 'single', 'multiple', 'recursive'):
                    options = [*flags, '-1', *(['-A'] if hidden else []),
                               *(['-L'] if follow else []), *(['-R'] if graph == 'recursive' else [])]
                    operands = {'empty': ['totals/vacant'], 'single': ['totals/tree'],
                                'multiple': ['totals/vacant', 'totals/tree'],
                                'recursive': ['totals/tree']}[graph]
                    name = f'totals-{order}-' + ('hidden' if hidden else 'visible')
                    name += '-' + ('logical' if follow else 'physical') + '-' + graph
                    yield case('ls', name, options + operands, ticket='CSH-116',
                               ls_totals=dict(hidden=hidden, follow=follow, graph=graph), out='ls-totals')


def expected_sections(before, spec):
    directories = {'empty': ['vacant'], 'single': ['tree'],
                   'multiple': ['tree', 'vacant'], 'recursive': ['tree', 'tree/child']}[spec['graph']]
    sections = []
    for directory in directories:
        names = [n for n in ENTRIES[directory] if spec['hidden'] or not n.startswith('.')]
        blocks = []
        for name in names:
            path = directory + '/' + name
            if spec['follow'] and path in LINKS:
                path = 'tree/regular'
            blocks.append(before[path]['blocks'])
        # Sum raw kernel units before rounding. Hard-link names each contribute;
        # do not deduplicate inodes or include the directory itself or descendants.
        sections.append(dict(directory='totals/' + directory, total=(sum(blocks) + 1) // 2,
                             entries=[(n, (b + 1) // 2) for n, b in zip(names, blocks)],
                             header=('optional' if spec['graph'] == 'recursive' and directory == 'tree'
                                     else spec['graph'] in ('multiple', 'recursive'))))
    return sections


def setup(directory, row):
    if 'ls_totals' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls total witnesses require one unprivileged identity')
    root = directory / 'totals'
    root.mkdir()
    for name in DIRECTORIES:
        (root / name).mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
    os.link(root / 'tree/regular', root / 'tree/hard')
    os.mkfifo(root / 'tree/fifo', 0o600)
    for name, target in LINKS.items():
        (root / name).symlink_to(target)
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = stat.S_IFDIR if name in DIRECTORIES else stat.S_IFLNK if name in LINKS else stat.S_IFIFO if name == 'tree/fifo' else stat.S_IFREG
        if stat.S_IFMT(info['mode']) != kind or info['blocks'] < 0:
            raise OSError('ls total fixture metadata probe failed')
    regular, hard = (before[n] for n in ('tree/regular', 'tree/hard'))
    if (regular['device'], regular['inode'], regular['nlink']) != (hard['device'], hard['inode'], 2):
        raise OSError('ls total hard-link probe failed')
    for name, content in FILES.items():
        if before[name]['size'] != len(content) or (content and before[name]['blocks'] <= 0):
            raise OSError('ls total regular allocation probe failed')
    target = (root / 'tree/symbol').stat()
    if (target.st_dev, target.st_ino) != (regular['device'], regular['inode']):
        raise OSError('ls total symlink probe failed')
    return dict(before=before, sections=expected_sections(before, row['ls_totals']),
                unit_bytes=1024, uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat allocation in 512-byte units and stat alias identity')


def output_matches(environment, output):
    patterns = []
    for section in environment['sections']:
        pattern = re.escape(section['directory'].encode()) + b':\n' if section['header'] else b''
        if section['header'] == 'optional':
            pattern = b'(?:' + pattern + b')?'
        pattern += b'total +' + str(section['total']).encode() + b'\n'
        for name, count in section['entries']:
            pattern += b' *' + str(count).encode() + b' +' + re.escape(name.encode()) + b'\n'
        patterns.append(pattern)
    return re.fullmatch(b'\n'.join(patterns), output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'totals'
    after = measurements(root, NAMES)
    if after != environment['before']:
        return ['ls total fixture metadata changed'], after
    errors = []
    for name, content in {**FILES, 'tree/hard': FILES['tree/regular']}.items():
        if (root / name).read_bytes() != content:
            errors.append('ls total fixture bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / name) != target:
            errors.append('ls total fixture link changed: ' + name)
    for name, entries in {'': ['tree', 'vacant'], **ENTRIES}.items():
        if sorted(p.name for p in (root / name).iterdir()) != entries:
            errors.append('ls total fixture entries changed: ' + name)
    return errors, after
