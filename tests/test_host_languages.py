"""Qualification controls must reject incorrect providers and retain failures."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

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
            self.assertTrue(required <= headings)
            for section in page['sections']:
                self.assertTrue(section['reason'])
                self.assertEqual(section['owner'],'CSH-074')
                self.assertTrue(set(section['witnesses']) <= ids)
            for row in rows:
                if row['utility']==page['utility']:
                    self.assertTrue(set(row['clauses']) <= headings)
                    self.assertNotIn('gap',row)

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
                         stdout=b'actual\n',stderr=b'',status=0,files={'result':b'actual'})
            for change in ({},{'stdout':b'wrong\n'},{'status':1},{'files':{'result':b'wrong'}},
                           {'nonempty_files':['missing']},{'stderr':b'wrong'}):
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
                if proc.exists():
                    self.assertEqual(proc.read_text().rsplit(')', 1)[1].split()[0], 'Z')
                else:
                    with self.assertRaises(ProcessLookupError):
                        os.kill(pid, 0)
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


if __name__=='__main__':
    unittest.main()
