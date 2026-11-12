# Graphite implementation campaign

Twenty passes. Governing master: Graphite Master Specification v5 BOSS.

Graphite 0.2a6.post1 revises Visual Pass 1 on the P01–P10 implementation. See [the five-reference visual review](BOSS_VISUAL_PASS_01_REVISION.md) and [the halfway release](BOSS_HALFWAY_P10.md). P11 is next.

## Latest owner decisions

- The head shows the full active workspace path as directly editable text, without a surrounding box.
- Programs entries and dropdown menu commands participate in contextual cascading actions, alongside work objects.
- Use twenty substantial implementation passes for the entire master specification.
- No automatic test run after each pass; batch related work and use a quick launch-and-use check. Extra testing requires a concrete failure or data-integrity concern. No new test suites by default.

## Verification policy

No automatic tests per pass. Batch related changes and perform one quick launch-and-use check. Skip new tests for cosmetic changes. Reuse a small existing check only when an actual failure or specific data-integrity concern warrants it. No routine full suites, all-case reruns, model sweeps, or assertion-count targets.

## Passes

### P01 Build the native BOSS shell

Unify the current shell styling around charcoal, copper-orange, readable terminal lettering, restrained green signals, and intentional manga or ASCII spaces. Retire default cursive and reserved logo or corner-cat space. Provide Illustrated, ASCII, and Clean appearance choices without changing capabilities. Preserve reading scale, keyboard focus, reduced motion, and the owner's saved preferences.

Complete when: The actual Qt application opens in the new visual direction. Decoration can be reduced or removed, and working text, menus, files, and exports remain usable. Ship real widgets and separate artwork assets rather than a screenshot as the interface.

Dependencies: Supplied baseline.
Source anchors: shell2.py; reading_preferences.py; reading_profile.py; desk_qt.py; pane_qt.py; programs_qt.py.
State: IMPLEMENTED. Owner-host qualification remains pending.

Native charcoal/copper/green Qt chrome; optional Illustrated/ASCII/Clean ornament; named Work/Programs/System head, three writing modes, mirrored file/instrument panes. Stored legacy keys and reading preferences retained.

### P02 Make location and working objects coherent

Replace the old header title cluster with one borderless editable full path for the active workspace item. Support Ctrl+L, copying, Enter to navigate, and Escape to restore. Keep the complete address available without substituting an ellipsis. Extend current artifact bindings so selection, revision, location, and source identity stay consistent when switching work. Treat a database record or unsaved item truthfully instead of inventing a file path.

Complete when: Opening a file, changing tabs, navigating to a folder, and cancelling path editing preserve the right location and work. Programs and System remain reachable. Related artifacts can share a working surface without losing their individual identities.

Dependencies: P01.
Source anchors: shell2.py TopBar and PathBar; qt_app.py active_path; finder_qt.py; universal_viewer_qt.py; documents.py; object_context.py.
State: IMPLEMENTED. Owner-host qualification remains pending.

Full borderless path with Ctrl+L, Enter navigation and Escape restore; real file/folder paths and stable internal addresses for records and open unsaved work. Deferred command routes bind working identity, selection and revision.

### P03 Extend cascades to programs and menu commands

Give Programs entries and dropdown menu commands their own contextual actions. Ordinary clicks keep their familiar action; right-click and a keyboard or touch-accessible equivalent reveal relevant capabilities, parameters, source inspection, or a route into a chain. Bind those actions to the current artifact and supported operation. Extend Graphite's menus first and use actual application interfaces for native-program integration.

Complete when: A program entry, a dropdown command, and a selected object each expose useful contextual actions. The same operation carries the same target and revision checks through every route. Menus remain within the display and have predictable Escape, focus, and continuation behavior.

Dependencies: P02.
Source anchors: context_menu.py Target Entry providers and Router; programs_qt.py; menus2.py; hatch_qt.py; engineering_kernel.py; explore.py.
State: IMPLEMENTED. Owner-host qualification remains pending.

The contextual router handles program entries, native QMenu commands and contextual menu rows. Original QActions stay the ordinary click route. Secondary presses cannot activate an underlying menu action. Existing providers expose captured-work modifications.

### P04 Connect chains previews and the shared writing strip

Build on the existing staC chain builder to retain an editable sequence across menu openings, bind its inputs, preview its effects, run supported steps, and inspect the actual output. Consolidate Assistant, Terminal, and Log around the existing writing line; retain search through commands and keyboard access. Keep natural language and supported staC available through Assistant. Preserve real pause, stop, and process controls.

Complete when: The new desk can complete a real small chain and open its resulting artifact. A preview remains distinct from execution. Useful procedures can be retained through existing method records, and ordinary computer use still works with no model loaded.

Dependencies: P03.
Source anchors: chain_menu.py; stac/; context_menu.py; typebar_qt.py; console_qt.py; log_qt.py; qt_master_stop.py; system_menu_qt.py.
State: IMPLEMENTED. Owner-host qualification remains pending.

Retained chain tray, clickable stage prefixes, original cascade builder, read-only Kernel previews, source fingerprints, shared-strip editing, actual CSV and receipt saving, and existing kept-method menu. Changed sources refuse reuse; capped 200-row results cannot be exported as an apparently complete sheet.

### P05 Deliver the ThinkPad profile and Vulkan worker

Extend the existing model manager rather than add a competing inference system. Detect CPU, Radeon, usable memory, driver, Mesa, Vulkan, and runtime capabilities. Deliver or reproducibly build a pinned compatible Vulkan worker and its dependency route. Keep GGUF registration and a compatible CPU fallback. Show the effective backend and offload state from actual worker information.

Complete when: Graphite can configure and launch the supported Vulkan path on compatible hardware, preserve the current CPU route, and explain unavailable acceleration. Driver and firmware delivery uses maintained packages and retained notices.

Dependencies: P02.
Source anchors: brain_runtime.py; local_brain.py; brain_worker.py; model_settings.py; model_settings_qt.py; hardware_settings_qt.py; runtime manifests.
State: IMPLEMENTED. Owner-host GPU/model qualification remains pending.

Pinned Vulkan worker, actual host profile, saved launch preferences, observed-offload readback and one CPU fallback are delivered. The cloud reports no physical Vulkan device. Read docs/THINKPAD_VULKAN_P05.md.


### P06 Coordinate shared memory and foreground work

Implement the traffic cop through existing work ownership, agenda, worker controls, and model lifecycle. Account for weights, attention state, temporary allocations, CPU evidence, tools, and graphics in the one system memory pool. Prefer useful supported GPU inference while CPU preparation remains responsive. Keep priority, queue ordering, CPU niceness, and actual preemption limits distinct. Adapt resource containment to GPU virtual-address behavior.

Complete when: Foreground interaction can take priority at supported boundaries. Memory pressure, cancellation, failure, and fallback retain findings and correct worker ownership. The installed 64 GB is never presented as 64 GB of guaranteed GPU allocation.

Dependencies: P05.
Source anchors: agenda.py; agent_loop.py; local_brain.py; brain_worker.py; worker_boundary.py; job_priority.py; operations.py; host_service.py.
State: IMPLEMENTED. Shared-bandwidth, thermal and owner-host responsiveness qualification remain pending.

Resource admission now uses the existing queued worker and durable job record; foreground priority, model serialization and owned memory guards are delivered. Read docs/TRAFFIC_COP_P06.md.


### P07 Prepare useful evidence on the CPU

Join retrieval, indexing, typed extraction, exact arithmetic, units, dependency relationships, and relevant tool selection into intelligent data arrangement. Build a compact current evidence packet before a useful model turn, while letting model interpretation identify additional material or calculations. Preserve source conditions and unresolved meanings. Keep deterministic correctness separate from interpretation and engineering applicability.

Complete when: A model question can use observed calculations and current source references, retrieve omitted prose when needed, and identify the next consequential question. Changed inputs invalidate the affected preparation instead of quietly reusing a stale answer.

Dependencies: P02, P06.
Source anchors: knowledge_service.py; reference_service.py; math_service.py; math_backend.py; reason_graph.py; typed_artifacts.py; tool_selection.py; conditions.py.
State: IMPLEMENTED. Live model interpretation and owner-host qualification remain pending.

Ask Graphite prepares revision-bound source evidence and exact arithmetic before inference. The model receives
results within their declared conditions and supplied dependencies. Read or focus an omitted passage from the
same frozen sources. See docs/INTELLIGENT_DATA_P07.md.

### P08 Complete context cache and model lifecycle

Manage effective token budgets, prepared prefixes, eviction, streaming, worker identity, replacement, and rollback coherently. Verify model identity at appropriate lifecycle boundaries without needlessly hashing all weights every turn. Reuse established inference methods only where the selected model, backend, and pinned runtime support them: suitable precision, microbatching, attention, prefix reuse, speculation, or expert placement. Treat each as a compatible candidate rather than an obligatory imported engine.

Complete when: Model replacement preserves knowledge, temporary state is correctly invalidated or reconstructed, and stopped work stays stopped. Effective settings and the reason for fallback are inspectable. Actual usefulness and resource observations guide configuration; no promised speed multiplier or parameter-count guarantee is inserted.

Dependencies: P05, P06, P07.
Source anchors: local_brain.py; brain_runtime.py; brain_worker.py; model_turn.py; model_settings.py; tool_selection.py; current runtime interfaces.
State: IMPLEMENTED. Live model and owner-host qualification remain pending.

The resident worker binds load verification to the weight file's identity, reads back effective settings and invalidates old launch requests on Stop. Matching source turns can ask the existing runtime for single-slot prompt reuse.

### P09 Make the material collection useful and portable

Complete the file and collection experience around real locations, project associations, incoming material, source identities, local search, and readable exports. Preserve originals, revisions, Ingress, Egress, Trash, and established working-copy behavior. Index permitted project material without loading the whole collection into each model turn. Keep files, machine resources, and settings directly usable by the owner and assistant.

Complete when: A supplied collection can be brought in, found, opened, inspected, and exported with its relationships. Missing private project files remain a named input requirement. Records and source material remain useful without the conversation or a model.

Dependencies: P02, P04, P07.
Source anchors: files_service.py; files_qt.py; browse.py; finder_qt.py; receiving.py; working_copies.py; cabinet.py; knowledge_service.py.
State: IMPLEMENTED.

Project notes attach admitted collections. Evidence preparation searches their index with source locators and current revisions. The verified export includes ordinary filenames and a readable relationship catalog.

### P10 Complete documents sheets and PDF work

Finish the everyday artifact chain: read or OCR a PDF where needed, extract tables with units and conditions, build an editable sheet, calculate through suitable local tools, and produce an editable document or printable output. Preserve selected text during edits, formatting and undo where supported, numerical meaning, source pages, and unresolved extraction questions. Use mature document and spreadsheet engines.

Complete when: Datasheet to sheet to calculation to report is a real route through saved artifacts. Owner and assistant can alternate edits. A changed extracted value leads to the appropriate recheck; a scanned table or missing unit receives explicit handling rather than a fabricated value.

Dependencies: P04, P07, P09.
Source anchors: documents.py; document_qt.py; pdf_service.py; reference_service.py; office_service.py; office_runtime.py; math_office.py; office_math_runtime.py.
State: IMPLEMENTED.

Reviewed PDF table rows create an editable sheet with units, conditions and provenance. Exact calculations write editable reports from named cells. Changed inputs mark affected reports for recheck. Image-only pages use the PDF OCR route before table review.

### P11 Make full native programs part of the desk

Provide dependable native application launching, focus, ordinary windows, clipboard, file dialogs, and return to Graphite within a maintained Linux session. Connect compact work views through supported APIs, scripts, or explicit file handoffs. Keep full Blender, browsers, mail, office, and other installed applications reachable even where specialized automation is incomplete. Preserve manual use with the assistant off.

Complete when: The owner can operate a full application, return to the same task, and retain the actual saved or shared state. An explicit handoff reports its continuity guarantees. Installation is distinguishable from assistant-callable capability; universal foreign-window embedding is not required.

Dependencies: P02, P09.
Source anchors: native_sessions.py; desktop_services.py; workspace_services.py; universal_viewer_qt.py; explore.py; launcher.py; LS_XSESSION.sh.
State: PLANNED.

### P12 Follow edits across artifacts and applications

Unify revision and selection bindings across source excerpts, documents, tables, scenes, reports, and investigations. Connect source-to-result inspection, before and after, supported undo, staleness, and recovery. Refresh actual state after native application work. A preview, proposal, completed edit, and saved export retain separate meanings. Let related objects share the surface without freezing every task into equal columns.

Complete when: A manual correction reaches affected dependent work, an assistant change is inspectable, and returning from a native program reconciles the current artifact. A compatible retained method can be rebound to new material without borrowing old input values or execution claims.

Dependencies: P10, P11.
Source anchors: typed_artifacts.py; reason_graph.py; object_context.py; change_sets.py; conditions.py; working_copies.py; investigation_service.py; context_menu.py.
State: PLANNED.

### P13 Generalize the resident assignment loop

Extend the existing durable loop beyond its narrow built-in profiles. Carry an arbitrary supported assignment through relevant tool selection, incremental planning, actual execution, observation, revised interpretation, and a useful next action. Preserve goals, findings, attempted approaches, unresolved conditions, and budgets outside the context window. Continue permitted long work when the presentation window closes and resume coherently after restart.

Complete when: A supplied unfamiliar assignment can use supported tools and leave real work, an appropriate specific question, or a precise condition preventing progress. Pause, Stop, failure recovery, and completion reflect the actual worker. A completed calculation is not automatically a completed assignment.

Dependencies: P07, P08, P12.
Source anchors: agent_loop.py; agent_profiles.py; investigations.py; investigation_service.py; continuing_work.py; host_service.py; tool_selection.py; model_turn.py.
State: PLANNED.

### P14 Obtain missing abilities and retain useful tools

Discover installed software and existing supported operations before inventing a helper. When an assignment lacks an ability, establish an authorized acquisition or integration route, use mature software as a base, and return to the original task. Add dynamic helper development with inspectable inputs, outputs, dependencies, limits, and execution records. Consider retaining or promoting a recurring useful tool when the need appears again.

Complete when: A genuine capability gap can become a usable installed tool, adapter, or helper within the assignment's authority. Repeated need reuses or improves that work. Programs and menus expose substantial capabilities without flooding the launcher with every internal helper.

Dependencies: P11, P13.
Source anchors: tool_atlas.py; tool_inventory.py; tool_selection.py; helpers.py; checked_methods.py; worker_tasks.py; package_service.py; integration_tools.py.
State: PLANNED.

### P15 Connect web correspondence and scheduling

Add useful web research, authenticated browsing, email understanding, mailbox operations, evidence-based correspondence, calendars, and commitment-aware scheduling through maintained integrations. Preserve thread identities, dates, accounts, sources, relevant permissions, and external acknowledgements. Include prepared online forms, record reconciliation, and clean paper letters where the task needs them. Keep imported material and local preparation usable offline; connect selected services for actual external work.

Complete when: Graphite can complete an authorized research or secretary chain with real artifacts and clear external state. Drafting, sending, acknowledgement, and delivery remain distinct. Reconcile an uncertain response before retrying. Obtain missing intent or access only when it is genuinely missing; a webpage or email does not grant new authority.

Dependencies: P09, P10, P13, P14.
Source anchors: research_service.py; knowledge_service.py; reference_service.py; office_service.py; documents.py; agenda.py; existing browser routes and new supported service adapters.
State: PLANNED.

### P16 Complete specialist and creative work routes

Extend the common interfaces and useful specialized adapters for engineering, CAD and Blender, compilers and software repair, images, audio and video, network investigation, translation, and demanding records work. Preserve native project formats and let one program produce inputs to another. Build task-relevant helpers when needed. Deliver roughly thirty programs' worth of useful ability through mature applications and supported operations rather than thirty rewritten applications.

Complete when: Representative complex assignments leave editable deliverables and source-linked results across installed tools. Geometry, electrical assumptions, calculations, and external project facts are assessed through their actual sources and tools. An engineering uncertainty or missing private dataset is retained explicitly rather than converted to an unsupported confidence percentage.

Dependencies: P10, P11, P12, P13, P14, P15.
Source anchors: Existing engineering and office adapters; kicad_tools.py; spice_tools.py; hdl_tools.py; first_stage_tools.py; network_watch.py; native_sessions.py; new task-driven adapters.
State: PLANNED.

### P17 Make improvement durable and recoverable

Connect observed friction and recurring work to a useful improvement process. Distinct observer, builder, and reviewer responsibilities can share one inference service and durable store. Retain candidates, compare actual artifacts or behavior where necessary, curate preferred methods, activate suitable changes within standing authority, and recover code and data together. Preserve failed attempts with their conditions and learn useful host configuration from ordinary work.

Complete when: A recurring limitation can lead to a retained method or software improvement with a clear basis, previous working path, and recovery behavior. An adopted change does not erase useful records or expand its own authority. Model replacement preserves the accumulated knowledge. Three cooperative roles do not require three resident LLMs.

Dependencies: P06, P08, P13, P14, P16.
Source anchors: helpers.py; checked_methods.py; study_service.py; experiment_runtime.py; reason_graph.py; update_service.py; existing worker and evidence stores.
State: PLANNED.

### P18 Converge the full journeys and capability coverage

Use the thirty-five assignment cases as a coverage and integration ledger, including all five four-application chains. Reuse observations accumulated while implementing the capabilities. Close missing handoffs, recovery, changed-input behavior, and ordinary manual operation across the same desk. Separate software completion, supported uncertainty, a missing input, and hardware or service qualification. Finish portable partial and whole-collection exports.

Complete when: Each case has an implementation owner and a stated capability route; delivered journeys point to real outputs or the precise remaining input or qualification. There is no automatic rerun of all thirty-five scenarios. New activity is limited to resolving an actual unestablished boundary or observed defect.

Dependencies: P12, P15, P16, P17.
Source anchors: All implemented artifact, application, assignment, method, and evidence boundaries; the case coverage ledger in this campaign.
State: PLANNED.

### P19 Build the maintained Debian delivery

Finish the minimal maintained Debian desktop profile, Graphite session, full native application access, bootable USB image, supported installation, persistence, and recovery. Include the compatible driver, firmware, runtime, application, and offline dependency route. Keep model acquisition and any separately licensed components explicit. Preserve the ordinary application upgrade route while delivering the complete system.

Complete when: A reproducible image or supported build recipe, installer, offline cache layout, dependency identities, notices, and recovery instructions are available. The system uses maintained Debian components; the project is not required to fork the Linux kernel. User data and supported native formats survive upgrades.

Dependencies: P05, P11, P13, P15, P18.
Source anchors: INSTALL_LS.py; INSTALL_DEBIAN.sh; START_MINIMAL_DEBIAN.sh; LS_XSESSION.sh; package_service.py; deployment and release tools.
State: PLANNED.

### P20 Qualify the ThinkPad and ship the complete release

Collect the missing owner-host observations through normal use: install and session startup, display and input, full applications, actual Radeon backend and model, useful memory headroom, responsiveness, stopping, and continuation. Complete recovery and upgrade readback, reconcile the requirement and case ledgers, and ship the usable release, source, guides, and installer volumes at or below 15,000,000 bytes each.

Complete when: The final handoff states what is implemented, actually observed, and still blocked. Preserve the free-of-charge local core and existing rights and upstream notices. Owner-host acceptance is closed only by the actual machine observations. A missing laptop can leave that qualification pending while independent packaging continues.

Dependencies: P08, P17, P18, P19.
Source anchors: Current release registry and manifests; package_graphite.py; package_release_parts.py; existing install, backup, runtime, and readiness entry points.
State: PLANNED.

## Completion policy

A pass closes on delivered usable implementation and the relevant observed boundary, not a plan, screenshot, test count, or model assertion. Record live-model, native-application, account, and owner-host qualification separately. P20 owner-host acceptance remains open without the actual machine.
