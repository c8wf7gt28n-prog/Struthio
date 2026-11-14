export const meta = {
  name: "review-graphite-053-070",
  description: "Independent read-only review of Graphite 0.5.3 to 0.7.0 (Stacy's hand, the Godot start, the meters as doors, the equalizer): four lenses find defects, then each finding is adversarially verified",
  phases: [
    { title: "Review", detail: "four reviewers, one lens each, read-only" },
    { title: "Verify", detail: "one skeptic per lens tries to refute each finding" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const PY = S + "/work/venv/bin/python"

const COMMON = `
You are an independent reviewer. Nobody but the author has read this code yet. The repository is /home/user/Struthio
(a Python 3.13 / PySide6 desktop program called Graphite; its assistant is "Stacy"). Review ONLY what changed between
commit 3d37da7 and commit a95732b (HEAD):

  git -C /home/user/Struthio diff 3d37da7 a95732b -- <files>

HARD RULES (the checkout is the owner's working tree):
- READ-ONLY. Do not edit, create, move or delete any file under /home/user/Struthio. Do not run git commands that change
  anything (no checkout, stash, commit, reset, worktree). git diff / show / log / grep and reading files are fine.
- Do NOT run anything under tools/, do NOT run unittest or pytest, do NOT start the Qt program, do NOT import
  workbench.shell2 or anything that imports PySide6 widgets.
- You MAY run short snippets to prove a point about the pure modules, like this (cwd must be the repository):
    cd /home/user/Struthio && ${PY} -B -c "from workbench import stacy_hand as h; print(h.terminal_hers('ls -la'))"
  Pure modules: workbench.stacy_hand, workbench.stacy_start, and workbench.equalizer_qt's module-level functions and
  its Activity class (importing equalizer_qt imports PySide6 but creates no widget; that one import is allowed; give
  Activity your own temporary files as its paths, under the scratch folder).
- Another process is running the program's own checks against this same checkout right now: do not touch it.
  If you need a scratch file, put it under ${S}/work/review_scratch/ (create the folder), never in the repository.
- The code style is dense on purpose (several statements on a line, separated by semicolons; long lines; docstrings
  written in plain words). Do NOT report style, naming, formatting, missing type hints or "could be refactored".
- Report only real defects: something that does the wrong thing, raises into the window, loses or corrupts the owner's
  data, lets the assistant do without asking what it should ask about, or contradicts what its own docstring promises.
  Every finding needs a concrete scenario: exact input or state, then what goes wrong. If you cannot state one, drop it.
- Up to 8 findings, most severe first. An empty list is a fine answer if the code holds.
`

const LENSES = [
  {
    key: "hand-safety",
    files: "workbench/stacy_hand.py workbench/shell2.py workbench/session.py tests_integrated/test_stacy_hand.py",
    focus: `LENS: can the assistant do, WITHOUT ASKING the owner, something it should have asked about?

workbench/stacy_hand.py is the rule: a dial (ask / show / free), ALWAYS_ASKS (what asks on every place because it cannot
be undone), hers(), takes_back() (the line that undoes an act), made() (the grammar for "make a folder/file/page/note
called X saying Y"), and terminal_hers() (the Terminal commands she may run herself because they ONLY READ).
In workbench/shell2.py see SlateFace.stage, run_staged, made_asked, run_asked.

NOTE: the author already found and closed one round of holes in terminal_hers (ip netns exec / vrf exec / -batch, find
-fprint0, file -C, date <digits>, sensors -s, journalctl --update-catalog) and widened ALWAYS_ASKS; a test runs the
registry against the rule. Do not re-report those. Find what is STILL open after that fix.

Attack it:
1. terminal_hers(): find command strings for which it returns True although the command writes a file, changes system
   state, or executes another program. Think about each allowed command's own flags and sub-commands (ip, find, file,
   date, sensors, journalctl, dmesg, env, hostname, tail, grep, du, stat, lsblk, ps ...), about shlex quoting versus what
   a shell would do with the same text (the text is later run through the user's shell: see run_asked and
   shell2.to_console), about globbing, braces, tilde, variable expansion ($VAR without parentheses), backslash-newline,
   process substitution, here-strings, history expansion, and any shell metacharacter not in TERMINAL_MARKS. PROVE each
   bypass by calling terminal_hers on the string with the snippet runner.
2. why_asks() / ALWAYS_ASKS / LEAVES / hers(): list operation names that exist in the program (they are the keys of
   "operations" in /home/user/Struthio/docs/GRAPHITE_0.1_REGISTRY.json, each with a "scope") that send data to another
   computer, delete without a way back, or start external programs, and that hers('free', scope, name) would let through.
   Say which are actually reachable today through stage(asked=True) callers and which are only latent.
3. made(): sentences an owner might say for another purpose that it would take as a request to make something; names
   that escape Files or hit reserved places once they reach files.write / files.mkdir (see workbench/files_service.py
   resolve() and clean_name()); the overwrite check in made_asked.
4. takes_back(): can an Undo line ever put back the wrong thing, or trash something the owner made?`,
  },
  {
    key: "acts-undo-trail",
    files: "workbench/shell2.py workbench/field_page.py workbench/field_qt.py workbench/session.py workbench/stacy_hand.py",
    focus: `LENS: correctness of the acts themselves, their Undo, the trail, and "noticing".

In workbench/shell2.py read SlateFace.stage, run_staged, run_line, undo_staged, show_hand, open_hand, say_trail,
undo_entry, say_always, say_plan, run_plan, say_steps, made_asked, made_done, run_asked, and the module function
hand_menu. In workbench/field_page.py read _waits, _shown_kind, take, _after, notice, stage_set and the settle() inside
check_desk. In workbench/session.py the two new whitelist lines; in stacy_hand.py record/trail/taken_back/clean.

Look for: exceptions that can escape into the Qt event loop (attribute assumed on a card that a code path never set,
a None result, a result that is not a dict, operation/arguments used before assignment); an act run twice; Undo offered
when it should not be or usable twice; the trail recording the wrong thing or growing without bound; a stale
expected_revision making Undo put back something over a newer edit; notice() re-entering itself or running when it must
not (it is queued with QTimer.singleShot(0) from _after: what if the Field page is gone, the face is not the work face,
or the dial changed); the Field left saying something waits when nothing does (page.pending / view.go / view.would);
lambdas capturing a loop variable; session.save() failures; the menu built before the pane exists.`,
  },
  {
    key: "godot-journey",
    files: "workbench/stacy_start.py workbench/program_build.py workbench/shell2.py tests_integrated/test_stacy_start.py",
    focus: `LENS: "start a Godot project called X" (workbench/stacy_start.py; SlateFace.start_asked and started in
workbench/shell2.py; the one-line change to _tool in workbench/program_build.py).

Look for: the ASK regex taking ordinary sentences for a request, or missing plain ways of asking; names that break the
generated files (what does _quoted() do with a newline, a tab, a backslash at the end, a percent sign, braces, non-ASCII
text; can a name inject a line into project.godot, main.tscn or main.gd; build the files with the snippet runner and
show the broken output); folder_name() producing something files.mkdir refuses, something reserved ("Slate", "Egress",
".trash", ".versions": see workbench/files_service.py), an empty name, or a collision the "already there" check misses;
godot_major() and godot_tool() (timeouts, an engine that prints its version to stderr, a version like "3.6.stable" or
"4.4.1.stable.official", a wrapper script, blocking the window for up to 8 s); the Godot 3 and Godot 4 file sets
against what those engines really accept (config_version, scene format, ext_resource syntax, Label properties,
Input.get_vector availability); started(): partial failure halfway through the five steps, the Undo trashing the folder
after the owner has put their own work into it, the inspect result's shape, sha256 binding to programs.godot.open, and
adding "godot3" to the room's command list (does the room's open/play command line suit Godot 3?).`,
  },
  {
    key: "window-053-070",
    files: "workbench/equalizer_qt.py workbench/meter_cards.py workbench/desktop_header_qt.py workbench/typebar_qt.py workbench/shell2.py workbench/centre_bar.py workbench/pane_qt.py workbench/menus2.py workbench/programs_qt.py workbench/console_qt.py workbench/session.py",
    focus: `LENS: the window parts built in 0.5.3 and 0.7.0.

0.7.0 (newest, least looked at): workbench/meter_cards.py (the four meters CPU/GPU/RAM/TXT open cards; the System menu's
button is hidden in TopBar.place and its things moved); DesktopMonitors.key_at/open_card/mouseReleaseEvent in
workbench/desktop_header_qt.py; the '@leave' branch in workbench/menus2.py (Log out / Exit / Restart / Shut down at the
foot of the Work menu: are the QActions created once, do they survive rebuild(), can one fire twice); the Game row in
ProgramsList (workbench/programs_qt.py); ExpandButton in workbench/typebar_qt.py and the call back from
Console.set_size; PaneBody.arrange with tabs.at_rest in workbench/pane_qt.py and pane_title in shell2.py (the right
pane's title row hidden at rest); and the rewritten workbench/equalizer_qt.py: Activity.sample and the six readers
(kernel_counts, memory_counts, disk_counts, net_counts, gpu_counts), scaled(), the flat target/shown/peak lists against
self.sizes when the processor count changes, the ActivityCard popup, timers when hidden or closing. Check the readers
against real /proc formats: counter wrap or reset (a negative difference), a disk named like dm-0 / md0 / zram0 /
nvme0n1p1 / sr0, an interface that disappears between samples, /proc/diskstats sector size, pgpgin units, a clock that
does not advance (span 0), MemAvailable missing on old kernels, gpu_busy_percent unreadable.

0.5.3:

workbench/equalizer_qt.py (new: bars from /proc/stat in the head of the window); in workbench/shell2.py the TopBar and
PathBar changes (the address line is hidden unless typed; the equalizer takes its place), SlateFace's "This:"/"Now:"
lines, face_changed and pane_title, CAPTIONS/KEY_WORDS and the popup rows; workbench/typebar_qt.py (five names on the
strip, the Web target, address_of, open_web, typed(), submit_line, send_says, the eventFilter); workbench/centre_bar.py
(the title label is back and clickable through an eventFilter); workbench/pane_qt.py PaneTabs.place.

Look for: /proc/stat parsing mistakes (a CPU going offline or online between readings, counters wrapping, a line with
fewer fields, "cpu" aggregate line handling), division by zero, timers that keep firing when the widget is hidden or the
window is closing, peak/target/shown list lengths drifting apart (IndexError in move() or paintEvent when the bar count
changes), grouped() with thread counts that do not divide evenly; address_of() taking ordinary words for an address or
an address for words (file names like notes.txt, "3.5", "e.g.", IPv6, localhost:8080, a path), typed() switching the
target away from the Terminal or Search while the owner types a URL as an argument there, the search URL not being
percent-encoded, open_web on empty text; the address line: can it be left visible with the equalizer hidden (focus lost
to a menu, window deactivated, Escape, Enter that fails to navigate); eventFilter methods returning True for events they
should not swallow or touching self.title before it exists; the pane title button and the hidden tab buttons getting
out of step with the page actually shown.`,
  },
]

const FINDINGS = {
  type: "object",
  properties: {
    findings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          file: { type: "string", description: "repo-relative path" },
          line: { type: "integer", description: "1-indexed line at HEAD" },
          title: { type: "string", description: "the defect in one sentence" },
          failure_scenario: { type: "string", description: "exact input or state, then what goes wrong" },
          severity: { type: "string", enum: ["high", "medium", "low"] },
          evidence: { type: "string", description: "the code quoted or the snippet you ran and its output" },
          suggested_fix: { type: "string" },
        },
        required: ["file", "title", "failure_scenario", "severity", "evidence"],
      },
    },
  },
  required: ["findings"],
}

const VERDICTS = {
  type: "object",
  properties: {
    verdicts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          index: { type: "integer", description: "0-based index of the finding in the list you were given" },
          real: { type: "boolean", description: "true only if you reproduced it or traced it line by line to a wrong result" },
          why: { type: "string" },
          how_checked: { type: "string", description: "what you read or ran" },
          corrected_scenario: { type: "string", description: "if the finding is real but its scenario was imprecise, the precise one" },
        },
        required: ["index", "real", "why"],
      },
    },
  },
  required: ["verdicts"],
}

const reviewPrompt = lens => `${COMMON}
FILES FOR YOUR LENS: ${lens.files}

${lens.focus}

Return your findings as structured output.`

const verifyPrompt = (lens, findings) => `${COMMON}
You are the SKEPTIC. Another reviewer reported the findings below about ${lens.files}. Your job is to try to REFUTE each
one. For each: open the file at HEAD, read the code around the line and every caller that matters, and where the claim
is about a pure module, run it with the snippet runner. Mark real=true ONLY if you reproduced it or can trace, line by
line, an input to the wrong result. If the scenario cannot happen (a caller already guards it, the input cannot reach
that code, the claimed behaviour is what the docstring says is intended), mark real=false and say exactly why. If you
are unsure, real=false. One verdict per finding, with its index.

FINDINGS (JSON):
${JSON.stringify(findings, null, 1)}

Return your verdicts as structured output.`

phase("Review")
const results = await pipeline(
  LENSES,
  lens => agent(reviewPrompt(lens), { label: `review:${lens.key}`, phase: "Review", schema: FINDINGS }),
  (found, lens) => {
    if (!found || !found.findings || !found.findings.length) return { lens: lens.key, findings: [], verdicts: [] }
    return agent(verifyPrompt(lens, found.findings), { label: `verify:${lens.key}`, phase: "Verify", schema: VERDICTS })
      .then(v => ({ lens: lens.key, findings: found.findings, verdicts: v && v.verdicts ? v.verdicts : null }))
  },
)

const confirmed = [], rejected = [], unverified = []
for (const r of results.filter(Boolean)) {
  r.findings.forEach((f, i) => {
    if (r.verdicts === null) { unverified.push({ lens: r.lens, ...f }); return }
    const v = r.verdicts.find(x => x.index === i)
    if (!v) unverified.push({ lens: r.lens, ...f })
    else if (v.real) confirmed.push({ lens: r.lens, ...f, verdict: v })
    else rejected.push({ lens: r.lens, title: f.title, file: f.file, line: f.line, why: v.why })
  })
}
const lost = LENSES.length - results.filter(Boolean).length
if (lost) log(`${lost} lens(es) returned nothing (agent died or was skipped): their files were NOT reviewed`)
log(`confirmed ${confirmed.length}, rejected ${rejected.length}, unverified ${unverified.length}`)
return { confirmed, rejected, unverified, lenses_lost: lost }
