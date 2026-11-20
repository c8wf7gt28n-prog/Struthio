# Graphite 0.8.6 · the application set

This set replaces the application set in the `App` folder of your Graphite_Transfer kit (0.8.5, or anything earlier).
Everything else in that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are
the same for 0.8.6, and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs and every
later `Graphite_…_part` ZIP up to `Graphite_0.8.5_part`, with their `START_HERE` ZIPs. Keep the System and Wheels sets;
the offline install on the ThinkPad still needs them. The Records set is history only and nothing here reads it. The
source itself is also kept at the address at the end of this page.

## What is here

- `Graphite_0.8.6_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.6_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App`. They are no longer
   needed.
2. Extract `Graphite_0.8.6_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.6_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.6-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The same steps as for 0.8.5, with 0.8.6 in the folder name. Install into the new folder; your earlier folder and your
workspace stay as they are. With `debs/` and `wheels/` already copied into `App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.6
bash "$HOME/Applications/Graphite-0.8.6/START_MINIMAL_DEBIAN.sh"
```

## This set was not tested

You said "No tests" for 0.8.6 and 0.8.7, and "We test before 88". So nothing in 0.8.6 has been through the test suite,
the tiers or the window checks, and no part was reviewed by a second agent. Install it into a new folder and keep your
0.8.5 folder: it is a preview. The full test pass comes after 0.8.7, before any of 0.8.8.

## New in 0.8.6: Kas's mind without a model

- **Why, on every card.** Right-click a card on the Field and choose Why: a short proof in her column, each line with
  its state and where it came from; click a line and its wires light up. Beside it: Rests on, Either way, What would
  settle it. Model calls: 0.
- **Her mind, with no model:** goals worked out exactly, your word kept with revisions (it always asks), either way,
  what would settle it, her dictionary, pinned quotes and rule cards, dates further, what this change did, where does my
  desk say it, your phrasebook.
- **Your head and footer:** your Struthio as Apps upper right, the menus from the middle column, the neon equalizer
  upper left, the writing line, room button and send (cyan in Kasandra) under the middle column, the four ring meters
  under the right column.
- **The first parts of 0.8.7:** the sealed room for her model (a key set in your shell for another tool no longer
  reaches it), prompt reuse, her clock and switches, worth asking, pick never write, the doorway, pages in pencil, her
  voice floor and her character file. Most of these show only with a model loaded.
- docs/RELEASE_NOTES_0.8.6.md (Guide → What's New) has all of it, and four things the talks promised that are not true
  yet.

## Worth trying on the ThinkPad

1. Guide → Try Rail Demo (it builds in a new folder of its own and opens in its own window). Right-click "Startup is
   inside the Rev B limit of 40 ms" and choose Why; click a line; press Next.
2. On the same demo: Either way and What would settle it on the startup goal.
3. Guide → An Evening with Kas's Mind, the ten things to try. Two of its ten examples were run here; the rest are written
   from the design's numbers.
4. Look at your new head and footer at your own screen size, in both looks.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built on 20 November 2026 in a cloud build container, offscreen, with no model, on the commit cut, `d97127c`:

- **Not run:** the test suite, the tiers and the window checks (your rule), and every model arm of I05 (its kit is in
  `tools/i05_kit/` in the source, for the ThinkPad). The demo windows themselves were not started here.
- **Checked:** each part's builder ran one script of the design's own examples; at each merge, Graphite started and its
  window opened offscreen in both looks. These parts restore with `INSTALL_LS.py`; the restored tree matches the commit
  file for file except the folders left out on purpose (`wip/`, the build's working notes, `tools/planted_bugs/` and
  `tools/i05_kit/`), and `tools/check_release.py` PASSED on it (1,399 files).

Nothing in this set has run on the ThinkPad.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
