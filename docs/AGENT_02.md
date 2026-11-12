# AGENT-02 · the three mechanisms in one page

November 6, 2026 · UTC. Operator's summary; the details are in docs/CONTINUE_01.md, docs/MODEL_TURN_01.md and docs/FILES_ABOUT_01.md.

| What | Where | Operations and settings | Evidence |
| --- | --- | --- | --- |
| A running assignment continues in the resident Ledger service while Ledger is closed; the desktop takes it back | `workbench/agent_loop.py` (driver, lease_until, service_steps, authority columns; `pump`, `pause_all`), `workbench/host_service.py` (tick, Master Stop), `workbench/agent_qt.py` (release on close, adopt on open, Today) | `agent.step {id, driver?}`, `agent.release {id}` (new, execute), `agent.status` rows gain driver, lease_live, lease_until, service_steps; setting `agent.continue_when_closed` (default on) | `tests_integrated/test_agent_loop.py`, `tools/check_continue_ui.py`, `tools/check_continue_service.py` (the real service) |
| A document edit the model proposes for the open page is applied at once, highlighted, undoable | `workbench/model_turn.py`, `workbench/document_qt.py` (`apply_model_edit`, the glow), `workbench/shell2.py` (the APPLIED card), `workbench/documents.py` (`EDIT_ORIGINS`), `workbench/instruction_matrix.py` (`APPLIED`) | `documents.edit` origin `SLATE_MODEL` (edit only); readback `basis: MODEL_PROPOSAL_CHECKED_AND_APPLIED`, `model_used: true` | `tests_integrated/test_model_turn.py`, `tools/check_model_turn_ui.py`, build/agent02_ui/model_trial (live, build container) |
| Files about something: a findings page from Files and Ingress | `workbench/profile_files.py` (registered in `agent_profiles.py`), `agent_qt.assign_from_page` | `agent.assign` profile `files_about`; reads `receiving.status`, `files.find`, `ledger.browse`, `files.get` (four at most); writes `documents.create`, `documents.edit` append | `tests_integrated/test_profile_files.py`, `tools/check_files_about_ui.py` |

Rules that hold across all three: one dispatcher (the Kernel), no new scheduler, store or process; every step recorded before it is interpreted; Master Stop is the one kill switch; the desktop has priority over the service; only a page edit applies by itself; nothing claims acceptance.
