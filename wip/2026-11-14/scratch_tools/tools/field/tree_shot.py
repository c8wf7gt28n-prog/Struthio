tree = w.cabinet_page.tree; tree.expandAll(); settle(200, 3)
items = []
def walk(item):
    for i in range(item.childCount()):
        c = item.child(i); items.append(c); walk(c)
for i in range(tree.topLevelItemCount()):
    t_ = tree.topLevelItem(i); items.append(t_); walk(t_)
deep = [it for it in items if it.parent() is not None and it.parent().parent() is not None]
target = deep[min(len(deep) - 1, 3)] if deep else items[-1]
tree.setCurrentItem(target); settle(300, 4)
print('current:', target.text(0), '| rows:', len(items))
g = w.left_pane.grab() if hasattr(w, 'left_pane') else tree.window().grab()
g.save(str(OUT / ('Tree_%s.png' % tag))); save('Tree_Window_%s.png' % tag)
