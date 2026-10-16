"""Exercise platform-neutral Swift approval matcher and watch semantics."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SWIFT = ROOT / "skills" / "codex-dingtalk-ping" / "scripts" / "approval_probe.swift"
RUNNER = SWIFT.with_name("run-approval-probe.sh")


class ApprovalProbeTests(unittest.TestCase):
    def test_source_exists_and_does_not_modify_codex(self):
        source = SWIFT.read_text(encoding="utf-8")
        self.assertIn('com.openai.codex', source)
        self.assertIn('AXIsProcessTrusted()', source)
        self.assertIn('approval_pending_5s', source)
        self.assertNotIn('send_text(', source)
        self.assertNotIn('AXUIElementPerformAction', source)
        self.assertTrue(RUNNER.exists())
        self.assertIn('run-approval-probe.sh', (ROOT / 'README.md').read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which("swiftc"), "Swift compiler unavailable")
    def test_native_matcher_and_timer_selftest(self):
        with tempfile.TemporaryDirectory() as td:
            binary = pathlib.Path(td) / "approval-probe"
            compiled = subprocess.run(["swiftc", str(SWIFT), "-o", str(binary)],
                                      capture_output=True, text=True, timeout=90)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            test = subprocess.run([str(binary), "--self-test"], capture_output=True, text=True, timeout=15)
            self.assertEqual(test.returncode, 0, test.stderr)
            self.assertIn("PASS: approval matching", test.stdout)


if __name__ == "__main__":
    unittest.main()
