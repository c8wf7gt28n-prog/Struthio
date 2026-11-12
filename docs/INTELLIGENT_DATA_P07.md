# Graphite P07 · Intelligent data arrangement

Open **Project Desk → Ask Graphite**. Enter a question, select your assignment,
and add any extra source addresses. **Prepare evidence** runs on the CPU and
shows the selected passages, quantities, and gaps. You can do this with the
local model stopped.

## Put a calculation beside its sources

For an example, put “The warm rail is 12 V. The warm draw is 200 mA.” in a
workspace file named `rail.txt`. Add `files:rail.txt` to Extra sources. Enable
**Include an exact calculation**, enter `voltage * current`, and give it these
source quotes.

```text
voltage = 12 V
current = 200 mA
```

Set the result unit to `W` and the condition to “At the stated warm operating
point.” Preparation shows **2.4 W (12/5 exact)** and keeps the two source spans.
The condition travels with the result. If the question is whether a supply
can start the device, the warm calculation leaves the startup draw open.
When several passages contain a quote, use `name = files:rail.txt | quote` to
select its source. A still ambiguous quote remains a gap. The Kernel can also
bind by a retained passage ID.

## Follow the evidence

- Files and native documents keep their revision and text location. Use
  `namespace:ID` to search an already indexed, admitted reference collection.
  Reviewed reference packets keep their original passage locators, fact
  roles, variants, and conditions. Their address is `packet:ID`.
- Add `calculation:ID`, `reason:ID`, `artifact:ID`, or `condition:ID` to read a
  saved calculation, declared dependency graph, application output, or
  condition card. Each uses its existing applicability reader.
- The compact packet distinguishes unresolved quantities, reviewed facts,
  exact consequences, and scope. Preparation uses the existing reference
  index, ranking, quantity extraction, unit-aware expression engine, and
  read tool selector. It keeps numeric roles explicit and records suggested
  readers separately from actual observations.
- An answer turn receives the selected text and the calculation rows whose
  dependencies fit the measured model context. It can suggest one passage
  from a short catalog of omitted sources and the next question. **Read
  passage** shows the bound text. **Focus next turn** prepares a fresh
  selection from the same sources, with that passage first. You can edit the
  question before focusing, then choose when to ask the local model.
- The Kernel checks source revisions before and after inference, and when
  reading or focusing a passage. When a source changes, prepare again. The
  older packet remains available as a historical record. **Inspect context
  and result** shows the original bindings and what actually fit the turn.

Exact expressions use the existing arithmetic engine's supported dimensions.
Quantity mentions in other units remain visible for interpretation. Native
documents, source text, and reviewed reference facts can contain ambiguous
roles or conflicting conditions. The calculation and its evidence retain
those boundaries. Follow-up selection and interpretation quality depend on
the selected model.

This checkpoint uses a disposable local source and a short native Qt
walkthrough. The model handoff is observed with a held inference boundary.
ThinkPad and live model qualification remain pending.
