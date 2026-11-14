# Experiment 9 build slice: one clearance method you can take apart

All paths are relative to `/home/user/Struthio`. I re-read the code at HEAD **34f00ba**, which has a clean working tree, and the line numbers below come from that commit. Nothing in the repository was written.

**The seed has changed since the readers ran.** The words reader found the seed `STALE`, so every staC line was refused. At 34f00ba, commit "…seed rebuilt", `stacy_foundation.seed_status` reads `VERIFIED_SOURCE_BINDINGS` with 0 changed sources. That state is fragile: 485 files are seed inputs, including `shell2.py`, `engineering_kernel.py`, `engineering_cli.py`, `local_brain.py` and `chain_menu.py`. Any edit to one of them makes `language.run` refuse until the seed is rebuilt. So this slice does three things:
- **The experiment does not need staC.** Every clearance action dispatches a registered Kernel operation directly, so a stale seed cannot block it.
- **The seed is recorded, not required.** The seed state is shown in Inspect and is not a condition for running.
- **The seed is rebuilt last.** The slice ends with `tools/package_graphite.py --rebuild-seed`.

**What is new:**
- Two modules: `workbench/clearance_methods.py` (Kernel) and `workbench/clearance_qt.py` (Talk and the right-click menu).
- One fixture tool and two test files.
- A few lines each in `engineering_kernel.py`, `engineering_cli.py`, `shell2.py` and `context_menu.py`.

Another session is editing `shell2.py` and `context_menu.py`, so the edits there are kept to a few lines.

---

## 1. The method and its check: `workbench/clearance_methods.py`

**Functions:**
- **`judge(text, method)`**: pure, with exact `Decimal`. It takes the CSV text, applies `csv.reader` and finds the method's bound columns (`Ref`, `Clearance`, `Unit`). It returns one row per data line with these fields: `ref, written, value, unit, mm, conversion, minimum, verdict, reason`.
  - A value must match `^-?\d+(\.\d+)?$`. Anything else gives `NOT_A_NUMBER`.
  - A blank unit gives `UNIT_MISSING` and no arithmetic is done.
  - A spelling outside the table gives `UNKNOWN_UNIT`.
  - Spellings accepted: `mm`, `millimetre(s)` and `millimeter(s)` read as mm; `in`, `inch` and `inches` read as in.
- **`UNITS = {'mm': '1', 'in': '25.4'}`**: exact, and copied into each method record so that the record's digest covers it.
- **`implementation()`**: the sha256 of this file plus `workbench.version.SHORT`.
- **`dispatch(kernel, op, args, p)`**: in the style of `checked_methods.dispatch`, storing records through `project_desk.new/write/edit/read`.

**Operations:**

| Operation | Scope | What it does |
|---|---|---|
| `clearance.create` | execute | `{project, folder, title, ref_column, value_column, unit_column, minimum, minimum_unit, note?}` |
| `clearance.get` | read | `{id, revision?}`. Returns the method at that revision (an older one is read from `desk_history` and its digest checked), its `history`, and `parent_state` |
| `clearance.list` | read | `{project?, folder?}` |
| `clearance.check` | read | `{method, revision, source}` |

**How `clearance.check` reads its source.** It reads the CSV once through `desk.sources.read` (`project_desk.py:443-467`) and decodes `exact_bytes_base64`. So the bytes it judges are the bytes it hashes. It does not use `files.get`, because `files_service.number` (`files_service.py:257-265`) turns cells into floats. A file over 128 KiB is refused with `CLEARANCE_SOURCE_TOO_LARGE`. The result has no timestamps, so two identical calls give identical results:
```
{schema:'ledger.clearance-result/1', saved:false, model_calls:0,
 call:{operation:'clearance.check', arguments:{…}},
 method:{id, revision, digest, title, minimum, minimum_unit, parent, current_revision},
 source:{address, bytes, sha256, content_revision, rows},
 conversion:{table, digest}, implementation:{file, sha256, release},
 rows:[…], counts:{…}, account:[readable "result ← …" lines]}
```

**Records written** (`create` only):
- One `desk_records` row of kind `clearance_method`, with these fields: `schema 'ledger.clearance-method/1'`, `profile 'ledger.clearance-minimum/1'`, `project`, `folder`, `title`, `columns`, `relation 'AT_LEAST'`, `minimum` (a string), `minimum_unit`, `units`, `units_digest`, `parent: null`, `notes`, and `authority 'READ_ONLY_CHECK_NO_PHYSICAL_QUALIFICATION'`.
- One `desk_history` row and one `desk_events` row, with event `CLEARANCE_METHOD_CREATED`.
- `check` writes nothing beyond the Kernel's existing request journal entry.

**Fixture** (one file, `SLIM4/clearance.csv`):
```
Ref,Clearance,Unit
C1,0.49,mm
C2,0.50,mm
C3,0.69,mm
C4,0.70,mm
C5,0.028,in
C6,0.60,
```
- C6 is 0.60 on purpose: it lies between the two minimums, so a check that ignores the missing unit would pass it at 0.50 and fail it at 0.70.
- With LF line endings the file is 84 bytes, with sha256 `5a1262c7b9ac11ef68cec860443d72e47725d3ecaf54f3bb36c20a41bb5074df` and `content_revision` `c31802b14b5b134374f46a22231ccbcd8525ccd506c1b1058703773c259f95e4`.
- The conversion table's digest (`project_desk.digest({'in':'25.4','mm':'1'})`) is `77aebfa5dd490f1f8a5d28c404e042d55fd79ed7e5593f6f8788af9611b54d0e`.

**Tests** (`tests_integrated/test_clearance_methods.py`, in-process Kernel, with the `setUpModule` holds of `test_project_desk.py`: no worker, no provider, seed patched):

| Ref | written | mm | conversion | original 0.50 mm | fork 0.70 mm |
|---|---|---|---|---|---|
| C1 | `0.49 mm` | `0.49` | – | FAIL `0.49 mm is under 0.50 mm` | FAIL `0.49 mm is under 0.70 mm` |
| C2 | `0.50 mm` | `0.50` | – | PASS `0.50 mm is at least 0.50 mm` | FAIL `0.50 mm is under 0.70 mm` |
| C3 | `0.69 mm` | `0.69` | – | PASS | FAIL `0.69 mm is under 0.70 mm` |
| C4 | `0.70 mm` | `0.70` | – | PASS | PASS `0.70 mm is at least 0.70 mm` |
| C5 | `0.028 in` | `0.7112` | `0.028 in × 25.4 = 0.7112 mm` | PASS | PASS `0.7112 mm is at least 0.70 mm` |
| C6 | `0.60` | `None` | – | UNIT_MISSING | UNIT_MISSING `Unit missing: 0.60 has no unit, so it is not compared` |

- **Counts:** the original gives `{PASS:4, FAIL:1, UNIT_MISSING:1}` and the fork gives `{PASS:2, FAIL:3, UNIT_MISSING:1}`. `mm` for C5 is exactly the string `'0.7112'`, never `0.7111999999999999`.
- **Pure extras** (not in the fixture): `n/a` gives NOT_A_NUMBER, `1e-3` gives NOT_A_NUMBER, and `ft` gives UNKNOWN_UNIT with `No conversion to mm is known for “ft”`.
- **Records the result depended on:**
  - `source.sha256` equals the sha256 of the file's bytes. The Linux constants above are asserted only when `os.linesep == '\n'`.
  - `conversion.digest` is the value above.
  - `implementation.sha256` equals the sha256 of `clearance_methods.py`.
  - `model_calls == 0` and `saved is False`.
- **Refusals:**
  - A CSV without `Unit` gives `CLEARANCE_COLUMNS_MISSING: the table has no column “Unit”`.
  - A `.txt` source gives `CLEARANCE_SOURCE_NOT_A_TABLE`.
- **Why the method exists:** `language.run "@files:SLIM4/clearance.csv | rows | where Clearance under 0.70 | select Ref"` returns `C1, C2, C3, C5, C6`. The bare-number answer fails C5 and drops C6 into the list, while the method gives C5 PASS and C6 UNIT_MISSING.

**Left out:**
- Inches in `quantities.py`: `in` is an English word, so "3 in the box" would become inches in prose extraction.
- Units other than mm and in.
- Other relations or dimensions. There is one profile only.
- A persisted result record. A check is a read and saves nothing.

## 2. Fork, revise, difference, side by side (same module)

**Operations:**

| Operation | Scope | What it does |
|---|---|---|
| `clearance.fork` | execute | `{id, expected_revision, title, minimum, note?}`. A new record that copies every field and records `parent: {id, revision, digest, title}` of the original at `expected_revision`. It keeps the same `project` and `folder`. |
| `clearance.revise` | execute | `{id, expected_revision, minimum?, title?, note}`. A new revision of the same record. |
| `clearance.diff` | read | `{id, from_revision, to_revision}`. Returns `[{field, was, now}]` over title, columns, relation, minimum, minimum_unit and units. |
| `clearance.compare` | read | `{source, method, revision, against_method?, against_revision?, draft_minimum?}`. Exactly one of `against_*` or `draft_minimum`. It reads the source once and judges it twice. Returns `{source, left, right, rows:[{ref, written, mm, left, right, changed}], changed:[refs]}`. |

**How changes stay visible:**
- `clearance.get` on a fork compares its parent's recorded revision with the parent's current one. It returns `parent_state: CURRENT | PARENT_CHANGED` and `parent_change: [{field, was, now}]`.
- A fork never reads its parent at run time. So a change to the original is shown and is never applied to the fork.

**Records written:**
- `fork` writes a new `clearance_method` record (revision 1, `parent` set), with history and event `CLEARANCE_METHOD_FORKED`.
- `revise` writes revision n+1, with history and event `CLEARANCE_METHOD_REVISED`.
- A stale `expected_revision` is refused with the existing `REVISION_CHANGED`.

**Tests:**
- **Fork:** forking the original at revision 1 with `minimum '0.70'` gives `parent.revision == 1` and `parent.digest == project_desk.digest(original@1)`. A fork with `expected_revision: 2` is refused with `REVISION_CHANGED`.
- **Compare:** comparing the original with the fork gives `changed == ['C2','C3']`, one `source` block, and the left and right counts above. With `draft_minimum '0.70'` the right column is the same and the right method is `draft: true` with no id.
- **The original changes:**
  - Revise the original to `0.55` (revision 2).
  - The fork's `get` gives `parent_state 'PARENT_CHANGED'` and `parent_change == [{'field':'minimum','was':'0.50','now':'0.55'}]`.
  - The fork's check is unchanged: FAIL C1, C2, C3; PASS C4, C5; UNIT_MISSING C6.
  - The original at revision 1 still gives its original column.
  - The original at revision 2 gives FAIL C1, C2; PASS C3, C4, C5; UNIT_MISSING C6.
- **Tampering:** editing the fork's revision-1 `desk_history` payload makes its check refuse with `CLEARANCE_METHOD_HISTORY_DAMAGED`.

**Left out:**
- Following a changed original into a fork (rebase).
- Withdrawing a fork. The desk store has no delete, and a fork nobody pins changes nothing.

## 3. Pins: one project menu entry (same module)

**Operations:**
- **`tools.pin`** (execute): `{method, revision, label, origin?, id?, expected_revision?}`.
  - It takes `project` and `folder` from the method, and records `needs_columns`.
  - With `id` and `expected_revision` it points an existing pin at another revision, as a new revision of the pin. That makes moving it a single step, and moving back is the same step again.
- **`tools.pins`** (read): `{path?, project?}`.
  - For a path, it returns the pins whose folder contains the path.
  - Each pin carries `compatible` and `reason`, found by reading the header through `desk.sources.read`.
  - Each pin also carries `newer_revision` and `difference` (from `clearance.diff`) when the method has moved on.
- **`tools.unpin`** (execute): `{id, expected_revision}` sets state `UNPINNED`. A new pin revision is written and nothing is deleted.

**Naming.** The names avoid `*.remove`, `*.forget` and `*.clear`, which `stacy_hand.ALWAYS_ASKS` would treat as irreversible (`stacy_hand.py:50`). Unpinning can be undone by pinning again.

**Records written:** a `desk_records` row of kind `tool_pin` with these fields: `project`, `folder`, `label`, `operation 'clearance.check'`, `method {id, revision, digest, title}`, `needs_columns`, `state`, `origin` (`HUMAN` or `SLATE`, reusing `project_desk.ORIGIN`). Each change adds history and an event (`TOOL_PINNED` or `TOOL_UNPINNED`).

**Tests:**
- **Pin the fork at revision 1 with label `Check enclosure clearance`.** `tools.pins {path:'SLIM4/clearance.csv'}` then returns one pin with `compatible: true` and `newer_revision: None`.
  - `Other/clearance.csv` gives `[]`.
  - `SLIM4/gaps.csv` with columns `Ref,Gap` gives `compatible: false` with reason `The table has no column “Clearance”`.
- **Revise the fork to `0.75` (revision 2).**
  - `tools.pins` shows `newer_revision 2` and `difference [{'field':'minimum','was':'0.70','now':'0.75'}]`.
  - The pinned check still gives PASS for C4 and C5.
  - Revision 2 itself gives FAIL C1 to C5 (0.7112 is under 0.75) and UNIT_MISSING C6.
- **Unpin.** `tools.unpin` gives `state 'UNPINNED'`, `tools.pins` returns `[]`, and the history holds 2 revisions.

**Left out:**
- A Tools entry in the menu bar for each project (`menus2.py:275` stays a fixed list).
- Sharing pins between owners. `records.read` is per owner.
- Joining pins with staC words and the `~/Concern/Ledger menu` chains. This is a third store, said plainly.

## 4. Registration, registry, seed

**Files:**
- **`engineering_kernel.py`:** import beside `stac_words` (:58), add `**clearance_methods.SCOPES` beside :227, and add a route `if op in clearance_methods.FIELDS: return clearance_methods.dispatch(self, op, a, p)` beside :627.
- **`engineering_cli.py`:** import `FIELDS as CLEARANCE_FIELDS` beside :90 and add it to the merge beside :186.
- **`docs/GRAPHITE_0.1_REGISTRY.json`:** regenerate with `tools/record_registry.py`.
- **`stacy_foundation.SEED_FILES`:** add both new modules so her catalogue knows them. Then rebuild the seed with `tools/package_graphite.py --rebuild-seed`, and rebuild the manifest with `--manifest-only`, as recent commits have done.

**Tests:**
- All 11 operations are in `CAPABILITIES`, in `schemas()` and in the registry, each with the scope listed above.
- `test_machine.py` and `tools/check_release.py` pass.
- The existing test `test_stacy_hand.py::test_no_operation_the_program_has_that_leaves_the_computer_or_forgets_is_hers` still passes, and it now covers the 5 new non-read operations.

## 5. Kas produces the result: `clearance_qt.asked(face, text)`

**Hook:** one line in `shell2.SlateFace.ask` right after `own_word` (`shell2.py:2500`). Because it runs before `brain.status` is read, her request takes the same path with the model on or off.

**Rules:**
- **Explain request:** the text has `explain` and also `result`, `clearance` or `check`. This goes to piece 9.
- **Check request:** the text has `clearance` and a CSV (a `files:`/`@files:` path in the text, or `face.selected_file()`).
  - The candidate methods are `clearance.list {folder}` for folders that contain the CSV.
  - The longest method title found in the text wins.
  - Otherwise, if exactly one method has no parent, she uses it and names any other versions.
  - Otherwise she offers one word per method.
  - With no method she says so and does nothing.
- **What she runs:** `clearance.check` through `Kernel.dispatch` with `operator()`. It is a read, so it is hers at every dial place (`stacy_hand.hers` returns True for `read`). She never creates, forks or pins by herself.

**Tests** (`tests_integrated/test_clearance_talk.py`, the offscreen window with the holds from `test_context_menu.py`; `brain.status` patched to `NO_MODEL_SELECTED`; `brain.ask` patched to raise):
- `face.ask('check the clearances in SLIM4/clearance.csv')` makes one card. Its `card.check['call']` is `{'operation':'clearance.check','arguments':{'method':<original>,'revision':1,'source':'files:SLIM4/clearance.csv'}}`.
- The card text holds the line `C6 · 0.60 · — · Unit missing` and the line `4 pass · 1 fail · 1 unit missing`.
- No `brain.*` operation is dispatched.

## 6. Her card, the right-click on it, and Inspect at three levels

**Files and functions:**
- **`clearance_qt.result_card(face, result, intro, by)`.**
  - It builds a `Bubble` showing the table, the exact line made with `field_do.op('clearance.check', …)`, and the words `preview · open method · fork · run again · in the line`.
  - It stores `card.check = {call, result, by}`.
  - It does not offer save: a saved result without its record is left out, not offered half-done.
- **`clearance_qt.find_result(host, w, point)`.**
  - It walks from `w` up to a `Bubble` that has `check`, and returns `Target('result', …)`.
  - It returns None while the label has selected text, so the label's own Copy menu stays.
  - It has to start from the label because `owns_menu` stops at selectable labels (`context_menu.py:1708`), and her answer labels are selectable (`shell2.py:1889`, `:1921`).
- **`clearance_qt.result_entries(host, t)`**: the menu rows in the table below.
- **`context_menu.py`:**
  - add the finder to `FINDERS` (:1701) and the provider to `PROVIDERS` (:1442), both through thin wrappers that import inside, to avoid an import cycle;
  - add `NOUNS['result']`;
  - remove the printed key from `inspect_in_line` at :231.

| Row | What it does |
|---|---|
| Inspect | Opens the Inspect card |
| Preview | Side by side (piece 7) |
| Open method | Level (b) as a card |
| Fork… | The fork card (piece 7) |
| Run again | Same method revision, the source read now |
| In the line | Puts the exact line in the writing strip |
| Pin under Tools for SLIM4 | The owner pins directly; the confirmation offers Unpin |
| Ask her to explain this | Piece 9 |

**The Inspect card** uses the existing `program_detail` disclosure (`shell2.py:1679`):
- **(a) At a glance**, always shown:
  - `Input: SLIM4/clearance.csv · 6 rows · sha256 5a1262c7b9ac…`
  - `Gives: a verdict for each row: 4 pass, 1 fail, 1 unit missing`
  - `Saves: nothing. It only reads.`
  - `Model: none was asked.`
- **(b) "Open method"** (disclosure). It shows:
  - the columns: Ref, Clearance, Unit;
  - `Rule: a row passes when its clearance in mm is at least 0.50 mm`;
  - `Conversions: 1 in = 25.4 mm (exact); mm as written`;
  - `A row with no unit is not compared: Unit missing`;
  - the revision and its history, and the parent with its state.
- **(c) "The exact line and this run"** (disclosure). It shows:
  - the exact line, `/clearance.check {"method": "<id>", "revision": 1, "source": "files:SLIM4/clearance.csv"}`;
  - how Graphite called it: `Kernel.dispatch as the owner, scope read`;
  - `No program outside Graphite: workbench/clearance_methods.py sha256 …`;
  - the release and the seed state (read only when Inspect opens);
  - this run: bytes read once, rows, refusals, time taken (measured on the card, not in the Kernel), and the `account` lines.

**Tests:**
- `cm.target_at` on the card's answer label returns kind `result`. With text selected in the label it returns `None`.
- The entry keys are exactly `result:inspect, result:preview, result:method, result:fork, result:again, result:line, result:pin, result:explain`.
- Running Inspect gives the four glance lines verbatim, the two disclosure titles, and the method and line texts quoted above.
- **Run again:** write C3 as `0.71` with `files.write` and press "run again" on the fork's card. The new card says `SLIM4/clearance.csv changed since the last run`, and C3 now passes.

**Left out:**
- This right-click for her other cards (her other staC answers, StagedRun, PlanRun).
- Sorting failures into kinds (claim 7).

## 7. Fork with side by side; pin from the card; Kas proposes the pin

**The fork card** (`clearance_qt.fork_card(face, card)`):
- It has a name field, a minimum field, a side-by-side table that refreshes 250 ms after typing stops (through `clearance.compare … draft_minimum`), and a "Keep my version" button that dispatches `clearance.fork`.
- Nothing is kept until the button is pressed. This is the brief's "open the line behind her answer, change it, see the list change, name your version".

**Preview** on a fork's card runs `clearance.compare` against its parent's recorded revision. On an original's card it compares against its first fork, or says `There is no other version yet: fork it to see two side by side.`

**Kas proposes the pin.** After a fork is kept, she stages `Step('Pin “Enclosure clearance 0.70” under Tools for SLIM4', 'write', op('tools.pin', …, origin='SLATE'), why, 'execute')` through the existing `stage()` (`shell2.py:1948`) with `asked=False`. It waits for Approve on every dial place. `tools.pin` is on no list in `stacy_hand.py:39-43`, and the lists are not changed. The Approve tooltip's printed key ("in the Field, G does the same", `shell2.py:1977`) is removed in the slice.

**Tests:**
- Typing `0.70` in the fork card gives `changed == ['C2','C3']` and the footer `Same input: SLIM4/clearance.csv, read once for both · 2 rows change`. `clearance.list` still holds 1 method.
- "Keep my version" named `Enclosure clearance 0.70` gives 2 methods. The card says `Kept: “Enclosure clearance 0.70”, revision 1, from “Enclosure clearance” revision 1.`
- At `ask`, `show` and `free`, the staged pin card has `card.ran is None` with Approve visible, and `stacy_hand.hers(place,'execute','tools.pin')` is False. Approving it pins, with `origin 'SLATE'`.
- The owner's own pin from the right-click shows an Unpin word, and pressing it gives `tools.pins == []`.

## 8. The menu entry on a compatible table, run with the model off

**Function:** `clearance_qt.pinned_entries(host, t)`, a provider for `t.kind == 'table'` on the Files surface.
- It adds a `Tools for SLIM4` submenu in the `command` section. Its row `Check enclosure clearance` (caption `rev 1`) runs `clearance.check` and shows the result card with `by='owner'`, introduced as `You ran …`.
- An incompatible table gets the row greyed, with its reason.
- When a newer revision exists, a second row `What changed in rev 2` opens a difference card: `Your pin runs revision 1 … minimum 0.70 mm → 0.75 mm … stays on revision 1 until you pin revision 2`. It has a word to repin, with "back to revision 1" offered after.

**Tests:**
- Turn the model off: `brain.status` is patched to `NO_MODEL_SELECTED`, and `brain.ask` and `brain.stop` are recorded.
- Right-click `SLIM4/clearance.csv` in Files and run the pinned row. Rows: FAIL C1, C2, C3; PASS C4, C5; UNIT_MISSING C6. The only operations dispatched are `tools.pins` and `clearance.check` (and the `desk.sources.read` the check makes inside).
- **Same operation under the click and under her request.** `face.ask('check the clearances in SLIM4/clearance.csv with Enclosure clearance 0.70')` gives `card.check['call']` equal to the menu's, and an equal `result` (rows, source, method, conversion and implementation).

## 9. "Explain the result from your version"

**Function:** `clearance_qt.explain(face, card)`, reached from the card word, the right-click, or typed text. For "my/your version" or "fork" it picks the latest card whose method has a parent.
- **The facts it uses** come from `clearance.compare` against the parent:
  - `Your version “Enclosure clearance 0.70” (revision 1) is a fork of “Enclosure clearance” revision 1: the minimum went from 0.50 mm to 0.70 mm.`
  - `C2 and C3 pass the original and fail yours.`
  - `C5 is 0.028 in, which is 0.7112 mm exactly, so it passes both.`
  - `C6 has no unit, so neither version compared it.`
  - plus the input's sha and the row reasons.
- **Model off:** the card opens with `No model is loaded, so this is not in my own words.` and then gives those lines.
- **Model on:** the same facts and `RECORDS_HINT` go to `brain.ask`, following the grounded pattern at `shell2.py:2526-2539`: `face.job`, `grounded`, `In my words…`.

**Tests:**
- With the model off, the card text is exactly the first line and the four facts above.
- With `brain.status` patched to READY, the captured `brain.ask` message holds the four facts and `RECORDS_HINT`, and its row lines carry the fork's reasons (`0.50 mm is under 0.70 mm`). The card shows `In my words…`. The test stops `face.timer` so the fake job is never polled.

**Left out:** putting `clearance.check` in her fixed planner set (`local_brain.py:521`) or in `tool_selection`. She reaches it by rule only.

## 10. The fixture: `tools/clearance_fixture.py WORKSPACE`

It refuses if `SLIM4/clearance.csv` already exists. Otherwise, through `Kernel.dispatch` as the owner, it runs `files.write` (the CSV above), `projects.create` (SLIM4), `projects.link` (SOURCE, the CSV) and `clearance.create` (`Enclosure clearance`, 0.50 mm, Ref/Clearance/Unit, folder SLIM4). It prints each id.

**Left out:** a way to make a method in the interface. One operation line in the bar does the same.

---

## The experiment, step by step, as one test

`test_clearance_talk.py::test_the_experiment` runs these steps in order:
1. The fixture.
2. Her check, with the model off.
3. Inspect.
4. Fork to 0.70, with the side-by-side preview.
5. Keep the fork.
6. Pin it by approving her proposal.
7. The model stays off; run the pinned entry from Files.
8. The model is on (patched); explain from your version.

It also asserts that no displayed text or tooltip in any new card or menu row matches `Ctrl|Shift\+|Alt\+|Enter|Return|F10`.

**The owner's rules, as kept:**
- **Asks or on the list:** she only reads and proposes. The 5 changing operations are on no list, and `stacy_hand.py` is not changed.
- **Undo:** the pin has Unpin and repin back. A fork and a revision are append-only records, so they have no Undo, and this is said.
- **Nothing silent:** forks are full copies with a parent reference. Pins run their exact revision from history, and newer revisions are shown as a difference.
- **No printed keys:** two existing printed keys on this path are removed (`context_menu.py:231`, `shell2.py:1977`).

**Printed keys outside the slice, still to fix:** `shell2.py:2362`, `console_qt.py:467`, `context_menu.py:406`, `:1333`, `:1338`.

## Left out of the slice, together
- **Talk:** the right-click for her other cards, failure kinds, a stage index and partial rows (claim 7).
- **Methods:** persisted result records and saving with a record; rebasing or withdrawing forks; units beyond mm and in; other relations; inches in prose `quantities.py`; a method editor; the Field showing methods.
- **Menus and stores:** Tools entries in the menu bar for each project; joining pins, words and kept chains into one store.
- **Kas and the writing strip:** her planner choosing the check; making Enter and the arrow agree, and `explain WORD` in Talk (claim 5); word lineage and words outside the bar (claim 3); provenance carried through staC pipes (claim 4); correcting `GRAPHITE_DESK.md:482/486`.

---

## Claims in the brief that do not hold, said plainly

- **Claim 1 (Inspect: right-click a result and open the operation).**
  - Her Talk cards have no right-click of Graphite's own. No finder covers Talk.
  - There is no Preview, Open method or Fork anywhere.
  - A result she saves (`save_rows`) keeps no record of its source.
  - "Inspect" already means four different things.
- **Claim 2 (the same operation under the click and her request).**
  - Nothing ties her answer to the operation a click runs. Her fixed set has no `field.*`, and other operations are chosen by word matching.
  - The `field.*` operations came in 0.4.1, not 0.3 as cited.
  - staC refuses every line whenever the seed is stale, and any source edit makes it stale. It verifies at 34f00ba only because the seed was just rebuilt.
- **Claim 3 (staC words).**
  - **Where a word runs.** It expands only where a line is typed (the bar, Talk, "Your words"). It does not expand at the Kernel, the CLI, JSONL or in kept chains, and "Waits" with a capital letter is not expanded.
  - **`explain waits`.** It works only through the arrow. With Enter to her, it falls to the model; with no model the answer is "I have no brain running yet". Its echo is cut to 32 characters.
  - **"The full line is in history".** This holds only in part:
    - console history is per user, not per workspace;
    - the journal records `words.keep` without the line;
    - Talk is not saved.
  - **Replacing a word.** Keeping a word under an existing name silently replaces it, with no record of the old line.
  - **"Teach by doing".** The pieces exist apart but are not joined:
    - her card has no "keep as a word";
    - there is no live preview for words;
    - words and kept chains are separate stores;
    - a word has no parent or versions.
- **Claim 4 (provenance through the pipe).** None of it exists today. A staC result names no file hash, and values travel without units.
- **Claim 5 (the destination is visible when you press the key).**
  - The cues describe the arrow, while Enter goes to her. The two send answers to different places.
  - For a word, the list under the line never shows the staC section, while the context word says "runs as staC".
  - Nothing marks the key press itself.
  - `GRAPHITE_DESK.md:486` "plain Enter never runs staC" is false for her words and for `word`/`forget`. `:482` is out of date, and the document's four modes do not match the code's five.
- **Claim 6 (fork the rule).**
  - No clearance, limit or threshold operation exists.
  - No unit table has inches.
  - staC compares bare numbers: "0.028 in" counts as 0.028, a blank unit passes silently, and `where Unit=mm` drops rows.
  - No fork exists. A word is overwritten in place, so a change reaches every use silently.
  - The record of what a result depended on exists only in pieces.
- **Claim 7 (debug together).**
  - There are no failure kinds: every refusal comes back as `ValueError`.
  - Earlier steps' results are not shown.
  - staC errors carry no stage index.
  - Talk shows only `job.error` or the state.
  - Program rooms throw stderr away.
- **Claim 8 (a menu that grows from your work).**
  - There are no per-project tools. The menu file is one per user, and Tools and Programs are fixed lists.
  - No path exists for her to propose a menu entry and the owner to pin it.
  - A method change is never shown as a difference before the menu moves. Menu entries have no ids or revisions.
  - The citations exist but describe something else:
    - `STAGE5.md` procedures are owner-scoped, with no project, revision or parent, and are limited to 8 operations. Each use needs an assignment, working copies, a budget and a grant, so they are not menu commands.
    - `BOSS_IMPLEMENTATION_PLAN.md:176` (P14) is marked PLANNED only.
- **Claim 9 (the experiment).** It cannot be run on today's tree. There is no clearance method, fork, project menu or right-click on her Talk cards, and staC alone gives the wrong answer for C5 and C6.