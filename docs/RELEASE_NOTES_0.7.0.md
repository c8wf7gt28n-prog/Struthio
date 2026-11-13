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
- **RAM**: memory in use, paging, disks and network as the equalizer reads them, and **Machine** (this computer,
  described, in the left pane).
- **TXT**: the text Stacy holds: **Full chat**, and **What she has in view** (Context). The reading itself is still a
  dash: the model's runtime does not report how full her context is.

## The equalizer shows everything that moves

"Make the thinking/activity equalizer represent any and all data activity available together actively showing SSD, RAM,
GPU, CPU, kernel activity. Just a animated way to see that it's working/reasoning/computing/busing data."

It is one picture in six groups, left to right, with a small gap between them:

- **Processor**: one bar for each thread (in pairs when there are more than eight: on the ThinkPad, eight bars).
- **Kernel**: its share of the processor's time; how fast it switches between tasks and takes interrupts.
- **Memory**: in use; paging.
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

## Stacy's hand: holes closed

These were in 0.6.0 and 0.6.1 as sent, and were found by reading her rule against every command and every operation:

- **Her Terminal list let through forms that do more than read.** `ip netns exec …` and `ip vrf exec …` run any
  program; `ip -batch` runs a file; `find … -fprint0` writes a file; `file -C` writes one; `date` followed by digits
  sets the clock; `sensors -s` sets limits. Most need root to do harm, but none is a read. Each command is now held to
  its reading forms.
- **With a free hand she could have been handed things that leave the computer or forget.** Not by any path that
  existed, but the rule itself would have allowed transfers, mail, pairing, publishing, packet capture, installing a
  release, and several kinds of forgetting. The rule now names them, and a test runs every operation the program has
  against it.
- **A project name with a line break could break the Godot files it was written into.** A name can no longer end its
  own line; both real engines still load such a project.

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

Not done: nothing later than 0.4.6 has run on the ThinkPad. The graphics group has never been seen moving: the build
container's driver reports nothing, so those two bars rested and the card said so. Leaving (Log out, Restart, Shut
down) was not carried out: the four lines are the same actions the System menu called, and only their presence was
checked. An independent review by other readers was started twice and both times stopped by the account's usage limit
before any reader reported; what the first had begun (her rule against every operation) was finished by hand and is
the source of the fixes above. So there is still no second reader over 0.4.7 to 0.7.0.
