# Source and archive checks

The release check verifies SHA256 for every distributed file except SHA256SUMS
itself, all five original attachment sizes/hashes, JSON parsing, required current
artifacts and the generated Word document's internal ZIP structure/image presence.
It requires a successful full host/HDL report. The ZIP is CRC-tested, its complete
membership compared, and every entry compared byte-for-byte with the source tree.

Build directories, Python bytecode/caches and Git metadata are excluded. Third-party
tool binaries, raw vendor workbook and proprietary EDA/IP are not in the source
tree. Historical original ZIPs remain byte-identical and may contain their own
historical generated artifacts.

Check an untouched extracted package before running tests:

```
python3 tools/check_package.py
```

Reproduction changes reports/build outputs. After intentional changes, regenerate
the source manifest and build a fresh archive outside the source tree:

```
python3 tools/check_package.py --write-manifest --create-zip ../ARC1_COMPACT_DEVELOPMENT_R05_2026-10-14.zip
```

The final release ZIP also has an adjacent SHA256 text file. Do not embed a ZIP's
own hash inside that ZIP. Archive integrity is independent of engineering validity;
these checks do not establish hardware fit, performance or manufacturing readiness.
