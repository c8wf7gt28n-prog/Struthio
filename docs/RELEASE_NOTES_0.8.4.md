# What's new in Graphite 0.8.4

November 20, 2026. Guide → What's New opens this page. The 0.8.3 to 0.3 notes beside it describe what came before.

This release is **Tests you can believe**. It adds no new feature on purpose: it makes the ground firm before Kasandra's
riskier work (her day look, her hand inside other programs, the web). From now on a red test means something is really
wrong.

Your words of 19 November shaped it: "Just kas. Otherwise we have too many people", and "I want you to build this until
completion". It was built over one day and night by agents working on their own, each part checked by a second agent that
did not build it, then fixed.

## Kasandra, by name, in every look

- The name on screen is **Kasandra** in both looks: menus, tips, her column, Activity, the brain's rows, the About page,
  the Guide pages and the phone page.
- Stacy's portraits stay as the first look's art. Her art plate is now called "Kasandra after midnight".
- Records written before keep the name they were written with. A test fails if the old name comes back on screen.

## A sturdier start

- **Leaving with the Office open no longer risks "Graphite could not start".** Found in 0.8.3: in the full-screen session,
  a start after leaving with the Office tab open could fail. It no longer can, and a damaged session file falls back to
  the defaults instead of stopping the start.
- **Rooms come back.** What you had open comes back when you start again: 72 kinds of room, where 22 did before.
- **The set-aside list no longer grows.** What cannot come back is set aside once, never twice, and Kasandra says so once
  in Activity, in plain words.
- Her column no longer says "Now: Now:".

## Her look, finished

- In the Kasandra look her burnt-yellow light round the writing line and the Field's chosen sheet is a **warm glow**
  instead of grey.
- A selected row looks the same everywhere: the Log, Documents, the process list, Explore, the cabinet.
- The PDF evidence mark is a clean yellow edge; the kp logo's thin strokes are crisp; the pointer's glow no longer turns
  green over the yellow bar.
- Tips, notes and guides **name the button to press, never a key**. A test reads every sentence of the program and fails
  if a key name comes back. The few that stay (the Field's key labels, the console's "Press Enter again", the Help
  keyboard page, the games) are keys with nothing to click instead; they are on a reviewed list.
- A **colour-vision check**: every pair of colours that means different things is simulated for weak red and weak green
  sight, and every pair those eyes cannot tell apart also has a word or a shape that tells them apart.
- Side panes come back to their width after you change the reading size and go back; "Date Modified" and long folder
  names are no longer cut in the Kasandra look.
- The menu toggle "Pleasantries in script" is gone: it changed nothing on screen.

**To look at, by eye:** the writing line's light now steps as it fades; the Field's rings show under overlapping sheets;
the Return thread's writing box turned from yellow to blue.

## Lines answer correctly

- `2*-3` gives −6. Totals are exact (no rounding to six places). Numbers written as text count as numbers, under one
  rule everywhere.
- `select title, state` works with a space after the comma; a quoted `;` is accepted like a quoted `|`.
- `true` and `1` stay separate groups; a join matches keys exactly as written and never overwrites one of your fields.
- **A line you saved before may now give a slightly different, and correct, answer.**

## Rail Demo, an invented workspace

A small engineering workspace made of invented data (a 12 V rail: bench readings, two limit revisions, calculations,
findings, an open question), built by the program itself in a few seconds. The playable scene and the campaign's checks
now run on it anywhere, without your After Hours 07 backup. Every page of it says "Invented demonstration data. Nothing
here was measured."

## The checks themselves

- **Zero failing, in both looks**: 1,204 tests in 78 modules, in the Graphite look and in the Kasandra look.
- **The window checks**: seven that measured a desk Graphite no longer has were retired, each with its reason
  (docs/WINDOW_CHECKS.md); the 22 that remain all pass in both looks and run in the release check.
- **Tiers** (`tools/run_tiers.py`, docs/CHECKS.md): tier 0 in about 40 seconds, tier 1 for what a change touches, tier 2
  the whole release check in about 11½ minutes per look (the release checks took about 65 minutes before).
- **Planted bugs**: small bugs planted on purpose to see whether the tests notice. In the code that protects you
  (Kasandra's hand and what always asks, the Kernel's permissions and record paths, the memory and model rules, change
  sets and Undo, continuing work, the seed and the release check) the tests caught 30 of 53 at 0.8.2 and catch **51 of 53
  (96%)** now; across all 131, from 53% to 76%. Most new tests were written for these same planted bugs, so this says
  these holes are closed, not how a bug nobody has planted yet would fare; a fresh sample is the next measure.

## Built, checked here, not run, observed on the ThinkPad

- **Built:** everything above.
- **Checked here:** in a container, offscreen, on copies of the program: the whole suite in both looks, the 22 window
  checks in both looks, the release check on the exact commit of this kit, Rail Demo's campaign cases.
- **Not run:** nothing on the ThinkPad. No model has run with this release. Only one version of the PDF reader (Poppler
  24.02) was tried with Rail Demo.
- **Observed on the ThinkPad:** nothing yet. Worth trying when you install it:
  1. leave Graphite with the Office tab and two rooms open, then start again;
  2. look at the Kasandra look's light round the writing line and on the Field;
  3. `python3 tools/campaign.py run --set demo` (Rail Demo with your machine's PDF reader);
  4. when you are ready, the first model run.

## What is not done

- Kasandra's hand in programs, her day look, the web and the maths in lines come in the next releases (0.8.5 to 0.8.9).
- Two small changes were built but held for 0.8.5 so this kit could be cut sooner: removing the setting "Script for
  incidental text" (in Settings, it changes nothing on screen), and taking a few values from your own workspace out of
  the program's shared files.
- Small things carried forward: odd corners of the line evaluator that were never silent errors (a line ending in `group`
  with nothing after it, `add` replacing a field you named) go to 0.8.8; one step of the retired frame check (the tab
  strip's height across six tabs) is covered by nothing yet; a fresh sample of planted bugs.
