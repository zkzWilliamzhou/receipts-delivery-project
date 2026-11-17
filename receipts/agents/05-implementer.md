# 05 Implementer agent

**Mission.** Make the suite green with the minimum correct code.

**Inputs.** `DESIGN.md`, the failing suite, `obra/superpowers/skills/systematic-debugging`.

**Outputs.** `receipts/*.py`.

**Acceptance criteria.**
- Standard library only, Python 3.9+.
- `subprocess` always `shell=False`, fresh session, wall-clock timeout, process group killed on timeout.
- Key and ledger created with 0600/0700 permissions.
- No full environment stored, no unredacted known secrets written.
- Every receipt records the actual sandbox backend.
- Full suite green with zero skips and zero warnings.

**Rejection triggers.** Code written before the RED run. A swallowed exception. A `PASS` shortcut. A hardcoded verdict. Adding a dependency to make a test pass. Changing a test to make it pass instead of fixing the code.
