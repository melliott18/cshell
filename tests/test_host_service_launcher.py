#!/usr/bin/env python3
"""Docker API failures must still attempt removal of the uniquely owned object."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('service_launcher',
    Path(__file__).resolve().parents[1] / 'tools/host-services/run.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_create_response_timeout_still_removes_owned_container(self):
        calls = []
        def query(argv, **kwargs):
            calls.append(argv)
            if argv[1:3] == ['image', 'inspect']:
                return b'[{"Id":"sha256:fixture"}]'
            if argv[1] == 'create':
                self.assertIn('none', argv)
                self.assertNotIn('--volume', argv)
                self.assertNotIn('--privileged', argv)
                raise subprocess.TimeoutExpired(argv, 15)
            if argv[1] == 'ps': return b''
            self.fail(f'unexpected query: {argv}')
        def run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, 'removed\n', '')
        with tempfile.TemporaryDirectory() as directory, \
                patch('sys.argv', ['run.py', '--output', directory]), \
                patch.object(launcher.subprocess, 'check_output', side_effect=query), \
                patch.object(launcher.subprocess, 'run', side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main(), 1)
            result = json.loads((Path(directory) / 'launcher.json').read_text())
        create = next(c for c in calls if c[1] == 'create')
        name = create[create.index('--name') + 1]
        self.assertIn(['docker', 'rm', '-f', name], calls)
        self.assertEqual(create[-1], 'sha256:fixture')
        self.assertEqual(result['cleanup']['status'], 0)
        self.assertTrue(result['failures'])

    def test_missing_engine_records_setup_without_creating_anything(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('sys.argv', ['run.py', '--output', directory]), \
                patch.object(launcher.subprocess, 'check_output', side_effect=FileNotFoundError('docker')), \
                patch.object(launcher.subprocess, 'run') as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main(), 1)
            self.assertTrue(json.loads((Path(directory) / 'launcher.json').read_text())['failures'])
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
