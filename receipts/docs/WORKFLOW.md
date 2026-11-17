# Workflow

```
[0 skills] -- [1 research] -- [2 brainstorm/design] -- [3 workflow+agents]
                                                          |
                                                          v
                                     [4 RED tests] --gate--> [5 implementation]
                                                          |            |
                                                          |            v
                                                          |      [6 CLI/demo]
                                                          |            |
                                                          +------------+
                                                                       |
                                                                       v
                              +------------------------------------------> [7 review rounds 1-8]
                              |                                                  |
                              |                                                  v
                              |                                       [8 independent audit]
                              |                                                  |
                              |                                                  v
                              |                              [9 architecture deepening]
                              |                                      |  golden contract
                              |                                      |  must be identical
                              |                                      v
                              +---------- reject / revise -------- [10 final verification]
```

## Boss rules

1. No completion claim without a fresh command output. `verification-before-completion` is binding on every agent.
2. A test written after the code is not evidence. Tests land first and must be watched failing.
3. An agent's self-report is not evidence. The boss runs the suite, reads the diff, and checks exit codes.
4. A finding without a fix and a re-run is not a review round.
5. If a round finds nothing, it records the commands that found nothing. Silence is not a pass.
6. Any agent that returns `PASS` without receipts, claims a test passed without output, or hides a limitation in the README is sent back.
7. The architecture pass must preserve behavior. `tests/test_golden.py` compares a normalized CLI transcript before and after. A diff blocks the release.

## Handoff contract

Every agent produces a file, not a promise:

| Agent | Output |
|---|---|
| Research | `prior_art_receipts.md`, `github_star_dynamics.md` |
| Brainstorm | `docs/BRAINSTORM.md`, `docs/DESIGN.md` |
| Workflow | `docs/WORKFLOW.md`, `agents/*.md` |
| Test | `tests/test_*.py` |
| Implement | `receipts/*.py` |
| Release | `README.md`, `pyproject.toml`, CI, `demo` command |
| Security | `docs/THREAT_MODEL.md`, `SECURITY.md`, findings in review log |
| Review | `docs/REVIEW_LOG.md` |
| Architecture | `docs/ARCHITECTURE_REVIEW.html`, `GLOSSARY.md`, ADRs |
| Auditor | `docs/AUDIT_FINDINGS.md` |

## Honest execution note

The `deep_research` subagent ran the two research tracks (prior art, star dynamics). An independent adversarial audit subagent was requested but returned no usable report, so the boss executed that charter directly: manual source review plus `tools/probes.py`, with findings written to `docs/AUDIT_FINDINGS.md`. The other roles are charters in `agents/` executed sequentially by the boss, with the gates above enforced between them. No role is claimed to be an independent autonomous process when it is not. The review log records actual commands and outputs, not simulated ones.
