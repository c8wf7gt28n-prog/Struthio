# Live model trial · the smallest Qwen and the step up (HATCH AGENT-01)

November 5, 2026 · UTC. Where: the build container (4 logical CPUs, Intel Xeon at 2.30 GHz, 15.7 GiB RAM, no GPU), not the owner's ThinkPad. What ran: the real operations, real worker processes and the pinned llama.cpp CPU runtime (build b11669) that ships under runtimes/. Nothing here is owner-host qualification; the records are build/agent01_ui/model_trial/*.json.

## The owner's direction

"If you must test a model, let's build our program to work with the smallest, so that a model upgrade is multi benefit." So the trial used the smallest instruct GGUF of the Qwen2.5 family and then the next size up, with the same questions.

| Model | File | Size | SHA-256 | Licence |
| --- | --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct Q4_K_M | qwen2.5-0.5b-instruct-q4_k_m.gguf | 491,400,032 bytes | 74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db | Apache-2.0 |
| Qwen2.5-1.5B-Instruct Q4_K_M | qwen2.5-1.5b-instruct-q4_k_m.gguf | 1,117,320,736 bytes | 6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e | Apache-2.0 |

Both come from the Qwen organisation's GGUF repositories on the public hub; the hashes above are the hub's own and matched the downloads. No model file is included in the release; the Brain room registers a file you place on the computer.

## What happened, in order

1. `brain.model.add` registered each file (a real inspection job, about 2 to 3 s); `brain.model.use` with context 4,096 and four threads loaded it and qualified it for CPU chat (0.5B in 0.7 s); `brain.status` read READY with a live worker.
2. The first `brain.ask` ever run with a live worker failed on an undefined name in the reply path. Fixed in this pass (workbench/local_brain.py). Nobody could have hit it without a model.
3. Plan mode then failed with CONTEXT_BUDGET_EXCEEDED: the direct set's schemas alone were about 6,800 characters, more than a 2,048-token context leaves after the answer. Fixed: with a request in hand the plan prompt carries a core set of eight operations plus the tools chosen for the request's words (under 5,000 characters), and the trial activated with a 4,096 context.
4. Chat: both models answered in a sentence (0.5B in 1.5 to 4.6 s, 1.5B in 3 to 6 s).
5. Plan mode on "make the words quick brown bold" with the page and selection as context: the 0.5B model produced schema-valid JSON but chose knowledge.page; the 1.5B model proposed `documents.edit` with the document id, expected revision 2, offsets 4 to 15, the quoted words and a bold change. Its paragraph index was wrong (4 instead of 0); the store would refuse that selection as SELECTION_CHANGED rather than apply it to the wrong words.
6. Choice mode (added in this pass: `brain.ask` with mode `choice` and `choices` n answers with one option number, schema-constrained at temperature 0): the 0.5B model picked option 3 (read the page again) in every situation; the 1.5B model picked option 1 (sum the quantities) deterministically in the plain case, which is right, and still option 1 when the units differed, where asking the owner was right.

## What it means for the loop

The agent loop keeps explicit rules primary. A profile plans the steps and knows which options are acceptable in the current state; the model is consulted only where more than one option is acceptable, its pick is accepted only if the profile marks that option acceptable, and every consultation is recorded as a step with the job id, the pick and the decision. A better model simply picks better; the record and the safety are the same.

Recommendation for the ThinkPad: qualify the 1.5B file as the default and keep the 0.5B file as the minimum the program must remain useful with. Both run on the CPU path; the Brain room says what is selected, qualified and running.

## What stays open

The owner-host run (display, input, the owner's own model file), speed on the ThinkPad's processor, longer conversations, the model turn applied to a real page in the desktop (the proposal path exists and is covered mechanically; the live application is the next pass), and any claim about larger models.
