# ADR 0002: no LLM judge in the verdict path

**Status.** Accepted.

**Context.** An LLM judge can be prompted by the command output it is asked to evaluate. A command can print "all tests passed" and exit 0. Evaluation is not verification.

**Decision.** Claim binding uses deterministic rules from `policy.json`. `PASS` requires an admissible receipt. `UNVERIFIED` is returned for unbound, stale, ambiguous, corrupt, or network-unverifiable claims. An LLM may assist with binding in a later version only behind an explicit policy switch, and never as the source of truth for execution.

**Consequences.** The verifier cannot interpret arbitrary prose. That is a stated limitation, not a missing feature.

**Do not re-litigate** without a regression test that shows a prompt-injected stdout cannot produce `PASS`.
