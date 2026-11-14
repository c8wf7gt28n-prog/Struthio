{
 "verdict": "The Field keeps the project's structural rules: every read goes through Kernel.dispatch as the owner with read-scope observer operations, the registry, settings and adapters still match the record, the menus contract holds, F9 is free, and the test modules and UI checks I ran behave the same as on the delivered program. It is not yet safe to trust what it says. The worst finding is that its main signal is wrong in both directions: an unchanged imported sheet is marked RECHECK forever, a finding whose source really changed is drawn as an open question with a solid \"supports\" wire, and a record that could not be read is drawn CURRENT in green. It also silently drops everything past the newest 100 documents, so the oldest calculations vanish first. Outside a large window at the default text size it cuts most of its words, and from 18 pt on a 1366x768 screen the last column is off-screen with no sideways scroll. The \"writes nothing\" claim holds on the worked case but not when an Office document was copied from a notebook or when a read refuses. Fix the state mapping and the paging in workbench/field_source.py before building more on top; the layout and journal items can follow.",
 "defects": [
  {
   "title": "Unchanged sheets are marked RECHECK forever, and Office writing documents are drawn as SHEET",
   "severity": "wrong-result",
   "reproduction": "Run: cd /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work && venv/bin/python -B /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_office_kinds.py (real window, disposable copy of the worked case, holds on). It imports a 3-line CSV through office.import.preview/commit and copies a notebook into Office with office.from.notebook. office.get then reports source_state UNCHANGED_ORIGINAL (expected and current sha256 equal) and UNCHANGED_NOTEBOOK_SNAPSHOT. The Field shows both as kind=sheet, state=recheck, and the head says '5 sheets ... 2 to recheck'. The notebook copy has listing kind 'document' but is tagged SHEET under TABLES. In /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_real_scale.py, 29 unchanged imported CSVs gave '29 to recheck'.",
   "expected": "A sheet whose original is byte-for-byte unchanged, or a working copy with no source, reads CURRENT. Only the STALE_* states ask for a recheck, and the *_UNAVAILABLE states read as unavailable. An Office row of kind 'document' is not called a sheet.",
   "where": "workbench/field_source.py:21 (AGREES) and workbench/field_source.py:75",
   "suggested_fix": "Map the words office_service.source_state really returns (workbench/office_service.py:36-58). Treat UNCHANGED_ORIGINAL, WORKING_COPY_OR_DERIVATIVE, UNCHANGED_NOTEBOOK_SNAPSHOT and UNCHANGED_BOOK_SNAPSHOT as agreeing; ORIGINAL_UNAVAILABLE and DERIVATIVE_SOURCE_UNAVAILABLE as UNAVAILABLE; STALE_* and PDF_SOURCE_REVIEW_REQUIRED as recheck. Use row['kind'] ('table' or 'document') from office.list to choose the object kind and role.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A finding whose source changed is not shown as recheck: it becomes OPEN QUESTION with a solid 'supports' wire",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_states.py the same way. Through the Kernel on the disposable copy it creates a page, an investigation, add_source document:<id>, a FINDING claim and SUPPORTS evidence. The Field shows FINDING, current, wire 'supports'. It then saves the page with changed words and calls investigation.refresh. The record now says learned=[], unresolved=[('Rail A draws 2 W.', 'UNKNOWN', 'NEEDS_REVIEW')], and the path step has counts=False, source_state='CHANGED'. The Field shows that same claim as kind=question, tag 'OPEN QUESTION \u00b7 OPEN', its wire still ('supports', stale=False), and the head's '1 to recheck' counts only the condition card. Screenshot: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/states/field_condition_selected.png",
   "expected": "The finding stays a FINDING, reads RECHECK, is counted in 'to recheck', and the wire from the changed source is the dashed stale wire. This is the case the model's `stale` flag exists for.",
   "where": "workbench/field_source.py:107 (through :112, and the stale flags at :119 and :123)",
   "suggested_fix": "investigations.sheet puts every NEEDS_REVIEW claim into 'unresolved' (workbench/investigations.py:246-247), so `unknown` is always true for them and the STATE_RECHECK branch at line 112 can never run. Decide from the claim itself: role == 'QUESTION' is an open question; review == 'NEEDS_REVIEW', or any path step with counts False or source_state 'CHANGED', is STATE_RECHECK with that step's wire stale; evidence UNKNOWN or CONFLICT with review CURRENT is open or held.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A record the reader could not read is drawn CURRENT with a green mark",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_refusal.py. It makes office.get refuse for every sheet (office_service.get raises ValueError('OFFICE_RECORD_DAMAGED')). The Field still shows '3 sheets', each SHEET \u00b7 CURRENT, nothing to recheck. The only sign is a 9-second status line: 'Field \u00b7 3 of its readers did not answer: office.get'. Over two showings the workspace journal went 182 -> 188 rows and audit 60 -> 66 (office.get DENIED_OR_FAILED).",
   "expected": "What the module's own docstring says ('an operation that ... refuses leaves its kind out of the Field'), or the sheet drawn as unavailable. Never CURRENT.",
   "where": "workbench/field_source.py:68 (with :76); the same pattern for documents.get at workbench/field_source.py:83 (with :94)",
   "suggested_fix": "When self.call(...) returns None for a per-record read, add the object with state UNAVAILABLE and a fact such as 'could not be read', or skip it. Take '' out of AGREES for records that are expected to carry a source_state.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Past 100 documents the Field silently shows only the newest 100; the calculations vanish first",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_real_scale.py. It creates 105 pages with documents.create on the disposable copy; paging documents.list confirms 108 documents. The Field's head reads '3 sources \u00b7 3 sheets \u00b7 100 pages \u00b7 4 findings \u00b7 1 open question'. Calculations shown: 0. Both calculation reports and the conclusion page of the worked case are gone, with no notice and nothing in `refused`.",
   "expected": "Every document, or a plain statement that 100 of 108 are shown. The oldest work, which holds the derivations, must not be the first to disappear.",
   "where": "workbench/field_source.py:82",
   "suggested_fix": "documents.list defaults to and caps at limit 100, newest first (workbench/project_desk.py:22 and :277-278). Page with limit/offset until a short page comes back. Do the same at workbench/field_source.py:57: intake.items defaults to 100 per namespace and returns 'total', which is ignored (workbench/intake_service.py:434-440). conditions.list is cut to 100 inside its handler (workbench/conditions.py:206). If a cap stays, say so in the head.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A stale condition is titled with a Python dict",
   "severity": "wrong-result",
   "reproduction": "Same probe_states.py run. conditions.create binds a total to a page; saving the page with a changed input makes conditions.list return state STALE with result {'text': '5 W', 'unit': 'W', 'value': '5'}. The Field's sheet title, the foot and the accessible description all read: {'text': '5 W', 'unit': 'W', 'value': '5'} (description: \"Open question: {'text': '5 W', 'unit': 'W', 'value': '5'}. State: recheck. Fed by Probe page.\"). Screenshot: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/states/field_condition_selected.png",
   "expected": "Words the owner wrote or can read, for example 'Total 5 W no longer matches the page', and not the tag OPEN QUESTION for a calculation that went stale.",
   "where": "workbench/field_source.py:131",
   "suggested_fix": "A condition summary's result is {value, unit, text} (workbench/conditions.py:141-144). Use row['result']['text'], with row.get('reason') as the fact line, and give it a kind or tag of its own.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Words are cut and columns fall off the right edge at larger text sizes and on a 1366x768 screen",
   "severity": "rule-conflict",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_access.py (sets reading.ui_pt through ledger.settings.set, renders, and logs every elision; log at /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/access/log.txt, pictures beside it). Worked case, 1920x1200: at 14 pt 1 of 79 strings cut; at 18 pt 20 of 45 cut and 21 of 22 fact lines not drawn; at 20 pt 23 of 44 cut, all facts gone; at 28 pt 29 of 44 cut and the OPEN column is cut by the right edge. 1366x768 at the default 14 pt: 28 of 44 cut, all 22 facts gone, every title one line of about 9 characters ('07 Settle\u2026', 'OPEN QUE\u2026'), state words dropped. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_view.py part 3: a 666 px view at 18 pt puts the last column at x 660..792, wholly off-screen, and that is the column the Field opens on. Fonts drawn are 12-20 px at 14 pt and 20-34 px at 28 pt, about 168%.",
   "expected": "The project's own rules: words whole (tools/ui_fit.py), text reaching 200% at 28 pt and 'never shrunk to fit a window' (workbench/reading_profile.py:10, workbench/shell2.py:277-279), smallest metadata 14 px at the default size. The selected sheet must always be reachable on screen.",
   "where": "workbench/field_model.py:228 (place: sheet_w floor at :240 with no sideways scroll, sheet_h squeezed at :246); workbench/field_qt.py:282 (one title line), :288 (facts dropped), :69 (scale clamp)",
   "suggested_fix": "Give a sheet the height its wrapped title and facts need and let the surface scroll, instead of squeezing rows to fit. When the width cannot hold every column at a readable minimum, scroll sideways and make _reveal (workbench/field_qt.py:99-103) reveal horizontally too, or show fewer ranks at once. Take the scale from ui_pt/14 without the 2.0 clamp, and floor the small mono sizes at 14 px.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Showing the Field does write to the journal in two ordinary situations",
   "severity": "rule-conflict",
   "reproduction": "(a) probe_office_kinds.py: with one Office document copied from a notebook present, three showings moved the workspace's activity_journal 196 -> 202 and audit 67 -> 70 (rows: desktop-owner notebook.get REQUEST_RECEIVED / REQUEST_COMPLETED). That is 2 journal rows and 1 audit row per such document per showing. (b) probe_refusal.py: every refused read writes 1 journal and 1 audit row per call per showing (182 -> 188, 60 -> 66 over two showings).",
   "expected": "What workbench/field_source.py:3 and the comment at workbench/activity.py:11 promise: showing the Field fills no timeline.",
   "where": "workbench/field_source.py:68 (office.get runs office_service.source_state, workbench/office_service.py:44-52, which dispatches notebook.get, notebook.resolve and book.contents; none is in activity.OBSERVER_OPERATIONS)",
   "suggested_fix": "Either add the nested reads (notebook.get, notebook.resolve, book.contents) to OBSERVER_OPERATIONS after checking nothing keys on them, or have the Field take origin and state without the nested dispatch. For refusals, remember what refused and do not ask again on every showing. Correct the docstring either way.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "The Field opens on what needs the owner but does not scroll to it, and every return resets the scroll to the top",
   "severity": "wrong-result",
   "reproduction": "probe_view.py part 2: a Field of 30 findings where number 27 needs a recheck. The Field selects it (first()), but its sheet sits at y 3194..3282 while the visible body is y 69..869 and scroll is 0. Visible when the Field opens: False. Picture: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/first_selection_below_fold.png. The only way to bring it into view is an arrow key, which moves the selection off it. The same reset runs each time F9 brings the Field back after opening a page, so the kept selection can be off-screen.",
   "expected": "Sections 70-72, 'without losing place': the selected sheet is in view when the Field appears and when the owner comes back to it.",
   "where": "workbench/field_qt.py:48",
   "suggested_fix": "In set_field, keep the old scroll when the selection was kept, then run self._layout(); self._reveal(). Do the same in a resizeEvent.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Every intake item is drawn as an 'admitted source', CURRENT, whatever its admission",
   "severity": "wrong-result",
   "reproduction": "Read only; intake.import and intake.review are jobs, held. intake.items with only {namespace} returns items of every admission: UNREVIEWED, ACCEPTED, HELD, REJECTED, REVOKED (workbench/intake_service.py:35 and :434-440). The Field passes no state, gives every item the role 'admitted source', and gives STATE_CURRENT to any item that is not in references.sources, because readable == '' is in AGREES.",
   "expected": "Only ACCEPTED items are called admitted sources. Unreviewed, held, rejected or revoked files are left out or drawn in their own state.",
   "where": "workbench/field_source.py:57 (role at :62, state at :63)",
   "suggested_fix": "Ask for state 'ACCEPTED', or map item['admission'] to the role and state: unreviewed and held wait for the owner; rejected and revoked are not sources.",
   "confirmed_by": "read-it"
  },
  {
   "title": "Text on receded sheets and the stale wire fall below the project's 4.5:1 reading contrast",
   "severity": "rule-conflict",
   "reproduction": "probe_view.py part 4 renders a Field with a finding selected and samples pixels on a sheet three steps away (ground #111513): kind tag ink #656154 = 2.97:1, title #797669 = 4.04:1, identity line #565247 = 2.36:1, at 12-17 px. A stale 'recheck' wire between two sheets that do not touch the selection: brightest pixel #2e2010 on #080a09 = 1.26:1, one pixel wide. Picture: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/contrast_probe.png",
   "expected": "The project measures lettering and quiet lettering at 4.5:1 or better (tools/check_desk_ui.py:630). A wire that says 'recheck' should be findable without first selecting one of its ends.",
   "where": "workbench/field_qt.py:17 (DEPTH_INK), with the wire strength at workbench/field_qt.py:229 and :236",
   "suggested_fix": "Floor the receding: keep text at 0.75 of its ink or more (TEXT, QUIET) and stop using FAINT below full strength. Recede with the sheet's fill and edge rather than its words. Draw stale wires at full strength whatever the selection.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "On a narrow sheet recheck, open and held share one mark, and 'unavailable' differs from them only by colour",
   "severity": "rough-edge",
   "reproduction": "When a sheet is too narrow for the state word (every sheet at 1366x768 at the default size, and at 18 pt and up on 1920x1200; see /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/out/access/field_1366x768_14pt.png) only the 7 px square is drawn. CURRENT is a filled square. RECHECK, OPEN and HELD are the same hollow amber square. 'unavailable' is the same hollow square in grey.",
   "expected": "Each state keeps a mark that differs in shape, not only in hue, when its word gives way.",
   "where": "workbench/field_qt.py:266 (word dropped), :272-275 (the mark)",
   "suggested_fix": "Give each state its own glyph when the word is dropped (for example a hollow square for open, a half-filled one for recheck, a crossed one for held, a dash for unavailable), or keep a one-letter word.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "One refresh is synchronous on the UI thread: about 0.85 s at today's record limits",
   "severity": "rough-edge",
   "reproduction": "probe_real_scale.py on the real Kernel. Worked case: 19 dispatches, 108-231 ms. With 100 documents shown, 32 Office documents (the store's own limit, OFFICE_DOCUMENT_COUNT_LIMIT) and 65 claims: 206 dispatches, 841 ms inside show_field. Per call: office.get about 8.4 ms, documents.get 2.8 ms, investigation.path 3.7 ms. Dispatch count is 5 + 2 per namespace + sheets + documents + investigations + claims. Pressing F9 while the Field is showing reads everything again. Painting: 36 ms at 200 objects; 179 ms per paint and per arrow key at 820 objects (fake kernel, /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/probe_scale.py), because every sheet is painted whether visible or not.",
   "expected": "F9 answers at once. A workspace with 500 sheets cannot exist today (limit 32), but if that limit is lifted, 500 x 8.4 ms is about 4.2 s of frozen window for office.get alone.",
   "where": "workbench/field_page.py:47 (read_field called from refresh on the UI thread); workbench/field_qt.py:167-170 (no culling)",
   "suggested_fix": "Read off the UI thread, or show the last Field and replace it when the read returns. Skip the re-read when F9 is pressed while the Field is already in front. In paintEvent, skip sheets and wires whose rectangles miss the body.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "User-visible strings that name internal identifiers",
   "severity": "rough-edge",
   "reproduction": "Seen in the runs above or read from the literals: (1) status line 'Field \u00b7 3 of its readers did not answer: office.get', an operation name, and the count is failed calls, not readers; (2) 'Field \u00b7 could not open <title>: <exc>' passes the raw exception text, such as OFFICE_ACTUAL_OWNER_PROFILE_REQUIRED or a KeyError repr; (3) every sheet carries 'revision 69dada6fef72', a content-hash prefix; (4) wire label 'checked check_failed', where the underscore is not replaced as it is elsewhere; (5) state constants lowercased straight onto the sheet ('located but unavailable', 'unknown \u00b7 needs review'); (6) fallback titles are record ids (row['id'], item['id'], claim['id']); (7) accessible description has a double full stop: 'Finding: Startup ran 30 ms past the Rev B limit.. State: current.' None of the four new files contains Ledger, Slate or Hatch.",
   "expected": "Words the owner would use; identifiers stay in the record.",
   "where": "workbench/field_page.py:52 and :109; workbench/field_source.py:73, :123, :61, :113, :75; workbench/field_qt.py:61",
   "suggested_fix": "Name what could not be read in plain words ('3 sheets could not be read'). Drop the hash-prefix fact for sheets, or show the saved date. Replace underscores in outcomes. Strip a trailing full stop before composing the description.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Choosing the Clean desk while the Field is showing leaves its scan texture on until the next F9",
   "severity": "rough-edge",
   "reproduction": "probe_access.py part C: with the Field showing, boss_qt.choose_art(w, 'clean') (Arrange \u25b8 desk art \u25b8 Clean). The texture flag stays True and the scan lines are still painted (pixel check). After a_field.trigger() the flag is False and the lines are gone.",
   "expected": "Clean takes effect at once, as it does for the art panels that choose_art refreshes.",
   "where": "workbench/field_page.py:41",
   "suggested_fix": "Read desk_art in FieldView.paintEvent through the host, or have boss_qt.choose_art also update host.field_page.view.texture and repaint.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "While anything is waiting, Tab and Shift+Tab never leave the Field; with exactly one waiting they do nothing",
   "severity": "rough-edge",
   "reproduction": "probe_view.py part 1: with nothing waiting, Tab moves focus to the next widget; with one waiting object, focus stays on FieldView after Tab and after Shift+Tab. probe_access.py part B on the worked case (one open question): Tab, Tab, Shift+Tab leave the selection and the focus unchanged. PageDown, End and Space also do nothing. The only keyboard way to the rest of the window is Esc, which also closes the Field.",
   "expected": "A keyboard-only owner can move from the Field to the navigator, the writing line or the Activity pane without closing the Field, and can page through a tall Field.",
   "where": "workbench/field_qt.py:123 (focusNextPrevChild), keys at workbench/field_qt.py:106-121",
   "suggested_fix": "Let Tab leave when the selection is already the last waiting object (or use another key, such as N / Shift+N, for 'next waiting'). Add PageUp, PageDown and End.",
   "confirmed_by": "ran-it"
  }
 ],
 "checked_and_fine": [
  "Worked case, journal and side effects: three showings changed no row count in any table of the workspace or profile databases (activity_journal 182 -> 182, audit 60 -> 60) and no non-database file; only transient -wal/-shm files came and went (probe_journal.py, file hashes plus per-table counts before and after, with an idle baseline).",
  "Empty workspace: the first showing in a fresh profile creates four empty Office tables (office_documents, office_drafts, office_history, office_plans) in the profile's concern/catalog.sqlite3. That is office.list's own schema step; no rows. Later showings change nothing.",
  "Esc from the Field with no tab open lands on Home, and Home rewrites session.json (last_surface). Traced to empty_workspace_qt.show_home -> set_view_preference; show_field/leave_field alone leave session.json byte-identical.",
  "office.list / office.get added to OBSERVER_OPERATIONS: the set is consulted only at engineering_kernel.py:390 and :508; no code, test or timeline word keys on those two names (grep over workbench, sdk, tools, tests_integrated; tail_words has no entry for them).",
  "20 tests_integrated modules, one per process, on /home/user/Struthio and on a pristine export of aa0ce07: identical outcomes. 17 pass on both (agent_loop, browse, conditions, context_menu, documents, explore, frame, launcher, network_watch, operations, related, release_check, return_thread, service_lifecycle, tool_selection, vocabulary, writing_line). test_graphite (3 failures), test_desk (6) and test_paper (4) fail with the same test names on both trees. No new failure.",
  "Wording tests: test_graphite's two scans (no 'Ledger & Slate' in workbench literals; no Ledger/Slate/Hatch in frame modules) pass on both trees. Its third guard, test_public_name_and_internal_identities, already fails on the delivered program at its version assertion ('0.2a13' != '0.1'). The four new files contain none of the forbidden words.",
  "One-dispatcher rule: every read in field_source.py goes through Reader.call -> kernel.dispatch(operation, arguments, principal) (field_source.py:36-42) with engineering_kernel.operator() (field_page.py:46-47), the same convention as office_qt. All 11 operations have scope 'read' and are observers. I read each handler: none submits a job or starts a worker or child process, and the Kernel.launch / Kernel.submit / Popen holds never tripped in any run.",
  "tools/check_release.py on the Field tree: registry PASSED / MATCHES (760 operations, 113 job tools, schema digest equal to the record), settings PASSED (49), adapters PASSED (760 served), payload_privacy PASSED. Runtime FAILED as expected (EDITED_SOURCES_NOT_YET_PACKAGED: .gitignore, workbench/activity.py, menus2.py, qt_app.py changed).",
  "tools/check_explore_ui.py and tools/check_navigation_ui.py: PASSED on the pristine export and on /home/user/Struthio with identical check lines, including 'Repeated menu rebuild preserves original menu objects, QAction identities and keyboard shortcuts'. Captures went to my own folder.",
  "F9 is free in the Qt window: exactly one QAction ('Field', WindowShortcut) and no QShortcut is bound to it. The other function keys in use are F1, F3, F5, F7, F8, F10, F11, F12. The only other F9 in the tree is the old Tk program (workbench/app.py:389), a separate window. F9 opened the Field with focus in the window, the writing line and the navigator.",
  "After two menus2.rebuild calls the Field action is the same QAction, in the same QMenu, exactly once in Arrange, directly after Today. menu_groups['View'] and ['Options'] are one QMenu object, on the pristine tree as well.",
  "Synthetic scale through the reader's own interface (fake kernel; 300 sheets, 300 documents with 150 derivations, 3 x 60 claims, 40 sources = 820 objects, 810 links, 790 dispatch calls): read_field 19-27 ms, Field construction 14-21 ms, place() 0.15-0.29 ms, depth() 0.12 ms, one paint at 1368x1010 179 ms.",
  "No QTimer, QPropertyAnimation, startTimer or singleShot in the four new files (grep). The surface is static.",
  "Accessible name is set ('Field: the work in this workspace and what feeds what') and the accessible description changed with each of four selections, naming kind, title, state and what feeds what.",
  "Not colour alone: the stale wire is dashed as well as amber; the selection has a 2 px edge plus corner ticks; current is a filled square against hollow ones.",
  "Clean desk art is honoured when the Field is shown (texture flag False and no scan lines in the pixels).",
  "tools/ui_fit.py cannot see the Field's words: whole_words(view) returned [] with 0 measurable widgets under the view, because the text is painted. Reading sizes were therefore checked by rendering and logging every elision.",
  "Typing 'field' in the writing line finds the action ([('Field', 'F9')], from the capture harness).",
  "The repository was left untouched by me (git status --short and --ignored both empty). HEAD moved to fe99961 during the review (a .gitignore-only commit from the orchestrating session); the Field files are identical to 63d9d2d."
 ],
 "could_not_check": [
  "What a screen reader actually announces when the selection changes: the offscreen platform has no accessibility bridge, so I could only confirm that the name and description properties are set and change.",
  "The cost of references.sources with large, currently readable PDFs. By reading, it reads and SHA-256s every indexed original on each showing (reference_service.py:484-490 -> current -> intake.eligible -> Vault.read, intake_files.py:53-58), on the UI thread. The restored case's three small sources report REFERENCE_INDEX_BINDING_STALE_REBUILD_REQUIRED, and admitting larger files needs a job (held), so I have no timing for it.",
  "Intake items that are unreviewed, held, rejected or revoked, and namespaces with more than 100 items: both need intake jobs, so those two findings rest on reading the handler.",
  "Whether F9 reaches the Field while an embedded game or terminal program holds the keyboard: starting either needs a child process (held).",
  "The PDF opener from the Field (known limit).",
  "Whether adding notebook.get / notebook.resolve / book.contents to OBSERVER_OPERATIONS would remove an event something relies on; I only checked office.list and office.get."
 ]
}