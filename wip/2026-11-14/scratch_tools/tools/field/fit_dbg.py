w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle()
body = v.body(); print('body', body.width(), body.height(), '| fit says', v.fit())
QTest.keyClick(v, Qt.Key_Z); settle(200, 4); print('Z: zoom', v.zoom, '| far (map):', v.zoom < v.FAR, '| whole:', v._fitted); save('Fit_%s.png' % tag)
body = v.body(); wide, high = v.room(); print('surface', v._surface, 'room', (round(wide), round(high)), '| runs off:', v._surface[0] > wide + 1 or v._surface[1] > high + 1)
