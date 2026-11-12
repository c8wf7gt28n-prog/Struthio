# HATCH SERVICE 01

November 3, 2026 · America/Phoenix

Complete checkpoint over PRESENTATION-01. This pass integrates the existing Hatch On, Off and Reboot choices with durable cycle state, shared Settings history, graceful draining and visible Operations/service-detail readback. It also adds a verified release-parts installer, minimal Debian session scripts and the complete project specification requested by the owner.

## Service state and ownership

The trusted local service adapter stores its current cycle in the existing Kernel settings database. Off/Reboot atomically commit the cycle receipt and the false services-admission setting, including the normal shared setting journal entry. Running work is not emergency-held at this point. Queued jobs are cancelled by the original jobs.cancel route; running jobs, owned worker observations, tracked Qt commands and existing provider in-flight indicators keep the cycle draining.

Once drained, a guarded transaction applies the work hold and advances the cycle to stopping. Backend-owned model, console, desktop-tool and phone services close through their existing ownership paths. A narrow owner-only service_quiesce coordinator method covers backend-owned handles; it accepts only the current live stopping cycle. It is not a new public Kernel operation or an arbitrary RPC method dispatcher. The coordinator remains available as the service-control plane. No OS shutdown, logout or reboot command is invoked by Hatch.

Explicit On commits the supported work-gate release and admission update together with history. It refuses unresolved owned work when releasing a hold. A no-hold On does not cancel an already running job. Cancelled jobs are not replayed. Phone access remains off and no model is invented or started by On.

Reboot is the guarded second half of the same cycle. It may request the previously observed running model with its original configuration, using the original model action. Requested is distinct from running. Slate off skips that reload. A failed reload is separately reported. Every continuation checks the admission revision, work-gate epoch, cycle identity and live desktop. A newer Stop, Resume, even a same-value admission edit, another cycle or an absent desktop prevents the old automatic continuation. Reopening the programme never replays a pending Reboot.

Failed or corrupt cycle state is not silently replaced. Readback distinguishes admission-only holds from confirmed service closure, draining, stopping, interruption and changed decisions. Unknown state disables the Hatch service actions while retaining New Idea/New Project and ordinary inspection where their own stores remain available. Settings remain governed by their original definitions and scopes.

## Desktop and admission integration

Hatch retains its five current actions. Operations now shows service state separately from Slate/model state, and the existing Background service room provides details. New direct desktop commands, language/debugger starts or execution, console activity, phone starts and cloud replies respect the applicable admission checks. Existing close/inspection paths remain usable. Asynchronous queued cancellation and backend closure keep the desktop responsive during a cycle.

The real Qt walkthrough found a working-file save bug: the atomic replacement adopted temporary-file permissions. Save now preserves the original ordinary mode before replacement. The walkthrough verifies both saved text and mode through Off and Reboot. Service details is a workspace room, so it retains the edited source Preview.

## Installer and delivery

INSTALL_LS.py accepts a local release-parts directory or a pinned public HTTPS release manifest. It validates every part, restores hashed chunks for an individually oversized runtime, verifies the full payload and extracts into a new folder. It retains existing installation folders. Extract-only and plan routes invoke no package manager.

Offline mode requires a complete matching dependency cache with OFFLINE_FILES.json, debs and wheels. It refuses missing/unlisted/changed cache files and has no network fallback. The default desktop profile and optional suite profile reuse the existing Debian/runtime installers. Quick mode checks runtime imports, package integrity and source bindings without automatically repeating the extended historical walkthroughs.

START_MINIMAL_DEBIAN.sh and LS_XSESSION.sh provide the manual dedicated X11/Fluxbox fullscreen route on existing Debian. They do not rewrite login or disk configuration. Actual apt/pip installation, wireless connection, display/driver startup, a bootable appliance ISO, public release hosting and the complete offline media cache remain unaccepted deployment work. See MINIMAL_DEBIAN_INSTALL_01.md for exact usage and requirements.

Every delivered ZIP is limited to 15,000,000 bytes. The pinned llama runtime archive is larger than one volume, so it is split into hashed transport pieces and restored before payload checks. The original runtime archive, its bytes and its hash are retained after installation. This preserves the complete programme while meeting the owner's part-size request.

## Complete specification and direction

LEDGER_SLATE_COMPLETE_PROJECT_SPEC_01.md and Ledger_Slate_Complete_Project_Specification_01.docx contain the long complete-product specification, including architecture, working copies, permissions, local Slate, staC, mathematical reasoning, documents, service controls, installation, UI appearance and acceptance. The Word document has 27 rendered pages with four actual UI illustrations. Its source is about 9,300 words. Every rendered page was visually reviewed; the inherited decorative title rule was removed.

The November 2 Interface Companion gives the launcher a broader capability-catalogue role. That accepted direction is retained explicitly. The five-action menu is the current implementation stage; Explore remains the current broad discovery route. Integration of that catalogue role into Hatch, the remaining all-settings audit and the writing-marker experiment remain open. The final development estimate must not erase these goals or turn registration counts into readiness claims.

## Focused evidence and limits

54 focused tests passed: 18 service authority/lifecycle cases, nine release-media/installer cases and 27 related Operations/shared-settings regressions. Eleven actual Qt checks passed with six captures. Three disposable durable job records exercise running/queued/completed states; no actual job was submitted. All Kernel launchers and provider entry points were held. No native tool, model worker, generation or provider request started. The real coordinator IPC/display/model and wireless installation remain owner-host acceptance work.

All 690 public operation schemas and scopes, 112 job-tool targets and all forty prior setting definitions remain unchanged. The registry digest remains 9b28255cf4cd31117ece3edada8a737b569e9de996cbb32836e3b1040f92e1a1. Full packaging, source binding, preservation, volume-size and restored-payload checks are recorded after packaging in the separate discussion.

Three of the four estimated cloud development passes are complete. One integration/debug pass is planned, with scope and findings allowed to change the estimate. Owner-host validation/fixes are separately estimated at one or two passes when the machine and inputs are available. Strict HATCH acceptance remains 0/6 and historical integrated acceptance 4/6. Exact-model/native I05, owner-host I06, live scheduling, pointer dragging, real service cycles and owned Stop acceptance remain open.

INTEGRATION-01 (November 4, 2026): the five choices remain first; a Services row, capability groups and a session footer follow; see docs/HATCH_INTEGRATION_01.md.
