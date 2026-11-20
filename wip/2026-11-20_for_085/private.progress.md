# private: progress (owner's own values out of the shared files)

## Done
- Classified (evidence gathered with look.py / look2.py in private/; counts only, nothing copied):
  - AH07_IDS (5 record ids + PDF sha) in fixture.py: (b), all found in the backup; the PDF's bytes and text differ from Workshop_datasheet.pdf.
  - test_kasandra.py:72 sheet id + expected_revision hash: (b), both in the backup.
  - 12 V, 280 mA, 3.36 W (84/25): (a) THINKPAD_FIRST_INSTALL.md "First-run workshop". 300 mA / 3.6 W: Rail Demo's own change.
  - 650 mA, 110 ms (bench CSV), Pulse duration 120/80 ms, "Up to 120/80 ms", Continuous limit 6 W, "At up to 8 W",
    finding texts "Settled draw is 3.36 W. Rev B allows 6 W.", "Startup ran 30 ms past the Rev B limit.",
    "What stretched the startup pulse?", titles 07 Bench readings / 07 Limits Rev A ARCHIVED / Rev B CURRENT / 07 Settled power /
    07 Startup power / 07 Case conclusion, 07_Bench_Readings.pdf, 07_Rail_Limits_Rev_B.pdf: (c), all in the backup.
- Design: P01 rewritten on Rail Demo's names (seed rail_demo); workspaces.after_hours_07 has "find" (kind + words), resolved
  in the child at run time (desk_scene.find_names); anchors find records by shape (cases_anchor.found).

## Next
- implement, copy, test, patch.
