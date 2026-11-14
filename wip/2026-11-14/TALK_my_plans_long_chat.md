# My plans, in a long chat

*14 November 2026, at Graphite 0.8.3. Everything below is saved in `wip/2026-11-14/`.*

---

## Where we stand, and what today taught me

0.8.3 is out: the hologram, her typewriter face for every word, DELETE, burnt yellow, the neon kp. Three pieces of work
are paused and saved: her hand's first slice, the test clean-up, and the maths core design.

Before I tell you the plan, here's what I learned today, because it changes the plan.

**1. The twenty failing tests were never bugs.** The measuring found all twenty are stale. Every one was already failing
at the very first commit in the history; they broke before git began. Fifteen assert an old look. The five model tests
check behaviour that is *right*: their fixtures went stale when later code added fields and checks. Better still, the
agent that diagnosed them wrote the fixes: 16 tests ported to what you want now, 4 retired, and every module passing.
It also checked the ported tests still catch real faults by breaking the code each one guards. Those fixes are saved.

**2. Our tests catch about half of what they should.** We planted 136 deliberate small bugs across the code that matters
most. The tests caught 70 of them by checking behaviour. That's 53%. Another 18 were caught only by a check that fails
whenever the file changes at all, which proves nothing about behaviour. 61 survived every test. Those 61 are a map of
exactly where the tests are blind.

**3. The release checks cost an hour and found almost nothing.** The battery outside the suite takes about 65 minutes. In
every stored release run since 0.5.0, it caught one real fault (the gate's frame check, in 0.7.0). Your playable scene
caught two more in its first release. The crawler and the 30 probes caught none. Dropping only the duplicate and dead
checks brings a release to about 15 minutes without writing new code. Moving what the probes really check into the
repository brings it to about 9.

**4. The 4B is a real test bench now.** It proved the memory rules with real workers. It also showed exactly where
today's loop fails: three correct decisions, then out of time.

**5. Screenshots can lie by omission.** The green under the pointer was invisible to every frame we took, because the
window system draws the cursor outside the window. A reviewer found it by thinking about how a person actually sees the
screen. I'll carry that into every look review: check what a screenshot can't show.

**6. The container can restart under us.** Today it did, mid-save. From now on every pass saves to `wip/` and pushes
as it goes, not just at the end.

## How I'll work from here

These are process changes, small but deliberate:

- **Smaller passes, each shippable.** One release per slice, each with one thing you can see and try.
- **Tiered checks, from the next release.**
  - *Tier 0, under a minute:* the pure logic modules, on every change.
  - *Tier 1:* the window modules picked by which files changed, before every commit.
  - *Tier 2:* the full battery, only at a release, slimmed from 73 minutes to about 15.
- **Your scene is the acceptance test for every pass that touches the window,** in both appearances. It found more than
  the crawler and the probes together.
- **Every pass is reviewed by agents that didn't build it,** with one reviewer asked specifically what pictures can't
  show: the cursor, timing, sound, real input, a slow disk.
- **I'll show you frames at each step,** not only at the end, so you can redirect early.
- **Save and push as I go,** and keep the disk below 80%.
- **Changes to the plan get said out loud.** Like the one coming next.

## The order changes: tests first

When we stopped, my resume order was her door on the Field, then the tests, then the maths. I'd now swap the first two,
and here's why:

- **The test fixes already exist.** Applying them is a day, not a week.
- **Every later pass gets faster and safer.** With honest tests and a 15-minute release check, her hand gets built on a
  suite that means something. A red result will be a real fault, not "one of the known twenty".
- **Her door is the riskiest code we'll write:** synthetic input, a stop that must work between presses, a planner. I
  want the strongest safety net under it before it goes in, not after.

So 0.8.4 is "Tests you can believe". Her door becomes 0.8.5. If you'd rather have her door first because you want to
see her move sooner, say so; the cost is a slower, noisier build for it.

## The releases, one by one

### 0.8.4 · Tests you can believe

**What you'll see:** nothing new on screen, except the small 0.8.3 yellow leftovers fixed. And a release note that says
"0 failing" for the first time.

**What gets built:**
- **The twenty:** 16 ported to what you want now, 4 retired with a written reason each. The five model tests come back
  green with corrected fixtures, guarding exactly the restore and cancel behaviour the model swap will need.
- **The window checks:** of the 29 scripts, 7 retired or folded into tests (about 2,800 lines gone), the rest fixed or
  ported. Every one that remains passes.
- **The line bugs from PAL P0:**
  - `2*-3` gives −6;
  - a sum includes numbers written as text, or refuses them visibly;
  - true and 1 stay separate groups;
  - a join never overwrites a field;
  - `select title, state` with a space works.

  Each gets a test that pins it.
- **The blind spots:** of the 61 surviving planted bugs, the ones in code that guards you (the Kernel's scopes, her
  hand's rules, the memory rules, the release check) each get a test that would have caught them. Target: at least 75%
  caught in those modules. Rounding helpers can wait.
- **The tiered runner and the slimmed release battery.** The probes that check something real move into the
  repository, so they run everywhere. The duplicates and the dead ones retire.
- **The yellow leftovers:**
  - the grey glows become warm light;
  - the lists with their own colours use the highlight;
  - the PDF highlight becomes an edge;
  - the Run button's focus turns yellow;
  - and the colour-vision check from the quiet-parts talk: every pair of meaning colours simulated for weak red and weak
    green, and every meaning also given a word or a shape.

**How it's proven:** the planted bugs run again, and the catch rate in those modules goes up, not down, after the
retirements. Then tier 0 under a minute, and a release check under 15.

### 0.8.5 · Her door on the Field

**What you'll see:** you ask her in words, *"trace the bench readings and put the limits side by side"*, and she does
it on the Field:
- a small ring shows where she's about to click;
- her card shows each goal light up;
- the hologram goes to "at work";
- the moment you touch the mouse, she stops;
- "Put my window back" undoes the moves.

**What gets built:** the saved half-build from today, finished as planned:
- `read.desk` learns what's hidden today: where the keyboard is, whether the line's words are hers or yours, what's
  waiting;
- the operator table for the Field's acts;
- the forward planner with its budgets;
- goals with evidence and the finish rule;
- the touch filter;
- the stop between presses;
- the snapshot and put-back;
- the "pick" turn for the model.

Only moves in this slice: no changes. Also the word fixes the readers found (a key still printed in the Approve tip and
in the console's approval words, "Programs" in some model errors) and a stale trace report.

**The ThinkPad check ships with it.** One command you run once. More on it below.

**How it's proven:**
- two new scenes in both appearances: P02, her door on the Field; P03, you take the window back;
- P01 unchanged;
- a conformance test: for each planned act, predict the window's state, run it, and compare exactly;
- the 4B check: three requests, each answered in under 60 seconds with under 1,200 tokens of prompt, all three exact.

### 0.8.6 · Maths in lines

**What you'll see:** lines that answer engineering questions exactly:
- `solve "voltage * current <= limit" for current` → "up to 500 mA, at 12 V and the continuous limit".
- `range` over the tolerances → the exact span.
- `check` → holds, does not hold, or cannot tell, with the reason.

Your tolerances become records you set: a card that waits for your Approve. Every answer carries a receipt.

**What gets built:** the one maths core from PAL draft 0.2 and the hand plan:
- `math_ranges` (exact ranges, the rules for endpoints and integer steps, the dependency trap handled);
- `math_answers` (one answer record for lines and goals alike);
- `tolerances`;
- a freshness check, so a stale limit is never used silently.

Existing exact engines are reused, not rewritten.

**How it's proven:** the draft's numbers as exact test vectors:
- 500 mA and 499 mA (strict);
- 30,000/61 mA, with 491 and 492 in whole mA;
- the zero coefficient, the empty domain, the pole, the repeated variable, the stale limit;

and the same model through a typed line and through Then.

### 0.8.7 · Goals over data

**What you'll see:** she judges your After Hours findings herself. The startup pulse with ±5 ms: "does not hold, over
by 25 to 35 ms; a finer measurement can't change that." Startup power against 8 W: "cannot tell; the current reading
would settle it most often." Each verdict has its evidence a click away, and each goes to "recheck" when its source
changes.

**What gets built:**
- goals that bind to cells and tolerances;
- value of information;
- break-even;
- the four-valued evidence logic Graphite already has, reused;
- rebinding when an unchanged value moves revision, and repair in order when a changed one does.

**Also here: quarantine for outside material,** because this is when her goals start reading sources you didn't write.
A new download is marked "unread by kp" until it's been read as plain text, with anything addressed to an assistant
flagged.

### 0.8.8 · Changes through her hand

**What you'll see:** she can change things through her door:
- set a cell;
- write a file from your exact words;
- move something to DELETE;
- run a step.

Each happens at your dial: Ask first waits, Do and show does it with one Undo. DELETE gets an exact Undo that puts the
file back where it was, never overwriting.

**What gets built:**
- the changes through the same staging path her hand already uses;
- a check, after any write that timed out, of what actually landed before anything retries;
- the rest of the desk acts under her door (menus, Files, Then);
- the desk trail beside her data trail.

The **Delete and Forget** split from the quiet-parts talk lands here too, because this is when DELETE gets its Undo.

**How it's proven:** P04, the whole playable scene done from her words in 13 acts or fewer; P05, changes under her hand
at each dial place.

### 0.8.9 · Her question, and the experiment

**What you'll see:** when two choices genuinely tie, she asks you one short question with the options ranked, instead
of guessing.

**What gets built:**
- the NEXT turn;
- the late-answer rule: if the model is late, a read can be taken by default, a change never;
- prompt reuse, so a question she's asked before costs seconds;
- **the I05 experiment** you proposed, run here with the 4B, and packed as a kit for your 35B on the ThinkPad.

### 0.8.10 · The floor

**What you'll see:** a faster window and a safer upgrade.
- **The split:** the three biggest window files broken up by surface (the head, the left column, her column, the
  writing line, the Field) behind small interfaces. Move and test, never rewrite, with the full suite between moves.
- **Budgets measured:** start to the Field in 6 seconds, a Field frame in 16 ms, the hologram under 2% of a core,
  nothing blocking the window for more than 50 ms.
- **The migration drill:** a real 0.4.6 workspace backed up, restored into 0.8.10, every record and revision and Undo
  read back, then compared the other way to prove nothing was silently rewritten.
- **The pull-the-power drill:** a write interrupted, and the workspace proven to open clean.

### 0.9.0 · When the ThinkPad says so

Not a feature release. 0.9.0 is the version where all six gates are open on your machine:
- the check's numbers are on file;
- the 35B answers on the Radeon;
- your scene passes on the real display;
- her hand works;
- the tests are honest;
- your data came forward.

The release note will list what was actually observed on the ThinkPad, separately from what was checked here.

## The ThinkPad check, in detail

This is the single most valuable thing I'll build, because it turns estimates into measurements.

**What it is.** One command, run from the installed Graphite folder. It sends nothing anywhere and writes one report
file. It reads:

- **The GPU:** which device Vulkan sees, which driver, and the memory heaps it reports.
- **The GPU's memory window:** the limits the kernel puts on how much system memory the Radeon can borrow, read from the
  system's own files, plus whether a larger limit is set.
- **The memory:** total, free, and the module speed when it can be read without root.
- **The model's real speed:** a short benchmark of your 35B (prompt reading and generation, Vulkan and processor), with
  the context size you use. About two minutes.
- **The window:** which display platform Qt chose, the scale factor, the panel's pixels per inch, whether her faces
  loaded with the right hashes.
- **Graphite's own speed:** time from launch to the Field on After Hours 07, and the Field's frame time while you pan.
- **Your scene:** P01 played on your real display, both appearances.

**What it never does:** change a setting, install anything, or touch your workspace (it plays the scene on a copy).

**What it gives me:**
- the real tokens per second, so the planner's time limits are set from facts;
- whether the memory window needs one kernel setting raised before the 35B runs out of room;
- the scale factor that decides how the typewriter face and the hologram really look;
- and the first real-machine evidence for 0.9.0.

You'll get a short card at the end in plain words: what's fine, what needs a change, and the one line to send me.

## The I05 experiment, as a protocol

Your idea, done properly, so it can come out wrong:

- **Three arms, same model, same cases, same budgets:**
  - **A:** today's loop.
  - **B1:** the model sees the open conditions and a short lookahead, and picks every step.
  - **B2:** B1 plus deduction wherever only one step is possible.
- **Runs:** three repeats per arm, interleaved, with the disk cache dropped before each. Here with the 4B, there with
  your 35B.
- **Measured:** pass or fail per case, model turns, prompt and answer tokens, seconds per turn, repeats blocked,
  "finished with an open condition" (must be zero), and how often B1 picked the planner's top option.
- **Predicted in advance:**
  - A fails at the time wall again;
  - B2 passes all three cases with three or fewer model turns each, under 60 seconds per turn here, using under half of
    A's tokens;
  - B1 passes with more turns, picking the top option at least 80% of the time.
- **What would change my mind:** if B1 beats B2, the model is adding judgment that deduction lacks, and I'd give it more
  of the steps. If neither passes with the 4B but both do with your 35B, the planner is right and the 4B is just too
  small. If B2 fails on the 35B, my central bet is wrong, and I'll say so.

## Things from the quiet-parts talk, and where they land

| Idea | When | Why then |
|---|---|---|
| Colour-vision check | 0.8.4 | small, and the yellow just landed |
| Quarantine for outside material | 0.8.7 | when her goals start reading sources |
| Delete and Forget | 0.8.8 | when DELETE gets its exact Undo |
| Secrets scan before any record is written | 0.8.8 | when she starts writing records |
| Pull-the-power drill | 0.8.10 | with the migration drill, same floor |
| Kasandra's character file | any time | with you writing it; I'll draft a skeleton |
| Time slider on the Field | after 0.9.0 | needs the revision walk-back |
| Night shift | after 0.9.0 | needs her changes and the budgets settled |
| Receipt bundles | after 0.9.0 | the first piece of a published protocol, if you choose to publish |
| Missions to learn kp | after 0.9.0 | the scenes double as lessons |
| Voice, phone window, vision role | 0.9.x to 1.0 | each after the ThinkPad numbers |

## What I need from you, by release

- **0.8.4:** nothing; it's mine to grind.
- **0.8.5:** run the ThinkPad check once and send me the report. Try her door: does the pace feel right (300 ms between
  her clicks), and does stopping feel instant?
- **0.8.6–0.8.7:** your real tolerances for After Hours 07 (the pulse reading, the rail, the current), and which limit
  applies when Rev A and Rev B disagree.
- **0.8.8:** decide the dial's default for her changes.
- **0.8.9:** run the I05 kit with your 35B.
- **0.8.10:** a copy of a real 0.4.6 workspace, or tell me which backup to use.
- **Any time:** the first draft of Kasandra's character file, and whether kp stays yours, becomes a product, or becomes
  a protocol.

## What could go wrong, and what I'll do

- **The ThinkPad surprises us** (the memory window too small, the Vulkan path slow, the faces scaled oddly). That's why
  the check comes early. Each surprise becomes a fix in the next release, not a crisis at 0.9.0.
- **The 35B is slower than the physics says.** Then prompt reuse and the small chooser matter more, and the planner's
  time limits are set from your real numbers.
- **The planner is wrong somewhere.** Every slice has a conformance test and a scene, and the experiment is designed to
  show me if my central bet fails.
- **Your direction changes.** It will, and that's good; the best parts came from your turns. Smaller releases mean a turn
  costs a week at most, not a month.
- **The container restarts again.** Saved and pushed as we go, so the worst case is redoing an hour, not losing a day.

## The short version

1. **Honest tests and fast checks first,** because the fixes exist and everything after stands on them.
2. **Then her door, her maths, her goals, her changes, her question,** one release each, each with a scene you can
   watch.
3. **Then the floor:** the split, the budgets, the drills.
4. **0.9.0 is the day the ThinkPad agrees.**

And through all of it, the rule from the first release: she proposes, the system checks, you decide.
