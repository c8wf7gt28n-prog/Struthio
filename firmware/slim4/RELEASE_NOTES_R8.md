# R8 — power-policy corrections from the R7 review

The R7 review compiled `slim4_power.c` on a host and reproduced three defects. All three are fixed, and the scenarios are now a test in the tree (`sh tests/host/run.sh`, 29 cases, any C compiler).

- **Low-battery switch-off did not happen on its own.** `slim4_power_poll()` returned early while the power button was released (or not yet re-armed) and never reached the `battery_low` test. The low-battery decision now comes first. It needs 2 s of valid readings below 3.3 V on the battery, so a load step does not switch the board off; a failed reading never does.
- **The thermal charge suspend could start below its own 3.6 V floor.** Entry now needs a qualified cell (charging, no fault, valid reading ≥ 3.5 V for 2 s) at or above 3.6 V. It ends when the die cools below 65 °C, the cell falls below 3.6 V, the reading fails or USB goes away. While suspended, the backlight is capped at 15 %.
- **CHG low alone lifted the USB backlight cap,** including with a battery fault or a cell in pre-charge. The cap now lifts only for a qualified cell (as above), with hysteresis: it returns below 3.4 V, when charging stops, on a fault or a failed reading.
- The review's own harness, run unchanged on R8, passes six of its seven cases. The seventh expects a switch-off after a single 3.2 V reading; R8 deliberately waits 2 s (the review also asked that transient dips not switch off). R8's test covers the switch-off with the button released and held.
- Documents no longer promise "no damage" for a reversed pack on USB: the 4–11 mA figure is a steady-state design analysis, not a tested result, and the warning does not disconnect the pack.
