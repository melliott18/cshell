"""CSH-121: mixed ls operands and operand versus entry symlink following.

The authored graph and pre-exec kernel probes define expectations. No provider
output is used as an oracle; only C locale, ordinary private objects are covered.
"""
import os
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements
from host_filesystem_ls_identity import output_matches as entries_match

DIRECTORIES = ('a-directory', 'a-directory/nested', 'c-empty')
FILES = {'z-file': b'operand\n', 'a-directory/leaf': b'child\n',
         'a-directory/nested/guard': b'not recursively listed\n'}
LINKS = {'b-dir-link': 'a-directory', 'y-file-link': 'z-file',
         'a-directory/dir-link': 'nested', 'a-directory/file-link': '../z-file'}
OPERANDS = ('a-directory', 'b-dir-link', 'c-empty', 'x-fifo', 'y-file-link', 'z-file')
ENTRIES = {'': OPERANDS, 'a-directory': ('dir-link', 'file-link', 'leaf', 'nested'),
           'a-directory/nested': ('guard',), 'c-empty': ()}
NAMES = (*DIRECTORIES, *FILES, *LINKS, 'x-fifo')


def cases():
    for follow in ('default', 'H', 'L'):
        for style in ('plain', 'F', 'p'):
            for inode in (False, True):
                for reverse in (False, True):
                    options = ['-1', *([] if follow == 'default' else ['-' + follow]),
                               *([] if style == 'plain' else ['-' + style]),
                               *(['-i'] if inode else []), *(['-r'] if reverse else [])]
                    # Interleave types and reverse neither group consistently.
                    operands = ['c-empty', 'z-file', 'a-directory', 'x-fifo', 'b-dir-link', 'y-file-link']
                    yield case('ls', f'operands-{follow}-{style}-{int(inode)}-{int(reverse)}',
                               options + ['mixed/' + n for n in operands], ticket='CSH-121',
                               ls_operands=dict(follow=follow, style=style, inode=inode, reverse=reverse),
                               out='ls-operands')


def expected_output(before, spec):
    def entry(key, display, follow):
        target = {'b-dir-link': 'a-directory', 'y-file-link': 'z-file',
                  'a-directory/dir-link': 'a-directory/nested',
                  'a-directory/file-link': 'z-file'}.get(key)
        info = before[target if follow and target else key]
        mode, suffix = info['mode'], ''
        if spec['style'] in ('F', 'p') and stat.S_ISDIR(mode):
            suffix = '/'
        elif spec['style'] == 'F':
            if stat.S_ISLNK(mode):
                suffix = '@'
            elif stat.S_ISFIFO(mode):
                suffix = '|'
        return dict(name=display + suffix, inode=info['inode'] if spec['inode'] else None)

    # Only -F suppresses automatic operand directory-link following in this
    # matrix. -H follows operands, while -L also follows links inside listings.
    directory_names = ['a-directory', 'c-empty']
    if spec['follow'] != 'default' or spec['style'] != 'F':
        directory_names.append('b-dir-link')
    files = [entry(n, 'mixed/' + n, spec['follow'] != 'default')
             for n in sorted(set(OPERANDS) - set(directory_names), reverse=spec['reverse'])]
    sections = []
    for directory in sorted(directory_names, reverse=spec['reverse']):
        target = 'a-directory' if directory == 'b-dir-link' else directory
        entries = [entry(target + '/' + n, n, spec['follow'] == 'L')
                   for n in sorted(ENTRIES[target], reverse=spec['reverse'])]
        sections.append(dict(name='mixed/' + directory, entries=entries))
    return dict(entries=files, sections=sections)


def setup(directory, row):
    if 'ls_operands' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls operand witnesses require one unprivileged identity')
    root = directory / 'mixed'
    root.mkdir()
    for name in DIRECTORIES:
        (root / name).mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
    os.mkfifo(root / 'x-fifo', 0o600)
    for name, target in LINKS.items():
        (root / name).symlink_to(target)
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFDIR if name in DIRECTORIES else stat.S_IFLNK if name in LINKS
                else stat.S_IFIFO if name == 'x-fifo' else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls operand type/inode probe failed: ' + name)
    for name, target in LINKS.items():
        info = (root / name).stat()
        expected = before[os.path.normpath(os.path.join(os.path.dirname(name), target))]
        if (info.st_dev, info.st_ino, info.st_mode) != tuple(expected[k] for k in ('device', 'inode', 'mode')):
            raise OSError('ls operand symlink referent probe failed')
        if before[name]['inode'] == info.st_ino:
            raise OSError('ls operand link/referent inodes must differ')
    return dict(before=before, **expected_output(before, row['ls_operands']),
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat type/inode and stat operand/entry symlink referent identity')


def output_matches(environment, output):
    # Headers and blank separators are mandatory for these multiple operands.
    # Directory operand order, as well as each list, is explicitly C-sorted.
    remainder = output
    files, separator, remainder = remainder.partition(b'\n\n')
    if not separator or not entries_match(environment, files + b'\n'):
        return False
    for index, section in enumerate(environment['sections']):
        header = section['name'].encode() + b':\n'
        if not remainder.startswith(header):
            return False
        remainder = remainder[len(header):]
        if index + 1 < len(environment['sections']):
            # Empty directory output ends at its header newline. The next
            # section contributes one further newline, not two.
            if not section['entries']:
                body, separator, remainder = b'', remainder[:1], remainder[1:]
                if separator != b'\n':
                    return False
            else:
                body, separator, remainder = remainder.partition(b'\n\n')
                if not separator:
                    return False
                body += b'\n'
        else:
            body, remainder = remainder, b''
        if not entries_match(section, body):
            return False
    return not remainder


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'mixed'
    after = measurements(root, NAMES)
    errors = []
    if after != environment['before']:
        errors.append('ls operand metadata changed')
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls operand bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / name) != target:
            errors.append('ls operand link changed: ' + name)
    for name, entries in ENTRIES.items():
        if sorted(p.name for p in (root / name).iterdir()) != sorted(entries):
            errors.append('ls operand entries changed: ' + name)
    return errors, after
