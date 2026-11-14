# What's new in Graphite 0.8.2

November 14, 2026. Guide → What's New opens this page. The 0.8.1, 0.8.0, 0.7.0, 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1,
0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what
came before.

## The desk can be driven by name

This release lays the ground for Kasandra's hand on the desk. Until now only a person could drive the window: open the
Field, select a sheet, right-click and choose a row, carry a line through Then, zoom, read back what is open. Now each of
those is a **desk act** with a name, and the window does it the way your hand would.

There are 40 acts in ten families: **go** (the Field, Today, Files, a sheet, one of the Apps, back), **point** (select a
sheet, move the selection, zoom), **head** (open a menu across the head and read it, choose a row that goes somewhere,
open a meter's card), **menu** (the right-click: open it, choose a row, close it), **then** (the line panel: keep rows,
count, take a step off, end the line), **sheet** (trace, doubt, compare revisions, what-if, the steps, put away what is
shown), **type** (put words in the writing line, give it room), **hand** (her changes), **look** and **read**.

**Try them in the writing line.** Type `/help acts` for the list, with what each one does. Then, for example:

```
/go.field
/point.sheet title="07 Bench readings"
/sheet.trace
```

The Field comes to the front, the sheet is selected, and Trace crystallizes along its wires, as if you had clicked. Most
acts take `by=pointer` (it moves and clicks as a mouse would) or `by=keys` (it presses keys); `/help sheet.trace` shows an
act's arguments. A line that runs an act reads **Act** in the list under the writing line, beside **Operation** for the
Kernel's operations.

**What keeps it safe.**

- An act that **navigates** changes nothing: it opens, selects, zooms or reads back. In the right-click and the menus
  across the head it chooses only rows on a written list of rows that go somewhere, show, read or copy. A row that
  changes a record, leaves Graphite, asks her model or opens a window that asks stays yours.
- An act that **changes** something (`hand.write`, `hand.rename`, `hand.trash`, `hand.cell`, `hand.step`) goes through
  her hand exactly as a change asked of her does: its card, its line in her trail, its one Undo. What always asks still
  asks, and a file that already exists waits for your Approve whatever the dial says.
- Five acts are **yours only**: approve, undo, the dial, the appearance (`look.set`), and sending what the writing line
  holds (`type.send`).
- Words put in the writing line are typed one character at a time, so Ω, ≥ and 電流 arrive as written; a line break or
  an invisible character is refused, so an act can never press Enter by accident.

Nothing offers the acts to her model yet. Her rule for them is written and tested, and the next pass gives her the door.

**The playable scene.** Your "Graphite after hours" closes with one scene in After Hours 07, "by mouse and keyboard, with
reduced motion". It is P01, a script of seventeen acts: Tools across the head; write a CSV through her hand; Then over it
in Files (keep the rows in mA, count, put the line in the writing line); the Field; trace 07 Bench readings to its two
powers; compare Limits Rev A with Rev B; Undo. `python3 tools/campaign.py run --set scenes` plays it four times on your
backup, by pointer and by keys, each again with Reduce motion on, and checks every step against what the window reads
back (docs/CAMPAIGN.md, "The playable scene"). Here it passes 4 of 4 at 1920×1200 and at 1366×768.

**An independent review** went through the acts before this release and found eleven problems, among them an act that
could type a line break into the Terminal, rows that changed a document or opened a file outside Graphite while calling
themselves navigation, and a what-if that asked the model. All eleven are fixed, and each fix has a test; a sweep runs
every navigating act on a live window and checks that no record changed, nothing opened outside and no program started.

## Kasandra in her typewriter face

You asked for "as much font in that LAIN font as what looks kool, but still readable". In Kasandra, Special Elite is now
the face of the window's words: the menus across the head and every row dropped from them, the right-click, Apps, the
tabs and the trees, buttons, her column, Home's cards, the names on the typing strip, table headers and section labels,
and the Field's cards and column titles. Card titles are set a hair smaller and tighter (97%, with the letters pulled
in) so a long title breaks between words, not inside one. What has to be read exactly stays in the clear monospaced
face: the typing line itself, lines and code, addresses, the numbers on cards and in tables, and the small tags, so 0
and O, 1, l and I never blur. If you have chosen your own faces under reading, yours stay. Graphite keeps IBM Plex Sans.

**Apps is the kp mark alone.** "Probably don't need to call it Apps menu, just a bigger kp icon." In Kasandra the head
shows the kp monogram at 36 px (it was 24, beside the word), with no word; it opens the same list, and its tip still
says Apps. Graphite keeps "[#] Apps".

## After hours: the desk responds

From your "Graphite after hours": "Then you touch the machine and it responds with a little more force than you
expected." Each effect follows the brief's rule: it helps you work, it never slows a hand that knows the way, and with
**Reduce motion** on (or the Clean glow) it lands straight on the settled frame.

**Trace crystallizes along the wires.** Trace a sheet, a source or a finding in the Field:

- A white point, small enough to almost miss, leaves the farthest source and follows the wires already on the desk.
  Both branches of a fork light as the signal reaches them.
- Where a wire meets a card, a few facets catch, like pencil lines through bright glass. At the end of the route they
  fan out, and the light spills into the gap before the card, never over its face, so the numbers stay readable.
- Then the light drains away, the middle of each wire first, leaving a fine line along the route that you can study
  until you select something else.
- About 700 ms of travel, a 150 ms peak and half a second of decay, as the brief suggested; they are starting points to
  tune on the ThinkPad.
- The test the brief set: trace **07_Bench_Readings.pdf** in After Hours 07, and the two findings it supports light up
  while "Rev A allowed 120 ms" stays dark. You can see at once which findings share a source.

**Menus catch as they open.** For 150 ms a violet tracking band, with a bright line at its heart, crosses the second and
third rows; a cyan ghost shows on the far edge; the frame lights and settles. A child menu (Then, More) catches from the
side its parent is on, as if the signal continued from one box into the next. It is light only: the menu answers your
keys and clicks from its first instant, so opening Then and choosing in one motion does exactly what it always did.
The menus across the head (Tools, Rules…) and the desk's own (the right-click, Apps) all catch.

**A line lands.** When a line goes into the writing line (Put it in the writing line), the line's edge lights for a beat:
you feel where it went, with no banner.

**REV A / REV B.** A reviewed sheet that has another revision on the desk offers **Compare with Rev A** under More
(Look into it). The Field cuts straight to the two side by side:

- **REV A / REV B** in the desk's display face, under the same row and column guides;
- each changed cell with a fine pink edge, the earlier value lifted just above it in violet;
- the selected row's change in plain words ("Pulse duration: value 120 ms in Rev A, 80 ms in Rev B").

Values stay in the clear face, so 1, l and I never blur. Up and Down move along the rows; Esc, or a click beside it,
goes back to the Field. On After Hours 07 the cut shows Pulse duration going from 120 ms to 80 ms, and the pulse
ceiling's condition from "Up to 120 ms" to "Up to 80 ms". The open question stays pink until the case answers it.

## Also

- **The writing line's results go when you leave the line.** After **Put it in the writing line**, the list of what the
  line can do opened under it and stayed there, over the Field, after you clicked into the Field. It now goes as soon
  as the line is left for other work; the words stay in the line, and the list comes back when you click the line
  again. The playable scene found it.

## What is not done

- Nothing later than 0.4.6 has run on the ThinkPad. The timings, the brightness and the catch were judged from frames
  taken offscreen at fixed moments of their clocks, by the one who built them; how they feel at the keyboard on your
  panel is the real test.
- The acts are not offered to her model yet: no door for her, no word forms ("open the Field"), and no way in from
  outside Graphite. The menus across the head have no keyboard route, so an act played by keys opens one by pressing
  its word directly.
- Not tested yet: a successful what-if and `hand.cell` (the test sheets hold words where a number would be), the change
  path of `hand.step`, and `type.send`. A changing call made during a navigating act is recorded in the act's result,
  not stopped, because the window's own timers can make one.
