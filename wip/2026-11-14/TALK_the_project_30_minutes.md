# Graphite: the project, in thirty minutes

*Given 14 November 2026, at 0.8.3. A talk in ten parts.*

---

## 0:00 · What it is for

Graphite exists so that one person, on one computer they own, can do serious thinking work with an assistant at their
side, and trust what comes out of it.

Each word in that sentence is a design choice:

- **One person.** It is not a team product. There are no accounts, no shared workspace, no cloud sync to reason about.
  The owner is the authority on everything.
- **One computer.** Your ThinkPad E16: Ryzen 7 7735HS, Radeon 680M, 64 GB, Debian 13 at a text console. Everything runs
  there and stays there unless you turn a service on. A phone is optional access, never required.
- **Serious thinking work.** Engineering, research, documents, datasheets, calculations, findings. The worked case we
  keep returning to, After Hours 07, is a power rail on a bench: readings, two revisions of a limits sheet, a startup
  pulse that ran long, an open question.
- **An assistant at their side.** Stacy in the Graphite appearance, Kasandra in hers. Not a chatbot in a box: a
  colleague with a hand on the desk, under rules you set.
- **Trust what comes out.** This is the part most AI tools skip, and it is the reason Graphite looks the way it does
  inside. Every number has a source and a revision. Every change has an Undo or asks first. Every finding can be traced
  back to what supports it.

If I had to say the project's thesis in one line: *a local model is not trustworthy, but a local model inside a system
of records, rules and checks can be.*

## 2:30 · The shape of the machine

There are seven parts, and they nest.

**1. The Kernel: one door.** Everything that reads or changes anything goes through one function,
`Kernel.dispatch(operation, arguments, principal)`. There are 771 registered operations today: 396 read, 157 execute,
206 approve, plus 11 candidates and one repair review. The scope is the safety model:

- *read* runs freely;
- *execute* runs for the owner and for her hand when the dial allows;
- *approve* always waits for your click.

The window, the typed line, the model and the tests all come through the same door. That's why a model can never do
something the window couldn't: there is no back door to use.

**2. Records, with revisions and provenance.** Sources, sheets, calculations, findings, pages, questions. Each record
has a revision. Each derived thing knows what it was derived from, at which revision. When a source changes, everything
downstream is marked "recheck", not silently stale. This is the ledger in Ledger & Slate, the name before Graphite.

**3. The Field.** The desk seen as a map: columns of material, tables, calculations, findings and open questions, with
wires between them. It's where trust becomes visible. Trace lights the wires from a finding back to its sources; Doubt
asks what a plausible result might hide; What if works a calculation again with another value and changes nothing. The
after-hours look made Trace crystallize along those wires, but the wires were always the point.

**4. Lines.** The little language underneath. A line picks a source and carries it through steps:
`@files:bench.csv | rows | where unit=mA | count`. It is never named in the window; you decided it stays our secret
power. The right-click's Then menu builds lines step by step, showing what each step gives before you take it. The same
lines are what the model proposes, so you, the menus and the model all speak one language that Graphite can check.

**5. The window.** PySide6: the head with its eight menus and the equalizer, the left column with the trees and now
Kasandra's hologram, the centre, her column on the right, the writing line at the foot with its five targets (Kasandra,
Terminal, Search, Web, Log). Two appearances share every piece of code; only the palette, the faces and the art change.

**6. Her hand.** Since 0.6.0 the assistant can act, not just talk. There's a dial of three places:

- **Ask first:** every change waits for you.
- **Do and show:** a change you ask for is made at once, shown, and has one Undo.
- **Free hand:** she may also make changes the records mark for approval.

What cannot be undone always asks, at every place on the dial. Her trail lists everything she did. Since 0.8.2 she also
has desk acts: forty named things a hand can do in the window, so she can be given a door to the window itself.

**7. The model.** A local language model through a pinned llama.cpp (build b11669), started and stopped by Graphite's
own service, with memory rules decided in 0.8.1. Auto admits your 35B with 31.4 GiB free (32,157 MiB, so it now
takes the 39 GiB case it used to refuse): its 26,013 MiB estimate, a 2 GiB reserve and 4 GiB of headroom. *(Corrected
14 Nov after review: the talk first said "when there are 39 GiB free".)* A handover waits for the old model's memory. Ready means it actually
answered.

The principle across all seven: **the model proposes, the system disposes.** The model's words are marked as its own.
What it proposes is checked against the same registry the menus use. What it finds is a proposal until evidence
supports it.

## 8:00 · How we got here

The arc is worth seeing whole, because each era taught us something we still use.

**The foundation, 0.1 to 0.3 (early November).**
- The rename from Ledger & Slate to Graphite.
- The Field arrives in 0.3, with the shelf and the GPL.
- *The lesson:* the desk should open on the work, not on a launcher.

**The desk that does, 0.4 to 0.4.9.**
- Stacy reading with lines; Trace, What if and Doubt.
- A mouse-first pass, the green pointer, amber for the keyboard.
- An audit that gave each action one visible home.
- *The lesson:* a second set of readers going through the code while it's written finds real faults. We've worked that
  way ever since.

**Your first walk on the ThinkPad, 0.5.x.**
- You ran 0.4.6 on the real machine and came back with directions: menus across the head, way more glow, no keys
  printed anywhere, neon green icons.
- *The lesson:* the real panel judges the look, not the pictures.

**Her hand, 0.6.**
- The dial, Undo, the trail, what always asks.
- The first journey: start a Godot project from words.
- *The lesson:* acting is only safe when every act is shown and can be taken back.

**The machine as instruments, 0.7.**
- The System menu dissolved into the four meters as doors, the equalizer, the expanding line.
- *The lesson:* fewer menus, more places that answer when touched.

**Kasandra, 0.8.0 to 0.8.3.**
- A second appearance with its own identity.
- The 35B campaign runner.
- The right-click that chains, and the memory rules decided for the 35B.
- Desk acts and your playable scene.
- The after-hours look; today's hologram, typewriter face, DELETE, burnt yellow and the neon kp.
- *The lesson:* identity matters to how the tool feels, and it must never cost readability or trust.

Seventeen releases in nine days, each checked, packaged into 15 MB parts and restored byte for byte before it reached
you.

## 12:00 · Kasandra, and why the look is not decoration

It would be easy to see the look as the fun part and the Kernel as the serious part. I think that's wrong for this
project.

You work long hours in this window. If it's dull, you'll use it less; if it's tiring, you'll make more mistakes. Your
"Graphite after hours" piece put it exactly: "you touch the machine and it responds with a little more force than you
expected." The design rules we've learned all serve that line:

- **Motion helps or it goes.** Trace's 700 ms surge shows you which findings share a source. The 150 ms menu catch never
  delays a click: the menu answers from its first instant. Reduce motion lands everything on its settled frame.
- **Readability wins every tie.** The typewriter face is everywhere, but a fixed-width cut of it carries the code and
  numbers so columns align, and the 1 got a long sloped flag so it never reads as an l.
- **Colour means one thing.** Yellow now means "this is where you are". The rule "never green" came from your eye:
  yellow over her cyan is green. The review proved it with the mouse pointer's halo, which no screenshot shows.
- **Her state is visible without words.** The hologram's base and static change with what she's doing. That carries
  0.8.0's idea of "art chosen by the state of the work" into a living form.

The look is also where the assistant becomes someone rather than something. A hologram that is busy when she works and
holds still when something waits for you tells you more, faster, than a status line. That's not decoration; it's an
interface.

## 15:00 · Her hand and the planner: the heart of the next phase

Here's the central technical problem of the next month.

We want you to say "trace the bench readings and put the limits side by side", and have Kasandra do it on the desk,
where you can see, at your pace, stoppable at any moment. A model good enough to drive a GUI by itself, step by step,
needs to be very large and still fails often. On your machine, every step costs a prompt read, and prompt reading is the
slow part.

The evidence came this morning. On a quiet CPU the 4B made **three correct decisions in a row** in the I05 case. Then
it ran out of time on the fourth, after eleven minutes and 31,000 tokens, because each step re-sent the whole situation
and asked it to think from scratch.

The answer is to split the work by what each part is good at:

- **The model understands what you meant.** It gets one small question: "Which of these numbered goals did you mean?"
  It answers with one to three numbers. That's choosing, not writing, and small models choose well. Under 1,200 tokens of
  prompt and 32 of answer: seconds on your 35B, under half a minute on the 4B here.
- **Deduction finds the steps.** Each desk act has preconditions (a trace needs the Field in front and a sheet
  selected) and effects (the route is shown). From the window's state, read fresh before every act, a search finds the
  shortest sequence that makes the goal true. It's bounded at 4,096 states and 12 acts, and deterministic, so the same
  request gives the same plan.
- **Receding horizon.** Plan, do one act, read the window back, plan again. A surprise (a dialog, your click, a refresh)
  is absorbed at the next read instead of compounding. A progress measure that must fall at every step guarantees a turn
  can't run forever.
- **You stay in charge.** Touch the mouse or keyboard and she stops before her next click; scrolling doesn't stop her,
  so you can read her card. "Put my window back" returns it as it was. At Ask first she lists the moves and waits for Go
  ahead.

Then the maths on data, which is where your proposal shines:

- **Exact ranges.** Values become exact fraction ranges in base units, and the decision is one of three: holds, does not
  hold, or cannot tell. Your pulse: 110 ms ±5 against Rev B's 80 ms is over by 25 to 35 ms whatever the true value, so a
  better instrument can't change that verdict, and she won't ask for one.
- **Which measurement to ask for next.** Startup power against 8 W straddles the limit. Narrowing the current settles it
  more often than narrowing the voltage (89% against 78%), so she asks about the current first. That's value of
  information, exact.
- **Solve for, range, check.** From PAL draft 0.2: solve 12 V × I ≤ 6 W and the ceiling is exactly 500 mA; across
  11.8–12.2 V it's 30,000/61 mA, and in whole mA, 491.

**PAL** is the contract that makes this coherent. You, the Then menu and the model all propose lines; one registry
declares each step's types, effects and guards; every answer carries a receipt (the line, the source revisions, the
coverage). Its audit found four ways today's line evaluator can give a wrong number silently: `2*-3` comes out as −3, a
sum skips numbers written as text, true and 1 group together, and a join overwrites a field. Those get fixed first.

## 20:00 · The model reality

Your 35B is a mixture of experts: about 35 billion weights stored, about 3 billion used per token. That's the right
shape for your machine, and the physics says why.

- **Generating is limited by memory bandwidth.** Two channels of DDR5 at 4,800 give about 77 GB/s on paper. Each token
  reads about 1.8 GB of active weights, so the ceiling is about 40 tokens a second. Realistically, about 15 to 25 on the
  680M. That's fast.
- **Reading the prompt is limited by arithmetic,** a few hundred tokens a second on the 680M. A 1,200-token prompt costs
  4 to 8 seconds; a 6,000-token prompt, 20 to 40.
- **The GPU borrows system memory** through a kernel-managed window, typically about half of RAM on stock Debian. 26 GB
  fits under 32, but not by a wide margin once the KV cache grows.

Three consequences shape everything:

1. **Short prompts are the whole game.** That's why the planner asks the model small questions and reuses prompt prefixes
   it has already read.
2. **The memory window must be measured, not assumed.** A one-command ThinkPad check that reads it is the first
   deliverable on the road to 0.9.0.
3. **Escalation, not hope.** When the model can't decide: first narrow the options, then let it think, then ask three
   times and take what two agree on. Only then propose a model swap (a dense model, or a vision model where pictures
   matter), as a card you approve, and only if the memory admissibility check says it fits.

The 4B here is our test bench, not your model. It proved the memory rules with real workers today: Auto start, an answer,
a handover to the 2B in 4.1 seconds and back in 6.1. And it gave us the honest baseline the planner must beat.

## 23:00 · Quality: how we know, and where we don't

Every release goes through:

- a module suite (now 64 modules and 1,007 tests);
- your playable scene in both appearances, through the campaign;
- 30 window probes at two sizes;
- a crawler that presses every control in both appearances;
- a sweep that checks the language is never named on screen;
- a window gate;
- a byte-for-byte restore of the kit.

On top of that, independent reviews go through each major pass before it reaches you, and they keep earning their place:

- the desk acts review found eleven problems, including an act that could type a line break into the Terminal;
- the look reviews found the green pointer halo;
- your playable scene found a list left sitting over the Field.

Now the honest part. Your "clean up this mammoth" was right, and here is what the measuring found:

- **Twenty tests have failed for many releases**, carried as "known". Fifteen assert an old look. Five are about model
  activation and restore, which the model swap will lean on; those must be read one by one, not ignored.
- **The window gate has passed 7 of 17 scripts for many releases.** A check that never changes carries no signal.
- **The release check costs about 73 minutes.** One test module is 190 of the suite's 488 seconds. Many checks run
  whether or not anything they guard changed.
- **Coverage and about 160 deliberately planted bugs** were measured to see which tests actually catch anything. The
  decision step is what's left: retire with evidence, fix what matters, keep one good test per owner rule, and tier the
  runs so a change costs a minute, not an hour.

And the gaps no test here can close:

- Nothing later than 0.4.6 has run on your ThinkPad.
- The 35B has never answered on the Radeon.
- Your real data started on 0.4.6 and hasn't been carried forward through a migration drill.
- The window's code is concentrated: three files over 2,900 lines each, where parallel work collides.

## 26:00 · The bets and the risks

Four bets this project makes, stated so they can be wrong:

1. **Records plus rules can make a local model trustworthy enough for real work.** Evidence so far: Trace, the
   revisions, what always asks, and the receipts all work offscreen. The real test is a whole journey with your 35B: a
   datasheet to a sheet to a calculation to a report.
2. **Deduction can carry most of the steps, so the model only has to understand.** Evidence: the 4B's three correct
   decisions, and the planner design's predictions. Its I05 experiment is pre-registered so it can fail honestly: B2
   should pass with three or fewer model turns per case.
3. **One language for you, the menus and the model.** PAL says so; the line bugs show why it matters.
4. **Identity and readability together.** The look is a bet that a tool you love to sit with is a tool you use well.

Three risks I'd name:

1. **The ThinkPad gap.** Every week without real-machine observations widens the distance between what we check and
   what you live with. It's also the cheapest gap to close.
2. **Scope.** PAL's full type system, SQL adapters, vision models, the twenty-pass plan's mail and calendar: each is
   right eventually, and each could stall 0.9.0 if pulled in early. The answer is slices, each shippable.
3. **Concentration.** Five-thousand-line files and a suite that takes an hour make every change riskier and slower. The
   split and the tiers are not cosmetics; they're what lets her hand grow without breaking the desk.

## 28:00 · The road, and what I need from you

**To 0.9.0, six gates:**

1. **The ThinkPad itself:** the one-command check, the 35B answering on the Radeon, your scene on the real display.
2. **Her hand with the planner:** slice S1, the door on the Field (half-built and saved); one maths core in lines; goals
   over data; changes through her door with DELETE's Undo; the I05 arms.
3. **Tests you can believe:** zero failing, useless ones retired with evidence, the line bugs fixed, tiered runs.
4. **Architecture and speed:** the window split by surface, with budgets (start in 6 s, a Field frame in 16 ms, the
   hologram under 2% of a core).
5. **Your data across versions:** a migration drill from 0.4.6.
6. **The look settled on your panel.**

**After 0.9.0, to 1.0,** the rest of the twenty-pass plan:

- full native programs from the desk;
- a changed fact that travels to everything that used it;
- the assistant on any described job;
- getting the tools it lacks;
- web, mail and calendar on your terms;
- specialist and creative routes;
- durable self-improvement;
- the maintained Debian image;
- the ThinkPad qualified.

**What only you can do:**

1. Install 0.8.3 on the ThinkPad and live with it for an evening; tell me what felt wrong.
2. When the check exists, run it once and send me the file.
3. The real tolerances for After Hours 07, and the 35B's daily context size.
4. Keep doing what you've been doing: the mood pieces, the hard questions, the "is this a good idea". The best parts of
   this project came from your directions; my job is to turn them into something exact, checked and safe.

Next session we resume the plan in order: her door on the Field, then the test clean-up, then the one maths core. The
notes and the saved work are in `wip/2026-11-14/`.
