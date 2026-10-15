# Coverage and evidence — R05

This work uses the current conversation and five supplied attachments: Compact
R02 DOCX plus four R19/R22/R23 ZIPs. Other chats were not accessible; the chat ID
alone did not grant their contents. Missing historical U2/U3/U4 and authoritative
STRUTHIO source remain unavailable.

The prior audit inventoried all 180 archive entries (122 distinct byte contents),
reviewed the full R23 owner handoff and engineering evidence, reproduced historical
112/67 software checks, and compared source inventories/manifests. Those results
are preserved under `reference/verification/`; they do not verify new Compact hardware.

## Current evidence

| Claim | Evidence stage | Artifacts |
|---|---|---|
| Core and 320 MiB target | OWNER_SELECTED | `OWNER_SELECTION.md` |
| Component interfaces/capacities | MANUFACTURER_DOCUMENTED; applicability still requires integration | `engineering/sources.json` |
| Protocol codec/session | HOST_TESTED | C/Python tests, golden vectors, fuzz/sanitizer logs |
| Fixed-point reference | HOST_TESTED, independent oracle | C scalar/batch/UBSan records for 1,165 cases |
| Transform datapath | RTL_SIMULATED | Actual Icarus 11.0 compile/run and 1,165-case reference comparison |
| Combined host model | HOST_TESTED | 13 integration tests and deterministic 256-object bounds scene |
| Corrected display timing | PLANNING_CALCULATED | 14 validator tests; conditional register model, no writes |
| BT memory allocation | PLANNING_CALCULATED | 18 validator tests; illustrative assets only |
| T35F400 400-ball inventory | SOURCE_BYTES_EXTRACTED_AND_INDEPENDENTLY_COMPARED | CSV, raw-workbook hash, stdlib/openpyxl comparison |
| Complete FPGA, CPU boot, BT drawing | NOT_IMPLEMENTED_HERE | No native full project, image or renderer supplied |
| Board fit/timing and real operation | UNEXECUTED | Efinity/synthesis/STA/physical tests unavailable |

The C session is a conservative software reference; it is not FPGA RTL. Integration
uses the C numeric reference, not the HDL datapath. Separate RTL simulation does
not prove an integrated mailbox. The source package inventory has no PCB nets.
The display register model is not initialization. The scene draws no pixels.
No measured SPI throughput, game FPS, latency, power, memory reliability or
acceleration benefit is claimed.

`verification/last_run/summary.json` records the final reproduction run. Component
reports bind relevant sources to SHA256 hashes. Author-environment paths in logs
describe where a command ran; use portable instructions in `VERIFY.md` to reproduce.
Failed initial Icarus testbench parsing is retained as history and was corrected;
the final runner requires explicit PASS markers and rejects ERROR/FATAL diagnostics.
LeakSanitizer was disabled due to environment constraints; ASan/UBSan did execute.

Vendor PDFs were reviewed through available extracted documentation; their raw
hashes remain null where bytes were unavailable. The official T35 workbook was
downloaded, hashed and independently compared, but is not bundled. The downloaded
Icarus Debian package was extracted locally to run simulation; it is also excluded.
`tools/toolchain_provenance.json` records acquisition details. No proprietary tool
installer, licensed EDA/IP or claimed native report is redistributed.

All five originals are preserved unchanged with original hashes. Previous R04
instructions/porch arrays in `reference/r04/` are historical and superseded by R05.
