# Kasandra art resolver: where Graphite shows art today (HEAD 13ddfc5, 0.7.0)

The pack says to start from 0.6.1 (`7e84d1b`). HEAD is now four commits past it, at 0.7.0.

**Pack check.** All 8 stills match the sha256 values in the catalog. They come in exactly the two sizes the current plates use:
- 1672×941: `office_dusk`, `office_rain`, `field_wires`. Same size as `Workshop after midnight.webp`.
- 1086×1448: `working_notes`, `awaiting_enter`, `completed_pencil`, `blocked_cable`, `quiet_window`. Same size as `Stacy after midnight.webp`.

## 1. Surfaces that show art today

**Shared loaders, `workbench/boss_qt.py`**
- All art comes from `program(host.root)/'branding'/'boss'` (`locations.program`).
- `workshop_plate` (22–24), `charcoal_workshop` (35–38) and `midnight_plate(folder, scene)` (41–44) each decode a full-size `QImage` into a small `lru_cache` keyed by `(folder, scene)`.
- There is no scaled decode, no `QPixmapCache` and no device-pixel-ratio handling anywhere. The only scaled-decode examples in the code are `finder_qt.py:250-255` and `thumbnails.py:156`.
- `draw_plate(painter, target, image, vertical_focus, region=None)` (47–56) does a cover crop. It always centres horizontally; only the vertical focus is a parameter. A catalog focal point `[x, y]` therefore needs a two-axis variant.
- `choose_art(host, mode)` (347–364) saves `session.state['desk_art']`, then:
  - calls `.refresh()` on every `ArtPanel` and `PanelInk`;
  - sets `field.view.art_mode` and `.texture = mode != 'clean'`;
  - calls `type_bar.align()`, which runs `desk_qt.apply` and so recomputes the worksheet strip;
  - relights the `WAITS` buttons.
- `appearance_menu` (265–294) is the "Desk artwork" menu: Illustrated / ASCII / Clean, Glow, idle display, Art plates. It is reached through Settings (`menus2.py:223-227, 273`). `session.py:117` validates the three modes.

**Home / "Good afternoon" (the pack's Office banner)**
- Home is `finder_qt.FinderPage`. Its first place is `shell2.TodayPage` (`finder_qt.py:368-370`; installed by `empty_workspace_qt.py:~40-52`).
- `shell2.greeting()` is at 2892–2895.
- `TodayPage.__init__` (2911) puts the greeting label in role `'hero'`. Directly under it, 2914–2915 adds `self.art = ArtPanel(host)`, above `CaptureBox`.
- `fill()` (2997, every 4 s via `self.timer`, 2941) rewrites the greeting. `showEvent` (2981) is the natural place for "rotate dusk/rain when the Office is reopened".
- `ArtPanel` (boss_qt 85–138):
  - Mouse-transparent (91). `QSizePolicy.Ignored, Fixed`.
  - Height from `plate_height()`: Illustrated `min(368, max(112, width//3))`, ASCII 112, Clean 0 and hidden.
  - Illustrated draws `midnight_plate(...,'workshop')` at focus 0.28, then falls back to charcoal at 0.05, then `night-signal.svg` through `QSvgRenderer`. It calls `drawImage` on the full image on every paint; nothing is cached at display size.
  - ASCII draws four fixed text lines plus `[>_]`.
- The "Office" destination itself (the Ingress room) draws no art.
- Legacy `home_qt.WorkshopHome` / `qt_app.StartPage` (453, used only without the shell, 3518–3523) draws the Slate bird. Its `ART = 'branding/stacy/control-center.png'` (25) is unused, and that file does not exist.

**Worksheet strip**
- `WorkshopStrip` (boss_qt 59–82) is mouse-transparent (65). It lives in `shell2.TopBar` (527–529) and is placed by `TopBar.place` (681–684) under the head band.
- Its height is set in `desk_qt.apply` (504–506):
  ```python
  strip = scaled(116, s) if worksheet and art == 'illustrated' and d.width >= 1250 and host.height() >= 820 else 0
  ```
  So it never appears in ASCII or Clean mode or in a small window.
- It paints a label at y=18, then the image in `QRectF(0, 28, w-1, h-33)` (about 15:1): the left 64% of the 'workshop' plate at focus 0.44, or charcoal at 0.22. No caching.

**Worksheet evidence rail**
- `sheet_workbench_qt.py:331`: `self.art = PanelInk(self.host, 'portrait')` in the preview side column.
- It becomes available at 756: `set_available(ready and self.tray.controls['sheet'].isEnabled())`. It is refreshed in `resizeEvent` (388).
- `self.bracket = PanelInk(host, 'bracket')` (368) is the ASCII bracket.

**`PanelInk(host, kind)`** (boss_qt 141–262)
- Mouse-transparent (149). Kinds: `portrait`, `bracket`, `journal`, `face`.
- Visible when `available and mode != 'clean'`. `face` additionally requires that `midnight_plate` is not null (164).
- Sizes from `plate_height`:
  - `portrait`: `min(width, max(130, host.height()-500))`
  - `face`: square, `round(84*ui_pt/14)`
  - `journal`: 116 (160 in `investigations_qt.JournalArt`, line 25)
  - `bracket`: 146
- `face` crops with `FACE = (0.262, 0.086, 0.488, 0.366)`. This is a hand-tuned box for Stacy's face; Kasandra will need focal points instead.
- Cached forever via `hasattr`: `_face`, `_charcoal_crop`, `_fallback_portrait`.
- ASCII mode:
  - `face` draws `FACE_MARK`; `bracket` draws `BRACKET`; `journal` reads `roof-antenna.txt`.
  - `portrait` samples the image into characters, cached under the key `(columns, rows)` only (249–255). A resolver must add the image ID to these cache keys.

**Stacy's pane portrait**
- `shell2.SlateFace.__init__` (1731–1733): `self.portrait = PanelInk(host, 'face')`, top-left beside the signature `Stacy`. `set_available(True)` is at 1739.
- SlateFace is the right-pane tab (`Shell2.__init__` 3100).

**Field**
- `FieldPage.refresh` (`field_page.py:116-118`) sets `view.art_mode` from `desk_art`, `view.art_folder`, and `view.texture = mode != 'clean'`.
- `FieldView.rail()` (`field_qt.py:204-219`) returns 0 unless all of these hold:
  - Illustrated mode;
  - `height >= 520*s`;
  - `_plate = midnight_plate(folder,'portrait')` is not null;
  - the room left after `columns*least_width() + gaps + 2*16*s` is at least `200*s`.
  
  Width is then `min(340*s, width*0.25, room)`.
- `least_width()` (199–202) is 164 in Illustrated and 176 otherwise. `body()` (221–222) subtracts the rail.
- `_art()` (862–884) renders the plate once per size into `_plate_drawn = (size, QPixmap)` at focus 0.0, with a 16% black veil, a left fade and a foot fade. The cache is keyed by size only, and `_plate` is never reset; both must change for an ID-driven still.
- ASCII mode: `BRACKET` in the body corner when `body > 760x420*s`. Clean: no rail and no texture.
- The rail is painted, not a widget. Its text boxes (`_stac` 896–938, `_do` 940–975) add click spots to `_hot`; the art itself has none.
- Paint order (715–752): ground, `_texture`, `_light`, `_art`, `_stac`, `_head`, then the clipped body.

**Others**
- `workbench/stacy_presence.py` is dead code: nothing imports it; only `MANIFEST.json:4680` lists it. The live reaction layer is `qt_app.ClipAssistant` (1241) with `bird_presence.BirdPresence` (1286–1287), which paints the Slate bird (1471–1473).
- `workbench/graphite_brand.py` paints only vector marks, the pointer and the cat. It loads no raster art.
- `idle_display_art.py:9, 199-212` also uses `midnight_plate`, `charcoal_workshop` and `Brain on Disk.png`.

## 2. Where images live, and shipping

- **Folder:** `branding/boss/`. Plates are in `branding/boss/plates/`, with file names containing spaces (`Stacy after midnight.webp`, etc.). Also there: `preview-operator.webp`, `journal-operator.webp`, `night-signal.svg`, `roof-antenna.txt`. The `branding/stacy/*.png` files are served only by `remote_service.py:279-281`.
- **Packaging:** `tools/package_graphite.py` `payload_paths` (109–120) ships every file under the program root except:
  - `EXCLUDED_PARTS` (`.ledger`, `.venv`, `__pycache__`, `.pytest_cache`, `.git`);
  - `*.pyc` and `*.partial`;
  - `build/` outside `BUILD_SHIPPED`.
  
  New files, for example `branding/kasandra/catalog.json` and `branding/kasandra/art/*.webp`, therefore ship automatically.
- **What has to happen for new images to ship:**
  - Regenerate `MANIFEST.json` with `package_graphite.py --manifest-only` (`write_manifest`, 135–140). Until then `check_hatch.runtime_section` reports `EDITED_SOURCES_NOT_YET_PACKAGED` and fails.
  - `release_integrity.verify` (25–45) checks only the listed files.
  - `payload_privacy` (`check_hatch.py:272-299`) scans the raw bytes of every listed file, so embedded metadata in the WebP files will be scanned.
  - `release_integrity.relative()` (16–22) is a ready validator for catalog `file` paths.
  - `RIGHTS.md:5` already covers artwork under `branding/`. The Special Elite font licence must be added alongside `branding/fonts/`.
- **WebP decoding works.** The venv's `PySide6/Qt/plugins/imageformats` contains `libqwebp.so` (PySide6 6.8.3, `requirements-qt.txt:2`). The shipped plates are already `.webp`. I read all 8 Kasandra stills through `QImageReader`, with no widgets created, and they report the catalog sizes.
- **Not confirmed:** whether the ThinkPad uses this pip wheel or Debian's system PySide6. The latter would need `qt6-image-formats-plugins`; no install script mentions Qt image plugins.

## 3. Work-state signals for the assistant rail

These are polled attributes; no Qt signals exist for them. The existing heartbeat is `Shell2.tick` (shell2 3135, 3319, every 5 s).

**Something waits for the owner**
- `boss_qt.WAITS = 'waitsForOwner'` (297). It is set by `waits(button, host, yes)` (321–324), which `approve_button` (shell2 485–495) calls.
  - Set True for `StagedRun` in `stage()` (1968, 1977) and `PlanRun` in `say_plan()` (2349–2354).
  - Set False in `run_staged` (1993) and `run_plan` (2366).
  - The property does not depend on the art mode.
- A Talk card is waiting while `card.ran is None` (staged) or `card.results is None` (plan).
- Cards are never deleted; `fold_earlier` (1824–1833) only hides them. Old unpressed Approves therefore stay true.
- Field: `FieldPage.pending` and `FieldView.go` are set by `_await_go` (`field_page.py:253-258`) and cleared by `go()` (261–266), `_reading_closed` (85–87) and sheet changes. Talk's Run survives those, so the WAITS buttons are the source of truth.
- **Name clash:** `SlateFace.pending` is the "Reading…" bubble (2525, 2562), not an approval.
- Elsewhere:
  - agent rows with `state == 'WAITING'` (`agent_qt.STATE_WORDS` 34; `WorkBlock.current`, 357);
  - jobs whose state starts with `'Waiting for'` (precedent: `qt_app.ClipAssistant.read_state` 1295–1309);
  - `agenda_qt.summary(host)[1]`, the waiting count (221–230).

**Something is running**
- `TopBar.refresh` (785–802) computes `active = [j for j in jobs.list if state in ('Queued','Running')]` and sets `self.equalizer.busy = bool(active)`. Read `host.shell2.top.equalizer.busy` rather than calling `jobs.list` again.
- `SlateFace.job` is truthy while the model answers. It is set at 2524 and 2561 and cleared in `poll` (2572); the timer runs every 800 ms.
- `host.agent_driver.running()` and `WorkBlock.current['state'] == 'RUNNING'`.
- `agenda_qt.Runner.busy` (264, 279).
- `FieldView.would`, a non-empty what-if (`field_page.show_would` 525–536). The pack's "notes during a what-if" maps to this.

**Just completed**
- `run_staged` sets `card.ran = True` and the text "Approved" (1991). `run_plan` finishes with all results ok (2385). `undo_staged` sets `card.undone = True` (2043).
- `poll` sees `job['state'] == 'Completed'` (2577).
- `stacy_hand.record(...)` appends `{'state':'done', 'at': '%Y-%m-%d %H:%M'}` to `session.state['stacy_trail']` (`stacy_hand.py:33, 241-249`). Minute resolution is too coarse for decay.
- Worksheet `tray.saved_receipt` (`sheet_workbench_qt.py:760`).

**Blocked / refused / failed**
- `card.ran = False` ("Refused", 1991/2006); a plan row marked `REFUSED` (2373–2376); `poll` job in Failed/Cancelled/Interrupted ("I stopped", 2573–2575); `card.undone = False`.
- Agent `FAILED`/`STOPPED` or `driver.last_error`.
- Field `view.problem` (records not readable).

**Proposed `current_state`** (e.g. in a new pure module; `QPushButton` from `PySide6.QtWidgets`, `WAITS` from `boss_qt`):
```python
HOLD = {'completed': 20.0, 'blocked': 45.0}   # 20 s = ClipAssistant.RECENT_SECONDS (qt_app 1254)
def note_outcome(host, ok):  # call at the end of run_staged, run_plan, undo_staged, poll
    host._art_outcome = ('completed' if ok else 'blocked', time.monotonic())
def current_state(host):
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    if any(b.property(WAITS) and b.isEnabled() for b in (face.findChildren(QPushButton) if face else [])) \
       or getattr(getattr(host, 'field_page', None), 'pending', None) is not None:
        return 'awaiting_approval'
    kind, at = getattr(host, '_art_outcome', (None, 0.0))
    fresh = kind and time.monotonic() - at < HOLD[kind]
    if fresh and kind == 'blocked': return 'blocked'
    top = getattr(host.shell2, 'top', None)
    if (face and face.job) or getattr(getattr(top, 'equalizer', None), 'busy', False) \
       or getattr(getattr(host, 'field_page', None), 'view', None) and host.field_page.view.would:
        return 'working'
    return 'completed' if fresh else 'idle'
```
- **Priority:** awaiting > blocked > working > completed > idle.
- **How "completed" decays:** after 20 s; immediately when a new waiting card or new work appears, because higher priority wins; or when `note_outcome` writes a newer stamp.
- To scope the WAITS check to cards that are not hidden, use `b.isVisibleTo(face)`. That is a policy choice: a folded Approve can still be pressed.
- Call the resolver from `Shell2.tick` (5 s) plus a nudge from `note_outcome`, `_await_go` and `go`.
- For model-suggestion tokens, `host._operation_epoch` already exists (`SlateFace.job_epoch`, 2524).

## 4. Field: where a skyline could go

- **The rail is portrait.** It is tall, the same shape as the 1086×1448 assistant stills. Keep the `rail()` rule unchanged and give it the `assistant_rail` still, invalidating `_plate` and `_plate_drawn` on (id, size). Landscape `field_wires` would be cropped badly there.
- **Head band (recommended for `field_edge`).** Height is `round(min(58*s, max(44, height*0.16)))` (189–190), across the full width, outside `body()`. Paint the still at low alpha at the start of `_head` (1016), before the `FIELD` label, the faces, the title and the census, with a fade under the text. At 1366 px wide this is a ~61-pixel source band near y≈0.39: wires and rooftops. It takes no space from the graph. Turn it off when `not texture` (Clean) and in ASCII.
- **Above the columns.** `Field.place` reserves `top = 40*scale` (`field_model.py:320`); column titles are drawn at `body.top() + 24*s - scroll_y` (`field_qt.py:1058-1070`). With slack, sheets sit at 0.42 of the free height (327), leaving room above. But this band scrolls and holds the headings, so art there would compete with them.
- **Empty Field** (`_empty`, 1339). With no sheets the whole body is free; a larger `field_edge` still could be drawn there.
- **The foot** (`foot_height` 192–197) carries text and Approve. Avoid it.

**Not found:** no Qt signal for work-state changes; no device-pixel-ratio handling for art; no existing focal-point or two-axis crop code.