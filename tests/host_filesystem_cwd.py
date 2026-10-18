"""CSH-091 physical pwd and CSH-094 logical fallback after namespace changes.

The helper changes only its own cwd, never PWD. Physical cases end in -P;
logical cases prove inherited PWD cannot identify the changed cwd.
"""
import json
import os
from pathlib import Path

from host_filesystem_cases import case

MARKER = '.cwd-environment.json'


def cases():
    return _cases(False)


def logical_cases():
    """Inherited PWD is absent or names the fixture root, never the changed cwd."""
    return _cases(True)


def _cases(logical):
    for action in ('rename-leaf', 'rename-parent', 'delete-leaf', 'delete-parent'):
        deleted = action.startswith('delete')
        for options in (([], ['-L'], ['-P', '-L']) if logical else (['-P'], ['-L', '-P'])):
            effects = {'cwd-parent/cwd-leaf': {'type': 'absent'},
                       'cwd-parent': {'type': 'absent' if action.endswith('parent') else 'directory'}}
            if not deleted:
                effects['cwd-renamed' + ('/cwd-leaf' if action.endswith('parent') else '')] = {'type': 'directory'}
            suffix = '-default' if not options else '-last-' + options[-1][1:] if len(options) == 2 else options[0]
            extra = dict(logical_fallback=True) if logical else {}
            yield case('pwd', ('cwd-logical-' if logical else 'cwd-') + action + suffix,
                       options, ticket='CSH-094' if logical else 'CSH-091', cwd_action=action, **extra,
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
             and type(marker.get('getcwd_errno')) is int
             and type(marker.get('old_path_errno')) is int
             and marker.get('getcwd_errno') == (errno.ENOENT if deleted else 0)
             and marker.get('getcwd') == (None if deleted else expected_path(directory, action)))
    if row.get('logical_fallback'):
        pwd = marker.get('pwd')
        root = directory.stat()
        root_identity = dict(device=root.st_dev, inode=root.st_ino)
        valid = (valid and marker.get('logical_fallback') is True
                 and 'pwd' in marker and 'pwd_after' in marker and pwd == marker['pwd_after']
                 and 'pwd_identity' in marker
                 and ((pwd is None and marker['pwd_identity'] is None)
                      or (isinstance(pwd, str) and pwd == str(directory.resolve())
                          and marker['pwd_identity'] == root_identity
                          and root_identity != before)))
    if not deleted:
        info = os.stat(expected_path(directory, action))
        valid = valid and before == dict(device=info.st_dev, inode=info.st_ino)
    return marker, [] if valid else ['cwd environment was not independently armed']
