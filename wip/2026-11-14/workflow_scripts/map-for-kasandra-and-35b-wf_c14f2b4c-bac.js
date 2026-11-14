export const meta = {
  name: "map-for-kasandra-and-35b",
  description: "Read-only map of Graphite for the Kasandra appearance and the 35B test campaign: colours, art surfaces, fonts and names, resource and model paths, fixtures",
  phases: [{ title: "Map", detail: "five readers, one area each, read-only" }],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const K = S + "/in/kasandra_zip/Kasandra_Assets_for_Claud"
const COMMON = `
You are mapping a codebase so another engineer can change it. The repository is /home/user/Struthio: Graphite, a
Python 3.13 / PySide6 desktop workspace (version 0.7.0, HEAD 13ddfc5). Its assistant is currently called Stacy.

HARD RULES: READ-ONLY. Do not create, edit, move or delete any file under /home/user/Struthio. No git command that
changes anything. Do not run anything under tools/, do not run tests, do not start the program, do not import modules
that create Qt widgets. Reading files, grep/rg, git log/show and short python snippets that only read are fine (run them
with ${S}/work/venv/bin/python -B from /home/user/Struthio if you must import a pure module).
The code style is dense (several statements per line); docstrings are in plain words and are reliable guides.
Be concrete: give file paths with line numbers, the exact names of constants, functions and attributes. Quote short
code where it decides something. Say plainly what you could not find. Your answer is the only thing the engineer sees.
`

const AREAS = [
  { key: "colours", prompt: `${COMMON}
AREA: THE COLOUR SYSTEM, for adding a second palette ("Kasandra") chosen at startup.

The new palette (${K}/palette.json): ground #171B3C, panel #292D56, divider #5969A1, control border #8796CB, ink
#E3E3FF / secondary #C1C6E8, focus and ready #83EAFF (cyan), recheck #C3B6F4 (lavender, with a dashed edge),
approval #FA507C (raspberry; ink on it #171B3C). Today Graphite's colour rule is: amber = selected / has the keyboard /
waits for the owner; green (READY '#c3ed74', TEAL_*) = live, pointer, hover.

Map, with paths and line numbers:
1. Where every colour constant is DEFINED: workbench/boss_theme.py, workbench/theme2.py, workbench/shell2.py (CARD,
   LINE, TEXT, QUIET, ERASER, AMBER_*, READY, TEAL_*, GROUND, MONO...), workbench/desk_qt.py, workbench/pane_qt.py,
   workbench/field_qt.py, workbench/pointer.py, workbench/boss_qt.py, workbench/settings_qt.py, and any other module
   that defines hex colours (grep for '#[0-9a-fA-F]{6}' across workbench/ and count per file).
2. HOW they are consumed: imported as names at module import time (from .boss_theme import READY), read as attributes
   at call time (t.READY), baked into style sheets built once, or cached pixmaps. Which of these would NOT see a palette
   that is set before the first window is built but after the modules are imported? Is there any import of a colour
   that happens before qt_app.make_app()/WorkbenchWindow are created (e.g. at interpreter start in the launcher)?
3. The earliest point in startup where the owner's choice could be read and the palette set so that EVERY module sees
   it (trace the launcher: START_MINIMAL_DEBIAN.sh / the python entry point / qt_app.main or make_app; where the
   session file is read, workbench/session.py). Propose the least risky mechanism (e.g. boss_theme reads a tiny setting
   at import; or a function apply_palette() that rebinds module globals before the window is built) and list exactly
   which modules' globals it must reach.
4. The MEANINGS: list the call sites that use amber for "selected / keyboard focus" versus amber for "waits for the
   owner" (boss_qt.waits, shell2.approve_button, waitsForOwner property, Approve buttons, the Field's go/pending marks),
   versus green for live/hover/pointer. The Kasandra palette needs focus=cyan, live=cyan, waits-for-owner=raspberry,
   recheck=lavender dashed. Where is "recheck" drawn today (field_qt state marks, 'RECHECK' labels)?
5. Anything that will look wrong on an indigo ground: hard-coded dark greys/blacks in painters (field_qt sheets, the
   map, the equalizer, meter cards, menus' QSS), PDF 'desk light' (page_light.py DESK_LIGHT), images tinted for amber.
Return a structured map (use headings and bullet lists) of at most ~1800 words.` },
  { key: "art", prompt: `${COMMON}
AREA: WHERE ART IS SHOWN, for a resolver that picks Kasandra stills by surface ("slot") and work state.

The pack: ${K}/catalog.json (slots office_banner, field_edge, worksheet_strip, assistant_rail; states idle, viewing,
working, awaiting_approval, completed, blocked; default_by_state; quiet_fallback; focal points), ${K}/IMPLEMENTATION.md,
${K}/Pass_02_Play_the_Field/START_HERE.md. Read those three first.

Map, with paths and line numbers:
1. Every surface that shows Stacy's art or desk artwork today: workbench/boss_qt.py (ArtPanel, WorkshopStrip, PanelInk,
   appearance_menu, art modes Illustrated / ASCII / Clean, 'desk_art' session key), the Home/Office page (where is
   "Good afternoon" and its picture drawn? grep finder / home / start page modules), the Field (workbench/field_qt.py:
   FieldView.rail(), any backdrop), the worksheet strip, Stacy's pane portrait (shell2.SlateFace uses PanelInk(host,
   'face')), workbench/stacy_presence.py, workbench/graphite_brand.py. For each: the class, how it loads images (which
   files under which folder; QPixmap/QImage; caching; scaling and cropping), how it is sized, whether it is
   mouse-transparent, and how Clean/ASCII change it.
2. Where the shipped images live (find the image files Stacy's art uses; folder and naming) and how the package
   manifest (MANIFEST.json, tools/package_graphite.py) includes art files: what must be done for new image files to ship.
   Can Qt here decode .webp (check the venv's PySide6 imageformats plugins: list
   ${S}/work/venv/lib/python3.13/site-packages/PySide6/Qt/plugins/imageformats if present)? If not, say so.
3. The work STATE signals a resolver could read, for the assistant rail: something waits for the owner (waitsForOwner
   property, boss_qt.waits, Field page.pending / view.go, Talk's StagedRun cards); something is running (jobs, the
   head's equalizer busy flag, shell2 TopBar.refresh 'active'); just completed (a run_staged card ran; trail entries);
   blocked/refused/failed. Name the exact attributes/signals and where they change, and propose one function
   current_state(host) -> 'idle'|'working'|'awaiting_approval'|'completed'|'blocked' with how 'completed' should decay.
4. Field: where a skyline/edge image could sit without taking the graph's working space (FieldView.rail space rule,
   the strip at the top, the columns' headings).
Return a structured map of at most ~1800 words.` },
  { key: "fonts-names", prompt: `${COMMON}
AREA: FONTS, AND THE ASSISTANT'S DISPLAYED NAME.

The Kasandra appearance uses the typewriter face Special Elite (${K}/Pass_02_Play_the_Field/fonts/SpecialElite-Regular.ttf,
licence alongside) for display headings (Office "Good afternoon", the Field's heading, the pane's name), and keeps IBM
Plex Sans / Plex Mono for work. In that appearance the assistant is shown as "Kasandra" (the design studies in
${K}/references/ put "Kasandra" at the top of the right pane); the language stays "staC".

Map, with paths and line numbers:
1. How fonts are bundled and loaded today: shell2.load_fonts(), qt_app.make_app(), the fonts folder, licences, the
   package manifest; the "script" face for pleasantries (pleasantry(), quiet_script, Arrange ▸ Pleasantries in script);
   what would be needed to add Special Elite (file placement, licence file, registration, a font family name).
2. Every place the NAME "Stacy" is shown to the owner in the running window (not docstrings or comments): the right
   pane (shell2.SlateFace signature, pane_title 'Stacy', '‹ Stacy · Context'), the strip under the line
   (typebar_qt.SHOWN {'slate': 'Stacy'}, TIPS), her hand's words and cards ('I …'), the meter cards (meter_cards.py),
   menus ("Stacy's hand", "What she did…"), status messages, the Field's rail, accessible names. Give a count and the
   list grouped by file. Propose ONE function (e.g. assistant_name(host)) and say which sites should call it and which
   can stay (e.g. accessible descriptions, the trail).
3. Headings that would take the display face: Home's greeting, the Field's title line, the pane title, the head's
   brand if any. Where are they drawn and how is their font set (QSS vs QFont vs painter)?
Return a structured map of at most ~1500 words.` },
  { key: "resources", prompt: `${COMMON}
AREA: THE MEMORY, MODEL AND JOB PATHS that a "resource simulation" test runner must exercise by injecting hardware
readings, time and worker failures at their boundaries, without a real model.

The spec's cases (read ${S}/in/spec_docx/spec.txt lines 19-40): model preflight (qwen35moe architecture, tensor types,
chat template, identity; invalid file, changed hash, unsupported architecture: which check rejects each); shared RAM
admission at 60, 40, 39 and 30 GiB available at 4,096 context, unavailable readings, too-small manual cap (model
estimate, configured cap, job admission; foreground reserve and outstanding commitments counted once); competing work
(queued 32 GiB request, 2 GiB foreground reserve, 34 and 33 GiB available, then 40 GiB with another job reserving 8 GiB
of future growth); Radeon discovery (accessible, missing, software Vulkan; offload counts in load logs); load and first
reply (launch timeout, driver failure, empty first reply, smaller context reported; fallback CPU retry once); pressure
and Stop; foreground and recovery. Baseline note: in 0.4.4 a simulated 20.5 GB model at 4,096 context estimated 25.4 GiB
and the Auto cap topped out at 32 GiB.

Map, with paths and line numbers:
1. workbench/resource_control.py (admission, claim(), foreground reserve, forecast, observation, policy), workbench/
   local_brain.py (model add/inspect/preflight: GGUF parsing, architecture allow-list, hash binding, the memory estimate,
   the Auto cap, activation/handover/restore, fallback to CPU), workbench/brain_runtime.py (host(), probe), workbench/
   brain_worker.py, workbench/inference_hardware.py, the job queue (engineering_kernel submit/claim, agenda), Master
   Stop, operation_priority. For each decision the spec names: the function that makes it, its inputs, and the EXACT
   seam where a test can inject the reading (a function to patch, a parameter, a settings key, an environment variable).
2. What existing tests already do this (tests_integrated/test_model_settings.py, test_operations.py, test_agent_loop.py,
   test_service_lifecycle.py, others: grep for patch( of host()/memory/snapshot): reuse their fixtures where possible.
3. Compute or locate the current estimate for a 20.5 GB Q4_K_M MoE GGUF at 4,096 context and the current Auto cap with
   64 GB installed (read the formula; do not guess). If architecture 'qwen35moe' is not allowed today, say where the
   allow-list is.
4. Propose the smallest set of seams the runner needs, and a list of 12-20 concrete resource-simulation cases with
   inputs and the expected decision under the CURRENT policy (say where the current code would decide differently from
   what the spec seems to expect).
Return a structured map of at most ~2200 words.` },
  { key: "fixtures", prompt: `${COMMON}
AREA: A REPEATABLE TEST WORKSPACE and a headless way to drive Graphite's real entry points.

The spec (read ${S}/in/spec_docx/spec.txt lines 1-18 and 41-80) asks for one repeatable entry point to run a case or a
batch, a fixture workspace reset between attempts, partial results saved on timeout, a resume test that reopens its own
checkpoint, a case manifest and per-attempt results, and a readable run summary. Cases declare starting state, inputs,
allowed actions, expected outcome, time budget. The anchor case is "After Hours 07": open 07 Bench readings from the
Field; change settled current 280 mA -> 300 mA on a working copy; recalculate settled power (3.36 W -> 3.60 W at 12 V);
the dependent finding flagged for recheck; the source still 280 mA.

Map, with paths and line numbers:
1. How a workspace is created and seeded: workbench/locations.py (office(), program(), the per-user data folder),
   workbench/session.py, the After Hours 07 case (where its files and records come from: grep 'After Hours 07',
   '07_Bench', 'Bench readings', a seed/fixture module, project/stacy_seed), the engineering kernel's root and database.
   Can two workspaces exist side by side in temp folders? What must be isolated (HOME, XDG dirs, profile/session.json)?
2. How to drive the real operations WITHOUT the window: engineering_kernel dispatch with operator() principal; which
   operations implement the anchor case (field.set, office.datasheet.recheck, investigation.*, field.read/trace); which
   of the Field's computations live outside Qt (field_source, field_do, field_ripple) so a headless runner can check
   the expected state from records (saved cell, calculation result, finding state, source unchanged).
3. Existing headless/offscreen harnesses in the repo (tools/check_*_ui.py set up a window offscreen with patches;
   tests_integrated fixtures; any 'rehearsal' or 'journey' tool; tools/check_release.py sections). What can be reused
   for a campaign runner (tools/campaign.py) and what is missing.
4. Propose: the fixture layout (a folder template + a builder function), how to reset it fast, the case file format
   (JSON or Python dataclass) with the fields the spec lists, the per-attempt result format, timeouts and checkpoint
   files, and the summary. Keep it buildable in a day.
Return a structured map of at most ~2000 words.` },
]

phase("Map")
const results = await parallel(AREAS.map(a => () => agent(a.prompt, { label: `map:${a.key}`, phase: "Map" }).then(text => ({ area: a.key, text }))))
const got = results.filter(Boolean)
if (got.length < AREAS.length) log(`${AREAS.length - got.length} reader(s) returned nothing: those areas are NOT mapped`)
return got
