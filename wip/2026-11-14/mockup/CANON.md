# Graphite · the canonical direction

*The finished desk in the Kasandra appearance, on the owner's ThinkPad, where Graphite is the whole desktop session.
Approved by the owner on 14 November 2026 ("I approve!!!"), who asked for more screens and menus to be drawn and the set
saved as the canonical direction. This file, the ten screens and `canon.css` are that direction.*

The ten on one page: `canon_sheet.png` (from `canon_sheet.html`).

---

## 1 · What this set is, and how to use it

The first screen is the one the owner approved: an evening, Thursday 14 November, 23:41, the night Rev C of the rail
limits arrived. The other nine were made from it to show the desk's other screens and menus open. Each was checked against
the base and against the others, so that the ten tell one story with one set of numbers.

Not every feature on them exists yet. They are the direction, drawn to look buildable rather than fantastic. They use the
real faces, colours, hologram and kp. Every element on them is in 0.8.3 already, or on the release road below, or listed in
section 5 as drawn but not yet given a release.

**How to use it:**
- **A build is judged against these screens.** When a release brings a surface drawn here, its check puts the real window
  beside the screen. A difference in colour, word, face, place or state is a defect, unless the owner chose it.
- **A screen changes only with the owner's approval.** No builder edits `canon.css`, `perfect_desktop.html` or a screen in
  `screens/` on their own. A proposed change is made as a copy beside the screen and shown to the owner. Once he approves
  it, it replaces the screen, and this file records the change.
- **A new screen joins the set the same way:** it is made as in section 4 and shown to the owner, and it joins only when he
  approves it.
- **Where a screen and the rules in section 3 disagree,** the disagreement is listed in section 5 until the owner settles
  it. Nobody settles it by editing the screen alone.

**The files** (all in `wip/2026-11-14/mockup/`):

| File | What it is |
|---|---|
| `perfect_desktop.html`, `Graphite_finished_desktop_mockup.png` | the approved base (3840×2400) |
| `canon.css` | the shared look: faces, colours, the head, the left column, the Field, her column, the writing line |
| `screens/01…09_*.html` and `.png` | the nine screens made from the base; each PNG is the record (3840×2400) |
| `render.js` | the renderer |
| `canon_sheet.html`, `canon_sheet.png` | the ten on one page, with the story's order and the key |
| `CANON.md` | this file |

---

## 2 · The ten screens

### The story they tell

After Hours 07: a 12 V rail on the bench, the evening Rev C of its limits arrived, and the morning after.

| When | Screen | Her state | Her dial |
|---|---|---|---|
| Tue 12 Nov 18:20 | (05 looks back to this moment) | | |
| Thu 14 Nov 14:02 | Rev C arrives; two findings go to recheck | | |
| Thu 23:12 | 02 · right-click, then a line | quiet | Ask first |
| Thu 23:20 | 03 · Apps from the kp | quiet | Ask first |
| Thu 23:30 | 04 · her plan, asking first | waits for you | Ask first |
| Thu 23:41 | 00 · the approved base | at work | Do and show |
| Thu 23:44 | her hand is done: 5 acts, the desk put back as it was | | |
| Thu 23:45 | 08 · sharing a signed receipt | done | Do and show |
| Thu 23:47 | 01 · the Rules menu, her hand | quiet | Do and show |
| Thu 23:50 | 05 · the desk as it was | quiet | Do and show |
| Thu 23:58 | the owner leaves the desk ("as you left them at 23:58") | | |
| Fri 15 Nov 02:00–04:12 | the night shift: recheck, Ingress read as text, the exam, the backup test | | |
| Fri 07:42 | 07 · Today, the morning brief | waits for you | Do and show |
| Fri 09:05 | 09 · a datasheet in quarantine | waits for you | Do and show |
| Fri 10:15 | 06 · live at the bench | at work | Do and show |

**The numbers every screen uses.**
- **Bench readings:** rail 12 V; settled current 280 mA; startup current 650 mA (the live meter reads 662 mA ±0.35%, its
  own tolerance); startup duration 110 ms ±5 ms (the owner's tolerance).
- **Limits:** the startup pulse is limited to 120 ms in Rev A, 80 ms in Rev B and 100 ms in Rev C (arrived Thu 14:02). The
  continuous limit is 6 W in all three.
- **Findings:**
  - settled power 3.36 W (84/25) under 6 W: holds;
  - startup power [7.57, 8.04] W against 8 W: cannot tell, and the startup current settles it most often (89%);
  - the startup pulse is over Rev C by 5–15 ms: does not hold (before Rev C it was over Rev B by 25–35 ms);
  - settled current ceiling ≤ 500 mA at 12 V;
  - the margin on the settled draw: 2.64 W.
- **The two findings Rev C sent to recheck:** the pulse, and "The reviewed sheet keeps the 80 ms condition". Both no longer
  hold after the night's recheck.
- **The open question:** what stretched the startup pulse?
- **Receipt ids already in use:**
  - 7f3a… the pulse against Rev C;
  - 2e91… the pulse against Rev B, Tue 21:52;
  - 3d71… Tue 17:46, as the records stood;
  - 9c0a…, e3f2…, 5d17…, b20e… the night's four acts;
  - 51c8… the bench margin.

  The owner's key is 4f2a…91c0. A new screen never reuses an id for something else.

### What brings each element

New elements are marked with the release that brings them, from the plan of 14 November
(`wip/2026-11-14/TALK_next_coming_future_one_hour.md`):

| Release | What it brings |
|---|---|
| 0.8.4 | tests you can believe, with the colour-vision check |
| 0.8.5 | her door on the Field (goals, acts, her ring, Stop, Put my window back) and the ThinkPad check |
| 0.8.6 | maths in lines (exact, range, solve, check), tolerances as the owner's records, a receipt on every answer |
| 0.8.7 | goals over data (verdicts, recheck, which reading settles it) and quarantine for outside material |
| 0.8.8 | changes through her hand, DELETE's exact Undo, Forget |
| 0.8.9 | her question, and the experiment |
| 0.8.10 | the floor |
| 0.9.x | the night shift, the time slider, receipts you can share, her character file, missions |
| the road to 1.0 | passes P11–P20, for example KiCad, LibreOffice, Godot and Blender opening as rooms on the desk (P11), and mail read through quarantine (P15) |
| after 1.0 | kp at the bench (instruments as sources, the next measurement), kp that sees, kp that listens, kp on the phone, kp as a protocol, kp that designs experiments |

**Already in 0.8.3, on every screen:**
- **The head:** the eight menus (Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide), the equalizer, and the
  neon kp that opens Apps.
- **The left column:** Files, Machine and Settings, the Concern tree, and DELETE.
- **Her hologram,** with its five state colours, static, scan lines and tear.
- **Her column's masthead:** her name, the cursor, the state word, and the model line with her dial.
- **The writing line:** its chooser (Kasandra, Terminal, Search, Web, Log), the red send arrow, and the CPU, GPU, RAM and
  TXT meters.
- **The Field:** its five columns, its faces (Field, Work, Apps, Network), its wires, Trace and its foot.
- **The look:** the typewriter faces, burnt yellow, the catch and the surge.

**New on every screen:**
- the KP meter, her share of the machine, and "on mains" in the head (neither yet given a release; see section 5);
- the TONIGHT card (the night shift, 0.9.x);
- "listening · say "Kas" or type" (kp that listens, after 1.0).

**Not drawn on any screen, though the set rests on them:**
- 0.8.4's tests and colour-vision check: every meaning here also has a word or a shape;
- 0.8.5's ThinkPad check;
- 0.8.9's question and experiment;
- 0.8.10's floor: the hologram under 2% of a core, and a Field frame in 16 ms;
- 0.9.x's character file and missions;
- the phone and the protocol, after 1.0.

### 00 · The approved finished desk
`perfect_desktop.html` · `Graphite_finished_desktop_mockup.png` · Thu 14 Nov 23:41 · at work

The owner asked "what changed in Rev C, and does the startup pulse still fail?" and she is at work on the Field: cyan base,
cyan cursor, Do and show. All five columns are filled:
- material, including a live bench meter and Rev C marked new;
- tables, with Rev B archived and Rev C current;
- three calculations;
- four findings with their verdict badges;
- the open question.

The sheet she selected has a yellow edge, and her ring marks her next click. Below the Field are the time slider and the
foot, with the selected finding, its buttons and the line that produced it with its receipt. Her column holds:
- WHILE YOU WERE AWAY;
- the owner's question on its violet slab;
- her hand card: three goals met, not met and undecided, five acts with the fifth next, Stop and Put my window back, and
  the cost;
- TONIGHT.

**New:**
- her ring, goals, acts, Stop and Put my window back (0.8.5);
- exact calculations, ranges, solve, verdict badges, and the line with its receipt (0.8.6);
- recheck, "settles it most often", and Rev C read as text in quarantine (0.8.7);
- the time slider, Share as receipt, and the away and TONIGHT cards (0.9.x);
- the live meter on the Field and "two hypotheses · a test separates them" (after 1.0).

### 01 · Rules menu, her hand
`screens/01_head_menu_rules.html` · Thu 23:47 · quiet

Rules is open from the head with nine rows, each with a violet glyph and its value on the right: Desk artwork
(Illustrated), Glow (Neon), Appearance (Kasandra), Her hand, Reduce motion (off), Tired eyes (off), Colour vision,
Night shift…, Tolerances….

"Her hand" sits on the burnt-yellow bar under the pointer. Its submenu offers:
- Ask first, Do and show (ticked) and Free hand, each with one faint line saying what it means;
- What always asks…;
- Her trail….

The menu is caught 18 ms into its 150 ms catch. Behind it is the Field after her run: her card reads DONE 23:44 with 5 acts
and the desk put back as it was, the owner's own selection is back on the pulse finding, and the wires are plain again.

**Already in 0.8.3:**
- the Rules menu, Desk artwork, Glow, Appearance and Reduce motion;
- the dial with its three places, What always asks, and her trail (the code calls it "What she did");
- the menu glyphs and the catch.

**New:**
- Tolerances… (0.8.6);
- Colour vision (with 0.8.4's colour-vision check);
- Night shift… (0.9.x);
- Tired eyes (on the look track, no release yet);
- her DONE card (0.8.5).

### 02 · Right-click, then a line
`screens/02_right_click_then.html` · Thu 23:12 · quiet

Files is shown as a list (Name, Kind, Changed, Size, Address), and the CSV of the bench readings is selected. Its right-click
has the file at the top, then Open, Ask Kasandra about this…, Rename…, Delete, Then (on the yellow bar under the pointer)
and More.

The Then panel beside it shows:
- the line on its royal slab, `@files:07 Bench readings.csv | rows | where unit=mA | count`;
- a preview ("count gives 1 row");
- five steps: Back a step, Keep rows where, Sort by, Count, Count by;
- four endings under a hairline: Show it, Put it in the writing line, Copy the line, Copy the rows.

An INSIDE preview shows the CSV's four rows. Her card, "QUIET · NOTHING OF MINE RUNS", says what the desk knows of the
file, and that she reads it first and then asks before she acts.

**Already in 0.8.3:** nearly all of it: the Files list and its action line, the right-click and Then with their glyphs
(0.8.1).

**New:**
- "the 5 ms on its duration is yours" (0.8.6);
- "2 findings on that sheet to recheck since Rev C" (0.8.7).

### 03 · Apps from the kp
`screens/03_apps_progman.html` · Thu 23:20 · quiet

Apps has dropped from the neon kp, caught 30 ms into opening. The kp has a burnt-yellow edge under it, and its ghosts spread.
The panel has:
- a "find an app" search;
- six labelled columns of tiles:
  - Work: Files, Field, Documents;
  - Think: Library, Calc, Calculator;
  - Make: Writer, Godot, Blender;
  - Build: KiCad, Bench, Terminal;
  - Move: Web, Delivery;
  - Set up: Machine, Settings;
- KiCad under the pointer, in the yellow edge;
- cyan "open" marks on the rooms already open;
- the STRUTHIO ARCADE strip with Play.

The panel opens over the Field and never over her column. Behind it is the Field before her run: the pulse finding still
rests on Rev B, in recheck, and is the owner's selection. Her card is "NOTICED · NOT YET DONE", with Recheck now and Leave it
for tonight.

**Already in 0.8.3:** Apps from the kp (a flat A–Z list), the kp's catch and the jousting game.

**New:**
- the shelf as six labelled columns with a search (direction only, not yet on the road);
- rooms that open in their full windows and come back to the desk, with their "open" marks (P11);
- Bench (after 1.0);
- the recheck she offers (0.8.7) and "for tonight" (0.9.x).

### 04 · Her plan, asking first
`screens/04_ask_first_plan.html` · Thu 23:30 · waits for you

The owner typed "trace the bench readings and put the limits side by side". Her dial is at Ask first, so nothing has moved:
she waits for you, with a pink base and pink cursor.

Her card, "MY HAND · ASK FIRST", shows:
- two goals with empty marks;
- four acts, each marked "offered": select 07 Bench readings, trace it, then select 07 Limits Rev B and compare it with
  Rev C;
- Go ahead (yellow edge) and Not now;
- "Go ahead · acts 1–2, then I ask again" and "touching the window voids this offer";
- the cost, with the goals marked as the model's pick.

Four faint dotted cyan rings, numbered, show where her clicks would land: "her plan · 4 clicks, none made".

**New:** all of it comes with 0.8.5: the one small model question that picks the goals, the planner over acts, the rings,
and the offer that a touch voids. The dial is in 0.8.3 already (0.6.0).

### 05 · The desk back then
`screens/05_time_slider_then.html` · Thu 23:50, showing Tue 12 Nov 18:20 · quiet

The time slider has been dragged back. A violet band reads "THE DESK AS IT WAS · Tue 12 Nov 18:20 · read only", with a cyan
"back to now". The Field shows how it stood then:
- readings at r3;
- Rev A archived, Rev B current, and no Rev C;
- the meter "not kept as records";
- the pulse not holding against Rev B, by 25–35 ms.

The slider has day marks, the knob at Tuesday, the pink Rev C tick ahead of it, and a cyan "now" end. The foot keeps Trace,
Its receipt and Beside now; Doubt, Range, Check and What if are greyed, because each would make a new record. Her card, WHAT
YOU KNEW THEN, lists the limits and verdicts of that moment and what has happened since.

**New:** the time slider and the read-only past (0.9.x), over receipts and verdicts (0.8.6–0.8.7).

### 06 · Live at the bench
`screens/06_bench_room.html` · Fri 15 Nov 10:15 · at work

The Bench room is live:
- three instruments as sources, each with its own tolerance;
- Scope 1's capture 03 drawn with Rev C's 100 ms limit, and the part over it shaded pink;
- a dashed honey card, "read from a picture · proposal", ≈ 108 ms ±3, with neutral Confirm with a reading and Not this;
- NEXT MEASUREMENT, ranking the startup current at 89% and the rail voltage at 78%, with a finer pulse reading struck out
  because it "can't change the verdict";
- the bench log, with time, value, instrument, tolerance and what went into the record on every row.

She is at work and listening. She heard "Kas, margin on the settled draw?" and answers "2.64 W under the continuous limit —
from the 10:12 reading and Rev C". Her working and her receipt mark which words are the model's and which number is a
line's.

**New:**
- the Bench room, instruments as sources and the ranked next measurement (after 1.0);
- the picture read as a proposal (kp that sees, after 1.0);
- voice (kp that listens, after 1.0).

Which reading settles a verdict comes first with 0.8.7. The Today tab, the foot and Trace exist.

### 07 · Today, the morning brief
`screens/07_today_morning_brief.html` · Fri 07:42 · waits for you

Today opens with "Good morning. Three lines from the night.":
1. Rev C's two rechecks were worked again, and neither holds.
2. Last night's backup restored clean.
3. One decision for you: record a tolerance for the startup current, or measure it again.

Each line has its "show" and an evidence row with verdict badges. Below them are:
- the night shift's log, 02:00–04:12, with a receipt for each act;
- "nothing changed your records";
- a TODAY strip with the Agenda and the recent receipts.

Her card repeats the three lines, with neutral Record a tolerance, Measure again and Later, and is marked "written from the
night's 4 receipts · no model words". A second card says what each choice does.

**Already in 0.8.3:** the Today page, the Agenda and the Log.

**New:**
- the night shift and its three morning lines (0.9.x);
- recording a tolerance (0.8.6).

### 08 · Sharing a signed receipt
`screens/08_share_as_receipt.html` · Thu 23:45 · done

The SHARE AS RECEIPT sheet rises from the foot's pressed button, joined to it by a thin yellow lead, over the dimmed Field.
It is for "Startup pulse over Rev C by 5–15 ms · does not hold", and has these sections:
- WHAT LEAVES: two cells, each with its source file, revision and short hash;
- THE LINE, on its royal slab;
- THE VERDICT, with its working and "no model involved";
- SIGNED, by the owner's key, which stays on this ThinkPad;
- WHAT DOES NOT LEAVE;
- THEIR VIEW, a preview of a colleague's Graphite receipt reader with its three cyan ticks;
- AS OF.

At the foot are Put in Egress (yellow edge) and Not now, with "nothing is sent until you send it from Egress". She is done,
with a honey base, and her card says none of the receipt is hers.

**New:**
- receipts you can share, the signature and the free reader (0.9.x);
- the line and its receipt (0.8.6).

Egress and the foot exist.

### 09 · A datasheet in quarantine
`screens/09_quarantine_ingress.html` · Fri 09:05 · waits for you

Ingress shows `datasheet_mosfet_v3.pdf`, which came by email: "not used until you say". The centre is its plain-text copy,
with line numbers:
- the words in her typewriter face, and the ratings table in fixed width;
- a note where a script was removed;
- lines 29–31 edged pink, "ADDRESSED TO ASSISTANTS · shown, never obeyed".

The side panel lists:
- what kp did;
- the three choices, all neutral: Keep as material, Keep without the flagged passage, and Forget it in red ("cannot be
  undone; asks");
- the sealed original with its hash.

She waits for you. Her card begins "I read this as text only", and its words are marked as the model's.

**Already in 0.8.3:** Ingress, and originals kept sealed in a private quarantine on arrival.

**New:**
- the plain-text copy, the flagged passage and the choices (0.8.7);
- Forget (0.8.8);
- the night's reading of Ingress (0.9.x);
- mail arriving through quarantine (P15).

---

## 3 · The rules the set embodies

### Colours: each means one thing

| Colour | Value | Means | In the set |
|---|---|---|---|
| burnt yellow | bar `#e2a72e` with dark ink `#171b3c` in menus; elsewhere edge `#e2a72e` with words `#ffd27a` | where you are; selected | the open menu title, the row under the pointer, the selected tab, the tree's selection (on brown `#5a3f0c`), the owner's selected card, the slider's knob, the writing line's box |
| cyan | `#83eaff`, words `#b9f4ff` | ready; at work; live wires; her ring | HOLDS, her base at work, glowing wires while she works, the "now" end, "open" rooms, the head's and writing line's rules |
| pink | `#fa507c` | waits for the owner; does not hold; open question | DOES NOT HOLD, NEW material, her base when she waits, "offered", "waits for you" |
| violet | `#ab8eda`, deep `#5f4fa8` | the desk's structure; cannot tell | column titles, card headings, glyphs, CANNOT TELL (dashed violet edge), her base when quiet, the owner's words on a deep violet slab |
| lavender, dashed | `#c3b6f4` | recheck | RECHECK, and a dashed lavender edge |
| honey | `#e9b872` | hers | the left edge of her cards, her proposals (dashed until confirmed), her base when done |
| royal purple | `#7b4fd8` on slab `#271a58` | a line | every line, in the foot, in Then, in a receipt |
| red | `#ff3b5c` | DELETE and the send arrow | DELETE, the send arrow, Forget, her base when stopped |

- **The grounds:**
  - `#171b3c` her indigo, for the window;
  - `#1b1f45` for panels, `#1f234d` for cards and `#292d56` for raised things;
  - `#11132c` for her column and the line's box.
- **Rules and words:** rules are `#3b4479` and `#5969a1`; words are `#e3e3ff`, quiet `#c1c6e8` and faint `#9ca3d2`.
- **Wires** are plain blue (`#5a8fc4`, 70%). They glow cyan only while she is at work, or while a Trace surges.
- **Never lay yellow thinly over cyan or blue:** it reads green. Her ghosts cross the yellow bar as added light, never as
  cyan mixed over it.
- **Every meaning also has a word or a shape** (a badge, a glyph, a dashed edge), so no colour carries it alone.
- **Buttons:**
  - A yellow edge marks the step that carries out what the owner started (04's Go ahead, 08's Put in Egress), or the
    next step for the selected thing (the foot's Share as receipt).
  - A choice that waits on him is neutral (06, 07, 09).
  - Forget is red.

### Her states

| State | Base and cursor | Her column's top says | On screens |
|---|---|---|---|
| quiet | violet | quiet | 01, 02, 03, 05 |
| at work | cyan | at work | 00, 06 |
| waits for you | pink | waits for you | 04, 07, 09 |
| done | honey | done | 08 |
| stopped | red | stopped | none yet |

- Her base, her cursor, the word at the top of her column and the caption under her always agree.
- The caption starts with her state word, then a short note, as in "at work · her hand on the Field" and "waits for you ·
  one decision from the night".
- Her card's title says what her hand is doing: "MY HAND · ON THE FIELD", "MY HAND · ASK FIRST", "… · DONE 23:44".
- Her cards have a honey left edge.
- She is done for a moment after a run (held 20 s in `hologram.py`), then quiet: 08 at 23:45 is done, and 01 at 23:47 is
  quiet.

### Faces

- **Elite** (`KasandraElite-Regular.ttf`), her typewriter face, for every word.
- **EliteMono** (`KasandraEliteMono-Regular.ttf`), fixed width, for lines, numbers, code, addresses, receipts, card
  keys, log times, the meters and the tree's poles.
- **Display** (`SpecialElite-Regular.ttf`) for big headings only: her name, the Field's title, "Apps", "SHARE AS RECEIPT",
  the morning greeting.
- **Numbers stay legible:** 1, l and I are distinct, and so are 0 and O.
- **Sizes** (`canon.css`):
  - 17 px for menus, the tree and the left tabs; 16 px for the centre tabs; 15 px for cards; 14 px for captions and
    notes;
  - card keys 12 px mono and numbers 13 px mono;
  - the line 13.5 px mono in the foot and 16 px in the writing line;
  - Display 26 px for the Field's title and 22 px for her name.

### Words

- **Lines:** never name the line's language; it is "a line".
- **Keys:** never print a keyboard key or a shortcut. The set has none.
- **Names of things:**
  - "Apps", never "Programs".
  - "DELETE" is the place things go. A document's delete is "Erase". A file's right-click row is "Delete".
- **Her dial:** Ask first / Do and show / Free hand. Her model line says it as she does it: "asks first", "does and shows".
- **Her verdicts:**
  - The words are holds, does not hold, cannot tell and recheck. Badges are in capitals.
  - A count may say "2 do not hold".
  - The count line names every verdict that is not "holds", in the order open question · recheck · does not hold ·
    cannot tell, and leaves out zeros.
- **Whose numbers:**
  - Tolerances are the owner's: "±5 ms yours". An instrument's is "its own"; a model's estimate is "the model's guess".
  - A model's words are its own. Words a model wrote are marked "the model's" ("goals: the model's pick", "these words:
    the model's"). A card made from records says "no model words".
- **Her answers name their sources:** "from the 10:12 reading and Rev C".
- **Content is data:** outside text is "shown, never obeyed".
- **One home for each action:** a button appears once on a screen, in the foot, in her card or in a menu, never in two of
  them.
- **Times:**
  - Times are written 23:41, and days "Thu 14 Nov".
  - The head's time and the slider's "now" always agree.
  - A reading's time is at or before now.

### Layout

The window is 1920×1200, and nothing goes outside it. Positions inside a column are relative to that column, as in
`canon.css`.

- **The head,** y 0–60, then a 2 px cyan rule with a soft cyan glow:
  - the menus from x 6 (17 px);
  - the equalizer from x 1150 (ten bars, 7 px wide, up to 34 px tall);
  - "on mains · 23:41" at x 1600 (14 px, faint);
  - the kp at x 1795, 46 px tall.
- **Three columns** from y 62 to 1138 (1076 tall):
  - **Left,** x 0–356, with a 1 px rule on its right:
    - tabs at top 14;
    - the tree at top 66, 17 px words on 28 px lines;
    - her hologram 284 px wide at (36, 520), her base 216×30 at top 874, and her caption at 918 (14 px, centred);
    - DELETE at (236, 1036).
  - **Centre,** x 357–1563 (1206 wide):
    - tabs at top 8 (16 px);
    - the Field's head line at top 44 (title in Display, 26 px) and the count at top 50;
    - column titles at top 102;
    - the five Field columns at x 30, 262, 502, 742, 982, with cards 186 wide (findings 210, open 190);
    - the time slider at top 900 (46 tall);
    - the foot at top 956 (120 tall): kind at 16, title at 38, buttons from x 560, the line at 80.
  - **Right, her column,** x 1564–1920, on her darker ground `#11132c`:
    - her name at (18, 14), the state word at x 226, and the model line at top 46;
    - cards 328 wide from x 14: WHILE YOU WERE AWAY at top 76, the owner's words at top 212 (x 58, 284 wide), her
      card at top 296, and TONIGHT at top 760;
    - the voice line at top 1032.
- **The writing line,** y 1138–1200, with a 2 px cyan rule on top:
  - the chooser from x 20;
  - the line's box at x 404, 1190 wide and 38 tall, with a burnt-yellow edge (16 px mono);
  - the send arrow at x 1600;
  - the meters from x 1664.
- **Menus and panels:**
  - **Where they open:** a menu opens from where it was asked (the head's foot, the row under the pointer, the kp).
    Menus, panels and sheets open over the centre and never over her column. A menu may cover the desk behind it, as a
    real one would (01 covers part of the Field).
  - **Rows:** head-menu rows are 38 px at 17 px; desk menus (the right-click, Then) are 34 px at 16 px. Each row has one
    violet glyph. The row under the pointer is the burnt-yellow bar with dark ink, and its glyph takes the bar's ink.
  - **Sheets:** a sheet starts from its button, joined to it by a thin yellow lead (08).
- **Finish:** nothing overlaps that should not, no word is clipped, and nothing spills out of a card.

### Motion

Motion is never needed to understand anything: every state also has a word, a colour and a shape.

- **The catch** (`menu_catch.py`, 0.8.2):
  - Every menu and Apps opens at once and works from its first instant. For 150 ms, light only is laid over it.
  - The frame is lit brightest. A violet tracking band (up to 26 px, its middle at 0.10 h + 0.34 h·f) passes down behind
    the second and third rows, with a bright line in it.
  - For the first 60% of the catch there is a faint cyan copy of the far edge. A child menu's band sweeps in from the side
    nearest its parent.
  - The kp catches with Apps: its cyan and magenta ghosts spread, then settle.
  - When a line lands in the writing line, its edge flashes for 260 ms.
  - A still draws the catch frozen early (01 at f = 0.12, about 18 ms; 03 at f = 0.20, about 30 ms), with the bright
    line between rows, never through a word.
- **The surge** (`field_qt.py`, 0.8.2): Trace made visible.
  - A small white point leaves the farthest source and follows the wire already on screen, lighting each branch as it
    reaches it.
  - At the far end the light peaks and blooms into the gaps between cards. Then the middle of each wire goes dark before
    its ends: 0.70 s travel, 0.15 s peak, 0.50 s decay.
  - A fine line then stays along the route until the selection moves.
  - All of it is drawn under the cards.
- **The hologram** (`hologram.py`, 0.8.3):
  - Static lands on her figure only, redrawn four times a second from six patterns. Scan lines drift down every frame,
    with a slow flicker under 4%. Her base breathes with the tree every 2.8 s.
  - At work: the drift is faster, a write band rises through her every 2.4 s, and the breath is twice as fast.
  - Waits for you: the static is faint and held, with no flicker, and her cursor breathes with her base.
  - Done: one lock sweep, top to bottom, in 0.6 s.
  - Stopped: dimmed and half grey, still.
  - Quiet and at work: a tear now and then.
- **The equalizer** shows true heights. Each bar is something that moves (CPU, kernel, RAM, SSD, network, GPU), and rates
  sit on a fixed scale, so a quiet machine lies low (01, 02) and a busy one stands high (00, 06).
- **Reduce motion,** and the Clean glow:
  - no catch, and no surge: the settled route is drawn at once;
  - the kp is still and her cursor is steady;
  - her hologram is one still frame, and a change of state changes only its colour.

---

## 4 · How a screen is made and rendered

1. Copy `perfect_desktop.html` to `screens/<nn>_<name>.html`.
2. Link the shared look with `<link rel="stylesheet" href="../canon.css">`, and change image paths to
   `../../../../branding/...`.
3. Keep the head (menus, equalizer, "on mains · time", the neon kp), the left column (tabs, tree, her hologram, DELETE),
   her column and the writing line. Change only what the screen needs: the centre, an overlay, her card, her state and
   caption, the time.
4. Put the screen's own styles in a `<style>` block after the link. Never edit `canon.css`.
5. Render, from `wip/2026-11-14/mockup/`:

   ```
   node render.js screens/<file>.html screens/<file>.png 2      # the record, 3840×2400
   node render.js screens/<file>.html <scratch>/<file>_1x.png 1 # a preview, 1920×1200, to look at
   ```

   `render.js` opens the page in Chromium through Playwright at 1920×1200, waits for the faces, and writes the window at
   the scale given: 2 for the record, 1 to look.

   The faces, her hologram and the kp are read from the repository's `branding/` by relative path, so a page renders
   rightly only from its own place: `mockup/` for the base and the sheet, `mockup/screens/` for a screen.
6. Look at the 1× preview. Fix every overlap, clipped word, overflow out of a card and misalignment, and render again until
   it is clean.
7. Check the screen against section 3 and the story in section 2: the time, her state in all four places, the dial, the
   counts, the receipt ids.

The contact sheet is rendered with `node render.js canon_sheet.html canon_sheet.png 1`.

---

## 5 · Open, for the owner

The set does not settle these yet. Each needs the owner's word; until then the screens stay as they are.

1. **The "Rev C · 14:02" label on the time slider.** Its pink tick runs through "14:02" in the base, 01, 03, 04 and 08.
   The fix is one line in `canon.css` (`#time .ticklab{top:35px}`), and it changes the approved base.
2. **LIVE is pink.** `canon.css` draws the LIVE mark and its dot pink (`.card.live`, `.dot`), while the rules say cyan
   means live. 06 keeps pink on purpose, while its scope trace and bars are cyan. One choice, applied everywhere.
3. **The base's count line.** At 23:41 it says "1 open question · 2 recheck · 1 does not hold". The Field shows one
   RECHECK card, and the cannot-tell finding is left out. By the count rule it would read "1 open question · 1 recheck ·
   1 does not hold · 1 cannot tell", as 01 and 08 do.
4. **Her tear.** Every screen draws a faint tear across her face. In `hologram.py` a tear comes only when she is quiet or
   at work, but 04, 07 and 09 (waits for you) and 08 (done) show one. Either those states gain a faint tear, or those
   screens lose it.
5. **Stopped.** It is the one state no screen shows.
6. **Drawn but not yet on the road:** the KP meter, "on mains" in the head, the Apps shelf as six labelled columns with a
   search, and the Tired eyes setting.
7. **Two menu sizes.** Head menus are 38 px rows at 17 px; desk menus are 34 px at 16 px. They stay two sizes unless the
   owner wants one.
8. **The calendar.** "Tue 12 / Thu 14 / Fri 15 Nov" are 2024's weekdays; 14 November 2026 is a Saturday. No screen prints
   the year (09's made-up datasheet says "March 2026"), so nothing reads wrong on screen.
