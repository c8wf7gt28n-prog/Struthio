# Desk acts, test and simulation side: map and proposals

The repository's HEAD moved while I was reading: 6f60833, then bf8c12d (the REV A / REV B cut), then c401f59. Every citation below is against c401f59. Everything marked "probe" was checked offscreen on that commit, on a disposable copy of After Hours 07, with the usual holds in place. The probe scripts and their outputs are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_read/tests_side/`:

- `probe_scene_ts.py` wrote `out1.json` (the scene, mouse-style)
- `probe_kb_ts.py` wrote `out2.json` (keyboard-style, reduced motion, revision comparison)
- `probe_kb2_ts.py` wrote `out3.json` (keys for the head menus, key paths in the Field)
- `probe_menus_ts.py` wrote `out4.json` (every head menu's rows, the starting state)

## 1. Which tests build a live window today

| Module | How the window is built | Holds and timers | Size |
|---|---|---|---|
| `test_context_menu` | One window for the whole module, built in `setUpModule` (tests_integrated/test_context_menu.py:44-69) and closed in `tearDownModule` (:72-79). | Environment: `ARC_LEDGER_EMBEDDED`, `ARC_LEDGER_DISABLE_BOOK_WATCHER`, a temporary profile and Concern folder, `ARC_LEDGER_XSESSION` removed (:47-49).<br>Held before the build: `clip._request`, `Kernel.launch`, `Kernel.submit`, `session_power.system` (a fake logind), `QMessageBox.question` answered Yes (:56-59).<br>Held after the build: `subprocess.Popen`, `os.system`, `QProcess.startDetached` (:62-64).<br>Timers stopped: `ledger_bridge.timer` and `type_bar.hatch.lifecycle.timer` (:67-69); `settle()` also stops `agenda_runner` and `study_idle` (:82-88). | 1920×1200 (:65) |
| `test_system_menu` (`RealWindowLeaveTests`) | A new window for each test (tests_integrated/test_system_menu.py:292-317). | The same holds (:299-306) and the same two timers (:307). It wraps `kernel.dispatch` and the leave methods to record them (:308-312). | 1366×768 (:307) |

No other test module builds a window:

- `test_desk` and `test_frame` create no QApplication; their live-window checks are `tools/check_*_ui.py` (tests_integrated/test_desk.py:5, tests_integrated/test_frame.py:3).
- `test_graphite` patches `qt_app.main` (tests_integrated/test_graphite.py:254-257).
- `test_launcher` uses an offscreen QApplication with no window (tests_integrated/test_launcher.py:5).

**Tests that use no window but hold the Kernel.** These modules hold `Kernel.launch`, `Kernel.submit` (except for a kernel whose launch the protocol double replaced) and `clip._request`, and sometimes `stacy_foundation.seed_status`:

- tests_integrated/test_change_sets.py:41-60
- tests_integrated/test_continuing_work.py:19-38
- tests_integrated/test_project_desk.py:21-40
- tests_integrated/test_slate_reasoning.py:25-44
- tests_integrated/test_deployment.py:30-42
- tests_integrated/test_workspace_backup.py:22-34

**After Hours 07 in tests: none.** The backup is owner data and is not shipped (tools/campaign_lib/fixture.py:11-12; tests_integrated/test_campaign.py:4-5). `test_context_menu` writes its own `BENCH_CSV` (tests_integrated/test_context_menu.py:30-32). Its rows match the After Hours 07 sheet "07 Bench readings" (probe `out1.json`, `sheet.reviewed_rows`).

**How the tests reach into widgets today.**

- A real `QContextMenuEvent` sent to a widget (test_context_menu.py:91-99)
- `menu.open_child(menu.row('then'))` and `panel.choose(key)` (:823-834); `choose` is documented as "a reader's and a check's way" (workbench/context_menu.py:2747-2753)
- `cm.perform(...)` and the `host._context_last` read-back (context_menu.py:2784-2788)
- `w.console.last_program` (test_context_menu.py:835)
- A `Recorder` around `cm.dispatch` (:114-123)

The window module takes 44 tests in 58.8 s in my copy, well under the 600 s each module is allowed (tools/check_hatch.py:310).

## 2. What a new test module needs to be in the release check

1. Be `tests_integrated/test_*.py` and be named in `FOCUSED_MODULES` (tools/check_hatch.py:34-65), or else in `ON_DEMAND_MODULES` (:67-68).
   - `test_release_check` fails "a test module nothing runs" otherwise, and refuses duplicates and modules named in both lists (tests_integrated/test_release_check.py:222-229).
2. Pass on its own as `python -B -m unittest -v tests_integrated.<name>`, from the repository root, in its own child, within 600 s (check_hatch.py:310-320).
   - The child gets `QT_QPA_PLATFORM=offscreen` unless it is already set (:154-166).
   - It is never run by discovery.
   - A module that is listed but missing is ABSENT and fails the section (:314, :318).
3. Hold what the window tests hold.
   - The regex check for the three holds (tests_integrated/test_release_check.py:252-268) applies only to `tools/check_*_ui.py`, but the house rule for tests is the same (see section 1).
4. Get packaged.
   - Editing `check_hatch.py` makes the runtime section fail with `EDITED_SOURCES_NOT_YET_PACKAGED` until packaging rewrites `MANIFEST.json` (check_hatch.py:262-270; workbench/release_integrity.py:40-42).
   - The tests are shipped and listed in `MANIFEST.json` (63 `tests_integrated/` entries).
5. Re-record the registry if desk acts become Kernel operations.
   - `docs/GRAPHITE_0.1_REGISTRY.json` must be re-recorded with `tools/record_registry.py` (tools/record_registry.py:1-16; check_hatch.py:6-9).
   - A registry that lives only in Python, outside the Kernel, leaves that section untouched.
6. Know the section is already red. In my copy on c401f59:
   - `test_desk`: 6 failures
   - `test_paper`: 4 failures
   - `test_graphite`: 3 failures

   Commit 6f60833's message says "test_graphite, test_desk, test_paper fail as in 0.8.1", so `focused_tests` is FAILED before any desk-act work. A new module must be green on its own so it is not lost among those failures.

`tools/check_release.py` only runs `check_hatch.py` (tools/check_release.py:1-12). `--self-test` adds the focused set; `--ui` adds the UI gate (check_hatch.py:354-369).

## 3. The campaign (`tools/campaign.py`, `tools/campaign_lib/`)

**Commands.** `list`, `run --case/--set [--attempts --out --fixtures --mode]` and `summary` (tools/campaign.py:2-16, 34-73).

**Cases.**

| Set | Cases | Notes |
|---|---|---|
| resource | R01–R22 | tools/campaign_lib/cases_resource.py:836 onward |
| anchors | A01–A35, one per situation S01–S35 | Read from tools/campaign_lib/data/situations_35.json (cases_anchor.py:39-40, 431-448) |
| selftest | T01–T03 | runner.py:57-69 |
| real | M01–M02 | runner.py:70-82 |

Sets and selection: runner.py:39, 85-101. A case is plain data plus a function (core.py:59-90). Its revision is a SHA-256 over its data, its function's source and every file of the runner (core.py:44-56, 85-90).

**Anchor situations.** The spec asks for "One anchor per original situation … Record unavailable capabilities as Blocked" (spec.txt:68). Five anchors have steps written; each covers a stated slice of its situation:

| Anchor | Situation | Slice | Where |
|---|---|---|---|
| A01 | S01 | Trace and the exact 84/25 W check | cases_anchor.py:231-249, 376-382 |
| A16 | S16 | 280 → 300 mA, headless, scripted | :158-226, 383-402 |
| A17 | S17 | Backup verify and restore | :254-279, 403-409 |
| A27 | S27 | Resume after a kill | :284-316, 410-419 |
| A28 | S28 | Busy desk on simulated readings | :321-336, 420-427 |

The other 30 carry their needs (:341-373). `test_campaign` pins the runnable anchors to exactly {A01, A16, A17, A27, A28} (tests_integrated/test_campaign.py:263-264). The driver is recorded as `scripted` (cases_anchor.py:46).

**How a case runs.**

- The parent checks needs (needs.py:203-219), makes a fresh folder and starts `campaign.py --child` in its own process group with a clean environment (runner.py:211-218; fixture.py:45-58). It kills the child at its budget (runner.py:198-209, 233-236).
- A resume case is killed at its declared checkpoint and run again (runner.py:220-232, 263-265).
- The child seeds the workspace, calls `case.fn(ctx)`, then scores (runner.py:106-156).
- `ctx.observe` and `ctx.progress` write durable lines with a monotonic `t` (core.py:121-138).
- Checks use `matches`: equality, `contains`, `startswith`, `in`, `decimal`, `gte`, `lte`, `between`, `not` (core.py:192-215).

**Outcomes.** Pass; "Pass (current code; the spec asks otherwise)"; Partial; Blocked; Fail; Timeout (core.py:18-20, 35-36, 218-241). The report groups by set (report.py:101-107).

**Fixture workspace.**

- `base`: an empty Office built by Graphite (fixture.py:84-94).
- `after_hours_07`: the backup, verified and restored with `workspace_backup` (fixture.py:97-108).
- The backup is found under `--fixtures` as a `Graphite_Backup` folder or a zip (fixture.py:123-168).
- Known After Hours 07 ids are in `AH07_IDS` (fixture.py:28-35).
- Here the backup is at `scratchpad/x/Graphite_After_Hours_07/After_Hours_07/Graphite_Backup`, which the `*/After_Hours_07/Graphite_Backup` glob finds (fixture.py:137).

**Can it run a window offscreen?** Not today: no case builds a window. It could:

- The child already runs with `QT_QPA_PLATFORM=offscreen` and no `DISPLAY`, since `KEEP_ENV` drops it (fixture.py:36, 57).
- The child uses the parent's interpreter, so PySide6 is present when the run starts from the project venv (runner.py:217).
- Killing the process group ends Qt cleanly.
- A window case adds no needs: the `desktop` need tests for a real display (needs.py:155-160) and does not apply offscreen.

## 4. The probe harness (`scratchpad/tools/field/nomodel.py`)

**Arguments.** PROGRAM (a source tree), OUT (where captures go), width and height, and an optional `empty` (nomodel.py:8).

**How After Hours 07 gets into a run.**

- It is not restored from the backup. The harness copies a folder that was already restored, `scratchpad/work/demo/After_Hours_07` and `After_Hours_07-profile`, into a fresh `tools/field/run/run-*` (:9-11).
- It writes a one-screen `screen.json` (:12-13).
- It sets HOME, profile, Concern and `ARC_LEDGER_WORKSPACE` to the copy (:14-17).
- With `empty`, it uses a fresh Office under HOME instead (:30-31).
- That workspace's Files folder holds `.trash`, `.versions`, `Egress` and `Slate`, and no CSV (probe `out1.json`).

**REHEARSAL variables.**

- `REHEARSAL_MODEL` is required (:52) although nomodel never uses it. The 0.8.1 driver passes `x` (scratchpad/work/run_probes_081.sh:6).
- `REHEARSAL_SCRIPT` is `exec`'d with these globals in scope: `w`, `app`, `settle`, `align`, `save`, `where`, `call`, `wait_job`, `k`, `p`, `OUT`, `tag` (:34-67).
- `REHEARSAL_CONTEXT` exists only in `model.py` (model.py:72).
- `GRAPHITE_APPEARANCE` selects Kasandra (run_probes_081.sh:6; workbench/boss_theme.py:88-91).

**Holds.** Only `clip._request`, `session_power.system` and `QMessageBox.question` answered No (:26-28). `Kernel.launch`, `Kernel.submit` and `Popen` are not held, which the tests do hold.

**Housekeeping.** Run folders are never removed: 1,520 so far. The 0.8.1 driver ran it against /home/user/Struthio without `unshare` (run_probes_081.sh:6).

**What it reads back.** `where()` prints the centre widget, whether the Field or home is active, the window title and the current tab (:46-48). That is the closest thing today to "read back what is open".

## 5. Read-backs verified offscreen (the basis for the first scene)

| Item | Read-back |
|---|---|
| Starting state | Field off, home off, centre `QSplitter`; dial `show` (`out4.json`; stacy_hand.py:32, 129-132) |
| Head words | Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide (`out1.json`; shell2.py:647-669) |
| Tools rows | Explore capabilities…, Inquiries…, Algorithm && Theory Atlas…, Tool Atlas…, System Check, STOP / KILL all Graphite operations…, Engineering |
| Field and Files rows | Under Arrange (`out4.json`); the Field action's key is F9 (menus2.py:184-190) |
| Opening a head word | Mouse click or Tab + Space opens the QMenu (`out3.json`). Both go through `QToolButton` InstantPopup (shell2.py:658), which enters a nested `QMenu.exec`; the probe needed a timer to close it. Alt+T and F10 open nothing (`out2.json`, `out3.json`). |
| CSV right-click | First keys: open, ask, rename, trash, then, more |
| Then | `@files:07 Bench readings.csv \| rows`, "4 rows · 6 steps left"; after `where unit=mA`, "2 rows · 5 steps left"; after Count, `… \| where unit=mA \| count` with preview `[{'count': 2}]` |
| End: put it in the writing line | The writing line holds exactly that line; `_context_last.ok` is true (`out1.json`, `out2.json`) |
| Keyboard, Files | Menu key → focus on `open`; Down×4 to `then`, Right; Down×2 to `step:where`, Right; Down×4 to `field:unit`, Right; Down×2 to `where unit=mA`, Return; Down×4 to `step:count`, Return; Down×6 to `end:line`, Return (`out2.json`). Right after Right opens a child, the focused widget can read as none, so each key has to find the focus again. |
| Keyboard, Field | Home selects "What stretched the startup pulse?". Left×3 reaches 07 Bench readings; Left×3 then Down×2 reaches Rev B (`out3.json`). Left and Right follow a wire when there is one (field_qt.py:518-519). T traces (:567-569). |
| Trace on 07 Bench readings | 3 wires, 2 hops, ends "07 Settled power · 3.36 W" and "07 Startup power · 7.8 W" (`out1.json`; field_qt.py:1306-1317) |
| Reduced motion | `ledger.settings.set reading.reduce_motion true`, then `ledger_bridge.sync_profile(force=True)`, which is needed because the tests stop the bridge's tick (control_qt.py:287-327). Afterwards `menu_catch.calm` is true, the Field's `still()` is true, the Trace's `at` is None with no surge timer (`out2.json`; menu_catch.py:30-43, 112-115; field_page.py:50-54). |
| Rev B › More › Compare with Rev A | The `field:revisions` row is under More, reached by Down×3 (context_menu.py:1438-1442) |
| Comparison result | REV A "07 Limits Rev A ARCHIVED" against REV B "07 Limits Rev B CURRENT". Pulse duration: value 120 → 80 ms. Pulse ceiling: condition "Up to 120 ms" → "Up to 80 ms". Esc closes it (`out2.json`; field_page.py:691-752). |
| Gap in "what is open" | `ledger.desktop_context` said `workspace: FilesTab` while the Field was showing, because it reads `tabs.currentWidget()` (control_qt.py:446-449; `out2.json`). |

## (a) Proposed scene format and one runner

**Format** (JSON, so it can sit in a campaign Case and be part of its revision, core.py:85-90):

```json
{"schema":"graphite.scene/1","id":"P01","title":"After Hours 07, the playable scene","seed":"after_hours_07",
 "given":{"size":[1920,1200],"appearance":"graphite","reduce_motion":false,"dial":"show"},
 "runs":[{"style":"mouse"},{"style":"keys"},{"style":"mouse","reduce_motion":true},{"style":"keys","appearance":"kasandra"}],
 "answers":{},
 "steps":[{"act":"head.open","args":{"menu":"Tools"},"expect":{"popup.title":"Tools","popup.rows":{"contains":"System Check"}}}, "..."]}
```

- **`act`** is a desk-act name from the registry. Its mark is "navigates" or "changes".
- **`args`** follow the act's schema.
- **`style`** picks the act's mouse form (clicks at a widget's real point; a real `QContextMenuEvent`) or its keys form (keys sent to the focused widget).
- **`expect`** maps a path in the read-back to a value or to one of the campaign's matchers (core.py:192-215). Tests, probes and the campaign then score the same way.
- **`expect_by_seed`** overrides values for a test seed.
- **`answers`** declares every ask the scene will meet. The runner patches `QMessageBox.question` and the stage card's Approve to record and answer them. An ask that is not declared fails the step, so "what always asks still asks" shows.

**The read-back act (`desk.read`) returns:**

- surface: home, Field or workspace, and the centre widget (as `nomodel.where()` does)
- Field: face, selected id and title, `route` (owner, hops, ends, whether it is animating), `revisions` (a, b, changed rows)
- the open popup: kind, title, rows or first keys, focused key
- the line panel: line and count
- the writing line: text and target
- the last status words (`host._context_said`, context_menu.py:158-165)
- the hand: dial, latest trail entry and its Undo (stacy_hand.py:241-254)
- motion: calm and still
- appearance, size and zoom

It must read the Field from the centre stack, not from `tabs.currentWidget()` (see the gap in section 5).

**One runner: `run_scene(window, scene, run, observe=None, capture=None)`.** Proposed home: a shipped module such as `workbench/desk_scene.py`, beside the registry.

- For each step it runs the act's form for the chosen style, settles, takes the read-back, and scores each expected value with `core.matches`.
- A "navigates" act is also checked to have changed no record, using the before and after of `fixture.state_digest` (fixture.py:111-118), less the settings and activity tables. That is my suggestion and unverified: those two tables may move on a read.
- A "changes" act goes through `w.shell2.face.stage(title, Step(...), asked=True)` (shell2.py:3177, 1994-2079). That gives its card, a trail entry and its Undo. For `files.write` the Undo is `/files.trash {"path": …}`, guarded by the file's SHA-256 (stacy_hand.py:193-215).
- An act that opens a nested event loop (a head word's InstantPopup, any `exec` dialog) schedules the read-back and the next step with `QTimer.singleShot` before sending its input. The probe proves this pattern.

**Three adapters over the one runner:**

- **Test.** `tests_integrated/test_desk_scenes.py` uses the `test_context_menu` fixture: same environment, holds and timers.
  - Seed "bench": built through Graphite's own operations. `files.write` makes the CSV (files_service.py:55, 524). `office.import.preview` and `office.import.commit` run directly, with no job (office_service.py:149-151). They can make two sheets titled "07 Limits Rev A ARCHIVED" and "07 Limits Rev B CURRENT"; the comparison reads cells when a sheet has no reviewed rows (field_page.py:709-727).
  - Trace on an unwired sheet gives 0 hops, ends = itself (field_qt.py:1304-1305), so the test carries `expect_by_seed.bench`.
  - Add it to `FOCUSED_MODULES` (section 2).
- **Probe.** A `REHEARSAL_SCRIPT` body (for example `scene_probe.py`) that loads the scene, calls `run_scene(w, …)`, prints JSON and `save()`s a capture per step. Run it under `unshare`. Suggested fixes to nomodel: hold `Kernel.launch`, `Kernel.submit` and `Popen`, and stop requiring `REHEARSAL_MODEL`.
- **Campaign.** A new `scenes` set: `cases_scene.py`, added to `SETS`, `select` and `registry` (runner.py:39, 85-101).
  - Each case: `seed='after_hours_07'`, `needs=['after_hours_07']`, `inputs={'scene': …, 'run': …}`, `expect` flattened to `"<n>:<key>"`, and an `fn` that builds the window in the child.
  - It holds the tests' calls plus `_guard_launch` (cases_anchor.py:61-66), writes `ctx.progress` per act (that is the spec's "UI presentation" timeline, spec.txt:105), and saves a capture into the attempt folder (spec.txt:61).
  - Keeping scenes out of the anchors leaves `test_campaign`'s pinned list untouched. Scene files under `tools/campaign_lib/data/scenes/` fall inside the library digest (core.py:44-56).

## (b) The first scene: P01, the owner's "playable scene" in After Hours 07

Starting conditions: the restored workspace, 1920×1200, dial "Do and show".

Two of these are run parameters, not acts:

- **The appearance** is chosen at start. Changing it in the window relaunches Graphite (boss_theme.py:25, 88-91; boss_qt.py:419).
- **Reduced motion** goes through `ledger.settings.set`, which is not on her "Do and show" list (stacy_hand.py:39-40). Through her hand it would wait for Approve, so the scene sets it as `given` or through the owner's door.

| # | Act (mark) | Mouse | Keys | Expected read-back |
|---|---|---|---|---|
| 1 | `head.open` Tools (navigates) | Click the head word | Tab to the word, Space | `popup.title` = Tools; rows contain "System Check"; no "Programs" |
| 2 | `popup.close` | Click outside | Esc | No popup |
| 3 | `files.write` "07 Bench readings.csv" (changes, through her hand) | The text is the sheet's reviewed rows (`office.get`, a read) | Same | Card ran; trail Undo = `/files.trash {"path": "07 Bench readings.csv"}`; address `@files:07 Bench readings.csv` |
| 4 | `view.open` Files (navigates) | Arrange › Files | Same through the menu by keys | Current tab is FilesTab; the CSV is listed |
| 5 | `menu.open` on the CSV (navigates) | Right-click its row | Row focused, Menu key | First keys: open, ask, rename, trash, then, more; Then's line is `@files:07 Bench readings.csv \| rows` |
| 6 | `menu.choose` then | Click | Down×4, Right | Panel: "4 rows · 6 steps left" |
| 7 | Keep rows where unit is mA | where › unit › `where unit=mA` | Down×2 Right; Down×4 Right; Down×2 Return | "2 rows · 5 steps left"; that row's caption "2 rows"; nothing read again (test_context_menu.py:831) |
| 8 | Count | `step:count` | Down×4, Return | Line `… \| where unit=mA \| count`; preview `[{count: 2}]` |
| 9 | Put it in the writing line | `end:line` | Down×6, Return | The writing line holds that line; menus closed; `_context_last.ok` |
| 10 | `view.open` Field | Arrange › Field | F9 (the key works; it is never printed) | Field active, face "work", 14 tiles |
| 11 | `field.select` 07 Bench readings | Click its tile (`sheet_rect`, field_qt.py:590-596) | Home, then a searched arrow path (Left×3 today) | Selected = `office:owner:db5f669f863d4c71b89fa7ba348957da` |
| 12 | `field.trace` | More › Trace it › The whole trace (context_menu.py:1318-1332, 1432) | T | `route.owner` = that id; 2 hops; ends Settled power 3.36 W and Startup power 7.8 W; animating unless reduced motion |
| 13 | `field.select` Rev B, then Compare with Rev A | Click the tile, right-click › More › Compare with Rev A | Home Left×3 Down×2; Menu key, Down to More, Right, Down×3, Return | REV A / REV B; changed: Pulse duration 120 → 80 ms, Pulse ceiling "Up to 120 ms" → "Up to 80 ms" |
| 14 | `field.close_revisions` | Click beside it | Esc | `revisions` is None |
| 15 | `hand.undo` the CSV (optional; leaves the workspace as found) | Click Undo on the card | Same | Trail entry is "undone"; the CSV is in the Trash |

**Records that support a comparison.**

- **Supports one:** the reviewed sheets `office:owner:5a43beee28224c4e818af7b985cdb535` ("07 Limits Rev A ARCHIVED") and `office:owner:4f357ff3c843489a9758db71e23bf4b4` ("07 Limits Rev B CURRENT"). Their sources are `07_Rail_Limits_Rev_A.pdf` and `07_Rail_Limits_Rev_B.pdf`, and the finding "Rev A allowed 120 ms. Rev B allows 80 ms." corroborates them (`out1.json`).
- **Does not:**
  - 07 Bench readings has no sibling revision.
  - The Files CSV has none either: Files only compares names that are revisions of one file (context_menu.py:205-210, 685-697).

**Variants.**

- **Reduced motion:** steps 1, 5 and 9 open and land with no catch or flash; step 12 has `animating` false.
- **Kasandra:** the same expected values, plus her name where it is shown.

## (c) Anchor situations that could become scenes next

| Situation | Title | Scene | Model? |
|---|---|---|---|
| S01 | Engineering feasibility | Field › 07 Settled power › Trace to 07_Bench_Readings.pdf; open the source at its row; back to the same tile. Read-backs as in A01 (84/25 W). | No |
| S16 | Product redesign after constraints change | The spec's mouse run (spec.txt:43-45), driver scripted. Open 07 Bench readings; set 280 → 300 mA (`field.set`, hers). The recheck card waits (`office.datasheet.recheck` is only on her Free-hand list, stacy_hand.py:41); Approve by mouse. Read back: finding "recheck", source still 280 mA, back to the same tile. | Scripted now; "let Stacy choose" needs the model |
| S27 | Crash recovery with an uncertain external action | Kill after the cell write (campaign resume), reopen the window, read back the revision, the trail and the Undo. | No |
| S28 | Demanding work on a responsive ThinkPad | The owner's foreground clicks and edits as acts while sim readings run a background job (as A28; spec.txt:37). | Sim now; real responsiveness on the ThinkPad |
| S17 | Recovery from conflicting backups | Partial only: open the restored workspace and read back the desk. Restoring is not a window act. | No |

Spec variations with no anchor number that also fit: "Source read" (spec.txt:49-50), "Tool failure" by injecting a failed read the way the Recorder answers do (test_context_menu.py:114-123), and "Owner takes over" (spec.txt:57-58).

These cannot be offscreen scenes:

- **Native applications:** S03, S10, S11, S19, S20, S31–S35 (cases_anchor.py:343-372)
- **Network:** S12, S14, S21, S33

## Needs a real model, so waits for the ThinkPad

- **Door 1:** offering the acts to her model is later, by the owner's decision. Until then the runner's driver stays scripted (cases_anchor.py:46).
- **Stacy choosing from words:** S16's "Let Stacy choose the relevant operations" (spec.txt:44), the clarification of an "Ambiguous request" (spec.txt:53-54), and the actions the model selects in the 35B run (spec.txt:14).
- **Anchors whose needs include the model:** S02, S04, S05, S06, S07, S08, S13, S15, S22, S23, S26, S29, S30. S06 and S22 also need the ThinkPad itself (cases_anchor.py:341-372; needs.py:150-153).
- **Measurements:** responsiveness while the owner works, time to first reply, Radeon offload and peak RAM (spec.txt:15-16, 105-106).
- **Real mode:** today it only checks prerequisites and prints its plan (runner.py:392-468).

Without a model, "Ask Stacy about this" answers from the records (context_menu.py:1451), so a scene can use it without waiting.