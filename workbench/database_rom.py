"""Database ROM workspace and machine API over the shared SDK record store."""
from __future__ import annotations
from sdk.cli.arc1cli import record_store as records

FIELDS = {
    "records.status": ({}, []),
    "records.search": ({"query":{"type":"string","maxLength":200},"limit":{"type":"integer","minimum":1,"maximum":100}},["query"]),
    "records.record": ({"record_id":{"type":"string","maxLength":600},"volume_id":{"type":"string","maxLength":30}},["record_id"]),
    "records.page": ({"record_id":{"type":"string","maxLength":600},"volume_id":{"type":"string","maxLength":30},"page_index":{"type":"integer","minimum":0}},["record_id","page_index"]),
    "records.queue": ({}, []),
    "records.hardware": ({"query":{"type":"string","maxLength":200},"limit":{"type":"integer","minimum":1,"maximum":100}},[]),
    "records.attach": ({"path":{"type":"string","maxLength":1000}},["path"]),
    "records.verify": ({"path":{"type":"string","maxLength":1000}},["path"]),
    "records.stage": ({"paths":{"type":"array","items":{"type":"string"},"minItems":1,"maxItems":2000}},["paths"]),
    "records.prepare": ({"queue_id":{"type":"string","maxLength":32},"volume_id":{"type":"string","maxLength":30}},["queue_id","volume_id"]),
    "records.clear_staging": ({"queue_id":{"type":"string","maxLength":32},"primary_path":{"type":"string","maxLength":1000},"backup_path":{"type":"string","maxLength":1000}},["queue_id","primary_path","backup_path"]),
}
SCOPES = {name: "approve" if name in ("records.attach","records.verify","records.stage","records.prepare","records.clear_staging") else "read" for name in FIELDS}


def select(root, volume_id=None):
    for store in records.stores(root):
        if volume_id is None or store.catalog["volume_id"] == volume_id:return store
    raise records.RecordsError("UNKNOWN_VOLUME")


def dispatch(kernel, op, args):
    root=kernel.root
    if op=="records.status":
        stores=records.stores(root)
        return {"schema":"arc.database-rom/1","volumes":[s.status() for s in stores],"pending":[{"id":q["id"],"state":q["state"],"records":len(q["records"]),"bytes":sum(r["bytes"] for r in q["records"].values())} for q in records.queue_status(root)],"physical_cd_verified":False,"fabrication":"HOLD"}
    if op=="records.search":
        limit=args.get("limit",30);hits=[]
        for store in records.stores(root):hits.extend(store.search(args["query"],limit))
        return {"query":args["query"],"hits":hits[:limit],"truncated":len(hits)>limit,"search_scope":"SEALED_RECORDS_ONLY","design_authority":False}
    if op=="records.hardware":
        store=records.RecordStore(root);path=records.inside(root,store.config["hardware_seed_path"])
        if records.sha(path)!=store.config["hardware_seed_sha256"]:raise records.RecordsError("RESEARCH_SEED_CHANGED")
        data=records.load(path);query=args.get("query","").casefold();limit=args.get("limit",50)
        rows=[row for row in data["facts"] if query in str(row).casefold()]
        gaps=[row for row in data["gaps"] if query in str(row).casefold()]
        return {"edition":data["edition"],"review_state":data["review_state"],"facts":rows[:limit],"gaps":gaps[:limit],"total_facts":len(rows),"total_gaps":len(gaps),"native_counts":data["native_counts"],"fabrication":"HOLD","engineering_use":"NOT_APPROVED","source_seed_sha256":store.config["hardware_seed_sha256"]}
    if op=="records.record":
        store=select(root,args.get("volume_id"));name=args["record_id"]
        location=store.locate(name)
        return {"record_id":name,**store.row(name),"volume_id":store.catalog["volume_id"],"original_state":location["state"],"available":location["path"] is not None,"review_state":"SEALED_SOURCE_REQUIRES_CURRENT_REVIEW"}
    if op=="records.page":return select(root,args.get("volume_id")).page(args["record_id"],args["page_index"])
    if op=="records.queue":return {"entries":records.queue_status(root)}
    if op=="records.attach":return records.attach_volume(root,args["path"])
    if op=="records.verify":return records.verify_volume(args["path"])
    if op=="records.stage":return records.stage_records(root,args["paths"])
    if op=="records.prepare":return records.prepare_queue(root,args["queue_id"],args["volume_id"])
    if op=="records.clear_staging":return records.clear_verified_queue(root,args["queue_id"],args["primary_path"],args["backup_path"])
    raise records.RecordsError("UNKNOWN_RECORDS_OPERATION")
