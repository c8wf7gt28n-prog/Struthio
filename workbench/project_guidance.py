"""Read-only, provider-neutral project guidance shared by Clip and every client.

Plans are advice, never authority. Consumers must still use the kernel's existing
candidate/execution/approval operations. No planner invokes tools or providers.
"""
from pathlib import Path
import fnmatch
import json
import shutil
from .project_inventory import inventory, hashes, revision
from . import locations

CONTRACT = "arc-ledger.guidance/1"
FIELDS = {
    "project.authority": ({"prefix": {"type": "string"}, "offset": {"type": "integer", "minimum": 0},
                           "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, []),
    "agent.handoff": ({}, []),
    "tasks.templates": ({}, []),
    "tasks.plan": ({"template": {"type": "string"}, "goal": {"type": "string", "maxLength": 2000},
                    "path": {"type": "string"}}, ["template"]),
    "clip.overview": ({}, []),
}

# Deliberate authority decisions, separate from inferred import relationships.
DOMAINS = [
    ("workbench/", "Ledger application", "Current desktop, shared services and phone source", "ledger"),
    ("hardware/", "Hardware engineering", "Protected cumulative engineering sources; fabrication HOLD", None),
    ("software/arcos/", "ARC-OS", "Current host OS foundation; upstream kernel sources are references", "arcos.host"),
    ("software/struthio/", "STRUTHIO native C", "Current portable native game; protected tests and oracles", "struthio.host"),
    ("examples/struthio_arcade/", "STRUTHIO JavaScript", "Authoritative gameplay behavior reference", "struthio.javascript-reference"),
    ("sdk/", "ARC-1 SDK", "Shared host SDK; physical backend unverified", "arc1.host-sdk"),
    ("tests/", "Qualification", "Maintained regression and qualification entry points", "ledger.tests"),
    ("development/agent_qualification/", "Agent qualification fixture", "Controlled host fixture, not console firmware", "qualification.test"),
    ("development/diag_ticket_isolation/", "Development Lab", "Bounded diagnostic comparison fixture", "diagnostic.compare"),
    ("passes/", "Engineering evidence", "Immutable historical pass records, not current implementations", None),
    ("archive/", "Historical references", "Preserved provenance, not working source", None),
    ("recovery/", "Recovery", "Retained recovery snapshots, not active code", None),
    ("tools/", "Development tools", "Maintained tooling; release scripts are version-specific", "ledger.tools"),
]

TEMPLATES = [
    dict(id="hardware-coverage", title="Reconcile hardware coverage", tool="proof.coverage",
         paths=[], reads=["docs/WORKSHOP.md"],
         criterion="Reconcile current sources; retain every unmatched component, interface and evidence gap."),
    dict(id="struthio-parity", title="Investigate STRUTHIO parity", tool="struthio.test",
         paths=["software/struthio/"], reads=["software/struthio/README.md"],
         criterion="Preserve JavaScript rules; compare every tick and retain the first divergence."),
    dict(id="compiler-failure", title="Investigate a C compiler failure", tool="struthio.build",
         paths=["software/struthio/"], reads=["software/struthio/README.md"],
         criterion="Reproduce diagnostics before proposing a minimal candidate; run struthio.test before acceptance."),
    dict(id="arcos-service", title="Develop an ARC-OS service", tool="arcos.test",
         paths=["software/arcos/src/", "software/arcos/games/"], reads=["docs/WORKSHOP.md"],
         criterion="Keep portable SDK/BSP boundaries, deterministic replay and all ARC-OS regressions passing."),
    dict(id="hardware-dependency", title="Trace a hardware dependency", tool="proof.qualify",
         paths=[], reads=["docs/HARDWARE_STATUS.md"],
         criterion="Read hardware.proof.inspect/trace; report source-bound gaps, never infer physical readiness."),
    dict(id="reproduce-failure", title="Reproduce a known test failure", tool="qualification.test",
         paths=["development/agent_qualification/src/"], reads=["development/agent_qualification/README.md"],
         criterion="Use the qualification fixture only; retain failed baseline evidence and verify unchanged tests."),
    dict(id="review-candidate", title="Review a reversible candidate", tool=None,
         paths=[], reads=["docs/WORKSHOP.md"],
         criterion="Inspect exact diff and evidence, require operator approval; reject or checked rollback on failure."),
]


def authority(root):
    doc = inventory(root)
    policy_path = locations.program(root)/"policy/protected_paths.json"
    protected_patterns = json.loads(policy_path.read_text())["protected"] if policy_path.is_file() else ["AGENTS.md", "policy/*"]
    for row in doc["files"]:
        name = row["path"]
        match = next((d for d in DOMAINS if name.startswith(d[0])), None)
        historical = name.startswith(("passes/", "archive/", "recovery/", "REVIEW_")) or (name.startswith('AGENT_HANDOFF_') and name!='AGENT_HANDOFF_V1_4_9_1.json')
        historical = historical or ("/" not in name and name.startswith(("PATCH_NOTES_", "ARC_LEDGER_V1_", "FILE_CHANGES_", "R10_", "IMPORT_")))
        row.update(authority_root=match[0] if match else None,
                   authority_role="historical-evidence-or-reference" if historical else "current-domain-member" if match else "unassigned-review",
                   authority_reason=match[2] if match else "Root/support file: consult docs/WORKSHOP.md and the current source manifest",
                   authority_confidence="explicit domain; file role and dependency edges remain inferred")
        if historical:
            row.update(protected=True, editable=False, classification="evidence" if name.startswith(("passes/", "REVIEW_")) else "reference")
        if match and match[3] and row["owning_build_target"] is None:
            row["owning_build_target"] = match[3]
        if name in ("README.md", "START_HERE.html", "AGENTS.md", "AGENT_HANDOFF_V1_4_9_1.json", "RELEASE_MANIFEST.json"):
            row.update(authority_root="./", authority_role="current-entry-point", authority_reason="Current release entry point; prior documentation below it is explicitly historical")
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in protected_patterns):
            row.update(protected=True, editable=False)
        row["candidate_editable"] = name.startswith(("software/arcos/src/", "software/arcos/games/", "software/struthio/", "development/agent_qualification/src/", "development/diag_ticket_isolation/src/")) and not row["protected"]
    doc["schema"] = CONTRACT
    doc["domains"] = [dict(path=d[0], name=d[1], purpose=d[2], target=d[3]) for d in DOMAINS]
    doc["duplicate_review"] = [dict(paths=g, decision="retain-pending-reference-review", reason="Identical bytes do not establish equivalent ownership; preserved snapshots are not active duplicates") for g in doc["duplicates"]]
    doc["excluded"] = ["Private .ledger state and credentials", "Reproducible build outputs", "Git history, environments and caches"]
    return doc


def plan(k, a, p):
    template = next((t for t in TEMPLATES if t["id"] == a["template"]), None)
    if not template:
        raise ValueError("Unknown template; discover tasks.templates")
    path = a.get("path")
    scoped = template["paths"]
    if path:
        k.safe(path)
        if not any(path.startswith(prefix) for prefix in scoped):
            raise ValueError("Path does not belong to this template's candidate scope")
        if Path(path).name.startswith(("test_", "state_oracle", "ring_oracle")) or path.endswith("_generated.h"):
            raise ValueError("Tests, oracles and generated files are protected")
        scoped = [path]
    permitted = [s for s in scoped if any(s.startswith(prefix) for prefix in p.paths)]
    tool = template["tool"]
    tools = {name: shutil.which(name) for name in ("gcc", "clang", "node", "iverilog")}
    blockers = []
    if tool and ("execute" not in p.scopes or p.mode == "Tutor" or tool not in p.tools):
        blockers.append("This identity cannot execute the proposed tool")
    if tool and tool.startswith(("struthio.", "arcos.", "qualification.")) and not (tools["gcc"] or tools["clang"]):
        blockers.append("No host C compiler detected on PATH")
    if tool == "struthio.test" and not tools["node"]:
        blockers.append("Node.js missing: JavaScript parity cannot run")
    return dict(schema=CONTRACT, dry_run=True, source_revision=revision(hashes(k.root)), identity=p.identity,
                template=template["id"], title=template["title"], goal=a.get("goal") or template["criterion"],
                candidate_scope=permitted, protected_paths=["hardware/", "examples/struthio_arcade/", "tests/", "policy/", "passes/", "sdk/", "software/arcos/upstream/"],
                source_reads=[s for s in template["reads"] if (k.root/s).is_file()],
                proposed_job=dict(operation="jobs.submit", params=dict(tool=tool, timeout=300, goal=a.get("goal") or template["title"])) if tool else None,
                tool_detection=tools, blockers=blockers, acceptance_criterion=template["criterion"],
                limits=dict(runtime_seconds=300, iterations=1, provider_calls=0),
                approvals=["Native candidate execution at exact revision", "Separate operator source acceptance", "Independent repair review if baseline fails"],
                steps=["Inspect source and accepted revision", "Run the bounded baseline check", "Inspect actual diagnostics and evidence", "Propose an isolated candidate within delegated scope", "Review diff; operator authorizes native execution", "Run mandatory regressions and compare", "Submit for independent/operator review; accept, reject or checked rollback"],
                notice="Read-only plan. No job, candidate, provider call or permission grant was created. PATH detection is not tool qualification.")


def dispatch(k, op, a, p):
    if op == "project.authority":
        prefix = a.get("prefix", "")
        if prefix and (prefix.startswith(("/", ".")) or ".." in prefix or "\\" in prefix):
            raise ValueError("Use a normalized project-relative prefix")
        doc = authority(k.root)
        rows = [r for r in doc["files"] if r["path"].startswith(prefix)]
        start, size = a.get("offset", 0), a.get("limit", 40)
        return dict(schema=CONTRACT, revision=doc["revision"], domains=doc["domains"], total=len(rows),
                    files=rows[start:start+size], next_offset=start+size if start+size<len(rows) else None,
                    duplicate_groups=len(doc["duplicates"]), consolidation=doc["consolidation"], excluded=doc["excluded"])
    if op == "tasks.templates":
        return dict(schema=CONTRACT, templates=TEMPLATES, notice="Templates do not grant execution or edit authority")
    if op == "tasks.plan":
        return plan(k, a, p)
    if op == "agent.handoff":
        from . import VERSION
        return dict(schema=CONTRACT, release=VERSION, source_revision=revision(hashes(k.root)),
                    identity=p.identity, scopes=sorted(p.scopes), paths=list(p.paths), tools=list(p.tools),
                    start_here=["README.md", "docs/WORKSHOP.md", "docs/CONSOLE.md", "docs/HARDWARE_STATUS.md", "docs/ARCOS_BOOT_ABI.md", "docs/ENGINEERING_API_V1.md", "AGENTS.md"],
                    discovery=["capabilities", "system.inspect", "project.authority", "tasks.templates", "clip.overview"],
                    workflow="tasks.plan → jobs.submit → evidence.read → candidate → review → authorize execution → tests → compare → operator decision",
                    commands=["python -m workbench.engineering_cli call agent.handoff", "python -m workbench.engineering_cli --allow-candidates mcp"],
                    boundaries=["No shell or flashing", "No self-acceptance", "No external provider without informed consent", "Native code execution is not sandboxed"],
                    known_limits=["Owner display and live-provider qualification pending", "Physical ARC-1 execution unverified; fabrication HOLD", "Static file relationships are incomplete for dynamic imports", "Hardware assessment is source review and simulation; physical evidence is required"])
    if op == "clip.overview":
        jobs = k.listing("jobs")
        candidates = k.listing("candidates")
        return dict(schema=CONTRACT, assistant="Clip", provider="local deterministic guidance; no model called",
                    revision=revision(hashes(k.root)), active_jobs=[j for j in jobs if j["state"] in ("Running", "Queued", "Paused", "Interrupted", "Waiting for Approval", "Waiting for Agent", "Waiting for Execution Approval")],
                    pending_candidates=[{key:c[key] for key in ("id", "goal", "state", "owner")} for c in candidates if c["state"] == "Waiting for Approval"],
                    recent_results=[dict(id=e["id"], tool=e["tool"], state=e["state"], revision=e["revision"]) for e in k.listing("evidence")[:5]],
                    can_accept="approve" in p.scopes and p.mode != "Tutor", fabrication="HOLD")
    raise ValueError("Unknown guidance operation")
