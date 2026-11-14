"""staC CCC 0.3: opt-in, tamper-evident chronology of *read observations*.

This is NOT Ledger's Engineering Kernel event log or an execution authority.
Historical snapshots report what staC observed at recording time; they cannot
prove past physical state or reconstruct missing original documents.

Writes are deliberately restricted to .ledger/stac/chronicle.sqlite3 and an
optional local head anchor. Untrusted programs/LLM output cannot write directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import os
import re
import sqlite3
import time
from typing import Optional

from .. import record_io
from .. import locations

SCHEMA = 'arc.stac.ccc.event/0.3'
RESULT_SCHEMA = 'arc.stac.ccc.result/0.3'
PROFILE = 'arc-record-io-json/1'  # Keep existing pass 002 digest profile; NOT RFC 8785
GENESIS = '0' * 64
HASH_RE = re.compile(r'^[a-f0-9]{64}$')
COMPONENT_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')
MAX_EVENTS = 100000  # Bound verification work; a larger archive requires explicit migration
MAX_ROWS = 200


class ChronicleError(ValueError):
    pass


def _paths(root, create=False):
    root = Path(root).resolve()
    base = root / '.ledger'
    directory = base / 'stac'
    dbpath = directory / 'chronicle.sqlite3'
    anchor = directory / 'chronicle.head.json'
    for item in (base, directory, dbpath, anchor):
        if item.is_symlink():
            raise ChronicleError('SYMLINK_CHRONICLE_PATH: private chronology path may not be a symlink')
    if create:
        if not (locations.program(root) / 'workbench/engineering_kernel.py').is_file():
            raise ChronicleError('INVALID_LEDGER_ROOT')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != 'nt':
            directory.chmod(0o700)
    return dbpath, anchor


def _connection(root, writable=False) -> tuple[Optional[sqlite3.Connection], Path]:
    path, anchor = _paths(root, create=writable)
    if not path.exists() and not writable:
        return None, anchor
    db = None
    try:
        if writable:
            db = sqlite3.connect(path, timeout=5)
            if os.name != 'nt':
                path.chmod(0o600)
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('''CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY,
              recorded_ns INTEGER NOT NULL,
              event_json TEXT NOT NULL,
              prev_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL UNIQUE
            )''')
        else:
            db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
        db.execute('PRAGMA busy_timeout=5000')
    except (sqlite3.Error, OSError) as exc:
        if db is not None:
            db.close()
        raise ChronicleError('CHRONICLE_DATABASE_UNAVAILABLE_OR_CORRUPT') from exc
    return db, anchor


def _anchor(anchor):
    if not anchor.is_file():
        return None
    try:
        obj = record_io.strict_json(anchor.read_bytes())
    except (OSError, ValueError) as exc:
        raise ChronicleError('INVALID_CHRONICLE_ANCHOR') from exc
    if (not isinstance(obj, dict) or set(obj) != {'schema', 'profile', 'count', 'head_hash'}
        or obj['schema'] != 'arc.stac.ccc.anchor/0.3' or obj['profile'] != PROFILE
        or type(obj['count']) is not int or obj['count'] < 0
        or not isinstance(obj['head_hash'], str) or not HASH_RE.fullmatch(obj['head_hash'])):
        raise ChronicleError('INVALID_CHRONICLE_ANCHOR')
    return obj


def _verified_rows(db, anchor_path):
    sealed = _anchor(anchor_path)
    if db is None:
        if sealed and sealed['count']:
            raise ChronicleError('ANCHOR_HAS_NO_DATABASE: chronology is missing')
        return [], GENESIS, sealed
    try:
        raw = db.execute('SELECT seq,recorded_ns,event_json,prev_hash,event_hash FROM events ORDER BY seq').fetchall()
    except sqlite3.Error as exc:
        raise ChronicleError('CHRONICLE_SCHEMA_INVALID') from exc
    if len(raw) > MAX_EVENTS:
        raise ChronicleError('CHRONICLE_EVENT_LIMIT: archive/rotate before continuing')
    rows=[];parent=GENESIS
    for n,(seq,clock,encoded,previous,digest) in enumerate(raw, 1):
        if seq != n or type(clock) is not int or type(encoded) is not str or len(encoded) > 65536:
            raise ChronicleError(f'CHRONICLE_INVALID_ROW at sequence {n}')
        try:
            obj=record_io.strict_json(encoded)
        except ValueError as exc:
            raise ChronicleError(f'CHRONICLE_UNPARSABLE_EVENT at sequence {n}') from exc
        if (not isinstance(obj,dict) or obj.get('schema') != SCHEMA or obj.get('profile') != PROFILE
            or obj.get('sequence') != seq or obj.get('recorded_ns') != clock
            or obj.get('prev_hash') != previous or previous != parent
            or not isinstance(digest,str) or not HASH_RE.fullmatch(digest)):
            raise ChronicleError(f'CHRONICLE_CHAIN_BROKEN at sequence {n}')
        if record_io.digest(obj) != digest:
            raise ChronicleError(f'CHRONICLE_DIGEST_MISMATCH at sequence {n}')
        ir = obj.get('ir')
        legacy_read = (obj.get('kind') == 'READ_OBSERVATION' and obj.get('status') == 'OBSERVED'
            and isinstance(ir, dict) and obj.get('intent_digest') == record_io.digest(ir)
            and ir.get('effects') in ([], ['read']))
        reason_read = (obj.get('kind') == 'REASON_RECOMPUTATION' and obj.get('status') == 'OBSERVED'
            and isinstance(ir, dict) and set(ir)=={'graph','graph_revision','context_digest','definition_digest','effects'}
            and ir.get('effects') == ['read'] and obj.get('intent_digest') == record_io.digest(ir)
            and isinstance(obj.get('reason_result'),str) and re.fullmatch('[0-9a-f]{32}',obj['reason_result'])
            and all(isinstance(ir.get(k),str) and HASH_RE.fullmatch(ir[k]) for k in ('context_digest','definition_digest'))
            and isinstance(ir.get('graph'),str) and re.fullmatch('[0-9a-f]{32}',ir['graph'])
            and type(ir.get('graph_revision')) is int and ir['graph_revision']>=1)
        if (not (legacy_read or reason_read)
            or not isinstance(ir, dict) or obj.get('intent_digest') != record_io.digest(ir)
            or ir.get('effects') not in ([], ['read'])
            or not isinstance(obj.get('result_digest'), str)
            or not HASH_RE.fullmatch(obj['result_digest'])
            or (obj.get('result_summary') or {}).get('physical_qualification') != 'NOT_DEMONSTRATED'):
            raise ChronicleError(f'CHRONICLE_EVENT_INVARIANT_FAILURE at sequence {n}')
        rows.append((obj,digest));parent=digest
        if sealed and n == sealed['count'] and parent != sealed['head_hash']:
            raise ChronicleError('CHRONICLE_SEALED_PREFIX_MISMATCH')
    if sealed and (sealed['count'] > len(rows)
                   or (sealed['count'] == 0 and sealed['head_hash'] != GENESIS)):
        raise ChronicleError('CHRONICLE_TRUNCATED_BEFORE_SEALED_HEAD')
    return rows,parent,sealed


def _meta(result):
    """Allowlisted and bounded summary. Never store original vendor page text or full chat."""
    kind = result.get('result', {}).get('type','UNKNOWN')
    body = result.get('result', {}).get('payload',{})
    if not isinstance(body,dict):body={}
    summary={'result_type':kind, 'state':str(body.get('state', body.get('knowledge_state','NOT_ASSESSED')))[:64],
             'physical_qualification': 'NOT_DEMONSTRATED'}
    if kind == 'PartInspection':
        summary['component']=str(body.get('component',{}).get('reference',''))[:40]
        summary['native_mpn']=str(body.get('component',{}).get('value',''))[:120]
    elif kind == 'FactInquiry':
        summary['component']=str(body.get('component',''))[:40]
        summary['property']=str(body.get('property',''))[:64]
        summary['fact_reason']=str(body.get('reason',''))[:100]
        reviewed=body.get('reviewed_fact')
        if body.get('original_verified') and isinstance(reviewed,dict):
            summary['reviewed_fact_id']=str(reviewed.get('fact_id',''))[:120]
            # Only the reference to the fact, not a new assertion about compliance.
    elif kind == 'GapReport':
        summary['gap_codes']=[str(g.get('code',''))[:72] for g in body.get('gaps',[])[:32] if isinstance(g,dict)]
    elif kind == 'QualificationAssessment':
        summary['state']=str(body.get('state','UNKNOWN'))[:64]
        summary['obligations']=[str(x)[:100] for x in body.get('proof_obligations',[])[:32]]
    elif kind == 'ScenarioAssessment':
        summary['state']=str(body.get('state','UNKNOWN'))[:64]
        summary['hypothetical_only']=True
    elif kind == 'EngineeringQuestion':
        summary['state']='UNRESOLVED'
        summary['open_obligations']=[str(x.get('code'))[:80] for x in body.get('proof_obligations',[])
                                      if isinstance(x,dict) and x.get('state')=='OPEN'][:24]
    elif kind == 'ObligationReport':
        summary['state']='OPEN' if body.get('open') else 'SATISFIED_FOR_RECORDED_SCOPE'
        summary['open_obligations']=[str(x)[:80] for x in body.get('open',[])][:24]
    elif kind == 'KnowledgePacket':
        summary['packet_digest']=str(body.get('packet_sha256',''))[:64]
    return summary


def _subject(ir):
    for node in ir.get('nodes',[]):
        if node.get('op') == 'links.inspect':
            return {'kind':'component','ref':node['arguments']['component']}
        if node.get('op') == 'links.trace':
            return {'kind':'trace','start':node['arguments']['start'],'end':node['arguments']['end']}
    return {'kind':'context','ref':'ARC-1@R10'}


def _deps(result):
    refs=result.get('source_dependencies',[])
    if not isinstance(refs,list) or len(refs) > 256:
        raise ChronicleError('INVALID_SOURCE_DEPENDENCIES')
    out=[]
    for src in refs:
        if not isinstance(src,dict):raise ChronicleError('INVALID_SOURCE_DEPENDENCY')
        if src.get('kind') == 'native_file':
            path=src.get('path','');sha=src.get('sha256')
            if type(path) is not str or len(path)>300 or not _safe_relative(path):
                raise ChronicleError('INVALID_SOURCE_PATH')
            if sha is not None and (type(sha) is not str or not HASH_RE.fullmatch(sha)):
                raise ChronicleError('INVALID_SOURCE_DIGEST')
            out.append({'kind':'native_file','path':path,'sha256':sha})
        elif src.get('kind') == 'vendor_original':
            dig=src.get('sha256');doc=src.get('document_id')
            if not isinstance(dig,str) or not HASH_RE.fullmatch(dig):
                raise ChronicleError('INVALID_VENDOR_ORIGINAL_DIGEST')
            out.append({'kind':'vendor_original','document_id':str(doc)[:120], 'sha256':dig})
        else:
            raise ChronicleError('UNKNOWN_DEPENDENCY_KIND')
    return sorted(out,key=lambda x:(x['kind'],x.get('path',''),x.get('document_id','')))


def _safe_relative(path):
    if not path or any(x in path for x in ('\\', ':', '\x00', ';', '&', '|', '<', '>', '`', '$', '*', '?', '[', ']', '{', '}', '\n', '\r')):
        return False
    p=PurePosixPath(path)
    return (not p.is_absolute() and not any(x in ('.','..','') or x.startswith('.') for x in path.split('/'))
            and len(p.parts) <= 25)


def observe(root, ir, result):
    """Append one *successful, read-only* staC observation to a private chronicle.

    Does not authorize or execute anything. Caller has already executed the IR
    through Ledger Kernel Tutor/read scope. No LLM output accepted as evidence.
    """
    from .runtime import _validate_ir
    _validate_ir(ir)
    if (result.get('ok') is not True or result.get('engineering_authority') != 'LEDGER_KERNEL_READ_ONLY'
        or result.get('model_invoked') is not False or result.get('physical_qualification_granted') is not False
        or result.get('intent_digest') != record_io.digest(ir)):
        raise ChronicleError('INVALID_READ_OBSERVATION')
    deps=_deps(result)
    db, anchor=_connection(root, writable=True)
    try:
        db.execute('BEGIN IMMEDIATE')
        rows, parent, sealed = _verified_rows(db,anchor)
        n=len(rows)+1;now_ns=time.time_ns()
        event={'schema':SCHEMA,'profile':PROFILE,'sequence':n,'recorded_ns':now_ns,
               'recorded_utc':datetime.fromtimestamp(now_ns/1e9, timezone.utc).isoformat(timespec='microseconds'),
               'kind':'READ_OBSERVATION','status':'OBSERVED',
               'prev_hash':parent,'intent_digest':record_io.digest(ir),
               'resolved_program_digest':result.get('resolved_program_digest'),
               'context':ir['context'],'binding':result.get('binding'),
               'subject':_subject(ir),'ir':ir,
               'result_digest':record_io.digest(result),'result_summary':_meta(result),
               'source_dependencies':deps,
               'provenance_note':'read observation; no executed test or physical qualification'}
        encoded=record_io.canonical(event)
        if len(encoded)>65536:raise ChronicleError('CHRONICLE_EVENT_TOO_LARGE')
        event_hash=record_io.digest(event)
        db.execute('INSERT INTO events(seq,recorded_ns,event_json,prev_hash,event_hash) VALUES(?,?,?,?,?)',
                   (n,now_ns,encoded.decode('utf-8'),parent,event_hash))
        db.commit()
        return {'schema':RESULT_SCHEMA,'status':'RECORDED','sequence':n,
                'event_hash':event_hash,'intent_digest':event['intent_digest'],
                'resolved_program_digest':event['resolved_program_digest'],
                'recorded_utc':event['recorded_utc'],'result_summary':event['result_summary'],
                'binding':event['binding'],'source_dependencies':deps,
                'effects':['read'],'authority':'LEDGER_KERNEL_READ_ONLY'}
    except (sqlite3.Error, OSError) as exc:
        db.rollback();raise ChronicleError('CHRONICLE_WRITE_FAILED') from exc
    except Exception:
        db.rollback();raise
    finally:
        db.close()


def observe_reason(root, graph, result):
    """Record a coordinator-owned finite recomputation, never a model attestation.

    No kernel operation accepts event dictionaries. Callers load owner-checked
    records and compute the snapshot before entering this private adapter.
    """
    if (graph.get('kind')!='reason_graph' or result.get('kind')!='reason_result'
        or result.get('graph')!=graph.get('id') or result.get('context_digest')!=graph.get('context_digest')
        or result.get('model_calls')!=0 or result.get('snapshot',{}).get('physical_qualification') is not False):
        raise ChronicleError('INVALID_REASON_RECOMPUTATION')
    ir={'graph':graph['id'],'graph_revision':result['graph_revision'],'context_digest':result['context_digest'],
        'definition_digest':result['definition_digest'],'effects':['read']}
    db,anchor=_connection(root,writable=True)
    try:
        db.execute('BEGIN IMMEDIATE');rows,parent,sealed=_verified_rows(db,anchor)
        for event,event_hash in rows:
            if event.get('reason_result')==result['id']:
                if event['result_digest']!=record_io.digest(result):raise ChronicleError('REASON_RECORD_CHANGED')
                return {'status':'RECORDED','sequence':event['sequence'],'event_hash':event_hash,'replayed':True}
        now=time.time_ns();snapshot=result['snapshot']
        event={'schema':SCHEMA,'profile':PROFILE,'sequence':len(rows)+1,'recorded_ns':now,
            'recorded_utc':datetime.fromtimestamp(now/1e9,timezone.utc).isoformat(timespec='microseconds'),
            'kind':'REASON_RECOMPUTATION','status':'OBSERVED','prev_hash':parent,'ir':ir,'intent_digest':record_io.digest(ir),
            'resolved_program_digest':result['definition_digest'],'context':{'problem':result['problem'],'revision':result['problem_revision']},
            'binding':{'context_digest':result['context_digest'],'graph':graph['id']},'subject':{'kind':'problem','ref':result['problem']},
            'reason_result':result['id'],'result_digest':record_io.digest(result),
            'result_summary':{'result_type':'FiniteReasonGraph','state':snapshot['state'],'reason_digest':snapshot['reason_digest'],
                'change':result['change'],'rule_review':'PROPOSED_RULES_NOT_APPROVED_FACTS','coverage':snapshot['coverage'],
                'physical_qualification':'NOT_DEMONSTRATED'},'source_dependencies':[],
            'provenance_note':'Coordinator recomputation of proposed rules over owned receipts; assumptions and interpretation remain explicit. Complete reason paths stay in the referenced durable result.'}
        encoded=record_io.canonical(event)
        if len(encoded)>65536:raise ChronicleError('CHRONICLE_EVENT_TOO_LARGE')
        event_hash=record_io.digest(event)
        db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(event['sequence'],now,encoded.decode(),parent,event_hash));db.commit()
        return {'status':'RECORDED','sequence':event['sequence'],'event_hash':event_hash,'replayed':False}
    except Exception:
        db.rollback();raise
    finally:db.close()


def verify(root):
    db,anchor=_connection(root)
    try:
        rows,head,sealed=_verified_rows(db,anchor)
        return {'schema':RESULT_SCHEMA,'status':'PASS','event_count':len(rows),
                'head_hash':head,'digest_profile':PROFILE,'sealed_count':sealed['count'] if sealed else 0,
                'independent_anchoring':False,
                'notice':'Local hash chain and optional local checkpoint; not proof of author identity or source truth.'}
    finally:
        if db:db.close()


def seal(root):
    """Pin current head to a separate local file. Not a trusted external signature."""
    db,anchor=_connection(root)
    try:
        rows,head,sealed=_verified_rows(db,anchor)
        if db is None:
            raise ChronicleError('NO_CHRONICLE_TO_SEAL')
        count=len(rows)
    finally:
        if db:db.close()
    obj={'schema':'arc.stac.ccc.anchor/0.3','profile':PROFILE,'count':count,'head_hash':head}
    record_io.write_json(anchor,obj)
    return {'schema':RESULT_SCHEMA,'status':'LOCALLY_SEALED','count':count,'head_hash':head,
            'notice':'Copy the checkpoint to independently controlled read-only media for stronger tamper evidence.'}


def _ns(value):
    if not isinstance(value,str) or len(value)>50:
        raise ChronicleError('INVALID_TIME: use timezone-aware ISO 8601, e.g. 2026-10-26T00:00:00Z')
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None:raise ValueError('no timezone')
        return int(dt.timestamp()*1_000_000)*1000
    except (OverflowError,ValueError) as exc:
        raise ChronicleError('INVALID_TIME: timezone/offset required') from exc


def _read(root):
    db,anchor=_connection(root)
    try:
        rows,head,sealed=_verified_rows(db,anchor)
        return rows,head
    finally:
        if db:db.close()


def history(root,limit=20,since=None,until=None,component=None):
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:raise ChronicleError('INVALID_LIMIT')
    if component is not None and not COMPONENT_RE.fullmatch(component):raise ChronicleError('INVALID_COMPONENT')
    left=_ns(since) if since else None;right=_ns(until) if until else None
    if left is not None and right is not None and left>right:raise ChronicleError('INVALID_TIME_RANGE')
    rows,head=_read(root)
    subset=[(r,h) for r,h in rows if (left is None or r['recorded_ns']>=left) and
            (right is None or r['recorded_ns']<=right) and
            (component is None or r['subject'].get('ref')==component)]
    selected=subset[-limit:]
    return {'schema':RESULT_SCHEMA,'status':'PASS','coverage':'EXPLICIT_STAC_READ_OBSERVATIONS_ONLY',
            'total_matching':len(subset),'truncated':len(subset)>limit,
            'recorded_kinds':sorted(set(r['kind'] for r,h in subset)),
            'events':[{'sequence':r['sequence'],'kind':r['kind'],'recorded_utc':r['recorded_utc'],
                       'subject':r['subject'],'intent_digest':r['intent_digest'],
                       'resolved_program_digest':r['resolved_program_digest'],
                       'source_generation':(r.get('binding') or {}).get('source_generation'),
                       'result_summary':r['result_summary'],'event_hash':h} for r,h in reversed(selected)]}


def known_at(root,recorded_as_of,component):
    if not isinstance(component,str) or not COMPONENT_RE.fullmatch(component):raise ChronicleError('INVALID_COMPONENT')
    moment=_ns(recorded_as_of)
    rows,_=_read(root)
    candidates=[(r,h) for r,h in rows if r['recorded_ns']<=moment and r['subject']=={'kind':'component','ref':component}]
    if not candidates:
        return {'schema':RESULT_SCHEMA,'status':'UNKNOWN_NO_RECORDED_OBSERVATION',
                'component':component,'recorded_as_of':recorded_as_of,
                'notice':'No observation in the opt-in chronology; this does not prove no investigation occurred.'}
    r,h=candidates[-1]
    return {'schema':RESULT_SCHEMA,'status':'HISTORICAL_OBSERVATION','component':component,
            'recorded_as_of':recorded_as_of,'recorded_utc':r['recorded_utc'],'sequence':r['sequence'],
            'binding':r['binding'],'result_summary':r['result_summary'],
            'source_dependencies':r['source_dependencies'],
            'event_hash':h,'current_applicability':'NOT_ASSESSED',
            'temporal_semantics':'AS_RECORDED_AT; source valid-time interval not established',
            'physical_qualification':'NOT_DEMONSTRATED'}


def whatif_source_changed(root,path):
    """Only known recorded dependencies; never assume missing edges imply safety."""
    if not isinstance(path,str) or len(path)>300 or not _safe_relative(path):
        raise ChronicleError('INVALID_SOURCE_PATH')
    rows,_=_read(root)
    impacted=[];digests=set()
    for r,h in rows:
        matching=[d for d in r.get('source_dependencies',[]) if d.get('kind')=='native_file' and d.get('path')==path]
        if matching:
            digests.update(x.get('sha256') for x in matching if x.get('sha256'))
            impacted.append({'sequence':r['sequence'],'event_hash':h,
                             'intent_digest':r['intent_digest'],'observed_at':r['recorded_utc'],
                             'source_generation':(r.get('binding') or {}).get('source_generation'),
                             'consequence':'REQUALIFICATION_REVIEW_IF_DEPENDENCY_CHANGED'})
    try:
        target=record_io.project_path(root,path,must_exist=False)
        current_sha=record_io.sha(target) if target.is_file() and target.stat().st_size<=268435456 else None
    except (OSError,ValueError):
        current_sha=None
    already_drifted=bool(digests and (current_sha is None or current_sha not in digests))
    return {'schema':RESULT_SCHEMA,'status':'PREVIEW_ONLY','assumption':{'type':'HYPOTHETICAL_SOURCE_CHANGE','path':path},
            'recorded_source_hashes':sorted(digests),'observed_current_sha256':current_sha,
            'captured_dependency_count':len(impacted), 'affected_observations':impacted[-MAX_ROWS:],
            'affected_truncated':len(impacted)>MAX_ROWS,
            'baseline_state':'ALREADY_DRIFTED_OR_UNAVAILABLE' if already_drifted else 'NO_OBSERVED_DRIFT',
            'coverage':'TRACKED_OBSERVATIONS_ONLY' if impacted else 'NO_CAPTURED_DEPENDENCY; NOT PROOF OF NO IMPACT',
            'predicted_test_outcome':'UNKNOWN','execution_authority':'NONE','effects':['read','propose'],
            'notice':'No source changed; no job executed; preview is not a physical or simulation result.'}
