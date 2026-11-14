"""Pure-engine probes: units, affine boundary, sweep, witness check, solvers. Run from the code copy root."""
import json, sys
from fractions import Fraction
sys.path.insert(0, sys.argv[1])
from workbench import math_model as m, math_backend as b, math_units as u

def show(label, value):
    print('##', label); print(json.dumps(value, default=str, indent=None)[:1500])

print('status', b.status())
# Exact rational and dimension checks
show('rational 0.1+0.2', str(u.rational('0.1') + u.rational('0.2')))
for bad in ('1e400', '0.1f', 'nan'):
    try: u.rational(bad); print('accepted', bad)
    except ValueError as e: print('refused', bad, e)
try: m.compile_expression('v + i', {'v': {'unit': 'V'}, 'i': {'unit': 'A'}})
except m.MathError as e: print('dimension mismatch ->', e.code, e)
ir = m.compile_expression('v * i', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA', 'value': '280'}})
show('12 V x 280 mA in W', m.evaluate(ir, output_unit='W')['outputs'])
try: show('12 V x 280 mA in MiB', m.evaluate(ir, output_unit='MiB'))
except ValueError as e: print('output unit mismatch raises', type(e).__name__, e)

# After Hours: 12 V * I <= 6 W, I >= 0 (mA)
lim = m.compile_expression('v * i <= p', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA', 'lower': '0'}, 'p': {'unit': 'W', 'value': '6'}})
sw = m.sweep(lim, 'i', '0', '1000', 3, None)
show('sweep boundaries 12 V', sw['boundaries'])
show('sweep notice', sw['notice'])
for value in ('500', '501'):
    show('evaluate i=' + value, m.evaluate(lim, {'i': value}, 'W')['outputs'][0])
    print('witness_check i=' + value, m.witness_check(lim, {'i': value}))
print('witness_check i=-1', m.witness_check(lim, {'i': '-1'}))
lim122 = m.compile_expression('v * i <= p', {'v': {'unit': 'V', 'value': '12.2'}, 'i': {'unit': 'mA', 'lower': '0'}, 'p': {'unit': 'W', 'value': '6'}})
show('sweep boundaries 12.2 V', m.sweep(lim122, 'i', '0', '1000', 3)['boundaries'])
for value in ('491', '492'):
    print('12.2 V i=' + value, m.evaluate(lim122, {'i': value}, 'W')['outputs'][0]['left'], m.witness_check(lim122, {'i': value}))
# Integer domain: boundary not rounded to step
limint = m.compile_expression('v * i <= p', {'v': {'unit': 'V', 'value': '12.2'}, 'i': {'unit': 'mA', 'domain': 'integer', 'lower': '0'}, 'p': {'unit': 'W', 'value': '6'}})
show('sweep boundaries integer i', m.sweep(limint, 'i', '0', '1000', 3)['boundaries'])
# Strict relation, negative coefficient, zero coefficient, domain bound
strict = m.compile_expression('v * i < p', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
show('strict lt boundary', m.sweep(strict, 'i', '0', '1000', 3)['boundaries'])
try: m.compile_expression('p - v * i <= 0', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
except m.MathError as e: print('bare 0 against W ->', e.code, e)
neg = m.compile_expression('p <= v * i', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
show('negative coefficient', m.sweep(neg, 'i', '0', '1000', 3)['boundaries'])
zero = m.compile_expression('v * i - v * i + p <= q', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}, 'q': {'unit': 'W', 'value': '7'}})
show('zero coefficient (x - x)', m.sweep(zero, 'i', '0', '10', 3)['boundaries'])
outside = m.compile_expression('v * i <= p', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA', 'upper': '400'}, 'p': {'unit': 'W', 'value': '6'}})
show('root outside declared upper 400 mA', m.sweep(outside, 'i', '0', '300', 3)['boundaries'])
two = m.compile_expression('v * i <= p', {'v': {'unit': 'V'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
show('two free variables -> boundary list', m.sweep(two, 'i', '0', '10', 3)['boundaries'] if True else None)
# Repeated variable: affine exact cancellation
rep = m.compile_expression('x - x', {'x': {'unit': 'V'}})
print('affine x - x ->', m.affine(rep)[rep['model']['outputs'][0]])
# Nonlinear rejected by affine
try: m.affine(m.compile_expression('v * i <= p', {'v': {'unit': 'V'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}}))
except m.MathError as e: print('affine v*i both free ->', e.code, e)
# Denominator crossing zero in evaluate
den = m.compile_expression('1 / x', {'x': {'unit': '1'}})
print('domain conditions 1/x', den['domain_conditions'])

# Solvers
for name in ('Z3', 'SYMPY'):
    show(name + ' 12V*I<=6W', {k: v for k, v in b.solve(lim, name).items() if k not in ('evaluation', 'domain_conditions')})
inconsistent = m.compile_expression('i <= p', {'i': {'unit': 'mA', 'lower': '600'}, 'p': {'unit': 'mA', 'value': '500'}})
show('Z3 inconsistent bounds', {k: v for k, v in b.solve(inconsistent, 'Z3').items() if k not in ('evaluation',)})
eq = m.compile_expression('v * i == p', {'v': {'unit': 'V', 'value': '12'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
show('SYMPY 12V*I==6W', {k: v for k, v in b.solve(eq, 'SYMPY').items() if k not in ('evaluation', 'domain_conditions')})
nonlin = m.compile_expression('v * i <= p', {'v': {'unit': 'V'}, 'i': {'unit': 'mA'}, 'p': {'unit': 'W', 'value': '6'}})
show('Z3 nonlinear', b.solve(nonlin, 'Z3'))
norm = m.compile_expression('x * x / x', {'x': {'unit': '1'}})
show('SYMPY normalization nonlinear', {k: v for k, v in b.solve(norm, 'SYMPY').items() if k not in ('evaluation',)})
# Witness rejected path: patch z3 answer
import unittest.mock as mock
fake = mock.Mock(returncode=0, stdout=json.dumps({'state': 'FEASIBLE', 'assignments': {'i': '501'}}))
with mock.patch.object(b.subprocess, 'run', return_value=fake):
    show('forged FEASIBLE i=501 from backend', b.solve(lim, 'Z3'))
fake = mock.Mock(returncode=0, stdout=json.dumps({'state': 'INFEASIBLE'}))
with mock.patch.object(b.subprocess, 'run', return_value=fake):
    r = b.solve(lim, 'Z3'); show('forged INFEASIBLE from backend (model is feasible)', {k: r[k] for k in ('state', 'backend', 'witness_check')})
