"""Check that Pipeline receives failed evidence when application suites fail."""

from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import container_report


class ContainerReportTests(unittest.TestCase):
    def run_report(self, source):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        helper = directory / "command.py"
        helper.write_text(source)
        output = directory / "reports"
        output.mkdir()
        (output / "junit.xml").write_text("stale passing report")
        status = container_report.run_suites(
            output, ("first", "second"), (sys.executable, str(helper)))
        return status, output, ET.parse(output / "junit.xml").getroot()

    def test_passes_have_real_cases_and_logs(self):
        status, output, root = self.run_report("print('an assertion ran')\n")
        self.assertEqual(status, 0)
        self.assertEqual(root.attrib["tests"], "2")
        self.assertEqual(root.attrib["failures"], "0")
        self.assertEqual(len(root.findall("testcase")), 2)
        self.assertIn("an assertion ran", (output / "first.log").read_text())

    def test_failure_stops_and_replaces_stale_success(self):
        status, output, root = self.run_report("print('actual failure'); exit(23)\n")
        self.assertEqual(status, 1)
        self.assertEqual(root.attrib["tests"], "1")
        self.assertEqual(root.attrib["failures"], "1")
        self.assertIn("23", root.find("testcase/failure").attrib["message"])
        self.assertIn("actual failure", (output / "first.log").read_text())
        self.assertFalse((output / "second.log").exists())

    def test_missing_command_fails_and_writes_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.assertEqual(container_report.run_suites(
                output, ("first",), (str(output / "nonexistent"),)), 1)
            root = ET.parse(output / "junit.xml").getroot()
            self.assertEqual(root.attrib["failures"], "1")
            self.assertIn("could not run", (output / "first.log").read_text())


if __name__ == "__main__":
    unittest.main()
