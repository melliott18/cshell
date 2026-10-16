"""CSH-092 final creation modes under independently proved child umasks.

Expected permissions are authored from mkdir/mkfifo OPTIONS and chmod symbolic
mode rules. These are final-state checks, not transient-permission or ACL tests.
"""
import json
import os

from host_filesystem_cases import case, DATA

MARKER = '.creation-environment.json'


def cases():
    for utility, kind, initial in [('mkdir', 'directory', 0o777), ('mkfifo', 'fifo', 0o666)]:
        for mask in (0o027, 0o077):
            # Explicit who ignores umask; +X distinguishes a directory from a
            # FIFO whose assumed initial mode has no execute bits.
            for name, mode, expected in [
                ('default', None, initial & ~mask),
                ('remove-write', 'go-w', initial & ~0o022),
                ('copy-sequence', 'u=rw,g=u,o=g,o-w', 0o664),
                ('conditional-execute', 'a-x,a+X', initial),
                ('copy-execute-clear', 'u=rx,g=u,o=', 0o550),
            ]:
                yield case(utility, f'creation-{mask:03o}-{name}',
                           ([] if mode is None else ['-m', mode]) + ['created'],
                           ticket='CSH-092', creation_mask=mask,
                           effects={'created': {'type': kind, 'mode': expected}})
        yield case(utility, 'creation-existing-middle-continue',
                   ['-m', 'u=rw,g=u,o=g,o-w', 'first', 'data', 'last'],
                   ticket='CSH-092', creation_mask=0o027, status='nonzero', err='nonempty',
                   effects={'first': {'type': kind, 'mode': 0o664},
                            'data': {'type': 'file', 'content': DATA, 'mode': 0o640},
                            'last': {'type': kind, 'mode': 0o664}})
    for mask in (0o027, 0o777):
        for explicit in (False, True):
            intermediate = (0o300 | ~mask) & 0o777
            yield case('mkdir', f'creation-parents-{mask:03o}-' + ('explicit' if explicit else 'default'),
                       ['-p'] + (['-m', 'u=rwx,g=rx,o='] if explicit else []) + ['existing/new/a/leaf'],
                       ticket='CSH-092', creation_mask=mask, creation_parents=True,
                       effects={'existing': {'type': 'directory', 'mode': 0o751},
                                'existing/new': {'type': 'directory', 'mode': intermediate},
                                'existing/new/a': {'type': 'directory', 'mode': intermediate},
                                'existing/new/a/leaf': {'type': 'directory', 'mode': 0o750 if explicit else 0o777 & ~mask}})


def setup(directory, row):
    if 'creation_mask' not in row:
        return
    if os.geteuid() == 0:
        raise OSError('creation witnesses require an unprivileged fixture identity')
    if row.get('creation_parents'):
        existing = directory / 'existing'
        existing.mkdir()
        existing.chmod(0o751)
        info = existing.stat()
        row['creation_existing_identity'] = [info.st_dev, info.st_ino]


def verify(directory, row, provider):
    marker = json.loads((directory / MARKER).read_text())
    mask = row['creation_mask']
    expected = dict(phase='armed', provider=provider, requested_mask=mask,
                    observed_mask=mask, directory_mode=0o777 & ~mask,
                    fifo_mode=0o666 & ~mask, uid=os.getuid(), euid=os.geteuid())
    valid = (isinstance(marker, dict) and all(marker.get(k) == v and type(marker.get(k)) is type(v)
                                              for k, v in expected.items())
             and type(marker.get('pid')) is int and marker['pid'] > 0)
    errors = [] if valid else ['creation mask was not independently armed']
    if row.get('creation_parents'):
        info = (directory / 'existing').stat()
        if [info.st_dev, info.st_ino] != row['creation_existing_identity']:
            errors.append('existing parent identity changed')
    return marker, errors


def restore(directory, row):
    # Authored directories may deliberately lack read/search permissions. Restore
    # top-down only AFTER effect assertions, and also on setup/failure/timeout.
    if 'creation_mask' not in row:
        return
    for name in ('created', 'first', 'last', 'existing', 'existing/new',
                 'existing/new/a', 'existing/new/a/leaf', '.creation-probe-dir'):
        path = directory / name
        if path.is_dir() and not path.is_symlink():
            path.chmod(0o700)
