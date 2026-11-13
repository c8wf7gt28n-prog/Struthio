# What's new in Graphite 0.5.1

November 13, 2026. Guide → What's New opens this page. The 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2,
0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

This release answers the owner's first walk round the program on the ThinkPad itself (with 0.4.6 installed there), top
to bottom. What he said is quoted; what was done about it follows; what he said needs thinking about has a
recommendation at the end and is not built.

## The menus are across the top

"The work menu, I don't know if I like that. It's just an extra click to get to the familiar ... file, edit, tools,
arrange, command, rules, property, guide ... I almost wonder if we should just have those at the top, kind of like
Apple does, instead of hidden away in a menu."

**Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide** stand in the open at the left of the head, one word
each; the name of what is open follows them; Programs and System stay at the right. Each word opens the very menu that
was inside Work (the same menus, so nothing is listed twice and every key works as before). In a window too narrow
for all eight and a name, the rightmost fold into **⋯**, which lists every menu.

## Way more glow

"You asked me about the glow effect. It's not enough. I want way more glow effect."

There is now one dial for all of it: **Rules ▸ Desk artwork ▸ Glow ▸ Soft | Bright | Neon**. It opens on **Bright**,
about twice what 0.5.0 had (Soft is 0.5.0's). Everything that glows follows it: the halo round the sheet that has the
keyboard (which also reaches further), the lamps of what is current, the wires, lit names, the pool of light under the
pointer on the Field, the pointer itself, an icon under the pointer, Approve. And three things glow that did not: the
amber rule of each band throws its light into the band, the name at the head of the window is lit, and the live path
in the left tree (below). The Clean desk still has no glow at all. The level was set from pictures, not on the
ThinkPad's panel: that is what the dial is for.

## The tree is a circuit

"I almost wonder if the tree and the branching could be green and maybe kind of circuit themed. That'd be cool."

The branches of every left tree are drawn as the traces of a circuit board: green, leaving the trunk by a short
chamfer as a trace leaves a bus, and ending in a pad at a row with nothing inside. **The traces from the root to the
row you are on are lit**, and glow: the path is read at a glance. They were one-pixel grey lines with square elbows.

## More icons

"I love your icons. I wish we had more icons."

Twenty-two more glyphs in the same hand (copy, paste, cut, select all, full screen, home, settings, terminal, log,
about, close, receive, this computer, book, key, library, changes, agenda, chain, favourite, split, artwork), and the
fourteen kinds of sheet can now be worn anywhere. **The lines of the menus carry them**: with icons chosen (what a
workspace opens with), a line that names something a glyph was drawn for has that glyph before its words. With
Buttons ▸ Words the menus are words only, as they were. Close on the Find line is a glyph.

Not done here: glyphs on the pane tabs and on the bottom modes. Both are about to be rethought (below), and their
widths are measured by the project's own checks; they should get their glyphs when their shape is settled.

## The System menu, a little

"Systems menu could be simplified and maybe organized a little bit better."

With nothing queued, the queue's heading, its two dimmed order buttons and the note about sliders said nothing; they
now show only when there is a queue to order. The menu is about a sixth shorter at rest. The larger regrouping is a
recommendation, below: that menu's rows are specified and measured in several places, and it deserves the owner's eye.

## For the owner to decide: recommendations, not built

**The right pane: one view, not three.** "I don't think we need three options. Context and activity almost seem like
they could be merged ... talk seems like that could be merged with activity too." Agreed. One scroll, no tabs, in the
order a person asks: Stacy (her face, and in one line what she is doing); *this* (what is open or selected: today's
Context); *now* (what is running, what waits for you: today's Activity, three lines unless opened); then the
conversation. Each part folds to its heading. Nothing is lost, and the pane stops being a place you have to switch.

**The bottom line: keep one master line.** "I like the idea of one master typing line that I select whom I'm typing
to." Agreed, and not a field in Stacy's pane. The recommendation: at the left end of the line, the one you are typing
to as a glyph and a word (Stacy, Terminal, Search, Web, Log), chosen with the mouse or Ctrl+1 to 5, or by how the line
begins (`>` the terminal, `?` search, an address goes to the web). The panel above the line shows what that one
answers with: the terminal, the logs (Graphite's, the system's, the network's), search results. The meters stay.
Today's Assistant, Terminal, Search and Log are four of these already; Web and the "begin with" rule are new.

**The System menu, regrouped.** Three plain groups: *Work* (what is running, the queue, what waits, Stop all),
*Services* (on, off, restart), *This computer* (exit, log out, restart, shut down). Game moves to Programs, where a
program belongs.

**Programs: GIMP, Godot and the like.** The menu lists what is installed and known to Graphite. Adding a program is
a small record (its name, how it is started, what it opens); the question for the owner is which ones, and whether
Graphite should offer to install them from Debian's packages when they are missing.

## What was checked, and what was not

Probes run the real window offscreen at 1920 by 1200 and 1366 by 768: the head (eight menus in the open with their
lines, the fold at 1000 pixels wide, the fold button still listing every menu), the glow at each level and on the
Clean desk, the tree with a nested row current, the menus with their glyphs, the System menu's rows, and all the
earlier walks. Twenty tests cover the glyphs, the faces, Find, the page's light, the menu glyphs and the dial. The
project's own tests and the window gate were run on the exact commit before this set was cut: see the set's
START_HERE for the numbers.

One of the project's window checks counted the trees' branch lines by their old exact grey (`tools/check_desk_ui.py`);
it now counts the green traces, and stops where it stopped before this release, on an older matter.

Not seen: any of it on the ThinkPad's own panel. How strong Bright should be, and whether the traces read as a
circuit there, are the owner's to say. No second reader has gone over 0.4.7 to 0.5.1.
