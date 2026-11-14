exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from workbench.typebar_qt import stac_hint_kind
INV = 'c574ae94d79542f582932d151fad631f'
BENCH = 'owner:db5f669f863d4c71b89fa7ba348957da'; REVA = 'owner:5a43beee28224c4e818af7b985cdb535'; REVB = 'owner:4f357ff3c843489a9758db71e23bf4b4'
def T(text, note=''):
    print('\n[hint kind: %r]' % stac_hint_kind(text), end='')
    return S(text, note)
print('=========== A. varied lines that should run')
T('@document:218f9efb3315412099761113f1ef2e5d | pick document | select title,revision', 'address form')
T('documents.list | pick documents | sort -words | select title,words | take 2', 'sort/select/take')
T('investigation.sheet {"id":"%s"} | pick attempted | select seq,kind,program,outcome,summary' % INV, 'the recorded steps of the investigation')
T('investigation.sheet {"id":"%s"} | pick checked | group last_outcome | count' % INV, 'group+count')
r = T('@office:%s' % REVB, 'what an office sheet is')
T('@office:%s | rows' % REVB, 'rows lens')
T('@office:%s | pick data.sheets' % REVB, 'sheets?')
T('office.get {"id":"%s"} | pick sheet' % BENCH, 'pick sheet?')
T('office.get {"id":"%s"}' % BENCH, 'whole')
