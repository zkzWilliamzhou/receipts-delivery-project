"""Best-effort secret redaction. Applied before any captured output reaches the ledger."""
import re

REDACTED = "[REDACTED]"

PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{10,}"),
]


def contains_secret(text):
    return any(p.search(text) for p in PATTERNS)


def redact(text):
    for pattern in PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text
