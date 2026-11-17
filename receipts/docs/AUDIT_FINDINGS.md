# Independent audit findings

**Execution note.** An independent `deep_research` audit subagent was requested but returned no usable report (the first attempt left a placeholder file). The boss executed the security-auditor charter directly: a manual read of every file in `receipts/` plus the adversarial harness `tools/probes.py`. All outputs below come from commands that were actually run in the sandbox. The harness outputs are preserved in `docs/REVIEW_LOG.md`.

**Scope.** `receipts/*.py`, `tests/*.py`, `tools/probes.py` inside the project.

## Findings

### F1 — Escaping symlink wrote outside the COW workspace (High)

**Where.** `workspace.py` `create_cow`, `engine.py` `run`.

**Reproduction.** `python3 tools/probes.py` → `probe_symlink_escape` before the fix:

```json
{"outside_file_created": true, "receipt_captured_write": false, "added": []}
```

A symlink at `project/escape` pointing outside the project was copied into the COW directory. A command writing `escape/pwned.txt` created the file outside the project, and the receipt recorded no delta.

**Fix.** `Workspace.scan` marks symlinks whose real target escapes the base as `unsafe`; `create_cow` skips them and records `cow_warnings`; `engine.run` stores `workspace.unsafe_symlinks`, filters those paths out of the diff, refuses `apply`, and `ClaimVerifier` returns `UNVERIFIED` with `unsafe_symlink`. Regression: `tests/test_security.py::test_escaping_symlink_is_not_copied_and_blocks_pass`.

### F2 — Protected-path content leaked into the object store (High)

**Where.** `workspace.py` `scan`, `capture`.

**Reproduction.** `probe_secret_objects` before the fix:

```json
{"secret_objects": ["e1db4ea1de51d89ed52b1aa45f4dace5152effc9d7813e762ff7a0b90069bb98"]}
```

A command that wrote `.env` with `SUPER_SECRET_VALUE_123` had that content hashed and stored as a recoverable object under `.receipts/objects/`.

**Fix.** `Workspace` receives `protected_fn` from `Policy.is_protected`. `scan`, `capture`, `apply_diff`, and `revert_diff` skip protected paths; `_write_changes` tolerates a missing object for a protected path. The state still records the file hash, so the violation is visible without storing the bytes. Regression: `tests/test_security.py::test_protected_file_content_never_enters_object_store`.

### F3 — A malformed ledger line crashed `run` and could be extended (High)

**Where.** `ledger.py` `all`, `append`; `engine.py` `run`.

**Reproduction.** `probe_corrupt_append` before the fix: `PROBE ERROR KeyError 'hash'`. Appending `{}` to `ledger.jsonl` made the next append read the malformed line as a receipt and dereference `record["hash"]`.

**Fix.** `Ledger.all()` keeps only dict records with a string `hash`. `append()` acquires the lock, calls `doctor()`, and raises `ValueError("refusing to append to a corrupt ledger: ...")` if the chain is broken. `Engine.run` propagates the refusal. Regression: `tests/test_ledger.py::test_append_refuses_corrupt_ledger`, `tests/test_engine.py::test_run_refuses_corrupt_ledger`.

### F4 — Changing the policy did not invalidate an earlier PASS (Medium)

**Where.** `claims.py` `verify`.

**Reproduction.** `probe_policy_change` before the fix: `{"before": "PASS", "after_policy_change": "PASS"}`.

**Fix.** Each receipt stores `policy.hash`. `ClaimVerifier` compares it with the current policy and returns `UNVERIFIED` with `policy_changed`. Regression: `tests/test_claims.py::test_policy_changed_after_receipt_invalidates_pass`.

### F5 — Network commands were allowed under an enforcing backend (High)

**Where.** `policy.py` `evaluate` (old lines 114-121).

**Reproduction.** Code review: the `deny_commands` loop ran only when `not is_enforcing(backend)`. Under `unshare -n`, `pip install` or `npm install` could run with network blocked but still write to host paths outside the COW workspace.

**Fix.** Default-deny applies on every backend. An enforcing backend no longer turns `deny_commands` into allowed commands. `tests/test_policy.py::test_evaluate_denies_network_command_even_with_enforcing_backend` covers it. `bwrap` and `sandbox-exec` profiles now also contain absolute writes.

### F6 — Containment guarantees were not disclosed; strict verification did not exist (High)

**Where.** `sandbox.py`, `engine.py`, `claims.py`.

**Reproduction.** On this host `unshare -n` works, so `Backend.resolve()` returns `unshare`. That provides network isolation but no filesystem containment. Before the fix the receipt recorded only the backend name, and `verify "tests pass"` returned `PASS` with no indication that absolute writes outside the workspace were uncaptured.

**Fix.** `sandbox.Backend` owns `capabilities` (`network_isolation`, `filesystem_containment`, `note`). Every receipt stores them under `policy.capabilities`. Non-strict `PASS` carries `warnings`; `verify --strict` returns `UNVERIFIED` with `uncontained_execution` unless both capabilities are true. `probe_strict_containment` after the fix:

```json
{"backend": "advisory", "normal": "PASS", "strict": "UNVERIFIED",
 "strict_reason": "uncontained_execution",
 "warnings": ["absolute writes outside the copy-on-write workspace are not captured",
              "network isolation is advisory only"]}
```

Regressions: `tests/test_backend.py`, `tests/test_claims.py::test_strict_mode_blocks_pass_on_advisory_backend`, `tests/test_claims.py::test_pass_on_advisory_carries_containment_warning`.

### F7 — 20 MB of stdout consumed ~38 MB of Python heap (Medium)

**Where.** `engine.py` `_popen_run` (old `subprocess.communicate`).

**Reproduction.** `probe_large_output` before the fix: `{"python_peak_mb": 38.2}`.

**Fix.** Subprocess stdout/stderr go to `tempfile.TemporaryFile()`. `_read_capped` streams through 64 KB blocks, hashes the entire stream, and keeps only `max_output_bytes` in memory. After the fix: `{"python_peak_mb": 1.0, "stored_cap_bytes": 262144}`. Regression: `tests/test_engine.py::test_large_output_is_hashed_without_loading_it_all`.

### F8 — CLI edge cases were sloppy (Low)

**Where.** `cli.py`.

**Reproduction.** `probe_cli` before the fix: `verify ""` returned `UNVERIFIED unbound_claim`; `log --limit abc` returned a raw `invalid literal for int()` error; `--help` exited 2; `show r0000001` printed a quoted `KeyError` string.

**Fix.** Empty claims are rejected with an explicit message, `--limit` is validated, `--help`/`-h`/`help` exit 0, `KeyError` messages are unwrapped. `--strict` and `--json` are documented in usage. Regressions in `tests/test_cli.py`.

### F9 — Sandbox profiles were too permissive or incomplete (Low, platform-specific)

**Where.** `sandbox.py` `wrap`.

**Reproduction.** Manual review: the macOS `sandbox-exec` profile allowed writes under `/private/tmp` rather than the workspace; the `bwrap` invocation did not isolate `/tmp` or `/var/tmp`, so absolute writes to those paths could reach the host.

**Fix.** `sandbox-exec` now generates a profile per workspace allowing writes only inside it and `/dev`; `bwrap` adds `--dev /dev`, `--tmpfs /tmp`, and `--tmpfs /var/tmp` on top of a read-only root. These paths are not exercised on this Linux host (no `bwrap`, no macOS), so the fix is documented rather than claimed as runtime-verified here. `tests/test_backend.py` checks the constructed argv.

## Checks that found no defect

| Check | Command / path | Result |
|---|---|---|
| Hash chain, MAC, head anchor | `tests/test_ledger.py`, `Ledger.doctor` | 12 tests pass; tampering, deletion and truncation all detected |
| Concurrent appends | `probe_two_processes` | `{"doctor_ok": true, "count": 32, "process_errors": []}` |
| Timeout and process-group kill | `tests/test_engine.py::test_run_timeout_kills_process_group` | timed out in <6 s, exit recorded as `None` |
| `shell=False` | `tests/test_security.py::test_shell_false_prevents_command_substitution` | `$(touch ...)` printed literally, no file created |
| Secret redaction | `tests/test_security.py::test_secret_patterns_are_redacted` | six patterns redacted, plain text unchanged |
| Path traversal in `materialize` | `tests/test_workspace.py` | `..`, absolute paths and symlink parents rejected |
| Golden behavior contract | `python3 -m unittest tests.test_golden -v` | `Ran 1 test ... OK` before and after the architecture refactor |

## Residual risks (accepted, documented)

- A second shell outside `receipts run` produces no receipt at all. Capture completeness is the hard boundary.
- A privileged local attacker who can rewrite `key`, `ledger.jsonl` and `head` can rebuild a valid chain.
- `unshare` and `advisory` do not contain absolute writes. `--strict` refuses PASS; non-strict PASS warns.
- A command can print a false success sentence and exit 0. Structured test-result parsing is v2.
- `sandbox-exec` and `bwrap` containment were not runtime-verified on this host.
