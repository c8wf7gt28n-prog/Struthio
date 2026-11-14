{
 "summary": "The fixes are real: 12 of the 13 window/view/keyboard defects are closed against /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt, and W3 is partly closed (at 28 pt on 1366x768 no sheet can be shown whole). The new checks pass: only the staC box is drawn over the rail and it gives way at 1366x768; S and Shift+Enter behave as described and a refusal is said as one; both menus work on both faces; title, bars and saveState are identical after leaving the Field; nothing raises at 28 pt. The fixes introduced seven things I reproduced. The one that matters most is that the Field now keeps its reading while the journal stands still, so a sheet whose original changed on disk stays CURRENT through F9 and Esc+F9 until R is pressed. Next: at 1920x1200 Stacy's rail pushes the MATERIAL column off screen (ASCII and Clean fit all five columns), and S followed by Esc in the writing strip leaves the keyboard nowhere with the Field in front. One thing predates the fixes and is still there: the Concern's 'Working area \u00b7 Workspace' strip stays under the Field when it is opened from the work with no tab. All probes and their outputs are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/ (outputs in out/, captures in cap1920/, cap1366/, shots/); nothing under the worktree or /home/user/Struthio was edited.",
 "verdicts": [
  {
   "defect": "W1. Enter or double-click on a sheet whose tab was already open did nothing",
   "verdict": "closed",
   "observed": "w1.py and win2.py s11, for a sheet, calculation, finding, source (PDF), open question and page, each with the Field really in front: 'Enter, tab exists and is current' -> centre=QSplitter field=False, 'same tab shown: True | tabs 3 -> 3'; 'Enter, another tab in front' (Files in front) -> the object's tab comes forward, field=False; double-click in both situations the same. wmisc.py: after each of these the keyboard is in DocumentPage and 'typing xyz -> arrives in the page'. 0 uncaught errors.",
   "remains": ""
  },
  {
   "defect": "W2. Place lost on return; first selection below the fold never revealed",
   "verdict": "closed",
   "observed": "win3.py place at 1280x720: lowest finding selected by keyboard (scroll x 459 y 590), Enter, F9 back -> 'selection kept: The reviewed sheet keeps the 80 ms condition.' and 'scroll x 459 y 590 | selected wholly visible: True'. Resizing through 1600x900, 1366x768, 1280x720, 1040x640 and back: 'selected wholly visible: True' every time. probe_view.py part 2: 'opened on: Finding 27 must be rechecked ... scroll 4659 -> visible when the Field opens: True'. view.py: 'after set_field with the same records: selected s29 (kept: True) ... selected sheet visible: True'; 'first() = s25 visible on first paint: True'.",
   "remains": "Nothing at ordinary sizes. At 28 pt on 1366x768 the selected sheet is revealed only as a sliver; that is counted under W3."
  },
  {
   "defect": "W3. Columns cut off below about 1200 px and from 18 pt on 1366x768; words cut; fact lines vanished",
   "verdict": "partly",
   "observed": "w3.py in the real window (out/w3.txt). Sheets are no longer squeezed (209x167 at 14 pt, 264x210 at 18, 297x236 at 20, 407x327 at 28); the surface scrolls both ways; the selection is revealed sideways. Share of sheet strings elided, all 14 sheets drawn one by one: 7 of 69 (10%) at 14, 18 and 20 pt and 8 of 69 (12%) at 28 pt, the same at 1920x1200 and 1366x768; facts not drawn 0 of 15; identity lines not drawn 0. As seen on one screen: 9%, 12%, 9%, 11% at 1920x1200 and 10%, 9%, 11%, 17% at 1366x768. What is cut is identity lines ('After Hours 07 sources' -> 'After Hour\u202607 sources', '07_Rail_Limits_Rev_A.pdf' -> '07_Rail_Li\u2026_Rev_A.pdf') and two finding titles longer than two lines. Keyboard alone (arrows): every sheet reachable at every size; wholly on screen 14 of 14 at 1920x1200 for all four sizes and at 1366x768 for 14 and 18 pt. At 1366x768 20 pt: 12 wholly, 2 at 91%. At 1366x768 28 pt: 'body 492x120 sheet 407x327 ... wholly on screen 0, more than half 0, half or less 14 ... least share shown 8%'. Window minimum is 1040x640; at that size 'selected wholly visible: True'.",
   "remains": "At 28 pt on 1366x768 no sheet can be brought wholly on screen: the head (134 px) and foot (222 px) scale with the text and leave a 120 px body for a 327 px sheet (254 px when the Field is opened from Home, still less than a sheet); /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_qt.py:108-112 and 126-127. The reveal adds 26*scale above the sheet when coming from below (field_qt.py:163), so a sheet taller than the body shows only its top 28 px (8%), and at 20 pt two sheets show 91%. Older than the fixes but part of the same squeeze: opened from the work with no tab, the Concern's 'Working area \u00b7 Workspace / Working area / Ask Graphite' strip stays under the Field (38 px at 14 pt, 134 px at 28 pt); /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/arc_desktop.py:545-548 hides context_bar and workspace_status but not that strip."
  },
  {
   "defect": "W4. Lettering on receded sheets and the stale wire below 4.5:1",
   "verdict": "closed",
   "observed": "w45.py, a sheet three steps from the selection, painted, ground #0b0e0d: 'kind 6.47 | state word+mark 8.98 | title 9.82 | identity 6.47' (state CURRENT) and 'state word+mark 6.47' (unavailable), the same with and without the scan texture. By the theme's own numbers the lowest lettering at any step is the identity line at step 1 (FAINT on CARD), 5.83:1. Stale wire between two step-3 sheets: 'brightest pixel #f39334 on ... #080a09 = 8.54:1', texture on or off (the original probe's single sampling column no longer crosses the wire and printed 1.00:1; I scanned the whole gap). My sampling box missed the fact line; it uses the same pen as the kind tag (QUIET at 0.78), 6.47:1.",
   "remains": ""
  },
  {
   "defect": "W5. Recheck, open and held shared one mark; 'unavailable' differed only by colour",
   "verdict": "closed",
   "observed": "w45.py drew each mark at the size the view uses and compared pixel masks: current is a filled square, recheck a square with its left half filled, open a hollow square, held a square with a diagonal, waiting a square with a dot, failed a cross, unavailable a dash. On 176 px sheets where the word gives way (out/narrow_marks.png) the mark stays. Identical pairs are only ('waiting','paused'), ('failed','interrupted') and the quiet states ('unavailable','not read','down'), which all draw the dash.",
   "remains": "Not a failure of the stated expectation, to know: 'unavailable', 'not read' and 'down' share the dash, so on a narrow sheet they are told apart only in the foot; at 16 px text 'open' and 'waiting' differ by a 4-pixel dot (at the default 19 px they differ by 6 or more)."
  },
  {
   "defect": "W6. While anything waited, Tab and Shift+Tab never left the Field",
   "verdict": "closed",
   "observed": "w6c.py in the real window with 1 object waiting: 'Tab x3 -> keyboard goes to: [Writing line mode: Assistant, Terminal, Log] | selection moved: False | Field in front: True'; Shift+Tab x3 goes to widgets of the side panel; F9 from there -> 'keyboard: FieldView'. A x5 over four waiting objects: ['q1','t1','c1','j1','q1','t1'], each wholly on screen; Shift+A x4: ['t1','q1','j1','c1','t1']. PageDown moves scroll_y 99 -> 859 -> 889, PageUp back to 128; End selects the last object, Home the first waiting one. Standalone view.py: 'two waiting objects: Tab x5' never changes the selection and focus leaves.",
   "remains": ""
  },
  {
   "defect": "W7. After Esc back to a page or a sheet typing went nowhere",
   "verdict": "closed",
   "observed": "win5.py typing: 'focus before the Field: DocumentPage | page length 631 -> 634 after typing abc'; 'focus after Field + Esc: DocumentPage | page has focus: True'; 'typed xyz after coming back: page length 634 -> 637'. Sheet room: focus QScrollArea before and QScrollArea after Field + Esc. wb.py: after S, Shift+Enter and Esc the snapshot's focus is again DocumentPage.",
   "remains": ""
  },
  {
   "defect": "W8. Ctrl+W on the Field closed the hidden current tab while the Field stayed in front",
   "verdict": "closed",
   "observed": "win7.py: 'Ctrl+W while the Field shows -> centre=QSplitter field=False title=Graphite tabs=1 tab=DocumentsTab'. win8.py: 'current tab closed under the Field -> centre=QSplitter field=False'; 'another tab made current under the Field -> centre=QSplitter field=False'. w8.py with one tab: Ctrl+W closes it and Home comes forward (centre=FinderPage, tabs=0). Ctrl+Tab, Ctrl+PgDown and Ctrl+PgUp leave the Field in front and change no tab.",
   "remains": ""
  },
  {
   "defect": "W9. Field opened twice from Home forgot Home; F9 while showing re-read everything",
   "verdict": "closed",
   "observed": "win1.py S3: '_field_from_home after the second F9: True' and 'S3 Esc (came from Home) -> centre=FinderPage home=True title=Home \u2014 Graphite'. w9.py counting Kernel.dispatch: 'F9 from Home (first reading): 22 reads'; 'F9 again while the Field shows: Kernel reads during this step: 0 {}'; after Esc, 'F9 from Home again, nothing recorded since: 2 {ledger.journal.status: 1, ledger.operations: 1}'; 'R (look again): 21'.",
   "remains": "The way it was closed introduced a wrong result; see the first regression."
  },
  {
   "defect": "W10. A long title without spaces froze every repaint",
   "verdict": "closed",
   "observed": "view.py: 'unbroken title of 300 chars 0.005s', '1000 chars 0.005s', '3000 chars 0.005s', '10000 chars 0.006s', 'CJK sentence x40 (1000 chars, no spaces) 0.011s', 'title of 4000 words 0.006s'. The slowest paint in the whole run was 0.023 s. It was 0.64 s at 1000 and 15.7 s at 3000.",
   "remains": ""
  },
  {
   "defect": "W11. An exception inside paintEvent ended the program with a segmentation fault",
   "verdict": "closed",
   "observed": "crash.py with an unknown kind: 'still alive after painting', exit code 0. crash2.py made each of the 13 drawing steps raise in turn (_layout, _texture, _art, _stac, _head, _columns, _ghosts, _wires, _sheet, _wire_words, _more, _foot, _empty) with normal paints and key presses: every run 'still alive ...; amber message pixels under the head: 89..108', exit code 0. The surface says 'The Field could not be drawn: ...'.",
   "remains": ""
  },
  {
   "defect": "W12. With no kernel the Field said 'nothing in the field yet' and the status line said nothing",
   "verdict": "closed",
   "observed": "w12.py and win2.py s8: 'objects: 0 | problem: \"Graphite's records are not available in this window\" | status line: \"Field \u00b7 Graphite's records are not available in this window\"'. Capture shots/w12_no_records.png shows on the surface '// the records could not be read / Graphite's records are not available in this window. / R looks again.' With the records back, R -> the full census and problem ''.",
   "remains": ""
  },
  {
   "defect": "W13. Choosing the Clean desk while the Field was showing left its scan texture on; rail in Clean and ASCII",
   "verdict": "closed",
   "observed": "wb.py with the Field showing at 1920x1200, through boss_qt.choose_art: 'desk art ascii -> rail 0 texture flag True scan lines painted True'; 'desk art clean -> rail 0 texture flag False scan lines painted False'; 'desk art illustrated -> rail 342 texture flag True scan lines painted True'. Each takes effect at once, without F9.",
   "remains": ""
  }
 ],
 "regressions": [
  {
   "title": "The Field keeps showing CURRENT for a sheet whose original changed on disk; F9 and Esc+F9 no longer read again",
   "severity": "wrong-result",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/w9b.py. Import a CSV from the workspace as a sheet (office.import.preview, office.import.commit), F9: 'Field shows it: (probe_limits, current, (from probe_limits.csv, version 1)) | record says: UNCHANGED_ORIGINAL'. Esc, then change the CSV on disk as another program would: 'record now says: STALE_ORIGINAL | journal head moved: False'. Then 'F9 -> the Field shows the sheet as: current (census []) | record says: STALE_ORIGINAL'; 'F9 again while showing -> current'; 'Esc, F9 -> current'; 'after a resize -> current'. Only 'R -> recheck (census [1 to recheck])'. At the reviewed commit every F9 read again (refresh had no cache), so this state would have shown at once.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_page.py:84 (the early return when the journal head equals _read_at) and :101 (show_field while already in front only takes the keyboard). A sheet's source state is computed from the file on disk at read time (workbench/office_service.py:57), which the journal never sees.",
   "suggested_fix": "Do not treat an unchanged journal head as an unchanged workspace for records whose state depends on disk. Either read again whenever the Field is brought to the front from elsewhere (keep the zero-read path only for F9 while it is already showing), or keep the cache but re-ask office.get for sheets with origin.source.path (or compare their files' mtime and size) on every show."
  },
  {
   "title": "At 1920x1200 Stacy's rail takes the room the sheets need: the MATERIAL column is cut off when the Field opens",
   "severity": "rule-conflict",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/wb.py and capture cap1920/Graphite_Field_01_Opened_1920x1200.png. Illustrated desk, default text size, worked case: 'view 1366x1078 scale 1.19 rail 342 body 1024x895 surface 1188x1010 scroll x 161 | without the rail the body would be 1366 wide -> the sheets would fit'; 'sheets not wholly on screen sideways, per selection: min 1 max 3 of 14'. The capture shows the three sources cut to 'URRENT / dings. / ources' at the left edge with '\u2190 more'. In ASCII and Clean: 'rail 0 ... body 1366 wide, sideways scroll room 0'. The module's own rule says the rail appears only when the sheets keep their room. Nothing is drawn over a sheet or wire (the rail's pixels differ from the bare rail only from x=1036, the staC box), but a whole column is pushed off screen.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_qt.py:114-124 (rail() decides on the view's width alone: 1040*scale) and :126-127 (body() subtracts it before the layout).",
   "suggested_fix": "Decide the rail after the layout: place the field in the full width first and give the rail only the room left over (width minus the surface the columns need), narrowing it down to a minimum and dropping it when that minimum does not fit."
  },
  {
   "title": "After S, Esc in the writing strip leaves the keyboard nowhere while the Field stays in front",
   "severity": "rough-edge",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/w6c.py (last section). Field in front, a calculation selected, press S: 'keyboard: OneBox | Field in front: True' (the strip holds exactly obj.stac and its completion popup opens over the Field). Press Esc in the strip: 'keyboard: None | window focus widget: None | Field in front: True | strip still holds the line: True'. Then 'Left -> selection moved False', 'Down -> False', 'Enter -> False', 'Esc -> Field in front True, keyboard None'. Only Tab (goes to the writing-line mode buttons), F9 or a click recovers.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_page.py:146-150 (stac_in_line hands the keyboard to the strip) together with workbench/shell2.py:872 (Esc in the strip only clears focus).",
   "suggested_fix": "When the strip gives up the keyboard (Esc, or after Ctrl+Enter ran the line) while host._field_active is true, give it back to host.field_page.view, as stac_run already does after Shift+Enter."
  },
  {
   "title": "The Menu key opens the empty-place menu instead of the selected sheet's menu when the sheet's corner is off screen",
   "severity": "rough-edge",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/wmenu.py at 1366x768. 14 pt: selection on screen -> 'menu for: (What stretched the start, open question \u00b7 open) rows [Open, \u2014, What feeds it]'; after PageDown x4 (sheet y -143..24, body y 69..494) -> 'menu point (610,-119) inside the body False | menu for: (Field, an empty place of the Field) rows [Look again, Show the network, Back]'. At 28 pt it happens right after an arrow key: 'after Home ... sheet y -105..222, body y 134..254 | menu for: (Field, an empty place of the Field)'; 'after Down' the same. A keyboard owner then has no Open, What feeds it, Inspect, Run its staC or Ask for the selected sheet.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_qt.py:153-157 (selected_point returns the sheet's top-left plus 24 px even when that lies outside the body) and workbench/context_menu.py:1510-1516 (find_field hit-tests that point).",
   "suggested_fix": "For the keyboard's menu take the selected object directly instead of hit-testing a point: in selected_point reveal the sheet first and clamp the point into the visible part of its rectangle, or have focus_point/find_field build the 'field-sheet' target from view.selected() when the menu was asked for by key."
  },
  {
   "title": "The key legend in the foot is no longer shown when the Field opens, and never below about 1900 px",
   "severity": "rough-edge",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/wmisc.py. At 1920x1200: 'view 1366 wide, legend 1091 px, room 1300 px: legend drawn per selected kind: {SOURCE \u00b7 CURRENT: True, PAGE: True, CALC \u00b7 CURRENT: True, OPEN QUESTION \u00b7 OPEN: False, FINDING \u00b7 CURRENT: True, SHEET \u00b7 CURRENT: True}'; 'first selection when the Field opens: What stretched the startup pulse? -> NO LEGEND' (see cap1920/Graphite_Field_01_Opened_1920x1200.png: no keys in the foot). 'at 1600x900 (view 1046): legend drawn for 0 of 6 kinds'; 'at 1366x768: 0 of 6'. 'the legend as reviewed (63d9d2d) was 489 px at this size: it was drawn for every kind: True'. So A, R, Menu and Esc are not said anywhere on first sight (the rail names only S and Shift+Enter, and only when the rail shows).",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_qt.py:552-563 (one long line, drawn only if all of it fits beside the tag).",
   "suggested_fix": "Let the legend give way a key at a time instead of all at once (keep 'Esc back', 'Enter open', 'A next waiting' longest), or wrap it onto the foot's free line; the foot is three lines tall and the right half of two of them is empty."
  },
  {
   "title": "Home, End and A do not bring the selected sheet back into view when it is already the one they select",
   "severity": "rough-edge",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/wd.py (last section), a column of 30 with one waiting sheet near the top: 'first() = s2 | on screen: True'; 'PageDown x5: scroll_y 1993, selected sheet on screen: False'; 'Home: selected s2, scroll_y 1993, selected sheet on screen: False'; 'A (the only waiting one is already selected): on screen: False'; 'Up, Down: on screen: True'.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/field_qt.py:201-202 (the reveal runs only when the selection changed).",
   "suggested_fix": "Reveal after every selecting key (arrows, Home, End, A) whether or not the selection changed: drop the 'if self.field.selected != before' guard for the reveal and keep it only for _describe()."
  },
  {
   "title": "The menu heading for a page with no state reads 'page \u00b7 '",
   "severity": "rough-edge",
   "reproduction": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-window/wmenu.py: Menu key on the plain page '07 Case conclusion \u00b7 HOLD' -> 'menu for: (07 Case conclusion \u00b7 HOL, page \u00b7 )'. Plain pages now have state '' and the heading still joins kind and state with a separator.",
   "where": "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt/workbench/context_menu.py:1523 (find_field: '%s \u00b7 %s' % (words, obj.state)).",
   "suggested_fix": "Join only when there is a state: words if not obj.state else '%s \u00b7 %s' % (words, obj.state)."
  }
 ]
}