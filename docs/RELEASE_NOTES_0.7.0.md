# What's new in Graphite 0.7.0

November 13, 2026. Guide → What's New opens this page. The 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7,
0.4.6, 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

## The System menu is gone

"How much of the system menu could we move into clickable: cpu/gpu/ram/text? Could we eliminate the system menu if we
got creative."

All of it could move, so it is eliminated. The right end of the head now holds only **Programs**. Each thing went
behind the meter it is about, and what is about no meter went where a person would look for it:

| It was in the System menu | It is now |
| --- | --- |
| The process list (what runs and waits, niceness, the queue's order) | click **CPU** |
| Stop all jobs | click **CPU** (first on its card; also Tools ▸ STOP / KILL, as before) |
| Background CPU | click **CPU** |
| Open Agenda, Work trail | click **CPU** |
| Graphite services: On, Off, Restart | click **GPU** |
| Log out, Exit Graphite, Restart, Shut down | the foot of the **Work** menu, the first menu |
| Game | the foot of **Programs** |
| What waits for you | already in Stacy's pane: "Now: … N waiting for you" |

## The four meters are doors

Click a meter and its card opens upward from the band. A click anywhere else puts it away.

- **CPU**: Graphite's work on the processor. It is the System menu's own process list, whole.
- **GPU**: what the graphics processor is for here: Stacy's model (**Brain room**) and Graphite's services (On, Off,
  Restart, Service details). "Brain room can probably move into system menu": it moved here with the rest.
- **RAM**: memory in use, swapping, disks and network as the equalizer reads them, and **Machine** (this computer,
  described, in the left pane).
- **TXT**: the text Stacy holds: **Full chat**, and **What she has in view** (Context). The reading itself is still a
  dash: the model's runtime does not report how full her context is.

## The equalizer shows everything that moves

"Make the thinking/activity equalizer represent any and all data activity available together actively showing SSD, RAM,
GPU, CPU, kernel activity. Just a animated way to see that it's working/reasoning/computing/busing data."

It is one picture in six groups, left to right, with a small gap between them:

- **Processor**: one bar for each thread (in pairs when there are more than eight: on the ThinkPad, eight bars).
- **Kernel**: its share of the processor's time; how fast it switches between tasks and takes interrupts.
- **Memory**: in use; swapping (what is moved to the disk for want of room).
- **Disks**: being read; being written.
- **Network**: coming in; going out.
- **Graphics**: how busy; its own memory in use.

It reads twice a second and glides. Every height means one thing always: a share is drawn as that share, and a rate is
drawn on a fixed scale (for the disks, a bar rests under 16 kB a second and is full at 500 MB a second), so the same
height is the same rate tomorrow and a quiet computer lies low. A source this computer does not report rests. **Click
the equalizer** for what each group reads now, in words.

## Stacy's pane: her face is its top

"Probably don't even need the Stacy name tag taking up space." The title row is gone at rest. It comes back only while
Activity or Context is up, as the way back ("‹ Stacy · Context"). The two links under her face, Brain room and Full
chat, are behind the GPU and TXT meters. What is left: her face, what she speaks with, her hand, **This**, **Now**, and
the conversation.

## The line expands

"The type bar at the bottom needs a optional expand to show more data, like if I'm trying to use the terminal."

A small control stands at the left end of the line. One chevron up: show more above the line. Two: taller still. One
down: back to one line. The room it opens shows the page of whoever you are typing to: with **Terminal** lit, the
commands and their output; with **Search**, the results; with **Stacy**, her answers; with **Log**, the Log. (The room
always had these three sizes, but their words were hidden and the only way to them was the Arrange menu.)

"Full chat in Stacy column can probably move into log … but then how to select what log file we're looking at." The Log
chooses its stream by two words at its own top, **Events** and **Network**, which show as soon as the line is expanded
with Log lit. Full chat did not become a third stream: it is a conversation you type into, with its own commands, and
the Log is something you read. It is on TXT. If you want the conversation's record as a stream of the Log as well, say
so.

## Stacy's hand: holes closed, and her rule turned round

These were in 0.6.0 and 0.6.1 as sent. Some I found by reading her rule against each command and every operation; most
were found by other readers (below).

- **Her rule is now a list of what she may do, not of what she may not.** Before, she could do any change of the right
  kind unless it was on a list of things that ask. Now she does by herself only operations named on her list (setting
  a number, keeping a page, writing a new file or folder, making a page or a note, working a calculation again with a
  free hand, opening a program on a project with a free hand, and a few more). Anything else asks, including whatever
  is added to the program later. The list of what always asks stays as a second net, and now also names cancelling a
  job and retiring a finding: neither can be put back.
- **Her Terminal list let through forms that do more than read.** The line is run by your shell, and a shell expands
  what she read as plain text: `find . -delete$Z` reaches `find` as `-delete`. She now refuses any line with a
  character a shell would expand (`$`, a backslash, braces, brackets, `!`, `#`), and holds each command that has
  changing forms to an exact list of its reading options (so `ip l s eth0 down`, `date -s12:00`, `dmesg -Tc`,
  `tail -f`, `lspci -q` and the like ask).
- **An Undo could take more than she made.** Undo on a file or folder she made now runs only while it is still exactly
  as she made it. Once you have written in it, it is yours, and she says so instead of moving it to the Trash. A trail
  read back from the session file runs only the two kinds of Undo she writes.
- **Smaller things the readers found.** A name in quotes is the whole name ("Notes on saying no"). "… called Lander,
  please" names the project Lander. A project cannot take a name Graphite keeps for itself (Exports, Egress, Slate).
  A step word on an older list no longer takes whatever step now stands at its number. "Run df -h" while another
  command is still running says so instead of claiming it ran. "Make a folder called Rev 2" with a sheet selected
  makes the folder instead of being read as setting a number. "Settle what I can" says "done at once" when it is. With
  a free hand, noticing keeps the calculation you had selected selected. The Godot version check gives up after three
  seconds and ends whatever it started. A name with an invisible direction mark no longer breaks a Godot 4 script.

## The line: typing never changes whom you are typing to

In 0.5.3 the line moved to Web as soon as it began with an address. A reader showed what that did: a question for
Stacy that began with a link was sent to a search engine. The lit name now changes only when you choose it. With Stacy
or Search lit, a line that is nothing but an address (`https://…`, `www.…`, `localhost:8080`, `192.168.1.1`) is opened
in the browser; anything else stays with them. With Web lit, an address on this computer or this network (localhost, an
IP number, a `.local` name, any host with a port) is opened, never searched for, and `notes.txt` is searched for, not
opened as a site.

## Other things the readers found in the window

- "This:" under Stacy's face stayed at "nothing is open" when the same page was opened again. It no longer does.
- A right-click Paste in the address line was lost, because the line hid itself when its own menu opened.
- With a spreadsheet's worksheet open, the pane's title now goes between Stacy and the sheet's Preview, so neither is
  out of reach.
- The equalizer's second memory bar counted every disk read and write, so it was the disk bars over again. It now
  counts swapping.
- A second graphics card was never read if the first had many screen connectors. It is read now.
- With Web lit, the list under the line offered "Ask Stacy". Web has no list now.

## Smaller

The room above the line no longer names keys in its standing words.

## What was checked, and what was not

A new probe walks every move in the real window: each meter's card opens inside the window with the right words;
Brain room, Machine and What she has in view go where they say; the Work menu ends with the four ways of leaving; the
game is the last of the programs; her pane has no title at rest and has one while Context is up; the expand steps
through its three sizes; a Terminal command run with the line expanded shows its output there. The equalizer's readers
have tests with counters written by hand (a gigabyte read in a second fills the read bar; a partition is not counted
twice; the loopback is not the network). The project's own tests and the window gate were run on the exact commit
before this set was cut: see the set's START_HERE for the numbers.

**Other readers.** Four readers went over everything from 0.5.3 to 0.7.0, each from one side (Stacy's hand; her acts,
Undo and trail; the Godot start; the window), and reported 32 faults in all. A fifth reader then tried to disprove the
eight on Stacy's hand and confirmed every one. The checks of the other 24 were stopped by the account's usage limit.
I treated those as real unless the code showed otherwise. Every fault is either fixed or listed here as not fixed.
Each fix has a test or a step in a probe. Not fixed: the Godot version check still runs while the window waits (three
seconds at most now).

Not done: nothing later than 0.4.6 has run on the ThinkPad. The graphics group has never been seen moving: the build
container's driver reports nothing, so those two bars rested and the card said so. Leaving (Log out, Restart, Shut
down) was not carried out: the four lines are the same actions the System menu called, and only their presence was
checked. The readers read; they did not run the program on a screen.
