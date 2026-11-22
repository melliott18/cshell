"""Qualification controls must reject incorrect providers and retain failures."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pty_harness

from host_language_cases import UTILITIES, cases
from host_languages import matches, run_case, run_signal
import time
import subprocess
import signal


class LanguageEvidenceTests(unittest.TestCase):
    def test_contract_accounting(self):
        manifest=json.loads(Path(__file__).with_name('host_language_contracts.json').read_text())
        rows=list(cases())
        ids={r['id'] for r in rows}
        ids.update('ed/signal-'+s for s in ('hup','hup-home','int'))
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertEqual(set(UTILITIES),{r['utility'] for r in manifest['pages']})
        required={'NAME','SYNOPSIS','DESCRIPTION','OPTIONS','OPERANDS','STDIN','INPUT FILES',
                  'ENVIRONMENT VARIABLES','ASYNCHRONOUS EVENTS','STDOUT','STDERR',
                  'OUTPUT FILES','EXTENDED DESCRIPTION','EXIT STATUS','CONSEQUENCES OF ERRORS'}
        for page in manifest['pages']:
            self.assertEqual(len(page['source_sha256']),64)
            headings={s['section'] for s in page['sections']}
            self.assertEqual(set(page['selected_contracts']),
                             {r['id'] for r in rows if r['utility']==page['utility']})
            self.assertTrue(required <= headings)
            for section in page['sections']:
                self.assertTrue(section['reason'])
                self.assertEqual(section['owner'],'CSH-074')
                self.assertTrue(set(section['witnesses']) <= ids)
            for row in rows:
                if row['utility']==page['utility']:
                    self.assertTrue(set(row['clauses']) <= headings)
                    for clause in row['clauses']:
                        section=next(s for s in page['sections'] if s['section']==clause)
                        self.assertIn(row['id'],section['witnesses'])
                    self.assertNotIn('gap',row)
        from host_language_provider_cases import cases as remaining_cases
        remaining=list(remaining_cases())
        self.assertTrue({r['id'] for r in remaining} <= ids)
        self.assertEqual({r['id'] for r in remaining},
                         {r['id'] for r in manifest['provider_regressions']})

    def test_multibyte_audit_contract_accounting(self):
        from host_language_multibyte_cases import cases as audit_cases
        manifest = json.loads(Path(__file__).with_name('host_language_contracts.json').read_text())
        rows = list(audit_cases())
        self.assertEqual({r['id'] for r in rows}, {r['id'] for r in manifest['multibyte_audit']})
        for row in rows:
            page = next(p for p in manifest['pages'] if p['utility'] == row['utility'])
            self.assertTrue(set(row['clauses']) <= {s['section'] for s in page['sections']})

    def test_status_ranges_exclude_signal_death(self):
        for expectation in ('normal','nonzero','error','xargs-error'):
            self.assertFalse(matches(expectation,-9))
        self.assertTrue(matches('normal',0))
        self.assertFalse(matches('xargs-error',126))
        self.assertTrue(matches('xargs-error',125))

    def test_wrong_outputs_status_and_effects_fail_and_remove_fixtures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            provider=root/'provider'
            provider.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nprint("actual")\nPath("result").write_bytes(b"actual")\n')
            provider.chmod(0o700)
            control=dict(id='control',utility='provider',args=[],stdin=b'',
                         stdout=b'actual\n',stderr=b'',status=0,files={'result':b'actual'},
                         file_rules=[dict(pattern='result',count=1,data=b'actual')])
            for change in ({},{'stdout':b'wrong\n'},{'status':1},{'files':{'result':b'wrong'}},
                           {'nonempty_files':['missing']},{'stderr':b'wrong'},
                           {'file_rules':[dict(pattern='result',count=2)]},
                           {'file_rules':[dict(pattern='result',count=1,data=b'wrong')]},
                           {'file_rules':[dict(pattern='result',count=1,data={'regex':rb'wrong.*'})]},
                           {'file_rules':[dict(pattern='missing*',count=1)]}):
                result=run_case(provider,str(provider),dict(control,**change),'direct',root,os.defpath)
                self.assertEqual(result['verdict'],'FAIL' if change else 'PASS')
                self.assertTrue(result['fixture_removed'])
                self.assertIn('actual',result)

    def test_signal_timeout_cleans_descendants_and_preserves_unrelated_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / 'pids'
            provider = root / 'provider'
            provider.write_text('#!' + sys.executable + '\n' +
                'import os, signal, time\n' +
                'signal.signal(signal.SIGHUP, signal.SIG_IGN)\n' +
                'pid = os.fork()\n' +
                'if pid == 0:\n    time.sleep(30)\nelse:\n' +
                '    open(' + repr(str(marker)) + ', "w").write(str(pid))\n' +
                '    print("recovered", flush=True)\n    time.sleep(30)\n')
            provider.chmod(0o700)
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            try:
                started = time.monotonic()
                record = run_signal(provider, str(provider), 'hup', 'direct', root, os.defpath)
                self.assertLess(time.monotonic() - started, 10)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(record['fixture_removed'])
                self.assertIsNone(unrelated.poll())
                pid = int(marker.read_text())
                # The inherited group cleanup kills descendants; container PID 1
                # may retain a dead orphan briefly, as in the shared smoke tests.
                proc = Path('/proc') / str(pid) / 'stat'
                deadline = time.monotonic() + 2
                while True:
                    try:
                        if proc.exists():
                            state = proc.read_text().rsplit(')', 1)[1].split()[0]
                            if state == 'Z':
                                break
                        else:
                            os.kill(pid, 0)
                    except (FileNotFoundError, ProcessLookupError):
                        break
                    # SIGKILL delivery is asynchronous. Wait for observed death,
                    # not merely successful signal delivery; a survivor still
                    # fails within a fixed bound on both Linux and Darwin.
                    if time.monotonic() >= deadline:
                        self.fail(f'owned descendant {pid} survived cleanup')
                    time.sleep(0.01)
            finally:
                unrelated.terminate()
                unrelated.wait(timeout=2)
                if marker.exists():
                    try:
                        os.kill(int(marker.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_setup_error_is_not_a_skip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            row=dict(id='missing',utility='missing',args=[],stdin=b'',stdout=b'',stderr=b'',status=0)
            result=run_case(root/'none',str(root/'none'),row,'direct',root,os.defpath)
            self.assertEqual(result['verdict'],'FAIL')
            self.assertTrue(result['fixture_removed'])
            self.assertIn('error',result)

    def test_terminal_streams_and_transcript_are_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = root/'provider'
            row = dict(id='control/terminal', utility='provider', args=[], stdin=b'',
                       terminal='stdout', steps=[{'send': 'y\n'}], status=0,
                       stdout={'regex': rb'prompt\nreply:y\n'}, stderr=b'')
            for fd, extra, expected in [(1, '', 'PASS'), (2, '', 'FAIL'),
                                        (1, 'print("extra")', 'FAIL'),
                                        (1, 'print("runtime error: injected")', 'FAIL')]:
                provider.write_text('#!'+sys.executable+'\nimport os\n'+
                    f'os.write({fd},b"prompt\\nreply:"+os.read(0,100))\n'+extra+'\n')
                provider.chmod(0o700)
                result = run_case(provider, str(provider), row, 'direct', root, os.defpath)
                self.assertEqual(result['verdict'], expected, result)
                self.assertTrue(result['fixture_removed'])

    def test_terminal_unavailable_is_retained_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = dict(id='control/no-terminal', utility='ed', args=[], stdin=b'',
                       terminal='stdout', steps=[], status=0, stdout=b'', stderr=b'')
            with patch('pty_harness.capture', side_effect=pty_harness.PtyUnavailable('no controlling tty')):
                result = run_case(Path(sys.executable), sys.executable, row, 'direct', root, os.defpath)
            self.assertEqual(result['verdict'], 'FAIL')
            self.assertIn('no controlling tty', result['error'])
            self.assertTrue(result['fixture_removed'])

    def test_signal_recovery_cannot_hide_editor_sanitizer_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            provider=root/'provider'
            provider.write_text('#!'+sys.executable+'\n'+
                'from pathlib import Path\nimport os,signal,sys\n'+
                'def recover(*args):\n'+
                '    Path(".home/ed.hup").write_bytes(b"recovered\\n")\n'+
                '    os.write(2,b"ERROR: AddressSanitizer: injected\\n")\n'+
                '    sys.exit(0)\n'+
                'signal.signal(signal.SIGHUP,recover)\n'+
                'print("recovered",flush=True)\n'+
                'Path("ready").write_text("ready")\n'+
                'while True: signal.pause()\n')
            provider.chmod(0o700)
            record=run_signal(provider,str(provider),'hup-home','direct',root,os.defpath)
            self.assertEqual(record['verdict'],'FAIL')
            self.assertIn('editor sanitizer diagnostic',record['actual']['errors'])
            self.assertTrue(record['fixture_removed'])


class EdResponseCaptureTests(unittest.TestCase):
    def test_real_editor_stderr_eof_precedes_queued_final_response(self):
        from ed_signal_order_probe import probe
        helper = Path(__file__).with_name('host_language_helper.py').resolve()
        editor = helper.parents[1] / 'build/host-ed'
        if not editor.exists():
            self.skipTest('build/host-ed is built by test-host-languages')
        record = probe(helper, [str(editor), '-s', 'original'])
        self.assertEqual(record['outcome'], 'PASS', record)
        self.assertEqual(record['files']['saved'], b'recovered\n'.hex())
        self.assertTrue(record['reaped'])
        self.assertTrue(record['fixture_removed'])
        reads = [e for e in record['events'] if e['event'] == 'read']
        self.assertEqual(reads[0], dict(event='read', stream='stderr', data=''))
        self.assertEqual(reads[1]['stream'], 'stdout')
        self.assertIn(b'recovered\n'.hex(), reads[1]['data'])

    def test_pipe_eof_does_not_discard_other_stream_and_marker_can_split(self):
        from host_language_helper import EdCapture
        for response_stream in ('stdout', 'stderr'):
            with self.subTest(response_stream=response_stream):
                out_read, out_write = os.pipe()
                err_read, err_write = os.pipe()
                capture = EdCapture(out_read, err_read)
                try:
                    closed_write = err_write if response_stream == 'stdout' else out_write
                    live_write = out_write if response_stream == 'stdout' else err_write
                    os.close(closed_write)
                    capture.read(time.monotonic() + 1)
                    self.assertEqual(len(capture.selector.get_map()), 1)
                    os.write(live_write, b'recov')
                    # Use small real reads to split the response across batches.
                    real_read = os.read
                    with patch('host_language_helper.os.read', side_effect=lambda fd, n: real_read(fd, min(n, 3))):
                        os.write(live_write, b'ered\n')
                        capture.read_until(b'recovered\n')
                    os.close(live_write)
                    capture.drain()
                    self.assertEqual(bytes(getattr(capture, response_stream)), b'recovered\n')
                    # Old bytes must not satisfy a new response boundary.
                    with self.assertRaisesRegex(RuntimeError, 'exited before response'):
                        capture.read_until(b'recovered\n')
                finally:
                    capture.close()
                    os.close(out_read)
                    os.close(err_read)

    def test_signal_bad_providers_fail_reap_and_remove_fixtures(self):
        # A small protocol peer exercises the real PTY, selector and outer
        # cleanup without depending on timing or a permissive provider oracle.
        protocol = '''import os, signal, sys, time
from pathlib import Path
variant = VARIANT
signal.signal(signal.SIGINT, lambda *args: os.write(1, b'?\\n*'))
for line in sys.stdin:
    if line.startswith('!'):
        Path('ready').write_text('ready')
    elif line == '1p\\n':
        os.write(1, b'recovered\\n')
    elif line == 'P\\n':
        os.write(1, b'*')
        break
for line in sys.stdin:
    if line == '1p\\n':
        if variant != 'missing': os.write(1, b'recovered\\n')
    elif line == 'w saved\\n':
        Path('saved').write_bytes(b'wrong\\n' if variant == 'file' else b'recovered\\n')
    elif line == 'q\\n':
        if variant == 'stdout': os.write(1, b'extra')
        if variant == 'stderr': os.write(2, b'extra')
        if variant == 'flood':
            while True: os.write(2, b'x' * 4096)
        if variant == 'timeout': time.sleep(30)
        if variant == 'death': os.kill(os.getpid(), signal.SIGKILL)
        break
'''
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = root / 'provider'
            for variant in ('ok', 'missing', 'file', 'stdout', 'stderr', 'flood', 'timeout', 'death'):
                with self.subTest(variant=variant):
                    provider.write_text('#!' + sys.executable + '\n' + protocol.replace('VARIANT', repr(variant)))
                    provider.chmod(0o700)
                    started = time.monotonic()
                    record = run_signal(provider, str(provider), 'int', 'direct', root, os.defpath)
                    self.assertLess(time.monotonic() - started, 7)
                    self.assertEqual(record['verdict'], 'PASS' if variant == 'ok' else 'FAIL', record)
                    self.assertTrue(record['fixture_removed'])
                    self.assertTrue(record['signal']['reaped'], record)
                    self.assertLessEqual(len(bytes.fromhex(record['signal']['stdout'])) +
                                         len(bytes.fromhex(record['signal']['stderr'])), 65536)

    def test_setup_failures_close_pty_and_retain_record(self):
        import host_language_helper as helper
        for failure in ('attributes', 'spawn', 'capture'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                previous = Path.cwd()
                descriptors = []
                real_openpty = helper.pty.openpty
                def openpty():
                    pair = real_openpty()
                    descriptors.extend(pair)
                    return pair
                try:
                    os.chdir(temporary)
                    target = dict(attributes='termios.tcgetattr', spawn='subprocess.Popen',
                                  capture='EdCapture')[failure]
                    with patch.object(helper.pty, 'openpty', side_effect=openpty), \
                         patch('host_language_helper.' + target, side_effect=OSError('injected setup failure')):
                        with self.assertRaisesRegex(OSError, 'injected setup failure'):
                            helper.ed_signal([sys.executable, '-c', 'import time; time.sleep(30)'], 'int')
                    detail = json.loads(Path('signal.json').read_text())
                    self.assertTrue(detail['incomplete'])
                    if failure == 'capture':
                        self.assertTrue(detail['reaped'])
                        self.assertEqual(detail['status'], -signal.SIGKILL)
                    else:
                        self.assertIsNone(detail['status'])
                    for fd in descriptors:
                        with self.assertRaises(OSError):
                            os.fstat(fd)
                finally:
                    os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
