"""Private snapshot exports and strict, non-mutating workbook proposal previews.

The XLSX profile is a populated copy of the reviewed Artifact Tool template.
Only declared typed table cells are exchanged. Formatting and row order grant
no authority. This module never promotes an import or executes a formula.
"""
from __future__ import annotations
import io as streams
import re
import uuid
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile
from . import record_io as io

PROFILE = "arc-ledger.xlsx-register/1"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("", NS)
COLS = {
    "Requirements": ["record_id", "subsystem", "statement", "acceptance_criterion", "definition_state", "fulfillment", "source_refs"],
    "Evidence": ["record_id", "check_plan_id", "outcome", "currency", "evidence_class", "target_status", "summary"],
    "Actions": ["record_id", "statement", "owner", "status", "reference"],
    "Meta": ["key", "value"],
}
EDITABLE = {"Requirements": {"statement", "acceptance_criterion"}, "Actions": {"statement", "owner"}}
MAX_ZIP = 20 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_ROWS = 2000


def col(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def tables(data, export_id):
    def display_refs(refs):
        return "; ".join(r["path"] + ("#" + r["locator"] if r.get("locator") else "") for r in refs or [])
    result = {}
    for sheet, key in (("Requirements", "requirements"), ("Evidence", "evidence"), ("Actions", "actions")):
        result[sheet] = [[display_refs(r.get(c)) if c == "source_refs" else r.get(c) for c in COLS[sheet]] for r in data[key]]
    result["Meta"] = [[k, v] for k, v in {"profile": PROFILE, "export_id": export_id, "snapshot_id": data["snapshot_id"], "project_id": data["project_id"], "baseline_tree_sha256": data["baseline_tree_sha256"], "source_catalog_revision": data["source_catalog_revision"], "register_revision": data["register_revision"], "publication_profile": "PRIVATE_ENGINEERING", "edit_profile": "REQUIREMENT_TEXT_AND_ACTION_TEXT_REVIEW", "promotion": "OPERATOR_TYPED_TEXT_CANDIDATE", "fabrication": "HOLD"}.items()]
    return result


def _cell(address, value, style=None):
    cell = ET.Element("{" + NS + "}c", {"r": address})
    if style is not None: cell.set("s", style)
    if value is None:
        return cell
    if isinstance(value, bool):
        cell.set("t", "b"); ET.SubElement(cell, "{" + NS + "}v").text = "1" if value else "0"
    elif isinstance(value, (int, float)):
        ET.SubElement(cell, "{" + NS + "}v").text = str(value)
    else:
        cell.set("t", "inlineStr")
        text = ET.SubElement(ET.SubElement(cell, "{" + NS + "}is"), "{" + NS + "}t")
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = str(value)
    return cell


def fill_template(root, data, export_id):
    template = io.project_path(root, "project/register/workbook_template.xlsx")
    payload = tables(data, export_id)
    with ZipFile(template) as archive:
        entries = {n: archive.read(n) for n in archive.namelist()}
    wb = ET.fromstring(entries["xl/workbook.xml"])
    rels = {r.get("Id"): r.get("Target").lstrip("/") for r in ET.fromstring(entries["xl/_rels/workbook.xml.rels"])}
    for sheet in wb.findall("{" + NS + "}sheets/{" + NS + "}sheet"):
        name = sheet.get("name")
        if name not in payload: continue
        target = rels[sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
        target = target if target.startswith("xl/") else "xl/" + target
        xml = ET.fromstring(entries[target])
        body = xml.find("{" + NS + "}sheetData")
        style_row = next((r for r in body if int(r.get("r")) == 6), None)
        styles = [c.get("s") for c in style_row] if style_row is not None else []
        for row in list(body):
            if int(row.get("r")) >= 6: body.remove(row)
        for n, values in enumerate(payload[name], 6):
            row = ET.SubElement(body, "{" + NS + "}row", {"r": str(n), "ht": "52" if name != "Meta" else "30", "customHeight": "1"})
            for i, value in enumerate(values): row.append(_cell(col(i + 1) + str(n), value, styles[i] if i < len(styles) else None))
        extent = "A1:%s%d" % (col(len(COLS[name])), max(6, len(payload[name]) + 5))
        dim = xml.find("{" + NS + "}dimension")
        if dim is not None: dim.set("ref", extent)
        entries[target] = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
        for table_name, raw in list(entries.items()):
            if table_name.startswith("xl/tables/") and table_name.endswith(".xml"):
                table = ET.fromstring(raw)
                if table.get("displayName") == "ARC_" + name:
                    table.set("ref", "A5:%s%d" % (col(len(COLS[name])), max(6, len(payload[name]) + 5)))
                    af = table.find("{" + NS + "}autoFilter")
                    if af is not None: af.set("ref", table.get("ref"))
                    entries[table_name] = ET.tostring(table, encoding="utf-8", xml_declaration=True)
    buffer = streams.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as out:
        for n, raw in entries.items(): out.writestr(n, raw)
    return buffer.getvalue()


def export(kernel, principal):
    from .engineering_register import snapshot
    data = snapshot(kernel.root)
    export_id = uuid.uuid4().hex
    folder = io.project_path(kernel.root, ".ledger/register_exports/" + export_id + "/snapshot.json", False, private=True).parent
    folder.mkdir(parents=True, mode=0o700)
    stored = {"owner": principal.identity, "profile": PROFILE, "export_id": export_id, "data": data, "tables": tables(data, export_id), "record_digests": {r["record_id"]: io.digest(r) for k in ("requirements", "evidence", "actions") for r in data[k]}}
    io.write_json(folder / "snapshot.json", stored)
    io.write_json(folder / "register.json", {"profile": PROFILE, "export_id": export_id, "snapshot_id": data["snapshot_id"], "records": {k: data[k.lower()] for k in ("Requirements", "Evidence", "Actions")}})
    io.atomic(folder / "register.xlsx", fill_template(kernel.root, data, export_id))
    return {"export_id": export_id, "snapshot_id": data["snapshot_id"], "profile": PROFILE, "files": [{"path": p.relative_to(kernel.root).as_posix(), "bytes": p.stat().st_size, "sha256": io.sha(p)} for p in (folder / "register.json", folder / "register.xlsx")], "publication_profile": "PRIVATE_ENGINEERING", "import_support": "PREVIEW_THEN_OPERATOR_TEXT_CANDIDATE"}


def read_xlsx(path):
    if path.stat().st_size > MAX_ZIP: raise ValueError("WORKBOOK_SIZE_LIMIT")
    with ZipFile(path) as z:
        infos = z.infolist()
        if len(infos) > 512 or sum(i.file_size for i in infos) > MAX_EXPANDED: raise ValueError("WORKBOOK_EXPANSION_LIMIT")
        if len({i.filename for i in infos}) != len(infos): raise ValueError("DUPLICATE_ZIP_ENTRY")
        entries = {}
        for i in infos:
            p = PurePosixPath(i.filename)
            if p.is_absolute() or ".." in p.parts or "\\" in i.filename: raise ValueError("WORKBOOK_PATH_ESCAPE")
            lower = i.filename.casefold()
            if any(s in lower for s in ("vbaproject", "externallinks", "embeddings/", "connections", "querytables")): raise ValueError("ACTIVE_WORKBOOK_CONTENT")
            raw = z.read(i)
            if i.filename.endswith((".xml", ".rels")):
                if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper(): raise ValueError("XML_ENTITIES_FORBIDDEN")
                xml = ET.fromstring(raw)
                if any(e.get("TargetMode") == "External" for e in xml.iter()): raise ValueError("EXTERNAL_RELATIONSHIP")
                if any("macroEnabled" in str(v) for e in xml.iter() for v in e.attrib.values()): raise ValueError("MACRO_CONTENT_TYPE")
            entries[i.filename] = raw
    shared = []
    if "xl/sharedStrings.xml" in entries:
        shared = ["".join(e.itertext()) for e in ET.fromstring(entries["xl/sharedStrings.xml"])]
    wb = ET.fromstring(entries["xl/workbook.xml"])
    rels = {r.get("Id"): r.get("Target").lstrip("/") for r in ET.fromstring(entries["xl/_rels/workbook.xml.rels"])}
    result = {}
    for sheet in wb.findall("{" + NS + "}sheets/{" + NS + "}sheet"):
        name = sheet.get("name")
        if name not in COLS and name != "Overview": raise ValueError("UNDECLARED_SHEET: " + str(name))
        target = rels[sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
        target = target if target.startswith("xl/") else "xl/" + target
        xml = ET.fromstring(entries[target])
        if xml.findall(".//{" + NS + "}f"): raise ValueError("FORMULA_NOT_ALLOWED_IN_EXCHANGE_PROFILE")
        if name == "Overview": continue
        cells = {}
        for c in xml.findall(".//{" + NS + "}c"):
            address = c.get("r")
            v = c.findtext("{" + NS + "}v")
            if c.get("t") == "s": v = shared[int(v)] if v is not None else None
            elif c.get("t") == "inlineStr": v = "".join(c.find("{" + NS + "}is").itertext())
            elif c.get("t") == "b": v = v == "1"
            elif v is not None and c.get("t") not in ("str", "e"):
                raise ValueError("UNEXPECTED_NUMERIC_CELL: " + str(address))
            if address in cells: raise ValueError("DUPLICATE_CELL")
            cells[address] = v
        headers = [cells.get(col(i + 1) + "5") for i in range(len(COLS[name]))]
        if headers != COLS[name]: raise ValueError("COLUMN_SCHEMA_MISMATCH: " + name)
        rows = []
        indices = sorted({int(re.search(r"\d+$", a)[0]) for a in cells if int(re.search(r"\d+$", a)[0]) >= 6})
        if len(indices) > MAX_ROWS: raise ValueError("ROW_LIMIT")
        for index in indices:
            values = [cells.get(col(i + 1) + str(index)) for i in range(len(headers))]
            if any(v not in (None, "") for v in values): rows.append(dict(zip(headers, values)))
        result[name] = rows
    if set(result) != set(COLS): raise ValueError("MISSING_DECLARED_SHEET")
    return result


def preview(kernel, principal, args):
    from .engineering_register import snapshot
    eid = args["export_id"]
    if len(eid) != 32 or any(c not in "0123456789abcdef" for c in eid): raise ValueError("INVALID_EXPORT_ID")
    stored_path = io.project_path(kernel.root, ".ledger/register_exports/" + eid + "/snapshot.json", private=True)
    stored = io.strict_json(stored_path.read_bytes())
    if stored["owner"] != principal.identity: raise ValueError("EXPORT_PRINCIPAL_MISMATCH")
    name = args["path"]
    if not name.startswith("build/register/imports/"): raise ValueError("IMPORT_PATH_NOT_APPROVED")
    path = io.project_path(kernel.root, name)
    if path.suffix.lower() != ".xlsx": raise ValueError("QUALIFIED_XLSX_REQUIRED")
    try: sheets = read_xlsx(path)
    except (ValueError, KeyError, ET.ParseError, BadZipFile, RuntimeError) as exc:
        return {"status": "REJECTED", "diagnostics": [{"code": str(exc).split(":")[0], "message": str(exc)}], "writes": 0}
    diagnostics = []
    meta_rows = sheets["Meta"]
    meta = {r["key"]: r["value"] for r in meta_rows}
    if len(meta) != len(meta_rows) or meta != dict(stored["tables"]["Meta"]): diagnostics.append({"code": "PROTECTED_META_CHANGED"})
    current = snapshot(kernel.root)
    if current["register_revision"] != stored["data"]["register_revision"] or current["source_catalog_revision"] != stored["data"]["source_catalog_revision"]:
        diagnostics.append({"code": "BASE_DRIFT", "message": "Exported register or source catalog changed; export a fresh base."})
    changes = []; omitted = []
    for sheet in ("Requirements", "Evidence", "Actions"):
        base = {row[0]: dict(zip(COLS[sheet], row)) for row in stored["tables"][sheet]}
        seen = set()
        for row in sheets[sheet]:
            rid = row["record_id"]
            if rid in seen: diagnostics.append({"code": "DUPLICATE_ID", "record_id": rid}); continue
            seen.add(rid)
            if rid not in base: diagnostics.append({"code": "UNKNOWN_ID", "record_id": rid}); continue
            for field, value in row.items():
                before = base[rid].get(field)
                if (value or None) == (before or None): continue
                if field not in EDITABLE.get(sheet, set()): diagnostics.append({"code": "PROTECTED_FIELD", "record_id": rid, "field": field}); continue
                if not isinstance(value, str) or not value.strip() or len(value) > 4000:
                    diagnostics.append({"code": "INVALID_FIELD_VALUE", "record_id": rid, "field": field}); continue
                changes.append({"record_id": rid, "field": field, "before": before, "after": value, "base_digest": stored["record_digests"][rid]})
        # Rows removed from the workbook are listed, never treated as deletions.
        omitted += [{"sheet": sheet, "record_id": rid} for rid in sorted(set(base) - seen)]
    return {"status": "REJECTED" if diagnostics else "PREVIEW", "export_id": eid, "changes": changes, "diagnostics": diagnostics, "writes": 0, "missing_rows_mean_deletion": False, "omitted_rows": omitted, "promotion": "OPERATOR_TYPED_TEXT_CANDIDATE", "candidate_created": False}
