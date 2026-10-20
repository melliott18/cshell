"""CSH-096 bounded touch calendar and timestamp-selection witnesses.

Expected seconds come from integer Gregorian date subtraction, not touch,
strptime, mktime, a reference utility, or the process's local timezone.
"""
from datetime import datetime, timezone
from os import utime

from host_filesystem_cases import case

CONTENT = b'calendar witness\n'
BASELINE = (900000000125000000, 1000000000250000000)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Spellings and calendar interpretations are independently authored. In
# particular, the SS=60 input maps to the next minute, and YY=68 maps to 2068.
DATES = [
    ('epoch', '-t', '197001010000.00', (1970, 1, 1, 0, 0, 0)),
    ('year-70', '-t', '7001010000.01', (1970, 1, 1, 0, 0, 1)),
    ('year-99', '-t', '9912312359.59', (1999, 12, 31, 23, 59, 59)),
    ('year-00-default-seconds', '-t', '0001010000', (2000, 1, 1, 0, 0, 0)),
    ('leap-day', '-t', '200002292359.59', (2000, 2, 29, 23, 59, 59)),
    ('second-60-rollover', '-t', '199912312359.60', (2000, 1, 1, 0, 0, 0)),
    ('required-2038', '-d', '2038-01-01T00:00:00Z', (2038, 1, 1, 0, 0, 0)),
    ('after-signed32', '-d', '2038-01-19T03:14:08Z', (2038, 1, 19, 3, 14, 8)),
    ('year-68', '-t', '6812312359.59', (2068, 12, 31, 23, 59, 59)),
    ('leap-day-date', '-d', '2000-02-29T12:34:56Z', (2000, 2, 29, 12, 34, 56)),
]


def cases():
    for name, option, spelling, fields in DATES:
        delta = datetime(*fields, tzinfo=timezone.utc) - EPOCH
        target_ns = (delta.days * 86400 + delta.seconds) * 1000000000
        for selection, flags in [('both', []), ('access', ['-a']),
                                 ('modify', ['-m']), ('explicit-both', ['-a', '-m'])]:
            atime = BASELINE[0] if flags == ['-m'] else target_ns
            mtime = BASELINE[1] if flags == ['-a'] else target_ns
            yield case('touch', 'calendar-' + name + '-' + selection,
                       [*flags, option, spelling, 'target'], ticket='CSH-096',
                       files={'target': CONTENT}, env={'TZ': 'UTC0'},
                       effects={'target': dict(type='file', content=CONTENT,
                                               atime_ns=atime, mtime_ns=mtime)},
                       calendar_environment=dict(utc_fields=fields, target_ns=target_ns,
                                                 baseline_ns=BASELINE))


def setup(directory, row):
    spec = row.get('calendar_environment')
    if spec is None:
        return None
    target = directory / 'target'
    if target.read_bytes() != CONTENT:
        raise OSError('calendar fixture content readback mismatch')
    measured = []
    # Probe the exact inode to be passed to touch, then restore unequal,
    # fractional baselines so an omitted or unintended update is detectable.
    for stamps in [(spec['target_ns'], spec['target_ns']), BASELINE]:
        utime(target, ns=stamps)
        info = target.stat()
        actual = (info.st_atime_ns, info.st_mtime_ns)
        if actual != stamps:
            raise OSError('filesystem cannot represent authored calendar timestamps')
        measured.append(dict(requested_ns=stamps, observed_ns=actual,
                             device=info.st_dev, inode=info.st_ino))
    return dict(phase='armed', timezone='UTC0', utc_fields=spec['utc_fields'],
                target_ns=spec['target_ns'], baseline_ns=BASELINE, probes=measured,
                scope='private representable timestamps; no full range or failure qualification')
