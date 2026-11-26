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

## 9. The two passes

- **D1 (now):** the foot without Kasandra (Line as default, Ask Kasandra →), NET in the meters, the one table of state
  words and shapes wired into tiles, wires, steps and her state, the one centre bar, the "Waits for you" band, Day as a
  fresh profile's look, the empty states.
- **D2 (after every feature slice, before X1):** every surface in three looks at two sizes: overlaps, cut words,
  contrast, stacking, spacing on the 8 px grid; fixes made in place; a frame atlas for the owner.
