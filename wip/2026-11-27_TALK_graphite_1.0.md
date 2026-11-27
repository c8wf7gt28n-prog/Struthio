# Graphite 1.0, a twenty-minute talk

*27 November 2026. A walk through the finished program, written to be read aloud in about twenty minutes. The times in
the margins are a guide. Everything here was built and seen working in the build machine, offscreen and against
stand-ins; none of it has run on your ThinkPad yet.*

---

## 0:00 · What 1.0 is

Your paper had a title: *The Living Desktop and the Ghost in the Shell*. Graphite 1.0 is that paper, built.

Three ideas hold it together. First, **Graphite is the computer you sit at**, not a program you open on it. Second, the
middle of the screen is a **living desktop**: what you select sits in the centre, surrounded by what it's connected to.
Third, there is **a ghost in the shell**: Kasandra, Kas, who is not a chat window but an agent user of the system. She
uses the same files, the same tools and the same programs you do, under your authority, and she never claims a thing is
done until she has checked that it is.

One sentence runs under all of it, and you'll hear it again: **the model proposes; the desk disposes.**

Before we go on, the honest part. You said "No testing", so nothing in 1.0 has been through a test suite. It was built
on a machine with no screen, no USB port, no sound and no Radeon. What I describe was seen working there in a window
nobody could look at, against stand-ins for your hardware. Your evening on the ThinkPad is the first real proof.

## 1:30 · Turning it on

You log in at the text console and start Graphite. A small supervisor takes over the session. Fluxbox runs hidden
underneath, and Graphite's window fills the screen. If Graphite's window ever crashes, the supervisor brings it back,
up to three times in a row, and **your apps stay open**, because each one runs in a session of its own. Across the very
top is a slim dock: Graphite, and every app window you have open. One press brings any of them forward.

The first time 1.0 starts, it opens in **Day**, the launch look, with one quiet line saying where your earlier look went.
Day is calm and light, built on one set of design tokens, with the Inter typeface for words and IBM Plex Mono for
numbers. Its dark twin is **Night**. Graphite and Kasandra, the older looks, are still there under Arrange ▸ Appearance.

The window has five places, and each has one job.

- **The head**: HALT in the upper left, the menus across the middle, Apps ⊕ in the upper right.
- **The left**: where things are. Files, Machine, Settings.
- **The centre**: the thing you're working on and its neighbourhood.
- **The right**: Kas, who works with you.
- **The foot**: the computer's own line, and the meters.

Nothing lives in two places. That rule is what keeps the screen quiet.

## 3:30 · The whole computer

Start on the left, with **Files**. It begins at "This computer /", the whole machine, with your Home folder open. In
Home you can do what you'd expect: open a file in its app, Rename, Move to, Copy to, New folder, Delete. Each action
leaves a line with an Undo.

You can also choose **many files at once**: a click, a range, add one more. A band appears, "48 files chosen in
~/Downloads", with Move to, Copy to and Delete. One press moves all of them, and **one Undo puts the whole batch back**.
If something changed in between, it puts back what it can and names what it couldn't. It never forces anything.

Delete sends things to the system's own bin. On screen it's still called DELETE, your rule from long ago, and from there
you can restore. Two things can never be deleted: Home itself, and the folder that holds Graphite's workspace.

Upper right, **Apps** lists what is actually installed, read from the apps' own desktop entries, by category, with a
search line. Any file can be opened with any app, and "Always open PDFs with this" sets the default.

The **Machine** tab is real, through Debian's own services. USB drives appear, open, and eject safely; "safe to remove"
shows only when it truly is. If a file on the drive is still open, it tells you which app is holding it and forces
nothing. The battery, the network and Wi-Fi, sound, and screens are all there. Change a screen arrangement and it goes
back by itself after fifteen seconds unless you press Keep.

**Settings → This computer** changes real settings: default apps, sound, screens, network, power, the session.
Notifications from apps arrive as a quiet toast that never steals your keys, and each one is kept in Log.

And when you leave (Lock, Suspend, Log out, Restart, Shut down, Return to Debian), Graphite names the apps still open
and asks each to close politely. It never kills one. Suspend always locks first.

## 6:30 · The living desktop

Now the centre, the part your paper drew as a bulletin board.

Select something, say the Rail Demo bench readings sheet, and it sits in the middle. Around it, on rings, are its
neighbours: the PDF it was read from, the limits it's checked against, the calculations made from it, the findings about
it, the open question it bears on, the summary page that quotes it.

The wires between them mean something. **A solid wire is a recorded link**: the desk knows it. **A dashed wire is a
guess**, and it says "possible, not verified". Click any wire and it tells you exactly why it's there: which cells,
which revision, which calculation.

**A tile's size is its relevance**, to the focus and to what you're doing right now. There are four sizes, and they
don't jump around for small changes. A refuted finding grows while you're working on the question it refutes; an
archived revision shrinks. When there isn't room, the least relevant fold into "and 3 more". Right-click any tile:
**Why am I shown?**, **Pin**, **Turn down**.

Everything that has a state speaks **one language**, the same on tiles, wires, steps and in Kas's column: a filled
square for CURRENT and SUPPORTED, a crossed circle for REFUTED, an empty square for an OPEN question, a diamond for
NEEDS YOUR WORD, two bars for stopped. Colour is only ever the third cue, after the word and the shape.

**Double-click to open** the thing and work on it in the centre. **Save and Return** saves and brings you back to the
same board at the same zoom, with whatever depended on your change marked for a recheck. **Full program** opens it in
LibreOffice or its own app, and when that app saves, the new revision is recognised.

You can have **tabs**, and a **split**: the specification on the left, the worksheet on the right. Only the pane you're
working in drives the tree and Kas's "this". **Back and Forward** take you to exactly where you were: the focus, the
zoom, the place in the document.

## 10:00 · The foot: the computer's line

At the foot is one line, with five names beside it: **Line, Terminal, Search, Web, Log**. Line is the default. It takes
a line, an operation by name, or an address. Terminal is a real shell. Search matches every word you type, across the
desk's records and your Home files' names, and a hit opens on the board. Web opens a page in your browser, and Log keeps
what happened.

If you type something that is really a request for Kas, the line doesn't try to run it. It offers **Ask Kasandra →**,
and the words move to her column. To the right are the meters: CPU, GPU, RAM, TXT, and the new one, NET.

## 11:00 · Kas

The right column is hers. There is no picture of her any more, as you asked. At the top is the activity bars' band, and
under it her name, the model she's using, and her state word with its shape: QUIET, WORKING, NEEDS YOUR WORD.

Then, only when something needs you, comes **Waits for you**. A step waiting for your word, your permission, or your
review appears there with its one press. That band is never covered, never folded, never pushed off the screen. After
that come her exchange with you, **ACTIVE WORK** (each task with its progress bar, its time left and its own Stop), her
grants, **FINDINGS** (live), up to four **NEXT STEPS**, the six commands (DO, DOUBT, TRACE, BRIEF, LINE, CHECK ALL) and
at the foot, her ask line.

## 12:30 · Watching her work: the paper's day

Let me walk you through the day from your paper, the way it actually ran in the window, with a real model loaded.

You open Rail Demo, an invented 12-volt rail on a bench. You ask her: *"Kas, review this assembly and tell me whether the
proposed power supply is sufficient."*

She does not invent an opinion. She answers from the desk's findings, one by one, each with its shape. One is refuted:
startup is *not* inside the Rev B limit of 40 milliseconds. Others are supported: settled power is 3 watts, inside the
4-watt limit. And one question is still open: why does startup take longer than 40 ms? Then she says: **"So I cannot
call it sufficient."** The model was never asked for that verdict. It comes from what the records hold.

You open the bench readings beside the specification, in the split, and change the settled current from 250 to 300
milliamps. Save.

Here is the ghost. **She notices by herself** that the summary page still says 3 watts, while the saved sheet now works
out to 3.6. In her next steps she offers **Update**. You press it. Her model proposes a plan; the desk checks every step.
Here the model's plan left out the change you'd asked for, so the desk refused it, used its own plan instead, and she
told you so.

The plan appears in ACTIVE WORK. Reads run on their own. **Every change waits**: "Waits for you: Authorise step 2", then a
permission, "Grant this for this assignment", and you see exactly what it covers before you press. Step 5 updates the
report in LibreOffice: "Settled power is 3.6 W at 12 V." She does that in her own hidden LibreOffice, never in your
windows. She saves, reads it back, compares it, and records a new revision, keeping the old one.

Then the line you'll come to trust: **"Every step is done (verified)."** Done means the effect was checked, not that a
command was sent. Each step leaves two records, "sent" and "confirmed". Close Graphite, open it again, and under ACTIVE
WORK is "Last: … done. Its journal": every step, every check, still there.

The startup question? Still open. She didn't paper over it.

## 15:30 · Her limits, and your authority

What makes this safe to live with is what she can't do.

**Permissions are yours.** Each one names an operation, a target and a scope (this task, until a time, or always) in
plain words before you press. The Kernel checks every step against them as it runs, not just the model's instructions.
When a plan needs several kinds of action in one folder, one press can give them all, each one named.

**HALT**, upper left, holds all of her work at once, and nothing else. Never your desktop, never your apps. RESUME
restarts nothing by itself: each task waits for its own Resume.

**In your apps**, she works through accessibility first: named buttons, menu items, fields, while you watch, under a
permission, checked afterwards. **A touch of your mouse or keys pauses her** between presses. Stop puts the window back
exactly as it was: focus, selection, cursor, scroll, even closing a menu she'd opened. She never presses Send, Pay,
Delete or Install in another app, and never types a password.

**A utility she writes** runs sealed: on copies only, no network, nothing outside its own folder, limited time and
memory. Applying its result to your real files always asks, and can be undone.

**The network** is offline first and always visible. NET shows "Kas: and the host" while she fetches. A page she brings
back is kept as quarantined data, and any line in it aimed at an assistant is held back and outlined. If the connection
drops halfway, the step reads "blocked: needs the network". It is never "done".

And now **she reads your documents**. Ask about the manual in your Home folder and she reads its pages and tells you
which page her answer came from. If the pages don't say, she says so.

## 17:30 · Her model

Her model runs on **llama.cpp v1.0.0**, sealed: only the settings it needs, a private socket, its agent tools refused.
On the ThinkPad that's the 35B, ideally the file with its own multi-token-prediction head.

The **model check** measures your machine. Its tuning stage tries flash attention, cache types, batch sizes and
multi-token prediction, and keeps a setting only if the answers come out identical without it. Then it tells you how far
reading and writing are from your goal of **99 tokens a second**, and offers each setting with Undo.

There's also an optional **quick model**: a small one beside the 35B. It takes a kind of question only after it passes
that kind's exam on your machine and measures faster. Here, a 2B failed every exam it sat, so it took nothing. That's the
system doing its job.

Here, on a busy cloud processor with the 4B, her planning turns took about five seconds. The 35B on your Radeon has
never been loaded anywhere. That's what your evening measures.

## 19:00 · What's left, and your evening

What 1.0 doesn't do yet, said plainly. The small model here couldn't plan a tidy-up of Downloads; the desk's own tidy
works without a model, and the 35B is untried. A few moments still freeze the window just over a tenth of a second.
Search doesn't look inside your files' text yet. She edits .odt and .ods, but only reads .docx and .xlsx.

Your evening is on the Guide menu: **Your First Evening with 1.0**. Install from the kit; your paper's §2 test with no
model, including crashing Graphite on purpose to watch your apps survive; the 35B and its tuning; then this same day on
Rail Demo, with numbered photos. Whatever differs from the page is a result. Send it, with the model check's two files
and the stall log.

That's Graphite 1.0. A computer that is the session; a desk where things sit among what they're connected to; and a
ghost in the shell who asks before she changes anything, and checks before she says it's done.

The model proposes. The desk disposes. And you keep the authority.
