# HATCH SETTINGS-03

November 3, 2026 · America/Phoenix

Full checkpoint over MEMORY-01. Five existing owner-memory preferences are now connected to the shared Settings hierarchy under Slate → Memory. Their values come from the original owner-scoped stacy_memory profile. There is no second configuration store and no new operation, job tool, worker, workspace adapter or Hatch menu item.

## Values and effect

The five controls are Use personality reference, Soft feedback half-life (days), Owner correction weight, Owner statement weight and Confirmed choice weight. Settings now contains 31 real connected preferences; the preceding 26 definitions retain their IDs, defaults, types, bounds and backing stores. See SETTINGS_INVENTORY_03.md for the current inventory and remaining work.

A missing profile is unavailable in Settings; it is not replaced with an enabled default. Import, delete, archive, task and feedback actions retain the original Memory controls. An unavailable or corrupt optional profile leaves the other settings available and does not replace profile bytes.

The enable default is true because the existing import operation creates enabled profiles. It is only a default for an imported profile, not a claim that a missing profile exists. Numeric defaults are the original half-life of 90 days and feedback weights 4, 2 and 0.5. Persistent owner corrections do not decay; the half-life applies to soft feedback accounting.

Readback distinguishes the saved value from the profile-context effect. Numeric parameters remain stored when the profile is off, while their effective value is unavailable. Enabling the profile does not load a model, grant permission for AI activity, alter model weights or prove that a response follows a preference. The existing local profile-context path consumes these parameters on its next eligible use.

## One guarded transaction

The adapter reads and validates the existing profile, including its stored digest, imported reference and parameter bounds. The profile token binds the calling owner and the complete inspected profile. Legacy configure/enable operations, an away-and-back edit and a delete/re-import invalidate that token even if the displayed scalar returns to the same value.

Apply requires the inspected revision. Within one BEGIN IMMEDIATE transaction, it changes only the requested field through the original profile commit logic and writes the existing shared settings journal. Other parameters and the original imported reference remain intact. A refused journal write rolls back the profile update as well. No duplicate ledger.memory.* setting values or separate file-delivery journal are introduced.

The original profile branch was extracted into commit_profile. An AST comparison proves that its update body is unchanged and the rest of memory_service is unchanged except for that extraction. Feedback handling, source-aware procedure reading and original memory operations retain their existing routes.

Default uses the same guarded route. Undo is an owned, journalled new change: the selected change must still be latest for the key, and the complete current profile token must match. A newer change to another profile parameter therefore also blocks blind Undo. The owner can inspect current values and submit a fresh change.

## Caller identity and sharing

Kernel Settings reads, effective readback and history now carry the actual calling principal. New memory setting history is visible only to its actor; existing shared setting history semantics are retained. Memory changes require the existing owner boundary and are refused in Tutor mode. The generic internal value helper refuses private memory keys so consumers must choose an explicit caller-scoped read.

The optional shareable ledger.context activity snapshot omits these five values and their definitions. It reports that owner memory requires an explicit local read. Default cloud action proposals refuse broad Settings/effective/history reads that could disclose owner memory, direct private key access and private operations reached through pipeline or join sources. Narrow public setting reads remain available. This is a targeted privacy boundary, not a new blanket promise about every existing record or private_local operation.

## Desktop behavior

The five leaves use the existing typed Settings tree, distinct from cabinet record ownership. Apply, Default, Detail, Reload and Undo retain their established locations. Number writing uses an exact text passage rather than a rounding spinbox: a legal 1e-20 weight is displayed unchanged, and invalid writing stays visible for correction without changing stored values. Its hint is the exact lowercase poem.

An intervening profile change preserves the current draft and reports the conflict. Explicit reload reads the current owner profile before a new Apply. Settings drafts remain desktop-local; this slice does not add restart recovery for unfinished Settings writing. Stored profile values survive a fresh desktop through the existing store.

Fixed left-panel Trash, visible Stop, monitors, return thread, the paper palette and the five-item Hatch menu remain. No provider request, model activation, tool job or native process is needed to inspect these controls.

## Evidence and remaining work

Evidence is in docs/SETTINGS_03:

- Nine new boundary cases passed in 1.807 seconds. They cover absent/corrupt profiles, original storage, stale/away-and-back changes, owned Undo, default, private identity/history/context, precision/bounds, atomic rollback and valid cloud pipeline/join privacy cases.
- Twenty-eight related Settings regressions passed in 7.214 seconds: 37 distinct focused cases in total. The full historical suite was not rerun.
- Thirteen actual offscreen Qt checks passed. These include button interactions, conflict-preserved writing, Default/Undo, profile-off readback, tiny-number display, invalid writing, privacy and a fresh 1366 × 768 desktop. Five actual window captures are included.
- Registry comparison: 690 operations and all 112 job-tool targets unchanged; all old operation schemas/scopes and all old 26 setting definitions unchanged. Registry digest remains 9b28255cf4cd31117ece3edada8a737b569e9de996cbb32836e3b1040f92e1a1.
- The UI used a disposable owner reference. Zero model calls, provider requests, job submissions and native invocations were made. Stored preference readback is not actual-model compliance.

The complete archive retains earlier source and evidence. Packaging refreshes the existing source bindings and manifest; the external release discussion records the resulting archive size, checksum and post-package checks without embedding a self-referential archive hash.

HATCH acceptance stays 0/6; historical integrated acceptance stays 4/6. I05 exact-model/native and I06 owner-host remain OPEN. ThinkPad scheduling, pointer dragging, owned Master Stop and physical/native behavior are not qualified by these cloud captures.

Next is a cohesive UI review pass across launcher choices, menus, left-tree navigation and workspace transitions, with a consolidated screenshot review set. Remaining real configuration adapters include model reload/handover preferences, favorites/view choices and other presentation fields; they are not disguised as completed scalar settings here.
