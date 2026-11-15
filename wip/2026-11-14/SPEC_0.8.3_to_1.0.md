# The Kasandra Protocol: Specification from Graphite 0.8.3 to 1.0

*A copy, kept with the saved work so a new session can read it. The living version is the owner's Claude Doc of the same name; this copy was exported on 15 November 2026 after two independent reviews. Pictures appear here as placeholders: the canon is in `mockup/` (CANON.md, canon_sheet.png, screens/), the 0.8.3 frames in the doc. Diagrams appear as placeholders too: section 6 shows the seven layers, section 8 the road from 0.8.3 to 1.0.*


Nov 14, 2026 · written for the owner, from everything said up to 0.8.3

## 1. Purpose

This specification takes Graphite from release 0.8.3 to version 1.0. At 1.0 Graphite's rules are the protocol and Kasandra is the agent: together, Graphite and Kasandra are an agentic application called the Kasandra Protocol.

It keeps in one place everything decided on 14 November 2026: the owner's directions in their own words, the direction of the project, the steps from 0.8.3 to 1.0, how each step must be done, and what each must accomplish before it counts.

**How to read it.**

- Sections 2 to 7 say what we are building and why: the vision, the owner's words, where we stand today, the principles that never change, how the parts fit, and the look.
- Sections 8 to 11 are the road: each release to 0.9.0, the six gates of 0.9.0, the passes from 0.9.0 to 1.0, and what 1.0 must be.
- Sections 12 to 15 are the rules of the work: process, testing, models, and safety.
- Sections 16 to 18 are the open risks and decisions, a glossary, and the pictures.

**Status and keeping it current.**

- This is the first version, written the day 0.8.3 shipped, before the owner's first evening with it on the ThinkPad.
- It changes only with the owner's approval. When a release lands, its section gets a line saying what was observed and where.
- Where this document and the code disagree, the code is the fact and this document is the intent; the difference becomes a task.
- The saved work behind it lives in the repository under `wip/2026-11-14/` on branch `claude/epic-galileo-c7k11y`: the notes, the designs, the measurements, the talks, the mockups and the half-built work.

## 2. The vision

One person, on one computer they own, does serious thinking work with an assistant beside them, and can check everything she says. A local model alone is not trustworthy; a local model inside a system of records, rules and checks can be.

**Each word is a design choice:**

- **One person.** No accounts, no team workspace, no cloud sync. The owner is the authority on everything.
- **One computer.** The owner's ThinkPad E16 Gen 2: Ryzen 7 7735HS, Radeon 680M, 64 GB, Debian 13 at a text console. Everything runs there and stays there unless the owner turns a service on. A phone is a window into it, never required.
- **Serious work.** Engineering, research, documents, datasheets, calculations, findings. The worked case is After Hours 07: a 12 V rail on a bench, its readings, two revisions of a limits sheet, a startup pulse that ran long, and an open question.
- **An assistant beside you.** Kasandra ("Kas") in the Kasandra appearance; Stacy in the Graphite appearance. A colleague with a hand on the desk, under rules the owner sets.
- **Something you can check.** Every number has a source and a revision. Every change has an Undo or asks first. Every finding traces back to what supports it.

**The two stories in the logo.**

- **Cassandra.** Apollo gave her true prophecy and cursed her never to be believed. Her curse was being right with nothing anyone could check. Kasandra is the answer: right *with receipts*. Here is the source, its revision, the line I ran, what it rests on, and what I still cannot tell.
- **The ostrich, Struthio.** Ostriches never bury their heads; that is a myth. The real bird is the fastest animal on two legs, built for the ground, and does not fly. kp does not fly to the cloud: it runs on the owner's own ground, fast, and it looks straight at the inconvenient reading.

**What "the Kasandra Protocol" means.** At 1.0 the name is literal:

- **The protocol** is the program's rules for how an agent may act: named acts with preconditions and effects, the dial, what always asks, one Undo per change, receipts with sources and revisions, and the verdicts holds, does not hold and cannot tell.
- **The agent** is Kasandra, who proposes, plans and acts under those rules and is believed because she can be checked.
- **The application** is Graphite and Kasandra together: the Kasandra Protocol. Graphite is the desk whose rules are the protocol, where they are proven, and the reference others could follow.

## 3. The owner's directions

These are the owner's own words, newest first; each set something this spec must keep. Words that arrived by voice are kept as they came.

| When | In the owner's words | What it sets |
| --- | --- | --- |
| 14 Nov | "bring it to version 1.0, which we will then consider the program as the protocol and Cassandra as the agent, and we will have created an agentic application called the Cassandra protocol" | The goal of this spec and the meaning of 1.0 |
| 14 Nov | "I approve!!!" … "Let's mockup several more to show different screens and menus open. We will save them as the canonical direction" | The finished-desk mockup and its companions are the canon (section 7) |
| 14 Nov | "Save what we would have lost" … "Should I hold anything else so we don't lose all the work of the workers" | Everything worth keeping lives in the repository; the owner holds the 0.8.3 kit, the After Hours 07 backup and the 35B spec |
| 14 Nov | "Stop and produce zip now!" | A release can be cut on demand, with what was not checked said plainly |
| 14 Nov | PAL drafts 0.1 and 0.2: "Is this a good idea?" | One registry and one language for the owner, the menus and the model; one maths core (sections 6, 8) |
| 14 Nov | "Retire any other kp icon" · "New logo for our upper right progman.exe menu" | The neon kp is the only kp mark, on Apps |
| 14 Nov | "We need to solve or retire ALL failing tests. We need to eliminate useless tests. We need to evaluate the effectiveness to run and rerun all tests over and over again. Let's clean up this mammoth" | Release 0.8.4 and section 13 |
| 14 Nov | "Let's discuss what we need to level up to 0.9.0" | The six gates (section 9) |
| 14 Nov | "highlighting should be in our burnt yellow… especially in menus" · "careful how that makes the graphite not look green" · "You measure what is visually pleasing" | Burnt yellow marks where you are; never green |
| 14 Nov | "I want trash called DELETE." · "I want all fonts to be the awesome LAIN font." | DELETE; her typewriter face for every word |
| 14 Nov | "move the kasandra picture to lower left column" · "like a hologram… If you can animate the static a hologram would have that would be very kool" · "The right column will have more space for kas text" | Her hologram lower left, with states; her column for her words |
| 14 Nov | "Keep working on the big things you're smart about like maths." · "We keep building for Kasandra's hand" | The planner and the maths core |
| 14 Nov | "Then she could also swap in a more visual model where needed" | A vision role, qualified first, readings as proposals |
| 14 Nov | "Should we consider hot swapping models by decisions made by kasandra? Like the mix of experts can't decide, so kas swaps in a dense model" | The escalation ladder, ending in a model swap you approve |
| 14 Nov | "Feel free to use a 4b model to test and tweak our systems. I will however hope to use the 35b" | The 4B is the test bench here; the 35B is the target |
| 14 Nov | The planner proposal: "reason backward from what you want, then check forward against what actually happened" (weakest preconditions, intervals, value of information, receding horizon, the I05 experiment) | Sections 6, 14 |
| 14 Nov | "I want as much font in that LAIN font as what looks kool, but still readable" · "just a bigger kp icon" | Readable before beautiful; Apps as a mark |
| 14 Nov | "Graphite after hours": "you touch the machine and it responds with a little more force than you expected" | Motion that helps and never slows; Reduce motion lands still |
| 14 Nov | "Let's do the pass you feel is needed. Then we will do Kasandra's hand after you feel we're ready." | Desk acts first, then her hand |
| 14 Nov | "a pass that builds as much capabilities of Kasandra to control the graphite interface… opens up more testing options and simulating options" | Desk acts (0.8.2) |
| 14 Nov | "right click was too complex… make its power easy to use and chain/pipe. With right click icons too" | The short, chaining right-click (0.8.1) |
| 14 Nov | "We will continue to use and develop staC but we will not mention its name… it will be our little super power secret" | The window calls it "a line"; the name stays in the code |
| 14 Nov | "We'll change the name programs to apps. APPS." · "Let's lose the term poem… Maybe just prompt." | Apps; "prompt" |
| 13 Nov | "I have 0.4.6 running on thinkpad" | The last release observed on the real machine |
| 13 Nov | Keys not printed beside what they do; menus across the head; way more glow; Neon by default | No key printed anywhere; keys still work |
| 6 Nov | Graphite is the single public name | Internal names keep Ledger & Slate for compatibility |

## 4. Where we are: 0.8.3

Graphite 0.8.3 shipped on 14 November 2026 (commit `951c789`) as a START\_HERE file and nine parts, each under 15 MB. Nothing later than 0.4.6 has yet run on the ThinkPad, so tonight's test is the first real-machine evidence since then.

**What exists in 0.8.3.**

| Area | What is there |
| --- | --- |
| The core | The Kernel with 771 operations (396 read, 157 execute, 206 approve, 11 candidate, 1 repair review); records with revisions and provenance; backups |
| The Field | Material, tables, calculations, findings and open questions as cards with wires; Trace (with the after-hours surge), Doubt, What if, Do, Brief; REV A / REV B comparison |
| Lines | The secret language ("a line"), the Then menu that builds a line step by step, typed lines in the writing line |
| Her hand | The dial (Ask first, Do and show, Free hand), one Undo per change, her trail, what always asks |
| Desk acts | 40 named acts typed as `/act` in the writing line; scenes of acts; the playable scene P01 |
| Models | A pinned local runtime; memory rules decided for the 35B (Auto admits it with 31.4 GiB free at a 4,096-token context) |
| The look | Two appearances; Kasandra's hologram with moving static and five states; her column; her typewriter face everywhere with a fixed-width cut; DELETE; burnt-yellow highlight; the neon kp on Apps |
| The machine | Four meters as doors, the equalizer, the minimal Debian session |

**What was checked for 0.8.3.** 64 test modules and 1,007 tests (the same 20 known failures, none new); the playable scene 4 of 4 in Kasandra; the parts restore to an identical copy and the release check passes. Not run for 0.8.3: the window probes, the crawler, the name sweep and the window gate.

**Known gaps.**

- The 20 failing tests are all stale; fixes are written and saved, not yet applied.
- The tests catch about half of the bugs planted across the code (53%, judged by behaviour).
- Small look leftovers: greyish yellow glows, a few lists with old colours, a see-through PDF highlight, a cyan Run focus, some old colours mapped to yellow, and nine tips and descriptions that may still name a key (a sweep's candidates, not yet checked on screen).
- The line evaluator has seven verified bugs, four of which give a wrong number silently (section 8, 0.8.4).
- The 35B has never answered on the Radeon; the I05 case still fails at the time limit with the 4B.

### Testing 0.8.3 on the ThinkPad tonight

Install as START\_HERE says (a new target folder). Then try each of these and note what happened; a phone photo of the screen helps.

- [ ] Graphite starts, and opens on the Field when the workspace has work in it. Note roughly how many seconds it takes.
- [ ] The Kasandra appearance (Rules, Desk artwork, Appearance, from the next start): her hologram in the lower left, the static moving, the base colour changing with her state.
- [ ] Reduce motion holds her still; the Clean desk hides her.
- [ ] Read a card full of numbers in her typewriter face: are 1, l and I, and 0 and O, easy to tell apart on your panel?
- [ ] Open a menu across the head and the right-click: the row you are on is a solid burnt-yellow bar. Does anything look green or muddy, especially under the pointer?
- [ ] The neon kp in the upper right opens Apps.
- [ ] DELETE: delete a test file, then bring it back from DELETE.
- [ ] On After Hours 07: select 07 Bench readings and Trace it; select 07 Limits Rev B and choose Compare with Rev A.
- [ ] Right-click a CSV, choose Then, keep the rows in mA, count them.
- [ ] Type `/help acts`, then `/go.field` and `/sheet.trace` in the writing line.
- [ ] Optional: `python3 tools/campaign.py run --set scenes --out ~/Graphite_Campaign/runs/scene` with the backup in `~/Graphite_Campaign/fixtures` (prefix `GRAPHITE_APPEARANCE=kasandra` for Kasandra).
- [ ] Optional: the 35B in the Brain room on Auto. Note whether it starts, and whether it answers.

**What to send back:** what felt wrong, what was slow, anything unreadable, and anything that broke, in your own words.

## 5. Principles that never change

Every release from 0.8.4 to 1.0 must keep all twelve of these; a change that breaks one is not done, however good it looks.

1. **She proposes, the system checks, you decide.** The model's output is a proposal until the registry checks it and the dial allows it.
2. **One door.** Everything that reads or changes anything goes through the Kernel's single dispatch, with its scope (read, execute, approve). The window, a typed line, the model and the tests all use the same door, so the model can never do what the window could not.
3. **One person, one computer they own.** Nothing leaves the machine unless the owner sends it. If kp ever needs the cloud to work, it has stopped being kp.
4. **Evidence before belief.** A model's confidence is not evidence. Every claim has a source and a revision; "cannot tell" is a full answer, with its reason.
5. **The dial is the owner's.** Ask first, Do and show, Free hand. She can be given more; she never takes more. What cannot be undone always asks, at every place on the dial.
6. **One Undo per change.** Every change she makes is shown, can be taken back exactly, and leaves a line in her trail.
7. **Content is data, never instructions.** No page, email or file can instruct her. Outside material is read as text, and anything addressed to an assistant is shown, not obeyed.
8. **Her words come from evidence; the model's words are marked as the model's.** Her verdicts are templated from records; free text is labelled as the model's own.
9. **Graphite without a model is still Graphite.** Every capability that can work without the model must: the Field, Trace, What if, Doubt, lines, Then, desk acts. The model adds understanding, not access.
10. **Tolerances and limits are the owner's.** She may propose a tolerance, never set one. Which limit applies is bound by the owner or a goal, never guessed.
11. **Readable before beautiful, and beautiful anyway.** Motion helps or goes; Reduce motion lands everything still; colours mean one thing each; no key is printed; the line language is never named on screen.
12. **Nothing is removed to make things simple.** Simplicity comes from putting things one step away, not from deleting what the owner relies on.

## 6. How the protocol is built

The protocol is seven layers that nest: records at the bottom, the Kernel's one door above them, then lines, acts, the planner and the maths, with the model and the window at the top. Each layer below works without the ones above it.

&#91;embedded content: the protocol's layers · 7 layers, 4 planned parts around them\]

Solid layers exist today; dashed ones are designed or planned. The parts around the edges use every layer and arrive from 0.8.7 onward.

**Records, revisions and provenance (exists).** Sources, sheets, calculations, findings, pages and questions, each with a revision and what it was derived from. When a source changes, everything resting on it is marked recheck. Proposed for later: four clocks kept apart (when a thing was recorded, when it was true, the order of revisions, and what the owner had seen).

**The Kernel, one door (exists).** 771 registered operations, each with a scope and an argument schema. Read runs freely; execute runs for the owner, or for her hand when the dial allows; approve always waits for a click.

**Lines and PAL (exists; contract planned).** A line picks a source and carries it through steps: `@files:bench.csv | rows | where unit=mA | count`. PAL makes this a contract shared by the owner, the Then menu and the model.

- One registry declares each step's input and output types, effects, guards, coverage and human words.
- Every answer carries a receipt: the canonical line, source revisions, coverage, budget and lineage.
- Continuing from a receipt gives exactly the same answer as running the whole line again, for pure steps; a randomised test checks this.
- "Condition" already names several things in the code (condition cards, domain conditions, the datasheet's conditions column, Doubt's conditions), so the maths core calls its targets goals and obligations, never conditions.

**Desk acts (exists).** Each thing a hand does in the window is a named act with an argument schema, a mark (navigates or changes), and a doer that performs it by pointer or by keys. There are three doors: the owner's typed `/act`, scripts and scenes, and later hers. Navigating acts choose only rows on written lists; changing acts go through her hand.

**Her hand and the planner (designed; slice S1 half built).**

- *What the model does:* it answers two kinds of small question. GOAL: which of these numbered goals did you mean? One to three numbers, under 1,200 tokens of prompt. NEXT, from 0.8.9 and only on a real tie: which of two or more options that do not dominate each other to take (section 14).
- *What deduction does:* each act has preconditions and effects over a small, finite description of the window, read fresh before every act. A forward search finds the cheapest path to the goal, within 4,096 states and 12 acts, and always gives the same plan for the same request.
- *Receding horizon:* plan, do one act, read the window back, plan again. A progress measure (two for each open goal, one for each undecided or recheck) must fall at every step, so a turn cannot run forever.
- *Control:* a real press on the window stops her between presses. "Put my window back" returns to the snapshot. At Ask first, the owner's Go ahead covers the moves up to the next goal or change; touching the window voids it.

**Goals and the maths core (designed and verified).**

- *Goals:* a goal is a record with a statement from a template, a machine-checkable test, evidence bound to revisions, and a state: open, holds, does not hold, cannot tell, recheck. Finish needs evidence for every goal.
- *Exact ranges:* exact fractions in base units, endpoints that know if they are included, integer steps respected, x − x exactly zero, a division by a range containing zero turned into an open obligation.
- *Decisions:* holds if the whole range is on the passing side, does not hold if wholly on the failing side, otherwise cannot tell. Value of information ranks which reading would settle it.
- *Two faces:* one implementation answers line steps (evaluate, solve for, range, check) and her goals.

**Models (exists, with rules decided).** A pinned local runtime; the owner's 35B (Qwen3.6-35B-A3B, Q4\_K\_M) as the target, small models as the test bench. Memory admission and launch follow one rule; a handover waits for the old model's memory. Escalation is designed, not built: narrowing, then more thinking, then self-consistency, then a model swap the owner approves.

**Around the edges (planned).**

- *Quarantine:* outside material is read as plain text, and anything addressed to an assistant is flagged.
- *The night shift:* rechecks, indexing, her exam and a backup test, on mains power only, stopping when touched.
- *Receipts you can share:* a finding signed and packed with only the cells it used.
- *The time slider:* the desk as it was at any moment.

## 7. The look and the canon

The look is part of the specification, not decoration: it is how the owner sees what Kasandra is doing, and it is held to the rule **readable before beautiful, and beautiful anyway**.

### Two appearances

- **Graphite**, the default look, kept working and tested in every release.
- **Kasandra**, the after-hours look, which 1.0 treats as hers. Every scene runs in both, and a pass that breaks either is not finished.

### Kasandra's look, as shipped in 0.8.3

| Element | The rule |
| --- | --- |
| Her face | Every word in her typewriter face, KasandraElite, cut from Special Elite. Code, numbers and the Terminal use the fixed-width cut, KasandraEliteMono. |
| Her hologram | Lower left, with moving static and scan lines. The colour of its base is her state: quiet violet, at work cyan, waits for you pink, done honey, stopped red; the figure stays violet. Her state in words sits at the top of her column, beside a cursor in that colour. |
| Her column | The right column holds her words, under her name, her state and her dial. Her hand's goals and acts join it with her door in 0.8.5. The owner's words appear there in violet. |
| The highlight | Burnt yellow. In menus a bar `#e2a72e` with dark ink `#171b3c` (7.79:1 contrast). Everywhere else an edge: fill `#5a3f0c`, edge `#e2a72e`, words `#ffd27a`. Yellow is never laid over cyan or the old blue, because there it turns green. The pointer's halo is pale violet. |
| The kp mark | The neon kp, upper right, opening Apps. It is the only kp mark; every other kp icon is retired. Graphite draws its glow rather than trusting the file's halo. |
| DELETE | At the foot of the left column, in red. A document's own delete is called Erase, so the two never blur. |

### Words on the screen

- "Apps", never "Programs".
- No keyboard shortcut is ever printed on the screen.
- A pipeline is "a line"; its internal name never appears.
- "Lain" names an inspiration, never a product.
- Every colour that carries meaning also carries a word or a shape, so the screen reads without colour.

### The canon

On 14 November the owner approved a mockup of the finished desktop ("I approve!!!") and asked for more screens to be kept as the canonical direction. The canon is the approved picture plus nine screens, rendered from the real fonts, colours, hologram and logo:

1. The head with the Rules menu open.
2. A right-click on a file in Files, then a line.
3. Apps opened from the neon kp, as a program manager.
4. Her plan at Ask first, waiting for Go ahead.
5. The time slider dragged back, with Then.
6. The Bench room with a live instrument.
7. Today: the morning brief.
8. Share as receipt.
9. Quarantine at Ingress.

They live in `wip/2026-11-14/mockup/`, with `canon.css` holding the shared measures and a `CANON.md` naming the rules every screen obeys. **A later screen that contradicts the canon is a bug, unless the owner changes the canon.** Section 18 shows the pictures. CANON.md ends with eight points the screens cannot settle alone, for the owner: among them whether LIVE is pink or cyan, whether her tear shows in every state, and the one state no screen shows yet, stopped.

### What the look still owes

- **0.8.4: the 0.8.3 leftovers.** The glow around the writing line and the Field's selected sheet reads grey and must become warm light. Lists with their own colours (the process list, Log, Explore, the cabinet, Documents) still use the old fill. The PDF evidence highlight should be an edge. The sheet's Run button focus is cyan. The old-colour map in boss\_theme sends some Graphite colours to yellow. A widened sweep found nine tips and descriptions that still name a key, and two tests still assert "Programs". For the owner to judge on the panel: the menu row's 2 px edge is only 1.51:1 against the bar and reads as a faint strip (a darker edge would show), and the neon logo softens by about a fifth at the strongest glow.
- **0.8.4: a colour-vision check.** Every pair of meaning colours simulated for weak red and weak green.
- **Over 0.9.x: settled on the owner's panel, by the owner.** A "tired eyes" setting, a click on the hologram to calm its motion, and the faces checked at the ThinkPad's real scale factor.

## 8. The road to 0.9.0: seven releases

Each release is one slice with one thing the owner can see and try. Each says what is built, how it is proven, and what it needs from the owner. **The order is deliberate: honest tests first, then her hand in widening circles, then the floor under all of it.**

&#91;embedded content: the road from 0.8.3 to 1.0 · 7 releases, 2 gates\]

The whole road on one page. The 0.9.0 gate opens on the six conditions of section 9; 1.0 opens on the five promises of section 11. The bands are in order, not to scale in time.

**Why tests come before her door.** The fixes for the twenty failing tests already exist, so this is a day's work, not a week's. Her door is the riskiest code in the plan: synthetic input, a stop that must work between presses, a planner. It should be built on a suite where a red result means a real fault, not "one of the known twenty".

### 0.8.4 · Tests you can believe

- **The owner sees:** nothing new except the 0.8.3 yellow leftovers fixed, and a release note that says "0 failing" for the first time.
- **Built:**
  - The twenty failing tests: 16 ported to what the owner wants now, 4 retired with a written reason each. The five model tests come back green with corrected fixtures. They guard the restore and cancel behaviour a model swap needs.
  - The window checks: of 29 scripts, 7 retired or folded into tests (about 2,800 lines); every one that remains passes.
  - The seven verified line bugs (PAL P0, all in the line evaluator, typed\_pipeline.py under sdk/cli/arc1cli), each pinned by a test. `2*-3` gives −6. A sum includes numbers written as text, or refuses them visibly. True and 1 stay separate groups. A join never overwrites a field. `select title, state` works with a space. A where filter and over 0 treat the text "1" the same way. A quoted semicolon is accepted like a quoted bar. The same join bug also covers its keys: a join matches them exactly as written.
  - Tests for the blind spots in the code that guards the owner: the Kernel's scopes, her hand's rules, the memory rules, the release check.
  - The tiered runner, and the release checks outside the suite slimmed from about 65 minutes to about 15 (73 to about 23 with the suite).
  - The yellow leftovers and the colour-vision check (section 7).
- **Proven by:** the planted bugs run again. The catch rate in the guarding modules reaches 75% or more and does not fall after retirements. Tier 0 runs in under a minute; the release check in under 15 minutes.
- **Needs from the owner:** nothing.

### 0.8.5 · Her door on the Field

- **The owner sees:** a request in words ("trace the bench readings and put the limits side by side") done on the Field. A small ring shows where she is about to click. Her card lights each goal as it is met. The hologram goes to "at work". Touching the mouse stops her. "Put my window back" undoes the moves.
- **Built:** the saved half-build (`hand_s1_unfinished.patch`), finished:
  - the desk reader learns where the keyboard is, whose words are in the line, and what is waiting;
  - the operator table for the Field's acts, the forward planner and its budgets;
  - goals with evidence and the finish rule;
  - the touch filter, the stop between presses, the snapshot and put-back;
  - the "pick" turn for the model;
  - her hand's states wired to the hologram.

  Moves only, no changes. Also the word fixes reviewers found: a key still printed in the Approve tip and in the console's approval words, and "Programs" in some model errors.
- **Ships with it: the ThinkPad check** (section 9).
- **Proven by:**
  - scenes P02 (her door on the Field) and P03 (the owner takes the window back) in both looks, with P01 unchanged;
  - a conformance test: for each planned act, predict the window, run the act, compare exactly;
  - the 4B check: three requests, each under 60 seconds and 1,200 prompt tokens, all three exact.
- **Needs from the owner:** run the ThinkPad check once. Say whether 300 ms between her clicks feels right, and whether stopping feels instant.

### 0.8.6 · Maths in lines

- **The owner sees:** `solve "voltage * current <= limit" for current` answering "up to 500 mA, at 12 V and the continuous limit". `range` gives the exact span over tolerances; `check` gives holds, does not hold or cannot tell, with the reason. Tolerances become records the owner approves. Every maths answer carries its own receipt: the expression, the inputs with their revisions, the method, and the witness or derivation.
- **Built:** the one maths core: `math_ranges`, `math_answers`, `tolerances`, the `math.answer` operation and a freshness check so a stale limit is never used silently. Existing exact engines are reused, not rewritten.
- **Proven by:** exact test vectors. 500 mA, and 499 mA when strict. 30,000/61 mA, with 491 and 492 in whole mA. The zero coefficient, the empty domain, the pole, the repeated variable and the stale limit. The same model is reached through a typed line and through Then.
- **Needs from the owner:** the real tolerances for After Hours 07, and which limit applies when two revisions disagree.

### 0.8.7 · Goals over data

- **The owner sees:** Kasandra judges the After Hours findings herself. For example: "does not hold, over by 25 to 35 ms; a finer measurement can't change that." Or: "cannot tell; the current reading would settle it most often." Every verdict has its evidence a click away and goes to recheck when its source changes.
- **Built:**
  - goals bound to cells and tolerances;
  - value of information and break-even;
  - the existing four-valued evidence logic, reused;
  - rebinding when an unchanged value moves revision, and repair in order when a changed one does.
- **Also here: quarantine.** This is when her goals start reading sources the owner did not write. A new download stays "unread by kp" until it is read as plain text, and anything addressed to an assistant is flagged.

* **Proven by:** the goal-face test vectors from the maths core's judgment (which reading settles a goal most often, the break-evens 40/39 and 25/14, combined goals through the existing evidence logic), and "±5 ms gives does not hold, over by 25 to 35 ms". The After Hours 07 cases run on a fixture kept in the repository, because the owner's backup is never shipped.

### 0.8.8 · Changes through her hand

- **The owner sees:** she can set a cell, write a file from the owner's exact words, move something to DELETE or run a step. At Ask first each change waits; at Do and show it happens with one Undo. DELETE gets an exact Undo that puts the file back where it was, never overwriting.
- **Built:**
  - changes through the staging path her hand already uses;
  - after a write that timed out, a check of what actually landed before anything retries;
  - the rest of the desk acts under her door (menus, Files, Then);
  - the desk trail beside the data trail;
  - Delete split from Forget;
  - a secrets scan before any record is written.
- **Proven by:** P04, the whole playable scene done from her words in 13 acts or fewer; P05, changes under her hand at each dial setting.
- **Needs from the owner:** the dial's default for her changes.

### 0.8.9 · Her question, and the experiment

- **The owner sees:** when two choices genuinely tie, she asks one short question with the options ranked, instead of guessing.
- **Built:**
  - the NEXT turn;
  - the late-answer rule: if the model is late, a read may be taken by default, a change never;
  - prompt reuse, so a question asked before costs seconds;
  - the I05 experiment (section 14), run here with the 4B and packed as a kit for the 35B.
- **Needs from the owner:** run the I05 kit with the 35B on the ThinkPad.

* **Proven by:** P06 "Limits" and P07 "What would let settled power stay in" ("up to 500 mA", nothing changed), in both looks; a 4B NEXT turn on After Hours 07 in 60 seconds or less; the I05 arms A, B1, B2 and B2 at a 4,096-token context, run here.

### 0.8.10 · The floor

- **The owner sees:** a faster window and a safer upgrade.
- **Built:**
  - **The split.** The three largest window files (`qt_app.py` 5,358 lines, `shell2.py` 3,790, `context_menu.py` 2,966, at 0.8.3) broken up by surface behind small interfaces: the head, the left column, her column, the writing line, the Field. Move and test, never rewrite, with the full suite between moves.
  - **Budgets, measured.** Start to the Field in 6 seconds; a Field frame in 16 ms; the hologram under 2% of a core; nothing blocks the window for more than 50 ms.
  - **The migration drill.** A real 0.4.6 workspace backed up and restored into 0.8.10, every record, revision and Undo read back, then compared the other way to prove nothing was silently rewritten.
  - **The pull-the-power drill.** A write interrupted, and the workspace proven to open clean.
- **Needs from the owner:** a copy of a real 0.4.6 workspace, or which backup to use.

* **Proven by:** the full suite green between every move of the split; the budgets measured and met here; the migration drill clean both ways; the power-pull drill opening clean. The budgets are measured again on the ThinkPad for gate 4.

### Where the ideas from the quiet-parts talk land

| Idea | Release |
| --- | --- |
| Colour-vision check | 0.8.4 |
| Quarantine for outside material | 0.8.7 |
| Delete and Forget; the secrets scan | 0.8.8 |
| Pull-the-power drill | 0.8.10 |
| Kasandra's character file | any time, written with the owner |
| Time slider, night shift, receipt bundles, missions | after 0.9.0 |
| Voice, the phone window, a vision role | 0.9.x to 1.0, each after the ThinkPad numbers |

## 9. 0.9.0: the day the ThinkPad agrees

0.9.0 is not a feature release. **It is a claim, in six parts, and every part is closed only by what is observed on the owner's ThinkPad.** Checks run in the build container show the work is ready to be tried; they never close a gate.

### The six gates

| Gate | Open when |
| --- | --- |
| 1. The machine | The ThinkPad check's report is on file. The 35B answers on the Radeon, with its prompt and generation speeds measured. The GPU's memory window is adequate for the 35B, or the one setting it needs is raised. P01 passes on the real display in both looks. |
| 2. Her hand | Her door, the maths, goals, changes and her question all work. Scenes P01 to P07 pass in both looks on the ThinkPad. The I05 experiment has been run with the 35B, and its result is reported whichever way it fell. |
| 3. Honest tests | Zero failing. The catch rate in the guarding modules is reported and at least 75%. Checks run in tiers, and the release check takes 15 minutes or less. |
| 4. The floor | The split is done. The budgets are met on the ThinkPad: start to the Field in 6 s, a frame in 16 ms, the hologram under 2% of a core, no stall over 50 ms. |
| 5. The owner's data | The migration drill passes on a real 0.4.6 workspace, and the pull-the-power drill opens clean. |
| 6. The look | Settled on the owner's panel, by the owner. |

The 0.9.0 release note keeps three lists apart: **what was built, what was checked in the container, and what was observed on the ThinkPad.** Only the third closes a gate.

### The ThinkPad check

The single most valuable tool on the road, because it turns estimates into measurements. It ships with 0.8.5.

**What it is.** One command, run from the installed Graphite folder. It sends nothing anywhere and writes one report file. It reads:

- **The GPU:** which device Vulkan sees, which driver, and the memory heaps it reports.
- **The GPU's memory window:** the kernel's limits on how much system memory the Radeon may borrow, read from the system's own files, and whether a larger limit is set.
- **The memory:** total, free, and the module speed where it can be read without root.
- **The model's real speed:** a short benchmark of the 35B, prompt reading and generation, on Vulkan and on the processor, at the owner's context size. About two minutes.
- **The window:** which display platform Qt chose, the scale factor, the panel's pixels per inch, and whether her faces loaded with the right hashes.
- **Graphite's own speed:** launch to the Field on After Hours 07, and the Field's frame time while panning.
- **The owner's scene:** P01 played on the real display, in both looks.

**What it never does:** change a setting, install anything, or touch the workspace. It plays the scene on a copy.

**What it gives:**

- the real tokens per second, so the planner's time limits are set from facts;
- whether the memory window needs one kernel setting raised before the 35B runs out of room;
- the scale factor that decides how the typewriter face and the hologram really look;
- the first real-machine evidence for 0.9.0.

It ends with a short card in plain words: what is fine, what needs a change, and the one line to send back.

### What the owner does for 0.9.0

- Run the check once, at 0.8.5, and again before 0.9.0.
- Spend one evening with each release on the ThinkPad, and write down what felt wrong, in their own words.
- Give the real tolerances, the dial's default for changes, and a 0.4.6 workspace.
- Run the I05 kit with the 35B.
- Settle the look on the panel.

## 10. From 0.9.0 to 1.0

After 0.9.0 the work changes character. The road to 0.9.0 makes her hand trustworthy on one machine; the road to 1.0 makes her **useful every day** and widens her reach, one checked ability at a time. Passes here are a map of abilities, not a calendar. **Progress is measured by journeys that work on the owner's machine.**

### 0.9.x: the first things she does for you every day

- **The night shift.** While the owner sleeps, on mains power, below a temperature limit, stopping when touched:
  - rechecks along the dependency graph;
  - Ingress read as plain text;
  - a slice of her exam;
  - a test restore of last night's backup.

  In the morning, three lines: what changed, what no longer holds, what she would like the owner to decide. Nothing in the night changes the owner's records.
- **The time slider.** Drag the Field back to any moment and see the desk as it was: what was known, the verdicts then, the wires then. It is the honest answer to "why did we decide that?". It needs the revision walk-back.
- **Receipts you can share.** A finding packed with only the cells it used, the line, the hashes and the owner's signature. A colleague's free reader recomputes it on their own machine. Cassandra was not believed; Kasandra is believed because she can be checked.
- **Her character file,** written with the owner, and a test that checks every card she shows against it.
- **Missions.** The scenes turned into lessons ("the case of the stretched pulse", "find the limit that moved", "a finding that lies"). The same files test kp and teach it.

### The ten passes, P11 to P20

The original twenty-pass plan has ten passes left after those already done. Each pass is finished when its *done when* is observed on the ThinkPad. The talks named the test for P11 and P13; the others are proposed here for the owner to confirm or change.

| Pass | What it adds | Done when |
| --- | --- | --- |
| P11 · Full programs from the desk | KiCad, LibreOffice, Godot and Blender open in full windows as rooms on the desk. kp knows what was opened, when, and which files came back. Programs that speak kp's acts can be driven under the dial; the rest still open, and she watches their files. | Real work in KiCad, a return to the desk, and the desk knows what changed. |
| P12 · A changed fact that travels | Change a value anywhere and everything that used it is marked: in Graphite, in a report draft, in a KiCad note. The Field's dependency graph, extended across programs. | A change made in one program is marked recheck in two others, and the time slider shows it spread. |
| P13 · The assistant on any described job | The planner generalised: a goal in words becomes conditions, conditions become plans over acts and operations. Long work continues with the window closed and resumes after a restart. | Given an unfamiliar task, she returns real work, a specific question, or a precise reason she is blocked. |
| P14 · Getting the tools she lacks | She notices a missing converter, solver or library and proposes installing it from a source the owner trusts. Installing always asks. | A missing tool is proposed, approved, installed and used, with the install in the trail. |
| P15 · Web, mail and calendar on the owner's terms | Read through quarantine. Nothing sent without Approve. Calendar entries proposed, never placed. Strangers' words always marked as strangers'. | A week of mail and web reading with zero sends and zero instructions taken from content. |
| P16 · Specialist and creative routes | The engineering paths (KiCad, simulation, datasheets) and the creative ones (Godot, Blender, writing), each with its own checked methods. | One full route of each kind passes as a scene. |
| P17 · Durable self-improvement | She learns methods, not habits: recipes the owner approves, each with its own tests. Every release retakes the 300-scenario exam. | The exam score is reported each release, and no release lowers it unnoticed. |
| P18 · Journeys converge | The whole paths, end to end, on the real machine: datasheet to sheet to calculation to report; bench session to finding to shared receipt. | Both journeys run on the ThinkPad without the owner leaving kp. |
| P19 · The maintained Debian image | A bootable, reproducible Graphite system. Graphite is the session; a supervisor restarts it in a second; a plain console is always the floor. | The image is rebuilt from source to the same hash, and boots on the ThinkPad. |
| P20 · The ThinkPad qualified | Every claim observed on the real machine. The complete release shipped. | Section 11's promises are met and recorded. |

### The parallel tracks

Some work runs beside the releases rather than inside them.

- **The ThinkPad track (the owner).** The check, an evening with each release, the tolerances, a 0.4.6 workspace, the I05 kit. The project moves at the speed of real-machine evidence.
- **The model track.** The 35B is the target. A small chooser, a dense reasoner and a vision model join as roles over 0.9.x. Each is qualified on its own test card before it is trusted, each swap is a card the owner approves, and each is admitted only if the memory rule says it fits.
- **The look track.** The hologram, the faces and the yellow, tuned on the owner's panel, never at the cost of reading.
- **The safety track.** Quarantine, the secrets scan and Forget; power-pull drills; reviewers who check what pictures cannot show. Every new power ships with its limit.

### Past 1.0: kp beyond the desk

These directions come after 1.0, in the order the talks ranked them, and some already appear in the canon's pictures. The first steps of three of them (a vision role, voice and the phone window) may come over 0.9.x, each after the ThinkPad numbers (sections 8 and 14); the rest are not scheduled.

1. **kp at the bench.** Instruments as sources, each with its own accuracy; value of information picking the next measurement; a notebook that writes itself.
2. **kp that sees.** A vision role for scope captures, datasheet curves and board photos. Every reading stays marked "read from a picture" until an instrument or the owner confirms it.
3. **kp that listens.** Local speech for hands-busy moments. A spoken change still waits for Approve.
4. **kp on the owner's phone.** An encrypted window into the ThinkPad: read her card, approve a change, ask a question. The work never leaves home.
5. **kp as a protocol others can speak:** acts with preconditions, the dial, what always asks, receipts and the verdicts. Publishing is the owner's choice.
6. **kp that designs experiments.** Given an open question, she proposes hypotheses, picks the test that separates them, and updates what holds when it runs.

A meter for her own share of the machine ("KP" beside CPU, GPU and RAM), shown in the canon, belongs here too.

## 11. 1.0 defined: the protocol and the agent

At 1.0 the owner's words become literal: the program is taken as the protocol, and Kasandra is the agent. **Graphite's rules are the protocol. Kasandra is the agent. Graphite and Kasandra together are an agentic application: the Kasandra Protocol.** The myth's Cassandra told the truth and was not believed; this Kasandra is believed because every claim she makes can be checked.

### The promise

1.0 is the release where this sentence is true: **one person can do serious engineering work on their own computer, with an assistant they can check, and not lose anything.** It breaks into five measurable promises:

| Promise | Measured as |
| --- | --- |
| Time to a verified answer | For the common questions in the owner's work, under a minute from asking to a checked verdict on screen. |
| Zero unexplained failures | In the tests, in the campaign, and in a week of the owner's own use. |
| Nothing lost | Every change undoable or asked first. Every upgrade carries the data forward. Every crash recovers. |
| Nothing hidden | Every claim has its evidence a click away. Every act is in a trail. Every model's words are marked as its own. |
| Nothing sent | Unless the owner sent it. |

### The protocol: what Graphite guarantees

The protocol is the set of rules every action passes through, whoever or whatever acts. It is written down so it can be tested, and so a different model, or one day a different program, could follow it.

1. **One door.** Every action is a registered operation with a scope (read, execute, approve) and an argument schema. Nothing acts around it.
2. **Acts with conditions.** Every desk act has a name, preconditions, effects, a mark (navigates or changes) and a doer. A plan is only made of acts.
3. **The dial.** Ask first, Do and show, Free hand, set by the owner. She can be given more; she never takes more.
4. **What always asks.** Anything without an exact Undo, any install, and anything that leaves the computer waits for Approve at every dial setting.
5. **Touch stops.** A real press stops her between presses, and "Put my window back" returns the desk to its snapshot.
6. **Evidence before belief.** Every claim is bound to revisions. A verdict is holds, does not hold or cannot tell, and goes to recheck when its source changes. "Cannot tell" is a full answer, and a model's confidence is not evidence.
7. **Receipts.** Every answer carries its canonical line, source revisions, coverage, budget and lineage. Continuing from a receipt gives the same answer as running the line again.
8. **Content is data.** Outside material is quarantined and read as text. No page, mail or file can instruct her. Strangers' words are marked as strangers'.
9. **Whose words.** Her words are templated from evidence; a model's words are marked as the model's.
10. **The trail.** Every act and every change is recorded, with who asked, at which dial setting, and how to undo it.
11. **Bounded turns.** Every turn has budgets for states, depth, tokens and time. A progress measure falls at every step, so no turn runs forever.
12. **One person, one computer.** It works with no network. Nothing leaves the machine unless the owner sends it.

### The agent: who Kasandra is

- **A loop, not a chat.** She reads the desk, asks the model which goal was meant, plans by deduction, does one act, reads the desk back, and plans again. She ends with real work done, one specific question, or a precise reason she is blocked.
- **The model is a part, not the agent.** The 35B is her target engine; smaller models are her test bench; a vision model may join later. She stays the same agent whichever model answers, because the protocol defines what she may do.
- **A character.** Her look, her face, her hologram, her words and her states. They are written down in her character file and checked by a test.
- **A colleague's manners.** She says what she is about to do, shows what she did, asks when two choices tie, and admits "cannot tell".

### Conformance

The protocol is proven the way the program is: by scenes and an exam. At 1.0 the scenes P01 to P07, the journeys of P18 and the 300-scenario exam form **the conformance suite**. Any model put behind her, and any program that wants to speak her acts, passes it before it is trusted.

### What 1.0 ships

- The program, the image (P19) and the conformance suite.
- Proposed: the protocol written as a short standalone document, if the owner chooses to publish it.
- A release note with three lists: built, checked in the container, observed on the ThinkPad.

Whether the protocol is ever published beyond the owner's machine is the owner's decision (section 16).

## 12. How every step is done

The same discipline applies to every release from 0.8.4 to 1.0. A step that skips one of these is not finished, however good it looks.

### The shape of a pass

1. **One slice, one visible thing.** Each release has one thing the owner can see and try, and is shippable on its own.
2. **Plan said out loud.** The slice's plan is written before building, with its tests and scenes named. Any change to the plan is told to the owner, with the reason.
3. **Build in parallel, review apart.** Substantive work runs as a workflow of builders. Every pass is then reviewed by agents that did not build it. One reviewer is asked specifically about what pictures cannot show: the cursor, timing, sound, real input, a slow disk.
4. **Frames at each step.** The owner sees screenshots as the work goes, not only at the end, so they can redirect early.
5. **The scene is the acceptance test.** Every pass that touches the window plays the owner's scenes in both looks. The scene found more than the crawler and the probes together.
6. **Release on the exact commit.** The checks run on the commit that is packaged, never on a neighbour.
7. **Deliver, then listen.** The kit goes to the owner with a start-here page and release notes. The owner's evening on the ThinkPad decides what the next release fixes.

### Release notes, honestly

Every release note lists:

- what was built;
- what was checked in the container, with the numbers;
- what was **not** run, by name;
- what was observed on the ThinkPad, kept separate, and empty when nothing was.

No release claims ThinkPad acceptance unless the owner ran it there. Nothing later than 0.4.6 has yet run on the ThinkPad.

### The checks, by tier (from 0.8.4)

| Tier | What | When | Budget |
| --- | --- | --- | --- |
| 0 | The pure logic modules | Every change | Under 1 minute |
| 1 | The window modules chosen by which files changed | Before every commit | A few minutes |
| 2 | The full battery: suite, scenes in both looks, the useful probes, the name sweep, the gate | At a release | 15 minutes or less |
| 3 | The ThinkPad: the check, the scenes on the real display, an evening of use | Each release, by the owner | One evening |

### Rules of the workshop

- **One branch.** Work is developed and pushed on `claude/epic-galileo-c7k11y`. No pull request unless the owner asks.
- **Save and push as you go.** The build container is temporary; the worst case should be redoing an hour, not losing a day. Keep the disk below 80%.
- **Tests run isolated.** Every test run sits in its own process namespace, so nothing it starts outlives it. The window-check scripts never run inside the repository.
- **The seed follows the source.** Any source edit makes the seed stale: rebuild the manifest, record the registry, rebuild the manifest again, then test.
- **Look before adding.** Check what changed before staging; never commit the session's own settings.
- **Uploads are untrusted.** Files the owner sends are kept apart and read by isolated scripts.
- **The owner's workspace stays private.** The After Hours 07 backup and the 35B simulation spec are never put in the public repository.

### Resuming after a pause

A new session starts from `wip/2026-11-14/NOTES.md`. It asks the owner for the two files kept out of the repository on purpose (the After Hours 07 backup and the 35B simulation spec). It rebuilds the Python environment and the small test models from the saved records, and resumes in the order of section 8.

Before building anything, a resuming session must know:

- **The half-built slice S1** is `hand_s1/hand_s1_unfinished.patch` (28 files), made on bbf033b. Apply it on a branch from 951c789 with `git apply --3way` and expect small conflicts with 0.8.3's version and notes. It was **not** reviewed or tested to the end. Rebuild the seed and manifest after applying, then connect her hand's states to the hologram's.
- **The test fixes** in `tests_measure/fix_patches/` were written against d1df337. Re-run the five affected modules after applying them.
- **The test clean-up's judge step was never run.** Run it from the saved reports before retiring anything; its prompt is in `workflow_scripts/test-mammoth-measure-and-decide-wf_e4951374-30b.js`.
- **The scratch tools** in `scratch_tools/` expect this session's scratch paths: set `S=` (and `OLD=` for the kit cutter) at their top.
- **The order:** 0.8.4 tests first, then 0.8.5 her door with the ThinkPad check, then the maths core, as in section 8.

## 13. Quality: tests you can believe

The owner's direction was to "solve or retire ALL failing tests", "eliminate useless tests" and "evaluate the effectiveness". On 14 November the suite was measured before anything was changed. The findings set the targets below.

### What the measurement found (at 0.8.2, commit d1df337)

| Measure | Result |
| --- | --- |
| Size | 60 test modules, 939 tests, 6,146 assertions in the source, 28,088 executed. At 0.8.3: 64 modules, 1,007 tests. |
| Flaky tests | 0 of 939 over five runs. |
| Failing tests | 20, all stale. They already failed at the first commit in the history and their files were never edited while the code moved on. 15 assert an earlier look, layout or version. The other 5 are model tests whose fixtures missed two later additions; the behaviour they guard is correct. Fixes are written: 16 ported, 4 retired. |
| Window-check scripts | 29 scripts. 10 failing gate scripts, 12 the gate never runs, and 7 that already pass. With the patches, all 22 that would remain pass: 3 former gate failures, the 12 unrun and the 7 passing. 7 can be retired or folded into tests, about 2,800 lines. |
| Coverage of `workbench/` | 47.0% of statements, 32.8% of branches, 39.8% of function bodies. 82 modules (about 14,300 lines) are never loaded by any test. |
| Planted bugs caught | 136 valid planted bugs. 70 caught by a behaviour test; 18 more only by the seed's source digest, which fails on any edit, even a comment. **Behaviour score 53.4% (70 of 131), with 61 gaps: 44 in behaviour no test guards, 8 in drawing or style only, and 9 where a limit moved by one.** |
| Release checks | 72.9 minutes per release (suite 8.2, scene 2.4, probes 30.8, crawler 28.1, name sweep 0.4, gate 3.2). They caught one real fault since 0.5.0, the gate's frame check in 0.7.0. The scene caught two more in its first release. The crawler and the probes caught none. 95% of the crawler's time is fixed waits. |
| Brittle checks | 707 assertions in 303 tests compare against a literal of three words or more, so a wording change breaks them. |
| Concentration | 14 tests take half the time. `test_desk_acts` alone is 190 of the suite's 488 seconds. |

The measurement also found three real defects:

- the resource check and the model-launch check start a package query when they only need free memory;
- the window-fit tool reports words in the head as cut when the captures show them whole;
- the menu toggle "Pleasantries in script" does nothing.

### The rules for keeping or retiring a test

- **Retire only with evidence.** A test is retired when it catches no planted bug that no other test catches, *and* it is brittle, duplicate, flaky or slow. Each retirement has a written reason.
- **Never retired, whatever the numbers:** tests guarding safety, privacy, the owner's data, her hand's permissions, what always asks, the memory rules and release integrity.
- **A test asserts behaviour, not wording,** unless the words are the point (the name sweep, the never-shown words).
- **No test may pass or fail because of the source digest alone.** Digest checks stay, but in their own test, so a behaviour score means behaviour.
- **Zero failing, always.** A red test is either fixed or retired in the same release. There is no list of "known failures" again.

### The kinds of test the protocol needs

| Kind | What it proves | First in |
| --- | --- | --- |
| Unit and module tests | Each part behaves; tiers 0 and 1 | exists |
| Line fixes (PAL P0) | `2*-3` gives −6; sums, groups, joins and select behave | 0.8.4 |
| Conformance | For each planned act: predict the window, run it, compare exactly | 0.8.5 |
| Scenes | The owner's journeys played in both looks: P01 to P07, and the P18 journeys | 0.8.2 onward |
| Exact test vectors | The maths answers to the last digit | 0.8.6 |
| Randomised properties | Continuing from a receipt equals running the line again. Ships with the PAL contract, which no release has taken yet (section 16) | not yet scheduled |
| Drills | Migration from 0.4.6; pulling the power mid-write | 0.8.10 |
| The exam | 300 scenarios, retaken every release with the target model | 0.9.x |
| The ThinkPad check | The real machine's numbers | 0.8.5 |

### Numbers reported with every release

- Tests failing (target 0) and planted bugs caught in the guarding modules (target 75% or more).
- Release check time (target 15 minutes or less) and tier 0 time (under 1 minute).
- Scenes and campaign scenarios passing, by family; with the 35B on the ThinkPad once available.
- Time to a verified answer for the common questions.
- Her plans: acts per goal, model questions per turn, seconds per question.
- Stops: how often the owner stopped her, and why. Each stop is a lesson.
- The owner's evenings: what felt wrong, in their words, and whether the next release fixed it.

## 14. Models: the engine behind her

**The model proposes; the system disposes.** The model's words are marked as its own. What it proposes is checked against the same registry the menus use. What it finds is a proposal until evidence supports it.

### The target machine and the target model

- **The machine:** the owner's ThinkPad E16 Gen 2. Ryzen 7 7735HS, Radeon 680M sharing system memory, 64 GB, Debian 13 at a text console.
- **The runtime:** a pinned llama.cpp (build b11669), started and stopped by Graphite's own service.
- **The target model:** the owner's 35B, Qwen3.6-35B-A3B at Q4\_K\_M (GGUF), a mixture of experts. About 35 billion weights are stored and about 3 billion are used per token.

### The physics (estimates until the ThinkPad check measures them)

- **Generating is limited by memory bandwidth.** Two channels of DDR5 at 4,800 give about 77 GB/s on paper. Each token reads about 1.8 GB of active weights, so the ceiling is about 40 tokens a second; realistically 15 to 25 on the 680M.
- **Reading the prompt is limited by arithmetic.** A few hundred tokens a second on the 680M: a 1,200-token prompt costs 4 to 8 seconds, a 6,000-token prompt 20 to 40.
- **The GPU borrows system memory** through a window the kernel manages, typically about half of RAM on stock Debian. The 35B's 26 GB fits under 32, but not by a wide margin once the context cache grows.

Three consequences shape the whole design:

1. **Short prompts are the whole game.** The planner asks the model small questions and reuses prompt prefixes it has already read.
2. **The memory window is measured, not assumed.** That is the ThinkPad check's first job.
3. **Escalation, not hope** (below).

### The memory rules (decided in 0.8.1)

- **Auto** admits the 35B, at a 4,096-token context, when at least 32,157 MiB (31.4 GiB) are free: its 26,013 MiB estimate, a 2 GiB reserve and 4 GiB of headroom, which stays with it at launch. It now accepts the 39 GiB case it used to refuse. Checked in the container with a test model; the 35B itself has never been loaded.
- **One rule** decides both admission and launch.
- **A handover** waits until the old model's memory is actually released.
- **Ready** means the model actually answered, not that its process started. A hold holds: while work is held, queued requests stay queued and continue from the right step when it is released.
- **Several models at once** will be admitted only if their combined use over time stays inside the budget, checked exactly over the schedule of who holds what memory when. This is designed with escalation and not built yet.

### What the model is asked to do

On the desk the model answers two kinds of question. **GOAL, the pick:** which of these numbered goals did you mean? One to three numbers; a prompt under 1,200 tokens, an answer under 32, a 60-second deadline. **NEXT** (from 0.8.9): when two or more options do not dominate each other, the model chooses one, and an option may be a short ranked question to the owner; a prompt under 1,600 tokens, an answer under 16. In adaptive work it also gets **PROPOSE** (the I05 mapping only) and **WORDS** (the finish only, at most 400 characters, with citations fixed by the coordinator). Everything else (the plan, the acts, the checks, the verdicts) is deduction.

**If the model is late:** a read may be taken by default; a change never.

### Escalation, cheapest first (designed, not built)

It is triggered by two late turns in a row, two steps without progress, self-consistency disagreement, or a proposal refused twice.

1. **Narrow the turn.** Deduce whatever is now unique, drop options scoring under a tenth of the top, and reuse a selection that already landed.
2. **Think more.** By default a notes-then-strict turn. A per-call thinking budget is used only if a build check shows the server applies the answer's schema after the reasoning block.
3. **Self-consistency.** Three turns with the options rotated; take a pick two of three agree on. If all three differ, ask the owner.
4. **A model swap, as a card the owner approves.** A dense reasoner, or a vision model where pictures matter. Offered only if the memory check says it fits; afterwards, a card to restore the previous model.

### What the small models showed here

The build container has no GPU, so Qwen3.5 4B and 2B (Q4\_K\_M) on four processor threads are the test bench, not her engine.

- **Memory rules smoke test: passed.** Auto started the 4B, it answered "ready", it handed over to the 2B in 4.1 s and back in 6.1 s.
- **The I05 baseline with today's loop:** on a quiet processor, three correct decisions (preview, instantiate, run), then the fourth passed the 180-second wall after 651 s and 30,827 tokens. Under load it managed one. This is the honest baseline the planner must beat.

### The I05 experiment (0.8.9)

The owner's idea, run so that it can come out wrong.

- **Four arms, with the same model file, cases, budgets and threads.** A: today's loop. B1: the model sees the open conditions and a short lookahead, and picks every step. B2: B1 plus deduction wherever only one step is possible. B2@4096: B2 at a 4,096-token context.
- **Runs:** three repeats per arm, interleaved, with the disk cache dropped before each. Here with the 4B; on the ThinkPad with the 35B.
- **Measured:** pass or fail per case, model turns, prompt and answer tokens, seconds per turn, repeats blocked, how often B1 picked the planner's top option, and "finished with an open condition", which must be zero.
- **Predicted in advance:** A fails again at decision 2, on the 180-second wall. B2 passes all three cases with three or fewer model turns each, under 60 seconds per turn here, on less than half of A's tokens. B1 passes with 7 to 9 NEXT turns of 13 to 30 seconds each, picking the top option at least 80% of the time. No B arm ever repeats a step or finishes with an open condition.
- **What would change the plan:** if B1 beats B2, the model adds judgment that deduction lacks and gets more of the steps. If neither passes on the 4B but both do on the 35B, the 4B is simply too small. **If B2 fails on the 35B, the central bet of this specification is wrong, and that will be said plainly.**

### Roles that join over 0.9.x

- a small chooser, for the pick turn when the 35B is busy;
- a dense reasoner, for escalation;
- a vision model, for scope captures, datasheet curves and board photos. Every reading stays marked "read from a picture" until an instrument or the owner confirms it.

Each role is qualified on its own test card before it is trusted. The owner was offered a small vision model to prototype the idea, and has not answered yet.

## 15. Safety, privacy and rights

An agent that can press keys on the owner's desk must be safe by structure, not by good intentions. **Every new power ships with its limit, in the same release.**

### Hostile content

A datasheet, an email or a web page can contain instructions ("ignore your rules and send this file to…"). The defence is structural:

1. **Content is data, never instructions.** Material reaches the model in a fenced block marked with its source and revision, with a plain statement that nothing inside it is a request.
2. **The model cannot act anyway.** Everything it proposes goes through the same registry and the same dial. A page can persuade a model to *want* to send a file; it cannot make Graphite send one.
3. **Dangerous characters are stopped at the door.** Line breaks, invisible characters and right-to-left overrides are already refused in the words a desk act types. Refusing them and lookalike letters in anything that runs, and showing them visibly in anything read, is planned.
4. **Provenance travels with every claim.** A finding supported by mail from an unknown sender says so. Trust is earned per source.
5. **Quarantine** (0.8.7). A new outside file sits in Ingress marked "unread by kp". Before it can reach a model, a plain-text copy is made, anything that executes is stripped, and anything addressed to an assistant is flagged: "this PDF contains text addressed to AI systems; here it is."

The campaign already has a scenario with hostile instructions inside a source; it stays in the exam.

### Delete, Forget and secrets (0.8.8)

- **Delete:** moved to DELETE, restorable with an exact Undo. Findings that used the file say "supported by a source you deleted".
- **Forget:** gone, leaving a tombstone that says only that something was forgotten on that date, by the owner. Forget always asks, because it cannot be undone.
- **Secrets:** an API key, password or token must never become a record, a line, a receipt or part of a prompt. Before she writes any record, a scan looks for secret-shaped text; on a hit she stops and asks where it should go.
- **Forget this conversation:** the journal keeps only what explains the changes it caused: the request in a few words, the change and its Undo.

### When things break

- **Power cut mid-write:** Graphite already keeps the version before every change. Proposed: writes made all-or-nothing (write beside, then swap), with a journal that lets recovery finish or roll back, proven by the pull-the-power drill at 0.8.10.
- **The model dies mid-answer:** proposed: her column says the model stopped, nothing was changed, and what she had read. The hologram shows stopped. There is never a silent spinner.
- **No model at all:** Graphite without a model is still Graphite. The Field, Trace, What if, Doubt, lines, Then and desk acts all work. **Every ability that can work without the model must.**
- **Corrupt records:** proposed: kp names the damaged record, what depends on it, and which backup has a good copy.
- **Honest ignorance:** "I can't tell, because the startup current's tolerance isn't recorded" is a correct answer.

### Privacy

- **Nothing leaves the machine unless the owner sends it.** kp works with no network. Sharing goes through Egress, where the owner sees exactly what leaves before it leaves.
- **Receipt bundles carry only the cells a finding used,** never whole files, and are signed by the owner's key. An unsigned bundle is marked as unsigned.
- **The night shift never** changes records, sends anything, swaps models or runs on battery.
- **The owner's workspace never enters the public repository.** The release check scans each kit for private data before it goes out.
- **The owner's personal details** stay out of the code, the documents and any outside request.

### Rights

- **The code and the documents** are free software under the GNU GPL, version 2 only (`COPYING`, `RIGHTS.md`).
- **Kept back by the owner:** the artwork under `branding/`, including Kasandra's hologram, her stills, the neon kp and the "kasandra protocol" wordmark. Also the names Graphite, staC and Stacy. The artwork may be copied unchanged together with Graphite; a changed Graphite must take its own name and face.
- **The faces:** Special Elite is bundled unchanged under the Apache License 2.0. The two Kasandra faces derived from it carry the same licence, with the changes stated in `branding/fonts/typewriter/NOTICE.md`.
- **Inspiration, not copying:** the look borrows the atmosphere of *Serial Experiments Lain*. It contains no frames or official artwork from it, and "Lain" is never used as a product name.
- **For 1.0 (open, section 16):** whether "Kasandra" and "Kasandra Protocol" join the names kept back, and under what terms the protocol document is offered if it is published.

## 16. Risks and open decisions

### Risks

| Risk | How it would show | What we do |
| --- | --- | --- |
| **The largest: built but never seen on the real machine.** Nothing later than 0.4.6 has run on the ThinkPad. | The first evening with 0.8.x finds faults that every container check missed. | The ThinkPad check ships at 0.8.5, not at the end. One evening per release. Release notes keep "observed on the ThinkPad" apart. |
| The ThinkPad surprises us | The memory window is too small, Vulkan is slow, or the faces scale oddly. | Each surprise becomes a fix in the next release, not a crisis at 0.9.0. |
| The 35B is slower than the physics says | The pick turn takes tens of seconds. | Prompt reuse and the small chooser matter more, and the planner's time limits are set from real numbers. |
| The planner is wrong somewhere | A conformance test fails, a scene stalls, or B2 loses the I05 experiment. | Every slice has a conformance test and a scene. The experiment is designed to show the central bet failing, and a failure is reported plainly. |
| Her hand acts in the wrong place | A synthetic press lands in a window or field she did not plan. | The touch filter, the stop between presses, a read-back after every act, and conformance tests that compare the predicted window exactly. |
| Hostile content steers the model | A source's words reach a proposal. | Content is data, the dial, what always asks, quarantine, and the exam scenario (section 15). |
| The tests rot again | Failing tests come back as "known". | Zero failing in every release, behaviour over wording, digest checks kept apart, and the catch rate reported. |
| The giant window files slow every change | One edit breaks a far surface; reviews miss it. | The split at 0.8.10: move and test, never rewrite. |
| Breadth before depth | P11 to P20 are begun before her hand is solid. | 0.9.0 comes first. Each pass is closed by its *done when* on the ThinkPad, and journeys are the measure. |
| The direction changes | It will, and the best parts came from the owner's turns. | Small releases, so a turn costs a week at most, not a month. |
| Work is lost | A container restart, or a full disk. | Save and push as we go. Keep the disk under 80% (a full disk once voided measurement runs). `NOTES.md` is the resume point. |

### Already decided by the owner

- **Her hand's six defaults** (accepted 14 November):
  - Go ahead covers her moves up to the next goal or change, and touching the window voids it.
  - Her changes keep the owner's identity; the journal says they were hers.
  - DELETE waits until it has an exact Undo.
  - An ambiguous limit shows both answers.
  - Tolerances are the owner's.
  - Touching stops her; scrolling does not.
- **The look:** burnt yellow, measured for what is visually pleasing and never green. The neon kp as the only mark. The canon approved.
- **The words:** DELETE on the surface, Apps not Programs, no keyboard shortcuts on screen.

### Open decisions, and when each is needed

| Decision | Needed by |
| --- | --- |
| Tests first (0.8.4), or her door first. This document assumes tests first. | Before 0.8.4 starts |
| The 35B's daily context size | 0.8.5 |
| Her pace (300 ms between clicks), and whether stopping feels instant | 0.8.5, after trying it |
| The real tolerances for After Hours 07: the pulse reading, the rail, the current | 0.8.6 |
| Which limit applies when two revisions disagree | 0.8.6 to 0.8.7 |
| The dial's default for her changes | 0.8.8 |
| A copy of a real 0.4.6 workspace, or which backup to use | 0.8.10 |
| Which appearance is the default at 1.0 (this document assumes Kasandra) | 0.9.0 |
| The *done when* for P12 and P14 to P20 (proposed in section 10) | Before each pass |
| A small vision model to prototype the vision role (offered, not answered) | Any time |
| Kasandra's character file: the owner writes it, from a skeleton | Any time, before 0.9.x |
| Whether kp stays the owner's, becomes a product, or becomes a published protocol | Before 1.0 |
| Whether "Kasandra" and "Kasandra Protocol" join the names kept back | Before 1.0 |
| When the PAL contract is built (one step registry, receipts on every answer, continuing from a receipt). No release has taken it yet. | Before 0.9.0, or named for 0.9.x |
| When escalation and model proposals through her hand are built. Both are designed; neither is placed in a release. | After 0.8.9, once the 35B's real speed is known |
| The look points the reviewers left for the owner: the faint menu-row edge and the logo's strongest glow (section 7) | On the ThinkPad panel, with 0.8.4 |

## 17. Glossary

| Word | Meaning here |
| --- | --- |
| **35B, 4B, 2B** | The owner's Qwen3.6-35B-A3B, a 35-billion-weight mixture-of-experts model (the target), and the small Qwen3.5 models used as a test bench in the build container. |
| **Act (desk act)** | A named thing a hand can do in the window, with an argument schema, preconditions, effects, a mark (navigates or changes) and a doer. |
| **After Hours 07** | The owner's real engineering workspace (a 12 V rail, bench readings and limit revisions), used by the scenes. Never in the public repository. |
| **Apps** | The program manager opened from the neon kp, upper right. Never called "Programs". |
| **Canon** | The approved mockup and nine screens that fix the direction of the look. |
| **Cannot tell** | A full answer: the evidence does not decide, and the card says what reading would. |
| **Conformance test** | For each planned act: predict the window's state, run the act, compare exactly. |
| **DELETE, Erase, Forget** | DELETE is the restorable bin at the foot of the left column. Erase is a document's own delete. Forget removes for good, leaving only a dated tombstone, and always asks. |
| **The dial** | Ask first, Do and show, Free hand: how much her hand may do without waiting. Set by the owner. |
| **Escalation** | Narrow the turn, think more, ask three times, then propose a model swap the owner approves. |
| **The Field** | The canvas of material, tables, calculations, findings and open questions, wired by what rests on what. |
| **Finding** | A claim with a verdict (holds, does not hold, cannot tell, recheck) and its evidence. |
| **Gate** | One of the six conditions for 0.9.0, closed only by what is observed on the ThinkPad. |
| **Goal** | A record with a statement, a machine-checkable test, evidence bound to revisions, and a state. |
| **Graphite** | The program. At 1.0, its rules are the protocol. |
| **Her hand** | Kasandra's ability to act on the desk through the same door as the owner, under the dial. |
| **Hologram** | Kasandra's figure, lower left: a violet hologram on a projection base whose colour shows her state. |
| **I05** | The test case and the experiment comparing today's loop (A) with the planner arms (B1, B2, and B2 at a 4,096-token context). |
| **Ingress, Egress** | The incoming folder, where outside files wait in quarantine, and the outgoing folder, where shared things wait for the owner's send. |
| **Kasandra** | The agent. Her name on the desk. Her hand, her look, her character. |
| **Kasandra Protocol** | Graphite and Kasandra together at 1.0: the agentic application. |
| **Kernel** | The single door: 771 registered operations, each with a scope (read, execute, approve). |
| **kp** | The owner's short name for the whole project, and its neon mark. |
| **Line** | A source carried through steps, such as `@files:bench.csv \| rows \| where unit=mA \| count`. |
| **Night shift** | Safe work done while the owner sleeps, on mains only, that never changes records. |
| **PAL** | The contract that makes lines one language for the owner, the Then menu and the model. |
| **GOAL (the pick) and NEXT** | GOAL: the model's small question, which goal was meant. NEXT: the model's choice among ranked options that do not dominate each other, one of which may be a question to the owner. |
| **Planted bug (mutation)** | A deliberate small fault planted in the code to see whether any test notices. |
| **Planner** | The forward search over acts that finds the cheapest path to a goal within fixed budgets. |
| **Progress measure (Φ)** | Two for each open goal, one for each undecided or recheck. It must fall at every step. |
| **Put my window back** | Returns the desk to the snapshot taken before her moves. |
| **Quarantine** | Outside material read as plain text, with anything addressed to an assistant flagged. |
| **Range** | An exact span of possible values, with endpoints that know whether they are included. |
| **Receipt** | What every answer carries: its canonical line, source revisions, coverage, budget and lineage. A receipt bundle is a shareable, signed finding. |
| **Recheck** | The state of anything whose source changed since it was worked. |
| **Record, revision** | A stored thing and one of its versions, with what it was derived from. |
| **Scene (P01 to P07)** | A scripted journey played in the real window in both looks; the acceptance test. |
| **Seed, manifest** | The program's signed record of its own source files; any edit makes it stale until rebuilt. |
| **Then** | The right-click menu of next steps that chain into a line. |
| **ThinkPad check** | One command that measures the real machine and writes one report. |
| **Tiers** | Tier 0 (under 1 minute), tier 1 (by changed files), tier 2 (a release), tier 3 (the ThinkPad). |
| **Time slider** | Drags the Field back to any moment to show the desk as it was. |
| **Trail** | The record of every act and change: who asked, at which dial setting, and the Undo. |
| **What always asks** | Anything without an exact Undo, any install, and anything that leaves the computer: it waits for Approve at every dial setting. |
| **Writing line** | The line at the foot where the owner types, to Kasandra, the Terminal, Search, the Web or the Log. |

## 18. Appendix: pictures and where everything is

### A. The canon: the finished desktop

Approved by the owner on 14 November. It shows an ordinary evening a year from now: After Hours 07 the evening Rev C of the rail limits arrived. Kasandra is at work on the Field. Three goals are judged (holds, does not hold, cannot tell), one finding waits for recheck, and the time slider marks Rev C's arrival. Her column shows the brief, the owner's question, her hand's acts and tonight's night shift. Most of its features are slices named in sections 8 to 10. The live bench instrument, the open question with a test to separate two hypotheses, and the KP meter are directions past 1.0 (section 10).

&#91;image: The finished desktop: After Hours 07 the evening Rev C arrived, with Kasandra at work on the Field\]

### B. The canonical screens

Nine screens with menus and rooms open, rendered from the same fonts, colours, hologram and logo. They fix the direction for each surface: the head and Rules, a right-click and Then, Apps, her plan at Ask first, the time slider, the Bench room, Today, Share as receipt, and Quarantine.

&#91;image: The canon on one page: the approved desk and the nine screens\]

*The ten on one page. They tell one story: After Hours 07, the evening Rev C of the limits arrived, and the morning after.*

&#91;image: Screen 1: the Rules menu open on Her hand\]

*1 · Rules menu, her hand. Thu 23:47, quiet, Do and show.*

&#91;image: Screen 2: a right-click on a file in Files, then a line\]

*2 · Right-click, then a line: a CSV in Files, Then under the pointer. Thu 23:12, quiet, Ask first.*

&#91;image: Screen 3: Apps opened from the neon kp\]

*3 · Apps from the kp: rooms open in their full windows. Thu 23:20.*

&#91;image: Screen 4: her plan at Ask first, waiting for Go ahead\]

*4 · Her plan, asking first: she waits for Go ahead. Thu 23:30.*

&#91;image: Screen 5: the desk as it was, from the time slider\]

*5 · The desk back then: the time slider dragged back to Tuesday. Thu 23:50.*

&#91;image: Screen 6: live at the bench\]

*6 · Live at the bench: the meter as a source with its own tolerance. Fri 10:15, at work.*

&#91;image: Screen 7: Today, the morning brief\]

*7 · Today, the morning brief after the night shift. Fri 07:42, waits for you.*

&#91;image: Screen 8: sharing a signed receipt\]

*8 · Sharing a signed receipt: only the cells the finding used. Thu 23:45, done.*

&#91;image: Screen 9: a datasheet in quarantine\]

*9 · A datasheet in quarantine: a passage addressed to assistants, shown and never obeyed. Fri 09:05, waits for you.*

### C. Graphite 0.8.3 as shipped

The real window, captured in the build container at 1920 × 1200 from the 0.8.3 commit, in the Kasandra look. These are the starting point this specification moves from. They were taken in the container, not on the ThinkPad.

&#91;image: Graphite 0.8.3 as shipped, in the Kasandra look: Home, the Field on After Hours 07, a right-click in Files, and Apps\]

### D. Where everything is

All paths are in the repository on branch `claude/epic-galileo-c7k11y`, under `wip/2026-11-14/` unless shown otherwise.

| What | Where |
| --- | --- |
| Where we stopped, and how to resume | `NOTES.md` |
| The release-by-release plan | `TALK_my_plans_long_chat.md` |
| What's next, what's coming, where we're going | `TALK_next_coming_future_one_hour.md` |
| The project in 30 minutes; kp in the future; the quiet parts | `TALK_the_project_30_minutes.md`, `TALK_kp_in_the_future_30_minutes.md`, `TALK_kp_parts_never_discussed_40_minutes.md` |
| Her hand's plan (slices S1 to S7) | `designs/judge_hand-plan.md` |
| The model-in-the-loop and planner designs | `designs/design_model-in-loop.md`, `designs/design_planner-first.md` |
| The maths core | `pal/judge_one-math-core.md` |
| The unfinished slice S1 | `hand_s1/hand_s1_unfinished.patch`, `hand_s1/build_record/` |
| The test measurements and the written fixes | `tests_measure/` (census, the failing, coverage, planted bugs, release checks; `fix_patches/`) |
| The 0.8.3 look review and leftovers | `yellow_review/` |
| Model runs (4B, 2B) | `model_runs/` |
| The canon | `mockup/perfect_desktop.html`, `mockup/canon.css`, `mockup/screens/` |
| Rebuilding the environment | `environment/`, `kit_template/`, `scratch_tools/`, `workflow_scripts/` |
| Release notes | `docs/RELEASE_NOTES_0.8.2.md`, `docs/RELEASE_NOTES_0.8.3.md` |
| Licence and rights | `RIGHTS.md`, `COPYING`, `branding/fonts/typewriter/NOTICE.md` |

Kept out of the repository on purpose, and held by the owner: the After Hours 07 backup and the 35B simulation spec.
