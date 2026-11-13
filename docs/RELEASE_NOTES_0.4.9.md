# What's new in Graphite 0.4.9

November 13, 2026. Guide → What's New opens this page. The 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1
and 0.3 notes beside it describe what came before.

The owner: "Really question what everything does and if it's place is justified. Every click necessary. No redoing the
same thing multiple places."

This release adds two choices (a line under More on a PDF page, see "No white boxes"; and Words or Icons for the
buttons, see "Icons, as an option"), mends one fault that could end the program, and otherwise only takes away. Every control on the main
surfaces was listed from the running program with what it does, and each was asked two questions: does anything else on
this screen already do this, and would anyone miss it. The rule the cuts follow:

**One visible home for each action.** Its key is the second road. The right button on a thing is that thing's own road.
A name is said once.

## What was cut

**Above and under the work**

- **The strip under the work is gone.** It said the name of what is open (the bar above the work says it). Its "Working
  area" opened the record that Activity's "Open record" opens. Its "Ask Stacy" opened a second place to talk to her with
  the name typed in, when the writing line under the window already carries what is open.
- **Actions is gone from the bar.** It opened the chain menu, which has nothing to do with what is open. It will come
  back when it can show what can be done with the open thing. The Menu key and the right button open what they always did.
- **Save is lit only when a press would save something.** It was always lit, which invites pressing it to be sure. With
  no changes it is dimmed and says so; on the page of writing, which saves itself, it says that.

**The sheet page**: More no longer has Save working. Save in the bar is the one place that saves.

**The PDF page**

- **Save note** is gone from under the note: Save in the bar saves the note, and is lit when a note has been typed.
- **The size choice** is gone from the row: − and + in the bar step the page (fit the width, 125, 150, 200 per cent).
  The bar's − and + used to change the size of the note's letters on this page, which nobody asked for.
- **Its heading** is gone: it repeated the file's name, which the bar says.
- **Reload notes** and **Recover draft** are under More; one button, New note, is left under the note.

**The Field**

- **The ⋯ on the sheet under the pointer is gone.** It opened the menu the right button opens, and the foot already has
  Do, Doubt and Trace for the selected sheet.
- **The words "more below ↓" and their like are gone.** The bars at the edges show where the desk goes on and move it;
  the words said it a second time and moved it a second way.
- **The foot has nine buttons where it could show sixteen.** Out: Enter open (a click on a sheet opens it), the arrows
  (they are not a control), the faces (they are at the head), A next waiting (the lamp at the head), Z (on the strip
  above), Menu (the right button), and S where Stacy's rail already offers it. Left: Do, Doubt, Trace, Check all, Brief,
  Look again, Where I was, Keys, Back. Every key is still on the card that ? shows.

**The Work menu**: Desk artwork was under both Arrange and Rules. It is under Rules.

## No white boxes

The owner, looking at the PDF page of 0.4.8: "No ugly white boxes that stand out like a sore thumb."

Two things on that screen were white, and both are changed.

- **Buttons and fields were outlined in the pale ink.** 0.4.8 made every action a box drawn in the brightest line the
  desk has, so a row of tools shone harder than the work under it. A button is now a dark raised plate with a quiet
  edge: it is found by its shape, not by its brightness. It answers in green under the pointer and in amber when it has
  the keys, as before. A button that cannot be used now is dimmer still. The same was done wherever that ink outlined a
  box: the writing line, the fields, the page number, the scroll thumbs, the keys at the Field's foot, the menu's edge,
  the tips, the checkboxes, the table review, the worksheet's grid, the program rooms, the frames round the pictures.
- **A PDF page is a white sheet.** The page is now shown **in the desk's light**: the same page, every mark where it
  is, with its paper brought down from white to a low warm tone (each colour multiplied by one tone, so black ink stays
  black). Only how brightly the page is shown here changes: the file, its citation, what is exported, shared or read by
  OCR are the page as it is. **More ▾ → Show the page in its own light** shows it exactly as the file has it; the
  choice is kept, and the same line turns it back. The page beside the rows in Review table and the original page in
  Exact References follow the same choice.

Left as they were: the sheets on the Field (their edges fade with distance and were not what was pointed at), pictures
and artwork (a photograph is not a white box), and the amber Send button.

## Icons, as an option

The owner, after the plates: "Or graphite themed icons can be tried as an option also."

**Work ▸ Rules ▸ Buttons ▸ Words | Icons.** Words is what opens; the choice is kept.

With Icons, a tool button has no box at all. It wears one of thirty glyphs drawn for Graphite in the language of its
own mark: straight strokes of one weight with sharp joins, arrow heads and folded corners as small solid facets, and a
hexagon where another program would draw a circle (graphite is sheets of carbon in a hexagonal lattice; the lens of
Find is one).

- **What every program has is its glyph alone**: Find, − and +, Undo, Redo, Save in the bar above the work; the page
  before and after; More; and on the page of writing B, I, U, H1, H2, H3, ¶, {} and Aa. Its tip begins with its name.
- **What is particular to a page keeps its words beside its glyph**: Field, Copy citation, Review table, New note,
  Calculate and write report, Recalculate, Preview export, Edit cell, Open source row, New document, Export, Compare
  sources again, Stop. No drawing says "Copy citation".
- Under the pointer a button answers in green, with a little glow; pressed, chosen or holding the keyboard it is amber;
  when it cannot be used it is dim. The way back to the Field is green at rest, as it was.

Only how a button is painted and how wide it is change. Its words, its name for a screen reader, its tip, its click and
its place are the same, so the keys, Stacy, More and the checks still find it by its words; going back to Words gives
every button the width it had. The keys at the Field's foot are not changed: a key cap is already a letter.

The glyphs were drawn and looked at at their true size, 20 pixels, in pictures. They have not been seen on the
ThinkPad's panel, and nobody but their author has judged whether each one says what it means.

## A fault that could end the program (in 0.4.7 and 0.4.8)

Found while the icons were being checked, and not caused by them. The bar above the work looked at the open page the
instant the keyboard moved. A finding replaces its whole sheet when it is read again, and if the keyboard was on one of
its buttons (after a click on **Compare sources again**, say), the keyboard moved while that button was being
destroyed; the bar then read a page whose parts were half gone, and Qt ended the program with no message. The bar now
looks a moment after the move, never inside it. A probe reproduces the end of the program without the mend and runs
three replacements with it. 0.4.6 and earlier have no bar and were never exposed.

## What was questioned and kept, and why

- **A click opens a sheet, and the right button shows its menu.** Two roads to a sheet's actions remain: the foot (for
  the selected sheet) and the right button (for the sheet under the pointer). They are kept because the foot is the only
  visible one and the menu is the only one that reaches a sheet without opening or selecting it first.
- **Edit cell and the double-click** both change a cell. The button is the visible home; the double-click is its
  shortcut, as a key would be.
- **− + and Z on the Field's strip**, with Ctrl and the wheel: one visible home and its shortcut.
- **The name of what is open** is still said by the bar, by the tab when there are several, and by the writing line
  (where it says what "this" will mean to Stacy). The sheet's own title field is where the name is changed.

## What still repeats, and is the owner's to decide

- **The Work menu repeats most of the screen.** Save, Undo, Redo and Find are in the bar; Field, Files, Today, Settings,
  This Computer, the writing line's modes and Pin are all places on the screen; and Favorite commands is a list of
  repeats by design. A menu that lists everything is the usual way to find a thing by name, and several of the project's
  window checks read this menu, so it was not cut here. The clean answer is a Work menu that holds only what has no
  place on the screen. That is a pass of its own.
- **The Activity pane** has seven links, and most open things the menus also open (Explore, Work list, Organizer, Return
  thread, Service details). It was not touched.
- **The Engineering branch of the Work menu** (some seventy-five lines from one project) is hidden in a workspace that
  attaches no project, which is how an installed copy runs; it shows, dimmed, only where the program runs from its own
  source tree.

## What was checked, and what was not

A probe asks the running window for the facts above (no Open in the foot, no scrolling words, the faces once, Z once,
the strip hidden, Save dimmed with nothing to save and lit after a change, the PDF's size stepped from the bar, Desk
artwork once). The mouse path (open a sheet tile, change a cell, save with the bar's Save, come back, trace, approve) and
the keyboard walks pass at 1920 by 1200 and 1366 by 768. One of the cuts removed a small function the Field's clicks
depend on; the mouse probes failed at once and it was put back before anything was committed. The project's own tests
were run on the exact commit before this set was cut: see the set's START_HERE for the numbers.

The plates and the desk's light were looked at in pictures of the running window at both sizes, on every work page,
the Field, the table review, Settings, Machine and Talk; a probe switches the page's light both ways and reads the
brightest point of the page as shown (117 of 255 in the desk's light, 241 in its own). The low tone was chosen by eye
from those pictures, not on the ThinkPad's panel: if the page reads too dim or still too bright there, it is one value.

Not seen: any of it on the ThinkPad's own screen. No second reader has gone over this release. The owner reports
(13 November) that 0.4.6 is installed and running on the ThinkPad; nothing later has run there, and no account of what
was tried there has been recorded yet.
