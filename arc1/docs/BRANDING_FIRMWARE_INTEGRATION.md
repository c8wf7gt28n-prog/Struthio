# ARC-1 branding & firmware integration — engineering draft R01

## Decision

Keep firmware, SDK, Windows developer console, simulator, launcher, tools and
branding in one versioned **development platform**. Ship firmware and SDK as
distinct build outputs. A game SDK is not the same thing as the console OS/runtime.
Existing R10 bootloader and D213/F133 driver sources are preserved under
`firmware/imports/r10/`. No bootloader, hardware driver or FPGA bitstream is
deemed functional merely by importing this code.

## Identity authority

- Name: **ARC-1**. Expansion: **Adaptive RISC-V Console**.
- Primary identity: the user-supplied brushed-metal silver wordmark with orange accents.
- Hardware concept photograph is a **visual reference**, not a dimensional CAD model.
- Preserve supplied artwork pixels; do not redraw the logo from a font.
- Console UX, SDK CLI, Windows launcher, status LCD, HDMI boot and recovery screens
  should draw from `branding/identity.json` and their platform-specific compiled assets.
- Games (including STRUTHIO) have their own brands; do not silently overwrite them.
- The hardware identity must never imply that FPGA or hardware diagnostics passed
  when only a host simulator ran.

## Target scope

| Target | Brand presentation | Validation |
|---|---|---|
| DOS-style `arc1 ui` | ASCII ARC-1 title, expansion, SDK version | Host test |
| Windows 11 tools | Icon/splash from official supplied art, native terminal and GUI | Windows test pending |
| `arc1 brand` | Verify official asset digests, show LCD conventions | Host test |
| 16x2 character LCD | Brief status, fault and cartridge messages | F133 driver & board test pending |
| HDMI firmware splash | Official graphical logo + boot diagnostics | D213 graphics/video pending |
| F133 boot messages | Compact string status codes and version | Firmware pending |
| D213/12F/45F boot | Individually tracked checks | Firmware/RTL pending |
| USB cartridge launcher | ARC-1 branding; game identity is separate | Runtime pending |

## Lifecycle and architecture

`firmware/` builds boot and system binaries, whereas `sdk/` builds games and
Windows developer utilities. Hardware and firmware have a contract: memory map,
UART/I2C addresses, power state, images and recovery. Both depend on the same
versioned platform ABI and brand identity. The host simulator is not a replacement
for the target BSP and drivers.

## 16x2 LCD status practice

`branding/identity.json` lists allowed boot-stage text. Do not display a fictional
progress percentage. Only show `READY` after the required F133/D213/FPGA and
cartridge-service checks actually pass or explicitly record degraded mode. Keep
visible fault codes for recovery. A powered LCD with no processor can show only
its module-defined splash, not valid NOR/USB/FPGA status.

## Hardware interface hold

The recommended F133 PB3/PB2 TWI0/I2C candidate is **not approved** until the
schematic symbols, real package pins, mux, 3.3-V domain, reset behavior and boot
conflicts are independently verified. Prevent connector hot-plug backfeed and
qualify display power consumption. No GPIO should be allocated merely because a
pin-name matrix marks it "spare".

## Windows 11-first follow-up

SDK 0.2.0 currently has Python entry, host simulator and curses UI. Native
Windows 11 execution, MSVC compiler flags, path behavior, and `curses` fallback
remain separate 0.3.0 engineering objectives; **this branding patch does not
claim to fix them**. Preserve a DOS/Windows-familiar layout with keyboard-first
navigation and readable error codes.

## Tests and release gates

1. Brand image source hashes agree with stored manifest (fail closed on edits).
2. All LCD text fits 16 ASCII characters per line.
3. Firmware C header successfully compiles as C11, separate from target boot.
4. `arc1 brand` passes CLI response schema and returns no hardware claim.
5. Existing host SDK tests do not regress.
6. Hardware LCD communication and HDMI splash can only be marked verified with
   first-article evidence. Flash writes remain disabled.
