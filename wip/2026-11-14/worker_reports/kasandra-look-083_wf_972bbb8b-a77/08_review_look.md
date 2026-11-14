The look holds on most surfaces, but "every word in the typewriter face" is not yet true. In Kasandra, the Documents page body, every tooltip and the Markdown reading view are still in Plex Sans or the system sans. I found no crashes or tracebacks. The crawler covered only part of the window because the main session stopped it three times.

All my own frames are under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_review_a/frames/` (the probes are in `.../look_review_a/code/`, the zoomed crops in `.../look_review_a/crops/`). I used the copied tree, ran everything offscreen under `unshare`, and changed nothing.

## Findings, most severe first

**1. High: the Documents page is drawn in Plex Sans and Plex Mono in Kasandra.**
- Body text and headings ("Decision", "Bench PDF page 1"…) are plainly sans in `.../frames/kasandra_1920x1200/17_document.png` and `.../frames/kasandra_1366x768/17_document.png`.
- Cause: `workbench/document_qt.py:46-49` `fonts_of()` passes `profile['prose_family']` and `profile['code_family']` straight through and never calls `reading_preferences.in_force`. The stored defaults are still `IBM Plex Sans` / `IBM Plex Mono`.
- The toolbar letters (B I U H1 H2 H3 ¶ {} Aa) are also Plex. My painter audit recorded them in Plex Sans/Mono; they come from `glyph_set.letters(family='IBM Plex Sans')` and `'code'` uses `'IBM Plex Mono'` (`glyph_set.py:384, 457`).
- Fix: in `fonts_of`, take `_, prose, code = in_force((profile['family'], profile['prose_family'], profile['code_family']))` before calling `font(...)`. In Kasandra, give `letters()` `bt.FACE`, and give the `{}` glyph `bt.MONO`.

**2. Medium-high: every tooltip is in the system sans.**
- The DELETE and Apps tooltips render in the app default face (Inter here, 12 px): `.../frames/tips_1366x768/tooltip_DELETE.png`. Probe `.../code/tips2.py` printed `QTipLabel Inter 12`.
- Only widgets with their own font sheet escape this; the masthead model tooltip, for example, is Kasandra Elite Mono.
- Fix: in Kasandra, call `QToolTip.setFont(QFont(bt.FACE, ui px))` in `load_fonts`/`make_app`, or add `QToolTip {font-family:"%(FACE)s"; font-size:…}` to the app sheet (theme2 QSS2).

**3. Medium: 1 and l are still hard to tell apart at real sizes.**
- "A1 · text · literal" reads "Al", and in Terminal "Nov12" reads "Novl2": `.../crops/one_vs_l_ui.png` and `.../crops/l1_x3.png`.
- I measured a pixel difference between l and 1 at 13, 15 and 18 px. In Kasandra Elite Mono it is 0.50–0.55. That is lower than Special Elite (0.61–0.73) and Plex Mono (0.65–0.69), so the mono face made them more alike, not less.
- An underlined "1" in a link ("1 waiting for you") hides the only difference, the foot.
- The builder's test checks this at 64 px only. The slashed 0 against O reads clearly.
- Fix: in `tools/derive_typewriter.py`, change the shape, not just the foot. Either give `one` a long, angled flag and drop its left foot, or give `l` a curved right tail. Then test at 13 and 15 px against Plex Mono's l-to-1 difference.

**4. Medium: her words are cut mid-word in her column.**
- "07_Bench_Readings." / "pdf" and "07_Rail_Limits_Rev" / "_B.pdf", at both sizes: `.../frames/kasandra_1920x1200/15_her_column_cards.png` and `.../frames/kasandra_1366x768/15_window_cards.png`.
- Each name would fit on a 296 px line. Graphite keeps the same names whole: `.../frames/graphite_1366x768/15_window_cards.png`.
- Cause: `leaded()` calls `breakable()` (`shell2.py:1725`), which inserts a zero-width space every 18 characters.
- Fix: in `leaded()`, only break runs longer than the line holds (label width ÷ the face's advance of 'M', about 26 characters here), and break at `_`, `.` or `/` first.

**5. Medium (also in 0.8.2): the Markdown reading view is Plex Sans, and its code is a tiny generic monospace.**
- See `.../frames/tips_1366x768/md_viewer_1366x768.png`, against 0.8.2 in `.../frames/base082/md_viewer_1366x768.png`.
- Cause: `workbench/view_modules/markdown_view.py:12-13` hard-codes Plex in its CSS.
- On the same page at 1366, the viewer's action row clips mid-word ("Ask about th", "Receive int", "Open in Gra", "bench note.").
- Its minimum width also narrows the whole desk: panes go from 354 to 278, the band words drop to about 11 px, and she shrinks.
- Fix: build that CSS from `bt.FACE`/`bt.MONO` (through `in_force`) at the code size. Let the action row fold behind More… so it never sets the desk's minimum width.

**6. Medium-low: her column's dark ground is a box set inside the column, not the column itself.**
- The dark ground #11132c covers only SlateFace (322×1015 at x 1582). Around it are 16 px lighter strips on each side, 10 px above, and the empty 53 px right foot below, all #171b3c. The teal edge sits 16 px away from the dark ground.
- See `.../crops/home1366_right.png` and the ground samples in `.../frames/holo_1920x1200/holo.json`.
- Fix: paint the terminal ground across the whole right PaneBody (content and foot, from the teal edge to the window edge) and keep SlateFace transparent.

**7. Low-medium: the static is almost as busy in the calm states as at idle.**
- Live mean brightness change per new frame at 1920 (0–255 scale): idle 6.4, at work 7.4, waits for you 6.3, done 6.5, stopped 5.0 (`.../frames/holo_1920x1200/holo.json`, strips in `state_*.png`).
- The noise is re-rolled on every frame at 12 fps, so "waits for you" is barely calmer than idle.
- Between live frames at 1366 the mean brightness swung 2.4%; the plan's limit is 2%.
- It reads well as a hologram (`.../frames/kasandra_1920x1200/03_holo_x2_a.png`). The risk is a constant sparkle in peripheral vision over a long session.
- Fix: re-roll the noise every 2nd or 3rd frame and keep the scan lines at 12 fps. Cut the static for waits for you and stopped to about 0.10, or hold their noise tile still.

**8. Low: the hologram's base ring nearly touches DELETE at 1920.**
- The ring ends about 4 px above the can and overlaps its x range: `.../crops/files1920_delete_x4.png`.
- Fix: raise ROOM from 16 to about 24, or narrow the ring when it would sit over DELETE.

**9. Low: the "1 waiting for you" link wraps after the "1".**
- A lone underlined "1" is left at the line end, at both sizes, and it reads as "l": `.../crops/files1920_right_top.png`.
- Fix: a non-breaking space inside the link's words.

**10. Low: the emblem's violet trace loses contrast at its size.**
- Its edges are clean at 58×38, with no navy fringe (`.../crops/emblem_x8.png`).
- The violet trace (#7635fe) sits over the head band's teal glow (y 40–46), at roughly 2:1 contrast.
- Fix: lift the icon 3–4 px, or lighten the trace in the small cut.

**11. Low (also in Graphite): the REV A / REV B afterimage collides with the current value.**
- "Up to 120 ms" sits on the red box's top edge and touches "Up to 80 ms": `.../crops/rev_cut_x2.png`, and the same in Graphite in `.../crops/rev_g1366_x2.png`.
- Fix: draw the afterimage above the box, or make the row taller.

**12. Low: the Then panel preview cuts names short.**
- It shows "Rail volta…" and "Settled cu…" although the panel has room for about 40 characters: `.../frames/kasandra_1366x768/11_then_panel.png`.
- Fix: in `context_menu.LinePanel.preview_text`, count the letters from the panel's width after it is shown.

**13. Low: in Terminal, box-drawing lines meet across but not down.**
- `┌─┐` joins across, but there is a gap down to `└─┘`, because the reading profile's 1.4 line spacing is applied to the console output.
- The `ls -l` columns do align in Kasandra Elite Mono: `.../frames/kasandra_1920x1200/22b_terminal_ls_x2.png`.
- The console document's default font is still IBM Plex Sans; this is not visible today.
- Fix: leave `ConsoleOutput` out of the reading profile's line spacing, and set its document default font to MONO.

**14. Low: the Settings font report reads like a failure.**
- Interface font shows "Saved: IBM Plex Sans … Effective: Kasandra Elite · applied with fallback": `.../frames/kasandra_1366x768/07_settings.png`.
- Fix: say "Kasandra's face (the default)".

**15. Low, a judgement call: her column is no wider at 1920.**
- Her text is 296 px wide (about 17 px more) and the conversation is 37 px taller. But two Trace cards (about 414 px each) still fill it, and "7 earlier · show them" appears while the centre has about 1200 px spare.
- The fold itself is correct: about 146 px left against 414 px needed.
- Fix: consider a wider right pane (about 420 px) at widths of 1600 and up.

## What holds
- **DELETE:** the can reads DELETE in red typewriter, letter-spaced, 120×29 at (218,662) at 1366 and (218,1094) at 1920.
  - The file right-click says "Delete", the Files page says "Deleting moves it to DELETE", and the tab is titled DELETE.
  - No "Trash" appears in any frame; it remains only in docstrings and internal names.
  - Delete and Erase never meet: removing words is "Erase", files are "Delete".
- **Typewriter face elsewhere:** all 8 head menus, the right-click menu, More, the Then panel, the trees, tabs, Field cards, her column, the band, the meters, and message and input dialogs are Kasandra Elite or Kasandra Elite Mono.
- **The hologram reads as a hologram** at both sizes.
  - At 1920 she stands on the stage at (28,698,297,396). At 1366 she stands in the corner at (39,507,152,200). On Machine she is on the stage.
  - She is hidden on Settings and on the Clean desk (timer off). With all rows open at 1920 she moves to the corner at (24,899,182,240).
  - With Reduce motion the timer is off and two frames 0.9 s apart are identical.
  - The ASCII desk shows a still figure in characters; it is a little abstract.
  - The timer runs at 83 ms while the window is active.
  - Her base and the masthead cursor show the same colour in all five states.
- **Masthead:** its rule is at y 117, level with the left tab rule, at both sizes.
- **Scroll census:** 2 at 1920 (0.8.2: 3) and 18 at 1366 (0.8.2: 26). Logs: `.../look_review_a/logs/census_1920x1200.log` and `census_1366x768.log`.
- **Graphite:** unchanged except DELETE (Plex Sans) and the card line, which is now Plex Mono. The portrait and "[#] Apps ▾" are still there: `.../frames/graphite_1366x768/`.

## Crawler (CRAWL_MODE=icons, 1366×768, Kasandra)
- 53 controls and menu lines were pressed: all of Sheet (with 6 dialogs), PDF and Writing, and Finding up to "Read source". There were 0 tracebacks and no crash: `.../look_review_a/logs/crawl_icons_1366.log`.
- The main session stopped the run three times (`crawl_icons_1366.log`, `crawl_icons_1366_b.log`, `crawl_Sheet.log`). The Calc page and the rest of Finding were not reached.