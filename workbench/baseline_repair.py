"""Explicit, independently reviewed exception for a proven failing test baseline.

Not a golden-update mechanism. Three distinct delegated identities: proposer,
reviewer, accepting operator. Review never grants edit/execute/accept authority.
"""
import hashlib
import json
import time
from .project_inventory import hashes, revision

S = {"type": "string", "minLength": 1, "maxLength": 4000}
FIELDS = {
    "repairs.propose": ({"id": S, "baseline": S, "candidate_evidence": S, "reason": S}, ["id", "baseline", "candidate_evidence", "reason"]),
    "repairs.inspect": ({"id": S}, ["id"]),
    "repairs.attest": ({"id": S, "binding": S, "review": S}, ["id", "binding", "review"]),
    "repairs.authorize": ({"id": S, "binding": S}, ["id", "binding"]),
}
SCOPES = {"repairs.propose": "candidate", "repairs.inspect": "read", "repairs.attest": "repair.review", "repairs.authorize": "approve"}
SUPPORTED = {"qualification.test": ("development/agent_qualification/src/",),
             "arcos.parser": ("software/arcos/src/host.c",),
             "arcos.test": ("software/arcos/src/", "software/arcos/games/"),
             # Implementation files only: never the tests, oracles, headers or generated tables.
             "struthio.test": tuple("software/struthio/" + n for n in ("game.c", "state.c", "struthio_core.c", "host.c"))}


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def binding(k, c, baseline, candidate):
    if c["state"] != "Waiting for Approval" or not c["changes"]:
        raise ValueError("Repair requires a submitted, nonempty candidate")
    if hashes(k.root) != c["base"]:
        raise ValueError("Accepted source drift; create a fresh candidate")
    fresh = hashes(k.candidate_root(c["id"]))
    delta = {n: h for n, h in fresh.items() if c["base"].get(n) != h}
    if delta != c["changes"] or set(c["base"]) - set(fresh):
        raise ValueError("Untracked candidate changes or deletions")
    b, e = k.record("evidence", baseline), k.record("evidence", candidate)
    tool = b["tool"]
    if tool not in SUPPORTED or tool not in c["required_tools"]:
        raise ValueError("Repair currently supports structured " + ", ".join(SUPPORTED) + " failures only")
    if tool=='arcos.parser' and set(delta)!={'software/arcos/src/host.c'}:
        raise ValueError('Parser repair supports only the exact host.c implementation')
    if any(not n.startswith(SUPPORTED[tool]) for n in delta):
        raise ValueError("Repair cannot change tests, tools, interfaces or protected sources")
    if any(n.rsplit("/", 1)[-1].startswith("test_") for n in delta):
        raise ValueError("Test changes cannot use baseline repair")
    d = b.get("diagnostics", {})
    cases = d.get("cases", d.get("checks", []))
    if not (b["candidate"] is None and b["revision"] == c["revision"] and b["state"] == "Failed"
            and b.get("exit_status") == 1 and not b.get("error") and d.get("status") == "FAIL"
            and any(row.get("passed", row.get("pass")) is False for row in cases)):
        raise ValueError("Baseline must contain an actual failed assertion, not timeout, missing tools or source drift")
    if not (e["candidate"] == c["id"] and e["tool"] == tool and e["revision"] == revision(fresh)
            and e["state"] == "Completed" and e.get("exit_status") == 0 and not e.get("error")):
        raise ValueError("Fresh passing candidate evidence for the same tool required")
    body = dict(candidate=c["id"], proposer=c["owner"], tool=tool, baseline_revision=c["revision"],
                candidate_revision=revision(fresh), changes=delta, baseline_evidence=baseline,
                candidate_evidence=candidate, baseline_digest=sha(b), candidate_digest=sha(e))
    return dict(body, binding=sha(body))


def valid_grant(k, c, tool):
    repair = c.get("repair")
    if not repair or repair["tool"] != tool:
        return False
    current = binding(k, c, repair["baseline_evidence"], repair["candidate_evidence"])
    review, approval = repair.get("review", {}), repair.get("authorization", {})
    actors = {c["owner"], review.get("identity"), approval.get("identity")}
    return (current["binding"] == repair["binding"] == review.get("binding") == approval.get("binding")
            and None not in actors and len(actors) == 3)


def dispatch(k, op, a, p):
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        c = k.record("candidates", a["id"])
        if op == "repairs.inspect":
            repair = c.get("repair")
            if not repair:
                return dict(id=c["id"], repair=None, supported_tools=list(SUPPORTED))
            try:
                fresh = binding(k, c, repair["baseline_evidence"], repair["candidate_evidence"])
                return dict(id=c["id"], repair=repair, current=fresh["binding"] == repair["binding"], authorized=valid_grant(k, c, repair["tool"]))
            except ValueError as e:
                return dict(id=c["id"], repair=repair, current=False, authorized=False, reason=str(e))
        if op == "repairs.propose":
            k.require_owner(c, p)
            if p.identity != c["owner"]:
                raise ValueError("Only candidate proposer may request the repair exception")
            r = binding(k, c, a["baseline"], a["candidate_evidence"])
            r.update(reason=a["reason"], requested_at=time.time())
            c["repair"] = r
        else:
            r = c.get("repair")
            if not r:
                raise ValueError("Propose a source-bound repair first")
            fresh = binding(k, c, r["baseline_evidence"], r["candidate_evidence"])
            if fresh["binding"] != r["binding"] or a["binding"] != r["binding"]:
                raise ValueError("Stale repair binding; review again")
            if p.identity == c["owner"]:
                raise ValueError("Proposer cannot review or authorize own baseline repair")
            if op == "repairs.attest":
                if "approve" in p.scopes:
                    raise ValueError("Reviewer must use the dedicated non-operator review role")
                r["review"] = dict(identity=p.identity, binding=r["binding"], notes=a["review"], at=time.time())
                r.pop("authorization", None)
            elif op == "repairs.authorize":
                review = r.get("review", {})
                if not review or review.get("identity") == p.identity or review.get("binding") != r["binding"]:
                    raise ValueError("Independent reviewer attestation required before operator authorization")
                r["authorization"] = dict(identity=p.identity, binding=r["binding"], at=time.time())
        k.save("candidates", c, db)
        return dict(id=c["id"], repair=c["repair"])
