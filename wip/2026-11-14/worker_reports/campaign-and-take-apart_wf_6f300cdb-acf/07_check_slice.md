# Experiment 9 slice: where it breaks against the code

I checked the slice against commit **34f00ba**. Line numbers below are at that commit unless marked HEAD. I wrote nothing to the repository. Two probes ran against a scratch workspace: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/take_apart/probe.py` and `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/take_apart/probe2.py`.

## 0. The code has moved since 34f00ba

- **HEAD is now 1645caa, not 34f00ba.** The other session committed 48d889b and 1645caa after the slice was written.
- **shell2.py lines have shifted by 12 to 32:**
  - `stage` 1948 → 1980
  - Approve tooltip 1977 → 2009
  - the hook point in `ask` 2500 → 2532
  - the grounded pattern 2526-2539 → 2558-2571
  - `program_detail` 1679 → 1691
  - the twin tooltip 2362 → 2394
- **context_menu.py:1338 already has no printed key at HEAD.**
- **The owner has a new rule** (RECORD_OF_DIRECTIONS, 48d889b): nothing shown in the window may name the language. The slice's visible text complies. The explain prompt must keep calling a line "a line".
- **What did not move:** the context_menu.py lines (:231, :1442, :1701, :1708), the engineering_kernel.py lines (:58, :227, :627) and the engineering_cli.py lines (:90, :186). Rebase onto HEAD before editing.

## 1. Steps that would not work as written

1. **Her rule cannot find the CSV that the tests name** (pieces 5 and 8).
   - The rule accepts only a `files:`/`@files:` path in the text, or `face.selected_file()`.
   - The tests type a bare path: `'check the clearances in SLIM4/clearance.csv'`.
   - `selected_file()` is `tab.slate_file()`, which is `None` unless one file is selected in Files (files_qt.py:138-140).
   - So both tests fall through to the no-method path or the model path. The rule needs to accept a bare relative `*.csv` path that resolves under Files.

2. **Piece 8's list of dispatched operations is wrong.**
   - `desk.sources.read` dispatches `files.get` itself: project_desk.py:454 calls `addresses.read`, which dispatches at addresses.py:95. The probe observed `['desk.sources.read','files.get']`.
   - `tools.pins` also reads each pin's header through `desk.sources.read`.
   - The real set is `tools.pins, desk.sources.read, files.get, clearance.check`, with the last three dispatched twice.

3. **"check writes nothing beyond the Kernel's existing request journal entry" is false.**
   - Each check makes three journaled requests (engineering_kernel.py:513, :526).
   - `tools.pins` runs on every right-click of a table in Files, and its header reads are journaled too.
   - The precedent puts view reads in `activity.OBSERVER_OPERATIONS` (activity.py:8, documents.py:54). The slice never touches activity.py.

4. **Adding to `SEED_FILES` breaks tests before the rebuild.**
   - A changed input set makes `seed_status` raise "Seed input set … differs" (stacy_foundation.py:371-372), which returns state `INVALID` (:398).
   - The test holds only map `STALE` and `SOURCE_UNAVAILABLE` to verified (test_project_desk.py:37).
   - So `language.run` refuses. That fails the piece 1 "why the method exists" test and the existing `assignments.plan` tests until the rebuild. "Rebuild last" only works if the `SEED_FILES` edit lands in the same step.
   - `--rebuild-seed` followed by `--manifest-only` runs the rebuild twice, because `--manifest-only` already calls `rebuild()` (package_graphite.py:4, :189-191).

5. **The talk tests share one window and one workspace per module** (test_context_menu.py:31-53).
   - The fixture refuses if `SLIM4/clearance.csv` exists, so it can run once per module. Step 1 of `test_the_experiment` collides with the piece 5–8 tests.
   - Piece 6's run-again test writes C3 = 0.71. After that, piece 8's expected "FAIL C3" becomes PASS.
   - The fixture must use `operator()` (identity `desktop-owner`, engineering_kernel.py:299). Records are per owner (project_desk.py:113-114), and the window uses `operator()`. The desk tests use `operator('owner')`.

6. **The tampering test depends on a read path the slice does not specify.**
   - If `check` loads the current revision from `desk_records` through `project_desk.read`, an edited `desk_history` row is never seen.
   - Reading history also needs an owner check. `desk_history` has no owner column (project_desk.py:88). `checked_methods` reads the record first and then compares owners (checked_methods.py:180-185).

7. **Piece 9 contradicts itself.** The facts include "plus the input's sha and the row reasons". The model-off test says the card is "exactly the first line and the four facts".

8. **The printed-key regex would not catch the key the slice removes.**
   - `Ctrl|Shift\+|Alt\+|Enter|Return|F10` does not match "in the Field, G does the same" (shell2.py:1977). It also misses Esc, Backspace and single letters.
   - The "still to fix" list is wrong:
     - :1338 is already fixed at HEAD.
     - It misses `caption='Shift+Enter'` (:1406), "Ctrl Z" in said text (:353, :378) and `Ctrl Shift N` (:829).
     - :2362 is the same tooltip string as :1977, so fix both.

9. **Verbatim text assertions will fail.** `breakable()` (shell2.py:1674, used by `Bubble` at :1697) puts U+200B after 18 characters without a space.
   - `SLIM4/clearance.csv` is 19 characters and becomes `SLIM4/clearance.cs\u200bv`.
   - This breaks the glance line, the fork footer and "…changed since the last run" unless the test strips U+200B. No existing test does.

10. **context_menu.py needs two `PROVIDERS` entries, not one:** `result_entries` (piece 6) and `pinned_entries` (piece 8).

11. **Fixture arguments are missing.** `projects.create` also needs `intent` (project_desk.py:43). `projects.link` needs `expected_revision: 1` and `role` (:45-47).

## 2. Where it breaks the owner's rules

- **Undo:**
  - Her pin, approved in step 6, cannot be taken back from the interface. `run_staged` adds a trail entry or Undo only when `card.hers` is set (shell2.py:2018), and `asked=False` means it never is.
  - Piece 8's Tools submenu has no Unpin row. Unpin appears only on the owner's own right-click pin.
  - Fix: give `stage()` a `done` callback that adds Unpin, or add an Unpin row to the submenu.
  - "Forks have no Undo, and this is said": no card text says it. The "There is no exact Undo" line (:2031) only appears for her own acts.

- **Nothing silently applied:**
  - **The hook runs too early and matches too much.** It runs before `start_asked`, `made_asked`, `set_asked` and `run_asked` (shell2.py:2501-2504). With a CSV selected in Files, "make a file called clearance-notes.txt …" or "what is the clearance on C3?" becomes a check, or a "no method" answer. The owner's request is silently not done and the model is never asked.
  - The explain rule ("explain" plus result, clearance or check) also takes requests it should not, such as `explain` of a word named "check".
  - **The pin's recorded `digest` is never checked.** `clearance.check` takes `{method, revision, source}`, so a history row rewritten consistently (its digest is just a hash of the payload, project_desk.py:130) would run silently. Add an expected digest to `clearance.check`.
  - **Run again** on an older revision says the source changed, but nothing says the method has a newer revision.
  - **Her request and the menu stop matching after a revise.** Her request runs the current revision and the menu runs the pinned one.

- **Allow-list:** this holds, since `stacy_hand.py` is unchanged and nothing new is hers. One nuance: "she reaches it by rule only" is not quite true. The provider planner offers every read and execute operation (stacy_control.py:305). The five changing operations become proposable by a provider model, which also chooses `origin`. Proposals are still reviewed.

## 3. Larger than it needs to be

- **Revise, diff, parent state, newer revision, the difference card and repin** (pieces 2, 3 and 8): none of the eight experiment steps uses them.
  - If they stay, `clearance.diff` need not be a registered operation. It duplicates `get`'s `parent_change` and `pins`' `difference`.
  - `tools.pin`'s re-point mode only exists for repin.
- **`project` plus `folder`:** no piece reads the project or its link. Everything keys on the folder. Drop `projects.create`, `projects.link` and `project`.
- **The `SEED_FILES` addition:**
  - `SEED_FILES` has not changed since 0.3.1.
  - stac_words.py, field_service.py, stacy_hand.py, checked_methods.py and context_menu.py are not seed inputs.
  - Adding the new modules widens the fragility the slice itself warns about.
- **Inspect's seed state:** it is not recorded in the result, only read when Inspect opens, so it describes today's seed, not the run.
- **Smaller extras:** `minimum_unit` (only mm is defined), `units_digest` (the record digest already covers units), a new `CLEARANCE_METHOD_HISTORY_DAMAGED` where `PROJECT_DESK_HISTORY_DAMAGED` exists (project_desk.py:287), and a fifth meaning of "Inspect".
- **The `tools.*` namespace** for a clearance-only pin: "tools" already means job tools in the Kernel. `clearance.pin`, `clearance.pins` and `clearance.unpin` would be clearer.

## 4. Smaller gaps in the spec

- **Fork semantics are ambiguous.** "The original at expected_revision" (a history read) conflicts with "a stale expected_revision is refused". `REVISION_CHANGED` is the wrong word for a revision that does not exist yet.
- **`judge` edge cases:**
  - `re.match` with `$` accepts `'0.49\n'` and Unicode digits (`'٠.٥'` gives Decimal 0.5). Use `re.fullmatch(r'-?[0-9]+(\.[0-9]+)?')`.
  - An Excel BOM (`\ufeffRef`) gives a false `COLUMNS_MISSING`.
  - A short row (`C7,0.5`) gives an index error unless handled.
  - Unit case (`MM`, `In`) is unspecified.
- **Pins:**
  - "Folder contains the path" must compare path parts, so `SLIM4` does not match `SLIM40/…`.
  - `tools.pins {project}` without a path has no table to test compatibility against.
  - The owner's pin and her pin can duplicate the same label.
  - The pin label conflicts: piece 7 proposes `Enclosure clearance 0.70`, while piece 8 expects the row `Check enclosure clearance`.
- **Counts:** in the all-fail case the counts dict has no `PASS` key.
- **Explain with the model on:** it must check `face.job` itself, because the hook runs before the "still answering" guard (shell2.py:2512).

## 5. What holds

- **The fixture constants are exact.** These were verified with a real `files.write` and `desk.sources.read`:
  - 84 bytes
  - sha256 `5a1262c7…5074df`
  - content_revision `c31802b1…59f95e4`
  - units digest `77aebfa5…54d0e`
- **Every verdict is right.** I recomputed them with Decimal:
  - At 0.50: 4 pass, 1 fail, 1 unit missing.
  - At 0.70: 2 pass, 3 fail, 1 unit missing. The rows that change are `['C2','C3']`.
  - At 0.55: C1 and C2 fail; C3, C4 and C5 pass.
  - At 0.75: C1 to C5 fail.
  - C3 = 0.71 passes at 0.70.
  - C5's mm value is exactly `'0.7112'`.
- **The staC comparison** `language.run` returns C1, C2, C3, C5 and C6.
- **Byte handling:** `files.get` turns cells into floats (files_service.py:257-265). `desk.sources.read` judges the same bytes it hashes. The 128 KiB bound matches `exact_bytes_base64`.
- **The Kernel and CLI insertion points are correct.** No `clearance.*` or `tools.*` operations exist among the 771. `handler_map` picks up the new module for the registry.
- **The `stacy_hand` claims hold:**
  - A read is hers (:154).
  - `tools.pin` is on no list (:39-43).
  - No `ALWAYS_ASKS` pattern matches any of the new operations.
  - The registry test will cover the 5 new changing operations and still pass.
- **The staging and menu mechanics hold:**
  - `stage(asked=False)` waits at every dial place (:1964).
  - `Step` and `op` match field_do.py:26-36.
  - Finders are tried before `owns_menu` stops the walk at selectable labels (:1708).
- **The hook position holds.** It runs before `brain.status` is read (:2516), and `own_word` passes `explain …` lines through (:2462).
- **The seed facts hold.** There are 485 seed inputs, and the five named files are among them. The seed is verified at both 34f00ba and HEAD.
- **The other citations are correct:** menus2.py:275, local_brain.py:521, and the "claims" spot-checks (words.keep keeps no old line, stac_words.py:91-93; `field.*` came in 0.4.1).