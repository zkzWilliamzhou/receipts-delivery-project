"""Default-deny policy, environment allowlist, and claim grammar."""
import json
import os
import re

from .models import canonical, sha256_text
from .sandbox import Backend, capabilities, is_enforcing

DEFAULT_POLICY = {
    "version": 1,
    "network": {"mode": "deny", "allow_domains": []},
    "deny_commands": [
        "curl", "wget", "nc", "ncat", "telnet", "ftp", "ssh", "scp",
        "git clone", "git fetch", "git push", "pip install", "npm install",
    ],
    "protected_paths": [
        ".receipts", ".git", ".env", ".ssh", "id_rsa", ".pem", "credentials",
    ],
    "env_allowlist": [
        "PATH", "LANG", "LC_ALL", "HOME", "TMPDIR", "PYTHONPATH",
        "VIRTUAL_ENV", "CI", "GOFLAGS", "NODE_PATH", "CARGO_HOME", "GOPATH",
    ],
    "max_wall_seconds": 120,
    "max_output_bytes": 262144,
    "max_file_bytes": 67108864,
    "max_files": 20000,
    "claims": {
        "tests pass": {
            "kind": "command_ok",
            "commands": [
                "pytest", "python -m pytest", "python3 -m pytest",
                "python -m unittest", "python3 -m unittest",
                "go test", "npm test", "cargo test", "make test",
            ],
            "require_exit": 0,
            "requires_network_isolation": False,
        },
        "build succeeded": {
            "kind": "command_ok",
            "commands": ["make", "npm run build", "cargo build", "go build", "python -m build"],
            "require_exit": 0,
            "requires_network_isolation": False,
        },
        "lint clean": {
            "kind": "command_ok",
            "commands": ["ruff check", "flake8", "eslint", "golangci-lint run"],
            "require_exit": 0,
            "requires_network_isolation": False,
        },
        "no network access": {
            "kind": "network_isolation",
            "requires_network_isolation": True,
        },
    },
}

DEAD_PROXY = "http://127.0.0.1:1"


def normalize_claim(claim):
    text = re.sub(r"[^a-z0-9 ]+", " ", claim.lower())
    return re.sub(r"\s+", " ", text).strip()


class Policy:
    def __init__(self, data):
        self.data = data

    @classmethod
    def default(cls):
        return cls(json.loads(canonical(DEFAULT_POLICY)))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path):
        tmp = path + ".tmp-%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, sort_keys=True, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    def hash(self):
        return sha256_text(canonical(self.data))

    def match_command(self, argv, commands):
        argv = [str(a) for a in argv]
        for command in commands:
            parts = str(command).split()
            if parts and len(argv) >= len(parts) and argv[:len(parts)] == parts:
                return True
        return False

    def is_protected(self, rel):
        norm = str(rel).replace("\\", "/").lstrip("/")
        parts = norm.split("/")
        for marker in self.data["protected_paths"]:
            if marker.startswith("."):
                if marker in parts or norm.endswith(marker):
                    return True
            elif marker in parts or norm.endswith("/" + marker) or norm == marker:
                return True
        return False

    def evaluate(self, argv, backend):
        name = backend.name if isinstance(backend, Backend) else backend
        caps = capabilities(backend)
        reasons = []
        if not argv:
            reasons.append("empty command")
        else:
            if self.data["network"]["mode"] == "deny":
                for command in self.data["deny_commands"]:
                    if self.match_command(argv, [command]):
                        reasons.append(
                            "network: %s denied by default-deny policy" % command
                        )
                        break
            for token in argv[1:]:
                token = str(token)
                if token.startswith("/"):
                    reasons.append("absolute path: %s" % token)
                    break
                if self.is_protected(token):
                    reasons.append("protected path: %s" % token)
                    break
        return {
            "version": self.data["version"],
            "hash": self.hash(),
            "decision": "deny" if reasons else "allow",
            "reasons": reasons,
            "network_mode": self.data["network"]["mode"],
            "backend": name,
            "capabilities": caps,
        }

    def child_env(self, base_env, home, tmpdir, backend):
        env = {k: str(v) for k, v in base_env.items()
               if k in self.data["env_allowlist"]}
        env["HOME"] = home
        env["TMPDIR"] = tmpdir
        if not is_enforcing(backend):
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
                        "https_proxy", "all_proxy"):
                env[key] = DEAD_PROXY
            env["NO_PROXY"] = ""
        return env

    def claim_rule(self, claim):
        norm = normalize_claim(claim)
        for key, rule in self.data["claims"].items():
            key_norm = normalize_claim(key)
            if key_norm and (norm == key_norm or key_norm in norm):
                return rule
        return None
