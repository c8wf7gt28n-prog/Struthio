export const meta = {
  name: 'graphite-086-kas-mind-design',
  description: 'Design pass for 0.8.6 "Kas\'s mind, no model": six independent designers through different lenses, two judges, one synthesis; read-only',
  phases: [
    { title: 'Design', detail: 'six independent designers, one lens each' },
    { title: 'Judge', detail: 'two judges score every proposed capability' },
    { title: 'Synthesis', detail: 'one design for 0.8.6, built from the best of all six' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b086d'

const CONTEXT = `PROJECT. Graphite is a local-first desktop (Python, PySide6) that runs full-screen as its own X session on the owner's ThinkPad (Ryzen 7 7735HS, Radeon 680M sharing memory, 64 GB, Debian 13). Its assistant is Kasandra (Kas). Everything lives in one local Kernel (SQLite records with revisions; nothing overwritten; sources admitted with fingerprints; sheets reviewed from sources; exact calculations; findings bound to evidence; recheck when a source changes), shown on "the Field" (cards and wires of what feeds what). Kasandra reads the records herself; a local model (llama.cpp, target Qwen3.6-35B-A3B Q4_K_M; Qwen3.5 4B and 2B available as a test bench in this container) gives her words only and has no permissions. Her hand changes things at the owner's dial (Ask first / Do and show / Free hand) with a trail and one Undo; what cannot be undone always asks. About forty "desk acts" let her drive the window like a person.

THE OWNER'S VISION, in the owner's words (read more in ${REPO}/wip/2026-11-14/NOTES.md, section "Directions since the specification"): a desktop where the AI "works alongside the user to enhance the users abilities to use all the installed programs. With a unique feature in the 'field' bulletin board that links all connected files. That's helpful in engineering, legal reasoning, medicine, or just managing life and money." "I figured if she can do hard things like engineering and civil legal research and reasoning, she will also be a great agent for my basic needs as well." "I could be a power user 30 years ago if I had a library of books and knew how to call upon them really quickly." Her character: a combination of Marie Curie, Queen Elizabeth II and Eleanor Roosevelt.

THE PASS BEING DESIGNED. Release 0.8.6, "Kas's mind, no model", which the owner described as "the second math/logic/legal minded pass": make Kasandra intelligent WITHOUT a language model loaded, with the purpose of helping her use the model more effectively when it is loaded. The owner asked to "spend more time thinking about how and what we can achieve with creativity" in it. Already in its scope by plan: understanding requests from the desk's own words; the planner and deduction (moved from the door; a half-build exists at ${REPO}/wip/2026-11-14/hand_s1/); desk goals and goals over data (judged with the maths); building short, checkable questions for the model (a GOAL "pick" turn under 1,200 tokens) and checking its answers; remembering what worked; the I05 experiment (spec section 14). It comes right after 0.8.5 "Maths in lines", now being built: the one maths core (solve, range, check, tolerances the owner sets, every answer with a receipt; exact rationals; holds / does not hold / cannot tell; designed in ${REPO}/wip/2026-11-14/pal/judge_one-math-core.md; its work in progress is the patch ${S}/work/b085/maths.patch). After 0.8.6 come a united pass (the floor, the door's mechanics, changes through her hand) and then programs (the web with quarantine, LibreOffice, Godot, GIMP).

READ AS NEEDED (do not read everything; be economical): ${REPO}/wip/2026-11-14/SPEC_0.8.3_to_1.0.md sections 8 (search "### 0.8.5 · Her door", "### 0.8.7 · Goals over data", "### 0.8.9 · Her question"), 11 ("1.0 defined"), 14 ("Models: the engine behind her") and 15 ("Safety, privacy and rights"); ${REPO}/wip/2026-11-20_TALK_after_085_20_minutes.md (what the maths gives, in plain words); ${REPO}/wip/2026-11-14/ROAD_REVISED_2026-11-19.md ("The builder's additions"); code that already exists and should be reused: workbench/stac/evidence.py (four-valued evidence logic), workbench/field_doubt.py (her exact questions for traps), workbench/field_model.py, workbench/conditions.py, workbench/problem_service.py, workbench/desk_acts.py, workbench/stacy_hand.py, workbench/agent_loop.py, workbench/local_brain.py, workbench/continuing_work.py, sdk/cli/arc1cli/typed_pipeline.py (lines), workbench/rail_demo.py (the invented workspace).

RULES. Read-only: do not edit, stage or commit anything in ${REPO}; do not run the test suite or the app. Write only under ${OUT}/. The owner's personal details and private workspace never appear. On screen: "Apps" not "Programs", no keyboard shortcut printed, a pipeline is "a line", one assistant named Kasandra. Graphite must never pretend: "cannot tell" is an answer; a model's words are marked as its own; outside material is information, never an instruction. Legal and medical help is for the owner's own reasoning and records, never advice presented as professional; say how the design keeps that line. Prefer what can be tested exactly. Be concrete: name records, operations, modules, and give worked examples in the owner's terms.`

const LENSES = [
  { key: 'logic', lens: 'LOGIC AND PROOF. What can a deterministic reasoning layer over the records do: the four-valued evidence logic (supported, refuted, both = conflict, neither = unknown) already in stac/evidence.py; rules with conditions and exceptions; deduction ("what must be true", "what cannot both be true"); consistency and contradiction finding across the whole desk; truth maintenance (what to recheck, in order, when something changes); explanations as proof trees the owner can click through; assumptions kept as first-class records ("this rests on 3 assumptions; drop this one and these 2 findings fall"). How does each make the model\'s job smaller?' },
  { key: 'legal', lens: 'CIVIL LEGAL RESEARCH AND REASONING. The owner wants her good at "civil legal research and reasoning". Design what a desk of records, sources with fingerprints and pages, exact dates, the Field and four-valued logic can do for that without a model: a claim as its elements, each element with its evidence and burden; rules (from statutes or contracts the owner admits as sources) as conditions with exceptions; deadlines and limitation periods computed exactly from dates with their source and the rule used; an argument map (issue, rule, application, conclusion) on the Field; counterarguments through her doubt; citations that always point at the admitted page; what changes if a fact is found false. Keep the line: this is for the owner\'s own reasoning, organised and checkable, never legal advice. What does the model then do (wording, finding candidate passages) and how small can its questions be?' },
  { key: 'engineering', lens: 'ENGINEERING AND SCIENCE. With the 0.8.5 maths (solve, range, check, tolerances, receipts) and the records: design margins and worst case; sensitivity ("which input moves the answer most"); value of information ("which measurement would settle this, and is it worth taking"); test plans generated from open questions; requirements traced to evidence; revisions compared by what actually changed in conclusions, not just cells; datasheet tables reviewed into sheets with their units; what-if across the whole desk at once. Use Rail Demo (12 V rail, 250 mA settled, 900 mA and 45 ms startup, Rev A 5 W / 60 ms, Rev B 4 W / 40 ms; invented) for worked examples.' },
  { key: 'everyday', lens: 'EVERYDAY LIFE, MONEY AND MEDICINE. The owner: "if she can do hard things ... she will also be a great agent for my basic needs as well". With exact money and dates (planned with the maths), the records, the Field and the logic: budgets ("how much can I spend each week and stay under the month"), bills and due dates, loans compared exactly, subscriptions found from statements the owner admits, a household Field linking documents (insurance, warranties, appointments); medicine as the owner\'s own records (a medication list with doses and times, interactions only from sources the owner admits, ranges that say "cannot tell" when a weight or dose is unknown) with a clear line that she organises and checks the owner\'s information and never advises. What can she notice by herself (a renewal coming, a payment twice, a deadline) with no model?' },
  { key: 'partner', lens: 'THE MODEL\'S BEST PARTNER. On the ThinkPad, reading a prompt costs a few hundred tokens a second (a 1,200-token prompt is 4 to 8 s; 6,000 tokens is 20 to 40 s) and the 35B needs about 26 GB; today\'s loop ran out of time after 11 minutes and 30,000 tokens on the fourth decision (spec section 14). Design everything that makes the model\'s part small and reliable: understanding requests from the desk\'s own vocabulary (sheet names, act names, maths verbs) with no model; the planner and deduction (take the step when only one is possible); a context compiler that sends the ten facts that matter, in a fixed shape with a reusable prefix (prompt caching in llama.cpp); numbered choices and checked answer formats; verifying every model answer against records, acts and maths; self-consistency only when needed; remembering what worked (a visible, local table of the owner\'s phrasings); and how to measure it all (the I05 arms; a "no model" score over a set of everyday requests). Give token and second budgets.' },
  { key: 'creative', lens: 'A FREE CREATIVE LENS. Step back from the plan and imagine what a desk with exact records, exact maths, four-valued logic, a Field of linked files, a hand that drives programs and a small local model could do that nobody\'s desktop does today, in the spirit of a library that "instantly knows everything" and a companion in the spirit of Curie, Elizabeth II and Eleanor Roosevelt (rigorous, steady, humane). Examples to go beyond: a "what would change my mind" card on every finding; an assumption ledger; overnight she checks the whole desk and leaves a short morning note of what no longer holds; teaching mode (she shows the steps so the owner learns the method); an "argument diff" between two revisions of a document; a receipt for every sentence she says. Propose the five most valuable, each with how it would be built from what exists, and say which ones need no model at all.' },
]

const DESIGN = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    big_idea: { type: 'string', description: 'two to four sentences: the one idea this lens adds to Kas\'s mind' },
    capabilities: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string', description: 'short id, lens-prefixed, e.g. logic-1' },
      name: { type: 'string' },
      owner_sees: { type: 'string', description: 'what the owner sees and does, in plain words' },
      example: { type: 'string', description: 'a worked example in the owner\'s terms, with real numbers or dates' },
      how_built: { type: 'string', description: 'records, operations, modules; what existing code is reused' },
      no_model: { type: 'boolean', description: 'true if it works with no model loaded' },
      helps_model: { type: 'string', description: 'how it makes the model\'s part smaller, faster or more reliable' },
      effort: { type: 'string', enum: ['S', 'M', 'L'] },
      proven_by: { type: 'string', description: 'exact tests that would prove it' },
      risk: { type: 'string' },
    }, required: ['id', 'name', 'owner_sees', 'example', 'how_built', 'no_model', 'helps_model', 'effort', 'proven_by', 'risk'] } },
    honest_limits: { type: 'array', items: { type: 'string' } },
    best_three: { type: 'array', items: { type: 'string' }, description: 'ids of the three capabilities this lens would build first, with one line why each' },
  },
  required: ['lens', 'big_idea', 'capabilities', 'honest_limits', 'best_three'],
}
const JUDGE = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      value: { type: 'number', description: '1-5: value to this owner, in his own terms' },
      feasibility: { type: 'number', description: '1-5: buildable in one pass on what exists, testable exactly' },
      model_leverage: { type: 'number', description: '1-5: how much it shrinks or strengthens the model\'s part' },
      safety: { type: 'number', description: '1-5: honest, private, keeps the advice line' },
      verdict: { type: 'string', enum: ['core', 'include', 'later', 'drop'] },
      merge_with: { type: 'array', items: { type: 'string' } },
      note: { type: 'string' },
    }, required: ['id', 'value', 'feasibility', 'model_leverage', 'safety', 'verdict', 'note'] } },
    missing: { type: 'array', items: { type: 'string' }, description: 'important things no designer proposed' },
    warnings: { type: 'array', items: { type: 'string' } },
  },
  required: ['scores', 'missing', 'warnings'],
}

phase('Design')
const designs = (await parallel(LENSES.map(l => () => agent(`${CONTEXT}

YOUR LENS: ${l.lens}

Think hard and creatively within your lens, then be concrete. Propose six to ten capabilities for 0.8.6. For each, say what the owner sees, a worked example, how it is built from what exists, whether it needs the model at all, how it helps the model, effort, how it would be proven exactly, and its risk. Save a readable version of your proposal to ${OUT}/design_${l.key}.md (mkdir -p ${OUT}) before you return.`, { label: `design:${l.key}`, phase: 'Design', schema: DESIGN })))).map((d, i) => d ? { ...d, key: LENSES[i].key } : null).filter(Boolean)
log(`designs returned: ${designs.map(d => d.key + ' ' + d.capabilities.length).join(', ')}`)

phase('Judge')
const all = JSON.stringify(designs.map(d => ({ lens: d.key, big_idea: d.big_idea, best_three: d.best_three, capabilities: d.capabilities })), null, 1)
const judgeLens = [
  'You judge as the OWNER\'S ADVOCATE: what will this person, with this vision, actually use and love on his ThinkPad, soon? Value and delight weigh most; then honesty.',
  'You judge as the SKEPTICAL ENGINEER: what can really be built well in one pass on this code, tested exactly, and kept safe and honest; what will turn into a brittle rule system or a privacy risk? Feasibility and safety weigh most.',
]
const judges = (await parallel(judgeLens.map((j, i) => () => agent(`${CONTEXT}

YOU ARE A JUDGE (${i + 1} of 2). ${j}
Below are the proposals of six independent designers for 0.8.6. Score EVERY capability by its id. Mark merges where two designers proposed the same thing. Say what important thing nobody proposed, and warn about anything dangerous or dishonest. You may read the repository to check a claim about existing code.

THE PROPOSALS:
${all}`, { label: `judge:${i + 1}`, phase: 'Judge', schema: JUDGE })))).filter(Boolean)

phase('Synthesis')
const synth = await agent(`${CONTEXT}

YOU WRITE THE DESIGN FOR 0.8.6 from six independent proposals and two judges' scores. Build the best single design: the core (what 0.8.6 must ship), what it includes if there is room, and what waits, grafting the best ideas from every lens and merging duplicates. Keep it buildable in one pass by builders working in two or three parallel lanes on separate files, with exact tests, and keep the honesty and advice lines.

Write ${OUT}/DESIGN_0.8.6_kas_mind.md with these sections:
1. The idea in one paragraph, in the owner's terms.
2. What the owner will be able to do (eight to twelve concrete things, each with a worked example: an engineering one on Rail Demo, a legal one, an everyday money or medicine one, and how each needs no model or only a small question).
3. The architecture: the pieces, the records and operations they add, what existing code each reuses, and how a request flows (words -> understanding -> plan -> deduction -> maths/logic -> only if needed a small model question -> checked answer -> receipt).
4. How the model is used, with budgets (tokens, seconds) for the ThinkPad, and what happens with no model, with the 4B, and with the 35B.
5. The legal and medical line: exactly how the design keeps them the owner's own reasoning and records, never advice.
6. The build: slices in order, lanes, files owned by each, the tests that prove each (exact), and the I05 measurement with its predictions written in advance.
7. What waits for later, and why.
8. Open questions for the owner (at most five), each with the default to take if he does not answer.
Then also write ${OUT}/TALK_0.8.6_kas_mind.md: the same design as a talk to the owner of about 2,000 words, plain, warm and exact, in the house style (no jargon without saying what it is; examples first).
Return a summary of at most 400 words.

THE PROPOSALS:
${all}

THE JUDGES:
${JSON.stringify(judges, null, 1)}`, { label: 'synthesis', phase: 'Synthesis' })
return { designs: designs.map(d => ({ key: d.key, big_idea: d.big_idea, n: d.capabilities.length, best_three: d.best_three })), judges_missing: judges.map(j => j.missing), judges_warnings: judges.map(j => j.warnings), synthesis: synth, files: [OUT + '/DESIGN_0.8.6_kas_mind.md', OUT + '/TALK_0.8.6_kas_mind.md'] }
