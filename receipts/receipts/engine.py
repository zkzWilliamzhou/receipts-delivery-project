"""Orchestrates one action: policy, COW workspace, Backend, capture, receipt."""
import hashlib
import os
import shutil
import signal
import subprocess
import tempfile
import time

from . import redact, sandbox
from .ledger import Ledger
from .models import utc_now
from .objects import ObjectStore
from .policy import Policy
from .workspace import Workspace

CHUNK = 65536


def _read_capped(stream, cap):
    """Hash the whole stream while keeping only `cap` bytes in memory."""
    digest = hashlib.sha256()
    kept = bytearray()
    total = 0
    while True:
        block = stream.read(CHUNK)
        if not block:
            break
        digest.update(block)
        total += len(block)
        if len(kept) < cap:
            kept.extend(block[:cap - len(kept)])
    return bytes(kept), digest.hexdigest(), total


class Engine:
    def __init__(self, root, backend=None):
        self.root = os.path.abspath(root)
        self.base = os.path.join(self.root, ".receipts")
        self.policy_path = os.path.join(self.base, "policy.json")
        self.tmp_root = os.path.join(self.base, "tmp")
        self._backend_override = backend

    def init(self):
        os.makedirs(self.base, exist_ok=True)
        os.chmod(self.base, 0o700)
        os.makedirs(self.tmp_root, exist_ok=True)
        self.store = ObjectStore(os.path.join(self.base, "objects"))
        if not os.path.exists(self.policy_path):
            Policy.default().save(self.policy_path)
        self.ledger = Ledger(self.base)
        self.ledger.init()
        self._refresh()

    def _refresh(self):
        self.policy = Policy.load(self.policy_path)
        self.workspace = Workspace(
            self.root, self.store,
            max_file_bytes=self.policy.data["max_file_bytes"],
            max_files=self.policy.data["max_files"],
            protected_fn=self.policy.is_protected,
        )

    def _ensure(self):
        if not hasattr(self, "ledger") or not hasattr(self, "store"):
            self.init()

    def _backend(self):
        if self._backend_override:
            return sandbox.Backend(self._backend_override)
        return sandbox.Backend.resolve()

    def _popen_run(self, argv, cwd, env, timeout, cap):
        """Capture output to temp files so a chatty command cannot exhaust RAM."""
        with tempfile.TemporaryFile() as out_file, tempfile.TemporaryFile() as err_file:
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, shell=False,
                stdout=out_file, stderr=err_file, start_new_session=True,
            )
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    process.kill()
                process.wait()
                timed_out = True
            out_file.seek(0)
            err_file.seek(0)
            out_b, out_sha, out_len = _read_capped(out_file, cap)
            err_b, err_sha, err_len = _read_capped(err_file, cap)
            return {
                "stdout": out_b, "stderr": err_b,
                "stdout_sha256": out_sha, "stderr_sha256": err_sha,
                "stdout_bytes": out_len, "stderr_bytes": err_len,
                "truncated": out_len > cap or err_len > cap,
                "exit_code": None if timed_out else process.returncode,
                "timed_out": timed_out,
            }

    def _reset_cow(self, cow):
        if os.path.isdir(cow):
            shutil.rmtree(cow, ignore_errors=True)
        os.makedirs(cow)
        self.workspace.create_cow(cow)

    def run(self, argv, tag=None):
        if not argv:
            raise ValueError("run requires a non-empty command")
        argv = [str(a) for a in argv]
        self._ensure()
        self._refresh()

        backend = self._backend()
        decision = self.policy.evaluate(argv, backend)
        started = utc_now()
        started_clock = time.monotonic()
        cap = self.policy.data["max_output_bytes"]
        run_dir = tempfile.mkdtemp(prefix="run-", dir=self.tmp_root)
        cow = os.path.join(run_dir, "cow")
        os.makedirs(cow)
        try:
            self.workspace.create_cow(cow)
            before = self.workspace.scan()
            skipped = list(self.workspace.skipped)
            unsafe = list(self.workspace.unsafe_symlinks) + list(self.workspace.cow_warnings)
            after = dict(before)

            result = {
                "stdout": b"", "stderr": b"",
                "stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "stdout_bytes": 0, "stderr_bytes": 0, "truncated": False,
                "exit_code": None, "timed_out": False,
            }
            env = self.policy.child_env(dict(os.environ), cow, cow, backend)
            attempts = [backend]
            if backend.network_isolation:
                attempts.append(sandbox.Backend(sandbox.ADVISORY))
            for attempt in attempts:
                if decision["decision"] != "allow":
                    break
                wrapped = attempt.wrap(argv, cow)
                try:
                    attempt_result = self._popen_run(
                        wrapped, cow,
                        self.policy.child_env(dict(os.environ), cow, cow, attempt),
                        self.policy.data["max_wall_seconds"], cap,
                    )
                except OSError:
                    if attempt is attempts[-1]:
                        raise
                    backend = sandbox.Backend(sandbox.ADVISORY)
                    decision = self.policy.evaluate(argv, backend)
                    self._reset_cow(cow)
                    continue
                backend = attempt
                decision = self.policy.evaluate(argv, backend)
                env = self.policy.child_env(dict(os.environ), cow, cow, backend)
                result = attempt_result
                break

            backend_name = backend.name
            caps = backend.capabilities()
            if decision["decision"] == "allow":
                after = self.workspace.scan(cow)
                skipped += self.workspace.skipped
                unsafe += self.workspace.unsafe_symlinks
            unsafe = sorted(set(unsafe))
            diff = self.workspace.diff(before, after)
            for key in ("added", "removed", "changed"):
                diff[key] = [rel for rel in diff[key] if rel not in unsafe]
            violations = [rel for rel in (diff["added"] + diff["removed"] + diff["changed"])
                          if self.policy.is_protected(rel)]
            objects = self.workspace.capture(before, after, self.root, cow, diff)

            stdout = redact.redact(result["stdout"].decode("utf-8", "replace"))
            stderr = redact.redact(result["stderr"].decode("utf-8", "replace"))
            body = {
                "schema": 1,
                "started": started,
                "ended": utc_now(),
                "wall_ms": int((time.monotonic() - started_clock) * 1000),
                "action": {
                    "argv": argv, "cwd": self.root, "tag": tag or "",
                    "env": env, "stdin_sha256": hashlib.sha256(b"").hexdigest(),
                    "shell": False,
                },
                "policy": {
                    "version": self.policy.data["version"],
                    "hash": decision["hash"],
                    "decision": decision["decision"],
                    "reasons": decision["reasons"],
                    "network_mode": decision["network_mode"],
                    "backend": backend_name,
                    "capabilities": caps,
                },
                "execution": {
                    "exit_code": result["exit_code"], "timed_out": result["timed_out"],
                    "backend": backend_name, "stdout": stdout, "stderr": stderr,
                    "stdout_sha256": result["stdout_sha256"],
                    "stderr_sha256": result["stderr_sha256"],
                    "stdout_bytes": result["stdout_bytes"],
                    "stderr_bytes": result["stderr_bytes"],
                    "truncated": result["truncated"],
                },
                "workspace": {
                    "before": before, "after": after,
                    "added": diff["added"], "removed": diff["removed"],
                    "changed": diff["changed"],
                    "protected_violations": violations,
                    "unsafe_symlinks": unsafe,
                    "skipped": sorted(set(skipped)),
                },
                "objects": objects,
                "integrity": {"chain": "sha256", "mac": "hmac-sha256", "schema": 1},
            }
            return self.ledger.append(body)
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def find(self, receipt_id):
        self._ensure()
        for receipt in self.ledger.all():
            if receipt.get("id") == receipt_id:
                return receipt
        raise KeyError("unknown receipt %s" % receipt_id)

    def apply(self, receipt_id):
        receipt = self.find(receipt_id)
        if receipt["workspace"]["protected_violations"] or receipt["workspace"].get("unsafe_symlinks"):
            raise ValueError("refusing to apply a receipt with protected-path or symlink violations")
        diff = {k: receipt["workspace"][k] for k in ("added", "removed", "changed")}
        self.workspace.apply_diff(
            self.root, receipt["workspace"]["before"], receipt["workspace"]["after"], diff
        )
        return {"id": receipt_id, "applied": True}

    def undo(self, receipt_id):
        receipt = self.find(receipt_id)
        diff = {k: receipt["workspace"][k] for k in ("added", "removed", "changed")}
        self.workspace.revert_diff(
            self.root, receipt["workspace"]["before"], receipt["workspace"]["after"], diff
        )
        return {"id": receipt_id, "undone": True}

    def replay(self, receipt_id):
        receipt = self.find(receipt_id)
        self._ensure()
        cap = self.policy.data["max_output_bytes"]
        backend = sandbox.Backend(receipt["policy"]["backend"])
        run_dir = tempfile.mkdtemp(prefix="replay-", dir=self.tmp_root)
        cow = os.path.join(run_dir, "cow")
        os.makedirs(cow)
        try:
            self.workspace.materialize(cow, receipt["workspace"]["before"])
            env = self.policy.child_env(dict(os.environ), cow, cow, backend)
            wrapped = backend.wrap(receipt["action"]["argv"], cow)
            result = self._popen_run(wrapped, cow, env,
                                     self.policy.data["max_wall_seconds"], cap)
            after = self.workspace.scan(cow)
            diff = self.workspace.diff(receipt["workspace"]["before"], after)
            expected = receipt["workspace"]
            stdout_match = result["stdout_sha256"] == receipt["execution"]["stdout_sha256"]
            delta_match = (diff["added"] == expected["added"]
                           and diff["removed"] == expected["removed"]
                           and diff["changed"] == expected["changed"])
            exit_match = result["exit_code"] == receipt["execution"]["exit_code"]
            return {
                "id": receipt_id, "match": stdout_match and delta_match and exit_match,
                "exit_code": result["exit_code"],
                "details": {"exit_match": exit_match, "stdout_match": stdout_match,
                            "delta_match": delta_match},
            }
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)
