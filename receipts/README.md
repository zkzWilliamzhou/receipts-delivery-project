# receipts

**Your agent says "tests pass". Make it show the receipt.**

`receipts` runs a shell command in a copy-on-write workspace, records what the command actually did in a tamper-evident local ledger, and checks an agent's sentence against that ledger. It does not trust the sentence.

```console
$ receipts run -- python3 -m unittest
[r0000003] allow  exit=0  412ms  3 files changed

$ receipts verify "tests pass"
PASS  admissible_receipt  r0000003

$ receipts verify "tests pass"      # after someone edits a source file
UNVERIFIED  stale_evidence  r0000005 changed src/app.py after r0000003
```

Three outcomes, no fourth: `PASS`, `FAIL`, `UNVERIFIED`. A claim with no receipt never becomes `PASS`.

## Install

Python 3.9+, no dependencies, no account, no API key, no daemon.

```console
git clone https://github.com/YOUR_ORG/receipts
cd receipts
python3 -m receipts init
python3 -m receipts demo
```

Or run the module entry point from a checkout:

```console
python3 -m receipts --help
```

## The loop

```
agent wants to run a command
        |
        v
receipts run -- <command>     policy decision -> COW workspace -> capture
        |
        v
receipt (hash-chained, HMAC, pre/post file hashes, redacted output)
        |
        +--> receipts apply <id>   take the change into your real tree
        +--> receipts undo   <id>   put the tree back
        +--> receipts replay <id>  run it again and compare
        +--> receipts verify "<claim>"   PASS / FAIL / UNVERIFIED
```

Commands:

| Command | What it does |
|---|---|
| `init` | Create `.receipts/`, a 0600 HMAC key, and a default-deny policy |
| `run -- CMD` | Execute CMD in a copy-on-write workspace, append a receipt |
| `verify "CLAIM"` | Bind the claim to receipts and decide PASS / FAIL / UNVERIFIED |
| `verify "CLAIM" --strict` | Require full containment before any PASS |
| `log` / `show` / `diff` | Inspect the ledger |
| `apply` / `undo` | Move a recorded delta into or out of the real tree |
| `replay` | Re-execute under the recorded policy and compare |
| `doctor` | Recompute every MAC, hash, and chain link; check head anchoring |
| `policy` | Show or edit the default-deny policy |
| `demo` | Offline three-act demo: PASS, policy denial, stale evidence |

Exit codes for `verify`: `0` PASS, `1` FAIL, `2` UNVERIFIED. CI can gate on them.

## What this is not

`receipts` is an evidence and rollback tool. It is **not** a universal kernel security sandbox. A malicious process can bypass it by running outside the wrapper or reading the HMAC key. Every receipt records the backend that actually ran and what that backend contains:

| Backend | Network isolation | Filesystem containment |
|---|---|---|
| `bwrap` | yes | root read-only, workspace and temp dirs writable |
| `unshare -n` | yes | no; absolute writes outside the workspace are not captured |
| `sandbox-exec` | yes | writes restricted to the workspace and `/dev` |
| `advisory` | dead proxy only | none |

On a host with no containing backend, `verify "tests pass"` can still return `PASS` for the recorded command, but it prints a warning that absolute writes outside the copy-on-write workspace are not captured. `verify --strict` refuses `PASS` in that case and returns `UNVERIFIED` with `uncontained_execution`. Every receipt carries a `capabilities` object so a reader can check the guarantee without trusting the README. See [THREAT_MODEL.md](docs/THREAT_MODEL.md).

It also does not prove a command is honest about its own output. It proves that a specific argv ran, exited with a specific code, and produced a specific filesystem delta. Structured test-result parsing is a v2 item.

## Why it exists

Agents report work in prose. Prose has no exit code. Prior-art research found tracing platforms, editor checkpoints, sandboxes, backup tools, and provenance frameworks covering parts of this, but no single local tool that binds policy, execution, filesystem state, and a natural-language claim into one falsifiable record. The claim is an **integration claim**, not a claim of new primitives. See [docs/BRAINSTORM.md](docs/BRAINSTORM.md) and `docs/PRIOR_ART_SUMMARY.md`.

## Documentation

- [Design](docs/DESIGN.md) and [threat model](docs/THREAT_MODEL.md)
- [Brainstorm and self-grilling](docs/BRAINSTORM.md)
- [Plan](docs/PLAN.md), [workflow](docs/WORKFLOW.md), [agent charters](agents/README.md)
- [Review log](docs/REVIEW_LOG.md) and [architecture review](docs/ARCHITECTURE_REVIEW.html)
- [Star strategy](docs/STAR_STRATEGY.md) and [installed skills](docs/INSTALLED_SKILLS.md)
- [Contributing](CONTRIBUTING.md), [security policy](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
