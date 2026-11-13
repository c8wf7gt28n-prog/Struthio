# What's new in Graphite 0.4.8

November 13, 2026. Guide → What's New opens this page. The 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and
0.3 notes beside it describe what came before.

The owner: "Should we do a ui pass to bring in buttons where useful. And simplify the interface. And also make it look
more complete and untied to the work."

The interface drew its actions as bare words. On a page full of the work's own words, "Recalculate" and "Copy citation"
read as more of the work, and the page looked unfinished. This release gives the interface its own look, apart from the
work it holds.

## A control looks like a control

One rule, in three parts:

- **An action is a button**: a boxed word. It answers the pointer in green and the keyboard in amber, and it is dimmed
  when it cannot be used now.
- **A word that only goes somewhere is an underlined word**: Service details, Open record, Brain room.
- **The work has neither look**: a page, a table and a sheet are never boxed or underlined by the interface, so the two
  are not mistaken for each other.

Where the buttons are now:

- **The Field's foot.** Enter, D, X, C, T, B, ? and Esc were quiet letters; each is a button, with its key still named on
  it. So are − and + and Z on the strip above them.
- **The sheet page.** One row above the sheet: **Calculate and write report…**, **Recalculate**, the export format with
  **Preview export**, and **More ▾**. Edit cell and Open source row are buttons.
- **The PDF page.** One row above the page: **‹ Previous**, the page number, **Next ›**, the size, **Copy citation**,
  **Review table**, **More ▾**. The four note actions are buttons.
- **The page of writing.** New document and Export…, and the row that shapes the writing (Bold, Italic, Underline,
  Heading, Subheading, Minor heading, Body, Code, Plain), are a row of buttons, as in any writing program.
- **The findings page.** Compare sources again and Stop are buttons, beside Continue.
- **Under the centre.** Working area and Ask Stacy are buttons.

## Simpler

- **The sheet page had eleven actions spread over six lines** above the sheet. Five are used every time and are in the
  row. The other seven (Save working, Review recovery, Prepare edit copy, Open editor, Review file, Save output copy,
  Compare BOM) are under **More ▾**, each with what it does, and when it cannot be done now, why not. The sheet itself
  starts about 160 pixels higher on the ThinkPad's screen. The standing sentence about working copies is the first line
  of More.
- **The PDF page had twelve actions in five lines.** Seven are in the row. Open citation, OCR this page, Check original,
  Export library volume, Share page view and Focus reading are under **More ▾**.
- **Nothing was taken away.** Every action is still there and does exactly what it did; More presses the same button
  the page always had.
- **The bar above the centre names what is open**: the PDF by its file name, a question by its own words, where it used
  to say the cabinet's section.

## Left as it was, on purpose

`poem` stays the empty hint in every writing place: the record of directions lists it among the small things that stay.
The side panes keep their words (most of them go somewhere, and are underlined). The Activity pane's wording, Talk and
Home are not touched in this pass.

## What was checked, and what was not

In the build container, with the window run offscreen at 1920 by 1200 and 1366 by 768: each rebuilt page was opened from
its tile and looked at; the More menus press the buttons they stand for, and a line that cannot be done is dimmed and
says why; a tool turns green under the pointer; the mouse path (open a sheet tile, change a cell, save with the bar's
Save, come back, trace, approve) and the keyboard walks still pass. The project's own tests were run on the exact commit
before this set was cut: see the set's START_HERE for the numbers.

Not seen: any of it on the ThinkPad's own screen. No second reader has gone over this release (the review stops on the
usage limit of the plan it runs under; it has not been tried again). Nothing has run on the ThinkPad.

Still not built: an ordinary workbook as a citizen of the chain; Find outside text files; the same sheet in the full
application through Programs; Stacy working out the steps of a job.
