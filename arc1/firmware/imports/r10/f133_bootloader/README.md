# R10 configuration loader and board HAL contract

The bootloader core and D213 45F loader are HOST_TESTED with a behavioural model.
There is no production F133/D213 BSP binding, linked board firmware image, or
measured rail-sequencing evidence. Fabrication remains HOLD.

`src/ecp5_cfg.c` serves both FPGA configuration paths. It retains the historical
`ecp5_cfg.h` API from `R85C_WORK/firmware/include`; the R10 contract below applies
to its GPIO/SPI HAL implementations without modifying that archived header.

## Rail qualification is a hardware prerequisite

`ECP5_PIN_VCC_PG` must represent reviewed valid-voltage qualification for the
selected FPGA, including core, auxiliary and relevant IO rails. It must not be
a constant one or inferred from INITN/DONE. Qualifier thresholds, tolerances,
delay, discharge, and isolation response must be checked against guaranteed
device limits during startup, shutdown and brownout. See
[`R10_RAIL_QUALIFICATION.md`](../../hardware/R10_RAIL_QUALIFICATION.md) and
[`R10_INTERCONNECT_DECISIONS.md`](../../hardware/R10_INTERCONNECT_DECISIONS.md).

The current CAD nets `FPGA12_VCC_PG` and `FPGA45_VCC_PG` originate at the respective
TLV62569P core buck PG outputs, pulled up to switched VCCIO. That connection does
not supervise VCCAUX or establish a guaranteed valid-voltage window for every
rail. It does not satisfy the production contract by itself. Software polling
cannot correct that hardware limitation or replace asynchronous isolation.

## Required HAL behavior

- `PROGRAMN`: setting zero drives low; setting one releases to high impedance.
  The binding must never actively drive a high level into an unpowered device.
- `PWR_EN`: enables/disables the selected FPGA rail set. A no-op requires a
  reviewed hardware-owned equivalent. A service jumper can override shutdown;
  software cannot prove the rails are physically off.
- `BUS_EN_N`: setting one requests isolation. A no-op requires a reviewed
  hardware-owned equivalent. The current 45F CAD buffers are always enabled
  while their IO supply is present; the abstract GPIO does not add a physical
  enable. The 12F return buffer is selected by chip select alone.
- `PSRAM_REQ`: setting zero requests memory quiescence in bindings that use it.
  It is unused for the 45F SDRAM path and is not an R10 memory-isolation proof.
- SPI `select(ctx, 0)` deasserts the FPGA selection, including during cleanup;
  the 12F binding must also keep the shared NOR deselected for FPGA transfers.
- HAL callbacks must complete in bounded time. Pin waits poll every 100 us;
  blocking GPIO, source reads, or SPI transfers extend the time between samples.
  A transfer already underway can continue clocking after a physical fault.

## Sampled fault handling

The loader checks PG around each SPI HAL transfer, around blocking source reads,
and during PROGRAMN/INITN/DONE waits. A sampled rail failure remains
`ECP5_E_POWER` even if a later sample has recovered. It stops issuing subsequent
SPI transfers, deasserts chip select, requests bus isolation and memory
quiescence, releases PROGRAMN, and requests rail shutdown.

All failed power-up attempts take the same cleanup path. A configuration error
with valid rails retains the existing powered/unconfigured state; a rail fault
sampled during that cleanup promotes the result to `ECP5_E_POWER` and requests
shutdown. `ecp5_safe(c, 0)` also requests shutdown if its own PG samples are bad.
Successful configuration checks PG before returning. A successful 45F probe
holds PROGRAMN low, isolates the bus, and checks PG after that cleanup.

These guarantees refer to samples and HAL requests. They do not detect an
unlatched transient occurring entirely between samples, prove power-off
isolation, or monitor the FPGA continuously after configuration returns.

## Reproduction

From this directory run `make test sanitize freestanding mutants`. The fault
suite covers early power-up loss, stale INITN, PROGRAMN release, selection,
command header/receive boundaries, a recovered sampled fault, burst payload,
source read, DONE wait, and loss during configuration/probe cleanup. Existing
boot-selection and end-to-end 45F path tests and mutation checks also run.
The freestanding step compiles objects; it is not a target image or SDK build.
