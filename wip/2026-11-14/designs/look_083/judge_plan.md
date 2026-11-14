# 0.8.3 build plan: DELETE, the typewriter faces everywhere, Kasandra's hologram in the lower left, her column, the kp emblem

Repository: /home/user/Struthio at 0.8.2 (d1df337). The judging pass changed nothing in the repository. My own measurements are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_judge/.

---

## 0. Verdict

| | owner's six directions | readability at 1366×768 | cost (CPU, risk to tests and behaviour) | buildable in one session | total |
|---|---|---|---|---|---|
| **A (quiet and readable)** | 4 | 4 | 4 | 5 | **17/20** |
| **B (after hours, bold)** | 4 | 3 | 3 | 3 | **13/20** |

**The base is A.**
- A's word system holds together: DELETE is the place, Delete is the verb, Erase means gone for good.
- A fixes the face for words as well as for code: a slashed zero, an `l` with a right foot only, and tabular digits.
- A's hologram motion is calm enough for long work.
- A's tests are the most complete of the two.

**Taken from B:**
1. **Two stances for the hologram.** At 1920 she stands large and centred above the foot; at 1366 she stands in the corner beside DELETE. At 1920 A leaves her at 194×261, with about 300 px of the dull space still empty above her.
2. **The word DELETE is spaced** +1.0 px between letters (Kasandra) and +0.8 px (Graphite).
3. **Search still finds DELETE** when you type "trash".
4. **Fallback fonts are named** with `QFont.insertSubstitutions`, so ← and box-drawing characters come from Plex Mono at the same width.
5. **The kp emblem is 38 px tall**, with a "small" cut in which the thin strokes are thickened, and the monogram as fallback. The window icon uses the same emblem on a tile.
6. **The noise is a set of shared 64×64 tiles** drawn with SourceAtop, instead of full-size noise images for every size.
7. **Moments:**
   - **Power-up:** a short reveal when she first appears, 360 ms.
   - **Touch:** a small tear when the pointer reaches her. This follows the owner's after-hours words, "responds with a little more force than you expected", RECORD_OF_DIRECTIONS.md:283.
8. **Her column as her terminal:**
   - the TERMINAL_GROUND #11132c behind her words;
   - a TEAL_EDGE line along the column's inner edge, with a 32 px tick on the masthead rule;
   - a block cursor in the state colour beside her name;
   - the model name in the mono face, shortened in the middle.
9. **HONEY means "done"**, so that each of the five states has its own colour.

### Claims checked against the code, and what the plan corrects

1. **The window sheet beats `setFont`, family and size.**
   - `reading_preferences.apply` sets `QWidget {font-family; font-size}` on the window (reading_preferences.py:113).
   - Checked offscreen: a QLabel given `setFont(mono)` reports the sheet's family and the sheet's size.
   - With A's `*[arcFace="mono"]` rule, the family is right but the size stays the sheet's: measured 10.5 pt, not the 15 px set with `setFont`.
   - So the line slab at shell2.py:1944 is drawn in the words face today (`bt.line_sheet()`, boss_theme.py:76-79, sets no family).
   - **Fix:** each such widget gets its own sheet with both family and px (see §2.4). Checked: that works.
2. **The mono face's line height.**
   - A's Mono is 1.2 em (19.2 px at 16 px). B's is 1.3 em, centred (ascent 1747, descent 915).
   - Plex Mono is ascent 1.025 em and descent 0.275 em (hhea 1025/−275 per 1000 units).
   - `pane_qt.place` measures the tab row height from `tab_font` (pane_qt.py:634), and the Field, the typing line and Terminal all inherit their heights from the mono face.
   - **Fix:** use Plex Mono's split exactly: ascent 2099 and descent 563 per 2048 units. Baselines and heights then match, and no row moves.
   - Special Elite's ink fits inside that box: descenders reach −483, accents +1806.
3. **Special Elite kerns digits.**
   - Its `kern` table has 2048 pairs; 86 of them involve a digit.
   - Its GPOS pair lookups list `four`, `seven`, `nine` and `one` in their coverage.
   - "Tabular" must therefore be proved over all 100 digit pairs, not only over single advances.
   - Measured: A's prototype gives '71' = 2 × 9.797 px. The derive tool still removes digit-to-digit pairs, and the test guards it.
4. **A's derive.py rebuilds every glyph through pathops** and deletes `fpgm`, `prep` and `cvt ` from the words face.
   - **Fix:** in the words face only the ten digits and `l` change (the slash is part of the zero).
   - Every other glyph stays byte-identical, with its hinting.
   - The changed glyphs get empty instruction programs.
5. **B's Machine figure is wrong.**
   - Nine rows end at pane y 317 (65 + 9×28); B used 191.
   - Content starts at pane y 65 (tabs 57 + gap 8); the left PaneBody starts at window y 61.
6. **The DELETE box, measured with the real trash_can_qt code:**
   - the old box is 102×29 (the code map's figure is right);
   - 'DELETE' at letter spacing 0 gives a 115 px box (A said 116);
   - at +1.0 it gives **120 px** (B said 121);
   - the can's x is 354 − 16 − 120 = **218**.
7. **The name tag.** Both designs put a 24 px "Kasandra" at the top of her column.
   - 13 November, the owner: "Probably don't even need the Stacy name tag taking up space" (RECORD_OF_DIRECTIONS.md:196). shell2.py:3457 keeps her signature hidden for that reason.
   - **Fix:** her name appears once, at the size of her words, in a status row, never as a tag.
8. **Leading through rich text works**: a 5-line card at 297 px measures 95 px plain and 119 px at 125% (×1.253).
   - But `desk_doers.read_desk` reads `label.text()` (desk_doers.py:633-634), which would then return HTML.
   - **Fix:** each card label keeps a plain copy.
9. **The fold keeps 14 px** hard-coded: `fold_earlier` uses `self.thread.width() - 14` (shell2.py:1888). It must follow the new margin.
10. **The picture square keeps a timer.** `PanelInk(host, 'face')` is parented to SlateFace and made available at shell2.py:1788 and :1795, and it runs a 2 s watch timer (boss_qt.py:212-216). In Kasandra it is not built.
11. **The hologram's real bounds.**
    - Pixels at alpha ≥ 8 span x 86–681 and y 21–830.
    - At alpha ≥ 1 they reach 0–771 and 10–874; these are the faint glitch lines.
    - Crop **QRect(80, 15, 608, 822)**, aspect **a = 608/822 = 0.73966**.
    - SHA-256 of hologram.webp and kp_logo.png match the brief.
    - The monogram is 7c5b3c9c…a073 and the wordmark 0a8d44e5…eb1e6.
12. **Cost, measured** (offscreen, Qt raster, PySide6 6.8.3, this container):
    - decoding the picture once: 14 ms;
    - one composed and painted frame, with the scan lines drawn by a 1×3 brush: 0.61 ms at 281×380 and 0.20 ms at 136×184. At 12 fps that is 0.73% and 0.24% of one core;
    - mean frame-to-frame change in brightness: 4.4–4.8/255.
13. **Seed inputs** were checked with an AST read of `workbench/stacy_foundation.py` SEED_FILES (marked **[seed]** below).
    - Changing them means rebuilding the seed and the manifest: `python3 tools/package_graphite.py --manifest-only`. This rebuilds `project/stacy_seed/current` and `MANIFEST.json`, as every recent commit did.
14. **Runtime dependencies are PySide6 only** (requirements-qt.txt): no numpy and no Pillow. So every test uses Qt alone.
    - The two build tools run outside the app:
      - the fonts with /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python (fontTools 4.68, skia-pathops, PySide6 6.8.3);
      - the emblem with `python3 -I` (numpy 2.5, Pillow 12.3).

### Before starting
- Run the focused list once and record which tests already fail. The 0.8.2 commit 1f59293 notes that test_desk and test_graphite already failed.
- Open the owner's files with Qt or `python3 -I` only; they are data. Copy them in:
  - /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/in/holo_082920/x/branding/kasandra/hologram.webp → `branding/kasandra/hologram.webp`
  - /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/in/holo_082920/kp_logo.png → `branding/kasandra/kp_emblem_source.png`
- portrait.webp and kasandra-hologram.patch are **not** used. The patch was only a reference for where she goes, and the signals it listens to.

### Order of work
1. DELETE words.
2. The faces: build, then wiring.
3. The kp emblem.
4. The right column.
5. The hologram.
6. Tests.
7. Seed and manifest.
8. Frames.

---

## 1. DELETE (both appearances)

### Words
| meaning | word |
|---|---|
| the place where deleted things wait | **DELETE**: always capitals, a name, no article ("in DELETE") |
| sending something there | **Delete** (menu row); "deleted" in sentences |
| bringing it back | restore (unchanged) |
| removing words, or erasing records for good | **Erase** |
| giving up a working copy | Discard (unchanged; it sends the copy to DELETE) |

**Internal names stay:**
- `files.trash`, `files.trash_list`, `files.restore`;
- the act `hand.trash` and the reply field `trashed`;
- the row key `'trash'` and the key `edit:delete`;
- the `.trash` folder and the `files_trash` table;
- `/files.trash {…}` on cards;
- `{'op':'DELETE'}` in the Changes room (a Kernel operation shown as code).

### The can: `workbench/trash_can_qt.py`
- Add `WORD = 'DELETE'`. It is used at :64 (the ink that is measured) and :120 (the word that is drawn).
- `setAccessibleName('DELETE')`.
- Tooltip: `'DELETE · what you delete waits here, and restore puts it back where it was · drop files here to delete them'`.
- The word's font: FACE at `round(16·s)` px, `setLetterSpacing(QFont.AbsoluteSpacing, 1.0·s)` in Kasandra and `0.8·s` in Graphite.
  - Colour: RED with its glow in Kasandra; TEXT in Graphite (unchanged).
  - The count stays at FACE 13 px.
- Box: 120×29 at s = 1 in Kasandra. Window position (218, 1094) at 1920×1200 and (218, 662) at 1366×768. P stays 354.
- Docstrings at :1-6 and :45-48, and pane_qt.py:2-21, now say DELETE.

### Exact strings, old → new
| file:line | new |
|---|---|
| context_menu.py:498 | `'Deleted. Restore it from DELETE.'` |
| context_menu.py:499 | `'Deleted %s · DELETE puts %s back.'` |
| context_menu.py:673 | label `'Delete'`, section `'danger'`, tip `'DELETE keeps it; restore puts it back'` |
| context_menu.py:703 | label `'Delete'` |
| context_menu.py:740 | tip `'Files keeps its own changes: rename, versions, export, DELETE'` |
| context_menu.py:2924 | FOLDED `('Files: a selection', 'Delete', 'file', 'trash')` |
| context_menu.py:429 | `Entry('edit:delete', 'Erase', 'edit', …, reason='Select words first.')`. FOLDED :2948 keeps Qt's old word `'Delete'` (kind 'passage', a different home key, so test_context_menu.py:265-269 still holds). |
| files_qt.py:107 [seed] | `"… every change keeps the version before it, and deletions go to DELETE."` |
| files_qt.py:109 [seed] | `'… Deleting moves it to DELETE, '` |
| files_qt.py:334 [seed] | `'Move this working copy to DELETE? %s is not touched, and the record of the work is kept.'` (title `'Discard draft'` unchanged) |
| files_qt.py:335 [seed] | `'The draft is in DELETE. The original is unchanged.'` |
| files_qt.py:367 [seed] | `'Deleted. Restore it from DELETE.'` |
| files_qt.py:478 [seed] | `'Delete'` (changes with :673, :703 and :2924, for test_context_menu.py:678-712) |
| files_qt.py:499, :505 [seed] | `'DELETE'` |
| files_qt.py:507 [seed] | `'Nothing is in DELETE.'` (second sentence unchanged) |
| shell2.py:1179 [seed] | `('DELETE', 'trash')`. `commands()` also matches a needle against `ALSO = {'trash': ('Trash',)}`, so typing "trash" offers DELETE. |
| shell2.py:2069 [seed] | `'Done: “%s” is in DELETE, which gives it back.'` |
| shell2.py:2118, :2192 [seed] | `'“%s” is in DELETE, which gives it back.'` |
| shell2.py:2143, :2145 [seed] | `'… so it is yours now and I leave it. Delete it yourself if you want it gone'` |
| shell2.py:2262 [seed] | `'… What this start made is in “%s” in Files; delete that folder if you do not want it (DELETE gives it back).'` |
| shell2.py:2269 [seed] | `'Delete the whole folder (DELETE gives it back) while it is still as I made it'` |
| shell2.py:2324, :2325 [seed] | `'…; Undo deletes it, and DELETE gives it back'` |
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
| tail_words.py:13 [seed] | `'files.trash': 'Deleted (in DELETE)'`, `'files.restore': 'Restored from DELETE'` |
| navigator_catalog.py:51 [seed] | `'footer': ['Settings', 'DELETE']` |
| memory_qt.py:24, :106 [seed] | `'Erase profile and feedback'`; reason `'Owner selected Erase profile and feedback'`; note `'Profile and feedback erased. Tasks and external archives remain separate.'` |
| office_building_qt.py:514 [seed] | `'Erase every recorded instruction and outcome? Lessons you reviewed stay.'` |
| docs/GRAPHITE_DESK.md (35), docs/DAILY_GUIDE.md [seed] (4), README.md [seed] (2) | the place → DELETE; "Move to Trash" → Delete; one sentence: "DELETE keeps what you delete; restore puts it back." |
| tools/check_desk_ui.py:253-257, tools/check_context_menu_ui.py:207, tools/desk_review.py | keep in step: draw 'DELETE' with its spacing; the words 'Delete' and 'DELETE' |

**Unchanged:**
- version.py history (:14, :53) and the old release notes;
- docstrings and comments;
- all the "Remove …" words;
- qt_app.py:5233 (legacy; a keys list, to be removed later).

---

## 2. Every face is the typewriter face (Kasandra)

### 2.1 Two derived faces: `tools/derive_typewriter.py` (new; build time only)
**Running it:**
- Interpreter: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python `-I`.
- Uses fontTools ≥ 4.40 and skia-pathops. Starting point: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/derive.py.
- Source: `branding/fonts/typewriter/SpecialElite-Regular.ttf` (SHA-256 a776fcb4ceb8bdf03e2967688ebdad42680de5b91a7e62c17e718ae212d14bc4; 2048 units per em).
- Byte-reproducible: keep `head.created` and `head.modified`, and save with `recalcTimestamp=False`.

**`branding/fonts/typewriter/KasandraElite-Regular.ttf`** (family "Kasandra Elite"; the words face)
- **Only these glyphs change:** `zero` to `nine`, and `l`.
  - **zero:** pathops union with a slash from (330,330) to (890,1150), half-width 62 units.
  - **l:** pathops difference with the rect (−200,−200)–(446,132), leaving a right foot only.
  - **The ten digits:** advance 1254; ink moved by (1254 − old advance)/2.
  - The changed glyphs get empty instruction programs.
- **Everything else stays byte-identical:** every other `glyf` entry and its `hmtx` row, `fpgm`, `prep`, `cvt `, `gasp`, `GSUB`, and vertical metrics hhea 1440/−608/0.
- **Kerning:** drop every `kern` pair, and every GPOS PairPos Format 1 pair, whose two glyphs are both digits.
- **name:** IDs 1, 4, 6, 16 and 17 become Kasandra Elite / KasandraElite-Regular.
  - ID 3: `Kasandra Elite 1.000 (derived from Special Elite)`.
  - ID 10: `Derived from Special Elite (Apache 2.0) for Graphite: slashed zero, l on a right foot, tabular figures.`
  - IDs 0, 13 and 14 are kept.

**`branding/fonts/typewriter/KasandraEliteMono-Regular.ttf`** (family "Kasandra Elite Mono"; the face for lines, numbers, addresses, Terminal and tags)
- **Outlines:** taken from Kasandra Elite's, so the zero and the `l` carry the same fixes.
- **Cell:** every advance is 1229 units (0.6 em).
  - Ink is centred in the cell.
  - Ink wider than 1189 units is narrowed about its own centre to 1189.
  - Glyphs with zero advance stay at 0.
- **Tables:** drop `kern`, `GPOS`, `GSUB`, `fpgm`, `prep`, `cvt `, `hdmx`, `LTSH` and `VDMX`. `gasp` = {0xFFFF: 0x000A}.
- **Vertical metrics, equal to Plex Mono's:**
  - hhea ascent 2099, descent −563, lineGap 0;
  - OS/2 typo the same, with USE_TYPO_METRICS (fsSelection bit 7) set;
  - win 2099/563.
- **Fixed-pitch flags:** `post.isFixedPitch=1`, panose `bProportion=9`, `xAvgCharWidth=1229`, `hhea.advanceWidthMax=1229`.
- **name:** "Kasandra Elite Mono" / KasandraEliteMono-Regular. ID 10 adds `; fixed 0.6 em pitch on IBM Plex Mono's line, no kerning or ligatures.`

**Records to update:**
- `branding/fonts/typewriter/NOTICE.md`: one section per derived file, with what changed (Apache 2.0 §4(b)) and its `· SHA-256 <hex>` line. Add the line "Not the Special Elite font; its name is not used for the derived faces." Replace "Values, receipts, cells and controls stay in IBM Plex" with the mono face's role.
- `THIRD_PARTY_NOTICES.md:8`: name both derived files.
- **Nothing on screen or in a name says "Lain".**

### 2.2 Names and loading
- **`boss_theme.PALETTES` [seed]:**
  - add `MONO`: graphite `'IBM Plex Mono'`, kasandra `'Kasandra Elite Mono'`;
  - kasandra `FACE` and `DISPLAY` become `'Kasandra Elite'`;
  - Graphite is unchanged;
  - boss_theme.py:216, :230 and :235 become `"%(MONO)s"`;
  - add `face_css(family, px)` → `'font-family:"%s";font-size:%dpx;'`;
  - update the role comment at :55-60.
- **`shell2.py` [seed]:**
  - :26 becomes `SANS, MONO = bt.FACE, bt.MONO`; `mono_font()` (:265) uses MONO, then DejaVu Sans Mono.
  - `load_fonts` (:49-60) also loads both derived files. Special Elite stays loaded, so a face the owner chose stays available. Then it calls:
    - `QFont.insertSubstitutions('Kasandra Elite', ['IBM Plex Sans', 'DejaVu Sans'])`
    - `QFont.insertSubstitutions('Kasandra Elite Mono', ['IBM Plex Mono', 'DejaVu Sans Mono'])`
- **`reading_preferences.py` [seed]:**
  - new `in_force(names)` holds the three default swaps: the two at :108-109, plus code `'IBM Plex Mono'` → `bt.MONO`;
  - `apply()` uses it;
  - a face the owner chose herself is never swapped.
- **`control_qt.py:400-404` [seed]:** reports `family(in_force(...)[i], key == 'code_family')` as "effective".

### 2.3 Hard-coded families become theme names (each is a no-op in Graphite, where MONO is Plex Mono)
- **pane_qt.py:122-131:**
  - `tab_font` draws in FACE;
  - in Kasandra the chosen tab is Normal weight in TEXT, and `widest_bold` measures that same weight;
  - the row height at :634 is still measured from `QFont(bt.MONO)` at the menu size, so it stays 57.
- **shell2.py:3458 [seed]:** PaneTitle becomes FACE (weight 400 in Kasandra).
- **These become MONO:**
  - theme2.py:46, :124 [seed];
  - console_qt.py:172, :199-233, :399 [seed];
  - log_qt.py:291-294, :392-409;
  - compare_qt.py:27, :100;
  - finder_qt.py:216 [seed];
  - thumbnails.py:204;
  - universal_viewer_qt.py:185, :193;
  - code_rain.py:27-28 (it was DejaVu);
  - boss_qt.py:110, :186-193, :319-351 [seed];
  - idle_display_art.py:36-37;
  - chain_menu.py:87-95 [seed];
  - field_qt.py:200 (`mono()`).
- **Room-wide sheets become `%(MONO)s` / `bt.MONO`:** investigations_qt [seed], datasheet_qt [seed], sheet_workbench_qt [seed], work_trail_qt [seed], program_rooms_qt [seed].
- **These stay Plex (pictures and Graphite's brand):** glyph_set.py:384, :457; chain_icons.py:26, :83; thumbnails.py:58, :97; graphite_brand.py:220, :244; the legacy qt_app rooms.
- **pulse_qt.py:47, :116, :126 (Kasandra):** 11 px becomes 12 px. No Kasandra text is smaller than 12 px.

### 2.4 The face drawn is the face measured (both appearances)
New `shell2.set_face(widget, family, px, sheet='')`. It:
- sets `face_css(family, px) + sheet` as the widget's own sheet;
- also calls `setFont(QFont(family, pixelSize=px))`, so the metrics are right before polish.

**Where it is used:**
- shell2.py:1726 (code bubble, 16), :1944 (slab, 15), :1981 (13), :2031 (15), :2417 (14), :2702 (16), :2794 (16), :2896 (15), :3141 (16). Each px is × `scale_of(host)` where a host is at hand. Any `line_sheet()` or colour string goes in `sheet`.
- context_menu.py:2577 (LineSlab) and :2584 (LinePreview), with `MONO` at `max(12, m.caption_px)`.

In Graphite, her lines on cards then draw in Plex Mono, as they were always meant to (today they draw in Plex Sans). This is noted as a fix.

### 2.5 Sizes (14 pt; everything × s = ui_pt/14)
| role | face | size |
|---|---|---|
| menus, tabs, tree rows, buttons, lower band, her words | Kasandra Elite | the reading profile (unchanged) |
| the typing line, Terminal, code views, Field tags, the workspace path, meter readings | Kasandra Elite Mono | as now |
| a line on her card | Mono | 15 |
| model line | Mono | 13 |
| meter keys | Kasandra Elite | 12 |

The Field's −0.35 tracking (field_qt.py:210) stays.

---

## 3. The hologram in the lower left (Kasandra; Illustrated)

### 3.1 Asset and verification: `workbench/kasandra_art.py`
- **`MARKS = {name: sha256}`** for:
  - `hologram.webp` (b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec);
  - `kp_emblem_source.png` (94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa);
  - the six derived kp files in §5;
  - `kp_monogram.png` (7c5b3c9c1f16e0d1eca1f881a0ece60bda777355fdc0fa634495deb77170a073);
  - `wordmark.webp` (0a8d44e549b4c9904df11496fb81106c918680c4c84a268098067dc919deb1e6).
- **`mark(base, name)`** returns `usable(base, {'file': name, 'sha256': MARKS[name]})`: the same cached (mtime, size) check (:103-121) and the 16 MB limit. The catalog keeps its 8 scenes.
- **`cutout(path)`:**
  - `QImageReader` → `Format_ARGB32_Premultiplied`, never `source()`'s RGB32 (:181);
  - cached once;
  - `CROP = QRect(80, 15, 608, 822)`;
  - `GLITCH_ROWS`: the crop rows where pixels with 1 ≤ alpha < 8 lie left of x 86 or right of x 681. These are the glitch lines already baked into the picture, worked out once.
- **boss_qt.py:77-80 [seed]:** the wordmark loads through `mark()`.

### 3.2 `workbench/hologram.py` (new; pure, no Qt)
**Constants (× s, rounded):**
- `ASPECT = 608/822`;
- `GAP 16` (gap under the last row), `SIDE 8`, `NEAR 12` (gap to DELETE), `HMIN 120`, `HMAX 380`, `ROOM 16` (room for the base below her).

**`place(rows_end, foot_top, delete, P, I, s)`** returns `(stance, figure, stage)` or None. Everything is in left-PaneBody coordinates.
- None when `rows_end is None` (the tree scrolls).
- `top = rows_end + GAP`.
- **stage:** x in [I+SIDE, P−I−SIDE]; her base line = `delete.y − ROOM` (she stands above the foot).
- **corner:** x in [I+SIDE, delete.x − NEAR]; her base line = `delete.y + delete.h` (DELETE's floor).
- For each stance: `h = min(HMAX, base − top, int(W/ASPECT))`, then `h −= h % 4`.
- Take the taller stance; on a tie, stage.
- `h < HMIN` → None.
- `w = round(h·ASPECT)`; `x = left + (W − w)//2`; `y = base − h`.
- `stage = (x − SIDE, y, w + 2·SIDE, h + ROOM)`.
- The stage never meets DELETE and never goes past the pane's bottom.

**`rows_bottom(visible_rows, row_h, content_top)`, worked out arithmetically.** The tree scrolls when `visible_rows·row_h > viewport_h`. No layout pass is needed, so she moves aside within the same signal.

**Results** (P 354, I 16, s 1; DELETE (218, foot_top+8, 120, 29); pane → window: x is the same, y + 61):

| case | rows_end | foot_top | result (stance, figure x,y,w,h, stage) |
|---|---|---|---|
| 1920 Files, 13 rows (as the workspace opens) | 429 | 1025 | stage (36,637,281,380), stage (28,637,297,396) |
| 1920 Machine, 9 rows | 317 | 1025 | stage (36,637,281,380) |
| 1920 Files, all 27 rows open | 821 | 1025 | corner (32,838,166,224), stage (24,838,182,240) |
| 1366 Files, 13 rows | 429 | 593 | corner (47,446,136,184), stage (39,446,152,200) |
| 1366 Files, top level (11 rows) | 373 | 593 | corner (26,390,178,240) |
| 1366 Files, 15 rows | 485 | 593 | corner (67,502,95,128) |
| 1366 Files, 16 rows | 513 | 593 | None |
| 1366 Machine, 9 rows | 317 | 593 | stage (84,333,186,252), stage (76,333,202,268) |
| Settings, or any tree that scrolls | None | — | None |

**`STATE_LOOK`** (shared by the stage and the masthead; 'viewing' counts as idle):

| state | word | colour |
|---|---|---|
| idle | quiet | VIOLET #ab8eda |
| working | at work | READY #83eaff |
| awaiting_approval | waits for you | OWNER #fa507c |
| completed | done | HONEY #e9b872 |
| blocked | stopped | RED #ff3b5c |

**`MOTION`** (frame rate 12 fps, 83 ms, `Qt.CoarseTimer`; all motion is a function of `time.monotonic()`):

| | idle | working | awaiting_approval | completed (20 s hold) | blocked (45 s hold) |
|---|---|---|---|---|---|
| figure opacity | 0.80 | 0.84 | 0.86 | 0.82 | 0.62, colour drained 50% (grey layer at 0.5) |
| static (noise opacity) | 0.30 | 0.39 | 0.19 | 0.28 | 0.28 |
| scan-line drift, downward | 6 px/s | 14 | 4 | 6 | 3 |
| flicker | ×(1 + 0.03·sin 2π·0.7t + 0.02·sin(2π·1.9t+1.3)·sin 2π·0.23t) | same | none | same | none |
| tears | Poisson, mean 11 s, ≥ 4 s apart | mean 8 s, ≥ 4 s apart | none | none | one at the moment it starts |
| base breath | period 2.8 s ±15% | 1.4 s ±20% | 2.8 s ±25% | 2.8 s ±10%; colour HONEY → VIOLET over the hold | none |
| extra | — | a write band 20·s px, #b9f4ff at 18% peak, rising bottom to top every 2.4 s, SourceAtop | — | one lock sweep top to bottom, 600 ms, 25% | — |

`period 2.8` is `pane_qt.BREATH`. Make it a named constant and use it in `pane_qt.breath`, so she and the tree breathe together.

**`frame_plan(state, t, rng, still, since_state, since_show)`** returns `{opacity, flicker, noise_index, noise_offset, scan_offset, tear|None, base_rgb, base_alpha, sweep_y|None, power|None}`.

When `still`, it always returns `flicker 1.0`, `noise_index 0`, `noise_offset (0,0)`, `scan_offset 0`, `tear None`, `sweep None`, `power None`, and the base at its state colour without breath.

### 3.3 `workbench/hologram_qt.py` (new): `HologramStage(QWidget)`
**What it is:**
- A child of the left PaneBody, raised over the content and the foot.
- `WA_TransparentForMouseEvents`, `NoFocus`.
- `WA_OpaquePaintEvent`: it fills GROUND #171b3c itself. The ground under her is flat (measured (23,27,60) in both probe frames). Frame F01 checks it.
- Accessible name: `named('Stacy') + ', projected · ' + word`.
- `pane_qt.install` sets `host.hologram` in Kasandra only, and only when `mark(…, 'hologram.webp')` verifies. Otherwise `host.hologram = None` and the left column is as in 0.8.2.

**When it is placed again** (synchronously, so it never covers a row for even one frame):
- the current tree's `itemExpanded` and `itemCollapsed`;
- its model's `rowsInserted`, `rowsRemoved`, `modelReset` and `layoutChanged`;
- `verticalScrollBar().rangeChanged`;
- `nav.stack.currentChanged`;
- the end of `PaneBody.arrange` and of `pane_qt.place`;
- `boss_qt.choose_art` (add it to the loop at boss_qt.py:481-483) and `set_glow`;
- a change of reading profile.

It calls `raise_()` after placing.

**Layers:**
- **Per (w, h, dpr), keeping the last 2 sizes:**
  - `figure`: CROP scaled smooth, with a DestinationIn fade over its lowest 14%;
  - `cyan` (#83eaff) and `pink` (#f23e6b) silhouettes;
  - `grey`: a desaturated twin;
  - `frame`: one reused ARGB32 buffer.
- **Built once and shared:**
  - six 64×64 noise tiles. 1 pixel in 9 lit, alpha uniform 0–1, half #ffffff and half #0a081e. Built with `random.Random(seed).randbytes` + `bytes.translate` into Alpha8 images; no per-pixel Python painting;
  - a 1×3 scan tile (one pixel at alpha 70).
- **Memory:** about 12 MB at most, including the decoded source.

**Each frame:**
1. `frame` = figure;
2. blocked only: grey at 0.5;
3. a noise tile brush at a random offset, at the static opacity, with SourceAtop (static lands on her only);
4. the scan tile brush with DestinationOut, offset `int(drift·t) % 3`;
5. the sweep or lock, with SourceAtop;
6. a tear, if one is due:
   - a band 2–5·s px tall;
   - its y is one of GLITCH_ROWS 60% of the time, otherwise anywhere in her top 80%;
   - shifted ±3–7·s px for 2 frames;
   - cyan at −1 px and pink at +1 px, at 22%, inside the band only.

**Then the stage paints:**
1. GROUND;
2. the beam: a trapezoid from 0.32w at her base to 0.92w at 45% of her height, alpha 0.10×breath, fading to 0 upward;
3. the base: a radial ellipse at (cx, base − 3), radii 0.36w × 0.058w, alpha 0.42×breath;
4. its rim (from B): an ellipse outline 1.5·s px wide, alpha 0.55×breath;
5. `cyan` at +1 px, at 0.08 × opacity (the projector's fringe);
6. `frame` at opacity × flicker.

When the state changes, the base colour cross-fades over 400 ms (instantly when still).

**Moments (from B):**
- **Power-up, 360 ms.** On the first show after start, after leaving Clean, or after she was hidden at least 10 s. The timer runs at 40 ms for those 360 ms only.
  - 0–120 ms: the base rim lights from 0 to 1.
  - 120–360 ms: she is revealed from the bottom up behind a 2 px READY scan edge, with the static at ×3 falling linearly to ×1.
  - A tab switch within 10 s is a plain cut, with no power-up.
- **Touch.** When the pointer enters her figure rect: one tear of 5·s px for 2 frames, and brightness +6%.
  - A cooldown of 1.5 s.
  - Not in awaiting_approval or blocked, and never when still.
  - Read through an event filter for MouseMove on the current tree's viewport and the left PaneFoot. Clicks still go to the tree and to DELETE.

**Still:**
- `still = pane_qt.still(view) or menu_catch.calm(stage)`. This covers Reduce motion, and the Clean glow (`glow() ≤ 0`).
- No animation timer. One frame from `frame_plan(still=True)`.
- A change of state repaints once (colour is not motion).

**State:**
- A 1 s QTimer reads `kasandra_art.current_state(host)` while she is placed, even when still.
- `kasandra_art.watch(host, stage)` nudges her as well.
- The state is read at most once every 250 ms.

**The animation timer runs only while all of these hold:**
- the appearance is Kasandra, the desk is Illustrated, and she is placed and `isVisible()`;
- the window is not minimised;
- `QGuiApplication.applicationState() == Qt.ApplicationActive`;
- `not host.idle_display.showing()` (idle_display_qt.py:75);
- not still.

`applicationStateChanged` and the window's `changeEvent` (WindowStateChange and ActivationChange) call `stage.wake_or_sleep()`. While asleep she keeps her last frame.

**Where she stands aside:**
- the tree scrolls, or there is no room → hidden at once, with no fade;
- Settings → hidden;
- Clean desk → hidden, timer stopped, layers dropped;
- Graphite, or a mark that fails → no stage at all.

**ASCII desk:** a still figure made of characters.
- Kasandra Elite Mono at 9·s px, cells from its metrics.
- Ramp `" .:-=+*#%@"` by luminance × alpha, in VIOLET_PALE at 0.8.
- The base line in the state colour. No motion.

**BranchTree._breathe (pane_qt.py:499)** repaints only the rows' extent: `viewport().update(QRect(0, 0, w, rows_end))`. The tree's 140 ms breath then never repaints her.

**Budget:**
- a frame at 281×380, dpr 1: ≤ 1.5 ms (measured 0.61 ms here);
- 30 s with the window open and idle: Illustrated minus Clean ≤ 2% of one core.

---

## 4. The right column without the picture (Kasandra; Graphite unchanged except §2.4)

### SlateFace (shell2.py:1784-1823 [seed])
In Kasandra the picture row is not built: `self.portrait = None`, no `PanelInk('face')`, and :1795 is guarded. `signature` stays hidden. In its place goes a **masthead**:
- **Height:** the left tab rule's window y − the right content's window y + 1, which is **47** at 14 pt. It grows rather than clip if the owner's sizes are larger.
- **Its bottom row:** a 1 px LINE #3b4479 rule across the column. It lies on the left tab row's rule (window y **117** at both sizes). At its left, a 32·s × 2·s TEAL tick that glows only when `glows(host)`.
- **Row 1:**
  - `named('Stacy')` ("Kasandra") in FACE at the size of her words, VIOLET_PALE, weight 400;
  - 4·s px gap;
  - a cursor block 0.45 em × 0.78 em on the baseline, in the STATE_LOOK colour. It is steady. In awaiting_approval its alpha breathes 0.6–1.0 over 2.8 s, in phase with the hologram's base; it is steady when still;
  - right-aligned: the state word in FACE 14·s px, QUIET;
  - accessible name `named('Stacy is ') + word`.
- **Row 2:**
  - the model line in MONO 13·s px, FAINT, shortened in the middle to the room the hand link leaves, with the full name in its tooltip;
  - ` · `;
  - the hand link (`self.hand`) in FACE 14·s px.
- **Ground:**
  - `QWidget#SlateFace {background:#11132c}` (TERMINAL_GROUND) with `WA_StyledBackground`;
  - the scroll area, its viewport and the thread are transparent;
  - on Clean the ground stays and the glows go.
- **The right PaneBody's inner edge line** (pane_qt.py:241-246) is TEAL_EDGE #5a8fc4 at alpha 0.5 in Kasandra, with a still 6 px glow when `glows(host)`.
- **Below the masthead:** 10 px of space, then the This: and Now: lines exactly as they are, then the thread.

### The thread
- `self.lines.setContentsMargins(0, 0, 4, 0)` (it was 14). `fold_earlier` (:1888) uses `self.lines.contentsMargins().right()`.
- **Bubble** (:1720-1729):
  - margins (10, 9, 8, 9) in Kasandra;
  - her text goes through a new `leaded(label, text)`: escape the HTML, keep `breakable()`, turn `\n` into `<br>`, wrap in `<p style="line-height:125%;margin:0">…</p>`, `Qt.RichText`, and set `label.setProperty('plain', text)`;
  - `set_text` does the same;
  - her card text is **297 px** wide at P 354 (it was about 280).
- `desk_doers.read_desk` (:633-634), tools/check_document_ui.py:87, check_files_about_ui.py:72, check_agent_ui.py:74 and check_continue_ui.py:82 read `label.property('plain') or label.text()`.
- **Your bubbles:** right-aligned, hugging their words up to 85% of the thread's width. The width is set again on resize, with a stretch on the left. VIOLET_SOFT with a 1 px VIOLET_DEEP edge, radius 8.
- **Line slab:** `set_face(code, MONO, round(15·s), bt.line_sheet())`. A new `breakable_line()` puts U+200B after `,` `|` `/` `:` `=` `{`; `breakable()`'s 18-character chunks remain only as a fallback. The tooltip and Copy keep the exact line.
- Space between items: 12 (it was 10).

**Gain (measured layout + 37 px):**
- the conversation box is 322×**869** at 1920 (it was 832) and 322×**437** at 1366 (it was 400);
- her text is 17 px wider.

---

## 5. The kp emblem

### `tools/cut_kp_emblem.py` (new; build time; `python3 -I`, numpy + Pillow)
Starting point: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_design/kp_cut.py.

1. **Ground** G = #070221. **Inks:** cream (254,241,227), pink (242,62,107), pink (253,54,108), violet (118,53,254).
2. **Unmixing:**
   - for each ink, αᵢ = clamp(((C−G)·(Fᵢ−G)) / |Fᵢ−G|², 0, 1);
   - the ink with the least residual wins;
   - the stored colour is that ink itself at αᵢ;
   - a residual over 40 → the pixel is kept opaque as it is;
   - α < 0.04 → 0; α > 0.97 → 1.
3. **Trim** to the ink bounds x 259–980, y 417–883, plus 8 px → **737×482** (source rect (251, 409, 737, 482)).
4. **The small cut:** pink and violet alpha dilated with a 9×9 max filter, keeping the ink colour; then cream pixels, and the opaque mixed pixels, pasted back exactly.
5. **Resizing** uses Lanczos in premultiplied form.

### Assets (branding/kasandra/)
| file | size | made from | use |
|---|---|---|---|
| `kp_emblem_source.png` | 1254×1254 RGB | the owner's file | source for any later cut |
| `kp_emblem.png` | 737×482 RGBA | the cut | master |
| `kp_emblem_small.png` | 737×482 RGBA | the small cut | the 1× icon |
| `kp_emblem_38.png` | 58×38 | the small cut | Apps button, 1× |
| `kp_emblem_76.png` | 116×76 | the master | Apps button, 2× |
| `kp_tile.png` | 256×256 | the master on #070221, rounded square radius 56, emblem at 84% width, centred | window icon 32–256 |
| `kp_tile_letters.png` | 64×64 | the same tile with the cream "kp" only | window icon 16 and 24 |
| `kp_monogram.png` | 256×256 | kept unchanged | fallback; its SHA is now recorded |

### Apps button (shell2.py:586-597 [seed])
- A `QIcon` from `mark('kp_emblem_38.png')` and `mark('kp_emblem_76.png')`.
- `setIconSize(QSize(round(58·s), round(38·s)))`; the button is 76×60 with its right edge where it is now.
- `paperIcon`, `accessibleName 'Apps'`, the tip and `text ''` are unchanged.
- **Fallbacks:** if the emblem fails, the verified monogram at 36×36; if that fails too, the text `'[#] Apps ▾'`.

### Window icon (graphite_brand.py:92-96 [seed])
- In Kasandra, when both tiles verify: 16 and 24 from `kp_tile_letters.png`, and 32, 48, 64, 128 and 256 from `kp_tile.png`, each scaled smooth.
- Otherwise Graphite's tile.
- Add `window_icon_source()` → `'kasandra' | 'graphite'`.
- The splash and the installed launcher stay Graphite's.

### Records
- `branding/kasandra/README.md`: one line per file above, plus `hologram.webp` (800×875, the owner's hologram, 14 November 2026), each with its SHA-256; the monogram line gets 7c5b3c9c…a073.
- The same SHAs go in `kasandra_art.MARKS`, and in MANIFEST.json through `--manifest-only`.
- All of this is owner art, kept back by RIGHTS.md.

---

## 6. Files

### New
- `workbench/hologram.py`
- `workbench/hologram_qt.py`
- `tools/derive_typewriter.py`
- `tools/cut_kp_emblem.py`
- `branding/fonts/typewriter/KasandraElite-Regular.ttf`, `KasandraEliteMono-Regular.ttf`
- `branding/kasandra/`: `hologram.webp`, `kp_emblem_source.png`, `kp_emblem.png`, `kp_emblem_small.png`, `kp_emblem_38.png`, `kp_emblem_76.png`, `kp_tile.png`, `kp_tile_letters.png`
- tests: `tests_integrated/test_delete_words.py`, `test_typewriter_faces.py`, `test_hologram.py`, `test_kasandra_column.py`
- the helper `tests_integrated/kasandra_window_probe.py`. It is not a test module. It runs in a subprocess with `GRAPHITE_APPEARANCE`, offscreen with a screen configuration file at the size asked, a temporary workspace and profile, and the holds of test_context_menu.py:44-79. It prints JSON.

### Changed (**[seed]** = a SEED_FILES input)
- **Seed inputs:** boss_theme [seed], boss_qt [seed], shell2 [seed], reading_preferences [seed], control_qt [seed], theme2 [seed], console_qt [seed], finder_qt [seed], chain_menu [seed], investigations_qt [seed], datasheet_qt [seed], sheet_workbench_qt [seed], work_trail_qt [seed], program_rooms_qt [seed], graphite_brand [seed], files_qt [seed], tail_words [seed], navigator_catalog [seed], memory_qt [seed], office_building_qt [seed].
- **Other workbench modules:** trash_can_qt, context_menu, desk_doers, desk_acts, stacy_hand, stacy_start, working_copies, working_folders, files_service, pane_qt, kasandra_art, log_qt, compare_qt, thumbnails, universal_viewer_qt, code_rain, idle_display_art, field_qt, pulse_qt.
- **Documents and records:** docs/GRAPHITE_DESK.md, docs/DAILY_GUIDE.md [seed], README.md [seed], RECORD_OF_DIRECTIONS.md [seed] (the owner's six directions of 14 November), THIRD_PARTY_NOTICES.md, branding/fonts/typewriter/NOTICE.md, branding/kasandra/README.md.
- **Tests and tools:** tools/check_hatch.py (FOCUSED_MODULES), tools/check_desk_ui.py, check_document_ui.py, check_files_about_ui.py, check_agent_ui.py, check_continue_ui.py, check_context_menu_ui.py, desk_review.py.
- **Last:** `python3 tools/package_graphite.py --manifest-only`, then commit `project/stacy_seed/current/*` and `MANIFEST.json`.

---

## 7. Tests (exact assertions)

### Existing tests that change
| test | change |
|---|---|
| test_kasandra.py:54 | `assertEqual(k['DISPLAY'], 'Kasandra Elite')`, plus `k['FACE'] == 'Kasandra Elite'` and `k['MONO'] == 'Kasandra Elite Mono'` |
| test_kasandra.py:45 | add `g['MONO'] == 'IBM Plex Mono'` and `g['FACE'] == 'IBM Plex Sans'` |
| test_desk_acts.py:186 | `(False, 'DELETE, once emptied, cannot be brought back')` |
| test_desk_acts.py:193 | `'Move to Trash'` → `'Delete'` |
| test_graphite.py:292 | the KEPT string ends `"… and deletions go to DELETE."` |

**Unchanged:**
- test_kasandra.py:90-94 and :134-140 (8 and 5 scenes);
- test_kasandra.py:115-121 (the monogram stays);
- test_context_menu.py:678-712 and :265-269 (they pass with the matched words);
- test_desk.py:163-175.

### `test_delete_words.py`
**`test_the_can_says_DELETE`** (in-process Graphite, plus a Kasandra subprocess):
- `TrashCan.WORD == 'DELETE'`;
- `accessibleName() == 'DELETE'`;
- `toolTip() == 'DELETE · what you delete waits here, and restore puts it back where it was · drop files here to delete them'`;
- `word_font.letterSpacing() == 1.0` in Kasandra and `0.8` in Graphite, with type AbsoluteSpacing;
- `width() == trash_size(1.0, ceil(ink width of 'DELETE'), ceil(ink right of '999'), can_ink(30), count_gap)[0]`;
- in Kasandra, `width() == 120` and `height() == 29`.

**`test_no_Trash_is_shown`:**
- AST scan of `workbench/*.py`: no non-docstring string constant matches `\bTrash\b`, except in version.py;
- none matches `\bthe DELETE\b`.

**`test_Delete_and_Erase_never_meet`** (AST of context_menu.py `Entry(...)` calls with literal arguments):
- a label `'Delete'` ⇒ key `'trash'`;
- key `'edit:delete'` ⇒ label `'Erase'`;
- FOLDED rows with the word `'Delete'` have (kind, key) in {('file','trash'), ('passage','edit:delete')};
- memory_qt contains `'Erase profile and feedback'` and not `'Delete profile'`;
- office_building_qt contains `'Erase every recorded instruction and outcome?'`.

**`test_DELETE_is_a_search_place`:**
- `[l for l, _, _ in OneBox.commands(SimpleNamespace(host=SimpleNamespace(actions=lambda: [])), 'trash')] == ['DELETE']`;
- `'DELETE' in` the labels of `commands(…, 'dele')`.

**`test_the_words_say_DELETE`:**
- `tail_words.WORDS['files.trash'] == 'Deleted (in DELETE)'`;
- `tail_words.WORDS['files.restore'] == 'Restored from DELETE'`;
- `stacy_hand` refusal text as above.

### `test_typewriter_faces.py` (Qt; fonts added with `addApplicationFont`; `shell2.load_fonts(ROOT)`)
**Files and families:**
- The SHA-256 of both TTFs equals NOTICE.md's `· SHA-256` lines.
- The families are `['Kasandra Elite']` and `['Kasandra Elite Mono']`.

**The mono face:**
- `QFontDatabase.isFixedPitch('Kasandra Elite Mono')`.
- `reading_preferences.family('Kasandra Elite Mono', True) == 'Kasandra Elite Mono'`.
- For px in (12, 13, 14, 16, 18):
  - every character of `string.ascii_letters + string.digits + string.punctuation + ' '` has an advance in Mono equal to `QFontMetricsF(Plex Mono px).horizontalAdvance('M')` within 0.01;
  - `ascent()` and `descent()` equal Plex Mono's within 0.05.
- At 16 px, `horizontalAdvance('←')` and `('─')` equal Plex Mono's 'M' within 0.05 (substitution).

**The words face:**
- At 16 px, every one of the 100 two-digit strings has advance = 2 × advance('0') within 0.01.
- Every character of `ascii_letters + punctuation + ' '`, and each of 'DELETE', 'Kasandra', 'Terminal', 'Search', 'Web', 'Log', 'Files', 'Machine', 'Settings', has the same advance as in Special Elite within 0.01.
- `height() == 16.0`.

**Glyphs that must differ** (drawn at 64 px into Grayscale8, baseline at (8, 72); "ink" = value ≥ 128; the builder confirms the thresholds on the built files):
- In both faces, `l` has 0 ink pixels in [ink_left, ink_left + 0.3·advance) × [67, 72).
- `1` has ≥ 6 ink pixels in the same box.
- `0` has ≥ 8 in the 6×6 box at its ink centre; `O` has 0 there.

**Wiring:**
- Subprocess in Kasandra: `bt.MONO == shell2.MONO == 'Kasandra Elite Mono'` and `bt.FACE == bt.DISPLAY == 'Kasandra Elite'`.
- `reading_preferences.in_force(('IBM Plex Sans','IBM Plex Sans','IBM Plex Mono')) == ('Kasandra Elite','Kasandra Elite','Kasandra Elite Mono')`.
- `('DejaVu Sans','DejaVu Serif','DejaVu Sans Mono')` comes back unchanged.
- In Graphite: MONO is 'IBM Plex Mono', FACE 'IBM Plex Sans', DISPLAY 'IBM Plex Mono'.
- AST scan of the §2.3 modules: the literal `'IBM Plex Mono'` appears only as boss_theme's graphite values.

### `test_hologram.py`
**Pure part:**
- Every row of the §3.2 results table, exactly, through `place(...)` with DELETE (218, foot_top+8, 120, 29), P 354, I 16, s 1.
- Grid: s ∈ {1, 18/14, 20/14}, H ∈ {646, 800, 1078}, rows_end from 100 to 993 in steps of 7. For each result:
  - `y ≥ rows_end + GAP`;
  - the stage lies inside [I, P−I];
  - the stage does not meet DELETE;
  - the stage's bottom ≤ H;
  - `h % 4 == 0`;
  - `|w − h·ASPECT| < 1`;
  - `h ≥ HMIN`.
- `MOTION['awaiting_approval']['tears'] is None`, and the same for completed.
- The flicker amplitudes sum to at most 0.05.
- `MOTION['idle']['period'] == pane_qt.BREATH == 2.8`.
- For every state and t in 0, 0.5, … 10 with `still=True`: flicker 1.0, noise_index 0, scan_offset 0, tear None, sweep None, power None.
- With `Random(7)` over 600 s:
  - idle tear intervals are all ≥ 4 s, with a mean between 9 and 13 s;
  - no tears in awaiting_approval or completed;
  - blocked has exactly one tear within 0.2 s of its start.

**Qt part (probe subprocess, Kasandra, 1920×1200):**
- `mark(PACK, 'hologram.webp')` is a path. In a temporary copy of the pack with one byte changed, it is None.
- With `mark` patched to return None, `host.hologram is None`.
- `cutout(p).hasAlphaChannel()`, `pixelColor(2,2).alpha() == 0`, `cutout(p) is cutout(p)`.
- With `reduce_motion` True: `_timer.isActive()` is False after placing, and two `grab()`s 300 ms apart are byte-identical.
- With `desk_art 'clean'`: `isHidden()`, `layers is None`, and the timer is inactive.
- Illustrated, shown and active: `_timer.interval() == 83`.
- `wake_or_sleep()` with the application inactive stops the timer.
- On the Settings tab: hidden.
- Expand rows until the tree scrolls, then check `isHidden()` immediately, with no `processEvents`.
- Her stage rect never meets any visible row's rect, or DELETE's.
- **Motion** (24 frames composed at 1/12 s steps, tears off), as the mean per-pixel |ΔL| between consecutive frames over the stage:
  - idle between 2.5 and 8.0 /255;
  - working between 4.0 and 10.0, and above idle;
  - awaiting_approval between 1.0 and idle's value;
  - still: 0;
  - the stage's mean luminance changes by at most 2% between frames.
- Mean compose + paint over 50 frames at 281×380 is under 3.0 ms.

### `test_kasandra_column.py` (probe subprocess at 1366×768 and 1920×1200; one Graphite run)
**The column's top:**
- `face.portrait is None`, and no `PanelInk` of kind `'face'` under the face.
- The masthead rule's window y equals the left tab rule's (`left.tabs.mapTo(window, QPoint(0, left.tabs.height()-1)).y()`), at both sizes.
- `masthead.name.text() == 'Kasandra'`, family `'Kasandra Elite'`.
- The model label's family is `'Kasandra Elite Mono'`. A 60-character model name shows `'…'` in the middle, with the full name as its tooltip.
- For each of the five forced states (`host._art_outcome`, a waiting Approve button, `face.job`):
  - `masthead.word.text() == STATE_LOOK[state][0]`;
  - the cursor colour is that role's colour;
  - it equals `host.hologram.base_colour().name()`.

**The thread:**
- `face.lines.contentsMargins().right() == 4`.
- Her bubble's `text.width() == 297` at P 354.
- A 4-line card's `heightForWidth(297)` is ≥ 1.2 × a plain QLabel's in the same font.
- `bubble.text.property('plain')` equals the text given.
- `read_desk(host, 'talk')['talk']['last']` contains no `'<p'`.
- The slab of an answer in a line, after `ensurePolished()`: `font().family() == 'Kasandra Elite Mono'` and `pixelSize() == 15`. In the Graphite run: `'IBM Plex Mono'`. This is the regression test for the face bug.
- A pixel in empty thread space equals #11132c within 2 per channel.
- P stays 354 at both sizes.

**The emblem:**
- Every `MARKS` file's SHA matches, and README.md lists each SHA.
- `kp_emblem.png` is 737×482 with alpha, `pixel(2,2).alpha() == 0`, `|w/h − 1.529| < 0.02`.
- Composited over #070221, it matches source rect (251, 409, 737, 482) with mean error ≤ 2.5/255 and p99 ≤ 16.
- Pixels with 0.1 < α < 0.9 lie within 12 of one of the four inks.
- `kp_emblem_38.png` is 58×38, `_76` is 116×76.
- `kp_tile.png` is 256×256 with corner alpha 0 and centre alpha 255; `kp_tile_letters.png` is 64×64.
- `programs.iconSize() == QSize(58, 38)`, `accessibleName() == 'Apps'`, `text() == ''`.
- With the emblem's mark patched to None → `QSize(36, 36)`. With both None → `text() == '[#] Apps ▾'`.
- `window_icon_source()` is `'kasandra'` here and `'graphite'` in the Graphite run.
- **Graphite run:** `face.portrait` is a PanelInk, `face.masthead` is None, and the right margin is 14.

### `tools/check_hatch.py`
FOCUSED_MODULES gets, after the 0.8.2 line:

```
# 0.8.3: DELETE, the typewriter faces, her hologram, her column and the kp emblem
'test_delete_words','test_typewriter_faces','test_hologram','test_kasandra_column',
```

Finish with the whole focused list. Report pass or fail against the baseline taken at the start.

---

## 8. Frames as proof
**How to take them:**
- Probe: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_build/look_083.py, based on /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/code/probe.py.
- A disposable copy of /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/demo/After_Hours_07.
- Kasandra, Illustrated, 14 pt.
- Output in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_build/frames/, with a `frames.json` of the measured rects.

| file | what it must show (window coordinates) |
|---|---|
| F01_left_files_1920.png | stage stance; figure (36,698,281,380); DELETE (218,1094,120,29); pixels in the stage rect away from her = GROUND within 2 |
| F02_left_files_1366.png | corner stance; figure (47,507,136,184); DELETE (218,662,120,29) |
| F03_left_machine_1366.png | stage stance (84,394,186,252) |
| F04_left_settings_1920.png, F04_left_settings_1366.png | no hologram |
| F05_left_files_open_1920.png, F05_left_files_open_1366.png | all 27 rows: corner (32,899,166,224) at 1920; none at 1366 |
| F06_clean_1920.png | no hologram, nor any base or beam |
| F07_still_a.png, F07_still_b.png | Reduce motion; 1 s apart; byte-identical in the stage rect |
| F08_idle_strip_24.png + F08_motion.txt | 24 frames at 12 fps; the ΔL numbers |
| F09_states_5.png | idle, working, awaiting_approval, completed and blocked side by side; base and masthead cursor in the same colour |
| F10_powerup_9.png | the power-up at 40 ms steps |
| F11_right_1920.png, F11_right_1366.png | Home, then after two Traces: masthead rule at y 117; conversation 322×869 and 322×437 (±2); the slab in Mono, broken at commas; the #11132c ground; the teal edge |
| F12_head_apps_x3.png | the kp emblem 58×38 in the 60 px band |
| F13_terminal.png | `ls -l` columns aligned in Kasandra Elite Mono beside a Plex Mono reference; `printf '┌─┐\n└─┘'` connects |
| F14_glyphs.png | `Il1| 0Oo 07 10 l0O1` at 12, 14, 16 and 18 px in both faces |
| F15_graphite_1366.png | DELETE in Plex Sans spaced 0.8; no hologram; right column as in 0.8.2 |
| F16_cpu.txt | 30 s idle, process CPU, Illustrated minus Clean ≤ 2.0% of one core |
| F17_window_icon.png | the Kasandra tile at 16, 24, 32, 48, 64, 128 and 256 |

---

## 9. Not in this pass
- Animation on the ASCII desk (she is a still there); B's motes, flicker drops, frame-rate governor and changing frame rates; the "flinch" when something is deleted; B's chroma split for blocked.
- Folded older cards as one-line heads; B's raster lines in her column; the This: and Now: lines at a smaller size; a large 24 px name tag.
- Number spans in her prose (B's `cells_spans`); any change to the Field's −0.35 tracking.
- portrait.webp; the reference patch; the Graphite appearance beyond the DELETE and Erase words, the card-line face fix (§2.4) and the Settings report of fonts.
- The legacy qt_app rooms, and their keys list at :5233 (noted for removal).
- Renaming operations, folders or tables (`files.trash`, `.trash`, `files_trash`).
- The installed launcher icon and the splash.
- The version line, release notes and kit: a release step of its own.
- Kasandra's hand planner over the acts' conditions (the maths): it continues as its own pass.