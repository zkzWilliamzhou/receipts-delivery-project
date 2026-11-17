# ADR 0001: default-deny network, explicit backend disclosure

**Status.** Accepted.

**Context.** A trust tool that claims enforcement on a host without a sandbox backend is worse than no tool. The prior-art report found that a sandbox can block access without recording which policy blocked it.

**Decision.** The default policy denies network commands. `receipts` tries `bwrap`, then `unshare -n`, then `sandbox-exec`, and records the backend that actually ran. With no backend, it sets a dead proxy, labels the Action `advisory`, and `verify` refuses to return `PASS` for a claim that requires network isolation.

**Consequences.** Some valid commands are denied on a fresh install until the user edits `policy.json`. The README states the limitation. A future ADR may add a remote witness or a signed backend capability.

**Do not re-litigate** unless a backend can be verified on the three supported platforms.
