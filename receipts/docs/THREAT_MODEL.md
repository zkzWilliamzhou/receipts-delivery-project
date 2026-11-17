# Threat model

## What receipts protects

- An agent claims work it did not run. `verify` returns `UNVERIFIED` with `no_evidence`.
- An agent claims tests pass after a test failed. `verify` returns `FAIL` with `conflicting_evidence`.
- An agent claims tests pass, then edits a source file. `verify` returns `UNVERIFIED` with `stale_evidence`.
- Someone edits a receipt after the fact. `doctor` breaks the chain and `verify` returns `UNVERIFIED` with `ledger_corrupt`.
- Someone deletes the last N receipts. The `head` anchor no longer matches the last line.
- Someone appends a malformed line. `Ledger.append` runs `doctor` under the lock and refuses to extend a corrupt chain.
- An agent touches a protected path. The policy denies it and the receipt records the violation.
- An escaping symlink is excluded from the COW copy, recorded in the receipt, and blocks `apply` and `PASS`.
- A reviewer wants the exact change before it enters the real tree. `apply` and `undo` are explicit.

## Trust assumptions

- The wrapper is the only path the agent uses to run commands.
- `.receipts/key` stays 0600 and the user's account is not compromised.
- The clock is local and informational; wall time is not a security proof.
- The Python process itself is trusted to record what it observed.

## What it does not protect

- **Bypass.** An agent with a second shell outside `receipts run` produces no receipt. Capture completeness is the hard boundary, not the hash format. The report in `prior_art_receipts.md` says this plainly.
- **Privileged forgery.** A process that can write `.receipts/key`, the ledger, and `.receipts/head` can rebuild a valid chain. There is no TPM, hardware key, or remote witness in v1.
- **Host containment.** `unshare -n` isolates the network but does not stop absolute writes outside the COW workspace. `advisory` isolates neither. The receipt records `policy.capabilities` so the gap is visible, and a non-strict `PASS` carries a warning. `verify --strict` returns `UNVERIFIED` with `uncontained_execution` unless both capabilities are `true`. Only `bwrap` and `sandbox-exec` provide filesystem containment in v1.
- **Output honesty.** A command can print "all tests passed" and exit 0. The receipt proves the argv, exit code, output, and file delta; it does not prove the printed sentence is true. Structured test-report ingestion is a v2 item.
- **Malicious command content.** A command can flood stdout, embed secrets, or spawn background processes. Output is capped, secrets matching known patterns are redacted, and the child runs in its own process group which is killed on timeout. None of these is a complete defense.
- **Global state.** Package managers, sockets, mounted volumes, and device state outside the workspace are not snapshotted. `undo` restores tracked files only.
- **Windows.** Untested. Labeled unsupported in the README.

## Backend capability matrix

| Backend | `network_isolation` | `filesystem_containment` | Uncaptured side effects |
|---|---|---|---|
| `bwrap` | true | true | none from absolute writes inside the sandbox; host state outside the mount still depends on the kernel |
| `unshare` | true | false | absolute writes to host paths outside the workspace |
| `sandbox-exec` | true | true | none from writes outside the workspace and `/dev` |
| `advisory` | false | false | network paths that ignore proxy variables; absolute writes outside the workspace |

## Integrity modes

| Mode | Demonstrates | Does not demonstrate |
|---|---|---|
| Local hash chain | Later entries cannot change without breaking the chain | A privileged attacker did not rewrite the whole chain |
| HMAC with local key | The receipt was written by a holder of the key | The key was not read by the agent |
| Head anchor | The ledger was truncated | The head was not rewritten too |
| Remote witness (v2) | A third party saw the entry | The witness is honest and available |

## Reporting a vulnerability

See [SECURITY.md](../SECURITY.md). Do not open a public issue for a bypass that would let an agent obtain `PASS` without evidence.
