# HATCH RETURN-01

November 2, 2026 · America/Phoenix

Full checkpoint over ACTIONS-01. This slice adds a **Return thread** to the
activity footer, a retained central session room, and an explicit leaving review.
It gives unfinished cabinet writing a return copy and reuses the original code
recovery store. Saved return writing is distinct from project records, source
files, engineering evidence and model memory. It is never executed as a command.

## What the owner sees

- Return thread in the persistent activity footer, also Ctrl+Alt+R and a window
  action discoverable by the existing command palette.
- A yellow poem writing passage: Next time, begin here. Keep for return saves
  the note and cabinet drafts and keeps current code recovery copies.
- Still on the desk: current open work and buffer-edit state. Go to selected
  work navigates to the same live tab without replacing a buffer.
- Cabinet writing to continue: readable current cabinet labels, stored-versus-
  current recovery status, review of exact writing and checked record reopening.
  If a record disappeared, recovery writing remains readable/copyable; it is not
  silently assigned to another record.
- Recorded activity from the existing Operations read, labelled as stored work
  states rather than a verified census of live processes.
- Review leaving: Continue working is focused initially. Keep and close uses
  the ordinary close path with return capture. Close without a new return copy
  explicitly preserves the earlier stored copy and may lose newer thread/draft
  writing. Existing file-save prompts still apply. Closing LS leaves Linux on.

The page scrolls at laptop size. The original fixed Trash, host monitors,
Operations/Context/Slate, all Hatch items and the visible original Master Stop
remain. The return room uses graphite reading, pink actions and a flat yellow
writing passage. It introduces no new Hatch menu item or workspace setting.

## Shared saved state

`ledger.session.read` requires read scope. `ledger.session.keep` requires execute
scope and is forbidden in Tutor mode. Both are covered by a new cloud-private
session prefix. They route through the original Kernel/CLI/MCP machinery.
No new execution dispatcher, model worker or host-power operation is added.

The Kernel's existing workspace database holds one `session_handoffs` row per
principal identity. The row stores a note, cabinet draft IDs/titles/text, an
optional cabinet selection, a revision, a digest and a time. A read does not
create the handoff table. A keep validates the complete bounded payload and
compares the retained revision inside BEGIN IMMEDIATE. No-op keeps retain the
revision. A new keep increments it. Other owners and workspaces have separate
copies; no ownership is inferred from an ID in saved writing.

Limits: 8,000 note characters; 40 cabinet drafts; 60,000 text and 200 title
characters per draft; 256 KiB total canonical UTF-8 writing. Duplicate IDs,
extra fields, invalid modes, overflow and corrupt rows are refused without
truncating or overwriting the stored copy. SQLite non-text payloads and invalid
metadata are treated as integrity failures. A local digest is an integrity
check, not publisher authentication or evidence acceptance.

If a competing session has kept a newer copy, local writing remains in place.
Inspect stored copy reads its words without changing the current buffer or the
retained revision. Replace inspected return copy requires an explicit No-default
confirmation, then compares the exact inspected revision. Another intervening
change still blocks replacement. It never silently rebases a stale update.

## Desktop lifecycle

The controller restores the stored note and cabinet drafts into the existing
bridge draft map when the shell is installed. Returning to a cabinet record uses
that same map. No idea/project is created by restoration. ReturnTab can be
reopened through the existing deferred-tab mechanism after the controller is
installed; it does not override existing startup policy or recreate every old
workspace automatically.

Explicit Keep validates writing, writes dirty code buffers through the existing
RecoveryStore, then performs the guarded shared keep. Ordinary window close
runs existing concern/PDF and code-save decisions, then captures return writing
before shutdown steps. Return/recovery failure keeps the window open. The
explicit skip-new-copy choice bypasses only this new return-copy update, not
existing file prompts or ownership policies.

A relevant inconsistency is fixed: whole-window Discard now retains the code
buffer in RecoveryStore as tab-close Discard already did. It does not write the
source file, and final close cleanup does not remove that retained buffer.
The original model-stop, engineering shutdown, tracked command-tree handling,
execution lock, session/layout persistence and desktop lease close path remains.
Closing a client window is not a global cancellation receipt; separately hosted
work may continue, and actual owned-process Stop still uses its original control.

Coverage is explicit. Cabinet drafts and this note are kept at Keep or normal
close; changes since the last successful keep can be lost on a crash. Code
recovery retains its existing 2 MiB-per-buffer limit. Other workspace forms keep
their own save controls and are not claimed to be recovered by this slice. The
open-work list is bounded at 100 rows. This is not universal application hibernation.

## Verification

Nine focused boundary tests passed; the final run took 1.117 seconds. They cover
restart, owner/workspace/mode separation, revision conflict, no-op/clear behavior,
all-or-nothing bounds, malformed/non-text state and cloud-private rules.
Seventeen actual offscreen Qt checks passed. The runner opens two desktops in
sequence, checks a competing update through the real shared command, tests stale
and explicit replacement, cancels exit, forces a recovery-write refusal, tests
the explicit skip option and verifies a fresh desktop's restored writing and
recovery offer. Replacement confirmation uses a controlled Yes response. The
original recovery startup dialog's offer is observed with its modal interaction
suppressed; clicking its restore button is not new acceptance evidence.

Five actual Qt images show Thread, Compact, Leaving, Conflict and Returned. The
Leaving image is the actual dialog widget; the other four are window captures.
The UI fixture has two saved job-state records, with no running worker behind
them. No job is submitted, provider contacted, model run, engineering/native tool
invoked, Master Stop executed or OS priority changed. The full historical suite
was not rerun. Evidence is under `docs/RETURN_01`.

Registry: 688 operations; the 686 earlier operation schemas/scopes and all 112
job-tool targets are unchanged. Settings remain 26, Explore workspace adapters
15 and authored method profiles 12. Explore now projects 827 combined entries.
Discovery's protocol-bound files and all historical evidence remain unchanged.

## Remaining work

HATCH remains 0/6 formally accepted; integrated remains 4/6 in retained evidence.
I05 exact-model/native and I06 owner-host gates remain OPEN. Offscreen tests do
not qualify ThinkPad installation, native handoff, pointer dragging, live
scheduling, real model reasoning or owned-process Stop.

The connected interface is ready for a cohesive owner review. Next bounded
development: make Slate's saved directions and memory navigable alongside the
cabinet/settings hierarchy, with provenance and deliberate edit controls.
Complete settings/memory adapters, final menu choices and real-host qualification
remain; no completed cloud slice substitutes for those acceptance gates.
