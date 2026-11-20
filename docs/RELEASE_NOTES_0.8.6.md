# What's new in Graphite 0.8.6

November 20, 2026. Guide → What's New opens this page. The 0.8.5 to 0.3 notes beside it describe what came before.

This release is **Kas's mind without a model**: with no model loaded, Kasandra now works out what your desk allows,
exactly, says why, and names the one thing that would settle what is left. It also carries your new head and footer,
and the first parts of 0.8.7 (her model, interwoven), which were built beside it.

**It was not tested.** You said "No tests" for 0.8.6 and 0.8.7, and "We test before 88". So nothing in this release has
been through the test suite, the tiers or the window checks, and no part was reviewed by a second agent. Each part was
built by one agent, who checked a handful of the design's own examples in one script of their own. At each merge
Graphite was started and its window opened, offscreen, in both looks; nothing more. The full test pass comes after
0.8.7, before any of 0.8.8. Treat this as a preview: install it into a new folder and keep your 0.8.5 folder.

## Your head and footer

The layout you drew. Your Struthio is upper right, as Apps, in both looks. The menus start at the middle column's left
edge and follow it when you resize. The equalizer moved upper left, as neon tubes over a two-minute trace of all
activity. In the footer, under the middle column: the writing line, the room button (Line / Half / Tall), then send,
cyan in the Kasandra look. Under the right column, the four meters as rings with a minute of history; a meter with no
reading stays dim and says so. Send's right edge sits 8 px inside the column, as in the mockup you approved.

## Why, on every card

Right-click any card on the Field and choose **Why**. A short proof opens in her column: at most twelve lines, each with
its state word and where it came from, For and Against, and what would change it. Click a line and that card is
selected and the proof's wires light up. Next and Back walk it from the source. Beside Why: **Rests on** (and Without
it), **Either way** and **What would settle it**. Every line says "Model calls: 0".

## Her mind, with no model

- **Goals, exactly.** Keep a goal ("settled power is at most the limit") and she works out the room left, exactly, and
  the reading that would settle it.
- **Your word.** When something is yours to settle (which revision applies, how a row reads, that a list is complete),
  you say it once and it is kept as your word, with revisions. Setting it always asks, at every place of her dial.
- **Either way.** She works out the answer under every reading still open. Settled power holds whether Rev A or Rev B
  applies, so she does not ask. Startup depends only on which revision you say applies, so that one question goes to
  you.
- **What would settle it.** The one open thing that decides it, and the meter reading that would: "Measure startup
  current first."
- **Her dictionary.** She reads your words against your desk's own names and units, with no model.
- **Quotes and rule cards.** A quote is pinned only if its exact words stand on that page, and it shows MOVED or GONE
  when the file is replaced. A rule card rests only on pinned quotes or rows you reviewed; it never concludes
  "refuted", and goes stale when a quote moves.
- **Dates, further.** Periods after an event, deadlines that roll past a weekend or a holiday you list, events that may
  not happen, and answers "as of" a day.
- **What this change did.** After a sheet changes: what was worked again, what still carries an old number and needs
  you, and what carried over, with the reason.
- **Where does my desk say it.** The places on your admitted pages that may answer, ranked with no model, each ready to
  pin as a quote.
- **Your phrasebook.** When she reads your words a new way and you agree, you may keep the phrase. It never authorises a
  change and never leaves your machine.

## Try it on the two demos

Guide → **Try Rail Demo** or **Try Home Demo**. She tells you first: invented data, built in a new folder of its own
with its own profile, never in your workspace, opened in a window of its own. Guide → **An Evening with Kas's Mind**
has ten things to try; the first is: open Rail Demo, right-click the startup finding, and choose Why.

Home Demo is an invented household and an invented tenancy act. On it, Kasandra says what your text says, never what it
means for you; "Should I …" gets her fixed decline. No legal or financial advice.

## Early parts of 0.8.7 in this release

Built beside 0.8.6 and merged as they landed. Most are not visible until a model is loaded.

- **The sealed room.** Her model now runs with only the settings it needs, listens on a private socket, answers only her
  key, and its built-in agent tools (which include a shell) are refused. This closes a real hole: a key your shell set
  for another tool would have opened her model. Checked every time the model starts. Where the computer will not seal
  its network, she says "Not sealed from the network on this computer; started offline." Whether the seal works on the
  Radeon is untried.
- **Prompt reuse.** A second question of the same kind reads only what is new (on the 4B here: 21 new tokens, under a
  second). Her model's memory is now counted exactly for models like the 35B: it is admitted from 32,140 MiB free with
  reuse off, 32,521 MiB with the middle setting, 33,541 MiB with full reuse (0.8.5 said 32,157).
- **Her clock, the ceiling and the switches.** Every model question is priced before it is sent; at most three per
  request and one question card; five switches by kind in the Brain room, with Undo.
- **Worth asking, and late.** She asks the model only when the answer could change what she does; when it is late, a
  read is taken by default and a change never is.
- **Pick, never write.** A change only the model chose is never done, at any place of the dial: it comes as a card.
- **Ask the Library.** The places on your admitted pages that may answer, listed with no model; with a model, it may
  only point at a line, and the desk checks the words stand there, cuts the quote itself and lights it.
- **The doorway, pages in pencil, her voice floor, her character file.** Lines on a page written to an assistant are
  withheld from the model and shown to you; Read this page puts pencil marks you keep or rub out; her answers are cut
  from the receipt, rounded never to claim more; her character lives in `kasandra/character.md` in your workspace,
  taking effect only when you admit it.

## Four things we told you that are not true yet

- The 0.8.7 talk said that with every switch off "Kas is exactly 0.8.6, and a test proves it". The switches are built;
  that test is not written.
- The 0.8.6 talk said "A single wrong reading fails the build". The everyday score that would do it is not built.
- A table said 0.8.7 is "measured to be faster and better than without it". Apart from one short 4B run, nothing has
  been measured.
- Both designs said "Nothing in the safety tests is ever cut". For 0.8.6 and 0.8.7, your no-tests rule cut them; they
  come in the test pass before 0.8.8.

And one more, plainly: some 0.8.7 parts plug into 0.8.6 parts behind a guarded import. A plug that does not fit falls
back quietly, with no error. The test pass is where that would show.

## Built, checked here, not run, observed on the ThinkPad

- **Built:** everything above, each part by one agent, no independent review.
- **Checked here:** each builder's one smoke script of the design's examples; at each merge, the seed rebuilt and the
  window opened offscreen in both looks. The kit was restored with the installer and the release check run on the
  restored tree; its result is on the kit's start page.
- **Not run:** the test suite, the tiers, the window checks (by your rule); every model arm of I05 (its kit is in
  `tools/i05_kit/` in the source, for the ThinkPad); the demo windows themselves were not started here.
- **Observed on the ThinkPad:** nothing yet.

## What is not done

- 0.8.7 itself: reading your words with the model ("I took it as …"), the one question card, the marks
  and the account of what the model did, and "Check her model on this machine". They come in 0.8.7.
- The test pass, with the tests and reviews these two releases skipped.
