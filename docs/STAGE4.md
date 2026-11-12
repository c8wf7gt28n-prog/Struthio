# Stage Four: import, change, review and recover

Open **View → Changes**, or choose **Review project changes** in Project Desk. This stage adds reviewed import profiles, frozen multi-file proposals, typed CSV/TSV and conservative XLSX cell edits, bounded local-model text drafts, separate original publishing, and journaled recovery/undo. Every operation uses the shared Kernel, CLI and MCP. It does not start a model at launch or grant unattended file application.

## Walk through a project

1. In Changes → Import, choose a project folder or ZIP inside your home folder. Select Mixed, Notes, Code, Tables or Engineering. Preview the exact inclusion/exclusion list before accepting it. Duplicated bytes are labelled and retained at each path. Reviewed code configuration includes .gitignore, .gitattributes, .editorconfig, .clang-format and .clang-tidy; common dependency lockfiles are retained. Credentials, private keys, unreviewed hidden content, caches, build products, model weights and history are excluded by default. Links/special files are never followed. Unsafe archive paths and duplicate/case-colliding members are refused.
2. Accept the preview. Ledger streams selected bytes into protected objects and creates an ordinary folder under Files → Working copies. Originals stay in place. Empty admitted directories are retained. Any included source change between preview and capture requires a new preview. The included limits and profile remain with the copy.
3. Select the copy in Changes. Open a text file in Draft, edit it and stage the text. Add, remove and rename files through the adjacent controls. For a supported table, choose Cell change and identify a sheet/cell, its typed old value and the desired new value. Staging does not write the file. Freeze the staged operations as one proposal.
4. Review every target, before/after hash, text difference, cell change, parser check and adapter limit together. A rename is labelled and implemented as retained-byte create/delete operations. Long displayed diffs explicitly say they are shortened; Read frozen bytes pages through the complete protected revision. Applying uses those exact frozen objects, not the current draft editor.
5. **Apply to working copy** changes only that copy, after rechecking all target bytes and permissions. **Preview original update** separately freezes the current working revision against the admitted original baseline. **Update originals** is a distinct owner action. ZIP originals are not rewritten: export the working folder as a new result instead.
6. Read the batch journal. After interruption, Inspect recovery reports which file operations are observed as applied, pending or conflicting. Resume verifies the batch before completing pending operations. Undo or roll back restores retained earlier bytes only when it will not overwrite a later outside edit. Close other applications writing the project during these operations.

## Local model drafts

With a local model already selected in Brain, describe a text change and select up to eight existing text paths. The model sees exact UTF-8 bases and may propose only character-range patches to those paths. Total selected text is limited to 16000 characters. The actual tokenizer checks the prompt/output reserve; exact bases are not silently clipped. A complete, normally terminated stream, correct target/base identities, nonoverlapping exact ranges, unchanged sources and the same model are required before one change set is frozen. No file is applied by the model job.

The single-file exact-edit result from Project Desk can also enter this workflow through `changes.from_slate`; only a complete validated reply targeting this particular working copy is accepted. AI provenance, model/job identity, input revisions and available metrics remain beside the proposal. The small Stage Three task trials do not establish multi-file editing quality. Real GGUF quality/performance still requires owner-host measurement.

## Formats and preservation limits

Text changes support UTF-8, explicit full-text replacements and exact character-range patches. The draft editor opens text up to 1 MiB; the complete encoded proposal request is also bounded at 1 MiB by the service. Exact patches can target text up to 4 MiB with up to 200 nonoverlapping ranges, while model drafts retain their smaller context/range limits. BOMs are retained on full-text replacement. The UI retains uniform CRLF endings. Python and JSON results receive named parse checks without executing source. No test/build success is inferred from parsing.

CSV/TSV edits target existing A1-style cells. Existing values are text; new numeric/boolean/empty values are serialized as strings. Cell strings, BOM and newline style are preserved, while quoting is reserialized. Formulas are not evaluated or introduced through the CSV cell adapter.

The XLSX adapter supports a deliberately narrow simple-workbook profile: local ordinary formulas/cells, no macros, external relationships, named ranges, merged cells, shared/array formulas, calc chains, signatures or embedded objects. Unsupported workbooks remain importable as untouched opaque bytes and need a native application for editing. Cell style attributes are retained; replacing rich text produces plain text in that changed cell. Unmodified package parts retain their exact bytes. Rewritten worksheet/workbook XML is semantically serialized. Formula caches are cleared and recalculation is requested; no calculated values are invented. New formulas are restricted to local arithmetic and the documented small function set in cell_edits.py. Tables and XLSX packages are bounded at 16 MiB input; XLSX expansion is limited to 64 MiB, 2000 parts and 8 MiB per XML part. This is not an Excel compatibility or calculation qualification.

Use **Changes → Export ZIP** for profiled projects. This preserves admitted configuration files and empty directories, captures exact revisions and writes a separate export receipt/metadata member. The generic Files export retains its older hidden-file policy and is not a substitute for the project profile export. Generated assignment reports and source-revision tables enter the same proposal/review workflow with their source and generation provenance.

## Durability and boundaries

The existing copies table remains the source/work address registry, and the existing protected copies object store retains bytes. Versioned edit tables extend that authority with import previews, profile metadata, proposals, commit state and an append-only event journal. Profiled copies route updates/recovery through Changes; the older working-copy workflow remains for legacy copies. A correction removes metadata-only folder identity reuse for legacy copies as well: all relevant bytes are rehashed.

Linux descriptor-relative operations reject linked parents. Cooperative per-copy locks prevent concurrent Ledger batches. Intent is committed before each filesystem mutation. Replacements use Linux rename exchange, creates use no-replace publication and deletes move to retained private temporaries. Displaced bytes remain until verified and acknowledged. CAS objects, files and containing directories are flushed at the relevant boundaries. This is atomic per file and recoverable across files, not one globally atomic transaction.

Master Stop is checked at file boundaries during import, application, recovery and export. A stopped partial application remains journaled and requires explicit work resumption and recovery. Large desktop operations use a background service worker; a persistent transport failure has an unknown outcome and is inspected through the journal rather than automatically retried. Bulk Changes/import calls have a 600-second client timeout, without increasing the existing host message-size limits. Preview/proposal/journal records are private to their principal; the normal working files retain the Ledger's existing Files access policy.

An uncooperative external writer can still race an update: Ledger cannot lock another application's writes. Unexpected displaced bytes are retained and the batch stops for manual inspection rather than guessing. Such conflicts can require a native-file recovery or a fresh working copy. A power loss, hostile kernel/native worker or two-machine deployment has not been qualified here. No undo automatically overwrites an unknown later revision. New empty parent directories may remain after undo; nonempty directories and excluded original files are never removed as cleanup.

Default imports allow 2000 files, 512 MiB total and 64 MiB per file; reviewed API limits can increase to 5000 files, 2 GiB total and 256 MiB per file. Traversal/ZIP metadata is bounded at 20000 entries and expansion at 200:1 above a 1 MiB allowance. Credential detection combines path policy and bounded streaming patterns; it is not a promise to recognize every possible secret. A proposal supports up to 100 semantic operations/200 file changes. Context and UI tests remain separate from real-model and owner-display acceptance.

`changes.report` creates a reviewable Markdown assignment report or CSV source-revision table as a CREATE proposal, preserving source assignment revision and generation provenance. It does not turn a model statement into engineering proof. Broader native authoring remains an application handoff.

## Shared operations

The 21 new operations extend the registry from 514 to 535. All 514 earlier operation schemas remain unchanged; the new tables use an additive versioned migration. Dependency pins and the 78 protected SDK, policy and runtime files remain unchanged.

| Purpose | Operations |
| --- | --- |
| Reviewed imports | `imports.preview`, `imports.get`, `imports.accept` |
| Copies and exact input | `changes.workspaces`, `changes.workspace`, `changes.file`, `changes.cell` |
| Freeze proposals | `changes.propose`, `changes.from_slate`, `changes.original.preview`, `changes.report` |
| Local model draft | `changes.ask` |
| Frozen review | `changes.review`, `changes.content` |
| Apply and original publication | `changes.apply`, `changes.publish` |
| Journal and recovery | `changes.commits`, `changes.commit`, `changes.recover`, `changes.undo` |
| Profile-aware export | `changes.export` |

## Shipped checks

```sh
python3 tools/check_release.py --self-test --runtime
python3 -m unittest discover -s tests_stage_four -v
python3 -m workbench.edit_checks
python3 -m workbench.edit_checks --ui
```

The disposable walkthrough imports configuration and notes, edits text and cells, renames/adds files, updates a copy, then deliberately exits a child process after an actual original-file rename. Another process observes the durable intent, resumes, and undoes the original update. A complete backup/restore then reopens the same frozen proposal and working bytes. Protocol fixtures do not measure real model intelligence. `STAGE4_RESULT.json` records actual scope and pending acceptance.

Independent readback with openpyxl 3.1.5 confirmed a simple edited XLSX value, a preserved ordinary formula and an untouched cell; the stale formula cache was absent. openpyxl is a verification tool on this execution host, not a new application dependency. Native Excel/LibreOffice round trips, the real Qt/Fluxbox walkthrough, real GGUF edit quality and power-loss behavior remain unqualified.

Format and filesystem references: [Microsoft SpreadsheetML cells](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-cells), [SpreadsheetML formulas](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-formulas), and [Linux rename flags](https://man7.org/linux/man-pages/man2/rename.2.html).
