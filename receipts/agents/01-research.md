# 01 Research agent

**Mission.** Establish whether the five-part function (isolated COW execution, tamper-evident receipt, claim verification, undo/replay, default-deny policy) exists as one tool, and establish what 105k GitHub stars actually requires.

**Inputs.** The user brief, the GitHub REST API, primary documentation for adjacent tools, GitHub Octoverse, project retrospectives.

**Outputs.** `prior_art_receipts.md`, `github_star_dynamics.md`, and a summary in `docs/PRIOR_ART_SUMMARY.md`.

**Acceptance criteria.**
- Names at least 20 adjacent systems with a source URL and states which of the five parts each lacks.
- Concedes where documentation could not be retrieved.
- Narrows the novelty claim to an integration claim.
- Flags every uncertain statistic instead of inventing precision.
- Gives a blunt verdict on star odds, including a realistic ceiling for this category.

**Rejection triggers.** "No tool does this" without named alternatives. Uncited star counts. A report that reads like launch copy. SEO-spam numbers copied from a search snippet.

**Boss note.** This agent ran as a `deep_research` subagent. Its star report returned a path under `dr:github_star_dynamics/`; the boss read the actual file and corrected the summary from that file, not from the agent's self-report.
