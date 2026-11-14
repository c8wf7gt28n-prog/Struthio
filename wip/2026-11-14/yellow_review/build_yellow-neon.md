I built both directions and committed them in my worktree. Graphite's colours are unchanged, and no frame of Kasandra has a green pixel.

**Worktree** `/home/user/Struthio/.claude/worktrees/wf_50cf7120-e40-1`, branch `worktree-wf_50cf7120-e40-1`, commit `b3e19852ac384d54f2b678063112ce97aa100b02`, on top of base `bbf033b`. Nothing was pushed, and `version.py` and the release notes were not touched.

**After the pass:** the manifest was rebuilt, the registry recorded (`docs/GRAPHITE_0.1_REGISTRY.json` came out byte-identical), and the manifest rebuilt again. `seed_status` reads `VERIFIED_SOURCE_BINDINGS` and `release_integrity.verify` reads `VERIFIED`. Every changed or added file is mirrored to `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_mirror/` (48 files, plus 9 `<path>.DELETED` markers).

## ONE: burnt yellow (Kasandra only)

**Tokens.** In Kasandra, `AMBER` and `AMBER_SOFT` are now `#5a3f0c`, `AMBER_EDGE` is `#e2a72e` and `AMBER_TEXT` is `#ffd27a`. I added these names to both palettes; in Graphite each one equals the colour that place already drew:
- `BAR` `#e2a72e`, `ON_BAR` `#171b3c` and `BAR_EDGE` `#ffd27a`: the solid menu row.
- `ON_BAR_QUIET` `#4a3d2a` (4.92:1 on the bar): a row that says why it can't act.
- `ON_AMBER` `#ffd27a`: the words on a highlight.
- `CUE`, `CUE_EDGE`, `CUE_TEXT`: Graphite's amber exactly, and her old cyan (`#1d3d63`, `#83eaff`, `#b9f4ff`) in Kasandra.

`BAND_MARK` (the keyboard's mark on a band word or tab) is now `#e2a72e` in Kasandra, and `BAND_PENCIL` (the chosen tab) is `#ffd27a`.

**Menus.** The row you are on is the solid bar with a 2 px edge, and its glyph is drawn in the bar's dark ink with no glow. This covers the menus across the head and those dropped from them, the right-click and its line panel, Apps, the System menu, the chain menu, the sheet's row menu, and the writing line's results. The pieces are `programs_qt.paint_bar`, `ContextRow`, the Active and Selected states in `tool_faces.icon`, and `MENU_BAR_CSS` and `HIGHLIGHTS` in `boss_theme.py`.

**Never green.** The new `boss_theme.lays_light()` adds yellow as light (Screen) instead of mixing it. It is used for:
- the Field's keyboard halo and lit words, and the chosen face's rule light;
- the writing line's lit edge;
- the menu catch's cyan ghost where it crosses the bar.

**Where I bent the spec.** The Apps logo shows focus with the burnt-yellow edge only, with no fill under it. The logo's cyan glow laid over a yellow fill would turn green, which the "never green" rule forbids.

**Each AMBER use, and what it became.** About 199 lines; I went through every one.

*Stays a highlight (burnt yellow in Kasandra, unchanged in Graphite):*
- `boss_theme` chrome sheet: focus borders on fields and text boxes, the selected menu row, checked buttons and selected tabs, tool buttons pressed, focused and checked, tree and list selection edges, the address line's selection, focus on the head's words and on Apps, the capture box's focus, and the `FOCUS` role.
- `theme2`: the palette's Highlight, menu row fill, checked filter buttons, every selection colour, field and text focus, tree and list rows, selected tabs, checked boxes and radios, the writing line's focus and its results row.
- `shell2`: combo box focus; button focus underline (yellow in Kasandra, as before in Graphite); the Timeline's selected words.
- `field_qt`: the reading page's halo and frame while it has the keyboard; the chosen face (bloom, words, lit rule, rule); the selected sheet with the keyboard (halo, edge, corner ticks, its name's bloom, near and far).
- `meter_cards` focus; `centre_find`'s found mark; `centre_bar` focus edges.
- `sheet_workbench`: selection, checked row header, selected rows, focus edges, marked rows, the row menu's selected row.
- `chain_menu` selected row.
- `typebar`: the writing line's focus edge and lit edge.
- `document_qt`: the selected document, and the flash wash where something lands.
- `investigations`: the focused claim, Continue's focus edge, the selected journal row.
- `desktop_header`: the AI on/off switch when it is checked.
- `datasheet`: the evidence highlight, its link line, the selected evidence label, the table selection.
- `program_rooms`: selection, focus edges, button focus.
- `tool_faces`: pressed or chosen, and the keyboard edge.
- The tree and tab highlights in `pane_qt`.

*Moved to `CUE` (cyan in Kasandra exactly as before, Graphite's amber unchanged):*
- `field_qt`:
  - **Words:** error and problem words, page headings, key rows, bullets, "more", the question/condition kind ink, the what-if fact, stale link words, foot notes, the foot's name tag, the go / WHAT IF / DO lines, and the DO box's DO, asks and go words.
  - **Edges, marks and light:** the DO box's edge, the floor light, the FIELD label, the census, the "lately" fold, the what-if edge and halo.
- `equalizer`: near-limit bar tops and the busy row.
- `sheet_workbench`: hover edge (split from focus), the run-chain primary button, the dashed rail, the mixed total, a stale source, the current step.
- `shell2`: count badge, the hidden pencil tile, the model-stopped dot, ask and search result words, the step bar, the pane title's underline.
- `chain_menu` frame; `document_qt` report hint.
- `investigations`: heading rule, priority section, Continue (primary), WAITING.
- `desktop_header` slider; all of `console`'s words, echo and approval wash; `compare`'s added wash and edge (3 places).
- `datasheet`: panel rule, title, Commit; `desk_qt.paint_band`: the bands' rule and its light.
- `program_rooms`: header rule, status, hover (split from focus), primary button.
- `work_trail`: rule, title, state words; `pulse` chart; the `[>_]` in `boss_qt`; `centre_bar`'s no-match count; drawn icons in `thumbnails` and `finder`; every `idle_display_art` label; `chain_workbench`'s rail and tray rule.
- Writing passages (`theme2`, `explore`); the progress bar fill; the address line's words; the chain tray's rule.

*Unused, left alone:* the `trash_can_qt` import, and comments in `graphite_brand` and `cabinet_qt`.

## TWO: the neon kp logo

**The asset.** `branding/kasandra/kp_neon.png` is the clean drawing: every pixel of alpha 200 or more exactly as given, everything else cleared, trimmed to x 102–1502, y 80–917 (1401 × 838, 371,785 bytes). It is cut by `tools/cut_kp_neon.py`, which refuses any file whose SHA-256 is wrong.
- Source SHA-256: `70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e` (recorded, not stored in the repo).
- Clean drawing SHA-256: `f3c6e5fb5cd0f2d61019187bae0d70771378fba5a6c7da27dd8d15d486fd2cc0`, recorded in `branding/kasandra/README.md` and in `kasandra_art.MARKS`.

**The button.** `workbench/kp_logo.py` (`AppsButton`) is Apps in Kasandra:
- The logo is 74 × 44 inside a 92 × 60 button in the head's upper right. Its name is "Apps" and its tip is unchanged ("Installed apps and capabilities").
- The neon is drawn as light: a wide and a close glow in each part's own colour, a cyan ghost to the left and a magenta ghost to the right. Its strength follows the Glow dial (0.2 / 0.28 / 0.16 per step), with none on the Clean desk or at 0.
- It catches when the Apps list opens (`menu_catch.CATCH_MS`) and stays still with Reduce motion.
- If the file's bytes don't match, the button falls back to the words "[#] Apps ▾". Graphite keeps "[#] Apps ▾".

**Retired:**
- `kp_monogram.png`, `kp_emblem.png`, `kp_emblem_38.png`, `kp_emblem_76.png`, `kp_emblem_small.png`, `kp_emblem_source.png`, `kp_tile.png`, `kp_tile_letters.png`;
- `tools/cut_kp_emblem.py`, and their README lines, `MARKS` hashes and `MANIFEST` entries;
- Kasandra's window icon (`kasandra_tiles` and `window_icon_source`). The window icon is Graphite's sharpened point in both appearances.

The old names remain only in history: `version.py`'s lineage, earlier release notes, and the seed built from them.

**Docs.** I also updated two docs beyond the code: `RECORD_OF_DIRECTIONS.md` (a new bullet for this pass, and the stale monogram line) and the Kasandra paragraph in `docs/DAILY_GUIDE.md`.

## Tests (one module at a time, before → after)

| Module | Before | After |
|---|---|---|
| test_kasandra | 20 OK | 20 OK |
| test_kasandra_highlight (new, added to `FOCUSED_MODULES`) | — | 10 OK |
| test_hologram | 23 OK | 23 OK |
| test_kasandra_column | 18 OK | 18 OK (ported to the neon logo) |
| test_typewriter_faces | 13 OK | 13 OK |
| test_delete_words | 6 OK | 6 OK |
| test_faces_find_light | 34 OK | 34 OK |
| test_context_menu | 44 OK | 44 OK |
| test_launcher | 17 OK | 17 OK |
| test_writing_line | 32 OK | 32 OK |
| test_release_check | 22 OK | 22 OK |
| test_graphite | 3 known failures | the same 3 |
| test_system_menu | 2 known failures | the same 2 |
| test_desk | 6 known failures | the same 6 |

I also ran six modules that touch changed code, after only: test_documents (13), test_frame (11), test_model_turn (28), test_related (11), test_desk_scenes (5) and test_desk_acts (28). All passed.

The first after-run broke three modules with "No space left on device": the shared disk filled up while my frame copies were being written. I freed my own scratch copies and run folders and reran everything; the table shows the clean rerun. The disk still has under 1 GB free, shared with another session.

`rsync` isn't installed, so the frame copy was made with `tar --exclude=./.git`.

## Frames

All in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_build/frames/`. Each name exists for `kasandra_1920x1200`, `kasandra_1366x768`, `graphite_1920x1200` and `graphite_1366x768`, for example `Y_02_head_menu_kasandra_1920x1200.png`.
- `Y_01_head_tree_tabs_*`: the Files tree with a selected row, the chosen pane tab, the head with the logo.
- `Y_01b_head_right_x3_*`: the head's right end zoomed ×3. `Y_01c_head_right_*`: the head's right end at 1×.
- `Y_02_head_menu_*`: the Rules menu, its row as the bar.
- `Y_03_head_menu_dropped_*`: Desk artwork ▸ with its submenu, both rows lit, and a checked item.
- `Y_04_head_menu_catch_*`: the menu catch held at 0.3, its ghost crossing the bar.
- `Y_05_right_click_*` and `Y_06_right_click_line_panel_*`: the right-click on a file, then its line panel open.
- `Y_07_list_selection_tab_*`: the Files list's selected row and a selected centre tab.
- `Y_08_apps_open_*`: Apps open, its first row lit.
- `Y_09_writing_line_results_*`: the results bar, with the line focused.
- `Y_10_focused_field_*` and `Y_10b_focused_field_x2_*`: the find line holding the keyboard.

The base's Graphite frames are in `.../yellow_build/frames_base/`.

## Measured

**Contrast in the frames** (fill → ink):
- Menu bar `#e2a72e` → `#171b3c`: **7.79:1**. Apps and results rows measure 7.31–7.72, lower only because of text antialiasing.
- Edge and words `#5a3f0c` → `#ffd27a`: **6.86:1** (6.76–6.86 measured).
- The focus edge `#e2a72e` on her ground: 7.79 on `#171b3c`, 8.5 on `#11132c`.
- `ON_BAR_QUIET` on the bar: 4.92:1.

**Hue.** Every burnt-yellow pixel cluster in all 26 Kasandra frames falls between **28.1° and 40.8°**. Green pixels (70–170°, saturation ≥ 0.25) total **0** across all Kasandra frames, including within 4 px of every highlight and in the held catch frame. The tests also check why mixing is ruled out: yellow mixed 30–50 % over `#83eaff` or `#1d3d63` lands at 70–170° (green); added as light it never does.

**Graphite unchanged:**
- Every palette value is the same, and every sheet rule matches the base, compared rule by rule.
- Against the base frames, every popup, tab, the results list, the Apps button and the find field differ by 0 pixels.
- The pixels that do differ are all live: the tree's breathing glow, the equalizer, the meter readings, a timestamp and the cursor.

The comparison files are `compare_graphite_*.json` and `measure_frames.json` in the frames folder.