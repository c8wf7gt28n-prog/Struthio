{
 "summary": "SCOPE AND STATE OF THE TREE. The tree moved while I read it: 1d45b9c -> a9a1b4e -> bf42691 -> cb72be5 (\"Graphite 0.4 in progress\", workbench/field_do.py now exists). All trials ran in the throwaway After Hours 07 workspace on a `git archive` snapshot of 1d45b9c (/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs/pristine); the two helper functions were re-run on the live tree (0.4.0). Line numbers below are the live tree at cb72be5. My scripts: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs/ (run.sh, last_touched.py, full_window.py, a1_probe.py, a2b_probe.py, a3_probe.py, b_probe.py, b2_probe.py, b3_probe.py, live_check.py; screenshots in out/).\n\n(A1) WHAT IS RECORDED. One journal: table activity_journal(seq, event_id, payload) in <workspace>/.ledger/engineering.sqlite3 (workbench/activity.py:55,68). A row holds schema, id, at, origin (the principal's identity, or GUI / DESKTOP / KERNEL / STACY), operation, state, detail (300 chars, redacted, absolute paths removed) and optionally job_id, evidence_id, candidate_id, correlation_id, parent_id, source_generation (activity.py:44-51). It holds NO arguments and NO object ids. Every dispatch that is not an observer operation writes REQUEST_RECEIVED then REQUEST_COMPLETED or DENIED_OR_FAILED with one correlation_id (engineering_kernel.py:509, 389-395); about 120 observer reads (activity.py:8-31: documents.get, office.get, investigation.sheet, jobs.list, ledger.journal.read ...) write nothing; a job's state changes write rows with the tool name as operation plus job_id (engineering_kernel.py:453-459). Tried, real rows: opening a page from the Field = one row {origin GUI, operation ledger.view, state FOCUSED, detail \"Documents\"} (the tab title, qt_app.py:3559); opening a sheet = detail \"Preview \u00b7 07 Bench readings\"; editing a cell = office.save RECEIVED/COMPLETED (no id) plus a row (at, 'office.save', 'owner:db5f...') in the Office store's own events table in <config>/concern/catalog.sqlite3 and a kept version in office_history; running staC = language.run RECEIVED/COMPLETED (no text) plus an instruction_matrix row holding the whole line; saving a page = documents.save two rows plus desk_events (record id, revision, actor, DOCUMENT_SAVED, at); approving a proposed change = files.decide two rows, and files.story then says \"you applied its change\" with a kept version. A second store, ledger_trail (work_trail.py:72-103), keeps one row per non-read request (id = correlation id, operation, scope, created, returned, state, scope_check, pid; at most 256) and says of itself METADATA_ONLY_NO_ARGUMENTS_SOURCE_OR_OUTPUT_TEXT (work_trail.py:280).\nReading back: last N = ledger.journal.status for head, then ledger.journal.read {\"after\": str(head-N), \"limit\": N}; since time T = there is no time filter: page 200 at a time and compare `at`, or staC `activity {\"after\":\"<seq>\",\"limit\":200} | where at over <T>`; touched object X = not answerable from the journal at all; it comes from each record's own store (A2).\n\n(A2) FROM A ROW TO THE OBJECT. Written and run: last_touched(kernel, principal, field) in last_touched.py. For the worked case it gave a time and operation for all 14 objects, before and after five owner actions (table in recipes). Sources per Field id: document:<id> from documents.list row.updated/last_change (documents.get also returns events[]); claim:<id> from investigation.sheet claim.created; intake:<id> from its batch (intake.batches created) and from jobs whose request_spec names the item; job:<id> from jobs.list; office:owner:<id> ONLY from the Office store's events rows, which no operation returns (through operations alone the three sheets get no time); any object whose 32-hex id appears in a staC line that ran, from matrix.list; and ledger.view rows matched by tab title when exactly one sheet has that title. Not mappable: which page was opened or viewed (reads are unrecorded, and a DocumentsTab's title is always \"Documents\"); which record a journal request row was about (no arguments by design); evidence added to a claim (investigation.path steps carry no time); condition: none in the case.\n\n(A3) LAST SEEN / AWAY. Five existing notions. (1) A watermark per named consumer: table activity_consumers(name, cursor, event_id, projection); ledger.awareness {consumer} gives cursor, head, backlog; ledger.awareness.catch_up advances it. The window advances consumer \"stacy\" every 750 ms (control_qt.py:468-473) so its backlog is always about 0; a consumer of your own works (tried \"field\": backlog 185 -> 0, later 4). (2) Session boundaries: one journal row ledger.open READY from origin DESKTOP per launch (control_qt.py:148); tried: rows 1 and 182, \"away for 3.4 days\" computed from the row before the newest one. (3) Today (shell2.py:2164 TodayPage): arrived = receiving.status.inbox_waiting; waiting = receiving.deliveries + agenda.view.waiting + paused assignments + copies.list; Continue = host._viewer_recent (memory only) + session.state['recent'] (10 file paths). In the worked case Continue is empty although pages and sheets were opened, because only files count. (4) \"While Graphite was closed, it took N steps on ...\" (agent_qt.py:287) reads agent.list rows' service_steps within 24 h; only for assignments the service stepped (read, not tried: agent.list is empty). (5) The return thread, ledger.session.read: note, drafts, context, updated; kept at close only when its content changed, so `updated` is not a reliable closing time.\n\n(A4) IN USE NOW. ledger.context: desktop {surface 'home'|'workspace', workspace = class name of the front tab, selection, stacy_view, active_file} republished every 750 ms (control_qt.py:431-466), desktop_connection, active_jobs. Tried: with the Field in front it still says surface \"workspace\" and nothing of the Field's selection. Open tabs exist only in Qt (host.tabs) and, after save_session, in session.json workspace.tabs (kind, pinned, concern id for an OfficePanel, pdf_namespace/pdf_item/pdf_page for a PDF; a DocumentsTab row has no page id). Running work: ledger.explore instruments[].running_jobs/queued_jobs per program, ledger.awareness.jobs with process_health. Native sessions: only the owned Calc session is a record (desk record kind native_session + job math.session); a program started by programs.*.open leaves a pid in its receipt and two journal rows, nothing else.\n\n(B5) THE 33. Full native window behind it, 6 programs: FreeCAD (programs.freecad.open), Inkscape (programs.inkscape.open), Blender (programs.blender.open), Godot (programs.godot.open / .play), Mail = Thunderbird (programs.mail.open), Cartridge Bay = RetroArch (programs.cartridge.launch). All need a file inside Graphite Files plus the sha256 from the matching .inspect; all are scope approve and also demand principal identity desktop-owner; executables are found with shutil.which; all need DISPLAY or WAYLAND_DISPLAY; they start detached and return {state STARTED, pid}. Two more reach LibreOffice: Office (a sheet's prepared copy through office.operation.*, back through office.candidate.*) and Files (a .ods/.xlsx in the worksheet view: \"Full spreadsheet\", then \"Return to sheet\"; no operation, sheet_workbench_qt.py:426-443). Calculator holds the one tracked native session (joined.session.*). Graphite rooms only: Projects, Questions, Documents, Assignments, Agenda, Laboratory, Methods, Sources, References, Memory, Work trail, Media Bench (ffprobe/ffmpeg headless), Print Proof, Transfer (curl), Delivery, Local model, Settings, Tool Atlas; and the six BUILD entries are Graphite checks whose own editor never opens (explore.py:62-70).\n\n(B6) STAGING, TRIED. Nothing installed and no display: programs.freecad.open -> \"The FreeCAD editor is unavailable on this host.\"; inkscape -> \"Install Inkscape to render or edit this SVG.\"; blender / godot -> \"Blender is unavailable on this host.\" / \"Godot is unavailable on this host.\"; mail -> \"Open the Graphite desktop session to hand this file to Thunderbird.\"; cartridge -> \"Install native RetroArch and an NES core to play this local cartridge.\" In the FreeCAD room the Full app button stays disabled and the status reads \"Document inspected \u00b7 geometry check unavailable for this source.\" With a stand-in executable named freecad on PATH and DISPLAY set, the same click started it: status \"FreeCAD process started \u00b7 PID 15\", command line `freecad --safe-mode <Files>/probe/part.FCStd`. There is no confirmation dialog: the click (or the approve-scope call) is the consent. The one function: full_window(kernel, principal, key, path) in full_window.py = programs.<key>.inspect then programs.<key>.open. \"With no file\" does not exist anywhere.\n\n(B7) THE SEAM. In the live tree F on a shelf sheet already emits FieldView.full_asked (field_qt.py:52, 233-234) and nothing is connected to it (tried: F does nothing visible); field_do.BY_KIND (field_do.py:181) has no 'app' entry. See advice.",
 "operations": [
  {
   "name": "ledger.journal.status",
   "arguments": "{}",
   "effect": "Returns head (highest seq), first, count, state CURRENT|INCOMPLETE, retention ALL_RECORDED_EVENTS, coverage sentence, observer_events_suppressed (the operation names that never leave a row).",
   "evidence": "Tried: head 182 on the restored case (181 stored + this launch's ledger.open). workbench/activity.py:124.",
   "scope": "read"
  },
  {
   "name": "ledger.journal.read",
   "arguments": "{\"after\": \"<seq as digits, or an event id>\", \"limit\": 1..200}  (both optional; limit defaults to 100; after defaults to the beginning)",
   "effect": "Rows in commit order after the cursor: {events:[{seq,id,at,origin,operation,state,detail,correlation_id?,job_id?,evidence_id?,candidate_id?,source_generation?}], cursor, head, gap, has_more}. No time filter, no object filter. staC alias: `activity`.",
   "evidence": "Tried: last 6 = after head-6; paged all 198 rows. An observer operation, so reading adds no row. stacy_awareness.py:10,120; activity.py:148.",
   "scope": "read"
  },
  {
   "name": "ledger.activity",
   "arguments": "{\"after\": \"...\", \"query\": \"<substring matched against origin, operation, state, detail>\", \"limit\": 1..200}  (all optional)",
   "effect": "The same stream with a text filter. An unknown non-numeric `after` sets gap true and reads from the start.",
   "evidence": "Tried: query 'ledger.view' returned the 10 tab-title rows; query 'office.save' the 2 rows of one save. ledger_control.py:40,523.",
   "scope": "read"
  },
  {
   "name": "ledger.context",
   "arguments": "{}",
   "effect": "{desktop:{surface,workspace,selection,stacy_view,active_file?,cabinet_selection?}, desktop_connection CONNECTED|LAST_RECORDED, active_jobs (up to 20 unfinished of the newest 100), recent_activity (the last 20 journal rows), settings}.",
   "evidence": "Tried in four places: surface is 'home' or 'workspace' only; with the Field in front it says 'workspace' and workspace None. ledger_control.py:475-496; control_qt.py:447.",
   "scope": "read"
  },
  {
   "name": "ledger.trail.list / ledger.trail.inspect",
   "arguments": "ledger.trail.list {\"limit\": 1..50}; ledger.trail.inspect {\"id\": \"<32 hex = the request's correlation id>\"}",
   "effect": "One 'intent' per non-read request of this owner: id, operation, created, request_state, scope_check, work, job_ids; inspect adds linked jobs and artifact checks. Metadata only: no arguments.",
   "evidence": "Tried: the four writes of the probe appear newest first with their correlation ids. work_trail.py:17-19, 235, 259, 280.",
   "scope": "read"
  },
  {
   "name": "ledger.awareness",
   "arguments": "{\"consumer\": \"<name, ^[a-zA-Z0-9_.-]{1,48}$>\"}  (optional; default 'stacy')",
   "effect": "A named watermark into the journal: {state CURRENT|CATCHING_UP|INCOMPLETE, cursor, head, backlog, projection{processed, jobs{job_id:{state,seq,evidence_id}}, last_event}, jobs (unfinished, with process_health)}.",
   "evidence": "Tried with consumer 'field': cursor 0, backlog 185; after two more actions backlog 4. In a staC line `| select state,cursor` returns nothing because staC descends into the `jobs` list first (typed_pipeline.py:216); call the operation directly. stacy_awareness.py:12,36.",
   "scope": "read"
  },
  {
   "name": "ledger.awareness.catch_up",
   "arguments": "{\"consumer\": \"<name>\", \"limit\": 1..200}  (both optional)",
   "effect": "Advances that consumer's cursor by up to `limit` rows and stores cursor and projection together (table activity_consumers). An observer operation: leaves no journal row.",
   "evidence": "Tried: 'field' went 0 -> 185 in one call, a second call was a no-op. The window calls it for 'stacy' every 750 ms (control_qt.py:468-473). stacy_awareness.py:13,57.",
   "scope": "execute"
  },
  {
   "name": "ledger.session.read / ledger.session.keep",
   "arguments": "ledger.session.read {}; ledger.session.keep {\"expected_revision\": int, \"note\": str, \"drafts\": [{id,title,text}], \"context\": str?}",
   "effect": "The owner's one return copy per workspace: {revision, updated, note, drafts, context}. keep returns changed:false and does not move `updated` when nothing differs.",
   "evidence": "Read tried: revision 1, updated = the previous session's close. return_thread.py:17-22, 64-82.",
   "scope": "read / execute"
  },
  {
   "name": "documents.list",
   "arguments": "{\"limit\": int, \"offset\": int, \"project\": str}  (all optional)",
   "effect": "Rows {id, title, revision, updated, words, blocks, project, last_change{actor, at, words}}: a page's last change without a read per page.",
   "evidence": "Tried: after documents.save the row showed revision 2, updated = the save, last_change 'HUMAN saved the writing'.",
   "scope": "read"
  },
  {
   "name": "documents.get",
   "arguments": "{\"id\": \"<32 hex>\"}",
   "effect": "{document, summary, events:[{revision, actor, action DOCUMENT_CREATED|DOCUMENT_SAVED, at}] newest first (32 at most), plain, source_state when it is a calculation}.",
   "evidence": "Tried. workbench/documents.py:418 reads desk_events.",
   "scope": "read"
  },
  {
   "name": "office.list / office.get",
   "arguments": "office.list {}; office.get {\"id\": \"owner:<32 hex>\"}",
   "effect": "list rows {id, version, title, state, kind}; get {id, version, revision (sha), document{sheets[{cells{A1:{value,type,unit,...}}}]}, origin{pdf{item, job, page_index,...}}, source_state}. Neither carries a time.",
   "evidence": "Tried: after office.save version went 1 -> 2 and no field says when. The time is only in the Office store's events table (sdk/cli/arc1cli/office_work.py:61,74; concern_catalog.py:192), which no operation reads.",
   "scope": "read"
  },
  {
   "name": "office.save",
   "arguments": "{\"id\": \"owner:<32 hex>\", \"expected_revision\": \"<sha from office.get>\", \"document\": {...whole document...}}",
   "effect": "Saves the sheet as a new version; an identical document is a no-op (same version and revision).",
   "evidence": "Tried: B2 '12' -> '12.5' gave version 2 and an events row; cell values are strings.",
   "scope": "approve"
  },
  {
   "name": "documents.save",
   "arguments": "{\"id\", \"expected_revision\": int, \"blocks\": [...], \"title\"?, \"origin\"?}",
   "effect": "A new revision of the page; writes a desk_events row.",
   "evidence": "Tried.",
   "scope": "execute"
  },
  {
   "name": "intake.items + intake.batches",
   "arguments": "intake.items {\"namespace\": \"<32 hex>\", \"limit\"?, \"offset\"?, \"batch\"?, \"state\"?}; intake.batches {\"namespace\": \"<32 hex>\", \"limit\"?, \"offset\"?}",
   "effect": "An item row has no time (keys: admission, batch, bytes, decision_id, id, name, namespace, profile, sha256, working_version ...); its batch row has `created` and the scan job id.",
   "evidence": "Tried: last_touched uses item.batch -> batch.created.",
   "scope": "read"
  },
  {
   "name": "investigation.list / investigation.sheet / investigation.path",
   "arguments": "investigation.list {}; investigation.sheet {\"id\"}; investigation.path {\"claim\"}",
   "effect": "list rows carry `updated`; sheet claims (learned, unresolved) carry `created`; path steps (kind, address, direction, counts, source_state) carry no time.",
   "evidence": "Tried.",
   "scope": "read"
  },
  {
   "name": "jobs.list",
   "arguments": "{}",
   "effect": "The newest 100 jobs with created, started, finished, tool, state and request_spec; request_spec names the record worked on (for example references.item = the intake item id).",
   "evidence": "Tried: maps a references.page job to its source.",
   "scope": "read"
  },
  {
   "name": "matrix.list",
   "arguments": "{\"limit\": int, \"outcome\": str, \"query\": str}  (all optional)",
   "effect": "Every staC line that ran: {id, created, updated, program (the whole line), shape, operation 'language.run', outcome SUCCESS|EMPTY|FAILED, reason}. The only place the text of a run survives.",
   "evidence": "Tried: the lines I ran appear with their text and time; a line naming a 32-hex id ties that run to its object.",
   "scope": "read"
  },
  {
   "name": "files.story",
   "arguments": "{\"path\": \"<path inside Files>\"}",
   "effect": "One file's recorded history newest first: last changed on disk, versions kept, proposals and the owner's decisions, working copies, Trash, Agenda.",
   "evidence": "Tried: after files.propose + files.decide it read 'you applied its change', 'Graphite proposed a change: ...', 'a version was kept before a change'. files_service.py:198.",
   "scope": "read"
  },
  {
   "name": "files.find",
   "arguments": "{\"text\": str, \"kind\": str, \"days\": int, \"under\": str, \"limit\": int, \"all\": bool}  (all optional)",
   "effect": "{records:[{name, path, kind, modified, size, address '@files:<path>'}]}: the files a program could open, by name or age.",
   "evidence": "Tried: {\"text\":\".fcstd\"} found probe/part.FCStd (kind 'zip'); {\"days\":1} lists the newest.",
   "scope": "read"
  },
  {
   "name": "files.propose / files.decide",
   "arguments": "files.propose {\"path\", \"text\", \"why\"} -> {proposal, state WAITING}; files.decide {\"id\": \"<proposal>\", \"apply\": true|false}",
   "effect": "A proposed change waits for the owner; decide applies it and keeps the earlier version.",
   "evidence": "Tried: decide returned {state APPLIED, kept_version}. The journal rows carry no path.",
   "scope": "execute / approve"
  },
  {
   "name": "ledger.explore",
   "arguments": "{\"kind\": \"INSTRUMENT\"}",
   "effect": "The 33 shelf rows: key, title, view_class, destination, presentation_kind workspace|checks|operations, tool_status, setup_needed, running_jobs, queued_jobs, interrupted_jobs, slate_operations.",
   "evidence": "Tried: 33 rows. For the six native programs tool_status reads 'Use existing controls' whether or not the program is installed. workbench/explore.py:25-59.",
   "scope": "read"
  },
  {
   "name": "language.run",
   "arguments": "{\"text\": \"<a staC line>\"}",
   "effect": "Runs a read-only pipeline. Refused with 'Graphite seed/source binding is not current' whenever any of the 485 seed input files differs from the seed manifest.",
   "evidence": "Tried: refused in a window launched from the live tree while workbench/datasheet_work.py was edited and the seed not yet rebuilt; fine on the snapshot and on the live tree after the rebuild. stacy_language.py:9-13; stacy_foundation.py:366.",
   "scope": "read"
  },
  {
   "name": "programs.freecad.inspect",
   "arguments": "{\"path\": \"<.FCStd path inside Graphite Files>\"}",
   "effect": "{state READY|TOOL_UNAVAILABLE, path, sha256, bytes, tool{name, available, check_available}, label, objects, shape_names, editor_safe}. Works as a staC line.",
   "evidence": "Tried: state TOOL_UNAVAILABLE here; with a stand-in freecad on PATH tool.available true. program_freecad.py:73, 236-260.",
   "scope": "read"
  },
  {
   "name": "programs.freecad.open",
   "arguments": "{\"path\": \"<same path>\", \"expected_sha256\": \"<sha256 from inspect>\"}",
   "effect": "Starts `freecad --safe-mode <absolute file>` detached in the file's folder and returns {state STARTED, path, sha256, bytes, tool, pid}. Refuses a file that changed since inspect, a file with scripted objects, a missing editor, a missing display, and any principal other than desktop-owner.",
   "evidence": "Tried: refused 'The FreeCAD editor is unavailable on this host.'; with a stand-in and DISPLAY set returned STARTED pid 10 and the stand-in received `--safe-mode .../Files/probe/part.FCStd`. program_freecad.py:242, 261-270; program_build.py:229-240.",
   "scope": "approve"
  },
  {
   "name": "programs.inkscape.open",
   "arguments": "{\"path\": \"<.svg in Files>\", \"expected_sha256\"}  (after programs.inkscape.inspect {\"path\"})",
   "effect": "Starts `inkscape <file>`; returns {state STARTED, path, sha256, pid}. Also requires the SVG to be render_ready.",
   "evidence": "Tried: 'Install Inkscape to render or edit this SVG.' when absent; 'Open the Graphite desktop session to hand this file to Inkscape.' with no display; STARTED with a stand-in. program_vector.py:294-304, 315.",
   "scope": "approve"
  },
  {
   "name": "programs.blender.open",
   "arguments": "{\"path\": \"<.blend in Files>\", \"expected_sha256\"}  (programs.blender.inspect first; programs.blender.check runs Blender headless)",
   "effect": "Starts `blender --disable-autoexec <file>`; {state STARTED, path, sha256, tool{executable}, pid}.",
   "evidence": "Tried: 'Blender is unavailable on this host.'; with a stand-in but no display 'Open the Graphite desktop session to hand this file to a native window.'; STARTED with both. program_build.py:51, 250-262.",
   "scope": "approve"
  },
  {
   "name": "programs.godot.open / programs.godot.play",
   "arguments": "{\"path\": \"<.../project.godot in Files>\", \"expected_sha256\", \"scene\": \"res://x.tscn\"?}",
   "effect": "open: `godot4|godot --path <project folder> --editor [scene]`; play: the same without --editor, on the chosen or main scene.",
   "evidence": "Tried the refusal only: 'Godot is unavailable on this host.' Command line read at program_build.py:275-279.",
   "scope": "approve"
  },
  {
   "name": "programs.mail.open",
   "arguments": "{\"path\": \"<.eml in Files>\", \"expected_sha256\"}",
   "effect": "Starts `thunderbird -file <file>`; {state STARTED, pid, path, sha256, tool}. The display is checked before the executable.",
   "evidence": "Tried: no display -> 'Open the Graphite desktop session to hand this file to Thunderbird.'; STARTED with a stand-in. The missing-program words are 'Install Thunderbird to open this message in the full mail program.' (program_mail.py:169-189).",
   "scope": "approve"
  },
  {
   "name": "programs.cartridge.launch",
   "arguments": "{\"path\": \"<.nes in Files>\", \"expected_sha256\", \"core\": \"<id from inspect.cores>\"}",
   "effect": "Copies the image into .ledger/cartridge/<core>-<sha>/session-*/cartridge.nes, starts `retroarch --config <profile cfg> -L <core> <copy>`, holds play.lock so a second session is refused; returns {state STARTED, pid, working_copy, core, profile, log}. The original is never opened.",
   "evidence": "Tried the refusal: 'Install native RetroArch and an NES core to play this local cartridge.' Launch read at program_cartridge.py:109-145.",
   "scope": "approve"
  },
  {
   "name": "office.operation.preview",
   "arguments": "{\"id\": \"owner:<32 hex>\", \"expected_revision\": \"<sha>\", \"mode\": \"edit\"|\"export\"|\"recalculate\", \"format\": \"ods\"|\"xlsx\"|\"csv\"|\"docx\"|\"pdf\", \"sheet\"?}",
   "effect": "A reviewed plan {id, digest, losses, environment, source_state} for handing a sheet to LibreOffice.",
   "evidence": "Tried with mode edit, format ods on the Bench readings sheet. office_service.py:23,165.",
   "scope": "approve"
  },
  {
   "name": "office.operation.run",
   "arguments": "{\"plan\": \"<plan id>\", \"expected_digest\": \"<plan digest>\", \"request_key\"?}",
   "effect": "Submits a job (tool references.office.edit for mode edit) that writes the prepared copy.",
   "evidence": "Tried: job Completed in 0.7 to 1.9 s; copy at .ledger/jobs/<job>/Working_table.ods. office_service.py:170-177.",
   "scope": "execute"
  },
  {
   "name": "office.operation.result",
   "arguments": "{\"job\": \"<job id>\"}",
   "effect": "{state AVAILABLE, mode, directory, files[{name, sha256}], candidate_state READY_FOR_DESKTOP_EDITOR, losses, reviewed_environment}. The Office panel then starts the editor itself with QProcess (office_qt.py:188-194, office_runtime.editor_command).",
   "evidence": "Tried. Without a display editor_command refuses 'OFFICE_EDITOR_DISPLAY_UNAVAILABLE: use the prepared candidate on the Debian desktop'; with one it is `soffice -env:UserInstallation=<private profile> --nologo --norestore --nofirststartwizard <copy>`.",
   "scope": "read"
  },
  {
   "name": "office.candidate.preview / office.candidate.commit",
   "arguments": "office.candidate.preview {\"id\", \"expected_revision\", \"path\": \"<absolute path of the saved copy>\", \"csv\"?}; office.candidate.commit {\"plan\", \"expected_digest\"}",
   "effect": "The way back: the saved copy is compared cell by cell (changes[], losses[]) and, on commit, becomes the sheet's next version.",
   "evidence": "preview tried on the UNTOUCHED prepared .ods: it reported 4 CELL_CHANGED (B2..B5) because the cells' units (V, mA, ms) do not survive ODS. commit not run.",
   "scope": "approve"
  },
  {
   "name": "joined.session.open (and .get .pause .takeover .edit .resume .recalculate .refresh .close)",
   "arguments": "joined.session.open {\"job\": \"<a completed joined (math) job id>\"}; the others {\"id\", \"expected_revision\"}; edit adds {\"cell\": \"B<n>\", \"value\"}; refresh adds {\"note\"}",
   "effect": "The only tracked native session: a visible LibreOffice Calc window owned by a job (tool math.session, lease 540 s), a desk record of kind native_session with mode PAUSED|TAKEOVER|AUTOMATION|REFRESH_REQUIRED|CLOSED; owner edits come back through resume and refresh as a new checked revision.",
   "evidence": "Read only (native_sessions.py:8-22, 107-129, 176-234). Needs DISPLAY ('SESSION_REQUIRES_X11_DISPLAY'). The case has no such record.",
   "scope": "execute (get read; takeover, edit, refresh approve)"
  },
  {
   "name": "agenda.view, receiving.status, receiving.deliveries, copies.list, agent.list",
   "arguments": "agenda.view {}; receiving.status {}; receiving.deliveries {\"limit\": 30}; copies.list {}; agent.list {}",
   "effect": "What Today reads for 'what arrived' and 'what waits': inbox_waiting file names, held deliveries, the Agenda's waiting rows, working copies needing a look, paused or waiting assignments.",
   "evidence": "Tried: agenda.view.waiting holds the investigation 'After Hours 07'; the others are empty in the case. shell2.py:2224-2293.",
   "scope": "read"
  }
 ],
 "recipes": [
  {
   "goal": "The last N events",
   "steps": "h = dispatch('ledger.journal.status', {})['result']['head']; dispatch('ledger.journal.read', {'after': str(h - N), 'limit': N})  (N at most 200). Or ledger.context -> recent_activity.events for the last 20.",
   "tried": true,
   "result": "N=6 returned seq 189..194: documents.save, files.write, files.propose, each RECEIVED then COMPLETED; has_more false, gap false."
  },
  {
   "goal": "Events since time T",
   "steps": "No operation filters by time. Page ledger.journal.read from a cursor 200 at a time and keep rows with at > T (journal() in last_touched.py). As a staC line: activity {\"after\":\"<seq near the head>\",\"limit\":200} | where at over <T> | select seq,at,operation,state,detail",
   "tried": true,
   "result": "`activity {\"after\":\"134\",\"limit\":200} | where state=REQUEST_COMPLETED | where at over <T0> | group operation | count` gave office.save 1, language.run 2, documents.save 1, files.write 1, files.propose 1. The same line with after \"0\" and no limit returned [] because only the first 100 rows are read."
  },
  {
   "goal": "Events that touched object X, as {Field object id: last touched, by which operation}",
   "steps": "sys.path.insert(0, '<scratchpad>/tools/doer/memory-programs'); import last_touched as lt; out = lt.last_touched(kernel, principal, w.field_page.view.field)  -> {id: (time, operation, how)}. It reads jobs.list, documents.list, intake.namespaces/items/batches, investigation.list/sheet, matrix.list, ledger.journal.read, and (office_rows=True) the Office store's events table through office_service.store().catalog.db().",
   "tried": true,
   "result": "After five owner actions, newest first: intake:4967... references.page (the job's request_spec) \u00b7 intake:b60c... language.run (matrix row) \u00b7 claim:c3bf... language.run \u00b7 document:218f... documents.save (revision 2, 'HUMAN saved the writing') \u00b7 office:owner:db5f... office.save (Office store row) \u00b7 office:owner:4f35... ledger.view (journal seq 183, by tab title) \u00b7 the other claims investigation.claim at their creation \u00b7 the two calculations documents.save 11-09 \u00b7 office:owner:5a43... office.create. 0.04 s, journal head unchanged. With office_rows=False two of three sheets have no time. Also runs on the live tree (14 of 14)."
  },
  {
   "goal": "What was used last on the shelf",
   "steps": "views = [(row[0], row[7]) for row in explore.VIEWS]; rows = lt.journal(kernel, principal); lt.programs_touched(rows, views)  -> {shelf key: (time, 'operation STATE', seq)} by matching each journal operation against the program's operation prefixes.",
   "tried": true,
   "result": "app:references 21:49:46 references.page Completed \u00b7 app:documents documents.save \u00b7 app:office office.save \u00b7 app:brain brain.stop (11-09) \u00b7 app:investigations investigation.claim (11-09). Operations no shelf program owns: intake.*, language.run, ledger.open, ledger.session.keep, ledger.view."
  },
  {
   "goal": "New since the Field was last looked at",
   "steps": "dispatch('ledger.awareness', {'consumer': 'field'}) -> backlog and cursor; read the new rows with ledger.journal.read {'after': str(cursor)}; when shown, dispatch('ledger.awareness.catch_up', {'consumer': 'field', 'limit': 200}) (repeat while backlog > 0).",
   "tried": true,
   "result": "First call: cursor 0, backlog 185. After catch_up: CURRENT, cursor 185. After one office.save and one language.run: backlog 4; the rows after the mark grouped to {office: 1, language.run: 1}. The cursor is stored in the workspace database, so it survives a restart (not tried across a restart)."
  },
  {
   "goal": "How long the owner was away, and what the last session ended on",
   "steps": "opens = dispatch('ledger.activity', {'query': 'ledger.open', 'limit': 50})['result']['events'] (one READY row from origin DESKTOP per launch); the row at seq opens[-1].seq - 1 is the last thing of the previous session; rows between two ledger.open rows are one session.",
   "tried": true,
   "result": "ledger.open at seq 1 (11-09 11:17:19) and seq 182 (this launch); the previous session ended on seq 181 brain.stop REQUEST_COMPLETED; away 3.4 days. Limit: the query filter reads at most 200 matches per call."
  },
  {
   "goal": "What is in use now",
   "steps": "dispatch('ledger.context', {}) -> desktop.surface, desktop.workspace (front tab's class), active_jobs; dispatch('ledger.explore', {'kind': 'INSTRUMENT'}) -> running_jobs/queued_jobs per program; in the window: [type(w.tabs.widget(i)).__name__ for i in range(w.tabs.count())] and w.tabs.snapshot(); w._field_active and w.field_page.view.selected().id for the Field.",
   "tried": true,
   "result": "A page in front: {'surface': 'workspace', 'workspace': 'DocumentsTab'}; the Field in front: {'surface': 'workspace', 'workspace': None}; Home: surface 'home'. snapshot = {\"tabs\": [{\"kind\": \"DocumentsTab\", \"pinned\": false}], \"active\": 0}: no page id, though the tab object has document_id. Shelf states after opening the FreeCAD room: app:freecad 'in use'."
  },
  {
   "goal": "Open a native program in its full window with a file, from code",
   "steps": "from full_window import full_window; ok, receipt = full_window(kernel, operator(), 'freecad', 'probe/part.FCStd')  -> programs.freecad.inspect {path} then programs.freecad.open {path, expected_sha256}. Keys: freecad, inkscape, blender, godot (path = .../project.godot), mail, cartridge (extra core=...). Path is relative to files_service.root(kernel) = <workspace>/Files.",
   "tried": true,
   "result": "Nothing installed: (False, 'Blender is unavailable on this host.') and the like. Stand-ins on PATH, no display: (False, 'Open the Graphite desktop session to hand this file to ...'). Stand-ins and DISPLAY: (True, {'state': 'STARTED', 'path': ..., 'sha256': ..., 'pid': 8}); command lines received: `inkscape <file>`, `blender --disable-autoexec <file>`, `thunderbird -file <file>`, `freecad --safe-mode <file>`. A principal other than desktop-owner: 'A native action needs desktop owner approval.' No file: no operation accepts that."
  },
  {
   "goal": "The same through the room, as the owner does it",
   "steps": "Field, P, select app:freecad, Enter (opens FreeCADRoom through field_page.open_object -> explore_qt.open_instrument). room = w.tabs.currentWidget(); room.source.setText('probe/part.FCStd'); room.inspect(); wait until not room.busy; the button with accessibleName 'Open in FreeCAD' (text 'Full app \u2197') is enabled only when room.tool_ready(); clicking it is room.bound('open').",
   "tried": true,
   "result": "Not installed: button disabled, status 'Document inspected \u00b7 geometry check unavailable for this source.'; forcing room.bound('open') shows 'The FreeCAD editor is unavailable on this host.' With the stand-in: one click, no dialog, status 'FreeCAD process started \u00b7 PID 15', the details gain 'FreeCAD process started \u00b7 PID 15 / Source probe/part.FCStd'. Screenshot: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs/out/doer_freecad_room_started.png"
  },
  {
   "goal": "How a file changed in the native program comes back",
   "steps": "Nothing watches. After the program saves: programs.<key>.inspect {path} returns the new sha256; any action still carrying the old hash is refused; files.story {path} shows 'last changed on disk'.",
   "tried": true,
   "result": "The stand-in appended to the file: inspect sha 9738... -> 834f...; programs.freecad.open with the old hash -> 'The selected file changed. Inspect it again before starting a FreeCAD action.'; the room kept showing the old hash and 'process started' until Inspect was pressed again; files.versions is empty (no Graphite version is kept of a native edit); no job, no active_jobs entry, only the two journal rows programs.freecad.open RECEIVED/COMPLETED."
  },
  {
   "goal": "Hand a reviewed sheet to the full spreadsheet and take it back",
   "steps": "g = office.get {id}; plan = office.operation.preview {id, expected_revision: g.revision, mode: 'edit', format: 'ods'}; job = office.operation.run {plan: plan.id, expected_digest: plan.digest}; wait for jobs.get state Completed; r = office.operation.result {job}; copy = r.directory + '/' + r.files[0].name; start the editor with office_runtime.editor_command(copy, r.directory + '/desktop-editor') (the Office panel does this with QProcess); after save and close: c = office.candidate.preview {id, expected_revision, path: copy}; office.candidate.commit {plan: c.id, expected_digest: c.digest}.",
   "tried": true,
   "result": "Ran up to candidate.preview (LibreOffice 24.2 is installed here; no display, so the editor itself was not started). The prepared copy appeared in 0.7 to 1.9 s. candidate.preview of the untouched copy already lists B2, B3, B4, B5 as CELL_CHANGED: unit 'V'/'mA'/'ms' became ''. commit was not run."
  },
  {
   "goal": "Wire F on the shelf in the live tree",
   "steps": "FieldView.full_asked exists (field_qt.py:52) and is emitted on F for kind 'app' (field_qt.py:233-234). Connect it in FieldPage.__init__ next to do_asked (field_page.py:42). For the six native keys open the room (open_object) and, when a file is known, room.source.setText(path); room.inspect(); the room's own Full app button or room.bound('open') does the rest.",
   "tried": true,
   "result": "On the live tree (0.4.0, cb72be5): F on app:freecad emitted full_asked ['app:freecad'] and nothing else happened; status bar empty; field_do.steps_for(app:freecad) returns one generic read step."
  }
 ],
 "gaps": [
  "The journal cannot say which record a request was about: rows carry no arguments and no object ids (activity.py:44-51), and the work trail is metadata only by design (work_trail.py:280). 'Events that touched X' has to come from each record's own store.",
  "Opening or looking at a thing is not recorded per object. Reads are observer operations; the only trace is ledger.view FOCUSED with the tab's title (qt_app.py:3559), and a DocumentsTab is always titled 'Documents', a PDF 'Technical PDF', the assignments room 'Investigations'. Only a sheet's tab carries its title.",
  "A sheet's last-saved time is not reachable through any operation. office.list and office.get return version and revision only; the rows (at, operation, object_id) sit in the Office store's events table in <config>/concern/catalog.sqlite3 (sdk/cli/arc1cli/concern_catalog.py:130,192; office_work.py:61,74) with no reader.",
  "ledger.context does not know the Field. control_qt.py:447 publishes surface 'home' or 'workspace' only, and the Field's selected sheet is published nowhere; host.selection_context stays None.",
  "session.json does not keep which page was open: a DocumentsTab is saved as {kind, pinned} (tried), so 'where I left off' restores the Documents room, not the page. Today's Continue card lists files only (session recent, _viewer_recent) and is empty in the worked case.",
  "No program can be opened in its full window without a file: every open/launch operation requires path and expected_sha256.",
  "A program started by programs.*.open is not tracked: no job, no record, no entry in active_jobs; the pid is only in the receipt. Nothing tells Graphite when it exits or that the file changed, and no version of the file is kept before or after.",
  "The shelf cannot say whether a native program is installed. ledger.explore gives the six native rows tool_status 'Use existing controls' either way; only programs.<key>.inspect on a real file, or the module helpers (program_freecad._tools :73, program_build._tool :51, program_cartridge.installed_tools :67, shutil.which for inkscape and thunderbird), know.",
  "In the live tree F on the shelf emits full_asked and nothing is connected (tried); field_do.BY_KIND has no entry for kind 'app'.",
  "The Files worksheet's 'Full spreadsheet' and the Office panel's editor start LibreOffice with QProcess from the widget, not through the Kernel, so neither leaves a journal row or can be offered as an operation line.",
  "The .ods hand-over loses cell units: an untouched round trip shows four changed cells in office.candidate.preview. Committing it would strip the units the calculations read.",
  "No operation lists native sessions (joined.session.get needs the id; joined.list needs a problem), and ledger.navigate's destination list has no program rooms, so a room cannot be opened by an operation line; it is opened by window code (program_rooms_qt.show, explore_qt.open_instrument).",
  "The return thread's `updated` moves only when its content changes, so it is not a 'last closed' time; the reliable session boundary is the ledger.open row.",
  "The 'stacy' awareness consumer is caught up by the window every 750 ms from its first tick, so it cannot serve as 'since you were away'; a consumer with its own name must be used."
 ],
 "advice": "Build on these; add nothing that already exists.\n\n1. Recent marks in the Field: lift last_touched() from /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs/last_touched.py into field_source.Reader. Pages cost nothing extra: documents.list rows already carry updated and last_change, and Reader.newest already sorts by `updated` (field_source.py:113). Claims have created, investigations updated, jobs their times, sources their batch and their jobs. For sheets choose one: read the Office store rows directly from field_source (office_service.store().catalog.db(); field_source.py is not a seed input), or add `updated` to office.list rows in sdk/cli/arc1cli/office_work.py (cleaner, but that file is a seed input).\n\n2. Shelf \"used last\": programs_touched() over ledger.journal.read with explore.VIEWS prefixes; it needs no new record. For \"new since you last looked\" use ledger.awareness / ledger.awareness.catch_up with consumer \"field\" (not \"stacy\").\n\n3. F on the shelf: connect view.full_asked in FieldPage.__init__ (field_page.py:42 is where do_asked is connected). Honest behaviour: for freecad, inkscape, blender, godot, mail, cartridge open the room (open_object) because a file is required; if the owner has one candidate, fill room.source and call room.inspect(), and let the room's Full app button be the press. For every other key say in the status line that its room is the program. Do not promise a window without a file.\n\n4. As doer steps: add an 'app' entry to field_do.BY_KIND (field_do.py:181). Enumerate from records: files.find {\"text\":\".fcstd\"} (or .svg, .blend, project.godot, .eml, .nes) gives the candidates; per file one read step `programs.freecad.inspect {\"path\":\"...\"} | select state,tool.available,editor_safe,sha256` (runs as staC, tried) and one write step `/programs.freecad.open {\"path\":\"...\",\"expected_sha256\":\"...\"}` with scope 'approve', which your existing face.stage / Run in Talk already holds for the owner. The check that the job is done is a second inspect whose sha256 differs from the receipt's.\n\n5. Coming back from a full program: keep the receipt (key, path, sha256, pid) on the page; while /proc/<pid> exists show the sheet as running; when it is gone re-inspect and say \"changed\" when the hash moved. That is the whole return path available today. If a version should be kept first, that needs a decision (copies.start or a kept version), which I did not try.\n\n6. For a sheet's full window use the Office chain (office.operation.preview mode edit -> run -> result -> editor -> office.candidate.preview -> commit) rather than inventing one; prefer format xlsx or test it, because ods drops units.\n\n7. Seed: language.run refuses whenever a seed input differs from the manifest. Seed inputs include shell2.py, qt_app.py, control_qt.py, ledger_control.py, activity.py, engineering_kernel.py, explore.py, program_rooms_qt.py, program_build.py, program_freecad.py, office_service.py, sdk/cli/arc1cli/office_work.py and typed_pipeline.py; field_*.py, context_menu.py and programs_qt.py are not. After touching an input run `python3 tools/package_graphite.py --rebuild-seed` before any window check, or every staC line in the rehearsal fails for a reason that has nothing to do with your change.\n\n8. If the Field should count as \"where I am\", extend the published context at control_qt.py:447 (surface 'field' plus the selected id); it is a three-line change in a seed input.",
 "not_checked": "Not tried, read only: a real FreeCAD, Blender, Godot, Inkscape, Thunderbird or RetroArch (none is installed; the STARTED receipts came from stand-in shell scripts named after them, with DISPLAY set to a display that does not exist); programs.godot.open/play and programs.cartridge.launch beyond their refusals; starting the LibreOffice editor window, 'Full spreadsheet' and 'Return to sheet' (no display); office.candidate.commit; the whole joined.session.* Calc session; whether Stop all jobs reaches a program started by programs.*.open (it is detached with start_new_session and is neither a job nor a QProcess child, so I expect not; qt_master_stop.py:61); 'While Graphite was closed' on a real assignment stepped by the service; the awareness cursor across a real restart; ledger.session.keep at close; Today drawn on screen; the Work trail and Organizer rooms' own widgets (work_trail_qt.py, organizer_qt.py were only skimmed); journey.py and home_qt.py's Control Center (they describe the older hardware project and read no owner activity); object_context (Object Glass: components, nets, jobs, files, requirements; ledger.object.current returned EMPTY); format xlsx for the Office hand-over; behaviour with more than 200 journal rows per query or more than 100 jobs. The live tree changed three times during the work; everything was run on the 1d45b9c snapshot except live_check.py, so anything the 0.4 commits changed in shell2.py, field_page.py or field_source.py beyond what is cited was not re-tested."
}