"""Source-bound engineering records for Qt, CLI, MCP and the Orange Book.

Owned campaign records stay in docs/ledger2. This adapter neither copies their
authority nor promotes workbook edits. Every result retains its source currency.
"""
from __future__ import annotations
import platform
import re
import time
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
from . import record_io as io

CONTRACT = "arc-ledger.engineering-register/1"
ROOT_BINDINGS = "project/register/bindings.json"
R10 = "hardware/compact-arc1/R10_WORK/"
MAX_ROWS = 2000
MAX_RESPONSE = 100
UNIT_PROFILE = {"V": "voltage", "mV": "voltage", "A": "current", "mA": "current", "Ohm": "resistance", "s": "time", "ms": "time", "us": "time", "nF": "capacitance", "Hz": "frequency", "Cel": "temperature"}
POWER_INPUTS = [R10 + p for p in ("board/r10_board_plan.json", "cad/NETLIST.xml", "closure_p2/rail_envelope.py")]
POWER_INPUTS += ["workbench/proof_checks.py", "workbench/engineering_register.py", ROOT_BINDINGS]
POWER_INPUTS += ["workbench/hardware_proof.py"]
POWER_INPUTS += ["docs/vendor/datasheets/" + n for n in ("tps62827.pdf", "tps386000.pdf", "ecp5_datasheet.pdf", "text/tps62827.txt", "text/tps386000.txt", "text/ecp5_datasheet.txt")]
CORE_INPUTS = [ROOT_BINDINGS, "docs/ledger2/REQUIREMENTS.json", "docs/ledger2/OPEN_ISSUES.json", "docs/ledger2/DECISIONS.json", "docs/ledger2/OWNER_ENVIRONMENT.md", "vendor_kb/catalog.json", "vendor_kb/facts.json", "vendor_kb/lock.json", "docs/HARDWARE_STATUS.md", "project/source_identity.json"]
FIELDS = {
    "register.inspect": ({}, []),
    "register.query": ({"query": {"type": "string", "maxLength": 200}, "record_type": {"type": "string", "enum": ["requirements", "evidence", "actions", "objects", "quantities"]}, "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RESPONSE}, "cursor": {"type": "string", "maxLength": 500}}, []),
    "register.record": ({"record_id": {"type": "string", "minLength": 1, "maxLength": 100}}, ["record_id"]),
    "register.export": ({}, []),
    "register.preview": ({"export_id": {"type": "string", "maxLength": 32}, "path": {"type": "string", "maxLength": 300}}, ["export_id", "path"]),
}


def native_components(root):
    path = io.project_path(root, R10 + "cad/NETLIST.xml")
    if path.stat().st_size > 16 * 1024 * 1024: raise ValueError("NETLIST_SIZE_LIMIT")
    data = path.read_bytes()
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper(): raise ValueError("XML_ENTITIES_FORBIDDEN")
    tree = ET.fromstring(data)
    components = {}
    for c in tree.findall("./components/comp"):
        ref = c.get("ref")
        components[ref] = {"record_id": "R10:" + ref, "reference": ref, "value": c.findtext("value"), "footprint": c.findtext("footprint"), "native_uuid": c.findtext("tstamps"), "pins": []}
    for net in tree.findall("./nets/net"):
        for node in net.findall("node"):
            if node.get("ref") in components:
                components[node.get("ref")]["pins"].append({"pin": node.get("pin"), "function": node.get("pinfunction"), "pin_type": node.get("pintype"), "net": net.get("name")})
    return components


def source_ref(root, path, locator=""):
    m = io.manifest(root, [path])[path]
    return {"path": path, "sha256": m["sha256"], "locator": locator, "state": "CURRENT" if m["sha256"] else "MISSING"}


def binding_paths(root):
    cfg = io.load(root, ROOT_BINDINGS)
    if cfg.get("schema") != "arc-ledger.register-bindings/1": raise ValueError("UNSUPPORTED_SCHEMA")
    ids = []
    for row in cfg["requirements"]:
        if set(row) != {"record_id", "subsystem", "statement", "acceptance_criterion", "definition_state", "check_plan_refs", "object_refs", "source_paths"}:
            raise ValueError("BINDING_FIELD_SCHEMA")
        if not re.fullmatch(r"[A-Z0-9_-]{1,150}", row["record_id"]): raise ValueError("INVALID_RECORD_ID")
        if any(not isinstance(row[k], str) or not row[k].strip() or len(row[k]) > 4000 for k in ("statement", "acceptance_criterion", "subsystem", "definition_state")):
            raise ValueError("INVALID_REQUIREMENT_FIELD")
        ids.append(row["record_id"])
    plan_ids = [p["record_id"] for p in cfg["check_plans"]]
    if len(ids) != len(set(ids)) or len(plan_ids) != len(set(plan_ids)): raise ValueError("DUPLICATE_ID")
    if any(ref not in plan_ids for row in cfg["requirements"] for ref in row["check_plan_refs"]): raise ValueError("DANGLING_CHECK_PLAN")
    names = set(CORE_INPUTS + POWER_INPUTS)
    for r in cfg["requirements"]: names.update(r["source_paths"])
    from .firmware_tools import sources, COMPONENTS
    for cid in COMPONENTS: names.update(sources(root, cid))
    names.update(["workbench/record_io.py", "workbench/engineering_register.py", "workbench/register_exchange.py", "workbench/firmware_tools.py", "workbench/engineering_kernel.py", "workbench/engineering_cli.py", "project/register/schema.json", "project/register/workbook_template.xlsx"])
    return sorted(names)


def binding_inputs(root):
    return io.manifest(root, binding_paths(root))


def analyze_power(root):
    from .hardware_proof import power_inputs
    from .proof_checks import power
    started = time.time()
    before = io.manifest(root, POWER_INPUTS)
    if any(v["sha256"] is None for v in before.values()): raise ValueError("MISSING_POWER_INPUT")
    cases, limits, _ = power_inputs(Path(root))
    models = [{"case": case, "limits": limits, "result": power(case, limits)} for case in cases]
    if io.manifest(root, POWER_INPUTS) != before: raise ValueError("SOURCE_DRIFT_DURING_ANALYSIS")
    result = {"schema": CONTRACT, "record_id": "EVIDENCE-CORE-DC-" + uuid.uuid4().hex, "check_plan_id": "CHECK-CORE-DC", "created": started, "evidence_class": "HOST_SIM", "execution_status": "COMPLETED", "outcome": "PASS" if all(m["result"]["status"] == "VALID" for m in models) else "FAIL", "target_status": "BLOCKED", "fabrication": "HOLD", "input_manifest": before, "models": models, "producer": {"python": platform.python_version(), "module": "workbench.engineering_register", "digest_profile": "arc-json/1"}, "scope": "Executed DC envelope calculation from existing design inputs. Load, ripple, thermal, delay, PCB drop and physical reset behavior remain unqualified."}
    out = io.project_path(root, "build/register/power_analysis.json", False)
    io.write_json(out, result)
    return result


def snapshot(root):
    root = Path(root).resolve()
    before = binding_inputs(root)
    cfg = io.load(root, ROOT_BINDINGS)
    campaign = io.load(root, "docs/ledger2/REQUIREMENTS.json")
    actions = io.load(root, "docs/ledger2/OPEN_ISSUES.json")
    requirements = []
    for r in campaign["requirements"]:
        requirements.append({"record_id": r["id"], "record_type": "requirement", "subsystem": "Ledger", "statement": r["requirement"], "acceptance_criterion": r.get("acceptance_cases", ""), "definition_state": r.get("status", "OPEN"), "fulfillment": r.get("status", "OPEN"), "first_pass": r.get("first_pass"), "source_refs": [source_ref(root, "docs/ledger2/REQUIREMENTS.json", r["id"])], "check_plan_refs": [], "object_refs": []})
    for r in cfg["requirements"]:
        requirements.append({**r, "record_type": "requirement", "fulfillment": "BLOCKED", "source_refs": [source_ref(root, p, "G2" if r["record_id"].endswith("SUPERVISION") else "game media") for p in r["source_paths"]]})
    action_rows = [{"record_id": r["id"], "record_type": "action", "statement": r["issue"], "owner": r["owner_or_gate"], "status": r["status"], "reference": r["reference"], "source_refs": [source_ref(root, "docs/ledger2/OPEN_ISSUES.json", r["id"])]} for r in actions["issues"]]
    evidence = []
    quantities = []
    report_path = io.project_path(root, "build/register/power_analysis.json", False)
    if report_path.exists():
        r = io.load(root, "build/register/power_analysis.json")
        cur, differences = io.currency(root, r["input_manifest"])
        evidence.append({"record_id": r["record_id"], "record_type": "evidence", "check_plan_id": "CHECK-CORE-DC", "outcome": r["outcome"], "currency": cur, "evidence_class": "HOST_SIM", "target_status": "BLOCKED", "created": r["created"], "changed_inputs": differences, "input_manifest": r["input_manifest"], "summary": "Existing FPGA core DC envelope " + ("meets its modeled inequalities." if r["outcome"] == "PASS" else "fails its modeled inequalities; G2 remains open."), "source_refs": [source_ref(root, "build/register/power_analysis.json")]})
        for i, m in enumerate(r["models"]):
            for name, value in m["result"]["margins_v"].items():
                quantities.append({"record_id": "Q-CORE-%d-%s" % (i + 1, name), "record_type": "quantity", "parameter": name, "value_decimal": str(value), "unit_ucum": "V", "bound": "calculated worst case", "currency": cur, "evidence_class": "HOST_SIM", "evidence_ref": r["record_id"], "conditions": r["scope"], "source_refs": evidence[-1]["source_refs"]})
    else:
        evidence.append({"record_id": "EVIDENCE-CORE-DC-MISSING", "record_type": "evidence", "check_plan_id": "CHECK-CORE-DC", "outcome": None, "currency": "UNASSESSED", "evidence_class": "HOST_SIM", "target_status": "BLOCKED", "summary": "Run register.analyze_power to create a current analysis; no result is prefilled."})
    for plan in cfg["check_plans"]:
        if plan["tool"] is None:
            evidence.append({"record_id": "EVIDENCE-" + plan["record_id"] + "-MISSING", "record_type": "evidence", "check_plan_id": plan["record_id"], "outcome": None, "currency": "MISSING", "evidence_class": plan["evidence_class"], "target_status": "BLOCKED", "summary": plan["missing_reason"]})
    native = native_components(root)
    refs = set(ref for r in cfg["requirements"] for ref in r["object_refs"])
    objects = []
    for ref in sorted(refs):
        c = native.get(ref.removeprefix("R10:"))
        if c:
            objects.append({**c, "record_type": "object", "board_revision": cfg["board_revision"], "source_refs": [source_ref(root, R10 + "cad/NETLIST.xml", c["reference"])]})
        else:
            objects.append({"record_id": ref, "record_type": "object", "state": "MISSING", "missing_reason": "Reference not found in the accepted native netlist."})
    from .firmware_tools import inspect as firmware_inspect
    firmware = firmware_inspect(root)
    for row in requirements + action_rows + evidence + objects + quantities:
        row["record_digest"] = io.digest(row)
    if binding_inputs(root) != before: raise ValueError("SOURCE_DRIFT_DURING_SNAPSHOT")
    identity = {"schema": CONTRACT, "project_id": cfg["project_id"], "baseline_tree_sha256": cfg["baseline_tree_sha256"], "source_catalog_revision": io.digest(before), "register_revision": io.digest({n: before[n] for n in (ROOT_BINDINGS, "docs/ledger2/REQUIREMENTS.json", "docs/ledger2/OPEN_ISSUES.json")}), "input_manifest": before}
    data = {**identity, "board_revision": cfg["board_revision"], "requirements": requirements, "evidence": evidence, "actions": action_rows, "objects": objects, "quantities": quantities, "firmware": firmware["components"], "check_plans": cfg["check_plans"], "unit_profile": UNIT_PROFILE, "fabrication": "HOLD", "flashing": "HOLD", "physical_hardware": False, "publication_profile": "PRIVATE_ENGINEERING", "write_support": "OPERATOR_TYPED_TEXT_CANDIDATE"}
    data["snapshot_id"] = io.digest(data)
    return data


def records(data):
    return [r for kind in ("requirements", "evidence", "actions", "objects", "quantities") for r in data[kind]]


def query(root, args, principal):
    import base64
    data = snapshot(root)
    query_text = args.get("query", "").casefold()
    kind = args.get("record_type")
    rows = data[kind] if kind else records(data)
    rows = [r for r in rows if query_text in io.canonical(r).decode().casefold()]
    signature = io.digest({"snapshot": data["snapshot_id"], "query": query_text, "kind": kind, "principal": principal.identity, "scopes": sorted(principal.scopes)})
    offset = 0
    if args.get("cursor"):
        try: cursor = io.strict_json(base64.urlsafe_b64decode(args["cursor"]).decode())
        except Exception as exc: raise ValueError("INVALID_CURSOR") from exc
        if cursor.get("signature") != signature: raise ValueError("CURSOR_SNAPSHOT_OR_SCOPE_CHANGED")
        offset = cursor.get("offset")
        if type(offset) is not int or not 0 <= offset <= len(rows): raise ValueError("INVALID_CURSOR")
    limit = args.get("limit", 40)
    end = min(len(rows), offset + limit)
    cursor = base64.urlsafe_b64encode(io.canonical({"signature": signature, "offset": end})).decode() if end < len(rows) else None
    return {"schema": CONTRACT, "snapshot_id": data["snapshot_id"], "source_catalog_revision": data["source_catalog_revision"], "records": rows[offset:end], "total": len(rows), "next_cursor": cursor, "truncated": cursor is not None, "fabrication": "HOLD"}


def dispatch(kernel, operation, args, principal):
    if operation == "register.query": return query(kernel.root, args, principal)
    if operation == "register.record":
        data = snapshot(kernel.root)
        row = next((r for r in records(data) if r["record_id"] == args["record_id"]), None)
        if row is None: raise ValueError("UNKNOWN_ID")
        return {"snapshot_id": data["snapshot_id"], "record": row}
    if operation in ("register.export", "register.preview"):
        from . import register_exchange
        return register_exchange.export(kernel, principal) if operation.endswith("export") else register_exchange.preview(kernel, principal, args)
    return snapshot(kernel.root)
