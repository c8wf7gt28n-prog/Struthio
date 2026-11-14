# Release checks outside the suite: cost, what they caught, what to change (0.8.2, d1df337)

Most of this battery repeats itself and judges very little. It takes 64.8 minutes per release outside the 8.2-minute suite (72.9 minutes in all). At the 0.8.2 release run every check came back clean and no failure was new. Across the stored release runs since 0.5.0 I found one real fault that a release check caught (the gate's frame check, in 0.7.0). Two more came from the scene in its first release (0.8.2). None came from the crawler or a probe. Stopping only the duplicate runs and the dead ones gets the release battery to about 14.9 minutes without writing any new code. Moving what the probes really check into the repository brings it to about 9.3 minutes.

## Data files
All under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/testclean/checks/`:
- `checks.json`: per check: what it judges (file:line), what the suite already covers, its track record, behaviour at the two sizes, its share of fixed waits, the files it runs, and the proposal with minutes.
- `measurements.json` holds everything raw. The pieces are:
  - `timings.json`: seconds per check and per probe, from log mtimes.
  - `gate_history.json`: 34 stored gate results, script by script.
  - `census_identifiers.json`: the probes' identifiers looked up in the tests.
  - `release_changes.json`: workbench files changed per release.
  - `touch/`: one traced run of every probe and of the crawler, with the workbench files each one runs.
  - `logs/`: timed runs and the wider sweep.
- `tools/`: the scripts that produced these (`assemble.py` builds `measurements.json` first, then `verdicts.py` builds `checks.json`).

I ran everything in my own extracted copy, at nice 19, in a private pid namespace, with at most two processes at once.

## 1. Cost
The 0.8.2 run was strictly sequential (`checks_082.sh`), so each check's time is its log's mtime minus the previous log's mtime. The run started at the birth time of the extracted trees, 08:01:56.

| Check | Seconds | Minutes |
|---|---|---|
| Suite (59 modules) | 489.7 | 8.2 |
| Scene P01, Graphite + Kasandra | 70.9 + 71.9 | 2.4 |
| 30 probes at 1920x1200 | 923.1 | 15.4 |
| 30 probes at 1366x768 | 922.8 | 15.4 |
| Crawler, Graphite + Kasandra | 841.7 + 841.7 | 28.1 |
| Name sweep, both appearances | 12.2 + 11.5 | 0.4 |
| Gate (`check_release.py --ui`) | 191.0 | 3.2 |
| **Total** | **4376.5** | **72.9** |

- **Most expensive probes** (both sizes, seconds): icons 246, find 199, hand 168, door 112, start 93, look 87, pages 78. The 0.8.1 runs agree within about 1 s per probe.
- **The crawler's time is almost all waiting.** It took 836.9 s, of which 793.1 s (94.8 %) are fixed `QTest.qWait` calls the script asks for (`logs/crawl_timed.log`). It reopens a page before every press with `settle(700,6)`, plus `settle(350,4)` per press (`crawl_probe.py:27,61,65`).
- **The probes too.** Once the window is built, 80 % of the 28 traced probes' time is fixed waits (692 of 864 s; 29–92 % per probe, `touch/set.out`). `open_tile` alone waits 7.2 s with `settle(900,8)` (`icons_probe.py:9`).
- **Gate split.** From the capture folders' times, the ten scripts that stop early take about 74 s and the seven that pass about 117 s.

## 2. Track record

**Scene** (one release old)
- The playable scene found the writing line's results left over the Field (d1df337).
- The release run showed that a Kasandra attempt had been played in Graphite and still passed (02498ad). Until that fix, the Kasandra scene run was not testing Kasandra at all.
- It is the cheapest check here with a real finding.

**Crawler**
- I found 16 crawler logs. The first is from 0.4.9 development (`logs049/crawl_words.log`). The other 15 are byte-identical (md5 d806cfe7): every release from 0.5.0 to 0.8.2, Graphite and Kasandra alike, CLEAN every time. My own run at d1df337 matches too, digits aside.
- It has never found a fault. The 0.4.9 crash it was built to hunt was found during the icon work (4e7244c); `crash_probe` replays it.
- It presses only the controls of five work pages and the bar above them (`crawl_probe.py:37-73`). It never presses controls on the head, the Field, Home, Talk, the right-click, Apps or the meters, which is where the releases since 0.5.0 made their changes.

**Name sweep**
- It found 1 place ("stac ›") during 0.8.0 development (`logs080/sweep_graphite.log`), fixed before release. It has found 0 places at each of the three releases since.
- I widened its pattern to printed keys and "Programs" (`tools/wide_sweep.py`, 11 s). That found 0 "Programs" and 9 strings that print a key: Ctrl+Shift+P, Ctrl+Shift+F12, F11, ``Ctrl+` ``, Ctrl+Shift+N, F9. They sit in tips, status tips, one menu-line text and accessible descriptions (`logs/wide_sweep_graphite.log`).
- These are candidates only: the sweep does not check whether a widget is actually shown. The 0.5.2 kit already says "tips deep in the older rooms may still name a key" (`kit_START_HERE_052.md:191`).

**Gate** (34 stored results, `ui_base` to `ui_082`)
- **The seven passing scripts** failed together only once (`ui_070`), when 0.7.0 removed the System button on purpose; the scripts were edited to match in 94b0dee.
- **The ten failing scripts** stop at the same line as in the imported 0.2a13 tree (a15cdc8). Most stop lines assert names or a look that the owner's directions have since replaced; three are on the head's fit and geometry and on the Brain room's process start:
  - `check_frame_ui.py:173` and `check_rename_ui.py:136` expect 'Assignment'.
  - `check_machine_ui.py:75` expects Machine/Cabinet/Settings.
  - `check_graphite_ui.py:99` expects one wordmark at the far right.
  - `check_hatch_ui.py:124`: opening the Brain room runs dpkg-query (`inference_hardware._query_packages`) under the no-process hold; 13ddfc5 kept that read on purpose.
  - The others are `check_continue_ui.py:142`, `check_desk_ui.py:145`, `check_finder_ui.py:112`, `check_head_ui.py:106` and `check_paper_ui.py:110`.
- At most 122 of their 740 assert statements stand before the stop lines, so at least 83 % never run.
- **One real finding:** `check_frame_ui.py:151` caught a process start (dpkg-query on opening the Work trail) in 6 of the 34 runs from 0.4.8 on. The kits called it "unsteady" for five releases (`kit_START_HERE_051_sent.md:174`) before 0.7.0 fixed it (13ddfc5, `kit_START_HERE_070_sent.md:285`).
- **Changes the comparison hid.** `compare_ui.py:9-10` compares only pass and stop line, and reported "no difference from the baseline" in both cases below:
  - `check_finder_ui.py:112` changed its message at 0.5.1 (Work 38/36 px, Arrange 67/65 px) and at 0.8.1 ("Apps needs 96 px, has 79"). This is in the check's own "1920 Today" layout. The head probe on After Hours 07 shows Work at 60 px, so whether a person ever sees it cut is not shown.
  - `check_head_ui.py:106` changed its reason at 0.7.0: the widget it measures became [0,0,0,0].
- **Maintenance:** 9 commits edited gate scripts after the import (including 94b0dee, 16 files, and 2ca282c, 15 files). 4873b67 had to undo captures a gate run wrote into the tree.

**Probes** (30)
- **19 judge nothing.** They print and take pictures; a release can only fail them by a traceback, because the grading greps for WRONG|FAIL|terminate called (`checks_082.sh:20`). 10 keep a PASS/FAIL flag; `crash_probe` judges only that the process lives (`crash_probe.py:13` prints PASS unconditionally).
- **Faults found at release: none.** The only catches were during feature development:
  - icons: "More ▾" wider than 34 px (`logs049/icons_fh.log`), and the crash replay (`logs049/crash_before.log`).
  - kasandra: WRONG during 0.8.0 (`logs049/set_q_1366x768/kasandra_probe.log`).
  - line and door: FAIL during the 0.8.0 rename.
  - line: one FAIL in 0.7.0 development that passed 5 minutes later.
- **False alarms:** mouse in 0.5.3 (`kit_START_HERE_053.md:207`) and look in 0.6.1, a timing failure under load (`kit_START_HERE_061.md:255`).
- **Rewrites forced by intended changes:** look (0.8.0), mouse2 and cascade (0.8.1), kasandra (0.8.2), mouse, amber and ux044 (0.6.0), line (0.8.0).
- **Dead or wrong steps nobody noticed:**
  - The mouse probe has clicked a "? keys" button that no longer exists since 0.5.2 ("card: None" at both sizes, `mouse_probe.py:69`).
  - Its T row is None at 1366x768 in every run since 0.5.3 (`mouse_probe.py:75`).
  - The amber lamp is "not clickable" at 1366x768 in every stored run since 0.4.9 (`amber_probe.py:25`).
  - `more_probe.py:30` ends in `or True`, so its underline check can never fail.
  - `first_probe` has pictured After Hours 07, not an empty workspace, since 0.4.9: `nomodel.py:8` needs a fifth argument "empty", which `checks_082.sh` never passes. Its log says "empty field objects: 14" in 28 runs.

What each probe checks that no test does is listed per probe in `checks.json`. Field and page behaviour in the live window (glide, wheel, drag, the bar above the work, More presses, Find on live pages, the meter cards, the pane's way back) has no test by identifier. Logic-level overlap is large:
- `test_faces_find_light`: icons, Find, page light, equalizer, zoom kept.
- `test_writing_line`: line.
- `test_stacy_hand` and `test_stacy_start`.
- `test_kasandra`.
- `test_context_menu` and `test_desk_acts`: cascade.

## 3. Overlap
- **Crawler in two appearances:** identical output in all 3 pairs (0.8.0–0.8.2). The second run adds 14.0 minutes and nothing else.
- **Probes at two sizes:** 19 of 30 give the same output once digits are set aside. In the 11 that differ, the differences are printed and never judged; the probes judge nothing size-specific except look's Z.
- **Probes and crawler:** pages, more, icons and find open the same five pages the crawler presses.
- **Probes and suite** (`test_desk_acts.py:313-386`): the suite already drives the meters (:338), panes (:344) and zoom (:356) on a live window, asserting that each act changes nothing.
- **Scene and suite:** `test_desk_scenes.py:50-83` plays the same P01 five ways in the suite, 1366x768 included (62.7 s). The release run adds only the After Hours 07 workspace and Kasandra.
- **Gate and suite:** `check_desk_ui`, `check_paper_ui` and `check_graphite_ui` are the window halves of the failing `test_desk`, `test_paper` and `test_graphite`. Those modules' docstrings name the scripts, and a script and its test module stop at the same superseded design.
- **Change-based running by the import map would save little.** The window runs 295 of the 445 workbench modules before any probe starts. `shell2.py` changed in all 10 releases from 0.5.0 to 0.8.2, so a rule of "run when a file it runs changes" would have run every window check at every release.
- **The crawler is the exception.** Its own files are the pages beyond the window start plus `centre_bar.py` and `tool_faces.py`. Those changed in 6 of the 10 releases, so the rule would have skipped it at 0.6.0, 0.6.1, 0.7.0 and 0.8.2.

## 4. Proposal (minutes per release; 64.8 outside the suite today)

**Step 1: stop runs, write nothing new → 14.9 minutes (49.9 saved)**

| Change | Minutes saved |
|---|---|
| Retire the Kasandra crawl | 14.0 |
| Run the Graphite crawl only when its own files change (would have run 6 of 10 releases) | 14.0 per skipped release |
| Take the 18 probes that judge nothing off the release; run them on demand as pictures | 10.8 |
| Run the 12 kept probes at one size (1366x768, `test_desk_scenes.py:55`); only look stays at both | 9.4 |
| Name sweep into the suite | 0.4 |
| Take the ten failing gate scripts out of the gate until the failing-tests part fixes their stop lines or retires them | 1.2 |

Also make `compare_ui` compare the assertion message as well as the line.

**Step 2: move what is checked into the repository → about 9.3 minutes (55.4 saved)**
- **New scenes** from existing desk acts, played by `test_desk_scenes` and by the campaign at release (one case each, about 18 s per appearance): P02, the owner's mouse path (mouse); P03, her hand (hand); P04, the meters and the pane (door, pane).
- **Assertions into existing modules** on the window `test_desk_acts` already builds:
  - look: the head shows a page's name, not its address.
  - icons: bare glyph at most 34 px, and its tip.
  - line: names whole, no tip names a key.
  - centre, audit, zoom, mouse2 and regress: one or two assertions each.
  - The wider name sweep, with a "shown" filter.
  - The crash regression.
  The crash test, and Find on the PDF, writing and finding pages, need the After Hours 07 fixture in the repository (`campaign_fixtures/Graphite_After_Hours_07.zip`, 1.1 MB) or a bench seed with a finding.
- **Keep at release, one size:** find, eq (needs a real busy thread), start (reads a Godot script outside the repository, `start_probe.py:24`), kasandra (20 s). Also keep the scene in both appearances and the seven passing gate scripts.
- **Retire:** pages, more, cascade, window, stacy. Fix or retire first.

This step-2 shape follows `final_pass_081.md:24` ("probes … become scripts of desk acts") and the record's "Checking. Light … No new test suites" (`RECORD_OF_DIRECTIONS.md:61-62`): the moves add assertions to existing modules and scenes, not a new suite.

**Separately:** replacing the fixed waits with waits for a condition would cut most of what remains. When the crawler does run, 94.8 % of its 14 minutes is waiting.

**Not measured:** the gate's per-script times are estimated from capture folder times. The step-2 scene cost is an estimate. Whether the 9 key strings and the 1366x768 lamp and T row are visible to a person, or meant, was not decided here.