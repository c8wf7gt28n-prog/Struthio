# Seven verbs, one pipe: a simpler right-click for Graphite

*Designer 1 of 3. Angle: a few big verbs. Nothing in `/home/user/Struthio` was changed, and Qt was not started. Every pixel height below is worked out from the size constants; none was measured on screen.*

Citation shorthand used throughout:

| Short | File |
|---|---|
| cm | `workbench/context_menu.py` |
| cc | `workbench/command_context.py` |
| chm | `workbench/chain_menu.py` |
| cwq | `workbench/chain_workbench_qt.py` |
| pq | `workbench/programs_qt.py` |
| tf | `workbench/tool_faces.py` |
| gs | `workbench/glyph_set.py` |
| bt | `workbench/boss_theme.py` |
| sh | `workbench/stacy_hand.py` |
| s2 | `workbench/shell2.py` |
| sl | `workbench/stacy_language.py` |
| tp | `sdk/cli/arc1cli/typed_pipeline.py` |
| fsv | `workbench/files_service.py` |
| osv | `workbench/office_service.py` |
| ad | `workbench/addresses.py` |
| fp | `workbench/field_page.py` |
| fsrc | `workbench/field_source.py` |
| fd | `workbench/field_do.py` |
| sw | `workbench/stac_words.py` |
| mn | `workbench/menus2.py` |
| con | `workbench/console_qt.py` |
| ek | `workbench/engineering_kernel.py` |
| tcm | `tests_integrated/test_context_menu.py` |
| tsh | `tests_integrated/test_stacy_hand.py` |

Scratch work, all under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/`:

- **`verbs/worked.py`** runs both worked examples through the real `typed_pipeline.parse/apply` and `files_service.keyed`. It uses real After Hours 07 data from a read-only copy of the backup's catalog, `ah07_catalog.sqlite3`.
- **`verbs/keys_scan.py`** is a trial run of the "no line prints a key" check. On today's code it flags 27 call sites.

## 0. In one page

- **The first level is at most 7 lines.** Every line is a verb with a glyph.
  - The verbs always come in one order: New, Open, Open in ›, Then ›, Change ›, View ›, Ask ›, Copy ›, Remove.
  - A verb that does not apply is left out, never greyed.
  - New and View appear only on places and trees. Open, Change and Remove appear only on things. So no target ever shows more than 7.
  - A file goes from 25 rows in 6 sections, about 727 px (reader: menu, B1), to 7 rows, about 222 px.
- **Then › is the pipe.**
  - It opens one panel beside the verbs. At the top of the panel is the line so far on the line slab: `bt.line_sheet()` (bt:66-69), royal purple in Kasandra, green letters in Graphite. Under it are the row count and a three-row preview.
  - Under that are the next steps for this data, each choice with a real count. Under those are the endings.
  - Choosing a step adds it to the line and refills the same panel. You never get the 8 popups side by side that today's builder needs (chm:118-125).
- **The menu never shows more than two popups.** Anything deeper than the verb's own panel replaces that panel's rows in place, with a Back row.
- **No screen holds more than 16 rows, and none scrolls.** A screen splits into pages when the window is short (at 1366×768, every screen worked out here comes to about 560 px or less).
- **Counts come from one Kernel read per screen.** A new read, `language.offers`, reads the source once and counts every candidate in memory. Today opening one numeric column's `where` runs `language.run` 32 times on the window's thread (chm:212-216).
- **Changes follow Stacy's hand** through `SlateFace.stage(..., asked=True)` (s2:1991-2030).
  - Save as a sheet becomes one new operation, `chains.save`, with an exact Undo (the folder goes to the Trash).
  - Stop on a job or Agenda work is put up and waits, because `*.cancel` always asks (sh:52). Today it dispatches at once (cm:974 → 910-921).
- **Icons are glyph_set glyphs drawn through `tool_faces.icon`** in the theme's colours, with a new "line" tone in the ROYAL tokens. The menu's two private picture sets go: `EXTRA` (cm:1791) and the `programs_qt` icons. The builder's `chain_icons` set goes with the builder (chm:149-150). Eight glyphs are added.
- **No key is printed anywhere in the menu.** 27 call sites change today. That includes the "Shortcut:" line in the command inspector (cc:125).

---

## 1. The rules of the menu

### 1.1 The verbs

| # | Key | Words | Glyph | Holds |
|---|---|---|---|---|
| 1 | `new` | New › | `document`: page with a plus, `New File` in FOR_MENU (tf:177) | What can be made here. Places only. |
| 2 | `open` | Open | The target's own kind glyph: `KIND` (gs:413-415), or `folder`/`page`/`table`/`running`/`lines`/`reach` | The thing's default open. One click, never a submenu. A command row shows its own name here. |
| 3 | `openin` | Open in › | `source`: "this row, and where it leads" (gs:147) | Other places to open it: its folder, Files, the Log, Jobs, this computer's app, a program (adapters), the atlases, the writing line |
| 4 | `then` | Then › | `chain` (gs:362), drawn in the **line tone** | The pipe (section 3) |
| 5 | `change` | Change › | `cell`: the pencil (gs:140) | What changes it: rename, move, styles, Pause/Resume/Stop…, undo/redo |
| 6 | `view` | View › | `sliders` (gs:292) | How a place or tree is shown, including Look again (refresh). Places and trees only. |
| 7 | `ask` | Ask › | `asked` (gs:198) | Questions: Ask Stacy…, What is it?, Compare…, Where does it come from? ›, What could be wrong? ›, What if…? ›, What can be done? › |
| 8 | `copy` | Copy › | `copy` (gs:253) | The path, address, name or line; copies elsewhere (to a folder, Export, Delivery); cut, paste, select all |
| 9 | `remove` | Remove | `bin` (new) | Trash, Discard draft…, Delete the words. It sits below the menu's only hairline. |

Ask uses Stacy's own question wording, which the Field already uses: Trace asks "Where does “%s” come from, and what rests on it?" (fp:411) and Doubt asks "What could be wrong with “%s”?" (fp:425). "Ask Stacy" goes through `named()`, so it reads Kasandra in that appearance (`workbench/assistant_identity.py`).

### 1.2 The rules

1. **One order, at most 7 lines.** `first_level()` asserts `len <= 7`.
   - The maximum per target is 7 (a file).
   - Places reach at most 4–5, because New and View never appear together with Open, Change and Remove.
2. **Leave out, never grey, at the first level.** A verb whose entries are all unavailable is not shown.
   - The word "unavailable" (cm:1883) goes everywhere.
   - In deeper screens, an unavailable row is also left out. The one exception is an ending that needs fewer rows: its caption says what to do first (section 3.6).
3. **A verb with exactly one action acts directly.**
   - It keeps the verb's word, and its caption names the action, for example "Copy · the name" or "Remove · to the Trash".
   - The inner key is kept on the row (`entry.inner`), so the "nothing lost" check still finds it (section 5.3).
   - Then › is always a panel.
4. **Two popups at most.**
   - Level 1 is the verbs. Level 2 is one panel beside them.
   - A row with › inside a panel **drills in place**: the rows are replaced, and a Back row with the `previous` glyph appears at the top.
   - Today every submenu is a new popup beside its row (cm:2043-2048), and Field › What if › cell › value is 3 deep.
5. **At most 16 rows per screen, and never a scrollbar.**
   - The limit is `rows = min(16, (window height − chrome) // m.row)`.
   - Longer lists split into pages with a "More… (n)" row that drills in place.
   - The DeskMenu scroll area (pq:445-447) stays as a safety net. A test asserts its range is 0.
6. **Captions are a status or a count.** For example "2 rows", "220", "in the Log" or a process name. A caption is never a key (rule 1.4). This replaces "a key, a status, a far address" (cm:110).
7. **The heading names the thing.**
   - It shows the kind glyph plus `label · noun`. The noun has no "revision N" (cm:306, 309); the revision stays in the heading's tooltip.
   - The foot caption "what you can do right here" (cm:54, 1943) goes. It costs about 35 px and says nothing.
8. **Mouse first.**
   - Hovering for 240 ms opens the panel (cm:55, 1888). Clicking a verb opens it at once (cm:1892-1895).
   - Inside a panel, a drill needs a click. Nothing drills on hover, so nothing jumps while you read.
9. **The keyboard is unchanged in spirit.**
   - The Menu key and Shift+F10 still work (cm:2258).
   - Arrows, Home/End, type-to-select and F1 come from DeskMenu (pq:528-580).
   - Right or Enter drills. Left or Backspace goes back one screen; at the panel's root, Left closes the panel, as today (cm:2100-2103). Esc closes the panel.
   - Nothing about keys is printed.
10. **Opening the menu reads nothing.**
    - Today every file right-click dispatches `files.versions` (cm:627).
    - Today hovering Extract runs up to 16 reads (cm:537-555).
    - Today the console's menu runs the last line before it shows (con:445-450 → chm:133).
    - In the new design, a panel reads only when it opens (one `language.offers`) and only for what it shows.

### 1.3 Size, worked out from the constants

These estimates use: row = `max(line, icon) + 2·ROW_PAD` (pq:53); MENU_PX 15 gives a line of about 20; the icon becomes `SIDE` 20 (tf:29), so a row is about 24; a hairline is 9 (pq:37); margins are 6+6.

- **First level of a file:** heading 24 + hairline 9 + 7×24 + hairline 9 + margins 12 ≈ **222 px** (today about 727).
- **Then panel, steps screen:**
  - margins 12
  - slab of up to 3 mono lines, about 72
  - preview of a header plus 3 rows in 13 px print, about 76
  - hairline 9 + Back 24 + 8 steps × 24 + hairline 9 + 6 endings × 24
  - total ≈ **538 px**. That fits a 1366×768 window, which is about 700 px tall maximised; this is an estimate.
- **Value screen:** Back + up to 12 candidates + "Another value…" ≈ 505 px.
- **Width:** the first level follows today's width rule (cm:1977-1984). The panel is at most about 480 px. Two popups fit 1366 px side by side. Today's 4–8 cascades do not.

### 1.4 Icons

- **How a row is painted.**
  - `ContextRow.paintEvent` stops calling `paint_icon` (cm:1910).
  - It paints `tool_faces.icon(key, tone).paint(p, icon_rect, Qt.AlignCenter, mode)`. The mode is Normal, Active when under the pointer, or Disabled.
  - This gives the head menus' neon look: READY ink, TEAL_EDGE accent and the halo (tf:207-219). Today the row is plain TEXT/QUIET ink (cm:1909-1910).
  - The icon is painted, not set with `setIcon`. Otherwise `menus2.rebuild` would turn it into one graphite outline: it repaints every QAbstractButton that has a non-null icon (mn:286-289), and ContextRow is a QAbstractButton (pq:265).
- **The line tone.** `tool_faces.icon(key, tone='line')` uses ink `ROYAL_TEXT`, fill `ROYAL` and halo `ROYAL`.
  - In Kasandra these are #b9a1f6 and #7b4fd8 (bt:51). In Graphite the ROYAL tokens equal TEAL_TEXT #cbf08b (bt:40), so nothing changes there.
  - The cache key becomes `(key, glow, tone)`; today it is `(key, glow)` (tf:198).
  - The line tone is used on: the Then verb, every step, Show it, and the slab's edge.
- **Words or Icons.** The right-click follows the same Buttons choice as the head menus (`STATE['mode']`, tf:233). New workspaces open on Icons (tf:31). With Words chosen, the icon column closes.
- **New glyphs, drawn in the house rules** (one weight, flat caps, solid facets, hexagons; gs:6-16):

  | Glyph | Drawing | Used for |
  |---|---|---|
  | `bin` | A can, lid as an accent facet | Remove |
  | `pause` | Two solid bars | Pause |
  | `sieve` | A funnel with a solid drop at the spout | Keep rows where |
  | `sort` | Three rules from short to long and one head | Sort by |
  | `group` | Three rules gathered by a bracket into one | Group by |
  | `count` | `letters('#')` (gs:384) | Count |
  | `watch` | Straight lids with a diamond pupil, so it is not the `find` lens | Watch it |
  | `join` | Two tables sharing one accent column | Match with a table |

  `EXTRA`, `_extra_paths` and `paint_icon` in cm:1732-1806 are deleted.

---

## 2. Every target: the first level and one level down

In the lines below, `[glyph]` is the icon and `·` introduces a caption. Inside the › lists, "wc" marks rows that appear only on a working copy.

### Files

**A file** (today 24–30 rows) → **7 lines**:

1. `[table]` **Open**. The glyph is `page` for text, `table` for tables, `picture` for a drawing.
2. `[source]` **Open in ›**
   - This computer's app
   - Its folder (only when the file was found by a search)
   - Calculator, KiCad… (the adapters, cm:71-77)
   - The Tool Atlas
   - The Explore workspace
   - The original (wc)
3. `[chain]` **Then ›**, starting from `@files:power.csv`
4. `[cell]` **Change ›**
   - Rename…
   - Move to…
   - Back to a kept version…
5. `[asked]` **Ask ›**
   - Ask Stacy about it…
   - What is it?
   - Compare with…
   - What changed since a kept version? ›
   - Investigate…
   - Put it on the Agenda…
   - Ask Stacy to work on it… (wc)
   - What changed from the original? (wc)
6. `[copy]` **Copy ›**
   - The path
   - The address
   - To a folder…
   - Export a copy…
   - Into Delivery
7. `[bin]` **Remove** · to the Trash. A working copy gets **Remove ›** instead: Move to Trash, Discard this draft… (asks).

**A folder** → 5 lines: Open `[folder]`; Then › (`files.list {"path":…} | pick entries`, fsv:452); Change › (Rename…, Move to…); Copy › (The path, The address, To a folder…, Export a copy…); Remove.

- A folder copy adds: Open in › (A confined look inside…, The original), Ask › (What changed from the original?), Change › (Run a command inside, confined…), Copy › (Back as a pill…), and Remove › with Discard this draft…. That makes 7.
- **A smart folder** → 4 lines: Open; Change · rename…; Copy ›; Remove.

**Two files** → 4 lines:

- Open · side by side, in Compare (Compare revisions or Compare these two, cm:687)
- Change · move them to…
- Copy › (The paths, To a folder…, Into Delivery)
- Remove

With three or more files there are 3 lines; Open is left out.

**The empty place in Files** → 4 lines:

- **New ›**: Folder…, Smart folder…, Import copies of files…, A working copy of a file…
- **Open in ›**: Inquiries, Algorithm & Theory Atlas, The Tool Atlas, The writing line ›
- **Then ›**: start screen with This folder as rows, Yours ›, A file in Files ›
- **View ›**: Thumbnails ✓, List, Machine files too, Look again

### The Finder

- **An entry inside Files** → 5 lines: Open; Open in › (The viewer, Files, adapters); Then ›; Ask · Stacy, about it; Copy · the path.
- **An entry outside Files** → 4 lines: Open, Open in ›, Ask, Copy. The heading noun says "file · read only here".
- **The Finder's empty place** → 4 lines:
  - Open in › (Inquiries, the atlases, The writing line ›)
  - Then ›
  - View › (the views, cm:747; Hidden files too; The preview; Look again)
  - Copy · the path

### The Library

- **A received file** → 3 lines: Open `[stack]`; Ask · Stacy, about it; Copy › (The name, Into Files).
- **Its empty place** → 4 lines: New · receive files…; Open in ›; Then ›; View · look again.

### Documents

**A passage** (today 18 rows) → 5 lines:

1. **Then ›**, starting from `@document:<id> | pick document.blocks | select text`. This is the Field's own form (fsrc:216).
2. **Change ›**, 12 rows with hairlines between the groups:
   - Bold `[bold]`, Italic `[italic]`, Underline `[underline]`, Plain `[plain]`
   - Heading `[h1]`, Subheading `[h2]`, Minor heading `[h3]`, Body `[body]`, Code `[code]`
   - Move to notes `[note]`
   - Undo `[undo]`, Redo `[redo]`
3. **Ask ›**: Ask Stacy about it…, Search for these words
4. **Copy ›**: The words, Cut the words, Paste, Select all, Export a copy…
5. **Remove** · the selected words

**A page, caret only** → 3 lines: Then ›; Change › (the 5 styles, Undo, Redo); Copy › (Paste, Select all, Export a copy…).

### The Field

**A sheet on the work face** (today 13 rows and 7 submenus, 3 deep) → 4 lines:

1. Open, with the kind glyph from `KIND`, for example `table`
2. Then ›, start screen:
   - Its rows: `@office:<id> | rows` for a sheet (section 3.2)
   - Its own line: `obj.stac`
   - Yours › (words that start with `this`)
3. Ask ›
   - Ask Stacy about it… `[asked]`
   - Where does it come from? › `[source]`
   - What could be wrong? › `[found]`
   - What if…? › `[delta]`
   - What can be done? › `[steps]`
   - What feeds it? › `[previous]`
   - What does it feed? › `[next]`
4. Copy ›: Its name, Its line, Its address

On the programs and network faces, the same 4 verbs appear. Open's caption is "in the Log" for a network sheet (cm:1394). Ask has fewer rows there.

**The Field's empty desk, work face** → 3 lines:

- **Then ›**: start screen with the 8 lines of this face (cm:1371-1378) and Yours ›
- **View ›**: Look again `[recalc]`, The programs, The network, Leave the Field `[previous]`
- **Ask ›**: Check the desk `[found]`, The brief `[lines]`

The other faces show 2 lines (Then, View).

### Empty places and the new finders

**Today, the workspace, and any empty place** → 3 lines:

- **New ›**: Idea…, Project…, Import (Ingress)…
- **Open in ›**: Inquiries, Algorithm & Theory Atlas, The Tool Atlas, The writing line › (Assignment, Terminal, Search, Log)
- **Then ›**: Yours ›, A file in Files ›

**A viewer or PDF page** gets a new finder. Today it lands on "an empty place" (find_workspace, cm:1690-1698; PageCanvas pdf_qt.py:15). New → 4 lines: Open in › (Its folder, This computer's app); Then ›; Ask · about this file; Copy · the full path. These come from `viewer_entries` (cc:170-186), which today can only be reached through the "For <file> ›" row of a menu-row right-click (cc:157-161).

**An Office sheet page** gets a new finder built on `OfficePanel.ident` (office_qt.py:82-84) → 3 lines: Then ›; Ask ›; Copy · its address.

### Log, Activity and network

- **A Log event** → Open in › (Its job, in Jobs); Ask · Stacy, about it; Copy · the line. That is 2–3 lines.
  - "The Log" is left out inside the Log itself.
  - Activity adds Open first.
  - Then › is left out in phase 1 (section 6, risk 9).
- **A network connection or packet** → 4 lines:
  - Open in › (This conversation, in the Log; Its program, in the Log · firefox)
  - Then › (`network.observe | pick connections | where process=…`, the Field's form, fsrc:395)
  - Ask
  - Copy · 93.184.216.34:443

### Jobs and Agenda work

- **A running job** → 4 lines:
  - Open · in Jobs (left out in the Jobs list itself)
  - Then › (start screen: Its output `@evidence:…`, Its record `@job:…`; cm:962-964)
  - Change › (Pause, Stop… for a running job; Resume, Stop… for a paused one)
  - Copy · the job id

  An ended job has no Change line.
- **Agenda work** → 4 lines: Open · in the Agenda; Open in · its job, in Jobs; Then › (its stored line); Change › (Pause or Resume; Stop…).

### Trees

**A cabinet record (a project)** → 6 lines:

- Open
- Open in › (Open <workspace> ×M, The Explore workspace)
- Then › (`@<canonical>`, cm:802-808)
- Change · write an idea here…
- Ask › (What is saved here?, the N provider checks)
- Copy › (The identity, Export a copy…)

**The cabinet tree's empty place** → 3 lines: New › (Idea…, Project…, Import…); View › (Logical cabinet, Existing views, Look again); Copy · export a copy….

**The Machine tree:**

- A project → 3 lines: Open, Then ›, Copy · export a copy…
- The Work root → New ›, View
- A computer row → Open in · the Finder; View · look again; Copy · what it says

**A setting** → 3 lines: Open; View › (Expand all, Collapse all, Search settings…); Copy · the key. A settings group gets View › only.

### Programs and head menus

- **A Programs row** → 3 lines: Open; Open in · the Explore workspace; Ask · what is it?
- **A head-menu row** → 2–3 lines:
  - The command's own name: it runs bound to the current work, with today's revision recheck (cc:75-97). On a row that has a submenu, it becomes › and lists the children (cc:100-117).
  - Then ›, only on chain rows.
  - Ask · what does it do?
- **A row of the right-click menu itself:** no meta-menu. F1 describes the row (pq:559-562). Today building that meta-menu closes the menu you were in (cm:2158-2161).

### Surfaces with their own menu

- **The console's output** keeps Qt's Copy and Select All. `chain_menu.fill` (con:449-450) becomes one row, **Then ›**, which opens the same panel on `last_program`. Nothing runs when the menu opens.
- **Agenda rows that ask a line** get the same change (agenda_qt.py:134-141).
- **The worksheet's specialised menu** (sheet_workbench_qt.py:572-640) stays as it is in phase 1.

---

## 3. Then ›: chaining step by step

### 3.1 The panel

A `PipeMenu`, which is a `ContextMenu` subclass, opens beside the Then row. Its top part is fixed:

- **The slab.** A QLabel styled with `bt.line_sheet()`.
  - It shows the line, written out in full and shortened for the eye with `bt.eye()`, which turns `owner:db5f669f…` into `db5f66…` (bt:72-74). The exact line is in the tooltip.
  - The caption on the right is "N rows". When 2 or fewer steps are left (tp:25), it adds "· 2 steps left".
- **The preview.** The first 3 rows and up to 4 columns, in quiet print, then "and N more". It is data, not a line, so it is not on the slab.
- **Back a step `[previous]`.** Present once a step has been added. It removes the last step. Backspace does the same.

Then come the screens, all drilled in place:

1. **Start**, only when a target has several starting points. Readings with counts: "Sheet BOM · 40 rows", "Headings · 12". A CSV has only one reading that gives rows, so it goes straight to Steps.
2. **Steps**: what can come next, then the endings.
3. **Choose**: a column, then its values with counts.

### 3.2 Where a line starts: `line_for(host, target)`

This is one new function. Today the starting lines are scattered (pipes reader §8.1).

| Thing | Starting line(s) |
|---|---|
| File (Files, Finder, viewer) | `@files:REL`, then a reading. The space guard is lifted: today `needs_quotes` greys every pipe row for a name with a space (cm:216-217, 619-625), but an address with spaces parses as the main source (sl:38-44). Only `join` needs one word (tp:10). |
| Folder | `files.list {"path":REL} \| pick entries \| select name,kind,size,modified` |
| Passage, page | `@document:ID \| pick document.blocks \| select text` |
| Office sheet (Field or page) | `@office:ID \| rows`. **New:** for the `office` kind, `addresses.read` adds `data.rows` and `data.sheets`, made by `files_service.keyed` from the cell grid (fsv:268-278; ad:91-100). `office.get` and the Field's reads of every sheet (fsrc:151-153) stay as they are. |
| Other Field sheets | `obj.stac` |
| Cabinet record, Machine project | `@<canonical>` (cm:806, 869) |
| Job | `@evidence:ID` or `@job:ID` (cm:962-964) |
| Agenda work | its `program` |
| Connection | `network.observe \| pick connections \| where process=NAME` |
| Empty place | No line. The start screen offers Yours ›, A file in Files ›, This folder / This face as lines. |

Words and `this` are always written out before anything goes on the slab, using `stac_words.expand` (sw:114-120) and `field_page.expand_this` (fp:388-399). The slab therefore always shows what will run. Today `chain_menu.run/then` do not write them out, so a kept `waits | count` shows as enabled and is then refused (pipes reader §5).

### 3.3 The steps

Each row has plain words and adds one transform to the line. A step is left out when it would change nothing, for example First 5 on 4 rows, or a column whose values are all the same.

| Row | Glyph | Choose screen | Adds | Count shown |
|---|---|---|---|---|
| Keep rows where › | `sieve` | Column, then up to 6 spread values × "at least / at most" for numbers, or the 6 most common values × "is / is not" for text, then "Another value…" | `where F at least V`, `where F=V`, `where F is not V` | On every value |
| Sort by › | `sort` | Column, then smallest or largest first | `sort F` / `sort -F` | |
| Group by › | `group` | "All rows together" or a column, then Count, Sum/Average/Smallest/Largest of a numeric column | `group F \| count`, `sum F` | The value for each total |
| Only some columns › | `select` | Up to 13 columns as on/off rows, then "Keep these" | `select a,b` | |
| Add a column › | `larger` | Preset A − B, A + B, A × B, A ÷ B for numeric pairs, then "A × a number…" | `add NAME = …` | |
| First › | `limit` | 5 / 10 / 20 / 50 / 200 | `take N` | "of N" |
| Count | `count` | (direct) | `count` | The number itself |
| Match with a table › | `join` | A table in Files sharing a column, then the column, then "with a match / without a match" | `join …` / `missing …` | On every choice |
| Look inside › (a single record) | `source` | Its nested lists, for example `document.blocks · 23` | `pick path` | Yes |

Two changes to how values are offered:

- Candidates that keep all rows or no rows are dropped.
- Today, numbers get 4 words × 8 values (chm:208-216) and text gets 3 words × 8 values (chm:218-227). The new screen holds at most 12 rows.
- "Another value…" puts the line so far plus `| where F at least ` into the writing line, which already shows a 4-row preview (s2:1221-1243). In phase 3 this becomes an inline entry.

Two of today's dialogs end the chain: "add a column…" and "choose columns…" (chm:255-264). Both become steps that keep going.

### 3.4 The endings and Stacy's hand

The endings sit under the steps, after a hairline. There are at most 6 rows.

| Ending | Glyph | What runs | Hand rule |
|---|---|---|---|
| Show it | `prompt` | `run_stac(host, line)` (cm:235-249). The answer opens in the working area. A refusal is said as a refusal (cm:245-247). | A read; runs at once. |
| Save as a sheet | `table` | Staged `/chains.save {"text": LINE, "name": TARGET}` (new operation, section 5) | Added to HERS_SHOW. At Do and show it runs at once, with one Undo: the folder goes to the Trash, guarded by item count and both files' sha (s2:2111-2129). At Ask first it waits for Approve. |
| Watch it | `watch` | Staged `/agenda.add {"title":…, "program": LINE, "watch": true, "nice": "background"}`. Same arguments as s2:2832. | `agenda.add` is in HERS_SHOW (sh:39). There is no exact Undo; the card says so (s2:2073-2075). |
| Add to the Agenda | `agenda` | Staged `/agenda.add {"title":…, "program": LINE}` (s2:2888) | Same as Watch it. |
| Keep as a word… | `star` | Asks for a name, then stages `/words.keep {"name":…, "line": LINE}` | `words.keep` is execute scope (sw:32) and is not on her list, so it **waits for Approve**. The card shows why_waits: "it is not among the things I do by myself" (sh:161-164). It also says when the word replaces an existing one (sw:91). |
| Copy › | `copy` | The line; The rows (CSV); The rows for a spreadsheet (tabs); Into the writing line (`inspect_in_line`, cm:222-232); To a command… | To a command…: stages a `files.write` of the answer (with Undo), then puts the command in the Terminal line with the answer path written out, **for you to run**. This follows `run_asked` (s2:2354-2357), because `shell.*` always asks (sh:56). Today a kept `[shell]` runs on one click (chm:299, 311-323). |

Rows over the limit: when the line gives more than 200 rows, Show it, Save as a sheet and Copy › The rows stay visible, with the caption "over 200 · keep fewer first". Their tooltip names the First › step. This is the one deliberate grey in the design, because the count explains it. The limit itself is in tp:272 and sl:112.

Language errors: a parser error says "…not part of Stacy language" (tp:16). It is rephrased in the panel as "A line cannot hold ` $( ; > < or a line break", so the language is never named on screen.

### 3.5 How counts are made: `language.offers` (new read)

```
language.offers {text, field?, page?}  ->  {rows, shown[3], steps_left, lenses[{step, rows}], lists[{step, rows}],
                                            fields[{name, numeric, distinct, low, high}], candidates[{step, words, rows}],
                                            totals[{step, words, value}], model_calls: 0}
```

- It reuses `_compile_plan`, `_joined_plans` and `_execute_plan(..., limit=2000)` (sl:46-57, 74-82, 116-127). The source is read **once**.
- The current rows are kept in memory. Each candidate is applied with `typed_pipeline.apply(rows, [step], 2000)` and counted.
- Readings are counted from the same object with `typed_pipeline.pick` (tp:166-175). Today that costs about 16 runs (cm:537-555, chm:153-166).
- The 200-row cap applies only to answers that go to the window. Counting under the 2000-row source cap (tp:219) is what lets the panel say "1 240 rows" instead of "does not run" (chm:133-135).

### 3.6 Keeping and continuing

**Then › on an empty place** (and on any panel's start screen) shows **Yours ›**:

- The words come first (`words.list`, Kernel).
- The kept `[chain]` lines from the menu file follow (chm:363-391), each captioned "kept chain · then sheet".
- Choosing either one **loads its line into the panel**. You can go on from it, or end it.
- A kept chain's stored ending is shown with the existing "active choice" pencil mark (cm:1913-1916). Today a kept chain runs at once and cannot be continued (chm:449).
- "Edit the list of kept chains…" opens the menu file (chm:496-499).
- A word's own screen has: Go on from it; Forget it…. Forget puts `forget NAME` in the line, as today (cm:1333).

### 3.7 Worked example 1: After Hours 07, the sheet "07 Bench readings"

The data comes from the backup's catalog, `office_documents`: id `owner:db5f669f863d4c71b89fa7ba348957da`, sheet "Reviewed PDF data", cells A1:F5.

Once the cell grid is made into rows, the columns are Parameter, Value, Unit, Conditions, PDF_page and Extraction. `keyed` turns "PDF page" into `PDF_page` and "12" into the number 12 (fsv:257-278).

On the Field, the sheet is kind `sheet` (fsrc:194-196), so its glyph is `KIND['sheet'] = table` (gs:413).

**1. Right-click the sheet.**

```
[table] 07 Bench readings              sheet · current
───────────────────────────────────────────────────────
[table] Open
[chain] Then                                         ›     (line tone)
[asked] Ask                                          ›
[copy]  Copy                                         ›
```

**2. Hover Then (240 ms).** The panel opens. That is one `language.offers {"text":"@office:owner:db5f669f863d4c71b89fa7ba348957da | rows"}`. The start screen is skipped, because only Its rows gives rows; Its own line is offered under Back.

```
▌@office:owner:db5f66… | rows                          4 rows     ← slab (royal purple in Kasandra)
  Parameter          Value  Unit
  Rail voltage          12  V
  Settled current      280  mA
  Startup current      650  mA            and 1 more
──────────
[sieve]  Keep rows where              ›
[sort]   Sort by                      ›
[group]  Group by                     ›
[select] Only some columns            ›
[larger] Add a column                 ›
[count]  Count                        4
──────────
[prompt] Show it
[table]  Save as a sheet
[watch]  Watch it
[agenda] Add to the Agenda
[star]   Keep as a word…
[copy]   Copy                         ›
```

First › is left out because there are only 4 rows. Match with a table › is left out because no other table shares a column.

**3. Keep rows where ›** drills in place. It shows the columns with more than one value. PDF_page and Extraction are the same in every row, so they are left out.

```
[previous] Back
[sieve] Parameter    ›    4 different
[sieve] Value        ›    12 to 650
[sieve] Unit         ›    3 different
[sieve] Conditions   ›    4 different
```

Choosing **Unit ›** asks for one `language.offers` with `field: Unit`. The counts were checked with `worked.py`:

```
[previous] Back · Unit
[sieve] is mA        2 rows
[sieve] is V         1 row
[sieve] is ms        1 row
[sieve] is not mA    2 rows
[sieve] is not V     3 rows
[sieve] is not ms    3 rows
[cell]  Another value…
```

For comparison, the **Value ›** screen would show: at least 110 · 3, at least 280 · 2, at least 650 · 1, at most 12 · 1, at most 110 · 2, at most 280 · 3. The two candidates that keep all 4 rows (at least 12, at most 650) are dropped.

**4. Choose "is mA".** The panel goes back to Steps.

- Slab: `@office:owner:db5f66… | rows | where Unit=mA` · **2 rows**
- Preview: Settled current 280 mA; Startup current 650 mA
- A **Back a step · where Unit=mA** row appears
- Count's caption is **2**

**5. Choose Count.**

- Slab: `@office:owner:db5f66… | rows | where Unit=mA | count` · **1 row**
- Preview: `count 2`
- Every step is now left out, because there is only one row. Only the endings remain.
- 3 of the 7 steps are used, so no "steps left" note shows.

**6. Save as a sheet.** The whole menu closes (cm:2072-2074). Talk shows the staged card (s2:2008-2018):

```
For “07 Bench readings”: save these rows as a sheet.
▌/chains.save {"text": "@office:owner:db5f66… | rows | where Unit=mA | count", "name": "07 Bench readings"}
Done: “Slate/Chains/2026-11-14 2141 07 Bench readings” is in Files.          [Undo]
```

- The dial is at Do and show, which is the default (sh:32). `chains.save` is on HERS_SHOW, so the save runs at once.
- The card says what was done (s2:2055). The act goes into her trail with an Undo (s2:2061-2072).
- At Ask first, the same card waits on Approve instead.
- The folder holds `rows.csv` (`count` / `2`) and `receipt.json`. The receipt has the line, the sources' fingerprints, the seed, `LOCAL_NO_MODEL`, and the original **Bench readings revision** (cwq:314-316).

If you would rather keep the two mA rows themselves, choose Save as a sheet at step 4 instead.

### 3.8 Worked example 2: a CSV file in Files

The file is `power.csv`: `examples/clock_lab/inputs/power.csv`, imported with **New › Import copies of files…**. Its columns are Load, Typical_current and Unit.

**1. Right-click `power.csv`.** The 7 verbs of section 2 appear.

**2. Then ›.** A CSV has a single reading, so the panel opens on Steps.

- Slab: `@files:power.csv | rows` · **3 rows**
- Preview: Controller 120 mA, Display 100 mA, Sensor 30 mA
- Keep rows where › shows only **Typical_current** and **Load**. Unit (always mA) and Basis (always Assumption) are left out.

**3. Keep rows where › Typical_current ›** shows (checked counts):

- at least 100 · 2 rows
- at least 120 · 1 row
- at most 30 · 1 row
- at most 100 · 2 rows

Choose **at least 100**.

- Slab: `@files:power.csv | rows | where Typical_current at least 100` · 2 rows
- Preview: Controller 120, Display 100

**4. Group by › All rows together ›** shows totals worked out from the same single read:

- Sum of Typical_current · 220
- Average · 110
- Smallest · 100
- Largest · 120
- Count · 2

Choose **Sum**.

- Slab: `@files:power.csv | rows | where Typical_current at least 100 | sum Typical_current` · 1 row
- Preview: `sum_Typical_current 220 · count 2`. This is the output shape of tp:262-268.

**5. Keep as a word…** with the name `big-loads`, which fits NAME (sw:29). The staged card shows:

```
/words.keep {"name": "big-loads", "line": "@files:power.csv | rows | where Typical_current at least 100 | sum Typical_current"}
```

It waits for Approve. From then on, the word is in Then › Yours › on every empty place, and choosing it loads the line into the panel.

Choosing **Copy › The line** puts the same line on the clipboard.

**Show it** runs the line in the working area. The answer comes with its own "save as a sheet · watch it · add to the Agenda" (con:473-474). Those words are rerouted to the same staged endings, so every road ends the same way.

---

## 4. Nothing lost: where every entry of today's menus goes

Each entry is listed as **old → new**. "Dropped" means it is gone from the right-click; the reason and its other home follow. `FOLDED` (cm:2267-2307) is rewritten with the new paths, and a new `MOVED` list records the entries that leave the menu.

**A file** (B1, cm:604-663):

- Open / Open pill… → **Open**
- Open with this computer's app → **Open in › This computer's app**
- Show in its folder → **Open in › Its folder**. Shown only after a search; today it is greyed otherwise (cm:607-608).
- Rename… → **Change › Rename…**
- Copy to… → **Copy › To a folder…**
- Move to… → **Change › Move to…**
- Versions… → **Change › Back to a kept version…**
- Export… → **Copy › Export a copy…**
- Inspect in the line → **Then › Copy › Into the writing line**
- Run → **Then › Show it**
- Chain from here → **Then ›**
- Extract › → **the Then start screen**, with counts
- Compare with… → **Ask › Compare with…**
- Compare with a kept version › → **Ask › What changed since a kept version? ›**. It reads versions only when opened.
- Open in <adapter> → **Open in › <adapter>**
- Find tools in the Tool Atlas → **Open in › The Tool Atlas**
- Explore capabilities… → **Open in › The Explore workspace**
- Stage in Delivery → **Copy › Into Delivery**
- Explain this file → **Ask › What is it?**
- Ask Stacy about this… → **Ask › Ask Stacy about it…**
- Investigate… → **Ask › Investigate…**
- Add to the Agenda… → **Ask › Put it on the Agenda…**
- Copy path, Copy the address → **Copy › The path, The address**
- Move to Trash → **Remove**
- Working copy (cm:645-648):
  - Ask Stacy to work on this… → **Ask ›**
  - Review changes to the original… → **Ask › What changed from the original?**
  - Show the original → **Open in › The original**
  - Discard this draft… → **Remove › Discard this draft…** (asks)

**A folder, smart folder or folder copy** (B2, cm:649-663):

- Open, Rename, Copy to, Move to, Export, Copy path, Copy the address, Trash → as for a file
- Look inside, confined… → **Open in › A confined look inside…**
- Run a command here, confined… → **Change › Run a command inside, confined…**
- Return as a pill… → **Copy › Back as a pill…**
- Review the changes… → **Ask › What changed from the original?**
- Show the original, Discard → as for a file

**Several files** (B3, cm:681-693):

- Compare revisions / these two → **Open** · side by side, in Compare
- Copy to → **Copy ›**
- Move to → **Change**
- Stage selected in Delivery → **Copy › Into Delivery**
- Copy paths → **Copy › The paths**
- Trash → **Remove**

**The empty place in Files** (B4, cm:702-710):

- Root menu › is split:
  - Inquiries, the two Atlases, Writing line › → **Open in ›**
  - Your chains › → **Then › Yours ›**
  - Start a chain from › → **Then › A file in Files ›**
  - Edit the Graphite menu… → **Then › Yours › Edit the list of kept chains…**
- New folder, New smart folder, Import, Work on a copy → **New ›**
- View as › → **View › Thumbnails / List**
- Show all files / Hide machine files → **View › Machine files too**
- Refresh → **View › Look again**

**The Finder** (B5–B6, cm:720-752):

- Open → **Open**
- Open in viewer → **Open in › The viewer**
- Show in Files **and** Change it in Files → **Open in › Files**. They are the same call (cm:724, 729).
- Copy path → **Copy**
- Ask Stacy about this file/folder → **Ask**
- Inspect, Run, Extract → **Then ›**
- Adapters → **Open in ›**
- "Nothing changes here · Files keeps its own changes" → dropped as a greyed row. The heading noun says "read only here".
- Empty place: Root › split as in Files; View as, Hidden files, Show/Hide the preview (no more "Space") → **View ›**; Refresh → **View › Look again**; Copy path → **Copy**

**The Library** (B7, cm:760-772):

- Open → **Open**
- Keep a copy in Files → **Copy › Into Files**
- Ask Stacy about this file → **Ask**
- Copy the name → **Copy**
- Empty place: Root › → **Open in / Then**; Receive files… → **New**; Refresh → **View**

**A passage or page** (B8–B9, cm:388-425):

- Bold, Italic, Underline, Plain, the 5 styles (no Paragraph style › level), Move to notes, Undo, Redo → **Change ›**
- Cut, Copy, Paste, Select all → **Copy ›**
- Delete → **Remove**
- Ask Stacy → **Ask ›**
- Search for these words → **Ask ›**
- Export… → **Copy › Export a copy…**
- **Dropped (MOVED):**
  - New document. It lives in Work ▸ New File (mn:21) and on the page's own New document button (document_qt.py:211). It is not the passage's own road (RELEASE_NOTES_0.4.9.md:14-15).
  - Inspect in the line, which handed over raw `/documents.edit` JSON (cm:403-406). Its road is Stacy's strip ("make these words bold", document_qt.py:206): her card shows the exact line on the slab.

**A Field sheet** (B10, cm:1394-1430):

- Open / Show in Log → **Open**
- What feeds it / What it feeds → **Ask › What feeds it? / What does it feed? ›**
- Inspect in the line → **Then › Copy › Into the writing line**
- Run its line → **Then › Its own line › Show it**
- What if › → **Ask › What if…? ›**
- Doubt it › → **Ask › What could be wrong? ›**, first row "All of it, in Talk"
- Trace it › → **Ask › Where does it come from? ›**
- What can be done › → **Ask › What can be done? ›**. A step that writes keeps the status caption "asks".
- Your words › → **Then › Yours ›**
- Ask Stacy about this → **Ask ›**
- Copy its name → **Copy ›**
- **Dropped (MOVED):** The brief of the desk, on a sheet. It is about the desk: it is on the empty desk's Ask › and on the Field foot (field_qt.py:507-523).

**The Field's empty desk** (B11, cm:1354-1389):

- Look again, Show the programs/network, Back → **View ›** (Look again; The programs; The network; Leave the Field)
- Check the desk, The brief → **Ask ›**
- This face as lines › → **Then › start screen**
- Your words › (Run it / In the line / Forget it / Keep a new word…) → **Then › Yours ›** (Go on from it; Forget it…) and the **Keep as a word…** ending

**Today, the workspace, empty places** (B12, cm:1197-1225):

- Your chains › → **Then › Yours ›**
- Start a chain from › → **Then › A file in Files ›**, in pages of 14 with More…
- Writing line › → **Open in › The writing line ›**
- Edit the Graphite menu… → **Then › Yours › Edit the list…**
- Inquiries, Algorithm & Theory Atlas, Tool Atlas → **Open in ›**
- New Idea… / New Project… / Import (Ingress)… → **New ›**

**The Log and Activity** (B13, cm:1110-1137):

- Ask Stacy about this → **Ask**
- Show in Log → **Open in › The Log**
- Its job › → **Open in › Its job, in Jobs**. That is where its own Pause/Resume/Stop live; one right-click away instead of a submenu.
- Copy → **Copy**
- Activity's Open → **Open**
- Follow this conversation → **Open in › This conversation, in the Log**
- Show the process → **Open in › Its program, in the Log**
- Copy address → **Copy**

**Jobs and Agenda work** (B14, cm:965-978, 1040-1057):

- Show in Jobs → **Open**
- Inspect output → **Then › Its output**
- Pause, Resume → **Change ›**
- Stop → **Change › Stop…** (asks)
- Inspect in the line → **Then › Copy › Into the writing line**
- Copy the job id → **Copy**
- Open Agenda → **Open**
- Its job › → **Open in › Its job**

**Cabinet, Machine and Settings** (B15, cm:783-892; cabinet_actions.py:50-81):

- Open → **Open**
- Read saved details → **Ask › What is saved here?**
- Write an idea here… / Name a new project… → **Change**
- Provider checks → **Ask ›**
- Open <workspace> → **Open in ›**
- Explore all capabilities, plus Activity's extra Explore (cm:1438), which was a double → **Open in › The Explore workspace**
- Inspect, Run → **Then ›**
- Export (Egress)… → **Copy › Export a copy…**
- Copy the identity → **Copy**
- Refresh, View as, New Idea, New Project, Import → **New / View on the tree's empty place**. They are also under Arrange ▸ Cabinet (mn:107-108, 230) and the Work menu (mn:21). On a record row they are dropped as a third road.
- Machine: Open, Inspect, Export, New…, Refresh, Show in the Finder, Open Settings, Copy what it says → as in section 2
- Settings: Open this setting, Copy the key, Expand all / Collapse all / Search settings… → **Open, Copy, View ›**

**Programs rows and menu rows** (B16, cc:146-185):

- Inspect this capability/command → **Ask · what is it? / what does it do?**. The inspector no longer prints "Shortcut:" (cc:125).
- Open capability / Run this command → **Open**, or the command's own name
- Choose an operation › → **slot 1 ›** (the children)
- Continue this chain → **Then ›**
- Explore supported operations → **Open in › The Explore workspace**
- Viewer rows (Show enclosing folder, Copy full path, Ask about this file, Build a chain from this file, Read and transform) → **the new viewer finder**: Open in, Copy, Ask, Then
- **Dropped (MOVED):**
  - For <work> ›, which repeats the whole menu of the work. The work's own right-click is one move away, and Open keeps the binding to the work (cc:75-97).
  - The meta-menu on a right-click row. F1 says what the row does.

**The chain builder** (chm:128-196, 269-350):

- The greyed header → **the slab**
- Build on the desk… → **the panel itself**. The tray stays for the worksheet (cwq:130-135).
- where, sort, group by, select, add a column, join with, take, count → **the steps**
- then › console, sheet, watch, Agenda → **the endings**
- shell › → **Copy › To a command…** (asks)
- keep this chain… → **Keep as a word…**
- copy the line → **Copy › The line**

**Unchanged:** Qt's text-field menus, Master Stop, Lab, Adaptive, the meters and the companion (B17).

---

## 5. Build plan

### 5.1 Phases

**Phase 1: the verbs, glyphs and rules**

- **gs:** draw `bin`, `pause`, `sieve`, `sort`, `group`, `watch` and `join`; add `count = letters('#')`. Register them in `GLYPHS` (gs:394-410).
- **tf:** add `tone` to `icon()` (tf:196-220). The `'line'` tone uses ROYAL_TEXT, ROYAL and ROYAL_INK. The cache key becomes `(key, glow, tone)`.
- **cm, Entry:** reuse Entry, adding slots `verb`, `tone` and `inner` (cm:112-118). Drop the "Through Kernel.dispatch" line from tooltips (cm:123); F1 still shows the operation through `descriptor` (pq:543-549).
- **cm, verbs:** add `VERBS`, `MOST = 7`, `SCREEN_ROWS = 16` and `first_level(target, entries)` (collapse, leave out). `entries_for` keeps PROVIDERS and the first-key-wins rule (cm:1449-1461) but groups by verb instead of SECTIONS (cm:51).
- **cm, providers:** every provider tags each Entry with its verb. That is the 219 call sites, done mechanically.
- **cm, ContextRow** (cm:1879-1919): paints glyphs; the caption is never "unavailable"; no hover drill inside a panel.
- **cm, ContextMenu** (cm:1922-2135):
  - one hairline, before Remove only
  - no foot caption
  - icon size `SIDE`
  - `open_child` drills in place when `self.parent_menu is not None` (new `drill`, `back` and `paginate`)
  - Heading uses the kind glyph; the noun has no revision
- **cm, cleanup:** delete `EXTRA`, `_extra_paths` and `paint_icon` (cm:1732-1806).
- **cm, finders:** add `find_viewer` and `find_office` to FINDERS (cm:1701-1702).
- **cm, `change_staged(host, target, words, line, scope, check)`:** used for job and Agenda Stop. The `check` is today's `job_now` / `queued_now` (cm:901-907, 1015-1022).
- **s2:** `stage`/`run_staged` get a `card.check` hook that is called before dispatch. A Refused there is said, and nothing runs (s2:2032-2042).
- **Keys out:** remove every key caption and key tooltip (the 27 sites in `keys_scan.py`); cc:125 "Shortcut:"; and s2:1230 "Ctrl+Enter keeps this word" becomes "run it to keep this word".
- **cc:** `entries` and `viewer_entries` take verbs; the meta-menu on a ContextRow goes (cc:53-57).
- **mn:** fix the stale docstring (mn:7-8).
- **FOLDED** is rewritten to the new paths, and **MOVED** is added (cm:2267-2307).

**Phase 2: the pipe**

- **sl:** add `language.offers` (read) to FIELDS and SCOPES (sl:5-7) and `offers()`. It is registered through the existing `stacy_language` entries (ek:35, 210, 606). Record it in `docs/GRAPHITE_0.1_REGISTRY.json` with `tools/record_registry.py`.
- **ad:** in `read`, for `office` table objects, add `data.rows` and `data.sheets` using `office_service.rows_of(object)` (new), which reuses `files_service.keyed`.
- **New module `workbench/chain_save.py`** for `chains.save` (execute):
  - It runs the line and refuses at 200 rows or when a source view was cut short. This logic moves from cwq:306-309.
  - Source fingerprints use the logic of cwq:42-60, moved into the Kernel.
  - It writes the folder with `rows.csv` and `receipt.json` and returns `{path, kind: 'folder', rows, sha256}`.
  - It is registered the same way (ek) and in the registry.
- **sh:** add `'chains.save'` to HERS_SHOW (sh:39-40). `takes_back` returns `/files.trash {"path": folder}` (sh:193-203). `guard` returns `[{'path': folder, 'items': 2}, {'path': …/rows.csv, 'sha256': …}, {'path': …/receipt.json, 'sha256': …}]` (sh:206-215). UNDOES does not change.
- **cm:** add `line_for`, `PipeMenu` (with `Slab` and `Preview`), and `pipe_start`, `pipe_steps`, `pipe_fields`, `pipe_values`, `pipe_totals`, `pipe_endings`. They return Entries, so the "nothing lost" walker can follow them. The endings reuse `run_stac`, `inspect_in_line`, `copy_text` and `SlateFace.stage`.
- **chm:**
  - keep `parse_menu`, `menu_path`, `edit_menu_file`, `shell_lines` and `stock_methods` (chm:283-292, 331-429, 496-499)
  - `open_here` opens a PipeMenu (chm:502-509); the hidden key keeps working (chm:518)
  - retire `Chain`, `fill`, `lenses`, `shape`, `where_*`, `join_tables`, `choose_columns` and `add_column` from every menu (chm:99-264)
  - `then` routes to the staged endings (chm:269-280)
  - `chain_icons` is no longer used by any menu
- **con:445-451 and agenda_qt.py:134-141:** a single "Then ›" row. **con:473-474 and s2:2818-2820:** the staged endings.

**Phase 3: Undo and one store** (hard; see risks 3 and 8)

- Undo for `files.rename`, `files.move` and `files.copy`: new UNDOES lines with guards. This is security-sensitive (sh:218-229, `clean` sh:265-275).
- Words become the one store, and `[chain]` lines migrate with their ending noted.
- `this` means the sheet itself (fp:399).
- An inline "Another value" entry.
- Then › for Log events, once `ledger.journal.read`'s shape is checked.

### 5.2 Tests

The owner's standing decision is "No new test suites by default" (docs/BOSS_IMPLEMENTATION_PLAN.md:12). So these are additions to the existing `tcm` and `tsh` files.

**Pure checks (no window):**

```python
# tcm Rules
KEY = re.compile(r'\b(Ctrl|Shift|Alt|Meta|Cmd|Esc|Enter|Return|Space|Backspace|F\d{1,2})\b|^[A-Z0-9`]$|\(([A-Z])\)'
                 r'|\b[A-Z] / [A-Z]\b|^Shortcut:|\b[A-Z] (shows|tells|does)\b')
def test_no_entry_literal_prints_a_key(self):          # the AST walk of keys_scan.py over cm, cc, chm
    self.assertEqual(key_literals(['workbench/context_menu.py','workbench/command_context.py','workbench/chain_menu.py']), [])
def test_the_verbs_are_one_list_in_one_order(self):
    self.assertEqual([v for v,_,_ in cm.VERBS], ['new','open','openin','then','change','view','ask','copy','remove'])
    self.assertEqual(cm.MOST, 7)
def test_every_glyph_the_menu_names_is_drawn(self):
    from workbench.glyph_set import GLYPHS, KIND
    for key in cm.glyph_keys():                          # every icon= in cm/cc, every VERBS glyph
        self.assertTrue(key in GLYPHS or key in KIND, key)
    self.assertFalse(hasattr(cm, 'EXTRA')); self.assertFalse(hasattr(cm, 'paint_icon'))
    for key in ('bin','pause','sieve','sort','group','count','watch','join'):self.assertIn(key, GLYPHS)
# tsh
def test_a_saved_sheet_is_hers_to_show_and_goes_back_to_the_trash(self):
    self.assertTrue(hand.hers('show','execute','chains.save')); self.assertFalse(hand.hers('ask','execute','chains.save'))
    r = {'path':'Slate/Chains/2026-11-14 2141 x','kind':'folder','sha256':{'rows.csv':'a'*64,'receipt.json':'b'*64}}
    back = hand.takes_back('chains.save', {'text':'@files:a.csv | rows'}, r)
    self.assertEqual(back, '/files.trash {"path": "Slate/Chains/2026-11-14 2141 x"}')
    self.assertTrue(hand.undo_allowed(back, hand.guard('chains.save', {'text':'@files:a.csv | rows'}, r)))
```

`chains.save` must also appear in the registry document, because tsh:47 requires every name on her list to be a real operation.

**Kernel checks (`tcm`, using its existing `call` helper, tcm:96):**

```python
def test_offers_counts_from_one_read_equal_the_runs(self):        # power.csv fixture = examples/clock_lab/inputs/power.csv
    with Recorder(self.k) as rec: r = call('language.offers', {'text':'@files:power.csv | rows','field':'Typical_current'})
    self.assertEqual([(c['step'],c['rows']) for c in r['candidates']],
        [('where Typical_current at least 100',2),('where Typical_current at least 120',1),('where Typical_current at most 30',1),('where Typical_current at most 100',2)])
    self.assertEqual(rec.ops().count('files.get'), 1); self.assertEqual(r['model_calls'], 0)
    for c in r['candidates']:self.assertEqual(c['rows'], len(call('language.run',{'text':'@files:power.csv | rows | '+c['step']})['rows']))
def test_an_office_sheet_reads_as_rows(self):                     # fixture: the four reviewed rows of 07 Bench readings
    self.assertEqual(call('language.run',{'text':'@office:%s | rows | where Unit=mA | count' % SHEET})['rows'], [{'count':2}])
    self.assertNotIn('data', call('office.get',{'id':SHEET}))      # office.get itself is unchanged
```

**Window checks (`tcm`):**

```python
EXPECTED = {'file':['open','openin','then','change','ask','copy','remove'], 'folder':['open','then','change','copy','remove'],
            'smart':['open','change','copy','remove'], 'files':['open','change','copy','remove'], 'empty:files':['new','openin','then','view'],
            'passage':['then','change','ask','copy','remove'], 'page':['then','change','copy'], 'empty:today':['new','openin','then'],
            'finder':['open','openin','then','ask','copy'], 'library':['open','ask','copy'], 'connection':['openin','then','ask','copy'],
            'job:running':['open','then','change','copy'], 'job:jobs-list':['then','change','copy'], 'field-sheet':['open','then','ask','copy'],
            'field-empty:work':['then','view','ask'], 'setting':['open','view','copy']}
def test_first_level_is_at_most_seven_verbs_in_one_order_none_greyed(self):
    for kind, menu in self.every_menu():                  # the targets the existing tests already build
        keys = [e.key for e in menu.entries]
        self.assertEqual(keys, EXPECTED[kind], kind); self.assertLessEqual(len(keys), 7, kind)
        self.assertTrue(all(e.enabled for e in menu.entries), kind)
def test_no_row_prints_a_key(self):
    for kind, menu in self.every_menu(open_all=True):     # every verb panel and every drilled screen
        for row in menu.findChildren(cm.ContextRow):
            for text in (row.word, row.caption, row.toolTip()):self.assertIsNone(KEY.search(text or ''), (kind, row.word, text))
    self.assertNotIn('Shortcut', cc.describe_text(self.w, some_command_target))
def test_every_row_wears_a_drawn_glyph(self):
    for kind, menu in self.every_menu(open_all=True):
        for row in menu.findChildren(cm.ContextRow):self.assertFalse(tool_faces.icon(row.entry.icon, row.entry.tone).isNull(), (kind,row.word))
        self.assertEqual(menu.row('then').entry.tone if menu.row('then') else 'line', 'line')
def test_menus_fit_1366x768_without_scrolling_and_two_popups_at_most(self):
    self.w.resize(1366,768);settle()
    for kind, menu in self.every_menu(open_all=True):
        self.assertEqual(menu.scroll.verticalScrollBar().maximum(), 0, kind)
        self.assertTrue(QRect(self.w.mapToGlobal(QPoint(0,0)), self.w.size()).contains(menu.frameGeometry()), kind)
        self.assertLessEqual(sum(1 for t in QApplication.topLevelWidgets() if isinstance(t, cm.ContextMenu) and t.isVisible()), 2, kind)
def test_opening_reads_nothing(self):
    with Recorder(self.k) as rec: menu = right_click(view.viewport(), point('lost.csv'))
    self.assertFalse({'files.versions','language.run','language.offers'} & set(rec.ops()))
def test_then_on_the_bench_sheet_filters_counts_and_saves_with_undo(self):
    panel = self.open_then(field_sheet)
    self.assertEqual(panel.slab.styleSheet(), bt.line_sheet()); self.assertEqual(panel.line, '@office:%s | rows' % SHEET)
    self.assertEqual(panel.count.text(), '4 rows')
    panel.choose('step:where'); panel.choose('field:Unit'); self.assertEqual(panel.row('where Unit=mA').caption, '2 rows')
    panel.choose('where Unit=mA'); self.assertTrue(panel.line.endswith('| where Unit=mA')); self.assertEqual(panel.row('step:count').caption, '2')
    panel.choose('step:count'); panel.choose('end:sheet'); card = self.w.shell2.face.last_card
    self.assertEqual(card.step.line, '/chains.save ' + json.dumps({'text': '@office:%s | rows | where Unit=mA | count' % SHEET, 'name': '07 Bench readings'}, ensure_ascii=False, separators=(', ', ': ')))
    self.assertTrue(card.ran); self.assertEqual(files_text(card, 'rows.csv'), as_csv([{'count': 2}]))
    card.back.click(); self.assertTrue(card.undone)
def test_stop_asks_and_rechecks_the_state_at_approve(self):
    with Recorder(self.k) as rec: open_change(job_menu).row('job:stop').click()
    self.assertNotIn('jobs.cancel', rec.ops()); card = self.w.shell2.face.last_card; self.assertIsNone(card.ran)
    card.run.click(); self.assertEqual(rec.ops().count('jobs.cancel'), 1)
    # the same with the job's state moved before Approve: refused, jobs.cancel never dispatched
```

The existing `test_nothing_is_lost_from_the_old_menus` (tcm:594-629) changes in three ways:

- `menu_tree` (tcm:708-717) also records `prefix + e.key + '/' + e.inner` for collapsed verbs.
- The pinned path changes from `'root/menu:edit'` (tcm:621) to `'then/yours/menu:edit'`.
- Every `MOVED` home is checked to exist: `host.a_new` exists, the document tab has `new_word`, and the Field foot has `B`.

`tools/check_context_menu_ui.py` (the owner's screen captures) has to be updated alongside.

---

## 6. Risks: what is hard

1. **Muscle memory and depth.** Rename, Copy path and Trash were one click in a long menu. Now Rename is Change › Rename… (two clicks). I believe less scanning wins, but that is a bet the owner should judge on the ThinkPad.
2. **Drill-in-place is new behaviour inside DeskMenu.**
   - Rows are replaced, the height is measured again and the left edge is held.
   - Focus must land on the first row and pagination must follow the window height.
   - It cannot be checked on screen until Qt may be started. Every height in this document is an estimate.
3. **The hand rules apply even to your own clicks.**
   - At Ask first, your own Save as a sheet waits for Approve, because the rules are followed as written (sh:150-158).
   - Keep as a word always waits, because `words.keep` is not on her list.
   - If that proves heavy, an `owner=True` path through `stage` is a deliberate change to the rules, not an accident.
4. **The count read is synchronous.** `language.offers` reads the source once, on the window's thread.
   - For a CSV of up to 2000 rows that should be small, but this was not measured.
   - Moving it to a worker thread depends on whether `Kernel.dispatch` is safe off the GUI thread, which I did not verify.
5. **Office rows are stored values.**
   - `office.get` itself says `STORED_VALUES_ARE_NOT_RECALCULATION_EVIDENCE` (osv:60), so the panel's preview must say "stored values" for an office sheet.
   - The header comes from the first non-empty row (fsv:268-278), which fits reviewed sheets but not every hand-made sheet.
6. **`chains.save` is a new execute operation.** It needs the registry document, tsh:47, its own `receipt.json`, and an Undo guard over two files. The folder layout also changes today's two homes for saved answers (s2:2822-2829 and cwq:306-335) into one.
7. **FOLDED, MOVED and the captures.** The rewrite touches 74 FOLDED tuples, the pinned test path and `check_context_menu_ui.py`. "Nothing removed" (RECORD_OF_DIRECTIONS.md:213) is kept by moving entries to deeper levels. The MOVED entries (New document, the raw Inspect line, For <work> ›, the brief on a sheet, tree words on record rows, the right-click meta-menu) still need the owner's yes.
8. **Two stores for kept lines remain until phase 3.** Kept `[chain]` lines keep their stored endings. Words have none. Undo for rename, move and copy is not in phase 1, because widening UNDOES is security-sensitive (sh:218-229).
9. **Gaps that stay open:**
   - Then › on Log events (`ledger.journal.read`'s shape and its 200 limit were not checked).
   - `this` still reads only the first step of a sheet's line (fp:399). The panel sidesteps this by writing the full line on the slab.
   - The worksheet's own menu keeps its look in phase 1.
10. **Words or Icons.** If the owner has Words chosen, the right-click shows no glyphs, following the head menus. "With right click icons too" may mean always. That is one line to decide, and the default (Icons, tf:31) satisfies the request.