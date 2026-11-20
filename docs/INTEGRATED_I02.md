# Integrated I02 mathematics and applications

This candidate connects an exact mathematical model, bounded SymPy and Z3 adapters, a What if calculator, and real Calc/Writer operations to the problem sheet introduced in I01. It retains the complete previous application. It targets the single Debian Linux Ledger desktop.

## Install and try

Extract the whole ZIP into a new program folder and retain the previous program and workspace. On Debian, run `bash INSTALL_DEBIAN.sh --math` as your normal desktop user. The math option adds the pinned Python math/document packages, Calc, Writer and a headless JDK. Existing system-package approval and offline behavior are preserved. If system prerequisites are installed, use `bash INSTALL_LEDGER.sh --math`.

The exact calculator and graph use the standard library. Normal Ledger startup remains usable without optional solvers or Office software. Missing dependencies are reported explicitly. Java 17 or newer with its source compiler module is required by the new UNO client; the Debian option installs a JDK.

1. Open **Project Desk → Problem sheet** and start Clock Lab, or reopen the I01 Clock Lab problem.
2. Open **Calculate** and select **Concurrent memory case**. The expression uses the saved quantities; its assumption states that the allocations are concurrent.
3. Click **Calculate and keep**. The checked comparison is false: 17 MiB exceeds 16 MiB in that declared case. The missing lifetime question remains visible. This is a conditional model result, not a verdict on every possible lifetime schedule.
4. Choose workspace for **What if**, from 0 to 10. The graph samples the same mathematical model. Its separately calculated exact linear boundary is 4 MiB. A sample graph does not prove arbitrary behavior between samples.
5. Select **Typical power estimate**, calculate, and obtain 1.25 W from 5 V and the declared 250 mA assumption. The maximum-current question remains open.
6. Click **Make checked Calc and Writer files**. A normal Kernel job opens a clean owned workbook, populates its cells, calls `XCalculatable.calculateAll`, reads actual formulas/values/errors, saves the workbook and reopens it. It creates the supported paragraph/table findings document, edits/saves it in native Writer, exports PDF and reopens the saved DOCX to check content.
7. The completed outputs are then copied into a new `Calculations/ACTION_ID` directory within the delegated working copy. This publication occurs after the job completes, preserving the existing source-change guard. **Open generated working files** opens that directory. Originals are never overwritten. An existing generated file with changed bytes is preserved and causes a conflict; a repeated publication of identical bytes is idempotent.

The saved calculation list retains old observations with their own problem revision and applicability. Save displayed problem edits before calculating. A changed source or problem makes an old action historical and prevents its execution against the new context. No calculation resolves the unknown lifetimes by inventing values.

## Mathematical profile

| Area | I02 behavior |
| --- | --- |
| Quantities | Existing time/frequency/voltage behavior retained; current, power and byte-based memory added. MB is 1,000,000 bytes; MiB is 1,048,576 bytes. Ambiguous KB is refused. |
| Compound dimensions | Products, quotients and bounded integer powers; V times A is power, and memory per time is distinct from memory. Incompatible addition/comparison/conversion is refused. |
| Exact values | Decimal or rational strings become Fractions in base units. The stored rational is exact. A nonterminating decimal display is marked approximate. Floats are never input facts. |
| Expressions | Ordered typed nodes for quantities, variables, addition, subtraction, multiplication, division, negation, bounded integer powers and relations. Up to 16 variables, 128 nodes, depth 24 and degree 4. |
| Domains | Real/integer scalar declarations, optional bounds and retained nonzero denominator conditions. Unsupported interval arithmetic is not silently treated as scalar arithmetic. |
| Human entry | A bounded arithmetic syntax is parsed into those nodes. Calls, attributes, indexing, comprehensions and executable statements are refused. No Python eval or backend string parser is used. |
| SymPy | Constructed objects, exact normalization and bounded linear equalities. Underdetermined/free-variable results remain unknown. The adapter does not expose arbitrary nonlinear solving. |
| Z3 | A declared real/integer linear fragment, including inequalities. Variable products and variable denominators are unsupported. A feasible assignment is one witness, not a universal guarantee. |
| Witness checks | Solver assignments are checked against the original IR, bounds and denominator conditions. They cannot change a supplied known input. |
| Bounds | Solvers run in fixed child adapters with CPU/address-space/output/wall limits. Timeout/resource failure is UNKNOWN, not mathematical infeasibility. This is not the general experiment runner of I03. |

Backend states distinguish FEASIBLE, INFEASIBLE, UNKNOWN, UNSUPPORTED and UNAVAILABLE. Invalid dimensions/domains are checked separately. A false comparison can be a successful computation of an infeasible declared case. Process completion, parse/check verdict and evidential applicability are separate fields.

## Shared records and authority

New operations: `math.status`, `math.units`, `math.validate`, `math.evaluate`, `math.solve`, `math.preview`, `math.prepare`, `math.run`, `math.get`, `math.list`, `math.sweep`, `math.office.prepare`, `math.office.run`, `math.office.result`, and `math.office.publish`.

Pure mathematical reads remain read operations. Preparing/running durable observations and publishing owned output copies require execute scope. The shared Project Desk store holds new math action/result kinds with immutable problem/context/model/source bindings and versioned history. No new database schema or second scheduler is introduced. The new `math.office` job uses Kernel ownership, stable request keys, logs, cancellation and process-group termination. Its job request adds one optional `calculation` field to `jobs.submit`; previous fields and required parameters remain unchanged.

Each mathematical action pins its typed model, operation/schema, implementation hashes, assumptions, selected problem/source revision and backend. Known problem quantities and explicitly declared scenario quantities remain distinguishable. A successful computation is labeled a consequence of that declared model; it grants no physical qualification or original-publication authority.

The legacy model PLAN profile is unchanged. These calculator/Office actions are explicit coordinator operations. I04 introduces adaptive model action selection. No live-model decision or increased model intelligence is claimed in I02.

The read-only staC extension uses the same evaluator:

```text
math problem:PROBLEM_ID | calculate "voltage * assumed_typical_current" | unit W
```

The expression is quoted data for the typed compiler. The caller's real principal is forwarded. Compiling or previewing this program creates no write grant.

## Maths in lines (0.8.5)

The same line takes three more steps: solve for a quantity, the range of an expression, and a check. Each is the read operation `math.answer` (workbench/math_answers.py over the pure core workbench/math_ranges.py), and its answer is one record, `ledger.math-answer/1`: the question as asked, the model, every input with its revision and where it came from, the result, the guarantee, the steps, and whether the sheet's sources are still as they were. The grammar, strict shell words, at most 40, the steps in this order:

```
math problem:ID | calculate "EXPR" [| unit U]
math problem:ID | solve "REL" for NAME [| within LO HI] [| step S] [| given NAME LO HI] (up to four) [| unit U]
math problem:ID | range "EXPR" [| given NAME LO HI] (up to four) [| unit U]
math problem:ID | check "REL" [| given NAME LO HI] (up to four)
```

ID is the problem sheet's ID. LO, HI and S are in that quantity's declared unit; a `given` on the quantity being solved for is refused, since that quantity is the one left free. A sheet's quantities carry no domain of their own, which is why `within` and `step` exist. A `given` range is typed by the owner; a line Kasandra proposes never carries one, and her ranges come only from the owner's tolerances (`tolerances.set`, which waits for Approve). Every maths answer, `calculate` included, says whether the sheet's sources changed since it was made, so a stale limit is never used silently. Everything is worked in exact fractions; numbers are shown to four figures, rounded outward for a range and toward the inside for an allowed end, with the exact value beside them. When a range can only be bounded soundly (a quantity used twice, or under an even power), the check says the margin is at least so much and that the range may be wider than the true one; it never says the ranges reach both sides when that is not known. The existing hashed maths files are unchanged; an answer carries the hashes of its own implementation.

### Three worked examples on Rail Demo

Rail Demo comes without a problem sheet, so first make one from its invented numbers: rail_voltage 12 V and settled_current 250 mA from its bench readings, settled_power_limit 4 W from its limits Rev B. Graphite gives the sheet an ID of 32 hex characters; `RAIL` below stands for it, so type the sheet's own ID in its place. tests_integrated/test_math_lines.py makes that sheet, runs these three lines and compares what the window shows (the lines under each one) with the words below, line for line. The receipt, one word away under each answer, lists the inputs with their revisions, the method and the guarantee.

Solve for the current under the limit, in whole mA:

```text
math problem:RAIL | solve "rail_voltage * settled_current <= settled_power_limit" for settled_current | within 0 1000 | step 1
Solve for settled_current
Up to 333 mA, at rail_voltage 12 V and settled_power_limit 4 W.
In whole steps of 1 mA: 0 to 333 mA.
The exact end is 333.3 mA (exact 1000/3 mA).
The declared 250 mA lies inside.
333 mA holds (3.996 W); 334 mA does not (4.008 W).
```

Then the owner sets a tolerance on rail_voltage, plus or minus 0.5 V: with the operation `tolerances.set` typed in the Terminal after a leading / (`/help tolerances.set` lists what it takes: the sheet, the quantity, `plus_minus`, `percent` or `between`, the amount and where the tolerance comes from), or by asking Kasandra, who always asks before she sets one. The window has no control of its own for it yet. The owner then asks for the range of the power over it:

```text
math problem:RAIL | range "rail_voltage * settled_current" | unit W
Range
rail_voltage * settled_current: 2.875 to 3.125 W, over rail_voltage 11.5 to 12.5 V and settled_current 250 mA.
```

And the check against the limit, over the same tolerance:

```text
math problem:RAIL | check "rail_voltage * settled_current <= settled_power_limit"
Holds
rail_voltage * settled_current <= settled_power_limit: it holds for every value in the ranges, with 0.875 to 1.125 W to spare.
```

## Office profile and precision

The unmodified, hash-pinned LibreOffice UNO Java API JAR 25.2.0 is included with its MPL license and upstream POM/source reference. A fixed Java client receives data fields, not model-generated Java. The running native LibreOffice and Java versions are recorded per action. Documents load in an isolated profile with source document macros disabled and external updates disabled. This is a new generated-cell/paragraph/table profile; legacy Office adapters retain their existing interfaces and document-loss reports.

Calc uses native floating point. Each measured formula and numeric value is checked against the exact IR with an absolute tolerance of at least 1e-10 or relative tolerance of 1e-12. Both calculated and reopened observations must agree, and actual cell errors must be zero. Formula identities are checked. Stored input values are not labeled recalculation evidence. The Writer DOCX and its table are reopened and checked; PDF is an actual native export. Originals and arbitrary unsupported workbook/document features are outside this clean generated profile.

The execution host supplied LibreOfficeDev 26.8.0.0.alpha0, commit `2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`, and OpenJDK 17. The tested JAR API version and native engine version are separate identities. The report records this limited compatibility evidence. The owner ThinkPad's installed build and visible session remain separately qualified; a successful development-host fixture does not establish them.

## Debugging and storage

An early full fixture wrote generated outputs during a worker job and correctly triggered the existing source-change guard. This was repaired by keeping native output under the job and publishing to the working copy only after completion. The guard was not weakened.

A separate early concurrent fixture reported a damaged Kernel database. Its exact corruption mechanism has not been established. The compressed synthetic failed database is retained under `tests_integrated/diagnostics` for diagnosis, never as a workspace/migration input. Kernel connection lifetimes now share a reentrant thread/process guard on Linux while retaining SQLite WAL, transactions and database format. Later checks include two concurrent writers, 250 concurrent reads, exact record counts, database quick_check, actual native-job cancellation and complete native round trips. This evidence supports the guarded candidate; it does not retrospectively prove the original failure mechanism or qualify the target host.

## Verify and recover

```text
python3 tools/check_release.py --self-test
python3 tools/check_release.py --self-test --native --ui
```

Use the installed runtime Python. The first command includes earlier six-stage/I01 checks, the connected mathematical case without Office, focused mathematical tests and the concurrency check. The second adds a real native Office round trip, native cancellation and real Qt calculator checks. Native checks may take over a minute. Missing optional dependencies prevent qualification rather than becoming a pass.

`I02_RESULT.json` and the pass discussion identify actual results and limits. `examples/clock_lab/I02_observed` contains actual synthetic Calc/DOCX/PDF outputs for inspection, outside the model-visible input manifest. Expected answers remain in the separate evaluator. The entire I01 package and all earlier features remain in this candidate. Keep the earlier ZIP and back up workspaces before opening them with a new program. There is no automatic database repair or silent retry of a cancelled native action. A new action uses new output identities; incomplete previous output is retained separately.

I03 adds protected general experiments, selected-board native checks and evidence/reason graphs. I04 closes the adaptive model feedback loop. I05 expands visible calculator/application sessions, reuse and takeover. I06 measures real-model unseen tasks and qualifies the Debian ThinkPad.

## Primary technical references

- SymPy parsing/evaluation boundary: https://docs.sympy.org/latest/modules/parsing.html
- SymPy exact objects and solvers: https://docs.sympy.org/latest/modules/core.html and https://docs.sympy.org/latest/modules/solvers/solveset.html
- Z3 arithmetic and its division semantics: https://microsoft.github.io/z3guide/docs/theories/Arithmetic/
- LibreOffice recalculation: https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1sheet_1_1XCalculatable.html
- LibreOffice document loading properties: https://api.libreoffice.org/docs/idl/ref/servicecom_1_1sun_1_1star_1_1document_1_1MediaDescriptor.html
- LibreOffice native command interface: https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html
