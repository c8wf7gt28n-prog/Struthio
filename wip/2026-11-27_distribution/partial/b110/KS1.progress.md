# KS1 progress (builder notes)

## Design (decided)
- workbench/box_ops.py: narrow box.* Kernel ops (reads: box.files.find, box.space, box.memory, box.processor, box.system, box.pdf.info, box.zip.list, box.bin.list; changes execute: box.pictures.make, box.pdf.merge, box.pdf.split, box.zip.make, box.zip.extract, box.folder.copy, box.files.rename, box.files.sort, box.files.bin; approve: box.bin.empty). Each: plan() pure, act, verify, undo record in table box_changes.
- workbench/recipe_book.py: recipes from workbench/recipes/*.json + ~/.config/graphite/recipes/*.json; slot types; dictionary pick; RECIPE turn kind (model picks by number, slots only from W-numbered spans of the owner's words); dry run digest; run (execute, refuses her work / HALT); undo (approve). Ops recipes.list/pick/dry_run/look/runs (read), recipes.run (execute), recipes.undo (approve).
- workbench/recipe_book_qt.py: her talk bubbles (offer, dry run + Run, done-and-verified + Undo, Recipes list, one question).
- Edits (marked 1.1 KS1): engineering_kernel.py, engineering_cli.py, shell2.py ask chain (before objective_asked), her_column_qt.py next_steps/take_step, line_finder.py rows/VERBS, kas_voice.py lines.
- Zip via stdlib zipfile; PDFs via poppler-utils (pdfunite/pdfseparate/pdfinfo); pictures via ImageMagick (magick or convert).

## Done
- box_ops.py, recipe_book.py, workbench/recipes/01..40 (written by scratchpad make_recipes.py), Kernel + CLI registration.
- smoke.py in copy: 40 load, reads look verified, 7 change runs + undo verified (convert, resize, zip, sort, merge, ...).

## Half done / next
- fixed after smoke: file slot tails, rename spans; re-run smoke
- recipe_book_qt.py (her talk), shell2 ask chain hook, her_column next steps, line_finder rows, kas_voice lines
- tests_integrated/test_recipes.py, frames, result JSON
