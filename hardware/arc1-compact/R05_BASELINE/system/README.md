# T35F400 manufacturer package source audit

`T35F400_package_source_facts.csv` contains the official workbook's T35F400
columns A-H plus the original worksheet row and an empty `board_net` field.
`extract_t35_package.py` extracts those source facts using standard-library
ZIP/XML parsing. The raw manufacturer workbook is not bundled; its download URL
and SHA256 are recorded in `package_source_report.json`.

An independent read-only comparison used **openpyxl 3.1.5**, rather than the
extractor's implementation. It read all 400 ball records directly from the
workbook and compared all 3,200 A-H field values and original row numbers with
the CSV. All matched. Independently recomputed counts, per-bank counts and the
workbook SHA256 also matched the report. The method, results and current artifact
hashes are preserved in `source_audit_verification.json`; no broad tests were
rerun to create that record.

The inventory has 400 unique source balls, 230 GPIO-named entries, 54 DDR
annotations, 138 DDIO-Yes entries and 92 LVDS annotations. **These annotations
overlap; these counts are not an available-pin budget.** All 400 `board_net`
fields are blank, so this artifact assigns zero board nets. It does not establish
electrical closure, DDR routing, Efinity acceptance, timing closure or hardware
operation.

Source workbook SHA256:
`11dc7a00d71cc378cfc02f6a16159228b533f7f9bb3438f13dc3f23730af00dd`.
