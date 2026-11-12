# HATCH readiness and bounded checks

Run `bash HATCH_CHECK.sh` from the extracted program folder. It creates a new dated report directory, prints the missing prerequisites and saves `readiness.json` and `READ_ME.txt`. Exit 2 means a blocked prerequisite, failed diagnostic or cleanup needing attention; it is not a successful acceptance result. An existing output directory is refused.

The default command reuses Doctor, the math package pins, the Office/Java probe, protected Python and inference-runtime probes. It inspects an existing selected model through read-only SQLite, or accepts `--model /path/to/reference.gguf`. Model checks hash the explicit file with a 60-second hashing budget. No model weights or packages are downloaded, no workspace is initialized and no Kernel job or model generation starts. Small version/socket/display probes run locally; Office/Java probes retain their existing timeouts. The report identifies the current execution host without assuming it is the owner ThinkPad.

Example report command:

```bash
bash HATCH_CHECK.sh --model /path/to/Qwen3.5-4B-Q4_K_M.gguf --output /path/to/new-readiness-report
```

For a different installed Python environment, set `LEDGER_PYTHON` to its Python executable. Install the versions in the existing `requirements-math.txt`, `requirements-qt.txt` and `requirements-experiments.txt` through the selected environment's normal package setup when the report identifies them as missing. Qt Core/Widgets importability is shown separately from Doctor's complete desktop package metadata. Presence does not qualify behavior.

Explicit trials are available after the selected gate passes:

```bash
bash HATCH_CHECK.sh --run model-diagnostic --model /path/to/reference.gguf --output /path/to/new-diagnostic
bash HATCH_CHECK.sh --run visible-calc --output /path/to/new-visible-check
bash HATCH_CHECK.sh --run model-family --budget-seconds 3600 --model /path/to/reference.gguf --output /path/to/new-family
```

The diagnostic and visible check default to a 600-second runner budget. A full model family requires an explicitly declared budget; 3600 above is an example, not a promise that every host will finish in that time. The existing frozen cases, expected results, grants, duplicate guard and first-failed-case stop are unchanged. Model/runtime identity remains the retained I05 Qwen3.5-4B reference SHA256 and b11669 CPU runtime. Other models retain their normal Ledger entry points.

Passing `--run` explicitly requests the chosen existing checker and its isolated synthetic fixture. The checker creates fresh scoped work orders and owner grants within that fixture. It does not act on the owner's project workspace. The visible check opens real owned Calc windows on a connectable X11 host and performs its scripted takeover checks; it is not an offscreen substitute or a general owner-device qualification.

The supervisor retains stdout, stderr, trial intent and the checker's result. Budget expiry first interrupts the runner, then uses existing PID/start-token ownership checks to stop verified descendants. Cleanup uses existing Kernel cancellation and model-stop paths only inside the newly created fixture. If exit cannot be confirmed, `CLEANUP_REQUIRED` remains visible. Budget expiry produces `BUDGET_EXHAUSTED`, preserves partial evidence and never becomes a passed family.

Readiness and diagnostic receipts never overwrite historical results or promote I05, I06 or HATCH acceptance. A completed family still needs semantic/evidence review; native ownership evidence and owner-ThinkPad I06 qualification remain separate gates.
