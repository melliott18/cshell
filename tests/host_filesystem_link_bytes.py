"""CSH-106: authored readlink bytes, newline policy and bounded buffer growth.

POSIX readlink DESCRIPTION requires the link contents without following it.
Expected bytes are authored here, never copied from a provider's output. The
pre-exec syscall readback proves that the filesystem stored the intended bytes.
No NUL, actual filesystem limit, libc fault or arbitrary repertoire is claimed.
"""
import os
import stat

from host_filesystem_cases import case


def targets():
    for byte in range(1, 256):
        yield f'byte-{byte:02x}', b'absent/A' + bytes([byte]) + b'Z'
    # Valid multibyte boundaries, non-normalized text and invalid UTF-8 forms.
    for name, data in [
        ('utf8-two', b'\xc2\x80\xdf\xbf'),
        ('utf8-three', b'\xe0\xa0\x80\xed\x9f\xbf\xee\x80\x80\xef\xbf\xbf'),
        ('utf8-four', b'\xf0\x90\x80\x80\xf4\x8f\xbf\xbf'),
        ('normalization', b'\xc3\xa9-e\xcc\x81'),
        ('overlong', b'\xc0\xaf\xe0\x80\xaf\xf0\x80\x80\xaf'),
        ('surrogate', b'\xed\xa0\x80\xed\xbf\xbf'),
        ('above-unicode', b'\xf4\x90\x80\x80\xf5\x80\x80\x80'),
        ('incomplete', b'\xc2/\xe0\xa0/\xf0\x90\x80'),
        ('newlines', b'\n\r\n\n'),
        ('shell-text', b"'\"`$() *?[a]\\ -> target"),
    ]:
        yield name, b'absent/' + data
    # Straddle two growth boundaries with nonzero mixed bytes. These are
    # authored sizes, not assertions about a filesystem's maximum link length.
    for length in (255, 256, 257, 511, 512, 513, 1023):
        yield f'length-{length}', (b'absent/' + bytes(range(1, 256)) * 5)[:length]


def cases():
    for name, target in targets():
        for utf8 in (False, True):
            for no_newline in (False, True):
                yield case('readlink', 'link-bytes-' + name +
                           ('-utf8' if utf8 else '-c') + ('-n' if no_newline else ''),
                           (['-n'] if no_newline else []) + ['opaque'],
                           ticket='CSH-106', byte_link=target, link_bytes=True,
                           utf8=utf8, out=target + (b'' if no_newline else b'\n'))


def observe(directory):
    path = os.fsencode(directory / 'opaque')
    info = os.lstat(path)
    if not stat.S_ISLNK(info.st_mode):
        raise OSError('readlink fixture is no longer a symbolic link')
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                size=info.st_size, target_hex=os.readlink(path).hex())


def setup(directory, row):
    if not row.get('link_bytes'):
        return None
    observed = observe(directory)
    if observed['target_hex'] != row['byte_link'].hex() or observed['size'] != len(row['byte_link']):
        raise OSError('authored link bytes readback mismatch')
    return dict(phase='armed', before=observed,
                probe='lstat and bytes-path readlink on private symbolic link',
                scope='authored bytes and lengths; no filesystem exhaustion or libc injection')


def verify(directory, environment):
    if environment is None:
        return [], None
    observed = observe(directory)
    errors = [] if observed == environment['before'] else ['symbolic link changed during execution']
    return errors, observed
