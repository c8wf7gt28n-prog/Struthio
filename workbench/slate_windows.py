"""Owner-approved logical views. No owner impersonation, transport or job runner."""
from __future__ import annotations
import json
import secrets
import sqlite3
import time
from pathlib import Path
from sdk.cli.arc1cli import slate_windows as c
from sdk.cli.arc1cli.object_context import principal_key
from . import activity, object_context, record_io as io

ID = {"type": "string", "minLength": 35, "maxLength": 35}
DEVICE = {"type": "string", "minLength": 1, "maxLength": 100}
REV = object_context.SHA
FIELDS = {
    "ledger.windows.status": ({}, []),
    "ledger.windows.configure": ({"enabled": {"type": "boolean"}}, ["enabled"]),
    "ledger.windows.open": (object_context.ARGS, ["selector", "expected_revision", "expected_object_id"]),
    "ledger.windows.list": ({}, []),
    "ledger.windows.snapshot": ({"window_id": ID}, ["window_id"]),
    "ledger.windows.refresh": ({"window_id": ID, "expected_revision": REV}, ["window_id", "expected_revision"]),
    "ledger.windows.close": ({"window_id": ID}, ["window_id"]),
    "ledger.windows.publish": ({"window_id": ID, "device": DEVICE, "expected_revision": REV}, ["window_id", "device", "expected_revision"]),
    "ledger.windows.revoke": ({"window_id": ID, "device": DEVICE}, ["window_id", "device"]),
    "ledger.windows.present": ({"window_id": ID, "presentation": {"type": "object"}}, ["window_id", "presentation"]),
}
READS = {"ledger.windows.status", "ledger.windows.list", "ledger.windows.snapshot", "ledger.windows.present"}
SCOPES = {op: "read" if op in READS else "approve" for op in FIELDS}
ERROR = "WINDOW_UNAVAILABLE"


def ensure(db):
    db.execute("CREATE TABLE IF NOT EXISTS slate_windows(id TEXT PRIMARY KEY,owner TEXT,payload TEXT,sha256 TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS slate_window_flags(owner TEXT PRIMARY KEY,enabled INTEGER,epoch INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS slate_window_grants(window_id TEXT,device TEXT,session TEXT,revision TEXT,PRIMARY KEY(window_id,device))")
    db.execute("CREATE TABLE IF NOT EXISTS slate_window_layouts(window_id TEXT,device TEXT,payload TEXT,PRIMARY KEY(window_id,device))")
    from . import window_views
    window_views.ensure(db)


def flag(db, owner):
    row = db.execute("SELECT enabled,epoch FROM slate_window_flags WHERE owner=?", (owner,)).fetchone()
    return row if row else (0, 0)


def load(db, ident):
    c.window_id(ident)
    row = db.execute("SELECT owner,payload,sha256 FROM slate_windows WHERE id=?", (ident,)).fetchone()
    if not row or len(row[1].encode()) > c.MAX_RECORD or io.digest(io.strict_json(row[1])) != row[2]:
        raise ValueError(ERROR)
    value = io.strict_json(row[1])
    if value["owner"] != row[0] or value["id"] != ident or value["schema"] != c.VERSION:
        raise ValueError(ERROR)
    return value


def save(db, value):
    raw = io.canonical(value)
    if len(raw) > c.MAX_RECORD:
        raise ValueError("WINDOW_METADATA_LIMIT")
    db.execute("INSERT OR REPLACE INTO slate_windows VALUES(?,?,?,?)",
               (value["id"], value["owner"], raw.decode(), io.digest(value)))


def session(db, identity, principal=None):
    rows = [json.loads(raw) for raw, in db.execute("SELECT payload FROM sessions WHERE json_extract(payload,'$.identity')=?", (identity,))]
    rows = [s for s in rows if s.get("identity") == identity and s.get("expires", 0) > time.time()]
    enabled = db.execute("SELECT value FROM settings WHERE key='remote_enabled'").fetchone()
    if len(rows) != 1 or not enabled or enabled[0] != "true":
        raise ValueError(ERROR)
    s = rows[0]
    if not identity.startswith("remote-device-") or "read" not in s.get("scopes", []):
        raise ValueError(ERROR)
    if principal is not None and (principal.mode != "Engineer" or
        sorted(principal.scopes) != sorted(s["scopes"]) or
        list(principal.paths) != s["paths"] or list(principal.tools) != s["tools"]
    ):
        raise ValueError(ERROR)
    return io.digest({k: s.get(k) for k in ("identity", "scopes", "paths", "tools", "policy", "profile", "created", "expires", "csrf")})


def _access(kernel, principal, ident, owner_only=False, disabled_ok=False):
    if "read" not in principal.scopes:
        raise ValueError(ERROR)
    with kernel.db() as db:
        row = load(db, ident)
        owner = row["owner"] == principal.identity
        if owner_only and not owner:
            raise ValueError(ERROR)
        enabled, epoch = flag(db, row["owner"])
        if not enabled and not disabled_ok:
            raise ValueError(ERROR)
        grant = None
        if not owner:
            grant = db.execute("SELECT session,revision FROM slate_window_grants WHERE window_id=? AND device=?",
                               (ident, principal.identity)).fetchone()
            if not grant or grant != (session(db, principal.identity, principal), row["overview"]["source_revision"]):
                raise ValueError(ERROR)
        ticket = io.digest([row, epoch, enabled, grant, principal_key(principal)])
    return row, ticket, owner


def access(kernel, principal, ident, owner_only=False, disabled_ok=False):
    try:
        return _access(kernel, principal, ident, owner_only, disabled_ok)
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error):
        raise ValueError(ERROR) from None


def artifact_seal(kernel, jobs):
    """Check registered artifact bytes without borrowing any owner's Principal."""
    from . import engineering_map
    rows = []
    total_bytes = 0
    for ident in sorted(set(jobs)):
        job = kernel.record("jobs", ident)
        evidence = kernel.record("evidence", job["evidence"]) if job.get("evidence") else None
        artifacts = evidence.get("artifacts", []) if evidence else []
        if len(artifacts) > 64:
            raise ValueError("WINDOW_DEPENDENCY_LIMIT")
        for a in artifacts:
            total_bytes += a["bytes"]
            if total_bytes > c.MAX_ARTIFACT_BYTES:
                raise ValueError("WINDOW_ARTIFACT_BUDGET")
            # The existing reader verifies job/evidence linkage and safe paths.
            engineering_map.artifact(kernel, ident, a["path"], a["sha256"])
        rows.append([job, evidence])
    return io.digest(rows)


def _source_seal(kernel, selector, owner):
    """Revalidate exact published dependencies; never dispatch under owner identity."""
    kind, target = selector["kind"], selector["target"]
    if kind == 'pdf':
        from . import window_views
        return window_views.document_seal(kernel, selector, owner)
    if "map" in selector:
        from . import engineering_map as maps
        from sdk.cli.arc1cli import knowledge_sources
        with kernel.db() as db:
            row = maps.load(db, owner, selector["map"])
        _, rom, graph = maps.fresh(kernel, row)
        candidate_states = []
        if kind == "component":
            part = graph["components"].get(target)
            if not part:
                raise ValueError(ERROR)
            from sdk.cli.arc1cli import engineering_map as graph_reader
            _, manifest = knowledge_sources.header(rom["path"], rom["report"]["manifest_sha256"])
            for doc in graph_reader.document_candidates(part, manifest["records"]):
                try:
                    knowledge_sources.original(rom["path"], rom["report"], doc["record_id"])
                    state = "ORIGINAL_HASH_VERIFIED"
                except (ValueError, OSError):
                    state = "ORIGINAL_UNAVAILABLE"
                candidate_states.append([doc["record_id"], state])
            for doc in row["configuration"]["documents"]:
                if doc["component"] == target:
                    knowledge_sources.original(rom["path"], rom["report"], doc["record_id"])
        elif target not in graph["nets"]:
            raise ValueError(ERROR)
        jobs = [row["job"], *(b["job"] for b in row["configuration"]["evidence"])]
        return io.digest([row, candidate_states, artifact_seal(kernel, jobs)])
    if kind == "file":
        path = kernel.safe(target)
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("WINDOW_FILE_LIMIT")
        from . import record_access
        parts = path.relative_to(kernel.root).parts
        parent = None
        if len(parts) >= 2 and parts[0] == "build" and parts[1] in record_access.PRIVATE_OUTPUTS:
            if len(parts) < 5 or parts[2] != "runs":
                raise ValueError(ERROR)
            parent = kernel.record("jobs", parts[3])
            if parent.get("owner") != owner or not record_access.private_job(parent):
                raise ValueError(ERROR)
        return io.digest([io.sha(path), parent])
    if kind == "job":
        from .record_access import job_readable
        job = kernel.record("jobs", target)
        if not job_readable(job, owner):
            raise ValueError(ERROR)
        from .project_inventory import hashes
        candidate = kernel.record("candidates", job["candidate"]) if job.get("candidate") else None
        root = kernel.candidate_root(candidate["id"]) if candidate else kernel.root
        return io.digest([artifact_seal(kernel, [target]), candidate, hashes(root), hashes(kernel.root) if candidate else None])
    from . import project_context
    if project_context.detached(kernel.root):
        raise ValueError("PROJECT_NOT_ATTACHED")
    if kind == "requirement":
        from .engineering_register import snapshot
        return io.digest(snapshot(kernel.root))
    from .workspace_services import selected
    return io.digest(selected(kernel, kind, target))


def source_seal(kernel, selector, owner):
    from . import window_views
    return io.digest([_source_seal(kernel, selector, owner),
        *(io.sha(Path(module.__file__)) for module in (c, object_context)), io.sha(Path(__file__)),window_views.fingerprint()])


def capture(kernel, principal, args):
    if args.get('selector',{}).get('kind')=='pdf':
        from . import window_views
        view,unused=window_views.capture_document(kernel,principal,args['selector']['target'],args.get('expected_object_id'))
        return view,source_seal(kernel,args['selector'],principal.identity)
    args = {k: args[k] for k in object_context.ARGS if k in args}
    before = object_context.inspect(kernel, args, principal)
    if before["state"] != "AVAILABLE":
        raise ValueError("WINDOW_CONTEXT_NEEDS_REFRESH")
    seal = source_seal(kernel, before["selector"], principal.identity)
    after = object_context.inspect(kernel, args, principal)
    if before["revision"] != after.get("revision") or after.get("state") != "AVAILABLE":
        raise ValueError("WINDOW_SOURCE_CHANGED")
    return c.overview(after), seal


def snapshot(kernel, principal, ident):
    row, ticket, owner = access(kernel, principal, ident)
    try:
        if source_seal(kernel, row["selector"], row["owner"]) != row["source_seal"]:
            raise ValueError("WINDOW_SOURCE_CHANGED")
        # The owner-approved overview is pinned by the same dependency seal for
        # both callers. Restoring full Object Glass separately checks its API.
        with kernel.db() as db:
            found = db.execute("SELECT payload FROM slate_window_layouts WHERE window_id=? AND device=?",
                               (ident, principal.identity)).fetchone()
        value = c.snapshot(row, io.strict_json(found[0]) if found else c.DEFAULT_LAYOUT)
        if row['selector']['kind']=='pdf':value['kind']='reference.pdf'
        if source_seal(kernel, row["selector"], row["owner"]) != row["source_seal"]:
            raise ValueError("WINDOW_SOURCE_CHANGED")
    except (ValueError, OSError, KeyError, TypeError):
        value = {"schema": c.VERSION, "window_id": ident, "state": "STALE",
                 "summary": "Sources changed or are unavailable. The owner must refresh and republish.", "snapshot": None}
        if owner:
            value["expected_revision"] = row["overview"]["source_revision"]
    if access(kernel, principal, ident)[1] != ticket:
        raise ValueError(ERROR)
    if len(io.canonical(value)) > c.MAX_SNAPSHOT:
        raise ValueError("WINDOW_SNAPSHOT_LIMIT")
    return value


def dispatch(kernel, op, args, principal):
    from . import window_views
    if op in window_views.FIELDS:return window_views.dispatch(kernel,op,args,principal)
    ensure_scope = "read" in principal.scopes
    if not ensure_scope:
        raise ValueError(ERROR)
    with kernel.db() as db:
        ensure(db)
    if op == "ledger.windows.status":
        with kernel.db() as db:
            enabled, epoch = flag(db, principal.identity)
            count = db.execute("SELECT count(*) FROM slate_windows WHERE owner=?", (principal.identity,)).fetchone()[0]
            remote=db.execute("SELECT value FROM settings WHERE key='remote_enabled'").fetchone()
        return {"schema": c.VERSION, "enabled": bool(enabled), "owned_windows": count, "limit": c.MAX_WINDOWS,
                "remote_transport_enabled": bool(enabled and remote and remote[0]=='true'), "remote_transport_available":True,
                "views": ["overview",*window_views.core.VIEWS], "effects": ["read"]}
    if op == "ledger.windows.configure":
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            _, epoch = flag(db, principal.identity)
            db.execute("INSERT OR REPLACE INTO slate_window_flags VALUES(?,?,?)",
                       (principal.identity, int(args["enabled"]), epoch + 1))
            if not args["enabled"]:
                for ident, in db.execute('SELECT id FROM slate_windows WHERE owner=?',(principal.identity,)).fetchall():window_views.prune(db,ident)
                db.execute("DELETE FROM slate_window_grants WHERE window_id IN (SELECT id FROM slate_windows WHERE owner=?)", (principal.identity,))
                db.execute("DELETE FROM slate_window_layouts WHERE device!=? AND window_id IN (SELECT id FROM slate_windows WHERE owner=?)", (principal.identity, principal.identity))
        return {"enabled": args["enabled"], "jobs_preserved": True, "publication_requires_explicit_grant": True}
    if op == "ledger.windows.open":
        view, seal = capture(kernel, principal, args)
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if not flag(db, principal.identity)[0]:
                raise ValueError("SLATE_WINDOWS_DISABLED")
            # Reopening the same bound view reuses its identity, without extra windows.
            ident = None
            for old_id, in db.execute("SELECT id FROM slate_windows WHERE owner=?", (principal.identity,)):
                old = load(db, old_id)
                if old["overview"]["object_id"] == view["object_id"] and old["overview"]["source_revision"] == view["source_revision"]:
                    ident = old_id
                    break
            if ident is None:
                if db.execute("SELECT count(*) FROM slate_windows WHERE owner=?", (principal.identity,)).fetchone()[0] >= c.MAX_WINDOWS:
                    raise ValueError("WINDOW_REGISTRY_LIMIT")
                ident = "sw_" + secrets.token_hex(16)
                row = {"schema": c.VERSION, "id": ident, "owner": principal.identity,
                       "selector": view["object"], "overview": view, "source_seal": seal, "generation": 1}
                save(db, row)
        return snapshot(kernel, principal, ident)
    if op == "ledger.windows.list":
        with kernel.db() as db:
            ids = db.execute("SELECT id FROM slate_windows WHERE owner=? UNION SELECT window_id FROM slate_window_grants WHERE device=? LIMIT ?",
                             (principal.identity, principal.identity, c.MAX_WINDOWS)).fetchall()
        out = []
        for ident, in ids:
            try:
                out.append(snapshot(kernel, principal, ident))
            except (ValueError, OSError, KeyError, sqlite3.Error):
                pass
        return {"schema": c.VERSION, "windows": out, "limit": c.MAX_WINDOWS}
    ident = c.window_id(args["window_id"])
    if op == "ledger.windows.snapshot":
        return snapshot(kernel, principal, ident)
    row, ticket, owner = access(kernel, principal, ident,
        owner_only=op not in READS, disabled_ok=op in ("ledger.windows.close", "ledger.windows.revoke"))
    if op == "ledger.windows.present":
        layout = c.presentation(args["presentation"])
        if snapshot(kernel, principal, ident)["state"] != "AVAILABLE":
            raise ValueError("WINDOW_CONTEXT_NEEDS_REFRESH")
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if access(kernel, principal, ident)[1] != ticket:
                raise ValueError(ERROR)
            count = db.execute("SELECT count(*) FROM slate_window_layouts WHERE window_id=?", (ident,)).fetchone()[0]
            existing = db.execute("SELECT 1 FROM slate_window_layouts WHERE window_id=? AND device=?", (ident, principal.identity)).fetchone()
            if count >= c.MAX_DEVICES + 1 and not existing:
                raise ValueError("WINDOW_PRESENTATION_LIMIT")
            db.execute("INSERT OR REPLACE INTO slate_window_layouts VALUES(?,?,?)", (ident, principal.identity, io.canonical(layout).decode()))
        return {"schema": c.VERSION, "window_id": ident, "presentation": layout, "engineering_state_changed": False}
    if op == "ledger.windows.refresh":
        view, seal = capture(kernel, principal, {"selector": row["selector"], "expected_object_id": row["overview"]["object_id"]})
    elif op == "ledger.windows.publish":
        if snapshot(kernel, principal, ident)["state"] != "AVAILABLE":
            raise ValueError("WINDOW_CONTEXT_NEEDS_REFRESH")
    with kernel.db() as db:
        db.execute("BEGIN IMMEDIATE")
        if access(kernel, principal, ident, owner_only=True,
                  disabled_ok=op in ("ledger.windows.close", "ledger.windows.revoke"))[1] != ticket:
            raise ValueError(ERROR)
        if "expected_revision" in args and args["expected_revision"] != row["overview"]["source_revision"]:
            raise ValueError("WINDOW_REVISION_CHANGED")
        if op == "ledger.windows.close":
            window_views.prune(db,ident)
            for table in ("slate_windows", "slate_window_grants", "slate_window_layouts"):
                db.execute("DELETE FROM " + table + " WHERE " + ("id" if table == "slate_windows" else "window_id") + "=?", (ident,))
            return {"window_id": ident, "closed": True, "jobs_preserved": True}
        if op == "ledger.windows.revoke":
            window_views.prune(db,ident,args['device'])
            db.execute("DELETE FROM slate_window_grants WHERE window_id=? AND device=?", (ident, args["device"]))
            db.execute("DELETE FROM slate_window_layouts WHERE window_id=? AND device=?", (ident, args["device"]))
            return {"window_id": ident, "revoked": True}
        if op == "ledger.windows.refresh":
            window_views.prune(db,ident)
            row.update(overview=view, source_seal=seal, generation=row["generation"] + 1)
            save(db, row)
            db.execute("DELETE FROM slate_window_grants WHERE window_id=?", (ident,))
            db.execute("DELETE FROM slate_window_layouts WHERE window_id=? AND device!=?", (ident, principal.identity))
        elif op == "ledger.windows.publish":
            binding = session(db, args["device"])
            count = db.execute("SELECT count(*) FROM slate_window_grants WHERE window_id=?", (ident,)).fetchone()[0]
            existing = db.execute("SELECT 1 FROM slate_window_grants WHERE window_id=? AND device=?", (ident, args["device"])).fetchone()
            if count >= c.MAX_DEVICES and not existing:
                raise ValueError("WINDOW_PUBLICATION_LIMIT")
            db.execute("INSERT OR REPLACE INTO slate_window_grants VALUES(?,?,?,?)",
                       (ident, args["device"], binding, row["overview"]["source_revision"]))
            return {"window_id": ident, "published_to": args["device"], "views": ["overview"], "execution_granted": False}
    return snapshot(kernel, principal, ident)


# Additive SW-002 routes. The SW-001 SDK contract and operation names retain
# their overview-only behavior; explicit view grants are separate.
from . import window_views
FIELDS.update(window_views.FIELDS)
SCOPES.update(window_views.SCOPES)

