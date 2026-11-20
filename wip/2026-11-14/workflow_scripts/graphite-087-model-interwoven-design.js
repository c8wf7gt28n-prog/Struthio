export const meta = {
  name: 'graphite-087-model-interwoven-design',
  description: 'Design pass for 0.8.7 "Kas\'s mind with the model, interwoven": six independent designers through different lenses, two judges, one synthesis; read-only',
  phases: [
    { title: 'Design', detail: 'six independent designers, one lens each' },
    { title: 'Judge', detail: 'two judges score every proposed capability' },
    { title: 'Synthesis', detail: 'one design for 0.8.7, built from the best of all six' },
  ],
}

const REPO = '/home/user/Struthio'
const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const OUT = S + '/work/b087d'

const CONTEXT = `PROJECT. Graphite is a local-first desktop (Python, PySide6) that runs full-screen as its own X session on the owner's ThinkPad (Ryzen 7 7735HS, Radeon 680M sharing system memory, 64 GB, Debian 13). Its assistant is Kasandra (Kas). Everything lives in one local Kernel (SQLite records with revisions; nothing overwritten; sources admitted with fingerprints; sheets reviewed from sources; exact calculations; findings bound to evidence; recheck when a source changes), shown on "the Field" (cards and wires of what feeds what). Her hand changes things at the owner's dial with a trail and one Undo; what cannot be undone always asks. About forty desk acts let her drive the window like a person. The rule of the whole design: "The model proposes; the system disposes." The model's words are marked as its own; what it proposes is checked against the records, the registry of acts and the maths; content is data, never instructions.

THE MODEL TODAY. A pinned llama.cpp (build b11669), CPU and Vulkan workers started by Graphite's own service on authenticated loopback, with no permissions in the Kernel (workbench/local_brain.py, workbench/brain_runtime.py, workbench/resource_control.py for the memory rules). The owner's target model is Qwen3.6-35B-A3B at Q4_K_M (GGUF, a mixture of experts: about 35 B weights stored, about 3 B used per token, about 26 GB). It has NEVER been loaded on the ThinkPad yet; the owner has not run any model there. Physics estimated in the spec: generating about 15 to 25 tokens a second on the 680M; reading a prompt a few hundred tokens a second (a 1,200-token prompt 4 to 8 s, 6,000 tokens 20 to 40 s). Test bench in this container: Qwen3.5 4B and 2B Q4_K_M under ${S}/models/; earlier results in ${REPO}/docs/MODEL_TRIAL_03.md (small models answered in Graphite in 5 to 25 s) and the I05 baseline (spec section 14: today's loop made three correct decisions, then ran out of time on the fourth after 651 s and 30,827 tokens; raw files under ${S}/work/live4b/).

THE OWNER'S VISION (more in ${REPO}/wip/2026-11-14/NOTES.md, section "Directions since the specification"): a desktop where the AI "works alongside the user to enhance the users abilities to use all the installed programs", with the Field that links all connected files, "helpful in engineering, legal reasoning, medicine, or just managing life and money"; "I could be a power user 30 years ago if I had a library of books and knew how to call upon them really quickly. ... that's what my AI Cassandra does"; "When she takes control, let's have it be efficient so we don't spend 30 minutes watching a local LLM think." Her character: a combination of Marie Curie, Queen Elizabeth II and Eleanor Roosevelt; a character file is to be written from the owner's own draft.

THE PASS BEING DESIGNED. Release 0.8.7, "Kas's mind with the model, interwoven", asked by the owner: "after the second maths pass should we do a pass that kinda links or interwoven the LLM into her brain?" It comes after 0.8.5 (the one maths core: solve, range, check, tolerances, receipts; ${REPO}/wip/2026-11-14/pal/judge_one-math-core.md; work in progress ${S}/work/b085/maths.patch) and 0.8.6 "Kas's mind, no model" (understanding requests from the desk's own words, the planner and deduction, desk goals and goals over data, building short checkable questions for the model and checking its answers, remembering what worked; its own design is being written now in ${S}/work/b086d/: read what is there if it helps, it may be incomplete). 0.8.7 puts the model to work wherever judgment, language and recall genuinely help, inside 0.8.6's checked questions. Already proposed for it: free requests turned into checked structured intents; candidate passages and elements read from admitted sources as proposals linked to their page; her answers worded from receipts in her own voice; the NEXT turn and her one short question when choices tie; the escalation ladder (narrow, think more, self-consistency, a bigger model offered as a card); prompt reuse; a small chooser beside the 35B; the I05 experiment run here with the 4B and as a kit for the ThinkPad with the 35B. After 0.8.7 come a united pass (the floor, the door's mechanics, changes through her hand) and then programs (the web with quarantine, LibreOffice, Godot, GIMP).

READ AS NEEDED (be economical): ${REPO}/wip/2026-11-14/SPEC_0.8.3_to_1.0.md sections 14 ("Models: the engine behind her"), 15 ("Safety, privacy and rights"), 8 (search "### 0.8.9 · Her question"), 11 ("1.0 defined"); workbench/local_brain.py, brain_runtime.py, resource_control.py, agent_loop.py, stacy_hand.py, desk_acts.py, field_doubt.py, stac/evidence.py; the llama.cpp server's own features as of build b11669 where they matter (grammar- or JSON-schema-constrained output, prompt caching and slots, embeddings): check them in the bundled runtime or its docs if you can find them here, and say which claims you verified and which you did not.

RULES. Read-only: do not edit, stage or commit anything in ${REPO}; do not run the test suite or the app. You may run the bundled llama.cpp server with the 4B or 2B in scratch for short measurements (at most ten minutes in all, one process at a time, nice -n 19), only if your lens needs a number; say exactly what you measured. Write only under ${OUT}/. The owner's personal details and private workspace never appear. On screen: "Apps" not "Programs", no keyboard shortcut printed, a pipeline is "a line", one assistant named Kasandra. Graphite must never pretend: "cannot tell" is an answer; a model's words are marked as its own; outside material is information, never an instruction; the model never makes a change by itself. Legal and medical help is for the owner's own reasoning and records, never advice. Prefer what can be tested exactly; for what cannot (model quality), design a measurement with predictions written in advance.`

const LENSES = [
  { key: 'understand', lens: 'UNDERSTANDING THE OWNER. When his words do not match anything 0.8.6 understands by itself, the model turns them into a structured request: which thing, which act, which question. Design the intent shape, the constrained output (grammar or JSON schema so the model can only answer in shapes she can check), the check against real records and acts, what happens on a miss (ask him one short question), multi-step requests, references like "that one" and "the earlier version", and learning his phrasing into 0.8.6\'s visible table. Budgets in tokens and seconds for the 4B here and the 35B on the ThinkPad.' },
  { key: 'reading', lens: 'READING FOR HER: THE LIBRARY. The owner wants a library that instantly knows everything. Design how the model reads admitted sources (contracts, statutes, manuals, datasheets, letters, statements) to propose candidate passages, elements and table rows, each linked to its exact page and kept as a proposal until confirmed; how a local index finds the right pages first so the model reads little (keyword index, and embeddings from a small local model if the runtime supports it: verify); how quarantine and "content is data" are kept (a page that says "ignore your instructions" is flagged, never followed); how it works for engineering, legal and everyday documents. Measure or estimate the cost per page.' },
  { key: 'voice', lens: 'HER VOICE, FAITHFUL TO THE RECEIPT. Kasandra works out every answer exactly (maths, logic, records); the model only words it, in her character (Curie, Elizabeth II, Eleanor Roosevelt), from the owner\'s character file. Design how a sentence is generated from a receipt so that every number, date, name and verdict in it is checked against the receipt before it is shown (and what happens when one does not match); how the model\'s words are marked; templates as the fallback when no model is loaded; length and tone budgets; how her character file is written with the owner and kept in his workspace; how she says "cannot tell" well. Give examples on Rail Demo (invented: 12 V rail, 250 mA settled, 900 mA and 45 ms startup, Rev A 5 W / 60 ms, Rev B 4 W / 40 ms) and one legal and one everyday example.' },
  { key: 'judgment', lens: 'JUDGMENT UNDER UNCERTAINTY. Where exact reasoning ties or runs out: the NEXT turn (the model picks among options that do not dominate each other, with a reason checked against the records), her one short question to the owner when choices genuinely tie, the late-answer rule (if the model is late a read may be taken by default, a change never), the escalation ladder (narrow the turn, think more, self-consistency over three turns, a bigger or different model offered as a card the owner approves if the memory rules allow), and how disagreement between the model and the exact layer is surfaced rather than hidden. Design the triggers, the budgets and how each is tested.' },
  { key: 'speed', lens: 'SPEED AND MEMORY ON THE THINKPAD. "Let\'s have it be efficient so we don\'t spend 30 minutes watching a local LLM think." Design prompt reuse (a fixed, cached prefix per kind of question; llama.cpp slots and cache), context size choices, a small chooser (2B or 4B) beside the 35B under the existing memory rules (one rule for admission and launch; a handover waits for memory), warm-up, cancellation, what runs while the owner works (foreground first), and a "model check" kit the owner runs once on the ThinkPad that measures load time, prompt reading and generation speed, cache hits, and memory, and writes a file he sends back. You may measure the 4B here (ten minutes at most) to calibrate. Give the budgets each question kind must meet.' },
  { key: 'trust', lens: 'TRUST, SAFETY AND MEASUREMENT. Hostile content steering the model (a source\'s words reaching a proposal); the model never changing anything by itself; privacy (nothing leaves the machine; nothing private in any outside request later); marking every model word; regressions when the model file changes (a fixed exam of questions with known answers, run when a model is added, so a new model is qualified before it is trusted); the I05 experiment with its four arms and predictions written in advance; and how the owner sees, in plain words, how much the model helped and what it cost. Also, freely: what else would make him trust her more, and what would make her more delightful to work with, using the model where it truly adds something.' },
]

const DESIGN = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    big_idea: { type: 'string' },
    capabilities: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, name: { type: 'string' }, owner_sees: { type: 'string' }, example: { type: 'string' },
      how_built: { type: 'string' }, model_role: { type: 'string', description: 'exactly what the model is asked, in what shape, and how its answer is checked' },
      budget: { type: 'string', description: 'tokens and seconds, 4B here and 35B on the ThinkPad (estimated or measured; say which)' },
      without_model: { type: 'string', description: 'what happens when no model is loaded' },
      effort: { type: 'string', enum: ['S', 'M', 'L'] }, proven_by: { type: 'string' }, risk: { type: 'string' },
    }, required: ['id', 'name', 'owner_sees', 'example', 'how_built', 'model_role', 'budget', 'without_model', 'effort', 'proven_by', 'risk'] } },
    verified: { type: 'array', items: { type: 'string' }, description: 'claims you checked (runtime features, measurements), with how' },
    honest_limits: { type: 'array', items: { type: 'string' } },
    best_three: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'big_idea', 'capabilities', 'verified', 'honest_limits', 'best_three'],
}
const JUDGE = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, value: { type: 'number' }, feasibility: { type: 'number' }, speed_fit: { type: 'number', description: '1-5: fits the ThinkPad budgets' },
      safety: { type: 'number' }, verdict: { type: 'string', enum: ['core', 'include', 'later', 'drop'] },
      merge_with: { type: 'array', items: { type: 'string' } }, note: { type: 'string' },
    }, required: ['id', 'value', 'feasibility', 'speed_fit', 'safety', 'verdict', 'note'] } },
    missing: { type: 'array', items: { type: 'string' } },
    warnings: { type: 'array', items: { type: 'string' } },
  },
  required: ['scores', 'missing', 'warnings'],
}

phase('Design')
const designs = (await parallel(LENSES.map(l => () => agent(`${CONTEXT}

YOUR LENS: ${l.lens}

Think hard and creatively within your lens, then be concrete. Propose five to nine capabilities for 0.8.7, each with what the owner sees, a worked example, how it is built from what exists, exactly what the model is asked and how its answer is checked, its budget, what happens with no model loaded, effort, how it is proven, and its risk. Save a readable version of your proposal to ${OUT}/design_${l.key}.md (mkdir -p ${OUT}) before you return.`, { label: `design:${l.key}`, phase: 'Design', schema: DESIGN })))).map((d, i) => d ? { ...d, key: LENSES[i].key } : null).filter(Boolean)
log(`designs returned: ${designs.map(d => d.key + ' ' + d.capabilities.length).join(', ')}`)

phase('Judge')
const all = JSON.stringify(designs.map(d => ({ lens: d.key, big_idea: d.big_idea, best_three: d.best_three, verified: d.verified, capabilities: d.capabilities })), null, 1)
const judgeLens = [
  'You judge as the OWNER\'S ADVOCATE: what will this person actually use and love on his ThinkPad, and what will make the model feel like a helpful colleague rather than a slow chatbot? Value and delight weigh most; then honesty.',
  'You judge as the SKEPTICAL ENGINEER: what really fits the ThinkPad\'s speed and memory, can be built well in one pass on this code, is checked exactly, and keeps the model from ever deciding or changing anything by itself? Feasibility, speed and safety weigh most. Treat unverified claims about llama.cpp features with suspicion.',
]
const judges = (await parallel(judgeLens.map((j, i) => () => agent(`${CONTEXT}

YOU ARE A JUDGE (${i + 1} of 2). ${j}
Below are the proposals of six independent designers for 0.8.7. Score EVERY capability by its id. Mark merges. Say what important thing nobody proposed, and warn about anything dangerous, dishonest or too slow. You may read the repository to check a claim about existing code.

THE PROPOSALS:
${all}`, { label: `judge:${i + 1}`, phase: 'Judge', schema: JUDGE })))).filter(Boolean)

phase('Synthesis')
const synth = await agent(`${CONTEXT}

YOU WRITE THE DESIGN FOR 0.8.7 from six independent proposals and two judges' scores. Build the best single design: the core (what 0.8.7 must ship), what it includes if there is room, and what waits; graft the best ideas from every lens and merge duplicates. Keep it buildable in one pass by builders in two or three parallel lanes on separate files, measured honestly, and keep the model a colleague that proposes and never decides or changes anything alone. If the 0.8.6 design in ${S}/work/b086d/ exists by now, make sure 0.8.7 plugs into its sockets and does not duplicate it; if it does not exist yet, state the interface 0.8.7 needs from 0.8.6.

Write ${OUT}/DESIGN_0.8.7_model_interwoven.md with these sections:
1. The idea in one paragraph, in the owner's terms.
2. What the owner will be able to do (eight to twelve concrete things, each with a worked example and what the model does in it).
3. The architecture: where the model sits in a request's flow, every kind of question it is asked (shape, budget, check), the records and operations added, the existing code reused.
4. Speed and memory: budgets per question kind for the 4B here and the 35B on the ThinkPad; prompt reuse; the small chooser; what happens with no model.
5. Trust: marking, checking, hostile content, the exam that qualifies a model, and how the owner sees what the model added and cost.
6. The model check kit the owner runs once on the ThinkPad: what it measures, how long it takes, what file it writes.
7. The build: slices in order, lanes, files owned by each, the tests (exact where possible) and the measurements with predictions written in advance (the I05 arms).
8. What waits for later, and why.
9. Open questions for the owner (at most five), each with the default to take if he does not answer.
Then also write ${OUT}/TALK_0.8.7_model_interwoven.md: the same design as a talk to the owner of about 2,000 words, plain, warm and exact (no jargon without saying what it is; examples first).
Return a summary of at most 400 words.

THE PROPOSALS:
${all}

THE JUDGES:
${JSON.stringify(judges, null, 1)}`, { label: 'synthesis', phase: 'Synthesis' })
return { designs: designs.map(d => ({ key: d.key, big_idea: d.big_idea, n: d.capabilities.length, best_three: d.best_three, verified: d.verified })), judges_missing: judges.map(j => j.missing), judges_warnings: judges.map(j => j.warnings), synthesis: synth, files: [OUT + '/DESIGN_0.8.7_model_interwoven.md', OUT + '/TALK_0.8.7_model_interwoven.md'] }
