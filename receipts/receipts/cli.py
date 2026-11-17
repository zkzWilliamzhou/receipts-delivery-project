"""Command line interface. Exit codes are part of the contract."""
import json
import os
import sys

from .claims import ClaimVerifier, FAIL, PASS
from .demo import run_demo
from .engine import Engine
from .ledger import Ledger
from .models import canonical
from .policy import Policy

USAGE = """usage: receipts <command> [options]

commands:
  init                         create .receipts/ with a default-deny policy
  run [--tag NAME] -- CMD       run CMD in a copy-on-write workspace, append a receipt
  verify "CLAIM" [--json] [--strict]
                               PASS / FAIL / UNVERIFIED (exit 0 / 1 / 2)
                               --strict requires full containment
  log [--limit N]              list receipts
  show ID                      print one receipt
  diff ID                      print the recorded filesystem delta
  apply ID                     apply a recorded delta to the real tree
  undo ID                      restore the pre-action tree
  replay ID                    re-execute and compare
  doctor                       verify every mac, hash and chain link
  policy show|set KEY VALUE    inspect or edit the policy
  demo                         offline three-act demonstration

global:
  --root PATH                  operate on a different project directory
"""


def _usage(code=2):
    print(USAGE, end="")
    return code


def _fail(message, code=2):
    print("receipts: %s" % message, file=sys.stderr)
    return code


def _engine(root, command):
    engine = Engine(root)
    if command == "doctor" and not os.path.isdir(os.path.join(root, ".receipts")):
        return engine, True
    engine.init()
    return engine, False


def _parse_run(rest):
    if "--" not in rest:
        return None, None, "run requires '--' before the command"
    index = rest.index("--")
    options = rest[:index]
    command = rest[index + 1:]
    if not command:
        return None, None, "run requires a command after '--'"
    tag = None
    if "--tag" in options:
        pos = options.index("--tag")
        if pos + 1 >= len(options):
            return None, None, "--tag requires a value"
        tag = options[pos + 1]
    return command, tag, None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return _usage()
    if argv[0] in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    root = os.getcwd()
    if argv[0] == "--root":
        if len(argv) < 2:
            return _fail("--root requires a path")
        root = argv[1]
        argv = argv[2:]
    if not argv:
        return _usage()
    command, rest = argv[0], argv[1:]

    if command == "demo":
        print(run_demo())
        return 0
    if command == "init":
        Engine(root).init()
        print("receipts initialized at %s" % os.path.join(root, ".receipts"))
        return 0
    if command not in ("run", "verify", "log", "show", "diff", "apply",
                       "undo", "replay", "doctor", "policy"):
        return _usage()

    engine, missing = _engine(root, command)
    if missing:
        print("receipts: no ledger found at %s" % root, file=sys.stderr)
        return 1

    try:
        if command == "run":
            cmd, tag, error = _parse_run(rest)
            if error:
                return _fail(error)
            receipt = engine.run(cmd, tag=tag)
            print("[%s] %s exit=%s %dms" % (
                receipt["id"], receipt["policy"]["decision"],
                receipt["execution"]["exit_code"], receipt["wall_ms"]))
            return 0

        if command == "verify":
            as_json = "--json" in rest
            strict = "--strict" in rest
            words = [w for w in rest
                     if w not in ("--json", "--strict") and w.strip()]
            if not words:
                return _fail("verify requires a non-empty claim")
            result = ClaimVerifier(engine.ledger, engine.policy).verify(
                " ".join(words), strict=strict)
            if as_json:
                print(canonical(result))
            else:
                print("%s  %s  %s" % (result["verdict"], result["reason"] or "",
                                      result["receipt"] or ""))
                for warning in result.get("warnings", []):
                    print("warning: %s" % warning)
            return {PASS: 0, FAIL: 1}.get(result["verdict"], 2)

        if command == "log":
            limit = 20
            if "--limit" in rest:
                pos = rest.index("--limit")
                if pos + 1 >= len(rest):
                    return _fail("--limit requires an integer")
                try:
                    limit = int(rest[pos + 1])
                except ValueError:
                    return _fail("--limit requires an integer")
                if limit < 0:
                    return _fail("--limit must be non-negative")
            for receipt in engine.ledger.all()[-limit:]:
                print("[%s] seq=%s %s exit=%s %s" % (
                    receipt["id"], receipt["seq"], receipt["policy"]["decision"],
                    receipt["execution"]["exit_code"],
                    " ".join(receipt["action"]["argv"][:2])))
            return 0

        if command == "show":
            if not rest:
                return _fail("show requires a receipt id")
            print(canonical(engine.find(rest[0])))
            return 0

        if command == "diff":
            if not rest:
                return _fail("diff requires a receipt id")
            ws = engine.find(rest[0])["workspace"]
            print(canonical({k: ws[k] for k in ("added", "removed", "changed",
                                                 "protected_violations")}))
            return 0

        if command in ("apply", "undo"):
            if not rest:
                return _fail("%s requires a receipt id" % command)
            getattr(engine, command)(rest[0])
            print("%s %s ok" % (command, rest[0]))
            return 0

        if command == "replay":
            if not rest:
                return _fail("replay requires a receipt id")
            out = engine.replay(rest[0])
            print("replay %s match=%s exit=%s" % (rest[0], out["match"], out["exit_code"]))
            return 0 if out["match"] else 1

        if command == "doctor":
            health = engine.ledger.doctor()
            print("doctor ok=%s receipts=%d errors=%d" % (
                health["ok"], health["count"], len(health["errors"])))
            for error in health["errors"]:
                print("  " + error)
            return 0 if health["ok"] else 1

        if command == "policy":
            if not rest or rest[0] == "show":
                print(canonical(engine.policy.data))
                return 0
            if rest[0] == "set" and len(rest) >= 3:
                key, raw = rest[1], rest[2]
                try:
                    value = json.loads(raw)
                except ValueError:
                    value = raw
                engine.policy.data[key] = value
                engine.policy.save(engine.policy_path)
                print("policy %s = %s" % (key, canonical(value)))
                return 0
            return _fail("usage: receipts policy show | policy set KEY VALUE")
    except (KeyError, ValueError, FileNotFoundError, OSError) as exc:
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        return _fail(str(message), 1)
    return _usage()
