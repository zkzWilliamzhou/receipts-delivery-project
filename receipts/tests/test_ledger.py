import json
import os
import stat
import unittest
from concurrent.futures import ThreadPoolExecutor

from receipts.ledger import Ledger
from tests.base import ReceiptTestCase


class LedgerTests(ReceiptTestCase):
    def ledger(self):
        return Ledger(os.path.join(self.root, ".receipts"))

    def body(self, marker="a"):
        return {"schema": 1, "marker": marker, "action": {"argv": ["echo", marker]}}

    def test_append_assigns_seq_id_prev(self):
        led = self.ledger()
        a = led.append(self.body("a"))
        b = led.append(self.body("b"))
        self.assertEqual(a["seq"], 1)
        self.assertEqual(b["seq"], 2)
        self.assertEqual(a["id"], "r0000001")
        self.assertEqual(b["prev"], a["hash"])
        self.assertEqual(a["prev"], "0" * 64)
        self.assertEqual(len(a["mac"]), 64)

    def test_doctor_ok_on_clean_chain(self):
        led = self.ledger()
        led.append(self.body("a"))
        led.append(self.body("b"))
        out = led.doctor()
        self.assertTrue(out["ok"], out["errors"])
        self.assertEqual(out["count"], 2)

    def test_doctor_detects_tampered_body(self):
        led = self.ledger()
        led.append(self.body("a"))
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        line = open(path).readline().replace('"a"', '"z"')
        with open(path, "w") as f:
            f.write(line)
        out = led.doctor()
        self.assertFalse(out["ok"])
        self.assertTrue(any("mac" in e or "hash" in e for e in out["errors"]))

    def test_doctor_detects_broken_mac(self):
        led = self.ledger()
        led.append(self.body("a"))
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        obj = json.loads(open(path).readline())
        obj["mac"] = "0" * 64
        with open(path, "w") as f:
            f.write(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")
        self.assertFalse(led.doctor()["ok"])

    def test_doctor_detects_deleted_middle_line(self):
        led = self.ledger()
        led.append(self.body("a"))
        led.append(self.body("b"))
        led.append(self.body("c"))
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        lines = open(path).readlines()
        with open(path, "w") as f:
            f.writelines([lines[0], lines[2]])
        self.assertFalse(led.doctor()["ok"])

    def test_doctor_detects_truncation_via_head(self):
        led = self.ledger()
        led.append(self.body("a"))
        led.append(self.body("b"))
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        with open(path) as f:
            first_line = f.readlines()[0]
        with open(path, "w") as f:
            f.write(first_line)
        self.assertFalse(led.doctor()["ok"])

    def test_head_matches_last_hash(self):
        led = self.ledger()
        a = led.append(self.body("a"))
        self.assertEqual(led.head(), a["hash"])

    def test_key_file_is_private(self):
        self.ledger()
        key = os.path.join(self.root, ".receipts", "key")
        self.assertEqual(stat.S_IMODE(os.stat(key).st_mode), 0o600)

    def test_ledger_file_is_private(self):
        self.ledger().append(self.body())
        p = os.path.join(self.root, ".receipts", "ledger.jsonl")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)

    def test_all_returns_receipts_in_order(self):
        led = self.ledger()
        led.append(self.body("a"))
        led.append(self.body("b"))
        self.assertEqual([r["marker"] for r in led.all()], ["a", "b"])

    def test_concurrent_appends_are_unique_and_chain_intact(self):
        led = self.ledger()
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(lambda i: led.append(self.body(str(i))), range(24)))
        seqs = [r["seq"] for r in led.all()]
        self.assertEqual(sorted(seqs), list(range(1, 25)))
        self.assertTrue(led.doctor()["ok"])

    def test_append_rejects_unknown_schema(self):
        led = self.ledger()
        with self.assertRaises(ValueError):
            led.append({"schema": 999, "marker": "x"})

    def test_append_refuses_corrupt_ledger(self):
        led = self.ledger()
        led.append(self.body())
        path = os.path.join(self.root, ".receipts", "ledger.jsonl")
        with open(path, "a") as f:
            f.write("{}\n")
        with self.assertRaises(ValueError) as ctx:
            led.append(self.body("b"))
        self.assertIn("corrupt", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
