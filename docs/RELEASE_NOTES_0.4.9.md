# What's new in Graphite 0.4.9

November 13, 2026. Guide → What's New opens this page. The 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1
and 0.3 notes beside it describe what came before.

The owner: "Really question what everything does and if it's place is justified. Every click necessary. No redoing the
same thing multiple places."

This release adds nothing. Every control on the main surfaces was listed from the running program with what it does, and
each was asked two questions: does anything else on this screen already do this, and would anyone miss it. The rule the
cuts follow:

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

Not seen: any of it on the ThinkPad's own screen. No second reader has gone over this release. Nothing has run on the
ThinkPad.
