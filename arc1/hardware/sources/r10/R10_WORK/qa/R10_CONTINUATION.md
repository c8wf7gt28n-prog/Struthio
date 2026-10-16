# R10 continuation: configuration recovery and electrical evidence

Base: owner-supplied Struthio 18b778b plus the power-review changes.
Fabrication HOLD. This pass changes loader software, not copper or regulator wiring.

## Implemented

The common FPGA loader isolates its bus before requesting power. It checks the
reported PG signal before commands and busy polling, before and after source
reads during bitstream transfer, and before returning configuration success.
A detected rail loss returns ECP5_E_POWER, releases chip select, isolates the bus,
releases PROGRAMN and requests power-off. A zero transfer chunk is rejected
instead of allowing an infinite loop.

Fault injection drops PG during the second source read. The test verifies that
only the first 4096 payload bytes were sent, CS is released, the bus is isolated,
PROGRAMN is released and power is disabled. Healthy configuration also passes.
Existing boot and D213 configuration-path tests remain part of the validation.

This is synchronous software recovery. It cannot stop an already-running SPI
transfer instantaneously, protect against an unreported voltage excursion, or
replace hardware interlocks. It does not claim autonomous monitoring after the
loader has returned. The production HAL must report real signals.

## FPGA rail finding

The selected TLV62569P uses typical PG thresholds of 95% rising and 90% falling,
with a typical 40 us falling delay. For the nominal 1.095 V FPGA rail these are
about 1.040 V and 0.986 V. ECP5's stated operating minimum is 1.045 V. Therefore
the existing PG signal is not a sufficient valid-operating-voltage qualifier.
Threshold tolerances, auxiliary/IO rails, discharge and brownout slew still need
hardware review. Do not mark sequencing complete because the software test passes.

TI source, sections 6.5 and 7.3:
https://www.ti.com/lit/ds/symlink/tlv62569.pdf
Lattice operating limits:
https://www.latticesemi.com/view_document?document_id=50461

## HDMI evidence recovered

The ADV7513 Hardware User's Guide Rev.0 is accessible at the lowercase URL below.
Sections 5 and 7.6 confirm R_EXT = 887 ohms, 1%, with a short ground connection.
Section 6.7.1 permits either rail order but requires all domains to finish
powering up/down within one second. Section 7 recommends supply filtering and
local 100 nF bypass capacitors. The current buck/ferrite implementation must be
checked against the guide's noise requirements; access to the document alone
does not close layout or HDMI validation. Programming-guide review remains open.

https://www.analog.com/media/en/technical-documentation/user-guides/adv7513_hardware_user_guide.pdf

## Next unresolved engineering work

Specify and verify hardware rail qualification and shutdown behavior; obtain
FPGA power estimates using the actual implemented designs; review HDMI filtering
and initialization; restore a complete KiCad toolchain to repeat footprint/ERC/DRC
checks before routing. No owner decision is needed to continue these tasks.
