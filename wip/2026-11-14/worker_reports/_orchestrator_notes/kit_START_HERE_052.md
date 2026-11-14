# Graphite 0.5.2 · the application set

This set replaces the `Graphite_0.2a13_part` ZIPs in the `App` folder of your Graphite_Transfer kit, and any later application set (0.3 to 0.5.1) you put there. Everything else in
that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are the same for 0.5.2,
and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs, and the
`Graphite_0.3_part`, `Graphite_0.3.1_part`, `Graphite_0.4_part`, `Graphite_0.4.1_part`, `Graphite_0.4.2_part`,
`Graphite_0.4.3_part`, `Graphite_0.4.4_part`, `Graphite_0.4.5_part`, `Graphite_0.4.6_part` (both cuts), `Graphite_0.4.7_part`, `Graphite_0.4.8_part`, `Graphite_0.5.0_part` and `Graphite_0.5.1_part` ZIPs, with their `START_HERE` ZIPs (0.3 through 0.5.1). Keep the System and Wheels sets; the offline install on the
ThinkPad still needs them. The Records set is history only and nothing here reads it. The source itself is also kept at the
address at the end of this page.

## What is here

- `Graphite_0.5.2_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.5.2_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App` (0.2a13 and anything
   later). They are no longer needed.
2. Extract `Graphite_0.5.2_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.5.2_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.5.2-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The steps are the ones in your 0.2a13 kit, with 0.5.2 in the folder name. With `debs/` and `wheels/` already copied into
`App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.5.2
bash "$HOME/Applications/Graphite-0.5.2/START_MINIMAL_DEBIAN.sh"
```

New in 0.5.2, from what you said on seeing 0.5.1:

- **No keys are shown.** Every key still works; none is printed. Menus have no key column and no underlined letters.
  The Field's buttons say Do, Doubt, Trace, Check all, Back. Tips no longer end in a key. The one page that lists the
  keys is the card the **?** key opens in the Field.
- **The glyphs in the menus are neon green.**
- **The glow opens on Neon.** Soft and Bright are still under Rules ▸ Desk artwork ▸ Glow.

Stacy with a free hand is written up for you in `docs/RELEASE_NOTES_0.5.2.md` with my proposal and three questions;
nothing of it is built until you answer.

From 0.5.1, from your walk round the program on the ThinkPad:

- **The menus are across the top.** Work, Revise, Tools, Arrange, Commands, Rules, Properties and Guide stand in the
  open at the left of the head, as you asked ("kind of like Apple does, instead of hidden away in a menu"). They are
  the same menus that were inside Work. The name of what is open follows them.
- **Way more glow, on a dial.** **Rules ▸ Desk artwork ▸ Glow ▸ Soft | Bright | Neon**. It opened on Bright in 0.5.1 (about
  twice what 0.5.0 had) and opens on Neon now. The bands' amber rules, the name at the head and the tree now glow too. I set the level from
  pictures: turn it to Neon if Bright is still not enough on your panel, and tell me.
- **The tree is a circuit.** Green traces, chamfered, with pads; the path to the row you are on is lit.
- **More icons.** Twenty-two more, and the lines of the menus carry them.
- **The System menu** no longer shows an empty queue's controls.

Not built, with my recommendation in `docs/RELEASE_NOTES_0.5.1.md` for you to decide: the right pane as one view
instead of three; the bottom line kept as your one master line with a chooser for whom you are typing to; the System
menu regrouped; GIMP, Godot and the like in Programs.

From 0.5.0, what I chose when you said "Turn off all my rules, and don't hold back", and then "mostly focus on how
it looks ... and fun to use. Think apple simplicity but still very powerful":

- **Simple at rest.** The head of the window says the name of what is open ("07_Bench_Readings.pdf · Preview · PDF"),
  not `graphite://open/5ab8a3fd…`; click it or press Ctrl+L and the address is there, selected. The name is said once:
  the bar above the work is the way back to the Field and six controls. Tools are drawn icons with no boxes at first
  sight (**Work ▸ Rules ▸ Buttons ▸ Words** brings worded plates back). Stacy is the first thing on the right.
  A PDF page's identity lines and a sheet's status lines are faint.
- **Z fits your window, and glides.** Since 0.4.7 Z always shrank the desk to 35 per cent, however large the window;
  on a 1920 by 1200 screen the whole desk sat small in the middle. It now uses the room there is: the worked case
  shows whole at 80 per cent on that screen, every sheet readable, and it gets there in a short glide instead of a cut.
- **The whole desk is a map.** Press **Z** in the Field. From that far the words on a sheet used to be five pixels
  high. Now each sheet is the glyph of its kind (a page for a source, a table for a sheet, the sum for a calculation,
  a ticked cell for a finding, a question mark for a question), its name in letters that stay readable, and the lamp
  of its state. The arrows walk it and a click opens a sheet, as near to.
- **Find works on every page.** It was dimmed everywhere but in a text file. **Find** in the bar (or Ctrl+F) opens one
  line under the controls and searches whatever is open: writing, the cells of a sheet, a list, the lines of a finding,
  the words of a PDF page (the page that is open, not the whole file). Enter for the next place, Shift+Enter for the
  one before, Esc to close.
- **The Field opens as you last saw it**: its size, or the whole desk.
- Under the hood, a crawler now presses every control of the work pages looking for a way to end the program, and
  sixteen tests cover the new parts.

`docs/RELEASE_NOTES_0.5.0.md` says why each was chosen.

From 0.4.9, which was never sent as a set of its own (all of it is here), no white boxes. You pointed at the PDF page of 0.4.8: "No ugly white boxes that stand out like a sore
thumb." Buttons and fields are no longer outlined in the pale ink: each is a dark plate with a quiet edge, green under the
pointer, amber when it has the keys. A PDF page is shown **in the desk's light**: the same page with its paper brought
down from white (the file, its citation and anything exported are untouched). **More ▾ → Show the page in its own
light** shows it as the file has it, and the choice is kept. The low tone was chosen from pictures, not on your panel: say
if it is too dim or still too bright and it is one value.

Also from 0.4.9: **icons**. Every tool wears one of thirty glyphs drawn for Graphite (cut strokes, small solid facets, a
hexagonal lens for Find) and has no box at all. What every program has is its glyph alone and says its name in its tip;
what is particular to a page keeps its words beside its glyph. **Work ▸ Rules ▸ Buttons ▸ Words** brings the worded
plates back. Whether each glyph says what it means is yours to judge on your panel.

**If you put 0.4.7 or 0.4.8 on the ThinkPad, replace it with this.** Those two could end without a message when a
finding was read again while the keyboard was on one of its buttons (after a click on Compare sources again). 0.4.6,
which you have running, was never exposed: it has no bar above the work.

Otherwise 0.4.9 only took away. Every control was asked whether something else on the same screen
already did its job. Gone: the strip under the work, the Actions control (it opened an unrelated menu), the second and
third Save buttons, the PDF page's own size choice and heading, the dots on a sheet in the Field, the words that scrolled
the Field, and seven buttons from its foot. **Save** in the bar above the work is the one place that saves, and it is lit
only when there is something to save. `docs/RELEASE_NOTES_0.4.9.md` lists each cut, what was questioned and kept, and what
still repeats and is yours to decide (the Work menu, the Activity pane).

From 0.4.8, a control looks like a control. An action is a button (since 0.4.9 a dark plate, not a bright outline); a word that only goes somewhere is underlined;
the work itself has neither look. The keys at the foot of the Field are buttons. The sheet page, the PDF page and the page
of writing each have one row of tools above the work, and **More ▾** holds what is needed now and then (on the sheet page,
seven of its eleven actions), each line saying what it does and, when it cannot be done now, why not. Nothing was taken
away.

From 0.4.7, the mouse first. Above whatever is open in the centre there is one row of controls, always in the same
place: **‹ Field**, the name of what is open, **Find**, **−** **+**, **Undo**, **Redo**, **Save**. One that the
open view cannot serve is dimmed and its tip says why. In the Field, **Z** shows the whole desk in the window (Z again for
the ordinary size), **+** and **−** or Ctrl with the wheel change the size, the bars at the edges can be dragged, and the
right button on a sheet shows what can be done with it. A
button is now as wide as its words: on the sheet page a click on empty ground beside "Recalculate" used to recalculate.

Also from 0.4.7, amber glows where it means something. One amber halo marks where your next key will go: the selected
sheet, the page being read, or the writing line. What waits for you is lit at its mark, and **Approve** glows until it is
pressed, in the Field and in Talk alike. The Clean desk (Work → Desk art) has no glow.

From 0.4.6, green: your pointer (the two facets of the Graphite mark, aimed at 11 o'clock, the click at the tip) is drawn
in the desk's green, and whatever it is over answers in green. What is live glows a little. The pointer has not been seen
on a real screen yet; yours will be the first.

From 0.4.5, the mouse: click a tile in the Field to open it in the centre, and **‹ Field** (now the first control
above the centre) comes back to the same tile. The right button shows a tile's menu. Every key shown at the foot, on the key card (**?**) and
on a page can be clicked, and a change that waits has an **Approve** button. Ask Stacy "set B3 to 300" with a sheet
selected: the change waits for your Approve, with what it would move marked on the Field.

From 0.4.4: the doubt (**X**), the desk check (**C**), the brief (**B**) and the steps (**D**) open on a page over the work,
at your reading size; **Esc** or Close closes any of them.

From 0.4.3: with a sheet or a calculation selected, ask "what if B4 were 100?" in the writing line and the Field marks
everything that would move (nothing is changed; **Esc** clears). Right-click a sheet for the same things as cascading
menus. **G** keeps the brief as a page. **Backspace** goes back to the sheet you were on before. In the writing strip,
`word waits = field.read | pick waiting | select kind,title,state` keeps a staC line under a word of your own; then
`waits`, `words`, `forget waits`.

As before: **X** doubts the selected sheet (what a plausible result may hide), **D** shows what can be done about it (a digit
chooses, **G** is your go), **C** checks the whole desk, **T** traces a sheet to its source, **P** shows every program as a
shelf, and in the writing strip `this` is the selected sheet. Graphite opens on Home the first time (the workspace is
empty); once there is work it opens on the Field, and **F9** shows the Field at any time. `docs/RELEASE_NOTES_0.5.2.md`
(Guide → What's New) says what is new; the 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe the buttons, the mouse-first pass and the amber light, the green pointer, the mouse path, the reading pass, the look ahead,
the doubt, staC on the desk, the doing, Stacy, the shelf and the Field; `RECORD_OF_DIRECTIONS.md` says where this is going.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 13 November 2026 in a cloud build container: these parts restore with `INSTALL_LS.py`, the restored
tree matches the published source file for file, and `tools/check_release.py` passes on it. The window was run offscreen
with no model. The commit cut is `3d37da7`. On that exact commit the project's own tests give 52 modules and 786
tests with the same 20 failing as before this work began (they assert an earlier look, layout and version; none is new),
and the window gate gives 7 of 17 scripts passing with the other ten stopping at the same lines as before. One of those
ten, the frame check, is unsteady: on 0.5.1 it sometimes stopped 22 lines early, when Graphite's own timed hardware
probe (`dpkg-query`, untouched) fired while the check was looking. This time it stopped at its old line. I have not
found why it became unsteady. The 23 window probes at 1920 by 1200 and 1366 by 768 and the crawler (71 controls and
menu lines pressed with icons, the program never ended, no error) ran on `459583b`; the cut commit differs from it
only in one test and the manifest, and the program's code is identical.

Not done: nothing in this set has run on the ThinkPad (0.4.6 is what you have there). Tips deep in the older rooms
may still name a key. The look was judged from pictures by the one who made it. No second reader has gone over 0.4.7
to 0.5.2.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
