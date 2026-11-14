# Graphite colour system: map for adding a second palette ("Kasandra")

All of this comes from reading the code at HEAD 13ddfc5. I ran no tests and did not start the program. The import-order findings come from static AST tracing, and none of the traced modules uses `importlib`. 66 files under `workbench/` contain `#rrggbb` literals, on 578 lines in total.

## 1. Where colours are defined

**`workbench/boss_theme.py`** is the single source of the desk palette.
- Lines 16–24:
  - `GROUND, PANEL, CARD, RAISED` (16)
  - `TERMINAL_GROUND '#080a09'` (17)
  - `LINE, LINE_STRONG` (18)
  - `LINE_MID` (19)
  - `TEXT, QUIET, FAINT` (20)
  - `AMBER, AMBER_SOFT` (both `'#4b2a14'`), `AMBER_EDGE '#ff9a36'`, `AMBER_TEXT '#ffba72'` (21)
  - `PENCIL_DEEP, ERASER, ERASER_DEEP, ERASER_MARK` (22)
  - `TEAL '#c3ed74', TEAL_SOFT, TEAL_EDGE, TEAL_TEXT` (23)
  - `READY '#c3ed74', STOP '#ff9a36'` (24)
- Values built from those at import time: `TOKENS` (39), `LEGACY` (40–46) and `CHROME_OVERRIDES` (75–132, built with `% globals()`).
- `GLOW` is a mutable list (33). It is the existing precedent for a runtime-set appearance value, set by `boss_qt.set_glow`.

**`workbench/shell2.py`** defines no hex of its own. It re-exports 23 names from `boss_theme` at lines 21–23. `SANS, MONO` (24) are font names, not colours.

**`workbench/theme2.py`** has no own hex. It takes 18 names from `shell2` (14–15) and `LINE_MID` from `boss_theme` (16). From them it builds:
- `PALETTE` (18–21)
- `QSS2` (23–137, plus `CHROME_OVERRIDES` appended at 278–279)
- its own `TOKENS` (143)

**`workbench/pane_qt.py`** has no hex. Line 41 imports `TEXT, QUIET, LINE, LINE_STRONG as BRANCH, ERASER, GROUND, TEAL_EDGE as TRACE, READY as LIVE`. `TREE_STYLE` (42) is built from them.

**`workbench/desk_qt.py`** has its own constants, not tied to `boss_theme`:
- `BAND = (12, 15, 14)` (239)
- `ERASED '#efeae0'` (240) and `ERASED_QUIET '#b0bcb9'` (241)
- `ERASER_MARK '#dd854b'` (242)
- `PENCIL '#f2a369'` (243)

**`workbench/field_qt.py`** has 3 literals: `'#000000'` (872, 985) and `'#ffffff'` (980). Everything else is `t.X` read at call time.

**`workbench/pointer.py` and `workbench/boss_qt.py`** have no hex; both read `t.X` at call time.

**`workbench/settings_qt.py`** (16 hex) hard-codes `INK '#eee9dd'` (14) and the sheets `ACTION_STYLE`, `PASSAGE_STYLE` and `STYLE` (15–39). These include `#cbf08b`, `#493225`, `#593a29` and `#14191b`.

**Other modules with their own colour constants:**
- `graphite_brand.py:28-30` (`GRAPHITE '#504d46'`, `PAPER`, `PAPER_LIGHT`, `ERASER_MARK`, `PENCIL`, `ERASED`; the splash and the cat)
- `page_light.py:13` (`DESK_LIGHT '#8c826b'`)
- `menus2.py:14` (`GRAPHITE '#6c675e'`)
- `chain_icons.py:7` (QColor objects)
- `code_rain.py:13-15`
- `idle_display_art.py:21-22`
- `app.py:31-35` (Tk-era)
- `qt_master_stop.py:31-34`

**Hex counts by file:**
- `qt_theme.py` 216. This file is dead: no module imports it; it is only named as a path in `engine.py:31` and `hardware_nav.py:136`.
- `qt_app.py` 61
- `viewer_tabs.py` 33
- `settings_qt.py` 16
- `boss_theme.py` 14
- `home_qt.py` 11
- `universal_viewer_qt.py` 10, `arcfairy_qt.py` 10
- `markdown_view.py`, `instruments_qt.py`, `hdl_qt.py` 9 each
- `calculator_qt.py` 8
- `empty_workspace_qt.py`, `console_tab.py`, `cabinet_qt.py`, `brain_link_tab.py`, `arcos_tab.py`, `arc_trace.py` 7 each
- `desk_qt.py` 4, `graphite_brand.py` 4, `field_qt.py` 3
- the rest have 1–6 each

**Painter `QColor('#…')` literals, which nothing ever relights:** `qt_app` 31, `hdl_qt` 9, `arcfairy_qt` 8, `console_tab` / `calculator_qt` / `arcos_tab` / `arc_trace` 7 each, `stacy_presence` 3, `code_rain` 3.

## 2. How colours are consumed, and what a late change would miss

Suppose a palette is set after the modules are imported but before the window is built. This is who would see it.

**Sees it: attribute read at call time through a module alias.**
- `field_qt` (`t`), `pointer` (`t`), `boss_qt` (`t`), `meter_cards`, `equalizer_qt`, `centre_bar` (sheet built with `getattr` at line 92), `centre_find`, `tool_faces`, `datasheet_qt` (`vars(ink)` at call time, 114), `work_trail_qt` (43), `chain_workbench_qt`.

**Sees it: imports from `boss_theme` inside functions.**
- `desk_qt:331, 428`; `pane_qt:160`; `typebar_qt:186, 222, 461, 606, 619`; `log_qt:281`; `document_qt:360`.

**Does NOT see it: function-level `from .shell2 import …`.** These read `shell2`'s copies.
- `chain_menu:87`, `context_menu:1836, 1905`, `desktop_header_qt:189, 239, 245, 473`, `explore_qt:237`, `log_qt:274, 391`, `programs_qt:363, 384, 423, 455`, `system_menu_qt:113`, `thumbnails:113`, `typebar_qt:244`, `view_modules/images_plus:106`.
- Also `log_qt:275`, which takes `ERASER_MARK, PENCIL` from `desk_qt`.

**Does NOT see it: module-level name imports.**
- `shell2:21`, `theme2:14, 16, 278`, `pane_qt:41`, `console_qt:34-35`, `compare_qt:14`, `document_qt:18`, `finder_qt:37`, `pulse_qt:17`, `thumbnails:11`, `trash_can_qt:12`, `agenda_qt:13`, `agent_qt:26`, `computer_qt:4`, `files_qt:16`, `investigations_qt:16`, `pills_qt:6`, `writing_marker:16`.

**Does NOT see it: values built once at import.**
- `boss_theme.TOKENS/LEGACY/CHROME_OVERRIDES`
- `theme2.PALETTE/QSS2/TOKENS`
- `pane_qt.TREE_STYLE`
- `document_qt.PAGE_STYLE` (27)
- `investigations_qt.EVIDENCE_WASH, STOP` (19–20)
- `writing_marker.INK` (21)
- `sheet_workbench_qt.SURFACE` (23–58, `% vars(ink)` at import)
- `program_rooms_qt.STYLE` (17–51, `% vars(colors)`)
- `idle_display_art._INK … _FAINT_GREEN`, which are module-level `QColor` objects (13–20)
- The application sheet and palette, applied once in `qt_app.make_app` (5331–5335).

**Caches.** These are fine if the palette is set before `make_app`, but each would need a reset or a palette key for a switch while running:
- `pointer.Pointer.cursors`, built at `install(app)`. `restyle` rebuilds only when `(glow, level)` changes (`pointer.py:162`).
- `tool_faces._icons`, keyed `(key, glow)` (`tool_faces.py:202`).
- `desk_qt._TILE`, the grain tile drawn from `BAND` (313–327).
- `field_qt._plate_drawn`, keyed by size only (868–877).
- `chain_icons._cache`.

**Relighting widget sheets.**
- `theme2.Relight` (250–270) passes every widget's own sheet through `boss_theme.relight` at Polish. Windows and widgets with `paperFunctionalInk` are skipped (shell2:205, 524, 571, 839; typebar_qt:204; return_thread_qt:143; machine_qt:78, 115; operations_qt:42; model_settings_qt:23).
- `relight` keeps any hex that is in `TOKENS`. Any other hex is remapped by property: backgrounds go to `GROUND` or `CARD`, borders to `LINE_MID`, `color` to `QUIET` or `TEXT`.
- Under Kasandra, Graphite hexes hard-coded in sheets (for example `settings_qt`'s `#cbf08b` and `#493225`) stop being tokens and get flattened. Remedy: add a Graphite-to-Kasandra entry to `LEGACY` for every Graphite token.

**Is any colour imported before `make_app` or `WorkbenchWindow`? No, in the real launch.**
- `launch.py` imports `workbench.version` (23), `prepare_release` (no `workbench` imports) and `graphite_brand` (splash at 142). Neither `graphite_brand` nor anything it imports at module level imports `boss_theme`.
- `from workbench.qt_app import …` (143) pulls in 38 `workbench` modules at module level, none of them `boss_theme`, `shell2` or `theme2`.
- The first import of `boss_theme` is `qt_app.py:5327` (`from .theme2 import PALETTE, QSS2`) inside `make_app`.
- Exceptions:
  - Tests import early, for example `tests_integrated/test_faces_find_light.py:14`.
  - The `*_checks.py` modules import `qt_app` and then call `make_app`.
  - I did not trace `tools/`.

## 3. The earliest place to read the owner's choice

**Launch path:**
1. `START_MINIMAL_DEBIAN.sh` → `startx LS_XSESSION.sh` → `START_OFFICE.sh:7-8` → `python -m workbench.launch`.
2. `launch.main`: `prepare(APP)` (135) → `startup_screen()` (142; first pixels, `graphite_brand.startup_pixmap` fills `GRAPHITE`) → `from workbench.qt_app import make_app` (143) → `qt_app.main` (5343).
3. `qt_app.main` calls `make_app()` (5344; `QSS2` and `PALETTE` applied, pointer drawn) and then `WorkbenchWindow(...)`.

**Session file:**
- The file is `session.config_dir()/'session-r10.json'` (`session.py:41-47, 82`). `config_dir()` honours `ARC1_WORKBENCH_CONFIG_HOME`.
- It is first read in `WorkbenchWindow.__init__` (`qt_app.py:2301`), which is after `make_app`. So the `Session` object comes too late.
- `Session.load` keeps only whitelisted keys (see `glow` at 125 and `desk_art` at 117), and `_save` writes `self.state` (276–283). A new `palette` key must be added to `load()`, or the first save drops it.
- `load()` also returns early when the saved `project` differs (104–105); the state then starts fresh.

**Recommended (least risk): `boss_theme` picks the palette at its own import.**
- Add `PALETTES = {'graphite': {...}, 'kasandra': {...}}` and a `_chosen()` helper:
  - If an environment variable such as `GRAPHITE_PALETTE` is set, use it.
  - Otherwise read `session-r10.json` key `palette` with plain `json` and `os`, falling back to `'graphite'` on any error.
  - Do not import `session.py`, which pulls in `engine` and `sdk`. Duplicate the 5-line `config_dir`, as `state_backup.py:41` already does.
- Assign lines 16–24 from the chosen dictionary.
- Because `boss_theme` is first imported inside `make_app`, every module-level copy and every built-at-import value listed above is computed from the right values with no rebinding.
- A change in Settings then applies at the next start.
- Tests patch `ARC1_WORKBENCH_CONFIG_HOME` only in `setUp`, after import. The environment variable is therefore needed so tests do not read the developer's real profile.

**Alternative: `apply_palette()`.** This is safe only if it is called in `make_app` before line 5327. It would have to recompute `TOKENS`, `LEGACY` and `CHROME_OVERRIDES`. Called any later, it must reach every module listed in section 2 under "Does NOT see it" (`shell2`, `theme2`, `pane_qt` including its aliases `BRANCH/TRACE/LIVE`, `console_qt`, `compare_qt`, `document_qt`, `finder_qt`, `pulse_qt`, `thumbnails`, `trash_can_qt`, `agenda_qt`, `agent_qt`, `computer_qt`, `files_qt`, `investigations_qt`, `pills_qt`, `writing_marker`, `sheet_workbench_qt`, `program_rooms_qt`, `idle_display_art`) and clear the caches. That is fragile.

**Either way, these need their own Kasandra branch:**
- `desk_qt` 239–243 and `_TILE`
- `graphite_brand` 28–30 (the splash comes before `qt_app`; it could call `boss_theme` lazily)
- `page_light.DESK_LIGHT`
- `settings_qt` 14–39
- `field_qt` black and white literals

## 4. What the colours mean, and where

**Amber = selected / has the keyboard:**
- `CHROME_OVERRIDES` (`boss_theme` 79–80, 84, 89, 94–96, 100, 102, 115–116, 126)
- `QSS2` (`theme2` 31, 50, 61–62, 64, 67–68, 71, 74, 81, 93, 95, 107, 111, 125; amber passages at 131)
- `desk_qt.InkWord.marked` 413–421 (`ERASER_MARK` for focus, `PENCIL` for checked)
- `pane_qt.PaneTab.mark_colour` 155–162
- `field_qt` sheet halo, edge and corner ticks (1166–1173), selected name `_bloom` (1209, 1261), reading page (794–795), FIELD head and chosen face (1019–1033)
- `tool_faces.paint` 107, 112
- `typebar_qt` 461–478 and 619–623
- `centre_bar` 84, 91; `centre_find` 219
- `shell2` 303, 406, 3369
- `context_menu` 1907; `chain_menu` 87–92
- `sheet_workbench_qt` `SURFACE` 26–40, 119, 588
- `datasheet_qt` 49–51
- `investigations_qt` 72–74, 87
- `program_rooms_qt` 36, 41–42

**Amber = waits for the owner (should become raspberry):**
- `boss_qt.WAITS = 'waitsForOwner'` (297). `waits()` (321–324), `choose_glow` (340–342) and `choose_art` (360–362) all call `lamp(button, t.AMBER_EDGE, …)`.
- `shell2.approve_button` (485–495): filled `AMBER_EDGE` with ink `GROUND`, hover edge `READY`. Called at 1977 and 2354; spent at 1993 and 2366. `ProgramReviewRun` (2633–2635) is also filled amber.
- `field_qt`:
  - Approve in the foot (549–551)
  - DO box halo, edge, 'DO', asks and `going` (954–971)
  - `_would_edge` halo while `self.go` (1228–1229)
  - census lamp `'waiting'` (1049–1055)
  - `state_colour` for every `ATTENTION` state (1186, 1251; `field_model.py:27`)
  - question/condition kind ink (1191, 1246)
  - help-sheet heads (816–832)
- Filled "commit" buttons: `sheet_workbench_qt` 54–56, `datasheet_qt` 112, `investigations_qt` 77, `program_rooms_qt` 44–45, `console_qt` 504 ("acts with your approval").
- Status words: `work_trail_qt` 110, 116; `investigations_qt` 199; `sheet_workbench_qt` 754–766.

**Amber with other meanings:**
- Near a limit: `equalizer_qt` 347, 352; `shell2:791` (`MODEL_STOPPED`).
- Current step: `shell2` 3075–3077.
- Recently changed (the turned corner): `field_qt` 1177.
- Decoration: band rule and its glow (`desk_qt` 331–350), Field floor light (992).
- Dashed leaders: `sheet_workbench_qt` 201, `chain_workbench_qt` 85.

**Green = live / pointer / hover:**
- The pointer: `pointer.drawn` 83–89
- `CHROME_OVERRIDES` 88, 93, 104, 118–119, 124
- `QSS2` 36, 42, 47, 55, 73, 82, 97, 122, 127
- `desk_qt` 427–429; `pane_qt` 159–161
- `pane_qt.draw_branches` (`LIVE` and `TRACE`, 303–340)
- `field_qt`: hover (1166, 1169), wires (1087–1093), thumbs (527), settled marks and glow (1137–1140, 1186), sky and pointer pool (995, 1013), staC rail (918–925)
- `tool_faces` 108, 126–131 and the menu icons 207–214
- `equalizer_qt`, `meter_cards:46`
- `settings_qt` hover `#cbf08b`

**Recheck today:**
- `field_qt._mark` draws `STATE_RECHECK` as a half-filled square (1146–1147) in `AMBER_EDGE`.
- The word 'recheck' (`STATE_WORD`, 34) is drawn upper-case as RECHECK (1187).
- Stale wires: amber, dashed `[5, 4]`, labelled 'recheck' (1079–1098).
- Census counts (1039–1055).
- `document_qt.stale_sentence` (705–714) and `agent_qt:378` show only a text link.

**Design consequences:**
- A dashed amber edge already means "would move" (`_would_edge`, 1225–1231, `[4, 4]`), so the lavender dashed recheck edge needs a different pattern.
- Kasandra uses the same cyan for focus and live. That erases the rule "the pointer is never mistaken for the keys" (`desk_qt` 410–412, `field_qt` 1163–1165); only shape cues would be left.
- Proposal: add role names to `boss_theme`, e.g. `FOCUS_*`, `OWNER`, `ON_OWNER`, `RECHECK`, `LIVE`. In Graphite they equal today's values; then move the call sites above to them.

## 5. What will look wrong on an indigo ground

- **Bands:** the near-black `desk_qt.BAND` grain (239, 270) is cached in `_TILE` and used by `paint_band` and `graphite_brand.pose_pixmap:420`. Its lettering, `ERASED '#efeae0'`, is warm paper.
- **Field:**
  - black veil and rim (872, 985), white scan lines (980)
  - rail plate filled with `TERMINAL_GROUND` (870–876)
  - Kasandra has no terminal ground; `art.shadow '#11132C'` is the nearest
  - the pointer's dark edge is also `TERMINAL_GROUND` (`pointer.py:89`)
- **Pages:** `page_light.DESK_LIGHT '#8c826b'` multiplies pages to warm brown. It is used by `pdf_qt:34`, `reference_qt:190` and `datasheet_qt:150`.
- **Brown fills:** `AMBER`/`AMBER_SOFT` `'#4b2a14'` are used as the selection fill and the writing passages (`theme2:131`).
- **Paper-era inks:**
  - `menus2` 14, `chain_icons` 7
  - `return_thread_qt` 144–149 and `machine_qt` 15–24: dark ink on widgets that are never relit; already wrong on today's dark desk
- **Other hard-coded colours:**
  - `idle_display_art` 21–22 (green tints)
  - `code_rain` 13–15 (orange)
  - `stacy_presence` 49–51
  - the splash, `graphite_brand.startup_pixmap` (225–232, warm grey)
  - `qt_app` painters: a light paper code gutter at 98–114 and 181–212, plus 399, 496–500, 871–894, 1469–1486, 2170–2231
- **Images:** the BOSS plates (`boss_qt` 10–17, under `branding/boss/plates`) are warm art. I did not inspect their pixels.
- **Tests:** `test_desk.py:124`, `test_graphite.py:75-76` and `test_system_menu.py:528` pin cross-module colour equalities. By reading, `desk_qt.PENCIL` (`'#f2a369'`) does not equal `shell2.AMBER_EDGE` (`'#ff9a36'`), and `graphite_brand.GRAPHITE` (`'#504d46'`) does not equal `shell2.TEXT` (`'#f4e8ce'`), so those assertions look stale already. I did not run them.