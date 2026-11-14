The pass is built and committed. All 40 desk acts run on the live window, and the first scene (P01) passes by mouse, by keys, and both with reduced motion. That holds on the bench seed in the tests and on the real After Hours 07 backup through the campaign. Every module I touched passes before and after, and the release check passes in every section.

- **Worktree:** `/home/user/Struthio/.claude/worktrees/wf_ffffb167-845-5`
- **Branch:** `worktree-wf_ffffb167-845-5`
- **Commit:** `a897af3193ce20d43c8ca5baf68ae94b7ded8fd3`, on top of 1f59293. Not pushed.
- **Mirror:** every committed file, generated ones included, is copied under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_acts_mirror/`.

## Acts built (40)

**Changes (7):**
- Through Stacy's hand on a Kernel line: `hand.write` (files.write), `hand.rename` (files.rename), `hand.trash` (files.trash), `hand.cell` (field.set).
- `hand.step`: the step's own line decides what it does.
- Owner-only: `hand.approve`, `hand.undo`, `hand.dial` and `look.set` (the plan files `hand.approve` under changes because of its name, though it changes nothing itself).

**Navigates (33):**
- go: `go.field`, `go.today`, `go.files`, `go.open`, `go.app`, `go.back`, `go.pane`
- point: `point.sheet`, `point.move`, `point.zoom`
- head: `head.open`, `head.row`, `head.meter`
- menu: `menu.open`, `menu.choose`, `menu.close`
- then: `then.keep`, `then.count`, `then.back`, `then.end`
- sheet: `sheet.trace`, `sheet.doubt`, `sheet.compare`, `sheet.close`, `sheet.whatif`, `sheet.steps`
- type: `type.to`, `type.put`, `type.room`, and `type.send` (owner-only)
- read: `read.desk`

35 acts are exported for her model later; nothing offers them to the model now. `door='her'` is refused.

New files: `workbench/desk_acts.py`, `workbench/desk_doers.py`, `workbench/desk_scene.py`, `tools/campaign_lib/cases_scene.py`, `tools/campaign_lib/data/scenes/P01.json`, `tests_integrated/test_desk_acts.py`, `tests_integrated/test_desk_scenes.py`.

Changed files:
- `workbench/console_qt.py`: acts typed in the writing line run; `help`, `help acts`, `ops` and Tab completion know them.
- `workbench/shell2.py`: a row word "Act" for an act line; the command search no longer prints a key; `card.reply = r`.
- `tools/campaign_lib/runner.py` and `tools/campaign.py`: the new `scenes` set.
- `tools/check_hatch.py`: both new test modules added to the focused set.
- Rebuilt: `MANIFEST.json` and `project/stacy_seed/current/*`, by `--manifest-only`, then `record_registry`, then `--manifest-only` again. The registry file came out unchanged, so there was nothing to stage for it.

Checks: the seed reads `VERIFIED_SOURCE_BINDINGS`, `release_integrity.verify` reads `VERIFIED`, and `tools/check_release.py` passed runtime, registry, settings, adapters and payload_privacy.

## Tests

Each module was run on its own with `cd <worktree> && QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child …/venv/bin/python -B -m unittest tests_integrated.<module>`.

| Module | Before (HEAD) | After |
|---|---|---|
| test_desk_acts | (new) | Ran 20, OK |
| test_desk_scenes | (new) | Ran 3, OK |
| test_stacy_hand | Ran 19, OK | Ran 19, OK |
| test_writing_line | Ran 31, OK | Ran 31, OK |
| test_kasandra | Ran 20, OK | Ran 20, OK |
| test_release_check | Ran 22, OK | Ran 22, OK |
| test_campaign | Ran 23, OK | Ran 23, OK |
| test_tool_selection | Ran 5, OK | Ran 5, OK |
| test_context_menu | Ran 44, OK | Ran 44, OK |

Campaign: `tools/campaign.py run --set scenes` with the After Hours 07 backup gave Pass 4 of 4 (P01a 54/54 checks, P01b 55/55, P01c 56/56, P01d 57/57).

## The scene on After Hours 07

| # | Act | What it read back (all four runs unless noted) |
|---|---|---|
| 1 | head.open Tools | 6 rows including "System Check", no "Programs"; `keyboard_route: false`. Mouse runs leave the menu open; keys runs read it and close it. |
| 2 | menu.close | Mouse closed `head:Tools`; keys: nothing was open. |
| 3 | hand.write | `ran: true`, `hers: true`, `undo: /files.trash {"path": "07 Bench readings.csv"}`; her trail's line starts with `/files.write`. |
| 4 | go.files list | Workspace in front; the CSV is listed. |
| 5 | menu.open file | First keys `[open, ask, rename, trash, then, more]`; Then carries `@files:07 Bench readings.csv \| rows`. Reduced-motion runs: calm is true. |
| 6 | menu.choose then | Panel reads "4 rows · 6 steps left" (keys: 5 presses). |
| 7 | then.keep unit / is mA | "2 rows · 5 steps left", line `… \| where unit=mA`. |
| 8 | then.count | Line `… \| where unit=mA \| count`, preview `[{count: 2}]`, "1 row · 4 steps left". |
| 9 | then.end line | The writing line holds that line, goes to her, the menu is closed, outcome ok. |
| 10 | go.field | Field in front, work face (keys: F9). |
| 11 | point.zoom whole | Zoom 0.8 and the whole desk in sight; no press was needed, the desk was already whole. |
| 12 | point.sheet "07 Bench readings" | Selected (keys: 3 presses). |
| 13 | sheet.trace | Owner "07 Bench readings", 2 hops, ending at "07 Settled power · 3.36 W" and "07 Startup power · 7.8 W". Animating is true in normal runs and false in reduced-motion runs. |
| 14 | point.sheet "07 Limits Rev B CURRENT" | Selected (keys: 2 presses). |
| 15 | sheet.compare | Rev A "07 Limits Rev A ARCHIVED" against Rev B "07 Limits Rev B CURRENT"; changed: Pulse ceiling, Pulse duration. |
| 16 | sheet.close | Nothing over the work; the Field is still in front. |
| 17 | hand.undo | State `undone`, trashed "07 Bench readings.csv"; the file is gone afterwards. |

On the bench seed (the tests) the read-backs are the same except trace gives 0 hops and zoom is 1.0.

## Where it differs from the plan, or is not done

- **Arrange › Cabinet left off `HEAD_ROWS`:** it is a submenu of choices, not a row that goes somewhere.
- **Export size target missed:** `plan_variants()` is 10,940 bytes, not ≤ 9,000; the 35 wrappers alone are about 4,200. The test bound is 11,000. Each schema stays ≤ 300 bytes (largest: head.row, 298).
- **`hand.step` has no fixed Kernel operation** (its step's line decides), so test 1 accepts it as a change act.
- **Smaller test changes:**
  - Two checks on one path in P01 use a `#label` suffix, because JSON keeps one value per key.
  - The never-changes check ignores the journal tables, the `audit` table, and tables a read creates empty. The Files and Library reads created `copies*` and `receiving_deliveries` that way.
  - The test fixture answers `QMessageBox.question` with No rather than test_context_menu's Yes.
- **Forms that fall back or differ:**
  - head.open by keys focuses the word in code and presses Space, since no keyboard route exists.
  - point.zoom by pointer clicks the size strip only when it is drawn; otherwise it uses keys and reports `by: keys`.
  - sheet.close puts away steps and what-ifs with Esc, since no click closes them.
  - sheet.steps by pointer reads the rows of "What can be done" rather than the page's step list.
  - menu.close by pointer presses at a window corner no popup covers. The plan's "outside" point could land on the first popup.
- **Small additions:**
  - The dialog guard also catches `QDialog.exec`, `QMessageBox.exec` and `QFileDialog.exec`.
  - The campaign case expects every step's act to finish without an undeclared ask or refusal.
  - `read.desk` also accepts `motion` and `last`.
- **Edge cases found in a scratch run of every act:**
  - On the bench sheet the Kernel refused `hand.cell B3=300` ("B3 holds words"). The act reported the refusal correctly, but the bench seed has no settable number at B3, so a successful `hand.cell` is not tested.
  - The change path of `hand.step` and all of `type.send` (it ran `ls` in a scratch Terminal) are not in the test modules.
  - `go.app calculate` read back "Project Desk" as the tab in front; I didn't look into why.
- **Not done:** her door, word forms, MCP/CLI exposure, putting the acts in `SEED_FILES`, a keyboard route to the head menus, the Kasandra run of P01, converting existing probes, and the version number (still 0.8.1).

The full step-by-step log of the final campaign run is in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_acts_build/campaign_scenes_final`.