# Graphite 0.8.1 · the application set

This set replaces the `Graphite_0.2a13_part` ZIPs in the `App` folder of your Graphite_Transfer kit, and any later application set (0.3 to 0.8.0) you put there. Everything else in
that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are the same for 0.8.1,
and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs, and the
`Graphite_0.3_part`, `Graphite_0.3.1_part`, `Graphite_0.4_part`, `Graphite_0.4.1_part`, `Graphite_0.4.2_part`,
`Graphite_0.4.3_part`, `Graphite_0.4.4_part`, `Graphite_0.4.5_part`, `Graphite_0.4.6_part` (both cuts), `Graphite_0.4.7_part`, `Graphite_0.4.8_part`, `Graphite_0.5.0_part`, `Graphite_0.5.1_part`, `Graphite_0.5.2_part`, `Graphite_0.5.3_part`, `Graphite_0.6.1_part`, `Graphite_0.7.0_part` and `Graphite_0.8.0_part` ZIPs, with their `START_HERE` ZIPs (0.3 through 0.8.0). Keep the System and Wheels sets; the offline install on the
ThinkPad still needs them. The Records set is history only and nothing here reads it. The source itself is also kept at the
address at the end of this page.

## What is here

- `Graphite_0.8.1_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.1_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App` (0.2a13 and anything
   later). They are no longer needed.
2. Extract `Graphite_0.8.1_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.1_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.1-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The steps are the ones in your 0.2a13 kit, with 0.8.1 in the folder name. With `debs/` and `wheels/` already copied into
`App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.1
bash "$HOME/Applications/Graphite-0.8.1/START_MINIMAL_DEBIAN.sh"
```

New in 0.8.1: **the right-click**, as you asked ("right click was too complex … make its power easy to use and
chain/pipe. With right click icons too").

- **Short.** Every right-click has one shape: the thing at the top with its glyph, up to four usual actions for that
  kind of thing, **Then ›** (or **Start from ›** on an empty place), and **More ›** with everything else in named groups.
  A file's menu is six rows; it was 25, taller than the small screen. Nothing was taken away: the rest is under More.
- **Pictures.** Every row wears one of Graphite's drawn glyphs, eight of them new (trash, pause, filter, sort, count,
  count by, watch, trace). In Kasandra, Then and the line's steps are royal purple, and Move to Trash is red.
- **It chains.** **Then ›** shows the thing's line on its royal-purple slab, how many rows it gives, the first few, and
  steps to carry it on, each saying what it gives before you take it: **Keep rows where ›** a column › a value (is mA, 2
  rows; at least 110, 3 rows), **Sort by**, **Count**, **Count by**, **First**, **Back a step**; then **Show it**, **Put
  it in the writing line**, **Copy the line**, **Copy the rows**. It reads once when it opens; every choice after that is
  counted from that read. In the Field, on 07 Bench readings it reads the sheet's reviewed rows: 4 rows, and where unit is
  mA, count, gives 2.
- **Stop asks first**, on a screen of its own (Stop it, Leave it). **Nothing scrolls** and **no key is printed**; never
  more than two popups beside each other.
- Try it: right-click a CSV in Files, choose **Then**, then **Keep rows where** › a column › a value, then **Count**,
  then **Show it**.
- Three choices are yours (the release notes have them): an Undo for Rename/Move/Copy; whether rows that repeat another
  may leave the menu; whether the glyphs follow Rules ▸ Buttons. Until you say, nothing changed there.
- Not yet: saving a line's rows as a sheet, watching it, adding it to the Agenda or keeping it as a word from the
  panel (these will go through her hand, with Undo), and a few more steps (Total by, Only some columns, Add a column,
  Match with a table). That is the second half of the plan.

**The model's memory rules are decided for your 35B.** Auto now takes your Qwen3.6-35B-A3B at 39 GiB free (it needs
31.40 GiB free: its 26,013 MiB estimate, the 2 GiB reserve and 4 GiB of headroom), and that headroom stays with it after
you ask, so the model waits rather than starting with too little room. Admission and launch follow one rule; a model
replacing another waits for the old one's memory; Ready means it answered; a hold holds. The campaign's resource cases are
22 of 22 plain passes. On the ThinkPad, `python3 tools/campaign.py run --mode real --case M01 --model
/path/to/Qwen3.6-35B-A3B-Q4_K_M.gguf` from the installed folder checks your file and your memory; send me its folder.

**Also new:** the typing line's empty words say **prompt**; **Programs is Apps**; in Kasandra the send arrow and the
Trash are red; the left trees have a little light under the path you are on, and in Kasandra the tree is a line of
telephone poles.

What came before 0.8.1 is in Guide → What's New (the notes for 0.8.0 back to 0.3): Kasandra and the campaign (0.8.0),
the meters as doors (0.7.0), the first journey into Godot (0.6.1), her hand (0.6.0), and the Field before that.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 14 November 2026 in a cloud build container: these parts restore with `INSTALL_LS.py`, the restored
tree matches the published source file for file, and `tools/check_release.py` passes on it. The window was run offscreen
with no model. The commit cut is `e13f6e0`; it differs from `efe3378`, where the window probes, the crawler and the
project's tests ran, only by the right-click's window check (`tools/check_context_menu_ui.py`, brought to the new shape)
and the manifest.

- **The project's tests:** 57 modules and 897 tests (one module, 15 tests, new for the memory rules), with the same 20
  failing as before this work began (they assert an earlier look, layout and version); none is new. The right-click's own
  module has 44 tests (10 new).
- **The model's memory rules:** the campaign's resource set gives 22 of 22 plain passes; the memory-rule tests 15 of 15.
  An independent check of the first fix found two gaps (Auto's headroom kept only at submit, and a handover near the
  limit that could lose the previous model); both are closed here, with a test each.
- **The window probes:** all 30 pass at 1920 × 1200 and at 1366 × 768. Two of my probes had to learn the new shape first: What if is now under More, opened in place, and at 1920 × 1200 the Field fits whole, so the drag test zooms to reading size before it looks for a scroll bar.
- **The crawler** pressed every control and menu line with icons, in Graphite and in Kasandra: 71 controls and menu lines pressed in each, the program never ended, no error.
- **The name sweep** of every label, tip and menu line, in both appearances: the language is named in 0 places.
- **The window gate:** run alone, 7 of 17 scripts pass, as in 0.8.0; the other ten stop at the same lines. The right-click's own script now checks the new shape, with a new capture of the line panel.

Not done: nothing in this set has run on the ThinkPad (0.4.6 is what you have there). No model was loaded: her answers
here are the ones she gives from the records. The memory rules were checked with simulated readings of your machine
(64 GB, the model's real header), not with the model in memory; `tools/campaign.py run --mode real` on the ThinkPad is
the first real test. The right-click was judged from pictures at 1920 × 1200 and 1366 × 768 by the one who built it,
not on your panel.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
