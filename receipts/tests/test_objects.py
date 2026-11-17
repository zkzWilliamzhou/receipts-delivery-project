import hashlib
import os
import stat
import unittest

from receipts.models import sha256_bytes
from receipts.objects import ObjectStore
from tests.base import ReceiptTestCase


class ObjectStoreTests(ReceiptTestCase):
    def test_put_bytes_returns_sha256_and_stores_content(self):
        store = self.store()
        sha = store.put_bytes(b"alpha")
        self.assertEqual(sha, hashlib.sha256(b"alpha").hexdigest())
        self.assertEqual(store.get(sha), b"alpha")

    def test_put_bytes_is_idempotent(self):
        store = self.store()
        a = store.put_bytes(b"alpha")
        b = store.put_bytes(b"alpha")
        self.assertEqual(a, b)
        self.assertEqual(len([n for n in os.listdir(store.root) if n != "index"]), 1)

    def test_object_file_is_private(self):
        store = self.store()
        sha = store.put_bytes(b"alpha")
        mode = stat.S_IMODE(os.stat(store.path_for(sha)).st_mode)
        self.assertEqual(mode, 0o600)

    def test_put_file_streams_content(self):
        store = self.store()
        payload = b"x" * (1024 * 512)
        path = self.write("big.bin", payload)
        sha = store.put_file(path)
        self.assertEqual(sha, hashlib.sha256(payload).hexdigest())
        self.assertEqual(store.get(sha), payload)

    def test_get_rejects_path_traversal_sha(self):
        store = self.store()
        for bad in ("../etc/passwd", "abc", "A" * 64, "g" * 64, "", "../../key"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                store.get(bad)

    def test_get_missing_object_raises(self):
        store = self.store()
        with self.assertRaises(FileNotFoundError):
            store.get("0" * 64)

    def test_verify_all_detects_corruption(self):
        store = self.store()
        sha = store.put_bytes(b"alpha")
        with open(store.path_for(sha), "wb") as f:
            f.write(b"tampered")
        self.assertIn(sha, store.verify_all())

    def test_verify_all_clean(self):
        store = self.store()
        store.put_bytes(b"alpha")
        store.put_bytes(b"beta")
        self.assertEqual(store.verify_all(), [])

    def test_has(self):
        store = self.store()
        sha = store.put_bytes(b"alpha")
        self.assertTrue(store.has(sha))
        self.assertFalse(store.has("1" * 64))

    def test_sha256_bytes_matches_hashlib(self):
        self.assertEqual(sha256_bytes(b"abc"), hashlib.sha256(b"abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
