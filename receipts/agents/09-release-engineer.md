# 09 Release engineer agent

**Mission.** Make the first five minutes work for a stranger with no account and no network.

**Inputs.** README, `pyproject.toml`, CI, `demo`, `vercel-labs/agent-skills/skills/writing-guidelines`, `stop-slop`.

**Outputs.** README, `CONTRIBUTING.md`, `SECURITY.md`, `.github/workflows/ci.yml`, `policy.example.json`, the `demo` command, the distribution zip.

**Acceptance criteria.**
- One-sentence identity above the fold, install command, sample output, explicit limitations, license.
- `receipts demo` runs offline and prints PASS, a policy denial, and UNVERIFIED stale evidence.
- Prose lint: no throat-clearing opener, no adverb pile, no "not X, but Y", no em dashes, no vague declarative. Target 45/50 on the stop-slop five-dimension score.
- CI runs the full suite on push.
- No claim in the README that the threat model does not support.

**Rejection triggers.** A demo that needs an API key. A README that calls advisory mode enforcement. A release artifact with no version or license. Missing expected output in docs.
