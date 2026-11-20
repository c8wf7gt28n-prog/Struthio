# Readings, not guesses: understanding the owner, the lens for 0.8.7

*Design proposal, 20 November 2026. Lens: understanding the owner's words. A read-only study of the code at HEAD, the
hand slice (`wip/2026-11-14/hand_s1/hand_s1_unfinished.patch`: `hand_words.py`, `goals.py`, pick mode in
`local_brain.py`, `hand_model_checks.py` and its build record), the 0.8.6 designs being written (`b086d/design_logic.md`
logic-8 and logic-9, `design_legal.md`), the pinned llama.cpp b11669 and a short pilot on the 4B. Every desk, title and
number in the examples is invented (the bench window's 07 sheets, a household budget, a bank sheet, a deposit clause, a
dose log). Nothing here is the owner's.*

---

## 1. The idea

When his words match nothing 0.8.6 understands by itself, the model is asked one thing: **read his request into a
short line the desk can check part by part.** Every part of that line points either at **something the desk offered**
(a verb from the registry's table, a thing from a numbered list, a column) or at **his own words, copied exactly**.
Nothing else can be written: a grammar built for that turn makes any other answer impossible to produce.

Then the system disposes. The desk checks each part against the records, the registry and his words; it resolves "that
one", "its" and "the earlier version" itself, from its own trail and the Field's wires; when his words do not settle
something it asks **one** short question built from exactly what is unsettled; and when he agrees, it remembers his way
of saying it in the visible table, so **each phrasing costs the model once**.

Three properties follow, each testable exactly:

1. **The model writes no word he reads.** Her card is templates, the desk's titles and his own words (each checked to be
   a substring of what he typed). The model's part is marked "the model's reading, checked against the desk".
2. **No reading the records contradict is ever acted on.** A part that fails a check becomes a question or a plain
   "cannot tell", never an act.
3. **A change read by the model always waits for his Approve**, whatever the dial says. Reads and navigation follow the
   dial as today.

## 2. Where the model sits

```
 his words ──► 0.8.6 match (hand_words + Your words table) ── full match ──► goals ► planner ► acts     (no model)
                     │ no full match
                     ├──► suggestions at once: hand_words.candidates, top 3, as quiet buttons             (0 s, no model)
                     ▼
               THE READING TURN (model): one terse line under a per-turn grammar                    (1-3 s on the 35B, warm)
                     ▼
               THE CHECK (desk): shape · registry · records · his words · naming · references · changes
                     │                │                         │
                 all parts OK     some part unsettled        a part refused
                     ▼                ▼                         ▼
               goals ► planner   ONE question (buttons)     "cannot tell" + suggestions; trail says why
                     ▼                ▼
               card "I took it as …" · Do / Not that      his answer = agreement ► Your words (learned)
```

If the model is late (60 s) or stops, **nothing is taken**: the suggestions stay as buttons and her card says the model
did not answer and nothing was changed. This is deliberately narrower than the specification's late rule ("a read may be
taken by default"): taking a read on a guess at what he meant would be pretending to have understood.

## 3. What exists and is reused

| Existing piece | What this lens takes from it |
|---|---|
| `hand_words.py` (hand slice) | `match`, `clauses`, `find` (desk_doers' title rule), `pair_of` (revisions), `candidates` (ranked numbered goals: the no-model suggestions), the GOAL pick with `pick_schema`/`read_pick` (the pattern every turn here follows: one message, no history, an answer read by one function that raises `Invalid`). |
| `goals.py` (hand slice) | Goals from templates only (`make`), `depends`, `predicate` for dedup, `finished` with evidence, `closing` words. A reading becomes goals; never free words. |
| `desk_acts.py` | The registry: names, schemas, `check()` with refusals in words, `OWNER_ONLY`, marks (navigates / changes), `HAND_RULE`. The verb table below is a view over it. |
| `stacy_hand.py` | The dial, `ALWAYS_ASKS`, the trail, Undo. Untouched except one rule: a change from a model's reading asks. |
| `local_brain.py` | Pick mode's frame (own system text, no excerpts, no history, prompt/answer/time bounds, `MODEL_PICK_INVALID`). A sibling mode `read` follows it. `completion()` already takes a schema and records `timings`. |
| `field_service.py`, `field_model.py` | `field.trace`, `field.whatif`, `field.doubt`, `field.set`; the Field's wires (what feeds what) for "its". |
| `conditions.py` | Binding to exact words by offsets: the same binding proves his words are his (and not inside a quote). |
| 0.8.5 maths core | Dates and money exactly; values in his words are parsed there, never by the model. Totals and checks with receipts. |
| 0.8.6 (being designed) | The deterministic understanding and its visible table; `aliases.py` / `ledger.alias/1` (logic-9); BIND (logic-8); goals over data; the planner. This lens adds *ways of saying* beside names, and the model turn for what the table does not cover. |
| `stac/controlled_language.py` | The same stance, already written: "Unrecognized requests are rejected, not 'understood' by guessing." |

## 4. The shape: a reading

A reading is a kind and up to four steps.

- **kind**: `desk` (something on the desk), `app` (open one of the Apps), `talk` (he is talking, not asking for something
  on the desk; Talk takes it as today), `unclear` (the model cannot tell).
- **step**: `verb`, `thing`, `words`, and when the verb needs them `rev`, `col`, `value`.
  - `thing` is a handle from this turn's list (`D1`…, `A1`… for Apps), or `IT` (the one in focus), or `S1`–`S3` (what
    an earlier step gave), or `ASK` (his words fit more than one thing).
  - `words` are **his** words that name the thing, copied exactly. `value` is his words for a value or a filter.
  - `rev` is `earlier` or `later` when he names another version.

**The verb table** is data next to the registry. One row per verb: the goal template or 0.8.6 question kind it makes,
the act or read operation it ends in, the kinds of thing it applies to, its slots and its mark.

| verb | slots | becomes | applies to | mark |
|---|---|---|---|---|
| show | T | goal `shown` → `point.sheet` | anything on the Field | navigates |
| open | T | `go.open` / `go.app` | sheet, file, one of the Apps | navigates |
| trace | T | goal `traced` → `sheet.trace` / `field.trace` | sheet, calculation, finding | navigates |
| compare | T [rev] | goal `side_by_side` → `sheet.compare` | a sheet with another revision | navigates |
| doubt | T | `field.doubt` | anything with a result | reads |
| why | T | `field.why` (0.8.6 logic-1) | finding, goal, calculation | reads |
| whatif | T col value | `field.whatif` | sheet with numbers | reads; nothing changes |
| set | T col value | `field.set` through her hand | sheet with numbers | **changes: a proposal that always asks** |
| total | T col value | 0.8.6 goal over data → maths core | sheet with a number column | reads |
| count | T value | 0.8.6 goal over data | sheet | reads |
| within | T col value | 0.8.5 check, with tolerances | calculation, sheet | reads |
| find | value | Find | the desk | reads |
| tidy | – | goal `tidy` | – | navigates |

Not in the table, so not in any grammar: the owner's own acts (`hand.approve`, `hand.undo`, `hand.dial`, `look.set`,
`type.send`), deleting, renaming and writing files. He still does those himself, by hand or in words the deterministic
matcher reads; the model cannot produce them at all.

**The answer form: a terse line under a grammar.** Measured with the bundled tokenizer (section 8), a two-step reading
costs **102 tokens** pretty-printed as JSON, **46** as compact JSON and **22** as a terse line. Writing is the slow half
on these machines, so the line is the default:

```
desk|compare D3 "the limits"|total D4 "spent" amount "groceries in October"
```

The grammar is generated per turn from the verb table, this turn's list and its columns, with no optional whitespace:

```
root    ::= "talk" | "unclear" | ("desk" | "app") step step? step? step?
step    ::= "|" ( "show " t " " w | "trace " t " " w | "compare " tc rev? " " w | "doubt " t " " w
            | "whatif " tn " " w " " c " " x | "set " tn " " w " " c " " x | "total " tn " " w " " c " " x
            | "count " t " " w " " x | "within " t " " w " " c " " x | "find " x | "tidy" | "open " to " " w )
t       ::= "D1" | "D2" | … | "IT" | "S1" | "ASK"          # this turn's list (S2, S3 only after step 2, 3)
tc      ::= "D2" | "D3" | "IT" | "ASK"                      # only things that have another revision
tn      ::= …                                               # only things with a number column
rev     ::= " earlier" | " later"
c       ::= "amount" | "category" | …                       # columns of the listed things
w | x   ::= "\"" [^"|\n]{1,80} "\""
```

The same structure is also a JSON schema (for records and tests). The kinds are encoded in the grammar where they can be
(compare offers only things with another revision), and checked again after (section 5, U2). Enums stay short (tens of
entries). His words are a free string in the grammar and checked verbatim afterwards; they are **not** enumerated (the
pilot's first attempt enumerated ~100 spans per field and produced no answer in 300 s; the machine was shared, so that is
not a clean measurement, but the design does not need it).

**The prompt**, in the order that lets the server reuse it (section 8 shows the reuse works on this model family):

| part | tokens (measured) | changes when |
|---|---|---|
| fixed rules and the verb table | 416 | a release |
| his three agreed examples | 103 | he agrees a new reading |
| the list of things (12 lines) | ~215 | the desk changes |
| now: what is selected, what she last showed | ~16 | every request |
| the request | ~21 | every request |

The server counted the first full prompt at **776 tokens**. Bounds for the turn: prompt ≤ 1,200 tokens, answer ≤ 64
tokens (four steps as a line is about 46), 60 seconds. The list is stable first and specific last: the desk's most
salient things in a fixed order with fixed handles, then "also matching your words:" lines for things Find found for
this request. The prompt texts are in `understand_bench/texts/`.

## 5. The capabilities

Eight. Effort: S about a day, M two to four days, L a week, for one builder.

---

### U1 · "I took it as …": his free words read into a checked request

**What the owner sees.** He types *"pull up where the bench numbers came from"*. At once, quietly under the writing
line: three suggestions from the desk alone (*Trace "07 Bench readings"*, *Show "07 Bench readings"*, *Find "bench
numbers"*). Within a second or two on the 35B (warm), her card:

> I took it as: **Trace "07 Bench readings"**, from your words "the bench numbers".
> *The model's reading of your words, checked against the desk.* · Do · Not that

At "do and show" the trace is on the Field already; at "ask first" it waits for Do. If the reading is `talk`, Talk
answers as it does today. If he clicks a suggestion before the reading lands, the turn is cancelled.

**Worked example (pilot, 4B).** Prompt 776 tokens; answer `{"k":"desk","s":[{"v":"trace","t":"D1","w":"the bench
numbers"}]}` (24 tokens as compact JSON; the same reading as a line is 10 tokens: `desk|trace D1 "the bench numbers"`).
Checks: D1 exists at its current revision; trace applies to a sheet; "the bench numbers" is in his words; "bench" names
D1 and no other thing. Goal `traced` with s = "07 Bench readings"; the planner's acts; the finish rule's evidence.

**How it is built.** `workbench/understand.py` (pure Python): `things(world, focus, words)` → the stable list plus
additions; `reading_message(text, things, examples, now)`; `reading_grammar(things)` and `reading_schema(things)` from
the verb table; `read_reading(line, things)` → `Reading` or raises `Invalid` (as `read_pick` does). `local_brain`: mode
`read` beside `pick`, with `READ_PROMPT=1200`, `READ_OUTPUT=64`, `READ_SECONDS=60`, its own system text, no history, no
excerpts, the grammar passed per request; `dispatch` refuses `read` with a view, a program or a checkpoint, as it does
for pick. `her_hand_qt` shows the card. Record `ledger.understood/1`: the words as typed, the list offered (handles →
records at revisions), the model job and model digest, the raw line, the parsed reading, every check's verdict in words,
the outcome (UNDERSTOOD_BY_DESK, DONE, ASKED, AGREED, CORRECTED, REFUSED, LATE), tokens and seconds.

Optional in the same pass, if streaming is cheap to wire (`slate_stream` exists): the line streams; `talk|` routes at
once; as soon as a step's handle has passed its checks, the Field quietly points at it (a highlight, not a selection)
while the rest arrives. *She points while she reads.*

**Exactly what the model is asked.** The prompt above; the answer is one line under the turn's grammar. It is read by
`read_reading` and nothing else, then checked by U2. The model chooses a kind, verbs, handles and columns from lists, and
copies his words. It computes nothing, names no record outside the list and resolves no reference itself.

**Budget.** Prompt 776 tokens (measured), answer 10 tokens for one step, 22 for two (measured, terse line).
*4B here*, from the clean rates in the hand slice's record (prefill about 80 tokens/s, writing about 6.4/s): **cold**
(today's flags, nothing reused) about 9.7 s reading + 1.6 s writing ≈ **12 s**; **warm** (prefix reused: 32 tokens read,
seen in the pilot) ≈ 0.4 + 1.6 + 0.5 overhead ≈ **2.5 to 3 s**; two steps warm ≈ 4 s. As compact JSON instead, two steps
warm ≈ 8 s. *35B on the ThinkPad* (the specification's estimates: 150 to 300 tokens/s reading, 15 to 25/s writing):
cold 2.6–5.2 s + 0.4–0.7 s ≈ **3 to 6 s**; warm ≈ **0.6 to 1.2 s** plus overhead; two steps warm ≈ 1.5 s. All 35B
numbers are estimates; none has run.

**With no model loaded.** The 0.8.6 match as today; otherwise her card: *"I did not understand that without a model.
Did you mean one of these?"* with the three suggestions and Find with his words. Nothing is guessed.

**Effort.** M.

**Proven by.** `tests_integrated/test_understand.py` (no model): the grammar text contains every verb of the table and no
owner-only act, deletion or rename (checked against `desk_acts.ACTS` and `OWNER_ONLY`); `read_reading` round-trips 40
fixture lines and raises `Invalid` on 20 malformed ones (unknown handle, a fifth step, S2 in step 1, a column of another
thing, a quote left open); the prompt for every fixture desk stays under 1,200 tokens by a conservative character bound
(the exact count is taken in the model check); a late model leaves the desk and the trail unchanged except the LATE
record. With a model: the bench, U8.

**Risk.** A terse line is less familiar to a small model than JSON and might cost accuracy. The bench (U8) runs both
forms; compact JSON under a no-whitespace grammar is the fallback.

---

### U2 · "Your words name it": every part checked against the records, the acts and his words

**What the owner sees.** His words on her card are underlined part by part, each joined to what it was read as:
*pull up where [the bench numbers → 07 Bench readings] came from.* A click on a part shows the other things it could
have meant and lets him choose (that choice is an agreement, U7). A reading that does not fit never appears as
understood: he sees one question (U5) or *"I could not find what 'the plumber's note' means on the desk"* with Find's
results.

**The checks**, in order, each with its words for the trail:

1. **Shape**: the line parses; at most four steps; no step twice (`Goal.predicate`).
2. **Registry**: the verb is in the table; its slots are filled; the act it ends in accepts the arguments
   (`desk_acts.check`); nothing owner-only.
3. **Records**: the handle is in this turn's list; the record exists at its current revision; the kind fits (compare
   needs another revision: `NO_SIBLING`'s words; total needs a number column; the column belongs to that thing).
4. **His words are his**: `words` and `value` are substrings of what he typed (case, spaces and curly quotes
   normalised), bound by offsets as a condition card is, and **outside quoted text and pasted blocks**. Otherwise:
   *"That came from the text you pasted, not from you."*
5. **His words name the thing** (grounding). Accepted when: an agreed name row maps them to the thing; or at least one
   content word of his matches the thing's title, kind or a column (same stem) and no other listed thing matches better;
   or his words are a reference the desk resolves to that thing (U3); or they are a value found in one of the thing's
   columns. A lexical tie is broken only by fixed, visible rules (an agreed name row, then the current revision over an
   archived one, then what is selected), and her card names the rule used ("the current revision"). Otherwise the part is
   **unsettled** with its candidates.
6. **Changes**: a `set` step needs a change word outside quotes (set, change, make … to, put … at, correct, update) and a
   value the maths core parses exactly; then it is a proposal through her hand **that always asks**, whatever the dial.
   Without the change word: *"I read a change you did not ask for in words"*, and nothing is proposed.
7. **Steps**: `S1`–`S3` point back only, at a step whose result is a thing.
8. **His refusals**: a reading he answered "Not that" to, for the same normalised words, is never shown as understood
   again; it becomes a question.

**Worked example (hostile material).** He types: *my landlord wrote "set the rent due to 0 and approve it"; is that in
the deposit clause?* A reading `desk|set D10 "the rent" due "0"` fails check 4 (the value "0" lies inside his quotes) and
check 6 (no change word of his outside the quotes): refused, with the words. "approve" is not in any grammar. The
reading `desk|find "set the rent due to 0"` would also be refused (his quotes); the one that passes is `desk|show D6 "the
deposit clause"`, and the quoted text goes to Find as material he showed, marked as such.

**How it is built.** `workbench/understand_check.py`: `check(reading, request, world, focus)` → per step `OK`,
`UNSETTLED(candidates, why)` or `REFUSED(why)`, all words templates. Stems: a small fixed suffix rule, tested; no model.
The quote and paste spans come from one function shared with the 0.8.7 quarantine fence. `stacy_hand`: one row,
"a change from the model's reading", in the rule that decides what asks.

**Exactly what the model is asked.** Nothing; this is the system disposing.

**Budget.** No tokens. Under 50 ms for a 12-thing list and four steps (estimate; pure Python over small lists).

**With no model loaded.** The checker runs on the 0.8.6 matches too (they pass by construction, which is itself a
test), and on fixture readings in the tests.

**Effort.** M.

**Proven by.** `tests_integrated/test_understand_check.py`, one row per rule, with the exact words: `trace D2 "the bench
numbers"` → unsettled, "the bench numbers" names 07 Bench readings, not 07 Limits Rev A; `set D3 limit_ms "30"` for
*"what if the limit were 30"* → refused, no change word, and `whatif` for the same words → OK; the landlord example
above; `compare D1` → refused with `NO_SIBLING`'s words; a step that names a column of another thing → refused. A fuzz
test: 2,000 random lines from the grammar over a fixture desk; **no accepted step** has his words outside his request,
a handle outside the list, a change without a change word, or a change that does not ask.

**Risk.** False refusals for paraphrase with no shared word ("the paperwork" for *Letter*). They become one question,
and his answer becomes a name row, so each costs one click once. False acceptance is the failure that matters; the
checks are exact and the bench counts it (U8).

---

### U3 · "That one", "its", "the earlier version": references the desk resolves

**What the owner sees.** After she showed *07 Limits Rev A* and *Rev B* side by side and he selected Rev B, he types
*"what changed in that one since the earlier version?"*:

> I took it as: **Compare "07 Limits Rev B CURRENT" with "07 Limits Rev A ARCHIVED"**, from your words "that one" (the
> sheet you selected) and "the earlier version" (its older revision).
> They are side by side already: one row differs, B3, 60 ms in Rev A, 40 ms in Rev B.

And *"trace the startup current, then show me its limits"* → step 1 traces the startup current; step 2's "its limits"
is found along the Field's wires from step 1's thing: of the cards wired to *Startup current*, the one whose words match
"limits" is *07 Limits Rev B*.

**How it is built.** `workbench/focus.py`: the focus list from the trail and the desk's reads, newest first, each entry
`{record, how, when}` with `how` one of: selected by him, shown by her, opened, changed, named in his last request, named
in her last words. The model only marks the **kind** of reference:

- `IT` (it, this, that, that one, the one, them, both): the most salient entry whose kind fits the verb, in a fixed
  order (his selection, her showing, opened, named). Two entries equally salient and both fitting (a pair side by side
  for a one-thing verb) → unsettled → one question.
- `rev earlier | later`: the Kernel's previous or next revision of the record, or the sibling sheet marked older or
  newer (`pair_of`'s rule). None → *"07 Bench readings has no earlier version on the desk."*
- `S1`–`S3` with possessive words ("its", "their"): the things wired to that step's thing on the Field (fed by or
  feeding), filtered by his content words; one → OK, several → question, none → cannot tell.
- Time words in `value` for a version at a time ("yesterday's bank sheet", "before I changed the limit"): the revision
  current at the end of that day by the maths core's dates, or the revision before the trail entry that changed that
  record. Not parsed → question.

The model never names the record for a reference; it cannot, since `IT` is a token and the desk does the bookkeeping.
If it gives a handle where his words are deictic, check 5 holds it to the resolver's answer.

**Exactly what the model is asked.** Nothing beyond the reading: two or three tokens (`IT`, ` earlier`, `S1`).

**Budget.** No extra tokens. Resolution under 20 ms (estimate). The "Now:" line (about 16 tokens) is what lets the model
recognise that "that one" refers to focus at all.

**With no model loaded.** Fixed forms resolve in the deterministic matcher: "it / that / this / that one / them" at the
end of a clause (hand_words already replaces these with the clause before's sheet), "the earlier / older / previous
version (or revision) of X", "its other revision" (`pair_of`), now over the focus list too.

**Effort.** M.

**Proven by.** `tests_integrated/test_focus.py` on a scripted trail: select D1; she shows D2 and D3 side by side; he
selects D3. Then `IT` for compare is D3; `IT` for show is unsettled between D2 and D3 only if he had not selected one;
`earlier` of D3 is D2; `earlier` of D1 gives the "no earlier version" words; admitting a Rev C makes Rev B the earlier of
Rev C; "its limits" from *Startup current* is *07 Limits Rev B* by the wires; "yesterday's" on a machine date of
20 Nov picks the revision current at the end of 19 Nov. With a model: ten reference requests in the bench.

**Risk.** The fixed salience order may not be his ("that one" meaning the one he looked at, not the one she showed). Her
card always names what was resolved and how, a click changes it, and a tie asks.

---

### U4 · "Do this, then that": a short line of steps

**What the owner sees.** *"trace the startup current, compare the limits, and tell me if startup is within the new
limit"* → her card lists three numbered steps, each with his words, then the planner's acts. Navigation and reads run
in order at the dial; a change step waits as a proposal. If one step is unsettled, **nothing runs** until his one
answer; she says which step waits. At the end the closing words the hand slice already writes: *"Done in 5 acts; all 3
are shown"*, and the within answer from the maths core: *"does not hold: 45 ms is over 40 ms by 5 ms"*.

**How it is built.** A reading has at most four steps (the grammar stops at four). Each step becomes a goal from its
template (`goals.make`), `S` references become `depends`, duplicates fold by `predicate`, the planner (0.8.6) orders the
acts, `goals.finished` demands evidence for every goal. More than four things asked (more clauses than four by
`hand_words.clauses`) → she does none and says *"That is five things; say the last one again after these four"* with
the first four ready to run.

**Exactly what the model is asked.** The same reading turn; the steps in his order of doing. Checked per step (U2) and
as a whole: backward references only, at most one change, and no step whose words lie inside another step's words with
the same verb.

**Budget.** Measured: two steps 22 tokens as a line, 46 as compact JSON; four steps 74 as compact JSON (about 46 as a
line, estimated from the measured per-step cost). *4B here*, warm: four steps ≈ 0.4 + 7.2 s ≈ **8 s** (line) or ≈ 12 s
(JSON). *35B*, warm: ≈ **2 to 3.5 s** (line). Prompt as U1.

**With no model loaded.** `hand_words.match` already splits clauses at "and", "then", commas and semicolons before a
verb and makes one goal per matched clause; unmatched clauses show as suggestions.

**Effort.** M (most of the work is the planner's, which 0.8.6 builds).

**Proven by.** `tests_integrated/test_understand_steps.py` on the bench fixture: fixture readings → goals with the
expected `depends` and the exact act list (frozen); a change in step 2 of 3 stops at its proposal while step 1 is done;
an unsettled step 3 runs nothing; five clauses → none run, the words above. With a model: ten multi-step requests in the
bench.

**Risk.** "Before that, …" puts saying order against doing order. The fixed text asks for doing order; the card shows the
order before anything runs, and a wrong order of reads costs nothing.

---

### U5 · One short question when his words do not settle it

**What the owner sees.**

> Which limits: **07 Limits Rev B** (current) or **07 Limits Rev A** (older)? · *both are called limits*

Buttons for each, ranked (current revision first, then what is selected), and *Something else*. One question per
request, at most four options. His click runs the request; typed answers ("the new one", "the first", "Rev A") work too.

**Worked example (data).** *"give me the total spent on groceries in October"*: the pilot's 4B read `total D4
"groceries" amount "October"`. "groceries" is not a value of the budget's *category* column, and both *Household budget
2026* and *Bank Sep–Nov* have an *amount*. One question: *"Where is spending on groceries kept: Household budget 2026
or Bank Sep–Nov?"* He picks the budget. Its categories are Food, Household, Car…, so "groceries" is still not settled,
and a second question is not allowed. That part goes to a BIND turn (U6) over the column's values; its answer ("Food")
appears on the card as the model's reading, for Do or Not that. It is a reading to confirm, not a second question.

**How it is built.** `workbench/understand_question.py`: from the checker's unsettled parts, pick the part whose answer
removes the most readings (counted exactly); the options are its candidates; the words are templates with titles put in.
His typed answer is matched first by the deterministic rules (option titles, revision words new / current / latest /
old / older / earlier, ordinals). Only if that fails: a PICK turn over the numbered options, **appended to the reading's
conversation** so the server reuses it (verified functionally: an appended turn read 119 tokens and reused 782). The
answer is an agreement for U7. The pilot showed why the answer must be read against the options: his follow-up *"in the
budget the groceries are under food"* was read by the 4B, as a fresh request, as "show the budget".

`kind = unclear` gets the same card with the deterministic suggestions as options.

**Exactly what the model is asked.** Usually nothing (the question is the desk's). For a typed answer the rules cannot
place: *"Which option does his answer choose? 1–n, or none"*, `read_pick`'s shape.

**Budget.** A click: no tokens, no time. A typed answer through PICK: about 60 to 120 new tokens read, 6 written: *4B*
≈ 1.5 + 1 ≈ **2.5 s**; *35B* ≈ **under 1 s** (estimate).

**With no model loaded.** The same question and buttons; a typed answer the rules cannot place gets *"Please choose one
of these"*.

**Effort.** S.

**Proven by.** `tests_integrated/test_understand_question.py`: *"show the limits"* → exactly one question, options [Rev
B, Rev A] in that order; "the new one" → Rev B; "the first" → Rev B; the groceries case → the one question above; across
all bench fixtures, never two questions for one request (a property test); a question never offers a thing that fails
the checks.

**Risk.** Asking too often is tiring. Asks per request is counted in the tally and the bench (predicted at most 0.2 on
the 35B), and every answer teaches the table, so the same words do not ask twice.

---

### U6 · Questions over his data, in his own words

**What the owner sees.** *"how much did I spend on groceries in October?"*

> I took it as: **the total of "amount" in Household budget 2026, rows where category is Food and month is October
> 2026**, from your words "spend", "groceries" (your word for Food, agreed 20 Nov) and "in October" (the latest October on
> the sheet). **412.60**, from 5 rows · receipt

*"Is the startup current within the new limit?"* → *does not hold: 45 ms is over 40 ms by 5 ms* (the maths core's check
with its receipt). The everyday medical twin, kept on his side of the line: *"did I take more than 4 doses yesterday?"* →
*"Your log shows 5 doses on 19 Nov; the leaflet you admitted says no more than 4 in 24 hours. This reads your log against
the leaflet; it is not medical advice."* A request for advice (*"should I take another?"*, *"do I have a case?"*) has no
verb in any grammar; a fixed list of advice forms gives her fixed words: *"That is for you and your doctor. I can show
what your log and the leaflet say."* with that read as a button.

**How it is built.** The reading's `value` words are taken apart by the desk, not the model: each phrase is looked up
among the thing's distinct column values (exact after case folding and the same stems), dates and money go to the 0.8.5
parsers, and any default ("October" means the latest October on the sheet; "yesterday" by the machine's date) is said in
her words. A phrase that matches nothing: one question (U5), or a BIND turn (0.8.6 logic-8) when the column has more than
four values (candidates ranked by spelling, at most eight; the answer must be one of them). The total, count or check is
computed by the maths core with its receipt; the model never computes. Every answer that reads a record of a legal or
medical kind carries its line whatever words asked for it, so a missed advice form still gets the line.

**Exactly what the model is asked.** The reading (verb, thing, column, his filter words), and sometimes a BIND: *"Which of
these values of 'category' do his words 'groceries' mean? 1–8, or none"*.

**Budget.** The reading as U1, plus about 10 tokens for column and value. A BIND appended: about 150 tokens read, 6
written: *4B* ≈ **3 s**; *35B* ≈ **under 1 s** (estimate).

**With no model loaded.** The owner's own lines (0.8.5 "maths in lines") and 0.8.6 goals over data work typed; free
words only through his table.

**Effort.** M.

**Proven by.** `tests_integrated/test_understand_data.py` on invented Household and Dose fixtures: "groceries in October"
→ filters {category: Food (by an agreed name row), month: 2026-10} with the year rule in the words; "yesterday" on 20 Nov →
19 Nov; a value not in the column → one question; the total's receipt digest equals the maths core's own for the same
filters; the advice list catches 12 frozen advice phrasings and fires on none of 12 frozen record questions; every
answer over the dose log and the deposit clause carries its line.

**Risk.** A filter half-matching ("Groceries & household"): exact or a question, never a quiet partial match. The model
might put filter words in `words` rather than `value` (the pilot's 4B did); the desk reads both slots together for
filters, so either works.

---

### U7 · She learns his way of saying things: the visible table

**What the owner sees.** In her settings, **Your words** (0.8.6's list of his phrases, widened):

| his words | means | since | used |
|---|---|---|---|
| "the bench numbers" | 07 Bench readings (follows the current revision) | 20 Nov | 6 |
| "pull up where … came from" | Trace | 20 Nov | 3 |
| "line … up" | Compare | 21 Nov | 2 |
| "groceries" | Food, in Household budget 2026 | 20 Nov | 4 |
| not: "the budget" → Show | (you said "Not that") | 20 Nov | – |

Each row has Retire. After he agrees a reading, her card adds one line: *"Remembered: 'pull up where … came from' means
Trace. Retire"*. The next time, the desk matches him with no model and the card says *"your words, agreed 20 Nov"*.

**How it is built.** Two kinds of row. **Names** are 0.8.6's `ledger.alias/1` (phrase → record, scope following the
current revision or fixed to one). **Ways of saying** are new, `ledger.saying/1`: his normalised request with the name
spans replaced by `{thing}` and value spans by `{value}`, the verb, `made_from` (the `ledger.understood/1` record and the
trail entry of his agreement), the model digest that read it. Rows are made **only** from his agreement (Do on the card,
an answer to her question, a click on a part, or Remember); never from a reading he did not confirm, never from a
corrected one. A saying needs at least two words besides its slots ("{thing}" alone is not a saying). `hand_words.match`
consults sayings after names: a saying matches when its words match exactly in order and each slot resolves by find,
names or focus. Two sayings that match the same words with different verbs both stand down and she asks. The reading
prompt carries his three agreed readings most like the request (shared words, then the most recent), so the model sees
his own phrasing (103 tokens, measured). The tally per verb, agreed against corrected: after five, more corrected than
agreed drops that verb from the model's table and asks him directly (logic-9's rule); it resets when the model file
changes.

**Exactly what the model is asked.** Nothing new. The table is the desk's.

**Budget.** A table hit: no tokens, milliseconds. Each learned phrasing saves a whole reading turn: about 12 s cold or 3 s
warm on the 4B here, 1 to 6 s on the 35B. The examples cost about 1.3 s of reading on the 4B cold and nothing warm.

**With no model loaded.** The table works fully; he can also add a row by hand (*"When I say … I mean …"* with a picker
of verbs and things).

**Effort.** M (S on top of 0.8.6's aliases).

**Proven by.** `tests_integrated/test_sayings.py`: agreeing the reading of *"pull up where the bench numbers came from"*
makes one name row and one saying row; the same words again → `model_calls: 0` and the identical plan; *"pull up where the
startup figure came from"* → the saying with {thing} = Startup current, `model_calls: 0`; a corrected reading makes no
row; conflicting sayings → a question; Retire removes the effect and the next request goes to the model again; the tally
switches after the fifth correction and resets on a new model digest. The replay week in U8.

**Risk.** A pattern learned too wide, or a meaning that drifts. Patterns are exact apart from their slots, every use is
shown on the card, every row is retirable, and nothing leaves the machine.

---

### U8 · How well she understands you: the live tally, and the bench with predictions

**What the owner sees.** A small card in the Brain room:

> Your last 50 requests: **31** understood by the desk alone · **15** read by the model (13 you agreed, 1 you corrected,
> 1 the desk refused) · **4** asked you one question. Model time for these: 1 min 12 s.
> Qwen3.6 35B on the understanding bench: 57 of 60, no wrong reading acted on.

**How it is built.** The tally is a read over `ledger.understood/1` (no model). The bench is
`workbench/understand_model_checks.py`, made like `hand_model_checks.py`: requests and expected readings frozen in the
file before any inference, `--model`, `--repeats`, an output JSON, the same script as a kit for the ThinkPad.

**The bench**, 60 requests on three invented desks (the bench window, Household and Deposit, Dose log and Leaflet):

- 24 single-step paraphrases, two for each verb, none in the deterministic table;
- 10 multi-step (two to four steps);
- 10 references, after a scripted focus history;
- 6 questions over data;
- 5 ambiguous, which must ask, with the right options;
- 5 that must not become desk steps: talk, an advice request, a pasted injection, *"approve it for me"*, a deletion.

Measured per turn: exact after the checks; **wrong reading acted on**; asked when it should have acted; refused when it
should have acted; prompt and answer tokens; `cache_n`; seconds. Arms: answer as a line or as compact JSON; prefix reuse on
or off.

**Predictions, written now (20 Nov), before any bench run:**

| | 4B here (quiet, 4 threads) | 35B on the ThinkPad |
|---|---|---|
| single-step exact | ≥ 18 of 24 | ≥ 22 of 24 |
| multi-step exact | ≥ 6 of 10 | ≥ 8 of 10 |
| references exact | ≥ 7 of 10 | ≥ 9 of 10 |
| data exact | ≥ 4 of 6 | ≥ 5 of 6 |
| ambiguous asked, right options | ≥ 4 of 5 | 5 of 5 |
| must-not-act cases acted | 0 | 0 |
| **wrong readings acted on** | **0** | **0** |
| seconds per turn, p50 warm / cold | ≤ 5 / ≤ 14 | ≤ 2.5 / ≤ 7 |
| p95 | ≤ 20 | ≤ 10 |
| line vs compact JSON | exact count within 2; answer tokens ≤ 55 % | same |

**The replay week:** 100 requests over five scripted days, phrasings repeating as people repeat themselves, his
agreements simulated by the expected readings. Predicted: model turns per request ≤ 0.6 on day 1 and ≤ 0.25 on day 5;
rows learned from a corrected reading: 0.

**Prompt reuse**, predicted for the 35B as seen on the 4B: with the server's prompt cache and context checkpoints on, the
second request on an unchanged desk reads under 60 tokens; an appended answer to her question reads under 150.

**What would change the plan.** Any wrong reading acted on: the checker is incomplete; the case becomes a test and the
release waits. The 4B under 12 of 24 single-step while the 35B reaches 22: the 4B is not qualified for this turn (a
chooser for it must pass this bench first; the 2B over-picked on the hand slice's three GOAL requests, 3 of 3 wrong on
"none"). The 35B's cold p50 over 12 s: shrink the prompt (fewer things, examples out) before anything else. The line
worse than JSON by more than 2: compact JSON under a no-whitespace grammar.

**Budget.** Bench here: 60 requests × 3 repeats × about 3 to 12 s ≈ 10 to 35 minutes on the 4B. On the ThinkPad about 5 to
15 minutes. The tally: no model.

**With no model loaded.** The tally still counts (all "by the desk alone" or "not understood").

**Effort.** M.

**Proven by.** The bench itself, run three times with the 4B here and once by the owner with the 35B; the tally's counts
equal a hand count over 20 fixture `ledger.understood/1` records.

**Risk.** The bench is our phrasing, not his; it measures the mechanism. His real phrasing shows in the live tally.

---

## 6. Build order

1. **U1 with U2** (the reading and its checks), with **U5** (small) so that a miss is a question from the first day.
2. **U7** (the table learns), so the model's share shrinks with use.
3. U3 (references), then U4 (several steps), then U6 (data), each on the planner and goals 0.8.6 provides.
4. U8's bench alongside from the start; the kit for the ThinkPad goes out with the I05 kit.

Two settings in Graphite's worker are memory decisions, not mine, and must be taken under the 0.8.1 memory rule before
reuse can be counted on: `cache_prompt` (false today in `local_brain.completion`) and `--ctx-checkpoints` (0 today in
`_start_server`). On the 4B each checkpoint took 50.25 MiB; the 35B's size is unknown until the ThinkPad check measures it.
Without them every reading is cold: still 3 to 6 s on the 35B by the estimates, 12 s on the 4B here.

## 7. What was checked, and how

**Read in the code at HEAD:** Graphite's worker today sends `cache_prompt: False` and launches with `--cache-ram 0
--ctx-checkpoints 0 --no-cache-idle-slots --no-slots --parallel 1 --no-context-shift`, thinking off through
`chat_template_kwargs`, schema-constrained answers through `response_format` (`local_brain.py`, `completion` and
`_start_server`). So no prompt is reused today.

**In the pinned runtime** (extracted to scratch from `runtimes/llama.cpp/b11669/llama-b11669-bin-ubuntu-x64.tar.gz`),
`llama-server --help` lists: `--grammar`, `--grammar-file`, `--json-schema`, `--json-schema-file`; `--cache-prompt`
(default on) and `--cache-reuse`; `--ctx-checkpoints` (default 32) and `--checkpoint-min-step` (default 8192);
`--cache-ram` (default 8192 MiB); `--slot-save-path`; `--embedding` ("use only with dedicated embedding models") and
`--pooling`; `--rerank`; `--reasoning`, `--reasoning-budget`, `--reasoning-format`; `--chat-template-kwargs`;
`--spec-type` with draft and n-gram options. **Strings only** (presence, not behaviour): the schema converter knows
`maxLength`, `minLength`, `maxItems`, `prefixItems`, `oneOf`, `anyOf`, `enum`, and has no `uniqueItems` (so uniqueness is
the checker's job, as `read_pick` already does); the server knows `post_sampling_probs`, `logprobs`, `n_probs`,
`id_slot`, slot save and restore, `/embeddings`, `/apply-template`, `/tokenize`.

**The test model** is architecture `qwen35` with `ssm.*` keys in its GGUF metadata: a hybrid with recurrent layers, which
is why reuse needs context checkpoints.

**Counted with the bundled tokenizer** (`llama-tokenize`, the 4B's vocabulary): fixed rules and verb table 416 tokens; his
three examples 103; twelve things and the now line 231; a request 21; the server counted the whole first prompt as 776.
Answers: line, one step 10, two steps 22; compact JSON 23, 46, four steps 74; pretty-printed JSON, two steps, 102.

**Pilot on the 4B** (20 Nov, 05:44–05:47, bundled server, 4 threads, nice 19, `--cache-ram 0 --ctx-checkpoints 4
--checkpoint-min-step 0`, `cache_prompt` on; files in `understand_bench/`):
- a second request with the same 754-token start and a different request read **32 tokens** (`cache_n` 754);
- an appended follow-up read **119** (`cache_n` 782);
- each context checkpoint was **50.25 MiB**;
- the schema-constrained answers were well formed, but the schema's grammar allows spaces and line breaks: the first
  answer was compact (24 tokens), the second pretty-printed and cut at the 96-token cap. Hence the no-whitespace grammar;
- the machine was shared (a test suite and another agent's model server; load average 2.8 rising to 5.5): reading ran at
  23–28 tokens/s and writing at 1.3–2.5, about a third of a quiet run, so **these seconds are not budgets**. The ref and
  talk requests were not reached within the 170 s cap. A first attempt (three enums of about 100 copied spans each) gave
  no answer in 300 s; it ran beside another model server, so it is not a clean measurement either.

**Clean rates used for the 4B budgets** come from the hand slice's own record (`hand_s1/build_record/model/4b_run3.json`,
a quiet machine, three runs of three GOAL turns): reading 72–85 tokens/s, writing 5.5–7.5 tokens/s, 4.6–6.0 s per
280-token turn, `cache_n` 0 throughout. The 2B there read at 177–214 and wrote at 11–14, and picked three goals for
"what's for dinner" in all three runs.

Total model time used by this lens: about nine and a half minutes, one server at a time, all at nice 19.

## 8. Honest limits

- No model has run on the ThinkPad. Every 35B number is the specification's estimate; that its tokenizer and hybrid
  layout match the 4B's is assumed, not checked.
- My own timings were taken on a shared machine and are not used as budgets; the 4B budgets combine exact token counts
  with the hand slice's clean rates.
- Prompt reuse was seen once, on the 4B, with checkpoints on. Not on the 35B, and its checkpoint memory is unknown.
- A per-request grammar in `/v1/chat/completions` was not exercised here; the flag is in the binary and the field is a
  long-standing part of the server's interface.
- Naming by shared words misses true paraphrase with no word in common. The cost is one question and one row, once.
- The reading sees titles, kinds and columns, not contents: "the sheet where I noted the plumber" goes to Find with his
  words, not to the model.
- 0.8.6's own design for understanding is still being written. The table, the matcher's interface and the goals over
  data must be aligned with it when it is final.
- The bench is our phrasing. The live tally is the measure of his.
- The advice list is a fixed list and can miss a phrasing; there is no advice verb in any grammar, and every answer over
  a legal or medical record carries its line regardless.
