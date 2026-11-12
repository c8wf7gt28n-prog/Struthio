# HATCH MEMORY-01

November 3, 2026 · America/Phoenix

Full checkpoint over RETURN-01. Existing private memory is now filed under
Ledger → Slate memory in the logical cabinet (or the cabinet root when the
catalogue has no Ledger object). Directions, Task memory, Procedures and the
Personality reference retain their original provider identities. No second
memory database, automatic collection, model training or execution authority
is introduced.

## Filing and reading

`memory.cabinet` is a shared read projection over the existing owner-filtered
`stacy_memory` table. The existing cabinet detail command resolves typed targets:
`memory:feedback:ID`, `memory:task:ID`, `memory:lesson:ID` and
`memory:profile:current`. Drawers are presentation views, not filesystem paths
or permissions. The original Memory and Settings workspaces remain linked from
the contextual action shelf; all earlier routes remain available.

The projection reads stored records with a 4 MiB cumulative payload budget,
128 KiB per record and at most 4,000 eligible rows; public result limit is
1–1,000 (cabinet default 300). It verifies stored digests and minimum shapes,
uses owner predicates before display, and skips corrupt records with a partial
view notice. Incomplete direction history disables guarded editing. No source
files, model inference or engineering/native tools run during browsing. Existing
Kernel operational auditing remains; this is not a zero-database-write claim.

Directions show saved wording, context, origin and history state: active,
superseded, undone, forgotten or incomplete. Profile state is reported separately;
an enabled profile does not establish actual model compliance or guarantee a
particular direction is selected in every response. A missing/corrupt profile is
not silently enabled or replaced. Imported reference bytes remain in the
existing store and are not returned as base64 by this projection.

Task filing retains the original task and checkpoint identifiers. Its explicit
Read task history action uses `memory.task`, with the original checkpoint/readback
and resume controls available in Memory. This slice does not reinterpret owner
task notes as measurements or evidence.

Procedure bodies are always withheld by the new browse/detail adapter, including
for previously reviewed procedures. It displays review metadata with bindings
NOT_RECHECKED. Check procedure sources invokes the existing `memory.lessons`
reader, which rechecks bindings and withholds unavailable text. A review label
does not establish source freshness, truth or permission to execute anything.
The original source-aware recall path is unchanged.

## Corrections and retained history

`memory.direction.revise` requires approve scope and is forbidden in Tutor mode.
The existing memory cloud-private prefix covers both new operations. Corrections
use a new caller-supplied event ID, an expected history digest, corrected wording
(1–300 characters) and an owner reason (1–200 characters). Blank wording/reasons
are refused by the existing text validators as well.

Inside BEGIN IMMEDIATE, the adapter verifies the currently owned direction and
the complete inspected preference/context family, including reachable forgotten
history tombstones. A family change or inactive target blocks a new correction.
Unrelated contexts do not invalidate the inspected family. A matching event ID
may be retried without creating another event; different input under the same
ID remains a conflict.

The original feedback branch was extracted unchanged into `commit_feedback` so
both routes can use the same logic inside their own transaction. A correction
retains the prior agreement value and preference/context, uses the original
persistent owner-correction semantics, and supersedes the existing family while
leaving all prior event records untouched. The owner's reason becomes its
source reference. Existing Undo can remove the new correction from active
learning and reactivate the earlier directions. Forgotten text is not recovered
from its tombstone; separately retained recovery copies remain separate.

The cabinet editor uses a flat yellow poem passage and an explicitly labelled
reason. Revise this direction arms the shown history, then Keep correction and
history submits it. Historical/incomplete entries stay read-only here. There is
no direct overwrite of an old feedback row and no edit of the imported seed.

## Draft continuity

Unfinished correction text and its reason use the existing return-copy draft
shape (`text` and `title`; reason limit is within its 200-character title bound).
They survive record switches and a normal close/restart. The old history guard
is deliberately not silently recreated from a fresh record on reopening.
Recovered corrections have Keep disabled until the owner explicitly chooses
Use this shown history for the recovered correction. The backend still rejects
a further change after that review. Recovery writing does not itself apply a
memory correction.

The original code recovery, return thread, fixed Trash, visible Stop, monitors,
cabinet/settings navigation and five-item Hatch menu remain. No setting or
Explore workspace adapter was added; the new memory roles navigate to existing
Memory and Settings controls.

## Verification and limits

- 23 distinct focused checks passed in 3.858 seconds: nine new memory checks
  and fourteen Cabinet regressions. Cases cover private identity, mode/scope,
  cloud privacy, procedure-body withholding, stale history, unrelated contexts,
  idempotent retries, original Undo, forgotten/corrupt records and input bounds.
- Fourteen actual offscreen Qt checks passed. They exercise tree filing,
  correction saving through the original preference path, retained old words,
  pending drafts, stale edits, explicit refreshed review, procedure/task readers,
  fresh-desktop recovery and laptop layout. Five actual window captures are
  retained under `docs/MEMORY_01`.
- UI data is disposable: a small imported owner-reference fixture, explicit
  feedback, a task/checkpoint and a proposed procedure with an empty reference
  list. The missing-source behavior is a controlled boundary-test observation;
  the UI does not establish external-source freshness. No model, provider request,
  engineering/native tool, job submission, Master Stop or OS-priority change ran.
- The existing profile-context reader reflects the corrected direction, and
  the imported profile hash is unchanged. This proves the data path, not that a
  running model follows the direction. Full historical tests were not rerun.

Registry: 690 operations, all 688 baseline schemas/scopes unchanged; 112 job-tool
targets unchanged; 26 settings, 15 Explore workspace adapters and 12 authored
method profiles unchanged. Explore now projects 829 combined entries. Discovery's
protocol-bound files and all historical evidence remain unchanged.

HATCH remains 0/6 formally accepted; integrated remains 4/6 in retained evidence.
I05 exact-model/native and I06 owner-host gates remain OPEN. ThinkPad, live model,
native handoff, pointer dragging, live scheduling and owned Stop still need their
proper acceptance environment. The connected UI is ready for owner review.

Next bounded slice: expose remaining personality/memory configuration through
the shared settings hierarchy with current-value readback, preserving existing
approval, provenance and source-authority boundaries. Procedure/task editing
and profile import/review retain their established Memory workspace controls.
