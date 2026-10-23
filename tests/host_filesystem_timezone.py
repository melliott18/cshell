"""CSH-099 touch witnesses for explicit POSIX daylight-saving rules.

Local spellings and expected UTC fields are independently authored. Only unique
local times are used: skipped and repeated wall times have no oracle here.
No timezone database, mktime, provider output or current clock supplies answers.
"""
from datetime import datetime, timezone

from host_filesystem_cases import case
from host_filesystem_datetime import BASELINE, CONTENT, EPOCH, SELECTIONS

NORTH = 'NST5NDT,M3.2.0/2,M11.1.0/2'
SOUTH = 'SST-10SDT-11,M10.1.0/2,M4.1.0/3'
SCOPE = ('private exact timestamps and explicit POSIX M rules; unique local times only; '
         'no timezone database, skipped/repeated time, range or failure qualification')

# In 2024 the authored Sundays are March 10, November 3, October 6 and April 7.
# Before fallback, stop before the *repeated* hour begins. After fallback, use
# the first unique standard-time instant; do not assume an ambiguous-time policy.
DATES = [
    ('north-winter', NORTH, '2024-01-15T12:00:00', '202401151200.00', (2024, 1, 15, 17, 0, 0)),
    ('north-summer', NORTH, '2024-07-15T12:00:00', '202407151200.00', (2024, 7, 15, 16, 0, 0)),
    ('north-start-before', NORTH, '2024-03-10T01:59:59', '202403100159.59', (2024, 3, 10, 6, 59, 59)),
    ('north-start-after', NORTH, '2024-03-10T03:00:00', '202403100300.00', (2024, 3, 10, 7, 0, 0)),
    ('north-end-before', NORTH, '2024-11-03T00:59:59', '202411030059.59', (2024, 11, 3, 4, 59, 59)),
    ('north-end-after', NORTH, '2024-11-03T02:00:00', '202411030200.00', (2024, 11, 3, 7, 0, 0)),
    ('south-january', SOUTH, '2024-01-15T12:00:00', '202401151200.00', (2024, 1, 15, 1, 0, 0)),
    ('south-july', SOUTH, '2024-07-15T12:00:00', '202407151200.00', (2024, 7, 15, 2, 0, 0)),
    ('south-start-before', SOUTH, '2024-10-06T01:59:59', '202410060159.59', (2024, 10, 5, 15, 59, 59)),
    ('south-start-after', SOUTH, '2024-10-06T03:00:00', '202410060300.00', (2024, 10, 5, 16, 0, 0)),
    ('south-end-before', SOUTH, '2024-04-07T01:59:59', '202404070159.59', (2024, 4, 6, 14, 59, 59)),
    ('south-end-after', SOUTH, '2024-04-07T03:00:00', '202404070300.00', (2024, 4, 6, 17, 0, 0)),
]


def cases():
    spellings = [(name + suffix, zone, option, spelling, fields)
                 for name, zone, extended, compact, fields in DATES
                 for suffix, option, spelling in [('d', '-d', extended), ('t', '-t', compact)]]
    # These dates lie inside each zone's daylight season. Z must still mean UTC.
    spellings += [
        ('north-z', NORTH, '-d', '2024-07-15T12:00:00Z', (2024, 7, 15, 12, 0, 0)),
        ('south-z', SOUTH, '-d', '2024-01-15T12:00:00Z', (2024, 1, 15, 12, 0, 0)),
    ]
    for name, zone, option, spelling, fields in spellings:
        delta = datetime(*fields, tzinfo=timezone.utc) - EPOCH
        target_ns = (delta.days * 86400 + delta.seconds) * 1000000000
        for selection, flags in SELECTIONS:
            stamps = (BASELINE[0] if flags == ['-m'] else target_ns,
                      BASELINE[1] if flags == ['-a'] else target_ns)
            yield case('touch', 'timezone-' + name + '-' + selection,
                       [*flags, option, spelling, 'target'], ticket='CSH-099',
                       files={'target': CONTENT}, env={'TZ': zone},
                       effects={'target': dict(type='file', content=CONTENT,
                                               atime_ns=stamps[0], mtime_ns=stamps[1])},
                       datetime_environment=dict(utc_fields=fields, fraction_ns=0,
                                                 target_ns=target_ns, baseline_ns=BASELINE,
                                                 scope=SCOPE))
