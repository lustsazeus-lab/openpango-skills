import base64
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    here = Path(__file__).resolve().parent
    module_path = here / "sandbox.py"
    spec = importlib.util.spec_from_file_location("data_analysis_sandbox", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestDataAnalysisSandbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_csv_input_and_stdout(self):
        sandbox = self.mod.DataAnalysisSandbox()
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "sales.csv"
            csv_path.write_text("amount\n10\n15\n5\n", encoding="utf-8")

            script = """
import csv, os
p = os.path.join(INPUT_DIR, 'sales.csv')
with open(p, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    total = sum(int(r['amount']) for r in reader)
print(total)
"""
            result = sandbox.execute(script, input_files=[str(csv_path)])
            self.assertEqual(result["status"], "success")
            self.assertIn("30", result["stdout"])

    def test_network_blocked(self):
        sandbox = self.mod.DataAnalysisSandbox()
        script = """
import socket
try:
    socket.socket()
except Exception as e:
    print(type(e).__name__)
"""
        result = sandbox.execute(script)
        self.assertEqual(result["status"], "success")
        self.assertIn("PermissionError", result["stdout"])

    def test_write_outside_sandbox_blocked(self):
        sandbox = self.mod.DataAnalysisSandbox()
        script = """
try:
    with open('/tmp/openpango_escape.txt', 'w', encoding='utf-8') as f:
        f.write('nope')
except Exception as e:
    print(type(e).__name__)
"""
        result = sandbox.execute(script)
        self.assertEqual(result["status"], "success")
        self.assertIn("PermissionError", result["stdout"])

    def test_chart_base64_return(self):
        sandbox = self.mod.DataAnalysisSandbox()
        script = """
import base64, os
# tiny valid 1x1 PNG
png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7+v8QAAAAASUVORK5CYII='
with open(os.path.join(OUTPUT_DIR, 'chart.png'), 'wb') as f:
    f.write(base64.b64decode(png_b64))
print('ok')
"""
        result = sandbox.execute(script)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["charts"])
        payload = base64.b64decode(result["charts"][0]["base64"])
        self.assertTrue(payload.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
