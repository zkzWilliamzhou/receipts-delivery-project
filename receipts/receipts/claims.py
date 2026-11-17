"""Binds a natural-language claim to an admissible receipt. No LLM judge."""
from .sandbox import capabilities, is_enforcing

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"


def _caps_for(receipt):
    stored = receipt.get("policy", {}).get("capabilities")
    if isinstance(stored, dict) and "filesystem_containment" in stored:
        return dict(stored)
    return capabilities(receipt["policy"]["backend"])


def _containment_warnings(caps):
    warnings = []
    if not caps["filesystem_containment"]:
        warnings.append(
            "absolute writes outside the copy-on-write workspace are not captured"
        )
    if not caps["network_isolation"]:
        warnings.append("network isolation is advisory only")
    return warnings


class ClaimVerifier:
    def __init__(self, ledger, policy):
        self.ledger = ledger
        self.policy = policy

    def _result(self, claim, verdict=UNVERIFIED, reason=None, receipt=None,
                checks=None, warnings=None):
        return {
            "claim": claim, "verdict": verdict, "reason": reason,
            "receipt": receipt, "checks": checks or [],
            "warnings": warnings or [],
        }

    def verify(self, claim, strict=False):
        health = self.ledger.doctor()
        if not health["ok"]:
            return self._result(claim, reason="ledger_corrupt",
                                checks=["ledger: " + "; ".join(health["errors"][:3])])

        rule = self.policy.claim_rule(claim)
        if rule is None:
            return self._result(claim, reason="unbound_claim",
                                checks=["claim: no matching rule"])

        receipts = self.ledger.all()
        if rule["kind"] == "network_isolation":
            candidates = [r for r in receipts
                          if r["policy"]["decision"] == "allow"
                          and is_enforcing(r["policy"]["backend"])]
            if not candidates:
                return self._result(claim, reason="network_unverifiable",
                                    checks=["backend: no network-isolated receipt"])
            candidate = candidates[-1]
            caps = _caps_for(candidate)
            if strict and not caps["filesystem_containment"]:
                return self._result(claim, reason="uncontained_execution",
                                    receipt=candidate["id"],
                                    checks=["backend: strict mode requires filesystem containment"])
            return self._result(claim, verdict=PASS, reason="admissible_receipt",
                                receipt=candidate["id"],
                                checks=["backend: network isolation recorded"],
                                warnings=_containment_warnings(caps))

        candidates = [r for r in receipts
                      if r["policy"]["decision"] == "allow"
                      and r["execution"]["exit_code"] is not None
                      and self.policy.match_command(r["action"]["argv"], rule["commands"])]
        if not candidates:
            return self._result(claim, reason="no_evidence",
                                checks=["evidence: no admissible command receipt"])

        candidate = max(candidates, key=lambda r: r["seq"])
        receipt_id = candidate["id"]
        caps = _caps_for(candidate)
        if candidate["policy"]["hash"] != self.policy.hash():
            return self._result(claim, reason="policy_changed", receipt=receipt_id,
                                checks=["policy: receipt was produced under a different policy"])
        if candidate["workspace"].get("unsafe_symlinks"):
            return self._result(claim, reason="unsafe_symlink", receipt=receipt_id,
                                checks=["workspace: escaping symlink blocked the COW copy"])
        if strict and not (caps["network_isolation"] and caps["filesystem_containment"]):
            return self._result(claim, reason="uncontained_execution", receipt=receipt_id,
                                checks=["backend: strict mode requires full containment"],
                                warnings=_containment_warnings(caps))
        if candidate["execution"]["exit_code"] != rule["require_exit"]:
            return self._result(claim, verdict=FAIL, reason="conflicting_evidence",
                                receipt=receipt_id,
                                checks=["exit: %s" % candidate["execution"]["exit_code"]],
                                warnings=_containment_warnings(caps))
        if candidate["execution"]["truncated"]:
            return self._result(claim, reason="output_truncated", receipt=receipt_id,
                                checks=["output: captured output was truncated"],
                                warnings=_containment_warnings(caps))
        if candidate["workspace"]["protected_violations"]:
            return self._result(claim, reason="protected_path_violation", receipt=receipt_id,
                                checks=["workspace: protected path touched"],
                                warnings=_containment_warnings(caps))
        if rule.get("requires_network_isolation") and not caps["network_isolation"]:
            return self._result(claim, reason="network_unverifiable", receipt=receipt_id,
                                checks=["backend: advisory only"],
                                warnings=_containment_warnings(caps))

        later = [r for r in receipts
                 if r["seq"] > candidate["seq"]
                 and (r["workspace"]["added"] or r["workspace"]["removed"]
                      or r["workspace"]["changed"])]
        if later:
            return self._result(claim, reason="stale_evidence", receipt=receipt_id,
                                checks=["stale: %s changed files after the receipt" % later[-1]["id"]],
                                warnings=_containment_warnings(caps))

        return self._result(
            claim, verdict=PASS, reason="admissible_receipt", receipt=receipt_id,
            checks=["ledger: intact", "policy: allow", "command: matched",
                    "exit: %s" % candidate["execution"]["exit_code"],
                    "workspace: no protected violation", "stale: none"],
            warnings=_containment_warnings(caps),
        )
