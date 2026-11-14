exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from workbench.typebar_qt import stac_hint_kind
INV = 'c574ae94d79542f582932d151fad631f'
def T(text, note=''):
    print('\n[hint kind: %r]' % stac_hint_kind(text), end='')
    return S(text, note)
print([ (o, CAPABILITIES[o]) for o in sorted(CAPABILITIES) if o.startswith('office.') and CAPABILITIES[o]=='read'])
L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,4,pcs\nC4,5,9,pcs\nU2,3,0,pcs\n'})
L('files.write', {'path': 'prices.csv', 'text': 'Part,Price\nR1,0.02\nU2,4.5\n'})
L('files.write', {'path': 'stock2.csv', 'text': 'Part,Required,Available,Unit\nR9,7,1,pcs\nC1,2,2,pcs\n'})
print('=========== B. tables: add, where words, join, missing, aggregates, keep rows')
T('@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | select Part,Short,Unit', 'the shortage chain')
T('@files:stock.csv | rows | join @files:prices.csv rows on Part | add Cost = Required * Price | sum Cost', 'join + add + sum')
T('@files:stock.csv | rows | missing @files:prices.csv rows on Part', 'missing')
T('files.get {"path":"stock.csv"} | rows | keep rows 1,3 | where Unit=pcs | count', 'keep rows / equality / count')
T('@files:stock.csv | rows | where Part has r | sort -Required | take 1', 'has')
T('@files:stock.csv | rows | where Required at least @Available', '@Field compares two columns')
print('=========== C. explain')
T('explain @files:stock.csv | rows | add Short = Required - Available | where Short over 0')
T('explain desk')
T('explain explain desk')
print('=========== D. stac.run start words')
for line in ('desk', 'desk | find sheet', 'atlas | find csv', 'algorithms', 'algorithms | find shortage', 'inquiries', 'library x | search volt | take 2', 'investigation %s | inspect' % INV, 'investigation %s | why' % INV, 'use something'):
    T(line)
print('=========== E. what a line may start with: aliases, and operations by scope')
for line in ('jobs', 'models', 'activity | take 2', 'agenda.view | pick waiting | select kind,title', 'matrix.patterns | pick patterns | select shape,tries,success'):
    T(line)
print('=========== F. refusals: staC only reads')
for line in ('files.write {"path":"x.txt","text":"y"}',
             'agenda.add {"title":"t","program":"jobs"} | take 1',
             'agenda.run_next',
             'stac.observe {"program":"desk"}',
             'language.run {"text":"jobs"}',
             'stac.inspect {"program":"jobs"}',
             'stac.run {"program":"desk"}',
             'documents.list > out.txt',
             'documents.list ; jobs',
             'documents.list | pick documents | where words > 100',
             'documents.list | pick documents | $(x)',
             'documents.list | take 1 | take 1 | take 1 | take 1 | take 1 | take 1 | take 1 | take 1',
             'documents.list | frobnicate',
             'documents.list | pick documents | set x = 1',
             'nonexistent.op',
             'documents.get',
             'documents.get {"id":"218f9efb3315412099761113f1ef2e5d","bogus":1}',
             '@nokind:abc',
             '@files:stock.csv | rows | join @files:prices.csv rows on Part | join @files:stock2.csv rows on Part',
             'x = documents.list',
             'documents.list | pick documents | where title = $name',
             'documents.list | pick documents | where title={name}',
             'make me a sandwich'):
    T(line)
print('=========== G. other staC ops')
L('stac.translate', {'text': 'show the documents'}, n=1200)
L('stac.translate', {'text': 'power at 3.3 V and 2 A'}, n=1200)
L('language.parse', {'text': '@files:stock.csv | rows | add Short = Required - Available | where Short over 0'}, n=1500)
L('stac.compile', {'program': 'desk | find sheet'}, n=800)
o = L('stac.observe', {'program': 'desk'}, n=500)
L('stac.history', {}, n=600)
L('matrix.list', {'limit': 30}, quiet=True)
m = k.dispatch('matrix.list', {'limit': 60}, p)['result']['rows']
print('matrix rows:', len(m))
for r in m[:40]: print('   %-8s %-18s %s | %s' % (r['outcome'], r['operation'], r['program'][:90], (r['reason'] or '')[:80]))
