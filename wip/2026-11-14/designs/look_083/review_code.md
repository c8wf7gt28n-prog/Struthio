**Review of 0.8.3 code and cost (worktree 3af59a1 against d1df337)**

I reviewed a copy of the worktree at `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_review_b/tree` and a copy of the base made with `git archive d1df337` at `.../look_review_b/base`. Every run used `QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child .../venv/bin/python`. My probe is `.../look_review_b/probe_review.py`, which runs the real window through `tests_integrated/kasandra_window_probe.run`. Its outputs are `.../look_review_b/out_*.txt` and the test logs are in `.../look_review_b/runs/`. I fixed nothing.

## Findings, most severe first

**1. Medium: Graphite's pane tabs changed face, from IBM Plex Mono to IBM Plex Sans.**
- Cause: `workbench/pane_qt.py:125-129`. `tab_font` now uses `FACE`, and `FACE` is `'IBM Plex Sans'` in Graphite. The plan's "no-op in Graphite" claim is wrong for this line.
- Evidence: `probe_review.py base|tree graphite 1366 768 layout` (files `out_layout_{base,tree}_graphite.txt`).
  - Tabs, base: `['Files',[17,77,88,41],'IBM Plex Mono',...]`. Tabs, tree: `'IBM Plex Sans'`.
  - The same change shows on all six tabs (Files, Machine, Settings, Talk, Activity, Context).
  - The pane minimums moved: `least` 61→51 and `need` 215→185.
  - Nothing else in Graphite's layout changed apart from DELETE (`[187,662,95,29]`→`[168,662,114,29]`).
- Fix: make `tab_font` use `DISPLAY` (Plex Mono in Graphite, Kasandra Elite in Kasandra), or `FACE if APPEARANCE == 'kasandra' else MONO`. That restores Graphite's tabs, `least` and `need`.

**2. Medium: A face the owner chose herself no longer reaches her column, the line slabs or the tabs. Her size changes do not reach them either.**
- Cause: `set_face` (`shell2.py:1748`) and every `face_css(bt.FACE/bt.MONO, …)` in `kasandra_column.py:107-116` hard-code the theme faces.
- Evidence: `owner_faces` case, Kasandra 1366. I applied a profile with DejaVu Serif for words and DejaVu Sans Mono for code through `reading_preferences.apply(persist=True)`.
  - Base: hand link, model line and line slab are all `DejaVu Serif`; they follow her face.
  - Tree: hand `Kasandra Elite`, model `Kasandra Elite Mono`, masthead name `Kasandra Elite`, slab `Kasandra Elite Mono` (her chosen code face is ignored), tabs `Kasandra Elite`.
  - The plain-text editors still follow her: `['DejaVu Sans Mono','DejaVu Serif']`.
- The sizes are also fixed when the widget is built: `round(14*s)`, `round(15*scale_of(host))`. A change of reading size never reaches the masthead or slabs already shown; the builder admits this for the masthead.
- Fix:
  - Resolve faces through `reading_preferences.in_force((p['family'], p['prose_family'], p['code_family']))`: index 0 for words, index 2 for lines.
  - Re-apply the masthead and existing slabs from `Shell2.restyle(profile)`.

**3. Low-Medium (owner's Reduce-motion rule): the masthead cursor keeps breathing after Reduce motion is turned on while something waits, and while the app is inactive.**
- Cause: `kasandra_column.py:76-85` and `:156`. The `still` value is read only when the state changes (`show_state` returns early when the state is the same). `alpha()` never checks it again. The 140 ms timer has no app-state check.
- Evidence: `cost2` case with `current_state` patched to `'awaiting_approval'`:
  - `cursor_waiting {'active': True, 'interval': 140}`
  - `cursor_app_inactive {'active': True, 'stage_running': False}`
  - `cursor_reduce_motion {'active': True, 'stage_running': False}`
  - Minimised: stopped.
- Fix:
  - In `Cursor.alpha()` and on each tick, return 1.0 and stop the timer when `pane_qt.still(self)` is true or the app is not active.
  - Have `HologramStage.wake_or_sleep` (or `reading_preferences.apply`) call `masthead.cursor.set_state(...)` again.

**4. Low-Medium (cost): her frames cost more than the plan's budgets. The test threshold was loosened to twice the budget.**
- Evidence: `cost2`, 1920×1200, Files tab, stage 297×396. Her clock was switched on and off in turn, 3 × 10 s each.
  - 12.0 frames a second.
  - `paint_ms` mean 1.966, p50 1.87, p95 2.82, max 13.5 ms. The plan's budget is ≤1.5 ms.
  - Process CPU: running `[13.9, 15.71, 14.93]`, her clock off `[12.28, 12.2, 11.52]`. Her share is **2.85% of one core**. The plan's budget was ≤2%, and that budget covered all of Illustrated minus Clean.
  - Other processes were loading this shared container, so absolute numbers are noisy. The on/off pairing limits the bias.
- `test_hologram.py` asserts `paint_ms < 3.0`; the plan said 1.5.
- Cause: each frame (`hologram_qt.py:100-131`, `:330-357`) makes five full-size compositing passes, then two `drawImage` calls (the fringe and the frame).
- Fix:
  - Make `noise_offset` follow `n % 6` and the scan offset follow `n % 3`, so the frames repeat every 6.
  - Pre-compose those 6 frames once per size and state (about 2.8 MB at 297×396). Each tick is then one `drawImage`.
  - Bake the cyan fringe into the figure layer.
  - Or run at 10 fps.

**5. Low: the idle-display condition is dead code.**
- Cause: `hologram_qt.py:275-279` calls `idle()` only if `callable(idle)`, but `IdleDisplay.showing` is a property that returns a bool (`idle_display_qt.py:74-76`). So the condition is never true, and nothing calls `wake_or_sleep` when the idle screen opens.
- Evidence: `stops` case. `idle_showing_type bool`; with `showing: True`, the timer was still running even after an explicit `wake_or_sleep`. She received 0 paints in 1.5 s, because Qt skips widgets that are covered. So the waste is 12 Python ticks a second, not paints.
- Fix:
  - `idle = getattr(self.host.idle_display, 'showing', False); idle = idle() if callable(idle) else bool(idle)`.
  - Call `stage.wake_or_sleep()` from `IdleDisplay.preview` and `dismiss`.

**6. Low: when the picture's bytes verify but it cannot be decoded (for example, no WebP plug-in), the stage still shows and decodes the file again on every frame.**
- Evidence: `NO_WEBP=1 … nowebp` case, with `QImageReader.read` patched to return null for `hologram.webp`.
  - Result: `{"installed": true, "visible": true, "running": true, "decodes": 39, "paints": 38}` in about 3 s.
  - It logs `QPainter::begin: Paint device returned engine == 0` and `QImage::scaled: Image is a null image`.
  - She shows as a beam and base with no figure.
- Cause: `kasandra_art.py:259` returns `(QImage(), ())` without caching it, and `plan()` calls `glitch_rows(path)` every frame.
- Fix:
  - Cache the failure in `_cut`.
  - In `hologram_qt.install` (`:434`), return None when `kasandra_art.cutout(path).isNull()`.

**7. Low: a touch while her clock is asleep leaves a torn frame on screen.**
- Evidence: `touch_asleep` case. With `app_active` False the timer was off. A MouseMove over her figure gave `{"paints_after_touch": 1, "last_paint_had_tear": true}`, and nothing repainted her within 1.5 s.
- Cause: `hologram_qt.py:292-301` requests one repaint, and no tick ever clears the tear.
- Fix: ignore touches unless `self._timer.isActive()`, or schedule `QTimer.singleShot(2*FRAME_MS+1, self.update)`.

**8. Low (wording): the masthead says "quiet" directly above "Now: Nothing running · 1 waiting for you".**
- Evidence: builder frame `look_build/frames/F02_left_files_1366.png`.
- Cause: `current_state` counts only a waiting Approve button or the Field's pending item. "Waiting for you" on the Now line counts Agenda items (`shell2.py:1937`).
- Fix: count waiting Agenda items in `awaiting_approval`, or show no state word while idle.

**9. Low (information removed): in Kasandra the model line's hover tip no longer says "Learning from N outcomes you marked or ran".**
- Cause: `shell2.py:2996` moves it to `accessibleDescription`, which sighted users never see. The owner's rule is that nothing is removed.
- Fix: make the tooltip the full model name, a line break, then the learning count.

**10. Nits.**
- `hologram_qt.py:112`: `L.setdefault('scan', scan_tile())` builds a new 1×3 image every frame, because the argument is evaluated before `setdefault`. Build it once at module level.
- Stale words:
  - `README.md:11` and `docs/DAILY_GUIDE.md:56` still say the hand words sit "under her face".
  - DELETE's rows say "moved <when>" (`files_qt.py:510`); "deleted <when>" would match the other DELETE words.
- The new fonts load without a hash check (`shell2.py:59-62`). Special Elite was loaded the same way before, while Plex goes through `SOURCE.json`. Their SHA is recorded only in NOTICE.md and MANIFEST.

## What holds

**(1) The animation's timer**
- It stops on the Settings tab and restarts on Files. On Machine it runs, because she stands there too.
- When the tree needs the room, she is hidden and the timer stops within the same signal (`rows_scroll_at_once {'hidden': True, 'running': False}`). She comes back when the rows collapse.
- The timer stops when the window is minimised, when it is hidden, and when the app is inactive (signal emitted); it restarts each time.
- Reduce motion through the real `reading_preferences.apply(persist=True)` stops it, and turning Reduce motion off restarts it.
- On the Clean desk she is hidden, the timer stops and `layers is None`. On the ASCII desk there is no timer. In Graphite there is no stage, stage widget or masthead.
- Repaints: a 3 s census of paint events overlapping her rect, for widgets other than her, is empty both with her running and with her clock off. Window paints were 74 against 69, and her own paints 38. Each tick repaints only her.
- No leak: over 4 rounds of 15 cycles of tab changes (Settings, Files, Machine) and desk changes (Clean, ASCII, Illustrated), the object count stayed at 2520 after the first round, which builds Settings lazily. There were 47 QTimers throughout. Her layers stay at most 2 sizes, with 1 cutout, 6 noise tiles and 2 watchers. RSS rose about 11 MB after 20 resizes, bounded by the 2-size limit. A change of appearance needs a relaunch (`boss_qt.py:422`), so nothing can leak across appearances within one process.

**(2) Art verification**
- In a damaged copy of the pack (`tree_bad`):
  - one flipped byte in `hologram.webp` gives `hologram None`;
  - a damaged `kp_emblem_38.png` falls back to the monogram at `[36,36]`;
  - a deleted `kp_tile.png` gives `icon_source 'graphite'`;
  - a damaged `wordmark.webp` gives a null image.
- No traceback in any of these. Every entry in `MARKS` verifies in the intact tree.
- Both build tools are byte-reproducible: re-running `derive_typewriter.py` and `cut_kp_emblem.py` gives SHA-256 values identical to the committed fonts and the six kp files.

**(3) Fonts**
- Kasandra Elite Mono has hhea/typo 2099/−563, USE_TYPO_METRICS set, and `gasp {65535: 10}`. It has no glyph programs and no fpgm, prep or cvt.
- ←, ─, ┌, ▾, ✓ and ZWSP are missing from both faces and are substituted. `test_typewriter_faces` passes (OK 11).
- Apart from finding 1 and the intended DELETE change, Graphite's measured layout is unchanged.

**(4) DELETE**
- An AST scan of `workbench/*.py`, with docstrings and `version.py` excluded, finds no on-screen "Trash" except the search alias `ALSO = {'trash': ('Trash',)}` (`shell2.py:1214`).
- Internal names are unchanged: `files.trash`, `hand.trash`, the `'trash'` row key, `edit:delete`, `desk_acts.MENU_ROWS` (untouched), `.trash`, `files_trash`, the `trashed` field and the stacy_hand `trash.*` pattern.
- The words agree across menus, acts, cards, help and docs.
- The added lines introduce no "staC", printed key or "Programs". The only match is a docs row that already existed in the base.

**(5) The release**
- `release_integrity.verify` gives VERIFIED: 1310 files, against 1290 in the base, matching the 20 new files.
- `seed_status` gives `VERIFIED_SOURCE_BINDINGS`.
- FOCUSED_MODULES includes the 4 new modules, and `test_release_check` passes (OK 22).
- I ran the whole focused list (63 modules) on both trees; the builder's report covers only 16 of them.
  - Every module's result in the tree is identical to the base.
  - The failure names are the same as in the base: test_graphite 3, test_system_menu 2, test_desk 6, test_model_settings 4 failures and 1 error, test_paper 4. The last two were not in the builder's report.
  - New: test_delete_words OK 6, test_typewriter_faces OK 11, test_hologram OK 18, test_kasandra_column OK 9.