exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
import os, time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QInputDialog, QPushButton, QLabel, QMenu
from workbench import chain_menu, chain_workbench_qt
files = Path(k.root) / 'Files'
L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,4,pcs\nC4,5,9,pcs\nU2,3,0,pcs\n'}, quiet=True)
L('files.write', {'path': 'stock2.csv', 'text': 'Part,Required,Available,Unit\nR9,7,1,pcs\nC1,2,2,pcs\nQ3,8,3,pcs\n'}, quiet=True)
L('files.write', {'path': 'stock3.csv', 'text': 'Part,Required,Available,Unit\nR9,7,1,reel\n'}, quiet=True)
print('=========== A. the chain tray (chain_workbench_qt): stage, preview, run, save with a source receipt')
prog = '@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | select Part,Short,Unit'
t = chain_workbench_qt.stage(w, prog); settle(20, 3)
print('   staged: visible=%s heading=%r status=%r chips=%s' % (t.isVisible(), t.heading.text(), t.status.text(), [t.chips.itemAt(i).widget().text() for i in range(t.chips.count()) if isinstance(t.chips.itemAt(i).widget(), QPushButton)]))
print('   tray object lives at host.chain_tray:', w.chain_tray is t, '| fields: program/rows/sources/seed/method/saved_receipt')
ok = t.preview(); settle(20, 3); print('   preview ->', ok, '| status:', t.status.text(), '| rows:', t.rows, '\n   sources:', short(t.sources, 500), '| seed:', (t.seed or '')[:16])
print('   run_chain ->', t.run_chain(), '| status:', t.status.text(), '| console.last_program == program:', w.console.last_program == prog, '| box:', repr(w.type_bar.box.text()[:60]))
rc = t.save_sheet(open_folder=False); settle(20, 3); print('   save_sheet -> receipt:', short(rc, 900)); print('   status:', t.status.text())
print('   in Files/Slate/Chains:', sorted(x.name for x in (files / 'Slate/Chains').glob('*'))[:6])
# the source changes after preview: does the tray notice?
t.preview(); L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,0,pcs\n'}, quiet=True)
print('   after the source changed: save_sheet ->', t.save_sheet(open_folder=False), '| status:', t.status.text())
L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,4,pcs\nC4,5,9,pcs\nU2,3,0,pcs\n'}, quiet=True)
print('\n=========== B. kept chains: the plain text file')
print('   menu_path():', chain_menu.menu_path(), '| exists:', chain_menu.menu_path().exists())
with patch.object(QInputDialog, 'getText', return_value=('Short parts', True)):
    chain_menu.keep(w, prog, 'sheet')
    t.program = prog; t.keep()     # the tray's "Keep as a method…" goes to the same place
print('   file now:\n' + '\n'.join('      ' + l for l in chain_menu.menu_path().read_text().splitlines()))
tree, problems = chain_menu.parse_menu(chain_menu.menu_path().read_text()); print('   parse_menu ->', tree, problems)
m = chain_menu.root_menu(w); print('   root menu items:', [a.text() for a in m.actions() if a.text()][:14])
print('   then(host, program, "sheet") runs a kept chain to its ending:'); chain_menu.then(w, prog, 'sheet'); settle(20, 3); print('      ', getattr(w.statusBar(), 'currentMessage', lambda: '')() or w.type_bar.message)
print('   a kept line that is not staC:'); print('      ', chain_menu.parse_menu('[chain] (Bad) {files.write {"path":"x","text":"y"}} then console\n[chain] (NoBraces) documents.list\n'))
print('\n=========== C. Method Press: keep a shortage method from selected rows, replay it on other rows')
from workbench.sheet_workbench_qt import Worksheet
def worksheet(rel):
    w.open_in_viewer(files / rel); settle(80, 6)
    found = [x for x in w.findChildren(Worksheet) if x.relative == rel]
    return found[-1] if found else None
ws = worksheet('stock.csv'); print('   worksheet for stock.csv:', ws is not None, '| shell2.worksheet is ws:', w.shell2.worksheet is ws if ws else None)
if ws:
    print('   fields:', ws.model.fields, '| stock_fields:', ws.stock_fields(), '| active_sheet:', ws.active_sheet)
    ws.grid.selectRow(0); settle(10, 2)
    sel = ws.grid.selectionModel()
    from PySide6.QtCore import QItemSelectionModel
    sel.select(ws.model.index(2, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows); settle(10, 2)
    rows = ws.rows_selected(); print('   rows selected:', rows)
    binding = (ws.active_sheet, rows); fields = ws.stock_fields()
    print('   program for the selection:', ws.program(binding))
    with patch.object(QInputDialog, 'getText', return_value=('Shortage in pcs', True)):
        ws.shortage_method(binding, fields)          # "Keep shortage method…"
    print('   menu file now:\n' + '\n'.join('      ' + l[:420] for l in chain_menu.menu_path().read_text().splitlines() if l.startswith('[')))
    methods = chain_menu.stock_methods(details=True); print('   stock_methods(details=True):', short(methods, 700))
    name, unit, saved = methods[-1]; method = dict(saved, name=name)
    # replay on the same sheet, other rows
    ws.grid.clearSelection(); ws.grid.selectRow(1); settle(10, 2); b2 = (ws.active_sheet, ws.rows_selected())
    ws.shortage_method(b2, fields, unit, method=method); settle(30, 3)
    print('   replay on row', b2[1], '-> tray program:', ws.tray.program[:200]); print('      tray status:', ws.tray.status.text(), '| rows:', ws.tray.rows, '| method bound:', ws.tray.method is not None)
    rc = ws.tray.save_sheet(open_folder=False); settle(20, 3); print('      save_sheet receipt:', short(rc, 1100)); print('      status:', ws.tray.status.text())
ws2 = worksheet('stock2.csv')
if ws2 and ws:
    ws2.grid.selectAll(); settle(10, 2); b3 = (ws2.active_sheet, ws2.rows_selected())
    ws2.shortage_method(b3, ws2.stock_fields(), unit, method=method); settle(30, 3)
    print('   replay on ANOTHER FILE (stock2.csv) rows', b3[1], '-> rows:', ws2.tray.rows, '| status:', ws2.tray.status.text())
    rc2 = ws2.tray.save_sheet(open_folder=False); settle(20, 3); print('      receipt source:', short((rc2 or {}).get('sources'), 400), '| output:', (rc2 or {}).get('output'))
ws3 = worksheet('stock3.csv')
if ws3 and ws:
    ws3.grid.selectAll(); settle(10, 2); b4 = (ws3.active_sheet, ws3.rows_selected())
    ws3.shortage_method(b4, ws3.stock_fields(), unit, method=method); settle(30, 3)
    print('   replay on rows with another unit ->', ws3.tray.status.text())
if ws:
    print('   saved runs folder:', chain_menu.method_runs(method), sorted(x.name for x in (files / chain_menu.method_runs(method)).glob('*')))
    S('files.list {"path":"%s"} | pick entries | select name,size' % chain_menu.method_runs(method))
print('   kernel operations named for this: none?', [o for o in CAPABILITIES if 'chain' in o or 'stock' in o or 'press' in o])
