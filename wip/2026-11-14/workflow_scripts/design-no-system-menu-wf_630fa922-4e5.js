export const meta = {
  name: "design-no-system-menu",
  description: "Design panel: three independent plans for dissolving Graphite's System menu into the meters, the equalizer and familiar places, then one judge scores and synthesizes",
  phases: [
    { title: "Propose", detail: "three designers, three stances, grounded in the code" },
    { title: "Judge", detail: "score the three plans and synthesize one" },
  ],
}

const BRIEF = `
You are designing a change to the window of Graphite, a local-first desktop workspace (Python 3.13 / PySide6) for one owner
on one ThinkPad (1920x1200, Debian 13, X11). Its assistant is Stacy. The repository is /home/user/Struthio. This is a
DESIGN task: READ-ONLY. Do not edit or create files in the repository, do not run git commands that change anything, do
not run anything under tools/, do not run tests, do not start the program. Reading files and git log/show/grep are fine.

THE WINDOW TODAY (version 0.6.1)
- Head (top band): eight menus in the open at the left (Work, Revise, Tools, Arrange, Commands, Rules, Properties,
  Guide); in the middle a small EQUALIZER (bars: each bar one CPU thread's load over the last second; amber at the top of
  a bar; bottom row amber while Graphite itself has work running); at the right "Programs" (a menu the owner calls
  "terrific") and "System" (the menu in question).
- Left pane: tabs Files / Machine / Settings.  Centre: the work (the Field, pages, sheets ...).
- Right pane: Stacy. A title "Stacy"; her portrait; beside it "speaks staC - <model or 'no model yet'>" and two words
  for how far she acts by herself; links "Brain room" (choose/swap/stop the local model) and "Full chat" (opens the
  full conversation with /commands as a separate overlay); a line "This: <what is open> - more"; a line
  "Now: <what runs> - N waiting for you - open - activity"; then the conversation.
- Bottom band: five names "Stacy Terminal Search Web Log" (the lit one receives what is typed), ONE typing line, an
  arrow button, then four METERS: CPU, GPU, RAM, TXT (a word over a reading, refreshed every 2 s; TXT is the model's
  context window and currently always shows a dash because the runtime does not publish it). The meters do nothing when
  clicked today.
- Above the typing line there is a console/working area with three sizes (Line, Half, Tall) that shows the chosen
  target's page (Stacy's answers, the Terminal's output, Search results, the Log). The three size words exist in code but
  are HIDDEN; today the size is only reachable through the Arrange menu. The Log page has two streams, Events and Network,
  chosen by two words inside the Log page itself.

THE SYSTEM MENU'S CONTENTS TODAY (a custom popup, workbench/desktop_header_qt.py, class SystemMenu and friends)
 1. Game (a small arcade game)
 2. Stop all jobs
 3. OWNED JOBS: the running and queued background jobs, each with niceness; "earlier/later" when something is queued
 4. WAITING: the things that wait for the owner (for example an open question of an investigation)
 5. Background CPU (how much processor background jobs may take)
 6. Open Agenda / Work trail (two links)
 7. Graphite services: Off / On / Restart
 8. Log out / Exit Graphite / Restart / Shut down

THE OWNER'S WORDS (13 November 2026, dictated on a phone; this is the whole request)
"How much of the system menu could we move into clickable: cpu/gpu/ram/text?
Could we eliminate the system menu if we got creative
Make the thinking/activity equalizer represent any and all data activity available together actively showing
SSD, RAM, GPU, CPU, kernel activity. Just a animated way to see that it's working/reasoning/computing/busing data
Brain room can probably move into system menu
Full chat in Stacy column can probably move into log ... but then how to select what log file we're looking at.
Probably don't even need the Stacy name tag taking up space
The type bar at the bottom needs a optional expand to show more data, like if I'm trying to use the terminal"

THE OWNER'S STANDING TASTE (rules already adopted; a plan that breaks one must say so and why)
- "Think Apple simplicity but still very powerful." Simple at rest: names and pictures; the machinery is one move away.
- One visible home for each action. No redoing the same thing in several places.
- NO keyboard shortcut is printed anywhere (keys still work). So everything must be findable with the pointer.
- Colour: amber = selected / has the keyboard / waits for the owner. Green = live, pointer, hover. He likes strong
  neon glow. Nothing is a white box: controls are dark plates with a quiet edge. Drawn glyph icons are liked.
- He liked the menus across the top "kind of like Apple does", the Programs menu, the four meters, the circuit-trace
  tree, and "one master typing line that I select whom I'm typing to".
- He wants Stacy autonomous but anything that cannot be undone (emptying the Trash, ending the session, anything
  leaving the computer) must stay a deliberate act of his.

WHAT TO PRODUCE
A complete, concrete plan that answers every sentence of the request:
 (a) for EACH of the 8 System-menu items: its new home, or why it stays;
 (b) whether the System menu disappears entirely, and if so what remains at the right of the head;
 (c) for each of the four meters: what a click shows (the form: a card that opens upward from the meter? a page in the
     console area? a pane?), its exact contents in order, and what a second click or a click elsewhere does;
 (d) the equalizer: which signals it shows (from Linux: /proc/stat, /proc/meminfo, /proc/vmstat, /proc/diskstats,
     /proc/net/dev, /sys/class/drm/card*/device/gpu_busy_percent ...), how many bars, how they are grouped so it still
     reads as ONE animated thing, how unbounded rates are scaled honestly, and whether clicking it does anything;
 (e) where Brain room and Full chat go, and how the owner picks WHICH log/stream he is looking at;
 (f) the right pane without its name tag: what is at its top, and how he gets back when Activity or Context is shown;
 (g) the typing line's optional expand: the control, where it sits, what its states are, what it does by itself when
     he uses the Terminal;
 (h) the three biggest risks of your plan (what the owner could dislike or lose) and what is deliberately NOT done.
Ground it: before you write, read the code that exists so you do not invent what is already there or propose what the
code cannot do: workbench/desktop_header_qt.py (SystemMenu, DesktopMonitors), workbench/typebar_qt.py,
workbench/console_qt.py (sizes, modes), workbench/log_qt.py (STREAMS), workbench/equalizer_qt.py, and in
workbench/shell2.py the classes TopBar and SlateFace. Say which existing pieces you reuse.
Keep it buildable in one sitting by one person: prefer reusing existing widgets and operations to inventing new ones.
`

const STANCES = [
  { key: "meters-are-doors", stance: `YOUR STANCE: the four meters are the doors. Push as much as honestly fits behind CPU, GPU, RAM and TXT, each meter
owning the things that are ABOUT that resource, and make the System menu vanish. Be strict that a thing goes behind a
meter only if a person would look for it there; say where the leftovers go.` },
  { key: "equalizer-is-the-computer", stance: `YOUR STANCE: the equalizer is the computer. It is the one live picture of the machine, so it is also the door to the
machine's things (session, power, services, jobs), and the meters stay light (a reading, at most a small card). Make
the System menu vanish without adding a new permanent control.` },
  { key: "familiar-places", stance: `YOUR STANCE: familiar places first. Put each thing where a person who has used a Mac or any desktop would look without
being told (power under the first menu, a game among programs, jobs with the one who does them ...), use the meters and
the equalizer only where they are the obvious place, and prefer deleting a thing to moving it when another surface
already shows it. Be sceptical of cleverness.` },
]

const PLAN = {
  type: "object",
  properties: {
    one_line: { type: "string", description: "the plan in one sentence" },
    system_menu_fate: { type: "string" },
    placements: {
      type: "array",
      items: {
        type: "object",
        properties: { item: { type: "string" }, new_home: { type: "string" }, why_there: { type: "string" } },
        required: ["item", "new_home", "why_there"],
      },
    },
    meters: {
      type: "array",
      items: {
        type: "object",
        properties: { meter: { type: "string" }, form: { type: "string" }, contents_in_order: { type: "array", items: { type: "string" } } },
        required: ["meter", "form", "contents_in_order"],
      },
    },
    equalizer: { type: "string", description: "signals, bar count and grouping, scaling, what a click does" },
    brain_room_and_full_chat: { type: "string" },
    choosing_a_log: { type: "string" },
    right_pane_top: { type: "string" },
    line_expand: { type: "string" },
    reuses: { type: "array", items: { type: "string" }, description: "existing classes/functions/operations reused, with file" },
    risks: { type: "array", items: { type: "string" } },
    not_done: { type: "array", items: { type: "string" } },
  },
  required: ["one_line", "system_menu_fate", "placements", "meters", "equalizer", "brain_room_and_full_chat", "choosing_a_log", "right_pane_top", "line_expand", "reuses", "risks"],
}

const VERDICT = {
  type: "object",
  properties: {
    scores: {
      type: "array",
      items: {
        type: "object",
        properties: {
          plan: { type: "string" },
          findable_without_keys: { type: "integer", description: "0-10" },
          one_home_per_action: { type: "integer", description: "0-10" },
          simple_at_rest: { type: "integer", description: "0-10" },
          answers_every_sentence: { type: "integer", description: "0-10" },
          buildable_in_one_sitting: { type: "integer", description: "0-10" },
          strongest_idea: { type: "string" },
          weakest_point: { type: "string" },
        },
        required: ["plan", "findable_without_keys", "one_home_per_action", "simple_at_rest", "answers_every_sentence", "buildable_in_one_sitting", "strongest_idea", "weakest_point"],
      },
    },
    winner: { type: "string" },
    synthesis: PLAN,
    grafted_from_runners_up: { type: "array", items: { type: "string" } },
    disagreements_for_the_owner: { type: "array", items: { type: "string" }, description: "choices where the plans split and the owner's taste should decide" },
  },
  required: ["scores", "winner", "synthesis", "grafted_from_runners_up", "disagreements_for_the_owner"],
}

phase("Propose")
const plans = (await parallel(STANCES.map(s => () =>
  agent(`${BRIEF}\n${s.stance}\n\nReturn the plan as structured output.`, { label: `plan:${s.key}`, phase: "Propose", schema: PLAN })
    .then(p => p ? { stance: s.key, plan: p } : null)))).filter(Boolean)
if (plans.length < STANCES.length) log(`${STANCES.length - plans.length} designer(s) returned nothing; judging ${plans.length} plan(s)`)
if (!plans.length) return { plans: [], verdict: null }

phase("Judge")
const verdict = await agent(`${BRIEF}

You are the JUDGE. Three designers, each told to take a different stance, answered the brief above. Their plans follow
as JSON. First check each plan against the code yourself where a claim matters (does the thing it reuses exist, would the
placement really be findable). Then score each plan 0-10 on the five criteria in the schema, name the winner, and write
ONE synthesized plan in the same shape as theirs: start from the winner and graft the best ideas of the others, but keep
it coherent (one home per action; do not graft two homes for one thing). Where the plans genuinely split and only the
owner's taste can decide, list that under disagreements_for_the_owner instead of hiding it.

PLANS:
${JSON.stringify(plans, null, 1)}

Return your verdict as structured output.`, { label: "judge", phase: "Judge", schema: VERDICT })

return { plans, verdict }
