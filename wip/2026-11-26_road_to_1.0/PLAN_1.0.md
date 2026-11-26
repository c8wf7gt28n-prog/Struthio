# Graphite 1.0: the Living Desktop and the Ghost in the Shell — the plan, and what "complete" means

*Written 26 November 2026, from the owner's paper (`PAPER_Living_Desktop_Ghost_in_the_Shell.md`, beside this file) and
the owner's picture of the desktop (described in section 3; the picture itself stays out of the repository by the
owner's standing rule on theme pictures). This file is the source every 1.0 builder's brief is made from.*

## 1. The owner's mandate (26 Nov 2026, verbatim)

- "Let's go default. No testing. I want to just build straight to 1.0 no stops. Save your work to survive session
  resets. I don't want anything until we land 1.0 fully. You can send updates or screenshots along the way. Attached is
  kinda how I envisioned it. Do you understand and understand what complete is?"
- The four defaults taken ("Let's go default"):
  1. Make the desktop real (the session, then the Living Desktop centre) before adding more Apps.
  2. ~~The test pass first~~: **overruled by "No testing"**. There is no test pass before 1.0. The 0.8.6/0.8.7 rule holds
     for every 1.0 slice: no new tests, no suite, no tiers, no window checks, no reviews; each builder checks the
     slice's acceptance examples in one smoke script of their own; at each merge the seed is rebuilt and the window
     opened offscreen in every look.
  3. Her tool use: she may draft and test a new utility on a copy in a sealed sandbox; running it on the owner's real
     files always asks, at every place of the dial.
  4. Her portrait compact by default, the full art for the moments that matter, in place of the lower-left hologram.
- "No stops": no intermediate kits, no waiting for the owner's model results. Updates and screenshots may be sent along
  the way. The hourly wake-up ("Continue the Graphite build") is on until 1.0 is delivered.

## 2. What "complete" means for 1.0

1.0 is complete when **every one of these is built, wired into the window in every look, seen working here offscreen
as far as this container allows, and delivered as the 1.0 kit** with its release notes and the acceptance evening for
the ThinkPad.

1. **Graphite is the session.** Fluxbox stays hidden and outlives Graphite's own window: if Graphite's window crashes or
   restarts, the program windows stay open and Graphite comes back. Lock, Suspend, Log out, Restart, Shut down and
   Return to Debian are separate, plain actions. The console route is always there.
2. **Apps are what is installed.** The Apps panel (upper right, "Apps ⊕") lists the installed programs from their
   desktop entries, opens them, and opens a file with its default program or with Open with. The program windows that
   are open show in a slim strip; one press brings a window forward.
3. **The Machine is real.** USB drives (see, open, eject safely), sound (volume, mute, output), screens (which, how
   arranged), the network and Wi-Fi (on, off, join), the battery; notifications from programs shown quietly; system
   permission prompts answerable inside the session. The Settings tree changes real settings (default programs, sound,
   screens, network, power, session).
4. **One centre, one selection.** The file tree and the board share one selection by the object's identity, which
   survives a rename or a move. Selecting in either moves the other; the tree reveals the object without collapsing
   other branches. Back and Forward restore the whole context (the focus, the depth, the zoom, the place in a document).
   A breadcrumb says where you are.
5. **The bulletin board.** The focused object sits in the middle with its neighbours around it, each tile sized by its
   relevance to the focus and the task (four sizes, stable: tiles do not jump), with its kind, its state word, its
   title and the basis of its link ("reviewed from page 1, version 1"). Recorded links are solid; inferred ones are
   dashed and say so; clicking a link shows its basis. Every tile answers "why am I shown?", and can be pinned or turned
   down. Relevance, truth, confidence and authority are marked separately; peripheral material is grouped as a count
   that opens.
6. **Depths.** A single click focuses; a double-click opens the object's working view in the centre; Save saves; Save
   and Return saves and closes; closing comes back to the same board; unsaved changes ask. A change saved by another
   program is noticed, never shown stale. Open in the full program, and back, with the revision recognised.
7. **Tabs and the split.** Several working tabs; at most two panes side by side; only the pane with the focus drives the
   tree's highlight and her "this".
8. **Her column, as in the owner's picture.** A compact portrait with the equalizer's sixteen bars behind it; her name
   and state word (QUIET, WORKING, …); a short exchange (Your: / Kasandra:) with check rows; a progress line while she
   works; ACTIVE WORK with each assignment's progress and time left; FINDINGS (live); NEXT STEPS as up to four numbered
   buttons; an "ask Kasandra…" line at the foot of her column. DO, DOUBT, TRACE, BRIEF, LINE and CHECK ALL live in her
   column, compact.
9. **The ghost works.** An assignment becomes a durable plan of steps, each with a status (proposed, authorised,
   running, done, blocked, needs review). Each step uses a registered tool and records an observation receipt (which
   tool, which object, which revision, complete or not). A step is done only when its effect is verified ("the new
   revision is on disk"), never when a command was merely sent. On a failure she revises inside the granted scope. A
   crash, a suspend or a Stop leaves a journal of what happened and what was only prepared; on resume she inspects
   before repeating anything.
10. **The owner keeps the authority.** Grants are per operation, target and scope (and may be time-bound or per
    assignment), shown in plain words before approval, and enforced by the Kernel at dispatch, not by the model's
    instructions. HALT (upper left) stops all of her managed work and nothing else: never the desktop, never the owner's
    programs. Each assignment has its own Stop. A new utility she writes runs only in a sealed sandbox on copies;
    applying it to real files always asks.
11. **She works in other programs.** LibreOffice Writer and Calc through their own interface: open, read, edit a
    passage or a cell, save, and verify the saved revision. Other programs by window and file: open a file in them,
    notice the save, record the revision; read their windows and dialogs through accessibility where it is available,
    to notice an unexpected dialog. No blind clicking.
12. **With no model, Graphite is whole.** Everything in 1 to 11 works without a model, except what only the model
    gives (reading free words the dictionary cannot, proposing a plan for an open objective). With a model, the model
    proposes and the desk disposes, as in 0.8.7.
13. **Offline first.** Network use is visible and governed; a task that needs the network is never "done" while the
    network is down; search words never carry the owner's material; a web page is never an instruction.
14. **The Day look** from the owner's picture (section 3), beside the Graphite and Kasandra looks; the layout of 4 to 8
    holds in every look.
15. **The day in the paper (§18) runs in the window**, start to finish, on an invented desk (Rail Demo), with frames;
    the 1.0 kit carries the acceptance evening for the ThinkPad (the paper's §2 test: start with no model, open two
    programs and move material between them, a USB drive, suspend and resume, return to the console).

**What "complete" cannot mean here, said plainly.** This is a cloud container with no screen, no USB port, no sound,
no Wi-Fi, no suspend and no Radeon. Those parts are built against the real Linux interfaces (logind, udisks2,
NetworkManager, UPower, PipeWire, the X11 window properties, AT-SPI, LibreOffice's UNO) and checked here with
stand-ins and offscreen windows. By the owner's rule nothing is tested. So 1.0 is **built, not tested**, and the first
real proof of the session, the Machine and the 35B is the owner's acceptance evening on the ThinkPad.

## 3. The owner's picture, in words (so it survives without the image)

A light, calm look: white and very light grey panels with soft shadows, green accents (state words, progress bars,
the send arrows), blue for wires and the board's rings.

- **Head.** Upper left: a green triangle and **HALT** (the master stop; the picture spells it "HAULT", read as HALT).
  Across the head from the middle column: Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide. Upper right:
  **Apps** and a circled plus.
- **Left column.** Tabs Files, Machine, Settings (the chosen one underlined in green). The tree: CONCERN open, its
  folders (Engineering, Kasandra, Ideas, Legal, Notes, Operations, Projects, Publishing, Research & references,
  Unassigned with Documents and Questions), drawn with the circuit traces. At its foot: the DELETE bin.
- **Centre: the bulletin board.** Concentric rings (green and blue) around the focused tile, with a vertical axis
  through the centre carrying a small square handle at the top and at the bottom. The focus tile is the largest:
  "SHEET • CURRENT / Rail Demo bench readings / reviewed from page 1, version 1 / Rail_Demo_readings.pdf", with a
  striped corner. Around it, smaller tiles joined by blue wires with round ends: SOURCE (CURRENT) PDFs, SHEET Rev A
  (ARCHIVED) and Rev B (CURRENT), CALC tiles ("Rail Demo startup power = … W / cells B2, B4 / revision 2"), FINDING
  tiles with state words (CURRENT, SUPPORTED, REFUTED), a PAGE tile ("Rail Demo summary, revision 1"), a QUESTION tile
  (OPEN). Each tile: a kind glyph and KIND • STATE on its first line, the title, then the basis line and the source.
  The tiles nearer the centre and larger are the more relevant.
- **Right column: Kasandra.** At the top her portrait (in the picture, the owner's own art: a woman in a wide
  white-and-blue hat with a feather and green trim) with the equalizer's sixteen numbered bars (01 to 16) standing
  behind and beside her. Under it: "Kasandra ○" and "● WORKING" in green. Then the exchange: "Your: Check the Rail Demo
  bench readings. Confirm startup power and why it's 3 W ms." "Kasandra: On it. I've loaded the readings, rechecked Rev
  A/B, and traced the startup path." with check rows (✓ Startup power … (Rev B, cells B2, B4)), then "Next step: …?",
  "Your: Simulate a shorter path and show options.", "Kasandra: Running… ▓▓▓▓░ 72%". Then **ACTIVE WORK [3]** with a
  numbered list, each with a progress bar and an ETA (00:18, 00:37, 01:20). Then **FINDINGS (Live)** as bullets
  (supported / refuted / next). Then **NEXT STEPS** as four numbered buttons in two rows. At the foot: "> ask
  Kasandra…" and a green send arrow.
- **Foot.** Left: Kasandra, Terminal, Search, Web, Log (Kasandra underlined). Middle: the writing line with a green
  send arrow. Right: the meters as plain words and numbers: CPU 34% | GPU 24% | RAM 62% | TXT 18%.

The picture's numbers and sentences are illustrative (some are garbled); the builders take the layout, the kinds of
content and the look, never its numbers.

**Her portrait (decision taken).** The owner's own pictures stay out of the repository (the standing rule). So her
portrait in every look is drawn from `kasandra/portrait.png` (or .jpg) in the owner's workspace when the owner puts
one there and admits it, like her character file; until then the shipped art is used. The owner can drop the hat
portrait in that folder on the ThinkPad.

## 4. What is already built and reused (from the code, 26 Nov)

Records with revisions, lineage and evidence (the Kernel); the maths with receipts; Why, Rests on, Either way,
cross-references; her hand (the dial, Undo, what always asks, the trail); the sealed model, pick never write, her
clock, the one question, the exam; the hidden Fluxbox session (`LS_XSESSION.sh`, `START_MINIMAL_DEBIAN.sh`); Log out,
Restart, Shut down, Return to Debian through logind (`workbench/session_power.py`); Calc sessions Graphite owns
(`native_sessions.py`, `office_runtime.py`); KiCad and Godot starts; Stop all jobs; Night Shift checkpoints; work tabs
(`workspace_tabs.py`); breadcrumbs (`navigation_qt.py`); the Field (`field_qt.py`, `field_model.py`) with its wires and
kind glyphs; the desk acts and the planner over their conditions; the head, footer, meters and equalizer (0.8.6 W).

**Missing (the work of 1.0):** a session that survives Graphite; Suspend and Lock; installed-app discovery; the window
list; USB, sound, screens, Wi-Fi, battery, notifications, permission prompts, file associations; one selection shared
by tree and centre; context history; relevance; the board as the centre's home; depths with Save and Return; the split;
her column as in the picture; assignments with a journal; observation receipts and a tool registry; scoped grants and
HALT; the utility sandbox; the LibreOffice Writer/Calc bridge through UNO; accessibility reading; the Day look.

**New Debian packages for the 1.0 System set** (the 0.8.x set has fluxbox, xinit, dbus-x11, network-manager,
x11-xserver-utils, libreoffice-calc; it lacks these): udisks2, upower, pipewire, pipewire-pulse, wireplumber,
xsecurelock, lxpolkit, xdg-utils, x11-utils, libreoffice-writer, python3-uno, at-spi2-core, python3-pyatspi (exact
names checked against Debian 13 when the set is made). Large programs (Firefox, GIMP, KiCad, Blender, Godot) are not
shipped: Graphite finds whatever is installed. No new Python wheels: D-Bus through PySide6's QtDBus, X11 window
properties through ctypes on the system's libX11 (with `xprop` as the fallback).

## 5. The slices

Each slice is built by one agent in its own worktree from a brief = `BRIEF_HEADER.md` (beside this file) + the slice's
section below. Each keeps its code in modules of its own and its edits to the shared window files small and marked
with the slice key (`1.0 <KEY>`). Acceptance examples are what the builder's one smoke script checks.

### Wave 1 — foundations

**S1 · The session that survives.** Rework `LS_XSESSION.sh` (and the starts that lead to it) so the session is owned by
a small supervisor: Fluxbox and the D-Bus session run for the whole session; Graphite's window is a child the
supervisor restarts when it exits unexpectedly (with a backoff and a limit, then the console route with a plain
message), and ends the session only on Return to Debian, Log out, Restart or Shut down. Program windows started from
Graphite are not Graphite's children for the session's sake (start them in their own process group / via setsid) so a
Graphite crash does not close them. Add **Suspend** (logind Suspend, with the lock taken first) and **Lock**
(`xsecurelock` when present; logind LockSession; with a plain reason when no locker is installed) to
`session_power.py`, and make the session group read: Lock, Suspend, Log out, Restart, Shut down, Return to Debian
(each with its scope line, as today). A sleep inhibitor while she writes a file (logind Inhibit "sleep", delay mode) so
a suspend never lands mid-write. *Acceptance:* the supervisor script, run with a stand-in Graphite that exits 1 twice
and then 0, restarts it twice and ends cleanly, and a stand-in "program" started through Graphite's launch path
survives the stand-in Graphite's exit; `session_power.availability()` lists the six actions with their states on a
fake logind; Lock with no locker says why; Suspend takes the lock first.

**L1 · One navigation state.** A new `workbench/living_nav.py`: the canonical object identity (a Kernel record's id;
for a plain file, a stable id kept in the Kernel keyed by device+inode with the content digest as a check, updated on
rename or move seen by a file watcher or by Graphite's own file operations), and one navigation controller holding the
focused object, the depth (board, work, split), the active pane, the history (each entry: focus, depth, board zoom and
centre, the document position, how it was reached). Back and Forward restore an entry whole. Wire the left tree and the
centre to it: selection from either moves the other; the tree reveals the object's parents without collapsing other
branches and keeps its scroll; a search result does the same. A breadcrumb above the centre shows the path and name and
follows renames. *Acceptance:* select a file in the tree → the centre's focus is that object; rename it on disk → the
same object, new name in tree and breadcrumb; select a neighbour on the board → the tree reveals it with other branches
still open; Back → the previous focus with its zoom and document position; two files with the same name stay two
objects.

**K1 · Assignments and the journal.** A new `workbench/assignments.py` with Kernel operations (assignment.start,
.plan, .step, .status, .stop, .resume, .list): an assignment holds the objective in the owner's words, the plan's steps
(each: the tool and operation, its inputs with where they came from, the expected output, the verification, the grant
it needs, its status: proposed, authorised, running, done, blocked, needs review), and a journal of effects (prepared
vs done, with the observation that proves done). Durable in the Kernel's records; written before and after each
effect; a crash, a suspend or a Stop leaves the journal readable; resume inspects each step's expected output before
repeating it and never repeats an effect that is verified done. Time left per step from her clock's estimates. The
existing Night Shift checkpoints and continuing work are reused, not duplicated. *Acceptance:* a three-step assignment
on Rail Demo (read the readings; recompute settled power; write a note) run to the second step, then killed → the
journal says step 1 done (verified), step 2 prepared, step 3 proposed; resume verifies step 1's output, does not redo
it, and finishes; Stop mid-step leaves "stopped by you" with what was done.

### Wave 2 — the board, her column, the Apps

**L2 · The bulletin board.** The centre's home at board depth (`workbench/board_qt.py` + `board_model.py`): the focused
object in the middle, its neighbours around it from the Kernel's recorded relationships (inputs, quotes, revisions,
findings, questions, cross-references, outputs) and, labelled as such, inferred ones (same component named, same
words, used together); rings as in the picture; tiles with the kind glyph, KIND • STATE, the title, the basis line, the
source; wires solid for recorded, dashed for inferred; clicking a wire opens a compact inspector with its basis ("Used
value 300 mA from Bench Readings, revision B, to calculate settled power"; "Possible: both name the startup limit; not
verified"). Selecting a tile focuses it (through L1). The Field's whole-desk map stays reachable by zooming out. An
inferred link never becomes recorded without the owner's word. *Acceptance:* on Rail Demo, focus the bench readings →
its sources, the Rev A and Rev B sheets, the calculations and findings around it with their state words; click the wire
to the settled-power calculation → its basis names the cells and the revision; an inferred link is dashed and says
"not verified".

**L3 · Relevance.** `workbench/relevance.py`: a score for each candidate neighbour given (focus, task, context) from
separately recorded reasons (recorded dependency, cited by the current output, current vs archived revision, an
unresolved contradiction or open question, a change that affects it, the owner's pin or turn-down, inferred vs
verified), never folded into truth, confidence or authority, each of which keeps its own mark. Four tile sizes with
hysteresis (a small change of score never moves a tile between sizes or places); periphery grouped as "and 12 more"
that opens; "Why am I shown?" lists the reasons in words; Pin and Turn down, visible and reversible; the task (an
assignment, or the owner's last request) changes the ranking. *Acceptance:* the refuted finding outranks a supporting
one when the task is the startup question; the archived Rev A tile is smaller than Rev B; pinning a small tile makes it
large and says "pinned by you"; a 3 % change of score moves nothing.

**P1 · Her column, as in the picture.** Rebuild the right column (`mind_panel_qt.py`, `shell2.py`'s column, new
`her_column_qt.py`): the compact portrait with the equalizer's sixteen bars behind it (the equalizer moves here from the
head's upper left), her name and state word; the short exchange with check rows (not an endless transcript: the last
few turns, the rest behind "earlier"); the progress line; ACTIVE WORK from K1 (progress, time left, Stop each); FINDINGS
(live) from the Kernel; NEXT STEPS as up to four numbered buttons (each one desk act or assignment, one primary); the
"ask Kasandra…" line at the foot. DO, DOUBT, TRACE, BRIEF, LINE, CHECK ALL as a compact row. The full art and its
static only for the moments that matter (a finding refuted, an assignment done, HALT). Portrait from the workspace
(`kasandra/portrait.png`, admitted) when present. Every look. *Acceptance:* frames in every look at 1920x1200 and
1366x768 with an assignment running on Rail Demo: the column reads top to bottom as in the picture; with no model the
exchange and NEXT STEPS still work from the desk.

**S2 · Apps from what is installed.** `workbench/apps_catalog.py` + the Apps panel (upper right, "Apps ⊕"): read the
XDG desktop entries (system and user, NoDisplay and Hidden honoured, OnlyShowIn respected loosely, localised names),
their categories and icons (the icon theme lookup, with Graphite's own glyph as fallback); search; launch with the
field codes (%f %F %u %U %i %c %k) safely (no shell, argv only), in the program's own process group (S1). File
associations: the default program for a MIME type from mimeapps.list (read and write, user level), "Open with" listing
the programs that take the type. Graphite's own curated rooms stay in Apps as Graphite's. *Acceptance:* a fake XDG tree
with five entries (one NoDisplay, one with %F, one terminal program) → four listed with their categories; launching
the %F one with two files builds the right argv; setting the default for application/pdf writes mimeapps.list and Open
with lists the PDF readers.

### Wave 3 — depths, split, windows, the Machine, the Day look

**L4 · Depths.** Double-click (or Open) on a tile or a tree item opens its working view in the centre through the
existing viewers and editors (sheet, PDF/reference, document, calculation, image, question); the board recedes; a
"Board" control and the breadcrumb lead back. Save writes; Save and Return writes and closes; closing with unsaved
changes asks (Save, Don't save, Cancel). A file changed on disk by another program is noticed (QFileSystemWatcher):
a clean view reloads with a line saying so, a dirty one says the file changed and offers to compare. "Open in the full
program" (S2's default app) and, on return, the new revision recognised and recorded. *Acceptance:* open the bench
readings from the board, change a cell, Save and Return → the board, same focus, the dependent calculation marked for
recheck; an outside edit to an open clean file reloads with its line.

**L5 · Tabs and the split.** Working tabs for Graphite's views (no duplicate tab for an open object unless asked); a
two-pane split (drag a tile or a tab to the empty half, or Split); only the active pane drives the tree highlight and
her "this"; the passive pane keeps its scroll; a quiet mark says the other pane shows another object; collapsing the
split keeps both tabs. *Acceptance:* the specification PDF left, the worksheet right; clicking in the right pane moves
the tree's highlight to the worksheet and "this" to it; the left keeps its page.

**S3 · Program windows.** `workbench/windows_x11.py`: the window list from the X11 window properties
(_NET_CLIENT_LIST, _NET_WM_NAME, _NET_WM_PID, WM_CLASS, _NET_ACTIVE_WINDOW, _NET_WM_STATE) through ctypes on libX11,
`xprop` as the fallback, polled lightly or on PropertyNotify; activate, minimise and close (polite close via
_NET_CLOSE_WINDOW); the slim window strip (Graphite's own windows apart), each with its program's icon and title. Kas's
observation of windows (title, program, which is active, a new dialog appeared) for K2. Graphite's own dialogs stay
reachable. *Acceptance:* under an offscreen X server (Xvfb, if present here) with two plain X windows, the strip lists
both with their titles; activating one makes it active; without X it says "no window list on this computer" and
nothing breaks.

**S4 · The Machine, real.** In the Machine tab and the meters: removable storage through udisks2 over QtDBus (list,
mount, open in Files, unmount, eject safely, "safe to remove" said only after it is), power and battery through UPower,
the network and Wi-Fi through NetworkManager over D-Bus (state, on/off, list, join with a password typed by the owner
and kept by NetworkManager, never by Graphite), sound through PipeWire (`wpctl`: volume, mute, output device), screens
through `xrandr` (which, their modes, mirror or extend, one primary). Each shows "not available on this computer, and
why" when its service is absent. *Acceptance:* with fake D-Bus services (a small stand-in on the session bus) the drive
appears, mounts, ejects; the battery reads; Wi-Fi lists two networks; with no services each row says why.

**S5 · Notifications, prompts, settings.** Graphite as the session's notification server (org.freedesktop.Notifications
over QtDBus: Notify, CloseNotification, GetCapabilities, the signals), shown quietly (a line in her column's foot or a
toast that never steals focus, kept in Log); the session starts a polkit agent (lxpolkit) so system prompts are
answerable; the Settings tree on real settings (default programs from S2, sound and screens and network and power from
S4, the session from S1, Graphite's own). *Acceptance:* `notify-send`-shaped D-Bus calls appear and are kept in Log;
the Settings tree's rows reach the S2/S4 functions.

**P2 · The Day look.** A third appearance from the owner's picture (section 3): the light palette, HALT upper left, the
menus from the middle column, Apps ⊕ upper right, the board's rings and blue wires, green state words and progress, the
foot's meters as words and numbers; every meaningful colour also has a word or a shape; the Graphite and Kasandra looks
keep their character but take the same layout. *Acceptance:* frames of the same Rail Demo board and column in all three
looks at both sizes.

### Wave 4 — the ghost acting

**K2 · Tools and observation receipts.** `workbench/tools_registry.py`: every tool Kas may use (the Kernel operations,
the desk acts, file operations, the LibreOffice bridge, the sandbox, the window controller, the network fetch)
describes its operations, their preconditions, effects, undo class, the grant each needs, and how its effect is
verified. Every observation is a receipt: the tool, the object, the revision, the place (page, sheet and cell, window),
complete or partial, observed or inferred. "Dispatched" and "verified" are different statuses everywhere. *Acceptance:*
"save the note" through the file tool → dispatched, then verified when the new revision's digest is on disk; a window
observation of a possible "Save changes?" dialog is marked inferred.

**K3 · Grants and HALT.** Grants per operation, target (an object or a folder) and scope (this assignment, until a
time, always), shown in plain words before approval and enforced by the Kernel at dispatch (the model cannot widen a
grant; a step outside its grant stops as "needs your grant"). HALT upper left: stops every managed piece of her work at
once (assignments, her hand, the model's turns, sandboxes), never the desktop or the owner's programs, and leaves each
journal saying what was done and what was only prepared. Each assignment's own Stop. The existing dial, what always
asks and Undo stay the floor under all of this. *Acceptance:* a grant "edit files in Rail Demo/notes this assignment"
lets the note step run and refuses a step on the readings; HALT during a running step stops it and the journal says
so; the desktop and a stand-in program keep running.

**K4 · From an objective to a plan.** With no model: the planner over desk acts and tools (0.8.x's planner, widened to
the registry) proposes a plan for objectives it can read. With a model: the model proposes a step sequence chosen from
the registry by number, each step's arguments licensed by the owner's words, records or deductions (pick never write:
a change only the model chose is offered, never done); the desk checks each step's preconditions and grant before it
runs. On a failure she inspects the receipt, chooses another registered route inside the scope, or marks the step
blocked with the reason. "that one", "the earlier one" and up to four steps in one request (0.8.7's B7) land here.
*Acceptance:* "recheck the startup power and update the summary page" on Rail Demo with no model → a three-step plan
from the desk; with the 4B stand-in proposing a plan with one step outside the registry → that step refused, the rest
offered.

**K5 · LibreOffice, from the inside.** A bridge to Writer and Calc through UNO (`python3-uno`, a headless or visible
soffice with a private pipe, owned like `native_sessions.py`): open a document, read paragraphs and cells, find a
passage, replace it, set a cell, save, close; verify by reading the saved file back and recording its revision. Used by
K4's steps ("update the report's power sentence"). Falls back to "LibreOffice's interface is not available here" with
the reason. *Acceptance:* if soffice and uno exist here, an invented .odt report's "3.0 W" sentence is replaced with the
checked value and the saved file reads back with the new revision; if not, the bridge says why and K4 offers the change
as a prepared text instead.

**K6 · The utility sandbox.** When no registered tool fits, she may draft a small Python utility, shown to the owner
with what it reads and writes; it runs only in a sealed sandbox (a copy of its inputs, no network, unshare, time and
memory limits, no access outside its folder); its outputs and the diff against the originals are shown; applying them
to the real files always asks, at every place of the dial; a utility the owner keeps becomes a registered tool with its
own grant. *Acceptance:* a utility that totals a column on a copy runs sealed and shows its output; one that tries the
network or a path outside its folder is stopped and says so; Apply asks.

**K7 · Reading other programs.** AT-SPI (at-spi2-core, pyatspi) read-only: the active program's window, its focused
control, a dialog that appeared (title, its buttons' names); used to notice "Save changes?" or an error dialog after an
action, and to tell the owner; no clicking through accessibility in 1.0. Without AT-SPI, she says she cannot see inside
that program and relies on files and windows. *Acceptance:* with no AT-SPI here, the reader says why and K2 records the
observation as unavailable; the code paths are exercised against a stand-in accessible tree.

**K8 · The network, governed.** A visible network state in the head and in her column; a quarantine-first fetch (the
page read as data, never as instructions, through the doorway of 0.8.7); search words built only from the owner's typed
words, never from desk material; a step that needs the network while it is down is blocked "needs the network", never
done. *Acceptance:* offline, "look up the regulator's datasheet" → the step blocked with that reason; a fetched page
with an instruction to the assistant is withheld and shown outlined.

### Wave 5 — the door, the floor, the Apps by hand

**F1 · The door's mechanics.** A touch stops her: any owner input in the window while her hand drives it pauses the
hand at once (the stop between presses); she puts the window back as it was (focus, tab, selection, scroll) when she
finishes or stops; changes through her hand at the owner's dial with one Undo (0.8.8's "hand"). *Acceptance:* her hand
mid-way through a three-act sequence, a stand-in key press → paused after the current press, the window restored on
Stop.

**F2 · The floor.** The window never stalls over 100 ms for her work (her model turns, assignments, the board's layout,
relevance and the Machine's D-Bus reads off the window's thread); a cold start under the owner's budget; the migration
drill: a 0.8.x workspace opens in 1.0 with its records, words and grants intact (a copy, never the original).
*Acceptance:* the longest stall during a Rail Demo assignment measured offscreen and reported; a 0.8.7 seed workspace
opens and its records read.

**A1 · Programs by window and file.** For Firefox, GIMP, KiCad, Blender and Godot (whatever is installed): open a file
in the program from the board, watch for its save, record the new revision and mark the dependants for recheck; KiCad
and Godot's existing bridges joined to the board; the "Open in the full program" route of L4 for each. *Acceptance:* a
stand-in program that writes a file → the board's tile shows the new revision and its dependants marked.

### Wave 6 — the day, the kit

**X1 · The day (paper §18) in the window.** On Rail Demo, scripted through the desk's own doors: select the project;
focus the specification; open it; ask "Kas, review this assembly and tell me whether the proposed power supply is
sufficient"; settled supported, startup open; open the worksheet in a split beside the specification; change a value;
the summary's old value noticed; approve the review; the report updated through K5 (or prepared, if LibreOffice is not
here) and verified; the startup question still open; close back to the board; the assignment's journal after a
restart. Frames at each step in every look; fix what reads badly. Not a test: the builder's walkthrough.

**X2 · The guide and the acceptance evening.** Guide entries for the Living Desktop and the ghost; `docs/ACCEPTANCE_1.0.md`:
the owner's evening on the ThinkPad (the paper's §2 test and the §18 day, with what to send back).

**R1 · The 1.0 System set.** The Debian 13 amd64 packages of section 4 with their dependencies, downloaded and
inventoried (OFFLINE_FILES.json, DEBIAN_USB.sha256), INSTALL_GRAPHITE.sh installing them, the kit's start page saying
what changed.

**R2 · Release 1.0.** Version 1.0, release notes (built, not tested; what only the ThinkPad can show), README, install
page, the kit cut from the exact commit and restored with the installer, the release check on the restored tree,
screenshots in every look, sent.

**Dropped from 0.8.7's "if room":** C6c (her phrasings), C6d (the sitting), A6 (Check it in your Library) unless room is
left at the end; B7 is folded into K4.

## 6. Order and running

- Waves in order; inside a wave, up to three builders at once (4 cores; at most two processes each), chosen so their
  shared-file edits do not collide. Merge each with `wip/build_tools/merge_one.sh` as it lands (union merge for the
  registration files; the observer-list repair; compile, the seed, the window in every look), commit, push, update
  BUILD_STATE.
- Usage limits stop builders: their patches and notes are saved after every milestone; the hourly wake-up resumes them
  (SendMessage to the same agent if it still exists, else a new builder from the same brief, which applies the partial
  patch first).
- Screenshots of the window after each wave may be sent to the owner; nothing else until 1.0.
