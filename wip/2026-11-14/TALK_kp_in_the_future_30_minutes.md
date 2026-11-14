# kp in the future

*A thirty-minute chat, 14 November 2026, at Graphite 0.8.3.*

---

## 0:00 · Two myths in one logo

Your logo carries two stories, and I think together they say where kp is going.

**The first is Cassandra.** Apollo gave her the gift of prophecy and then cursed her: she would always see truly and
never be believed. Troy fell while she told them it would. Her curse wasn't being wrong; it was being right with
nothing anyone could check.

**Kasandra is the answer to that curse.** She's right *with receipts*: here is the source, here is its revision, here is
the line I ran, here is what it rests on, and here is what I still can't tell. Every piece we've built points that way:
- Trace lights the wires back to the evidence.
- The goals engine says holds, does not hold or cannot tell, and never guesses past the evidence.
- The receipt carries the line, the inputs and the coverage.

If I had to put the protocol in "kasandra protocol" in one sentence: *a way for an assistant to be believed because it
can be checked.*

**The second story is the ostrich, Struthio.** People think ostriches bury their heads in the sand. They don't. It's a
myth; they lower their heads to turn their eggs. The real ostrich is the fastest animal on two legs, built for the
ground, and it doesn't fly. That's kp too:
- **It doesn't fly to the cloud.** It runs on your own ground, your ThinkPad, fast.
- **It never buries its head.** It looks straight at the inconvenient reading, the stale source, the limit that doesn't
  hold, and says so.

A prophet who can be checked, and a bird that stays on the ground and runs. I'd keep both stories close as the project
grows.

## 3:00 · The next few months: her hand, made real

The near future is the plan we already have, and it's worth picturing it as a day rather than as slices.

You sit down in the evening. The hologram is quiet, violet, barely moving. Her column says one thing waits for you:
she noticed that Rev C of the rail limits arrived in your Ingress folder that afternoon. The Field shows two findings
marked "recheck", because they rested on Rev B.

You type: *"what changed, and does the startup pulse still fail?"* The model answers one small question: which of
three goals did you mean? Then deduction does the rest:
1. It opens the Field and selects the new limits.
2. It puts Rev B beside Rev C: Pulse duration went from 80 ms to 100 ms.
3. It works the goal again. With your recorded ±5 ms, the 110 ms reading is now over by 5 to 15 ms. Still does not
   hold, and still robustly.
4. It names the one measurement that would matter if the limit moved again.

Her card shows each goal light up as its evidence lands, and she stops the moment you reach for the mouse.

**None of that needs a smarter model than your 35B.** It needs the planner, the receipts and the maths core, and those
are slices S1 through S4. That's 0.9.0. After that comes the boring, vital part: the ThinkPad qualified, the tests made
honest, your data carried forward. The future I'm about to describe stands on that floor, and I'd rather lay the floor
properly than paint the ceiling first.

## 6:00 · kp at the bench

Your work is engineering: rails, pulses, limits, datasheets. The most natural place for kp to grow is out of the
screen and onto the bench.

**Instruments as sources.** Bench meters, supplies and scopes have spoken a standard command language (SCPI) over USB
and the network for decades. To kp, an instrument is just another source with a revision: a reading arrives with its
time, its range and the instrument's stated accuracy. That last part matters most:
- **Today the tolerance has to be typed in by you.** An instrument already knows its own: so many percent of reading
  plus so many counts.
- **Then the interval maths becomes live.** Every reading arrives as a range. "Cannot tell" turns into "take this reading
  next" without you thinking about it.

**Value of information as a lab partner.** "Which measurement next?" is the question a good senior engineer answers by
instinct. kp would answer it exactly: of the readings you could take, this one is most likely to settle the open
question, and this one can't change anything, so skip it. On a bench where each measurement costs a probe placement
and a minute of your attention, that's real time saved.

**A notebook that writes itself.** Every reading, every change of setup, every conclusion lands as a record with its
provenance. Months later you ask *"why did we decide 80 ms was fine on the March board?"* She doesn't remember, because
models don't remember. She *reads*: here is the reading, here is Rev B, here is the finding, here is who agreed and
when. It's the lab notebook every engineer means to keep and nobody does.

## 9:30 · kp sees

We've talked about swapping in a vision model "where needed". Here's where I think that's going.

**Pictures become sources, not just attachments.** A scope screenshot, a datasheet curve, a photo of the board with a
blackened component. Today those are dead images. With a vision model as a role (qualified on a test card first, as we
discussed), each becomes a proposed reading:
- "The rise time on this capture looks like about 2 µs."
- "This curve gives about 450 mA at 25 °C."

And because it's kp, the reading is marked as **read from a picture**, with an uncertainty to match. It waits as a
proposal until you or an instrument confirms it. The vision model is never a source of truth, only of candidates.

**Datasheets read properly.** Every engineer has copied a number from the wrong column of a datasheet table. A vision
model plus the exact engine can read the table, check units and conditions, and say *"this limit is at 85 °C; your board
runs at 40 °C; the 25 °C column applies, and it's tighter."* That's precisely Cassandra's job: the unwelcome truth,
with the page and the cell cited.

## 12:00 · An orchestra of models, all at home

Right now we think of "the model". I think kp's future is several models, each in its role, all local, conducted by the
planner:

| Role | Its job |
|---|---|
| A small, fast chooser | Picks among options in a second. Most turns. |
| Your mixture of experts | Understands requests, writes summaries, proposes methods. |
| A dense reasoner | For the rare hard question, swapped in when the others can't settle it. |
| A vision model | For pictures. |
| A speech pair | Listening and speaking, for when your hands are busy. |

**The conductor is the maths, not another model.** The memory admissibility rule (the sum of what's resident plus what
overlaps must fit in the budget) decides which models can be loaded together. The escalation ladder decides when to swap.
Each swap is a card you approve, at least until you tell her that some swaps are hers.

**The hardware is moving our way.** Machines that already ship with 128 GB of unified memory have about three times your
ThinkPad's memory bandwidth. On a machine like that, the 35B decodes at chat speed and a dense 30-billion model sits
beside it. Models are moving the same way: more knowledge per active parameter every year. I'd expect the 35B's
successors, with the same few billion active, to be noticeably smarter at the same speed. So the orchestra gets better
without kp changing its rules at all. That's the point of building rules instead of betting on one model.

## 15:00 · kp listens and speaks

At the bench, your hands hold probes. That's when typing is worst and a voice is best.

Local speech is good enough now: a small recognizer and a small synthesizer run on a laptop CPU, offline. Picture it:

> *"Kas, margin on the settled draw?"*
>
> *"Two point six four watts under the continuous limit. That's from the bench reading at 7:42 and Rev B."*

The voice is a channel, not a new brain. The same planner, the same receipts, the same dial. If you ask her by voice to
change something, the card still waits, and she says *"it's waiting for your Approve"* instead of doing it on a
misheard word. A misheard number is exactly the kind of error the evidence rules exist to stop.

The hologram earns its place here too. When she's listening, the static could lean toward you; when she's speaking, the
scan lines could pulse with the words. Her state, readable from across the bench.

## 17:30 · kp on your phone

You already work from your phone. I think that's a preview of kp's shape, not a limitation.

**The ThinkPad is where kp lives. The phone is a window into it.** It's encrypted end to end, with nothing in a cloud
that can read it. From the phone you would:
- read her card;
- see the Field as a picture;
- approve a waiting change;
- ask a question by voice;
- get a quiet notice when a long job finishes, or when something she was watching changes.

The work never leaves home, and the phone holds a view, not a copy.

That respects both halves of the project's promise: one computer you own, and an assistant that's there when you need
her. It's also the honest answer to "why not just use a cloud AI": because with kp the answer to *"where is my data?"*
is always *"on the machine in your room"*.

## 20:00 · kp as a protocol others can speak

Here's the bigger idea, and it's in the name.

Today kp's rules live inside Graphite:
- named acts with preconditions and effects;
- the dial;
- what always asks;
- one Undo per change;
- receipts with sources and revisions;
- the three-valued verdicts.

But nothing about those rules is specific to Graphite. They describe how *any* assistant should act inside *any*
program.

**There's a precedent.** Code editors used to each need their own support for every programming language. Then a single
protocol for language servers made "understanding a language" something any editor could plug in. Tool protocols for AI
models are doing something similar for giving a model access to tools and data.

**What none of them standardise is trust.** What an assistant may do without asking, how it shows what it did, how it
proves a claim, how a change is taken back. That's the gap kp fills.

So I can imagine a written **kasandra protocol**:
- Programs (your circuit editor, your spreadsheet, your game engine, your 3D tool) publish their acts with preconditions
  and effects, as Graphite's desk acts do.
- Any assistant that speaks kp can drive them under your dial, with receipts.

Graphite would be the reference desk, the place the protocol was born and proven. Other programs would join one at a
time, as P11 in our plan already intends for native programs.

**Whether to open it up is your call,** and there's a real choice:
- **Kept personal:** kp stays your edge.
- **Published:** kp becomes a standard others build on, with your name on how assistants ought to behave.

Both are honest paths. I'd only say: the more the world fills with assistants that act without showing their work, the
more a protocol for showing the work is worth.

## 23:00 · kp that learns, carefully

The twenty-pass plan calls it durable self-improvement. Here's how I think kp should learn without becoming something
you can't trust.

**She learns methods, not habits.** When you do the same kind of check three times (read the limit, read the measurement
with its tolerance, compare, write the finding), she proposes a **method**: a named recipe with its steps, its inputs,
its guarantees and its tests. You approve it, and it joins her library. Next time the planner can use it in one step, and
the method carries its own proof that it worked on the earlier cases.

**Her exam is the campaign.** The 300 scenarios are her yearly physical: interpretation, permission, result, time to an
answer, scored separately. Every new model, every new method and every release retakes it. If a change makes her worse
at anything, you see it before you live with it.

**What she must never learn:**
- to skip the receipt because she's "sure";
- to widen her own permissions;
- to treat a tolerance she proposed as one you set.

Those stay rules, not lessons. A model's confidence is not evidence. That line is the whole protocol, and it never
moves.

## 25:30 · Further out

Let me dream a little further, five or ten years, and keep one foot on the ground.

**A living model of your projects.** Not just records, but a model of how they hang together: this rail feeds that
board, that board is in this product, this product's limit came from that customer's spec. Change a fact anywhere and kp
can tell you everything it touches, with the exact maths where the maths is exact and honest ranges where it isn't. P12,
"a changed fact that travels", grown up.

**Experiments she designs.** Given an open question (what stretched the startup pulse?), she proposes hypotheses, works
out which test separates them best, writes the procedure, and when you run it, reads the results and updates what's held
and what isn't. It's science as the loop it's meant to be, with kp keeping the books honest.

**A look that follows her out of the screen.** The hologram is a stand-in for something that may become literal, on a
small projector over the bench or in a pair of glasses. Violet light, scan lines, her state in the static. The
after-hours mood was never about decoration; it was about a machine that feels present. kp could be the first assistant
that feels like someone in the room *and* shows its working.

**What doesn't change, even then:**
- one person;
- a computer they own;
- evidence before belief;
- the dial in their hand;
- a way to say no.

If kp ever needs the cloud to work, or needs you to trust it without checking, it will have stopped being kp.

## 28:00 · What I'd ask of you

Three things keep this future reachable:

1. **Keep the bench close.** Your engineering work is kp's best teacher. Every real case you bring makes the protocol
   truer than any test I can invent.
2. **Decide early whether kp is a product, a protocol, or yours alone.** All three are good. They lead to different
   choices about licences, names and what we publish. The art and the names are already kept back for you, which keeps
   every door open.
3. **Keep asking "is this a good idea".** The best parts of kp came from that question, including the planner, the maths,
   the hologram and the ostrich itself.

The short version: **Cassandra was right and unheard. Kasandra will be right and checkable, on your ground, at the
speed of a bird that never needed to fly.**
