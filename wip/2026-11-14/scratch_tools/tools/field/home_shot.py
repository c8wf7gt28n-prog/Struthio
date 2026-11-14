w.a_home.trigger(); settle(400, 6); align()
today = w.findChild(__import__('workbench.shell2', fromlist=['TodayPage']).TodayPage)
print('columns', today.columns, '| art', today.art.height(), 'limit', getattr(today.art, 'limit', None), '| cards min widths', [c.minimumSizeHint().width() for c in today.cards], '| room', today.width())
save('Home_%s.png' % tag)
