# What's new in Graphite 1.0 · The Living Desktop and the Ghost in the Shell

November 26, 2026. Guide → What's New opens this page. The 0.8.7 to 0.3 notes beside it describe what came before.

Graphite 1.0 is the desktop of your paper: **Graphite is the session**, the whole computer is in it (files from "This
computer /", Apps, the Machine, Settings), the centre is a **bulletin board** where what you select sits among what it
is connected to, and **Kasandra is an agent user of the system**: she plans a task from the real tools, asks for each
permission in plain words, works in LibreOffice and in your other apps while you watch, and marks a step done only
when its effect is verified. The model proposes; the desk disposes.

**It was not tested.** You said "No testing" for 1.0. Nothing in it has been through the test suite, the tiers or the
window checks, and no part was reviewed by a second agent. Each part was built by one agent, who checked the design's
own examples in one script of their own; at each merge Graphite was started and its window opened, offscreen, in all
four looks. Twenty-four walkthroughs of ordinary and power-user sessions and the paper's §18 day were walked in the
window under a stand-in display (the day with a real 4B model). It was built in a cloud machine with **no screen, no
USB port, no sound, no Wi-Fi, no suspend and no Radeon**: everything that touches those was seen against stand-ins
only. **Nothing has run on your ThinkPad, and the 35B has never been loaded anywhere.** Install it into a new folder,
keep your 0.8.x folders, and back up your workspace first.

## Your first evening

`docs/ACCEPTANCE_1.0.md` (Guide → Your First Evening with 1.0): the install from the kit, your paper's §2 test with
no model (including a deliberate crash of Graphite's window), the 35B with its MTP head and the model check with its
tuning, the §18 day on Rail Demo, and what to send back, with numbered photos. Two evenings are fine.

## Graphite is the session

- A small supervisor owns the session: Fluxbox runs hidden underneath, Graphite's window fills the screen, and if the
  window crashes it comes back (up to three times in a row) while **your apps stay open**, each in a session of its
  own. A slim dock across the top lists Graphite and the open app windows; one press brings one forward.
- Lock (xsecurelock), Suspend (it locks first, always), Log out, Restart, Shut down and Return to Debian are separate,
  plain actions. Leaving names the apps still open and asks each to close politely; nothing is killed. System
  permission prompts are answered inside the session (lxpolkit). Notifications from apps arrive as a quiet toast that
  never takes your keys, each kept in Log.

## The whole computer

- **Files** start at "This computer /" with Home open. In Home: open in its app, Rename, Move to, Copy to, New folder,
  Delete to the system's own bin (and Restore), drag to move, each with a line and Undo. Choose many rows at once (a
  click, a range, add one) and move, copy or delete them in one press with **one Undo for the batch**; a line can end
  in move, copy or delete, and asks first. Graphite never deletes Home
  itself or the folder holding its workspace. On screen the bin is DELETE, by your rule.
- **Apps** lists what is installed, from the apps' own desktop entries, by category, with a search line; ⊕ adds one to
  your list; Open with on any file; "Always open PDFs with this" sets the default.
- **The Machine** is real (through the system's own services): USB drives (open, eject safely; "safe to remove" only
  when it is), the battery, the network and Wi-Fi (on, off, join), sound (volume, mute, output), screens (mirror or
  extend, with a change that goes back by itself unless you press Keep).
- **Settings → This computer**: default apps, sound, screens, network, power, the session, notifications.
- **Apps by window and file**: a file opened in another app from the board is watched; when that app saves, the new
  revision is recorded and what depends on it is marked for a recheck.

## The Living Desktop

- **The board.** Select something and it sits in the middle with its neighbours on rings: its sources, the revisions
  of a limit, the calculations made from it, the findings about it, open questions, pages that quote it. Recorded links
  are solid; guessed ones are dashed and say "not verified"; click a wire for its basis. **Tile size is relevance** to
  the focus and to what you are doing, in four stable sizes; right-click: Why am I shown?, Pin, Turn down. The least
  relevant fold into "and N more".
- **One selection**: the tree and the board share it by the object's identity, which survives a rename or a move.
- **Depths**: a click focuses, a double-click opens the working view; Save; **Save and Return** comes back to the same
  board at the same zoom, with what depended on your change marked for a recheck; Full program opens it in its app.
- **Tabs and a two-pane split**; only the pane in focus drives the tree and her "this". **Back and Forward** return to
  exactly where you were.
- **One language of states**: every state that matters has one word and one shape, the same on tiles, wires, steps,
  her state and the dock (CURRENT ■, REFUTED ⊘, OPEN □, NEEDS YOUR WORD ◆, stopped ▮▮ …), with colour only as a third
  cue.
- **The foot is the computer's line**: Line · Terminal · Search · Web · Log, Line by default (a line, an operation by
  name, an address). Words meant for her are offered as "Ask Kasandra →" and go to her column. The meters gain NET.

## The ghost in the shell

- **Her column** (no picture of her, by your direction): the equalizer across the top, her name, model and state word;
  **Waits for you** when something does; ACTIVE WORK with each task's progress, time left and its own Stop; FINDINGS
  (live); up to four NEXT STEPS; DO, DOUBT, TRACE, BRIEF, LINE and CHECK ALL; her ask line.
- **A task becomes a plan** of steps from the registered tools (records and maths, files in Home, LibreOffice, the
  sandbox, windows, Apps, the Machine's state, the network). With no model her desk plans; with one, the model picks
  each step by number from the real tools and the desk checks every step's inputs and conditions. A change the model
  alone chose is never done.
- **Permissions in plain words**, per operation, target and scope (this task, until a time, always), shown before you
  press and enforced by the Kernel at every step. When a plan's steps in one folder need several, one press gives them,
  each named. A step that needs a permission she lacks stops: "needs your grant … Nothing was sent".
- **Done means verified**: two records per step, "sent" and "confirmed". A crash, a suspend or a Stop leaves a journal;
  on resume she checks each step's result before repeating anything.
- **In LibreOffice** (Writer and Calc, .odt and .ods) she works in her own hidden LibreOffice, saves, reads back,
  compares and records a new revision; she refuses a document you have open.
- **In your apps** she presses named buttons, chooses menu items and types into fields through accessibility first,
  while you watch, under a permission, confirmed afterwards. **A touch of your mouse or keys pauses her** between
  presses; Stop puts the window back as it was (focus, selection, cursor, scroll, any menu she opened). She never
  presses Send, Pay, Delete or Install in another app, and never types a password.
- **A utility she writes** runs sealed: on copies, no network, nothing outside its own folder, limited time and memory.
  Applying its output to your files always asks.
- **The network** is offline first and always visible ("Kas: <host>" while she fetches). A page she fetches is kept as
  a quarantined source; a line in it written to an assistant is withheld and outlined. A step that needs the network
  while it is down is "blocked: needs the network", never done.
- **Your documents in Home**: asked about one, she reads its pages through the same doorway and names the page her
  answer came from.
- **HALT** (upper left) holds all of her work at once and nothing else: never the desktop, never your apps. RESUME
  restarts nothing by itself; each task waits for its own Resume.

## Her model

- **llama.cpp v1.0.0** (build b12359), sealed as before, its refused flags rebuilt from v1.0.0's own help.
- **Speed settings, measured on your machine**: flash attention, the KV cache's type, reading batches, threads, full
  or partial offload, and multi-token prediction with a model file that carries its own MTP head. The model check's
  tuning stage keeps a setting only when the answer is identical without it, and says how far reading and writing are
  from **99 tokens a second**; each proposal comes with Undo. The rates it measures reach her clock.
- **A quick model beside the 35B** (optional): a small model takes a kind of question only where it passed that kind's
  exam on your machine and measured faster. The Brain room's Quick model page says which model answers what, and why.
- **Memory**: a cap you set stays your budget; the runtime's address space gets the room it needs; the Brain room says
  before loading whether she fits.

## The look

- **Day** is the launch look, rebuilt on one set of design tokens (`workbench/design_tokens.py`) with the Inter
  typeface and IBM Plex Mono for numbers and lines; **Night** is its dark twin. Every text pair measures at least
  4.5:1. Graphite and Kasandra stay as alternatives (Arrange ▸ Appearance). An existing profile moves to Day once, with
  one line saying where your earlier look is.
- **No picture of Kas** anywhere, in any look ("No kas avatar anymore"): her name, her state and her work.
- A polish pass framed every main surface in four looks at two sizes and fixed what read badly.

## The floor

- Reads run beside her writes, so the window no longer waits for her; HALT, RESUME, TRACE, CHECK ALL and asking her do
  their work off the window's thread. Measured under the window's own event loop on Rail Demo, nothing held the window
  over 0.1 s (TRACE answered in 0.14 s, CHECK ALL in 0.74 s, HALT and RESUME in 0.04 to 0.06 s, all without freezing
  it). Still over 0.1 s here: the first tree read at a start (1.1 to 1.6 s), opening the Machine page, and the start of
  asking her (about 0.3 s).
- The cold start is about a third faster here (4.7–6 s offscreen).
- A 0.8.7 workspace opens in 1.0 as it is: 1.0 adds tables of its own and changes none of 0.8.7's. A task Kas left
  running in 0.8.7 shows in ACTIVE WORK with its own Stop.
- `GRAPHITE_STALL_LOG=<file>` writes every stall over 0.1 s with the part of Graphite that held it.

## The 1.0 System set

136 Debian 13 packages added to the 0.8.x set (USB drives, the battery, sound, Wi-Fi, the lock, permission prompts,
your login session, Writer and UNO, accessibility). The installer now gives apt only what your computer lacks and never
downgrades (0.8.7's preview would have downgraded 11 to 32 packages and then failed). The kit's start page and
`WHAT_THE_1.0_SYSTEM_SET_ADDS.md` say how to put it in place.

## The walkthroughs

Your question "should we simulate general user operations instead of the same rail tests?" became two sets of twelve
sessions, walked in the window under a stand-in display, each with frames and a plain account
(`wip/2026-11-26_b100_saved/X3.account.md`, `X4.account.md`, `X1.account.md` in the source).

- **Everyday (twelve sessions, invented Home):** first start with no model; Taxes 2026 made, three PDFs moved in, one
  renamed, Undo; photos copied off a USB stick and the stick ejected safely; a letter written in LibreOffice through
  Apps and an outside save noticed as revision 2; "what did we spend on groceries this month?" answered 244.65 exactly,
  with its receipt; Downloads tidied in 16 verified steps and put back; the web offline (blocked) and online (the
  planted line held back); two apps, the dock and a notification; Settings; HALT mid-task and RESUME with nothing done
  twice; Log out with apps open, each asked politely. Her hand in an app was walked by the power-user set and the day.
- **Power user (twelve sessions, a busy invented Home with 205 files in Downloads and a 300-record desk):** lines and the
  Terminal; Search; bulk files; three tasks at once under different permissions with HALT; split and recheck; a sandbox
  utility; her hand across Calc and Writer with a touch stopping her; the network adversarial; Graphite killed
  mid-task and brought back by the supervisor with the apps still open; the board at scale; her model's tuning sweep;
  two screens, a busy drive, and a pass by keyboard alone.
- **The paper's §18 day** on Rail Demo, following your acceptance page step by step, with the real 4B loaded: her
  review answered from the desk's findings ("So I cannot call it sufficient"), the worksheet beside the specification,
  the settled current changed to 300 mA, the out-of-date summary noticed by her, the page and the report updated through
  LibreOffice and verified, "Every step is done (verified)", and the journal intact after a restart.

What these walks found was fixed in place where it was small, and in four slices where it was not: her reach in Home
(reading your documents' pages, file tools for her plans, one press for a folder's permissions), the walkthroughs'
faults (a cut-short fetch is never "done"; a permission given under HALT carries its task after RESUME and its own
Resume; TRACE on the focused finding; her column true after a restart and with her model's state; the long stalls moved
off the window's thread; the HALT notice off "Waits for you"; Search matching each word, finding Home's files by name
and opening the board; every keyboard stop named), bulk files (many rows at once, one Undo for the batch, lines that
move or delete after asking, the sandbox taking a folder's worth with Undo for what it made), and the polish pass.

## What was measured, and what was not

- **Measured here, on a busy cloud processor, with the 4B** (smokes, not numbers to plan on): sealed starts on
  v1.0.0; her kept prompts survive (PLAN and READ, 312 of 314 tokens reused); a PLAN turn in 4.0–11.8 s; reading 47→67
  and writing 5 tokens a second at best; a 2B beside the 4B about twice as fast but failing every exam it sat (so it
  took no kind).
- **Not measured anywhere**: the 35B's speed, MTP's gain on the Radeon, whether reading reaches 99 tokens a second
  (likely) and writing (not likely with the 35B alone), Vulkan, and everything that needs a real screen, USB, sound,
  Wi-Fi or suspend. That is what your evening measures.

## The builder's own design, for you to strike

You asked the builder to "take more control of how the desktop is designed". These are the builder's, not yours:
`wip/2026-11-26_road_to_1.0/DESIGN_DIRECTION_1.0.md` (one place per job, one language of states, one centre bar, her
column ordered by what waits for you, the foot as the computer's line); the launch look's exact colours (three of the
planned colours darkened to pass contrast); the equalizer as her presence once her picture went; and the memory-cap
rule above. Each is a default; say the word and it changes.

## What 1.0 does not do yet

- **Her model planning a tidy**: the 4B here answered "the bin for every group" once and "look at Downloads" eight
  times; the desk refused both, so nothing harmful ran, but it planned nothing useful. The desk's own tidy works with
  no model. The 35B's planning is untried.
- A few moments still hold the window over 0.1 s (the first tree read at a start, opening the Machine page, the start
  of asking her); your stall log on the ThinkPad will say which matter there.
- A task step that puts a line's money total into words stops: the total arrives as a decimal number, and her rule
  refuses to word a number that is not exact (X4's "Groceries note"). Her answer to "what did we spend on groceries?"
  is exact and unaffected.
- Dragging many chosen files onto a folder is wired but was never exercised (no real drag here).
- Search matches each word in the desk's records and in your Home's file names, not inside your files' text.
- The whole-desk view (the Field) cuts tiles at its edges at 1366x768; the Arrange menu splits into two columns there.
- She edits only .odt and .ods in LibreOffice (.docx and .xlsx are read only). Her hand reaches LibreOffice opened as
  an ordinary app; the Calc sessions Graphite owns and her own hidden LibreOffice expose nothing to accessibility.
- The split is not restored at the next start (its tabs are). No encrypted drives, no enterprise or hidden Wi-Fi.
- Large apps (Firefox, GIMP, KiCad, Blender, Godot) are not shipped: Graphite finds whatever you install.
- The test pass, with every test and review 0.8.6, 0.8.7 and 1.0 skipped by your rule.
