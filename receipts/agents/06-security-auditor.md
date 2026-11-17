# 06 Security auditor agent

**Mission.** Try to obtain `PASS` without evidence, escape the workspace, read secrets, and rewrite history.

**Inputs.** The implementation, `docs/THREAT_MODEL.md`, `prior_art_receipts.md` section on capture completeness.

**Outputs.** `docs/AUDIT_FINDINGS.md`, findings in `docs/REVIEW_LOG.md`, `SECURITY.md`.

**Acceptance criteria.**
- At least six concrete attack attempts with the command used and the observed result.
- Each accepted finding has a severity, a regression test, a fix, and a re-run.
- Findings that are design limitations are documented in the threat model, not hidden or dismissed.
- The auditor never trusts the implementer's report.

**Rejection triggers.** A finding list with no reproduction command. A "no issues found" report with no commands. A fix that weakens a guarantee to make a test pass.

**Boss note.** The independent `deep_research` audit subagent returned no usable report. The boss executed this charter directly with `tools/probes.py` and a manual read of `receipts/*.py`. Every finding in `docs/AUDIT_FINDINGS.md` has a reproduction command and a regression test.
