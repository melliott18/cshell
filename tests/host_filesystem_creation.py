"""CSH-092 final creation modes under independently proved child umasks.

Expected permissions are authored from mkdir/mkfifo OPTIONS and chmod symbolic
mode rules. These are final-state checks, not transient-permission or ACL tests.
"""
import json
import os
import stat

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
    if row.get('parent_graph'):
        (directory / 'parent-alias').symlink_to('existing')
        row['creation_preserved'] = {}
        for name in ('existing', 'parent-alias', 'data', 'dangling'):
            info = (directory / name).lstat()
            row['creation_preserved'][name] = [info.st_dev, info.st_ino, info.st_mode]


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
    for name, identity in row.get('creation_preserved', {}).items():
        info = (directory / name).lstat()
        if [info.st_dev, info.st_ino, info.st_mode] != identity:
            errors.append('preserved graph identity/mode changed: ' + name)
    return marker, errors


def restore(directory, row):
    # Authored directories may deliberately lack read/search permissions. Restore
    # top-down only AFTER effect assertions, and also on setup/failure/timeout.
    if 'creation_mask' not in row:
        return
    # Only explicitly authored paths inside the private fixture are restored;
    # never follow a provider-created symlink during cleanup.
    names = set(row.get('effects', {})) if row.get('parent_graph') else set()
    names.update(('created', 'first', 'last', 'existing', 'existing/new',
                 'existing/new/a', 'existing/new/a/leaf', '.creation-probe-dir'))
    for name in sorted(names, key=lambda value: (value.count('/'), value)):
        # Check every ancestor with lstat before touching the final object.
        path = directory
        for part in name.split('/'):
            path /= part
            try:
                info = path.lstat()
            except FileNotFoundError:
                break
            if not stat.S_ISDIR(info.st_mode):
                break
        else:
            path.chmod(0o700)


def omitted_who_cases():
    """CSH-107: chmod EXTENDED DESCRIPTION with the creation initial modes.

    Omitted who masks bits being added/removed; '=' first clears ALL bits.
    The literal triples below are in mask order 027, 077, 777. Expected modes
    are authored independently of chmod, mkdir, mkfifo or a mode parser.
    """
    for utility, kind in (('mkdir', 'directory'), ('mkfifo', 'fifo')):
        directory = utility == 'mkdir'
        modes = [
            ('remove-write', '-w', (0o577, 0o577, 0o777) if directory else (0o466, 0o466, 0o666)),
            ('explicit-remove-write', 'a-w', (0o555,) * 3 if directory else (0o444,) * 3),
            ('clear-add', 'a=,+rwx', (0o750, 0o700, 0o000)),
            ('explicit-clear-add', 'a=,a+rwx', (0o777,) * 3),
            ('assign', '=rw', (0o640, 0o600, 0o000)),
            ('explicit-assign', 'a=rw', (0o666,) * 3),
            ('copy-add', 'u=rw,g=r,o=,+u', (0o640,) * 3),
            ('copy-remove', '-u', (0o027, 0o077, 0o777) if directory else (0o026, 0o066, 0o666)),
            ('copy-assign', 'u=rw,g=r,o=,=u', (0o640, 0o600, 0o000)),
            ('conditional-execute', 'a-rwx,+X', (0o110, 0o100, 0o000) if directory else (0o000,) * 3),
            ('empty-assign', '=', (0o000,) * 3),
            ('action-list', 'a=,+rw-x', (0o640, 0o600, 0o000)),
        ]
        for name, mode, expected in modes:
            for mask, permissions in zip((0o027, 0o077, 0o777), expected):
                yield case(utility, f'omitted-who-{mask:03o}-{name}',
                           ['-m', mode, 'created'], ticket='CSH-107',
                           creation_mask=mask,
                           effects={'created': {'type': kind, 'mode': permissions}})


def parent_graph_cases():
    """CSH-108: mkdir OPTIONS -p, final modes, and error continuation.

    Literal intermediate/final modes are independent of the utility. Existing
    operands are not chmod targets; symlinks in path prefixes resolve normally.
    """
    for mask, parent_mode, default_mode, copy_mode in (
            (0o027, 0o750, 0o750, 0o640),
            (0o077, 0o700, 0o700, 0o600),
            (0o777, 0o300, 0o000, 0o000)):
        for mode_name, mode, leaf_mode in (
                ('default', None, default_mode), ('owner', '700', 0o700),
                ('empty', 'a=', 0o000), ('copy', 'u=rw,g=r,o=,=u', copy_mode)):
            for graph in ('shared', 'duplicate', 'symlink', 'file-obstruction', 'dangling-obstruction'):
                effects = {'existing': {'type': 'directory', 'mode': 0o751},
                           'parent-alias': {'type': 'link', 'link': 'existing'},
                           'data': {'type': 'file', 'mode': 0o640, 'content': DATA},
                           'dangling': {'type': 'link', 'link': 'absent'},
                           'absent': {'type': 'absent'}}
                if graph == 'shared':
                    operands = ['existing/new/a/left', 'existing/new/a/right']
                    parents = ['existing/new', 'existing/new/a']
                    leaves = operands
                elif graph == 'duplicate':
                    operands = ['existing', 'existing/new/a/leaf', 'existing/new/a/leaf', 'existing']
                    parents = ['existing/new', 'existing/new/a']
                    leaves = ['existing/new/a/leaf']
                elif graph == 'symlink':
                    operands = ['parent-alias', 'parent-alias/new/a/leaf']
                    parents = ['existing/new', 'existing/new/a']
                    leaves = ['existing/new/a/leaf']
                else:
                    obstruction = 'data' if graph == 'file-obstruction' else 'dangling'
                    operands = ['existing/new/a/left', obstruction + '/child', 'existing/new/a/right']
                    parents = ['existing/new', 'existing/new/a']
                    leaves = ['existing/new/a/left', 'existing/new/a/right']
                effects.update({name: {'type': 'directory', 'mode': parent_mode} for name in parents})
                effects.update({name: {'type': 'directory', 'mode': leaf_mode} for name in leaves})
                failure = graph.endswith('obstruction')
                yield case('mkdir', f'parent-graph-{mask:03o}-{mode_name}-{graph}',
                           ['-p'] + ([] if mode is None else ['-m', mode]) + operands,
                           ticket='CSH-108', creation_mask=mask, creation_parents=True,
                           parent_graph=graph, effects=effects,
                           status='nonzero' if failure else 0,
                           err='nonempty' if failure else b'')
