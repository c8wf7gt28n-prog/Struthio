# The I05 kit

**What it measures.** I05 is the task the old loop failed: take an accepted, checked method (whether a set of
current demands fits a fixed capacity over their lifetimes), apply it to a new source, and carry the result
through Calc, protected Python and Writer, or refuse it with the method's own precondition check. The kit runs
six ways of doing that, the arms, on three cases, three times each, and writes down what happened. The
predictions were written before any code (PREDICTIONS.md, copied word for word from the design).

**The arms.**
- **A**: today's loop. The model picks every action and its arguments.
- **B1**: the planner lays out the steps and the open conditions; the model picks every step and proposes the mapping.
- **B2**: B1, but every step that is the only one possible is taken without asking. The model maps, and chooses only at a fork.
- **B2@4096**: B2 at a 4,096-token context.
- **B3**: B2, with the mapping question fenced and answered in one short line, and the answer checked against
  what the desk can read itself before anything uses it. No prompt reuse (that is 0.8.7).
- **N**: no model at all. The same planner, the rows paired by their names and units, and each precondition
  declared only when a sentence of the source says it in words from a fixed list. Anything else is a question for you.

**The cases.** A (Current_A, fits: peak 9 A against 10 A), B (Current_B, does not fit: peak 11 A), C
(Overhead_unknown: the overhead is present and unbounded, so the method does not apply). They are in
`cases.json`. The sealed case D, written by someone who did not write the rules, comes as a file of its own in
the same form and is opened only at the run. Cases A to C were known to the person who wrote the rules.

**What you need.** Graphite's folder (this kit sits in its `tools/` folder, or point at it with
`--graphite`), LibreOffice, and for every arm but N your model file. About 2 GB free on disk while it runs.

**Run it.**
1. Check it starts nothing and parses: `python tools/i05_kit/run_kit.py --dry`
2. Arm N alone, no model: `python tools/i05_kit/run_kit.py --arms N --out ~/i05_results`
3. Everything with your model:
   `python tools/i05_kit/run_kit.py --model /path/to/your-model.gguf --memory-mb 30000 --out ~/i05_results`
   Add `--backend VULKAN` for the graphics chip, and `--context 8192` to raise the context for every arm but
   B2@4096, which always runs at 4,096. Without these the specification's settings are used (context 6,144,
   4 threads, 4,480 MB), which suit a 4B model, not a 35B one.
4. The sealed case D: `python tools/i05_kit/run_kit.py --cases-file sealed_D.json --cases D --model ... --out ~/i05_results`

It is long: several hours with a model. You can stop it and start it again with the same `--out`: runs that
already have a result file are skipped. Each run sets up its own Office, qualifies the method once, runs one
arm on one case, writes `<arm>_<case>_<repeat>.json` and removes its Office. The model's file is dropped
from the disk cache before each model run.

**Reading the results.** `summary.md` has one line per arm: passed, wrong verdicts (the one that must stay at
zero), times it asked you, finishes with an open condition (must be zero), repeats blocked, the most model
turns and prompt tokens in one case, the longest turn, the most seconds in one case, and for B1 how often the
model took the planner's first option. Compare it with PREDICTIONS.md line by line. A result file holds every
step, every model turn (its tokens, seconds and what the checker said), and for N the questions it would put
to you.

**Honest limits.** None of this was run with a model before it reached you; only arm N was run once on case
A while it was built. The server keeps its last prompt in its own slot even in B3 (the program always asks it
to); each turn's `cache_n` is in the result file so you can see how much was re-used. Arm A and the setup are
the specification's code, unchanged.

**Run one arm on one case by hand.**
`python -m workbench.i05_arms --list`, then
`python -m workbench.i05_arms --arm N --case A --keep /tmp/i05_one --output /tmp/i05_one.json`
