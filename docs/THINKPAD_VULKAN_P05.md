# Graphite P05 · the ThinkPad inference path

Graphite 0.2a2 adds a pinned Linux x64 Vulkan worker alongside its CPU worker.
Both are llama.cpp b11669, source commit
`620d2225cc436ab0b001e3200e590e3b286ef9ab`. The GGUF registration, model hashes,
owned jobs, authenticated loopback API, model handover and local records remain
the same. No GGUF weights are included or downloaded by this upgrade.

The intended owner computer has a Ryzen CPU, Radeon integrated GPU and 64 GB
system RAM. The exact product and GPU identifiers remain unverified. Graphite
reads the actual current computer; a cloud inventory is never presented as a
measurement of the owner's ThinkPad. No serial number or UUID is collected.

## What to use

Open Brain from Programs or the existing model controls. The launch preferences
also appear in Settings under Local model:

| Preference | Meaning |
| --- | --- |
| Auto | Prefer Vulkan when an accessible AMD amdgpu render device and the bundled worker are present. Otherwise select CPU and record why. |
| CPU | Use the existing pinned CPU distribution, with GPU offload explicitly disabled. |
| Vulkan | Discover devices using the pinned worker and request GPU offload. |
| GPU layers: Auto fit (-1) | Let upstream llama.cpp select layers against its reported Vulkan budget. The explicitly selected context stays supplied. |
| GPU layers: 0 | Use CPU. |
| GPU layers: positive | Request at most that many layers. Device limits can still prevent loading. |
| Allow CPU fallback | Make one CPU attempt after Vulkan discovery, load or the initial qualification generation fails. The reason is retained. |

Saved defaults apply to the next explicit Use or Qualify operation. A queued
load keeps its frozen request. Editing a preference never restarts a working
model. Earlier records without these fields retain their CPU meaning.

The running status distinguishes the requested backend from the effective
backend. Vulkan requires a positive `offloaded N/M layers to GPU` readback from
the owned pinned worker's load log. Device discovery alone does not qualify
inference. Qualification receipts name the actual backend and runtime hash.
The normal ready-generation qualification is separate from answer accuracy.

Hardware / Vulkan shows the observed CPU/core features, system RAM, product
name, kernel, DRM render devices and driver/package versions. **Inspect Vulkan
devices** runs only `--list-devices`, in the existing asynchronous UI path.
It loads no model. Software-only Vulkan devices do not qualify as acceleration.
The report labels its device discovery and qualification limits explicitly.

## Debian dependencies

The worker archive is included. The kernel, Mesa and firmware remain maintained
Debian packages, with their package notices and security updates. Graphite does
not copy a cloud machine's drivers onto a laptop or change repository sources,
kernel parameters, user groups or BIOS memory reservations.

From the extracted program folder, the existing Debian installer can add them:

```bash
bash INSTALL_DEBIAN.sh --vulkan --quick --yes
```

That explicit command uses apt and then the normal runtime installer. It needs
the same network/package access and administrator rights as the existing Debian
installer. It is not an offline operating-system image. Offline/check-only
modes still run no apt commands. If `firmware-amd-graphics` has no candidate,
enable Debian's documented `non-free-firmware` component as an owner system
configuration step, then rerun. Graphite does not silently rewrite sources.

The outer release installer accepts the same option: add `--vulkan` to
`python3 INSTALL_LS.py --usb . --target ... --minimal-session --yes`.
Use `--plan` first for a read-only explanation. This checkpoint does not supply
a complete Debian `.deb` or Python wheel cache; full offline delivery is P19.

Runtime packages: `libvulkan1`, `mesa-vulkan-drivers`,
`firmware-amd-graphics`, `vulkan-tools`, `libstdc++6`, `libgomp1`,
`libssl3t64`, `zlib1g`, `libzstd1`, `libgcc-s1`, `libc6`.
The native worker's observed shared-library dependencies include OpenSSL,
zlib and Zstandard as well as the Vulkan loader. These package names target
Debian 13; another distribution may supply the same ABI under different names.
The existing kernel supplies amdgpu. An inaccessible render node is reported;
the upgrade never makes device files world-writable.

## Shared memory, honestly accounted

System RAM is one shared pool. DRM VRAM/GTT figures and Vulkan memory budgets
describe allocation views; Graphite never adds them to system RAM or declares
that 64 GB system RAM means 64 GB dedicated GPU memory. Device allocation limits
can be smaller than the available system memory. A large model fitting in RAM
does not establish interactive generation speed.

The preflight keeps the existing weight/KV estimate and available-host-RAM
budget. It is a conservative planning estimate, not a complete driver allocation
model. Auto layers use upstream device fitting rather than a guessed VRAM size.

CPU retains its address-space resource cap. Vulkan drivers can reserve large
virtual ranges, so a Linux supervisor instead samples the native child's RSS
and host/cgroup memory headroom every quarter second. It ends the worker when
the resident budget or reserved headroom is exhausted. Its receipt says
`RSS_AND_HOST_HEADROOM_GUARD`: **this is not a hard cap on GPU allocations**.
Shared and GPU memory may be accounted differently from process RSS; a kernel
OOM can still happen before a sample. P06 adds coordinated resource admission.
The child dies if its supervisor disappears, and Stop uses the existing owned
PID/start-token process tree. No root is needed for worker supervision.

Cancellation, changed model files and a host-memory guard stop never cause a
CPU retry. A later failed user generation is reported through its original job;
this pass does not replay user work automatically. A failed new load still uses
the existing previous-model recovery path when the owner has not cancelled.

The separately qualified protected MODEL profile stays CPU-only because it has
no GPU device grant. Resident assistant inference uses the new backend route.
Extending a protected profile requires its own deliberate device boundary work.

## Upstream pin, dependencies and reproducible build

Bundled archive:
`runtimes/llama.cpp/b11669/llama-b11669-bin-ubuntu-vulkan-x64.tar.gz`

SHA-256:
`e8709e5ba6c1b093dea7f3de57f4aba842f9a188fba6b465782d65d6fcfa4d9f`

The downloaded bytes were compared to the official release attestation. A
checksum is not itself a signature. The runtime materializer checks that pin
before extraction and verifies its private extracted-file receipt before use.
The distribution retains its upstream licence/notice files. CPU archives and
the Windows CPU add-on metadata are preserved. This pass supplies Linux x64
Vulkan; it does not promise a Windows Vulkan build.

For a local source build of the same revision, upstream documents:

```bash
sudo apt-get install build-essential cmake libvulkan-dev glslc spirv-headers
git clone https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp checkout 620d2225cc436ab0b001e3200e590e3b286ef9ab
cmake -S llama.cpp -B llama.cpp/build -DGGML_VULKAN=1
cmake --build llama.cpp/build --config Release
```

Those commands document reproduction; Graphite uses its bundled verified pin,
not a random executable from PATH. Replacing the shipped worker deliberately
requires updating its runtime manifest and qualification. Local builds need not
be byte-identical to upstream binaries.

Primary references verified for this upgrade:

- [Official b11669 release](https://github.com/ggml-org/llama.cpp/releases/tag/b11669)
- [Official Vulkan archive attestation](https://github.com/ggml-org/llama.cpp/attestations/56338993)
- [Build instructions at the pinned revision](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/docs/build.md)
- [Debian 13 Mesa Vulkan package](https://packages.debian.org/trixie/mesa-vulkan-drivers)
- [Debian AMD firmware package](https://packages.debian.org/trixie/firmware-amd-graphics)
- [Debian 13 OpenSSL shared libraries and compression dependencies](https://packages.debian.org/trixie/libssl3t64)

## Completion boundary and next work

P05 delivers the runtime, selection route, device inventory, launch controls,
fallback and actual offload readback. The cloud has no physical Vulkan device;
owner hardware/model throughput and rendering comfort remain pending. No GPU
speedup or large-model capacity is claimed from this checkpoint.

P06 is the traffic cop: coordinate CPU preparation, inference admission and the
single shared RAM pool. P07 builds intelligent data arrangement; P08 handles
context/cache lifecycle. P05 provides their hardware and worker facts without
claiming those later behaviours already exist.
