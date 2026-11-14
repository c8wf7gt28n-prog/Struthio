# Three things next, and what each one sets moving

*About 20 minutes, in five parts.*

## 00:00–02:30 · Where we are

Kasandra is in. The window can be indigo with her pictures following the work, her name, your wordmark, your monogram,
honey for what is hers, violets for the desk, royal purple for the line. The line itself is our secret: it runs under
everything and the window never names it. The campaign runner is in too, and it already did its first job, which was
to find things: five places where Graphite's memory and model rules would treat your 35B model wrongly, and a dozen
places where the code cannot do what your "take it apart" document imagines.

So here is where I think the next work should go. I picked three things by one test: does it make other things fall
out of it, almost for free, once it is there? A feature you can see is nice. A floor that five features stand on is
better. Two of these are floors and one is a door: the door to the machine this was always for.

1. **Every act leaves a receipt.** One record, written by the Kernel itself, of what ran: which operation, on what,
   from which revision, with which method, what came out or where it stopped, who asked, and whether a model was
   involved.
2. **A method you can take apart.** Your clearance experiment, built honestly: a check that knows units, a fork that
   remembers its parent, a side-by-side preview, a pin in the project's own menu, and a run with the model off.
3. **Kasandra on the real model, on the ThinkPad.** The campaign's second deliverable: your 35B model loaded through
   the runner's real mode, measured, and the memory rules it tripped over fixed first.

I will take each in turn: what it is, why it is next, what it sets moving, what it stands on in the code today, the
first slice I would build, and how we will know it worked.

## 02:30–08:30 · One: every act leaves a receipt

Picture Kasandra changing B3 to 300 mA. Today the change happens, the Field turns two calculations lavender, her card
says "Approved", and her trail gets a line. Now picture asking, a week later, *what exactly did she run, on which
revision of the bench sheet, and what did the sheet say before?* Some of that is somewhere. Her trail has the line and
an Undo. The Kernel's journal says a request was received and completed. The sheet has revisions. But nothing ties
them together, and some of it is simply not kept. The readers found the gaps:

- When she saves an answer's rows as a sheet, it is written as `answer <time>.csv` with no record of which line made it
  or what it read. The line shows once in the status bar and is gone.
- The conversation itself is not saved, and words kept under a name are recorded in the journal without the line they
  stand for.
- Every refusal comes back from the Kernel with the same code, ValueError, so the window cannot tell "your input was
  wrong" from "a program is missing" from "the program answered nonsense". A line that fails says why, but not at which
  stage.
- The program rooms throw away what a program wrote to its error stream, though the Kernel's own jobs keep exit status,
  output and errors.

There is one place in Graphite that already does it right, and it is the model to copy: when you save a sheet from the
chain tray, it writes a receipt beside it with the program, the sources it read and their fingerprints, the seed, and
"LOCAL_NO_MODEL". That is a receipt. I want one for every act, written in one place, the Kernel's dispatch, so no window
can forget to write it.

**What a receipt holds.** The operation's registered name and its exact arguments. For every source it read, the
address and the revision or hash it had at that moment. The method and its revision, when there is one. The result's
hash and where it went (a cell, a file, a card), or the step where it stopped, with a kind: bad input, missing tool,
malformed output, refused by a rule, or stopped by you. Who asked: you by a click, you by a line, or Kasandra, and at
which place on her dial. Whether a model took part, which one, and how long. The seed's state at that moment. And a link
to its Undo, when it has one. Reads that only look (the census of the desk every few seconds) stay out, as the activity
log already keeps its observer reads out; acts that change something, and every line someone runs, go in.

**What falls out of it.** This is why it comes first:

- **Inspect at three levels** becomes nothing more than three views of one receipt. At a glance: what went in, what
  came out, whether anything was saved, whether a model was involved. One click deeper, the method: its fields, units
  and rule, and which revision ran. Deepest, the line itself, on its royal-purple slab, and the registered operation
  underneath. Right-click any of her cards, any result, any saved file, and it is the same view, because it is the same
  record.
- **"The same operation under the click and her request"**, the rule your document insisted on, stops being a promise
  and becomes a check: two receipts, the same operation name, compare the inputs and the outputs. If they differ, we
  have found a bug with exactly two places to look.
- **Debugging together.** When something stops, the receipt already says the last step that worked, the first that
  stopped, what it had in hand, and which of the kinds it was. The card can say "the program expected a number in this
  column" in plain words, with the exit status and the raw message under a fold. With the model off, all of that is
  still there, because none of it came from the model.
- **"Explain the result from your version."** When the model is on, she is handed the receipt as facts, through the
  same grounded path she already uses for the Field: these are the rows, this is the method and its revision, say it in
  your words and invent nothing.
- **The campaign** checks receipts instead of reading values back by hand. The reviewer caught an anchor whose reopen
  check looked at one cell; with receipts, "what did this run read and write" is one query, and two runs of the same
  case on different builds can be compared line by line. That is what turns the campaign into a regression net.
- **Her pictures** take their state from the latest receipts instead of watching buttons: completed when the last act
  went through, blocked when it stopped, and the kind decides which still.
- **Her trail and Undo** become one list: the trail is the receipts of her own acts, each with its Undo where it has one.
- **History that belongs to the workspace.** Today what you ran is in a per-user history; receipts are kept with the
  work, so opening a project shows what was done in it, by whom, from what.

**The first slice.** A `receipts` table in the workspace's own database, written by the Kernel's dispatch for every act
that changes something and every line that runs. Two reads, `receipts.get` and `receipts.list` (by thing, by time, by
who). Her cards keep their receipt's id. A finder for her cards in the right-click, with **Inspect**, **Run again** and
**in the line**. The failure kinds, as five words on the receipt, filled in where they are knowable today (the address
missing, the program missing, the program's answer unreadable). The chain tray's receipt becomes a receipt like the rest.

**How we know it worked.** A test that does one act each way (click, line, her) and finds three receipts with the same
operation and the same inputs. A test that kills the process after an act and reopens the receipt in a second process.
A campaign case that compares the receipts of two runs. And a census like the one I just ran for scrolling: every
changing operation in the registry either writes a receipt or is listed as an observer, and the list is a test.

**The one risk** I can name: volume. A busy afternoon is a few hundred acts; SQLite takes that without noticing. The
bigger risk is the opposite, writing too little, and the census test is for that.

## 08:30–14:30 · Two: a method you can take apart

This is your experiment, the one your document asked for: one clearance method, one fixture, one menu entry. I had it
designed, then had a skeptic try to break the design against the code. The arithmetic held exactly; eleven steps did
not, and every one of them has a fix. Here is what I learned, and why the experiment should be built on its own
operation rather than on lines.

**Why not just a line.** The line language compares bare numbers. Give it your fixture and it reads the row "0.028 in"
as 0.028 and fails it, though it is 0.7112 mm and should pass at 0.70. A row with no unit passes silently. Filtering on
"Unit = mm" quietly drops the rows that are not mm, so they vanish instead of being reported. And "less than or equal"
is refused; you have to say "at least" or "under". None of this is wrong for what lines are for, which is reading. But
a check that decides pass or fail on a part needs units, so the clearance check is its own registered operation, and a
line can call it.

**What the method is.** A record: the fields it needs (reference, gap, unit), the unit it judges in (mm), the rule (pass
when the gap is at least the minimum), the minimum (0.50), a revision, and when it is a fork, its parent and the parent's
revision. Applying it to a table gives one verdict per row: PASS, FAIL, or UNIT MISSING, never arithmetic on an undefined
input. Inches are converted exactly, at 25.4 mm to the inch, and the conversion is shown on the row. The verified
numbers for the fixture: at 0.50, four pass, one fails, one has no unit; fork it to 0.70 and two pass, three fail, one
has no unit; the rows whose verdict changes are C2 and C3; 0.028 in is exactly 0.7112 mm.

**The loop it gives you.** Kasandra runs the check on the table you have selected and says which method she used. You
right-click her card: Inspect shows the input, the method, the line. **Fork** makes your project's copy with its parent
recorded, and you change 0.50 to 0.70. The preview puts both side by side on the same input, the changed rows lit. You
keep your fork. She proposes a menu entry, "Check enclosure clearance", for this project; you approve it, and it can be
unpinned. Next week, a right-click on a compatible table in that project shows it. Turn the model off and run it from
the menu yourself: it works, because nothing in it needs her. Turn her back on and ask her to explain the result: she
answers from your version's receipt.

**What the skeptic found, plainly**, because this is the part that would have bitten us:

- Her rule only found a file given as an address or selected in Files; a plain path in a sentence ("check the
  clearances in SLIM4/clearance.csv") fell through to the model. It must accept a plain relative path.
- The hook for her check ran before her other rules, so with a CSV selected, "make a file called clearance-notes.txt"
  would have been taken for a check and silently not done. It must run after them, and only on clear check wording.
- A pin recorded a digest of the method's revision that nothing checked, so a rewritten history row could have run
  silently. The check must take the expected digest and refuse a mismatch.
- Her pin, once approved, had no Unpin. Everything she pins must be unpinnable from the same place.
- Number parsing would have accepted Arabic-Indic digits and a trailing newline; a spreadsheet's byte-order mark would
  have hidden the first column; "SLIM4" would have matched "SLIM40". All small, all real.
- And the design was larger than it needed to be: revising, diffing and re-pinning are not used by any of the
  experiment's eight steps. They wait.

**What falls out of it:**

- **Per-project tools.** Today the menu of kept chains is one file per user, and Tools and Programs are fixed lists. The
  pin store makes "this project's tools" exist, and the menu that grows from your work grows there.
- **Units travel.** Once one operation carries a value with its unit and its source revision, the same shape can go
  through the line's pipe: a column that knows it is mm, a result that says which revision supplied it. That is your
  document's fourth point, provenance through the pipe, and it starts here.
- **Two old special cases become one kind.** The worksheet's shortage method (Method Press) already keeps its column
  bindings and the source's hash and refuses changed units; the checked-methods module already has revise and accept.
  Both are methods. A general method kind takes them in instead of a third special case.
- **Words get a lineage.** A word kept under a name is overwritten in place today, silently. A fork with a parent and a
  revision is exactly what words need: no silent replacement, a difference before a change.
- **Your bench is already full of methods.** After Hours 07 has a limits sheet at revision A (120 ms) archived and one at
  revision B (80 ms) current. That is a fork in real life: one rule, two revisions, and a finding that depends on which
  one applies. The bench check in Pass 02 crosses the 3.50 W limit at 3.84 W. Once methods exist, those findings stop
  being prose and become checks you can fork, pin and run.
- **The campaign gets cases for free.** A method plus its fixture is a test: you can hand me one and say "here is the
  operation I want the next build to preserve", which is exactly what your document asked for.
- **Teaching by doing.** Her answer can offer "keep as a method" or "keep as a word". The first time she does it; the
  second time you fork it; by the fourth you may have a better one than she found.

**The first slice.** Two modules (the check and its records in the Kernel; her card, the right-click and the preview in
the window), a fixture tool, tests that walk your eight steps with the exact verdicts above, and the skeptic's eleven
corrections. Not in the seed's input set, so building it does not make lines refuse. Built on receipts if they are in,
since Inspect is a view of one; it can come first and take receipts later if you would rather see it sooner.

## 14:30–19:00 · Three: Kasandra on the real model, on the ThinkPad

Everything model-shaped in Graphite has been tested with small models in this container and never with yours. Nothing
later than 0.4.6 has run on the ThinkPad. The campaign can now tell us exactly what to fix before that first real run,
and it found five things that would bite on the first day:

- **On Auto, Graphite refuses your model at 39 GiB free.** The cap is 65 per cent of what is free, 25,958 MiB, and the
  estimate for your model is 26,013 MiB: 55 MiB short, with thirteen gigabytes to spare. With 64 GB in the machine you
  will often have more than 39 free, but not always, and "refused" for 55 MiB is the wrong answer.
- **Admission and launch disagree.** A 32 GiB model is admitted at 34 GiB free, then refused at launch by a second rule
  (the cap must be under 80 per cent of what is free). One rule should decide, once.
- **When the installed memory cannot be read**, the foreground reserve drops from 2 GiB to 128 MiB, and a request whose
  reading is lost after it was submitted waits with no deadline.
- **A restored model is called ready even when its test reply is empty**, and a worker that reports a smaller context
  than was asked for reaches Ready anyway. Your spec says ready means a valid reply.
- **A hold on background work cancels the queue** instead of holding it; your spec says hold, then continue from the
  right step.

And one more, smaller: the memory readings come from `/proc/meminfo` and not the process's own limits, which is the
same thing on a plain Debian desktop but not in every session.

**What falls out of it:**

- **Thirty anchors unlock.** The runner now checks what each situation needs on the machine it runs on: the model
  registered and matching your file, at least 24 GiB free, the 7735HS, a desktop session, LibreOffice, FreeCAD, Blender,
  GIMP, Thunderbird, your data. On the ThinkPad, the ones whose needs are all met will say "steps not written yet; its
  needs are here", and that list, made by the machine itself, is the build order for the next releases.
- **Her own words become real.** The grounded path, receipts as facts and the model saying them, is only worth
  something on the model you will use. So is the pack's idea that the model may suggest one of her stills.
- **Numbers decide the open questions.** How long the 35B takes to load, how many tokens a second the Radeon gives, how
  much memory a long context costs, whether the window stays smooth while it thinks (input to paint), and what her art
  costs against Clean. Those numbers decide whether the 35B is the everyday model or the one for long jobs with a small
  one for quick turns.
- **The two "spec asks otherwise" cases turn into Pass** when the rules are fixed, and the summary will show it.
- **The real panel.** The glow, the pointer, the typewriter face and royal purple all judged on your screen instead of
  in pictures.

**What I need from you, and it is small.** Install 0.8.0 from this set. Put the model file somewhere on the ThinkPad.
Then, from the installed folder: `python3 tools/campaign.py list` (it says what the machine has), and
`python3 tools/campaign.py run --mode real --case M01 --model /path/to/Qwen3.6-35B-A3B-Q4_K_M.gguf`. Today real mode
checks the file and the memory and prints exactly what it would run, and stops; send me its folder and a photo of the
screen. My side, first: the five rules above, so that the next real-mode step loads the model through Graphite's own
path and measures it instead of stopping.

## 19:00–20:00 · The order, and what I would ask you

**Receipts first**, because Inspect, debugging, explaining and the campaign's comparisons all stand on them, and because
it is a contained piece of work in one place. **The method second**, standing on receipts, because it is your experiment
and it opens per-project tools, units and lineage. **The real model in parallel**, because it needs your machine and not
mine, and because the rule fixes it starts with are independent of the other two.

What I would ask you:

1. Is the clearance check the right first method, or is there a check you actually run on real work (the bench's power
   limit, a startup pulse against a revision's limit) that you would rather see first? The machinery is the same; the
   first one should be one you care about.
2. Should pins belong to a project folder (as designed), or follow you across projects?
3. When you can, the real-mode run on the ThinkPad, and anything you notice about the look on the real panel.
