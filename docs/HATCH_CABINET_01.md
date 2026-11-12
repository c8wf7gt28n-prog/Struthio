# HATCH CABINET-01 · poem

November 2, 2026. Full checkpoint over SETTINGS-02. The requested empty-field invitation is exactly `poem`.

## Writing invitation

The desktop's existing text-entry hints now use one `text_prompts.writing_prompt` helper: 114 existing Qt call sites in 57 source files, plus the new cabinet writing box. Search, conversation, command, title, notes and technical text-entry fields use the same invitation. Each field retains its semantic label; its former example remains in a tooltip and accessibility description. Changing context or switching among Slate, staC, Kernel, Find and Shell keeps the invitation. It never inserts a value, sends a message, changes validation, or changes a stored record. Read-only output hints retain their original status text.

Seven dynamic mobile companion entry hints and the pairing-code and generated records-browser HTML hints use `poem` too. The mobile shell cache has a new version so the next service-worker update can install the new interface. This verifies source behavior; live iPhone/owner-host acceptance remains open. Typebar status messages have their own visible console label so save/error feedback remains available while the typing placeholder stays `poem`.

## Logical cabinet

`workbench/cabinet.py` projects the existing Concern catalogue, Project Desk, working-copy and investigation stores into stable typed nodes. `ledger.cabinet` and `ledger.cabinet.get` are bounded read operations, owner scoped where the provider has owner identities. The existing Concern catalogue remains scoped to its connected profile. A declared filing relation is not a grant of access.

The new tree distinguishes the record's canonical identity from a display placement. Existing catalogue containment/maintaining relations select a deterministic primary placement, with additional declared placements shown as references. Project Desk projects contain views of their ideas, assignments and saved inquiries. Records with no declared project membership have an explicit Unassigned view. Working copies and older investigations have no project-membership field, so the tree does not guess a project from a path or from another project's reference. Records whose project lies outside a bounded snapshot appear as Other project work rather than being falsely reclassified as unassigned.

A second project's reference keeps its frozen source binding and resolves the same original target. It does not copy the record, change its owner or declared project, or move/overwrite a master. The tree reads stored metadata only: it does not refresh source hashes, declare an inquiry current, launch jobs, or run a solver. Opening a record permits explicit read actions such as checking inquiry bindings or rechecking a copy. Cycles, integrity failures, unsupported catalogues and projection limits are reported without migrating or repairing the underlying store.

The central Cabinet record room preserves an edited Preview. It reads original records and can save a new idea or create a project through the existing commands. Drafts are retained per node while this desktop remains open; Keep is required for durable writing. Selection, expanded branches, scroll and the existing-view switch are saved in validated Session presentation state. Filtering temporarily reveals matching branches, then restores the prior expansion state. The real `cabinet.sort` setting chooses natural or alphabetical sibling order without changing identity.

Existing views retains the previous catalogue, alternate views, tools, and workspace routes. Import and Export are separate fixed actions opening the existing receiving and outgoing-file controls. They do not perform a transfer automatically. Trash remains fixed outside the scrolling tree. Hidden legacy-library polling skips file walks and copy freshness checks while the logical cabinet is active.

## Verification

Evidence is under `docs/CABINET_01`: 42 focused backend checks (14 cabinet and 28 settings), 18 actual Qt offscreen checks, registry compatibility, prompt inventory, and three populated desktop captures. The UI run exercises two projects, unassigned work, a real source and working copy, a stale inquiry, a saved catalogue note with two placements, and an older investigation. It verifies draft and edited-Preview preservation, actual Keep behavior, original master bytes/mode, sort changes through Settings, search expansion restoration, old navigation rebuilds, the five typing targets, status feedback, Import/Export destinations, 1366 by 768 layout and clean Session/lease close. No job, model generation, provider request or engineering solver is run. JavaScript syntax and the mobile prompt helper's preservation of typed content and accessible labels were checked locally.

All 681 existing operation schemas and scopes and all 112 job tools remain unchanged. The two cabinet read operations bring the registry to 683; the real settings count is 26. Discovery's five protocol-bound service sources are unchanged. The full historical test suite was not rerun. Offscreen Qt and source checks do not qualify native handoff, a live model, or the owner's ThinkPad/iPhone.

## Remaining campaign work

The next coherent UI slice is the expanded capability launcher, menu organization/names, contextual command ranking and right-column monitors/queue. The current record room is an initial adapter; editing existing assignments and inquiries retains their existing workspaces. Object Glass can retain its prior file context while the cabinet selection is separately exposed to the desktop context reader; integrating that selection into the right-column presentation remains part of that UI work. Final wording, switch presentation and overall layout remain deferred owner-review choices.

The complete settings/memory adapter requirement remains open. HATCH acceptance is unchanged at 0/6; integrated acceptance remains 4/6. Real-model/native I05 and owner-host I06 remain open. The next step is to complete those UI pieces, then present the interface for a cohesive review before owner-host acceptance.
