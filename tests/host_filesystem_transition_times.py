"""CSH-101: explicit transition clocks and sub-hour daylight offsets.

Local inputs and UTC fields are authored separately from XBD chapter 8's TZ
arithmetic. No provider, local conversion, or timezone database is an oracle.
All samples are unique local times; no ambiguous-time policy is assumed.
"""
from datetime import datetime, timezone

from host_filesystem_cases import case
from host_filesystem_datetime import BASELINE, CONTENT, EPOCH, SELECTIONS

WEST = 'WST3:30:15WDT2:45:05,M3.2.0/1:15:20,M11.1.0/3:40:50'
EAST = 'EST-5:45:30EDT-6:15:45,J60/0:10:15,J300/23:50:40'
ROLLOVER = 'NST0NDT-0:30,59/-1:30,299/26:15'
SCOPE = ('private exact timestamps and authored M/J/n transition clocks, minute/second '
         'offsets and signed/next-day transitions; unique local times only; no '
         'arbitrary rule, skipped/repeated time, timezone database, range or failure qualification')

# WEST advances 45m10s; EAST advances 30m15s. Before fallback, sample one
# second before the repeated interval starts, not one second before the change.
# In leap year 2024 day 59/-1:30 is Feb 28 22:30; day 299/26:15 is Oct 27 02:15.
DATES = [
    ('west-start-before', WEST, '2024-03-10T01:15:19', '202403100115.19', (2024, 3, 10, 4, 45, 34)),
    ('west-start-after', WEST, '2024-03-10T02:00:30', '202403100200.30', (2024, 3, 10, 4, 45, 35)),
    ('west-end-before', WEST, '2024-11-03T02:55:39', '202411030255.39', (2024, 11, 3, 5, 40, 44)),
    ('west-end-after', WEST, '2024-11-03T03:40:50', '202411030340.50', (2024, 11, 3, 7, 11, 5)),
    ('east-start-before', EAST, '2024-03-01T00:10:14', '202403010010.14', (2024, 2, 29, 18, 24, 44)),
    ('east-start-after', EAST, '2024-03-01T00:40:30', '202403010040.30', (2024, 2, 29, 18, 24, 45)),
    ('east-end-before', EAST, '2024-10-27T23:20:24', '202410272320.24', (2024, 10, 27, 17, 4, 39)),
    ('east-end-after', EAST, '2024-10-27T23:50:40', '202410272350.40', (2024, 10, 27, 18, 5, 10)),
    ('previous-day-start-before', ROLLOVER, '2024-02-28T22:29:59', '202402282229.59', (2024, 2, 28, 22, 29, 59)),
    ('previous-day-start-after', ROLLOVER, '2024-02-28T23:00:00', '202402282300.00', (2024, 2, 28, 22, 30, 0)),
    ('next-day-end-before', ROLLOVER, '2024-10-27T01:44:59', '202410270144.59', (2024, 10, 27, 1, 14, 59)),
    ('next-day-end-after', ROLLOVER, '2024-10-27T02:15:00', '202410270215.00', (2024, 10, 27, 2, 15, 0)),
]


def cases():
    for name, zone, extended, compact, fields in DATES:
        delta = datetime(*fields, tzinfo=timezone.utc) - EPOCH
        target_ns = (delta.days * 86400 + delta.seconds) * 1000000000
        for suffix, option, spelling in [('d', '-d', extended), ('t', '-t', compact)]:
            for selection, flags in SELECTIONS:
                stamps = (BASELINE[0] if flags == ['-m'] else target_ns,
                          BASELINE[1] if flags == ['-a'] else target_ns)
                yield case('touch', 'transition-times-' + name + '-' + suffix + '-' + selection,
                           [*flags, option, spelling, 'target'], ticket='CSH-101',
                           files={'target': CONTENT}, env={'TZ': zone},
                           effects={'target': dict(type='file', content=CONTENT,
                                                   atime_ns=stamps[0], mtime_ns=stamps[1])},
                           datetime_environment=dict(utc_fields=fields, fraction_ns=0,
                                                     target_ns=target_ns, baseline_ns=BASELINE,
                                                     scope=SCOPE))
