"""Hardware manifest validation (HW-001..HW-005) and `arc1 hw inspect`."""

from pathlib import Path

from .core import SDK_ROOT, UsageError, bounded, digest_files, display_path, load_json, schema_validator, sha256_file

MANIFEST_DIR = SDK_ROOT / "hardware" / "manifests"
DEFAULT_BOARD = MANIFEST_DIR / "arc1-r10.hw.json"
HOST_SIM = MANIFEST_DIR / "host-sim.hw.json"

# Fields a board-affecting command must know before it may run (HW-005).
SAFETY_CRITICAL_CHIP_FIELDS = ("manufacturer", "datasheet_ref", "power_domain",
                               "clock_sources", "wiring_source")


def _evidence_ok(ev):
    return isinstance(ev, dict) and all(ev.get(k) for k in ("board_id", "equipment", "log", "log_sha256"))


def _check_sources(doc, root, errs):
    """HW-001 traceability: every cited file exists unmodified and every
    reference names a source (and, with #anchor, text that occurs in it)."""
    texts = {}
    for i, src in enumerate(doc["sources"]):
        where = "/sources/%d" % i
        if src["id"] in texts:
            errs.append(("HW-001", where + "/id", "duplicate source id %r" % src["id"]))
            continue
        texts[src["id"]] = None
        try:
            p = bounded(root, src["path"], "source path")
        except UsageError as e:
            errs.append(("HW-001", where + "/path", str(e)))
            continue
        if not p.is_file():
            errs.append(("HW-001", where + "/path", "cited source missing: %s" % src["path"]))
        elif sha256_file(p) != src["sha256"]:
            errs.append(("HW-001", where + "/sha256", "cited source changed: %s" % src["path"]))
        else:
            texts[src["id"]] = p.read_text(encoding="utf-8", errors="replace")

    def ref(value, where, code="HW-001"):
        if value is None:
            return
        sid, _, anchor = value.partition("#")
        if sid not in texts:
            errs.append((code, where, "reference %r names no entry in sources" % value))
        elif anchor and texts[sid] is not None and anchor not in texts[sid]:
            errs.append((code, where, "anchor %r does not occur in source %s" % (anchor, sid)))

    for i, chip in enumerate(doc["chips"]):
        ref(chip["datasheet_ref"], "/chips/%d/datasheet_ref" % i)
        ref(chip["wiring_source"], "/chips/%d/wiring_source" % i)
        for j, mem in enumerate(chip["memory"]):
            ref(mem["source"], "/chips/%d/memory/%d/source" % (i, j), "HW-002")
    for i, per in enumerate(doc["peripherals"]):
        ref(per["source"], "/peripherals/%d/source" % i)
    for i, link in enumerate(doc["links"]):
        for j, r in enumerate(link["sources"]):
            ref(r, "/links/%d/sources/%d" % (i, j), "HW-003")
        if not link["sources"] and not doc["simulation_only"]:
            errs.append(("HW-003", "/links/%d/sources" % i, "a board link must cite at least one source"))


def check_manifest(doc, root=SDK_ROOT):
    """Returns a list of (code, json_pointer, message). Empty means valid.
    Source paths are resolved inside root (the SDK root by default)."""
    errs = [("SCHEMA", p, m) for p, m in schema_validator("hardware.schema.json").errors(doc)]
    if errs:
        return errs

    if doc["simulation_only"] != doc["revision"].startswith("SIM-"):
        errs.append(("HW-005", "/revision",
                     "simulation_only manifests must use a SIM- revision and board manifests must not"))
    if doc["simulation_only"] != (doc["fabrication_status"] == "NOT_APPLICABLE"):
        errs.append(("HW-005", "/fabrication_status",
                     "NOT_APPLICABLE is for simulation_only descriptors only, and they must use it"))

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
            if mem["provenance"] == "BOARD_TEST" and not _evidence_ok(doc["claims"]["evidence"]):
                errs.append(("HW-002", mw + "/provenance", "BOARD_TEST provenance without board evidence"))
        for dep in chip["boot_dependencies"]:
            if dep not in [c["id"] for c in doc["chips"]]:
                errs.append(("HW-001", where + "/boot_dependencies", "unknown chip %r" % dep))
        if chip["provenance"] == "BOARD_TEST" and not _evidence_ok(doc["claims"]["evidence"]):
            errs.append(("HW-001", where + "/provenance", "BOARD_TEST provenance without board evidence"))

    part_ids = set(chip_ids)
    for i, per in enumerate(doc["peripherals"]):
        where = "/peripherals/%d" % i
        if per["id"] in part_ids:
            errs.append(("HW-001", where + "/id", "id %r already names a chip or peripheral" % per["id"]))
        part_ids.add(per["id"])
        if per["provenance"] == "BOARD_TEST" and not _evidence_ok(doc["claims"]["evidence"]):
            errs.append(("HW-001", where + "/provenance", "BOARD_TEST provenance without board evidence"))
    for i, per in enumerate(doc["peripherals"]):
        for att in per["attached_to"]:
            if att not in part_ids or att == per["id"]:
                errs.append(("HW-003", "/peripherals/%d/attached_to" % i, "unknown attachment %r" % att))

    for i, link in enumerate(doc["links"]):
        where = "/links/%d" % i
        for end in link["endpoints"]:
            if end.split(".", 1)[0] not in part_ids:
                errs.append(("HW-003", where + "/endpoints", "endpoint %r names an unknown chip or peripheral" % end))
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
    if doc["fabrication_status"] == "RELEASED" and not (claims["physical_boot"] == "pass" and _evidence_ok(claims["evidence"])):
        errs.append(("HW-005", "/fabrication_status", "RELEASED requires a measured physical boot with board evidence"))

    _check_sources(doc, root, errs)
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
        "fabrication_status": doc["fabrication_status"],
        "sources": [{"id": s["id"], "path": s["path"], "kind": s["kind"]} for s in doc["sources"]],
        "peripherals": [{"id": p["id"], "part": p["part"], "attached_to": p["attached_to"], "status": p["status"]}
                        for p in doc["peripherals"]],
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
    errs = check_manifest(doc)
    cited = []
    if isinstance(doc, dict) and not errs:
        cited = [bounded(SDK_ROOT, s["path"], "source path") for s in doc["sources"]]
    result.input_digest = digest_files(SDK_ROOT, [path] + cited) if cited else sha256_file(path)
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
                             if any(e.split(".")[0] == chip_id for e in l["endpoints"])],
                   "peripherals": [p for p in doc["peripherals"] if chip_id in p["attached_to"]]}
    if doc["simulation_only"]:
        result.warn("simulation_only descriptor: facts describe the host model, not ARC-1 hardware")
    else:
        result.warn("Facts are design-level (DESIGN provenance); none are measured on a board")
        result.warn("Fabrication status: %s" % doc["fabrication_status"])
    result.extra["details"] = {"manifest": display_path(path), "facts": summary}
