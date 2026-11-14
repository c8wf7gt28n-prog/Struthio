export const meta = {
  name: 'graphite-field-review',
  description: 'Two independent reviewers try to break the new Field overview: one on behaviour and edge cases, one on the project rules, scale and accessibility',
  phases: [
    { title: 'Review', detail: 'behaviour and edge cases; rules, scale and accessibility' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const R = '/home/user/Struthio'
const PY = S + '/work/venv/bin/python'

const BASE = `
CONTEXT
${R} is the git checkout of Graphite 0.2a13 (Python 3.13, PySide6 6.8.3; a local-first desktop workspace). Commit aa0ce07 is the program as delivered. Commits f7f0a5e and 63d9d2d add a new overview called the Field (owner's master specification, sections 70-72, "overview and detail without losing place"; owner's wish: a desk "like Lain's computer"). See it with:  git -C ${R} diff aa0ce07 63d9d2d --stat   and   git -C ${R} diff aa0ce07 63d9d2d
New files: workbench/field_model.py (objects, links, layout, keyboard moves; no Qt), workbench/field_qt.py (the painted view), workbench/field_source.py (reads real records through Kernel.dispatch and derives the links), workbench/field_page.py (mounts the view in the window's centre; show_field / leave_field / back / open_object). Edited: workbench/qt_app.py (show_field, and _close_start / show_start / update_document_info know about the Field), workbench/menus2.py (one QAction "Field" on F9, in the Arrange menu after Today), workbench/activity.py (office.list and office.get added to OBSERVER_OPERATIONS).
A capture harness that builds the REAL window offscreen on a disposable copy of a restored worked case ("After Hours 07": 3 PDFs, 3 sheets, 2 calculation reports, 1 page, 4 findings, 1 open question) is ${S}/tools/field/window.py — run it as:  cd ${S}/work && ${PY} -B ${S}/tools/field/window.py ${R} <an output folder you create under ${S}/tools/<your-label>/> 1920 1200     (add a 5th argument "empty" for an empty workspace). It applies the project's usual holds (no worker launch, no job submission, no provider request, no session or power command, no child process). Copy and adapt it for your own probes.

RULES
- You are a reviewer. Do NOT edit anything under ${R} and do not commit. Write your own probe scripts under ${S}/tools/<your-label>/ and run them with ${PY} -B. Never run python with its working directory inside ${R} unless a project tool requires it; if you run a project tool that writes captures, point it elsewhere or remove what it wrote (leave  git -C ${R} status --short  empty).
- Keep the holds in every probe (copy them from the harness). No network. Do not start jobs, models or workers.
- Report only defects you have CONFIRMED by running something or by an unambiguous reading of the code, each with a concrete reproduction (inputs or steps, what happened, what should have happened) and the file:line to change. Do not report style opinions, missing tests, or things already stated as known limits below. Rank by how much it would hurt the owner.
- Known and accepted for this slice (do not report): wires that span several columns pass under the sheets between; the PDF opener needs a child process and a job, so it cannot be exercised under the holds; MANIFEST.json and the seed are not rebuilt yet; no new automated tests were added (owner's rule: no new test suites).
- Be economical: read the diff first, then probe the specific risks. Stop when you have covered your list.
`

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: '3-6 sentences: is this safe to keep building on, and what is the worst thing you found' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['breaks-work', 'wrong-result', 'rough-edge', 'rule-conflict'] },
          reproduction: { type: 'string', description: 'Exact steps or script, and the observed output' },
          expected: { type: 'string' },
          where: { type: 'string', description: 'file:line' },
          suggested_fix: { type: 'string' },
          confirmed_by: { type: 'string', enum: ['ran-it', 'read-it'] },
        },
        required: ['title', 'severity', 'reproduction', 'expected', 'where', 'suggested_fix', 'confirmed_by'],
      },
    },
    checked_and_fine: { type: 'array', items: { type: 'string' }, description: 'Risks you probed that held up, one line each with how you checked' },
    could_not_check: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'defects', 'checked_and_fine', 'could_not_check'],
}

const LENSES = [
  {
    key: 'behaviour',
    prompt: `${BASE}
YOUR LENS: behaviour and edge cases. Try to break it.
1. Model (field_model.py), with plain Python probes: cycles in links (A feeds B feeds A), self-links, links to missing ids, duplicate ids, empty field, one object, 200 objects in one column, 12 ranks; does _ranks terminate and stay bounded; does place() ever return overlapping sheets, negative or NaN sizes, or sheets outside the given width at widths 300, 600, 814, 1368, 3000 and scales 0.85, 1.0, 1.4, 2.0; do move('left'|'right'|'up'|'down'), next_attention and first() always land on an existing object and never raise; is depth() correct for a selection with no links.
2. View (field_qt.py), offscreen: paint with each of the above models at several sizes without exceptions; very long titles, titles with no spaces, non-Latin text, empty titles, 40 fact lines; mouse click and double-click hit-testing while scrolled; wheel scroll bounds; keyboard: arrows, Home, Tab/Shift+Tab with and without waiting objects (can focus leave the Field with Tab when nothing waits? can the owner get stuck?), Enter with nothing selected, Escape.
3. Window integration (field_page.py, qt_app.py) in the real window via the harness: open the Field from the work and from Home; Esc back to each; open the Field twice; open a room while the Field is in front (Files, Today via its action, Documents) and confirm the workspace or Home really is in front and the Field flag is cleared; close the last tab while the Field is showing; resize the window while it is showing; change the art mode setting (session.state['desk_art'] = 'clean') and refresh; call show_field when host.ledger_bridge is missing; a reader operation that raises or returns ok False (patch Kernel.dispatch for one operation) — does the Field still show the rest and say so; does opening an object whose record was deleted since the Field was drawn fail politely; does the window title and the docks/context bar state return exactly to what it was before the Field was shown (compare saveState and visibility before and after).
4. Reader (field_source.py) against the real case: are any links wrong or missing compared with what the records say (use the operations yourself: office.get origin, documents.get derivation, investigation.sheet/path); is any object given a state the record does not support (in particular: sources shown as "unavailable", claims, the plain page); does a second investigation in the same workspace produce a sensible title; are link directions right (source feeds target).`,
  },
  {
    key: 'rules-scale',
    prompt: `${BASE}
YOUR LENS: the project's own rules, scale, and accessibility.
1. Journal and side effects: the Field's docstrings claim it writes nothing and fills no timeline. Verify on a copy of the worked case: snapshot the workspace's activity journal (and the audit table) row counts and the files under the workspace and profile before and after showing the Field three times; report every write caused by showing it. Check that adding office.list / office.get to activity.OBSERVER_OPERATIONS (workbench/activity.py) does not remove an event something else depends on: grep for readers of the journal that key on those names, and run tests_integrated modules that touch activity or office (one module per process:  cd ${R} && QT_QPA_PLATFORM=offscreen ${PY} -B -m unittest tests_integrated.<module>  ) comparing against the same module run on a pristine export of aa0ce07 (make one with  git -C ${R} archive aa0ce07 | tar -x -C <a new folder under ${S}/tools/<your-label>/>  ).
2. The one-dispatcher rule: confirm every read in field_source.py goes through Kernel.dispatch with the owner's principal and that none of the operations it calls is a write, starts a job or a child process (read each operation's handler). Confirm the registry is untouched: run  cd ${R} && QT_QPA_PLATFORM=offscreen ${PY} -B tools/check_release.py  and report the registry, settings and adapters sections (the runtime section is expected to fail on unpackaged sources).
3. The menus contract: tools/check_explore_ui.py and tools/check_navigation_ui.py assert that menus2.rebuild keeps QMenu and QAction identities across rebuilds; run those two checks on the pristine export and on ${R} (set their capture directory environment variable to a folder of yours; read the top of each file for its name) and report any difference in outcome. Is F9 really free (search the tree for other bindings of F9, including widget-local shortcuts and the game)? Does the Field action appear exactly once in Arrange after two rebuilds?
4. Scale: build a synthetic workspace through the reader's own interface (do not write to the database: wrap a fake kernel object whose dispatch returns 300 sheets, 300 documents of which 150 have derivations, 3 investigations with 60 claims each) and measure read_field time, Field construction time, place() time and one paintEvent at 1368x1010; report numbers. Then, on the real Kernel and the worked case, count how many Kernel.dispatch calls one refresh makes and how long it takes; say what a workspace with 500 sheets would cost and whether the UI thread would stall.
5. Accessibility and reading sizes: does the view keep text whole and readable at interface text sizes 14, 18, 20 and 28 pt (the project's tools/ui_fit.py whole_words / cut_lines helpers work on real widgets, not painted text — say so if they cannot see it, and check by rendering); is everything reachable and operable by keyboard alone; is there an accessible name and a description that changes with the selection; is colour ever the only signal (check each state mark and the stale wire); does the view respect the Clean art mode and avoid animation/timers entirely (grep for QTimer, QPropertyAnimation, startTimer in the four new files).
6. Wording: the project forbids the words Ledger, Slate and Hatch in user-visible strings of frame modules and "Ledger & Slate" anywhere in workbench literals (tests_integrated/test_graphite.py). Run that test module on both trees and report any NEW failure; list any user-visible string in the four new files that names an internal identifier the owner should not have to read.`,
  },
]

phase('Review')
const reviews = (await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }).then(r => r && ({ lens: l.key, ...r }))
))).filter(Boolean)
log(`${reviews.length}/${LENSES.length} reviews returned`)
return { reviews }
