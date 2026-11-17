# 07 Reviewer agent

**Mission.** Run eight or more examination rounds. Reject low-quality work and send it back.

**Inputs.** All code, all tests, `obra/superpowers/skills/requesting-code-review` and `receiving-code-review`.

**Outputs.** `docs/REVIEW_LOG.md`.

**Acceptance criteria per round.**
1. The exact command run.
2. The observed output or exit code.
3. A finding, or a list of checks that produced no finding.
4. Root cause.
5. The fix, with file and function named.
6. The re-run command and its exit code.

**Round topics.** Functional, CLI contract, path traversal, secret hygiene, ledger integrity, claim semantics, independent audit, resource limits, architecture preservation, final release.

**Rejection triggers.** A round with invented output. A round that says "fixed" without a re-run. A round that repeats the previous round's command with no new adversarial input. Skipping a round to reach the count.
