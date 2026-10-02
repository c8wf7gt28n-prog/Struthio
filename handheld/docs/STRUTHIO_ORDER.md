# STRUTHIO ONE SLIM: what to order

Everything for one handheld, in one list. Order the four groups at the same time; the board from JLCPCB takes
the longest (about one to two weeks).

## 1. Buy

| ☐ | Qty | Part | Exactly what | Where |
|---|---|---|---|---|
| ☐ | 1 | Screen board | **Waveshare ESP32-S3-Touch-LCD-3.5B**: the bare board, not the "-C" version in a case. Its speaker lead comes with it | Waveshare's shop, or search the exact name |
| ☐ | 1 | Battery | LiPo pouch **302535**, 3.7 V, about 250 mAh, **with protection board**, **JST PH 2.0 mm 2-pin plug**, lead 60–100 mm. 3.0 × 25 × 35 mm (about 38 mm long with its board) | Search "302535 250mAh PH2.0". Sellers list it as 200 to 250 mAh: either works |
| ☐ | 1 | Speaker | **Same Sky (CUI Devices) CMS-151125-078SP**: 15 × 11 × 2.5 mm, 8 Ω, 0.7 W (the -67 version is the same speaker, waterproofed) | Mouser, DigiKey |
| ☐ | 5 | Screws | **M2 × 6 countersunk** (flat head), ISO 10642 or DIN 965. All five are the same | Any screw shop; a mixed M2 kit works |
| ☐ | 1 | Header | One strip of **2.54 mm male header pins**, single row, 40 pins (you use 12) | Any electronics shop |
| ☐ | 1 | Foam tape | **Double-sided foam tape, 1.0 mm thick**, about 20 × 30 mm | Hardware store |
| ☐ | 1 | Cable | **USB-C data cable** (many cables only charge: a data cable is the one that came with a phone) | |

## 2. Order the board (JLCPCB)

From package 3, folder `ONE_SLIM`:

1. jlcpcb.com → Order now → upload `struthio_one_slim_gerbers.zip`.
2. **PCB Thickness: 0.8 mm** (not the default 1.6). Everything else as it is.
3. Turn on **PCB Assembly**, top side. Upload `BOM_JLCPCB.csv` and `CPL_JLCPCB.csv`. Six parts, all surface-mount:
   four buttons (SW1–SW4), the battery socket (J2), one transistor (Q1). The header pins are not on it: you fit them.
4. In the placement preview: J2's opening faces the board's **right** edge. Rotate a part in 90° steps if it does not.

## 3. Print the case

From package 4, folder `ONE_SLIM`: front shell, back shell, two wing buttons, rocker, power button, pin jig,
panel jig. And an 11 mm piece of 1.75 mm filament for the rocker's axle (the pin jig has a slot that cuts it to length).

- **Your own printer:** PETG (or ASA), 0.2 mm layers, 4 walls, 6 top and bottom layers, 40 % infill. Not PLA.
- **No printer:** upload the STLs to a print service (JLCPCB's 3D printing, or any local one). Ask for **MJF nylon
  (PA12)** or **PETG**: both are tough enough. Resin (SLA) prints are too brittle for the screw bosses.

## 4. Order the face panel

From package 2. Send a laser-cutting and UV-printing shop the files and this sentence:

> 1.0 mm clear cast acrylic, cut to the DXF, reverse-printed (colour, then white) from the mirrored PNG, window left
> clear. Please laminate clear adhesive transfer tape (3M 468MP or equal) on the back, except over the window.

The adhesive makes fitting it peel-and-stick. Cheaper: a clear cut panel and the art printed on sticker vinyl, stuck on its back.

## Tools

A small Phillips screwdriver (PH0), a soldering iron and solder (for the 12 header pins and the 2 speaker pads), flush
cutters, a paperclip. A computer with a USB port.
