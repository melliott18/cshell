"""CSH-120: recursive hidden selection and directory-link traversal.

A finite, acyclic, privately owned graph; no provider output defines the oracle.
Section order is not qualified; names within each section have exact C order.
"""
import os
import stat

from host_filesystem_cases import case
from host_filesystem_ls_identity import output_matches as entries_match

DIRECTORIES = ('tree', 'tree/.hidden-dir', 'tree/.hidden-dir/.deep',
               'tree/branch', 'tree/visible', 'tree/visible/.nested')
FILES = {'guard': b'outside operand\n', 'tree/.hidden': b'hidden\n',
         'tree/file': b'visible\n', 'tree/.hidden-dir/leaf': b'hidden child\n',
         'tree/.hidden-dir/.deep/leaf': b'hidden grandchild\n',
         'tree/branch/leaf': b'sibling\n', 'tree/visible/leaf': b'child\n',
         'tree/visible/.nested/leaf': b'grandchild\n'}
LINKS = {'tree/alias': 'visible', 'tree/.hidden-alias': '.hidden-dir'}
ENTRIES = {'': ('guard', 'tree'),
           'tree': ('.hidden', '.hidden-alias', '.hidden-dir', 'alias', 'branch', 'file', 'visible'),
           'tree/.hidden-dir': ('.deep', 'leaf'), 'tree/.hidden-dir/.deep': ('leaf',),
           'tree/branch': ('leaf',), 'tree/visible': ('.nested', 'leaf'),
           'tree/visible/.nested': ('leaf',)}
ALIASES = {'tree/alias': 'tree/visible', 'tree/alias/.nested': 'tree/visible/.nested',
           'tree/.hidden-alias': 'tree/.hidden-dir',
           'tree/.hidden-alias/.deep': 'tree/.hidden-dir/.deep'}
# Include dot and dot-dot through both physical directories and alias spellings.
NAMES = tuple(dict.fromkeys((*DIRECTORIES, *FILES, *LINKS,
                            *(d + '/' + n for d in (*DIRECTORIES, *ALIASES)
                              for n in ('.', '..', *ENTRIES[ALIASES.get(d, d)])))))


def measurements(root, names):
    result = {}
    for name in names:
        # Keep trailing '/.' intact: Path normalizes it away, which would lstat
        # the symlink itself instead of the directory reached through the link.
        info = os.lstat(str(root) + '/' + name)
        result[name] = dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                            size=info.st_size, nlink=info.st_nlink, blocks=info.st_blocks,
                            uid=info.st_uid, gid=info.st_gid, mtime_ns=info.st_mtime_ns,
                            ctime_ns=info.st_ctime_ns)
    return result


def cases():
    for selection in ('default', 'A', 'a'):
        for reverse in (False, True):
            for follow in (False, True):
                for rendering in ('plain', 'inode', 'F', 'p'):
                    options = ['-1', '-R', *([] if selection == 'default' else ['-' + selection]),
                               *(['-r'] if reverse else []), *(['-L'] if follow else []),
                               *([] if rendering == 'plain' else ['-i' if rendering == 'inode' else '-' + rendering])]
                    yield case('ls', f'recursive-{selection}-{int(reverse)}-{int(follow)}-{rendering}',
                               [*options, 'recursion/tree'], ticket='CSH-120',
                               ls_recursive=dict(selection=selection, reverse=reverse,
                                                 follow=follow, rendering=rendering), out='ls-recursive')


def expected_sections(before, spec):
    sections = {}
    # Authored paths, not filesystem enumeration or provider output, determine
    # the finite traversal. Dot/dot-dot are listed with -a, never descended into.
    paths = list(DIRECTORIES) + (list(ALIASES) if spec['follow'] else [])
    for path in paths:
        if spec['selection'] == 'default' and any(p.startswith('.') for p in path.split('/')):
            continue
        names = list(ENTRIES[ALIASES.get(path, path)])
        if spec['selection'] == 'default':
            names = [n for n in names if not n.startswith('.')]
        elif spec['selection'] == 'a':
            names += ['.', '..']
        entries = []
        for name in sorted(names, reverse=spec['reverse']):
            key = path + '/' + name
            info = before['tree/' + LINKS[key]] if spec['follow'] and key in LINKS else before[key]
            suffix = ''
            if spec['rendering'] in ('F', 'p') and stat.S_ISDIR(info['mode']):
                suffix = '/'
            elif spec['rendering'] == 'F' and stat.S_ISLNK(info['mode']):
                suffix = '@'
            entries.append(dict(name=name + suffix,
                                inode=info['inode'] if spec['rendering'] == 'inode' else None))
        sections['recursion/' + path] = dict(entries=entries)
    return sections


def setup(directory, row):
    if 'ls_recursive' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls recursive witnesses require one unprivileged identity')
    root = directory / 'recursion'
    root.mkdir()
    for name in DIRECTORIES:
        (root / name).mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
    for name, target in LINKS.items():
        (root / name).symlink_to(target)
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFLNK if name in LINKS else stat.S_IFDIR
                if name in DIRECTORIES or name.endswith(('/.', '/..')) else stat.S_IFREG)
        # Alias child directories have their own measured directory identity.
        if name in ALIASES and name not in LINKS or name.endswith(('/.deep', '/.nested')):
            kind = stat.S_IFDIR
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls recursive type/inode probe failed: ' + name)
    for alias, target in ALIASES.items():
        info = (root / alias).stat()
        if (info.st_dev, info.st_ino, info.st_mode) != tuple(before[target][k] for k in ('device', 'inode', 'mode')):
            raise OSError('ls recursive directory alias probe failed')
    for path in (*DIRECTORIES, *ALIASES):
        if before[path + '/.']['inode'] == before[path + '/..']['inode']:
            raise OSError('ls recursive dot and dot-dot must be distinct')
    return dict(before=before, sections=expected_sections(before, row['ls_recursive']),
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat type/inode and stat directory-alias identity; private dot/dot-dot')


def output_matches(environment, output):
    sections = environment['sections']
    seen = set()
    for index, block in enumerate(output.split(b'\n\n')):
        header, separator, body = block.partition(b':\n')
        if index == 0 and not separator:
            name, body = 'recursion/tree', block
        else:
            try:
                name = header.decode('ascii')
            except UnicodeDecodeError:
                return False
        if name not in sections or name in seen or not separator and index != 0:
            return False
        # Splitting removes the last newline from every non-final section.
        if index < output.count(b'\n\n'):
            body += b'\n'
        if not entries_match(sections[name], body):
            return False
        seen.add(name)
    return seen == set(sections)


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'recursion'
    after = measurements(root, NAMES)
    errors = []
    if after != environment['before']:
        errors.append('ls recursive metadata changed')
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls recursive bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / name) != target:
            errors.append('ls recursive link changed: ' + name)
    for name, entries in ENTRIES.items():
        if sorted(p.name for p in (root / name).iterdir()) != sorted(entries):
            errors.append('ls recursive entries changed: ' + name)
    return errors, after
