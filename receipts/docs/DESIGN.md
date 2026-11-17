# Design

## Intent

Bind an AI agent's natural-language work claim to an admissible local record of execution. A claim is never evidence. A receipt is.

## Architecture

Seven modules. Each has a deep interface: few entry points, substantial internal complexity hidden behind them.

| Module | Interface | Hides |
|---|---|---|
| `workspace.py` | `scan`, `create_cow`, `diff`, `materialize` | symlinks, object store, size caps, path validation, permissions |
| `objects.py` | `put_bytes`, `put_file`, `get`, `verify_all` | content-addressed layout, atomic writes, sha validation |
| `policy.py` | `load`, `evaluate`, `save`, `default` | default-deny rules, env allowlist, claim rules, hashing |
| `sandbox.py` | `Backend.resolve`, `Backend.wrap`, `capabilities` | bwrap / unshare / sandbox-exec / advisory fallback, containment capabilities, profiles |
| `ledger.py` | `append`, `all`, `doctor`, `find` | hash chain, HMAC, head anchor, flock, fsync, canonical JSON |
| `engine.py` | `run`, `apply`, `undo`, `replay` | orchestration of policy -> COW -> sandbox -> capture -> receipt |
| `claims.py` | `verify` | claim binding, staleness, integrity gate, conflict detection |

`cli.py` parses arguments and calls these. `redact.py`, `models.py`, `timeutil.py` are small shared utilities.

## Receipt schema (version 1)

One JSON object per line in `.receipts/ledger.jsonl`, keys sorted, no insignificant whitespace.

- `schema`: 1
- `seq`: monotonic integer starting at 1
- `id`: `r` + 7 zero-padded digits
- `prev`: `hash` of the previous receipt, or 64 zeros for the first
- `hash`: sha256 of canonical JSON of this receipt including `mac`
- `mac`: HMAC-SHA256 over canonical JSON of the receipt without `mac`, keyed by `.receipts/key` (32 random bytes, mode 0600)
- `started` / `ended` / `wall_ms`
- `action`: `argv`, `cwd`, `tag`, `env_allowlist`, `stdin_sha256`, `shell: false`
- `policy`: `version`, `hash`, `decision` (`allow`/`deny`), `reasons`, `network_mode`, `backend`
- `execution`: `exit_code`, `timed_out`, `backend`, `stdout`, `stderr`, `stdout_sha256`, `stderr_sha256`, `stdout_bytes`, `stderr_bytes`, `truncated`
- `workspace`: `before`, `after` state dicts, `added`, `removed`, `changed`, `protected_violations`, `skipped`
- `objects`: list of sha256 values needed to materialize `before` and `after`
- `integrity`: `{"chain": "sha256", "mac": "hmac-sha256", "head": "..." }`

State entry: `{"kind": "file"|"symlink"|"dir", "sha": <sha256 or null>, "mode": <int>, "size": <int>}`. Symlinks hash their target string, not the target file.

## Integrity rules

1. `canonical(obj)` = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
2. Append under `fcntl.flock` on `.receipts/ledger.lock`, write one line, `fsync`, update `.receipts/head` atomically with the new `hash`, `fsync` the directory.
3. `doctor` recomputes `mac`, `hash`, `prev` linkage for every line, then compares the last `hash` to `head`. Tampering, deletion of a middle line, and truncation all break it.
4. A privileged local attacker who rewrites both the ledger and the head can forge a chain. This is stated in the threat model, not hidden.

## Policy (default)

- `network.mode`: `deny`
- `deny_commands`: obvious network tools, plus destructive absolute-path forms
- `protected_paths`: `.receipts`, `.git`, `.env`, `*.pem`, `id_rsa`, `.ssh`
- `env_allowlist`: `PATH`, `LANG`, `LC_ALL`, `HOME`, `TMPDIR`, `PYTHONPATH`, `VIRTUAL_ENV`, `CI`, `GOFLAGS`, `NODE_PATH`, `CARGO_HOME`, `GOPATH`
- `max_wall_seconds`: 120, `max_output_bytes`: 262144, `max_file_bytes`: 67108864, `max_files`: 20000
- `claims`: rules for `tests pass`, `build succeeded`, `lint clean`, `no network access`

`HOME` and `TMPDIR` are rewritten to the COW workspace. No secret-bearing variables enter the child environment. Known secret patterns in stdout/stderr are redacted before the receipt is written.

## Backends and capabilities

`sandbox.Backend` is the deep module for host containment. It owns detection, command wrapping, and the capability record. Detection order:

1. `bwrap`: `--unshare-net`, `--ro-bind / /`, `--dev /dev`, `--tmpfs /tmp`, `--tmpfs /var/tmp`, workspace bind, `--die-with-parent`. Network isolation and filesystem containment.
2. `unshare -n`: network namespace only. Filesystem containment is `false`; absolute writes outside the workspace are not captured.
3. `sandbox-exec`: macOS profile that denies network and restricts writes to the workspace and `/dev`.
4. `advisory`: dead `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` at `127.0.0.1:1`. Both capabilities are `false`.

Every receipt stores `policy.backend` and `policy.capabilities` (`network_isolation`, `filesystem_containment`, `note`). `run` never claims a guarantee the backend does not provide. A failed backend attempt falls back to `advisory`, re-evaluates the policy, resets the COW workspace, and records the fallback.

Default-deny applies to `deny_commands` on every backend. A network-isolated backend does not turn `pip install` into an allowed command, because that command can still write outside the workspace.

## Claim verification

```
normalize claim -> bind to rule -> doctor(ledger) -> find candidate receipts
   -> policy hash -> unsafe symlinks -> strict containment -> exit code -> truncation
   -> protected paths -> network requirement -> staleness
   -> PASS | FAIL | UNVERIFIED
```

Reasons are machine-readable: `no_evidence`, `unbound_claim`, `ledger_corrupt`, `stale_evidence`, `policy_changed`, `unsafe_symlink`, `uncontained_execution`, `protected_path_violation`, `network_unverifiable`, `conflicting_evidence`, `output_truncated`. Exit codes 0/1/2.

`PASS` requires: chain intact, policy `allow`, matching command, unchanged policy hash, required exit code, output not truncated past the predicate, no protected-path violation, no escaping symlink, no later workspace change, and any rule-specific network requirement.

`verify --strict` adds one more gate: both `network_isolation` and `filesystem_containment` must be `true`, otherwise the verdict is `UNVERIFIED` with `uncontained_execution`. Non-strict `PASS` carries `warnings` describing every missing containment guarantee. The verdict object always includes `warnings`, even when empty.

## COW workspace

`create_cow(src, dst)` copies the project tree excluding `.receipts`, preserving symlinks and modes, skipping sockets and FIFOs, capping file count and size. The command runs with `cwd=dst`, `shell=False`, a fresh session, and a wall-clock timeout. `diff(before, after)` produces added/removed/changed lists. Changed and removed files are stored as objects from the `before` copy; changed and added files from the `after` copy.

`apply <id>` materializes `after` into the real root. `undo <id>` materializes `before`. Both refuse paths containing `..`, absolute paths, or a symlink in any parent component. `replay <id>` rebuilds `before` in a fresh COW directory, reruns the argv under the recorded policy, and compares exit code, output hashes, and the resulting delta.

## Builder's calls (mine, not the user's)

- Redaction patterns: a fixed list in `redact.py`, extensible through policy.
- Object store: `.receipts/objects/<sha[:2]>/<sha>`, mode 0600.
- Backend detection order as above; a failed backend attempt falls back and records why.
- Architecture report: self-contained HTML with inline CSS and SVG, no CDN, so it works offline.

## Acceptance criteria

- `python3 -m unittest discover -s tests -t . -v` passes with zero skips (142 tests at release).
- `receipts demo` shows PASS, a policy denial, and UNVERIFIED stale evidence, offline.
- `doctor` catches a flipped byte, a deleted line, and truncation.
- No `PASS` without an admissible receipt.
- `undo` restores a tree byte-for-byte after `apply`.
- Refactor changes no observable behavior: golden contract suite byte-identical before and after.
