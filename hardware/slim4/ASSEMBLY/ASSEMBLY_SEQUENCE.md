# R28 assembly sequence (PCB R23; CASE R12 set aside)

`STRUTHIO_SLIM4_R28_ASSEMBLY.step` holds the R23 board envelopes with CASE R12 and ACRYLIC R2 as they are. PCB solids in it are envelopes derived from the PCB layer JSON (board outline, part courtyards × heights from `CHECKS/COMPONENT_ENVELOPES_R23.json`); the KiCad file remains the PCB authority. The case does not fit the 5 in panel yet (`PRODUCTION_GATES.md`), so the sequence below is the bench build of the board and its four plug-in parts.

## Bench build (no case)

1. **Board on the bench, back side up.** Plug the speakers into J4 (left) and J5 (right), pin 1 +. Check the cell's plug: red lead to pin 1 (BAT+). Plug it into J3 at the battery window's left edge; lay the cell in the window. (A reversed pack leaves the board off: Q2 blocks it.)
2. **Turn the board front side up.** Put 3–4 mm foam spacers on the board front where the panel will rest, clear of J1 and SW1–SW4.
3. **Panel.** Fold its tail once behind the module and plug it into J1, contacts up, as `LAYERS/01_PCB/DISPLAY_PORT.md` shows (panel face up, its bottom edge toward the board's bottom edge). Close J1's latch. The panel rests on the spacers, bottom edge at Y 109.8, overhanging the board's top edge by 13.6 mm.
4. **USB-C.** Connect to a computer and flash `firmware/slim4` (`idf.py -p <port> flash monitor`; first time: hold BOOT, tap RESET). Work through `firmware/slim4/docs/FIRST_BOOT.md`.

## In a case

The R12 sequence (rear shell, speakers in their chambers, board, screen into the front shell, controls, close with the lap tape, then film) still applies to the case design, but the screen and route steps change with the case pass: the panel's tail now folds behind it into J1 on the board front, so the panel is plugged in before the front shell closes over it.
