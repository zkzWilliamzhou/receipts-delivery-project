# Star strategy

The user's target is 105k GitHub stars. I am not going to promise it.

## What the research found

`research/github_star_dynamics.md` in the delivery zip checked star counts through the GitHub API on 2026-11-10. Of 17 famous repos named in the brief, only nine were verified above 100k, and several of those are curated lists or learning platforms, not tools. `ripgrep` (69,961), `fzf` (84,119), `thefuck` (97,950), `jq` (36,094) and `cline` (71,496) were below 100k at the snapshot. GitHub reported 395 million public repositories; the report estimates 100k-star repos at roughly one in a million, and no more common than one in 100,000. For a focused AI-agent trust CLI the report puts a realistic ceiling at 25k-60k over two to four years, with 1k-10k as the likely niche outcome unless it becomes an integration standard.

Several search results in the first pass claimed 313,657 stars for `obra/superpowers` and 316,900 for `mattpocock/skills`. Those numbers are inconsistent across pages and were not used. Hype metrics do not survive a grilling.

## What we build toward anyway

The product decisions driven by the research are real even if the star count is not:

- One-sentence comprehension: "Your agent says tests pass. Make it show the receipt."
- Zero-config first run: Python 3.9+, no dependencies, no account, no API key.
- Offline replayable demo with a safe trace and a policy-violating trace, shipped in the repo.
- Falsifiable claims: exact inputs, expected verdicts, exit codes, and evidence files in `tests/` and `demo`.
- Permissive MIT license, `SECURITY.md`, `CONTRIBUTING.md`, CI on push.
- A documented evidence schema that another runtime can adopt, because the 100k path runs through integrations, not launch posts.

## Better metrics

Verified policy-enforced runs per month, completion rate of the verification loop, false PASS count, time from release to policy update, external integrations, outside contributors with merged code, and time to remediation. Stars are a lagging visibility metric, not a release gate.

## Launch order

1. Five to ten practitioners reproduce the three-act demo and try to break `PASS`.
2. Technical write-up that publishes a deliberately forged receipt and shows `doctor` catching it.
3. One Show HN post whose title names a failure scenario, not a category.
4. One narrow integration: a GitHub Action that gates a PR on `receipts verify`.
5. A vendor-neutral receipt schema proposal. This is the only path in the report that plausibly reaches the user's number.

No purchased stars, no engagement trading. A trust product that buys attention has already failed its own test.
