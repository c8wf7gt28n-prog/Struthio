export const meta = {
  name: 'graphite-kas-superpower',
  description: 'Design Kas 1.1: very useful at everything on a fully loaded Linux box, under the owner\'s authority. Five scouts, an architect, two skeptics, a revision',
  phases: [
    { title: 'Scout', detail: 'what she can do today, the tasks of a Linux box, safe commands, grounding, what a small local model can do' },
    { title: 'Architect', detail: 'one design for Kas 1.1 from the scouts' },
    { title: 'Attack', detail: 'a security skeptic and a usefulness skeptic try to break it' },
    { title: 'Revise', detail: 'the architect answers the skeptics' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const REPO = '/home/user/Struthio'
const OUT = S + '/work/dist/kas'
const PY = S + '/work/venv/bin/python'

const CONTEXT = `
THE PROGRAM. Graphite is a PySide6 desktop for Debian 13 that is the whole session, with an assistant, Kasandra (Kas). Version 1.0 was released yesterday. Kas is an AI AGENT USER of the system. Her rule: "the model proposes; the desk disposes". Today she: reads the owner's words (a dictionary with no model; with a model, the model reads free words only into the desk's verbs); makes a plan whose every step is one of about 27 numbered registered tools (${REPO}/workbench/tools_registry.py; with a model, the model PICKS steps by number under a grammar, at most eight, and the desk checks each: ${REPO}/workbench/objective_plan.py); runs it as an assignment with a journal where a step is "done" only when its effect is verified (${REPO}/workbench/assignments.py); needs the owner's grant per operation, target and scope, enforced by the Kernel at dispatch (${REPO}/workbench/grants.py); HALT stops all her work (${REPO}/workbench/halt.py); changes NOTHING outside the owner's home (${REPO}/workbench/home_reach.py); edits Writer and Calc documents through LibreOffice's UNO (${REPO}/workbench/office_bridge.py); works in other apps' windows through accessibility, where a touch of the owner's stops her (${REPO}/workbench/a11y_hand.py, hand_door.py); runs utilities she drafts only sealed on copies (${REPO}/workbench/utility_sandbox.py); fetches web pages as quarantined data (${REPO}/workbench/network_governed.py); reads the pages of documents in Home (${REPO}/workbench/home_pages.py). Her model is LOCAL and sealed: llama.cpp v1.0.0 with a 35B model (Qwen3.6-35B-A3B) on the owner's ThinkPad (Ryzen, Radeon 680M integrated graphics: perhaps 20 to 55 tokens a second written), the 4B as fallback; every question to the model has a kind, a price, a deadline, a grammar, a checker and a fallback (${REPO}/workbench/turns.py, model_turn.py, brain_briefs.py), and each kind is examined on the machine before it is trusted (${REPO}/workbench/model_exam.py). In walkthroughs the 4B could not plan a tidy of a folder usefully (it answered "the bin for every group", then the same step eight times: ${REPO}/wip/2026-11-26_b100_saved/K10.progress.md and K10.live_rerun_coordinator.log), while the desk's own planner did it with no model.

THE OWNER'S NEW DIRECTION (verbatim, 27 Nov 2026): "Kasandra is the "super power" of this project. Make her very useful at everything in a world where a full loaded Linux box is the computer I use." Also from the owner today: "this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know I can only get what I want in Debian so I have to switch." and "Feel free to change anything under the hood and anything visible. Think the functionality of windows, with the graceful class of Apple, and the freedom power of Linux". The goal of version 1.1 is a distribution-ready desktop in which Kas is the reason to use it.

WHAT STAYS (not negotiable): the model proposes, the desk disposes; every change waits for the owner's press or a grant shown in plain words; a change only the model chose is never made; a step is done only when its effect is verified; HALT; nothing leaves the computer without asking; her model is local. What MAY change: everything else, including "nothing outside your home" (a full Linux box means system work: software, services, settings; the natural door is the system's own permission prompt, polkit, with the owner present).

READ: ${REPO}/docs/GUIDE_KASANDRA.md, ${REPO}/docs/RELEASE_NOTES_1.0.md, ${REPO}/wip/2026-11-26_road_to_1.0/PLAN_1.0.md (sections 1 to 4 and the K slices in section 5), the walkthrough accounts ${REPO}/wip/2026-11-26_b100_saved/X3.account.md and X4.account.md, and the modules named above as your task needs.

RULES FOR YOU: read only on ${REPO} (never edit, stage or commit there); write only under ${OUT}/. Anything you run that imports the tree runs on a throwaway copy (cd ${REPO} && git ls-files -z --cached --others --exclude-standard | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t <copy>), wrapped as: nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen ${PY} -B <script>. Keep the disk under 80 %. Send long output to files. The owner's personal details are not in the tree and must not be sought.
`

const SCOUT_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    summary: { type: 'string', description: 'the answer in under 200 words' },
    key_facts: { type: 'array', items: { type: 'string' }, description: 'up to 20 facts the architect must design on, each one line, with file:line or the measurement behind it' },
    recommendations: { type: 'array', items: { type: 'string' }, description: 'up to 12, most important first' },
    file: { type: 'string', description: 'path of your full notes' },
  },
  required: ['topic', 'summary', 'key_facts', 'recommendations', 'file'],
}

const SCOUTS = [
  { key: 'today', prompt: `YOUR TOPIC: WHAT KAS CAN REALLY DO TODAY, AND WHERE SHE STOPS (write ${OUT}/scout_today.md).
Read the code, not the guide: list every registered tool (number, name, what it reads or changes, its verifier), every verb her dictionary reads (${REPO}/workbench/understand.py and what it imports), every kind of model question (turns.py / brain_briefs.py), the planner's limits (objective_plan.py: step cap, what counts as a refusal, the grammar), what an assignment can and cannot express (assignments.py: no loops? no conditions? no waiting for an event? no schedule?), what her memory is (instruction_matrix.py, the journal: does she learn what worked? does she know what software is installed?), and what requests simply have NO route (try 40 plausible requests of a person on a Linux box against her dictionary and planner with NO model, by calling the real entry points on a copy with Rail Demo or the everyday Home (python -m workbench.everyday_demo FOLDER; see X3's notes), and record for each: understood? planned? refused with what words?). Examples to try: "install vlc", "why is my wifi slow", "find the biggest files in my home", "convert these photos to jpg at half size", "merge these two pdfs", "what changed in this folder since yesterday", "rename all these files to lower case", "set up a backup of Documents every Friday", "unzip this", "what is using all my memory", "show me how to do in Debian what dir /s does in DOS", "open the spreadsheet and add up column C", "download this page and summarise it", "make a new user", "is my system up to date", "burn this folder to a USB stick", "play this music folder", "what does chmod 644 mean", "write a script that ...", "remind me at 5".
Deliver: an honest capability table (can / partly / cannot), the structural reasons she cannot, and the smallest changes that would open the most.` },
  { key: 'tasks', prompt: `YOUR TOPIC: THE TASKS OF A FULLY LOADED LINUX BOX (write ${OUT}/scout_tasks.md).
Build the map of what "very useful at everything" must mean for THIS owner: a Windows-and-DOS person, engineer by the look of the desk (the program carries rooms for KiCad, FreeCAD, Blender, Godot, ngspice, Inkscape, LibreOffice), whose only computer is a full Debian 13 box. List about 150 concrete tasks in families: files and folders; documents and office (Writer, Calc, PDF: merge, split, OCR, convert, fill a form); pictures, audio and video (ImageMagick, GIMP batch, ffmpeg); the web (look up, download, save a page, compare prices: read-only); software (find, install, remove, update, "what is this package"); the system (disks, memory, processes, services, logs, users, time, printers, Bluetooth, Wi-Fi, firewall, backups); troubleshooting ("why is X slow / not working": read logs, test, explain, propose); the command line (explain a command, write one from words, translate DOS habits to Debian, write and schedule a script); automation (every Friday, when a file appears, when a download finishes, remind me); engineering apps (KiCad, FreeCAD, Blender, Godot, ngspice: batch exports, checks, renders); development (git, Python, building from source); learning ("teach me": how Debian does what Windows did); her own upkeep (her model, her memory, her tools).
For EACH task give one line: the request as the owner would type it; the Debian tools that do it (exact package and command, checked to exist in Debian 13 where you can: apt-cache is not available offline here, so use your knowledge and say so); whether it only reads, changes the home, or changes the system (needs root); how its effect can be VERIFIED by a program afterwards; whether it is reversible and how; how often such a person would want it (daily / weekly / rarely). Then rank: the 40 tasks that would make her feel like a superpower in the first two weeks, and the 15 that are dangerous enough to need special care (data loss, security, money, sending things out).` },
  { key: 'commands', prompt: `YOUR TOPIC: A SAFE WAY FOR KAS TO RUN ANY COMMAND (write ${OUT}/scout_commands.md).
The heart of "useful at everything" on Linux is the command line. Design how an agent whose model is small and local can run real commands without ever acting on the model's word alone.
- Study what exists: the utility sandbox (${REPO}/workbench/utility_sandbox.py: netns, Landlock, seccomp, copies), grants.py, home_reach.py, the Terminal mode of the foot (find it: typebar_qt.py, console_qt.py and what they call: 0.7.0 had a list of read-only Terminal commands "held to reading forms"), assignments.py's verify step.
- Propose the mechanism concretely: (a) a COMMAND TOOL in her registry: the model (or a recipe) proposes argv, never a shell string; the desk parses it against a table of known commands (which flags only read, which change, which are destructive, which need root, which reach the network) and REFUSES what it cannot classify; (b) read-only commands run at once inside a sealed reader (Landlock read-only on what the owner can read, no network unless granted), their output returned as DATA through the same doorway as a fetched page (prompt-injection in a file's contents or a command's output must never become instructions); (c) changing commands shown to the owner in plain words AND as the exact command ("this will: … / the command: …"), run only on the press or under a grant, with a dry run first where the tool has one (rsync -n, apt -s, mv -n ...), a snapshot or Undo where possible (the bin, a copy, a revision), and a VERIFIER per command family; (d) system changes (apt, systemctl, usermod, mount, ufw) only through polkit/pkexec with the owner present at the system's own prompt, never under a standing grant, one command per prompt, and what a minimal root helper (a fixed, audited list of actions with typed arguments, not "run anything as root") looks like; (e) what is NEVER run (rm -rf /, dd to a disk, curl | sh, chmod -R 777 /, anything writing to /etc/sudoers, anything the table does not know with a change-shaped flag), and how pipes, redirection, globbing, sudo, env, xargs, find -exec and subshells are handled (argv only: no shell; a small pipeline form the desk composes itself).
- Give the classification table for the 80 most useful commands (ls, find, du, df, grep, cat, head, file, stat, wc, sort, diff, cp, mv, mkdir, rm, ln, chmod, chown, tar, zip/unzip, gzip, rsync, convert/magick, ffmpeg, pdftk/qpdf, pdftotext, pandoc, soffice --convert-to, apt/apt-get/apt-cache/dpkg, systemctl, journalctl, ps, top/free, kill, ip, ping, nmcli, ss, lsblk, mount/umount, udisksctl, lpstat/lp, bluetoothctl, timedatectl, crontab/systemd-run timers, git, python3, pip, curl/wget ...): for each, the read-only forms, the changing forms, the verifier, the undo.
- Try in this container what you can: write a prototype classifier (a Python file under ${OUT}/proto/) for 20 of those commands and run 60 command lines through it, including hostile ones, to show what it accepts and refuses. Say what Landlock/seccomp/netns give here (the K6 notes: ${REPO}/wip/2026-11-26_b100_saved/K6.progress.md).` },
  { key: 'grounding', prompt: `YOUR TOPIC: GROUNDING KAS IN THE MACHINE'S OWN KNOWLEDGE (write ${OUT}/scout_grounding.md).
A small local model does not reliably know command flags; a full Linux box carries its own truth: man pages, --help output, /usr/share/doc, info pages, apt's package descriptions, .desktop entries, bash completion files, tldr-style example pages (the Debian package tldr-pages or similar: say what Debian 13 ships). Design how Kas answers and plans FROM those, never from the model's memory.
- What is on a Debian 13 box and in what form (man-db, the mandb index, 'man -k', compressed roff under /usr/share/man; 'apropos'; dpkg -L; apt-cache show needs lists; debian's Contents files), how big (sizes: measure what this container has, whatever its distribution: count man pages, total size, time to convert one to text with man or mandoc or zcat + a roff stripper), and how to build a LOCAL SEARCH INDEX of it (Graphite already uses SQLite FTS5 with BM25 for its Library: find it, e.g. grep -rn fts5 ${REPO}/workbench | head; reuse the "Ask the Library" doorway: ${REPO}/docs/RELEASE_NOTES_0.8.7.md describes the model pointing at lines on pages).
- The retrieval design for a slow, small model: the request -> candidate commands by FTS over names, one-line descriptions and example pages (no model) -> the model PICKS one by number -> the desk shows the man page's own SYNOPSIS and the matching option lines -> the model picks options by number from the page's option list (pick, never write), so every flag she proposes exists on THIS machine's version. Token budgets per step at 4k to 8k context and about 30 tokens a second; what is cached in kept prompts.
- "Teach me": for a Windows-and-DOS person: a table DOS command -> Debian command built from real pages, and answers that always quote the page they came from.
- What she should know about THIS machine without asking a model: installed packages and versions, apps (.desktop), services, hardware (lspci/lsusb/lsblk output), disks and free space, recent logs: a "machine facts" store refreshed in the background, searchable by her dictionary.
- Prototype in this container: build an FTS5 index over whatever man pages and --help outputs exist here (under ${OUT}/proto/), run 30 plain requests ("find big files", "resize an image", "merge pdfs", "see what uses memory", "unpack a tar.gz" ...) and report how often the right command is in the top 5 with no model at all.` },
  { key: 'model', prompt: `YOUR TOPIC: WHAT A SMALL LOCAL MODEL CAN RELIABLY DO, MEASURED (write ${OUT}/scout_model.md).
Kas's usefulness must not depend on the model being clever. Find the shapes of question a 4B to 35B local model answers RELIABLY, by measuring on the real 4B here.
- Read how questions are asked today: ${REPO}/workbench/turns.py, model_turn.py, brain_briefs.py, objective_plan.py (the PLAN grammar and the primed menu), model_exam.py (the exam kinds and thresholds), and the results so far: ${REPO}/wip/2026-11-26_b100_saved/K4b.progress.md, K10.progress.md, K10.live_rerun_coordinator.log, M2.progress.md (the 2B failed its exams; the 4B's READ and NEXT numbers), X1.account.md (the 4B's PLAN dropped a step).
- EXPERIMENT, once, short, with the real 4B: the model file is ${S}/models/Qwen3.5-4B-Q4_K_M.gguf and the runtime ${S}/work/rt/llama-b12359/llama-server (llama.cpp v1.0.0). Hold the machine's model lock for the whole run: flock ${S}/work/model.lock <your script>. Start llama-server yourself on 127.0.0.1 with a free port (-c 4096, --jinja, --reasoning off if the flag exists: check --help; 4 threads), use its /completion or /v1/chat/completions endpoint with a GBNF grammar or JSON schema to force the answer shape, temperature 0. Keep the whole run under 25 minutes; other agents share the 4 cores, so expect slowness and say so.
  Measure these four shapes on about 30 items each, items you write yourself from the task families of a Linux box (files, documents, pictures, software, system, troubleshooting), with the right answer decided beforehand:
  (1) PICK ONE: the request plus a numbered list of 12 recipes (one line each) -> the number of the recipe, or 0 for none. (2) FILL SLOTS: the request plus a chosen recipe with 2 to 4 typed slots (a folder, a file pattern, a size, a format) -> each slot filled ONLY with words from the request or a value from a short list. (3) ORDER/COMPOSE: the request needs two or three recipes in order ("unzip this then convert the pictures"): -> a list of numbers. (4) YES/NO/CANNOT TELL over a short text (a command's output or a log excerpt): "does this show the disk is full?".
  Report accuracy, harmful errors (a wrong pick that would change something), tokens in and out, seconds per answer, and how each varies with list length (12 versus 30 recipes for shape 1 if time allows).
- Conclude: which shapes the design may lean on, with what guard (the desk's check, the exam), which it must not; how many recipes can be offered at once; whether free-form command writing should ever be asked of the model; what the 35B changes (it cannot run here: argue from the 4B's numbers and say what must be measured on the ThinkPad). Delete nothing of the shared model or runtime; stop your server when done.` },
]

phase('Scout')
const scouts = (await parallel(SCOUTS.map(s => () =>
  agent(CONTEXT + '\nYOU ARE A SCOUT for the design of Kas 1.1. ' + s.prompt + '\nReturn the structured result when your notes are written.',
    { label: 'scout:' + s.key, phase: 'Scout', schema: SCOUT_SCHEMA }).then(r => (r ? { key: s.key, ...r } : null))
))).filter(Boolean)
log(scouts.length + ' of ' + SCOUTS.length + ' scouts returned')
const lost = SCOUTS.map(s => s.key).filter(k => !scouts.some(x => x.key === k))
if (lost.length) log('NOT RETURNED: ' + lost.join(', '))

const scoutDigest = scouts.map(s => `## Scout "${s.key}": ${s.topic}\n${s.summary}\nFACTS:\n- ${s.key_facts.join('\n- ')}\nRECOMMENDS:\n- ${s.recommendations.join('\n- ')}\nFULL NOTES: ${s.file}`).join('\n\n')

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    one_line: { type: 'string' },
    pillars: { type: 'array', items: { type: 'string' }, description: 'the 4 to 7 ideas the design stands on' },
    what_she_can_do: { type: 'array', items: { type: 'string' }, description: 'the capability families of 1.1, each one line with an example request' },
    authority_changes: { type: 'array', items: { type: 'string' }, description: 'every change to her authority rules compared with 1.0 (e.g. system changes through polkit), each with its guard' },
    slices: { type: 'array', items: { type: 'string' }, description: 'build slices in order, one line each: key (KS1...), name, the files it mostly adds or touches, depends on, acceptance' },
    not_in_1_1: { type: 'array', items: { type: 'string' } },
    needs_real_hardware: { type: 'array', items: { type: 'string' } },
    file: { type: 'string' },
  },
  required: ['one_line', 'pillars', 'what_she_can_do', 'authority_changes', 'slices', 'file'],
}

phase('Architect')
const design = await agent(`${CONTEXT}
YOU ARE THE ARCHITECT of Kas 1.1. Five scouts have reported (their findings are below; read their FULL NOTES files before you write). Design how Kas becomes "very useful at everything in a world where a full loaded Linux box is the computer I use", for an owner who is a Windows-and-DOS person, with a small local model, without weakening the owner's authority.

Write ${OUT}/KAS_1.1.draft.md (about 3,000 to 4,000 words): 1. The idea in a paragraph: what changes in what she IS. 2. What she can do in 1.1, by family, each with three example requests and what the owner sees happen. 3. The mechanism: recipes (a library of verified, parameterised task recipes with preconditions, steps, dry run, verifier and undo: the format, where they live, how the owner and Kas add new ones), the command tool and its classifier, the sealed reader, the system door through polkit and the fixed root helper, grounding in the machine's own pages, machine facts, automation (schedules, watchers, reminders: how a standing task is granted, shown, stopped), memory (what worked before, the owner's preferences, in readable files). 4. How a request flows, end to end, with NO model, with the 4B, with the 35B: who decides what at each step, the token budget and the time. 5. Teaching: how every action shows the Debian command behind it and its DOS or Windows equivalent, and how "teach me" answers from the machine's pages. 6. The authority rules restated for 1.1, and every change from 1.0 with its guard. 7. Her exam, extended: what must be measured on the owner's machine before each new kind is trusted. 8. What the owner sees: her column, the plan, the command preview, the permission prompt, the journal (words only: the screen design is another panel's). 9. The 40 first recipes, as a table: name, family, tools, reads/changes home/changes system, verifier, undo. 10. The build: 10 to 16 slices in order (keys KS1, KS2, ...), each with the files it adds or touches in ${REPO}/workbench/, what it depends on, what it must not collide with, and its acceptance in two lines (examples a smoke script can check). 11. What is deliberately NOT in 1.1. 12. What only the owner's machine can settle.

Decide; do not list options. Where the scouts disagree, say which you followed and why. Design for the 4B's measured reliability, so the 35B is a bonus.

THE SCOUTS:
${scoutDigest}`, { label: 'architect', phase: 'Architect', schema: DESIGN_SCHEMA })

if (!design) return { scouts, error: 'the architect did not return' }

const ATTACK_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    breaks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' }, severity: { type: 'string', enum: ['fatal', 'serious', 'minor'] },
          scenario: { type: 'string', description: 'concrete: the request, the state, what goes wrong' },
          fix: { type: 'string' },
        },
        required: ['title', 'severity', 'scenario', 'fix'],
      },
    },
    missing: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'breaks'],
}

phase('Attack')
const SKEPTICS = [
  { key: 'security', who: `THE SECURITY SKEPTIC. Assume the model is wrong, the web is hostile, file names and file contents are written by an attacker, and the owner presses "yes" when tired. Find how this design gets the owner's machine or data damaged or their secrets sent out: a recipe slot filled with "; rm -rf ~" or "$(...)" or "--output=/etc/passwd"; option injection through file names beginning with "-"; a command the classifier calls read-only that writes (find -delete, sed -i, tee, sort -o, tar with --to-command, git with hooks, less with LESSOPEN, man with a pager, awk system(), xargs); symlinks out of the home; the dry run differing from the real run; the root helper's arguments; polkit prompts the owner learns to click through; standing grants for automation that widen over time; a watcher triggered by an attacker-controlled download; prompt injection through man pages? through a PDF she reads, a fetched page, a log line, a file NAME; the undo that does not undo; verifiers that can be fooled. For each: the concrete scenario and the fix. Read the scouts' prototype classifier (${OUT}/proto/) and try to defeat it on paper or by running it on hostile lines in a throwaway folder.` },
  { key: 'usefulness', who: `THE USEFULNESS SKEPTIC. You are the owner: decades of Windows and DOS, an engineer, new to Debian, with a slow local model. You will judge Kas in the first two weeks by whether she saves you time or wastes it. Walk twenty real requests through the design, including vague ones ("my wifi is acting up", "clean up this mess", "make this smaller", "the printer won't print", "I need the thing I did last week again"), ones that need a follow-up question, ones in DOS words, ones with typos, and ones no recipe covers. Where does she say "I cannot" when she should try? Where does she ask for five presses for a trivial thing, so you stop using her? Where is she slow (count the model turns and seconds at 30 tokens a second)? Where does the safety design make her useless, and what would give the same safety with less friction? What is the first thing you would ask that is simply missing? Say what would make you call her a superpower, concretely.` },
]
const attacks = (await parallel(SKEPTICS.map(k => () =>
  agent(`${CONTEXT}
YOU ARE A SKEPTIC reviewing the draft design of Kas 1.1 before it is built. YOUR LENS: ${k.who}

Read the full draft (${design.file}) and the scouts' notes it rests on (${scouts.map(s => s.file).join(', ')}). Try to BREAK the design, not to praise it. Report only breaks with a concrete scenario, most severe first (at most 20), and what is missing.`,
    { label: 'skeptic:' + k.key, phase: 'Attack', schema: ATTACK_SCHEMA }).then(r => (r ? { skeptic: k.key, ...r } : null))
))).filter(Boolean)
log(attacks.map(a => a.skeptic + ': ' + a.breaks.length + ' breaks (' + a.breaks.filter(b => b.severity === 'fatal').length + ' fatal)').join('; '))

phase('Revise')
const revised = await agent(`${CONTEXT}
YOU ARE THE ARCHITECT of Kas 1.1 again. Two skeptics attacked your draft (${design.file}). Revise it into the final design: answer EVERY fatal and serious break, either by changing the design (say where) or by showing why the scenario cannot happen (with the code or mechanism that prevents it); take the missing items that belong in 1.1. Keep it one coherent design: do not bolt on a list of patches. Where the security skeptic and the usefulness skeptic pull apart, find the mechanism that gives the safety with less friction, or decide and say what was given up.

Write the final document to ${OUT}/KAS_1.1.final.md (the whole design, revised, same sections, plus a last section "What the skeptics found and what changed", a table: the break, fatal/serious, the answer). Update the build slices and their acceptance so that each security answer is something a builder must implement and a smoke script must check.

THE BREAKS:
${attacks.map(a => `## ${a.skeptic}: ${a.verdict}\n` + a.breaks.map((b, i) => `${i + 1}. [${b.severity}] ${b.title}: ${b.scenario} -> ${b.fix}`).join('\n') + `\nMISSING: ${(a.missing || []).join(' | ')}`).join('\n\n')}

Then return the structured summary of the FINAL design (the 'file' field is the final document's path).`, { label: 'architect:revise', phase: 'Revise', schema: DESIGN_SCHEMA })

return { scouts: scouts.map(s => ({ key: s.key, summary: s.summary, file: s.file })), lost, draft: design.file, attacks, final: revised || design }
