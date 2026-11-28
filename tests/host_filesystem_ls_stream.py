"""CSH-125: ls stream separators, fixed-width extremes and option precedence.

C-locale ASCII names on a private graph; no terminal or arbitrary-width claim.
The comma in a filename is data, never parsed as a record separator.
"""
import os
import re
import stat

from host_filesystem_cases import case
from host_filesystem_ls_blocks import measurements

FILES = {'a,comma': b'comma', 'b space': b'space', 'c-exec': b'executable',
         'd-dir/guard': b'not listed'}
DIRECTORY, FIFO, LINK = 'd-dir', 'e-fifo', 'f-link'
ENTRIES = ('a,comma', 'b space', 'c-exec', DIRECTORY, FIFO, LINK)
NAMES = (*FILES, DIRECTORY, FIFO, LINK, 'empty')
FORMATS = {'m': ['-m'], '1m': ['-1', '-m'], 'lm': ['-l', '-m'], 'm1': ['-m', '-1']}


def cases():
    for graph in ('directory', 'operands'):
        for form, flags in FORMATS.items():
            for style in ('plain', 'F', 'p'):
                for reverse in (False, True):
                    for columns in (1, 4096):
                        options = [*flags, *([] if style == 'plain' else ['-' + style]),
                                   *(['-r'] if reverse else [])]
                        operands = (['stream'] if graph == 'directory' else
                                    ['-d', *['stream/' + n for n in reversed(ENTRIES)]])
                        yield case('ls', f'stream-{graph}-{form}-{style}-{int(reverse)}-{columns}',
                                   options + operands, ticket='CSH-125', out='ls-stream',
                                   env={'COLUMNS': str(columns)},
                                   ls_stream=dict(graph=graph, form=form, style=style,
                                                  reverse=reverse, columns=columns))
    for graph in ('empty', 'single'):
        for columns in (1, 4096):
            yield case('ls', f'stream-{graph}-{columns}',
                       ['-m', 'stream/empty' if graph == 'empty' else 'stream/a,comma'],
                       ticket='CSH-125', out='ls-stream', env={'COLUMNS': str(columns)},
                       ls_stream=dict(graph=graph, form='m', style='plain', reverse=False, columns=columns))


def expected_entries(before, spec):
    if spec['graph'] == 'empty':
        return []
    if spec['graph'] == 'single':
        return ['stream/a,comma']
    result = []
    for name in sorted(ENTRIES, reverse=spec['reverse']):
        mode = before[name]['mode']
        suffix = ''
        if spec['style'] in ('F', 'p') and stat.S_ISDIR(mode):
            suffix = '/'
        elif spec['style'] == 'F':
            if stat.S_ISLNK(mode):
                suffix = '@'
            elif stat.S_ISFIFO(mode):
                suffix = '|'
            elif stat.S_ISREG(mode) and mode & 0o111:
                suffix = '*'
        result.append(('stream/' if spec['graph'] == 'operands' else '') + name + suffix)
    return result


def setup(directory, row):
    if 'ls_stream' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls stream witnesses require one unprivileged identity')
    root = directory / 'stream'
    root.mkdir()
    (root / DIRECTORY).mkdir()
    # The empty directory lives outside the listed graph until that case needs it.
    for name, content in FILES.items():
        (root / name).write_bytes(content)
        (root / name).chmod(0o700 if name == 'c-exec' else 0o600)
    os.mkfifo(root / FIFO, 0o600)
    (root / LINK).symlink_to(DIRECTORY)
    spec = row['ls_stream']
    names = list(NAMES[:-1])
    if spec['graph'] == 'empty':
        (root / 'empty').mkdir()
        names.append('empty')
    before = measurements(root, names)
    for name, info in before.items():
        kind = (stat.S_IFDIR if name in (DIRECTORY, 'empty') else stat.S_IFIFO if name == FIFO
                else stat.S_IFLNK if name == LINK else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls stream type/inode probe failed')
        if name in FILES and stat.S_IMODE(info['mode']) != (0o700 if name == 'c-exec' else 0o600):
            raise OSError('ls stream mode probe failed')
    target = (root / LINK).stat()
    if (target.st_dev, target.st_ino, target.st_mode) != tuple(before[DIRECTORY][k] for k in ('device', 'inode', 'mode')):
        raise OSError('ls stream symlink referent probe failed')
    names = sorted(ENTRIES + (('empty',) if spec['graph'] == 'empty' else ()))
    if sorted(os.listdir(root)) != names or os.listdir(root / DIRECTORY) != ['guard']:
        raise OSError('ls stream directory entries probe failed')
    entries = expected_entries(before, spec)
    if spec['columns'] == 4096 and len(', '.join(entries)) + 1 >= 4096:
        raise OSError('wide stream fixture does not fit')
    if spec['columns'] == 1 and any(len(n) <= 1 for n in entries):
        raise OSError('narrow stream fixture does not force wrapping')
    return dict(before=before, entries=entries, directory_entries=names, spec=spec,
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat type/mode/inode, stat referent and listdir; authored ASCII lengths versus COLUMNS=1/4096')


def output_matches(environment, output):
    entries = environment['entries']
    if not entries:
        return output == b''
    spec = environment['spec']
    # STDOUT permits a single optional space before a wrapping newline.
    separator = (b'\n' if spec['form'] == 'm1' else
                 rb', ?\n' if spec['columns'] == 1 else b', ')
    pattern = separator.join(re.escape(n.encode('ascii')) for n in entries) + b'\n'
    return re.fullmatch(pattern, output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'stream'
    after = measurements(root, environment['before'])
    errors = []
    if after != environment['before']:
        errors.append('ls stream metadata changed')
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls stream bytes changed: ' + name)
    if os.readlink(root / LINK) != DIRECTORY:
        errors.append('ls stream link changed')
    if (sorted(os.listdir(root)) != environment['directory_entries']
            or os.listdir(root / DIRECTORY) != ['guard']
            or ('empty' in environment['before'] and os.listdir(root / 'empty'))):
        errors.append('ls stream directory entries changed')
    return errors, after
