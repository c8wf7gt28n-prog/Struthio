# How Graphite already chains and pipes today

The repo was only read. I made one scratch script, `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/probe_parse.py`. It loads only `typed_pipeline.py` and `addresses.py` by file path and checks the parser claims below. Qt was not started.

## 1. The machinery

**The line itself**
- `typed_pipeline.split` takes one source plus at most seven steps (`sdk/cli/arc1cli/typed_pipeline.py:25`).
  - A lens such as `rows` uses up one of those seven steps (`:75-81`). From a file, that leaves **6 real steps**. Probe: 7 steps parse, 8 fail.
  - These characters are refused anywhere in the line, even inside quotes: `` ` ``, `$(`, `${`, `;`, `>`, `<`, newline (`:16`). Probe: `where Name = "a > b"` fails.
  - Total text is capped at 8192 characters (`:15`).
- The steps that exist (`:51-105`):
  - `take N` (1–200) and `keep rows i,j…` (up to 200 rows, numbered from 1).
  - `select a,b` (1–16 columns).
  - `where f=v`, or `where f over|under|at least|at most|has|is not v`. Plain `=` must match the type exactly (`:228-229`). `over @Other` compares two columns of the same row (`:232-234`).
  - Lenses: `sheet NAME | rows | facts | layers | lines | headings | texts`, and `pick path`.
  - `sort [-]f`, `count`, `group f1..f4`, then one of `sum|avg|min|max f`, which also adds a `count` (`:268`).
  - `add NAME = arithmetic` with `+ - * /` and brackets, never evaluated as code (`:112-136`).
  - `join|missing @addr [lens] on F` (`:98-104`). The address must be one word (`JOIN` regex, `:10`; probe: `@files:b c.csv` fails). Only one level deep: a joined source cannot join again (`workbench/stacy_language.py:79-80`).
- Not in the language: distinct, rename, OR, sorting by several columns, offset, and any text or date functions. Probe: `distinct` gives "Unknown transform".
- Size limits:
  - A source may hold 2000 rows or 512 KiB (`typed_pipeline.py:219`).
  - **The answer may hold at most 200 rows, or the whole line fails with "Output exceeds 200 rows; add take"** (`:272`; `stacy_language.py:112`). A joined side may hold 2000 (`:112`, `:125`).
  - Files gives at most 2000 data rows (`workbench/files_service.py:254`, `:278`).
- Shortcut names: `jobs`, `models` and `activity` stand for `jobs.list`, `brain.models` and `ledger.journal.read` (`typed_pipeline.py:46`).
- Sources:
  - A line's source must be a registered read-only operation, not `language.*` (`stacy_language.py:60-71`).
  - `@kind:id` is rewritten to `ledger.address.read` (`:38-44`). The kinds are listed in `addresses.KINDS` (`workbench/addresses.py:20-61`), e.g. `files`, `document`, `office`, `job`, `evidence`, `idea`, `project`, `component|net|requirement` (selectors).
  - A file name with spaces is accepted as the main source. Probe: `@files:Rev C notes.md | headings` parses.
- Every run needs a verified seed, otherwise everything fails with "seed/source binding is not current" (`stacy_language.py:9-13`).
- A result carries `'model_calls': 0` (`:127`).

**The chain builder** (`workbench/chain_menu.py`)
- `Chain` is a QMenu that runs the line built so far when it opens, once (`:99-109`).
- `fill` builds each menu (`:128-150`):
  - It starts with a header row showing the line so far in mono print (`:112-115`) and "Build on the desk…" (`:132`).
  - If the answer is not rows, or is the file object itself (it has a `view` or `address` key), it offers `lenses` (`:136-137`). Otherwise it offers `shape` (`:139`).
  - It ends with `then`.
- `run` is `language.run` called directly, with no `this` and no word written out (`:47-52`).
- What `then` offers (`THEN`, `:36`; `:141-148`):
  - show it in the console, save as a sheet, watch it, add to the Agenda;
  - `shell ▸` (your kept `[shell]` commands, or type a command);
  - keep this chain…, copy the line.

**The menu file** `~/Concern/Ledger menu` (`:331-333`)
- Format (`:353-360`; regex `:40`): `[chain] (Name) {line} then console|sheet|watch|agenda`, `[stock] (Name) {json}`, `[shell] (Name) {command}`, `[submenu]…[end]`, `[separator]`.
- `parse_menu` turns it into a tree plus a list of problems (`:363-391`). An unknown `then` becomes `console` (`:374`).
- A `[stock]` line is a unit, or a shortage-method record carrying the source's SHA-256 and the selected rows (`:394-413`). They are listed by `stock_methods` (`:416-425`) and their runs live in `Slate/Chains/Methods/<id>` (`:428-429`).
- `keep` appends `[chain] … then console` straight to the file, without going through the Kernel (`:336-350`). The destination you picked is never stored.
- Kept chains are shown greyed when they fail `typed_pipeline.parse(source(p))` (`:447`; `context_menu.py:1166`).

**The chain tray** (`workbench/chain_workbench_qt.py`)
- `stage` lays out one chip per step. Each chip carries the line up to that step and re-opens the builder from there (`:165-201`, `:220-225`).
- Preview (`:227-255`):
  - It runs `language.parse` to get the seed.
  - It fingerprints each source before and after (`sources_now`, `:42-60`; `source_calls` follows join sources, `:31-39`).
  - Then it runs `language.run` with `expected_seed` and shows the first 100 rows and 20 columns (`:257-280`).
- Run re-checks the seed and sources (`current_preview`, `:282-294`), then puts the shown rows in the console (`:296-304`).
- Save sheet (`:306-335`):
  - It writes `Slate/Chains/chain-<hex>.csv` plus a `.json` receipt with `execution='LOCAL_NO_MODEL'`, the sources and the seed (`:314-316`).
  - It is refused at 200 rows or more, or when a source view was cut short (`:308-309`).
- Keep method calls `chain_menu.keep`, which writes `then console` (`:337-340`). Edit in strip calls `inspect_in_line` (`:342-345`).

**The console** (`workbench/console_qt.py`)
- `run_stac` sets `last_program` only when the line ran (`:470`). Under each answer it offers save as a sheet · watch it · add to the Agenda · again (`:473-474`).
- Right-clicking the output gives Qt's own text menu with `chain_menu.fill(last_program)` added below it (`:445-451`).
- The Agenda does the same for items whose program starts with `@` (`workbench/agenda_qt.py:127`, `:134-141`).

**Words** (`workbench/stac_words.py`)
- `word NAME = LINE`, `NAME`, `NAME | …`, `explain NAME`, `words`, `forget NAME` (`:1-24`).
- They are stored in the Kernel's `stac_words` table (`:43`).
- A word is checked with `language.parse` and kept fully written out (`:72-93`). The only exception: a line starting with `this` is kept without the parse check (`:82`).
- Written out only by the writing line (`typebar_qt.py:399-402`), its context hint (`:665-667`) and its preview (`shell2.py:1226-1231`). `this` is written out in the same places by `field_page.expand_this` (`field_page.py:385-399`).

## 2. Each right-click target: its line today, and what chaining it is offered

| Target (finder) | Line that reads it today | Offered from the right-click |
|---|---|---|
| File, drawing, datasheet or table in Files (`find_files`, `context_menu.py:1483-1499`) | `staC_for_file` = `@files:REL \| <lens by suffix>` (`:68-69`, `:210-213`) | Inspect in the line, Run, **Chain from here** (starts from bare `@files:REL`, `:624`), Extract (lens rows with counts, then straight to the console, `:537-555`). All are disabled when the name has a space or a bar (`needs_quotes`, `:216`, `:619-625`), although only `join` needs one word |
| Several files selected (`:674-694`) | none (a line has one source) | none |
| Folder or smart folder | none (staC only `if not folder`, `:617`) | none |
| Finder entry inside Files (`:713-739`) | `staC_for_file` | Inspect, Run, Extract. **No Chain from here** (`:730-734`) |
| A file open in a viewer (`command_context.py:170-186`) | `staC_for_file` (checks only for a bar, `:181`) | Build a chain from this file (the tray), Read and transform (the builder) |
| Passage or page (`:381-427`) | only an operation line, `/documents.edit {…}` (`:403-406`). A read `@document:<id>` exists (`addresses.py:25`; Field form: `documents.get {"id":…} \| pick document.blocks \| select text`, `field_source.py:216`) but is not offered | none |
| Cabinet record (`:777-813`) | `@<canonical>` when its kind is in `KINDS` and is not a selector (`:802-808`) | Inspect, Run |
| Work on the Machine tree (`:869`) | `@<canonical_id>` | Inspect only |
| Job (`:957-979`) | `@job:<id>`, its output `@evidence:<id>` (`:962-964`) | Inspect output (runs), Inspect |
| Agenda work (`:1033-1058`) | its stored `program` | Inspect |
| Network connection or packet, event (`:1101-1138`) | none. The Field reads these with `network.observe \| pick connections \| where process=X` (`field_source.py:395`), and `activity` (`ledger.journal.read`) could read events | none |
| Setting, Library file (`:756-763`, `:883-893`) | none | none |
| A sheet on the Field (`:1342-1431`) | `obj.stac`, e.g. jobs `jobs \| where id=… \| select tool,state,goal` (`field_source.py:319`), office `office.get {"id":…} \| select source_state.state` (`:180`), documents `:206`, `:216`, `:232`, conditions `:299`, network `:364`, `:395`, programs `:499` | Inspect its line, Run its line, Your words (`this`-based, `:1421-1423`), What can be done (from the records: a read runs at once, a change is put up and waits, `:1267-1281`), What if, Doubt, Trace. **No chain builder** |
| Empty place on the Field | "This face as lines": fixed lines per face (`:1363-1378`) plus your words (`:1381-1390`) | each goes to the writing strip |
| Empty place (Today, workspace, Files, Finder, Library) | none | Root (`:1197-1211`): Your chains (`:1149-1174`), Start a chain from (up to 30 files of the table, markdown, dxf, stl, obj, 3mf, text and json kinds, `:1177-1183`), Writing line |
| Worksheet rows (its own menu, `sheet_workbench_qt.py:572-640`) | `files.get {"path","expected_sha256","sheet"} \| rows \| keep rows …` (`:548-560`) | Calculate ▸ Required − available ▸ Keep positive or all (`add Shortage = …`, `where Shortage over 0`, `select …`, `:705-729`), Method Press, Preview selected rows, Preview the plan (`explain`), Copy the selection as a line |
| Console output, Agenda `@` item | `last_program`, or the item's program | the full builder |
| Menu row or command (`command_context.py:44-62`, `135-167`) | none | Continue this chain when that row was the builder (`:152-153`) |

**`this` on the Field keeps only the first step of the sheet's own line** (`field_page.py:399`).
- For a sheet whose line starts from a list and filters it (job `jobs | where id=…`, condition, network, program, intake: `field_source.py:145`, `:299`, `:319`, `:364`, `:395`, `:499`), `this | …` reads the whole list, not the sheet.

## 3. What a step can offer (real values from the data)

- **Lenses** (`chain_menu.py:153-166`):
  - sheet names from `pick data.sheets` (up to 12);
  - then each of `rows, headings, layers, texts, lines, facts` that gives records.
  - Each carries its row count ("N rows", `:74-76`, `:120`).
- **where** (`:199-227`):
  - Up to 24 fields, taken from the first 50 rows.
  - A numeric column (seen in the first 500 rows) offers over / under / at least / at most × up to 8 values spread across its distinct values (`:208-216`).
  - A text column offers is / is not / has × its 8 most common values (`:218-227`).
  - **Each value shows how many rows it keeps.** That count comes from a full `language.run`.
- **sort**: each field, smallest or largest first, no counts (`:173-177`).
- **group by** a field ▸ `count`, or `sum|avg|min|max` of up to 8 numeric fields, no counts (`:178-186`). Grouping by several fields at once is not offered, though the language allows up to 4.
- **select**: "only F" (up to 24); "choose columns…" opens a dialog (`:187-189`, `:255-257`).
- **add a column…**: a dialog prefilled with the first two numeric columns (`:260-264`).
- After "choose columns…" or "add a column…" the chain goes **straight to the console**, so it cannot go on from the menu.
- **join with**: up to 16 csv or spreadsheet files from `files.find`, with one-word names and sharing a column (up to 6 columns). Each offers join on F or missing on F, with counts (`:230-252`).
- **take**: first 5, 10 or 20. **count** is a final item that shows its number (`:193-196`).
- In the language but not in the menu:
  - `keep rows`;
  - `where F over @Other`;
  - `pick` into nested lists. For a record source such as `@job:x` or `@document:x`, `fill` treats the one object as a single row and offers where/sort over its top-level keys, with no way to step inside a nested list such as `document.blocks`.
- Other step offers that need no model:
  - `explain.explain` suggests `take 10`, `count`, `sort -N | take 5`, `where N over 0`, `layers`, `texts`, `headings`, `lines | where text has TODO`, `facts` (`workbench/explain.py:21-51`);
  - the Field's `steps_for` (`field_do.py:241`).

## 4. Where a chain can end, and what each ending changes

| Ending | Code | What it changes | Goes through the hand rules / Undo? |
|---|---|---|---|
| show it in the console | `then('console')` stages the tray and runs `console.run_stac` (`chain_menu.py:271-274`) | nothing | not needed (a read) |
| save as a sheet | `face.save_rows` writes `Slate/answer <time>.csv`, **no receipt** (`shell2.py:2822-2829`) | files.write | **No.** `stacy_hand.takes_back` already knows a files.write Undo (moving the file to the Trash, `stacy_hand.py:201-202`), but nothing records it |
| tray: Save sheet | `Slate/Chains/chain-<hex>.csv` plus receipt (`chain_workbench_qt.py:306-335`) | files.write ×2 | No |
| watch it | `agenda.add {watch:true, nice:background}`, asked again every 6 hours (`shell2.py:2831-2834`) | agenda.add | No Undo (taking it out is `agenda.cancel`, which always asks, `stacy_hand.py:52`) |
| add to the Agenda | `agenda.add` (`shell2.py:2887-2889`) | agenda.add | No |
| keep this chain… | appends to the menu file (`chain_menu.py:336-350`) | a local file, outside the Kernel | No; always written `then console` |
| shell ▸ kept command or typed | **overwrites** `Slate/answer for the shell.csv`, then runs the command at once in the console's Shell page with `$LEDGER_ANSWER` (`chain_menu.py:311-323`) | files.write plus any command | **One click on a kept `[shell]` runs it** (`:299`), although `shell.*` always asks (`stacy_hand.py:56`) |
| copy the line | clipboard (`:326-328`) | nothing | not needed |
| keep as a word | typing `word NAME = …` only (`stac_words.py:123-129`; the Field's "Keep a new word…" puts `word ` in the line, `context_menu.py:1337`) | words.keep replaces a word of the same name (`stac_words.py:91`) | No |

- Never an ending today: a page (documents.create), an Office sheet, the rows copied as CSV/TSV, a compare, a Field sheet, `stac.export` (approve scope, `stac_bridge.py:178-181`).
- The proper path for a change already exists: `SlateFace.stage` / `run_staged` follow the hand rules (`stacy_hand.hers`) and record a trail entry with an Undo (`shell2.py:1991-2070`, `field_do.Step` `:26-33`).

## 5. Preview and keeping

- Inside the builder, a count is shown only on lens, sheet, where-value and join items. There are no example rows, and none on sort, group, select or take. "Build on the desk…" gives the full preview (tray, section 1).
- In the writing line, typed `| …` shows a 4-row preview, read only (`shell2.py:1221-1243`).
- **Every count is a synchronous `language.run` on the window's thread that reads the source again.** Opening one numeric where-field means 32 runs (4 words × 8 values). Join adds 2 × up to 6 per table × up to 16 tables (`chain_menu.py:215`, `:248`).
- Two stores for kept lines that do not know about each other:
  - the menu file: runs a chain with its ending, cannot be continued;
  - words in the Kernel: can be continued by typing, have no ending.
- `chain_menu.run`, `then` and `console.run_stac` (`console_qt.py:454-455`) do not write out words or `this`. So a kept chain such as `waits | count` or `this | …` parses (the operation-name regex accepts any lowercase name) and shows enabled (`chain_menu.py:447`), but is refused when it runs.

## 6. The model

- **No chain step and no ending uses the model.** `language.run` reports `model_calls: 0` (`stacy_language.py:127`). The receipt says `LOCAL_NO_MODEL` (`chain_workbench_qt.py:316`). Words "do not depend on any model" (`stac_words.py:16`). Watch re-runs the line itself.
- The model only adds prose to:
  - the "Ask Stacy" rows (with no model she answers from the records, `context_menu.py:275-276`, `:1429`);
  - Doubt and Trace on the Field (`field_page.py:403-404`, `:416-418`);
  - free-form requests.

## 7. What already works end to end with the model off

The general preconditions: a verified seed, a file name with no space or bar, at most 200 rows at every step, and at most 6 steps after a lens. Under those:

1. In Files, right-click a file ▸ Chain from here ▸ a lens (count) ▸ where ▸ field ▸ is or over ▸ value (count) ▸ … ▸ then ▸ console, sheet, watch, Agenda, keep, copy or shell (`context_menu.py:624` → `chain_menu.fill`).
2. Build on the desk ▸ the tray: Preview with fingerprints, Save with receipt, continue from any chip, Keep, Edit in strip.
3. Run a line in the console ▸ right-click the output ▸ keep chaining (`console_qt.py:445-451`).
4. Root menu ▸ Your chains ▸ runs with its stored ending (`context_menu.py:1149-1174`).
5. Worksheet rows ▸ Calculate or Method Press ▸ tray preview ▸ save with receipt (`sheet_workbench_qt.py:572-729`).
6. Field sheet ▸ Run its line, Your words, What can be done (reads run; changes are put up under the hand rules).
7. Typing `NAME | …` or `this | …` in the writing line, with the 4-row preview.

## 8. Missing for "right-click a thing, pick a next step, then another, and end somewhere"

1. **One function that gives each target its read line.** Today the lines are scattered:
   - `staC_for_file` and `LENS` (`context_menu.py:68`, `:210`), the cabinet (`:806`), the job (`:962`), `obj.stac` (`field_source.py`), the Field face lines (`context_menu.py:1363-1378`), the worksheet `program` (`sheet_workbench_qt.py:548-560`).
   - Not covered at all: passage or page (`@document:<id> | pick document.blocks`), folder (`files.list {"path":…} | pick entries`), connection and packet (`network.observe | pick connections | where …`), event (`activity | where id=…`), Office sheet (`office.get` returns cells, not rows, `context_menu.py:1246`, and no lens converts them, `typed_pipeline.py:12`), several files at once (one source only).
   - Files touched: `context_menu.py` providers, `command_context.py:170-186`, `field_page.expand_this`. **New:** a lens from cells to rows in `typed_pipeline.LENSES` or `office_service`.
2. **One "then ▸ next" cascade on every target that has a line.** It is missing on Finder entries, cabinet records, jobs, Agenda work, Field sheets and the Log. One idea is spread over four rows today (Inspect, Run, Chain from here, Extract; `:620-634`). Lift the over-strict space guard: only `join` needs one word. Files: `context_menu.py`, `chain_menu.fill`, `chain_menu.lenses`.
3. **Tables over 200 rows.** A lens over 200 rows is silently left out (`chain_menu.py:164`). `fill` then stops with "does not run" (`:133-135`), because the answer limit is 200 (`typed_pipeline.py:272`; `stacy_language.py:112`). Needed: a step count with "first 200 of N" (the tray already knows about cut-short sources, `chain_workbench_qt.py:238-240`), or a narrowing step offered first. Files: `stacy_language._execute_plan`, `typed_pipeline.apply`, `chain_menu.lenses/fill`.
4. **Show the step budget.** Nothing shows how many of the 6 or 7 steps remain. Sort, group, select and take are built without running, so at the limit they look usable and fail only when opened. Files: `chain_menu.header`, `link`, `shape`; parser rule `typed_pipeline.py:25`.
5. **Dialogs that end the chain.** "add a column…" and "choose columns…" end it (`chain_menu.py:255-264`). They should be links: `add` presets from numeric column pairs, column picks. Also offer `keep rows`, `over @Other` and multi-field `group`, and step into nested lists of record sources (`pick`).
6. **Endings that follow the hand rules.** Endings that change something (save as a sheet, watch, Agenda, keep, word, shell) should go through `SlateFace.stage(…, asked=True)` with a `field_do.Step(kind='write', scope=…)`, so they appear in the trail with an Undo (`stacy_hand.takes_back` already knows files.write). Shell must always ask. Keep must store the chosen ending. "save as a sheet" and the tray's Save sheet should become one ending with a receipt. Add as endings: keep as a word (`words.keep`), copy rows, new page or sheet. Files: `chain_menu.then/keep/to_shell`, `chain_workbench_qt.save_sheet/keep`, `shell2.save_rows/watch/keep_in_agenda`, `stacy_hand.HERS_SHOW` (it already lists `files.write` and `agenda.add`, `:39`).
7. **One store for kept lines, and write words and `this` out everywhere.** Write them out in `chain_menu.run/then`, `console.run_stac` and `context_menu.run_stac`. Make `this` mean the sheet itself, not the first step of its line (`field_page.py:399`). Let a kept chain be continued, not only run. Files: `stac_words.py`, `chain_menu.py:432-455`, `context_menu.py:1149-1174`, `console_qt.py:454`, `field_page.py:388-399`.
8. **Speed and fit.**
   - Counts run one after another on the window's thread (section 5). They should be read once and counted from the rows already held, or run off the window's thread.
   - Lists are long: "start from" holds 30 files (`chain_menu.py:472`; `context_menu.py:1182`); sort, group and select up to 24 fields; kept chains unbounded.
   - The builder is a QMenu with tear-offs, popped up from inside the right-click menu (`context_menu.py:2036-2042`), so one cascade mixes two kinds of menu.
9. **Words and look.**
   - The parser's error says "Stacy language" (`typed_pipeline.py:16`), which names the language on screen. It reaches the screen through `chain_menu.py:122`, `:135` and `chain_workbench_qt.py:255`.
   - The line so far is shown in mono print (`chain_menu.py:112-115`) and in the tray as plain text on the panel colour (`chain_workbench_qt.py:136-151`). It is not on the royal slab (`bt.line_sheet()`, as `shell2.py:2016-2017` uses).
   - The chain's pictures (`chain_icons.py`) are not `GLYPHS`. Their colours are fixed hex values (`:7`). "copy the line" gets no picture, because the lookup still says "copy the stac" (`:102`, against `chain_menu.py:147`).
   - The right-click rows still print keys as captions: `Ctrl B`, `Ctrl Z`, `Enter`, `Shift+Enter`, `S`, `X`, `T`, `D`, `B`, `R`, `C`, `Esc`, `Space` (`context_menu.py:388`, `394`, `417-423`, `750`, `829`, `1290`, `1310`, `1354-1361`, `1379`, `1395`, `1404-1418`; drawn at `:1917-1918`). The word preview prints "Ctrl+Enter keeps this word" (`shell2.py:1230`).