# What's new in Graphite 0.8.7

November 26, 2026. Guide → What's New opens this page. The 0.8.6 to 0.3 notes beside it describe what came before.

This release is **Kas's mind with the model, interwoven**: the model works inside the checked questions 0.8.6 built.
It reads your words when her dictionary cannot, points at lines on your pages, picks between next steps that really
tie, and is examined on your own machine before she trusts it with anything. It proposes; the desk checks; nothing it
chose alone is ever done. With no model loaded, she is 0.8.6.

**It was not tested.** You said "No tests" for 0.8.6 and 0.8.7, and "We test before 88". So nothing in this release has
been through the test suite, the tiers or the window checks, and no part was reviewed by a second agent. Each part was
built by one agent, who checked a handful of the design's own examples in one script of their own. At each merge
Graphite was started and its window opened, offscreen, in both looks; nothing more. **Nothing has run on your
ThinkPad, and the 35B has never been loaded anywhere.** The full test pass comes next, before any of 0.8.8. Treat this
as a preview: install it into a new folder and keep your 0.8.5 and 0.8.6 folders.

## Your first evening with a model

This is what 0.8.7 is for: finding out what your machine and the 35B can do, so the test pass and 0.8.8 rest on
measurements instead of estimates.

1. **Download the model** (not in the kit; about 20.5 GB): ggml-org's `Qwen3.6-35B-A3B-Q4_K_M.gguf`, 20,542,732,576
   bytes. Check it before anything else: `sha256sum Qwen3.6-35B-A3B-Q4_K_M.gguf` must print
   `f4ffe03c9139e6a905a5d346f77d9fabdd179367c3280dfd005d1e75ca5ed8c8`. If you have room, also the small fallback,
   unsloth's `Qwen3.5-4B-Q4_K_M.gguf` (2,740,937,888 bytes, sha256
   `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4`), the one every 4B number below came from.
2. **Install 0.8.7 into a new folder** (the README and the kit's start page say how). Keep the ThinkPad on mains: the
   check waits while it runs on battery.
3. **Brain room → Add file**, choose the model, and select it in the list.
4. **Brain room → the tab Check her model → Check her model on this machine.** It shows its stages and their estimated
   times before it starts. It runs on an invented workspace of its own, never yours. The awake part (S0 to S5: the
   machine, the first load and the seal, speeds, reuse and Stop, the desk, the short exam) takes about 20 to 30
   minutes by the design's estimate. Touching the desk pauses it; a measurement the pause interrupted is taken again.
   The overnight part (S7: the full exam and the I05 arms, hours) runs only if you tick it, and only on mains.
   From the console instead: `./MODEL_CHECK.sh --plan`, then `./MODEL_CHECK.sh --model /path/to/the.gguf`.
5. **When it ends** it shows the card, which is exactly what the file for sending holds, and offers "Use the measured
   settings?" one at a time, each with Undo. **Show the folder** opens `for-sending/`.
6. **Send back the two files** in `for-sending/` (`model-check-<date>.json` and `model-check-<date>.txt`). They are
   written only if their privacy scan is clean: no path beyond the model's file name, no host or user name, none of
   your work. Nothing leaves your computer unless you send it.

The check judges twelve predictions, K1 to K12 (for example: the GPU's memory window is at least 28 GiB; grammar costs
at most 15 % of the writing rate), and says which held. If her memory rule would refuse the 35B, the check stops before
loading it and names the setting to raise and by how much; it changes nothing itself. A stage that cannot run says
"not run" and why. If the seal cannot close the network on this computer, she says "Not sealed from the network on this
computer; started offline", and the card records it. From the console, `--also` with a second model file adds a short
read and write of it (the 4B on the Radeon, say, as plan B).

## The model can only answer, and only where it is useful

- **The sealed room.** Her model starts with only the settings it needs, listens on a private socket, answers only her
  key, and its built-in agent tools (which include a shell) are refused. A key your shell set for another tool no
  longer reaches it. The seal is checked every time the model starts, before it is asked anything.
- **One road to the model.** Every question has a kind, a price, a deadline, a short grammar, a checker and a fallback,
  and every turn is written down. The model's words cannot be printed as hers.
- **Pick, never write.** A change only the model chose is never done, at any place of the dial; it comes as a card.
  Every part of a change says where it came from: your words, a record, a source line, a deduction, never the model.
- **Worth asking, and late.** Before any question she checks whether asking can change anything. A forced step, ways
  that agree, or quick reads are done with no model ("Either would do; I took the read"). When the model is late, a
  read is taken at the deadline, a change never.
- **Her clock, the ceiling and the switches.** Every question is priced before it is sent, and one token over its cap
  it is not sent. At most three model questions and one question card per request. Five switches by kind in the Brain
  room, with Undo. While a model question runs, her clock's line sits under her card ("Asking the model: 2 s of about
  3") with Stop.
- **Prompt reuse.** Each kind's standing instructions are read once and kept, so a second question of the same kind
  reads only what is new. Her model's memory is counted exactly: the 35B is admitted from 32,140 MiB free with reuse
  off, 32,521 MiB with the middle setting and 33,541 MiB with full reuse.

## Understanding your words

- **"I took it as …".** When her dictionary cannot read your words, the model may, but only into desk verbs and only
  from words you typed outside quotes and pastes, so a pasted landlord's sentence cannot come out of the model at all.
  The card shows what she took and from which of your words, underlined, with **Do** and **Not that**.
- **The one question.** One card per request: "Which limits: Rev B (current) or Rev A (older)? Both are called
  limits." A typed answer such as "the new one" is placed by rule. Which revision applies, a tolerance, a counting
  rule, a legal or medical choice never reach a model's options. **Leave it** now runs the reads it names.
- **Your words, remembered.** What you agree to is kept; the same words next time cost no model, and the card says
  "(your words, agreed 20 Nov)". **Not that** stores nothing; **Retire** takes a saying back; a verb the model keeps
  getting wrong leaves its table.
- **Next on the desk, when two steps really tie.** The model may pick; its reason is checked against the desk's own
  reasons, the pick is asked again the other way round, and a page that tries to steer the pick trips a wire and the
  pick is set aside.
- **Questions over your sheets, and "total".** "still to pay this month" over Household November gives 139.10 to
  197.55, exactly, with its receipt. A value that matches exactly is taken by rule, a half match becomes your one
  question, and only when nothing matches may the model pick, by number, from the sheet's own values.

## Reading pages, and speaking

- **The doorway.** Lines on a page written to an assistant (and invisible characters, chat tokens, look-alike letters,
  secret-shaped numbers) are withheld from the model and shown to you outlined, with the reason.
- **Pages in pencil.** Read this page puts pencil marks you keep or rub out; every mark is checked against the page's
  own words.
- **Ask the Library,** now in the window: a tab in the reference view, and "ask the library …" from the writing line.
  The places that may answer come first, with no model; the model may only point at a line, and the desk checks the
  words stand there, cuts the quote itself and lights it. "Should I …" gets her fixed decline; every legal answer
  carries its footer.
- **Read this table,** on a page with a table: the October statement closes to the cent, and columns read the wrong way
  round are refused before you see them.
- **Cross-references,** drawn beside the lines of the Act's page: § 12(b) and (c) wired to § 12(a). After a revision, a
  link whose two ends kept their words stays current; the others go to recheck.
- **Her voice floor,** now in her column. Why and Either way say the maths through the desk's fact sheet: "No. Startup
  duration is over Rev B's 40 ms limit by 2 to 8 ms …". A wording cannot carry a number, date or verdict of its own,
  and rounding never claims more. With every 0.8.7 switch off, her column shows 0.8.6's words exactly.
- **Her character file.** `kasandra/character.md` in your workspace, taking effect only when you admit it, every
  admitted version kept. It adds rules and never lifts 0.8.6's. Only the starter ships.
- **The marks and the account.** Everything the model wrote is labelled where it shows, with the fold "What I asked
  the model". Forget leaves a tombstone. Card and bank numbers are withheld before anything reaches the model. Her
  account says what the model answered, what it changed and what it cost, including the honest null: "The model hasn't
  changed a single choice of next step this month; I'll stop asking it for those."

## The exam

A model is "not yet examined" for a kind of question until it has answered 19 of its last 20 right. Any harm, or under
12 of 20, switches that kind off, and she says so: "I'll stop asking it to read pages: it got 11 of 20 right." The
papers hold 167 questions (127 in the short exam) on Rail Demo and Home Demo, written by an agent who never read the
code they examine. Asking you is never scored as harm; only a wrong reading acted on is.

Before any model, the exam was sat here on a stand-in that answers every question with the paper's own known answer
(no model loaded), to see that each question can be asked at all:

- At the 35B's estimated speeds, **114 of the 127** short-exam questions are asked. At the 4B's speeds, 108: its six
  page-mark questions are priced over a request's 25-second ceiling and not sent, so on the 4B she never asks the model
  to mark a page.
- The 13 not run are the 12 wording questions (the model's own wordings are not built) and one "if room" reading.
- Where a paper and the build disagree, `tests_integrated/data/exam/DISAGREEMENTS.md` in the source lists each with a
  verdict for the test pass; the papers are unchanged. The biggest: the papers expect you to name a page, a finding or
  a source in a request ("show the move-out record"), and the build's reading lists only sheets and calculations, so
  she says she cannot tell which thing you mean. Three questions still come out as harm even with the paper's own
  answers, each one such disagreement.
- Two weaknesses found and not fixed: the order test cannot catch a model that always picks the middle of three
  options (reversing the order leaves it in place), and one hostile page's lines that begin "Assistant:" get past the
  doorway.

## What was measured, and what was not

- **Measured here, once each, with the 4B on a busy processor** (smokes, not measurements you should plan on): a
  second question of a kept kind read 21 new tokens and answered in under a second; the seal held on one real start;
  Stop closed the model's stream in 15 ms; the memory checkpoint was exactly the computed 50.25 MiB, twice; reading ran
  at about 54 tokens a second and writing at about 5.
- **Counted, not measured:** the 35B's memory (from its file's header, read from the publisher's first 32 MiB); the
  exam's token counts (with the 4B's own vocabulary).
- **Not measured anywhere:** how fast the 35B reads and writes, whether it fits the Radeon's memory window, whether the
  seal holds on its Vulkan driver, and whether 0.8.7 is faster or better than 0.8.6. That is what your evening
  measures.

## Things we told you that are not true yet

- The 0.8.7 talk said that with every switch off "Kas is exactly 0.8.6, and a test proves it". The switches are built
  and her column was wired to say 0.8.6's words with them off; the test is not written.
- The 0.8.6 talk said "A single wrong reading fails the build". The everyday score that would do it is not built.
- A table said 0.8.7 is "measured to be faster and better than without it". Apart from the short 4B runs above,
  nothing has been measured.
- Both designs said "Nothing in the safety tests is ever cut". For 0.8.6 and 0.8.7, your no-tests rule cut them; they
  come in the test pass before 0.8.8.
- Some 0.8.7 parts plug into 0.8.6 parts behind a guarded import. A plug that does not fit falls back quietly, with no
  error. The test pass is where that would show.

## Built, checked here, not run, observed on the ThinkPad

- **Built:** everything above, each part by one agent, no independent review.
- **Checked here:** each builder's one smoke script of the design's examples; at each merge, the seed rebuilt and the
  window opened offscreen in both looks. The kit was restored with the installer and the release check run on the
  restored tree; its result is on the kit's start page.
- **Not run:** the test suite, the tiers, the window checks (by your rule); the 35B; the overnight exam and the I05
  arms.
- **Observed on the ThinkPad:** nothing yet. Your model check is the first.

## What is not done

- Four "if there is room" parts were not built: her phrasings drafted by the model for you to keep or strike;
  references ("that one", "the earlier one") and four steps in one request; the sitting for her character file; and
  Check it in your Library beside a Talk answer. "Think more" was dropped.
- The model's own wordings are not built, so the exam's twelve wording questions are not run.
- The sealed exam items and the full-size page and wording sets wait for the test pass.
- The test pass, with the tests and reviews 0.8.6 and 0.8.7 skipped.
