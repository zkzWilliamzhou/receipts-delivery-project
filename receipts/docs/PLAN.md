# Plan

Hard gates. A phase does not start until the previous gate is green. The boss rejects work that misses a gate and sends it back.

| # | Phase | Owner | Gate |
|---|---|---|---|
| 0 | Install six upstream skill collections | Boss | `docs/INSTALLED_SKILLS.md` lists real files on disk |
| 1 | Prior art + star dynamics research | Research agents | Two reports exist; novelty claim narrowed to an integration claim |
| 2 | Brainstorm, self-grilling, design | Boss | `BRAINSTORM.md` + `DESIGN.md` written before product code |
| 3 | Workflow and agent charters | Boss | `WORKFLOW.md` + 8 charters with acceptance criteria |
| 4 | Tests first (RED) | Test agent | Suite collected; every new test fails for the expected reason |
| 5 | Implementation (GREEN) | Implement agent | Full suite green, zero skips |
| 6 | CLI, demo, packaging | Release agent | `demo` runs offline and shows three outcomes |
| 7 | Review rounds 1-8+ | Security + Review agents | `docs/REVIEW_LOG.md` records a real finding, a real fix, and a re-run per round |
| 8 | Independent adversarial audit | Auditor agent | Findings triaged; each accepted finding fixed and re-verified |
| 9 | Architecture deepening | Architecture agent | `docs/ARCHITECTURE_REVIEW.html`; golden contract byte-identical after refactor |
| 10 | Final verification | Boss | Full suite, demo, doctor, packaging, evidence in `REVIEW_LOG.md` |

## Phase 4 test inventory

`test_objects.py`, `test_workspace.py`, `test_policy.py`, `test_ledger.py`, `test_engine.py`, `test_claims.py`, `test_cli.py`, `test_security.py`, `test_golden.py`. Adversarial cases: tampering, truncation, symlink escape, secret leakage, stale evidence, unbound claim, timeout, orphan processes, output cap, path traversal in materialize, invalid sha, concurrent append.

## Phase 7 review rounds

1. Functional correctness, TDD red/green
2. CLI contract, exit codes, error handling
3. Path traversal and symlink escape
4. Secret hygiene and file permissions
5. Ledger integrity, atomicity, concurrency
6. Claim semantics: false PASS, staleness, conflicts
7. Independent adversarial audit
8. Resource exhaustion, timeouts, binary and unicode output
9. Architecture deepening with behavior preservation
10. End-to-end release verification

Each round writes: what was run, what failed, root cause, fix, and the exact re-run command with its exit code. A round with no finding states the checks that produced no finding and still records evidence.

## Out of scope for v1

Remote witness, LLM claim binding, structured test-result parsers, editor plugins, Windows support, hosted service. Each is a named issue, not a silent omission.
