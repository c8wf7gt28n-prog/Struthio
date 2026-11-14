export const meta = {
  name: 'kasandra-083-finish-yellow-and-neon',
  description: "Finish 0.8.3: the burnt-yellow highlight in Kasandra (a solid bar in menus, an edge elsewhere, never green), the owner's neon kp logo as the only kp mark with a glow Graphite draws, every other kp mark retired",
  phases: [
    { title: 'Build', detail: 'one builder in its own worktree' },
    { title: 'Review', detail: 'a look reviewer and a code reviewer' },
    { title: 'Fix', detail: 'the builder fixes what the reviews proved' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const PY = S + '/work/venv/bin/python'
const REPO = '/home/user/Struthio'
const MIRROR = S + '/work/yellow_mirror'

const GOAL = `
Graphite (repository ${REPO}, branch head bbf033b: 0.8.2 plus Kasandra's look pass) is a PySide6 desktop workspace with two
appearances (workbench/boss_theme.py PALETTES 'graphite' and 'kasandra'). This pass finishes 0.8.3 with two owner directions.

ONE. The owner: "I'm kinda thinking that highlighting should be in our burnt yellow??? Like especially in menus???", then "You
measure what is visually pleasing", and "we have to be careful how that makes the graphite not look green". Decided and measured
(WCAG contrast, HSL hue; candidates rendered in ${S}/work/yellow/yellow_options.png):
  - Kasandra only. The Graphite appearance does not change at all (its amber and green stay exactly as they are).
  - Menus (QMenu across the head and dropped from it, the right-click workbench/context_menu.py rows, the Apps list
    workbench/programs_qt.py DeskMenu, the writing line's results list shell2.ResultsPopup): the row you are on is a SOLID
    burnt-yellow bar #e2a72e with dark ink #171b3c (7.79:1), a 2 px edge #ffd27a; its glyph drawn so it reads on the bar.
  - Everywhere else a highlight or focus shows (selected rows in lists and trees, selected tabs, checked buttons, focus outlines,
    the keyboard's place): the burnt-yellow EDGE AND WORDS: fill #5a3f0c, edge #e2a72e, words #ffd27a (6.86:1 words on fill;
    edge 7.79:1 on the ground #171b3c).
  - NEVER green: yellow must never be laid translucently over cyan (#83eaff) or the old blue fill (#1d3d63): measured, 30-50 %
    yellow over those gives hue 86-156 (green). Every highlight fill is opaque; where a highlight used to be cyan, the cyan is
    replaced, not tinted. Over her indigo grounds even half-strength yellow stays warm (hue 28-37).
  - In Kasandra the tokens AMBER, AMBER_SOFT, AMBER_EDGE, AMBER_TEXT carry focus and highlight (they were cyan there); about 150
    uses across workbench/. Hover (TEAL_SOFT/READY) and other cyan meanings (ready, the line, links) stay cyan unless a place is
    a highlight. Check every use and decide; list the decisions.
TWO. The owner sent a new logo: "New logo for our upper right progman.exe menu ;) ... Omg I love it", then "Retire any other kp
icon". The file: ${S}/in/logo_neon/kp_neon.png (owner upload: data only), SHA-256
70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e, 1586x992 with real alpha. IMPORTANT: its neon fringe is stored
in pixels with alpha 1 (of 255) carrying saturated colour: drawn correctly it vanishes, and literally restored it turns to grey
mush (measured: ${S}/work/neon/kp_neon_choices.png). Decided (mock: ${S}/work/neon/kp_neon_drawn_view.png):
  - The asset is the CLEAN drawing: the pixels with alpha >= 200, trimmed to the content (about x 102-1504, y 80-918), saved in
    branding/kasandra/ with the source's SHA-256 and the derived files' SHA-256 recorded in branding/kasandra/README.md, verified
    before it is shown as the look pass verifies its art (workbench/kasandra_art.py).
  - Graphite DRAWS the neon glow around it: a wide soft glow and a close glow in each part's own colour, a cyan ghost a little to
    the left and a magenta ghost a little to the right (Screen), scaled by the Glow dial (boss_theme.glow()), none on the Clean
    desk or Clean glow. It may catch with the menu catch when Apps opens (workbench/menu_catch.py); with Reduce motion it is still.
  - It is the Apps button in the head's upper right, about 44 px tall (about 74 px wide), its tip still "Apps"; it must read at
    1366x768 and 1920x1200.
  - It is the ONLY kp mark. Retire every other: branding/kasandra/kp_monogram.png, and the look pass's cream emblem and its
    derivatives (kp_emblem.png, kp_emblem_38.png, kp_emblem_76.png, kp_emblem_small.png, kp_emblem_source.png, kp_tile.png,
    kp_tile_letters.png and any tool that makes them, e.g. tools/cut_kp_emblem.py), their README lines and hashes. The window's own
    icon goes back to Graphite's sharpened point (workbench/qt_app.py window_icon) in both appearances; the game keeps its own.
    grep for every remaining use (kp_monogram, kp_emblem, kp_tile, monogram) and port the tests that pin them
    (tests_integrated/test_kasandra.py and the look pass's tests) to the neon logo.
Owner rules: no keyboard key printed on screen; the line language never named on screen ("a line"); "Apps", never "Programs";
never "Lain" in the program.
`

const RULES = `
HARD RULES:
- Tests only inside: cd <your worktree> && QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child ${PY} -B -m unittest tests_integrated.<module>. Never run tools/check_*_ui.py anywhere. Never the whole suite at once. Run before (on the base) and after: test_kasandra, test_hologram, test_kasandra_column, test_typewriter_faces, test_delete_words, test_faces_find_light, test_context_menu, test_launcher, test_writing_line, test_release_check, test_graphite (3 known failures), test_system_menu (2 known), test_desk (6 known), and any module you touch.
- Frames: ${S}/tools/field/nomodel.py from a copy of your worktree (rsync -a --exclude .git), inside unshare as above, GRAPHITE_APPEARANCE=kasandra and once Graphite, at 1920 1200 and 1366 768; save under ${S}/work/yellow_build/frames/; look at them. Show: an open menu across the head, the right-click with its line panel, Apps open, the writing line's results, a tree and a list with a selection, a selected tab, a focused field, the head's right end with the logo (and zoomed x3), Graphite unchanged.
- Measure in numbers: contrast of every highlight's ink on its fill, and the hue of every highlight pixel cluster in the frames (none between 70 and 170 degrees in Kasandra).
- ${REPO} is read-only for you. Never push. Do not change workbench/version.py or write release notes.
- After any change: ${PY} -B tools/package_graphite.py --manifest-only, then ${PY} -B tools/record_registry.py, then the manifest again; seed_status 'VERIFIED_SOURCE_BINDINGS' and release_integrity.verify 'VERIFIED'; stage every regenerated file. Mirror each changed or added or deleted file's state to ${MIRROR}/<path> (for a deletion, write <path>.DELETED).
- Commit in your worktree (git status first; never .claude/). Message ends with:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8
`

const BUILD = GOAL + `
You are the builder, in your OWN git worktree (your current directory). Build ONE and TWO. Use the existing places: the
theme tokens and stylesheets (boss_theme, theme2), the custom-painted menus (context_menu row paint near the class whose
paintEvent fills AMBER_SOFT; programs_qt DeskMenu; shell2.ResultsPopup), the Apps button (shell2 near the programs button),
kasandra_art for verification. Add tests: Kasandra's highlight tokens and their contrast (bar ink >= 7:1, edge words >= 6.5:1),
Graphite's tokens unchanged, every highlight fill opaque, the neon logo verified and drawn with glow scaled by glow() and none at
0, no file or reference left for the retired marks.
` + RULES + `
REPORT: worktree, branch, commit; each AMBER_* use and what it became; the logo asset and its hashes; what was retired; tests
before and after per module; frames (absolute paths) with one line each; the measured contrasts and hues.
`

const REVIEW = (who, built) => GOAL + `
A builder built this pass. Their report:
---
${built}
---
The worktree named there is READ-ONLY for you; copy it (rsync -a --exclude .git) to ${S}/work/yellow_review_${who}/tree and work
there, only inside QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child ${PY} ...; never run
tools/check_*_ui.py.
` + (who === 'look' ? `You review THE LOOK. Take your own frames in Kasandra and Graphite at both sizes (as listed in the build
rules: menus, the right-click and its line panel, Apps, the writing line's results, trees, lists, tabs, focus, the head's logo
zoomed). Judge as the owner would: is the burnt yellow pleasing and clearly the highlight, does anything look green or muddy,
is any word on a highlight hard to read, does the logo read at 44 px and glow without smudging, is Graphite exactly unchanged.
Measure contrast and hue yourself.` : `You review THE CODE. Read the diff against bbf033b. Check: every AMBER_* use decided
sensibly; no translucent yellow over cyan or blue; Graphite's palette and stylesheets byte-identical in effect; the logo's bytes
verified before shown, a missing or changed file shows nothing and breaks nothing; the glow follows glow() and Reduce motion and
costs little (measure paint time of the Apps button); every retired mark gone from code, branding, tests, README, NOTICE and the
manifest; the window icon back to the point; seed and release integrity; the modules the builder ran, run again.`) + `
Report findings MOST SEVERE FIRST, each with evidence (frame path or command and output, file:line) and a concrete fix. Say
what holds. Do not fix anything.
`

const FIX = (built, a, b) => GOAL + `
You built this pass in a git worktree. Your report:
---
${built}
---
The look review:
---
${a}
---
The code review:
---
${b}
---
Work in THAT SAME worktree (cd to the path in your report). Reproduce each proven finding, fix it, show the check passing; for one
you judge wrong, say why with evidence. Re-run modules and frames, rebuild seed and manifest, commit (a new commit), keep the mirror.
` + RULES + `
REPORT: worktree, branch, final commit; per finding fixed or not; final tests per module; final frames (absolute paths).
`

phase('Build')
const built = await agent(BUILD, { label: 'build:yellow-neon', phase: 'Build', isolation: 'worktree' })
if (!built) return { built: null }
phase('Review')
const [rA, rB] = await parallel([
  () => agent(REVIEW('look', built), { label: 'review:look', phase: 'Review' }),
  () => agent(REVIEW('code', built), { label: 'review:code', phase: 'Review' }),
])
phase('Fix')
const fixed = await agent(FIX(built, rA || '(no look review)', rB || '(no code review)'), { label: 'fix:yellow-neon', phase: 'Fix' })
return { built, rA, rB, fixed }
