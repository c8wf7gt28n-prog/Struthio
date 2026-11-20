# Kas's mind, no model: the engineering and science lens

*A design proposal for 0.8.6, written 20 November 2026. Every number below comes from Rail Demo, which is invented (nothing
was measured), or follows exactly from it. Each one was worked with exact fractions. The tolerances in the examples are
ones the owner would record himself. Kas never records one.*

---

## 1. The idea: three zones

Every question an engineer asks about a limit has the same shape. Take one input and hold the others within their
tolerances. There is a stretch of its values where the goal **holds whatever the others do**, a stretch where it **does
not hold whatever they do**, and a grey stretch between where **it depends**. The 0.8.5 maths already finds those edges
exactly. `allowed` ("solve for") run on the relation gives where the holds zone ends. Run on the opposite relation, it
gives where the does-not-hold zone begins.

Once Kas has the edges, most engineering judgment is exact arithmetic on them:

| The question | What it is on the zones | Capability |
|---|---|---|
| How much room is left? | the distance from the reading to the edge | eng-1 To spare |
| Which input eats the room? | how much of the spread each tolerance causes | eng-2 What moves it most |
| What measurement would settle it? | how much of the grey stretch one reading removes | eng-3 What would settle it |
| What reading should I accept with this meter? | the edge moved inward by the meter's accuracy | eng-4 Test plans and guard bands |
| What did the new revision change? | how the edges moved, and which cell moved them | eng-5 Revisions by conclusions |
| Does this limit apply here at all? | an edge in time or temperature, not in value | eng-6 Where it applies |
| Is every requirement checked? | which limits have zones at all | eng-7 Coverage |
| What if the supply sags? | the reading moved, every goal on the desk judged again | eng-8 What if, desk-wide |
| Did reality land where we said it would? | the predicted range against the new reading | eng-9 What I expected |
| How does the model use all this? | the zones, already ranked and rounded, as its facts | eng-10 The brief and the number check |

With no model loaded, this works like an engineer's notebook that does its own sums and never claims more than it can
show. When a model is loaded, its job gets smaller. Instead of "think about the rail", it is asked to pick one of two
ranked options, or to say three given facts in a sentence. Any number it says must already be in a receipt.

## 2. What it stands on

Nothing below rewrites existing maths. The files hashed by `math_service.components()` stay frozen.

| Existing | Used for |
|---|---|
| `math_ranges.allowed`, `enclose`, `check_box`, `corner_witness`, `decide`, `Enclosure` (0.8.5 patch) | every edge, range, worst corner and witness |
| `math_answers.answer` and `ledger.math-answer/1` (0.8.5) | every new analysis is a new *stage* of the same receipt: `model_calls: 0`, inputs with origins, guarantee, freshness, implementation hashes |
| `tolerances.py`, `ledger.tolerance/1`, the ALWAYS_ASKS row (0.8.5) | the only source of her ranges |
| `math_service.model_for` overrides, origin `DECLARED_SCENARIO` | what-ifs (eng-8) |
| `stac/evidence.py` `truth_and`, `knowledge_join`, `EvidenceSupport` | joined goals, and two readings that cannot both be right |
| `goals.py`, `planner.py` (hand_s1 half-build); the S3 goal face (`bindings_from_cells`, `goals.check`) | goals bound to cells; deduction |
| `field_model.py`, `field_source.py`, `field_ripple.py` | which goals lie downstream of a cell (never for numbers) |
| `field_doubt.py` | rule 3 ("what it leans on", float 1 %) replaced by an exact figure; rule 2 ("different conditions") made exact by eng-6 |
| `field_brief.py` | the desk as one page; eng-10 adds a form for the model |
| `quantities.py`, `math_units.py` | units of every number in a sheet, a condition or the model's words |
| `datasheet_work.what_if`, `office.datasheet.recheck`, `investigation.claim/check` | calculation pages, rechecks, open questions |
| `rail_demo.py` | the fixture for every test below |

**One new pure module carries the shared core.** It is `workbench/math_zones.py`: Fractions only, with no Qt, Kernel,
model, SymPy or Z3, and it gets the same float scan as `math_ranges`.
- `zones(ir, box, name)`: the two `allowed` calls.
- `room(ir, box, name)`: the distance from the reading to the edge.
- `swings(ir, box)` and `consumption(ir, box)`: how much of the spread and of the room each input causes or uses.
- `leverage(ir, name)`: what a 1 % rise does to the room.
- `decisive_share(...)`: how much of an input's range a reading would settle.
- `settling_reading(...)`: what a new reading must say, with a given accuracy, to settle the goal.

These functions also appear as new `math.answer` stages, so the owner can type them as a line too:

```
math problem:ID | room "REL"          how far each input may move before the relation changes
math problem:ID | lean "REL"          what moves it most, and how much of the room each range uses
math problem:ID | settle "REL"        the three zones of each input, and which reading would settle it
```

## 3. The desk used in every example (Rail Demo, invented)

- **Readings** (sheet "Rail Demo bench readings"):
  - B2 rail voltage 12 V;
  - B3 settled current 250 mA;
  - B4 startup current 900 mA;
  - B5 startup duration 45 ms.
  - Each row's Conditions cell says "Bench at 25 C".
- **Limits** (Rev A, archived / Rev B, current):
  - B2 settled power limit 5 / 4 W, "Continuous";
  - B3 startup duration limit 60 / 40 ms, "From switch-on";
  - B4 startup power ceiling 12 / 12 W, "Up to 60 ms" / "Up to 40 ms";
  - B5 nominal voltage 12 V, "At the rail" (the same in both).
- **Goals.** The owner binds these through the goal face. Kas may propose them; the owner agrees.
  - **G1** settled power: rail voltage × settled current ≤ settled power limit.
  - **G2** startup duration ≤ startup duration limit.
  - **G3** startup power: rail voltage × startup current ≤ startup power ceiling, over the span the ceiling covers.
- **The owner's tolerances in the examples** (invented):
  - rail voltage ±0.25 V ("the bench supply");
  - startup duration ±3 ms ("the stopwatch");
  - in some examples, startup current ±50 or ±100 mA ("the clamp meter").

---

## 4. The capabilities

Effort: **S** is about half a builder session, **M** about one, **L** more than one. Every capability below works with no
model loaded.

### eng-1 · To spare: margins and the worst case, desk-wide

**What the owner sees.** Each goal's card shows its state, the room left at the worst corner (in the goal's own unit and as
a share of the limit), and how far each input may move before the goal changes. There is also a "To spare" page, and Kas's
card lists the tightest three. The order is fixed:
1. goals that do not hold;
2. goals she cannot tell;
3. goals that hold, least room first.

A goal checked over a range that is sound but not exact says "at least …", never an exact figure.

**Worked example** (Rev B, voltage ±0.25 V, startup duration ±3 ms):
1. *Startup duration: does not hold, over by 2 to 8 ms.* To hold with this stopwatch, the reading would have to be at most
   37 ms.
2. *Startup power (0 to 40 ms): holds, 0.975 W to spare at worst* (exactly 39/40 W, 8.125 % of the 12 W ceiling). The
   startup current may rise to 979 mA (exactly 48000/49 mA) before it stops holding at 12.25 V. That is 8.8 % above the
   reading.
3. *Settled power: holds, 0.9375 W to spare at worst* (15/16 W, 23.4375 % of 4 W). The settled current may rise to 326 mA
   (16000/49 mA, 30.6 % above the reading). At 250 mA the voltage may rise to 16 V.

Under Rev A the settled power has 1.9375 W to spare (31/16 W).

**How it is built.**
- `math_zones.room` uses `allowed` with the other inputs at their ranges. It reports the exact end, the end on the
  quantity's step (rounded inward, as `allowed` already does), the distance from the reading and the share of the limit.
- A new stage `room` of `math.answer`.
- The goal-face read `goals.room` walks the goals with `bindings_from_cells`.
- The card uses the existing headings Holds / Does not hold / Cannot tell.

**Needs a model:** no.

**How it helps the model.** "Which part is riskiest?" and "how close are we?" become lookups, and deduction answers them
with no model turn. When a model does speak, these facts reach it already rounded, each with its receipt.

**Effort:** S, on top of the goal face.

**Proven by** `tests_integrated/test_math_zones.py` (pure) and `test_goal_views.py` (the Rail Demo fixture through
`rail_demo.workspace`):
- the exact values 39/40, 15/16, 48000/49 mA → 979, 16000/49 mA → 326, 16 V and 31/16;
- the order G2, G3, G1;
- determinism: the same desk gives the same order and the same digest;
- every reported end holds at the corner that sets it, and one step past it fails, with the witness re-evaluated by
  `math_model.evaluate` on the freed copy;
- a sound (not attained) range is worded "at least";
- the float scan.

**Risk.** "To spare" may be read as a safety factor, or as permission to use the room. A share "of the limit" may be
confused with a share "of the reading", so the words always name which. Ordering by the share of room is a convention, and
the page says so.

*Everyday twin:* "groceries this month: 38.20 to spare against the budget, at the worst of the prices you gave."

### eng-2 · What moves it most: exact sensitivity and the error budget

**What the owner sees.** A goal's "What moves it most" lists, for each input with a range:
- how much of the answer's spread it causes, in the goal's own unit, and its share;
- how much of the room its tolerance uses;
- its leverage: a 1 % rise in this input changes the room by exactly so much.

Across the desk, a short list names the inputs whose tolerances use the most room. Those are the tolerances worth
tightening.

**Worked example** (G3 with voltage ±0.25 V and startup current ±50 mA):
- **The spread.** The power lies in 9.9875 to 11.6375 W. This range is exact: both ends really happen.
- **Shares of the spread.** The startup current causes 1.2 W of the 1.65 W spread (8/11). The voltage causes 0.45 W
  (3/11).
- **The room.** At the reading there is 1.2 W of room.
  - The current's ±50 mA uses 0.6 W of it.
  - The voltage's ±0.25 V uses 0.225 W.
  - The two together use 0.0125 W more.
  - That leaves 0.3625 W.
  - Exactly: 6/5 = 3/5 + 9/40 + 1/80 + 29/80.
- **Leverage.** A 1 % rise in the startup current takes exactly 9 % of the startup power's room. A 1 % rise in the settled
  current takes exactly 3 % of the settled power's room. Tight goals have high leverage, and this number shows it.
- **Desk-wide.** The rail voltage feeds G1 and G3. Its ±0.25 V uses 6.25 % of G1's room and 18.75 % of G3's.

**How it is built.**
- `math_zones.swings`: the slack range with only that input ranged and the others at their declared values; the width is
  what the input causes.
- `consumption`: walks from the reading to the worst corner one input at a time, then adds the joint remainder. Nothing is
  dropped.
- `leverage`: the slack at value × 101/100 against the slack at the value, an exact rational.
- The desk-wide list joins this with `field_model`'s wires (which goals read a cell).
- **It replaces `field_doubt` rule 3** (field_doubt.py:172-189), which today works a float 1 % change and prints
  `%+.2g %`. The rule keeps its row and its staC `see` line, but its figure becomes exact.
- Inputs are ranked only in the slack's own unit, never by per-unit derivatives (W/V and W/mA cannot be compared; item 9
  of the maths judgment).

**Needs a model:** no.

**How it helps the model.** "Why is it tight?" gets a templated answer ("the startup current's ±50 mA uses half the room"),
and the model only phrases it. A ranked list of a few tokens replaces the sheet in the prompt.

**Effort:** S.

**Proven by:**
- the exact values 6/5, 9/20, 8/11, 3/5, 9/40, 1/80 and 29/80;
- the identity "parts + remainder + room left = room at the reading", exact on seeded random boxes;
- each input's swing never exceeds the whole width (sub-box property);
- leverage −9/100 and −3/100;
- `field_doubt`'s note for V × I reads "+1 %" exactly, and the float scan covers the replaced rule.

**Risk.**
- Swings are exact only where the corner rule of the maths core holds. Elsewhere they are a sound range, said as "at
  most".
- With no room left, a percentage of the room means nothing, so the state "no room left" is shown instead of a number.

### eng-3 · What would settle it: the three zones and the worth of a measurement

**What the owner sees.** For a goal she cannot tell, each input gets a bar. It is marked *holds up to here* / *cannot tell* /
*does not hold from here*, with the reading's own range drawn on it. The words sit beside the bar, so it never relies on
red and green alone.

Under the bars she says which reading to take first, and what it must show:
- **The first reading.** "Measure the startup current first: a reading of it settles this over 44/49 of its range; the
  voltage over 1/2. These are shares of the range, not chances."
- **What it must show.** "With a meter good to ±10 mA, a reading at or below 969 mA settles it."
- **When nothing can help.** "No measurement can change this" (when it already holds or fails whatever the values).
- **For goals joined together.** "Measuring the startup current cannot change whether the rail meets Rev B: startup
  duration already does not hold."
- **The owner's own decisions count as information too.** "Your word on which revision applies settles this if it is
  Rev A."

**Worked example.**
- **G3** with voltage ±0.25 V and startup current ±100 mA:
  - The power lies in 9.4 to 12.25 W against 12 W, so she cannot tell. It fails for some values, at 12.25 V and 1000 mA
    (12.25 W).
  - **Startup current.** It holds whatever the voltage up to 979.59 mA (48000/49). It would fail whatever the voltage only
    above 1021.28 mA (48000/47), which is outside its range. So a reading of it settles the question over 44/49 of its
    range.
  - **Voltage.** It holds up to 12 V and fails only above 15 V, so a reading of it settles the question over 1/2.
- **G2** with a ±5 ms stopwatch: 40 to 50 ms, so she cannot tell.
  - If the owner says Rev A (60 ms) applies, it holds with 10 to 20 ms to spare.
  - Under Rev B, re-timing with something good to ±0.5 ms settles it unless the new reading lies between 39.5 and 40.5 ms.

**How it is built.**
- `math_zones.zones(ir, box, name)` makes two `allowed` calls: the relation, and its opposite (≤ against >, < against ≥).
  For = and ≠ it refuses, with the reason.
- `decisive_share` is the length of the decided zones inside the range, divided by the range's width, exactly.
- `settling_reading` is the holds edge minus the meter's accuracy, and the does-not-hold edge plus it, rounded inward.
- Joined goals go through `truth_and` (stac/evidence.py:78). When one conjunct fails whatever the values, every
  measurement's worth for the joined goal is 0.
- An open owner decision ("which limit applies") is judged under each candidate row. None is chosen.
- These are the S3 plan's `decisive_share`, `break_even` and `value_of_information`, with a home and a line verb (`settle`)
  and a read `goals.settle`.
- **Deduction rule.** One measurement dominates another when its share is at least as large on every open goal it touches,
  and its cost, if the owner gave one, is no higher. A single dominant option is taken without a model turn.

**Needs a model:** no.

**How it helps the model.** The NEXT turn is only needed when options truly tie. Then it gets at most three options, one
line each, with exact shares, and its pick is checked to be one of them. This is the B2 arm of I05 ("deduction wherever
only one step is possible") with an engineering reason behind each deduction.

**Effort:** M.

**Proven by:**
- 44/49, 1/2, 48000/49, 48000/47 and 969 mA;
- G2 under Rev A holds with slack [10, 20];
- the joined goal's measurement worth is 0;
- a goal that holds offers no measurement;
- the S3 vectors 27 and 28 (decisive shares 6989/7878 and 3089/3978, break-evens 40/39 and 25/14, on the in-repo After
  Hours fixture);
- every settling reading re-checked at both ends of the meter by `math_model.evaluate`;
- a scan of every template proving no wording says "chance", "likely", "probability" or "risk of".

**Risk.**
- Shares may be read as probabilities. The words forbid it, but people still might.
- A share of the range treats every part of the range alike, which is a convention, not a fact.
- It ranks one input at a time.
- Goals outside the corner guard get UNSUPPORTED, with the reason.

*Everyday twin, for the owner's own records:* "whether this dose by weight stays under the maximum you recorded from the
label cannot be told from 'about 70 kg'; a weighing settles it unless it reads between …"

### eng-4 · Test plans from open questions, with guard bands

**What the owner sees.** "What to measure next" is a short plan Kas writes from every goal she cannot tell. Each step says:
- what to measure, and how accurately;
- the reading that settles it each way: accept at or below this, reject above that, and between them a better meter is
  needed;
- what follows each outcome.

The owner's decisions come first, as questions. The plan is shown at once. Keeping it is a change, so it waits at her dial.
Once kept, each step is an open question on the investigation. When a new reading arrives, the goals recheck and the plan
moves on by itself, saying what the reading settled. A new reading arrives either through a newly reviewed source or a cell
the owner sets.

**Worked example** (Rev B; open: G2 with ±5 ms, G3 with ±100 mA):
- **Step 0. Yours to say: which revision applies?** If Rev A, startup duration holds and the 12 W ceiling covers the whole
  startup, so step 1 is not needed.
- **Step 1. Re-time startup with something good to ±0.5 ms.**
  - At or below 39.5 ms: holds.
  - Above 40.5 ms: does not hold, and then the rail does not meet Rev B whatever steps 2 and 3 show. She says so.
  - Between the two: a better meter is needed. If it reads 40.2 ms, only a meter better than ±0.2 ms can settle it.
- **Step 2. Measure the startup current to ±10 mA.**
  - At or below 969 mA: startup power holds whatever the voltage between 11.75 and 12.25 V.
  - Above 969 mA: go to step 3.
- **Step 3. Read the rail voltage during startup to ±0.05 V.** With 980 mA read (970 to 990 mA):
  - holds if the voltage reads at most 12.07 V (the exact end is 7967/660 V, rounded inward);
  - between that and 12.42 V, these meters still cannot tell.

The accept line is the limit moved inward by the meter's accuracy: a guard band. With one, a pass is a pass even at the
meter's worst.

**How it is built.**
- `workbench/test_plans.py` is pure planning over `goals.settle` answers.
- **The record** `ledger.test-plan/1` (kind `test_plan`) holds:
  - `steps[]`, each with `quantity`, `cell`, `accuracy`, `accept`, `reject`, `then`, `settles` (goal ids),
    `can_change_overall` and receipt digests;
  - `made_from`, a digest of the goal states;
  - `state`: OPEN, DONE or STALE.
- Kept steps become QUESTION claims (`investigation.claim`) and prepared `investigation.check` programs with templated
  oracle words.
- **Optional `ledger.measure-tool/1`** records what the owner measures with and how accurately. It is owner-set like a
  tolerance, with an ALWAYS_ASKS row. With it the plan can say "nothing you have listed settles this".
- **The order rule**, said on the page:
  1. the owner's decisions;
  2. steps that can settle the joined question as "does not hold" (fail fast);
  3. decisive share;
  4. the owner's time, if given;
  5. name.

**Needs a model:** no.

**How it helps the model.** The plan is a fixed decision tree. The model orders steps only on a true tie, and may word a
step, but every number in it is fixed by a receipt.

**Effort:** M.

**Proven by** the Rail Demo plan as an exact fixture:
- the thresholds 79/2 and 81/2 ms, 969 mA and 7967/660 V;
- entering 38 ms gives holds, 41 ms gives does not hold, and 40.2 ms gives cannot tell with "better than ±0.2 ms";
- the plan's digest is the same twice;
- `can_change_overall` is false for the steps after a conjunct that fails;
- nothing is written until the owner keeps it, checked by record counts before and after;
- a measured cell is never edited to make its own goal true (the S2 rule).

**Risk.**
- A step may read as an instruction.
- Whether the owner has such a meter is unknown until the measure-tool list exists.
- A kept plan goes STALE when goals change.
- In the medical twin a step must stay "information to obtain", never an act on a body.

### eng-5 · Revisions compared by what they conclude

**What the owner sees.** Compare two revisions of a source or a sheet (Rev A and Rev B, or before and after a recheck).
Instead of a list of changed cells, the comparison lists:
- the conclusions whose state changed;
- room that grew or shrank;
- allowed values that moved;
- for each change, the cell or cells that caused it.

Cells that changed without moving any conclusion come after, briefly. After every recheck caused by a changed source, the
same comparison appears by itself as "What this change did".

**Worked example** (Rev A → Rev B, voltage ±0.25 V, duration ±3 ms):
- *Startup duration:* holds, 12 to 18 ms to spare → **does not hold, over by 2 to 8 ms.** Caused by B3, the startup
  duration limit, 60 → 40 ms. Putting that cell back alone restores the old state.
- *Startup power over the whole startup:* holds → **cannot tell for 40 to 48 ms.** The 12 W ceiling now covers only up to
  40 ms. Caused by D4, "Up to 60 ms" → "Up to 40 ms". The 12 W did not change; a cell diff would show only a change of
  words.
- *Settled power:* holds → holds. Worst room 1.9375 W → 0.9375 W (38.75 % → 23.4375 % of the limit). Caused by B2,
  5 → 4 W.
- *Allowed settled current:* up to 408 mA → up to 326 mA.
- *Unchanged:* the nominal voltage row.

The demo's own change, settled current 250 → 300 mA, gives:
- room at the reading 1 W → 0.4 W;
- no state changes;
- the allowed settled current does not move, because it does not depend on the reading.

**How it is built.** The module is `workbench/conclusion_diff.py`.
- **Pair the rows** across the two revisions by parameter. When names differ, the owner confirms the pairing once.
- **Judge every goal twice** through `math_answers.answer`, with bindings pinned to each revision.
- **Compare** state, room and allowed ends.
- **Attribute each change.** For each changed cell, judge again with only that cell put back, and with all others put back.
  - "Caused it" means putting it back alone restores the old state.
  - "Together" means no single cell does.
- Conditions cells go through eng-6.
- `field_ripple` finds which goals lie downstream, never numbers.
- A read `goals.compare {a, b}` serves it.
- `office.datasheet.recheck` and `investigation.refresh` show "What this change did" as activity. It becomes a page only if
  the owner keeps it.

**Needs a model:** no.

**How it helps the model.** After a change, the model gets three lines of changed conclusions instead of two whole sheets,
and whatever it says about the change is checked against those lines.

**Effort:** M.

**Proven by:**
- the A → B table as an exact fixture;
- putting back B3 alone restores holds;
- B2 changes only room;
- D4 changes coverage;
- a variant that changes an unused notes cell lists it under "moved nothing";
- two cells that only change a conclusion together are reported "together";
- the 300 mA vector (room 2/5 W).

**Risk.**
- Pairing rows by name can go wrong.
- Attribution is not unique when changes interact, so "together" must be shown honestly.
- Many goals make a long comparison, so it is capped with "and N more".

*Everyday twin:* a new lease or tariff, compared by what it does to the owner's own goals ("the notice period went from 60
to 30 days; the deadline you set yourself no longer holds").

### eng-6 · Where it applies: conditions read as exact spans

**What the owner sees.** Below each Conditions cell on a reviewed sheet, Kas writes how she reads it, for example "applies
from 0 to 40 ms, counted from an unstated start". The owner answers *Right* or *Not that*. Until he says Right, the reading
is not used.

Once confirmed, goals check that the reading and the limit apply under the same conditions. When a limit covers only part
of an event, the uncovered stretch is "cannot tell", with the question: which limit applies there is yours to say. A row
with Min, Typ and Max columns becomes a proposed tolerance, which the owner approves.

**Worked example.**
- **Rev B, D4 "Up to 40 ms"** reads as 0 to 40 ms. **D3 "From switch-on"** reads as counted from switch-on.
- **The gap.** The startup lasts 45 ms, or 42 to 48 ms with the stopwatch. The 12 W ceiling covers 0 to 40 ms, and from
  40 ms to the end of startup no row of Rev B gives any limit.
- **Kas asks:** "From 40 ms to the end of startup, which limit applies: none, or the 4 W continuous one? If the 4 W one,
  startup power, 10.8 W, is over it by 6.8 W for that time." (Exactly 34/5 W.)
- **Readings, D2 "Bench at 25 C".** She writes: "C is not a unit I read: °C?" Today `quantities.resolve('C')` returns
  nothing and `math_units` says UNKNOWN_OR_AMBIGUOUS_UNIT; C is also the coulomb's symbol. It stays words until the owner
  says.

**How it is built.**
- **The grammar.** `workbench/applies.py` reads the cell text with a small fixed grammar, taking numbers and units from
  `quantities.extract`.
  - Forms: "up to Q", "from Q to Q", "Q to Q", "at Q", "at most / at least Q", "from <event>".
  - Fixed words: continuous, pulsed, typical, bench, ambient.
  - Anything else stays words.
- **The record** `ledger.applies/1` (kind `applies`) holds:
  - `sheet`, `cell`, `revision`, `text`;
  - `form`, `axis` (time, temperature, voltage …), exact `lo` and `hi`, closed ends, `unit`, `from_event`;
  - `confirmed_by: owner`;
  - `state`: CURRENT, or RECHECK when the cell's words change, like a tolerance.
- **Exact comparisons.** Containment and overlap are exact Fraction comparisons inside `applies.py`. Temperature is a local
  dimension in quantities.py, not a Kernel unit, so it cannot go through the IR.
- **The goal face.** A goal whose limit has a confirmed span gets an extra conjunct, "the event lies inside the span",
  joined by `truth_and`.
- **field_doubt rule 2** ("inputs read under different conditions", field_doubt.py:163-171) compares confirmed spans when
  both sides have one, and keeps its string rule otherwise.
- **Min, Typ and Max.** A previewed row with three numbers in one unit proposes `tolerances.set` (ALWAYS_ASKS), with the
  basis "the source's min and max, row N".

**Needs a model:** no, for the grammar. Optionally, text outside the grammar can go to a PROPOSE turn that picks one of the
fixed forms. Every number in its proposal must appear in the cell's own text, which is checked. It is shown as the model's
reading and still needs the owner's Right.

**How it helps the model.** The model never reads conditions freehand. Its whole task is "which of these five forms", with
its numbers checked.

**Effort:** M for the grammar, the record and one goal conjunct. L if the Min/Typ/Max review is done in full.

**Proven by:**
- a table of each Rail Demo Conditions cell against its exact reading, or "stays words";
- "25 C" is never read as degrees or coulombs without the owner;
- [0, 45] ms against [0, 40] ms leaves (40, 45] uncovered, and with ±3 ms (40, 48];
- 34/5 W once the owner says the 4 W applies;
- an unconfirmed reading never changes a goal's state;
- editing the cell's words sends the reading to RECHECK;
- a model proposal with a number that is not in the text is refused.

**Risk.**
- The grammar may be too small, leaving many conditions as words.
- A hurried owner may confirm a wrong reading.
- References to events ("from switch-on") cannot themselves be checked.
- There is pressure to grow it into general language understanding, which it should resist.

*Everyday twins:* "within 30 days of the notice" (legal, the owner's own papers), "for adults over 50 kg" (a label the owner
recorded), "per calendar month" (money). Each is the same exact span check.

### eng-7 · Requirements traced to evidence: coverage

**What the owner sees.** A "Coverage" page for a limits sheet has one line per row:
- the requirement;
- where it came from (source, revision, fingerprint);
- the goal that checks it;
- that goal's state and room;
- the receipt;
- any gap, in plain words.

A count sits at the top. For a row that no goal checks, Kas proposes candidate goals built only from expressions whose unit
matches the limit's, ranked by shared words. The owner picks one, or a GOAL pick turn chooses among the top three.

**Worked example** (Rev B: 4 rows, 3 checked):
- **Settled power limit 4 W:** checked by G1; holds, 0.9375 W to spare. Rests on readings B2 and B3 and on Rev B's B2.
- **Startup duration limit 40 ms:** checked by G2; does not hold.
- **Startup power ceiling 12 W:** checked by G3; holds within 0 to 40 ms. Gap: 40 to 48 ms is covered by no limit.
- **Nominal voltage 12 V:** not checked against anything.
  - Candidate: the rail voltage (12 V, readings B2).
  - "Nominal" is not a limit word, so the comparison is the owner's to choose.

**How candidates are found.** For the power limits, the candidates are rail voltage × settled current (3 W) and rail
voltage × startup current (10.8 W). "Settled" shares a word with "Settled power limit", so that pairing ranks first for
that row, and "Startup" ranks first for the ceiling. Nothing whose unit does not match is ever offered: no duration ×
current for a power.

**How it is built.** A read `goals.coverage {sheet}` joins:
- the sheet's rows (`office.get`);
- the goals bound to its cells (`goals.list`) and their math answers;
- the Field's wires to sources and their fingerprints (`field_source`, the intake items' sha256);
- `field_doubt`'s marks for cells edited after review (`basis != REVIEWED_PDF_ROW`);
- stale receipts (freshness REVIEW_REQUIRED).

Candidates:
- They are single readings, or products and quotients of two readings, at most 12, whose `math_units` dimension equals the
  limit's.
- They are ranked by shared words in the parameter names (fixed stop-words), then by row order.
- The comparison comes from fixed words. "Limit", "ceiling", "max" and "at most" give ≤. "Min" and "at least" give ≥.
  "Nominal" and "typical" give none, and the owner is asked.
- This is S3's candidate rule (maths judgment, vector 30) turned into a page.

`goals.coverage.keep` saves the page. That is a change, so it waits at the dial. The kept page carries only the cells it
used.

**Needs a model:** no.

**How it helps the model.**
- "Are we within Rev B?" is answered from the coverage lines.
- The GOAL pick turn gets at most three candidates whose units match, in a few dozen tokens, and its pick is checked to be
  one of them.

**Effort:** M.

**Proven by:**
- the Rail Demo coverage, exact: 3 of 4 checked, the states, the room, the gap 40 to 48 ms;
- the exact, ordered candidate list;
- a property test over random sets of units: no candidate ever has the wrong dimension;
- a goal on a cell edited after review shows "rests on a cell changed after review";
- a changed source shows "recheck".

**Risk.**
- Not every requirement is a row in a table.
- The number of candidates must stay bounded (it is capped at 12).
- Ranking by shared words is crude; ties go to the owner or the pick turn.

### eng-8 · What if, across the whole desk

**What the owner sees.** A What if is a named set of changes that touches nothing real: values for cells, a tolerance, or
"Rev A applies". Kas judges every goal on the desk under it and shows a table:
- goals down the side, What ifs across the top;
- the state and room in each cell;
- the break-even beside each changed value;
- a last column naming the goals that hold under every What if.

Several What ifs can sit side by side. The page always says that nothing has changed.

**Worked example:**
- **"Supply at 12.6 V":**
  - settled power 3.15 W, 0.85 W to spare;
  - startup power 11.34 W, 0.66 W to spare;
  - allowed settled current 317 mA (20000/63).
- **"Rev A applies":** startup duration holds, 15 ms to spare.
- **"Settled current 300 mA":** settled power 3.6 W, 0.4 W to spare. At 300 mA the voltage could rise to 13.33 V (40/3)
  before the 4 W limit.
- **Holds under every What if:** settled power, and startup power within the span its ceiling covers. Startup duration holds
  only under Rev A.

**How it is built.**
- **The record** `ledger.what-if/1` (kind `what_if`) holds:
  - `name`;
  - `overrides`: up to 16 (math_service's own limit), each a cell or problem variable with a value and a unit;
  - `revision_choices`;
  - `tolerances` (by id);
  - `made_by`.
- **Judging.** Each answer goes through `math_answers.answer`. Every overridden input has origin `DECLARED_SCENARIO` and an
  assumption such as "What if: rail voltage = 12.6 V", exactly as `math_service.model_for` already does for problems
  (:48-63).
- **Finding the goals.** `field_ripple` lists the goals downstream of the changed cells. `datasheet_work.what_if` handles
  calculation pages.
- **The read** is `goals.whatif`. Making a What if record changes no data, but it is still a record, so it waits at the dial.
- **Limit:** 8 What ifs × 32 goals per table.

**Needs a model:** no.

**How it helps the model.** "What if the supply sags to 11 V?" in words needs the model only to fill {cell, number, unit},
under 32 tokens. That answer is checked for its unit and for the cell existing. Everything else is the desk's own work.

**Effort:** M.

**Proven by:**
- the table, exact: 63/20, 17/20, 567/50, 33/50, 20000/63, 18/5, 2/5 and 40/3;
- the desk's fingerprint (`field_brief.fingerprint`) is the same before and after;
- every overridden input in an answer carries `DECLARED_SCENARIO` and its assumption;
- a What if never edits a measured cell.

**Risk.**
- A What if may be mistaken for reality, so the page heading says nothing here has changed.
- The table can grow large, hence the limit.
- A What if may go stale after a revision. It goes to RECHECK, like a tolerance.

### eng-9 · What I expected: predictions graded, and readings that cannot both be right

**What the owner sees.** Before a new measurement, Kas writes down what the desk expects it to read: the exact range from
the calculation and the owner's tolerances. When the reading arrives, the expectation is marked one of three ways:
- *as expected*;
- *not as expected*;
- *cannot tell*, when the reading's own range straddles an edge.

"Not as expected" is a finding about the desk itself: the calculation, a tolerance or a reading is wrong. Kas names the
smallest changes that would make them agree. Which one is right is the owner's to say. Each calculation builds a track
record, such as "settled power: 5 of 5 as expected".

**Worked example** (re-measuring settled power; tolerances voltage ±0.25 V and settled current ±10 mA):
- **Expected:** 2.82 to 3.185 W.
- **A meter reading of 3.02 W, good to ±0.01:** as expected.
- **A reading of 3.3 W, good to ±0.05** (3.25 to 3.35): not as expected. Kas says:
  - "12 V ±0.25 times 250 mA ±10 is at most 3.185 W. The meter says at least 3.25 W."
  - "They agree only if the voltage could be 0.5 V off, or the current 15.31 mA off (750/49 mA), or one of the readings is
    wrong."

**How it is built.**
- **The record** `ledger.expected/1` (kind `expected`) holds:
  - the goal or calculation, the quantity, and the cell to be measured;
  - the maths answer (range and receipt digest);
  - `made_at`;
  - `state`: OPEN, AS_EXPECTED, NOT_AS_EXPECTED or CANNOT_TELL;
  - `graded_by`: the reading's receipt.
- **Grading** compares ranges with `Enclosure`:
  - disjoint ranges: not as expected;
  - the reading inside: as expected;
  - overlapping otherwise: cannot tell.
- **As evidence**, an expectation adds positive or negative `EvidenceSupport`. Two readings of one quantity meet in
  `knowledge_join`, and CONFLICT is shown as "the two readings cannot both be right", the wording from the maths judgment.
- **The smallest agreeing change** is an `allowed` solve on each tolerance's half-width, one at a time.
- Writing an expectation is a change, so it waits at the dial. Grading happens by itself on recheck.

**Needs a model:** no.

**How it helps the model.** If a model is ever asked for an estimate, its guess is recorded as its own expectation and
graded the same way. Its track record on this desk is then measured, not assumed. That is "remembering what worked", made
exact.

**Effort:** M.

**Proven by:**
- the expected range 141/50 to 637/200 W;
- 3.02 graded as expected;
- 3.25 to 3.35 graded not as expected, with 1/2 V and 750/49 mA;
- a straddling reading graded cannot tell;
- CONFLICT through `knowledge_join`;
- an expectation written after its reading is refused ("an expectation is written before the reading"), checked by
  revision order.

**Risk.**
- "Not as expected" may feel like blaming an instrument.
- With no tolerances recorded, nothing can be expected.
- After-the-fact expectations must be refused, or the track record means nothing.

### eng-10 · The brief for the model, and every number checked

**What the owner sees.** With no model loaded, nothing new: the desk brief already exists. When the model speaks:
- every number in its words has a receipt one click away;
- a number that matches no receipt is removed, and the sentence says so;
- a state word that contradicts a goal is refused.

Its words stay marked as its own.

**Worked example.** These are the facts the model is given for "how is the rail doing?", about 180 tokens:
```
F1 startup duration: does not hold; over by 2 to 8 ms            [G2, receipt …]
F2 startup power, 0 to 40 ms: holds; 0.975 W to spare (8.1 % of 12 W)
F3 40 to 48 ms: no limit on Rev B; which applies is the owner's
F4 settled power: holds; 0.9375 W to spare (23.4 % of 4 W)
F5 settle next: startup current; settles 44/49 of its range    (only while a goal is open)
```
Three answers, checked:
- "Startup takes too long, by 2 to 8 ms, and settled power has almost a watt to spare" passes.
- "Settled power is 3.2 W" has 3.2 W removed, because the desk says 3 W.
- "Startup holds" is refused, because G2 does not hold.

**How it is built.**
- `field_brief.compose` gains a `for_model` form: numbered facts in a fixed order, each with its receipt digest, cut to a
  token budget from the bottom with "and N more". The order is:
  1. goals that do not hold;
  2. goals she cannot tell;
  3. least room;
  4. changes since the last revision;
  5. the next reading to take.
- Every fact line is templated, never the model's text. Anything quoted from a source is fenced as information.
- **The check.** `quantities.extract` finds each quantity in the model's words. Each one is converted to base units with
  `math_units`/`quantities` and compared exactly with the facts' figures and their outward-rounded words. State words near
  a goal's name are compared with that goal's state.
- It sits with `hand_model_checks.py` (the half-build) and `local_brain`'s WORDS turn.

**Needs a model:** no for the brief. The check runs only when a model speaks.

**How it helps the model.**
- The prompt holds only the facts that matter for the decision, so the GOAL pick stays under 1,200 tokens and NEXT under
  1,600.
- A made-up number cannot reach the owner.

**Effort:** S to M.

**Proven by:**
- the Rail Demo fact list, exact and under 400 tokens on the 4B's own tokenizer, measured here;
- the three checked answers above;
- a property test: a random number inserted into an accepted answer is always removed unless it equals a fact;
- I05: on "what should I measure next", the B2 arm with the eng-3 dominance rule uses 0 model turns.

**Risk.**
- Rounding: "about 1 W" against 0.9375 W. A number is allowed only in a fact's own words or as the exact rational; words
  without numbers are allowed.
- A claim that carries no number can still be wrong. Only goal states are checked.

---

## 5. How the legal and medical line is kept

The same maths serves the owner's own legal papers, medical records and money. The design keeps it on the owner's side of
the line by structure:

1. **Limits, tolerances and "which applies" are the owner's alone.** Kas never deduces which limit applies, never sets a
   tolerance, and never invents a range (0.8.5's rules, kept). A limit read from an outside source becomes a goal only
   when the owner binds it, and quarantine's "information, not instruction" travels with it.
2. **Her words are fixed templates about records.** For example: "holds against the limit you bound from <source>",
   "cannot tell", "what would settle it". No template says "you should", "safe", "legal" or "compliant with the law", and
   none prescribes. A test plan lists information to obtain, never an act on a body, a filing or a payment.
3. **Every answer shows where each limit came from** (your note, or this source at this revision) and `model_calls: 0`.
   A model's words are marked as its own and their numbers are checked (eng-10).
4. **Pages for legal and medical goals carry one fixed line:** "Your reasoning over your own records. Not professional
   advice."

## 6. What it does for the model

| Turn | Today | With this pass |
|---|---|---|
| GOAL pick | choose among goals built from words | at most three candidates whose units match, ranked by shared words (eng-7); pick checked to be one of them |
| NEXT | weigh options | deduction takes the dominant measurement (eng-3); NEXT only on a true tie, at most three options with exact shares |
| PROPOSE (conditions) | free reading | one of a fixed set of forms; every number must occur in the text (eng-6) |
| What if, from words | the model works it out | the model fills {cell, number, unit}; the desk judges everything (eng-8) |
| WORDS | may calculate, may make up numbers | ranked facts already rounded; numbers and state words checked (eng-10) |
| Estimates | trusted or not, on faith | recorded as its own and graded like hers (eng-9) |

**I05 addition.** Add an engineering case, Rail Demo's "what should I measure next?". The prediction made in advance:
- B2 with the dominance rule answers in 0 model turns;
- B1 picks the same first step at least 80 % of the time;
- A takes several turns.

If B1 regularly picks differently and the owner prefers its pick, the dominance rule is missing something, and that will be
said plainly.

## 7. Order and effort

1. `math_zones` and **eng-3** (M): every other capability reads the zones.
2. **eng-1** and **eng-2** (S + S): thin views on the zones; rule 3 of field_doubt made exact.
3. **eng-6** (M): needed for the most striking finding on Rail Demo (40 to 48 ms covered by no limit).
4. **eng-5** (M).
5. **eng-7** (M).
6. **eng-10** (S to M).
7. **eng-4**, **eng-8**, **eng-9** (M each). Each is shown at once in 0.8.6. Keeping a plan, a What if or an expectation
   writes a record, and so goes through her hand at the dial. If the pass is tight, those three can be finished in the
   united pass, where changes through her hand arrive.

**The three to build first:**
- **eng-3**, because it is the core that the rest read, and the deduction that saves model turns.
- **eng-6**, because it finds what neither a cell diff nor a model would, and it serves every kind of work.
- **eng-5**, because it answers "what changed that matters?", the question every revision raises.

## 8. Honest limits

- **Worst case only.** No statistics: no root-sum-square stack, no Monte Carlo. A probability needs a distribution the desk
  does not have, and RSS needs square roots and an independence assumption. If added later, it must be marked
  "statistical, assumes independent centred errors".
- **Shares are not chances.** A decisive share treats every part of a range alike. It ranks measurements; it does not
  predict them.
- **One unknown at a time; straight-line maths with corners.** Zones exist only where `allowed`'s guard holds: each ranged
  input used once, never under a division or a power. Anything else is UNSUPPORTED, with the reason. Several unknowns at
  once wait for Z3, marked as not certified when it says "infeasible".
- **No curves yet.** Exponentials, RC charging and derating curves are outside the exact core. A datasheet curve could
  later become a table, interpolated exactly in pieces, or be read from a picture by a vision model and marked so.
- **Conditions are read by a small grammar only.** The rest stays words until the owner says.
- **"Cannot tell" will be common at first.** It is the honest price of never inventing a range. The test plans exist to
  turn those answers into work.
- **Nothing here is measured on the ThinkPad.** The token counts are estimates until they are counted on the 4B here, and
  the 35B's are estimates until the ThinkPad check.
- **Speed.** A desk of 30 goals × 4 inputs × 2 `allowed` calls × 16 corners is about 4,000 exact evaluations. It should take
  well under a second, but that is unmeasured. The target is under 200 ms for the To spare page on Rail Demo, measured here.

## 9. Names, checked against Graphite's existing meanings

| Would have used | Already means in Graphite | Use instead |
|---|---|---|
| margin | Qt layout margins (over a hundred files) | code `room`; on screen "to spare", "over by" |
| scope | a principal's permission scope (Kernel) | `applies`, `ledger.applies/1`; on screen "applies from … to …" |
| scenario | `math_service` overrides, origin `DECLARED_SCENARIO` | reuse the origin; record `what_if`; on screen "What if" |
| instrument | the hardware instruments panel (instruments_qt.py) | `measure_tool`; on screen "what you measure with" |
| prediction | adaptive_work / adaptive_contract | `expected`; on screen "what I expected" |
| plan | her hand's planner (planner.py) | `test_plan`; on screen "what to measure next" |
| trace | `field.trace` | `coverage` |
| condition, interval, verdict, bound | condition cards; problem type interval; `Doubt.verdict`; `problems.BOUND` (the maths judgment's table) | "where it applies", "range", `state`, never "bound" |

On screen: "Apps", never "Programs"; no keyboard shortcut printed; a pipeline is "a line"; one assistant, Kasandra (Kas).
