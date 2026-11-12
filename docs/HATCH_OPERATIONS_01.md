# HATCH OPERATIONS-01

November 2, 2026 (America/Phoenix). Full checkpoint over EXPLORE-01. This connects the right-column observations and existing operation controls while preserving their original authority.

## The operations column

The right column now has Operations, Context and Slate faces. The original CPU/GPU/RAM/TXT monitor widget has moved from the header into a fixed strip above them. It stays visible while those faces change. The header has room for all eight menu words at 1366 by 768, and the original Master Stop button is visible at the upper right. Its existing QAction, shortcut, confirmation and owned-process controller remain in place. Nice remains available through its original popup route.

Operations contains local-model and admission status, an explicit cabinet-selection card, active jobs, the ordered Agenda, visible waiting reasons, accessible Earlier/Later controls and the existing priority controls. Its body scrolls at compact sizes. The existing Slate AI admission switch is retained behind AI admission, with its original store and behavior. It is no longer a permanent header toggle. The original Agenda and Work trail remain reachable.

The current cabinet selection is a named anchor, including while a file editor is active; it does not assert that the file belongs to that record. Context follows an active Cabinet/Explore record through a checked read of its original identity. It presents that record rather than an earlier Object Glass file. Returning to other workspaces retains the original inspector and Object Glass state and routes. Selection reads do not recheck source or master freshness.

## Shared read model

`ledger.operations` is the one new read operation. It composes the existing Agenda, work-admission and local Brain stores with a caller-checked cabinet selection and source-labelled host observations. Its compact queue records omit private program bodies and output snapshots. It is included in the existing cloud-private boundary.

The Agenda's existing view may reconcile due/missed scheduling metadata and initialize its component stores. The new projection preserves those established read semantics. It never starts a runner, submits a tool job, activates a model, changes priority or creates a grant. The supplied idle flag is observation context for queue checks; the actual runner rechecks its own environment at execution.

The Agenda's Kernel-job projection now reuses the canonical record-access filter, so another owner's private jobs are not disclosed through the right column or legacy Agenda/Nice views. Existing shared engineering records keep their original visibility policy. A dependency lookup also checks the item's owner, preventing a malformed cross-owner dependency from releasing an item based on another owner's record.

## Three distinct controls

Agenda position remains the persistent queue order. Dragging and Earlier/Later use the original `agenda.reorder` operation; crossing a scheduling tier adopts the destination tier, as the existing implementation specifies. The Agenda tier slider chooses now, normal or background. Background/idle requirements, dependency completion, future due time, pause, another running Agenda item, work holds, service admission and applicable AI admission are shown separately.

The first item passing those queue checks is named above the list. This is preliminary scheduling state; runtime, model, source and continuing-work grant checks remain authoritative. A blocked row stays in the owner's order with its reason even if another row passes the checks first. An ordered list is not permission to run an item.

Kernel job CPU nice uses the original `jobs.nice` operation and its 0–19 range. A queued value is labelled requested and applies at the next worker start. A verified running-process readback is labelled as an observation; an unverifiable, unsupported or unavailable process reports no live value and has no enabled adjustment control. Read-only/Tutor callers cannot be advertised as eligible to adjust priority. An OS refusal retains the actual readback and displays the refusal. A queued record with an old PID still shows its next-start request without measuring or modifying that old process.

CPU niceness controls CPU competition for tracked owned processes and verified descendants. It does not claim GPU, memory or I/O scheduling effects. The global Background CPU preference retains its existing owner-operated controller and next-use limitations.

## Observations

`host_observations.py` supplies bounded, Qt-independent readings of the current Ledger host. CPU utilization requires two valid increasing aggregate `/proc/stat` samples. Missing, reset or inconsistent samples clear the percentage. RAM uses MemTotal and MemAvailable from `/proc/meminfo`; invalid or unavailable readings remain unavailable. GPU uses the busiest reported value among the bounded DRM samples and reports missing driver access honestly.

TXT remains unavailable because this runtime does not supply trusted live context occupancy. A declared context capacity, completion count or file length is not substituted. Each model response carries a sample time and identifies the current Ledger host rather than claiming acceptance on the owner's ThinkPad. These fields measure observations, not settings or engineering qualification.

## Verification

Evidence is under `docs/OPERATIONS_01`: 13 operation/observation boundary checks, 13 Explore regressions, 15 actual Qt offscreen checks and three affected screenshots. Boundary checks cover missing/reset counters, TXT semantics, private job/context filtering, dependency and idle checks, cross-owner dependencies, paused/held/service-off work, reordered tier adoption, queued CPU requests, verified-process rejection, OS refusal and read-only/cloud restrictions. OS priority behavior is tested using controlled readback/refusal mocks; no live OS priority is changed.

The Qt fixture contains three Agenda items and two clearly documented job-state fixture records. It starts no worker. It exercises the real shared commands through keyboard sliders and Earlier, confirms dependency waits after reordering, preserves source bytes and an edited document, switches all three faces, verifies original Stop references without invoking Stop, renders compact layout, preserves poem and closes without a leftover desktop lease. Host CPU/GPU/RAM observations in screenshots are from the cloud session, not the ThinkPad. No provider request, model generation, engineering tool invocation or tool job is run. The full historical suite was not rerun.

All 684 prior operation schemas and scopes and all 112 job tools remain unchanged. The new read operation brings the registry to 685, and Explore's combined view to 824 entries. The 15 workspace adapters, 12 authored method profiles and 26 settings remain. The five Discovery protocol-bound source files are unchanged, and all earlier code and evidence are preserved.

## Next

The main cabinet, Explore/menu and operations surfaces now form a connected first layout suitable for a cohesive UI review. Remaining interaction work includes broader contextual command eligibility/ranking, complete settings and memory adapters, final naming/launcher consolidation, the session-exit footer and shared native application handoff. Actual pointer-drag, live OS scheduling/owned STOP, native GUI and exact-model acceptance still need their proper host cases; these offscreen checks do not close them.

HATCH remains 0/6 fully accepted milestones; integrated acceptance remains 4/6 in the retained evidence. I05 model/native and I06 owner-host gates remain open. Continue with a bounded contextual-action slice and consolidate the UI review, while preserving the existing grants, worker ownership and original-file protections.
