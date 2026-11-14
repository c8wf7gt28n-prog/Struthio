# Today's right-click menu: a full map

Read-only reading of `/home/user/Struthio`. Nothing was edited and Qt was never started. The pixel heights below are estimates worked out from the size constants, not measured on screen. All 219 `Entry(...)` call sites were pulled out with an AST walk. That listing is in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/entries.tsv` (file:line, key, label, section, icon, caption, operation and submenu flag for each row).

Abbreviations used for citations: **cm** = `workbench/context_menu.py`, **cc** = `workbench/command_context.py`, **chm** = `workbench/chain_menu.py`, **pq** = `workbench/programs_qt.py`.

## A. How the menu is assembled

- **Router.** One application-wide event filter (cm:2221-2248), installed by `install` (cm:2251-2261), which `chain_menu.install` calls (chm:512-518).
  - It answers `QEvent.ContextMenu` events.
  - It also catches the right-button *press* on a menu row or program row, so a QMenu cannot fire that row (cm:2229-2238).
  - The Menu key and Shift+F10 go to `open_at_focus` (cm:2196-2209, keys bound at cm:2258-2259). When nothing is known under the focus, the menu is for "Here · an empty place" (cm:2208).
- **Finding the target.** `target_at` (cm:1712-1727) walks from the widget under the pointer up through its parents.
  - At each widget it asks `command_context.find` and then the 14 `FINDERS` (cm:1701-1702).
  - It stops at any widget that `owns_menu` (cm:1705-1709): text fields, spin boxes, combo boxes, sliders, selectable labels, and any widget whose policy is CustomContextMenu or ActionsContextMenu. The escape property `graphiteContext` is read at cm:1709 and nowhere sets it.
- **Collecting rows.** `entries_for` (cm:1449-1461) asks `cc.entries` plus the 19 `PROVIDERS` (cm:1442-1446).
  - It keeps only the first row for each key.
  - It then sorts by the 8 `SECTIONS` (cm:51).
  - `SECTION_WORDS` (cm:52-53) is never read anywhere, so a section is only a hairline on screen (cm:1937).
- **Drawing.** `ContextMenu` (cm:1922-1945) is **not a QMenu**. It is a `DeskMenu`: a Qt.Popup QFrame wrapped around a QScrollArea (pq:431-451).
  - At the top is a heading row: icon, label and noun. The noun often carries "revision N" (cm:306, 309).
  - Then come the rows (`ContextRow`, cm:1879-1919) and hairlines.
  - At the foot is a script caption, "what you can do right here" (cm:54, 1943).
  - The text at a row's right end follows one rule: a greyed row prints "unavailable", a submenu row prints "›", any other row prints its caption (cm:1883-1884).
  - A submenu opens after the pointer rests 240 ms (cm:55, 1888, 1899) or on the Right arrow (cm:2099).
- **Two kinds of submenu.**
  - `submenu` opens another ContextMenu (cm:2043-2048). Every such submenu re-sorts its rows and draws its own hairlines.
  - `qmenu` opens a plain Qt QMenu (cm:2036-2042). In practice this is the chain builder `chain_menu.Chain` (chm:99-109), with tear-off strips switched on (chm:104, 141, 171, 173, 178, 187, 191), its own style sheet (chm:81-96) and pictures from `chain_icons` (chain_icons.py:115-128).
- **Size.** Height is capped to the host **window**, not the screen (`bounds` cm:1992-1996; `open_at` cm:2004, 2016). Anything taller scrolls inside the menu. Width is the larger of the pane column and the widest row, capped at the window width less an inset each side (cm:1977-1984).
  - Estimated geometry at 14 pt: row ≈ 24 px, from `max(line, icon)+2·ROW_PAD` (pq:53) with MENU_PX 15 (desk_qt.py:37) and ICON 16, ROW_PAD 2, RULE 9, MARGIN 6 (pq:31-38).
  - Fixed extras per menu: heading 24 + 9, script caption ≈ 35, margins 12.
- **Volume.** 219 `Entry` call sites: 206 in cm and 13 in cc. In addition, 74 `FOLDED` tuples record where every word of the old menus went, under the "nothing lost" rule (cm:2264-2307).

## B. Every target

**Legend**
- Sections: open, modify, state, **line** (the code's `command`), **cap** (`capability`), tree, edit, danger.
- Icon:
  - ✓ means the key is drawn, either in cm's own extra set (`EXTRA`, cm:1791, 18 keys) or in programs_qt's set (`_icon_paths`, pq:150-246, 42 keys).
  - **gen** means the key is not drawn and falls back to a generic window box (pq:245-246).
  - **—** means no key, so the icon column is blank (cm:1796).
- Submenus: › is a ContextMenu submenu; » is a Qt QMenu chain cascade.

### B1. A file in Files (`find_files` cm:1483-1499; `file_entries` cm:596-664)

Example: `notes.csv`. Heading: the calculator icon, "notes.csv · table".

| # | Words | Section | Icon | Operation | Sub | cm |
|---|---|---|---|---|---|---|
|1|Open|open|window ✓|tab.activate||604|
|2|Open with this computer's app|open|—|||606|
|3|Show in its folder|open|files ✓|greyed ("unavailable") unless the file came from a search||607-608|
|4|Rename…|modify|rename ✓|files.rename||609|
|5|Copy to…|modify|—|files.copy||610|
|6|Move to…|modify|—|files.move||611|
|7|Versions…|modify|—|files.versions, files.revert||613|
|8|Export…|modify|leave ✓|files.export||615|
|9|Inspect in the line|line|line ✓|language.run (puts `@files:notes.csv \| rows` in the writing line)||620|
|10|Run|line|run ✓|language.run||622|
|11|Chain from here|line|chain ✓||»|624|
|12|Compare with…|cap|compare ✓|files.compare||626|
|13|Compare with a kept version|cap|—|files.compare; greyed when no versions are kept|› up to 12|628-632|
|14|Extract|cap|extract ✓|language.run|› up to 8 sheets + 6 readings, each with "N rows" (537-555)|633|
|15|Open in Calculator (adapters by suffix, ADAPTERS 71-77)|cap|calculate ✓|ledger.explore||577|
|16|Find tools in the Tool Atlas|cap|tools ✓|||580|
|17|Explore capabilities…|cap|explore ✓|ledger.explore||585|
|18|Stage in Delivery|cap|delivery ✓|||636|
|19|Explain this file|cap|inquiries ✓|files.get||639|
|20|Ask Stacy about this…|cap|—|||640|
|21|Investigate…|cap|investigations ✓|investigation.create||641|
|22|Add to the Agenda…|cap|agenda ✓|agenda.add||642|
|23|Copy path|edit|copy ✓|||661|
|24|Copy the address|edit|—|||662|
|25|Move to Trash|danger|trash ✓|files.trash, no question asked||663|

- **Totals:** 25 rows in 6 sections. 3 submenus. 7 rows have no icon. 2 rows are greyed on a typical file. Height ≈ 727 px.
- **Depth:** 2 through Compare with a kept version and Extract; **unbounded** through Chain from here.
- **Variants:**
  - The adapter count runs 0-2 (.xlsx, .ods, .kicad_pcb, .v and .sv have 2), so 24-26 rows.
  - A working copy adds four rows (cm:644-648): Ask Stacy to work on this…, Review changes to the original…, Show the original, and Discard this draft…. That gives up to **30** rows.
  - A name with a space or "|" greys four more rows: Inspect, Run, Chain and Extract (cm:619-634).
  - A pill file reads "Open pill…" (cm:604).

### B2. A folder in Files

- Rows: Open (open, window ✓), Rename… (rename ✓), Copy to… (—), Move to… (—), Export… (leave ✓), Copy path (edit, copy ✓), Copy the address (—), Move to Trash (danger, trash ✓).
- **8 rows, 4 sections, depth 1.** A smart folder gets the same 8 (cm:601).
- A folder copy in the working area adds Look inside, confined… (confine.inspect), Run a command here, confined… (confine.run), Review changes to the original…, Show the original and Discard this draft… (cm:649-660), giving **13**. A pill copy gives 11.

### B3. Several files in Files (`files_entries` cm:674-694)

- Two files: Compare revisions or Compare these two (open, compare ✓, files.compare; "revisions" when the names differ only by revision words, cm:202-207), Copy to…, Move to…, Stage selected files in Delivery (delivery ✓), Copy paths (copy ✓), Move to Trash.
- **6 rows, 5 sections.** With 3 or more files: 5 rows, 4 sections. If any item is a folder: 4 rows (cm:680).

### B4. The empty place in Files (`files_place_entries` cm:697-710)

- Rows:
  - Root menu › (line, chain ✓; cm:1214-1218)
  - New folder… (tree, new ✓, files.mkdir)
  - New smart folder… (—, files.smart)
  - Import… (office ✓)
  - Work on a copy of a file… (—, copies.start)
  - View as › (view ✓): Thumbnails or List, the current one marked
  - Show all files or Hide machine files (—)
  - Refresh (restart ✓, files.list)
- **8 rows, 2 sections.** Depth is unbounded through Root menu › Start a chain from ›.

### B5. An entry in the Finder (`finder_entries` cm:713-739)

- A file inside Files (.csv): Open, Open in viewer (—), Show in Files, **Change it in Files** (modify, —), Inspect in the line, Run, Ask Stacy about this file, Extract ›, Open in Calculator, Copy path.
  - **10 rows, 5 sections, depth 2.**
  - Show in Files and Change it in Files make the same call, `page.show_in_files` (cm:724 and cm:729).
- A file outside Files: Open, Open in viewer, Copy path, Ask…, the greyed row "Nothing changes here · Files keeps its own changes" (cm:736), plus adapters: 5-7 rows.
- A folder: 5 rows.

### B6. The Finder's empty place (cm:742-753)

- Rows: Root menu ›, View as ›, Show or Hide hidden files (—), Show or Hide the preview (—, **prints "Space"**), Refresh, Copy path.
- **6 rows, 3 sections.**

### B7. The Library

- A received file (cm:756-763): Open, Keep a copy in Files (files.keep), Ask Stacy about this file, Copy the name. **4 rows, 4 sections.**
- The empty place (cm:766-772): Root menu ›, Receive files…, Refresh. **3 rows, 2 sections.**

### B8. A passage in a document (`find_document` cm:1466-1473; `document_entries` cm:381-427)

Heading: "“words…” · passage · <title> · revision N".

| # | Words | Section | Icon | Operation | Prints | cm |
|---|---|---|---|---|---|---|
|1|Bold (or Not bold)|modify|bold ✓|documents.edit|**Ctrl B**|388-391|
|2|Italic|modify|—|documents.edit|**Ctrl I**|388|
|3|Underline|modify|—|documents.edit|**Ctrl U**|388|
|4|Plain (greyed when the words carry no marks)|modify|—|documents.edit||392|
|5|Paragraph style › Heading, Subheading, Minor heading, Body, Code|modify|—|documents.edit|**Ctrl 1/2/3/0/`** inside|394-399|
|6|Move to notes|modify|notes ✓|ideas.capture + documents.edit||401|
|7|Inspect in the line: puts `/documents.edit {"id":…,"expected_revision":…,"selection":{…},"change":{"bold":…},"origin":"HUMAN"}` in the writing line|line|line ✓|||403-406 (283-284)|
|8|Ask Stacy about this|cap|inquiries ✓|||408|
|9|Search for these words|cap|investigations ✓|||410|
|10|New document|tree|new ✓|documents.create||424|
|11|Export…|tree|leave ✓|documents.render||425|
|12-18|Undo, Redo, Cut, Copy, Paste, Delete, Select all|edit|copy ✓ on Copy only|page's own|**Ctrl Z/Y/X/C/V, Ctrl A**|417-423|

- **18 rows, 5 sections, 1 submenu, depth 2.** 10 rows have no icon. Up to **9 keys** are printed at the top level and 5 more in the submenu.

### B9. A page in a document, caret only

- Rows: Paragraph style ›, New document, Export…, Undo, Redo, Cut, Copy, Paste, Delete, Select all.
- **10 rows, 3 sections.** Cut, Copy and Delete are greyed and print "unavailable". Undo and Redo are often greyed too.

### B10. A sheet in the Field (`find_field` cm:1674-1687, kind `field-sheet`; `field_entries` cm:1392-1431)

On the work face, a sheet or calculation that has a line:

| # | Words | Section | Icon | Prints | Sub | cm |
|---|---|---|---|---|---|---|
|1|Open|open|kind icon ✓|**Enter**||1394|
|2|What feeds it (or What it is held by)|state|—||› rows that select a sheet|1400|
|3|What it feeds|state|—||›|1402|
|4|Inspect in the line|line|line ✓|**S**||1404|
|5|Run its line (language.run)|line|line ✓|**Shift+Enter**||1406|
|6|What if|line|line ✓||› up to 24 numbers › 10 % more, 10 % less, Twice, Half, Another value… (field.ripple)|1410, 1233-1264|
|7|Doubt it (its "X" is hidden by ›)|line|line ✓||› "All of it, in Talk" (**X**) + up to 16 rows|1412, 1284-1301|
|8|Trace it (its "T" is hidden by ›)|line|line ✓||› "The whole trace, in Talk" (**T**) + the trace|1415, 1304-1318|
|9|What can be done (its "D" is hidden by ›)|line|line ✓||› steps; a step that writes prints "asks"|1418, 1267-1281|
|10|Your words|line|line ✓||›|1422, 1321-1339|
|11|The brief of the desk (about the desk, not this sheet)|line|line ✓|**B**||1425|
|12|Ask Stacy about this|line|ask (**gen**)|||1428|
|13|Copy its name|edit|copy ✓|||1430|

- **13 rows, 4 sections, 7 submenus, depth 3.** 4 keys print at the top and 2 inside submenus.
- 9 of the 13 rows wear the same chevron icon.
- The programs face gives 10 rows and the network face 9 (its first row reads "Show in Log" and it has no Ask). On those faces Doubt it and Trace it are plain rows that print X and T, so **5 keys** show.

### B11. The Field's empty desk (cm:1352-1391)

- On the work face:
  - open section: Look again (explore ✓, **R**), Show the programs (projects ✓, **P**), Show the network (network ✓, **N**), Back (**Esc**)
  - line section: Check the desk (**C**), The brief (**B**), This face as lines ›, Your words ›
  - This face as lines › holds 8 lines plus one row per kept word (cm:1371-1388).
  - Your words › opens a row per word, each › Run it / In the line / Forget it, plus "Keep a new word…" (cm:1330-1338).
- **8 rows, 2 sections, depth 3. 6 of the 8 rows print a key.**
- The other two faces have 6 rows each, 4 of them with a key.

### B12. Today, the workspace's empty place, and every page that has no finder

Built by `empty_entries` (cm:1221-1225), which joins the root rows (cm:1197-1211), creation (cm:822-831) and the first transfer row (cm:834-842).

- Rows:
  - line section: Your chains › (chain ✓; the kept chains from the menu file, greyed when one does not parse; cm:1149-1174), Start a chain from › (up to 30 files, each a » cascade; cm:1177-1183), Writing line › (Assignment, Terminal, Search, Log; no icons; cm:1186-1194), Edit the Graphite menu… (—; opens a bracket-syntax text file, chm:353-360, 496-499)
  - cap section: Inquiries…, Algorithm & Theory Atlas…, Tool Atlas…
  - tree section: New Idea… (**Ctrl Shift N**), New Project…, Import (Ingress)…
- **10 rows, 3 sections, depth unbounded.**
- **The PDF page lands here.** `PageCanvas` (pdf_qt.py:15) sits in a tab added to `host.tabs` (pdf_qt.py:360), and no finder covers it. The walk therefore reaches `find_workspace` (cm:1690-1698), and the heading reads "Technical PDF · an empty place". The same happens on the Office sheet grid and on viewer and image pages.
- The viewer's own file rows (`viewer_entries`, cc:170-186: Show enclosing folder, Copy full path, Ask about this file, Build a chain from this file, Read and transform ») can only be reached through the "For <file> ›" submenu of a right-click on a menu row or program row (cc:25-32, 157-161).

### B13. The Log and Activity

- An event (cm:1119-1138): Ask Stacy about this (state, inquiries ✓), Show in Log (event ✓; offered **inside the Log itself**), Its job › (when the event has a job; the 7 job rows), Copy. **3-4 rows, 2 sections, depth 2.**
- An event in Activity adds Open at the top: 4-5 rows, 3 sections.
- A network connection or packet (cm:1101-1116): Ask Stacy about this, Follow this conversation (greyed with no far side), Show the process (brain ✓; its caption is the process name; greyed when unknown), Copy address (its caption is the address). **4 rows, 2 sections, depth 1.**

### B14. Jobs and Agenda work

- A job (cm:957-979), from the process list (cm:1626-1651) or the Jobs list (cm:1661-1671):
  - Rows: Show in Jobs (workspace.job; not offered in the Jobs list), Inspect output, Pause, Resume, **Stop (jobs.cancel, no question asked)**, Inspect in the line, Copy the job id.
  - **7 rows (6 in the Jobs list), 4 sections.** Pause or Resume is always greyed; for an ended job 3 rows are greyed.
- Agenda work (cm:1033-1058):
  - Rows: Open Agenda; Pause, Resume and **Stop (agenda.cancel, no question asked)**; Its job ›; Inspect in the line.
  - **4-6 rows, depth 2.**

### B15. The cabinet, Activity's selection, the Machine tree and Settings

- **A cabinet record that is a project** (cm:777-813, 845-858; the record's actions come from cabinet_actions.py:50-81):
  - Rows: Open, **Read saved details** (the same record again), **Write an idea here…**, Inspect in the line, Run, N provider checks (no icon), M "Open <workspace>" rows, Explore all capabilities, Export (Egress)…, Refresh, View as ›, **New Idea…** (Ctrl Shift N), New Project…, Copy the identity.
  - **12+N+M rows, 6 sections, depth 2.**
  - Other records: 10+N+M rows. The empty cabinet tree: 6 rows, 1 section.
- **Activity's selection** (operations_qt.py:128-135) gets the cabinet rows plus an extra "Explore" (cm:1434-1438). That makes two Explore rows in one menu.
- **The Machine tree** (cm:861-880):
  - A project: Open, Inspect in the line, Export (Egress)…, New Idea…, New Project…, Refresh: 6 rows.
  - The Work root: 4 rows.
  - A computer row: 2-4 rows.
- **Settings** (cm:883-893): Open this setting, Expand all (—), Collapse all (—), Search settings…, Copy the key. **5 rows, 3 sections.** A group: 3 rows.

### B16. Menu rows and Programs rows (`cc.find` cc:44-62; `cc.entries` cc:135-167)

- **A row in the Programs list:** Inspect this capability (icon key `inspect`, **gen**), Open capability (the same as a left click), For <current work> › (the whole menu of the open file or page), Explore supported operations.
  - 3-4 rows. Depth is unbounded, through For › … Chain from here.
- **A row in a head menu:** Inspect this command, then either Run this command or Choose an operation ›, then For <work> ›.
  - Choose an operation mirrors the QMenu's own nesting (cc:100-117), for example Tools › Engineering › a group › an item, which is depth 3.
  - Inspect this command writes **"Shortcut: <key>"** into the Command inspector (cc:125; chain_workbench_qt.py:211-218).
- **A row of the right-click menu itself** (cc:53-57) gets the same meta-menu, including "Continue this chain »" (cc:153) and "For <the same target> ›". Building it **closes the menu you were in** (cm:2158-2161).

### B17. Surfaces that keep a menu of their own

These widgets own their menu, so the walk stops there (cm:1709).

- **The console's output** (a QTextBrowser, console_qt.py:197-199, 445-451):
  - Qt's standard Copy, Copy Link Location and Select All, followed by `chain_menu.fill` on the last line run.
  - `fill` adds a greyed header showing the line, "Build on the desk…", then where ›, sort ›, group by ›, select ›, "add a column…", join with ›, take ›, count, and then › (chm:128-151, 169-196).
  - About 14 rows, depth unbounded. The line is **run when the menu opens** (chm:133).
- **Worksheet rows** (sheet_workbench_qt.py:291-292, 566-640):
  - Rows: "[ Selection · N rows ]" (greyed), Calculate › [ Calculate ] › Required − available › [ Then ] › Keep positive or Keep all differences, Method Press › (with Open saved runs ›), Preview selected rows, Preview the plan, Copy the selection as a line, Inspect source, Open full spreadsheet.
  - 8 rows, depth 3, no icons.
- **Agenda rows that ask a line** (agenda_qt.py:134-141): the chain builder on its own.
- **A program room's results** (program_rooms_qt.py:195-209): every enabled button of the room again.
- Also: the Master Stop button (qt_master_stop.py:114-126), Lab paths (lab_qt.py:172-185), Adaptive (adaptive_qt.py:162-201), the meters' priorities (desktop_header_qt.py:464-472), the companion (qt_app.py:1443-1452), and every text field (Qt's own menu).

## C. Totals

| Target | Rows | Sections | Submenus | Deepest | No icon | Keys printed |
|---|---|---|---|---|---|---|
|File in Files|25 (24-30)|6|2 › + 1 »|2 / ∞|7|0|
|Folder (and folder copies)|8 (11-13)|4|0|1|3|0|
|Two files|6|5|0|1|2|0|
|Files empty place|8|2|2|∞|3|0|
|Finder file in Files|10|5|1|2|2|0|
|Finder empty place|6|3|2|∞|2|1|
|Library file / empty place|4 / 3|4 / 2|0 / 1|1 / ∞|0|0|
|Passage|18|5|1|2|10|9 + 5|
|Page|10|3|1|2|7|up to 4 + 5|
|Field sheet (work / programs / network)|13 / 10 / 9|4|7 / 3 / 3|3 / 2 / 2|2 (+1 gen)|4 (+2 inside) / 5 / 5|
|Field empty desk (work / other)|8 / 6|2|2|3|0|6 / 4|
|Today, workspace, PDF, Office grid, viewer|10|3|3|∞|1|1|
|Log event / Activity event|3-4 / 4-5|2 / 3|0-1|2|0|0|
|Network entry|4|2|0|1|0|0|
|Job|7 (6)|4|0|1|0|0|
|Agenda work|4-6|2-3|0-1|2|0|0|
|Cabinet project / empty tree|12+N+M / 6|6 / 1|1|2|N|1|
|Machine (project / root)|6 / 4|3 / 1|0|1|0|1|
|Settings (setting / group)|5 / 3|3 / 1|0|1|2|0|
|Programs row / menu row|3-4 / 2-3|2-3|1-2|∞|0 (1 gen)|"Shortcut:" line|
|Console output / worksheet rows|≈14 / 8|— / 2|6 » / 2|∞ / 3|plain QMenu / all|0|

- **Maximum depth is unbounded.** Every value in a chain is itself a `Chain` with its own where, sort, group by and then (chm:118-125, 169-196, 206-227).
  - Example: to keep "qty over 5" from a CSV you open **8 popups side by side**: file menu › Chain from here » rows » where » qty » over » 5 » then » and click "save as a sheet".
  - Some levels are very long: group by › a field holds up to 33 rows (chm:181-186), a where comparison holds 8 values (chm:37), and Start a chain from holds 30 files (cm:1182). At ≈24 px a row, 30-33 rows is taller than a 768-line screen.
  - Without the chain cascade, the right-click's own deepest is 3 (Field What if; Your words; Root › Writing line). A menu file with nested `[submenu]` blocks can go deeper.
- **Rows that recur across targets:**

| Row (all wordings) | Targets | Where |
|---|---|---|
|Inspect in the line|8 targets|cm:405, 620, 732, 807, 869, 976, 1055, 1404|
|Ask Stacy … (5 wordings, plus "Ask about this file" and "…to work on this…")|9 targets, spread over 3 sections: cap (408), state (1110, 1125), line (1428)|cm:408, 640, 645, 726, 762, 1110, 1125, 1428; cc:176|
|Copy … (13 wordings)|≥14 targets|for example cm:420, 661, 662, 692, 763, 812, 877, 888, 977, 1116, 1137, 1430; cc:175|
|Run (4 wordings)|6 targets|cm:622, 733, 808, 1331, 1406; cc:155|
|Refresh|5 targets|cm:710, 752, 772, 851, 879|
|The root rows (as "Root menu ›" or inline)|6 places|cm:702, 744, 769, 1225|
|View as ›|3 targets|cm:707, 747, 852|
|New Idea… / New Project…|3 targets|cm:1225, 855, 872|
|Import (3 wordings)|6 targets|cm:705, 770, 840|
|Export (2 wordings, in 2 different sections)|6 targets|modify cm:615; tree cm:425, 810, 840, 871|
|Explore (4 wordings)|4 targets|cm:585, 1438; cc:166; cabinet_actions.py:81|
|Tool Atlas (2 wordings)|2 targets|cm:580, 1207|
|Pause / Resume / Stop|2 targets|cm:968-975, 1040-1047|
|Its job ›|2 targets|cm:1053, 1136|
|Extract ›|2 targets|cm:633, 734|
|Copy to / Move to / Trash / Stage in Delivery|3 targets|cm:610-611, 636, 663, 681, 690-693|
|Show in Log|2 targets|cm:1126, 1394|
|Your words, The brief|2 targets, each behaving differently|cm:1389 / 1422; cm:1379 / 1425|

- **Rows that duplicate something one click away elsewhere:**
  - **Passage: 13 of 18.** The page's own button rows hold Bold, Italic, Underline, Plain, the five styles, New document and Export… (document_qt.py:211-212, 226-230). The Revise menu holds Undo, Redo, Cut, Copy, Paste and Select all (menus2.py:23).
  - **Files empty place: 6 of 8.** The Files page's word row holds the same (files_qt.py:100-104).
  - **Today, the workspace and PDF pages: 10 of 10.** Commands › Chain Menu builds the same root (chm:458-484, menus2.py:272); the Tools and Work menus hold the rest (menus2.py:21, 275).
  - **Cabinet tree:** Refresh and View as are under Arrange › Cabinet (menus2.py:229-248); New and Import/Export are under Work.
  - **Machine:** Refresh is under Arrange (menus2.py:24).
  - **Field: empty desk 6 of 8, sheet 7 of 13.** These are the Field foot's clickable keys (field_qt.py:507-523).
  - **Program and menu rows:** "Open capability" and "Run this command" are the same as a left click. "Explore supported operations" is the Programs list's own "Explore the workshop" row (pq:710).
  - **Program room results:** every enabled button of the room is repeated (program_rooms_qt.py:202-204).
  - **Inside a single menu:**
    - Show in Files and Change it in Files (cm:724, 729)
    - Open and Read saved details
    - Write an idea here… and New Idea…
    - Explore and Explore all capabilities
    - Doubt it › and its first row "All of it, in Talk"
    - Extract › and Chain from here », which both list the same readings (cm:537-555 and chm:153-166)
- **Rows that print a key: 31 rows from 24 call sites.** The lines are cm:390, 397, 417-421, 423, 750, 828, 1290, 1310, 1354, 1356, 1359, 1361, 1379, 1394, 1404, 1406, 1412, 1415, 1418 and 1425.
  - On top of those, "Shortcut:" appears in the Command inspector (cc:125).
  - Tooltips name keys too: cm:1259 ("until Esc"), cm:1261 ("Enter asks"), cm:1280 ("(G)"), cm:1414, cm:1417 and cm:1420 ("X / T / D shows…").
- **Icons: which rows have them, and whether they show.**
  - **The ContextMenu does show icons.** Each `ContextRow` paints its own icon (cm:1910), from cm's 18 extra keys or programs_qt's 42. menus2's `setIconVisibleInMenu(action is stop)` (menus2.py:283-284) only touches QActions, and these rows are widgets (pq:265), so it never reaches them. The Words/Icons choice (`tool_faces.STATE`) is never read here either.
  - **They are not the owner's glyphs.**
    - None of glyph_set's 63 `GLYPHS` are used.
    - The drawing style is different: an 18-unit grid with round caps (cm:1801-1802, pq:255-256) against glyph_set's 20-unit grid with mitre joins, solid facets and hexagons (glyph_set.py:1-16, 21-26).
    - The colour is different: plain text ink, TEXT or QUIET (cm:1906-1910), against the neon READY/TEAL with a halo that tool_faces uses (tool_faces.py:204-219). The head menus wear tool_faces glyphs (shell2.py:661-666), so the two menus the owner sees side by side look different.
  - **Coverage of the 219 call sites:**
    - 68 (31 %) have no key and show a blank icon column.
    - 5 use keys that are not drawn and show the generic window box: `ask` at cm:1260, 1290, 1310 and 1428, and `inspect` at cc:147.
    - `line` is used 33 times, `copy` 14 times and `chain` 10 times, so icons rarely tell rows apart.
  - **The chain cascade uses a fourth picture set.** `chain_icons` forces its pictures visible on every opening (chain_icons.py:124, 127-128), in fixed colours #504d46 and #cba5a4 (chain_icons.py:7) rather than theme tokens. "copy the line" gets no picture, because the lookup still expects the words "copy the stac" (chain_icons.py:102 against chm:147).
  - **The separate QMenus** (worksheet, console, rooms, Master Stop) show no icons at all.

## D. What makes it complex, ranked

1. **The most common menu is a wall of rows.** A file gets 25 rows (up to 30) in 6 sections. The capability section alone has 11 rows, and the sections are bare hairlines because their words are never shown (cm:52-53, 1937). At ≈727 px (≈823 for a working copy) the menu is taller than a 1366×768 window, so it scrolls (cm:2004, 2016; pq:445). The passage menu has 18 rows; even the empty desk has 10.
2. **The chain/pipe power is buried, and every level runs.**
   - Chaining happens in a different widget, a tear-off Qt QMenu reached through "Chain from here »".
   - Keeping one filter takes **8 cascading popups**. Levels run to 30-33 rows. The only trace of the chain is a greyed header line.
   - A link cannot be removed or reordered, and the endings sit under "then ›" at the foot of every level.
   - Opening a level runs the line once per candidate: up to 32 runs for one numeric column and 24 for a text column (chm:212-216, 222-227), plus several per table under join (chm:233-250). Each run is synchronous (chm:47-52).
3. **There are 9 ways in to the same pipe, under 6 different names.**
   - The 9 ways: Inspect in the line; Run; Chain from here; Extract; Root menu › Start a chain from; Your chains; Build on the desk…; Continue this chain; Build a chain from this file / Read and transform.
   - On top of those, the console output and Agenda rows each open the chain builder alone.
   - Extract and Chain from here list the same readings side by side.
4. **Words and places don't line up.**
   - Ask Stacy has 5+ wordings across 3 sections. Copy has 13 wordings. Import has 3. Export has 2, filed under 2 different sections. Explore has 4.
   - Same-menu doubles: 6 pairs (listed under C).
5. **Most rows are already one click away.** On a passage 13 of 18; on Files' empty place 6 of 8; on Today and the PDF page 10 of 10; on the Field's empty desk 6 of 8 and on a sheet 7 of 13.
6. **Keys are printed against the owner's rule.** 31 rows at 24 sites carry a key. A passage prints up to 9 at the top plus 5 in its submenu, and 6 of the Field's 8 empty-desk rows print one. The Command inspector adds "Shortcut:" and several tooltips name keys.
7. **The icons are not the owner's glyphs, and coverage is partial.** It is a third picture set, with a fourth in the chain cascade. None of the 63 glyphs are used, 31 % of rows are blank, 5 show a generic box, the chevron repeats 33 times, and the chain pictures are fixed colours rather than theme tokens.
8. **Coverage has holes, and there are 10 separate menu systems.**
   - The PDF page, the Office grid and viewer pages have no finder, so they get the empty-place root menu ("Technical PDF · an empty place").
   - Ten surfaces build their own QMenu, each with its own look; the worksheet even uses "[ … ]" header rows.
   - Right-clicking a menu row, or a row of the right-click menu, opens a meta-menu, and the second right-click closes the first (cm:2158-2161).
9. **The hand rules are not followed.**
   - Stop on a job or on Agenda work dispatches jobs.cancel or agenda.cancel straight away (cm:974 → 910-921; cm:1045 → 1025-1030), although `ALWAYS_ASKS` covers `*.cancel` (stacy_hand.py:52). cm never imports stacy_hand.
   - Rename, Copy to and Move to have no Undo (cm:479-503); `UNDOES` lists only field.set and files.trash (stacy_hand.py:43).
   - Undo after Move to notes puts the words back on the page but leaves the idea in the cabinet (cm:357-378).
10. **Noise in the rows and tooltips.**
    - 19 call sites are rows that are always greyed placeholders.
    - Greyed rows print the word "unavailable" (cm:1883).
    - Headings carry revision numbers (cm:306, 309).
    - 68 tooltips end with "Through Kernel.dispatch: <operation>" (cm:123).
    - Lines are shown as plain greyed menu text or in tooltips, never on the royal-purple slab (chm:112-115; boss_theme.py:60-69). The passage's Inspect in the line hands over raw JSON (cm:403-406).
11. **Work happens when the menu opens.**
    - Every right-click on a file dispatches files.versions (cm:627).
    - The console output's menu runs the last line before it shows (console_qt.py:450 → chm:133).
    - Hovering Extract runs up to 16 reads (cm:541-553).

## E. Worth keeping in the redesign

- **The Target/Entry model** (cm:88-130): a target, plus a row that carries its enabled state and a reason when it is unavailable.
- **The revision checks taken at the right-click:** `edit_document` (cm:322-354), `still_file` (cm:454-460), `job_now` (cm:901-907) and `queued_now` (cm:1015-1022).
- **The single Kernel.dispatch door** (cm:143-147).
- **The heading that names the target.**
- **The desk menu's keyboard:** arrows, type-to-select and F1 (pq:551-580).