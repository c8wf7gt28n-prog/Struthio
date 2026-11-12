# Stage Three: local reasoning with visible sources

This stage adds ranked, source-bound context assembly to Project Desk; streaming local replies; and separate answer, read-plan, exact-edit and clarification trials in Brain. Model weights remain replaceable external GGUF files. The pinned CPU runtime and its existing startup, memory limits, loopback authentication and Stop controls are retained. No model is started by opening Ledger or assembling sources. No proposed action or edit is applied by this stage.

## Daily walkthrough

1. Open **View → Project Desk** and select an assignment with input addresses, such as `files:clock.txt`. A small UTF-8 note is a useful first source. Existing project source links are also considered. Keep your original request and interpretation in the assignment as before.
2. Open its **Ask Slate** tab. Write a question and choose **Assemble sources**. This works with no model running. Read the selected passages, why each matched, exclusions and unavailable revisions. Extra source addresses are optional. Sources that changed since the assignment was saved are excluded with a gap; explicitly refresh the assignment's inputs before using a new revision.
3. Open Brain. Add a compatible GGUF file or drag it in, inspect it and choose **Use model**. Model files and their provenance remain outside the program package. CPU is the supported route; Vulkan performance on your Radeon has not been qualified.
4. In Brain choose **Run answer, staC, exact-edit and clarification trials**. The four small trials record their own outcomes, model/runtime identity, context limit, load measurement when available, first-token and total latency, measured prompt tokens and worker memory. A previous successful load/chat probe does not qualify editing. A passed small fixture is not general factual or engineering accuracy.
5. Return to Ask Slate. Choose **Answer from sources**, **Suggest staC reads**, **Draft exact text edit**, or **Clarify the request**, then **Ask local Slate**. The chosen context and output token limits are explicit. A complete prompt is measured with the actual model tokenizer; lower-ranked passages may be excluded to fit, and those exclusions are listed with the result. The exact edit base is never silently shortened.
6. Incoming prose is visibly labelled as an unchecked draft. Only a complete stream, valid final structure and current source checks produce a result. Unknown citation aliases, unfinished output, stale bases, overlapping edit ranges and changed task context are refused. Inspect the complete context and result when detail is useful. **Stop this reply** cancels through the shared Kernel. A completed reply can be linked to the project as an alternative. **Use this interpretation** copies a suggested interpretation into the assignment editor, retaining the model job link; you explicitly save its next revision. The original request stays unchanged.

For an edit, select a `files:NAME` or `file:NAME` text input already frozen in the context. The current draft profile supports nonempty UTF-8 text up to 16000 characters and sixteen nonoverlapping character-range replacements against the exact SHA-256 base. The returned text is a preview; the original and working copy are not modified. Broader import profiles, multi-file application, typed cell changes and undo remain Stage Four work.

## Retrieval and authority

Context comes from the caller's selected assignment inputs, project links, explicit source addresses, optionally selected reference namespaces, Ledger's source-bound knowledge seed and past procedures. Existing reference readers continue to enforce intake eligibility and current original bytes. Files continue to use Stage Two's full-content revision hashes, including equal-size edits with restored modification times. Each passage retains its text hash, source revision/hash where available, locator, extraction version and authority class.

Task state, owner decisions, successful procedures, failed procedures, owner-reviewed lessons, source assertions and scoped engineering evidence keep separate classes. Owner presentation preferences are supplied separately through the existing memory policy. Neither ranking nor a model response upgrades these records into evidence or permission. Answer citations must identify supplied passages; preference/procedure citations cannot be presented as engineering source evidence. Citation validation does not prove whole-answer entailment.

Ranking uses SQLite FTS5 BM25 over a disposable in-memory corpus for this one context. There are no cross-owner ranking statistics, downloads, embeddings or extra dependencies. Literal CJK matching is a labelled fallback. The opening passage of each explicitly selected source is also considered when its words do not match the question, within the same budget: a table labelled Need/Have should remain available when the question says short parts. This is labelled source selection, not semantic matching. Selected/excluded passages and budget reasons are retained. The index is discarded and can be rebuilt from the frozen corpus; `slate.context.rebuild` checks that it reproduces the selection. Optional semantic embeddings and a learned reranker remain disabled until there are representative owner-host quality/latency measurements.

Frozen context records are private to the principal identity in the shared `.ledger/engineering.sqlite3`. The new component migration is versioned and transactional. Requests, live prose and task qualification receipts use that same database. The existing Kernel jobs execute inference; no scheduler or execution-grant system is added. A context address is `context:ID`. CLI and MCP expose the same operations as the UI.

| Operations | Scope | Purpose |
| --- | --- | --- |
| `slate.context.create` | execute | Freeze context from selected, readable sources |
| `slate.context.get`, `slate.context.check`, `slate.context.rebuild` | read | Inspect, revalidate or rebuild the disposable ranking |
| `slate.memory.search` | read | Rank caller-owned procedure outcomes and reviewed lessons |
| `slate.ask` | execute | Submit a bounded local inference job against frozen context |
| `slate.progress`, `slate.result` | read | Read caller-owned provisional prose or completed output |
| `slate.qualify` | approve | Run the selected local model's task trials |
| `slate.qualifications`, `slate.qualification.get` | read | Inspect caller-owned task receipts |

The eleven new operations bring the registry from 503 to 514. Every Stage Two scope and argument schema, including the original 485, remains unchanged. The two new job tools are `brain.reason` and `brain.task_qualify`; they use the existing private Brain job family and frozen internal request records. Direct job submissions cannot forge the request or omit owner qualification scope. Existing `brain.ask` calls now stream and refuse unfinished output. A privacy correction makes `brain.result` require the actual job owner, consistently with the existing private-job sharing policy; approve scope no longer reveals another principal's Brain reply. These are documented behavior corrections rather than schema changes.

Initial bounds are 32 selected address/project input bindings, four reference namespaces with twelve hits each, 512 candidate passages, 1200 characters per extracted chunk, a 2 MiB combined binding budget and a 3 MiB frozen record. At most sixteen passages and 32000 passage characters can be selected. Output budgets are 64–4096 tokens and 5–120 seconds of generation, with a 64 Ki-character stream bound and 2 MiB total SSE transport bound. Whole Kernel jobs additionally have 240-second reasoning and 600-second trial-suite ceilings. Server/template/tokenizer errors are reported rather than assumed to fit. A full prompt that cannot fit after lower-ranked passages are excluded is refused. The exact edit base is never clipped. Other Stage Two file snapshot/hashing limits still apply.

Task receipts bind their suite and validator source hashes. Older receipts report whether the current validator matches. Memory measurements distinguish RSS at measurement from process-lifetime peak RSS; they do not claim an isolated per-task peak. The selected GGUF must pass a small representative fixture for each task you care about. No fixture result establishes general correctness, application safety, physical qualification or model suitability for all future projects.

## Verification and limitations

```sh
python3 tools/check_release.py --self-test
python3 -m unittest discover -s tests_stage_one -v
python3 -m unittest discover -s tests_stage_two -v
python3 -m unittest discover -s tests_stage_three -v
python3 -m workbench.slate_checks --runtime
python3 -m workbench.slate_checks --ui
```

The no-model walkthrough checks context assembly, ranking, source freshness and deterministic rebuilding across fresh Python processes and complete backup/restore. Protocol tests use an explicitly labelled authenticated loopback test double; they do not measure GGUF model quality. The runtime probe launches the actual pinned executable with `--version`; it does not generate text. Actual ThinkPad/Fluxbox UI, a selected GGUF's four task trials, real latency/memory and optional GPU performance still require owner-host acceptance. `STAGE3_RESULT.json` distinguishes those scopes.

The streaming endpoint is authenticated loopback only, uses no HTTP proxy and rejects redirects. Source text has no tool authority. Streams are bounded by elapsed time, bytes, output tokens, measured context and final completion reason. The existing native worker memory cap remains in force; this does not qualify OS confinement against a hostile native runtime. Full worker/appliance boundary qualification remains a later stage.

Implementation references: [SQLite FTS5 and BM25](https://www.sqlite.org/fts5.html), and the [llama.cpp server protocol](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). The shipped runtime remains pinned to build b11669, commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`, and its original archive hashes. Documentation on the current branch is not permission to upgrade that runtime.
