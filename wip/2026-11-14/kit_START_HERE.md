# Graphite 0.8.3 · the application set

This set replaces the `Graphite_0.2a13_part` ZIPs in the `App` folder of your Graphite_Transfer kit, and any later application set (0.3 to 0.8.2) you put there. Everything else in
that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are the same for 0.8.3,
and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs, and the
`Graphite_0.3_part`, `Graphite_0.3.1_part`, `Graphite_0.4_part`, `Graphite_0.4.1_part`, `Graphite_0.4.2_part`,
`Graphite_0.4.3_part`, `Graphite_0.4.4_part`, `Graphite_0.4.5_part`, `Graphite_0.4.6_part` (both cuts), `Graphite_0.4.7_part`, `Graphite_0.4.8_part`, `Graphite_0.5.0_part`, `Graphite_0.5.1_part`, `Graphite_0.5.2_part`, `Graphite_0.5.3_part`, `Graphite_0.6.1_part`, `Graphite_0.7.0_part`, `Graphite_0.8.0_part`, `Graphite_0.8.1_part` and `Graphite_0.8.2_part` ZIPs, with their `START_HERE` ZIPs (0.3 through 0.8.2). Keep the System and Wheels sets; the offline install on the
ThinkPad still needs them. The Records set is history only and nothing here reads it. The source itself is also kept at the
address at the end of this page.

## What is here

- `Graphite_0.8.3_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.3_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App` (0.2a13 and anything
   later). They are no longer needed.
2. Extract `Graphite_0.8.3_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.3_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.3-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The steps are the ones in your 0.2a13 kit, with 0.8.3 in the folder name. With `debs/` and `wheels/` already copied into
`App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.3
bash "$HOME/Applications/Graphite-0.8.3/START_MINIMAL_DEBIAN.sh"
```

New in 0.8.3: Kasandra's look, second pass, from your words of today.

- **Her hologram, lower left.** Kasandra stands under the Files tree, above DELETE, as a violet hologram on a projection
  base. The static moves (drifting scan lines, a soft flicker, a rare tear, a faint colour split), and her state shows
  in it: quiet, at work, waits for you, done, stopped. Reduce motion holds her still; the Clean desk shows no art.
- **Her column is for her words:** her name, her state and her dial at the top, her words the full width below.
- **Every word in her typewriter face.** Code, lines, numbers and Terminal output use a fixed-width cut of the same face,
  so columns line up, and the one never reads as an l.
- **DELETE** where Trash was; a document's own Delete is now Erase.
- **Burnt yellow is the highlight:** a solid bar with dark ink in menus, a yellow edge elsewhere, and never green (the
  pointer's halo is pale violet in Kasandra so it cannot turn the yellow bar green).
- **Your neon kp logo is Apps,** about 44 px tall with a neon glow drawn by Graphite, and the only kp mark.

Not yet: her hand on the desk and the test clean-up were stopped half-way for this cut, and a few small yellow items
are listed under "What is not done" in Guide → What's New.

What came before 0.8.3 is in Guide → What's New (the notes for 0.8.2 back to 0.3): desk acts and the playable scene
(0.8.2), the right-click and the memory rules (0.8.1), Kasandra and the campaign (0.8.0), and the Field before that.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

You asked for this set straight away, so it had fewer checks than usual. Built and checked on 14 November 2026 in a
cloud build container, on the commit cut, `951c789`: these parts restore with `INSTALL_LS.py`, the restored tree matches
the published source file for file, and `tools/check_release.py` passes on it. The window was run offscreen with no
model.

- **The project's tests:** 64 modules and 1,007 tests (five modules, 70 tests, new for this look), with the same 20
  failing as before (they assert an earlier look, layout and version); none is new.
- **Your playable scene** on After Hours 07, through the campaign in Kasandra: 4 of 4 (by pointer, by keys, and each with
  Reduce motion).
- **The look** was built and then gone through by four independent reviews (two for the hologram, faces, column and
  DELETE; two for the yellow and the logo), each from its own frames at 1920 × 1200 and 1366 × 768 in both appearances.
  Their findings were fixed except the small ones listed under "What is not done". The last two (the pointer's green
  halo on the yellow bar, the chain menu's pictures vanishing on it) were fixed for this cut and checked by measurement:
  0 green pixels under the pointer.
- **Not run for this cut:** the 30 window probes at two sizes, the crawler and the name sweep (about an hour together),
  and the window gate. They ran clean on 0.8.2; the look reviews took their own frames instead.

Not done: nothing in this set has run on the ThinkPad (0.4.6 is what you have there). No model was loaded. The
hologram's static, the faces and the yellow were judged from pictures taken offscreen, not on your panel.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
