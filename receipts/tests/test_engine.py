import os
import unittest

from receipts.engine import Engine
from receipts.sandbox import ADVISORY
from tests.base import ReceiptTestCase


class EngineTests(ReceiptTestCase):
    def advisory(self):
        return Engine(self.root, backend=ADVISORY)

    def test_init_creates_policy_and_store(self):
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".receipts")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".receipts", "policy.json")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".receipts", "objects")))

    def test_init_is_idempotent(self):
        self.engine.init()
        self.engine.init()
        self.assertEqual(self.engine.ledger.all(), [])

    def test_run_creates_receipt_with_required_fields(self):
        r = self.engine.run(["python3", "-c", "print('ok')"])
        for key in ("schema", "seq", "id", "prev", "hash", "mac", "action", "policy",
                    "execution", "workspace", "objects", "integrity"):
            self.assertIn(key, r)
        self.assertEqual(r["schema"], 1)
        self.assertFalse(r["action"]["shell"])

    def test_run_executes_in_cow_workspace_not_real_tree(self):
        r = self.engine.run(["python3", "-c", "open('made.txt','w').write('x')"])
        self.assertFalse(self.exists("made.txt"))
        self.assertIn("made.txt", r["workspace"]["after"])
        self.assertIn("made.txt", r["workspace"]["added"])

    def test_run_records_exit_code_and_output(self):
        r = self.engine.run(["python3", "-c", "import sys;print('hi');sys.stderr.write('err')"])
        self.assertEqual(r["execution"]["exit_code"], 0)
        self.assertIn("hi", r["execution"]["stdout"])
        self.assertIn("err", r["execution"]["stderr"])
        self.assertEqual(len(r["execution"]["stdout_sha256"]), 64)

    def test_run_records_nonzero_exit(self):
        r = self.engine.run(["python3", "-c", "import sys;sys.exit(3)"])
        self.assertEqual(r["execution"]["exit_code"], 3)

    def test_run_denied_command_does_not_execute(self):
        r = self.advisory().run(["curl", "https://example.com"])
        self.assertEqual(r["policy"]["decision"], "deny")
        self.assertIsNone(r["execution"]["exit_code"])
        self.assertEqual(r["workspace"]["added"], [])
        self.assertTrue(any("network" in x for x in r["policy"]["reasons"]))

    def test_run_records_backend(self):
        r = self.advisory().run(["python3", "-c", "pass"])
        self.assertEqual(r["policy"]["backend"], ADVISORY)

    def test_run_redacts_secret_in_stdout(self):
        r = self.engine.run(["python3", "-c", "print('AKIAIOSFODNN7EXAMPLE')"])
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", r["execution"]["stdout"])
        self.assertIn("REDACTED", r["execution"]["stdout"])

    def test_run_caps_output(self):
        self.set_policy(max_output_bytes=32)
        r = self.engine.run(["python3", "-c", "print('x'*1000)"])
        self.assertTrue(r["execution"]["truncated"])
        self.assertLessEqual(len(r["execution"]["stdout"]), 32)
        self.assertGreater(r["execution"]["stdout_bytes"], 900)

    def test_run_timeout_kills_process_group(self):
        self.set_policy(max_wall_seconds=1)
        r = self.engine.run(["python3", "-c", "import time;time.sleep(10)"])
        self.assertTrue(r["execution"]["timed_out"])
        self.assertLess(r["wall_ms"], 6000)
        self.assertIsNone(r["execution"]["exit_code"])

    def test_run_does_not_store_full_environment(self):
        os.environ["RECEIPTS_TEST_SECRET"] = "do-not-store"
        try:
            r = self.engine.run(["python3", "-c", "pass"])
        finally:
            os.environ.pop("RECEIPTS_TEST_SECRET", None)
        self.assertNotIn("RECEIPTS_TEST_SECRET", r["action"]["env"])

    def test_run_records_protected_path_violation(self):
        r = self.engine.run(["python3", "-c", "open('.env','w').write('SECRET=1')"])
        self.assertIn(".env", r["workspace"]["protected_violations"])

    def test_run_rejects_empty_argv(self):
        with self.assertRaises(ValueError):
            self.engine.run([])

    def test_run_tag_is_recorded(self):
        r = self.engine.run(["python3", "-c", "pass"], tag="unit")
        self.assertEqual(r["action"]["tag"], "unit")

    def test_apply_then_undo_restores_tree_byte_for_byte(self):
        self.write("a.txt", "alpha")
        self.write("b.txt", "beta")
        r = self.engine.run([
            "python3", "-c",
            "open('a.txt','w').write('changed');open('c.txt','w').write('new');"
            "import os;os.remove('b.txt')",
        ])
        self.assertEqual(self.read("a.txt"), b"alpha")
        self.engine.apply(r["id"])
        self.assertEqual(self.read("a.txt"), b"changed")
        self.assertEqual(self.read("c.txt"), b"new")
        self.assertFalse(self.exists("b.txt"))
        self.engine.undo(r["id"])
        self.assertEqual(self.read("a.txt"), b"alpha")
        self.assertEqual(self.read("b.txt"), b"beta")
        self.assertFalse(self.exists("c.txt"))

    def test_apply_refuses_protected_path_violation(self):
        r = self.engine.run(["python3", "-c", "open('.env','w').write('SECRET=1')"])
        with self.assertRaises(ValueError):
            self.engine.apply(r["id"])

    def test_replay_reproduces_exit_and_delta(self):
        r = self.engine.run(["python3", "-c", "open('made.txt','w').write('x')"])
        out = self.engine.replay(r["id"])
        self.assertTrue(out["match"], out["details"])
        self.assertEqual(out["exit_code"], 0)

    def test_find_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.engine.find("r9999999")

    def test_cow_directory_is_cleaned_after_run(self):
        self.engine.run(["python3", "-c", "pass"])
        tmp = os.path.join(self.root, ".receipts", "tmp")
        self.assertEqual(os.listdir(tmp), [])

    def test_many_runs_keep_chain_intact(self):
        for _ in range(6):
            self.engine.run(["python3", "-c", "pass"])
        self.assertTrue(self.engine.ledger.doctor()["ok"])

    def test_run_refuses_corrupt_ledger(self):
        self.engine.run(["python3", "-c", "pass"])
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        with open(path, "a") as f:
            f.write("{}\n")
        with self.assertRaises(ValueError):
            self.engine.run(["python3", "-c", "pass"])

    def test_large_output_is_hashed_without_loading_it_all(self):
        import hashlib
        payload = b"z" * 5000000
        r = self.engine.run(
            ["python3", "-c", "import sys;sys.stdout.buffer.write(b'z'*5000000)"])
        self.assertEqual(r["execution"]["stdout_bytes"], len(payload))
        self.assertEqual(r["execution"]["stdout_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertTrue(r["execution"]["truncated"])
        self.assertLessEqual(len(r["execution"]["stdout"]),
                             self.engine.policy.data["max_output_bytes"])


if __name__ == "__main__":
    unittest.main()
