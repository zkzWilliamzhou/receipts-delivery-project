"""Backend value object: detection, containment capabilities, command wrapping.

A Backend owns what the host can actually enforce. Callers deal with one
interface instead of scattering backend-name checks across Policy, Engine and
ClaimVerifier.
"""
import os
import shutil
import subprocess
import sys
import threading

BWRAP = "bwrap"
UNSHARE = "unshare"
SANDBOX_EXEC = "sandbox-exec"
ADVISORY = "advisory"
NONE = "none"

ENFORCING = frozenset({BWRAP, UNSHARE, SANDBOX_EXEC})

CAPABILITIES = {
    BWRAP: {
        "network_isolation": True,
        "filesystem_containment": True,
        "note": "network namespace; root read-only; workspace and temp dirs writable",
    },
    UNSHARE: {
        "network_isolation": True,
        "filesystem_containment": False,
        "note": "network namespace only; absolute writes outside the workspace are not captured",
    },
    SANDBOX_EXEC: {
        "network_isolation": True,
        "filesystem_containment": True,
        "note": "network denied; writes restricted to the workspace and /dev",
    },
    ADVISORY: {
        "network_isolation": False,
        "filesystem_containment": False,
        "note": "dead proxy only; no kernel containment",
    },
    NONE: {
        "network_isolation": False,
        "filesystem_containment": False,
        "note": "no backend recorded",
    },
}

_cache = None
_cache_lock = threading.Lock()


def capabilities(backend):
    """Return a fresh capability dict for a backend name or Backend object."""
    name = backend.name if isinstance(backend, Backend) else backend
    if name not in CAPABILITIES:
        raise ValueError("unknown backend: %r" % (name,))
    return dict(CAPABILITIES[name])


def is_enforcing(backend):
    """True when the backend provides real network isolation."""
    if isinstance(backend, Backend):
        return backend.network_isolation
    return CAPABILITIES.get(backend, CAPABILITIES[NONE])["network_isolation"]


def _probe(argv):
    try:
        result = subprocess.run(argv, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=3)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class Backend:
    """Deep interface over one host containment mechanism."""

    def __init__(self, name):
        if name not in CAPABILITIES:
            raise ValueError("unknown backend: %r" % (name,))
        self.name = name
        self._caps = CAPABILITIES[name]

    @property
    def network_isolation(self):
        return self._caps["network_isolation"]

    @property
    def filesystem_containment(self):
        return self._caps["filesystem_containment"]

    def capabilities(self):
        return dict(self._caps)

    def is_enforcing(self):
        return self.network_isolation

    def wrap(self, argv, workspace):
        argv = list(argv)
        if self.name == BWRAP:
            return ["bwrap", "--unshare-net", "--ro-bind", "/", "/",
                    "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/var/tmp",
                    "--bind", workspace, workspace, "--chdir", workspace,
                    "--die-with-parent", "--"] + argv
        if self.name == UNSHARE:
            return ["unshare", "-n", "--"] + argv
        if self.name == SANDBOX_EXEC:
            profile = os.path.join(os.path.dirname(workspace), "network-deny.sb")
            escaped = workspace.replace("\\", "\\\\").replace('"', '\\"')
            text = """(version 1)
(deny default)
(allow process-exec)
(allow file-read*)
(allow file-write* (subpath "%s"))
(allow file-write* (subpath "/dev"))
(allow sysctl-read)
(deny network*)
""" % escaped
            with open(profile, "w", encoding="utf-8") as f:
                f.write(text)
            return ["sandbox-exec", "-f", profile, "--"] + argv
        return argv

    @classmethod
    def resolve(cls):
        """Return a Backend verified to work on this host, cached per process."""
        global _cache
        with _cache_lock:
            if _cache is not None:
                return _cache
            if shutil.which("bwrap") and _probe(
                    ["bwrap", "--unshare-net", "--ro-bind", "/", "/",
                     "--die-with-parent", "--", "true"]):
                _cache = cls(BWRAP)
            elif shutil.which("unshare") and _probe(["unshare", "-n", "--", "true"]):
                _cache = cls(UNSHARE)
            elif sys.platform == "darwin" and shutil.which("sandbox-exec"):
                _cache = cls(SANDBOX_EXEC)
            else:
                _cache = cls(ADVISORY)
            return _cache


def resolve():
    return Backend.resolve().name


def detect():
    return resolve()


def wrap(argv, backend, workspace):
    if isinstance(backend, Backend):
        return backend.wrap(argv, workspace)
    return Backend(backend).wrap(argv, workspace)
