# Integrated campaign I01: one problem and a real source read

This candidate adds the first of six integrated math and software-use passes to the full Stage Six application. It targets the existing single-user Linux desktop workflow. The Stage Six features and historical records remain in the package.

## Try it

1. Extract into a new program folder and retain the previous program/workspace. Follow GETTING_STARTED.md for the Debian installer and launch command.
2. Open **Project Desk → Problem sheet → Start Clock Lab**. Choose a location in your home folder. Ledger creates a new `Clock_Lab_I01` folder there, imports a separate working copy through the existing ENGINEERING profile, delegates that copy to Slate, and opens its saved question. An existing example folder is never overwritten.
3. Read the **Question** page. Allocation lifetimes are UNKNOWN and have no numeric value. Goals, assumptions, questions, candidate approaches and typed placeholders are editable. The original request stays fixed. Saving creates a new revision.
4. On **Sources and results**, select Requirements and click **Read selected source and keep result**. The registered `work.read` operation reads the working copy. The saved receipt contains the returned text, exact byte count, source SHA-256, output digest, action contract and problem revision.
5. Close and reopen Ledger. Choose the saved problem. The original request, revisions, unknown variables and actual results remain. Reopening checks source freshness and never resumes an action automatically.
6. Edit a source in the working copy, then reopen the sheet. The saved observation remains visible and freshness requires review. A prepared action bound to the previous bytes is refused. Explicitly save the source selection in a new problem revision to investigate the changed input. Earlier evidence retains its earlier revision.

Any delegated profiled working copy can supply a relative UTF-8 text path on the Sources page. This first profile admits eight selected sources, up to the existing reader's 64 KiB per file. The full existing viewers and file operations retain their prior format support; this action profile does not expand the text reader to binary formats.

## What is connected

| Concern | Existing interface reused | I01 addition |
| --- | --- | --- |
| Ideas, projects and assignments | `project_desk` owner-scoped SQLite records, CAS revisions, history and events | `problem`, `problem_action` and `problem_result` record kinds in the same store; no new database migration |
| Selected source copies | ENGINEERING import, `copies` table, `edit_storage.workspace`, `work.read` | Copy/path/SHA-256/byte bindings, with delegation checked again before a read |
| Tool discovery | Capability catalogue, CLI schemas, declared handler map | Six relevant source-investigation operations, input/output descriptions and separate declared/installed/available/permitted/qualified dimensions |
| Actions and observations | Kernel schema validation, principal, audit and existing source reader | Problem revision/context digest, frozen operation schema and handler digest, exact returned snapshot, idempotent saved-result replay |
| Workspace UI | Project Desk and existing visual controls | Problem sheet with Question, Sources and results, and Tools pages |
| Model authority | Existing read-only PLAN proposal profile | Preserved unchanged. I01 source reads are explicit coordinator actions. The new model action profile belongs to I04. |
| Copy edits and originals | Existing Changes / Continuing work / publication checks | Preserved. I01 grants no new original-publication authority. |
| Launch and backup | Existing Debian installer, launchers, backup/restore | Preserved, with I01 verification added to the release-check entry point |

The complete baseline registry and schema fingerprint are pinned in `I01_BASELINE.json`. `I01_BASELINE_FILES.json` records every file from the supplied archive. `I01_DELTA.json` lists every intentional changed file and added file, and refuses deleted baseline files. Existing native tools and optional model routes remain registered. Presence, scope eligibility and one successful read do not qualify an engine.

## Problem and action contract

`problems.create` stores the exact request, goals, assumptions, typed variable placeholders, open questions, candidates, source bindings and optional project/assignment link. An assignment-linked question must retain that assignment's original request. Variables marked UNKNOWN cannot carry a value, including zero. These placeholders describe inputs; they do not yet implement dimensional arithmetic.

`problems.revise` requires both the current revision and context digest, keeps the original request, and appends history. Supplying sources explicitly binds their current working-copy bytes. Source content is treated as data and never conveys permission.

`problems.prepare` creates an action bound to the current problem and a selected source. It does not run the read. `problems.run` admits only the registered `work.read` contract with read effects. It rechecks owner, current problem revision, context digest, operation schema/handler digest, delegation, selected path, source size and source content digest. Kernel dispatch checks the caller's actual scope and the source reader's ordinary owner/path constraints. The actual result is frozen only after successful validation. A repeated run of a completed action returns its saved result without another read.

`problems.get`, `problems.list`, `problems.history` and `problems.tools` expose saved state to the same owner. `problems.get` returns current source freshness separately from historical observations. Read-only principals may inspect their records but cannot create/revise/prepare/run them. No arbitrary command, write effect, shell, scheduler, network grant or model self-authorization can be supplied through this profile.

## Frozen exercise

`examples/clock_lab/INPUTS.json` pins requirements in Markdown and one-page PDF, CSV memory/power/parts tables, an input-only XLSX, a native KiCad outline and an unexecuted Python stub. All data are invented. The workbook's lifetime values are blank with explicit UNKNOWN state. No native application has been inferred to work from the existence of those files.

The independent oracle is in `tests_integrated/clock_lab_oracle.json`, outside `examples/clock_lab/inputs`. The example copier uses a fixed manifest and excludes the evaluator. Tests independently check integer-byte and Decimal power calculations and a separately stated half-open lifetime variant. The initial task still lacks lifetimes and cannot acquire a feasibility verdict by assumption. Keeping the oracle out of the exercise is a fixture separation, not an adversarial security boundary against arbitrary repository reads.

## Verification

Run `python3 tools/check_release.py --self-test` with the installed runtime Python. It includes the existing six-stage checks and the I01 real-read/fresh-process check. `python3 -m unittest discover -s tests_integrated -v` adds seven focused tests for changed contracts, immutable unknowns, explicit source rebinding, retained evidence when sources disappear, delegation/path checks and the independent oracle.

`python3 -m workbench.problem_checks --ui` exercises the real Qt problem widgets offscreen when PySide6 is installed. Exit 2 with UNAVAILABLE means this host lacks that dependency; it is not a UI pass. The owner's display walkthrough and Debian ThinkPad qualification remain explicit acceptance work. `I01_RESULT.json` reports what actually ran on this execution host.

## Remaining integrated passes

I02 adds quantities, dimensional checks, bounded symbolic/constraint tools, actual Calc/Writer work and graphing calculations. I03 adds protected Python experiments, generic selected-board native checks, and finite evidence/reason graphs. I04 connects an adaptive model action/result/revision loop with scoped flexible grants. I05 adds reusable methods, transfer, linked artifacts and visible graphing/Calc sessions with takeover/resume. I06 performs real-model, unseen-task and target-host qualification and packaging.

The TI-style calculator should share the same units/expression/solver results as the reasoning tools. It is included in I02/I05/I06 rather than becoming a seventh campaign pass. I01 establishes durable context and observed software output; increased model reasoning has not yet been measured.
