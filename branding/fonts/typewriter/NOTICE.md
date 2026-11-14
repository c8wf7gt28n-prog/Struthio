# Display font (the Kasandra appearance)

Special Elite is bundled unmodified under the Apache License, version 2.0 (SpecialElite-LICENSE.txt). Font name and
copyright belong to their owners (Astigmatic One Eye Typographic Institute). It is kept so that a face the owner chooses in
the reading settings stays available; the window itself is drawn in the two faces derived from it below (0.8.3: the owner
asked for every face in the typewriter face): Kasandra Elite for the words of the Kasandra appearance, and Kasandra
Elite Mono for what must be read exactly and line up there (the typing line, lines and code, Terminal, addresses, numbers
in a table, small tags). Graphite's own appearance stays in IBM Plex.

Not the Special Elite font; its name is not used for the derived faces.

## Derived faces (Apache License 2.0, section 4(b): the changes, stated)

Both were built from SpecialElite-Regular.ttf (the SHA-256 below) by `tools/derive_typewriter.py`, which reproduces them
byte for byte. They are distributed under the same Apache License 2.0, with its copyright and licence notices kept in
their name tables (IDs 0, 13 and 14).

- KasandraElite-Regular.ttf (family "Kasandra Elite"): changed are the glyphs zero to nine and l only. The zero carries a
  slash across its counter; the l stands on a right foot only (the left half of its foot cut away); every digit is 1254
  units wide with its drawing centred (tabular figures), and no kerning pair between two digits is kept (the kern table
  and GPOS pair kerning). The names (IDs 1, 3, 4, 6, 10, 16 and 17) are its own. Every other glyph, its metrics, the
  hinting programs and the layout tables are unchanged.
- KasandraEliteMono-Regular.ttf (family "Kasandra Elite Mono"): the glyphs of Kasandra Elite on one fixed pitch of 0.6 em
  (1229 units), each centred in its cell and, if wider than 1189 units, narrowed about its own centre; IBM Plex Mono's
  line (ascent 2099, descent 563 per 2048 units, no line gap); no kerning, ligatures or hinting programs (kern, GPOS,
  GSUB, fpgm, prep and cvt removed); fixed-pitch flags set; its own names.

Source: the owner's Kasandra pack (Pass 02, fonts/), a copy of the Google Fonts release.

- SpecialElite-Regular.ttf · SHA-256 a776fcb4ceb8bdf03e2967688ebdad42680de5b91a7e62c17e718ae212d14bc4
- SpecialElite-LICENSE.txt · SHA-256 cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30
- KasandraElite-Regular.ttf · SHA-256 7cde3cea161199f2d2eaaf1ec9c0527d2bb048301fdebf48feb10c01d8391360
- KasandraEliteMono-Regular.ttf · SHA-256 1fe883c0a281154dcaa42d2191a32702b0cf509c635e7eea4a4c3f250cd219a7
