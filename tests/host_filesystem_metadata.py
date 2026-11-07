"""CSH-088 privately authored metadata and exact timestamp environments.

Pre-exec lstat/utime measurements are the oracle; no utility supplies expected
output. No volume filling, mounts, privilege changes or wall-clock races.
"""
import os
import re
import stat

from host_filesystem_cases import case

STAMP = 946771200000000000  # 2000-01-02 00:00:00 UTC
NAMES = ('meta/first', 'meta/second', 'meta/third', 'meta/twin')


def cases():
    def witness(utility, name, args, **kw):
        return case(utility, 'metadata-' + name, args, ticket='CSH-088',
                    metadata_environment=True, **kw)

    for kind in ('regular', 'hardlink', 'directory', 'fifo', 'symlink'):
        yield witness('ls', 'numeric-' + kind, ['-d', '-n', 'meta/' + kind],
                      metadata_kind=kind, out='metadata-listing')
    # Equal primary keys exercise the C-locale filename secondary key too.
    for name, options, order in [
        ('size', ['-S'], ('third', 'first', 'second', 'twin')),
        ('size-reverse', ['-S', '-r'], ('twin', 'second', 'first', 'third')),
        ('mtime', ['-t'], ('second', 'twin', 'third', 'first')),
        ('mtime-reverse', ['-t', '-r'], ('first', 'third', 'twin', 'second')),
        ('atime', ['-t', '-u'], ('first', 'third', 'second', 'twin')),
        ('atime-reverse', ['-t', '-u', '-r'], ('twin', 'second', 'third', 'first')),
    ]:
        yield witness('ls', 'sort-' + name, ['-1', *options, *NAMES],
                      metadata_kind='sorting', out=''.join('meta/' + n + '\n' for n in order).encode())
    for delta in (-1, 0, 1):
        yield witness('find', 'newer-' + {-1: 'before', 0: 'equal', 1: 'after'}[delta],
                      ['meta/candidate', '-newer', 'meta/reference', '-print'],
                      metadata_kind='newer', delta_ns=delta,
                      out=b'meta/candidate\n' if delta > 0 else b'')
    for option in ('-H', '-L'):
        # Reference-link timestamp is newer than candidate, but its target is
        # older. Following the reference is therefore observable independently.
        yield witness('find', 'newer-reference-' + option[1:],
                      [option, 'meta/candidate', '-newer', 'meta/reference-link', '-print'],
                      metadata_kind='newer', delta_ns=1, out=b'meta/candidate\n')


def measure(path):
    info = path.lstat()
    return {key: getattr(info, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'uid', 'gid', 'nlink', 'size', 'atime_ns', 'mtime_ns')}


def stamp(path, atime, mtime):
    os.utime(path, ns=(atime, mtime), follow_symlinks=False)
    observed = measure(path)
    if (observed['atime_ns'], observed['mtime_ns']) != (atime, mtime):
        raise OSError('private filesystem cannot represent authored timestamps exactly')


def setup(directory, row):
    if not row.get('metadata_environment'):
        return None
    root = directory / 'meta'
    root.mkdir()
    kind = row['metadata_kind']
    names = []
    if kind == 'sorting':
        for name, size, access, modified in [
            ('first', 19, 3, 1), ('second', 7, 1, 3),
            ('third', 41, 2, 2), ('twin', 7, 1, 3),
        ]:
            path = root / name
            path.write_bytes(b'x' * size)
            stamp(path, STAMP + access * 1000000000, STAMP + modified * 1000000000)
            if path.stat().st_size != size:
                raise OSError('authored sorting size was not established')
            names.append('meta/' + name)
    elif kind == 'newer':
        for name, delta in [('reference', 0), ('candidate', row['delta_ns'])]:
            path = root / name
            path.write_bytes(b'')
            stamp(path, STAMP, STAMP + delta)
            names.append('meta/' + name)
        (root / 'reference-link').symlink_to('reference')
        stamp(root / 'reference-link', STAMP, STAMP + 1000000000)
        names.append('meta/reference-link')
    else:
        target = root / kind
        if kind == 'directory':
            target.mkdir()
            target.chmod(0o750)
        elif kind == 'fifo':
            os.mkfifo(target, 0o600)
            target.chmod(0o600)
        elif kind == 'symlink':
            (root / 'target').write_bytes(b'referent\n')
            names.append('meta/target')
            target.symlink_to('target')
        else:
            target.write_bytes(b'authored metadata\n')
            target.chmod(0o640)
            if kind == 'hardlink':
                os.link(target, root / 'other-name')
                names.append('meta/other-name')
        stamp(target, STAMP, STAMP)
        names.append('meta/' + kind)
        info = measure(target)
        expected_type = dict(directory=stat.S_IFDIR, fifo=stat.S_IFIFO,
                             symlink=stat.S_IFLNK).get(kind, stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != expected_type:
            raise OSError('authored file type was not established')
        if kind == 'hardlink':
            other = measure(root / 'other-name')
            if (info['dev'], info['ino'], info['nlink']) != (other['dev'], other['ino'], 2):
                raise OSError('authored hard-link identity was not established')
    return dict(phase='armed', kind=kind,
                measurements={name: measure(directory / name) for name in names},
                probe='private lstat and exact utime(ns) readback before exec',
                scope='authored metadata only; no ACL, clock, capacity or timestamp-range claim')


def listing_matches(environment, output):
    kind = environment['kind']
    name = 'meta/' + kind
    info = environment['measurements'][name]
    # Column padding and the alternate-access marker vary by provider. Match
    # every semantic field, one complete line, with no unaccounted diagnostics.
    fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
              *(str(info[key]).encode() for key in ('nlink', 'uid', 'gid', 'size')),
              b'Jan', b'2', b'2000', re.escape(name.encode())]
    pattern = rb'[ \t]+'.join(fields)
    if kind == 'symlink':
        pattern += rb' -> target'
    return re.fullmatch(pattern + rb'\n', output) is not None


def verify(directory, environment):
    if environment is None:
        return [], {}
    observed = {name: measure(directory / name) for name in environment['measurements']}
    # readlink may update the link's atime. All other measured fields must be
    # unchanged; none of these commands should modify the objects they inspect.
    for name, actual in observed.items():
        before = environment['measurements'][name]
        if any(actual[key] != value for key, value in before.items()
               if key != 'atime_ns' or not stat.S_ISLNK(before['mode'])):
            return ['metadata fixture changed during execution'], observed
    return [], observed
