# The window checks

A window check is a script `tools/check_<name>_ui.py`. It builds the real Graphite window without a screen (Qt's offscreen
platform), on a new profile and a new workspace of its own, walks one area as the owner would with the mouse and the
keyboard, and asserts what the window then shows. Each one holds the calls that would start work: no job is submitted, no
worker or model is started, no provider is asked. Each writes its captures and a JSON report under the folder the gate gives it;
the folder it makes for its own profile and workspace is under a temporary folder of the gate's, removed when the check ends.

They are run by the release check: `python3 tools/check_release.py --ui` runs every script in `UI_CHECKS`
(`tools/check_hatch.py`), one after the other, each in its own process. The look is the one in force; set
`GRAPHITE_APPEARANCE=kasandra` to run them in the Kasandra look. Every script passes in both looks.

The release check runs one look, because one pass of all twenty-two takes about six minutes on the four-core build machine
(371.4 s in Graphite's look and 373.8 s in the Kasandra look, the scripts' times added up, on 19 November 2026), and both
looks would double that. So whoever cuts a release runs `--ui` twice before cutting it: once as it is, once with
`GRAPHITE_APPEARANCE=kasandra`. The Kasandra pass is not optional: it is where 0.8.4 found two of its three faults (below).
The release tier does both: `python3 tools/run_tiers.py 2` runs every check in `UI_CHECKS` in each look, two at a time,
with the suite and the scene (docs/CHECKS.md).

## The rule: no window check without a home

Every `tools/check_*_ui.py` is in one of two lists in `tools/check_hatch.py`:

- `UI_CHECKS`, the gate, run at every release check;
- `ON_DEMAND_CHECKS`, run by hand, where each entry has one line saying what it checks and why the gate leaves it out
  (it starts real processes, needs a program that is not always installed, or loads a model).

`tests_integrated/test_release_check.py` fails when a window check is in neither list or in both, when either list (or the
list of capture folders) names a file that is not there, when an on-demand entry has no reason, and when the program, its
tests or its tools still name a window check that no longer exists (`check_hatch.ui_check_lists`).

Why the rule: by 0.8.3 ten of the seventeen checks in the gate failed, and twelve more stood outside it. On the tree 0.8.4
started from, ten of those twelve failed too (only `check_explore_ui` and `check_operations_ui` passed): they had broken
without anyone seeing, because nothing ran them. From 0.8.4 all twenty-two that remain are in the gate. No window check is
on demand now.

## The twenty-two in the gate

| Check | What it walks |
| --- | --- |
| `check_agent_ui` | an assignment typed on a page, worked by the resident agent, paused by closing and resumed |
| `check_cabinet_ui` | the logical cabinet, its rooms and drafts; the written passages in the prose face |
| `check_cabinet_actions_ui` | a record's actions and the model they are built from |
| `check_context_menu_ui` | the right-click menu on every surface, and Then on a table |
| `check_continue_ui` | work that continues while Graphite is closed |
| `check_document_ui` | the shared document route |
| `check_explore_ui` | Explore, the menus' identity and kept drafts |
| `check_files_about_ui` | the second assignment: files about something |
| `check_finder_ui` | Home as a Finder; every word whole; the head's words folding; the panes' one width; Line, Half and Tall |
| `check_hardware_settings_ui` | the hardware views' settings editor |
| `check_machine_ui` | the Machine view and the work navigator |
| `check_memory_cabinet_ui` | filing and editing owner memory in the cabinet |
| `check_memory_settings_ui` | the memory settings |
| `check_model_settings_ui` | the local model's launch defaults |
| `check_model_turn_ui` | a model's turn applied to a real page |
| `check_navigation_ui` | moving between the cabinet and Settings; the Apps list between the bands |
| `check_operations_ui` | what the right column observes, and the queue's controls |
| `check_presentation_settings_ui` | favourites and saved catalogue views |
| `check_return_thread_ui` | leaving and coming back |
| `check_service_integration_ui` | the service cycle as the window shows it, after failures too |
| `check_settings_ui` | the settings editor |
| `check_settings_02_ui` | session batches, layout and provider preferences |

## Retired in 0.8.4, and why

Seven checks of the gate were retired. Each measured a desk that no longer exists and had failed at the same line since
before the program's history begins. A check that can only fail tells nothing, and a port would have had to be written
from nothing. What each one still said about today's desk was looked for in the tests and the other checks; where
nothing covered it, the step was kept by moving it into a check that passes.

| Retired | What it measured | Why it could not be kept | What checks it now |
| --- | --- | --- | --- |
| `check_desk_ui` (1,197 lines; with its helper `tools/symmetry.py`) | the mirrored desk of 0.1: every left and right pair at 0 px, the cat, the System menu's symbol, the mirrored band words | the desk is no longer a mirror: menus stand from the left of the head, the meters are at the foot, the cat and the symbol are out of sight | the desk's arithmetic in `test_desk`; the live window in `check_finder_ui`. Kept: the panes' one width and the drag (step 14), Line, Half and Tall (step 15) |
| `check_frame_ui` | the frame's five parts through a journey that went through the cat and the strip word "Assignment" | the strip's words and the cat are gone; four attempts to port it each stopped at the next line | `test_frame`, `check_finder_ui`, `test_pane_width`. Kept: the head's menu words fold into ⋯ before they clip at every width from 1,040 to 1,400 px (step 13); full screen and back keeps both panes; one pane width through 14, 16, 18, 20 and 28 pt and back to 14 pt with no ratchet, and under a drag (step 14) |
| `check_hatch_ui` | the Apps list opened from the cat, the System menu's services and leaving rows | opening the Local model room reads the hardware, which the check forbade; the System menu is gone | the list's order, rows, words and routes in `test_launcher`; `check_explore_ui`. Kept in `check_navigation_ui`: the list stays between the two bands in one column; where its rows are taller than the room it takes the whole room and scrolls, and never covers a band |
| `check_head_ui` | the four meters in the head beside the System menu | the meters moved to the foot and the System menu left the head in 0.7.0 | `test_faces_find_light` (each meter is a door), `test_operations` (the queue and its slider), `test_system_menu` (Stop all jobs reaches the Master Stop), `check_operations_ui` |
| `check_graphite_ui` | the head's mark and the cat's four poses on the live window | both are out of sight | the pose machine, its timing and the startup screen in `test_graphite` |
| `check_rename_ui` | that no word on screen said the old names | it walked the cat's list, the System menu and a strip word that are gone | `test_graphite` (RenameGuardTests) and the name sweep of 0.8.4, `test_one_name`, which reads the code, the guide and the live window |
| `check_paper_ui` | the paper theme: yellow writing areas, the X in the margin | writing areas are dark plates now | the writing mark, its setting and its motion in `test_paper`; the hardware editor in `check_hardware_settings_ui`. Kept in `check_cabinet_ui`: written passages are in the prose face at the prose size, a record's data in the code face |

Steps that were not kept, because the thing they measured is gone: the mirrored pairs, the bands' grain compared pixel by
pixel, the cat's poses and its pointer events on the live window, the System menu's keyboard order, the yellow passages.

One step was dropped although its subject is still there: `check_frame_ui`'s step 05, "switching among six tabs leaves the
centre's tab strip at one height and keeps the unsaved draft". Its six tabs were opened along the retired journey, through
the cat and the strip word, so it could not run without it, and it was not rebuilt. Nothing measures the strip's height
now; the code that keeps it still (`qt_app._steady_tab_strip`, the rows under the work) is unchanged since 0.4. It is a gap,
named here so that it is not mistaken for cover.

## The others, ported

Twelve checks needed a few lines each to say what the desk does now: the left tabs are Files, Machine, Settings; the
return thread's link is in the right pane's Activity view; Find's line has its own hint; the Apps list ends with Explore
the workshop and Game; the cabinet tree's right-click is the desk's own menu; Apply has the desk's ink. One,
`check_context_menu_ui`, stopped at its step 09 because the script was behind the program: since the review of 0.8.3 a line's
slab holds its face in its own sheet, before the line's colours. The script now reads the sheet that way; the program was right.

`check_settings_02_ui` had pressed a menu toggle, "Pleasantries in script", that wrote a setting nothing reads. The toggle
is gone (`tests_integrated/test_lit_controls.py`), and in the release pass the setting itself, "Script for incidental
text" (appearance.cursive), was retired; the check now edits the writing marker in Settings, a boolean whose change shows.

## Faults found while doing this

Until 0.8.4 the window checks were run in Graphite's look only. Run in the Kasandra look, `check_finder_ui` stopped twice,
both times on a word that the look's wider typewriter letters cut, and both were faults of the program, fixed in it
(`tests_integrated/test_whole_words.py`):

- the title of the Finder List's Date Modified column: a column is now never narrower than its title needs in the face in
  force (`finder_qt.column_width`);
- a long folder name in a line on one of Today's cards: a plain line now has a break point every 18 characters inside a long
  name, as well as after each `/`, so the name folds instead of being cut (`shell2.breakable_path`).

The review of this work found a third, older than 0.8.4. The retired frame check had gone up to 28 pt; its step, moved into
`check_finder_ui`, at first stopped at 20 pt, because at 28 pt it failed. On a fresh window at 1920 by 1200, 28 pt and back to
14 left both panes 415 px wide where a fresh window has 326 (479 where it has 354 in the Kasandra look). A pane counts every
face's least width, shown or not, and Qt measures a layout again only when its widget shows, so a face out of sight kept
the width 28 pt had given it. A pane now measures its faces out of sight again at each new size (`pane_qt.remeasure`), and
step 14 goes through 28 pt again (`tests_integrated/test_pane_width.py`).
