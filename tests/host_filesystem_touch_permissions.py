"""CSH-112: ordinary owner-mode touch errors and explicit-time permissions.

The fixtures use authored UTC seconds and kernel probes, not another utility.
No ACLs, alternate identities, injected faults or capacity limits are supplied.
"""
import errno
import os
import stat

from host_filesystem_cases import case
from host_filesystem_reference import BASELINE, SELECTIONS

TARGET = 1000000000000000000  # 2001-09-09 01:46:40 UTC, in nanoseconds.
CONTENT = b'preserved timestamp witness\n'


def cases():
    for boundary, existing, no_create, mode in (
            ('search-existing', True, False, 0o600),
            ('search-missing', False, False, 0o600),
            ('create-denied', False, False, 0o500),
            ('no-create', False, True, 0o500),
            ('owner-no-write', True, False, 0o500)):
        for selection, flags in SELECTIONS:
            failure = boundary in ('search-existing', 'search-missing', 'create-denied')
            stamps = (BASELINE[0] if flags == ['-m'] else TARGET,
                      BASELINE[1] if flags == ['-a'] else TARGET)
            yield case('touch', 'permission-' + boundary + '-' + selection,
                       [*flags, *(['-c'] if no_create else []), '-t', '200109090146.40',
                        'first', 'guard/target', 'last'], ticket='CSH-112',
                       files={'first': CONTENT, 'last': CONTENT},
                       touch_permission=dict(boundary=boundary, existing=existing, mode=mode,
                                             target_ns=stamps, failure=failure),
                       effects={name: dict(type='file', content=CONTENT, mode=0o400)
                                for name in ('first', 'last', *(['guard/target'] if existing else []))} |
                               ({} if existing else {'guard/target': dict(type='absent')}),
                       status='nonzero' if failure else 0, err='nonempty' if failure else b'')


def snapshot(directory, spec):
    result = {}
    for name in ('guard', 'first', 'last', *(['guard/target'] if spec['existing'] else [])):
        info = (directory / name).lstat()
        result[name] = dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                            nlink=info.st_nlink, atime_ns=info.st_atime_ns, mtime_ns=info.st_mtime_ns)
    return result


def setup(directory, row):
    spec = row.get('touch_permission')
    if spec is None:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('touch permission witnesses require one unprivileged identity')
    (directory / 'guard').mkdir(mode=0o700)
    if spec['existing']:
        (directory / 'guard/target').write_bytes(CONTENT)
    probes = []
    for name in ('first', 'last', *(['guard/target'] if spec['existing'] else [])):
        path = directory / name
        if path.read_bytes() != CONTENT:
            raise OSError('touch fixture content mismatch')
        path.chmod(0o400)
        # Owning the file permits explicit timestamps without write access.
        denied(lambda: write_open(path))
        for stamps in ((TARGET, TARGET), BASELINE):
            os.utime(path, ns=stamps)
            info = path.stat()
            actual = (info.st_atime_ns, info.st_mtime_ns)
            if actual != stamps:
                raise OSError('filesystem cannot represent authored touch timestamps')
            probes.append(dict(path=name, requested_ns=stamps, observed_ns=actual))
    return dict(before=snapshot(directory, spec), probes=probes,
                uid=os.getuid(), euid=os.geteuid(), write_errno=errno.EACCES)


def write_open(path, create=False):
    descriptor = os.open(path, os.O_WRONLY | (os.O_CREAT | os.O_EXCL if create else 0), 0o600)
    os.close(descriptor)


def denied(operation):
    try:
        operation()
    except OSError as error:
        if error.errno != errno.EACCES:
            raise
    else:
        raise OSError('touch permission probe unexpectedly succeeded')


def arm(directory, row):
    spec = row.get('touch_permission')
    if spec is None:
        return None
    guard = directory / 'guard'
    probe = guard / '.create-probe'
    try:
        guard.chmod(spec['mode'])
        if spec['mode'] == 0o600:
            denied(lambda: (guard / 'target').stat())
            operation = 'stat through denied search'
        else:
            denied(lambda: write_open(probe, create=True))
            operation = 'create in denied parent'
    finally:
        restore(directory, row)
        probe.unlink(missing_ok=True)
    guard.chmod(spec['mode'])
    return dict(phase='armed', errno=errno.EACCES, probe=operation,
                mode=stat.S_IMODE(guard.lstat().st_mode), uid=os.getuid(), euid=os.geteuid())


def restore(directory, row):
    if 'touch_permission' not in row:
        return
    guard = directory / 'guard'
    try:
        info = guard.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        guard.chmod(0o700)


def verify(directory, row, environment):
    if environment is None:
        return [], None
    spec = row['touch_permission']
    mode = stat.S_IMODE((directory / 'guard').lstat().st_mode)
    restore(directory, row)
    # Capture all timestamps before content reads can change access times.
    after = snapshot(directory, spec)
    errors = [] if mode == spec['mode'] else ['touch permission guard mode changed']
    for name, before in environment['before'].items():
        info = after[name]
        if any(info[k] != before[k] for k in ('device', 'inode', 'mode', 'nlink')):
            errors.append('touch permission identity mismatch: ' + name)
        if name != 'guard':
            stamps = BASELINE if name == 'guard/target' and spec['failure'] else spec['target_ns']
            if (info['atime_ns'], info['mtime_ns']) != tuple(stamps):
                errors.append('touch permission timestamp mismatch: ' + name)
    return errors, dict(armed_mode=mode, objects=after)
