"""CSH-084 private permission environments and authored residual witnesses.

These cases require an unprivileged identity. The parent proves EACCES before
dispatch, restores access before checking effects, and always restores it before
cleanup. This is ordinary owner-mode denial, not ACL/privileged qualification.
"""
import errno
import os

from host_filesystem_cases import case, DATA


def cases():
    def witness(utility, name, args, **kw):
        return case(utility, 'residual-' + name, args, ticket='CSH-084', **kw)

    denials = [
        ('cp', 'read-denied', ['denied/leaf', 'copy'], {'copy': {'type': 'absent'}}),
        ('cp', 'write-denied', ['data', 'denied/copy'], {'data': {'content': DATA}, 'denied/copy': {'type': 'absent'}}),
        ('ln', 'create-denied', ['data', 'denied/new'], {'data': {'nlink': 1}, 'denied/new': {'type': 'absent'}}),
        ('mv', 'destination-denied', ['data', 'denied/new'], {'data': {'content': DATA}, 'denied/new': {'type': 'absent'}}),
        ('mkdir', 'parent-denied', ['denied/new'], {'denied/new': {'type': 'absent'}}),
        ('mkfifo', 'parent-denied', ['denied/new'], {'denied/new': {'type': 'absent'}}),
        ('pathchk', 'prefix-denied', ['denied/new'], {}),
        ('realpath', 'prefix-denied', ['-e', 'denied/leaf'], {}),
        ('readlink', 'prefix-denied', ['denied/link'], {'denied/link': {'link': 'leaf'}}),
        ('rm', 'force-denied', ['-f', 'denied/leaf'], {'denied/leaf': {'content': b'private\n'}}),
        ('rmdir', 'parent-denied', ['denied/empty'], {'denied/empty': {'type': 'directory'}}),
        ('touch', 'prefix-denied', ['-t', '200109090146.40', 'denied/leaf'],
         {'denied/leaf': {'content': b'private\n', 'mtime': 900000000}}),
        ('find', 'operand-denied', ['denied/leaf', '-print'], {}),
        ('ls', 'operand-denied', ['denied/leaf'], {}),
    ]
    for utility, name, args, effects in denials:
        yield witness(utility, name, args, status='nonzero', err='nonempty',
                      permission_denied=True, effects=effects)

    for utility, args in [('basename', ['a/b']), ('dirname', ['a/b'])]:
        for action in ('closed-output', 'broken-pipe'):
            yield witness(utility, action, args, status='nonzero', err='nonempty', io_action=action)

    # The database and bytes are independent of the selected file implementation.
    # string/byte and > continuation syntax are specified by EXTENDED DESCRIPTION.
    samples = [
        ('string', b'0\tstring\tCSH84\tfixture-format\n', b'CSH84\x00\xff', b'fixture-format'),
        ('continuation', b'0\tstring\tCSH84\tfixture-format\n>5\tbyte\t=7\tversion-seven\n',
         b'CSH84\x07\x00', b'fixture-format version-seven'),
        ('offset', b'0x2\tstring\tCSH84\toffset-format\n', b'xxCSH84\x00', b'offset-format'),
        ('escaped', b'0\tstring\tA\\ B\tspace-format\n', b'A B\x00', b'space-format'),
    ]
    for name, magic, sample, message in samples:
        yield witness('file', 'magic-' + name, ['-m', 'magic', 'sample'],
                      files={'magic': magic, 'sample': sample}, out=b'sample: ' + message + b'\n')

    # Opaque bytes in a link target need not name an existing file. Args stay
    # portable; only the target contains invalid UTF-8, tested in both locales.
    for utf8 in (False, True):
        for no_newline in (False, True):
            target = b'byte-\xff-\xfe-\x80'
            yield witness('readlink', 'opaque-' + ('utf8' if utf8 else 'c') + ('-n' if no_newline else ''),
                          (['-n'] if no_newline else []) + ['opaque'],
                          byte_link=target, out=target + (b'' if no_newline else b'\n'), utf8=utf8)


def setup(directory, row):
    if row.get('byte_link') is not None:
        os.symlink(row['byte_link'], os.fsencode(directory / 'opaque'))
    if row.get('permission_denied'):
        if os.geteuid() == 0:
            raise OSError('owner-mode denial requires an unprivileged fixture identity')
        denied = directory / 'denied'
        denied.mkdir(mode=0o700)
        (denied / 'leaf').write_bytes(b'private\n')
        os.utime(denied / 'leaf', (900000000, 900000000))
        (denied / 'empty').mkdir()
        (denied / 'link').symlink_to('leaf')


def arm(directory, row):
    if not row.get('permission_denied'):
        return None
    denied = directory / 'denied'
    denied.chmod(0)
    try:
        (denied / 'leaf').stat()
    except OSError as error:
        if error.errno != errno.EACCES:
            raise
        return dict(phase='armed', errno=error.errno, uid=os.getuid(), euid=os.geteuid(),
                    gid=os.getegid(), groups=os.getgroups(), mode=0,
                    probe='stat denied/leaf', scope='private owner-mode search denial')
    raise OSError('permission probe unexpectedly succeeded')


def restore(directory, row):
    if row.get('permission_denied') and (directory / 'denied').exists():
        (directory / 'denied').chmod(0o700)
