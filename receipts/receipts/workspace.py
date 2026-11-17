"""Copy-on-write workspace: state capture, diffing, object capture, safe restoration."""
import os
import shutil
import stat

from .models import sha256_bytes, sha256_text

EXCLUDED_DIRS = frozenset({
    ".receipts", "__pycache__", ".pytest_cache", ".mypy_cache", ".git",
    ".tox", ".venv", "node_modules",
})
EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def _rel(path, base):
    return os.path.relpath(path, base).replace(os.sep, "/")


class Workspace:
    """One deep interface over filesystem state.

    Callers deal in State dicts and diffs. Symlink handling, size caps, path
    validation, protected-path object skipping and permission restoration stay
    behind the seam.
    """

    def __init__(self, root, store, max_file_bytes=64 * 1024 * 1024,
                 max_files=20000, protected_fn=None):
        self.root = os.path.abspath(root)
        self.store = store
        self.max_file_bytes = max_file_bytes
        self.max_files = max_files
        self.protected_fn = protected_fn or (lambda rel: False)
        self.skipped = []
        self.unsafe_symlinks = []
        self.cow_warnings = []

    def scan(self, directory=None):
        base = os.path.abspath(directory or self.root)
        self.skipped = []
        self.unsafe_symlinks = []
        state = {}
        count = [0]

        def walk(current):
            with os.scandir(current) as it:
                entries = sorted(it, key=lambda e: e.name)
            for entry in entries:
                rel = _rel(entry.path, base)
                if rel.split("/")[0] in EXCLUDED_DIRS:
                    continue
                if entry.name.endswith(EXCLUDED_SUFFIXES):
                    continue
                if entry.is_symlink():
                    target = os.readlink(entry.path)
                    resolved = os.path.realpath(entry.path)
                    safe = os.path.commonpath([resolved, base]) == base
                    item = {
                        "kind": "symlink", "target": target,
                        "sha": sha256_text(target), "mode": 0, "size": len(target),
                    }
                    if not safe:
                        item["unsafe"] = True
                        self.unsafe_symlinks.append(rel)
                    state[rel] = item
                    count[0] += 1
                elif entry.is_dir(follow_symlinks=False):
                    state[rel] = {
                        "kind": "dir", "sha": None,
                        "mode": stat.S_IMODE(os.stat(entry.path).st_mode), "size": 0,
                    }
                    walk(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    if count[0] >= self.max_files:
                        self.skipped.append(rel)
                        continue
                    info = os.stat(entry.path)
                    if info.st_size > self.max_file_bytes:
                        self.skipped.append(rel)
                        continue
                    with open(entry.path, "rb") as f:
                        data = f.read()
                    if not self.protected_fn(rel):
                        self.store.put_bytes(data)
                    state[rel] = {
                        "kind": "file", "sha": sha256_bytes(data),
                        "mode": stat.S_IMODE(info.st_mode), "size": info.st_size,
                    }
                    count[0] += 1
                else:
                    self.skipped.append(rel)

        walk(base)
        return state

    def create_cow(self, dst):
        os.makedirs(dst, exist_ok=True)
        self.cow_warnings = []
        self._copy_tree(self.root, dst)
        return dst

    def _copy_tree(self, src, dst):
        with os.scandir(src) as it:
            entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if entry.name in EXCLUDED_DIRS or entry.name.endswith(EXCLUDED_SUFFIXES):
                continue
            rel = _rel(entry.path, self.root)
            target = os.path.join(dst, entry.name)
            if entry.is_symlink():
                resolved = os.path.realpath(entry.path)
                if os.path.commonpath([resolved, self.root]) != self.root:
                    self.cow_warnings.append(rel)
                    continue
                if not os.path.lexists(target):
                    os.symlink(os.readlink(entry.path), target)
            elif entry.is_dir(follow_symlinks=False):
                os.makedirs(target, exist_ok=True)
                shutil.copymode(entry.path, target)
                self._copy_tree(entry.path, target)
            elif entry.is_file(follow_symlinks=False):
                if os.stat(entry.path).st_size > self.max_file_bytes:
                    continue
                shutil.copy2(entry.path, target, follow_symlinks=False)

    def diff(self, before, after):
        keys = sorted(set(before) | set(after))
        added = [k for k in keys if k not in before]
        removed = [k for k in keys if k not in after]
        changed = [k for k in keys
                   if k in before and k in after
                   and (before[k].get("sha") != after[k].get("sha")
                        or before[k].get("mode") != after[k].get("mode"))]
        return {"added": added, "removed": removed, "changed": changed}

    def capture(self, before, after, before_dir, after_dir, diff):
        """Store bytes for everything a later apply/undo would need.

        Protected paths are never written to the object store, even when a
        command created them. Their hash still appears in the state.
        """
        shas = set()
        for rel in diff["removed"] + diff["changed"]:
            if self.protected_fn(rel):
                continue
            entry = before.get(rel)
            if entry and entry["kind"] == "file":
                path = os.path.join(before_dir, rel)
                if os.path.isfile(path) and not os.path.islink(path):
                    shas.add(self.store.put_file(path))
        for rel in diff["added"] + diff["changed"]:
            if self.protected_fn(rel):
                continue
            entry = after.get(rel)
            if entry and entry["kind"] == "file":
                path = os.path.join(after_dir, rel)
                if os.path.isfile(path) and not os.path.islink(path):
                    shas.add(self.store.put_file(path))
        return sorted(shas)

    def _validate_paths(self, paths, target):
        target = os.path.abspath(target)
        for rel in paths:
            if not isinstance(rel, str) or not rel:
                raise ValueError("invalid state path: %r" % (rel,))
            if rel.startswith("/") or "\\" in rel:
                raise ValueError("absolute or windows path rejected: %s" % rel)
            parts = rel.split("/")
            if any(p in ("", ".", "..") for p in parts):
                raise ValueError("traversal rejected: %s" % rel)
            if parts[0] in EXCLUDED_DIRS:
                raise ValueError("protected store path rejected: %s" % rel)
            parent = os.path.realpath(os.path.dirname(os.path.join(target, rel)))
            if os.path.commonpath([parent, target]) != target:
                raise ValueError("symlink parent escapes workspace: %s" % rel)

    def materialize(self, target, state, remove_extra=False):
        """Write a full State into target. Used for replay setup and restoration."""
        target = os.path.abspath(target)
        self._validate_paths(state.keys(), target)
        changes = dict(state)
        if remove_extra:
            for rel in self._iter_target_files(target):
                if rel not in state:
                    changes[rel] = None
        self._write_changes(target, changes)

    def _iter_target_files(self, target):
        found = []
        for current, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for name in files:
                if name.endswith(EXCLUDED_SUFFIXES):
                    continue
                rel = _rel(os.path.join(current, name), target)
                if rel.split("/")[0] not in EXCLUDED_DIRS:
                    found.append(rel)
        return found

    def apply_diff(self, target, before, after, diff):
        changes = {}
        for rel in diff["removed"]:
            if not self.protected_fn(rel):
                changes[rel] = None
        for rel in diff["added"] + diff["changed"]:
            if not self.protected_fn(rel):
                changes[rel] = after[rel]
        self._write_changes(target, changes)

    def revert_diff(self, target, before, after, diff):
        changes = {}
        for rel in diff["added"]:
            if not self.protected_fn(rel):
                changes[rel] = None
        for rel in diff["removed"] + diff["changed"]:
            if not self.protected_fn(rel):
                changes[rel] = before[rel]
        self._write_changes(target, changes)

    def _write_changes(self, target, changes):
        target = os.path.abspath(target)
        self._validate_paths(changes.keys(), target)
        for rel in sorted(changes, key=lambda r: (r.count("/"), r)):
            entry = changes[rel]
            path = os.path.join(target, rel)
            if entry is None:
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    try:
                        os.rmdir(path)
                    except OSError:
                        pass
                continue
            if entry["kind"] == "dir":
                os.makedirs(path, exist_ok=True)
                continue
            if entry["kind"] == "file":
                try:
                    data = self.store.get(entry["sha"])
                except FileNotFoundError:
                    if self.protected_fn(rel):
                        continue
                    raise
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.lexists(path):
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            if entry["kind"] == "file":
                with open(path, "wb") as f:
                    f.write(data)
                os.chmod(path, entry["mode"] or 0o644)
            else:
                os.symlink(entry["target"], path)
