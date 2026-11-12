# What's new in Graphite 0.4.1

November 12, 2026. Guide → What's New opens this page. `docs/RELEASE_NOTES_0.4.md` describes the doing (D, G, C).

The owner asked: "Can we make staC and Stacy more powerful in creative ways". Three things, each built on what was there.

**staC can read the desk.** Until now a staC line could read any record but not the desk made of them. Three new reads
change that (`workbench/field_service.py`); they change nothing and add nothing to your timeline:

- `field.read` is the Field as records: its objects, its wires, what waits, what changed lately.
  `field.read | pick waiting | select kind,title,state` · `field.read | pick objects | where lately=yes | select kind,title,changed_at`
  · `field.read | pick links | where stale=yes | select from,to,label` · `field.read | pick objects | group kind | count`
- `field.trace {"id":"…"}` is where one thing comes from and what rests on it, hop by hop along the wires.
- `field.whatif {"id":"…","set":{"B3":"320"}}` is a calculation worked again with other values for some inputs.

The empty place of the Field offers the first three in its "This face in staC" menu. The picture and a line can never
disagree: both are the same reading.

**`this`.** In the writing strip, `this` at the start of a staC line is the sheet selected in the Field. Alone it is that
sheet's own line; `this | pick … | select …` goes on from the same record. The line is written out before it runs, so what
ran is what shows. With nothing selected it says so and runs nothing.

**T: trace.** Press **T** on a sheet (or Trace it in its menu, or the Trace step under D). Stacy shows the path: the source
and its page, the sheet and its cells, down to the thing, then what rests on it. With a model loaded she then tells it in
a sentence or two, from those rows.

**What if.** Select a calculation and ask in plain words: "what if B3 were 320?", or "what if the settled current were 320
and voltage 11.4". Stacy works the calculation's own recipe with those values, exactly, and shows what the page says now,
what it would give, the exact fraction, and that nothing was changed. Inputs are named by their cell, their symbol or their
words. It is a read: the sheet is not touched, and no model is needed for the number. With a model she adds it in words.

**Small things.** Several rows of several fields show as compact lines in Talk. A question that names its thing exactly
(a menu, T, a what-if) goes to Stacy and is no longer offered to the open page first.

**Not done, said plainly.** Nothing here has run on the ThinkPad; all of it was checked offscreen in a build container,
with a 2B model on a processor for the parts that use one. The what-if keeps each input's own unit: it does not yet take
"320 mA" or another unit. `this` is one word: there is no "these", and no way yet to name a line and use the name in
another line. The trace follows the wires the Field draws, so a link the records do not hold is not in it.
