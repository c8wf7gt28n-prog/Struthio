# D213 PBUS driver — superseded by decision D1

R10 §12.1 item 6 asks for a PBUS DMA/FIFO driver plan. On the D213ECV the only full 16-bit PBUS group (PD0–PD20)
uses the pads of every display output (`architecture/R10_PINMUX_CONFLICTS.md`), and the PBUS does single AHB
accesses only (≈ 20 MB/s derived ceiling at default timing). Decision D1 (`DECISIONS.md`) moved the D213 ↔ 45F
link to **GMAC0 RGMII**. The equivalent plan (DMA, coherent buffers, IRQ/timeout behaviour, test list) is in
`d213/gmac_link/PLAN.md`. If D1 is reversed, this directory is where the PBUS plan goes.
