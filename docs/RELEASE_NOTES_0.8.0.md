# What's new in Graphite 0.8.0

November 14, 2026. Guide → What's New opens this page. The 0.7.0, 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.9,
0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

## Kasandra: a second appearance

"How do you feel about going in this direction … I think I really like the LAIN/kasandra idea." And, with the
wordmark: "If you like the logo use it."

**Rules ▸ Desk artwork ▸ Appearance** now offers **Graphite** and **Kasandra**. The choice is kept for this computer
(not for one project) and is used from the next start; choosing it offers to start Graphite again at once (it saves the
window first). Graphite, the appearance you have, is unchanged.

In Kasandra:

- **Her palette.** Ink and pale blue on deep indigo, from your pack's palette. The colours part by meaning, where in
  Graphite all three were amber: **cyan** marks what is selected, has the keyboard or is ready; **raspberry** marks a
  decision that waits for you (Approve, and the lamp in the Field's head that says something waits); **lavender with a
  dashed edge** marks a sheet that must be worked again (a recheck), and a wire gone stale. The settings and cabinet
  pages, which wrote Graphite's colours by hand, take hers too.
- **Her art follows the work.** Your eight stills are in the program, and which one shows is decided by the state of
  the work, not at random:
  - at rest: the quiet bench by the rainy window;
  - while something waits for your Approve: her hand paused above Enter;
  - while she answers, a job runs, or a what-if is up: comparing her notebook with the screen;
  - for twenty seconds after an Approve that went through: the pencil set down;
  - for forty-five seconds after a refusal or a failed job: checking a loose cable.
  
  Waiting for you outranks everything; a fresh refusal outranks work that runs; work that runs outranks a fresh success.
  Her face at the top of her pane changes with it (a close crop round each still's focal point), and so do the
  worksheet's evidence rail and the Field's rail when there is room for it beside the sheets.
- **The Office** (Home, Today) shows her office, at dusk or in the rain: they take turns each time the Office is opened
  again, and keep one while it stays open. **Your wordmark**, "kasandra protocol" in circuit traces, stands at the foot
  of it.
- **The Field** carries her wires and rooftops, faint, behind its heading.
- **Her name is Kasandra**, wherever a sentence shows the assistant's name: the typing strip (Kasandra · Terminal ·
  Search · Web · Log), the menus ("Ask Kasandra about this…"), her pane's title, the meters' cards, and what the model is
  told it is called. What is history keeps the name it was written with (the Agenda's stored
  lines, her trail).
- **Headings in a typewriter face.** The greeting, the Field's heading and the workspace's title are set in Special
  Elite, the worn typewriter face from your pack. Values, cells, receipts and controls stay in IBM Plex.

Clean shows no art in either appearance, as before. ASCII draws her quiet still in characters.

**How a still is shown.** A still is shown only from inside the pack's folder, only if it is a picture, and only if its
bytes match the SHA-256 in the pack's catalog; a changed or missing file is passed over for the next in the order
(the still made for that place and state, then that place's default, then the quiet still, then the plain ground).
Each still is decoded once (about 17 ms here) and kept (the last three), then scaled to the size it is shown at (about
2 ms) and kept at that size (the last sixteen). The time of every decode is kept, for the 35B campaign's comparison of
runs with art on and with Clean.

**What is not done.** The pack's idea that the model may suggest one of the eligible stills alongside its answer is
written (a suggestion is taken only if it names a still offered for that place and state, and only while the view it
was asked for is still the view), but no model turn asks for one yet. No still changes with an animation: a change of
state swaps the picture. The appearance cannot change in a running window: every page is built in its colours when
Graphite starts.

## Her monogram, her column, and two more colours

"This could be the icon for the programs menu … Maybe icons in kasandra column if they look good and kool."

- **Programs** wears your "kp" monogram in Kasandra, in its own colours (the k pale, the p violet, the trace teal), cut
  from its dark ground so it sits on hers. Graphite keeps "[#] Programs".
- **Her column** has two of Graphite's own glyphs, in her cyan: a framed square beside **This** (what is open) and a
  play mark in a hexagon beside **Now** (what runs and waits). I tried a chip beside what she speaks with and sliders
  beside her hand as well; beside her face the room is short and her hand's words were cut, so those two are not there.

"Should we welcome more colors like a yellow that matches her hair and more shades of violet." Yes, each with one job,
so that a colour still says something:

- **Honey**, from her hair, is hers: the left edge of her answers in the conversation, and the mark under her name on
  the typing strip when she is the one you are typing to.
- **Violet**, from your monogram, is the desk's structure: section headings and the Field's column titles; the greeting
  in a pale violet; your own messages on a deep violet with a violet edge; the equalizer's bars, which rise from violet
  to cyan at their tops.

Graphite keeps every colour it had.

## A line is a line

The language of the lines you can run is no longer named anywhere in the window. It is all still there and still
growing; it is simply called a line: the arrow says **Run this line** and "· runs as a line", the Field's button is
**Line**, the console's prompt is "line ›", what she shows under an answer is "the line that reads it", and her model's
line says only which model she runs on. Her model is told to call a line a line. A sweep of the running window (every
label, tip, placeholder, accessible name and menu line, on Home, in the Field and on the typing line, in both
appearances) finds the name nowhere.

## Smaller

Two keys were still printed on the Office page, under the jot box ("Ctrl+Enter keeps it · Ctrl+Shift+N from anywhere")
and in the Continue card ("Ctrl Alt V"). They are gone; the keys still work.

## What was checked, and what was not

A new probe walks Kasandra in the real window at 1920 × 1200 and 1366 × 768: her palette and face are in force; the
typing strip says Kasandra; asking for a change puts her hand by Enter and lights Approve in raspberry; pressing it
puts her pencil down and marks the two calculations that read the cell for a recheck, in lavender with a dashed edge;
while she answers she takes notes; after a refusal she checks the cable and, later, rests; her pane's title says
"‹ Kasandra · Context"; Clean shows no art. Every page the earlier probes visit was looked at in Kasandra. New tests
cover the choice of appearance, the palettes, the catalog's checks (a changed byte, a missing file, a broken catalog,
a path outside the pack), the order of states, the crop, the cache, and her name in both appearances.

Not done: nothing later than 0.4.6 has run on the ThinkPad. Whether Debian's own PySide6, if the ThinkPad uses it
instead of the bundled one, can read WebP pictures depends on the package qt6-image-formats-plugins; with the bundled
PySide6 it can. The Field's rail shows art only when the sheets leave it room; with the After Hours 07 desk (five
columns) they do not, at either size, in either appearance.
