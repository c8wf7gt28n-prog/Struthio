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
8. **Her column, as in the owner's picture, without her picture** (the owner, 26 Nov: "No kas avatar anymore"). The
   equalizer's sixteen bars across the top; her name
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

**No picture of her (the owner, 26 Nov: "No kas avatar anymore").** This replaces the portrait decision, P3's
hologram and P5's poses. Graphite 1.0 shows no picture of Kas anywhere, in any look. Her column's top is the
equalizer across its full width, then her name, her model and her state word with its shape. The portrait's
on-screen offers are gone. The shipped art files stay in the tree unused (R2 may prune them), and the kit carries no
picture of her. P4 does this as part of the launch look.

*Superseded, kept for the record:* her portrait was to come from `kasandra/portrait.png` in the owner's workspace
once admitted, the shipped art until then.

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
xsecurelock, lxpolkit, xdg-utils, x11-utils, libreoffice-writer, python3-uno, at-spi2-core, libreoffice-gtk3 (so LibreOffice exposes its accessibility: K9), python3-pyatspi (exact
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
S4, the session from S1, Graphite's own). **The strip as a dock** (found by S3): the program-window strip and a
"Graphite" entry live in a slim window of their own of the dock type with a strut (_NET_WM_WINDOW_TYPE_DOCK,
_NET_WM_STRUT_PARTIAL), so it stays visible above every program and one press always brings Graphite back; programs
are placed below it. **The leave flow** (found by S1) warns which programs are open before Return to Debian, Log out,
Restart or Shut down, and closes them politely (S3's close) before the session ends. *Acceptance:* `notify-send`-shaped D-Bus calls appear and are kept in Log;
the Settings tree's rows reach the S2/S4 functions.

**P2 · The Day look.** A third appearance from the owner's picture (section 3): the light palette, HALT upper left, the
menus from the middle column, Apps ⊕ upper right, the board's rings and blue wires, green state words and progress, the
foot's meters as words and numbers; every meaningful colour also has a word or a shape; the Graphite and Kasandra looks
keep their character but take the same layout. *Acceptance:* frames of the same Rail Demo board and column in all three
looks at both sizes.

**P3 · Kas as a hologram** (merged, then superseded by the owner on 26 Nov: "No kas avatar anymore"; P4 removes it from the screen) (the owner, 26 Nov: "Use her as the on screen kas, like she is a hologram. Not the circle
picture", with a tall full-figure picture of her: a glowing blue wireframe figure in a wide white-and-blue hat with
green trim, on black). Her column's portrait becomes a standing hologram, not a circle: the figure cut free of its
black ground (the picture's dark pixels become see-through, so she floats over the column), drawn with a soft glow,
fine scanlines, a slow shimmer and, at state changes, a brief static, with the equalizer's bars standing behind her as
in the owner's picture. The slot is tall: at 1920x1200 she shows from her hat to below the hips; at 1366x768 from the
hat to the waist; the full figure, larger, for the moments that matter (P1's moments). In the dark looks she floats on
the column; in Day she stands on a dark glass panel of her own (a "projector glass") so the light look stays light
around her. Her state word, name and model ring stay beside her as P1 placed them. The picture comes from the owner's
workspace (`kasandra/portrait.png`, admitted, as P1 built); a picture taller than it is wide is shown as the full
figure, a wide or square one as before. Reduce motion stops the shimmer and static. The shipped art stays the default
until the owner's picture is admitted; the owner's picture never enters the repository (the 1.0 kit carries it to the
owner separately, outside the source).

**L6 · The whole computer in the tree** (the owner, 26 Nov: "Shouldn't the files part of the left tree start at root
/?"). The Files tab starts at **/** (named "This computer"), so every folder the owner's account can read is reachable:
under it **Home** (the owner's home folder) opens by default and is where the tree lands at start; removable drives
(S4) also stand as their own rows near the top ("Drives"); the other system folders are listed collapsed, and the
pseudo-filesystems (/proc, /sys, /dev, /run) are shown as such and never read for the board, relevance or ids. Hidden
files (dot-names) are hidden by default with a "Show hidden" switch. Graphite's own workspace is a folder in Home like
any other, and its records (Concern, Sources, Sheets, Calculations, Findings, Questions) stay in the tree as the **Desk**
drawer, as L1 built it. L1's stable ids extend to any path lazily (an id is made when a file is focused, opened or
linked, never by scanning the disk); the board can focus any file. The owner's own actions anywhere follow the
system's permissions (Graphite never asks for more). **Kas's reach:** she may read where the owner can read (reads
never send anything out: her model is local and sealed); her changes (K2's file tools, K3's grants, K6's Apply, A1)
reach **only inside Home**, under grants as before, and never outside it, at any place of the dial; a grant's folder
may be any folder in Home (not only the workspace's Files). *Acceptance:* the tree's top is "This computer /", Home open
and selected at start, a USB drive under Drives; /proc shown but not read; a grant for a folder in Home outside the
workspace lets her note step run there; a step targeting /etc stops as "outside your home: never".

**P5 · Kas's poses and faces** (cancelled: the owner stopped it, then on 26 Nov: "No kas avatar anymore") (the owner, 26 Nov, five pictures: Kas as a blue hologram in a dark tee with the
Struthio circuit-ostrich on it, jeans and sneakers; a sheet of full-figure poses (standing with a hand on her hip,
walking, turned away, seated thinking with her chin on her hand, crouching, arms crossed, hands behind her head,
pointing), close faces (smiling, winking, eyes closed, a knowing look), a small walking sprite cycle, and a kit: the
ostrich badge, the KAS wordmark, a ring, a panel frame, an equalizer). Her hologram becomes a **set**: a pose for each
state (quiet: standing; working: walking; thinking: chin on hand; waits for you: pointing; done: arms crossed; HALT:
turned away; asleep / no model: eyes closed), a face for the small slots (her name line, a toast, the dock), the
walking sprite in the dock while her hand works in another program, chosen from her state as P1 and K-slices set it,
with P3's treatment (keyed ground, glow, scan lines, shimmer, static at a change; Reduce motion stills it). The pictures
are the owner's and stay out of the repository: the app reads a pose set from the owner's workspace
(`kasandra/hologram/`: `quiet.png`, `working.png`, `thinking.png`, `waiting.png`, `done.png`, `halt.png`,
`asleep.png`, `faces/`, `walk/`), admitted once like the portrait; any pose missing falls back to the one picture or
the shipped art. The coordinator cuts the owner's sheets into that folder (in scratch, never the tree) and the 1.0 kit
carries it to the owner outside the source. *Acceptance:* with the set admitted, each state shows its pose in every
look; frames of four states; with no set, P3's single figure.

**L6b · Home's files, whole** (found by L6). Everything a person does to a file works in Home, not only in the
workspace's Files: open in its program (A1's door; its saves noticed and its revisions recorded through L4), the
working view's watcher on a focused or open Home file, rename, move (drag in the tree), new folder, and DELETE to the
system's Trash (the freedesktop Trash in `~/.local/share/Trash`, restorable, never an unrecoverable delete) on the
owner's press with Undo; Kas's changes (K2's file tools, A1, K5, K9, K6's Apply) all pass `home_reach.her_change` first,
so nothing of hers lands outside Home. *Acceptance:* a letter in ~/Documents opened in LibreOffice from the board, its
save recorded as a revision; a Home file renamed, moved and deleted to the Trash from the tree, then restored; her
note step under a grant for ~/Documents runs; one aimed at /etc stops.

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

**K9 · Her hand in other programs** (the owner, 26 Nov: "Kas is meant to be an AI agentic user of the system also"; and
the earlier road: "she takes the mouse in your programs while you watch"). Beyond K7's reading: she operates the owner's
programs the way a person would, while the owner watches: through accessibility actions first (AT-SPI Action and
EditableText: press a named button, choose a menu item by its path, type into a named field), and through synthetic
keys and pointer (XTest) only where the program exposes nothing, aiming by the accessible object's position, never by
guessed pixels. Each act is a registry tool (K2) with its grant (K3; "work in <program> on <file>, this assignment"),
its effect verified by what K7 then reads or by the file on disk (K2's receipts), a touch of the owner's mouse or keys
stops her at once (F1), HALT stops her, and she never types a password, never presses Send, Pay, Delete or Install in
another program (those always ask, at every place of the dial), and never acts in a window she did not open or was
not shown. Acceptance: under Xvfb with a real program installed here (LibreOffice in a visible window, through its
accessibility): open the invented report, find the sentence through the accessible text, replace it, save with the
menu's Save, and verify the file on disk; a dialog 'Keep current format?' read and answered only as granted; a key
press from the owner stops her between two acts.

**K4b · Her plan in time on a slow machine** (found by K4: with the real 4B here the PLAN turn was priced at 15.8 s
and came late at its 20 s deadline, so the desk's plan was offered). Prime PLAN's standing instructions and the tool
menu into the model's kept prompt when the model becomes ready (0.8.7's A2 prompt reuse; X7b did the same for READ),
keyed so a changed desk or registry primes again; keep the PLAN prompt lean (the menu as short numbered lines; only the
desk's handles the request names); measure the second PLAN turn with the real 4B here. Never raise a deadline or the
request's ceiling to make it fit: if it is still late, say so and leave the desk's plan as the fallback.

**The model in the loop** (the owner, 26 Nov: "How come we never have a LLM running?"). From K4 on, the slices where
the model has a part (K4's plans, K6's utilities, K9's acts, X1's day) run their acceptance once with the real 4B here
(under the model lock; this machine cannot hold the 35B), and frames show her with the model ready. X1's day runs with
the 4B loaded.

**M1 · Her model's runtime, current** (the owner, 26 Nov: "to manipulate the LLM let's make sure we're using the
latest and best technologies"). Graphite has bundled llama.cpp b11669; the project released **v1.0.0 on 13 Nov 2026**
(tag v1.0.0 = build b12359, commit b1b770d90d94cad9e9ea5b993bdbc383a522fb28; its first stable release with a promise
not to break its interface), and its official Ubuntu Vulkan and CPU archives are downloadable here. Move the bundled
runtime to v1.0.0 the way b11669 is shipped (`runtimes/llama.cpp/<build>/`: both archives, LICENSE, runtime.json with
the archive sha256 and the source commit), and put its newer capabilities to work where they help her, each measured
here with the 4B before it is on by default and each a setting the model check (A5) measures on the ThinkPad:
**multi-token prediction** (MTP speculative decoding for Qwen3.6 with an MTP GGUF: reported about 1.85x faster
writing on the 35B-A3B; the first evening names the exact MTP file and its hash if one exists for the owner's model);
the **host-memory prompt cache** (`--cache-ram`, sized from the memory sum, so PLAN's and READ's kept prompts both
survive: K4b's finding); **flash attention** and the **quantized KV cache** where the Vulkan path on the Radeon 680M
supports them (the model check judges them; defaults stay safe); **load-mode auto** for the integrated GPU (no double
memory through mmap); the model's own **jinja chat template** with thinking off; structured output through the
server's JSON-schema path where it is at least as strict as her own grammars (her GBNF grammars stay where they are
stricter). Bring every other place up to date: the seal's allow-list and refused-argument list from v1.0.0's own
`--help` (brain_seal.py; the seal checked again with a real start), the memory sum (A2) for the new KV types and the
MTP head, her clock's rates, the model check's stages and predictions, the pins (I04/I05, hatch readiness), and the
kit's first-evening page. *Acceptance:* the sealed 4B starts on v1.0.0 here and passes every wall; PLAN and READ kept
prompts both survive a priming round (cache-ram); the second PLAN turn's time on Rail Demo against K4b's 3,300 ms;
MTP's effect measured if a 4B or 2B MTP GGUF exists (else said); every refused argument still refused.

**M2 · A quick model beside the 35B, for 99 tokens a second** (the owner, 26 Nov: "The goal is 99 tokens per second,
up and down....if possible"). Reading at 99+ is likely on the Radeon 680M with the 35B-A3B; writing at 99 is not (its
memory bandwidth bounds the 35B's writing to roughly 20 to 30 tokens a second, perhaps 40 to 55 with MTP; to be
measured by M1's sweep on the ThinkPad). Her questions are short (20 to 60 tokens of answer over kept prompts), so the
way to 99 writing is a second, small model for the quick kinds (READ, PLAN, NEXT, MARKS, ASK) held beside the 35B
(memory allowing: the memory sum counts both), used for a kind **only when that model has passed the exam for that
kind** (A5's per-model-key, per-kind record) and measured faster; the 35B keeps the kinds that need it (wording,
utilities, anything the small model fails). Her clock prices each kind on the model that would answer it; the Brain
room shows which model answers which kind and why; Undo puts every kind back on the 35B. The model check measures the
pair and proposes the split. *Acceptance:* with the 4B and 2B here, the 2B takes a kind only after passing its exam
items, and her clock and the Brain room show the split; the speeds here said to mean nothing for the ThinkPad.

**M1b · Her model's memory cap and her measured rates** (added at M2's merge, 26 Nov, from M2's findings). (1) On
the processor the runtime's memory cap limits address space, and llama-server sits about 930 MiB over its estimate at
Ready. M2 fixed the cap for the quick model (the estimate plus the larger of 2 GiB and half the estimate, with cap and
tier agreeing). Her own model needs the same treatment wherever the owner sets an explicit cap, so a cap near the
estimate cannot crash her as M1's larger prompt cache fills. Where the owner's cap is too tight, say so in the Brain
room with the numbers before loading. (2) M1's tuning stage saves its measured rates in the model check's temporary
profile, which is deleted, so her clock never sees them. Carry them out the way M2 carries the pair's rates, so her
clock starts from what this machine measured. *Acceptance:* the 4B loaded once under the lock with an explicit cap
near its estimate, staying up through a primed READ and PLAN, or refused beforehand with the numbers; the tuning
stage's rates seen by her clock after the model check closes.

**K10 · Her reach in Home, finished** (added at X3's merge, 26 Nov, from X3's walk: "her answers about files in Home
don't read the files' pages"; "the model's planning menu has no file tools and plans at most four steps"; "under one
grant, the tidy's folder-making steps still waited for their own word"). (1) Asked about a document in Home (a PDF, an
.odt, a .txt, an .ods), she reads its pages through the existing readers as data, behind the same doorway as a source
(a line written to an assistant is withheld), and answers with the page it came from; "the records say nothing" only
when the pages do not either. (2) The model's PLAN menu gains the Home file tools (list, new folder, move, rename,
copy, delete to the bin) behind home_reach and the grants, and a model's plan may run to eight steps (the desk's own
planner keeps its length). (3) When a plan's steps in one folder need several operations, the grant card offers them
together in one press, each operation named in plain words. A grant is still per operation, target and scope, and
the Kernel still enforces it at dispatch. (4) D2's finding: her state word says WORKING during Graphite's own
background reads with no assignment open. Her state word follows her work only. *Acceptance:* in X3's everyday Home,
"what does the manual say about descaling?" answered from its page with the page named; the 4B (once, under the lock)
plans a tidy of Downloads from the file tools; one grant press covers the tidy's folder-making and moves; her state
word QUIET while only Graphite reads.

**F3 · The walkthroughs' faults** (added at X4's merge, 26 Nov, from X4's and X1's accounts; each breaks an item of
section 2). (1) Item 13: a fetch cut short when the network dropped was counted "done (verified)" and NET still said "her
fetch". A fetch is verified only when it is whole, and a step that needs the network while it is down is "blocked: needs
the network". (2) Item 10: a grant given while HALT holds must carry its assignment through after RESUME and its own
Resume, and the built-in grant "edit files in her own area, always" must cover a proposed step writing there. (3) TRACE
from her column on a finding focused on the board traces that finding (it asked "Which of these did you mean?"). (4) Her
column tells the truth at once: after a restart it reads ACTIVE WORK and FINDINGS from the journal and the desk (it said
"No assignment is open" with one waiting); her model line follows the brain's state (it said "no model yet" with the 4B
sealed, and "her model is answering" after it stopped); ACTIVE WORK follows Stop. (5) The window's thread does no work
over 100 ms where X4 measured seconds: TRACE and CHECK ALL (4.2 s), HALT and RESUME (1.5 to 1.8 s), asking her (1.8 s),
the board's rebuild after a cell change (2.1 s), on F2's floor workers. (6) The HALT toast never covers "Waits for you".
(7) Search: a hit opens the board's focus (not the old Cabinet record tab) and Back returns to the results; Home's files
are found by name; several words match separately. (8) Accessibility: every keyboard stop has a name a screen reader can
say (X4 found seven without), and Tab reaches the presses in a scrolled page (Storage's Mount and Eject). *Acceptance:*
each case replayed as X4 walked it (its scripts are in scratch), before and after.

**L6c · Bulk files** (added at X4's merge, 26 Nov: "the power user's first want"). The Files tree selects many rows
(click, a range, add one); Move to…, Copy to… and Delete act on all of them in one press, with one line and **one Undo
for the batch**. A line can move or delete what it lists, as a step that asks (one press, the count and the folder shown;
Undo for the batch). The sandbox takes a folder's worth (its file cap raised from 8 to 64 within its size limit), and its
Apply offers Undo for the files it made new. *Acceptance:* 48 invoices moved in one press and put back with one Undo; 50
deleted and 3 restored; a line moving a pattern's worth with one Undo; the dedupe utility over 24 photos with Apply and
Undo.

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

**F2b · The floor, finished** (added at F2's merge, 26 Nov). F2 shortened the stalls (longest 234 to 354 ms, from 341 to
750) but did not reach 100 ms. The workspace's lock admits one connection at a time, readers included, so a read on the
window's thread waits while she writes. Move the rest off the window's thread: the head control's tick, the board's
rebuild on a tile click, opening the Field, the left tree's paint under load. Or give read-only operations a shared
read path (WAL readers beside the one writer) if that is safe for the journal. Also list a 0.8.x assignment left
running in ACTIVE WORK (F2's drill found only the new kind listed). *Acceptance:* F2's measured Rail Demo assignment,
before and after, in Day at 1920x1200 and 1366x768, with the longest stall at or under 100 ms or its remaining cause
named; F2's migration drill still 16/16.

**A1 · Programs by window and file.** For Firefox, GIMP, KiCad, Blender and Godot (whatever is installed): open a file
in the program from the board, watch for its save, record the new revision and mark the dependants for recheck; KiCad
and Godot's existing bridges joined to the board; the "Open in the full program" route of L4 for each. *Acceptance:* a
stand-in program that writes a file → the board's tile shows the new revision and its dependants marked.

**D1 · The design direction, applied** (the owner, 26 Nov: "Bottom left no longer need a kasandra option, because that
exists already in the right Kasandra column" and "take more control of how the desktop is designed"). Apply
`DESIGN_DIRECTION_1.0.md` sections 2 to 7: the foot's chooser Line · Terminal · Search · Web · Log with Line the default
(lines, operations by name, addresses) and "Ask Kasandra →" for words meant for her; NET in the meters; one table of
state words and shapes (`workbench/state_words.py`) read by tiles, wires, steps, her state and the dock; one centre bar;
the "Waits for you" band at the top of her column; Day as a fresh profile's look; the empty and first states.
*Acceptance:* the foot has no Kasandra; a Graphite line typed in Line runs; "recheck the startup power" typed in Line
offers Ask Kasandra → and, pressed, lands in her column as a plan (K4); frames in three looks at two sizes.

**P4 · The launch look** (the owner, 26 Nov: "Day or other modes, I want you to create a default version that is
apple/microsoft level refined for the 1.0 launch"). `DESIGN_DIRECTION_1.0.md` section 9: `workbench/design_tokens.py`
for Day and Night; Inter bundled (Regular, Medium, SemiBold, Display SemiBold, with its licence) beside the bundled
IBM Plex Mono; Day rebuilt on the tokens and Night made from them; every surface reads the tokens; the move to Day on
1.0's first start. *Acceptance:* frames of every main surface (board, working view, split, her column, Apps, Machine,
Settings, menus, the dock, a toast, the Grants page, the sandbox tab, an empty workspace) in Day and Night at 1920x1200
and 1366x768; every text pair measured ≥ 4.5:1; no colour literal for Day or Night outside the tokens. **And no picture of
Kas** (the owner, 26 Nov: "No kas avatar anymore"): her column's top is the equalizer, her name, her model and her
state word; the left pane's hologram, the art stills, the BOSS plates of her and the portrait's offers are gone, in
every look.

**X3 · Everyday sessions** (the owner, 26 Nov: "Should we simulate general user operations instead of the same rail
tests?"). An invented everyday Home (`workbench/everyday_demo.py`, built through its own door in a throwaway folder):
Documents (a letter, a lease PDF, a manual PDF), Pictures (a dozen small invented photos), Downloads (a messy mix:
PDFs, images, an .ods budget, a .zip, duplicates), Music, Desktop; a household budget in Calc; a stand-in USB drive
with photos. Twelve ordinary sessions walked end to end in the window, under Xvfb with the stand-in window manager,
in the Day look, as a person would use the computer, each with frames and a plain account of what happened:
1. first start with no model: Home, open a photo, open the manual, back to the board; 2. files: make "Taxes 2026",
move three PDFs from Downloads into it, rename one, Undo; 3. a USB drive: copy its photos into Pictures, eject safely;
4. a letter: new document in LibreOffice through Apps, save, see it on the board, an outside edit noticed; 5. the
budget: ask Kas "what did we spend on groceries this month?" and read her answer with its receipt; 6. ask Kas to tidy
Downloads (sort by type into folders): her plan, the grant, the steps verified, the result, Undo; 7. the web: look
something up offline (blocked), then online on the stand-in (quarantined, an injected line outlined); 8. two programs,
the dock, a notification; 9. Settings: the default PDF reader, the volume, the screens (stand-ins); 10. HALT in the
middle of a task, then RESUME; 11. her hand in a program: fill a field, a touch stops her; 12. leave: Log out with
programs open (polite close). Kas's language parts run once with the real 4B under the model lock. The builder fixes
what is small and clearly broken in place and lists the rest, ranked, for D2 and F2. Not a test suite: a walkthrough,
like X1, by the owner's rule.

**X4 · Power-user sessions** (the owner, 26 Nov: "Double the casual user deep scenarios to power user situations").
X3's method, applied to twelve deeper sessions by someone who uses the whole system: the everyday Home grown to a busy
one (200+ files in Downloads, a desk of 300+ records beside Rail Demo, two drives), in the Day look, under Xvfb with
the stand-in window manager. Each session has frames and a plain account.
1. **Lines and the Terminal:** chain a line, keep it, run it again on another folder; maths in a line on the budget
   (money exact); the same work in Terminal with a real shell; every output in Log.
2. **Search everything:** the Search tab across Home's files, the desk's records and the Log; open a hit in place;
   narrow it; come back to it.
3. **Bulk files:** select many, move a pattern's worth with a line, Undo the whole move as one; delete 50, restore 3
   from DELETE.
4. **Three assignments at once** under different grants: one waits for a grant, granted from "Waits for you"; a grant
   revoked mid-run; one stopped; HALT holds all; RESUME restarts nothing by itself.
5. **Split and recheck:** the specification left, the worksheet right; a value changed; the dependants marked; TRACE a
   finding back to its cells; CHECK ALL.
6. **A utility in the sandbox:** a job no tool fits (dedupe photos by content and rename them by date); Kas drafts the
   utility; its code read; run sealed on copies; applied only when asked; Undo.
7. **Her hand across two programs:** a table from Calc into a Writer report under grants; a dialog that needs review;
   a touch stops her; both windows put back.
8. **The network, adversarial:** a fetched page carrying a line aimed at an assistant (withheld, outlined); the
   network dropped mid-fetch, so the step reads "blocked: needs the network"; search words only from typed words.
9. **Crash and resume:** the window killed mid-assignment; the supervisor brings it back; programs stay open; the
   journal resumes without repeating a step; a suspend (stand-in) in the middle.
10. **The board at scale:** relevance, Pin, Turn down, Why am I shown?; ten hops back and forward; tabs; the longest
    stall reported.
11. **Her model:** the Brain room; the model check's tuning sweep on the 4B; the measured settings applied, then Undo;
    HALT during a model turn; the model removed, so she says what she can still do.
12. **The machine under load:** two screens, extend and mirror, with the timed revert; default programs by type; a
    drive ejected while a file on it is open (refused, naming the program); Log out with unsaved work in LibreOffice
    (asked politely, never killed); one whole pass by keyboard alone, the focus always visible.
Kas's language parts run once with the real 4B under the model lock. Runs after F1 and F2 are merged, so it walks
their work. Small, clear fixes are made in place; the rest is ranked for D2 and the coordinator. A walkthrough, not a
test suite, by the owner's rule.

**D2 · The polish pass** (after every feature slice, before X1): every surface in three looks at two sizes, fixed in
place to the design direction; a frame atlas for the owner.

### Wave 6 — the day, the kit

**X1 · The day (paper §18) in the window**, with the real 4B loaded (her model ready). On Rail Demo, scripted through the desk's own doors: select the project;
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

- From X3 on, the everyday Home is the frame scene alongside Rail Demo (F1, F2, P4, D2, X1).
- Waves in order; inside a wave, up to three builders at once (4 cores; at most two processes each), chosen so their
  shared-file edits do not collide. Merge each with `wip/build_tools/merge_one.sh` as it lands (union merge for the
  registration files; the observer-list repair; compile, the seed, the window in every look), commit, push, update
  BUILD_STATE.
- Usage limits stop builders: their patches and notes are saved after every milestone; the hourly wake-up resumes them
  (SendMessage to the same agent if it still exists, else a new builder from the same brief, which applies the partial
  patch first).
- Screenshots of the window after each wave may be sent to the owner; nothing else until 1.0.
