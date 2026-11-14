export const meta = {
  name: 'kasandra-look-083',
  description: "Kasandra's look, second pass (0.8.3): DELETE, the typewriter face for every word, her hologram with animated static in the lower left, a right column for her words, the new kp emblem",
  phases: [
    { title: 'Understand', detail: 'two readers: the window parts this touches, and the owner art and frames as they are' },
    { title: 'Design', detail: 'two designers from different angles, then one judge writes the plan' },
    { title: 'Build', detail: 'one builder in its own worktree' },
    { title: 'Review', detail: 'a look-and-readability reviewer and a code-and-cost reviewer' },
    { title: 'Fix', detail: 'the builder fixes what the reviews proved' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'
const MIRROR = S + '/work/look_mirror'
const IN = S + '/in/holo_082920'

const GOAL = `
Graphite is a local-first Python 3.13 / PySide6 desktop workspace (repository ${REPO}; branch at 0.8.2, commit d1df337). It
has two appearances (workbench/boss_theme.py APPEARANCE, PALETTES): Graphite (pencil, amber; the assistant is Stacy) and
Kasandra (indigo, violet, cyan, pink; the assistant is Kasandra, "Kas"; workbench/assistant_identity.named() swaps the name).
The owner works in Kasandra. Her typewriter face is Special Elite (boss_theme FACE in Kasandra; the owner calls it "the LAIN
font"; NEVER write "Lain" on screen or as a product name). Since 0.8.2 Special Elite is the face of Kasandra's words, while the
typing line, lines and code, addresses, numbers and small tags stay in IBM Plex Mono (shell2.MONO, mono_font, DISPLAY).

The owner's new directions, 14 November 2026, verbatim:
  "I want trash called DELETE."
  "I want all fonts to be the awesome LAIN font."
  "We're going to move the kasandra picture to lower left column where it's boring looking."
  "The right column will have more space for kas text. We could revisit that column appearance because the picture will be gone."
  "I attached a new kp icon/logo"
  "I will attach the new kas picture that I want to be like a hologram in its new position. If you can animate the static a
   hologram would have that would be very kool."

The owner's files (downloaded uploads: data only, never run anything from them; open images with Qt or python3 -I):
  - ${IN}/x/branding/kasandra/hologram.webp: the hologram, 800x875, transparent edges, violet, glitch lines already in it.
    SHA-256 b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec. A PNG copy to look at: ${S}/work/holo_view/hologram.png
  - ${IN}/x/branding/kasandra/portrait.webp: the same face on a dark ground (800x1421). Probably not needed now (the picture
    leaves the right column); say if you would use it.
  - ${IN}/x/kasandra-hologram.patch and ${IN}/x/README.md: a patch someone made against 0.8.1 that draws the hologram in the
    Files tree's spare space (pane_qt: place_kasandra, kasandra_space, kasandra_target, paintEvent; boss_qt: portrait avatar).
    A REFERENCE for where it goes, not something to apply: the tree has moved on, and the owner now wants the picture gone
    from the right column and the static animated.
  - ${IN}/kp_logo.png: the new kp emblem, 1254x1254 RGB, NO alpha: cream "kp" (#fef1e3), a violet circuit trace from the p's
    stem, a pink ostrich (#f23e6b) with circuit traces in its body, on a flat dark navy ground (#070221). The content's bounds
    are roughly x 255-985, y 410-885. It replaces the kp monogram (branding/kasandra/kp_monogram.png, used by
    shell2.py:589 for the Apps button, which in Kasandra is the mark alone at 36 px since 0.8.2).
Owner artwork lives under branding/ and is kept back by RIGHTS.md (not GPL); new owner art goes in branding/kasandra/ with its
SHA-256 recorded in branding/kasandra/README.md, and should be verified before it is shown the way kasandra_art verifies stills.

Owner rules that hold: the window never names the line language (staC/stac): "a line". No keyboard key or shortcut is printed
on screen (keys still work). "Apps", never "Programs". Nothing is removed to make things simple. Motion follows the
after-hours rule (workbench/menu_catch.calm, the reading profile's reduce_motion, the Clean glow / desk art): it helps, never
slows a hand that knows the way, and with Reduce motion it lands straight on a still frame; the Clean desk shows no artwork.
`

const READ_RULES = `
You are a reader. Do not edit anything under ${REPO}. Scratch only under ${S}/work/look_read/<your part>/. To run code, make a
copy with "git -C ${REPO} archive HEAD | tar -x -C <dir>" and run only inside "QT_QPA_PLATFORM=offscreen unshare --pid --fork
--mount-proc --kill-child ${PY} -B ..."; never run tools/check_*_ui.py anywhere. Cite file:line for every claim. Return a
Markdown map (plain words, tables welcome), no preamble.
`

const R1 = GOAL + READ_RULES + `
YOUR PART: the code this pass touches. Map exactly:
(1) Every word on screen that says Trash or trash (labels, rows, tips, captions, help, act words in workbench/desk_acts.py,
    confirmations, the can in the left column: workbench/trash_can_qt.py, the right-click: workbench/context_menu.py, Files,
    Library, documents), with file:line and the exact string; and every OTHER on-screen "Delete"/"Remove" that already means
    something else (a document's Delete row, a key, a Kernel operation's words), so DELETE does not collide.
(2) Every place a font family is chosen: boss_theme FACE/DISPLAY/MONO and its stylesheets, shell2 SANS/MONO and mono_font,
    reading_preferences.apply and the reading profile, field_qt fonts (sans(), display(), mono numbers), console_qt and
    typebar_qt, the Terminal page, pane_qt trees, menus, context_menu metrics, tool_faces, programs_qt, every QFont('...') or
    font-family literal in workbench/*.py. For each, say what it shows (words, numbers, a line, code, a table, Terminal output)
    and whether a proportional face would break an alignment (columns of Terminal output, mono-width measurements,
    elision math, fixed-width layouts).
(3) The right column in Kasandra: the widgets from the face picture down (boss_qt ArtPanel kinds 'face' and 'journal',
    kasandra_still, the 'assistant_rail' slot, the name and dial words, the cards of her Talk, her trail, what fills it at
    1920x1200 and 1366x768), its width and how the width is decided; and where else her stills appear (the Field's rail,
    Home/Office, Today).
(4) The left column: the nav dock, Files/Machine/Settings tabs, the cabinet tree (pane_qt: the tree class, set_metrics,
    breathing, the Kasandra telephone-pole painting), the Trash can widget at its foot, and how much empty space is under the
    tree on After Hours 07 at both sizes (measure it).
(5) workbench/kasandra_art.py (folder, catalog, byte verification), branding/kasandra/README.md and catalog.json, and how a
    new file (hologram, emblem) would be verified the same way.
(6) The kp monogram's uses (Apps button, any wordmark, window icon) and their sizes.
(7) The tests that pin any of the above (grep tests_integrated for Trash, kp_monogram, FACE, MONO, ArtPanel, face, the
    programs button): file:line and what each asserts, so the builder knows what must change with the owner's direction.
`

const R2 = GOAL + READ_RULES + `
YOUR PART: the look as it is, in frames. Using the probe harness ${S}/tools/field/nomodel.py (read it first; it restores the
After Hours 07 workspace into a throwaway profile; a probe script it runs gets the live window as w and helpers such as
settle; examples: ${S}/tools/field/kasandra_probe.py, ${S}/tools/field/catch_shots.py), run, from your own copy of the tree:
  GRAPHITE_APPEARANCE=kasandra REHEARSAL_MODEL=x REHEARSAL_SCRIPT=<your script> PYTHONUNBUFFERED=1 QT_QPA_PLATFORM=offscreen \\
  unshare --pid --fork --mount-proc --kill-child ${PY} -u -B ${S}/tools/field/nomodel.py <your tree> <out dir> 1920 1200
and the same at 1366 768. Take frames of: the whole window on Home, on the Field, on Files; the left column alone; the right
column alone (with a few Talk cards in it if you can put some there without a model, e.g. her trace of a sheet as in the
Field's Trace); the head's Apps mark close up. Look at each frame (read the PNGs) and describe plainly what is there, what is
empty or dull, how much room her words get, and how the typewriter face and the mono face sit together. Also look at
${S}/work/holo_view/hologram.png and ${IN}/kp_logo.png and describe them for a designer (proportions, colours, where the alpha
is, what would survive at 36-48 px tall). Measure: the empty height under the tree at both sizes; the right column's width
and how many characters of her text fit per line now. List the frames you saved (absolute paths) so designers can open them.
`

const DESIGNER = (angle, m1, m2) => GOAL + `
Two readers mapped the code and the look:
=== THE CODE ===
${m1}
=== THE LOOK, IN FRAMES ===
${m2}
===
You are a designer with this angle: ${angle}
Open the frames the second reader listed (read the PNGs) and the owner's two images. Read-only for ${REPO}; scratch under
${S}/work/look_design/. Write a design (Markdown) that a builder can build, covering ALL six points:
(a) DELETE: the exact words everywhere Trash was (the can's label, rows, tips, acts' words, help), casing, what the can's tip
    says so it is clear that what is there can still be brought back, and how any existing "Delete" that means something else
    is renamed so the two never meet. Both appearances (the owner's word is general); internal names (files.trash, the act
    hand.trash, row keys) do not change.
(b) Every font the typewriter face, in Kasandra: what changes, where alignment matters (Terminal output columns, tables,
    numbers in the Field, elision math) and how it is kept right with a proportional face, sizes and letter spacing per role
    so it stays readable at 1366x768 (1/l/I and 0/O must stay distinguishable). The owner's own reading faces, if chosen,
    still win. Graphite keeps its faces.
(c) The hologram in the lower left: exact placement under the Files tree and above DELETE, size limits at both window sizes,
    when it steps aside (the tree needs the room, another left tab, the Clean desk), and THE ANIMATED STATIC: each effect
    (for example scan lines drifting, a soft flicker, rare horizontal tears, a chromatic split, a projection base or beam,
    noise), its rate and amplitude in numbers, how the state of the work could show in it (idle, working, waiting for the
    owner, a refusal; the 0.8.0 idea of "art by the state of the work" carried into the hologram), what Reduce motion and the
    Clean desk do, and a CPU budget with the means to meet it (frame rate, cached layers, paint only its rect, stop when
    hidden, minimised or inactive).
(d) The right column with the picture gone: what is at its top instead (her name in the typewriter face, her state and dial
    words), how her Talk cards use the width and height they gain, the column's look (lines, plates, colour), at both sizes.
(e) The new kp emblem: how to make it transparent from the flat navy ground (an exact method: colour-distance alpha with
    unpremultiplying, or a redraw; edges must stay clean on indigo), the asset(s) to produce (sizes, format), and where it
    goes (the Apps button at what height and width; anything else, e.g. the window icon) and how it reads at that size.
(f) What tests change and what new tests pin (exact assertions), and the frames that prove it.
Be concrete: numbers, names, file:function. Return the design only.
`

const ANGLE_A = 'QUIET AND READABLE. The owner works long hours in this window; every change must keep reading effortless and the motion subtle (the hologram alive but never pulling the eye from the work), the right column calm and roomy.'
const ANGLE_B = 'AFTER HOURS, BOLD. The owner\'s mood piece "Graphite after hours": Lain, 2600, Unix, Hackers, Bubblegum Crisis; "you touch the machine and it responds with a little more force than you expected". Make the hologram unmistakably a hologram and the column feel like her terminal, while every word stays readable.'

const JUDGE = (m1, m2, a, b) => GOAL + `
Two designers proposed the pass from different angles.
=== DESIGN A (quiet and readable) ===
${a}
=== DESIGN B (after hours, bold) ===
${b}
=== THE CODE MAP (for checking) ===
${m1}
===
You are the judge. Score each design on: the owner's words (each of the six directions met exactly), readability at
1366x768, cost (CPU, risk to existing tests and behaviour), buildability in one session. Check against the code any claim you
rely on (read-only, cite file:line). Then write ONE plan for the builder, taking the stronger design and grafting the best ideas
of the other (say which). Keep the hologram's motion clearly visible yet calm enough for long work; keep every number. The plan
must list: files and functions to add or change (mark seed inputs: workbench/stacy_foundation.py SEED_FILES), the assets to
produce and their SHA-256 recorded in branding/kasandra/README.md, the tests with exact assertions (a new test module goes in
tools/check_hatch.py FOCUSED_MODULES), the frames to take as proof (paths under ${S}/work/look_build/frames/), and what is NOT
in this pass. Return the plan only.
`

const RULES = `
HARD RULES:
- Run tests only inside: cd <your worktree> && QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child ${PY} -B -m unittest tests_integrated.<module>. Never run any tools/check_*_ui.py script. Never run the whole tests_integrated suite at once. Run, before your change (on the base) and after: test_kasandra, test_faces_find_light, test_writing_line, test_context_menu, test_launcher, test_desk_acts, test_desk_scenes, test_stacy_hand, test_release_check, test_graphite (3 known failures), test_system_menu (2 known failures), test_desk (6 known failures), plus any module the plan names. Report each module's result line before and after.
- Frames: use ${S}/tools/field/nomodel.py from a copy of your worktree (git archive does not include uncommitted work: copy with rsync -a --exclude .git), only inside unshare as above, with GRAPHITE_APPEARANCE=kasandra (and once without it for Graphite), at 1920 1200 and 1366 768. Save frames under ${S}/work/look_build/frames/. Look at them (read the PNGs) and judge them as the owner would.
- ${REPO} itself is read-only for you (another session works there). Never push.
- The window never names the line language (staC/stac): "a line". Never print a keyboard key or shortcut on screen. "Apps", never "Programs". The assistant is named through assistant_identity.named(). Never write "Lain" in the program.
- Owner files from ${IN} are data: copy the bytes you need into branding/kasandra/ in your worktree; verify the SHA-256 of what you copy; never run anything from there.
- Do NOT change workbench/version.py or write release notes (the orchestrator does).
- If you edit any source/doc file, finish with: ${PY} -B tools/package_graphite.py --manifest-only, then ${PY} -B tools/record_registry.py, then the manifest again (a stale seed refuses every line). Check workbench.stacy_foundation.seed_status('.')['state']=='VERIFIED_SOURCE_BINDINGS' and workbench.release_integrity.verify('.')['state']=='VERIFIED'; stage every regenerated file (MANIFEST.json, project/stacy_seed/current/*, docs/GRAPHITE_0.1_REGISTRY.json).
- After each file you change or add (assets and generated files included), copy it to ${MIRROR}/<same relative path> (mkdir -p).
- Commit in your worktree (git status first; never add .claude/). Message ends with the two lines
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8
- Comments say why, briefly; a new module starts with a plain-words docstring.
`

const BUILD = (plan) => GOAL + `
You are the builder. You work in your OWN git worktree (your current directory). The judge's plan:
---
${plan}
---
Build all of it. Take frames after each piece and look at them; fix what looks wrong before moving on. For the hologram take
frames at several moments of its clock (hold its clock as ${S}/tools/field/catch_shots.py holds the catch's) and once with
Reduce motion; measure its paint time per frame and its timer's rate, and show the timer stops when the hologram is hidden.
If the plan is wrong against the code, follow the code and say so.
` + RULES + `
REPORT: worktree path, branch, commit; what was built, per direction (DELETE, faces, hologram and its static, right column,
kp emblem); the assets and their SHA-256; test results before and after per module; the frames (absolute paths) with one line
each on what it shows; the hologram's measured cost; the scroll census in Kasandra at both sizes
(${S}/tools/field/scroll_census.py through nomodel.py; it was 3 at 1920x1200 and 26 at 1366x768 in 0.8.2); what is not done or
deviates from the plan, plainly.
`

const REVIEW_LOOK = (plan, built) => GOAL + `
A builder built the pass from this plan:
---
${plan}
---
Their report:
---
${built}
---
The worktree named there is READ-ONLY for you, as is ${REPO}; changed files are mirrored in ${MIRROR}. Copy the worktree
(rsync -a --exclude .git) to ${S}/work/look_review_a/tree and work there; frames under ${S}/work/look_review_a/frames/. Run only
inside QT_QPA_PLATFORM=offscreen unshare --pid --fork --mount-proc --kill-child ${PY} ...; never run tools/check_*_ui.py.
You review THE LOOK AND READABILITY, as the owner would on a 1366x768 and a 1920x1200 panel. Take your own frames (do not trust
the builder's): Home, the Field (After Hours 07), Files, a right-click menu, the Then panel, the Terminal page with some output
(ls -l of a folder in the restored workspace, via the Terminal target if the harness allows; otherwise the console's own
page), a document page, the Field's REV A / REV B cut, the menus across the head, Apps, her column with cards, the left column
with the hologram (several moments of its clock, and Reduce motion), in Kasandra; and Graphite once to see nothing regressed
there except DELETE. Check: every word of Kasandra's window in the typewriter face (find any that is not); 1/l/I and 0/O
distinguishable; nothing clipped, cut mid-word or overlapping; the scroll census at both sizes against 0.8.2's 3 and 26; DELETE
everywhere Trash was, and no two different meanings of Delete; the hologram reads as a hologram and its static moves without
tiring the eye; the emblem's edges are clean on indigo at its size; the right column gives her words room. Also run the crawler
in Kasandra (CRAWL_MODE=icons, ${S}/tools/field/crawl_probe.py through nomodel.py at 1366 768, timeout 1700) and report crashes
or tracebacks. Report findings MOST SEVERE FIRST, each with the frame path or command and output, and a concrete fix. Say
plainly what holds. Do not fix anything.
`

const REVIEW_CODE = (plan, built) => GOAL + `
A builder built the pass from this plan:
---
${plan}
---
Their report:
---
${built}
---
The worktree named there is READ-ONLY for you, as is ${REPO}; changed files are mirrored in ${MIRROR}. Copy the worktree
(rsync -a --exclude .git) to ${S}/work/look_review_b/tree and work there. Run only inside QT_QPA_PLATFORM=offscreen unshare
--pid --fork --mount-proc --kill-child ${PY} ...; never run tools/check_*_ui.py.
You review THE CODE AND ITS COST. Read the diff (git -C <worktree> diff d1df337..HEAD). Check: (1) the hologram's animation:
measure paint time per frame and frames per second on the live window; prove the timer stops when the left tab changes, the
tree needs the room, the window is minimised or hidden, Reduce motion is on, the desk is Clean, and in Graphite; no repaint of
the whole window per tick; no leak (timers, images) across appearance or tab changes. (2) art verification: the hologram and
emblem bytes are checked against recorded SHA-256 before they are shown, and a missing or changed file shows nothing and
breaks nothing. (3) fonts: a proportional face where code measured mono widths (elision, column alignment, fixed widths);
the owner's own reading faces still win; Graphite unchanged. (4) DELETE: every on-screen Trash word changed and nothing
internal renamed (files.trash, hand.trash, row keys, settings keys, stored data, the desk acts' MENU_ROWS keys); help and act
words consistent; no "staC" or printed key or "Programs" introduced. (5) the release: seed state, release_integrity.verify,
FOCUSED_MODULES, test_release_check, and every module the builder ran, run again and compared with the base. Report findings
MOST SEVERE FIRST, each with evidence (command, output, file:line) and a concrete fix. Say plainly what holds. Do not fix
anything.
`

const FIXUP = (built, reviewA, reviewB) => `
You built Kasandra's look pass (0.8.3) in a git worktree. Your report:
---
${built}
---
Two reviewers attacked it.
=== THE LOOK AND READABILITY ===
${reviewA}
=== THE CODE AND ITS COST ===
${reviewB}
===
Work in THAT SAME worktree (cd to the path in your report; do not create another). Reproduce each proven finding, fix it, show
the same check passing; for a finding you judge wrong, say why with evidence. Re-run the modules and the frames, rebuild the
seed and manifest, commit (a new commit), keep the mirror current.
` + GOAL + RULES + `
REPORT: worktree path, branch, final commit; per finding fixed or not (file:function, evidence); final test results per module;
the final frames (absolute paths) with one line each; the hologram's final cost; the scroll census; what is still not done.
`

phase('Understand')
const [m1, m2] = await parallel([
  () => agent(R1, { label: 'read:code', phase: 'Understand' }),
  () => agent(R2, { label: 'read:frames', phase: 'Understand' }),
])
if (!m1 || !m2) return { m1, m2, plan: null }
phase('Design')
const [dA, dB] = await parallel([
  () => agent(DESIGNER(ANGLE_A, m1, m2), { label: 'design:quiet', phase: 'Design' }),
  () => agent(DESIGNER(ANGLE_B, m1, m2), { label: 'design:after-hours', phase: 'Design' }),
])
if (!dA && !dB) return { m1, m2, plan: null }
const plan = await agent(JUDGE(m1, m2, dA || '(missing)', dB || '(missing)'), { label: 'judge:plan', phase: 'Design' })
if (!plan) return { m1, m2, dA, dB, plan: null }
phase('Build')
const built = await agent(BUILD(plan), { label: 'build:look', phase: 'Build', isolation: 'worktree' })
if (!built) return { m1, m2, dA, dB, plan, built: null }
phase('Review')
const [rA, rB] = await parallel([
  () => agent(REVIEW_LOOK(plan, built), { label: 'review:look', phase: 'Review' }),
  () => agent(REVIEW_CODE(plan, built), { label: 'review:code', phase: 'Review' }),
])
phase('Fix')
const fixed = await agent(FIXUP(built, rA || '(the look review did not report)', rB || '(the code review did not report)'), { label: 'fix:look', phase: 'Fix' })
return { m1, m2, dA, dB, plan, built, rA, rB, fixed }
