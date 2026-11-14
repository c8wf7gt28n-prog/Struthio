# Graphite 0.7.0 · the application set

This set replaces the `Graphite_0.2a13_part` ZIPs in the `App` folder of your Graphite_Transfer kit, and any later application set (0.3 to 0.6.1) you put there. Everything else in
that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are the same for 0.7.0,
and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs, and the
`Graphite_0.3_part`, `Graphite_0.3.1_part`, `Graphite_0.4_part`, `Graphite_0.4.1_part`, `Graphite_0.4.2_part`,
`Graphite_0.4.3_part`, `Graphite_0.4.4_part`, `Graphite_0.4.5_part`, `Graphite_0.4.6_part` (both cuts), `Graphite_0.4.7_part`, `Graphite_0.4.8_part`, `Graphite_0.5.0_part`, `Graphite_0.5.1_part`, `Graphite_0.5.2_part`, `Graphite_0.5.3_part` and `Graphite_0.6.1_part` ZIPs, with their `START_HERE` ZIPs (0.3 through 0.6.1). Keep the System and Wheels sets; the offline install on the
ThinkPad still needs them. The Records set is history only and nothing here reads it. The source itself is also kept at the
address at the end of this page.

## What is here

- `Graphite_0.7.0_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.7.0_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App` (0.2a13 and anything
   later). They are no longer needed.
2. Extract `Graphite_0.7.0_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.7.0_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.7.0-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The steps are the ones in your 0.2a13 kit, with 0.7.0 in the folder name. With `debs/` and `wheels/` already copied into
`App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.7.0
bash "$HOME/Applications/Graphite-0.7.0/START_MINIMAL_DEBIAN.sh"
```

New in 0.7.0: **the System menu is gone.** You asked how much of it could move into the clickable CPU / GPU / RAM / TXT,
and whether it could be eliminated. All of it moved:

- **Click a meter** at the foot of the window and its card opens upward. **CPU**: Graphite's work (Stop all jobs, what
  runs and waits with its niceness, the queue's order, background priority, Agenda, Work trail). **GPU**: Stacy's
  model (**Brain room**) and Graphite's services (On, Off, Restart). **RAM**: memory, swapping, disks, network, and
  Machine. **TXT**: **Full chat**, and what Stacy has in view.
- **Leaving** (Log out, Exit Graphite, Restart, Shut down) is the last group of the **Work** menu, the first menu.
- **Game** is the last row of **Programs**.
- **The equalizer shows everything that moves**, as you asked: processor, kernel, memory, disks, network, graphics,
  in six groups, read twice a second. A height always means the same rate. Click it for what each group reads now.
  On the ThinkPad the graphics bars should move with the Radeon; here they rested, because this container's driver
  reports nothing.
- **Stacy's pane has no name tag.** Her face is its top. The two links, Brain room and Full chat, are behind GPU and
  TXT. A title comes back only while Activity or Context is up, as the way back.
- **The line expands.** The small control at the left end of the line: one chevron up for more room above the line,
  two for taller, one down to close. With Terminal lit, that room is the Terminal's commands and output.
- **Choosing a log**: with Log lit and the line expanded, the Log's own two words at its top, Events and Network,
  choose the stream. I did not make Full chat a third stream: the Log is read, the chat is typed into, so it is on
  TXT. Say if you want the conversation's record in the Log as well.

**Stacy's hand, gone over by other readers.** Four readers went over 0.5.3 to 0.7.0 and found 32 faults, and I have
fixed them. The important ones: she now does by herself only what is named on her list, and anything else asks,
including whatever is added to the program later. A Terminal line with anything your shell would expand (`$`,
braces, a backslash) asks, because `find . -delete$Z` reaches `find` as `-delete`. Each reading command is held to
its exact reading options. An Undo on a file or folder she made runs only while it is still as she made it: once you
have worked in it, it is yours. And typing never changes the lit name any more (in 0.5.3 a question for Stacy that
began with a link went to a search engine). `docs/RELEASE_NOTES_0.7.0.md` lists all of them.

Still asked of you: **which program next** for "get me started" (Inkscape, FreeCAD, Blender, GIMP, KiCad); whether
Godot on the ThinkPad is Debian's `godot3` or a Godot 4 download; and what "pick up this DSF if we could find it"
meant.

From 0.6.1: **the first journey.** You said: "ask her to get me started on a project in a program that I may not be
particularly familiar with. I get a starting point in that program, and then I can work from within Graphite for basic
operations, or the actual program window." It is built for **Godot**.

- Say to Stacy: **start a Godot project called Lander** (or "get me started in Godot").
- She makes a folder `Lander` in Files with the smallest project that runs: `project.godot`, one scene, one script,
  and `START_HERE.md`, the first five minutes in Godot. It is written for the Godot on the ThinkPad. Debian 13's own
  package is `godot3` (Godot 3.6); Godot's own download is Godot 4; the two do not read each other's projects, so she
  asks the engine which it is. With none installed she writes for Godot 3 and tells you the package name.
- She says what the Godot room reads the project as. **Open it in Godot** waits for your Approve (with a Free hand she
  opens it). Words on her card read the first steps, read the script here, or open the Godot room, which inspects the
  project, opens it in Godot, or plays a scene.
- It is one act: one line in her trail, and one **Undo** that moves the folder to the Trash.
- The Godot room used to look only for `godot4` and `godot`, so with Debian's Godot installed it would have said Godot
  was unavailable. It now finds `godot3` too.

I ran both sets of starting files in real Godot engines here (3.5.2 and 4.3, without a screen): the scene loads and
the script runs. What I could not do is open Godot's editor window, and I do not know which Godot, if any, is on the
ThinkPad.

From 0.6.0 (checked and cut, but not sent as a set of its own: all of it is in this one): **Stacy has a hand.** You said you wanted her able to do what you can, "so I can tell her to do
something and an artifact is made just as if I had saved a file", and that what cannot be undone should always ask.

- **The dial.** Under her face, beneath "speaks staC", two words say how far she acts by herself. Click them to change
  it (also **Rules ▸ Stacy's hand**): **Ask first** (every change waits for your Approve, as before), **Do and show**
  (what it opens with), **Free hand**.
- **Do and show.** In the Field, select the bench sheet and say to her **set the startup current to 700**. It is done
  at once; she says what it said before; the card has **Undo**, which puts the old number back exactly, and is refused
  if the sheet was saved again since. What the records mark for approval (working a calculation again) still waits.
- **Something made, as if you had saved it.** **make a folder called Bracket** · **write a file called
  Bracket/plan.txt saying cut the stock first** · **start a page called Bench plan** · **make a note called Rail idea
  that says try a ferrite**. Each is where your own would be. A folder or file she made has Undo (it goes to the
  Trash, which gives it back). She never writes over a file that is there.
- **Free hand.** She also makes the changes marked for approval, and she notices: ask her to set the startup current
  and she sets it, then says "I noticed 2 things that stood on what just changed" and works both calculations again.
- **What always asks**, wherever the dial is: sending to another computer, removing what cannot be brought back,
  emptying the Trash, ending the session, and any Terminal command that is not a plain read.
- **The Terminal.** **run df -h** or **in the terminal: ls Documents**: a command that only reads, she runs. Any
  other she puts in the line, with Terminal chosen, for you.
- **Her trail.** Click her hand's words, then **What she did…**: every act, latest first, with "Undo this" where one
  is left.

What this first slice is not: without a model she understands only the forms above (she cannot yet "export this" or
"rename that" from plain words) and noticing happens once, after a change made through her.

From 0.5.3, the three parts of the window you asked to keep building:

- **The top bar's middle is an equalizer.** The name and address are out of it, as you asked. Each bar is one
  processor thread of the ThinkPad (sixteen of them) and its height is how hard that thread worked over the last
  second, so it rises when Stacy thinks or anything is busy and lies low at rest. The top of a bar is amber near its
  limit; the bottom row is amber while Graphite itself is working. The name of what is open is back in the bar above
  the work; click that name and its address comes up at the head while you type it.
- **The right pane is one view.** No more Talk, Activity, Context. One title, **Stacy**; under her face a line
  **This:** (what is open, or the sheet selected in the Field; **more** opens everything about it) and a line **Now:**
  (what is running and what waits for you; **activity** opens the whole list), then the conversation. When the whole
  of either is up, the title reads "‹ Stacy · Activity" and a click on it comes back.
- **The line at the bottom: you choose whom you are typing to.** Five names at its left: **Stacy · Terminal · Search ·
  Web · Log**; the lit one gets the words. **Web** is new: an address is opened, and words are searched for, in the
  ThinkPad's own browser (Graphite fetches nothing itself); an address typed with Stacy lit is opened too (since 0.7.0 only when the
  line is nothing but an address, and the lit name never changes by itself). The arrow
  at the end says what it will do, and when what you typed reads as staC it turns green and runs it. No key is named
  anywhere on the line.

Your answers about Stacy's free hand are recorded in `docs/RELEASE_NOTES_0.5.3.md` and `RECORD_OF_DIRECTIONS.md`
(what cannot be undone always asks; some Terminal commands are hers; she may act on what she notices; her model,
Qwen3.6-35B-A3B at Q4_K_M; the first journey: "get me started on a project in a program I don't know"). The first
slice of it is 0.6.0, above.

From 0.5.2, from what you said on seeing 0.5.1:

- **No keys are shown.** Every key still works; none is printed. Menus have no key column and no underlined letters.
  The Field's buttons say Do, Doubt, Trace, Check all, Back. Tips no longer end in a key. The one page that lists the
  keys is the card the **?** key opens in the Field.
- **The glyphs in the menus are neon green.**
- **The glow opens on Neon.** Soft and Bright are still under Rules ▸ Desk artwork ▸ Glow.

Stacy with a free hand was written up in `docs/RELEASE_NOTES_0.5.2.md` with my proposal and three questions.

From 0.5.1, from your walk round the program on the ThinkPad:

- **The menus are across the top.** Work, Revise, Tools, Arrange, Commands, Rules, Properties and Guide stand in the
  open at the left of the head, as you asked ("kind of like Apple does, instead of hidden away in a menu"). They are
  the same menus that were inside Work. (In 0.5.1 the name of what is open followed them; since 0.5.3 the equalizer does.)
- **Way more glow, on a dial.** **Rules ▸ Desk artwork ▸ Glow ▸ Soft | Bright | Neon**. It opened on Bright in 0.5.1 (about
  twice what 0.5.0 had) and opens on Neon now. The bands' amber rules, the name at the head and the tree now glow too. I set the level from
  pictures: turn it to Neon if Bright is still not enough on your panel, and tell me.
- **The tree is a circuit.** Green traces, chamfered, with pads; the path to the row you are on is lit.
- **More icons.** Twenty-two more, and the lines of the menus carry them.
- **The System menu** no longer shows an empty queue's controls.

Built since, in 0.5.3: the right pane as one view instead of three; the bottom line as your one master line with a
chooser for whom you are typing to. Since then the System menu has gone altogether (0.7.0, above). Still not built:
GIMP and the like in Programs.

From 0.5.0, what I chose when you said "Turn off all my rules, and don't hold back", and then "mostly focus on how
it looks ... and fun to use. Think apple simplicity but still very powerful":

- **Simple at rest.** The name of what is open is said once ("07_Bench_Readings.pdf · Preview · PDF"), not
  `graphite://open/5ab8a3fd…`; click it and the address is there, selected. (0.5.0 said it in the head of the window;
  0.5.3 says it in the bar above the work, beside the way back to the Field and six controls.) Tools are drawn icons
  with no boxes at first sight (**Work ▸ Rules ▸ Buttons ▸ Words** brings worded plates back). Stacy is the right pane.
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
empty); once there is work it opens on the Field, and **F9** shows the Field at any time. `docs/RELEASE_NOTES_0.7.0.md`
(Guide → What's New) says what is new; the 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe the buttons, the mouse-first pass and the amber light, the green pointer, the mouse path, the reading pass, the look ahead,
the doubt, staC on the desk, the doing, Stacy, the shelf and the Field; `RECORD_OF_DIRECTIONS.md` says where this is going.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built and checked on 13 November 2026 in a cloud build container: these parts restore with `INSTALL_LS.py`, the restored
tree matches the published source file for file, and `tools/check_release.py` passes on it. The window was run offscreen
with no model. The commit cut is `13ddfc5`. On that exact commit the project's own tests give 54 modules and 829
tests with the same 20 failing as before this work began (they assert an earlier look, layout and version; none is new).
The window gate, run alone, gives 7 of 17 scripts passing, with the other ten stopping at the same lines as before. That
includes the frame check, which was unsteady from 0.5.1 to 0.6.1 and is steady now. Its early stop was real: opening
the Work trail started a process (Graphite asking Debian for its installed packages), and that is fixed. The 29 window
probes, three of them new in this set (Stacy's hand, the Godot start, the meters as doors), all passed at 1920 by 1200
and at 1366 by 768. The crawler (71 controls and menu lines pressed with icons, the program never ended, no error)
ran on a clean copy of the same commit.

Not done: nothing in this set has run on the ThinkPad (0.4.6 is what you have there). The graphics bars of the
equalizer have never been seen moving. Leaving (Log out, Restart, Shut down) was not carried out, only found in its
new place. Godot's editor window was never opened. No model was loaded: everything asked of Stacy was asked in the
forms her grammar knows. No real browser was opened. Tips deep in the older rooms may still name a key. The look was
judged from pictures by the one who made it. Other readers went over 0.5.3 to 0.7.0 by reading the code; a fifth tried
to disprove the eight faults on Stacy's hand and confirmed all of them, and the checks of the other 24 were stopped by
the account's usage limit. 0.4.7 to 0.5.2 have still had no second reader.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
