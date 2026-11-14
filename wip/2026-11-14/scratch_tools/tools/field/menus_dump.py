top = w.shell2.top; settle(200, 3)
def lines(menu, depth=0):
    menu.aboutToShow.emit(); out = []
    for a in menu.actions():
        if a.isSeparator(): continue
        text = a.text().replace('&', '').split('\t')[0]
        if a.menu() is not None and depth < 1: out.append(text + ' ▸ [' + ' | '.join(lines(a.menu(), depth + 1)) + ']')
        else: out.append(text + (' ▸' if a.menu() is not None else ''))
    return out
for b in top.bar_menus: print('== %s: %s' % (b.text(), ' | '.join(lines(b.menu()))))
