# Kas keeps her reasons: the logic and proof lens for 0.8.6, "Kas's mind, no model"

*Design proposal, 20 November 2026. Lens: logic and proof. Read-only study of the code at HEAD, the half-build
`hand_s1_unfinished.patch` and the 0.8.5 maths patch. Every number in the examples is Rail Demo's invented data, the
maths core's own test vectors, or an invented everyday twin made for this page (a flat's deposit, a household budget, a
leaflet and a dose log). Nothing here is the owner's.*

---

## 1. The idea

Today Kas keeps her **answers**: a finding has its evidence rows, a calculation its inputs, a maths answer its receipt, a
doubt its line. What she does not keep, in one place, is her **reasons**: the chain from a verdict on the Field down to
the source cells, the owner's choices and the rules it stands on.

The proposal for this lens is one thing, with ten faces: **a reasons graph over the whole desk**, computed from the
records that already exist, four-valued (holds / does not hold / cannot tell / the records disagree), exact, and
model-free. Its leaves are reviewed cells at revisions, admitted sources with fingerprints, and *named assumptions*. Its
inner nodes are maths answers, checks, findings, goals and rules, each joined by a named rule of inference. Once that
graph exists, Kas can say, with zero model calls:

- **why** a verdict stands (a proof tree, with "for" and "against" side by side);
- **what it rests on** ("this rests on 3 assumptions; without this one, these 2 findings fall");
- **what must be true** (rules with "unless", applied exactly);
- **what cannot both be true** (contradictions, each with its smallest proof);
- **what could be wrong** (the few premises whose removal makes the desk consistent again);
- **what to recheck, in order** (and what is carried over with proof);
- **what would settle it** (the one reading, document or choice that decides a "cannot tell");
- **what is merely absent** ("nothing on the desk shows it" is not "it did not happen").

And because the graph names every open leaf and every candidate, **the model's part shrinks to filling small, typed
blanks that the graph generates and then checks**: which of 2 rows did you mean, which 4 slots of a rule does this
paragraph fill, which words say this proof. A model answer that would make the desk contradict itself is refused
before the owner sees it.

## 2. What already exists, and is reused

| Existing piece | What it already gives this lens |
|---|---|
| `workbench/stac/evidence.py` | Belnap's four values (`EvidenceSupport` positive/negative), `negate`, `truth_and`, `truth_or`, `knowledge_join`, `knowledge_meet`; `Applicability` (CURRENT, STALE, MISSING_SOURCE) kept separate from truth; `ScopedJudgement.admissible`. Not rewritten. |
| `workbench/reason_graph.py` + `reason_service.py` | A finite, acyclic support/refutation path calculator: ATOM, ASSUMPTION and CLAIM nodes, rules with premise polarity, every **path** carrying its `atoms`, `assumptions` and `rules` (these are exactly an ATMS's environments), budgets (64 nodes, 128 rules, 4,096 combinations, 256 paths), coverage stated as "outside the graph: unknown", `reasons.impact`. Today it serves the lab's declared graphs only. |
| `workbench/investigations.py` | Claims (FINDING, CANDIDATE, QUESTION), evidence rows SUPPORTS/OPPOSES with an **independence** key and a `stale` flag, checks with oracles, `claim_state` (four-valued from current independent evidence), `path()`, `next_action()`. |
| `workbench/field_doubt.py` | Fixed exact questions per kind of object (doubt / cannot tell / note / holds), each with a staC line (`see`); `_said_otherwise`, `_counted_twice`, `weak_check`, `_placed` (a number in words against the desk). |
| 0.8.5 maths core (`math_ranges.py`, `math_answers.py`, `tolerances.py`) | `ledger.math-answer/1`: state HOLDS / FAILS / UNDECIDED for the one real value, `for_all` with a witness, guarantee, at most 8 derivation steps, freshness, `model_calls: 0`; owner-only tolerances with APPLIES / CARRIED_OVER / RECHECK. |
| `goals.py`, `planner.py`, `hand_words.py` (hand_s1) | Goals from templates with states OPEN/HOLDS/FAILS/UNDECIDED/SEEN, origins OWNER/HER/**DEDUCED**/WORK_ORDER, `depends`; the planner's methods and search; the deterministic request match and the GOAL "pick" turn (`pick_message`, `read_pick`). |
| `conditions.py` | Binding to exact words: block id, offsets and quoted text; CURRENT / STALE / BROKEN when the words move. The same binding serves a rule's source span. |
| `field_ripple.py`, `field_model.py`, `field_service.py` | What lies downstream of a change; the Field's ranks (topological), wires, depth; the read operations `field.read`, `field.trace`, `field.whatif`, `field.doubt`. |
| `stacy_hand.py` | The dial and `ALWAYS_ASKS`: a new row for "what decides what I conclude" (tolerances already have one in 0.8.5). |
| `rail_demo.py` | The invented workspace every test below stands on. |

**One refactor rule.** `reason_graph.py` is hashed into the lab's reason results (`engine_binding` in
`reason_service.compute`). It is not edited. The desk graph uses a sibling, `reasons_desk.paths()`, with the same path
loop, proven equal to `reason_graph.compute` on every lab graph fixture by a differential test.

## 3. The four values, and four rules of honest logic

On screen the four values keep Graphite's existing words: **holds** (supported), **does not hold** (refuted),
**cannot tell** (neither), and **cannot tell: the records disagree** (both; never shown as "false"). Applicability stays
its own axis: anything resting on a stale premise reads **recheck**, whatever its value.

Four rules, each with a test file of its own (`tests_integrated/test_no_fallacies.py`), guard the classic mistakes:

1. **A rule that does not apply says nothing.** "If A then C" with A false gives no support to "not C". Only an
   explicit else-branch, written as its own rule, can (no denying the antecedent).
2. **A conclusion does not prove its premise.** C supported never supports A (no affirming the consequent).
3. **Absence is not falsity.** "Nothing on the desk shows a payment" is UNKNOWN about the payment until the owner says
   the record is complete (an explicit assumption); then, and only then, it is REFUTED.
4. **What is not agreed is not in.** An assumption or rule proposed by Kas or by a model never changes an official
   state. Its effect is shown as a hypothetical: "would hold if you agree A4".

## 4. The capabilities

Ten, in the order they stand on each other. Effort: S about a day, M two to four days, L a week, for one builder,
without Qt work where possible.

---

### logic-1 · Why: one reasons graph, and proof trees you can click through

**What the owner sees.** On any card of the Field (finding, goal, calculation, total, maths answer), "Why" in its
right-click opens a proof tree in her column: at most 12 lines, typewriter face, each line a statement with its state
word and where it comes from. Clicking a line selects that card on the Field; the wires of the proof light up and the
rest of the desk steps back (the Field's existing depth). Two tabs: **For** and **Against**. A footer under every answer
she gives: *"Rests on: 2 reviewed rows, 1 choice of yours. Model calls: 0."*

**Worked example (Rail Demo).** Why does *"Startup is inside the Rev B limit of 40 ms"* not hold?

```
Does not hold · Startup is inside the Rev B limit of 40 ms
  all of these are needed, and one does not hold                        (Graphite's rule: all of)
  ├ does not hold · 45 ms is at most 40 ms: over by 5 ms                (maths, exact · its receipt)
  │   ├ holds · Startup duration 45 ms        "Rail Demo bench readings" B5, reviewed from page 1
  │   └ holds · Startup duration limit 40 ms  "Rail Demo limits Rev B CURRENT" B3, reviewed from page 1
  ├ yours · Rev B is the revision that applies                          a choice you made on 20 Nov
  └ does not hold · its check: where parameter=Startup duration | where value at most 40
For it: nothing.  Against it: the bench readings (one independent source).
Rests on: 2 reviewed rows, 1 choice of yours. Model calls: 0.
```

Every inner line names its rule, including Graphite's own built-in ones (the "G-rules": *all of*, *any of*, *evidence
joined*, *a stale premise sends it to recheck*, *one independent source is a doubt*), each with its module and the hash
of its code, so "why is this a doubt?" ends in a rule the owner can read, not in "the program decided".

**How it is built.**
- `workbench/reasons_desk.py` (pure, no Qt): `graph(kernel, principal, field) -> DeskGraph`. Nodes are made from
  records, never typed by anyone: SOURCE (admitted, fingerprint, revision), ROW / CELL (reviewed row at revision),
  CALC (derivation inputs), ANSWER (`ledger.math-answer/1`), CHECK (investigation check, last outcome), FINDING
  (claim + `inv_evidence` with independence), GOAL (goals.py), CARD (condition card), ASSUMPTION (logic-2), RULE
  (logic-3). Justifications carry a rule name from a fixed vocabulary (`reads`, `worked`, `supports`, `opposes`,
  `checked`, `maths`, `all_of`, `any_of`, `joined`, `rule:<id>`).
- `reasons_desk.paths(target)`: the reason_graph path loop on the target's closure, plus **subsumption** (drop a path
  whose assumption set contains another's), within reason_graph's budgets. Past the budget: "cannot tell: too many
  reasons to follow", never a crash, never a guess.
- `reasons_desk.tree(target)`: the proof tree, as a record `ledger.proof/1` (computed on read; stored only when
  `stac.observe` keeps it), with a digest, so a proof is also a receipt.
- Kernel op **`field.why {id}`** (read), in `field_service.py` beside `field.trace`; its staC line
  `field.why {"id":"claim:<id>"} | pick tree | select depth,state,words,see` re-runs it exactly.
- Desk act **`sheet.why`** (navigates) in `desk_acts.py`, so her hand and scenes can open it.
- Field overlay: the proof's edge ids handed to the existing trace highlighting in `field_qt.py`.

**Needs the model?** No.

**How it helps the model.** The WORDS turn (at most 400 characters) gets the top two levels of the proof as a fixed
block of about 300 tokens instead of raw records; its words are then checked against the proof (logic-8). The NEXT turn
gets each option with a one-line proof summary. The model is never asked "why" about records: it only words a proof it
can see.

**Effort.** M.

**Proven by** (`tests_integrated/test_reasons_desk.py`, on Rail Demo):
- `why(startup_holds)`: state REFUTED; leaves exactly {readings B5 = 45 ms, limits Rev B B3 = 40 ms, assumption "Rev B
  applies", check outcome CHECK_FAILED}; the maths node's slack is exactly −5 ms; each SOURCE leaf's fingerprint equals
  the admitted source's.
- `why(settled_holds)`: SUPPORTED, For has 2 independent sources, Against is empty.
- Adding one OPPOSES row from a second source gives CONFLICT with both tabs non-empty and the words "the records
  disagree".
- Determinism: the same records give the same graph digest across two builds and two processes.
- With `local_brain` made unimportable, every output is identical and carries `model_calls: 0`.
- The lit wires equal the proof's edges, checked against `field.read` links.
- A synthetic desk whose target closure has 65 nodes answers UNDECIDED with the budget reason.
- Differential test: `reasons_desk.paths` equals `reason_graph.compute` on every lab graph fixture; `reason_graph.py`'s
  hash is unchanged.

**Risk.** A dependency recorded nowhere is invisible, so the graph can be incomplete. The words therefore never say
"nothing depends on it": they say "nothing on the desk's wires" (reason_graph already carries
`missing_dependency_excludes_no_impact_claim`). Large desks hit the budgets; that is said, not hidden.

---

### logic-2 · What it rests on: assumptions as records, and "without this one"

**What the owner sees.** Under "Why", a **Rests on** panel lists the assumptions a verdict stands on, whose each is
(yours, or hers and not agreed), and two buttons per assumption: *Without it* and, for a choice between revisions,
*With the other one*. A desk-wide register in the Field's foot: *"5 assumptions. 'Rev B applies' carries 4 statements,
2 of which would change without it."* Kas never assumes silently: any default she uses (the current revision, calendar
days, "this sheet is complete") becomes an assumption record marked **hers, not agreed**, and the official state is
worked out without it, with one line: *"It would hold if you agree A4."*

**Worked example (Rail Demo).** The goal *"Settled power is within the limit that applies"*:

```
Holds · 2.94 to 3.06 W against 4 W: 0.94 to 1.06 W to spare
Rests on 3 assumptions, all yours:
  A1  Rev B is the revision that applies                       a choice, 20 Nov
  A2  The bench at 25 C stands for the rail in use             your words, 20 Nov
  A3  Rail voltage is good to ±0.25 V                          your tolerance
Without A1: cannot tell.   With Rev A instead: holds, 1.94 to 2.06 W to spare.
Without A3: holds, exactly 1 W to spare.
Without A2: cannot tell. Nothing else on the desk says what the rail draws in use.
```

And for *"Startup is inside the limit"*: *"Whether startup is over the limit rests on one choice: that Rev B applies.
With Rev A it would hold, with 15 ms to spare."* The owner learns in one line which of his choices is load-bearing.

Hers, not agreed: in logic-3's example Kas needs *"A4: the startup current of 900 mA lasts for the whole startup"*.
Until the owner agrees it, the verdict is "cannot tell", with *"would not hold if you agree A4: 10.8 W against 4 W for
the last 5 ms."*

**How it is built.**
- `workbench/assumptions.py`: record `ledger.assumption/1` (kind `assumption`) through `project_desk` helpers, as
  `conditions.py` does. Fields: `statement` (template words or the owner's words), `sort` (BINDING, SCENARIO,
  REPRESENTS, COMPLETE, OWNER_SAYS, RULE_READING), `subject` (record addresses), `alternatives` (for a BINDING: the
  other revisions' rows), `set_by` (owner | kas), `agreed`, `state` (IN | OUT; retracting writes a revision, nothing is
  deleted), `basis` (the owner's words). Tolerances are not copied: `tolerances.standing` is read and each tolerance
  shown as a value assumption (RECHECK shows as OUT, with the 0.8.5 words).
- Two kinds, two mechanics. *Support assumptions* (a statement taken as true) appear in path labels: "without" is a
  label lookup, instant. *Value assumptions* (a tolerance, a scenario value, a binding's alternative) shape inputs:
  "without" or "with the other" re-evaluates only the affected statements, read-only, through the maths core, in the
  order logic-6 gives.
- Ops: `assumptions.list`, `assumptions.get` (read); `assumptions.propose` (draft: hers, never agreed);
  `assumptions.agree`, `assumptions.set`, `assumptions.retract` (approve), with one new `ALWAYS_ASKS` row in
  `stacy_hand.py`: *"an assumption is yours to say: it decides what I conclude."* Read ops `field.rests {id}` and
  `field.without {drop:[ids], with:[ids]}`.

**Needs the model?** No.

**How it helps the model.** A model never carries an assumption into a verdict: anything it takes for granted
("assuming the readings are at working temperature") becomes a proposal the owner sees, and changes nothing until
agreed. The model does not need to be told what was assumed earlier in a long conversation: the register says it, so
prompts stay short.

**Effort.** M (S once logic-1 exists, plus the record and its approve flow).

**Proven by** (`tests_integrated/test_assumptions.py`):
- `rests(settled goal)` is exactly {{A1, A2, A3}}; `rests(startup goal)` is exactly {{A1, A2}}.
- Without A1: settled goal UNDECIDED; with Rev A instead: HOLDS with spare exactly [31/16, 33/16] W; startup goal with Rev A:
  HOLDS with exactly 15 ms to spare. Without A3: HOLDS with exactly 1 W.
- Subsumption: a node with paths {A1} and {A1, A2} has the label {{A1}}.
- Not agreed: with A4 proposed, the official state is UNDECIDED and the hypothetical says "would not hold"; after
  `assumptions.agree(A4)` it is FAILS by exactly 34/5 W.
- Retract then agree again restores the label exactly; both revisions are in the history.
- The `ALWAYS_ASKS` matcher catches `assumptions.agree`, `.set` and `.retract` at all three dial settings; her
  principal cannot agree.

**Risk.** Noise: if every review were an assumption, every finding would rest on twenty. So reviews stay premises (shown
collapsed: "and 4 rows you reviewed"), and only the six sorts above are assumptions. Fatigue: an owner asked to agree
too often may agree without reading. Kas proposes an assumption only when a verdict depends on it.

---

### logic-3 · What must be true: rules with "unless", from the owner's own sources

**What the owner sees.** A **rule card** on the Field, wired to the paragraph or table row it was read from: *needs*
(the elements), *gives* (what follows), *unless* (exceptions), and optionally *otherwise* (an else-branch). For an issue,
an **elements checklist**: each element holds / does not hold / cannot tell with its evidence a click away, and each
"unless" row the same. Conclusions appear as **deduced** cards (origin DEDUCED, already in `goals.ORIGINS`), each with
its proof. When two agreed rules disagree and the owner has not said which governs: *"Two rules disagree; which governs
is yours to say."* Never deduced.

**Worked example, engineering (Rail Demo).** Rev B row 4 says *Startup power ceiling, 12 W, Up to 40 ms*. The
conditions column is where rules hide. Kas proposes, from that row:

```
Rule R1 (from "Rail Demo limits Rev B CURRENT", row 4)
  needs      startup duration ≤ 40 ms
  gives      the startup power limit is 12 W
  otherwise  after 40 ms, the settled power limit (4 W) applies        ← your reading of "Up to 40 ms" (A5)
```

With the reading of 45 ms the "needs" does not hold, so the 12 W ceiling does not cover the whole startup. The deduced
card: *"Cannot tell whether startup power stays inside the limit after 40 ms: the desk does not say what the current is
between 40 and 45 ms."* If the owner agrees A4 (900 mA for the whole startup): *"Does not hold: 10.8 W against 4 W for
the last 5 ms, over by 6.8 W."* With the startup tolerance ±5 ms, the "needs" itself is cannot tell, and the card says
*"the 12 W ceiling covers startup if it lasts at most 40 ms"*. No finding on the desk today makes this deduction; it is
the "footnote that qualifies a rating" trap of the owner's specification, caught.

**Worked example, everyday legal twin (invented "Deposit Demo").** A lease clause the owner admitted: *"The deposit
shall be returned in full within 14 days of the end of the tenancy, unless the check-out report records damage beyond
fair wear and tear."* Facts on the desk: keys returned **31 Aug 2026** (a reviewed row of the key receipt); deposit
850.00; a bank sheet for Sep to Nov 2026, 93 rows; today 20 Nov 2026.

```
Rule (clause 9 of the lease you admitted)
  needs   the tenancy ended                       holds   31 Aug 2026, the key receipt
          today is more than 14 days after it     holds   81 days    (A6, yours: "14 days" means calendar days)
          the deposit was not returned            cannot tell   nothing on "Bank Sep–Nov" shows 850.00 (logic-10)
  unless  the check-out report records damage     cannot tell   the check-out report is not on the desk
  gives   the full deposit was due by 14 Sep 2026
State: cannot tell. It holds unless the check-out report records damage; and that no payment was made rests on your
bank sheet being complete.
```

When the owner admits the check-out report (reviewed row: "No damage noted") and says the bank sheet is complete:
*"Holds, against clause 9 of the lease you admitted: the full deposit was due by 14 Sep 2026. Your bank sheet shows no
payment of 850.00, 67 days later."* Footer, always: *"Reasoning over your records and the text you admitted. It is not
legal advice."*

**How it is built.**
- `workbench/rules.py`: record `ledger.rule/1` (kind `rule`). `source` bound like a condition card (document, block id,
  offsets, quoted words; or a sheet row at a revision), `sort` (DATASHEET, CONTRACT, POLICY, STATUTE_TEXT, LABEL,
  HOUSEHOLD), `needs` [{about: cell address or statement id, relation le/lt/ge/gt/eq/ne, value, unit}], `gives`
  (a statement template or a binding), `unless` [{quoted span, shown_by: statement id or an absence pattern}],
  `otherwise` (optional), `overrides` [rule ids, set by the owner], `set_by`, `agreed`, `state` CURRENT / STALE.
- Pure evaluation `rules.evaluate(rule, desk)`: each element decided by `math_answers.answer(stage='check')` on the one
  real value (HOLDS → supported, FAILS → refuted, UNDECIDED → neither); date elements by exact day counts once the
  0.8.5 dates item lands (UNSUPPORTED before it). The rule fires when `truth_and(needs…, negate(unless)…)` is
  supported; an unknown exception therefore blocks, never passes. A rule that does not fire gives **no** support
  (rule 1 of section 3); `otherwise` is compiled as a second rule with the needs reversed. Several rules concluding the
  same statement are combined with `knowledge_join`; `overrides` drops the overridden rule's contribution when the
  overriding one fires.
- Each rule is one justification in the reasons graph (logic-1), so Why, Rests on and the recheck order cover rules
  for free. A STALE source span (the clause's words changed) takes the rule out until the owner agrees it again.
- Ops: `rules.list`, `rules.get`, `rules.check {id}` (read); `rules.propose` (draft); `rules.agree`, `rules.override`
  (approve, with an `ALWAYS_ASKS` row: *"a rule is yours to agree: it decides what I conclude"*); retiring is
  `rules.retire`, already caught by `*.retire`.
- `workbench/deposit_demo.py`: a second invented workspace beside Rail Demo (the "easy twin"), built the same way
  through the Kernel's doors, with its NOTICE on every page.

**Needs the model?** No. Rules are written by the owner, or proposed by Kas from a table row's conditions column by
template. A model may *propose* a rule from a paragraph (logic-8), never apply one.

**How it helps the model.** Once a rule card exists, the model is never asked to apply it: application is exact. The
model's whole part in rule reasoning is filling four slots from one paragraph, once, and that is checked. The
legal-sounding questions that LLMs get confidently wrong (deadlines, exceptions, which clause governs) are never put to
the model.

**Effort.** L.

**Proven by** (`tests_integrated/test_rules.py`, `test_no_fallacies.py`):
- R1 with 45 ms: the needs FAILS, the 12 W conclusion has no support, the otherwise-branch fires; with A4 agreed, FAILS
  by exactly 34/5 W; without A4, UNDECIDED naming the missing current; with ±5 ms, the needs is UNDECIDED.
- Deposit: 81 days and the due date 14 Sep 2026 exactly; with the report absent, UNDECIDED and the words "holds unless
  the check-out report records damage"; with the report "No damage noted" and the bank sheet's COMPLETE agreed, HOLDS,
  67 days after the due date.
- Fallacies: "if A then C" with A refuted leaves C UNKNOWN (never REFUTED); C supported leaves A unchanged; an exception
  UNKNOWN never lets the rule fire.
- An addendum rule (21 days) beside clause 9 (14 days), both agreed: CONFLICT with "which governs is yours to say";
  after `rules.override`, the due date is 21 Sep 2026.
- Changing the clause's words makes the rule STALE and not applied, as `conditions.assess` does for totals.
- A proposed rule changes no official state; `rules.agree` is caught by `ALWAYS_ASKS` at every dial.
- A word scan of every template: no "you will", "entitled", "safe", "should take", "advice" except in the fixed footer;
  every CONTRACT, STATUTE_TEXT and LABEL card carries the footer.

**Risk.** Turning prose into a rule is an interpretation; it can be wrong. Hence every rule shows its source words beside
its elements, the reading choices are assumptions (A5, A6), and only the owner agrees. Authoring is work: Kas proposes by
template from table conditions, and the model's slot-filling (logic-8) makes the rest a review, not a writing task.
Calendar months and business days wait for the dates item.

---

### logic-4 · What cannot both be true: contradictions across the desk, each with its smallest proof

**What the owner sees.** A count in the Field's head beside "to recheck": *"1 cannot both be true."* Each contradiction is
drawn as a wire between the cards involved, labelled *cannot both be true*, and listed among the doubts with its
smallest proof: the fewest statements that cannot all hold together. Nothing is called wrong: the words say which
statements clash and where each comes from.

**Worked examples.**
- *Two readings.* The summary says the rail settles at 250 mA; a later note says the meter showed 0.31 A. With the
  meter's ±2 % tolerance, 245 to 255 mA and 303.8 to 316.2 mA do not overlap: *"These two readings cannot both be right
  for the same rail at the same conditions."* (280 mA and 0.28 A are the same value and never clash.)
- *Rev A and Rev B.* 5 W and 4 W for the settled power limit are two revisions of one sheet: no clash, a change (the
  existing finding "the limit changed").
- *A timeline (legal twin).* The check-out report says the inspection was "after the tenant vacated", dated 29 Aug; the
  key receipt says 31 Aug. As a difference constraint, inspection − keys ≥ 0 and inspection − keys = −2 days: a negative
  cycle of −2 days, and the cycle is the proof: *"These three cannot all be true: the report's date, its 'after you
  vacated', and the key receipt's date."*
- *Money twin.* The lease says rent 950.00 a month; the standing order on the bank sheet pays 975.00 from October: same
  thing (rent, monthly, from October), two values: a clash, until an addendum on the desk explains it.
- *Rules.* Two agreed rules with different conclusions and no override (logic-3).

**How it is built.**
- `workbench/clashes.py` (pure): five detectors, each giving a **nogood** (the set of leaves and assumptions in its
  proof): (1) the same *fact key* (subject, property, conditions, revision scope) with different values, compared
  exactly in base units through `math_units` with fractions (not `field_doubt._same`, which is a float tolerance);
  (2) ranges that do not overlap, from `math_ranges` enclosures and the owner's tolerances; (3) dates and times as
  difference constraints from reviewed cells and owner-entered dates only, Bellman-Ford on exact integers, the negative
  cycle reported; (4) rules (logic-3); (5) any reasons-graph node in CONFLICT.
- Smallest proof: a deletion filter (drop one member, re-check with the same exact checker; keep it out if still
  inconsistent), giving a minimal unsatisfiable subset.
- Rows join `field_doubt.desk()` as verdict "doubt", about "cannot both be true"; Kernel op `field.clashes {}` (read).

**Needs the model?** No.

**How it helps the model.** A **consistency gate** on every model proposal (a binding, a rule, a mapping): before the
owner sees it, it is added hypothetically and the detectors run. A proposal that would make the desk contradict itself
is refused with the reason, and the next candidate taken. And the model is never asked "is anything inconsistent?"
across dozens of records, a task it does badly and slowly.

**Effort.** M.

**Proven by** (`tests_integrated/test_clashes.py`):
- 250 mA ±2 % against 0.31 A ±2 %: a clash; against ±25 % each: none; 280 mA against 0.28 A: none, exactly.
- Rev A 5 W and Rev B 4 W: none (two revisions of one pair).
- The timeline: a cycle of exactly −2 days whose members are the three statements; adding an unrelated date leaves the
  proof unchanged.
- Minimality, as a property over seeded random constraint sets: removing any member of a reported proof leaves a
  consistent set.
- An AST scan finds no float in `clashes.py`.

**Risk.** A fact key can join two different things that share a name ("limit" of two rails). Keys include the subject
and the conditions; where the subject is not recorded, the words say "if they are about the same thing". Dates are taken
only from reviewed cells and the owner's own entries, never from free text, so the timeline is smaller but true.

---

### logic-5 · What could be wrong: the few premises that would make the desk consistent again

**What the owner sees.** Under a contradiction, *"What could be wrong"*: the smallest sets of statements whose removal
clears every clash, each with what else would fall with it, and **which reading would tell them apart**. Stated as facts,
never as blame or likelihood.

**Worked example (Rail Demo, with the owner's requirement "startup must stay inside the limit").** Two clashes:
C1 = {startup reading 45 ms, Rev B applies, the requirement}; C2 = {startup reading 45 ms, Rev B applies, rule R1 and
A4, "startup power inside the limit"}. The candidates, each of one statement:

```
Either the 45 ms reading is wrong, or Rev B does not apply.
Everything else on the desk is consistent with both.
Measuring startup again would tell them apart: only the first rests on that reading.
The 45 ms has one independent source (the bench readings); Rev B is your choice of 20 Nov.
```

Legal twin: *"Either the report's date (29 Aug, one source) or the key receipt's date (31 Aug, two independent sources:
the key receipt and the agent's email of that day) is wrong."* The source counts are facts from `investigations`' independence
keys; Kas does not say which is wrong.

**How it is built.** `clashes.could_be_wrong(nogoods)`: Reiter's hitting-set tree, bounded to sets of at most 3 and at
most 32 candidates; statements the owner marked as requirements ("must hold") are left out of the candidates unless the
owner asks. For each candidate, the readings it contains that no other candidate contains are named as the
discriminating reading. Part of `field.clashes`.

**Needs the model?** No.

**How it helps the model.** It replaces the open question "what could be going on here?", which costs a long prompt and a
long, unverifiable answer, with a short exact list. If the owner asks in words, the model only phrases a list it is given.

**Effort.** S (on logic-4).

**Proven by** (`tests_integrated/test_could_be_wrong.py`): the two-clash example gives exactly {{reading 45 ms},
{Rev B applies}} and names re-measuring startup; on seeded random families of nogoods over a 10-element universe, the
tree's answers equal the brute-force minimal hitting sets.

**Risk.** Many candidates on a big desk; the bound is said ("and more; narrow the desk to see them"). Owners may read a
list as an accusation; the words stay factual and give source counts, not odds.

---

### logic-6 · What to recheck, in order: truth maintenance with proof

**What the owner sees.** When a source changes (a new revision admitted, a cell set, a page edited), one card: *"What
this changes"*, in three groups, in the Field's left-to-right order and, within a column, most load-bearing first:

1. **Carried over, with proof**: cannot have moved, because everything it reads is unchanged ("reads B2 and B4, which
   did not change").
2. **Worked again by Kas**: re-read and re-decided at once (maths answers, rules, clashes are reads); rewritten records
   (a calculation, a finding's words, a result paragraph) at the owner's dial.
3. **Needs you**: a row to review again, a tolerance in RECHECK, an assumption whose subject changed, a rule whose words
   moved.

And a **verdict diff**: which states moved and by how much. Before admitting a new revision, the same card answers
"what would this change?"

**Worked example (Rail Demo).** The settled current is set to 300 mA:

```
1 to work again: settled power, 3 W → 3.6 W                     (at your dial: working a calculation again)
1 to say again:  "Settled power is 3 W, inside the Rev B limit of 4 W"
                 → proposed: "Settled power is 3.6 W, inside the Rev B limit of 4 W"
4 carried over, with proof: startup power (reads B2 and B4), "Startup is inside the Rev B limit",
                 "The startup limit was 60 ms…", "The Rev B sheet carries the 40 ms…"
States: nothing changed state. Settled power's margin fell from 1 W to 0.4 W.
```

Today the whole sheet's calculations go to recheck (`field_ripple`: "any saved change to a sheet sends all its
calculations to recheck"); with the proof, startup power is *carried over* by a rebind instead of a rework. Before
admitting an invented Rev C with a 50 ms startup limit: *"'Startup is inside the limit' would go from does not hold to
holds, with 5 ms to spare; nothing else moves."*

**How it is built.**
- `workbench/recheck_order.py` (pure): the changed leaves (cells and rows by revision diff; sources by fingerprint; spans
  by `conditions.assess`) → their downstream in the reasons graph → topological order (the Field's ranks) → each node
  classed: CARRIED (every premise value-identical: same value, unit and conditions at the new revision, the same rule as
  0.8.5's CARRIED_OVER for tolerances), REDECIDED (a read: maths answers, rules, clashes, doubts), REWRITE (a record
  write through its existing op: `office.datasheet.recheck` HERS_FREE, `conditions.recheck` and
  `investigation.refresh` HERS_SHOW), OWNER (a review, a tolerance or assumption in recheck, a STALE rule).
- A "rebind with proof" op for CARRIED records that hold a state (a calculation's source state): a write whose only
  content is "bound to revision n+1, inputs identical", added to HERS_SHOW with an Undo.
- Read op `field.recheck_order {changed?}`; the what-if form reuses `field_ripple.ripple` for the would-be values.
- The rule that makes this simple: **reading again is hers; writing again is at your dial.** Verdicts are computed on
  read, never stored as truth, so re-deciding costs nothing and needs no Approve.

**Needs the model?** No.

**How it helps the model.** The model is never asked what to recheck. After a change, only prompts for affected goals are
rebuilt; unaffected prefixes stay cached (the prompt reuse of the NEXT turn).

**Effort.** M.

**Proven by** (`tests_integrated/test_recheck_order.py`):
- Settled current 300 mA: REWRITE = {settled power}, words to propose = {settled_holds}, CARRIED = exactly the four
  named; the margin goes from exactly 1 W to exactly 2/5 W.
- A new readings revision with identical values: every node CARRIED, zero rewrites.
- Rev C fixture: exactly one state moves, FAILS → HOLDS with 5 ms spare.
- Order: for every wire a → b on the Field, a comes before b.
- The Kernel's audit shows no record write during the REDECIDED step; at Ask first every REWRITE waits (as in P05).

**Risk.** A rework storm on a big desk: the card is bounded to the first 20 per group with "and n more". Rebinding is only
safe when the premises are complete in the graph; where the graph's coverage is not complete (an uncovered record kind),
it falls back to today's recheck.

---

### logic-7 · What would settle it: from "cannot tell" to the one thing that decides

**What the owner sees.** On a "cannot tell", a short list under **What would settle it**, each item one of: a better
reading, a document to admit, a row to review, a choice that is the owner's, an exception to look up. Items that decide
the question alone come first; then pairs. And **What would make it hold**: the smallest changes that would turn it
around. When exactly one item is open, Kas does not ask; she says what she is about to read or asks the one question.

**Worked examples.**
- Rail Demo, startup with the stopwatch good to ±5 ms (40 to 50 ms): *"A reading good to better than 5 ms would settle
  it: it would not hold."* (Break-even from the maths core's goal face.)
- Settled power, with no tolerance yet on the current: *"Already settled: with your voltage tolerance, any current up to
  326 mA keeps it inside, so no tolerance under 76 mA on the 250 mA reading could change the answer."* (Weakest
  precondition from `solve`: 16/49 A exactly.)
- Deposit: *"Needs both: the check-out report, and your word that 'Bank Sep–Nov' is complete. Neither alone decides it."*
- What would make startup hold: *"Startup at most 40 ms, or Rev A applying."*

**How it is built.**
- `workbench/settle.py`: regression over the reasons graph and rule cards from the target to its open leaves (UNKNOWN or
  STALE premises, unagreed assumptions, exceptions not shown either way, absences without COMPLETE). A leaf is
  **decisive** when setting it supported, and setting it refuted, both decide the target: two exact four-valued
  evaluations per leaf; pairs only when no single leaf decides, at most 12 leaves. For numeric leaves the maths core's
  goal-face functions (break-even, decisive share, value of information, from the judged design) give the size of
  reading needed; this module does not duplicate them.
- "What would make it hold": minimal sets of leaf changes giving a positive path (abduction over the same graph,
  bounded to sets of 2).
- Read op `field.settle {id}`; desk goal hook `settle.next_options(goal) -> [≤ 4 options]`.

**Needs the model?** No.

**How it helps the model.** This is the B2 arm of the I05 experiment made general: *deduction wherever only one step is
possible*. One open decisive leaf: the next step is deduced, model turns 0. Several that tie: the NEXT turn gets at most 4
options, each with its one-line reason, under 1,600 tokens, instead of a desk description. The planner's own choices get
the same treatment: an act's preconditions are premises, so "why this act first" is a proof too.

**Effort.** M.

**Proven by** (`tests_integrated/test_settle.py`):
- ±5 ms: the only open leaf is the startup reading's range; decisive alone; tolerance under 5 ms gives FAILS, 5 ms or more
  UNDECIDED, exactly.
- Deposit: no single leaf is decisive; the pair {report, COMPLETE} is.
- Decisiveness, as a property: on seeded random four-valued formulas with up to 8 leaves, it equals brute-force
  enumeration of completions.
- B2: with one open leaf, a fake brain that fails the test if called is never called; with three tied options, the NEXT
  prompt is at most 1,600 tokens.

**Risk.** Leaves multiply on rich goals; bounded to 12 leaves and pairs, beyond which the words say "too many open
questions to rank; here are the first". "Decisive" is about the records' logic, not the world: a new document can
always add a premise.

---

### logic-8 · The model's small questions, built by logic and checked by logic

**What the owner sees.** When the desk's own words do not settle something, Kas asks the model one small question and
shows the answer as **the model's reading, not yet agreed**, with the check it passed. If the model is wrong in a way the
records can show, the owner never sees that answer; the trail says it was refused and why.

**Three new question kinds** (beside GOAL and NEXT):
- **BIND.** "Which row does *'the startup limit'* mean?" Candidates by logic: only rows whose quantity is a time and whose
  name or role marks a limit: Rev A B3 (60 ms) and Rev B B3 (40 ms), not the 45 ms reading. The answer is one number.
  The result is an assumption of sort BINDING, hers, not agreed (which limit applies is never deduced).
- **RULE.** One quarantined paragraph (fenced, with its source and revision, and the statement that nothing inside is a
  request) and a template with four slots: needs, gives, unless, otherwise. The answer is checked: every number and unit
  in the slots appears verbatim in the paragraph; every relation is one of six; every "unless" is a verbatim span (bound
  by offsets like a condition card); every named record exists and has the right kind of quantity; the consistency gate
  (logic-4) passes. Then it is a *proposed* rule, marked as the model's.
- **WORDS.** At most 400 characters paraphrasing a proof (logic-1). Every number in the words must be in the proof
  (`field_doubt.said_quantities`, compared exactly), every quoted title must be a title in the proof, and the relation
  words (over, under, inside, short) must match the proof's states. Failing words are dropped and Kas's templated words
  shown; passing words are shown marked as the model's.

**Worked example.** The clause (Deposit Demo, 27 words) and the template: about 650 prompt tokens. The model
answers `needs: tenancy ended; today − end > 14 days; deposit not returned · gives: full deposit due · unless: "the
check-out report records damage beyond fair wear and tear"`. Checked: "14 days" is verbatim; the unless span is at
offsets 87–148 of the clause; the deposit row exists (850.00). Proposed. If it had said "21 days": refused, "21 days is
not in the paragraph".

**How it is built.** `workbench/logic_questions.py`: `bind_question`, `read_bind`, `rule_question`, `read_rule`,
`words_question`, `check_words`, following `hand_words.pick_message` / `read_pick` and `local_brain`'s pick mode with a
grammar-constrained answer. Fencing as the quarantine rules of section 15 of the specification. The model's answers go
through `assumptions.propose` and `rules.propose` only.

**Needs the model?** Yes for the answers; every builder and checker runs and is tested without it.

**How it helps the model.** Each question is finite (at most 8 candidates or 4 slots), under 1,200 prompt tokens and
120 answer tokens, and its answer is checked by the same exact logic that will use it. The model does recognition, the
one thing it is good at; the desk does everything that must be right.

**Effort.** M.

**Proven by** (`tests_integrated/test_logic_questions.py`, and `workbench/logic_model_checks.py` which needs a model):
- `bind_question("the startup limit")` offers exactly [Rev A B3, Rev B B3].
- `read_rule` refuses a number not in the paragraph, a relation outside the six, a non-verbatim unless, a missing record,
  a proposal that would clash; accepts the valid one as `agreed=False`, origin MODEL.
- `check_words` accepts "Startup is 5 ms over the 40 ms limit", refuses "6 ms over" and "5 ms under".
- On the 4B here: six frozen paragraphs (three engineering, three everyday), expectations frozen before inference; passes
  when at least 5 of 6 are exact after the checker, **no wrong answer is accepted**, every prompt is at most 1,200
  tokens and every turn at most 60 s.

**Risk.** A small model's answers may be refused often (false refusals are acceptable; false acceptances are not). The
checker sees numbers, names and relation words, not the whole meaning of a sentence; a wrong reading that uses the
paragraph's own numbers can pass, which is why it stays a proposal for the owner to agree.

---

### logic-9 · Remembering what worked: the model is asked once per phrase

**What the owner sees.** After he agrees that *"the limits"* means the Rev B pair, the next request that says it is
matched by the desk itself, with no model; Kas's card says *"'the limits': your phrase, agreed 20 Nov."* A small list of
his phrases in her settings, each retirable. When a kind of model question keeps being corrected, Kas says so and asks
the owner directly: *"I ask you directly now: the model's readings of rules were corrected 4 times in 6."*

**How it is built.**
- `workbench/aliases.py`: record `ledger.alias/1` {phrase (normalized words), target (sheet, row, rule or
  assumption), scope (FOLLOWS_CURRENT_REVISION or THIS_REVISION, the owner's choice), agreed_by owner, made_from (the
  model job and the trail entry of the agreement)}. `hand_words.match` consults aliases before the GOAL turn. Ops
  `aliases.list`, `aliases.get` (read); made only by agreeing a BIND (approve); `aliases.retire` asks.
- Proof memo: a proof's digest is keyed by the implementation hash and its premises' digests; identical premises give the
  same proof without recomputation.
- A tally per question kind of agreed / corrected / refused, read from the trail; a fixed policy (after at least 5, more
  corrected than agreed) sends that kind to the owner; it resets when the model file changes.

**Needs the model?** No (the owner can also name a phrase himself).

**How it helps the model.** Model turns fall with use: each phrase is asked once, and kinds of question the model does
badly stop being asked. A measurable number for every release: model turns per request, falling.

**Effort.** S.

**Proven by** (`tests_integrated/test_aliases.py`): the same request twice, the second with model calls 0 and an identical
plan; admitting Rev C moves a FOLLOWS_CURRENT_REVISION alias to Rev C with the words saying so, and leaves a
THIS_REVISION alias on Rev B; the tally policy switches after the fifth correction and resets on a new model digest; the
proof memo's counter shows one computation for two identical requests.

**Risk.** A phrase's meaning drifts ("the limits" next year). Scope is the owner's choice and every use is shown; aliases
are local, never leave the machine, and are listed for retiring.

---

### logic-10 · Absent is not false: coverage, and the owner's word that a record is complete

**What the owner sees.** Whenever Kas looked for something and did not find it, she says what she searched, at which
revisions, and stops there: *"Nothing on 'Bank Sep–Nov' (93 rows, revision 2) shows a payment of 850.00. Whether none was
made rests on that sheet being complete, which is yours to say."* With the owner's COMPLETE assumption, the statement
becomes *"No payment of 850.00 was made between 1 Sep and 20 Nov, by your word that the sheet is complete."* Engineering:
*"No reading on the desk was taken below 25 C"* before anyone claims the limit holds in the cold.

Everyday medicine twin, kept on the owner's side of the line: the owner admitted a leaflet that says *"at least 4 hours
between doses; no more than 4 doses in 24 hours"* and keeps a dose log. Log for 12 Nov: 08:00, 11:30, 16:00, 20:00, 23:30.
*"Against the leaflet you admitted: on 12 Nov your log shows 5 doses within 24 hours, and 3 h 30 min between the first
two. This reads your log against the leaflet;
it is not medical advice."* Kas never computes a dose to take and never says "safe".

**How it is built.** `workbench/absence.py`: `absent(pattern, scope) -> {searched: [sources with revisions], rows,
found: 0, words}`, searching with lines (`where … has`, exact keys, `count`) and Find; its statement is UNKNOWN until a
COMPLETE assumption (logic-2) with a matching scope (the sheet, a date range) is agreed. A new sheet in the scope sends
the absence to recheck (logic-6). The dose-log check is two rules (logic-3) over difference constraints (logic-4).

**Needs the model?** No.

**How it helps the model.** The model is never asked whether something exists; Kas searches exactly and states coverage.
`check_words` (logic-8) refuses model words that turn an absence into a fact ("no payment was made") unless COMPLETE is
agreed, and allows "nothing on the desk shows".

**Effort.** S.

**Proven by** (`tests_integrated/test_absence.py` and `test_no_fallacies.py`): 93 rows searched, found 0, the state
UNKNOWN; after the owner's COMPLETE for Sep–Nov, REFUTED; adding a December sheet leaves Sep–Nov's statement as it is and
a question about December UNKNOWN; the dose log gives exactly 5 doses in the 24 hours from 08:00 and a 210-minute gap.

**Risk.** An owner may agree "complete" too easily; the assumption's words name the exact sheet and dates, and it shows
in every Rests on.

## 5. How the model's part gets smaller

| Question | Today | With this lens | Skipped when |
|---|---|---|---|
| GOAL (which goal was meant) | every unmatched request | the same, under 1,200 tokens | the request matches, or an agreed alias covers it (logic-9) |
| NEXT (which step) | the profile's options, or a long loop | at most 4 options ranked by decisiveness, under 1,600 tokens | one decisive open leaf: deduced (logic-7) |
| BIND (which row is meant) | not asked; guessed in long prompts | at most 8 candidates of the right kind | an alias exists; or one candidate and the owner already chose |
| RULE (fill four slots) | not possible | one paragraph, under 1,200 tokens, checked | the rule card exists: never asked again |
| WORDS (the finish) | free text over records | at most 400 characters over a proof, checked | Kas's templated words are always enough |
| "Is this consistent?", "what could be wrong?", "what to recheck?", "does this exist?" | asked in prose | never asked | always |

The honest baseline (specification, section 14): today's loop made 3 correct decisions, then hit the 180-second wall
after 651 s and 30,827 tokens. With these pieces, the Deposit question costs 0 model turns once its rule card exists,
one RULE turn if it does not, and 0 forever after.

## 6. Keeping legal and medical help on the owner's side of the line

The design keeps the line by structure, not by disclaimers alone:

1. **Rules come only from text the owner admitted** (a lease, a leaflet, a statute's text, a datasheet), bound to the exact
   words, and apply only when the owner agrees them. Kas does not supply law or medicine from a model.
2. **Verdicts are relative and templated**: "holds against clause 9 of the lease you admitted", never "you are entitled",
   "you will win", "it is safe". A word scan in the tests enforces it.
3. **Every CONTRACT, STATUTE_TEXT and LABEL card carries the footer**: "Reasoning over your records and the text you
   admitted. It is not legal advice" (or "medical advice").
4. **Which rule governs, which version is in force, how "14 days" is counted** are the owner's choices (assumptions),
   never deduced.
5. **"Cannot tell" is a full answer**, with what would settle it. Nothing is rounded toward comfort.
6. **Kas never computes a dose to take, a sum to claim or a deadline to rely on as advice**; she checks a record against
   a text and says what the records show.
7. **Outside text is information.** A clause that says "the tenant agrees to ignore…" or a page addressed to an assistant
   is quarantined text inside a fence; it can be quoted in a rule's source, never followed.

## 7. Order, and the three to build first

**First, the three that work on the records that exist today, with no new authoring:** logic-1 (Why), logic-2 (Rests
on; nearly free once the graph exists, since the paths already carry their assumption sets), logic-7 (What would settle
it; the B2 bet of I05). Together: about 8 builder-days, no Qt beyond the overlay and the column.

**Then:** logic-4 and logic-5 (contradictions and what could be wrong), logic-10 (absence), logic-6 (recheck order).
**Then, with the Deposit Demo fixture:** logic-3 (rules with unless, the legal core), logic-8 (the model's new small
questions), logic-9 (remembering).

If the pass must be smaller, 1 + 2 + 7 + 4 + 10 is the floor that changes what she can honestly say.

## 8. Honest limits

- This is reasoning over the desk's own records: propositional, rule-based and exact, with no understanding of text that
  is not in a record. A dependency recorded nowhere is invisible; "no impact" is never claimed.
- It decides only what the maths core decides: one unknown at a time, straight-line relations, no splitting at poles;
  calendar months and business days wait for the dates item of 0.8.5.
- Reason paths can multiply. Budgets (64 nodes per closure, 256 paths, 4,096 combinations, 12 leaves, hitting sets of 3)
  turn a too-large question into "cannot tell", said as such.
- Rules are the owner's readings of his sources. A wrong reading gives exact, wrong conclusions; the source words beside
  every element are the defence, not a guarantee.
- "What could be wrong" names candidates and what would tell them apart; it never knows which premise is wrong.
- The WORDS check sees numbers, titles and relation words, not a sentence's full meaning; the model's words stay marked
  as its own.
- Ten capabilities are more than one pass; section 7 orders them.
- Nothing here has been run, and nothing is measured on the ThinkPad.

## 9. Names, checked against Graphite's existing meanings

New: modules `reasons_desk`, `assumptions`, `rules`, `clashes`, `recheck_order`, `settle`, `logic_questions`, `aliases`,
`absence`, `deposit_demo` (none exists); records `ledger.assumption/1`, `ledger.rule/1`, `ledger.alias/1`,
`ledger.proof/1`; read ops `field.why`, `field.rests`, `field.without`, `field.clashes`, `field.recheck_order`,
`field.settle` (beside `field.trace`, `field.whatif`, `field.doubt`); desk act `sheet.why`. Avoided: "condition" (condition
cards; a rule's parts are *needs* and *unless*), "bound" and "interval" (problem bindings, maths), "admissible"
(`ScopedJudgement`), "verdict" as a field (`Doubt.verdict`; the field is `state`), `reasons.*` (the lab's reason graphs).
On screen: "Apps", "a line", one assistant, Kasandra, no key printed.
