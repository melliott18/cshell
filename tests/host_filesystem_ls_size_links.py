"""CSH-133: size sorting uses link or referent metadata under -H/-L.

Authored link lengths and regular-file bytes yield distinct orders. Only private
acyclic file links, C collation and old UTC dates are qualified.
"""
import grp
import os
import pwd
import re
import stat

from host_filesystem_cases import case
from host_filesystem_metadata import stamp, STAMP
from host_filesystem_ls_blocks import measurements

FILES = {'a': b'A' * 19, 'bbbbbbb': b'B' * 3, 'ccc': b'C' * 7}
LINKS = {'alpha': '../targets/a', 'bravo': '../targets/bbbbbbb',
         'charlie': '../targets/ccc', 'delta': '../targets/a'}
NAMES = tuple(LINKS)


def cases():
    for graph in ('operands', 'directory'):
        for form in ('1', 'l', 'n'):
            for follow in ('physical', 'H', 'L'):
                for reverse in (False, True):
                    options = ['-' + form, '-S', '-k',
                               *([] if follow == 'physical' else ['-' + follow]),
                               *(['-r'] if reverse else [])]
                    operands = (['-d', *['size-links/links/' + n for n in reversed(NAMES)]]
                                if graph == 'operands' else ['size-links/links'])
                    yield case('ls', f'size-links-{graph}-{form}-{follow}-' +
                               ('reverse' if reverse else 'forward'), options + operands,
                               ticket='CSH-133', out='ls-size-links', env={'TZ': 'UTC0'},
                               ls_size_links=dict(graph=graph, form=form, follow=follow, reverse=reverse))


def follows(spec):
    return spec['follow'] == 'L' or (spec['follow'] == 'H' and spec['graph'] == 'operands')


def selected_path(spec, name):
    return 'targets/' + LINKS[name].rsplit('/', 1)[1] if follows(spec) else 'links/' + name


def ordered_names(spec):
    # The sizes are authored independently of the measured provider output.
    sizes = {n: len(FILES[LINKS[n].rsplit('/', 1)[1]]) if follows(spec) else len(LINKS[n])
             for n in NAMES}
    names = sorted(NAMES, key=lambda n: (-sizes[n], n))
    return list(reversed(names)) if spec['reverse'] else names


def setup(directory, row):
    if 'ls_size_links' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('size-link witnesses require one unprivileged identity')
    root = directory / 'size-links'
    (root / 'targets').mkdir(parents=True)
    (root / 'links').mkdir()
    for name, data in FILES.items():
        path = root / 'targets' / name
        path.write_bytes(data)
        path.chmod(0o640)
        if path.read_bytes() != data:
            raise OSError('size-link content setup failed')
        stamp(path, STAMP, STAMP)
    for name, target in LINKS.items():
        path = root / 'links' / name
        path.symlink_to(target)
        if os.readlink(path) != target:
            raise OSError('size-link text setup failed')
        stamp(path, STAMP, STAMP)
    names = ['targets', 'links', *['targets/' + n for n in FILES], *['links/' + n for n in NAMES]]
    before = measurements(root, names)
    for name, data in FILES.items():
        info = before['targets/' + name]
        if not stat.S_ISREG(info['mode']) or stat.S_IMODE(info['mode']) != 0o640 or info['size'] != len(data):
            raise OSError('size-link target type/mode/size probe failed')
    referents = {}
    for name, target in LINKS.items():
        info = before['links/' + name]
        ref = (root / 'links' / name).stat()
        expected = before['targets/' + target.rsplit('/', 1)[1]]
        referents[name] = dict(device=ref.st_dev, inode=ref.st_ino, size=ref.st_size)
        if not stat.S_ISLNK(info['mode']) or info['size'] != len(target):
            raise OSError('size-link link type/size probe failed')
        if (ref.st_dev, ref.st_ino, ref.st_size) != (expected['device'], expected['inode'], expected['size']):
            raise OSError('size-link referent probe failed')
        if info['inode'] == ref.st_ino:
            raise OSError('size-link identities must distinguish links and referents')
    if any(v['uid'] != os.geteuid() or v['blocks'] < 0 for v in before.values()):
        raise OSError('size-link ownership/allocation probe failed')
    entries = {name: sorted(os.listdir(root / name)) for name in ('targets', 'links')}
    if entries != dict(targets=sorted(FILES), links=sorted(NAMES)):
        raise OSError('size-link directory entries differ from authored graph')
    try:
        owners = {n: pwd.getpwuid(v['uid']).pw_name for n, v in before.items()}
        groups = {n: grp.getgrgid(v['gid']).gr_name for n, v in before.items()}
    except KeyError as error:
        raise OSError('size-link account names unavailable') from error
    if any(not n or n.isdecimal() or any(not 32 < ord(c) < 127 for c in n)
           for n in (*owners.values(), *groups.values())):
        raise OSError('size-link account names must be distinct printable ASCII')
    return dict(spec=row['ls_size_links'], before=before, referents=referents,
                entries=entries, owners=owners, groups=groups,
                uid=os.getuid(), euid=os.geteuid(), unit_bytes=1024,
                probe='pre-exec authored bytes/link lengths, lstat metadata/blocks, stat referent identity and exact old UTC timestamps')


def output_matches(environment, output):
    spec = environment['spec']
    names = ordered_names(spec)
    prefix = 'size-links/links/' if spec['graph'] == 'operands' else ''
    if spec['form'] == '1':
        return output == ''.join(prefix + n + '\n' for n in names).encode('ascii')
    pattern = b''
    if spec['graph'] == 'directory':
        total = (sum(environment['before'][selected_path(spec, n)]['blocks'] for n in names) + 1) // 2
        pattern += b'total +' + str(total).encode() + b'\n'
    for name in names:
        path = selected_path(spec, name)
        info = environment['before'][path]
        numeric = spec['form'] == 'n'
        owner = str(info['uid']) if numeric else environment['owners'][path]
        group = str(info['gid']) if numeric else environment['groups'][path]
        fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
                  str(info['nlink']).encode(), re.escape(owner.encode()), re.escape(group.encode()),
                  str(info['size']).encode(), b'Jan', b'2', b'2000', (prefix + name).encode()]
        pattern += rb'[ \t]+'.join(fields)
        if not follows(spec):
            pattern += b' -> ' + re.escape(LINKS[name].encode())
        pattern += b'\n'
    return re.fullmatch(pattern, output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'size-links'
    after = measurements(root, environment['before'])
    # Access times are deliberately excluded: readlink and directory traversal
    # can update them. All other measured metadata, including ctime, is strict.
    if after != environment['before']:
        return ['size-link fixture metadata changed'], after
    errors = []
    for name, data in FILES.items():
        if (root / 'targets' / name).read_bytes() != data:
            errors.append('size-link target bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / 'links' / name) != target:
            errors.append('size-link text changed: ' + name)
    if sorted(os.listdir(root)) != ['links', 'targets'] or any(
            sorted(os.listdir(root / n)) != entries for n, entries in environment['entries'].items()):
        errors.append('size-link directory entries changed')
    return errors, after
