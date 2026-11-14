Claim 3 mostly holds. The word mechanism works with the model unloaded and stays read-only. But `waits` exists only where a line is typed, and `explain waits` only works through the arrow. Claim 5 partly holds: the destination cues describe the arrow, not Enter, and the cited desk document is out of date. The pieces for "open the line, add a filter, see the list change, name your version" exist in separate places but are not joined up.

**Before anything else: the working tree, as it stands, refuses every staC line and every `words.keep`.** Run against `/home/user/Struthio`, the seed reads `"state": "STALE"`, with 17 bound sources changed (shell2.py, typebar_qt.py and others carry uncommitted 0.8.0 edits). `words.keep` then answers `That is not a staC line I can keep: Graphite seed/source binding is not current`, and `language.run` refuses for the same reason. The checks are in stac_words.py:83-85, stacy_language.py:9-13, :54 and :108, and the rebuild note is at stacy_foundation.py:44. All the checks below therefore ran on an export of HEAD 3d284ac, where the seed reads `VERIFIED_SOURCE_BINDINGS`. The export was made with `git archive`, so nothing in the repository was written. The point-9 demonstration will fail at its first step on a build whose seed has not been rebuilt.

Line numbers are for HEAD 3d284ac. Another session is editing shell2.py, typebar_qt.py and context_menu.py right now; those edits only rename her (`named()`, "Kasandra") and shift lines by a few. At HEAD she is "Stacy" (shell2.py:1734).

## What I ran
All windowless, inside `unshare --pid --fork --mount-proc --kill-child …/venv/bin/python -B`, with `QT_QPA_PLATFORM=offscreen`, `ARC_LEDGER_EMBEDDED=1` and temporary HOME, config home and concern folder. Scripts are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/take_apart/`: `words_probe.py`, `words_probe2.py`, `words_probe3.py`. Output, condensed:
```
brain.status                         NO_MODEL_SELECTED
words.keep waits (A)                 Kept. "waits" now runs: field.read | pick waiting | select kind,title,state
words.list (B)                       {"words": []}
expand('waits | where kind=finding | count') -> field.read | pick waiting | select kind,title,state | where kind=finding | count   rows [{"count": 0}]
expand('explain waits') -> stac.inspect: steps read field.read / pick waiting / select [kind,title,state], executed false, model_calls 0
language.run {"text":"waits"} at the Kernel   A pipeline source must be a registered read-only Kernel operation
keep field=…    "field" already means something at the start of a line
keep mine = files.write …   not a staC line I can keep
keep w2 = waits | where kind=finding  stored written out: field.read | … | where kind=finding
fixture gaps (C1 0.49 mm … C5 0.028 in, C6 0.62 blank unit):
  gaps | where gap at least 0.5   C2,C3,C4,C6       gaps | where gap at least 0.7   C4
  gaps | where gap under 0.5 | count   2   (C1 and C5: 0.028 in is read as 0.028)
keep gaps again   replaced: true; old line gone       forget gaps -> gaps-07 still runs
Talk own_word('gaps-07')         answer_in_stac(full line)     own_word('explain gaps-07') -> False (not handled)
bar 'gaps-07': written_out = full line, hint_kind 'stac', parses_as_stac(as typed) False
matrix.list   "@files:clearance.csv | rows | select ref,gap,unit | where gap at least 0.5" SUCCESS
9-stage line   Use one source and at most seven transforms
journal        words.keep REQUEST_RECEIVED / REQUEST_COMPLETED, detail ""
```

## Claim 3: staC words (cites workbench/stac_words.py:1)
- **"word waits = field.read | pick waiting | select kind,title,state" keeps a read: HOLDS** (when the seed is current).
  - `command()` turns the typed line into `/words.keep {name, line}` (stac_words.py:123-129, which lowercases the name).
  - `keep()` checks the line with `language.parse` (82-85), stores it written out (81), and refuses reserved or taken names (35, 46-55) and a word made of itself (78-79).
  - Typed in the bar it runs through `written_out` → console Kernel page (typebar_qt.py:397-408). Typed with Enter to Stacy it runs through `own_word`, which calls the Kernel directly (shell2.py:2436-2446).
  - Caveats: keeping under an existing name silently replaces the old line, with no record of what it was (stac_words.py:91). The table holds only name, owner, line, made, updated (43).
- **`waits` runs alone: PARTLY.** It runs in the bar (typebar_qt.py:400) and in Talk (shell2.py:2447, 2456). It also runs from the "Your words ›" menu, which calls `ask(name)` (context_menu.py:1327). It does not run at the Kernel, CLI or JSONL: expansion happens only where a line is typed (RELEASE_NOTES_0.4.3.md:101; probe). Kept chains are parsed without expanding words (chain_menu.py:447). "Waits" with a capital letter is not expanded (stac_words.py:36).
- **`explain waits`: PARTLY.**
  - Through the arrow or Ctrl+Enter it works. The bar classifies it as `inspect` (typebar_qt.py:144, 664-667; arrow tip "Show this plan", 435). It goes to `stac.inspect` (stac_bridge.py:127-160) and the plan is drawn by console_qt.py:134-165.
  - Through Enter ("Ask Stacy", shell2.py:1087) it is not explained: `own_word` returns False for lines starting with `explain ` (shell2.py:2448). It then falls to the model; with no model the answer is "I have no brain running yet" (2532-2536).
  - The plan's echo cuts the line to 32 characters (console_qt.py:461), and the plan itself does not print the line (134-165).
- **`waits | where kind=finding | count` carries on: HOLDS** (stac_words.py:117-120; probe). The whole line is bound to one source plus 7 transforms (typed_pipeline.py:25). A word may be built on another word and survives the other word being forgotten (probe).
- **The word expands before it runs: HOLDS.** See typebar_qt.py:400, shell2.py:1211 (preview), 2447 (Talk) and stac_words.py:81 (keep).
- **The full line is in the result and history: PARTLY.**
  - Result: the console echoes the full line (console_qt.py:459), and her card shows it with the exact line as tooltip (shell2.py:1878-1879, card.stac 1921). The explain echo is cut (above).
  - History, per user: Up/Down history stores the expanded line (console_qt.py:340-345, 382), but in the per-user `session-r10.json` (session.py:82), not the workspace.
  - History, per workspace: the instruction matrix stores the full line (instruction_matrix.py:81-85; probe 3).
  - The journal records `words.keep` without the line (probe 3). The Talk thread is not saved, and earlier exchanges fold away after 8 (shell2.py:1817).
- **The alias belongs to the workspace: HOLDS.** Words live in `<workspace>/.ledger/engineering.sqlite3` (stac_words.py:42-43; engineering_kernel.py:344-346). Workspace B was empty after keeping in A (probe). The owner column is written but never used to filter (stac_words.py:58-62).
- **Runs with the model unloaded: HOLDS.** Every step ran with `NO_MODEL_SELECTED`. `own_word` is the first thing `ask` does (shell2.py:2486), before any model check, and inspect reports `model_calls: 0` (stac_bridge.py:159).
  - The flip side: with a model loaded, a word still gets rows only, never her own words, because `ask` returns before the grounded path (2486, 2456 versus 2507-2526).
- **Stays inside the read boundary: HOLDS.** A kept line must parse as a registered read-only operation (stacy_language.py:60-71); `files.write` was refused (probe). Keeping a word is itself an `execute` operation (stac_words.py:32). Lines starting with `this` skip the parse check at keep time (82) and are checked when they run.

## Claim 5: the shell stays a shell; the destination is visible when you press the key (cites docs/GRAPHITE_DESK.md:486)
- **The shell stays a shell: HOLDS.**
  - In Terminal every line goes to the shell (shell2.py:1003).
  - The bar only expands words in Stacy mode (typebar_qt.py:395, 659-664).
  - Typing `$` into an empty line switches to Terminal (shell2.py:1028-1032).
- **The destination is visible when you press: PARTLY.**
  - What shows today: the lit name (typebar_qt.py:282-284), the hint (94-98, 315-323), the context word "runs as staC" / "a plan to look at" / "keeps this word" (654-683), the arrow's colour and tip (432-438), and the sections of the list under the line (shell2.py:1083-1087).
  - Problem 1: the cues describe the arrow, while Enter sends to "Ask Stacy" (shell2.py:1273-1279, 1087). The two put the answer in different places: the arrow uses the working area (typebar_qt.py:427-428 → 408), Enter uses the Talk card.
  - Problem 2: for a word, the list never shows the staC section, because `parses_as_stac` is not given the expanded line (shell2.py:1083; probe: False). The context word does expand it and says "runs as staC" (typebar_qt.py:664). The two cues disagree.
  - Problem 3: nothing marks the moment of the key press itself.
- **The cited document line: DOES NOT HOLD.**
  - GRAPHITE_DESK.md:486 says "plain Enter never runs staC". Enter on one of the owner's words does run it, through Stacy (shell2.py:2486 → 1884), and so do `word NAME = …` / `forget NAME`.
  - Line 482 says "staC on Ctrl+Enter"; the code says "runs as staC" (typebar_qt.py:667).
  - The document describes four modes with "Assignment"; the code has five names with "Stacy" (typebar_qt.py:24-27).

## Her Talk card: "run, change or keep" (shell2.py:1724): PARTLY
- The card shows the exact line and offers "in the line", "watch it", "add to the Agenda", "save as a sheet" (shell2.py:1917-1920). "in the line" puts the line in Stacy mode, nothing run (context_menu.py:221-231).
- There is no run-again on the card (the console has "again", console_qt.py:474) and no "keep as a word".
- Right-click on the card opens nothing: no finder covers the Talk pane (context_menu.py:1700-1701).
- Other answer shapes: model proposals offer Run/Edit (shell2.py:2609-2645); `explain_file` offers run/watch/keep with no "in the line" (2813-2826); `execute` results offer watch/keep/save (2744-2761).

## "Open the line behind her answer, add a filter, see the list change, name your version"
- **Open the line:** exists. "in the line" on her card (above).
- **Add a filter:**
  - By typing `| where …`, which works.
  - By the chain menu, which offers where/sort/group with real column values and a row count for each choice (chain_menu.py:118-125, 169-227). It is reachable from a right-click on the console output (console_qt.py:445-451) or from the chain tray, not from her card.
- **See the list change:**
  - The new table appears in the working area, not on her card; nothing sets her list beside yours or shows the difference.
  - The live preview under the line only runs for lines that start with `@` and contain `|` (shell2.py:1049). A word therefore never previews, because the expansion pattern cannot match `@` (stac_words.py:36).
  - The chain tray previews and records the sources it read (chain_workbench_qt.py:227-255).
- **Name your version:**
  - Only by typing `word NAME = <the whole line>`. "Keep a new word…" only puts `word ` in the line (context_menu.py:1336-1337).
  - The tray's and chain menu's "keep" write a different store, a per-user `~/Concern/Ledger menu` file (chain_menu.py:331-350, 146; chain_workbench_qt.py:337-340). Words and kept chains do not know about each other.
  - A word records no parent and no versions (stac_words.py:43, 91).

## What the point-9 experiment can stand on
- A per-workspace, read-only word that runs with the model off: stac_words.py, engineering_kernel.py:627. "Your words ›" is already a per-workspace menu entry that runs with no model (context_menu.py:1320-1338, 1388, 1421).
- `this`-led words apply a kept line to the sheet selected in the Field (field_page.py:388-399).
- Her card shows the exact line, with "in the line" (shell2.py:1866-1921).
- A plan view without running (stac_bridge.py:127-160; console_qt.py:134-165).
- Filters chosen from real values with row counts (chain_menu.py:128-227).
- The chain tray: Preview with source fingerprints and seed (chain_workbench_qt.py:31-62, 227-294), and Save sheet with a receipt of program, sources, seed and "LOCAL_NO_MODEL" (306-335). This is the nearest thing to "what did this result depend on".
- The instruction matrix as a per-workspace record of every line run (instruction_matrix.py:106-135).
- The grounded "read first, then say it in her words" pattern, built for Field things (shell2.py:2504-2526).
- The fixture works as a CSV through `@files:… | rows`; the mm boundary rows come out right (probe 2).
- Other readers' areas, pointer only: checked_methods.py (`methods.*` with revisions and preview) and compare_qt.py (file and version difference).

## What is missing, piece by piece
1. **A right-click menu on her card** (Preview / Open method / Fork). Touches context_menu.py (FINDERS at 1700, a new Talk finder) and shell2.py (mark the cards so they can be found; `card.stac` is already set at 1921).
2. **Fork to a named word in one action** from her card, the console answer and the tray. Touches shell2.py:1917-1920, console_qt.py:473-474, chain_workbench_qt.py:337-345, chain_menu.py:141-148. Words and chains should be kept in one store, or the two linked: stac_words.py, chain_menu.py:336-350.
3. **Word lineage:** a parent (her line or card, and the matrix id), a revision, the previous line, a difference shown before a replace, and a `words.history`. Touches stac_words.py:43, 72-93; the registry entries in docs/GRAPHITE_0.1_REGISTRY.json:733-735; the schemas imported at engineering_cli.py:90.
4. **Her list and yours side by side, with the difference,** on the same input including the boundary rows. Touches shell2.py (the card) or chain_workbench_qt.py (two programs in the tray), possibly compare_qt.py.
5. **Live preview for any staC line and for words,** and expand before classifying in the list under the line. Touches shell2.py:1045-1053, 1083, 1201-1223; stac_words.py:36 (the pattern).
6. **Enter and the arrow should agree, or each should say where it goes,** and `explain WORD` should work in Talk. Touches shell2.py:2448, typebar_qt.py:420-438 and 654-683, and docs/GRAPHITE_DESK.md:482 and 486, which are out of date.
7. **Words outside the bar** (CLI, MCP, pinned menu entries): expand in the language itself, or store pinned entries written out with the word's name as provenance. Touches stacy_language.py:46-57, stac_words.py, chain_menu.py:447.
8. **Units and the missing-unit case in the clearance check.** staC compares bare numbers (typed_pipeline.py:178-187, 65-74): "0.028 in" counts as 0.028, a blank unit passes, and `where` on a missing column silently drops rows. This needs a unit-aware read or step: a new service module registered in engineering_kernel.py, or typed_pipeline.py.
9. **A threshold that can change without copying the whole line:** a word with a parameter, or an explicit fork that records its parent. Touches stac_words.py:114-120 and typed_pipeline.py.
10. **"Explain the result from your version" with a model:** send a word's line and rows through the grounded path. Touches shell2.py:2486, 2456 and 2507-2526; local_brain.py (`RECORDS_HINT`).
11. **A current seed on the experiment build,** or every step is refused. Touches stacy_foundation.py:531 (`build_seed`) and tools/package_graphite.py.
12. **History that belongs to the workspace:** console history is per user (session.py:82; console_qt.py:340-345), the journal does not hold the kept line, and Talk is not saved. Touches console_qt.py, activity.py, stac_words.py.
13. **Run again on her card.** Touches shell2.py:1917-1920.