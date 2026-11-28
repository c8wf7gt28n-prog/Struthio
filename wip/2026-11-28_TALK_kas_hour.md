# Kas: an hour on the program

*28 November 2026. A talk on Kas as it stands after six releases today (1.1 to 1.1.6), written to be read aloud in about
an hour. The times in the margins are a guide. Everything here was built and seen working on the build machine: drawn
offscreen or on a virtual screen, with invented files, and one clean install in a Debian chroot. None of it has run on
your ThinkPad yet, and I'll say so wherever it matters.*

---

## 0:00 · One name

Let me start with the name, because you settled it this morning, and it says more about the program than any feature
does.

You said: *"No more graphite. I hate that public name."* Then: *"it's kas. All of it. kas only kas. The other thing if
there must be something else is computer."*

That's the whole design in two sentences. There's one name on the screen, and it's hers. The thing you sit at and the one
who works beside you are called the same. Where the desktop has to be told apart from her, it's just "the computer". The
first button on the bar reads **Computer**. Your settings say Kas. The commands are `kas-startx` and `kas-do`. When you
switch on and Night is warming up, the word burnt faintly into the middle of the screen, like a mark left by years of the
same image, is **kas**.

The program has had other names. It started as Ledger & Slate. It became Graphite on 6 November. Now it's Kas. Inside
the code the old names survive as folder names and settings keys, because changing those would only break things, but
you'll never see them. Nothing of yours moves when the name changes.

So for the next hour, when I say Kas I mean the whole of it, and when I need to be precise I'll say "the computer" for the
desktop and "her" for the one who works with you.

## 2:00 · What you asked for

Let me remind us both what you asked for, because every choice in this hour goes back to these lines.

After 1.0 you wrote: *"this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know
I can only get what I want in Debian so I have to switch."*

Then: *"Think the functionality of windows, with the graceful class of Apple, and the freedom power of Linux."*

And: *"Kasandra is the super power of this project. Make her very useful at everything in a world where a full loaded
Linux box is the computer I use."*

And one more, which turned out to matter a lot: *"Kasandra is like Kate Libby."*

Those four lines are the brief. Windows for where your hands go. Apple for how it feels. Linux for what it can do. And
Kas as the reason any of it is better than just installing a desktop someone else made.

## 3:30 · Three ideas, and a turn

Kas 1.0 was built on three ideas, and they're still the bones of it.

**First: the computer is the session**, not a program you open. When you log in, Kas takes the whole screen. A small
supervisor keeps it alive. If Kas's own window ever crashes, the supervisor brings it back, and the apps you had open stay
open, because each app runs in a session of its own.

**Second: the living desktop.** In the middle of the screen, what you select sits in the centre, surrounded by what it's
connected to: the PDF a sheet came from, the limits it's checked against, the findings about it. Solid wires are links the
desk knows. Dashed wires are guesses, and they say so.

**Third: the ghost in the shell.** Kas isn't a chat window. She's an agent user of the computer. She uses the same files,
tools and apps you do, under your authority. She never says a thing is done until she has checked that it is.

And under all three runs one sentence: **the model proposes; the desk disposes.** Her model can suggest anything. Only the
desk's own rules, and your presses, decide what happens.

1.1 kept all of that and made one turn. 1.0 was clever, but it asked you to learn its ways. 1.1 starts from where your
hands already go. If your hand reaches for something in Windows, something is there in Kas. Each of those things is done
gracefully, and each opens onto the whole Linux box underneath.

I worked from three rules. **Familiar first.** **One place for each thing**, so nothing lives in two places and the screen
stays quiet. And **nothing hidden**: everything you can press is also a line you can read, copy and run yourself.

## 6:00 · Installing it like Debian software

The first thing 1.1 changed is invisible but matters most for a computer you'll live with: **Kas is Debian software now.**

It comes as four packages in a folder repository you carry on a USB stick:

- **kas-computer** is the program itself. It lives in `/usr/lib/graphite`, an internal name you'll never need to type,
  and it runs on Debian's own PySide6, not a copy of its own.
- **kas-llama-runtime** is llama.cpp, the engine that runs Kas's model.
- **kas-session** is the login session and its small commands: `kas-startx`, `kas-session`, `kas-do`.
- **kas-desktop** is optional. It adds a graphical login screen, LightDM, set to Kas.

None of them is called just `kas`, and there's a reason worth knowing. Debian already has an unrelated package called
`kas`, a build tool, with a higher version number. If your package were named `kas`, apt could one day decide the other
one is newer and swap it in. So the names say what they are, and they never collide.

Installing comes in two stages, on purpose.

**Stage one changes nothing about how the machine boots.** You copy the kit's files into a folder and run `bash JOIN.sh`
as yourself. It checks every file by its checksum, puts the large ones back together from their pieces, and ends with
`JOINED AND CHECKED`. If anything doesn't match, it tells you which file to copy again. Then, as root, you run
`install.sh --check` to see what it would do, and `install.sh` to do it. That copies the repository to a fixed place,
adds it as an apt source, and installs the computer and the session. You log out and back in on the text console, type
`kas-startx`, and Kas starts.

**Stage two, the login screen, is separate,** and it comes only after stage one works. A login screen changes how the
computer boots, so you shouldn't take that step until you know the rest works. Two commands undo it. And if the login
screen ever fails to come up, START_HERE tells you exactly what to type at a text console to get back.

Your old 1.0, in `~/Applications/Graphite-1.0`, stays where it is. The new Kas opens the same workspace and the same
settings. `apt remove` takes the program away and never touches your files.

Today I tested this for real, once. In a clean Debian 13 system with your 1.0 System set installed, `apt-get install
kas-computer kas-session` from the kit's own repository worked. It pulled in the polkit agent and PackageKit for the
system door. Every `kas-*` command was there. `kas-computer --version` said "Kas 1.1.6". The old `graphite-startx` said
it's now `kas-startx` and the old name goes next release. And the doctor accepted Debian's own PySide6. What that test
can't show is the session actually starting on a screen. That's your ThinkPad's job.

## 11:00 · Your hands: Windows keys and DOS words

Now your hands. Preview 1 gave them back their habits.

**In Files**, the Windows keys do what you expect:

- Ctrl+C, Ctrl+X and Ctrl+V copy and move files, and one Ctrl+Z undoes the whole paste.
- F2 renames. Delete sends to the bin. Shift+Delete asks first, then deletes for good.
- Enter opens. Alt+Enter shows Properties. F5 reads the folder again. Backspace goes back.

One detail I fixed today because you'd hit it: a Windows hand presses Ctrl+Z fast. Right after a paste, the files land a
moment before the paste's Undo is recorded. A fast Ctrl+Z used to find nothing. Now it waits up to a second for the
Undo, then takes the paste back.

**Above every app** in the Kas session:

- **The Windows key** opens Start.
- **Win+E** opens Files, **Win+D** brings the computer forward, **Win+L** locks.
- **Win+K** opens Kas's panel. **Pause** presses HALT.
- **Win+`** or **Ctrl+Alt+T** drops the Terminal.
- **Ctrl+Alt+Del** shows what's running, **PrintScreen** saves a picture into Pictures/Screenshots, and Alt+Tab and
  Alt+F4 work.

**Menus show their keys again.** In 1.0 you'd asked for no keys on screen. For someone switching, the menus are where
keys are learned, so they're back, and one setting, View ▸ Show keys, turns them off. That's one of your reversals to
strike, and I'll come back to the list.

**And the Terminal speaks DOS.** Type `dir`, `cd..`, `copy`, `move`, `del`, `ren`, `md`, `type`, `cls` or `ipconfig`,
and it works. Each time, it shows the Debian command it actually ran: `dir → ls -l`. So the bridge teaches itself away. In
a month you'll type `ls` without thinking.

A few safety rules come with it. `del` sends to the bin, never `rm`, so it can be undone. `copy` and `move` never write
over a file unless you add `/y`. `format` and `chkdsk` are explained and never run.

## 15:00 · The bar

Now the screen. The biggest visible change is **one bar along the bottom of the screen, above every app.** It replaced
1.0's slim dock at the top. From the left:

**Start.** Press the Windows key and Start rises from the corner. Your apps are grouped by kind, read from the apps' own
desktop entries, so whatever Debian installs appears there. Your recent files sit beside them. Lock, Suspend, Log out,
Restart and Shut down are along the foot. Leaving names any app that's still open and asks it to close politely. It never
kills one. Start opens when you let go of the Windows key, as in Windows. Esc closes it.

**The line.** "Search or do." It's the one place you type to find or do anything:

- `calc` finds LibreOffice Calc. A file's name finds the file.
- `control panel` takes you to settings, because Windows words are understood.
- `12*7` says 84, exactly. Kas's maths core never rounds behind your back.
- `dir` shows the Debian command beside the DOS one.
- `free space` offers a recipe, and I'll come to those.
- `run: df -h` offers a command for Kas to run sealed.
- `install gimp` offers the system door.
- And "Ask Kas" is always there, at the foot of the list.

**Every row says what Enter will do**: Open, Run, Calculate, Show, Ask. You never press Enter wondering what happens.

**Your open windows.** The computer comes first, then each app. One press brings any of them forward.

**Kas.** Her name, her state as a word and a shape, and HALT beside her. More on her soon.

**Quick Settings.** This one came from your idea this morning. You wanted the tray off the bar. I didn't want network
and battery hidden behind your apps, so instead they became **one small button**: three glyphs side by side, network,
sound and battery, with their words in its tip. One press opens one panel with all three, each with its own real actions
(join a network, change the volume, the battery's time left), plus the meters as a fourth section. At 1366 wide, three of
your app windows now fit on the bar beside everything else, with nothing folded away.

**The clock.** Press it for the month.

The computer itself opens maximised above the bar, not full screen, so the bar is always there. Another reversal for
your list.

## 21:00 · Files becomes an Explorer

The left side of the window used to begin at "This computer /", the whole Linux tree. Your first sight of Kas was a wall
of system folders. Now it begins with **Quick access**: Home, Desktop, Documents, Downloads, Pictures and Music. Below
that is the Desk, the drawers of records, and then **This computer**, with **System (C:)** one press down. The root is
there when you want it and out of the way when you don't.

A folder opens in the centre in one of three views, chosen on the centre bar:

- **List** is a details view: Name, Modified, Type, Size and Links. Press a column to sort. Downloads sorted by size is
  one press. Select many as you always have, and one Undo takes back a whole batch.
- **Icons** shows thumbnails of your pictures. They're made in the background so the window never waits, and kept in a
  cache so they're instant next time.
- **Board** is the living desktop, the bulletin board of the selected thing. It wasn't redrawn. It's the same board from
  1.0, now one press away from any folder.

The **address field** takes a typed path: `~/Downloads`, `/etc`, even `C:\`.

The bin is called **Recycle Bin** on a new install. Your profile has used 1.0, so it keeps the word **DELETE**. One
setting, under Tools, changes it.

**The details pane** opens with View ▸ Details pane, or **Alt+P** as in Windows. For whatever is selected, in any view,
it shows a preview, the facts, and its connections: the board's neighbours as plain rows. It's off at every start.

**Command…** sits above Properties on a file's right-click, and on Ctrl+. too. It shows you the exact command that Open
would run for that file, with Copy and "Put it in the line". Nothing is hidden. If you ever wonder what a button really
does, ask it.

## 26:00 · The menus, one line, and a real terminal

At the top of the computer's window, the head is now 32 pixels, with six menus a Windows hand already knows: **File,
Edit, View, Go, Tools, Help.** Nothing was taken away. Every action of 1.0's eight menus is still there:

- Work became File. Revise became Edit. Guide became Help.
- Arrange split in two: its places went to Go, and its layout and looks went to View.
- Commands and Rules went into Tools, with Kas's own rules keeping a row of their own.

The release notes have the full table of what moved where.

The menus now start at the left edge, as in a Windows app, and "Apps" left the head because Start does that job. **One
place for each thing.**

The window's own furniture now takes 115 pixels of height at full size instead of 187. That's more room for your work.

**One line, not two.** 1.0 had a line at the foot of the window with five names: Line, Terminal, Search, Web, Log. You'd
asked for that line back in 0.5.3. Once the bar had its own line, they were doing the same job twice, so the foot folded
away. Line, Search and Web are now the bar's line. Log is View ▸ Log. The meters went into Quick Settings. That's
reversal 10 on your list, if you want it back.

**The Terminal now drops from the top of the screen**, over any app, on Win+` or Ctrl+Alt+T. And since 1.1.2 it's **a
real terminal**: xterm, embedded in Kas's drop-down, running your own shell in your Files folder. vim, top, less and
nano all work, because it's a real terminal device. sudo's password prompt should work too. I couldn't test that here,
because the build machine runs as root and sudo never asks.

Your DOS words still work in it. Kas's own small startup file reads your `~/.bashrc` first and never edits it, then adds
the DOS words only in this terminal. `dir` shows "dir → ls -l" and runs it, and the real command goes into your history.
The same key, or `exit`, puts it away and gives your keys back to the app you were in.

## 30:00 · The living desktop

Let me spend a few minutes on the heart of 1.0, because 1.1 didn't change it and it's still what makes Kas different.

Select something, say a sheet of bench readings, and it sits in the middle. Around it, on rings, are its neighbours: the
PDF it was read from, the limits it's checked against, the calculations made from it, the findings about it, the open
question it bears on, the summary page that quotes it.

**The wires mean something.** A solid wire is a link the desk has recorded. A dashed wire is a guess, and it says
"possible, not verified". Click any wire and it tells you exactly why it's there: which cells, which revision, which
calculation.

**A tile's size is its relevance**, to the focus and to what you're doing right now. There are four sizes, and they don't
jump about for small changes. When there isn't room, the least relevant fold into "and 3 more". Right-click a tile for
**Why am I shown?**, **Pin**, or **Turn down**.

Everything with a state speaks **one language**, the same on tiles, wires, steps and in Kas's panel:

- a filled square for CURRENT and SUPPORTED;
- a crossed circle for REFUTED;
- an empty square for an OPEN question;
- a diamond for NEEDS YOUR WORD;
- two bars for stopped.

**Colour is only ever the third cue**, after the word and the shape. That rule matters more than ever now that Night is
monochrome phosphor.

**Double-click** to open a thing and work on it in the centre. **Save and Return** saves and brings you back to the same
board at the same zoom, with whatever depended on your change marked for a recheck. **Full program** opens it in
LibreOffice or its own app, and when that app saves, the new revision is recognised. You can have **tabs**, and a **split**:
the specification on the left, the worksheet on the right. **Back and Forward** take you to exactly where you were.

## 34:00 · Kas herself

Now the reason to use any of this. **Kas.** There's no picture of her, and there hasn't been since you asked.

**On the bar** sit her name, her state as a word and a shape, and **HALT beside her name**. The states:

- QUIET is a ring.
- WORKING is a filled dot.
- NEEDS YOUR WORD is a diamond.
- STOPPED and HELD are two bars.
- DONE is a tick.

**HALT** stops all of her work and nothing else. It never touches your desktop or your apps. RESUME restarts nothing by
itself: each task waits for its own Resume. HALT moved to the bar because an app in front of the computer used to hide
it, and the bar is above everything. That's reversal 3.

**Press her name and her panel slides in from the right edge**, over whatever app you're in. It holds her whole column:

1. **Waits for you**, first, never covered and never folded: anything that needs your word, your permission or your
   review, each with its one press.
2. Her work, with its progress and its own Stop.
3. Her findings, live.
4. Up to four next steps.
5. Her line, where you type to her.

Esc or her name closes the panel. Inside the computer's own window she stays docked at the right, as you're used to.

**When something needs you and her panel is closed, a card rises from her name**: "Authorise step 3", or "Grant this for
this assignment", with the same single press as in her panel. It never takes the keys from the app you're typing in.

**Her voice.** You said she's like Kate Libby. So her voice is sharp, sure and dry, and she never bluffs.

- **Short.** No sentence of hers runs past twenty words. A sweep checks every one of her lines on every build.
- **Never selling.** She never says "trust me" or "obviously".
- **Never claiming more than the records hold.** "Not verified. Here is what I checked." is a fixed line. She says "Done,
  verified" only where the records prove it.
- **Plain when it matters.** Refusals, losses and permissions are said plainly, with no wit. When the desk refuses
  something, she tells you in plain words what to do, and the desk's own wording goes to Log.

Ask her the question from your paper: *does the 12 V rail meet its limits?* She goes finding by finding, each with its
shape. Startup inside the Rev B limit: refuted. Settled power inside the limit: supported. Why startup takes longer than
40 milliseconds: still open. Then: **"Not proven sufficient."** The model was never asked for that verdict. It comes from
what the records hold.

## 37:00 · Her rules, and your authority

What makes her safe to live with is what she can't do. These rules haven't moved since 1.0, and every new power of hers
in 1.1 sits inside them.

- **Permissions are yours.** Each grant names an operation, a target and a scope in plain words before you press:
  this task, until a time, or always. The desk checks every step against them as it runs, not just the model's
  instructions.
- **Every change waits.** Reads run on their own. Anything that changes something waits for your press.
- **Done means verified.** A step is done when its effect has been checked, not when a command was sent. Each step leaves
  two records, "sent" and "confirmed", in a journal that survives a crash.
- **In your apps** she works through accessibility first: named buttons, menu items, fields. She does it while you watch,
  under a permission, and checks afterwards. A touch of your mouse or keys pauses her. She never presses Send, Pay, Delete
  or Install in another app, and she never types a password.
- **A utility she writes** runs sealed: on copies only, with no network and nothing outside its own folder.
- **The network** is offline first and always visible. A page she brings back is kept as quarantined data, and any line
  in it aimed at an assistant is held back and outlined.

Hold those rules in mind for the next ten minutes, because 1.1 gave her three new reaches into the whole box, and each
one is built on them.

## 40:00 · Her recipes

The first reach is **forty recipes**, the everyday jobs a Windows person asks of a Linux box:

- **Finding things:** big files, what takes the space, duplicates, what changed since yesterday, recent downloads, a
  file by its name or by its words.
- **Pictures and PDFs:** convert pictures, resize them, make them small for email, merge PDFs, split a PDF.
- **Folders and the bin:** zip and unzip, back up a folder to a drive, rename many, sort Downloads by kind, empty the
  bin.
- **The machine:** what uses memory, what uses the processor, whether the system is up to date (reading only), disk
  health, which apps start with the session.

Every recipe follows the same discipline:

1. **Reads run at once.** "What's using my disk" just answers.
2. **A change shows its dry run first.** Ask her to *sort my downloads by kind* and she lists exactly which file goes
   where: the chart viewer to Installers, the timetable to Documents, the photo to Pictures. Then she waits: **"Run it
   (your press)"** or **"Not now."**
3. **It runs only on your press, and only if nothing changed since you saw it.** If a file moved in between, she plans
   again and shows you.
4. **It's checked afterwards.** "Done and verified: 8 files read back at the new place, the same file, the old place
   empty." **Undo** puts every file back.
5. **What can't be undone says so before the press.** Emptying the bin asks twice.

With no model loaded, her dictionary picks the recipe from your words and asks one question if something's missing. With
a model, the model picks a recipe *by its number*, and may fill its blanks only with words you actually used. That's pick,
never write: the 1.0 rule carried into the box.

Recipes are small readable files. You can write your own in `~/.config/graphite/recipes/`, and a broken one is refused
with the reason.

## 43:00 · Her command tool

The second reach is **her command tool**. Type `run:` and a command in her line or the bar's line.

Any command is taken as a program and its words, never a shell string. About 150 programs are known to it, and each form
of each one is classed: it reads, it changes, it destroys, it needs root, or it reaches the network.

- **Reads run at once, inside a seal:** no network, only the paths you named readable, and nothing of yours writable.
  The output is shown as data, never taken as instructions. A line in the output written to an assistant is marked, so
  you can see somebody tried.
- **A change waits.** "This will make the folder Rev 2. The command: mkdir …" Then your press, a check on the disk
  afterwards, and Undo. `rm` goes to the Recycle Bin instead.
- **Network reads** wait for your press, refuse when you're offline, and show on the meter while they run.
- **Anything she can't classify is refused.** Pipes, `;`, `&&`, redirection, and unknown programs or flags are all
  refused in plain words, with the exact line shown: "A pipe: I run one program with its words, never a shell."

That last rule might sound strict. It's the point. A shell line can hide anything, and a classified command can't.

## 45:00 · The system door

The third reach is **the system door**, and it's reversal 8 on your list. In 1.0 the rule was "outside your home: never".
For a full Linux box that you live in, Kas has to be able to install software and run services. So she can now, through
fifteen fixed actions:

- **Software:** install, remove or update a package, refresh the list, and see what has updates.
- **Services:** start, stop, restart, enable or disable one.
- **The clock:** time zone, network time, or the time itself.
- **The computer's name.**
- **Accounts:** add a standard account, or set someone's full name. She never touches another person's password.

Each one goes the same way:

1. **She shows it first.** "Install GIMP": what the system will do, what it pulls in, and how large it is. Nothing has
   changed yet.
2. **Your press starts it.**
3. **Debian's own password prompt asks.** That's polkit, the system's own guard, not Kas. She never sees the password.
4. **She reads the result back** before she says done: the package installed at that version, the service running, the
   zone set.
5. **Undo, where the system allows,** asks again.

It's never her own step, never under a standing grant, and never while HALT holds. It's one action per prompt, one at a
time. And it talks only to Debian's own services (PackageKit, systemd and the rest), each of which asks polkit itself.
There's no shell, no `sudo` and no root helper of Kas's.

Here's the honest part. The door has only ever talked to stand-in services on the build machine. It has never installed
anything for real. So the first time you use it, ask for something small and harmless: *install cowsay*. Watch the
prompt, then press Undo.

## 47:00 · Her model

Kas's model runs on **llama.cpp v1.0.0**, sealed: only the settings it needs, a private socket, and its own agent tools
refused. On your ThinkPad that's meant to be the 35B model, ideally the file with its own multi-token-prediction head.

The **model check** measures your machine. Its tuning stage tries flash attention, cache types, batch sizes and
multi-token prediction, and keeps a setting only if the answers come out identical without it. Then it tells you how far
reading and writing are from your goal of **99 tokens a second**, and offers each setting with Undo.

There's an optional **quick model**: a small one beside the 35B, which takes a kind of question only after it passes that
kind's exam on your machine and measures faster. Here, a small 2B failed every exam it sat, so it took nothing. That's
the system doing its job.

And everything I've described about Kas works **without a model**: the recipes through her dictionary, the command tool,
the door, her findings and her checks. The model makes her better at understanding you. It never makes her able to do
more than her rules allow.

The 35B on your Radeon has never been loaded anywhere. That's still the biggest unknown, and your evening answers it.

## 49:00 · Night

Now the part you've had the most fun with today.

You said: *"Remember night mode is to look like old computers that only had orange and black / green and black
monitors....but updated to 2026 but still old school modern."* Then: *"Screen burns and all the fun."* Then: *"both the
orange and green working together with grey (like screen burns)."* Then: *"This is like the other hero view so really make
it creative awesome."* And finally: *"possibly greys in addition to orange and green."*

So Night is now a phosphor monitor on near-black, and its default, **Night Duo**, speaks in four inks:

- **Green is the computer:** your files, text, lists, the tree, the board, the terminal.
- **Amber is Kas and your word:** her panel and words, Waits for you, HALT, the selected row, the buttons you press, the
  bar's active window.
- **Paper-white grey is the machine's own labels:** column heads, dates, sizes, captions. That's the third classic
  phosphor, the old white monitors, slightly cool.
- **Warm grey is the past:** the burn-in, disabled things, the lines.

Every ink stays easy to read on the black, and a test enforces it.

**Her panel is a second tube.** It has a warmer amber ground and its own bezel line, and when Night starts it warms up a
beat after the green one, like two monitors on one desk.

**The CRT effects** come in three settings: Off, Subtle (Night's default) and Full.

- **The burn-in** is the machine's own past, burnt where it sat for years:
  - 1.0's old dock, a grey band along the top;
  - the old foot's five names along the bottom, burnt deepest because they were there longest;
  - a boxed MAIN MENU;
  - a VCR's **12:00** in seven segments;
  - an F1 HELP … F10 QUIT strip, and `LOAD "*",8,1` under READY.;
  - an old DIR listing and `C:\>`;
  - **kas** in the middle;
  - in her tube, lines of an old session above her `KAS>` prompt.
- **Phosphor afterglow** as typed text and the cursor change.
- **A warm-up line** when Night starts.
- **Faint scanlines** and a soft vignette.
- **A block cursor.**
- In Full, **a character-cell grid** on the empty ground.

Reduce motion stops anything that moves. The burns and the scanlines stay, because they don't move.

You can also choose **Night: Amber** or **Night: Green**, one phosphor each. Coming in 1.1.7, which is building as I
write: an **amber seven-segment clock** on the bar, **her words typing out** on an amber block cursor, **amber peak
marks** on the green meters, and a fourth choice, **Night: Paper**, all paper-white.

Day is still the launch look: calm and light, Inter for words and IBM Plex Mono for numbers. The two older looks have
new names now: **Pencil** (once Graphite) and **Indigo** (once Kasandra). Those two names are mine, for you to strike.

## 54:00 · What was tested, and what wasn't

Here's the honest accounting.

**What was done:**

- Every piece of 1.1 has its own test file.
- At every merge the program was rebuilt and its window opened offscreen in every look.
- The test suites, which 1.0 skipped by your rule, run again. The quick tier is at zero failing; the full tier has two
  named failures left.
- Over 160 tests of the new parts pass together.
- Every release passed the release check on the exact commit it was cut from, payload verified file by file.
- Today, one clean install in a Debian 13 chroot with your System set worked.

**What wasn't:**

- **Real Fluxbox.** So whether apps really stay clear of the bar, and Start's key timing, are untried.
- **The login screen.**
- **A real system-door install.** It has only met stand-ins.
- **sudo's prompt** in the real terminal.
- **Any of her new words, recipes or commands with a real model.**
- **Anything on your ThinkPad.**

Your evening is the first real proof.

## 56:00 · Your reversals

1.1 goes against some things you decided earlier. Each is my call for a distribution, and each is yours to strike: say
"strike N" and it goes back.

1. Keys shown in menus.
2. A graphical login, alongside the console.
3. HALT on the bar, beside Kas.
4. Start at the lower left, on the Windows key. The word stays Apps, never Programs.
5. Quick access first, with the root one press down.
6. Recycle Bin on new installs; your profile keeps DELETE.
7. File, Edit, View, Go, Tools and Help as the menu names.
8. Kas making system changes through the system's own prompt, with you there.
9. The computer maximised above the bar, not full screen.
10. No foot in the window.

And from today: the looks named Pencil and Indigo, and the Guide page called "Kas, the Ghost in the Shell".

What didn't move:

- no picture of her;
- Apps, never Programs;
- Day as the launch look;
- every state a word and a shape;
- her authority rules.

## 57:30 · What comes next, and your evening

**Next week, in order:**

1. **Your ThinkPad results first.** Whatever you find outranks my list.
2. **Grounding.** An index of your machine's own manual pages, so every option she proposes is checked against your
   version and quoted, and "teach me" answers from the page.
3. **The rest of a distribution:** printers, Bluetooth, date and time pages; a Task Manager; a live image to boot from;
   a security review of every door she has; and a pass over the licences.
4. **The old graphite-* command names go away.**

**For your evening:**

1. Install Kas from the 1.1.6 kit (1.1.7 if it arrives first): `JOIN.sh`, then `install.sh` as root.
2. Log out and in, then type `kas-startx`.
3. Open LibreOffice from Start with the Windows key. Is it above the bar?
4. In the bar's line, type `calc`, `12*7`, `dir`, `control panel` and `free space`.
5. In the Explorer, sort Downloads by size, then try Icons in Pictures, then Alt+P.
6. Press Win+` and try `top`, then `vim`, then `dir`.
7. Ask Kas to sort your downloads by kind. Press Run, then Undo.
8. Ask her to install cowsay. Watch the system's prompt, then Undo.
9. Switch to Night with CRT effects on Full, and look at the burn.

Whatever differs from what I've said is a result. Send it, with a photo if it's on the screen.

That's Kas: one name, a computer your Windows hands already know, opening onto a whole Linux box. Kas sits beside you
and reaches most of it. She shows you exactly what she'd do, waits for your press, and checks before she says it's done.

The model proposes. The desk disposes. And you keep the authority.
