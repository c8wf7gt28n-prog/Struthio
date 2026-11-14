from workbench.engineering_kernel import operator
w.a_field.trigger(); settle(300, 4); v = w.field_page.view; k = w.ledger_bridge.kernel
for o in v.field.objects:
    if o.kind == 'sheet':
        tgt = o.target or {}
        print('SHEET', o.title, '|', o.role, '|', tgt)
        if tgt.get('kind') == 'office':
            r = k.dispatch('office.get', {'id': tgt['id']}, operator())
            res = r.get('result') or {}
            rows = (res.get('origin') or {}).get('reviewed_rows') or []
            print('  rows', len(rows), [ {kk: row.get(kk) for kk in ('sheet_row','parameter','value','unit','conditions')} for row in rows][:8])
            doc = res.get('document') or {}
            cells = ((doc.get('sheets') or [{}])[0].get('cells') or {})
            print('  cells', {c: (cells[c] or {}).get('value') for c in list(cells)[:14]})
print('REV DONE')
