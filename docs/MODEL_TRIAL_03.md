# A small model answers in Talk (0.3.1 rehearsal)

November 12, 2026 · UTC · a cloud build container (4 processor threads, 15 GB), the bundled CPU runtime llama.cpp b11669,
not the owner's ThinkPad. The owner's words: "Let's rehearse and perfect with a small model."

Two files from the same family as the owner's chosen first model, fetched from the publisher's page and registered through
Graphite's own operations (`brain.model.add`, then `brain.model.use` with the processor backend, 4 threads, a 4,096-token
context): `Qwen3.5-2B-Q4_K_M.gguf` (1.28 GB, sha256 aaf42c8b…699223) and `Qwen3.5-4B-Q4_K_M.gguf` (2.74 GB, sha256
00fe7986…ef11a4), both Apache 2.0, thinking off. Inspecting a file took about 5 seconds and starting it 6 to 15. The window
was the real one, offscreen, on the restored After Hours 07 case, with the Field in front and a sheet selected. No file
ships with Graphite.

## What the first try showed

Asked "what went into this?" about a calculation, the 2B model took 27 seconds in plan mode, restated the staC line and
proposed two actions nobody asked for. Asked "why do we believe this?" about a finding, it took 37 seconds and proposed
FreeCAD and Delivery. A small model asked to plan from the whole desk does not answer a question.

## What changed

Stacy reads first and the model only says it. For a question about a sheet she now runs the sheet's staC line herself (exact,
no model), shows the line and the rows, and then gives the model one small job: say the answer in one to three sentences
from those rows and from what the Field already knows of the sheet (its kind, state, what feeds it, what it feeds). The
request goes in chat mode with the mark `What the records say (read with staC):`, which tells `local_brain.run_reply` to use
a short instruction and to leave out the seed excerpts. Empty fields are not shown to the model or to the owner. A question
typed in the Field is taken as about the selected sheet only when it points at it (this, it, that, here); anything else goes
the ordinary way.

## The same questions afterwards

| Sheet | Question | Qwen3.5-2B | s | Qwen3.5-4B | s |
| --- | --- | --- | --- | --- | --- |
| calculation | what went into this? | The calculation uses the voltage from cell B2 and the settled current from cell B3. | 5 | The calculation uses the settled current from cell B3 and the rail voltage from cell B2. These values were recorded during both observations and after settling, respectively. | 13 |
| finding | why do we believe this? | The finding is supported by two sources, both of which are marked as current. | 7 | The records show that the finding is supported by source "07_Bench_Readings.pdf" and source "07_Rail_Limits_Rev_B.pdf". These sources are marked as current… No further details explaining the reasoning are present in the provided rows. | 25 |
| open question | what is still open here? | The question "What stretched the startup pulse?" is still open with a state of UNKNOWN and a review of CURRENT. | 5 | The question … is still open. Its evidence state is UNKNOWN and its review status is CURRENT. | 10 |
| sheet | where did this table come from, and is it still good? | The sheet "07 Bench readings" comes from the current PDF source "07_Bench_Readings.pdf" and is still good. It was reviewed from page 1 and is currently in version 1. | 7 | The table comes from the source file "07_Bench_Readings.pdf" and is currently in good standing… | 18 |
| source | what is this file? | The file … has a state of current. It feeds the finding "Settled draw is 3.36 W. Rev B allows 6 W." and the finding "Startup ran 30 ms past the Rev B limit." | 10 | The file … is currently in the ACCEPTED state. It contains 77439 bytes and feeds findings regarding settled draw and startup times. | 16 |
| page | what is this page? | The document "07 Case conclusion · HOLD" is a record with revision 1 and contains 125 words. | 5 | This page is a document titled "07 Case conclusion · HOLD" with revision 1 and 125 words. | 10 |

Asked about something the rows do not hold while it still pointed at the sheet, the 2B model said the records do not contain
it and said what they do show. "What is the capital of France?", which points at nothing, went the ordinary way and was
answered in 14 to 15 seconds.

## What this means for the owner

- A 2B model is enough to put a read into words, in 5 to 10 seconds on four slow processor threads. The 4B says more and
  names the sources, at about twice the time.
- The answer is only as good as the rows. Where a read returns opaque addresses (a finding's sources), the words are thin;
  what the Field knows of the wires fills that in. Better reads make every model better.
- Everything the model says in this path is marked as the model's words, under rows the owner can run again.
- Not measured: the ThinkPad, the Radeon, a 27B file, a long conversation, and anything that proposes an action.
