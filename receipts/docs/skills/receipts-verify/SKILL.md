---
name: receipts-verify
description: "Use before claiming that tests pass, a build succeeded, a bug is fixed, or any work is complete. Binds a natural-language claim to a local execution receipt and refuses to assert success without one."
---

# Receipts verify

Evidence before claims. Always.

## When to use

Before any of these sentences, or any paraphrase of them:
- "tests pass"
- "the build succeeds"
- "I fixed the bug"
- "done", "complete", "all green", "verified"

## Procedure

1. Run the work through the wrapper:
   ```console
   python3 -m receipts run -- python3 -m unittest discover -s tests -v
   ```
2. Bind the claim to the receipt:
   ```console
   python3 -m receipts verify "tests pass" --json
   ```
3. Read the verdict and the exit code. `0` PASS, `1` FAIL, `2` UNVERIFIED.
4. If the host has no containing backend, add `--strict` and treat `uncontained_execution` as a refusal to claim PASS. Read `warnings` even on a non-strict PASS.
5. Only then write the claim, and include the receipt id.

## Rules

- `UNVERIFIED` is not `PASS`. Say "I could not verify this" and name the reason.
- Do not run a command outside `receipts run` and then claim it was verified.
- Do not edit `.receipts/ledger.jsonl` to make a verdict change. `receipts doctor` will catch it and the verdict becomes `ledger_corrupt`.
- If `doctor` fails, stop. Do not report success on a broken ledger.
- `PASS` proves the recorded command exited with the recorded code and produced the recorded delta. It does not prove a printed sentence inside stdout is true.
- A later file change makes earlier test evidence stale. Re-run the test command.

## Example

```console
$ python3 -m receipts verify "tests pass" --json
{"verdict":"PASS","reason":"admissible_receipt","receipt":"r0000003","checks":[...]}
```

Created with the `anthropics/skills` `skill-creator` template.
