"""CSH-130: exact mtime/atime selection, nanosecond sorting and C ties.

Private regular operands only. No ctime, clock-boundary or filesystem-range claim.
"""
import grp
import os
import pwd
import re
import stat

from host_filesystem_cases import case
from host_filesystem_metadata import measure, stamp, STAMP

NAMES = ('alpha', 'bravo', 'charlie', 'delta')
# Access and modification orders differ from each other and from name order.
RANKS = dict(alpha=(3, 1), bravo=(1, 3), charlie=(2, 2), delta=(1, 3))
FORMS = ('1t', '1tu', '1ut', 'lt', 'ltu', 'lut', 'nt', 'ntu', 'nut', 'lu', 'nu', 'l')
SCALES = dict(days=86400 * 10**9, nanoseconds=1)


def cases():
    for precision in SCALES:
        for form in FORMS:
            for reverse in (False, True):
                yield case('ls', f'times-{precision}-{form}-' + ('reverse' if reverse else 'forward'),
                           ['-d', *['-' + flag for flag in form], *(['-r'] if reverse else []),
                            *['times/' + name for name in reversed(NAMES)]],
                           ticket='CSH-130', out='ls-times', env={'TZ': 'UTC0'},
                           ls_times=dict(precision=precision, form=form, reverse=reverse))


def setup(directory, row):
    if 'ls_times' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('time listing witnesses require one unprivileged identity')
    root = directory / 'times'
    root.mkdir()
    spec = row['ls_times']
    contents = {}
    for name in NAMES:
        path = root / name
        data = (name + '\n').encode('ascii')
        path.write_bytes(data)
        path.chmod(0o640)
        if path.read_bytes() != data:
            raise OSError('time listing content setup failed')
        contents[name] = data.hex()
        access, modified = RANKS[name]
        # All content reads precede stamping: access time is part of the oracle.
        stamp(path, STAMP + access * SCALES[spec['precision']],
              STAMP + modified * SCALES[spec['precision']])
    before = {name: measure(root / name) for name in NAMES}
    ctimes = {name: (root / name).lstat().st_ctime_ns for name in NAMES}
    if sorted(os.listdir(root)) != list(NAMES):
        raise OSError('time listing names differ from authored names')
    for name, info in before.items():
        if not stat.S_ISREG(info['mode']) or stat.S_IMODE(info['mode']) != 0o640 or info['uid'] != os.geteuid():
            raise OSError('time listing type/mode/ownership probe failed')
    try:
        owner = pwd.getpwuid(before['alpha']['uid']).pw_name
        groups = {name: grp.getgrgid(info['gid']).gr_name for name, info in before.items()}
    except KeyError as error:
        raise OSError('time listing requires resolvable owner and group') from error
    if any(not value or value.isdecimal() or any(not 32 < ord(c) < 127 for c in value)
           for value in (owner, *groups.values())):
        raise OSError('time listing requires distinct printable ASCII account names')
    return dict(spec=spec, before=before, ctimes=ctimes, contents=contents,
                entries=list(NAMES), owner=owner, groups=groups,
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec authored bytes, exact utime/lstat nanoseconds, types/modes/identities and account names')


def ordered_names(spec):
    if 't' in spec['form']:
        field = 0 if 'u' in spec['form'] else 1
        names = sorted(NAMES, key=lambda name: (-RANKS[name][field], name))
    else:
        names = list(NAMES)
    return list(reversed(names)) if spec['reverse'] else names


def output_matches(environment, output):
    spec = environment['spec']
    names = ordered_names(spec)
    if not any(flag in spec['form'] for flag in 'ln'):
        return output == ''.join('times/' + name + '\n' for name in names).encode('ascii')
    patterns = []
    for name in names:
        info = environment['before'][name]
        numeric = 'n' in spec['form']
        owner = str(info['uid']) if numeric else environment['owner']
        group = str(info['gid']) if numeric else environment['groups'][name]
        # All dates are authored interior January 2000 UTC, independent of ls.
        rank = RANKS[name][0 if 'u' in spec['form'] else 1]
        day = 2 + rank if spec['precision'] == 'days' else 2
        fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
                  str(info['nlink']).encode(), re.escape(owner.encode('ascii')),
                  re.escape(group.encode('ascii')), str(info['size']).encode(),
                  b'Jan', str(day).encode(), b'2000', ('times/' + name).encode()]
        patterns.append(rb'[ \t]+'.join(fields) + b'\n')
    return re.fullmatch(b''.join(patterns), output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'times'
    # Snapshot every timestamp before the verifier reads any contents.
    after = {name: measure(root / name) for name in NAMES}
    errors = []
    for name, before in environment['before'].items():
        if after[name] != before:
            errors.append('time listing metadata changed: ' + name)
        after[name]['ctime_ns'] = (root / name).lstat().st_ctime_ns
        if after[name]['ctime_ns'] != environment['ctimes'][name]:
            errors.append('time listing ctime changed: ' + name)
        if (root / name).read_bytes().hex() != environment['contents'][name]:
            errors.append('time listing bytes changed: ' + name)
    if sorted(os.listdir(root)) != environment['entries']:
        errors.append('time listing directory entries changed')
    return errors, after
