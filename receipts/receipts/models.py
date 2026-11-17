"""Canonical serialization and digests shared by every module."""
import hashlib
import hmac
import json
from datetime import datetime, timezone


def canonical(obj):
    """Stable JSON used for every hash and MAC in the system."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_hex(data):
    return sha256_bytes(data)


def sha256_text(text):
    return sha256_bytes(text.encode("utf-8"))


def hmac_hex(key, payload):
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
