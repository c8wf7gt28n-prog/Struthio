# Schema migration notes

Schema 0.x allows documented breaking changes (spec §12.1). Each one is listed
here with what a manifest author has to change.

## arc1.hardware/0.2 → 0.3 (ARC1-PASS-0002)

Why: ARC1-PASS-0001 transcribed the hardware from the requirements document
only. The owner's R10 handoff supplies real part numbers, links and decisions,
and HW-001 requires each fact to say where it comes from.

| Change | What to do |
|---|---|
| `schema` is `arc1.hardware/0.3` | Update the constant. |
| New required `fabrication_status`: `HOLD`, `RELEASED` or `NOT_APPLICABLE` | Board manifests use `HOLD` until a physical boot is recorded with board evidence. Simulation descriptors use `NOT_APPLICABLE`. |
| New required `sources[]` with `id`, `path` (from the SDK root), `sha256`, `kind`, `description` | Vendor each cited file unmodified and list it. The validator re-hashes it. |
| `datasheet_ref`, `wiring_source`, memory `source`, peripheral `source` and link `sources[]` are references | Write `id` or `id#anchor`. The id must be a source and the anchor text must occur in that file. |
| New required `peripherals[]` | Non-processor parts that matter to software (flash, HDMI transmitter, hubs, regulators with software-visible behaviour). `[]` is allowed. |
| Links require `sources` and `notes`; endpoints may name a peripheral | Board links need at least one source. |

No conversion tool is provided: the only two manifests were rewritten by hand
in the same pass. `arc1.hardware/0.2` documents are now rejected with a SCHEMA
error naming `/schema`.
