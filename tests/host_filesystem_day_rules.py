"""CSH-100: POSIX Julian and zero-based daylight-saving day rules.

The input spellings and UTC fields are authored independently; no local time
conversion or provider result supplies the oracle. Only unique times are used.
"""
from datetime import datetime, timezone

from host_filesystem_cases import case
from host_filesystem_datetime import BASELINE, CONTENT, EPOCH, SELECTIONS

JULIAN = 'JST0JDT,J60,J300'
NUMBERED = 'NST0NDT,59,299'
SCOPE = ('private exact timestamps and explicit POSIX J/n rules with default 02:00 '
         'transitions; unique local times only; no timezone database, skipped/repeated '
         'time, arbitrary rule, range or failure qualification')

# J60 is March 1 in every year; day 59 is February 29 in a leap year.
# J300 is October 27 in every year; day 299 is October 26 in a leap year.
# The omitted transition time is 02:00; daylight offset defaults to -01:00.
# Before fallback use 00:59:59, preceding the repeated 01:00 hour.
DATES = [
    ('julian-common-start-before', JULIAN, '2023-03-01T01:59:59', '202303010159.59', (2023, 3, 1, 1, 59, 59)),
    ('julian-common-start-after', JULIAN, '2023-03-01T03:00:00', '202303010300.00', (2023, 3, 1, 2, 0, 0)),
    ('julian-leap-day', JULIAN, '2024-02-29T12:00:00', '202402291200.00', (2024, 2, 29, 12, 0, 0)),
    ('julian-leap-start-before', JULIAN, '2024-03-01T01:59:59', '202403010159.59', (2024, 3, 1, 1, 59, 59)),
    ('julian-leap-start-after', JULIAN, '2024-03-01T03:00:00', '202403010300.00', (2024, 3, 1, 2, 0, 0)),
    ('numbered-common-start-before', NUMBERED, '2023-03-01T01:59:59', '202303010159.59', (2023, 3, 1, 1, 59, 59)),
    ('numbered-common-start-after', NUMBERED, '2023-03-01T03:00:00', '202303010300.00', (2023, 3, 1, 2, 0, 0)),
    ('numbered-leap-start-before', NUMBERED, '2024-02-29T01:59:59', '202402290159.59', (2024, 2, 29, 1, 59, 59)),
    ('numbered-leap-start-after', NUMBERED, '2024-02-29T03:00:00', '202402290300.00', (2024, 2, 29, 2, 0, 0)),
    ('numbered-march-day', NUMBERED, '2024-03-01T12:00:00', '202403011200.00', (2024, 3, 1, 11, 0, 0)),
    ('julian-leap-end-before', JULIAN, '2024-10-27T00:59:59', '202410270059.59', (2024, 10, 26, 23, 59, 59)),
    ('julian-leap-end-after', JULIAN, '2024-10-27T02:00:00', '202410270200.00', (2024, 10, 27, 2, 0, 0)),
    ('numbered-leap-end-before', NUMBERED, '2024-10-26T00:59:59', '202410260059.59', (2024, 10, 25, 23, 59, 59)),
    ('numbered-leap-end-after', NUMBERED, '2024-10-26T02:00:00', '202410260200.00', (2024, 10, 26, 2, 0, 0)),
    ('julian-common-end-after', JULIAN, '2023-10-27T02:00:00', '202310270200.00', (2023, 10, 27, 2, 0, 0)),
    ('numbered-common-end-after', NUMBERED, '2023-10-27T02:00:00', '202310270200.00', (2023, 10, 27, 2, 0, 0)),
]


def cases():
    for name, zone, extended, compact, fields in DATES:
        delta = datetime(*fields, tzinfo=timezone.utc) - EPOCH
        target_ns = (delta.days * 86400 + delta.seconds) * 1000000000
        for suffix, option, spelling in [('d', '-d', extended), ('t', '-t', compact)]:
            for selection, flags in SELECTIONS:
                stamps = (BASELINE[0] if flags == ['-m'] else target_ns,
                          BASELINE[1] if flags == ['-a'] else target_ns)
                yield case('touch', 'day-rules-' + name + suffix + '-' + selection,
                           [*flags, option, spelling, 'target'], ticket='CSH-100',
                           files={'target': CONTENT}, env={'TZ': zone},
                           effects={'target': dict(type='file', content=CONTENT,
                                                   atime_ns=stamps[0], mtime_ns=stamps[1])},
                           datetime_environment=dict(utc_fields=fields, fraction_ns=0,
                                                     target_ns=target_ns, baseline_ns=BASELINE,
                                                     scope=SCOPE))
