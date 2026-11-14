"""Backend states when packages are absent (-S) and when the worker is launched from another working directory."""
import json, os, sys
sys.path.insert(0, sys.argv[1])
from workbench import math_model as m, math_backend as b
lim = m.compile_expression('v * i <= p', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA', 'lower': '0'}, 'p': {'unit': 'W', 'value': '6'}})
print('cwd', os.getcwd())
print('status', json.dumps(b.status()))
for name in ('Z3', 'SYMPY'):
    r = b.solve(lim, name); print(name, json.dumps({k: r.get(k) for k in ('state', 'reason', 'exit_code')}))
nonlin = m.compile_expression('v * i <= p', {'v': {'unit': 'V'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
print('Z3 nonlinear', json.dumps({k: v for k, v in b.solve(nonlin, 'Z3').items() if k in ('state', 'reason')}))
