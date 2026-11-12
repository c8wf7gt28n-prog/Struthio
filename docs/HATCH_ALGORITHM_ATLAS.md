# Algorithm & Theory Atlas — ATLAS-02

Open **Tools → Algorithm & Theory Atlas**, or enter `/open algorithms`. Search a method name, purpose or assumption. The Method page gives its signature, domain, preconditions, guarantees, counterexample, cost, references and licence-review limits. Exact descriptor exposes the source bindings and canonical Kernel operation schemas.

**Try an example** is a scratch area. Choose a supplied example, optionally edit its JSON, and click **Check declared input**. This checks the finite profile; it does not save a problem, launch a solver or submit an engineering job. The Admission check page explains rejected inputs and outstanding obligations. Scratch edits are discarded when another example/method is selected; no master or working-copy file is changed.

## Initial corpus

| Profile | Existing implementation | Scope |
| --- | --- | --- |
| Exact dimensional arithmetic | `math.evaluate` | Supported typed scalar quantities and exact rational evaluation |
| Additive interval capacity | `math.schedule`, `methods.preview` | Constant additive capacity, half-open known intervals; learned methods retain their separate acceptance gate |
| Linear equalities | `math.solve`, fixed SYMPY backend | Local affine equality profile, exact witness recheck |
| Linear feasibility | `math.solve`, fixed Z3 backend | Local real/integer affine constraints, witness/infeasible/unknown |
| Rational normalization | `math.solve`, fixed SYMPY backend | Quantity expressions, no selected constraints, retained original denominator guards |
| Dependency impact | `reasons.impact` | Tracked dependencies in an owned saved reason DAG |
| Finite support/refutation paths | `reasons.evaluate` | Proposed finite graph, with receipt/current-source checks at execution |
| Linear optimization | Reference only | No objective or optimality adapter |
| Shortest path | Reference only | No qualified pathfinding adapter |
| Linear least squares | Reference only | No fitting adapter |
| Bracketed scalar root finding | Reference only | No numerical root adapter |
| Experimental design | Reference only | No automatic design generator |

The last five entries are explicitly **NOT_IMPLEMENTED**, even if a related library happens to be installed. The seven linked profiles reuse existing implementations; this pass does not implement five additional solvers or claim all twelve are executable.

## What a match means

`MATCH_DECLARED_PROFILE` means the supplied typed input satisfies the admission checks of that finite profile. `MATCH_WITH_OBLIGATIONS` means the input shape fits, with listed obligations still open. Neither is a successful solver result, a current-host qualification, a learned-method acceptance or an engineering conclusion.

`NEEDS_INPUT` retains unknown quantities/intervals or missing declarations. `REJECTED_INPUT` identifies a malformed or unsupported model, incompatible units, a zero denominator, a nonlinear form in the affine profile, an unsupported resource declaration, a missing graph node or a cycle. A problem owned by someone else or with a changed revision/context fails through the existing Kernel boundary; it is not relabeled as a mathematical counterexample.

Admission and implementation status are separate. For example, a linear equation may fit while pinned SymPy is unavailable. **LINKED** means the required direct source files, operation contracts and pinned optional packages are present. Every profile retains **NOT_CURRENT_HOST_QUALIFIED**. File/package presence and a matched example do not qualify an operation. Existing historical evidence is preserved, not silently promoted into the Atlas.

## Input forms

`algo.lookup` accepts optional query, task and expected_catalog_digest. `algo.get` accepts id and optional expected_catalog_digest. `algo.find_applicable` accepts context, optional algorithm and optional expected_catalog_digest. All three are registered read operations in the existing Engineering Kernel, also exposed by its CLI/MCP schemas and Slate discovery.

All contexts require task. Exact/equality/feasibility/normalization contexts accept a typed `arc.math-model/1` model. The existing mathematical validator enforces units, bounds, node order, supported operations and domain guards. Equality and feasibility admission reuse the existing affine checker. Unknown values remain unknown. Normalization preserves denominator obligations; cancellation cannot make an excluded point valid.

Resource contexts accept an owned saved problem binding (`id`, `expected_revision`, `expected_context_digest`), capacity variable, allocation/lifetime pairs and declarations using `checked_methods.DECLARATIONS`. Freshness and owner checks reuse `math_service.current` and `problems.check_bound`. The existing pure exact event sweep validates quantity dimensions, intervals and completeness. At most 32 allocations are admitted. The result does not certify the truth of owner declarations. Actual `math.schedule` persists its normal receipt and requires its existing scope; `methods.preview` still requires an accepted, currently qualified method version. Atlas admission bypasses neither route.

Graph contexts accept a supplied reason graph and, for impact, a node. Graph shape reuses `reason_graph.validate`. These are declared-input previews, not automatic saved graph creation or a check of the receipts mentioned by arbitrary JSON. Real receipt ownership, observation freshness and rule evaluation remain in `reasons.*` operations. A missing node or dependency is not evidence of no impact.

Unexpected fields from another profile are refused. Planned methods always return NOT_IMPLEMENTED; their reference assumptions are not advertised as validated input adapters. Context size is bounded at 128 KiB. Actual core/profile bounds remain narrower where applicable.

## Versions and authority

The corpus is `workbench/algorithm_corpus.json`, schema `ledger.algorithm-atlas/1`, version 1.0.0. Its finite code bindings are in `workbench/algorithm_atlas.py`; corpus text cannot add an executable module or a dispatch route. The catalog digest includes corpus content, direct implementation/validator sources, the guide and existing operation contracts. Passing an earlier digest rejects a changed catalog before selection. This covers declared direct sources, not every transitive dependency, imported model, operating-system package or hardware condition.

The corpus and its examples are authored engineering descriptions bound to code and references. They are not cryptographically authenticated theorems. Reference pages remain links, with concise offline descriptions; full upstream documents are not copied. External docs may describe newer or broader capabilities than the pinned local adapters. Executable scope is always the local code and contract, not the upstream library's marketing or API breadth. Dependency licences are retained under existing notices and not independently audited by this Atlas.

## staC

```
algorithms
algorithms | find "capacity"
algorithms | method interval_capacity
```

The finite embedded staC read extension forwards the existing caller principal. The upstream POSIX staC interpreter is unchanged. The general existing read pipeline can also use `algo.lookup {"query":"linear"}` and `algo.find_applicable` with typed arguments. Invocation/dispatch still comes from the same Engineering Kernel. No second execution engine, shell adapter, background scheduler or model profile is added.

## Focused validation and outstanding work

Development receipts in `docs/ATLAS_02` distinguish descriptor/admission examples, actual executions of existing mathematical implementations, UI interaction, registry preservation and package integrity. They do not qualify the owner's ThinkPad. Solver examples run only through the existing bounded pinned adapters when those dependencies are available. Screenshots use actual Qt offscreen rendering; they do not establish native display acceptance.

ATLAS-02 completes this bounded corpus/admission/browser implementation. It is additional H03 work, not completed H03. Typed Discovery IR, automatic valid method composition, operation-specific Tool Atlas probe promotion, full context menus and real native owner interaction remain open. HATCH acceptance remains 0/6. I05 actual-model/native acceptance and I06 owner-host qualification remain open while additive cloud development continues under the owner's current direction.
