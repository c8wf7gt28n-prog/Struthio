# Prototype A0 pinout and wiring lock

## Wing buttons
Use the board's exposed general-purpose GPIOs:

- **LEFT WING -> GPIO17** (Waveshare expansion header pin 16 in the published 2x16 pinout image)
- **RIGHT WING -> GPIO18** (header pin 18)
- other side of both switches -> **GND** (for example header pin 30)

Firmware configures GPIO17/GPIO18 as inputs with pull-ups. Pressing a button pulls the line LOW.
The lines are sampled at 1 kHz and debounced for 8 ms. Each press is stamped at its raw edge, so the 100 ms chord window measures real thumb timing.

No extra wiring for DART: trial C (the v0.5 default) is both wings held for 200 ms.

GPIO17 and GPIO18 are preferred for A0 because the board publishes them as exposed GPIOs, while GPIO0/45/46 are boot strapping pins and GPIO19/20 are native USB.

## Candidate switch
**Omron B3F-4050** projected-plunger 12 x 12 mm through-hole tactile switch is the first feel-test candidate. Omron specifies 7.3 mm height and 1.27 N operating force for B3F-4050. The related B3F-4055 shares the general projected-plunger mechanical family and gives a firmer alternative. Do not call either final until a real thumb test is performed through the printed STRUTHIO caps.

## Speaker
For the first audio test, use an **8 ohm, ~1 W mono speaker around 28 mm diameter**. The board uses an NS4150B mono Class-D amplifier; its published characteristics include 4-ohm and 8-ohm loads. Keep firmware gain low on first power-up.

## USB-C
The board USB-C is needed for easiest flashing/charging. In portrait packaging it is internal to the handheld footprint. A0 CAD therefore reserves a bottom opening for a **short full-data USB-C male-to-female panel extension**. Bench A0 may be run with the rear shell off until an extension is chosen.

## Service access
Keep BOOT/RESET/PWR reachable during bring-up. Normal gameplay should expose only power; BOOT and RESET become recessed service access later.
