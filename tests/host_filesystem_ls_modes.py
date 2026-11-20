"""CSH-127: base-profile ls permission fields on private owned objects.

No object is executed. Sticky-bit t/T rendering is XSI and is not qualified.
"""
import os
import stat

from host_filesystem_cases import case
import host_filesystem_ls_long as long
from host_filesystem_metadata import measure

# Cross both special bits with their corresponding execute/search bits.
MODES = tuple(0o600 | owner | group | other
              for owner in (0, 0o100, 0o4000, 0o4100)
              for group in (0, 0o10, 0o2000, 0o2010)
              for other in (0, 0o7))


def cases():
    for kind in ('regular', 'directory'):
        for mode in MODES:
            for form in ('l', 'n'):
                yield case('ls', f'modes-{kind}-{mode:04o}-{form}',
                           ['-d', '-' + form, 'meta/' + kind],
                           ticket='CSH-127', out='ls-modes', env={'TZ': 'UTC0'},
                           ls_modes=dict(kind=kind, form=form, mode=mode))


def setup(directory, row):
    if 'ls_modes' not in row:
        return None
    spec = row['ls_modes']
    environment = long.setup(directory, dict(ls_long=spec))
    path = directory / 'meta' / spec['kind']
    path.chmod(spec['mode'])
    info = measure(path)
    if stat.S_IMODE(info['mode']) != spec['mode']:
        raise OSError('requested permission bits were not retained by the filesystem')
    if (info['uid'], info['gid']) != (os.geteuid(), os.getegid()):
        raise OSError('permission witness requires the fixture user and primary group')
    environment['before'][spec['kind']] = info
    environment['ctime_ns'] = path.lstat().st_ctime_ns
    environment['probe'] = 'pre-exec chmod/lstat exact mode readback, owned identity, account names and UTC timestamp'
    return environment


output_matches = long.output_matches


def verify(directory, environment):
    if environment is None:
        return [], None
    path = directory / 'meta' / environment['spec']['kind']
    # The matrix includes directories without owner search permission; they
    # are empty and listing their entries requires only owner read permission.
    errors, after = long.verify(directory, environment)
    after[environment['spec']['kind']]['ctime_ns'] = path.lstat().st_ctime_ns
    if after[environment['spec']['kind']]['ctime_ns'] != environment['ctime_ns']:
        errors.append('permission listing ctime changed')
    return errors, after
