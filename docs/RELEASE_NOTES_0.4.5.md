# What's new in Graphite 0.4.5

November 13, 2026. Guide → What's New opens this page. The 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside
it describe what came before.

The owner's second whole-build specification says where the last releases had drifted: more of a computer that shows its
work than one to sit down at and use, with the mouse, and hand a part of the job to Stacy. This release is the first
journey through that, and it is the specification's own first demonstration: with the mouse alone, open a sheet tile,
change a cell, save, come back to the same tile, trace the calculation and approve its recheck. Then the same change,
asked of Stacy in words.

**The mouse does what the keys do.**

- **A click opens a tile** in the centre and makes it the selected one. The right button selects the tile under the
  pointer and shows its menu. Dragging moves the surface. The tile under the pointer shows its wires and its whole name.
- **‹ Field**, in the bar under the centre, comes back to the Field at the tile you opened, with the view where you left
  it. It is F9 as a button, and it is there whatever is open.
- **Every key the Field shows is a place to click**: the keys at its foot, the rows of the key card (?), the steps, the
  keys at the foot of a page.
- **Approve is a button.** A change that waits shows an Approve button at the foot of the Field with what it would do and
  to what. Clicking a step or an action only puts the change up; clicking Approve applies it. G approves the same
  change. In Talk the button that was called Run is called Approve.
- **Pages have a Close**, at the top right, and their own keys are places to click.
- **D shows the steps on a page** whose rows are the steps, each with why and whether it waits for your Approve. Click a
  row or press its digit. On a small screen the steps used to run off the end of one line.

**Ask Stacy to change a number.** With a sheet or a calculation selected: "set B3 to 300", or by the row's words, "set
the startup current to 700". She puts the change up with its exact line, the Field marks what it would move (the what-if,
shown before the fact), and nothing is changed until you approve. Approving saves the sheet through the same save your
own edit uses, and what was worked from it waits for a recheck. In staC terms the what-if (`field.ripple`) is the read and
`field.set` is the change it previews.

**Put right.** Asking Stacy anything while a sheet's page was the open item in the centre raised an error (the page keeps
a cell box under a name the question looked up). It no longer does.

**What the demonstration showed, and what it did not.** At 1366 by 768, driven by mouse events with no key pressed: the
tile opened the sheet, a cell was changed from 280 to 300 and saved, ‹ Field came back to the same tile, the calculation
showed recheck, the trace was reached through the key card, the step and Approve were clicked, and the calculation was
worked again to 3.6 W. Stacy's change of another cell was approved with a click and the record changed. Not shown,
because it is not built: the same sheet opened in the full application through Programs and its saved revision coming
back; zoom and fit for the Field; the centre's common frame and toolbar (the sheet still opens in its existing page, where
a cell is changed in a dialog and the grid has little room). An ordinary workbook brought in from a file still cannot
feed a calculation; only a sheet reviewed from a PDF can. Stacy's part here is one change you describe exactly; working
out the steps of a job is not built. Nothing has run on the ThinkPad.
