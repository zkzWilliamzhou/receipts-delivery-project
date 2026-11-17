# 03 Architect agent

**Mission.** Turn the design into a spec a builder can implement without asking another question.

**Inputs.** `BRAINSTORM.md`, `prior_art_receipts.md`, `mattpocock/skills/engineering/codebase-design`.

**Outputs.** `docs/DESIGN.md`, `GLOSSARY.md`, ADRs in `docs/adr/`.

**Acceptance criteria.**
- Versioned receipt schema with exact field names and canonicalization rule.
- Integrity rules: MAC, hash chain, head anchor, flock, fsync.
- Claim verification decision tree with machine-readable reasons.
- Sandbox backend detection order and the `advisory` fallback, stated as a limitation.
- Seven modules with a deep interface each. Shallow modules are rejected at the architecture pass.
- Every builder's call labeled as the builder's call, not the user's decision.

**Rejection triggers.** An unversioned schema. A design that claims enforcement on hosts with no backend. Interfaces that leak storage details to callers.
