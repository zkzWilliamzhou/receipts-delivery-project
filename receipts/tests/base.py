"""Shared fixtures for the receipts test suite."""
import os
import shutil
import tempfile
import unittest

from receipts.engine import Engine
from receipts.objects import ObjectStore


class ReceiptTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="receipts-test-")
        self.root = os.path.join(self.tmp.name, "project")
        os.makedirs(self.root)
        self.engine = Engine(self.root)
        self.engine.init()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, data="hello", mode=None):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data.encode() if isinstance(data, str) else data)
        if mode is not None:
            os.chmod(path, mode)
        return path

    def read(self, rel):
        with open(os.path.join(self.root, rel), "rb") as f:
            return f.read()

    def exists(self, rel):
        return os.path.lexists(os.path.join(self.root, rel))

    def store(self):
        return ObjectStore(os.path.join(self.root, ".receipts", "objects"))

    def set_policy(self, **changes):
        self.engine.policy.data.update(changes)
        self.engine.policy.save(os.path.join(self.root, ".receipts", "policy.json"))
        self.engine.policy = type(self.engine.policy).load(
            os.path.join(self.root, ".receipts", "policy.json")
        )

    def fresh_engine(self):
        return Engine(self.root)


def make_project():
    """Create a bare project directory that the caller must clean up."""
    tmp = tempfile.TemporaryDirectory(prefix="receipts-standalone-")
    root = os.path.join(tmp.name, "p")
    os.makedirs(root)
    return tmp, root
