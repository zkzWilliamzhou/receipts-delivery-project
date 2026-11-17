# Delivery: receipts

This zip contains the finished program, the research behind it, and the six
GitHub skill collections installed into the workspace.

## Run it

    cd receipts
    python3 -m receipts init
    python3 -m receipts demo
    python3 -m unittest discover -s tests -t . -v

No dependencies, no account, no API key, no daemon. Python 3.9+.

## What is here

| Path | Contents |
|---|---|
| `receipts/` | Program: CLI, 142 tests, docs, agent charters, 10-round review log, architecture report, CI |
| `research/` | Prior-art report and GitHub-star dynamics report with figures and CSVs |
| `third_party_skills/` | Six GitHub skill repositories (89 SKILL.md files), with their own licenses |
| `installed_skills_manifest.json` | Branch, file count and SKILL.md count per repository |
| `README_DELIVERY.md` | This file |

## What the program does

`receipts` runs a command in a copy-on-write workspace, writes a hash-chained,
HMAC-signed local receipt, and returns PASS, FAIL or UNVERIFIED for an agent's
natural-language claim. It also supports `apply`, `undo`, `replay`, `doctor`
and `verify --strict`. The novelty is an integration claim: binding policy,
execution, filesystem state and prose into one falsifiable record. See
`receipts/docs/PRIOR_ART_SUMMARY.md`.

## Verification at delivery

- 142 tests pass, zero skips.
- Golden behavior contract passes before and after the architecture refactor.
- Ten review rounds recorded in `receipts/docs/REVIEW_LOG.md`; each round has a
  command, a finding, a fix and a re-run.
- Independent audit findings in `receipts/docs/AUDIT_FINDINGS.md`.
- Offline three-act demo prints PASS, DENY and UNVERIFIED.
- `docs/ARCHITECTURE_REVIEW.html` is self-contained, offline, no CDN.

## Honest limits

- 105,000 GitHub stars is an aspiration, not a promise.
  `receipts/docs/STAR_STRATEGY.md` gives the researched odds and a realistic ceiling.
- The novelty claim is an integration claim, not a claim that any sandbox primitive is new.
- `unshare` and `advisory` do not contain absolute writes outside the workspace;
  `verify --strict` refuses PASS in those modes and non-strict PASS prints a warning.
- A second shell outside `receipts run`, a stolen HMAC key, or a fully compromised
  host can bypass the receipt. See `receipts/docs/THREAT_MODEL.md`.
- `bwrap` and `sandbox-exec` containment were not runtime-verified on the build host.
- The independent deep_research audit subagent returned no usable report; the boss
  executed the security-auditor charter directly. This is stated in the docs.

## Licenses

The `receipts/` program is MIT. Third-party skill repositories keep their own
licenses inside `third_party_skills/`.
