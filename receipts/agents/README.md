# Agents

Nine charters. Two research tracks and one adversarial audit ran as `deep_research` subagents. The remaining roles are executed by the boss in sequence, with a gate between each. A charter is a contract, not a claim of an independent process.

| # | Agent | Output | Gate |
|---|---|---|---|
| 01 | Research | `prior_art_receipts.md`, `github_star_dynamics.md` | Sources cited, uncertainty flagged |
| 02 | Brainstorm | `docs/BRAINSTORM.md` | 14 self-grilling questions, three approaches, anti-goals |
| 03 | Architect | `docs/DESIGN.md` | Receipt schema, integrity rules, threat boundary |
| 04 | Test engineer | `tests/test_*.py` | Tests fail for the expected reason before implementation |
| 05 | Implementer | `receipts/*.py` | Full suite green, zero skips |
| 06 | Security auditor | `docs/THREAT_MODEL.md`, findings | Every accepted finding fixed and re-run |
| 07 | Reviewer | `docs/REVIEW_LOG.md` | 8+ rounds, each with command, finding, fix, re-run |
| 08 | Architecture refactorer | `docs/ARCHITECTURE_REVIEW.html` | Golden contract byte-identical |
| 09 | Release engineer | README, CI, `demo` | Offline three-act demo, clean package |

## Boss rejection triggers

- A success claim without a command output in the same turn.
- A test that passes on first run (it does not test the new behavior).
- A review round with no recorded command.
- A `PASS` verdict produced without an admissible receipt.
- A limitation of the tool left out of the README.
- A refactor with any golden contract diff.
- An agent that reports "done" but left a skipped test, an unhandled exception path, or an unversioned schema change.

Rejected work goes back with the specific gate named. No partial credit.
