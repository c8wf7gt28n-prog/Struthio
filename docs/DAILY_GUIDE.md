# Graphite · daily guide

November 7, 2026 · Graphite 0.1. Graphite is the public name of the workspace (earlier Ledger & Slate); its assistant is Stacy (Kasandra in the Kasandra appearance); folders, scripts and settings keys keep their earlier names. The owner's short guide for a working day: what the program does in this release. It does not claim owner-host acceptance: the ThinkPad, its display and inputs and the owner's model file are still to be tried. Installation is in the README and docs/MINIMAL_DEBIAN_INSTALL_01.md; how each part works is listed in RECORD_OF_DIRECTIONS.md, under Where the knowledge is.

## Start and stop

- From a text login on the minimal Debian machine: `bash START_MINIMAL_DEBIAN.sh`. It starts the dedicated Fluxbox session with Graphite fullscreen and prints `Graphite ended with status N` when you leave. From an existing desktop the same command opens the fullscreen Office instead; `bash START_OFFICE.sh` opens the ordinary window.
- Graphite opens on the work. When this workspace has anything in it you start in the Field (below), with what waits for you selected; Esc goes to where you left off. An empty workspace starts on Home. Home's own choice "Start: always Home" starts on Home every time.
- Leave through the last group of the Work menu → Return to Debian (in the dedicated session) or Exit Graphite (elsewhere). Graphite asks about unsaved files, offers a return copy, stops its own model and tracked commands, then closes. The computer stays on.
- The same group holds Log out (this login session), Restart and Shut down (this computer). Each asks what leaving asks (unsaved files, the return copy), then asks you to confirm, naming what it affects. Nothing is stopped before you confirm, and Cancel leaves Graphite as it was. Then Graphite closes the ordinary way (the local model and tracked commands stop, running assignments pause, the session is saved) and only then asks the system itself (logind, through loginctl or systemctl, never sudo), because ending the session or the computer ends Graphite at once.
- When the system does not allow one of them, or Graphite is not running in a login session, its row says unavailable; F1, its tooltip and choosing it say why, and Graphite stays open. In the dedicated session nothing can answer the system's own permission prompt, so a Restart or Shut down that would need one is unavailable there: Return to Debian and use `systemctl reboot` or `systemctl poweroff` at the text login. If the system refuses at the very last moment, Graphite has already closed with your work saved and tells you why.
- Graphite services (the admission of new work) are separate from leaving: click the GPU meter → Graphite services → On, Off, Restart cycle Graphite's own services, never the computer, and keep the desktop open.

## The Field (new in 0.3)

Press **F9** for an overview of the work in this workspace: sources, reviewed sheets, calculations, pages, findings and open
questions as sheets, with wires that show what feeds what. Arrow keys follow the wires, Enter opens the real page, F9 comes
back to the same sheet, Esc leaves. Stacy's rail at the right shows the line that reads the selected sheet: S puts it in the
writing strip, Shift+Enter runs it. Ask Stacy about a sheet (its menu, or just type a question while it is selected) and she answers in
Talk: with no model she shows the line that reads it and what the records say. Right-click a sheet (or press the Menu key) for what can be done with it. **P** shows every program and room as a shelf in six fixed columns
(Work, Think, Make, Build, Move, Set up): Enter opens one. N shows this computer's network the same way; W returns to the
work. With a model loaded Stacy reads the sheet first and then says the answer in her own words under the rows; say "this"
in your question and she takes the selected sheet. **D** asks the records what can be done about the selected sheet: the
steps show numbered, a digit takes one, a read runs at once and a change marked "asks first" waits for your go (**G**, or
Approve in Talk; a digit never approves a step that waits). How far Stacy acts by herself is the two words under her face
(Ask first, Do and show, Free hand): with Do and show a change you ask for or take is made at once and has an Undo. **C** checks the desk and says what waits; **1** then puts up what needs no decision of yours and
**G** is one go for the listed changes; the desk checks itself again. On the shelf, **F** offers a program's full window on
one of its files. A turned corner marks what changed in the last twelve hours. **T** traces the selected sheet back to its source and on
to what rests on it. With a calculation selected, ask "what if B3 were 320?": Stacy works it exactly and changes nothing.
In the writing strip `this` is the selected sheet (`this | count`, Ctrl+Enter), and `field.read` is the whole desk as
records (`field.read | pick waiting | select kind,title,state`). **X** doubts the selected sheet: Stacy puts exact questions to the records and shows what does not hold, what she cannot
tell and what holds; **D** then offers the step that removes a doubt, and **C** lists what she doubts across the desk.
"What if" also works with a sheet selected, by cell or by the row's words ("what if the pulse duration were 100?"): the
change is followed along the wires, nothing is changed, and the Field marks what would move until **Esc**. **B** shows the
desk written up as one page from the records; **G** keeps it as a page, and D on that page writes it again when the desk
has changed. **Backspace** goes back to the sheet you were on before. In the writing strip you can keep a line under a
word of your own: `word waits = field.read | pick waiting | select kind,title,state`, then `waits` (Ctrl+Enter), `words`
to list them, `forget waits` to let one go. Right-click a sheet (or the Menu key) for the same things as cascades: What if ›
a number › a value to try, Doubt it ›, Trace it ›, What can be done ›, Your words ›; choosing in a menu never approves a
change. **?** shows every key of the Field on a card. The doubt, the desk check and the brief open on a page over the work,
at your reading size; the doubt and the check step aside at the next key you press, and Esc closes any of them.
With the mouse: a click on a tile opens it in the centre, and **‹ Field** in the bar above the centre comes back to the same tile; the
right button shows a tile's menu; every key shown at the foot, on the key card and on a page can be clicked; a change that
waits has an **Approve** button. Ask Stacy "set B3 to 300" with a sheet selected: with her hand at Do and show it is done at once and has an Undo; at Ask first it waits for your Approve.
The pointer is the desk's green, and whatever it is over answers in green; amber is what is selected and what waits for you.
Above whatever is open in the centre there is one row of controls: **‹ Field**, Find, **−** **+**, Undo, Redo, Save; one that
the open view cannot serve is dimmed and says why, and Save is lit only when there is something to save. In the Field **Z** shows the
whole desk (again for the ordinary size), the bars at the edges drag, and the right button on a sheet shows its menu. The amber light is where the keys go.
An action is a button, a dark plate with a quiet edge; a word that only goes somewhere is underlined. Each work page has one row of tools above it, and
**More ▾** holds what is needed now and then. A PDF page is shown in the desk's light (the same page, its paper brought down from white);
**More ▾ → Show the page in its own light** shows it as the file has it, and the choice is kept.
**Find** (Ctrl+F) opens one line above the work and searches whatever is open: writing, the cells of a sheet, a list, the lines of a finding, the words of a PDF page; Enter goes to the next place, Shift+Enter to the one before, Esc closes it.
With the whole desk in the window (**Z**), each sheet is the glyph of its kind, its name and the mark of its state, all large enough to read; the Field opens as you last saw it.
The menus (Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide) stand across the head; after them, in the middle, is an equalizer: each bar is one processor thread of this computer over the last second (amber at the top of a bar near its limit, amber along the bottom while Graphite itself is working). The bar above the work says the name of what is open and whether it is saved; click the name for its address, which comes up at the head while you type it.
The right pane is one view, **Stacy**: her face, **This** (what is open, or the sheet selected in the Field; **more** opens everything about it), **Now** (what is running and what waits for you; **activity** opens the whole list), then the conversation. While the whole of either is up, the pane's title is the way back.
**Stacy's hand.** Under her face, beneath what she speaks with, two words say how far she acts by herself; click them (or **Rules ▸ Stacy's hand**) to change it. **Ask first**: every change waits for your Approve. **Do and show**: a change you ask her for is made at once; she says what she did, and its card has **Undo**, which puts back exactly what it took and is refused if the thing was changed again since. **Free hand**: she also makes the changes the records mark for approval, and after a change she checks the desk and brings back to current what stood on it. On every place, what cannot be undone asks first (sending to another computer, removing what cannot be brought back, emptying the Trash, ending the session, a Terminal command that is not a plain read). **What she did…** in the same menu is her trail. Say "make a folder called Bracket", "write a file called Bracket/plan.txt saying cut the stock first", "start a page called Bench plan" or "make a note called Rail idea that says try a ferrite" and the thing is where your own would be; a folder or file she made has an Undo that moves it to the Trash, and she never writes over a file that is there. Say "run df -h" and she runs a command that only reads; any other command she puts in the line for you.
**A start in Godot.** Say "start a Godot project called Lander" (or "get me started in Godot"). Stacy makes the folder `Lander` in Files with `project.godot`, `main.tscn`, `main.gd` and `START_HERE.md` (the first five minutes in Godot), written for the Godot on this computer: Godot 3, which Debian installs as the package `godot3`, or Godot 4. She says what the Godot room reads it as; "Open it in Godot" waits for your Approve (with a free hand she opens it); the words on her card read the first steps, read the script, or open the Godot room, which inspects the project, opens it in Godot or plays a scene. Undo moves the folder to the Trash.
The line at the bottom is the one place you type. Five names stand at its left (**Stacy · Terminal · Search · Web · Log**) and the lit one gets the words. Web opens an address, or searches for words, in this computer's own browser (Graphite fetches nothing); with Stacy or Search lit, a line that is only an address (https://…, www.…, localhost) is opened there too, and anything else stays with whom it was typed to: typing never changes the name that is lit. The arrow at the end says what it will do; when the line reads as a line it turns green and runs it.
**Two appearances (0.8.0).** **Rules ▸ Desk artwork ▸ Appearance** chooses **Graphite** (pencil, paper and amber) or **Kasandra** (indigo; cyan for what is selected or ready, raspberry for what waits for your Approve, lavender with a dashed edge for a recheck). The choice is this computer's and is used from the next start; choosing it offers to start again now. In Kasandra the assistant is called Kasandra, headings are in a typewriter face, and her pictures follow the work: the quiet bench at rest, her hand by Enter while a change waits for you, notes while she answers or a job runs, the pencil down after an Approve, a loose cable after a refusal. The Office shows her office with the kasandra protocol wordmark. Clean shows no pictures in either.

**Rules ▸ Desk artwork ▸ Glow** sets how strongly the desk glows: Soft, Bright or Neon (what it opens with). Keys work as they always did but are not printed beside what they do; the **?** key in the Field lists them. In the left tree the traces from the root to the row you are on are lit.
Every tool is one of Graphite's own glyphs with no box (a tool particular to a page keeps its words beside its glyph; a glyph alone says its name in its tip); **Work ▸ Rules ▸ Buttons ▸ Words** brings back worded plates.
`docs/RELEASE_NOTES_0.8.1.md`, `docs/RELEASE_NOTES_0.8.0.md`, `docs/RELEASE_NOTES_0.7.0.md`, `docs/RELEASE_NOTES_0.6.1.md`, `docs/RELEASE_NOTES_0.6.0.md`, `docs/RELEASE_NOTES_0.5.3.md`, `docs/RELEASE_NOTES_0.5.2.md`, `docs/RELEASE_NOTES_0.5.1.md`, `docs/RELEASE_NOTES_0.5.0.md`, `docs/RELEASE_NOTES_0.4.9.md`, `docs/RELEASE_NOTES_0.4.8.md`, `docs/RELEASE_NOTES_0.4.7.md`, `docs/RELEASE_NOTES_0.4.6.md`, `docs/RELEASE_NOTES_0.4.5.md`, `docs/RELEASE_NOTES_0.4.4.md`, `docs/RELEASE_NOTES_0.4.3.md`, `docs/RELEASE_NOTES_0.4.2.md` and `docs/RELEASE_NOTES_0.4.1.md` have the details. `docs/RELEASE_NOTES_0.4.md` has the details. `docs/RELEASE_NOTES_0.3.md` has the details.

## The desk

The window is one symmetrical desk: two graphite bands, the head at the top and the writing line at the bottom, with warm paper between them, a pane at each side and your work in the centre. Both panes are one width (drag either edge and both follow; Settings → Workspace → Left column width sets both), and the desk is mirrored about the window's centre to the pixel. Lettering on the bands is pale, as if erased from the shading; words you can act on are eraser pink; the choice in use has a short yellow mark under it. Words you may skip (a caption, a note, an explanation) are in the script, and what you act on or read first stays in print; Arrange → Pleasantries in script turns the script off everywhere. The desk's measures are in docs/GRAPHITE_DESK.md, and its "Where things went" says where each older control went.

1. **The head.** Work · Revise · Tools · Arrange · Commands · Rules · Properties · Guide stand at the left. In the middle is the equalizer: this computer at work in six groups (processor, kernel, memory, disks, network, graphics); click it for what each reads now. At the right, Programs. (There is no System menu since 0.7.0: see The four meters, and leaving, below.)
2. **The left pane.** Three tabs, Machine · Cabinet · Settings, each a tree with connecting branch lines, and Trash, larger, at the lower right. Machine is this computer (processor, memory, storage, connections, devices, installed tools); every row's tooltip says where and when its reading was taken, and the Machine row's carries the one-line machine summary. Cabinet is your work by project: ideas, documents, assignments, questions, working copies. Settings is the shared registry Graphite reads too, under Workspace and Assistant. Nothing else sits in the pane: Import and Export are in Work, the cabinet's views and Refresh are under Arrange and on the tree's right-click, and Search finds records and settings by their words.
3. **The centre.** The real work. Documents, source files, calculations and workspaces open here. One Preview tab reuses itself; up to five pins stay; workspaces opened from a menu are rooms beside your Preview and never replace it. With nothing open the centre is the Finder (below).
4. **The right pane.** Stacy. Her face, what she speaks with, and two words for her hand (how far she acts by herself; click them to change it). **This:** what is open or selected, with **more** for everything about it (Context). **Now:** what runs and what waits for you, with **activity** for the whole list. Then the conversation. While Context or Activity is up, a title at the top of the pane is the way back to her.
5. **The writing line.** The lower band, as tall as the head. At its left five names, Stacy · Terminal · Search · Web · Log: the lit one gets what you type. Then a small control that opens the room above the line (one chevron: more; two: taller; one down: close), one long line to write in (its empty hint is `poem`), and the arrow, which says what it will do. At the right the four meters, CPU · GPU · RAM · TXT, each a door (below).

The pointer is the Graphite mark's two facets aimed at eleven o'clock, the click at its tip. Text fields keep their I-beam, and the pane edges show the resize pointer while you are over them.

## The cat and the programs list

The cat at the lower left, pale paper on the band, opens the programs list: one click, even while it dozes, or Space or Enter when it has the focus (its tooltip says Open programs). It rests with graphite eyes, glances sideways with yellow eyes and a question-mark tail when you point at it, lifts a paw while the list is open, and closes its eyes after a quiet while. Under Reduce motion it changes pose at once.

The list is like the Programs folder of a Start menu: every program and capability Graphite has, one plain name and one small graphite icon each, A to Z (Agenda, Assignments, Calculator, Documents, Files, the KiCad, KiBot, ngspice, Yosys, nextpnr & Trellis and HDL checks, Laboratory, Local model, Memory, Methods, Office, Projects, Questions, References, Settings, Sources, Tool Atlas, Work trail), then Explore the workshop. Type a name's first letters to jump to it; Up, Down, Home and End move; Return opens; Escape closes. A row's word at the right says only what Graphite observed: open, N running or interrupted, needs setup (a program was not found), unavailable. F1 or the tooltip gives the full description: what opens, what Graphite can do there, what is missing. Opening a row runs nothing. Creating things is not in the list: New Idea (Ctrl+Shift+N) and New Project are under Work.

## The four meters, and leaving

The System menu is gone since 0.7.0. Click a meter at the foot of the window and its card opens upward; a click elsewhere puts it away.

- **CPU**: Graphite's work. **Stop all jobs**, the one stop for every job, model, assignment and capture Graphite manages (also Tools → STOP / KILL); programs Graphite does not manage keep running. Then the process list: active jobs as they started, then the queue; each row's slider is its niceness, left more urgent and right nicer; the queue's order is a separate control (the place number at the left of a queued row, drag, Earlier and Later). Background CPU priority. Open Agenda and Work trail.
- **GPU**: Stacy's model (**Brain room**) and **Graphite services** On · Off · Restart: Graphite's own services, never the computer.
- **RAM**: memory in use, swapping, disks and network, and **Machine** (this computer, in the left pane).
- **TXT**: **Full chat**, and **What she has in view**.
- **Game** is the last row of **Programs**: STRUTHIO, in its own window, paused at tick zero (below, The game behind the mark).
- At the foot of the **Work** menu: **Log out**, **Return to Debian** or **Exit Graphite**, **Restart**, **Shut down** (above, Start and stop).

From the keyboard the symbol opens with Game under focus; Stop all jobs is one Down away.

## The writing line

One place to type. Ctrl+K puts the cursor there in Search from anywhere. Choose a mode with its word at the right, with Alt and a number, or by typing its lead character first on an empty line:

- **Assignment** (Alt+1): give Graphite work in your own words and press Enter. A typed line that reads (the structured commands) runs only when you press Ctrl+Enter, and the line says so while what you typed is one; Enter never runs it. Up on the empty line brings back the line you ran. A line starting with `/` runs an operation by name (Alt+3, or Commands → Run an operation…).
- **Shell** (Alt+5, or start with `$`): the line goes to your configured shell, in your Files folder; the word reads Bash when that shell is bash.
- **Search** (Ctrl+K, Alt+4, or start with `?`): files and their words, the cabinet, settings and commands, results under the line as you type; Enter searches everything.
- **Log** (Alt+6): above the line at Half or Tall, two streams chosen with the Events and Network tabs (below).

Choosing a mode never opens or closes the working area; running a line opens it at Half, and Line closes it.

## Log: Events and Network

**Events** is Graphite's own record of what happened, newest at the bottom, with Follow latest. Words in the line and Enter filter it. There are no notes: Log follows; it does not take notes.

**Network** is this computer's network as Graphite observes it, read from the system without privileges and without sending anything: each interface with how fast it receives and sends, and every open connection with the program that holds it. Type a host, a port, a program, a protocol or a state (`10.0.0.5`, `443`, `firefox`, `tcp`, `listen`) and press Enter to filter; words of one kind widen, kinds narrow.

Ctrl+Enter in the Network stream (or Capture… above it) captures packet headers with the line's filter. The first capture after Graphite starts asks once, saying exactly what is captured: headers only (addresses, ports, protocol, length, TCP flags, never what packets carry), this computer's own interfaces, never in promiscuous mode, at most 60 seconds or 2,000 packets, nothing leaving the computer. Stop capture ends it, and so does Stop all jobs. Capture needs the system's own capture tool: when it is not installed or not allowed, the stream says so and lists the steps for the administrator (Debian's wireshark-common and its group; `bash INSTALL_DEBIAN.sh --network-capture` adds the package); Graphite never runs them and never asks for a password. Capture only networks you own or may monitor.

Click an entry in either stream to pin it at the top while the stream moves on. **Ask Stacy about this** puts it in the line as an assignment's subject; **Follow this conversation** filters the stream to it.

**What Graphite can inspect.** During an assignment Graphite may read what the Network stream shows: the interfaces, the connections and the packets of the latest capture. Ask in Assignment, for example `what is talking to the network?` or `what ports are open?`, and it writes a findings page saying who talks to whom and what listens. It never starts a capture: when one would help, it proposes it, the assignment waits, and the proposal shows in Log, Network for you to start (or not). docs/NETWORK_01.md has the details.

## The right-click menu

Right-click anything you are working on, or use the keyboard's menu key for what has the focus. Every menu has one short shape, and every row wears one of Graphite's drawn glyphs:

- **At the top, the thing itself**: its kind's glyph, its name and what it is (a passage and its page, a file, two files, a record, a job and its state, an event, a network connection).
- **Up to four usual actions** for that kind of thing: on a file Open, Ask Stacy about this, Rename, Move to Trash; on selected words Bold, Italic, Move to notes, Ask; on a sheet in the Field Open, What can be done, Doubt it, Ask; on a job Inspect output, Pause or Resume (whichever applies), Stop, Show in Jobs. Only rows that can act now are here; one that cannot is under More, dim, and its tooltip says why.
- **Then ›** when the thing has a line, or **Start from ›** on an empty place (one of your kept chains or words, or a file in Files).
- **More ›** for everything else, in named groups: Open and show, Change it, Look into it, Send and keep, Edit and copy, This working copy, Make and arrange, As a line. Nothing was taken away to make the menu short.

**Then ›, the line panel.** It shows the thing's line on its royal-purple slab, how many rows it gives, the first few, and how many steps the line has left. It reads once when it opens; after that every choice is counted from that one read, so you see what a step would give before you take it:

- **Keep rows where ›** a column › a value. Each value says how many rows it keeps (is mA, 2 rows; at least 110, 3 rows). Another value… puts the line so far in the writing line for you to finish.
- **Sort by ›**, **Count**, **Count by ›** a column, **First ›** 5, 10, 20… rows, **Read it as ›** (rows, headings, layers…), and **Back a step** (Backspace does the same).
- **Then**: Show it (runs it; the answer is in the working area), Put it in the writing line, Copy the line, Copy the rows (as CSV). A line gives at most 200 rows; above that Show it says so and First › offers 200.

**Stop asks first.** Stop on a job or on Agenda work opens a small screen that says why it asks (what it stops cannot be put back), with Stop it and Leave it. Nothing is stopped before Stop it, and the job is read again at that moment.

Deeper screens open beside the menu and replace each other in place, with Back at their top, so there are never more than two popups and no screen scrolls.

Everything goes through the same checks as elsewhere. A change is refused, with nothing done, if the page, file or job moved on since you right-clicked it. The result shows where it belongs: the page, the Compare room, the working area, the job's row. Run and Inspect output say "Not run" with the reason when the line is refused; they never say they ran. Text fields keep their own menu (cut, copy, paste).

## Home is the Finder

With no project attached and nothing open, the centre is a Finder window inside the same frame. The left pane is its sidebar: choose Today for what arrived, what waits for you, where you left off and Graphite; choose a storage mount under Machine, the Files row or a project's folder and the centre lists that folder, or open Places ▾ in the Finder's own bar (Today, Files, Ingress, Egress, Workspace, Program, each disk). With a project attached the same Finder is Home. Three views (Icons, List with Name · Date Modified · Size · Kind, Columns that open to the right) share one listing; a preview pane shows the chosen file's kind, size, dates, an image or the first lines of a text; the path bar at the bottom is clickable; the status line says how many items and how much space is free, observed on this computer. Enter opens (a text in the editor, anything else in the viewer), Backspace goes up, Space shows or hides the preview, Alt Left and Right go back and forward, typing selects by name. The Finder looks and opens; it never creates, renames, moves or deletes: those stay the Files room's own operations. Folders with more than 500 entries say so and offer up to 2,000.

## Ingress and Egress

Files come in through Ingress (`~/Concern/Office/Ingress` for the Office): drop them there or on the Office, and Today, the Library's ARRIVE section and the Office count them as new until you receive them. Files leave from Egress (`Files/Egress`): exports of documents, reviewed Office output copies, result pills and manufacturing or sharing copies with their SHA256SUMS start or land there. The names are the owner's; the older folders Arrived (and the 4.1 Inbox) and Exports are moved to the new names once, without overwriting anything, the first time Graphite runs on a workspace. Operation names such as files.export and receiving.* are unchanged.

## Writing a document with Graphite

The programs list → Documents opens a page. Write; it saves itself a moment after you pause (and before anything else touches it). Select words, go to the writing line, in Assignment, and ask in plain words: `make these words bold`, `italic`, `underline`, `make it a heading`, `heading 2`, `body text`, `code`, `plain`, `replace fox with cat`. These are direct edits Graphite makes without a model; its answer names the change and the saved revision. With a model loaded, a request the rules do not know goes to the model, and the edit it proposes for the open page is applied at once: the changed words glow pencil-yellow for a moment, the face shows APPLIED ON THE PAGE with undo, and Ctrl Z takes it back. If the page changed while the model was thinking, nothing is applied and the card says why. Anything else the model proposes waits for your Run. Ctrl Z takes any change back, Stacy's included, and `undo` or `redo` typed to her does the same. Anything it does not recognise goes to the model when one is loaded; without one it says so. Reopen a page from the list on the left or from the cabinet's Documents folder; every page is a saved revision with its history. Export… writes Markdown, HTML or plain text to Egress (Files/Egress). Keys on the page: Ctrl B, Ctrl I, Ctrl U, Ctrl 1/2/3 headings, Ctrl 0 body, Ctrl ` code, Ctrl S save now.

## Giving Graphite an assignment

On a page with quantities, ask in the writing line, in Assignment: `add up the numbers on this page` (a verb such as add up, total, sum or count; a noun such as numbers, quantities or values; and a place such as on this page). Graphite reads the page, finds the quantities exactly where you wrote them, sums them with a unit check, writes the total under your words and binds it to those numbers. The Work block at the top of Activity says what it is working on, doing now, found, needs from you, and where to inspect; Stop, Pause and Resume are words there, and Inspect opens the investigation with every recorded step. Units that differ become a question and the assignment waits for you. Change one of the numbers and the page shows a quiet line, a result on this page is stale · recheck; one word rechecks. Closing Graphite while it works: with the Graphite service on (System menu ▸ Graphite services ▸ On), the assignment continues in the service and Today says what was done while Graphite was closed; opening Graphite takes the work back. Settings ▸ Assistant ▸ Assignments ▸ Continue assignments while Graphite is closed turns this off, and then closing pauses it and Today offers to resume. Stop all jobs stops it on both sides. A request it has no procedure for becomes a waiting assignment that says so. Related, beneath the Work block, lists your own earlier records that share the page's words; dismiss what does not help. Assignments in the programs list (the cat) opens the room with all of them.

With nothing open, ask for files: `find files about pellets` or `what files do we have about the crate`. Graphite looks through Files and Ingress (Ingress by name only), reads the first lines of up to four of the best matches and writes a findings page; inspect opens it. Requests about the open page (`search this document for …`) go to the model instead.

## Writing elsewhere

Write directly into yellow passages: ideas, project intent, document titles, settings values, the return thread, the writing line. The X mark in the margin shows the line you are writing on; it is a setting (Settings → Workspace → Appearance → Writing marker) and goes still when Reduce motion is on. Owner prose uses the prose font and size from Settings → Reading; code keeps the code font.

## The local model

The programs list → Local model opens the Brain room: drop a GGUF file on it or choose one, and the pinned llama.cpp runtime (CPU build, included under runtimes/) serves it on this computer. No model file is included in the release; the room says which file is selected, qualified, running or stopped. Graphite's direct document edits, the machine view, the cabinet and every workspace work without a model.

Which file to fetch (both Apache-2.0, from the Qwen organisation's GGUF repositories on the public hub; both were run through Graphite's real operations in the build container, see docs/MODEL_TRIAL_01.md):

- Default: `qwen2.5-1.5b-instruct-q4_k_m.gguf` (1,117,320,736 bytes, SHA-256 6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e). It proposed the right document edit and the right plain next step.
- Minimum: `qwen2.5-0.5b-instruct-q4_k_m.gguf` (491,400,032 bytes, SHA-256 74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db). It answers in a sentence and loads in under a second, but decides poorly; the program stays useful with it because the loop's rules come first.

Place the file anywhere on the computer, register it in the Brain room (Add a model), then Use it; the room reports the qualification. Check the hash before trusting a copy: `sha256sum <file>`.

## Finding and checking

- Explore suggests capabilities for the selected record and opens the Explore room for a broad search: the programs list's Explore the workshop, Tools → Explore capabilities…, Explore in Activity for the selected record, or the right-click on a file or record.
- Settings → Workspace → Hardware category views remembers how each hardware pane lists its files.
- Run `python3 tools/check_release.py` from the program folder to verify the payload against `MANIFEST.json`, the seed and the live program against the recorded Graphite 0.1 registry (`docs/GRAPHITE_0.1_REGISTRY.json`: operations, job tools, settings, adapters); any difference is listed in words. `--self-test` adds the focused test modules one by one and `--ui` the offscreen window checks. A passing check is integrity, not readiness.

## The game behind the mark

Game, the last row of Programs, opens STRUTHIO ARCADE 1.9.0 in its own window, in desk mode: keyboard only (no touch controls are shown), no title screen, and a new run waits on the pause screen at tick zero with the keys listed. ← → (or A D) flap left and right, ↑ W or Space flap hard, ↓ (S) darts, Esc pauses; a flap key starts the run and resumes it. Game over offers NEW RUN only (Space or Enter), paused at tick zero again. Desk runs save to their own run slots, apart from the web game's. The game window keeps its own storage on this computer, separate from the phone game (which stays as it is and keeps its saves and high scores on the phone), and Graphite serves the game at the same local address each time (127.0.0.1:47913), so the window's saved runs and high scores last from one session to the next. If something else holds that address, Graphite uses a free one for that session, and that session's saves stay with it.

## What is not yet in place

More assignments (an ARC calculation that follows a changed condition, datasheet to spreadsheet), Python helpers Graphite writes itself, real native application handover, and model replacement with rollback are the next passes; owner-host acceptance of the dedicated session, real models and native tools needs the ThinkPad.
