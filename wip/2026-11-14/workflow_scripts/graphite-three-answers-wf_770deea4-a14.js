export const meta = {
  name: 'graphite-three-answers',
  description: 'Read the Graphite tree for the licence change and the first model',
  phases: [
    { title: 'Read', detail: 'four readers: rights statements, third-party parts, the local model path, what exists on the web' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const COMMON = `
You are reading a real project for its owner. The tree is at /home/user/Struthio (a git checkout; branch claude/epic-galileo-c7k11y, commit 37b78f0). It is "Graphite 0.3": a local-first desktop workspace with a built-in assistant, Python 3.13 and PySide6 (Qt), aimed at one ThinkPad E16 Gen 2 (Ryzen 7 7735HS, Radeon 680M, about 61 GiB shared memory) on minimal Debian 13. Read RECORD_OF_DIRECTIONS.md first: it is the one-page record of where the project is going and the owner's standing rules.

Rules for you:
- READ ONLY. Do not edit, create, move or delete anything under /home/user/Struthio, and run no git command that changes state. If you need a scratch script, put it under ${S}/tools/answers/<your-label>/ and run Python as ${S}/work/venv/bin/python -B (it has PySide6; for a window use QT_QPA_PLATFORM=offscreen).
- Do NOT run the project's test suites (tests_integrated) or tools/check_release.py; they are slow and not your question.
- Internal names in the code are older than the product name on purpose (Ledger, Slate, Hatch, LS, arc1, clip): "Slate" in code is the assistant, "Ledger" the workspace, staC ("Stacy language 1") is the read-only typed pipeline language (sdk/cli/arc1cli/typed_pipeline.py, workbench/stacy_language.py).
- The owner's name, email and the project's name are private: never put them in a web search or any request to an outside service.
- Give file paths with line numbers for every claim about the code. Say plainly what you did not check. Stop when the question is answered; do not wander.
`

const FINDINGS = { type: 'object', properties: {
  summary: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, where: { type: 'string' }, detail: { type: 'string' },
    weight: { type: 'string', enum: ['blocker', 'important', 'minor', 'note'] } }, required: ['title', 'detail', 'weight'] } },
  recommendation: { type: 'string' }, not_checked: { type: 'string' } }, required: ['summary', 'findings', 'recommendation'] }

const PARTS = { type: 'object', properties: {
  summary: { type: 'string' },
  components: { type: 'array', items: { type: 'object', properties: {
    name: { type: 'string' }, where: { type: 'string' }, licence: { type: 'string' },
    kind: { type: 'string', enum: ['bundled-code', 'bundled-binary', 'bundled-font', 'bundled-art', 'bundled-text-or-data', 'dependency-not-bundled', 'owner-made'] },
    how_used: { type: 'string' }, issue_with_gpl2_only: { type: 'string' } }, required: ['name', 'where', 'licence', 'kind', 'issue_with_gpl2_only'] } },
  problems: { type: 'array', items: { type: 'string' } },
  wording_needed: { type: 'string' }, not_checked: { type: 'string' } }, required: ['summary', 'components', 'problems', 'wording_needed'] }

const DESIGN = { type: 'object', properties: {
  name: { type: 'string' }, in_one_sentence: { type: 'string' },
  what_the_owner_sees: { type: 'string' }, naming: { type: 'string' }, stac_role: { type: 'string' }, without_a_model: { type: 'string' },
  changes: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, what: { type: 'string' } }, required: ['file', 'what'] } },
  risks: { type: 'array', items: { type: 'string' } }, checks: { type: 'array', items: { type: 'string' } }, not_in_this_slice: { type: 'string' } },
  required: ['name', 'in_one_sentence', 'what_the_owner_sees', 'naming', 'stac_role', 'without_a_model', 'changes', 'risks', 'checks'] }

phase('Read')
const READERS = [
  { key: 'rights', schema: FINDINGS, prompt: COMMON + `
YOUR QUESTION: the owner has decided that Graphite's own source code will be licensed "the way Linus Torvalds does it": the GNU General Public License, version 2 only (SPDX GPL-2.0-only), with the full text in a COPYING file at the root. Today RIGHTS.md says "No licence is assigned ... all rights remain with the owner".
Find EVERY place in the tree that states or implies the terms of the project's own code or artwork, so that none is left contradicting the new licence. Search by content, not by guess: "licen[sc]e", "copyright", "all rights", "rights reserved", "RIGHTS.md", "proprietary", "unlicensed", "SPDX", "redistribut", "permission", "©", "(c)", and the About / Guide / installer / release-notes / README / manifest / package metadata / remote PWA / game (games/, STRUTHIO ARCADE) surfaces. Include user-visible strings in the program (workbench/, sdk/, tools/, INSTALL_*.sh/.py, docs/*.md that the Guide menu opens) and machine-read fields (MANIFEST.json, tools/package_graphite.py, tools/record_registry.py, any JSON with a "license"/"rights" key), and anything a test or the release check compares RIGHTS.md or licence words against (tests_integrated/, tools/check_*.py, workbench/release_integrity.py) so a change does not break a check.
For each: file:line, the exact words now, whether it must change, and the smallest correct replacement. Separate (a) statements about the project's OWN code, (b) statements about Stacy's artwork and the names (the owner's girlfriend is the model for Stacy; assume the artwork and the names Graphite / staC / Stacy are NOT to be licensed for reuse unless the tree says otherwise), (c) statements about third-party parts (leave alone, just list). Also report whether individual source files carry licence headers today (count, pattern) and whether any file ALREADY claims a licence for project-owned code that conflicts with GPL-2.0-only.` },
  { key: 'parts', schema: PARTS, prompt: COMMON + `
YOUR QUESTION: the owner will license Graphite's own code under the GNU GPL version 2 only (GPL-2.0-only), as the Linux kernel is. Make the inventory that makes that honest: every third-party component that is physically in this tree, and every dependency the program imports or runs but does not bundle, each with its licence and whether it raises a problem when Graphite's own code is distributed under GPL-2.0-only.
Look by container, not only by notice file: runtimes/ (llama.cpp archives, office-uno JAR, python-wasi), branding/ (fonts; which images are owner-made and which are not), games/, pillkit/, sdk/, workbench/ (vendored modules, algorithm_corpus.json, handbook/manual text, remote_pwa, view_modules, nav_icons), docs/ (PDFs, vendor text), examples/, project/, tools/; requirements-*.txt and any wheel/deb inventory (the offline kit lists wheels in OFFLINE_FILES.json: a copy is at ${S}/x/Graphite_00_START_HERE/Graphite_Transfer/App/OFFLINE_FILES.json). THIRD_PARTY_NOTICES.md is the tree's own list; check it against what is really there (it mentions paths such as software/arcos and hardware/ that may no longer exist in this tree: say so).
For the imported dependencies, establish the actual licence (PySide6/Qt for Python, shiboken, PyMuPDF or whichever PDF library is used, numpy, sympy, z3, wasmtime, cryptography, anything else imported by workbench/ or sdk/): check installed metadata in ${S}/work/venv (pip show / dist-info METADATA) first, and the web only where metadata is unclear. Pay particular attention to: (1) anything AGPL or GPL-3.0-only that the program imports (GPL-2.0-only cannot be combined with those), e.g. PyMuPDF is AGPL; (2) Apache-2.0 libraries imported into the same process (the FSF reads Apache-2.0 as incompatible with GPL-2.0-only); (3) LGPL-3.0 (Qt for Python offers LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only: confirm); (4) binaries run as separate programs (llama.cpp server, LibreOffice, KiCad, ngspice): mere aggregation, no problem, but confirm how each is invoked (subprocess vs import).
In "problems" list only real conflicts, each with the evidence and the smallest remedy. In "wording_needed" draft, in plain short sentences, the note that should accompany the licence so the boundary is clear in the way the Linux kernel's COPYING note about user programs is: which separately licensed libraries Graphite uses, that they keep their own terms, and any additional permission the owner must grant so that running and distributing Graphite together with them is allowed. You are not a lawyer: mark anything that needs one.` },
  { key: 'model', schema: FINDINGS, prompt: COMMON + `
YOUR QUESTION: the owner has chosen the first model to try on the ThinkPad. Their words (voice-typed): "Quinn 4.0 27B Quant 4 when it's available". Read that as a not-yet-released Qwen-family model of about 27 billion parameters as a GGUF file at 4-bit quantisation (Q4_K_M, roughly 16 to 18 GB). Trace, in the code, exactly what happens when the owner brings such a file to Graphite, and find everything that would block it, degrade it, or need a decision before first boot.
Read: docs/HATCH_MODEL_01.md, docs/MODEL_TRIAL_01.md, docs/MODEL_TRIAL_02.md, docs/MODEL_TURN_01.md, docs/THINKPAD_VULKAN_P05.md, docs/THINKPAD_FIRST_INSTALL.md, docs/I04_MODEL_PINS.json, I04_MODEL_*.json and I05_MODEL_TRIAL.json at the root, runtimes/llama.cpp/ (which build, which backends: CPU only or Vulkan too, how old), and the code: workbench/brain_runtime.py, brain_worker.py, brain_qt.py, brain_link.py, local_brain.py, model_settings.py, model_settings_qt.py, model_turn.py, inference_hardware.py, memory_forecast.py, memory_settings.py, slate_stream.py, slate_reasoning.py, agent_loop.py, and whatever they call.
Answer specifically: (1) how a model file is chosen and where it must be put; which formats are accepted; is there an allowlist, a pin, a digest requirement or a "qualified models" list that a new model would fail? (2) which llama.cpp build runs it, how it is started (arguments, context size, GPU layers, threads), and whether a model architecture newer than the bundled build (b11669) would fail to load: what the owner would see, and how the runtime is replaced with a newer build; is a Vulkan build present for Linux or only CPU? (3) the chat template: taken from the GGUF, or hard-coded? what happens to reasoning output (Qwen models emit <think>...</think> blocks and can be switched with /no_think or a template flag): is it stripped, shown, or would it corrupt tool/edit parsing? (4) tool calling / edit proposals: which format does the program expect from the model (JSON, a grammar, function-call tags) and is it model-family specific? (5) memory: with about 61 GiB shared between CPU and the Radeon 680M, what does the forecast do with a 17 GB file and a large context; any hard limits written for a smaller machine? (6) what the tree says was actually tried before (which models, which results). End with a short, exact list of steps for the owner for the day the model exists, and what can be rehearsed today with an existing Qwen-family GGUF. Mark each finding blocker / important / minor / note.` },
  { key: 'web', schema: FINDINGS, prompt: `
You are doing web research for a person who is choosing a local language model for a laptop (Ryzen 7 7735HS, Radeon 680M integrated graphics, about 61 GiB shared memory, Debian 13, llama.cpp). Today is 12 November 2026. Their words, voice-typed: "Quinn 4.0 27B Quant 4 when it's available". The working reading is: Alibaba's Qwen family, a version 4.0, 27 billion parameters, 4-bit quantisation (GGUF Q4_K_M), not yet released when they said it.
Use web search (load the WebSearch tool with ToolSearch if it is not already available; use extended mode for the recent facts). Privacy: put nothing about the person or their project in any query; search only for the public model and tool names.
Establish, with sources and dates, and say clearly what you could not verify:
1. Is there any model actually named "Quinn"? Is "Qwen 4" / "Qwen4" / "Qwen 4.0" announced or released as of today? If so: sizes, licence, whether a 27B exists, whether GGUF files exist and from whom.
2. The newest released open-weight Qwen model in the 27B class today (for example a Qwen 3.x 27B): exact name, release date, licence, context length, whether it is a thinking model and how thinking is switched, its chat template family, and the file size of its Q4_K_M GGUF.
3. The minimum llama.cpp version that loads that newest 27B, and when llama.cpp release tag b11669 was published (the laptop's bundled build), so it is clear whether the bundled build is old enough to fail.
4. Realistic speed on this class of hardware (Ryzen 7 7735HS CPU, Radeon 680M through Vulkan) for a 27B Q4_K_M model: tokens per second figures people report, CPU versus Vulkan on the 680M, and whether Vulkan on RADV with an integrated GPU is known to help or hurt at this size.
5. Whether "Q4" for this family is best taken as Q4_K_M, and any known quality warnings about 4-bit quantisation for this model.
Return findings with the source URL in "where". Weight: blocker / important / minor / note. In "recommendation" say what the person should use to rehearse today and what to watch for when the 4.0 model appears.`, },
]
const read = await parallel(READERS.map(r => () => agent(r.prompt, { label: 'read:' + r.key, phase: 'Read', schema: r.schema })))
const by = {}; READERS.forEach((r, i) => { by[r.key] = read[i] })
log('readers back: ' + READERS.map((r, i) => r.key + (read[i] ? ' ok' : ' MISSING')).join(', '))

return { read: by }
