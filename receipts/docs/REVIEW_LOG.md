# Review log

Ten examination rounds. Every round records the command, the observed output or exit code, the finding, the root cause, the fix, and the re-run. A round with no new finding still lists the checks that produced none. Outputs below are quoted from commands actually run in the sandbox; longer runs were captured to `/tmp/green1.txt` … `/tmp/final_checks3.txt` and `/tmp/probes1.txt` … `/tmp/probes3.txt`.

## Round 1 — Functional correctness, TDD RED-GREEN

**Command.** `python3 -m unittest discover -s tests -t . -v`

**Before implementation.**

```
Ran 9 tests in 0.000s
FAILED (errors=9)
ModuleNotFoundError: No module named 'receipts'
```

All nine test modules failed to import. This is the expected RED: tests were written before production code.

**After first implementation.**

```
Ran 121 tests in 3.598s
FAILED (failures=1, errors=12)
```

**Findings.**
- `Engine` constructed without `init()` had no `store` attribute: eight errors in `test_engine`, `test_claims`, `test_security`.
- `Workspace.scan` did not put file bytes into the object store, so `materialize` raised `FileNotFoundError`: four errors in `test_workspace`.
- `test_doctor_detects_truncation_via_head` opened the ledger for writing before reading its first line, producing `IndexError`.
- `test_scan_skips_fifo_without_hanging` inspected a fresh `Workspace` instead of the one that scanned, so `skipped` was empty.

**Root cause.** Object-store ownership lived in `Engine.init()` but `run()` and `find()` could be called on a bare `Engine`; `scan()` computed hashes without storing the bytes; two tests had order bugs.

**Fix.** `Engine._ensure()` initializes on every entry point; `Workspace.scan` calls `store.put_bytes`; both test bugs corrected.

**Re-run.** `python3 -m unittest discover -s tests -t . -v` → `Ran 121 tests in 3.420s OK`.

## Round 2 — CLI contract and error handling

**Command.** `python3 tools/probes.py` (first run, `/tmp/probes1.txt`)

**Findings.**
- `verify ""` returned `UNVERIFIED unbound_claim` instead of rejecting an empty claim.
- `log --limit abc` returned exit 1 with a raw `invalid literal for int()` string.
- `show r0000001` printed a quoted `KeyError` string.
- Later, `/tmp/final_checks.txt` showed `--help` exited 2.

**Root cause.** `main()` passed empty words to the verifier, parsed `--limit` with bare `int()`, printed `str(KeyError)` verbatim, and treated `--help` as an unknown command.

**Fix.** Empty claims are rejected with an explicit message; `--limit` validates and reports a user-facing error; `KeyError` messages are unwrapped; `--help`, `-h` and `help` exit 0. The help fix landed in round 10.

**Re-run.** `/tmp/probes3.txt`: `verify ""` → `receipts: verify requires a non-empty claim`, exit 2; `log --limit abc` → `receipts: --limit requires an integer`, exit 2; `show r0000001` → `receipts: unknown receipt r0000001`, exit 1.

## Round 3 — Path traversal and symlink escape

**Command.** `python3 tools/probes.py` → `probe_symlink_escape`

**Before.**

```json
{"outside_file_created": true, "receipt_captured_write": false, "added": []}
```

**Finding.** An escaping symlink was copied into the COW workspace. A command writing through it created a file outside the project and the receipt recorded no delta.

**Root cause.** `create_cow` copied every symlink; `diff` compared symlink target hashes rather than file content; no unsafe-path list existed.

**Fix.** `Workspace.scan` marks escaping symlinks `unsafe`; `create_cow` skips them and records `cow_warnings`; `engine.run` stores `workspace.unsafe_symlinks`, filters them from the diff, refuses `apply`, and `ClaimVerifier` returns `UNVERIFIED` with `unsafe_symlink`. Regression: `tests/test_security.py::test_escaping_symlink_is_not_copied_and_blocks_pass`.

**Re-run.** `/tmp/probes2.txt`: `{"outside_file_created": false, "receipt_captured_write": false, "added": []}`.

## Round 4 — Secret hygiene and file permissions

**Command.** `python3 tools/probes.py` → `probe_secret_objects`

**Before.**

```json
{"secret_objects": ["e1db4ea1de51d89ed52b1aa45f4dace5152effc9d7813e762ff7a0b90069bb98"]}
```

**Finding.** A command writing `.env` stored the secret bytes as a recoverable object under `.receipts/objects/`.

**Root cause.** `Workspace.scan` and `capture` treated every file as storable, including protected paths.

**Fix.** `Workspace` receives `protected_fn=self.policy.is_protected`. `scan`, `capture`, `apply_diff` and `revert_diff` skip protected paths; `_write_changes` tolerates a missing object for a protected path. The receipt still records the file hash and `protected_violations`. Regression: `tests/test_security.py::test_protected_file_content_never_enters_object_store`.

**Re-run.** `/tmp/probes2.txt`: `{"secret_objects": []}`.

## Round 5 — Ledger integrity, atomicity, concurrency

**Command.** `python3 tools/probes.py` → `probe_corrupt_append`, `probe_two_processes`

**Before.**

```
== probe_corrupt_append
PROBE ERROR KeyError 'hash'
== probe_two_processes
{"doctor_ok": true, "count": 32, "process_errors": []}
```

**Finding.** Appending `{}` to `ledger.jsonl` made the next `run` crash with `KeyError: 'hash'`. A corrupt chain could be extended. Concurrent appends from four processes were sound (32 receipts, intact chain).

**Root cause.** `Ledger.all()` trusted every line as a receipt; `append()` never validated the existing chain before extending it.

**Fix.** `Ledger.all()` keeps only dict records with a string `hash`. `append()` acquires the flock, calls `doctor()`, and raises `ValueError("refusing to append to a corrupt ledger: ...")` when the chain is broken. Regressions: `tests/test_ledger.py::test_append_refuses_corrupt_ledger`, `tests/test_engine.py::test_run_refuses_corrupt_ledger`.

**Re-run.** `/tmp/probes3.txt`:

```json
{"doctor_before": false, "append_refused": true,
 "refusal": "refusing to append to a corrupt ledger: line 2: missing mac or hash",
 "doctor_after": false}
```

Concurrent probe unchanged: `{"doctor_ok": true, "count": 32, "process_errors": []}`.

## Round 6 — Claim semantics: false PASS, staleness, conflicts

**Command.** `python3 tools/probes.py` → `probe_policy_change`

**Before.** `{"before": "PASS", "after_policy_change": "PASS", "reason": "admissible_receipt"}`

**Finding.** Editing `policy.json` after a valid test receipt did not invalidate the verdict.

**Root cause.** The verifier never bound a receipt to the policy version that produced it.

**Fix.** Each receipt stores `policy.hash`; `ClaimVerifier` compares it with the current policy and returns `UNVERIFIED` with `policy_changed`. Stale-evidence and conflicting-evidence paths were already covered by `tests/test_claims.py` and remained green. Regression: `tests/test_claims.py::test_policy_changed_after_receipt_invalidates_pass`.

**Re-run.** `/tmp/probes2.txt`: `{"before": "PASS", "after_policy_change": "UNVERIFIED", "reason": "policy_changed"}`.

## Round 7 — Independent adversarial audit

**Command.** A `deep_research` audit subagent was requested. It returned no usable report; the first attempt left only the word `placeholder` in `docs/AUDIT_FINDINGS.md`. The boss executed the security-auditor charter directly: manual read of `receipts/*.py` plus `python3 tools/probes.py`.

**Findings** (full detail in `docs/AUDIT_FINDINGS.md`):
- F5: `Policy.evaluate` exempted `deny_commands` when a backend was network-isolated. `pip install` could run under `unshare -n` and write to host paths outside the COW workspace.
- F6: `unshare` provides network isolation but no filesystem containment; receipts did not disclose the gap and `verify` could return `PASS` without warning.
- F9: `sandbox-exec` allowed writes under `/private/tmp` instead of the workspace; `bwrap` did not isolate `/tmp` or `/var/tmp`.

**Root cause.** Backend semantics were encoded as string checks scattered across `Policy`, `Engine` and `ClaimVerifier`; no module owned both containment facts.

**Fix.** Default-deny now applies on every backend. `sandbox.Backend` records `capabilities` in each receipt. Non-strict `PASS` carries `warnings`; `verify --strict` returns `UNVERIFIED` with `uncontained_execution` unless both capabilities are true. `bwrap` adds `--dev /dev`, `--tmpfs /tmp`, `--tmpfs /var/tmp`; `sandbox-exec` generates a workspace-scoped profile. The `curl` denial reason text changed here; that is a safety fix, not part of round 9.

**Re-run.** `/tmp/green5.txt`: `Ran 140 tests ... OK`. `/tmp/probes3.txt` → `probe_strict_containment`:

```json
{"backend": "advisory", "normal": "PASS", "strict": "UNVERIFIED",
 "strict_reason": "uncontained_execution",
 "warnings": ["absolute writes outside the copy-on-write workspace are not captured",
              "network isolation is advisory only"]}
```

## Round 8 — Resource exhaustion, timeouts, binary and unicode output

**Command.** `python3 tools/probes.py` → `probe_large_output`

**Before.** `{"python_peak_mb": 38.2, "stored_cap_bytes": 262144}` for 20 MB of stdout.

**Finding.** `subprocess.communicate()` buffered the entire output in the Python process before capping it.

**Root cause.** Output capture happened in memory instead of streaming to disk.

**Fix.** `_popen_run` redirects stdout/stderr to `tempfile.TemporaryFile()`. `_read_capped` streams 64 KB blocks, hashes the whole stream, and keeps only `max_output_bytes`. Timeout still kills the process group and records `exit_code: None`. Regression: `tests/test_engine.py::test_large_output_is_hashed_without_loading_it_all`.

**Re-run.** `/tmp/probes2.txt`: `{"python_peak_mb": 1.0, "stored_cap_bytes": 262144}`.

## Round 9 — Architecture deepening, behavior preserved

**Command.** Read `mattpocock/skills/engineering/improve-codebase-architecture/SKILL.md`, `codebase-design`, `GLOSSARY.md`, `docs/adr/`. Scanned `sandbox.py` as the recently changed hot spot. Wrote `docs/ARCHITECTURE_REVIEW.html`. Refactored. Re-ran golden.

**Finding.** `sandbox.py` was shallow: a bare backend string forced `Policy`, `Engine` and `ClaimVerifier` to interpret the same name. Deleting the module would move complexity, not concentrate it.

**Fix.** `Backend` became a deep module with `resolve()`, `wrap()`, `capabilities()`, `network_isolation`, `filesystem_containment`. Module-level `resolve`, `detect`, `wrap`, `is_enforcing`, `capabilities` remain as thin adapters. `Engine`, `Policy` and `ClaimVerifier` now use the object. Two other candidates (Capture adapter, CLI registry) were surfaced and rejected in the HTML report with the deletion test.

**Behavior preservation.** `tests/fixtures/golden_transcript.txt` was captured before the pass and compared after. `python3 -m unittest tests.test_golden -v` → `Ran 1 test ... OK` before and after. The full suite after all fixes: `Ran 142 tests ... OK`. No verdict, exit code, receipt field or filesystem delta changed during the architecture pass.

## Round 10 — End-to-end release verification

**Command.** Final block captured in `/tmp/final_checks3.txt`:

```
python3 -m unittest discover -s tests -t . -v
python3 -m unittest tests.test_golden -v
python3 -m receipts demo
python3 -m receipts --help
python3 -m receipts doctor
python3 -m compileall -q receipts
python3 tools/probes.py
```

**Findings in the preceding `/tmp/final_checks.txt`.**
- `--help` exited 2.
- `doctor` on a fresh checkout returned 0 with `no ledger found`, so the CI ledger self-check was a no-op.

**Fix.** `--help` exits 0 with usage. `doctor` returns 1 when no ledger exists. `.github/workflows/ci.yml` now runs `python3 -m receipts init && python3 -m receipts doctor`. Regressions: `tests/test_cli.py::test_cli_help_exits_zero`, `tests/test_cli.py::test_cli_doctor_missing_ledger_exits_one`.

**Re-run** (`/tmp/final_checks3.txt` and `/tmp/probes3.txt`):

```
Ran 142 tests in 4.709s OK
Ran 1 test ... OK                      (golden)
demo EXIT=0
help EXIT=0
doctor-missing EXIT=1  receipts: no ledger found at /data/workspace/receipts
compile EXIT=0
probes EXIT=0
```

`probe_symlink_escape`: `outside_file_created: false`. `probe_secret_objects`: `secret_objects: []`. `probe_corrupt_append`: `append_refused: true`. `probe_policy_change`: `UNVERIFIED policy_changed`. `probe_large_output`: `1.0 MB` peak. `probe_two_processes`: `doctor_ok: true, count: 32`. `probe_strict_containment`: `strict: UNVERIFIED, uncontained_execution`.

**Checks that produced no new finding in this round.** `doctor` on an initialized ledger (`tests/test_cli.py::test_cli_doctor_exit_code`), `apply`/`undo` byte-for-byte restoration, `replay` match, redaction patterns, 0600 key and ledger permissions, offline three-act demo. All were already covered by the 142-test suite and remained green.

## Boss rejection record

- The first post-implementation run was rejected: 12 errors and 1 failure. Sent back to the implementer.
- The first probe run was rejected: symlink escape, secret object, corrupt-append crash, policy-change PASS, 38 MB output peak. Sent back to the security and implementer roles.
- The architecture candidate B and C were rejected: deletion test said complexity would move, not concentrate.
- The independent audit subagent returned a placeholder file. Rejected; the boss executed the charter directly and wrote the real report.
- The `--help` exit code and no-op CI doctor step were rejected in round 10 and fixed before the final run.

No round was recorded as complete without a re-run command and its exit code.
