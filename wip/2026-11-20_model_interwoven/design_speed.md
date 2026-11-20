# Fast enough to work beside: speed and memory on the ThinkPad (0.8.7 design, the speed lens)

*Design for Graphite 0.8.7, "Kas's mind with the model, interwoven". Written 20 Nov 2026 in the build container. Nothing
here has run on the ThinkPad: every 35B number is an estimate and says so. The 4B and 2B numbers were measured here on a
shared processor, so their seconds are not budgets. Their token counts, `cache_n` and memory sizes do not depend on load,
and those are the findings. Every text sent to a model in these measurements was invented.*

---

## 0. The idea in one paragraph

The owner said: "let's have it be efficient so we don't spend 30 minutes watching a local LLM think." The I05 run here
shows where the time goes today. **About half of every model turn is spent re-reading a prompt the model has just read,
and the other half writing long answers.** Graphite starts its worker with prompt reuse switched off, and it asks for
padded JSON. 0.8.7 fixes both, inside the memory rules.

- Each kind of question gets a standing brief, read once and kept ready in its own slot of the worker. A question then
  costs only its own words.
- Each answer has a shape that is short by construction, and a price set before it is asked.
- The owner's turn always comes first. Anything else stops within one batch.
- A small chooser stands by while the 35B is busy, loading or out of room.
- A model check the owner runs once on the ThinkPad turns the estimates into numbers he sends back.

The model's role does not change: it answers 0.8.6's checked questions, and every answer is checked as before. It only
answers sooner.

---

## 1. Where the time goes today (measured from the recorded runs)

**The I05 joined-chain run with the 4B** (`live4b/i05_joined_4b_quiet.json`, quiet processor, four threads). It holds six
distinct generations, each recorded with the server's own timings:

| | Per generation | Sum of the six |
|---|---|---|
| Prompt read | 2,537 to 3,190 tokens at 65 to 74 tokens a second: **34 to 47 s** | 255 s |
| Answer written | 126 to 243 tokens at 4.5 to 5.7 tokens a second: **22 to 50 s** | 210 s |
| Tokens reused from the previous prompt (`cache_n`) | **0 in all 18 timing records** | 0 |

Each decision made two generations (choose, then arguments): 56 to 95 s a generation, **145 to 172 s a decision**.

**Why nothing is reused.** Graphite launches the worker with `--cache-ram 0 --ctx-checkpoints 0 --no-cache-idle-slots
--parallel 1` (`local_brain.py` lines 394 to 397). `local_brain.completion` sends `cache_prompt: False` (line 477).
`slate_stream.complete` reuses a prefix only when the very next request has the identical prefix key, and every
generation consumes that claim.

**Turning `cache_prompt` on is not enough** (measured, P7 below). Qwen3.5 models are hybrid: three of every four layers
are recurrent (`qwen35.full_attention_interval = 4`, read from the files). A recurrent state cannot be rolled back to
the end of a shared prefix unless the server kept a checkpoint there. With Graphite's flags and `cache_prompt: true`,
the same kind of question asked three times re-read the whole prompt every time (`cache_n` 0, 0, 0).

**The desk's own cost around a model turn** (job timestamps against the model's own elapsed time, 15 completed model jobs
in `live4b/run1`, `i05_run1` and `i05_run2`):

- 0.13 to 0.36 s from submit to start (process start, imports, claim);
- 0.22 to 0.31 s of non-model time inside the run.

That is **about 0.4 to 0.6 s a turn**. It is nothing against a 150-second decision. Against a 1-second 35B turn it is a
third of the wait.

---

## 2. What I measured and verified here

### 2.1 Runs (bundled `llama-server` b11669, CPU, four threads, `nice -n 19`, one process at a time)

Two sittings of this lens. The first ran 06:22 to 06:34 UTC as an earlier attempt of this lens, whose scripts, raw
outputs and server logs are kept in `speed_bench/`; I re-derived every number below from those raw files. The second
ran 07:18:51 to 07:19:47 UTC (`speed_bench2/`), with its predictions written first. Server time in all: about **5 min
10 s**, inside the ten-minute limit. Each sitting waited until no other model server was running.

Graphite's launch flags were used in every run, with only the cache flags changed as named.

| What | Setting | Result |
|---|---|---|
| Same kind twice, 4B | `--ctx-checkpoints 8 --checkpoint-min-step 0` | Second question read **43 of 439** tokens (`cache_n` 391). 10.5 s, then 1.6 s (contended). Quiet sitting: **6.46 s, then 1.14 s** |
| Same kind three times, 2B, **Graphite's flags exactly** | `--cache-ram 0 --ctx-checkpoints 0`, `cache_prompt: true` | **`cache_n` 0 every time**, 2.4 to 2.8 s each (P7) |
| Kind switch, one slot, 4B | `--cache-ram 512` | Back to the first kind: `cache_n` 391; back to the second: 449 |
| Four kinds in turn, 2B | `--cache-ram 1024`, checkpoints 8 or 2 | Every second-round question hit (`cache_n` 398 or 456): **0.46 to 0.67 s against 2.4 to 3.1 s**. Resident memory grew from 1,810 MiB after load to 2,172 MiB |
| The same, no RAM cache | `--cache-ram 0` | Every question missed; memory stayed at 1,859 MiB after the first question |
| **Kind slots**, 2B (P8) | `--parallel 3 --ctx-size 12288`, checkpoints 2, `id_slot` per kind | Second round: `cache_n` **391, 449, 401**, 0.55 to 0.69 s against 3.1 to 3.5 s. Memory **+135 MiB** at load over one slot, **+134 MiB** over the six questions |
| Where the reuse point falls | the questions above, and a page in its own turn | At the **start of the last user message**: `cache_n` 391 for a 394-token brief whose last 3 tokens open the user turn |
| A page kept for follow-ups, 2B | page as its own earlier turn, then the question | Follow-ups read **19 to 21 new tokens** (`cache_n` 1,526 of 1,546). With page and question joined: 66 to 69 |
| Slot files, 4B | `--slot-save-path`, `POST /slots/0?action=save|restore`, with `--no-slots` still set | Save 59 to 85 ms, restore **89 to 109 ms**. Files of **171 MB** (394 to 452 tokens plus two checkpoints of 100.5 MiB). After a restore the question read 39 to 64 tokens (`cache_n` equal to the whole brief) |
| Erase a slot | `POST /slots/0?action=erase` | 5 ms (`n_erased` 513) |
| Checkpoint size (server log) | | 4B **50.251 MiB**, 2B **19.266 MiB**, each |
| Cancel mid-read, 4B | stream closed while reading a 1,343-token prompt | Server logged the cancel; the slot was **released 2.15 s later**, after its current 256-token batch (`n_tokens` 264). The next small question answered at once |
| Prompt progress | `return_progress: true` on a stream | Progress events arrive per batch (`total`, `cache`, `processed`, `time_ms`) |
| Server write deadline, 2B (P9) | `t_max_predict_ms: 1500`, 200 tokens asked | Stopped after 24 tokens at **1.82 s**, `finish_reason` "length" |
| Load, 4B | `--load-mode none` | **3.7 to 6.7 s** from the page cache; 46 s on its first read from disk (contended) |
| Load, 4B | `--load-mode mmap` | 1.5 s, but 2.68 GB of file pages counted in its resident memory |
| Context 32,768 against 4,096, 4B | `--load-mode none` | **+898 MiB** resident (3,537 to 4,456 MB): 32 KiB a token |
| Batch sizes on CPU, 4B | 256/64 against 512/512 | 71 to 76 against 73 to 82 tokens a second: no real difference on CPU |
| Rates, 4B, cold | | reads 70 to 82 tokens a second; writes **4.2 to 7.4** |
| Rates, 2B, cold | | reads 151 to 185 tokens a second; writes 12 to 15 |

### 2.2 Predictions against results

| | Predicted before the run | Result |
|---|---|---|
| P1 | Same kind twice reads under 80 tokens (`cache_n` ≥ 85 %) | **Held**: 43 tokens, 89 % |
| P2 | Kind switch with `--cache-ram 512` restores the first kind | **Held**: `cache_n` 391 |
| P3 | Slot file 50 to 70 MiB, restore under 0.3 s, then only the question is read | **Size wrong**: 163 MiB, because two 50 MiB checkpoints ride along. Restore time and reuse held |
| P4 | Cancel frees the slot within one batch | **Held**: 264 tokens processed, 2.15 s |
| P5 | Load under 15 s from page cache; `none` gives resident memory about the file size | **Held** |
| P6 | KV grows only with the full-attention layers | **Held**: 32 KiB a token, which is exactly 8 of 32 layers |
| P7 | Graphite's flags with `cache_prompt` on reuse nothing | **Held**: `cache_n` 0, 0, 0 |
| P8 | Kind slots reuse every kind with no files and no RAM cache, under 150 + 150 MiB | **Held**: 391, 449, 401; +135 and +134 MiB |
| P9 | `t_max_predict_ms` stops writing at about 1.5 s | **Roughly held**: 1.82 s (the check is per token) |
| P10 | 4B quiet: reads 70 to 90 a second, writes 6 to 8, warm turn under 1.5 s | **Partly wrong**: reads 69.8, warm 1.14 s, but writes only **4.15** a second |

### 2.3 Sizes computed exactly from the files' own metadata

Read with a 30-line GGUF header reader (`speed_bench2/tools/gguf_keys.py`; no tensors read).

- **Checkpoint (one recurrent state):** `n_linear × (inner × state × 4 + (conv_kernel − 1) × (inner + 2 × groups × state) × 4)` bytes.
  - 4B: 24 × (4096·128·4 + 3·(4096 + 4096)·4) = **50.25 MiB**, as the server logged.
  - 2B: 18 × (2048·128·4 + 3·(2048 + 4096)·4) = **19.27 MiB**, as the server logged.
- **KV a token:** `n_attn × 2 × kv_heads × head_dim × 2` bytes, with `n_attn = block_count / full_attention_interval`.
  - 4B: 8 × 2 × 4 × 256 × 2 = 32 KiB. For 28,672 more tokens that is 896 MiB; **898 MiB was measured**.
- **The 35B (estimate, not read):** I do not have its file. If its metadata matches the published hybrid shape (40 blocks,
  interval 4, 2 KV heads of 256, inner 4096, state 128, 16 groups), then:
  - KV is **20 KiB a token**, so 80 MiB at 4,096 tokens;
  - one state or checkpoint is **62.8 MiB**.

  The model check reads the real metadata and the server's own log line, and corrects this.

### 2.4 Runtime features, verified in the bundled b11669

**From `llama-server --help` (`rt/server_help.txt`):**
- `--cache-ram` (default 8,192 MiB: Graphite must always set it, and does);
- `--ctx-checkpoints` (default 32);
- `--checkpoint-min-step` (default **8,192 tokens**, which means no checkpoints at all for short prompts unless set low;
  the runs above used 0);
- `--slot-save-path`, `--parallel`, `--kv-unified`, `--cache-idle-slots`;
- `--cache-reuse` (KV shifting);
- `--json-schema` and `--grammar`;
- `--embeddings`, `--pooling`, `--rerank`;
- `--reasoning`, `--reasoning-budget`;
- `-ctk` and `-ctv`;
- `--load-mode none|mmap|mlock|dio`;
- `--moe-cache-mib`, `--n-cpu-moe`;
- the speculative draft options, `--metrics`, `--timeout`.

**Request fields in `libllama-server-impl.so` (`strings`):** `id_slot`, `cache_prompt`, `return_progress`,
`t_max_predict_ms`, `n_probs`, `json_schema`, `grammar`, `thinking_budget_tokens`. There is no prompt-time limit field.

**Used in the runs above:** `id_slot`, `cache_prompt`, `return_progress`, `t_max_predict_ms`, slot save, restore and
erase, `--ctx-checkpoints` with `--checkpoint-min-step 0`, `--cache-ram` and `--parallel`.

**Not verified here** (there is no GPU in this container):
- anything on Vulkan: batch sizes, whether checkpoints and slot states live in GPU or host memory, cancel latency on the GPU;
- whether a long GPU read delays the X server's drawing;
- the default size of the GPU's memory window on Debian 13;
- the 35B's own architecture;
- whether reuse changes any answer at temperature 0. Changed batch boundaries change rounding, so a near tie could flip.
  This is designed as a test (SP1).

`--cache-reuse` is not used. It shifts attention KV, and a hybrid model's recurrent layers cannot follow a shift. That is
reasoned, not tested.

---

## 3. Five rules of speed

1. **Read once.** What does not change between questions of a kind is read once, kept in that kind's slot and never sent
   again. The changing part goes last, because the reuse point is the start of the last user message.
2. **Write little.** Every answer has a grammar that makes it short, a token cap and a write deadline the server
   enforces. Facts never wait for words: the receipt shows at once, and the model's wording follows.
3. **Know the price first.** Every question kind has a budget in new tokens, answer tokens and seconds, priced from this
   machine's measured speeds. A question over its budget is narrowed, sent to the chooser, or shown as buttons. It is
   never sent hoping it will be quick.
4. **The owner first.** Background model work stops within one batch when the owner needs the model, and only runs when
   the desk is quiet, on mains power, with room in memory.
5. **Memory is counted, not hoped.** Every slot, checkpoint and cache is added to the one memory rule from the file's
   own metadata before launch, and compared with what is measured after.

---

## 4. The capabilities

### SP1 · Standing briefs: each kind of question read once, kept in its own slot

**What the owner sees.** He types "what did we spend on food in October". "I took it as …" appears in about 2 s on the
35B (estimated) instead of 4 to 8 s. The model turn record shows: "read 61 new, 438 kept · 1.2 s". With the 4B on this
container, the same kind of question took **1.14 s instead of 6.46 s** (measured, quiet sitting).

**Worked example (measured, 4B).** The GOAL brief has a 394-token fixed part: rules, three invented examples, and the
goal templates the desk knows. Then come the owner's words and the numbered goals.
- First question: 439 tokens read, 6.46 s.
- Second question of the same kind: 43 tokens read (`cache_n` 391), 1.14 s, answer "1".
- The checker sees the same answer shape in both cases.

**How it is built.**
- **`brain_briefs.py`, the registry of standing briefs.** Each entry has a kind, the fixed text, its version and its
  SHA-256, its slot, its grammar, and its budget row (section 5). Four slots:

  | Slot | Kinds | Brief |
  |---|---|---|
  | 0 | the page: READ, ASK-READ, COLUMNS, and anything unregistered | the reading rules |
  | 1 | choose: 0.8.6's GOAL, PICK and NEXT | one brief; the kind is named in the question |
  | 2 | understand: free words into a checked intent | |
  | 3 | words: her FRAME turn | the character card, at most 160 tokens |

- **No owner data in a brief.** A brief holds rules, invented examples and the desk's own names of acts and templates.
  The character card is the only owner-written text in any brief; it stays in RAM and is never written to a slot file.
  A test fails the build if a brief contains a workspace name.
- **One layout, enforced by `brain_briefs.messages()`:**
  1. system: the brief;
  2. optional: a user turn with stable material, such as a page or the desk's state, followed by a fixed assistant
     line ("Page received.");
  3. user: the question, always last.

  Nothing that changes per question may come before the last message.
- **The worker's launch line changes** (section 6):
  - `--parallel 4 --ctx-size 16384`, so each slot gets 4,096 tokens (measured: `n_ctx_slot` = context ÷ slots);
  - `--ctx-checkpoints 3 --checkpoint-min-step 0`;
  - `--cache-ram` stays 0.

  Every request carries `cache_prompt: true` and its kind's `id_slot`.
- **`local_brain.completion` and `slate_stream.complete` take the kind,** not a free cache key.
  - The single `prepared_context` claim becomes a per-slot record: brief digest, worker identity, prefix tokens, last
    `cache_n`.
  - The worker readiness check compares the reported `n_ctx` with the per-slot context, not the total.
- **The reuse watchdog.** After every turn, `cache_n` is compared with the brief's own token count.
  - A miss (more than 4 short) is counted, never treated as an error.
  - Two misses in a row for a slot re-prime it: a read of the brief alone, or a slot-file restore (SP6).
  - This guards against the fragility the voice lens saw: with `--ctx-checkpoints 4`, a repair turn evicted the
    checkpoint at the brief's end, and two later cases re-read everything.

**What the model is asked.** Exactly what 0.8.6 and the other 0.8.7 lenses ask, in the same shapes, under the same
checker. Only the layout and the slot change. Each answer is checked twice:
- **its content,** by the kind's own checker, unchanged;
- **the reuse,** by the watchdog: the server's `cache_n` must reach the brief's length. This affects speed only, never
  what is shown.

**Budget.**
- A choose turn after the first: 43 to 59 new tokens.
  - 4B here: **1.14 s quiet, 1.6 to 3.3 s contended** (measured).
  - 2B here: **0.48 to 0.69 s** (measured).
  - 35B on the ThinkPad: 0.8 to 1.6 s for about 120 new tokens (estimated).
- Cost: one brief read per slot per worker start. 400 to 700 tokens each, about 1.5 to 4.5 s on the 35B (estimated),
  in the background (SP6).
- Memory: +135 MiB at load and +134 MiB in use for three slots on the 2B (measured). About 1.2 GiB for four slots on
  the 35B (estimated, SP2).

**With no model loaded.** Nothing is read and nothing is held. The brief is still the buttons (0.8.6).

**Effort.** M. The layout rule, the registry, the per-slot claim, the flags and the watchdog. It touches `local_brain`,
`slate_stream` and the callers that build messages.

**How it is proven.**
- *Exact, no model:* every registered kind's messages put all varying text in the last user message, tested by
  building each kind twice with different questions and comparing the token prefixes from `/tokenize`.
- *Exact, no model:* no brief contains a workspace name or a record title.
- *Measured, 4B here, the reuse bench, with predictions written in advance:* 200 questions in mixed order over the four
  kinds.
  - At least 95 % of non-first questions reach `cache_n` ≥ brief − 4.
  - Median new tokens read under 80 for choose and understand.
  - Answers byte-identical to the same 200 asked cold for at least 98 %. Every difference is listed with the model's
    top-two odds (`n_probs`); the checker passes or refuses each answer either way.
- *I05, a factor added to the arms:* reuse on against reuse off, all else equal. Prediction, written now: with reuse
  alone and today's loop (arm A+R), prompt tokens read per decision fall by at least 40 %. The arm still fails a case
  on the 180-second wall, because writing (126 to 243 tokens at about 5 a second) is the other half (SP3).

**Risk.**
- Checkpoint placement at the start of the last user message is an observed behaviour of b11669, not a documented
  contract. A runtime update could move it. The watchdog catches that, and the reuse bench is part of the runtime exam
  that the trust lens's tr-5 gives every new runtime.
- Four slots hold four questions' states in the worker's memory. They are counted (SP2) and erased on Forget (SP2).

---

### SP2 · Room for the briefs: the one memory rule, exact for hybrid models

**What the owner sees.** In the Brain room, under her model:

> Kept ready: choosing, understanding, her words, the page.
> Memory: 27.2 GB counted · 26.9 GB in use after load.

(The figures are invented to show the form.)

When a source is forgotten, she also clears what the model holds: "Cleared from her model's memory: 4 slots."

**Worked example (35B, estimated from the assumed shape).**

| | Today's estimate | 0.8.7's estimate, one slot | 0.8.7's estimate, four kind slots |
|---|---|---|---|
| KV at 4,096 tokens a slot | 160 MiB (today's formula counts all 40 layers) | 80 MiB (10 attention layers) | 320 MiB |
| Recurrent state | (not counted) | 63 MiB | 251 MiB |
| Checkpoints (3 a slot) | (not counted) | 188 MiB | 754 MiB |
| RAM prompt cache | 0 | 0 | 0 |
| **Model budget** | **26,013 MiB** | about 26,180 MiB | **about 27,180 MiB** |
| Auto admits when free | 32,157 MiB | about 32,320 MiB | **about 33,320 MiB** |

On a 64 GB machine with the desk and a few Apps open, that still fits. The owner's Auto setting, the reserve, the
headroom and the one rule do not change. Only the estimate becomes true to the model.

**How it is built.**
- **`local_brain.configuration` computes the hybrid terms from the GGUF metadata** that registration already reads:
  `full_attention_interval`, `ssm.inner_size`, `ssm.state_size`, `ssm.group_count`, `ssm.conv_kernel`.
  - KV is computed over the attention layers only, for slots × context per slot.
  - The state, checkpoint and RAM-cache terms are added.
  - Models without `full_attention_interval` keep today's formula, which is exactly the dense KV formula.
- **The weights term (×1.3 + 384 MiB) is unchanged and stays conservative.**
- **Everything goes through `budget_room`.** The launch flags are frozen with the budget, so admission, configuration
  and launch still compare the same number. A handover still waits for memory (`await_room`).
- **After every load, the measured figures are put beside the computed budget:**
  - resident memory;
  - for Vulkan, `mem_info_gtt_used` from the amdgpu sysfs files, which `inference_hardware.py` already reads for the
    totals;
  - the server's logged checkpoint size.

  A term off by more than 10 % is recorded on the model record. It never silently changes the rule.
- **Context per slot stays at 4,096.**
  - On a hybrid model, a bigger context costs little memory: 32 KiB a token on the 4B (measured), about 20 KiB on the
    35B (estimated).
  - Reading time is what costs. A 6,000-token prompt takes 20 to 40 s on the 35B by the specification's physics.
  - So the rule is a reading rule, not a memory rule: **no foreground question sends more than 1,600 new tokens.**
    Larger material is split by the desk or read in the background.
- **Forget and Delete (0.8.8) erase the slots** (`POST /slots/{n}?action=erase`, 5 ms measured). The erase goes through
  `local_brain.request`'s endpoint list, with the slot number checked.

**What the model is asked.** Nothing. This is accounting.

**Budget.** Computing the terms takes microseconds. The readback after load takes under 50 ms.

**With no model loaded.** The Brain room shows what a selected model would need at the chosen settings, and why
("needs 33.3 GB free; 41.0 GB is free"), as it does today.

**Effort.** M. The formula, tests against the two measured models, the readback, and the erase endpoint.

**How it is proven.**
- *Exact:* the state formula on the 4B's and 2B's metadata gives 50.25 and 19.27 MiB (logged: 50.251 and 19.266).
- *Exact:* the KV formula on the 4B gives 32 KiB a token. The measured growth from 4,096 to 32,768 was 898 MiB against
  896 computed.
- *Exact:* a dense model's estimate is byte-identical to today's.
- *Exact:* the 35B at one slot is admitted at the same free memory as today, within 200 MiB.
- *Measured on the ThinkPad by the model check (SP8):* the computed budget against resident memory plus GTT used,
  after load and after twenty questions.

**Risk.**
- Whether checkpoints and slot states sit in GPU or host memory on Vulkan is not known here. The budget counts them
  either way, but the guard's resident-memory check may not see them. The model check reports both sides.
- If the 35B's metadata differs from the assumed shape, only the estimate changes. The rule does not.

---

### SP3 · Every question has a price: short answers by construction, and deadlines the server keeps

**What the owner sees.** While she asks the model, her card says how long it should take: "Choosing … about 2 s". A thin
ring fills as the model reads, driven by the server's own progress events. If the answer is late, the buttons are
already there; nothing freezes. Her answer never waits for her wording: the receipt line shows at once, and her own
sentence replaces it when it has passed the voice gate.

**Worked example.**
- **Today's choice mode** asks for `{"choice": n}` under a JSON schema with up to 24 tokens. The I05 loop's decisions
  wrote 126 to 243 tokens each.
- **In 0.8.7,** the choose kind's grammar is `ANSWER := NUM (" " NUM){0,2} | "0"`, with a cap of 6 tokens and
  `t_max_predict_ms` 1,500. The model writes "2 1". The checker reads two numbers in range.
- **On the 4B,** at 4.2 to 7.4 tokens a second (measured), writing 3 tokens instead of 24 saves 3 to 5 s a turn.
  Writing 6 instead of 200 saves 26 to 46 s.
- **On the 35B,** at 15 to 25 a second (estimated), the same change saves 1 to 13 s.

**How it is built.**
- **Each brief registry row carries:**
  - its grammar, a compact line format. Other lenses design the shapes; this lens holds them to the budget;
  - `max_tokens`;
  - the write deadline, sent as `t_max_predict_ms`;
  - the hard new-token cap;
  - the deadline.
- **Before a question is sent,** the desk counts its tokens exactly, as `completion` already does with `/tokenize`, and
  prices it with SP4's rates. A question over its kind's cap or deadline is not sent. Instead it is:
  - narrowed (fewer options, 0.8.6's rules); or
  - routed to the chooser (SP7) if it is a choose turn; or
  - shown as buttons.
- **Every model turn streams with `return_progress: true`.**
  - The progress events drive the ring. They also wake the reader once a batch, so a cancel or a deadline is noticed
    within one batch, not at the first token. Today `slate_stream.events` blocks in `readline` through the whole
    prompt read.
  - A `prompt_progress` chunk is accepted by `slate_stream.events` as a non-content event.
- **A turn that ends on "length" is refused whole.** The kind's grammar makes truncation detectable, and a partial
  answer is never used. Then come the buttons, or her no-model words.
- **Her words (FRAME) are never on the critical path.** The answer card renders from the receipt (0.8.6's no-model
  voice) first. The model's sentence replaces it within its deadline only after it has passed the voice gate.

**What the model is asked.** Each kind's question as designed by the other lenses, under a grammar sized to the budget
table (section 5). It is checked by the kind's own checker. In addition:
- `finish_reason` must be "stop";
- the token count must be within the cap;
- the time must be within the deadline.

Any of these failing means "not used", with the reason shown in the turn record.

**Budget.** The table in section 5 is this capability.

**With no model loaded.** The price card says "buttons" and the buttons are shown. That is 0.8.6's behaviour.

**Effort.** M. Grammars for four kinds; the price check; streaming with progress for `completion`'s callers; the ring;
the receipt-first card.

**How it is proven.**
- *Exact:* each grammar admits only answers within its token cap (enumerated or fuzzed against the 4B's tokenizer
  through `/tokenize`).
- *Exact:* a question one token over its cap is never sent.
- *Exact, with a fixture stream:* a cancel arriving between progress events closes the connection before the next
  event.
- *Measured, 4B here:* `t_max_predict_ms` stops writing within 0.4 s of the limit. Measured once on the 2B: 1.82 s for
  1.5 s.
- *I05:* the B arms record answer tokens per turn. Prediction: under 16 on every choose turn, against 126 to 243 today.

**Risk.**
- A grammar can make a model worse at the task, by forcing a number where it would have said "none". Every choose
  grammar keeps "0" for none of these. The understand lens's bench compares a line format against compact JSON.

---

### SP4 · Her clock and the quick lane: speeds measured on this machine, and no wasted half-second

**What the owner sees.** Her estimates come from his own machine and grow more exact with use: "about 2 s". When a turn
takes three times its estimate, she says why, from the meters: "Slow today: memory is tight (another App is using
14 GB)." Or: "on battery". Or: "the processor is busy". In the Brain room, a small table shows the model's rates on this
machine: read, write, a kept question, and the desk's own share.

**Worked example.**
- After twenty turns on the 35B, her clock might hold: reads 310 a second, kept questions 160 a second, writes 19 a
  second, desk share 0.15 s. These are invented numbers that the model check replaces.
- A choose turn with 140 new tokens and 3 answer tokens is then priced at 0.15 + 140/160 + 3/19 = 1.2 s. Its deadline
  is the larger of 3 s and 2 × 1.2 + 1 = 3.4 s.

**How it is built.**
- **`brain_clock.py`** keeps rolling medians per model file, backend and slot kind. It reads the timings every turn
  already returns (`prompt_n`, `cache_n`, `prompt_ms`, `predicted_n`, `predicted_ms`) and the job's timestamps.
  - Read rate is kept by size band: under 64, 64 to 512, and over 512 new tokens. Small reads are slower per token:
    30 to 43 a second against 70 cold on the 4B (measured).
  - The desk's share is job time minus the model's elapsed time.
- **Deadline:** `max(3 s, 2 × predicted + 1 s)`, capped by the kind's hard deadline in section 5. Before any turns,
  the table's defaults apply; after the model check (SP8), its measured rates apply.
- **"Slow today"** reads the existing meters at the moment of the slow turn: `resource_control.observation`,
  `host_observations.gpu`, and the power-supply files.
- **The quick lane.** The recorded runs show about 0.4 to 0.6 s of desk time around each model job: process start,
  imports, the claim's 0.4-second poll, result writing. For choose and understand turns, which are short and
  foreground, a resident turn runner takes the job inside the existing job process family.
  - It is still a Kernel job, with its record, cancel, hold and admission.
  - It is built **only if** the clock shows the desk's share above 0.3 s on the ThinkPad. Measure first.

**What the model is asked.** Nothing new. Timings are the server's own figures; nothing is inferred from the model's
text.

**Budget.**
- Under 1 ms a turn to update the clock.
- The quick lane's target: desk share at most 0.15 s a turn, against 0.35 to 0.67 s measured from today's job records.

**With no model loaded.** The clock keeps its last rates and shows when they were measured. Prices say "no model:
buttons".

**Effort.** S for the clock and "slow today". M for the quick lane, if the ThinkPad numbers call for it.

**How it is proven.**
- *Exact:* given recorded timings, the medians and deadlines are computed exactly (table-driven tests).
- *Measured, 4B here:* the price for a choose turn is within ±40 % of the measured time in 80 % of turns on a quiet
  machine. Prediction written now. This is the first check that her estimates are not decoration.
- *ThinkPad:* the same check from the kit's turns.

**Risk.** A shared or hot machine makes rates noisy. Medians over a size band, and the stated cause, keep the estimate
honest rather than precise.

---

### SP5 · The owner first: background work stops within one batch, and Stop gives buttons at once

**What the owner sees.**
- She is reading a manual overnight, one page at a time (the reading lens's night work). He comes back, opens the
  Field and asks "trace what feeds the power card". His question is answered in about 2 s.
- The night reading resumes from the same page when the desk has been quiet for two minutes.
- If he presses Stop on her card while the model is reading, the buttons are there at once.
- Touching the mouse still stops her hand (0.8.5).

**Worked example (measured mechanism, estimated time on the 35B).**
- A background READ of a 1,000-token page is in its second batch when a foreground choose question is queued.
- The desk closes the background stream. The server logs the cancel and frees the slot after its current batch. On the
  4B here that took 2.15 s for a 256-token batch. On the 35B it should be 0.6 to 1.7 s (estimated).
- The choose turn runs on slot 1, warm, in about 1 s.
- The READ job goes back to the queue at the same page, not as failed.

**How it is built.**
- **`resource_control.decision`** already gives foreground the next turn, and one inference lane. It gains preemption:
  - when a foreground model request is queued and a background or normal turn is running, the running turn's job gets
    `yield_requested`;
  - its reader, woken each batch by progress events (SP3), closes the stream, records "yielded at token n", and goes
    back to Queued with its step intact;
  - this is the same rule as "a hold holds".
- **A background model turn may start only when all of these hold:**
  - the foreground lease (`resource_control.touch`, 8 s) has been clear for 120 s;
  - the machine is on mains power (`/sys/class/power_supply/*/online`; the owner can allow battery);
  - the memory forecast allows it.
- **Background turns are small:** at most one page (1,300 new tokens). So the worst foreground wait is one batch plus a
  warm turn.
- **The batch size bounds cancel time.** 256 tokens on CPU, kept as today. On Vulkan the model check chooses it from
  measured read rates and cancel latency (SP8).
- **Stop on her card cancels the job.** `slate_stream` closes the stream on its next event; with progress events, that
  is within a batch. Today the stream can sit silent through a whole prompt read.
- **No two model turns at once on one worker.** Continuous batching stays available in the server but is never used:
  - on a bandwidth-bound machine, two sequences share the same memory bus;
  - on a mixture of experts, a batch of two wakes more experts, so both are slower and the estimate is wrong.

**What the model is asked.** Nothing new.

**Budget.**
- Foreground wait behind background work: at most one batch, plus the warm turn.
  - 4B here: about 2 s, plus 1.1 to 1.6 s (measured mechanism).
  - 35B: 0.6 to 1.7 s, plus 1 to 2 s (estimated).
- Re-reading after a yield: the page's unread part. The kept part survives only if a checkpoint landed. SP1's layout
  puts one at the page's start.

**With no model loaded.** Nothing to preempt. Stop and buttons work as in 0.8.6.

**Effort.** M. Preemption in admission, a yield state on model jobs, and progress-driven cancel. The AC and quiet rules
are S.

**How it is proven.**
- *Exact, with a fixture worker:*
  - a queued foreground request causes the background job to yield before its next progress event;
  - the background job resumes at the same step;
  - no step is run twice. The I05 harness already counts repeats.
- *Measured, 4B here:* preemption latency, from foreground submit to background slot free, is at most one batch plus
  0.5 s. Prediction: under 3 s on a quiet machine.
- *ThinkPad:* the kit measures cancel latency on Vulkan (SP8).

**Risk.**
- A page yielded repeatedly could starve. A background job that has yielded three times runs its next turn as normal
  priority, still behind the owner.
- On Vulkan a single batch may take longer than on CPU. The kit measures this before the batch size is chosen.

---

### SP6 · Warm before asked: briefs ready after load, the open page read ahead, and the model loaded after the desk

**What the owner sees.**
- The desk opens as fast as today. The 6-second start-to-Field budget is untouched.
- About ten seconds later, her model loads in the background. The meter shows it; her card says "Her model is getting
  ready" until it has answered "ready".
- When he opens page 3 of *Lease 2025* in the Library and the model is idle on mains power, the desk reads the page
  into the page slot without asking anything. A question about that page then costs only the question.
- Nothing about the read-ahead is shown unless he asks: the turn record lists it as "read ahead, nothing asked".

**Worked example.**
- *Measured, 2B:* a 39-line page in its own turn took 9.5 s cold. The two follow-up questions read 19 and 21 new
  tokens, 0.36 s each.
- *Estimated, 35B:* the page read ahead takes 2.5 to 6.7 s while he reads it himself. His question "when is the rent
  due?" then takes about 1.5 to 3 s instead of 5 to 10.

**How it is built.**
- **After Ready** (the existing "Reply with the word ready" probe, which also builds the GPU's shaders), a background
  job primes each slot.
  - It reads exactly the brief, with no answer (`n_predict` 0).
  - Measured: a slot primed this way then reuses the whole brief (`cache_n` 394 of 394 after restore).
- **Slot files for briefs only.**
  - After priming, each brief's state is saved to `state/brain/briefs/<digest>.bin`: private directory, mode 0700,
    file names chosen by Graphite.
  - The digest key covers: model file SHA-256, runtime build, template SHA-256, brief SHA-256, context per slot, and
    the checkpoint flags.
  - At the next start, a matching file is restored instead of re-reading: 89 to 109 ms each on the 4B (measured).
  - Files hold no owner data, because briefs hold none (SP1). The words slot is never saved, because it holds the
    character card.
  - Pages are never saved to disk; they live only in the worker's memory.
  - A file holds one state, the brief's KV and the checkpoints priming leaves (two, measured): 163 MiB on the 4B
    (measured), about 200 MiB on the 35B (estimated: 63 + 9 + 2 × 63 MiB), so about 800 MiB of disk for four briefs.
    Measured by the kit.
  - Only the four current briefs are kept. Older files are deleted when a brief changes.
- **Read-ahead of the open page.**
  - Runs when: a page is open in the Library or a document view for 3 s; the model is idle; on mains power; no
    foreground lease.
  - It reads the page as its own user turn in the page slot, with `n_predict` 0.
  - It is cancelled by any foreground model need (SP5), and dropped when the page closes or the slot is needed.
  - It respects the reading lens's doorway: only pages already checked by the doorway, with flagged lines withheld.
- **Load after the desk.** An option in the Brain room: "Load her model when the desk opens".
  - Off until the model check has passed; then on if memory allows.
  - The load starts 10 s after the Field is shown, as background priority, through the same admission.
  - If a chooser is registered (SP7), it loads first, in 2 to 4 s. The 35B follows.

**What the model is asked.** Nothing, except the existing "ready" probe. Priming and read-ahead ask the model to read,
never to answer. The check: `cache_n` on the next real question equals the primed length (SP1's watchdog).

**Budget.**
- Priming four briefs: about 2,000 tokens.
  - 35B: 5 to 13 s of background reading (estimated), or under 0.5 s from files.
  - 4B here: about 28 s, or 0.4 s from files (measured rates).
- Read-ahead: one page, 2.5 to 6.7 s on the 35B (estimated). Cancelled within a batch.

**With no model loaded.** Nothing is read ahead. The load-at-start option is hidden until a model is registered.

**Effort.** M. The priming job, slot files with their key and cleanup, the endpoint, and the read-ahead trigger.

**How it is proven.**
- *Exact:* a slot file whose key differs in any field is never restored.
- *Exact:* no file is written for the words slot or the page slot.
- *Exact:* Forget erases the page slot. A test with a fixture worker records the erase call.
- *Measured, 4B here:* after a restart with valid files, the first choose question reads under 80 new tokens.
- *ThinkPad:* load-to-first-warm-answer time with and without files, from the kit.

**Risk.**
- Read-ahead spends energy on pages he never asks about. It is mains-only, quiet-only and one page at a time, and the
  turn record shows every read.
- A runtime update could change the slot file format. The key includes the runtime build, so an old file is never
  restored.

---

### SP7 · The chooser: a small model beside the 35B, for the choose kind only

**What the owner sees.** In the morning the desk opens and a small model is ready in a few seconds, while the 35B loads.
He types "total the car costs". 0.8.6's dictionary finds two goals that fit equally, and the choose question goes to the
small model. The card says "Picked by the small model (Qwen3.5 2B) · 0.6 s", with the other goal one press away. Later
the 35B is reading a manual in the background; his choose questions go to the small model without stopping that
reading. When memory gets tight because GIMP and Godot are open, the small model is the first to step aside, and her
card says so.

**Worked example (measured here, 2B on CPU).**
- First choose question: 439 tokens in 2.64 s (184 a second). Answer "1 2".
- Warm questions: 0.48 and 0.63 s, answers "1" and "1 2".
- Resident memory: 1.8 to 2.1 GB at a 4,096 context.
- On the ThinkPad's processor (8 cores, DDR5) it should be at least as fast (estimated). It runs on the processor, so
  the GPU and its memory window are left to the 35B.

**How it is built.**
- **A second worker key, `brain.chooser`,** next to `brain.worker`.
  - `resource_control._view` already loops over model worker keys; it adds this one, so the chooser's budget is a
    commitment like any other.
  - Admission uses the same `budget_room`. This is the specification's "several models at once" for the simplest
    schedule: both resident, budgets summed, nothing timed.
- **Launch:** CPU only (`-ngl 0 --device none`), 4 threads, `--parallel 1`, its own choose brief, slot priming as in
  SP6. The chooser's state is its own; briefs are per model.
- **Routing**, in `brain_route.py`. A choose turn goes:
  - to the 35B if it is ready and idle;
  - to the chooser if the 35B is loading, not admitted, or busy with background work (no preemption needed);
  - to buttons if neither.

  Understand, page and words turns never go to the chooser.
- **Order of stepping aside under pressure:**
  - when `memory_forecast` predicts headroom below the chooser's budget, the chooser is stopped first, and restarted
    when room returns;
  - the worker guard's hard stop is unchanged.
- **Trust:** the chooser must pass the choose exam (trust lens, tr-5) before routing sends it anything. Every pick it
  makes is checked by the same checker. At night, recorded choose briefs are replayed to both models and agreement is
  counted. Under 90 % agreement, the chooser is shown as "unreliable here" and routing stops using it until the
  owner says otherwise.
- **Needs from the owner:** a small model file (Qwen3.5 2B or 4B Q4_K_M). Graphite never downloads models.

**What the model is asked.** The choose question only: numbered goals, places or steps, plus "0". The answer is 1 to 3
numbers under the choose grammar, checked by 0.8.6's checker: in range, licensed by his words, a joint plan, no hidden
authority. The card always names which model picked.

**Budget.**
- Choose turn, warm: 2B here **0.48 to 0.69 s** (measured); ThinkPad CPU about 0.3 to 1 s (estimated).
- Cold: 2B here 2.6 s (measured).
- Load: 2.4 s from page cache here (measured).
- Memory: about 2.1 GB budget for the 2B at 4,096 tokens (today's formula), about 4.4 GB for the 4B (its I05 budget was 4,480 MiB at 6,144).

**With no model loaded.** No chooser and no 35B: buttons. A chooser alone: choose turns are live and the rest is
buttons, as with any single model.

**Effort.** L. A second worker key through status, stop, handover and the memory view; routing; exam gating; the
agreement replay; the Brain room rows.

**How it is proven.**
- *Exact, with fixture workers:*
  - with both resident, admission sums both budgets;
  - a launch that would break the rule is refused with the numbers;
  - under a falling forecast, the chooser stops first;
  - the 35B's handover never waits on the chooser.
- *Measured, here:* with the 4B as the "big" model and the 2B as the chooser, both resident, a choose turn routed to
  the 2B while the 4B reads in the background. Prediction: the 2B's turn takes at most 1.5 × its alone time; the 4B's
  page read is slowed by at most 30 %.
- *ThinkPad:* the kit measures the 35B's write rate while the chooser writes on the processor, which is the memory-bus
  contention.

**Risk.**
- Both models share one memory bus, and a writing 2B reads about 1.2 GB of weights a token. Turns are short (under 1 s) and only
  happen when the 35B is busy in the background, so contention costs the background, not the owner.
- A smaller model picks worse. The exam, the agreement count and the name on every pick keep that visible.

---

### SP8 · The model check: one run on the ThinkPad, one file sent back, settings proposed from evidence

**What the owner does and sees.** From the installed Graphite folder he runs the model check once. It is the model
chapter of the specification's ThinkPad check, and it also runs on its own. He can run it from the text console before
Graphite starts, which gives the cleanest numbers, or from the Brain room. It asks him to leave the machine for about
ten minutes on mains power; touching the desk pauses it.

It ends with a card in plain words:

> Her model on this machine (Qwen3.6 35B, on the Radeon):
> loads in 24 s (first time 51 s);
> reads 310 tokens a second; writes 19 a second;
> a question she has seen before: 0.9 s.
> Memory window: 31.0 GB; she needs 27.4: fine.
> One change suggested: reading in batches of 512 is 2.4 times faster than 64 here, and Stop still answers within 1.1 s.
> Send back: model-check-2026-11-21.txt

All numbers in this card are invented to show its form.

Back in Graphite, the Brain room offers "Use the measured settings?", with each change and its evidence. A yes is a
change at his hand, with Undo.

**How it is built.**
- **`workbench/model_check.py`, a script entry `MODEL_CHECK.sh`, and a button in the Brain room.**
- **It uses Graphite's own launch path:** `brain_runtime.prepare`, the device probe, `local_brain.configuration` and
  the memory rule. So it measures what the desk will really run, not a hand-built command line. Each stage is a fixed
  list of invented prompts with known answers.
- **Stages** (time estimated for the 35B; total about 9 to 12 min):

| # | Stage | What it records | Time |
|---|---|---|---|
| 0 | The machine | Vulkan devices (the existing probe); amdgpu `mem_info_vram_total/used` and `mem_info_gtt_total/used`; the TTM page limit and amdgpu `gttsize` if readable; MemTotal, MemAvailable; CPU; power source; kernel and Mesa versions; the model file's size and registered hash; its GGUF metadata (architecture, layers, interval, state shape) | 10 s |
| 1 | First load | Load seconds, first since boot, with no cache drop because that needs root and the check never asks for it; offloaded layers; reported context; resident memory and GTT used, before and after | 20 to 60 s |
| 2 | Ready | The ready probe's time, which includes the first build of the GPU's shaders | 1 to 10 s |
| 3 | Reading | Cold reads of 300, 1,200 and 3,000 tokens, twice each, cache off, one answer token | 40 s |
| 4 | Writing | 16, 64 and 256 tokens at temperature 0 | 25 s |
| 5 | Batch size on Vulkan | Two relaunches from the page cache, at batch/ubatch 256/256 and 512/512 against today's 256/64: the 1,200-token read and cancel latency for each | 60 to 90 s |
| 6 | Kept briefs | Four kind slots, two rounds: `cache_n`, seconds; the server's checkpoint size; resident memory and GTT growth; slot file save and restore time and size | 20 s |
| 7 | Stop | A 3,000-token read closed after 1 s; seconds from close to the next small answer | 10 s |
| 8 | Think, then the schema | `thinking_budget_tokens` 48 with a strict schema: is the schema applied after the reasoning? This is the specification's condition for "think more" | 10 s |
| 9 | Heat | Writing for 60 s without a break: the rate in the first and last 10 s | 60 s |
| 10 | The chooser, if a small model is registered | Its load, cold and warm choose turns on the processor, and the 35B's write rate while the chooser writes | 40 s |
| 11 | Handover | The 35B stopped, its memory waited for (`await_room`), then started again; seconds and memory at each step | 40 to 90 s |
| 12 | The desk while she reads | If run from the Brain room: the Field's frame times while panning, during a 3,000-token read, counting stalls over 50 ms (the floor's budget). From the console, this stage says "not run" | 30 s |
| 13 | Optional, long | The 35B on the processor only, for the fallback: read and write rates | 3 to 5 min |

- **What it writes:** `for-sending/model-check-<date>.json` (schema `graphite.model-check/1`) and a `.txt` card.
  - Contents: the machine's figures, every stage's numbers, the predictions below with "held" or "did not hold", the
    proposed settings, and the stated limits.
  - Never: no paths (only the model's file name and size), no host name, no user name, no workspace content. Every
    prompt was invented.
  - Size under 50 KB.
- **What it never does:** change a kernel setting, install anything, download anything, or touch the workspace.
  - If the memory window is too small for the 35B, the card says which setting would need raising and by how much.
    Raising it is the owner's decision, outside Graphite.
  - If the model is not admitted by the memory rule, the check says so with the numbers and runs the machine stages
    only.
- **Settings from evidence** (in Graphite, after a check):
  - batch and ubatch for Vulkan;
  - checkpoints per slot (enough for the watchdog to see under 5 % misses in stage 6);
  - whether to load at desk start;
  - the clock's starting rates (SP4);
  - whether the quick lane is needed (SP4).

  Each change is proposed with its stage's number. The owner approves; Undo restores.

**Predictions, written now, for the 35B on the ThinkPad.** They are printed in the kit, and the result says which held.

| Ref | Prediction |
|---|---|
| K1 | The memory window (GTT total) is at least 28 GiB on stock Debian 13, so the 35B fits without a kernel change. If it is under 27 GiB, the card says the window must be raised |
| K2 | First load 20 to 60 s; from the page cache 8 to 25 s |
| K3 | Reading at 1,200 tokens: 150 to 400 a second (the specification's 4 to 8 s) |
| K4 | Writing at 64 tokens: 15 to 25 a second; after 60 s of writing, still at least 12 |
| K5 | On Vulkan, ubatch 512 reads at least twice as fast as ubatch 64. If true, the launch line changes for Vulkan only |
| K6 | A kept choose question with about 120 new tokens answers in under 1.6 s. Every second-round question reaches `cache_n` ≥ brief − 4 |
| K7 | A checkpoint is 55 to 75 MiB, against 62.8 computed from the assumed shape |
| K8 | Stop: the next answer within 2 s of the close at the chosen batch size |
| K9 | With a 2B chooser writing on the processor, the 35B's write rate drops 10 to 35 % |
| K10 | The handover's memory returns within the 8-second launch wait |
| K11 | During a 3,000-token read, the Field shows no stall over 50 ms. This may fail: the X server's 2D drawing can use the GPU. If it fails, the batch size for foreground use is lowered and the stall is reported |

**What the model is asked.**
- Only invented prompts with known answers: the ready probe; "count the lines" reads with one-token answers; a fixed
  choose brief with gold picks; a list-writing prompt for the write rate.
- Answers are checked exactly against gold. A wrong gold answer is reported as a quality flag for that model, never
  hidden. Quality itself is the trust lens's exam, not this check.

**Budget.** About 9 to 12 minutes on the 35B (estimated), plus 3 to 5 for the optional processor stage. Here with the 4B,
the same kit runs in about 6 minutes, on CPU, with stages 5, 12 and 13 marked "not run" (estimated from the rates
above).

**With no model loaded.** Stages 0 and 12 still run: the GPU, its memory window, the memory, the desk's frame times. The
card says "No model file given: the model chapter was skipped". That alone answers K1, the specification's first gate
question.

**Effort.** L. A staged runner over the existing launch path, the report schema, the card, the settings proposal with
Undo, a dry run here with the 4B, and the kit document.

**How it is proven.**
- *Exact, here:* the kit runs end to end with the 4B and the 2B, producing a valid report.
  - A privacy test scans the report for the workspace path, the user name and the host name, and fails if any is
    present.
  - Every stage that cannot run says "not run" with the reason.
- *Exact:* the settings proposal changes nothing until approved, and Undo restores the exact previous settings record.
- *On the ThinkPad:* the owner runs it once. The returned file is the evidence for gate 1 of 0.9.0, and K1 to K11 are
  reported held or not, whichever way they fall.

**Risk.**
- The owner has never loaded a model there. The first load is the riskiest moment: it might stop on memory, or Vulkan
  might fail. The check runs stage 0 first and refuses with the numbers before loading anything that the rule would
  refuse. A Vulkan failure falls back to CPU, as `start_server` already does, and the card says so.

---

## 5. Budgets each question kind must meet

New tokens are what the model must actually read for this question; the brief is kept (SP1). Answer tokens are hard
caps by grammar. The 35B columns are **estimates** from the specification's physics, until the model check measures
them. The rates assumed are:
- cold read: 150 to 400 tokens a second;
- kept-question read: 100 to 250 a second;
- write: 15 to 25 a second;
- desk share: 0.15 s with the quick lane, 0.5 s without.

The 4B columns are **measured** where marked, otherwise estimated from measured rates: reads 70 a second cold and about
43 a second for small kept reads, writes 4.2 to 7.4.

| Kind (slot) | Brief, kept (tokens) | New tokens: typical / hard cap | Answer tokens: cap | 35B on the ThinkPad, warm (est.) | 35B, first of its kind (est.) | 4B here | Deadline before the check | Deadline after the check |
|---|---|---|---|---|---|---|---|---|
| **Choose** (1): GOAL, PICK, NEXT, her question when choices tie | ≤ 450 | 120 / 300 | 6 | **0.8–1.6 s** typical; at most 3.6 s | +1.1–3.0 s | **1.14 s quiet, 1.6–3.3 s contended** at 43 new (measured); about 4 s at 120 (est.) | 6 s | 2 × price + 1 s, 3 to 6 s |
| Choose, by the chooser (2B, CPU) | ≤ 450 | 120 / 300 | 6 | 0.3–1.0 s on the ThinkPad CPU (est.) | +1–2 s | **0.48–0.69 s** at 43–59 new (measured, 2B) | 4 s | same rule |
| **Understand** (2): free words to a checked intent | ≤ 700 | 120 / 250 | 48 | **1.9–3.4 s** typical; at most 5.9 s | +1.8–4.7 s | about 9 s (est.) | 10 s | 2 × price + 1 s, 4 to 10 s |
| **Read a page** (0): READ marks | ≤ 500 | page as its own turn: 700 / 1,000 (1,300 at night) | 140 | 6.7–13.5 s, with the ring | +1.3–3.3 s | about 35 s (est.; the reading lens measured 122 s contended) | 20 s on request; none at night (one page per turn) | 2 × price + 1 s |
| **Ask the read page** (0): ASK-READ follow-up | page kept | 25 / 40 | 60 | **1.6–2.6 s** typical; at most 4.5 s | (the page first) | 0.36 s to read 19–21 new on the 2B (measured); about 7 s with 30 written on the 4B (est.) | 6 s | same rule |
| **Columns** (0) | ≤ 500 | 300 / 400 | 30 | 3–6 s | +1.3–3.3 s | about 12 s (est.) | 10 s | same rule |
| **Her words** (3): FRAME, never on the critical path | ≤ 450, character card included | 150 / 250 | 100 | 3.2–5.7 s after the receipt is already shown | +1.1–3.0 s | about 16 s (est.) | 10 s, then the no-model sentence stays | same rule |
| **Think more** (escalation, notes then strict) | the kind's | +0 | +64 thinking | +2.6–4.3 s | | about +12 s (est.); the judgment lens measured 19.3 s at 48 thinking tokens, contended | the kind's + 5 s | same rule |
| **Self-consistency**: three orders of a choose turn | kept | 3 × 120 | 3 × 6 | 2.4–4.8 s | | about 12 s (est.) | 12 s | same rule |

**Whole-request budgets on the 35B (targets for the model check and the scenes):**
- **A request in words:**
  - "I took it as …" in at most 4 s typical: one understand turn, plus at most one choose turn when the dictionary ties.
  - The receipt answer follows at once; it is exact work, not the model's.
  - Her own sentence follows in at most 6 s more, or the no-model sentence stays.
- **Her hand running a line of desk acts:** model time only at true ties, at most 2 s a tie typical. The line's price is
  shown before she starts, for example "about 8 s".
- **One I05 decision:** at most 15 s and 2,400 tokens read, counting re-reads (the judgment lens's bound).
- **No foreground question reads more than 1,600 new tokens.** No foreground turn has a deadline over 20 s. Anything
  bigger is the desk's job to split, or the night's.

These are tighter than the specification's GOAL row (1,200 tokens in, 32 out, 60 s) and fit inside it. The model check
replaces every estimate with a measured rate, and the deadlines then follow SP4's rule.

---

## 6. The launch line, before and after

| | Today (`local_brain._start_server`) | 0.8.7 |
|---|---|---|
| Slots | `--parallel 1` | `--parallel 4`; per-request `id_slot` by kind |
| Context | `--ctx-size` = the selected context | `--ctx-size` = 4 × 4,096; readiness compares the per-slot context |
| Checkpoints | `--ctx-checkpoints 0` | `--ctx-checkpoints 3 --checkpoint-min-step 0` |
| RAM prompt cache | `--cache-ram 0` | `--cache-ram 0` (kind slots make it unnecessary; may be raised later, counted in the budget) |
| Idle slots | `--no-cache-idle-slots` | unchanged |
| Slot files | none | `--slot-save-path <state>/brain/briefs`, briefs only (SP6) |
| Batch | `--batch-size 256 --ubatch-size 64` | CPU unchanged; Vulkan from the model check (K5) |
| Request | `cache_prompt: false` | `cache_prompt: true`, `return_progress: true`, `t_max_predict_ms` per kind, the kind's grammar |
| Endpoints `local_brain.request` allows | `/health`, `/props`, `/tokenize`, `/apply-template`, `/v1/chat/completions` | plus `/slots/{0..3}` with `action` in save, restore, erase, and a file name Graphite chose |
| Unchanged | `--no-slots`, `--no-context-shift`, `--no-warmup`, `--no-webui`, the key file, loopback, `--load-mode none` | same |

`--load-mode none` stays. With mmap, the file's pages were counted in resident memory (2.68 GB extra on the 4B), which
would confuse the guard. The model check's stage 1 confirms load times on the ThinkPad.

---

## 7. The memory sum, exact for hybrid models (SP2 in one place)

```
budget = weights × 1.3 + 384 MiB                                       (unchanged)
       + KV:          n_attn × 2 × kv_heads × head_dim × 2 B × slots × ctx_per_slot
                      n_attn = block_count / full_attention_interval  (hybrid), else block_count
       + state:       slots × n_linear × [inner × state × 4 + (kernel − 1) × (inner + 2 × groups × state) × 4] B
       + checkpoints: slots × ctx_checkpoints × (one state)
       + RAM cache:   cache_ram MiB
```

- Checked against the server here: one state is 50.251 MiB (4B) and 19.266 MiB (2B); KV is 32 KiB a token on the 4B.
- For a dense model the KV line is today's formula exactly, and there are no state lines.
- Auto, the reserve, the 4 GiB headroom, `budget_room`, `await_room` and the worker guard are unchanged.

---

## 8. Order, effort, and the best three

**Order:**
1. **SP2** first: the sums, with nothing switched on.
2. **SP1** and **SP3** together: the layout, slots and grammars; nothing is faster without both.
3. **SP5**: needs SP3's progress events.
4. **SP4**: needs turns to measure.
5. **SP6**.
6. **SP8**: built here and dry-run with the 4B before it is sent.
7. **SP7**: needs a second file from the owner, and the kit's contention numbers.

| | Capability | Effort |
|---|---|---|
| SP1 | Standing briefs in kind slots, with the reuse watchdog | M |
| SP2 | The one memory rule, exact for hybrid models; Forget clears slots | M |
| SP3 | Every question has a price: grammars, caps, write deadlines, progress, receipt first | M |
| SP4 | Her clock, "slow today", and the quick lane if needed | S (M with the lane) |
| SP5 | The owner first: preemption within a batch; Stop gives buttons | M |
| SP6 | Warm before asked: priming, brief files, read-ahead, load after the desk | M |
| SP7 | The chooser beside the 35B | L |
| SP8 | The model check, and settings from evidence | L |

**The best three:**
1. **SP1, standing briefs.** The largest gain for the least risk. Measured here: 6.5 s to 1.1 s on the 4B, 2.6 s to
   0.5 s on the 2B, with every answer still checked. It fixes the half of the I05 time spent re-reading.
2. **SP3, every question has a price.** It fixes the other half: writing 126 to 243 tokens at 5 a second. It also makes
   every wait bounded and visible, so "watching a local LLM think" becomes a 2-second ring or a set of buttons.
3. **SP8, the model check.** Nothing about the 35B is known until it runs. One file from the owner turns every estimate
   in this design into a fact, and settles the first question of 0.9.0: does the 35B fit the GPU's memory window.

---

## 9. Honest limits

- **Nothing here ran on the ThinkPad or on any GPU.** Every 35B time is an estimate from the specification's physics.
  The 35B's memory shape is computed from an architecture assumed, not read: the formula is exact on the 4B and 2B
  files, but I do not have the 35B's file.
- **This container's processor is shared.** The 4B's seconds varied by up to two times between sittings (10.5 s against
  6.46 s for the same cold question). Token counts, `cache_n` and memory sizes are the findings; seconds are not
  budgets.
- **Where reuse lands is observed behaviour of b11669:** the start of the last user message, plus checkpoints near the
  prompt's end. It is not a documented contract, and the voice lens saw a checkpoint evicted with
  `--ctx-checkpoints 4`. Hence the watchdog and the brief files, and why the reuse bench belongs in every runtime's
  exam.
- **Not measured:** whether reuse changes any answer at temperature 0. It could, at near ties, because batch boundaries
  change rounding. Designed as SP1's test, with a prediction.
- **Unknown on Vulkan:** where checkpoints and slot states live (GPU or host memory); whether a long GPU read delays
  drawing on the desk; the right batch size for the 680M. The model check measures all three (K5, K7, K11).
- **The desk's share of a turn** (0.35 to 0.67 s) comes from job timestamps in recorded runs, not an isolated
  benchmark. The quick lane is built only if the ThinkPad shows it matters.
- **Mixed hands.** The first sitting of this lens's measurements was run by an earlier attempt of the same lens
  (06:22 to 06:34 UTC). I checked its scripts and raw logs and re-derived every number. One of its predictions (P3, the
  file size) was wrong, and is reported as wrong.
- **P10 was partly wrong:** the 4B wrote at 4.15 tokens a second on the quiet sitting, not 6 to 8. On this processor,
  writing is the slow side. That is why SP3 matters even before the 35B.
- **The chooser needs a small model file** the owner does not have yet. Without it, SP7 waits and the buttons cover.
- **Not proposed:**
  - **Speculative decoding** with the 2B drafting for the 35B: verifying drafts wakes more experts on a mixture of
    experts, and the answers are 6 to 100 tokens. Revisit only if the words turn is too slow on the ThinkPad.
  - **Sending the owner's words while he types:** it saves under 0.3 s on the 35B and would send unfinished words to
    the model.
  - **An embedding model** (the reading lens's meaning index) would be a third resident process, counted by the same
    rule. Its timing is the reading lens's.

---

## 10. Files

- This design: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087d/design_speed.md`
- First sitting (scripts, raw results, server logs, predictions):
  `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087d/speed_bench/`
- Second sitting (predictions P7 to P10, script, results, logs):
  `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087d/speed_bench2/`
- The GGUF header reader: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087d/speed_bench2/tools/gguf_keys.py`
- The runtime's help text: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b087d/rt/server_help.txt`
- Code read (read-only): `workbench/local_brain.py` (launch flags 390 to 398; `completion` 473 to 486; `run_model_job`),
  `workbench/slate_stream.py` (`complete`, `events`), `workbench/slate_reasoning.py` (`prepared_context`),
  `workbench/resource_control.py` (`budget_room`, `decision`, `claim`, `await_room`), `workbench/brain_runtime.py`,
  `workbench/brain_worker.py`, `workbench/agent_loop.py` (`ask_model`, `MODEL_PATIENCE`).
