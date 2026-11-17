"""Append-only, HMAC-signed, hash-chained receipt ledger."""
import fcntl
import json
import os
import secrets

from .models import canonical, hmac_hex, sha256_text

ZERO = "0" * 64


class Ledger:
    SCHEMA = 1

    def __init__(self, directory):
        self.dir = os.path.abspath(directory)
        self.ledger_path = os.path.join(self.dir, "ledger.jsonl")
        self.key_path = os.path.join(self.dir, "key")
        self.head_path = os.path.join(self.dir, "head")
        self.lock_path = os.path.join(self.dir, "ledger.lock")

    def init(self):
        os.makedirs(self.dir, exist_ok=True)
        os.chmod(self.dir, 0o700)
        if not os.path.exists(self.key_path):
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(secrets.token_bytes(32))
                f.flush()
                os.fsync(f.fileno())
        if not os.path.exists(self.ledger_path):
            fd = os.open(self.ledger_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        if not os.path.exists(self.head_path):
            self._write_head(ZERO)
        if not os.path.exists(self.lock_path):
            fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        os.chmod(self.key_path, 0o600)
        os.chmod(self.ledger_path, 0o600)

    def _key(self):
        with open(self.key_path, "rb") as f:
            return f.read()

    def _write_head(self, value):
        tmp = self.head_path + ".tmp-%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.head_path)
        try:
            fd = os.open(self.dir, os.O_RDONLY)
            os.fsync(fd)
            os.close(fd)
        except OSError:
            pass

    def head(self):
        if not os.path.exists(self.head_path):
            return ZERO
        with open(self.head_path, encoding="utf-8") as f:
            return f.read().strip()

    def _lines(self):
        if not os.path.exists(self.ledger_path):
            return []
        with open(self.ledger_path, encoding="utf-8") as f:
            return [line for line in f.read().splitlines() if line.strip()]

    def all(self):
        receipts = []
        for line in self._lines():
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(record, dict) and isinstance(record.get("hash"), str):
                receipts.append(record)
        return receipts

    def append(self, body):
        if body.get("schema") != self.SCHEMA:
            raise ValueError("unsupported receipt schema: %r" % body.get("schema"))
        os.makedirs(self.dir, exist_ok=True)
        with open(self.lock_path, "a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                health = self.doctor()
                if not health["ok"]:
                    raise ValueError("refusing to append to a corrupt ledger: %s"
                                     % "; ".join(health["errors"][:3]))
                existing = self.all()
                record = dict(body)
                record["seq"] = len(existing) + 1
                record["id"] = "r%07d" % record["seq"]
                record["prev"] = existing[-1]["hash"] if existing else ZERO
                record["mac"] = hmac_hex(self._key(), canonical(record))
                record["hash"] = sha256_text(canonical(record))
                with open(self.ledger_path, "a", encoding="utf-8") as f:
                    f.write(canonical(record) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(self.ledger_path, 0o600)
                self._write_head(record["hash"])
                return record
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def doctor(self):
        errors = []
        key = self._key() if os.path.exists(self.key_path) else b""
        lines = self._lines()
        prev = ZERO
        last_hash = ZERO
        count = 0
        for index, line in enumerate(lines, 1):
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                errors.append("line %d: invalid JSON" % index)
                continue
            count += 1
            mac = record.get("mac")
            digest = record.get("hash")
            if not isinstance(mac, str) or not isinstance(digest, str):
                errors.append("line %d: missing mac or hash" % index)
                continue
            base = dict(record)
            base.pop("mac", None)
            base.pop("hash", None)
            if hmac_hex(key, canonical(base)) != mac:
                errors.append("line %d: mac mismatch" % index)
            with_mac = dict(base)
            with_mac["mac"] = mac
            if sha256_text(canonical(with_mac)) != digest:
                errors.append("line %d: hash mismatch" % index)
            if record.get("prev") != prev:
                errors.append("line %d: broken chain (prev mismatch)" % index)
            prev = digest
            last_hash = digest
        head = self.head()
        if head != last_hash:
            errors.append("head mismatch: ledger may have been truncated")
        return {"ok": not errors, "errors": errors, "count": count}
