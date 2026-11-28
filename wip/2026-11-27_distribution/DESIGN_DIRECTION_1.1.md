# Graphite 1.1 — design direction

*28 November 2026. The owner: "Think the functionality of windows, with the graceful class of Apple, and the freedom
power of Linux". Three designers answered that independently on 27 Nov (their full proposals are in
`partial/design/proposal_familiar.md`, `proposal_calm.md`, `proposal_power.md`); the judging round was lost to a usage
limit, so the coordinator decided. This file is the decision. Everything in it is the builder's design for the owner to
strike.*

## 1. The decision

**The base is "Familiar":** start from where a Windows-and-DOS person's hands already go, then make each of those
things graceful and open. It wins because the owner's hands decide what must exist. Two grafts:

- From **"Calm"**: the line on the bar finds and does everything, and every row says what Enter will do; a real
  terminal drops from the top edge on one key; whatever is summoned leaves when done.
- From **"Power"**: anything visible answers **Command…** with the exact line it is or runs, and from there one press
  keeps it as a word of the owner's, pins it, or binds a key. The power never looks like a cockpit: it is one row at
  the foot of a menu.

Refused: Calm's hiding of the side list and of Kas at rest (a Windows person looks for what is always there), and
Power's tiling and workspaces (a different desktop).

## 2. The screen

| Place | Its one job |
|---|---|
| **The bar** (bottom, 44 px; 40 at 1366x768; above every app) | the session, always within reach: Start, the line, the open windows, Kas with HALT, the tray, the clock |
| **The head** (32 px) | what can be done here: File, Edit, View, Go, Tools, Help |
| **The navigation pane** (left, 256 px) | where things are: Quick access, the Desk, This computer, the bin |
| **The centre** | the folder or the thing: one bar, tabs, List · Icons · Board, the split |
| **The details pane** (on call, 320 px) | the selected thing: preview, facts, connections |
| **Kas's panel** (the right edge, 380 px, over any app) | who works with you |

Start, flyouts and cards rise from the part of the bar that owns them and nowhere else. The bulletin board stays the
heart of the centre: it is the third view of any place (List, Icons, Board), one press away, and the details pane shows
a thing's connections in every view.

## 3. The grammar

- A click selects; a double-click opens (the default app, as in Windows; Graphite's own viewer is the default for PDFs,
  pictures and text); a right-click offers what can be done, in the Windows order, with Properties last and
  **Command…** above it; a drag moves; a drag with Ctrl copies.
- Windows' keys do what Windows hands expect, in Graphite and above every app (PLAN_1.1.md, W1). Menus show their keys.
- Every destructive act goes to the bin with Undo; what cannot be undone always asks.
- Kas's cards rise from her chip; her panel slides from the right edge; **HALT sits beside her name on the bar** and
  stops her and nothing else. Her rules do not move, only her furniture.
- Words: the owner's Windows or DOS word is accepted wherever something is typed, and the Debian word is shown beside
  it, so the bridge teaches itself away.

## 4. Grace

One type family (Inter; IBM Plex Mono for numbers, cells and lines), 1.0's tokens kept, with chrome cut from about
188 px to 116. One accent. Elevation, not glow, in Day and Night. Motion only where it means something (a card rising
from its owner, a panel sliding from its edge, a tile easing to a new size), 160 to 240 ms, off under Reduce motion.
Nothing under 11 px. Empty states that say what to do. The Graphite and Kasandra looks keep their character on the same
frame.

## 5. Freedom

Everything visible is also a name to type on the line, a line in a readable text file under `~/.config/graphite/`
(the bar's slots, the keys, the words, the looks), and a part that can be replaced. The Terminal is a real shell that
also understands DOS words and shows the Debian command it ran. Nothing is hidden: **Command…** on anything shows the
line behind it.

## 6. Kas

She is the reason to use it. On the bar: her name, her state word and shape, HALT. In her panel: what waits for you
first, then her work, findings and next steps, then her line. Her voice (PLAN_1.1.md, KV): sharp, sure, dry, never
bluffing. In preview 3 she reaches the whole box through recipes, a classified command tool, the system's own
permission prompt and the machine's manual pages.
