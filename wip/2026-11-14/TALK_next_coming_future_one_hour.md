# What's next, what's coming, and where we're going

*An hour, 14 November 2026, at Graphite 0.8.3. It ends with a mockup of the finished desktop
(`wip/2026-11-14/mockup/Graphite_finished_desktop_mockup.png`).*

---

## 0:00 · Three horizons

I'll talk in three horizons, because each needs a different kind of thinking:

- **What's next** is the next three releases. It's engineering: specific files, specific tests, specific proofs. I can tell
  you almost exactly what each contains.
- **What's coming** is the road to 0.9.0 and the releases just after. It's architecture: how the pieces fit, what has to
  be true on your ThinkPad, what order the risks get retired in.
- **Where we're going** is 1.0 and beyond. It's direction: what kp is for, what it must never become, and what "finished"
  would look like.

Then I'll show you that finished desk, as a picture.

One principle runs through all three horizons, so let me say it once at the start: **she proposes, the system checks, you
decide.** Every plan below is a way of making that sentence true in more places.

---

# PART ONE · WHAT'S NEXT

## 2:00 · Where we left it

0.8.3 is on your phone: the hologram, her typewriter face, DELETE, burnt yellow, the neon kp. Three pieces of work are
saved and waiting:

- her hand's first slice (half built);
- the test clean-up (measured, with fixes written);
- the maths core (designed and verified).

The measuring changed the order:
- all twenty failing tests turned out to be stale, with fixes ready;
- the tests catch about half of the planted bugs;
- the release checks cost an hour and have caught almost nothing.

So the next release is about tests, and her hand follows.

## 4:00 · 0.8.4 · Tests you can believe

**Why first.** A test suite is a promise: red means broken. Ours has broken that promise for weeks: twenty reds that meant
nothing, and a window gate stuck at the same score since before we started. A red that means nothing trains everyone to
ignore red. Before we build her door, which is the riskiest code ahead, the reds have to mean something again.

**What's in it:**
1. **The twenty, resolved.** Sixteen tests rewritten to check what you actually want today; four retired, each with a
   one-line reason in the history. The five model tests matter most: they guard "a failed activation restores the
   previous model" and "a cancel stays cancelled", exactly what her model swaps will rely on.
2. **The window gate made honest.** Twenty-nine window-check scripts:
   - seven retired or folded into tests, about 2,800 lines gone;
   - the rest fixed or ported, so every remaining script passes.
3. **The line bugs PAL found,** each pinned by a test:
   - `2*-3` gives −6;
   - sums stop skipping numbers written as text;
   - true and 1 stop sharing a group;
   - joins stop overwriting fields;
   - `select title, state` with a space works.
4. **The blind spots.** Wherever a planted bug survived in code that guards you (permissions, her hand, the memory
   rules, the release check), a test that would have caught it. Target: three-quarters of planted bugs caught in those
   modules, up from about half.
5. **Faster checks:**
   - *tier 0*, under a minute, on every change;
   - *tier 1*, only what a change touched, before every commit;
   - *tier 2*, the full release battery, cut from 73 minutes to about 15, by retiring the checks that duplicate others
     or have never failed, and moving what the probes really check into the main tests.
6. **The yellow leftovers:** warm glows instead of grey, lists using the highlight, the PDF highlight as an edge, the Run
   button's focus in yellow.
7. **A colour-vision check.** Every pair of meaning colours is simulated for weak red and weak green vision, and every
   meaning also gets a word or a shape.

**How you'll know it worked:** the release notes will say "0 failing" for the first time, and the planted-bug catch rate
will be reported before and after.

## 9:00 · 0.8.5 · Her door on the Field

**What you'll see.** You type, *"trace the bench readings and put the limits side by side."*
- The hologram goes to "at work".
- A small ring appears where she's about to click.
- The Field comes forward, the sheet is selected, the trace crystallizes, and Rev A slides in beside Rev B.
- Her card lists the goals, each lighting up as it's met, and the acts, each ticking off.
- When she's done, she puts away what she opened.
- Touch the mouse, and she stops before her next click. "Put my window back" undoes her moves.

**How it works.** Already designed, half built and saved:
- **What the model does:** it gets one small question, which of these numbered goals did you mean, and answers with one
  to three numbers. Under 1,200 tokens of prompt, so seconds on your 35B.
- **What deduction does:**
  - every desk act has preconditions and effects;
  - a search finds the shortest sequence of acts from where the window is now to where the goal says it should be,
    bounded at 4,096 states and twelve acts;
  - she does one act, reads the window back, and plans again.
- **Why it can't run away:** a progress measure must fall at every step, so a turn cannot run forever.
- **Stopping:** a real press on the window comes through the window system; her synthetic presses don't. That's how she
  knows it's you, and she stops between presses, never halfway through a click.

**Scope.** In this slice she only moves; she changes nothing. Changes come three releases later, once the maths and the
goals are in place.

**The ThinkPad check ships with it.** One command that tells us, about your machine:
- how much memory the Radeon can borrow;
- how fast your 35B really reads and writes;
- what scale factor the window chose;
- how fast Graphite starts.

It sends nothing and changes nothing. It's the most valuable two minutes you can give the project.

**Proven by:**
- P02 (her door) and P03 (you take the window back), in both appearances;
- P01 unchanged;
- each planned act's predicted effect matching the window exactly;
- the 4B answering three requests correctly in under a minute each.

## 15:00 · 0.8.6 · Maths in lines

**What you'll see.** Lines that answer engineering questions exactly:
- `solve "voltage * current <= limit" for current` → *"up to 500 mA, at 12 V and the continuous limit"*. In whole
  milliamps with a strict limit, 499.
- `range` over your tolerances → the exact span.
- `check` → holds, does not hold, or cannot tell, with the reason.

**What's under it.** One maths core, shared by lines and by her goals:
- exact fractions in base units, never floating point where it matters;
- endpoints that know whether they're included;
- integer steps respected;
- the dependency trap avoided (x minus x is zero, not a range);
- a division whose range crosses zero becomes an obligation, never a silent infinity.

Your tolerances become records that only you set, each waiting for your Approve. A limit whose source moved is refused,
not used. Every answer carries a receipt: the expression, the inputs with their revisions, the method, and the witness or
derivation.

**Proven by:** the draft's numbers as exact tests (500, 499, 30,000/61, 491 and 492), the edge cases, and the same model
answered the same way through a typed line and through Then.

---

# PART TWO · WHAT'S COMING

## 19:00 · 0.8.7 to 0.8.10: the rest of the road to 0.9.0

**0.8.7 · Goals over data.** She judges your findings herself:
- The startup pulse with ±5 ms: *does not hold, over by 25 to 35 ms, and a finer measurement can't change that.*
- Startup power against 8 W: *cannot tell; the current reading would settle it most often.*
- Each verdict goes to "recheck" when its source changes, and rebinds silently when the change didn't touch what it used.

Quarantine for outside material lands here, because her goals start reading sources you didn't write.

**0.8.8 · Changes through her hand.**
- She can set a cell, write a file from your exact words, DELETE, and run a step, each at your dial.
- DELETE gets an exact Undo that never overwrites, and the Delete/Forget split.
- After any write that timed out, she checks what landed before anything retries.
- She scans for anything secret-shaped before writing a record.
- Your playable scene runs entirely from her words, in thirteen acts or fewer.

**0.8.9 · Her question, and your experiment.**
- When two choices genuinely tie, she asks one short question with the options ranked.
- A late model answer may let a read go ahead by default; never a change.
- The I05 experiment runs here with the 4B, and ships as a kit for your 35B:
  - three arms, three repeats each, with the predictions written down before the runs;
  - if my central bet fails, the experiment will say so.

**0.8.10 · The floor:**
- The three largest window files split by surface, moved and tested, never rewritten.
- Performance budgets measured:
  - start to the Field in 6 seconds;
  - a Field frame in 16 milliseconds;
  - the hologram under 2% of a core;
  - nothing blocking the window for more than 50 milliseconds.
- A migration drill: your real 0.4.6 workspace carried forward, every record read back both ways.
- A power-cut drill: a write interrupted, and the workspace opens clean.

## 24:00 · 0.9.0: the day the ThinkPad agrees

0.9.0 isn't a feature release. It's a claim, and the claim has six parts, each tested on your machine:

1. **The machine:** the check's numbers on file, the memory window adequate, your scene passing on the real display.
2. **Her hand:** her door, the maths, goals, changes, her question; all scenes passing in both appearances.
3. **Honest tests:** zero failing, the catch rate reported, checks in tiers.
4. **The floor:** the split done, the budgets met on the ThinkPad.
5. **Your data:** the migration drill passed on a real 0.4.6 workspace.
6. **The look:** settled on your panel, by you.

The release notes will separate three things clearly: what was built, what was checked here, and what was observed on the
ThinkPad. Only the third closes a gate.

## 27:00 · The 0.9.x releases: the first things she does for you every day

After 0.9.0, I'd spend a few releases on the features that turn kp from impressive into daily:

- **The night shift.** While you sleep, on mains, below a temperature, stopping when you touch:
  - rechecks along the dependency graph;
  - Ingress read as plain text;
  - a slice of her exam;
  - a test restore of last night's backup.

  In the morning, three lines: what changed, what no longer holds, what she'd like you to decide.
- **The time slider.** Drag the Field back to any moment and see the desk as it was: what you knew, the verdicts then,
  the wires then. It's the honest answer to *"why did we decide that?"*
- **Receipts you can share.** A finding packed with only the cells it used, the line, the hashes and your signature. A
  colleague's free reader recomputes it on their machine: Cassandra believed because she was checked.
- **Her character file,** written with you, and a test that checks every card she shows against it.
- **Missions.** Your scenes turned into lessons: *the case of the stretched pulse; find the limit that moved; a finding
  that lies.* The same files test kp and teach it.

## 31:00 · The twenty-pass plan, made concrete

The plan document lists ten passes after the ones we've done. Here's what each means in kp terms, in the order I'd take
them:

- **P11 · Full programs from the desk.** KiCad, LibreOffice, Godot and Blender open in their full windows as rooms on
  your desk. kp knows what you opened, when, and which files came back. Programs that speak kp's acts can be driven
  under the dial; the rest still open, and she watches their files. *Done when* you can do real work in KiCad, come back,
  and the desk knows what changed.
- **P12 · A changed fact that travels.** Change a value anywhere and everything that used it is marked: in Graphite, in a
  report draft, in a KiCad note. The dependency graph we built for the Field, extended across programs. With the time
  slider, you can see the change propagate.
- **P13 · The assistant on any described job.** The planner, generalised:
  - a goal you describe in words becomes conditions;
  - conditions become plans over acts and operations;
  - long work continues while the window is closed and resumes after a restart.

  *Done when* she can take an unfamiliar task and come back with real work, a specific question, or a precise reason
  she's blocked.
- **P14 · Getting the tools she lacks.** She notices she needs something (a converter, a solver, a library) and proposes
  installing it, from a source you trust, under what always asks. Installing is never hers alone.
- **P15 · Web, mail and calendar on your terms.**
  - Read through quarantine.
  - Never sent without your Approve.
  - Calendar entries proposed, not placed.
  - Strangers' words are always marked as strangers'.
- **P16 · Specialist and creative routes.** The engineering paths (KiCad, simulation, datasheets) and the creative ones
  (Godot, Blender, writing), each with its own checked methods.
- **P17 · Durable self-improvement.**
  - She learns methods, not habits: recipes you approve, with their own tests.
  - Every release retakes the 300-scenario exam, so you see if anything got worse.
- **P18 · Journeys converge.** The whole paths, end to end, on the real machine: datasheet to sheet to calculation to
  report; a bench session to a finding to a shared receipt.
- **P19 · The maintained Debian image.** A bootable, reproducible Graphite system:
  - Graphite is the session;
  - a supervisor restarts it in a second;
  - a plain console is always the floor.
- **P20 · The ThinkPad qualified.** Every claim observed on the real machine; the complete release shipped.

That's the road to 1.0. Passes are a map of abilities, not a calendar. Progress is measured by journeys that work on your
machine.

## 38:00 · The parallel tracks

Some work runs beside the releases rather than inside them:

- **The ThinkPad track (you).** The check, an evening with each release, your tolerances, a 0.4.6 workspace, the I05
  kit. The project moves at the speed of real-machine evidence.
- **The model track.** Your 35B is the target. The small chooser, a dense reasoner and a vision model join as roles over
  0.9.x, each qualified on its own test card before it's trusted, each swap a card you approve, each admitted only if the
  memory rule says it fits.
- **The look track.** The hologram, the faces, the yellow: tuned on your panel, never at the cost of reading. A "tired
  eyes" setting, a click on the hologram to calm the motion, and words beside every colour.
- **The safety track:**
  - quarantine, the secrets scan and Forget;
  - pulling the power in drills;
  - reviewers who check what pictures can't show.

  Every new power ships with its limit.

---

# PART THREE · WHERE WE'RE GOING

## 41:00 · What 1.0 means

1.0 is the release where I'd be comfortable saying: **one person can do serious engineering work on their own computer,
with an assistant they can check, and not lose anything.**

That breaks into measurable promises:
- **Time to a verified answer:** for the common questions in your work, under a minute from asking to a checked verdict
  on the screen.
- **Zero unexplained failures:** in tests, in the campaign, in a week of your use.
- **Nothing lost:** every change undoable or asked first; every upgrade carrying your data forward; every crash recovered.
- **Nothing hidden:** every claim with its evidence a click away; every act in a trail; every model's words marked as
  its own.
- **Nothing sent:** unless you sent it.

## 44:00 · kp beyond the desk

Past 1.0, the directions from the earlier talks, ordered by what I believe matters most:

1. **kp at the bench.**
   - Instruments as sources, with their own accuracy.
   - Value of information picking the next measurement.
   - A notebook that writes itself.

   This is where your work lives, so it's where kp should grow first.
2. **kp that sees.** A vision role for scope captures, datasheet curves and board photos. Every reading is a proposal,
   marked as "read from a picture", until an instrument or you confirms it.
3. **kp that listens.** Local speech for hands-busy moments. The same rules: a spoken change still waits for your Approve.
4. **kp on your phone.** An encrypted window into the ThinkPad: read her card, approve a change, ask a question. The work
   never leaves home.
5. **kp as a protocol.** The rules written down so other programs and other assistants can speak them:
   - acts with preconditions;
   - the dial;
   - what always asks;
   - receipts;
   - three-valued verdicts.

   Whether to publish is your choice.
6. **kp that designs experiments.** Given an open question, she proposes hypotheses, picks the test that separates them,
   and updates what holds when you run it.

## 48:00 · What must never change

Every direction above is optional. These aren't:

- **One person, one computer they own.** If kp ever needs the cloud to work, it has stopped being kp.
- **Evidence before belief.** A model's confidence is not evidence. "Cannot tell" is a full answer.
- **The dial in your hand.** She can be given more, never take more. What can't be undone always asks.
- **Content is data.** No page, email or file can instruct her.
- **Her words are templated from evidence; the model's words are marked as the model's.**
- **Readable before beautiful,** and beautiful anyway.

## 51:00 · How we'll measure progress

Not by features, but by these numbers, reported every release:
- tests failing (target: 0) and planted bugs caught in critical modules (target: 75% or more);
- release check time (target: 15 minutes or less);
- campaign scenarios passing, by family, with your 35B on the ThinkPad;
- time to a verified answer for the common questions;
- her plans: acts per goal, model questions per turn, seconds per question;
- stops: how often you stopped her, and why (each stop is a lesson);
- your evenings: what felt wrong, in your words, fixed in the next release.

## 54:00 · The perfect finished desktop

Let me close with the picture. I've rendered a mockup of what the finished desk could look like on a normal evening
in a year. It's made from the real fonts, colours, hologram and logo; the features are the ones on the road above. Here's
what you're looking at, in reading order.

**The head:**
- the eight menus, Work lit;
- the equalizer in the middle;
- "on mains · 23:41";
- your neon kp in the corner.

**The left column:**
- the Files tree, with the rail project selected in burnt yellow;
- a quiet note that Ingress holds one new file, unread by kp;
- Kasandra's hologram on a cyan base, because she's at work, with her scan lines and a tear crossing her face, and a
  caption: "at work · her hand on the Field";
- DELETE in red at the foot.

**The Field, After Hours 07, the evening Rev C arrived:**
- **Material:**
  - the bench readings;
  - *a live bench meter* reading the startup current with its own tolerance;
  - Rev C, marked new and quarantined.
- **Tables:** the bench readings with your ±5 ms; Rev B archived; Rev C current, ringed in yellow because she's just
  selected it, with her cyan ring showing her next click.
- **Calculations:**
  - settled power, exact (3.36 W, 84/25);
  - startup power as an attained range;
  - a solved ceiling, 500 mA at 12 V.
- **Findings, each with its verdict badge:**
  - holds (settled draw);
  - *does not hold* (the pulse over Rev C by 5 to 15 ms, "whatever the true value");
  - *cannot tell* (startup power, "the current reading settles it most often");
  - *recheck* (a finding whose source moved).
- **Open:** "What stretched the startup pulse? Two hypotheses; a test separates them."
- **Below the Field, the time slider:** from Tuesday to now, with Rev C's arrival at 14:02 marked in pink.
- **The Field's foot:** the selected finding, its buttons (Trace, Doubt, Range, Check, What if, *Share as receipt*), and
  the line that produced it, with its receipt and "coverage complete".

**Her column:**
- **The top:** "Kasandra" with a cyan cursor, "at work", and "35B · local · on the Radeon · does and shows".
- **While you were away:** Rev C arrived, two findings went to recheck, last night's backup restored clean.
- **Your question,** in violet: *"what changed in Rev C, and does the startup pulse still fail?"*
- **Her hand card:**
  - three goals, met, not met and undecided;
  - five acts, four done and the fifth, putting the desk back, next;
  - Stop and Put my window back;
  - the cost: "5 acts · 3 goals · 2 model questions, 9 s", and the sources.
- **Tonight, on mains only:** 02:00 recheck, 02:20 read Ingress as text, 03:00 her exam, 04:00 test last night's backup;
  "nothing changes your records · stops when you touch."
- **At the foot:** "listening · say 'Kas' or type".

**The writing line:**
- the five names, Kasandra lit;
- "prompt", in her fixed-width face;
- the red arrow;
- the meters, including a new one: **KP 18%**, her share of the machine.

Everything in that picture follows from the plan in this hour. None of it is magic: each piece is a slice we've named,
with a test that says it works. That's what "finished" means here: not a moment when the work stops, but a desk where
every claim on the screen can be checked, every act can be stopped, and every evening's work survives into the next.
