# Graphite 0.2a5 · BOSS P10

Ten of the twenty BOSS implementation passes are in this build. The new route takes a collection from Ingress through project search, then turns a reviewed PDF table into a sheet and an editable report.

## P08 · Keep a model ready

Use **Brain → Use model** to activate a registered GGUF. Graphite checks the weight file at load and binds that check to the running worker and the file's identity. Each turn checks that identity before using the worker. The Brain view shows the effective context, backend and fallback reason when available. **Restore previous** uses the saved model handover record. Stop invalidates earlier launch and rollback requests.

A source question can reuse the prepared prompt budget when the same owner asks the exact same question with the same frozen evidence on the same worker. Graphite asks the runtime to reuse its single resident slot and reports reused tokens only when the runtime supplies that count. Another turn, changed evidence or a replaced worker makes the next preparation start cold. Source records and work history live with the project.

## P09 · Give a project its sources

1. Bring a folder in through **Intake** and review the sources in **References**. Choose **Index admitted sources** to make those files searchable.
2. Open **Project Desk → Project notes → Attach collection…** and pick the collection. **Open collection** brings it back for review. **Ask Graphite → Prepare evidence** finds matching indexed passages with their source locations.
3. Choose **Export collection** in References for a ZIP in Egress. It contains ordinarily named source files, a readable collection summary and a catalog of source and project relationships. The summary lists omitted material. The collection and its export are useful with the Brain off.

The native export view publishes the verified ZIP when the worker finishes. A caller using registered operations can publish the completed export with `references.volume.publish`.

## P10 · Make a checked report from a datasheet

1. Select an admitted source in **References → Read technical PDF**. Select the table region and open **Review table**. For an image-only page, use the PDF view's OCR first.
2. Compare the candidates with the original crop. Fix values and units, retain the conditions, and choose **Save reviewed sheet**. The saved sheet keeps the PDF page, extraction notes and the reviewed values.
3. In the sheet, choose **Calculate and write report…**. For example, name the input cells `voltage=B2` and `current=B3`, enter `voltage * current`, and request watts. Give dimensionless values the explicit unit `1`. A missing unit needs a decision before the calculation runs.
4. Open the result in **Documents**. Edit or export it as you would any other document. **Sheet** and **Source page** reopen the inputs. When a selected value changes, Graphite marks the report for recheck. **Recheck** writes a new report from the current sheet and keeps the earlier one.

The review works on a selected table region with a bounded row layout. OCR and unusual tables can leave entries for you to resolve. The report carries both the reviewed source values and any later sheet edits.

## What ran here

- The model protocol check exercised a cold turn, a matching reuse request, a changed weight file and Stop during an earlier launch request. Live GGUF reuse, Radeon performance and ThinkPad operation are pending.
- A local test collection went through real Ingress, review, indexing, project search and verified Egress export. The exported source bytes matched the admitted originals.
- A native Qt walkthrough opened a text PDF table, an image-only page with real OCR, the editable sheet and the report. Exact local arithmetic gave **2.4 W** from **12 V × 200 mA**. Changing the sheet to **250 mA** marked the old report for recheck. The next report gave **3 W**.

See [the walkthrough observations](P10_captures/P08_P10_OBSERVATIONS.json) and the [table review](P10_captures/Graphite_P10_PDF_Table.png) and [report](P10_captures/Graphite_P10_Report.png) captures.

P11 connects full native programs to the desk and brings the owner back to the same work after an explicit handoff.
