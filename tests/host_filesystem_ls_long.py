"""CSH-126: long listings against filesystem and account-database probes.

Only existing owner/group names, old UTC timestamps and private objects are
qualified. XSI -g/-o, missing accounts and live clock boundaries remain open.
"""
import grp
import os
import pwd
import re
import stat

from host_filesystem_cases import case
from host_filesystem_metadata import setup as metadata_setup, measure, STAMP

KINDS = ('regular', 'hardlink', 'directory', 'fifo', 'symlink')
FORMATS = ('l', 'n', 'nl', 'ln', '1l', 'l1', 'Cl', 'ml', 'xl', 'Cn', 'mn', 'xn')


def cases():
    for kind in KINDS:
        for form in FORMATS:
            yield case('ls', f'long-{kind}-{form}',
                       ['-d', *['-' + flag for flag in form], 'meta/' + kind],
                       ticket='CSH-126', out='ls-long', env={'TZ': 'UTC0'},
                       ls_long=dict(kind=kind, form=form))


def setup(directory, row):
    if 'ls_long' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('long listing witnesses require one unprivileged identity')
    spec = row['ls_long']
    # Reuse only fixture construction; expectations do not come from ls.
    metadata_setup(directory, dict(metadata_environment=True, metadata_kind=spec['kind']))
    root = directory / 'meta'
    names = sorted(os.listdir(root))
    before = {name: measure(root / name) for name in names}
    info = before[spec['kind']]
    if info['uid'] != os.geteuid() or info['mtime_ns'] != STAMP:
        raise OSError('long listing ownership/timestamp probe failed')
    try:
        owner = pwd.getpwuid(info['uid']).pw_name
        group = grp.getgrgid(info['gid']).gr_name
    except KeyError as error:
        raise OSError('long listing requires resolvable owner and group') from error
    # Numeric-looking names would not distinguish named from numeric rendering.
    if any(not name or name.isdecimal() or not name.isascii() or
           any(ch.isspace() for ch in name) for name in (owner, group)):
        raise OSError('long listing requires distinct printable ASCII account names')
    if any(not all(32 < ord(ch) < 127 for ch in name) for name in (owner, group)):
        raise OSError('long listing account names contain control characters')
    contents = {name: (root / name).read_bytes() for name in names
                if stat.S_ISREG(before[name]['mode'])}
    links = {name: os.readlink(root / name) for name in names
             if stat.S_ISLNK(before[name]['mode'])}
    # Capture after the independent content reads; access times are excluded in
    # verification because providers/inspectors may legitimately update them.
    before = {name: measure(root / name) for name in names}
    return dict(spec=spec, before=before, contents={n: b.hex() for n, b in contents.items()},
                links=links, entries=names, owner=owner, group=group,
                uid=os.getuid(), euid=os.geteuid(),
                probe='pre-exec lstat, exact utime readback, getpwuid/getgrgid, bytes and link text')


def output_matches(environment, output):
    spec = environment['spec']
    info = environment['before'][spec['kind']]
    numeric = 'n' in spec['form']  # -l does not turn off an earlier -n.
    owner = str(info['uid']) if numeric else environment['owner']
    group = str(info['gid']) if numeric else environment['group']
    fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
              str(info['nlink']).encode(), re.escape(owner.encode('ascii')),
              re.escape(group.encode('ascii')), str(info['size']).encode(),
              b'Jan', b'2', b'2000', ('meta/' + spec['kind']).encode()]
    pattern = rb'[ \t]+'.join(fields)
    if spec['kind'] == 'symlink':
        pattern += rb' -> target'
    return re.fullmatch(pattern + b'\n', output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'meta'
    after = {name: measure(root / name) for name in environment['before']}
    errors = []
    for name, before in environment['before'].items():
        if any(after[name][key] != value for key, value in before.items() if key != 'atime_ns'):
            errors.append('long listing metadata changed: ' + name)
    for name, content in environment['contents'].items():
        if (root / name).read_bytes().hex() != content:
            errors.append('long listing bytes changed: ' + name)
    for name, target in environment['links'].items():
        if os.readlink(root / name) != target:
            errors.append('long listing link changed: ' + name)
    if sorted(os.listdir(root)) != environment['entries']:
        errors.append('long listing directory entries changed')
    if environment['spec']['kind'] == 'directory' and os.listdir(root / 'directory'):
        errors.append('long listing child entries changed')
    return errors, after
