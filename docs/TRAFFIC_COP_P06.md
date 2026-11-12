# Graphite P06 · the shared-memory traffic cop

Graphite 0.2a3 adds resource admission to the existing Kernel worker entry point.
The durable jobs, queue, authority checks, evidence and cancellation remain the
same. There is no separate scheduler daemon, model service or database.

## The useful change

A submitted job first waits in Queued for memory and an available lane. The
existing worker owns that wait with its PID/start token. The tool and its
execution deadline start only after admission. Waiting reasons appear in the
System work list and Work trail. Owner cancellation and Master Stop still stop
queued work, without running it. A live waiting worker is no longer mistaken
for an interrupted request after sixty seconds.

At most four native Kernel jobs run at once. Up to sixteen running/waiting
requests can be retained. Automatic nonforeground submissions stop at fourteen,
keeping two places for foreground requests. The existing same-source and
authority restrictions still apply.

| Lane | Rule |
| --- | --- |
| Model turn / handover | One admitted inference job at a time, including activation and qualification. |
| CPU calculation | One by default, configurable to three, alongside inference. |
| I/O | Small indexing, intake and reference jobs share the bounded native capacity. |
| Coordinator | One clip coordinator at a time, leaving native capacity and the calculation lane for its children. |

The owner gets the next available turn; an active tool finishes at its supported
boundary. This is not GPU-kernel preemption or a promise to interrupt a native
edit halfway through. Stop remains the explicit cancellation control.

## Foreground and background

Manual submissions are foreground work. Service-driven agent steps submit
background work. Agenda Now / Normal / Background tiers become the matching
admission priorities. A higher-priority request goes first within its lane,
then creation order breaks ties.

The existing desktop input observer publishes a short, expiring foreground
lease asynchronously. It retains no keys, typed text or pointer positions.
While the owner interacts, new normal/background jobs wait and service-driven
assignments yield before their next step. Their investigation records, cursor,
findings and pending model choice stay in place. When the activity lease expires
or memory becomes available, their normal driver can continue.

The System list offers Foreground / Normal / Background on a queued job's
title by right click. The owner-only `jobs.priority` operation changes its next
admission; the CPU niceness slider remains a separate control. Agenda dragging
continues to change Agenda order. Active jobs are not falsely presented as
reorderable or instantaneously preemptible.

New background job processes default to CPU nice 10 unless an explicit job
request already exists. Cooperative numerical libraries receive a thread hint
of two, clamped to leave a logical CPU where possible. Existing llama.cpp
thread preferences remain explicit launch settings. OS nice changes may be
refused, and restoring a higher OS priority is not promised. These mechanisms
are not CPU-time or memory-bandwidth quotas.

## One memory pool

Admission observes current host available RAM, including other applications and
the existing container ceiling. It preserves a foreground reserve and accounts
for owned jobs and the resident model. It never adds DRM, GTT or Vulkan budgets
to system RAM.

Available RAM already excludes resident memory. For each live commitment the
controller reserves only `max(0, budget - observed process-tree RSS)` as future
growth. A 32 GiB model budget with 8 GiB observed RSS therefore contributes
24 GiB of future commitment. It does not subtract the resident 8 GiB again.
Model weights, KV space and temporary allocations stay inside the existing
model budget; ordinary tools use declared supported budgets where available,
or a conservative labelled estimate.

The resident model is not also counted as a second model reservation while its
own activation job is running. A completed activation leaves the model's
reservation attached to its independently owned live worker. Proven-exited
worker trees no longer occupy admission lanes; unknown ownership stays
conservative. Recovery does not replay a lost operation automatically.

Sequential model replacement can credit only observed private pages of the
owned old model for preflight. Its unused future reservation ends at handover.
The actual launch rechecks measured headroom after the old worker stops. Driver
allocations that cannot be proved reclaimable receive no advance credit.

These are **advisory commitments**, not a new global OS cap. RSS can include
shared pages, some GPU allocations are not visible in process RSS, and library
thread hints do not control all native software. Estimates and observation
limits stay labelled. Other workspaces' future reservations are not globally
brokered; their actual resident use appears in host availability. Existing
protected-worker cgroup caps remain authoritative and their CPU-only device
boundary is unchanged.

## Pressure and continued ownership

New work waits when there is no headroom. A model launch rechecks memory before
starting and before a fallback attempt. A changed headroom condition stops that
load without a CPU allocation retry.

Both Linux CPU and Vulkan model workers now have a supervising parent that
watches resident memory and host/cgroup headroom. CPU also retains its
address-space cap; Vulkan avoids that cap because driver mappings need a large
virtual range. The native child dies when its supervisor disappears. Owned Stop
still revalidates PID/start tokens and terminates the owned tree.

A guard stop is reported as preserving shared host memory. The saved model
selection, dialogue input and investigation remain; the owner explicitly
reloads when there is headroom. Guard failure does not automatically reload the
previous model into the same pressure. No unrelated application is killed.
Sampling is not a hard GPU-allocation guarantee; a kernel OOM can precede a
sample.

## Controls and readback

Settings / Shared resources contains three real owner-controlled values:

- Foreground RAM reserve: 2,048 MiB by default, clamped to a quarter of measured
  host RAM on smaller machines.
- Concurrent CPU calculations: one by default.
- Background library threads: two by default.

The next admission reads the current values. Existing workers keep their
recorded resource limits. Work trail shows current available RAM, reserve,
future commitments, admission headroom, lanes and the caller's waiting jobs.
Technical detail explains the observation and preemption limits.

## Qualification and the next pass

Focused mechanical observations exercise the changed memory arithmetic,
priority, cancellation and ownership boundaries. A real queued worker was held
before tool launch and cancelled. A small real CPU child exercised its resource
trampoline. A short native Qt walkthrough covers the new readback and controls.
No model weights, model generations, benchmark sweep or broad test suite are
needed for this software pass.

ThinkPad memory bandwidth, thermal behaviour, Radeon inference and sustained
responsiveness remain owner-host qualifications. This release makes no tokens
per second or maximum-model-size claim.

P07 builds intelligent data arrangement: useful exact calculations, source
selection and prepared evidence for the model. P08 handles context/cache
lifecycle. P06 provides their admission and foreground handoff boundaries.

## Short-horizon admission forecast

Graphite 0.2a11 applies the forecast to background jobs that pass the current
admission checks. It uses net headroom after the foreground reserve and existing
commitments. At most once a second, an exponentially weighted average updates
the estimated rate of loss with a two-second half-life. The projected headroom
four seconds ahead is current headroom less four seconds of positive estimated
loss. When that projection falls below the requested bytes, the worker waits.
The forecast can hold a job for eight seconds. The current admission checks
still decide whether it can start after that wait. Missing or stale samples let
the current checks decide immediately.

Run `python3 tools/traffic_forecast.py replay` for a synthetic scenario using
the production forecast. Run `python3 tools/traffic_forecast.py capture --help`
to record bounded, read-only samples on a running installation. Replay compares
new arrivals against future sampled headroom. A recording gives observations
from one run. Controlled runs are needed to measure the effect of changing
when work starts.

## Measure the cost of CPU and Radeon overlap

Market execution models charge for the congestion a trade creates. Apply that
idea to one small background CPU batch while the Radeon is idle, processing a
prompt, or generating a reply. Compare repeated runs with and without the batch.
Track time to first content, streaming gaps, input-to-paint delay, and useful
background work completed. The [Almgren–Chriss execution paper](https://doi.org/10.21314/JOR.2001.041)
gives the execution-cost analogy.

Use short-window Linux pressure-stall deltas to flag reclaim or swap trouble.
Measure foreground latency to assess CPU and Radeon overlap. Judge tail latency
and background progress, including the longest queue wait. The
[NIST EWMA handbook](https://www.itl.nist.gov/div898/handbook/mpc/section2/mpc2211.htm)
and [Linux PSI documentation](https://docs.kernel.org/accounting/psi.html)
describe the statistical and stall measurements.
