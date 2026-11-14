I reviewed the look and found two real defects and two smaller ones. The worst is green, and it can't show up in any screen grab: when the mouse points at a menu row, the cyan pointer's glow turns the burnt-yellow bar lime around it. Graphite is unchanged at both sizes.

**How I checked.** I took my own frames from a copy of `b3e1985`, in Kasandra and Graphite at 1366x768 and 1920x1200. I compared Graphite against `bbf033b` at both sizes, and Kasandra against `bbf033b` at 1366x768 as a baseline. All frames are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/yellow_review_look/frames/`. The scripts are in `.../yellow_review_look/code/` (`look.py`, `look2.py`, `look3.py`, `take.sh`, `diff.py`, `green.py`, `contrast.py`, `pointer_on_bar.py`, `neon_check.py`). The disk got down to 57 MB free while I worked, so I deleted my copy of the base tree. My working copy at `.../yellow_review_look/tree` (154 MB) is still there and can be removed.

## Findings, most severe first

**1. High: Kasandra's pointer glow turns green on the burnt-yellow bar.**
- **Where:** `workbench/pointer.py:83-87`. The pointer and its 3-ring glow are drawn in `t.READY`, which is cyan `#83eaff` in Kasandra, at up to 0.38 strength each.
- **Why it matters:** the window system lays a cursor over the screen semi-transparently. The bar is always the row under the pointer, so on every mouse hover the cyan glow sits over `#e2a72e`. That breaks the "never translucent cyan with yellow" rule.
- **Why the builder's "0 green" missed it:** a window grab never contains the cursor.
- **Measured:** I laid `pointer.drawn()` over each fill as the window system would.
  - Arrow on the bar: 27 green pixels (hue 70-170, saturation ≥ 0.25), the most saturated `(185,197,135)` at hue 72.
  - Hand on the bar: 39 green pixels.
  - Halo hue histogram on the bar: 72 px at 50-60° (lemon) and 47 px at 70-130° (lime to green).
  - On `#5a3f0c`, `GROUND` and `TEAL_SOFT`: 0 green. With the glow off: 0 green.
- **Evidence:** `.../yellow_review_look/ptr/pointer_arrow_on_BAR_x8.png`, made by `code/pointer_on_bar.py`.
- **Fix:** in Kasandra only, draw the pointer's glow in a colour that stays warm or neutral over `#e2a72e`, such as `VIOLET_PALE #d2c4f5` or `TEXT #e3e3ff`, or drop the glow and keep the cyan body and dark edge. Re-run `pointer_on_bar.py` and require 0 pixels at hue 70-170 with saturation ≥ 0.25 on `BAR`, `BAR_EDGE` and `AMBER_SOFT`. Graphite stays as it is.

**2. Medium: the yellow "light" comes out grey and muddy.**
- **Where:**
  - The writing line's lit edge: `typebar_qt.py:627-631`.
  - The Field's keyboard halo: `field_qt.py:1405`.
  - The Field's word glow: `field_qt.py:1419`.
  - The chosen face's rule light: `field_qt.py:1199`.
- **Why:** these are all drawn by adding the yellow as light (`lays_light`). Adding yellow light to her blue grounds and cyan glows makes grey, not warm light. The yellow edges themselves are crisp, so the highlight is still clear; only the glow around them is dull.
- **Measured, writing line focused (`R_09_results`, 1366):**
  - Above the line: `(78,96,109)` to `(92,103,106)`, saturation 0.07-0.17. Base was `(63,103,129)`, saturation 0.35.
  - Below the line: `(70,59,61)`, `(72,62,62)`, saturation 0.07-0.09, a grey-mauve.
- **Measured, the Field's selected sheet (`R_13_field`):**
  - Outer halo rings: `(58,49,52)`, saturation 0.08. Base was `(39,61,85)`, saturation 0.37.
  - Inner ring: `(98,82,62)`, saturation 0.23.
- **Evidence:** `.../yellow_review_look/line_focus_cmp.png` and `field_sheet_cmp.png`, each comparing base Kasandra, the build and Graphite.
- **Fix:** keep the yellow off the cyan in a different way, so it can be laid normally where it stays warm. On her indigo ground, half-strength yellow stays at hue 28-37.
  - For the line: don't draw the band's cyan glow inside the line's columns while it has the keyboard (paint `GROUND` there), then lay the yellow normally.
  - For the Field: draw the wires after the halo, or add a deeper orange as light.
  - Acceptance: ring pixels at saturation ≥ 0.25 and hue 25-45, and still 0 green.

**3. Low: at the default Neon glow, the logo's ghosts double its thin strokes.**
- **Where:** `kp_logo.py:29-33`. The ghosts sit 1.5 px to each side at 0.48 strength, plus a strong close glow at 0.84.
- **Measured:** the logo's mean edge sharpness drops from 9.60 with no glow to 7.92 at Neon (-18%). At Soft it is 8.80, at Bright 8.27. The ostrich's legs pick up a magenta double, and the glow hazes the gap between them.
- **Evidence:** `.../yellow_review_look/logo_x6_grid.png` (glow 0, 1, 1.9, 3) and `sheet_logo_k1366.png`. It still reads well at 1x (`cmp_mock.png`, next to the owner's mock).
- **Fix:** settle the ghosts at 1.0 px and cap their strength near 0.3 at Neon. Keep the full spread for the catch.

**4. Low, a spec choice worth telling the owner:** the 2 px menu-row edge `#ffd27a` on `#e2a72e` is only 1.51:1, so it reads as a faint strip rather than an edge (`R_02x3_menu_Work_kasandra_1366x768.png`). A darker edge such as `#a8741a` would be visible. Separately, on menu rows and writing-line result rows (`QMenu`, `OneBoxList`), the lit row's words still move 2 px right, as before this pass in both appearances.

**Already there before this pass, not part of it:** the writing line's results caption prints "/ an operation", a typed character on screen (`shell2.py:1040`).

## What holds

- **Menu bar:** every lit row is a solid `#e2a72e` bar with ink measured at 7.79:1, in all frames at both sizes. That covers the head menus, a submenu, the right-click, its line panel, Apps, and the writing line's results, including the ask rows that have their own cyan ink. Glyphs and check marks are dark on it. The submenu arrow measures 3.64:1, and "needs setup" on a lit Apps row is in the quiet dark ink (4.92:1).
- **Highlights:** fill, edge and words (`#5a3f0c`, `#e2a72e`, `#ffd27a`) measure 6.86:1 everywhere. That covers the tree, the Files list, the centre and left tabs, a focused head word, the Machine tree, text selection in the line, and the find field's 2 px edge.
- **Hue:** 1,167,292 burnt-yellow pixels sit between hue 34.1° and 43.2° (99.8%), max 55.6°.
- **No green in the grabs:** 0 green pixels in every Kasandra frame at both sizes, even with a looser threshold (hue 60-175, saturation ≥ 0.12). That includes the menu catch held at 0.08, 0.1, 0.25, 0.3, 0.5 and 0.7, and the logo's catch, hover and focus. The same check finds 145,950 green pixels in Graphite, so it does detect green. Where the catch's violet band crosses the bar it washes it to `(217,178,137)`, hue 31, for its 150 ms.
- **The logo:**
  - The asset is exactly the source's pixels with alpha ≥ 200 (0 pixels differ), trimmed to x 102-1502, y 80-917 (1401x838). Both SHA-256 values match the README.
  - It is 74x44 in a 92x60 button and reads at both sizes.
  - There is no glow at 0 or on the Clean desk.
  - It catches when Apps is clicked (surge 0.33 after 20 ms) and not with Reduce motion.
  - Its name is "Apps" and its tip is unchanged ("Installed apps and capabilities").
  - Keyboard focus shows as a yellow edge with no fill. Leaving out the fill was right: adding the cyan glow onto `#5a3f0c` would come out greenish grey.
- **Graphite is exactly unchanged:** every crop differs from base by 0 pixels at both sizes (menus, submenu, catch, right-click, panel, list row, tabs, Apps, logo region, results, line, find, left trees). Whole frames differ only in live places: the equalizer, the meters, the tree's breathing glow (at most 33 levels summed over the three colour channels), and one "This: Files / Graphite" state line.
- **Retired marks:** no `kp_monogram`, `kp_emblem` or `kp_tile` files remain. The old names appear only in `version.py`'s history and older release notes.