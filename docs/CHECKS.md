# The checks, in tiers

One command runs the checks at the size the moment needs:

```
python3 tools/run_tiers.py 0                      # at every change: under a minute
python3 tools/run_tiers.py 1 [--changed REF]      # before a commit: tier 0 and what imports a changed file
python3 tools/run_tiers.py 2                      # at a release: everything, in both looks
```

`--look graphite|kasandra|both` chooses the look (tiers 0 and 1: the look in force; tier 2: both). `--out DIR` is where
the run writes `tier<N>.json` and every module's output (a new temporary folder by default; never inside the program
folder). `--against EARLIER.json` says what changed since an earlier run of the same tier.

| Tier | What it runs | When | Measured here |
| --- | --- | --- | --- |
| 0 | 25 fast modules (two of them in part) that guard the most: the owner's guards always, then the most planted bugs caught per second | every change | 35 to 52 s (budget: 1 minute) |
| 1 | tier 0, and every test module and window check that imports a changed file | before a commit | 1 min 46 s for a one-line change in `workbench/agenda_qt.py` |
| 2 | every test module, the 22 window checks, the playable scene on Rail Demo four ways, the name sweep, the release check's integrity sections | a release | 11 min 36 s per look; both looks in one run 25 min (budget: 15 minutes a look) |
| 3 | the ThinkPad: the check, the scenes on the real display, an evening of use | each release, by the owner | not run here |

Each module, window check and scene runs in a process of its own, with an empty home folder and a temporary folder of its
own, offscreen, at the lowest priority, in the look it is given: Kasandra's with `GRAPHITE_APPEARANCE=kasandra`,
Graphite's with the variable unset, the default the owner starts with. None of the program's own variables passes from
the shell that starts the run (`ARC_LEDGER_*` such as the workspace a switch chose, `ARC1_WORKBENCH_*`, `LEDGER_*`,
`GRAPHITE_*`), nor the `XDG_*_HOME` folders or `PYTHONPATH`. It runs in a process namespace of its own where the machine
allows one (as root, or with user namespaces), and elsewhere, as on the owner's machine as a normal user, in a process
group of its own; either way, when it ends, by itself or at its limit, what it started ends with it. Two run at a time,
the longest first. Each has a time limit (`tools/tiers.json`); a run stopped at its limit is a failure. Each child also
carries its own limit (`timeout`, 30 s after the run's), so that even if the run itself is killed outright, no test goes
on past it.

The run prints one table (look, kind, name, tests run, failed, skipped, seconds, state), the failing tests with the words
they failed with, and a last line: `0 failing`, or how many and where, and then the tests skipped and where (a module
whose solver or rights are missing on this machine says so instead of passing quietly). It exits 0 only when nothing
failed. A module that dies or ends in the middle of a test without unittest's last word is a failure.

Ctrl-C (or SIGTERM, or the terminal closing) stops a run at once: nothing more is started, every module running is killed
with what it started and its folders removed, and `tier<N>.json` is written with those marked `interrupted` (a failure)
and the rest `not run`. The last line starts with `interrupted`, and the exit is 130. A second Ctrl-C changes nothing.

## Tier 0: the guards first

The list is in `tools/tiers.json`, each entry with why it is there. Always in it, whatever they cost: her hand's rules
(`test_stacy_hand`, and the pure rules of `test_desk_acts`), the memory rules (`test_resource_rules`,
`test_memory_settings`, `test_model_settings`), release integrity (`test_release_check`), the seed being current
(`test_project_desk`), one name (`test_one_name`'s name, sweep and code classes; its window sweep takes two minutes and
is left to tiers 1 and 2), and the Kernel's scopes (`test_conditions`, `test_network_watch`, `test_documents`,
`test_cabinet_actions`), change sets, continuing work and backup. The rest were chosen from the planted bugs of
14 November (`unique kills` per second of the module's time): every module that alone caught a planted bug in under
seven seconds, the line's rules and the colour-vision check.

## Tier 1: what the change touches

A test module is chosen when it, or one of its own helpers in `tests_integrated/` or `tools/`, imports or names a changed
file: an import anywhere in the file, a patch target such as `'workbench.x.y'`, a path such as `'tools/campaign.py'`. A
changed file that is not Python is followed to the Python files that name it, by its file name as a whole word
(`CHECKS.md` is not named by `WINDOW_CHECKS.md`). A file moved or renamed counts under both its names, so the tests that
import the old name are chosen. The changed files are what `git` says differs from the commit (`--changed REF`, HEAD by
default) and the files it does not know yet, so tier 1 needs a git checkout: in the installed kit, which is not one,
run tier 0 or tier 2. The program's own imports are not followed:
the window imports most of the program, so following them chooses 72 of the 74 modules for any change at all. What a
change reaches only through the window is tier 2's. A window check is chosen the same way. `MANIFEST.json` and the seed
follow the source and are read by tier 0; `wip/` is never run. The map of what each file imports is kept in the user's
cache folder and read again only where a file changed (3 s to make, a fraction of a second to reuse).

## Tier 2: the release

Every module in `tools/check_hatch.py` (`FOCUSED_MODULES` and `ON_DEMAND_MODULES`, the list a new module must join), in
each look; `test_one_name` and `test_rail_demo_campaign` once, because each already runs both looks itself. The window
checks are `UI_CHECKS`, read when the run starts, in each look, their captures under the run's folder. The scene is P01 on
Rail Demo, by pointer, by keys and each again with Reduce motion (`tools/campaign.py run --case DP01a,DP01b,DP01c,DP01d`),
in each look. The name sweep reads the code (`tools/name_sweep.py`); the window is swept by `test_one_name` in both looks.
The release check's own sections (`tools/check_release.py`: the payload, the seed, the registry record, the privacy scan)
run once; a report left in the folder by an earlier run is removed first, so it is never read as this one's.

## What the release no longer runs, and why

At 0.8.2 the checks outside the suite took 64.8 minutes (72.9 with the suite) and, since 0.5.0, had caught one real fault
(the frame check's process start, 0.7.0); the scene caught two more in its first release; the crawler and the probes caught
none. What changed:

- **The probes and the crawler are not part of the release.** The 30 probes (run at two sizes, 30.8 minutes) and the
  crawler (in two looks, 28.1 minutes, 95% of it fixed waits) lived only in the build's scratch folder, never in the
  program. Nineteen probes judged nothing (they printed and took pictures), and the crawler's 15 logs since 0.5.0 are the
  same bytes. What they looked at that still matters is for the scenes and the desk acts' tests to check (below).
- **The name sweep is in the suite** (`test_one_name`, 0.8.4), over the code, the guide pages and the live window in both
  looks, and it now also finds a printed key and "Programs".
- **The gate's failing scripts are gone:** seven retired, the rest ported; all 22 pass in both looks (docs/WINDOW_CHECKS.md).
- **A changed failure shows.** The old comparison looked only at pass and the line a check stopped on, and twice hid a
  message that changed. Each row of a tier's result keeps the failing tests and their words, and `--against` reports a
  change of words as a change.

Not done yet, from the same review: new scenes from existing desk acts (the owner's mouse path, her hand, the meters and
the pane) and the probes' remaining checks as assertions in the modules that already build the window.

## Fixed waits

Measured on 19 November by timing every `QTest.qWait` and `time.sleep` in one run of each window check (Graphite's look):
the 22 checks spent 115 of their 351 seconds waiting (33%). Tier 0 hardly waits at all (two pauses of 0.3 s in
`test_network_watch`, the time a real capture thread needs). Two checks wait for more than half their time:

- `check_model_turn_ui`, 8.8 of 14.5 s: almost all of it is already a wait for a condition (`wait_for` looks every 50 ms
  until the turn has landed); its fixed part is about 1.7 s.
- `check_finder_ui`, 37 of 67 s: its `settle()` (three rounds of events and 30 ms) runs about 400 times, inside the steps
  that walk the window from 1,040 to 1,400 px wide and the reading size from 14 to 28 pt. What it waits for is the
  window's own deferred work (layouts measured again, the head's words folding, a pane measuring its faces again), which
  has no single condition to wait on, and a check whose waits are cut too fine fails under load for no fault (the look
  probe did so in 0.6.1). It is left as it is. Halving it would save about 9 s of each look's tier 2.

Not changed either, and listed here: `check_operations_ui` waits 0.4 s after each slider key and 2.1 s for the meters'
timer (2.9 of its 8.8 s); `check_context_menu_ui` (9.4 of 21 s) and `check_agent_ui` (6.8 of 18 s) settle between steps
the same way. The crawler, which waited for 95% of its time, is no longer run.

## Measured here

On 19 November 2026, on a copy of the tree (four cores, another build's two test processes running beside it, load 2 to
3.5), each child at nice 19 in a process namespace of its own, two at a time:

- **Tier 0:** 39.9 s, 39.4 s and 38.6 s in three runs; 25 runs, 412 tests, 0 failing. After the review's fixes, on the
  same tree: 35 s, 37 s and 37 s in Graphite's look and 38 s in Kasandra's; then, with another build's tests running
  beside it (the children took 98 s between them instead of 67 s), 52 s and 47 s. Under a minute each time, but that
  margin is what a busy machine takes.
- **Tier 1** for a one-line change in `workbench/agenda_qt.py` (with the seed made current again): it chose
  `test_delete_words`, `test_hologram`, `test_kasandra_column`, `test_session_start` and `test_typewriter_faces`; 30 runs,
  492 tests, 1 min 46 s, 0 failing.
- **Tier 2,** one look after the other: Graphite 11 min 36 s, Kasandra 11 min 35 s; each 100 runs, 1,160 tests, the 22
  window checks (220 steps), the scene 4 of 4, 0 failing. In Graphite's look the children took 1,391 s between them: the
  modules 920 s (the slowest `test_desk_acts`, 187 s), the window checks 372 s (`check_finder_ui` 68 s), the scene 90 s,
  the name sweep 5 s and the release check's sections 4 s. Two at a time, the run takes half of that.

Both looks in one run (`--look both`, the default for tier 2), after the review's fixes, with another build's tests
running beside it (load 2.5 to 3.3): 25 min 3 s; 196 runs (the two modules that run both looks themselves, the sweep and
the release check's sections once), 2,302 tests, the 22 window checks and the scene 4 of 4 in each look, 0 failing, and
10 skipped, named on the last line (`test_startup_scripts`, 5 in each look: the privilege tests). The children took
3,005 s between them, so two at a time were busy the whole run; each look's half, 12.5 minutes, is inside the budget.
