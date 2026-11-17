import json
import os
import unittest

from receipts.policy import Policy
from receipts.sandbox import ADVISORY, BWRAP
from tests.base import ReceiptTestCase


class PolicyTests(ReceiptTestCase):
    def policy(self):
        return Policy.load(os.path.join(self.root, ".receipts", "policy.json"))

    def test_default_policy_denies_network(self):
        self.assertEqual(self.policy().data["network"]["mode"], "deny")

    def test_evaluate_denies_network_command_without_backend(self):
        d = self.policy().evaluate(["curl", "https://example.com"], ADVISORY)
        self.assertEqual(d["decision"], "deny")
        self.assertTrue(any("network" in r for r in d["reasons"]))

    def test_evaluate_denies_network_command_even_with_enforcing_backend(self):
        d = self.policy().evaluate(["curl", "https://example.com"], BWRAP)
        self.assertEqual(d["decision"], "deny")
        self.assertTrue(any("network" in r for r in d["reasons"]))
        self.assertTrue(d["capabilities"]["network_isolation"])

    def test_evaluate_denies_destructive_absolute_path(self):
        d = self.policy().evaluate(["rm", "-rf", "/etc"], ADVISORY)
        self.assertEqual(d["decision"], "deny")

    def test_evaluate_denies_protected_relative_path(self):
        d = self.policy().evaluate(["cat", ".env"], ADVISORY)
        self.assertEqual(d["decision"], "deny")

    def test_evaluate_allows_local_test_command(self):
        d = self.policy().evaluate(["python3", "-m", "unittest", "discover"], ADVISORY)
        self.assertEqual(d["decision"], "allow")
        self.assertEqual(d["reasons"], [])

    def test_evaluate_rejects_empty_argv(self):
        d = self.policy().evaluate([], ADVISORY)
        self.assertEqual(d["decision"], "deny")

    def test_child_env_has_no_secret_keys(self):
        env = dict(os.environ)
        env.update({"AWS_SECRET_ACCESS_KEY": "s3cr3t", "GITHUB_TOKEN": "ghp_abc", "PATH": "/usr/bin"})
        child = self.policy().child_env(env, "/tmp/cow", "/tmp/cow", ADVISORY)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", child)
        self.assertNotIn("GITHUB_TOKEN", child)
        self.assertEqual(child["PATH"], "/usr/bin")
        self.assertEqual(child["HOME"], "/tmp/cow")

    def test_child_env_sets_dead_proxy_in_advisory_mode(self):
        child = self.policy().child_env({}, "/tmp/cow", "/tmp/cow", ADVISORY)
        self.assertIn("HTTP_PROXY", child)
        self.assertIn("127.0.0.1:1", child["HTTP_PROXY"])

    def test_child_env_has_no_proxy_override_with_real_backend(self):
        child = self.policy().child_env({}, "/tmp/cow", "/tmp/cow", BWRAP)
        self.assertNotIn("HTTP_PROXY", child)

    def test_claim_rule_matches_tests_pass(self):
        rule = self.policy().claim_rule("Tests pass.")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["kind"], "command_ok")

    def test_claim_rule_unknown_returns_none(self):
        self.assertIsNone(self.policy().claim_rule("I invented a new color"))

    def test_match_command_matches_token_prefix(self):
        p = self.policy()
        self.assertTrue(p.match_command(["python3", "-m", "unittest", "discover", "-v"],
                                        ["python3 -m unittest", "pytest"]))
        self.assertFalse(p.match_command(["echo", "hi"], ["python3 -m unittest"]))

    def test_policy_hash_changes_when_policy_changes(self):
        p = self.policy()
        before = p.hash()
        p.data["max_wall_seconds"] = 7
        self.assertNotEqual(before, p.hash())

    def test_policy_save_load_roundtrip(self):
        p = self.policy()
        p.data["max_wall_seconds"] = 42
        path = os.path.join(self.tmp.name, "p.json")
        p.save(path)
        self.assertEqual(Policy.load(path).data["max_wall_seconds"], 42)

    def test_is_protected_detects_sensitive_files(self):
        p = self.policy()
        for rel in (".env", "config/id_rsa", "certs/server.pem", ".git/config", ".receipts/key"):
            with self.subTest(rel=rel):
                self.assertTrue(p.is_protected(rel))
        self.assertFalse(p.is_protected("src/app.py"))

    def test_policy_file_is_private(self):
        path = os.path.join(self.root, ".receipts", "policy.json")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_default_policy_matches_example(self):
        example = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policy.example.json")
        with open(example) as f:
            shipped = json.load(f)
        self.assertEqual(shipped["network"]["mode"], self.policy().data["network"]["mode"])


if __name__ == "__main__":
    unittest.main()
