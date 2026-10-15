# BT820 private-memory planning tool

This is an executable, declared-allocation budget for Compact's selected **MN820 / 128 MiB DDR3L** prototype. It does not test a memory controller, RAM contents, vendor initialization or a live renderer.

```sh
python memory/validate_memory.py --output memory/planning_report.json
python -m unittest discover -s memory/tests -v
```

API: `validate_memory(plan: dict) -> dict`. CLI exit 0 means valid declared intervals; exit 1 rejects malformed or inconsistent planning data. Addresses are byte offsets in the **BT-owned** DDR address space. Intervals are half-open `[start,end)`. CPU/FPGA memory is not mapped into this space.

The source-bounded constants are 134,217,728 installed bytes and **2,621,440 reserved upper bytes**. The reserved interval is `[131596288,134217728)`; user-region capacity before buffers is **125.5 MiB**. Reducing the reservation or silently changing module capacity is rejected. Overlap, out-of-range access, duplicate names, another device's ownership, alignment violations, undersized/incorrect-stride framebuffers and inconsistent swapchain slots are rejected.

The selected budget uses two RGB8 render/scanout buffers, each 1024 by 600 with 3072-byte stride and 1,843,200-byte storage. They start at 0 and 2 MiB. Other regions are **illustrative allowances**, pending the actual STRUTHIO scene: 32 MiB resident atlases, 8 MiB scratch render targets, 4 MiB asset staging, and 1 MiB saved command lists. Native RAM_DL/RAM_CMD live in separate BT regions and are not charged again to DDR.

Total declared allocation is **48.515625 MiB**, leaving **76.984375 MiB** in all free intervals. The largest contiguous free interval is 76.5 MiB; the small gaps reflect 2-MiB framebuffer spacing. The 4096-byte address and 64-byte row alignment rules are explicit planning policies, not a complete vendor alignment qualification. A future two-buffer RGB8 capture stage would need at least 3,686,400 payload bytes plus layout/alignment. It is **not allocated or enabled** in this initial profile.

The active RGB8 pixel stream at nominal60 Hz is110.592 decimal MB/s; that excludes memory passes, padding, refresh, arbitration and overlay/asset reads. Free capacity does not establish rendering throughput. Workload sizes and hardware results remain unverified even if a caller asserts confirmation fields.

Sources: [MN820 product](https://brtchip.com/product/mn820/) and [datasheet](https://brtchip.com/wp-content/uploads/2025/01/DS_MN820-1.pdf) (S06); [BT82X guide v1.4](https://brtchip.com/wp-content/uploads/2026/09/BRT_AN_086_BT82X-Series-Programming-Guide-1.pdf) §2.1/§2.14 (S12), including upper2.5-MiB reservation and2–4 buffer swapchains. Source documentation is referenced rather than redistributed. A module-level budget does not qualify a discrete DDR substitution, final electrical layout or real workload.
