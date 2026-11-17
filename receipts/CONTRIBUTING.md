# Contributing

## Setup

```console
git clone https://github.com/YOUR_ORG/receipts
cd receipts
python3 -m unittest discover -s tests -v
```

No dependencies, no virtual environment, no build step.

## Rules

1. Write the test first. Run it and watch it fail. Name the production change that would make it pass before you write it.
2. Keep the standard library only.
3. `verify` must never return `PASS` without an admissible receipt. Any change that relaxes this needs an ADR.
4. Update `docs/THREAT_MODEL.md` when you change a trust boundary.
5. Run `python3 -m unittest discover -s tests -v` and `python3 -m receipts demo` before a PR. Paste both outputs in the PR description.
6. A claim that tests pass without the command output is not a contribution.

## Good first issues

- A structured parser for one test runner (pytest JSON, Go `test -json`).
- A GitHub Action that gates a PR on `receipts verify`.
- A backend for one more sandbox primitive.

## Design decisions

Read `docs/adr/` before proposing a change to the verdict logic, the receipt schema, or the default policy.
