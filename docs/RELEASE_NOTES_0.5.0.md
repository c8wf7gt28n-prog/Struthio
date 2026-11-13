# What's new in Graphite 0.5.0

November 13, 2026. Guide → What's New opens this page. The 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1,
0.4, 0.3.1 and 0.3 notes beside it describe what came before. 0.4.9 was never cut as a set of its own: everything in it
(the audit, no white boxes, icons as an option, the mended fault) is in this one, and its notes still describe it.

The owner: "If there is anything that you want to add or subtract or change in the program, in the ui, desktop,
interface, options, under the hood, deep inside, whatever. Turn off all my rules, and don't hold back."

And, the same evening: "But mostly focus on how it looks ... and fun to use. Think apple simplicity but still very
powerful. ... ill stop and let you do it your way :)"

So what is here was chosen by the builder, not asked for line by line: first a pass over how the window looks at rest,
then three things that were missing or did not work, and one hunt under the hood.

## How it looks

The rule of the pass: **at rest the window shows names and pictures, and the machinery is one move away.** Nothing was
taken out of the program; several things stopped being the first thing seen.

- **The head of the window says a name.** It used to show the address of what is open, and for a page opened from a
  record that is `graphite://open/5ab8a3fd7bb342f9…`: honest, typeable, and no use to a person. Now it says the name
  ("07_Bench_Readings.pdf"), then quietly the room it is in and whether it is saved ("Preview · PDF", "Documents · not
  saved yet"); in the Field it says "The Field". **Click it, or press Ctrl+L, and the address is there**, whole and
  selected, to read, copy or type over, exactly as before; Esc puts the name back. Its tip always carries the address.
- **The name is said once.** The bar above the work no longer repeats it beside the controls: the bar is the way back
  to the Field on the left and six controls on the right, and nothing else.
- **Tools are icons at first sight.** A workspace that has never chosen opens with the drawn glyphs and no boxes;
  **Work ▸ Rules ▸ Buttons ▸ Words** brings back the worded plates, and the choice is kept. (0.4.9 opened with words;
  the owner asked for the look first.)
- **Stacy is the first thing on the right**, with her face and what she can be asked, not the ledger of services.
  Activity is one word away.
- **Z glides.** The desk draws back to show all of itself, or comes near again, in about a fifth of a second instead of
  a cut, so the eye keeps its place on it. With "reduce motion" on it changes at once, as before.
- **Fine print is fine print.** The two lines of a PDF page's identity (its physical page, labels and SHA-256) are
  drawn faint: there to be read when wanted, not the first thing seen.

What this pass did not do, and would be next: the Activity pane is still a wall of small words; the tab row still says
"Pin / Unpin"; the sheet page still shows three lines of status under the table; Home was not touched.

## The whole desk is a map

**Z** has shown the whole desk in the window since 0.4.7, and from that far the words on a sheet were five pixels high
and said nothing: a wall of small grey boxes. Now a sheet seen from far off is drawn as a map draws a town:

- **the glyph of its kind** (a source is a page with its corner folded, a sheet is a table, a calculation is the sum, a
  page of writing is the pencil, a finding is a ticked cell of the lattice, a question is the question mark, and so on
  for all fourteen kinds: the same hand that drew the tool icons),
- **its name, in letters that stay large enough to read** however far away the desk is,
- **its state's mark in the corner**, with the same light it has near to: green for what is current, amber round what
  waits for you.

The names of the columns keep their reading size too. Nothing else changes: the arrows walk the map, a click opens a
sheet, the selected sheet has its amber halo, a what-if still marks what it would move. Nearer than 60 per cent the
sheets are drawn as they always were.

With icons (what a workspace opens with), the glyph also leads the kind's word on a sheet seen near to; where there is no room
for both, the glyph stands alone rather than half a word beside it.

## Find works on every page

Find in the bar above the work was dimmed on the sheet, the PDF, the page of writing and a finding, with the words "This
view has no find of its own yet"; in a text file it opened a dialog. A control that is dimmed on most pages is a hole
in the bar.

**Find** (or Ctrl+F) now opens one line under the bar's controls, on whatever is open:

- a passage of writing or a text file: the words are selected, one place after another;
- a sheet: the cells of the table (a hidden row is not searched);
- a list or a tree: its rows;
- a finding: its lines, with an amber rule round the line that was found;
- a PDF page: the words of the page (the native text; the OCR's words when that tab is the one showing). The page's
  tab of words comes to the front. It searches the page that is open, not the whole file: that is not built.

**Enter** or **Next ›** goes to the next place, **Shift+Enter** or **‹ Before** to the one before, **F3** steps too,
**Esc** or **Close** closes the line and gives the keyboard back to where it was. The line says "3 of 17", or "not
here". Finding changes nothing: it selects and scrolls. When another page comes to the front the line closes, because
its words were for the page before.

## The Field is seen as it was last seen

The size of the desk (and whether the whole desk was asked for) is kept between sessions. It was one of the gaps
listed since 0.4.7.

## Under the hood

- **A crawler pressed every control.** After the fault found by accident in 0.4.9 (the bar reading a page while its
  parts were being destroyed), a probe now opens each of five work pages and presses every control and every line of
  every More menu a hand could press, one at a time, coming back each time, then presses the right button on the page,
  then puts the keyboard on each control in turn and opens the page again. Dialogs that come up are named and closed.
  On this release: see the set's START_HERE for the counts. It found nothing further; the fault it was built to find
  is the one already mended.
- **Sixteen tests for the new parts** (`tests_integrated/test_faces_find_light.py`): every glyph draws inside its box
  and leaves the painter as it found it, every kind of sheet has a glyph, a button's words and widths survive the
  change to icons and back, Find's search of writing, tables, lists, trees and pages of words, the page in the desk's
  light (white comes down, black stays black, the picture given is untouched), and what the session keeps.
- **The README's list of what is new** had one bullet run into another in the 0.4.9 commit. Mended.

## What was thought about and left for the owner

These are the builder's proposals, in the order he would take them; none is done.

1. **The Work menu, pruned to what has no home on the screen.** It still repeats most of the screen (see the 0.4.9
   audit). Several window checks read it, so it is a pass of its own.
2. **Find across a whole PDF**, and Find in the Field itself (type a name, the map lights the sheets that carry it).
3. **The twenty old tests** that still assert the earlier look, brought up to the look there is, so that the whole
   suite is green and a new failure is seen at once.
4. **The journey**: an ordinary workbook feeding a calculation; a full program opened from Programs and its result
   carried back to the Field; Stacy working out the steps she does not have.
5. **On the ThinkPad**: what is slow there decides what is rewritten first.

## What was checked, and what was not

Probes run the real window offscreen at 1920 by 1200 and 1366 by 768: the look (what the head says on four pages and
in the Field, the address on a click, the glide seen frame by frame and its absence when motion is reduced, icons and
Stacy at first sight), the map (Z, the arrows, the programs face, + and
−, back to near, the zoom written to the session file), Find on five pages (lit, opens with the keyboard, counts,
steps both ways, "not here", Esc, Ctrl+F, F3, closing when another page comes forward, and a finding replacing its
sheet while the line is open on it), the icons, the plates, the page's light, and the earlier mouse and keyboard walks.
The project's own tests were run on the exact commit before this set was cut: see the set's START_HERE for the numbers.

Not seen: any of it on the ThinkPad's own screen. The glyphs, the map and the low tone of a page in the desk's light
were judged from pictures by the one who made them. No second reader has gone over this release. The owner reports
(13 November) that 0.4.6 is installed and running on the ThinkPad; nothing later has run there.
