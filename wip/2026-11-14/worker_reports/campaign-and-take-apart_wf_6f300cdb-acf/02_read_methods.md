Graphite has no clearance method today. The nearest thing is a staC line over a CSV, such as `@files:clearance.csv | rows | where Clearance at least 0.5`. On the four mm rows it gives exactly the pass/fail split the brief expects. It cannot handle units: "0.028 in" is compared as 0.028, and a blank unit passes silently.

Tree read: `/home/user/Struthio` at 0354ca1. The repo moved from b6883da during the read (another session is committing), so line numbers are from the working tree as I read it.

## Claims

**Claim 2: PARTLY.** What the release notes say about the Field holds. The "same operation under a click and under Kas's request" is not in place.
- **Holds:** each sheet carries an exact read-only staC line (docs/RELEASE_NOTES_0.3.md:21; built at workbench/field_source.py:216, :232). The Field reads through `self.kernel.dispatch` (field_source.py:90-101, notes :47).
- **Holds:** Shift+Enter and "Run its staC" go `field_page.stac_run` → `context_menu.run_stac` → the console → Kernel.dispatch (field_page.py:619-631, context_menu.py:235-249, :1406). There are also six `field.*` operations (field_service.py:7-21, dispatched at engineering_kernel.py:626). Those came in 0.4.1 (engineering_kernel.py:57), not 0.3.
- **Missing — nothing ties Kas's answer to the operation the click runs:**
  - Her fixed set of operations includes `language.run` and `documents.get` but no `field.*` (local_brain.py:521-525).
  - Any further operations are chosen by word matching (tool_selection.py:1-9).
- **Missing — staC refuses every line in the dev tree today:** `language.run` refuses unless the seed binding is current (stacy_language.py:9-13). At HEAD the seed is STALE, with 20 changed sources. Packaging rebuilds it (tools/package_graphite.py:79-107). The probe below shows the refusal.

**Claim 6: PARTLY.** The comparison arithmetic holds; the units, missing-unit, fork and parent-revision parts do not exist.
- **Holds:** the four mm rows behave as the brief expects (probe below).
- **Missing — no clearance, limit or threshold operation:** the probe found only `math.units`.
  - `stac/quantities.py:115` `assess_upper_bound` is upper-bound only, and nothing in the repo calls it.
- **Missing — "0.028 in → 0.7112 mm, explicit":** there is no inch in any unit table (detail under Units below).
- **Missing — "Unit missing":** in staC a blank unit passes silently.
  - The one existing refusal of a blank unit is datasheet_work.py:208-210, and it rejects the whole report, not one row.
- **Missing — "a change to the original is never silently applied":**
  - Today's reusable form, a staC word, is overwritten in place with no revision (stac_words.py:91) and written out again at each run.
  - So a change does reach every use silently.
- **The pattern exists elsewhere:** checked methods and artifacts bind to an exact revision and refuse on any change (checked_methods.py:46-52, typed_artifacts.py:57-60). No diff view exists.
- **Dependency account:** exists only in pieces (see "What records a result's inputs").

**Claim 8: the citations HOLD; as a description of the base, PARTLY.**
- **docs/STAGE5.md:60-68 holds.** `procedure_save` stores steps with prerequisites (`after`) and checks (`require`), plus operations, effects and origin (continuing_work.py:27-32, :627-650).
  - Instantiating yields a DRAFT that needs its own grant (continuing_work.py:670-688, then `work.authorize`).
  - But procedures are owner-scoped, with no project, no revision and no parent; they are insert-only (continuing_work.py:77, :649).
  - They are limited to 8 operations (continuing_work.py:22-23).
  - Each use needs an assignment, working copies, a budget, an expiry and a grant, so a procedure is not a one-click menu command.
- **docs/BOSS_IMPLEMENTATION_PLAN.md:176 holds as intent only:** P14 is `State: PLANNED` (:182).
- **Closest thing to the menu idea:** "Your words ▸" (context_menu.py:1321-1339). It lists the workspace's staC words and runs them without the model.
  - It is not per-project.
  - It has no compatibility test, apart from words whose line starts with `this`.
  - It keeps no revisions.

## The four questions

**Closest thing to "a 0.50 mm clearance method applied to each row of a CSV":**
1. **A staC line over a CSV in Files.**
   - The file is read through `@files:` (addresses.py:55, files_service.py:268-278, with numbers turned into floats at :260-265).
   - `where X at least/under N` compares (typed_pipeline.py:8-9, :178-187, :231-234).
   - It can be kept as a word.
   - It filters rows rather than returning a pass/fail verdict per row, it uses floats, the minimum is a literal in the line, and a non-numeric row drops out of both lists.
2. **The PARTS registered check** (worker_tasks.py:59-70). This is the only per-row check that reports failures with a reason.
   - It uses exact Decimal and refuses non-finite rows.
   - But its columns are fixed (Part, Need, Have), it has no threshold parameter or units, and it runs only in the protected worker (STAGE5.md:46-48).
3. **The checked-method record shape** (checked_methods.py:79-90, :113-124, :152-156, :208-219). It is the right shape for a method:
   - typed inputs, preconditions, expected checks, failure cases, revision, ACCEPTED state, history, preview, instantiate, and a result that binds the method's `{id, revision, digest}`;
   - but it has a single profile, `ledger.additive-capacity-method/1` (:5).
4. **Exact relations in the calculator.** `math_model` has `ge`/`le` and the other comparisons, with dimension checks (math_model.py:15, :121, :144). Length is not a dimension it knows, though.

**Where a project-scoped fork would live:** the Project Desk store.
- `desk_records` has a `project` column, and `desk_history` keeps every revision (project_desk.py:86-88, :121-145).
- `checked_method` records already carry `project` (checked_methods.py:79-80).
- The parent link to copy is typed_artifacts' `reference()` = `{id, revision, digest}` (typed_artifacts.py:16-18, :33), with its check on parent revision (:57-60).
- `methods.get` already returns a method's history (checked_methods.py:179-187), which a diff could be built from.
- Words (`stac_words` table, stac_words.py:43; no owner filter at :61) and `flow_procedures` (owner-scoped, no project) are not suitable homes.

**Units:** there are two tables, and neither has inches.
- The calculator's table (stac/quantities.py:19-42, math_units.py:6-8) covers time, frequency, voltage, current, power and memory. It has no length, so the exact path refuses `mm`.
- The table for numbers written on a page (quantities.py:36-75) carries length as a "local dimension" (mm has factor 0.001, base m). It has no `in`/`inch`/`mil`/`thou`, so `extract('0.028 in')` returns a plain number with no unit.
- The only 25.4 in the code is in viewers (universal_view.py:675/685/735, program_vector.py:74).
- So a conversion today is a hand-written `add mm = Clearance * 25.4`. It is computed as a float and rounded to 6 places (typed_pipeline.py:119, :157), and the factor exists only in the line's text.

**What records a result's inputs:**
- **staC result:** the plan (text, call, transforms, `seed_id` = Graphite's source binding, `plan_id`) and the rows (stacy_language.py:116-127). There is no file hash (probe).
- **`desk.sources.read`:** gives the file's sha256 and a `content_revision` (project_desk.py:443-467). `call_binding` and `freshness` give a CURRENT/CHANGED state per source (:164-211). This is the make-like piece.
- **Datasheet calculation:** the derivation stores the sheet and its revision, the PDF source with its sha, each input (cell, value, unit, conditions, basis), the recipe and the model digest (datasheet_work.py:249-251). A recheck re-runs the recipe on the current sheet (:326-336). The conversion factor and tool version are not recorded.
- **Checked-method result:** the method reference, the problem revision and the context digest. Its action also carries `components`, a sha256 per implementation file (checked_methods.py:116-121, joined_work.py:21-25). Any change to these marks the result STALE (checked_methods.py:162-174).

## Probe output
Run inside unshare with the probe's own HOME, config home and workspace, offscreen, kernel in-process, on a scratch copy of HEAD whose seed I rebuilt the way packaging does. The repo was not touched.
```
seed check as shipped (dev tree): REFUSES: Graphite seed/source binding is not current
'mm' -> {"dimension": "length", "kernel_unit": null, "factor": "0.001", "base_unit": "m"}
'in' / 'inch' / 'mil' / 'thou' / '' -> null
unit_spec mm refused: UNKNOWN_OR_AMBIGUOUS_UNIT: mm
exact 'c >= m', unit '1' at 0.50/0.50 -> [{"value": true}];  unit 'mm' -> refused
language.run on clearance.csv (C1 .49 mm, C2 .50 mm, C3 .69 mm, C4 .70 mm, C5 .028 in, C6 .55 <blank>):
at least 0.5 -> ['C2','C3','C4','C6']   under 0.5 -> ['C1','C5']
at least 0.7 -> ['C4']                  under 0.7 -> ['C1','C2','C3','C5','C6']
row 'n/a' (engine only) -> in neither list
where Unit=in | add mm = Clearance * 25.4 -> 0.7112 (float 0.7111999999999999, rounded)
result keys: execution, model_calls, plan, rows, schema;  result names a file hash: False
desk.sources.read -> sha256 f22c17…, content_revision def603…
field.read with only this Files CSV -> 0 objects
```

## Experiment 9

**Already there to stand on:**
- The staC pipeline over a Files CSV, and words with the "Your words ▸" menu (typed_pipeline.py, stac_words.py, context_menu.py:1321).
- Kas's fixed set already includes `language.run` (local_brain.py:521).
- Exact comparison with dimensions (math_model.py, math_units.py).
- Length in the page-number table (quantities.py).
- The revisioned, project-aware desk store with history (project_desk.py).
- The parent-reference pattern (typed_artifacts.py).
- The checked-method record shape, with preview, instantiate, and a result bound to the method revision and implementation hashes (checked_methods.py).
- Source freezing and freshness (project_desk.py:164-211, :443-467).
- A reserved `method` kind in the Field (field_model.py:15-23).
- The per-sheet staC line and "Run its staC".
- Re-running a recipe on today's inputs (datasheet_work.py:326-336).

**Missing:**
1. **A check that gives each row a verdict,** with exact Decimal math and reasons (pass, fail, unit missing, not a number). Files: either a new staC transform in sdk/cli/arc1cli/typed_pipeline.py, or a new read operation in a new workbench module, wired into engineering_kernel.py (`_dispatch`, SCOPES) and the schemas in engineering_cli.py.
2. **Inches.** Add `in`/`inch`/`inches` = 0.0254 m exactly (and mil/thou if wanted) to quantities.py BASES/WORDS. Record each row's conversion as written unit, factor and converted value. Update the helper's limits in helpers.py:47-77.
3. **A row-check method record.** Columns, relation, minimum with its unit, state, revision, project, and a parent `{id, revision, digest}`. Build it in checked_methods.py or a sibling module, stored through project_desk.py.
4. **A fork operation and an "original changed" view.** Compare the stored parent reference with the original's current revision and show the difference from `desk_history`. The pinned menu entry stays on its revision until the owner moves it.
5. **A result record.** Method `{id, revision, digest}`, the source's `content_revision` (via `desk.sources.read`), a digest of the unit table, the seed id and implementation hashes, and the rows with their verdicts. "Run again" re-reads the source chosen now.
6. **A per-project menu entry with a compatibility test,** pointing at a method revision rather than a word. Files: context_menu.py, field_page.py.
7. **The Field shows methods, results and Files CSVs.** field_source.py has no reader for these today, even though the `method` kind exists.
8. **Kas calls the same operation as the menu:** the new check operation, either added to her fixed set in local_brain.py:521-525 or picked by tool_selection.py, so her inputs and results can be compared with the click's.
9. **A current seed:** run the experiment from a packaged kit, or rebuild the seed first (tools/package_graphite.py:79-107). Otherwise every staC line is refused.
10. **The Inspect card** (Preview / Open method / Fork): field_qt.py and context_menu.py.

Scripts and the scratch tree are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/take_apart/methods/` (`scripts/pure_probe.py`, `scripts/kernel_probe.py`, `prog/` with the rebuilt seed).