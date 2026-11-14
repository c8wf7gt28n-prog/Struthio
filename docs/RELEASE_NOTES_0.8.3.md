# What's new in Graphite 0.8.3

November 14, 2026. Guide → What's New opens this page. The 0.8.2, 0.8.1, 0.8.0, 0.7.0, 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1,
0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what
came before.

This release is Kasandra's look, second pass, from your words of today.

## Her hologram, lower left

"We're going to move the kasandra picture to lower left column where it's boring looking ... I want to be like a hologram
in its new position. If you can animate the static a hologram would have that would be very kool."

- Kasandra stands under the Files tree, above DELETE, as a violet hologram on a projection base: your picture, with its
  transparent edges.
- **The static moves:** scan lines drift, the picture flickers softly, a rare tear crosses it, a faint colour split
  lives at its edges, and the base glows.
- **It shows her state:** quiet, at work (busier static, cyan base), waits for you (held almost still, pink base), done
  (honey base), stopped (red base).
- When the tree needs the room she steps aside; on the Settings tab she is not there. Reduce motion holds her still;
  the Clean desk shows no art (the ASCII desk draws her in characters).
- She costs about a millisecond a frame, around 1.4% of one core here, and her clock stops when she is hidden, when the
  window is minimised or inactive, and under the idle display.

## Her column, for her words

With the picture gone, her column starts with her name in the typewriter face, a cursor in the colour of her state, the
state in words, and her dial; her words take the whole width and height below, on her terminal ground. Long file names
break only where they must, at `_ . / -`, never in the middle of a word.

## Every word in her typewriter face

"I want all fonts to be the awesome LAIN font." In Kasandra every face is now her typewriter face: menus, trees, tabs,
cards, pages, documents, tips, the Field, her column, the writing line.

- Code, lines, numbers in tables and Terminal output use a fixed-width cut of the same face, made for Graphite from
  Special Elite (licence and hashes in `branding/fonts/typewriter/NOTICE.md`), so `ls -l` columns and box lines still
  line up.
- The one has a long sloped flag and the l a curved tail, so 1, l and I never blur, underlined too; 0 and O stay
  apart. Tested at 13 to 18 px against IBM Plex Mono.
- If you have chosen your own faces under reading, yours stay. Graphite keeps its Plex faces.

## DELETE

"I want trash called DELETE." The can at the foot of the left column says **DELETE**; the right-click's row is
**Delete**, and her words say "deleted". Its tip says what is there can be brought back, because it can: nothing about
how it works changed. A document's own "Delete" (removing the selected words) is now called **Erase**, so the two
never meet.

## Burnt yellow is the highlight

"I'm kinda thinking that highlighting should be in our burnt yellow??? Like especially in menus???" and "be careful how
that makes the graphite not look green". In Kasandra:

- **In menus** (across the head and dropped from it, the right-click and its line panel, Apps, the writing line's list)
  the row you are on is a solid burnt-yellow bar `#e2a72e` with dark ink `#171b3c` (7.8:1) and its glyph in the same
  ink.
- **Everywhere else** a highlight or focus is a burnt-yellow edge with yellow words: selected rows, tabs, checked
  buttons, focus, the keyboard's place.
- **Never green.** Yellow laid thinly over her cyan or blue turns green, so the yellow is opaque wherever it fills, and
  where it glows it adds light instead of mixing. The mouse pointer's halo is pale violet in Kasandra, because its cyan
  halo over the yellow bar measured green; now 0 green pixels under it.
- Graphite's amber and green are exactly as they were.

## The neon kp logo, the only kp mark

"New logo for our upper right progman.exe menu ;)" and "Retire any other kp icon". Apps, in the head's upper right, is
your neon logo: the clean drawing from your file, about 44 px tall, with a neon glow Graphite draws around it in cyan
and magenta. It follows the Glow setting (brightest at Neon) and catches with the menus. Your file's own halo lives in
almost transparent pixels, so drawn honestly it would vanish; the drawn glow gives it back crisply. Every other kp mark
(the 0.8.0 monogram, the cream emblem) is gone, and the window's icon is Graphite's sharpened point again.

## What is not done

- Nothing later than 0.4.6 has run on the ThinkPad. The hologram's static, the faces and the yellow were judged from
  frames taken offscreen, by the ones who built them.
- Known small things from the last review, not yet fixed:
  - the yellow glow around the writing line's edge and the Field's selected sheet reads greyer than the yellow edge itself;
  - a few lists that set their own colours (the process list, the Log, Explore, the cabinet, Documents) still show the old
    fill under the yellow edge;
  - the PDF evidence highlight is a see-through yellow over the page;
  - the sheet's Run button shows focus in cyan.
- Kasandra's hand on the desk (her door, the planner, the stop) and the test clean-up were stopped half-way for this cut;
  they continue next.
- Twenty focused tests still fail as before (they assert an earlier look, layout and version); the clean-up is solving or
  retiring every one.
