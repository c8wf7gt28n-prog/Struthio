# What's new in Graphite 0.4.7

November 13, 2026. Guide → What's New opens this page. The 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3
notes beside it describe what came before.

Two things the owner asked for the same morning: "let's add some glow effects to the orange and anywhere else it would
enhance the mood", and "review and improve ui now that we're using mouse as primary input for graphite".

## Amber glows where it means something

The rule from 0.4.6 holds and is now lit on both sides. Green is what is live and whatever the pointer is over. Amber is
what has the keyboard and what waits for you.

- **One amber halo: where the keys go.** In the Field the selected sheet has an amber halo and its name is lit, while the
  Field has the keyboard. A page being read (a doubt, the brief, the keys) has it while it is read. The writing line has a
  lit edge above and below while you type in it. Only one of these shows at a time, so the amber light always answers
  "where will my next key go?".
- **What waits is lit at its mark.** A sheet that asks for a recheck, an open question, a held page: its mark has an amber
  light around it (never inside it, so a hollow mark still reads as hollow). The light outside a sheet stays for the hand:
  green under the pointer, amber for the keyboard. A sheet that waits can be under the pointer and say both.
- **A wire that asks for a recheck carries amber light**, as a live wire carries green. 0.4.6 said a stale wire carries no
  light; that is changed, because a waiting chain should be findable as a warm thread through the green.
- **Approve glows.** The Approve button at the foot of the Field glows amber while a change waits, and green under the
  pointer. In Talk, Approve was a bare word; it is now the same filled amber button, lit while it waits and plain once
  pressed, so one waiting change looks the same in both places. The DO box in Stacy's rail is lit while it holds something
  for you.
- **A lamp at the head of the Field** when anything on the desk waits, in view or not, beside the counts. Click it (or
  press A) to go to the next thing that waits.
- **The room.** A very low amber light rises from the foot of the Field and a lower green one falls from its head. They
  do not move and they say nothing.
- **The Clean desk has none of it.** The edges, marks and colours stay; every glow goes.

Left alone on purpose: the frame's two amber rules and the marks under the pane tabs. The project's desk check measures
their pixels against the grain, and lighting them would change what it measures. Reading text is not lit anywhere.

## The mouse first

**The centre has its bar.** Above whatever is open in the centre there is now one row of controls, always in the same
place: **‹ Field**, the name of what is open and whether it is saved, **Find**, **−** and **+**, **Undo**, **Redo**,
**Save**, **Actions ▾**. It is the first slice of the toolbar the whole-build specification asks for, and it is made of
actions Graphite already had (F9, Ctrl+F, Ctrl+Z, Ctrl+S, the Menu key), so the mouse and the keys still do one thing by
one road. A control the open view cannot serve is dimmed and its tip says why. − and + change the size of the open
table or writing, that view only. ‹ Field used to be at the far end of a strip under the page.

**The Field.**

- **Z shows the whole desk** in the window; Z again brings back the ordinary size. **+** and **−** make the sheets larger
  and smaller, and so does Ctrl with the wheel, about the pointer. At 1366 by 768 the case desk shows 3 whole sheets at
  the ordinary size and all 14 with Z. Clicks, the pointer and menus go by what is seen at any size.
- **Bars to drag.** When the desk runs beyond the window there is a thumb at the right edge and one along the foot of the
  sheets. Drag it, or click the track for a window's worth. Dragging the ground and the wheel still work.
- **The words that say where the desk goes on are places to click**: "↑ more above", "more below ↓", "← more",
  "more →", and beside them **−**, **+** and **Z**.
- **⋯ on the sheet under the pointer.** A left click on it shows what can be done with that sheet: the same menu the
  right button and the Menu key show, for the hand that does not think of the right button.
- **The faces** (Work, Programs, Network) answer the pointer and say what they are. The two keys in Stacy's rail (S and
  Shift+Enter) and a page's "more ↓" are places to click.
- **A double-click cannot press what it did not see.** A sheet opens on one click. If the hand double-clicks, the second
  click used to land on whatever the newly opened page put under the pointer. It is now dropped.

**The pages.**

- **A button is as wide as its words.** On the sheet page, the PDF page and the findings page, buttons are drawn as words,
  but each was pressed by a click anywhere in a strip up to half the page wide: a click on empty ground beside
  "Recalculate" recalculated. Twenty-three such buttons are now the size of their words.
- **Dividers** inside the document and PDF pages are 8 pixels wide (they were 4) and answer the pointer. **Tab close
  buttons** are 24 pixels a side (they were 20).
- **The hand-painted marks answer in green.** The words in the lower band, the pane tabs and the Log's tabs drew the same
  orange mark for "the pointer is here" and "the keys go here". The pointer's is green now.

## What was checked, and what was not

In the build container, with the window run offscreen at 1920 by 1200 and 1366 by 768, driven by mouse events: every
control above was pressed and did what it says; the 0.4.5 mouse path (open a sheet tile, change a cell, save, come back,
trace, approve) still passes; the keyboard walks still pass. The project's own tests were run before this set was cut:
see the note in the set's START_HERE for the numbers.

Not seen: any of this on the ThinkPad's own screen. The pointer still cannot be seen offscreen. How strong the amber
reads beside the green on that panel is for the first boot to show; every strength is a number that can be turned.

Not built: Find outside text files (the control is there and says so); a size control for the PDF page from the bar (it
keeps its own); the size chosen in the Field or in a view is not remembered between sessions; the same sheet in the full
application through Programs; an ordinary workbook as a citizen of the chain; Stacy working out the steps of a job. No
second reader has gone over this release: the review was started three times and stopped each time on the plan's usage
limit. Nothing has run on the ThinkPad.
