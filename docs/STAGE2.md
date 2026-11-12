# Stage Two: connect the work

This candidate adds Project Desk to View and the left Projects section. It joins an original idea, a project's intent, assignments, source revisions, frozen plans, and owner reviews in the existing Kernel database. It needs neither a local model nor a network connection. The interface keeps the current paper and graphite appearance. The actual ThinkPad display walkthrough is still required.

## Walk through it

1. Open **View → Project Desk**. In Ideas, keep an idea in your exact words, select it, and choose **Give selected idea a new project**. The original wording becomes the project's intent. Suggestions can be labelled as Slate's; that label describes their stated origin and is not an identity attestation.
2. Select the project. In Assignments, write the original request, interpretation, intended output, success conditions, and when to stop. Add input addresses such as `files:stock.csv`, one per line. Save. The original request is now read-only; later interpretations create new revisions.
3. Enter an everyday query such as `@files:stock.csv | rows | add Short = Need - Have | where Short over 0`. Freeze the plan. The screen requests the parsed read operations, a 24-hour expiry, and the displayed time/step limits. The remaining recorded defaults are zero model tokens, 1024 MiB memory, 1 MiB output and ten files. Network and working-root grants are empty. These are proposed limits; no execution loop exists in this stage.
4. Perform the actual work through the existing Ledger controls. The Stage Two plan button only parses and reads sources to preserve their revisions. It never calls `language.run`, `stac.run`, a job submitter, a shell, or an approval grant.
5. Enter output addresses, a review note and remaining questions. Keep the review. Accept requires current inputs, a current unexpired plan, at least one output, and resolved plan questions and symbolic source gaps. Changes needed and Defer can retain unresolved questions. A review is the owner's judgment; it does not manufacture test evidence or execution permission.
6. Close and reopen Ledger. Select the same assignment. **Inspect saved record and history** shows every interpretation, the native typed plan, exact scope request, budgets, source snapshots, output snapshots, review, and journal. Reopening never resumes execution. If an input changed or vanished, its old revision remains and the current state says it needs review. To refresh it deliberately, save the assignment again with the desired input addresses, then freeze a new plan.

Project notes hold source, question, decision, alternative, task, working-copy and output links. For example, link `copies:ID`, `job:ID`, `evidence:ID`, `assignment:ID` or `review:ID`. Addresses use existing registered readers and the same caller's permissions. Links preserve the observed revision and actor; they do not transfer ownership or upgrade a statement into evidence. The old attached engineering project is a separate source attachment and remains visible under Projects.

## Shared protocol and data

There are eighteen new operations. All eighteen pass through the existing Kernel, CLI and MCP registry and schema validator:

| Family | Operations | Scope |
| --- | --- | --- |
| Projects | `projects.create`, `projects.link`; `projects.list`, `projects.get` | execute to save; read to inspect |
| Ideas | `ideas.capture`, `ideas.promote`; `ideas.list`, `ideas.get` | execute to save; read to inspect |
| Assignments | `assignments.create`, `assignments.revise`, `assignments.plan`; `assignments.list`, `assignments.get`, `assignments.reopen` | execute to save; read to inspect |
| Plans | `plans.get` | read |
| Reviews | `assignments.review`; `reviews.get` | approve to record review; read to inspect |
| Byte-bound files | `desk.sources.read` | read |

New addresses are `project:ID`, `idea:ID`, `assignment:ID`, `plan:ID`, and `review:ID`. Every Desk record is private to its principal identity, including readers with approve scope; lists filter by that identity before pagination. UI uses the existing `desktop-owner` identity. CLI users must choose the same identity to inspect those UI records. This local principal separation is not encryption against the operating-system account that owns the database.

Records live in `.ledger/engineering.sqlite3` in component tables `desk_records`, `desk_history`, `desk_events`, and `desk_migrations`. Migration 1 is transactional, adds only these tables/indexes, records a migration checksum, and rejects gaps, changed checksums and unsupported future versions. It does not rewrite older tables or reinterpret legacy evidence. Historical revisions are append-only through the service; hashes detect accidental damage, not hostile replacement of the database. Optimistic revision checks reject stale editors and atomically save a new plan/review with its assignment update. Stage One complete backups include these tables through the existing SQLite snapshot mechanism.

The `arc.project-desk.plan/1` envelope contains project and assignment identity/revision, original request, interpretation, output goal, questions, success/stop conditions, input snapshots/revision hashes, native language IR, registered operation schemas and effects, caller, requested tools/effects/roots/network/expiry, six budget dimensions, source-foundation identity, result type and content digest. QUERY retains `arc.stacy-action-plan/1`; engineering STAC retains its existing typed IR and result type; CALL records a schema-checked registered operation. The languages remain distinct. Engineering IR whose runtime generation is symbolic reports that gap explicitly. CALL can describe a future write within the caller's existing scope, but no CALL executor is added here.

Files inputs and outputs use a SHA-256 identity over their full bytes and normalized address, so equal-size edits with a restored modification time are detected. Up to 128 KiB of each file is retained as exact base64 bytes; larger files retain a full-content hash plus the reader's projection and an explicit availability gap. Keep a complete backup of those source revisions. A snapshot is limited to 512 KiB, combined plan bindings to 2 MiB and 32 entries, and file hashing to 128 MiB per file. Folder addresses are navigation: choose individual files for frozen byte inputs. Other record addresses freeze the exact registered-reader projection; a reader with changing timestamps can legitimately require fresh review. Mutable source reads are observations, not one atomic filesystem-wide snapshot.

The UI shows up to 100 recent records. The read APIs support `limit` and `offset` pagination. Existing Jot notes and Catalog navigation projects stay in their original store. No silent conversion or bulk migration is performed; ideas entered in Project Desk are new durable records. The existing Agenda, investigations, working-copy reviews and engineering tools keep their own execution/evidence rules.

## CLI and checks

Use the existing CLI with a persistent principal, for example:

```sh
python3 -m workbench.engineering_cli --root ~/Concern/Office --identity desktop-owner --operator call projects.list
python3 -m workbench.engineering_cli --root ~/Concern/Office --identity desktop-owner --operator call assignments.list
```

For mutations, prepare a JSON object and use `call OPERATION --params-file file.json`. MCP exposes the same schemas; no second implementation or private transport is introduced. Saving records requires execute scope, and recording an owner review requires approve scope. Read-only clients cannot save plans. The original 485 operation names, scopes and schemas are frozen in `docs/STAGE1_CAPABILITIES.json` and still checked individually against the original schema digest. New operations deliberately extend that inventory; `docs/STAGE2_CAPABILITIES.json` is the current full inventory. SDK, policy, runtime archives and dependency pins remain unchanged.

```sh
python3 tools/check_release.py --self-test
python3 -m unittest discover -s tests_stage_one -v
python3 -m unittest discover -s tests_stage_two -v
python3 -m workbench.project_desk_checks
python3 -m workbench.project_desk_checks --ui
```

The standalone walkthrough uses a disposable workspace: idea → project → assignment → frozen query → a separately invoked read → output → review → a new Python process → complete backup/restore → another new process. The UI check opens the real Qt window and exercises Project Desk widgets. It needs the pinned PySide6 installation; a missing dependency is reported as a failure, never a pass. This candidate's actual measurements and outstanding host checks are in `STAGE2_RESULT.json`.

Stage Three will address local-model/source retrieval work. Bounded execution, restart of running work, richer artifact editing, and appliance/hardware qualification belong to later approved stages. They are not represented by a frozen plan or an accepted review in this candidate.
