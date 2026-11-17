import os
import unittest

from receipts.models import sha256_text
from receipts.workspace import Workspace
from tests.base import ReceiptTestCase, make_project


class WorkspaceTests(ReceiptTestCase):
    def ws(self, **kw):
        return Workspace(self.root, self.store(), **kw)

    def test_scan_records_files_dirs_and_symlinks(self):
        self.write("a.txt", "alpha")
        os.makedirs(os.path.join(self.root, "sub", "empty"), exist_ok=True)
        os.symlink("a.txt", os.path.join(self.root, "link"))
        state = self.ws().scan()
        self.assertEqual(state["a.txt"]["kind"], "file")
        self.assertEqual(state["a.txt"]["sha"], sha256_text("alpha"))
        self.assertEqual(state["link"]["kind"], "symlink")
        self.assertEqual(state["link"]["target"], "a.txt")
        self.assertEqual(state["sub"]["kind"], "dir")

    def test_scan_excludes_receipts_store(self):
        self.write("a.txt", "alpha")
        state = self.ws().scan()
        self.assertNotIn(".receipts", state)
        self.assertTrue(all(not k.startswith(".receipts/") for k in state))

    def test_scan_caps_large_files(self):
        ws = self.ws(max_file_bytes=16)
        self.write("big.bin", "x" * 100)
        state = ws.scan()
        self.assertNotIn("big.bin", state)
        self.assertIn("big.bin", ws.skipped)

    def test_scan_caps_file_count(self):
        ws = self.ws(max_files=2)
        for i in range(5):
            self.write("f%d.txt" % i, "x")
        state = ws.scan()
        self.assertLessEqual(len([k for k, v in state.items() if v["kind"] == "file"]), 2)
        self.assertTrue(ws.skipped)

    def test_scan_skips_fifo_without_hanging(self):
        os.mkfifo(os.path.join(self.root, "pipe"))
        ws = self.ws()
        state = ws.scan()
        self.assertNotIn("pipe", state)
        self.assertIn("pipe", ws.skipped)

    def test_create_cow_preserves_symlink_and_excludes_store(self):
        self.write("a.txt", "alpha")
        os.symlink("a.txt", os.path.join(self.root, "link"))
        dst = os.path.join(self.tmp.name, "cow")
        self.ws().create_cow(dst)
        self.assertTrue(os.path.islink(os.path.join(dst, "link")))
        self.assertEqual(os.readlink(os.path.join(dst, "link")), "a.txt")
        self.assertFalse(os.path.exists(os.path.join(dst, ".receipts")))

    def test_create_cow_copies_content(self):
        self.write("src/app.py", "print(1)")
        dst = os.path.join(self.tmp.name, "cow")
        self.ws().create_cow(dst)
        with open(os.path.join(dst, "src", "app.py")) as f:
            self.assertEqual(f.read(), "print(1)")

    def test_diff_reports_added_removed_changed(self):
        self.write("keep.txt", "keep")
        self.write("change.txt", "before")
        self.write("gone.txt", "gone")
        ws = self.ws()
        before = ws.scan()
        os.remove(os.path.join(self.root, "gone.txt"))
        with open(os.path.join(self.root, "change.txt"), "w") as f:
            f.write("after")
        with open(os.path.join(self.root, "new.txt"), "w") as f:
            f.write("new")
        after = ws.scan()
        diff = ws.diff(before, after)
        self.assertEqual(diff["added"], ["new.txt"])
        self.assertIn("gone.txt", diff["removed"])
        self.assertIn("change.txt", diff["changed"])

    def test_capture_stores_before_and_after_objects(self):
        self.write("change.txt", "before")
        ws = self.ws()
        before = ws.scan()
        before_dir = os.path.join(self.tmp.name, "before_dir")
        ws.create_cow(before_dir)
        with open(os.path.join(self.root, "change.txt"), "w") as f:
            f.write("after")
        after = ws.scan()
        after_dir = os.path.join(self.tmp.name, "after_dir")
        ws.create_cow(after_dir)
        diff = ws.diff(before, after)
        shas = ws.capture(before, after, before_dir, after_dir, diff)
        store = self.store()
        self.assertTrue(store.has(before["change.txt"]["sha"]))
        self.assertTrue(store.has(after["change.txt"]["sha"]))
        self.assertEqual(len(shas), 2)

    def test_materialize_restores_deleted_file(self):
        self.write("a.txt", "alpha")
        ws = self.ws()
        state = ws.scan()
        ws.capture(state, {}, self.root, self.root, {"changed": [], "removed": ["a.txt"], "added": []})
        os.remove(os.path.join(self.root, "a.txt"))
        ws.materialize(self.root, state)
        self.assertEqual(self.read("a.txt"), b"alpha")

    def test_materialize_removes_added_file(self):
        self.write("a.txt", "alpha")
        ws = self.ws()
        state = ws.scan()
        self.write("extra.txt", "extra")
        ws.materialize(self.root, state, remove_extra=True)
        self.assertFalse(self.exists("extra.txt"))

    def test_materialize_rejects_traversal_key(self):
        ws = self.ws()
        state = {"../escape.txt": {"kind": "file", "sha": "0" * 64, "mode": 0o644, "size": 1}}
        with self.assertRaises(ValueError):
            ws.materialize(self.root, state)

    def test_materialize_rejects_absolute_key(self):
        ws = self.ws()
        state = {"/tmp/escape.txt": {"kind": "file", "sha": "0" * 64, "mode": 0o644, "size": 1}}
        with self.assertRaises(ValueError):
            ws.materialize(self.root, state)

    def test_materialize_rejects_symlink_parent(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.root, "sub"))
        ws = self.ws()
        state = {"sub/escape.txt": {"kind": "file", "sha": "0" * 64, "mode": 0o644, "size": 1}}
        with self.assertRaises(ValueError):
            ws.materialize(self.root, state)
        self.assertFalse(os.path.exists(os.path.join(outside, "escape.txt")))

    def test_materialize_restores_symlink(self):
        self.write("a.txt", "alpha")
        os.symlink("a.txt", os.path.join(self.root, "link"))
        ws = self.ws()
        state = ws.scan()
        os.remove(os.path.join(self.root, "link"))
        ws.materialize(self.root, state)
        self.assertTrue(os.path.islink(os.path.join(self.root, "link")))
        self.assertEqual(os.readlink(os.path.join(self.root, "link")), "a.txt")

    def test_materialize_restores_mode(self):
        self.write("script.sh", "#!/bin/sh", mode=0o755)
        ws = self.ws()
        state = ws.scan()
        os.chmod(os.path.join(self.root, "script.sh"), 0o644)
        ws.materialize(self.root, state)
        self.assertEqual(os.stat(os.path.join(self.root, "script.sh")).st_mode & 0o777, 0o755)

    def test_materialize_does_not_touch_receipts_store(self):
        self.write("a.txt", "alpha")
        ws = self.ws()
        state = ws.scan()
        marker = os.path.join(self.root, ".receipts", "ledger.jsonl")
        self.assertTrue(os.path.exists(marker))
        ws.materialize(self.root, state, remove_extra=True)
        self.assertTrue(os.path.exists(marker))


if __name__ == "__main__":
    unittest.main()
