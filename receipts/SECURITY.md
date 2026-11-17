# Security policy

## Supported versions

`0.1.x` receives security fixes. The receipt schema is versioned; a change to `schema` is a breaking change and gets a minor version bump.

## Report a vulnerability

Open a draft advisory or email the maintainers privately. Do not open a public issue for a bypass that lets an agent obtain `PASS` without an admissible receipt, or for a way to read `.receipts/key`.

Include:
- the exact command you ran,
- the receipt or ledger excerpt,
- the verdict you expected and the verdict you got,
- whether it requires a local account or root.

We aim to acknowledge within 72 hours and to ship a regression test with every accepted fix.

## Scope

In scope: verdict correctness, ledger integrity, secret redaction, workspace escape, policy bypass, timeout handling, object store path validation.

Out of scope: a fully compromised host, a malicious command's own printed claims, and attacks that require rewriting both the ledger and the head anchor with a stolen key. Those limits are documented in `docs/THREAT_MODEL.md` instead of being denied.
