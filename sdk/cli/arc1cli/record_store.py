"""Read-only, hash-bound ARC records. Standard library; no GUI or provider.

A catalog describes a sealed edition, not the current truth of a design. The
local search index remains usable with the medium absent. Reading an original
always checks its complete bytes. Mount locations and staging are private state.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import html
from contextlib import closing
import time
import uuid
import sys

SCHEMA = "arc.records-volume/1"
CONFIG = "project/records/volume.json"
BUDGET = 640_000_000  # Owner allowance, decimal MB, including ISO overhead.
MAX_CATALOG = 12_000_000


class RecordsError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""): h.update(part)
    return h.hexdigest()


def strict(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise RecordsError("DUPLICATE_JSON_MEMBER")
            result[key] = value
        return result
    def bad(_): raise RecordsError("NON_FINITE_JSON")
    result = json.loads(data, object_pairs_hook=pairs, parse_constant=bad)
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v): raise RecordsError("NON_FINITE_JSON")
        if isinstance(v, dict):
            for x in v.values(): finite(x)
        if isinstance(v, list):
            for x in v: finite(x)
    finite(result)
    return result


def atomic(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".arc-record-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data if isinstance(data, bytes) else canonical(data) + b"\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def safe_name(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\0" in name:
        raise RecordsError("INVALID_RECORD_PATH")
    parts=name.split("/")
    if any(ord(c)<32 or c in '<>"|?*' for c in name):raise RecordsError("NONPORTABLE_RECORD_PATH")
    if any(re.fullmatch(r"(?i)(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?",x) for x in parts):raise RecordsError("RESERVED_DEVICE_PATH")
    if any(x in ("", ".", "..") or x.startswith(".") and not (i==len(parts)-1 and x in (".gitignore", ".gitattributes", ".editorconfig")) for i,x in enumerate(parts)):
        raise RecordsError("INVALID_RECORD_PATH")
    return name


def inside(folder, name):
    name = safe_name(name); root = Path(folder).absolute()
    path = root.joinpath(*name.split("/"))
    # Check lexical ancestors before resolving, including the selected root.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RecordsError("SYMLINK_RECORD_PATH")
    if not path.resolve().is_relative_to(root.resolve()): raise RecordsError("RECORD_PATH_ESCAPE")
    return path


def load(path, cap=MAX_CATALOG):
    path = Path(path)
    if path.stat().st_size > cap: raise RecordsError("RECORD_METADATA_LIMIT")
    return strict(path.read_bytes())


def object_name(digest):
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest): raise RecordsError("INVALID_OBJECT_HASH")
    return "objects/" + digest[:2] + "/" + digest[2:]


def check_catalog(catalog):
    if catalog.get("schema") != "arc.records-catalog/1": raise RecordsError("CATALOG_SCHEMA")
    if not isinstance(catalog.get("volume_id"),str) or not re.fullmatch(r"ARC-ROM-[0-9]{3,6}",catalog['volume_id']):raise RecordsError("VOLUME_ID")
    records = catalog.get("records")
    if not isinstance(records, dict) or len(records) > 20000: raise RecordsError("CATALOG_RECORD_LIMIT")
    for name, row in records.items():
        safe_name(name)
        if row.get("object") != object_name(row.get("sha256")): raise RecordsError("OBJECT_PATH_HASH_MISMATCH")
        n = row.get("bytes")
        if type(n) is not int or not 0 <= n <= BUDGET: raise RecordsError("OBJECT_SIZE_LIMIT")
    return catalog


def verify_volume(folder, expected=None):
    """Full logical readback. A directory/ISO test does not prove a burned CD."""
    folder = Path(folder).absolute(); mp = inside(folder, "VOLUME.json")
    identity = sha(mp)
    if expected and identity != expected: raise RecordsError("WRONG_VOLUME_IDENTITY")
    manifest = load(mp)
    if manifest.get("schema") != SCHEMA or manifest.get("budget_bytes") != BUDGET:
        raise RecordsError("VOLUME_SCHEMA_OR_BUDGET")
    catalog_path = inside(folder, "CATALOG.json")
    if sha(catalog_path) != manifest["catalog_sha256"]: raise RecordsError("CATALOG_HASH_MISMATCH")
    catalog = check_catalog(load(catalog_path))
    if catalog["volume_id"] != manifest["volume_id"]: raise RecordsError("VOLUME_CATALOG_MISMATCH")
    seen = {}; count = 0
    for name, entry in catalog["records"].items():
        digest = entry["sha256"]
        if digest in seen:
            if seen[digest] != entry["bytes"]: raise RecordsError("DUPLICATE_OBJECT_SIZE")
            continue
        path = inside(folder, entry["object"])
        if not path.is_file() or path.stat().st_size != entry["bytes"] or sha(path) != digest:
            raise RecordsError("CORRUPT_OR_MISSING_OBJECT: " + name)
        seen[digest] = entry["bytes"]; count += 1
    for name, row in manifest.get("sidecars", {}).items():
        path = inside(folder, name)
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise RecordsError("SIDECAR_HASH_MISMATCH: " + name)
    actual = 0;entry_count=0
    for path in folder.rglob("*"):
        if path.is_symlink(): raise RecordsError("SYMLINK_VOLUME_ENTRY")
        if path.is_file():
            actual += path.stat().st_size;entry_count+=1
            if actual>BUDGET or entry_count>40050:raise RecordsError("VOLUME_ENUMERATION_LIMIT")
    if actual > BUDGET: raise RecordsError("VOLUME_OVER_BUDGET")
    if sum(seen.values()) != manifest["unique_object_bytes"]: raise RecordsError("VOLUME_ACCOUNTING_MISMATCH")
    return {"volume_id": manifest["volume_id"], "manifest_sha256": identity,
            "records": len(catalog["records"]), "unique_objects": count, "folder_bytes": actual,
            "budget_bytes": BUDGET, "remaining_bytes": BUDGET - actual,
            "verification": "LOGICAL_FULL_READBACK", "physical_cd_verified": False}


def create_volume(destination, volume_id, entries, pages=None, sidecars=None):
    """Create a new immutable, deduplicated volume. Never replace an edition.

    entries maps logical names to {source: Path, kind/title/metadata: optional}.
    pages is an iterable of (logical_name, zero_based_index, label, plain_text).
    A caller can supply vendor-native PDF extraction without adding it to SDK.
    """
    if not re.fullmatch(r"ARC-ROM-[0-9]{3,6}", volume_id): raise RecordsError("VOLUME_ID")
    destination = Path(destination).absolute()
    if destination.exists(): raise RecordsError("SEALED_DESTINATION_EXISTS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".arc-rom-", dir=destination.parent))
    try:
        records = {}; unique = {}
        for name, entry in sorted(entries.items()):
            safe_name(name); source = Path(entry["source"])
            if not source.is_file() or source.is_symlink(): raise RecordsError("INVALID_RECORD_SOURCE")
            size = source.stat().st_size; digest = sha(source); obj = object_name(digest)
            if digest not in unique:
                if sum(unique.values()) + size > BUDGET - 8_000_000: raise RecordsError("VOLUME_PAYLOAD_OVER_BUDGET")
                target = inside(stage, obj); target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if target.stat().st_size != size or sha(target) != digest: raise RecordsError("SOURCE_CHANGED_DURING_SEAL")
                unique[digest] = size
            records[name] = {"sha256": digest, "bytes": size, "object": obj,
                             "mode": source.stat().st_mode & 0o777, "kind": entry.get("kind", "record"),
                             "title": entry.get("title", Path(name).name), "metadata": entry.get("metadata", {})}
        catalog = {"schema": "arc.records-catalog/1", "volume_id": volume_id,
                   "records": records, "edition_state": "SEALED_SNAPSHOT_NOT_ACCEPTANCE"}
        atomic(stage / "CATALOG.json", catalog)
        index = stage / "SEARCH.sqlite"
        with closing(sqlite3.connect(index)) as con:
            con.execute("CREATE VIRTUAL TABLE pages USING fts5(record_path UNINDEXED,page_index UNINDEXED,page_label UNINDEXED,body,tokenize='unicode61')")
            if pages is None:
                pages = ((n, 0, "record", e["title"] + " " + n) for n, e in records.items())
            for name, page_index, label, text in pages:
                if name not in records or type(page_index) is not int or page_index < 0: raise RecordsError("INDEX_DANGLING_SOURCE")
                con.execute("INSERT INTO pages VALUES(?,?,?,?)", (name, page_index, str(label), text))
            con.commit(); con.execute("INSERT INTO pages(pages) VALUES('optimize')"); con.commit()
        sidecar_rows = {"SEARCH.sqlite": {"sha256": sha(index), "bytes": index.stat().st_size}}
        for name, source in (sidecars or {}).items():
            if name in ("VOLUME.json", "CATALOG.json", "SEARCH.sqlite") or name.startswith("objects/"):
                raise RecordsError("RESERVED_SIDECAR_PATH")
            target = inside(stage, name); target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
            sidecar_rows[name] = {"sha256": sha(target), "bytes": target.stat().st_size}
        rows = "".join('<tr><td>'+html.escape(e["kind"])+'</td><td><a download="'+html.escape(Path(n).name, quote=True)+'" href="'+e["object"]+'">'+html.escape(n)+'</a></td><td>'+str(e["bytes"])+'</td></tr>' for n,e in records.items())
        guide = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>'+volume_id+' - ARC Database ROM</title>'
                 '<style>body{background:#161a1e;color:#eee;font:16px system-ui;margin:32px}h1,a{color:#ff9a54}input{font:inherit;padding:10px;width:75%}table{width:100%;border-collapse:collapse;margin-top:20px}td,th{border:1px solid #505860;padding:7px;text-align:left}small{color:#c4ccd4}</style>'
                 '<h1>ARC Database ROM - '+volume_id+'</h1><p>Sealed engineering records. This edition does not approve a circuit or close a physical gate.</p>'
                 '<p>Mount this volume in Ledger: View &gt; Database ROM &gt; Attach volume. Search remains available from the local catalog when the disc is absent.</p>'
                 '<p>Original filenames are retained in the catalog. File contents are deduplicated by SHA-256. Links download the original bytes using their logical filenames.</p>'
                 '<p>Keep another independent copy. Writing this image does not by itself verify a physical CD.</p>'
                 '<input id="q" placeholder="poem" title="Filter by part, path or category" aria-label="Filter records"><table><thead><tr><th>Category</th><th>Original path</th><th>Bytes</th></tr></thead><tbody>'+rows+'</tbody></table>'
                 '<script>document.getElementById("q").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))})</script></html>')
        (stage / "START_HERE.html").write_text(guide)
        sidecar_rows["START_HERE.html"] = {"sha256": sha(stage / "START_HERE.html"), "bytes": (stage / "START_HERE.html").stat().st_size}
        manifest = {"schema": SCHEMA, "volume_id": volume_id, "budget_bytes": BUDGET,
                    "catalog_sha256": sha(stage / "CATALOG.json"), "unique_object_bytes": sum(unique.values()),
                    "sidecars": sidecar_rows, "physical_cd_verified": False}
        atomic(stage / "VOLUME.json", manifest)
        result = verify_volume(stage)
        os.replace(stage, destination)
        return result
    finally:
        if stage.exists(): shutil.rmtree(stage)


class RecordStore:
    def __init__(self, root, binding_directory=None):
        self.root = Path(root).resolve()
        self.base = Path(binding_directory) if binding_directory else self.root
        self.config = load(inside(self.base, "volume.json" if binding_directory else CONFIG))
        if self.config.get("schema") != "arc.records-binding/1": raise RecordsError("BINDING_SCHEMA")
        catalog_path = inside(self.base, self.config["catalog_path"])
        if sha(catalog_path) != self.config["catalog_sha256"]: raise RecordsError("LOCAL_CATALOG_CHANGED")
        self.catalog = check_catalog(load(catalog_path))
        if self.catalog["volume_id"] != self.config["volume_id"]: raise RecordsError("BINDING_VOLUME_MISMATCH")
        self.records = self.catalog["records"]

    @property
    def private(self):
        path = self.root / ".ledger" / "records"
        if any(p.is_symlink() for p in (path, path.parent)): raise RecordsError("SYMLINK_PRIVATE_RECORDS")
        return path

    def mounts(self):
        paths = []
        state = self.private / "mounts.json"
        if state.is_file():
            for item in load(state).get("mounts", []):
                if item.get("manifest_sha256") == self.config["manifest_sha256"]: paths.append(Path(item["path"]))
        # Owner-local override, never part of a distributed project package.
        for item in os.environ.get("ARC_RECORDS_VAULT", "").split(os.pathsep):
            if item: paths.append(Path(item))
        return list(dict.fromkeys(paths))

    def row(self, name):
        safe_name(name)
        if name not in self.records: raise RecordsError("NOT_CATALOGUED: " + name)
        return self.records[name]

    def locate(self, name):
        row = self.row(name)
        local = inside(self.root, name)
        candidates = [local, inside(self.private / "cache", row["object"])]
        damaged = False
        for mount in self.mounts():
            try:
                mp = inside(mount, "VOLUME.json")
                if not mp.is_file() or sha(mp) != self.config["manifest_sha256"]: continue
                candidates.append(inside(mount, row["object"]))
            except (OSError, ValueError): continue
        for path in candidates:
            if path.is_file():
                if path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]:
                    return {"state": "VERIFIED_LOCAL", "path": path, "sha256": row["sha256"]}
                damaged = True
        return {"state": "CORRUPT" if damaged else "ROM_REQUIRED", "path": None, "sha256": row["sha256"]}

    def read(self, name, limit=2_000_000):
        row = self.row(name)
        if row["bytes"] > limit: raise RecordsError("RECORD_READ_LIMIT; locate the original instead")
        result = self.locate(name)
        if result["path"] is None: raise RecordsError(result["state"] + ": insert " + self.catalog["volume_id"])
        return result["path"].read_bytes()

    def attach(self, folder):
        result = verify_volume(folder, self.config["manifest_sha256"])
        if self.config.get("full_index_sha256"):
            source=inside(folder,"SEARCH.sqlite")
            if sha(source)!=self.config["full_index_sha256"]:raise RecordsError("FULL_INDEX_HASH_MISMATCH")
            target=self.full_index_cache();target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            fd,temporary=tempfile.mkstemp(prefix=".index-",dir=target.parent)
            try:
                with os.fdopen(fd,"wb") as out,source.open("rb") as stream:
                    shutil.copyfileobj(stream,out);out.flush();os.fsync(out.fileno())
                if sha(temporary)!=self.config["full_index_sha256"]:raise RecordsError("FULL_INDEX_COPY_CHANGED")
                os.replace(temporary,target)
            finally:
                if os.path.exists(temporary):os.unlink(temporary)
        path = str(Path(folder).resolve()); old = self.mounts()
        rows = [{"path": str(p), "manifest_sha256": self.config["manifest_sha256"]} for p in old if str(p.resolve()) != path]
        rows.append({"path": path, "manifest_sha256": result["manifest_sha256"]})
        atomic(self.private / "mounts.json", {"schema": "arc.records-mounts/1", "mounts": rows})
        return result

    def full_index_cache(self):
        override=os.environ.get("ARC_RECORDS_HOME")
        if override:base=Path(override)
        elif sys.platform=="win32":base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData/Local")))/"ArcLedger/records"
        elif sys.platform=="darwin":base=Path.home()/"Library/Application Support/ArcLedger/records"
        else:base=Path(os.environ.get("XDG_DATA_HOME",str(Path.home()/".local/share")))/"arc-ledger/records"
        return inside(base,self.config["manifest_sha256"]+"/SEARCH.sqlite")

    def _index_choice(self):
        path = inside(self.base, self.config["index_path"])
        if sha(path) != self.config["index_sha256"]: raise RecordsError("SEARCH_INDEX_CHANGED")
        if self.config.get("full_index_sha256"):
            cached=self.full_index_cache()
            if cached.is_file():
                if sha(cached)!=self.config["full_index_sha256"]:raise RecordsError("FULL_INDEX_CACHE_CHANGED; reattach a verified volume")
                return cached,"FULL_SEALED_TEXT"
            return path,"CATALOG_AND_RESEARCH"
        return path,"FULL_SEALED_TEXT"

    def _index(self):
        path,self.index_scope=self._index_choice()
        # An SSD cache may change even after a successful earlier hash check.
        # Open an isolated, exact-byte snapshot without asserting immutable media.
        from .knowledge_sources import pinned_index
        expected=(self.config["full_index_sha256"]
                  if self.config.get("full_index_sha256") and self.index_scope=="FULL_SEALED_TEXT"
                  else self.config["index_sha256"])
        return pinned_index(path,expected)

    def search(self, query, limit=30):
        if not isinstance(query, str) or len(query) > 200 or type(limit) is not int or not 1 <= limit <= 100:
            raise RecordsError("QUERY_LIMIT")
        terms = re.findall(r"\w+", query, re.UNICODE)
        if not terms: return []
        match = " AND ".join('"' + x.replace('"', '""') + '"' for x in terms[:20])
        with closing(self._index()) as con:
            rows = con.execute("SELECT record_path,page_index,page_label,snippet(pages,3,'[',']',' ... ',28) FROM pages WHERE pages MATCH ? ORDER BY bm25(pages),record_path,page_index LIMIT ?", (match, limit)).fetchall()
        states = {n: self.locate(n)["state"] for n, *_ in rows}
        return [{"record_id": n, "page_index": int(i), "page_label": label, "excerpt": body,
                 "source_sha256": self.row(n)["sha256"], "volume_id": self.catalog["volume_id"],
                 "original_state": states[n], "content_state": "CATALOG_METADATA" if label=="catalog" else "SEALED_INDEXED_TEXT",
                 "index_scope": self.index_scope,
                 "review_state": "NOT_DESIGN_AUTHORITY"} for n, i, label, body in rows]

    def page(self, name, page_index):
        row = self.row(name)
        if type(page_index) is not int or page_index < 0: raise RecordsError("PAGE_INDEX")
        with closing(self._index()) as con:
            item = con.execute("SELECT page_label,body FROM pages WHERE record_path=? AND page_index=? LIMIT 1", (name, page_index)).fetchone()
        if item is None: raise RecordsError("NO_INDEXED_PAGE")
        return {"record_id": name, "page_index": page_index, "page_label": item[0], "text": item[1][:16000],
                "truncated": len(item[1]) > 16000, "source_sha256": row["sha256"],
                "original_state": self.locate(name)["state"], "content_state": "CATALOG_METADATA" if item[0]=="catalog" else "SEALED_INDEXED_TEXT",
                "index_scope":self.index_scope,
                "review_state": "NOT_DESIGN_AUTHORITY", "volume_id": self.catalog["volume_id"]}

    def status(self):
        try:index,scope=self._index_choice();available=True;reason=None
        except (OSError,ValueError) as exc:available=False;scope="UNAVAILABLE";reason=str(exc)
        return {"volume_id": self.catalog["volume_id"], "manifest_sha256": self.config["manifest_sha256"],
                "records": len(self.records), "unique_object_bytes": self.config["unique_object_bytes"],
                "budget_bytes": BUDGET, "mounts": len(self.mounts()), "search_available": available,
                "index_scope":scope,"index_problem":reason,
                "archive_is_current_design": False, "physical_cd_verified": False}


def stores(root):
    result = [RecordStore(root)]
    parent = result[0].private / "catalogs"
    if parent.is_dir():
        for path in sorted(parent.iterdir()):
            if re.fullmatch(r"ARC-ROM-[0-9]{3,6}", path.name):
                result.append(RecordStore(root, path))
    return result


def attach_volume(root, folder):
    primary = RecordStore(root)
    result = verify_volume(folder)
    if result["volume_id"] == primary.config["volume_id"]:
        return primary.attach(folder)
    target = inside(primary.private,"catalogs/"+result["volume_id"])
    if target.exists():
        other = RecordStore(root, target)
        if other.config["manifest_sha256"] != result["manifest_sha256"]: raise RecordsError("SEALED_VOLUME_ID_CONFLICT")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".catalog-", dir=target.parent))
        try:
            for name in ("CATALOG.json", "SEARCH.sqlite"): shutil.copyfile(inside(folder, name), stage/name)
            cfg = {"schema": "arc.records-binding/1", "volume_id": result["volume_id"],
                   "manifest_sha256": result["manifest_sha256"], "catalog_path": "CATALOG.json", "index_path": "SEARCH.sqlite",
                   "catalog_sha256": sha(stage/"CATALOG.json"), "index_sha256": sha(stage/"SEARCH.sqlite"),
                   "unique_object_bytes": load(inside(folder,"VOLUME.json"))["unique_object_bytes"]}
            atomic(stage/"volume.json", cfg); os.replace(stage,target)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    return RecordStore(root,target).attach(folder)


def stage_records(root, names):
    """Durable copies of explicitly selected records; never move current source."""
    store = RecordStore(root)
    if not isinstance(names,list) or not 1 <= len(names) <= 2000 or len(names) != len(set(names)):
        raise RecordsError("STAGING_SELECTION_LIMIT")
    sources = {}; total = 0
    for name in names:
        if not name.startswith(("build/", "passes/", "project/records/incoming/")):
            raise RecordsError("STAGING_REQUIRES_OUTPUT_OR_INCOMING_RECORD")
        path = inside(store.root,name)
        if not path.is_file(): raise RecordsError("STAGING_SOURCE_MISSING")
        total += path.stat().st_size
        if total > BUDGET-8_000_000: raise RecordsError("STAGING_OVER_BUDGET")
        sources[name] = path
    parent = inside(store.private,"staging"); parent.mkdir(parents=True,exist_ok=True)
    ident = uuid.uuid4().hex; stage = Path(tempfile.mkdtemp(prefix=".queue-",dir=parent))
    try:
        rows = {}
        for name,path in sorted(sources.items()):
            digest=sha(path); target=inside(stage,object_name(digest)); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
            if sha(target)!=digest: raise RecordsError("STAGING_SOURCE_CHANGED")
            rows[name]={"sha256":digest,"bytes":target.stat().st_size,"object":object_name(digest)}
        receipt={"schema":"arc.records-queue/1","id":ident,"state":"PENDING_ARCHIVE","created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"records":rows,"source_files_removed":False}
        atomic(stage/"queue.json",receipt); os.replace(stage,parent/ident)
        return receipt
    finally:
        if stage.exists():shutil.rmtree(stage)


def queue_record(root, ident):
    if not isinstance(ident,str) or not re.fullmatch(r"[0-9a-f]{32}",ident):raise RecordsError("QUEUE_ID")
    store=RecordStore(root);path=inside(store.private,"staging/"+ident)
    if path.is_symlink():raise RecordsError("SYMLINK_QUEUE")
    return path,load(path/"queue.json")


def queue_status(root):
    store=RecordStore(root);parent=inside(store.private,"staging")
    if not parent.is_dir():return []
    return [queue_record(root,p.name)[1] for p in sorted(parent.iterdir()) if re.fullmatch(r"[0-9a-f]{32}",p.name)]


def prepare_queue(root, ident, volume_id):
    path,queue=queue_record(root,ident)
    if queue["state"]!="PENDING_ARCHIVE":raise RecordsError("QUEUE_NOT_PENDING")
    entries={}
    for name,row in queue["records"].items():
        source=inside(path,row["object"])
        if sha(source)!=row["sha256"]:raise RecordsError("STAGED_RECORD_CHANGED")
        entries[name]={"source":source,"kind":"sealed-development-record"}
    output=inside(RecordStore(root).private,"volumes/"+volume_id)
    result=create_volume(output,volume_id,entries)
    queue.update(state="PREPARED_AWAITING_READBACK",volume_id=volume_id,manifest_sha256=result["manifest_sha256"],prepared_path=str(output))
    atomic(path/"queue.json",queue)
    return {**result,"folder":str(output),"queue_id":ident,"source_files_removed":False}


def clear_verified_queue(root, ident, primary_path, backup_path):
    """Clear only staged copies after two distinct full readbacks and indexing.

    Two path locations do not prove physically independent media. The returned
    evidence says so. Active files are never removed by this operation.
    """
    path,queue=queue_record(root,ident)
    if queue["state"]=="CLEARED":return queue
    if queue["state"]!="PREPARED_AWAITING_READBACK":raise RecordsError("QUEUE_NOT_PREPARED")
    a=Path(primary_path).resolve();b=Path(backup_path).resolve()
    if a==b or a.is_relative_to(b) or b.is_relative_to(a):raise RecordsError("SECOND_COPY_REQUIRED")
    store=RecordStore(root)
    if any(p.is_relative_to(path) for p in (a,b)):raise RecordsError("STAGING_IS_NOT_A_BACKUP")
    one=verify_volume(a,queue["manifest_sha256"]);two=verify_volume(b,queue["manifest_sha256"])
    volume=load(inside(a,"CATALOG.json"))
    for name,row in queue["records"].items():
        if volume["records"].get(name,{}).get("sha256")!=row["sha256"]:raise RecordsError("QUEUE_VOLUME_MISMATCH")
        staged=inside(path,row["object"])
        if not staged.is_file() or sha(staged)!=row["sha256"]:raise RecordsError("STAGED_RECORD_CHANGED")
    attach_volume(root,a)  # Retain its local catalog/index before removing copies.
    queue.update(state="CLEARED",readbacks=[one,two],physical_media_independence="UNASSESSED",source_files_removed=False)
    atomic(path/"queue.json",queue)
    objects=inside(path,"objects")
    if objects.exists():shutil.rmtree(objects)
    return queue


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("action", choices=("status", "search", "locate", "verify", "mount"))
    p.add_argument("value", nargs="?"); a = p.parse_args(argv)
    try:
        store = RecordStore(a.root)
        if a.action == "status": result = store.status()
        elif a.action == "search": result = store.search(a.value or "")
        elif a.action == "locate": result = store.locate(a.value or "")
        elif a.action == "mount": result = store.attach(a.value or "")
        else: result = verify_volume(a.value or "", store.config["manifest_sha256"])
        print(json.dumps(result, default=str, indent=2)); return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)})); return 3


if __name__ == "__main__": raise SystemExit(main())
