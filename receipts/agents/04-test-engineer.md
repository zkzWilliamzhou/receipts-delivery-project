# 04 Test engineer agent

**Mission.** Write the suite before the implementation. Watch it fail.

**Inputs.** `DESIGN.md`, `obra/superpowers/skills/test-driven-development`, `writing-good-tests.md`.

**Outputs.** `tests/test_*.py`, `tests/conftest.py`.

**Acceptance criteria.**
- Each test names one behavior and asserts on real code, not mocks of the code under test.
- Adversarial cases present: chain tampering, ledger truncation, symlink escape, path traversal in materialize, secret leakage, stale evidence, unbound claim, output cap, timeout, orphan kill, invalid sha, concurrent append.
- The boss runs `python3 -m unittest discover -s tests -v` and sees collection errors caused by missing modules, not by typos or bad imports in the tests.
- The RED run is recorded in `docs/REVIEW_LOG.md` as round 1.

**Rejection triggers.** A test that passes before implementation. A test that asserts a mock was called. Skipped tests. A missing regression test for any fix in a later round.
