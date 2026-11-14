Every finding from both reviews is fixed in commit `bbf033b` except one, and one more is fixed only partly:
- **Not done (A15):** I judged against widening her column, with reasons below.
- **Partly done (A9):** the "1 waiting for you" count stays with its words only where that doesn't add a line.

All 16 modules match or improve on their results before the change. The seed and release check out.

**Where it is**
- Worktree: `/home/user/Struthio/.claude/worktrees/wf_972bbb8b-a77-6`
- Branch `worktree-wf_972bbb8b-a77-6`, commit `bbf033b` on top of `3af59a1`. The tree is clean.
- Seed state `VERIFIED_SOURCE_BINDINGS`, release integrity `VERIFIED`. Manifest, registry and seed are rebuilt and committed. The registry file came out unchanged.
- Mirror: all 37 changed files are under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_mirror/`. They match the worktree for every file changed since `d1df337`.

**Look and readability findings (A)**
1. **Documents page:** `document_qt.fonts_of` now uses the faces in force. `glyph_set.letters` draws the toolbar letters in her words face and `{}` in her mono face. Measured: Kasandra Elite and Kasandra Elite Mono, frame F18.
2. **Tooltips:** `reading_preferences.tip_face` sets them to her words face at 15 px. Measured: `QTipLabel` in Kasandra Elite 15, frame F19. Graphite keeps the application's face.
3. **1 against l:** `tools/derive_typewriter.py` now gives the one a long sloped flag on its full foot. The l loses its foot and ends in a tail curving right.
   - My measure is the share of grey the two glyphs don't share, 0 meaning identical. Kasandra Elite Mono went from 0.22–0.24 to 0.33–0.34 at 13, 15 and 18 px; Plex Mono is 0.31–0.33.
   - Underlined, it went from 0.15–0.18 to 0.23–0.26; Plex Mono is 0.22–0.25. Kasandra Elite went from 0.47–0.53 to 0.54–0.59.
   - The faces rebuild byte for byte; their new hashes are in NOTICE.md. A new test checks every size, underlined too, against Plex Mono.
4. **Names cut mid-word:** `shell2.break_long` adds break points only to a run that doesn't fit the line as drawn, preferring `_ . / - , :`. `kasandra_column.Folding` sets them again at each label's real width and refolds the thread. "07_Bench_Readings.pdf" and "07_Rail_Limits_Rev_B.pdf" now stay whole (F11).
5. **Markdown view:**
   - `markdown_view.css` builds its styles from the faces in force, and `dress_code` puts code in her mono face at her code size. The root cause was `reading_preferences.browser_spacing`, which set the prose face without going through the owner's choice.
   - In the shown note the words are Kasandra Elite and the code Kasandra Elite Mono.
   - `UniversalViewerTab.fold_actions` moves actions that don't fit behind More…. Panes stay 354 wide and no button is cut (F20).
6. **Column ground:** `pane_qt.PaneBody.paintEvent` paints her terminal ground over the whole right pane, and the conversation area is now clear. Five sample points around the column are #11132c.
7. **Static:** `hologram.noise_key` redraws the static every third frame from six patterns. It is held still at 0.10 for "waits for you" and "stopped"; the flicker changes under 2% a frame.
   - Motion with the clock held, per frame on a 0–255 scale: idle 3.66, working 7.65, waiting 2.14, done 3.64, stopped 1.12, still 0. The largest brightness swing is 1.19%.
   - Live, per frame that changed: idle 4.08, working 7.68, waiting 2.41, done 3.86, stopped 5.16. The review's live numbers were 6.4, 7.4, 6.3, 6.5 and 5.0.
   - "Stopped" changes only when its scan lines step, about three times a second, so few frames change and each counts in full.
8. **Ring near DELETE:** `hologram.ROOM` is 24 on the stage and stays 16 in the corner. The ring now ends 11 px above DELETE (F01b).
9. **"1 waiting for you" (partly done):** `shell2.together` keeps the count with its words wherever that costs no line, which Graphite's frame F15 shows.
   - In her 298 px Now line, keeping them together pushed "activity" onto a third line. That shrank her thread by 18 px, and the 1366 scroll overflow count rose from 18 to 26.
   - So there the line still breaks after the "1". The new sloped one reads as a one even underlined.
10. **Emblem contrast:** the Apps button is lifted 4 px, and `tools/cut_kp_emblem.py` draws the small cut's trace in a lighter tint of the same violet, #9466ff. The lift alone took the worst contrast from 2.12:1 to 2.64:1 (measured on the frames).
    - The lighter tint raises it to 3.99:1 or more against the band; that figure is calculated and pinned by a test, not read off a frame.
    - Only `kp_emblem_small` and `kp_emblem_38` changed; the master, 2x and tiles rebuild byte for byte. New hashes are in MARKS and the README.
11. **REV A / REV B afterimage:** `field_qt._revisions` gives a changed row its own line for the afterimage, above a pink edge that now closes round the current value only. This applies in both appearances (F22, F22b).
12. **Then panel:** `context_menu.LinePanel.top_widgets` and `preview_text` fix this. The real cause was the main window's style sheet reaching the panel, so it counted letters in another face.
    - The line and the preview are now held in her mono face at 14 px. Columns are sized by their own words.
    - The preview now reads "Rail voltage 12 V" and so on, with all three columns (F21).
13. **Terminal:** `console_qt` keeps the reading profile's spacing and prose face off the output. Box lines meet down and across (F13b).
14. **Font report:** `settings_qt.state_words` now reads "Effective: Kasandra Elite · Kasandra's face (the default)" (F23).
15. **Wider right column (not done):** both panes share one width under the owner's symmetry rule, and her own drag widens both. Her text grew from about 279 to 296 px and the fold behaves correctly. Making both panes about 420 px from 1600 wide upward is a one-line default change if she wants it.

**Code and cost findings (B)**
1. **Graphite tabs:** `pane_qt.tab_font` uses `DISPLAY`. Graphite's tabs are Plex Mono again, with `least` 61 and `need` 215.
2. **Owner's faces and sizes:** `reading_preferences.faces_in_force`, `shell2.held_face` / `hold_faces` and `Masthead.restyle`, called from `Shell2.restyle`.
   - Tested with DejaVu Serif and DejaVu Sans Mono at 18 pt: her name is DejaVu Serif, the model line and an existing line on a card are DejaVu Sans Mono at 19 px, and the state word is 18 px.
   - Going back to the defaults restores everything exactly.
3. **Cursor:** `Cursor.wake_or_sleep` and `tick`, also called from the hologram's clock. Measured: it runs while something waits, stops with Reduce motion (alpha 1.0), runs again when it is turned off, and stops when the app is inactive.
4. **Cost:**
   - Her figure with its static and fringe is composed once per pattern (`still_part`), and the scan lines are a 256 px wide tile. A one-pixel tile alone had cost 0.48 ms a frame.
   - Live paint at 297×404 measured 0.96–1.16 ms on average, with the 95th percentile at 1.22–2.19 ms.
   - Rendering into a premultiplied image takes 0.70 ms. The test now asserts under 1.5 ms, the plan's figure. It measures into that format because a plain ARGB32 image measures Qt's conversion.
   - Her share of one core, with her clock on and off in turn, over five runs: 0.97, 1.15, 2.20, 1.70 and 1.37% (median 1.37%). The container is noisy.
5. **Idle display:** `wake_or_sleep` now reads the `showing` property correctly, and `IdleDisplay._hologram` wakes or sleeps her from its preview and dismiss. Measured: stopped under the idle display, running after.
6. **Undecodable picture:** `kasandra_art._cut` remembers a failed decode (read once, tested), and `hologram_qt.install` returns None for a picture that won't decode.
7. **Touch while asleep:** `HologramStage.touch` ignores touches while her timer is off. Measured: no tear.
8. **"Quiet" above "1 waiting":** `kasandra_art.column_state` turns quiet into "waits for you" while the Agenda has something waiting. The stills keep using the old state. Note that in the demo workspace she now shows pink "waits for you" while its one Agenda item waits.
9. **Model tooltip:** it is now the full name, a line break, then "Learning from N outcomes you marked or ran".
10. **Nits:**
    - The scan tile is built once, at module level.
    - README and the daily guide say where her hand is in Kasandra.
    - DELETE's rows say "deleted".
    - The typewriter faces load only with their recorded hashes (`shell2.TYPEWRITER`, tested against NOTICE.md).

**Tests, before (this round's run on `3af59a1`) → after**

| module | before | after |
|---|---|---|
| test_kasandra | OK 20 | OK 20 |
| test_faces_find_light | OK 34 | OK 34 |
| test_writing_line | OK 32 | OK 32 |
| test_launcher | OK 17 | OK 17 |
| test_stacy_hand | OK 19 | OK 19 |
| test_release_check | OK 22 | OK 22 |
| test_graphite | 3 failures | same 3 |
| test_system_menu | 2 failures | same 2 |
| test_desk | 6 failures | same 6 |
| test_delete_words | OK 6 | OK 6 |
| test_typewriter_faces | OK 11 | OK 13 |
| test_hologram | OK 18 | OK 23 |
| test_kasandra_column | OK 9 | OK 18 |
| test_desk_scenes | OK 5 | OK 5 |
| test_context_menu | OK 44 | OK 44 |
| test_desk_acts | OK 28 | OK 28 |

The failing tests in the three known modules have the same names as before. One `test_context_menu` assertion was rewritten: it pinned the exact style sheet of the panel's line, and now checks the line's colours plus its mono face. The new checks run through a `review` case in `tests_integrated/kasandra_window_probe.py`.

**Scroll census:** 2 overflows at 1920×1200, as before, and 18 at 1366×768, as in the review. The lists are `scroll_census_1920x1200.txt` and `scroll_census_1366x768.txt` in the frames folder.

**Frames** (in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_build/frames/`; the first pass's frames are kept in `.../look_build/frames_first_pass/`)
- `F01_left_files_1920.png`: she stands on the stage, figure (36,690,281,380). `F01b_delete_ring_x4_1920.png` and `F01b_delete_ring_x4_1366.png` show the ring clear of DELETE.
- `F02_left_files_1366.png`: the corner stance; `F03_left_machine_1366.png`: on the stage under Machine.
- `F04_left_settings_1920.png`, `F04_left_settings_1366.png`: no hologram on Settings.
- `F05_left_files_open_1920.png`: all rows open, she moves to the corner. `F05_left_files_open_1366.png`: the tree scrolls, she is hidden.
- `F06_clean_1920.png`, `F06b_ascii_1920.png`: the Clean desk, and her figure in characters on the ASCII desk.
- `F07_still_a.png`, `F07_still_b.png`: Reduce motion, identical one second apart.
- `F08_idle_strip_24.png` and `F08_motion.txt`: the frame strip, plus held-clock and live motion.
- `F09_states_5.png`: the five states; her base and cursor share each colour.
- `F10_powerup_9.png`: the power-up.
- `F11_right_home_1920.png`, `F11_right_home_1366.png`, `F11_right_1920.png`, `F11_right_1366.png`, `F11_window_1920.png`, `F11_window_1366.png`: her column with ground edge to edge, names whole, and the Now line.
- `F12_head_apps_x3.png`, `F12b_head_apps_x4_1366.png`: the lifted emblem with the lighter trace.
- `F13_terminal.png`, `F13b_terminal_real_x2.png`: the real Terminal output, with `ls -l` columns aligned and box lines meeting. The output is a fixed sample; no shell was run.
- `F14_glyphs.png`: l, 1, 0 and O at 13–18 px, including "A1 Al Nov12".
- `F15_graphite_1366.png`, `F15b_graphite_tabs_x2.png`: Graphite, with Plex Mono tabs and "1 waiting" kept together.
- `F16_cpu.txt`: the processor measurements.
- `F17_window_icon.png`: the window icon at its sizes.
- `F18_document_1366.png`: the Documents page in her faces.
- `F19_tooltip_delete_x2.png`: a tooltip in Kasandra Elite. This one came from a separate probe on the same tree, because the frames run didn't catch the tooltip window.
- `F20_md_viewer_1366.png`: a Markdown note in her faces; Ask about this plus More…, panes still 354.
- `F21_then_panel_1366.png`: the full preview table.
- `F22_rev_cut_1366.png`, `F22b_rev_cut_rows_x2_1366.png`, `F22_rev_cut_graphite.png`, `F22b_rev_cut_rows_x2_graphite.png`: the afterimage above the edge.
- `F23_settings_font_1366.png`: "Kasandra's face (the default)".
- `frames_wide.json`, `frames_small.json`, `frames_graphite.json`: the measurements.

**Still not done, or different from what was asked**
- A15 (wider column) and the A9 limit, as above.
- The Then panel's line now shows in her mono face at 14 px in both appearances. Before, the window's style sheet had put it in the words face at reading size.
- The B, I and U toolbar letters use synthetic bold and italic, because the typewriter face has one weight.
- The "Clean glow" still never happens: no glow setting reaches 0.
- Not touched: the version line, the release notes and `portrait.webp`.