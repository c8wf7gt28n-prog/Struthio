**Surfaces for Inspect, failure and menus: claims 1, 7 and 8 checked against the code (HEAD 34f00ba, read only)**

The right-click machinery already exists and could carry Inspect / Open method / Fork, but nothing hooks onto Kas's own results in Talk. There is no per-project place for commands. Plan cards show which step stopped, but nothing sorts failures into kinds. Everything except free-form chat runs with the model off.

## Verdicts

### Claim 1 (right-click a result, open the operation; Preview / Open method / Fork): PARTLY

What holds:
- The right-click is built from small provider functions. Adding entries means adding rows to a provider (`context_menu.py:1442` PROVIDERS, `:1449` entries_for). New targets need a finder (`:1701`).
- A file in Files already offers:
  - Open (`:604`)
  - Inspect in the line (`:620`)
  - Run (`:622`)
  - Chain from here (`:624`)
  - Extract (`:633`)
  - Compare and Versions
- The Finder offers the same staC rows for files inside Files (`:732-734`).
- A Field sheet offers:
  - Inspect in the line, Run its staC (`:1404-1406`)
  - What can be done (`:1418`)
  - Your words (`:1389`, `:1422`)
- Right-clicking a menu command or a Programs row gives "Inspect this command / capability" (`command_context.py:146`). It shows label, kind, tooltip, shortcut, whether it is available, operation and the work it is bound to (`:120-133`).
- The console output's right-click carries on from the last staC answer as a chain (`console_qt.py:445-451`).

What does not hold:
- **Talk cards (Kas's answers, StagedRun, PlanRun) have no right-click of Graphite's own.** No finder covers Talk (`context_menu.py:1701`). An offscreen check (Qt with no screen) of `target_at` on a Talk-shaped card returned None for the staC label, the answer label, a plain note and the frame. `owns_menu` stops the walk at any QLabel (`:1705-1709`).
- Her cards carry words instead:
  - answer card: "in the line · watch it · add to the Agenda · save as a sheet" (`shell2.py:1925-1928`)
  - staged card: Approve and "in the line" (`:1976-1978`)
  - plan card: each exact line plus "Approve all N" (`:2357-2361`)
- There is no Open method, Fork or Preview anywhere.
- **A result Kas saves cannot be traced back.** `save_rows` writes `Slate/answer <time>.csv` with no receipt; the source line appears only in the status bar (`shell2.py:2779-2786`).
- "Inspect" already means four different things: put the staC in the line, describe a command, the program rooms' primary Inspect (read the source file, `program_rooms_qt.py:227-235`), and "Inspect source" on worksheet rows (`sheet_workbench_qt.py:636`).

### Claim 7 (debugging a failed run)

**Last step that worked, first that stopped, what it had in hand: PARTLY.**
- `run_plan` marks each row "done" or "REFUSED: msg" and stops at the first refusal (`shell2.py:2379-2394`). Its results are kept on the card only (`:2385`); what the earlier steps returned is not shown.
- `started()` says "I stopped at the step that was refused, after N of M" (`:2203`).
- A staC line fails as one message with no stage index: `typed_pipeline.apply` and `pick` raise plain errors (`sdk/cli/arc1cli/typed_pipeline.py:152,186-273`).

**Three failure kinds pointing to three remedies: DOES NOT HOLD as a classification.**
- The Kernel's error is `{code: <exception class>, message}`. In the run below every refusal came back as `"code": "ValueError"`.
- Fragments of the three kinds exist:
  - missing input: `readable_error` turns errno 2 into "Missing input · …" (`ux_polish.py:33-44`); messages carry prefixes such as `ADDRESS_UNAVAILABLE` and `MISSING_SOURCE`
  - missing tool: inspect results carry the state `TOOL_UNAVAILABLE` (`program_build.py:198`, `program_vector.py:234`)
  - malformed output: per-program sentences only, e.g. "Inkscape returned an unreadable PNG" (`program_vector.py:266`)

**Diagnostics still suffice with the model off: HOLDS.** Every refusal comes from Kernel or program code; no model is involved (verified).

**Plain words, with exit status and diagnostic under a disclosure: PARTLY.**
- Kernel jobs keep `exit_status`, `stdout` and `stderr`. A failed job's error reads "Tool exited with status N: <last log line>" (`engineering_kernel.py:1536-1579`).
- Talk shows only `job.error or state` (`shell2.py:2591`).
- The program rooms send stderr to DEVNULL (`program_build.py:233-235`, `program_vector.py:258,298`). The room's status line shows plain words, with the raw message only in a tooltip (`register_tabs.py:54-55`).
- The Terminal prints "exit N · secs" (`console_qt.py:603`).
- A disclosure widget already exists, `program_detail` (`shell2.py:1679-1690`). It is used at `:2339`, `:2611` and `:2660`.

**Ordinary actions on the surface, Inspect one click away: PARTLY.** Menu sections put "open" first (`context_menu.py:51`), and Files shows Open, Run and Inspect together. Talk does not.

### Claim 8 (a right-click menu that grows from your work)

**Precedent that holds:**
- The worksheet row menu shows **Method Press** only on tables with Part, Required, Available and Unit columns (`sheet_workbench_qt.py:542-546,596,612-631`).
  - "Keep shortage method…" saves a `[stock]` record with column bindings and the source sha256 (`:675-679`; `chain_menu.py:336-360,394-413`).
  - Re-running refuses changed columns, a different unit, or blank or mixed units (`sheet_workbench_qt.py:662-673`). The total says "Mixed or missing units" (`:744-751`).
- Kept chains appear under right-click › Root › "Your chains" (`context_menu.py:1149-1174,1208`).

**Per-project tools: DOES NOT HOLD.**
- The menu file is `concern_home()/Ledger menu`, one per user (`chain_menu.py:331-333`; `locations.py:48-49`; the run below printed the resolved path).
- staC words are per workspace (`stac_words.py:16-17,42-43`).
- Tools is a fixed list (`menus2.py:275`). Only Engineering depends on a project being attached (`:262`).
- Programs is a fixed list built from explore.VIEWS (`programs_qt.py:670-674,708-710`).
- Favorite commands pin existing application actions only (`presentation_qt.py:56-74`).

**Kas proposes, the owner pins: DOES NOT HOLD.** The menu file is written only through a dialog (`chain_menu.py:336-360`). There is no Kernel operation for it, and nothing in her lists (`stacy_hand.py:39-43`).

**A pinned command runs with the model unloaded: HOLDS.** Kept chains run through `then()` and `language.run` (`chain_menu.py:269-280`); the chain receipt records `execution='LOCAL_NO_MODEL'` (`chain_workbench_qt.py:316`). Words ran with `NO_MODEL_SELECTED` in the run below.

**A method change is shown as a difference before the menu moves: DOES NOT HOLD.**
- The menu file is re-read at every opening and has no ids or revisions (`context_menu.py:1153-1155`).
- `words.keep` replaces an existing word silently (`stac_words.py:19`).
- The only related notice is "new source revision" when the *data* file changed (`chain_workbench_qt.py:241-247`).
- Revision discipline exists only for `checked_methods`, which has one profile (additive capacity): revise and accept (`checked_methods.py:5,24-27`), and refusal of a changed or unaccepted method (`:46-50`).

**Cited docs: HOLD.**
- `docs/STAGE5.md:60-68`: procedures exist in code (`continuing_work.py:51-58`). Their only interface is the Continuing work room (`continuing_work_qt.py:228-242`), not a menu.
- `docs/BOSS_IMPLEMENTATION_PLAN.md:176` is item P14, marked "State: PLANNED." (`:182`).

## What runs with the model off

These run with no model:
- staC reads and `explain`. Explain reports `model_calls: 0`.
- Kept chains, words and the Method Press.
- Field steps, doubt and trace.
- Approve and Undo (`shell2.py:1989-2066,2371-2401`).
- Kas's own acts. They are matched by rules before `brain.status` is even read (`shell2.py:2500-2504` against `:2516`): own words, Godot start, make a file/folder/page/note, set a cell, Terminal reads, what-if.

These need the model:
- Free-form questions (`brain.ask`, `:2566-2576`).
- Saying an answer in her own words (`:2521-2539`).

`brain.stop` turns the model off (`local_brain.py:978`, `brain_qt.py:232`).

## Runs

Each ran in `unshare … venv/bin/python -B` with `QT_QPA_PLATFORM=offscreen`, temporary HOME, `ARC1_WORKBENCH_CONFIG_HOME` and `ARC_LEDGER_CONCERN`, and `ARC_LEDGER_EMBEDDED=1`, on a `git archive HEAD` copy.

**Through the in-process Kernel** (fixture: A–D at 0.49, 0.50, 0.69, 0.70 mm; E = 0.028 in; F = 0.60 with a blank unit):
```
brain.status state: NO_MODEL_SELECTED
OK   language.run "...| where Clearance under 0.50 ..." -> A 0.49 mm, E 0.028 in
OK   language.run "...| where Clearance under 0.70 ..." -> A, B, C, E, F
FAIL language.run "@files:SLIM4/nothere.csv | rows" -> {"code":"ValueError","message":"ADDRESS_UNAVAILABLE: FILES_NOT_FOUND: SLIM4/nothere.csv"}
FAIL language.run "... where Clearance <= 0.5" -> {"code":"ValueError","message":"Shell syntax and command substitution are not part of Stacy language"}
FAIL programs.godot.inspect -> {"code":"ValueError","message":"MISSING_SOURCE: SLIM4/project.godot"}
OK   methods.list -> []    OK procedures.list -> []    OK words.keep "clear" ... (runs with no model)
explain -> {"schema":"arc.stac-inspection/1","steps":[read files.get, pick data.rows, compare Clearance < 0.5],
            "required_scope":"read","effects":["read"],"source_binding":{"state":"VERIFIED_SEED",...},"executed":false,"model_calls":0}
```

staC alone cannot do the clearance check correctly:
- The 0.028 in row fails as if it were 0.028 mm.
- The blank-unit row passes at 0.50 and fails at 0.70, with no "Unit missing".
- `where Unit=mm` silently drops both rows.
- There is no conditional or unit-conversion step ("Unknown transform").
- `<=` is refused, so a threshold has to be written as `at least` / `under`.

**Menu file parsing:** `parse_menu` reads `[submenu] (SLIM4) [chain] (Check enclosure clearance) {…} then sheet` with no problems. A kept chain that does not parse is greyed with its reason.

**Kas's acts:** her place on the dial (ask / show / free) decides `hers()`. `programs.godot.open` waits at show ("the records mark it for your approval"). `procedures.instantiate` is never hers.

## Point 9: what the experiment can stand on

1. Right-click providers and finders (`context_menu.py:1442,1701`), plus "Inspect this command" (`command_context.py:120-146`).
2. `stac.inspect` as the at-a-glance content: input, steps, effects, saves or not, model calls (`stac_bridge.py:166`).
3. The worksheet Method Press as the shape of "Keep this method", including column-role compatibility, unit refusals and the source sha (`sheet_workbench_qt.py:542-685`; `chain_menu.py:336-413`).
4. The chain tray's preview, source digests and the receipt saved beside the CSV, with `LOCAL_NO_MODEL` (`chain_workbench_qt.py:42-63,227-335`).
5. Staged and plan cards with exact lines, Approve, Undo with guards, and her trail (`shell2.py:1948-2144,2344-2401`; `stacy_hand.py:193-262`).
6. The `program_detail` disclosure (`shell2.py:1679`) and job records with `exit_status` / `stdout` / `stderr` (`engineering_kernel.py:1569-1579`).
7. `brain.stop`, and the answer path that works with no model (`shell2.py:2541-2556`).

## Point 9: what is missing, with the files each piece touches

1. **A Talk finder and provider** (Inspect / Preview / Open method / Fork) keyed on `card.stac` or `card.step`. It must recognise the card from a child label, because the walk stops at labels. Files: `context_menu.py`, `shell2.py`.
2. **A run record on Kas's answers**: line, plan id, seed, source digests, row digest. `save_rows` should write a receipt the way `save_sheet` does. Files: `shell2.py:1874-1931,2779-2786`, reusing `chain_workbench_qt.sources_now`.
3. **A clearance method kind**: fields, minimum with its unit, the ≥ rule, the exact in→mm conversion shown, and a "Unit missing" verdict. It needs to be a Kernel operation, since staC cannot express it. Files: a new module registered like checked_methods (`engineering_kernel.py:177,566`), with an entry in `sheet_workbench_qt.py:open_menu`.
4. **A fork record** with parent id and parent revision, shown as a difference before following a changed original. Files: the method module, the menu-file grammar (`chain_menu.py:39,363-391`), or `stac_words.keep`.
5. **A per-project command store**, plus a rebuilt-on-open Tools key in the style of `@cabinet` and entries on a compatible table's right-click. Files: `chain_menu.menu_path`, `menus2.py:229-275`, `context_menu.file_entries`, `sheet_workbench_qt.open_menu`.
6. **A pin operation Kas can propose and the owner approves**, kept out of HERS_SHOW. Files: Kernel scopes, `shell2.stage`, `stacy_hand.py`.
7. **A side-by-side preview** of original and fork on the same source digest. Files: `chain_workbench_qt.py`; or `files.compare` on the two saved receipts.
8. **Failure kinds** (bad input / missing tool / malformed output) with the stage index and partial rows, shown under `program_detail` in Talk. Files: `typed_pipeline.apply`, `shell2.run_plan`, `shell2.poll`; and the program runners that discard stderr.
9. **Kas explaining from your version** needs the method or fork record added to `facts` in the grounded path. Files: `shell2.py:2529-2535`.

Files are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/take_apart/surfaces:
- scripts/pure.py
- scripts/kernel.py
- scripts/walk.py
- prog/ (the git archive copy the runs used)