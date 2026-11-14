# Graphite 0.8.0 · the application set

This set replaces the `Graphite_0.2a13_part` ZIPs in the `App` folder of your Graphite_Transfer kit, and any later application set (0.3 to 0.7.0) you put there. Everything else in
that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are the same for 0.8.0,
and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs, and the
`Graphite_0.3_part`, `Graphite_0.3.1_part`, `Graphite_0.4_part`, `Graphite_0.4.1_part`, `Graphite_0.4.2_part`,
`Graphite_0.4.3_part`, `Graphite_0.4.4_part`, `Graphite_0.4.5_part`, `Graphite_0.4.6_part` (both cuts), `Graphite_0.4.7_part`, `Graphite_0.4.8_part`, `Graphite_0.5.0_part`, `Graphite_0.5.1_part`, `Graphite_0.5.2_part`, `Graphite_0.5.3_part`, `Graphite_0.6.1_part` and `Graphite_0.7.0_part` ZIPs, with their `START_HERE` ZIPs (0.3 through 0.7.0). Keep the System and Wheels sets; the offline install on the
ThinkPad still needs them. The Records set is history only and nothing here reads it. The source itself is also kept at the
address at the end of this page.

## What is here

- `Graphite_0.8.0_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.0_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App` (0.2a13 and anything
   later). They are no longer needed.
2. Extract `Graphite_0.8.0_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.0_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.0-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The steps are the ones in your 0.2a13 kit, with 0.8.0 in the folder name. With `debs/` and `wheels/` already copied into
`App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.0
bash "$HOME/Applications/Graphite-0.8.0/START_MINIMAL_DEBIAN.sh"
```

New in 0.8.0: **Kasandra.** You sent her pack, a palette, a wordmark and a monogram, and asked how I felt about going
in that direction. Yes: it is built as a second appearance beside Graphite, and Graphite is unchanged.

- **Turn it on:** **Rules ▸ Desk artwork ▸ Appearance ▸ Kasandra**. It is kept for this computer and used from the next
  start; choosing it offers to start Graphite again at once (it saves the window first).
- **Her colours, each with one job:** indigo ground; **cyan** for what is selected, has the keyboard, or is ready;
  **raspberry** for a decision that waits for you (Approve); **lavender with a dashed edge** for a sheet that must be
  worked again; **honey**, from her hair, for what is hers (the edge of her answers, the mark under her name when she
  is the one you type to); **violets** for the desk's structure (headings, the Field's columns, your own messages, the
  equalizer, which rises from violet to cyan).
- **Her pictures follow the work**, not chance: the quiet bench at rest; her hand above Enter while a change waits for
  you; comparing her notes with the screen while she answers or a job runs; the pencil down for twenty seconds after an
  Approve; checking a loose cable for forty-five seconds after a refusal. Her face at the top of her pane changes with
  it. The Office shows her office at dusk or in the rain, in turn, with your **kasandra protocol** wordmark at its foot;
  the idle display shows it too; the Field carries her wires and rooftops faintly behind its heading.
- **Your kp monogram** is the icon of **Programs**. Two small glyphs in her column mark **This** and **Now**.
- **Royal purple is the line**, as you suggested: a line you can run stands on a royal-purple slab on her cards, and the
  arrow at the end of the typing line turns royal purple when it will run what you typed.
- **Her name is Kasandra** wherever the assistant is named, and the headings are in the typewriter face from your pack.
- Try it: in the Field select the bench sheet and type to her **set B3 to 300**. Approve glows raspberry and her hand
  goes to Enter; press it and her pencil goes down, while the two calculations that read B3 turn lavender and dashed.

**A line is a line.** As you asked, the language of the lines you can run is not named anywhere in the window any
more: the arrow says **Run this line**, the Field's button is **Line**, the console says "line ›", and her model is told
to call a line a line. A sweep of the running window, in both appearances, finds the name nowhere. It is all still there.

**Less scrolling**, as you asked. A census of every area larger than its window found 7 at 1920 × 1200 and 25 at
1366 × 768. Now: the Field shows itself whole when 80 per cent of its size is enough (on After Hours 07 at 1920 × 1200
nothing scrolls); her pane keeps in view only the latest exchanges that fit, the earlier ones fold behind one word, and
record numbers in a line she shows are cut to six characters; Home fits its window (two columns of cards, a picture that
gives way). At 1920 × 1200, three remain: a finding's long journal page, the settings tree by 35 px, and her pane while
a long answer is the latest. Keys still printed on the main surfaces are gone too (Ctrl Z, Ctrl K, F11, Enter sends…).

**The 35B campaign, first deliverable.** `tools/campaign.py`, with `docs/CAMPAIGN.md` for how to use it: a fixture
workspace for every attempt, 22 resource cases through Graphite's own memory and model rules with a model file built
from your Qwen3.6-35B-A3B's real header (20.5 GB on paper, 56 KB on disk), your 35 situations as anchor cases, timeouts,
resume, a manifest and a summary. Here: 57 cases, 25 Pass, 2 Pass on behaviour your spec asks otherwise, 30 Blocked by
what this machine lacks (the model, LibreOffice and the rest), none failed. On the ThinkPad, from the installed folder:
`python3 tools/campaign.py list` says what that machine has; `python3 tools/campaign.py run --mode real --case M01 --model
/path/to/Qwen3.6-35B-A3B-Q4_K_M.gguf` checks your model file and memory and prints what it would run. Send me its folder.
It also found five places where Graphite's rules would treat your model wrongly (on Auto it refuses it at 39 GiB free,
55 MiB short); they are the first thing to fix next, and are written up in the release notes.

Questions still open for you: which program next for "get me started" (Inkscape, FreeCAD, Blender, GIMP, KiCad);
whether Godot on the ThinkPad is Debian's `godot3` or a Godot 4 download; and what "pick up this DSF" meant.

What came before 0.8.0 is in Guide → What's New (the notes for 0.7.0 back to 0.3): the meters as doors and the
equalizer of everything that moves (0.7.0), the first journey into Godot (0.6.1), her hand (0.6.0), the one view and
the one line (0.5.3), no printed keys and neon glyphs (0.5.2), menus across the top and the glow dial (0.5.1), Apple-
simple at rest (0.5.0), no white boxes and the icons (0.4.9), and the Field before that.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 14 November 2026 in a cloud build container: these parts restore with `INSTALL_LS.py`, the restored
tree matches the published source file for file, and `tools/check_release.py` passes on it. The window was run offscreen
with no model. The commit cut is `5208841`. The project's own tests give 56 modules and 868 tests with the same 20
failing as before this work began (they assert an earlier look, layout and version; none is new); they ran on 7bcae0a,
and the one module whose code changed after it, the campaign's, was run again on the commit cut (23 tests, all pass).
The 27 window probes passed at 1920 by 1200 and at 1366 by 768, one of them new in this set (Kasandra: her palette, her name, her face following the work, the Approve in raspberry, the recheck in lavender, Clean with no art). One older probe had to learn that the Field now opens whole when 80 per cent is enough: at 1920 by 1200 the first Z now brings the reading size, and the second shows it whole again. The crawler pressed 71 controls and menu lines with icons, in Graphite and in Kasandra: the program never
ended, no error. A sweep of every label, tip and menu line in both appearances finds the language's name nowhere.
The window gate, run alone, gives 7 of 17 scripts passing, with the other ten stopping at the same lines as in 0.7.0.

Not done: nothing in this set has run on the ThinkPad (0.4.6 is what you have there). No model was loaded: her answers
here are the ones she gives from the records, and her pictures were checked by setting the work's state (a change that
waits, an Approve, a refusal), not with a model thinking. The campaign's real mode refuses here (no model file, about
15 GB of memory); the five rules it found are not fixed in this set. Whether Debian's own PySide6, if the ThinkPad uses
it instead of the one Graphite brings, can read the WebP pictures depends on the package `qt6-image-formats-plugins`.
The Field's rail shows her picture only when the sheets leave room for it; with After Hours 07 they do not. The look
(royal purple, honey, the violets, the typewriter face) was judged from pictures by the one who made it, at 1920 × 1200
and 1366 × 768, not on your panel.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
