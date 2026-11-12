"""Source-bound Ledger self knowledge, capability health and portable seed.

The Kernel operations in this module are read-only. Seed authoring is a separate
local maintenance command. It neither grants tools nor executes source files.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import tempfile
import time
from zipfile import ZipFile, ZIP_DEFLATED

from . import stacy_contracts as contracts
from . import locations

SEED_DIR = 'project/stacy_seed/current'
SCHEMA = 'arc.stacy-ledger-seed/1'
TEXT = {'type': 'string', 'maxLength': 180}
VIEW_ARGS = {'view': {'type': 'string', 'enum': list(contracts.VIEWS)}, 'selection': TEXT}
READERS = ('ledger.settings', 'ledger.commands', 'records.status', 'knowledge.status', 'vendor.status',
           'hdl.inspect', 'boot.inspect', 'hardware.proof.inspect')
FIELDS = {
    'stacy.foundation': ({}, []),
    'stacy.capabilities': ({'query': TEXT}, []),
    'stacy.seed.status': ({}, []),
    'stacy.seed.search': ({'query': TEXT, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 30}}, []),
    'stacy.seed.record': ({'id': TEXT}, ['id']),
    'stacy.context': (VIEW_ARGS, ['view']),
    'stacy.explain': (VIEW_ARGS, ['view']),
    'stacy.reader': ({'operation': {'type': 'string', 'enum': list(READERS)}}, ['operation']),
}
SCOPES = {operation: 'read' for operation in FIELDS}

# The seed binds Graphite's code, guides, and entry points. Its explicit source
# list keeps workspace data, credentials, model files, and vendor sources outside
# the seed. Rebuild it with tools/package_graphite.py after editing bound files.
SEED_FILES = (
    'workbench/program_mail.py', 'workbench/program_build.py',
    'workbench/program_transfer.py', 'workbench/program_cartridge.py',
    'workbench/program_vector.py', 'workbench/program_media.py', 'workbench/program_freecad.py',
    'workbench/program_print.py', 'workbench/program_delivery.py',
    'workbench/program_inquiry.py',
    'workbench/program_rooms_qt.py',
    'workbench/boss_theme.py', 'workbench/boss_qt.py', 'workbench/work_location.py',
    'workbench/command_context.py', 'workbench/chain_workbench_qt.py', 'branding/boss/night-signal.svg',
    'workbench/inference_hardware.py', 'docs/THINKPAD_VULKAN_P05.md',
    'workbench/resource_control.py', 'docs/TRAFFIC_COP_P06.md',
    'workbench/intelligent_data.py', 'docs/INTELLIGENT_DATA_P07.md',
    'workbench/datasheet_work.py', 'workbench/datasheet_qt.py', 'docs/BOSS_HALFWAY_P10.md',
    'workbench/sheet_workbench_qt.py', 'docs/BOSS_WORKSHEET_VISUAL_REVIEW.md',
    'docs/BOSS_IMPLEMENTATION_PLAN.md', 'docs/BOSS_IMPLEMENTATION_PLAN.json', 'docs/BOSS_M1.md',
    'HATCH_CHECK.sh', 'INSTALL_DEBIAN.sh', 'INSTALL_LEDGER.sh', 'INSTALL_LS.py', 'LS_XSESSION.sh', 'README.md',
    'RECORD_OF_DIRECTIONS.md', 'START_MINIMAL_DEBIAN.sh', 'prepare_release.py', 'requirements-experiments.txt',
    'requirements-math.txt', 'requirements-office.txt',
    'branding/fonts/NOTICE.md',
    'branding/hatch/hatch-16-disabled.svg', 'branding/hatch/hatch-16-hover.svg', 'branding/hatch/hatch-16-normal.svg',
    'branding/hatch/hatch-16-pressed.svg', 'branding/hatch/hatch-24-disabled.svg', 'branding/hatch/hatch-24-hover.svg',
    'branding/hatch/hatch-24-normal.svg', 'branding/hatch/hatch-24-pressed.svg', 'branding/hatch/hatch-32-disabled.svg',
    'branding/hatch/hatch-32-hover.svg', 'branding/hatch/hatch-32-normal.svg', 'branding/hatch/hatch-32-pressed.svg',
    'branding/hatch/hatch-48-disabled.svg', 'branding/hatch/hatch-48-hover.svg', 'branding/hatch/hatch-48-normal.svg',
    'branding/hatch/hatch-48-pressed.svg',
    'branding/stacy/character.json',
    'docs/AGENT_01.md', 'docs/AGENT_02.md', 'docs/CONTINUE_01.md', 'docs/DAILY_GUIDE.md', 'docs/DECISION_REGISTER.json',
    'docs/DOCUMENTS_01.md', 'docs/FILES_ABOUT_01.md', 'docs/FINDER_01.md', 'docs/GRAPHITE_01.md', 'docs/HATCH_ACTIONS_01.md',
    'docs/HATCH_AGENT_01.md', 'docs/HATCH_AGENT_02.md', 'docs/HATCH_ALGORITHM_ATLAS.md', 'docs/HATCH_CABINET_01.md',
    'docs/HATCH_DISCOVERY_01.md', 'docs/HATCH_EXPLORE_01.md', 'docs/HATCH_INTEGRATION_01.md', 'docs/HATCH_MEMORY_01.md',
    'docs/HATCH_MODEL_01.md', 'docs/HATCH_NAVIGATION_01.md', 'docs/HATCH_OPERATIONS_01.md', 'docs/HATCH_PRESENTATION_01.md',
    'docs/HATCH_READINESS.md', 'docs/HATCH_RETURN_01.md', 'docs/HATCH_SERVICE_01.md', 'docs/HATCH_SETTINGS_01.md',
    'docs/HATCH_SETTINGS_02.md', 'docs/HATCH_SETTINGS_03.md', 'docs/HATCH_TOOL_ATLAS.md', 'docs/HATCH_UI_REVIEW_01.md',
    'docs/HATCH_WORKSHOP_01.md', 'docs/IMPLEMENTATION_MAP.md', 'docs/INTEGRATED_I01.md', 'docs/INTEGRATED_I02.md',
    'docs/INTEGRATED_I03.md', 'docs/INTEGRATED_I04.md', 'docs/LEDGER_SLATE_COMPLETE_PROJECT_SPEC_01.md',
    'docs/MACHINE_VIEW_01.md', 'docs/MINIMAL_DEBIAN_INSTALL_01.md', 'docs/MODEL_TRIAL_01.md', 'docs/MODEL_TRIAL_02.md',
    'docs/MODEL_TURN_01.md', 'docs/NAVIGATOR_REVIEW_01.md', 'docs/SETTINGS_INVENTORY_07.md', 'docs/STAGE1.md', 'docs/STAGE2.md',
    'docs/STAGE3.md', 'docs/STAGE4.md', 'docs/STAGE5.md', 'docs/STAGE6.md', 'docs/UI_MINI_PASS.md',
    'docs/assistant_identity.json', 'docs/milestones.json',
    'pillkit/state.py', 'pillkit/tls_link.py',
    'runtimes/llama.cpp/b11669/runtime.json',
    'runtimes/office-uno/runtime.json',
    'runtimes/python-wasi/runtime.json',
    'sdk/cli/arc1cli/capability_catalog.py', 'sdk/cli/arc1cli/command_bar.py', 'sdk/cli/arc1cli/concern_catalog.py',
    'sdk/cli/arc1cli/document_extract.py', 'sdk/cli/arc1cli/engineering_cases.py', 'sdk/cli/arc1cli/engineering_map.py',
    'sdk/cli/arc1cli/engineering_packets.py', 'sdk/cli/arc1cli/evidence_contracts.py', 'sdk/cli/arc1cli/gguf_inspect.py',
    'sdk/cli/arc1cli/host_cpu.py', 'sdk/cli/arc1cli/host_ipc.py', 'sdk/cli/arc1cli/intake_files.py',
    'sdk/cli/arc1cli/intake_profiles.py', 'sdk/cli/arc1cli/kicad_sexpr.py', 'sdk/cli/arc1cli/knowledge_sources.py',
    'sdk/cli/arc1cli/learning_contracts.py', 'sdk/cli/arc1cli/notebook.py', 'sdk/cli/arc1cli/notes_exchange.py',
    'sdk/cli/arc1cli/object_context.py', 'sdk/cli/arc1cli/office_documents.py', 'sdk/cli/arc1cli/office_tables.py',
    'sdk/cli/arc1cli/office_work.py', 'sdk/cli/arc1cli/package_transport.py', 'sdk/cli/arc1cli/pdf_evidence.py',
    'sdk/cli/arc1cli/record_store.py', 'sdk/cli/arc1cli/record_visibility.py', 'sdk/cli/arc1cli/reference_extract.py',
    'sdk/cli/arc1cli/research_packets.py', 'sdk/cli/arc1cli/slate_attention.py', 'sdk/cli/arc1cli/slate_windows.py',
    'sdk/cli/arc1cli/sprite_player.py', 'sdk/cli/arc1cli/study_contracts.py', 'sdk/cli/arc1cli/typed_pipeline.py',
    'sdk/cli/arc1cli/ui_assets.py', 'sdk/cli/arc1cli/window_views.py', 'sdk/cli/arc1cli/work_organizer.py',
    'sdk/cli/arc1cli/work_trail.py', 'sdk/cli/arc1cli/workbench_view.py',
    'tools/hatch_check.py',
    'workbench/LedgerOffice.java', 'workbench/activity.py', 'workbench/adaptive_checks.py', 'workbench/adaptive_contract.py',
    'workbench/adaptive_qt.py', 'workbench/adaptive_work.py', 'workbench/agenda.py', 'workbench/agenda_qt.py',
    'workbench/agent_loop.py', 'workbench/agent_operations.py', 'workbench/agent_profiles.py', 'workbench/agent_qt.py',
    'workbench/algorithm_atlas.py', 'workbench/algorithm_atlas_qt.py', 'workbench/algorithm_corpus.json',
    'workbench/arc_desktop.py', 'workbench/arcfairy_qt.py', 'workbench/baseline.py', 'workbench/baseline_repair.py',
    'workbench/bird_presence.py', 'workbench/board_runtime.py', 'workbench/boot_loading.py', 'workbench/brain_link.py',
    'workbench/brain_qt.py', 'workbench/brain_runtime.py', 'workbench/brain_worker.py', 'workbench/browse.py',
    'workbench/cabinet.py', 'workbench/cabinet_actions.py', 'workbench/cabinet_actions_qt.py', 'workbench/cabinet_qt.py',
    'workbench/calculator_qt.py', 'workbench/capability_catalog.py', 'workbench/catalog_settings.py', 'workbench/cell_edits.py',
    'workbench/chain_menu.py', 'workbench/change_sets.py', 'workbench/change_sets_qt.py', 'workbench/clip.py',
    'workbench/clip_external.py', 'workbench/clip_tasks_tab.py', 'workbench/clip_workshop.py', 'workbench/clip_workspace.py',
    'workbench/clock_lab.py', 'workbench/concern_qt.py', 'workbench/concern_tree.py', 'workbench/conditions.py',
    'workbench/config_lock.py', 'workbench/console_qt.py', 'workbench/console_services.py', 'workbench/console_simulation.py',
    'workbench/continuing_checks.py', 'workbench/continuing_work.py', 'workbench/continuing_work_qt.py',
    'workbench/control_qt.py', 'workbench/database_checks.py', 'workbench/database_guard.py', 'workbench/database_rom.py',
    'workbench/deployment.py', 'workbench/deployment_checks.py', 'workbench/deployment_qt.py', 'workbench/desktop_header_qt.py',
    'workbench/desktop_services.py', 'workbench/development_tabs.py', 'workbench/discovery_ir.py', 'workbench/discovery_qt.py',
    'workbench/discovery_service.py', 'workbench/doctor.py', 'workbench/document_qt.py', 'workbench/documents.py',
    'workbench/edit_checks.py', 'workbench/edit_model.py', 'workbench/edit_storage.py', 'workbench/empty_workspace_qt.py',
    'workbench/engineering_cli.py', 'workbench/engineering_kernel.py', 'workbench/engineering_map.py',
    'workbench/engineering_map_qt.py', 'workbench/engineering_register.py', 'workbench/engineering_tabs.py',
    'workbench/evidence_compiler.py', 'workbench/evidence_compiler_qt.py', 'workbench/exchange.py',
    'workbench/experiment_runtime.py', 'workbench/explore.py', 'workbench/explore_qt.py', 'workbench/file_delivery.py',
    'workbench/files_qt.py', 'workbench/finder_qt.py', 'workbench/firmware_tools.py', 'workbench/genesis_tab.py',
    'workbench/graphite_brand.py', 'workbench/hardware_coverage.py', 'workbench/hardware_nav.py',
    'workbench/hardware_overview.py', 'workbench/hardware_proof.py', 'workbench/hardware_settings_qt.py',
    'workbench/hatch_qt.py', 'workbench/hatch_readiness.py', 'workbench/hdl_qt.py', 'workbench/hdl_tools.py',
    'workbench/helpers.py', 'workbench/host_cli.py', 'workbench/host_client.py', 'workbench/host_observations.py',
    'workbench/host_qt.py', 'workbench/host_service.py', 'workbench/import_profiles.py', 'workbench/instruments_qt.py',
    'workbench/intake_qt.py', 'workbench/intake_service.py', 'workbench/investigation_service.py',
    'workbench/investigations_qt.py', 'workbench/job_priority.py', 'workbench/joined_qt.py', 'workbench/kibot_qt.py',
    'workbench/kibot_tools.py', 'workbench/kicad_qt.py', 'workbench/kicad_tools.py', 'workbench/knowledge_qt.py',
    'workbench/knowledge_service.py', 'workbench/lab_checks.py', 'workbench/lab_qt.py', 'workbench/lab_service.py',
    'workbench/launch.py', 'workbench/ledger_control.py', 'workbench/ledger_tabs.py', 'workbench/local_brain.py',
    'workbench/machine_overview.py', 'workbench/machine_qt.py', 'workbench/math_backend.py', 'workbench/math_checks.py',
    'workbench/math_model.py', 'workbench/math_office.py', 'workbench/math_service.py', 'workbench/math_units.py',
    'workbench/memory_cabinet.py', 'workbench/memory_cabinet_qt.py', 'workbench/memory_qt.py', 'workbench/memory_service.py',
    'workbench/memory_settings.py', 'workbench/menus2.py', 'workbench/model_settings.py', 'workbench/model_settings_qt.py',
    'workbench/model_turn.py', 'workbench/native_project_tab.py', 'workbench/native_projects.py', 'workbench/navigation_qt.py',
    'workbench/navigator_catalog.py', 'workbench/notebook_qt.py', 'workbench/notebook_service.py',
    'workbench/notes_exchange.py', 'workbench/notes_exchange_qt.py', 'workbench/object_context.py',
    'workbench/object_context_qt.py', 'workbench/office_building_qt.py', 'workbench/office_math_runtime.py',
    'workbench/office_qt.py', 'workbench/office_runtime.py', 'workbench/office_service.py', 'workbench/operations.py',
    'workbench/operations_qt.py', 'workbench/orange_book.py', 'workbench/organizer_qt.py', 'workbench/package_service.py',
    'workbench/pdf_qt.py', 'workbench/pdf_service.py', 'workbench/pnr_tools.py', 'workbench/presentation_preferences.py',
    'workbench/presentation_qt.py', 'workbench/problem_checks.py', 'workbench/problem_qt.py', 'workbench/problem_service.py',
    'workbench/profile_files.py', 'workbench/profile_numbers.py', 'workbench/project_context.py', 'workbench/project_desk.py',
    'workbench/project_desk_checks.py', 'workbench/project_desk_qt.py', 'workbench/project_guidance.py',
    'workbench/project_tabs.py', 'workbench/qt_app.py', 'workbench/qt_master_stop.py', 'workbench/quantities.py',
    'workbench/reading_preferences.py', 'workbench/reading_profile.py', 'workbench/reason_graph.py',
    'workbench/reason_service.py', 'workbench/record_access.py', 'workbench/records_tab.py', 'workbench/reference_qt.py',
    'workbench/reference_service.py', 'workbench/register_proposals.py', 'workbench/register_tabs.py', 'workbench/related.py',
    'workbench/release_cli.py', 'workbench/release_integrity.py', 'workbench/release_publisher.py',
    'workbench/release_updates.py', 'workbench/remote_link.py', 'workbench/remote_service.py', 'workbench/remote_sessions.py',
    'workbench/research_qt.py', 'workbench/research_service.py', 'workbench/result_surface.py', 'workbench/return_thread.py',
    'workbench/return_thread_qt.py', 'workbench/schedule_math.py', 'workbench/service_lifecycle.py',
    'workbench/service_lifecycle_qt.py', 'workbench/session.py', 'workbench/session_settings.py', 'workbench/settings_qt.py',
    'workbench/settings_registry.py', 'workbench/shell2.py', 'workbench/slate_action.py', 'workbench/slate_checks.py',
    'workbench/slate_context.py', 'workbench/slate_reasoning.py', 'workbench/slate_reasoning_qt.py',
    'workbench/slate_stream.py', 'workbench/slate_windows.py', 'workbench/slate_windows_qt.py', 'workbench/spice_tools.py',
    'workbench/stac_bridge.py', 'workbench/stacy_awareness.py', 'workbench/stacy_awareness_qt.py',
    'workbench/stacy_contracts.py', 'workbench/stacy_control.py', 'workbench/stacy_foundation.py',
    'workbench/stacy_foundation_qt.py', 'workbench/stacy_language.py', 'workbench/static_bird.py',
    'workbench/study_editions.py', 'workbench/study_qt.py', 'workbench/study_service.py', 'workbench/surfer_tools.py',
    'workbench/tail_words.py', 'workbench/text_prompts.py', 'workbench/theme2.py', 'workbench/tool_atlas.py',
    'workbench/tool_atlas_qt.py', 'workbench/tool_selection.py', 'workbench/typebar_qt.py', 'workbench/update_checks.py',
    'workbench/ux_assets.py', 'workbench/ux_gallery.py', 'workbench/ux_services.py', 'workbench/vendor_adapter.py',
    'workbench/viewer_data.py', 'workbench/window_views.py', 'workbench/window_views_qt.py', 'workbench/work_organizer.py',
    'workbench/work_scope.py', 'workbench/work_trail.py', 'workbench/work_trail_qt.py', 'workbench/worker_boundary.py',
    'workbench/worker_child.py', 'workbench/worker_tasks.py', 'workbench/workshop_tabs.py', 'workbench/workspace_backup.py',
    'workbench/workspace_qt.py', 'workbench/workspace_services.py', 'workbench/workspace_tabs.py',
    'workbench/writing_marker.py', 'workbench/yosys_tools.py',
    'workbench/remote_pwa/app.js', 'workbench/remote_pwa/deck.js', 'workbench/remote_pwa/index.html',
    'workbench/remote_pwa/sw.js',
    'workbench/stac/__init__.py', 'workbench/stac/chronicle.py', 'workbench/stac/cli.py',
    'workbench/stac/controlled_language.py', 'workbench/stac/evidence.py', 'workbench/stac/kernel_witness.py',
    'workbench/stac/knowledge.py', 'workbench/stac/language.py', 'workbench/stac/obligations.py',
    'workbench/stac/quantities.py', 'workbench/stac/redirection.py', 'workbench/stac/runtime.py', 'workbench/stac/semantics.py',
    'workbench/stac/source_facts.py', 'workbench/stac/witnesses.py',
    'workbench/view_modules/sheets.py',
)
# Notes the seed carries (carried(): a docs/ note or AGENTS.md absent from the tree). Their only working copy is the text in
# the seed's verified catalog: they left the tree before Graphite 0.1 and the seed kept them so staC still answers from them.
# Kept under the owner's rule (D35: keep what teaches how the program works, why, or what was learned); packaging recovers
# each from the catalog into a disposable copy of the tree before a rebuild (tools/package_graphite.rebuild).
CARRIED_NOTES = (
    'AGENTS.md',
    'docs/DOCX_ACCEPTANCE.md', 'docs/HDL_INTEGRATION.md', 'docs/LEDGER_CONTROL.md', 'docs/LEDGER_SLATE_CAMPAIGN.md',
    'docs/MILESTONES.md', 'docs/NATIVE_CAPABILITY_ROADMAP.md', 'docs/OFFICE_CLI.md', 'docs/SLATE_GROUNDWORK5.md',
    'docs/SLATE_N1.md', 'docs/SLATE_N3.md', 'docs/SLATE_PASS_13.md', 'docs/SLATE_PASS_14.md', 'docs/SLATE_PASS_15.md',
    'docs/SLATE_PASS_16.md', 'docs/SLATE_PASS_17.md', 'docs/SLATE_PASS_18.md', 'docs/SLATE_PASS_19.md', 'docs/SLATE_PASS_20.md',
    'docs/SLATE_RECORD_SHARING.md', 'docs/SLATE_SW001.md', 'docs/SLATE_SW002.md', 'docs/SLATE_WINDOWS_CAMPAIGN.md',
    'docs/STACY_FOUNDATION.md', 'docs/STACY_PASS_10.md', 'docs/STACY_PASS_11.md', 'docs/STACY_PASS_12.md',
    'docs/STACY_PASS_2.md', 'docs/STACY_PASS_3.md', 'docs/STACY_PASS_4.md', 'docs/STACY_PASS_5.md', 'docs/STACY_PASS_6.md',
    'docs/STACY_PASS_6_LEARNING_PLAN.md', 'docs/STACY_PASS_7.md', 'docs/STACY_PASS_8.md', 'docs/STACY_PASS_9.md',
    'docs/STAC_CONSTRUCTION_PASS006.md', 'docs/STAC_HANDOFF_ALIGNMENT.md', 'docs/UNIFIED_GROUNDWORK_ADDENDUM.txt',
    'docs/UNIFIED_N3_ADDENDUM.txt', 'docs/UNIFIED_P17_ADDENDUM.txt',
)
SEED_INPUTS = tuple(sorted(set(SEED_FILES) | set(CARRIED_NOTES)))
OWNER_INTENT = (
    'Graphite studies itself first: its purpose, windows, commands, settings and evidence. '
    'It explains selected program data and uses registered capabilities through the shared Kernel. '
    'Custom reference libraries augment independently replaceable model weights. '
    'Durable awareness, quarantine admission into a clean V1 project, context checkpoints, '
    'The current expanded campaign covers passes 13 through 37 and the approved window campaign. '
    'Object Glass binds selected identities, sources, evidence, gaps and read actions. '
    'Retain evidence-backed ARC-1 enhancement leads discovered by software tests for separate review. '
    'Capability prerequisites are inspected separately from permission and qualification. '
    'Study, recovery and external reasoning still require their declared host and real-provider qualification.'
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def project_file(root, name, limit=4_000_000, program_file=True):
    # Seed inputs, catalog sources and pins are program files; project checks pass program_file=False.
    root = locations.program(root) if program_file else Path(root).resolve()
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Expected an allowed project-relative path')
    parts = PurePosixPath(name).parts
    if not parts or name.startswith('/') or any(p in ('..', '.') or p.startswith('.') for p in parts):
        raise ValueError('Source path is outside the project')
    path = root.joinpath(*parts)
    if any(p.is_symlink() for p in [path, *path.parents]) or not path.resolve().is_relative_to(root):
        raise ValueError('Linked or escaping source path')
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Source is missing or exceeds its bound: ' + name)
    return path


def source_ref(root, name):
    path = project_file(root, name)
    return {'id': 'source:' + name, 'path': name, 'sha256': sha(path.read_bytes()),
            'basis': 'EXACT_SOURCE_BYTES', 'qualification': 'SOURCE_PRESENT'}


def prerequisites(root, operation):
    if operation == 'boot.inspect':
        from .boot_loading import FILES
        required = [str(p) for p in FILES]
    elif operation == 'hardware.proof.inspect':
        from .hardware_review import BASE
        required = [(BASE / 'closure_p8/P8_VERIFICATION.json').as_posix()]
    else:
        required = []
    missing = []
    for name in required:
        try:
            project_file(root, name, 32_000_000, program_file=False)
        except (ValueError, OSError):
            missing.append(name)
    return missing


def reader(kernel, operation, principal):
    if operation not in READERS:
        raise ValueError('Reader is outside the foundation allowlist')
    from .project_context import detached,requires_project,unavailable
    if detached(kernel.root) and requires_project(operation,{}):
        return {'schema':'arc.stacy-reader/1','operation':operation,'state':'PROJECT_NOT_ATTACHED',
                'result':None,'missing_inputs':[],'reason':unavailable(operation)['reason']}
    missing = prerequisites(kernel.root, operation)
    if missing:
        return {'schema': 'arc.stacy-reader/1', 'operation': operation,
                'state': 'BLOCKED_MISSING_INPUT', 'missing_inputs': missing,
                'reason': 'Required source/report is absent; restore or generate it through its approved producer.',
                'result': None}
    response = kernel.dispatch(operation, {}, principal)
    if not response['ok']:
        return {'schema': 'arc.stacy-reader/1', 'operation': operation,
                'state': 'READER_FAILED', 'missing_inputs': [], 'result': None,
                'reason': response['error']['message']}
    return {'schema': 'arc.stacy-reader/1', 'operation': operation, 'state': 'READ_COMPLETED',
            'missing_inputs': [], 'result': response['result'],
            'notice': 'A completed read does not qualify the subject or a native tool.'}


def handler_map():
    from . import engineering_kernel as ek
    handlers = {}
    for value in vars(ek).values():
        fields = getattr(value, 'FIELDS', None)
        dispatch = getattr(value, 'dispatch', None)
        module = getattr(value, '__name__', '')
        if isinstance(fields, dict) and callable(dispatch) and module.startswith('workbench.'):
            path = module.replace('.', '/') + '.py'
            for operation in fields:
                handlers[operation] = {'path': path, 'symbol': 'dispatch', 'basis': 'DECLARED_FIELDS_ROUTE'}
    # Parse the file without executing it. Literal dispatch cases provide an
    # explicit link; this does not infer arbitrary dynamic call dependencies.
    source = Path(ek.__file__).read_text(encoding='utf-8')
    kernel_class = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'Kernel')
    dispatch_node = next(n for n in kernel_class.body if isinstance(n, ast.FunctionDef) and n.name == '_dispatch')
    for node in ast.walk(dispatch_node):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == 'op':
            for rhs in node.comparators:
                values = rhs.elts if isinstance(rhs, (ast.Tuple, ast.List)) else [rhs]
                for literal in values:
                    if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                        if literal.value in ek.CAPABILITIES:
                            handlers.setdefault(literal.value, {'path': 'workbench/engineering_kernel.py',
                                                                 'symbol': 'Kernel._dispatch', 'basis': 'LITERAL_DISPATCH_CASE'})
    return handlers


def capabilities(kernel, principal, query=''):
    from .capability_catalog import by_operation
    from .engineering_kernel import CAPABILITIES, TOOLS
    from .project_context import detached, requires_project

    assessed = by_operation(kernel,principal,query)
    is_detached = detached(kernel.root)
    rows = []
    for operation, scope in sorted(CAPABILITIES.items()):
        if query.casefold() not in operation.casefold():
            continue
        current = assessed[operation]
        handler = current['handler']
        allowed = scope in principal.scopes and not (principal.mode == 'Tutor' and scope != 'read')
        missing = prerequisites(kernel.root, operation)
        if handler and current['source']['state'] != 'PRESENT':
            missing.append(handler['path'])
        project_missing = is_detached and requires_project(operation,{})
        if not handler:
            state, reason = 'HANDLER_UNRESOLVED', 'Registration is present; a handler link has not been established.'
        elif project_missing:
            state, reason = 'PROJECT_NOT_ATTACHED', 'The original project is sealed separately; reviewed project intake is required.'
        elif missing:
            state, reason = 'BLOCKED_MISSING_INPUT', 'Required source/report is missing.'
        elif not allowed:
            state, reason = 'OUTSIDE_SCOPE', 'The current principal cannot request this operation.'
        elif current['arguments']['required']:
            state, reason = 'NEEDS_ARGUMENTS', 'Supply validated arguments; runtime and operation checks still apply.'
        else:
            state, reason = 'REGISTERED', 'Handler linked; runtime and result qualification have not been inferred.'
        rows.append({'operation': operation, 'scope': scope, 'status': state, 'reason': reason,
                     'assessment': current['assessment'], 'summary': current['summary'],
                     'handler': handler, 'arguments': current['arguments'], 'missing_inputs': missing,
                     'authorized': allowed, 'qualification': 'NOT_ASSESSED_BY_FOUNDATION',
                     'runtime_state': 'NOT_CHECKED', 'basis': 'REGISTRY_AND_DECLARED_SOURCE'})
    return {'schema': 'arc.stacy-capability-health/1', 'operations': rows,
            'registered_operations': len(CAPABILITIES), 'registered_job_tools': len(TOOLS),
            'sampled_input_profiles': ['boot.inspect', 'hardware.proof.inspect'],
            'notice': 'This is source-level capability discovery, not a claim that every operation has run.'}


def carried(name):
    """A seed input whose text the seed itself carries: a written note (.md or .txt) in docs/, or AGENTS.md. Its full
    text is indexed in the seed's catalog, and the catalog is bound to the manifest by its own hash, so a runtime copy of
    Ledger may leave the note out and staC still answers from a verified seed. Program files are never carried: every
    .py, .js, .json and runtime file must be present and unchanged, or staC refuses to run."""
    return name.endswith(('.md', '.txt')) and (name.startswith('docs/') or name == 'AGENTS.md')


def _seed_paths(root):
    return locations.program(root) / SEED_DIR


def seed_status(root):
    base = _seed_paths(root)
    try:
        manifest_path = project_file(root, SEED_DIR + '/manifest.json', 150_000)
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('schema') != SCHEMA or set(manifest.get('inputs', {})) != set(SEED_INPUTS):
            raise ValueError('Seed input set or schema differs from the supported contract')
        if manifest.get('seed_id') != sha(canonical(manifest['inputs'])):
            raise ValueError('Seed identity differs from its declared inputs')
        if set(manifest.get('files', {})) != {'catalog.json', 'index.sqlite'}:
            raise ValueError('Unexpected seed members')
        for name, expected in manifest['files'].items():
            path = project_file(root, SEED_DIR + '/' + name, 12_000_000)
            if sha(path.read_bytes()) != expected:
                raise ValueError('Seed artifact hash mismatch: ' + name)
        changed, missing, absent = [], [], []
        for name, expected in manifest['inputs'].items():
            if carried(name) and not (locations.program(root) / name).exists():
                absent.append(name)  # left out of this copy; its text is in the verified catalog
                continue
            try:
                current = sha(project_file(root, name).read_bytes())
                if current != expected:
                    changed.append(name)  # a note that is present must still match, as before
            except (ValueError, OSError):
                missing.append(name)
        state = 'SOURCE_UNAVAILABLE' if missing else 'STALE' if changed else 'VERIFIED_SOURCE_BINDINGS'
        return {'schema': SCHEMA, 'state': state, 'seed_id': manifest['seed_id'],
                'records': manifest['records'], 'changed_sources': changed, 'missing_sources': missing, 'carried_in_seed': absent,
                'input_fingerprint_scope': 'Declared Ledger seed inputs only; not whole-project acceptance.',
                'notice': 'Integrity and source identity only. This does not establish model or physical qualification.'}
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {'schema': SCHEMA, 'state': 'NOT_GENERATED' if not base.exists() else 'INVALID',
                'records': 0, 'reason': str(exc), 'changed_sources': [], 'missing_sources': []}


def _require_seed(root):
    status = seed_status(root)
    if status['state'] != 'VERIFIED_SOURCE_BINDINGS':
        raise ValueError('Seed is ' + status['state'] + '; rebuild or restore its declared sources first')
    return status


@contextmanager
def _seed_index(root):
    path = project_file(root, SEED_DIR + '/index.sqlite', 12_000_000)
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        yield db
    finally:
        db.close()


def seed_search(root, query='', limit=12):
    status = _require_seed(root)
    if not isinstance(query, str) or len(query) > 180 or type(limit) is not int or not 1 <= limit <= 30:
        raise ValueError('Search is outside the seed query bound')
    with _seed_index(root) as db:
        terms = re.findall(r'[\w.-]+', query, re.UNICODE)[:12]
        if terms:
            match = ' OR '.join('"' + word.replace('"', '""') + '"' for word in terms)
            ids = [r[0] for r in db.execute('SELECT record_id FROM search WHERE search MATCH ? ORDER BY rank LIMIT ?', (match, limit))]
        else:
            ids = [r[0] for r in db.execute('SELECT id FROM records ORDER BY id LIMIT ?', (limit,))]
        records = [json.loads(db.execute('SELECT payload FROM records WHERE id=?', (ident,)).fetchone()[0]) for ident in ids]
    return {'schema': 'arc.stacy-seed-search/1', 'seed_id': status['seed_id'], 'query': query,
            'records': records, 'state': status['state']}


def seed_record(root, ident):
    _require_seed(root)
    if not isinstance(ident, str) or len(ident) > 180:
        raise ValueError('Invalid seed record ID')
    with _seed_index(root) as db:
        row = db.execute('SELECT payload FROM records WHERE id=?', (ident,)).fetchone()
    if row is None:
        raise ValueError('Seed record not found')
    return {'schema': 'arc.stacy-seed-record/1', 'record': json.loads(row[0]), 'state': 'VERIFIED_SOURCE_BINDINGS'}


def view_context(kernel, principal, view, selection=''):
    from . import ledger_control, hdl_tools
    if view not in contracts.VIEWS:
        raise ValueError('Unsupported foundation view')
    _require_seed(kernel.root)
    unknowns = ['Model load/generation qualification does not verify engineering answers.',
                'Durable awareness uses a commit-ordered journal; physical and owner-host qualification remain separate.']
    if view == 'settings':
        key = selection or 'reading.code_pt'
        rows = ledger_control.settings(kernel)['settings']
        row = next((r for r in rows if r['key'] == key), None)
        if row is None:
            raise ValueError('Unknown setting selection')
        data = {k: row[k] for k in ('key', 'label', 'value', 'description', 'effect')}
        data['unit'] = 'points' if key.endswith('_pt') else 'ratio' if key == 'reading.line_height' else 'setting value'
        data.update(scope=row['scope'], default=row['default'])
        data.update({k:row[k] for k in ('stored','effective','revision','scope_id','application','application_state')})
        source_names = ['workbench/ledger_control.py', 'workbench/settings_registry.py', 'workbench/settings_qt.py', 'workbench/control_qt.py', 'workbench/reading_profile.py', 'workbench/session_settings.py', 'workbench/presentation_preferences.py', 'workbench/clip.py']
        if key.startswith('favorites.') or key=='catalog.view':source_names += ['workbench/catalog_settings.py','workbench/presentation_qt.py','sdk/cli/arc1cli/command_bar.py','sdk/cli/arc1cli/concern_catalog.py','workbench/concern_qt.py']
    elif view == 'commands':
        operation = selection or 'boot.inspect'
        rows = capabilities(kernel, principal, operation)['operations']
        row = next((r for r in rows if r['operation'] == operation), None)
        if row is None:
            raise ValueError('Unknown command selection')
        data = {k: row[k] for k in ('operation', 'scope', 'status', 'reason', 'qualification')}
        data.update(arguments=row['arguments'], missing_inputs=row['missing_inputs'], authorized=row['authorized'])
        source_names = ['workbench/engineering_kernel.py', 'workbench/engineering_cli.py', 'workbench/stacy_foundation.py']
        if row['handler'] and row['handler']['path'] not in source_names:
            source_names.append(row['handler']['path'])
    else:
        profile = selection or 'rgmii'
        if profile not in hdl_tools.PROFILES:
            raise ValueError('Unknown HDL profile selection')
        # Discovery is passive. It does not invoke the native binary or reuse a
        # historical simulation as proof that this request has been executed.
        runtimes = {engine: hdl_tools.discover(engine)['state'] for engine in ('icarus', 'verilator')}
        data = {'profile': profile, 'title': hdl_tools.PROFILES[profile]['title'],
                'runtime_state': ', '.join(f'{k}: {v}' for k, v in runtimes.items()),
                'recorded_trace': 'NOT_SELECTED',
                'evidence_scope': 'HOST_SIM or STATIC_CHECK for a named native result; no board timing verdict',
                'signals': list(hdl_tools.PROFILES[profile]['signals'])}
        unknowns.append('No trace, signal value, native timescale or fresh simulation is supplied by this descriptor.')
        source_names = ['workbench/hdl_tools.py', 'workbench/hdl_qt.py', 'docs/HDL_INTEGRATION.md']
    packet = {'schema': contracts.PACKET_SCHEMA, 'view': view, 'selection': selection,
              'permission': 'read', 'captured_at': time.time(), 'data': data,
              'sources': [source_ref(kernel.root, name) for name in source_names],
              'unknowns': unknowns, 'seed_id': seed_status(kernel.root)['seed_id'],
              'source_scope': 'Selected descriptor and declared seed inputs; no project acceptance claim'}
    packet['packet_id'] = contracts.digest(packet)
    return contracts.validate_packet(packet)


def explain(kernel, principal, view, selection=''):
    packet = view_context(kernel, principal, view, selection)
    answer = contracts.DeterministicProvider().describe(packet)
    return {'schema': 'arc.stacy-foundation-explanation/1', 'state': 'SOURCE_BACKED_DETERMINISTIC',
            'text': contracts.render_answer(answer, packet), 'answer': answer, 'packet': packet,
            'notice': answer['notice']}


def foundation(kernel, principal):
    from .engineering_kernel import CAPABILITIES, TOOLS
    return {'schema': 'arc.stacy-foundation/1', 'pass': 1, 'assistant':'Slate', 'current_campaign_pass':22, 'current_delivery':__import__('workbench.version',fromlist=['VERSION']).VERSION, 'version':__import__('workbench.version',fromlist=['VERSION']).VERSION, 'seed': seed_status(kernel.root),
            'registered_operations': len(CAPABILITIES), 'registered_job_tools': len(TOOLS),
            'supported_views': list(contracts.VIEWS), 'provider': 'deterministic-seed-reader',
            'local_llm': __import__('workbench.local_brain',fromlist=['status']).status(kernel)['state'], 'durable_journal': 'DELIVERED_PASS_2',
            'intake': 'DETERMINISTIC_REFERENCE_INTAKE_PASS_4', 'references': 'EXACT_ORIGINAL_LOCATORS_PASS_5',
            'task_memory': 'VERIFIED_CHECKPOINTS_AND_EXPLICIT_LEARNING_PASS_6', 'study': 'FINITE_READ_ONLY_PILOT_PASS_8',
            'notice': 'Source-backed foundation only. No cloud call, inference or engineering job is started.'}


def dispatch(kernel, operation, args, principal):
    if operation == 'stacy.foundation': return foundation(kernel, principal)
    if operation == 'stacy.capabilities': return capabilities(kernel, principal, args.get('query', ''))
    if operation == 'stacy.seed.status': return seed_status(kernel.root)
    if operation == 'stacy.seed.search': return seed_search(kernel.root, args.get('query', ''), args.get('limit', 12))
    if operation == 'stacy.seed.record': return seed_record(kernel.root, args['id'])
    if operation == 'stacy.context': return view_context(kernel, principal, args['view'], args.get('selection', ''))
    if operation == 'stacy.explain': return explain(kernel, principal, args['view'], args.get('selection', ''))
    if operation == 'stacy.reader': return reader(kernel, args['operation'], principal)
    raise ValueError('Unknown Slate foundation operation')


def build_seed(root, export=None):
    """Explicit local authoring command. Never called by a read operation."""
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from . import ledger_control
    root = locations.program(root)
    sources = [source_ref(root, name) for name in SEED_INPUTS]
    inputs = {source['path']: source['sha256'] for source in sources}
    seed_id = sha(canonical(inputs))
    records = []
    def record(ident, kind, title, text, paths):
        records.append({'id': ident, 'kind': kind, 'title': title, 'text': text,
                        'sources': [s for s in sources if s['path'] in paths],
                        'review_state': 'SOURCE_BOUND_CANDIDATE', 'evidence_class': 'SOURCE_PRESENT'})
    record('owner:ledger-first', 'owner_intent', 'Graphite purpose and initial scope', OWNER_INTENT,  # GRAPHITE-01: the id stays
           ['docs/STACY_FOUNDATION.md'])
    for name in SEED_INPUTS:
        full_note = carried(name)
        if full_note or name.endswith('.md'):
            raw = project_file(root, name).read_text(encoding='utf-8')
            record('document:' + name, 'documentation', name, raw if full_note else raw[:24000], [name])
    definitions = schemas()
    for operation, scope in sorted(CAPABILITIES.items()):
        record('operation:' + operation, 'operation', operation,
               json.dumps({'scope': scope, 'arguments': definitions[operation],
                           'notice': 'Registration alone is not native qualification.'}, sort_keys=True),
               ['workbench/engineering_kernel.py', 'workbench/engineering_cli.py'])
    for spec in ledger_control.SPECS:
        record('setting:' + spec['key'], 'setting', spec['label'], json.dumps(spec, sort_keys=True),
               ['workbench/settings_registry.py', 'workbench/ledger_control.py', 'workbench/reading_profile.py'])
    catalog = {'schema': SCHEMA, 'seed_id': seed_id, 'records': records,
               'scope': 'Ledger application sources and explicit owner intent; no imported hardware or vendor facts.'}
    parent = locations.program(root) / 'project/stacy_seed'
    parent.mkdir(parents=True, exist_ok=True)
    if any(p.is_symlink() for p in [parent, *parent.parents]):
        raise ValueError('Seed output cannot use a linked path')
    with tempfile.TemporaryDirectory(prefix='seed-', dir=parent) as temporary:
        temp = Path(temporary)
        (temp / 'catalog.json').write_bytes(canonical(catalog))
        db = sqlite3.connect(temp / 'index.sqlite')
        try:
            db.execute('CREATE TABLE records(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            db.execute('CREATE VIRTUAL TABLE search USING fts5(record_id UNINDEXED,title,body)')
            for row in records:
                db.execute('INSERT INTO records VALUES(?,?)', (row['id'], json.dumps(row, sort_keys=True)))
                db.execute('INSERT INTO search VALUES(?,?,?)', (row['id'], row['title'], row['text']))
            db.commit()
            db.execute('VACUUM')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Seed index integrity check failed')
        finally:
            db.close()
        manifest = {'schema': SCHEMA, 'seed_id': seed_id, 'records': len(records), 'inputs': inputs,
                    'files': {name: sha((temp / name).read_bytes()) for name in ('catalog.json', 'index.sqlite')},
                    'builder': 'workbench.stacy_foundation', 'qualification': 'SOURCE_BINDINGS_ONLY',
                    'rights': 'Graphite seed. Project code and documents are GPL-2.0-only (COPYING); artwork, names and third-party parts keep their own terms (RIGHTS.md, THIRD_PARTY_NOTICES.md).'}
        (temp / 'manifest.json').write_bytes(canonical(manifest))
        target = _seed_paths(root)
        if target.is_symlink(): raise ValueError('Linked seed output')
        backup = parent / 'previous'
        if backup.exists(): shutil.rmtree(backup)
        if target.exists(): target.rename(backup)
        try:
            temp.rename(target)
        except OSError:
            if backup.exists(): backup.rename(target)
            raise
        if backup.exists(): shutil.rmtree(backup)
    if export:
        destination = Path(export)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(destination, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(_seed_paths(root).iterdir()): archive.write(path, path.name)
            for name in SEED_INPUTS: archive.write(project_file(root, name), 'originals/' + name)
    return seed_status(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('command', choices=('build-seed', 'status'))
    parser.add_argument('--export', type=Path)
    args = parser.parse_args(argv)
    result = build_seed(args.root, args.export) if args.command == 'build-seed' else seed_status(args.root)
    print(json.dumps(result, indent=2))
    return 0 if result['state'] == 'VERIFIED_SOURCE_BINDINGS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
