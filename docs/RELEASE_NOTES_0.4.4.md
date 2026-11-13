# What's new in Graphite 0.4.4

November 13, 2026. Guide → What's New opens this page. The 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it
describe what came before.

This release adds no power. It is a pass over what the earlier ones built, made by looking at the real screens the way
someone meeting them for the first time would: can I read this at a glance, and do I know what to press? Four things got
in the way, and each is put right.

**? shows every key.** On a small screen the foot of the Field had room for four keys, so X, T, B and C could not be
found. Press **?** in the Field for a card of every key, grouped by what it is for (move, open, ask, do), one line each.
The foot now always keeps "? keys", whatever else gives way, and an empty Field says it too.

**An answer is read where your eyes are.** Stacy's column is narrow, and an answer of several rows was hard to read
there: on a small screen the doubt you asked for was below the fold. Three answers now open on a page over the work, at
your reading size:

- **X**, the doubt: grouped as what does not hold, what she cannot tell, what is worth knowing, what holds.
- **C**, the desk check: what waits for you with its next step, and what looks right that she doubts.
- **B**, the brief: the whole page, to scroll, as it would be kept.

The doubt and the desk check are light pages: they step aside at the next key, and that key does what it always does.
An arrow moves on, D offers what can be done, 1 settles the desk, A goes to the next thing that waits. Esc closes them.
The brief and the key card are for reading: the arrow keys scroll them, G keeps the brief, Esc closes. Talk still gets
each answer as a card, with its links, so nothing is lost from the record. The page gives up its margins when a large
reading size meets a small screen, so it still reads at 28 points on 1366 by 768.

**Talk reads at a glance.** In Stacy's column:

- When the rows are the whole answer (a doubt, a what-if), they come first and the staC line that read them comes after,
  smaller. Before, the line and a long introduction pushed the answer out of sight.
- A doubt is written as its verdict and question on one line and the reason under it; a what-if as the thing, then what
  it says now and what it would say, then why; a trace as an arrow, the kind, the name and the wire's word.
- Long record numbers in a shown line are shortened as the Field's rail shortens them. The line itself is exact: it is
  what runs, what "in the line" gives, and the label's tooltip.
- Introductions are a line, not a paragraph.

**Two labels no longer collide.** During a what-if on a small screen, "what if … · Esc clears" ran into "more above ·
more below" under the sheets. What is being said is now written whole and the scroll words take what room is left. While
a what-if marks the selected sheet, the foot gives its last line to the what-if.

**Not done, said plainly.** Nothing here has run on the ThinkPad; all of it was judged on screens drawn offscreen in a
build container, at 1920 by 1200 and 1366 by 768, and at reading sizes up to 28 points. Nobody but the builder has looked
at these screens: the judgment of whether they read well is one person's, and yours on the real panel is the one that
counts. Stacy's column itself is as narrow as it was, and Home was left as it is.
