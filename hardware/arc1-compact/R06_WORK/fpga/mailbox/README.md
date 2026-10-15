# F133 ↔ T35 mailbox ("AMBX" v1, R06)

Evidence level: **RTL_SIMULATED** (`../top/tb/tb_top.sv`). No physical SPI link has been tested.

The mailbox is a byte-addressed SPI register window. It **transports the R05 ARC1 wire frames
unchanged** (`R05_BASELINE/protocol/WIRE_ABI.md`, 24–4120 bytes with CRC32), so the R05
session, credit, epoch and CRC rules stay authoritative. The mailbox adds no second framing
layer and no second CRC.

## SPI framing (mode 0, F133 is master)

```
write : 0x02, A[15:8], A[7:0], D0, D1, ...          (address auto-increments)
read  : 0x0B, A[15:8], A[7:0], dummy, D0, D1, ...
```

* The slave oversamples SCK, so **f_SCK ≤ f_sys / 8** (simulated at /8 and /16; 10 MHz with an
  80 MHz `sys_clk`).
* MISO is driven only while SS_N is low. When SS_N is high, the line is released to the F133
  pull-up. PC5 is also the F133 BOOT-SEL1 strap; see the board plan.
* A CS# rise mid-byte discards that byte. The next frame starts clean.

## Register map

| Addr | Name | Notes |
|---|---|---|
| 0x0000 | MAGIC | `41 4D 42 58` = "AMBX" |
| 0x0004 | VERSION u16 = 1, CAPS u16 | CAPS b0 PSRAM fitted, b1 BIST |
| 0x0008 | STATUS u16 | b0 FPGA_READY, b1 PSRAM_READY, b2 PSRAM_ERROR, b3 JOB_PENDING, b4 RESP_READY, b5 DOORBELL_OVERRUN, b6 BIST_BUSY, b7 BIST_PASS, b8 BIST_FAIL, b10:9 PSRAM error code |
| 0x000C | CONTROL (write-1 pulses) | b0 DOORBELL, b1 RESP_ACK, b2 PSRAM_RECOVER, b3 BIST_START, b4 CLEAR_OVERRUN |
| 0x0010 | REQ_LEN u16 | 1..8192 |
| 0x0014 | RESP_LEN u16 | RO |
| 0x0018 | DOORBELLS u32 | accepted doorbells since FPGA reset |
| 0x001C | BIST_ERRS u32 | mismatching bytes plus failed PSRAM operations |
| 0x2000–0x3FFF | REQ buffer | host writes a frame here |
| 0x4000–0x5FFF | RESP buffer | host reads the answer here |

IRQ_N (open drain, on F133 PC6) is asserted while RESP_READY is set; RESP_ACK clears it.

## Host rules (implemented in `R06_WORK/firmware/t35_link.c`)

* If MAGIC is not "AMBX" or VERSION ≠ 1, the device is **FPGA_NOT_READY**. With no FPGA, or
  an unconfigured one, MISO is pulled up and the host reads 0xFF.
* A doorbell while a job is pending, a response is unacknowledged, or REQ_LEN is 0 or above
  8192 is refused and sets DOORBELL_OVERRUN.
* An FPGA reset clears all mailbox state (simulated). The host must then send a new R05 HELLO
  with a larger epoch, and must re-run on the CPU any job whose result it has not received.

## R06 job engine = transport loopback only

`mbx_loopback.sv` copies REQ to RESP. It exists to prove the transport and the host fallback. The
R05 `arc1_transform` RTL is **not** connected yet; adding an R05 frame parser, CRC and transform
engine behind this mailbox is PASS 7 step 4.
