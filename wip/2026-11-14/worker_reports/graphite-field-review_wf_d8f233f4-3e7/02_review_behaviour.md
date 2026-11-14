{
 "verdict": "The model and the painted view are sound to build on: nothing I threw at them hung, overlapped or raised, and entering and leaving the Field restores the window's title, panels and dock state exactly. The reader (workbench/field_source.py) is not yet trustworthy, because its state vocabulary does not match the records. Ordinary imported sheets and Word documents show RECHECK; a finding whose source changed shows as an OPEN QUESTION; the three PDFs of the worked case show UNAVAILABLE although their originals are present; sheets from other workspaces appear; and a stale condition is titled with a Python dict. The worst single thing is in the window: Enter or double-click on a sheet whose tab is already open does nothing at all, so the second visit to any sheet from the Field fails silently. After that, place is lost at laptop size: the kept selection is scrolled out of view on return, and below about 1200 px window width the OPEN column is cut off with no way to reach it. All probes are under /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/ and are run from /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work with ./venv/bin/python -B; the repository is untouched (git status empty).",
 "defects": [
  {
   "title": "Enter or double-click on a sheet whose tab is already open does nothing; the Field stays in front",
   "severity": "breaks-work",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win2.py s11 (real window, worked case). F9, select '07 Bench readings', Enter: the sheet opens (centre=QSplitter, tab=OfficePanel). F9 (selection kept), Enter again: centre=FieldPage, _field_active=True, title 'Field \u2014 Graphite', status line empty. A third Enter and a double-click give the same. It also happens when another tab (Files) is in front: the sheet's tab becomes current behind the Field but the Field stays. Calculations and findings reopen correctly. Cause: open_office returns from its reuse loop (host.tabs.setCurrentWidget(tab); return tab) before host._close_start(), and _workspace_tab_changed only closes Home, not the Field.",
   "expected": "Enter on a sheet always shows that sheet, as the foot promises ('Enter open'), whether or not its tab already exists.",
   "where": "workbench/field_page.py:98 (also workbench/office_qt.py:378 and workbench/qt_app.py:3548)",
   "suggested_fix": "In open_object, call leave_field(host) whenever an opener returns a tab. Additionally make _workspace_tab_changed leave the Field as it leaves Home: if self._home_active or self._field_active: self._close_start().",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Ordinary sheets and Word documents are marked RECHECK and counted as waiting",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/states.py import. It imports a 3-line CSV through office.import.preview and office.import.commit; office.get reports source_state UNCHANGED_ORIGINAL (hashes equal). The Field shows 'plain_table | recheck' and the head gains '1 to recheck'. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/docx_probe.py does the same with a .docx: office.list says kind 'document', the Field shows kind sheet, column TABLES, state recheck. By reading workbench/office_service.py:46-58, WORKING_COPY_OR_DERIVATIVE, UNCHANGED_NOTEBOOK_SNAPSHOT and UNCHANGED_BOOK_SNAPSHOT are also absent from AGREES and will be flagged the same way.",
   "expected": "A sheet whose original is unchanged, or that has no original, is not amber, is not in 'N to recheck' and is not a Tab stop. A Word document is not called SHEET.",
   "where": "workbench/field_source.py:21 (AGREES) and :75-76",
   "suggested_fix": "Decide recheck from the words that mean changed (STALE_ORIGINAL, STALE_NOTEBOOK_SNAPSHOT, STALE_NOTEBOOK_REFERENCE, STALE_BOOK_SNAPSHOT, PDF_SOURCE_REVIEW_REQUIRED, RECHECK_SHEET_CHANGED) and unavailable from ORIGINAL_UNAVAILABLE, DERIVATIVE_SOURCE_UNAVAILABLE, SHEET_UNAVAILABLE; treat everything else as current. Use row['kind'] to tell a table from a document.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A finding whose source changed is shown as an OPEN QUESTION; RECHECK is unreachable for claims and its wires are doubled",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/states2.py both. It adds a FINDING supported by two sheets (Field: 'finding | current'), saves an edit to one sheet with office.save, then runs investigation.refresh. The record is now SUPPORTED + NEEDS_REVIEW and sits in both 'learned' and 'unresolved'. The Field shows it as kind question, state open, stale flags all False, 'Fed by 07 Limits Rev A ARCHIVED, 07 Limits Rev B CURRENT, 07 Limits Rev A ARCHIVED, 07 Limits Rev B CURRENT'; the census says '5 open questions' and no 'to recheck'. states.py review shows the same for the three real findings once their evidence goes stale ('1 finding', '4 open questions'). Cause: 'unknown = claim in unresolved' turns every unresolved claim into a question, and investigations.sheet only puts SUPPORTED or REFUTED claims in 'learned', so the RECHECK branch at line 112 can never run. A claim in both lists is read twice and its links appended twice.",
   "expected": "A FINDING that needs review stays a FINDING, reads RECHECK, has dashed 'recheck' wires and is counted in 'N to recheck'. Only role QUESTION is an OPEN QUESTION. Each wire appears once.",
   "where": "workbench/field_source.py:106-112 (links at :119 and :123)",
   "suggested_fix": "Iterate claims once by id. Kind is 'question' only when claim['role'] == 'QUESTION'. State is RECHECK when review == 'NEEDS_REVIEW' or the path step has counts False, OPEN for questions and UNKNOWN, HELD for CONFLICT or REFUTED. Also drop duplicate links in Field.__post_init__ (workbench/field_model.py:72).",
   "confirmed_by": "ran-it"
  },
  {
   "title": "The three PDFs of the worked case show UNAVAILABLE although the originals are present; never-admitted items show green CURRENT as 'admitted source'",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/reader.py field: all three sources read 'unavailable' with the fact 'located but unavailable'. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/unavail.py shows why: for each item 'original eligible, 77 kB, sha matches True, decision matches True, extractor fingerprint matches this program: False'; references.status gives REFERENCE_INDEX_BINDING_STALE_REBUILD_REQUIRED. So it is the reference search index that is stale, not the source. The same records say otherwise elsewhere: office.get gives CURRENT_PDF_SOURCE for each sheet and investigation.path gives source_state CURRENT. Conversely, states2.py unadmitted adds UNREVIEWED, HELD and REJECTED rows to the intake.items answer (synthetic rows; such items cannot be created without a job): each is drawn 'state: current | role: admitted source', because an item with no index row maps '' to current and intake.items is called without a state filter.",
   "expected": "A source's state follows its admission and its original: ACCEPTED with the original present is current; REVOKED, HELD, REJECTED and UNREVIEWED carry their own word and are not called 'admitted'. A stale search index is at most a quiet fact line.",
   "where": "workbench/field_source.py:55-64",
   "suggested_fix": "Take the state from item['admission'] (and optionally from the pdf_service.original check that datasheet_work.sheet_state already uses). Show references.sources only as a fact such as 'reference index needs rebuilding'. Set the role from the admission.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "The Field of one workspace shows every sheet the owner has in any workspace, each marked RECHECK",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/scope.py. It builds a Kernel on a new empty folder with the same profile and calls read_field. Result: census ['3 sheets', '3 to recheck'], the three After Hours sheets each 'recheck', no sources, no pages. office.list reads the profile-wide catalogue (config_dir()/concern/catalog.sqlite3, workbench/office_service.py:34), while documents, intake and investigations are per workspace.",
   "expected": "A workspace's Field ('the work in this workspace', as its accessible name says) shows only sheets that belong to it, or marks foreign ones as such; it does not raise three recheck alarms in an empty workspace.",
   "where": "workbench/field_source.py:67",
   "suggested_fix": "Keep a sheet only when its origin resolves here (origin.pdf.item is among this workspace's intake items, or origin.source.path is under the workspace root, or a document or claim here refers to it). Otherwise leave it out or draw it without a state.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A stale condition card is titled with a raw Python dict and called an OPEN QUESTION",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/cond.py. It creates a page 'Cable budget', a real condition card with conditions.create, then edits an input with documents.save so the card goes STALE with reason 'The words \u201c12 m\u201d now read \u201c14 m\u201d.'. The Field object is: kind question, title \"{'text': 'Total: 15 m', 'unit': 'm', 'value': '15'}\", facts ('stale',), and the census says '2 open questions'. conditions.summary returns result as a dict {value, unit, text}; the reader applies str() to it.",
   "expected": "The sheet reads 'Total: 15 m' with the record's reason as its fact line, and is not counted as an open question.",
   "where": "workbench/field_source.py:131",
   "suggested_fix": "Use (row.get('result') or {}).get('text') as the title, put row.get('reason') in lines, and give conditions their own kind or tag.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Place is lost on return: the kept selection is scrolled out of view, and a first selection below the fold is never revealed",
   "severity": "rule-conflict",
   "reproduction": "Run PROBE_W=1920 /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win3.py place (real window resized to 1280x720, worked case). Arrow to the lowest finding 'The reviewed sheet keeps the 80 ms condition.' (scroll 221, visible). Enter opens the investigation. F9: selection kept, scroll 0, 'selected visible: False'. The picture /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/shots/edge_place_2_back.png shows the foot naming the finding while only 'more below \u2193' is on screen. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/view.py shows the same on first open: with 30 findings and one needing recheck at row 25, first() selects it at y 2498 while the body ends at 508. set_field sets scroll to 0 and nothing calls _reveal except a key press.",
   "expected": "Specification section 72 ('without losing place', 'return to a previous selection'): the selected sheet is on screen whenever the Field is shown or refreshed.",
   "where": "workbench/field_qt.py:48",
   "suggested_fix": "Set a pending-reveal flag in set_field and honour it after _layout() in paintEvent and resizeEvent (call _reveal()), instead of only resetting scroll to 0.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Below about 1200 px window width the right-hand columns are cut off and cannot be reached",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win3.py resize. With the Field showing, resize to 1024x768: the window clamps to its own minimum of 1040, the view is 486 px wide at scale 1.19, and 6 sheets lie past the right edge. FINDINGS is clipped (right edge 501) and OPEN, which holds the selected open question, is entirely off screen ('selected visible: False'); see /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/shots/edge_resize_1024x600.png. Five columns need 544 px times scale (647 px here) and the view is the window minus about 554 px of side panels. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/model.py shows place() returning sheets beyond the given width at 300 px for 3 or more columns, at 600 px from scale 1.4 and at 814 px at scale 2.0 for five columns. There is no horizontal scroll and no hint, and the arrows move onto invisible sheets.",
   "expected": "Every sheet is reachable at any size the window allows: either the columns shrink or stack further, or the surface scrolls sideways and reveals the selection.",
   "where": "workbench/field_model.py:240",
   "suggested_fix": "Return a surface width from place() when columns times the minimum sheet width exceed the given width, and give the view a horizontal offset that _reveal() and the wheel also drive; or fold columns into rows on a narrow surface.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "More than 100 pages: the oldest silently disappear from the Field",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/limit.py. It creates 110 short pages with documents.create (113 documents in the workspace) and reads the Field: 'pages + calculations in the Field: 100', refused [], census '100 pages'. Both calculations of the worked case and its conclusion page are gone, with no notice. documents.list defaults to limit 100, newest first (workbench/project_desk.py:277). By reading, intake.items has the same default of 100 (workbench/intake_service.py:440) and conditions.list is capped at 100.",
   "expected": "All records are read page by page, or the head says that only the first N are shown.",
   "where": "workbench/field_source.py:82 (also :57 and :127)",
   "suggested_fix": "Loop with offset until a short page comes back, for documents.list and intake.items. If a cap is wanted, record it in reader.refused so the status line says so.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Arrow keys cannot reach a column that wires bridge over",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/reach.py. Field with sources p1, p2, sheets t1, t2, findings f1, f2 and links p1\u2192f1, p2\u2192f2 (sources cited directly by findings, sheets unlinked, as an imported CSV is). A search over move() from first() never reaches t1 or t2: Right from a source jumps along its wire to the finding, Left jumps back, and Up and Down stay in a column. 65 of 3000 small random forward-only fields have such unreachable objects. Tab does not help unless the object is waiting.",
   "expected": "Every sheet can be selected from the keyboard (specification section 72: 'offer keyboard navigation').",
   "where": "workbench/field_model.py:185-191",
   "suggested_fix": "Follow a wire only when its other end is in the adjacent column; otherwise step to the nearest row of the adjacent column.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "After Esc back to a page or a sheet, the keyboard focus is on the tab container and typing goes nowhere",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win5.py typing. Open a page in Documents; focus is DocumentPage and typing 'abc' grows the page from 631 to 634 characters. F9, Esc: focus is DocumentsTab (focus policy NoFocus, 'page has focus: False'); typing 'xyz' leaves the page at 634. The sheet room does the same (QScrollArea before, OfficePanel after). A plain text editor tab is fine because the tab is the editor.",
   "expected": "Esc returns the caret to where it was, so the owner can keep typing.",
   "where": "workbench/field_page.py:89-90",
   "suggested_fix": "Remember QApplication.focusWidget() in show_field and restore it in back() when it is still alive and visible; fall back to the current tab only otherwise.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Ctrl+W on the Field closes the hidden current tab while the Field stays in front",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win7.py. With two tabs (Documents, Files) and the Field showing, Ctrl+W takes the tab count from 2 to 1 (Files closed) with centre=FieldPage and nothing visible changing. /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win8.py shows the delivered behaviour under Home for comparison: closing or switching a tab brings the workspace forward, because _workspace_tab_changed closes Home. Under the Field it does not.",
   "expected": "Either the workspace comes forward when its current tab changes, as under Home, or tab commands do nothing while the Field is in front.",
   "where": "workbench/qt_app.py:3547-3548",
   "suggested_fix": "if self._home_active or self._field_active: self._close_start()",
   "confirmed_by": "ran-it"
  },
  {
   "title": "Opening the Field twice from Home forgets Home: Esc lands in the work",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win1.py (step S3). From Home press F9, then F9 again (or Arrange \u25b8 Field while it is showing): _field_from_home is False after the second call. Esc gives centre=QSplitter, title 'Graphite', instead of Home. A single F9 then Esc returns to Home correctly.",
   "expected": "Esc goes back to where the owner came from, however many times the Field was refreshed.",
   "where": "workbench/field_page.py:65",
   "suggested_fix": "Do not overwrite the flag when the Field is already active: host._field_from_home = from_home or (was_active and host._field_from_home).",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A long title without spaces freezes every repaint",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/view.py. One paint of a two-object Field at 1368x900 takes 0.02 s with a 300-character unbroken title, 0.64 s at 1000, 4.7 s at 2000, 15.7 s at 3000, and 5.3 s for 1000 characters of Japanese text (no spaces). 4000 space-separated words take 0.02 s. Every key press and click repaints. investigation.claim accepts 4000 characters. Cause: _wrap measures every prefix from the full length downwards for each cut.",
   "expected": "Paint time does not depend on title length; the title is cut once.",
   "where": "workbench/field_qt.py:316-318",
   "suggested_fix": "Truncate the text to a few hundred characters before wrapping, and find each cut by bisection or by estimating from the average character width.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A plain page, and any object whose own record could not be read, is drawn with the green CURRENT mark",
   "severity": "wrong-result",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/reader2.py: documents.get for '07 Case conclusion \u00b7 HOLD' has no derivation and source_state null, yet the Field (reader.py field) shows it 'document | current'. Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win2.py s9: with documents.get refused, the census changes from '2 calculations, 1 page' to '3 pages', all current, and the two sheet-to-calculation wires vanish. The status line names the operation for 9 seconds.",
   "expected": "An object with no source state carries no state mark (the view already supports an empty state). An object whose record could not be read says so on the sheet instead of 'current'.",
   "where": "workbench/field_source.py:85 and :93-94",
   "suggested_fix": "Pass state '' for documents without a derivation. When documents.get or office.get returns nothing, give the object a quiet 'not read' state.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "An exception inside paintEvent ends the whole program with a segmentation fault",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/crash.py note. A Field with one object of a kind that rank_title's table does not list ('note') is shown in a FieldView and events are processed: KeyError 'note' from rank_title, then 'QPaintDevice: Cannot destroy paint device that is being painted' and exit code 139. Everything else in the model tolerates unknown kinds (KIND_RANK.get, KIND_TAG.get). The reader today only emits listed kinds, so this is not reachable from real records yet, but any future paint error would take unsaved work in other tabs with it.",
   "expected": "A drawing error is contained: the painter is ended and the surface shows what it can.",
   "where": "workbench/field_qt.py:154-175 (trigger at workbench/field_model.py:137-138)",
   "suggested_fix": "Wrap the body of paintEvent in try/finally with p.end(), and use .get(kind, kind.upper()) in rank_title.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "With no kernel the Field says 'nothing in the field yet, bring material in' and the status line says nothing",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/win2.py s8. With host.ledger_bridge removed, show_field does not raise; the Field has 0 objects, page.refused is [('kernel', 'not available')] and the status line is ''. The one uncaught AttributeError printed in that run comes from elsewhere in the window, not from the Field. refresh() returns at line 45 before the status message, although its docstring promises 'says so in the status line'.",
   "expected": "The owner is told the records could not be read, not that the workspace is empty.",
   "where": "workbench/field_page.py:43-45",
   "suggested_fix": "Show the same status message on this branch, and have the empty surface draw 'the records could not be read' when page.refused is not empty.",
   "confirmed_by": "ran-it"
  },
  {
   "title": "A cycle pushes its members, and what they feed, to the far right under wrong headings",
   "severity": "rough-edge",
   "reproduction": "Run /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/edge/cycle.py. Eleven objects with links pdf\u2192s1, s1\u2192s2, s2\u2192s1, s1\u2192f give ranks pdf 0, s2 19, f 19, s1 20. Columns left to right are MATERIAL, OPEN [q], 'OPEN' [s2, f], TABLES [s1], so the finding sits left of the sheet that feeds it. _ranks does terminate and is bounded by len(KIND_RANK)+len(objects), but each pass moves a cycle one rank further. Today's reader cannot produce a cycle; a later link kind could.",
   "expected": "Cycle members stay near their kind's column.",
   "where": "workbench/field_model.py:97-103",
   "suggested_fix": "Ignore back edges found by a depth-first pass before ranking, or cap the push at the kind's rank plus the number of distinct ranks.",
   "confirmed_by": "ran-it"
  }
 ],
 "checked_and_fine": [
  "Model _ranks: terminates and stays bounded for 2-, 3- and 30-object cycles, self-links, links to missing ids, duplicate and empty ids, an empty field, one object, 200 objects in one column, 12 ranks and a 40-long chain inserted in reverse (max rank 39 as expected) \u2014 model.py",
  "Model place(): at widths 300/600/814/1368/3000, heights 200/500/1050 and scales 0.85/1.0/1.4/2.0 there are no overlaps, no NaN, no negative sizes, one placement per object and nothing outside the surface vertically; the only problem is the horizontal overflow reported above \u2014 model.py",
  "Model move(left/right/up/down/unknown word), next_attention (both ways) and first(): always return an existing id and never raise, from every start including '' and across 200 random graphs with 60 random moves each; an empty field returns '' \u2014 model.py",
  "depth() for a selection with no links returns 0 for it and 2 for everything else, as its comment intends, and never raises \u2014 model.py",
  "View paints every model at 300x200, 600x400, 814x600, 1368x900, 3000x1600, 40x40 and 1x1 without exceptions, including empty titles, Arabic and Japanese text, tabs and newlines in titles, 40 fact lines, a 400-character identity line and an unknown long state word \u2014 view.py",
  "Hit-testing while scrolled: six visible sheet centres all hit the right sheet; points in the head and foot hit nothing; a click selects and a double-click opens; the wheel clamps at 0 and at the maximum for deltas of \u00b1120000 \u2014 view.py",
  "Keyboard: Enter with nothing selected does nothing; arrows, Home, Tab, Shift+Tab, Space and letters on an empty Field are safe; Esc emits 'left' \u2014 view.py",
  "Tab: with waiting objects Tab and Shift+Tab cycle them and never leave the Field (Esc and F9 still work); with none, Tab leaves to the writing-line buttons, Esc then does nothing, and F9 brings the focus back to the Field, so the owner is not stuck \u2014 view.py, win3.py tab",
  "Window: Field from the work and from Home, Esc back to each; title, saveState, every dock's visibility, context bar and document info are identical before and after for a text-file tab, a Documents tab, Home and the empty-workspace Home (only the focus differs, reported above) \u2014 win1.py, win5.py, win6.py",
  "Rooms opened while the Field is in front (Files, Agenda, Library, Project Desk, Changes, Continuing work, Deployment, Documents, Home, open_document on a file) all bring the workspace or Home forward and clear _field_active \u2014 win1.py, win7.py",
  "Closing the last tab while the Field shows goes to Home with the flag cleared; resizing between 1040x640 and 1920x1200 with the Field showing raises nothing \u2014 win2.py s5, win3.py resize",
  "Art mode: session.state['desk_art']='clean' plus refresh turns the texture off; 'illustrated' plus F9 turns it back on \u2014 win2.py s7",
  "A reader operation that raises, refuses or returns None (office.list, documents.get, investigation.path, intake.namespaces): the Field shows the rest, the status line names the operation, nothing is uncaught \u2014 win2.py s9",
  "Opening an object whose record was deleted after the Field was drawn fails politely in all three rooms: page ('That document is not available right now.'), investigation (room opens), sheet (status 'Field \u00b7 could not open 07 Bench readings: OFFICE_DOCUMENT_UNAVAILABLE'); nothing is uncaught \u2014 win2.py s10",
  "Links of the real case: all 12 match the records (sheet origin.pdf.item, report derivation.sheet, investigation.path SOURCE addresses and the CHECK program), and every direction is source to target \u2014 reader.py, reader2.py",
  "A second investigation: the reader returns no title and the page falls back to the workspace folder name, which is sensible \u2014 states.py second",
  "F9 adds no journal rows (186 before, after two F9 and after Esc); read_field takes about 0.1 s on the worked case; no other F9 binding exists in the program \u2014 win3.py journal, states.py time"
 ],
 "could_not_check": [
  "The PDF opener from a source sheet (needs a child process and a job; held, and accepted as a known limit)",
  "Whether the three sources also read UNAVAILABLE on the owner's own machine: it depends on whether the reference index's extractor fingerprint matches the installed program there; on this machine it does not",
  "A never-admitted intake item through real operations (admitting or scanning needs a job); confirmed only with rows added to the intake.items answer, and by reading",
  "More than 100 intake items in one namespace (same reason); the default limit of 100 was read in workbench/intake_service.py:440 and confirmed by running only for documents",
  "A blank new sheet (WORKING_COPY_OR_DERIVATIVE) and notebook or book snapshots: flagged RECHECK by reading only; I ran only CSV and DOCX imports (UNCHANGED_ORIGINAL)",
  "Painting on a real display, HiDPI scaling and real window-manager key delivery (for example F9 while an embedded terminal has the focus): everything ran on the offscreen platform at dpr 1.0"
 ]
}