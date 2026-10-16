"""Hardware manifest validation (HW-001..HW-005) and `arc1 hw inspect`."""

from pathlib import Path

from .core import SDK_ROOT, display_path, load_json, schema_validator, sha256_file

MANIFEST_DIR = SDK_ROOT / "hardware" / "manifests"
DEFAULT_BOARD = MANIFEST_DIR / "arc1-r10.hw.json"
HOST_SIM = MANIFEST_DIR / "host-sim.hw.json"

# Fields a board-affecting command must know before it may run (HW-005).
SAFETY_CRITICAL_CHIP_FIELDS = ("manufacturer", "datasheet_ref", "power_domain",
                               "clock_sources", "wiring_source")


def _evidence_ok(ev):
    return isinstance(ev, dict) and all(ev.get(k) for k in ("board_id", "equipment", "log", "log_sha256"))


def check_manifest(doc):
    """Returns a list of (code, json_pointer, message). Empty means valid."""
    errs = [("SCHEMA", p, m) for p, m in schema_validator("hardware.schema.json").errors(doc)]
    if errs:
        return errs

    if doc["simulation_only"] != doc["revision"].startswith("SIM-"):
        errs.append(("HW-005", "/revision",
                     "simulation_only manifests must use a SIM- revision and board manifests must not"))

    chip_ids, mem_ids = set(), set()
    for i, chip in enumerate(doc["chips"]):
        where = "/chips/%d" % i
        if chip["id"] in chip_ids:
            errs.append(("HW-001", where + "/id", "duplicate chip id %r" % chip["id"]))
        chip_ids.add(chip["id"])
        for j, mem in enumerate(chip["memory"]):
            mw = "%s/memory/%d" % (where, j)
            if mem["id"] in mem_ids:
                errs.append(("HW-002", mw + "/id", "duplicate memory id %r" % mem["id"]))
            mem_ids.add(mem["id"])
            if mem["owner"] != chip["id"]:
                errs.append(("HW-002", mw + "/owner",
                             "memory owner %r differs from enclosing chip %r" % (mem["owner"], chip["id"])))
            if mem["shared_address_space"]:
                errs.append(("HW-002", mw + "/shared_address_space",
                             "ARC-1 memory pools are independent; a shared address space claim is rejected"))
            if mem["provenance"] == "BOARD_TEST" and not doc["claims"]["evidence"]:
                errs.append(("HW-002", mw + "/provenance", "BOARD_TEST provenance without board evidence"))
        for dep in chip["boot_dependencies"]:
            if dep not in [c["id"] for c in doc["chips"]]:
                errs.append(("HW-001", where + "/boot_dependencies", "unknown chip %r" % dep))
        if chip["provenance"] == "BOARD_TEST" and not _evidence_ok(doc["claims"]["evidence"]):
            errs.append(("HW-001", where + "/provenance", "BOARD_TEST provenance without board evidence"))

    for i, link in enumerate(doc["links"]):
        where = "/links/%d" % i
        for end in link["endpoints"]:
            if end.split(".", 1)[0] not in chip_ids:
                errs.append(("HW-003", where + "/endpoints", "endpoint %r names an unknown chip" % end))
        measured = link["state"] == "measured"
        if measured and not _evidence_ok(link["evidence"]):
            errs.append(("HW-003", where + "/state", "state 'measured' requires board evidence"))
        if link["measured_throughput_Bps"] is not None and not measured:
            errs.append(("HW-003", where + "/measured_throughput_Bps",
                         "a throughput figure is only allowed for a measured link"))

    claims = doc["claims"]
    positive = claims["physical_boot"] == "pass" or claims["hdmi_audio"] == "pass" or claims["verified_60fps"]
    if positive and not _evidence_ok(claims["evidence"]):
        errs.append(("HW-005", "/claims", "a positive hardware claim requires board evidence"))
    if positive and doc["simulation_only"]:
        errs.append(("HW-005", "/claims", "a simulation_only manifest cannot carry hardware claims"))
    return errs


def unknown_safety_critical(doc):
    out = []
    for chip in doc["chips"]:
        for field in SAFETY_CRITICAL_CHIP_FIELDS:
            if chip.get(field) in (None, []):
                out.append("%s.%s" % (chip["id"], field))
    return out


def summarize(doc):
    pools = [{"id": m["id"], "owner": c["id"], "capacity_bytes": m["capacity_bytes"],
              "shared_address_space": m["shared_address_space"], "provenance": m["provenance"]}
             for c in doc["chips"] for m in c["memory"]]
    return {
        "revision": doc["revision"],
        "simulation_only": doc["simulation_only"],
        "chips": [{"id": c["id"], "part": c["part"], "role": c["role"], "provenance": c["provenance"],
                   "status": c["status"]} for c in doc["chips"]],
        "memory_pools": pools,
        "memory_total_bytes": sum(p["capacity_bytes"] for p in pools),
        "unified_address_space": False,
        "links": [{"id": l["id"], "endpoints": l["endpoints"], "state": l["state"],
                   "measured_throughput_Bps": l["measured_throughput_Bps"]} for l in doc["links"]],
        "claims": doc["claims"],
        "unknown_safety_critical": unknown_safety_critical(doc),
        "uncertainties": doc["uncertainties"],
    }


def inspect(result, manifest_path, chip_id=None):
    path = Path(manifest_path)
    doc = load_json(path, "hardware manifest")
    result.input_digest = sha256_file(path)
    errs = check_manifest(doc)
    for code, ptr, msg in errs:
        result.fail(code, "%s: %s" % (ptr, msg), display_path(path))
    if errs:
        return
    summary = summarize(doc)
    if chip_id:
        chips = [c for c in doc["chips"] if c["id"] == chip_id]
        if not chips:
            result.fail("HW-001", "no chip %r in %s" % (chip_id, doc["revision"]))
            return
        summary = {"revision": doc["revision"], "simulation_only": doc["simulation_only"], "chip": chips[0],
                   "links": [l for l in doc["links"]
                             if any(e.split(".")[0] == chip_id for e in l["endpoints"])]}
    if doc["simulation_only"]:
        result.warn("simulation_only descriptor: facts describe the host model, not ARC-1 hardware")
    else:
        result.warn("Facts are design-level (DESIGN provenance); none are measured on a board")
    result.extra["details"] = {"manifest": display_path(path), "facts": summary}
