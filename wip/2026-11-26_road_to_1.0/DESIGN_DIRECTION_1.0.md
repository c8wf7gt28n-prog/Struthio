# Graphite 1.0 — design direction

*26 November 2026. The owner: "As we're building I want you to take more control of how the desktop is designed, as to
better reflect the system we're building." This is the builder's design direction for the rest of 1.0. Every slice
from here follows it; D1 applies it now, D2 polishes every surface at the end. The owner's own directions (their
picture, their head and footer, their paper) stand above it; where this file goes further, it is the builder's design,
labelled so in the release notes, for the owner to strike.*

## 1. What the window must say at a glance

Graphite is four things at once, and the window gives each one a fixed place:

| Place | Its one job | Holds |
|---|---|---|
| **Head** | the session and the authority | HALT (upper left), the menus, Apps ⊕ (upper right) |
| **Left** | where things are | Files (from "This computer /", Home open), Machine, Settings; the Desk drawer of records; DELETE |
| **Centre** | the thing, its neighbourhood, and working on it | the board (focus + neighbours), the working view, tabs and the split |
| **Right** | who works with you | Kas: her hologram, what waits for you, what she is doing, what she found, what comes next, her ask line |
| **Foot** | the computer's own line and vital signs | Line, Terminal, Search, Web, Log; the writing line; CPU GPU RAM TXT NET |

Nothing lives in two places. Kas is spoken to in her column only; the foot is the computer's line.

## 2. One language of states

Every state that matters has **one word and one shape**, the same everywhere (tiles, wires, her column, the journal,
the dock, the Machine), and a colour only as a third cue:

| State | Shape | Word | Where |
|---|---|---|---|
| recorded link | solid line | recorded | board wires |
| inferred link | dashed line | possible · not verified | board wires |
| current / supported | ■ filled square | CURRENT · SUPPORTED | tiles, findings |
| archived | — dash | ARCHIVED | tiles |
| refuted | ⊘ | REFUTED | tiles, findings |
| open question | □ empty square | OPEN | tiles |
| verified (done) | ✓ | done (verified) | steps, receipts |
| prepared | ○ | prepared | steps |
| sent, being checked | → | sent | steps |
| waits for your word | ◆ | NEEDS YOUR WORD | steps, her state |
| waits for your grant | ◆ with a key | NEEDS YOUR GRANT | steps, grants |
| needs your review | ◆ with an eye | NEEDS REVIEW | steps (a dialog seen) |
| blocked | ■ hollow-bar | blocked: <why> | steps |
| stopped | ▮▮ | stopped by you · stopped by HALT | steps, her state |
| held | ‖ | held | her work under HALT |

D1 makes these one table in the code (`workbench/state_words.py`), read by every surface.

## 3. Chrome that never stacks

At most: the dock (in the session), the head, and **one centre bar**. The centre bar carries, left to right: Back,
Forward, the breadcrumb; at board depth the board's counts ("7 recorded · 3 possible, not verified") and Whole desk; at
work depth Board, Find, zoom, Undo, Redo, Save, Save and Return, Full program, Split, Close. The board's own header row
and the second bar above a working view fold into it. The program-window strip lives in the dock; inside Graphite's
window it appears only when no dock can be made.

## 4. Kas's column orders by what needs you

From the top: her hologram with the equalizer behind her, her name, model and state word; then **"Waits for you"**, a
band that appears only when something does (a step that needs your word, your grant or your review; a question card),
each with its one press; then the exchange (last turns); ACTIVE WORK; FINDINGS (live); NEXT STEPS (up to four); the
six commands; her ask line. GRANTS and earlier turns are folds. When space is short (1366x768), the exchange gives way
first, then findings fold to their first two; what waits for you never folds.

## 5. The foot is the computer's line

The chooser reads **Line · Terminal · Search · Web · Log** (Kasandra leaves it: the owner, 26 Nov). **Line** is the
default and does what the old mode did for lines: a Graphite line (`this | count`), an operation by name (`/files.list`),
an address (to Web). Words that read as a request to her are not run: the line offers **Ask Kasandra →**, which moves
the words into her ask line and sends them there. The meters gain **NET**: online, offline, or "Kas: <host>" while her
fetch runs (K8's state), with a shape for each.

## 6. Looks

Day (the owner's picture) is the reference look for 1.0 and the look of a fresh profile; an owner's saved look is kept.
Graphite and Kasandra keep their character in the same layout. One family of type per look (Kasandra: the typewriter
face; Graphite and Day: the sans, with the fixed-width cut for numbers, cells and lines); nothing under 12 px at
1366x768; a state word is never cut short.

## 7. Empty and first states that teach

A fresh workspace never shows an empty grey centre: the board shows Home with one line, "Select something on the left;
what it is connected to appears here." Her column with no model says what she can still do and where her model is
added (Brain room → Add file). A board with one tile and no links says why ("nothing recorded links to it yet").

## 8. Motion

Motion means something: her shimmer while she works, static at a state change, a tile easing to its new size when
relevance moves it (never for less than the hysteresis band), wires drawing in when a focus changes. Nothing loops for
decoration. Reduce motion stills all of it.

## 9. The launch look: Day, refined to a system standard, and its Night twin

The owner, 26 Nov: "Day or other modes, I want you to create a default version that is apple/microsoft level refined
for the 1.0 launch." Graphite 1.0 launches in **Day**, rebuilt on one set of design tokens to the standard of a
first-party desktop, with **Night** as its dark twin from the same tokens. Graphite and Kasandra stay as characterful
alternatives. A fresh profile starts in Day; on the first start of 1.0 an existing profile moves to Day once, with one
line: "Graphite 1.0 starts in Day. Your earlier look is in Arrange ▸ Appearance."

**One source of truth.** `workbench/design_tokens.py` holds every colour, size, radius, shadow, duration and font
role for Day and Night; the style sheets and every painted surface (board, tiles, wires, her column, hologram glass,
meters, dock, menus, toasts) read from it. No colour literal outside it for these two looks.

**Type.** Inter (bundled, SIL Open Font License) for the interface, IBM Plex Mono (already bundled) for numbers, cells,
lines and the Terminal, with tabular figures. One scale, in px at 100 %: caption 11/14 medium (section labels in
capitals, +0.4 tracking); footnote 12/16; body 13/18; body-strong 13/18 semibold; subhead 15/20 semibold; title 17/22
semibold; title-2 20/26 semibold; display 26/32 Inter Display semibold (empty states only). Nothing under 11 px; body
never under 13 px at 1366x768.

**Colour, Day.** Window #F5F5F7; surfaces #FFFFFF; sidebar #F7F7F9; hairline rgba(0,0,0,0.08); control stroke
rgba(0,0,0,0.14). Text #1D1D1F, secondary #5A5A60 (≥ 6:1 on white), disabled #9A9AA0. Accent (selection, focus, links,
wires) #0A66D8; live and verified #1E8A4C (the picture's green, darkened for text contrast); waiting #A35A00; refuted
and danger #C62828. Board rings: accent at 9 % and live at 11 %. Every text pair ≥ 4.5:1, measured.

**Colour, Night.** Window #161618; surfaces #1F1F22; sidebar #1B1B1E; hairline rgba(255,255,255,0.08); stroke
rgba(255,255,255,0.14). Text #F2F2F5, secondary #A8A8AF, disabled #6A6A70. Accent #4C93FF; live #34C26A; waiting
#F0A63A; refuted #FF6B60. Same measured contrast rule.

**Space and shape.** A 4 px grid; paddings 8 / 12 / 16 / 24; column gutters 16. Radii: 6 for controls, 10 for tiles
and cards, 14 for panels, menus and popovers. Elevation: level 1 (tiles, cards) 0 1px 2px at 6 % plus 0 0 0 1px
hairline; level 2 (menus, popovers, toasts) 0 8px 24px at 14 %. No glow in Day or Night; depth comes from elevation.

**Controls.** Buttons 28 px tall: primary filled accent with white text (one per area at most), secondary tinted
(accent 10 %, accent text), plain (text only). Text fields 28 px, radius 6, stroke, a 3 px focus ring at accent 35 %.
The foot's chooser is a segmented control. Tabs underline 2 px in accent. Tree and list rows 26 px, the selected row an
inset rounded fill at accent 12 % with the text in accent (Day) or white (Night). Thin overlay scroll bars that show on
hover. Every control has hover, pressed, focused and disabled states, and a focus ring a keyboard user can follow.

**Icons.** One family of line icons, 16 and 20 px, 1.5 px stroke, drawn from Graphite's own glyphs, monochrome; colour
only for state.

**Motion.** 160 ms ease-out for hover and press; 220 ms for panels and depth changes; 240 ms for a tile easing to a new
size. Reduce motion turns all of it off.

**Her presence.** In Day, her hologram stands on its dark glass, edged with a hairline and level-1 elevation; in Night
she floats on the column as in the dark looks. The equalizer's bars take the accent and live colours.

**HALT** keeps the owner's green triangle and word in Day (red in Night would read as an error; it keeps the live
green there too); while held it reads RESUME with the triangle turned to ▶.

## 10. The two passes

- **D1 (now):** the foot without Kasandra (Line as default, Ask Kasandra →), NET in the meters, the one table of state
  words and shapes wired into tiles, wires, steps and her state, the one centre bar, the "Waits for you" band, Day as a
  fresh profile's look, the empty states.
- **P4 (after D1): the launch look** (section 9): the tokens, the fonts, Day rebuilt and Night made from them, every
  surface reading the tokens, the move to Day on 1.0's first start.
- **D2 (after every feature slice, before X1):** every surface in three looks at two sizes: overlaps, cut words,
  contrast, stacking, spacing on the 8 px grid; fixes made in place; a frame atlas for the owner.
