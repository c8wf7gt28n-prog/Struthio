# Graphite 0.8.5 · the application set

This set replaces the application set in the `App` folder of your Graphite_Transfer kit (0.8.4, or anything earlier).
Everything else in that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are
the same for 0.8.5, and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs and every
later `Graphite_…_part` ZIP up to `Graphite_0.8.4_part`, with their `START_HERE` ZIPs. Keep the System and Wheels sets;
the offline install on the ThinkPad still needs them. The Records set is history only and nothing here reads it. The
source itself is also kept at the address at the end of this page.

## What is here

- `Graphite_0.8.5_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.5_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App`. They are no longer
   needed.
2. Extract `Graphite_0.8.5_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.5_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.5-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The same steps as for 0.8.4, with 0.8.5 in the folder name. Install into the new folder; your earlier folder and your
workspace stay as they are. With `debs/` and `wheels/` already copied into `App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.5
bash "$HOME/Applications/Graphite-0.8.5/START_MINIMAL_DEBIAN.sh"
```

## New in 0.8.5: maths in lines

Type a line in the writing line at the bottom and ask four kinds of question about the numbers on your desk, with no
model loaded and in a fraction of a second. Guide → the page on lines has every form and worked examples, each checked.

- **Solve:** on Rail Demo, the settled current that keeps the rail under Rev B's 4 W is up to 333 mA at 12 V; with your
  own tolerance on the voltage it tightens (326 mA at ±0.25 V), and the answer shows the case that would break it.
- **Range and check:** the exact span of an answer when its inputs have ranges, and **Holds**, **Does not hold** or
  **Cannot tell**, always with the reason.
- **A receipt for every answer:** what was asked, every input with where it came from, the method, how exact it is,
  whether anything it rests on has changed, and "model calls: 0".
- **Your tolerances stay yours:** only you set one, Kasandra always asks first, and a changed value sends it to recheck.
- **Money and dates:** amounts kept exact in their currency (a weekly budget, two loans compared by the total repaid);
  days between dates, months the calendar's way, business days, and deadlines that say whether the last day counts.
  Holidays only from a list you type in the line. No financial or legal advice: it computes what you ask.
- Also: the setting "Script for incidental text" is gone, and a few values from your own workspace are out of the
  program's shared files.

## Worth trying on the ThinkPad

1. In the writing line, the Rail Demo solve from Guide → the page on lines; then press "see the receipt".
2. The weekly budget example with your own numbers.
3. If you have time, the four things from 0.8.4's list.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 20 November 2026 in a cloud build container, offscreen, with no model, on the commit cut, `5329a51`:

- **The release check, tier 2** (`tools/run_tiers.py 2`), on that exact commit: 208 runs, 2,543 tests, **0 failing**, in
  both looks (30 minutes 41 seconds): the whole suite in each look, the 22 window checks in each look, the playable scene
  on Rail Demo in each look, the name sweep, and the release check's own sections. Ten tests were skipped, five per look:
  the start scripts' tests that need an ordinary user on a Debian host; they run on the ThinkPad.
- **These parts** restore with `INSTALL_LS.py`; the restored tree matches the commit file for file except two folders
  left out on purpose (`wip/`, the build's working notes, and `tools/planted_bugs/`, a test tool), and
  `tools/check_release.py` passes on it.
- **Every part of 0.8.5 was built by one agent, reviewed by another that did not build it, and fixed.**

Not done: nothing in this set has run on the ThinkPad. No model was loaded (none is needed for anything in 0.8.5).

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
