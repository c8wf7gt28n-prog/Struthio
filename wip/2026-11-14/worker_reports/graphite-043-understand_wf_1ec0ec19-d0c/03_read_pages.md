{
 "report": "# Ground map for \"the brief\" (a page written from the records)\n\nPaths are relative to `/home/user/Struthio`. Nothing was edited, no test was run, the app was not started. One pure snippet was run (noted in section 5).\n\n## 0. Read this first: the brief is already in the working tree, uncommitted, and still being edited\n\n- HEAD is `164fe3c` (\"Graphite 0.4.2: a doubt's reason is shown whole in Talk\", 02:56 UTC). HEAD has **no** brief.\n- The working tree has uncommitted changes in 11 `workbench/` files plus two untracked files, `workbench/field_brief.py` and `workbench/field_ripple.py`. Together they already implement a brief end to end.\n- Files changed **while I was reading**: `field_brief.py` (03:14 then 03:16), `field_do.py` / `field_model.py` / `field_source.py` (03:19), `field_doubt.py` (again between 03:22 and 03:24). Something else is writing this tree.\n- Line numbers below are the working tree at 03:22\u201303:24 UTC. `field_doubt.py` numbers are approximate; use the function names.\n\nWhat the working tree already has:\n\n| Piece | Where |\n|---|---|\n| `compose` / `keep` / `fingerprint` / `standing` | `workbench/field_brief.py:61`, `:124`, `:40`, `:140` |\n| `field.brief` (read) and `field.brief.keep` (execute), both `({}, [])` | `workbench/field_service.py:44-49`, routed `:157-160` |\n| `documents.create(..., brief=None, blocks=None)` keyword arguments | `workbench/documents.py:356-370` |\n| Field card with tag `BRIEF`, replacement, stale state | `workbench/field_source.py:210-216`, `:417-421`, `:441-447` |\n| B key \u2192 preview in Talk \u2192 staged keep \u2192 G | `workbench/field_qt.py:248`, `workbench/field_page.py:50`, `:328-353` |\n| D steps for a brief; brief written last when settling | `workbench/field_do.py:202-211`, `:284` |\n| Doubt rule for a kept brief | `field_doubt.py` `_page` \u2192 `field_brief.standing` (~`:436-443`) |\n| Observer list and recorded registry | `workbench/activity.py:33`; `docs/GRAPHITE_0.1_REGISTRY.json` and `MANIFEST.json` (modified) |\n\n## 1. Operations that create and revise a document\n\nThere is no `documents.revise` or `documents.update`. The write operations are `documents.create`, `documents.save` and `documents.edit` (`workbench/documents.py:43-52`):\n\n```\n'documents.create': ({'title': TITLE, 'project': ID, 'text': {'type':'string','maxLength':200000}, 'origin': {'type':'string','enum':['HUMAN','SLATE','IMPORTED']}}, [])\n'documents.save':   ({'id': ID, 'expected_revision': REV, 'title': TITLE, 'blocks': BLOCKS, 'origin': {enum ORIGINS}}, ['id','expected_revision','blocks'])\n'documents.edit':   ({'id': ID, 'expected_revision': REV, 'selection': SELECTION, 'change': CHANGE, 'origin': {enum HUMAN,SLATE,IMPORTED,SLATE_MODEL}, 'request': {'type':'string','maxLength':400}}, ['id','expected_revision','selection','change'])\n```\n\n- `TITLE` is a string of 1..200 (`documents.py:31`). `ID` is a string of exactly 32, `REV` an integer \u2265 1 (`workbench/project_desk.py:14`, `:18`, `:24`). `BLOCKS = {'type':'array','maxItems':5000,'items':{'type':'object'}}` (`documents.py:42`).\n- `SELECTION` is `{block, start, end, text?}`; `CHANGE` is `{bold, italic, underline, clear, style, replace, append, append_style}` (`documents.py:36-41`).\n- **Scope:** all three are `execute`; `list/get/interpret/render` are `read` (`documents.py:53`). They merge into `CAPABILITIES` at `workbench/engineering_kernel.py:222`, into the schemas at `workbench/engineering_cli.py:82`, `:177`, and route at `engineering_kernel.py:617`.\n- **Dispatcher checks:** unknown or missing keys are refused (`engineering_kernel.py:499-502`), then `agent_operations.validate` (`:503`), then scope (`:504-507`). `operator()` holds read, candidate, execute, approve (`:297-300`).\n\n**Returns**\n- `documents.create` returns the document record itself, not wrapped (`documents.py:370`; `project_desk.py:133`). So the id is `result['id']` and the revision `result['revision']` (always 1, `project_desk.py:136-139`). `document_qt.py:323-325` uses it that way.\n- `documents.save` returns `{'document', 'saved': True, 'conditions_stale'}` or `{'document', 'saved': False, 'reason': 'UNCHANGED'}` (`documents.py:378-384`).\n- `documents.edit` returns `{'document','applied','actor','basis','model_used','conditions_stale'}` (`documents.py:399`).\n- A stale `expected_revision` is refused with `REVISION_CHANGED\u2026` (`documents.py:391`; `project_desk.py:142-145`).\n\n**Record shape** (`project_desk.py:136-139` plus `documents.py:363-369`):\n```\n{'schema':'arc.project-desk.document/1','kind':'document','id','owner','actor','revision','created',\n 'document_schema':'ledger.document/1','title','blocks':[{'id','style','text','marks'}],'project','origin','updated',\n 'last_change':{'actor','words','at'}, 'derivation'?, 'brief'?}\n```\n`documents.get` returns `{'document', 'summary', 'events':[{'revision','actor','action','at'}], 'plain'}`, plus `'source_state'` only when there is a derivation (`documents.py:419-428`).\n\n**Limits**\n- `text` \u2264 200,000 characters (`documents.py:44`). It is split on `\\n` into one `Normal` block per line (`:120-122`).\n- A block's text is \u2264 32,768 characters and may not contain `\\n`, `\\r` or `\\x00` \u2192 `DOCUMENT_BLOCK_LINE_BREAK` (`:26`, `:97-98`).\n- A document is \u2264 5,000 blocks and \u2264 2,000,000 characters (`:25`, `:27`, `:110`, `:116`).\n- The validator refuses any array over 1,000 items and ignores `maxItems` (`workbench/agent_operations.py:65-67`), so `documents.save` through dispatch carries at most 1,000 blocks.\n- Titles have whitespace collapsed and are cut at 200; an empty title becomes the first 60 characters of the page (`documents.py:136-141`).\n- There is no other character filter.\n- **`derivation`, `brief` and styled `blocks` cannot be set through the operation**; they are Python keyword arguments only (`documents.py:356-358`). A raw `documents.create` line yields only `Normal` paragraphs.\n\n## 2. Body format and what the Documents tab renders\n\n- The body is **blocks**, not markdown: `{'id','style','text','marks'}` with style one of `Normal, Heading1, Heading2, Heading3, Code` (`documents.py:23`). Marks are `{start, end, bold?, italic?, underline?}` (`:24`, `:70-91`).\n- The tab is a `QTextEdit` with `setAcceptRichText(False)` (`workbench/document_qt.py:167`). `to_qt` draws each block with a scaled font: Heading1 \u00d71.6, Heading2 \u00d71.3, Heading3 \u00d71.12, Code in the code font (`:25-26`, `:51-77`).\n- **Renders:** three heading levels, code paragraphs, bold/italic/underline. **Does not exist:** lists, tables, links. A \"- item\" line is literal text.\n- **No reference syntax becomes clickable.** I found no anchor or link handling in `document_qt.py`. `@kind:id` addresses exist only for staC reads (`workbench/addresses.py:20-61`, `document` at `:25`). There is no `claim` or `investigation` address kind.\n- Export is `documents.render` as plain, markdown or html (`documents.py:162-198`; `document_qt.py:677-689`).\n- A page with a `derivation` gets the report bar (Sheet / Source page / Recheck) (`document_qt.py:346-361`). A page with a `brief` mark gets nothing special in the tab.\n- **The model you asked about**, `datasheet_work.report` (`workbench/datasheet_work.py:181-265`): it builds text lines (`:239-248`), then calls `documents.create(kernel, {'title','text','origin':'IMPORTED'}, principal, derivation=derivation)` (`:263-264`) and returns `{'document': document, 'calculation': result}` (`:265`). The derivation is:\n```\n{'profile':'pdf-sheet-calculation-v1','sheet','sheet_revision','pdf':{namespace,item,source_sha256,decision,name,page_index,rect,layer,job},\n 'inputs':[{'symbol','cell','parameter','value','unit','conditions','basis','source_row','original_cells'}],\n 'calculation':<result>, 'recipe':{'expression','inputs','output_unit'?,'assumption'?}, 'replaces'?}\n```\n(`datasheet_work.py:224-226`, `:249-251`, `:257`; pdf keys `:111-112`).\n- **The worked case page** \"07 Case conclusion \u00b7 HOLD\" is not written by any code in the repo; the string appears only in `docs/MODEL_TRIAL_03.md:38`. In the restored case's read dumps (session scratchpad, outside the repo) it is a plain page: no derivation, revision 1, 16 blocks, 125 words, `last_change {actor: HUMAN, words: 'started the document'}`. That is one `documents.create {title, text}`. On the Field it has state `''` and no wires, so it is not a model for wiring.\n\n## 3. What makes a document a Field card, and what wires it\n\nThe rule is `Reader.pages_and_calculations` (`workbench/field_source.py:201-236`). For each `documents.list` row (newest 300, `:44`, `:202`) it reads `documents.get`, then in this order:\n\n1. **Brief** (working tree only, `:210-216`): if `document['brief']` is a dict with `profile == 'field-brief/1'`, it adds `FieldObject('document:<id>', 'document', title, 'the desk written up from the records', 'current', ('revision N',), '', target, 'BRIEF', stac=\u2026)` and then `continue`. **No link is made.** If `mark['replaces']` is set, `'document:'+replaces` goes into `reader.replaced` (`:212`).\n2. **No derivation** (`:224-225`): kind `document`, role `page`, state `''`, facts `('revision N',)`, **no links**.\n3. **Derivation** (`:226-236`): kind `calculation`, state from `source_state.state`. Links: `office:<derivation.sheet>` \u2192 page, labelled `cells B2, B3` (`:233-234`); else `intake:<derivation.pdf.item>` \u2192 page, labelled `source page` (`:235-236`).\n\n- So the only keys that wire a page **to what feeds it** are `derivation.sheet` and `derivation.pdf.item`. No `references` key, investigation id or title prefix is read; the \"07 \" prefix is only the owner's naming.\n- A page is a wire **source** in two places: a finding whose path names `document:<id>` (`field_source.py:277-286`), and a condition card bound to it (`:300`).\n- **A generated brief therefore appears on the Field unwired.** `compose` gives every line an `about` object id (`field_brief.py:65`), but `keep` stores only text blocks and the mark `{'profile','fingerprint','written','counts','replaces'?}` (`field_brief.py:132-134`). The ids are dropped.\n- If you add wires, these facts apply:\n  - Links whose endpoint is not on the Field are dropped silently (`workbench/field_model.py:111`). The page reader runs before findings, totals and jobs (`field_source.py:414-416`).\n  - `fingerprint` already leaves out briefs and wires touching them (`field_brief.py:43-45`), so wiring a brief would not make it stale.\n  - A sheet named by any link counts as belonging to the workspace (`field_source.py:164`, `:174`).\n  - Rank is the longest path from `KIND_RANK` (`document` 3, `finding` 3; `field_model.py:19`), so a brief fed by findings moves a column right.\n\n**How a later page replaces an earlier one**\n- Calculations (committed): a recheck calls `report(..., replaces={'id','title'})` (`datasheet_work.py:325-336`), which sets `derivation['replaces'] = <old document id>` (`:257`). The reader records it (`field_source.py:217-218`).\n- `read_field` then drops replaced objects and their links (`field_source.py:417-420`) and says \"N earlier calculation(s) replaced, kept in Documents\" (`:438`). The old record stays in the Documents list; there is no delete operation.\n- Briefs (working tree): the `gone` test at `:418` was widened to `obj.kind == 'calculation' or obj.tag == 'BRIEF'`. `keep` takes the first brief on the Field as `prior` and sets `mark['replaces'] = prior.target['id']` (`field_brief.py:131`, `:134`). Replaced briefs are not counted in the aside (`field_source.py:421`).\n- Staleness (working tree): after the Field is built, a brief whose `mark['fingerprint']` differs from the current one gets state `recheck` and the line \"the desk changed since it was written\" (`field_source.py:441-447`). The fingerprint is a sha256 over `[id, kind, title, state]` of every non-brief, non-job object and `[source, target, label, stale]` of their wires (`field_brief.py:40-46`).\n\n## 4. How a staged multi-line plan is put up and run\n\n**Step** (`workbench/field_do.py:26-33`): `words`, `kind` ('read' or 'write'), `line`, `why`, `scope`, `settles`, `more` (a tuple of `(words, line)` pairs). `words_first` is not a field; it is set on the instance (`:146`, `:157`) and read with `getattr` (`workbench/field_page.py:258`).\n\n**Lines:** `op()` writes `'/' + operation + ' ' + json.dumps(arguments, ensure_ascii=False, separators=(', ', ': '))` (`field_do.py:36-38`). `call()` parses a `/` line with `json.loads`, anything else through staC's router (`:46-53`). `_by_scope` takes the kind from the Kernel's scope of the **first** line only, and drops a step whose operation is unknown (`:259-273`). At most 9 steps are offered (`:256`).\n\n**Putting up** (`field_page.take`, `:240-267`):\n- A read runs at once through `answer_in_stac` (`:254-255`).\n- A step with `more` becomes `parts = [first line] + [each (words, line) of more]` (`:258`), goes to `face.say_plan(parts, \u2026)` (`:260`), and waits via `_await_go(host, 'all N changes, as listed in Talk', lambda: face.run_plan(card, done))` (`:261`).\n- A single write goes to `face.stage(obj.title, step, done)` and waits for `face.run_staged` (`:264-265`).\n- `_await_go` stores the run in `page.pending` and the words in `view.go` (`:207-212`). G emits only while `view.go` is set (`workbench/field_qt.py:262-263`); `go()` runs the pending run once (`field_page.py:215-221`). The card's own Run button does the same (`workbench/shell2.py:1702`, `:1771`).\n\n**Running** (`shell2.py`):\n- `run_staged` (`:1706-1727`): one run only (`:1710`); dispatches `card.step.line` with `operator()` (`:1712-1713`). On success it says `Done: \"<result['document']['title']>\"` if the result has a `document` dict, else falls through `words` / `changed` / `ran` / `Done.` (`:1719-1723`). On refusal: \"It was refused, and nothing was changed: \u2026\" (`:1725`). Then `done(ok, result)` (`:1727`).\n- `run_plan` (`:1775-1794`): one run only (`:1779`); for each `(obj, step)` **in list order** it dispatches the line (`:1781-1784`), appends `(line, ok, result-or-message)` to `card.results` (`:1787`), marks the row `\u00b7 done` or `\u00b7 REFUSED: \u2026` (`:1790`), and **breaks at the first refusal or exception** (`:1785-1786`, `:1791`). The button reads \"Ran X of N\" (`:1793`) and `done(card.results)` is always called (`:1794`).\n- Lines that ran before a refusal are **not undone**.\n\n**Using an earlier result in a later line: not possible.** Lines are fixed strings when the plan is put up and are dispatched verbatim. There is no substitution in `call()`, and staC refuses `$(` and `${` (`sdk/cli/arc1cli/typed_pipeline.py:16`). Existing plans only use ids known beforehand (`field_do.py:141-157`). The working-tree brief avoids the problem by doing compose and create inside one operation.\n\n**A consequence for a raw create line:** `documents.create` returns the record unwrapped, so the card would say only \"Done.\" and `_after` would not select the new page; both look for `result['document']` (`shell2.py:1719`; `field_page.py:277-280`). `field.brief.keep` returns `{'schema','document':{'id','title','revision'},'lines','replaces','counts'}` (`field_brief.py:136-137`), which fits both.\n\n## 5. Can a line carry a few thousand characters of text?\n\n**A staC line cannot carry a write at all.** Its source must be a registered read (`workbench/stacy_language.py:66-67`). It is also bounded to 8,192 characters (`stacy_language.py:5-6`; `typed_pipeline.py:15`) and may not contain a backtick, `$(`, `${`, `;`, `>`, `<` or a line break anywhere (`typed_pipeline.py:16`).\n\n**A `/op {json}` line can, uncut.** I ran `field_do.op('documents.create', title=\u2026, text=<5,569 chars with \" \" ; > < | backtick $( and 59 line breaks>)` then `field_do.call(line)`: a 5,702-character line, arguments identical after the round trip, no literal newline in the line. The only bounds are the operation's own schema (200,000 for `documents.create.text`).\n\nEvery truncation I found on or near the path:\n\n| Where | What is cut | Touches the dispatched arguments? |\n|---|---|---|\n| `field_do.py:38`, `:46-53` | nothing | no cut |\n| `field_do.py:256`; `shell2.py:1680` | steps offered: first 9 | no |\n| `field_do.py:66` | `_watch` title `[:120]` (agenda step only) | not this path |\n| `shell2.py:1696`, `:1766` | the line is shown whole; `breakable()` adds U+200B after every 18 non-space characters to the **label text only** (`:1462-1464`) | no; the run uses `card.step.line` (`:1712`, `:1783`) |\n| `shell2.py:1715`, `:1786` | exception text `[:300]` | message only |\n| `shell2.py:1725`; `:1790` | refusal message `[:400]`; `[:200]` | message only |\n| `field_qt.py:34`, `:423` | the G words: 240 characters, 3 lines | display only |\n| `context_menu.py:230` | status echo `short(text, 120)` for \"in the line\" | display only |\n| `shell2.py:804` | the writing line is a `QLineEdit` with no `setMaxLength` in `shell2.py` or `typebar_qt.py`; Qt's default cap applies | only if the owner sends the line through the writing strip |\n| `engineering_kernel.py:499-503`; `agent_operations.py:59-62` | no cut: over-length is **refused**, not trimmed (default string cap 1,200,000) | refusal |\n\nTwo side effects of a long line. A staged card shows the full line as one unfolded mono label (`shell2.py:1696`), so a 5,700-character body is a wall of text in Talk. Text copied from that label carries the U+200B characters, and `field_do.call` does not strip them for `/` lines (staC's router does, `workbench/stac_bridge.py:24`).\n\nReading a brief back in Talk has its own cuts (`answer_in_stac`, `shell2.py:1626-1674`): one-field rows show the first 120 rows at 600 characters each (`:1653-1654`); multi-field rows cut each field at 400 (`whole`) or 120, first 50 rows (`:1661-1664`); the text kept for the model cuts each `key: value` at 400, first 50 rows (`:1642-1644`). The read itself refuses more than 200 output rows with \"Output exceeds 200 rows; add take\" (`stacy_language.py:112`; `typed_pipeline.py:272`). So `field.brief | pick lines | select text` fails on a brief of more than 200 lines, while `field.brief.keep` would still work.\n\n## 6. Reads that already return a claim's standing\n\nRead scope: `investigation.list`, `investigation.sheet`, `investigation.path` (`workbench/investigations.py:66-67`). **`investigation.review` is not a read**: its scope is `approve`, it takes `{'claim', 'decision': 'ACCEPT_CHANGE'|'RETIRE'}` (`:63`) and changes records (`:435-447`).\n\n`investigation.list {}` (`:383-386`):\n```\n{'investigations': [{'id','question','state','reason','updated','steps_used'}]}\n```\n`investigation.sheet {'id'}` (`:231-256`):\n```\n{'id','question','objective','state','reason','budget','used':{'steps','seconds'},\n 'read':     [{'id','investigation','address','digest','current','state','added'}],        # state CURRENT | CHANGED | SUPERSEDED\n 'attempted':[step rows where kind == 'STEP'],\n 'checked':  [{'id','claim','program','oracle','expect','value','refutes','created','claim_text','last_outcome','last_step','last_authority'}],\n 'learned':  [claim rows, evidence_state SUPPORTED | REFUTED],\n 'unresolved':[claim rows], 'retired':[claim rows], 'next':{'kind','text','check'?}, 'notice'}\nclaim row: {'id','investigation','role','text','review','retired','created','evidence_state','independent_support','independent_opposition'}\nstep row:  {'id','investigation','seq','kind','purpose','program','inputs','input_key','check_id','outcome','result_digest','summary','duplicate_of','authority','started','finished','stale'}\n```\n- `last_outcome` is `NOT_RUN`, `STALE`, or the step outcome `PASSED | CHECK_FAILED | FAILED` (`:242`).\n- `evidence_state` is `UNKNOWN | SUPPORTED | REFUTED | CONFLICT`, computed from current independent evidence (`:222-228`).\n\n`investigation.path {'claim'}` (`:355-370`):\n```\n{'claim','text','role','evidence_state','independent_support','independent_opposition','review','path':[\n  {'direction','note','independence','kind':'SOURCE','address','digest','counts','source_state'},\n  {'direction','note','independence','kind':'CHECK','step','program','inputs':{address: digest},'outcome','result_digest','ran_with','counts'} ]}\n```\nThe path lists **evidence rows only**. A check that never ran, or failed without `refutes_on_fail`, is not in it (`:184-188`); the full check list for a claim is `sheet['checked']` filtered by `claim`. `field_do.py:136` and `field_doubt._claim` both do exactly that.\n\nDesk-level reads in `workbench/field_service.py` (`SCHEMA = 'graphite.field/1'`, `:36`):\n```\nfield.read  -> {'schema','title','objects':[{'id','kind','title','state','role','facts','where','stac','changed_at','lately','waits'}],\n                'links':[{'source','target','from','to','label','stale'}], 'waiting':[object rows], 'counts',\n                'moved':[{'was','now','calculation'}], 'left_out','elsewhere','could_not_read'}                  (:57-73)\nfield.doubt {id} -> {'schema','id','title','kind','rows':[{'verdict','about','why','see'}],'doubts','cannot_tell','holds'}   (:124-132)\nfield.doubt {}   -> {'schema','rows':[{'title','kind','id','verdict','about','why','see'}],'doubts','cannot_tell','looked_at'} (:133-136)\nfield.trace {id} -> {'schema','id','title','rows':[{'way','steps','kind','title','state','by','stale','next','id','stac'}],\n                     'comes_from','rests_on_it','stale_on_the_way'}                                             (:76-104)\nfield.brief {}   -> {'schema','title','lines':[{'part','text','about'}],'fingerprint',\n                     'counts':{'things','stand','wait','doubts','cannot_tell'}}       (working tree; :148-153, field_brief.py:117-118)\n```\n- `part` is one of `head, title, stands, waits, doubt, cannot tell, number, source, foot` (`field_brief.py:72-116`).\n- A finding's states on the Field come from `field_source.py:256-267`: open, not read, recheck, held, refuted, current.\n- Calculations: `documents.get` gives `document.derivation.inputs` and `source_state.state` of `CURRENT | RECHECK_SHEET_CHANGED | PDF_SOURCE_REVIEW_REQUIRED | SHEET_UNAVAILABLE` (`datasheet_work.py:166-178`).\n- Conditions: `conditions.list` rows are `{'id','document','document_revision','state','reason','expression','result','result_block','assignment','inputs','checked_at','updated','origin'}`, states `CURRENT | STALE | BROKEN` (`workbench/conditions.py:46`, `:141-144`).\n\n## Hook points, in one place\n\n- **A new or changed operation in `field_service.FIELDS`** reaches `CAPABILITIES` (`engineering_kernel.py:225`), the schemas (`engineering_cli.py:89`, `:184`) and the route (`engineering_kernel.py:624`) by itself. A read must be added by hand to `activity.OBSERVER_OPERATIONS` (`workbench/activity.py:33`), and the registry must be re-recorded with `tools/record_registry.py` (`tools/check_release.py` compares against it).\n- **Page \u2192 Field card:** `field_source.py:210-216`. **Replacement:** `:417-421`. **Staleness:** `:441-447`.\n- **Steps for a page:** `field_do._page` (`:202-211`). **Settle order:** `:284`.\n- **Staging and go:** `field_page.brief` (`:328-353`), `_await_go` (`:207`), `shell2.stage` / `run_staged` (`:1687`, `:1706`).\n- **Styled blocks and the mark:** `documents.create(..., brief=, blocks=)` (`documents.py:356-370`); `documents.block(text, style)` (`:60-62`).",
 "key_locations": [
  {
   "what": "Brief module (untracked, in motion): compose() builds lines {'part','text','about'}",
   "file": "/home/user/Struthio/workbench/field_brief.py",
   "line": 61
  },
  {
   "what": "keep(): recomposes, builds styled blocks, mark {'profile','fingerprint','written','counts','replaces'?}, calls documents.create(brief=, blocks=)",
   "file": "/home/user/Struthio/workbench/field_brief.py",
   "line": 124
  },
  {
   "what": "fingerprint(): sha256 over non-brief, non-job objects [id,kind,title,state] and their wires",
   "file": "/home/user/Struthio/workbench/field_brief.py",
   "line": 40
  },
  {
   "what": "standing(): doubt rows for a kept brief, compares desk fingerprint only",
   "file": "/home/user/Struthio/workbench/field_brief.py",
   "line": 140
  },
  {
   "what": "documents FIELDS: create / save / edit argument schemas; no revise or update",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 43
  },
  {
   "what": "documents SCOPES: create/save/edit are 'execute'",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 53
  },
  {
   "what": "Block limits MAX_BLOCKS 5000, MAX_BLOCK_TEXT 32768, MAX_TEXT 2000000; STYLES at line 23",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 25
  },
  {
   "what": "normalize_block: a block's text may not contain \\n, \\r or \\x00 (DOCUMENT_BLOCK_LINE_BREAK)",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 98
  },
  {
   "what": "from_text: plain text becomes one Normal block per line",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 120
  },
  {
   "what": "create(kernel, args, principal, derivation=None, brief=None, blocks=None): keyword arguments not settable through the operation; returns the record unwrapped",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 356
  },
  {
   "what": "get(): {'document','summary','events','plain'} plus 'source_state' only with a derivation",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 419
  },
  {
   "what": "render(): plain / markdown / html export; headings, code, bold/italic/underline only",
   "file": "/home/user/Struthio/workbench/documents.py",
   "line": 162
  },
  {
   "what": "Documents tab page: QTextEdit with setAcceptRichText(False); no links, lists or tables",
   "file": "/home/user/Struthio/workbench/document_qt.py",
   "line": 167
  },
  {
   "what": "to_qt: how stored blocks are drawn (style-scaled fonts, marks)",
   "file": "/home/user/Struthio/workbench/document_qt.py",
   "line": 69
  },
  {
   "what": "report(): the generated calculation page; text lines at 239, derivation at 249, 'replaces' at 257, documents.create at 263",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 181
  },
  {
   "what": "report_state(): CURRENT / RECHECK_SHEET_CHANGED / PDF_SOURCE_REVIEW_REQUIRED / SHEET_UNAVAILABLE",
   "file": "/home/user/Struthio/workbench/datasheet_work.py",
   "line": 166
  },
  {
   "what": "pages_and_calculations(): the rule that turns a document into a Field card",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 201
  },
  {
   "what": "Brief card rule: brief.profile == 'field-brief/1' gives kind document, tag BRIEF, state current, then continue with no links",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 211
  },
  {
   "what": "Plain page rule: no derivation gives role 'page', state '', no links",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 224
  },
  {
   "what": "The only page-feeding wires: office:<derivation.sheet> to the page, else intake:<derivation.pdf.item> to the page",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 233
  },
  {
   "what": "Findings: wires from investigation.path steps (SOURCE address, CHECK inputs) to claim:<id>",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 277
  },
  {
   "what": "read_field: replaced calculations and briefs removed from the Field ('gone')",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 417
  },
  {
   "what": "read_field: a brief whose fingerprint differs becomes state 'recheck'",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 441
  },
  {
   "what": "settle_tables: a sheet named by any link counts as belonging to the workspace",
   "file": "/home/user/Struthio/workbench/field_source.py",
   "line": 164
  },
  {
   "what": "Field.__post_init__: links with an endpoint not on the Field are dropped silently",
   "file": "/home/user/Struthio/workbench/field_model.py",
   "line": 111
  },
  {
   "what": "Step dataclass: words, kind, line, why, scope, settles, more",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 26
  },
  {
   "what": "op(): the '/operation {json}' line writer, no truncation",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 36
  },
  {
   "what": "call(): parses a '/' line with json.loads, anything else through the staC router",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 46
  },
  {
   "what": "_claim: existing multi-line steps (more=...) using only ids known beforehand; words_first set at 146 and 157",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 141
  },
  {
   "what": "_page: steps for a page; BRIEF adds 'See what it would say now' and 'Write it again' (/field.brief.keep)",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 202
  },
  {
   "what": "_by_scope: step kind comes from the Kernel scope of the first line only",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 259
  },
  {
   "what": "settling(): the brief is sorted last in a settle plan",
   "file": "/home/user/Struthio/workbench/field_do.py",
   "line": 284
  },
  {
   "what": "take(): read runs at once; step.more goes to say_plan/run_plan; a single write goes to stage/run_staged",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 240
  },
  {
   "what": "_await_go / go: page.pending and view.go; G runs the pending run once",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 207
  },
  {
   "what": "_after: selects 'document:'+result['document']['id'] after a write",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 270
  },
  {
   "what": "brief(host): B key handler; preview via field.brief, stage /field.brief.keep, wait for G",
   "file": "/home/user/Struthio/workbench/field_page.py",
   "line": 328
  },
  {
   "what": "SlateFace.answer_in_stac: display truncations at 1642-1644, 1646, 1649, 1653-1654, 1661-1664",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1626
  },
  {
   "what": "SlateFace.stage: card shows breakable(step.line) whole; card.step keeps the real line",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1687
  },
  {
   "what": "SlateFace.run_staged: one run, dispatch of card.step.line, 'Done' wording from result['document']['title']",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1706
  },
  {
   "what": "SlateFace.say_plan: several changes listed with one Run",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1756
  },
  {
   "what": "SlateFace.run_plan: lines run in order, break at first refusal (1791), no undo, done(card.results)",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1775
  },
  {
   "what": "breakable(): inserts U+200B every 18 non-space characters into label text",
   "file": "/home/user/Struthio/workbench/shell2.py",
   "line": 1462
  },
  {
   "what": "field_service FIELDS, WRITES, SCOPES, OBSERVERS including field.brief and field.brief.keep",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 38
  },
  {
   "what": "field.read result shape and object row shape (_row at 57)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 63
  },
  {
   "what": "field.doubt result shapes (one thing, or the whole desk)",
   "file": "/home/user/Struthio/workbench/field_service.py",
   "line": 118
  },
  {
   "what": "investigation FIELDS and SCOPES: list/sheet/path are reads; review is 'approve'",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 48
  },
  {
   "what": "sheet(): read / attempted / checked / learned / unresolved / retired / next shapes",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 231
  },
  {
   "what": "path(): evidence path with SOURCE and CHECK link shapes, support and opposition counts",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 355
  },
  {
   "what": "claim_state(): UNKNOWN / SUPPORTED / REFUTED / CONFLICT from current independent evidence",
   "file": "/home/user/Struthio/workbench/investigations.py",
   "line": 222
  },
  {
   "what": "Kernel.dispatch: unknown/missing parameter refusal at 499-502, validate 503, scope 504-507, result envelope 526",
   "file": "/home/user/Struthio/workbench/engineering_kernel.py",
   "line": 485
  },
  {
   "what": "validate(): string length check (default cap 1,200,000) and the 1,000-item array cap at 65-67",
   "file": "/home/user/Struthio/workbench/agent_operations.py",
   "line": 38
  },
  {
   "what": "language.run: 8192-character bound; source must be a read (66-67); 200-row output limit (112)",
   "file": "/home/user/Struthio/workbench/stacy_language.py",
   "line": 5
  },
  {
   "what": "staC split(): 8192 bound and forbidden characters (backtick, $(, ${, ;, >, <, line breaks)",
   "file": "/home/user/Struthio/sdk/cli/arc1cli/typed_pipeline.py",
   "line": 15
  },
  {
   "what": "OBSERVER_OPERATIONS: hand-kept list; field.brief is in it, field.brief.keep is not",
   "file": "/home/user/Struthio/workbench/activity.py",
   "line": 33
  },
  {
   "what": "B key emits brief_asked; G key at 262 emits go_asked only while view.go is set",
   "file": "/home/user/Struthio/workbench/field_qt.py",
   "line": 248
  },
  {
   "what": "Address kinds (@kind:id for staC reads): 'document' at 25; no 'claim' or 'investigation' kind",
   "file": "/home/user/Struthio/workbench/addresses.py",
   "line": 20
  },
  {
   "what": "Only repo mention of the worked case page '07 Case conclusion \u00b7 HOLD'",
   "file": "/home/user/Struthio/docs/MODEL_TRIAL_03.md",
   "line": 38
  }
 ],
 "gaps": [
  "The working tree is being edited by something else while this map was made: field_brief.py, field_do.py, field_model.py, field_source.py and field_doubt.py all changed during the read. Line numbers are a snapshot at 03:22-03:24 UTC and may drift; field_doubt.py numbers are approximate. None of the brief is committed (HEAD 164fe3c has no field_brief.py).",
  "A kept brief is not wired to anything: field_source.py:211-216 adds the card and continues. compose() gives each line an 'about' object id, but keep() stores only text blocks and the mark, so the ids a wire rule would need are not in the record.",
  "Nothing binds the brief the owner saw to the brief that is written: the staged line is '/field.brief.keep {}' with no arguments (field_service.py:45), and keep() reads the desk and composes again at run time (field_brief.py:129-130).",
  "An owner's edit to a kept brief does not change its standing: the mark holds no digest of the page's own blocks, and standing() compares only the desk fingerprint (field_brief.py:140-148). documents.save keeps the 'brief' key (documents.py:381).",
  "The fingerprint covers Field objects and wires only (id, kind, title, state; source, target, label, stale), not the composed lines. A change that alters only a doubt or a cannot-tell row without changing a state, title or wire would leave the brief marked current. Read from the code, not demonstrated.",
  "A line break in any record text would make keep() fail: compose() does not strip them, keep() passes line text straight to documents.block, and normalize_block raises DOCUMENT_BLOCK_LINE_BREAK (documents.py:98). investigation.claim text has no such restriction (investigations.py:38, 54). Read from the code, not run.",
  "Kernel-side title: keep() calls read_field with an empty title, so the page is titled '<investigation question> \u00b7 brief' only when there is exactly one investigation, otherwise 'This workspace \u00b7 brief' (field_source.py:431-433; field_brief.py:64). The window uses the workspace folder name instead (field_page.py:105).",
  "The Talk preview 'field.brief | pick lines | select text' is refused when the brief has more than 200 lines (stacy_language.py:112; typed_pipeline.py:272), and Talk shows at most 120 lines of 600 characters (shell2.py:1653-1654).",
  "The builder of the worked case page '07 Case conclusion \u00b7 HOLD' is not in the repository. Its shape (plain page, origin HUMAN, revision 1, 16 blocks, no derivation, no wires) comes from read dumps of the restored case in the session scratchpad, not from repo code.",
  "No tests or tool checks mention field.brief, field.brief.keep or field_brief (grep over tests_integrated/, tools/, docs/). Per the hard rule no suite was run, so nothing about compose/keep behaviour is confirmed by execution; it is all from reading.",
  "The only thing executed was a pure snippet: field_do.op/call round trip of a 5,569-character body, documents.from_text/normalize_block, and agent_operations.validate limits. No Kernel database, Qt widget or operation dispatch was exercised.",
  "QLineEdit's default maximum length for the writing line was not verified in this PySide6 build; I only confirmed that shell2.py and typebar_qt.py set no explicit maximum on OneBox. The console prompt widget's limit was not checked either.",
  "office_service (office.get) and intake_service (intake.items) were not read. Their result keys are quoted only as the Field code consumes them (field_source.py:133-199; field_doubt.py), not from their own modules.",
  "Whether right-click on a page passage offers anything for an address-like string was checked only by grep (no address regex in context_menu.py); context_menu.target_at was not read in full. related.py (records sharing a page's words) was not read.",
  "field_ripple.py (untracked) was not read; it is outside this subject."
 ]
}