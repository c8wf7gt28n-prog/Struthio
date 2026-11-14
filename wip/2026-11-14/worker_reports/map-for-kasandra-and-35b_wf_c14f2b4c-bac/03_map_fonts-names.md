# Fonts and the assistant's name: map for the Kasandra appearance (HEAD 13ddfc5, read-only)

## 1. Fonts today

**How fonts load**
- `workbench/shell2.py:24-25` sets `SANS, MONO = 'IBM Plex Sans', 'IBM Plex Mono'` and `PLEX = (5 ttf names)`. `:43` sets `SCRIPT = 'Parisienne'`.
- `shell2.load_fonts(root)` (`:46-55`) registers each file in `branding/fonts/plex/` and then `branding/fonts/script/Parisienne-Regular.ttf` with `QFontDatabase.addApplicationFont`. A missing file is skipped without error. It returns `SANS in QFontDatabase.families()`.
- It is called in two places: `qt_app.make_app()` at `qt_app.py:5319-5331` (`load_fonts(PACKAGE)`, before `app.setStyleSheet(QSS2)`), and again in `shell2.install(host)` at `shell2.py:3517`.
- There is a second, separate loader, `reading_preferences.load_fonts(root)` (`reading_preferences.py:13-22`). It reads only `branding/ux17/fonts/SOURCE.json` (OpenDyslexic), checks every file's sha256 and raises `FONT_SOURCE_CHANGED` on a mismatch. Callers are `:102` and `:163`. This is the model to follow if Special Elite should be pinned to its source.
- No app-wide font is set by code. `reading_preferences.py:105-113` writes `QWidget {font-family:…}` from the reading profile.

**Files, licences and the manifest**
- `branding/fonts/plex/` holds the 5 ttf files plus `LICENSE.txt` (OFL) and `NOTICE.md` (lists sha256s).
- `branding/fonts/script/` holds `Parisienne-Regular.ttf` and `OFL-Parisienne.txt`.
- `branding/fonts/LICENSE.txt` and `NOTICE.md` sit at the top level. Oddity: that NOTICE describes Noto Sans CJK, but no Noto file is present.
- `MANIFEST.json:160-203` lists each font file with bytes and sha256. The manifest is rewritten by `tools/package_graphite.py:123-139` (`manifest_for` / `write_manifest`). `payload_paths` takes every file except `EXCLUDED_PARTS` (`:33`), so a new font under `branding/` is picked up when packaging. `workbench/release_integrity.py:25-44` verifies it.
- `THIRD_PARTY_NOTICES.md:5-7` has one line per font.

**The script face is effectively off**
- `cursive_on(host)` (`shell2.py:61-64`) always sets `SCRIPT_ON[0] = False` and returns False ("BOSS uses readable terminal lettering").
- So `pleasantry(label, host, pixels)` (`:245-255`) always takes its else-branch: a widget QSS of `font-family:"IBM Plex Mono"; font-size:<pixels>px; font-weight:500`. It also sets the properties `pleasantry` and `pleasantry_px`.
- `quiet_script` (`:82-92`) only colours the text QUIET. The script heading rule in `chrome_css` (`:297-300`) never applies.
- **Pleasantries in script**: the action is created at `shell2.py:3211` in the View group, which is shown as Arrange (`menus2.py:17,75`). It writes the setting `appearance.cursive` (`ledger_control.py:87`, `session_settings.py:21`). But `menus2.rebuild` detaches every action (`:268-269`) and re-adds only the keys in `VIEW` (`:24-25`), and `VIEW` has no `'@pleasantries'` (the key exists only in the extras map at `:197`). So it is probably not visible. I did not run the program to confirm.
- `control_qt.py:330-343` is the existing live re-apply loop. It walks every QLabel with the property `pleasantry`, `quiet_script` or `quiet_words`, then calls `top.ledger_head()` and `inspector.refresh()`. It is the template for switching the appearance live.

**What adding Special Elite needs**
- **Placement:** copy `SpecialElite-Regular.ttf` (166180 bytes, sha256 `a776fcb4…4bc4`) to `branding/fonts/typewriter/`, with `SpecialElite-LICENSE.txt` beside it plus a `NOTICE.md` in the style of the Plex one. The Plex files in the zip are byte-identical to the bundled ones, so nothing else needs copying.
- **Family name:** from the font's name table, family (ID 1) is `'Special Elite'` and PostScript (ID 6) is `SpecialElite-Regular`. Add `DISPLAY = 'Special Elite'` next to `SANS`/`MONO` and one more `addApplicationFont` in `shell2.load_fonts`.
- **Licence:** it is **Apache 2.0**, not OFL (name IDs 0 and 13; the licence file is Apache 2.0). `THIRD_PARTY_NOTICES.md` needs a line that says so. `COPYING` note 4 (`:46-56`) lists Apache-licensed libraries only. Whether a bundled Apache font needs naming there is a licensing decision for the owner.
- **Packaging and tests:** regenerate the manifest at packaging. Tests register fonts by path directly (`tests_integrated/test_graphite.py:132-133,157,187,212`).

## 2. Where the name "Stacy" is shown

Method: I tokenised every `workbench/*.py`, dropped docstrings and comments, and kept string literals containing "Stacy" or "STACY". That gives **99 literals, of which 79 are shown, across 23 files.**

**`shell2.py` (19)**
- `:460` menu title `"Stacy's hand"` (Rules ▸ and the hand words)
- `:795` BrainChip tooltip (the chip is hidden at `:551`)
- `:968` `CAPTIONS['slate']`
- `:982` OneBox tooltip
- `:1086` section `'ASK STACY'` and `:1087` row `'Ask Stacy · …'`
- `:1145` command `'Talk to Stacy'`
- `:1734` `self.signature = pleasantry(QLabel('Stacy'),…)` (hidden by `:3366`)
- `:1735` `self.model` starts as `'Stacy'` (overwritten at `:2837` with "speaks staC · …")
- `:1765` accessible name `'Message Stacy'`
- `:1796` tooltip on the "This:" line
- `:2083-2084` hand button accessible name and tooltip
- `pane_title` `:3373-3378`: `'‹ Stacy'`, `'Stacy'`, `'‹ Stacy  ·  %s'`, accessible `'Stacy'` / `'Back to Stacy'`, tooltip `'Back to Stacy'` (7 literals)

**`typebar_qt.py` (4)**
- `:27` `SHOWN = {'slate': 'Stacy'}` (used at `:98` and `:252`)
- `:43` `SENDS['slate']`
- `:45` `TIPS['slate']`
- `:676` tooltip

**`meter_cards.py` (7)**
- `:31` and `:33` `DOORS` (meter tooltips via `desktop_header_qt.py:178-179`)
- `:89` heading `'GRAPHICS · STACY’S MODEL…'`
- `:92` `'Stacy ' + face.model.text()`
- `:93` tooltip
- `:132` heading `'TEXT · WHAT STACY HOLDS'`
- `:136` tooltip

**`context_menu.py` (15)**
- Menu entries "Ask Stacy about this… / to work on this…" at `:407, 639, 644, 725, 761, 1109, 1124, 1427, 2268, 2270, 2291`
- Tooltips at `:1258, 1356, 1379, 1425`

**Smaller counts**
- `files_qt.py` (4): `:322` (dialog title), `:402`, `:441`, `:447`
- `qt_app.py` (3): `:1444` menu, `:1775` placeholder, `:5240` About
- `instruments_qt.py` (3): `:268`, `:269`, `:291`
- `boss_qt.py` (4 accessible names of the art): `:92`, `:151`, `:152` ×2
- `log_qt.py` (2): `:346`, `:682`
- `field_qt.py` (2): `:54` (keys help), `:966` (tooltip in the DO rail)
- `agenda.py` (2): `:378`, `:400`. These are written into DB rows, so they are stored text.
- `empty_workspace_qt.py` (2): `:90`, `:143`
- `home_qt.py` (2): `:41`, `:129`
- One each:
  - `finder_qt.py:857`
  - `field_brief.py:175`
  - `conditions.py:229`
  - `document_qt.py:205`
  - `pulse_qt.py:163`
  - `brain_qt.py:21`
  - `concern_qt.py:67`
  - `project_desk_qt.py:49` (tab)
  - `office_building_qt.py:189`
  - `profile_network.py:201`

**Not shown**
- `version.py` (12 literals): `LINEAGE` is referenced nowhere else.
- Object names: `shell2.py:1737` `'StacyHand'`, `stacy_presence.py:19` `'StacyReaction'`.
- `boss_qt.py:12` is a file name. `project_desk.py:234` is a type name.
- `stacy_start.py` (5): text written into the owner's Godot project files.
- `local_brain.py:746,749`: the model's system prompt ("You are Stacy…").
- The activity actor `'STACY'` (`local_brain.py:82,517`).

**Places with no name to change**
- The Field's rail paints only `'staC'` and `'DO'` (`field_qt.py:918,957`).
- Her own cards speak in the first person ("What I did by myself…", `shell2.py:2100`).
- `stacy_hand.LEVELS` / `SAYS` (`stacy_hand.py:30,35`) contain no name.
- "What she did…" (`shell2.py:480`) and "What she has in view" (`meter_cards.py:138`) use pronouns only.
- No status message names her.

**Outside this count:** `workbench/remote_pwa/*`, the docs, and about 63 literals still saying "Slate" (settings category, folder names).

**Proposed function.** Add one pure function, with no Qt import, in a small module such as `workbench/assistant_identity.py`:
```python
def assistant_name(host=None):
    """'Kasandra' in the Kasandra appearance, else 'Stacy'. The language stays staC."""
    state = getattr(getattr(host, 'session', None), 'state', {}) or {}
    return 'Kasandra' if state.get('appearance') == 'kasandra' else 'Stacy'
```
The appearance key is an assumption. Today's appearance switch is `session.state['desk_art']` in `ART_MODES` (`boss_qt.py:9,347-349`).

- **Should call it:** every shown site above, apart from the exceptions in the last bullet.
  - The module-level dicts `typebar_qt.SHOWN/SENDS/TIPS`, `shell2.CAPTIONS` and `meter_cards.DOORS` are built at import time, so they must become functions or be formatted where they are used.
  - `pane_title` needs it for every literal.
  - Labels built once (typebar words at `:252`, menu titles) need re-applying on a switch, through a loop like `control_qt.py:330-343`.
  - `local_brain.py:746,749` should also use it, so the model names herself to match.
- **Accessible names and descriptions** should follow the shown name, except the `boss_qt` art names, which belong with the artwork set.
- **Can stay:**
  - About/RIGHTS text (`qt_app.py:5240`), because it is legal wording.
  - Stored agenda rows, the trail (`stacy_trail`), the actor `STACY`, and `stacy_start` file headers, because they are history.
  - Object names, settings keys (`stacy.*`), and `LINEAGE`.

## 3. Headings that would take the display face

- **Today's greeting ("Good afternoon.")**
  - Built at `shell2.py:2911` as `role(QLabel(greeting()), 'hero')` in `TodayPage.__init__`; the text comes from `greeting()` at `:2892-2895`.
  - The app QSS gives `arcRole2="hero"` Plex Mono (`boss_theme.py:105-106`) at 28 px (`shell2.py:296`).
  - But `fill()` at `:3002` calls `pleasantry(self.greeting, host, round(34*scale))`, and that widget-level QSS wins: Plex Mono, 500 weight, 34 px.
  - Hook: the else-branch of `pleasantry()` (`:253`), or a new `display_face(label, host, px)` that sets `font-family:"Special Elite"`.
- **The Field's heading**
  - Drawn with QPainter in `FieldView._head` (`field_qt.py:1016-1045`).
  - `'FIELD'` uses `self.mono(13, QFont.Medium)` in AMBER_EDGE (`:1019-1021`).
  - The workspace title `self.field.title or 'This workspace'` uses `self.sans(17)` (`:1036-1045`).
  - Reading pages over the Field use `self.sans(17|19)` (`:796-801`).
  - Hook: add a `display(px)` helper next to `mono()` / `sans()` (`:183-187`). These build `QFont('IBM Plex Mono')` / `QFont('IBM Plex Sans')` by literal name, not through the shell2 constants.
- **The right pane's title**
  - A `QPushButton#PaneTitle` created in `Shell2.pane_title` (`shell2.py:3361-3368`). Its own QSS fixes `font-family:"IBM Plex Mono"; font-weight:600`. Its size comes from `PaneTabs.place` → `title.setFont(font)` (`pane_qt.py:199-201`, `tab_font` at `:122-126`).
  - Since 0.7.0 the whole title row is hidden at rest (`tabs.setVisible(not home)`, `shell2.py:3383-3385`), and `face.signature` is hidden at `:3366`.
  - So "Kasandra" at the top of the pane, as in the study, needs that at-rest rule changed, not just the text.
- **Brand in the head**
  - `Wordmark` (`shell2.py:194-242`, a painter outline of "Graphite") is built at `:537` but always hidden (`:537`, `:685`). Nothing else draws a brand.
  - Study `01-office.webp` shows "GRAPHITE / LAIN" at the head's left. That would be new, and could use `Wordmark` with the display face.
- **Other page titles** (`arcRole2="title"`) are styled only by app QSS (`shell2.py:296`, `boss_theme.py:105`). Changing the family is one QSS rule.