import sys
sys.path.insert(0, '/home/user/Struthio'); sys.dont_write_bytecode = True
from workbench.field_model import Field, FieldObject as O, FieldLink as L
objs = [O('pdf', 'source', 'pdf'), O('s1', 'sheet', 's1'), O('s2', 'sheet', 's2'), O('f', 'finding', 'f'), O('q', 'question', 'q', state='open')] + [O('n%d' % i, 'source', 'n') for i in range(6)]
f = Field(objs, [L('pdf', 's1'), L('s1', 's2'), L('s2', 's1'), L('s1', 'f')])
print('ranks:', {i: f.rank_of(i) for i in ('pdf', 's1', 's2', 'f', 'q')}); print('columns left to right:', [(r, f.rank_title(r), f.column(r)) for r in f.ranks()])
