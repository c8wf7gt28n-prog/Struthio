# 0.8.3 design: quiet and readable

Kasandra appearance, with DELETE in both appearances. Repository at 0.8.2 (d1df337). I changed nothing under `/home/user/Struthio`.

I built and measured working prototypes for the points that carry risk. Paths are listed in §7.

## Decisions in one place

1. **DELETE** is the name of the place, always in capitals, in both appearances. **Delete** is the verb on the menu row. The document's old "Delete" row (it removes selected words) becomes **Erase**. Every "Delete" that means gone for good also becomes "Erase". After this, DELETE always means "can be brought back", and the two words never meet. Internal names stay as they are.
2. **One typewriter face, in two cuts.** Special Elite's `1` and `l` are almost the same glyph, and so are its `0` and `O`. I checked this at 120 px (`se_big.png`). So it cannot be used as it is for everything. I derived two faces from it (Apache 2.0 allows this):
   - **Kasandra Elite**, for words. It has a slashed zero, an `l` that stands on a right foot only, and tabular figures.
   - **Kasandra Elite Mono**, for lines, Terminal, numbers and tags. It is fixed pitch at 0.6 em, which is exactly the width of IBM Plex Mono. Every column, elision and ASCII cell measured for Plex Mono keeps its width.

   With these two cuts every face in Kasandra can be the typewriter face, the "LAIN font", and nothing goes out of alignment.
3. **The hologram** stands in the lower left, beside DELETE, on the same floor line as the can. It sits in the space left of DELETE and below the last tree row. It is 194×261 at both window sizes when there is room; on Files at 1366×768 it is 140×189. It steps aside whenever the tree needs the room. The static runs at 12 fps from cached layers and costs 0.6 ms a frame in the prototype (0.7% of one core). It shows the state of the work through the colour of its base, and changes its motion only a little. With Reduce motion or the Clean glow it is one still frame. On the Clean desk it is not there.
4. **The right column** loses the picture square. At its top goes a masthead: "Kasandra" in the typewriter face, a state dot with a state word, then "model · hand". Its rule lies on the same y as the left tab row's rule. Her cards gain about 45 px of height, 17 px of text width, and 25% leading.
5. **The kp emblem** is cut from its navy ground by unmixing against its own three inks. Edges stay exact, with no navy fringe. On the Apps button it is 52×34. A navy tile version can serve as the window icon in Kasandra.

---

## (a) DELETE

### The words

| meaning | word | where |
|---|---|---|
| the place where deleted things wait and can be put back | **DELETE** (always capitals, a proper name, never "the DELETE") | the can, the page title, the Search place, every sentence |
| the act of sending something there | **Delete** (menu row, sentence case); **deleted** in sentences | Files menu rows, her cards, Timeline |
| bringing it back | **restore** (unchanged) | DELETE page rows, tips |
| removing words, or erasing records for good | **Erase** | the document menu, Memory, the instruction matrix |
| a working copy given up | **Discard** (unchanged), which sends it to DELETE | Files ▸ working copies |

Internal names stay the same: `files.trash`, `files.trash_list`, `files.restore`, the act `hand.trash`, the menu key `'trash'`, `edit:delete`, the `.trash` folder, the `files_trash` table, and the undo line `/files.trash {…}` (code on her card). The Changes room's `{'op': 'DELETE'}` is a Kernel operation shown as code in the line face, and it stays.

### The can (`workbench/trash_can_qt.py`)

- Add a module constant `WORD = 'DELETE'`. Use it at :64 (the measured ink) and :120 (`p.drawText(word, WORD)`).
- `setAccessibleName('DELETE')`.
- `setToolTip('DELETE · what you delete waits here, and restore puts it back where it was · drop files here to delete them')`. The tip says that nothing in DELETE is lost.
- Face and colour do not change: FACE at 16 px × scale, letter spacing 0, so the capitals of either face read cleanly without tracking. In Kasandra it stays RED with its glow; in Graphite, TEXT.
- The box grows from 46.0 to 59.8 px of word ink, so `trash_size` gives about 116 px instead of 102. The right-aligned slot (pane_qt.py:649) moves the can left by 14 px. Measured position: x 222–338, y 1094–1123 at 1920 and y 662–691 at 1366. P does not change, because the foot's need is 116 + 32, far below 354.
- Update the docstrings at trash_can_qt.py:1-6 and :45-48 and pane_qt.py:2-21 to say DELETE.

### Exact strings, old → new

| file:line | new text |
|---|---|
| context_menu.py:498 | `'Deleted. Restore it from DELETE.'` |
| context_menu.py:499 | `'Deleted %s · DELETE puts %s back.'` |
| context_menu.py:673 | `Entry('trash', 'Delete', 'danger', …, tip='DELETE keeps it; restore puts it back')` |
| context_menu.py:703 | `Entry('trash', 'Delete', 'danger', …)` |
| context_menu.py:740 | tip `'Files keeps its own changes: rename, versions, export, DELETE'` |
| context_menu.py:2924 | FOLDED `('Files: a selection', 'Delete', 'file', 'trash')` |
| context_menu.py:429 | `Entry('edit:delete', 'Erase', 'edit', …)`. FOLDED :2948 keeps `'Delete'`, because it records the old Qt menu's word, and its home is still the key `edit:delete`. |
| files_qt.py:107 | `"… every change keeps the version before it, and deletions go to DELETE."` |
| files_qt.py:109 | `'… Deleting moves it to DELETE, '` |
| files_qt.py:334 | title `'Discard draft'` (unchanged); `'Move this working copy to DELETE? %s is not touched, and the record of the work is kept.'` |
| files_qt.py:335 | `'The draft is in DELETE. The original is unchanged.'` |
| files_qt.py:367 | `'Deleted. Restore it from DELETE.'` |
| files_qt.py:478 | `'Delete'` |
| files_qt.py:499, :505 | `'DELETE'` |
| files_qt.py:507 | `'Nothing is in DELETE.'` / `'Everything here can go back where it came from.'` (kept) |
| shell2.py:1179 | `('DELETE', 'trash')` |
| shell2.py:2069 | `'Done: “%s” is in DELETE, which gives it back.'` |
| shell2.py:2118, :2192 | `'“%s” is in DELETE, which gives it back.'` |
| shell2.py:2143, :2145 | `'… so it is yours now and I leave it. Delete it yourself if you want it gone'` |
| shell2.py:2262 | `'… What this start made is in “%s” in Files; delete that folder if you do not want it (DELETE gives it back).'` |
| shell2.py:2269 | Undo tip `'Delete the whole folder (DELETE gives it back) while it is still as I made it'` |
| shell2.py:2324, :2325 | `'…; Undo deletes it, and DELETE gives it back'` |
| desk_doers.py:1261 | `'Delete “%s”'` and `'DELETE keeps it and gives it back'` |
| desk_doers.py:1263 | `'deleted “%s”; it waits in DELETE'` |
| desk_acts.py:159 | `named("Delete a file in Files through Stacy's hand; DELETE gives it back.")` |
| stacy_hand.py:53 | `'DELETE, once emptied, cannot be brought back'` |
| stacy_start.py:153 | `named('- To be rid of it, delete the folder; DELETE gives it back. While it is still as Stacy made it, Undo on her card does that.')` |
| working_copies.py:275, :303 | `'Working copy missing (moved or deleted)'` |
| working_copies.py:386, :511, :538; working_folders.py:133 | `'COPIES_WORK_MISSING: the working copy was moved or deleted'` |
| files_service.py:94 | `'FILES_RESERVED: use DELETE and versions through their own words'` |
| files_service.py:210 | `'deleted (in DELETE)'`, `'restored from DELETE'` |
| files_service.py:510 | `'In DELETE. Restore puts it back.'` |
| tail_words.py:13 | `'files.trash': 'Deleted (in DELETE)'`, `'files.restore': 'Restored from DELETE'` |
| navigator_catalog.py:51 | `'footer': ['Settings', 'DELETE']` |
| docs/GRAPHITE_DESK.md (35), DAILY_GUIDE.md (4), README.md (2) | the place → DELETE; "Move to Trash" → Delete. Release notes keep their history and add one 0.8.3 line: "Trash is called DELETE." |
| tools/check_desk_ui.py:253-257 | redraw `'DELETE'` |

### Other "Delete" and "erase" words, renamed so they never meet DELETE

| file:line | new text |
|---|---|
| memory_qt.py:24 | `'Erase profile and feedback'` |
| memory_qt.py:106 | reason `'Owner selected Erase profile and feedback'`; note `'Profile and feedback erased. Tasks and external archives remain separate.'` |
| office_building_qt.py:514 | `'Erase every recorded instruction and outcome? Lessons you reviewed stay.'` |
| qt_app.py:5233 (legacy keys list, prints keys) | not touched in 0.8.3. It is legacy and already breaks the no-keys rule; note it for removal. |

The "Remove …" words in change_sets_qt, program_rooms_qt, agenda, notebook, concern, problem, document_qt and console_tab are a different word and stay.

---

## (b) Every face the typewriter face, in Kasandra

### The two derived faces (built once, committed, verified)

Add `tools/derive_typewriter.py`, a maintainer tool using fontTools and skia-pathops. It runs once, never at app start. It reads `branding/fonts/typewriter/SpecialElite-Regular.ttf` (2048 units per em) and writes:

| file | family | changes from Special Elite |
|---|---|---|
| `branding/fonts/typewriter/KasandraElite-Regular.ttf` | Kasandra Elite | **zero:** union with a slash from (330,330) to (890,1150), half-width 62 units, in the face's own weight. **l:** the left half of its foot removed, by subtracting the rect (−200,−200)–(446,132). **Digits:** every digit advance set to 1254 units (0.612 em), ink centred. Kerning, ligatures and vertical metrics are left exactly as Special Elite's (ascent 1440, descent 608, line gap 0), so tree rows (28), band heights and P do not move. |
| `branding/fonts/typewriter/KasandraEliteMono-Regular.ttf` | Kasandra Elite Mono | The same glyphs. Every advance is 1229 units (0.6 em, the Elite pitch of 12 characters an inch at 10 pt). Each glyph's ink is centred in the cell. Any glyph wider than 1189 units (M, W, m, _) is narrowed about its ink centre. Zero-width marks stay zero. `kern`, `GPOS` and `GSUB` are dropped, so there are no ligatures in a cell. `post.isFixedPitch=1`, panose proportion 9, `xAvgCharWidth` 1229. Ascent 1560, descent 898 (1.2 em lines). |

Both faces:
- Remove `fpgm`, `prep` and `cvt ` (the old hints no longer fit the new outlines). Set `gasp` to smooth-and-grid-fit at all sizes.
- Name tables: family as above. Description: "Derived from Special Elite (Apache 2.0) for Graphite: slashed zero, l on a right foot, tabular figures (+ fixed 0.6 em pitch, 1.2 em lines, no kerning or ligatures)". Keep the copyright and licence strings.

`branding/fonts/typewriter/NOTICE.md` gets one section per derived file:
- what was changed (Apache 2.0 §4(b));
- the SHA-256 of each file;
- the line "not the Special Elite font; its name is not used for the derived faces" (Apache 2.0 §6).

`SpecialElite-Regular.ttf` and its licence stay as the derivation's source. `shell2.load_fonts` (shell2.py:49-60) loads the two derived files and stops loading the source.

**Measured with my prototype** (`derive.py`, which can serve as the starting point for the tool):

| | Special Elite | Kasandra Elite | Kasandra Elite Mono | IBM Plex Mono |
|---|---|---|---|---|
| `QFontDatabase.isFixedPitch` | False | False | **True** (fontconfig spacing=100) | True |
| height at 16 px | 16.0 | 16.0 | 19.2 | 20.8 |
| digit advances at 16 px | 8.59 to 9.80 (ten values) | **9.80 (one value)** | 9.59 | 9.59 |
| `M`, `i`, space at 16 px | 11.16, 9.09, 4.69 | same | **9.59** for every glyph | 9.59 |
| DELETE / Kasandra / Terminal at 16 px | 59.8 / 73.8 / 74.6 | same | 57.6 / 76.8 / 76.8 | same as Mono |

- `ls -l` output in Kasandra Elite Mono lines up column for column with Plex Mono (`faces.png`).
- The lower band words keep Special Elite's widths, so P stays 354.

### One theme name per role, and one way to set a face

- In `boss_theme.PALETTES`:
  - add `MONO`: graphite `'IBM Plex Mono'`, kasandra `'Kasandra Elite Mono'`;
  - kasandra `FACE` and `DISPLAY` become `'Kasandra Elite'`;
  - Graphite keeps `FACE='IBM Plex Sans'`, `DISPLAY='IBM Plex Mono'` and Plex Mono for code.
- `shell2.py:26`: `SANS, MONO = bt.FACE, bt.MONO`. `mono_font()` (shell2.py:265) uses MONO with the DejaVu Sans Mono fallback, as now.

**Fix the slab bug.** `QWidget {font-family:…}` in the window sheet (reading_preferences.py:113) beats `setFont`. Because of it, the card's line (shell2.py:1944) draws in Special Elite while code elsewhere measures in Plex Mono. The fix:
- Add one property, `arcFace` = `'mono'` | `'display'`.
- Add two rules to the sheet in `reading_preferences.apply`: `*[arcFace="mono"] {font-family:'<code>';}` and `*[arcFace="display"] {font-family:'<DISPLAY>';}`.
- Add a helper `shell2.mono(widget, px)` that sets the property and the pixel size.
- Every place in the list below that calls `setFont(mono_font(n))`, or names "IBM Plex Mono" in a sheet, uses this property or `%(MONO)s`.

The face that is measured is then always the face that is drawn. That is what keeps every `elidedText` and `horizontalAdvance` right.

**Hard-coded families become theme names:**
- pane_qt.py:124 `tab_font`: becomes FACE. In Kasandra, the chosen tab is drawn Regular in TEXT, because a synthetic bold smears a worn face. Its mark already says which tab is chosen.
- shell2.py:3458 `PaneTitle` font-family: becomes DISPLAY.
- boss_theme.py:216 `WorkspacePath`, :230 `MonitorReading` and :235 `ChainProgram`: become MONO.
- theme2.py:46 and :124: become MONO.
- `QFont(MONO)` / `'IBM Plex Mono'` in console_qt (:172, :199-233, :399), log_qt (:291, :392-409), compare_qt (:27, :100), finder_qt (:216), thumbnails (:204), universal_viewer (:185, :193, `'monospace'`), code_rain (:27, DejaVu), boss_qt (:110, :186-193, :319-351), idle_display_art (:36), chain_menu (:87-95) and context_menu (:2577, :2584): all become MONO.
- The room-wide sheets in investigations_qt, datasheet_qt, sheet_workbench_qt, work_trail_qt and program_rooms_qt: become `%(MONO)s`.

**These stay Plex in Kasandra too:**
- the letters inside icons (glyph_set.py:384, :457; chain_icons.py:26, :83), which are drawings shared by both appearances;
- folder thumbnail lettering (thumbnails.py:58, :97);
- Graphite's own brand (graphite_brand.py:220, :244, the splash);
- legacy rooms behind qt_app.

### The reading profile and the owner's own faces

- `reading_preferences.apply` (:108-109) already swaps the default Plex Sans for FACE. Add the same swap for code: `if names[2]=='IBM Plex Mono' and bt.MONO!='IBM Plex Mono': names=names[:2]+(bt.MONO,)`.
- `family(…, fixed=True)` accepts Kasandra Elite Mono, because it is fixed pitch.
- A face the owner chose herself is never swapped: only the untouched defaults are.
- control_qt.py:400-404: report the effective families after the swap. In Kasandra today it reports Plex while the window shows the typewriter face.

### Sizes, spacing and leading in Kasandra, at 14 pt (everything scales with the interface size)

| role | face | px | letter spacing | leading |
|---|---|---|---|---|
| her words in cards, your bubbles | Kasandra Elite | 18 | 0 | 125% (see (d)) |
| prose in documents | Kasandra Elite | prose_pt | 0 | profile line height (1.4) |
| menus, head menus, tabs, tree rows, buttons, lower band | Kasandra Elite | 16 | 0 | font (none) |
| her name in the right column | Kasandra Elite | 24 | 0 | — |
| This: / Now: lines, the fold line | Kasandra Elite | 16 / 14 | 0 | font |
| quiet notes, model line, hand words | Kasandra Elite | 14 | 0 | font |
| section labels (JOT IT DOWN) | Kasandra Elite | 13 | +1.0 (as now) | — |
| meter keys (CPU GPU RAM TXT) | Kasandra Elite | 12 | +0.5 | — |
| meter readings | Kasandra Elite Mono | 14 | 0 | — |
| the typing line (OneBox) | Kasandra Elite Mono | 16 | 0 | — |
| a line on a card's slab | Kasandra Elite Mono | 15 | 0 | 125% |
| Terminal, console, log lists, code and text views | Kasandra Elite Mono | code_pt | 0 | font (1.2 em) |
| tags (SOURCE, SHEET, CURRENT, the 44 px tag column) | Kasandra Elite Mono | 12–13 | +0.5 | — |
| addresses, file names in Field facts, the workspace path, AddressChip | Kasandra Elite Mono | 14 | 0 | — |

- **The floor:** no Kasandra text under 12 px. At 12 px the slashed zero still reads (`z_ke14.png` shows 14 px, which is clear).
- **Remove field_qt.py:210's −0.35 spacing.** Negative tracking makes a worn face's letters touch.

### Where alignment matters, and how it stays right

1. **Terminal and console output** (console_qt): Mono at 0.6 em, identical to Plex Mono's advance, so columns line up exactly. Rows are 19.2 px at 16 px instead of 20.8.
2. **The right-click line preview** (context_menu.py:2603-2612 counts from `'M'`): the same fixed pitch, so the maths does not change.
3. **ASCII art** (PanelInk and ArtPanel, boss_qt.py:186-193 and :319-351; code_rain): the cells keep their width. The cell height comes from `fm.height()`, which these routines already read.
4. **The log lists and the code views**: fixed pitch.
5. **The 44 px tag column** (shell2.py:2952): Mono at 13 px is 7.8 px a character, the same as Plex Mono 13, so 5 characters take 39 px and fit as before.
6. **Numbers**:
   - Both faces have tabular digits, so numbers no longer jitter as they change (meters) and right-aligned columns line up.
   - The Field compare table's values (field_qt.py:449-470) go in Mono.
7. **Elision**: measured everywhere already. It stays right because of the arcFace rule above (measured face = drawn face).
8. **1/l/I and 0/O**: the derived glyphs. `I` keeps both bars, `1` keeps its full base and flag, `l` has a right foot only, and `0` carries a slash that `O` lacks (`z_ke16.png`).

---

## (c) The hologram in the lower left

### The asset, verified and decoded with its alpha

- `branding/kasandra/hologram.webp`: 800×875, SHA-256 `b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec`. Recorded in README.md and MANIFEST.json.
- **Verification uses a marks table, not the catalog**, so the catalog tests keep their 8 and 5 counts:
  - `kasandra_art.MARKS = {'hologram.webp': 'b73f…', 'kp_emblem.png': …, 'kp_emblem_34.png': …, 'kp_emblem_68.png': …, 'wordmark.webp': '0a8d44e5…eb1e6', 'kp_monogram.png': '7c5b3c9c…a073'}`.
  - `kasandra_art.mark(base, name)` returns the path or None. It uses the same cached (mtime, size) hash check as `usable()` (:113-121) and the same 16 MB limit.
  - The wordmark (boss_qt.py:77) and the Apps icon load through `mark()` too.
- **Decode keeping alpha:** `kasandra_art.cutout(path)` reads with `QImageReader` and converts to `Format_ARGB32_Premultiplied`, never `source()`'s RGB32 (:181). The decoded image is cached once.
- Work only on the figure's ink box with 6 px round it: `INK = QRect(80, 16, 606, 816)`, aspect **a = 0.7426**.
- `portrait.webp` is not used. The hologram has the alpha that the lower left needs.

### Structure

New module `workbench/hologram_qt.py`.

**Pure part**, testable without Qt:
- `hologram_box(P, I, rows_end, delete_w, floor, scale)`
- `MOTION` (the table below)
- `frame_plan(state, t, rng, still)`, which returns `{opacity, noise_index, scan_offset, tear|None, base_rgb, base_alpha, sweep_y|None}`

**Qt part:** `HologramStage(QWidget)` and `Layers`.
- `HologramStage` is a child of the left `PaneBody`, raised over both the content and the foot.
- It has `WA_TransparentForMouseEvents` (clicks and drops reach the tree and DELETE as now).
- It has `WA_OpaquePaintEvent`: it fills GROUND #171b3c itself. Its rect never covers a row or DELETE, so nothing under it needs painting.
- Accessible name: `named('Kasandra, projected') + ' · ' + state word`.
- `pane_qt.install` creates it in Kasandra only, as `host.hologram`.

**Re-placed synchronously on:**
- the current tree's `itemExpanded`, `itemCollapsed`, `verticalScrollBar().rangeChanged`, and its model's `rowsInserted`, `rowsRemoved`, `modelReset` and `layoutChanged` (the reference patch's list);
- `nav.stack.currentChanged`;
- the end of `PaneBody.arrange()` and of `pane_qt.place()`;
- `boss_qt.choose_art` (add it to the loop at :481-483);
- `set_glow`.

What I take from the reference patch: the signals. What I leave: painting inside the tree's `paintEvent`, scaling the picture on every paint, the 150 px floor, the 288×316 centred box, and the portrait avatar.

### Placement (pane coordinates)

- **DELETE's box:** x_D = P − I − D.w, y_D = H − I − D.h. The floor is y_D + D.h, the can's bottom line.
- **rows_end:** the bottom of the last visible row of the current tree, mapped from its viewport to the pane. None if the tree scrolls (`vbar.maximum() > vbar.minimum()`).
- **The free box:** left = I; right = x_D − 12·s; top = rows_end + 12·s; bottom = floor. W = right − left, Hb = bottom − top.
- **The figure:**
  - h = min(Hb, 360·s, ⌊W / a⌋); w = round(h·a).
  - Shown only if h ≥ 120·s and w ≥ 89·s.
  - x = left + (W − w) / 2 (centred left of DELETE); y = floor − h.
  - The stage is (x, y, w, h + 8·s): the 8 px below the floor hold the base's glow, inside the pane's bottom inset.

With D.w ≈ 116 and P = 354, W = 194, so the width cap is ⌊194/0.7426⌋ = 261 tall.

| place | 1920×1200 (window x, y, w, h) | 1366×768 |
|---|---|---|
| Files, as the workspace opens (13 rows) | 16, 862, **194×261** | 43, 502, **140×189** |
| Machine (9 rows) | 16, 862, 194×261 | 16, 430, 194×261 |
| Files, 15 rows | 194×261 | 99×133 |
| Files, 16 rows | 194×261 | steps aside (Hb 105) |
| Files, all 27 rows open | 28, 894, 170×229 | the tree scrolls: steps aside |
| Settings | the tree scrolls: none | none |

- She stands on DELETE's floor, beside it, in the corner the owner pointed at.
- Mocks from the 0.8.2 frames: `holo2/left_1920x1200.png` and `holo2/left_1366x768.png`.
- A wider pane, dragged by the owner, gives her more width, up to the 360·s cap.

### When she steps aside (immediately: no fade, because the tree's need comes first)

| case | what happens |
|---|---|
| the tree scrolls, or the free box is under the floor | hidden |
| the Settings tab | hidden (its tree scrolls) |
| the Clean desk (`desk_art == 'clean'`) | hidden, the timer stopped, the layers dropped |
| the ASCII desk | a still ASCII figure: Kasandra Elite Mono at 8·s px (4.8×9.6 cells, 40×27 at 194×261), ramp `" .:-=+*#%@"` by luminance × alpha, in VIOLET_PALE at 0.8. The base line is in the state colour. No motion. |
| Graphite appearance | no stage |
| the mark fails (bytes changed) | no stage; the left column is as in 0.8.2 |

### The animated static

**Layers, made once per (w, h, dpr) and keeping the last two sizes, so that a folder opened and closed costs nothing:**
1. `figure`: the INK crop scaled smooth, with a code fade (DestinationIn) over its lowest 14%, so she ends in light, not in a cut.
2. `cyan` and `pink`: silhouettes of `figure` in READY #83eaff and #f23e6b.
3. `grey`: a desaturated twin, used only for blocked.
4. `noise[6]`:
   - specks over 1 pixel in 9, alpha uniform 0–1, half light (#ffffff) and half dark (#0a081e), masked to the figure;
   - made from `random.Random(seed).randbytes()` into a Grayscale8 image used as the alpha channel, not from per-pixel painter calls;
   - target build time: under 20 ms. My Python-loop prototype took 31–49 ms.
5. `frame`: one reusable ARGB32 buffer.

**Each frame** (a QTimer at 83 ms = 12 fps, `Qt.CoarseTimer`; all motion is a function of `time.monotonic()`, so a late frame never slows anything):
- `frame` = figure;
- blocked only: grey at 0.5;
- `noise[k]` at the state's static opacity, with k cycling through a fixed shuffled order;
- scan lines cut with DestinationOut: 1 px every 3 px at alpha 70/255 (27%), offset by drift·t mod 3;
- the working sweep, or the completed lock, with SourceAtop so it lands on her only;
- an optional tear.

Then the stage paints:
1. GROUND;
2. the beam;
3. the base;
4. `cyan` at +1 px x and opacity 0.08 (the projector's fringe);
5. `frame` at opacity × flicker.

| effect | idle | working | awaiting_approval | completed (20 s hold) | blocked (45 s hold) |
|---|---|---|---|---|---|
| figure opacity | 0.80 | 0.84 | 0.86 | 0.82 | 0.62, colour drained 50% |
| static (noise layer opacity) | 0.30 | 0.39 | 0.19 | 0.28 | 0.28 |
| scan-line drift, downward | 6 px/s | 14 px/s | 4 px/s | 6 px/s | 3 px/s |
| flicker | ×(1 + 0.03·sin 2π·0.7t + 0.02·sin(2π·1.9t+1.3)·sin 2π·0.23t), within ±5% | same | none: she holds still while she waits for you | same as idle | none |
| tears | Poisson, mean 11 s, at least 4 s apart | mean 8 s | none | none | one, at the moment it starts |
| base colour | VIOLET #ab8eda | READY #83eaff | OWNER #fa507c | READY, back to VIOLET over the hold | RED #ff3b5c |
| base breath | 2.8 s ±15% (the tree's lit path breathes at 2.8 s: they breathe together) | 1.4 s ±20% | 2.8 s ±25% | ±10% | none: a refusal is a fact, not an alarm |
| extra | — | a write band 20 px tall, #b9f4ff at 18% peak, rising bottom to top every 2.4 s | — | one lock sweep, top to bottom, 600 ms, 25%, then still | — |

**A tear:**
- a band 2–5 px tall;
- its y is one of the picture's own baked glitch rows (scaled) 60% of the time, otherwise uniform in the top 80%;
- it shifts ±3–7·s px for 2 frames (about 166 ms);
- it carries a cyan copy at −1 px and a pink copy at +1 px, at 22%, inside the band only.

There is no constant colour split: that would read as blur on her face.

**The base and beam:**
- an ellipse of light at (cx, floor − 3), radii 0.36w × 0.058w, in the state colour, alpha 0.42 × breath;
- a 1 px line 0.44w long, alpha 0.55 × breath;
- a trapezoid beam from 0.32w wide at the floor to 0.92w at 45% of her height, alpha 0.10 × breath fading to 0 upward;
- on a state change the base colour cross-fades over 400 ms (instantly when still).

**The state:**
- `kasandra_art.current_state(host)`, polled every 1 s, plus `kasandra_art.watch(host, stage)` for nudges. This carries 0.8.0's "art by the state of the work" into the hologram.
- The colour of the base is the signal. Motion barely changes, so the periphery never pulls the eye.

**Measured motion** (`motion.py`), as the mean per-pixel |ΔL| between consecutive frames over the stage:

| state | mean | max |
|---|---|---|
| idle | 5.0/255 | 7.4 |
| working | 8.3/255 | 8.9 |
| awaiting_approval | 3.5/255 | 6.9 |
| blocked | 2.8/255 | 5.7 |

This is fine-grained static, not flicker.

### Reduce motion, calm, Clean

`still = pane_qt.still(view) or menu_catch.calm(stage)`, which covers Reduce motion and the Clean glow (glow ≤ 0). When still:
- no timer;
- one frame: t = 0, noise[0], scan offset 0, flicker 1, no tear, no sweep, base at its state colour without breath;
- a state change repaints once (colour is not motion).

Two frames taken 1.4 s apart are identical (measured: `still: identical True`). On the Clean desk there is no stage at all.

### CPU budget and how it is met

- **Budget:** at most 1.5 ms per frame at 194×261 dpr 1 (3 ms at dpr 2), and at most 2% of one core on the ThinkPad.
- **Prototype:** 0.60 ms per frame at 194×261 and 0.55 ms at 140×189, composed offscreen: 0.7% of one core at 12 fps.
- **How:**
  - layers cached per size and dpr;
  - one reusable frame buffer;
  - the stage paints only its own rect (its own widget, opaque);
  - the timer runs only while all of these hold:
    - the appearance is Kasandra and the desk is Illustrated;
    - the stage is placed and `isVisible()`;
    - the window is not minimised;
    - `QGuiApplication.applicationState() == Qt.ApplicationActive`;
    - not still.

    `applicationStateChanged` and the window's `changeEvent` (WindowStateChange, ActivationChange) call `stage.wake_or_sleep()`. Asleep, she shows her current frame frozen.
- **One improvement to existing code:** `BranchTree._breathe` (pane_qt.py:499) updates only the rows' extent (`viewport().update(QRect(0, 0, w, rows_end))`), not the empty space under them that the stage now holds.

---

## (d) The right column with the picture gone (Kasandra; Graphite unchanged)

### The masthead, in place of the picture row (shell2.py:1784-1794)

The masthead is a widget whose height is `host.panes['tab_height'] − 10` (47 at 14 pt). Its last pixel row is a 1 px LINE #3b4479 rule across the content width. That rule falls on the left pane's tab-row rule (pane y 56 at both sizes): obsessive symmetry. If the owner's fonts are taller, it grows instead of clipping.

- **Row 1:**
  - **Kasandra** (`named('Stacy')`), Kasandra Elite 24 px, VIOLET_PALE #d2c4f5, weight 400, bottom-aligned.
  - At the right, a state dot: 5 px core in a 10 px halo at 30% alpha, in the same colour as the hologram's base.
  - Then the state word in 14 px QUIET:

    | state | word |
    |---|---|
    | idle | quiet |
    | working | at work |
    | awaiting_approval | waits for you |
    | completed | done |
    | blocked | stopped |

    One table, `kasandra_art.STATE_LOOK = {state: (word, colour role)}`, is shared by the stage and the masthead. Accessible name: `named('Kasandra is ') + word`.
- **Row 2:** the model line (`self.model`, 14 px QUIET), then ` · `, then the hand link (`self.hand`, 14 px). The model is elided on the right to whatever room the hand leaves, with the full name in its tooltip.
- The `PanelInk(host, 'face')` is not built into the layout in Kasandra. `self.portrait` stays as an attribute that never shows. `signature` stays hidden as now. In Graphite all of this is unchanged.

### Below the masthead

- 12 px space.
- The This: and Now: lines with their 17 px cyan marks, as now, at **16 px** instead of 18. They are status, and her words are 18.
- 8 px space.
- The thread.

### The thread

- **Widths:**
  - `self.lines.setContentsMargins(0, 0, 4, 0)`, from 14 (shell2.py:1816).
  - Card padding: 10 px after the 3 px honey edge on the left, 8 px on the right, 9 px top and bottom (`Bubble.box`, shell2.py:1723).
  - Her card text width goes from 280 to 297 px: about 31 to 33 characters a line at 18 px (measured average advance 9.0 px).
- **Leading:**
  - Her words and your words are set as one rich-text paragraph, `<p style="line-height:125%;margin:0">…</p>`, built by a helper `leaded(label, text)` that escapes the text, keeps `breakable()`, and turns `\n` into `<br>`.
  - Measured: `QLabel.heightForWidth` honours it (4 lines at 18 px: 72 px plain, 94 px at 130%), so the fold's sums stay right.
  - Pitch: 22.5 px instead of 18.
- **Your bubbles:**
  - right-aligned and hugging their words, up to 85% of the thread's width;
  - replace the 30 px margin and 1:5 stretch (shell2.py:1912-1913) with `setMaximumWidth(0.85·w)` and a stretch on the left;
  - VIOLET_SOFT #2b2660 with a 1 px VIOLET_DEEP #5f4fa8 edge, radius 8.
- **The line slab:**
  - Kasandra Elite Mono 15 px through `arcFace='mono'` (this fixes F17), 125% leading, on ROYAL_SOFT with a ROYAL 3 px edge.
  - Break points come from a new `breakable_line()` that puts a zero-width break after `,`, `|`, `/`, `:` and `=`. The 18-character chunks of `breakable()` remain only as a fallback, so `tit / le` becomes `kind, / title,state,by` (`right_1920x1200.png`).
- Spacing between items: 12 px, from 10. The fold line is 14 px QUIET.
- Her answers already scroll to their first line (shell2.py:1988 and following). Keep that.

**Gain:**
- The top block goes from 181–196 px to about 141 px.
- The conversation box goes from 322×817 to about 322×860 at 1920, and from 322×385 to about 322×430 at 1366 (+12%).
- Cards grow by their leading. The latest card still always shows, as now.

**The look:** no new plates and no new colours. The single masthead rule echoes the left tab rule. Her cards keep CARD fill, the HONEY edge (hers) and radius 6. The right foot (53 px) stays empty as DELETE's mirror.

---

## (e) The kp emblem

### The cut (tools/cut_kp_emblem.py; my prototype is `kp_cut.py`)

- **Input:** `kp_logo.png`, 1254×1254 RGB, SHA-256 `94d7bfb3…afaa`. Its ground is flat #070221 (std 0.6, max deviation 2). Store it as `branding/kasandra/source/kp_logo.png` with its SHA-256, as the source for any later cut.
- **Unmixing against the emblem's own inks:**
  - Inks F: cream (254,241,227), pink (242,62,107), pink (253,54,108), violet (118,53,254).
  - For each pixel C and each ink: αᵢ = clamp(((C−G)·(Fᵢ−G)) / |Fᵢ−G|², 0, 1), with residual rᵢ = |C − (G + αᵢ(Fᵢ−G))|.
  - The ink with the least residual wins. The stored colour is the ink itself, unpremultiplied (never darkened by the navy), at αᵢ.
  - Where no ink explains a pixel (r > 40 where cream meets violet; 17 pixels in all), it is kept opaque as it is.
  - α < 0.04 becomes 0; α > 0.97 becomes 1.
  - The bird's dark circuit lines and eye are the ground showing through, so they become clear and show the band behind them.
- **Trim:** ink bounds x 259–980, y 417–883, plus an 8 px clear margin, giving **737×482**, aspect 1.53.
- **Proof:**
  - Composited back over #070221, it reproduces the original with mean error 1.9/255 and p99 13.
  - On a pale test ground its edge pixels average luminance 208, against 165 for naive distance-alpha. The naive cut leaves a navy fringe; this one leaves none.

### Assets (all in branding/kasandra/, each SHA-256 recorded in README.md, MARKS and MANIFEST.json)

| file | size | use |
|---|---|---|
| `kp_emblem.png` | 737×482 RGBA | master |
| `kp_emblem_34.png` | 52×34 (Lanczos from master) | Apps button, dpr 1 |
| `kp_emblem_68.png` | 104×68 | Apps button, dpr 2 |
| `kp_tile_{48,64,128,256}.png` | square | window icon in Kasandra: a #070221 rounded square (radius 22%) with the mark centred at 84% of its width |
| `kp_tile_{16,24,32}.png` | square | window icon at small sizes: the "kp" letters only on the tile, because the bird's legs fall under 1 px |
| `kp_monogram.png` | 256×256 | kept in the pack and in MARKS (nothing is removed), no longer shown. README gets its SHA `7c5b3c9c…a073`. |

### Where it goes

- **The Apps button** (shell2.py:586-597):
  - `QIcon` with both sized files, through `kasandra_art.mark()`;
  - `setIconSize(QSize(round(52·s), round(34·s)))`;
  - button about 70×60 (icon plus 9 px each side), its right edge where it is now;
  - `paperIcon`, accessible name `'Apps'`, tip `'Installed apps and capabilities'` and `text ''` unchanged;
  - centred in the band above the 2 px cyan rule;
  - if a mark fails, the word `Apps ▾` shows instead.
- **How it reads at 34 px tall** (`kp/kp_unmixed_h34_x6.png`):
  - "kp" is about 29 px tall with 4–6 px stems, cream on #141734: crisp, and about the visual size of the old monogram (32×30 of ink);
  - the violet trace is about 1 px;
  - the bird is a pink silhouette with 1 px legs; the circuit lines inside it become texture.

  It is the brightest thing in the head's right corner, and it is static.
- **The window icon:** `graphite_brand.window_icon()` (graphite_brand.py:92) picks the Kasandra tiles when `APPEARANCE == 'kasandra'`. The splash stays Graphite's.

---

## (f) Tests and frames

### Tests that change

| test | change |
|---|---|
| test_kasandra.py:54 | `assertEqual(k['DISPLAY'], 'Kasandra Elite')`; add `k['FACE'] == 'Kasandra Elite'` and `k['MONO'] == 'Kasandra Elite Mono'` |
| test_kasandra.py:45 | add `g['MONO'] == 'IBM Plex Mono'` and `g['FACE'] == 'IBM Plex Sans'` |
| test_desk_acts.py:186 | `(False, 'DELETE, once emptied, cannot be brought back')` |
| test_desk_acts.py:193 | path `'Move to Trash'` → `'Delete'`, so it again checks that the file row is refused to a free hand |
| test_graphite.py:292 | the KEPT string ends `"… and deletions go to DELETE."` |
| test_context_menu.py:678-712 | no assertion change. It passes because files_qt.py:478 and FOLDED :2924 both say `'Delete'`. |
| tools/check_desk_ui.py:253-257 | redraws `'DELETE'` |

These stay as they are: test_kasandra.py:90-94 and :134-140 (the catalog keeps its 8 scenes), :115-121 (the monogram file is kept), and test_desk.py:163-175.

### New tests

**test_delete_words.py**
- `test_the_can_says_DELETE`:
  - `TrashCan.WORD == 'DELETE'`;
  - `can.accessibleName() == 'DELETE'`;
  - `'restore puts it back' in can.toolTip()` and `'Trash' not in can.toolTip()`;
  - `can.width() == pane.trash_size(1.0, ceil(word ink of 'DELETE'), ceil(ink of '999'), can_ink(30), gap)[0]`.
- `test_no_Trash_is_shown`:
  - parse every `workbench/*.py` with `ast`;
  - look at string constants that are not docstrings;
  - none matches `r'\bTrash\b'`;
  - exceptions: version.py (history), and constants matching `^/?files\.trash` (lines and operations).
- `test_Delete_and_Erase_never_meet`:
  - over the entries context_menu builds for a file, a selection and a passage, every label `'Delete'` has key `'trash'` and section `'danger'`;
  - the label `'Erase'` has key `'edit:delete'`;
  - no entry's label is `'Delete'` with another key;
  - memory_qt's source contains `'Erase profile and feedback'` and no `'Delete profile'`.
- `test_DELETE_is_a_search_place`: `('DELETE', 'trash')` is among the places in `commands()`.

**test_typewriter_faces.py**
- Both TTFs' SHA-256 equal the values in NOTICE.md. `addApplicationFont` gives `['Kasandra Elite']` and `['Kasandra Elite Mono']`.
- `QFontDatabase.isFixedPitch('Kasandra Elite Mono')`, and `reading_preferences.family('Kasandra Elite Mono', True) == 'Kasandra Elite Mono'`.
- For every character of `string.ascii_letters + string.digits + string.punctuation + ' '` at 16 px, Mono's advance equals `QFontMetricsF(IBM Plex Mono 16).horizontalAdvance('M')` within 0.01.
- `len({round(QFontMetricsF(Kasandra Elite 16).horizontalAdvance(d), 2) for d in '0123456789'}) == 1`.
- `QFontMetricsF('Kasandra Elite', 16).height() == QFontMetricsF('Special Elite', 16).height() == 16.0`, so the rows do not move.
- **Distinct glyphs.** Use `QRawFont.fromFont(QFont(family, pixelSize=2048))` and `pathForGlyph`, with y measured up from the baseline:
  - the `0` path contains the counter's centre (606, 737) and `O`'s path does not contain (631, 688);
  - the `l` path contains no point of the box x 0–420, y 0–110;
  - the `1` path contains (120, 60).
- Every other letter A–Z and a–z, except `l`, has the same bounding rect (within 1 unit) and element count as Special Elite's.

**test_hologram.py (pure)**
- `hologram_box(354, 16, 429, 116, 1062, 1.0) == (16, 801, 194, 261)`
- `hologram_box(354, 16, 429, 116, 630, 1.0) == (43, 441, 140, 189)`
- `hologram_box(354, 16, 317, 116, 630, 1.0) == (16, 369, 194, 261)`
- `hologram_box(354, 16, 513, 116, 630, 1.0) is None` (Hb = 105)
- For any result: `abs(w/h − 0.7426) < 0.01`; `x + w ≤ 354 − 16 − 116 − 12`; `y + h == floor`.
- `MOTION`:
  - `MOTION['awaiting_approval']['tears'] is None`, and likewise for completed and blocked;
  - the flicker amplitude sum is at most 0.05;
  - `MOTION['idle']['period'] == 2.8`, the same as the period inside `pane_qt.breath`.
- For every state and t in 0–10 s with `still=True`, `frame_plan` returns flicker 1.0, scan_offset 0, noise_index 0, tear None and sweep None.

**test_hologram_qt.py (offscreen, `GRAPHITE_APPEARANCE=kasandra` in a subprocess, as NameTests does)**
- `kasandra_art.mark(PACK, 'hologram.webp')` is a path. In a temporary copy with one byte changed, it is None and no stage is made.
- `kasandra_art.cutout(path).hasAlphaChannel()`, and pixel (2, 2) has alpha 0.
- With `reduce_motion` True: `stage._timer.isActive()` is False after `place()`.
- With `desk_art 'clean'`: `stage.isHidden()` and `stage.layers is None`.
- Illustrated, shown and active: the timer interval is 83.
- When the application goes inactive, the timer stops.
- 24 frames composed at 1/12 s steps in idle have mean per-pixel |ΔL| at most 10/255 and a stage-mean luminance change at most 2% between frames.
- Two still frames are byte-identical.

**test_right_column.py (Kasandra, offscreen window)**
- `face.masthead.name.text() == 'Kasandra'`, family `'Kasandra Elite'`, 24 px.
- The masthead rule's window y equals the left tab rule's window y.
- `face.portrait.isVisible()` is False.
- For each state, `face.masthead.word.text()` equals `STATE_LOOK[state][0]`, and the dot colour equals the stage's base colour.
- `face.lines.contentsMargins().right() == 4`.
- A 4-line Bubble's `text.heightForWidth(297)` is at least 1.2× the plain QLabel's.
- The slab's `font().family() == 'Kasandra Elite Mono'` after `ensurePolished()` under the window's sheet. This is the F17 regression test.

**test_kp_emblem.py**
- The SHA-256 of `kp_emblem.png` and the sized files equal README.md's and `MARKS`'.
- `hasAlphaChannel()`; pixel (2, 2) has alpha 0; `abs(w/h − 1.529) < 0.02`.
- Re-composited over #070221 against the source crop: mean error at most 2.5 and p99 at most 16.
- Pixels with 0.1 < α < 0.9 are within 12 of one of the four inks.
- In Kasandra, `programs.iconSize() == QSize(52, 34)` at 14 pt, `accessibleName() == 'Apps'` and `text() == ''`.

### Frames that prove it (new `tools/look_083.py`, after the readers' `look_frames.py`)

Taken on After Hours 07, Kasandra, Illustrated, 14 pt, at 1920×1200 and 1366×768.

| frame | what it proves |
|---|---|
| L1 | Files, at both sizes: the hologram at the rects in the table, DELETE at x 222 |
| L2 | Machine at 1366 (194×261) |
| L3 | Settings: no hologram |
| L4 | Files fully open: 170×229 at 1920, none at 1366 |
| L5 | the Clean desk: none |
| L6 | Reduce motion: two shots 1 s apart, identical in the stage rect |
| L7 | a 24-frame strip at 12 fps with its ΔL numbers |
| L8 | the five states, side by side |
| R1 | the right column at both sizes: Home, and after two Traces (masthead rule on the left tab rule; 33 characters a line; the slab in Mono, broken at commas) |
| H1 | the head band ×3 with the emblem |
| T1 | Terminal `ls -l` in Kasandra Elite Mono beside a Plex Mono reference |
| G1 | the glyph sheet `Il1| 0Oo 07 10 l0O1` at 12, 14, 16 and 18 px in both cuts |
| C1 | CPU over 30 s with the window open and idle, Illustrated against Clean; the difference is at most 2% of one core |

---

## 7. Prototypes behind the numbers (scratch, not for the tree)

Everything is under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/`.

- **Faces:**
  - `derive.py` builds `fonts/KasandraElite-Regular.ttf` and `fonts/KasandraEliteMono-Regular.ttf`;
  - `faces.py` gives `faces.png`, and the zooms `z_ke14.png`, `z_ke16.png` and `z_kem14.png`;
  - `distinct.py`;
  - `se_big.png` shows Special Elite's `1l` and `0O` problem;
  - `leadtest.py` is the leading measurement.
- **Emblem:** `kp_cut.py` gives `kp/kp_emblem_master.png` and `kp/kp_unmixed_h{30,34,36}_x6.png`, against `kp/kp_naive_*`.
- **Hologram:**
  - `holo.py` gives the timing, `holo2/states_194x261.png`, `holo2/states_idle_working_x2.png`, `holo2/left_1920x1200.png` and `holo2/left_1366x768.png`;
  - `motion.py` gives the frame-difference numbers.
- **Right column:** `right.py` gives `right_1920x1200.png`. The 1366 mock overflowed its fixed box, because it has no scroll area as the app does; ignore it.

## Open for the owner

- **DELETE** reads as a capitalised name in her sentences ("is in DELETE, which gives it back"). That is the owner's word, and it stands out as a deletion should.
- **The face names** "Kasandra Elite" and "Kasandra Elite Mono" appear in Settings' face list. Nothing on screen says "Lain".
- **The window icon tile** is a recommendation. The Apps button is the part she asked for.