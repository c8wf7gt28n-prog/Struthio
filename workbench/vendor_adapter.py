"""Versioned private read adapter over the existing F00 vendor_kb API."""
from __future__ import annotations
from . import record_io as io

CONTRACT = "arc-ledger.vendor-adapter/1"
FIELDS = {
    "vendor.status": ({}, []),
    "vendor.search": ({"query": {"type": "string", "minLength": 1, "maxLength": 200}, "limit": {"type": "integer", "minimum": 1, "maximum": 30}, "document_id": {"type": "string", "maxLength": 100}}, ["query"]),
    "vendor.page": ({"document_id": {"type": "string", "maxLength": 100}, "page_index": {"type": "integer", "minimum": 0, "maximum": 10000}, "original": {"type": "boolean"}}, ["document_id", "page_index"]),
    "vendor.facts": ({"document_id": {"type": "string", "maxLength": 100}}, []),
    "vendor.value": ({"fact_id": {"type": "string", "maxLength": 150}, "design_ref": {"type": "string", "minLength": 1, "maxLength": 200}}, ["fact_id", "design_ref"]),
}


def status(root):
    import vendor_kb as kb
    base = {"schema": CONTRACT, "publication_profile": "PRIVATE_ENGINEERING", "database_is_derived": True, "tool_versions": kb.measured_versions(), "pin_drift": kb.check_pins(kb.load_json(kb.kb_dir(root) / "lock.json"), kb.measured_versions()), "fabrication": "HOLD"}
    try:
        k = kb.open_kb(root)
        try:
            docs = k.documents()
            return {**base, "status": "AVAILABLE", "meta": k.meta, "documents": docs, "facts": k.facts(), "record_set_sha256": k.meta["record_set_sha256"]}
        finally: k.close()
    except kb.KBError as exc:
        catalog = io.load(root, "vendor_kb/catalog.json")
        originals = kb.Originals(root)
        return {**base, "status": "BLOCKED", "reason": str(exc), "documents": [{**d, "source_state": originals.resolve(d)[0]} for d in catalog["documents"]], "facts": []}


def dispatch(kernel, operation, args):
    import vendor_kb as kb
    if operation == "vendor.status": return status(kernel.root)
    try:
        k = kb.open_kb(kernel.root)
        try:
            base = {"schema": CONTRACT, "record_set_sha256": k.meta["record_set_sha256"], "pin_profile": k.meta.get("pin_profile", "F00-original-lock"), "publication_profile": "PRIVATE_ENGINEERING"}
            if operation == "vendor.search":
                limit = args.get("limit", 10)
                hits = k.search(args["query"], limit + 1, document_id=args.get("document_id"))
                return {**base, "hits": hits[:limit], "query": args["query"], "truncated": len(hits) > limit, "scope": "EXTRACTED_TEXT; a search hit is not an approved engineering number"}
            if operation == "vendor.page":
                page = k.open_original(args["document_id"], args["page_index"]) if args.get("original") else k.page(args["document_id"], args["page_index"])
                document = k.document(args["document_id"])
                return {**base, "page": page, "document": document, "fact_state": "EXTRACTED_TEXT"}
            if operation == "vendor.facts": return {**base, "facts": k.facts(args.get("document_id"))}
            return {**base, "value": k.engineering_value(args["fact_id"], args["design_ref"]), "fact_state": "REVIEWED_FACT"}
        finally: k.close()
    except kb.KBError as exc:
        raise ValueError(type(exc).__name__ + ": " + str(exc)) from exc
