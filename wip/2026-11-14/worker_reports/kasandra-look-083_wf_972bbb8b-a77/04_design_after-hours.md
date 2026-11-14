# Kasandra 0.8.3: design for DELETE, one typewriter face, her hologram lower left, her column, the kp emblem

Angle: after hours, bold. Kasandra appears as a projection in the lower left and her column reads like her terminal. Every word stays readable, and every effect stops when it should.

**Evidence I made and checked.** All of it is in scratch; nothing under `/home/user/Struthio` was changed.
- A working prototype of the fixed-pitch typewriter face. Qt reads it as fixed pitch, and its width per character is identical to IBM Plex Mono.
- A working colour-to-alpha cut of the kp emblem, with no navy fringe.
- A hologram renderer laid onto the real left-column frames at both window sizes, with its cost per frame measured.
- A mock of the right column at 1366×768.

Paths are listed at the end.

---

## (a) DELETE

### The word and its casing
- **DELETE** is the name of the place, always in capitals, like a word stamped on the can. It takes no article: "in DELETE", never "in the DELETE".
- Add `locations.DELETE = 'DELETE'` and `locations.OLDER_DELETE = ('Trash',)`, the same pattern as `INGRESS` / `OLDER_INGRESS`.
- It applies in **both appearances**. In Graphite it is drawn in IBM Plex Sans 16 px with letter spacing +0.8. In Kasandra it is Special Elite 16 px with letter spacing +1.0, in `RED`, with the existing glow.
- Internal names do not change:
  - the operations `files.trash`, `files.trash_list` and `files.restore`;
  - the act `hand.trash` and the reply field `trashed`;
  - the row key `'trash'` and the destination `'trash'`;
  - the `.trash` folder and the `files_trash` table;
  - the undo line `/files.trash {...}`.

**One word, one meaning.** These rules go into the vocabulary test:
- **DELETE** is the place that gives things back. To "delete" means to move something there.
- **Erase** means gone for good, and it always asks first.
- **Remove** means taken out of a list; nothing is lost.

### Exact strings

| file:line | now | becomes |
|---|---|---|
| trash_can_qt.py:51 | name `'Trash'`; tip `'Trash · deleted files wait here and can be put back · drop files here'` | name `'DELETE'`; tip `'DELETE · deleted files wait here, and Restore puts them back · drop files here'` |
| trash_can_qt.py:64, :120 | the measured and drawn word `'Trash'` | `'DELETE'` (word font gets `setLetterSpacing(AbsoluteSpacing, 1.0*scale)` in Kasandra, `0.8*scale` in Graphite) |
| trash_can_qt.py:63 | count in SANS 13 | count in `boss_theme.CELLS` 13 (Kasandra) |
| context_menu.py:498 / files_qt.py:367 | `'Moved to Trash. Restore it from Trash.'` | `'Moved to DELETE. Restore puts it back.'` |
| context_menu.py:499 | `'Moved %s to Trash · Trash puts %s back.'` | `'Moved %s to DELETE · Restore puts %s back.'` |
| context_menu.py:673 | `'Move to Trash'`, tip `'Trash keeps it; Restore puts it back'` | `'Move to DELETE'`, tip `'DELETE keeps it; Restore puts it back'` |
| context_menu.py:703 | `'Move to Trash'` | `'Move to DELETE'` |
| context_menu.py:740 | `'Files keeps its own changes: rename, versions, export, Trash'` | `'… rename, versions, export, DELETE'` |
| context_menu.py:2924 (FOLDED) | `('Files: a selection', 'Move to Trash', 'file', 'trash')` | `('Files: a selection', 'Move to DELETE', 'file', 'trash')` |
| files_qt.py:478 (the old menu: built, not shown) | `'Move to Trash'` | `'Move to DELETE'`. It changes together with :673, :703 and :2924, so `test_nothing_is_lost_from_the_old_menus` holds. |
| files_qt.py:107 (KEPT) | `"… and deletions go to Trash."` | `"… and deletions go to DELETE."` |
| files_qt.py:109 | `'… Deleting moves to Trash, '` | `'… Deleting moves to DELETE, '` |
| files_qt.py:334 | `'Move this working copy to Trash? …'` | `'Move this working copy to DELETE? %s is not touched, and the record of the work is kept.'` |
| files_qt.py:335 | `'Moved the draft to Trash. The original is unchanged.'` | `'Moved the draft to DELETE. The original is unchanged.'` |
| files_qt.py:499, :505 | `'Trash'` | `'DELETE'` |
| files_qt.py:507 | `'Nothing is in Trash.'` | `'Nothing is in DELETE.'` (the second sentence stays: `'Everything here can go back where it came from.'`) |
| shell2.py:1179 | `('Trash', 'trash')` | `('DELETE', 'trash')`. Search also matches every word in `OLDER_DELETE`, so a hand that types "trash" still lands there. |
| working_copies.py:275, :303 | `'Working copy missing (moved or in Trash)'` | `'… (moved or in DELETE)'` |
| working_copies.py:386, :511, :538; working_folders.py:133 | `'COPIES_WORK_MISSING: … put in Trash'` | `'… put in DELETE'` |
| files_service.py:94 | `'FILES_RESERVED: use Trash and versions …'` | `'FILES_RESERVED: use DELETE and versions through their own words'` |
| files_service.py:210 | `'moved to Trash'`, `'restored from Trash'` | `'moved to DELETE'`, `'restored from DELETE'` |
| files_service.py:510 | `'In Trash. Restore puts it back.'` | `'In DELETE. Restore puts it back.'` |
| tail_words.py:13 | `'Moved to Trash'`, `'Restored from Trash'` | `'Moved to DELETE'`, `'Restored from DELETE'` |
| shell2.py:2069 | `'Done: “%s” is in the Trash, which gives it back.'` | `'Done: “%s” is in DELETE, which gives it back.'` |
| shell2.py:2118, :2192 | `'“%s” is in the Trash, which gives it back.'` | `'“%s” is in DELETE, which gives it back.'` |
| shell2.py:2143, :2145 | `'… Move it to the Trash yourself …'` | `'… Move it to DELETE yourself if you want it gone'` |
| shell2.py:2262 | `'… to the Trash if you do not want it.'` | `'… move that folder to DELETE if you do not want it.'` |
| shell2.py:2269 | `'Move the whole folder to the Trash, which gives it back, …'` | `'Move the whole folder to DELETE, which gives it back, while it is still as I made it'` |
| shell2.py:2324, :2325 | `'… Undo moves it to the Trash'` | `'… Undo moves it to DELETE'` |
| desk_doers.py:1261 | `'Move “%s” to the Trash'`; `'the Trash keeps it and gives it back'` | `'Move “%s” to DELETE'`; `'DELETE keeps it and gives it back'` |
| desk_doers.py:1263 | `'moved “%s” to the Trash'` | `'moved “%s” to DELETE'` |
| desk_acts.py:159 | `named("Move a file in Files to the Trash through Stacy's hand; the Trash gives it back.")` | `named("Move a file in Files to DELETE through Stacy's hand; DELETE gives it back.")` |
| stacy_hand.py:53 | `'the Trash, once emptied, cannot be brought back'` | `'DELETE, once emptied, cannot be brought back'` |
| stacy_start.py:153 | `'- To be rid of it, move the folder to the Trash, which gives it back. …'` | `'- To be rid of it, move the folder to DELETE, which gives it back. …'` |
| navigator_catalog.py:51 | `'footer': ['Settings', 'Trash']` | `['Settings', 'DELETE']` |
| qt_app.py:5233 (legacy) | `('F2 / Del', 'Rename / delete in Browse')` | `('F2 / Del', 'Rename / move to DELETE in Browse')` (legacy room, word only) |
| Help: GRAPHITE_DESK.md (35), DAILY_GUIDE.md (4), README.md (2) | Trash | DELETE, plus one sentence: "DELETE keeps what you delete; Restore puts it back. Graphite never empties DELETE by itself." (No empty action exists in the app.) |

These stay as they are:
- the release history (`version.py:15`, `:53`, the old notes);
- docstrings and comments;
- the thumbnail emblem, which is a drawing.

A new entry goes into RELEASE_NOTES for 0.8.3.

### Renames, so DELETE never meets another "Delete"

| file:line | now | becomes |
|---|---|---|
| context_menu.py:429 (key `edit:delete` unchanged) | `'Delete'` (removes the selected words) | `'Erase'`, reason `'Select words first.'`. FOLDED :2948 keeps Qt's old word `'Delete'`: it records where the old menu's word went (data, never shown), and the test only checks that its key is offered. |
| memory_qt.py:24 / :106 | `'Delete profile and feedback'` / `'Profile and feedback deleted…'` | `'Erase profile and feedback'` / `'Profile and feedback erased…'` |
| office_building_qt.py:514 | `'Delete every recorded instruction and outcome? …'` | `'Erase every recorded instruction and outcome? Lessons you reviewed stay.'` |
| change_sets_qt.py:114, :161; program_rooms_qt.py:839 | `'Remove file'`, plus the op `{"op":"DELETE"}` shown as JSON | Unchanged. "Remove" does not collide. The JSON is a Kernel operation shown verbatim as a line in the cells face; this is the one documented exception. |

All other "Remove …" labels (Agenda, links, variables, sources, Eject media) stay.

---

## (b) Every font the typewriter face, in Kasandra

### What I measured
- **Special Elite is not a typewriter face in the strict sense: it is proportional.**
  - Advances run from 402 to 1429 per 2048-unit em, with a median of 1171. The space is 600.
- **Two pairs look the same.** `1` and `l` differ only by the angle of the flag. `0` and `O` differ by 0.1 px at 16 px.
  - Feature check: neither `0` nor `O` has ink at its centre. `1`, `l` and `I` all have a foot on the left.
  - Render: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/big_glyphs.png`.
- **The face lacks** ← → ↑ ↓ and box drawing. IBM Plex Mono has all of them.

### The decision: two typewriter faces from one
1. **WORDS: `Special Elite`**, the shipped file, unchanged. It is used for every word: menus, tabs, trees, titles, buttons, her prose and the right-click rows.
2. **CELLS: `Special Elite Mono`**, a fixed-pitch face derived from it. Real typewriters were monospaced, so this is the more honest typewriter face.
   - It is metrically identical to IBM Plex Mono: the same 0.6 em cell and the same 1.3 em line.
   - So every existing piece of column, cell or width maths written for MONO stays exactly right:
     - Terminal columns, `ls -l` output, the right-click line preview counting from `'M'`;
     - PanelInk and ArtPanel cells, the code rain;
     - the fixed 44 px tag column, the log lists, the Timeline `hh:mm` stamps;
     - the meters, where digits no longer jitter.
   - Prototype result: Qt `isFixedPitch=True`; every printable ASCII character advances 9.59 px at 16 px, the same as Plex Mono; height is 20.81 px at 16 px, the same as Plex Mono.
   - Feature check against the original face:
     - centre of `0` is 185/248/241 at 13/14/16 px; centre of `O` is 0;
     - left foot of `l` is 0 px; left foot of `1` is at least 2 px.
     - That is at least as distinct as Plex Mono.
   - Render: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/faces_compare.png`.

**The build tool: `tools/make_typewriter_cells.py`.** It runs at build time only and needs fontTools ≥ 4.40 (MIT); fontTools is not a runtime dependency. The prototype is `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/make_mono.py`.
1. Source: `branding/fonts/typewriter/SpecialElite-Regular.ttf` (SHA-256 a776fcb4…14bc4). `CELL = 1229`, which is 0.6 × 2048.
2. Decompose every glyph:
   - if its advance is greater than CELL, scale x by CELL/advance about the centre of the advance;
   - otherwise translate x by (CELL − advance)/2;
   - glyphs with zero advance stay at 0.
3. `0`: add the face's own `.` glyph, scaled 0.62, at the centre of the zero's bounding box (a dotted zero, as in Plex Mono).
4. `l`: clamp every point with y < 150 and x < 452 to x = 452. This removes the left half of its foot, so `l` keeps a serif, a stem and a right foot.
5. Every advance becomes CELL.
   - Drop `fpgm`, `prep`, `cvt `, `hdmx`, `LTSH`, `VDMX`, `kern`, `GPOS` and `GSUB`: no kerning and no ligatures in a cell face.
   - `gasp` = symmetric smoothing plus grayscale at every size.
6. Vertical metrics: ascent 1747 and descent 915 in hhea, typo and win, line gap 0. That gives 1.3 em, shared above and below.
7. Fixed-pitch flags: `post.isFixedPitch=1`, `OS/2.panose.bProportion=9`, `xAvgCharWidth=1229`, `advanceWidthMax=1229`.
8. Names: family "Special Elite Mono", PostScript name "SpecialEliteMono-Regular". Append to nameID 0: "Modified 2026 for Graphite: fixed pitch, dotted zero, l with a right foot only." This is the change notice Apache-2.0 §4(b) asks for.
9. Keep `head.created` and `head.modified` from the source and save with `recalcTimestamp=False`, so the output is byte-reproducible.

Output: `branding/fonts/typewriter/SpecialEliteMono-Regular.ttf`, about 275 KB. Record its SHA-256 in `branding/fonts/typewriter/NOTICE.md`, `THIRD_PARTY_NOTICES.md` and `MANIFEST.json`. Rewrite the NOTICE line "Values, receipts, cells and controls stay in IBM Plex" to describe the cells face.

**Glyph fallback.** In `shell2.py:49-60`, right after loading the fonts:
- `QFont.insertSubstitutions('Special Elite Mono', ['IBM Plex Mono', 'DejaVu Sans Mono'])`
- `QFont.insertSubstitutions('Special Elite', ['IBM Plex Sans', 'DejaVu Sans'])`

Verified in Qt 6.8: `a←b─c` in the cells face takes ← and ─ from IBM Plex Mono at 9.59 px, so the box-drawing lines in Terminal output connect. A list in the style sheet and `setFamilies` work too.

### Wiring
- `boss_theme.PALETTES`:
  - add `CELLS='Special Elite Mono'` to kasandra and `CELLS='IBM Plex Mono'` to graphite;
  - add `cells_font(px, weight=Normal)`, which ignores weight in Kasandra (the face has no bold; synthetic bold smears the worn edges).
- `shell2.py:26`: `MONO = bt.CELLS`. `mono_font()` uses `MONO`, then DejaVu Sans Mono.
- `reading_preferences.apply` (:108-109): add a third swap. While `code_family == 'IBM Plex Mono'` and `bt.CELLS != 'IBM Plex Mono'`, use `bt.CELLS`. Because `family(…, fixed=True)` accepts it (isFixedPitch), Terminal and every `QPlainTextEdit` take it. **The owner's own reading faces still win**: a swap happens only while the profile holds the Plex default.
- `control_qt.py:400-404`: report the families in force after the swaps. Today Kasandra reports IBM Plex Sans; this is a bug.
- Hard-coded `'IBM Plex Mono'` becomes `bt.CELLS` in:
  - boss_theme.py:216, :230, :235;
  - theme2.py:46, :124;
  - boss_qt.py:110, :186-193, :319-351;
  - code_rain.py:27 (DejaVu → CELLS);
  - console_qt; log_qt:291-294 and :392-409;
  - finder_qt:216; compare_qt:27 and :100; universal_viewer:185 and :193 (through the code family); thumbnails.py:204;
  - investigations_qt; datasheet_qt; sheet_workbench_qt; work_trail_qt; program_rooms_qt;
  - field_qt `mono()`; chain_menu; context_menu:2577 and :2584; typebar OneBox.
- Hard-coded `'IBM Plex Mono'` becomes `bt.FACE` (words) in:
  - `pane_qt.tab_font` (:122-126). In Kasandra the chosen tab is drawn in TEXT with the LIVE glow and Normal weight;
  - shell2.py:3458 (pane title);
  - idle_display_art labels.
- Unchanged (pictures): glyph_set and chain_icons letters inside icons; the folder-thumbnail letters (thumbnails.py:58, :97); the Graphite splash (graphite_brand.py:220, :244).

### Sizes, spacing and leading by role (Kasandra; px at 14 pt, × s = ui_pt/14)
Floors at every interface size: **WORDS at least 13 px, CELLS at least 12 px**. Emphasis is by colour (TEXT over QUIET) or underline, never by weight. CELLS are never letter-spaced, except standalone caps tags, which are measured.

| role | face | px | spacing | leading |
|---|---|---|---|---|
| Head menus, More, Apps' name | WORDS | 16 | 0 | — |
| Workspace address in the head | CELLS | 14 | 0 | — |
| Left tabs Files · Machine · Settings | WORDS | 16 | 0 | — |
| Tree rows | WORDS | 16 | 0 | row = line + 12 = 28 (unchanged) |
| DELETE / its count | WORDS caps / CELLS | 16 / 13 | +1.0 / 0 | — |
| Her name (nameplate) | WORDS | 24 | +0.5 | — |
| Dial words / model line | WORDS / CELLS | 15 / 13 | 0 | — |
| This: / Now: lines | WORDS | 16 | 0 | 125% |
| Her words and yours (cards) | WORDS | 17 | 0 | 130% |
| Numbers, addresses and file names inside prose | CELLS span | prose − 1 (16) | 0 | — |
| The line slab in her card | CELLS | 14 | 0 | 1.3 em (built in) |
| Typing line | CELLS | 16 | 0 | — |
| Terminal, log lists, code and text views | CELLS | code_pt | 0 | 1.3 em |
| Meter keys CPU GPU RAM TXT / readings | CELLS caps / CELLS | 12 (was 11 px small caps) / 14 | +0.6 / 0 | — |
| Field tags, state, facts, where | CELLS | max(12, now) | 0 | — |
| Field revision table values | CELLS, **right-aligned** | 13 | 0 | — |
| Field sheet titles | WORDS | as now | −0.35 (as now) | — |
| Home greeting / card titles / body / section caps ("JOT IT DOWN") | WORDS | 34 / 20 / 16 / 13 | −0.3 / 0 / 0 / +1.2 | — / — / 125% / — |
| Tooltips | WORDS | 14 | 0 | — |

**Alignment, kept right with a proportional face.**
- Anything that lines up in columns is in CELLS, whose advance is exactly Plex Mono's, so nothing moves.
- Everything in WORDS is measured (`elidedText`, `horizontalAdvance`, ink), so it only gets wider. P stays 354, because no new WORDS text enters the lower band.
- Leading for the WORDS face (its line box is 1.0 em) comes from rich text `<p style="line-height:130%">`; this rendered correctly in the mock.

**Numbers and addresses inside her prose.** `shell2.cells_spans(text)`:
1. `html.escape` the text first.
2. Wrap each token that contains a digit (`[\w.:/-]*\d[\w.:/-]*`), each file name (`\S+\.\w{1,5}`) and each `@address` in `<span style="font-family:'Special Elite Mono';font-size:(px−1)px">`.

So "07", "3.36", "B2" and "page 1" can never read as O7, 3.3b or page l.

**The line slab** (shell2.py:1944) loses to the window style sheet today, which is why the frame showed "tit / le" breaking mid-word.
- Give the slab label its own style sheet: `font-family:'Special Elite Mono';font-size:14px`. In Qt, a widget's own sheet beats inherited rules, whatever their specificity.
- Show one stage of the pipe per row, broken before each `|`.
- Inside a stage, break only after `,` `:` `{` `/`. Use `\u200b` for display; Copy keeps the original line.

---

## (c) The hologram in the lower left

### Assets and verification
- Copy `hologram.webp` (800×875, SHA-256 b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec) into `branding/kasandra/`.
- Record its SHA in the README and MANIFEST.
- **Do not ship `portrait.webp` now.** The hologram carries the alpha the lower left needs, and the face leaves the right column. Keep the portrait for a solid still elsewhere later.
- Verify with route (b), the marks table. In `kasandra_art`, add:
  - `MARKS = {'hologram.webp': …, 'kp_emblem.png': …, 'kp_emblem_small.png': …, 'kp_tile.png': …, 'kp_tile_letters.png': …, 'kp_monogram.png': '7c5b3c9c1f16e0d1eca1f881a0ece60bda777355fdc0fa634495deb77170a073', 'wordmark.webp': '0a8d44e5…eb1e6'}`;
  - `mark(root, name)`: `usable()`'s cached SHA check over these; it returns a path or None;
  - `cutout(path)`: decode to `Format_ARGB32_Premultiplied`, never `source()`, which drops alpha at :181.
  - The wordmark (boss_qt.py:77-80) and the Apps mark go through `mark()` too.
  - The catalog's 8 scenes are untouched.
- Crop to the figure's own bounds (alpha > 16: x 86–680, y 22–826) plus 8 px: `CROP = QRect(78, 14, 612, 822)`, `ASPECT = 0.7445`.

### Placement
Write it as a pure function in a new Qt-free module, `workbench/hologram.py`: `place(rows_bottom, foot_top, delete_box, P, inset, s)`. It returns `(figure, emitter, stance)` or None. It is computed in left-PaneBody coordinates.

```
GAP=24s  SIDE=8s  EMIT=14s  H_MIN=120s  H_MAX=380s   (h is rounded down to a multiple of 4)
top = rows_bottom + GAP                       # never nearer the last row
stage : x in [inset+SIDE, P-inset-SIDE], emitter centre y = foot_top - EMIT/2 - 2s     (centred, on the foot's top edge)
corner: x in [inset+SIDE, DELETE.x-12s],   emitter centre y = DELETE.bottom+1 - EMIT/2 (lower left, on DELETE's baseline)
h(stance) = min(H_MAX, (ey - EMIT/2) - top, span_width/ASPECT);  take the larger, tie -> stage; h < H_MIN -> None
w = round(h*ASPECT); figure = (round(cx - w/2), round(ey - EMIT/2 - h + 0.04h), w, h)   # her faded foot melts into the beam
emitter = (cx - 0.31w, ey - EMIT/2, 0.62w, EMIT)
```

The tree scrolling (vertical range > 0) means None.

DELETE's box grows by the word's extra ink: about 121×29 at x ≈ 217 when P = 354.

Results, in pane coordinates (window y = +61):

| case | rows end | stance | figure x,y,w,h | window y of figure |
|---|---|---|---|---|
| 1920×1200 Files as it opens (13 rows) | 429 | stage | 36, 644, 283, 380 | 705–1085; emitter centre (177, 1077) |
| 1920 Files, everything open (27 rows) | 821 | corner | 40, 856, 149, 200 | — |
| 1920 Machine | 191 | stage | 36, 644, 283, 380 | — |
| **1366×768 Files as it opens** | 429 | **corner** | 55, 462, 119, 160 | 523–683, beside DELETE |
| 1366 Files, top level only | 373 | corner | 34, —, 161, 216 | — |
| 1366 Machine | 191 | stage | 43, 231, 268, 360 | — |
| Settings, or any tree that scrolls | — | none | — | — |

At 1366 the reference patch's rule (a 150 px floor on the free box) hid her on Files. This rule gives her 160 px by letting her stand on DELETE's baseline.

### The widget
`hologram_qt.Projection(QWidget)` is a child of the left PaneBody, raised above the content and the foot.
- Attributes: `WA_TransparentForMouseEvents`, `NoFocus`. Use `WA_OpaquePaintEvent` with a GROUND fill, because the ground under her is flat; confirm with a frame diff, otherwise drop the flag.
- Geometry: the union of the figure plus 16 px at the sides, 8 px above, and the emitter plus 0.25 rx. It is clipped to x in [inset, P − inset].
- It is placed again synchronously, before the next paint, on:
  - `itemExpanded` and `itemCollapsed`;
  - the model's `rowsInserted`, `rowsRemoved`, `modelReset` and `layoutChanged`;
  - `verticalScrollBar().rangeChanged`;
  - `nav.stack.currentChanged`;
  - `PaneBody.arrange`; a change of reading profile (s); `boss_qt.choose_art`.
- **She never covers a row, not even for one frame.**
- Accessible name: `named('Kasandra') + ', projected'`. The accessible description gives the state words.
- She appears in Kasandra only. Graphite has no projection.

**When she steps aside:**

| condition | behaviour |
|---|---|
| The tree needs the room (h < H_MIN, or the tree scrolls) | Hidden at once. |
| Another tab | She stands under Machine when it has room; she is hidden on Settings (it scrolls). |
| Clean desk | Nothing at all: no figure, no emitter, no beam. |
| ASCII desk | Drawn as characters (see below). |
| Pane hidden, window minimised, app inactive, idle display shown | Timer stops. An inactive window holds the still frame for its state. |

### The animated static (Illustrated)
**Fixed layers, cached per (height bucket, dpr, state):**
- the figure tinted with `SourceAtop`;
- the pair of chroma ghosts (cyan `#83eaff` and pink `#fa507c`) pre-composited into one image;
- the beam and emitter, at 8 pulse phases;
- six noise tiles of 64×64 at 18% density, shared by every size.

**Per frame**, into one reused buffer of figure size:
1. figure;
2. tears: horizontal slices re-blitted at a shift;
3. noise at ×2, with a random tile and offset, `SourceAtop` (static only on her);
4. scan lines: a 1×3 px tile, `SourceAtop`;
5. in working only, the write-head band.

Then to screen: beam (Plus), ghosts, buffer at opacity × flicker, emitter rim, motes.

| state (from `kasandra_art.current_state`) | figure opacity · tint | scan lines (drift up, alpha, period 3s px) | noise | flicker depth · drops | tears (mean interval · shift · band) | chroma | emitter · pulse | motes (n, rise) | frame rate |
|---|---|---|---|---|---|---|---|---|---|
| **idle** (viewing too) | 0.86 · none | 10 px/s · 0.30 | 0.20 | 3% · 1 per 12 s | 9 s · 3–8 px · 2–5 px | ±1 px, 0.22 | TEAL · steady | 4, 14 px/s | 10 fps |
| **working** | 0.90 · TEAL 0.10 | 24 · 0.30 | 0.32 | 4% · 1 per 10 s | 5 s · 3–10 · 2–5 | ±1 | TEAL · ±25%, 1.2 s | 10, 36 | 15 fps |
| **awaiting_approval** (waiting for the owner) | 0.94 · OWNER 0.08 | 6 · 0.24 | 0.12 | 1.5% · none | **none**: she holds still and looks at you | cyan 0.18, pink 0.30 | OWNER `#fa507c` · ±20%, 2.8 s (the tree's breath) | 4, 10 | 8 fps |
| **completed** (20 s hold) | 0.88 · HONEY 0.06 | 10 · 0.28 | 0.16 | 2% · none | 12 s · 3–6 · 2–5 | ±1 | HONEY · steady | 6, 18 | 10 fps |
| **blocked / refusal** (45 s hold, from `note_outcome(False)`) | 0.78 · RED 0.14 | 6 · 0.36 | 0.40 | 8% · 1 per 4 s | 1.5 s · 6–14 · 3–8 | ±3, 0.35 | RED `#ff3b5c` · steady | 0 | 15 fps |

All shifts and band heights are × s.

**Rates and effect details:**
- Flicker each frame: `b ← 0.5b + 0.5u`, where u is uniform on [0, 1]; brightness = 1 − depth·b.
- A drop sets brightness to 0.62 for one frame.
- Tears: one band with probability 0.7, two with 0.3. Band y is uniform over 0.12h to 0.92h. A tear lasts 100 ms (the timer runs at 50 ms while it lasts), and chroma and noise double during it.
- **Never more than 3 flashes a second**: at least 400 ms between drops and tears.
- Beam: a trapezoid from the emitter (width 0.62w) up to 0.55h above her top, 0.92w wide at the top, alpha 0.16 × pulse fading to 0, drawn with Plus.
- Emitter: an ellipse with ry = 0.16 rx; rim 1.5 px at 0.85 × pulse; fill 0.10; radial glow out to 1.25 rx at 0.30.

**Moments, each 25 fps for its length only, then back to the state's rate:**
- **Power-up**, 360 ms: on first show after start, after leaving Clean, or after being hidden at least 10 s.
  - The emitter ring lights over 0–120 ms.
  - She is drawn in from the base upward behind a bright scan edge over 120–360 ms, with noise ×3 decaying.
  - A tab switch within 10 s is a cut, not a power-up.
- **State change**: a 300 ms crossfade of the two figure layers and the emitter colour.
- **Lock-in**, on entering completed: one sweep from top to bottom, 400 ms, peak 0.3.
- **Jolt**, on entering blocked: 300 ms, two tears, chroma ±4, one drop.
- **Touch**: the pointer enters her rect. Read it through an event filter on `tree.viewport()` and `PaneFoot`, so clicks still go to the tree.
  - 160 ms: one tear of 5 px, chroma ×2, brightness +6%.
  - Cooldown 1.5 s. "It responds with a little more force than you expected."
- **Flinch**, after a `files.trash` (the can is beside her): 120 ms, one tear.

**Never slows the hand.** She takes no input, delays nothing and covers no row. Nothing waits on her animations.

**Reduce motion, or `menu_catch.calm`:**
- The timer never starts.
- She lands straight on a still frame for her state: figure, tint, scan lines at a fixed phase, one fixed noise tile at half strength, emitter steady.
- No tears, flicker, motes, power-up, crossfade or touch.
- A state change swaps the still at once.

**ASCII desk:**
- The cut figure is sampled into CELLS cells at 10 px × s, using the ramp `' .:-=+*#%@'` on luminance × alpha. At 1920 that is about 47×29 cells.
- The emitter is a row `(═════)`; ═ falls back to Plex Mono.
- Static at 6 fps: 2% of non-blank cells step ±1 on the ramp each tick; one row in 9 is drawn at 60%; a tear shifts a row by 1–2 cells.
- Reduce motion: a still.

### CPU budget and how it is met
**Measured.** Prototype in Python with the Qt raster engine, offscreen, on a 2.3 GHz Xeon:
- one whole frame: 1.9 ms (idle) to 2.5 ms (working) at 283×380; 0.8–1.0 ms at 119×160;
- building the layers for one size: 4–6 ms.

**Budget:**
- idle: at most 1.2% of one core at 1920 and 0.6% at 1366;
- working: at most 2.5%;
- moments: at most 400 ms at 25 fps.

**Means:**
1. All fixed layers are cached as above. The two ghosts are one blit; the beam is a cached phase.
2. One buffer is reused.
3. Heights are bucketed in 4 px steps, with an LRU of 3 sizes, about 2.6 MB at 1920. While a resize is still moving (within 150 ms), draw the nearest bucket with a fast transform; rebuild smooth after it settles.
4. `update()` touches only her own widget rect, which is opaque.
5. **`BranchTree._breathe` updates only the rows on the lit path.** It uses the union of their `visualItemRect`s, at full viewport width, instead of the whole viewport. So the tree's 140 ms breath never repaints her, and it gets cheaper itself.
6. The timer stops when:
   - she is hidden, or the tree scrolls;
   - the desk is Clean, or motion is reduced;
   - the window is minimised (`changeEvent` WindowStateChange) or the app is inactive (`QGuiApplication.applicationStateChanged`);
   - the idle display is up.
7. A governor watches the moving average of paint time. Above 4 ms, the frame rate halves. Above 8 ms, she holds a still frame until the next change of state.
8. `hologram.webp` is decoded once (2.8 MB ARGB). `boss_qt.choose_art` refreshes her along with ArtPanel and PanelInk.

Mock frames on the real columns (idle, working, waiting, blocked):
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/strip_1920.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/strip_1366.png`

---

## (d) The right column without the picture (Kasandra; Graphite unchanged)

**At the top, a nameplate.** It replaces PanelInk 'face'. The signature, hidden today, comes back as this nameplate.

| part | measurements | look | behaviour |
|---|---|---|---|
| Row 1, 30 px × s | — | `named('Stacy')`, so "Kasandra", in WORDS 24 px, `VIOLET_PALE #d2c4f5`, letter spacing +0.5 | — |
| Her cursor, 4 px after the name | a block 0.45 em × 0.78 em (11×19 px), on the baseline | colour by state: idle `LINE_STRONG #8796cb`; working `TEAL #83eaff`, blinking 530/530 ms; awaiting_approval `OWNER #fa507c`, breathing 0.6–1.0 over 2.8 s; completed `HONEY #e9b872` (20 s); blocked `RED #ff3b5c` (45 s) | steady with Reduce motion. The hologram's emitter says the same state, so the two ends of the window agree. |
| Dial words (the existing `StacyHand` link, e.g. "does and shows") | right-aligned on the same row | WORDS 15 px, QUIET | when name, cursor and dial are wider than the row (at large interface sizes), the dial moves under the name |
| Row 2, 20 px | — | the model line in CELLS 13 px, FAINT | `ElideMiddle`: model names are identifiers |
| Rule | 1 px LINE `#3b4479` across the column, with a 32×2 px TEAL tick at its left | glows on Illustrated | — |
| Gap | 10 px | — | — |

The nameplate is 61 px tall, against 104 px today (the picture row plus spacing): **43 px gained at both sizes**. The This: and Now: lines and their cyan marks stay, at 16 px with 125% leading.

**The cards:**
- Thread gutter 14 → 6 px, with a 6 px scroll bar that appears only when needed.
- Card padding 12 → 10 px; corners radius 3 (plates, not bubbles); honey edge 3 px (hers).
- Your bubbles: `VIOLET_SOFT` with a `VIOLET_DEEP` edge, left margin 30 → 24.
- Text: WORDS 17 px × s, 130% leading.
- Text width: 280 → **293 px**, about 32–33 characters a line.
- Numbers and addresses in CELLS spans; the line slab as in (b).

**How the gained height is used:**
- The fold (`shell2.py:1886-1899`) keeps the newest item whole.
- Older items that do not fit whole become **heads**: one 26 px row each, WORDS 15 px QUIET, the first line elided, a dim honey 2 px edge and a "show" link. Up to 6 heads, under the existing "N earlier · show them".
- A new answer taller than the view is scrolled to its **top**, not its bottom.

**At each size:**
- **1366**: in the mock, the Trace answer that was cut by 38 px now fits whole; its bottom is at 633 of 646. Mock: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/right_1366.png`.
- **1920**: the 292 px left empty after the fold now holds about 6 heads.

**The column's look: her terminal.**
- Ground `TERMINAL_GROUND #11132c` for the right pane, its foot included. The rest of the desk stays `#171b3c`.
- A still raster: 1 px black lines every 4 px at alpha 0.035, painted under the cards only.
- A bezel: a 1 px `TEAL_EDGE #5a8fc4` line at alpha 0.5 on her inner edge, with a soft 6 px glow on Illustrated.
- On Clean, the colour stays but the raster and glow go.
- The right foot stays an empty mirror of DELETE's foot.

The column keeps P: "one width for both panes" is pinned by `test_desk.py:13`, so her column does not widen.

---

## (e) The kp emblem

**Cut by colour-to-alpha with unpremultiply.** Tool: `tools/cut_kp_emblem.py`, build time only. Run it with `python3 -I`; it may use Pillow or Qt. Prototype: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/kp_cut2.py`.
1. The ground B is the median of a 40 px ring round the edge: `#070221`. The ground's noise is at most 11/255.
2. For each pixel: `a = max over channels of max(0, c−B)/(255−B)`. Use only the rise above the ground: counting the fall below it makes α jump to 1 wherever B is near 0 in a channel.
3. If a ≤ 0.05, the pixel is clear. Otherwise colour = clamp((c − (1−a)·B)/a), and alpha = 255 · min(1, (a − 0.05)/0.92).
4. Trim to the content bounding box (259, 417, 980, 883) plus 12 px: **745×490**.
5. The bird's dark eye and circuit lines become holes, which read correctly on the band.

**Verified on the prototype:**
- every pixel with α ≥ 16 lies at least 222 (RGB distance) from the ground: no navy fringe;
- the k stem is (255, 242, 225) against the art's `#fef1e3`;
- the corners are clear.

**Assets**, all in `branding/kasandra/`, with SHA-256 in `README.md` and `MANIFEST.json` and in `kasandra_art.MARKS`:

| file | content | use |
|---|---|---|
| `kp_emblem_source.png` | the original, 1254² RGB, 94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa | so the cut can be made again |
| `kp_emblem.png` | 745×490 RGBA, the master cut | sizes above 48 device px |
| `kp_emblem_small.png` | 745×490 RGBA, an optical cut for heights up to 48 device px: pink and violet strokes grown by a 9×9 per-channel max filter (4 px a side at source scale), the cream letters pasted back exact | so the bird's legs (0.8 → about 1.3 px) and the violet trace survive at 38 px |
| `kp_tile.png` | 512×512, rounded square (radius 92), navy `#070221` from the original art's own ground, the emblem at 84% width | window icon |
| `kp_tile_letters.png` | 64×64, the same tile with the cream "kp" only | 16 and 24 px icons |

**The Apps button (shell2.py:586-597):**
- Icon **38 px tall × 58 px wide** (× s), from a `QIcon` with the small cut at 1× and the master at 2×.
- The button is 74×60, with 8 px a side; the icon sits 10 px from the top of the 60 px band, above the cyan rule.
- `paperIcon`, the accessible name `'Apps'` and the tip stay. No word is shown.
- Fallbacks: if the emblem fails its SHA, the verified `kp_monogram.png` at 36×36 (kept, with its SHA recorded now); if that fails too, the word "Apps".
- How it reads at 38 px: crisp cream "kp" stems of 5–6 px, a pink ostrich silhouette 36 px tall, a violet trace about 2 px. On `#141734` the edges are clean. Proof: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/kp_band_x3.png`.

**The window icon, Kasandra only:**
- `graphite_brand.window_icon(appearance)`: kp_tile at 32, 48, 64, 128 and 256 px; kp_tile_letters at 16 and 24 px.
- Graphite keeps its own tile.
- The installed launcher and the splash stay Graphite's.

---

## (f) Tests and frames

### Tests that change
- `test_desk_acts.py:186`: becomes `(False,'DELETE, once emptied, cannot be brought back')`.
- `test_desk_acts.py:193`: the path `'Move to Trash'` becomes `'Move to DELETE'`, so the test still checks something.
- `test_graphite.py:292`: the KEPT string becomes `"… and deletions go to DELETE."`.
- `test_context_menu.py:678-712`: no code change; it passes once files_qt.py:478, context_menu.py:673, :703 and :2924 change together.
- Tools to keep in step, though not run: `tools/check_desk_ui.py:253-257` redraws `'DELETE'` with the +1.0 spacing.

### New tests
**`test_delete_words.py`:**
- An AST scan of the string literals in `workbench/*.py`, docstrings excluded. `\bTrash\b` appears only in an allowlist (the version history).
- No label is exactly `'Delete'` or starts with `'Delete '`, except FOLDED's old Qt word.
- `context_menu` entry `edit:delete` has the label `'Erase'`.
- `TrashCan.accessibleName()=='DELETE'`; the tip is exactly the one above.
- `trash_size` with the ink of `'DELETE'`: box width = the old formula with that word.
- `TrashTab.title()=='DELETE'`; its lead is `'Nothing is in DELETE.'` when empty.
- Search finds the place for the query "trash".
- `tail_words` gives the two DELETE words.
- The words of `hand.trash` contain `'DELETE'` and `'gives it back'`.

**`test_typewriter_cells.py`:**
- The TTF's SHA equals the one in NOTICE.md.
- `QFontDatabase.isFixedPitch('Special Elite Mono')`, and `reading_preferences.family('Special Elite Mono', True)` returns it.
- For px in 12, 13, 14, 16 and 18: every printable ASCII character's advance equals Plex Mono's `'M'` ±0.01, and `height()` equals Plex Mono's ±0.05.
- `0` centre ink ≥ 160 and `O` ≤ 16; `l` left-foot pixels = 0 and `1` ≥ 2; at 12, 13, 14 and 16 px.
- `horizontalAdvance('←')` at 16 px is 9.6 ±0.05.
- If fontTools is present, rebuilding is byte-identical.
- In a subprocess with `GRAPHITE_APPEARANCE=kasandra`: `bt.CELLS` and `shell2.MONO` are `'Special Elite Mono'`; the font of the typing line, the console and the line slab (14 px despite the window style sheet) is CELLS.
- In Graphite, CELLS and MONO are `'IBM Plex Mono'` and FACE is `'IBM Plex Sans'`.
- A profile with code_family `'DejaVu Sans Mono'` wins.
- The control_qt readback says Special Elite.
- An AST scan finds no `QFont('IBM Plex Mono')` in desk modules outside the picture allowlist.

**`test_hologram.py`:**
- `place()` gives the six table rows above exactly.
- Invariants over a grid (rows_bottom 100–1000 in steps of 7; s in {1, 18/14, 20/14}):
  - figure top ≥ rows_bottom + 24s;
  - figure and emitter do not meet DELETE;
  - x stays inside [inset, P − inset];
  - h % 4 == 0;
  - aspect error < 1 px;
  - h < 120s gives None.
- Widget, in Kasandra Illustrated:
  - visible on Files at 1920; hidden on Settings, on Clean and when the tree scrolls;
  - after `itemExpanded`, its geometry is already clear of the rows, synchronously;
  - the ASCII desk paints no image.
- Motion:
  - with Reduce motion, the timer is inactive and two grabs 300 ms apart are identical;
  - timer interval 100 ms idle and 66 ms working;
  - stopped when minimised or the app is inactive.
- The `hologram.STATES` numbers are pinned.
- Layers are built once per (size, state) over 50 frames; mean paint < 6 ms offscreen.
- One changed byte in `hologram.webp` makes `mark()` return None and the widget hide.
- The cut figure's corner has α = 0.

**`test_kasandra.py`, additions:**
- `kp_emblem.png` is 745×490 with alpha, clear corners, every α ≥ 16 pixel at least 120 from `#070221`, and the k stem ≈ `#fef1e3` ±4 at α 255.
- Every entry in `MARKS` verifies, and README lists each SHA.
- The Apps icon is `QSize(58,38)` at 14 pt with accessibleName 'Apps' and no text.
- The fallback chain: monogram at 36×36, then the word.
- The window icon in Kasandra comes from kp_tile.
- `test_kasandra.py:115-121` (the monogram) **stays**, because the monogram stays as the fallback. The catalog counts (:92, :140) stay.

**Right column, in Kasandra:**
- No PanelInk 'face' is shown.
- The nameplate's family is FACE at 24 px.
- The cursor's colour follows `current_state` for all five states.
- The thread's top is at least 30 px higher than in 0.8.2 at 1366.
- Card text width is at least 290 px at P = 354.
- The card's line pitch is at least 1.25 × px.
- Heads appear when the older item does not fit.
- Graphite's face square is unchanged.

### Frames that prove it
Capture conditions: the nomodel harness, After Hours 07, Kasandra, Illustrated, 14 pt, at 1920×1200 and 1366×768.

| frame | what it shows |
|---|---|
| G01 | Left column, Files, hologram idle |
| G02 | Machine |
| G03 | Settings: no hologram |
| G04 | Files with everything open: corner at 1920, none at 1366 |
| G05 | Clean desk: none |
| G06 | Reduce motion: two grabs 1 s apart, identical |
| G07 | The four states as a strip (force `waiting` and `host._art_outcome`) |
| G08 | DELETE at ×4 |
| G09 | Right column at rest, and after two Traces |
| G10 | The line slab at ×2 (no mid-word break) |
| G11 | Terminal with `ls -l` (columns aligned) |
| G12 | Field cards at ×2 |
| G13 | The Apps emblem at ×3 in the head |
| G14 | Graphite: DELETE in Plex, no hologram, the right column unchanged |
| G15 | 24 frames at 10 fps of the static |
| G16 | A 60 s idle CPU log at 1920 (process time delta; design target ≤ 1.5%, probe asserts ≤ 3%) |

---

## Evidence I made (scratch only)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/SpecialEliteMono-proto.ttf`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/make_mono.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/features.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/faces_compare.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mono_big.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/small_sizes.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/holo_proto.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/holo_1920_idle.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/strip_1920.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/strip_1366.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/right_mock.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/mock/right_1366.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/scripts/kp_cut2.py`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/kp_master.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/kp_small.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/kp_band_x3.png`