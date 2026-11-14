# The test campaign: how to run it

The campaign runner tests Graphite on scripted cases in throwaway workspaces and writes a short summary you can
read once. It is the first piece of the 300-case campaign in the 35B simulation spec. It never touches your own
workspace or profile: every attempt gets a fresh folder with its own home, profile and workspace, and that folder
is deleted and rebuilt for the next attempt.

## The commands

Run these from the Graphite program folder.

```bash
python3 tools/campaign.py list                      # every case, its set, and what it needs, checked now
python3 tools/campaign.py list --set resource       # just one set: resource, anchors, all, selftest, real
python3 tools/campaign.py run --case R07            # one case
python3 tools/campaign.py run --set resource        # a batch
python3 tools/campaign.py run --set all --attempts 2 --out ~/Graphite_Campaign/runs/today
python3 tools/campaign.py summary ~/Graphite_Campaign/runs/today
```

`--out` names the run folder. Without it the run goes to a new folder in the system's temporary folder, and the
last line printed says where. Choose a folder outside the program folder.

A run counts only itself. If the `--out` folder already holds a run, that run's own files are moved aside into
`previous-1/` (then `previous-2/`, and so on) before anything starts; a folder that holds anything else is refused and
nothing in it is moved, and so is a folder that holds the program, the fixtures, your home or the root, so re-running one failing case into
today's folder gives a summary of that one case. The summary reads only the cases and attempts this run's
`MANIFEST.json` lists. `campaign.py summary <folder>/previous-1` still reads the earlier run on its own.

## What the sets are

- **resource** (R01 to R22): Graphite's own memory, model and job decisions under simulated readings. Model
  checks use a stand-in for your Qwen3.6-35B file built from its real header. It takes about 56 KiB on disk but
  looks to Graphite like the 20.5 GB file: every variant is 20,542,732,576 bytes apparent, except the
  deliberately truncated one, which stops one byte short of where its last tensor ends (20,531,799,903 bytes).
  Each case takes about a second.
- **anchors** (A01 to A35): one case per original situation, S01 to S35. Five have their steps written (A01, A16,
  A17, A27, A28). Each of those covers a **baseline slice** of its situation, not the situation's whole intent,
  and the summary labels it that way: A01, for example, traces settled power to its PDF row and checks it exactly,
  while S01 asks for a readiness report and a physical test. The other thirty list what they need and wait for
  their steps.
- **selftest** (T01 to T03): checks of the runner itself. T01 overruns its time on purpose, to show that the runner
  stops it and keeps what it had done. T02 raises after meeting one check, to show that a case that breaks is a
  Fail. T03 runs R17's steps on a software-only Vulkan device, to show that R17's checks do not pass there.

## What a case needs, and Blocked

Every case lists what it needs from the machine, and the runner checks each need when the run starts. Nothing is
marked Blocked in advance. The needs are:

- **model**: your 35B model registered in the workspace given with `--workspace`, with your file's SHA-256 (the
  registration hashed it in full), and the file still present at its size.
- **projector**: the same registration also carries the vision projector (mmproj) file.
- **ram**: at least 24 GiB of RAM available to the run. When the run is in a cgroup with a memory limit, the
  limit less its usage counts, as Graphite's own worker guard reads it. Otherwise `/proc/meminfo` counts.
- **thinkpad**: the host is your ThinkPad (Ryzen 7 7735HS).
- **desktop**: a desktop session (`DISPLAY` or `WAYLAND_DISPLAY` set).
- **network**: a simulation run never reaches the network, so this need is never met here.
- **an application**, such as LibreOffice Calc, Blender or FreeCAD: found on `PATH`.
- **your own files for a situation**: put them in `<fixtures>/S07/` for S07, and so on.
- **the After Hours 07 backup**: see below.

A case whose needs are not all met is Blocked, and its reason lists what is missing and what is present (for
example "present here: LibreOffice Calc (/usr/bin/localc)"). A case whose needs are all met but whose steps are
not written yet says "Blocked: steps not written yet; its needs are here".

## The After Hours 07 cases

A01, A16, A17 and A27 use your After Hours 07 backup. It is not shipped with Graphite. Put
`Graphite_After_Hours_07.zip` (or its unpacked `Graphite_Backup` folder) in `~/Graphite_Campaign/fixtures`, or
pass `--fixtures <folder>`, or set `GRAPHITE_CAMPAIGN_FIXTURES`. Without it those four cases say Blocked.

A16 is the spec's first complete run without the window. It changes settled current from 280 mA to 300 mA on the
working copy and recalculates. From the saved records it checks that:

- the cell says 300 mA;
- settled power is 3.60 W (18/5) at 12 V, where it was 3.36 W;
- the finding is flagged for recheck;
- the source still says 280 mA.

A fresh process then reopens the workspace and reads every one of those back, with the units. No model runs
here, so the operations the assistant would choose are scripted, and the result says so. Which steps would wait
for your approval is read from the assistant's policy table for the steps Graphite offers. No approval is pressed:
in the window it is your Run, and the run grants it for you.

## Reading the results

Each run folder holds:

- `SUMMARY.md`: what Pass means, counts by outcome, one line per case, the cases where the code and the spec
  disagree, the baseline slices, the slowest cases, the spec questions and what is Blocked.
- `MANIFEST.json`: the build (git commit, version, and whether any file differs from the commit, new files
  included), Python and PySide6 versions, the host, your model file's identity, every case's revision, its needs
  as checked, and the fault schedule.
- `results.jsonl` and `cases/<case>/attempt-<n>/`: each attempt's result, its progress log and any checkpoint.

**What Pass means.** Each case's checks describe what Graphite does today. Pass means every check matched the
current code. It does not mean the spec is met.

The outcomes:

- **Pass**: every check met.
- **Pass (current code; the spec asks otherwise)**: every check met, but a check records behaviour that a line
  of the spec plainly contradicts. The case quotes that line. R19 (a restored model marked Ready with an empty
  reply) and R22 (a work hold that cancels queued work) are counted this way, apart from Pass. When the code
  changes to what the spec asks, the same case becomes a plain Pass.
- **Partial**: some checks met.
- **Blocked**: a need is not met here, or the steps are not written yet.
- **Fail**: no check met, or the case raised an error. A case that breaks is a Fail whatever it met before.
- **Timeout**: the case ran past its time and was stopped. What it had done so far is kept.

The first attempt is the scored one; `--attempts 2` adds reruns.

A **spec question** means the case passes on what Graphite does today, but the spec leaves the answer open (R07,
R09, R15, R17, R19's smaller context, R20, A16). Those are decisions for you, not failures.

A case's revision covers its data, its own steps and every file the runner is made of, so a changed helper or
fixture shows up as a new revision. The runner reads git without taking its lock, so a run never writes inside
the program folder.

## Here versus the ThinkPad

The resource and anchor cases run anywhere, in seconds, with no model. The real-model cases need the ThinkPad:

```bash
python3 tools/campaign.py run --mode real --case M01 --model ~/Models/Qwen3.6-35B-A3B-Q4_K_M.gguf
```

Real mode checks that the file is your exact model (size, architecture, then its SHA-256, which takes a minute or
two) and that at least 24 GiB of RAM is free (counted the same way as the **ram** need). It prints exactly what it
would run and refuses clearly if anything is missing. It never downloads anything. `--workspace <folder>` uses a
model already registered there instead.

## What comes next

Real mode only checks and plans today. Next come the real 35B runs (load, first reply, Talk and the job tools,
CPU then Vulkan), then the steps for the anchors that wait for them, then the rest of the spec's 300 cases: the
five variants per situation, the pressure cases and the held-back set, written in the same case format.
