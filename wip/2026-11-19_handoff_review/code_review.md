# The code review of the Colored Pencil overlay (19 Nov 2026)

One independent reviewer read the overlay (a third appearance built elsewhere on 0.8.3, 16 Python files and one picture)
against commit 951c789. Nothing was merged. The handoff itself is not in this repository; the owner holds it.

## Summary

The owner's instinct is sound: a calm paper look is worth having, the screenshot is readable, and the palette shows the existing colour roles can carry a light desk. The overlay is a trial build on 0.8.3, not something to merge: about 65 checks on the look's name across 13 files, colours written outside the palette, and whole surfaces never looked at. Read branch by branch against the base, it does not change how Graphite or Kasandra draw. In its own look it has real faults: document pages turn dark slate, glow effects remain as smudges (visible in its own screenshot), the bird will show over the screensaver, Stacy's dark art appears under Kasandra's name, the desk act cannot choose the look, selection fills are nearly invisible, and its red and green merge for weak red-green sight. It breaks one existing test, overlaps the 0.8.4 leftovers and would not survive the 0.8.10 split. The installer is careful but silently drops three parts of the copy, so it should not be run as delivered. Three things in it are worth taking in 0.8.4 for every look: a probable 0.8.3 start-up failure when the Office tab was left open, the doubled "Now: Now:" line, and a crash on a damaged appearance value. So the plan changes little: those fixes join 0.8.4, one place for look differences joins the 0.8.10 split, and Colored Pencil is built on that after 0.9.0, where a look for tired eyes is already planned. The word on the head, the bird, her name and which figure she is are the owner's to decide. Everything here was read from the code and measured from the files; nothing was run, and nothing is claimed about the ThinkPad.

## Points, each with a recommendation

### A third appearance, Colored Pencil: a light paper desk beside Graphite and Kasandra

- **Assessment:** good · **Recommendation:** park_until_after_0.9.0 · 0.9.x look track, as the calm look already planned for tired eyes; its groundwork rides the 0.8.10 split
- **Where:** <scratch>/handoff3_work/overlay.diff (whole: 16 Python files, 448 lines added, 103 removed) and <scratch>/in/handoff3/Screenshots/KP_Colored_Pencil_Desktop.png
- **Reasons:** The look is worth having. It is calm, words are comfortably readable (5:1 to 12:1 on its grounds), and it shows the palette roles can carry a light desk. What is delivered is a trial overlay for 0.8.3, not a merge candidate: it has faults of its own (items below), one existing test fails with it, it overlaps 0.8.4 and would not survive the 0.8.10 split, and gates 1, 2 and 6 of 0.9.0 are written for two looks. Take the pictures and the palette as the brief and build it once, on one place for look differences.
- **Evidence:** Palette at diff lines 87-100. Contrast measured with <scratch>/handoff3_review/code/contrast.py. /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md lines 195-198 (two appearances), 239 (a tired-eyes setting over 0.9.x), 359-364 (gates).
- **Cost or risk:** About one release-sized slice to reach the standard the Kasandra look was held to (0.8.0 and 0.8.3 were whole releases), then about half again on the checking share of every later window pass. Before 0.9.0, the gates' "both looks" becomes three.

### How the look is wired in: about 65 new checks on the name 'pencil' in 13 files, on top of 58 two-way appearance checks already in the base

- **Assessment:** weak · **Recommendation:** adapt_first · 0.8.10, inside the split
- **Where:** <scratch>/handoff3_work/overlay.diff (all hunks); <scratch>/handoff3_work/pyz/payload/workbench/
- **Reasons:** The base decides colour by role (boss_theme.PALETTES) and behaviour by comparing the look's name. The overlay fills the palette properly (all 57 roles), then adds 65 literal branches and eight colours outside the palette row. About a quarter of the branches only switch light off. Roles that exist are bypassed (Approve ignores OWNER, Send ignores the palette). A two-way check has no right answer for a third value, which is where several faults below come from. The style differs too: the base is dense one-line statements with long comments quoting the owner; the overlay writes spaced blocks and drops about a dozen of those comments and three docstrings. The word pencil already means Graphite's own mark in this code (desk_qt.PENCIL, BAND_PENCIL, PENCIL_DEEP). Adaptation: a small table of traits per look in boss_theme (has light, bar or edge selection, hologram or still, her name, head word) read everywhere instead of comparing names, done while the split is touching those sites anyway.
- **Evidence:** Counts by grep: base has 46 `== 'kasandra'`, 5 `!= 'kasandra'`, 5 `== 'graphite'`, 2 `!= 'graphite'`; the overlay widened 11 and left 47. 'pencil' literals: field_qt 14, shell2 14, boss_theme 6, pane_qt 6, typebar_qt 6, kasandra_column 5, boss_qt 4, desk_qt 3, hologram_qt 2, programs_qt 2, three files 1 each. Colours outside the palette: diff lines 102-104, 571, 1152-1153. The owner's quoted words on Neon removed at diff line 131.
- **Cost or risk:** Two to three days of builder time inside 0.8.10 plus the suite between moves. Without it, every later look or look change pays the scattered branches again.

### The Colored Pencil palette: all 57 colour roles filled for a light desk

- **Assessment:** mixed · **Recommendation:** adapt_first · with the look; its colour-vision check uses what 0.8.4 builds
- **Where:** <scratch>/handoff3_work/overlay.diff lines 87-104
- **Reasons:** Good: every role is present, so most of the window follows without code, and words read well (TEXT 10.8 to 12.1:1, QUIET 5.8 to 6.1:1, FAINT 5.0 to 5.5:1). Measured weaknesses: (1) selection fills are almost the colour they sit on: tree row 1.03:1, Field card 1.15:1, menu bar on menu paper 1.17:1, so where you are rests on a 2 px edge (3.8 to 4.2:1) and word colour. (2) Red and green are its two action colours and they merge for weak red or weak green sight: STOP against READY falls from a colour distance of 47 to 9.7 and 11.6 under simulation. (3) One blue (#315f82) is selection words, cue words, a line's words, the band's chosen mark and Send; RECHECK, VIOLET and ROYAL sit within 5 to 7 of the selection edge. (4) OWNER and HONEY are the same value, so hers and waits-for-you cannot be told apart. (5) DESK_LIGHT is wrong for a light desk (next item).
- **Evidence:** <scratch>/handoff3_review/code/contrast.py (WCAG ratios; CIE76 distances under Machado 2009 simulation). /home/user/Struthio/wip/2026-11-14/mockup/CANON.md lines 369-395. /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md line 238.
- **Cost or risk:** A palette pass of a day or two with the measurements written beside the values, as the burnt yellow was done. Cheap before code depends on it.

### Document pages in Colored Pencil (not addressed by the overlay)

- **Assessment:** harmful · **Recommendation:** adapt_first · before any trial on real documents
- **Where:** <scratch>/handoff3_work/overlay.diff line 96 (DESK_LIGHT='#6f8598')
- **Reasons:** Every PDF page, datasheet crop and reference picture is multiplied by DESK_LIGHT so a white page does not glare on a dark desk. The pencil row gives a mid slate as dark as Graphite's own value, so on the paper desk a white page is shown as a dark blue-grey slab, 3.6:1 darker than the ground, and coloured plots are tinted. Reading evidence is the core of the work. Neither screenshot shows a document, so this was not seen. Read from the code, not run.
- **Evidence:** /home/user/Struthio/workbench/page_light.py:14 and :22-24 (Multiply by DESK_LIGHT); /home/user/Struthio/workbench/pdf_qt.py:34. Luminance 0.224 against the ground's 0.929.
- **Cost or risk:** One value near white and a test that a page is not darkened in a light look. Left as is, the first real document opened in the trial looks broken.

### No glow in Colored Pencil: Glow fixed at Soft and switched off place by place

- **Assessment:** weak · **Recommendation:** adapt_first · with the traits table
- **Where:** <scratch>/handoff3_work/overlay.diff lines 27-29, 50, 58, 130-134, 196-199, 306-373, 698-708
- **Reasons:** The intent is right for paper and the central switch glows() is a good move. But the level stays at 1.0, not 0, and effects that do not ask glows() still draw, as dark smudges instead of light. The live meter readings keep a blurred shadow, visible on 52% and 22% in the handoff's own screenshot. Every menu still gets the 150 ms catch, now a dark frame and a dark band across paper. Menu glyphs and the pointer keep a halo. After any change of desk art, every waiting Approve gets a lamp although glows() says no. Greying the Glow submenu with a reason is the right manners.
- **Evidence:** /home/user/Struthio/workbench/desktop_header_qt.py:121-137; /home/user/Struthio/workbench/menu_catch.py:30-44 and :66-89; /home/user/Struthio/workbench/tool_faces.py:220-235; /home/user/Struthio/workbench/pointer.py:87-93; /home/user/Struthio/workbench/boss_qt.py:499. Crop at <scratch>/handoff3_review/code/crops.png.
- **Cost or risk:** One has-light trait removes most of the Field's 14 guards and these leftovers together. As built: small visual faults on every menu and meter.

### A 'protocol' wordmark in the upper left of the head, drawn in code, with the menus moved to start over the centre column

- **Assessment:** mixed · **Recommendation:** needs_the_owner
- **Where:** <scratch>/handoff3_work/overlay.diff lines 843-888, 929-931, 953-956, 999-1012
- **Reasons:** It looks neat, but it puts a new public name on screen. In one screenshot the head says protocol, the cards and menus say Graphite, and her column says Kasandra. The record has Graphite as the single public name; the owner's own wordmark reads "kasandra protocol" and sits unused in the tree; and the head's left was emptied on purpose (the word Graphite is hidden there today and the canon starts the menus at x 6). In code, the mark is hand-drawn polylines, not the owner's art. Its size is read from font().pixelSize(), which the window's sheet overrides, so it probably keeps one size at every reading size. It never yields, so a narrow window loses about 160 px of menu room to it and the bird. Its accessible name is Protocol while the object is still named GraphiteWord.
- **Evidence:** /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 25-28, 178-184, 192-200; /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md line 82; /home/user/Struthio/wip/2026-11-14/mockup/CANON.md line 462; /home/user/Struthio/workbench/shell2.py:600 and :753; boss_theme.face_css docstring on setFont losing to the sheet.
- **Cost or risk:** A naming decision that touches what the application is called at 1.0. If wanted: use the owner's wordmark file, sized by the desk scale; a few hours.

### Apps as the words 'Apps ▾' with a green ostrich beside them, cut at start from the owner's neon kp logo and recoloured

- **Assessment:** mixed · **Recommendation:** needs_the_owner
- **Where:** <scratch>/handoff3_work/overlay.diff lines 806-834, 941-945, 977-995, 1028-1031
- **Reasons:** The bird is charming and it is the owner's own bird. But the record says the neon kp is the only kp mark; this shows the bird without the letters, in another colour, by altering the owner's artwork at run time. Build faults: (1) the bird is a child of the main window so its feet can hang 6 px below the band, and the head's placement runs every half second and calls show() and raise_() on it unconditionally. The screensaver is also a child of the main window raised once, so the bird will reappear on top of it within half a second (read from the code, not run). (2) It is recoloured pixel by pixel in Python at every start (115 x 156 pixels) instead of being one checked file. Good: it lets the pointer through, takes no focus, Apps keeps its name, tip, click and keys, and wrong logo bytes fall back to the words alone.
- **Evidence:** /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 294-306; /home/user/Struthio/workbench/typebar_qt.py:273 (500 ms timer) to /home/user/Struthio/workbench/desk_qt.py:513; /home/user/Struthio/workbench/idle_display_qt.py:16-38. The crop is shown in <scratch>/handoff3_review/code/kp_neon_crop.png.
- **Cost or risk:** If wanted: one prepared, hash-recorded picture painted by the Apps button itself; a few hours. As built: a visible fault on the idle screen and extra work in the start path.

### Paper menus: warm paper, a pale blue bar on the row you are on, pencil grain only in the margins, for head menus, Apps and the right-click

- **Assessment:** good · **Recommendation:** adapt_first · with the look; the list fix itself is already 0.8.4's
- **Where:** <scratch>/handoff3_work/overlay.diff lines 142-168, 170-188, 719-746
- **Reasons:** The best-made part. It goes through the existing hook (MENU_BAR_CSS), keeps every row on a solid fill so words never sit on texture, and keeps the 2 px edge so a row does not move when chosen. To fix: the bar is only 1.17:1 against the paper; the catch still sweeps a dark band over it; and the cabinet menu is given the bar for pencil only, where 0.8.4 already plans that fix for it and four other lists.
- **Evidence:** <scratch>/in/handoff3/Screenshots/KP_Colored_Pencil_Menus.png; /home/user/Struthio/wip/2026-11-14/NOTES.md lines 41-44; /home/user/Struthio/wip/2026-11-14/yellow_review/review_code.md lines 17-21.
- **Cost or risk:** Small. Do the list fix once for every look that has a bar.

### The writing line: a blue button with the word Send in place of the arrow, the line starting at the centre column, and Send and the expand control added to the Tab order

- **Assessment:** mixed · **Recommendation:** adapt_first · with the look
- **Where:** <scratch>/handoff3_work/overlay.diff lines 1133-1219
- **Reasons:** A worded button is friendlier than a bare arrow and it goes through the same submit_line. Three things are lost or changed. (1) The arrow says what it will do: it turns live when what is typed will run as a line; in pencil only its 1 px border changes. (2) Send is the wrong word for four of the five targets (Terminal runs, Search searches, Web opens, Log filters). (3) The Tab order differs by look, which is behaviour, not appearance. Focus on Send is a fill change of 1.31:1, and its colours are written into the function, outside the palette.
- **Evidence:** /home/user/Struthio/workbench/typebar_qt.py:45 (SENDS) and :478 (the reads state); /home/user/Struthio/RECORD_OF_DIRECTIONS.md line 184; diff lines 1152-1153, 1160, 1215.
- **Cost or risk:** A word per target (Ask, Run, Search, Open, Filter) and a real will-run state: half a day. The Tab order needs one decision and one test for all looks.

### Her figure in the lower left as a still picture placed by the hologram's rules, her state as a word only, and her column in Kasandra's layout

- **Assessment:** mixed · **Recommendation:** adapt_first · after 0.8.5 has settled what her states mean on the figure
- **Where:** <scratch>/handoff3_work/overlay.diff lines 399-534, 546-612, 1041-1080, 1112-1124
- **Reasons:** Reusing the hologram's placement is right: she stands aside for rows, never covers DELETE, is absent in Settings, takes no clicks or focus, and Illustrated, ASCII and Clean all work. Her column takes Kasandra's masthead and bubble layout without the honey edge. What is dropped is her base, its colour and her caption. In Kasandra her base, cursor, word and caption agree and carry five states; here the figure never changes and the word has two looks, so at work, done and stopped differ only in the word. The 0.8.5 promise that the hologram goes to at work has nothing to show. In code: the still is rescaled from the full picture at every paint (bilinear, uncached); the tint behind waits-for-you is a colour outside the palette that the old-panel relighter can turn into the card colour; the pencil exception in Masthead.follow is not needed; most of HologramStage is carried unused.
- **Evidence:** /home/user/Struthio/wip/2026-11-14/mockup/CANON.md lines 397-413; /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md lines 266, 273; diff lines 469-473, 554, 568-572; /home/user/Struthio/workbench/theme2.py Relight class.
- **Cost or risk:** A small still-figure class sharing the placement function, plus one honest state mark for a still: a day or two, decided together with her hand's states.

### The Field on paper: a dotted guide instead of scan lines, no halos or surge, blue wires, a pale fill and second pencil line for the selected sheet

- **Assessment:** mixed · **Recommendation:** adapt_first · with the look
- **Where:** <scratch>/handoff3_work/overlay.diff lines 249-398 (field_qt.py, 14 branches)
- **Reasons:** Sensible choices one by one, and the corner ticks, the dashed recheck edge and the state shapes are kept, so the Field still reads without colour. But the handoff has no picture of the Field at all, though it is the centre of every scene. The changes are 14 separate name checks. Hovered and selected wires are the same blue. Trace lands with no surge even without Reduce motion. The dot grid builds about three thousand points in Python on every paint, and the pointer's lit square still triggers repaints that now draw nothing.
- **Evidence:** Diff lines 283-298 (dots), 324-328 (wires), 336-337 (surge off). /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md line 332 (a Field frame in 16 ms).
- **Cost or risk:** Needs P01 played in this look and frames of the Field before any judgment; the grid should be a cached tile. One to two days once the traits exist.

### Green for Approve and red for Stop in this look ("separate green and red actions")

- **Assessment:** mixed · **Recommendation:** needs_the_owner
- **Where:** <scratch>/handoff3_work/overlay.diff lines 265-276, 907, 916-921, 1103-1107
- **Reasons:** Familiar from other desktops, and both keep their words. But in each existing look, what waits for the owner has one colour of its own (amber, raspberry) shared by the mark, the Approve button and her state. Here the mark and her state use OWNER (dark honey) while the button uses the ready green, which is also the pointer's and what is live. Stop always red also changes its rule (plain until something is stuck). And red against green is the pair that fails for weak red-green sight. The palette already has OWNER and ON_OWNER for this; the code goes round them.
- **Evidence:** /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 80-90; /home/user/Struthio/wip/2026-11-14/mockup/CANON.md lines 369-395; <scratch>/handoff3_review/code/contrast.py.
- **Cost or risk:** No code cost either way. If green is wanted, set it through the OWNER role so the mark, the button and her state stay one colour.

### Tabs, band words and the left tree in Colored Pencil

- **Assessment:** mixed · **Recommendation:** adapt_first · with the look
- **Where:** <scratch>/handoff3_work/overlay.diff lines 208, 613-711
- **Reasons:** The tree is fine: traces in the look's blue, no breathing timer, the pane's own ground. But the rule that whatever the pointer is over answers in the pointer's colour is dropped: a hovered tab or band word takes the chosen mark's colour, so two tabs can look chosen. In the tree the lit path is blue while the chevrons on it stay green.
- **Evidence:** Diff lines 208 and 637. <scratch>/handoff3_work/pyz/payload/workbench/pane_qt.py, the chevron pen in draw_branches. /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 80-83.
- **Cost or risk:** Minutes each, once it is decided what hover means on paper.

### She is Kasandra in Colored Pencil (assistant_identity)

- **Assessment:** mixed · **Recommendation:** needs_the_owner
- **Where:** <scratch>/handoff3_work/overlay.diff lines 2-18
- **Reasons:** The change is one clean line in the one place that owns the name. History keeps the names it was written with, and nothing changes in Graphite (Stacy) or Kasandra. Whether it is right is the owner's: the record says Stacy is the assistant and Kasandra is her name in the Kasandra appearance; nothing says who she is in a third look. Kasandra fits where the plan is going, but then Kasandra is both the assistant in two looks and the name of one look in the Appearance menu. One string bypasses the single place: the figure's accessible name is written as "Kasandra, pencil illustration".
- **Evidence:** /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 25-28, 72-76; /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md lines 37, 780; diff line 432.
- **Cost or risk:** None in code. One naming decision, best made once for all looks.

### Pages the overlay did not touch: two-way appearance checks fall both ways for a third look

- **Assessment:** weak · **Recommendation:** adapt_first · with the look
- **Where:** /home/user/Struthio/workbench/boss_qt.py:106-137 and :212-214; /home/user/Struthio/workbench/sheet_workbench_qt.py:332; /home/user/Struthio/workbench/idle_display_art.py:194; overlay.diff lines 1089-1093
- **Reasons:** Words are chosen by asking whether the look is Graphite, pictures by asking whether it is Kasandra. In pencil both answers are no, so the sheet page's portrait, the worksheet strip and the screensaver show Graphite's dark After Midnight plates and Stacy's portrait on paper, while their accessible names say Kasandra. The overlay avoids this on Home's first page only by removing the art panel there. The five lists 0.8.4 names as leftovers and every room outside the two screenshots are in the same state: unexamined.
- **Evidence:** As in where. /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md line 145 (nothing is removed to make things simple).
- **Cost or risk:** This is the real size of a third look: every surface looked at once, with frames. About a week of builder and reviewer time, going by the 0.8.3 look pass.

### Choosing the look by name through the desk act (missing from the overlay)

- **Assessment:** weak · **Recommendation:** adapt_first · with the look
- **Where:** /home/user/Struthio/workbench/desk_acts.py:166-169
- **Reasons:** The Appearance menu gains a third row but look.set still accepts only graphite and kasandra. The window can then do what a typed act, a scene or later her door cannot. The standing rule is that a new power for the window gets its act, and one list should feed both.
- **Evidence:** /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 269-275; /home/user/Struthio/tests_integrated/test_desk_acts.py:672-674.
- **Cost or risk:** One line and a test that the act's choices equal boss_theme.APPEARANCES.

### Reading the saved appearance safely, and one list of appearances for the session

- **Assessment:** strong · **Recommendation:** adopt_now · 0.8.4
- **Where:** <scratch>/handoff3_work/overlay.diff lines 111-125 and 747-760
- **Reasons:** A real fault in 0.8.3 is fixed in passing. If the session file holds an appearance that is not text (a list or an object, from a damaged or hand-edited file), the membership test raises TypeError, which the function does not catch, and Graphite cannot start. The isinstance check fixes it. Taking the allowed names from one list is also right, but the session module should not import the theme to get it; keep a plain tuple somewhere neutral. A saved 'pencil' degrades safely on a build without it (it falls back to Graphite).
- **Evidence:** /home/user/Struthio/workbench/boss_theme.py:135-136 (only OSError, ValueError, AttributeError caught); /home/user/Struthio/workbench/session.py:104.
- **Cost or risk:** Minutes, with one test. It belongs with 0.8.4's tests for blind spots.

### A guard so a saved Office or Slate room tab does not stop Graphite from starting

- **Assessment:** strong · **Recommendation:** adopt_now · 0.8.4, reproduced first; worth knowing before the ThinkPad evening with 0.8.3
- **Where:** <scratch>/handoff3_work/overlay.diff lines 1220-1239 (workspace_tabs.py)
- **Reasons:** Nothing to do with the look, and it points at what reads as a start-up failure in stock 0.8.3. The window restores its tabs before the bridge that opens rooms exists, so a session saved with the Office tab open calls show_office on a missing attribute. restore() does not catch that error, and the launcher reports that Graphite could not start. The dedicated session opens the Office at every start, so the second start is the likely place to meet it. I read this from the code and did not run it; no test covers it. The overlay's guard is a patch, not the fix: the row goes to the deferred list, the start script opens the Office again, and the deferred list then grows by one at every start. The fix is to restore rooms after the bridge exists.
- **Evidence:** /home/user/Struthio/workbench/qt_app.py:2375 before :2407, and :3201; /home/user/Struthio/workbench/workspace_tabs.py:145-146 and :149-170; /home/user/Struthio/START_OFFICE.sh:6; /home/user/Struthio/LS_XSESSION.sh:41.
- **Cost or risk:** An hour to reproduce in the container with a ten-line test, an hour to fix properly. If real and left, the owner's second start on the ThinkPad fails until the session file is removed.

### Her column's line no longer says 'Now: Now: …'

- **Assessment:** good · **Recommendation:** adopt_now · 0.8.4, for every look
- **Where:** <scratch>/handoff3_work/overlay.diff lines 1067-1071
- **Reasons:** When something is running, the agenda summary already begins with Now: and her column adds Now: again. The overlay fixes it, but only when the look is pencil, which makes no sense for a wording fault. Take the fix without the condition.
- **Evidence:** /home/user/Struthio/workbench/agenda_qt.py:227; /home/user/Struthio/workbench/shell2.py:2028-2029.
- **Cost or risk:** Two lines and one test.

### What the overlay does to the existing Graphite and Kasandra looks

- **Assessment:** good · **Recommendation:** adapt_first · only if any of it is merged
- **Where:** <scratch>/handoff3_work/overlay.diff read against <scratch>/handoff3_work/base/workbench/
- **Reasons:** I checked every branch on the appearance name and found no drawing or layout change in Graphite or Kasandra. The rewritten head placement, Apps mark, writing-line sheet and geometry, hologram install and paint, tree branches and Field texture give the same values when the look is not pencil. Four side effects remain. Both looks gain a third row in Rules ▸ Desk artwork ▸ Appearance. One existing test fails in every look. Three new constants join boss_theme.TOKENS in every look, so the old-sheet relighter would keep #fffdf8 as near-white where it used to make it the card colour (nothing uses that today). The tab-restore guard changes start-up in every look.
- **Evidence:** Diff lines 964-1022 against base shell2.py lines 742-790; 1151-1170 against base typebar_qt.py lines 470-483; 102-104 with /home/user/Struthio/workbench/boss_theme.py:171 and :211-213.
- **Cost or risk:** None if not merged. If merged, remove the four side effects first.

### Existing tests the overlay breaks or leaves too narrow

- **Assessment:** weak · **Recommendation:** adapt_first · with the look
- **Where:** <scratch>/handoff3_work/overlay.diff line 542 (kasandra_art.MARKS) and the payload as a whole
- **Reasons:** In the default look, test_every_mark_is_recorded fails: pencil-avatar.png is added to MARKS but its hash is not added to branding/kasandra/README.md, which the handoff's own notes say to do. Every test that checks the seed's source digest fails until the seed and manifest are rebuilt. Still passing but now too narrow: the test that both palettes name the same colours compares two of three, and look.set is tested for two names. Run in pencil, the test that Glow opens on Neon fails by design. The only suite evidence the handoff offers is five scene tests, with the look not stated.
- **Evidence:** /home/user/Struthio/tests_integrated/test_kasandra_column.py:157-163; /home/user/Struthio/branding/kasandra/README.md; /home/user/Struthio/tests_integrated/test_kasandra.py:38-40; /home/user/Struthio/tests_integrated/test_faces_find_light.py:268; <scratch>/in/handoff3/02_IMPLEMENTATION_AND_QA.md line 47.
- **Cost or risk:** The rule from 0.8.4 on is zero failing; this arrives with one.

### What a third look needs in tests, and what it costs on every later window pass

- **Assessment:** mixed · **Recommendation:** park_until_after_0.9.0 · 0.9.x, in the slice that builds the look
- **Where:** /home/user/Struthio/docs/CAMPAIGN.md lines 107-111; /home/user/Struthio/tools/campaign_lib/cases_scene.py:61-62 and :109; /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md section 12
- **Reasons:** Needed once: palette tests (same roles, a text contrast floor, meaning colours distinct, weak red and green simulated); the sheets; the look accepted from the environment, the session and look.set; her name; the figure (still, characters, hidden on Clean, absent in Settings, stands aside, no timer); the head at 1366 x 768, 1920 x 1200 and a large reading size; Send and its will-run state; a page not darkened; no light drawn anywhere; the window probe; P01's four runs. The Kasandra look has 84 tests in five modules and a 445-line probe; expect 40 to 60 here. Standing: scenes and window modules run once per look, so two looks to three is half again. P01 costs about 2.4 minutes per look, and seven scenes are planned by 0.8.9 against a 15-minute release battery. Frames, reviewers' reading and the owner's ThinkPad evenings grow the same way. Every new piece of window drawing (her ring and card in 0.8.5, the time slider, quarantine) must also be designed for a light ground.
- **Evidence:** Test counts from /home/user/Struthio/tests_integrated/test_kasandra.py, test_kasandra_column.py, test_kasandra_highlight.py, test_hologram.py, test_typewriter_faces.py and kasandra_window_probe.py. SPEC lines 359-360, 520, 541, 580.
- **Cost or risk:** One-off: roughly a week inside the slice that builds the look. Standing: about half again on the checking share of every window pass, for as long as three looks are kept.

### Swap the lower-left figure for Kasandra_Combined_More_Glitch.png

- **Assessment:** mixed · **Recommendation:** needs_the_owner · only once Colored Pencil exists in the tree
- **Where:** <scratch>/in/handoff3/Artwork/Kasandra_Combined_More_Glitch.png; <scratch>/in/handoff3/02_IMPLEMENTATION_AND_QA.md lines 38-43
- **Reasons:** It is not a drop-in. Measured: 724 x 2172 RGBA, 2.17 MB (the R2 figure is 365 x 1200, 671 kB). Clear margins around her ink (alpha above 8): left 46, right 59, top 16, bottom 15 px. No pixel is fully opaque: her body is alpha 250 to 253, 4.5% of the canvas is a faint haze around the glitch blocks, 43.8% is clear. The place she stands in is not 365 x 1200: it is 608:822 wide to tall, at most 380 px tall at 14 pt, fitted by height. She would stand the same height as now (about 375 px of ink) and 127 px wide instead of 116, so no layout changes. Cropped to her ink and scaled to 1200 tall she is 347 x 1200. At slot size the picture is drawn 5.7 times down with a bilinear scale on every paint, so the glitch blocks become specks; it should be scaled once. The swap takes a prepared export, the new SHA-256 in kasandra_art.MARKS and in branding/kasandra/README.md, the seed and manifest rebuilt, and checks in Illustrated, ASCII and Clean. The larger decision: the R2 figure has the bob and face of the owner's hologram; this one is a different-looking woman (copper curls, glasses), described as borrowed from another character and made elsewhere.
- **Evidence:** <scratch>/handoff3_review/code/img_stats.py and alpha_hist.py (numbers), slot_scale.png and avatars.png (both figures at slot size). /home/user/Struthio/workbench/hologram.py:21-26 and :80-103. /home/user/Struthio/branding/kasandra/README.md lines 17-27. /home/user/Struthio/RIGHTS.md.
- **Cost or risk:** About half a day of art preparation and checks, after the owner has said who she is and that the picture is theirs to keep under branding/.

### The installer pencil2.pyz: a side-by-side trial copy of 0.8.3 with the overlay

- **Assessment:** mixed · **Recommendation:** decline
- **Where:** <scratch>/handoff3_work/pyz/__main__.py (179 lines; read, not run)
- **Reasons:** Careful in most ways. It checks its 17 files against its manifest, refuses unsafe paths, requires the source to be 0.8.3 with those 16 files unmodified, copies the folder beside it, writes the 17 files, and makes a launcher that forces the look and points the Concern, profile and state at folders inside the copy. It uses no network and no root and never writes into the owner's 0.8.3 or their Concern. Wrong or unwise: (1) its copy filter, meant for core dumps, skips anything named core or core.*. That drops sdk/cli/arc1cli/core.py (the arc1 command line cannot import), tools/campaign_lib/core.py (the campaign and its scenes cannot run from the copy) and the game's src/core folder. It then rebuilds MANIFEST.json in the copy, so the integrity check agrees with the incomplete tree. (2) The copy still calls itself 0.8.3. (3) It will use the Python environment of the 0.4.6 install if it finds no other, which may carry a different PySide6. (4) It leaves a lock file beside the destination and copies everything in the source folder, including any model files kept there. (5) Because the launcher sets the look in the environment, choosing another look in the menu has no effect at the next start from that launcher.
- **Evidence:** __main__.py lines 20-21 and 85-86 (the filter), 72 (the 0.4.6 environment), 94 and 107 (scripts run in the copy), 109 (.venv link), 124 (lock), 22-31 (launcher). /home/user/Struthio/sdk/cli/arc1cli/main.py:11; /home/user/Struthio/tools/campaign_lib/runner.py:36.
- **Cost or risk:** To let the owner see the look on their panel before it is built properly: fix the two filter patterns, mark the copy as a trial in its manifest note, and run it only after the 0.8.3 evening. About an hour. As delivered: a trial that is quietly incomplete.

### The 'ready-to-paste task for Claude' and the handoff's statements of status (shipped, released, selected, approved)

- **Assessment:** weak · **Recommendation:** decline
- **Where:** <scratch>/in/handoff3/START_HERE.md lines 28-32; <scratch>/in/handoff3/01_DESIGN_AND_CHARACTER.md lines 3-17
- **Reasons:** Treated as data and not carried out. It asks for the figure to be integrated into a Colored Pencil appearance that does not exist in our tree, on the authority of decisions our record does not hold; the owner calls the package ideas. Its list of checks (exact manifests, two window sizes, Clean and Reduce motion, saying what was not verified on the ThinkPad) is the right kind and matches our process.
- **Evidence:** As in where. /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md section 12.
- **Cost or risk:** None.

## Conflicts with the plan, the canon or the rules

- **(high) Spec section 7 (two appearances, every scene in both), the 0.9.0 gates 1, 2 and 6, and the 15-minute release battery:** A third look before 0.9.0 turns 'both looks' into three for P01 to P07 on the ThinkPad, reopens 'the look settled on the owner's panel', and adds half again to scene time. *Evidence:* /home/user/Struthio/wip/2026-11-14/SPEC_0.8.3_to_1.0.md lines 195-198, 359-364, 520, 541
- **(high) 0.8.10, the split of shell2.py, qt_app.py and context_menu.py:** The overlay is a diff against 0.8.3's file layout with about 350 changed lines in shell2.py alone. Merged before the split, the split carries 65 more branches and a third look through every full-suite run between moves. Merged after, the hunks no longer apply and must be redone by hand. The installer also refuses any version but 0.8.3. *Evidence:* overlay.diff lines 761-1111; SPEC line 331; <scratch>/handoff3_work/pyz/__main__.py lines 15, 38-44
- **(medium) 0.8.4 (the yellow leftovers and zero failing tests):** The cabinet menu change is the planned leftover fix, done for one look only. Hunks overlap the files 0.8.4 edits (boss_theme.py, field_qt.py, typebar_qt.py, cabinet_actions_qt.py). One existing test fails on arrival. *Evidence:* /home/user/Struthio/wip/2026-11-14/NOTES.md lines 41-44; overlay.diff lines 170-188; /home/user/Struthio/tests_integrated/test_kasandra_column.py:157-163
- **(medium) 0.8.5, her door (the saved slice hand_s1):** The saved patch touches shell2.py, field_qt.py, kasandra_art.py and desk_acts.py, as the overlay does. 'Her hand's states wired to the hologram' has no counterpart on a still figure. P02 and P03 are defined in both looks and would need a third. *Evidence:* /home/user/Struthio/wip/2026-11-14/hand_s1/files.txt; SPEC lines 266-278
- **(medium) The canon (CANON.md layout and her states):** A word at the head's left, menus starting over the centre column, a bird with the word Apps, Send as a blue word where the canon has the red arrow, and a figure with no base or caption all differ from the ten approved screens. The canon is drawn in Kasandra only, so a third look needs its own sheet or the owner's ruling. *Evidence:* /home/user/Struthio/wip/2026-11-14/mockup/CANON.md lines 397-413, 461-488; SPEC line 233
- **(medium) RECORD_OF_DIRECTIONS (the owner's standing directions):** The neon kp is the only kp mark, but this shows a recoloured bird cut from it. The head's left was freed, and this adds a word there. The owner asked for way more glow with Neon by default; this look has none. Graphite is the single public name; this shows 'protocol'. All are the owner's to change. *Evidence:* /home/user/Struthio/RECORD_OF_DIRECTIONS.md lines 185-200, 294-306; SPEC lines 62, 81-82
- **(medium) Principle 11 (colours mean one thing each; readable before beautiful):** OWNER equals HONEY. One blue serves selection, cues, a line, structure and Send. Approve takes the ready green. Red and green merge under simulated weak red-green sight. Selection fills are 1.03 to 1.17:1. *Evidence:* overlay.diff lines 87-100; <scratch>/handoff3_review/code/contrast.py
- **(medium) The desk acts rule (one door; a new power for the window gets its act):** The menu can choose Colored Pencil but look.set cannot. *Evidence:* /home/user/Struthio/workbench/desk_acts.py:166-169; /home/user/Struthio/RECORD_OF_DIRECTIONS.md line 275
- **(medium) Release discipline (the exact commit; what ran where):** The trial copy calls itself 0.8.3 with a rebuilt manifest and three parts missing. Run first on the ThinkPad, it would blur the first real-machine evidence since 0.4.6. *Evidence:* <scratch>/handoff3_work/pyz/__main__.py lines 20-21, 85-86, 107; SPEC lines 86, 521, 533
- **(medium) RIGHTS.md and the privacy rule:** A figure made elsewhere from another character's features would sit under branding/ as the owner's artwork, and the kp mark is altered at run time. The handoff's notes use the owner's first name and the installer names folders in the owner's home, so none of its text may be copied into the repository as it stands. The overlay's Python itself carries no personal detail. *Evidence:* /home/user/Struthio/RIGHTS.md second paragraph; <scratch>/in/handoff3/01_DESIGN_AND_CHARACTER.md lines 28-38; __main__.py line 72
- **(low) Principle 12 (nothing is removed to make things simple):** In this look the Glow dial is greyed, Home's picture is removed, her state colours are dropped and Trace has no surge. *Evidence:* overlay.diff lines 27-29, 336-337, 1089-1093; SPEC line 145

## Errors in the handoff's own claims

- It calls revision 2 'shipped' and 'released' (01_DESIGN_AND_CHARACTER.md lines 5 and 17; 02_IMPLEMENTATION_AND_QA.md line 5). It is an unreviewed side build that this project has not tested or released, and 02 itself says the ThinkPad launch was unverified.
- 02 says to mirror the picture's checksum wherever the repository documents the mark, but revision 2 did not: branding/kasandra/README.md is not in the payload, so /home/user/Struthio/tests_integrated/test_kasandra_column.py test_every_mark_is_recorded fails with the overlay.
- 02's table says cabinet_actions_qt.py carries the contextual menu styling. The right-click menu in the screenshot is the desk menu from context_menu.py, styled through programs_qt.DeskMenu; context_menu.py is not in the overlay, and cabinet_actions_qt.py styles only the older cabinet-record menu.
- 02 says to keep menu 'shortcuts' readable. No shortcut is printed in any menu, by rule.
- 01 says the Apps area uses 'the green Struthio bird by itself'; the build and the screenshot show the bird beside the words 'Apps ▾'. 02 says the bird is 'above' the Apps control; it is beside the words, inside the button's own padding, on a widget owned by the main window.
- 01 says to 'preserve the distinct approval, stop and send cues'. In the code the cue that the line will run is reduced to a 1 px border, and Approve takes the ready green instead of the waits-for-you colour.
- 01 says Illustrated, ASCII and Clean are independent of the Appearance choice. In pencil the Glow submenu is disabled, Home's art panel is removed whatever the art mode, and Illustrated shows Graphite's plates on pages the overlay did not touch.
- 02 describes the trial as stock 0.8.3 plus the overlay. The installer's copy filter drops sdk/cli/arc1cli/core.py, tools/campaign_lib/core.py and games/struthio/src/core, then rebuilds the manifest to match.
- 02 offers 'test_desk_scenes passed all five tests on the installed app-v2' as proof. The module does have five tests, but the look they ran in is not stated, the campaign's own scene run cannot work from that copy, and no full suite run is reported.
- 02 does not mention that the Tab order of the writing line changes in pencil only (overlay.diff lines 1213-1216), nor that workspace_tabs.py changes start-up behaviour in every look.
- The package calls the copper-haired figure 'selected' and a reference file 'Approved', and the desktop choices 'agreed'. Our record holds no such decisions, and the figure that revision 2 actually installs is a different one from the 'selected' one.
- 02 treats 365 x 1200 as the comparison canvas. That is the R2 picture's size, not the place she stands in, which is 608:822 and at most 380 px tall at 14 pt (/home/user/Struthio/workbench/hologram.py:21-26).
- 02's install commands assume 0.8.3 is installed at ~/g83 on the ThinkPad with the USB at /mnt/graphite-8. Our record is that nothing later than 0.4.6 has run there.
- Checked and true: the zipapp's SHA-256, its 17 payload hashes against UPDATE.json, the five files changed between revisions 1 and 2, the R2 picture's size and alpha, and that the 16 base files match commit 951c789.

## Questions for the owner

- Do you want a third look before 0.9.0, knowing gates 1, 2 and 6 are written for two looks and each extra look adds about half again to every window pass and to your ThinkPad evenings? Or should Colored Pencil be the calm look for tired eyes already planned for 0.9.x?
- In Colored Pencil, is she Kasandra? If so, is 'Kasandra' still the right name for the indigo look in the Appearance menu?
- Do you want the word 'protocol' on the head? Your own wordmark reads 'kasandra protocol', the record has Graphite as the single public name, and you asked for the head's left to be freed.
- May the neon kp be shown as the bird alone, recoloured green, in this look? You said the neon kp is the only kp mark.
- Which figure is she in this look: the one revision 2 installs (the bob and face of your hologram) or the copper-haired one with glasses? Where was that art made and from what references, and may it sit under branding/ as your artwork?
- Should Approve be green and Stop always red in this look, or should what waits for you keep one colour of its own as in the other two looks?
- Do you prefer the word Send to the arrow? If so, should it change with the target (Ask, Run, Search, Open, Filter)?
- On the ThinkPad, did a second start of 0.8.3 work after closing it with the Office open? The code suggests it may fail.
- Has the Colored Pencil trial already been run on the ThinkPad? If so, from which folder, and what happened?
- Is 0.8.3 installed at ~/g83 on the ThinkPad, and are any model files kept inside that folder? The installer copies the whole folder.
