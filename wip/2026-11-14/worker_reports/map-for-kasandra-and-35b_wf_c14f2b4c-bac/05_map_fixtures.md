# Graphite headless test workspace and campaign runner: map for the After Hours 07 anchor case

I read the code only. Nothing under `/home/user/Struthio` was changed and `git status` is clean. I imported `workbench.engineering_kernel` once, with HOME and profile pointed at a scratch folder. It loaded no PySide6 module and took 0.16 s. I also ran `math_model.evaluate` on its own. It gives 12 V × 280 mA = `3.36` (exact 84/25 W) and 12 V × 300 mA = `3.6` (exact 18/5 W).

## 0. Five facts that decide the design

1. **The After Hours 07 case is not in the repo.** No seed or fixture module builds it. `project/stacy_seed/current` is Stacy's self-knowledge seed, not this case. The case exists only as an uploaded backup, `Graphite_After_Hours_07.zip`, under `/root/.claude/uploads/62270cd8-8155-590e-b29e-91307882a142/`. It is already extracted at `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/x/Graphite_After_Hours_07/After_Hours_07/Graphite_Backup` (schema `arc.workspace-backup/1`, 50 files, about 2 MB). An earlier session restored it to `scratchpad/work/demo/After_Hours_07` and `After_Hours_07-profile`.
2. **The sheets and the PDF originals live in the profile, not the workspace.**
   - `office_service.path()` is `config_dir()/'concern/catalog.sqlite3'` (`workbench/office_service.py:34`).
   - The PDF vault is `config_dir()/'libraries'/sha256(owner)[:24]/'quarantine'` (`workbench/intake_service.py:103`).
   - So a fixture is always a workspace plus profile pair.
3. **Office operations require the identity `desktop-owner`.** `office_service.owner()` (`:61`) raises `OFFICE_ACTUAL_OWNER_PROFILE_REQUIRED` for any other identity. Use `operator()` with its default identity; `operator('campaign')` would be refused.
4. **Set `ARC_LEDGER_EMBEDDED=1`.** Without it, `engine.engineering()` → `host_client.engineering()` (`workbench/host_client.py:158-165`) starts or attaches to a background host service on Linux. Constructing `Kernel(root)` directly avoids that too.
5. **Restores refuse any destination inside the program folder.** `locations.ensure_workspace` (`locations.py:117`) and `workspace_backup.restore` (`workspace_backup.py:203`) both check this. Campaign workspaces must live outside `/home/user/Struthio`, including outside its `build/`.

## 1. How a workspace is created and seeded

**`workbench/locations.py`**
- Marker: `MARKER='LEDGER_WORKSPACE.json'`, `SCHEMA='arc.ledger-workspace/1'`, `KINDS=('NO_PROJECT','PROJECT')` (`:25-27`).
- `ensure_workspace(path, kind, name)` (`:115`) creates the folder with mode 700 and writes the marker atomically.
- `office(path)` (`:99`) is `ensure_workspace(... name='Office')` plus an `Ingress/` folder.
- `concern_home()` (`:48`) is `$ARC_LEDGER_CONCERN` or `~/Concern`.
- `default_root()` (`:52`) uses `$ARC_LEDGER_WORKSPACE`, then `$ARC_LEDGER_EDITION=office`, then `~/Concern/Ledger`.
- `program(root)` (`:34`) is the code folder. It is shared and read-only across workspaces.

**Kernel state.** `Kernel.__init__` (`engineering_kernel.py:342-379`) sets `root/.ledger/engineering.sqlite3` (WAL, mode 600) and runs every service's `ensure(db)`. Database locks are per path (`database_guard.connection`, `:17`), so two kernels on two roots do not interfere.

**Per-user data folder.** `session.config_dir()` (`session.py:41-47`) is `$ARC1_WORKBENCH_CONFIG_HOME`, else `$XDG_CONFIG_HOME/arc1-workbench`. `Session(path, project)` (`:80`) defaults to `config_dir()/'session-r10.json'`; every UI check passes `RUN/'profile/session.json'` instead. The case's `profile/session.json` holds the window layout only and is not needed headless.

**Seeding from the backup (`workbench/workspace_backup.py`)**
- `verify(backup)` (`:140`) checks sha256 and SQLite integrity.
- `restore(backup, root, profile)` (`:200-234`) only writes to new paths (`fresh()`, `:32`). It publishes with `renameat2` no-replace and returns `{'workspace','profile','open':[...]}`.
- `create(root, out)` (`:160`) snapshots the workspace together with the profile that `config_dir()` currently points at. It holds `state_backup.closed_ledger` and copies databases with the SQLite backup API (`state_backup.copy_database`, `:103`).
- The `*_checks.py` modules already use create-then-restore to prove a reopen: `continuing_checks.py:95`, `slate_checks.py:59`, `edit_checks.py:113`.

**Case contents** (read read-only from the extracted backup)

| Record | Where it lives | Content |
|---|---|---|
| Sheet `owner:db5f669f863d4c71b89fa7ba348957da` "07 Bench readings" | profile catalog | B2 = `12` V, **B3 = `280` mA**, B4 = `650` mA |
| Sheet origin | same record | `profile='reviewed-pdf-table-v1'`; `pdf` = {name `07_Bench_Readings.pdf`, item `c1d3fc85…`, page 0, sha `2c60377d…`}; `reviewed_rows` (sheet_row 3 → value `'280'`, unit `mA`, `original_cells`) |
| Calculation `0e39bf65e24740a29a504a6be6e00885` "07 Settled power · 3.36 W" | workspace `desk_records`, revision 2 | `voltage * settled_current`, inputs B2 and B3 |
| Calculation `500cd60e…` "07 Startup power · 7.8 W" | same | reads B2 and B4 of the same sheet |
| Investigation `c574ae94…` "After Hours 07" | workspace | the dependent finding is claim `f2a610f24ca84112a400e02d6ad04869`: "Settled draw is 3.36 W. Rev B allows 6 W." |

**Problem with shipping the case.** The case database and `session.json` contain the builder's absolute paths (`/workspace/scratch/38aead9d7517/...`). `tools/check_hatch.py:113-115` flags these as `developer-machine-path`. Also, `.ledger` is in `PRIVATE_PARTS` (`check_hatch.py:107`) and in `.gitignore`. So the case cannot be committed as an unpacked tree, and should not ship in the payload.

**Can two workspaces exist side by side?** On disk, yes. In one process, no: `config_dir()` reads the environment on every call, so the profile is effectively process-global. Run one subprocess per attempt with this environment:
- `workbench.baseline.environment(base, root, profile)` (`baseline.py:15-19`) sets `ARC1_WORKBENCH_CONFIG_HOME`, `ARC_LEDGER_WORKSPACE`, `ARC_LEDGER_EMBEDDED=1`, `ARC_LEDGER_DISABLE_BOOK_WATCHER=1` and `PYTHONDONTWRITEBYTECODE=1`.
- Add `HOME=<attempt>/home` and `ARC_LEDGER_CONCERN=<attempt>/home/Concern`. `field_source.settle_tables` (`:157-165`) compares `concern_home()/'Office'` with the root.
- Add `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_STATE_HOME` under the attempt. They are used by `record_store.py:312`, `launch.py:70` and `setup_arc1.py:116`.
- Pop `ARC_LEDGER_XSESSION`.

## 2. Driving the real operations without the window

```python
k = Kernel(ws); P = operator()          # identity 'desktop-owner'
r = k.dispatch(op, args, P)             # {'ok', 'result' | 'error', 'correlation_id'}
```

`dispatch` (`engineering_kernel.py:487-547`) validates the schema, checks scope, records activity and the work trail, and audits. It never raises; refusals come back as `{'ok':False,'error':{code,message}}`.

**Operations for the anchor case**

| Step | Operation | Scope | Where |
|---|---|---|---|
| Find ids | `field.read` | read | `field_service.py:70` → `field_source.read_field` (`:411`) |
| Name to cell ("settled current" → B3) | `field_ripple.cells_named(k, P, obj)` | (function) | `field_ripple.py:60`; the window's parser is `shell2.set_asked` (`:2459-2483`, Qt-bound) |
| Preview what moves | `field.ripple {"id":"office:<sheet>","set":{"B3":"300"}}` | read | `field_ripple.ripple` (`:107`) |
| Change B3 | `field.set {id, cell, value, expected_revision}` | execute | `set_cell` (`field_service.py:163-194`): reads `office.get`, refuses if `revision != expected`, saves through `office.save`, returns `{was, now, unit, revision, words}` |
| Recalculate | `office.datasheet.recheck {id:<calc doc>, expected_revision:<int doc rev>}` | approve | `datasheet_work.dispatch` (`:319`) → `report(... replaces=...)` (`:181`); creates a new page with `derivation.replaces` and renames "· 3.36 W" to "· 3.6 W" (`:254-260`) |
| Source link | `field.trace {"id":"document:<calc>"}`, `office.get <sheet>` (`origin.reviewed_rows`, `source_state`), `intake.read {id:item}` | read | `field_service.py:83`, `office_service.get` (`:59`) |
| Settle the finding | `investigation.claim` (rewrite with new number) or `investigation.review RETIRE` | execute / approve | offered by `field_do._claim` (`:115-172`) |

**What each operation is allowed to do by itself.** `workbench/stacy_hand.py` is pure and has no Qt.
- `hers(place, scope, op)` (`:150`): `HERS_SHOW` includes `field.set`. `office.datasheet.recheck` and `investigation.claim` are only in `HERS_FREE`.
- `ALWAYS_ASKS` covers `*.review`.
- `takes_back()` (`:193`) writes the Undo line for a `field.set`.
- The runner's "approvals" can be decided by `hers()` plus a scripted approve list in the case.

**Expected record state after `field.set` then the recheck of the settled calculation** (all Qt-free)
- **Sheet:** `office.get` shows `cells.B3.value == '300'` with unit `mA`, and a new `revision`. A second subprocess reading it covers "save and reopen".
- **Source still 280 mA:**
  - `origin.reviewed_rows[sheet_row==3].value == '280'`;
  - `source_state.state == 'CURRENT_PDF_SOURCE'`;
  - the quarantine object `2c60377d…` hash is unchanged;
  - the new calculation's input has `basis == 'WORKING_SHEET_EDIT'` (`datasheet_work.py:225`) and still carries `original_cells`.
- **Calculation:** the new page's `derivation.calculation.outputs[0].value` = {decimal `'3.6'`, rational `'18/5'`, unit `W`}. Compare the rational or the `Decimal` value, never the string "3.60".
- **Old calculation:** retired from the Field (`read_field`, `:418-422`).
- **Finding:** `field.read` gives claim `f2a610f2…` state `'recheck'`, with first line `'says 3.36 W; now 3.6 W'` (`field_source.py:425-430` via `_moved` at `:451` and `field_model.carries` at `:35`). This flag is derived when the Field is read; nothing is stored, and `inv_claims.review` stays `CURRENT`. It appears only after the recheck, not after `field.set` alone.
- **Side effect to declare:** any saved sheet change sends all of that sheet's calculations to `RECHECK_SHEET_CHANGED` (`report_state`, `:166-178`). "07 Startup power · 7.8 W" will also read `recheck` unless it is rechecked too. The expected outcome must list this.

Every Field module used here is Qt-free: `field_source`, `field_do`, `field_ripple`, `field_doubt`, `field_model`, `field_brief`, `field_service`, `datasheet_work`, `office_service`, `investigations`, `stacy_hand`, `model_turn`, `local_brain`. `field_page.py` and `field_qt.py` are Qt.

## 3. Existing harnesses

**Offscreen UI checks (`tools/check_*_ui.py`).** The template is `check_desk_ui.py:59-90`:
- `RUN=tempfile.mkdtemp()`; a `screen.json` for `QT_QPA_PLATFORM='offscreen:configfile=…'`;
- environment `ARC_LEDGER_EMBEDDED=1`, `ARC_LEDGER_DISABLE_BOOK_WATCHER=1`, `ARC1_WORKBENCH_CONFIG_HOME=RUN/profile`, `ARC_LEDGER_CONCERN=RUN/Concern`;
- patches on `clip._request`, `Kernel.launch`, `Kernel.submit`, `session_power.system` and `QMessageBox.question`;
- then `make_app([])`, `locations.office(RUN/'workspace')`, `Session(RUN/'profile/session.json', root)`, `WorkbenchWindow(root, session, restore=False)` (`qt_app.py:2292`, `make_app` at `:5319`);
- the kernel is reached as `w.ledger_bridge.kernel`. A reopen is shown at `check_desk_ui.py:1178` and `check_return_thread_ui.py:116`.

None of them opens After Hours 07; all start from an empty Office.

**Child-process runner.** `tools/check_hatch.py:148` `run(command, timeout, ...)` runs a child interpreter and reads its last JSON with `tail_json` (`:129`). `check_release.py` is a 12-line wrapper around `check_hatch.py`. Sections: runtime (`check_stage_one.py`), registry, privacy, `--self-test`, and `--ui` (`UI_CHECKS`, `:64`).

**Test fixtures.**
- `tests_integrated/protocol_fixture.py` `ProtocolWorker` is a loopback llama.cpp double with a canned `reply()` per output contract and patches on `worker_live` and `launch`. It is reusable for scripted-model and resource-simulation runs.
- `test_workspace_backup.py:20-36` shows the standard holds.

**Probe scripts outside the repo.** `scratchpad/tools/edge/common.py` and `scratchpad/tools/field/real.py` already restore the demo pair into a fresh run, set the environment, apply the holds and call `read_field`. They are the closest thing to a runner.

**Other places.** `workbench/journey.py` is unrelated (Control Center stages). The only "rehearsal" is a document (`docs/MODEL_TRIAL_03.md`). `agent_loop.py` has durable pause and resume states (`agent.pause` / `agent.resume`), which are useful later for the owner-takeover cases.

**Missing**
- A case format, manifest, runner and fixture builder.
- A headless natural-language path from request to operations. "Change the settled current…" is parsed only in `shell2.SlateFace.set_asked` and staged by `field_page.stage_set` (`:496`), both Qt. Without a window, the runner can only run scripted or known-good operation lines (`field_do.call(line)`, `:46`). Model-selected actions need the offscreen window.
- Timeout and checkpoint handling.

## 4. Proposal (buildable in a day)

### Fixture layout
- Do not ship the fixture. Keep the original zip outside the payload and pass it with `--fixtures DIR` (default `~/Graphite_Campaign/fixtures`). `tools/package_graphite.payload_paths` (`:109`) ships every file outside `build/`, and the case contains machine paths.
- `fixtures/after_hours_07/` contains `Graphite_Backup/` (verified with `workspace_backup.verify`) and `FIXTURE.json` with:
  - `{id, backup_sha256 (sha of BACKUP.json), ids: {sheet, calc_settled, calc_startup, claim_settled, investigation, pdf_item}}`.
- Builder `build_fixture(zip, out)`: unzip into an empty folder, `verify`, `restore` once into `golden/ws` and `golden/profile`, open `Kernel(golden/ws)` once so migrations run, then record the ids by title from `field.read`.

### Reset between attempts
- Copy `golden/` to `runs/<run>/<case>/<attempt>/{ws,profile}` with `shutil.copytree`. This takes under a second for about 2 MB, and the `edge/common.py` probe already does it.
- Alternatively, `workspace_backup.restore` straight from the backup, which is the product's own path and is verified.
- Also create a fresh `home/` per attempt.

### Case file (JSON, one per case, `cases/AH07-anchor.json`)
```json
{"id":"AH07-A01","situation":"07","revision":1,"fixture":"after_hours_07","budget_s":120,
 "start":{"selected":"office:<sheet>","dial":"show","apply":[]},
 "inputs":{"request":"On this working copy, change settled current from 280 mA to 300 mA, ...","answers":[],"approvals":["field.set","office.datasheet.recheck"]},
 "allowed":["field.read","field.trace","field.ripple","field.set","office.get","documents.get","office.datasheet.recheck","intake.read"],
 "script":["/field.set {...}","/office.datasheet.recheck {...}"],
 "expect":[{"read":"office.get","id":"<sheet>","path":"document.sheets.0.cells.B3.value","eq":"300"},
           {"calc":"Settled power","value":"18/5","unit":"W"},
           {"finding":"<claim>","state":"recheck"},
           {"source_row":3,"eq":"280"},{"reopen":true}],
 "resume":{"checkpoint_after":1}, "faults":[]}
```
- `script` is the known-good path. `mode: "scripted" | "offscreen" | "model"` picks the driver.
- Placeholders such as `<sheet>` resolve from `FIXTURE.json` ids.
- Keep `expect` out of anything handed to the model.

### Attempt worker (`tools/campaign.py --child`)
- Runs in its own process group with the environment from section 1.
- After each step it appends `{t, step, op, args_digest, ok, result_digest, approved_by}` to `attempt/progress.jsonl` and flushes. That file is the partial result.

### Timeout
- The parent runs `subprocess.Popen(..., start_new_session=True)` and waits `budget_s`.
- On expiry it sends `os.killpg` SIGTERM, then SIGKILL after 5 s, and writes `result.json` with `verdict:"Timeout"`, the last durable step from `progress.jsonl`, and the grades it can still compute by reading the attempt's folders in a fresh child.

### Checkpoint and resume
- At `checkpoint_after`, the child calls `workspace_backup.create(ws, attempt/ckpt_<n>)`. This uses the profile from the environment and closes the ledger.
- The resume test is a second child that runs `workspace_backup.restore(ckpt, attempt/resume/ws, attempt/resume/profile)`, re-reads `office.get` for the revision, runs the remaining steps, and grades.

### Per-attempt `result.json`
- Identity: `{case_id, case_sha256, fixture_sha256, build: {version: workbench.version.VERSION, git_head, manifest_sha256}, model: {file_sha256 | null}, host, env_keys}`.
- Run record: `{started, ended, mode, steps:[...], approvals:[...], fallbacks:[...]}`.
- Grading: `{checks:[{name, ok, got, want}], verdict: Pass|Partial|Blocked|Fail|Timeout, reason, last_durable, reopen: {sheet_revision, calc_doc}}`.
- Also save `trace.txt`, plus `shot.png` in offscreen mode.

### Manifest and summary
- Write `runs/<run>/MANIFEST.json` with `{run, cases:[{id, sha256, fixture, attempts:[path]}], build, started}` before the first attempt. A rerun reads it (`--rerun FAILED`).
- `SUMMARY.md`: a counts line, one table row per case (verdict, seconds, reason, first failing check), and the failures grouped by the step that broke.

### One-day order
1. Fixture builder and reset.
2. Scripted child with the AH07 anchor and its five checks (sheet B3 = 300, calculation 18/5 W, finding recheck, source row 280, reopen in a new process).
3. Parent with timeout and kill, partial results, manifest and summary.
4. Resume case through create/restore.
5. Offscreen mode, by copying the `check_desk_ui.py:59-90` setup, with the holds removed only where the case grants them.

## 5. Not found, and risks

- **No `office.datasheet.recheck` for a sheet as a whole.** It works per calculation page, and needs the integer document revision (`project_desk.REV`).
- **"Working copy" is not `copies.*`.** `working_copies.py` is for home-folder files. In this case the working copy is the reviewed office sheet.
- **"Return to the same Field tile" and "follow the source link" have no headless equivalent.** They are Qt only (`field_qt`, `pdf_qt`). Only `field_zoom` is kept in the session (`session.py:122`).
- **Release check.** A new `tools/campaign.py` ships, so the release check fails until the manifest is rewritten by packaging (`check_hatch.runtime_section`, `EDITED_SOURCES_NOT_YET_PACKAGED`). The operation registry is untouched as long as no Kernel operation is added.