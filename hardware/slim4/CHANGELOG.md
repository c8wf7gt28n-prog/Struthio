# R24 change log

- Kept the R21 native KiCad board byte-for-byte unchanged and placed it in the PCB parent folder with its project and local footprints.
- Separated the R10 front enclosure/screen/control solids from the clear acrylic face film into standalone CASE and ACRYLIC layers.
- Added STEP/STL per parent, 2D SVG/DXF sticker cutline, platform-neutral geometry JSON, shared-coordinate documentation, and repeatable CadQuery export sources.
- Split the PWA mesh data by CASE and ACRYLIC parent so the studio viewer reads separate parent-layer files.
- Retained R3 and the mixed R10 STEP assembly only as clearly labeled reference material.
- Added AI handoff guidance, production gates, file manifest, and checksums.
