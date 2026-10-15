"""CSH-091 physical pwd after private directory namespace changes.

The helper changes only its own cwd. No PWD assignment or logical-mode claim:
POSIX makes application changes to PWD unspecified. Both option forms end in -P.
"""
import json
import os
from pathlib import Path

from host_filesystem_cases import case

MARKER = '.cwd-environment.json'


def cases():
    for action in ('rename-leaf', 'rename-parent', 'delete-leaf', 'delete-parent'):
        deleted = action.startswith('delete')
        for options in (['-P'], ['-L', '-P']):
            effects = {'cwd-parent/cwd-leaf': {'type': 'absent'},
                       'cwd-parent': {'type': 'absent' if action.endswith('parent') else 'directory'}}
            if not deleted:
                effects['cwd-renamed' + ('/cwd-leaf' if action.endswith('parent') else '')] = {'type': 'directory'}
            yield case('pwd', 'cwd-' + action + ('-last-P' if len(options) == 2 else '-P'),
                       options, ticket='CSH-091', cwd_action=action,
                       out=b'' if deleted else 'cwd-renamed',
                       status='nonzero' if deleted else 0,
                       err='nonempty' if deleted else b'', effects=effects)


def setup(directory, row):
    if row.get('cwd_action'):
        leaf = directory / 'cwd-parent/cwd-leaf'
        leaf.mkdir(parents=True)
        info = leaf.stat()
        row['cwd_identity'] = dict(device=info.st_dev, inode=info.st_ino)


def expected_path(directory, action):
    return str(directory.resolve() / 'cwd-renamed') + ('/cwd-leaf' if action.endswith('parent') else '')


def verify(directory, row, provider):
    """A setup/exec failure must never pass as the expected pwd error."""
    marker = json.loads((directory / MARKER).read_text())
    import errno
    if not isinstance(marker, dict):
        raise ValueError('cwd marker must be an object')
    action = row['cwd_action']
    deleted = action.startswith('delete')
    before, after = marker.get('before'), marker.get('after')
    valid = (marker.get('phase') == 'armed' and marker.get('action') == action
             and marker.get('provider') == provider and marker.get('old_path_errno') == errno.ENOENT
             and isinstance(before, dict) and set(before) == {'device', 'inode'}
             and all(type(v) is int for v in before.values()) and before == after == row['cwd_identity']
             and type(marker.get('pid')) is int and marker['pid'] > 0
             and marker.get('getcwd_errno') == (errno.ENOENT if deleted else 0)
             and marker.get('getcwd') == (None if deleted else expected_path(directory, action)))
    if not deleted:
        info = os.stat(expected_path(directory, action))
        valid = valid and before == dict(device=info.st_dev, inode=info.st_ino)
    return marker, [] if valid else ['cwd environment was not independently armed']
