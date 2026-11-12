# Work that continues while Ledger is closed (HATCH AGENT-02 · WI-A)

November 6, 2026 · UTC. The owner approved the next pass on 2026-11-05 ("Next pass approved") for the three items named at the end of AGENT-01; this is the first of them. Standing authorities: the Program Specification for Claude v1.0 and the Creative Implementation Commission v2.1 (no second dispatcher, shell runner, scheduler or data store; Master Stop is the one kill switch; never claim acceptance). Owner decision D19 holds: Slate acts freely inside an assignment and asks only for originals, network and outside effects.

## What the owner sees

An assignment Slate is working on no longer has to stop when Ledger closes. With the Ledger service running (Hatch ▸ Ledger services On; the desktop is attached to it) and the setting **Continue assignments while Ledger is closed** on (Settings ▸ Slate ▸ Assignments; on by default), closing Ledger hands the running assignment to the service, which keeps taking one step at a time. When Ledger opens again:

- Today's Waiting card says what happened: *While Ledger was closed, Slate took N steps on “…” · now done* (or *now running*, *now needs you*, *now paused*), with the word **inspect** (the investigation sheet) or **resume** when it waits or was paused; a paused one says why, as the AGENT-01 paused line does (*now paused (Master Stop)*, *now paused (The Ledger service stopped)*). The line stays for 24 hours after the assignment last changed.
- If the work is still running, the window takes it back about 1.5 s after it opens; from then on it steps at the window's own pace again. If a window that ended without handing the work over (a crash) left its 20-second lease behind, the reopened window looks again the moment that lease runs out and takes the work back itself (at most three such looks, so a second window that really is driving the work is left alone).
- While the service holds an assignment, the Work block's doing-now line begins *in the Ledger service ·*.

With the setting off, or with no Ledger service (the in-process desktop), closing pauses the assignment as in AGENT-01 (*Ledger closed*) and Today offers to resume it. Master Stop pauses every assignment, on both sides. When the service itself stops (Off, Reboot, shutdown), its own Master Stop on the way out pauses what it was carrying with the reason *The Ledger service stopped*; Today offers to resume those.

## How it works (no new scheduler, store or process)

The record is the AGENT-01 `agent_assignments` row with four added columns (an additive, idempotent `ALTER TABLE` in `agent_loop.ensure`): `driver` (`desktop`, `service`, or empty when released), `lease_until`, `service_steps` and `authority` (what the owner granted the work for the service's steps: the read and execute scopes, paths, tools and mode of the principal that assigned it, narrowed at hand-over to what the releasing principal holds). The step is the AGENT-01 `agent.step`, with an optional `driver` argument.

**The lease rule** (written in `workbench/agent_loop.py`'s docstring):

- A step by the desktop always proceeds and takes the lease (`driver` desktop, `lease_until` now + 20 s). The owner's desktop has priority, so reopening Ledger takes the work back.
- A step by the service proceeds only when no desktop lease is live; otherwise it is refused with `ASSIGNMENT_DRIVEN_BY_DESKTOP`.
- Every step renews the stepping driver's lease (`LEASE_SECONDS = 20`). A step the service takes adds one to `service_steps`, and its recorded inputs carry `{"driver": "service"}`, so the investigation sheet says who took each step.
- Nothing steps a PAUSED, WAITING or finished assignment, whichever driver asks.

**The hand-over.** `agent.release {id}` clears the driver and the lease (a READY assignment becomes RUNNING, because the owner asked for it to run; PAUSED, WAITING and finished ones are refused). The desktop's close (`qt_app.closeEvent`) calls it on every running assignment when the window is attached to the service (`ledger_bridge.kernel.is_host_client`) and the setting reads on (`ledger.settings.effective`); an assignment that cannot be handed over is paused instead.

**The service's side.** The resident service's existing 5 s loop already calls `Coordinator.tick_agenda`, which runs `continuing_work.pump` in its one daemon thread. That same thread now also calls `agent_loop.pump(kernel)`: one step each, as driver service, for every RUNNING assignment of any owner whose desktop lease is not live, at most eight per tick, with the owner's principal reduced to read and execute (never approve or candidate) and to the authority recorded on the assignment (`agent_loop.owner_principal`), kept inside the operator's ceiling by the same rule as the host's own delegation (`host_ipc.delegation`). So a command-line, MCP or JSONL caller that assigns and releases work never gains the desktop operator's paths through the service; the desktop owner keeps its own. (A record from before the column steps with the operator's paths only when its owner is the desktop owner, and with the Principal defaults for any other identity.) It does nothing when the setting is off, work is held (`work_trail.execution_held`) or the service is closing, and it checks all three again under the dispatch lock before every single step: Master Stop holds work before it takes that lock, so a batch already under way ends at the step in flight, and so does one under way when the owner turns the setting off or the service begins to shut down (`pump(kernel, guard=dispatch_lock, stop=closing.is_set)`). It holds the service's dispatch lock around each single step (so a desktop request never interleaves with one), and never raises: a step's own failure lands in that assignment's reason; anything unexpected becomes WAITING with *The Ledger service could not step it: …*. `Coordinator.master_stop` calls `agent_loop.pause_all` before it cancels jobs.

**The setting.** `agent.continue_when_closed` (boolean, default on, Slate ▸ Assignments, project private, owner only) is stored in the workspace's Kernel settings table (`ledger.agent.continue_when_closed`), where both consumers read it: the service on every tick (`agent_loop.continue_when_closed`; a row that is not a boolean reads as off) and the desktop at close (`agent_qt.continue_setting`). It is the 43rd setting; the 42 prior definitions are byte-identical (digest `c3126ee2…`); the single-key Set route is used, and the 17-key batch enum is unchanged.

## Operations, recorded

- **Added:** `agent.release {id}` (execute) → `{assignment, next}`; private to this computer for cloud proposals (`stacy_control.CLOUD_PRIVATE`); not a journal observer. Registry: 714 operations, 112 job tools.
- **Extended:** `agent.step` gained the optional `driver` (`desktop` | `service`, default `desktop`), a recorded extension of an AGENT-01 operation.
- **Status rows** (`agent.status`, `agent.list`) gained `driver`, `lease_live`, `lease_until` (when the live lease ends; empty when none is live) and `service_steps`.

## Decisions taken for the register

1. **The desktop has priority** (D19: the owner acts freely; the window the owner is looking at is the owner's own hand). A desktop step is never refused for a service lease; the service yields to a live desktop lease, and a reopened, attached window adopts running work.
2. **A 20-second lease**, renewed by every step: four service ticks or eighty desktop ticks. Long enough that the service never steps between two desktop ticks, short enough that work left by a crashed window resumes in the service within half a minute.
3. **Default on.** The owner asked for work that continues; the setting is the one switch to keep the AGENT-01 behaviour (pause on close).
4. **Service shutdown pauses with its own words** (*The Ledger service stopped*), not *Master Stop*, because Off and Reboot are not the kill switch; both run the same Master Stop path.
5. **Master Stop on the desktop is unchanged** (`qt_master_stop` keeps `driver.pause_all('Master Stop')`); the attached desktop then asks the service's Master Stop, which pauses everything else, READY assignments and other owners' included.
6. **The service acts with no more than the owner granted** (Commission v2.1: no new execution authority). The authority is recorded on the assignment when it is assigned and narrowed when it is handed over, rather than rebuilt from the identity, because the identity alone cannot tell the desktop operator from a command-line caller with the same name.

## Evidence

- `tests_integrated/test_agent_loop.py` (24 tests): the lease both ways, release, the pump to DONE on a numbers assignment with the setting on, nothing with it off or held, the pump's own failure words, `pause_all` across owners, the new status fields, an AGENT-01 table gaining the columns once; and from the independent review: the service steps with no more authority than the owner granted (a non-operator caller's assignment keeps the Principal default paths; release by a narrower principal narrows; the ceiling and read+execute bound whatever is recorded), the hold, the setting and the closing flag end a batch at the step in flight, a reopened window takes back work a crashed window's lease held once that lease runs out, and Today's line says why a paused assignment paused.
- `tools/check_continue_ui.py` (offscreen Qt, launchers held; `is_host_client` patched True on the window's Kernel for the close and for the adopt call only; the pump run in-process): 11 checks, captures at 1920×1200 and 1366×768, report `build/agent02_ui/continue/continue-ui.json`.
- `tools/check_continue_service.py` (no Qt; a real run of the resident process, started exactly as `host_client.ensure` starts it, in a disposable profile): the assignment released through the client reaches DONE from the service's own ticks with no desktop (about 25 s), the sheet's steps say driver service, a second one is paused *The Ledger service stopped* when the service shuts down, and the process ends with exit code 0. Report `build/agent02_ui/continue/continue-service.json`. The only process it starts is the service.

## What remains open

The owner-host run under the systemd user unit, the owner's display, and a live model are not exercised here; the service steps the explicit procedure only, and a pending model choice is polled by the service exactly as by the desktop. Today's non-resume rows are drawn by `TodayPage.fill` as a flat button that does not wrap, so at 1366×768 the long *While Ledger was closed* line is cut at the card's edge; a one-line change there (drawing it as a sentence with the word inspect, as resume rows already are) is proposed to the integrator. Nothing here claims acceptance.
