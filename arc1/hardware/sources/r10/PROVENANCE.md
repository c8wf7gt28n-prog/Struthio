# R10 source excerpt — provenance

These files are **unmodified copies** from the owner-supplied *ARC-1 R10 clean
handoff* (six archives, 2026-10-16; built from Struthio `18b778b` per the
handoff README). They are the evidence that `hardware/manifests/arc1-r10.hw.json`
cites. The full handoff (1,158 files: KiCad project, RTL, firmware, analyses) is
**not** vendored here.

The handoff's own `HANDOFF_MANIFEST_SHA256.txt` has SHA-256
`42bb13546b0a292e57f308525e946dc4813063d79fd7b545213334a634a2bcee`; every file
below matches its entry there. `SHA256SUMS` in this directory lists the same
digests and `arc1 hw inspect` re-checks the ones the manifest cites.

| Archive | SHA-256 |
|---|---|
| ARC1_R10_HANDOFF_PART01.zip | 5ada850c9b44687a689056932f190eba75ea2a5ca2bf20a068e645912a04b740 |
| ARC1_R10_HANDOFF_PART02.zip | f97ea9d2f8dc534c3e6f304dbea0da439e37550c55d93376c703b730e02ebb2b |
| ARC1_R10_HANDOFF_PART03.zip | f683d0e5c47390d9cd3ff81feb0bad7acd12ced100599e490ce9b60ec0ad19b5 |
| ARC1_R10_HANDOFF_PART04.zip | 9313688246e311ebc4036abaa7fbc0b2e1079dca3ca62c5475ae7527909ca218 |
| ARC1_R10_HANDOFF_PART05.zip | 5e95b210b6a298cd40a4ac64b0d5481d25ff5b652dedee235bf8b5b7f94a1cf6 |
| ARC1_R10_HANDOFF_PART06.zip | 2f5a183a436ea1c5cc2dd689c90ce4a648e3e6dbc94b7383cebeba68b8f7444c |

Paths keep their location relative to the handoff's `arc1-compact/` root. The
handoff's authority order applies: `R10_WORK/` supersedes the historical R05–R8.5
trees, and its status is **fabrication HOLD** — nothing here is board evidence.

## Host-check reproduction (2026-10-16, this session)

`R10_WORK/run_host_checks.sh` on a clean copy of the extracted handoff, Linux,
gcc 13.3.0, Python 3.13.16, no KiCad, no FPGA tools:

- 13/16 steps exit 0. Every generator reproduced its committed output byte for byte.
- `firmware/f133_bootloader make all` exits 2: its `layout` step runs
  `git diff --exit-code`, and the handoff has no `.git`. Inside a throwaway git
  repository the same step exits 0 (tests, sanitizers, freestanding build, all
  mutants killed). Reproducibility gap, not a design defect.
- `cad/gen/design.py` exits 1 and `cad/check/crosscheck_r10.py` reports 580
  findings: both need the KiCad standard footprint library at `/usr/share/kicad`,
  which was not installed. The shipped `qa/RUN_HOST_CHECKS.log` shows them
  passing on a machine that had it.
- `run_all.sh` (RTL and P&R) NOT_RUN: Icarus, Verilator, Yosys, nextpnr-ecp5 and
  Trellis are not installed here.
