import unittest

from receipts.sandbox import (ADVISORY, BWRAP, NONE, SANDBOX_EXEC, UNSHARE,
                              Backend, capabilities, is_enforcing, wrap)


class BackendTests(unittest.TestCase):
    def test_capabilities_are_explicit_per_backend(self):
        self.assertTrue(capabilities(BWRAP)["filesystem_containment"])
        self.assertFalse(capabilities(UNSHARE)["filesystem_containment"])
        self.assertTrue(capabilities(SANDBOX_EXEC)["network_isolation"])
        self.assertFalse(capabilities(ADVISORY)["network_isolation"])
        self.assertFalse(capabilities(NONE)["filesystem_containment"])

    def test_backend_object_exposes_same_capabilities(self):
        for name in (BWRAP, UNSHARE, SANDBOX_EXEC, ADVISORY):
            with self.subTest(name=name):
                self.assertEqual(Backend(name).capabilities(), capabilities(name))

    def test_is_enforcing_accepts_name_and_object(self):
        self.assertTrue(is_enforcing(BWRAP))
        self.assertTrue(is_enforcing(Backend(UNSHARE)))
        self.assertFalse(is_enforcing(ADVISORY))
        self.assertFalse(is_enforcing(Backend(ADVISORY)))

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            Backend("magic")
        with self.assertRaises(ValueError):
            capabilities("magic")

    def test_advisory_wrap_is_identity(self):
        self.assertEqual(wrap(["echo", "hi"], ADVISORY, "/tmp/ws"), ["echo", "hi"])

    def test_unshare_wrap_adds_network_namespace(self):
        argv = wrap(["echo", "hi"], UNSHARE, "/tmp/ws")
        self.assertEqual(argv[:3], ["unshare", "-n", "--"])

    def test_bwrap_wrap_contains_root_and_temp_dirs(self):
        argv = wrap(["echo", "hi"], BWRAP, "/tmp/ws")
        self.assertIn("--ro-bind", argv)
        self.assertIn("--tmpfs", argv)
        self.assertIn("--unshare-net", argv)
        self.assertIn("/tmp/ws", argv)

    def test_capabilities_returns_a_copy(self):
        caps = capabilities(UNSHARE)
        caps["filesystem_containment"] = True
        self.assertFalse(capabilities(UNSHARE)["filesystem_containment"])


if __name__ == "__main__":
    unittest.main()
