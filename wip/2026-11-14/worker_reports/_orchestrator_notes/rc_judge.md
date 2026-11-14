# Right-click, simple and chainable: verdict on the three designs and one plan

## 0. Verdict

The plan merges the best of each design:

- **Shape at rest, from "learn".** Every menu has the same short shape: up to four usual actions, then **Then ›** (or **Start from ›** on an empty place), then **More ›**. I leave out three parts of "learn": the learned slot, kept chains shown at rest, and the line foot under every menu.
- **Engine, from "pipe".** The line is read through the Kernel once. Every count and preview after that uses the same `typed_pipeline.apply` that `language.run` runs. Reviewed sheets start from `pick origin.reviewed_rows`. I do not take pipe's two-dimensional chip panel.
- **Rules and panel layout, from "verbs".** At most two popups, with deeper levels replacing rows in place. At most 16 rows on any screen, with no scrollbar. A row that cannot act is left out at the first level, never greyed. A caption is only ever a status. The line panel is a vertical list with the line on its slab at the top.

Neither session adds a Kernel operation or changes the line language. Session 1 edits no seed input.

Scratch checks, all run with `python3 -I`, with no Qt and the repository unchanged:
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/judge/parse_check.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/judge/offers_check.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/judge/keys_scan.py`

## 1. What I checked in the code

Abbreviations: cm = `workbench/context_menu.py`, cc = `workbench/command_context.py`, chm = `workbench/chain_menu.py`, tf = `workbench/tool_faces.py`, gs = `workbench/glyph_set.py`, bt = `workbench/boss_theme.py`, sh = `workbench/stacy_hand.py`, s2 = `workbench/shell2.py`, sl = `workbench/stacy_language.py`, tp = `sdk/cli/arc1cli/typed_pipeline.py`, pq = `workbench/programs_qt.py`, fp = `workbench/field_page.py`, tcm = `tests_integrated/test_context_menu.py`.

| # | Claim | Evidence | Result |
|---|---|---|---|
| 1 | Which files are seed inputs (an edit to one stops every line until the seed is rebuilt). | `SEED_FILES` (`stacy_foundation.py:45-182`) includes shell2 (:159), command_context (:53), chain_menu (:111), console_qt (:114), menus2 (:139), session (:158), stacy_language (:164), typed_pipeline (:98), boss_theme (:52) and agenda_qt (:103). A stale seed refuses every line (sl:9-13). The rebuild is `build_seed` (:531); the last commit, 2ca282c, rebuilt the seed. | **cm, tf, gs, sh, pq, fp, stac_words and chain_icons are not seed inputs.** Session 1 can avoid a rebuild. |
| 2 | `language.run` is one Kernel read plus `typed_pipeline.apply`. | sl:116-127. `language.parse` returns the plan with its `call` (sl:107-111). | Reading once and counting locally is exactly the same computation. |
| 3 | Reviewed sheets already have rows. | The After Hours 07 copy (`office_documents`, id `owner:db5f669f…`) has `origin.reviewed_rows` with 4 rows. fs `field_doubt.py:211` reads them; they are written at `datasheet_work.py:163`. | Pipe and learn are right. Verbs' `@office:ID \| rows` needs a new read that is not required. |
| 4 | The worked lines parse. | `parse_check.py` on the real parser: base = 1 step and 4 rows; `where unit=mA` gives 2; `\| count` gives `[{'count': 2}]`; `group unit \| count` gives V 1, mA 2, ms 1. 8 transforms are refused (tp:25). `@files:parts list.csv \| rows` parses; a join on a name with a space is refused (tp:10). | Confirmed. |
| 5 | Numbers stored as text sort as text. | `sort value` gives 110, 12, 280, 650 (`offers_check.py`). `where value at least 110` coerces correctly and gives 3. | Filter values on numeric text is fine. Sort must not be offered on numeric text. |
| 6 | Stop does not ask. | `job_action` dispatches `jobs.cancel` straight after `job_now` (cm:910-921, 974), yet `*.cancel` always asks (sh:52). | Confirmed. |
| 7 | Opening the menu reads. | `versions_of` runs while a file's rows are being built (cm:627). Extract runs up to 16 `language.run` calls (cm:537-555). | Confirmed. |
| 8 | Printed keys. | An AST walk finds 21 `caption=` key sites in cm: 417-421, 423, 750, 829, 1290, 1310, 1354, 1356, 1361, 1379, 1395, 1404, 1406, 1412, 1415, 1418, 1425. Computed key captions sit at cm:388 and cm:394. Tooltip key words sit at cm:1259, 1261, 1280, 1414, 1417, 1420. Also "Shortcut:" (cc:125), "(F9)" (fp:397) and "Ctrl+Enter keeps this word" (s2:1230). | All must go. Only cc:125 and s2:1230 are in seed inputs. |
| 9 | The icons are painted, not set. | `ContextRow` paints `paint_icon` in TEXT or QUIET (cm:1905-1910). `MenuRow` is a `QAbstractButton` (pq:265), and `menus2.rebuild` turns any such button's icon into one flat colour (menus2.py:286-289). | Paint glyphs; never call `setIcon`. |
| 10 | How glyphs are drawn. | `tf.icon` caches by `(key, glow)` (tf:198), with colours by state at tf:207-208. ROYAL is `#7b4fd8` / `#b9a1f6` in Kasandra and equals TEAL_TEXT in Graphite (bt:40, 51). `line_sheet` is at bt:69-72. In Kasandra the Trash can is drawn red with `RED` (trash_can_qt.py:115). | A tone argument is needed, plus a "danger" tone for Trash. |
| 11 | Widgets that own their menu are still reachable. | Finders run before `owns_menu` (cm:1716-1720); the Router consumes the event (cm:2244-2248). `owns_menu` returns True for any `QTextEdit` before it reads `graphiteContext` (cm:1706 vs 1709). | A `find_console` finder can claim the console output without editing console_qt. Learn's `graphiteContext` mechanism is wrong in detail. |
| 12 | Changes the owner asks for already have a path. | `SlateFace.stage(…, asked=True)` gives a card, a trail entry and an Undo (s2:1991-2076). The Field uses it for the owner's own steps (fp:324, 517). `stage` prints the whole line; only `say_plan` has `brief` (s2:2398). | Save as a sheet waits for `brief`, which means an edit to shell2 (session 2). |
| 13 | Programs is now called Apps. | Commit 2ca282c; `setAccessibleName('Apps')` at pq:703. | None of the three designs reflects this. |

## 2. Scores (1 to 10)

| | verbs | pipe | learn |
|---|---|---|---|
| Simplicity at rest | 8 | 5 | **9** |
| Power reachable (nothing lost) | 8 | 8 | 8 |
| Chaining (build it, see it) | 8 | **10** | 8 |
| Honesty with the code | 6 | **9** | 7 |
| Keeping the owner's rules | 7 | 7 | **8** |
| Buildable in 1–2 sessions | 5 | 4 | **6** |
| **Total / 60** | 42 | 43 | **46** |

**Verbs**
- Strengths:
  - The rule set is clean: two popups, drill in place, 16 rows per screen, no grey rows at the top.
  - The panel layout is good: slab, preview, steps, then endings.
  - It found the menus2/QAbstractButton trap (pq:265, menus2.py:286-289).
- Faults:
  - It needs three new Kernel-side pieces: `language.offers` (sl is a seed input), `chains.save` (engineering_kernel plus the registry), and office rows through `addresses.read`, although `origin.reviewed_rows` already exists. It never mentions the seed.
  - Its tests call an `every_menu` helper that tcm does not have (tcm has `right_click` :78 and `menu_tree` :708).
  - It follows Words|Icons (tf:233), which can switch off the icons the owner just asked for.
  - Rename and Copy path become two clicks.
  - Some verbs are filed oddly: "Put it on the Agenda" sits under Ask, and "Into Delivery" under Copy.

**Pipe**
- Strengths:
  - The most accurate design: read once with the existing operations (sl:116-127), reviewed rows, a correct seed list, and the text-sort trap.
  - The best chain affordances: budget, Back a step, honest handling of the 200-row limit.
- Faults:
  - At rest a CSV right-click shows a head, 7 buttons, 8 chips, 2 suggestions, a slab, a 4-row preview and 6 endings: about 25 targets in a panel about 680 px wide. The owner's rule is "At rest the window shows names and pictures, and the machinery is one move away" (RECORD_OF_DIRECTIONS.md:211-213).
  - It needs the most new widget code: two-dimensional keyboard navigation, ghost steps, and slab segments as hit areas.

**Learn**
- Strengths:
  - The best shape at rest: one shape everywhere, four usual actions, Then, More, about 6 rows.
  - Honest hand classes: what has an Undo, what has none, and what always asks.
- Faults:
  - `language.peek` lives in a seed input (sl). `menu_use` lives in session.py, also a seed input.
  - `these` is a new lead word for the language.
  - The line foot at rest puts the machinery in view at rest, against the same rule.
  - A learned slot moves rows around.
  - The console claim is wrong in detail (row 11 above).

## 3. The plan

### 3.1 Rules every menu keeps

1. **One shape.**
   - **Heading:** the kind glyph, the name, and the noun. The noun loses "revision N" (cm:306, 309); the revision stays on `Target.revision` for changes.
   - **Up to 4 usual actions** for this kind, from the `REST` table (§3.3).
   - A hairline.
   - **Then ›**, when the thing has a line, or **Start from ›** on an empty place.
   - **More ›**.
   - At most 6 rows, about 198 px at 14 pt. Today a file's menu is about 727 px (estimated from pq:30-38).
   - The foot caption "what you can do right here" goes (cm:54, 1942-1944).
2. **Leave out, never grey, at the first level.**
   - Of Pause and Resume, only the one that applies is shown.
   - Show in its folder appears only after a search.
   - Cut, Copy and Delete do not appear when there is only a caret.
   - In deeper screens a row that cannot act now is dim, with its reason in the tooltip. The word "unavailable" (cm:1883) is never printed.
3. **Two popups at most.**
   - The first level is popup 1. Then, More and any first-level › open popup 2 beside it, as today (cm:2043-2048).
   - Anything deeper replaces popup 2's rows in place, under a **Back** row with the `previous` glyph.
   - The rebuild is deferred with `QTimer.singleShot(0)`, as cm:1895 already does, so that a row is never deleted inside its own click handler.
4. **At most 16 rows on a screen, and never a scrollbar.**
   - Longer lists split into pages through a "More… (n)" row that drills in place.
   - If More would exceed 16 rows, its largest group becomes one drill row.
   - The DeskMenu scroll area (pq:445-447) stays as a safety net; tests assert its range is 0.
5. **A caption is a status**: a count ("4 rows"), "asks", a process name or an address. It is never a key. The tooltip line "Through Kernel.dispatch: …" goes (cm:123); F1 still describes the row.
6. **Opening the menu reads nothing.** Versions are read only when "Compare with a kept version ›" opens (cm:627-632). Extract becomes the line panel's "Read it as", counted from that panel's single read.
7. **Mouse first; the keyboard keeps working; no key is printed.**
   - The Menu key and Shift+F10 still open the menu (cm:2258).
   - Arrows, type-to-select and F1 work as before (pq:528-580).
   - Right or Enter goes in; Left or Esc comes back one screen (cm:2099-2107).
   - In the line panel, Backspace goes back one step.
8. **Words.**
   - The window never names the language, and step words never begin with the line's keywords (where, pick, select, join, take, group).
   - "Ask … about this" keeps `named()`, so it reads Kasandra or Stacy by appearance.
   - The words say "Apps", not "Programs".

### 3.2 Icons

- **Painting.**
  - `ContextRow.paintEvent` (cm:1905-1919) and `Heading.paintEvent` (cm:1836-1839) paint `tool_faces.icon(entry.glyph, entry.tone).paint(p, rect, Qt.AlignCenter, mode)`. The mode is Normal, Active when the row is lit, or Disabled.
  - They never call `setIcon` (see check 9). Rows also set `paperIcon` as an extra guard.
  - This menu alone uses 20 px glyphs, the size they were drawn for (`SIDE`, tf:29). The Apps list keeps 16 (pq:30). The row height at 14 pt stays 24 (pq:53).
- **Tones.** `tf.icon(key, tone=None)`; the cache key becomes `(key, glow, tone)` (tf:198).
  - `None`: today's neon look (tf:207-208).
  - `'line'`: ink ROYAL_TEXT and fill ROYAL in Kasandra; the green TEAL_TEXT in Graphite (bt:40, 51). Used by Then, Start from, Show it, Put it in the writing line, Run its line, and the panel's step glyphs.
  - `'danger'`: RED in Kasandra only, for Move to Trash and Discard this draft, following the Trash can (trash_can_qt.py:115; bt:64-66). Graphite is unchanged.
- **Words or Icons.** The right-click always wears glyphs ("With right click icons too"; there has always been an icon column, cm:1910). This is owner question 3.
- **Eight new glyphs** in the house rules (gs:6-16: one 1.6 weight, sharp joins, solid facets, a hexagon instead of a circle), added to `GLYPHS` (gs:394-410):

| Glyph | Drawing |
|---|---|
| `trash` | A straight-sided can with an accent lid facet, after the Trash can's shape |
| `pause` | Two solid bars (`stop` stays one square, gs:176) |
| `filter` | A funnel of straight strokes with an accent band |
| `sort` | Two stems, one facet head up and one down, in undo's facet style (gs:73) |
| `count` | `letters('#')` (gs:384-391) |
| `group` | Three short rules gathered by a bracket into one head facet |
| `watch` | Straight lids around a diamond pupil, so it does not read as `find` |
| `trace` | Three nodes on an elbow wire ending in a facet, so it does not read as `field` (gs:52) |

- **`GLYPH_OF`** maps an Entry key or its prefix to a glyph. Every value must be in `GLYPHS` or `KIND`.
  - Open → the target's `KIND` glyph (gs:413-415): `table` for tables, `page` for text and PDF, `picture` for drawings, `folder` for folders.
  - `open:outside`, `process` → `window`
  - `open:viewer` → `page`
  - `show:*`, `job:show`, `copy:original`, `viewer:folder` → `source`
  - `rename`, `menu:edit` → `cell`
  - `copy:*`, `copy`, `edit:copy`, `field:copy`, `viewer:path`, `copy:to` → `copy`
  - `move:to`, `new:folder`, `new:project` → `folder`
  - `versions`, `compare:version`, `field:whatif` → `delta`
  - `compare:*`, `copy:review` → `again`
  - `export`, `doc:export`, `copy:pill` → `export`
  - `delivery:stage` → `stack`
  - `adapter:*`, `explore`, `cabinet:explore`, `cabinet:workspace:*`, `command:atlas`, `command:invoke` → `rooms`
  - `atlas`, `algorithms` → `book`
  - `explain`, `cabinet:record`, `command:inspect` → `info`
  - `ask`, `field:ask`, `copy:slate`, `viewer:ask`, `inquiries` → `asked`
  - `investigate`, `search`, `new:smart`, `copy:look` → `find`
  - `agenda` → `agenda`
  - `trash`, `copy:discard` → `trash` (danger tone)
  - `import`, `keep`, `work:copy` → `receive`
  - `view`, setting `open` → `sliders`
  - `view:all`, `hidden` → `full`
  - `preview` → `split`
  - `refresh`, `field:again` → `recalc`
  - `mark:*`, `style:*` → the letter glyphs
  - `notes`, `cabinet:write`, `new:idea`, `field:brief` → `note`
  - `edit:*` → `undo`, `redo`, `cut`, `paste`, `select`, `close`
  - `doc:new` → `document`
  - `job:output` → `lines`
  - `job:pause`, `queued:pause` → `pause`
  - `job:resume`, `queued:resume`, `job` → `running`
  - `job:stop`, `queued:stop` → `stop`
  - `follow` → `reach`
  - `field:doubt`, `field:check`, `cabinet:check:*` → `found`
  - `field:trace` → `trace`
  - `field:do` → `steps`
  - `field:words`, `chains` → `star`
  - `field:face:network` → `port`
  - `field:back` and `field:fed` → `previous`; `field:feeds` → `next`
  - `then`, `start` → `chain` (line tone)
  - `more`, `command:choices` → `more`
  - `expand`, `collapse` → `larger`, `smaller`
- **What leaves the right-click:**
  - `EXTRA`, `_extra_paths` and `paint_icon` (cm:1732-1806).
  - The `programs_qt` icon set (it stays in the Apps list).
  - `chain_icons`, with its fixed hex colours and its dead "copy the stac" lookup (chain_icons.py:7, 102), once the builder leaves the menus in session 2.

### 3.3 The first level for each kind of thing

`REST[kind]` is an ordered preference list. The first 4 keys that are present and enabled are shown. `a|b` means "whichever applies".

| Kind (finder) | Usual actions at rest [glyph] | Then › / Start from › starts at | More › groups |
|---|---|---|---|
| File in Files (`find_files` cm:1483) | Open [kind] · Ask … about this… [asked] · Rename… [cell] · Move to Trash [trash, danger] | `@files:REL \| lens` (`staC_for_file` cm:210-213). The space guard (cm:216, 619-634) is lifted; only Match needs one word (tp:10). | Open and show; Change it; Look into it; Send and keep; Edit and copy; This working copy |
| Folder | Open [folder] · Rename… · Copy path [copy] · Move to Trash | `files.list {"path":REL} \| pick entries` (files_service.py:452) | Change it; Send and keep; Edit and copy; This working copy |
| Smart folder | Open · Rename… · Copy path · Move to Trash | none | Change it; Send and keep; Edit and copy |
| Several files | Compare these two or Compare revisions [again] (two files only) · Move to… [folder] · Copy paths [copy] · Move to Trash | none (a line reads one source) | Change it (Copy to…); Send and keep (Delivery) |
| Files empty place | New folder… [folder] · Import… [receive] · View as › [sliders] · Refresh [recalc] | Start from ›: This folder as rows · Yours › · A file in Files › | Make and arrange; Open and show (Inquiries, both Atlases, Writing line ›, Edit the Graphite menu…) |
| Finder entry inside Files | Open · Show in Files [source] · Ask … about this file · Copy path | `@files:REL \| lens` | Open and show (Open in viewer, adapters) |
| Finder entry outside Files | Open · Open in viewer [page] · Ask … · Copy path | none; the noun reads "file · read only here" | Open and show (adapters) |
| Finder empty place | View as › · Show or Hide hidden files [full] · Show or Hide the preview [split] · Refresh | Start from › | Edit and copy; Open and show |
| Library file | Open [page] · Keep a copy in Files [receive] · Ask … about this file · Copy the name | none | none |
| Library empty place | Receive files… [receive] · Refresh | Start from › | Open and show |
| Passage | Bold or Not bold [bold] · Italic [italic] · Move to notes [note] · Ask … about this | `@document:<id> \| pick document.blocks \| select text` (addresses.py:25; field_source.py:216) | Change it (Underline, Plain, Paragraph style ›); Look into it (Search for these words); Make and arrange; Send and keep; Edit and copy (Undo, Redo, Cut, Copy, Paste, Delete, Select all); As a line |
| Page, caret only | Paragraph style › [body] · Paste · Select all · New document [document] | same | Edit and copy (Undo, Redo); Send and keep |
| Field sheet, work face | Open [KIND] · What can be done › [steps] · Doubt it › [found] · Ask … about this | Reviewed sheet: `@office:<id> \| pick origin.reviewed_rows`. Otherwise `obj.stac`. "Its own line" is the other start. | Look into it (Trace it ›, What feeds it ›, What it feeds ›, What if ›); As a line (Run its line, Your words ›); Edit and copy |
| Field sheet, network face | Show in Log [lines] · What can be done › · Doubt it › · Trace it › | `network.observe \| pick connections \| where process=X` (field_source.py:395) | As above |
| Field empty desk, work face | Look again [recalc] · Check the desk [found] · The brief [note] · Show the apps [rooms] | Start from ›: This face as lines (cm:1371-1378) · Yours › | Open and show (other face, Back); As a line (Your words ›) |
| Today, workspace, any empty place | New Idea… [note] · New Project… [folder] · Import (Ingress)… [receive] · Inquiries… [asked] | Start from › | Open and show (Algorithm & Theory Atlas…, Tool Atlas…, Writing line ›, Edit the Graphite menu…) |
| Log event (Activity adds Open and Show in Log) | Ask … · Its job › [running] · Copy [copy] | none in this plan | none |
| Network connection or packet | Ask … · Follow this conversation [reach] · Show the process [window] · Copy address | `network.observe \| pick connections \| where process=<p>` when the process is known | none |
| Job | Show its output [lines] · Pause or Resume · Stop… [stop] (caption "asks") · Show in Jobs [source], or Copy the job id in the Jobs list | `@evidence:<id>` or `@job:<id>` (cm:962-964) | Edit and copy |
| Agenda work | Pause or Resume · Stop… (asks) · Its job › · Open Agenda [agenda] | its stored program | none |
| Cabinet record | Open [folder] · Write an idea here… [note] · Open in <first workspace> [rooms] · Copy the identity | `@<canonical>` when it has an address (cm:802-808) | Open and show; Look into it (checks, one Explore); Make and arrange; Send and keep |
| Cabinet tree empty place | New Idea… · New Project… · Import (Ingress)… · View as › | none | Make and arrange (Refresh); Send and keep |
| Machine: project / Work root / computer row | Open · Export (Egress)… · New Idea… · Refresh / New Idea · New Project · Import · Refresh / Show in the Finder · Open Settings · Copy what it says · Refresh | `@<canonical_id>` for a project | Make and arrange |
| Setting / settings group | Open this setting · Search settings… · Copy the key · Expand all / Expand all · Collapse all · Search settings… | none | Make and arrange (Collapse all) |
| Apps row / head-menu row (cc:135-167) | Inspect (later "What it does") [info] · Open or Run, or Choose an operation › · For <work> › · Explore supported operations | "Continue this chain" (cc:153) becomes Then › | none |

### 3.4 Then ›: the line panel

**Engine: `workbench/line_steps.py`, new, no Qt.**
- `Held(dispatch).read(line)` makes two Kernel calls:
  1. `language.parse`, which checks the seed and the read permission and returns the plan's `call` (sl:107-111).
  2. That call itself. An address result is unwrapped from `['object']`, as `_execute_plan` does (sl:120).
- Every count and preview after that is `typed_pipeline.apply(value, transforms, 2000)`, the same function `language.run` applies (sl:126). Each step is parsed locally with `stacy_language.source` and `typed_pipeline.parse` and must keep the held call.
- The panel calls the Kernel through `context_menu.dispatch`, so the test `Recorder` sees every call (tcm:101).

**Opening.**
- Then › opens on a click or after the 240 ms rest (cm:55), as popup 2.
- The read happens after the panel is first painted (`singleShot(0)`), with "reading…" as the count caption until it is done.
- The whole line is written out before it is shown: words through `stac_words.expand` (sw:114-120) and `this` through `fp.expand_this` (fp:388-399).

**Layout of popup 2** (estimated about 425 px tall, at most about 480 px wide):

```
▌@files:bench.csv | rows                           4 rows · 6 steps left   ← bt.line_sheet() slab, bt.eye() text, exact line in its tip
 parameter         value  unit                                            ← preview: 3 rows, ≤4 columns, quiet mono, "and N more"
 Rail voltage      12     V
 Settled current   280    mA        and 2 more
[previous] Back a step · where unit=mA          (only once a step is added; Backspace does the same)
[table]   Read it as                    ›  rows    (only when a thing has more than one reading; replaces Extract)
[filter]  Keep rows where               ›
[sort]    Sort by                       ›          (only on columns that sort honestly; see Limits)
[count]   Count                            4
[group]   Count by                      ›
[limit]   First                         ›          (only when there are more than 5 rows)
─── then ───
[running] Show it                                  (line tone)
[prompt]  Put it in the writing line               (line tone)
[copy]    Copy the line
[copy]    Copy the rows                            (CSV on the clipboard)
```

**Offers. Every value carries its count; a candidate that keeps all rows or none is dropped.**
- **Number columns** (every non-empty value reads as a number, numeric text included): "at least V" and "at most V" over up to 6 values spread across the column.
- **Text columns**: "is V" for up to 6 of the most common values, and "is not V" for up to 3. Ties go to the value seen first.
- **"Another value…"** puts the line so far plus ` | where F ` into the writing line, through `inspect_in_line` (cm:222-232).
- The value screen has at most 11 rows, about 300 px.

**Endings in session 1** change nothing:
- **Show it** goes through `run_stac` (cm:235-249), which reports a refusal honestly.
- **Put it in the writing line** uses `inspect_in_line`.
- **Copy the line** copies the line text.
- **Copy the rows** runs `language.run` with `expected_seed` and copies the CSV (`files_service.as_csv`).

**Endings in session 2**, through the hand (§3.5): Save as a sheet, Watch it, Add to the Agenda, Keep as a word…, To a command… (asks), and Lay it out below (the tray, chain_workbench_qt.py:165-201).

**Limits, said in plain words.**
- **Steps left** shows from 1 source plus 7 steps (tp:25). At 0, the steps are dim with "This line has no step left".
- **Over 200 rows** (tp:272; sl:112): Show it and Copy the rows are dim with the caption "over 200 · keep fewer first", and First › offers 200. This is the only deliberate grey row, because the count explains it.
- **Over 2000 rows or 512 KiB at the source** (tp:219): the panel says it is too big to read here and offers only Put it in the writing line.
- **Sort** is left out on numeric text, because it would sort as text (check 5).
- **Refusals** pass through `line_steps.plain()`, so the parser's "…not part of Stacy language" (tp:16) is never shown.

**Start from ›** (empty places, and the start screen):
- **Yours ›** lists your words (`words.list`) and the menu file's kept chains (`chm.parse_menu` :363-391). Choosing one loads its written-out line into the panel, so you can carry on from it. A kept chain's stored ending is shown as a caption. A line that does not parse is dim with its plain reason.
- **A file in Files ›** shows the existing 30 entries (cm:1177-1183), 14 per screen.

**Worked example: "07 Bench readings".** Verified with the real parser over the scratch copy.
1. Right-click the sheet, choose Then. Slab: `@office:owner:db5f66… | pick origin.reviewed_rows`, "4 rows · 6 steps left". So far: 2 Kernel calls.
2. Keep rows where › unit shows: is mA 2 · is V 1 · is ms 1 · is not mA 2 · is not V 3 · is not ms 3.
3. Keep rows where › value shows: at least 110 3 · at least 280 2 · at least 650 1 · at most 12 1 · at most 110 2 · at most 280 3.
4. Choose "is mA": 2 rows, 5 steps left.
5. Choose Count: the preview shows `count 2`. Count by › unit would give V 1 · mA 2 · ms 1.
6. Still 2 Kernel calls in total. Show it adds one `language.run`.
- Today this sheet has no chain at all: its own line reads its state, not its rows (field_source.py:180).

### 3.5 Changes and the hand

| Rows | Path |
|---|---|
| Reads and navigation (Open, Show…, Ask…, Copy…, every step, Show it) | Direct, unchanged |
| An operation covered by `why_asks` (sh:141-147): Stop on a job (`jobs.cancel`), Stop on Agenda work (`agenda.cancel`); in session 2, To a command… (`shell.*`, sh:56) | The row's caption is "asks". Choosing it opens an **ask screen** in popup 2: the `why_asks` sentence ("What it stops or settles cannot be put back."), then **Stop it** [stop] and **Leave it** [previous]. Nothing is dispatched before Stop it. Stop it then runs today's `job_action` or `queued_action`, so the `job_now` / `queued_now` re-check (cm:901-907, 1015-1022) happens at that moment. |
| Discard this draft… | Already asks (files_qt.py:333-335). It gets the "asks" caption. |
| Rename, Copy to, Move to | Unchanged. The dialog is the confirmation (cm:479-503). There is no Undo until owner question 1 is answered (`UNDOES` is an allow-list, sh:43). |
| Move to Trash | Unchanged. It is hers at Do and show (sh:39), and the Trash gives it back (cm:487-491). |
| Page edits (Bold…) | Unchanged. The page's own Undo applies (cm:322-354). |
| Session 2 endings | `SlateFace.stage(title, Step(words, 'write', line, scope='execute'), asked=True, word='chosen from the right-click')` (s2:1991-2030):<br>• **Save as a sheet** is `files.write` of the CSV: hers at Do and show, with the exact Undo (`takes_back` and `guard`, sh:201-212).<br>• **Watch it** and **Add to the Agenda** are `agenda.add`: hers, with no exact Undo, which the card says (s2:2073-2075).<br>• **Keep as a word…** is `words.keep`: not hers, so it waits for Approve with `why_waits` (sh:161-164).<br>• **To a command…** asks first, then stages `files.write` of the answer and puts the command in the Terminal line **for you to run**. Today one click on a kept command runs it (chm:299, 311-323). |

### 3.6 Where every current entry goes

**Key to the codes:**
- **rest**: the first level
- **more·X**: More ›, group X
- **then**: the line panel. **then·read** is Read it as; **then·end:\*** is an ending.
- **start**: Start from ›
- **ask**: the ask screen
- **merged**: folded into another row that makes the same call
- **out\***: left out entirely; needs the owner's yes (owner question 2)

| Today | New home |
|---|---|
| **File** (cm:604-663): open, ask, rename, trash | rest |
| open:outside, show:folder (only after a search), adapter:\*, atlas, explore | more·Open and show |
| copy:to, move:to, versions | more·Change it |
| explain, compare:with, compare:version (reads when opened), investigate | more·Look into it |
| export, delivery:stage, agenda | more·Send and keep |
| copy:path, copy:address | more·Edit and copy |
| copy:slate, copy:review, copy:original, copy:discard (asks) | more·This working copy |
| inspect / run / chain / extract | then·end:line / then·end:show / then / then·read |
| **Folder**: open, rename, copy:path, trash | rest |
| Folder: copy:to, move:to; export; copy:address | more·Change it; more·Send and keep; more·Edit and copy |
| Folder copies: copy:look, copy:run, copy:pill, copy:review, copy:original, copy:discard | more·This working copy |
| **Several files**: compare:two or compare:revisions, move:to, copy:paths, trash | rest |
| Several files: copy:to; delivery:stage | more·Change it; more·Send and keep |
| **Files empty place**: new:folder, import, view › (view:icons, view:list), refresh | rest |
| new:smart, work:copy, view:all | more·Make and arrange |
| root › (cm:1214): inquiries, algorithms, atlas, line ›, menu:edit | more·Open and show |
| root ›: chains, start | start (Yours, A file in Files) |
| **Finder**: open, show:files, ask, copy:path | rest |
| Finder: change:files | merged into show:files (the same call, cm:724, 729) |
| Finder: open:viewer, adapter:\* | more·Open and show |
| Finder: inspect, run, extract | then |
| Finder: change:none | out\*. The noun says "read only here". |
| Finder empty place: view, hidden, preview, refresh; copy:path; root | rest; more·Edit and copy; more and start |
| **Library**: open, keep, ask, copy:name; empty place import, refresh; root | rest; more and start |
| **Passage**: mark:bold, mark:italic, notes, ask | rest |
| Passage: mark:underline, mark:clear, style › and style:\* | more·Change it |
| Passage: search; doc:new; doc:export | more·Look into it; more·Make and arrange; more·Send and keep |
| Passage: edit:undo, redo, cut, copy, paste, delete, all | more·Edit and copy |
| Passage: inspect (raw `/documents.edit`, cm:403-406) | more·As a line, as "Put this change in the writing line" |
| **Page**: style, edit:paste, edit:all, doc:new | rest |
| Page: edit:undo, edit:redo; doc:export | more |
| Page: edit:cut, edit:copy, edit:delete | Left out on a caret (they never act there); the passage keeps them |
| **Field sheet**: field:open, field:do ›, field:doubt ›, field:ask | rest |
| field:trace ›, field:fed ›, field:feeds ›, field:whatif › | more·Look into it |
| field:run, field:words › | more·As a line |
| field:inspect | then (Its own line) · end:line |
| field:copy, field:brief | more·Edit and copy, more·Open and show |
| Field captions X, T, S, B, Enter, Shift+Enter | removed |
| **Field empty desk**: field:again, field:check, field:brief, first other face | rest |
| Second face, field:back | more·Open and show |
| field:stac › and its rows | start |
| field:words › (Run it, In the line, Forget it, Keep a new word) | start·Yours, plus more·As a line |
| Field captions R, C, P, N, Esc | removed |
| **Today and workspace**: new:idea, new:project, import, inquiries | rest |
| algorithms, atlas, line ›, menu:edit | more·Open and show |
| chains, start | start |
| Caption "Ctrl Shift N" (cm:829) | removed |
| **Log event**: ask, job ›, copy | rest |
| Activity: open, show:log | rest |
| show:log inside the Log itself | Left out (you are already there) |
| **Network**: ask, follow, process, copy:address | rest |
| **Job**: job:output, job:pause or job:resume, job:stop (asks), job:show | rest |
| Job: copy:id; inspect | more·Edit and copy; then·end:line |
| **Agenda work**: queued:pause or queued:resume, queued:stop (asks), job ›, agenda | rest |
| Agenda work: inspect | then |
| **Cabinet**: open, cabinet:write, the first cabinet:workspace:\*, copy:id | rest |
| cabinet:record and the other workspaces | more·Open and show |
| cabinet:check:\* | more·Look into it |
| cabinet:explore and activity:explore (cm:1438) | merged into one Explore, under more·Open and show |
| Cabinet: inspect, run | then |
| export; refresh, view ›, new:\*, import | more·Send and keep; more·Make and arrange |
| actions:none | The heading's noun |
| **Machine and Settings**: every row | rest or more·Make and arrange (§3.3) |
| **Apps and menu rows** (cc:146-166): command:inspect, command:invoke or command:choices, command:work, command:atlas | rest |
| "Continue this chain" (cc:153) | then |
| The meta-menu on the right-click's own rows (cc:53-57) | out\* (F1 describes the row) |
| **Viewer rows** (cc:170-186) | Session 2 `find_viewer`: viewer:folder, viewer:ask, viewer:path go to rest; viewer:chain and viewer:continue go to then |
| **Chain builder** (chm): header line; lenses; where › F › word › V | the slab; then·read; Keep rows where › F › value |
| sort, take, count | Sort by, First, Count |
| group by › count | Count by |
| group by › sum, avg, min, max | Session 2: Total by |
| select, choose columns | Session 2: Only some columns |
| add a column | Session 2: Add a column, which no longer ends the chain (chm:255-264) |
| join with | Session 2: Match with a table |
| then › console, sheet, watch, agenda, keep, copy, shell | Show it, Save as a sheet, Watch it, Add to the Agenda, Keep as a word, Copy the line, To a command (asks) |
| Build on the desk… | Session 2: Lay it out below |
| Tear-off strips | out\* (the panel, and Lay it out below, keep a chain in view) |
| **Unchanged**: worksheet rows, program-room results, Master Stop, Lab, Adaptive, the meters, the companion, text fields | — |

`FOLDED` (cm:2264-2307) keeps its 74 tuples, with the key column rewritten as paths: `more/<key>`, `then/<key>`, `start/<key>`. The pinned test path `'root/menu:edit'` (tcm:621) becomes `'more/menu:edit'`. The Then entry's `submenu` returns the panel's entries (`read:*`, `step:*`, `end:*`), so `menu_tree` (tcm:708-717) can walk it.

### 3.7 Files and functions

**Session 1. No file here is a seed input** (check 1).

| File | Change |
|---|---|
| `workbench/glyph_set.py` | Add `trash`, `pause`, `filter`, `sort`, `group`, `watch`, `trace` and `count = letters('#')` to `GLYPHS` (gs:394-410). |
| `workbench/tool_faces.py` | `icon(key, tone=None)` with `TONES = {None, 'line', 'danger'}`; cache key `(key, t.glow(), tone)` (tf:198). Fix the "amber" docstring (tf:197). |
| `workbench/line_steps.py` (new, no Qt) | • `start_line(host, target)`, one function for every kind in §3.3<br>• `Held(dispatch)` with `.read(line)`, `.rows(line)`, `.count(line)`, `.readings()`<br>• `columns(rows)`, `values(held, line, field)`, `sortable(held, line)`, `firsts(n)`<br>• `steps_left(line)`, `plain(message)`, `ending_ready(n)`, `STEPS`, `Offer(key, words, glyph, step, count, enabled, reason)` |
| `workbench/context_menu.py` | • `Entry` gains `glyph`, `tone` and `group` slots (cm:112-118). `tooltip()` loses the dispatch line (cm:123). `GLYPH_OF`, `REST`, `GROUP_OF` (default by section, cm:51, with prefix overrides). `kind_of(target)`.<br>• `first_level(kind, entries, line)` returns `(rest, more)`. The menu keeps `menu.entries` as every provider row (readers and tests), and adds `first_keys()`, `first_rows()` and `screens()`.<br>• `ContextMenu.__init__` lays out heading, rest, Then or Start from, and More (cm:1926-1945); no foot caption (cm:1942-1944); a labelled `Rule` for the More groups; this menu's metrics use a 20 px icon.<br>• `ContextRow` and `Heading` paint glyphs (cm:1836-1839, 1905-1919); no "unavailable" caption (cm:1883).<br>• `open_child` (cm:2027-2049) gains `drill()`, `back()` and paging when `parent_menu is not None`. Ask screen for `why_asks` rows.<br>• `LinePanel(ContextMenu)` with `Slab` (a QLabel with `bt.line_sheet()`) and `Preview`.<br>• Lazy versions (cm:627-632). Extract, Inspect, Run and Chain move into the line panel (cm:619-634, 537-555, and the inspect rows at cm:732, 807, 869, 976, 1055, 1404-1406).<br>• Every key caption and key word is removed (check 8). The noun loses its revision (cm:306, 309).<br>• Delete `EXTRA`, `_extra_paths` and `paint_icon` (cm:1732-1806). Rewrite `FOLDED`. |
| `workbench/field_page.py` | Drop "(F9)" (fp:397). |
| `tests_integrated/test_context_menu.py` | §3.8. "No new test suites by default" (docs/BOSS_IMPLEMENTATION_PLAN.md:12). |

**Session 2.** Files marked **S** are seed inputs: edit them together and rebuild the seed once (`stacy_foundation.build_seed`, :531).

| File | Change |
|---|---|
| `workbench/shell2.py` **S** | Give `stage()` a `brief` argument that shows a long line by its start, as `say_plan` does (s2:2398). Send `save_rows`, `watch` and `keep_in_agenda` (s2:2822-2834, 2887-2889) through `stage(asked=True)`, which also covers the console's answer links (console_qt.py:473-474). Reword s2:1230 so it names no key. |
| `workbench/command_context.py` **S** | Remove "Shortcut:" (cc:125). The meta-menu goes, per owner question 2 (cc:53-57). `viewer_entries` (cc:170-186) is reused by `find_viewer`. |
| `workbench/chain_menu.py` **S** | `open_here` (chm:502-509) and Commands ▸ Chain Menu open the line panel. `keep()` stores the ending you chose (chm:347). `then` and `to_shell` (chm:269-323) go through the hand. |
| `workbench/menus2.py` **S** | Fix the stale docstring (menus2.py:7-8). |
| `workbench/context_menu.py` | • Endings of §3.4 and §3.5.<br>• Steps Total by, Only some columns, Add a column (number-pair presets), Match with a table (reads the other side once), Look inside (`pick` into nested lists). The rarer ones go under "More steps ›".<br>• Finders: `find_console` (claims the console output before its own menu, cm:1716-1720, cm:2244), `find_agenda_line` (agenda_qt.py:134-141), and `find_viewer` (PDF page only after confirming its file attribute). |
| `tools/check_context_menu_ui.py` | Port the screen captures. |
| `docs/GRAPHITE_DESK.md:803-959`, `docs/DAILY_GUIDE.md:119-131` | Rewrite the right-click section. |

**Not in these two sessions** (later, or waiting on the owner):
- An Undo for rename, move and copy (owner question 1).
- A receipt folder for saved sheets (`chains.save`).
- Office cell grids read as rows.
- Sorting numeric text as numbers; this changes the meaning of lines already kept.
- `this` meaning the sheet's rows (fp:399).
- One store for kept lines.
- Reads off the window's thread.
- Then › on Log events.
- A learned slot.

### 3.8 Tests, with exact assertions

All of these go into `tests_integrated/test_context_menu.py`.

**Rules class** (no window):

```python
SHEET = 'office:owner:' + 'a' * 32
BENCH = [{'parameter': 'Rail voltage', 'value': '12', 'unit': 'V'}, {'parameter': 'Settled current', 'value': '280', 'unit': 'mA'},
         {'parameter': 'Startup current', 'value': '650', 'unit': 'mA'}, {'parameter': 'Startup duration', 'value': '110', 'unit': 'ms'}]

def test_a_line_is_read_once_and_every_offer_is_counted_from_that_read(self):
    from workbench import line_steps
    calls = []
    def dispatch(op, args):
        calls.append(op)
        if op == 'language.parse':
            return {'ok': True, 'result': {'call': {'operation': 'ledger.address.read', 'arguments': {'address': SHEET}}, 'address': SHEET, 'seed_id': 's'}}
        return {'ok': True, 'result': {'object': {'origin': {'reviewed_rows': BENCH}}}}
    base = '@%s | pick origin.reviewed_rows' % SHEET
    held = line_steps.Held(dispatch); held.read(base)
    self.assertEqual(held.count(base), 4)
    self.assertEqual([(o.words, o.count) for o in line_steps.values(held, base, 'unit')],
                     [('is mA', 2), ('is V', 1), ('is ms', 1), ('is not mA', 2), ('is not V', 3), ('is not ms', 3)])
    self.assertEqual([(o.words, o.count) for o in line_steps.values(held, base, 'value')],
                     [('at least 110', 3), ('at least 280', 2), ('at least 650', 1), ('at most 12', 1), ('at most 110', 2), ('at most 280', 3)])
    self.assertEqual(held.rows(base + ' | where unit=mA | count'), [{'count': 2}])
    self.assertEqual(held.rows(base + ' | group unit | count'), [{'unit': 'V', 'count': 1}, {'unit': 'mA', 'count': 2}, {'unit': 'ms', 'count': 1}])
    self.assertEqual((line_steps.steps_left(base), line_steps.steps_left(base + ' | where unit=mA')), (6, 5))
    self.assertNotIn('value', line_steps.sortable(held, base))          # numeric text sorts as text: 110 before 12
    self.assertEqual(calls, ['language.parse', 'ledger.address.read'])  # two reads in all

def test_the_window_never_names_the_language_and_says_the_200_limit(self):
    from workbench import line_steps
    self.assertIsNone(re.search(r'(?i)language|stac|pipeline', line_steps.plain('Shell syntax and command substitution are not part of Stacy language')))
    self.assertEqual(line_steps.ending_ready(450), (False, 'The answer is 450 rows; a line gives at most 200 · keep fewer first'))
    self.assertTrue(line_steps.ending_ready(200)[0])
    self.assertFalse([s.words for s in line_steps.STEPS if s.words.lower().startswith(('where ', 'pick ', 'select ', 'join ', 'take ', 'group '))])

def test_no_string_in_the_menu_prints_a_key(self):
    # AST walk; docstrings and strings passed to QKeySequence are skipped. Today: 21 caption sites in cm, cm:388/394/1259/1261/1280/1414/1417/1420, fp:397.
    self.assertEqual(key_literals(['workbench/context_menu.py', 'workbench/field_page.py']), [])   # session 2 adds command_context.py and shell2.py

def test_every_glyph_the_menu_names_is_drawn(self):
    from workbench.glyph_set import GLYPHS, KIND
    self.assertTrue({'trash', 'pause', 'filter', 'sort', 'count', 'group', 'watch', 'trace'} <= set(GLYPHS))
    for key in cm.glyph_keys():self.assertTrue(key in GLYPHS or key in KIND, key)
    self.assertFalse(any(hasattr(cm, n) for n in ('EXTRA', '_extra_paths', 'paint_icon')))

def test_four_usual_then_more_and_nothing_grey_at_rest(self):
    for kind, usual in cm.REST.items():self.assertGreaterEqual(len(usual), 1, kind)
    keys = ('open', 'open:outside', 'show:folder', 'rename', 'copy:to', 'move:to', 'versions', 'export', 'inspect', 'run', 'chain', 'compare:with',
            'compare:version', 'extract', 'atlas', 'explore', 'delivery:stage', 'explain', 'ask', 'investigate', 'agenda', 'copy:path', 'copy:address', 'trash')
    rest, more = cm.first_level('file', [cm.Entry(k, k, 'open') for k in keys], line='@files:a.csv | rows')
    self.assertEqual([e.key for e in rest], ['open', 'ask', 'rename', 'trash', 'then', 'more'])
    self.assertFalse({'inspect', 'run', 'chain', 'extract'} & set(cm.keys_of(more)))
    self.assertEqual(set(cm.keys_of(more)) | {'open', 'ask', 'rename', 'trash', 'inspect', 'run', 'chain', 'extract'}, set(keys))
    job = [cm.Entry('job:output', 'Inspect output', 'state'), cm.Entry('job:pause', 'Pause', 'state', enabled=False), cm.Entry('job:resume', 'Resume', 'state'),
           cm.Entry('job:stop', 'Stop', 'state', operation='jobs.cancel'), cm.Entry('copy:id', 'Copy the job id', 'edit'), cm.Entry('job:show', 'Show in Jobs', 'open')]
    rest, _ = cm.first_level('job', job, line='@job:' + 'a' * 32)
    self.assertEqual([e.key for e in rest], ['job:output', 'job:resume', 'job:stop', 'job:show', 'then', 'more'])
    self.assertEqual(next(e for e in rest if e.key == 'job:stop').caption, 'asks')
```

`KEY_CAPTION = r'^(?:(?:Ctrl|Shift|Alt|Meta)\b.*|Esc|Enter|Return|Space|Backspace|Tab|F\d{1,2}|[A-Z0-9`])$'`, matched against a whole caption.

`KEY_TEXT = r'\b(?:Ctrl|Shift|Alt|Meta)\s*[+ ]\s*\w|\buntil Esc\b|\b(?:Esc|Enter|Space|Backspace|F\d{1,2})\s+(?:asks|shows|takes|does|keeps|runs|closes)\b|\([A-Z]\)|\(F\d{1,2}\)|\b[A-Z](?:\s*/\s*[A-Z])*\s+(?:shows|tells|does)\b|\bShortcut:'`

These are the patterns `keys_scan.py` used.

**Window class** (offscreen, with the existing fixtures `files` :216, `document` :241, `jobs` :248, `right_click` :78 and `Recorder` :101):

```python
FIRST = {'file': ['open', 'ask', 'rename', 'trash', 'then', 'more'], 'folder': ['open', 'rename', 'copy:path', 'trash', 'then', 'more'],
         'two files': ['compare:two', 'move:to', 'copy:paths', 'trash', 'more'], 'empty:files': ['new:folder', 'import', 'view', 'refresh', 'start', 'more'],
         'passage': ['mark:bold', 'mark:italic', 'notes', 'ask', 'then', 'more'], 'empty:today': ['new:idea', 'new:project', 'import', 'inquiries', 'start', 'more']}

def test_first_level_is_four_usual_then_more(self):
    for kind, menu in self.menus():                      # builds each FIRST kind with the fixtures above
        self.assertEqual(menu.first_keys(), FIRST[kind], kind);self.assertTrue(all(r.isEnabled() for r in menu.first_rows()), kind);close(menu)

def test_every_screen_fits_without_scrolling_and_two_popups_at_most(self):
    for size in ((1366, 768), (1920, 1200)):
        self.w.resize(*size);settle()
        for kind, menu in self.menus():
            for screen in menu.screens():                # first level, More and its drills, the line panel and its drills
                self.assertEqual(screen.scroll.verticalScrollBar().maximum(), 0, (size, kind, screen.title))
                self.assertTrue(screen.bounds().contains(screen.frameGeometry()), (size, kind, screen.title))
                self.assertLessEqual(sum(1 for t in QApplication.topLevelWidgets() if isinstance(t, cm.ContextMenu) and t.isVisible()), 2)
            close(menu)

def test_no_row_prints_a_key_or_unavailable_and_every_row_wears_a_drawn_glyph(self):
    from workbench import tool_faces
    with patch.object(cm.programs_qt, 'paint_icon', side_effect=AssertionError('not Graphite glyphs')):
        for kind, menu in self.menus():
            for screen in menu.screens():
                screen.grab()
                for row in screen.findChildren(cm.ContextRow):
                    for text in (row.word, row.caption, row.toolTip()):self.assertIsNone(re.search(KEY_TEXT, text or ''), (kind, row.word, text))
                    self.assertIsNone(re.fullmatch(KEY_CAPTION, row.caption or ''), (kind, row.word));self.assertNotEqual(row.caption, 'unavailable')
                    self.assertFalse(tool_faces.icon(row.entry.glyph, row.entry.tone).isNull(), (kind, row.word))
            close(menu)

def test_opening_reads_nothing_and_the_line_panel_reads_once(self):
    tab, view, point, root = self.files((('bench.csv', 'parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n'),))
    rec = Recorder()
    with patch.object(cm, 'dispatch', rec):
        menu = right_click(view.viewport(), point('bench.csv'));self.assertEqual(rec.ops(), [])      # today: files.versions (cm:627)
        panel = menu.open_child(menu.row('then'));settle()
        self.assertEqual(rec.ops(), ['language.parse', 'ledger.address.read'])
        self.assertEqual(panel.line, '@files:bench.csv | rows');self.assertEqual(panel.slab.styleSheet(), bt.line_sheet())
        self.assertEqual(panel.count_words(), '4 rows · 6 steps left')
        panel.choose('step:where');panel.choose('field:unit');self.assertEqual(panel.row('where unit=mA').caption, '2 rows')
        panel.choose('where unit=mA');panel.choose('step:count')
        self.assertEqual(panel.line, '@files:bench.csv | rows | where unit=mA | count');self.assertEqual(panel.preview_rows(), [{'count': 2}])
        self.assertEqual(rec.ops(), ['language.parse', 'ledger.address.read'])      # nothing read while choosing
        panel.row('end:show').click();settle()
    self.assertEqual(self.w.console.last_program, '@files:bench.csv | rows | where unit=mA | count')
```

**Stop asks.** This ports `test_jobs_by_state…` (tcm:448) and `…agenda item … that stops` (tcm:520):
- After `menu.row('job:stop').click()`, `'jobs.cancel' not in rec.ops()` and `menu.child.sentence() == 'What it stops or settles cannot be put back.'`.
- After `menu.child.row('ask:yes').click()`, `rec.ops()[-2:] == ['jobs.get', 'jobs.cancel']`.
- When the job moved between the right-click and the yes, the words still contain `'moved on since you right-clicked it (Queued, now Cancelled)'`.

**Tests that change:**
- Nothing lost (tcm:594-629) keeps its loop with the rewritten `FOLDED`, and pins `'more/menu:edit'` (tcm:621). Session 2 adds `FOLDED_CHAIN` for the old builder's words, mapped to `then/*`.
- The metrics test (tcm:679) becomes `menu.m.icon == scaled(20)`, with the row equal to `programs_qt.metrics(w).row` at 14 pt.
- These read `menu.entries` or `first_keys()` instead of the drawn order: `test_today_folds_the_root_chain_menu` (:401), `test_an_empty_place_…` (:671), `test_run_inspect_output_and_extract…` (:540; Extract becomes Read it as), and `test_a_passage_is_named…` (:261; the noun has no revision).

**Campaign anchor** (needs the owner's backup, so it is not in the repository suite): on "07 Bench readings", `held.count(base + ' | where unit=mA') == 2` and `held.rows(base + ' | where unit=mA | count') == [{'count': 2}]`.

### 3.9 Slices

**Session 1: the face and a read-only line.** It needs no seed rebuild and no new Kernel operation. Build in this order, checking after each step:
1. Glyphs and tones in `gs` and `tf`. Run the pure glyph test.
2. In cm: glyph painting, every printed key removed, "unavailable" removed, the dispatch tooltip line removed, the revision removed from the noun, and the foot caption removed. Also fix fp:397. Run the key-scan test.
3. `REST` and `first_level`, More with group words, lazy versions, drill in place with Back and paging, the ask screen for Stop, and the rewritten `FOLDED`. Run the pure shape test and the nothing-lost test.
4. `line_steps.py` and `LinePanel`: Read it as, Keep rows where, Sort by, Count, Count by, First; the endings Show it, Put it in the writing line, Copy the line, Copy the rows; and Start from › (Yours, A file in Files). Run the read-once tests.
5. The window tests at 1366×768 and 1920×1200, then `tools/check_context_menu_ui.py`. These run only once Qt may run on the machine again.

Done means a file's right-click shows 6 rows with Graphite glyphs, and a CSV or reviewed sheet can be filtered, counted and shown from the line panel. That costs 2 reads and adds 3 more for Show it; no key is printed anywhere, and nothing scrolls.

**Session 2: endings through the hand, and the remaining surfaces.**
- The seed-input group: shell2 `stage(brief)` and the three answer endings, cc "Shortcut:", the chain_menu entry points and `keep()`, the menus2 docstring. Rebuild the seed once.
- Endings: Save as a sheet with Undo, Watch it, Add to the Agenda, Keep as a word…, To a command… (asks), Lay it out below.
- Steps: Total by, Only some columns, Add a column, Match with a table, Look inside.
- Finders for the console output, Agenda line rows and viewer pages. Retire `Chain`, `fill` and `chain_icons` from every menu.
- Port the captures and rewrite the docs.

## 4. Questions only the owner can answer

1. **Undo for your own right-click changes.**
   - Rename, Move to and Copy to are done after their dialog today, with no Undo.
   - Giving them an exact Undo means adding `files.rename`, `files.move` and `files.copy` to the Undo allow-list (`UNDOES`, sh:43) and to her Do-and-show list (sh:39). That would also let Stacy (Kasandra) do them by herself at Do and show.
   - The same choice applies to Keep as a word… (`words.keep`): done at once, with Forget as its Undo, or wait for your Approve as now?
2. **May a few dead or third-way rows leave the right-click entirely, rather than sit under More?** Your rule is "Nothing is removed to make it simple" (RECORD_OF_DIRECTIONS.md:213). The rows are:
   - "Nothing changes here · Files keeps its own changes" (cm:736)
   - Show in Log inside the Log
   - The menu that opens when you right-click a row of the right-click menu itself (cc:53-57; F1 says the same)
   - "For <work> ›" on Apps and menu rows
   - New document on a passage (Work ▸ New File and the page's own button already have it)
   - The tear-off strips
3. **Should the right-click wear its glyphs even when Buttons is set to Words?** This plan assumes yes, from "With right click icons too". The other choice is to follow Buttons ▸ Words | Icons, as the head menus do (tf:228-254).