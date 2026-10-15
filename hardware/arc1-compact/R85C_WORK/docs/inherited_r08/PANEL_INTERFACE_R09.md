# Panel interface: deferred to R09 (corrective handoff §8.1, D-07)

R08 does **not** select a panel, pixel clock, FFC footprint, LCD supply or backlight driver. It preserves the following.

## MN820 CN1 signals reserved for the panel (no-connect in the R08 schematic, J3)

| CN1 pin | Signal | R09 net (proposed) |
|---|---|---|
| 59 / 57 | LVDS_TX0_D0_P / _N | LVDS0_D0_P/N |
| 63 / 61 | LVDS_TX0_D1_P / _N | LVDS0_D1_P/N |
| 67 / 65 | LVDS_TX0_D2_P / _N | LVDS0_D2_P/N |
| 71 / 69 | LVDS_TX0_CLK_P / _N | LVDS0_CLK_P/N |
| 75 / 73 | LVDS_TX0_D3_P / _N | LVDS0_D3_P/N (24-bit panels only) |
| 81 / 79, 85 / 83, 89 / 87, 93 / 91, 97 / 95 | LVDS_TX1 D0, D1, D2, CLK, D3 (even channel) | dual-channel panels only |
| 62 | DISP | panel enable |
| 64 | BKLIT_PWM | backlight driver PWM |
| 68, 70, 72, 74, 76, 78, 80 | GPIO3, GPIO2, GPIO4, GPIO6, GPIO5, GPIO7, GPIO8 (GPIO5–8 = touch SCL/SDA/INT/RST on the VM820C) | touch / panel control |

BT820 LVDS (DS v1.1):
- 2 channels × (4 data + clock), up to an 83.2 MHz pixel clock, 247–454 mV differential, 1.125–1.375 V common mode.
- Channel 0 = odd pixels; single-channel panels use channel 0 only.

## Allowances already in R08

- 3V3 and VBUS_5V budget (panel and backlight are excluded and must be added: RK-USB-BUDGET).
- Route class "LVDS 100 Ω" in MANUFACTURING_AND_BGA_PLAN.md.
- The receptacle footprint is placed so that both LVDS channels can leave on L1.

## R09 must

1. Select the panel and archive its datasheet.
2. Add the FFC connector, LCD supply and backlight driver (TPS61165 from SLIM4 is a candidate only).
3. Re-run ERC, the cross-check and the budget.
4. Update the BT820 timing (`bt820_timing_candidate_1024x600` is a candidate only).
