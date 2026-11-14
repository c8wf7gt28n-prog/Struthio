export const meta = {
  name: 'graphite-field-verify-fixes',
  description: 'Re-run the reviewers\' reproductions against the fixed 0.3 side copy and report which defects are closed, which remain, and what the fixes broke',
  phases: [
    { title: 'Verify', detail: 'one verifier per defect family: the reader; the window, view and keyboard' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const WT = S + '/work/wt'
const PY = S + '/work/venv/bin/python'

const BASE = `
CONTEXT
Graphite is a Python 3.13 / PySide6 desktop workspace. A new overview called the Field was reviewed at commit 63d9d2d in /home/user/Struthio by two reviewers, who confirmed the defects listed below with runnable probes. The author has since fixed them in a SIDE COPY at ${WT} (a git worktree, not yet committed; see what changed with  git -C ${WT} diff 63d9d2d --stat  and read the four Field modules there: workbench/field_model.py, field_qt.py, field_source.py, field_page.py). Your job is to VERIFY THE FIXES against ${WT}, not to review from scratch.
The reviewers' probes are in ${S}/tools/edge/ and ${S}/tools/rules-lens/ (each has a common.py). They point at /home/user/Struthio (edge: a hard-coded PROGRAM in common.py; rules-lens: the PROBE_PROGRAM environment variable) and they were written for the OLD interfaces. Copy the probes you need into a new folder of your own under ${S}/tools/<your-label>/ and adapt the copies:
  - point PROGRAM at ${WT};
  - read_field(kernel, principal, title='', skip=()) and read_network(kernel, principal) now return (Field, reader); reader.refused is a list of (operation, reason) for whole lists that did not answer, reader.unread is a list of record ids that could not be read; page.refused is gone (page.problem is the sentence shown to the owner, page.unread the remembered ids);
  - Field.place(width, height, scale, sheet_h, least_w) now returns (placements, surface_width, surface_height); the view has scroll_x and scroll_y instead of scroll;
  - Tab no longer walks waiting objects: the key is A (Shift+A backwards); new keys S (the selected object's staC line goes to the writing strip) and Shift+Enter (run it); PageUp/PageDown/End exist;
  - states: '' means no state (a plain page); 'not read' and 'unavailable' are quiet words; sources take their state from their admission.
Run probes as:  cd ${S}/work && ${PY} -B <your copy>   . Keep the holds the probes already apply (no worker launch, no job submission, no provider request, no session or power command, no child process). NEVER run tests_integrated.test_model_settings outside an isolated process namespace: on the delivered tree it signals real processes. If you must run any tests_integrated module, run it as  unshare --pid --fork --mount-proc --kill-child ${PY} -B -m unittest tests_integrated.<module>  from inside ${WT}.
staC note: staC lines (language.run) only run when the program's sources match its seed. ${WT} was rebuilt (tools/package_graphite.py --manifest-only) after the last edit, so they run there. Do NOT edit anything under ${WT} or /home/user/Struthio and do not commit; write only under ${S}/tools/<your-label>/.

For EACH defect in your list: re-run the original reproduction (adapted), and return verdict closed (the bad behaviour is gone and the expected behaviour is observed), partly (say what remains), open (still reproduces), or cannot-tell (say why). Quote what you observed. Then report any NEW defect the fixes introduced that you actually reproduced (regressions), ranked by how much it would hurt the owner. Be economical: adapt and run, do not re-review the design.
`

const RESULT = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: '3-6 sentences: are the fixes real, and is anything important still wrong' },
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          defect: { type: 'string' },
          verdict: { type: 'string', enum: ['closed', 'partly', 'open', 'cannot-tell'] },
          observed: { type: 'string', description: 'What the adapted reproduction printed or showed' },
          remains: { type: 'string', description: 'For partly/open: exactly what is still wrong and where (file:line)' },
        },
        required: ['defect', 'verdict', 'observed', 'remains'],
      },
    },
    regressions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['breaks-work', 'wrong-result', 'rough-edge', 'rule-conflict'] },
          reproduction: { type: 'string' },
          where: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
        required: ['title', 'severity', 'reproduction', 'where', 'suggested_fix'],
      },
    },
  },
  required: ['summary', 'verdicts', 'regressions'],
}

const FAMILIES = [
  {
    key: 'reader',
    prompt: `${BASE}
YOUR LIST: the reader (workbench/field_source.py) and the model (workbench/field_model.py).
R1. Unchanged imported sheets (UNCHANGED_ORIGINAL) and working copies were marked RECHECK forever; an Office row of kind 'document' was drawn as SHEET. (edge/states.py import, edge/docx_probe.py, rules-lens/probe_office_kinds.py) Expected: unchanged or source-less sheets read current; only STALE_* / *_REVIEW_REQUIRED ask for a recheck; *_UNAVAILABLE read unavailable; a written document is not called SHEET.
R2. A finding whose source changed was shown as an OPEN QUESTION with a solid wire; RECHECK was unreachable for claims; wires were doubled. (edge/states2.py both, edge/states.py review, rules-lens/probe_states.py) Expected: the finding stays a FINDING, reads RECHECK, is counted in 'to recheck', its wire from the changed source is dashed/stale, each wire appears once, only role QUESTION is an open question.
R3. The three PDFs of the worked case showed UNAVAILABLE although their originals are present; never-admitted items (UNREVIEWED, HELD, REJECTED) showed green CURRENT as 'admitted source'. (edge/reader.py field, edge/unavail.py, edge/states2.py unadmitted) Expected: state follows admission; rejected/revoked are not sources.
R4. The Field of one workspace showed every sheet in the owner's profile, each marked RECHECK. (edge/scope.py) Expected: an empty workspace shows no foreign sheets and raises no recheck alarms.
R5. A stale condition card was titled with a raw Python dict and called an OPEN QUESTION. (edge/cond.py, rules-lens/probe_states.py) Expected: title is the result's text, the record's reason is its fact line, it has its own kind/tag and is not counted as an open question.
R6. A plain page, and any record that could not be read, was drawn with the green CURRENT mark; with documents.get refused the calculations turned into pages and their wires vanished; refusals wrote journal/audit rows on every showing. (edge/reader2.py, edge/win2.py s9, rules-lens/probe_refusal.py) Expected: a plain page has no state; an unreadable record says 'not read' and is not asked again on the next showing until the owner presses R; the status line uses plain words, not operation names.
R7. Past 100 pages the oldest (including the calculations) silently disappeared. (edge/limit.py, rules-lens/probe_real_scale.py) Expected: lists are paged, and if a ceiling applies the Field says how many are not shown.
R8. Showing the Field wrote journal rows when an Office document was copied from a notebook (nested notebook.get / notebook.resolve / book.contents reads). (rules-lens/probe_office_kinds.py, rules-lens/probe_journal.py) Expected: showing the Field adds no journal or audit rows in the worked case and in the notebook case. Also confirm nothing in the tree keys on those three operation names in the journal.
R9. User-visible strings named internal identifiers (operation names in the status line, raw exception text, 'revision <hash prefix>' on sheets, 'checked check_failed' with an underscore, a doubled full stop in the accessible description).
R10. Arrow keys could not reach a column that wires bridged over (edge/reach.py); a cycle pushed its members to the far right under wrong headings (edge/cycle.py); an unknown kind raised KeyError in rank_title (edge/crash.py note).
Also check, since they are new: every FieldObject of the worked case has a non-empty .stac line and EVERY one of those lines actually runs through kernel.dispatch('language.run', {'text': line}, operator()) with ok True (list any that are refused, with the reason); the same for the network face objects.`,
  },
  {
    key: 'window',
    prompt: `${BASE}
YOUR LIST: the window, the painted view and the keyboard (workbench/field_page.py, field_qt.py, qt_app.py, context_menu.py, arc_desktop.py, boss_qt.py).
W1. Enter or double-click on a sheet whose tab was already open did nothing; the Field stayed in front. (edge/win2.py s11) Expected: Enter always shows the sheet, for sheets, pages and findings, whether or not the tab exists, and also when another tab is in front.
W2. Place was lost on return: the kept selection was scrolled out of view after F9, and a first selection below the fold was never revealed. (edge/win3.py place, rules-lens/probe_view.py part 2) Expected: the selected sheet is on screen whenever the Field is shown, refreshed or resized.
W3. Below about 1200 px window width, and from 18 pt text on a 1366x768 screen, columns were cut off with no way to reach them, most words were cut and fact lines vanished. (edge/win3.py resize, rules-lens/probe_access.py) Expected: sheets keep a readable size; the surface scrolls both ways; the selection is revealed horizontally too; report the share of strings still elided at 14, 18, 20 and 28 pt at 1920x1200 and 1366x768, and whether every sheet can be brought on screen by keyboard alone.
W4. Text on receded sheets and the stale wire fell below 4.5:1 contrast. (rules-lens/probe_view.py part 4) Expected: lettering on a sheet three steps away is at least 4.5:1; a stale wire far from the selection is clearly visible. Measure again.
W5. On a narrow sheet recheck, open and held shared one mark and 'unavailable' differed only by colour. Expected: each state has a mark different in shape.
W6. While anything waited, Tab and Shift+Tab never left the Field. Expected: Tab leaves; A / Shift+A walk what waits; PageUp, PageDown, End and Home work.
W7. After Esc back to a page or a sheet the keyboard focus was on the tab container and typing went nowhere. (edge/win5.py typing) Expected: typing continues in the page.
W8. Ctrl+W on the Field closed the hidden current tab while the Field stayed in front. (edge/win7.py, edge/win8.py) Expected: the workspace comes forward when its current tab changes.
W9. Opening the Field twice from Home forgot Home (Esc landed in the work); F9 while showing re-read everything. (edge/win1.py S3) Expected: Esc returns to Home; a second F9 reads nothing.
W10. A long title without spaces froze every repaint (0.64 s at 1000 characters, 15.7 s at 3000). (edge/view.py) Expected: paint time does not follow title length. Measure again.
W11. An exception inside paintEvent ended the program with a segmentation fault. (edge/crash.py) Expected: contained.
W12. With no kernel the Field said 'nothing in the field yet' and the status line said nothing. (edge/win2.py s8) Expected: the owner is told the records could not be read.
W13. Choosing the Clean desk while the Field was showing left its scan texture on. (rules-lens/probe_access.py part C) Expected: Clean takes effect at once; also the portrait rail disappears in Clean and ASCII.
Also check, since they are new, in the real window on the worked case (a capture harness that already does most of this is ${S}/tools/field/window.py, window_net.py and window_menu.py; run them with  cd ${S}/work && ${PY} -B ${S}/tools/field/window.py ${WT} <your out folder> 1920 1200 ): (a) Stacy's portrait rail appears in the Illustrated desk at 1920x1200, never overlaps a sheet or a wire end, and gives way at 1366x768; (b) the rail shows the selected sheet's staC line, S puts exactly obj.stac in the writing strip without leaving the Field, Shift+Enter runs it (console.last_program equals obj.stac) with the Field still in front and the keyboard still in the Field; what happens with Shift+Enter when the staC line is refused; (c) right-click / Menu key menu on a sheet lists Open, What feeds it, What it feeds, Inspect in the line, Run its staC, Ask Graphite about this, Copy its name, and the empty-place menu works on both faces; (d) entering and leaving the Field still restores the window's title, dock state and bars exactly (compare saveState before and after), including after Shift+Enter opened the working area; (e) with the interface text size at 28 pt nothing raises.`,
  },
]

phase('Verify')
const results = (await parallel(FAMILIES.map(f => () =>
  agent(f.prompt, { label: `verify:${f.key}`, phase: 'Verify', schema: RESULT }).then(r => r && ({ family: f.key, ...r }))
))).filter(Boolean)
log(`${results.length}/${FAMILIES.length} verifications returned`)
return { results }
