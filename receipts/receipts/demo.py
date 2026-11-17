"""Offline, reproducible demo. No model, no key, no network."""
import os
import shutil
import tempfile

from .claims import ClaimVerifier
from .engine import Engine
from .sandbox import ADVISORY

DEMO_TEST = """import unittest


class DemoTests(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(1 + 1, 2)

    def test_string(self):
        self.assertEqual("a" + "b", "ab")
"""

TEST_CMD = ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]


def run_demo():
    tmp = tempfile.mkdtemp(prefix="receipts-demo-")
    project = os.path.join(tmp, "project")
    os.makedirs(project)
    with open(os.path.join(project, "test_demo.py"), "w", encoding="utf-8") as f:
        f.write(DEMO_TEST)
    lines = ["receipts demo (offline, no API key, no network)", ""]
    try:
        engine = Engine(project, backend=ADVISORY)
        engine.init()

        receipt = engine.run(TEST_CMD)
        lines.append("ACT 1  agent runs a test suite")
        lines.append("       receipt %s  exit=%s  decision=%s" % (
            receipt["id"], receipt["execution"]["exit_code"], receipt["policy"]["decision"]))
        verdict = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        lines.append("       verify 'tests pass' -> %s (%s)" % (
            verdict["verdict"], verdict["reason"]))

        denied = engine.run(["curl", "https://example.com"])
        lines.append("ACT 2  agent tries a network command")
        lines.append("       receipt %s  decision=%s  reason=%s" % (
            denied["id"], denied["policy"]["decision"],
            "; ".join(denied["policy"]["reasons"])))
        lines.append("       policy verdict: DENY (command did not run)")
        lines.append("       backend=%s (advisory, not enforced)" % denied["policy"]["backend"])

        engine.run(["python3", "-c", "open('edited.py','w').write('changed')"])
        stale = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        lines.append("ACT 3  someone edits a file, then repeats the claim")
        lines.append("       verify 'tests pass' -> %s (%s)" % (
            stale["verdict"], stale["reason"]))

        health = engine.ledger.doctor()
        lines.append("")
        lines.append("ledger doctor: ok=%s receipts=%d errors=%d" % (
            health["ok"], health["count"], len(health["errors"])))
        return "\n".join(lines)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
