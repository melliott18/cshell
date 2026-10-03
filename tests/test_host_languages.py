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


if __name__=='__main__':
    unittest.main()
