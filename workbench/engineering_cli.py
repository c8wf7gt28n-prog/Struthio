"""Stable local CLI and MCP stdio adapter over the shared engineering kernel."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import os
import stat
from .engine import engineering
from .engineering_kernel import Principal, CAPABILITIES, PROGRAM_HANDLERS, operator


def schemas():
    from .exchange import FIELDS as EXCHANGE_FIELDS
    from .release_updates import FIELDS as RELEASE_FIELDS
    from .deployment import FIELDS as DEPLOY_FIELDS
    from .continuing_work import FIELDS as CONTINUING_FIELDS
    from .worker_boundary import FIELDS as WORKER_FIELDS
    from .edit_model import FIELDS as EDIT_MODEL_FIELDS
    from .import_profiles import FIELDS as IMPORT_PROFILE_FIELDS
    from .change_sets import FIELDS as CHANGE_SET_FIELDS
    from .slate_context import FIELDS as SLATE_CONTEXT_FIELDS
    from .slate_reasoning import FIELDS as SLATE_REASONING_FIELDS
    from .project_desk import FIELDS as PROJECT_DESK_FIELDS
    from .problem_service import FIELDS as PROBLEM_FIELDS
    from .adaptive_work import FIELDS as ADAPTIVE_FIELDS
    from .joined_work import FIELDS as JOINED_FIELDS
    from .typed_artifacts import FIELDS as ARTIFACT_FIELDS
    from .checked_methods import FIELDS as METHOD_FIELDS
    from .native_sessions import FIELDS as NATIVE_SESSION_FIELDS
    from .schedule_math import FIELDS as SCHEDULE_FIELDS
    from .math_answers import FIELDS as MATH_ANSWER_FIELDS
    from .tolerances import FIELDS as TOLERANCE_FIELDS
    from .math_money import FIELDS as MONEY_FIELDS
    from .math_dates import FIELDS as DATES_FIELDS
    from .goals import FIELDS as GOAL_FIELDS  # 0.8.6 S1: goals over data
    from .reasons import FIELDS as MIND_REASON_FIELDS  # 0.8.6 S3: her reasons
    from .your_word import FIELDS as YOUR_WORD_FIELDS  # 0.8.6 S3: your word
    from .reading import FIELDS as READING_FIELDS  # 0.8.6 S4: her dictionary (requests.read)
    from .turns import FIELDS as TURN_FIELDS  # 0.8.7 E0 (the turn contract)
    from .quotes import FIELDS as QUOTE_FIELDS  # 0.8.6 S6: pinned quotes
    from .rules import FIELDS as RULE_FIELDS  # 0.8.6 S6: rule cards
    from .either_way import FIELDS as EITHER_WAY_FIELDS  # 0.8.6 S5: either way
    from .settle import FIELDS as SETTLE_FIELDS  # 0.8.6 S5: what would settle it
    from .recheck_order import FIELDS as CHANGE_CARD_FIELDS  # 0.8.6 if there is room, item 1: what this change did
    from .places import FIELDS as PLACE_FIELDS  # 0.8.6 if there is room, item 2: where does my desk say it
    from .phrases import FIELDS as PHRASE_FIELDS  # 0.8.6 S7: the phrasebook
    from .answer_check import FIELDS as PAGE_CHECK_FIELDS  # 0.8.6 S7: the page check
    from .lab_service import FIELDS as LAB_FIELDS, OPTIONS as LAB_OPTIONS
    from .reason_service import FIELDS as REASON_FIELDS
    from .math_service import FIELDS as MATH_FIELDS, OPTIONS as MATH_OPTIONS
    from .office_service import FIELDS as OFFICE_FIELDS,OPTIONS as OFFICE_OPTIONS
    from .notebook_service import FIELDS as NOTEBOOK_FIELDS
    from .notes_exchange import FIELDS as NOTES_FIELDS
    from .package_service import FIELDS as PACKAGE_FIELDS
    from .work_organizer import FIELDS as ORGANIZER_FIELDS
    from .work_trail import FIELDS as TRAIL_FIELDS
    from .slate_windows import FIELDS as WINDOW_FIELDS
    from .object_context import FIELDS as OBJECT_FIELDS
    from .addresses import FIELDS as ADDRESS_FIELDS
    from .instruction_matrix import FIELDS as MATRIX_FIELDS
    from .receiving import FIELDS as RECEIVING_FIELDS
    from .investigations import FIELDS as INVESTIGATION_LOOP_FIELDS
    from .agenda import FIELDS as AGENDA_FIELDS
    from .job_priority import FIELDS as JOB_PRIORITY_FIELDS
    from .files_service import FIELDS as FILES_FIELDS
    from .working_copies import FIELDS as COPIES_FIELDS
    from .host_support import FIELDS as HOST_SUPPORT_FIELDS
    from .pills import FIELDS as PILL_FIELDS
    from .confine import FIELDS as CONFINE_FIELDS
    from .universal_view import FIELDS as VIEWER_FIELDS
    from .discovery_service import FIELDS as DISCOVERY_FIELDS
    from .algorithm_atlas import FIELDS as ALGORITHM_FIELDS
    from .tool_atlas import FIELDS as ATLAS_FIELDS
    from .capability_catalog import FIELDS as CATALOG_FIELDS
    from .investigation_service import FIELDS as INVESTIGATION_FIELDS,OPTIONS as INVESTIGATION_OPTIONS
    from .evidence_compiler import FIELDS as PACKET_FIELDS,OPTIONS as PACKET_OPTIONS
    from .knowledge_service import FIELDS as KNOWLEDGE_FIELDS,OPTIONS as KNOWLEDGE_OPTIONS
    from .study_service import FIELDS as STUDY_FIELDS,OPTIONS as STUDY_OPTIONS
    from .research_service import FIELDS as RESEARCH_FIELDS
    from .memory_service import FIELDS as MEMORY_FIELDS
    from .stac_bridge import FIELDS as STAC_FIELDS
    from .reference_service import FIELDS as REFERENCE_FIELDS,OPTIONS as REFERENCE_OPTIONS
    from .intake_service import FIELDS as INTAKE_FIELDS, OPTIONS as INTAKE_OPTIONS
    from .stacy_language import FIELDS as LANGUAGE_FIELDS
    from .local_brain import FIELDS as BRAIN_FIELDS, OPTIONS as BRAIN_OPTIONS
    from .stacy_awareness import FIELDS as AWARENESS_FIELDS
    from .stacy_foundation import FIELDS as STACY_FIELDS
    from .hdl_tools import FIELDS as HDL_FIELDS
    from .surfer_tools import FIELDS as SURFER_FIELDS
    from .pnr_tools import FIELDS as PNR_FIELDS
    from .yosys_tools import FIELDS as YOSYS_FIELDS
    from .spice_tools import FIELDS as SPICE_FIELDS
    from .kibot_tools import FIELDS as KIBOT_FIELDS
    from .kicad_tools import FIELDS as CAD_FIELDS
    from .ledger_control import FIELDS as LEDGER_FIELDS
    from .machine_overview import FIELDS as MACHINE_FIELDS
    from .documents import FIELDS as DOCUMENT_FIELDS
    from .agent_loop import FIELDS as AGENT_FIELDS
    from .conditions import FIELDS as CONDITION_FIELDS
    from .helpers import FIELDS as HELPER_FIELDS
    from .related import FIELDS as RELATED_FIELDS
    from .browse import FIELDS as BROWSE_FIELDS
    from .network_watch import FIELDS as NETWORK_FIELDS
    from .field_service import FIELDS as FIELD_FIELDS
    from .doorway import FIELDS as DOORWAY_FIELDS  # 0.8.7 C1 (the doorway)
    from .model_account import FIELDS as ACCOUNT_FIELDS  # 0.8.7 A4 (the ledger, the marks and the account)
    from .page_marks import FIELDS as PENCIL_FIELDS  # 0.8.7 C2 (pages in pencil)
    from .library_service import FIELDS as LIBRARY_FIELDS  # 0.8.7 C3 (Ask the Library)
    from .tables import FIELDS as TABLE_FIELDS  # 0.8.7 C6a (tables that check themselves)
    from .crossrefs import FIELDS as CROSSREF_FIELDS  # 0.8.7 C6b (cross-references)
    from .model_exam import FIELDS as EXAM_FIELDS  # 0.8.7 A5 (the exam and the model key)
    from .voice_column import FIELDS as VOICE_COLUMN_FIELDS  # 0.8.7 W7 (the window wiring): voice.say
    from .living_nav import FIELDS as LIVING_NAV_FIELDS  # 1.0 L1 (one navigation state): objects.files, objects.get
    from .apps_catalog import FIELDS as APPS_FIELDS  # 1.0 S2 (apps from what is installed): apps.list, .for, .open, .default, .pin, .unpin
    from .board_model import FIELDS as BOARD_FIELDS  # 1.0 L2 (the bulletin board): board.read, board.links, board.keep
    from .voice_character import FIELDS as CHARACTER_FIELDS  # 0.8.7 C5 (her character file)
    from .assignments import FIELDS as ASSIGNMENT_FIELDS  # 1.0 K1 (assignments and the journal)
    from .relevance import FIELDS as RELEVANCE_FIELDS  # 1.0 L3 (relevance): relevance.why, .pin, .turn_down, .clear
    from .her_portrait import FIELDS as PORTRAIT_FIELDS  # 1.0 P1 (her column): her portrait, admitted
    from .machine_real import FIELDS as MACHINE_REAL_FIELDS  # 1.0 S4 (the Machine, real): machine.state
    from .depths import FIELDS as DEPTH_FIELDS  # 1.0 L4 (depths): revisions.record, revisions.list
    from .tools_registry import FIELDS as TOOLS_REGISTRY_FIELDS  # 1.0 K2 (tools and observation receipts): tools.*, windows.*
    from .office_bridge import FIELDS as OFFICE_BRIDGE_FIELDS  # 1.0 K5 (LibreOffice, from the inside): libreoffice.status, .read, .find, .prepare, .replace, .cell
    from .grants import FIELDS as GRANT_FIELDS  # 1.0 K3 (grants and HALT): grant.words, .list, .give, .revoke
    from .halt_gate import FIELDS as HALT_FIELDS  # 1.0 K3 (grants and HALT): halt.status, .press, .release
    from .utility_sandbox import FIELDS as SANDBOX_FIELDS  # 1.0 K6 (the utility sandbox): sandbox.*
    from .objective_plan import FIELDS as OBJECTIVE_PLAN_FIELDS  # 1.0 K4 (from an objective to a plan): objective.plan, objective.offer
    from .a11y_reader import FIELDS as A11Y_READER_FIELDS  # 1.0 K7 (reading other programs): accessibility.status, accessibility.read
    from .network_governed import FIELDS as WEB_FIELDS  # 1.0 K8 (the network, governed): web.*
    from .app_files import FIELDS as APP_FILES_FIELDS  # 1.0 A1 (programs by window and file): appfile.open, appfile.look, appfile.list
    from .a11y_hand import FIELDS as A11Y_HAND_FIELDS  # 1.0 K9 (her hand in other programs): program.status, .look, .find, .open, .type, .press, .save, .answer, .shown
    from .hand_door import FIELDS as HAND_DOOR_FIELDS  # 1.0 F1 (the door's mechanics): hand.door, hand.door.continue, hand.door.stop
    from .quick_model import FIELDS as QUICK_MODEL_FIELDS  # 1.0 M2 (a quick model beside hers): brain.quick.status, .use, .stop, .split
    from .home_pages import FIELDS as HOME_PAGES_FIELDS  # 1.0 K10 (her reach in Home, finished): file.pages
    from .home_plan import FIELDS as HOME_PLAN_FIELDS  # 1.0 K10 (her reach in Home, finished): grant.give.set
    from .windows_hand import FIELDS as WINDOWS_HAND_FIELDS  # 1.1 W1 (a Windows hand's keys): files.delete_for_good
    from .bulk_files import FIELDS as BULK_FILES_FIELDS  # 1.0 L6c (bulk files): files.batch_plan, files.batch, files.batch_undo, files.batches
    from .stac_words import FIELDS as WORD_FIELDS
    from .agent_operations import FIELDS
    from .hardware_proof import FIELDS as PROOF_FIELDS
    from .project_guidance import FIELDS as GUIDANCE_FIELDS
    from .baseline_repair import FIELDS as REPAIR_FIELDS
    from .hardware_coverage import FIELDS as COVERAGE_FIELDS
    from .console_simulation import FIELDS as SIMULATION_FIELDS
    from .boot_loading import FIELDS as BOOT_FIELDS
    from .firmware_tools import FIELDS as FIRMWARE_FIELDS
    from .engineering_register import FIELDS as REGISTER_FIELDS
    from .vendor_adapter import FIELDS as VENDOR_FIELDS
    from .orange_book import FIELDS as BOOK_FIELDS
    from .database_rom import FIELDS as RECORDS_FIELDS
    from .brain_link import FIELDS as LINK_FIELDS
    from .ux_services import FIELDS as UX_FIELDS
    from .register_proposals import FIELDS as PROPOSAL_FIELDS

    from .console_services import FIELDS as CONSOLE_FIELDS
    from .clip_external import FIELDS as EXTERNAL_FIELDS
    from .remote_sessions import FIELDS as REMOTE_FIELDS
    from .clip_workshop import FIELDS as WORKSHOP_FIELDS
    from .desktop_services import FIELDS as DESKTOP_FIELDS
    from .workspace_services import FIELDS as SELECTION_FIELDS
    from .native_projects import FIELDS as NATIVE_FIELDS

    fields = {
        **EXCHANGE_FIELDS, **RELEASE_FIELDS, **DEPLOY_FIELDS,
        **CONTINUING_FIELDS,
        **WORKER_FIELDS,
        **OFFICE_FIELDS,
        **NOTEBOOK_FIELDS,
        **NOTES_FIELDS,
        **PACKAGE_FIELDS,
        **ORGANIZER_FIELDS,
        **TRAIL_FIELDS,
        **WINDOW_FIELDS,
        **OBJECT_FIELDS,
        **ADDRESS_FIELDS,
        **MATRIX_FIELDS,
        **RECEIVING_FIELDS,
        **INVESTIGATION_LOOP_FIELDS,
        **AGENDA_FIELDS,
        **JOB_PRIORITY_FIELDS,
        **PROJECT_DESK_FIELDS,
        **PROBLEM_FIELDS,
        **MATH_FIELDS,
        **LAB_FIELDS,
        **ADAPTIVE_FIELDS,
        **JOINED_FIELDS, **ARTIFACT_FIELDS, **METHOD_FIELDS, **NATIVE_SESSION_FIELDS,
        **SCHEDULE_FIELDS,
        **MATH_ANSWER_FIELDS, **TOLERANCE_FIELDS, **MONEY_FIELDS, **DATES_FIELDS,
        **GOAL_FIELDS,  # 0.8.6 S1: goals over data
        **MIND_REASON_FIELDS, **YOUR_WORD_FIELDS,  # 0.8.6 S3: her reasons and your word
        **READING_FIELDS,  # 0.8.6 S4: her dictionary (requests.read)
        **TURN_FIELDS,  # 0.8.7 E0 (the turn contract)
        **QUOTE_FIELDS, **RULE_FIELDS,  # 0.8.6 S6: pinned quotes and rule cards
        **EITHER_WAY_FIELDS, **SETTLE_FIELDS,  # 0.8.6 S5: either way and what would settle it
        **CHANGE_CARD_FIELDS, **PLACE_FIELDS,  # 0.8.6 if there is room, items 1 and 2: what this change did; where does my desk say it
        **PHRASE_FIELDS, **PAGE_CHECK_FIELDS,  # 0.8.6 S7: the phrasebook and the page check
        **REASON_FIELDS,
        **SLATE_CONTEXT_FIELDS,
        **SLATE_REASONING_FIELDS,
        **IMPORT_PROFILE_FIELDS,
        **CHANGE_SET_FIELDS,
        **EDIT_MODEL_FIELDS,
        **FILES_FIELDS,
        **COPIES_FIELDS,
        **HOST_SUPPORT_FIELDS,
        **PILL_FIELDS,
        **CONFINE_FIELDS,
        **VIEWER_FIELDS,
        **CATALOG_FIELDS,
        **ATLAS_FIELDS,
        **ALGORITHM_FIELDS,
        **DISCOVERY_FIELDS,
        **INVESTIGATION_FIELDS,
        **PACKET_FIELDS,
        **MEMORY_FIELDS,
        **RESEARCH_FIELDS,
        **KNOWLEDGE_FIELDS,
        **STUDY_FIELDS,
        **STAC_FIELDS,
        **REFERENCE_FIELDS,
        **INTAKE_FIELDS,
        **LANGUAGE_FIELDS,
        **BRAIN_FIELDS,
        **AWARENESS_FIELDS,
        **STACY_FIELDS,
        **CAD_FIELDS,
        **KIBOT_FIELDS,
        **SPICE_FIELDS,
        **YOSYS_FIELDS,
        **PNR_FIELDS,
        **HDL_FIELDS,
        **SURFER_FIELDS,
        **LEDGER_FIELDS,
        **MACHINE_FIELDS,
        **DOCUMENT_FIELDS,
        **AGENT_FIELDS,
        **CONDITION_FIELDS,
        **HELPER_FIELDS,
        **RELATED_FIELDS,
        **BROWSE_FIELDS,
        **NETWORK_FIELDS,
        **FIELD_FIELDS,
        **DOORWAY_FIELDS,  # 0.8.7 C1 (the doorway)
        **ACCOUNT_FIELDS,  # 0.8.7 A4 (the ledger, the marks and the account)
        **PENCIL_FIELDS,  # 0.8.7 C2 (pages in pencil)
        **LIBRARY_FIELDS,  # 0.8.7 C3 (Ask the Library)
        **TABLE_FIELDS,  # 0.8.7 C6a (tables that check themselves)
        **CROSSREF_FIELDS,  # 0.8.7 C6b (cross-references)
        **EXAM_FIELDS,  # 0.8.7 A5 (the exam and the model key)
        **VOICE_COLUMN_FIELDS,  # 0.8.7 W7 (the window wiring): voice.say
        **LIVING_NAV_FIELDS,  # 1.0 L1 (one navigation state): objects.files, objects.get
        **APPS_FIELDS,  # 1.0 S2 (apps from what is installed)
        **BOARD_FIELDS,  # 1.0 L2 (the bulletin board): board.read, board.links, board.keep
        **CHARACTER_FIELDS,  # 0.8.7 C5 (her character file)
        **ASSIGNMENT_FIELDS,  # 1.0 K1 (assignments and the journal)
        **RELEVANCE_FIELDS,  # 1.0 L3 (relevance)
        **PORTRAIT_FIELDS,  # 1.0 P1 (her column): her portrait, admitted
        **MACHINE_REAL_FIELDS,  # 1.0 S4 (the Machine, real): machine.state
        **DEPTH_FIELDS,  # 1.0 L4 (depths): revisions.record, revisions.list
        **TOOLS_REGISTRY_FIELDS,  # 1.0 K2 (tools and observation receipts): tools.*, windows.*
        **OFFICE_BRIDGE_FIELDS,  # 1.0 K5 (LibreOffice, from the inside): libreoffice.status, .read, .find, .prepare, .replace, .cell
        **GRANT_FIELDS,  # 1.0 K3 (grants and HALT): grant.words, .list, .give, .revoke
        **HALT_FIELDS,  # 1.0 K3 (grants and HALT): halt.status, .press, .release
        **SANDBOX_FIELDS,  # 1.0 K6 (the utility sandbox): sandbox.*
        **OBJECTIVE_PLAN_FIELDS,  # 1.0 K4 (from an objective to a plan): objective.plan, objective.offer
        **A11Y_READER_FIELDS,  # 1.0 K7 (reading other programs): accessibility.status, accessibility.read
        **WEB_FIELDS,  # 1.0 K8 (the network, governed): web.*
        **APP_FILES_FIELDS,  # 1.0 A1 (programs by window and file): appfile.open, appfile.look, appfile.list
        **A11Y_HAND_FIELDS,  # 1.0 K9 (her hand in other programs): program.status, .look, .find, .open, .type, .press, .save, .answer, .shown
        **HAND_DOOR_FIELDS,  # 1.0 F1 (the door's mechanics): hand.door, hand.door.continue, hand.door.stop
        **QUICK_MODEL_FIELDS,  # 1.0 M2 (a quick model beside hers): brain.quick.status, .use, .stop, .split
        **HOME_PAGES_FIELDS,  # 1.0 K10 (her reach in Home, finished): file.pages
        **HOME_PLAN_FIELDS,  # 1.0 K10 (her reach in Home, finished): grant.give.set
        **WINDOWS_HAND_FIELDS,  # 1.1 W1 (a Windows hand's keys): files.delete_for_good
        **BULK_FILES_FIELDS,  # 1.0 L6c (bulk files): files.batch_plan, files.batch, files.batch_undo, files.batches
        **WORD_FIELDS,
        **{op: service.FIELDS[op] for op, service in PROGRAM_HANDLERS.items()},
        **NATIVE_FIELDS,
        **SELECTION_FIELDS,
        **DESKTOP_FIELDS,
        **WORKSHOP_FIELDS,
        **EXTERNAL_FIELDS,
        **REMOTE_FIELDS,
        **CONSOLE_FIELDS,
        **PROPOSAL_FIELDS,
        **LINK_FIELDS,
        **UX_FIELDS,
        **RECORDS_FIELDS,
        **REGISTER_FIELDS,
        **VENDOR_FIELDS,
        **BOOK_FIELDS,
        **BOOT_FIELDS,
        **FIRMWARE_FIELDS,
        **SIMULATION_FIELDS,
        **COVERAGE_FIELDS,
        **FIELDS,
        **PROOF_FIELDS,
        **GUIDANCE_FIELDS,
        **REPAIR_FIELDS,
        "clip.submit": (
            {
                "request_key": {"type": "string", "minLength": 1, "maxLength": 128},
                "goal": {"type": "string"},
                "paths": {"type": "array", "items": {"type": "string"}},
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 3},
                "max_runtime": {"type": "integer", "minimum": 10, "maximum": 600},
                "provider": {"type": "string", "enum": ["gemini", "deterministic"]},
                "max_provider_calls": {"type": "integer", "minimum": 0, "maximum": 3},
                "test_tool": {"type": "string"},
                "share_source": {"type": "boolean"},
                "proposals": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "object"}},
                },
            },
            ["goal", "paths"],
        ),
        "files.read": ({"path": {"type": "string"}}, ["path"]),
        "files.search": (
            {
                "query": {"type": "string", "minLength": 1, "maxLength": 200},
                "prefix": {"type": "string"},
            },
            ["query"],
        ),
        "candidates.create": (
            {
                "goal": {"type": "string"},
                "paths": {"type": "array", "items": {"type": "string"}},
                "required_tools": {"type": "array", "items": {"type": "string"}},
            },
            ["goal", "paths"],
        ),
        "candidates.patch": (
            {
                "id": {"type": "string"},
                "path": {"type": "string"},
                "sha256": {"type": "string"},
                "content": {"type": "string"},
            },
            ["id", "path", "sha256", "content"],
        ),
        "jobs.submit": (
            {
                "office": OFFICE_OPTIONS,
                "calculation": MATH_OPTIONS,
                "lab": LAB_OPTIONS,
                "investigation": INVESTIGATION_OPTIONS,
                "packet": PACKET_OPTIONS,
                "references": REFERENCE_OPTIONS,
                "knowledge": KNOWLEDGE_OPTIONS,
                "study": STUDY_OPTIONS,
                "intake": INTAKE_OPTIONS,
                "brain": BRAIN_OPTIONS,
                "project": {"type":"string","pattern":"^[a-z][a-z0-9_]{0,31}$","maxLength":32},
                "tool": {"type": "string"},
                "candidate": {"type": "string"},
                "request_key": {"type": "string"},
                "timeout": {"type": "number", "minimum": 1, "maximum": 600},
                "goal": {"type": "string"},
                "isolation": {"type": "string", "enum": ["debian-workshop-v1"]},
            },
            ["tool"],
        ),
    }
    result = {}
    for op in CAPABILITIES:
        props, required = fields.get(
            op,
            ({"id": {"type": "string"}}, ["id"])
            if op.endswith(
                (
                    ".get",
                    ".read",
                    ".diff",
                    ".review",
                    ".reject",
                    ".accept",
                    ".rollback",
                    ".cancel",
                    ".pause",
                    ".resume",
                    ".authorize_execution",
                    ".authorize",
                    ".stage",
                )
            )
            else ({}, []),
        )
        result[op] = {
            "type": "object",
            "properties": props,
            "required": required,
            "additionalProperties": False,
        }
    return result


def mcp(kernel, principal, incoming=None, outgoing=None):
    incoming = incoming or sys.stdin
    outgoing = outgoing or sys.stdout
    initialized = False
    for line in incoming:
        request = {}
        try:
            if len(line) > 1200000:
                raise ValueError("Message exceeds 1.2 MB")
            request = json.loads(line)
            if (
                not isinstance(request, dict)
                or request.get("jsonrpc") != "2.0"
                or not isinstance(request.get("method"), str)
            ):
                raise ValueError("Expected JSON-RPC object with string method")
            if not isinstance(request.get("params", {}), dict):
                raise ValueError("Parameters must be an object")
            if "id" not in request:
                continue
            method = request["method"]
            rid = request.get("id")
            if method == "initialize":
                initialized = True
                result = {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "arc-ledger", "version": __import__("workbench", fromlist=["VERSION"]).VERSION},
                }
            elif method.startswith("notifications/"):
                continue
            elif not initialized:
                raise ValueError("Initialize before tool use")
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": op.replace(".", "_"),
                            "description": op
                            + " · "
                            + scope
                            + " scope · kernel schema v1",
                            "inputSchema": schemas()[op],
                        }
                        for op, scope in CAPABILITIES.items()
                        if scope in principal.scopes
                    ]
                }
            elif method == "tools/call":
                args = request.get("params", {})
                names = {op.replace(".", "_"): op for op in CAPABILITIES}
                if not isinstance(args.get("name"), str):
                    raise ValueError("Tool name must be a string")
                op = names.get(args.get("name"))
                envelope = kernel.dispatch(op, args.get("arguments", {}), principal)
                result = {
                    "content": [{"type": "text", "text": json.dumps(envelope)}],
                    "isError": not envelope["ok"],
                }
            else:
                raise ValueError("Method not found")
            response = {"jsonrpc": "2.0", "id": rid, "result": result}
        except (ValueError, KeyError, TypeError) as exc:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32602, "message": str(exc)},
            }
        outgoing.write(json.dumps(response) + "\n")
        outgoing.flush()


def call_parameters(params=None,params_file=None):
    """Read explicit JSON objects without shell limits or executable payloads."""
    from sdk.cli.arc1cli.host_ipc import MAX_REQUEST
    from .record_io import strict_json
    if params_file is None:raw=('{}' if params is None else params).encode('utf-8')
    elif str(params_file)=='-':raw=sys.stdin.buffer.read(MAX_REQUEST+1)
    else:
        fd=os.open(params_file,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_REQUEST:raise ValueError('Parameters require a bounded regular JSON file')
            with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(MAX_REQUEST+1)
        finally:os.close(fd)
    if len(raw)>MAX_REQUEST:raise ValueError('JSON parameters exceed the local transport limit')
    value=strict_json(raw)
    if not isinstance(value,dict):raise ValueError('JSON parameters must be an object')
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=None
    )
    parser.add_argument("--identity", default="local-client")
    parser.add_argument("--repair-reviewer", action="store_true", help="Locally delegate read/attest only; no edits, execution or acceptance")
    parser.add_argument(
        "--allow-candidates",
        action="store_true",
        help="Grant isolated candidate writes; not acceptance",
    )
    parser.add_argument(
        "--operator",
        action="store_true",
        help="Local OS owner approval authority; never pass to external agents",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    call = sub.add_parser("call")
    call.add_argument("operation")
    parameters=call.add_mutually_exclusive_group()
    parameters.add_argument("--params", default=None,help='Inline JSON object')
    parameters.add_argument("--params-file",type=Path,help='JSON object from a regular file, or - for stdin')
    sub.add_parser("mcp")
    tail = sub.add_parser('tail', help='Read the shared activity stream')
    tail.add_argument('--follow', action='store_true')
    tail.add_argument('--lines', type=int, default=20)
    sub.add_parser("recover")
    apply = sub.add_parser("apply-update")
    apply.add_argument("id")
    worker = sub.add_parser("worker")
    worker.add_argument("id")
    remote = sub.add_parser("remote")
    remote.add_argument("--port", type=int, default=8765)
    remote.add_argument("--origin", default="http://localhost:8765")
    remote.add_argument("--allow-approvals", action="store_true")
    remote.add_argument("--profile", choices=("view", "develop", "owner"), default="develop")
    remote.add_argument("--bind", default="127.0.0.1", help="Explicit owner interface; non-loopback requires direct TLS")
    remote.add_argument("--cert", type=Path, help="Owner TLS certificate chain PEM")
    remote.add_argument("--key", type=Path, help="Private TLS key PEM (keep outside project)")
    args = parser.parse_args()
    if args.root is None:
        from .locations import default_root
        args.root = default_root()
    if args.command=='call':
        try:parameters=call_parameters(args.params,args.params_file)
        except (ValueError,OSError,RecursionError) as exc:parser.error(str(exc))
    if args.repair_reviewer and (args.operator or args.allow_candidates):
        parser.error("Repair review role cannot be combined with operator or candidate authority")
    # A claimed job is an existing Kernel worker, never another front-end
    # coordinator. All user CLI/MCP operations attach to the shared host.
    if args.command == "worker":
        from .engineering_kernel import Kernel
        k = Kernel(args.root)
    else:
        k = engineering(args.root)
    principal = (
        operator(args.identity)
        if args.operator
        else Principal(
            args.identity,
            frozenset(
                {"read", "execute", "candidate"}
                if args.allow_candidates
                else {"read", "execute"}
            ),
        )
    )
    if args.repair_reviewer:
        principal = Principal(args.identity, frozenset({"read", "repair.review"}))
    if args.command == "worker":
        from .operation_priority import apply_self
        if k.record('jobs',args.id).get('cpu_nice') is None:apply_self(k.root)
        k.run_job(args.id)
        return 0
    if args.command == "mcp":
        mcp(k, principal)
        return 0
    if args.command == 'tail':
        import time
        from .activity import stream
        cursor=''
        try:
            while True:
                result=stream(k.root,after=cursor,limit=max(1,min(200,args.lines if not cursor else 200)))
                if result['gap']:print(json.dumps({'gap':True,'message':'Previous cursor is outside retained history'}),flush=True)
                for event in result['events']:print(json.dumps(event),flush=True)
                cursor=result['cursor'] or ''
                if not args.follow:return 0
                time.sleep(.5)
        except KeyboardInterrupt:return 0
    if args.command == "recover":
        result = k.dispatch("jobs.recover", {}, principal)
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    if args.command == "apply-update":
        if not args.operator:
            parser.error("Applying a staged update requires the local operator")
        from .update_service import apply_staged
        if getattr(k, 'is_host_client', False):
            from .host_cli import offline_update
            result = offline_update(k, args.id, principal)
        else: result = apply_staged(k, args.id, principal)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "remote":
        if not args.operator:
            parser.error(
                "Remote pairing must be enabled explicitly by the local operator"
            )
        if getattr(k, 'is_host_client', False):
            result = k.rpc('remote_start', {'port':args.port, 'origin':args.origin,
                'bind':args.bind, 'cert':str(args.cert) if args.cert else None,
                'key':str(args.key) if args.key else None,
                'profile':'owner' if args.allow_approvals else args.profile}, principal)
            print('One-time pairing code (5 minutes): ' + result['pair_code'], flush=True)
            print('The shared background service keeps serving after this client exits.', flush=True)
            return 0
        from .remote_service import serve

        serve(k, args.port, args.origin, args.allow_approvals, bind=args.bind,
              cert=args.cert, key=args.key, profile=args.profile)
        return 0
    result = k.dispatch(args.operation, parameters, principal)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
