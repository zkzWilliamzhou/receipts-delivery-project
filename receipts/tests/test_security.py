import os
import stat
import unittest

from receipts.claims import ClaimVerifier
from receipts.redact import contains_secret, redact
from receipts.sandbox import ADVISORY
from receipts.engine import Engine
from tests.base import ReceiptTestCase


class SecurityTests(ReceiptTestCase):
    def test_key_and_ledger_are_private(self):
        self.engine.run(["python3", "-c", "pass"])
        base = os.path.join(self.root, ".receipts")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(base, "key")).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(base, "ledger.jsonl")).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(base).st_mode), 0o700)

    def test_secret_patterns_are_redacted(self):
        samples = [
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "sk-abcdefghijklmnopqrstuvwxyz0123456789",
            "-----BEGIN PRIVATE KEY-----",
            "password=hunter2",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9",
        ]
        for s in samples:
            with self.subTest(s=s[:12]):
                self.assertTrue(contains_secret(s))
                self.assertNotIn(s, redact(s))
                self.assertIn("REDACTED", redact(s))

    def test_plain_text_is_not_over_redacted(self):
        self.assertEqual(redact("all tests passed"), "all tests passed")

    def test_env_not_leaked_into_receipt(self):
        os.environ["RECEIPTS_AWS_SECRET"] = "leak-me"
        try:
            r = self.engine.run(["python3", "-c", "pass"])
        finally:
            os.environ.pop("RECEIPTS_AWS_SECRET", None)
        self.assertNotIn("RECEIPTS_AWS_SECRET", r["action"]["env"])
        self.assertNotIn("leak-me", str(r))

    def test_no_pass_without_admissible_receipt(self):
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED")

    def test_denied_action_cannot_produce_pass(self):
        Engine(self.root, backend=ADVISORY).run(["curl", "https://example.com"])
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify("tests pass")
        self.assertNotEqual(v["verdict"], "PASS")

    def test_shell_false_prevents_command_substitution(self):
        marker = os.path.join(self.tmp.name, "pwned")
        r = self.engine.run(["echo", "$(touch %s)" % marker])
        self.assertFalse(os.path.exists(marker))
        self.assertIn("$(touch", r["execution"]["stdout"])

    def test_symlink_escape_does_not_write_outside_root(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.root, "sub"))
        store = self.store()
        sha = store.put_bytes(b"escaped")
        from receipts.workspace import Workspace
        ws = Workspace(self.root, store)
        state = {"sub/escape.txt": {"kind": "file", "sha": sha, "mode": 0o644, "size": 7}}
        with self.assertRaises(ValueError):
            ws.materialize(self.root, state)
        self.assertFalse(os.path.exists(os.path.join(outside, "escape.txt")))

    def test_object_sha_traversal_is_rejected(self):
        store = self.store()
        with self.assertRaises(ValueError):
            store.get("../../../etc/passwd")

    def test_receipt_does_not_store_unredacted_private_key_marker(self):
        r = self.engine.run(["python3", "-c", "print('-----BEGIN PRIVATE KEY-----')"])
        self.assertNotIn("BEGIN PRIVATE KEY", r["execution"]["stdout"])

    def test_advisory_backend_never_claims_enforcement(self):
        r = Engine(self.root, backend=ADVISORY).run(["python3", "-c", "pass"])
        self.assertEqual(r["policy"]["backend"], "advisory")
        self.assertNotIn("enforced", str(r["policy"]).lower())
        self.assertFalse(r["policy"]["capabilities"]["network_isolation"])
        self.assertFalse(r["policy"]["capabilities"]["filesystem_containment"])

    def test_timeout_does_not_record_success(self):
        self.set_policy(max_wall_seconds=1)
        r = self.engine.run(["python3", "-c", "import time;time.sleep(10)"])
        self.assertTrue(r["execution"]["timed_out"])
        self.assertIsNone(r["execution"]["exit_code"])
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify("tests pass")
        self.assertNotEqual(v["verdict"], "PASS")

    def test_ledger_line_count_matches_doctor_count(self):
        for _ in range(4):
            self.engine.run(["python3", "-c", "pass"])
        d = self.engine.ledger.doctor()
        self.assertTrue(d["ok"])
        self.assertEqual(d["count"], 4)

    def test_escaping_symlink_is_not_copied_and_blocks_pass(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.root, "escape"))
        self.write("test_ok.py", "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        receipt = self.engine.run(
            ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"])
        self.assertIn("escape", receipt["workspace"]["unsafe_symlinks"])
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED")
        self.assertEqual(v["reason"], "unsafe_symlink")
        self.engine.run(["python3", "-c", "open('escape/pwned.txt','w').write('x')"])
        self.assertFalse(os.path.exists(os.path.join(outside, "pwned.txt")))

    def test_protected_file_content_never_enters_object_store(self):
        self.engine.run(["python3", "-c", "open('.env','w').write('SUPER_SECRET_VALUE_123')"])
        objects = os.path.join(self.root, ".receipts", "objects")
        for current, _, files in os.walk(objects):
            for name in files:
                with open(os.path.join(current, name), "rb") as f:
                    self.assertNotIn(b"SUPER_SECRET_VALUE_123", f.read())


if __name__ == "__main__":
    unittest.main()
