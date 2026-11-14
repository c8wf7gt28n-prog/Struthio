# Code map for 0.8.3: DELETE, one face, the right column, the hologram's place, the kp emblem, and the tests

Reader's scratch: probe `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/code/probe.py` (also `probe2.py`, `fontcheck.py`). Output in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/code/out1920/` and `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/code/out1366/`: `probe.json`, `window.png`, `left_Files.png`, `left_Machine.png`, `left_Settings.png`, `right.png`.

The probe ran the real window on a disposable copy of After Hours 07 with `GRAPHITE_APPEARANCE=kasandra`, Illustrated art and the default 14 pt. Nothing under `/home/user/Struthio` was changed.

---

## 1. Every on-screen "Trash", and the other Delete/Remove words

### 1a. The can at the foot of the left column (`workbench/trash_can_qt.py`)
| file:line | exact string / what |
|---|---|
| trash_can_qt.py:51 | accessible name `'Trash'`; tooltip `'Trash · deleted files wait here and can be put back · drop files here'` |
| trash_can_qt.py:64 | the word whose ink is measured for the box: `'Trash'` (the box is sized from it; room for `'999'` at :65) |
| trash_can_qt.py:120 | the word drawn: `p.drawText(word, 'Trash')` |
| trash_can_qt.py:115-119 | Kasandra only: the can and word in `RED`, plus a little glow (`_bt.glow()`) |
| trash_can_qt.py:102, :107 | a click or Return/Enter/Space opens destination `'trash'` |
| trash_can_qt.py:145 | dropping files on the can runs `files.trash` |

The word's size is `SANS` 16 px × scale (:62); the count is 13 px (:63).

Measured box at P=354: 102×29 at window x=236, y=1094 (1920) and y=662 (1366).

In Special Elite at 16 px, `'Trash'` is 46.0 px wide and `'DELETE'` is 59.8 px, so the box grows by about 14 px. `pane_qt.trash_size` (pane_qt.py:89-97) and the right-aligned slot (pane_qt.py:649) take the new width without other changes.

### 1b. The right-click (`workbench/context_menu.py`)
| file:line | string |
|---|---|
| :498 | `'Moved to Trash. Restore it from Trash.'` |
| :499 | `'Moved %s to Trash · Trash puts %s back.'` |
| :673 | Entry `'trash'`, label `'Move to Trash'`, section `'danger'`, tip `'Trash keeps it; Restore puts it back'` |
| :703 | the same for a selection of several files (no tip) |
| :740 | tip `'Files keeps its own changes: rename, versions, export, Trash'` |
| :657, :669 | `'Discard this draft…'`; this moves the working copy to Trash (files_qt.py:334-335) |
| :1778, :1799, :1810, :1834-1835 | the key `'trash'`: its glyph, the danger tone, the "Change it" group, and its place in the first rows (keys, not words) |
| :2924 | the FOLDED table: `('Files: a selection', 'Move to Trash', 'file', 'trash')` |

`SECTION_WORDS` at :53 (`'danger': 'remove'`) is defined but never used, so it is not on screen.

### 1c. Files, the Trash page, Search
| file:line | string |
|---|---|
| files_qt.py:107 | `"Graphite's area (the Slate folder). Graphite writes here directly; every change keeps the version before it, and deletions go to Trash."` |
| files_qt.py:109 | `'An ordinary folder on this computer: any Debian program can open it too. Deleting moves to Trash, '` |
| files_qt.py:334 | dialog title `'Discard draft'`; text `'Move this working copy to Trash? %s is not touched, and the record of the work is kept.'` |
| files_qt.py:335 | `'Moved the draft to Trash. The original is unchanged.'` |
| files_qt.py:367 | `'Moved to Trash. Restore it from Trash.'` |
| files_qt.py:478 | the old Files menu: `'Move to Trash'`. The test reads it back, see §7. |
| files_qt.py:499, :505 | tab title and page title `'Trash'` |
| files_qt.py:507 | `'Nothing is in Trash.'` and `'Everything here can go back where it came from.'` |
| files_qt.py:510-511 | rows read `<original>  ·  moved <when>  ·  restore` |
| shell2.py:1179 | the Search "go" places: `('Trash', 'trash')` |
| shell2.py:1453-1455 | the `'trash'` destination opens `show_trash` |
| working_copies.py:275, :303 | status `'Working copy missing (moved or in Trash)'` |
| working_copies.py:386, :511, :538; working_folders.py:133 | `'COPIES_WORK_MISSING: the working copy was moved or put in Trash'` |
| files_service.py:94 | `'FILES_RESERVED: use Trash and versions through their own words'` |
| files_service.py:210 | the file's story: `'moved to Trash'`, `'restored from Trash'` |
| files_service.py:510 | the Kernel reply note `'In Trash. Restore puts it back.'` |
| tail_words.py:13 | Timeline words `'files.trash': 'Moved to Trash'`, `'files.restore': 'Restored from Trash'` |

The trash emblem on a folder thumbnail (thumbnails.py:89) is a drawing; it has no words.

### 1d. Kasandra's hand and her cards in Talk (shell2.py, desk_doers.py, stacy_hand.py, stacy_start.py)
| file:line | string |
|---|---|
| shell2.py:2069 | `'Done: “%s” is in the Trash, which gives it back.'` |
| shell2.py:2118, :2192 | `'“%s” is in the Trash, which gives it back.'` |
| shell2.py:2143, :2145 | `'… Move it to the Trash yourself if you want it gone'` |
| shell2.py:2262 | `'… move that folder to the Trash if you do not want it.'` |
| shell2.py:2269 | Undo tip `'Move the whole folder to the Trash, which gives it back, while it is still as I made it'` |
| shell2.py:2324, :2325 | plan steps `'… Undo moves it to the Trash'` |
| desk_doers.py:1261 | `'Move “%s” to the Trash'` and `'the Trash keeps it and gives it back'` |
| desk_doers.py:1263 | `'moved “%s” to the Trash'` |
| stacy_hand.py:53 | the refusal reason `'the Trash, once emptied, cannot be brought back'`. This exact string is asserted by a test. |
| stacy_start.py:153 | a line written into the starter project's notes: `'- To be rid of it, move the folder to the Trash, which gives it back. …'` |

### 1e. Desk acts
| file:line | string |
|---|---|
| desk_acts.py:159 | the act `hand.trash`: `named("Move a file in Files to the Trash through Stacy's hand; the Trash gives it back.")`, kernel `files.trash` |
| desk_doers.py:44, :1259-1263, :1351, :1397 | `HAND_ACTS['files.trash'] = 'hand.trash'`, `hand_trash`, and the reply field `'trashed'` |
| desk_doers.py:408-422 | `find_row` matches a menu path by row key or by row words. A path like `'Move to Trash'` therefore follows the label. |

### 1f. Not words on screen (they can stay)
- Operation names: `files.trash`, `files.trash_list`, `files.restore` (files_service.py:48, :53, :504-522) and the `trash.*` / `*.empty` pattern (stacy_hand.py:50-53).
- Undo lines `/files.trash {...}` (stacy_hand.py:202; shell2.py:2264). These are shown as a line on her card, so they appear on screen as code.
- On disk: the `.trash` folder (files_service.py:35; stacy_start.py:32) and the `files_trash` table (files_service.py:145).
- Docstrings and comments: pane_qt.py:2-21; cabinet_qt.py:181; settings_qt.py:277; menus2.py:105; machine_qt.py:5; glyph_set.py:397; tool_faces.py:201; boss_theme.py:72; shell2.py:304.
- Data with no reader on screen: navigator_catalog.py:51 `'footer': ['Settings', 'Trash']`.
- Release history: version.py:15, :53.
- Docs: GRAPHITE_DESK.md (35 mentions), DAILY_GUIDE.md (4), RELEASE_NOTES (several), README.md (2).

### 1g. Other on-screen Delete/Remove words that already mean something else
| file:line | string | meaning |
|---|---|---|
| context_menu.py:429 (and the FOLDED row at :2948) | `'Delete'`, key `edit:delete` | removes the selected words in a document. This is the direct collision with DELETE. |
| change_sets_qt.py:114, :161 | button `'Remove file'`; stages `{'op': 'DELETE', …}` | the op is shown as JSON text in the Changes room; it is a Kernel operation word |
| program_rooms_qt.py:839 | `'Remove file'` | unstages a file |
| compare_qt.py:122 | op `'delete'` (a colour only) | |
| working_folders.py:151 | `'remove <path>'` | words in a proposal |
| files_service.py:218 | `'a file was removed from the original'` | |
| memory_qt.py:24, :106 | `'Delete profile and feedback'`; `'Profile and feedback deleted…'` | |
| office_building_qt.py:514 | `'Delete every recorded instruction and outcome? Lessons you reviewed stay.'` | |
| agenda_qt.py:159, :204 | the word `'remove'` | cancels an Agenda row |
| agenda.py:174 | `'… Remove this, or add that again.'` | |
| document_qt.py:230 | tip `'Remove bold, italic and underline from the selected words'` | |
| typebar_qt.py:682 | `'… Remove explain when you are ready to run it.'` | |
| concern_qt.py:320; problem_qt.py:49, :58; notebook_qt.py:114 | `'Remove selected link'`, `'Remove selected variable'`, `'Remove selected source'`, `'Remove'` | |
| console_tab.py:78-80 | `'Remove drive'` → `'Eject media'` | |
| qt_app.py:558 | `'Remove Staged'` | legacy |
| qt_app.py:5233 | `('F2 / Del', 'Rename / delete in Browse')` | a legacy keys list; it prints a key |

No `Qt.Key_Delete` is bound anywhere in workbench. Backspace keys: field_qt.py:554, finder_qt.py:326, console_qt.py:184.

---

## 2. Every place a font family is chosen

### 2a. The three names and how they flow
- **boss_theme.py:38** (Graphite): `DISPLAY='IBM Plex Mono'`, `FACE='IBM Plex Sans'`. **:49** (Kasandra): `DISPLAY='Special Elite'`, `FACE='Special Elite'`. The rule is stated at :55-60.
- **shell2.py:26**: `SANS = FACE` of the appearance in force, `MONO = 'IBM Plex Mono'` always. shell2.py:265-267 `mono_font()` uses Plex Mono, falls back to DejaVu Sans Mono, and sets the Monospace hint.
- **shell2.py:49-60**: loads the Plex files, Parisienne and `branding/fonts/typewriter/SpecialElite-Regular.ttf`. Special Elite has a Regular style only, so DemiBold, Medium and 600 are synthesized or ignored. The fontcheck showed DemiBold has the same advance as Regular.
- **reading_profile.py:2-4**: DEFAULT `family`/`prose_family` 'IBM Plex Sans', `code_family` 'IBM Plex Mono'.
- **reading_preferences.py:100-122** `apply`: :108-109 swap Plex Sans for `bt.FACE` in ui and prose. :113 `QWidget {font-family:ui}` is the rule that puts every widget in Special Elite. :115 every `QPlainTextEdit` gets the code face. :116 prose. :123 the nav font.
- **reading_preferences.py:25-30** `family(name, fixed)`: **a code face must be fixed pitch.** Special Elite is not (measured: `isFixedPitch=False`), so as `code_family` it would fall back to DejaVu Sans Mono.
- **control_qt.py:400-404**: the Settings readback of "effective" families ignores the swap at :108-109. In Kasandra it reports IBM Plex Sans while the window shows Special Elite.
- **boss_theme.py:211-213**: titles, section labels, table header sections and hero labels in DISPLAY. **:218-221**: the head buttons More, HeadMenu, BossPrograms (Apps) and System in DISPLAY.

Measured in Kasandra on After Hours 07: the window font, the trees, the Talk lines, the input and the bubbles all resolve to **Special Elite**. The typing line resolves to **IBM Plex Mono**.

Special Elite is not fixed pitch, but it is close: at 16 px, i 9.09, l 8.64, M 11.16, space 4.69. Its line height at 16 px is **16.0**, against **20.8** for Plex. Tree rows (line + 12 = 28) and band heights follow it (desk_qt.py:382-383, :452-454).

### 2b. Every pick, what it shows, and whether a proportional face breaks it
"Kas now" is what the face resolves to in Kasandra today.

| file:line | Kas now | shows | proportional face? |
|---|---|---|---|
| pane_qt.py:122-126 `tab_font` `QFont('IBM Plex Mono')`, :190-191 | Plex Mono | Files · Machine · Settings tab words | safe: measured by `widest_bold` (:129-131) and `tab_px` |
| shell2.py:3458 pane title `font-family:"IBM Plex Mono"` | Plex Mono | `‹ Kasandra · Activity` back word | safe (sizeHint) |
| pane_qt.py:42-44 TREE_STYLE (no family); RowDelegate :470 `elidedText` | window face (SE) | the three left trees | safe: measured |
| shell2.py:631-635 `band_style` | DISPLAY 18 px (Kas); mono 16 (Graphite) | head menus, address `self.path`, More, Apps, System | safe |
| boss_theme.py:216 `WorkspacePath` "IBM Plex Mono" | Plex Mono | the workspace address | a path; mono reads better |
| boss_theme.py:230 `MonitorReading` "IBM Plex Mono" | Plex Mono | CPU/GPU/RAM/TXT numbers | digits change width (jitter as values move) |
| pulse_qt.py:60, :116, :126 `QFont(SANS)` | SE | meter labels, small caps | safe |
| boss_theme.py:235 `ChainProgram`; chain_menu.py:87-95 `MONO` | Plex Mono | a line in the chain builder, its rows | lines |
| typebar_qt.py:465-480 OneBox `font-family:MONO` | Plex Mono | **the typing line** | safe for layout; it holds lines and `@`/`/`/`$` input |
| typebar_qt.py:494-497 `font_at` (console button font) | SE | lower band words: Kasandra, Terminal, Search, Web, Log | measured; these words decide P (§3) |
| console_qt.py:172, :199-203, :214, :229-233, :399-400 | Plex Mono | **Terminal / console output, NoWrap** | **breaks**: shell output columns (`ls -l`, `ps`) line up by spaces |
| context_menu.py:2577, :2584 LineSlab and LinePreview `MONO` | Plex Mono | the line in the right-click panel and its row preview | **breaks**: :2603-2612 count letters from `'M'` and pad columns |
| context_menu.py:2028-2035, :2048-2084 | SE | right-click rows, captions | safe: elision is measured |
| programs_qt.py:45-59, :62-66, :455-458 | SE (caption: script or SANS) | desk menus (Apps list, System menu) | measured; but see test_system_menu.py:503 in §7 |
| tool_faces.py:133 `button.font()` | inherited | button faces | safe |
| shell2.py:1726 (Bubble code), :1944, :1981, :2031, :2417, :2702, :2794, :2896 `mono_font(13-16)` | Plex Mono | lines on her cards | wrap (`breakable`); readability only |
| shell2.py:2952 tag `setFixedWidth(44)` + MONO | Plex Mono | small tags in a fixed 44 px column | **risk**: a wider face clips in 44 px |
| shell2.py:400-415 TimelineDelegate stamp `mono_font` | Plex Mono | `hh:mm` times in Activity's recent lines | measured, but times stop lining up |
| shell2.py:1283, :1289 `mono_font` | Plex Mono | Search notes and line rows | safe |
| shell2.py:1285, :1550 `QFont(SANS)` | SE | Search and Library section headers | safe |
| shell2.py:3141 `mono_font(16)` | Plex Mono | "Works best: …" (a line's shape) | safe |
| shell2.py:3406-3407 SANS | SE | the Context face | safe |
| shell2.py:258-260 `pleasantry` DISPLAY | SE | greeting, date | safe |
| shell2.py:94, :112, :255, :306; desk_qt.py:135-138 | Parisienne (script is off: shell2.py:66-69) | quiet notes | n/a |
| field_qt.py:199-211 `mono()`, `display()`, `sans()` (Kas: SE, letter spacing −0.35 at :210) | mixed | the Field | see below |
| field_qt.py:449-470 | display(30) title; mono header and values; sans words | revision compare table | columns are fixed shares; values lose digit alignment |
| field_qt.py:1178-1220 | display (Kas) and mono | the head strip (FIELD, face words, census) | safe |
| field_qt.py:1471-1508 | mono tag and state, sans title, mono facts and where (`elidedText`) | a sheet card | measured; facts and addresses read best in mono |
| field_qt.py:1645-1678 | mono key legend and tag; sans title | the foot | measured (`_keys_line`) |
| trash_can_qt.py:62-63 | SE | the word and its count | measured by ink |
| log_qt.py:291-294, :392-409 MONO | Plex Mono | network connections and packets lists | **breaks**: column rows |
| finder_qt.py:216 | Plex Mono | a file's first lines | code/text indentation |
| compare_qt.py:27, :100 | Plex Mono | diff/compare cells | indentation |
| universal_viewer_qt.py:185, :193 `'monospace'` | system mono | text and code editors | code |
| thumbnails.py:204 MONO | Plex Mono | text-file thumbnails | code |
| thumbnails.py:58, :97 | Plex Sans, Parisienne | letters drawn on folder thumbnails | pictures |
| boss_qt.py:110 | Plex Mono | `[ WORKSHEET · LOCAL WORKSPACE ]` strip label | safe |
| boss_qt.py:186-193 | Plex Mono | ArtPanel ASCII lines; `[>_]` at `width-52` | fixed x |
| boss_qt.py:319-351 | Plex Mono | PanelInk ASCII portrait (character cells from `'M'`, :337) | **breaks**: ASCII art |
| idle_display_art.py:36-37 | Plex Mono | idle display labels | safe |
| code_rain.py:27-28 | DejaVu Sans Mono | Home's rain (character columns) | **breaks** |
| theme2.py:46 | Plex Mono | `arcButton="stac"` buttons (lines) | lines |
| theme2.py:124 | Plex Mono | `AddressChip` (addresses) | addresses |
| investigations_qt.py:44, :69-85, :199 | Plex Mono | the whole Investigations journal | room-wide styling |
| datasheet_qt.py:97-113; sheet_workbench_qt.py:27-55, :346, :353; work_trail_qt.py:39; program_rooms_qt.py:19 | Plex Mono | room-wide styling: Datasheet, Worksheet, Work trail, program rooms | tables and numbers |
| glyph_set.py:384, :457; chain_icons.py:26, :83 | Plex Sans/Mono | letters inside icons (¶, `{}`, `$`) | pictures |
| graphite_brand.py:220, :244 | Plex Sans | startup splash `GRAPHITE` | Graphite brand |
| memory_qt.py:62; reference_qt.py:55 | `setFamilies` fallback | | |
| qt_app.py:55-66 (MONO list), :5233 (`'%-26s'` column text); qt_theme.py:93, :110; arc_desktop.py:347; arcfairy_qt.py:256; arcos_tab.py:37, :56; console_tab.py:37-65; brain_link_tab.py:132-154; hardware_overview.py:32, :177; spice_qt.py:56; handbook.py:24 | legacy or other rooms | | the qt_app.py:5233 keys list is space-aligned |

### 2c. Where a proportional face would break alignment
1. Terminal and console output (console_qt.py:199-203, :229-233).
2. The right-click line preview columns (context_menu.py:2603-2612).
3. ASCII art: PanelInk and ArtPanel (boss_qt.py:186-193, :319-351) and code_rain.
4. The log lists (log_qt.py:392-409).
5. Code and text views: compare_qt, finder_qt, universal_viewer, thumbnails.
6. The fixed 44 px tag column (shell2.py:2952).
7. The space-aligned legacy keys list (qt_app.py:5233).
8. The code family through `reading_preferences.family(..., fixed=True)`, which refuses Special Elite (reading_preferences.py:27).

Everything else measures its words (ink, `horizontalAdvance`, `elidedText`), so it only gets wider. In particular P grows (§3).

---

## 3. The right column in Kasandra

**The width is the same P for both panes.** It comes from `desk_qt.pane_width` (desk_qt.py:162-170), whose result is `max(least, min(max(want, whole), room))`:
- `want` is the owner's dragged or saved width, otherwise `PANE` 268 × scale (desk_qt.py:30, :167-168).
- `whole` and `least` come from `needs()` (desk_qt.py:461-473): the slot words of the lower band and the head, and each dock's minimum.
- Applied at desk_qt.py:518-519, laid out in pane_qt.py:628-660.

Measured on After Hours 07:

| | Kasandra | Graphite |
|---|---|---|
| P at 1366×768 | **354** | 298 |
| P at 1920×1200 | **354** | |
| what sets it | `whole` 354 from `type_bar.slot_needs` [266, 354] (typebar_qt.py:528-530) | `whole` 298 |
| no owner width | yes | yes |
| sim_dock minimum | 279 | 272 |
| right content minimum | 242 | 240 |

So the lower band's words in Special Elite (Kasandra, Terminal, Search, Web, Log) make both panes 56 px wider. The right content box is P − 2×16 = **322 px** wide.

**At rest** the pane's title row is hidden (shell2.py:3470-3475) and the face starts at the top. Widgets from the top down (SlateFace, shell2.py:1782-1823), with measured window geometry `x, y, w, h`:

| widget | code | 1920×1200 | 1366×768 |
|---|---|---|---|
| right PaneBody | pane_qt.py:589-592 | 1566,61 354×1078 | 1012,61 354×646 |
| content (SlateFace) | | 1582,71 322×1015 | 1028,71 322×583 |
| **her picture**: `PanelInk(host,'face')` | shell2.py:1788 | 1582,71 **84×84** | same |
| her name (`signature`, a pleasantry) | shell2.py:1789; hidden at shell2.py:3457 | hidden | hidden |
| model line `'no model yet'` | shell2.py:1790 | 1678,71 226×18 | 1124,71 |
| hand (dial words) `'does and shows'`, a link | shell2.py:1792-1793, :2150-2155; words from stacy_hand.SAYS / LEVELS stacy_hand.py:30 | 1678,93 139×25 | 1124,93 |
| `This: … · more` line, with a 17 px mark (`marked`) | shell2.py:1804, :1756-1773 | 1606,165 298×21 | 1052,165 |
| `Now: … · activity` line | shell2.py:1806 | 1606,196 298×36 | 1052,196 |
| WorkBlock / RelatedBlock | shell2.py:1812-1813; WorkBlock moved into Activity at pane_qt.py:598 | hidden | hidden |
| conversation scroll (her cards) | shell2.py:1814-1817 | 1582,242 322×**832** | 1028,242 322×**400** |
| one greeting Bubble | shell2.py:1818, :1720-1729 | 308×110 | same |
| Composer and hint | shell2.py:1819-1823 | hidden (one typing line at the foot) | hidden |
| right foot (empty mirror of Trash) | pane_qt.py:589, :650 | 354×53 | same |

At 1920×1200, the picture and her two lines take the top 84 px. About 720 px under the one card is empty.

The picture is drawn at boss_qt.py:288-298. In Kasandra it is `kasandra_still(..., 'assistant_rail', <state>, zoom=2.2)`, edged in `LINE_MID`.
- Its size is 84 × ui_pt/14 (boss_qt.py:249-250), square (:241).
- It is hidden on Clean (boss_qt.py:236-244).
- It repaints when the state of the work changes (a 2 s watch plus `kasandra_art.watch`, boss_qt.py:211-224).
- In ASCII it shows `FACE_MARK` in Plex Mono (boss_qt.py:13, :324-325).

Her trail and "what always asks" are Talk cards (shell2.py:2166-2181, from the hand menu at :486-488). Card lines and code use `mono_font` (§2b).

**Where her stills appear besides Talk:**

| place | code | still chosen |
|---|---|---|
| the Field's rail | field_qt.py:228-246 (width `min(340s, 25% width, room)`; none if height < 520s or room < 200s); drawn at :1003-1027 (veil, inner-edge fade, foot fade, cached pixmap) | `assistant_rail` by state |
| the Field's head strip | field_qt.py:1169-1176, at 0.42 opacity | `field_edge` 'viewing' |
| Home/Today | `ArtPanel` (boss_qt.py:127-194; Today shell2.py:2989-2990; height fit shell2.py:3034-3047; up to 368 px) | `office_banner` 'idle' by `daily_turn`, plus the wordmark (boss_qt.py:170, :83-94) |
| worksheet strip | `WorkshopStrip` (boss_qt.py:97-124; shell2.py:534-535; strip height desk_qt.py:524) | `worksheet_strip` |
| worksheet evidence rail | `PanelInk 'portrait'` (sheet_workbench_qt.py:331) | `assistant_rail` |
| Investigations journal | `JournalArt(PanelInk 'journal')` (investigations_qt.py:25-27), right 46%, 160 px | `assistant_rail` |
| idle display | idle_display_art.py:195-198 | `office_banner` |

`choose_art` (boss_qt.py:477-494) refreshes only `ArtPanel` and `PanelInk`, plus the Field. A new left-column widget must be added there.

---

## 4. The left column

**Structure:**
- The dock `host.nav_dock` holds the PaneBody: tabs, content (`nav.stack`) and foot (pane_qt.py:569-572).
- The tabs are `PaneTabs(('Files','Machine','Settings'))`, built at settings_qt.py:261. Switching is at settings_qt.py:303-309. The saved mode returns at start (settings_qt.py:296-297).
- The stack holds: the cabinet page with `BranchTree 'LogicalCabinet'` (cabinet_qt.py:175-176), the settings page (settings_qt.py:271-273) and the Machine page (machine_qt.py:117-118).
- `host.desk_trees` (pane_qt.py:584) lists the three trees.
- Hidden parts are kept alive: pane_qt.py:573-583.
- PaneBody paints its inner edge line at pane_qt.py:241-246.

**The trees:**
- `BranchTree` (pane_qt.py:480-507). `set_metrics` (:492-496) makes the Kasandra indent ×1.25 (22 → 28).
- Row height = line + `ROW_PAD` 12 = **28**, from `tree_metrics` (pane_qt.py:84-86, :652-654).
- `drawBranches` → `draw_branches` (:304-366). In Kasandra it returns `draw_wires` (:314), the telephone poles: pole, crossarm, insulators, sagging drop with a faint strand, and a live path with glow (:369-442).
- Row words glow: `RowDelegate` (:445-477).

**Breathing (pane_qt.py:285-301, :487-507):**
- A 140 ms timer repaints the viewport only while the tree is visible, `glows()` is true (not Clean, boss_qt.py:427-431) and `still()` is false (Reduce motion, :285-291).
- `breath` = 0.85 + 0.15·sin(2πt/2.8). It is 1 when still.
- The after-hours rule for menus is `menu_catch.calm` (menu_catch.py:30-43).

**The can and the foot:**
- The foot is `PaneFoot` (pane_qt.py:213-221). Its height is `CONTENT_GAP` + can + inset = 8 + 29 + 16 = **53** (:100-102, :640-646).
- Trash's slot is right-aligned at `P − I − w` (:649). The right foot keeps an empty mirror of it (:650).
- Trash is created at shell2.py:3280-3283 and reparented at pane_qt.py:570.
- Its count is refreshed at shell2.py:1593-1594 and cabinet_qt.py:231-233.
- Spare room in the foot left of Trash: x 16→236, **220×29 px**. That is too short for a picture.

**Measured space under each tree (After Hours 07, Kasandra, Illustrated):**

| | 1920×1200 | 1366×768 |
|---|---|---|
| content / viewport | 322×960 at y=126 | 322×528 at y=126 |
| **Files**: 13 rows, owner's expansion (Concern › 10 + Unassigned › Documents, Questions); rows end at 364 | **596 px empty** | **164 px empty** |
| **Machine**: 9 rows, end at 252 | **708 px** | **276 px** |
| **Settings**: 65 rows, end at 1820 | scrolls (overflow 860, bar 0–31); **no room** | scrolls (overflow 1292); **no room** |

For comparison, Graphite at 1366: Files 112, Machine 240, Settings scrolls.

**The patch's rule against these numbers.** The reference patch places the picture with `kasandra_space`: viewport adjusted by 8 px at the sides, a top 18 px below the last row, and 12 px off the bottom. It hides the picture when the free box is under 150×110, and caps it at 288×316 keeping the 800:875 aspect.
- 1920 Files: free 306×567, picture **288×315**.
- 1366 Files: free 306×**135**, **hidden** (under 150).
- 1366 Machine: free 306×247, picture **226×247**.
- 1920 Machine: picture 288×315.
- Settings: none.

On the 1366×768 ThinkPad-class screen the patch's own threshold would hide the hologram on Files.

Repaint cost: the patch's `paintEvent` scales the 800×875 picture on every paint, and the tree repaints every 140 ms while breathing. A scaled picture should be cached per size.

---

## 5. Kasandra's art: `workbench/kasandra_art.py`, `branding/kasandra/`

**The module:**
- `folder(root)` returns `program/branding/kasandra` (:44-46).
- `SLOTS` = office_banner, field_edge, worksheet_strip, assistant_rail (:27). `STATES` (:28).
- Size limits: `MAX_CATALOG` 256 KB, `MAX_PICTURE` 16 MB (:33-34).
- `inside()` (:49-61): relative path, no `..`/`\`/`:`, picture suffix (`.webp .png .jpg .jpeg`), resolves inside the pack.
- `_scene_ok` (:64-72): id, file, a 64-character sha256, known slots and states, focal point in 0–1.
- `catalog()` (:75-100): read again when its mtime changes.
- `usable()` (:103-121): the **byte check**. The SHA-256 of the whole file must equal the catalog's `sha256`. The result is cached by (mtime, size), and a mismatch means "missing".
- `choose()` (:132-142): exact match, then the default for the state, then the quiet still, then None.
- `picture()` (:189-212): `cover()` crops round the focal point (:159-167); results are cached by size and dpr.

**Alpha is lost.** `source()` (:170-186) does `convertToFormat(QImage.Format_RGB32)` at :181. Any still that goes through `picture()` and `source()` loses its alpha. The hologram's transparent edges would turn opaque, and `cover()` would crop it instead of fitting it.

**`catalog.json`** (branding/kasandra/catalog.json):
- `default_by_state` (:4-21); `assistant_rail` covers working, awaiting_approval, completed, blocked and idle.
- `quiet_fallback` 'quiet_window' (:22).
- 8 scenes (:23-225): 3 at 1672×941 (office ×2, field_wires) and 5 at 1086×1448 (assistant_rail), each with a sha256.

**`README.md`:**
- :5-7 catalog, art and preview.
- :10-11 `wordmark.webp`, with its SHA-256 recorded (0a8d44e5…eb1e6).
- :13-14 `kp_monogram.png`, "256 x 256", the icon of Programs. **No SHA is recorded.** Actual: `7c5b3c9c1f16e0d1eca1f881a0ece60bda777355fdc0fa634495deb77170a073`.
- :16-17 the rights note (RIGHTS.md:5).

**Files outside the catalog are never verified:**
- the wordmark: boss_qt.py:77-80, a bare `QImage`;
- `kp_monogram`: shell2.py:592, a bare `QIcon`.

**MANIFEST.json** records bytes and sha for every pack file (:320-403), including kp_monogram at :360-363. New files need entries there.

**Hashes checked here:**

| file | SHA-256 |
|---|---|
| hologram.webp | b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec (matches the brief) |
| portrait.webp | c5be9f95648f3980210484e67bf380d00bd16503a16c8bad2f97e054eb3efe66 |
| kp_logo.png | 94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa |

**Verifying a new file the same way. Two routes:**

(a) **As a catalog scene.** Add a slot, for example `'left_projection'`, to `SLOTS` (kasandra_art.py:27). Add the scene with its sha256, focal point and states to catalog.json. `usable()` then checks the bytes.
- Paint path: needs an alpha-keeping decode instead of `source()`'s RGB32, and a contain-fit path instead of `cover()`.
- Tests: test_kasandra.py:92 asserts **exactly 8** scenes, and :140 expects **5** after 3 are broken. Both change.

(b) **As a marks table.** Put a small `{'hologram.webp': sha, '<emblem>.png': sha}` in kasandra_art, checked by a `usable`-like cached hash (the logic at :113-121), with the same SHAs written in README.md. This route also covers the wordmark and the kp mark, which are unverified today. Catalog counts and tests stay untouched.

`portrait.webp` is not needed if the face leaves the right column. Its only use in the patch is the Talk avatar crop.

---

## 6. The kp monogram's uses and sizes

| place | file:line | size |
|---|---|---|
| **The Apps button** at the right of the head (Kasandra only): `QIcon(kasandra_folder/'kp_monogram.png')`, icon only, text cleared; accessible name `'Apps'`, tip `'Installed apps and capabilities'` (:587); property `paperIcon` keeps its colours | shell2.py:586-597 | icon `QSize(side, side)` with side = round(36 × scale): **36×36** at 14 pt. Measured button 54×60 at x=1850 (1920) and x=1296 (1366). The head band is 60 px (`d.band`). Its font is DISPLAY (boss_theme.py:218-221; shell2.py:634). |

There are no other uses:
- The **wordmark** is `wordmark.webp`, on Home's banner only (boss_qt.py:83-94, :170). It is drawn at most 88 px tall and up to 46% of the width, only when the area is at least 240 px wide.
- The **window icon** is Graphite's tile in both appearances (`graphite_brand.window_icon`, graphite_brand.py:92-96; set at qt_app.py:2341-2342).
- The head's Graphite mark button is hidden (shell2.py:3339-3344).
- The splash is Graphite's (graphite_brand.py:238-245).

The new emblem is square, RGB, with **no alpha** on navy #070221, and its content sits in roughly x 255-985, y 410-885 (aspect about 1.54).
- `QSize(side, side)` with a keep-aspect icon would shrink it to 36 px wide (about 23 px tall).
- A cut-out version needs alpha. test_kasandra.py:115-121 asserts a 256×256 picture with alpha and a clear corner.

---

## 7. Tests that pin any of this

None of these were run (a reader's pass).

**Most window tests run in Graphite.** `boss_theme.chosen_appearance` falls back to Graphite (boss_theme.py:87-102), so Kasandra fonts and art are exercised only where `GRAPHITE_APPEARANCE` is set. For example, test_kasandra.py:198-208 runs subprocesses with it.

### Trash and DELETE
| test | asserts | changes with the direction? |
|---|---|---|
| test_context_menu.py:678-712 `test_nothing_is_lost_from_the_old_menus` | every word of the old Files menu (files_qt.py:478 `'Move to Trash'`) appears in the new menu's words, or FOLDED gives it a home; every FOLDED key is found | **Yes.** files_qt.py:478, context_menu.py:673/:703 and FOLDED context_menu.py:2924 must change together. |
| test_context_menu.py:265-269 | FOLDED has at least 65 rows; one home per word and kind | yes, with :2924 |
| test_context_menu.py:245, :252-256, :389-392, :764-765 | the keys `'trash'` (glyph, first four rows, FIRST) | no (keys) |
| test_desk_acts.py:186 | refusal text exactly `'the Trash, once emptied, cannot be brought back'` (stacy_hand.py:53) | **yes** |
| test_desk_acts.py:193 | `menu.choose` path `'Move to Trash'` is refused for a free hand | the path is a label (desk_doers.py:412-413). It keeps passing (refused) but checks nothing unless renamed. |
| test_desk_acts.py:206, :598-604 | key `'trash'` is not in MENU_ROWS; a CHANGES_ROW; `'hand.trash'` in the words | no |
| test_desk_acts.py:425, :441, :473, :557, :578, :628; test_desk_scenes.py:35 | the operation `files.trash` and the undo line `/files.trash {...}` | no (operation name) |
| test_graphite.py:292 | KEPT entry: the exact files_qt.py:107 string `"… and deletions go to Trash."`. Because it contains "Slate", the vocabulary test at :315-324 fails on any edit not mirrored here. | **yes** |
| test_desk.py:163-175 | `TRASH_CAN==30`; `trash_size`/`can_ink` formula; `foot_height` | no (independent of the word) |
| test_stacy_hand.py:29-34, :50, :95-119; test_stacy_start.py:39; test_vocabulary.py:64 | operation names, the `.trash` folder on disk; :34's text is only the assertion message | no |

### Fonts
| test | asserts | changes? |
|---|---|---|
| test_kasandra.py:45 | Graphite `DISPLAY == 'IBM Plex Mono'` | no |
| test_kasandra.py:54 | Kasandra `DISPLAY == 'Special Elite'` | no |
| test_graphite.py:131-140 | the wordmark set in Parisienne / IBM Plex Sans | no |
| test_desk.py:69 | `word_px` | no |
| test_system_menu.py:491-505 | the programs/System menu width is `max(d.pane−2·inset, programs_need, words_need)` and equals the pane column at 14 pt (:503) | Graphite; would matter if run in Kasandra with wider words |
| test_settings_registry.py:67-76 | the reading-family fallback is reported as DejaVu Sans | — |

No test pins `FACE`, `MONO`, `SANS` or `mono_font`.

### Art and the right column
| test | asserts | changes? |
|---|---|---|
| test_kasandra.py:90-94 | exactly **8** scenes, all usable | **yes** if a hologram scene is added to the catalog |
| test_kasandra.py:96-108 | choice by slot and state (assistant_rail ×5 states, field_edge, worksheet_strip, office ×2 turns, quiet fallback) | no unless the defaults move |
| test_kasandra.py:123-132 | a changed or missing still gives way; a broken catalog gives None | — |
| test_kasandra.py:134-140 | 3 bad scenes leave **5** | **yes** if scenes are added |
| test_kasandra.py:148-154 | `cover()`, including the Talk square 84×84 at zoom 2.2 | stays as a function test if the face leaves Talk |
| test_kasandra.py:156-167 | `picture()` at 84×84, dpr 2, zoom 2.2: 168×168, decoded once, caches bounded | same |
| test_kasandra.py:115-121 | **kp_monogram.png is 256×256, has alpha, corner alpha 0** | **yes** if the emblem replaces it (RGB, navy ground) |

No test names `ArtPanel`, `PanelInk`, the `face` kind, `SlateFace`'s layout (only `apply_on_page`, test_model_turn.py:211-216), `title_word`, `draw_wires` or `breath`.

### The Apps button
| test | asserts | changes? |
|---|---|---|
| test_desk_acts.py:274, :334-339, :636 | `head.open {'menu':'Apps'}` opens the Apps list; the word is 'Apps', never Programs | no |
| test_launcher.py:241 | the cat's names `('Open apps','Open apps','Apps')` | no |

No test pins the kp icon, its 36 px size or `paperIcon`.

### Not to run, for the builder's information
`tools/check_desk_ui.py:253-257` redraws the word `'Trash'` and compares pixels. `tools/check_cabinet_ui.py:118`, `tools/check_cabinet_actions_ui.py:99`, `tools/check_agent_ui.py:83` and `tools/check_continue_ui.py:91` assert `trash_can` and `top.programs` are visible.

---

## Notes for the builder

1. **DELETE collides with the document's `'Delete'` row** (context_menu.py:429, `edit:delete`) and with the Changes room's `DELETE` op (change_sets_qt.py:161). Keep the key `'trash'` and the operations `files.trash`/`files.restore`. Change only the words, and move `FOLDED` (context_menu.py:2924), the old Files menu (files_qt.py:478) and test_graphite.py:292 together.
2. **"All fonts" against what must stay fixed pitch:** Terminal output, line previews, ASCII art, the log lists and code views (§2c). The reading profile's code family cannot be Special Elite (reading_preferences.py:27). The typing line is MONO (typebar_qt.py:473-480). The pane tab words and title are hard-coded Plex Mono (pane_qt.py:124; shell2.py:3458).
3. **Kasandra's wider words already widen both panes:** P is 354 against 298 in Graphite. Any more Special Elite in the lower band widens them further.
4. **The hologram in the left column:**
   - Room: Files has 596/164 px free, Machine 708/276, Settings none (scrolls).
   - The patch's 150 px floor hides it on Files at 1366×768.
   - `kasandra_art.source()` drops alpha and `cover()` crops, so the hologram needs its own decode and fit.
   - Static animation can ride the tree's 140 ms breath timer. It must stop on `still()` and Clean, and the scaled frame should be cached.
5. **Removing the face square** frees the top 84 px of a 322 px column. The model and hand lines then stand alone, and the conversation (832 px at 1920, 400 px at 1366) is otherwise mostly empty.