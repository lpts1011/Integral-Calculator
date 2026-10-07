import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import Integral_Calculator


class RuntimeCliTests(unittest.TestCase):
    def test_failed_runtime_check_writes_report_and_exits_without_a_gui_error(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'failure.json'
            arguments = ['calculator', '--self-test', '--self-test-output', str(report)]
            with patch('sys.argv', arguments), patch('runtime_self_test.run', side_effect=ImportError('incompatible native dependency')), contextlib.redirect_stderr(io.StringIO()):
                code = Integral_Calculator.main()
            self.assertEqual(code, 1)
            result = json.loads(report.read_text())
            self.assertFalse(result['passed'])
            self.assertIn('incompatible native dependency', result['error'])
