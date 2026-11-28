"""CSH-128: interior recent, old and future ls dates in two fixed zones.

No six-month/now boundary, clock adjustment, DST or timestamp-range claim.
"""
from datetime import datetime, timedelta, timezone
import os
import time

from host_filesystem_cases import case
import host_filesystem_ls_long as long
from host_filesystem_metadata import measure, stamp, STAMP

DAY = 86400
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
ZONES = (('utc', 'UTC0', 0), ('east', 'NPT-5:45', 345))


def cases():
    for kind in long.KINDS:
        for form in ('l', 'n'):
            for age in ('old', 'recent', 'future'):
                for zone, tz, offset in ZONES:
                    yield case('ls', f'dates-{kind}-{form}-{age}-{zone}',
                               ['-d', '-' + form, 'meta/' + kind],
                               ticket='CSH-128', out='ls-dates', env={'TZ': tz},
                               ls_dates=dict(kind=kind, form=form, age=age,
                                             offset_minutes=offset))


def age_is_interior(age, seconds, now):
    # Deliberately far from both the current instant and any interpretation of
    # six calendar months. A changed clock cannot silently change the oracle.
    delta = now - seconds
    return (DAY < delta < 7 * DAY if age == 'recent' else
            delta > 365 * DAY if age == 'old' else delta < -365 * DAY)


def date_fields(spec, seconds):
    # Numeric calendar conversion plus literal English month names is independent
    # of provider/libc strftime, process locale, and the TZ spelling under test.
    value = datetime.fromtimestamp(seconds, timezone.utc) + timedelta(minutes=spec['offset_minutes'])
    final = f'{value.hour:02}:{value.minute:02}' if spec['age'] == 'recent' else str(value.year)
    return tuple(s.encode('ascii') for s in (MONTHS[value.month - 1], str(value.day), final))


def setup(directory, row):
    if 'ls_dates' not in row:
        return None
    spec = row['ls_dates']
    environment = long.setup(directory, dict(ls_long=spec))
    now = time.time()
    day = int(now // DAY) * DAY
    seconds = (STAMP // 10**9 if spec['age'] == 'old' else
               day + (-2 if spec['age'] == 'recent' else 400) * DAY + 23 * 3600 + 47 * 60 + 23)
    if not age_is_interior(spec['age'], seconds, now):
        raise OSError('ls date fixture is not safely inside its clock category')
    path = directory / 'meta' / spec['kind']
    stamp(path, STAMP, seconds * 10**9)
    root = directory / 'meta'
    # Update the hard-link alias as well as the operand after utime.
    environment['before'] = {name: measure(root / name) for name in environment['entries']}
    environment['ctimes'] = {name: (root / name).lstat().st_ctime_ns for name in environment['entries']}
    environment.update(seconds=seconds, clock_before=now,
                       date_fields=[s.decode('ascii') for s in date_fields(spec, seconds)],
                       probe='pre-exec exact utime/lstat readback, interior wall-clock category, fixed numeric zone offset')
    return environment


def output_matches(environment, output):
    return long.output_matches(environment, output,
                               date_fields(environment['spec'], environment['seconds']))


def verify(directory, environment):
    if environment is None:
        return [], None
    errors, after = long.verify(directory, environment)
    now = time.time()
    if not age_is_interior(environment['spec']['age'], environment['seconds'], now):
        errors.append('ls date clock category changed during execution')
    for name, before in environment['ctimes'].items():
        after[name]['ctime_ns'] = (directory / 'meta' / name).lstat().st_ctime_ns
        if after[name]['ctime_ns'] != before:
            errors.append('date listing ctime changed: ' + name)
    return errors, dict(measurements=after, clock_after=now)
