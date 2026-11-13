# What's new in Graphite 0.6.0

November 13, 2026. Guide → What's New opens this page. The 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5,
0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

## Stacy has a hand

"I want to discuss giving Stacy agency to control all of Graphite just like I can so I can tell her to do something and
an artifact is made just as if I had saved a file. I'm less concerned about her running out of control."

Until 0.5.3 the rule was: she reads freely, and any change waits for your Approve. That rule is now one place on a dial
of three. This is its first slice: the dial, the changes she can already make, her trail with Undo, the rule for what
always asks, noticing, and the Terminal commands that are hers.

### The dial

Under her face, beneath "speaks staC", two words say where her hand is. Click them to change it (the same three are
under **Rules ▸ Stacy's hand**):

- **Ask first** ("asks before any change"). As it was: every change waits for your Approve.
- **Do and show** ("does and shows"). What a workspace opens with. A change you ask her for is made at once. She says
  what she did, with the exact line, and it has one **Undo**. What the records themselves mark for approval (working a
  calculation again, taking a finding out of what is known) still waits for you.
- **Free hand** ("has a free hand"). She also makes the changes marked for approval, and she acts on what she notices.

### What "at once" looks like

In the Field, select the sheet and say to her **set the startup current to 700**. With Do and show, the sheet is saved
with the new value, she says "Done. B4 … now says 700 mA (it said 650)", and the card has **Undo**. Undo puts the 650
back, exactly, and says so. If the sheet was saved again after her change, Undo is refused and nothing is touched: it
only ever puts back what it took.

The steps she lists for a thing (**Do**) say which wait: a step marked "asks first" waits for you; another that
changes something she does when you take it.

### Something made, as if you had saved it

"... so I can tell her to do something and an artifact is made just as if I had saved a file."

Say it in words and the thing is where yours would be, made through the same operation your own New Folder, save and
New Document use:

- **make a folder called Bracket** → a folder in Files.
- **write a file called Bracket/plan.txt saying cut the stock first** → that file, with those words (a name with no
  ending becomes a .txt).
- **start a page called Bench plan, saying: check the rail first** → a page in Documents and on the Field, marked in
  its record as started by Stacy.
- **make a note called Rail idea that says try a ferrite** → a note, marked as kept by Stacy.

A folder or file she made has **Undo**: it goes to the Trash, which gives it back. She never writes over a file that
is already there: she says so and asks for another name. A page or a note has no exact Undo (the records have no
"remove a page"), and she says that.

### Her trail

Every act of hers is one line: when, what, at which word of yours, and whether it was taken back. Click her hand's
words and choose **What she did…**: the latest first, each with "Undo this" where an exact Undo is left. The trail is
kept with the workspace (the last forty acts).

### What always asks

"Anything that can't be undone, by rule, would always force" her to ask. On every place of the dial these wait for you:

- sending something to another computer, or anything with another computer's address in it;
- removing what cannot be brought back (moving a file to the Trash is not this: the Trash gives it back);
- emptying the Trash;
- ending the session or turning the computer off;
- a command in the Terminal that is not on her list.

**What always asks…** in the same menu says the list. It is one short table in `workbench/stacy_hand.py`, written to
be read and struck from.

### The Terminal: some commands are hers

"Some terminal commands are reasonable for" her "to have control over." Say **run df -h**, or **in the terminal: ls
Documents**. A command that only reads (ls, cat, df, free, uname, lsblk, ps, find without its deleting forms, ip
without its changing forms, journalctl, and the like), one at a time, with nothing piped, redirected or substituted,
she runs herself in the Terminal and says so. Any other command she puts in the line, with Terminal chosen, for you to
run. With her hand at Ask first, every command is put in the line.

### Noticing

"I kind of want her to be autonomous." With a **Free hand**, after a change made through her she checks the desk as
**Check all** does, and what stood on the changed thing and needs no decision of yours she brings back to current
herself. Ask her to set the startup current: she sets it, then says "I noticed 2 things that stood on what just
changed" and works both calculations again. Each is a line in her trail. What needs your judgment (a review, an open
question) she leaves alone. On the other two places she notices nothing by herself.

## What this slice is not

- **She cannot yet name every operation from plain words.** Without a model her hand reaches what her grammar knows:
  setting a number on a sheet, the steps of her list, settling the desk, making a folder, a file, a page or a note,
  and a Terminal read. "Export this", "rename that", "move these" asked in words are not recognised yet. With the
  model you named (Qwen3.6-35B-A3B) her proposals arrive as staC, and letting those run under her hand is the next
  piece.
- **No exact Undo for what adds.** A calculation worked again is a new page kept beside the old one; she says there is
  no exact Undo, and the old page is in Documents.
- **Noticing is one pass, after her own change.** She does not yet watch the desk while you work elsewhere.
- **The first journey you asked for is not built**: "get me started on a project in a program that I may not be
  particularly familiar with". It is next, and needs one answer from you: which program first (Godot, GIMP, FreeCAD,
  KiCad, Inkscape, LibreOffice), since each needs its own starting files.

## What was checked, and what was not

A probe runs the real window offscreen through all of it on the worked case: Do and show (done at once, Undo, the
trail), an Undo that is no longer exact (refused, nothing touched), Ask first (Approve as before), a change marked for
approval (waits at Do and show, hers at Free hand), noticing (both calculations current afterwards), the Terminal (a
read runs, `rm -rf` is put in the line), things made at her word (a folder, a file in it, a refusal to write over it,
Undo to the Trash, a page, a note, and the same at Ask first), and the menu. Twelve tests cover the rule itself: the
dial, what always asks, what takes an act back, the words that ask for something to be made, the trail, the Terminal list. The earlier probes that walk the Approve path now set her hand to
Ask first themselves. The project's own tests and the window gate were run on the exact commit before this set was
cut: see the set's START_HERE for the numbers.

Not done: nothing later than 0.4.6 has run on the ThinkPad. No model was loaded: everything here was asked in the
words her grammar knows. The Terminal commands were stood in for in the checks (the list was tested; `df` was not
actually run by the probe). No second reader has gone over 0.4.7 to 0.6.0.
