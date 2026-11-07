"""CSH-098 touch date syntax, fractional seconds and fixed timezone witnesses.

UTC calendar fields and fractions are authored independently of input spellings.
No provider, date parser, local timezone database or floating point is an oracle.
"""
from datetime import datetime, timezone
from os import utime

from host_filesystem_cases import case

CONTENT = b'date syntax witness\n'
BASELINE = (900000000125000000, 1000000000250000000)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
SELECTIONS = [('both', []), ('access', ['-a']), ('modify', ['-m']),
              ('explicit-both', ['-a', '-m'])]

# Fixed POSIX TZ strings have no DST transitions or external zoneinfo dependency.
# A positive TZ offset means west of UTC. Z must override even a nonzero TZ.
DATES = [
    ('dot-tenth', '-d', '2000-01-01T00:00:00.1Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 100000000),
    ('comma-tenth', '-d', '2000-01-01T00:00:00,1Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 100000000),
    ('dot-nanosecond', '-d', '2000-01-01T00:00:00.000000001Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 1),
    ('comma-last-nanosecond', '-d', '2000-01-01T00:00:00,999999999Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 999999999),
    ('space-dot', '-d', '2000-01-01 00:00:00.123456789Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 123456789),
    ('space-comma', '-d', '2000-01-01 00:00:00,000001000Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 1000),
    ('space-whole', '-d', '2000-01-01 00:00:00Z', 'UTC0', (2000, 1, 1, 0, 0, 0), 0),
    ('local-utc', '-d', '2000-01-01T00:00:00.25', 'UTC0', (2000, 1, 1, 0, 0, 0), 250000000),
    ('west-year-rollover', '-d', '1999-12-31T23:30:00.5', 'FST5', (2000, 1, 1, 4, 30, 0), 500000000),
    ('east-leap-rollover', '-d', '2000-03-01 00:15:00,125', 'FST-5:30', (2000, 2, 29, 18, 45, 0), 125000000),
    ('west-half-hour', '-d', '2000-01-01 00:00:00', 'FST3:30', (2000, 1, 1, 3, 30, 0), 0),
    ('east-quarter-hour', '-d', '2000-01-01T00:00:00', 'FST-5:45', (1999, 12, 31, 18, 15, 0), 0),
    ('z-overrides-west', '-d', '2000-01-01T00:00:00.125Z', 'FST5', (2000, 1, 1, 0, 0, 0), 125000000),
    ('z-overrides-east', '-d', '2000-01-01 00:00:00,5Z', 'FST-5:30', (2000, 1, 1, 0, 0, 0), 500000000),
    ('compact-west', '-t', '199912312330.00', 'FST5', (2000, 1, 1, 4, 30, 0), 0),
    ('compact-east', '-t', '200003010015.00', 'FST-5:30', (2000, 2, 29, 18, 45, 0), 0),
]


def cases():
    for name, option, spelling, zone, fields, fraction in DATES:
        delta = datetime(*fields, tzinfo=timezone.utc) - EPOCH
        target_ns = (delta.days * 86400 + delta.seconds) * 1000000000 + fraction
        for selection, flags in SELECTIONS:
            stamps = (BASELINE[0] if flags == ['-m'] else target_ns,
                      BASELINE[1] if flags == ['-a'] else target_ns)
            yield case('touch', 'datetime-' + name + '-' + selection,
                       [*flags, option, spelling, 'target'], ticket='CSH-098',
                       files={'target': CONTENT}, env={'TZ': zone},
                       effects={'target': dict(type='file', content=CONTENT,
                                               atime_ns=stamps[0], mtime_ns=stamps[1])},
                       datetime_environment=dict(utc_fields=fields, fraction_ns=fraction,
                                                 target_ns=target_ns, baseline_ns=BASELINE))


def identity(target):
    info = target.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode, nlink=info.st_nlink)


def setup(directory, row):
    spec = row.get('datetime_environment')
    if spec is None:
        return None
    target = directory / 'target'
    if target.read_bytes() != CONTENT:
        raise OSError('datetime fixture content readback mismatch')
    before = identity(target)
    measured = []
    for stamps in [(spec['target_ns'], spec['target_ns']), BASELINE]:
        utime(target, ns=stamps)
        info = target.stat()
        actual = (info.st_atime_ns, info.st_mtime_ns)
        if actual != stamps or identity(target) != before:
            raise OSError('filesystem cannot represent authored datetime timestamps on the target inode')
        measured.append(dict(requested_ns=stamps, observed_ns=actual,
                             device=info.st_dev, inode=info.st_ino))
    return dict(phase='armed', timezone=row['env']['TZ'],
                **dict(spec, scope=spec.get('scope',
                    'private exact timestamps and fixed TZ; no DST, range or failure qualification')),
                probes=measured, before=before)


def verify(directory, environment):
    if environment is None:
        return [], None
    observed = identity(directory / 'target')
    return ([] if observed == environment['before'] else ['datetime target identity/mode changed']), observed
