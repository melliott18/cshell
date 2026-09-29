"""Negative controls for CSH-073 qualification and owned-process cleanup."""
import copy
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest

from host_text import run_case, stream_matches
from host_text_cases import UTILITIES, case, cases, crc
from host_text_boundaries import signal_case


class TextEvidenceTests(unittest.TestCase):
    def test_crc_independent_known_answers(self):
        self.assertEqual(crc(b''), 4294967295)
        self.assertEqual(crc(b'123456789'), 930766865)

    def test_every_provider_has_positive_and_error_evidence(self):
        rows=list(cases('en_US.UTF-8', True))
        self.assertEqual(len({r['id'] for r in rows}),len(rows))
        self.assertEqual({r['utility'] for r in rows},set(UTILITIES))
        for tool in UTILITIES:
            self.assertTrue(any(r['utility']==tool and r['status']==0 for r in rows))
        self.assertFalse(any('gap' in r for r in rows))

    def test_numeric_padding_cannot_hide_changed_counts_or_output(self):
        row=next(r for r in cases() if r['id']=='wc/counts')
        self.assertTrue(stream_matches(row,'stdout',b'  1  3 13\n'))
        for bad in (b'1 4 13\n',b'1 3 13\nextra',b'1 3 13',b'1\n3 13\n'):
            self.assertFalse(stream_matches(row,'stdout',bad))
        od=next(r for r in cases() if r['id']=='od/skip-count')
        self.assertTrue(stream_matches(od,'stdout',b' 3 4 5 6\n'))
        for bad in (b'3 4 5 7\n',b'3 4 5 6 rubbish\n',b'3 4 5 6 7\n'):
            self.assertFalse(stream_matches(od,'stdout',bad))

    def test_effect_failure_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as root:
            tool=Path(root)/'fake'
            tool.write_text('#!/bin/sh\nexit 0\n')
            tool.chmod(0o700)
            row=run_case(Path('/bin/sh'),os.defpath,{'split':{'path':str(tool)}},
                         case('split','effect',files={'xaa':b'expected'}),'direct',Path(root))
            self.assertEqual(row['verdict'],'FAIL')
            self.assertTrue(row['fixture_removed'])

    def test_signal_cleanup_and_inherited_ignore(self):
        old=signal.signal(signal.SIGINT,signal.SIG_IGN)
        try:
            with tempfile.TemporaryDirectory() as root:
                # A selected fake provider that exits before opening the FIFO
                # must fail rendezvous and still be reaped, never PASS.
                row=signal_case(Path('/bin/sh'),os.defpath,'/usr/bin/true',
                                'cat','read-termination','direct',Path(root))
                self.assertEqual(row['verdict'],'FAIL')
                self.assertTrue(row['leader_reaped'])
                self.assertTrue(row['fixture_removed'])
                from host_text_boundaries import launch, finish
                import subprocess
                child=launch(Path('/bin/sh'),os.defpath,sys.executable,
                    ['-c','import signal; print(signal.getsignal(signal.SIGINT) != signal.SIG_IGN)'],
                    'direct',Path(root),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE)
                try:
                    out,err=child.communicate(timeout=2)
                    self.assertEqual((out,err,child.returncode),(b'True\n',b'',0))
                finally:
                    self.assertTrue(finish(child))
        finally:
            signal.signal(signal.SIGINT,old)

    def test_boundary_capture_has_a_byte_limit(self):
        import subprocess
        import time
        from host_text_boundaries import collect, launch, finish
        with tempfile.TemporaryDirectory() as root:
            child=launch(Path('/bin/sh'),os.defpath,sys.executable,
                ['-c','import os; os.write(2, b"x" * 100000)'],
                'direct',Path(root),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE)
            try:
                with self.assertRaisesRegex(RuntimeError,'65536'):
                    collect(child,time.monotonic()+2)
            finally:
                self.assertTrue(finish(child))

    def test_timeout_kills_and_reaps_owned_provider(self):
        with tempfile.TemporaryDirectory() as root:
            # exec preserves the owned PID; no grandchild or unrelated process.
            tool=Path(root)/'stalled'
            tool.write_text('#!/bin/sh\nexec '+sys.executable+" -c 'import time; time.sleep(30)'\n")
            tool.chmod(0o700)
            row=signal_case(Path('/bin/sh'),os.defpath,str(tool),
                            'cat','read-termination','direct',Path(root))
            self.assertEqual(row['verdict'],'FAIL')
            self.assertIn('never opened',row['error'])
            self.assertTrue(row['leader_reaped'])
            self.assertTrue(row['fixture_removed'])

    def test_contract_map_rejects_missing_sections_and_dangling_cases(self):
        from host_text_contracts import load, validate
        data=load()
        self.assertEqual(validate(data),[])
        missing=copy.deepcopy(data)
        del missing['utilities'][0]['sections']['OPTIONS']
        self.assertTrue(any('sections' in error for error in validate(missing)))
        dangling=copy.deepcopy(data)
        dangling['utilities'][0]['cases'].append('cat/invented')
        self.assertTrue(any('unknown case' in error for error in validate(dangling)))


if __name__=='__main__':
    unittest.main()
