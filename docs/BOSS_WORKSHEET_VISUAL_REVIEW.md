# Graphite worksheet visual review

The Workshop Stock mockup depicts a worksheet mid-task. The first running screenshot was an editable calculation report. To separate the design differences from the different work, the comparison below uses the same real ODS workbook in P10 and in the revised desktop. The example rows belong to the walkthrough.

## Screen comparison

| Area | P10 on the same workbook | What the mockup calls for and how the revision handles it |
| --- | --- | --- |
| Whole screen | Three panes already line up between the full-width bands. | Keep the three panes and make the work easy to follow from the source at left through the table and into the result at right. The two outer panes still share the same width and sizing rules. |
| Background | A cooler graphite gray under darker head and foot bands. | Use near-black charcoal with warm gray rules and cream text. Keep enough separation between the background, table header and raised menus to read each surface. |
| Head | The actual path is editable and the three menus are already at the right. | Keep the real path on the band. Use a thin amber rule and a character-cell grid beside Programs. Work and System have ordinary words. |
| Colors | Muted copper selection, cool text and green monitor readings. | Give amber the active row, cascade, route and Run chain. Give green the verified preview and source state. Include words and row marks alongside the colors. |
| Lettering | The path is mono. The sheet, pane tabs and most labels are sans. | Set the worksheet data, pane tabs, and cascade in IBM Plex Mono. Long-form document reading has its own font and size. |
| Left tabs | Files, Machine and Settings already exist. | Keep those three destinations with sharper lettering and a short underline. |
| File tree | The logical cabinet shows the Concern categories. The workbook's siblings are absent. | Put the actual containing folder and its files above the cabinet while the worksheet is active. Put the active workbook first and mark it with amber. Keep the underlying cabinet reachable. |
| File icons | The logical tree is mostly words with branch lines. | Add one-line ASCII type marks to the worksheet folder. The filenames and accessible file types carry the meaning. |
| Left margin and Trash | Space beneath the cabinet and a pinned Trash. | Add a small bracket sketch drawn with keyboard characters for the stock worksheet. Fit it above the existing Trash, which keeps its real count and drop target. |
| Workspace heading | The filename repeats in the address, breadcrumb, viewer heading and tabs. | Give the worksheet one title and a line that counts the selection. File views holds the original sheet, Hex, Details, Ask and Investigate. |
| Full spreadsheet | The viewer shows its normal file actions. | Put Full spreadsheet by the title. It opens the file in the system's associated application when there is one. |
| Sheet headings | A, B, C and D sit above a grid containing the heading row as data. | Make Part, Required, Available and Unit the headers in Worksheet. This is the existing staC data view of the file. The original sheet view remains reachable through File views. |
| Table width and density | The small table sits in the upper left with a separate filter field. | Stretch a small number of columns across the working area, right-align quantities and use fine grid lines. Wide tables can scroll. The original sheet view still offers sort and text filter. |
| Selection | The viewer can focus a cell. | Select whole rows, including nonadjacent rows, with native Qt keyboard and pointer selection. Amber and a greater-than mark identify the selected rows. |
| Cascading commands | The established chain menu starts from a file or existing chain. | Open a cascade from the current rows. In the stock example, choose Calculate, Required - available, then Keep positive. The named stock route appears when those columns are present. Any supported table can preview its selected rows or copy them as staC. |
| Connection from selection | Selection and chain are separate visual surfaces. | Draw an amber trace from visible selected rows to the tray and mark the chip and Run control positions. The trace follows selection, scrolling and layout. The actual popup remains a Qt menu. |
| Constructed chain | A general chain tray can appear beneath the active workspace. | Stage the actual bound program beneath the worksheet. The chips show selected rows, subtraction, filter and output. Each chip can put its prefix into the shared typing line. The menu retains the existing method and console routes. |
| Run and output | A chain can preview, show its result in the console or save a CSV. | Put Run chain at the end of the route. It uses the inspected result and writes a new CSV and a source receipt. The worksheet stays open so the result can be read next to its inputs. |
| Right tabs | Talk, Activity and Context. | On a worksheet use Preview, Activity and Sources. Talk is reachable from the preview and the typing line. Ordinary views get their normal inspector back. |
| Preview card | Activity and Timeline occupy the right while a general chain preview lives in the tray. | Show the real result at right with two columns for the stock recipe. Print the unit beside each amount. Show a total only when the contributing units agree. |
| Ready and stale | The general chain records its sources and checks them before use. | Bring the current-source state to the preview. The selected sheet and source digest travel with the program. Changing the file clears readiness, and a run or save rechecks the digest. |
| Panel artwork | A general illustrated header or text treatment exists on Today. | Put the original woman at a CRT below a ready result. Illustrated shows the halftone. ASCII renders the portrait in character cells. Clean removes both illustrations. The actual source label supplies the state. |
| Bottom strip | Assistant, Terminal and Log already share the line with real resource monitors. | Add compact prompt and log glyphs and the amber seam. Keep the readouts live. The mockup's sample ready badge is expressed by the worksheet's actual verified state. |
| Decoration and fit | Dock widths, text size and shortcuts are part of the running desk. | Use a static, sharp treatment with actual controls. Menus can move or flip to stay in the available screen area. The app uses its real path, files, tooltips, focus and size rules. |

## How to see it

1. Put a CSV, ODS or XLSX file in the workspace's **Files** folder or a subfolder. Open it through the viewer or enter its full path in the head.
2. In **Worksheet**, select rows. Use Ctrl to select rows apart from one another. Right-click the selection or choose **Row commands**.
3. With numeric Required and Available columns and Part and Unit headings, choose **Calculate → Required - available → Keep positive**. The chain previews on the right. Use **Run chain** to save the derived CSV and its receipt in **Files/Slate/Chains**.
4. **File views** opens the original workbook views. **Full spreadsheet** hands the file to the desktop's associated application. **Reload source** reads current bytes and starts a fresh selection. Set the ornament under **Work → Arrange → Desk artwork**.

The result uses Graphite's bounded file view and existing staC runner. The worksheet route is for files inside **Files**. The editable Office working-copy and P10 PDF-to-report routes have their own controls. Full application handoff and return are P11.

## Observed in Qt

The same workbook opened in both versions. The revised desktop selected Bracket A and Shade, opened the three native cascading menus, and previewed **40 pcs + 22 pcs = 62 pcs**. Run chain saved the two rows and a receipt bound to the source. A change to the workbook bytes refused the old program and cleared the ready state. The preview also opened at 1366 × 768, and Illustrated, ASCII and Clean were exercised. The cascade image places the visible Qt popups over the window capture at their actual positions.

| Capture | What to inspect |
| --- | --- |
| [P10 workbook](BOSS_worksheet_captures/Graphite_P10_Workshop_Before.png) | The old header, table and Activity placement with the same file. |
| [Worksheet and cascade](BOSS_worksheet_captures/Graphite_Workshop_Cascade.png) | Row selection, connected commands, staged chain and live result. |
| [Compact view](BOSS_worksheet_captures/Graphite_Workshop_Compact.png) | The same working surface at 1366 × 768. |

These are offscreen Qt observations. Display comfort and the system's external spreadsheet launcher await the ThinkPad.
