{
 "report": "# Writing strip, staC words and Field keys: ground truth\n\nSnapshot: working tree of `/home/user/Struthio`, branch `claude/epic-galileo-c7k11y`, HEAD `164fe3c`, line numbers re-checked at 03:24 UTC on 2026-11-13. Nothing was edited, no test or app was run; two short pure-function snippets were run (parser/router behaviour, seed status).\n\n## 0. Three facts that change the plan\n\n1. **A Backspace \"back\" key already exists, uncommitted.** `/home/user/Struthio/workbench/field_qt.py`: state at :72 (`self._trail = [];self._last = ''`), recording in `_describe` :98-103, the key at :241-247, legend entry `(12, '\u232b  where I was')` at :679. HEAD does not have it (`git diff` shows these lines as added). **B is also taken** in the working tree (brief, :248-249).\n2. **The tree is being written by another session while I read.** `workbench/field_model.py` (mtime 03:19) and `workbench/datasheet_work.py` (03:18) became modified between two `git status` calls; `field_qt.py` 03:12, `field_page.py` and `shell2.py` 03:15. Uncommitted now: MANIFEST.json, docs/GRAPHITE_0.1_REGISTRY.json, project/stacy_seed/current/*, workbench/{activity,datasheet_work,documents,field_do,field_doubt,field_model,field_page,field_qt,field_service,field_source,shell2}.py, plus untracked workbench/field_brief.py and field_ripple.py.\n3. **The staC seed was STALE when checked (03:21).** `stacy_foundation.seed_status('.')` returned `STALE ['workbench/datasheet_work.py']`. By code, `language.run` then refuses every line with `Graphite seed/source binding is not current` (`/home/user/Struthio/workbench/stacy_language.py:9-13`, called at :53-54). Seed inputs (editing any makes it STALE until `tools/package_graphite.py --rebuild-seed`): typebar_qt.py, shell2.py, stac_bridge.py, stacy_language.py, console_qt.py, chain_menu.py, session.py, agenda.py, activity.py, engineering_kernel.py, engineering_cli.py, helpers.py, project_desk.py, sdk/cli/arc1cli/typed_pipeline.py, README.md, docs/DAILY_GUIDE.md. **Not** seed inputs: every field_*.py, context_menu.py, version.py.\n\n## 1. Path of a typed line\n\nWiring: `install` `/home/user/Struthio/workbench/typebar_qt.py:609`; `box.textChanged \u2192 TypeBar.typed` :212, :270; send button \u2192 `submit_line` :184, :311-315 (emits `box.returnPressed`). The box is `OneBox`, `/home/user/Struthio/workbench/shell2.py:804`.\n\n**Ctrl+Enter (the only key that runs typed staC)**\n1. `OneBox.keyPressEvent` shell2.py:852-856 \u2192 `bar.ctrl_enter()`.\n2. `TypeBar.ctrl_enter` typebar_qt.py:274-301: strip; log mode :281-286; not Assistant \u2192 False :287; `expand_this` :289-293; page = `box.console_page(text)` :295-296 (`'stac'` unless kernel/find/shell); `to_console(self.host, page, text)` :299.\n3. `to_console` shell2.py:988-998 \u2192 sets `console.prompt`, calls `console.enter()`.\n4. `Console.enter` `/home/user/Struthio/workbench/console_qt.py:375-382` \u2192 `remember(text)` :339-344 (history in `host.session.state['console']['history']`) \u2192 `run_stac`.\n5. `Console.run_stac` console_qt.py:453-475: `route_program(text, allow_inspection=True)` :454 \u2192 `call_write` :462 (shell2.py:2189) \u2192 `Kernel.dispatch`. Refusal printed `refused <message>` :463. Rows get the links `save as a sheet \u00b7 watch it \u00b7 add to the Agenda \u00b7 again` :472-473.\n6. `route_program` `/home/user/Struthio/workbench/stac_bridge.py:22-30` (the start-word lookup, below).\n7. `language.run`: `Kernel.dispatch` `/home/user/Struthio/workbench/engineering_kernel.py:485-545`, route :604 \u2192 `stacy_language.dispatch` stacy_language.py:107-113 \u2192 `_compile_plan` :46-57 (`source()` :38-44 rewrites a leading `@address`; `typed_pipeline.parse`; `validate_read_call` :60-71; seed check) \u2192 `_execute_plan` :116-127 (inner `kernel.dispatch` :118, `typed_pipeline.apply`, limit 200 rows :112). `stac.run`: route :601 \u2192 `stac_bridge.dispatch` :163 \u2192 `run` :113 \u2192 `compile_program` :64-112.\n\n**Enter in Assistant mode never runs staC.** shell2.py:873 \u2192 `returnPressed` \u2192 `ResultsPopup.activate_current` :1069-1075 \u2192 first actionable row of `OneBox.results` :898-935, which is `('ask', 'Ask staC \u00b7 \u2026', ('Enter', lambda:self.host.shell2.ask(text)))` :917 \u2192 `Shell2.ask` :2778 \u2192 `SlateFace.ask` :1838. A `/` line: row :911 \u2192 `Console.run_kernel` console_qt.py:478-507 (`name=value` or `{json}`, `parse_command` :67-81).\n\n**Hint while typing.** `TypeBar.typed` \u2192 `refresh_context` typebar_qt.py:511-537: `expand_this` :518-521, then `stac_hint_kind` :120-139; words `{'stac': 'staC on Ctrl+Enter', 'inspect': 'Preview on Ctrl+Enter'}` :523. Popup under the line: `OneBox.update_results` shell2.py:875 \u2192 `results`, which calls `parses_as_stac(text)` on the raw text :913.\n\n**Start-word table.** stac_bridge.py:18-19, exactly:\n```\nSTART_WORDS = ('library', 'desk', 'package', 'map', 'source', 'packet', 'investigation',\n               'inquiries', 'inquiry', 'algorithms', 'atlas', 'math', 'use')\n```\nLooked up at :28 as `first[0].lower() in START_WORDS` (`first = program.split(maxsplit=1)`); a hit routes to `('stac.run', {'program': program})`, else `('language.run', {'text': program})`. `explain` is taken at :26-27 only with `allow_inspection`. It is a module-level tuple with no register function. It is referenced only at :18 and :28, and `route_program` reads the global per call, so rebinding the attribute would be seen (inferred, not executed). But a start word only selects `stac.run`: its meaning is the hard-coded if-chain in `compile_program` :67-103, and anything unmatched is compiled as upstream staC (:104-112, where `use` goes).\n\nOther first-word tables: three op aliases inside `parse`, `/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py:46` `{'jobs':'jobs.list','models':'brain.models','activity':'ledger.journal.read'}` (a literal in the function); lead characters `JUMPS` typebar_qt.py:26 and shell2.py:835, :858-862. Typing \"field\" is not a start word: it matches the `Field` QAction (`/home/user/Struthio/workbench/menus2.py:186-189`) through `OneBox.commands` shell2.py:973-985.\n\n`route_program` callers: console_qt.py:454; shell2.py:2086; typebar_qt.py:130; `/home/user/Struthio/workbench/field_do.py:50-51`; office_building_qt.py:376; stac_bridge.py:131; investigations.py:34 as `run_with` (used by `/home/user/Struthio/workbench/agenda.py:317-319`).\n\n## 2. Where `this` is expanded\n\n`/home/user/Struthio/workbench/field_page.py:284` `THIS = re.compile(r'^(explain\\s+)?this\\b\\s*(\\|.*)?$', re.IGNORECASE | re.DOTALL)`; `expand_this(host, text)` :287-298. No match \u2192 text unchanged. Nothing selected or empty `obj.stac` \u2192 `ValueError('\u201cthis\u201d is the sheet selected in the Field (F9), and nothing is selected there')`. Alone \u2192 `obj.stac`; before a pipe \u2192 `obj.stac.split(' | ', 1)[0] + ' ' + rest`; an `explain ` lead is kept. `this {json}` does not match.\n\nExactly three callers:\n\n| # | Location | Function | On ValueError |\n|---|---|---|---|\n| 1 | typebar_qt.py:289-293 | `TypeBar.ctrl_enter` | `self.note(str(exc))`, returns True |\n| 2 | typebar_qt.py:518-521 | `TypeBar.refresh_context` (the hint) | swallowed |\n| 3 | shell2.py:1005-1009 | module function `preview_rows` (:1001) | PREVIEW note row |\n\nThere is no `SlateFace.preview_rows`. `preview_rows` is module-level, its only caller is `OneBox.results` shell2.py:915 under `preview and text.startswith('@')`; `THIS` cannot match text starting with `@`, so caller 3 never expands anything today.\n\nPlaces a line runs or is judged **without** `expand_this` (these would be missed):\n- Enter: shell2.py:917 \u2192 `SlateFace.ask`. Stacy handles \"this\" separately via `POINTING` :1514 and `thing_asked_about` :1613-1624, only while `_field_active`, and she answers with the sheet's own `thing['stac']`, not the typed pipeline.\n- Popup: `parses_as_stac(text)` raw, shell2.py:913. For `this | count` the popup omits \"STAC \u00b7 CTRL+ENTER RUNS IT\" while the context word says \"staC on Ctrl+Enter\".\n- `Console.run_stac` console_qt.py:453 when reached other than via `ctrl_enter`: `context_menu.run_stac` (`/home/user/Struthio/workbench/context_menu.py:234-248`), `chain_menu.then` (`/home/user/Struthio/workbench/chain_menu.py:269-274`), the `again` link console_qt.py:473.\n- `SlateFace.run_stac` shell2.py:2085; `field_do.call` field_do.py:44-51 (used at shell2.py:1634, :1712, :1783); Agenda runner agenda.py:317-319; `/stac` and `/pipe` in `/home/user/Struthio/workbench/stacy_control.py:40-42`; office_building_qt.py:376; `watch` / `keep_in_agenda` store the line as given, shell2.py:2120, :2174.\n- The Kernel: `this` is not known there. `typed_pipeline.parse('this | count')` yields operation `this`, which `validate_read_call` refuses.\n- History stores the expanded text (expansion happens before `to_console`).\n\nSingle funnels if wanted: `Console.run_stac` (everything the working area runs), `route_program` (every runner), `stacy_language.source()` (kernel-side first-stage rewrite, also used by the hint typebar_qt.py:127-128 and the chain menus chain_menu.py:447, context_menu.py:1165).\n\n## 3. staC grammar as implemented\n\nAll in `/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py`.\n- `split` :14-26: 1..8192 chars; any of `` ` `` `$(` `${` `;` `>` `<` newline, CR, NUL \u2192 `Shell syntax and command substitution are not part of Stacy language`; splits on `|` outside double quotes; at most 8 stages (`Use one source and at most seven transforms`).\n- First stage :45-48: `op,_,argument = stages[0].partition(' ')`; alias dict; op must fullmatch `[a-z][a-z0-9_.]{0,100}` else `Expected a registered operation name`; argument empty \u2192 `{}`, else `json.loads` that must give an object (`_arguments` :28-41). So `op` or `op {json}`; `name=value` is only for `/` lines.\n- Verbs :50-105: `take N` (1-200); `keep rows i,j`; `select a,b` (1-16); `where f=v`, `f!=v`, `f over|under|at least|at most|has|is not v`; lenses `sheet NAME`, `rows`, `facts`, `layers`, `lines`, `headings`, `texts` (LENSES :12) and `pick PATH`; `sort [-]f`; `count`; `group f1..f4`; `sum|avg|min|max f`; `add NAME = expr`; `join|missing @address [lens] on FIELD`. Anything else: `Unknown transform; use where, take, \u2026` :105.\n- Plan shape :106: `{'schema':'arc.stacy-action-plan/1','language_version':1,'call':{'operation':op,'arguments':args},'transforms':transforms,'text':source}`; stacy_language.py:55-56 adds `principal`, `seed_id`, `permission`, `plan_id`.\n- Result (stacy_language.py:126-127): `{'schema':'arc.stacy-pipeline-result/1','plan':plan,'rows':[\u2026],'execution':'REGISTERED_READ_ONLY_KERNEL_CALL','model_calls':0}`.\n\nUnknown op. Confirmed by snippet: `waiting` and `nosuch.op {} | count` parse (parse does not check registration); `Waiting` \u2192 `Expected a registered operation name`; `my word` \u2192 JSONDecodeError `Expecting value: line 1 column 1 (char 0)`. Registration is checked in `validate_read_call` stacy_language.py:66-67: unregistered, not `read`, `language.*` or `stac.inspect` \u2192 `A pipeline source must be a registered read-only Kernel operation`; wrong arguments \u2192 `Unknown or missing pipeline source arguments` :70. The Kernel wraps it as `{\"schema\": \"arc-ledger.kernel/1\", \"ok\": False, \"error\": {\"code\": \"ValueError\", \"message\": \u2026}}` (engineering_kernel.py:538-542). The hint for such a line is None (typebar_qt.py:134-139).\n\nExisting saved/named notions:\n- **Kept chains** (the only named saved staC line): plain text file `locations.concern_home() / 'Ledger menu'` (chain_menu.py:39, :331-333; `/home/user/Struthio/workbench/locations.py:48-49`, i.e. `~/Concern/Ledger menu` or `$ARC_LEDGER_CONCERN`). Line format `[chain] (Name) {staC pipeline} then console|sheet|watch|agenda` (regex :40, template :353-360). Written by `keep()` :336-350 (QInputDialog, append), read by `parse_menu` :363-391 into `('chain', name, program, then)`, offered at chain_menu.py:146 and as \"Your chains\" context_menu.py:1148-1173, :1207. Per home, not per workspace; no Kernel, no journal; names free text and not unique; validated with `typed_pipeline.parse(source(program)[0])`, so start-word programs show as not parsing.\n- \"WORKED BEFORE\" from the instruction matrix shell2.py:919-925 \u2192 `use_program` :892-896 (unnamed).\n- `procedures.*` (`/home/user/Struthio/workbench/continuing_work.py:51-55`, scopes :57-58): `procedures.save {work, title, parameters}` is `approve` and takes only an owner-ACCEPTED continuing-work order (:630). Stored record :645-648: `{'schema':'arc.stac-procedure/1','id','owner','title','source_work','source_order_digest','steps','parameters','operations','effects','copy_slots','assignment','created','authority':'TEMPLATE_ONLY_NEW_INSTANCE_REQUIRES_NEW_GRANT'}`; `procedures.instantiate` needs assignment, copies, budget, expires. Too heavy for one read-only line.\n- Method Press (`/home/user/Struthio/workbench/sheet_workbench_qt.py:613-631`) keeps `[stock]` lines in the same menu file. `methods.*` (checked_methods.py:21-33) and `matrix.promote` (instruction_matrix.py:253-264) are not runnable aliases.\n\n## 4. Where name \u2192 line pairs could live\n\nWorkspace store is `<root>/.ledger/engineering.sqlite3` (engineering_kernel.py:340-344). Nothing existing gives name \u2192 line, per workspace, through the Kernel.\n\n| Candidate | Declared | Journaled | Why it does not fit |\n|---|---|---|---|\n| `agenda.add` | agenda.py:48-50 `{'title' \u2264400, 'program' \u22648192, 'investigation','nice','when','rounds','watch','copy'}`, required `['title']`; scope `execute` :64; returns the row (`COLUMNS` :194-195 plus `origin_words`) | yes (not in OBSERVER_OPERATIONS; `agenda.view` is) | a queue: state NEXT, run by `run_next`, ends DONE; no name lookup |\n| Ledger menu file | chain_menu.py:336-391 | no | per home, Qt dialog, not unique |\n| `stacy_memory` | `/home/user/Struthio/workbench/memory_service.py:40-58` | own events | `KINDS` closed (`MEMORY_KIND`), no public op; caps 4000 records/owner, 128 KiB each |\n| Kernel `settings` table | engineering_kernel.py:354 | \u2014 | only behind typed setting specs (`/home/user/Struthio/workbench/settings_registry.py:11-30`, 49 recorded) |\n| `Session.state` | `/home/user/Struthio/workbench/session.py:82`, load whitelist :95-252 | no | profile file `~/.config/arc1-workbench/session-r10.json`; unknown keys dropped on load |\n\nNatural home for two tiny operations: the storage pattern is `/home/user/Struthio/workbench/helpers.py` (a name-unique-per-owner record in the versioned desk store; `NAME = re.compile(r'[a-z][a-z0-9_]{0,63}')` :36, `_by_name` :90, `records.new/write/edit` at `/home/user/Struthio/workbench/project_desk.py:121-145`, tables :86-90 with history and `desk_events`). For the operations, two already-wired modules need no kernel/cli edit because both are routed by FIELDS membership:\n- `/home/user/Struthio/workbench/field_service.py` (not a seed input): `WRITES` :47 makes an op `execute`, everything else `read` :48.\n- `stacy_language.py` (seed input): `SCOPES` :7 makes everything `read`, and `dispatch` :107-108 compiles `args['text']` first, so it would need a branch.\n\nHow an operation is registered, with field_service as the example:\n1. Module: `FIELDS = {op: (properties, required)}` field_service.py:38-46; `SCOPES` :48; `dispatch(kernel, operation, args, principal)` :156-166.\n2. `/home/user/Struthio/workbench/engineering_kernel.py`: import :57; `**field_service.SCOPES,` in `CAPABILITIES` :225; route :624 `if op in field_service.FIELDS:return field_service.dispatch(self,op,a,p)`.\n3. `/home/user/Struthio/workbench/engineering_cli.py`: `from .field_service import FIELDS as FIELD_FIELDS` :89; `**FIELD_FIELDS,` :184; each becomes `{\"type\":\"object\",\"properties\":\u2026,\"required\":\u2026,\"additionalProperties\":False}` :298-303. `doctor.inventory` raises if schemas and CAPABILITIES differ (`/home/user/Struthio/workbench/doctor.py:33`).\n4. Unjournaled reads: the hand-kept frozenset `/home/user/Struthio/workbench/activity.py:8-33` (field ops at :33). `field_service.OBSERVERS` :49 is not read by anything. Effect: engineering_kernel.py:392 and :510-511; failures are always audited.\n5. Record: `/home/user/Struthio/docs/GRAPHITE_0.1_REGISTRY.json` written by `/home/user/Struthio/tools/record_registry.py` (snapshot :44-65); entry shape `\"field.trace\": {\"arguments\": \"<sha256>\", \"properties\": {\"id\": \"52ba84a4bbf396ba\"}, \"scope\": \"read\"}` plus adapter `\"workbench/field_service.py#dispatch\"` (from `handler_map`, `/home/user/Struthio/workbench/stacy_foundation.py:285-310`). Counts now: 767 operations, 767 adapters, 113 job tools, 49 settings.\n6. Optional Timeline words: `/home/user/Struthio/workbench/tail_words.py:3-14`.\n\nName collisions to respect: START_WORDS, the three aliases, `this`, `explain`, the verbs, and the one single-word operation `capabilities` (the only undotted key of 767).\n\n## 5. Field keys\n\n`FieldView.keyPressEvent`, field_qt.py:215-277. `plain` (:216) excludes Ctrl/Alt/Meta only, so Shift+letter also matches.\n\n| Key | Lines | Effect |\n|---|---|---|\n| \u2190 \u2192 \u2191 \u2193 | 217-218 | `field.move` (field_model.py:241) |\n| Home / End | 219 / 220 | `select(first())` / `select(last())` |\n| PageDown / PageUp | 221-223 | scroll 85%; no selection change |\n| A, Shift+A | 224-225 | `next_attention` (field_model.py:265) |\n| Enter | 226-231 | `opened` \u2192 `open_object` (field_page.py:38, :461); Shift+Enter \u2192 `stac_run` (:43, :429) |\n| S | 232-234 | `stac_line` \u2192 `stac_in_line` (:42, :422) |\n| Esc | 235-240 | closes steps/go, then clears a what-if, then `left` \u2192 `back` (:39, :168) |\n| Backspace | 241-247 | back along `_trail` (uncommitted) |\n| B | 248-249 | `brief_asked` \u2192 `brief` (:50, :328) (uncommitted) |\n| D | 250-252 | `do_asked` \u2192 `do` (:44, :224) |\n| 1-9 | 253-255 | only while `self.steps`: `step_chosen` \u2192 `take` (:45, :240) |\n| X | 256-258 | `doubt_asked` \u2192 `doubt` (:49, :314) |\n| T | 259-261 | `trace_asked` \u2192 `trace` (:48, :301) |\n| G | 262-264 | `go_asked` if `self.go` (:47, :215); swallowed otherwise |\n| C | 265-266 | `check_asked` \u2192 `check_desk` (:46, :385) |\n| F | 267-269 | `full_asked` if kind `app` (:51, :370); swallowed otherwise, on every face |\n| R | 270-271 | `look_again` \u2192 `refresh(force=True)` (:41) |\n| W / P / N | 272-273 | face switch, **handled here**, data-driven: `event.text().lower()` against `self.faces` (`FACES` field_page.py:25, set :55) \u2192 `show_face` (:40, :75); checked last |\n| other | 274-275 | `super().keyPressEvent` |\n\nAsked specifically: **B taken** (uncommitted), **K free**, **M free**, **N/P/W faces** (in this handler), **L free**, **H free**, **Backspace taken** (uncommitted), **Tab not handled** (no override; comment :224 \"Tab leaves, as everywhere\"), **brackets free**. Free letters: E H I J K L M O Q U V Y Z. Also free: Space, Delete, Insert, 0, punctuation; 1-9 when no steps show.\n\nOutside the handler: F9 window action menus2.py:186-189; Menu and Shift+F10 context_menu.py:2119-2122 \u2192 `selected_point` field_qt.py:188. The main window has no `keyPressEvent`. Legend: field_qt.py:678-680 (highest number dropped first :695-696). Field menu entries: `field_entries` context_menu.py:1227-1293, `Entry(key, label, section, run, icon=, caption=<key>, tip=)` (class :106-117); it has no entry for brief or for going back.\n\n## 6. Selection history\n\n- **Funnel:** every change ends in `FieldView._describe()` field_qt.py:98-115 (clears `steps`/`go`, records the trail, emits `selection_changed`, which nothing connects to). Callers: keys :276-277; mouse :293-294, :299-300; `set_field` :93; context_menu.py:1236, :1543; field_page.py:280, :348, :398, :412. Model-level setters: `Field.select` field_model.py:216, `move` :241, `next_attention` :265, default in `__post_init__` :122-123. A new `Field` is built on every reading, so history cannot live in the model.\n- **Kept today (working tree only):** `_trail` (max 40, :102) and `_last`. `_describe` appends `_last` when the selection differs and is not already the trail's top. Backspace pops until an id that exists and is not current, sets `_last = ''` so going back leaves no trail; there is no forward. In memory only; `FieldPage` is created once (field_page.py:139-141), so it survives Esc/F9 but not a restart.\n- **Re-read (R, or the Field shown again):** `refresh` field_page.py:81-109 \u2192 `set_field` field_qt.py:83-93 keeps the selected id if still present (no trail entry); otherwise scroll resets and the new Field picks `first()` (field_model.py:207-214) and the vanished id goes on the trail. F9 while already in front reads nothing (field_page.py:133-134).\n- **Face change:** `show_face` field_page.py:75-79 sets `self.view.field.selected = ''`, then `refresh(force=True)`: scroll to 0,0, selection is the new face's `first()`. No per-face selection is remembered. The old face's id goes on the trail; Backspace on the new face pops and **discards** every id not on this face (:242-247), so W \u2192 P \u2192 Backspace empties the trail.\n- Esc \"back\" is a different thing: where the keyboard was before the Field (`host._field_focus`, field_page.py:143, :168-183).",
 "key_locations": [
  {
   "what": "TypeBar.ctrl_enter: Ctrl+Enter path, expand_this caller 1 (lines 289-293), hands the line to to_console at 299",
   "file": "/home/user/Struthio/workbench/typebar_qt.py",
   "line": 274
  },
  {
   "what": "TypeBar.refresh_context: the hint; expand_this caller 2 (lines 518-521) then stac_hint_kind",
   "file": "/home/user/Struthio/workbench/typebar_qt.py",
   "line": 511
  },
  {
   "what": "stac_hint_kind / parses_as_stac: local classification of a typed line (returns None for an unknown op)",
   "file": "/home/user/Struthio/workbench/typebar_qt.py",
   "line": 120
  },
  {
   "what": "THIS regex and expand_this(host, text)",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 284
  },
  {
   "what": "preview_rows (module function): expand_this caller 3 at 1005-1009; unreachable for 'this' because its only call site requires text to start with '@'",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1001
  },
  {
   "what": "OneBox.results: popup rows; parses_as_stac on raw text at 913 (no expansion), Enter row 'Ask staC' at 917, existing 'keep' row kind at 918, WORKED BEFORE rows 919-925",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 898
  },
  {
   "what": "OneBox.keyPressEvent: Ctrl+Enter to bar.ctrl_enter (855-856), lead characters (858-862), plain Enter falls to returnPressed",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 852
  },
  {
   "what": "to_console: hands a typed line to the console page and runs it",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 988
  },
  {
   "what": "SlateFace.ask: the Enter path; 'this' handled by POINTING (1514) and thing_asked_about (1613), not expand_this",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1838
  },
  {
   "what": "SlateFace.answer_in_stac: runs a line via field_do.call; action words line/watch/keep/save at 1668-1671",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1626
  },
  {
   "what": "SlateFace.watch (2120) and keep_in_agenda (2174): the existing ways a line is stored, both via agenda.add",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 2120
  },
  {
   "what": "Console.run_stac: single funnel for staC run in the working area; route_program at 454, refusal at 463, result links at 472-473",
   "file": "/home/user/Struthio/workbench/console_qt.py",
   "line": 453
  },
  {
   "what": "Console.complete and STAC_VERBS (line 44): Tab completion of verbs, ops and @addresses",
   "file": "/home/user/Struthio/workbench/console_qt.py",
   "line": 346
  },
  {
   "what": "START_WORDS tuple (18-19) and route_program (22-30): the start-word lookup at line 28, explain at 26-27",
   "file": "/home/user/Struthio/workbench/stac_bridge.py",
   "line": 18
  },
  {
   "what": "compile_program: hard-coded if-chain that gives each start word its meaning; fallthrough to upstream staC at 104-112",
   "file": "/home/user/Struthio/workbench/stac_bridge.py",
   "line": 64
  },
  {
   "what": "typed_pipeline.parse: first stage op + JSON, the three-alias dict at line 46, stage verbs 50-105, plan shape at 106",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py",
   "line": 44
  },
  {
   "what": "typed_pipeline.split: length bound, forbidden shell characters, at most 8 stages",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py",
   "line": 14
  },
  {
   "what": "stacy_language.source: kernel-side first-stage rewrite of '@address' (the closest existing analogue of a word expansion)",
   "file": "/home/user/Struthio/workbench/stacy_language.py",
   "line": 38
  },
  {
   "what": "validate_read_call: error for an unknown or non-read op ('A pipeline source must be a registered read-only Kernel operation')",
   "file": "/home/user/Struthio/workbench/stacy_language.py",
   "line": 60
  },
  {
   "what": "_verified_seed_id: language.run refuses when the seed is not VERIFIED_SOURCE_BINDINGS",
   "file": "/home/user/Struthio/workbench/stacy_language.py",
   "line": 9
  },
  {
   "what": "field_service FIELDS (38-46), WRITES (47), SCOPES (48), OBSERVERS (49, unused), dispatch (156): the wiring example",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 38
  },
  {
   "what": "CAPABILITIES includes **field_service.SCOPES (import at line 57, route at line 624)",
   "file": "/home/user/Struthio/workbench/engineering_kernel.py",
   "line": 225
  },
  {
   "what": "Kernel.dispatch: validation, journaling of non-observer ops (510-511), reply shapes (526-527, 538-542)",
   "file": "/home/user/Struthio/workbench/engineering_kernel.py",
   "line": 485
  },
  {
   "what": "schemas(): FIELD_FIELDS import at 89, merged at 184, schema object built at 298-303",
   "file": "/home/user/Struthio/workbench/engineering_cli.py",
   "line": 89
  },
  {
   "what": "OBSERVER_OPERATIONS: hand-kept frozenset of unjournaled reads; field.* at line 33",
   "file": "/home/user/Struthio/workbench/activity.py",
   "line": 8
  },
  {
   "what": "record_registry snapshot(): what the registry record holds per operation and adapter",
   "file": "/home/user/Struthio/tools/record_registry.py",
   "line": 44
  },
  {
   "what": "handler_map: how an operation's adapter (module#dispatch) is discovered for the record",
   "file": "/home/user/Struthio/workbench/stacy_foundation.py",
   "line": 285
  },
  {
   "what": "agenda FIELDS (agenda.add at 48-50), SCOPES at 64, add() at 198: the only Kernel op that stores title + staC program",
   "file": "/home/user/Struthio/workbench/agenda.py",
   "line": 46
  },
  {
   "what": "Kept chains: keep() writes '[chain] (Name) {staC} then \u2026' to ~/Concern/Ledger menu; LINE regex at 40, parse_menu at 363, menu_path at 331",
   "file": "/home/user/Struthio/workbench/chain_menu.py",
   "line": 336
  },
  {
   "what": "helpers.py: pattern for a name-unique-per-owner record in the versioned desk store (NAME regex 36, _by_name 90, ensure_helper 106)",
   "file": "/home/user/Struthio/workbench/helpers.py",
   "line": 106
  },
  {
   "what": "Project Desk record store: write/new/edit and desk_records tables (86-90)",
   "file": "/home/user/Struthio/workbench/project_desk.py",
   "line": 121
  },
  {
   "what": "procedures.* FIELDS (51-55) and the stored arc.stac-procedure/1 record (645-648): too heavy for one line",
   "file": "/home/user/Struthio/workbench/continuing_work.py",
   "line": 51
  },
  {
   "what": "FieldView.keyPressEvent: every key (215-277); Backspace at 241-247 and B at 248-249 are uncommitted; face letters at 272-273",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 215
  },
  {
   "what": "FieldView._describe: the single funnel for selection changes; trail recording at 100-103",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 98
  },
  {
   "what": "FieldView.set_field: what a re-read does to the selection",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 83
  },
  {
   "what": "_trail / _last state (uncommitted working-tree change)",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 72
  },
  {
   "what": "Foot legend of keys, including '\u232b  where I was' at 679",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 678
  },
  {
   "what": "FACES and FieldPage signal wiring (38-51); show_face at 75-79 clears the selection on a face change",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 25
  },
  {
   "what": "Field.select (216), move (241), next_attention (265), first (207), default selection in __post_init__ (122-123)",
   "file": "/home/user/Struthio/workbench/field_model.py",
   "line": 216
  },
  {
   "what": "field_entries: how Field context-menu entries are declared (Entry class at 106); no entry for brief or back",
   "file": "/home/user/Struthio/workbench/context_menu.py",
   "line": 1227
  },
  {
   "what": "context_menu.run_stac and inspect_in_line (221): lines put in or run from menus without expand_this",
   "file": "/home/user/Struthio/workbench/context_menu.py",
   "line": 234
  },
  {
   "what": "Session: profile-level state file with a load whitelist; console history kept here",
   "file": "/home/user/Struthio/workbench/session.py",
   "line": 95
  }
 ],
 "gaps": [
  "The working tree is being modified by another session while this map was made (field_model.py and datasheet_work.py changed between two git status calls; field_qt.py, field_page.py, shell2.py modified minutes earlier). Line numbers were re-checked at 03:24 UTC but can move again.",
  "The Backspace back-trail (field_qt.py:72, 98-103, 241-247, 679) and the B brief key exist only as uncommitted working-tree changes. I could not determine who wrote them or whether they will be kept; HEAD 164fe3c has neither.",
  "Seed state was STALE (workbench/datasheet_work.py) when checked at 03:21 via seed_status(). That language.run therefore refuses is read from the code (stacy_language.py:9-13, 53-54), not observed by running a line; the other session may rebuild the seed.",
  "No existing store gives name -> staC line pairs that are per workspace, survive restart and go through the Kernel. The only named saved staC lines are the kept chains in ~/Concern/Ledger menu (per home, no Kernel, no journal, names not unique).",
  "A plain file in Files via files.write/files.get was not evaluated as a store; files_service.py was only skimmed (FIELDS lines 44-71), so its limits and versioning are not stated.",
  "Not determined: whether tools/check_release.py or any other check compares the seed catalog's per-operation records with CAPABILITIES, or what it checks beyond the registry record. tools/record_registry.py --check was not run, so whether the currently modified registry record matches the live tree is unknown.",
  "No test in tests_integrated/ or tools/ references FieldView, field_model, field_service or expand_this (grep), so nothing pins current Field or 'this' behaviour. Only tests_integrated/test_writing_line.py:61-65 pins parses_as_stac.",
  "Tab in the Field is inferred from the absence of an event()/focusNextPrevChild override and the comment at field_qt.py:224; not observed at runtime. Likewise that no application-level shortcut takes a bare letter before FieldView is from grep only (the one dynamic case found is document_qt.py:254, scoped to a document page).",
  "That rebinding stac_bridge.START_WORDS at run time would take effect is inferred from the code (read per call at line 28, referenced nowhere else); not executed.",
  "That expand_this inside preview_rows never fires is inferred from its single call site (shell2.py:915 requires text.startswith('@')) and the THIS regex; not observed.",
  "There is no existing naming rule for staC words. Nearest patterns: helpers.NAME [a-z][a-z0-9_]{0,63} and the op pattern [a-z][a-z0-9_.]{0,100}. A lowercase single word that is not an operation already parses as a pipeline source and is refused only at validate_read_call.",
  "Enter in Assistant mode gives the line to Stacy (model or records path) and has no interception point for a typed word other than OneBox.results rows and SlateFace.ask; how a bare named word should behave on Enter is undecided by anything in the code.",
  "docs/DAILY_GUIDE.md, README.md and workbench/version.py do not mention Backspace or the brief key; whether the other session intends to document them was not determinable."
 ]
}