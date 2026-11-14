export const meta = {
  name: "right-click-simple-and-chainable",
  description: "Map today's right-click, its chain machinery and the icon set; three independent designs for a simple, chainable right-click with icons; a judge merges them into one buildable plan",
  phases: [
    { title: "Read", detail: "three readers map the right-click, the chains and pipes, and the icons and the owner's past directions" },
    { title: "Design", detail: "three designers, each from a different angle" },
    { title: "Judge", detail: "one judge scores the designs against the code and merges the best into a build plan" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const REPO = "/home/user/Struthio"
const RULES = `
HARD RULES for you: the repository ${REPO} is READ-ONLY (do not edit, create or delete anything there); scratch files only
under ${S}/work/rightclick/. Another process is running timing-sensitive window checks on this machine right now: do NOT
start Qt, the window, tools/check_*_ui.py, probes or any heavy process. Reading files and small pure-Python scripts run
with python3 -I (for example ast walks over the source) are fine. Cite file:line for every claim about the code.`

const OWNER = `
The owner of Graphite (a local-first Python/PySide6 desktop workspace with an assistant, Kasandra in one appearance and
Stacy in the other) said today: "Also right click was too complex. We need to make its power easy to use and chain/pipe.
With right click icons too." Standing rules from the owner that every design must keep:
- No keyboard shortcut is printed anywhere (keys may still work; the Field's key card is the one place that lists them).
- Under the window there is a line language the window NEVER names; on screen a runnable thing is called "a line" and is
  shown on a royal-purple slab in the Kasandra appearance (boss_theme.line_sheet, ROYAL tokens); the code may keep its
  internal names.
- Icons are Graphite's own drawn glyphs (workbench/glyph_set.py GLYPHS, rendered by workbench/tool_faces.icon) in the
  theme's colours; menus2.py currently hides icons in the main menus (setIconVisibleInMenu) and turns other pictures one
  colour (paper_icon) unless a widget carries the property paperIcon.
- What changes something follows the assistant's hand rules (workbench/stacy_hand.py) and has an Undo where possible;
  nothing is silently applied; what cannot be undone always asks.
- Less scrolling: a menu must fit the screen; nothing should need scrolling (1920x1200 is the owner's screen; 1366x768
  must work).
- Mouse-first, and the keyboard still works.`

const READERS = [
  { key: "menu", prompt: `Map today's right-click menu (workbench/context_menu.py and what it imports: Entry, PROVIDERS, FINDERS,
SECTION_WORDS, entries_for, the menu builder, owns_menu/target_at, open_at, open_at_focus; command_context.py's "Inspect this
command"). For EVERY target kind it serves (a file or folder in Files and the Finder, a Field sheet, the Field's empty desk,
a document passage, a table cell or rows, a PDF page, a Log line, the console's output, Today/the empty place, a network
entry, menus and Programs rows, anything else) list: the sections in order, every entry's words, its kind, its icon key,
its operation, whether it is a submenu, and how deep the deepest submenu goes. Give totals: entries per target, sections per
target, maximum depth, entries that appear for several targets, entries that duplicate something one click away elsewhere,
entries that print a key, and which entries have an icon key and whether that icon is actually shown today (and why not).
Then say plainly what makes it complex, ranked, with numbers.` },
  { key: "pipes", prompt: `Map the machinery that already chains and pipes: workbench/chain_menu.py (the cascading menus that build
chains, "then" destinations console|sheet|watch|agenda|shell, the per-user menu file, parse_menu, kept chains, [stock]
methods), workbench/chain_workbench_qt.py (the chain tray: preview, sources, receipt, save sheet), the console's right-click
"carry on from the last answer" (workbench/console_qt.py), workbench/stac_words.py (words), the typed pipeline transforms
(sdk/cli/arc1cli/typed_pipeline.py: which transforms exist, their syntax, their limits: one source and at most seven
transforms), and how each kind of thing is addressed as a line's source (files @files:..., this, field.read, office, etc.;
context_menu.staC_for_file and friends). Answer: for each target kind the right-click serves, what line reads it today, what
steps could follow it (with the real values a step can offer, e.g. a column's values, counts per choice as chain_menu
already shows), what destinations a chain can end in, how a chain is previewed and kept, and what the model is or is not
needed for. Say what already works end to end with the model off, and what is missing for "right-click a thing, then pick
a next step, and a next, and end somewhere", with the files each missing piece touches.` },
  { key: "icons", prompt: `Two parts. (1) Icons: list every glyph in workbench/glyph_set.py GLYPHS and KIND with what it depicts
(read each draw function), how workbench/tool_faces.icon renders a glyph for a menu (colours per state, sizes, halo), how
tool_faces.dress(menu) attaches glyphs to menu lines by their words (its lookup table), and why the main menus hide icons
(menus2.py setIconVisibleInMenu, paper_icon). Propose a mapping from the right-click's verbs (open, show, ask, change,
copy, compare, trace, keep, export, run, pipe/next step, filter, count, sort, group, save as sheet, watch, add to agenda,
undo, inspect) to existing glyphs, and name any verb with no fitting glyph. (2) The owner's past directions about the
right-click and menus: read ${REPO}/RECORD_OF_DIRECTIONS.md, docs/RELEASE_NOTES_0.3*.md to 0.8.0, docs/GRAPHITE_DESK.md
(the D4 right-click sections), docs/DAILY_GUIDE.md "The right-click menu", and quote what the owner asked for and what was
promised (cascading menus that build chains, one home for each action, no white boxes, mouse-first, Apple-simple at rest).
Note anything that contradicts "make it simple".` },
]

const READ_PROMPT = (r) => `You are one of three readers preparing a redesign of the right-click menu in Graphite.
${OWNER}
${RULES}

Your part: ${r.prompt}

Return markdown, dense and specific, with file:line citations.`

const ANGLES = [
  { key: "verbs", prompt: `ANGLE: a few big verbs. The menu's first level is at most seven lines, each a verb with an icon,
the same verbs in the same order for every kind of thing (what does not apply is absent, not greyed), and the power lives
one level down. One of the verbs is the pipe: "Then ›" (or a better word) which offers the next steps for this thing with
real values and counts, and each chosen step offers the next, ending in a destination.` },
  { key: "pipe", prompt: `ANGLE: the right-click is a pipe builder. Right-click a thing and a small panel (not a deep menu) opens
at the pointer: the thing at its left, the next steps as icon chips with counts, and the line being built shown on its
royal-purple slab with a live preview (row count, first rows) and the destinations at its right end (show, sheet, note,
watch, agenda, keep as a word). Each click adds a step; Backspace or a click on a step removes it. Ordinary actions (open,
copy, rename, delete) stay in a short row at the top.` },
  { key: "learn", prompt: `ANGLE: progressive disclosure and teaching. At rest the right-click shows only the 3 to 5 things most
used for this kind of thing (learned from use, with a fixed sensible default), each with an icon; one "More" opens the rest
grouped by verb; and every action shows, in the menu's foot, the line it would run, so a person learns the pipe by using
the menu, and can carry it on ("and then…") into a chain. Chains you build can be kept and then appear at rest for that kind
of thing in this project.` },
]

const DESIGN_PROMPT = (a, notes) => `You are one of three designers proposing a simpler, chainable right-click menu with icons
for Graphite.
${OWNER}
${RULES}

The readers' notes (read them; verify in the code what you rely on):
${notes}

${a.prompt}

Deliver: (1) the design, concretely, for each kind of thing the right-click serves today, with the exact first-level lines
and their icons, and what one level down holds; (2) how chaining works step by step, with a worked example on the After Hours
07 workspace (e.g. right-click the sheet "07 Bench readings": filter rows, count, save as a sheet) and one on a CSV file in
Files, with what is shown at each step (counts, preview) and the line built; (3) how nothing is lost: map every entry of
today's menus (from the reader's inventory) to where it lives in the new design, or say it is dropped and why; (4) the build
plan: files, functions, what is reused (Entry, PROVIDERS, chain_menu, tool_faces.icon, line_sheet), what is new, and the
tests (exact assertions) that prove it, including a count of first-level lines per target and a check that no line prints a
key; (5) risks. Be honest about what is hard. Markdown.`

const JUDGE = (notes, designs) => `You judge three designs for a simpler, chainable right-click with icons in Graphite and merge
the best into one plan that can be built in one or two sessions.
${OWNER}
${RULES}

Readers' notes:
${notes}

Designs:
${designs}

Score each design 1-10 on: simplicity at rest (what a person sees first), power reachable (nothing lost), chaining (how easy to
build and see a pipe), honesty with the code (does it rely on things that exist; verify a few in the code), keeping the
owner's rules, and buildability. Then write THE plan: the first-level lines per kind of thing with icons; the chain/pipe
interaction; where every current entry goes; the files and functions to change or add; the tests with exact assertions;
and a first slice small enough to build and verify in one session, plus what follows. Finish with the three questions, at
most, that only the owner can answer. Markdown.`

const notesArr = await parallel(READERS.map(r => () => agent(READ_PROMPT(r), { label: "read:" + r.key, phase: "Read" })))
const notes = READERS.map((r, i) => "## Reader: " + r.key + "\n\n" + (notesArr[i] || "(this reader did not return)")).join("\n\n")
const designsArr = await parallel(ANGLES.map(a => () => agent(DESIGN_PROMPT(a, notes), { label: "design:" + a.key, phase: "Design" })))
const designs = ANGLES.map((a, i) => "## Design: " + a.key + "\n\n" + (designsArr[i] || "(this designer did not return)")).join("\n\n")
const plan = await agent(JUDGE(notes, designs), { label: "judge", phase: "Judge" })
return { notes, designs, plan }
