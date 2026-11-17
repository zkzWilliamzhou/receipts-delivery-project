import os
import unittest

from receipts.claims import ClaimVerifier
from receipts.engine import Engine
from receipts.sandbox import ADVISORY
from tests.base import ReceiptTestCase

TEST_CMD = ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]
PASSING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"
FAILING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.assertTrue(False)\n"


class ClaimTests(ReceiptTestCase):
    def verifier(self, engine=None):
        engine = engine or self.engine
        return ClaimVerifier(engine.ledger, engine.policy)

    def test_no_evidence_returns_unverified(self):
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED")
        self.assertEqual(v["reason"], "no_evidence")
        self.assertIsNone(v["receipt"])

    def test_unbound_claim_returns_unverified(self):
        v = self.verifier().verify("I painted the moon")
        self.assertEqual(v["verdict"], "UNVERIFIED")
        self.assertEqual(v["reason"], "unbound_claim")

    def test_valid_test_receipt_returns_pass(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        v = self.verifier().verify("Tests pass.")
        self.assertEqual(v["verdict"], "PASS", v)
        self.assertEqual(v["reason"], "admissible_receipt")
        self.assertIsNotNone(v["receipt"])
        self.assertTrue(v["checks"])

    def test_failed_test_receipt_returns_fail(self):
        self.write("test_bad.py", FAILING_TEST)
        self.engine.run(TEST_CMD)
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "FAIL", v)
        self.assertEqual(v["reason"], "conflicting_evidence")

    def test_stale_evidence_returns_unverified(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        self.engine.run(["python3", "-c", "open('stale.txt','w').write('x')"])
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED", v)
        self.assertEqual(v["reason"], "stale_evidence")

    def test_denied_receipt_with_no_workspace_change_does_not_stale(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        self.advisory().run(["curl", "https://example.com"])
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "PASS", v)

    def test_latest_matching_receipt_wins(self):
        self.write("test_bad.py", FAILING_TEST)
        self.engine.run(TEST_CMD)
        os.remove(os.path.join(self.root, "test_bad.py"))
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        self.assertEqual(self.verifier().verify("tests pass")["verdict"], "PASS")

    def test_corrupt_ledger_returns_unverified(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        with open(path, "a") as f:
            f.write("{}\n")
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED")
        self.assertEqual(v["reason"], "ledger_corrupt")

    def test_denied_receipt_cannot_produce_pass(self):
        self.advisory().run(["curl", "https://example.com"])
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED")
        self.assertEqual(v["reason"], "no_evidence")

    def test_network_claim_unverifiable_in_advisory_mode(self):
        self.advisory().run(["python3", "-c", "pass"])
        v = self.verifier().verify("no network access")
        self.assertEqual(v["verdict"], "UNVERIFIED", v)
        self.assertEqual(v["reason"], "network_unverifiable")

    def test_output_truncation_blocks_pass(self):
        self.write("test_ok.py", PASSING_TEST)
        self.set_policy(max_output_bytes=8)
        self.engine.run(TEST_CMD)
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED", v)
        self.assertEqual(v["reason"], "output_truncated")

    def test_protected_violation_blocks_pass(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        bad = self.engine.run(["python3", "-c", "open('.env','w').write('X')"])
        v = self.verifier().verify("tests pass")
        self.assertNotEqual(v["verdict"], "PASS")
        self.assertIn(".env", bad["workspace"]["protected_violations"])

    def test_verify_json_shape(self):
        v = self.verifier().verify("tests pass")
        for key in ("verdict", "reason", "receipt", "checks", "claim"):
            self.assertIn(key, v)
        self.assertIsInstance(v["checks"], list)

    def test_pass_never_without_a_receipt(self):
        for claim in ("tests pass", "build succeeded", "lint clean", "no network access"):
            with self.subTest(claim=claim):
                self.assertNotEqual(self.verifier().verify(claim)["verdict"], "PASS")

    def test_claim_normalization_is_case_insensitive(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        self.assertEqual(self.verifier().verify("  TESTS PASS!! ")["verdict"], "PASS")

    def test_policy_changed_after_receipt_invalidates_pass(self):
        self.write("test_ok.py", PASSING_TEST)
        self.engine.run(TEST_CMD)
        self.set_policy(max_wall_seconds=3)
        v = self.verifier().verify("tests pass")
        self.assertEqual(v["verdict"], "UNVERIFIED", v)
        self.assertEqual(v["reason"], "policy_changed")

    def test_strict_mode_blocks_pass_on_advisory_backend(self):
        self.write("test_ok.py", PASSING_TEST)
        r = Engine(self.root, backend=ADVISORY).run(TEST_CMD)
        self.assertFalse(r["policy"]["capabilities"]["filesystem_containment"])
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify(
            "tests pass", strict=True)
        self.assertEqual(v["verdict"], "UNVERIFIED", v)
        self.assertEqual(v["reason"], "uncontained_execution")

    def test_pass_on_advisory_carries_containment_warning(self):
        self.write("test_ok.py", PASSING_TEST)
        Engine(self.root, backend=ADVISORY).run(TEST_CMD)
        v = ClaimVerifier(self.engine.ledger, self.engine.policy).verify("tests pass")
        self.assertEqual(v["verdict"], "PASS")
        self.assertTrue(any("absolute writes" in w for w in v["warnings"]))

    def advisory(self):
        return Engine(self.root, backend=ADVISORY)


if __name__ == "__main__":
    unittest.main()
