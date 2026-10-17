# ARC-1 Branding Integration — R01 (development-only)

Based on `arc1-sdk-0.2.0-dev.zip`; derived package intentionally retains
SDK version `0.2.0-dev` until the separately planned 0.3.0 work passes review.

**Implemented**: preserved R10 firmware/driver source snapshot, canonical brand identity manifest, original supplied logo and
case reference, CLI `arc1 brand` verification, shared firmware C header, 16x2
LCD boot-state contract, brand names in DOS UI, documentation, regression tests.

**Not implemented**: actual target firmware, I2C LCD driver, HDMI boot splash,
Windows 11 support, console launcher, USB game streaming, physical hardware
or NOR-writing support. No hardware readiness claim.

Run checks from root:

```
python arc1 brand --json
python -m unittest discover -s tests/branding -v
python tests/run_tests.py
```

For firmware header syntax test if a C compiler is available:

```
cc -std=c11 -Werror -x c -fsyntax-only -include firmware/include/arc1/brand.h /dev/null
```
