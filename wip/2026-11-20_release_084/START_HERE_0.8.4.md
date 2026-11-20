# Graphite 0.8.4 · the application set

This set replaces the application set in the `App` folder of your Graphite_Transfer kit (0.8.3, or anything earlier).
Everything else in that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are
the same for 0.8.4, and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs and every
later `Graphite_…_part` ZIP up to `Graphite_0.8.3_part`, with their `START_HERE` ZIPs. Keep the System and Wheels sets;
the offline install on the ThinkPad still needs them. The Records set is history only and nothing here reads it. The
source itself is also kept at the address at the end of this page.

## What is here

- `Graphite_0.8.4_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.4_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App`. They are no longer
   needed.
2. Extract `Graphite_0.8.4_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.4_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.4-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The same steps as for 0.8.3, with 0.8.4 in the folder name. Install into the new folder; your 0.8.3 folder and your
workspace stay as they are. With `debs/` and `wheels/` already copied into `App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.4
bash "$HOME/Applications/Graphite-0.8.4/START_MINIMAL_DEBIAN.sh"
```

## New in 0.8.4: tests you can believe

No new feature on purpose: the ground made firm before Kasandra's day look and her hand in other programs. In Graphite,
Guide → What's New has the whole story; in short:

- **Kasandra by name in every look.** Stacy's portraits stay as the first look's art.
- **A sturdier start.** Leaving with the Office tab open no longer risks "Graphite could not start"; a damaged session
  falls back to the defaults; what you had open comes back (72 kinds of room, where 22 did); what cannot come back is said
  once in Activity, and the set-aside list no longer grows.
- **Her look finished.** Her yellow light is warm, not grey; one selected row everywhere; the PDF evidence mark is a clean
  edge; the logo's strokes are crisp; the pointer's glow is never green on the yellow bar.
- **No key named on screen;** tips name the button. A colour-vision check for weak red and weak green sight.
- **Lines answer correctly:** `2*-3` is −6, totals are exact, numbers written as text count, a join never overwrites
  your field. A line saved before may now give a slightly different, correct, answer.
- **Rail Demo,** an invented 12 V rail workspace kept in the program, so the scene and the checks run anywhere.
- **Zero failing tests, in both looks.**

## Worth trying on the ThinkPad

1. Leave Graphite with the Office tab and two rooms open, then start again.
2. In the Kasandra look, the light round the writing line and on the Field's chosen sheet. Three things to judge by eye:
   the light steps as it fades; the Field's rings show under overlapping sheets; the Return thread's writing box is blue.
3. `python3 tools/campaign.py run --set demo` in the program folder: Rail Demo with your machine's PDF reader.
4. When you are ready, the first model run (Brain).

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 20 November 2026 in a cloud build container, offscreen, with no model, on the commit cut, `b6bdb50`:

- **The release check, tier 2** (`tools/run_tiers.py 2`), on that exact commit: 202 runs, 2,368 tests, **0 failing**, in both looks (26 minutes 45 seconds): the whole suite in each look, the 22
  window checks in each look, the playable scene on Rail Demo by pointer and by keys in each look, the name sweep, and the
  release check's own sections (payload, seed, registry, privacy scan). Ten tests were skipped, five per look: the start
  scripts' tests that need an ordinary user on a Debian host, which this container is not; they run on the ThinkPad.
- **These parts** restore with `INSTALL_LS.py`; the restored tree matches the commit file for file except two folders
  left out on purpose (`wip/`, the build's working notes, and `tools/planted_bugs/`, a test tool), and
  `tools/check_release.py` passes on it (1,321 files).
- **Every part of 0.8.4 was built by one agent, reviewed by another that did not build it, and fixed.** The reviews
  caught, among other things, a start-up crash in the first version of the Office-tab fix, "Stacy" still showing in two
  places, totals silently rounded, and a key named on the first screen. All were fixed before merging.

Not done: nothing in this set has run on the ThinkPad (0.8.3 is what you have there). No model was loaded. Two small
changes were built but held for 0.8.5 so this set could be cut sooner: removing the setting "Script for incidental text"
(it changes nothing on screen), and taking a few values from your own workspace out of the program's shared files.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
