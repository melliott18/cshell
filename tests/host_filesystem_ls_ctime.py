"""CSH-131: measured status-change times, hard-link ties and -c/-u selection.

No clock changes, privileged timestamp setting, or filesystem resolution claim.
"""
import os
import time

from host_filesystem_cases import case
from host_filesystem_metadata import measure
import host_filesystem_ls_times as times
from host_filesystem_ls_dates import date_fields

FORMS = ('1tc', '1ct', 'ltc', 'lct', 'ntc', 'nct', 'lc', 'nc',
         '1tuc', '1tcu', 'ltuc', 'ltcu', 'ntuc', 'ntcu', 'luc', 'lcu')
CHANGE_ORDER = ('alpha', 'bravo', 'charlie')


def cases():
    for form in FORMS:
        for reverse in (False, True):
            yield case('ls', 'ctime-' + form + ('-reverse' if reverse else '-forward'),
                       ['-d', *['-' + flag for flag in form], *(['-r'] if reverse else []),
                        *['times/' + name for name in reversed(times.NAMES)]],
                       ticket='CSH-131', out='ls-ctime', env={'TZ': 'UTC0'},
                       ls_ctime=dict(form=form, reverse=reverse))


def advance(path, previous):
    # Require a strict measured order, never assume successive syscalls have
    # distinct timestamps. Even a filesystem with coarse ctime must terminate.
    deadline = time.monotonic() + 2
    while True:
        path.chmod(0o600)
        path.chmod(0o640)
        value = path.lstat().st_ctime_ns
        if value > previous:
            return value
        if time.monotonic() >= deadline:
            raise OSError('private filesystem cannot establish ordered change times')
        time.sleep(0.001)


def clock_matches(ctimes, now):
    return all(0 <= now - value < 86400 * 10**9 for value in ctimes.values())


def setup(directory, row):
    if 'ls_ctime' not in row:
        return None
    spec = row['ls_ctime']
    environment = times.setup(directory, dict(ls_times=dict(spec, precision='days')))
    root = directory / 'times'
    (root / 'delta').unlink()
    os.link(root / 'bravo', root / 'delta')
    previous = 0
    for name in CHANGE_ORDER:
        previous = advance(root / name, previous)
    before = {name: measure(root / name) for name in times.NAMES}
    ctimes = {name: (root / name).lstat().st_ctime_ns for name in times.NAMES}
    if not (ctimes['alpha'] < ctimes['bravo'] == ctimes['delta'] < ctimes['charlie']):
        raise OSError('change-time order or hard-link tie was not established')
    if (before['bravo']['dev'], before['bravo']['ino'], before['bravo']['nlink']) != (
            before['delta']['dev'], before['delta']['ino'], 2):
        raise OSError('change-time hard-link identity was not established')
    now = time.time_ns()
    if not clock_matches(ctimes, now):
        raise OSError('change-time clock category is not recent and nonfuture')
    environment['contents']['delta'] = environment['contents']['bravo']
    environment.update(spec=spec, before=before, ctimes=ctimes, clock_before_ns=now,
                       probe='pre-exec chmod/lstat strict ctime order, hard-link identity/tie, exact atime/mtime readback and account names')
    return environment


def selected_field(spec):
    return 'atime_ns' if spec['form'].rfind('u') > spec['form'].rfind('c') else 'ctime_ns'


def ordered_names(spec):
    names = list(times.NAMES)
    if 't' in spec['form']:
        names = (['alpha', 'charlie', 'bravo', 'delta'] if selected_field(spec) == 'atime_ns'
                 else ['charlie', 'bravo', 'delta', 'alpha'])
    return list(reversed(names)) if spec['reverse'] else names


def output_matches(environment, output):
    import re
    import stat
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
        access = selected_field(spec) == 'atime_ns'
        seconds = (info['atime_ns'] if access else environment['ctimes'][name]) // 10**9
        dates = date_fields(dict(age='old' if access else 'recent', offset_minutes=0), seconds)
        fields = [re.escape(stat.filemode(info['mode']).encode()) + rb'[+@.]?',
                  str(info['nlink']).encode(), re.escape(owner.encode('ascii')),
                  re.escape(group.encode('ascii')), str(info['size']).encode(),
                  *dates, ('times/' + name).encode()]
        patterns.append(rb'[ \t]+'.join(fields) + b'\n')
    return re.fullmatch(b''.join(patterns), output) is not None


def verify(directory, environment):
    if environment is None:
        return [], None
    errors, after = times.verify(directory, environment)
    now = time.time_ns()
    if not clock_matches(environment['ctimes'], now):
        errors.append('change-time clock category changed during execution')
    return errors, dict(measurements=after, clock_after_ns=now)
