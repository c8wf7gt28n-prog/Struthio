# The Kasandra look as it is now (0.8.2, d1df337), in frames

The frames come from a copy of HEAD at `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/tree`. The harness (`nomodel.py`) loaded the After Hours 07 workspace with `GRAPHITE_APPEARANCE=kasandra`, no model, the Illustrated desk and interface size 14 pt. I ran it at 1920×1200 and at 1366×768.

- Probe: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/scripts/look_frames.py`
- Logs with all numbers (the `FACTS_JSON` line): `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/run1920.log` and `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/run1366.log`
- To put Talk cards in the right column without a model, I ran the Field's Trace twice (`field_page.trace`, field_page.py:402-411). The answer goes through the no-model route (shell2.py:2597-2601).
- Nothing under /home/user/Struthio was touched.

## 1. Where everything sits (window coordinates: x, y, width, height)

| Part | 1920×1200 | 1366×768 |
|---|---|---|
| Head band | 0,0,1920,60 | 0,0,1366,60 |
| Left column | 0,61,354,1078 | 0,61,354,646 |
| Centre | 355,61,1210,1078 | 355,61,656,646 |
| Right column | 1566,61,354,1078 | 1012,61,354,646 |
| Typing line (foot) | 0,1140,1920,60 | 0,708,1366,60 |
| Left: tree's box | 16,126,322,960 | 16,126,322,528 |
| Left: foot / Trash box | foot 0,1086,354,53; Trash 236,1094,102,29 | foot 0,654,354,53; Trash 236,662,102,29 |
| Right: content / foot | content 1582,71,322,1015; foot 1566,1086,354,53, always empty | content 1028,71,322,583; foot 1012,654,354,53 |

Both columns are 354 px wide at both window sizes. That is 18% of the window at 1920 and 26% at 1366. The width comes from one rule for both columns (desk_qt.py:31, 162-170, 484-519).

The right column has no title row when nothing else is open in it (shell2.py:3470-3475; pane_qt.py:233-234), so her column starts 10 px under the head.

## 2. Home, Field and Files: the whole window

**Home** (frames F01)
- The centre shows "Good morning." in the typewriter face at 34 px, then the Office banner: her still with the "kasandra protocol" wordmark at its foot (boss_qt.py:166-170, 83-94). Under it come "JOT IT DOWN" and four cards.
- At 1366 the banner shrinks to a 96 px strip and the cards scroll.
- Left column: 13 tree rows, then plain ground down to a red Trash at the lower right.
- Right column: an 84 px picture square, "no model yet" and "does and shows", then the "This:" and "Now:" lines, then her greeting card. Below that it is empty.

**Field** (frames F06 and F07)
- Head band: "FIELD WORK APPS NETWORK" in the mono face, "After Hours 07 · waiting" in the typewriter face, all over a faint still of wires.
- The sheets sit in five columns, with the cyan glow and wires.
- The Field's foot holds "Do / Doubt / Trace…" as mono buttons and a mono line.
- The rail for her picture is 0 wide at both sizes: it gives way to the sheets.
- At 1366 the sheets scroll both ways and the foot keeps only Do, Doubt and Back.

**Files** (frames F10)
- "Files" as a 28 px typewriter title, a row of underlined links, and two folder icons (Egress, Slate). Over 700 px of the centre is empty at 1920.
- The body text says "Deleting moves to Trash".

## 3. The left column, and the empty place under the tree

What is there:
- Tab words "Files Machine Settings" in IBM Plex Mono 15 px. The face is set in code (pane_qt.py:122-126).
- Tree rows in the typewriter face at 16 px, each with a faint cyan halo (pane_qt.py:445-477).
- Her "power lines": poles, crossarms and sagging drops, with the live path breathing (pane_qt.py:369-442, 294-301). Rows are 28 px tall and each level indents 27 px (pane_qt.py:84-86, 494).
- A red can and the word "Trash" in the typewriter face at 16 px. The word is drawn in code (trash_can_qt.py:60, 115-120); its accessible name and tooltip say "Trash" too (trash_can_qt.py:51).

Empty height under the last tree row (measured inside the tree's own box; the 53 px foot comes on top):

| Tree state | 1920×1200 | 1366×768 |
|---|---|---|
| Files, as the workspace opens (13 rows) | **596 px** (empty band y 490–1086, x 16–338) | **164 px** (y 490–654) |
| Files, top level only (11 rows) | 652 | 220 |
| Files, everything open (27 rows) | 204 | 0 (it scrolls) |
| Machine tab | about 700, read from the frame | about 275, read from the frame |
| Settings tab | 0 (scrolls) | 0 (scrolls) |

- The foot is 53 px tall. Only its right 102 px hold Trash, so its left 220 px are empty too.
- From the top of the empty band to the bottom of the window foot: 649 px at 1920 and 217 px at 1366 (frame F14).
- **Fit for the hologram:**
  - At 1920 the 322 px width is the limit: the whole 800×875 image fits at 322×352. Cropped to the figure's own bounds it fits at 322×436.
  - At 1366 the 164 px height is the limit: 150×164 whole, or 121×164 cropped to the figure. If the figure may stand into the empty left of the foot: about 198×217.
- **The owner's reference patch at these sizes.** It needs at least 150 px of free height and draws at most 288×316 (kasandra-hologram.patch:84-106).
  - At 1920 it would draw 288×315 at the bottom of the tree's box.
  - At 1366 its free height comes to 135 px, so with the tree as the workspace opens it shows nothing.
  - It shows nothing on the Settings tab, or when the tree is open far enough to scroll.

## 4. The right column, and how much room her words get

What is there now:
- **Picture row:** 84×84 px with a 1 px edge (boss_qt.py:246-250, 290-297), beside "no model yet" (18 px) and "does and shows" (16 px). The row plus its spacing is 94 px tall (shell2.py:1784-1794).
- **At rest the picture does not show her.** The resting still is "quiet_window" ("A quiet bench beside the rainy window", tagged empty; catalog.json:19, 201-223), zoomed 2.2× (boss_qt.py:293). Close up it is a dark window with power lines and city (frame F08c). She appears only while she works, waits for Approve, has just finished, or is blocked.
- **"This:" and "Now:" lines**, each with a 17 px cyan glyph (shell2.py:1756-1773, 1804-1806).
- **Conversation:**
  - Her cards: card fill, a honey left edge, rounded corners (theme2.py:127, 140).
  - Your bubbles: violet, pushed right by a 30 px margin and a 1:5 stretch (shell2.py:1912-1913; theme2.py:126).
  - A 14 px gutter on the right of the thread (shell2.py:1816) and 12 px padding inside each card (shell2.py:1723).

| Measure | 1920×1200 | 1366×768 |
|---|---|---|
| Height above the conversation | 181 px on Home; 196 px when the "This:" line wraps (18% of the column) | same 181–196 px (**30%** of the column) |
| Conversation box | 322×817 | 322×385 (312 wide once the scroll bar shows) |
| Text width / characters per line, her card | 280 px → **28 characters** (typewriter 18 px, about 9.45 px each) | 270 px → **27** |
| Text width / characters per line, your bubble | 206 px → 21 characters | about the same |
| Line pitch | about 18.5 px for 18 px type (very little leading) | same |
| After two Traces | "3 earlier · show them"; only the last question and answer kept; **292 px empty under her last card** | "4 earlier"; one card, **cut off 38 px at the bottom**, scroll bar showing |
| Empty on Home under her greeting | 787 px | 355 px |
| All cards unfolded | 1258 px of thread in 817 (scrolls 441) | scrolls 873 |

- **Why the space stays empty.** The fold keeps only whole items (shell2.py:1886-1899). The previous answer is about 530 px tall, so it does not fit in the 292 px left.
- **What taking the picture out gives back.** At most 94 px of height, if "no model yet" and "does and shows" move elsewhere; about 50 px if they keep their two rows. The width does not change, because the picture sits only in the top row.
- **Characters per line if width is found elsewhere:** dropping the 14 px gutter gives 31; the column's whole content width (322 px) gives 33. The right foot's 53 px (pane_qt.py:589, 650) is the other spare room.

## 5. The typewriter face and the mono face together

| Place | Face and size as measured | Note |
|---|---|---|
| Head menus (Work … Guide) | Special Elite 16 px | The code asks for 18 px (shell2.py:633-635); the window's 16 px rule for tool buttons (shell2.py:293) evidently wins. |
| Left tab words | **IBM Plex Mono 15 px** | Set in code (pane_qt.py:122-126). It is the only mono text in the left column and sits right above the typewriter rows. |
| Tree rows, Trash | Special Elite 16 px | |
| Right column: every line, her cards, your bubbles | Special Elite 18 px ("does and shows" 16 px) | |
| **The line in her card** (violet slab) | **Special Elite 18 px**, not mono | `setFont(mono_font(15))` at shell2.py:1944 loses to the window style sheet's `QWidget {font-family:…}` (reading_preferences.py:108-113) plus the 18 px rule for card labels (shell2.py:328). The slab breaks mid-word ("kind,tit / le,state,by", "owne / r:db5f66"). Frame F17. |
| Trace rows in her card (file names, page numbers, "cells B2, B3") | Special Elite 18 px | Numbers are in the typewriter face here. |
| Typing line: chooser words / the box | Special Elite 16 px / **Plex Mono 16 px** | The placeholder "prompt" is intended (text_prompts.py:2). |
| Meters (CPU GPU RAM TXT) | key words Special Elite 12 px, readings Special Elite 14 px | boss_theme.py:230 asks for Plex on the readings; it does not show (sizes come from desktop_header_qt.py:116-117). |
| Home | all Special Elite: 34 px greeting, 20 px card titles, 16 px body, 13 px "JOT IT DOWN" | The Ingress card's folder path (an address) is in the typewriter face. |
| Field | sheet titles and head title in the typewriter face; tags (SOURCE, SHEET, CURRENT), notes, file names, FIELD/WORK tabs, foot buttons, the foot's line and "Whole desk · 90%" in Plex Mono | Frames F15 and F16. |
| Files page | Special Elite 28 px title, 16 px links | |

How the two sit together:
- At these sizes they take almost the same width per character: Special Elite 18 px about 9.45 px, Plex Mono 16 px about 9.6 px (31 characters in 298 px). Columns of both line up well.
- Special Elite is lighter and rougher, with almost no leading. Plex is crisper and reads heavier at small sizes.
- On the Field cards the split reads clearly: typewriter for names, mono for tags.
- In her column there is no mono left at all. The line and the numbers are told from her prose only by the violet slab.

## 6. The Apps mark in the head, close up (frames F04, F04b, F04c)

- Button 54×60 at x 1850 (1920) or 1296 (1366), icon 36×36, no word; its accessible name is "Apps" (shell2.py:585-592).
- The ink is 32×30 px: a pale grey-lavender "k" (about #c7c3d3), a violet "p" (#9980c6–#aa8dd9), and a thin teal trace arching over them with a tail off the foot of the p.
- Behind it: band #141734 for the top 40 px, a soft glow down to #2f4a65, then a 2 px cyan rule #83eaff at y 58–59.
- The current monogram is loaded straight from the file with no checksum check (shell2.py:587).
- The wordmark is loaded the same way (boss_qt.py:77-80). Only the stills are checked against their recorded SHA-256 (kasandra_art.py:103).
- The kasandra README has no SHA-256 entry for kp_monogram.png (branding/kasandra/README.md:13-14). The file's SHA-256 is 7c5b3c9c…a073.

## 7. The owner's pictures, for a designer

**hologram.webp**: 800×875, SHA-256 b73f7108… (matches).
- **Alpha:**
  - The background is fully clear: 376k of 700k pixels are under alpha 32.
  - The figure is almost fully opaque (alpha 253), so it is **not see-through**. A hologram look has to come from how it is drawn.
  - Anything visible lies within x 86–680, y 22–826, so the figure takes about 74% of the width and 92% of the height.
  - The bottom fades out: centre-column alpha falls 253 → 19 between y 755 and 825, with horizontal streaks.
  - The baked-in glitch lines are about a dozen short ticks at the silhouette's edges, about 2–3 px tall and 15–40 px long. They fall below one pixel once the picture is under about 300 px tall, so animated static has to be drawn in code.
- **Colours:**
  - Blue-violet lavender, average #716390; 85% of the coloured pixels have hue 240–259.
  - Highlights about #9789b9, shadows about #3d3356.
  - Pink-red circuit traces on the left cheek and the neck (#854d72–#bb6483, about 1.9k px).
- **Glow that the app will not show:** 32k fully clear pixels carry coloured fringes (24k blue, 6.8k pink). Viewers that ignore alpha show a glow, as the `holo_view/hologram.png` copy did when I opened it. Drawn properly it has none (frames `holo_over_ground.png` and `holo_alpha_mask.png`).
- **At smaller sizes:**
  - 160–316 px tall: face, smile, hair and straps read well; the traces become pink smudges.
  - 96 px: still a face, soft.
  - 36–48 px: only a lavender bust shape.

**kp_logo.png**: 1254×1254, RGB with **no alpha**, SHA-256 94d7bfb3…afaa.
- **Ground:** flat #070221, darker than the head band (#141734). Placed as it is, it would show as a dark box; it needs cutting from its ground, as the old monogram was.
- **Overall shape:** all the artwork lies within x 259–977, y 417–881. Trimmed with a 10 px margin it is 739×485, about 1.52 wide to 1 tall. That is a wide mark, not a square.
- **Parts:**
  - Cream "kp" (#fef1e3), 409×413 px, stems 54–71 px thick.
  - A violet trace (#7635fe / #702bfe) runs right from the foot of the p: one 13–17 px line, one 6 px line, a 34 px end dot and a smaller one.
  - A pink ostrich (#fd366c), 323×460 px, walking left: neck 16 px, legs 10–11 px, a 13 px dark eye, three dark circuit lines across the body (6–9 px) ending in dots.
- **What survives at small sizes:**

  | Part | 36 px tall (whole mark 55 px wide) | 48 px tall (73 px wide) |
  |---|---|---|
  | "kp" stems | 4–5 px, crisp | 5–7 px, crisp |
  | Ostrich neck / legs | 1.2 px / 0.8 px hairlines | 1.6 px / 1 px |
  | Violet thick trace / thin trace / end dot | about 1 px / vanishes / 2.5 px | 1.3–1.7 px / 0.6 px / 3.4 px |
  | Circuit lines inside the bird | gone, a slight smudge | mush |
  | Eye | about 1 px | 1.3 px |

  The "kp" is solid at both sizes; the bird reads as a pink silhouette.
- Squeezed whole into today's 36×36 square, the artwork comes out about 21×13 px, too small (`kp_square_36_x6.png`). The wide mark wants about 55×36 px of room.

**portrait.webp**: 800×1421, no alpha, ground about #141535, SHA-256 c5be9f95…. The same face down to the waist, without glitch lines. I would not use it now: the hologram has the alpha the lower left needs. It would only matter for a solid still somewhere else later.

## 8. Saved frames

All under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/`.

At 1920×1200, in `out1920/` (F01–F14 also exist at 1366×768 in `out1366/` with the `_1366x768` suffix):
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F01_Home_Window_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F02_Home_Left_Column_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F03_Home_Right_Column_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F04_Apps_Mark_Actual_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F04b_Apps_Mark_x6_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F04c_Apps_Mark_In_Head_x3_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F05_Head_Band_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F06_Field_Window_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F07_Field_With_Talk_Cards_Window_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F08_Right_Column_With_Talk_Cards_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F08b_Right_Column_Unfolded_Top_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F08c_Right_Column_Face_x4_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F09_Left_Column_In_Field_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F10_Files_Window_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F11_Left_Column_Files_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F12_Left_Column_Tree_Expanded_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F13_Left_Column_Machine_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F13_Left_Column_Settings_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F14_Lower_Left_Empty_Band_1920x1200.png`

Only at 1920×1200:
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F15_Field_Card_Faces_x2_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F16_Field_Foot_Faces_x2_1920x1200.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/out1920/F17_Talk_Card_Line_Slab_x2_1920x1200.png`

Studies of the owner's pictures, in `art/`:
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/holo_over_ground.png` (the hologram as the app would draw it)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/holo_alpha_mask.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/holo_alpha_ignored.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/holo_on_ground_36.png`, `…_48.png`, `…_96.png`, `…_160.png`, `…_240.png`, `…_316.png` (same folder; the size in pixels tall)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/kp_trimmed.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/kp_trimmed_h36_x6.png` and `kp_trimmed_h24_x6.png`, `kp_trimmed_h30_x6.png`, `kp_trimmed_h48_x6.png`, `kp_trimmed_h64_x6.png` (same folder; the trimmed mark at that height, enlarged six times)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/kp_letters_h36_x6.png`, `kp_letters_h48_x6.png`, `kp_bird_h36_x6.png`, `kp_bird_h48_x6.png` (same folder)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/kp_square_36_x6.png` and `kp_square_48_x6.png` (same folder)
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/old_monogram_36_x6.png`
- `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_read/frames/art/portrait_view.png`