w.a_field.trigger(); settle(); v = w.field_page.view
s = v.scale(); cols = len(v.field.ranks()); need = cols * v.least_width() + max(0, cols - 1) * 22 * s + 2 * 16 * s
print('appearance', __import__('workbench.boss_theme', fromlist=['x']).APPEARANCE, '| view', v.width(), 'x', v.height(), '| columns', cols, '| needed', round(need), '| rail', v.rail())
w.left_pane.hide() if hasattr(w, 'left_pane') else None; settle(200, 4); print('without the left pane: view', v.width(), '| rail', v.rail())
