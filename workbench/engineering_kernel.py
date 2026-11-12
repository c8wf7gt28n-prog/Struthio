"""Ledger engineering authority, independent of Qt and model providers.

Local trust boundary: the OS account owns this project. API clients receive only
transport-issued Principals; no caller-supplied identity/scopes are accepted.
No shell strings, physical programming, or hardware-source writes exist here.
"""

from __future__ import annotations
from dataclasses import dataclass
from contextlib import contextmanager
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from .project_inventory import hashes, revision, paths, inventory
from . import agent_operations, hardware_proof, project_guidance, baseline_repair, hardware_coverage, console_simulation, boot_loading, firmware_tools
from . import engineering_register, vendor_adapter, orange_book, database_rom, brain_link, ux_services, register_proposals, console_services, clip_external, remote_sessions
from . import clip_workshop
from . import desktop_services
from . import job_priority,resource_control
from . import native_projects
from . import workspace_services
from . import ledger_control
from . import stacy_foundation
from . import stacy_awareness, project_context, activity
from . import local_brain, intake_service, reference_service, memory_service, stac_bridge, research_service, study_service, knowledge_service, evidence_compiler, investigation_service
from . import stacy_language
from . import capability_catalog, tool_atlas, algorithm_atlas, discovery_service
from . import object_context, slate_windows, work_trail, package_service, work_organizer, notes_exchange, notebook_service, office_service
from . import addresses, locations, instruction_matrix, receiving, universal_view, investigations, agenda, files_service, working_copies, host_support, pills, confine
from . import record_access
from . import project_desk
from . import problem_service
from . import math_service
from . import lab_service
from . import reason_service
from . import adaptive_work,schedule_math,slate_action
from . import joined_work,typed_artifacts,checked_methods,native_sessions
from . import slate_context, slate_reasoning
from . import edit_storage, import_profiles, change_sets
from . import edit_model
from . import continuing_work, worker_boundary
from . import exchange,release_updates,deployment
from . import kicad_tools, kibot_tools, spice_tools, yosys_tools, pnr_tools, hdl_tools, surfer_tools
from . import machine_overview  # DESKTOP-01: ledger.machine, a read over /proc, /sys and statvfs (recorded addition)
from . import documents  # WORKSHOP-01: documents.* over the existing Project Desk store (recorded additions)
from . import agent_loop, conditions, helpers, related, browse  # AGENT-01: the resident agent loop, condition cards, retained helpers, quiet connections, the Finder's listing (recorded additions)
from . import network_watch, network_capture  # HATCH DESK D5: network.observe and the headers-only capture, its job tool network.capture (recorded additions)
from . import program_mail, program_build, program_transfer, program_cartridge
from . import program_vector, program_media, program_freecad
from . import program_print, program_delivery

PROGRAM_HANDLERS = {
    op: service
    for service in (program_mail, program_build, program_transfer, program_cartridge,
                    program_vector, program_media, program_freecad, program_print, program_delivery)
    for op in service.FIELDS
}

VERSION = "arc-ledger.kernel/1"
STATES = (
    "Queued",
    "Running",
    "Waiting for Approval",
    "Paused",
    "Completed",
    "Failed",
    "Cancelled",
    "Interrupted",
    "Waiting for Agent",
    "Waiting for Execution Approval",
    "Waiting for Provider",
)
MAX_LOG = 2 * 1024 * 1024
TOOLS = {
    **{name:('workbench.local_brain',) for name in sorted(slate_action.JOB_TOOLS)},
    **{name:('workbench.lab_service',) for name in sorted(lab_service.JOB_TOOLS)},
    **{name:('workbench.math_service',) for name in sorted(math_service.JOB_TOOLS)},
    **{name:('workbench.office_service',) for name in sorted(office_service.JOB_TOOLS)},
    **{name:('workbench.investigation_service',) for name in sorted(investigation_service.JOB_TOOLS)},
    **{name:('workbench.evidence_compiler',) for name in sorted(evidence_compiler.JOB_TOOLS)},
    **{name:('workbench.knowledge_service',) for name in sorted(knowledge_service.JOB_TOOLS)},
    **{name:('workbench.study_service',) for name in sorted(study_service.JOB_TOOLS)},
    **{name:('workbench.reference_service',) for name in sorted(reference_service.JOB_TOOLS)},
    **{name:('workbench.intake_service',) for name in sorted(intake_service.JOB_TOOLS)},
    **{name:('workbench.local_brain',) for name in sorted(local_brain.JOB_TOOLS)},
    **{engine+'.'+op:('workbench.hdl_tools',engine+'-'+op) for engine in ('icarus','verilator') for op in ('qualify',*hdl_tools.PROFILES)},
    **{'surfer.'+op:('workbench.surfer_tools',op) for op in ('qualify',*surfer_tools.PROFILES)},
    **{'nextpnr.'+op:('workbench.pnr_tools','route-'+op) for op in ('qualify',*pnr_tools.PROFILES)},
    'trellis.qualify':('workbench.pnr_tools','pack-qualify'),
    **{'trellis.pack_'+op:('workbench.pnr_tools','pack-'+op) for op in pnr_tools.PROFILES},
    **{'yosys.'+op:('workbench.yosys_tools',op) for op in ('qualify',*yosys_tools.PROFILES)},
    **{'spice.'+op:('workbench.spice_tools',op) for op in ('qualify',*spice_tools.PROFILES)},
    **{'kibot.'+op:('workbench.kibot_tools',op) for op in ('qualify','bom','fabrication')},
    'cad.qualify':('workbench.kicad_tools','qualify'),
    'cad.drc':('workbench.kicad_tools','drc'),
    'native.build':('workbench.native_projects',),
    'links.export': ('workbench.cad_export',),
    'arcos.parser': ('workbench.host_parser',),
    'workshop.debug_build': ('workbench.desktop_services', 'debug-build'),
    "clip.workshop": ("workbench.clip_workshop", "run"),
    network_capture.JOB_TOOL: ("workbench.network_capture", "run"),  # HATCH DESK D5: run in the job worker by run_job (network_capture.run)
    "console.build": ("workbench.console_tools", "build"),
    "console.lifecycle": ("workbench.console_tools", "demo"),
    "register.validate_text": ("workbench.register_tools", "validate"),
    "register.analyze_power": ("workbench.integration_tools", "power"),
    "vendor.refresh": ("workbench.integration_tools", "vendor"),
    "book.refresh": ("workbench.integration_tools", "book"),
    "boot.campaign": ("workbench.boot_tools", "campaign"),
    "boot.first_stage": ("workbench.first_stage_tools", "campaign"),
    "simulation.campaign": ("workbench.simulation_tools", "campaign"),
    **{"firmware." + c: ("workbench.firmware_tools", "campaign", "--component", c)
       for c in firmware_tools.COMPONENTS},
    **{ "arcos." + a: ("workbench.arcos_tools", a)
        for a in ("build", "test", "replay", "package", "dependencies", "kernel_probe") },
    "proof.inspect": ("workbench.proof_tools", "inspect"),
    "proof.qualify": ("workbench.proof_tools", "qualify"),
    "proof.coverage": ("workbench.proof_tools", "coverage"),
    **{
        "qualification." + a: ("workbench.qualification_tools", a)
        for a in ("build", "test", "wait", "rtl")
    },
    "clip.loop": ("workbench.clip_jobs", "run"),
    "struthio.build": ("workbench.native_struthio", "build"),
    "struthio.test": ("workbench.native_struthio", "test"),
    "struthio.replay": ("workbench.native_struthio", "replay"),
    "struthio.package": ("workbench.native_struthio", "package"),
    "struthio.differential": ("workbench.native_struthio", "differential"),
    "struthio.reference_parity": ("workbench.ledger_tools", "parity"),
    "diagnostic.compare": ("workbench.development_cli", "compare"),
    "hardware.inspect": ("workbench.ledger_tools", "inspect"),
    "ledger.kernel_tests": ("unittest", "tests.test_ledger13_kernel"),
    "ledger.desktop_tests": ("unittest", "tests.test_r10_workbench"),
    "firmware.f133": ("arc1", "compact", "check", "--target", "f133"),
    "firmware.d213": ("arc1", "compact", "check", "--target", "d213"),
    "rtl.fpga45": ("arc1", "compact", "check", "--target", "fpga45"),
    "rtl.fpga12": ("arc1", "compact", "check", "--target", "fpga12"),
    "sdk.test": ("arc1", "test", "examples/hello_arc1"),
    "sdk.simulate": (
        "arc1",
        "sim",
        "examples/hello_arc1",
        "--frames",
        "120",
        "--dump-every",
        "1",
    ),
}
CAPABILITIES = {
    **{op: service.SCOPES[op] for op, service in PROGRAM_HANDLERS.items()},
    **job_priority.SCOPES,
    **exchange.SCOPES, **release_updates.SCOPES, **deployment.SCOPES,
    **continuing_work.SCOPES,
    **worker_boundary.SCOPES,
    **edit_model.SCOPES,
    **import_profiles.SCOPES,
    **change_sets.SCOPES,
    **slate_context.SCOPES,
    **slate_reasoning.SCOPES,
    **project_desk.SCOPES,
    **problem_service.SCOPES,
    **math_service.SCOPES,
    **lab_service.SCOPES,
    **reason_service.SCOPES,
    **adaptive_work.SCOPES,
    **schedule_math.SCOPES,
    **joined_work.SCOPES, **typed_artifacts.SCOPES, **checked_methods.SCOPES, **native_sessions.SCOPES,
    **office_service.SCOPES,
    **notebook_service.SCOPES,
    **notes_exchange.SCOPES,
    **package_service.SCOPES,
    **work_organizer.SCOPES,
    **work_trail.SCOPES,
    **slate_windows.SCOPES,
    **object_context.SCOPES,
    **addresses.SCOPES,
    **instruction_matrix.SCOPES,
    **receiving.SCOPES,
    **investigations.SCOPES,
    **agenda.SCOPES,
    **files_service.SCOPES,
    **working_copies.SCOPES,
    **host_support.SCOPES,
    **pills.SCOPES,
    **confine.SCOPES,
    **universal_view.SCOPES,
    **capability_catalog.SCOPES,
    **tool_atlas.SCOPES,
    **algorithm_atlas.SCOPES,
    **discovery_service.SCOPES,
    **memory_service.SCOPES,
    **research_service.SCOPES,
    **investigation_service.SCOPES,
    **evidence_compiler.SCOPES,
    **knowledge_service.SCOPES,
    **study_service.SCOPES,
    **stac_bridge.SCOPES,
    **reference_service.SCOPES,
    **intake_service.SCOPES,
    **stacy_language.SCOPES,
    **local_brain.SCOPES,
    **stacy_awareness.SCOPES,
    **stacy_foundation.SCOPES,
    **kicad_tools.SCOPES,
    **kibot_tools.SCOPES,
    **spice_tools.SCOPES,
    **yosys_tools.SCOPES,
    **pnr_tools.SCOPES,
    **hdl_tools.SCOPES,
    **surfer_tools.SCOPES,
    **ledger_control.SCOPES,
    **machine_overview.SCOPES,
    **documents.SCOPES,
    **agent_loop.SCOPES, **conditions.SCOPES, **helpers.SCOPES, **related.SCOPES, **browse.SCOPES,
    **network_watch.SCOPES,
    **native_projects.SCOPES,
    **{name:'read' for name in workspace_services.FIELDS},
    **desktop_services.SCOPES,
    **clip_workshop.SCOPES,
    **clip_external.SCOPES,
    **remote_sessions.SCOPES,
    **console_services.SCOPES,
    **register_proposals.SCOPES,
    **{name: "read" for name in brain_link.FIELDS},
    **{name: "read" for name in ux_services.FIELDS},
    **database_rom.SCOPES,
    **{name: "read" for name in engineering_register.FIELDS},
    **{name: "read" for name in vendor_adapter.FIELDS},
    **{name: "read" for name in orange_book.FIELDS},
    **{name: "read" for name in boot_loading.FIELDS},
    **{name: "read" for name in firmware_tools.FIELDS},
    **{name: "read" for name in console_simulation.FIELDS},
    **{name: "read" for name in hardware_coverage.FIELDS},
    **{name: "read" for name in project_guidance.FIELDS},
    **baseline_repair.SCOPES,
    **{name: "read" for name in hardware_proof.FIELDS},
    **{name: "read" for name in agent_operations.FIELDS},
    "jobs.recover": "approve",
    "capabilities": "read",
    "project.inspect": "read",
    "project.inventory": "read",
    "files.read": "read",
    "files.search": "read",
    "jobs.list": "read",
    "jobs.get": "read",
    "evidence.list": "read",
    "evidence.read": "read",
    "candidates.list": "read",
    "candidates.diff": "read",
    "candidates.create": "candidate",
    "candidates.patch": "candidate",
    "jobs.submit": "execute",
    "jobs.cancel": "execute",
    "jobs.pause": "execute",
    "jobs.resume": "execute",
    "candidates.review": "candidate",
    "candidates.reject": "candidate",
    "candidates.accept": "approve",
    "candidates.rollback": "approve",
    "remote.disable": "approve",
    "candidates.authorize_execution": "approve",
    "clip.submit": "candidate",
    "clip.authorize": "approve",
    "candidates.stage": "approve",
}


class KernelError(ValueError):
    pass


@dataclass(frozen=True)
class Principal:
    identity: str
    scopes: frozenset = frozenset({"read"})
    paths: tuple = (
        "software/arcos/src/",
        "software/arcos/games/",
        "software/struthio/",
        "development/diag_ticket_isolation/src/",
        "development/agent_qualification/src/",
    )
    tools: tuple = tuple(TOOLS)
    mode: str = "Engineer"


def operator(identity="desktop-owner"):
    return Principal(
        identity,
        frozenset({"read", "candidate", "execute", "approve"}),
        (
            "software/arcos/src/",
            "software/arcos/games/",
            "software/struthio/",
            "development/diag_ticket_isolation/src/",
            "development/agent_qualification/src/",
            "workbench/",
            "docs/ledger2/REQUIREMENTS.json",
            "docs/ledger2/OPEN_ISSUES.json",
            "project/register/bindings.json",
        ),
    )


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return time.time()


def process_token(pid):
    from .operation_stop import process_identity,UNKNOWN
    value=process_identity(pid)
    return None if value==UNKNOWN else value


def identifier(value):
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise KernelError("Invalid identifier")
    return value


class Kernel:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.state = self.root / ".ledger"
        self.state.mkdir(mode=0o700, exist_ok=True)
        self.dbpath = self.state / "engineering.sqlite3"
        self._workers = {}
        with self.db() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, owner TEXT, state TEXT, payload TEXT);
              CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, owner TEXT, state TEXT, payload TEXT);
              CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, payload TEXT);
              CREATE TABLE IF NOT EXISTS requests(owner TEXT, key TEXT, job TEXT, PRIMARY KEY(owner,key));
              CREATE TABLE IF NOT EXISTS audit(at REAL, actor TEXT, operation TEXT, outcome TEXT);
              CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, payload TEXT);
              CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
              CREATE TABLE IF NOT EXISTS ledger_activity(id TEXT PRIMARY KEY, payload TEXT);
            """)
            activity.initialize(self.root,db)
            intake_service.ensure(db)
            reference_service.ensure(db)
            evidence_compiler.ensure(db)
            memory_service.ensure(db)
            research_service.ensure(db)
            study_service.ensure(db)
            knowledge_service.ensure(db)
            slate_windows.ensure(db)
            work_trail.ensure(db)
            package_service.ensure(db)
            project_desk.ensure(db)
            slate_context.ensure(db)
            edit_storage.ensure(db)
            continuing_work.ensure(db)
            worker_boundary.ensure(db)
            exchange.ensure(db)
            release_updates.ensure(db)
        if os.name != "nt":
            self.dbpath.chmod(0o600)

    @contextmanager
    def db(self):
        # sqlite3 context managers commit but do not close the connection.
        from .database_guard import connection
        with connection(self.dbpath):
            db = sqlite3.connect(self.dbpath, timeout=10)
            try:
                db.execute("PRAGMA journal_mode=WAL")
                with db:
                    yield db
            finally:
                db.close()

    def audit(self, who, op, outcome, correlation_id=None):
        if op in activity.OBSERVER_OPERATIONS and outcome=='OK':return
        event=activity.make_event(who,op,'REQUEST_COMPLETED' if outcome=='OK' else outcome,correlation_id=correlation_id)
        try:
            with self.db() as db:
                db.execute("INSERT INTO audit VALUES(?,?,?,?)", (now(), who, op, outcome))
                activity.append(db,event)
        except (OSError,sqlite3.Error,ValueError) as exc:
            # A completed external operation must not be reported as undone just
            # because its audit delivery failed. Preserve and expose the gap.
            activity._failed(self.root,event,exc)

    def safe(self, name, base=None, must_exist=True):
        if (
            not isinstance(name, str)
            or not name
            or "\\" in name
            or ":" in name
            or "\x00" in name
        ):
            raise KernelError("Expected normalized relative path")
        parts = name.split("/")
        if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
            raise KernelError("Path is outside approved source")
        base = Path(base or self.root).resolve()
        p = base.joinpath(*parts)
        if not p.resolve().is_relative_to(base) or any(
            x.is_symlink() for x in [p, *p.parents]
        ):
            raise KernelError("Symlinks and escaping paths are not allowed")
        if must_exist and not p.is_file():
            raise KernelError("Source file not found")
        return p

    def record(self, table, id):
        identifier(id)
        with self.db() as db:
            row = db.execute(
                "SELECT payload FROM " + table + " WHERE id=?", (id,)
            ).fetchone()
        if not row:
            raise KernelError("Record not found")
        return json.loads(row[0])

    def save(self, table, obj, db=None):
        def write(conn):
            previous=None
            if table=='jobs':
                if not conn.in_transaction:conn.execute('BEGIN IMMEDIATE')
                row=conn.execute('SELECT state FROM jobs WHERE id=?',(obj['id'],)).fetchone()
                previous=row[0] if row else None
                if previous is None or (obj.get('state')=='Queued' and previous!='Queued'):
                    work_trail.accepting(self,conn)
            if table == "evidence":
                conn.execute(
                    "INSERT OR REPLACE INTO evidence VALUES(?,?)",
                    (obj["id"], json.dumps(obj)),
                )
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO " + table + " VALUES(?,?,?,?)",
                    (obj["id"], obj["owner"], obj["state"], json.dumps(obj)),
                )
                if table=='jobs':work_trail.bind(conn,self,obj['owner'],obj['id'])
            if (table=='jobs' and previous!=obj.get('state')) or table in ('candidates','evidence'):
                event=activity.make_event(obj.get('owner','KERNEL'),obj.get('tool',table),obj.get('state','RECORDED'),
                    job_id=obj.get('job',obj['id'] if table=='jobs' else None),
                    candidate_id=obj['id'] if table=='candidates' else obj.get('candidate'),
                    evidence_id=obj['id'] if table=='evidence' else obj.get('evidence'),
                    source_generation=obj.get('revision'),correlation_id=obj.get('request_key'))
                activity.append(conn,event)

        if db is not None:
            write(db)
        else:
            with self.db() as conn:
                write(conn)

    def listing(self, table):
        with self.db() as db:
            return [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT payload FROM " + table + " ORDER BY rowid DESC LIMIT 100"
                )
            ]

    def require_owner(self, record, p):
        if record["owner"] != p.identity and "approve" not in p.scopes:
            raise KernelError("Another operator owns this record")

    def candidate_root(self, id):
        return self.state / "candidates" / identifier(id) / "source"

    def dispatch(self, operation, params=None, principal=None):
        p = principal or Principal("anonymous")
        params = {} if params is None else params
        correlation_id=uuid.uuid4().hex
        trail_token=work_trail.enter(self, operation if isinstance(operation,str) and operation in CAPABILITIES else "unknown", p, correlation_id, CAPABILITIES.get(operation) if isinstance(operation,str) else None)
        scope_checked=False
        try:
            if not isinstance(params, dict):
                raise KernelError("Parameters must be an object")
            if not isinstance(operation, str) or operation not in CAPABILITIES:
                raise KernelError("Unknown operation")
            from .engineering_cli import schemas

            schema = schemas()[operation]
            if set(params) - set(schema["properties"]) or set(schema["required"]) - set(
                params
            ):
                raise KernelError("Unknown or missing parameters for " + operation)
            agent_operations.validate(params, schema)
            if CAPABILITIES[operation] not in p.scopes or (
                p.mode == "Tutor" and CAPABILITIES[operation] != "read"
            ):
                raise KernelError("Operation is outside the authorized mode/scope")
            scope_checked=True
            if trail_token is not None:work_trail.update(self,p,"DISPATCHING",True)
            if operation not in activity.OBSERVER_OPERATIONS:
                activity.record(self.root,p.identity,operation,'REQUEST_RECEIVED',correlation_id=correlation_id)
            outer=instruction_matrix.begin(operation)
            try:
                result = (project_context.unavailable(operation)
                          if project_context.detached(self.root) and project_context.requires_project(operation,params)
                          else self._dispatch(operation, params, p))
            except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
                if outer is not None:instruction_matrix.observe(self,p,operation,params,error=exc)
                raise
            finally:instruction_matrix.end(outer)
            if outer is not None:instruction_matrix.observe(self,p,operation,params,result=result)
            if operation in ("candidates.accept", "candidates.rollback"):
                orange_book.request_refresh(self.root)
            self.audit(p.identity, operation, "OK",correlation_id)
            if trail_token is not None:work_trail.update(self,p,"BLOCKED" if isinstance(result,dict) and result.get("status")=="PROJECT_NOT_ATTACHED" else "RETURNED",True)
            return {"schema": VERSION, "ok": True, "result": result,
                    "journal_state":activity.status(self.root)['state'],"correlation_id":correlation_id}
        except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
            if trail_token is not None:work_trail.update(self,p,"FAILED" if scope_checked else "DENIED",scope_checked)
            self.audit(
                p.identity,
                operation
                if isinstance(operation, str) and operation in CAPABILITIES
                else "unknown",
                "DENIED_OR_FAILED",
                correlation_id,  # so the request's received line is closed
            )
            return {
                "schema": VERSION,
                "ok": False,
                "error": {"code": type(exc).__name__, "message": str(exc)},
            }

        finally:
            work_trail.leave(trail_token)

    def _dispatch(self, op, a, p):
        if op in PROGRAM_HANDLERS:return PROGRAM_HANDLERS[op].dispatch(self,op,a,p)
        if op in exchange.FIELDS:return exchange.dispatch(self,op,a,p)
        if op in release_updates.FIELDS:return release_updates.dispatch(self,op,a,p)
        if op in deployment.FIELDS:return deployment.dispatch(self,op,a,p)
        if op in continuing_work.FIELDS:return continuing_work.dispatch(self,op,a,p)
        if op in worker_boundary.FIELDS:return worker_boundary.dispatch(self,op,a,p)
        if op in edit_model.FIELDS:return edit_model.dispatch(self,op,a,p)
        if op in import_profiles.FIELDS:return import_profiles.dispatch(self,op,a,p)
        if op in change_sets.FIELDS:return change_sets.dispatch(self,op,a,p)
        if op in slate_context.FIELDS:return slate_context.dispatch(self,op,a,p)
        if op in slate_reasoning.FIELDS:return slate_reasoning.dispatch(self,op,a,p)
        if op in project_desk.FIELDS:return project_desk.dispatch(self,op,a,p)
        if op in problem_service.FIELDS:return problem_service.dispatch(self,op,a,p)
        if op in adaptive_work.FIELDS:return adaptive_work.dispatch(self,op,a,p)
        if op in joined_work.FIELDS:return joined_work.dispatch(self,op,a,p)
        if op in typed_artifacts.FIELDS:return typed_artifacts.dispatch(self,op,a,p)
        if op in checked_methods.FIELDS:return checked_methods.dispatch(self,op,a,p)
        if op in native_sessions.FIELDS:return native_sessions.dispatch(self,op,a,p)
        if op in schedule_math.FIELDS:return schedule_math.dispatch(self,op,a,p)
        if op in lab_service.FIELDS:return lab_service.dispatch(self,op,a,p)
        if op in reason_service.FIELDS:return reason_service.dispatch(self,op,a,p)
        if op in math_service.FIELDS:return math_service.dispatch(self,op,a,p)
        if op in package_service.FIELDS:return package_service.dispatch(self,op,a,p)
        if op in work_organizer.FIELDS:return work_organizer.dispatch(self,op,a,p)
        if op in work_trail.FIELDS:return work_trail.dispatch(self,op,a,p)
        if op in job_priority.FIELDS:return job_priority.dispatch(self,op,a,p)
        if op.startswith('office.'):return office_service.dispatch(self,op,a,p)
        if op in notebook_service.FIELDS:return notebook_service.dispatch(self,op,a,p)
        if op in notes_exchange.FIELDS:return notes_exchange.dispatch(self,op,a,p)
        if op in slate_windows.FIELDS:return slate_windows.dispatch(self,op,a,p)
        if op in object_context.FIELDS:return object_context.dispatch(self,op,a,p)
        if op in addresses.FIELDS:return addresses.dispatch(self,op,a,p)
        if op in instruction_matrix.FIELDS:return instruction_matrix.dispatch(self,op,a,p)
        if op in receiving.FIELDS:return receiving.dispatch(self,op,a,p)
        if op in investigations.FIELDS:return investigations.dispatch(self,op,a,p)
        if op in agenda.FIELDS:return agenda.dispatch(self,op,a,p)
        if op in files_service.FIELDS:return files_service.dispatch(self,op,a,p)
        if op in working_copies.FIELDS:return working_copies.dispatch(self,op,a,p)
        if op in host_support.FIELDS:return host_support.dispatch(self,op,a,p)
        if op in pills.FIELDS:return pills.dispatch(self,op,a,p)
        if op in confine.FIELDS:return confine.dispatch(self,op,a,p)
        if op in universal_view.FIELDS:return universal_view.dispatch(self,op,a,p)
        if op in discovery_service.FIELDS:return discovery_service.dispatch(self,op,a,p)
        if op in algorithm_atlas.FIELDS:return algorithm_atlas.dispatch(self,op,a,p)
        if op in tool_atlas.FIELDS:return tool_atlas.dispatch(self,op,a,p)
        if op in capability_catalog.FIELDS:return capability_catalog.dispatch(self,op,a,p)
        if op in investigation_service.FIELDS:return investigation_service.dispatch(self,op,a,p)
        if op in evidence_compiler.FIELDS or (op in ('references.packet','references.answer.validate') and evidence_compiler.handles(self,a.get('id',a.get('packet')))):
            return evidence_compiler.dispatch(self,op,a,p)
        if op in knowledge_service.FIELDS:return knowledge_service.dispatch(self,op,a,p)
        if op in study_service.FIELDS:return study_service.dispatch(self,op,a,p)
        if op in research_service.FIELDS:return research_service.dispatch(self,op,a,p)
        if op in memory_service.FIELDS:return memory_service.dispatch(self,op,a,p)
        if op in stac_bridge.FIELDS:return stac_bridge.dispatch(self,op,a,p)
        if op in reference_service.FIELDS:return reference_service.dispatch(self,op,a,p)
        if op in intake_service.FIELDS:return intake_service.dispatch(self,op,a,p)
        if op in stacy_language.FIELDS:return stacy_language.dispatch(self,op,a,p)
        if op in local_brain.FIELDS:return local_brain.dispatch(self,op,a,p)
        if op in stacy_awareness.FIELDS:return stacy_awareness.dispatch(self,op,a,p)
        if op in stacy_foundation.FIELDS:return stacy_foundation.dispatch(self,op,a,p)
        if op in kicad_tools.FIELDS:return kicad_tools.dispatch(self,op,a)
        if op in kibot_tools.FIELDS:return kibot_tools.dispatch(self,op,a)
        if op in spice_tools.FIELDS:return spice_tools.dispatch(self,op,a)
        if op in yosys_tools.FIELDS:return yosys_tools.dispatch(self,op,a)
        if op in pnr_tools.FIELDS:return pnr_tools.dispatch(self,op,a)
        if op in hdl_tools.FIELDS:return hdl_tools.dispatch(self,op,a)
        if op in surfer_tools.FIELDS:return surfer_tools.dispatch(self,op,a)
        if op in ledger_control.FIELDS:return ledger_control.dispatch(self,op,a,p)
        if op in machine_overview.FIELDS:return machine_overview.dispatch(self,op,a,p)
        if op in documents.FIELDS:return documents.dispatch(self,op,a,p)
        if op in agent_loop.FIELDS:return agent_loop.dispatch(self,op,a,p)
        if op in conditions.FIELDS:return conditions.dispatch(self,op,a,p)
        if op in helpers.FIELDS:return helpers.dispatch(self,op,a,p)
        if op in related.FIELDS:return related.dispatch(self,op,a,p)
        if op in browse.FIELDS:return browse.dispatch(self,op,a,p)
        if op in network_watch.FIELDS:return network_watch.dispatch(self,op,a,p)
        if op in native_projects.FIELDS:return native_projects.dispatch(self,op,a,p)
        if op in workspace_services.FIELDS:
            return workspace_services.dispatch(self,op,a,p)
        if op in desktop_services.FIELDS:
            return desktop_services.dispatch(self, op, a, p)
        if op in clip_workshop.FIELDS:
            return clip_workshop.dispatch(self, op, a, p)
        if op in clip_external.FIELDS:
            return clip_external.dispatch(self, op, a, p)
        if op in remote_sessions.FIELDS:
            return remote_sessions.dispatch(self, op, a, p)
        if op in console_services.FIELDS:
            return console_services.dispatch(self, op, a, p)
        if op in register_proposals.FIELDS:
            return register_proposals.dispatch(self, op, a, p)
        if op in brain_link.FIELDS:
            return brain_link.dispatch(self, op, a)
        if op in ux_services.FIELDS:
            return ux_services.dispatch(self, op, a)
        if op in engineering_register.FIELDS:
            return engineering_register.dispatch(self, op, a, p)
        if op in database_rom.FIELDS:
            return database_rom.dispatch(self, op, a)
        if op in vendor_adapter.FIELDS:
            return vendor_adapter.dispatch(self, op, a)
        if op in orange_book.FIELDS:
            return orange_book.dispatch(self, op, a)
        if op in boot_loading.FIELDS:
            return boot_loading.dispatch(self, op, a)
        if op in firmware_tools.FIELDS:
            return firmware_tools.dispatch(self, op, a)
        if op in console_simulation.FIELDS:
            return console_simulation.dispatch(self, op, a)
        if op in hardware_coverage.FIELDS:
            return hardware_coverage.dispatch(self, op, a)
        if op in project_guidance.FIELDS:
            return project_guidance.dispatch(self, op, a, p)
        if op in baseline_repair.FIELDS:
            return baseline_repair.dispatch(self, op, a, p)
        if op in hardware_proof.FIELDS:
            return hardware_proof.dispatch(self, op, a)
        if op in agent_operations.FIELDS:
            return agent_operations.dispatch(self, op, a)
        if op == "jobs.recover":
            return self.recover_interrupted()
        if op == "capabilities":
            return {
                "version": VERSION,
                "contract": agent_operations.CONTRACT,
                "schemas": __import__(
                    "workbench.engineering_cli", fromlist=["schemas"]
                ).schemas(),
                "operations": {k: v for k, v in CAPABILITIES.items() if v in p.scopes},
                "tools": list(p.tools),
                "states": STATES,
                "mode": p.mode,
                "identity": p.identity,
                "paths": p.paths,
                "hardware_programming": False,
                "autonomous_provider_loop": True,
                "providers": [
                    "gemini",
                    "deterministic-test-adapter",
                    "external MCP/JSONL client",
                ],
                "acceptance_requires_operator": True,
            }
        if op == "project.inspect":
            return {
                "name": "Arc Ledger 2.0 B — Debian engineering workshop",
                "revision": revision(hashes(self.root)),
                "fabrication": "HOLD",
                "host": "online",
                "native_game": "Portable C gameplay with JS parity scenarios; diagnostic graphics; audio backend pending",
                "workspace_map": "project/workspaces.json",
                "records_catalog": "project/records/volume.json",
                "historical_retrieval": "records.search / records.hardware; sealed references are not current design authority",
            }
        if op == "project.inventory":
            return inventory(self.root)
        if op == "files.read":
            path = record_access.file_read(self,a['path'],p)
            data = path.read_bytes()
            if len(data) > 1024 * 1024:
                raise KernelError("Text read limit is 1 MiB")
            return {
                "path": a["path"],
                "sha256": digest(data),
                "content": data.decode("utf-8"),
            }
        if op == "files.search":
            query = a["query"]
            if not isinstance(query, str) or not 1 <= len(query) <= 200:
                raise KernelError("Query must contain 1–200 characters")
            result = []
            prefix = a.get("prefix", "")
            if prefix:
                self.safe(prefix.rstrip("/"), must_exist=False)
            for path in paths(self.root):
                if prefix and not path.relative_to(self.root).as_posix().startswith(
                    prefix
                ):
                    continue
                if path.stat().st_size > 8000000:
                    continue
                try:
                    for i, line in enumerate(
                        path.read_text(encoding="utf-8").splitlines(), 1
                    ):
                        if query.casefold() in line.casefold():
                            result.append(
                                {
                                    "path": path.relative_to(self.root).as_posix(),
                                    "line": i,
                                    "text": line[:300],
                                    "sha256": digest(path.read_bytes()),
                                }
                            )
                        if len(result) >= 100:
                            return result
                except UnicodeError:
                    pass
            return result
        if op in ("jobs.list", "candidates.list", "evidence.list"):
            return [
                {
                    k: v
                    for k, v in row.items()
                    if k not in ("base", "task", "input_hashes", "stdout", "stderr")
                }
                for row in record_access.listing(self,op.split(".")[0],p)
            ]
        if op in ("jobs.get", "evidence.read"):
            return record_access.read(self,op.split(".")[0],a['id'],p)
        if op == "candidates.create":
            return self.create_candidate(a, p)
        if op == "clip.submit":
            from .clip_jobs import submit

            return submit(self, a, p)
        if op == "clip.authorize":
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                j = self.record("jobs", a["id"])
                if (
                    j["tool"] != "clip.loop"
                    or j["state"] != "Waiting for Approval"
                    or j.get("authorized_by")
                ):
                    raise KernelError("Task is not awaiting scope approval")
                if revision(hashes(self.root)) != j["revision"]:
                    raise KernelError("Source changed; submit a new bounded task")
                j.update(state="Queued", authorized_by=p.identity, authorized_at=now())
                self.save("jobs", j, db)
            self.launch(j["id"])
            return j
        if op == "candidates.patch":
            return self.patch(a, p)
        if op == "candidates.diff":
            return self.diff(a["id"])
        if op == "candidates.stage":
            from .update_service import stage

            return stage(self, a["id"], p)
        if op == "candidates.authorize_execution":
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                c = self.record("candidates", a["id"])
                if c["state"] != "Draft":
                    raise KernelError(
                        "Review an editable draft before authorizing native code execution"
                    )
                c["execution_approval"] = {
                    "by": p.identity,
                    "revision": revision(hashes(self.candidate_root(c["id"]))),
                    "at": now(),
                }
                self.save("candidates", c, db)
            return c["execution_approval"]
        if op in (
            "candidates.review",
            "candidates.reject",
            "candidates.accept",
            "candidates.rollback",
        ):
            return self.transition(op, a, p)
        if op == "jobs.submit":
            return self.submit(a, p)
        if op in ("jobs.cancel", "jobs.pause", "jobs.resume"):
            selected = record_access.read(self,'jobs',a['id'],p)
            if selected['tool'] in (lab_service.JOB_TOOLS|math_service.JOB_TOOLS|office_service.JOB_TOOLS|local_brain.JOB_TOOLS|intake_service.JOB_TOOLS|reference_service.JOB_TOOLS|study_service.JOB_TOOLS|knowledge_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS|investigation_service.JOB_TOOLS) and op in ('jobs.pause','jobs.resume'):
                raise KernelError('Brain and intake jobs support cancel and a fresh reviewed request; pause/resume is not implemented')
            if selected['tool'] in network_capture.JOB_TOOLS and op in ('jobs.pause','jobs.resume'):
                raise KernelError('A capture is stopped, never paused or resumed: the owner starts a new one')
            if selected['tool'] == 'clip.workshop':
                return clip_workshop.control(self, op.split('.')[-1], a['id'], p)
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                job = json.loads(
                    db.execute(
                        "SELECT payload FROM jobs WHERE id=?", (identifier(a["id"]),)
                    ).fetchone()[0]
                )
                self.require_owner(job, p)
                if job.get("external_driver") and op in ("jobs.pause", "jobs.resume"):
                    raise KernelError("External tasks have no running inference process; read their handoff or control the actual child test job")
                if op == "jobs.resume":
                    if job["state"] not in ("Interrupted", "Paused"):
                        raise KernelError("Only interrupted/paused tasks can resume")
                    if job.get("candidate") and job["tool"] != "clip.loop":
                        c = self.record("candidates", job["candidate"])
                        self.require_owner(c, p)
                        if c["state"] != "Draft":
                            raise KernelError("Candidate no longer editable")
                        if not all(
                            any(
                                n.startswith(s) if s.endswith("/") else n == s
                                for s in p.paths
                            )
                            for n in c["paths"]
                        ):
                            raise KernelError("Candidate delegation changed")
                        if (
                            job["tool"] != "struthio.build"
                            and c.get("execution_approval", {}).get("revision")
                            != job["revision"]
                        ):
                            raise KernelError("Execution authorization changed")
                    if job["tool"] not in p.tools:
                        raise KernelError("Tool authorization changed")
                    source = (
                        self.candidate_root(job["candidate"])
                        if job["candidate"] and job["tool"] != "clip.loop"
                        else self.root
                    )
                    if revision(hashes(source)) != job["revision"]:
                        raise KernelError("Source changed; submit a new task")
                    job.update(
                        state="Queued",
                        cancel=False,
                        pause=False,
                        pid=None,
                        created=now(),
                    )
                elif job["state"] in ("Queued", "Running", "Waiting for Approval", "Waiting for Agent", "Waiting for Execution Approval", "Waiting for Provider", "Paused", "Interrupted"):
                    job["cancel"] = True
                    job["pause"] = op == "jobs.pause"
                    if job["state"] != "Running":
                        job["state"] = "Paused" if job["pause"] else "Cancelled"
                self.save("jobs", job, db)
            if op == "jobs.resume":
                self.launch(job["id"])
            elif job['tool'] in local_brain.JOB_TOOLS and job.get('cancel'):
                local_brain.cancel_job(self,job)
            return job
        if op == "remote.disable":
            with self.db() as db:
                db.execute("DELETE FROM sessions")
                db.execute(
                    "INSERT OR REPLACE INTO settings VALUES('remote_enabled','false')"
                )
            return {"remote_enabled": False, "sessions_revoked": True}
        raise KernelError("Operation not implemented")

    def create_candidate(self, a, p, register_text=None, db=None):
        scope = a.get("paths", list(p.paths))
        if not isinstance(scope, list) or not scope or len(scope) > 50:
            raise KernelError("Explicit file/prefix scope required")
        for name in scope:
            if name in register_proposals.PATHS and register_text is None:
                raise KernelError('Owned register files require the typed workbook proposal route')
            self.safe(name.rstrip("/"), must_exist=False)
            if not any(name.startswith(prefix) for prefix in p.paths):
                raise KernelError("Requested scope exceeds delegation")
            if name.startswith(("hardware/", "examples/struthio_arcade/", "passes/")):
                raise KernelError("Immutable engineering reference")
        required = a.get("required_tools", ["struthio.test"])
        if not required or any(t not in p.tools or t not in TOOLS for t in required):
            raise KernelError("Required regression tools unavailable")
        for prefix, tool in (
            ("software/arcos/", "arcos.test"),
            ("software/struthio/", "struthio.test"),
            ("development/agent_qualification/", "qualification.test"),
        ):
            if any(n.startswith(prefix) for n in scope) and tool not in required:
                raise KernelError("Required regression tool: " + tool)
        id = uuid.uuid4().hex
        base = hashes(self.root)
        dest = self.candidate_root(id)
        dest.mkdir(parents=True)
        for name in base:
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root / name, target)
        if hashes(dest) != base:
            raise KernelError("Source changed during snapshot; retry")
        c = {
            "id": id,
            "owner": p.identity,
            "state": "Draft",
            "goal": str(a.get("goal", "Candidate"))[:2000],
            "paths": scope,
            "base": base,
            "revision": revision(base),
            "created": now(),
            "changes": {},
            "required_tools": a.get("required_tools", ["struthio.test"]),
            "approval_required": True,
        }
        if register_text is not None:
            if set(scope)!=set(register_text['source_hashes']) or required!=['register.validate_text']:
                raise KernelError('Register proposal scope or required tool mismatch')
            c['register_proposal']=register_text
        if not c["required_tools"] or any(
            t not in p.tools or t not in TOOLS for t in c["required_tools"]
        ):
            raise KernelError("Required regression tools unavailable")
        if any(name.startswith("workbench/") for name in scope) and not {
            "ledger.kernel_tests",
            "ledger.desktop_tests",
        } <= set(c["required_tools"]):
            raise KernelError(
                "Graphite self-development requires kernel and desktop regression tools"
            )
        self.save("candidates", c, db)
        return {k: v for k, v in c.items() if k != "base"}

    def patch(self, a, p):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            c = self.record("candidates", a["id"])
            self.require_owner(c, p)
            if c["state"] != "Draft":
                raise KernelError("Candidate is not editable")
            path = a["path"]
            if not any(
                path.startswith(s) if s.endswith("/") else path == s for s in p.paths
            ):
                raise KernelError("Current delegation does not permit this file")
            if not any(
                path.startswith(s) if s.endswith("/") else path == s for s in c["paths"]
            ):
                raise KernelError("File outside candidate scope")
            if any(
                j["candidate"] == c["id"]
                and j["state"] in ("Queued", "Running")
                and j["tool"] not in ("clip.loop", "clip.workshop")
                for j in self.listing("jobs")
            ):
                raise KernelError("Candidate is locked while a job is using its source")
            target = self.safe(path, self.candidate_root(c["id"]), must_exist=False)
            if target.name.startswith("test_") or target.name in (
                "ring_oracle.mjs",
                "state_oracle.mjs",
                "struthio_tower_generated.h",
            ):
                raise KernelError(
                    "Regression oracle/generated constants are protected; separate operator-reviewed source pass required"
                )
            old = target.read_bytes() if target.exists() else b""
            if digest(old) != a["sha256"]:
                raise KernelError("Candidate file version conflict")
            data = a["content"].encode("utf-8")
            if len(data) > 1024 * 1024:
                raise KernelError("Patch exceeds 1 MiB")
            original = self.state / "candidates" / c["id"] / "original" / path
            if path not in c["changes"]:
                original.parent.mkdir(parents=True, exist_ok=True)
                original.write_bytes(old)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            c["changes"][path] = digest(data)
            self.save("candidates", c, db)
        return {"id": c["id"], "path": path, "sha256": digest(data)}

    def diff(self, id):
        c = self.record("candidates", id)
        rows = []
        for name, sha in c["changes"].items():
            before = self.state / "candidates" / id / "original" / name
            old = before.read_text(encoding="utf-8") if before.exists() else ""
            new = (self.candidate_root(id) / name).read_text(encoding="utf-8")
            rows.append(
                {
                    "path": name,
                    "base_sha256": c["base"].get(name),
                    "candidate_sha256": sha,
                    "diff": "".join(
                        difflib.unified_diff(
                            old.splitlines(True),
                            new.splitlines(True),
                            fromfile="accepted/" + name,
                            tofile="candidate/" + name,
                        )
                    ),
                }
            )
        return {
            "id": id,
            "state": c["state"],
            "changes": rows,
            "approval_required": True,
        }

    def transition(self, op, a, p):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            c = self.record("candidates", a["id"])
            self.require_owner(c, p)
            if any(
                j.get("candidate") == c["id"]
                and j["state"] in ("Queued", "Running")
                and j["tool"] not in ("clip.loop", "clip.workshop")
                for j in self.listing("jobs")
            ):
                raise KernelError("Job still uses candidate")
            if op == "candidates.reject":
                if c["state"] not in ("Draft", "Waiting for Approval"):
                    raise KernelError("Cannot reject applied candidate")
                c["state"] = "Rejected"
            elif op == "candidates.review":
                if c["state"] != "Draft" or not c["changes"]:
                    raise KernelError("An edited draft is required")
                c["state"] = "Waiting for Approval"
            elif op == "candidates.accept":
                if c["state"] != "Waiting for Approval":
                    raise KernelError("Submit candidate for review first")
                if c.get("external_agent_task") and p.identity == c["owner"]:
                    raise KernelError("An external agent cannot accept its own candidate")
                self.validate_promotion(c)
                if c.get("repair") and p.identity in (c["owner"], c["repair"].get("review", {}).get("identity")):
                    raise KernelError("Baseline repair acceptance requires the independent operator")
                if any(name.startswith("workbench/") for name in c["changes"]):
                    raise KernelError(
                        "Running Graphite cannot self-replace; stage/restart workflow required"
                    )
                c["journal"] = {
                    "operation": "accept",
                    "files": list(c["changes"]),
                    "at": now(),
                }
                journal = self.state / "recovery.json"
                journal.write_text(json.dumps(c), encoding="utf-8")
                for name in c["changes"]:
                    target = self.safe(name, must_exist=False)
                    backup = self.state / "candidates" / c["id"] / "backup" / name
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        shutil.copy2(target, backup)
                try:
                    for name in c["changes"]:
                        target = self.safe(name, must_exist=False)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        staged = target.with_name(target.name + ".ledger-tmp")
                        shutil.copy2(self.candidate_root(c["id"]) / name, staged)
                        os.replace(staged, target)
                except OSError:
                    self.restore(c)
                    raise
                c.update(state="Accepted", approved_by=p.identity, accepted_at=now())
                self.save("candidates", c, db)
                # Journal remains until transaction has committed; recovery can inspect source hashes.
            elif op == "candidates.rollback":
                if c["state"] != "Accepted":
                    raise KernelError("Only accepted candidates can be rolled back")
                if any(name.startswith("workbench/") for name in c["changes"]):
                    from .update_service import ensure_closed

                    ensure_closed(self)
                for name, sha in c["changes"].items():
                    if digest(self.safe(name).read_bytes()) != sha:
                        raise KernelError(
                            "Rollback conflict; accepted file has subsequent edits"
                        )
                c["journal"] = {"operation": "rollback", "at": now()}
                (self.state / "recovery.json").write_text(
                    json.dumps(c), encoding="utf-8"
                )
                self.restore(c)
                c.update(state="Rolled Back", rolled_back_by=p.identity)
            self.save("candidates", c, db)
            if op in ("candidates.accept", "candidates.reject", "candidates.rollback"):
                for task in self.listing("jobs"):
                    if (
                        task.get("candidate") == c["id"]
                        and task["tool"] in ("clip.loop", "clip.external", "clip.workshop")
                        and task["state"] not in ("Cancelled", "Failed")
                    ):
                        task.update(
                            state="Completed",
                            outcome=c["state"],
                            current_operation="Operator decision: " + c["state"],
                        )
                        self.save("jobs", task, db)
        if op in ("candidates.accept", "candidates.rollback"):
            (self.state / "recovery.json").unlink(missing_ok=True)
        return {"id": c["id"], "state": c["state"]}

    def validate_promotion(self, c):
        if any(n in register_proposals.PATHS for n in c['changes']) and not c.get('register_proposal'):
            raise KernelError('Register promotion requires a typed text proposal')
        if c.get('register_proposal'):
            register_proposals.validate_candidate(self, c)
        if hashes(self.root) != c["base"]:
            raise KernelError(
                "Accepted source changed since snapshot; rebase in a new candidate"
            )
        fresh = revision(hashes(self.candidate_root(c["id"])))
        evidence = self.listing("evidence")
        for tool in c["required_tools"]:
            if not any(
                e["candidate"] == c["id"]
                and e["tool"] == tool
                and e["revision"] == fresh
                and e["state"] == "Completed"
                for e in evidence
            ):
                raise KernelError("Missing fresh passing candidate evidence: " + tool)
            if not any(
                e["candidate"] is None
                and e["tool"] == tool
                and e["revision"] == c["revision"]
                and e["state"] == "Completed"
                for e in evidence
            ):
                if not baseline_repair.valid_grant(self, c, tool):
                    raise KernelError("Missing passing baseline evidence or explicitly reviewed repair authorization: " + tool)

    def restore(self, c):
        for name in c["changes"]:
            backup = self.state / "candidates" / c["id"] / "backup" / name
            target = self.safe(name, must_exist=False)
            if backup.exists():
                shutil.copy2(backup, target)
            elif name not in c["base"]:
                target.unlink(missing_ok=True)

    def submit(self, a, p):
        if not ledger_control.value(self,'operations.services_enabled'):
            raise KernelError('LEDGER_SERVICES_OFF: use Menu → Graphite services → On before submitting new work')
        tool = a["tool"]
        if tool in lab_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Lab jobs use owned selected snapshots')
            if a.get('timeout')!=(30 if tool=='lab.python' else 180):raise KernelError('Lab jobs require their bounded profile timeout')
            options=a.get('lab',{})
            if a.get('request_key')!='lab:'+str(options.get('action')):raise KernelError('Lab jobs require a stable action key')
            lab_service.authorize_job(self,tool,options,p)
        elif 'lab' in a:raise KernelError('Lab options belong only to registered lab jobs')
        if tool in math_service.JOB_TOOLS:
            if a.get("candidate") or a.get("isolation"):raise KernelError("Mathematical Office jobs use clean owned projections")
            options=a.get("calculation",{})
            if a.get("request_key")!="math-office:"+str(options.get("action")):raise KernelError("Mathematical Office jobs require their stable action key")
            math_service.authorize_job(self,tool,options,p)
        elif "calculation" in a:raise KernelError("Calculation options belong only to mathematical Office jobs")
        if tool in office_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Office jobs use clean private document projections only')
            options=a.get('office',{})
            if a.get('request_key')!='office:'+str(options.get('plan')):raise KernelError('Office jobs require the reviewed idempotency key')
            office_service.authorize_job(self,tool,options,p)
        elif 'office' in a:raise KernelError('Office options belong only to registered Office jobs')
        if tool in investigation_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Engineering cases use fixed read-only source profiles, never a project candidate')
            investigation_service.authorize_job(self,tool,a.get('investigation',{}),p)
        elif 'investigation' in a:raise KernelError('Investigation options belong only to the registered case job')
        if tool in evidence_compiler.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Evidence Compiler never executes a project candidate')
            evidence_compiler.authorize_job(self,tool,a.get('packet',{}),p)
        elif 'packet' in a:raise KernelError('Packet options belong only to the registered Evidence Compiler')
        if tool in knowledge_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Source connections never execute project candidates')
            knowledge_service.authorize_job(self,tool,a.get('knowledge',{}),p)
        elif 'knowledge' in a:raise KernelError('Knowledge options belong only to registered source jobs')
        if tool in study_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Study uses current read-only originals, not executable candidates')
            opts=a.get('study',{})
            if a.get('request_key')!='study:'+str(opts.get('id'))+':'+str(opts.get('attempt')):raise KernelError('Study requires its reserved idempotency key')
            study_service.authorize_job(self,tool,opts,p)
        elif 'study' in a:raise KernelError('Study options belong only to the study reader job')
        if tool in reference_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Reference jobs use admitted originals, never executable candidates')
            reference_service.authorize_job(self,tool,a.get('references',{}),p)
        elif 'references' in a:raise KernelError('Reference options belong only to registered reference jobs')
        if tool in intake_service.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('Intake jobs use private reference storage, never an executable candidate')
            intake_service.authorize_job(self,tool,a.get('intake',{}),p)
        elif 'intake' in a:raise KernelError('Intake options belong only to registered intake jobs')
        if tool in network_capture.JOB_TOOLS:
            if a.get('candidate') or a.get('isolation'):raise KernelError('A capture runs the system capture tool, never a project candidate')
            network_capture.authorize_job(self,tool,a.get('network'),a.get('request_key'),p)
        elif 'network' in a:raise KernelError('Network options belong only to the capture job')
        if tool in local_brain.JOB_TOOLS:
            if tool != 'brain.inspect':local_brain.require_enabled(self)
            if tool==edit_model.TOOL:edit_model.authorize_job(self,a.get('brain',{}),p)
            if tool in slate_reasoning.JOB_TOOLS:slate_reasoning.authorize_job(self,tool,a.get('brain',{}),p)
            if tool in slate_action.JOB_TOOLS:
                if a.get('request_key')!='slate-action:'+str(a.get('brain',{}).get('conversation')) or a.get('timeout')!=240:raise KernelError('ACTION jobs require their frozen request key and deadline')
                slate_action.authorize_job(self,tool,a.get('brain',{}),p)
            if tool in ('brain.inspect','brain.activate','brain.qualify') and 'approve' not in p.scopes:raise KernelError('Model registration, qualification and activation require direct owner approval')
            if a.get('candidate') or a.get('isolation'):raise KernelError('Brain jobs use registered external weights and the pinned local runtime')
            if tool in ('brain.activate','brain.qualify'):
                selected=local_brain.model(self,a.get('brain',{}).get('model_id'))
        elif 'brain' in a:raise KernelError('Brain options belong only to registered Brain jobs')
        if tool=='native.build':
            native_projects.project(self.root,a.get('project'))
            if a.get('candidate') or a.get('isolation'):raise KernelError('Native starter builds use the explicit trusted local workspace')
        elif 'project' in a:raise KernelError('Project parameter is only registered for native.build')
        key = a.get("request_key", uuid.uuid4().hex)
        if tool in ("clip.loop", "clip.workshop"):
            raise KernelError(
                "Use clip.submit and explicit bounded-scope authorization"
            )
        if tool not in TOOLS or tool not in p.tools:
            raise KernelError("Tool is not authorized")
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise KernelError("Invalid idempotency key")
        request_spec = {k: v for k, v in a.items() if k != "request_key"}
        with self.db() as db:
            old = db.execute(
                "SELECT job FROM requests WHERE owner=? AND key=?", (p.identity, key)
            ).fetchone()
        if old:
            prior = self.record("jobs", old[0])
            if prior.get("request_spec", request_spec) != request_spec:
                raise KernelError("Idempotency key reused with different request")
            with self.db() as db:work_trail.bind(db,self,p.identity,prior['id'])
            return prior
        timeout = a.get("timeout", 120)
        if type(timeout) not in (int, float) or not 1 <= timeout <= 600:
            raise KernelError("Runtime must be 1–600 seconds")
        candidate = a.get("candidate")
        source = self.root
        if candidate:
            c = self.record("candidates", candidate)
            self.require_owner(c, p)
            if c["state"] != "Draft":
                raise KernelError("Only editable draft candidates can be tested")
            source = self.candidate_root(candidate)
            if tool != "struthio.build" and c.get("execution_approval", {}).get(
                "revision"
            ) != revision(hashes(source)):
                raise KernelError(
                    "Native candidate execution needs operator review/authorization for this exact revision; host processes are not an OS sandbox"
                )
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT job FROM requests WHERE owner=? AND key=?", (p.identity, key)
            ).fetchone()
            if old:
                prior = self.record("jobs", old[0])
                if prior.get("request_spec", request_spec) != request_spec:
                    raise KernelError("Idempotency key reused with different request")
                work_trail.bind(db,self,p.identity,prior["id"])
                return prior
            work_trail.accepting(self,db)
            active = db.execute(
                "SELECT count(*) FROM jobs WHERE state IN ('Queued','Running')"
            ).fetchone()[0]
            if active >= 16:
                raise KernelError("Sixteen active or waiting jobs reached; finish or cancel an existing request")
            if active>=14 and resource_control.current_priority()!='foreground':
                raise KernelError('Two queue places are reserved for foreground requests')
            if tool not in (lab_service.JOB_TOOLS|math_service.JOB_TOOLS|office_service.JOB_TOOLS|local_brain.JOB_TOOLS|intake_service.JOB_TOOLS|reference_service.JOB_TOOLS|study_service.JOB_TOOLS|knowledge_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS|investigation_service.JOB_TOOLS|network_capture.JOB_TOOLS) and any(
                j.get("candidate") == candidate
                and j["state"] in ("Queued", "Running")
                and j["tool"] not in ("clip.loop", "clip.workshop")
                and j['tool'] not in (lab_service.JOB_TOOLS|math_service.JOB_TOOLS|office_service.JOB_TOOLS|local_brain.JOB_TOOLS|intake_service.JOB_TOOLS|reference_service.JOB_TOOLS|study_service.JOB_TOOLS|knowledge_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS|investigation_service.JOB_TOOLS|network_capture.JOB_TOOLS)
                for j in self.listing("jobs")
            ):
                raise KernelError("This source workspace already has an active job")
            job = {
                "id": uuid.uuid4().hex,
                "owner": p.identity,
                "state": "Queued",
                "goal": str(a.get("goal", tool))[:2000],
                "tool": tool,
                "candidate": candidate,
                "revision": revision(hashes(source)),
                "created": now(),
                "scope": list(p.paths),
                "timeout": timeout,
                "cancel": False,
                "pause": False,
                "pid": None,
                "approval_required": bool(candidate),
                "request_spec": request_spec,
                "isolation": a.get('isolation'),
                "iteration_limit": 1,
                "provider_budget": 0,
                "current_operation": "queued",
            }
            if tool in ('brain.activate','brain.qualify'):
                from .model_settings import freeze_launch
                job['brain_launch']=freeze_launch(self,selected,a.get('brain',{}),db)
            if tool in local_brain.JOB_TOOLS:
                job['brain_epoch'] = local_brain.get(self, 'stop_epoch', 0, db)
            job['resource_request']=resource_control.request(job)
            if job['resource_request']['priority']=='foreground':resource_control.touch(self,p.identity,db)
            self.save("jobs", job, db)
            work_trail.bind(db,self,p.identity,job["id"])
            db.execute(
                "INSERT INTO requests VALUES(?,?,?)", (p.identity, key, job["id"])
            )
        self.launch(job["id"])
        return job

    def launch(self, id):
        flags = (
            {"start_new_session": True}
            if os.name != "nt"
            else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        )
        output = self.state / "jobs" / identifier(id)
        output.mkdir(parents=True, exist_ok=True)
        with (output / "worker.log").open("ab") as log:
            self._workers[id]=subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "workbench.engineering_cli",
                    "--root",
                    str(self.root),
                    "worker",
                    identifier(id),
                ],
                cwd=self.root,
                env=locations.child_env(self.root),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                **flags,
            )

    def run_job(self, id):
        j=resource_control.claim(self,id)
        if j is None:return
        if j["tool"] == "clip.loop":
            from .clip_jobs import run

            run(self, id)
            return
        if j["tool"] == 'clip.workshop':
            clip_workshop.run(self, id)
            return
        if j["tool"] in network_capture.JOB_TOOLS:
            network_capture.run(self, id)  # HATCH DESK D5: the capture tool, followed and stopped here (jobs.cancel, Master Stop, held work)
            return
        source = self.candidate_root(j["candidate"]) if j["candidate"] else self.root
        original_source = source
        output = self.state / "jobs" / id
        output.mkdir(parents=True, exist_ok=True)
        module, *arguments = TOOLS[j["tool"]]
        argv = (
            [sys.executable, str(locations.program(source) / "arc1"), *arguments]
            if module == "arc1"
            else [sys.executable, "-m", module, *arguments]
        )
        if module not in ("unittest", "arc1"):
            argv += ["--root", str(source)]
        if j['tool']=='native.build':argv+=['--project',j['request_spec']['project']]
        if j['tool'] in (lab_service.JOB_TOOLS|math_service.JOB_TOOLS|office_service.JOB_TOOLS|local_brain.JOB_TOOLS|intake_service.JOB_TOOLS|reference_service.JOB_TOOLS|study_service.JOB_TOOLS|knowledge_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS|investigation_service.JOB_TOOLS):argv+=['--job',id]
        if j['tool'].startswith(('cad.','kibot.','spice.','yosys.','nextpnr.','trellis.','icarus.','verilator.','surfer.')):argv+=['--job',id]
        start = time.monotonic()
        proc = None
        state = "Failed"
        error = ""
        exit_code = None
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            in (
                "PATH",
                "SystemRoot",
                "WINDIR",
                "TEMP",
                "TMP",
                "HOME",
                "USERPROFILE",
                "LANG",
            )
        }
        env["PYTHONPATH"] = str(locations.program(source))
        env["PYTHONUNBUFFERED"] = "1"
        env["QT_QPA_PLATFORM"] = "offscreen"
        if (j.get('resource_request') or {}).get('priority')=='background':
            threads=str(j['resource_admission']['policy']['background_threads'])
            for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS'):env[name]=threads
        if module == 'unittest':
            # These existing fixture suites construct tiny isolated project
            # roots. They exercise the Kernel directly; they must not launch
            # another service for each disposable test fixture.
            env['ARC_LEDGER_EMBEDDED'] = '1'
        if j['tool'] in (lab_service.JOB_TOOLS|math_service.JOB_TOOLS|office_service.JOB_TOOLS|local_brain.JOB_TOOLS|intake_service.JOB_TOOLS|reference_service.JOB_TOOLS|study_service.JOB_TOOLS|knowledge_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS|investigation_service.JOB_TOOLS):
            from .session import config_dir
            env['ARC1_WORKBENCH_CONFIG_HOME']=str(config_dir())
        if j['tool'] in ('references.office.edit','math.session'):
            for name in ('DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XAUTHORITY'):
                if name in os.environ:env[name]=os.environ[name]
        before_outputs = (
            {
                p.relative_to(source).as_posix(): digest(p.read_bytes())
                for p in (source / "build").rglob("*")
                if p.is_file()
            }
            if (source / "build").exists()
            else {}
        )
        input_hashes = hashes(source)
        isolation = {'available': False, 'active': False, 'mechanism': 'ordinary host process'}
        try:
            if revision(input_hashes) != j["revision"]:
                raise KernelError("Source changed before execution")
            if j.get('isolation'):
                from . import workshop_sandbox
                if j['isolation'] != workshop_sandbox.PROFILE:
                    raise KernelError('Unknown isolation profile')
                snapshot = output / 'isolation' / 'source'
                snapshot.mkdir(parents=True, exist_ok=True)
                for name in input_hashes:
                    dest = snapshot / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / name, dest)
                if hashes(snapshot) != input_hashes:
                    raise KernelError('Source changed while preparing isolated execution')
                source = snapshot
                env['PYTHONPATH'] = str(locations.program(source))
                env['PYTHONDONTWRITEBYTECODE'] = '1'
                module, *arguments = TOOLS[j['tool']]
                argv = ([sys.executable, str(locations.program(source) / 'arc1'), *arguments] if module == 'arc1'
                        else [sys.executable, '-m', module, *arguments])
                if module not in ('unittest', 'arc1'):
                    argv += ['--root', str(source)]
                if j['tool'].startswith(('cad.','kibot.','spice.','yosys.','nextpnr.','trellis.','icarus.','verilator.','surfer.')):argv+=['--job',id]
                argv, isolation = workshop_sandbox.command(argv, source, env)
                isolation = {**isolation, 'active': True}
            with (
                (output / "stdout.log").open("wb") as stdout,
                (output / "stderr.log").open("wb") as stderr,
            ):
                proc = subprocess.Popen(
                    argv,
                    cwd=source,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=os.name != "nt",
                    stdin=subprocess.DEVNULL,
                )
                with self.db() as db:
                    db.execute("BEGIN IMMEDIATE")
                    live = self.record("jobs", id)
                    live["tool_pid"] = proc.pid
                    live["tool_start"] = process_token(proc.pid)
                    self.save("jobs", live, db)
                while proc.poll() is None:
                    live = self.record("jobs", id)
                    if (
                        live["cancel"]
                        or work_trail.execution_held(self)
                        or time.monotonic() - start > j["timeout"]
                        or sum(
                            (output / n).stat().st_size
                            for n in ("stdout.log", "stderr.log")
                        )
                        > MAX_LOG
                    ):
                        if os.name != "nt":
                            os.killpg(proc.pid, signal.SIGKILL)
                        else:
                            subprocess.run(
                                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                capture_output=True,
                                timeout=10,
                            )
                        proc.wait(timeout=10)
                        state = (
                            "Paused"
                            if live.get("pause")
                            else "Cancelled"
                            if live["cancel"] or work_trail.execution_held(self)
                            else "Failed"
                        )
                        error = (
                            "Paused at tool boundary; resume reruns tool"
                            if state == "Paused"
                            else "Cancelled"
                            if state == "Cancelled"
                            else "Runtime or output limit exceeded"
                        )
                        break
                    time.sleep(0.05)
                else:
                    control = self.record("jobs", id)
                    state = ("Paused" if control.get("cancel") and control.get("pause") else
                             "Cancelled" if control.get("cancel") or work_trail.execution_held(self) else
                             "Completed" if proc.returncode == 0 else "Failed")
                exit_code = proc.returncode
            if revision(hashes(source)) != j["revision"]:
                state = "Failed"
                error = (
                    "Source mutated during tool execution; result cannot be accepted"
                )
            if hashes(original_source) != input_hashes:
                state = 'Failed'
                error = 'Original source changed during isolated execution'
        except Exception as exc:
            error = str(exc)
            state = "Failed"
        if state == "Failed" and not error:
            # A tool that exits non-zero leaves its reason only in its logs.
            tail = [line.strip() for name in ("stdout.log", "stderr.log") if (output / name).exists()
                    for line in (output / name).read_text(errors="replace").splitlines()[-40:] if line.strip()]
            error = "Tool exited with status " + str(exit_code) + (": " + tail[-1][:300] if tail else "")
        artifacts = []
        if (source / "build").exists():
            for path in (source / "build").rglob("*"):
                if path.is_file() and not path.is_symlink():
                    name = path.relative_to(source).as_posix()
                    sha = digest(path.read_bytes())
                    if before_outputs.get(name) != sha:
                        artifacts.append(
                            {"path": name, "sha256": sha, "bytes": path.stat().st_size}
                        )
        ev = {
            "id": uuid.uuid4().hex,
            "job": id,
            "candidate": j["candidate"],
            "tool": j["tool"],
            "revision": j["revision"],
            "input_hashes": input_hashes,
            "state": state,
            "class": "STATIC_CHECK" if j["tool"] == "hardware.inspect" else "HOST_SIM",
            "environment": {
                "platform": sys.platform,
                "python": sys.version,
                "physical_hardware": False,
                "isolation": isolation,
            },
            "argv": argv,
            "cwd": str(source),
            "exit_status": exit_code,
            "duration_seconds": time.monotonic() - start,
            "resource_use": None,
            "artifacts": artifacts,
            "created": now(),
            "error": error,
            "stdout": (output / "stdout.log").read_text(errors="replace")[:MAX_LOG]
            if (output / "stdout.log").exists()
            else "",
            "stderr": (output / "stderr.log").read_text(errors="replace")[:MAX_LOG]
            if (output / "stderr.log").exists()
            else "",
        }
        detail_path={'arcos.parser':'build/arcos/command-parser.json','links.export':'build/links/export.json',
                     'console.build':'build/virtual_console/build.json','console.lifecycle':'build/virtual_console/lifecycle.json'}.get(j['tool'])
        if j['tool']=='native.build':detail_path='build/native_projects/'+j['request_spec']['project']+'.json'
        if j['tool'] in local_brain.JOB_TOOLS:
            detail_path='build/brain/runs/'+id+'/result.json'
            ev['class']='LOCAL_INFERENCE';ev['target_status']='NOT_APPLICABLE'
        if j['tool'] in intake_service.JOB_TOOLS:
            detail_path='build/intake/runs/'+id+'/result.json'
            ev['class']='STATIC_CHECK';ev['target_status']='NOT_APPLICABLE'
        if j['tool'] in knowledge_service.JOB_TOOLS:
            detail_path='build/knowledge/runs/'+id+'/result.json'
            ev['class']='STATIC_CHECK';ev['target_status']='NOT_APPLICABLE'
        if j['tool'] in investigation_service.JOB_TOOLS:
            detail_path='build/investigations/runs/'+id+'/result.json'
            ev['class']='HOST_SIM' if j['request_spec']['investigation']['case']=='PSRAM_TCEM' else 'STATIC_CHECK';ev['target_status']='HOLD'
        if j['tool'] in study_service.JOB_TOOLS:
            detail_path='build/study/runs/'+id+'/result.json'
            ev['class']='STATIC_CHECK';ev['target_status']='NOT_APPLICABLE'
        if j['tool'] in office_service.JOB_TOOLS:
            ev['class']='STATIC_CHECK';ev['target_status']='NOT_APPLICABLE'
        if j['tool'] in (reference_service.JOB_TOOLS|evidence_compiler.JOB_TOOLS):
            detail_path='build/references/runs/'+id+'/result.json'
            ev['class']='STATIC_CHECK';ev['target_status']='NOT_APPLICABLE'
        if j['tool'].startswith('cad.'):detail_path='build/cad/runs/'+id+'/record.json'
        if j['tool'].startswith('kibot.'):detail_path='build/kibot/runs/'+id+'/record.json'
        if j['tool'].startswith('spice.'):
            detail_path='build/spice/runs/'+id+'/record.json'
            ev.update({'class':'HOST_SIM','target_status':'HOLD','outcome':'CANCELLED' if state=='Cancelled' else 'NOT_ASSESSED'})
        if j['tool'].startswith('yosys.'):
            detail_path='build/yosys/runs/'+id+'/record.json'
            ev.update({'class':'STATIC_CHECK','target_status':'HOLD','outcome':'CANCELLED' if state=='Cancelled' else 'NOT_ASSESSED'})
        if j['tool'].startswith(('nextpnr.','trellis.')):
            detail_path='build/'+j['tool'].split('.')[0]+'/runs/'+id+'/record.json'
            ev.update({'class':'STATIC_CHECK','target_status':'HOLD','outcome':'CANCELLED' if state=='Cancelled' else 'NOT_ASSESSED'})
        if j['tool'].startswith(('icarus.','verilator.','surfer.')):
            detail_path='build/'+('surfer' if j['tool'].startswith('surfer.') else 'hdl')+'/runs/'+id+'/record.json'
            evidence_class='HOST_SIM' if j['tool'].startswith('icarus.') or j['tool'] in ('verilator.pump','verilator.qualify') else 'STATIC_CHECK'
            ev.update({'class':evidence_class,'target_status':'HOLD','outcome':'CANCELLED' if state=='Cancelled' else 'NOT_ASSESSED'})
        if j['tool'].startswith(('cad.','kibot.')):
            ev['class']='STATIC_CHECK';ev['target_status']='HOLD'
            ev['outcome']='CANCELLED' if state=='Cancelled' else 'NOT_ASSESSED'
        if detail_path and (source/detail_path).is_file():
            detail=json.loads((source/detail_path).read_text())
            if detail.get('created',0)>=j['started']:
                ev['diagnostics']=detail;ev['outcome']=detail.get('status',detail.get('state','UNASSESSED'))
                ev['class']=detail.get('class','UNASSESSED')
                if j['tool'].startswith('cad.'):
                    ev['tool_versions']={'kicad':{k:detail.get('tool',{}).get(k) for k in ('version','sha256','resolved_executable')}}
                if j['tool'].startswith('kibot.'):
                    ev['tool_versions']={name:{k:detail.get(field,{}).get(k) for k in ('version','sha256','resolved_executable')}
                                         for name,field in (('kibot','tool'),('kicad','kicad'))}
        if j['tool'].startswith('spice.'):
            ev['class']='HOST_SIM';ev['target_status']='HOLD'
            ev['tool_versions']={'ngspice':{k:ev.get('diagnostics',{}).get('tool',{}).get(k) for k in ('version','sha256','resolved_executable')}}
            if state=='Cancelled':ev['outcome']='CANCELLED'
            elif state!='Completed' and ev.get('outcome') in ('QUALIFIED','SIMULATED'):ev['outcome']='NOT_ASSESSED'
        if j['tool'].startswith('yosys.'):
            ev['class']='STATIC_CHECK';ev['target_status']='HOLD'
            ev['tool_versions']={'yosys':{k:ev.get('diagnostics',{}).get('tool',{}).get(k) for k in ('version','sha256','resolved_executable')}}
            if state=='Cancelled':ev['outcome']='CANCELLED'
            elif state!='Completed' and ev.get('outcome') in ('QUALIFIED','SYNTHESIZED'):ev['outcome']='NOT_ASSESSED'
        if j['tool'].startswith(('nextpnr.','trellis.')):
            ev['class']='STATIC_CHECK';ev['target_status']='HOLD'
            ev['tool_versions']={name:{k:tool.get(k) for k in ('version','sha256','resolved_executable')}
                                 for name,tool in ev.get('diagnostics',{}).get('tools',{}).get('programs',{}).items() if tool}
            if state=='Cancelled':ev['outcome']='CANCELLED'
            elif state!='Completed' and ev.get('outcome') in ('QUALIFIED','ROUTED_CLOCKS_MET','ROUTED_CLOCKS_MISSED','PACKED_HELD'):ev['outcome']='NOT_ASSESSED'
        if j['tool'].startswith(('icarus.','verilator.','surfer.')):
            ev['class']='HOST_SIM' if j['tool'].startswith('icarus.') or j['tool'] in ('verilator.pump','verilator.qualify') else 'STATIC_CHECK'
            ev['target_status']='HOLD';detail=ev.get('diagnostics',{})
            ev['tool_versions']={j['tool'].split('.')[0]:detail.get('tool',detail.get('tools',{}))}
            if state=='Cancelled':ev['outcome']='CANCELLED'
            elif state!='Completed' and ev.get('outcome') in ('QUALIFIED','SIMULATED','LINT_CLEAN','LINT_WARNINGS','RENDERED'):ev['outcome']='NOT_ASSESSED'
        build_report = source / "build/native_struthio/build.json"
        ev.setdefault('tool_versions',{})['python']=sys.version
        if j["tool"].startswith("struthio.") and build_report.is_file():
            try:
                report = json.loads(build_report.read_text())
                ev["tool_versions"]["compiler"] = {
                    "name": report["tool"],
                    "version": report["version"],
                }
            except (ValueError, KeyError, OSError):
                pass
        if j["tool"].startswith(("qualification.", "arcos.")):
            report = (
                source
                / ("build/arcos" if j["tool"].startswith("arcos.") else "build/agent_qualification")
                / (j["tool"].split(".")[-1] + ".json")
            )
            if report.is_file():
                detail = json.loads(report.read_text())
                if detail.get("created", 0) >= j["started"]:
                    ev["diagnostics"] = detail
                    if detail.get("compiler_version"):
                        ev["tool_versions"]["compiler"] = detail["compiler_version"]
                    if detail["status"] == "BLOCKED":
                        ev["outcome"] = "BLOCKED"
                    elif j["tool"].startswith("arcos."):
                        ev["outcome"] = detail["status"]
                        ev["class"] = "STATIC_CHECK" if j["tool"] == "arcos.dependencies" else "HOST_SIM"
                    elif j["tool"] == "qualification.rtl":
                        ev["class"] = "RTL_SIM"
        if j["tool"] in ("struthio.test", "struthio.differential"):
            report = source / "build/native_struthio" / (j["tool"].split(".")[-1] + ".json")
            if report.is_file():
                detail = json.loads(report.read_text())
                if detail.get("created", 0) >= j["started"]:
                    ev["diagnostics"] = detail
                    ev["outcome"] = detail["status"]
                    ev["class"] = "HOST_SIM"
        if j["tool"].startswith("proof."):
            report_path = source / "build/hardware_proof" / (j["tool"].split(".")[-1]+".json")
            ev["class"] = "STATIC_CHECK"
            if report_path.is_file():
                detail = json.loads(report_path.read_text())
                if detail.get("created", 0) >= j["started"]:
                    ev["diagnostics"] = detail
                    ev["tool_versions"].update(detail.get("tool_versions", {}))
                    ev["outcome"] = detail.get("status", "SOURCE-CHECKED")
        if j["tool"] in ("simulation.campaign", "boot.campaign", "boot.first_stage") or j["tool"].startswith("firmware."):
            folder = {"boot.campaign": "boot_loading", "boot.first_stage": "first_stage",
                      "simulation.campaign": "console_simulation"}.get(j["tool"])
            folder = folder or "firmware/" + j["tool"].split(".", 1)[1]
            report_path = source / "build" / folder / "campaign.json"
            if report_path.is_file():
                detail = json.loads(report_path.read_text())
                if detail.get("created", 0) >= j["started"]:
                    ev["diagnostics"] = detail
                    # The host experiment result and the target state are separate facts: a host PASS never
                    # makes the target anything but BLOCKED.
                    ev["outcome"] = detail.get("experiment_status", detail.get("status"))
                    ev["target_status"] = detail.get("target_status", detail.get("status", "BLOCKED"))
                    ev["class"] = "HOST_SIM"
        if j["tool"] == "register.analyze_power":
            report_path = source / "build/register/power_analysis.json"
            if report_path.is_file():
                detail = json.loads(report_path.read_text())
                if detail.get("created", 0) >= j["started"]:
                    ev["diagnostics"] = detail
                    ev["outcome"] = detail["outcome"]
                    ev["target_status"] = "BLOCKED"
                    ev["class"] = "HOST_SIM"
        self.save("evidence", ev)
        # Preserve process ownership and cancellation fields recorded while the
        # child ran. The launch-time copy predates tool_pid/tool_start.
        j=self.record('jobs',id)
        j.update(
            state=state,
            finished=now(),
            evidence=ev["id"],
            error=error,
            current_operation="finished",
        )
        self.save("jobs", j)
        if not j.get("candidate") and j["tool"] != "book.refresh":
            # The desktop watcher or the next book read consumes this request.
            # Never recursively submit jobs from a completed book export.
            orange_book.request_refresh(self.root)

    def recover_interrupted(self):
        """Never auto-resume mutations. Running workers survive closed tabs/clients."""
        recovered = []
        for j in stacy_awareness.live_jobs(self):
            if j["state"] == "Queued" and now() - j.get("created", now()) > 60 and not (
                j.get('worker_start') is not None and process_token(j.get('pid'))==j['worker_start']):
                j.update(
                    state="Interrupted",
                    error="Worker did not claim queued task; verify source and resume explicitly",
                )
                self.save("jobs", j)
                recovered.append(j["id"])
            if j["state"] == "Running":
                try:
                    os.kill(j["pid"], 0)
                    current_token=process_token(j['pid'])
                    if j.get('worker_start') and current_token is not None and current_token!=j['worker_start']:
                        raise KernelError('Manual recovery required: worker process identity changed; no signal sent')
                    if (
                        sys.platform.startswith("linux")
                        and process_token(j["pid"]) is None
                    ):
                        raise ProcessLookupError("Worker exited or is a zombie")
                except (ProcessLookupError, TypeError):
                    pid = j.get("tool_pid")
                    if pid and os.name == "nt":
                        raise KernelError(
                            "Manual Windows orphan-process recovery required before resume"
                        )
                    if pid and process_token(pid) is not None:
                        if (
                            not j.get("tool_start")
                            or process_token(pid) != j["tool_start"]
                        ):
                            raise KernelError(
                                "Manual recovery required: orphan process identity changed"
                            )
                        os.killpg(pid, signal.SIGKILL)
                    j["recovery"] = {
                        "at": now(),
                        "operation": "Dead worker detected; tracked POSIX tool group stopped",
                        "logs": ".ledger/jobs/" + j["id"],
                    }
                    j.update(
                        state="Interrupted",
                        error="Worker no longer exists; verify source and resume explicitly",
                    )
                    self.save("jobs", j)
                    recovered.append(j["id"])
        journal = self.state / "recovery.json"
        promotion = "none"
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if journal.exists():
                c = json.loads(journal.read_text())
                record = self.record("candidates", c["id"])
                # A committed acceptance with a leftover journal is already complete.
                if (
                    record["state"] == "Accepted"
                    and c.get("journal", {}).get("operation") != "rollback"
                ):
                    promotion = "committed acceptance retained"
                    journal.unlink()
                else:
                    for name, sha in c["changes"].items():
                        target = self.safe(name, must_exist=False)
                        actual = (
                            digest(target.read_bytes()) if target.exists() else None
                        )
                        if actual not in (sha, c["base"].get(name)):
                            raise KernelError(
                                "Manual recovery required: unrelated source edit at "
                                + name
                            )
                    for name in c["changes"]:
                        target = self.safe(name, must_exist=False)
                        backup = self.state / "candidates" / c["id"] / "backup" / name
                        if backup.exists():
                            shutil.copy2(backup, target)
                        elif name not in c["base"]:
                            target.unlink(missing_ok=True)
                    promotion = "interrupted acceptance restored"
                    if (
                        record["state"] == "Verifying"
                        or c.get("journal", {}).get("operation") == "rollback"
                    ):
                        record["state"] = "Rolled Back"
                        self.save("candidates", record, db)
                    journal.unlink()
        return {"interrupted": recovered, "promotion_recovery": promotion}
