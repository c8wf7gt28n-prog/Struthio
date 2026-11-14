export const meta = {
  name: 'graphite-field-understand',
  description: 'Map the two parts of Graphite a new overview-and-detail desk must plug into: the window shell and the work-object data',
  phases: [
    { title: 'Map', detail: 'two readers: shell composition and theme; work objects, relationships and demo data' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const G = S + '/work/graphite'
const PY = S + '/work/venv/bin/python'

const BASE = `
CONTEXT
Graphite 0.2a13 is one owner's local-first desktop workspace (Python 3.13, PySide6 6.8.3) with a built-in assistant. Its tree is at ${G} (a working copy; 623 .py files; main package workbench/). The owner has asked for a NEW DESKTOP MODEL "like Lain's computer" (the layered, nocturnal machine from the anime Serial Experiments Lain), and their own master specification (sections 70-72) already asks for an "objects and instruments desktop" with "overview and detail without losing place": an overview that shows an assignment's real objects (sources, sheets, calculations, findings, unresolved conditions) and their relationships, and a detail view that is the real editor, with a simple Open / Back between them.
The orchestrator will DESIGN and WRITE the new view itself: a full-surface "field" page in the centre of the existing window that draws the current workspace's real work objects as layered sheets with relationship lines, and opens the real page for the selected one. Your job is only to produce an accurate, COMPACT map of the part of the codebase named below so that code can be written against it without re-reading everything. Every fact needs file:line. Do not design the feature. Do not write feature code.

HOW TO WORK (be economical — this map is worth more short and right than long)
- Use Grep first, then Read only the line ranges you need. Do not read whole large files (workbench/qt_app.py is several thousand lines).
- You may run small READ-ONLY probes with the project's interpreter to confirm a fact empirically, e.g. to list registered operations or print a result shape. Rules for probes: save the script under ${S}/tools/<your-label>/ ; run it as  QT_QPA_PLATFORM=offscreen ${PY} -B <script> ; set HOME, ARC1_WORKBENCH_CONFIG_HOME and ARC_LEDGER_CONCERN to a fresh temp directory inside the script BEFORE importing workbench (copy the pattern at ${G}/tools/desk_review.py lines 28-58, including the patches that hold Kernel.launch, Kernel.submit, clip._request and session_power.system); insert ${G} on sys.path; never write inside ${G}; no network; no jobs, models or workers started. A working example that builds the window offscreen and grabs it is ${S}/tools/capture/shot.py — reuse it.
- Do not modify anything under ${G}. No git. If something cannot be determined, say so in unknowns rather than guessing.
`

const MAP = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: '6-12 sentences: how this part works, in plain words' },
    facts: {
      type: 'array',
      description: 'The map. Each entry is one thing code can rely on.',
      items: {
        type: 'object',
        properties: {
          topic: { type: 'string' },
          fact: { type: 'string', description: 'Precise statement: class/function/attribute names, signatures, call order, values' },
          where: { type: 'string', description: 'file:line (relative to the tree root), several if needed' },
          confirmed_by: { type: 'string', enum: ['read', 'probe', 'both'] },
        },
        required: ['topic', 'fact', 'where', 'confirmed_by'],
      },
    },
    recipes: {
      type: 'array',
      description: 'Minimal working code patterns (10-30 lines each) the orchestrator can copy, each one actually run if it is a probe',
      items: {
        type: 'object',
        properties: { name: { type: 'string' }, code: { type: 'string' }, observed_output: { type: 'string' } },
        required: ['name', 'code', 'observed_output'],
      },
    },
    pitfalls: { type: 'array', items: { type: 'string' }, description: 'Things that will break or mislead someone adding a new page/operation here' },
    unknowns: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'facts', 'recipes', 'pitfalls', 'unknowns'],
}

const AREAS = [
  {
    key: 'shell',
    prompt: `${BASE}
YOUR AREA: the window shell, navigation and theme — everything needed to mount one new full-surface page in the centre and make it reachable.
Answer, with file:line:
1. In workbench/qt_app.py WorkbenchWindow: which attributes hold the centre (central_stack, tabs, home_page, finder …), how show_start() puts Home in front, how the window returns from Home to the previous work, and what the window calls on a centre page (any required methods/attributes a page must have, e.g. for focus, status, resizing, reduced motion). What does the Home page class (workbench/finder_qt.py FinderPage and the "Today" face with the art panel in shell2.py) do in its constructor and how does it get the host?
2. Where the top bar's Work / Programs / System menus are built (menus2.py, programs_qt.py, system_menu_qt.py) and the exact way an existing command is added to Work with a keyboard shortcut (show one real example end to end). Which shortcuts are already taken (list F-keys and Ctrl+digit / Ctrl+letter bindings found) so a free one can be chosen.
3. How a typed command or the Ctrl+K search reaches an action (the command catalogue / "shortcut catalogue"), so the new view can also be opened by typing. One real example.
4. Kernel operations: how an operation is declared (engineering_kernel.py CAPABILITIES/TOOLS, engineering_cli.py argument schemas, ledger_control.py ledger.* handlers) and dispatched (Kernel.dispatch(op, args, operator())). What the release check compares against docs/GRAPHITE_0.1_REGISTRY.json and what tools/record_registry.py rewrites — i.e. exactly what must be re-recorded if ONE read-only operation is added, and whether adding a pure-UI action (no new operation, no new setting) leaves the registry untouched.
5. Settings: how a setting is defined in settings_registry.py, how the art mode (Illustrated / ASCII / Clean) and reduced-motion preferences are stored and read by widgets (exact keys and accessor calls), and what adding a setting changes in the recorded registry.
6. Theme: every named colour in workbench/boss_theme.py with its hex value and stated meaning; the fonts and font helpers used for terminal lettering; any shared painter helpers (rules, panel ink, halftone) in boss_qt.py; how a widget is expected to style itself (stylesheet helper vs palette); where the art plates live and how ArtPanel picks and scales one. Note the project's rules that constrain a new view (static surfaces, no animation unless opt-in, art never in documents).
7. The exact, shortest way to (a) construct the window offscreen in a disposable home, (b) add a QWidget page to the centre and bring it to the front, (c) grab the window to a PNG at 1920x1200 and at 1366x768. Extend ${S}/tools/capture/shot.py into a recipe and RUN it with a trivial placeholder page (a QWidget painting one line of text) to prove the mount works; save PNGs under ${S}/work/shots/probe/ and report what happened.
8. Which tests_integrated modules and tools/check_*_ui.py checks would be affected by adding one page and one menu action (e.g. tests that count menu entries or assert every word is whole).`,
  },
  {
    key: 'objects',
    prompt: `${BASE}
YOUR AREA: the work objects and their relationships — the real data an overview would draw.
Answer, with file:line and, where you can, a probe that prints the real shape:
1. Inventory of work-object kinds that have a stable identity and a revision or state: documents/pages, sheets or tables, PDF or source-collection passages, calculations (exact, named cells with units), findings, conditions (unresolved / stale / recheck), investigations or assignments, retained methods, queued jobs. For each: the module that owns it, where it is stored (which SQLite table or file under the workspace's .ledger folder), and the Kernel operation(s) that LIST and READ it — operation name, required arguments, and the keys of the result. Prefer operations that already exist over reading the database directly.
2. Relationships between objects: how a "source relationship" / dependency / derived-from / stale-needs-recheck link is recorded and how to query all links for one project or assignment (operations or tables). Look at related.py, change_sets.py, conditions.py, documents.py, anything named source_binding / receipt / dependency / recheck, and the P07-P10 modules (evidence preparation, collections, reviewed PDF table to sheet to report).
3. The workspace/project scoping: what "root", "Concern", "Office", "project" mean in code; how the current project/assignment is known to the window (attribute names), and how to enumerate the objects that belong to it.
4. A real dataset to draw. ${S}/x/Graphite_After_Hours_07/After_Hours_07/ is a worked case exported from this program: read its START_HERE.md and Graphite_Backup/BACKUP.json, then determine the supported way to open it as a workspace (the README in ${G}/README.md documents "LEDGER.sh backup verify / restore … --to NEW_FOLDER"; find the Python entry behind it). RUN the restore into a new folder under ${S}/work/demo/ with the project interpreter (verify first), then, with a probe that opens that restored root through the Kernel, list what it contains by kind with counts and a few names, and list the relationship links among them (which source PDF feeds which sheet/calculation/finding). Report the exact commands used and the result. If restore is not possible, say exactly why and fall back to describing the SQLite tables (read-only) with row counts.
5. The data that ships in the tree for first use (examples/clock_lab, examples/thinkpad_first_run, the "first-run workshop"): which operation or function seeds a workspace with it, and what objects result.
6. For a small heads-up display: the call that returns machine readings (CPU, GPU, RAM, context "TXT") and the result of the network.observe operation (keys for interfaces and connections) — print a real sample (redact nothing sensitive is present; the container has no personal data).
7. How the window opens a given object in its real editor from code (the function to call with an object identity to bring its page to the front), for at least: a document page, a sheet/table, a PDF source passage, an investigation/journal.`,
  },
]

phase('Map')
const maps = (await parallel(AREAS.map(a => () =>
  agent(a.prompt, { label: `map:${a.key}`, phase: 'Map', schema: MAP }).then(r => r && ({ area: a.key, ...r }))
))).filter(Boolean)
log(`${maps.length}/${AREAS.length} maps returned`)
return { maps }
