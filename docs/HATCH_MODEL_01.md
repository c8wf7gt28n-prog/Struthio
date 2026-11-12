# HATCH MODEL-01

November 3, 2026 · America/Phoenix

Complete checkpoint over NAVIGATION-01. Three actual local-model launch defaults now appear under Settings → Slate → Local model: context tokens, CPU threads and memory cap. Saved defaults, pending requests, recorded selection and running-worker readback remain distinct. The original model registration, qualification, activation, restore, cancellation and reply-protection routes remain authoritative.

## Real defaults and explicit loading

The defaults are context 2048 tokens, four CPU threads and Auto memory (zero). Context accepts 512–8192; threads 1–32; memory is zero or 512–262144 MiB. These fields persist in the existing Kernel settings table as ledger.brain.context, ledger.brain.threads and ledger.brain.memory_mb, with the ordinary shared settings journal. They are genuine new launch preferences, not duplicate copies of brain.selection or brain.worker.

Apply, Default and Undo update a future launch preference. They do not rewrite the recorded model configuration, replace the worker, start inference or enable Slate. The existing expected-value/revision checks and atomic value/history commit remain. A manual memory value between zero and 512 is refused without losing the draft.

New default-only requests use the existing Brain panel's 2048/four/Auto defaults across all model submission routes. This unifies the former API thread fallback with the panel's explicit four-thread default. Explicit per-request options still override defaults. Earlier queued requests retain their original behavior.

The Settings panel offers Reload saved defaults, Restore previous model and Open model controls. Reload resolves the shown Auto preference and passes explicit options to the original Brain launch/watch route. An intervening displayed-state change requires review. Restore uses the original brain.restore operation and its recorded prior configuration. Model identity and registration remain stateful actions in the original model chooser rather than a fabricated scalar setting.

## Frozen requests and retries

At the existing Kernel queue commit, new activation and qualification requests receive a brain_launch snapshot. It merges saved defaults with explicit request options and applies the original configuration validator. Auto memory is resolved against measured RAM at submission. The existing architecture, template, declared-context and memory checks still apply.

The snapshot records concrete context, threads, memory cap and model identity. Running the job uses those values and rechecks the original configuration constraints. Editing defaults after submission does not change a waiting request. If available RAM later becomes insufficient, validation refuses the request rather than silently increasing its budget.

The original request_spec is unchanged, including the existing idempotency comparisons. A retry of the same request key returns the original job and frozen options even after defaults change. Direct jobs.submit, brain.model.use, brain.model.qualify and brain.restore share this behavior. Restore's explicit prior configuration takes precedence over current defaults.

Jobs queued before this pass have no snapshot. They keep their original request options and original configuration behavior. A malformed new snapshot or changed model identity is refused. No public operation schema accepts arbitrary internal snapshot fields.

## Current values and recovery

Settings reads the stored defaults, a bounded caller-owned request view, the last recorded selection and the existing worker receipt. Running values require both the calling owner's worker receipt and its matching process-start identity; they are not inferred from a stored selection or a queued job. An unknown, stopped, other-owner, mismatched or incomplete worker configuration supplies no effective value.

The view returns only model IDs, job IDs, numeric options and bounded state metadata. Worker credentials, key-file paths, ports and raw error bodies are withheld. Optional activity sharing omits the new model rows and definitions. Default cloud proposals refuse their explicit effective/history/write routes through the existing privacy checker. Reads remain caller-scoped and changes retain direct owner approval; Tutor mode cannot change them.

The original failed-handover path remains: a failed candidate can reload the previous live worker; owner cancellation leaves it stopped; an active reply prevents the handover from stopping that worker. A successful original restore probe adds its request ID to the existing worker receipt. The Settings view reports RESTORED_PREVIOUS only from that receipt while the owned worker is still observed. A failed restore does not claim running values. These are process/configuration receipts, not answer-quality or engineering qualification.

## The original model panel

The existing model controls read saved defaults into fields that have no local override. A local edit stays visible when a saved default changes elsewhere. Use saved launch defaults deliberately clears those overrides; Edit launch defaults in Settings returns to the canonical key. A local Auto override is resolved to concrete options before submission, including when the saved cap is manual.

The affected numeric passages use flat yellow writing surfaces, with no spinner buttons; the model chooser uses the paper action palette. The shared Settings editor retains its Room policy and source Preview. Its model status refresh updates request/worker information while preserving an edited default and its original revision. Settings drafts and local model-panel overrides remain desktop-local.

Model submission messages now say Requested model change/inspection/qualification or Requested previous model. Model-job labels describe activation/inspection/qualification with their actual event state; accepting a queued request no longer says that the model has already switched.

## Verification

Evidence in docs/MODEL_01 includes:

- 41 focused tests passed in 4.763 seconds: 13 new model/control boundary cases and 28 related settings regressions. Cases include atomic history, owner/Tutor/privacy, invalid values, frozen Auto/defaults, explicit overrides, direct jobs.submit, qualification, restore, idempotent retries, legacy jobs, corrupt optional data and saved/requested/worker separation.
- Controlled worker stand-ins exercise successful activation from frozen options, failed-candidate restoration, failed restore, cancellation and the running-reply guard. No real GGUF, native model process or model generation is used by these cases.
- 11 final actual Qt checks passed, with five screenshots including 1366 × 768. They exercise Apply/Undo/refusal, stale default revision, reload through the original panel, local overrides, retained source writing and compact controls.
- The final UI run holds every Kernel launcher. It submits one actual queued fixture request, observes its frozen fields, then cancels it. Zero worker processes, model generations, provider requests and native invocations occur in that final run.
- All 690 operation schemas/scopes, all 112 job-tool targets and all prior 31 setting definitions are unchanged. There are now 34 genuine connected settings. The registry digest remains 9b28255cf4cd31117ece3edada8a737b569e9de996cbb32836e3b1040f92e1a1.
- AST comparison verifies that the original Kernel is unchanged except for the atomic launch snapshot/validation relocation, and the model worker is unchanged except for its frozen-option reader and restoration receipt. The behavioral checks supplement that structural comparison.
- No full historical suite was rerun. Native execution, actual-model response quality, live scheduling and owner-host acceptance remain separate.

Complete packaging retains all earlier source, modes and evidence, including the prior 15-view UI review captures. It refreshes the existing source bindings and release manifest. Archive checksum and post-package preservation checks are recorded in the separate progress discussion.

## Next

This lands the model-settings portion of the four estimated remaining development passes. Next is the audit and connection of remaining presentation, favorites and view preferences, followed by final Hatch/desktop integration and a focused integration/debug pass. The numbered 15-view review remains available for owner wording/spacing choices.

HATCH acceptance stays 0/6; historical integrated acceptance stays 4/6. I05 exact-model/native and I06 owner-host remain OPEN while the ThinkPad is unavailable. This pass does not close those gates through metadata or simulated worker checks.
