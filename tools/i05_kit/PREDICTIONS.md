# The I05 predictions

Copied word for word from the design of 0.8.6, "Kas's mind, no model", section 6.4, written on
20 Nov 2026 before any code of the arms. Nothing below is changed after a run.

### 6.4 The I05 measurement, with its predictions written in advance

**The arms.** Arms A, B1, B2 and B2@4096 are **exactly as pre-registered in the specification (section 14)**: the same
model file, cases, budgets and threads; three repeats per arm, interleaved; the disk cache dropped before each. Two arms
are added, and named as additions:
- **B3:** B2, plus the brief and the checker. There is no prompt reuse; that is 0.8.7.
- **N:** no model at all. The steps come from deduction:
  - the I05 operations (`work.read`, `methods.preview`, `methods.instantiate`, `methods.run`, `joined.*`) become a second
    operator table for the **same planner**, with their preconditions and effects. That is the Apps-ready format of S0
    put to work.
  - the mapping comes from unique typed matching: the capacity is the only current with no lifetime, and each demand is
    paired with its `*_life` row by exact name with a separator.
  - each declaration is licensed only by a phrase in the assumptions ("half-open lifetimes"; "present and unbounded"
    gives UNSUPPORTED).

**A sealed fourth case, D.** An agent that does not write the deduction rules writes it: different names and units,
assumption sentences in other words. It is committed as a sha256 **before** the rules are frozen and opened only at the
run. The report says plainly that cases A to C were known to the rule writer.

**Measured:**
- pass or fail per case;
- model turns;
- prompt and answer tokens;
- seconds per turn;
- repeats blocked;
- how often B1 picked the planner's top option;
- "finished with an open condition", which must be zero;
- for N, questions to the owner.

| Arm | Prediction (written 20 Nov 2026, before any code) |
|---|---|
| A | fails at least 2 of 3 cases on the 180 s decision wall (the baseline: 3 correct decisions, then the wall at 651 s and 30,827 tokens) |
| B1 | passes at least 2 of 3; 7 to 9 NEXT turns per passing case, 13 to 30 s each; the planner's top option picked at least 80 % of the time |
| B2 | passes 3 of 3 with at most 3 model turns per case, every turn at most 60 s here, total tokens under half of A's (the specification's prediction, unchanged) |
| B2@4096 | the same as B2: the context is not the bottleneck |
| B3 | passes 3 of 3 with at most 2 model turns and 1,500 prompt tokens per case, at most 30 s per case here; with the 2B, passes at least 2 of 3 |
| N | passes 3 of 3 with 0 model turns, under 10 s each. On sealed case D: **never a wrong verdict**; predicted to ask the owner one question (an assumption sentence outside its frozen phrase list) rather than pass outright |
| all | no arm repeats a step or finishes with an open condition |

**What would change the plan:**
- If N passes all four cases including D, the report says plainly: *"I05 does not need the model. On such tasks the
  model's part is reading assumption sentences the desk has no words for."*
- If B1 beats B2, the model adds judgment that deduction lacks, and 0.8.7 gives it more of the steps.
- If B3 does not use at least 30 % fewer tokens than B2, the brief is not helping, and 0.8.7 rethinks it.
- If B2 fails on the 4B, the 4B is too small, and nothing is said about the 35B until the kit runs on the ThinkPad.
- If B2 fails on the 35B there, **the central bet of the specification is wrong, and that will be said plainly.**

The run is long (several hours on the 4B here). It runs unattended at the end of the pass, with a kit packed for the
ThinkPad.
