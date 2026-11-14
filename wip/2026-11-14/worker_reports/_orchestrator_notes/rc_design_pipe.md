# Design C: the pipe panel. Right-click a thing, build its line, end it somewhere

I only read the repository `/home/user/Struthio`. I did not start Qt, the window or any check. Every number below comes from one of three places, and each is labelled:
- **(read)** read from code or data;
- **(run)** computed by running the real parser and `apply()` from `sdk/cli/arc1cli/typed_pipeline.py`, loaded by file path under `python3 -I`;
- **(est.)** estimated from the size constants.

My scratch files are:
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/panel/worked.py`: both worked examples through the real parser.
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/panel/offers.py`: chips and counts worked from rows read once, plus the step-removal check.
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/panel/keys_ast.py`: the no-key check run against today's source. It finds 39 hits in `context_menu.py` and 1 in `command_context.py`.

The After Hours 07 rows come from the copy of its records already in the scratch folder: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/ah07_catalog.sqlite3`, table `office_documents`, id `owner:db5f669f863d4c71b89fa7ba348957da`. That id matches `AH07_IDS['sheet']` in `tools/campaign_lib/fixture.py:29`.

Abbreviations:
- **cm** `workbench/context_menu.py`
- **cc** `workbench/command_context.py`
- **chm** `workbench/chain_menu.py`
- **pq** `workbench/programs_qt.py`
- **tp** `sdk/cli/arc1cli/typed_pipeline.py`
- **sl** `workbench/stacy_language.py`
- **sh** `workbench/stacy_hand.py`
- **s2** `workbench/shell2.py`
- **tf** `workbench/tool_faces.py`
- **gs** `workbench/glyph_set.py`
- **bt** `workbench/boss_theme.py`

---

## 0. In one page

1. **One panel instead of a menu tree.** A right-click opens one popup at the pointer. It has four parts:
   - **head**: the thing, its glyph and what it is;
   - **do row**: at most 6 ordinary actions plus **More**;
   - **body**: by default the thing's line on its royal slab, with next-step chips that show counts and a live preview;
   - **foot**: where the line ends (Show, Sheet, Note, Watch, Agenda, Word, ⋯).

   Anything that used to cascade opens *inside the same panel*, as a page with a back chip. No second popup ever opens beside it.
2. **The chain is the panel.** Each click adds one step to the line on the slab:
   - Clicking a step on the slab goes back to that step.
   - × removes a step if nothing after it depends on it. Backspace removes the last step.
   - The 7-step budget shows as seven diamonds (tp:25).
   - One road replaces today's nine ways in to the pipe (Inspect, Run, Chain from here, Extract, Start a chain from, Your chains, Build on the desk, Continue this chain, Read and transform).
3. **Reads happen once.** The panel reads the thing's source once, through `Kernel.dispatch` (`language.parse` and then the plan's own read). Every count and preview after that is worked locally by the *same* `typed_pipeline.apply` that `language.run` uses (sl:126).
   - Choosing a value no longer means 32 synchronous runs (chm:212-216). It means 0 more reads.
   - Endings run the line through the Kernel again with `expected_seed` and the source fingerprint check (`chain_workbench_qt.py:227-234`).
4. **Graphite's own glyphs, in the theme's colours.** Every row, chip and ending wears a `GLYPHS`/`KIND` glyph (gs:394-415), painted the way `tf.icon` paints them (tf:196-220).
   - I add **9 glyphs** in the house style: trash, pause, filter, sort, count, group, watch, trace, columns.
   - Rows that run or show a line use the **line tone**: `ROYAL_TEXT` ink and `ROYAL` fill in Kasandra (bt:51). In Graphite those tokens equal `TEAL_TEXT` (bt:40), so nothing changes there.
   - The two picture sets used today (`EXTRA` cm:1732-1806, `programs_qt._icon_paths` pq:134-260) and the chain cascade's fixed hex colours (`chain_icons.py:7`) leave the right-click entirely.
5. **No key is printed.** Every key caption goes: today there are 31 rows from 24 call sites, plus "until Esc", "Enter asks", "(G)", "X/T/D shows" and the Command inspector's "Shortcut:" (cc:125). Two tests guard this, one static (AST) and one live.
6. **Changes follow the hand.** Each ending that changes something goes through `SlateFace.stage(…, asked=True)` (s2:1991-2030), so it gets a trail line and an Undo where `stacy_hand.takes_back` knows one (sh:193-215). What cannot be undone asks inside the panel, in the words of `ALWAYS_ASKS`:
   - Stop on a job or on Agenda work, which today dispatches `*.cancel` at once (cm:974, cm:1045 against sh:52);
   - Discard this draft;
   - Forget a word;
   - Run in the Terminal.
7. **It fits with no scrolling.** The largest page is about 400 px tall and 680 px wide at 14 pt (est.). Long lists never scroll: they show their best 10 and a filter field narrows them. Tests assert `verticalScrollBar().maximum() == 0` on every page at 1366×768.
8. **Honestly hard** (detail in §6):
   - a line may answer at most 200 rows (tp:272) while the panel can count up to 2000;
   - an Office sheet has no "rows" reading today (tp:12), and a reviewed sheet's rows are *what the page said*, not today's cells;
   - reviewed values are text, so Sort orders `110` before `12` (run);
   - six edited files are seed inputs and need `build_seed` (stacy_foundation.py:531);
   - three owner decisions on Undo and on the hand rules.

---

## 1. The panel

### 1.1 Anatomy

At 14 pt the panel is about 640–680 px wide (est.). The example is a CSV file in Files:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ▦ parts.csv                                               table      ⊥pin │  head: KIND glyph, name, noun
│ [▦ Open] [▭ Its app] [✎ Rename…] [⧉ Copy path] [▯ Trash] [? Ask] [⋯ More]  │  do row: ≤6 + More
├──────────────────────────────────────────────────────────────────────────┤
│ [⊽ Keep rows where…] [⇅ Sort…] [# Count 3] [⬡ Group by…] [▥ Columns…]     │  next steps (verbs)
│ [≤ First…] [Σ Add a column…] [⊂⊃ Match with…]                              │
│ [⊽ Need over Have · 1] [⊽ Need over 1 · 1]                                 │  suggestions, with counts
│ ┃ >_ @files:parts.csv | rows ×                     3 rows  ◆◇◇◇◇◇◇ ┃ [▶ Show]│  the line on its slab + first ending
│   Part        Need  Have                                                   │  preview: ≤4 rows, ≤5 columns
│   Controller  1     1                                                      │
│   Display     1     1                                                      │
│   Sensor      2     1                                                      │
│            [▦ Sheet] [✎ Note] [◉ Watch] [☑ Agenda] [✦ Word] [⋯]             │  endings, at the slab's right end
└──────────────────────────────────────────────────────────────────────────┘
```

The glyphs in brackets stand for GLYPHS keys; §1.3 has the exact map.

**Head**
- It shows the target's `KIND`/`GLYPHS` glyph, its label, and its noun in quiet print. The noun no longer carries "revision N" (cm:306, 309). The target still holds the revision in `Target.revision`, and changes still carry it.
- The **pin** at its right end turns the popup into a `Qt.Tool` window that stays open while you look at things. It replaces the chain QMenu's tear-off strips (chm:104, 141, 171…).

**Do row**
- At most 6 buttons plus **More**. Each is a glyph and a short word; the full words are in the tooltip and the accessible name.
- If the words do not fit one row at the panel's width, the row wraps to a second row (never a third).
- A row that cannot apply to this thing at all is not shown. Example: Pause on an ended job is hidden, where today it is greyed and prints "unavailable" (cm:1883).
- A row that could apply but not now is dim, and its reason is the tooltip.

**Body** shows one page at a time:
- **pipe**: the default whenever the thing has a line (§3);
- **a verb's page**: Trace it, What if, Doubt it, What can be done, Its job, Compare with a kept version, View as, Writing line, Choose an operation, For ‹work›. These hold at most 12 rows. A two-level drill shows a breadcrumb such as "What if › B3 · Settled current".
- **More**: every remaining entry in up to three columns, under the section words. Today `SECTION_WORDS` is defined (cm:52-53) and never shown; here it is shown.
- **asks**: a confirmation, for what cannot be undone;
- **picker**: the choices for one step: column, then comparison, then value, each with a count. The slab stays visible underneath.

**Foot**: the endings. They appear only on the pipe page.

### 1.2 Sizes, placement, fit

The numbers come from `pq.metrics` (pq:45-54): row ≈ 24, rule 9, margin 6, `MENU_PX` 15. The glyph grows from 16 px to 20 px, which is its design size (tf:29; gs:9). Because a row's height is `max(line, icon) + 2·ROW_PAD` (pq:53), the bigger glyph costs nothing at 14 pt.

| Page | Height (est.) | Width (est.) |
|---|---|---|
| Head + do row only (event, setting, network) | 6+32+32+6 ≈ 76–110 | 360–520 |
| Pipe page (head, do, 2 verb rows, suggestions, slab, 4-row preview, endings) | ≈ 383 | ≈ 640 |
| Picker (10 columns shown + filter field, slab, endings) | ≈ 400 | ≈ 640 |
| More, 15–24 entries in 2–3 columns of ≤ 12 | ≈ 330 | ≈ 640 |
| Passage (head, a glyph strip, one row of words) | ≈ 110 | ≈ 520 |

- The panel opens at the pointer and is **shifted, never flipped**, to stay inside the host window. This reuses the clamp in cm:2009-2011, and `bounds()` (cm:1992-1996).
- At interface scale 1.4 the tallest page is about 560 px. That is still under the room between the bands on a 1366×768 screen at that scale, but tight (§6).
- The panel subclasses `DeskMenu` (pq:431-451) to keep its popup, keyboard, F1 and type-to-select. Its `QScrollArea` must never scroll, and a test asserts it.

### 1.3 Glyphs: Graphite's own, in the theme's colours

**How they are painted**
- Buttons and chips paint the glyph themselves, through a new `tool_faces.paint_glyph(p, rect, key, state, tone)`. It uses the scaled draw already in `field_qt._glyph` (field_qt.py:1299-1304) and the colours by state from tf:207-208:

  | State | Ink | Fill | Halo |
  |---|---|---|---|
  | At rest | `READY` | `TEAL_EDGE` | 0.10 |
  | Under the pointer | `TEAL_TEXT` | `READY` | 0.18 |
  | Dim | `LINE_MID` | `LINE` | none |

  With `tone='line'` the ink and fill become `ROYAL_TEXT` and `ROYAL`.
- Because nothing calls `setIcon`, `menus2.paper_icon` (menus2.py:286-289) and `setIconVisibleInMenu` (menus2.py:284) never touch the panel. As a guard, the panel's buttons also carry `paperIcon=True`.
- The panel shows glyphs whatever **Buttons ▸ Words | Icons** says, because the owner asked for "right click icons too". The one exception is under Words: the glyph-only strips (passage formatting, Undo/Redo) show their words instead.

**Map: Entry.key, part before ':', to glyph.** All are existing keys except those marked *new*.

| Glyph | Used for |
|---|---|
| target `KIND` | open, field:open |
| `window` | open:outside, process |
| `page` | open:viewer |
| `source` | show:*, job:show, copy:original, viewer:folder, show:finder |
| `cell` | rename, menu:edit, line:slate |
| `copy` | copy:path, copy:paths, copy:address, copy:id, copy:name, copy:key, copy:row, edit:copy, field:copy, viewer:path |
| `folder` | copy:to, move:to, new:folder, new:project |
| `delta` | versions, compare:version, field:whatif |
| `export` | export, doc:export, delivery:stage, copy:pill |
| `again` | compare:with, compare:two, compare:revisions, copy:review |
| `rooms` | adapter:*, explore, cabinet:explore, cabinet:workspace:*, command:atlas, field:face:programs |
| `book` | atlas, algorithms |
| `info` | explain, cabinet:record, command:inspect |
| `asked` | ask, field:ask, copy:slate, viewer:ask, inquiries |
| `find` | investigate, search, new:smart, copy:look, line:find |
| `agenda` | agenda (the Agenda's own row) |
| `trash` *new* | trash, copy:discard |
| `receive` | import, keep (Library), work:copy |
| `sliders` | view, open (setting) |
| `full` | view:all, hidden |
| `split` | preview |
| `recalc` | refresh, field:again |
| `bold`, `italic`, `underline`, `plain` | mark:* |
| `h1`, `h2`, `h3`, `body`, `code` | style:* |
| `note` | notes, cabinet:write, new:idea |
| `undo`, `redo`, `cut`, `paste`, `select` | edit:* |
| `close` | edit:delete |
| `document` | doc:new |
| `lines` | job:output, field:brief, line:log |
| `pause` *new* | job:pause, queued:pause |
| `running` | job:resume, queued:resume, job (Its job), command:invoke |
| `stop` | job:stop, queued:stop |
| `reach` | follow |
| `found` | field:doubt, field:check, cabinet:check:* |
| `trace` *new* | field:trace |
| `steps` | field:do |
| `star` | words, field:words, chains (Your lines) |
| `port` | field:face:network |
| `previous` | field:back, the "from" rows of a trace |
| `next` | the "to" rows of a trace |
| `prompt` | line:shell, the slab's "in the line" mark |
| `chain` | start, Match with… |
| `more` | command:choices, More |
| `larger`, `smaller` | expand, collapse |

**Chips and endings**

| Glyph | Chip or ending |
|---|---|
| `filter` *new* | Keep rows where |
| `sort` *new* | Sort |
| `count` *new* | Count |
| `group` *new* | Group by |
| `columns` *new* | Columns |
| `limit` | First (≤: "no more than this", gs:204) |
| `report` | Add a column |
| `chain` | Match with |
| `table` | Read it as rows or a sheet; Sheet ending |
| `lines` | Read it as headings, lines or texts |
| `stack` | Read it as layers |
| `info` | Read it as facts |
| `running` | Show (line tone) |
| `note` | Note |
| `document` | Page |
| `watch` *new* | Watch |
| `agenda` | Agenda |
| `star` | Word |
| `prompt` (line tone) | In the line |

**The nine new glyphs**, drawn in the house rules (gs:6-16: one 1.6 weight, mitre joins, solid facets, a hexagon instead of a circle):
- **trash**: a straight-sided can, an accent lid facet, two inner strokes.
- **pause**: two solid bars.
- **filter**: a funnel of straight strokes with an accent facet band.
- **sort**: two stems with facet heads, one up and one down, in undo's facet style (gs:73-76).
- **count**: `letters('#')` (gs:384-391).
- **group**: three lattice hexagons in a cluster, one accent.
- **watch**: two chevron lids with a diamond pupil facet in accent, so it is not confused with `find`'s hexagon lens.
- **trace**: small square, then diamond waypoint, then facet arrowhead: hop by hop.
- **columns**: a box with three vertical rules, the first column an accent facet.

**`tf.icon(key, tone=None)`** gains a tone, and its cache key becomes `(key, tone, glow)`; today it is `(key, glow)` (tf:198). Its docstring, which says "amber when its line is chosen" (tf:197), is corrected to the green the code actually draws (tf:207-208).

### 1.4 The line on its slab

- **Look.** The slab is a `QFrame` styled with `bt.line_sheet()` (bt:66-69): a royal-purple slab in Kasandra, and green `TEAL_TEXT` letters in Graphite.
- **Text.** It shows the line in the `bt.eye` form, which shortens long record numbers (bt:72-74). The exact line is in the tooltip.
- **Segments.** Each `| step` is a hit area:
  - hovering shows ×;
  - clicking a segment goes back to that point;
  - "Undo the cut" restores what a click cut off, for the rest of that panel session.
- **Left end.** A `prompt` mark puts the line in the writing line. This replaces Inspect in the line (cm:222-232).
- **Right end.** The row count and the budget diamonds, then **Show**.
- **Words.** The window never names the language. Chips speak plain verbs. Refusals are translated by `pipe_rows.plain()`; today the parser's guard reads "…are not part of Stacy language" (tp:16), and today's text reaches the screen through chm:122 and :135.

### 1.5 What changes something

Rule: `stacy_hand.why_asks(op)` (sh:141-147) decides whether the panel shows an **asks** page. Otherwise a change goes through `SlateFace.stage(…, asked=True)` (s2:1991-2030), which acts at once at Do and show (the default, sh:32) when the operation is `hers` (sh:150-158).

| Action | Operation | Today | New |
|---|---|---|---|
| Bold, Italic, Underline, Plain, Style | documents.edit | Done at once; page undo (cm:322-354) | Unchanged. The Undo glyph sits in the same strip. |
| Move to notes | ideas.capture + documents.edit | Undo leaves the idea behind (cm:357-378) | Unchanged, but the result now says "the idea stays in Ideas", with a link to it. |
| Rename / Copy to / Move to | files.rename / copy / move | Dialog, then done; no Undo (cm:479-503) | Dialog is the confirmation, then `stage` with a trail line. Undo only once `UNDOES` grows (owner decision D1). |
| Move to Trash | files.trash | Done at once | Done at once (in `HERS_SHOW`), plus a "Put it back" through files.restore (owner decision D1). |
| Discard this draft | copies.discard | Room dialog | **Asks**: "what it removes cannot be brought back" (sh:50-51). |
| Stop a job / Agenda work | jobs.cancel / agenda.cancel | **Done at once** (cm:974→910-921; cm:1045→1025-1030) | **Asks**: "what it stops or settles cannot be put back" (sh:52). |
| Pause / Resume | jobs.pause/resume, agenda.pause/resume | Done at once | Done at once; each is the other's Undo. |
| Ending: **Sheet** | files.write ×2 (CSV + receipt) | `save_rows` writes with no receipt and no trail (s2:2822-2829) | `stage`: hers. Two trail entries; one Undo button runs both guarded Trash lines (sh:201-215). |
| Ending: **Note** / **Page** | ideas.capture / documents.create | Not available | `stage`: hers; no exact Undo. The card already says so (s2:2073-2075). |
| Ending: **Watch** / **Agenda** | agenda.add | Done at once, no trail (s2:2831-2834, 2887-2889) | `stage`: hers; no exact Undo (taking it out is agenda.cancel, which asks). |
| Ending: **Word** | words.keep (execute) | Only by typing | `stage`: **waits for Approve**, because words.keep is not in `HERS_SHOW` (sh:39-40; owner decision D2). |
| Ending: **Keep in my menu** | Appends to the menu file | Always written `then console` (chm:336-350) | The name dialog is the confirmation; the *chosen* ending is stored. |
| Ending: **Run in the Terminal** | files.write + shell command | One click on a kept [shell] runs it (chm:299) | **Always asks** (sh:56); the command shows on the slab first. |
| Copy the line / Copy rows | Clipboard | — | Done at once. |

### 1.6 Keyboard (works; never printed)

- **Opening.** The Menu key and Shift+F10 still open the panel at the focus (cm:2196-2209, cm:2258-2259), with the first do-button focused.
- **Moving.** Up and Down move within a column or a chip row group; Left and Right move along rows and between the do row, the chips and the endings.
- **Acting.** Enter and Space activate. Backspace removes the last step. Delete on a focused slab segment removes that step.
- **Leaving.** Escape leaves a picker or page first, and then the panel.
- **The rest.** Type-to-select (pq:528-541) and F1 descriptors (pq:543-562) are inherited. A name field inside the panel (Add a column, Word) keeps its keys, because `DeskMenu.eventFilter` already exempts `QLineEdit` (pq:563, 578).

---

## 2. Each thing the right-click serves: first level and one level down

The "Do row" is the first level. "Body" is what fills the panel. "More" is one level down. Words marked ‡ are shortened; their full old words remain in the tooltip, and `FOLDED` maps the old words to the key.

| Target | Today's top level (reader) | New do row | Body | More |
|---|---|---|---|---|
| File in Files (.csv) | 25 (24–30), 6 sections | 7 | pipe | 14–15 |
| Folder (copies) | 8 (11–13) | 6 | pipe (listing) | 3 (+5) |
| Two files | 6 | 5 | "Match these two" when the names allow | 2 |
| Files empty place | 8 | 5 | Start from | 10 |
| Finder file in Files | 10 | 6 | pipe | 0–2 |
| Passage | 18 | 2 strips + 7 | — | 6 |
| Page (caret) | 10 | 1 strip + 5 | — | 0 |
| Field sheet (work face) | 13 | 7 | pipe | 3 |
| Field empty desk (work face) | 8 | 7 | Start from (8 + words) | 1 |
| Today, workspace | 10 | 4 | Start from | 7 |
| Log event / Activity event | 3–4 / 4–5 | 3–5 | — | 0 |
| Network entry | 4 | 4 | Start from (1 chip) | 0 |
| Job | 7 | 4–5 | pipe (its output) | 0 |
| Agenda work | 4–6 | 3–5 | pipe (its program) | 0 |
| Cabinet project | 12+N+M | 6 | pipe | 8 (checks › and workspaces › are drills) |
| Settings / Machine | 5 / 6 | 5 / 6 | — / pipe | 0 |

**B1. A file in Files** (`find_files` cm:1483-1499; `file_entries` cm:596-664)
- **Head:** `table` (csv, tsv, xlsx, ods); `page` (text, PDF); `picture` (drawings) · "notes.csv" · "table".
- **Do:** Open `table` · Its app‡ `window` · Rename… `cell` · Copy path `copy` · Trash `trash` · Ask `asked` · More.
- **Body:** one read of `@files:<rel>`. The line starts at the file's reading (`LENS` cm:68-69, e.g. `| rows`).
  - Clicking the reading's segment shows the **Read it as** chips with counts, all worked from the same read: sheet ‹name› (up to 4), rows, headings, lines, layers, texts, facts. This replaces Extract › (cm:633) and its 16 hover reads (cm:541-553).
  - Only `|` and the guard characters (tp:16) make a name unreadable. The space guard (cm:216-217, 619-634) is lifted, because the parser accepts a source with spaces (run: `@files:Rev C notes.md | headings` parses).
- **More:**
  - *open and show*: Show in its folder (only after a search; otherwise hidden instead of "unavailable", cm:607-608).
  - *change it*: Copy to… `folder`, Move to… `folder`, Versions… `delta`, Export… `export`, Compare with… `again`, Compare with a kept version › `delta`. The versions are read **when this opens**; today every right-click on a file dispatches files.versions (cm:627).
  - *capabilities*: Open in ‹adapter› `rooms` (0–2), Find tools in the Tool Atlas `book`, Explore capabilities… `rooms`, Stage in Delivery `export`, Explain this file `info`, Investigate… `find`, Add to the Agenda… `agenda`.
  - *working copy*: Ask Stacy to work on this… `asked`, Review changes… `again`, Show the original `source`, Discard this draft… `trash` (asks).
  - *edit and copy*: Copy the address `copy`.

**B2. A folder or smart folder.**
- **Do:** Open `folder` · Rename… · Copy path · Export… · Trash · More.
- **Body:** `files.list {"path":"<rel>"} | pick entries`, the folder as rows (`files_service.py:445-452`). A smart folder has no body.
- **More:** Copy to…, Move to…, Copy the address. For a folder copy: Look inside, confined… `find`, Run a command here, confined… `prompt` (its own dialog), Review changes…, Show the original, Return as a pill… `export`, Discard this draft… (asks).

**B3. Several files.**
- **Do:** Compare these two / Compare revisions `again` (two files only) · Copy paths · Stage selected files in Delivery `export` · Trash · More (Copy to…, Move to…).
- **Body, new:** when the two are tables with one-word names (`JOIN` tp:10) and share a column, the body offers "Match these two on ‹F› · N rows". That is `@files:a.csv | rows | join @files:b.csv rows on F`.

**B4. The empty place in Files.**
- **Do:** New folder… `folder` (files.mkdir: hers, with Undo) · Import… `receive` · View as `sliders` (page: Thumbnails / List) · Refresh `recalc` · More.
- **Body:** **Start from** chips:
  - this folder as rows;
  - up to 6 recent tables or texts (`files.find`, kinds from chm:471);
  - **Your lines** `star` (kept words plus menu-file chains).
- **More:** New smart folder… `find`, Work on a copy of a file… `receive`, Show all files / Hide machine files `full`, and *elsewhere*: Inquiries… `asked`, Algorithm & Theory Atlas… `book`, Tool Atlas… `book`, Writing line (page: Assignment `cell`, Shell `prompt`, Search `find`, Log `lines`), Start from a file (page: all up to 30, with a filter field), Edit the Graphite menu… `cell`.

**B5. A Finder entry.**
- **Do:** Open · Open in viewer `page` · Show in Files `source` · Copy path · Ask `asked` · More (adapters).
- *Change it in Files* is folded into Show in Files, because both call `page.show_in_files` (cm:724, 729).
- **Body:** the file's pipe, as in B1.
- Outside Files there is no body and the noun says "read only". The greyed row "Nothing changes here · Files keeps its own changes" (cm:736) is dropped.

**B6. The Finder's empty place.**
- **Do:** View as · Show hidden files `full` · Show the preview `split` (no "Space" caption, cm:750) · Copy path · Refresh · More (elsewhere, as B4).

**B7. The Library.**
- A file: Open `page` · Keep a copy in Files `receive` · Ask `asked` · Copy the name.
- The empty place: Receive files… `receive` · Refresh · More (elsewhere).

**B8. A passage** (`document_entries` cm:381-427)
- **Strip 1** (glyph only, the `BARE` rule tf:45-46): `bold` `italic` `underline` `plain` · `h1` `h2` `h3` `body` `code` · `undo` `redo`.
- **Do:** Cut `cut` · Copy `copy` · Paste `paste` · Move to notes `note` · Ask `asked` · Search for these words `find` · More.
- **More:** Delete `close`, Select all `select`, New document `document`, Export… `export`, "Bold, as a line" `prompt`, and "Its paragraphs as a line" `chain`.
  - "Bold, as a line" is the raw `/documents.edit` JSON that Inspect in the line gives today (cm:403-406), kept so nothing is lost.
  - "Its paragraphs as a line" opens the pipe on `@document:<id> | pick document.blocks` (addresses.py:25; the same read as field_source.py:216).
- No keys are printed; today 9 are printed here plus 5 in the submenu (cm:388-423).

**B9. A page (caret only).**
- **Strip:** styles · undo · redo.
- **Do:** Paste · Select all · New document · Export… .
- Cut, Copy and Delete cannot act on a caret, so they are hidden; the passage keeps them.

**B10. A sheet on the Field** (`field_entries` cm:1392-1431)
- **Head:** `KIND[obj.kind]` (sheet → `table`) · title · "sheet · current".
- **Do:** Open `table` · What if `delta` · Doubt it `found` · Trace it `trace` · What can be done `steps` · Ask `asked` · More.
- **Pages:**
  - **What if**: numbers, then values (10 % more, 10 % less, Twice, Half, Another value…), as cm:1233-1264.
  - **Doubt it**: "All of it, in Talk" plus up to 16 rows (cm:1284-1301).
  - **Trace it**: "The whole trace, in Talk", then ← rows (`previous`) and → rows (`next`). These absorb *What feeds it* and *What it feeds* (cm:1400-1402), which list the same neighbours and make the same `select(ident)` call.
  - **What can be done**: steps; a step that writes says "asks first" (cm:1267-1281).
- **Body:** the sheet's **rows** line, plus "Its own line" as a chip (`obj.stac`, for example the state line at field_source.py:180) and **Your words** chips. A word that starts `this |` continues the panel's line with its tail, so `this` means *the sheet's rows* here (§6 on `this`).
- **More:** The brief of the desk `lines`, Copy its name `copy`.
- **Programs face:** do = Open, Doubt, Trace, What can be done, Ask, More.
- **Network face:** do = Show in Log `source`, Doubt, Trace, What can be done, More; body = `network.observe | pick connections | where process=X` (field_source.py:395).

**B11. The Field's empty desk** (cm:1352-1391)
- **Do (work face):** Look again `recalc` · Check the desk `found` · The brief `lines` · Show the programs `rooms` · Show the network `port` · Back `previous` · More.
  - Today 6 of these 8 rows print a key; none do now.
- **Body:** **Start from** chips: the face's 8 lines (cm:1371-1378) plus kept words. Each chip starts the pipe from that line; the slab's `prompt` mark still sends it to the strip, as today.
- **More:** Your words (page: Run it / In the line / Forget it (asks: `*.forget`, sh:50-51) / Keep a new word…).

**B12. Today, the workspace's empty place, and the pages that had no finder**
- **Do:** New Idea… `note` · New Project… `folder` · Import (Ingress)… `receive` · More.
- **Body:** Start from: recent tables and **Your lines**. A menu-file chain highlights its stored ending.
- **More:** Inquiries… · Algorithm & Theory Atlas… · Tool Atlas… · Writing line (page) · Start from a file (page) · Edit the Graphite menu… .
- **New finders**, so these pages stop reading "Technical PDF · an empty place":
  - viewer pages: `cc.viewer_entries` (cc:170-186) become their do row, plus the file's pipe (phase 1);
  - the PDF page: `pdf_qt.PdfDocumentTab.source`, pdf_qt.py:59, 189 (phase 3);
  - the Office grid: `office_qt.OfficePanel.ident`, office_qt.py:84 (phase 3).

**B13. Log and Activity**
- **An event:** Ask `asked` · Show in Log `source` (hidden *inside* the Log, cm:1126) · Its job `running` (page) · Copy `copy`. In Activity, Open (kind glyph) comes first.
- **A connection or packet:** Ask · Follow this conversation `reach` · Show the process `window` · Copy address `copy`. Body: one Start-from chip, "Every connection of ‹process›" (field_source.py:395).

**B14. Jobs and Agenda work**
- **A job:** Show in Jobs `source` (not in the Jobs list) · Pause `pause` *or* Resume `running`, whichever applies · Stop `stop` (asks) · Copy the job id.
  - Body: `@evidence:<id>` when output is kept, else `@job:<id>` (cm:962-964). Show replaces Inspect output; the slab's mark replaces Inspect in the line.
- **Agenda work:** Open Agenda `agenda` · Pause or Resume · Stop (asks) · Its job (page). Body: its program, when it is a line.

**B15. Cabinet, Activity selection, Machine, Settings**
- **Cabinet record (project):** Open `folder` · Write an idea here… `note` · Explore all capabilities `rooms` · Export (Egress)… `export` · Copy the identity · More.
  - More: Read saved details `info`, Checks (page, N) `found`, Open in (page, M) `rooms`, Refresh, View as (page), New Idea…, New Project…, Import (Ingress)… .
  - Body: `@<canonical>` when its kind is readable (cm:802-808).
- **Activity's extra "Explore"** (cm:1434-1438) becomes the cabinet's own row, so one Explore.
- **Machine:**
  - project: Open · Export… · New Idea… · New Project… · Refresh; body `@<canonical_id>`;
  - computer row: Show in the Finder `source` · Open Settings `sliders` · Copy what it says · Refresh.
- **Settings:** Open this setting `sliders` · Copy the key · Search settings… `find` · Expand all `larger` · Collapse all `smaller`.

**B16. Rows of Programs and of the head menus** (cc:44-62, 135-167)
- **Programs row:** Open capability `rooms` · About this `info` · For ‹current work› (page: that work's do row and pipe, in place) · Explore supported operations `rooms`.
- **Head-menu row:** About this `info` · Run this command `running` / Choose an operation (page, up to 2 levels) · For ‹work› (page).
- "About this" no longer writes "Shortcut:" (cc:125).
- **Right-click on the panel's own rows:** no meta-panel. F1 gives the description; "For ‹the same target›" is the panel itself, and "Continue this chain" is the pipe. This removes the "a second right-click closes the first menu" behaviour (cm:2158-2161).

**B17. Surfaces that keep a menu of their own** (these widgets own their menus, so `owns_menu` stops the walk, cm:1705-1709)
- **Console output:** Qt's Copy and Select All stay. `chain_menu.fill` (console_qt.py:445-451), which runs the line when the menu opens (chm:133), is replaced by one row, "Carry on from this answer" `chain`, which opens the panel on `last_program`.
- **Agenda `@` items** (agenda_qt.py:134-141): the same.
- **Unchanged in phase 1:** worksheet rows, program-room results, Master Stop, Lab, Adaptive, the meters, the companion, and text fields.

---

## 3. How chaining works

### 3.1 The rules

1. **Start.** `pipe_rows.read_line(target)` gives the thing's line:

   | Thing | Start line |
   |---|---|
   | File | `staC_for_file` (cm:210-213) |
   | Folder | `files.list … \| pick entries` |
   | Reviewed Office sheet | `@office:<id> \| pick origin.reviewed_rows` (the read field_doubt.py:211 already uses) |
   | Other Field sheets | `obj.stac` |
   | Cabinet record | `@<canonical>` |
   | Job | `@evidence:` / `@job:` |
   | Agenda work | its program |
   | Connection | `network.observe \| pick connections \| where process=…` |
   | Passage or page | `@document:<id> \| pick document.blocks` (offered, not opened) |

2. **Read once.** `Held.read()` dispatches `language.parse` (a read, sl:7) and then the plan's own read (`plan['call']`). For an address source it unwraps `['object']` as `_execute_plan` does (sl:120). A join side is read only when Match with… is chosen.
3. **Not rows yet** (a file object, a record): **Read it as** / **Look inside** chips. These are each lens, plus every list of records inside the object down to depth 3, with its length. This offers the `pick` path the builder never offered, for example `document.blocks · 12`.
4. **Rows: verb chips.**

   | Chip | What it offers | Line words |
   |---|---|---|
   | Keep rows where… | Column, then comparison, then value, each with a count. Up to 8 values: spread across a numeric column, the most common in a text column. Also "another column" for numbers (`over @Have`). | `where` / `over @F` (tp:232-234) |
   | Sort… | Smallest or largest first | `sort` |
   | Count N | — | `count` |
   | Group by… | 1–4 columns, then count / sum / avg / min / max of a number column | `group …` (the language allows 4, tp:88-90) |
   | Columns… | Up to 16 checkboxes | `select` |
   | First… | 5 / 10 / 20 / 200 | `take` |
   | Add a column… | Presets from pairs of number columns (`A − B`, `B − A`, `A + B`, `A × B`, `A ÷ B`), each showing its first values, and a free `NAME = …` checked live by `tp.arithmetic` (tp:112-136) | `add` |
   | Match with… | Tables in Files that share a column, join or missing on F, with counts | `join` / `missing` |
   | Pick rows | Click row numbers in the preview | `keep rows i,j` |

   "Columns…" and "Add a column…" no longer end the chain (chm:255-264).

5. **Rows: suggestions.** Up to 4 one-click chips with counts, all local:
   - a text column whose commonest value repeats: "unit is mA · 2";
   - "Group by unit · 3 groups";
   - a number column over its median: "value over 110 · 2";
   - two number columns compared: "Need over Have · 1".
6. **Hover to preview.** Hovering any option draws a dashed ghost step on the slab with its count and rows. Clicking adds it.
7. **Remove.**
   - × on a segment is refused while a later step uses what it made, e.g. "Short is made by this step and used after it" (run).
   - Clicking a segment goes back to that point.
   - Backspace removes the last step.
8. **Budget.** Diamonds show the steps used and left; the parser allows 1 source + 7 (tp:25, run: the 8th fails). At 0, the verb chips dim with the reason "This line has no step left".
9. **Big answers.** Counts are local, up to 2000 rows and 512 KiB (tp:219). When N > 200, the endings that need the Kernel's answer dim with the reason "The answer is N rows; a line gives at most 200…", and **First 200** is highlighted (tp:272; sl:112).
10. **Endings.**
    - Show runs through `cm.run_stac` (cm:235-249), which reports refusals honestly.
    - Every ending first checks `language.parse` and the sources fingerprint (`sources_now`, chain_workbench_qt.py:42-60). If a source changed: "It changed while you were choosing; read again" and the preview refreshes.
    - What changes something goes to §1.5.

### 3.2 Worked example: After Hours 07, sheet "07 Bench readings"

Right-click the sheet on the Field (work face). The Field selects it (cm:1680-1681).

**What opens** (read: the four reviewed rows from the scratch copy)
- **Head:** `table` · "07 Bench readings" · "sheet · current".
- **Do:** Open · What if · Doubt it · Trace it · What can be done · Ask · More.
- **Kernel calls so far: 2.** `language.parse`, then `ledger.address.read {"address":"office:owner:db5f669f863d4c71b89fa7ba348957da"}`.
- **Slab:** `@office:owner:db5f66… | pick origin.reviewed_rows` · **4 rows** · ◆◇◇◇◇◇◇ (1 of 7 used, run).
- **Preview** (≤5 columns; lists such as `original_cells` and `source_words` are folded):

  | parameter | value | unit | conditions | sheet_row |
  |---|---|---|---|---|
  | Rail voltage | 12 | V | During both observations | 2 |
  | Settled current | 280 | mA | After settling | 3 |
  | Startup current | 650 | mA | During startup pulse | 4 |
  | Startup duration | 110 | ms | Measured pulse | 5 |

- **Chips:** Keep rows where… · Sort… · Count 4 · Group by… · Columns… · First… · Add a column… · Match with… .
- **Suggestions (run):** "unit is mA · 2", "Group by unit · 3", "value over 110 · 2".

**Step 1: filter.** Click "unit is mA · 2". The long way is Keep rows where… → unit → *is*, which shows mA · 2, V · 1, ms · 1 (run).
- Line: `… | pick origin.reviewed_rows | where unit=mA`. **2 rows**: Settled current 280 mA; Startup current 650 mA. ◆◆◇◇◇◇◇.
- The "value" column reads as numbers even though it holds text: "over 12 · 3, over 110 · 2, over 280 · 1, over 650 · 0" (run). `chain_menu.numeric` (chm:63-65) would have called it text.
- 0 Kernel calls.

**Step 2: count.** Click Count 2.
- Line: `… | where unit=mA | count`. Preview: **count 2** (run). ◆◆◆◇◇◇◇, 4 left (run).
- With one row left, the verb chips dim with the reason "one row".
- 0 Kernel calls.

**Step 3: save as a sheet.** Click Sheet. Talk shows a card through `stage`:
- "For “07 Bench readings”: save these rows as a sheet."
- The `files.write` line on the slab, shown by its start (`brief`, §5).
- At Do and show it is done at once: "Done: “Slate/Chains/07 Bench readings 2026-11-14 1032.csv” is in Files."
- A receipt `.json` is written beside it, with the line, the source fingerprints, the seed and `LOCAL_NO_MODEL` (chain_workbench_qt.py:314-316).
- Two trail lines, and **one Undo** that trashes both, each guarded by its sha256 (sh:206-215).
- Kernel calls for the ending: parse, sources ×2, run, write ×2.

**Variants**
- "Group by unit · 3" gives V 1, mA 2, ms 1 (run).
- **What if** page: B2 · Rail voltage · 12 V, B3 · Settled current · 280 mA, B4 · Startup current · 650 mA, B5 · Startup duration · 110 ms. Then B3 › 10 % more · 308 mA, which asks Stacy "what if B3 were 308" (cm:1257-1258), a read.

**Today's way for comparison:** this sheet offers no chain builder at all. Its line, `office.get … | select source_state.state,origin.pdf.page_index` (field_source.py:180), reads the sheet's *state*, not its rows.

### 3.3 Worked example: a CSV in Files (`examples/clock_lab/inputs/parts.csv`, placed in Files)

**What opens**
- **Head:** `table` · "parts.csv" · "table".
- **Do:** Open · Its app · Rename… · Copy path · Trash · Ask · More.
- **Kernel calls: 2** (parse, then `files.get` through the address).
- **Slab:** `@files:parts.csv | rows` · **3 rows** · ◆◇◇◇◇◇◇. Preview: Controller 1 1 · Display 1 1 · Sensor 2 1 (run).
- **Suggestions:** "Need over Have · 1" (`where Need over @Have`, run; a two-column comparison the old menu never offered) and "Need over 1 · 1".
- **Match with…:** "No other table in Files shares a column". `power.csv` (Load…) and `memory.csv` (Allocation…) share none with Part, Need, Have (read).

**Step 1: Add a column…** Presets: Need − Have (0, 0, 1) · Have − Need (0, 0, −1) · Need + Have · Need × Have.
- Choose Need − Have. The name field is prefilled `Need_minus_Have`; type `Short` and click Add.
- Line: `@files:parts.csv | rows | add Short = Need - Have` · **3 rows**, Short 0, 0, 1 (run).

**Step 2: Keep rows where…** → Short (numbers) → "over 0 · 1", "over 1 · 0", "at least 1 · 1".
- Choose "over 0". Line: `… | add Short = Need - Have | where Short over 0` · **1 row**: Sensor 2 1 1 (run). ◆◆◆◇◇◇◇.
- × on the `add` segment is now refused, because Short is used after it; × on the `where` segment works (run).

**Step 3 (optional): Columns…** → Part, Short. Line: `… | select Part,Short` · {Part: Sensor, Short: 1} (run).

**Step 4: Sheet** (as in §3.2). Other endings:
- Watch: a stage card, with no exact Undo.
- Word: name `short`; it waits for Approve, because words.keep is not hers (sh:39-40).

**Today's way:** Chain from here » rows » "add a column…" opens a dialog and goes **straight to the console** (chm:260-264). You cannot go on to `where`, and each submenu opening runs the line again.

---

## 4. Nothing lost: every entry of today's menus and its new home

"Do", "Body/pipe", "Page" and "More" refer to §2. Keys stay the same, so `FOLDED` (cm:2267-2307) keeps working once its paths are flattened (§5).

| Today (reader B#, cm lines) | New home |
|---|---|
| **B1** Open / Open pill… (604), Rename… (609), Copy path (661), Move to Trash (663), Ask Stacy about this… (640) | Do |
| Open with this computer's app (606) | Do, "Its app‡" |
| Show in its folder (607) | More; shown only when it can act |
| Copy to… / Move to… (610-611), Versions… (613), Export… (615), Compare with… (626), Compare with a kept version › (628-632) | More (*change it*) |
| Inspect in the line (620) | Slab `prompt` mark |
| Run (622) | Show ending |
| Chain from here » (624) | The body |
| Extract › (633) | "Read it as" chips |
| Adapters (577), Tool Atlas (580), Explore (585), Stage in Delivery (636), Explain (639), Investigate (641), Add to the Agenda (642), Copy the address (662) | More |
| Working copy: Ask Stacy to work on this…, Review…, Show the original, Discard… (644-648) | More (*working copy*); Discard asks |
| **B2** Open, Rename, Export, Copy path, Trash | Do |
| Copy to, Move to, Copy the address; folder copies (649-660) | More |
| **B3** Compare (687), Stage selected (681), Copy paths (692), Trash (693) | Do |
| Copy to / Move to (690-691) | More |
| **B4** New folder, Import, View as ›, Refresh | Do / pages |
| New smart folder, Work on a copy, Show all files | More |
| Root menu › (702) | Its rows into More (*elsewhere*); Your chains and Start a chain from into Start from |
| **B5** Open, Open in viewer, Show in Files, Copy path, Ask | Do |
| Change it in Files (729) | Show in Files (same call, cm:724) |
| Inspect, Run, Extract | Pipe |
| Adapters | More |
| "Nothing changes here…" (736) | **Dropped**: the noun says "read only" |
| **B6** View as, hidden files, preview, Refresh, Copy path | Do |
| Root | More |
| **B7** All four rows; Receive files, Refresh | Do |
| Root | More |
| **B8** Bold/Italic/Underline/Plain, Paragraph style › (5) | Strip 1 |
| Undo, Redo | Strip 1 |
| Cut, Copy, Paste, Move to notes, Ask, Search | Do |
| Delete, Select all, New document, Export… | More |
| Inspect in the line (raw JSON) | More, "Bold, as a line" |
| **B9** Page edits | Strip / Do. Cut, Copy and Delete on a caret are hidden (they cannot act; the passage has them) |
| **B10** Open | Do |
| What feeds it ›, What it feeds › (1400-1402) | The **Trace it** page (← and → rows) |
| Inspect in the line (1404) | Slab mark |
| Run its line (1406) | "Its own line" chip + Show |
| What if, Doubt it, Trace it, What can be done, Ask (1410-1428) | Do / pages |
| Your words › (1422) | Body chips |
| The brief of the desk (1425), Copy its name (1430) | More |
| **B11** Look again, Check, Show programs/network, Back, The brief | Do |
| This face as lines › | Start from chips |
| Your words › (with Run it / In the line / Forget it / Keep a new word) | More › page |
| **B12** Your chains › | Start from, Your lines |
| Start a chain from › | Start from (6 chips) + More › "Start from a file" |
| Writing line ›, Edit the Graphite menu…, Inquiries…, both Atlases | More |
| New Idea…, New Project…, Import (Ingress)… | Do |
| **B12 viewer rows** (cc:170-186): Show enclosing folder, Copy full path, Ask | Do on viewer pages |
| Build a chain from this file, Read and transform » | Pipe |
| **B13** Ask, Show in Log, Its job ›, Copy, Open (Activity) | Do / page |
| Show in Log inside the Log | **Dropped** (it is where you are) |
| Network rows (1110-1116) | Do |
| **B14** Show in Jobs, Pause, Resume, Stop, Copy the job id | Do (the inapplicable Pause or Resume is hidden) |
| Inspect output (965) | Body + Show |
| Inspect in the line (976) | Slab mark |
| Agenda: Open Agenda, Pause, Resume, Stop, Its job › | Do / page |
| Agenda: Inspect in the line (1055) | Body |
| **B15** Cabinet: Open, Write an idea here…, Explore all capabilities, Export…, Copy identity | Do |
| Cabinet: Read saved details, checks, workspaces, Refresh, View as, New Idea, New Project, Import | More / pages |
| Cabinet: Inspect, Run | Pipe |
| Activity "Explore" (1438) | One Explore |
| Machine and Settings rows | Do |
| **B16** Inspect this capability/command | "About this" |
| Open capability / Run this command, Explore supported operations | Do |
| Choose an operation ›, For ‹work› › | Pages |
| Continue this chain » | The body |
| Meta-menu on the right-click's own rows (cc:53-57) | **Dropped**: F1 says the same, the rest is the panel itself |
| **B17** Console output's `fill` (console_qt.py:445-451), Agenda `@` rows (agenda_qt.py:134-141) | "Carry on from this answer", which opens the panel |
| **Chain builder (chm)**: header line | The slab |
| Build on the desk… (132) | Pin (a panel that stays) + the tray, still reachable from More of the pipe |
| Lenses (153-166) | Read it as |
| where / sort / group by / select / add a column / join with / take / count (169-196) | Chips and pickers |
| then › console / sheet / watch / Agenda / shell / keep / copy (141-147) | Endings (shell and keep under ⋯) |
| Tear-offs (104…) | Pin |
| **Noise, dropped:** key captions (§5 test), "unavailable" captions (cm:1883), revision in the noun (cm:306, 309), "Through Kernel.dispatch: …" tooltip lines (cm:123; still in `Entry.as_dict` for readers), the script caption "what you can do right here" (cm:54, 1943), Command inspector "Shortcut:" (cc:125), "Ctrl+Enter keeps this word" (s2:1230) | — |

---

## 5. Build plan

### 5.1 What is reused

- `Target`, `Entry`, `PROVIDERS`, `FINDERS`, `target_at`, `Router`, `install`, `perform`, `Refused`, and every revision check (`edit_document` cm:322-354, `still_file` 454-460, `job_now` 901-907, `queued_now` 1015-1022). They stay where they are.
- `entries_for` (cm:1449-1461) still collects the rows; the panel only *places* them.
- `DeskMenu` (popup, keyboard, F1, type-to-select) and `metrics`.
- `tf.icon` and the `GLYPHS`/`KIND` set.
- `bt.line_sheet` and `bt.eye`.
- `typed_pipeline.parse` / `split` / `apply` / `arithmetic`.
- `chain_workbench_qt.sources_now`.
- `SlateFace.stage` / `run_staged` / `undo_staged`.
- `stacy_hand.why_asks`, `hers`, `takes_back`, `guard`, `record`.
- From chain_menu: `parse_menu`, `keep`, `shell_lines`, `to_shell`, `copy`.

### 5.2 Phase 1: the panel (no seed input is edited)

| File | Change |
|---|---|
| `workbench/glyph_set.py` | Add `trash, pause, filter, sort, count, group, watch, trace, columns` to `GLYPHS` (gs:394-410). |
| `workbench/tool_faces.py` | `icon(key, tone=None)`; cache key `(key, tone, glow)`; new `paint_glyph(p, rect, key, state='normal', tone=None)` (halo as tf:213-216); docstring fix (tf:197). |
| **new** `workbench/pipe_rows.py` (no Qt) | Listed below this table. |
| **new** `workbench/pipe_panel.py` | Listed below this table. |
| `workbench/context_menu.py` | Listed below this table. |
| `workbench/chain_icons.py` | `'copy the stac'` → `'copy the line'` (chain_icons.py:102), for the QMenus that remain. |

`workbench/pipe_rows.py` holds:
- `read_line(target)`;
- `Held.read(dispatch, line)`, `.rows(line)`, `.count(line)`, `.readings()`;
- `steps_left(line)`, `columns(rows)` (scalar columns; numeric = every non-empty value reads as a number, the same coercion as tp:182-184);
- `suggestions(held, line, most=4)`;
- `where_offers`, `sort_offers`, `group_offers`, `column_offers`, `first_offers`, `add_presets(numbers)`, `match_candidates(dispatch, line, fields)`;
- `removable(line, k)` and `without(line, k)`;
- `ending_ready(count)`;
- `plain(message)`;
- `Offer = (key, words, glyph, line, count, enabled, reason)`.

`workbench/pipe_panel.py` holds:
- `PipePanel(DeskMenu)` with `Head`, `DoButton`, `Strip`, `Chip`, `Slab` (QFrame + `line_sheet()`), `Preview`, `Endings`, and the pages `Picker`, `Drill`, `More`, `Asks`;
- the readers' API kept from ContextMenu: `entries`, `keys()`, `row(key)`, `words()`, plus `first_keys()`, `pages()`, `texts()`.

`workbench/context_menu.py` changes:
- `Entry(…, glyph=None, tone=None)`, with `GLYPH_OF`, `HEAD_GLYPH` and `FIRST[target kind]` (the ordered do keys of §2).
- `KEY_CAPTION` and `KEY_TEXT` guards; `Entry.__init__` drops a key-shaped caption.
- `build()` returns `PipePanel`. `ContextMenu`, `ContextRow`, `_extra_paths`, `EXTRA` and `paint_icon` are removed.
- All key captions removed (cm:388-423, 750, 828-829, 1257-1261, 1279-1280, 1290, 1310, 1354-1361, 1379, 1394-1425).
- `Entry.tooltip()` without the dispatch line (cm:123); nouns without revision (cm:306, 309).
- Stop marked `asks`.
- Field fed/feeds become the Trace page.
- Document Inspect moves to More.
- New finder `find_viewer` using `cc.active_object`'s `surface='viewer'` (cc:25-32).
- `FOLDED` paths flattened (`root/…` → plain keys).

### 5.3 Phase 2: endings under the hand, and the stragglers

These files are **seed inputs** (stacy_foundation.py:111, 114, 53, 159; lines stop running until the seed is rebuilt). Make the edits together and run `build_seed` once (stacy_foundation.py:531).
- `s2.SlateFace.stage(…, brief=False)`: show a long line by its start, as `say_plan` already does (s2:2400). `save_rows`, `watch` and `keep_in_agenda` go through `stage` (s2:2822-2834, 2887-2889). Drop s2:1230.
- `console_qt.output_menu` → "Carry on from this answer" (console_qt.py:445-451).
- `command_context.describe` without "Shortcut:" (cc:125); "For ›" and Choose an operation as panel pages.
- `chain_menu.open_here` (chm:502-509) and Commands › Chain Menu open the panel; `keep()` stores the chosen ending (chm:347).

Not seed inputs:
- `field_page.expand_this` (field_page.py:385-399): `this` = the sheet's rows line.
- `stacy_hand`: decisions D1 and D2 (§6).

### 5.4 Phase 3: language and coverage

- A `grid` lens: Office cells → rows keyed by row 1. This touches `tp` LENSES and `apply` (tp:12, 212-273), changes the language, and is a seed input.
- Number-reading of reviewed values, or numeric sort for number-like text (tp:196-209).
- Finders for the PDF page and the Office grid.
- Reads off the window's thread for large sources.

### 5.5 Tests (exact assertions)

**New `tests_integrated/test_pipe_rows.py`.** No Qt; runs anywhere; uses the shipped `examples/clock_lab/inputs/parts.csv` and a synthetic reviewed-sheet value shaped as `datasheet_work.create_sheet` writes it (datasheet_work.py:145-163).

1. **Steps.**
   - `steps_left('@files:parts.csv | rows') == 6`;
   - after six more steps, `== 0`;
   - every `Offer` from `offers()` then has `enabled is False` and `reason == 'This line has no step left'`.
2. **One read.** A dispatch spy:
   - `Held.read(spy, '@files:parts.csv | rows')`;
   - `[c[0] for c in spy.calls] == ['language.parse', 'ledger.address.read']`;
   - after 50 calls to `count()`/`rows()`, `len(spy.calls) == 2`;
   - `held.count(L + ' | add Short = Need - Have | where Short over 0') == 1`;
   - `held.rows(L + ' | add Short = Need - Have | where Short over 0') == [{'Part':'Sensor','Need':2,'Have':1,'Short':1}]`;
   - `held.count('@files:parts.csv | rows | where Need over @Have') == 1`.
3. **Numbers in text.** With `value` = `'12','280','650','110'`: `columns(rows)['value'].numeric is True`; the comparisons offered for value are `{'over','under','at least','at most'}`.
4. **Suggestions.** On the synthetic reviewed sheet (units V, mA, mA, ms; values 12, 280, 650, 110): `[(o.words, o.count) for o in suggestions(held, base)] == [('unit is mA', 2), ('Group by unit', 3), ('value over 110', 2)]`.
5. **Removal.** `removable(L + ' | add Short = Need - Have | where Short over 0', 2) == (False, 'Short is made by this step and used after it')`, and removing step 3 gives `(True, '')`.
6. **Words.** For each bad line (a `>` inside quotes, eight transforms, `distinct x`, `where`): `re.search(r'(?i)language|stac', pipe_rows.plain(str(err))) is None`.
7. **200 rows.** On 450 synthetic rows:
   - `held.count(line) == 450`;
   - `ending_ready(450) == (False, 'The answer is 450 rows; a line gives at most 200. Add a step, or keep the first 200.')`;
   - `ending_ready(200)[0] is True`.
8. **No key anywhere in the source** (AST over `context_menu.py`, `command_context.py`, `pipe_panel.py`, `pipe_rows.py`): no `Entry(caption=…)` string matches `KEY_CAPTION`, and no string in `label`/`tip`/`reason` or anywhere else matches `KEY_TEXT`. The two patterns are:

   ```
   KEY_CAPTION = r'^(?:(?:Ctrl|Shift|Alt|Meta)\b.*|Esc|Enter|Return|Space|Backspace|Tab|F\d{1,2}|[A-Z0-9]|[←→⌫`])$'
   KEY_TEXT    = r'\b(?:Ctrl|Shift|Alt|Meta)\s*[+ ]\s*\w|\buntil Esc\b|\b(?:Esc|Enter|Space|Backspace|F\d{1,2})\s+(?:asks|shows|takes|does|keeps|runs|closes)\b|\([A-Z]\)|\b[A-Z]\s+(?:shows|tells|does)\b|\bShortcut:'
   ```

   Run today, this check finds **39 hits in cm and 1 in cc**; it must find **0**.
9. **Glyphs.** `set(cm.GLYPH_OF.values()) | set(cm.HEAD_GLYPH.values()) <= set(GLYPHS) | set(KIND)`, and `{'trash','pause','filter','sort','count','group','watch','trace','columns'} <= set(GLYPHS)`.

**Ported `tests_integrated/test_context_menu.py`** (offscreen window, as today):

10. **First level, exact.**
    - csv file: `panel.first_keys() == ['open','open:outside','rename','copy:path','trash','ask','more']`
    - folder: `['open','rename','copy:path','export','trash','more']`
    - two files: `['compare:two','copy:paths','delivery:stage','trash','more']`
    - Files empty place: `['new:folder','import','view','refresh','more']`
    - passage: `['notes','edit:cut','edit:copy','edit:paste','ask','search','more']`, plus strip keys `['mark:bold','mark:italic','mark:underline','mark:clear','style:Heading1','style:Heading2','style:Heading3','style:Normal','style:Code','edit:undo','edit:redo']`
    - Field sheet, work face: `['field:open','field:whatif','field:doubt','field:trace','field:do','field:ask','more']`
    - Field empty desk, work face: `['field:again','field:check','field:brief','field:face:programs','field:face:network','field:back','more']`
    - workspace empty place: `['new:idea','new:project','import','more']`
    - running job: `['job:show','job:pause','job:stop','copy:id']`
    - every target: `len(panel.first_keys()) <= 7`.
11. **Fits.** With the window resized to 1366×768 and to 1920×1200, for every target above and **every page** (`for page in panel.pages(): panel.show_page(page)`):
    - `panel.scroll.verticalScrollBar().maximum() == 0`;
    - `panel.bounds().contains(panel.geometry())`.
12. **No key on screen.** For every target and page, no string in `panel.texts()` matches `KEY_CAPTION` (as a whole caption) or `KEY_TEXT`. `panel.texts()` covers every word, caption, toolTip and accessibleDescription.
13. **Only Graphite's glyphs.** With `patch('workbench.programs_qt.paint_icon', side_effect=AssertionError)` and the same for `chain_icons.icon`, `panel.grab()` raises nothing for every target.
14. **parts.csv end to end.**
    - Right-click it, then `panel.slab.line == '@files:parts.csv | rows'` and `panel.slab.count_text == '3 rows'`.
    - `panel.chip('add').choose_preset('Need - Have', name='Short')`, then the line ends with `'| add Short = Need - Have'`.
    - Choose where Short over 0, then `count_text == '1 row'`.
    - `panel.ending('sheet').click()`, then a Talk card with `objectName 'StagedUndo'` exists, and `files_service.root(k)/'Slate/Chains'` holds exactly one new `.csv` and one `.json`.
    - Click Undo, then both are gone (`files.trash_list` holds both).
15. **Stop asks.**
    - With a `Recorder` on dispatch, `panel.row('job:stop').click()` gives `'jobs.cancel' not in recorded`.
    - `panel.page() == 'asks'` and the page's words contain `'what it stops or settles cannot be put back'`.
    - Clicking "Stop it" gives `recorded.count('jobs.cancel') == 1`.
16. **No reads while choosing.** After the panel opens on parts.csv, choosing a filter column and hovering 8 values adds **0** dispatches. Today the same choice runs 32 times (chm:212-216).
17. **Nothing lost.**
    - `test_nothing_is_lost_from_the_old_menus` (test_context_menu.py:594-629) is kept with the flattened `FOLDED`; its pin `'root/menu:edit'` (:621) becomes `'menu:edit'`.
    - `test_an_empty_place_…` (:671-677) reads keys from `panel.entries`, not the first level.
18. **The slab.** Under `GRAPHITE_APPEARANCE=kasandra`, `panel.slab.styleSheet() == bt.line_sheet()`.

**Campaign anchor** (needs the owner's backup, so it is not in the repo suite): on "07 Bench readings":
- `held.count(base + ' | where unit=mA') == 2`;
- `held.rows(base + ' | where unit=mA | count') == [{'count': 2}]`.

`tools/check_context_menu_ui.py` is ported to the panel. I have not run it here.

---

## 6. Risks: what is hard, honestly

1. **Two engines, one function.** Counts come from local `apply()` over the value read once, while endings come from `language.run`. The function is literally the same (sl:126), but the read path differs.
   - The panel skips `language.run`'s 200-row cap and its seed check during preview.
   - Mitigation: every ending re-parses with `expected_seed` and compares source fingerprints before and after (chain_workbench_qt.py:227-234).
   - Remaining risk: a source that changes *between* the hover and the click shows a stale count for that moment.
2. **200 against 2000.** The panel can show "450 rows" that no line can deliver (tp:272). That is honest, but the owner may expect Sheet to save all 450. The full-data roads (Files › Export, the Office import) are outside the line.
3. **Reviewed rows are not today's cells.** `origin.reviewed_rows` is what the page said. After the 280 → 300 mA change, row 3 still reads 280 (cases_anchor.py:115-118). Until the phase-3 `grid` lens exists, the body must say "as reviewed from page 1". When `field.doubt` finds cells that differ (field_doubt.py:213-219), it should also say "2 cells differ now". The `grid` lens changes the language and is a seed input.
4. **Numbers kept as text.** Reviewed values are strings (datasheet_work.py:149-159). `where … over` coerces them (tp:182-184), but `sort` orders them as text: run, "smallest first" gives 110 ms before 12 V. Fixing `_sort_rows` changes the meaning of existing kept lines, which is why it waits for phase 3.
5. **Seed inputs.** `shell2.py`, `chain_menu.py`, `command_context.py`, `console_qt.py`, `typebar_qt.py`, `typed_pipeline.py` and `stacy_language.py` are bound into the seed (stacy_foundation.py:53-167, 98). Any edit makes every line fail with "seed/source binding is not current" (sl:9-13) until `build_seed` runs. Phase 1 deliberately edits none of them.
6. **Owner decisions.**
   - **D1:** add `files.rename`, `files.move` and `files.restore` (the latter for Trash's "Put it back") to `UNDOES` (sh:43), with guards. `UNDOES` is a deliberate allow-list.
   - **D2:** whether `words.keep` becomes hers at Do and show. Today the Word ending waits for Approve, and its Undo would be `words.forget`, which `ALWAYS_ASKS` covers (sh:50-51).
   - **D3:** whether Pause, and the owner's own job controls generally, go through the trail. Under Ask first (sh:30), every ending that changes something waits for one extra Approve.
7. **A custom popup is more work than a list.** Two-dimensional arrow navigation, accessible names for chips, slab segments and the ghost step, and focus return all have to be built. `DeskMenu` only gives the one-column versions (pq:500-580). The window check script must be rewritten.
8. **Fit at large interface sizes.** Words scale without a ceiling (pq:29-30). At scale 1.4 the picker page is about 560 px tall; the fixed caps (10 shown plus a filter field, at most 3 columns in More) keep it from scrolling, but long values elide.
9. **Test and `FOLDED` churn.** Flattened paths, shortened labels‡, and the passage and Field rows moving into strips and pages. Every old word must still map, and `test_the_folded_list_is_well_formed` (:199-208) holds the "one home per word" rule.
10. **Still on the window's thread.** One read per step is far better than 32, but one large read (an xlsx near 512 KiB, or a join's 16 candidate tables) still blocks. The left side of the panel is painted first and the body fills after the first paint; real off-thread reads are phase 3.
11. **Discoverability against brevity.** Some rows move one click deeper into More, for example Compare with a kept version and Investigate. Suggestions and hover previews make up for it in the pipe, but not for the plain actions.
12. **Two stores of kept lines remain.** Words in the Kernel and chains in the menu file are both listed under Your lines. New keeps go to words, which cannot store an ending. The menu file stays for `[shell]`, `[stock]` and hand-edited chains, so nothing is lost, but the two are not yet one store.