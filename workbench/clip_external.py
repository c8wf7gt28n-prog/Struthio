"""A durable Clip task for an explicitly delegated external AI agent.

No inference or shell is hidden here. The external runtime reads context and
submits a hash-bound edit. Fixed registered tests and existing owner execution /
source-promotion gates are shared with every other Ledger client.
"""
from __future__ import annotations
import json
import time
import uuid
from sdk.cli.arc1cli import agent_task
from .project_inventory import hashes, revision

S = {"type": "string", "minLength": 1, "maxLength": 4000}
ID = {"type": "string", "minLength": 32, "maxLength": 32}
FIELDS = {
    "clip.prepare": ({"goal": S, "path": S, "request_key": S}, ["goal", "path", "request_key"]),
    "clip.context": ({"id": ID}, ["id"]),
    "clip.inspect": ({"id": ID}, ["id"]),
    "clip.propose": ({"id": ID, "proposal": {"type": "object"}}, ["id", "proposal"]),
    "clip.test": ({"id": ID, "phase": {"type": "string", "enum": ["baseline", "candidate"]}}, ["id", "phase"]),
    "clip.finish": ({"id": ID}, ["id"]),
}
SCOPES = {op: "read" if op in ("clip.context", "clip.inspect") else
          "execute" if op == "clip.test" else "candidate" for op in FIELDS}


def checked(k, id, p, *, write=False, current=False):
    j = k.record("jobs", id)
    if j["tool"] != "clip.external":
        raise ValueError("Not an external Clip task")
    if write:
        k.require_owner(j, p)
        if j["state"] in ("Completed", "Cancelled", "Failed"):
            raise ValueError("Clip task is closed")
        if not all(any(n.startswith(s) if s.endswith("/") else n == s for s in p.paths) for n in j["scope"]):
            raise ValueError("Agent delegation no longer covers this task")
        if j["test_tool"] not in p.tools:
            raise ValueError("Test tool no longer delegated")
    c = k.record("candidates", j["candidate"])
    if current and hashes(k.root) != c["base"]:
        raise ValueError("Accepted source changed; prepare a new task")
    return j, c


def inspect(k, j, c):
    source = hashes(k.root)
    candidate = hashes(k.candidate_root(c["id"]))
    tests = []
    for phase, id in j.get("test_jobs", {}).items():
        row = k.record("jobs", id)
        tests.append({"phase": phase, "id": id, "state": row["state"],
                      "evidence": row.get("evidence"), "revision": row["revision"]})
    return {"task": j, "candidate_state": c["state"], "source_current": source == c["base"],
            "candidate_revision": revision(candidate), "tests": tests,
            "native_execution_authorized": c.get("execution_approval", {}).get("revision") == revision(candidate),
            "acceptance_requires_operator": True, "agent_identity_verified_by_provider": False}


def original_source(k, c, path):
    saved = k.state / "candidates" / c["id"] / "original" / path
    raw = (saved if saved.is_file() else k.candidate_root(c["id"]) / path).read_bytes()
    if agent_task.sha(raw) != c["base"][path]:
        raise ValueError("Original source snapshot changed")
    return raw.decode("utf-8")


def update(k, id, values, *, test=None):
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        live = json.loads(db.execute("SELECT payload FROM jobs WHERE id=?", (id,)).fetchone()[0])
        if live["state"] in ("Completed", "Cancelled", "Failed"):
            raise ValueError("Task closed while the request was in progress")
        live.update(values)
        if test:
            live["test_jobs"][test[0]] = test[1]
        k.save("jobs", live, db)
        return live


def prepare(k, a, p):
    if not {"candidate", "execute"} <= p.scopes:
        raise ValueError("Clip tasks require candidate and execute scopes")
    path = a["path"]
    # One reviewed implementation file; no interfaces, tests or target firmware.
    if (not path.startswith(("software/arcos/src/", "software/arcos/games/"))
            or not path.endswith(".c") or path.rsplit("/", 1)[-1].startswith("test_")):
        raise ValueError("Select one ARC-OS C implementation file")
    if len(k.safe(path).read_bytes()) > agent_task.MAX_CONTEXT // 2:
        raise ValueError("Source file exceeds the bounded context allowance")
    if "arcos.test" not in p.tools or not any(path.startswith(s) if s.endswith("/") else path == s for s in p.paths):
        raise ValueError("File or arcos.test is outside current delegation")
    spec = {"goal": a["goal"], "path": path}
    if len(a["request_key"]) > 128:
        raise ValueError("Request key exceeds 128 characters")
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT job FROM requests WHERE owner=? AND key=?", (p.identity, a["request_key"])).fetchone()
        if old:
            prior = k.record("jobs", old[0])
            if prior["tool"] != "clip.external" or prior.get("request_spec") != spec:
                raise ValueError("Idempotency key reused for a different request")
            return prior
        required=['arcos.test','arcos.parser'] if path=='software/arcos/src/host.c' else ['arcos.test']
        if any(tool not in p.tools for tool in required):raise ValueError('Required command-parser regression is outside delegation')
        c = k.create_candidate({"goal": a["goal"], "paths": [path], "required_tools": required}, p, db=db)
        id = uuid.uuid4().hex
        saved_candidate = json.loads(db.execute("SELECT payload FROM candidates WHERE id=?", (c["id"],)).fetchone()[0])
        saved_candidate["external_agent_task"] = id
        k.save("candidates", saved_candidate, db)
        file_hashes = {path: saved_candidate["base"][path]}
        j = {"id": id, "owner": p.identity, "tool": "clip.external", "state": "Waiting for Agent",
             "candidate": c["id"], "goal": a["goal"], "scope": [path], "revision": c["revision"],
             "test_tool": "arcos.test", "authorized_tools": required, "timeout": 120,
             "created": time.time(), "pid": None, "external_driver": True,
             "approval_required": True, "current_operation": "Read source, reproduce defect and propose one bounded edit",
             "request_spec": spec, "test_jobs": {}, "file_hashes": file_hashes,
             "binding": agent_task.binding(id, c["revision"], file_hashes, "arcos.test"),
             "provider_calls": 0, "provider_budget": {"max_calls": 0, "max_context_bytes": agent_task.MAX_CONTEXT,
                 "max_output_bytes": agent_task.MAX_OUTPUT}, "automatic_inference": False}
        k.save("jobs", j, db)
        db.execute("INSERT INTO requests VALUES(?,?,?)", (p.identity, a["request_key"], id))
    return j


def dispatch(k, op, a, p):
    if op == "clip.prepare":
        return prepare(k, a, p)
    write = op not in ("clip.context", "clip.inspect")
    j, c = checked(k, a["id"], p, write=write, current=write)
    if op == "clip.inspect":
        return inspect(k, j, c)
    if op == "clip.context":
        result = {"schema": agent_task.CONTRACT, "task": j["id"], "goal": j["goal"],
                  "binding": j["binding"], "revision": j["revision"], "source_current": hashes(k.root) == c["base"],
                  "files": [{"path": path, "sha256": j["file_hashes"][path],
                             "content": original_source(k, c, path)} for path in j["scope"]],
                  "test_tool": j["test_tool"], "tests": inspect(k, j, c)["tests"],
                  "required_tools":c['required_tools'],
                  "instructions": "Inspect and reproduce a real defect. Submit binding, agent runtime declaration, explanation and one path/sha256/content patch through clip.propose. Never change tests or source outside this file. Exact owner execution review is required before candidate tests. Source acceptance remains separate.",
                  "max_output_bytes": agent_task.MAX_OUTPUT, "automatic_inference": False}
        if len(json.dumps(result).encode()) > agent_task.MAX_CONTEXT:
            raise ValueError("Context budget exceeded")
        return result
    if op == "clip.propose":
        if c["state"] != "Draft" or c["changes"] or j.get("proposal"):
            raise ValueError("Only one proposal per task; prepare another task to revise")
        patch = agent_task.validate_proposal(a["proposal"], expected_binding=j["binding"], files=j["file_hashes"])
        r = k.patch({"id": c["id"], **patch}, p)
        j = update(k, j["id"], dict(state="Waiting for Execution Approval", proposal={"agent": a["proposal"]["agent"],
                 "explanation": a["proposal"]["explanation"], "file_sha256": r["sha256"], "at": time.time()},
                 current_operation="Review source diff, then authorize exact native candidate execution"))
    elif op == "clip.test":
        phase = a["phase"]
        if phase == "candidate" and not c["changes"]:
            raise ValueError("Propose a change before testing the candidate")
        # Existing submit() checks exact execution grant, source, ownership,
        # idempotency and concurrency. It launches only the registered test.
        args = {"tool": j["test_tool"], "goal": j["goal"], "timeout": 120,
                "request_key": "clip-external:" + j["id"] + ":" + phase}
        if phase == "candidate":
            args["candidate"] = c["id"]
        child = k.submit(args, p)
        update(k, j["id"], {"current_operation": "Follow " + phase + " test " + child["id"]}, test=(phase, child["id"]))
        return child
    elif op == "clip.finish":
        test = j.get("test_jobs", {}).get("candidate")
        if not test:
            raise ValueError("Run the candidate test first")
        job = k.record("jobs", test)
        if job["state"] != "Completed" or job["revision"] != revision(hashes(k.candidate_root(c["id"]))):
            raise ValueError("Fresh passing candidate evidence required")
        current_revision=revision(hashes(k.candidate_root(c['id'])))
        for tool in c['required_tools']:
            matches=[e for e in k.listing('evidence') if e.get('candidate')==c['id'] and e.get('revision')==current_revision
                     and e.get('tool')==tool and e.get('state')=='Completed' and e.get('exit_status')==0]
            if not matches:raise ValueError('Fresh passing candidate evidence required: '+tool)
        k.transition("candidates.review", {"id": c["id"]}, p)
        j = update(k, j["id"], dict(state="Waiting for Approval", current_operation="AI candidate passed; independent source review required"))
    else:
        raise ValueError("Unknown Clip external operation")
    return inspect(k, j, k.record("candidates", c["id"]))
