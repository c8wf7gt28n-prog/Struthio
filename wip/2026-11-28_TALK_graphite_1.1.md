# Graphite 1.1, a twenty-minute talk

*28 November 2026, for Graphite 1.1 as released that morning, before your weekly cut-off. Everything here was built
and seen working on the build machine, offscreen or on a virtual screen, with invented files. None of it has run on
your ThinkPad yet.*

---

## 0:00 · Why 1.1 exists

After 1.0 you said: *"this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know I
can only get what I want in Debian so I have to switch."* Then: *"Think the functionality of windows, with the graceful
class of Apple, and the freedom power of Linux."* And: *"Kasandra is the super power of this project."*

1.0 was a living desktop with a ghost in the shell. It was clever, but it asked you to learn its ways. 1.1 turns that
around. Graphite now starts from where your hands already go. The things a Windows and DOS person reaches for without
thinking (a bar at the bottom, a Start button, File and Edit menus, Ctrl+C, `dir`) are there and work. Each is done
gracefully, and each opens onto the whole Linux box underneath.

Three rules guided every choice:

- **Familiar first.** If your hand goes there in Windows, something is there.
- **One place for each thing.** Nothing lives in two places, so the screen stays quiet.
- **Nothing hidden.** Everything you can press is also a line you can read, copy and run yourself.

And one sentence from 1.0 has not moved an inch: **the model proposes; the desk disposes.** Kas got a great deal more
powerful in 1.1. Her rules did not loosen at all.

## 1:30 · Installing it like Debian software

The first thing 1.1 changed is invisible but matters most for a distribution: **Graphite is now Debian software.**

It comes as four packages in a folder repository on your USB stick:

- **graphite** is the program. It lives in `/usr/lib/graphite` and runs on Debian's own PySide6.
- **graphite-llama-runtime** is the llama.cpp that runs Kas's model.
- **graphite-session** holds the login session and the small commands: `graphite-startx`, `graphite-session` and
  `graphite-do`.
- **graphite-desktop** is optional. It brings a LightDM login screen set to Graphite.

Installing comes in two stages, on purpose. Stage one changes nothing about how the machine boots. You run `JOIN.sh` as
yourself; it checks every file by its checksum and puts the large ones back together. Then, as root, you run
`install.sh --check` to look, and `install.sh` to install. Log in on the console and type `graphite-startx`, as before.
Stage two, the graphical login, is separate and comes only after stage one works, because a login screen changes how
the computer boots. Two commands undo it, and START_HERE says what to do if it doesn't come up.

Your 1.0 stays exactly where it is. The new Graphite opens the same workspace with the same settings. `apt remove
graphite` takes the program away and never touches your files.

## 3:30 · Your hands: the keys and the DOS words

Preview 1 also gave your hands back their habits.

**In Files**, the Windows keys work the way you expect:

- **Copying and moving:** Ctrl+C, Ctrl+X and Ctrl+V copy and move files, and one Ctrl+Z undoes the whole paste.
- **Rename and delete:** F2 renames. Delete sends to the bin. Shift+Delete asks first, then deletes for good.
- **Getting around:** Enter opens and Alt+Enter shows Properties. F5 reads the folder again, and Backspace goes back.

**Above every app** in the Graphite session:

- **The Windows key** opens Start. Win+E opens Files, Win+D brings Graphite forward, and Win+L locks.
- **Switching:** Alt+Tab and Alt+F4 work.
- **The rest:** Ctrl+Alt+Del shows what is running, and PrintScreen saves a picture into Pictures/Screenshots.

**Menus show their keys again.** In 1.0 you'd asked for none to be printed. For someone switching, the menus are where
keys are learned, so they're back, and one setting turns them off. That's on your list of reversals to strike, which
I'll come back to.

**And the Terminal speaks DOS.** Type `dir`, `cd..`, `copy`, `move`, `del`, `ren`, `md`, `type`, `cls` or `ipconfig`
and it works. Each time, it shows the Debian command it actually ran, so the bridge teaches itself away. `del` sends to
the bin, with Undo. `copy` and `move` never write over a file without `/y`. `format` and `chkdsk` are explained and
never run.

## 6:00 · The bar

Now the screen. 1.1's biggest visible change is **one bar along the bottom of the screen, above every app.** It
replaces 1.0's slim dock at the top. From the left:

- **Start.** Press the Windows key and Start rises from the corner. It shows your apps by kind, read from the apps' own
  desktop entries, so whatever Debian installs appears. Your recent files are beside them, and Lock, Suspend, Log out,
  Restart and Shut down along the foot. Leaving names any app still open and asks it to close politely. It never kills
  one. Start opens when you let go of the Windows key, as in Windows. Esc closes it.
- **The line.** "Search or do." It is the one place you type to find or do anything:
  - Type `calc` and it finds LibreOffice Calc; type a file's name and it finds the file.
  - Type `control panel` and it takes you to the settings.
  - Type `12*7` and it says 84, exactly. Graphite's maths core never rounds behind your back.
  - Type `dir` and it shows the Debian command beside the DOS one.
  - "Ask Kasandra" is always offered, at the foot of the list.
  - Every row says what Enter will do: Open, Run, Calculate or Ask Kasandra. You never press Enter wondering.
- **Your open windows.** Graphite comes first, then each app. One press brings any of them forward.
- **Kas.** I'll come to her in a moment.
- **The tray.** Network, sound and battery, each a small picture and a word. Press one and its own panel rises above the
  bar with the Machine page's real actions: join a network, change the volume, see the battery's time left. At the
  smaller screen size, the tray shows its pictures alone and keeps the words in the tip, as Windows does.
- **The clock.** Press it for the month.

Graphite itself now opens maximised above the bar, not full screen, so the bar is always there. That's another reversal
for your list.

## 8:30 · Files becomes an Explorer

The left side used to begin at "This computer /", the whole Linux tree. In 1.0 your first sight was system folders. 1.1
starts with **Quick access**: Home, Desktop, Documents, Downloads, Pictures and Music. Below those comes the Desk, the
drawers of records, and then **This computer**, with **System (C:)** one press down, so the root is there when you
want it and out of the way when you don't.

A folder opens in the centre in one of three views, chosen on the centre bar:

- **List** is a details view: Name, Modified, Type, Size and Links. Press a column to sort. Downloads sorted by size is
  one press.
- **Icons** shows thumbnails of your pictures. They are made in the background so the window never waits, and kept in
  a cache.
- **Board** is 1.0's living desktop: the selected thing in the middle, its neighbours around it, recorded links solid
  and guesses dashed. It was not redrawn. It is the same board, now one press away from any folder.

The address field takes a typed path: `~/Downloads`, `/etc`, even `C:\`.

The bin is called **Recycle Bin** on a new install. Your profile has used 1.0, so it keeps the word **DELETE**. One
setting changes it.

## 10:00 · The menus, and the details pane

At the top of Graphite's window, the head is now 32 pixels with six menus a Windows hand knows: **File, Edit, View, Go,
Tools, Help.** Nothing was taken away. Every action of 1.0's eight menus is still there:

- **The straight renames:** Work became File, Revise became Edit and Guide became Help.
- **Arrange was split:** its places went to Go, and its layout and look went to View.
- **Into Tools:** Commands and Rules. Kas's own rules keep a row of their own there.

The release notes have the full table.

**View ▸ Details pane**, or **Alt+P** as in Windows, opens a pane at the right of the centre for whatever is selected,
in any view. It shows a preview, the facts, and its connections: the board's neighbours as plain rows. It's off at
every start.

All told, the window's own frame and menus now take 115 pixels of height instead of 187. That's more room for your work.

## 11:30 · Kas on the bar

Now the reason to use it. **Kasandra, Kas.** There is no picture of her; there hasn't been since you asked.

On the bar sit her name, her state word and its shape, and **HALT beside her name**:

- QUIET is a ring.
- WORKING is a filled dot.
- NEEDS YOUR WORD is a diamond.
- STOPPED and HELD are two bars.
- DONE is a tick.

Colour is only ever the third cue, after the word and the shape.

HALT is 1.0's HALT, moved. It stops all of her work and nothing else: never your desktop, never your apps. RESUME
restarts nothing by itself. It sits on the bar because an app in front of Graphite used to hide it, and the bar is above
everything.

**Press her name and her panel slides in from the right edge, over whatever app you're in.** It holds her whole column:
what waits for you first, then her work, her findings, her next steps, and her line. Esc closes it. Inside Graphite's
own window she stays docked at the right, as you're used to.

**When something needs you and her panel is closed, a card rises from her chip.** It might say "Authorise step 3" or
"Grant this for this assignment", with the same single press as in her panel. It never takes the keys from the app
you're typing in.

## 13:00 · Her voice

You said Kas is like Kate Libby: sharp, sure, dry, and never bluffing. 1.1 rewrote her lines in that voice.

- **Short.** No sentence of hers runs past twenty words. A sweep checks all 634 of her lines, and there are no problems.
- **Never selling.** She never says "trust me" or "obviously".
- **Never claiming more than the records hold.** "Not verified. Here is what I checked." is a fixed line. She says
  "Done, verified" only where the records prove it.
- **Plain when it matters.** Refusals, losses and permissions are said plainly, with no jokes. When the desk refuses
  something, she tells you in plain words what to do, and the desk's own words go to Log.

Ask her the paper's question on Rail Demo: *does the 12 V rail meet its limits?* She goes finding by finding, each with
its shape. Startup inside the Rev B limit is refuted. Settled power inside the limit is supported. Why startup takes
longer than 40 ms is still open. Then: **"Not proven sufficient."** The model was never asked for that verdict. It comes
from what the records hold.

## 14:30 · Her recipes: the whole box, safely

This is where Kas starts to reach the whole computer, and it came in preview 3.

She now has **forty recipes**, for the everyday things a Windows person asks of a Linux box:

- **Finding things:** find big files, see what takes the space, find duplicates, what changed since yesterday, find a
  file by its words.
- **Pictures and PDFs:** convert and resize pictures, merge and split PDFs.
- **Folders and the bin:** zip and unzip, back up a folder to a drive, rename many, sort Downloads by kind, empty the
  bin.
- **The machine:** what uses memory, what uses the processor, is the system up to date, disk health, which apps start
  with the session.

Each recipe is a small readable file. You can write your own in `~/.config/graphite/recipes/`, and a broken one is
refused with the reason.

Every recipe follows the same discipline:

1. **Reads run at once:** what's using my disk, how much memory is free.
2. **A change shows its dry run first.** Ask her to *sort Downloads by kind* and she lists exactly which file goes where:
   the chart viewer to Installers, the timetable to Documents, the photo to Pictures. Then she waits: **"Run it (your
   press)"** or **"Not now."**
3. **It runs only on your press, and only if nothing changed since you saw it.** If a file moved in between, it plans
   again and shows you.
4. **It's checked afterwards.** "✓ Done and verified: 8 files read back at the new place, the same file, the old place
   empty." **Undo** puts every file back.
5. **What can't be undone says so before the press.** Emptying the bin asks twice.

With no model loaded, her dictionary picks the recipe from your words and asks one question if something's missing.
With a model, the model picks a recipe *by its number* and may fill its blanks only with words you actually used. Pick,
never write: that's the 1.0 rule carried into the box.

And Kas never runs a change as her own step. No standing grant runs a recipe change. You press, every time.

## 16:30 · Her command tool, and what comes in 1.1.1

The last piece in 1.1 is **her command tool**. Type `run: df -h` in her line or the bar's line. Any command is taken as
a program and its words, never a shell string. About 150 programs are known, and each form is classed: it reads,
changes, destroys, needs root, or reaches the network.

- **Reads run at once inside a seal:** no network, only the named paths readable, nothing of yours writable. The output
  is shown as data, never taken as instructions.
- **A change waits.** "This will make the folder Rev 2. The command: mkdir …" Then your press, a check on the disk
  afterwards, and Undo. `rm` goes to the Recycle Bin.
- **Anything she can't classify is refused.** Pipes, `;`, `&&`, redirection, unknown programs and flags are refused in
  plain words, with the exact line shown: "A pipe: I run one program with its words, never a shell."
- **Root is refused too.** In 1.1 she makes no system changes, and she says so.

Four pieces were building when your week's limit came near. I paused them so 1.1 could ship whole, and their work is
saved. They come in **1.1.1**:

- **The system door:** software, services, the clock and users, through Debian's own password prompt, with you present,
  one fixed action per prompt.
- **A real terminal in the drop-down.** Today vim, top and sudo's password prompt don't work in it; use the text console
  (Ctrl+Alt+F2) for those.
- **Grounding:** an index of your machine's manual pages, so every option she proposes is checked and quoted, and
  "teach me" answers from the page.
- **A quieter bar,** from your idea about the tray: network, sound and battery as one Quick Settings button, so your
  window buttons get the room.

After that come printers, Bluetooth and date and time, a Task Manager, a live image, a security review of every door Kas
has, and the licences.

## 18:00 · Your reversals, and what's honest

1.1 goes against some things you decided earlier. Each is the builder's call for a distribution, and each is yours to
strike: say "strike N" and it goes back.

1. Keys shown in menus again.
2. A graphical login as well as the console.
3. HALT on the bar beside Kas.
4. Start at the lower left on the Windows key. The word is still "Apps", never "Programs".
5. Quick access first, the root one press down.
6. "Recycle Bin" on new installs, while your profile keeps DELETE.
7. File, Edit, View, Go, Tools and Help as the menu names.
8. Kas making system changes through the system's own prompt, with you there. That one arrives in 1.1.1.
9. Graphite maximised above the bar, not full screen.
10. No foot in the window: the bar's line, the drop-down Terminal, Log under View, the meters in the tray.

What did not move: no picture of Kas; Apps, never Programs; Day as the launch look; every state a word and a shape; her
authority rules.

And the honest part. Nothing has run on your ThinkPad. The build machine has no screen, so the window was drawn
offscreen, and the bar and Start ran on a virtual screen under a stand-in window manager:

- **Not tried under real Fluxbox:** whether apps really stay clear of the bar, and Start's key timing.
- **Not tried at all:** the login screen.
- **Not tried with a real model:** her new voice and her recipes.
- **The test suites:** the quick tier is at zero failing in Day and Graphite; the full tier has two named failures
  left. The release check passed on the exact commit the kit was cut from.

## 19:00 · Your evening

Graphite 1.1 is in your hands as one complete kit. Copy every file into one folder, run `JOIN.sh`, then `install.sh` as
root. Then:

1. Open LibreOffice from Start with the Windows key. Is its window above the bar?
2. Type `calc`, `12*7`, `dir`, `control panel` and `free space` in the bar's line.
3. Open Downloads in the Explorer, sort by size, try Icons in Pictures, and press Alt+P.
4. Press Win+` for the Terminal, type `dir`, and press Win+` again.
5. Ask Kas to sort your downloads by kind. Press Run, then Undo. Then ask her `run: df -h`.
6. From LibreOffice, press Win+K, then Pause. RESUME is on the bar.

Whatever differs from the page is a result. Send it, with a photo if it's on the screen.

That's Graphite 1.1: a computer your Windows hands already know, opening onto a whole Linux box, with Kas at your
side who can now reach most of it. She shows you exactly what she'd do and waits for your press. She checks before she
says it's done.

The model proposes. The desk disposes. And you keep the authority.
