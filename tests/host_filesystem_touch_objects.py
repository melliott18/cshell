"""CSH-114: touch existing directories/FIFOs and namespace-error continuation.

Authored timestamps and kernel probes are independent of the selected provider.
FIFOs are never opened; no devices, other identities or namespace races are used.
"""
import errno
import os
import stat

from host_filesystem_cases import case
from host_filesystem_reference import BASELINE, SELECTIONS
from host_filesystem_touch_permissions import CONTENT, TARGET

LINKS = {'object-link': 'object', 'object-chain': 'object-link',
         'cycle-a': 'cycle-b', 'cycle-b': 'cycle-a'}
BOUNDARIES = (('directory', 'object', 'directory', None),
              ('directory-chain', 'object-chain', 'directory', None),
              ('fifo', 'object', 'fifo', None),
              ('fifo-hard', 'object-hard', 'fifo', None),
              ('fifo-chain', 'object-chain', 'fifo', None),
              ('not-directory', 'obstruction/child', 'file', errno.ENOTDIR),
              ('symlink-loop', 'cycle-a', 'file', errno.ELOOP))


def cases():
    for boundary, operand, kind, expected_errno in BOUNDARIES:
        for selection, flags in SELECTIONS:
            stamps = (BASELINE[0] if flags == ['-m'] else TARGET,
                      BASELINE[1] if flags == ['-a'] else TARGET)
            effects = {name: dict(type='file', content=CONTENT, mode=0o640)
                       for name in ('first', 'last', 'obstruction')}
            effects.update({name: dict(type='link', link=target) for name, target in LINKS.items()})
            effects['object'] = dict(type=kind, mode=0o750 if kind == 'directory' else 0o640)
            if kind == 'directory':
                effects['object/leaf'] = dict(type='file', content=CONTENT, mode=0o640)
            elif kind == 'fifo':
                effects['object-hard'] = dict(type='fifo', same_inode='object', mode=0o640)
            else:
                effects['object']['content'] = CONTENT
            yield case('touch', 'objects-' + boundary + '-' + selection,
                       [*flags, '-t', '200109090146.40', 'first', operand, 'last'],
                       ticket='CSH-114', effects=effects,
                       touch_objects=dict(boundary=boundary, operand=operand, kind=kind,
                                          errno=expected_errno, target_ns=stamps),
                       status='nonzero' if expected_errno else 0,
                       err='nonempty' if expected_errno else b'')


def snapshot(directory, row):
    result = {}
    for name in row['effects']:
        info = (directory / name).lstat()
        result[name] = dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                            nlink=info.st_nlink, size=info.st_size,
                            atime_ns=info.st_atime_ns, mtime_ns=info.st_mtime_ns)
    return result


def namespace_probe(path, expected_errno):
    try:
        path.stat()
    except OSError as error:
        if error.errno != expected_errno:
            raise
        return error.errno
    raise OSError('touch namespace probe unexpectedly resolved')


def setup(directory, row):
    spec = row.get('touch_objects')
    if spec is None:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('touch object witnesses require one unprivileged identity')
    for name in ('first', 'last', 'obstruction'):
        (directory / name).write_bytes(CONTENT)
    target = directory / 'object'
    if spec['kind'] == 'directory':
        target.mkdir()
        (target / 'leaf').write_bytes(CONTENT)
    elif spec['kind'] == 'fifo':
        os.mkfifo(target)
        os.link(target, directory / 'object-hard')
    else:
        target.write_bytes(CONTENT)
    for name, link in LINKS.items():
        (directory / name).symlink_to(link)
    probes = []
    for name, effect in row['effects'].items():
        if effect['type'] == 'link':
            if os.readlink(directory / name) != effect['link']:
                raise OSError('touch symlink spelling mismatch')
            continue
        path = directory / name
        if effect['type'] == 'file' and path.read_bytes() != CONTENT:
            raise OSError('touch object content readback mismatch')
        path.chmod(effect['mode'])
        # Prove the requested times on every actual type, then leave distinct
        # fractional baselines. utime does not open or transfer through FIFOs.
        for stamps in ((TARGET, TARGET), BASELINE):
            os.utime(path, ns=stamps)
            info = path.stat()
            observed = (info.st_atime_ns, info.st_mtime_ns)
            if observed != stamps:
                raise OSError('filesystem cannot represent touch object timestamps')
            probes.append(dict(path=name, requested_ns=stamps, observed_ns=observed))
    before = snapshot(directory, row)
    identity = lambda name: (before[name]['device'], before[name]['inode'])
    for name in ('object-link', 'object-chain', *(['object-hard'] if spec['kind'] == 'fifo' else [])):
        info = (directory / name).stat()
        if (info.st_dev, info.st_ino) != identity('object'):
            raise OSError('touch object alias graph mismatch')
    measured_errno = (namespace_probe(directory / spec['operand'], spec['errno'])
                      if spec['errno'] else None)
    return dict(before=before, probes=probes, errno=measured_errno,
                uid=os.getuid(), euid=os.geteuid())


def verify(directory, row, environment):
    if environment is None:
        return [], None
    spec = row['touch_objects']
    # Snapshot before effect checks read bytes or enumerate the directory.
    after = snapshot(directory, row)
    errors = []
    for name, before in environment['before'].items():
        info = after[name]
        if any(info[k] != before[k] for k in ('device', 'inode', 'mode', 'nlink', 'size')):
            errors.append('touch object identity/metadata mismatch: ' + name)
        if stat.S_ISLNK(before['mode']):
            # Symlink resolution may change link atime; its mtime must persist.
            if info['mtime_ns'] != before['mtime_ns']:
                errors.append('touch object link timestamp mismatch: ' + name)
        else:
            changed = name in ('first', 'last') or (not spec['errno'] and name in ('object', 'object-hard'))
            expected = tuple(spec['target_ns']) if changed else BASELINE
            if (info['atime_ns'], info['mtime_ns']) != expected:
                errors.append('touch object timestamp mismatch: ' + name)
    if spec['kind'] == 'directory' and sorted(p.name for p in (directory / 'object').iterdir()) != ['leaf']:
        errors.append('touch directory contents changed')
    measured_errno = (namespace_probe(directory / spec['operand'], spec['errno'])
                      if spec['errno'] else None)
    return errors, dict(objects=after, errno=measured_errno)


def restore(directory, row):
    """Restore only the authored owned directory, without following a symlink."""
    if not row.get('touch_objects') or row['touch_objects']['kind'] != 'directory':
        return
    path = directory / 'object'
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        path.chmod(0o700)
