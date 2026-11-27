export const meta = {
  name: 'graphite-design-panel',
  description: 'Three independent designs of the Graphite 1.1 desktop from the owner\'s brief (Windows function, Apple grace, Linux freedom), judged by three lenses, then one synthesis',
  phases: [
    { title: 'Design', detail: 'three designers, each a whole desktop from a different starting point' },
    { title: 'Judge', detail: 'the owner\'s hands, a design critic, the engineer who must build it' },
    { title: 'Synthesize', detail: 'one design direction from the winner and the best grafts' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const REPO = '/home/user/Struthio'
const OUT = S + '/work/dist/design'

const BRIEF = `
THE PROGRAM. Graphite is a desktop for Debian 13: a PySide6 window that IS the session (a supervisor keeps it alive over a hidden Fluxbox on X11; apps run in sessions of their own; a slim dock lists app windows). Version 1.0 was released yesterday. Its window has five places: the head (HALT upper left, eight menus, Apps upper right), the left (tabs Files / Machine / Settings; the file tree from "This computer /"; DELETE, the bin, at the foot), the centre (the "bulletin board": the selected thing in the middle with what it is connected to around it, sized by relevance; working views, tabs, a two-pane split), the right (Kasandra's column: Kas is an AI agent USER of the system who plans tasks from registered tools, asks for each permission in plain words, and marks a step done only when verified; no picture of her), and the foot (one line: Line / Terminal / Search / Web / Log, and meters CPU GPU RAM TXT NET). Four looks: Day (launch), Night, Graphite, Kasandra.

THE OWNER'S BRIEF FOR 1.1 (verbatim, 27 Nov 2026): "this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know I can only get what I want in Debian so I have to switch." And: "Feel free to change anything under the hood and anything visible. Think the functionality of windows, with the graceful class of Apple, and the freedom power of Linux". The goal of 1.1 is a distribution-ready desktop. NOTHING on screen is fixed any more: layout, wording, keys, the looks, what exists at all.

WHAT STAYS (the builder's own choice, not negotiable in your design): Kas's authority rules (the model proposes, the desk disposes; every change waits for the owner's press or a grant shown in plain words; a step is done only when verified; HALT stops all of her work and nothing else); everything stays on the computer; every meaningful colour also has a word or a shape. The toolkit is PySide6 on X11 with Fluxbox hidden underneath; it must be buildable by separate agents in slices within a day or two, on top of the existing code (${REPO}/workbench/).

READ BEFORE YOU DESIGN: ${REPO}/wip/2026-11-26_road_to_1.0/DESIGN_DIRECTION_1.0.md (the 1.0 direction and its design tokens), ${REPO}/docs/GUIDE_LIVING_DESKTOP.md and GUIDE_KASANDRA.md (what exists), ${REPO}/docs/RELEASE_NOTES_1.0.md ("What 1.0 does not do yet"), the walkthrough accounts ${REPO}/wip/2026-11-26_b100_saved/X3.account.md and X4.account.md (what everyday and power-user sessions really met). LOOK at the finished screens: the PNG frames in ${S}/work/b100/D2/atlas/frames/ (read at least d2_board_day_1920x1200.png, d2_board_night_1920x1200.png, d2_split_day_1920x1200.png, d2_her_column_day_1366x768.png, d2_apps_day_1920x1200.png, d2_machine_day_1920x1200.png, d2_settings_day_1920x1200.png, d2_dock_day_1920x1200.png, d2_working_view_day_1366x768.png) and ${S}/work/b100/L6c/frames/l6c_1_chosen_48_day_1920x1200.png. An audit of functional gaps (packaging, tests, missing system pages, security) runs beside you: you design the EXPERIENCE, not the gap list.

RULES FOR YOU: read only; never edit ${REPO}; do not run the program; write only under ${OUT}/. The owner's personal details are not in the tree and must not be sought.
`

const PROPOSAL_SCHEMA = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    one_line: { type: 'string' },
    layout: { type: 'string', description: 'the places on screen and each one\'s job, in under 150 words' },
    signature_moves: { type: 'array', items: { type: 'string' }, description: 'the 5 to 8 ideas that make this design itself' },
    windows_function: { type: 'array', items: { type: 'string' } },
    apple_grace: { type: 'array', items: { type: 'string' } },
    linux_freedom: { type: 'array', items: { type: 'string' } },
    kas_presence: { type: 'string', description: 'where Kas lives, how her work is seen, how she is present with no picture' },
    keyboard: { type: 'string', description: 'the key map in brief, and whether keys are shown on screen' },
    removals: { type: 'array', items: { type: 'string' }, description: 'what exists in 1.0 and goes' },
    reverses_owner_decisions: { type: 'array', items: { type: 'string' }, description: 'explicit earlier decisions of the owner this design reverses (HALT upper left, no picture of Kas, DELETE as the bin\'s word, no key printed on screen, the tree from the root, Apps never Programs ...), each with the reason' },
    slices: { type: 'array', items: { type: 'string' }, description: 'the build slices, each one line with the files it mostly touches' },
    risks: { type: 'array', items: { type: 'string' } },
    file: { type: 'string', description: 'path of the full proposal you wrote' },
  },
  required: ['name', 'one_line', 'layout', 'signature_moves', 'windows_function', 'apple_grace', 'linux_freedom', 'kas_presence', 'slices', 'file'],
}

const LENSES = [
  { key: 'familiar', title: 'Familiar first',
    angle: `START FROM THE OWNER'S HANDS. A person who has used Windows and DOS for decades sits down: where do their eyes and fingers go in the first minute, the first day, the first week? Begin with what must simply be where they expect it (a taskbar with running apps and a clock, a Start-like launcher on the Windows key, an Explorer that behaves like Explorer, a tray for volume / network / battery, Alt+Tab, right-click > Properties, a Control Panel, a Task Manager, DOS words in the Terminal), then make every one of those GRACEFUL (Apple's restraint, typography, motion) and OPEN (Linux: each thing also reachable as a command, scriptable, replaceable). Do not clone Windows: keep what it does, drop how it looks. Decide where the bulletin board and Kas live in such a desktop.` },
  { key: 'calm', title: 'Calm first',
    angle: `START FROM GRACE. Ask what the fewest elements on screen are for this to be a whole computer, as Apple's best work would: one bar, one launcher-and-search field that does everything (apps, files, settings, commands, questions for Kas), content first, chrome that appears when summoned and leaves when done, one type scale, real hierarchy, meaningful motion, generous space, nothing that shouts. Then prove a Windows person loses NOTHING they rely on (every Windows function has a place, and their keys work), and that the Linux power is one gesture away (a terminal that drops down, every action showing the command behind it). Decide what the board and Kas become when the screen is this quiet.` },
  { key: 'power', title: 'Power first',
    angle: `START FROM FREEDOM. On Linux everything is a file, a command, a pipe; nothing is hidden and everything can be recombined. Graphite already has "lines" (pipelines over the desk, exact maths with receipts) and a kernel of named operations. Design the desktop where EVERY visible thing is a view onto something the owner can also type, script, bind to a key, schedule or hand to Kas: a command palette over all operations, panels that are saved lines, a Terminal that speaks DOS and shows the Debian command it ran, user-made tools on the launcher, the whole configuration in readable files, workspaces and tiling for people who want them. Then give it Windows' completeness (nothing a Windows user needs is missing or hard to find, with the mouse alone) and Apple's finish (the power never looks like a cockpit). Decide what the board and Kas become in such a desktop.` },
]

phase('Design')
const proposals = (await parallel(LENSES.map(l => () =>
  agent(`${BRIEF}
YOU ARE ONE OF THREE DESIGNERS working independently; you will not see the others' work. YOUR STARTING POINT: "${l.title}". ${l.angle}

Whatever your starting point, the finished design must honour ALL THREE parts of the owner's sentence, and must be ONE coherent desktop, not a list of features.

Write a complete proposal to ${OUT}/proposal_${l.key}.md (about 1,800 to 2,800 words), with these sections: 1. The idea in five sentences. 2. The screen: every place, its one job, with an ASCII sketch of the screen at 1920x1200 and one at 1366x768. 3. The first minute, the first day, the first week of a Windows-and-DOS person (concrete: what they press, what happens). 4. Files (as an Explorer and as the bulletin board: how the two live together). 5. Apps, windows and the taskbar or dock; the tray and the clock. 6. Search, the launcher and commands. 7. The Terminal and DOS words. 8. Settings and the system pages (a Control Panel). 9. Kas: where she lives, how her plans, permissions and journal are seen, her presence without a picture, HALT. 10. Keys: the full map, and whether menus show them. 11. Type, colour, space and motion (build on 1.0's design tokens or replace them: say which). 12. What goes (removed from 1.0), and every explicit earlier decision of the owner you reverse, with your reason. 13. The build: 10 to 16 slices in order, each with the files it mostly touches in ${REPO}/workbench/ (look at the real file names) and what it must not collide with. 14. Risks, and what only real hardware can settle.

Then return the structured summary (the 'file' field is the path you wrote).`,
    { label: 'design:' + l.key, phase: 'Design', schema: PROPOSAL_SCHEMA }).then(r => (r ? { key: l.key, lens: l.title, ...r } : null))
))).filter(Boolean)

log(proposals.length + ' of 3 proposals written')
if (proposals.length === 0) return { error: 'no proposal came back' }

const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string' },
          windows_function: { type: 'integer' }, apple_grace: { type: 'integer' }, linux_freedom: { type: 'integer' },
          coherence: { type: 'integer' }, kas_fit: { type: 'integer' }, buildability: { type: 'integer' },
          strongest: { type: 'string' }, weakest: { type: 'string' },
        },
        required: ['key', 'windows_function', 'apple_grace', 'linux_freedom', 'coherence', 'kas_fit', 'buildability', 'strongest', 'weakest'],
      },
    },
    winner: { type: 'string' },
    grafts: { type: 'array', items: { type: 'string' }, description: 'ideas from the non-winning proposals that the final design should take, each naming its source' },
    must_fix: { type: 'array', items: { type: 'string' }, description: 'faults the final design must not carry over' },
  },
  required: ['scores', 'winner', 'grafts', 'must_fix'],
}

const JUDGES = [
  { key: 'owner_hands', who: `THE OWNER'S HANDS. You judge as a person with decades of Windows and DOS habits, new to Debian, who will live in this desktop every day and wants never to need another one. Walk each proposal's first minute, first day and first week yourself: where do you get stuck, what do you reach for that is not there, what delights you? You are not a designer and you do not care about elegance for its own sake, but you do know the difference between a tool that respects you and one that shows off.` },
  { key: 'design_critic', who: `A DEMANDING DESIGN CRITIC. You judge coherence and grace as the best of Apple's human-interface work would be judged: is there ONE idea, a real hierarchy, restraint, a consistent grammar of places and gestures, meaningful motion, type and space that would survive at 1366x768 as well as 1920x1200? Look at the 1.0 frames the proposals build on (${S}/work/b100/D2/atlas/frames/) so you judge against what really exists. Call out anything that is a feature list wearing a design's clothes.` },
  { key: 'engineer', who: `THE ENGINEER WHO MUST BUILD IT. You judge buildability on the real code: read ${REPO}/workbench/ file names and sizes (ls -la, wc -l on the window files: shell2.py, qt_app.py, her_column_qt.py, board_qt.py, computer_tree_qt.py, system_dock_qt.py, typebar_qt.py, menus2.py, design_tokens.py, windows_x11.py, session supervisor scripts) and check each proposal's slices against them: which slices are real, which hide a rewrite, which collide, what a hidden Fluxbox and X11 can and cannot give (global keys such as the Windows key and Alt+Tab, a taskbar that reserves screen space, always-on-top), and what must wait for real hardware. Prefer the design that reaches the owner's sentence with the least risk of a broken desktop.` },
]

phase('Judge')
const digest = proposals.map(p => `### PROPOSAL "${p.key}" (${p.lens}): ${p.name}\n${p.one_line}\nLAYOUT: ${p.layout}\nSIGNATURE MOVES: ${p.signature_moves.join(' | ')}\nKAS: ${p.kas_presence}\nKEYS: ${p.keyboard || '-'}\nREMOVALS: ${(p.removals || []).join(' | ')}\nREVERSES: ${(p.reverses_owner_decisions || []).join(' | ')}\nSLICES: ${p.slices.join(' | ')}\nFULL TEXT: ${p.file}`).join('\n\n')

const verdicts = (await parallel(JUDGES.map(j => () =>
  agent(`${BRIEF}
YOU ARE A JUDGE of three independent design proposals for Graphite 1.1. YOUR LENS: ${j.who}

Read the three FULL proposals (the files named below), not only the summaries. Score each from 1 to 10 on: windows_function (does a Windows-and-DOS person lose nothing and find everything?), apple_grace, linux_freedom, coherence (one desktop, not a list), kas_fit (does Kas, an agent user under the owner's authority, have a right place?), buildability. Be hard: a 9 or 10 must be earned and argued. Name the winner THROUGH YOUR LENS, the ideas the final design should take from the others (grafts, naming the source), and the faults that must not be carried over.

${digest}`, { label: 'judge:' + j.key, phase: 'Judge', schema: SCORE_SCHEMA }).then(r => (r ? { judge: j.key, ...r } : null))
))).filter(Boolean)

log(verdicts.length + ' of 3 judges returned; winners: ' + verdicts.map(v => v.judge + '→' + v.winner).join(', '))

phase('Synthesize')
const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    one_line: { type: 'string' },
    base: { type: 'string', description: 'which proposal is the base, and why' },
    grafts_taken: { type: 'array', items: { type: 'string' } },
    grafts_refused: { type: 'array', items: { type: 'string' } },
    reverses_owner_decisions: { type: 'array', items: { type: 'string' } },
    slices: { type: 'array', items: { type: 'string' }, description: 'the build slices in order, one line each: key, name, files, depends on' },
    open_questions: { type: 'array', items: { type: 'string' } },
    file: { type: 'string' },
  },
  required: ['name', 'one_line', 'base', 'grafts_taken', 'slices', 'file'],
}

const synthesis = await agent(`${BRIEF}
YOU ARE THE SYNTHESIZER. Three designers proposed the Graphite 1.1 desktop independently, and three judges (the owner's hands, a design critic, the engineer who must build it) scored them. Write THE design direction for 1.1: one coherent desktop that honours the owner's sentence, "the functionality of windows, with the graceful class of Apple, and the freedom power of Linux".

Method: read the three full proposals and the judges' verdicts below. Take the strongest proposal as the base (weigh the three judges; where they disagree, the owner's hands win on what must exist, the critic on how it is expressed, the engineer on what is cut or deferred). Graft the best ideas of the others where they fit the base's ONE idea; refuse grafts that would make it a list, and say which you refused. Fix every 'must_fix' fault or say why it stands. Do not average: decide.

Write ${OUT}/DESIGN_DIRECTION_1.1.draft.md (about 2,500 to 3,500 words): 1. The idea, in a paragraph, and the three promises (function, grace, freedom) each as five checkable statements. 2. The screen: every place and its one job; ASCII sketches at 1920x1200 and 1366x768. 3. The grammar: the few rules everything obeys (where things appear, how they are summoned and dismissed, what a click, a double-click, a right-click and a drag always mean, what the Windows key, Alt+Tab, Ctrl+C/X/V, F2, Delete, Alt+F4, Ctrl+Alt+Del and PrintScreen do). 4. Files: Explorer and the board together. 5. Apps, windows, the taskbar or dock, the tray, the clock, notifications. 6. The launcher, search and commands. 7. The Terminal and DOS words. 8. Settings as a Control Panel; the system pages. 9. Kas: her place, her plans, permissions and journal, her presence, HALT. 10. Design tokens: what changes from 1.0's (type scale, colour, space, radius, elevation, motion), stated as values. 11. Wording: the vocabulary (a table: the thing, its 1.1 word, the Windows word, the Debian word). 12. What goes. 13. Every explicit earlier decision of the owner this reverses, with the reason, so the owner can strike it. 14. The build: the slices in order (12 to 18), each with a key (D-series for design/shell: use keys like W1..W9 for Windows function, G1..G5 for grace, P1..P5 for power), the files it mostly touches, what it depends on, what it must not collide with, and its acceptance in two lines. 15. What only real hardware can settle.

Then return the structured summary.

THE PROPOSALS:
${digest}

THE JUDGES:
${verdicts.map(v => `## Judge ${v.judge}: winner ${v.winner}\n` + v.scores.map(s => `- ${s.key}: function ${s.windows_function}, grace ${s.apple_grace}, freedom ${s.linux_freedom}, coherence ${s.coherence}, Kas ${s.kas_fit}, buildable ${s.buildability}. Strongest: ${s.strongest}. Weakest: ${s.weakest}`).join('\n') + `\nGRAFTS: ${v.grafts.join(' | ')}\nMUST FIX: ${v.must_fix.join(' | ')}`).join('\n\n')}`,
  { label: 'synthesis', phase: 'Synthesize', schema: SYNTH_SCHEMA })

return { proposals: proposals.map(p => ({ key: p.key, name: p.name, one_line: p.one_line, file: p.file, reverses: p.reverses_owner_decisions || [] })), verdicts, synthesis }
