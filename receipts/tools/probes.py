"""Adversarial probes used by docs/REVIEW_LOG.md. Each returns concrete evidence."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from receipts.claims import ClaimVerifier  # noqa: E402
from receipts.engine import Engine  # noqa: E402
from receipts.sandbox import ADVISORY  # noqa: E402


def project():
    tmp = tempfile.mkdtemp(prefix="receipts-probe-")
    root = os.path.join(tmp, "p")
    os.makedirs(root)
    return tmp, root


def probe_cli():
    tmp, root = project()
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cases = [
            ["init"],
            ["verify", ""],
            ["show", "r0000001"],
            ["replay", "r0000001"],
            ["log", "--limit", "abc"],
            ["policy", "set", "max_wall_seconds", "7"],
            ["policy", "show"],
            ["run", "--tag", "x", "--", "python3", "-c", "pass"],
            ["doctor"],
        ]
        out = []
        for case in cases:
            p = subprocess.run([sys.executable, "-m", "receipts"] + case,
                               cwd=root, env=env, capture_output=True, text=True, timeout=30)
            out.append((case, p.returncode, (p.stdout + p.stderr).strip()[:160]))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_symlink_escape():
    tmp, root = project()
    outside = os.path.join(tmp, "outside")
    os.makedirs(outside)
    try:
        os.symlink(outside, os.path.join(root, "escape"))
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        r = engine.run(["python3", "-c", "open('escape/pwned.txt','w').write('x')"])
        created = os.path.exists(os.path.join(outside, "pwned.txt"))
        captured = any("pwned" in k for k in r["workspace"]["after"])
        return {"outside_file_created": created, "receipt_captured_write": captured,
                "added": r["workspace"]["added"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_secret_objects():
    tmp, root = project()
    try:
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        engine.run(["python3", "-c", "open('.env','w').write('SUPER_SECRET_VALUE_123')"])
        objects = os.path.join(root, ".receipts", "objects")
        leaked = []
        for current, _, files in os.walk(objects):
            for name in files:
                with open(os.path.join(current, name), "rb") as f:
                    if b"SUPER_SECRET_VALUE_123" in f.read():
                        leaked.append(name)
        return {"secret_objects": leaked}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_corrupt_append():
    tmp, root = project()
    try:
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        engine.run(["python3", "-c", "pass"])
        path = os.path.join(root, ".receipts", "ledger.jsonl")
        with open(path, "a") as f:
            f.write("{}\n")
        before = engine.ledger.doctor()
        refusal = None
        try:
            engine.run(["python3", "-c", "pass"])
        except ValueError as exc:
            refusal = str(exc)
        return {"doctor_before": before["ok"], "append_refused": refusal is not None,
                "refusal": refusal, "doctor_after": engine.ledger.doctor()["ok"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_strict_containment():
    tmp, root = project()
    try:
        with open(os.path.join(root, "test_ok.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        receipt = engine.run(["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"])
        normal = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        strict = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass", strict=True)
        return {"backend": receipt["policy"]["backend"],
                "caps": receipt["policy"]["capabilities"],
                "normal": normal["verdict"], "strict": strict["verdict"],
                "strict_reason": strict["reason"], "warnings": normal["warnings"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_policy_change():
    tmp, root = project()
    try:
        with open(os.path.join(root, "test_ok.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        engine.run(["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"])
        v1 = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        engine.policy.data["max_wall_seconds"] = 3
        engine.policy.save(engine.policy_path)
        engine.policy = type(engine.policy).load(engine.policy_path)
        v2 = ClaimVerifier(engine.ledger, engine.policy).verify("tests pass")
        return {"before": v1["verdict"], "after_policy_change": v2["verdict"],
                "reason": v2["reason"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_large_output():
    tmp, root = project()
    try:
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        tracemalloc.start()
        engine.run(["python3", "-c", "import sys;sys.stdout.write('z'*20000000)"])
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {"python_peak_mb": round(peak / 1024 / 1024, 1),
                "stored_cap_bytes": engine.policy.data["max_output_bytes"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_two_processes():
    tmp, root = project()
    try:
        engine = Engine(root, backend=ADVISORY)
        engine.init()
        snippet = (
            "import sys;sys.path.insert(0,%r);"
            "from receipts.engine import Engine;"
            "from receipts.sandbox import ADVISORY;"
            "e=Engine(%r,backend=ADVISORY);e.init();"
            "[e.run(['python3','-c','pass']) for _ in range(8)]"
        ) % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), root)
        procs = [subprocess.Popen([sys.executable, "-c", snippet],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for _ in range(4)]
        for p in procs:
            p.wait(timeout=60)
        errors = [p.stderr.read().decode() for p in procs if p.returncode != 0]
        return {"doctor_ok": engine.ledger.doctor()["ok"],
                "count": engine.ledger.doctor()["count"],
                "process_errors": [e[:200] for e in errors]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name in ("probe_cli", "probe_symlink_escape", "probe_secret_objects",
                 "probe_corrupt_append", "probe_policy_change",
                 "probe_large_output", "probe_two_processes",
                 "probe_strict_containment"):
        print("==", name)
        try:
            print(json.dumps(globals()[name](), indent=2, default=str))
        except Exception as exc:
            print("PROBE ERROR", type(exc).__name__, str(exc))
