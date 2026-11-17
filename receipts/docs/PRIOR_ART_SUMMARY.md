# Prior art summary

Full report: `research/prior_art_receipts.md` in the delivery zip (produced by the research subagent).

The five functions were checked separately: isolated COW execution, tamper-evident receipt, claim verification, undo/replay, and default-deny policy.

**Verdict.** No retrieved primary source demonstrates all five as one local-first CLI. The novel core is the claim-to-evidence contract that binds policy, execution, state, and rollback into one falsifiable record. Every underlying primitive exists elsewhere. This is an integration claim.

**What exists.**

| Layer | Existing work | Missing from it |
|---|---|---|
| Tracing | OpenTelemetry, Langfuse, AgentOps, Braintrust, Weave, Phoenix | Command interposition, filesystem state, local receipt chain, claim binding |
| Editor checkpoints | Cline, Cursor-style checkpoints | Command metadata, hash-chained receipt, policy decision record |
| Sandboxes | Codex sandbox, Claude Code permissions, Landlock, bubblewrap, nsjail, firejail | Audit trail of the decision, undo, claim verification |
| Backups | restic, borg, git stash | Command identity, output, exit code, policy, receipt chain |
| Provenance | Bazel remote execution, in-toto, SLSA, Sigstore, TUF | Local shell interposition, claim semantics, `UNVERIFIED` as an outcome |

**Conceded limits of the search.** Codex and Claude Code source pages, and Cursor documentation, were not retrievable in the research pass. Hosted commercial products may exist that are not visible in public material. Documented absence is evidence of non-coverage, not proof of impossibility.

**Hardest attack.** Capture completeness, not hash-chain forgery. A second shell, a symlink escape, a background process, or a preloaded library can leave reality outside the receipt. `docs/THREAT_MODEL.md` states this rather than hiding it.

**Design consequences.** The receipt records the policy version and decision, the sandbox backend, before/after file hashes, and redacted raw output. `doctor` checks the chain before `verify` looks for evidence. `verify` returns `UNVERIFIED` when binding, completeness, integrity, or staleness checks fail.
