"""CSH-072 harness failure and oracle regressions, not provider conformance."""
import copy
from contextlib import nullcontext
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import pty_harness

from host_filesystem_extended import cases as extended_cases
from host_filesystem_remaining import cases as remaining_cases
from host_filesystem_residual_cases import cases as residual_cases
import host_filesystem_isolated as isolated
import host_filesystem_interactive as interactive
import host_filesystem_decisions as decisions
import host_filesystem_metadata as metadata
import host_filesystem_recursive as recursive
import host_filesystem_path_limits as path_limits
import host_filesystem_cwd as cwd_cases
import host_filesystem_creation as creation
import host_filesystem_output as output_cases
import host_filesystem_magic as magic_cases
import host_filesystem_magic_strings as magic_strings
import host_filesystem_calendar as calendar_cases
import host_filesystem_reference as reference_cases
import host_filesystem_datetime as datetime_cases
import host_filesystem_timezone as timezone_cases
import host_filesystem_day_rules as day_rules
import host_filesystem_transition_times as transition_times
from host_contract_inventory import utility_owner
from host_filesystem import run_case, stdout_matches, stderr_matches
from host_filesystem_cases import UTILITIES, DATA, case, cases, audit_cases, terminal_cases, effect_errors


class FilesystemHarnessTests(unittest.TestCase):
    def test_transition_times_have_exact_offsets_and_unique_boundaries(self):
        rows = list(transition_times.cases())
        seconds = [1710045934, 1710045935, 1730612444, 1730617865,
                   1709231084, 1709231085, 1730048679, 1730052310,
                   1709159399, 1709159400, 1729991699, 1729995300]
        self.assertEqual(len(rows), 96)
        self.assertEqual(len({r['id'] for r in rows}), 96)
        expected = [s * 10**9 for s in seconds for _ in range(2)]
        self.assertEqual([r['datetime_environment']['target_ns'] for r in rows[::4]], expected)
        self.assertEqual({r['env']['TZ'] for r in rows},
                         {transition_times.WEST, transition_times.EAST, transition_times.ROLLOVER})
        self.assertEqual(sum('-t' in r['args'] for r in rows), 48)
        for offset, advance in zip(range(0, 12, 4), (2710, 1815, 1800)):
            self.assertEqual(seconds[offset+1] - seconds[offset], 1)
            self.assertEqual(seconds[offset+3] - seconds[offset+2], 2*advance + 1)
        for offset, value in enumerate(expected):
            for row, stamps in zip(rows[offset*4:offset*4+4],
                                   [(value, value), (value, 1000000000250000000),
                                    (900000000125000000, value), (value, value)]):
                effect = row['effects']['target']
                self.assertEqual((effect['atime_ns'], effect['mtime_ns']), stamps)

    def test_transition_times_channels_fields_and_contents_are_required(self):
        self.check_datetime_channels(list(transition_times.cases())[:4])

    def test_transition_times_unrepresentable_or_failed_setup_never_executes(self):
        self.check_datetime_setup(next(transition_times.cases()))

    def test_transition_times_exec_failure_and_timeout_clean_all_modes(self):
        self.check_datetime_cleanup(next(transition_times.cases()))

    def test_day_rules_expected_values_distinguish_leap_day_counting(self):
        rows = list(day_rules.cases())
        seconds = [1677635999, 1677636000, 1709208000, 1709258399,
                   1709258400, 1677635999, 1677636000, 1709171999,
                   1709172000, 1709290800, 1729987199, 1729994400,
                   1729900799, 1729908000, 1698372000, 1698372000]
        self.assertEqual(len(rows), 128)
        self.assertEqual(len({r['id'] for r in rows}), 128)
        expected = [s * 10**9 for s in seconds for _ in range(2)]
        self.assertEqual([r['datetime_environment']['target_ns'] for r in rows[::4]], expected)
        self.assertEqual({r['env']['TZ'] for r in rows}, {day_rules.JULIAN, day_rules.NUMBERED})
        self.assertEqual(sum('-t' in r['args'] for r in rows), 64)
        for offset, value in enumerate(expected):
            for row, stamps in zip(rows[offset*4:offset*4+4],
                                   [(value, value), (value, 1000000000250000000),
                                    (900000000125000000, value), (value, value)]):
                effect = row['effects']['target']
                self.assertEqual((effect['atime_ns'], effect['mtime_ns']), stamps)

    def test_day_rules_channels_fields_and_contents_are_required(self):
        self.check_datetime_channels(list(day_rules.cases())[:4])

    def test_day_rules_unrepresentable_or_failed_setup_never_executes(self):
        self.check_datetime_setup(next(day_rules.cases()))

    def test_day_rules_exec_failure_and_timeout_clean_all_modes(self):
        self.check_datetime_cleanup(next(day_rules.cases()))

    def test_timezone_expected_values_are_independent_of_local_conversion(self):
        rows = list(timezone_cases.cases())
        # Literal Epoch seconds, independently checked against UTC dates. This
        # catches daylight offset signs, southern year wrap and transition dates.
        seconds = [1705338000, 1721059200, 1710053999, 1710054000,
                   1730609999, 1730617200, 1705280400, 1721008800,
                   1728143999, 1728144000, 1712415599, 1712422800]
        expected = [s * 1000000000 for s in seconds for _ in range(2)]
        expected += [1721044800000000000, 1705320000000000000]
        self.assertEqual(len(rows), 104)
        self.assertEqual([r['datetime_environment']['target_ns'] for r in rows[::4]], expected)
        for offset, value in enumerate(expected):
            for row, stamps in zip(rows[offset*4:offset*4+4],
                                   [(value, value), (value, 1000000000250000000),
                                    (900000000125000000, value), (value, value)]):
                effect = row['effects']['target']
                self.assertEqual((effect['atime_ns'], effect['mtime_ns']), stamps)
        self.assertEqual({r['env']['TZ'] for r in rows}, {timezone_cases.NORTH, timezone_cases.SOUTH})
        self.assertEqual(sum('-t' in r['args'] for r in rows), 48)

    def test_reference_oracle_distinguishes_fields_and_aliases(self):
        rows = list(reference_cases.cases())
        self.assertEqual(len(rows), 28)
        expected = {'both': (1000000000125000000, 1100000000250000000),
                    'access': (1000000000125000000, 950000000500000000),
                    'modify': (900000000375000000, 1100000000250000000),
                    'explicit-both': (1000000000125000000, 1100000000250000000)}
        for row in rows:
            selection = next(n for n, flags in reference_cases.SELECTIONS
                             if row['args'][:len(flags)] == flags and
                             (row['args'][len(flags)] in ('-r', '-c')))
            self.assertEqual(row['reference_environment']['target_ns'], expected[selection])
        self.assertEqual(sum(r['reference_environment']['no_create'] for r in rows), 4)
        self.assertEqual({r['reference_environment']['reference'] for r in rows},
                         {'reference', 'reference-link', 'reference-chain'})

    def test_reference_oracle_rejects_wrong_fields_graphs_channels_and_contents(self):
        # Include all selections and the no-create branch. Metadata must be
        # captured before a content read through either hard-linked name.
        for row in list(reference_cases.cases())[-4:]:
            original = copy.deepcopy(row)
            for fault in (None, 'atime', 'mtime', 'reference-time', 'reference-content',
                          'target-content', 'inode', 'link', 'created', 'stdout', 'stderr', 'status'):
                def capture(binary, invocation, cwd, *args, **kw):
                    stamps = row['reference_environment']['target_ns']
                    if fault == 'inode':
                        (cwd / 'target').unlink()
                        (cwd / 'target').write_bytes(reference_cases.FILES['target'])
                    if fault in ('reference-content', 'target-content'):
                        (cwd / fault.split('-')[0]).write_bytes(b'changed')
                    os.utime(cwd / 'target', ns=(stamps[0] + (fault == 'atime'),
                                                stamps[1] + (fault == 'mtime')))
                    ref = reference_cases.REFERENCE
                    os.utime(cwd / 'reference', ns=(ref[0], ref[1] + (fault == 'reference-time')))
                    if fault == 'link':
                        (cwd / 'target-chain').unlink()
                        (cwd / 'target-chain').symlink_to('reference')
                    if fault == 'created':
                        (cwd / 'missing-target').touch()
                    return (1 if fault == 'status' else 0,
                            dict(stdout=b'wrong' if fault == 'stdout' else b'',
                                 stderr=b'wrong' if fault == 'stderr' else b''), [])
                with self.subTest(case=row['id'], fault=fault), tempfile.TemporaryDirectory() as root, \
                        patch('host_filesystem.smoke.capture', side_effect=capture):
                    record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                      os.defpath, row, 'direct', Path(root), None)
                    self.assertEqual(record['verdict'], 'PASS' if fault is None else 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertEqual(row, original)

    def test_reference_setup_failure_prevents_exec_and_cleans(self):
        row = next(reference_cases.cases())
        real_utime = os.utime
        for fault in ('link', 'timestamp', 'rounded', 'baseline'):
            def utime(path, ns):
                if fault == 'timestamp' or (fault == 'baseline' and ns == reference_cases.BASELINE):
                    raise OSError(errno.EIO, 'synthetic timestamp setup failure')
                real_utime(path, ns=(ns[0] + (fault == 'rounded'), ns[1]))
            control = patch('host_filesystem_reference.os.link', side_effect=OSError(errno.EPERM, 'link')) \
                if fault == 'link' else patch('host_filesystem_reference.utime', side_effect=utime)
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, control, \
                    patch('host_filesystem.smoke.capture') as capture:
                record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                  os.defpath, row, 'direct', Path(root), None)
                capture.assert_not_called()
                self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_reference_exec_failure_and_timeout_clean_all_modes(self):
        row = next(reference_cases.cases())
        for mode in ('direct', 'string', 'file', 'stdin'):
            for fault in ('exec', 'timeout'):
                with self.subTest(mode=mode, fault=fault), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider, pidfile = root / 'touch', root / 'pid'
                    provider.write_text('#!/nonexistent-csh097-interpreter\n' if fault == 'exec' else
                                        '#!/bin/sh\necho $$ > "' + str(pidfile) + '"\nexec /bin/sleep 60\n')
                    provider.chmod(0o700)
                    record = run_case(Path('/bin/sh'), {'touch': {'path': str(provider)}},
                                      str(root), row, mode, root, None, timeout=1)
                    self.assertEqual(record['verdict'], 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertFalse(list(root.glob('csh-filesystem-*')))
                    if fault == 'timeout':
                        self.assertTrue(any('timeout' in e for e in record['errors']), record)
                        pid = int(pidfile.read_text())
                        deadline = time.monotonic() + 2
                        while True:
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            if time.monotonic() >= deadline:
                                self.fail('reference timeout child survived cleanup')
                            time.sleep(0.01)

    def test_calendar_oracle_has_independent_epoch_and_century_boundaries(self):
        rows = {r['id']: r for r in calendar_cases.cases()}
        self.assertEqual(len(rows), 40)
        for name, seconds in [('epoch', 0), ('year-70', 1), ('year-99', 946684799),
                              ('year-00-default-seconds', 946684800),
                              ('second-60-rollover', 946684800),
                              ('leap-day', 951868799), ('after-signed32', 2147483648),
                              ('year-68', 3124223999)]:
            row = rows['touch/calendar-' + name + '-both']
            self.assertEqual(row['calendar_environment']['target_ns'], seconds * 10**9)
        for row in rows.values():
            self.assertEqual(row['env'], {'TZ': 'UTC0'})
            self.assertNotEqual(row['calendar_environment']['target_ns'], calendar_cases.BASELINE[0])
            self.assertNotEqual(row['calendar_environment']['target_ns'], calendar_cases.BASELINE[1])

    def test_datetime_expected_values_do_not_parse_provider_inputs(self):
        rows = list(datetime_cases.cases())
        self.assertEqual(len(rows), 64)
        # Independent epoch constants catch sign, rollover and fraction scaling errors.
        expected = [946684800100000000, 946684800100000000, 946684800000000001,
                    946684800999999999, 946684800123456789, 946684800000001000,
                    946684800000000000, 946684800250000000, 946701000500000000,
                    951849900125000000, 946697400000000000, 946664100000000000,
                    946684800125000000, 946684800500000000, 946701000000000000,
                    951849900000000000]
        self.assertEqual([r['datetime_environment']['target_ns'] for r in rows[::4]], expected)
        for group, value in zip((rows[n:n+4] for n in range(0, 64, 4)), expected):
            for row, stamps in zip(group, [(value, value), (value, 1000000000250000000),
                                          (900000000125000000, value), (value, value)]):
                effect = row['effects']['target']
                self.assertEqual((effect['atime_ns'], effect['mtime_ns']), stamps)
        self.assertEqual({r['env']['TZ'] for r in rows},
                         {'UTC0', 'FST5', 'FST-5:30', 'FST3:30', 'FST-5:45'})

    def test_datetime_channels_fields_and_contents_are_required(self):
        self.check_datetime_channels(list(datetime_cases.cases())[:4])

    def test_timezone_channels_fields_and_contents_are_required(self):
        self.check_datetime_channels(list(timezone_cases.cases())[24:28])

    def check_datetime_channels(self, rows):
        for row in rows:
            original = copy.deepcopy(row)
            for fault in (None, 'atime', 'mtime', 'content', 'mode', 'inode', 'stdout', 'stderr', 'status'):
                def capture(binary, invocation, cwd, *args, **kw):
                    expected = row['effects']['target']
                    if fault == 'content':
                        (cwd / 'target').write_bytes(b'changed')
                    if fault == 'mode':
                        (cwd / 'target').chmod(0o700)
                    if fault == 'inode':
                        (cwd / 'target').rename(cwd / 'original')
                        (cwd / 'target').write_bytes(datetime_cases.CONTENT)
                    stamps = (expected['atime_ns'] + (fault == 'atime'),
                              expected['mtime_ns'] + (fault == 'mtime'))
                    os.utime(cwd / 'target', ns=stamps)
                    return (1 if fault == 'status' else 0,
                            dict(stdout=b'wrong' if fault == 'stdout' else b'',
                                 stderr=b'wrong' if fault == 'stderr' else b''), [])
                with self.subTest(case=row['id'], fault=fault), tempfile.TemporaryDirectory() as root, \
                        patch('host_filesystem.smoke.capture', side_effect=capture):
                    record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                      os.defpath, row, 'direct', Path(root), None)
                    self.assertEqual(record['verdict'], 'PASS' if fault is None else 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertEqual(list(Path(root).iterdir()), [])
            self.assertEqual(row, original)

    def test_datetime_unrepresentable_or_failed_setup_never_executes(self):
        self.check_datetime_setup(next(datetime_cases.cases()))

    def test_timezone_unrepresentable_or_failed_setup_never_executes(self):
        self.check_datetime_setup(next(timezone_cases.cases()))

    def check_datetime_setup(self, row):
        real_utime = os.utime
        for failure in ('error', 'rounded', 'baseline'):
            def utime(path, *, ns):
                if failure == 'error' or (failure == 'baseline' and ns == datetime_cases.BASELINE):
                    raise OSError(errno.EIO, 'synthetic timestamp setup error')
                actual = (ns[0] + 1000000000, ns[1]) if failure == 'rounded' else ns
                real_utime(path, ns=actual)
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem_datetime.utime', side_effect=utime), \
                    patch('host_filesystem.smoke.capture') as capture:
                record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                  os.defpath, row, 'direct', Path(root), None)
                capture.assert_not_called()
                self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_datetime_exec_failure_and_timeout_clean_all_modes(self):
        self.check_datetime_cleanup(next(datetime_cases.cases()))

    def test_timezone_exec_failure_and_timeout_clean_all_modes(self):
        self.check_datetime_cleanup(next(timezone_cases.cases()))

    def check_datetime_cleanup(self, row):
        for mode in ('direct', 'string', 'file', 'stdin'):
            for fault in ('exec', 'timeout'):
                with self.subTest(mode=mode, fault=fault), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider, pidfile = root / 'touch', root / 'pid'
                    provider.write_text('#!/nonexistent-csh098-interpreter\n' if fault == 'exec' else
                                        '#!/bin/sh\necho $$ > "' + str(pidfile) + '"\nexec /bin/sleep 60\n')
                    provider.chmod(0o700)
                    record = run_case(Path('/bin/sh'), {'touch': {'path': str(provider)}},
                                      str(root), row, mode, root, None, timeout=1)
                    self.assertEqual(record['verdict'], 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertFalse(list(root.glob('csh-filesystem-*')))
                    if fault == 'timeout':
                        self.assertTrue(any('timeout' in e for e in record['errors']), record)
                        pid = int(pidfile.read_text())
                        deadline = time.monotonic() + 2
                        while True:
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            if time.monotonic() >= deadline:
                                self.fail('datetime timeout child survived cleanup')
                            time.sleep(0.01)

    def test_calendar_channels_fields_and_contents_are_required(self):
        rows = list(calendar_cases.cases())[:4]
        for row in rows:
            original = copy.deepcopy(row)
            for fault in (None, 'atime', 'mtime', 'content', 'stdout', 'stderr', 'status'):
                def capture(binary, invocation, cwd, *args, **kw):
                    expected = row['effects']['target']
                    if fault == 'content':
                        (cwd / 'target').write_bytes(b'changed')
                    stamps = (expected['atime_ns'] + (fault == 'atime'),
                              expected['mtime_ns'] + (fault == 'mtime'))
                    os.utime(cwd / 'target', ns=stamps)
                    return (1 if fault == 'status' else 0,
                            dict(stdout=b'wrong' if fault == 'stdout' else b'',
                                 stderr=b'wrong' if fault == 'stderr' else b''), [])
                with self.subTest(case=row['id'], fault=fault), tempfile.TemporaryDirectory() as root, \
                        patch('host_filesystem.smoke.capture', side_effect=capture):
                    record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                      os.defpath, row, 'direct', Path(root), None)
                    self.assertEqual(record['verdict'], 'PASS' if fault is None else 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertEqual(list(Path(root).iterdir()), [])
            self.assertEqual(row, original)

    def test_calendar_unrepresentable_or_failed_setup_never_executes(self):
        row = next(calendar_cases.cases())
        real_utime = os.utime
        for failure in ('error', 'rounded', 'baseline'):
            def utime(path, *, ns):
                if failure == 'error' or (failure == 'baseline' and ns == calendar_cases.BASELINE):
                    raise OSError(errno.EIO, 'synthetic timestamp setup error')
                actual = (ns[0] + 1000000000, ns[1]) if failure == 'rounded' else ns
                real_utime(path, ns=actual)
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem_calendar.utime', side_effect=utime), \
                    patch('host_filesystem.smoke.capture') as capture:
                record = run_case(Path('/bin/sh'), {'touch': {'path': '/usr/bin/touch'}},
                                  os.defpath, row, 'direct', Path(root), None)
                capture.assert_not_called()
                self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_calendar_exec_failure_and_timeout_clean_all_modes(self):
        row = next(calendar_cases.cases())
        for mode in ('direct', 'string', 'file', 'stdin'):
            for fault in ('exec', 'timeout'):
                with self.subTest(mode=mode, fault=fault), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider, pidfile = root / 'touch', root / 'pid'
                    provider.write_text('#!/nonexistent-csh096-interpreter\n' if fault == 'exec' else
                                        '#!/bin/sh\necho $$ > "' + str(pidfile) + '"\nexec /bin/sleep 60\n')
                    provider.chmod(0o700)
                    record = run_case(Path('/bin/sh'), {'touch': {'path': str(provider)}},
                                      str(root), row, mode, root, None, timeout=1)
                    self.assertEqual(record['verdict'], 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    self.assertFalse(list(root.glob('csh-filesystem-*')))
                    if fault == 'timeout':
                        self.assertTrue(any('timeout' in e for e in record['errors']), record)
                        pid = int(pidfile.read_text())
                        deadline = time.monotonic() + 2
                        while True:
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            if time.monotonic() >= deadline:
                                self.fail('calendar timeout child survived cleanup')
                            time.sleep(0.01)

    def test_magic_strings_authored_bytes_offsets_and_eof(self):
        rows = list(magic_strings.cases())
        self.assertEqual(len(rows), 91)
        self.assertEqual(len({r['id'] for r in rows}), 91)
        exact = {r['id'].removeprefix('file/magic-strings-').removesuffix('-exact'):
                 r['files']['sample'][16:] for r in rows if r['id'].endswith('-exact')}
        for name, byte in [('alert', 7), ('backspace', 8), ('formfeed', 12),
                           ('newline', 10), ('return', 13), ('tab', 9),
                           ('vertical-tab', 11), ('octal-nul', 0), ('octal-high', 255)]:
            self.assertEqual(exact[name], b'A' + bytes([byte]) + b'B')
        self.assertEqual(exact['octal-three'], b'AA2')
        self.assertEqual(exact['octal-one'], b'A\x07Z')
        self.assertEqual(exact['octal-two'], b'A\x0aZ')
        self.assertEqual(exact['space'], b'left right')
        self.assertEqual(exact['backslash'], b'left\\right')
        for name in ('decimal', 'octal', 'hex', 'hex-upper'):
            self.assertEqual(exact['offset-' + name], b'AB')
        for row in rows:
            facts = row['magic_environment']
            decoded = bytes.fromhex(facts['decoded_hex'])
            observed = row['files']['sample'][16:16+len(decoded)]
            self.assertEqual(observed == decoded, facts['matches'])
            self.assertEqual(row['stdout'], b'sample: fixture' +
                             (b' matched' if facts['matches'] else b'') + b'\n')
            self.assertEqual(row['stderr'], b'')
            self.assertEqual(row['status'], 0)
        self.assertEqual(sum(r['magic_environment']['matches'] for r in rows), 34)

    def test_magic_numeric_samples_use_native_signed_values(self):
        rows = list(magic_cases.cases())
        self.assertEqual(len(rows), 46)
        for row in rows:
            facts = row['magic_environment']
            sample = row['files']['sample'][5:]
            if 'value' in facts:
                self.assertEqual(int.from_bytes(sample, sys.byteorder, signed=True), facts['value'])
                self.assertEqual(len(sample), facts['bytes'])
            if 'complete' in facts:
                self.assertEqual(len(sample), facts['bytes'] - (not facts['complete']))
        # Distinct boundary witnesses must not collapse to the same bytes.
        for kind in ('byte', 'short'):
            minimum = next(r for r in rows if r['id'] == 'file/magic-' + kind + '-minimum-yes')
            maximum = next(r for r in rows if r['id'] == 'file/magic-' + kind + '-maximum-yes')
            self.assertNotEqual(minimum['files']['sample'], maximum['files']['sample'])

    def test_magic_channels_status_and_immutable_inputs_are_required(self):
        self.check_magic_channels_status_and_immutable_inputs_are_required(next(magic_cases.cases()))

    def test_magic_strings_channels_status_and_immutable_inputs_are_required(self):
        self.check_magic_channels_status_and_immutable_inputs_are_required(next(magic_strings.cases()))

    def check_magic_channels_status_and_immutable_inputs_are_required(self, row):
        original = copy.deepcopy(row)
        for fault in (None, 'stdout', 'stderr', 'status', 'sample', 'magic'):
            def capture(binary, invocation, cwd, *args, **kw):
                if fault in ('sample', 'magic'):
                    (cwd / fault).write_bytes(b'changed')
                return (1 if fault == 'status' else 0,
                        dict(stdout=b'wrong' if fault == 'stdout' else row['stdout'],
                             stderr=b'diagnostic' if fault == 'stderr' else b''), [])
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'file': {'path': '/usr/bin/file'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS' if fault is None else 'FAIL', record)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])
        self.assertEqual(row, original)

    def test_magic_setup_failure_prevents_execution_and_cleans(self):
        self.check_magic_setup_failure_prevents_execution_and_cleans(next(magic_cases.cases()))

    def test_magic_strings_setup_failure_prevents_execution_and_cleans(self):
        self.check_magic_setup_failure_prevents_execution_and_cleans(next(magic_strings.cases()))

    def check_magic_setup_failure_prevents_execution_and_cleans(self, row):
        from host_filesystem_cases import setup
        def corrupt(directory, spec):
            cwd = setup(directory, spec)
            (directory / 'sample').write_bytes(b'wrong')
            return cwd
        with tempfile.TemporaryDirectory() as root, \
                patch('host_filesystem.setup', side_effect=corrupt), \
                patch('host_filesystem.smoke.capture') as capture:
            record = run_case(Path('/bin/sh'), {'file': {'path': '/usr/bin/file'}},
                              os.defpath, row, 'direct', Path(root), None)
            capture.assert_not_called()
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertIn('readback mismatch', record['error'])
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_magic_exec_failure_and_timeout_clean_all_modes(self):
        self.check_magic_exec_failure_and_timeout_clean_all_modes(next(magic_cases.cases()))

    def test_magic_strings_exec_failure_and_timeout_clean_all_modes(self):
        self.check_magic_exec_failure_and_timeout_clean_all_modes(next(magic_strings.cases()))

    def check_magic_exec_failure_and_timeout_clean_all_modes(self, row):
        for mode in ('direct', 'string', 'file', 'stdin'):
            for fault in ('exec', 'timeout'):
                with self.subTest(mode=mode, fault=fault), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider = root / 'file'
                    pidfile = root / 'pid'
                    provider.write_text('#!/nonexistent-csh095-interpreter\n' if fault == 'exec' else
                                        '#!/bin/sh\necho $$ > "' + str(pidfile) + '"\nexec /bin/sleep 60\n')
                    provider.chmod(0o700)
                    # A missing interpreter can make shells continue PATH search.
                    # Exclude the real file utility from this failure fixture.
                    record = run_case(Path('/bin/sh'), {'file': {'path': str(provider)}},
                                      str(root), row, mode, root, None, timeout=1)
                    self.assertEqual(record['verdict'], 'FAIL', record)
                    self.assertTrue(record['cleanup'])
                    if fault == 'timeout':
                        self.assertTrue(any('timeout' in e for e in record['errors']), record)
                        pid = int(pidfile.read_text())
                        deadline = time.monotonic() + 2
                        while True:
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            self.assertLess(time.monotonic(), deadline, 'provider was not reaped')
                            time.sleep(.02)
                        pidfile.unlink()
                    self.assertEqual(list(root.iterdir()), [provider])

    def test_logical_cwd_cases_preserve_spec_and_inherited_environment(self):
        rows = list(cwd_cases.logical_cases())
        self.assertEqual(len(rows), 12)
        for row in rows:
            original = copy.deepcopy(row)
            for mode in ('direct', 'string', 'file', 'stdin'):
                with self.subTest(case=row['id'], mode=mode), tempfile.TemporaryDirectory() as root:
                    record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                      os.defpath, row, mode, Path(root), None)
                    self.assertEqual(record['verdict'], 'PASS', record)
                    marker = record['cwd_environment']
                    self.assertEqual(marker['pwd'], marker['pwd_after'])
                    self.assertNotEqual(marker['pwd_identity'], marker['after'])
                    self.assertEqual(marker['pwd'], None if mode == 'direct' else str(Path(record['fixture']).resolve()))
                    self.assertEqual(row, original)
                    self.assertTrue(record['cleanup'])
                    self.assertEqual(list(Path(root).iterdir()), [])

    def test_logical_cwd_rejects_corrupt_environment_and_error_results(self):
        from smoke import capture as real_capture
        faults = ('missing-marker', 'missing-pwd', 'pwd', 'pwd_after', 'pwd_identity',
                  'logical_fallback', 'getcwd_errno', 'status', 'stdout', 'stderr', 'effect')
        for fault in faults:
            def capture(binary, invocation, cwd, *args, **kw):
                status, output, errors = real_capture(binary, invocation, cwd, *args, **kw)
                path = cwd / cwd_cases.MARKER
                marker = json.loads(path.read_text())
                if fault == 'missing-marker':
                    path.unlink()
                elif fault == 'effect':
                    (cwd / 'cwd-parent').mkdir()
                elif fault in ('stdout', 'stderr'):
                    output[fault] = b'unexpected\n' if fault == 'stdout' else b''
                elif fault == 'status':
                    status = 0
                else:
                    if fault == 'missing-pwd':
                        del marker['pwd']
                    else:
                        marker[fault] = (False if fault == 'getcwd_errno' else
                                         marker['after'] if fault == 'pwd_identity' else 'corrupt')
                    path.write_text(json.dumps(marker))
                return status, output, errors
            row = next(r for r in cwd_cases.logical_cases() if r['cwd_action'] == 'delete-parent')
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertTrue(record['cleanup'])

    def test_logical_cwd_setup_and_exec_errors_cannot_pass(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            for fault in ('setup', 'exec'):
                with self.subTest(mode=mode, fault=fault), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider = root / 'pwd'
                    provider.write_text('#!/nonexistent-csh094-interpreter\n')
                    provider.chmod(0o700)
                    row = next(r for r in cwd_cases.logical_cases() if r['cwd_action'] == 'delete-parent')
                    with patch('host_filesystem_cwd.setup') if fault == 'setup' else nullcontext():
                        record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                          os.defpath, row, mode, root, None)
                    self.assertEqual(record['verdict'], 'FAIL', record)
                    self.assertEqual(record['cwd_environment']['phase'], fault + '-failure')
                    self.assertTrue(record['cleanup'])
                    self.assertEqual(list(root.iterdir()), [provider])

    def test_logical_cwd_helper_rejects_a_valid_or_foreign_pwd_before_mutation(self):
        import subprocess
        helper = str(Path(__file__).with_name('host_filesystem_cwd_exec.py').resolve())
        for value in ('cwd-parent/cwd-leaf', 'other'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as root:
                root = Path(root).resolve()
                leaf = root / 'cwd-parent/cwd-leaf'
                leaf.mkdir(parents=True)
                # Deliberately corrupt the inherited input to test the harness;
                # this is never a utility qualification assertion.
                result = subprocess.run([sys.executable, '-S', helper, '--logical-fallback',
                                         'rename-leaf', '/bin/true'], cwd=root,
                                        env={'PWD': str(root / value)}, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 125)
                marker = json.loads((root / cwd_cases.MARKER).read_text())
                self.assertEqual(marker['phase'], 'setup-failure')
                self.assertTrue(leaf.is_dir())
                self.assertFalse((root / 'cwd-renamed').exists())

    def test_logical_cwd_timeout_reaps_provider_and_cleans_all_modes(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            for action in ('rename-parent', 'delete-parent'):
                with self.subTest(mode=mode, action=action), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    provider = root / 'pwd'
                    provider.write_text('#!/bin/sh\nexec /bin/sleep 60\n')
                    provider.chmod(0o700)
                    row = next(r for r in cwd_cases.logical_cases() if r['cwd_action'] == action)
                    record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                      os.defpath, row, mode, root, None, timeout=1)
                    self.assertEqual(record['verdict'], 'FAIL')
                    self.assertTrue(any('timeout' in e for e in record['errors']), record)
                    self.assertTrue(record['cleanup'])
                    pid = record['cwd_environment']['pid']
                    deadline = time.monotonic() + 2
                    while True:
                        try:
                            os.kill(pid, 0)
                        except ProcessLookupError:
                            break
                        self.assertLess(time.monotonic(), deadline, 'timed-out provider was not reaped')
                        time.sleep(.02)
                    self.assertEqual(list(root.iterdir()), [provider])

    def test_output_cases_and_immutable_spec(self):
        import shutil
        self.assertEqual(len(list(output_cases.cases('Darwin'))), 8)
        self.assertEqual(len(list(output_cases.cases('Linux'))), 14)
        for row in output_cases.cases():
            original = copy.deepcopy(row)
            provider = shutil.which(row['utility'], path=os.defpath)
            with self.subTest(case=row['id']), tempfile.TemporaryDirectory() as root:
                record = run_case(Path('/bin/sh'), {row['utility']: {'path': provider}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS', record)
                self.assertTrue(record['cleanup'])
                self.assertEqual(row, original)
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_output_marker_channels_status_and_effect_corruption(self):
        from smoke import capture as real_capture
        row = next(output_cases.cases())
        for fault in ('missing', 'malformed', 'list', 'phase', 'provider', 'action',
                      'errno', 'pid', 'stdout', 'stderr', 'status', 'effect'):
            def capture(binary, invocation, cwd, *args, **kw):
                status, output, errors = real_capture(binary, invocation, cwd, *args, **kw)
                marker = cwd / '.io-fault.json'
                if fault == 'missing':
                    marker.unlink()
                elif fault in ('malformed', 'list'):
                    marker.write_text('{' if fault == 'malformed' else '[]')
                elif fault == 'effect':
                    (cwd / 'data').write_bytes(b'changed')
                elif fault in ('stdout', 'stderr'):
                    output[fault] = b'corrupt' if fault == 'stdout' else b''
                elif fault == 'status':
                    status = 0
                else:
                    data = json.loads(marker.read_text())
                    data[fault] = 'corrupt'
                    marker.write_text(json.dumps(data))
                return status, output, errors
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertTrue(record['cleanup'], record)

    def test_output_exec_failure_and_missing_setup_do_not_pass(self):
        row = next(output_cases.cases())
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                provider = Path(root) / 'pwd'
                provider.write_text('#!/nonexistent-csh093-interpreter\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                  os.defpath, row, mode, Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertEqual(record['kernel_fault']['phase'], 'exec-failure')
                self.assertTrue(record['cleanup'])
            with tempfile.TemporaryDirectory() as root, patch('host_filesystem.smoke.capture',
                    return_value=(125, {'stdout': b'', 'stderr': b'setup failed'}, [])):
                record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                  os.defpath, row, mode, Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertTrue(record['cleanup'])

    def test_output_wrong_kernel_probe_and_device_marker(self):
        import subprocess
        from host_filesystem_fault import marker_matches
        helper = str(Path(__file__).with_name('host_filesystem_fault.py').resolve())
        # A successful write probe must abort before exec, even with the right action.
        script = ('import os,runpy,sys; os.write=lambda *args: 1; '
                  'sys.argv=[sys.argv[1],"broken-pipe","/bin/pwd","-P"]; '
                  'runpy.run_path(sys.argv[0],run_name="__main__")')
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run([sys.executable, '-c', script, helper], cwd=root,
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 125)
            marker = json.loads((Path(root) / '.io-fault.json').read_text())
            self.assertEqual(marker['phase'], 'setup-failure')
            self.assertFalse(marker_matches(marker, 'broken-pipe', '/bin/pwd', errno.EPIPE))
        marker = dict(phase='armed', action='enospc', provider='/bin/pwd',
                      errno=errno.ENOSPC, pid=123, device=dict(path='/dev/full', major=1, minor=7))
        self.assertTrue(marker_matches(marker, 'enospc', '/bin/pwd', errno.ENOSPC))
        for key, value in [('device', {}), ('pid', True), ('pid', 0), ('errno', str(errno.ENOSPC))]:
            corrupted = dict(marker, **{key: value})
            self.assertFalse(marker_matches(corrupted, 'enospc', '/bin/pwd', errno.ENOSPC))

    def test_output_timeout_reaps_provider_and_cleans_fixture(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'pwd'
                provider.write_text('#!/bin/sh\nexec /bin/sleep 60\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                  os.defpath, next(output_cases.cases()), mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in e for e in record['errors']), record)
                self.assertTrue(record['cleanup'])
                pid = record['kernel_fault']['pid']
                deadline = time.monotonic() + 2
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    self.assertLess(time.monotonic(), deadline, 'timed-out provider was not reaped')
                    time.sleep(.02)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_creation_cases_and_immutable_spec(self):
        import shutil
        rows = list(creation.cases())
        self.assertEqual(len(rows), 26)
        for row in rows:
            original = copy.deepcopy(row)
            provider = shutil.which(row['utility'], path=os.defpath)
            with self.subTest(case=row['id']), tempfile.TemporaryDirectory() as root:
                record = run_case(Path('/bin/sh'), {row['utility']: {'path': provider}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS', record)
                self.assertTrue(record['cleanup'])
                self.assertEqual(record['creation_environment']['observed_mask'], row['creation_mask'])
                self.assertEqual(row, original)
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_creation_marker_output_status_and_effect_corruption(self):
        from smoke import capture as real_capture
        row = next(r for r in creation.cases() if r.get('creation_parents'))
        for fault in ('missing', 'malformed', 'list', 'phase', 'provider', 'requested_mask',
                      'observed_mask', 'directory_mode', 'fifo_mode', 'uid', 'euid', 'pid',
                      'stdout', 'stderr', 'status', 'effect', 'identity'):
            def capture(binary, invocation, cwd, *args, **kw):
                status, output, errors = real_capture(binary, invocation, cwd, *args, **kw)
                marker = cwd / creation.MARKER
                if fault == 'missing':
                    marker.unlink()
                elif fault == 'malformed':
                    marker.write_text('{')
                elif fault == 'list':
                    marker.write_text('[]')
                elif fault == 'effect':
                    (cwd / 'existing/new').chmod(0o700)
                elif fault == 'identity':
                    (cwd / 'existing').rename(cwd / 'old-existing')
                    (cwd / 'existing').mkdir(mode=0o751)
                elif fault in ('stdout', 'stderr'):
                    output[fault] = b'corrupt\n'
                elif fault == 'status':
                    status = 1
                else:
                    data = json.loads(marker.read_text())
                    data[fault] = 'corrupt'
                    marker.write_text(json.dumps(data))
                return status, output, errors
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'mkdir': {'path': '/bin/mkdir'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertTrue(record['cleanup'], record)

    def test_creation_partial_setup_failure_never_dispatches(self):
        row = next(r for r in creation.cases() if r.get('creation_parents'))
        real_setup = creation.setup
        def fail(directory, row):
            real_setup(directory, row)
            raise OSError('injected failure after private setup')
        with tempfile.TemporaryDirectory() as root, \
                patch('host_filesystem.creation.setup', side_effect=fail), \
                patch('host_filesystem.smoke.capture') as capture:
            record = run_case(Path('/bin/sh'), {'mkdir': {'path': '/bin/mkdir'}},
                              os.defpath, row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            capture.assert_not_called()
            self.assertTrue(record['cleanup'])

    def test_creation_helper_failure_cannot_satisfy_expected_utility_error(self):
        row = next(r for r in creation.cases() if r['status'] == 'nonzero')
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                provider = Path(root) / 'mkdir'
                provider.write_text('#!/nonexistent-csh092-interpreter\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'mkdir': {'path': str(provider)}},
                                  os.defpath, row, mode, Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertEqual(record['creation_environment']['phase'], 'exec-failure')
                self.assertTrue(record['cleanup'])

    def test_creation_wrong_probe_and_partial_helper_cleanup(self):
        import subprocess
        wrapper = str(Path(__file__).with_name('host_filesystem_creation_exec.py'))
        for fault in ('wrong-mask', 'wrong-mode', 'fifo-failure'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root:
                script = r'''import os, runpy, sys
from unittest.mock import patch
wrapper, fault = sys.argv[1:]
sys.argv = [wrapper, '777', '/bin/true']
real_umask, real_stat = os.umask, os.stat
def umask(mask):
 result = real_umask(mask)
 return 0 if fault == 'wrong-mask' else result
def stat(path, *a, **kw):
 info = real_stat(path, *a, **kw)
 if path == '.creation-probe-dir':
  values = list(info); values[0] |= 0o777
  return os.stat_result(values)
 return info
with patch('os.umask', side_effect=umask) if fault == 'wrong-mask' else patch('os.stat', side_effect=stat) if fault == 'wrong-mode' else patch('os.mkfifo', side_effect=OSError('injected')):
 runpy.run_path(wrapper, run_name='__main__')
'''
                result = subprocess.run([sys.executable, '-c', script, wrapper, fault],
                                        cwd=root, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 125, result)
                marker = json.loads((Path(root) / creation.MARKER).read_text())
                self.assertEqual(marker['phase'], 'setup-failure')
                creation.restore(Path(root), {'creation_mask': 0o777})

    def test_creation_timeout_reaps_provider_and_restores_restrictive_directories(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'mkdir'
                provider.write_text('#!/bin/sh\n/bin/mkdir created\nprintf "%s\\n" "$$"\nexec /bin/sleep 60\n')
                provider.chmod(0o700)
                row = next(creation.cases())
                row['creation_mask'] = 0o777
                record = run_case(Path('/bin/sh'), {'mkdir': {'path': str(provider)}},
                                  os.defpath, row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in e for e in record['errors']), record)
                self.assertTrue(record['cleanup'])
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                deadline = time.monotonic() + 2
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    self.assertLess(time.monotonic(), deadline, 'timed-out provider was not reaped')
                    time.sleep(.02)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_cwd_namespace_cases_and_immutable_spec(self):
        for row in cwd_cases.cases():
            original = copy.deepcopy(row)
            with self.subTest(case=row['id']), tempfile.TemporaryDirectory() as root:
                record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS', record)
                self.assertTrue(record['cleanup'])
                marker = record['cwd_environment']
                self.assertEqual(marker['before'], marker['after'])
                self.assertEqual(marker['old_path_errno'], errno.ENOENT)
                self.assertEqual(row, original)
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_cwd_marker_and_output_status_effect_corruption(self):
        from smoke import capture as real_capture
        row = next(cwd_cases.cases())
        for fault in ('missing', 'malformed', 'list', 'phase', 'provider', 'action',
                      'before', 'after', 'old_path_errno', 'getcwd_errno', 'getcwd',
                      'stdout', 'stderr', 'status', 'effect'):
            def capture(binary, invocation, cwd, *args, **kw):
                status, output, errors = real_capture(binary, invocation, cwd, *args, **kw)
                marker = cwd / cwd_cases.MARKER
                if fault == 'missing':
                    marker.unlink()
                elif fault == 'malformed':
                    marker.write_text('{')
                elif fault == 'list':
                    marker.write_text('[]')
                elif fault == 'effect':
                    (cwd / 'cwd-renamed').rmdir()
                elif fault in ('stdout', 'stderr'):
                    output[fault] = b'corrupt\n'
                elif fault == 'status':
                    status = 1
                else:
                    data = json.loads(marker.read_text())
                    data[fault] = 'corrupt'
                    marker.write_text(json.dumps(data))
                return status, output, errors
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL', record)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_cwd_setup_failure_does_not_dispatch(self):
        real_mkdir = Path.mkdir
        def partial_setup(path, *args, **kw):
            if path.name == 'cwd-leaf':
                path.parent.mkdir(exist_ok=True)
                raise OSError('injected cwd setup failure')
            return real_mkdir(path, *args, **kw)
        with tempfile.TemporaryDirectory() as root, \
                patch('pathlib.Path.mkdir', autospec=True, side_effect=partial_setup), \
                patch('host_filesystem.smoke.capture') as capture:
            record = run_case(Path('/bin/sh'), {'pwd': {'path': '/bin/pwd'}}, os.defpath,
                              next(cwd_cases.cases()), 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            capture.assert_not_called()
            self.assertTrue(record['cleanup'])

    def test_cwd_exec_failure_cannot_satisfy_deleted_directory_error(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            row = next(r for r in cwd_cases.cases() if r['cwd_action'] == 'delete-parent')
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                provider = Path(root) / 'pwd'
                provider.write_text('#!/nonexistent-csh091-interpreter\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                  os.defpath, row, mode, Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertEqual(record['cwd_environment']['phase'], 'exec-failure')
                self.assertTrue(record['cleanup'])

    def test_cwd_wrapper_wrong_probe_and_partial_mutation(self):
        import subprocess
        wrapper = str(Path(__file__).with_name('host_filesystem_cwd_exec.py'))
        # Fault injection is confined to this helper regression subprocess. It
        # never contributes provider evidence or changes the parent process cwd.
        for fault in ('wrong-getcwd', 'getcwd-error', 'wrong-stat', 'remove-parent'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root:
                (Path(root) / 'cwd-parent/cwd-leaf').mkdir(parents=True)
                code = '''import os,runpy,sys
from unittest.mock import patch
wrapper,fault=sys.argv[1:]
root=os.getcwd()
real_stat=os.stat
real_rmdir=os.rmdir
real_getcwd=os.getcwd
def stat(path,*a,**kw):
 if path.endswith('/cwd-parent/cwd-leaf'): raise PermissionError(13,'injected')
 return real_stat(path,*a,**kw)
def rmdir(path,*a,**kw):
 if path.endswith('/cwd-parent'): raise PermissionError(13,'injected')
 return real_rmdir(path,*a,**kw)
calls=0
def getcwd():
 global calls
 calls+=1
 if calls==1: return root
 if fault=='wrong-getcwd': return root
 raise PermissionError(13,'injected')
sys.argv=[wrapper,'delete-parent','/bin/pwd','-P']
target,value=('os.stat',stat) if fault=='wrong-stat' else ('os.rmdir',rmdir) if fault=='remove-parent' else ('os.getcwd',getcwd)
with patch(target,side_effect=value): runpy.run_path(wrapper,run_name='__main__')
'''
                completed = subprocess.run([sys.executable, '-S', '-c', code, wrapper, fault],
                                           cwd=root, capture_output=True, timeout=5)
                self.assertEqual(completed.returncode, 125, completed.stderr)
                marker = json.loads((Path(root) / cwd_cases.MARKER).read_text())
                self.assertEqual(marker['phase'], 'setup-failure')

    def test_cwd_timeout_reaps_provider_and_cleans_every_mode(self):
        for mode in ('direct', 'string', 'file', 'stdin'):
            row = next(r for r in cwd_cases.cases() if r['cwd_action'] == 'delete-parent')
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'pwd'
                # /bin/sh can start in a deleted cwd on both supported hosts.
                provider.write_text('#!/bin/sh\nprintf "%s\\n" "$$"\nexec /bin/sleep 60\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'pwd': {'path': str(provider)}},
                                  os.defpath, row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in e for e in record['errors']), record)
                self.assertTrue(record['cleanup'])
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                deadline = time.monotonic() + 2
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    self.assertLess(time.monotonic(), deadline, 'timed-out provider was not reaped')
                    time.sleep(.02)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_path_limit_probe_keeps_spelling_and_counts_nul(self):
        for row in path_limits.cases():
            with self.subTest(case=row['id']), tempfile.TemporaryDirectory() as root:
                environment = path_limits.setup(Path(root), row)
                limit = environment['selected_limit']
                self.assertEqual(limit, 256 if row['portable'] else os.pathconf(root, 'PC_PATH_MAX'))
                for delta, measured in zip(row['deltas'], environment['measurements']):
                    self.assertEqual(measured['bytes'], limit + delta)
                    self.assertEqual(measured['bytes_with_nul'], limit + delta + 1)
                    self.assertLessEqual(max(map(len, measured['operand'].split('/'))), 2)
                    if measured['bytes'] >= environment['path_max']:
                        self.assertEqual(measured['errno'], errno.ENAMETOOLONG)
                    else:
                        self.assertEqual(measured['errno'], errno.ENOENT if measured['missing'] else 0)

    def test_path_limit_diagnostics_require_each_complete_operand(self):
        row = next(r for r in path_limits.cases() if r.get('missing_middle'))
        with tempfile.TemporaryDirectory() as root:
            path_limits.setup(Path(root), row)
            names = [name.encode() for name in row['diagnostic_operands']]
            good = b''.join(b'pathchk: ' + name + b': pathname too long\n' for name in names)
            self.assertTrue(stderr_matches(row, good))
            for bad in (b'', good.splitlines(keepends=True)[0], good * 2,
                        good.replace(names[1], b'other'), good + b'extra diagnostic\n',
                        good.replace(b'pathname too long', b'permission denied'), good.rstrip(b'\n'),
                        b'\n'.join(names) + b'\n'):
                self.assertFalse(stderr_matches(row, bad))

    def test_path_limit_setup_errors_clean_fixture_without_dispatch(self):
        row = next(path_limits.cases())
        real_stat = os.stat
        def wrong_probe(path, *args, **kw):
            if isinstance(path, str) and path.startswith('./'):
                raise OSError(errno.EACCES, 'injected wrong boundary')
            return real_stat(path, *args, **kw)
        real_mkdir = Path.mkdir
        def partial_setup(path, *args, **kw):
            if path.name == 'aa':
                raise OSError('injected mkdir failure')
            return real_mkdir(path, *args, **kw)
        for fault in ('indeterminate', 'too-large', 'probe', 'partial-setup'):
            target, value = {
                'indeterminate': ('host_filesystem_path_limits.os.pathconf', dict(return_value=-1)),
                'too-large': ('host_filesystem_path_limits.os.pathconf', dict(return_value=999999)),
                'probe': ('host_filesystem_path_limits.os.stat', dict(side_effect=wrong_probe)),
                'partial-setup': ('pathlib.Path.mkdir', dict(autospec=True, side_effect=partial_setup)),
            }[fault]
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch(target, **value), patch('host_filesystem.smoke.capture') as capture:
                record = run_case(Path('/bin/sh'), {'pathchk': {'path': '/usr/bin/pathchk'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
                capture.assert_not_called()
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_path_limit_output_status_effect_failures_and_immutable_spec(self):
        row = next(r for r in path_limits.cases() if r['deltas'] == [0])
        original = copy.deepcopy(row)
        for fault in ('none', 'stdout', 'status', 'diagnostic', 'effect'):
            def capture(binary, invocation, cwd, *args, **kw):
                name = invocation['args'][-1].encode()
                if fault == 'effect':
                    (cwd / 'a').rmdir()
                return (0 if fault == 'status' else 1), dict(
                    stdout=b'wrong' if fault == 'stdout' else b'',
                    stderr=b'' if fault == 'diagnostic' else b'pathchk: ' + name + b': too long\n'), []
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'pathchk': {'path': '/usr/bin/pathchk'}},
                                  os.defpath, row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS' if fault == 'none' else 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertEqual(row, original)

    def test_path_limit_timeout_reaps_child_and_cleans_every_mode(self):
        row = next(path_limits.cases())
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'pathchk'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\n'
                                    'print(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'pathchk': {'path': str(provider)}},
                                  str(root) + ':' + os.defpath, row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in error for error in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                # A non-optimizing /bin/sh may leave its killed child to the
                # container init. Require disappearance within a separate bound,
                # including zombies, rather than depending on scheduler order.
                deadline = time.monotonic() + 2
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    self.assertLess(time.monotonic(), deadline, 'timed-out child was not reaped')
                    time.sleep(0.01)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(root.iterdir()), [provider])

    def test_simple_terminal_prompt_accepts_provider_spelling_on_either_host(self):
        row = next(r for r in terminal_cases() if r['response'] == 'n')
        for mode in row['modes']:
            prefix = b'/selected/rm' if mode == 'pty-direct' else b'rm'
            apple = b'remove data? '
            gnu = prefix + b": remove regular file 'data'? "
            for output in (apple, gnu, gnu + b'junk', gnu.replace(b'data', b'other'), b''):
                with self.subTest(mode=mode, output=output), tempfile.TemporaryDirectory() as root, \
                        patch('host_filesystem.smoke.capture', return_value=(0, dict(output=output), [])):
                    record = run_case(Path('/bin/sh'), {'rm': {'path': '/selected/rm'}}, os.defpath,
                                      row, mode, Path(root), None)
                    self.assertEqual(record['verdict'], 'PASS' if output in (apple, gnu) else 'FAIL')
                    self.assertTrue(record['cleanup'])

    def test_nested_decline_requires_parent_prompt_and_diagnostic(self):
        row = next(r for r in recursive.cases() if r['id'] == 'rm/recursive-declined-descent-parent-y')
        descend = b"/bin/rm: descend into directory 'branch'? "
        child = b"/bin/rm: descend into directory 'branch/sub'? "
        parent = b"/bin/rm: remove directory 'branch'? "
        diagnostic = b"/bin/rm: cannot remove 'branch': Directory not empty\n"
        later = b"/bin/rm: remove regular file 'second'? "
        good = descend + child + parent + diagnostic + later
        self.assertTrue(decisions.output_matches(row, '/bin/rm', good))
        for bad in (good.replace(parent, b''), good.replace(diagnostic, b''),
                    good.replace(parent, child), good.replace(later, b''),
                    good.replace(diagnostic, diagnostic.replace(b'branch', b'elsewhere')),
                    good.replace(diagnostic, diagnostic.replace(b'branch', b'branch/sub')),
                    good + parent, descend + child + diagnostic + parent + later):
            self.assertFalse(decisions.output_matches(row, '/bin/rm', bad))

    def test_nested_decline_rejects_wrong_effect_status_and_output_channel(self):
        row = next(r for r in recursive.cases() if r['id'] == 'rm/recursive-nested-link-n')
        transcript = (b'examine files in directory branch? '
                      b'examine files in directory branch/sub? '
                      b'remove branch/sub/link? remove branch/sub? remove branch? remove second? ')
        for fault in ('none', 'retained-child', 'outside', 'continuation', 'status', 'stdout'):
            def capture(binary, invocation, cwd, *args, **kw):
                (cwd / '.prompt-environment.json').write_text(json.dumps(dict(
                    phase='armed', provider='/bin/rm', stdin_tty=True, stderr_tty=True,
                    stdout_tty=False, foreground=True)))
                (cwd / '.prompt-stdout').write_bytes(b'wrong channel' if fault == 'stdout' else b'')
                if fault != 'continuation':
                    (cwd / 'second').unlink()
                if fault == 'retained-child':
                    (cwd / 'branch/sub/link').unlink()
                if fault == 'outside':
                    (cwd / 'outside/leaf').unlink()
                return (1 if fault == 'status' else 0), dict(output=transcript), []
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'rm': {'path': '/bin/rm'}}, os.defpath,
                                  row, 'pty-direct', Path(root), None)
                self.assertEqual(record['verdict'], 'PASS' if fault == 'none' else 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_nested_partial_setup_failure_cleans_fixture(self):
        row = next(r for r in recursive.cases() if r['id'] == 'rm/recursive-nested-link-n')
        with tempfile.TemporaryDirectory() as root, \
                patch.object(Path, 'symlink_to', side_effect=OSError('injected setup failure')), \
                patch('host_filesystem.smoke.capture') as capture:
            record = run_case(Path('/bin/sh'), {'rm': {'path': '/bin/rm'}}, os.defpath,
                              row, 'pty-direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            capture.assert_not_called()
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_nested_timeout_after_decline_cleans_every_terminal_mode(self):
        row = next(r for r in recursive.cases() if r['id'] == 'rm/recursive-declined-descent-parent-n')
        for mode in decisions.MODES:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow-rm'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,sys,time\n'
                                    'print(os.getpid(),flush=True)\n'
                                    'for target in ("branch", "branch/sub"):\n'
                                    ' sys.stderr.write(target+"? "); sys.stderr.flush()\n'
                                    ' response=sys.stdin.readline()\n'
                                    'sys.stderr.write("declined="+response); sys.stderr.flush()\n'
                                    'time.sleep(60)\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'rm': {'path': str(provider)}}, os.defpath,
                                  row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertIn(b'declined=n', bytes.fromhex(record['terminal_output']['hex']))
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(root.iterdir()), [provider])

    def test_metadata_listing_rejects_corrupt_fields_and_extra_lines(self):
        row = next(r for r in metadata.cases() if r['id'] == 'ls/metadata-numeric-regular')
        with tempfile.TemporaryDirectory() as root:
            environment = metadata.setup(Path(root), row)
            info = environment['measurements']['meta/regular']
            fields = ['-rw-r-----', '1', str(info['uid']), str(info['gid']),
                      '18', 'Jan', '2', '2000', 'meta/regular']
            good = (' '.join(fields) + '\n').encode()
            self.assertTrue(metadata.listing_matches(environment, good))
            for index in range(len(fields)):
                bad = fields.copy()
                bad[index] = 'WRONG'
                self.assertFalse(metadata.listing_matches(environment, (' '.join(bad) + '\n').encode()))
            for bad in (good * 2, good.rstrip(), good + b'diagnostic\n'):
                self.assertFalse(metadata.listing_matches(environment, bad))

    def test_metadata_unrepresentable_timestamps_and_partial_setup_are_cleaned(self):
        row = next(r for r in metadata.cases() if r['id'] == 'find/metadata-newer-after')
        original = os.utime
        for fault in ('rounding', 'setup-error'):
            def faulty_stamp(path, *args, **kw):
                if Path(path).name == 'candidate':
                    if fault == 'setup-error':
                        raise OSError('timestamp fixture setup failed')
                    kw['ns'] = tuple(n // 1000000000 * 1000000000 for n in kw['ns'])
                return original(path, *args, **kw)
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('os.utime', side_effect=faulty_stamp), \
                    patch('host_filesystem.smoke.capture') as capture:
                record = run_case(Path('/bin/sh'), {'find': {'path': '/usr/bin/find'}}, os.defpath,
                                  row, 'direct', Path(root), None)
                self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
                capture.assert_not_called()
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_metadata_wrong_order_status_and_mutation_fail(self):
        row = next(r for r in metadata.cases() if r['id'] == 'ls/metadata-sort-size')
        for fault in ('order', 'status', 'mutation', 'stderr'):
            def capture(binary, invocation, cwd, *args, **kw):
                if fault == 'mutation':
                    (cwd / 'meta/first').write_bytes(b'changed')
                output = b'\n'.join(reversed(row['stdout'].splitlines())) + b'\n' if fault == 'order' else row['stdout']
                return (1 if fault == 'status' else 0), dict(stdout=output,
                        stderr=b'error\n' if fault == 'stderr' else b''), []
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=capture):
                record = run_case(Path('/bin/sh'), {'ls': {'path': '/bin/ls'}}, os.defpath,
                                  row, 'direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertIn('metadata_observed', record)

    def test_metadata_timeout_cleans_process_and_fixture_in_every_mode(self):
        row = next(metadata.cases())
        for mode in ('direct', 'string', 'file', 'stdin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'ls'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\n'
                                    'print(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'ls': {'path': str(provider)}}, str(root) + ':' + os.defpath,
                                  row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(root.iterdir()), [provider])

    def test_sequence_oracle_requires_order_complete_prompts_and_diagnostic(self):
        row = next(r for r in decisions.cases() if r['id'] == 'cp/decisions-missing-between-n')
        first = b"/bin/cp: overwrite 'destination/first'? "
        second = b"/bin/cp: overwrite 'destination/second'? "
        diagnostic = b"/bin/cp: cannot stat 'missing': No such file or directory\n"
        good = first + diagnostic + second
        self.assertTrue(decisions.output_matches(row, '/bin/cp', good))
        self.assertTrue(decisions.output_matches(row, '/bin/cp',
                        first + diagnostic.replace(b'/bin/cp:', b'cp:') + second))
        for bad in (first + second, second + diagnostic + first,
                    first + diagnostic * 2 + second, first + first + diagnostic + second, good + b'junk',
                    good.replace(b'missing', b'unrelated'),
                    good.replace(b'destination/second', b'destination/first')):
            self.assertFalse(decisions.output_matches(row, '/bin/cp', bad))
        # Identical directory targets at descent and deletion must have distinct
        # prompt actions; a transcript cannot reuse the first question twice.
        row = next(r for r in decisions.cases() if r['id'] == 'rm/decisions-recursive-final-n')
        good = (b"/bin/rm: descend into directory 'branch'? "
                b"/bin/rm: remove regular file 'branch/leaf'? "
                b"/bin/rm: remove directory 'branch'? ")
        self.assertTrue(decisions.output_matches(row, '/bin/rm', good))
        self.assertFalse(decisions.output_matches(row, '/bin/rm',
                         good.replace(b'remove directory', b'descend into directory')))
        self.assertEqual(decisions.steps(row), [
            {'expect': 'branch'}, {'expect': '?'}, {'send': 'y\n'},
            {'expect': 'branch/leaf'}, {'expect': '?'}, {'send': 'y\n'},
            {'expect': 'branch'}, {'expect': '?'}, {'send': 'n\n'}])

    def test_sequence_effect_oracle_rejects_stopped_or_reversed_continuation(self):
        from host_filesystem_cases import setup
        row = next(r for r in decisions.cases() if r['id'] == 'mv/decisions-multiple-ny')
        for fault in ('stopped', 'reversed', 'source-retained', 'good'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                setup(root, row)
                if fault == 'reversed':
                    (root / 'first').replace(root / 'destination/first')
                elif fault == 'source-retained':
                    (root / 'destination/second').write_bytes(decisions.SECOND)
                elif fault == 'good':
                    (root / 'second').replace(root / 'destination/second')
                errors, _ = effect_errors(root, row)
                self.assertEqual(bool(errors), fault != 'good')

    def test_recursive_decision_partial_setup_failure_is_cleaned(self):
        row = next(r for r in decisions.cases() if r['id'] == 'rm/decisions-recursive-symlink')
        original = Path.symlink_to
        def fail_branch(path, *args, **kwargs):
            if path.parent.name == 'branch':
                raise OSError('fixture symlink setup failed')
            return original(path, *args, **kwargs)
        with tempfile.TemporaryDirectory() as root, patch.object(Path, 'symlink_to', fail_branch):
            record = run_case(Path('/bin/sh'), {'rm': {'path': '/bin/rm'}}, os.defpath,
                              row, 'pty-direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_sequence_timeout_after_first_response_cleans_owned_process(self):
        # Reach the second prompt wait: early fixture timeout alone does not
        # prove cleanup after a partially completed interaction.
        row = next(r for r in decisions.cases() if r['id'] == 'cp/decisions-multiple-yy')
        for mode in decisions.MODES:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,sys,time\n'
                                    'print(os.getpid(),flush=True)\n'
                                    'sys.stderr.write("destination/first? "); sys.stderr.flush()\n'
                                    'sys.stdin.readline()\n'
                                    'sys.stderr.write("response-received\\n"); sys.stderr.flush()\n'
                                    'time.sleep(60)\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'cp': {'path': str(provider)}}, os.defpath,
                                  row, mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertIn(b'response-received', bytes.fromhex(record['terminal_output']['hex']))
                self.assertTrue(any('timeout' in e and 'destination/second' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(root.iterdir()), [provider])

    def test_overwrite_oracles_reject_wrong_decisions_status_and_channel(self):
        row = next(r for r in interactive.cases() if r['id'] == 'cp/prompt-interactive-n')
        def capture(binary, invocation, cwd, *args, **kwargs):
            (cwd / '.prompt-environment.json').write_text(json.dumps(dict(
                phase='armed', provider='/bin/cp', stdin_tty=True, stderr_tty=True,
                stdout_tty=False, foreground=True)))
            (cwd / '.prompt-stdout').write_bytes(b'')
            return 0, {'output': interactive.prompt_outputs(row, '/bin/cp')[0]}, []
        for fault in ('effect', 'status', 'stdout', 'prompt', 'marker'):
            def corrupt(*args, **kwargs):
                status, output, errors = capture(*args, **kwargs)
                cwd = args[2]
                if fault == 'effect':
                    (cwd / 'target').write_bytes(interactive.SOURCE)
                elif fault == 'status':
                    status = 1
                elif fault == 'stdout':
                    (cwd / '.prompt-stdout').write_bytes(output['output'])
                    output['output'] = b''
                elif fault == 'prompt':
                    output['output'] += b'unexpected diagnostic'
                else:
                    (cwd / '.prompt-environment.json').unlink()
                return status, output, errors
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as root, \
                    patch('host_filesystem.smoke.capture', side_effect=corrupt):
                record = run_case(Path('/bin/true'), {'cp': {'path': '/bin/cp'}}, os.defpath,
                                  row, 'pty-direct', Path(root), None)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertIn('captured', record)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_overwrite_diagnostic_requires_missing_operand_after_prompt(self):
        row = next(r for r in interactive.cases() if r.get('terminal_diagnostic'))
        prompt = interactive.prompt_outputs(row, '/bin/cp')[0]
        self.assertTrue(interactive.output_matches(row, '/bin/cp', prompt + b'cp: missing: no such file\n'))
        for bad in (prompt, b'cp: missing: no such file\n', prompt + b'unrelated error\n'):
            self.assertFalse(interactive.output_matches(row, '/bin/cp', bad))

    def test_overwrite_terminal_setup_failure_retains_cleanup(self):
        row = next(interactive.cases())
        with tempfile.TemporaryDirectory() as root, patch(
                'host_filesystem.smoke.capture', side_effect=pty_harness.PtyUnavailable('no owned PTY')):
            record = run_case(Path('/bin/true'), {'cp': {'path': '/bin/cp'}}, os.defpath,
                              row, 'pty-direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('no owned PTY', record['error'])
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_overwrite_partial_fixture_setup_failure_is_cleaned(self):
        original = Path.write_bytes
        def fail_target(path, data):
            if path.name == 'target':
                raise OSError('injected target setup failure')
            return original(path, data)
        with tempfile.TemporaryDirectory() as root, patch.object(Path, 'write_bytes', fail_target):
            record = run_case(Path('/bin/true'), {'cp': {'path': '/bin/cp'}}, os.defpath,
                              next(interactive.cases()), 'pty-direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_overwrite_timeout_kills_owned_provider_and_cleans_fixture(self):
        for mode in ('pty-direct', 'pty-string', 'pty-file'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\n'
                                    'print(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                record = run_case(Path('/bin/sh'), {'cp': {'path': str(provider)}}, os.defpath,
                                  next(interactive.cases()), mode, root, None, timeout=1)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertTrue(record['cleanup'])
                self.assertEqual(list(root.iterdir()), [provider])

    def test_accounting_rejects_wrong_totals_duplicates_and_missing_paths(self):
        row = next(r for r in isolated.cases() if r.get('accounting'))
        with tempfile.TemporaryDirectory() as root:
            environment = isolated.setup(Path(root), row)
            expected = environment['expected']
            good = b''.join(f'{count}\t{name}\n'.encode() for name, count in expected.items())
            self.assertTrue(isolated.accounting_matches(environment, good))
            for bad in (good + good, good.splitlines(keepends=True)[0],
                        good.replace(b'account/sub', b'wrong/sub'),
                        b''.join(f'{count + 1}\t{name}\n'.encode() for name, count in expected.items())):
                self.assertFalse(isolated.accounting_matches(environment, bad))
            (Path(root) / 'account/top').write_bytes(b'changed')
            self.assertEqual(isolated.verify(Path(root), environment),
                             ['accounting fixture changed during execution'])

    def test_hardlink_accounting_counts_inode_once(self):
        row = next(r for r in isolated.cases() if r.get('accounting', {}).get('hardlink'))
        with tempfile.TemporaryDirectory() as root:
            environment = isolated.setup(Path(root), row)
            count = environment['expected']['account']
            duplicate = environment['measurements']['account/sub/twin']['blocks']
            self.assertGreater(duplicate, 0)
            self.assertTrue(isolated.accounting_matches(environment, f'{count}\taccount\n'.encode()))
            self.assertFalse(isolated.accounting_matches(environment, f'{count + (duplicate + 1) // 2}\taccount\n'.encode()))

    def test_isolated_partial_setup_failure_is_cleaned(self):
        row = next(r for r in isolated.cases() if r.get('accounting', {}).get('hardlink'))
        with tempfile.TemporaryDirectory() as root, patch.object(isolated.os, 'link', side_effect=OSError('fixture link failure')):
            record = run_case(Path('/bin/true'), {'du': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_unrepresentable_timestamp_is_setup_failure(self):
        row = next(r for r in isolated.cases() if r.get('timestamp_environment'))
        original = os.utime
        def ignore_subseconds(path, *args, **kwargs):
            if 'ns' not in kwargs:
                return original(path, *args, **kwargs)
        with tempfile.TemporaryDirectory() as root, patch.object(isolated.os, 'utime', side_effect=ignore_subseconds):
            record = run_case(Path('/bin/true'), {'touch': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertIn('cannot represent', record['error'])
            self.assertTrue(record['cleanup'])

    def test_nanosecond_effect_oracle_rejects_truncated_timestamp(self):
        row = next(r for r in isolated.cases() if r.get('timestamp_environment'))
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'empty').touch()
            os.utime(root / 'empty', ns=(isolated.STAMP_NS, isolated.STAMP_NS))
            self.assertEqual(effect_errors(root, row)[0], [])
            truncated = isolated.STAMP_NS // 1000000000 * 1000000000
            os.utime(root / 'empty', ns=(truncated, truncated))
            self.assertEqual(effect_errors(root, row)[0], ['effect mismatch: empty'])

    def test_isolated_timeout_cleanup_for_each_environment(self):
        for capability in ('accounting', 'timestamp_environment', 'files'):
            with self.subTest(capability=capability), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                row = next(r for r in isolated.cases() if r.get(capability))
                record = run_case(provider, {row['utility']: {'path': str(provider)}}, os.defpath,
                                  row, 'direct', root, None, timeout=2)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_numeric_magic_negative_samples_have_distinct_oracles(self):
        rows = {r['id']: r for r in isolated.cases() if r['utility'] == 'file'}
        for key, positive in rows.items():
            if key.endswith('-yes'):
                negative = rows[key[:-4] + '-no']
                self.assertEqual(positive['files']['magic'], negative['files']['magic'])
                self.assertNotEqual(positive['files']['sample'], negative['files']['sample'])
                self.assertFalse(stdout_matches(positive['stdout'], negative['stdout'], None, None, positive))

    def test_permission_setup_rejects_root_and_cleans_private_tree(self):
        row = next(r for r in residual_cases() if r.get('permission_denied'))
        with tempfile.TemporaryDirectory() as root, patch('host_filesystem_residual_cases.os.geteuid', return_value=0):
            record = run_case(Path('/bin/true'), {'cp': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_permission_denial_must_be_independently_proved(self):
        import host_filesystem_residual_cases as residual
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            row = next(r for r in residual_cases() if r.get('permission_denied'))
            with patch.object(residual.os, 'geteuid', return_value=10001):
                residual.setup(root, row)
            # Simulate a filesystem that ignores mode bits. It cannot qualify.
            with patch.object(Path, 'chmod'):
                with self.assertRaisesRegex(OSError, 'unexpectedly succeeded'):
                    residual.arm(root, row)
            residual.restore(root, row)

    def test_residual_timeout_cleanup_for_each_environment(self):
        for capability in ('permission_denied', 'files', 'byte_link'):
            with self.subTest(capability=capability), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                row = next(r for r in residual_cases() if r.get(capability))
                record = run_case(provider, {row['utility']: {'path': str(provider)}}, os.defpath,
                                  row, 'direct', root, None, timeout=2)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_residual_effect_failure_is_not_hidden_by_permission_restore(self):
        row = next(r for r in residual_cases() if r['utility'] == 'rm')
        def corrupt(*args, **kwargs):
            directory = args[2]
            (directory / 'denied').chmod(0o700)
            (directory / 'denied/leaf').unlink()
            return 1, {'stdout': b'', 'stderr': b'denied'}, []
        with tempfile.TemporaryDirectory() as root, patch('host_filesystem.smoke.capture', side_effect=corrupt):
            record = run_case(Path('/bin/true'), {'rm': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('effect mismatch: denied/leaf', record['errors'])
            self.assertTrue(record['cleanup'])

    def test_magic_setup_write_failure_is_not_a_provider_result(self):
        original = Path.write_bytes
        def fail_sample(path, data):
            if path.name == 'sample':
                raise OSError('injected fixture write failure')
            return original(path, data)
        row = next(r for r in residual_cases() if r.get('files'))
        with tempfile.TemporaryDirectory() as root, patch.object(Path, 'write_bytes', fail_sample):
            record = run_case(Path('/bin/true'), {'file': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_byte_link_setup_failure_is_not_a_provider_result(self):
        original = os.symlink
        def fail_bytes(target, link, *args, **kwargs):
            if isinstance(target, bytes):
                raise OSError('injected fixture symlink failure')
            return original(target, link, *args, **kwargs)
        row = next(r for r in residual_cases() if r.get('byte_link'))
        with tempfile.TemporaryDirectory() as root, patch('os.symlink', side_effect=fail_bytes):
            record = run_case(Path('/bin/true'), {'readlink': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_magic_and_byte_oracles_reject_changed_output(self):
        for row in residual_cases():
            if row.get('files') or row.get('byte_link'):
                output = row['stdout']
                self.assertTrue(stdout_matches(output, output, Path('.'), Path('.'), row))
                self.assertFalse(stdout_matches(output, output + b'wrong', Path('.'), Path('.'), row))

    def test_complete_unique_case_inventory(self):
        rows = list(cases()) + list(audit_cases()) + list(terminal_cases()) + list(extended_cases("Linux")) + list(remaining_cases()) + list(residual_cases()) + list(isolated.cases()) + list(interactive.cases()) + list(decisions.cases()) + list(metadata.cases()) + list(recursive.cases()) + list(path_limits.cases()) + list(cwd_cases.cases()) + list(creation.cases()) + list(output_cases.cases("Linux")) + list(cwd_cases.logical_cases()) + list(magic_cases.cases()) + list(calendar_cases.cases()) + list(reference_cases.cases()) + list(datetime_cases.cases()) + list(timezone_cases.cases()) + list(day_rules.cases()) + list(transition_times.cases()) + list(magic_strings.cases())
        self.assertEqual({r['utility'] for r in rows}, set(UTILITIES))
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        self.assertTrue(all('gap' not in r for r in rows))

    def test_remaining_capability_setup_failure_is_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            row = next(r for r in remaining_cases() if r.get('utf8'))
            record = run_case(Path('/bin/true'), {row['utility']: {'path': '/bin/true'}},
                              os.defpath, row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])

    def test_allocation_markers_reject_missing_unarmed_and_malformed_results(self):
        from host_filesystem import allocation_marker_matches
        expected = dict(requested=2, triggered=1, calls_min=2, calls_max=4)
        self.assertTrue(allocation_marker_matches(expected, dict(requested=2, triggered=1, calls=3)))
        for marker in ({}, [], dict(requested=2, triggered=0, calls=2),
                       dict(requested=2, triggered=1, calls=1), dict(requested=2, triggered=1, calls=5),
                       dict(requested=2, triggered=True, calls=2)):
            self.assertFalse(allocation_marker_matches(expected, marker))
        with tempfile.TemporaryDirectory() as root:
            row = case('readlink', 'unarmed-allocation', ['link'], status='nonzero', err='nonempty',
                       allocation_fault=expected)
            with patch('host_filesystem.smoke.capture', return_value=(1, {'stdout': b'', 'stderr': b'failed'}, [])):
                record = run_case(Path('/bin/true'), {'readlink': {'path': '/bin/true'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('allocation marker' in e for e in record['errors']))
            self.assertTrue(record['cleanup'])

    def test_dd_oracle_rejects_padded_input_as_whole_record(self):
        row = next(r for r in remaining_cases() if r['id'] == 'dd/remaining-sync')
        good = b'0+1 records in\n1+0 records out\n4 bytes copied, 1 s, 4 B/s\n'
        self.assertTrue(stderr_matches(row, good))
        self.assertFalse(stderr_matches(row, good.replace(b'0+1', b'1+0')))
        self.assertFalse(stderr_matches(row, good.replace(b'4 bytes', b'5 bytes')))

    def test_each_remaining_contract_has_environment_reason_and_owner(self):
        root = Path(__file__).resolve().parent
        ledger = json.loads((root / 'host_filesystem_residuals.json').read_text())
        self.assertFalse(ledger['full_contracts_qualified'])
        self.assertEqual({r['utility'] for r in ledger['utilities']}, set(UTILITIES))
        self.assertEqual(len(ledger['utilities']), len(UTILITIES))
        for row in ledger['utilities']:
            self.assertEqual(row['next_owner'], utility_owner(row['utility']))
            self.assertEqual(row['status'], 'open')
            self.assertTrue(all(row[key] for key in ('reason', 'required_environment', 'remaining', 'implementation_owner')))
        manifest = json.loads((root / 'host_contracts.json').read_text())
        conditions = {c for owner in manifest['owners'] if 'basename' in owner['utilities'] for c in owner['conditions']}
        self.assertEqual({r['id'] for r in ledger['conditions']}, conditions)
        self.assertTrue(all(r['next_owner'] == utility_owner('basename') for r in ledger['conditions']))

    def test_missing_provider_is_setup_failure_and_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            row = case('cp', 'missing-provider', ['data', 'copy'])
            record = run_case(Path('/missing-shell'), {'cp': {'path': None}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_timeout_is_fatal_and_owned_process_disappears(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            provider = root / 'slow'
            provider.write_text('#!' + sys.executable + ' -S\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
            provider.chmod(0o700)
            record = run_case(provider, {'basename': {'path': str(provider)}}, os.defpath,
                              case('basename', 'timeout', ['a']), 'direct', root, None, timeout=1)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('timeout' in error for error in record['errors']))
            pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
            self.assertTrue(record['cleanup'])
            self.assertFalse(list(root.glob('csh-filesystem-*')))

    def test_unavailable_terminal_is_failure_with_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            row = next(terminal_cases())
            with patch('host_filesystem.smoke.capture', side_effect=pty_harness.PtyUnavailable('no terminal')):
                record = run_case(Path('/bin/rm'), {'rm': {'path': '/bin/rm'}}, os.defpath,
                                  row, 'pty-direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('no terminal', record['error'])
            self.assertTrue(record['cleanup'])

    def test_corrupt_archive_is_failed_assertion_with_cleanup(self):
        import tarfile
        with tempfile.TemporaryDirectory() as root:
            row = case('pax', 'corrupt-archive', [], archive='write')
            with patch('host_filesystem.smoke.capture', return_value=(0, {'stdout': b'', 'stderr': b''}, [])), \
                    patch('host_filesystem.effect_errors', side_effect=tarfile.ReadError('bad archive')):
                record = run_case(Path('/bin/pax'), {'pax': {'path': '/bin/pax'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'assertion'))
            self.assertIn('bad archive', record['error'])
            self.assertTrue(record['cleanup'])

    def test_fault_setup_failure_cannot_satisfy_error_oracle(self):
        with tempfile.TemporaryDirectory() as root:
            row = case('dd', 'broken-pipe', ['if=data'], status='nonzero', err='nonempty', io_action='broken-pipe')
            with patch('host_filesystem.smoke.capture', return_value=(125, {'stdout': b'', 'stderr': b'loader failed'}, [])):
                record = run_case(Path('/missing-shell'), {'dd': {'path': '/bin/dd'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('kernel fault marker' in e for e in record['errors']))
            self.assertTrue(record['cleanup'])

    def test_real_kernel_fault_control_does_not_accept_success(self):
        import errno
        import shutil
        with tempfile.TemporaryDirectory() as root:
            provider = shutil.which('true', path=os.defpath)
            row = case('dd', 'success-under-fault', [], status='nonzero', err='nonempty', io_action='broken-pipe')
            record = run_case(Path(provider), {'dd': {'path': provider}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual(record['kernel_fault']['phase'], 'armed')
            self.assertEqual(record['kernel_fault']['errno'], errno.EPIPE)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('status mismatch', record['errors'])
            self.assertTrue(record['cleanup'])

    def test_archive_oracle_rejects_duplicate_members(self):
        import tarfile
        from host_filesystem_extended import archive_errors
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            with tarfile.open(root / 'archive', 'w') as archive:
                for _ in range(2):
                    archive.addfile(tarfile.TarInfo('archived'))
            errors, _ = archive_errors(root, {'archive_output': 'append'})
            self.assertEqual(errors, ['archive member set mismatch'])

    def test_effect_oracle_rejects_link_instead_of_regular_copy(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'data').write_bytes(DATA)
            (root / 'copy').symlink_to('data')
            errors, _ = effect_errors(root, case('cp', 'bytes', [], effects={'copy': {'content': DATA}}))
            self.assertEqual(errors, ['effect mismatch: copy'])

    def test_archive_oracle_does_not_open_fifo(self):
        from host_filesystem_extended import archive_errors
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            os.mkfifo(root / 'archive')
            errors, _ = archive_errors(root, {'archive_output': 'types'})
            self.assertEqual(errors, ['archive is not a bounded regular file'])

    def test_new_required_contract_failures_are_not_allowed(self):
        row = next(r for r in audit_cases() if r['utility'] == 'readlink')
        self.assertFalse(stderr_matches(row, b''))
        self.assertTrue(stderr_matches(row, b'not a symbolic link\n'))

    def test_df_oracle_checks_percentage_header_and_record_count(self):
        good = b'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/example 120 30 70 30% /\n'
        self.assertTrue(stdout_matches('df-portable', good, None, None, {}))
        for bad in (good.replace(b'30%', b'31%'), good + b'junk\n', good.replace(b'1024-blocks', b'512-blocks')):
            self.assertFalse(stdout_matches('df-portable', bad, None, None, {}))

    def test_clause_map_preserves_every_provider_and_normative_section(self):
        root = Path(__file__).resolve().parent
        mapping = json.loads((root / 'host_filesystem_contracts.json').read_text())
        self.assertEqual({r['utility'] for r in mapping['utilities']}, set(UTILITIES))
        ids = {r['id'] for r in list(cases()) + list(audit_cases()) + list(terminal_cases()) + list(extended_cases("Linux")) + list(remaining_cases()) + list(residual_cases()) + list(isolated.cases()) + list(interactive.cases()) + list(decisions.cases()) + list(metadata.cases()) + list(recursive.cases()) + list(path_limits.cases()) + list(cwd_cases.cases()) + list(creation.cases()) + list(output_cases.cases("Linux")) + list(cwd_cases.logical_cases()) + list(magic_cases.cases()) + list(calendar_cases.cases()) + list(reference_cases.cases()) + list(datetime_cases.cases()) + list(timezone_cases.cases()) + list(day_rules.cases()) + list(transition_times.cases()) + list(magic_strings.cases())}
        for row in mapping['utilities']:
            self.assertFalse(row['full_contract_qualified'])
            self.assertTrue(row['remaining'])
            self.assertTrue(set(row['assertions']) <= ids)
            self.assertEqual(set(row['normative_headings']), set(row['sections']))
            self.assertTrue(all(value['disposition'] for value in row['sections'].values()))
            self.assertEqual(row['owner'], utility_owner(row['utility']))
        self.assertEqual({i for row in mapping['utilities'] for i in row['assertions']}, ids)
        for row in extended_cases('Linux'):
            mapping_row = next(r for r in mapping['utilities'] if r['utility'] == row['utility'])
            bucket = 'strict_provider_audit' if row.get('provider_audit') else 'passing_scope'
            self.assertIn(row['id'], mapping_row['extended_qualification'][bucket])


if __name__ == '__main__':
    unittest.main()
