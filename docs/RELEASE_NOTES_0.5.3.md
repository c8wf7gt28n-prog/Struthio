# What's new in Graphite 0.5.3

November 13, 2026. Guide → What's New opens this page. The 0.5.2, 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6, 0.4.5, 0.4.4,
0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

Three parts of the window the owner asked to keep building: the top bar's middle, the right-hand pane, and the line at
the bottom where everything is typed. Then his answers about Stacy's free hand, which are recorded here and not yet
built.

## The head's middle is an equalizer

"In between, we have the text ... Let's just leave it out in the middle. Free up the space ... an equalizer, and make
its style pulse up and down to represent something."

The name and address that stood between the menus and Programs are gone from there. In their place is a small
equalizer, and what it represents is real:

- **Each bar is one processor thread of this computer.** Its height is how hard that thread worked over the last
  second. On the ThinkPad that is sixteen bars. When Stacy thinks, a calculation runs or a program is busy, the bars
  rise; at rest they lie low.
- The top two lamps of a bar are **amber**: a thread near its limit. A small mark above a bar holds the height it
  reached a moment ago and sinks slowly.
- The bottom row turns amber while **Graphite itself** has work running.
- It moves only when the readings move, and stops. With "reduce motion" it changes at once, with no glide.

**The name of what is open** is back in the bar above the work, where 0.5.0 took it from, said once. **Its address**
comes up at the head, in the equalizer's place, when you click that name; it goes away again when you leave it.

## The right pane is one view

"I don't think we need three options. Context and activity almost seem like they could be merged together, but then
talk seems like that could be merged with activity too."

The three tabs (Talk, Activity, Context) are gone. The pane has one title, **Stacy**, and one view:

- her face, what she speaks with, and her two rooms (Brain room, Full chat);
- **This:** the name of what is open, or of the sheet selected in the Field: what "this" means to her. **more** opens
  everything about it (what Context was);
- **Now:** what is running and what waits for you. **open** goes to what waits; **activity** opens the whole list
  (what Activity was);
- then the conversation.

While the whole of Context or Activity is up, the title reads **‹ Stacy · Activity** and a click on it comes back. Her
name is said once: the title says it, so the line beside her face no longer does.

## The line at the bottom: you choose whom you are typing to

"I like the idea of one master typing line that I select whom I'm typing to."

Five names stand at the left of the line, each whole at every window size tried: **Stacy · Terminal · Search · Web ·
Log**. The one that is lit is who gets the words. (They read "Assistant", "[>_] Terminal", "[=] Log"; Search had no
name of its own on a narrow window.)

- **Web** is new. An address is opened, and words are searched for, **in this computer's own browser**. Graphite
  itself fetches nothing. If no browser answers, the line says so and keeps what you typed.
- **An address typed anywhere goes to Web by itself**: type `https://…` or `www.…` while on Stacy and the line
  switches.
- **The arrow at the end of the line says what it will do** (Ask Stacy, Run it in the Terminal, Search the workspace,
  Open it in your browser, Filter the Log). When what you typed reads as staC, the line says "runs as staC", the arrow
  turns **green**, and pressing it runs the line. Words in your own language still go to Stacy to answer.
- **No key is named on the line**: not in its hints, its tips or the list that opens under it. The keys work as before.
- Only the chosen name is lit (Stacy's used to stay lit while Search was chosen).

Log already holds two streams, Graphite's events and this computer's network. A separate system log is not built.

## Stacy with a free hand: the owner's answers (recorded, not built)

To the three questions in the 0.5.2 notes, the owner answered on 13 November 2026:

- **What still asks:** "anything that can't be undone, by rule, would always force" her to ask: emptying the Trash,
  anything leaving the computer. Not every Terminal command: "some terminal commands are reasonable for" her "to have
  control over".
- **Whether she acts unasked:** yes. "I kind of want her to be autonomous", noticing things.
- **Her model:** Qwen3.6-35B-A3B at Q4_K_M, as a GGUF file. Read from search results on 13 November 2026 and not
  tried: the file is about 21 to 22 GB depending on who made it, and one comparison says it wants about 24 GB of
  memory at a 16k context, which the ThinkPad's recorded memory (about 61 GiB) has room for. Whether the bundled
  runtime reads the file is not known: the Brain room shows it there.
- **The first journey he wants:** "ask her to get me started on a project in a program that I may not be particularly
  familiar with. I get a starting point in that program, and then I can work from within Graphite for basic
  operations, or the actual program window."

One phrase of that message did not come through dictation clearly ("be able to pick up this DSF if we could find it");
the builder has asked what it names.

The build that follows from these answers is the next one: the dial (Ask first · Do and show · Free hand), each act of
hers one line in a trail with one Undo, a list of Terminal commands she may run unasked, and the first journey above.

## Still open from the walk round the ThinkPad

Not built: the System menu regrouped; small versions of programs such as GIMP and Godot in Programs; glyphs on the
names of the panes and of the line.

## What was checked, and what was not

The probes run the real window offscreen at 1920 by 1200 and 1366 by 768. New ones cover the equalizer (it is shown, it
rises when another program works a thread hard, the address appears only while typed and from a click on the name),
the pane (one view, the two lines, the way back) and the line (five names whole and in order, each chosen alone, an
address going to Web, the browser asked with the right address, no browser, the arrow green on staC and running it, no
tip on the line naming a key). Twenty-three tests cover the parts added since 0.4.9, two of them the equalizer's
readings; the line's own tests grew by two. The project's own tests and the window gate were run on the exact commit
before this set was cut: see the set's START_HERE for the numbers.

Not seen: any of it on the ThinkPad's own panel; the equalizer has only been watched in a container with four
processor threads. The browser was stood in for in the checks: no real browser was opened. No second reader has gone
over 0.4.7 to 0.5.3. Tips deep in the older rooms may still name a key.
