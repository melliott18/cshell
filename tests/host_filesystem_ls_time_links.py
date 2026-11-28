"""CSH-134: time sorting uses link or referent timestamps under -H/-L.

Authored link and referent access/modification dates yield distinct orders. Only private
acyclic file links, C collation and old UTC dates are qualified.
"""
import grp
import os
import pwd
import re
import stat

from host_filesystem_cases import case
from host_filesystem_metadata import stamp, STAMP
from host_filesystem_ls_blocks import measurements as metadata_measurements

FILES = {'a': b'A' * 19, 'bbbbbbb': b'B' * 3, 'ccc': b'C' * 7}
LINKS = {'alpha': '../targets/a', 'bravo': '../targets/bbbbbbb',
         'charlie': '../targets/ccc', 'delta': '../targets/a'}
NAMES = tuple(LINKS)


# Day ranks distinguish access/modification and link/referent selections.
DAY = 86400 * 10**9
TIMES = {
    'mtime': {'targets/a': 3, 'targets/bbbbbbb': 1, 'targets/ccc': 2,
              'links/alpha': 1, 'links/bravo': 3, 'links/charlie': 2, 'links/delta': 1},
    'atime': {'targets/a': 1, 'targets/bbbbbbb': 2, 'targets/ccc': 3,
              'links/alpha': 3, 'links/bravo': 2, 'links/charlie': 1, 'links/delta': 3},
}


def measurements(root, names):
    result = metadata_measurements(root, names)
    for name, info in result.items():
        if name.startswith('targets/'):
            info['atime_ns'] = (root / name).lstat().st_atime_ns
    return result


def cases():
    for clock in ('mtime', 'atime'):
        for graph in ('operands', 'directory'):
            for form in ('1', 'l', 'n'):
                for follow in ('physical', 'H', 'L'):
                    for reverse in (False, True):
                        options = ['-' + form, '-t', '-k',
                                   *(['-u'] if clock == 'atime' else []),
                                   *([] if follow == 'physical' else ['-' + follow]),
                                   *(['-r'] if reverse else [])]
                        operands = (['-d', *['time-links/links/' + n for n in reversed(NAMES)]]
                                    if graph == 'operands' else ['time-links/links'])
                        yield case('ls', f'time-links-{clock}-{graph}-{form}-{follow}-' +
                                   ('reverse' if reverse else 'forward'), options + operands,
                                   ticket='CSH-134', out='ls-time-links', env={'TZ': 'UTC0'},
                                   ls_time_links=dict(clock=clock, graph=graph, form=form,
                                                      follow=follow, reverse=reverse))


def follows(spec):
    return spec['follow'] == 'L' or (spec['follow'] == 'H' and spec['graph'] == 'operands')


def selected_path(spec, name):
    return 'targets/' + LINKS[name].rsplit('/', 1)[1] if follows(spec) else 'links/' + name


def ordered_names(spec):
    ranks = TIMES[spec['clock']]
    names = sorted(NAMES, key=lambda n: (-ranks[selected_path(spec, n)], n))
    return list(reversed(names)) if spec['reverse'] else names


def setup(directory, row):
    if 'ls_time_links' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('time-link witnesses require one unprivileged identity')
    root = directory / 'time-links'
    (root / 'targets').mkdir(parents=True)
    (root / 'links').mkdir()
    for name, data in FILES.items():
        path = root / 'targets' / name
        path.write_bytes(data)
        path.chmod(0o640)
        if path.read_bytes() != data:
            raise OSError('time-link content setup failed')
        stamp(path, STAMP, STAMP)
    for name, target in LINKS.items():
        path = root / 'links' / name
        path.symlink_to(target)
        if os.readlink(path) != target:
            raise OSError('time-link text setup failed')
        stamp(path, STAMP, STAMP)
    names = ['targets', 'links', *['targets/' + n for n in FILES], *['links/' + n for n in NAMES]]
    before = measurements(root, names)
    for name, data in FILES.items():
        info = before['targets/' + name]
        if not stat.S_ISREG(info['mode']) or stat.S_IMODE(info['mode']) != 0o640 or info['size'] != len(data):
            raise OSError('time-link target type/mode/size probe failed')
    referents = {}
    for name, target in LINKS.items():
        info = before['links/' + name]
        ref = (root / 'links' / name).stat()
        expected = before['targets/' + target.rsplit('/', 1)[1]]
        referents[name] = dict(device=ref.st_dev, inode=ref.st_ino, size=ref.st_size)
        if not stat.S_ISLNK(info['mode']) or info['size'] != len(target):
            raise OSError('time-link link type/size probe failed')
        if (ref.st_dev, ref.st_ino, ref.st_size) != (expected['device'], expected['inode'], expected['size']):
            raise OSError('time-link referent probe failed')
        if info['inode'] == ref.st_ino:
            raise OSError('time-link identities must distinguish links and referents')
    if any(v['uid'] != os.geteuid() or v['blocks'] < 0 for v in before.values()):
        raise OSError('time-link ownership/allocation probe failed')
    entries = {name: sorted(os.listdir(root / name)) for name in ('targets', 'links')}
    if entries != dict(targets=sorted(FILES), links=sorted(NAMES)):
        raise OSError('time-link directory entries differ from authored graph')
    try:
        owners = {n: pwd.getpwuid(v['uid']).pw_name for n, v in before.items()}
        groups = {n: grp.getgrgid(v['gid']).gr_name for n, v in before.items()}
    except KeyError as error:
        raise OSError('time-link account names unavailable') from error
    if any(not n or n.isdecimal() or any(not 32 < ord(c) < 127 for c in n)
           for n in (*owners.values(), *groups.values())):
        raise OSError('time-link account names must be distinct printable ASCII')
    # stat/readlink probes can update link atime. Stamp only after those probes,
    # then use lstat exclusively until the provider runs.
    for name in TIMES['mtime']:
        stamp(root / name, STAMP + TIMES['atime'][name] * DAY,
              STAMP + TIMES['mtime'][name] * DAY)
    before = measurements(root, names)
    timestamps = {name: dict(atime_ns=(root / name).lstat().st_atime_ns,
                             mtime_ns=(root / name).lstat().st_mtime_ns)
                  for name in TIMES['mtime']}
    return dict(spec=row['ls_time_links'], before=before, referents=referents, timestamps=timestamps,
                entries=entries, owners=owners, groups=groups,
                uid=os.getuid(), euid=os.geteuid(), unit_bytes=1024,
                probe='pre-exec authored bytes/link lengths, lstat metadata/blocks, stat referent identity and exact old UTC timestamps')


def output_matches(environment, output):
    spec = environment['spec']
    names = ordered_names(spec)
    prefix = 'time-links/links/' if spec['graph'] == 'operands' else ''
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
                  str(info['size']).encode(), b'Jan', str(2 + TIMES[spec['clock']][path]).encode(), b'2000', (prefix + name).encode()]
        pattern += rb'[ \t]+'.join(fields)
        if not follows(spec):
            pattern += b' -> ' + re.escape(LINKS[name].encode())
        pattern += b'\n'
    return re.fullmatch(pattern, output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'time-links'
    after = measurements(root, environment['before'])
    # Symlink/directory atimes can change during traversal. Regular-file atimes
    # and all other measured metadata, including ctime, remain strict.
    if after != environment['before']:
        return ['time-link fixture metadata changed'], after
    errors = []
    for name, data in FILES.items():
        if (root / 'targets' / name).read_bytes() != data:
            errors.append('time-link target bytes changed: ' + name)
    for name, target in LINKS.items():
        if os.readlink(root / 'links' / name) != target:
            errors.append('time-link text changed: ' + name)
    if sorted(os.listdir(root)) != ['links', 'targets'] or any(
            sorted(os.listdir(root / n)) != entries for n, entries in environment['entries'].items()):
        errors.append('time-link directory entries changed')
    return errors, after
