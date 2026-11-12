# Tool Atlas — first implementation

Open **Tool Atlas** from the Ledger navigator, or use `/open atlas` in the Slate command entry. Search for Calc, Python, KiCad, ngspice, a tool ID or an operation ID. Press Enter or Find. Use Operations / Job tools and Previous / Next to narrow the results.

The Passport tab explains prerequisites, required permission, source, licence status and known limits. Exact contract shows the registered argument schema and passive bindings. Selecting an entry never runs that tool.

Save passport snapshot records a private observation in the existing workspace database. Choose a saved passport and Check saved passport to compare its binding with the current adapter, contract, declared runtime and host session. A changed binding is STALE. Historical snapshots are retained. This pass does not add a database migration or rewrite existing records.

## Meaning of the status

All operation qualification states in this first implementation are **UNTESTED**. The existing catalogue's installed, available and permitted dimensions remain separate. A source file or installed executable does not prove operation success. An unchanged passport proves only that the bindings checked here match, not that the entire dependency environment is unchanged.

The snapshot covers the direct adapter source, exact argument contract, registered job target, declared passive runtime information, selected executable bytes when a command is declared, and platform/boot session. It does not cover all transitive Python imports, shared libraries, launcher dependencies, model weights, grant state, user arguments or engineering inputs. Systems without a boot-session identifier have a weaker platform-only host binding, explicitly recorded as a null session digest and HOST_BINDING_UNAVAILABLE when the other bindings match. Rebooting a Linux host invalidates its session binding conservatively. Job-level fixture/evidence adapters and their qualification promotion are future work.

## One registry and one execution authority

The Atlas adapts `engineering_kernel.CAPABILITIES`, `TOOLS`, `engineering_cli.schemas()` and `capability_catalog.catalogue()`. There is no duplicate dispatcher, independently editable operation schema or shell runner. Existing IDs remain unchanged. Search vocabulary is presentation metadata only. The six new Atlas commands are registered through the same Kernel and available to CLI/MCP/Slate command discovery.

`atlas.lookup` accepts query, kind (OPERATION / JOB_TOOL), limit (1–100) and offset. Search matches all words against IDs, required scope and the small explicit vocabulary.

`atlas.operation_schema` accepts name and optional kind; OPERATION is the default. It returns the exact operation contract or the job's existing `jobs.submit` route and registered adapter target. Job-specific options remain validated by the existing worker; no complete job-options schema is invented here.

`atlas.invocation` accepts operation and arguments. It validates argument shape using the existing contract and returns a structured call with `SCHEMA_CHECKED_NOT_DISPATCHED` and `runtime_authorization: false`. It does not check every argument-dependent permission/precondition, emit a shell command, or execute the proposed call. Required Kernel scope is not a complete effect model.

`atlas.passport.save` requires execute scope because it writes a new private Desk record. `atlas.passport.get` and `atlas.passports.list` require read scope and retain owner isolation. Listing returns historical summaries; opening rechecks freshness. The desktop picker shows the newest 100 snapshots; the Kernel list supports offset pagination for older records.

## staC read forms

```
atlas
atlas | find "KiCad"
atlas | operation math.preview
atlas | tool cad.drc
```

These are finite extensions to the existing embedded staC bridge. They produce typed read IR and forward the existing caller principal to the Kernel. No shell, extra execution stage, scope elevation or arbitrary generated program is accepted. The upstream POSIX staC interpreter is unchanged.

The general read pipeline also accepts registered calls such as `atlas.lookup {"query":"Python"}` through its existing `language.run` route. The chain-menu root has a Tool Atlas navigation link; object-specific compatible-operation filtering is not implemented in this pass.

## Scope and campaign status

This is **ATLAS-01**, an additive H03 foundation implemented while the owner's ThinkPad is unavailable. It is not completed H03 or a HATCH release. H01/H02 hardware/model qualification, Algorithm & Theory Atlas, checked probe promotion, typed compatibility matching, object-specific pipe menus, full native ownership and the release gates remain open. I05 actual-model/native acceptance and I06 owner-host acceptance are unchanged.

The new code is checked with focused boundary tests and an actual Qt offscreen UI capture. Offscreen UI capture does not establish a usable native Debian desktop. No model generations, native probe jobs or owner hardware acceptance are performed here.

To stop using the view, close its tab and continue through existing workspaces. Saved passport records remain inert, owner-private Desk history. For rollback, retain a backup of the current workspace database alongside the previous program checkpoint; do not delete the database or discard newer records.
