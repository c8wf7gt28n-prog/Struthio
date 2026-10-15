# Coverage and evidence

This handoff is based on this conversation and **five supplied attachments**: the Compact R0.2 DOCX and four R19/R22/R23 engineering ZIPs. Other ChatGPT chats were not accessible. The supplied chat identifier did not provide its contents.

All 180 entries in the four ZIPs were inventoried (122 distinct byte contents). The full R23 owner handoff was read/extracted and its hash checked. Engineering decision/migration, memory, video, host, storage, power/recovery, pin-audit and evidence records were reviewed across parallel workstreams. Package inventories were compared with their manufacturer workbooks; the architectural diagram was inspected. Original archives are included unchanged under `reference/originals/`.

Fresh checks reproduced during the prior-work review:

| Check | Result | What it establishes |
|---|---|---|
| R23 Project House npm tests | 112/112 passed | Historical software regression; synthetic DOM/service-worker fixtures |
| R22 DEV-002 npm tests | 67/67 passed | Historical software regression |
| R23 source-workbook audit | 484 F484 rows match columns A–H | Manufacturer package-source consistency |
| R23 working manifest | 94/94 entries match | Supplied byte integrity |
| DEV-002 working manifest | 46/46 entries match | Supplied byte integrity |
| Original R22 manifest | 30/30 entries match | Original supplied byte integrity |

Logs under `reference/verification/` document those checks; they do not test the new Compact firmware, renderer or RTL. The 968 Tabletop records are unassigned A/B package definitions, not Compact nets.

Current Compact hardware claims remain at selected/documented/proposed stages. The 48 MHz screen timing and memory/bandwidth figures are calculations. No native T35 Efinity project, Compact CAD, actual firmware/RTL/bitstream, authoritative STRUTHIO build/trace or physical scene/display/DDR/power measurement is supplied here.

Missing historical documents U2/U3/U4 are identified in the reconciliation report. Their original contents were not reviewed. A synthetic graphics challenge can proceed without them or the actual game, but cannot certify STRUTHIO fidelity.

The prior recommendation and reconciliation are retained under `reference/research/`; their older open-part wording and Tabletop decisions are historical. The new Compact owner selection and decision register govern current work.

Primary sources were checked through manufacturer/project pages or web-extracted documentation. No newly downloaded vendor PDFs, proprietary IP or licensed tool installers are bundled. `engineering/sources.json` records source versions and provenance; original-file hashes stay null where raw bytes are unavailable.
