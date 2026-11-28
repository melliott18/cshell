"""CSH-132: size/time sort precedence, ties and independent long-format dates.

Only bounded regular operands and a hard-link pair; no capacity/size-limit claim.
"""
import re
import stat
import time

from host_filesystem_cases import case
from host_filesystem_metadata import measure, stamp
from host_filesystem_ls_dates import date_fields
import host_filesystem_ls_ctime as ctime
import host_filesystem_ls_times as times

SIZES = dict(alpha=7, bravo=19, charlie=3, delta=19)
SORT_FORMS = ('S', 'St', 'tS', 'utS', 'tuS', 'ctS', 'tcS', 'uSt', 'cSt')


def cases():
    for output in ('1', 'l', 'n'):
        for sorting in SORT_FORMS:
            for reverse in (False, True):
                form = output + sorting
                yield case('ls', 'size-' + form + ('-reverse' if reverse else '-forward'),
                           ['-d', *['-' + flag for flag in form], *(['-r'] if reverse else []),
                            *['times/' + name for name in reversed(times.NAMES)]],
                           ticket='CSH-132', out='ls-size', env={'TZ': 'UTC0'},
                           ls_size=dict(form=form, reverse=reverse))


def setup(directory, row):
    if 'ls_size' not in row:
        return None
    spec = row['ls_size']
    environment = ctime.setup(directory, dict(ls_ctime=spec))
    root = directory / 'times'
    # Write each inode once. Content reads precede restoration of the authored
    # atime/mtime; changing bytes also invalidates the previous ctime snapshot.
    for name in ctime.CHANGE_ORDER:
        path = root / name
        data = name[:1].encode('ascii') * SIZES[name]
        path.write_bytes(data)
        if path.read_bytes() != data:
            raise OSError('size listing content setup failed')
        environment['contents'][name] = data.hex()
        info = environment['before'][name]
        stamp(path, info['atime_ns'], info['mtime_ns'])
    environment['contents']['delta'] = environment['contents']['bravo']
    previous = 0
    for name in ctime.CHANGE_ORDER:
        previous = ctime.advance(root / name, previous)
    before = {name: measure(root / name) for name in times.NAMES}
    ctimes = {name: (root / name).lstat().st_ctime_ns for name in times.NAMES}
    if any(before[name]['size'] != size for name, size in SIZES.items()):
        raise OSError('size listing sizes differ from authored bytes')
    if not (ctimes['alpha'] < ctimes['bravo'] == ctimes['delta'] < ctimes['charlie']):
        raise OSError('size listing change-time order or hard-link tie failed')
    now = time.time_ns()
    if not ctime.clock_matches(ctimes, now):
        raise OSError('size listing clock category is not recent and nonfuture')
    environment.update(spec=spec, before=before, ctimes=ctimes, clock_before_ns=now,
                       probe='pre-exec authored byte counts, exact utime/lstat readback, chmod ctime order and hard-link tie')
    return environment


def selected_field(spec):
    form = spec['form']
    if 'c' in form:
        return 'ctime_ns'
    return 'atime_ns' if 'u' in form else 'mtime_ns'


def ordered_names(spec):
    form = spec['form']
    # These authored forms put -c/-u before the final -S/-t. That option
    # therefore decides sorting without changing the long-listing time field.
    if form.rfind('S') > form.rfind('t'):
        names = sorted(times.NAMES, key=lambda name: (-SIZES[name], name))
    elif selected_field(spec) == 'ctime_ns':
        names = ['charlie', 'bravo', 'delta', 'alpha']
    else:
        field = 0 if selected_field(spec) == 'atime_ns' else 1
        names = sorted(times.NAMES, key=lambda name: (-times.RANKS[name][field], name))
    return list(reversed(names)) if spec['reverse'] else names


def output_matches(environment, output):
    spec = environment['spec']
    names = ordered_names(spec)
    if spec['form'].startswith('1'):
        return output == ''.join('times/' + name + '\n' for name in names).encode('ascii')
    patterns = []
    field = selected_field(spec)
    for name in names:
        info = environment['before'][name]
        numeric = spec['form'].startswith('n')
        owner = str(info['uid']) if numeric else environment['owner']
        group = str(info['gid']) if numeric else environment['groups'][name]
        seconds = (environment['ctimes'][name] if field == 'ctime_ns' else info[field]) // 10**9
        dates = date_fields(dict(age='recent' if field == 'ctime_ns' else 'old', offset_minutes=0), seconds)
        fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
                  str(info['nlink']).encode(), re.escape(owner.encode('ascii')),
                  re.escape(group.encode('ascii')), str(SIZES[name]).encode(),
                  *dates, ('times/' + name).encode()]
        patterns.append(rb'[ \t]+'.join(fields) + b'\n')
    return re.fullmatch(b''.join(patterns), output) is not None


def verify(directory, environment):
    return ctime.verify(directory, environment)
