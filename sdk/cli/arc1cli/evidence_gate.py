"""Reusable, fail-closed evidence review checks; no hardware operations.

Levels are matched explicitly, never ranked: HOST_SIM cannot satisfy BOARD_TEST.
Review identities are declarations to verify externally, not authentication.
"""
import hashlib
import json
import re
from pathlib import Path


def evidence_digest(evidence):
    unsigned = {k: v for k, v in evidence.items() if k != "review"}
    return hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _verify_file(root, entry):
    rel, digest = entry["path"], entry["sha256"]
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("invalid relative evidence path")
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("missing or escaping evidence file: " + rel)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid evidence hash")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("stale evidence file: " + rel)


def check_gate(root, requirements, evidence):
    """All requirements need current, matching, independently reviewed evidence.

    A result is only eligibility under supplied requirements. The caller owns
    the approved requirement set and authenticates review identities separately.
    Empty, duplicate or malformed requirement sets remain HOLD.
    """
    root = Path(root).resolve()
    findings, satisfied = [], []
    try:
        if (not isinstance(requirements, (list, tuple)) or not isinstance(evidence, (list, tuple)) or
                any(not isinstance(r, dict) for r in requirements) or
                any(not isinstance(e, dict) for e in evidence)):
            raise ValueError("requirement/evidence object arrays required")
        ids = [r["id"] for r in requirements]
        if not ids or len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
            raise ValueError("nonempty unique requirement IDs required")
        for req in requirements:
            if (not isinstance(req["accepted_levels"], list) or not req["accepted_levels"] or
                    any(not isinstance(v, str) or not v for v in req["accepted_levels"]) or
                    not isinstance(req["kind"], str) or not req["kind"] or
                    not isinstance(req["subject"], dict) or not req["subject"]):
                raise ValueError("requirement lacks explicit scope/levels")
            candidates = [e for e in evidence if e.get("requirement") == req["id"]]
            reasons, ok = [], False
            for item in candidates:
                try:
                    if item["result"] != "pass" or item["level"] not in req["accepted_levels"]:
                        raise ValueError("result/evidence class does not satisfy requirement")
                    if item["kind"] != req["kind"] or item["subject"] != req["subject"]:
                        raise ValueError("wrong kind or exact device/revision scope")
                    if not isinstance(item["inputs"], list) or not item["inputs"]:
                        raise ValueError("source bindings required")
                    bindings = item["inputs"]
                    if len({b["path"] for b in bindings}) != len(bindings):
                        raise ValueError("duplicate input binding")
                    for binding in [item["report"], *bindings]:
                        _verify_file(root, binding)
                    review = item["review"]
                    if (review["state"] != "accepted" or not isinstance(item["producer"], str) or
                            not isinstance(review["reviewer"], str) or not item["producer"].strip() or
                            not review["reviewer"].strip() or
                            review["reviewer"].strip() == item["producer"].strip()):
                        raise ValueError("independent accepted review required")
                    if review["evidence_sha256"] != evidence_digest(item):
                        raise ValueError("review does not bind this evidence record")
                    ok = True
                    break
                except (KeyError, TypeError, ValueError, OSError) as exc:
                    reasons.append(str(exc))
            if ok:
                satisfied.append(req["id"])
            else:
                findings.append({"requirement": req["id"], "reasons": reasons or ["no matching evidence"]})
    except (KeyError, TypeError, ValueError) as exc:
        findings.append({"requirement": "INPUT", "reasons": [str(exc)]})
    return {"decision": "HOLD" if findings else "ELIGIBLE_FOR_REVIEWED_GATE",
            "satisfied": satisfied, "findings": findings,
            "review_identity_authenticated": False}
