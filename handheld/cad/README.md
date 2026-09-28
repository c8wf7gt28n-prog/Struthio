# STRUTHIO Prototype A0 CAD

This folder contains an **engineering-envelope enclosure** for the Waveshare ESP32-S3-Touch-LCD-3.5B, not the final cosmetic CAD authority.

## Locked A0 numbers
- Shell: **88 x 128 x 25 mm**
- Front plate: **3.0 mm**
- Rear perimeter wall: **2.4 mm**
- Carrier envelope, portrait: **61.00 x 92.44 x 11.50 mm**
- LCD active area: **48.96 x 73.44 mm**
- Button centers: **x = +/-21.5 mm, y = -47.5 mm** relative to shell center
- Candidate switch footprint: **12 x 12 mm Omron B3F projected-plunger family**

## Important correction discovered during A0 packaging
Rotating the 92.44 x 61.00 mm Waveshare board into portrait places its onboard USB-C connector on an **internal short edge**, not at the external bottom of an 88 x 128 mm shell. A production-looking enclosure therefore needs either:
1. a short USB-C male-to-female panel extension to the bottom opening (modeled as the A0 direction), or
2. a later custom PCB.

Do not freeze the final USB-C geometry until the actual cable/extension is selected.

## Export
```bash
openscad -o stl/struthio_a0_front.stl -D 'part="front"' struthio_a0_enclosure.scad
openscad -o stl/struthio_a0_back.stl -D 'part="back"' struthio_a0_enclosure.scad
openscad -o stl/struthio_a0_left_button.stl -D 'part="left_button"' struthio_a0_enclosure.scad
openscad -o stl/struthio_a0_right_button.stl -D 'part="right_button"' struthio_a0_enclosure.scad
```

## Print intent
First print should be a **fit test**, preferably PLA at 0.20 mm layers. Do not spend time on surface texture or branding until:
- carrier slides in without flexing the display,
- both button caps move freely,
- the chosen switches sit at the correct Z height,
- speaker/battery volumes do not collide,
- USB-C extension route is proven.

The `SWITCH_PCB_PLANE_Z` parameter is deliberately exposed for quick shimming/tuning after the first physical switch is measured.

## Mesh validation
The exported A0 STLs were re-generated after the internal supports were fused into the rear wall and the speaker slots were shortened to avoid isolated plastic islands. After normal STL vertex welding, all four print files validate as **watertight, single connected solids**. They are still fit-test geometry: slice preview and real printer tolerances remain part of the A0 gate.
