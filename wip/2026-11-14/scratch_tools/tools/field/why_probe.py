from workbench.engine import engineering
k = engineering(w.root)
r = k.dispatch('field.doubt', {}, operator())
for row in r['result']['rows']:
    print(row['verdict'], '|', row['about'], '|', len(row['why']), '|', row['why'])
