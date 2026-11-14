{
 "summary": "Nearly all of \"what keeps work true\" already exists as operations; none of it needs the window. I ran every operation below on throwaway copies of After Hours 07 (11 scripts, outputs kept). Statements are marked TRIED or READ.\n\nHOW STALENESS IS NOTICED (three different mechanisms):\n- Sources, sheets, calculations: nothing is stored. The state is computed inside the read (office.get, documents.get) by comparing a stored binding with the current one. Any reader sees it at once.\n- Totals (condition cards): stored state, rewritten after every documents.save / documents.edit of the page.\n- Findings: stored, but ONLY updated when investigation.refresh (execute scope) is run. Nothing runs it automatically; the window has one button for it (investigations_qt.py:209).\n\nPER KIND, what is compared (answers question 1):\n- source: the Field reads only `admission` (ACCEPTED current, HELD held, UNREVIEWED waiting, REJECTED/REVOKED not drawn; field_source.py:131-136). Real admission (intake_service.py:152-168) also needs catalog decision == item.decision_id, receipt.policy_hash == current policy hash, receipt.rule_hash == fingerprint of the intake code, dependency decisions/sha256.\n- reviewed sheet: origin.pdf.decision (the admission decision id at review time) against the item's current decision (datasheet_work.py:119-131). States CURRENT_PDF_SOURCE / PDF_SOURCE_REVIEW_REQUIRED. The cells are NOT compared with origin.reviewed_rows: an edited sheet stays current. File sheets: sha256 of the file at origin.source.path against origin.source.sha256 (office_service.py:57).\n- calculation: derivation.sheet_revision against the sheet's current revision, after the sheet's own source check (datasheet_work.py:166-178). States CURRENT / RECHECK_SHEET_CHANGED / PDF_SOURCE_REVIEW_REQUIRED / SHEET_UNAVAILABLE. Revision-level, not cell-level: any save of the sheet stales every calculation on it, and putting the cell back does not restore it (version is inside the revision).\n- page: no state. total: each input span's quoted words at block id + offsets (conditions.py:101-112): CURRENT / STALE / BROKEN.\n- finding/question: inv_sources.digest = sha256 of canonical JSON of ledger.address.read(address).object, against a new read (investigations.py:327-352). A changed source makes evidence citing it stop counting, marks steps whose inputs name that address stale, and sets claims review=NEEDS_REVIEW.\n\nTHE CIRCLE (question 4), TRIED: office.save with B3 280 to 300 -> both calculations RECHECK_SHEET_CHANGED and 'recheck' in the Field; conditions.list unchanged ([]); investigation.sheet unchanged and investigation.refresh says changed=[] (the findings cite the PDFs, not the sheet or calculation); office.datasheet.recheck makes a NEW page (3.6 W, input B3 basis WORKING_SHEET_EDIT) that reads CURRENT while the old page stays 'recheck' for good.\n\nBIGGEST FACTS FOR THE BUILDER: (1) every repair makes a new object and nothing retires the old one; (2) a finding follows a sheet or calculation only if that address was registered with investigation.add_source AND a check reads it; (3) the Field's 'recheck' on a finding is sticky after the owner accepted the change; (4) one check that cannot run blocks investigation.continue for the whole investigation; (5) the worked case's own check cannot fail.\n\nScripts: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/ (common.py, p1_shapes.py ... p11_oracles.py, run.sh); outputs in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/out/p1.txt ... p11.txt.",
 "operations": [
  {
   "name": "office.get",
   "arguments": "{\"id\":\"owner:<32 hex>\"}",
   "scope": "read",
   "effect": "CHECK a sheet. Returns {id, version (int), revision (sha256 over catalog object, version, document, origin), document{title, sheets[{id,name,cells{\"B3\":{type,value,unit,formula,...}}}]}, origin{profile:'reviewed-pdf-table-v1', pdf{namespace,item,source_sha256,decision,job,page_index,rect,layer,name}, reviewed_rows[{source_row,sheet_row,parameter,value,unit,conditions,original_cells,source_words}]}, source_state{state,...}}. source_state.state: CURRENT_PDF_SOURCE | PDF_SOURCE_REVIEW_REQUIRED (PDF sheets); UNCHANGED_ORIGINAL | STALE_ORIGINAL | ORIGINAL_UNAVAILABLE with expected_sha256/current_sha256 (file sheets); STALE_NOTEBOOK_SNAPSHOT, STALE_BOOK_SNAPSHOT, DERIVATIVE_SOURCE_UNAVAILABLE (derivatives).",
   "evidence": "TRIED (p1, p4, p10). workbench/office_service.py:36-60; workbench/datasheet_work.py:119-131. Notebook/book states READ only."
  },
  {
   "name": "documents.get",
   "arguments": "{\"id\":\"<32 hex>\"}",
   "scope": "read",
   "effect": "CHECK a calculation or page. Returns {document{id,title,revision (int),blocks,derivation?}, summary, events[{revision,actor,action,at}], plain, source_state?}. Only a page with a derivation has source_state: {state: CURRENT | RECHECK_SHEET_CHANGED | PDF_SOURCE_REVIEW_REQUIRED | SHEET_UNAVAILABLE, current_revision}. derivation = {profile:'pdf-sheet-calculation-v1', sheet, sheet_revision, pdf{...}, inputs[{symbol, cell, parameter, value, unit, conditions, basis: REVIEWED_PDF_ROW|WORKING_SHEET_EDIT, source_row, original_cells}], calculation{state:FEASIBLE, arithmetic:EXACT_RATIONAL, outputs[{value{decimal,rational,unit,dimension}}], assumptions, model_digest}, recipe{expression, inputs{symbol:cell}, output_unit, assumption}}.",
   "evidence": "TRIED (p1, p2). workbench/documents.py:415-424; workbench/datasheet_work.py:166-178."
  },
  {
   "name": "office.datasheet.recheck",
   "arguments": "{\"id\":\"<calculation page id>\",\"expected_revision\":<page revision, an integer>}",
   "scope": "approve",
   "effect": "RECOMPUTE a calculation from its inputs. Replays derivation.recipe on the sheet's current revision: reads each named Value-column cell again, takes the unit from column C, compiles the expression, evaluates in exact rationals, converts to output_unit. Makes a NEW page (title '<sheet title> \u00b7 calculation', revision 1); the old page is not touched and stays RECHECK_SHEET_CHANGED. Returns {document, calculation}. Refusals seen: 'INCOMPATIBLE_OUTPUT_UNIT' (unit check, after C3 mA to s), 'B3 now names a different parameter. Open the sheet and choose inputs again.', 'B2 needs a reviewed literal number', 'PDF source review changed. Reopen its current page.' Journal: REQUEST_RECEIVED/REQUEST_COMPLETED lines plus DOCUMENT_CREATED on the new page.",
   "evidence": "TRIED (p2, p3, p4, p8, p9). workbench/datasheet_work.py:257-274 (recipe at :272), report at :181-254 (new page at :252), unit check workbench/math_units.py:70."
  },
  {
   "name": "office.datasheet.report",
   "arguments": "{\"id\":\"owner:<sheet>\",\"expected_revision\":\"<sheet revision sha256>\",\"expression\":\"voltage * settled_current\",\"inputs\":{\"voltage\":\"B2\",\"settled_current\":\"B3\"},\"output_unit\":\"W\",\"assumption\":\"...\"}",
   "scope": "approve",
   "effect": "Make a calculation page from a reviewed PDF sheet. 1 to 8 inputs, each a column-B cell of a reviewed row holding a literal number with a unit in column C; every input must be used. This is the kept recipe run on new material: I passed an old page's derivation.recipe unchanged to a freshly reviewed sheet and got 3.36 W, CURRENT.",
   "evidence": "TRIED (p4). workbench/datasheet_work.py:181-254."
  },
  {
   "name": "office.save",
   "arguments": "{\"id\":\"owner:<32 hex>\",\"expected_revision\":\"<sha256 from office.get>\",\"document\":<the whole document from office.get with the cell changed, e.g. sheets[0].cells.B3.value=\"300\">}",
   "scope": "approve",
   "effect": "The only way to edit one cell of a sheet in the Office store: whole document, no cell-level operation. version+1, new revision, the old payload goes to office_history, catalog event 'office.save'. Stales every calculation on the sheet.",
   "evidence": "TRIED (p2, p3, p5a, p9). sdk/cli/arc1cli/office_work.py (_save)."
  },
  {
   "name": "office.candidate.preview / office.candidate.commit",
   "arguments": "preview {\"id\":\"owner:...\",\"expected_revision\":\"<sha>\",\"path\":\"<file>\"} ; commit {\"plan\":\"<plan id>\",\"expected_digest\":\"<plan digest>\"}",
   "scope": "approve",
   "effect": "Take a changed file in as the next version of a sheet. preview returns {id, digest, changes[{change:'CELL_CHANGED', sheet, cell, before, after}], losses}: the only cell-level difference in the program. On a reviewed PDF sheet a CSV replaced sheet 'Reviewed PDF data' by 'Table' with text cells and the calculation then refused to recheck. On a file sheet it merges the change but source_state stays STALE_ORIGINAL (origin.source.sha256 is never updated).",
   "evidence": "TRIED (p8, p10)."
  },
  {
   "name": "references.pdf.page / references.pdf.result",
   "arguments": "page {\"namespace\":\"<ns>\",\"item\":\"<item>\",\"source_sha256\":\"<sha>\",\"page_index\":0} ; result {\"job\":\"<job id>\"}",
   "scope": "execute / read",
   "effect": "Render a page of an admitted PDF as a job (tool references.page, about 1 s here). result returns {state, result{status:'RENDERED', decision, native{words}, image,...}}. All four arguments come from a sheet's origin.pdf.",
   "evidence": "TRIED (p4). workbench/pdf_service.py."
  },
  {
   "name": "office.datasheet.preview",
   "arguments": "{\"job\":\"<render job>\",\"rect\":[x,y,w,h],\"layer\":\"native\"}",
   "scope": "read",
   "effect": "CHECK a reviewed sheet against its page without writing. Returns {state:'REVIEW', source, rows[{source_row, cells, parameter, value, unit, conditions, gaps, words}], digest}. With the sheet's own origin.pdf.job, rect and layer it re-extracts the region; rows[].cells equal to origin.reviewed_rows[].original_cells means the page still says what was reviewed (True on the worked case).",
   "evidence": "TRIED (p4 S1, p10 with a read-only principal). workbench/datasheet_work.py:95-116."
  },
  {
   "name": "office.datasheet.create",
   "arguments": "{\"job\":\"<job>\",\"rect\":[...],\"layer\":\"native\",\"expected_digest\":\"<preview digest>\",\"title\":\"...\",\"rows\":[{\"source_row\":0,\"parameter\":\"Rail voltage\",\"value\":\"12\",\"unit\":\"V\",\"conditions\":\"During both observations\"},...]}",
   "scope": "approve",
   "effect": "RE-REVIEW a sheet from its PDF: makes a NEW sheet bound to the source's current decision (CURRENT_PDF_SOURCE). The rows can be passed straight from the preview. The old sheet stays PDF_SOURCE_REVIEW_REQUIRED.",
   "evidence": "TRIED (p4 S4). workbench/datasheet_work.py:134-163."
  },
  {
   "name": "conditions.list / conditions.get",
   "arguments": "list {} or {\"document\":\"<page id>\"} ; get {\"id\":\"<condition id>\"}",
   "scope": "read",
   "effect": "CHECK totals. list returns {conditions:[{id, document, document_revision, state: CURRENT|STALE|BROKEN, reason, expression:'sum', result{value,unit,text}, result_block, inputs (count), checked_at}]}. get returns {condition{..., inputs[{block,index,start,end,text,value,unit}], method, rechecks}, document_revision_now}. Reason example: 'The words \u201c1.2 W\u201d now read \u201c1.5 W\u201d.'",
   "evidence": "TRIED (p7). workbench/conditions.py:202-215."
  },
  {
   "name": "conditions.recheck",
   "arguments": "{\"id\":\"<condition id>\"}",
   "scope": "execute",
   "effect": "BRING a total up to date: reads the page again, extracts the quantities, adds them with math.evaluate, rewrites the result paragraph through documents.edit (origin SLATE), rebinds the card, state CURRENT. Returns {condition, document, words}. Units that do not add: the paragraph says why and the card stays STALE. Result paragraph gone: BROKEN, never rewritten. Journal: CONDITION_RECHECKED, DOCUMENT_EDITED_BY_SLATE.",
   "evidence": "TRIED (p7 C3, C4). workbench/conditions.py:218-262."
  },
  {
   "name": "documents.edit / documents.save",
   "arguments": "edit {\"id\":\"<page>\",\"expected_revision\":<int>,\"selection\":{\"block\":0,\"start\":14,\"end\":19,\"text\":\"1.2 W\"},\"change\":{\"replace\":\"1.5 W\"},\"origin\":\"HUMAN\"} ; save {\"id\",\"expected_revision\",\"blocks\":[...]}",
   "scope": "execute",
   "effect": "Change a page. Both return conditions_stale: the ids of every card of the page that is STALE or BROKEN after this write. This is where a total is noticed.",
   "evidence": "TRIED (p7). workbench/documents.py:369-404."
  },
  {
   "name": "investigation.sheet",
   "arguments": "{\"id\":\"<investigation id>\"}",
   "scope": "read",
   "effect": "CHECK findings as last recorded. Returns {state: OPEN|WAITING|CRITERIA_SATISFIED|STOPPED, reason, budget, used, read[{id,address,digest,current,state: CURRENT|CHANGED|SUPERSEDED}], attempted[steps], checked[{id,claim,program,oracle,expect,value,refutes,last_outcome: NOT_RUN|PASSED|CHECK_FAILED|FAILED|STALE}], learned[], unresolved[], retired[], next{kind: STOPPED|REVIEW|CHECK|QUESTION|BIND_CHECK|CLAIM|NONE, text, check?}}. `next` is an existing next-step enumerator for an investigation: reuse it.",
   "evidence": "TRIED (p1). workbench/investigations.py:231-272."
  },
  {
   "name": "investigation.path",
   "arguments": "{\"claim\":\"<claim id>\"}",
   "scope": "read",
   "effect": "Why a finding stands. {evidence_state: UNKNOWN|SUPPORTED|REFUTED|CONFLICT, independent_support, independent_opposition, review: CURRENT|NEEDS_REVIEW, path[{kind:'SOURCE', address, digest, counts, source_state} | {kind:'CHECK', step, program, inputs{address:digest}, outcome, counts}]}. Old evidence stays in the path with counts=false.",
   "evidence": "TRIED. workbench/investigations.py:355-370."
  },
  {
   "name": "investigation.refresh",
   "arguments": "{\"id\":\"<investigation id>\"}",
   "scope": "execute",
   "effect": "The write that NOTICES. Reads every source row whose state is CURRENT again; a different digest sets the row CHANGED, stops its evidence counting, marks steps that read that address stale (their checks read STALE) and sets the claims review=NEEDS_REVIEW. Returns the sheet plus changed[addresses]. It does not re-read CHANGED rows, so a source that came back is not seen.",
   "evidence": "TRIED (p3, p4, p6). workbench/investigations.py:327-352."
  },
  {
   "name": "investigation.continue",
   "arguments": "{\"id\":\"<investigation id>\"}",
   "scope": "execute",
   "effect": "RUN the checks that are due (last_outcome NOT_RUN, FAILED or STALE), one at a time in creation order, with read-only authority unless the budget says execute. Returns the sheet plus ran[{step,outcome,duplicate_of}] and authority. Runs nothing while next.kind is REVIEW. A check that cannot run (FAILED) stops the loop and is tried first again next time.",
   "evidence": "TRIED (p3, p5a, p6, p11). workbench/investigations.py:294-324."
  },
  {
   "name": "investigation.check",
   "arguments": "{\"claim\":\"<finding or candidate id>\",\"program\":\"<staC line>\",\"oracle\":\"<sentence>\",\"expect\":\"NONEMPTY|CONTAINS|NOT_CONTAINS|COUNT_AT_LEAST\",\"value\":\"<text or number>\",\"refutes_on_fail\":true}",
   "scope": "execute",
   "effect": "CREATE a check. It only passes when the Kernel ran the program and the oracle held. PASSED adds SUPPORTS evidence; CHECK_FAILED adds OPPOSES only with refutes_on_fail. The oracle is matched, case-folded, against the JSON of the WHOLE language.run answer (plan and program text included); COUNT_AT_LEAST and NONEMPTY count result.rows. Refused for a QUESTION. No operation edits or removes a check.",
   "evidence": "TRIED (p3, p5a, p11). workbench/investigations.py:108-119, 156-191, 417-426."
  },
  {
   "name": "investigation.add_source",
   "arguments": "{\"id\":\"<investigation id>\",\"address\":\"document:<id> | office:owner:<id> | intake:<id> | condition:<id> ...\"}",
   "scope": "execute",
   "effect": "Register an address so refresh watches it; the digest is taken now. Returns {source, address, digest}. Without this a changed sheet or calculation is never noticed by the investigation.",
   "evidence": "TRIED (p3, p5a). workbench/investigations.py:391-400."
  },
  {
   "name": "investigation.claim / investigation.evidence",
   "arguments": "claim {\"id\":\"<investigation>\",\"text\":\"...\",\"role\":\"FINDING|CANDIDATE|QUESTION\"} ; evidence {\"claim\":\"<claim>\",\"direction\":\"SUPPORTS|OPPOSES\",\"source\":\"<source ROW id from sheet.read, not the address>\",\"note\":\"...\"}",
   "scope": "execute",
   "effect": "Write a finding and cite a registered CURRENT source for it. Independence is the source's digest: the same bytes cited twice count once. evidence returns the path.",
   "evidence": "TRIED (p3, p5a, p6)."
  },
  {
   "name": "investigation.review",
   "arguments": "{\"claim\":\"<claim id>\",\"decision\":\"ACCEPT_CHANGE|RETIRE\"}",
   "scope": "approve",
   "effect": "The owner's decision. ACCEPT_CHANGE sets the claim's review to CURRENT and supersedes EVERY CHANGED source of the investigation with a new row whose digest is the last seen one (which can be the word UNAVAILABLE). RETIRE removes the claim from learned/unresolved; it is the only way a QUESTION is closed.",
   "evidence": "TRIED (p3, p5a, p6). workbench/investigations.py:435-447."
  },
  {
   "name": "investigation.step",
   "arguments": "{\"id\":\"<investigation>\",\"program\":\"<staC line>\",\"purpose\":\"<sentence>\"}",
   "scope": "execute",
   "effect": "Run one read and record it as a receipt (seq, program, input digests, outcome DONE|FAILED, result digest, summary). A repeat with unchanged inputs returns duplicate_of. Proves nothing by itself.",
   "evidence": "TRIED (p5a E3)."
  },
  {
   "name": "ledger.address.read",
   "arguments": "{\"address\":\"intake:<id>\"}",
   "scope": "read",
   "effect": "Read any object by address. Returns {address, kind, operation, arguments, object}. sha256(json.dumps(object, sort_keys=True, separators=(',',':'), default=str)) equals the digest the investigation stores: a read-only way to see what refresh would report. The intake digest includes the decision id; the document digest includes source_state, so it changes when the sheet behind a calculation changes.",
   "evidence": "TRIED (p3 B3: SAME for the three PDFs, CHANGED for the page and sheet). workbench/addresses.py:89-97."
  },
  {
   "name": "language.run",
   "arguments": "{\"text\":\"@document:<id> | pick source_state | where state=CURRENT\"}",
   "scope": "read",
   "effect": "Run a staC line. Returns {execution, model_calls:0, plan{call,text,...}, rows, schema}. Forms that work: '@document:<id> | pick source_state | select state'; '@document:<id> | pick document.derivation.calculation.outputs | select value.decimal,value.unit'; '@office:<id> | pick document.sheets | select cells.B3.value,cells.C3.value'; '@office:<id> | select source_state.state'; '@condition:<id> | pick condition | select state,reason,result.text'; 'investigation.sheet {\"id\":\"..\"} | pick checked | select oracle,expect,value,last_outcome'. Forms that fail: 'documents.get {..} | select source_state.state' gives nulls (rows are taken from the events list); '@office:<id> | rows' and '| sheet 1' are refused.",
   "evidence": "TRIED (p3 B0, p5a E0, p7, p11)."
  },
  {
   "name": "intake.items / intake.read / intake.item / intake.search",
   "arguments": "items {\"namespace\":\"<ns>\",\"state\":\"HELD\"} ; read {\"id\":\"<item>\"} ; item {\"id\":\"<item>\"} ; search {\"namespace\":\"<ns>\",\"query\":\"startup pulse\"}",
   "scope": "read, read, APPROVE, read",
   "effect": "CHECK sources. items: {total, items[{id,name,sha256,bytes,admission,decision_id,reasons,...}], generation}. read: text and decision of an admitted item, refused with REFERENCE_NOT_CURRENTLY_ADMITTED otherwise. item (needs approve although it reads): adds assessment{eligible, recommendation, reasons} , policy_hash and decisions[]. search: {hits[{id,name,sha256,decision,locator,text}], generation}.",
   "evidence": "TRIED (p1, p4, p5a, p10: intake.item refused for a read-only principal). workbench/intake_service.py:152-168, 428-447."
  },
  {
   "name": "intake.revoke / intake.decide",
   "arguments": "revoke {\"id\":\"<item>\",\"expected_decision\":\"<decision_id>\",\"reason\":\"...\"} ; decide {\"id\":\"<item>\",\"decision\":\"ACCEPTED|HELD|REJECTED\",\"expected_sha256\":\"<item sha256>\",\"expected_policy_hash\":\"<from intake.item or intake.policy>\",\"expected_decision\":\"<current decision_id>\",\"reason\":\"...\"}",
   "scope": "approve",
   "effect": "Change a source's admission. Each writes a new decision receipt with a new id. Every sheet reviewed from the item becomes PDF_SOURCE_REVIEW_REQUIRED and stays so, even after the same bytes are accepted again; its calculations follow; the investigation digest changes.",
   "evidence": "TRIED (p4, p6, p10)."
  },
  {
   "name": "intake.checkpoint / intake.catalog.restore",
   "arguments": "checkpoint {\"namespace\":\"<ns>\",\"label\":\"...\"} ; restore {\"id\":\"<checkpoint id>\",\"expected_generation\":<intake.items generation>,\"reason\":\"...\"}",
   "scope": "execute / approve",
   "effect": "Save and restore which items are admitted. An unchanged item keeps its decision id; an item whose admission had changed gets a new decision id on restore, so its sheet is still stale. Not an undo for sheets.",
   "evidence": "TRIED (p4 S5, p5b R1)."
  },
  {
   "name": "references.status / references.index / references.search",
   "arguments": "status {\"namespace\":\"<ns>\"} ; index {\"namespace\":\"<ns>\"} ; search {\"namespace\":\"<ns>\",\"query\":\"...\"}",
   "scope": "read / execute / read",
   "effect": "The searchable index over admitted sources. In the worked case status says current_sources 0 with REFERENCE_INDEX_BINDING_STALE_REBUILD_REQUIRED for all three, and search returns no hits; references.index (a job, about 1 s) brings it to current_sources 3 and search then returns passages.",
   "evidence": "TRIED (p5a, p5b R3)."
  },
  {
   "name": "references.pdf.info / references.impact",
   "arguments": "info {\"namespace\":\"<ns>\",\"item\":\"<item>\"} ; impact {\"namespace\":\"<ns>\",\"item\":\"<item>\"}",
   "scope": "read",
   "effect": "info: {state:'CURRENT', decision, page_count, source_sha256}, refused when the item is not admitted. impact: {affected_items, dependencies, links, packet_reviews, coverage:'CAPTURED_DEPENDENCIES_ONLY_UNTRACKED_IMPACT_UNKNOWN'}: it knows intake dependencies and reference packets only, not sheets, calculations or findings.",
   "evidence": "TRIED (p4 S0)."
  },
  {
   "name": "agent.assign + agent.run (profile numbers_on_page)",
   "arguments": "assign {\"request\":\"add up the numbers on this page\",\"profile\":\"numbers_on_page\",\"context\":{\"document\":\"<page id>\"}} ; run {\"id\":\"<assignment id>\",\"max_steps\":20}",
   "scope": "execute",
   "effect": "The only way through the dispatcher to make a condition card (conditions.create is a function, not an operation). Five recorded steps without a model: read, extract, sum, write the result paragraph, bind the card. Also opens its own investigation with one finding.",
   "evidence": "TRIED (p7 C1). workbench/profile_numbers.py; workbench/agent_loop.py:109-117."
  },
  {
   "name": "agenda.add / agenda.run_next / agenda.view",
   "arguments": "add {\"title\":\"...\",\"program\":\"@document:<id> | pick source_state | select state\",\"watch\":true} or {\"title\":\"...\",\"investigation\":\"<id>\"} ; run_next {} ; view {}",
   "scope": "execute / execute / read",
   "effect": "Already there: a watch keeps asking a staC read (every 6 h by default) and reports only a change ('Watching: 1 row now. You will hear only when this changes.'); an item with an investigation runs investigation.continue with read+execute. run_next ran both. An investigation item given only when.every_hours ended DONE after one run.",
   "evidence": "TRIED (p7 J). workbench/agenda.py:221-223, 311, 335-358."
  },
  {
   "name": "jobs.list / jobs.get / jobs.resume / jobs.cancel / jobs.recover",
   "arguments": "list {} ; get {\"id\"} ; resume {\"id\"} ; cancel {\"id\"} ; recover {}",
   "scope": "read, read, execute, execute, approve",
   "effect": "Unfinished work. States: Queued, Running, Waiting for Approval, Paused, Completed, Failed, Cancelled, Interrupted, Waiting for Agent, Waiting for Execution Approval, Waiting for Provider. resume accepts only Interrupted or Paused.",
   "evidence": "jobs.list and jobs.get TRIED; resume, cancel, recover READ only (workbench/engineering_kernel.py:68-80, 829). The worked case has no unfinished job."
  },
  {
   "name": "workbench.field_source.read_field(kernel, principal)",
   "arguments": "Python call, not an operation; returns (Field, reader)",
   "scope": "read (observer operations only)",
   "effect": "The Field's reader. Field.objects[] have id ('intake:<id>', 'office:owner:<id>', 'document:<id>', 'claim:<id>', 'condition:<id>', 'job:<id>'), kind, title, state, lines (not 'facts'), target, stac. Field.links[] have source, target, label, stale. The object ids are valid addresses for ledger.address.read except claim: and job-less kinds.",
   "evidence": "TRIED in every script. workbench/field_source.py:391-403."
  }
 ],
 "recipes": [
  {
   "goal": "Question 4, the whole circle: change one input cell of the sheet that feeds a calculation, watch what each reader says, bring it back. Ids are the worked case's.",
   "steps": "MAKE STALE\n[read] office.get {\"id\":\"owner:db5f669f863d4c71b89fa7ba348957da\"}\n[approve] office.save {\"id\":\"owner:db5f669f863d4c71b89fa7ba348957da\",\"expected_revision\":\"69dada6fef720000e4b538e9cc3a9518ecba564118661fc4b7a7e81372536a27\",\"document\":<office.get document with sheets[0].cells.B3.value=\"300\">}\nWHAT THE READS SAY\n[read] conditions.list\n[read] documents.get {\"id\":\"0e39bf65e24740a29a504a6be6e00885\"}\n[read] documents.get {\"id\":\"500cd60ebe49411bb9b9e5bbe0570214\"}\n[read] investigation.sheet {\"id\":\"c574ae94d79542f582932d151fad631f\"}\n[execute] investigation.refresh {\"id\":\"c574ae94d79542f582932d151fad631f\"}\nread_field(kernel, principal)\nBRING BACK\n[approve] office.datasheet.recheck {\"id\":\"0e39bf65e24740a29a504a6be6e00885\",\"expected_revision\":2}\n[approve] office.datasheet.recheck {\"id\":\"500cd60ebe49411bb9b9e5bbe0570214\",\"expected_revision\":2}\n[read] documents.get {\"id\":\"<new page id from the recheck result>\"}",
   "tried": true,
   "result": "After the save: sheet version 2, still CURRENT_PDF_SOURCE. conditions.list {conditions: []} (unchanged). Both calculations source_state RECHECK_SHEET_CHANGED, including the one that uses B2 and B4 only. investigation.sheet unchanged, refresh changed=[]. Field: both calculations 'recheck', both sheet-to-calculation wires stale, all four findings still 'current'. After the rechecks: two NEW pages titled '07 Bench readings \u00b7 calculation' (3.6 W = 18/5, inputs voltage B2 REVIEWED_PDF_ROW and settled_current B3 WORKING_SHEET_EDIT) read CURRENT; the two original pages are still 'recheck' in the Field and nothing can settle them. Putting B3 back to 280 makes version 3 and stales the new pages too."
  },
  {
   "goal": "Make a finding follow the calculation it quotes, then carry a change all the way to a current finding (the sequence the doer runs when a number moved).",
   "steps": "WIRE ONCE\n[execute] investigation.add_source {\"id\":\"<inv>\",\"address\":\"document:<calc>\"}\n[execute] investigation.check {\"claim\":\"<finding>\",\"program\":\"@document:<calc> | pick document.derivation.calculation.outputs | select value.decimal,value.unit\",\"oracle\":\"The settled power calculation gives 3.36 W.\",\"expect\":\"CONTAINS\",\"value\":\"\\\"value.decimal\\\": \\\"3.36\\\"\",\"refutes_on_fail\":true}\n[execute] investigation.check {\"claim\":\"<finding>\",\"program\":\"@document:<calc> | pick source_state | where state=CURRENT\",\"oracle\":\"The calculation agrees with its sheet.\",\"expect\":\"COUNT_AT_LEAST\",\"value\":\"1\",\"refutes_on_fail\":true}\n[execute] investigation.continue {\"id\":\"<inv>\"}\nAFTER THE SHEET CHANGED\n[execute] investigation.refresh {\"id\":\"<inv>\"}\n[approve] office.datasheet.recheck {\"id\":\"<calc>\",\"expected_revision\":<n>}   -> <new calc>\n[approve] investigation.review {\"claim\":\"<finding>\",\"decision\":\"ACCEPT_CHANGE\"}\n[approve] investigation.review {\"claim\":\"<finding>\",\"decision\":\"RETIRE\"}   (its words name the old number)\n[execute] investigation.claim {\"id\":\"<inv>\",\"text\":\"Settled draw is 3.6 W. Rev B allows 6 W.\",\"role\":\"FINDING\"}   -> <new claim>\n[execute] investigation.add_source {\"id\":\"<inv>\",\"address\":\"document:<new calc>\"}   -> <source row>\n[execute] investigation.evidence {\"claim\":\"<new claim>\",\"direction\":\"SUPPORTS\",\"source\":\"<source row>\",\"note\":\"The recomputed calculation.\"}\n[execute] investigation.check {\"claim\":\"<new claim>\",\"program\":\"@document:<new calc> | pick document.derivation.calculation.outputs | select value.decimal,value.unit\",\"oracle\":\"The settled power calculation gives 3.6 W.\",\"expect\":\"CONTAINS\",\"value\":\"\\\"value.decimal\\\": \\\"3.6\\\"\"}\n[execute] investigation.continue {\"id\":\"<inv>\"}",
   "tried": true,
   "result": "p3 and p11. After refresh: changed=['document:<calc>','office:<sheet>'], both checks STALE, the finding review NEEDS_REVIEW and 'recheck \u00b7 needs your review' in the Field, next.kind REVIEW, and continue ran nothing until the review. With the COUNT_AT_LEAST form the rerun gave CHECK_FAILED and the finding became CONFLICT (2 for, 2 against). After the retire-and-rewrite: new finding SUPPORTED, support 2, 'current' in the Field; the new check PASSED."
  },
  {
   "goal": "Read-only sweep: is anything out of date? (no write, read scope only)",
   "steps": "[read] intake.items {\"namespace\":\"<ns>\"}   -> admission of each source\n[read] office.get {\"id\":\"owner:<sheet>\"}   -> source_state.state, for each sheet\n[read] office.datasheet.preview {\"job\":origin.pdf.job,\"rect\":origin.pdf.rect,\"layer\":origin.pdf.layer}   -> compare rows[].cells with origin.reviewed_rows[].original_cells\n[read] documents.get {\"id\":\"<page>\"}   -> source_state.state, for each page with a derivation\n[read] conditions.list   -> state and reason of each total\n[read] investigation.sheet {\"id\":\"<inv>\"}   -> next, checked[].last_outcome, read[]\n[read] ledger.address.read {\"address\":<each read[].address whose state is CURRENT>}   -> sha256 of canonical JSON of .object against read[].digest\n[read] references.status {\"namespace\":\"<ns>\"}   -> current_sources, unavailable[]",
   "tried": true,
   "result": "All eight ran with a principal holding only 'read' (p10 M1) except intake.item, which needs approve. The digest comparison reproduced exactly what investigation.refresh then reported (p3 B3 and B4)."
  },
  {
   "goal": "Bring an investigation back after a source was withdrawn and admitted again.",
   "steps": "[execute] investigation.refresh {\"id\":\"<inv>\"}   (row becomes CHANGED, current='UNAVAILABLE')\n[approve] investigation.review {\"claim\":\"<each NEEDS_REVIEW claim>\",\"decision\":\"ACCEPT_CHANGE\"}   (new row with digest 'UNAVAILABLE')\n[execute] investigation.refresh {\"id\":\"<inv>\"}   (now sees the real digest: CHANGED again)\n[approve] investigation.review {\"claim\":\"<any live claim>\",\"decision\":\"ACCEPT_CHANGE\"}   (new CURRENT row with the real digest)\n[read] investigation.sheet {\"id\":\"<inv>\"}   -> take the id of the newest CURRENT row for that address\n[execute] investigation.evidence {\"claim\":\"<finding>\",\"direction\":\"SUPPORTS\",\"source\":\"<that row id>\",\"note\":\"...\"}   for each finding that cited it",
   "tried": true,
   "result": "p6. Support went 2 -> 1 -> back to 2, review CURRENT, evidence SUPPORTED. The Field still draws both findings 'recheck' afterwards because the superseded evidence stays in the path with counts=false."
  },
  {
   "goal": "Re-review a sheet whose PDF source changed admission, then recompute.",
   "steps": "[read] office.get {\"id\":\"owner:<old sheet>\"}   -> origin.pdf {namespace,item,source_sha256,page_index,rect,layer}\n[execute] references.pdf.page {\"namespace\":..,\"item\":..,\"source_sha256\":..,\"page_index\":0}   -> job; wait until jobs.get state is Completed\n[read] office.datasheet.preview {\"job\":\"<job>\",\"rect\":[..],\"layer\":\"native\"}   -> rows, digest\n[approve] office.datasheet.create {\"job\":\"<job>\",\"rect\":[..],\"layer\":\"native\",\"expected_digest\":\"<digest>\",\"title\":\"...\",\"rows\":[{source_row,parameter,value,unit,conditions} from the preview]}   -> new sheet\n[approve] office.datasheet.report {\"id\":\"<new sheet>\",\"expected_revision\":\"<its revision>\", ...the old page's derivation.recipe}",
   "tried": true,
   "result": "p4 S4. New sheet CURRENT_PDF_SOURCE, new calculation 3.36 W CURRENT. The old sheet and its two calculations stay 'recheck'; office.datasheet.recheck on an old calculation is refused with 'PDF source review changed. Reopen its current page.'"
  },
  {
   "goal": "A total on a page: make it, stale it, bring it back.",
   "steps": "[execute] documents.create {\"title\":\"07 Power budget\",\"text\":\"Board A draws 1.2 W.\\nBoard B draws 0.8 W.\"}\n[execute] agent.assign {\"request\":\"add up the numbers on this page\",\"profile\":\"numbers_on_page\",\"context\":{\"document\":\"<page>\"}}\n[execute] agent.run {\"id\":\"<assignment>\",\"max_steps\":20}\n[read] conditions.list {\"document\":\"<page>\"}\n[execute] documents.edit {\"id\":\"<page>\",\"expected_revision\":2,\"selection\":{\"block\":0,\"start\":14,\"end\":19,\"text\":\"1.2 W\"},\"change\":{\"replace\":\"1.5 W\"},\"origin\":\"HUMAN\"}\n[read] conditions.list\n[execute] conditions.recheck {\"id\":\"<condition>\"}",
   "tried": true,
   "result": "p7. Card CURRENT '2 W'; the edit returned conditions_stale=[id] and the card read STALE 'The words \u201c1.2 W\u201d now read \u201c1.5 W\u201d.' with a 'condition recheck' sheet in the Field; recheck rewrote the paragraph to 2.3 W and the card left the Field. With 0.8 V the card stays STALE ('cannot be added'); with the result paragraph deleted it is BROKEN and recheck only says so."
  },
  {
   "goal": "NEXT STEPS a program can offer, by kind and state (question 5). Every argument comes from the object's own record. R = read, W = write with its scope.",
   "steps": "SOURCE current: R intake.read {id}; R references.pdf.info {namespace,item}; R intake.search {namespace,query}; W(execute) references.pdf.page {namespace,item,source_sha256,page_index}.\nSOURCE held or waiting: R intake.items {namespace,state:'HELD'}; R(approve scope) intake.item {id} -> assessment; W(approve) intake.decide {id,decision,expected_sha256,expected_policy_hash,expected_decision,reason}.\nSHEET recheck (PDF_SOURCE_REVIEW_REQUIRED): R intake.items to see the item's admission; W(approve) intake.decide if it is not ACCEPTED; R office.datasheet.preview {job,rect,layer} from origin.pdf (W(execute) references.pdf.page first if the old job no longer answers); W(approve) office.datasheet.create -> new sheet.\nSHEET recheck (STALE_ORIGINAL): W(approve) office.candidate.preview {id,expected_revision,path: origin.source.path} to see changes[]; W(approve) office.candidate.commit; or W(approve) office.import.preview/commit for a fresh sheet.\nSHEET current but edited: R office.get and compare cells with origin.reviewed_rows; R office.datasheet.preview to compare with the page.\nCALCULATION recheck (RECHECK_SHEET_CHANGED): R '@document:<id> | pick document.derivation.inputs | select symbol,parameter,cell,value,conditions'; R '@office:<derivation.sheet> | pick document.sheets | select cells.<cell>.value' for each input cell, to say which input moved; W(approve) office.datasheet.recheck {id,expected_revision}.\nCALCULATION recheck (PDF_SOURCE_REVIEW_REQUIRED): the sheet steps above, then W(approve) office.datasheet.report on the new sheet with derivation.recipe.\nTOTAL recheck (STALE): R conditions.get {id} -> reason, inputs; W(execute) conditions.recheck {id}. BROKEN: W(execute) agent.assign + agent.run on row.document for a new card.\nFINDING recheck: R investigation.path {claim} -> which step has counts=false or source_state CHANGED; R ledger.address.read of that address; W(execute) investigation.refresh {id}; W(approve) investigation.review {claim,decision}; W(execute) investigation.continue {id}.\nFINDING open (UNKNOWN) or sheet.next BIND_CHECK: W(execute) investigation.check {...}; W(execute) investigation.evidence {...}; then investigation.continue.\nFINDING held (CONFLICT) or refuted: R investigation.path; W(approve) investigation.review {claim,decision:'RETIRE'}; W(execute) investigation.claim for the corrected words.\nOPEN QUESTION: R intake.search {namespace, query: the question's words}; R references.search (after references.index); R intake.items against sheet.read[].address to list sources not yet read; W(execute) investigation.add_source for one of them; W(execute) investigation.step {id,program,purpose} to record a read; W(execute) investigation.claim role CANDIDATE or FINDING with evidence; W(approve) investigation.review {claim: question, decision:'RETIRE'}.\nJOB waiting/paused/interrupted/failed: R jobs.get {id}; W(execute) jobs.resume {id} for Interrupted or Paused; W(execute) jobs.cancel {id}.\nANY object: W(execute) agenda.add {title, program: its staC line, watch: true}.",
   "tried": true,
   "result": "Every step listed was run at least once in p2 to p11 except jobs.resume and jobs.cancel (read only) and the file-sheet import of a fresh sheet after staleness (the import itself was run). The 'which input moved' comparison was run by hand, not as one line."
  }
 ],
 "gaps": [
  "STALE OBJECTS ARE NEVER RETIRED (TRIED). office.datasheet.recheck, office.datasheet.create and office.datasheet.report each make a new object; the old calculation page, old sheet stay 'recheck' in the Field for good. The registry has no delete, archive or supersede for a page, an Office sheet, a condition, a check or an investigation. An Office sheet can be archived only from the window, by a direct store call that bypasses the dispatcher (workbench/concern_qt.py:523, catalog.set_state).",
  "A recomputed calculation loses its name and its place: the new page is titled '<sheet title> \u00b7 calculation' (workbench/datasheet_work.py:252) and has a new id, so the owner's title ('07 Settled power \u00b7 3.36 W'), every check program and every registered address still point at the old page (TRIED).",
  "FINDINGS ARE NOT WIRED TO WHAT THEY QUOTE (TRIED). In the worked case the finding 'Settled draw is 3.36 W' cites two PDFs only. After the cell edit and the recompute to 3.6 W it is still SUPPORTED and 'current'. It follows the calculation only after investigation.add_source plus a check on that address.",
  "NOTHING RUNS investigation.refresh. It is an execute-scope write, called from one window button (workbench/investigations_qt.py:209). The Field reads investigation.sheet and investigation.path only, so a finding never turns 'recheck' by being looked at. There is no read-only refresh; the read-only substitute is ledger.address.read plus the digest comparison.",
  "A check whose input is not a registered source is never run again (TRIED, p5a E1): refresh marks a step stale only when a CHANGED source row has that address (workbench/investigations.py:342-347), and continue runs only NOT_RUN, FAILED or STALE checks.",
  "THE WORKED CASE'S OWN CHECK CANNOT FAIL (TRIED). Program '@office:owner:4f357ff3\u2026' with CONTAINS 'Up to 80 ms' still passed after cell D3 was changed to 'Up to 95 ms', because the whole record is matched and origin.reviewed_rows still holds the reviewed words. A sheet check must narrow to the cells: '@office:<id> | pick document.sheets | select cells.D3.value'.",
  "The oracle is matched against the whole language.run answer, plan and program text included (workbench/investigations.py:108-114, 167-174). A CONTAINS value that appears in the program text passes by itself (READ, follows from the code; the reviewed_rows case above is the TRIED instance).",
  "A failed check that does not refute leaves no trace in the Field (READ plus p3): CHECK_FAILED without refutes_on_fail adds no evidence row, so there is no wire and the finding keeps its state. next_action does not list CHECK_FAILED either (workbench/investigations.py:265).",
  "ONE CHECK THAT CANNOT RUN BLOCKS THE INVESTIGATION (TRIED, p5a E2 and p6 R4). continue takes the first pending check, breaks on FAILED, and takes the same one first next time. Checks of retired claims stay in the queue (the list is built over all claims, workbench/investigations.py:238-244), so retiring the claim does not unblock it. No operation removes a check.",
  "THE FIELD'S 'recheck' ON A FINDING IS STICKY (TRIED, p3 and p6). After ACCEPT_CHANGE, a rerun of the checks and fresh evidence, the claim is review CURRENT and SUPPORTED, but workbench/field_source.py:239-240 calls it changed while any path step has counts=false, and superseded evidence is never removed from the path. Only RETIRE plus a new claim clears it.",
  "A source that came back is not seen by refresh (TRIED, p6): refresh reads CURRENT rows only; ACCEPT_CHANGE then records the word UNAVAILABLE as the new snapshot. It takes review, refresh, review, evidence to restore one citation. Re-admitting identical bytes also counts as a change, because the intake digest includes the decision id.",
  "investigation.review ACCEPT_CHANGE on one claim supersedes every CHANGED source of the whole investigation (workbench/investigations.py:442-445), while the other affected claims stay NEEDS_REVIEW until each is reviewed (TRIED).",
  "A sheet whose source admission ever changed is stale for good (TRIED): accepting the same file again and intake.catalog.restore both leave it PDF_SOURCE_REVIEW_REQUIRED, because the sheet is bound to the old decision id. Only a new sheet is current.",
  "A file sheet stays STALE_ORIGINAL after the changed original was taken in with office.candidate.commit (TRIED, p10): origin.source.sha256 is never updated.",
  "An edited reviewed sheet still reads CURRENT_PDF_SOURCE and 'current' (TRIED). The edit shows only later, as basis WORKING_SHEET_EDIT on a recomputed calculation. No state says 'this sheet no longer matches its page'.",
  "Calculation staleness is by sheet revision, not by cell (TRIED): the startup calculation (B2, B4) went 'recheck' when only B3 changed, and no read says which input moved.",
  "A BROKEN total has no resolving operation (TRIED): conditions.recheck only reports it; a new card comes from agent.assign, and the broken card stays in the Field as 'recheck'. The finding the agent wrote ('total 2 W') is not updated by conditions.recheck and stays 'open \u00b7 no evidence yet'.",
  "conditions.create is not an operation; a card can be made only through agent.assign with profile numbers_on_page (workbench/profile_numbers.py:111).",
  "No cell-level edit for Office sheets: office.save takes the whole document (approve). files.cells and joined.session.edit exist for other stores and were not tried.",
  "The Field shows a source by admission only: a policy or rules change that makes every read fail (REFERENCE_POLICY_OR_RULES_STALE, workbench/intake_service.py:158) would still draw 'current' (READ, not tried).",
  "intake.item is a read that needs the approve scope, so a read-only doer cannot see why a source is held (TRIED)."
 ],
 "advice": "Build the enumerator on what is there; do not write a second staleness engine.\n\n1. Reuse three existing pieces. (a) investigation.sheet.next {kind, text, check} is already \"the program names the next step\" for an investigation (workbench/investigations.py:259-272). (b) derivation.recipe plus office.datasheet.report is already \"a chain kept and run again on new material\". (c) agenda.add with watch:true is already \"tell me only when this read changes\", and an agenda item with an investigation already runs the due checks.\n\n2. The states to enumerate from are the records' own words, not the Field's five. Read source_state.state, condition.state and reason, checked[].last_outcome, read[].state, review and evidence_state directly; the Field collapses several different repairs into 'recheck'.\n\n3. Scopes give the owner's gate for free. A doer holding read+execute can run investigation.refresh, investigation.continue, investigation.check/add_source/evidence/claim/step, conditions.recheck, references.pdf.page, references.index and documents.edit. Everything that changes a sheet, recomputes a calculation, decides a source or settles a claim is approve: office.save, office.datasheet.recheck/create/report, intake.decide/revoke, investigation.review. Note the asymmetry: conditions.recheck rewrites the owner's page with execute only.\n\n4. A job's checks, done properly: for each result, investigation.add_source on its address and a check with refutes_on_fail:true whose program starts with that @address and narrows with pick/select. Prefer COUNT_AT_LEAST over a where-filter, or CONTAINS on a selected field written as \"\\\"field\\\": \\\"value\\\"\". Never check a whole record. Done is investigation.sheet state CRITERIA_SATISFIED, which the code sets only when every non-refuting check PASSED and nothing waits (workbench/investigations.py:281-282).\n\n5. The smallest fixes that would close the worst holes, in order: let a stale calculation be recomputed in place or marked superseded by its replacement; drop superseded evidence from the Field's 'changed' test (workbench/field_source.py:239); skip checks of retired claims and let continue move past a FAILED check; have refresh re-read CHANGED rows; give a check its inputs as sources automatically when it is created.\n\n6. Writing staC for this: '@address | pick <path> | select <fields>' works; 'select' straight after documents.get reads the events list. ledger.journal.read takes after as a string (\"182\"), and limit alone returns the oldest events.",
 "not_checked": "Read in the code but not run: jobs.resume, jobs.cancel, jobs.recover, jobs.pause (the case has no unfinished job); the notebook and Orange Book sheet states (STALE_NOTEBOOK_SNAPSHOT, STALE_BOOK_SNAPSHOT); office.operation.preview/run with mode 'recalculate' or 'edit' (LibreOffice 24.2.7.2 is present per office.doctor, the job was not started); intake.import, intake.review and intake.policy.set, so a PDF whose bytes changed (a new file, a new item) was not rehearsed, only withdrawal and re-admission of the same bytes; OCR-layer sheets; the oracle matching its own program text (inferred from the code); the Field's 'elsewhere', 'not read' and 'unavailable' states. Not looked at beyond their names: reasons.*, math.get / problems.* freshness, methods.result, knowledge.investigation.result, copies.review / copies.refresh, slate.context.check, files.cells, joined.session.*, receiving.*, procedures.* and work.* (several follow the same stored-binding-against-current pattern for kinds the Field does not draw). No model was used; nothing was run on the ThinkPad; the window was only the offscreen harness. Nothing under /home/user/Struthio was changed."
}