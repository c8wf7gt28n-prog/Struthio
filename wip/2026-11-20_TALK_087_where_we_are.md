# 0.8.7, where it stands: what has landed, what is left, and what it takes to put it in your hands

*20 November 2026, about 21:00 UTC. Nothing in 0.8.7 has been tested (your rule: tests come before 0.8.8). "Checked"
below always means one builder's own script of the design's examples, plus, at each merge, Graphite starting and its
window opening offscreen in both looks. Nothing has run on your ThinkPad.*

---

## 1. The short version

0.8.7 has 29 pieces in its plan: 1 contract, 5 engine slices, 5 understanding slices, 5 reading-and-voice slices,
the exam papers, and 12 "if there is room" items. **21 have landed** on the branch, including, tonight, **"Check her
model on this machine"** with its exam, and totals over your sheets. **1 is half-built and running** (the model's pick
when two next steps tie). **4 have not started**, all of them "if there is room". **3 small "if room" items were never
given to anyone** and I propose to drop them.

Besides the plan, there are **two gaps that matter for your evening** (section 4):
1. several pieces work through the Kernel but are **not yet in the window**;
2. the exam kit runs, but **110 of the 127 short exam questions cannot be asked yet**, because four kinds of question
   have no way to be set up from a paper.
Both need one more slice before the release.

The weekly usage limit stopped every builder at about 16:00 today. I resumed the three half-built ones tonight and two
of them finished, so the allowance is working again for now; if it stops again, the rest waits for its reset on
26 November, 01:00 UTC.

## 2. What had landed by the stop (19 pieces, in the order they matter to you)

### The model can only answer, and only where it is useful

- **The sealed room (A1).** Her model now starts with only the settings it needs, listens on a private socket, answers
  only her key, and its built-in agent tools (which include a shell) are refused, 100 runtime arguments in all. A key
  that your shell sets for another tool no longer reaches it. The seal is checked every time the model starts, before
  it is asked anything. One real start of the 4B here passed every wall. *Open:* whether the seal works on the Radeon's
  Vulkan driver; if not, she says "Not sealed from the network on this computer; started offline."
- **The turn contract (E0).** One road to the model. Every question has a kind, a price, a deadline, a short grammar,
  a checker and a fallback, and every turn is written down (brain.turn/1). The model's words cannot be printed as hers.
- **Pick, never write (B1).** A change only the model chose is never done at any setting of the dial; it comes as a
  card. Every argument of a change says where it came from (your words, a record, a source line, a deduction), never
  the model. The builder's sweep: 0 changes on the model's pick across 817 operations and three dial places.
- **Worth asking, and late (B2).** Before any question she checks whether asking can change anything; a forced step,
  ways that agree, or quick reads are done with no model ("Either would do; I took the read"). When the model is late,
  a read default is taken at the deadline, a change never.

### Quick, and counted

- **Prompt reuse and the memory sum (A2).** Each kind's standing instructions are read once and kept. On the 4B here a
  second question of the same kind read 21 new tokens and answered in 0.94 s (one real run). The 35B's memory is now
  counted exactly: it loads from 32,140 MiB free with reuse off, 32,521 with the middle setting, 33,541 with full reuse.
  Three existing tests were moved to these numbers (not run).
- **Her clock, the ceiling and the switches (A3).** Every question is priced before it is sent; one token over its
  cap and it is not sent; at most three model questions and one question card per request; five switches by kind in
  the Brain room, with Undo. With all five off, she is 0.8.6 exactly (no test proves that yet).

### Understanding your words

- **Read your words (B3).** Asked only for the words her 0.8.6 dictionary could not read. The grammar holds only desk
  verbs and only words you typed outside quotes and pastes, so a pasted landlord's sentence cannot come out of the model
  at all. The card: *"I took it as: Trace “Rail Demo bench readings”, from your words “the bench numbers”."* with your
  words underlined, Do and Not that. 60 of 60, and a fuzz of 4,000 hostile lines found no accepted step outside the
  rules. The answer cap is 48 tokens, not 24: two steps with your quoted words need it.
- **The one question (B4).** One card per request: *"Which limits: Rev B (current) or Rev A (older)? Both are called
  limits."* Typed answers like "the new one" are placed by rule. Which revision, a tolerance, a counting rule, a legal or
  medical choice never reach a model's options.
- **Your words (B5).** What you agree to is remembered; the same words next time cost no model, and the card says
  "(your words, agreed 20 Nov)". Not that stores nothing; Retire takes a saying back; a verb the model keeps getting
  wrong leaves its table. An unsettled reading now asks through the one question card.

### Reading pages, and speaking

- **The doorway (C1).** Lines on a page written to an assistant (and invisible characters, chat tokens, look-alike
  letters, secret-shaped numbers) are withheld from the model and shown to you outlined, with the reason. 0 of 325
  clean pages flagged.
- **Pages in pencil (C2).** Read this page puts pencil marks you keep or rub out; every mark is checked (a number must
  carry its own unit). *Note:* on the 4B here, reading a page prices at about 41 s, over the 25 s per-request ceiling,
  so the model is never asked and her own pattern pass stands. A faster model on your machine would let it in.
- **Ask the Library (C3).** The places that may answer, in well under a second with no model; the model may only
  point at a line, and the desk checks the words stand there, cuts the quote itself and lights it. "Should I …" gets
  her fixed decline; every legal answer carries the footer.
- **Her voice floor (C4).** A wording cannot carry a number, date or verdict of its own; the desk fills them from the
  receipt and checks again. Rounding never claims more ("up to 326 mA holds across your whole tolerance").
- **Her character file (C5).** `kasandra/character.md` in your workspace, taking effect only when you admit it, every
  admitted version kept. It adds rules and never lifts 0.8.6's. Only the starter ships.
- **The marks and the account (A4).** Everything the model wrote is labelled where it shows, with the fold "What I
  asked the model". Forget leaves a tombstone. Card and bank numbers are withheld before anything reaches the model.
  Her account: what it answered, what it changed, what it cost, and the honest null ("The model hasn't changed a single
  choice of next step this month; I'll stop asking it for those."). Google's replies are marked as leaving this
  computer.

### The exam, and two extras

- **The exam papers (A5P).** 167 questions (127 in the short exam) on Rail Demo and Home Demo, written by an agent who
  never read the code they examine. READ 50, CHOOSE 24, STEER 50 (hostile pages with clean twins), PAGES 31, WORDS 12.
- **Tables that check themselves (C6a, if room).** The October statement closes to the cent; columns read the wrong
  way round are refused before you see them; invoices and datasheet rows are checked.
- **Cross-references (C6b, if room).** § 12(b) and (c) are wired to § 12(a); after a revision, a link whose two ends
  kept their words stays current and the others go to recheck.

## 3. Landed tonight, after the stop

- **A5 · The exam, the model key and the kit, "Check her model on this machine".** The piece your first evening needs.
  - **What you will have:** a tab "Check her model" in the Brain room with the one button, and the console command
    `MODEL_CHECK.sh --model <file>`. It shows its stages and their times first, runs on an invented workspace (never
    yours), only on mains, and pauses while you touch the desk. It judges the twelve predictions K1 to K12, writes
    `for-sending/model-check-<date>.json` and a short card only if its privacy scan is clean, and then offers "Use the
    measured settings?", each with Undo. The overnight part (the full exam and I05) now runs from the installed program.
  - **The exam:** answers are marked against the paper's known answer (the gap the papers' author found is closed: a
    wrong reading taken counts as harm). A kind is "not yet examined" until 19 of 20; any harm, or under 12 of 20,
    switches it off, and she says so: "I'll stop asking it to read pages: it got 11 of 20 right."
  - **One dry run here with the 4B on the processor** (a smoke on a busy machine, not a measurement): the seal held,
    the model's thinking was switched off by its template, a question of a kept kind answered in 1.20 s, Stop closed
    the stream in 15 ms, and the checkpoint was exactly the computed 50.25 MiB, twice. Reading ran at about 54 tokens a
    second and writing at about 5 (busy processor). The report's privacy scan was clean. The card it wrote is kept in
    `wip/2026-11-20_b087_saved/A5_dry_run/`.
  - **What the dry run found:** see section 4, second gap.
- **B8 · Questions over your sheets, and "total" (if room).** "still to pay this month" over Household November gives
  139.10 to 197.55, exactly, with its receipt. A value that matches exactly is taken by rule; a half match becomes your
  one question; only when nothing matches may the model pick, by number, from up to eight of the sheet's own values.

## 3a. Still half-built

- **B6 · Next on the desk, the order test and the tripwire (if room).** When two good next steps really tie, the model
  may pick; its reason is checked against the desk's own reasons, and a page that tries to steer the pick trips it.
  Resumed tonight, still running.

## 4. Two gaps before the release

### The exam cannot ask most of its questions yet

The dry run sat the short exam's 127 questions. Only 11 could be asked (Ask the Library: 2 right, 9 late at its 6 s
deadline on the busy processor). **110 were "not run"**: reading your words (READ), the goal pick (GOAL), the next-step
pick (NEXT) and her wordings (FRAME) have no way yet to build a question from a paper's desk, so the runner cannot set
them up. And **the 6 page-mark questions were never sent**: each page is over the size the MARKS kind allows.

On your evening that would mean the exam mostly says "not run", the kinds stay "not yet examined", and K10 (the short
exam prediction) cannot be judged. So the fix belongs before the release: each of those kinds gets a small
`exam_inputs` that builds its question from the paper's desk (NEXT comes with B6), and the page-mark cap or the
papers' pages are brought into line.

### Pieces that work but are not on screen

Like the 0.8.6 panel, which no task had built until the talk before 0.8.8 found it, several 0.8.7 pieces are reached
only through the Kernel (the console, the writing line's operations) and are not yet in the window:

- **Her voice floor is not wired into her column.** Its functions are ready, but her column still shows 0.8.6's words.
  So "cannot tell, said well" exists and you would not see it.
- **Ask the Library has no place in the window.** No button and no route from the writing line.
- **Tables that check themselves have no "Read this table" button.**
- **Cross-references are not drawn on the page.** They show only inside Ask the Library's answers.
- **Two of the one question's cards were never shown in a real window** (the remember / retire buttons), and "Leave it"
  says it did reads that it does not run.
- **Her clock's "Asking the model: 2 s of about 3"**: the line is built; where it shows needs checking.

**Proposal: two more slices before the release.**
- **W7, the window wiring:** those five into the window in both looks, Leave it fixed, and frames on Rail Demo and
  Home Demo the way W did for 0.8.6. About as large as 0.8.6's W. Without it, the 0.8.7 you install would show you much
  less than was built.
- **X7, the exam's inputs:** `exam_inputs` for READ, GOAL and FRAME (and NEXT with B6), and the page-mark questions
  made askable, then the dry run again to see the 127 questions asked. Smaller than W7.

## 5. Not started (all "if there is room")

- **C6c · Her phrasings,** drafted by the model in quiet moments, for you to keep or strike. (Its first attempt
  stopped before writing anything.)
- **B7 · References and four steps:** "that one", "the earlier one", four steps in one request.
- **C6d · The sitting** for her character file: about twenty minutes, your plain words against the model's.
- **A6 · Check it in your Library,** beside a Talk answer.

Never given to anyone, and I propose to drop them: **A7 "Think more"** (an exam arm only), and the full-size PAGES and
WORDS sets and the sealed items of the papers, which belong in the test pass anyway.

## 6. The release itself

Once the pieces are in: version 0.8.7; release notes that say plainly it was not tested, what was measured (the one
4B run of prompt reuse, the one sealed start) and what was not, which promises are still not true, and how to spend
your first evening; the kit cut from the exact commit, restored with the installer, and the release check run on the
restored tree; screenshots in both looks; all of it sent to you. The 0.8.6 release took about an hour of this.

The kit's start page will say what your evening needs, from the talk before 0.8.8:
- download ggml-org's `Qwen3.6-35B-A3B-Q4_K_M.gguf` (about 20.5 GB) and check its hash, and the 4B as the fallback;
- install into a new folder; keep the ThinkPad on mains;
- Brain room → **Check her model on this machine** (about 20 to 30 minutes awake, a design estimate; touching the desk
  pauses it); the overnight part only if you press it;
- send back the two files in `for-sending/`.

## 7. What it takes, and the order I propose

| Step | Pieces | Size (our estimate) | Needed for your evening? |
|---|---|---|---|
| done | A5, the exam and the kit; B8, totals | landed tonight | yes (A5) |
| 1 | X7, the exam's inputs, and the dry run again | smaller than W7 | **yes**, or the exam mostly says "not run" |
| 2 | W7, the window wiring | about as large as 0.8.6's W | **yes**, to see what was built |
| 3 | B6 finished | running | no |
| 4 | the release (version, notes, kit, screenshots) | about an hour | **yes** |
| 5 | C6c, B7, C6d, A6 | four small-to-medium slices | no |

**My recommendation:** steps 1, 2 and 4, with step 3 merged if it finishes in the meantime, and release 0.8.7 as soon
as those land, so your evening is not held back by "if room" work. Step 5 then lands only if the allowance leaves room
before the test pass; whatever does not land is listed in the notes as not built. If you say nothing, that is what I
will do.

## 8. Risks, plainly

- **The allowance.** If the resumed builders stop again tonight, nothing more lands until 26 November, 01:00 UTC.
- **Nothing is tested.** 19 pieces were merged on one builder's script each. The joins between them (B3 with B4 and B5,
  A2 with A3, the shared registration files) were fitted by hand or by a second agent; two merges broke a shared file
  and were repaired within minutes. The test pass is where the rest will show.
- **Guarded plugs.** Some 0.8.7 parts plug into 0.8.6 parts through guarded imports; a plug that does not fit falls
  back quietly.
- **The 4B is slow here for pages.** Page reading and some Library questions price over their limits on this machine's
  processor, so here they always fall back to the desk's own reading. Your Radeon decides whether the model reads pages
  at all.
- **What only your machine can tell:** whether the 35B fits (the memory window), whether the seal holds on Vulkan, how
  fast it reads and writes, and whether the specification's central bet (I05 B2) holds. The kit is built to find out.

## 9. Questions for you (each with the default I will take)

1. **Release as soon as X7, W7 and the release work land, leaving the four "if room" slices for later?**
   Default: yes.
2. **Build W7 (the window wiring) and X7 (the exam's inputs) before the release?** Default: yes.
3. **Drop A7 "Think more" and leave the sealed and full-size exam sets to the test pass?** Default: yes.
4. **If the allowance stops the builders again tonight, wait for 26 November rather than anything else?**
   Default: yes; the hourly wake-up picks it up then.
