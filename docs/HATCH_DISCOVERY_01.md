# Saved inquiries and Discovery IR — DISCOVERY-01

Open **Tools → Inquiries**, or use `/open inquiries`. A new inquiry needs a title, a question and one or more stopping criteria. Save revision records those words immediately; advanced structure is optional. Pin this workspace to keep unsaved edits while opening another Preview.

The Inquiry tab shows declared entities, dependencies, current status and why a binding changed. Optional structure contains editable JSON for sources, assumptions, hypotheses, constraints, candidate methods, proposed experiments, proposed claims, next actions and a budget. The visible title/question/stopping fields are the authority for those parts of the document. New inquiry and opening another saved inquiry replace the current editor; save work before switching. Check bindings preserves the editor buffer and does not advance its optimistic save revision. A competing save therefore requires reopening rather than silently overwriting newer work.

Checked predicates links existing numerical receipts. It never launches the calculation. Save draft changes first, select a target claim/hypothesis and a method in its declared dependency closure, then supply a reader, receipt/action ID, expected Boolean and note. **MATH** uses a completed math action ID, with a zero-based Boolean output index. **SCHEDULE** uses an exact schedule receipt ID and its fits predicate. The fixed adapters check owner, current inputs, model/argument identity and the selected method profile. Prepared actions without a completed receipt are refused.

## What the first IR contains

The canonical schema is `ledger.discovery-ir/1`, exposed by `discovery.schema` and in `docs/DISCOVERY_01/ir-schema.json`. It is an additive proposal format; the upstream staC grammar and legacy adaptive model profile are preserved.

| Collection | Meaning |
| --- | --- |
| goal | Original question plus explicit stopping criteria |
| sources | Named existing Ledger addresses and their role; captured by existing owner-aware readers |
| assumptions | Explicit text, scope, HUMAN/MODEL/IMPORTED origin label and DECLARED/UNKNOWN certainty |
| hypotheses | Proposed testable interpretations, not accepted facts |
| constraints | Named Algorithm Atlas contexts: typed models, owned problem bindings or declared graphs |
| candidate_methods | Atlas algorithm ID plus constraint reference; actual definitions/contracts are captured from the Atlas |
| experiments | Proposed check questions, method references and predicted observations; not executable plans |
| claims | Proposed statement and scope with explicit dependencies; no caller-controlled success status |
| next_actions | ASK, PROPOSE_CHECK or REVIEW proposals; not scheduled or authorized actions |
| budget | Existing Desk budget vocabulary; recorded intent, not an issued runtime grant |

Keys are unique across collections; goal is reserved. Dependencies must exist and be acyclic. Every inquiry-dependent proposal also depends on the goal. Candidate methods automatically depend on their constraint, and experiments on their method. Unknown fields, arbitrary execution commands, forged observation collections and claimed CHECKED_FORMAL/CHECKED_NUMERIC statuses in proposal JSON are refused. Text must be meaningful, and structure is strictly bounded.

The supplied origin field is an authored classification, not verified authorship. The stored record's owner and actor come from the actual Kernel principal. Source roles and links do not prove that a numeric model was correctly extracted from a document. That interpretation remains reviewable.

## Store and history

`discovery.create` and `discovery.revise` use the existing owner-private Desk records, event log and immutable revision history. No database migration or new scheduler is added. Revise requires the current expected revision and explicitly recaptures source/method bindings. Observation records are immutable, linked transactionally with a new inquiry revision. Repeating the same current predicate/receipt/dependency/note combination returns the existing observation instead of creating a duplicate.

`discovery.list` gives private summaries with the existing limit/offset pagination. The desktop picker shows the newest 100. `discovery.history` returns revision summaries; `discovery.get` can select a historical revision without restoring it over the current one. Historical inquiry documents and observations remain accessible after edits. The UI history is a read-only summary; detailed historical reads are available through the Kernel API.

## Freshness and declared dependencies

The inquiry also binds its schema and direct validation/receipt-reader source files. A changed protocol binding makes the goal and its declared descendants stale; explicit rebinding does not make historical checks current. This is a direct-source check, not a complete transitive software/environment fingerprint.

Source bindings reuse Desk snapshots and freshness checks. For small file sources, exact bytes and SHA-256 are retained under the existing reader limits; larger sources retain the existing hash/projection notice. Current reads do not rewrite saved snapshots. Method bindings include the source-bound Atlas definition, implementation, dependency state and canonical contracts, with caller scope-eligibility removed from identity. A read-only user can inspect the same owned inquiry without changing its method identity.

Constraint contexts containing a problem binding recheck the owner's current problem revision/context through the existing math/problem readers. A changed/unavailable source, changed Atlas binding or stale problem marks the affected declared descendants stale. Independent branches remain independent. New definition/source snapshots are captured only on an explicit revision save.

Each observation also binds the entire declared ancestor closure of its target. Editing a relevant assumption, constraint, method, source, goal or target invalidates the earlier observation; editing an unrelated branch does not. Receipt readers are rechecked when the inquiry is opened. Their changed or stale result invalidates the related check. Old checks are retained as history. A new explicit valid check can be current while earlier checks remain stale; historical failures do not permanently prevent renewed investigation.

This is declared-dependency invalidation, not automatic causal discovery. Omitted dependencies remain unknown. Shared Atlas corpus/adapter files can invalidate several methods conservatively. Transitive software dependencies beyond the Atlas's stated binding coverage are not fully identified. No automatic recomputation occurs.

## Numerical checks and claim language

Only two fixed observation profiles exist in this first pass: exact Boolean mathematical outputs and exact additive schedule fits. An actual current predicate may receive **CHECKED_NUMERIC**, with MATCH or MISMATCH against the explicitly supplied expected Boolean. That grade belongs to the bound predicate, not the nearby free-text claim. A current but unresolved/unsupported calculation receipt remains OBSERVED_ONLY and UNRESOLVED, never a successful numerical check. Unexecuted preparation is not a receipt.

A mismatch is a counterexample to that declared predicate expectation. It does not prove arbitrary prose false. Proposed claim/hypothesis text remains HYPOTHESIS or REVIEW_REQUIRED; changed dependencies can make it STALE. The system does not mark prose CHECKED_FORMAL, SUPPORTED_EMPIRICAL, ACCEPTED_METHOD or completed merely because a receipt was attached. It also does not treat tool failure or unknown as hypothesis refutation. Every view reports that completion is not authorized by this foundation.

The current adapters verify that the selected method is an admitted profile and is a declared prerequisite of the target. MATH requires the same typed model digest and exact/SYMPY/Z3 backend as that method. SCHEDULE requires the same problem/revision/context, capacity and allocation/lifetime arguments. A numerically convenient receipt from another model is refused.

## Interfaces and scope

Eight registered Kernel operations are added: schema, validate, create, revise, list, get, history and observe under `discovery.*`. Save/revise/observe require execute scope because they write records. Other operations require read scope. Standard Kernel audit/activity effects remain. No operation issues an execution grant, runs an experiment, invokes a model or launches a solver.

Embedded staC read forms:

```
inquiries
inquiry INQUIRY_ID | inspect
inquiry INQUIRY_ID | history
```

The general existing read pipeline and CLI/MCP also use the same registered operations. There is no extra shell/evaluator, dispatch authority, job runner or copy of the operation schema. The existing adaptive ACTION whitelist and actual-model profile are not expanded by this pass. Local-model generation of an inquiry and the constrained experiment/method compiler remain later integration work.

Documents are limited to 128 KiB and the schema's bounded collections. Captured source/method bindings are limited to 1 MiB combined. At most 32 observation links are admitted per inquiry in this version. Underlying source/receipt readers retain their own narrower bounds. Closed/stale records are retained; no purge, rollback overwrite or claim deletion operation is introduced.

## Campaign status

DISCOVERY-01 completes this bounded typed-record, dependency-view and checked-predicate foundation. It is not a completed Discovery Kernel, H03/H04 acceptance or HATCH release. Planned experiments are still proposals. Formal/empirical claim review, automatic model-to-IR normalization, constrained method composition, operation probe promotion, and real native owner interaction remain open. The owner's ThinkPad, real-model and native acceptance gates remain pending under the current direction to keep cloud implementation moving.
