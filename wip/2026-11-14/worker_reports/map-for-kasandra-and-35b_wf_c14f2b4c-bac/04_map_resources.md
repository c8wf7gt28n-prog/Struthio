Graphite resource simulation: map of the memory, model and job paths (HEAD 13ddfc5, read-only)

Everything below comes from reading the code. I ran no tests and started nothing, so I could not reproduce the "four failures and one error" model-settings baseline. I don't have the real qwen35moe GGUF, so its metadata and tensor types are assumptions, marked where they matter.

## 1. Where each decision is made, and the seam to inject it

**Host readings: one seam covers almost every path.** `workbench/brain_runtime.py:10` `host(profile=True)`:
- Available RAM is read from `/proc/meminfo` MemAvailable (25-27). It is clamped by `/sys/fs/cgroup/memory.max` at the cgroup root only (31-34).
- With `profile=True` it also returns `hardware_profile = inference_hardware.snapshot()` (41-42). That snapshot is cached for 60 s and runs dpkg-query.
- **Seam:** `patch('workbench.brain_runtime.host', side_effect=fake)`. The fake must accept `profile=`. These callers all look the attribute up at call time, so the one patch reaches them:
  - `local_brain.configuration` (194)
  - `resource_control.claim` (208)
  - `model_room` (243-244)
  - `background_reason` (251)
  - `snapshot` (261)
  - `observation` (278)
  - `work_trail.resources` (288)
- For AUTO the fake must include a `hardware_profile` dict. `configuration:219` calls `.get` on it, so `hardware_profile: None` crashes.
- Watch-out: the worker guard `brain_worker.memory_sample` (brain_worker.py:11-27) reads the process's own cgroup through `/proc/self/cgroup`, but `host()` reads only the root path. In a systemd scope with MemoryMax, admission does not see the limit and the guard does.

**Resource policy, `workbench/resource_control.py`:**
- `KEYS` (14): `reserve_mb=2048`, `compute_slots=1`, `background_threads=2`. They are stored as settings rows `ledger.operations.<key>` (`policy` 34-42).
- `reserve_bytes = min(reserve_mb*MiB, max(128MiB, total//4))` (40). If `total_ram_bytes` is None, the reserve falls to **128 MiB**.
- `request(job)` (58-81) sets priority, lane, budget and basis:
  - `brain.activate`/`brain.qualify` go to lane `inference`, budget = frozen `memory_mb`, `model_handover=True`.
  - Other brain tools get 128 MiB.
  - `brain.inspect`, `intake.`, `knowledge.`, `network.` and `references.` go to lane `io`, 256 MiB.
  - Anything else is `compute`, 512 MiB.
  - A declared `study|lab|office|investigation` `memory_mb`/`max_rss_mb` of 64-262144 raises the budget.
  - Priority comes from the `_priority` contextvar, which **defaults to `'foreground'`**. Only `agent_loop.step_once` (agent_loop.py:420, service → background) and `agenda.run_next` (agenda.py:285-288) set it. `jobs.priority` (job_priority.py:79-91) changes a queued job's priority.
  - **Seam:** write `resource_request` straight into a job row; `decision` prefers it (150).
- `_view` (114-146) builds the commitments:
  - Running jobs other than the one being admitted, still owned (`worker_start` None counts as owned, 120).
  - Resident `brain.worker`/`brain.trial_worker`, deduplicated by (pid, start) (133-136). A worker whose job is a running handover is skipped (137). The `brain.worker` row is skipped on a handover (138).
  - `future = Σ max(0, budget − rss)` (142).
  - `headroom = available − reserve − future` (146).
  - So the reserve and outstanding commitments are each counted once. MemAvailable already includes resident RSS, so only unmaterialized budget is subtracted.
- `decision` (149-168). The first matching reason wins:
  1. 'Host memory could not be measured'
  2. 'Foreground interaction has the next turn' (non-foreground jobs while the lease is live)
  3. 'Four native job slots are occupied'
  4. 'Another model turn or handover is in progress'
  5. 'CPU calculation slots are occupied'
  6. coordinator busy
  7. 'An earlier eligible request has the next <lane> turn' (rank = priority, created, id)
  8. 'Waiting for shared-memory headroom' (`requested > headroom + reclaimable credit`, strictly greater, 164)
- Handover jobs get credit = `reclaimable()` (162), the private bytes of the current `brain.worker`.
- **Seams:**
  - `patch('workbench.resource_control.process_memory')` (pid → rss and private bytes)
  - `patch('workbench.resource_control.process_identity')`
  - `patch('workbench.local_brain.worker_live')`
- Foreground lease: `touch` (45-50) writes settings row `resources.foreground={owner, until: now+8}`. `foreground()` (53-55) is true only when `0 < until − now <= 10`. Seam: write the row directly, or patch the module's `time`. Every foreground `jobs.submit` touches the lease (engineering_kernel.py:1325), and so does the GUI (agenda_qt.py:254).
- Forecast: `_forecast_admission` (171-189) uses the pure `memory_forecast.evaluate` (memory_forecast.py:44-62; horizon 4 s, maximum defer 8 s). It defers **background, non-handover** jobs only. The sample is stored in `resources.memory_forecast`.
- `claim(kernel, ident)` (203-239):
  - Loops forever with `time.sleep(.4)`.
  - Cancels the job ('Owner work hold prevented execution') on cancel, work hold, services off, or `SLATE_OFF` (217-224).
  - Saves `resource_wait` (236-238). On admission it sets `Running` plus `resource_admission`.
  - Calls `job_priority.apply_worker` (234), which **renices `os.getpid()`**: patch it in-process.
  - Claim has no deadline: the job deadline starts only after claim.
  - **Time seam:** `patch.object(resource_control, 'time', FakeClock)`. Its `sleep()` can raise a sentinel so the runner can read the wait reason.
- `model_room` (242-247) re-checks headroom at launch, with no credit. Failure raises `GRAPHITE_HOST_MEMORY_LIMIT: …`.
- `background_reason` (250-257) is the agent-loop service hold. `snapshot` (260-271) and `observation` (274-314) are readbacks.

**Model preflight, `sdk/cli/arc1cli/gguf_inspect.py`:**
- `TYPES` (11-14): F32, F16, Q4_0/1, Q5_0/1, Q8_0/1, Q2_K…Q8_K, BF16. Any other type is labelled `UNSUPPORTED_TYPE_<n>` (80).
- **`ARCHITECTURES` (15) does not include `qwen35moe`.** It has `qwen35` and `qwen3moe`. The profile is computed at inspection (104) and **stored in the model record**, so you must re-run `brain.model.add` after changing the list.
- `inspect` (49-107) raises on bad input: wrong suffix or linked file ('Select a regular local .gguf file…'), `GGUF_MAGIC_INVALID`, `GGUF_VERSION_UNSUPPORTED`, `GGUF_TENSOR_DATA_TRUNCATED`, `GGUF_TENSOR_OFFSET_INVALID`.
- `identity` (109-120) is a full-file SHA-256. `inspect_set` (122-166) sets `id = sha256(role + files[name, bytes, sha256])` (161-162) and copies `message_template` from `tokenizer.chat_template`.

**`workbench/local_brain.py`:**
- `add` (132-151) runs as job `brain.inspect`.
- `configuration(value, options, root, reclaimable_bytes)` (193-226) checks in this order:
  1. role chat (195)
  2. `MODEL_ARCHITECTURE_NOT_IN_SUPPORTED_PROFILE` (196)
  3. `MODEL_CHAT_TEMPLATE_MISSING` (197)
  4. `MODEL_QUANTIZATION_NOT_IN_INSPECTION_PROFILE` (198)
  5. `CONTEXT_EXCEEDS_MODEL_DECLARATION` (199-200)
  6. `MODEL_MEMORY_ESTIMATE_UNAVAILABLE` (203) if `block_count`, `embedding_length`, `head_count` or `head_count_kv` is not an int. A per-layer array would trip this; check the real file.
- The memory part of `configuration`:
  ```
  kv_bytes=4*layers*context*embedding*kv_heads//heads
  estimate=int(value['total_bytes']*1.3+kv_bytes+384*1024*1024)
  available=min(total or available, available+reclaimable)          # 206-208; falsy → HOST_MEMORY_COULD_NOT_BE_MEASURED
  memory_mb=options.get('memory_mb',min(32768,max(1024,int(available*.65/1024/1024))))   # Auto cap, 209
  if memory_mb*MiB>available*.8: MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM                # 210
  if estimate>memory_mb*MiB: MODEL_MEMORY_BUDGET_TOO_SMALL                               # 211
  ```
- Backend (212-222): `gpu_layers==0` gives CPU. `AUTO` gives VULKAN only if `inference_hardware.radeon_available` (vendor `0x1002`, driver `amdgpu`, `accessible`; inference_hardware.py:97-99) **and** `brain_runtime.status(root,'VULKAN')['state']=='PINNED_VULKAN_AVAILABLE'`. Otherwise it records the fallback_reason 'Auto selected CPU…'.
- `configuration` runs **at submit** (`Kernel.submit` engineering_kernel.py:1319-1321 → `model_settings.freeze_launch` :29-38; saved `memory_mb` 0 means Auto, line 32) and **again at run** (`run_model_job` 450). The `memory_mb` frozen at submit becomes the admission budget (`request` 64-65).
- `start_server` (306-330):
  - `check_job` (epoch or cancel), then `recheck` (hash; 165-172), then `model_room`.
  - For VULKAN: `brain_runtime.probe` (154-167; `parse_devices` 140-151 flags llvmpipe/lavapipe/swiftshader as software). If not AVAILABLE, it falls back to CPU or raises `VULKAN_UNAVAILABLE` (317-320).
  - Wraps `_start_server` and retries **once on CPU** unless the backend is not VULKAN, fallback is off, the job is cancelled, or the reason contains `MODEL_OPERATION_CANCELLED`/`MODEL_FILE_CHANGED`/`GRAPHITE_HOST_MEMORY_LIMIT` (325-330).
- `_start_server` (332-409):
  - `model_room`, then `brain_runtime.prepare`, then argv (342-350: `--memory-mb`, `--reserve-mb`, `-ngl auto|N|0`, `--fit`, `--device`).
  - `file_stamps` check gives `MODEL_FILE_CHANGED_BEFORE_LOAD` (356), then `subprocess.Popen` (360) with stdout to `runtime.log`.
  - Health loop of **90 s** on `time.monotonic` (371-382). The process exiting gives `GRAPHITE_HOST_MEMORY_LIMIT` if the log has the marker, else `MODEL_WORKER_EXITED_DURING_LOAD`. Timeout gives `MODEL_LOAD_TIMEOUT`.
  - `/props` `n_ctx` sets `context=min(requested, reported)` and `context_basis='WORKER_REPORTED_LIMIT'` (383-389).
  - VULKAN requires the log line `offloaded N/M layers to GPU` with N>0, else `VULKAN_GPU_OFFLOAD_NOT_OBSERVED` (391-397).
- `run_model_job` (446-518):
  - `control_claim`, `checkpoint`, refuses while a reply job is active, terminates the old worker, `start_server`, then the "Reply with the word ready." probe.
  - If that probe fails on VULKAN: terminate, `recheck`, one CPU `_start_server` (462-476).
  - **Empty text gives `MODEL_PROBE_RETURNED_NO_TEXT` (477) with no CPU retry.**
  - Commits selection/worker 'READY' (483-490).
  - The `finally` block restores the previous model if `allow_recovery` (false after `GRAPHITE_HOST_MEMORY_LIMIT`), the old worker was live, the current one is not, and the job was not stopped or cancelled (497-518). The restore probe's text is **not** checked (508).
- Stop: `terminate` (256-269), `stop` (271-280, `stop_epoch+1`), `check_job` (284-288), `cancel_job` (943-947), op `brain.stop` (977-983). `status()` (106-130) reports `resource_stop` from the log marker.

**Other pieces:**
- `brain_worker.supervise` (41-61): kills the child and **exits 75**, printing `GRAPHITE_HOST_MEMORY_LIMIT`, when `rss > memory_mb` or `available < reserve`. Seam: `patch('workbench.brain_worker.memory_sample')`. It must run in the main thread (signal handlers).
- Job queue, `engineering_kernel.py`:
  - `submit` (1165-1332): services gate 1166; brain checks 1218-1228; 16-job cap and 2 places held for foreground (1283-1289); `brain_epoch` (1323); `resource_request` (1324).
  - `launch` (1334) spawns a worker. Patch `Kernel.launch`.
  - `run_job` calls `claim` (1361-1362); the deadline, cancel and hold kill loop is at 1483-1519.
  - `jobs.cancel` (816-881): a Queued job goes to Cancelled at once; a Running job gets `cancel=True` plus `local_brain.cancel_job`.
- Master Stop: `host_service.py:176` `master_stop` runs `work_trail.hold`, then `worker_boundary.stop_all`, `agent_loop.pause_all`, `jobs.cancel` for each live job, `local_brain.stop('MASTER_STOP')`, and `force_cancel_worker` (operation_stop.py:241) after 1 s.
- Work hold: `work_trail.hold/resume/execution_held` (155/180/172). `resume` refuses while any job is Queued or Running.
- `operation_priority.py` is only an OS nice preference (`.ledger/master-stop/priority.json`). It makes no memory decisions.

There are **no environment-variable seams** for readings. Only `ARC1_WORKBENCH_CONFIG_HOME` and `ARC_LEDGER_CONCERN` exist, for fixture isolation.

## 2. Existing tests to reuse

There are no tests anywhere for `resource_control`, `memory_forecast`, `brain_worker`, `probe`/`parse_devices` or `inference_hardware`; `git grep` finds none.

- **`tests_integrated/test_model_settings.py`** is the template:
  - `setUp` (27-34): temporary workspace, both environment variables, `Kernel`, `Session` with `ledger_control.bind`, `patch('workbench.brain_runtime.host', return_value=HOST)`, `patch.object(k,'launch')`.
  - `fixture_model()` (16-23) is a model record injected with `brain.put(k,'model.'+id, …)`. Set `total_bytes=20_500_000_000` and `architecture='qwen35moe'` metadata.
  - `NOBODY=2**22` (13) is a safe fake pid.
  - `transaction()` (135-153) patches `worker_live`, `terminate`, `start_server` and `completion` around `brain.run_model_job`. It already covers the restore, failed-restore, cancel-no-restore, and reply-blocks-handover cases (155-174).
- `test_service_lifecycle.py` patches `local_brain.stop`, `desktop_services.close_all` and `Kernel.launch` as AssertionError guards (18, 120).
- `test_operations.py` patches `os.setpriority` and `job_priority.process_identity` (79, 109-117).
- `test_agent_loop.py` guards `Kernel.launch` and `Kernel.submit` (46).
- `tools/traffic_forecast.py` has `example_trace`/`capture` for forecast traces. I read it but did not run it.

## 3. Current numbers

The formula has been unchanged since import commit aa0ce07: `git log -S` finds only that commit.

**Assumed metadata:** qwen35moe with `block_count` 40, `embedding_length` 2048, `head_count` 16, `head_count_kv` 2, as integers. `total_bytes` = 20,500,000,000.
- KV = 167,772,160 B (0.156 GiB).
- **Estimate = 27,220,425,344 B = 25.35 GiB (25,960 MiB, rounded up).** This matches the 0.4.4 figure of 25.4 GiB. Even 10 or 48 layers only moves it to 25.23-25.38 GiB.
- If the size is 20.5 GiB instead of 20.5 GB, the estimate is 27.18 GiB.

**Auto cap** = `min(32768, int(available × 0.65))` MiB. It is based on available RAM, not installed RAM, so with 64 GB installed it still **tops out at 32,768 MiB**. It only reaches that once available ≥ 49.23 GiB.

| Available | Auto memory_mb | Result |
|---|---|---|
| 60 GiB | 32,768 | OK |
| 40 GiB | 26,624 | OK |
| 39 GiB | 25,958 | **2 MiB short: MODEL_MEMORY_BUDGET_TOO_SMALL** |
| 30 GiB | 19,968 | MODEL_MEMORY_BUDGET_TOO_SMALL |

- Auto succeeds from about 39.002 GiB available.
- Any manual cap needs available ≥ estimate/0.8 = 31.69 GiB.
- `memory_mb` 32,768 needs ≥ 40 GiB available.
- Reserve with 64 GiB total = 2 GiB.

## 4. Smallest seam set: patches only, no production edits

1. `workbench.brain_runtime.host`: a FakeHost with `available_ram_bytes`, `total_ram_bytes`, `logical_cpus` and `hardware_profile.graphics[]`.
2. `workbench.brain_runtime.status`, `.probe` and `.prepare`.
   - `probe` should build its result with the real `parse_devices` on fixture text such as `Vulkan0: AMD Radeon 680M (RADV REMBRANDT) (…)` or `llvmpipe`.
   - `prepare` should return a fake executable and runtime dict.
3. Process table:
   - `workbench.local_brain.process_identity`: fake pids get tokens, real pids pass through, because `control_claim` uses `os.getpid()`.
   - `workbench.local_brain.kill_owned`: marks fake pids dead.
   - `workbench.resource_control.process_identity` and `process_memory`.
4. `patch.object(local_brain.subprocess, 'Popen', FakePopen)`:
   - Record argv.
   - Write a scripted log (offload line, `GRAPHITE_HOST_MEMORY_LIMIT`) into the `stdout` handle.
   - `poll()` returns the scripted exit.
   - This patch is global while it is active.
5. `workbench.local_brain.request`: scripted `/health`, `/props n_ctx`, `/apply-template`, `/tokenize`, `/v1/chat/completions` content or HTTP error.
6. `FakeClock` patched over the `time` attribute of `local_brain` and `resource_control`. Keep `time() − monotonic()` constant, because `_same_clock` allows ±1 s.
7. `workbench.local_brain.recheck` (or `identity`), so a 20.5 GB file is not hashed on every load.
8. `workbench.job_priority.apply_worker` set to a no-op.
9. `Kernel.launch` set to record only.
10. `workbench.brain_worker.memory_sample`.

Settings rows the runner writes:
- `ledger.operations.reserve_mb`
- `ledger.brain.{context, memory_mb, backend, gpu_layers, cpu_fallback}`
- `resources.foreground`
- `ledger.work_gate`
- `ledger.stacy.enabled`
- `ledger.operations.services_enabled`

Optional code changes:
- A `simulated` label on `offload_evidence`. Nothing labels fixture offload today.
- Make `host()` read the process's own cgroup, as `memory_sample` does.

## 5. Cases and the decision the current code makes

Unless stated, each case uses 64 GiB total, 4,096 context and Auto. ⚠ marks where the current code differs from what the spec seems to expect.

1. **Valid qwen35moe fixture** (tiny real GGUF with Q4_K, Q6_K and F32 tensors and a template). It registers with `UNSUPPORTED_ARCHITECTURE`. `brain.model.use` is refused at `jobs.submit` with `MODEL_ARCHITECTURE_NOT_IN_SUPPORTED_PROFILE` (configuration:196). ⚠ It passes only after adding the architecture to gguf_inspect.py:15 and re-adding the model.
2. **Invalid file** (bad magic or truncated data). `gguf_inspect.inspect` gives `GGUF_MAGIC_INVALID` or `GGUF_TENSOR_DATA_TRUNCATED`; the `brain.inspect` job fails and no record is written.
3. **Changed hash after registration.** `recheck` in `start_server` raises `MODEL_FILE_CHANGED_SINCE_REGISTRATION: <name>`. There is no CPU fallback, and the previous model is restored if it was live. A change between `recheck` and Popen gives `…BEFORE_LOAD` (356); a change after load gives `…SINCE_LOAD` (179).
4. **Unsupported architecture or tensor type.** Architecture `mamba` is rejected at :196; tensor type 39 is rejected at :198 (`MODEL_QUANTIZATION_NOT_IN_INSPECTION_PROFILE`); a missing template is rejected at :197. All three fail at submit.
5. **60 GiB available.** Estimate 25.35 GiB, cap 32,768 MiB; claim admits with headroom 58 GiB.
6. **40 GiB.** Cap 26,624 MiB; admitted with headroom 38 GiB.
7. **39 GiB.** ⚠ Auto rejects at submit with `MODEL_MEMORY_BUDGET_TOO_SMALL`. A manual cap of 26,000 MiB is admitted.
8. **30 GiB.** Auto gives `TOO_SMALL`; a manual cap of 25,960 MiB gives `MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM`.
9. **Unavailable reading.** `available=None` at submit gives `HOST_MEMORY_COULD_NOT_BE_MEASURED`. If it becomes None after submit, claim waits forever on 'Host memory could not be measured'. ⚠ With `total=None`, the reserve drops to 128 MiB.
10. **Too-small manual cap** (`ledger.brain.memory_mb=16384` at 60 GiB) gives `MODEL_MEMORY_BUDGET_TOO_SMALL`. The 0.8 check passes first.
11. **Counted once.** 40 GiB available; a Running io job with budget 10 GiB and rss 2 GiB; one resident model listed in both worker slots with the same pid, `memory_mb` 8,192 and rss 8 GiB. Headroom = 40 − 2 − 8 = 30 GiB.
12. **Queued 32 GiB `normal` compute request, idle queue, 34 GiB available.** Admitted: headroom is exactly 32 and the test is strictly greater.
13. **Same request at 33 GiB.** 'Waiting for shared-memory headroom'; `resource_wait` is saved.
14. **40 GiB plus a Running io job with 8 GiB unmaterialized.** Waits, since 30 < 32. If the other job is also compute, the recorded reason is 'CPU calculation slots are occupied'.
15. **⚠ The 32 GiB request as a model activation.** It can only be submitted at ≥ 40 GiB available. If RAM drops to 34 GiB, claim admits it, but the second `configuration` call fails it with `MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM`. Admission and launch use different rules.
16. **Background request with falling headroom** (samples 1 s apart, losing 0.5 GiB/s). Deferred by the forecast for up to 8 s, then admitted as `wait_budget_elapsed`.
17. **Radeon accessible.** Probe reports Radeon; log says "offloaded 41/41 layers". Backend VULKAN (requested AUTO), `observed_gpu_layers` 41, argv `-ngl auto --fit on --device Vulkan0`.
18. **Radeon missing or inaccessible.** CPU with 'Auto selected CPU…'. With only llvmpipe, the probe reports `NO_PHYSICAL_VULKAN_DEVICE` and the load falls back to CPU, or raises `VULKAN_UNAVAILABLE` if fallback is off. A 0/41 or missing offload line gives `VULKAN_GPU_OFFLOAD_NOT_OBSERVED` and one CPU retry.
19. **Load failures.**
    - Timeout (fake clock past 90 s) and driver exit both retry once on CPU when the backend is Vulkan; a second failure fails the job and restores the previous model.
    - Empty first reply gives `MODEL_PROBE_RETURNED_NO_TEXT` with no retry.
    - Vulkan HTTP 500 on the first reply leads to CPU qualification (`CPU_CHAT_QUALIFIED`).
    - ⚠ A reported `n_ctx` of 2048 is accepted: the job reaches Ready with `worker.context` 2048 while `selection.config.context` stays 4096.
20. **Pressure and Stop.**
    - Supervisor marker during load, or a `model_room` shortfall: `GRAPHITE_HOST_MEMORY_LIMIT`, no CPU retry, no restore, and `status.resource_stop` is set.
    - Cancel while Queued: Cancelled at once.
    - Cancel while loading: `MODEL_OPERATION_CANCELLED`, no retry, no restore.
    - Foreground lease (until now+5) gives background jobs 'Foreground interaction has the next turn'.
    - ⚠ A work hold **cancels** queued jobs at claim rather than holding them; only agenda and agent assignments resume after the hold.

Relevant paths:
- /home/user/Struthio/workbench/resource_control.py
- /home/user/Struthio/workbench/local_brain.py
- /home/user/Struthio/sdk/cli/arc1cli/gguf_inspect.py
- /home/user/Struthio/workbench/brain_runtime.py
- /home/user/Struthio/workbench/brain_worker.py
- /home/user/Struthio/workbench/inference_hardware.py
- /home/user/Struthio/workbench/model_settings.py
- /home/user/Struthio/workbench/engineering_kernel.py
- /home/user/Struthio/workbench/memory_forecast.py
- /home/user/Struthio/workbench/job_priority.py
- /home/user/Struthio/workbench/work_trail.py
- /home/user/Struthio/workbench/host_service.py
- /home/user/Struthio/tests_integrated/test_model_settings.py