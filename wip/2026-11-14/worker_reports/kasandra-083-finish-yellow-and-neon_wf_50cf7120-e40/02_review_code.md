I found no blocking defects. Graphite is unchanged in effect, the logo asset and its verification hold, integrity and seed both verify, and all 20 test modules match the builder's table. I found three real but small gaps in the Kasandra highlight, plus a few minor items. I fixed nothing.

## Findings, most severe first

**1. Medium: chain-menu pictures disappear on the yellow menu bar.**
- `workbench/chain_icons.py:7` draws its pictures in pink `#cba5a4` or grey `#504d46`. `icon()` at lines 13-15 makes them from one pixmap, so the lit row shows the same pixmap.
- They are put on menus at `chain_menu.py:151`, `chain_menu.py:484` and `pulse_qt.py:191`. Those menus now take `MENU_BAR_CSS`, so the lit row is `#e2a72e`.
- Contrast of the pink "ending" pictures (then, keep, copy, shell, console, agenda, watch, sheetsave) on the bar is **1.04:1**; on her old row colour `#1d3d63` it was 4.98:1. Grey is 3.93:1.
- This breaks "its glyph drawn so it reads on the bar". `tool_faces.icon` handles this case; `chain_icons` was missed.
- Fix: in Kasandra, have `chain_icons.icon()` also add `QIcon.Active` and `QIcon.Selected` pixmaps drawn in `ON_BAR`, as `tool_faces.py:226-227` does.

**2. Medium-low: lists with their own stylesheet still show the old selection.**
- The builder only checked lines that use AMBER names, and these lists use ERASER or RAISED for their selected row.
- Rendered in Kasandra with the real sheets: the selected row has a yellow edge `#e2a72e`, but the fill is `#2e2a5c` (process list) or `#292d56` (Log) instead of `#5a3f0c`, and the words are TEXT, not `#ffd27a`.
- Script: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_code/scripts/own_sheet_rows.py`
- Places:
  - `desktop_header_qt.py:240-241`: the System menu's process list (`NicePopup`), which is part of a menu.
  - `log_qt.py:402`: the Log lists.
  - `explore_qt.py:245`: `ExploreResults` (`#f3e3e2`, which recolours to ERASER).
  - `cabinet_qt.py:163`: `LogicalCabinet`.
  - `document_qt.py:33`: `DocumentList` keeps an `ERASER_DEEP` fill under yellow words.
  - `desktop_header_qt.py:190-191`: the `SlateSwitch` checked state is an `AMBER` fill with TEXT words and no edge.
- Fix: in Kasandra, use `background:AMBER_SOFT; color:AMBER_TEXT` in those selected or checked rules, or leave the rule out in Kasandra so `HIGHLIGHTS` applies. Graphite stays as it is.

**3. Low: the PDF evidence highlight is a see-through yellow fill.**
- `datasheet_qt.py:49-50` fills `AMBER_EDGE` at alpha 50 over the PDF page with normal paint mode.
- This breaks "every highlight fill is opaque". Over cyan or blue ink in a PDF, about 20% yellow drifts toward green; on white paper it is harmless.
- Fix: in Kasandra, drop the fill and keep the opaque 2 px edge.

**4. Low: keyboard focus on the sheet's Run button is still cyan.**
- `sheet_workbench_qt.py:57` reads `RunWorksheetChain:hover, RunWorksheetChain:focus {background: CUE_TEXT}`, so in Kasandra focus is `#b9f4ff`, the same as hover.
- Fix: split it into `:focus {background:AMBER_TEXT; border-color:AMBER_EDGE}`. In Graphite those equal the CUE values, so Graphite is unchanged.

**5. Low: some colours turn yellow through the old-colour mapping and are not in the builder's list.**
- `boss_theme.LEGACY` maps `#d4b56a` to `AMBER_EDGE` and `#f8edc9` to `AMBER_SOFT`. The Graphite colours `#4b2a14`, `#ff9a36` and `#ffba72` now map to AMBER too, because AMBER comes first in the palette.
- Effect: the Log's pinned-line edge (`log_qt.py:409`) is now burnt yellow in Kasandra; it was cyan. That is acceptable, since pinned means chosen, but it should be on the decisions list.

**6. Low, efficiency: the full-size logo stays in memory.**
- `kp_logo.py:48` keeps the whole decoded 1401 × 838 image, about 4.7 MB, for a 74 × 44 button.
- Fix: keep one downscaled copy, for example 3× the largest size used, and drop the original.

**7. Low, wording: the Apps tip.**
- The direction says "its tip still 'Apps'". The accessible name is "Apps", but the tooltip is "Installed apps and capabilities" (`shell2.py:644`).
- If the owner meant the tooltip itself, set it to "Apps".

**8. Builder's disclosed deviation, which I agree with.** The Apps logo shows focus with the yellow edge only, no `#5a3f0c` fill. I computed the logo's cyan light added onto that fill: it lands at hue 60-156°, faint but greenish. Edge-only is the right call; the owner should be told.

**9. Before this pass.** "LAIN" appears in code comments (`boss_theme.py:28`, `82-83`) and "Serial Experiments Lain" in `branding/kasandra/README.md:29`. The pass re-wrapped the comment at line 28 and kept the word; nothing shows on screen. Neither the builder's frames nor the tests exercise the Field's selected sheet with the keyboard, which is where `_halo` and `_bloom` add yellow as light. The `Y_10` frames show the find field instead.

## What holds

- **AMBER decisions:** apart from items 1-5, every highlight versus not-a-highlight split in the diff is sensible. Hover stays cyan; focus, selection and checked are yellow.
- **Never green:**
  - The only see-through yellow drawn with normal paint is `field_qt.py:929` (90% alpha, stays warm), the document flash over her indigo page (warm), and item 3.
  - The menu catch's band is violet, which over the bar comes to about 27°, not green.
  - Screen-mode yellow over `#83eaff` or `#1d3d63` is never green (checked by `test_kasandra_highlight`).
- **Graphite identical:**
  - I imported 35 modules in Graphite from both the base and the new tree and compared every module-level stylesheet and colour.
  - The only differences are new token names, one comment in `theme2.QSS2`, and two rule splits with equal values (`program_rooms_qt` STYLE, `sheet_workbench_qt` SURFACE). `CHROME_OVERRIDES` is identical, and `HIGHLIGHTS`/`MENU_BAR_CSS` are empty in Graphite.
  - At runtime, `paint_bar`, `MenuRow`, `ContextRow` and `tool_faces` give Graphite the same values; `lays_light` does nothing there.
- **The logo asset:**
  - Re-cutting it from the owner's file (SHA `70efb677…`) gives `f3c6e5fb…` byte for byte.
  - Pixel check: 346,210 pixels kept exactly, 0 mismatched, every pixel under alpha 200 cleared, none of alpha 200 or more outside the trim.
  - Script: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_code/scripts/check_cut.py`
- **Verified before shown:** `kasandra_art.mark` hashes the file before `QImage` loads it. A changed or missing file gives a null image and the words "[#] Apps ▾", with no crash (the test probe passes `apps_words`).
- **The glow:**
  - It follows `glow()`: zero at level 0 and on the Clean desk, rising with the dial. The catch surges only when Apps opens, and it is still with Reduce motion.
  - No light falls outside the 92 × 60 button, so nothing gets clipped.
- **Paint cost of the Apps button:**

| Case | Time per paint |
|---|---|
| Logo with neon, 1×, Soft to Neon | 0.07 ms |
| Logo with neon, 2× pixel density | 0.45 ms |
| First paint (builds the cache) | 1.1-1.7 ms |
| Whole widget render | 0.145 ms |
| Plain tool button, for comparison | 0.013 ms |

  - Script: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_code/scripts/apps_paint.py`
- **Retired marks:** a grep of the whole tree finds kp_monogram, kp_emblem, kp_tile, monogram, cut_kp_emblem, kasandra_tiles and window_icon_source only in `version.py`'s history, `RELEASE_NOTES_0.8.0/0.8.2`, and the test's own list of retired names. `branding/kasandra` holds only `kp_neon.png` among the kp files. MANIFEST, the README and the notices files are clean.
- **Window icon:** `graphite_brand.window_icon()` uses the sharpened point in both appearances, and the test probe confirms `window_icon_graphite` in both.
- **Integrity:** `release_integrity.verify` reads VERIFIED (1305 files, no problems), `seed_status` reads VERIFIED_SOURCE_BINDINGS, and MANIFEST lists `kp_neon.png`, `cut_kp_neon.py`, `kp_logo.py` and the new test.
- **Tests,** rerun one module at a time in my copy, all matching the builder:
  - All pass: test_kasandra (20), test_kasandra_highlight (10), test_hologram (23), test_kasandra_column (18), test_typewriter_faces (13), test_delete_words (6), test_faces_find_light (34), test_context_menu (44), test_launcher (17), test_writing_line (32), test_release_check (22), test_documents (13), test_frame (11), test_model_turn (28), test_related (11), test_desk_scenes (5), test_desk_acts (28).
  - test_graphite (3), test_system_menu (2) and test_desk (6) fail exactly as on the base: the same tests, with the same assertion messages.

The disk is nearly full (about 130 MB free, shared with another session). My copy of the tree is `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_code/tree` (154 MB) and can be removed. Test logs are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_code/logs/`.