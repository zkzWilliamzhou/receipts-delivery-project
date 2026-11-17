# Brainstorm and self-grilling

The `obra/superpowers` brainstorming skill normally requires a design conversation and explicit approval before code. This request said to brainstorm, grill myself, then work until done, so the questions are run internally and recorded here. The user's "start working until the work is done" is treated as approval of the design below. No question was left to the user.

## The one-sentence job

> When an AI coding agent says it ran the tests, `receipts` shows the exact command, exit code, output hash, and filesystem delta that back the sentence, or it says `UNVERIFIED`.

## What I know, and why

The user wants a program that (1) does something no existing program does, (2) makes a real difference, (3) can aim at 105k GitHub stars, (4) is built to completion with strict multi-agent review, 8+ bug/safety rounds, and an architecture pass that changes no behavior.

The honest reading of "does not exist" is a falsifiable prior-art claim, not a metaphysical one. I searched for single tools covering all five functions and found none. The novelty is the integration of a claim-to-evidence contract, not a new sandbox primitive.

## Approaches considered

**A. An AI slop / fake-work detector for prose.**
Rejected. It would grade text with a model, which is exactly the failure mode it claims to fix. No ground truth, no exit code, no falsifiable evidence. It also overlaps `stop-slop` and dozens of AI detectors.

**B. A universal least-privilege sandbox for agents.**
Rejected as the core. `bubblewrap`, Landlock, `sandbox-exec`, Codex sandbox and Claude Code permissions already do containment. A new sandbox would be a me-too project on a hard platform matrix. Containment is a building block here, not the product.

**C. Receipts: policy + COW execution + tamper-evident ledger + claim verification + rollback.**
Chosen. Every layer exists somewhere; the binding of an agent's prose to an admissible local receipt does not. It answers a failure the user named in the request itself ("faked work"), it works offline with no API key, and the demo shows three distinct outcomes in under a minute. It also makes the strict-boss requirement in this task itself testable: the boss can call `receipts verify` instead of believing an agent.

## Self-grilling, 14 questions I did not want to answer

1. **Is "no tool does this" just a failure of my search?** Possibly. I commissioned an adversarial prior-art report that names 20+ adjacent systems and concedes where documentation was unretrievable. The claim is narrowed to "no retrieved primary source demonstrates the five-part integration as one local tool". That is the strongest defensible form.
2. **Isn't this OpenTelemetry plus a backup?** Traces record what code chose to emit. Backups record file state without command identity. Neither binds a sentence to an admissible receipt with `UNVERIFIED` as a first-class outcome.
3. **Can a malicious agent fake a receipt?** Yes, if it can run outside the wrapper or read `.receipts/key`. The threat model says so in plain words. `doctor` detects post-hoc edits and truncation against a head anchor; it cannot detect a full rewrite by a privileged attacker. No remote witness ships in v1.
4. **Why would anyone trust the verifier?** It uses deterministic predicates, no LLM judge. It checks ledger integrity before it looks for evidence. It refuses `PASS` on stale, ambiguous, or unbound claims.
5. **Does "tests pass" mean the same thing everywhere?** No. Project-specific claim rules live in `policy.json`. Unbound claims return `UNVERIFIED`.
6. **Does exit code 0 prove tests passed?** No. It proves the recorded test command exited 0. The README says this. Structured test-result ingestion is a documented v2 item.
7. **Isn't running in a copy useless? The agent never touches my tree.** That is the point. `apply` moves a reviewed delta into the real tree; `undo` puts it back. The default protects the working tree.
8. **What if the demo needs a model, a key, or a network call?** It does not. `receipts demo` creates a local unittest file, runs it, verifies it, then shows a denial and a stale verdict. Three acts, offline.
9. **Does 105k stars have any real chance?** No honest plan can promise it. GitHub reported 395 million public repositories; the research report puts 100k-star repos at roughly one in a million, and puts a focused trust CLI at a 25k-60k ceiling over two to four years. I treat 105k as an aspiration and track leading usage metrics instead. See [STAR_STRATEGY.md](STAR_STRATEGY.md).
10. **Is the name good enough?** "Show me the receipt" is a sentence people already say. It is short, spoken easily, and names the product contract.
11. **What makes this a failure even if it works?** If it returns `PASS` without admissible evidence. If it silently claims enforcement on a host with no backend. If it leaks secrets into the ledger. These are anti-goals with tests in `tests/test_claims.py` and `tests/test_security.py`.
12. **Why Python, zero dependencies?** First-run friction decides whether anyone tries it. The star research found zero-config and portability in every repo that crossed 100k. Python 3.9+ ships on the target machines.
13. **What is deliberately out of scope?** Kernel-enforced containment on all platforms, remote witnesses, LLM-assisted claim binding, editing-agent integrations, and a hosted service. Each is a named v2 item, not a hidden gap.
14. **Can I finish this in one session?** Yes, if the scope stays at a single CLI with a small number of deep modules, a stdlib test suite, and an explicit review log. Scope creep is the main schedule risk, so `PLAN.md` has hard gates.

## Goals, non-goals, anti-goals

- **Goals:** falsifiable claim verification, offline demo, honest threat model, zero dependencies, reversible deltas, CI-friendly exit codes.
- **Non-goals:** general agent observability, model evaluation, hosted dashboards, cross-host sandbox parity, LLM judging.
- **Anti-goals:** `PASS` without a receipt, silent advisory-to-enforced upgrade, secrets in the ledger, unverifiable marketing claims in the README.

## Constraints

Python 3.9+ standard library only. Linux and macOS first; Windows is untested and labeled. No network required at runtime. Receipt schema versioned. Every function change requires a failing test first, per `superpowers/test-driven-development`.

## Builder check

Read as a fresh builder: the spec fixes the CLI, the receipt schema, the three verdicts, the integrity chain, the threat model, and the acceptance tests. Open calls left to the builder: exact redaction patterns, object-store layout, backend detection order, and report styling. All four are recorded as my calls in [DESIGN.md](DESIGN.md).

Approved by the user's instruction to work until done. Next step: [PLAN.md](PLAN.md).
