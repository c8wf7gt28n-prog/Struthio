# Graphite desk · the frame (HATCH DESK D1a), the panes and the pointer (D1b), the reviews' fixes (D1-fix), the cat, the programs list and the System menu (D2), the writing line and Log (D3), the right-click menu (D4), the network capability (D5, docs/NETWORK_01.md), the integration

The owner's brief of 2026-11-06: "I want a quieter, symmetrical desk with a powerful Fluxbox-inspired right-click menu. Keep
every useful capability reachable and put it where I would naturally look for it." Then: "Be obsessive in symmetry." This
page is the desk as built: the one grid, the two graphite bands, the head and the lower band's slots (D1a); the two panes,
their tabs, trees, Trash and faces, the quiet centre foot, the pointer and the quiet-script rule on the desk (D1b); and what
two independent reviews of D1 found and how each was fixed (D1-fix): the words, the cat, the symbol and Trash are now placed
and measured by what is drawn, not only by their boxes. How symmetry is measured, the measured tables, the homes of every
control that moved, and what was chosen and why. The cat's look, the programs list and the System menu (D2), the writing
line's four modes and Log (D3) and the right-click menu (D4) build on it; the network capability Log follows and the agent may
read (D5) is docs/NETWORK_01.md. "Where things went" is the short map of every displaced control, and "The integration" what
was found and fixed when the items ran together; the owner's review set is build/graphite_desk/review/ (tools/desk_review.py).
Nothing here is owner-host acceptance: the owner's computer is pending until the desk is tried there.

## The grid

```
  head band     | left slot  P | centre column: the eight menus, their ink on the line's ends | right slot  P |
  panes         |  left pane P | sep |            workspace (the remainder)              | sep | right pane  P |
  lower band    | left slot  P | centre column: the writing line                            | right slot  P |
```

- **One width for both panes.** `workbench/desk_qt.py` holds the grid as pure functions. For a window width, the interface
  scale (reading.ui_pt / 14) and the band lettering's line height, `desk()` returns one pane width P used for both docks,
  the workspace (the remainder, between two one-pixel separators), the band height and the insets. Both docks are fixed at P,
  so they are equal by construction; the workspace's left edge is P + 1 and its right edge W − P − 1, so its centre is the
  window's axis, and an odd pixel can only fall to the workspace.
- **P** is the owner's width (a drag, the Workspace setting layout.navigator_width, the saved session), else the default 360
  px at 14 pt (scaled with the interface up to 1.4: 463 at 18 pt, 504 at 20 pt); raised to what every lower-band word needs
  at full size and both panes' own content (D1-fix: each face's scrolled page included, `pane_qt.PaneBody.content_minimum`);
  never so wide that the workspace falls under its floor; and never under the slots' least need (D1-fix: their words at the
  floor size, 70% of full, with the gaps closed up).
- **The workspace's floor** is the one the old rules protected (V01 W1): 400 px at 14 pt, scaled up to 1.4 (514 at 18 pt, 560
  at 20 pt), or what the workspace's own content needs when that is more. At 1280 by 800 and 20 pt the panes' three tabs need
  374 px (Conversation whole at the tabs' floor size), so the workspace has 530 px there; Home fits it.
- **The drag.** Both panes are fixed, so Qt's own separator move cannot run; the desk reads the owner's hand on either
  separator (desk_qt.MirroredDrag) and moves both: the left edge dragged 40 px right makes both panes 40 px wider, the right
  edge dragged 30 px right makes both 30 px narrower, equal at every step of the drag. D1-fix: with both docks fixed Qt
  stopped showing the resize cursor over the separators, so the drag could not be found; the desk shows the horizontal resize
  cursor while the pointer is over either separator (`MirroredDrag.hover`) and the window's own pointer again off it. The width
  is the owner's from the release on and is saved for both (navigator_width and simulator_width); a saved width restores
  both; Arrange → Reset Layout forgets it. The setting layout.navigator_width keeps its key and words ("Left column width"); it
  sets both panes. No setting was added and no setting definition changed.
- **The two bands** (the head, shell2.TopBar, and the lower band, typebar_qt.TypeBar) span the whole window and are one
  height in Line mode: the taller of the cat (44 px at 14 pt, scaled) and a band word, with 8 px above and below (60 px at 14
  pt, 73 at 18, 78 at 20). Half and Tall grow the console above the lower band; the band keeps its height.
- **Three columns in each band.** The left slot and the right slot are each P wide, exactly over the panes; the centre column
  is the workspace with its separators.
- **One inset** (16 px at 14 pt, scaled): the drawn words nearest the window edges sit that far from them; the slot words
  nearest the workspace sit that far from the pane edge; the menus' ink and the writing line sit that far inside the centre
  column (a few pixels more when the menus' equal gaps leave some over: the writing line then takes the menus' own ink, so
  the two always match while the menus lie on the workspace column).

## Drawn by their ink (D1-fix)

The symmetry review measured the desk's pixels and found the boxes mirrored to the pixel while what was drawn in them was
not: the menu words' ink 7 to 9 px inside the writing line's ends, their drawn gaps 2 to 3 px apart, the cat's drawing 3 to 6
px further in than the last word's, Trash drawn at the left of a box wider than it. Now every band word, the cat and Trash
are placed by what they draw:

- **Band words** (the eight menus and ⋯ in the head; Line · Half · Tall and the target words in the lower band) are drawn by
  `desk_qt.InkWord`: the word's own text from a whole-pixel origin, in the band's lettering, no padding and no bold. Each
  word's ink is measured once per font and text (`desk_qt.ink_extent`: the first and last columns at least a quarter covered),
  and its box is its ink and 4 px of air each side (`INK_AIR`, scaled), so mirrored boxes put mirrored ink and the words'
  drawn gaps are their boxes' gaps and twice the air. Marks sit under the ink, exactly as long as it: eraser pink for an
  action under the hand, with keyboard focus or with its menu open; pencil yellow for the active choice. The active choice is
  no longer drawn bold: its mark says it, and a word that does not change weight never moves.
- **The cat** is placed by its drawing at rest (`graphite_brand.cat_ink`: the cat's parts as `paint_cat` draws them, in its
  tile): its first drawn column is the band's inset.
- **Trash** draws exactly its box (below).
- **The word Graphite** was already drawn by its outline (D1b); **the symbol** is the mark drawn as wide as its box.

The check (below) compares every one of them with its design in the window's own pixels.

## The bands

Both bands are shaded edge to edge like a graphite pencil: one tile (256 by 128 px) drawn once per run from a fixed integer
hash (the paper's tooth) under long light diagonal strokes that lean like hand shading and wrap at the tile's edges, so it
repeats without a seam. No random seed per run. The grain stays within ±7 levels of the mean tone #4a4741 (warm graphite, a
shade deeper than the ink #504d46). Each band paints the tile from its own top-left; both start at the window's left edge,
so wherever no word is drawn the head's pixels and the lower band's pixels are equal, and equal the tile's (measured: 2,820
pixels in 94 free columns, none different; mean lightness 69.955 in both).

| On the band | Colour | Contrast on the mean tone | On the lightest 5% of the grain |
|---|---|---|---|
| Lettering (erased paper) | #efeae0 | 7.72:1 | 7.48:1 |
| Quiet lettering (the monitors' key words, Find, Kernel) | #d2ccc0 | 5.79:1 | 5.61:1 |
| Action mark (eraser pink: hover and keyboard focus) | #cba5a4 | 4.17:1 | 4.04:1 |
| Active choice (the short pencil-yellow mark) | #d4b56a | 4.68:1 | 4.53:1 |
| The word Graphite in the script, as drawn (D1-fix) | #efeae0 | strokes' cores 7.5:1 at 14 pt, 7.65 at 18, 7.7 at 20; the median inked pixel 6.0, 6.5, 6.7 | |

Words are above 4.5:1 everywhere on the grain; the two marks are graphics (3:1). The script word is measured in the window's
pixels: each pixel's coverage is how far its lightness has moved from the grain under it toward the lettering's; the cores
are the pixels at least 90% covered, the median inked pixel is the median of those at least half covered (the check asserts
7:1 and 4.5:1). The workspace between the bands stays warm paper.

## The head

- **Graphite** alone at the upper left, pale, in the Paper script (Parisienne; the owner, 2026-11-06: "upper left Graphite
  should be cursive"), in the bands' erased paper with a hairline of the same paper round its outline (0.5 px at 14 pt) so the
  script's thin strokes hold on the grain. D1-fix: its size is the one at which its capitals stand exactly as tall as the
  symbol (`desk_qt.script_word_px`: the face's cap height equals the symbol's drawn height to within half a pixel): 33 px at
  14 pt, 43 at 18, 47 at 20 (D1b had chosen 34, 44 and 48 by eye; the capitals were half a pixel taller than the symbol).
  `shell2.Wordmark` draws it by its outline, so the widget is the word's ink: the ink's first column is the band's inset and
  the ink is centred in the band's height, on the symbol's centre line. With View ▸ Pleasantries in script off (or the face
  missing) it is IBM Plex Sans SemiBold, 22 px, placed the same way.
- **The menus** Work · Revise · Tools · Arrange · Commands · Rules · Properties · Guide, pale, 15 px at 14 pt (scaled with the
  interface, no ceiling), normal case, drawn by their ink. They lie across the workspace column with equal gaps, the first
  word's ink starting and the last word's ink ending exactly at the writing line's ends, centred on the axis (desk_qt.menu_row:
  the largest equal gap; with seven gaps an odd pixel is taken by one pixel less in every gap, so no box is widened). When
  they do not fit the column with their least gap, they are centred on the axis with that gap, reaching evenly into both head
  slots but never closer than a band gap to either slot's own words; only then the rightmost fold into ⋯ (G-B), which opens
  the same menus. With ⋯ the count of gaps can be even; an odd pixel then widens ⋯'s box and its ink is drawn a pixel further
  in, so the row's drawn ends stay mirrored and only the gap before ⋯ is a pixel wider (the check knows this one case). Folded
  now: Guide at 1366 by 768 and 20 pt, Properties and Guide at 1280 by 800 and 20 pt (D1a and D1b folded two or three at
  three sizes: the ink boxes are narrower than the old padded ones).
- **CPU · GPU · RAM · TXT** in four columns, each value beneath its key word (the key words in the quieter lettering), right
  of centre in the right slot, a band gap left of the symbol.
- **The System menu**: the single erased Graphite symbol at the far right (graphite_brand.paint_erased_mark: the sharpened
  point drawn in the bands' erased paper straight onto the shading), 32 px wide at 14 pt, at the band's inset from the right
  edge. Tooltip and accessible name System menu. D2: it opens the System menu (below, "The cat, the programs list and the
  System menu"); before D2 it opened the existing Nice list, whose rows are now that menu's process list. It is still `host.shell2.top.nice` (a NiceButton) for callers
  and checks. D1-fix: this list is now the work list's one home (Activity says what runs and waits in one line, below), so it
  reads the same snapshot Activity's list read (`ledger.operations`, a read: each queued row with its waiting reasons).
- **Rule 4's choice: the block moves to keep the centre.** The word Graphite and the monitors with the symbol cannot mirror
  each other, so the menu row is laid out on the workspace column by itself (its centre is the axis, measured 0 px at all
  nine sizes, by its ink) and the CPU block stays inside the right slot beside the symbol; its counterpart across the axis is
  the left slot's empty room after the word Graphite. **The mirrored pair of the head is the word Graphite and the symbol:**
  equal distances from the window edges (by their boxes, by the word's outline and by their drawn pixels), one centre line
  (the word's outline and the symbol's mark), and one optical size (the script's capitals as tall as the symbol). D1-fix: the
  pairs "the same top" and "the same height" are gone: they compared two band-high boxes and so always measured 0, and a
  script word has no height comparable with a symbol's (its swashes and descenders are not its size); its capitals are.

## The lower band

- **Left slot**: the cat, then Line · Half · Tall; **right slot**: the writing line's four modes Assignment · Shell · Search ·
  Log (D3; they replaced the target words Graphite · staC · Console · Find · Kernel, see "The writing line and Log").
  Each slot's items are spread with equal gaps (a remainder pixel goes to the gaps nearest the middle) from the band's inset
  to the pane edge's inset, measured to their ink: the cat's drawing at rest starts the band's inset from the left edge and
  the last word's ink ends the same inset from the right edge; Tall's ink ends and the first word's ink starts an inset from
  the panes' edges. The slot is generic (`TypeBar.rows()` and `items()` name its words); D3 puts Assignment · Shell · Search ·
  Log there.
- **One size for every band word and the writing line**, never elided (D1-fix: the review found Kernel and Find elided to
  "K…" and "Fi…" at three of the nine sizes, and the frame check had been loosened to let "Ke…" pass). The size is the
  controls' (16 px at 14 pt, 21 at 18, 23 at 20) or, in a window too narrow for every word whole with the gaps closed up, the
  largest size down to 70% of it that keeps them whole (`TypeBar.fit_px`, `desk_qt.letter_floor`): 19 px at 1280 by 800 and 18
  pt and at 1366 by 768 and 20 pt, 18 px at 1280 by 800 and 20 pt. The writing line takes the same size, so the line and the
  words keep one height and one baseline. The panes widen to the floor size's need before a word could ever be cut.
- **The cat** sits whole inside the band (D1-fix; the brief: "Every pose fits inside the band"): its tile is centred in the
  band's height (8 px above and below at 14 pt), it sits on its own ground inside the tile (`graphite_brand.GROUND`: nothing of
  it is drawn below; the ledge it used to peek over is gone, and keyboard focus is a short eraser-pink mark under it,
  `FOCUS_MARK`), and its button holds every pose (the hover tail reaches 1.4 px further left than the paws at rest, still
  inside). The check renders every pose and finds it inside the band with at least the band's padding above and below and
  nothing of it cut. D2 redrew it pale on the band (its coat the workspace's paper white, graphite eye and paw details, the
  owner's colours for its state; below), `cat_extent` inside `CAT_BOX` as test_desk asserts.
- **The writing line** spans the centre column with the menus' ink as its ends, centred on the axis.
- **One baseline.** Every band word is drawn from the writing line's own text baseline (`TypeBar.line_baseline`, the style's
  contents rect and Qt's vertical rule), and the words and the line are one height (the text line plus 22 px).
- **Explore** left the band (the brief: "Remove Explore from this row"). Its routes: the menu's Explore the workshop…, Tools →
  Explore capabilities…, and Explore under Activity's cabinet selection; D2 lists it in the programs list (its last row).
- **Ctrl+K** puts the cursor in the writing line in Search (D3; it replaced D1-fix's one-line Find lead `?`): Search is now one
  of the line's four visible modes, marked by the short yellow mark when chosen and remembered like any mode, so choosing it
  is seen, which is what the reach review missed when Find was a quiet word.

## The panes (D1b)

```
  left pane, P wide                                        right pane, P wide
  |  Machine   ·   Cabinet   ·   Settings  |  tab row       |  Conversation  ·  Activity  ·  Context  |
  |  the active tree, inset I               |  content       |  the active face, inset I               |
  |                              [ Trash ]  |  foot          |  [ kept empty ]                          |
```

`workbench/pane_qt.py` builds both panes from the parts the window already had (every object keeps its name for callers)
and lays each out by hand on whole pixels from the same numbers (`pane_parts`), so every part of one pane is the mirror of the
same part of the other.

- **The tabs.** Left Machine · Cabinet · Settings (in that order), right Conversation · Activity · Context. Three equal tabs
  share the room between the pane's insets (`tab_row`: no gap between them; any spare pixels split evenly between the two ends,
  so each row is centred on its pane and the left pane's first tab mirrors the right pane's last). One word size for all six
  (`tab_px`): the menus' size, or less in a narrow pane (down to 70% of it), so every word stays whole: 15 px at 14 pt; 19 px
  at 1920 by 1200 and 18 pt, 18 px at 1366 by 768, 16 px at 1280 by 800; 21 px at 1920 by 1200 and 20 pt, 16 px at 1366 by
  768 and 1280 by 800. The row's height follows the menus' size, so it never moves. The chosen tab is semi-bold graphite with
  the short pencil-yellow mark under it; the others are quieter graphite. The mark is one length under every tab of both panes
  (the shortest tab word, drawn bold, so it is never longer than the word above it), centred in its tab (`tab_mark`: one offset
  everywhere). Keyboard focus and the pointer put the eraser-pink mark in the same place. A faint rule runs under each row from
  inset to inset. The tabs are checkable push buttons under their old names: `settings_navigator.machine / .cabinet /
  .settings` on the left, `shell2.slate_button / .operations_button / .context_button` on the right.
- **The left pane shows only its tabs, the active tree and Trash.** Machine, the cabinet and Settings are `BranchTree`s: one
  row height (the tree's line of text and 12 px at 14 pt, scaled), one indentation (22 px at 14 pt, scaled), the same branch
  lines: a one-pixel pencil-grey line (#9d978b) down each level that still has rows to come, an elbow from the parent's line to
  the row (to its chevron, or toward its words for a row with nothing inside), a short stem from an open row's chevron to its
  first child, and the chevron (open or closed) in graphite. Roots stand on their own. A chosen row is marked over its words
  only (eraser pink); the branches stay on plain paper. Existing views (the older Library and catalogue tree, chosen from
  Arrange) draws the same lines.
- **Trash** is larger (a 30 px can at 14 pt, scaled; it was 22) and pinned at the left pane's lower right by its ink (D1-fix;
  the review and the integrator found the can and word drawn at the left of a box wider than them, short of the inner right
  inset). Its box is exactly what it draws, right to left: the word Trash's last inked column on the box's right edge, a pad,
  the can (its lid the widest part, its bottom line on the box's bottom edge), and room for a three-digit count to the left,
  so nothing moves when Trash fills (a count is drawn after the word, and the group still ends at the right edge). Placed an
  inset from the pane's inner edge and from its bottom, outside every scroll area, in every tab, the drawn Trash is there:
  measured in the window's pixels, its ink ends 16, 21 and 22 px from the pane's inner edge and above its bottom at 14, 18 and
  20 pt. Its counterpart place in the right pane's foot is kept empty: no right-pane control belongs at the foot, so the feet
  balance by height and by the empty mirror (the check asserts the right foot holds no control).
- **The right pane.** Conversation is the Graphite face (SlateFace): talking with the assistant, its answers and the Related
  lines. **Activity is quiet** (D1-fix; the integrator: "Activity is what Graphite did, what it got and what it needs"): the
  Work block on top while an assignment runs (working on, doing now, found, needs you, inspect), the services line, the
  Graphite line, the cabinet selection with Open record and Explore, one printed line for Graphite's own work (`WORK · 1
  running · 2 queued`, and the first item through the queue checks when there is one; `operations_qt.work_words`) with, under
  it in the script, where their order, niceness and Stop are, and Work list, which opens the System menu's list; AI admission;
  then the Timeline: its status line, its last five lines (each the trees' row height, shown whole; activate one to open it),
  Organizer, Return thread and Follow latest. The work list itself (Stop everything, a niceness slider on every row, the
  queue's order with Earlier and Later, Background CPU for owned work, Open Agenda, Work trail, and the long explanation of
  sliders and order) left the face for the System menu's list, where it already was (D2 rebuilds that menu); the explanation
  is that list's note and the WORK line's tooltip, not lost. The embedded list and the queue's explanation are kept, out of
  sight, for callers (`operations_panel.work`, `operations_panel.queue_hint`). Context is today's Context face (the files,
  selections and instructions in use). `show_slate_face`, `show_operations_face` and `show_context_face` work as before;
  Activity is the face at start.
- **No face is wider than its pane** (D1-fix; the review found Activity 40 to 70 px wider than the right pane at three sizes,
  its words cut at the window edge and a sideways scroll bar, because the pane's least width read the faces' scroll area, not
  the page inside it). The pane's least width now counts each face's scrolled page, shown or not (`PaneBody.content_minimum`),
  so the desk's P learns it; and Activity no longer holds the work list's widest control. The check asserts that nothing in
  either pane scrolls sideways and every word in it is whole, with each of the three faces, at all nine sizes.
- **The centre foot is quiet.** In Line the workspace reaches the lower band: the Timeline's line and its words moved to
  Activity (and D3's Log mode). A status message still shows there while it lasts (`TypeBar.note`), and Half and Tall open the
  console there as before (its Log page is the Timeline). The workspace never asks the window for more height than it has
  (`pane_qt.CENTRE_MIN_HEIGHT`, its pages scroll or yield inside it), so its top and bottom are always the panes' top and
  bottom, whatever page is open.

## The pointer (D1b)

The brief: "Use the two facets of the Graphite mark for the pointer. Aim it at 11 o'clock, 30 degrees left of vertical, with
the click at the tip." `graphite_brand.pointer_shape` turns the mark's two wedges (UPPER and LOWER; the short stroke past the
tip is left out, since nothing may lie beyond the click) about the point so that the mark's own aim, the bisector of its two
outer edges (13.58 degrees below the horizontal in the mark), points 30 degrees left of straight up, and scales them alike so
the farthest corner is 22 px from the tip. The tip is the hotspot exactly (2, 2) in a 32 px image, at 1x and 2x; the hotspot's
own pixel is drawn solid graphite (a sharp point covers only a sliver of the pixel it starts in), so the point is crisp and
the click visibly on it. Graphite facets with a one-pixel paper edge (also between the facets, along the mark's gap), so it
reads on paper and on the graphite bands. `use_pointer` sets it on the window: every widget that sets no cursor of its own
shows it (the trees, the tabs, the bands, the workspace); text fields keep their I-beam, splitters their resize cursors, links
and Trash their hand, and the pane separators show the resize cursor while the pointer is over them (D1-fix). Menus and
dialogs are their own windows and keep the system's pointer. `tests_integrated/test_desk.PointerTests` checks the hotspot is
the tip and the aim is 30 degrees (to 1e-9), that nothing lies beyond the tip and that the facets are the mark under one
similarity; `test_graphite` checks the drawn pixels at 1x and 2x.

## The quiet-script rule on the desk (D1b, D1-fix)

The owner, 2026-11-06: "Don't we like cursive font for 'less necessary to read' text" and "upper left Graphite should be
cursive". The rule was already the program's (`shell2.quiet_script`, `pleasantry`, `QuietNote`): print for what you read first
and act on (menus, words to act on, file names, values, status, warnings, prose); the Paper script for the quieter words
around it (a corner note, a greeting, a signature, an explanation you may skip) and for a little grace; numbers stay printed;
View ▸ Pleasantries in script (the setting appearance.cursive, unchanged) turns the script off everywhere. On the desk:

| Where | In the script | Stays print |
|---|---|---|
| The head | the word Graphite (`shell2.Wordmark`), its capitals as tall as the symbol | the menus, the monitors, the symbol |
| Left pane | nothing: its visible words are the tabs, the tree's rows and Trash, all things you act on or read first | the tabs, every row, Trash |
| Activity | the cabinet selection's explanation when nothing is selected ("Select saved work in the cabinet…"); where the work's order, niceness and Stop are, under the printed WORK line | the services, the Graphite line, a selected record, the WORK line, the action words, the Timeline |
| The System menu's list | the captions after ACTIVE JOBS ("in the order they started") and QUEUED ("drag to schedule"); the sliders' and order's explanation (one print size with the rest when the script is off: D1-fix, it was a stray 13 px) | the headings, the job rows, Stop everything, the statuses and results |
| Conversation | the face's signature (as before); the composer's hint (hidden while the writing line is the way to write) | its line, the agenda line, every message |
| Context | a room's note you may skip (`shell2.Note`): the Files room's Open note and the viewer's Read-only note, with the keys in them printed (`quiet_html`) | every value, name, count and the rest of each room's rows |
| The workspace (D1-fix; the review found these in print) | Today's capture hint "Ctrl+Enter keeps it · Ctrl+Shift+N from anywhere" with its keys printed (a result of keeping is print); the Files room's explanation "Open anything read-only…"; the greeting and the cards' corner notes (as before) | Today's titles, values and statuses, the Files room's words to act on |

`shell2.QuietWords` is the one label for words that are, by turns, a status (setText: print) or an explanation (explain: the
script after a printed lead, on the same line or under it); a note with a digit stays print; the keys in a note stay print
(`quiet_html`); it follows the interface size (the script 1.3 times the print size, never under 19.5 px at 14 pt) and the
switch. **No script word is cut by its label** (D1-fix; the review found Parisienne's S, E and i cut flat at the label's left
edge): every script label keeps room round the script's swashes (`shell2.script_room`, word by word, since any word may start
or end a wrapped line: the left overhang of its first letter, the right overhang of its last, a descender below the line's
descent, each with a pixel of air). QuietWords sets the room as the note's block margins, a hanging indent when a printed lead
starts the same line (the lead stays on the column's edge, the script's wrapped lines are inset); `quiet_script` and
`pleasantry` set it as the label's padding. The check draws every visible script label again with room round it and finds no
ink outside the label's own rect (the Today greeting lost 26 px of its G before; a corner note 2 px). Turning the switch
re-styles them, the word Graphite and the Context face at once (control_qt).

## Symmetry, measured

`tools/symmetry.py` reads live widget geometry in window coordinates and returns every difference in pixels: `pair` (a box on
the left mirrors one on the right: outer distance, inner edge, width, top, bottom, height, vertical centre), `centred` (a
box's centre on the axis), `same` (values that must be equal: heights, gaps, edges, insets), `baseline` (a word's baseline
as Qt places it, or as `InkWord` draws it), `span` and `gaps` (a row), and (D1-fix) `within` (a value measured from drawn
pixels against its design) and `at_least` (room that must reach a floor). `tools/check_desk_ui.py` builds the real window
offscreen with the holds and asserts zero for every row below at 1920 by 1200, 1366 by 768 and 1280 by 800, each at 14, 18
and 20 pt, with every word whole (tools/ui_fit) and nothing in the workspace or either pane scrolling sideways (Home: the
Finder with Today).

**Laid out (boxes and designed ink):**

- Panes: outer, inner, width, top, bottom, height, vertical centre; the workspace's centre on the axis; the panes' contents
  inset alike.
- Bands: one height in Line mode; each band centred on the axis and the full width; the head's two slots and the lower band's
  two slots mirrored; the workspace column's left and right edges the same in the head, the lower band and the panes; at the
  left edge the word Graphite's outline, the cat's drawing at rest and the band's inset equal; at the right edge the symbol's
  mark, the last word's ink and the band's inset equal.
- Head: the word Graphite and the symbol (outer, vertical centre); the word's outline at the band's inset and on the symbol's
  centre line; the optical size (the script's capitals and the symbol, as tall, to within half a pixel); the menu row's boxes
  centred with equal gaps and the band's height; the menus' ink with equal gaps (the one parity pixel before ⋯ named) and
  centred on the axis; while they lie on the workspace column, their ink's ends and the writing line's ends.
- Lower band: the cat's drawing at rest and the last word's ink (outer); Tall's ink and the first word's (inner), both an inset
  from the panes' edges; the writing line centred and equally inset in the workspace column; one baseline; one height; one
  size for every word and the line.
- The panes (D1b): pane bodies, tab rows, each tab with its mirror, the tabs' widths, tops, heights, gaps and word size, each
  row centred on its pane, the short mark's length, offset and row, the content boxes and their inset, the feet, Trash and its
  kept-empty mirror, Trash an inset from the pane's inner edge and its bottom, no control in the right foot; the three trees'
  box, indentation, row height and branch column; Activity's lines at the trees' row height and shown whole.

**As drawn, in the window's own pixels (D1-fix):**

- **Drawn as designed** (`drawn_as_designed`): the word Graphite (its outline and hairline), the symbol, every shown menu word,
  every lower-band word, the cat at rest and Trash are drawn again by the check from their designs, by references it takes when
  it starts (so a later change to a painter is measured against them, not copied), over the same ground, and compared with the
  window's pixels: at most 2 levels apart (rounding). Measured: 0 levels for all twenty items at all nine sizes. A pixel's shift
  of any of them leaves its box where it was and differs by tens of levels.
- **The word and the symbol** as drawn (D1b): their first and last inked columns at equal distances from the window's edges.
- **The chosen tabs' yellow marks** (`tab_marks`): the pencil-yellow run under the chosen tab of each pane, its length and row
  equal, and, Cabinet and Activity being mirror partners, mirrored to the pixel.
- **Trash** (`trash_drawn`): its ink ends an inset from the pane's inner edge and an inset above the pane's bottom (0 px).
- **The cat** (`cat_poses_inside`): every pose (rest, hover, open, sleepy) rendered alone lies inside the band with at least the
  band's padding above and below, the button's edges cut nothing of it, its drawn edges are its design's to within a pixel of
  antialiasing, and its design lies inside the tile's room. Measured at 14 pt: 10 px above and below at rest, the sleepy head
  3 px lower.
- **Script whole** (`script_labels`): no visible script label has ink outside its rect (0 px clipped, every label, every face).
- **The script's contrast** on the band (`script_contrast`): above.

**At every size, beyond the default face** (D1-fix; the review found the right pane checked with Activity only, and Half, Tall
and the System menu's list at one size): with Conversation and with Context the right pane's pairs hold, its words are whole,
its script whole and nothing in it scrolls sideways; Half and Tall keep every desk pair; the System menu's list opens under the
symbol, its right edge the band's inset from the window's and its top the band's foot.

| Size | Both panes P | Workspace | Band | Inset | Menus' ink and line inset | Band words | Menus | Rows | Largest difference |
|---|---|---|---|---|---|---|---|---|---|
| 1920 × 1200, 14 pt | 360 | 1198 | 60 | 16 | 19 | 16 px | all eight | 200 | 0 |
| 1366 × 768, 14 pt | 360 | 644 | 60 | 16 | 22 | 16 px | all eight | 200 | 0 |
| 1280 × 800, 14 pt | 360 | 558 | 60 | 16 | 21 | 16 px | all eight | 200 | 0 |
| 1920 × 1200, 18 pt | 463 | 992 | 73 | 21 | 26 | 21 px | all eight | 200 | 0 |
| 1366 × 768, 18 pt | 415 | 534 | 73 | 21 | line 21; the menus reach into the head slots | 21 px | all eight | 198 | 0 |
| 1280 × 800, 18 pt | 372 | 534 | 73 | 21 | line 21; the menus reach into the head slots | 19 px | all eight | 198 | 0 |
| 1920 × 1200, 20 pt | 504 | 910 | 78 | 22 | 25 | 23 px | all eight | 200 | 0 |
| 1366 × 768, 20 pt | 386 | 592 | 78 | 22 | line 22; the menus reach into the head slots | 19 px | Guide in ⋯ | 198 | 0 |
| 1280 × 800, 20 pt | 374 | 530 | 78 | 22 | 15 | 18 px | Properties · Guide in ⋯ | 199 | 0 |

"Rows" counts every row measured at that size in step 01 (laid out, as drawn, the cat's poses, the script labels on screen,
the contrast): it varies with the menus' place and the script labels visible. "Largest difference" is in pixels for the
geometric and drawn-edge rows and in levels for the drawn-as-designed rows. Before D1-fix: 127 pairs at each size by boxes,
the drawn items unmeasured; the review's own mutations (the symbol drawn a pixel lower, the word drawn a pixel lower, the right
pane's yellow mark drawn a pixel right, the Trash can drawn a pixel left) passed it.

| Size | Tab width (no gap) | Tab words / menus | Tab row (in the pane) | Short mark (offset, length) | Tree row / indent | Trash box | Foot |
|---|---|---|---|---|---|---|---|
| 1920 × 1200, 14 pt | 108 | 15 / 15 px | 18 – 342 | 28, 52 | 32 / 22 | 95 × 29 | 53 |
| 1366 × 768, 14 pt | 108 | 15 / 15 px | 18 – 342 | 28, 52 | 32 / 22 | 95 × 29 | 53 |
| 1280 × 800, 14 pt | 108 | 15 / 15 px | 18 – 342 | 28, 52 | 32 / 22 | 95 × 29 | 53 |
| 1920 × 1200, 18 pt | 139 | 19 / 19 px | 23 – 440 | 36, 67 | 43 / 28 | 124 × 37 | 68 |
| 1366 × 768, 18 pt | 123 | 18 / 19 px | 23 – 392 | 30, 63 | 43 / 28 | 124 × 37 | 68 |
| 1280 × 800, 18 pt | 110 | 16 / 19 px | 21 – 351 | 27, 56 | 43 / 28 | 124 × 37 | 68 |
| 1920 × 1200, 20 pt | 152 | 21 / 21 px | 24 – 480 | 39, 74 | 47 / 31 | 134 × 40 | 73 |
| 1366 × 768, 20 pt | 114 | 16 / 21 px | 22 – 364 | 29, 56 | 47 / 31 | 134 × 40 | 73 |
| 1280 × 800, 20 pt | 110 | 16 / 21 px | 22 – 352 | 27, 56 | 47 / 31 | 134 × 40 | 73 |

The tab row's height is the menus' line and the band words' chrome: 41 px at 14 pt, 46 at 18, 50 at 20. Trash's box is its
drawing (D1-fix), so its feet are lower than D1b's (70, 90 and 97 px).

**The mutation proof** (D1-fix, in the evidence folder, not shipped): each fixed defect's old behaviour and each of the symmetry
review's own mutations is put back for a moment against the check's measures; all 21 are caught and the desk measures clean
again after each: the symbol drawn 1 px lower or left, the word drawn 1 px lower, the right pane's yellow mark drawn 1 px right,
the Trash can drawn 1 px left; the symbol, the Conversation tab, the last mode word and Trash moved 1 px; the script without
room round its swashes; Trash drawn at the left of its box; the cat at the band's foot; the writing line at the menus' boxes;
the word at its old 34 px; Kernel elided; the separators without their resize cursor; Ctrl+K choosing Find and keeping it; the
System menu's note at 13 px; the lower band's words at full size in a narrow window; Activity wider than its pane.

Captures for the owner, in build/graphite_desk/ (desk-ui.json holds every row of the tables above, the drawn-as-designed
levels, the cat's poses, the script labels and the script's contrast at each size):
`Graphite_Desk_01_1920x1200.png` and `Graphite_Desk_02_1366x768.png` (the desk with both launch menus closed),
`Graphite_Desk_03_Symmetry_Overlay_1920x1200.png` (the axis in pink, the mirrored guides in dashed yellow: the band insets,
the pane edges, the workspace column's inset that the menus' ink and the line share, the band edges),
`Graphite_Desk_04_Symmetry_Overlay_1280x800_20pt.png` (the tightest case, the band words at 18 px),
`Graphite_Desk_05_Left_Pane_Tabs_1920x1200.png` (the left pane with Machine, Cabinet and Settings chosen, each cut from the
window grab), `Graphite_Desk_06_Right_Pane_Tabs_1920x1200.png` (Conversation, Activity and Context), `Graphite_Desk_07_Pointer.png`
(the window with the cursor image drawn at its hotspot over the cabinet tree, and the pointer at 1x on paper and 2x on the
band, enlarged, with the hotspot's pixel and the aim marked), `Graphite_Desk_08_Quiet_Script_1920x1200.png` (the head's left
slot over Activity, cut from the window: the word Graphite and the panes' notes in the script; beside it the same with View ▸
Pleasantries in script off).

The check also measures: the two bands' grain (above); Line, Half and Tall (the console 30, 312 and 504 px at 1920 by 1200;
the lower band stays 60 px at the same place; the pairs stay 0 px); the separators' resize cursor; the drag (360 → 380/380
halfway → 400/400, then 385/385 halfway → 370/370), an excursion to 18 pt and back keeping the owner's width, the session saving
370 for both and the reopened window restoring 370 on both sides; Ctrl+K; the System menu's symbol, its list and the Game word.

## Choices, and why

1. **Both docks fixed at one width, the drag read by the desk.** Letting Qt move one separator and copying the width to the
   other leaves the panes unequal while the hand moves and rounds one short on some resizes; fixing both makes equality a
   property of the layout, and the mirrored drag keeps the owner's gesture (D1-fix: with its resize cursor).
2. **The default 360 px at 14 pt, scaled.** It is the mockup's proportion at 1920 (about 19% of the width per pane), between
   the old left (360) and right (400) columns; the old shipped pair (285 / 330) is read as no owner's choice, so a fresh
   profile gets 360.
3. **The workspace's floor is kept.** Under it the panes give up width first (D1-fix: the lower band's words are set smaller,
   the gaps close up; nothing elides), so Home and the Finder still fit at 1366 by 768 and 1280 by 800 at 18 and 20 pt.
4. **One inset everywhere, and the menus justified across the workspace.** The brief asks that the head's menus and the
   writing line align to the workspace "with matching insets"; spreading the menus across the column with equal gaps makes
   their drawn ends the line's ends. At 1920 the gaps are wide (the words read like a ledger's column headings).
5. **Menu words at 15 px (14 pt), following the interface size.** At 16 px all eight did not fit at 1366 by 768 and 18 pt (the
   likely size on the owner's ThinkPad); at 15 px they do. At 20 pt in a window of 1366 or less the rightmost fold into ⋯
   rather than clip.
6. **The monitors stay in the right slot** (rule 4: "the block moves to keep the centre"): see The head.
7. **The script for the word Graphite, with a hairline (D1b; it reverses D1a's choice), sized by its capitals (D1-fix).** The
   owner asked for the script ("upper left Graphite should be cursive"), and the program's own rule agrees (the script is for a
   little grace and the quieter words; the word is not something you act on). A 0.5 px hairline of the same pale paper round
   the outline keeps the strokes whole on the grain without making the word bold. D1b chose 34 px by eye; D1-fix makes it the
   size at which the capitals stand as tall as the symbol, so the head's two ends match in the size the eye reads.
8. **A quiet grain** (±7 levels, fine diagonal strokes): visible as pencil shading at full size, quiet enough that the quiet
   lettering keeps 5.6:1 on its lightest places.
9. **Explore left the band now**, with its routes kept (above); the old head mark's game moved to the System menu's list
   (Game) until D2 makes Game that menu's first row.
10. **Three equal tabs sharing the pane, no gap (D1b).** The brief's "three tabs in evenly spaced positions": equal tabs that
    fill the room between the insets put the words' centres evenly apart and give the longest word (Conversation) the most
    room; a gap would only take room from the words (the tabs have no box to separate).
11. **One word size for the six tabs, smaller rather than wider (D1b).** At 1280 by 800 and 18 or 20 pt the panes are at the
    width the workspace's floor allows; the menus' size would need wider panes (or an elided Conversation), so the tab words
    take the largest size that keeps every word whole in both panes, down to 70% of the menus' size.
12. **The short mark is the shortest word's length (D1b).** "The active tab's yellow mark the same length and offset": one
    length under every tab means it cannot be each word's own width; the shortest word's keeps it short and never longer than
    a word.
13. **Details in tooltips, not a pane (D1b).** The brief makes the tabs, the tree and Trash the left pane's only visible
    controls. A row's description (source, time, values) is where the pointer already is; the right pane's Context keeps its
    meaning (what is in use in the work).
14. **The Work block in Activity (D1b).** It says what Graphite took on, is doing, found and needs: the brief's words for
    Activity. The Conversation stays the talk.
15. **The foot's "Work trail" says Organizer (D1b).** That word opened the Organizer; in Activity, beside the work list's own
    Work trail, the same word for two rooms would mislead. Both rooms keep every route.
16. **Trash's mirror stays empty (D1b).** The right pane has no foot control in the brief; an empty foot of the same height
    keeps the panes' contents mirrored, and nothing is invented to fill it.
17. **The pointer's tip is the hotspot pixel's corner, its pixel solid (D1b).** The click is exactly at the point, and the
    point reads at 1x where a sharp 21-degree facet alone would draw its first pixel pale.
18. **Words, the cat and Trash placed by what they draw (D1-fix).** The owner asked for obsessive symmetry and the review measured
    the pixels: boxes mirrored to the pixel with their contents 3 to 9 px apart is not symmetry the eye sees. Measuring each
    word's ink once per font and text (rendered from a whole-pixel origin, so the window draws exactly that ink) costs nothing at
    layout time and makes the drawn pairs exact; the check proves it by drawing each item again from its design.
19. **Band words drawn regular, the choice shown by its mark (D1-fix).** A word drawn bold when chosen changes its ink by a pixel
    each side, so a mirrored pair would hold for one choice and not the next; the brief asks for "a short yellow mark for active
    choices", which says it alone.
20. **Smaller, never elided, for the lower band (D1-fix).** The rule the tabs already followed (choice 11): at 1280 by 800 and 20
    pt every word fits at 18 px; an elided "K…" is a word lost. The writing line takes the same size so the band keeps one
    height and one baseline.
21. **Activity quiet; the work list's one home is the System menu's list (D1-fix).** The integrator: the list's long explanation
    and its controls read as a wall of text, and the process list moves to the System menu with D2. It already opened from the
    symbol; Activity keeps one printed line (what runs and waits) and a script note where the rest is, and the list now reads
    the same snapshot so its rows keep their waiting reasons. Its widest control left the face with it, which is also what made
    the right pane overflow.
22. **The pane learns its faces' scrolled pages (D1-fix).** A scroll area reports a small minimum whatever its page needs, so the
    desk could make the pane narrower than its content; counting each face's page (shown or not, so the width does not change
    with the tab) is the root fix, and the check asserts no sideways scroll in either pane with every face.
23. **The head's mirrored pair by centre and optical size (D1-fix).** The integrator allowed it where equal height no longer makes
    sense: the old "top" and "height" pairs compared two band-high boxes and always passed; the script word's descenders and
    swashes are not its size. Its capitals are what the eye compares with the symbol.
24. **The cat whole on its own ground, centred in the band (D1-fix).** The brief: "Place the unlabeled cat entirely inside the
    lower-left shaded band … Every pose fits inside the band." The tile was pushed to 3 px above the band's foot and the cat
    peeked over a ledge drawn in graphite on graphite, so it read as cut off by the band's edge. Its look is D2's; its room is
    the desk's: the tile centred with the band's padding, every pose inside, asserted at nine sizes.
25. **Ctrl+K as a one-line Find (D1-fix).** Keeping Find chosen after one Ctrl+K sent the next words, and the next start, to
    Find. The band's own first-character jump (`?`) does exactly "find this line" and changes nothing else.
26. **Room round the script, word by word (D1-fix).** The font's own least side bearing is 8 px (the j's swash), far more than any
    word starting a line here needs (1 to 3 px); measuring the note's own words keeps the script on the column's edge.

## The writing line and Log (D3)

The brief: "Erase one long, flat writing line into the lower band with a light poem placeholder. Give it four modes and show
which is active", and the owner on the first mode: "We could simply call the Ai assistant/agent 'Assignment'". Then, on Log:
"Instead of log notes, let's have network. And we should probably add a network traffic scanner or packet sniffer capability
that the agent can inspect", and to be exact: "I meant log notes replaced with network". So the line keeps its four modes,
Log keeps following events and its notes feature is gone: in its place Log follows the network. The code: `typebar_qt.py`
(the modes, Ctrl+Enter, Ctrl+K, the line's quiet word), `shell2.py`'s OneBox and ResultsPopup (Enter, the first-character
jumps, the results under the line), `console_qt.py` (the working area's pages), `log_qt.py` (the Log view), `menus2.py`
(Commands ▸ Run an operation…, Commands ▸ Writing Line).

**The line.** One long, flat line on the band's erased paper (no frame, square ends), centred on the axis with the menus' ink
as its ends; keyboard focus is an eraser-pink rule along its foot, the paper unchanged (so the cat's white coat stays the
band's brightest value), with the same chrome above and below in both states so its text never moves. The placeholder is the owner's writing invitation `poem` (the Interface Companion of 2 November, every
writing field's word), in the quiet graphite (`POEM_INK` #6c675e, shell2's QUIET): lighter than typed text (7.03:1) and legible,
4.68:1 on the line's erased paper (D3-fix: the first light grey #9d978b was 2.42:1, under the desk's 4.5:1 floor for quiet
lettering; check_desk_ui step 12 measures its darkest drawn pixel). Its quiet word at the right end says, by turns, the active work
context (as before), "staC on Ctrl+Enter" while the typed line parses as staC, and in Log the stream's one-line summary.

| Mode (key) | Enter | Ctrl+Enter | The working area above the band (Half, Tall) |
|---|---|---|---|
| **Assignment** (`slate`; Alt+1, Alt+2) | The words go to Graphite exactly as the Graphite target did (`Shell2.ask`; the answer in Conversation). A line that parses as staC also goes to Graphite: **plain Enter never runs staC** | Typed staC runs through the staC target's own path: `shell2.to_console('stac')` → `Console.run_stac` → `stac.run` (a staC word) or `language.run` (a pipeline), through Kernel.dispatch with the same checks | The console's answers: staC tables (save as a sheet, watch it, add to the Agenda), `/` operations |
| **Shell** (`shell`; Alt+5, `$`) | The line goes to the configured shell, in your Files folder | as Enter | The shell's output (Stop and Master Stop end it; each command noted in the Timeline) |
| **Search** (`find`; Ctrl+K, Alt+4, `?`) | Searches the workspace: files and their words (`files.find`), received files, the cabinet, settings, commands and the Timeline, each with open | as Enter | The search's sections; under the line as you type: the search itself first, then files, cabinet records, settings and commands by name, each opening where it belongs |
| **Log** (`log`; Alt+6) | Filters the chosen stream with the line's words | Network: starts a capture with the line's filter (asks first, once a run); Events: filters | The Log view: Events or Network (below) |

- **Which shell.** The configured shell is the account's login shell from the account database (what `chsh` sets, Debian's
  configured shell for the user), else `$SHELL`, else `/bin/sh`; a shell that refuses logins (`nologin`, `false`) or is not
  an executable file is passed over (`typebar_qt.configured_shell`). The mode's word is **Bash** only when that shell's file
  name is `bash` (`shell_label`), otherwise **Shell**; it runs the line as `shell -l -c LINE` where the shell takes `-l`
  (`shell_argv`; before, the console always ran `/bin/bash -lc`). In this container the configured shell is `/bin/bash`, so
  the word reads Bash.
- **When a line parses as staC** (`typebar_qt.parses_as_stac`; nothing runs to decide it): an `@address` pipeline whose
  address parses, a program led by a staC word (`library`, `desk`, `map`…) that compiles (`stac_bridge.compile_program`), or a
  typed pipeline whose source is a registered read-only operation (`files.list`, `files.list | rows`), the rule
  `stacy_language` applies when it runs. Words such as "show me the files" never parse.
- **Keys, prefixes, shortcuts and histories kept.** The old targets map to the modes (`MAPPED`): `slate` and `stac` →
  Assignment, `shell` → Shell, `find` → Search, `kernel` → Assignment with the `/` lead (Commands ▸ Run an operation…). The
  remembered target (`type_target` in the session) is kept and mapped the same way at start; Log is remembered too, and so is
  Log's stream (`log_stream`; `session.py` now reads both back). The lead characters keep their meaning: `@` staC and `/` an
  operation (in Assignment), `?` Search, `$` Shell; typed as the first character of an empty line they choose the mode (`?`
  and `$` are then not part of the line; `@` and `/` are). In Shell every character is the shell's: `/usr/bin/env` and
  `?.txt` reach the shell (before, a `/` line in the shell target went to the Kernel). Up and Down walk each page's history,
  Tab completes operations, their arguments, staC words and `@files:` paths, as before. In Assignment, Up and Down on an empty
  line walk typed staC's history (the old staC target's: what Ctrl+Enter ran), and a recalled line walks on (`OneBox.history_page`;
  D3-fix: an empty Assignment line had no page, so the staC history could not be walked, and after `@` the walk stuck on the
  newest program); `/` walks the operations', and typed words keep Up and Down for the results under the line. Alt+1…Alt+5 keep their old targets'
  places (Alt+1 Assignment, Alt+2 staC → Assignment, Alt+3 Kernel → Run an operation…, Alt+4 Search, Alt+5 Shell); Alt+6 is Log.
- **Explore and Kernel left the strip.** Explore's useful actions: the programs list's Explore the workshop (D2), Tools ▸
  Explore capabilities…, and the right-click's capabilities for the thing under the pointer (D4). Kernel's: **Commands ▸ Run
  an operation…** (Alt+3, its old key): the line in Assignment with the `/` lead; Tab completes an operation's name and
  arguments, Enter runs it (an approve-scope operation asks for a second Enter), `help NAME`, `ops WORD` and `history` answer
  in the working area. Assignment's typed staC (Ctrl+Enter) is the other half of what the Kernel word was used for.
- **Choosing a mode never opens or closes the working area**; running a line opens it at Half; Line closes it. (Before, every
  target but Graphite forced Half.)

**Log.** The working area above the band, at Half or Tall, follows a stream chosen with two small tabs at its top, **Events**
and **Network** (print words, the short yellow mark under the chosen one); the choice is remembered. In Line, the line's quiet
word is the stream's one-line summary ("Events · 14:03:22 Saved bench.txt", "Network · eth0 ↓ 1.20 Mbit/s ↑ 96.0 kbit/s · 12
connections · capture idle"). The view reads only while the line is in Log.

- **Events**: Graphite's events from the activity journal, read through Kernel.dispatch of `ledger.journal.status` and
  `ledger.activity` (observer reads, never recorded), in the Timeline's words (`tail_words.readable`), newest at the bottom
  with Follow latest (reading back by wheel or scroll bar stops following). Words in the line and Enter filter it (the
  journal's own query). **There are no notes**: the view has nothing to write in (the check asserts no text field in it).
- **Network**: this computer's network as D5 observes it, read **only** through Kernel.dispatch of D5's four operations
  (`log_qt.NETWORK_OPERATIONS`; `LogView.network` refuses any other): `network.observe {filter?}` every two seconds (the
  interfaces with their receive and send rates, shown as bits per second, the contract's `rx_bps` and `tx_bps`; the open
  connections: protocol, local and remote address and port, state, the process and its id when known), and while a capture
  runs `network.capture.read {after, filter, limit}` every second (the packet stream: time, interface, protocol, source →
  destination with ports, length, TCP flags), newest at the bottom with Follow latest. When a capture ends between two reads
  (its seconds or packets reached), the view reads once more as soon as it sees it ended, so its last packets appear
  (`LogView.following`; D3-fix: they were lost when the next look was an observe); a read that leaves packets behind (D5's
  `rest`) reads on. The connections' count says when D5 matched more than it returns ("CONNECTIONS · 500 of 812"). Until D5's
  operations are registered the view makes no call and says "The network capability is not in this build yet".
- **The filter grammar** is D5's own (`network_watch.parse_filter`, `matches`, `bpf`; `log_qt.parse_filter`, `matches` and
  `capture_filter` call them), said in the line's hint: a host (an address, a network such as `10.0.0.0/24`, or `localhost`,
  which is 127.0.0.1 and ::1; a name with a dot is never looked up, so it matches nothing and says so), a port (`443`, `:443`,
  `port 443`, or `10.0.0.5:443` for both), a protocol word (`tcp` also matches `tcp6`; `udp`, `icmp`, `arp`, `ip6`…), a
  connection state (`listen`, `established`…; it narrows connections, not packets), any other word a process or user name or a
  port's service name, in part (`proc X`, `ssh`). Words of one kind widen (`port 80 port 443`: either), kinds narrow (`host
  10.0.0.5 tcp`: both). The owner's words go to D5's operations as typed (`filter`), and the view applies the same functions to
  what comes back, so it shows exactly what the capability selected; the errors D5 gives for the words (its own parse, and
  `result['filter']['errors']` with an answer) are shown beside the filter. D3-fix: the view had a grammar of its own and hid
  rows D5 had returned for `localhost`, a service name, or a state on packets; one grammar now, and the real capability agrees
  row for row (D3-fix probe/real_network.out).
- **Capture** is the owner's own action: Ctrl+Enter in the Network stream (or Capture… in the view's head) starts
  `network.capture.start {filter, seconds: 60, packets: 2000}`. The first capture of a run asks first, saying exactly what is
  captured: headers only (addresses, ports, protocol, length, TCP flags, never what the packets carry), this computer's own
  interfaces, not in promiscuous mode, for at most 60 seconds or 2000 packets, that nothing leaves the computer, and the filter
  as the capture tool receives it (D5's own capture filter: `localhost` is `host 127.0.0.1 or host ::1`; words that name no
  host, port or protocol select every packet and are applied as the packets are read; a state narrows connections, not packets).
  Words D5's grammar refuses (a name, a socket kind such as `raw`) are said before anything is asked or started, and a refusal
  from the capability itself (`NETWORK_CAPTURE_STOPPING`, an interface it does not know) stays in the stream, in its words,
  until the next capture or filter ("Not captured"; D3-fix: the refusal was overwritten at once by the idle note, and the
  confirmation showed a capture filter of the view's own that D5 does not use). While idle, a capture Graphite proposed during
  an assignment is shown in D5's words for the owner to start. Stop capture ends it (`network.capture.stop`); Master Stop also
  ends it (D5's tracked command). When capture is unavailable the stream shows D5's reason and how the owner can enable it,
  word for word, and offers nothing (never sudo).
- **Pinning**: choosing an entry in either stream pins it at the top with its details (it stays while the stream scrolls and
  refreshes; the note's place is the pin's). Its words: **Ask Stacy about this** (the line in Assignment with the entry as
  the assignment's context, the cursor after it, e.g. "About this network connection (tcp 192.0.2.10:51412 →
  198.51.100.7:443, ESTABLISHED, test-browser pid 4242): "), **Follow this conversation** (network: the stream filtered to the
  far host and its port) and **Unpin**.
- **For D4's right-click** (`log_qt`): `entry_at(widget, point)` is the entry under a point of the Log view or None (a dict
  with `stream` `events` or `network`, for the network `kind` `connection` or `packet`, and the entry's own fields; an event
  has `kind` `event` and the journal event under `event`); `focus(host, entry)` puts the line in Log on that entry's stream
  with the entry pinned (a network entry's stream filtered to its conversation, the filter in the line too; the area opens at
  Half from Line); `ask_about(host, entry)` puts the assignment in the line; `conversation(entry)` is the filter it uses.

**Symmetry.** The mode words and Line · Half · Tall are placed by their ink as before (D1-fix), so with any mode chosen (only
its mark changes; the word is never bold) the pairs hold: tools/check_desk_ui.py step 01 measures every desk pair with each of
the four modes chosen in Line, Half and Tall, and Log on both streams, at all nine sizes and fonts (0 px at every one), every
lower-band word drawn as designed in Line, and every word of the working area whole in Half and Tall (the console's answers
may scroll sideways, a terminal's by design). Bash and Shell are different widths; the slot spreads either by its ink.

**For the owner** (tools/check_desk_ui.py step 12, in build/graphite_desk at 1920 by 1200): `Graphite_Desk_D3_01_Writing_Line_
Modes` (the band in each mode, only the chosen word marked, measured in the window's pixels), `D3_02_Assignment_staC` (files.list
in the line saying staC on Ctrl+Enter; above, the answer of the staC program desk run with Ctrl+Enter), `D3_03_Search_Results`
(results under the line as you type) and `D3_03b_Search_Workspace` (Enter), `D3_04_Log_Events_Half`, and
`D3_05_Log_Network_Half_TEST_DATA` (connections filtered by port 443, a capture's packet stream and a pinned packet, on the
check's fake capability with documentation addresses, labelled TEST DATA on the image). `D3_03b` shows the search's whole answer:
the working area's output keeps to its end while the owner is there, also when the area opens and its horizontal scroll bar
appears after the answer was written (`Console.keep_end`; D3-fix: the text view kept its old position and the answer's last
rows sat out of sight; the check measures the answer's end in sight).

**Choices, and why.**
1. *Plain Enter in Assignment always goes to Graphite*, even for a line that parses as staC: one rule, said in the line's
   quiet word ("staC on Ctrl+Enter") and in the results' caption. A staC program that worked before (the instruction matrix's
   rows) goes into the line for Ctrl+Enter instead of running from the list, so no Enter on a highlighted row runs staC either.
2. *Ctrl+Enter on a `/`, `?` or `$` line* runs it on its page as Enter does, so the deliberate key never surprises.
3. *Search is a visible mode* reached by Ctrl+K, and remembered like any other: the reach review's objection to Find (a quiet
   word that stayed chosen unseen) does not apply to a marked word.
4. *The first-character jumps choose the mode* (the console's own old rule for its prompt), except in Shell, whose lines are the
   shell's own.
5. *Log reads nothing while the line is elsewhere*, and the Network stream calls nothing until D5's operations exist (a refused
   call is recorded in the journal, and the view asks every second).
6. *The capture's confirmation is once a run* (the first Ctrl+Enter after Graphite starts), not once ever: a packet capture is
   rare and consequential, and nothing new is stored for it.
7. *The placeholder stays `poem`*: the brief's "light poem placeholder" is the owner's standing writing invitation, the same
   word in every writing field; it is set lighter than typed text on the line, and no lighter than the desk's quiet lettering
   may be (4.5:1).
9. *One grammar for the Network filter* (D3-fix): the view uses D5's functions rather than a copy, so a filter means one thing
   on the screen, in the capability and for the capture tool.
8. *Rates are bits per second*, the usual reading of the contract's `bps`.

## The cat, the programs list and the System menu (D2)

The owner's brief of 2026-11-06: the cat, "unlabeled ... entirely inside the lower-left shaded band, with pale erased paper for
its silhouette and retained graphite for eye and paw details", opens "a flat, predictable list of available programs and
capabilities, like the Programs folder in a Start menu. Give each entry one plain name and one small graphite icon. Think of it
as the cat's toy box and my toolbox"; the single erased Graphite symbol at the far right opens the system menu: "Put Game
first ... Put Stop all jobs directly beneath it, scoped to work Graphite manages. Then show the ordered process list, with a
niceness slider on every active or queued row. Carry forward queue reorder and distinguish it from niceness. Put Log out,
Return to Debian, Restart, and Shut down in a separated group, as applicable, with session and machine scope clear." The two
menus are Symmetry rule 6's pair. Nothing here is owner-host acceptance: logind on the owner's computer has not been asked.

### The cat (`graphite_brand`, `hatch_qt.HatchButton`)

| Part | Colour (named constant) | When |
|---|---|---|
| Silhouette: head, ears, shoulders, paws, the lifted arm, the tail | `CAT_COAT` = `PAPER_LIGHT` #fffdf8, the workspace's full warm paper white | always |
| Eyes at rest (a small paper glint in each), pupils, closed lids, the paws' outline and two toes each, the mouth | `CAT_DETAIL` = graphite #504d46 | always |
| Irises round the graphite pupils | `CAT_IRIS` = pencil yellow #d4b56a | on hover and while the programs list is open (the pose number `iris`: 1); graphite at rest; none asleep |
| Nose and inner ears | `CAT_NOSE` = eraser pink #cba5a4 | always, small and soft |
| Keyboard focus | `CAT_FOCUS` = eraser pink | a short mark under the cat (`FOCUS_MARK`) |

A full pink cat is one swap: `CAT_COAT = ERASER_MARK`. The coat is the band's brightest value and a step above its lettering,
measured: **9.11:1 on the band's mean tone #4a4741** (8.82:1 on the grain's lightest 5%), the lettering #efeae0 7.72:1; in the
window's pixels the coat's lightness is 252 and the brightest pixel elsewhere in the lower band 232 (check_desk_ui step 13).
#f6f3eb (the panes' ground) would give only 8.35:1 and a cold #ffffff was not wanted (9.26:1).

The poses keep D1-fix's room (`CAT_BOX`, `GROUND`, every pose inside the band with its padding at all nine sizes,
`cat_poses_inside`); the numbers gained a seventh, `iris`, which moves with the rest in the one 150 ms animation, or at once
under Reduce motion. Rest: both paws down, tail tucked, graphite eyes. Hover: a side-glance in yellow, the tail curled like a
question mark with no dot. List open: the tail drops out of sight, the right paw lifts, yellow eyes up toward the list.
Asleep (90 s without input, the list closed): settled 9 units lower, eyes closed, no yellow. `cat_extent` counts the paws'
graphite outline (half of `DETAIL` outside them): the room every pose needs; the band places and pairs the cat by its pale coat (`outline=False`, the integration below). One click opens the list on the press, from any pose, sleep included;
Space, Return and Enter open it with its first row under focus (LauncherKeys); tooltip and accessible name **Open programs**;
the button keeps the Graphite services' lifecycle (`hatch.lifecycle`, which the System menu's services row and the window's
close use). Captures: `Graphite_Desk_13_Cat_Poses_In_The_Band.png` (the four poses cut from the window, enlarged three times).

### The programs list (`programs_qt.ProgramsList`)

Every installed program and capability that sat in the Hatch groups (the 23 adapters of `explore.VIEWS`, through the existing
`ledger.explore` read, one per opening), then a hairline and **Explore the workshop**. One plain name each (`PLAIN`; the
catalogue's own title stays the row's title and its descriptor's first words), sorted A to Z by that name:

Agenda · Assignments (Investigations & assignments) · Calculator (Calculate & compare) · Documents · Files (Files & working
copies) · HDL simulation checks · KiBot outputs · KiCad checks · Laboratory · Local model · Memory (Graphite memory) · Methods
(Methods & theory) · nextpnr & Trellis · ngspice profiles · Office (Office & incoming work) · Projects (Projects & ideas) ·
Questions (Questions & inquiries) · References · Settings (Graphite settings) · Sources (Sources & knowledge) · Tool Atlas ·
Work trail (Activity & receipts) · Yosys synthesis · — · Explore the workshop.

- Each row has one small graphite icon (drawn here on an 18-unit grid with one line weight, `programs_qt.paint_icon`: a bulb, a
  question, a calculator, a flask, a sigma, a folded map, an in-tray, a folder, a page, a magnifier, an ordered list, a chip,
  books, a bookmarked book, a ribbon, sliders, receipts, a board with traces, stacked sheets, a wave, a gate, a cell grid, a
  square wave, a compass) and, at its right, the one status word Graphite observed, in quiet print: unavailable, needs setup,
  N running, N interrupted, or open. The whole descriptor (what opens, what Graphite can do, what is missing, the context,
  Opening runs no tool) is the row's tooltip and F1's note, as before.
- Opening a row is navigation only (`explore_qt.open_instrument`, the existing view factories); nothing is dispatched but
  the reads. A failed read shows one explained row (Capabilities unavailable · its reason); Explore the workshop stays.
- Keyboard: Up and Down (wrapping), Home, End, Page Up and Down, Return, Enter or Space to open, Escape to close (focus back on
  the cat), F1 or Shift+F1 for the descriptor, and **type-to-select**: letters typed within a second make one prefix (`fi`
  Files); the same letter again moves to the next row with it (`k` KiBot outputs, `k` KiCad checks).
- Not in it, by the brief: creation (Work ▸ New Idea… with Ctrl+Shift+N, Work ▸ New Project…; D4 adds the Work tree's
  right-click), recent work (Work's recent list), services and leaving (the System menu).
- Its small caption, at its top in the script: *the cat's toy box and your toolbox* (the owner's words).

### The System menu (`system_menu_qt.SystemMenu`, from `desktop_header_qt.SystemButton`)

Top to bottom: **Game** (STRUTHIO in its offline desk mode, paused at tick zero: `struthio_qt.show`) · **Stop all jobs** (the
existing Master Stop action: its confirm dialog, its stop thread, Ctrl+Shift+F12; its scope in print, *work Graphite manages*;
programs Graphite does not manage keep running) · **the process list** (`desktop_header_qt.NicePopup` as the menu's section:
active jobs as they started, each with its CPU-niceness slider through `jobs.nice`; the queue, each row with its **place
number at the left** (its order: drag the row, or ↑ Earlier and ↓ Later through `agenda.reorder`) and its **niceness slider**
under its title (the Agenda tier through `agenda.nice`): two controls that look and read differently; its waiting reasons;
Background CPU; Open Agenda; Work trail) · **Graphite services On · Off · Restart** (Graphite's own services, never the computer:
the cycles that were the old menu's On, Off and Reboot, `LedgerLifecycle`, under their rules; the row's word opens Service
details; read without its row, by F1's note, a screen reader or the keyboard's order, each choice names its scope:
*Graphite services: Restart*) · a stronger hairline · **Log out** (*this login session*) · **Return to Debian** in the
dedicated session, else **Exit Graphite** (*this Graphite session*) · **Restart** and **Shut down** (*this computer*); an
unavailable row adds *· unavailable* to its scope in quiet ink and **stays in the keyboard's order** (D2-fix): its whole
reason is its tooltip, its accessible description and F1's note, and choosing it says why in a dialog, asking and issuing
nothing · its small caption at its foot in the script: *each asks first and keeps your work*. logind is asked each time the
menu opens, never when it is built. From the keyboard (Enter, Return, Space on the symbol) Game is under focus and Stop all jobs one Down away;
on a slider Left and Right change it and Up and Down move on; inside the queue the arrows choose its rows and leave at its
ends. Older callers keep their names: `top.nice.popup` is the menu, `.kill` its Stop all jobs row, `.game` its Game row, and the
work list's parts (`running`, `queue`, `earlier`, `note`, …) the section's.

### Session and power (`session_power`)

The brief supersedes the earlier rule that Graphite issues no session or power command and the old menu's disabled row
("Log Out · Restart · Shut Down — not in this edition"). What stays of that rule: no sudo, no password asked by Graphite,
nothing without the owner's confirmation, only the system's own interfaces.

- **Availability** from systemd-logind on the system D-Bus, in this process (QtDBus, nothing started): this program's own
  session (`/org/freedesktop/login1/session/self`, its `Id`) and the Manager's `CanReboot` and `CanPowerOff`: `yes` is
  offered; `challenge` (the system asks for permission itself) is offered except in the dedicated session, which starts no
  permission agent (LS_XSESSION.sh runs fluxbox and Graphite only) while the command runs without a terminal, so nothing
  could answer: there the row is unavailable and says to Return to Debian and use `systemctl reboot` or `systemctl poweroff`
  at the text login; `na` (this computer does not offer it) and `no` (your account may not do it here) show the row
  unavailable with that reason. **No logind session** (as in this container: there is no system bus) makes every action
  unavailable with that reason.
- **The commands**: Log out `loginctl terminate-session <id>`, Restart `systemctl reboot`, Shut down `systemctl poweroff`.
  **One function issues every one of them, looks the two programs up and asks logind, `session_power.system`**, so tests
  and checks patch one place; it starts only loginctl or systemctl, found on PATH, with no shell and no terminal, and refuses
  sudo, pkexec, su and doas.
- **The order** (`run_action`, D2-fix after the review): (1) availability: unavailable is refused with the whole reason,
  nothing asked; (2) the leave flow's questions with the window open and **nothing stopped** (`leave_steps`: the return copy's
  own dialog, keep and close or close without a new return copy or continue working; each working area's close question; each
  edited file saved or discarded with the window's own question, a discarded one keeping its recovery copy as on close, its
  buffer as it was); (3) the confirmation naming the scope (Cancel the default: Cancel leaves Graphite open as it was, nothing
  stopped, a discarded file owning its recovery copy again); (4) availability again and the program looked up: either failing,
  **Graphite stays open and says why**, nothing stopped; (5) **Graphite closes the ordinary way** with nothing asked again
  (`quiet_close`: the window's own close takes the return copy if you kept one, pauses running assignments or hands them to
  the Graphite service, closes Graphite's services, stops the local model and the tracked command, saves the session, removes
  its lease); a refused close leaves Graphite open and issues nothing; (6) the command. Ending the login session or the
  computer ends Graphite's process and its display at once (logind sends every process of the session SIGTERM and the X
  server goes with it; a reboot or power-off stops the session the same way), so nothing of the close can come after the
  command: it comes before. If the command then does not start (the system's own permission prompt declined, say), Graphite
  has already closed with the work saved; it says why in a last message and you start it again. The application's automatic
  quit is held across the close and the command (Qt 6.8 drops it when a dialog runs after the last window closed), then
  Graphite ends as after any close. Return to Debian and Exit Graphite are the existing leave (`session_power.leave`),
  unchanged.
- QtDBus's calls (a variant read back, a method's string, a refusal) were tried against a private bus
  (`v01_reruns/desk/D2/probe/dbus_probe.py`); D2-fix ran the whole Log out against a fake logind on a private bus with a fake
  loginctl that sends SIGTERM to its caller, as logind does: the close ran and the session was saved before the command
  (`v01_reruns/desk/D2-fix/e2e/`). The real logind was not asked here.

### Symmetry rule 6, measured (`check_desk_ui.menu_pairs`, step 01 at all nine sizes)

The programs list opens upward from the lower left, the System menu downward from the upper right: the list's left edge and
the System menu's right edge the band's inset from the window's edges; the list's foot on the lower band's top and the System
menu's top on the head band's foot; **one width** (`programs_qt.menu_width`: the panes' content column, P less an inset each
side, or the widest row either menu can show when that is more, the same for both, never past the axis); one row height; one
icon column (the icon's left edge and size, the words' start); the same margins at both ends; each menu's small caption at
its far end, one height; every word whole and nothing sideways in either. Never over a band: taller than the room, a menu
scrolls (the keyboard brings its row into view). 13 rows at each size, every difference 0.

| Size | Programs list (x, y, w, h) | System menu (x, y, w, h) | Width rule (column · list · System menu need) | Row | Icon x, size · words x | Scrolls |
|---|---|---|---|---|---|---|
| 1920 × 1200, 14 pt | 16, 503, 328, 637 | 1576, 60, 328, 539 | 328 · 302 · 308 | 24 | 12, 16 · 38 | no |
| 1366 × 768, 14 pt | 16, 71, 328, 637 | 1022, 60, 328, 539 | 328 · 302 · 308 | 24 | 12, 16 · 38 | no |
| 1280 × 800, 14 pt | 16, 103, 328, 637 | 936, 60, 328, 539 | 328 · 302 · 308 | 24 | 12, 16 · 38 | no |
| 1920 × 1200, 18 pt | 21, 306, 421, 821 | 1478, 73, 421, 668 | 421 · 387 · 388 | 31 | 15, 21 · 49 | no |
| 1366 × 768, 18 pt | 21, 73, 388, 622 | 957, 73, 388, 622 | 373 · 387 · 388 | 31 | 15, 21 · 49 | both |
| 1280 × 800, 18 pt | 21, 73, 388, 654 | 871, 73, 388, 654 | 330 · 387 · 388 | 31 | 15, 21 · 49 | both |
| 1920 × 1200, 20 pt | 22, 224, 460, 898 | 1438, 78, 460, 719 | 460 · 428 · 427 | 34 | 17, 22 · 53 | no |
| 1366 × 768, 20 pt | 22, 78, 428, 612 | 916, 78, 428, 612 | 342 · 428 · 427 | 34 | 17, 22 · 53 | both |
| 1280 × 800, 20 pt | 22, 78, 428, 644 | 830, 78, 428, 644 | 330 · 428 · 427 | 34 | 17, 22 · 53 | both |

(The System menu's height here is with nothing queued; with two queued rows it is 648 px at 1366 by 768 and 14 pt and scrolls
a little. Step 13 runs after earlier steps leave the panes 370 px wide, so its captures show both menus 338 px wide, the column
then, still one width.) Captures: `Graphite_Desk_09_Programs_List_1920x1200.png`, `Graphite_Desk_10_Programs_List_1366x768.png`,
`Graphite_Desk_11_System_Menu_1920x1200.png`, `Graphite_Desk_12_System_Menu_1366x768.png` (two queued rows; the check holds
logind with no login session, so Log out, Restart and Shut down read unavailable, as they truly are in this container), `Graphite_Desk_13_Cat_Poses_In_The_Band.png`,
`Graphite_Desk_14_Menus_Point_Mirror_1920x1200.png` (both open with the guides and the window's centre).

### Choices, and why (D2)

1. **Both menus are one popup design (`programs_qt.DeskMenu`), not a QMenu.** The System menu holds sliders, a draggable queue
   and three service words in a row, which a QMenu does not hold well; one painter for both rows makes Symmetry rule 6 exact
   by construction (the same numbers), and Fusion's QMenu offers no type-to-select.
2. **Plain names** where the catalogue's title is a pair (Projects for Projects & ideas, Work trail for Activity & receipts,
   Assignments for Investigations & assignments: the owner's word for the unit of work). The checks rows keep "checks",
   "outputs", "profiles" and "synthesis", so a row never reads as the tool's own editor.
3. **One width for both, the content column or the widest row.** The column lines each menu up with the pane under it; a
   larger interface size widens both together, so the pair stays mirrored.
4. **Game first and under focus from the keyboard; Stop all jobs one Down away.** The brief's order; a menu opened from the
   keyboard starts at its first row (as the list does), and Enter on Game is harmless.
5. **Graphite services in the System menu**, its Reboot cycle shown as Restart (its key unchanged; the plan's word) with
   "never the computer" in its words, set apart from the computer's Restart by its row's own word, the stronger hairline and
   the scope words; read without its row (F1, a screen reader, the keyboard's order) it is *Graphite services: Restart*.
6. **Scope words**: Log out says *this login session*, not *this Graphite session*: logind ends the whole login, which on an
   ordinary desktop is more than Graphite. Return to Debian and Exit Graphite say *this Graphite session*; Restart and Shut
   down *this computer*.
7. **The questions, then the confirmation, then the close, then the command** (D2-fix). The questions about work come first
   with the window open and stop nothing, so Cancel at the confirmation keeps the model, the tracked command and the
   assignments running. Everything the ordinary close does comes before the command, because the end of the session takes
   Graphite and its display with it (the review saw Log out end Graphite before its close ran). Every refusal that can be
   known before the close (no session, logind's no, the program missing, the close refused) leaves Graphite open and saying
   why; only a refusal the system makes at the last moment comes after the close, and Graphite then says why in a last message.
8. **`challenge` is offered where the system can ask** (a desktop's own permission prompt decides; Graphite never asks for a
   password), not in the dedicated session, where nothing can answer and Graphite would close for nothing.
12. **An unavailable row stays reachable** (D2-fix): quiet ink and *· unavailable*, but in the keyboard's order, so F1 and a
    screen reader reach its reason, and choosing it says why; a disabled row could only be hovered.
13. **A resting pointer takes no row** (D2-fix, as a QMenu does): a pointer resting where a menu opens leaves the keyboard's
    first row under focus and washes nothing; its first movement takes the row under it. (Found when the unavailable rows
    became reachable: the desk check's pointer rested where Restart opens and took the first row from Game.)
9. **The queue's order is its own control** (place numbers, drag, Earlier and Later), the niceness the slider under each
   title; the explanation is the sliders' one-line script note and the tooltips.
10. **Captions by the quiet-script rule**: each menu's small caption in the script at its far end (the list's top, the System
    menu's foot: mirrored); statuses, scope words and the game's name STRUTHIO in print.
11. **The coat #fffdf8**: the only warm paper white of the palette that clears 9:1 on the band.

## The right-click menu (D4)

The owner's brief of 2026-11-06: "Make the right-click menu a defining capability of Graphite. Take the Fluxbox pipe-menu idea
seriously. When I right-click, build the menu for the thing under the pointer, the current selection, and what is possible in
that workspace. I want to reach an action while my attention is still on the work." And: "Give these actions the same command,
tool, and permission checks used elsewhere in Graphite. Keep target and revision information attached to actions that change
work. Show the resulting edit, tool output, or job state where it belongs." The owner later replaced Log's notes with the
network (2026-11-06: "I meant log notes replaced with network"), so a log event offers no note; a network connection or packet
offers its own words. Nothing here is owner-host acceptance.

### How a right-click becomes a menu (`workbench/context_menu.py`)

In the pipe-menu spirit the menu is asked for, not written down: small functions answer for the thing under the pointer.

- **The router.** `context_menu.install(host)` (called by `chain_menu.install`) puts one event filter on the application
  (`Router`). A ContextMenu event for a widget of the window, or of one of its popups (the System menu's list), is answered
  here when a finder knows the place; anything else keeps its own menu. The Menu key and Shift+F10 open the same menu for the
  keyboard focus (`open_at_focus`: the current item, or the caret's passage), its first row under focus. The rooms' old hooks
  (`cabinet_qt.context_menu`, `finder_qt.context_menu`, `files_qt.FilesTab.menu`, `document_qt.DocumentPage.contextMenuEvent`,
  `shell2.LibraryTab.menu`, Today's) call `context_menu.open_at`, so they give the same menu if the router is ever off.
- **The finders** (`FINDERS`): one small function per surface turns the widget and the point into a `Target`. `target_at`
  walks from the widget under the pointer up to its parents and stops at a widget with a menu of its own: a text field (the
  writing line, an editor), a slider, a spin box, a combo box, a label you can select or follow a link in (its Copy), or a list
  that keeps its own menu (the Agenda's, the investigation's, the laboratory's, the Master Stop button's).

| Surface | Finder | Target |
|---|---|---|
| A document page | `find_document` | the selected **passage** (when the pointer is on the selection), else the **page** at the paragraph the caret moves to |
| Files (list or thumbnails) | `find_files` | a **file**, a **drawing**, a **datasheet** or a **table** (by its kind), a **folder**, **two or more files**, or the folder's **empty place** |
| The Finder | `find_finder` | an entry (file kinds as above, or a folder), or the folder's empty place |
| The cabinet tree | `find_cabinet` | a **record**, or the **tree** itself on its empty place |
| The Machine tree | `find_machine` | the **Work** branch and its projects, or a row about **this computer** |
| The Settings tree | `find_settings` | a **setting** or a settings group |
| The Library | `find_library` | a **received file**, or the Library's empty place |
| Log (D3's `log_qt`) | `find_log` | an **event** (Events), a **network connection** or a **packet** (Network), or the pinned entry; through `log_qt.entry_at` |
| Activity | `find_activity` | a Timeline line (an **event**), or the cabinet selection's words (its **record**: `operations_qt.OperationsPanel.context_target`) |
| The System menu's process list | `find_process_list` | a Kernel **job** (read again now) or **Agenda work**, queued or running, by the row's own kind (the running list holds both; D4-fix) |
| The Engineering room's Jobs list | `find_jobs` | a **job**, paused ones too (they are not rows of the System menu's list) |
| Today | `find_today` | an **empty place** |
| Any room's empty place (the walk reaches the rooms' tabs or the central stack) | `find_workspace` | an **empty place**, named by the room |

- **The target** carries what the menu's top names (`label`, `noun`: what it is, with its page and revision or its state), what
  an action that changes work carries (`ident` and `revision`), the surface's own record (`data`), every selected record
  (`items`), and the room or view it lives in (`owner`).
- **The providers** (`PROVIDERS`): small functions `(host, target) -> [Entry]`, asked in order; the first entry for a key wins;
  a provider that fails costs the others nothing (its one row says "Some actions are unavailable" with the reason). An `Entry`
  has a stable key, readable words, its section, what it runs, an icon, a quiet caption (a key, a status, a far address), whether
  it is available and why not (the reason is its tooltip and the row reads *unavailable*), the Kernel operation it dispatches
  (said in its tooltip), and a submenu when it has one.
- **The sections**, in this order with a hairline between them: open and show · change it · its state · staC · capabilities ·
  the tree · edit and copy · remove. Common actions stay where the eye expects them; the selected thing decides the rest.
- **The menu** (`ContextMenu`) is the desk's own menu, `programs_qt.DeskMenu`: the programs list's and the System menu's row
  height, icon column, margins and width rule (measured equal at 14, 18 and 20 pt). Its top row names the target before you
  act: the target's icon, its name in print (DemiBold) and what it is in quiet print at the right; in a narrow window *what it
  is* gives way first, so the name stays whole. Each row: a small graphite icon, the words, a quiet caption, `›` for a
  submenu; an active choice (the cabinet's current view, the paragraph's style, the line's mode) has the desk's short pencil-
  yellow mark. The menu's small caption at its foot, *what you can do right here*, is in the script (the quiet-script rule).
  It opens at the pointer and flips up or left to stay inside the window; submenus cascade beside their row (on a 240 ms rest,
  Right, or Enter; Left and Escape close them). The chain builder (`chain_menu.Chain`, the owner's pipe menu) cascades as
  its own QMenu dressed in the same numbers (`chain_menu.desk_style`).

### Every action through Kernel.dispatch, with the target's id and revision

The menu calls `context_menu.dispatch`: `Kernel.dispatch(operation, arguments, operator())`, the owner's principal, the same
scopes and checks every room uses. Nothing new is scheduled, stored or started.

- **A passage or a page**: Bold, Italic, Underline, Plain and the paragraph styles are `documents.edit` with the page's `id`,
  the `expected_revision` seen at the right-click (unsaved words are saved first, so it is the saved revision), the selection
  with its quoted words, and `origin: HUMAN`. The Kernel refuses `REVISION_CHANGED` or `SELECTION_CHANGED`; the page then shows
  the saved revision and the line says "The page moved on since you right-clicked it (revision 3, now 4), so nothing changed."
  An applied edit lands through the page's own undo stack (Ctrl Z takes it back), the page shows it, and its foot says the new
  revision. **Move to notes** reads the page again (`documents.get`, refused if it moved), keeps the words as an idea in the
  cabinet (`ideas.capture`, the cabinet's Keep idea path), then takes them off the page (`documents.edit`, Ctrl Z puts them back).
- **A file**: its revision is its modification time and size as listed; every change (`files.rename`, `files.copy`,
  `files.move`, `files.export`, `files.versions` / `files.revert`, `files.trash`) first reads it again (`files.get`) and is
  refused when it moved ("changed since you right-clicked it … Right-click it again"), then goes through the Files room's own
  act (Kernel.dispatch, then the room reloads).
- **A job**: Pause, Resume and Stop read the job again (`jobs.get`; its state is the revision) and are refused when it moved,
  then dispatch `jobs.pause`, `jobs.resume` or `jobs.cancel` with its `id`; the row reads its new state. A running job asked to
  pause or stop says so ("Asked to pause · … · it pauses at its next safe point"). Pause and Resume are shown unavailable, with
  the Kernel's own reason, for the jobs the Kernel will not pause (the service tools, D5's network capture, which is stopped and
  started anew, external tasks: `context_menu.no_pause` and its table `NO_PAUSE`; test_context_menu asks the Kernel itself to
  pause a running job of every `JOB_TOOLS` it imports and requires the menu to agree; the Kernel keeps the last word).
  **Agenda work**, queued or running (`agenda.pause` for NEXT or LATER work, `agenda.resume` for PAUSED work, `agenda.cancel`
  for any open work, a running item too, as the Agenda room's running row offers it; the same rules, asked of the Kernel for
  each state in the test), after `agenda.view` shows it unchanged; a running item that runs a job has Its job › by its state now.
- **A cabinet record**: the cabinet's own checked actions (`ledger.cabinet.actions`), each re-resolving its signature before it
  runs (`cabinet_actions_qt.perform` refuses a changed record or action list).
- **Reads**: Run and Inspect output are typed staC through the staC page of the working area (`shell2.to_console`, the normal
  path, `language.run`); the menu reports what the Kernel did, read back from that page (`Console.last_program` is set only
  when the program ran): "Ran in the working area: …", or, when staC refuses (a file gone, the source binding not current), a
  refusal, "Not run: *the Kernel's reason*", never that it ran (D4-fix). Inspect output reads the job's output from its evidence
  record (`@evidence:<id>`) once one is kept, its record (`@job:<id>`) until then. Compare is `files.compare` on the actual
  files; Extract lists the staC lenses that give rows, with their counts (read-only), and when staC refuses the file itself it
  shows one greyed row, "Not readable now: …", with the reason, instead of "Nothing to read as rows". **Inspect in the line** puts the equivalent command in the writing line in Assignment, for reading or editing,
  and runs nothing: a file's staC (`@files:bench.csv | rows`; Ctrl+Enter runs it), a job's `@job:<id>`, a record's address, a
  passage's `/documents.edit {…}` with its id, revision and selection (Enter runs it, through the same operation path).
- **Where the result shows**: the page with the change on it; the working area's staC page for a reading; the Compare room for
  a comparison (a tab you can keep); the job's row (and the line) for its state; the Log view, pinned and filtered, for a
  conversation; the writing line for an assignment; the status line for a small result (a copied address).

### The providers, by kind

| Target | Entries (top to bottom) |
|---|---|
| A passage | Bold · Italic · Underline (each "Not bold" when the mark is on) · Plain · Paragraph style › (Heading, Subheading, Minor heading, Body, Code; the current one marked) · Move to notes — Inspect in the line — Ask Stacy about this · Search for these words — New document · Export… — Undo · Redo · Cut · Copy · Paste · Delete · Select all |
| A page (no selection) | Paragraph style › — New document · Export… — the text edits |
| A file, drawing, datasheet or table (Files) | Open · Open with this computer's app · Show in its folder — Rename… · Copy to… · Move to… · Versions… · Export… — Inspect in the line · Run · Chain from here › — Compare with… · Compare with a kept version › · Extract › · Open in *the adapter for its kind* · Find tools in the Tool Atlas · Explore capabilities… · Explain this file · Ask Stacy about this… · Investigate… · Add to the Agenda… — Copy path · Copy the staC address — Move to Trash; for a working copy also Ask Stacy to work on this…, Review changes to the original…, Show the original, Discard this draft… |
| Two files | **Compare revisions** when they are revisions of one file ("board rev B" and "board rev C", "notes v1" and "notes v2", "draft" and "draft (2)"), else Compare these two; the older is passed as *before* — Copy to… · Move to… — Copy paths — Move to Trash |
| A folder or a smart folder (Files) | Open · Rename… (a smart folder too: `files.rename` takes it) · Copy to… · Move to… · Export… · Copy path · Move to Trash; a folder copy: Look inside, confined… · Run a command here, confined… · Review changes to the original… · Show the original · Discard this draft… (from a pill: Return as a pill… · Review the changes… · Discard this draft…) |
| Files' empty place | Root menu › (the whole root of the pipe menu, as Today has it, where the old chains › held it: Your chains ›, Start a chain from ›, Writing line ›, Edit the Graphite menu… — Inquiries…, Algorithm & Theory Atlas…, Tool Atlas…) — New folder… · New smart folder… · Import… · Work on a copy of a file… · View as › (Thumbnails, List) · Show all files · Refresh |
| A Finder entry | Open · Open in viewer · Show in Files — Change it in Files (or "Nothing changes here", greyed, outside Files) — Inspect in the line · Run (inside Files) — Extract · the adapters for its kind · Ask Stacy about this file — Copy path |
| A Finder folder's empty place | Root menu › — View as › (List, Icons, Columns) · Show/Hide hidden files · Show/Hide the preview · Refresh — Copy path |
| A cabinet record | Open · Read saved details — Write an idea here… / the record's preparing actions — the provider checks · Open *its workspaces* · Explore all capabilities — Inspect in the line · Run (its address) — Refresh · View as › · New Idea… · New Project… · Import (Ingress)… · Export (Egress)… (on a project) — Copy the identity |
| The cabinet tree's empty place | Refresh · View as › (Logical cabinet, Existing views; the current one marked) · New Idea… · New Project… · Import (Ingress)… · Export (Egress)… |
| The Work tree (Machine) | New Idea… · New Project… · Import (Ingress)… · Refresh; a project: Open · Inspect in the line · Export (Egress)… · New Idea… · New Project… · Refresh |
| A Machine row | Show in the Finder (a storage row) · Open Settings (its row) — Refresh — Copy what it says |
| A setting | Open this setting — Expand all · Collapse all · Search settings… — Copy the key |
| A received file (Library) | Open — Keep a copy in Files — Ask Stacy about this file — Copy the name; its empty place: Root menu › — Receive files… · Refresh |
| A job | Show in Jobs — Inspect output (its kept output, else its record) · Pause · Resume · Stop (each by its state; Pause and Resume greyed with the Kernel's reason for the tools it will not pause) — Inspect in the line — Copy the job id |
| Agenda work (queued or running) | Open Agenda — Pause (NEXT or LATER) · Resume (PAUSED) · Stop (any open work; a running item is cancelled) · Its job › (when it runs one) — Inspect in the line (its staC program, read from the Agenda: the System menu's snapshot leaves programs out) |
| An event (Log's Events, Activity's Timeline) | Open (in Activity: where it happened) — Ask Stacy about this · Show in Log · Its job › (when it has one: the job's entries by its state now) — Copy. No notes. |
| A network connection or packet (Log's Network) | Ask Stacy about this (an assignment in the line with the entry as its context, `log_qt.ask_about`) · Follow this conversation (`log_qt.focus`: the stream filtered to the far host and port, the filter in the line, the entry pinned) · Show the process (the stream filtered to the program, when the process is known; its name as the caption) — Copy address (the far side; a packet's is the side with the lower port, the service) |
| Today, the workspace (an empty place) | Your chains › (the owner's menu file) · Start a chain from › · Writing line › (Assignment, Shell or Bash, Search, Log) · Edit the Graphite menu… — Inquiries… · Algorithm & Theory Atlas… · Tool Atlas… — New Idea… · New Project… · Import (Ingress)… |

A connection is named by who talks to whom ("firefox → 93.184.216.34:443", *network connection · tcp · established*), a packet by
its source and destination (*packet · tcp · 60 bytes*). These entries read only the fields D5's `network.observe` and
`network.capture.read` give the Log view (`process`, `pid`, `local`/`lport`, `remote`/`rport`, `src`/`sport`, `dst`/`dport`,
`proto`, `state`, `length`); the menu starts no capture. When the program belongs to another user of the computer, D5's reader
writes *another user* and never guesses its name (`network_watch.ANOTHER_USER`); the menu then names the near side by its address
and shows Show the process unavailable, with that reason (`context_menu.known_process`).

### The old menus, folded (nothing lost)

Every entry today's context menus offered is in the new menu for the same thing; `context_menu.FOLDED` lists each (old menu, its
words, the target that offers it now, the entry's key) and test_context_menu builds each menu and finds every key.

| Old menu | Its entries | Now |
|---|---|---|
| Files: a file (`files_qt.FilesTab.menu`, now `old_menu`, kept for readers) | Open / Open pill…, Explain this file, Ask Stacy about this…, Investigate…, Add to the Agenda…, Open with this computer's app, Rename…, Versions…, Compare with…, Compare with a version…, Export…, Copy to…, Move to…, Move to Trash; the chain from `@files:` around it | The file's menu, the same words (Compare with a version is now Compare with a kept version ›, listing the kept versions); the chain is Chain from here › |
| Files: a working copy | Ask Stacy to work on this…, Review changes to the original…, Show the original, Discard this draft… | The file's menu |
| Files: a folder copy | Look inside, confined…, Run a command here, confined…, Review changes to the original…, Show the original, Discard this draft…; from a pill: Return as a pill…, Review the changes…, Discard this draft… | The folder's menu |
| Files: the empty place | New folder…, Import…, Work on a copy of a file…, chains › (the root chain menu: Inquiries…, Algorithm & Theory Atlas…, Tool Atlas…, your kept chains, start from ›, writing line ›, edit the Graphite menu…) | The empty place's menu: its own words, and Root menu › holding every word of the old chains › (D4-fix: the first build kept only Your chains › and Start a chain from ›) |
| Files: a smart folder | Open, Rename…, Export…, Copy to…, Move to…, Move to Trash | The smart folder's menu, the same words (D4-fix: the first build had dropped Rename…) |
| The Finder (`finder_qt.FinderPage.menu_for`) | Open, Open in viewer, Show in Files, Copy path, Ask Stacy about this file / folder, Change it in Files or the greyed "Nothing changes here" | The entry's menu, the same words (test: the old builder's words are all in it) |
| The cabinet (`cabinet_actions_qt.menu`) | "With *record*" (the heading), Read saved details, Write an idea here / Name a new project, the provider checks, Open *workspace*, Explore all capabilities | The record's menu: the heading names the record; every action of `ledger.cabinet.actions` is a row, unavailable ones with their reason |
| The Library (`shell2.LibraryTab.menu`) | Open, Keep a copy in Files | The received file's menu |
| Today (the root chain menu, `chain_menu.root_menu`) | Inquiries…, Algorithm & Theory Atlas…, Tool Atlas…, your kept chains, start from ›, console › (Log · staC · Kernel · Find · Shell), edit the Graphite menu… | Today's menu; console › is Writing line › with the four modes |
| A document page (Qt's text menu) | Undo, Redo, Cut, Copy, Paste, Delete, Select All | The passage's or page's menu, at its end |
| Activity's Timeline (activation only) | open the event | An event's Open |
| The Menu key (`chain_menu.install`: the chain builder) | the chain builder for the current room | The right-click menu for the focus; Ctrl+Shift+Space and Commands ▸ Chain Menu still open the builder alone |

### Choices, and why (D4)

1. **One event filter, not a hook per widget.** Surfaces D4 does not own (D3's Log view, D2's process list, the trees, the
   Engineering room) needed no edit, and a new surface needs only a finder. The old hooks call the same `open_at`.
2. **The menu is the desk's menu** (`DeskMenu`), not a QMenu: the same numbers as the programs list and the System menu by
   construction, a heading row that names the target, captions, the yellow mark and type-to-select; the chain builder keeps
   its QMenu (tear-off, filled as it opens) dressed in the same numbers.
3. **A passage's equivalent command is the operation line.** No staC address names a passage, and `/documents.edit {…}` with
   the id, revision and selection is exactly what Bold runs; a separate "Run" on a passage would repeat Bold, so it is not
   offered. A file, a record and a job get both Inspect in the line and Run (their staC).
4. **The target's revision is the one seen at the right-click**, never one read at the click on a row, so a change made in
   between is refused, not silently applied to newer words.
5. **Two revisions by their names** (rev / revision / v / r with a number or a letter, a trailing number, at the end or the
   start), the same kind of file; the older passed as *before* so what changed reads left to right.
6. **Paused jobs** are not rows of the System menu's list (it shows the active and the queued), so a paused job is reached
   from the Engineering room's Jobs list and from any event of it (Its job ›), where Resume is offered.
7. **Pause and Resume greyed when the Kernel would refuse them**, with its reason, rather than offered and refused; the rule
   is checked against the Kernel itself for every job tool it names (D4-fix: a network capture had been offered Pause).
8. **The root on every empty place**: the root of the owner's pipe menu is where nothing is selected, as on a Fluxbox desktop.
   Today and the workspace's empty place are the root itself; a room's empty place with words of its own (a folder in Files,
   in the Finder, the Library) carries it whole as its first row, Root menu ›, where Files' old chains › held it, so its own
   words stay in sight.
9. **Network entries name who talks to whom**; the far address is the caption of Copy address so you see what is copied.
10. **The capabilities for a file are named by its kind, not guessed from words** (`context_menu.ADAPTERS`, only those
    installed): a board → KiCad checks and KiBot outputs; a Gerber or drill file → KiBot outputs; a datasheet (PDF) →
    References; a netlist → ngspice profiles; Verilog → HDL simulation checks and Yosys synthesis; a table → Calculator (and
    Office for a workbook); Markdown or text → Documents; Python → Laboratory. A DXF, STEP or STL has no adapter installed, so
    it gets Compare, Extract (its layers), the Tool Atlas and Explore. Opening an adapter is navigation; its tool runs from there
    with its own checks.
11. **Any room's empty place is the root of the pipe menu** (`find_workspace`), as Today is; a selectable label keeps its own
    Copy menu.
12. **A refusal is never reported as done** (D4-fix): Run, Inspect output and an Extract lens read back from the staC page
    whether the Kernel ran the program, and say "Not run" with its reason when it did not.
13. **The row's kind decides what a process-list row is** (D4-fix): the System menu's running list holds the Kernel's jobs and
    the Agenda's running items; an Agenda item is Agenda work with the Agenda's own words (Stop is `agenda.cancel`), never a
    job.

### Checks and tests (D4)

- `tests_integrated/test_context_menu.py` (34 tests, in `tools/check_hatch.FOCUSED_MODULES`): the pure rules (revisions of
  one file, what a file is, its staC, the far side of a network entry, another user's process not a program, the providers'
  order and isolation, the Pause rule with the network capture, Agenda work and jobs by state, the folded list); and on one
  offscreen window with every hold (Kernel.launch, Kernel.submit, clip._request, session and power, processes): a real
  ContextMenu event on each surface finds its target (passage, page, file, drawing, datasheet, table, folder, two files, empty
  places, a Finder entry, a cabinet record and the tree, the Work tree, a setting, Today, a Log event, a connection, a packet,
  an Activity line, jobs in the System menu's list and the Jobs list, a running Agenda item in the System menu's list); the
  target named whole at the top; Bold, Move to notes, rename and Pause through Kernel.dispatch with the id and revision; each
  refused when the revision moved (the page, the file, the job); Compare revisions on the two actual files; Inspect in the
  line runs nothing; nothing lost from the old menus: every word of the old builders, their submenus too (Files' menu for a
  file, a folder, a smart folder, a selection and the empty place with its chains ›; Today's root chain menu; the Finder's), is
  read back from the new menu with its submenus opened, or FOLDED names its home there and that entry is offered; the Menu key
  and Shift+F10; text fields keep their own menu; the menu's metrics are the programs list's. D4-fix added the mirrors that
  ask the Kernel itself: Pause offered exactly when `jobs.pause` takes a running job, for every `JOB_TOOLS` the Kernel imports;
  Pause, Resume and Stop offered exactly when `agenda.pause`, `agenda.resume` and `agenda.cancel` take an item, for each Agenda
  state; Run, Inspect output and Extract with the source binding read as current (an answer reported done, a vanished file
  and an unbound source reported "Not run" with the reason, the job's kept output shown); and a real connection read by
  `network.observe` (a loopback connection the test holds open), with Follow and Show the process. Run against the first
  build's `context_menu.py`, these and the stricter nothing-lost test fail (nine failures), as they should.
- `tools/check_context_menu_ui.py` (in the UI gate; captures to build/graphite_desk or `ARC_LEDGER_CONTEXT_MENU_CAPTURE_DIR`,
  with `context-menu-ui.json`): the owner's captures at 1920 by 1200 — Graphite_Desk_D4_01 (a selected passage's menu),
  D4_02 (Bold applied: the page shows it, its foot the new revision), D4_03 (two revisions selected: Compare revisions first),
  D4_04 (the Compare room with the two files), D4_05 (a running job's menu in the System menu's list) and D4_05b (Pause chosen
  on a queued job: the System menu's list reads it waiting, paused, and the status line says so), both TEST DATA, so named and
  labelled on the image, because no job may run in a check (the jobs are records the check writes), D4_06 (the cabinet tree's
  menu with View as open), D4_07 (a real connection's menu: the check's own loopback connection, read by D5's
  `network.observe` from this computer's connection table, the stream filtered to its port; TEST DATA, so named and labelled,
  only where the table cannot be read) — and D4_08 at 1366 by 768; the refusal on a moved page; the menu's numbers at 14, 18
  and 20 pt; every word whole; the menu inside the window. Each capture's status line holds only its own step's words (the
  check asserts it; the first build's pause words had stayed in D4_06 to D4_08), and a capture's earlier name is removed when
  it is written under another (`superseded` in the JSON).
- No operation and no setting was added; the registry is unchanged.

## Where things went

The short map the brief asks for ("Give me a short map of displaced controls and the new paths to their actions"): every
control the desk took away, one line each, old place → where its action is now, as this tree builds it (the head's menus read
from the live window: `v01_reruns/desk/integrate/probe/menus.txt`). The table under Homes below says which item moved it and how
each home is checked.

- The small mark at the upper left (one click: the game) → the Graphite symbol at the upper right ▸ Game
- Nice ▾ in the head → the Graphite symbol (the System menu): Game, Stop all jobs, the process list
- Stop everything (the kill switch, first in Nice) → System menu ▸ Stop all jobs; Tools ▸ STOP / KILL all Graphite operations…; Ctrl+Shift+F12
- Activity's work list: the niceness sliders, the queue's order (Earlier, Later, drag), Background CPU, Open Agenda, Work trail → System menu ▸ the process list; Activity ▸ Work list opens it
- The queue's explanation under its status → Activity's WORK line and its tooltip; each queued row's waiting reasons in the System menu
- The cat's menu: the six tool groups → the cat's programs list (every capability once, A to Z, one small icon each)
- The cat's menu: Explore the workshop… → the programs list ▸ Explore the workshop (its last row)
- The cat's menu: New Idea, New Project → Work ▸ New Idea… (Ctrl+Shift+N) and Work ▸ New Project…; the right-click on the Work tree, the cabinet tree and Today
- The cat's menu: Graphite services On · Off · Reboot → System menu ▸ Graphite services On · Off · Restart
- The cat's menu: Exit Graphite or Return to Debian, and the disabled "Log Out · Restart · Shut Down" → System menu, the separated group: Log out, Return to Debian or Exit Graphite, Restart, Shut down
- The strip's Graphite word → the writing line ▸ Assignment (Alt+1; Enter gives the words to Graphite)
- The strip's staC selector → the writing line ▸ Assignment, Ctrl+Enter runs typed staC (Alt+2; the `@` lead); Up on the empty line brings back the staC you ran
- The strip's Kernel word → Commands ▸ Run an operation… (Alt+3: the line in Assignment with the `/` lead)
- The strip's Find word, and Ctrl+K into the box → the writing line ▸ Search (Ctrl+K, Alt+4, the `?` lead)
- The strip's Console word → the writing line ▸ Shell, read Bash when your shell is bash (Alt+5, the `$` lead)
- The strip's Explore word → the programs list ▸ Explore the workshop; Tools ▸ Explore capabilities…; a file's or record's right-click (its program, the Tool Atlas, Explore capabilities…)
- Tools ▸ Type to (Graphite, staC, Kernel, Find, Shell) → Commands ▸ Writing Line (Assignment, Bash, Search, Log) and Commands ▸ Run an operation…
- The centre foot's Timeline line, Return thread and Follow latest → Activity (the Timeline's last lines, Return thread with Ctrl+Alt+R, Follow latest); the whole Timeline is the writing line ▸ Log ▸ Events (Alt+6, at Half or Tall)
- The centre foot's Work trail → Activity ▸ Organizer; the Work trail room is the programs list ▸ Work trail and the System menu's Work trail
- Log notes (a note attached to a chosen event) → replaced by the network: the writing line ▸ Log ▸ Network; on any Log entry, Ask Stacy about this (its pin, or its right-click)
- The machine strip line above the left column → the Machine row's tooltip (Machine tab); the head's CPU · GPU · RAM · TXT
- The Machine view's details pane and its Refresh machine view word → each Machine row's tooltip; Arrange ▸ Refresh Machine View
- The cabinet's Logical cabinet / Existing views words → Arrange ▸ Cabinet ▸ Logical Cabinet / Existing Views; the cabinet tree's right-click ▸ View as
- The cabinet's Refresh cabinet word → Arrange ▸ Cabinet ▸ Refresh Cabinet; the cabinet tree's right-click ▸ Refresh
- The Existing views' line (its catalogue choice, Concern overview) → Arrange ▸ Cabinet (Properties & works, Offices, Work & ideas, Archive, Concern Overview)
- The cabinet's query box (Find work…) → the writing line ▸ Search (its CABINET rows)
- The cabinet's status line → the Cabinet tab's tooltip
- The settings filter (Find a setting…) and its caption → the writing line ▸ Search (its SETTINGS rows); the Settings tab's tooltip
- Import, beside Trash → Work ▸ Import (Ingress)…; Import… on the right-click where material enters (the cabinet tree, the Work tree, Today, Files' empty place; Receive files… in the Library's)
- Export, beside Trash → Work ▸ Export (Egress)…; Export… on a file's right-click, Export (Egress)… on a project's, Export… on a page's
- The left column's Cabinet · Machine · Settings words → the left pane's tabs Machine · Cabinet · Settings
- The right column's Context | Graphite segments and the Operations word → the right pane's tabs Conversation · Activity · Context
- The Work block in Graphite's face → Activity, at its top while an assignment runs
- The Menu key (the chain builder) → the right-click menu for what has the keyboard focus (the Menu key, Shift+F10); the chain builder alone: Commands ▸ Chain Menu, Ctrl+Shift+Space
- Today's right-click (the root chain menu) and Files' chains › → the right-click on an empty place: the root itself on Today and the workspace; Root menu › first in a Files folder, the Finder and the Library
- A smart folder's Rename… (the old Files menu) → the smart folder's right-click ▸ Rename…
- Two column widths → one width for both panes: drag either edge, or Settings ▸ Workspace ▸ Left column width
- The script wordmark → Graphite at the upper left, in the script, pale on the band

## Homes for displaced controls (D1a, D1b and D1-fix; D2 to D4 add theirs)

Every action a removed control reached is still reached; tools/check_desk_ui.py step 07 triggers each D1b home (the transfers
with their destination patched) and records the table in desk-ui.json (`homes`).

| Was | Now |
|---|---|
| The small mark at the upper left (one click: the STRUTHIO game) | The erased symbol at the far right is the mark; the game is Game in the System menu's list (D2: its first row) |
| Nice ▾ in the head | The erased symbol, System menu (D2): Game, Stop all jobs, the process list |
| Explore (the word beside the cat) | The menu's Explore the workshop…, Tools → Explore capabilities…, Explore under Activity's cabinet selection; D2: the programs list |
| Ctrl+K into the box | Ctrl+K: the writing line in Search, marked and remembered (D3; D1-fix had the one-line Find lead `?`) |
| The script wordmark | Graphite at the upper left, pale on the band and in the script again (the owner, 2026-11-06; D1a had set it in Plex) |
| Two column widths (left 248 Library floor / right floor from its row) | One width for both panes; the setting sets both; the separators show the resize cursor (D1-fix) |
| The work list in Activity: Stop everything, the niceness sliders, Earlier / Later and the queue's drag, Background CPU for owned work, Open Agenda, Work trail, the sliders' explanation (D1-fix) | The System menu's list (the symbol at the upper right; Activity's Work list word opens it), the same list with each row's waiting reasons; Activity's WORK line says what runs and waits, and its tooltip and the list's note keep the explanation; Stop everything also Tools ▸ STOP / KILL and Ctrl+Shift+F12 |
| The queue's explanation under its status in Activity (D1-fix) | The WORK line's first-through-the-queue status, its tooltip, and each row's waiting reasons in the System menu's list |
| The machine strip above the left column's words (processor · RAM · free space · network) | Machine: the Machine row's tooltip carries the line (sampled every 2 s as before); its facts are the Processor, Memory, Storage and Connections rows; the head's monitors stay live |
| The Machine view's details pane, its Refresh machine view word and caption | Each row's tooltip carries its whole description (source, time, values); Arrange ▸ Refresh Machine View (shows the Machine tab); the tree refreshes itself when shown after 30 s; the caption (when observed, from where, nothing run) is the Machine tab's tooltip |
| The cabinet's Logical cabinet / Existing views words | Arrange ▸ Cabinet ▸ Logical Cabinet / Existing Views; the cabinet tree's right-click ▸ View as (D4) |
| The Existing views' line ("Showing …", its catalogue choice and Concern overview) | Arrange ▸ Cabinet: the catalogue choices under "Existing views show" and Concern Overview |
| The cabinet's Refresh cabinet word | Arrange ▸ Cabinet ▸ Refresh Cabinet; the cabinet tree's right-click ▸ Refresh (D4); the cabinet still refreshes itself every 2.5 s |
| The cabinet's query box (Find work…) | The writing line's Search (Ctrl+K): CABINET rows under the line as you type, and a CABINET section when Enter searches the workspace (label and role, the box's own match); a record opens where it belongs: the Cabinet tab, selected and opened (D3) |
| The cabinet's status line (saved records, order) | The Cabinet tab's tooltip |
| Import (beside Trash) | Work ▸ Import (Ingress)…: the same transfer, the Office's receiving controls; where material enters, on the right-click (D4): the cabinet tree, the Work tree, Today, Files' empty place (Import…), the Library's (Receive files…) |
| Export (beside Trash) | Work ▸ Export (Egress)…: the same transfer, Files ▸ Egress; on a file's right-click Export… (files.export) and on a project's Export (Egress)… (D4); a document's Export… on its page's right-click |
| The settings filter (Find a setting…) and its caption | The writing line's Search: SETTINGS rows as you type and a SETTINGS section on Enter (label and key, the filter's own match); a setting opens in Settings. The caption (the count of settings) is the Settings tab's tooltip |
| Cabinet · Machine · Settings words (pink, the current one ruled) | The left pane's tabs Machine · Cabinet · Settings (the same buttons) |
| Context \| Graphite segments and the Operations word | The right pane's tabs Conversation · Activity · Context (the same buttons: slate_button, operations_button, context_button) |
| The Work block in the Graphite face | Activity, at the top while an assignment runs (`shell2.face.work` keeps its name) |
| The centre foot: Timeline line, Return thread, Follow latest, Work trail | Activity: the Timeline's status line and last lines, Return thread (and Ctrl+Alt+R), Follow latest; the foot's "Work trail" opened the Organizer and now says Organizer (the Work trail room is the System menu's list's Work trail word, and the menu's Activity row). Above the band, the Timeline is Log's Events stream (D3): Log at Half or Tall, newest at the bottom with Follow latest |
| The explorer's mast above the left column (logo, tree search; already out of sight) | Unchanged, kept as an object; the pane's top is its tab row |
| Graphite (the strip's target word) | Assignment (D3): Enter gives the words to Graphite as before; Alt+1 |
| staC (the strip's target word, the staC selector) | Assignment's Ctrl+Enter runs typed staC through the same path (D3); the `@` lead; Alt+2 |
| Kernel (the strip's quiet word) | Commands ▸ Run an operation… (Alt+3): the line in Assignment with the `/` lead; `help`, `ops`, Tab completion and the history as before (D3) |
| Find (the strip's quiet word) | Search (D3): Ctrl+K, Alt+4, the `?` lead; results under the line as you type, the workspace searched on Enter |
| Console (the strip's target word) | Shell (D3; Bash when the configured shell is bash): Alt+5, the `$` lead |
| Explore (the strip's quiet word, before D1a) | The programs list's Explore the workshop (D2), Tools ▸ Explore capabilities…, and the right-click's capabilities (D4): on a file, Open in *its adapter*, Find tools in the Tool Atlas, Explore capabilities…; on a record, Explore all capabilities |
| Log notes (the brief's Log: a note attached to a chosen event) | Replaced by the network (the owner, 2026-11-06): Log's Network stream; a chosen entry is pinned with Ask Stacy about this (D3); the brief's "Add note here" on a log event is, on the right-click, Ask Stacy about this · Show in Log · Its job › · Copy, and on a connection or packet Ask Stacy about this · Follow this conversation · Show the process · Copy address (D4) |
| Tools ▸ Type to (Graphite, staC, Kernel, Find, Shell) | Commands ▸ Writing Line (Assignment, Shell, Search, Log) and Commands ▸ Run an operation… (D3) |
| The cat's menu: the six tool groups (Work, Reason, Instruments, Programs, Knowledge, Configuration) | The cat's programs list (D2): every capability once, A to Z by its plain name, one small icon each |
| The cat's menu: Explore the workshop… | The programs list's last row, Explore the workshop (D2) |
| The cat's menu: New Idea, New Project | Work ▸ New Idea… (Ctrl+Shift+N) and Work ▸ New Project… (D2); the Work tree's, the cabinet tree's and Today's right-click (D4) |
| The cat's menu: the Services line, Graphite services ▸ On · Off · Reboot | System menu ▸ Graphite services On · Off · Restart; its word opens Service details (D2) |
| The cat's menu: Exit Graphite or Return to Debian, and the disabled "Log Out · Restart · Shut Down — not in this edition" | The System menu's separated group: Log out, Return to Debian or Exit Graphite, Restart, Shut down, live where logind allows (D2) |
| The System menu's list (D1): Stop everything first, Game last | Game first, Stop all jobs directly beneath, then the process list (D2) |
| The Menu key (the chain builder for the current room) | The right-click menu for the keyboard focus, and Shift+F10 (D4); Ctrl+Shift+Space and Commands ▸ Chain Menu open the chain builder alone |
| Today's right-click (the root chain menu) and Files' chains › | The empty place's right-click: on Today and the workspace's empty place the root itself (Your chains ›, Start a chain from ›, Writing line ›, Edit the Graphite menu…, Inquiries…, the two atlases); a folder in Files, in the Finder and the Library's empty place carry it whole as Root menu › (D4, D4-fix) |

## The integration (D2 to D5 together)

D2 (the cat, the programs list, the System menu), D3 (the writing line and Log), D4 (the right-click menu) and D5 (the network
capability, docs/NETWORK_01.md) were built, reviewed and fixed in parallel on one tree. Run together, the focused set,
check_desk_ui and the UI gate passed at once; where the items meet, the integration found these and fixed them at their cause:

- **The cat and the modes in one band** (the review of D3, finding 7, handed on): the band placed the cat by its drawing with
  the paws' graphite outline, which is graphite on the graphite band, so the cat you see (its pale coat) began a pixel inside
  the band's inset while the last mode word's ink ends exactly at it. `graphite_brand.cat_extent(params, outline=False)` and
  `cat_ink(rect, params, outline=False)` are now the pale coat alone (each paw's coat inside its outline, which is drawn on the
  paw's edge); `TypeBar.place_cat` and `ink_w` place and spread the cat by it, while the button's room and `CAT_BOX` keep the
  outline. check_desk_ui pairs the cat by its coat and measures both lower-band pairs again in the window's own pixels
  (`band_edges_drawn`: a column is ink where a pixel is `INK_LEVEL` of the way from the band's mean tone to the lettering):
  0 px at all nine sizes. The review's own probe, rerun, reads 0 at its thresholds 100, 110 and 170 (at 140 one anti-aliased
  column of the yellow mark when Assignment is chosen, as the review found; `v01_reruns/desk/integrate/probe/band_ink_thr_after.out`).
- **A long status message moved both panes** (handed on by D2-fix): a message shows in the working area's foot (`TypeBar.note`,
  the console's hint) on one line, so its whole length became the workspace's least width, and the desk narrowed both panes to
  the slots' floor (360 to 272 px at 1366 by 768 and at 1280 by 800) and left them there after the message went
  (`v01_reruns/desk/integrate/probe/status_squeeze*.json`). The hint wraps now (`console_qt`), asking only for its longest word.
- **The document room at 1366 by 768** (found by the review set's whole-word rule; the D4 captures showed it too): the saved
  list's line was cut at its time and the list scrolled sideways in its 230 px column, and the page's format words were
  squeezed to 26 px ("Bolc", "Ital"). The list wraps its lines; the format words are a `document_qt.WordRow`, one row while
  they fit and wrapping where the page is narrow, each word its own width.
- **Log's capture reason in a narrow window** (found by the review set, on the real capability): where the Network stream's
  lists stand one above the other (1366 by 768 and 1280 by 800, and at 20 pt), the capture's reason, five lines when capture is
  unavailable, was given two and cut, and an empty packet list took the room. The reason now sits in its own quiet scroll, as
  tall as its words up to three lines there (eight side by side), the rest reached by scrolling; while capture is unavailable and
  nothing was captured the empty packet list steps aside for it and the connections. `tools/ui_fit.cut_lines` finds a wrapped
  label given fewer lines than its words need; check_desk_ui asserts none in the working area in Half and Tall at all nine sizes.
- **Keys**: a probe of the live window's 77 key sequences (`v01_reruns/desk/integrate/probe/shortcuts.json`) finds no key two
  enabled window-wide actions share; Alt+1 to Alt+6, Ctrl+K, the Menu key, Shift+F10, Ctrl+Shift+F12, Ctrl+Shift+N and
  Ctrl+Shift+Space are each one action's.
- **Where the items meet, confirmed**: Log's Network stream reads D5's real operations in the window (the review set's 08: this
  computer's interfaces and connections and the capture's reason, here); D4's event, connection and packet entries use D3's
  `log_qt.entry_at`, `focus`, `ask_about` and `conversation` (check_context_menu_ui 07, on a real connection); D2's two menus
  stay point-mirrored and D4's menu shares their numbers (check_desk_ui step 01, check_context_menu_ui 08); D4's job entries
  live in D2's System menu (check_context_menu_ui 05, 05b); Master Stop ends a capture (test_network_watch: jobs.cancel and the
  work hold).

**The owner's review set**: `tools/desk_review.py` (on demand, not in the gate) writes build/graphite_desk/review/ in one run of
the real window with the checks' holds: each capture named for what it shows, every word in the window and its menus whole,
and review.json; build/graphite_desk/review/README.md names each capture, what to look at, and the choices made.

**Choices, and why (integration).**
1. *The cat is paired by its coat*: symmetry is what the owner sees, and on the band the cat is its pale coat; the outline stays
   in the cat's room, so no pose is ever cut.
2. *The foot's message wraps rather than elides*: an unavailable row's whole reason is read there (F1), and a message is short
   lived; a second line for a few seconds costs less than panes that move.
3. *The format words wrap as words*: at 1366 by 768 the page is about 390 px wide; a smaller face or fewer words would break the
   desk's rule that every word is whole and in print.
4. *The review set is its own tool*: it starts nothing and checks every word whole, but measures nothing the checks do not; the
   owner's set is made in one consistent run, while the checks keep their captures for their own steps.

## What the next items get

- D2: **the cat's room** is the desk's contract: the tile (`typebar_qt.cat_tile`, the cat's height × `CAT_RATIO`) is centred in
  the band's height, the button holds every pose, and the cat at rest is placed by its drawing (`TypeBar.place_cat`, from
  `graphite_brand.cat_ink`). A redraw keeps `cat_extent` (the parts as drawn, nothing below `GROUND`) inside `CAT_BOX`
  (test_desk asserts it) and updates `cat_extent` with the drawing; `check_desk_ui.cat_poses_inside` then checks every pose
  in the band. The symbol is `TopBar.nice` (desktop_header_qt.SystemButton). Built by D2: "The cat, the programs list and
  the System menu" above. For D4: New Idea and New Project are `host.a_new_idea` and `host.a_new_project` (the Work tree's
  right-click can add the same actions); the programs list's rows are `hatch.entries[key]` (QActions, navigation only) and
  `programs_qt.PLAIN` their plain names; a DeskMenu's numbers are `programs_qt.metrics(host)`.
- D3 (built: "The writing line and Log" below): the right slot's words come from `TypeBar.rows()` / `items()`; `place()`
  spreads any number by their ink and `fit_px` sets them smaller in a narrow window. A new band word is installed with
  `desk_qt.InkWord.install` and gets a whole word in `TypeBar.words`. Ctrl+K is `Shell2.search`, which hands it to
  `TypeBar.search` (Search).
- D4 (built: "The right-click menu" above): a new surface gets a finder in `context_menu.FINDERS`, a new kind of action a
  provider in `PROVIDERS`; actions dispatch through `context_menu.dispatch` with the target's `ident` and `revision`.
  D5: the Network stream's entries keep the fields the menu reads (`process`, `pid`, `remote`/`rport`, `src`/`dport`, …).
- Every item: the quiet-script rule (above): `shell2.QuietWords` for words that are a status or an explanation by turns,
  `shell2.Note` for a Context row you may skip, `script_room` for any other script label; the word Graphite is
  `shell2.Wordmark` (TopBar.wordmark).

## Checks and tests changed (integration)

- `tools/check_desk_ui.py`: `cat_span` is the cat's pale coat; new `band_edges_drawn` in step 01 at all nine sizes (the cat's
  coat and the last mode word, Tall and the first mode word, in the window's pixels at the words' ink level; desk-ui.json
  `band_edges_drawn`); step 08 shows a long message (an unavailable row's whole reason) and asserts the panes, the workspace and
  every pair unmoved and the foot's hint wrapped (`long_status_message`). `tools/check_graphite_ui.py`: the cat's place is its
  coat's.
- `tests_integrated/test_graphite.py`: `test_the_band_places_the_cat_by_its_pale_coat` (at 14, 18 and 20 pt the cat drawn where
  the band puts it shows its first pale column at the inset; placed by the outline, as before, a column later).
  `tests_integrated/test_writing_line.py`: `test_the_capture_reason_is_never_cut_and_an_empty_packet_list_steps_aside` (stacked
  and side by side the reason is as tall as its words in its scroll, the scroll no taller than its lines; the empty packet list
  steps aside while capture is unavailable, and packets bring it back: test_context_menu's packet right-click, which adds packets
  directly, found the first version hiding a list that had some).
- New: `tools/desk_review.py` (the owner's review set, on demand).
- `tools/ui_fit.py`: `cut_lines` (a wrapped label given fewer lines than its words need), used by check_desk_ui's
  `writing_line_pairs` in Half and Tall and by the review set for the whole window and every menu.
- `workbench/graphite_brand.py` (`cat_extent` and `cat_ink`, `outline`), `workbench/typebar_qt.py` (`cat_poses`, `ink_w`,
  `place_cat`), `workbench/console_qt.py` (the foot's hint wraps), `workbench/document_qt.py` (`WordRow`; the saved list wraps),
  `workbench/log_qt.py` (the capture's reason in its own scroll, `fit_note`, `NOTE_LINES`; the empty packet list hidden while
  capture is unavailable and none is shown). The last was found by the review set: in a narrow window or at a large text
  size, where Log's lists stand one above the other, the capture's reason (five lines when unavailable) was given two and cut
  (`v01_reruns/desk/integrate/probe/log_note_cut_before.json`: at five of six sizes; after, none).
- **The registry**: no operation or setting was added by the integration. `tools/record_registry.py` was run last, after every
  other change: `--check` found no difference and writing it gave the same bytes. Against the desk's base (fab801b) the record
  holds D5's additions: the operations `network.observe` (read), `network.capture.start` and `network.capture.stop` (execute)
  and `network.capture.read` (read); the job tool `network.capture` (113 job tools); `network_talk` among `agent.assign`'s
  profiles (its argument digest); 718 operations and adapters (714 before); the 43 settings unchanged.

## Checks and tests changed (D2)

- New: `workbench/programs_qt.py` (the two menus' one design, the programs list, the icons), `workbench/system_menu_qt.py`,
  `workbench/session_power.py`; `tests_integrated/test_system_menu.py` (21 tests: availability from a faked logind, no session,
  the system's own commands and never sudo, the one function, the leave flow before the command, cancelling, a refused
  command leaving Graphite open, availability asked again, the leave steps' order without closing, the System menu's order and
  scope words, order and niceness distinct, Stop all jobs reaching the Master Stop's action, Game, the services' rules, the
  session rows through session_power, the point-mirror placement, the shared numbers, the cat's colours and yellow only when
  awake to you), added to the focused set (`tools/check_hatch.py` FOCUSED_MODULES).
- `tests_integrated/test_launcher.py`: the Hatch menu's tests became the programs list's (flat, sorted, every capability once,
  type-to-select, the failed read, needs setup, the cat names no session or power command). `test_graphite`: Open programs, the
  three new modules under the rename guard, the palette with pencil yellow and the cat's colours. `test_operations`: the kill
  switch's words, Stop all jobs.
- `tools/check_desk_ui.py`: `menu_pairs` (Symmetry rule 6) at all nine sizes in step 01; step 05 (Game first, Stop all jobs
  beneath); step 13 (the cat's colours and contrast in the window's pixels, its poses, Reduce motion, one click from sleep, the
  keyboard and type-to-select, the System menu's order and availability, the leave flow before a faked command, refusal with no
  session, Stop all jobs, Game, Work's New Idea) and captures 09 to 14; desk-ui.json `cat_programs_and_system_menu`.
- `tools/check_hatch_ui.py` rewritten for the programs list (session_power.system held: only logind reads, no command);
  `tools/check_head_ui.py` (the System menu's order, the real Master Stop from its Stop all jobs row, the pale cat's pixels);
  `tools/check_frame_ui.py` (the list's rows, the services row in the System menu); `tools/check_graphite_ui.py` (Open programs,
  Agenda first, the focus mark net of the always-pink nose); `tools/check_rename_ui.py` (both menus' words). On demand:
  `check_navigation_ui`, `check_operations_ui`, `check_explore_ui`.
- No operation, setting, scheduler, store or process was added: the list reads `ledger.explore`, the System menu's section the
  existing `ledger.operations` read and the operations it already used; session and power ask logind and run the system's own
  two programs, only on the owner's confirmation.

## Checks and tests changed (D2-fix)

The review of D2 found: Log out ended Graphite before its close ran (no saved session, no paused assignments, no services
closed); the leave flow stopped the model and the tracked command before the confirmation, so Cancel lost them; Qt checks
opened the System menu with `session_power.system` unpatched, asking the real logind (they passed only where there is no
system bus); an unavailable row's reason could only be hovered; the services' Restart read the same as the computer's.

- `workbench/session_power.py`: the order above; `leave_steps` asks and stops nothing; `undo_leave`; `quiet_close` reports
  whether the window closed; `system(('where', program))`; `challenge` not offered in the dedicated session; the quit held
  across the close and the command. `workbench/system_menu_qt.py`: logind asked on opening only; unavailable rows reachable;
  the services' choices named with their scope. `workbench/programs_qt.py`: `MenuRow.set_unavailable` (quiet ink, the reason
  in the accessible description); `DeskMenu.pointer` (a resting pointer takes no row until it moves).
- `tests_integrated/test_system_menu.py` (21 to 32 tests): the order questions, confirmation, close, command; the quit held;
  Cancel, a refused close and a missing program stop nothing and issue nothing; a refusal after the close says why;
  `challenge` in the dedicated session; the questions stop nothing and Cancel puts back what they set aside; **on the real
  window** Log out's command comes after the close (the window hidden, the return copy taken, assignments paused, the
  services shut down, `brain.stop`, the session saved, the lease gone) and Cancel stops nothing; an unavailable row in the
  keyboard's order with F1 and the accessible description reading its reason; a resting pointer takes no row until it moves;
  the services' Restart named with its scope;
  **every Qt check that opens or builds the System menu holds `session_power.system` for its whole run** (a static rule
  over `tools/check_*.py`). Run on the reviewed D2 modules, 18 of them fail
  (`v01_reruns/desk/D2-fix/proof_tests_on_D2_code.log`).
- Checks: `check_desk_ui`, `check_head_ui`, `check_frame_ui`, `check_graphite_ui`, `check_navigation_ui`,
  `check_operations_ui`, `check_rename_ui` and `check_service_integration_ui` hold `session_power.system` (logind answers no
  session, on any computer; no command may start). A run of every Qt check with a probe on session_power's real paths found
  those eight reaching the real logind before (46 reads) and none after (`v01_reruns/desk/D2-fix/reach_probe/`).
  `check_desk_ui` step 13: the unavailable rows in the keyboard's order and F1's reason, the services' Restart's name, and
  the order with a fake logind: questions, confirmation, the (held) close, then `systemctl reboot`, with the quit held.

## Checks and tests changed (D1-fix)

- `tools/check_desk_ui.py`: the pairs by the band words' and the cat's ink and the word's optical size; at all nine sizes
  `drawn_as_designed`, `tab_marks`, `trash_drawn`, `cat_poses_inside`, `script_labels` (`clipped_ink`), `script_contrast`, no
  sideways scroll in either pane, every lower-band word whole; Conversation and Context, Half and Tall, and the System menu's
  list at every size (`faces_and_sizes`); the separators' resize cursor (`separator_cursors`, step 04); Ctrl+K's one-line Find
  (`ctrl_k_line`, step 05); the System menu's list's notes at one size (`one_size_notes`, step 10); Today's capture hint and the
  Files room's explanation in the script (step 10). `tools/symmetry.py`: `within` and `at_least`; `baseline` reads an InkWord.
  `tools/ui_fit.py`: a band word drawn by its ink has its whole box and is drawn regular.
- `tools/check_frame_ui.py`: the compact step asserts every strip word whole again at 1366 by 768 and 1280 by 720 with a room
  open (restored; the reach review found it loosened), the cat's button holding every pose; the held-state step reads the queue
  rows in the System menu's list. `tools/check_head_ui.py`: the cat's button holds every pose; the list's caption read as words.
  On demand: `tools/check_operations_ui.py` and `tools/check_navigation_ui.py` use the System menu's list for the rows, sliders
  and Earlier, and Activity's WORK line for the counts.
- `tests_integrated/test_desk.py`: the menu row takes an odd pixel in its gaps (no box widened); Trash's box is its drawing;
  BandWordTests (the letter size, its floor, `fit_size`, the symbol's height), CatTests (every pose inside the tile's room and on
  its ground), ActivityTests (the WORK line). `tests_integrated/test_graphite.py`: QuietWords' hanging indent and printed keys;
  no script label clipped (QuietWords, pleasantries); the word's capitals as tall as the symbol at 14, 18 and 20 pt.
- No setting was added or changed (the script switch is the existing appearance.cursive); no operation, scheduler, store or
  process was added (the System menu's list reads the existing `ledger.operations` read).

## Checks and tests changed (D1b)

- New: `workbench/pane_qt.py`; `graphite_brand.pointer_shape / pointer_angle / pointer_pixmap / pointer_cursor / use_pointer`.
- `tests_integrated/test_desk.py`: PaneTests (the tab row, the word size, the mark, the trees' rows, Trash, the feet, the
  parts) and PointerTests (the hotspot is the tip, the aim is 30 degrees, nothing beyond the click, the mark's facets under one
  similarity). `tests_integrated/test_graphite.py`: the pointer's pixels at 1x and 2x and the cursor's hotspot.
- `tools/check_desk_ui.py`: the pane and tree pairs at all nine sizes (and Activity's list rows at the trees' row height);
  the word Graphite's ink pairs at all nine sizes; the panes with each tab (pixels of the yellow mark); the homes (step 07);
  the quiet centre foot (08); the pointer (09); the quiet-script rule, on, off and on again (10); captures 05 to 08. The
  reopen is step 11.
- The quiet-script rule (the owner, 2026-11-06): `shell2.Wordmark`, `shell2.QuietWords`, `shell2.Note` and `quiet_html`;
  `desk_qt.WORD_PX / WORD_SCRIPT_PX / WORD_STROKE / word_px / word_stroke`; Activity's notes (operations_qt), the work list's
  captions and note (desktop_header_qt.NicePopup, also the System menu's list), the composer's hint (shell2.SlateFace), the
  Files room's and the viewer's notes (rooms, universal_viewer_qt, drawn by arc_desktop); control_qt re-styles them, the word
  and the Context face when the switch turns.
- `tools/check_machine_ui.py`: the strip's line is the Machine row's tooltip and each row's details its tooltip; Import and
  Export are Work entries; a setting is found from Find. `tools/check_rename_ui.py`: the face's tab reads Conversation.
  On demand: `tools/check_cabinet_ui.py` reaches Existing views and Import / Export from Arrange and Work;
  `tools/check_settings_ui.py` finds the Settings tab's tree where the filter was.
- `workbench/control_qt.py`: the Workspace setting Left column width applies to both panes at once (the desk's align).
- Found by the gate and fixed: a parentless moment of Follow latest showed it as a window (it closed the startup screen); the
  right pane's least width was read from a stale layout cache after a size excursion; with the foot quiet, a tall page made the
  window drop its separator under the head, fixed by the workspace's least height.

## Checks and tests changed (D1a)

- New: `workbench/desk_qt.py`, `tools/symmetry.py`, `tools/check_desk_ui.py` (in the UI gate, captures in build/graphite_desk
  or ARC_LEDGER_DESK_CAPTURE_DIR), `tests_integrated/test_desk.py` (in the focused set).
- `tests_integrated/test_frame.py`: the asymmetric column rules (column_cap, column_floor, library_floor, yield_to_centre,
  target_width, holder_widths) are gone, and their tests with them; the centre floor, elision, saved widths and the cat's size
  stay.
- `tools/check_frame_ui.py`: the columns are one width through the size excursion; a drag of either separator moves both; the
  setting sets both; the saved width restores both; the Tab walk starts at Line (Explore left); the fold into ⋯ is shown at
  1100 by 700 and 18 pt (at 14 pt all eight now fit there).
- `tools/check_head_ui.py`: the head's control is the System menu's symbol (no word, named System menu); the strip is the
  desk's band; the panes are one width.
- `tools/check_graphite_ui.py`: the mark is the erased symbol at the far right; the game opens from the System menu's list;
  the cat stands at the band's inset.
- `tools/check_hatch_ui.py` and `tools/check_explore_ui.py` (on demand): the Explore word is out of the band; its keys and
  routes are still checked.
- Small fixes found by the desk check: the right pane's "ACTIVE JOBS · in the order they started" and Today's capture hint
  wrap instead of clipping or pushing the page sideways in a narrow pane or workspace.
