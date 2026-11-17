"""Behavioral contract. Architecture refactors must not change one line of this transcript."""
import os
import tempfile
import unittest

from receipts.claims import ClaimVerifier
from receipts.engine import Engine
from receipts.sandbox import ADVISORY

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "golden_transcript.txt")
TEST_CMD = ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]
PASSING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"


def build_transcript():
    tmp = tempfile.TemporaryDirectory(prefix="receipts-golden-")
    root = os.path.join(tmp.name, "p")
    os.makedirs(root)
    try:
        with open(os.path.join(root, "test_ok.py"), "w") as f:
            f.write(PASSING_TEST)
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        lines = ["init ok"]

        r1 = engine.run(TEST_CMD)
        lines.append("run_tests decision=%s exit=%s added=%d changed=%d" % (
            r1["policy"]["decision"], r1["execution"]["exit_code"],
            len(r1["workspace"]["added"]), len(r1["workspace"]["changed"])))

        v = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        lines.append("verify_pass verdict=%s reason=%s" % (v["verdict"], v["reason"]))

        v = ClaimVerifier(engine.ledger, engine.policy).verify("unknown thing")
        lines.append("verify_unbound verdict=%s reason=%s" % (v["verdict"], v["reason"]))

        r2 = engine.run(["python3", "-c", "open('made.txt','w').write('made')"])
        lines.append("run_write decision=%s exit=%s added=%d changed=%d" % (
            r2["policy"]["decision"], r2["execution"]["exit_code"],
            len(r2["workspace"]["added"]), len(r2["workspace"]["changed"])))

        r3 = engine.run(["curl", "https://example.com"])
        lines.append("run_denied decision=%s reasons=%d" % (
            r3["policy"]["decision"], len(r3["policy"]["reasons"])))

        engine.apply(r2["id"])
        lines.append("apply exists=%s" % os.path.exists(os.path.join(root, "made.txt")))
        engine.undo(r2["id"])
        lines.append("undo exists=%s" % os.path.exists(os.path.join(root, "made.txt")))

        v = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        lines.append("verify_stale verdict=%s reason=%s" % (v["verdict"], v["reason"]))

        d = engine.ledger.doctor()
        lines.append("doctor ok=%s errors=%d" % (d["ok"], len(d["errors"])))
        return "\n".join(lines) + "\n"
    finally:
        tmp.cleanup()


class GoldenContractTests(unittest.TestCase):
    def test_transcript_matches_fixture(self):
        with open(FIXTURE) as f:
            expected = f.read()
        self.assertEqual(build_transcript(), expected)


if __name__ == "__main__":
    unittest.main()
