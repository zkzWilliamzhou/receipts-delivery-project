# Glossary

Shared vocabulary for architecture reviews. Use these words exactly.

| Term | Meaning in this codebase |
|---|---|
| **Receipt** | One signed, hash-chained record of a single action: policy decision, argv, output, and the before/after workspace state. |
| **Action** | One `receipts run` invocation. Has one receipt. |
| **Ledger** | The append-only sequence of receipts plus its head anchor. |
| **Verdict** | `PASS`, `FAIL`, or `UNVERIFIED` produced by the Claim module. |
| **Claim** | A natural-language sentence asserted by an agent. Never evidence by itself. |
| **Admissible receipt** | A receipt with an intact chain, `allow` policy decision, matching command, required exit code, untruncated output, no protected-path violation, and no later workspace change. |
| **State** | A mapping from a relative path to kind, sha, mode, and size. |
| **Object** | Content-addressed bytes for one file version, keyed by sha256. |
| **Workspace** | The copy-on-write directory where an Action runs. |
| **Module** | A unit with a deep interface. Deleting it should concentrate complexity, not move it. |
| **Seam** | The place two modules meet. One adapter is a hypothetical seam; two make it real. |
| **Depth** | Complexity hidden behind a small interface. Prefer depth over width. |
| **Locality** | Real bugs hide in how a function is called, not inside a pure function extracted from it. |
| **Leverage** | How much behavior a caller gets from one interface. |
| **Backend** | The OS mechanism that enforces network isolation for an Action, or `advisory`. |
