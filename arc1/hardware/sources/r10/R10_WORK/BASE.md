# R10_WORK — base and authority

- Change specification: spec/ARC1_R10.docx ("ARC-1 Architecture Change Control, R10, Engineering Proposal rev 0.1,
  15 October 2026"), text extraction spec/ARC1_R10.txt, hashes spec/SHA256SUMS. Supplied by the owner in this session.
- Archived reference designs (frozen, not edited here): R85_WORK (8636e38), R85C_WORK at 0defcfe (R8.5-C: RGMII
  job link on the ECP5-45F, closed at C4; C5 benchmark/doc pass not run because R10 moves the RGMII endpoint to a 12F).
- R10 reuses R85C_WORK RTL/firmware as reference only (R10 §6.3): nothing here inherits R8.5-C evidence.

## Owner decisions this spec overrides — need explicit owner confirmation (OPEN)
- PRODUCT_VISION_2D_FPGA_AUDIO.md: "Do NOT add a fourth programmable processor". R10 has F133 + D213 (two CPUs) +
  ECP5-45F + ECP5-12F (two FPGAs) = four programmable devices.
- CLAUDE.md (R06): "keep three chips; F133 controls BT820 directly". R10 replaces the BT820 with the D213ECV.
Work proceeds on R10 as the newer, dated change-control document; fabrication remains HOLD (R10 §10.2).
