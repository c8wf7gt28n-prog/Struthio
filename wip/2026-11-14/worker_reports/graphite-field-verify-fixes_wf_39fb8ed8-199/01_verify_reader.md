{
 "summary": "Most of the reader and model fixes are real: R1, R3, R5, R8 and R10 are closed, and R2, R4, R6, R7 and R9 are partly closed with small, located remainders. Every staC line runs with ok True and returns rows: 14 of 14 on the worked case's work face and 13 of 13 on the network face, none refused. The fixes introduced two wrong results that matter. The Field now keeps its reading while the workspace journal is unchanged, so a sheet whose original file changed on disk stays green CURRENT until R is pressed. The new \"belongs here\" test also hides sheets made in this workspace: a notebook copy, a file imported from outside the folder, and a reviewed sheet whose PDF admission was revoked, which is the one that needs the recheck. A refuted finding now carries the green CURRENT mark where it read HELD before. Probes and their outputs are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-reader/ (outputs under out/); nothing under the worktree or /home/user/Struthio was edited, and /home/user/Struthio has moved on to 917e9a5, so \"old\" comparisons use the three Field modules extracted from 63d9d2d.",
 "verdicts": [
  {
   "defect": "R1. Unchanged imported sheets and working copies marked RECHECK forever; an Office row of kind 'document' drawn as SHEET",
   "verdict": "closed",
   "observed": "states.py import: record 'UNCHANGED_ORIGINAL' -> 'sheet | plain_table | state=current | (from plain_table.csv, version 1)', census has no 'to recheck'. docx_probe.py: 'in the Field -> kind: document | role: written document | state: current', tag 'WRITING', census '2 pages'. stale_on_disk.py after R: STALE_ORIGINAL -> 'recheck' ('1 to recheck'); ORIGINAL_UNAVAILABLE -> 'unavailable' with 'its source cannot be reached' and no recheck count. calc.py: PDF_SOURCE_REVIEW_REQUIRED and RECHECK_SHEET_CHANGED -> 'recheck' with stale wires. source_word() maps WORKING_COPY_OR_DERIVATIVE, UNCHANGED_NOTEBOOK_SNAPSHOT and CURRENT_PDF_SOURCE to current, and every *_UNAVAILABLE to unavailable.",
   "remains": "Nothing in the state mapping itself. Two new defects hide or delay these states (see regressions): the cached reading in field_page.py:83-85 and the membership test in field_source.py:159."
  },
  {
   "defect": "R2. A finding whose source changed shown as OPEN QUESTION with a solid wire; RECHECK unreachable for claims; wires doubled",
   "verdict": "partly",
   "observed": "states2.py both: 'AFTER the change -> finding | recheck | (supported \u00b7 needs your review) | stale flags [True, False]', census '5 findings, 1 open question, 4 to recheck'. states.py review: 'duplicate links: 12 distinct: 12'. probe_states.py (window): 'kind=finding state=recheck ... wires in: [(document:..., supports, True)]'. Role FINDING with no evidence stays a finding ('44 findings, 1 open question' with 60 bulk claims).",
   "remains": "A finding that stands on a CHECK of a sheet: when that sheet changes, the finding reads RECHECK but its wire stays solid and still says 'check passed'. checks2.py: record path [('CHECK','PASSED','counts=False')], Field 'state recheck | wires in: [(07 Limits Rev B CURRENT, check passed, solid)]'. Cause: workbench/field_source.py:239-243 sets stale only when outcome == 'STALE', which investigation.path never reports (it reports counts=False). This is the worked case's own finding 'The reviewed sheet keeps the 80 ms condition'."
  },
  {
   "defect": "R3. The three PDFs showed UNAVAILABLE although present; never-admitted items showed green CURRENT as 'admitted source'",
   "verdict": "closed",
   "observed": "base.py: all three PDFs 'state=current | role: admitted source' (unavail.py confirms the extractor fingerprint still differs on this machine, so the fix is real, not a changed environment). states2.py unadmitted: 'never_admitted_unreviewed.pdf | state: waiting | role: waiting for your review', 'never_admitted_held.pdf | state: held | role: held at review', REJECTED item absent. states.py revoke: the REVOKED PDF is absent, census '2 sources'.",
   "remains": "Nothing for sources. The sheet read from a revoked PDF disappears with it (see regressions)."
  },
  {
   "defect": "R4. The Field of one workspace showed every sheet in the owner's profile, each marked RECHECK",
   "verdict": "partly",
   "observed": "scope.py: empty second workspace, same profile -> 'title: \"\" | census: []', no sheets, no recheck. The worked case still shows its 3 reviewed sheets as current.",
   "remains": "In the profile's own Office workspace the same false alarm remains. scope2.py: \"OFFICE workspace (Office): census ['4 sheets', '1 page', '3 to recheck']\", with the three reviewed sheets of After Hours 07 each state='recheck', although nothing changed. Cause: workbench/field_source.py:148-159 lets every sheet belong when the root is the Office, and :168 takes the state from office.get asked through the Office kernel, which cannot see another workspace's PDFs and so answers PDF_SOURCE_REVIEW_REQUIRED."
  },
  {
   "defect": "R5. A stale condition card titled with a raw Python dict and called an OPEN QUESTION",
   "verdict": "closed",
   "observed": "cond.py: \"kind: condition | title: 'Total: 15 m' | state: recheck | facts: ('The words \u201c12 m\u201d now read \u201c14 m\u201d.',) | role: a total bound to the words of a page | fed by: ['Cable budget']\", census '1 open question, 1 total, 1 to recheck'; nothing shown while the card is CURRENT. probe_states.py: accessible description 'Total: 5 W. State: recheck. From Probe page.' Its staC line runs and returns the state and reason.",
   "remains": "Nothing. (A total sits in the column headed OPEN beside the open questions; it is not counted as one.)"
  },
  {
   "defect": "R6. A plain page and any unreadable record drawn green CURRENT; documents.get refused turned calculations into pages; refusals wrote journal/audit rows on every showing",
   "verdict": "partly",
   "observed": "Plain page: \"document | 07 Case conclusion \u00b7 HOLD | state=''\", description 'Page: 07 Case conclusion \u00b7 HOLD.' probe_refusal.py with 3 unreadable sheets: showing 1 'office.get asked: 3', showings 2 and 3 'office.get asked: 0', 'journal rows 182 -> 185, audit rows 60 -> 63 over three showings'; after another record was written 'office.get asked: 0'; R -> 'office.get asked: 3'. Sheets read \"state='not read' role='could not be read'\". win2 s9: status 'Field \u00b7 the sheets could not be read \u00b7 R looks again', 'Field \u00b7 3 records could not be read \u00b7 R looks again'; documents.get refused -> 3 pages 'not read'.",
   "remains": "(a) investigation.path refused: status says '5 records could not be read' but the four findings keep the green 'current' with no wires and nothing on them says 'not read' (unread2.py; workbench/field_source.py:220-227). (b) investigation.sheet refused: every finding of that investigation vanishes, 'objects that say not read: []' (field_source.py:211-213). (c) An unreadable sheet that nothing refers to is dropped, not drawn: status counts 3, the surface shows 2 (field_source.py:159-167). Not new: the synthetic malformed investigation.sheet (unresolved: None) still raises an uncaught TypeError, as it did at 63d9d2d."
  },
  {
   "defect": "R7. Past 100 pages the oldest (including the calculations) silently disappeared",
   "verdict": "partly",
   "observed": "limit.py: 'documents in the workspace: 113 | pages + calculations in the Field: 113', both calculations and the conclusion page shown. probe_real_scale.py: 108 documents all shown; 60 claims -> '44 findings' with note 'not shown: 20 more findings'. At 123 documents: \"shown: 120 | note: 'not shown: 3 more pages' | calculations: [] | conclusion shown: False\".",
   "remains": "Lists are paged and the count left out is said, so the stated expectation is met. But past 120 documents the ones dropped are still the oldest, which in the worked case are both calculations and the conclusion page; they are counted as '3 more pages' and their sheet loses its wires. Cause: workbench/field_source.py:182 applies the ceiling to documents.list rows by recency before documents.get can tell a calculation from a page."
  },
  {
   "defect": "R8. Showing the Field wrote journal rows for nested notebook.get / notebook.resolve / book.contents reads",
   "verdict": "closed",
   "observed": "probe_journal.py (worked case): 'FIELD shown 3 times ...: 2 differences', only engineering.sqlite3-shm/-wal appearing, no table row count changed. probe_office_kinds.py with a CSV sheet and a notebook copy present: the same 2 file differences only. book.py: \"three readings: nested reads seen: {'notebook.get': 3, 'notebook.resolve': 0, 'book.contents': 0} | journal/audit rows (187, 63) -> (187, 63)\". The three names were added to activity.OBSERVER_OPERATIONS (workbench/activity.py:12). Grep of the tree: no code, test, tool or doc reads the journal or audit by these names; they appear only where they are dispatched and in the registry.",
   "remains": "Nothing reproduced. notebook.resolve and book.contents could not be exercised here (the notebook had no references; office.from.book refuses with OFFICE_BOOK_UNAVAILABLE without an attached project); they go through the same suppression."
  },
  {
   "defect": "R9. User-visible strings named internal identifiers (operation names, raw exception text, 'revision <hash>', 'checked check_failed', doubled full stop)",
   "verdict": "partly",
   "observed": "Status line uses plain words (see R6); sheets say 'version 1'; open failure reads 'Field \u00b7 07 Bench readings could not be opened (office document unavailable)'; 'Finding: Both limit sheets list the pulse row. State: recheck. From ...' has single full stops; wire labels 'supports', 'check passed'.",
   "remains": "(a) A real check that does not hold (outcome CHECK_FAILED) is labelled 'check check failed' (checks.py; workbench/field_source.py:243 prefixes 'check ' to the outcome word; the investigation room says 'did not hold'). (b) A title ending in '?' still gets a stop: 'Open question: What stretched the startup pulse?. State: open.' This is the worked case's first selection (workbench/field_qt.py:90 strips only '. '). (c) New: unfinished jobs are titled with the tool name, e.g. 'references.verify' (see regressions)."
  },
  {
   "defect": "R10. Arrow keys could not reach a bridged column; a cycle pushed members far right under wrong headings; unknown kind raised KeyError in rank_title",
   "verdict": "closed",
   "observed": "reach.py: 'real case shape: unreachable by arrows: []', 'sources feed findings directly, sheets stand alone: unreachable: []', 'random forward-only fields with objects the arrows cannot reach: 0 of 3000'. cycle.py: \"ranks: {'pdf': 0, 's1': 1, 's2': 2, 'f': 3, 'q': 4}\", headings MATERIAL, TABLES, TABLES, FINDINGS, OPEN. crash.py with kind 'gadget' and with '': 'still alive after painting'. model_fuzz.py, 4000 random fields with backward wires, loops, duplicates and unknown kinds: unreachable 0, raise 0, dup 0, attention 0, place 0, rank_title 0.",
   "remains": "Nothing."
  },
  {
   "defect": "New: every FieldObject has a non-empty staC line and each runs through language.run with ok True (work face and network face)",
   "verdict": "closed",
   "observed": "base.py: 'work face: 14 objects, 0 without a line or refused'; 'network face: 13 objects, 0 without a line or refused'. stac_values.py: every line returns non-empty rows for its object, e.g. source -> [{name: 07_Bench_Readings.pdf, admission: ACCEPTED, bytes: 77439}], sheet -> [{source_state.state: CURRENT_PDF_SOURCE, origin.pdf.page_index: 0}], port 2024 -> [{process: null, local: 0.0.0.0, state: LISTEN}]. Kinds outside the worked case also ran ok: stale total, written document, imported sheet, 'not read' page, jobs.",
   "remains": "None refused on this machine. One synthetic case refuses: a program whose name contains '|' gives 'where process=a|b=c', refused with 'Unknown transform' (workbench/field_source.py:342-346 falls back only for names with a space)."
  }
 ],
 "regressions": [
  {
   "title": "A sheet whose original file changed on disk stays green CURRENT until R is pressed",
   "severity": "wrong-result",
   "reproduction": "tools/verify-reader/stale_on_disk.py (real window). Import ws/parts.csv, F9: 'record says UNCHANGED_ORIGINAL | Field shows state=current'. Esc, change the CSV on disk, F9: 'record says STALE_ORIGINAL | Field shows state=current ... census: [4 sheets]'. Only R gives \"state='recheck' ... '1 to recheck'\". The same after deleting the file: the Field keeps 'recheck' while the record says ORIGINAL_UNAVAILABLE, until R. At 63d9d2d every showing read the records again.",
   "where": "workbench/field_page.py:83-85 (the reading is reused whenever ledger.journal.status reports the same head; a file edited outside Graphite never moves the journal)",
   "suggested_fix": "Do not treat an unchanged journal head as an unchanged workspace for records whose state depends on files. Either read again on every F9 (143 ms in the worked case) while keeping only the skip list for unreadable records, or on a reused reading re-ask office.get for sheets with an origin.source path (an observer read, no journal row) and update their state."
  },
  {
   "title": "Sheets made in this workspace are missing from its Field: revoked-source sheet, notebook copy, file imported from outside the folder",
   "severity": "wrong-result",
   "reproduction": "tools/verify-reader/calc.py Rev_A: after intake.revoke of 07_Rail_Limits_Rev_A.pdf the record says PDF_SOURCE_REVIEW_REQUIRED for '07 Limits Rev A ARCHIVED', but census is '2 sources, 2 sheets ...' with no 'to recheck' and \"sheets of this case missing from the Field: ['07 Limits Rev A ARCHIVED']\". tools/verify-reader/scope2.py: an Office document copied from this workspace's notebook and a CSV imported from ~/Downloads through this workspace: 'notebook copy shown here: False | Downloads sheet shown here: False'; they appear only in the Office workspace. At 63d9d2d all were shown.",
   "where": "workbench/field_source.py:159 (belongs = office or referred or under the workspace folder or its PDF item is drawn), together with :123-124, which drops REVOKED/REJECTED items before that test",
   "suggested_fix": "Test PDF membership against every intake item id of this workspace, before the admission filter, so a sheet whose source was revoked stays and reads RECHECK. For sheets whose home cannot be told (imports from outside, notebook copies, blank sheets), record the workspace in the sheet's origin when it is made, or show them here; at the least put 'N sheets of your Office not shown here' in field.note so nothing is left out silently."
  },
  {
   "title": "A refuted finding carries the green CURRENT mark (it read HELD before the fixes)",
   "severity": "wrong-result",
   "reproduction": "tools/verify-reader/checks.py: add a FINDING with a check that refutes on failure, run investigation.continue. Record: path [('CHECK','CHECK_FAILED','OPPOSES',True)], evidence_state REFUTED. Field: \"finding | state 'current' | lines ('refuted',)\". On the sheet the false statement gets the same green mark and word as a supported finding; only the small fact line says 'refuted'. The reader at 63d9d2d mapped REFUTED to held.",
   "where": "workbench/field_source.py:226 (evidence in ('SUPPORTED', 'REFUTED') -> STATE_CURRENT)",
   "suggested_fix": "Give REFUTED its own state word ('refuted', drawn like held or in quiet ink, never the green mark) and keep STATE_CURRENT for SUPPORTED only."
  },
  {
   "title": "Unfinished jobs are titled with the tool's internal name and filed under CALCULATIONS",
   "severity": "rough-edge",
   "reproduction": "tools/verify-reader/jobs.py: the worked case's own job rows with only the state changed in the jobs.list answer (a real failing job cannot be made under the probe holds). Field: \"JOB title='references.verify' role='work Graphite holds' state='failed' ... column=CALCULATIONS\", likewise 'references.export', 'references.page'. Jobs were not in the reader at 63d9d2d.",
   "where": "workbench/field_source.py:269 (title = goal or tool; for tool jobs the goal is the tool name); workbench/field_model.py:175 (a mixed column takes RANK_TITLE by rank)",
   "suggested_fix": "Title a job in words (the goal when it is a sentence, otherwise a phrase for the tool such as 'Verify the sources') and keep the tool name for the staC line only; give the job column its own heading (WORK) when jobs share a rank with calculations, or rank jobs apart."
  },
  {
   "title": "Unreadable sheets that do not belong here are still counted: an empty workspace says '3 records could not be read'",
   "severity": "rough-edge",
   "reproduction": "tools/verify-reader/scope3.py with office_service.get raising OFFICE_RECORD_DAMAGED: \"empty second workspace census: [] | status sentence: '3 records could not be read' | drawn as not read: []\"; worked case: status counts 3, surface draws 2 ('07 Limits Rev A ARCHIVED' is dropped because nothing refers to it).",
   "where": "workbench/field_source.py:138-142 (every profile sheet is read and counted in reader.unread) against :159-167 (only sheets that belong are drawn); problems() at :292-293 counts all of reader.unread",
   "suggested_fix": "Count in problems() only the unread records that are drawn, or draw every unreadable sheet as 'not read' when its home cannot be told; do not report foreign sheets in a workspace that shows none."
  },
  {
   "title": "The status line keeps saying records could not be read after R has read them",
   "severity": "rough-edge",
   "reproduction": "tools/verify-reader/probe_refusal.py, last step: the sheets become readable, R is pressed, all three read 'current' and page.problem is '', but the status line still shows 'Field \u00b7 3 records could not be read \u00b7 R looks again' (it stays until its 9 s timeout). Same in win2.py s8/s10: \"Field \u00b7 Graphite's records are not available in this window\" stays after the records are back.",
   "where": "workbench/field_page.py:93 (a message is shown only when there is a problem; nothing clears the earlier one)",
   "suggested_fix": "When a reading ends with no problem, clear the status line if it still shows a Field message (host.statusBar().clearMessage(), or show nothing with the same call)."
  }
 ]
}