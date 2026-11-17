import contextlib
import io
import json
import os
import unittest

from receipts.cli import main
from tests.base import ReceiptTestCase, make_project

TEST_CMD = ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]
PASSING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"


class CliTests(ReceiptTestCase):
    def setUp(self):
        super().setUp()
        self.cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.cwd)
        super().tearDown()

    def call(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_cli_init_creates_store(self):
        tmp, root = make_project()
        try:
            os.chdir(root)
            code, out = self.call("init")
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isdir(os.path.join(root, ".receipts")))
        finally:
            os.chdir(self.root)
            tmp.cleanup()

    def test_cli_run_then_verify_pass_exit_zero(self):
        self.write("test_ok.py", PASSING_TEST)
        code, _ = self.call("run", "--", *TEST_CMD)
        self.assertEqual(code, 0)
        code, out = self.call("verify", "tests pass")
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_cli_verify_unverified_exit_two(self):
        code, out = self.call("verify", "tests pass")
        self.assertEqual(code, 2)
        self.assertIn("UNVERIFIED", out)

    def test_cli_verify_fail_exit_one(self):
        self.write("test_bad.py", "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.assertTrue(False)\n")
        self.call("run", "--", *TEST_CMD)
        code, out = self.call("verify", "tests pass")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_cli_verify_json(self):
        code, out = self.call("verify", "tests pass", "--json")
        self.assertEqual(code, 2)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "UNVERIFIED")

    def test_cli_doctor_exit_code(self):
        self.assertEqual(self.call("doctor")[0], 0)
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        with open(path, "a") as f:
            f.write("{}\n")
        self.assertEqual(self.call("doctor")[0], 1)

    def test_cli_demo_prints_three_outcomes(self):
        code, out = self.call("demo")
        self.assertEqual(code, 0)
        for word in ("PASS", "DENY", "UNVERIFIED"):
            self.assertIn(word, out)

    def test_cli_unknown_command_returns_two(self):
        code, out = self.call("frobnicate")
        self.assertEqual(code, 2)
        self.assertIn("usage", out.lower())

    def test_cli_run_requires_double_dash(self):
        code, out = self.call("run", "echo", "hi")
        self.assertEqual(code, 2)
        self.assertIn("--", out)

    def test_cli_run_requires_command_after_double_dash(self):
        self.assertEqual(self.call("run", "--")[0], 2)

    def test_cli_log_and_show(self):
        self.call("run", "--", "python3", "-c", "print('ok')")
        code, out = self.call("log")
        self.assertEqual(code, 0)
        self.assertIn("r0000001", out)
        self.assertEqual(self.call("show", "r0000001")[0], 0)

    def test_cli_apply_undo(self):
        r = self.engine.run(["python3", "-c", "open('made.txt','w').write('x')"])
        self.assertEqual(self.call("apply", r["id"])[0], 0)
        self.assertTrue(self.exists("made.txt"))
        self.assertEqual(self.call("undo", r["id"])[0], 0)
        self.assertFalse(self.exists("made.txt"))

    def test_cli_diff_and_replay(self):
        r = self.engine.run(["python3", "-c", "open('made.txt','w').write('x')"])
        self.assertEqual(self.call("diff", r["id"])[0], 0)
        self.assertEqual(self.call("replay", r["id"])[0], 0)

    def test_cli_policy_show(self):
        code, out = self.call("policy", "show")
        self.assertEqual(code, 0)
        self.assertIn("deny", out)

    def test_cli_verify_empty_claim_is_rejected(self):
        code, out = self.call("verify", "")
        self.assertEqual(code, 2)
        self.assertIn("non-empty claim", out)

    def test_cli_verify_strict_json(self):
        self.write("test_ok.py", PASSING_TEST)
        self.call("run", "--", *TEST_CMD)
        code, out = self.call("verify", "tests pass", "--strict", "--json")
        obj = json.loads(out)
        self.assertIn(obj["verdict"], ("PASS", "UNVERIFIED"))
        self.assertIn("warnings", obj)

    def test_cli_log_invalid_limit_is_handled(self):
        code, out = self.call("log", "--limit", "abc")
        self.assertEqual(code, 2)
        self.assertIn("--limit requires an integer", out)

    def test_cli_help_exits_zero(self):
        self.assertEqual(self.call("--help")[0], 0)

    def test_cli_doctor_missing_ledger_exits_one(self):
        tmp, root = make_project()
        try:
            os.chdir(root)
            code, out = self.call("doctor")
            self.assertEqual(code, 1)
            self.assertIn("no ledger found", out)
        finally:
            os.chdir(self.root)
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
