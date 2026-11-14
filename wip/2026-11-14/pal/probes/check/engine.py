"""Part 2: the same cases through Graphite's own exact engine (workbench/math_model.py, math_units.py, field_doubt/field_ripple)."""
import sys, json
from fractions import Fraction as F
sys.path.insert(0, sys.argv[1])
from workbench import math_model as m, math_units as u

def show(key, value):
    print('%-58s %s' % (key, json.dumps(value, default=str)))

def q(row):  # compact quantity record
    return None if row is None else '%s %s (%s%s)' % (row['rational'], row['unit'], row['decimal'], '' if row['decimal_exact'] else ', rounded')

def out(res):
    rows = []
    for o in res.get('outputs', []):
        if o['kind'] == 'quantity':rows.append(q(o.get('value')))
        else:rows.append('%s: %s vs %s' % (o.get('value'), q(o.get('left')), q(o.get('right'))))
    return {'state': res['state'], 'outputs': rows, **({'reason': res['reason']} if 'reason' in res else {})}

def bnd(sw):
    return [{'root': '%s %s (%s)' % (b['input']['rational'], b['input']['unit'], b['input']['decimal']), 'relation': b['relation'],
             'sign': b['coefficient_sign'], 'in_range': b['within_sample_range']} for b in sw['boundaries']]

def states(sw):
    c = {}
    for s in sw['samples']:c[s['state']] = c.get(s['state'], 0) + 1
    return c

def compile_(expr, variables, **kw):
    try:return m.compile_expression(expr, variables, **kw)
    except m.MathError as e:return 'MathError %s: %s' % (e.code, e)

base = {'voltage': {'unit': 'V', 'value': '12'}, 'current': {'unit': 'mA', 'value': '280'}, 'limit': {'unit': 'W', 'value': '6'}}
# 1. 12 V x 280 mA
ir = m.compile_expression('voltage * current', base)
show('V*I default unit', out(m.evaluate(ir)))
show('V*I output W', out(m.evaluate(ir, output_unit='W')))
show('V*I output mW', out(m.evaluate(ir, output_unit='mW')))
show('V*I output in A (mismatch)', (lambda: out(m.evaluate(ir, output_unit='A')))() if False else 'see below')
try:m.evaluate(ir, output_unit='A')
except ValueError as e:show('V*I output in A raises', str(e))
show('headroom limit - V*I', out(m.evaluate(m.compile_expression('limit - voltage * current', base), output_unit='W')))
show('literal 6 - V*I (6 is dimensionless)', compile_('6 - voltage * current', base) if isinstance(compile_('6 - voltage * current', base), str) else 'compiled')
show('limit_mA vs V*I (unit mismatch)', compile_('voltage * current <= limit', {**base, 'limit': {'unit': 'mA', 'value': '6'}}))
show('V + I (unit mismatch)', compile_('voltage + current', base))
# 2. relation and solve for current
rel = m.compile_expression('voltage * current <= limit', {**base, 'current': {'unit': 'mA', 'value': '280', 'lower': '0'}})
show('V*I <= limit evaluate', out(m.evaluate(rel)))
for i in ('500', '501'):
    show('V*I <= limit at %s mA' % i, out(m.evaluate(rel, {'current': i}, output_unit='W')))
    show('witness_check current=%s' % i, m.witness_check(rel, {'current': i}))
sw = m.sweep(rel, 'current', '0', '1000', 81, output_unit='W')
show('sweep current 0..1000 boundaries', bnd(sw))
show('sweep sample states', states(sw))
show('affine form of relation (base units)', {k: (str(v[0]), {a: str(b) for a, b in v[1].items()}) for k, v in m.affine(rel, free=('current',)).items() if k == rel['model']['outputs'][0]})
lt = m.compile_expression('voltage * current < limit', base)
show('strict <: boundary', bnd(m.sweep(lt, 'current', '0', '1000', 3)))
show('strict < at 500 mA', out(m.evaluate(lt, {'current': '500'})))
# 3. startup
st = m.compile_expression('startup - pulse', {'startup': {'unit': 'ms', 'value': '110'}, 'pulse': {'unit': 'ms', 'value': '80'}})
show('startup - pulse default unit', out(m.evaluate(st)))
show('startup - pulse in ms', out(m.evaluate(st, output_unit='ms')))
show('startup power 12 V x 650 mA', out(m.evaluate(ir, {'current': '650'}, output_unit='W')))
# 4. 300 mA
show('V*I at 300 mA', out(m.evaluate(ir, {'current': '300'}, output_unit='W')))
show('headroom at 300 mA', out(m.evaluate(m.compile_expression('limit - voltage * current', base), {'current': '300'}, output_unit='W')))
# 5. rectangle corners through evaluate (Graphite has no interval operation)
for v in ('11.8', '12.2'):
    for i in ('270', '290'):
        show('corner %s V, %s mA' % (v, i), out(m.evaluate(ir, {'voltage': v, 'current': i}, output_unit='W')))
# 6. robust ceiling at 12.2 V, integer mA
r2 = m.compile_expression('voltage * current <= limit', {'voltage': {'unit': 'V', 'value': '12.2'}, 'current': {'unit': 'mA', 'domain': 'integer', 'lower': '0'}, 'limit': {'unit': 'W', 'value': '6'}})
sw2 = m.sweep(r2, 'current', '0', '1000', 81, output_unit='W')
show('12.2 V integer mA: boundary', bnd(sw2))
show('12.2 V integer mA: sweep sample states (step 12.5)', states(sw2))
sw2b = m.sweep(r2, 'current', '0', '1000', 101, output_unit='W')
show('12.2 V integer mA: sweep states (step 10)', states(sw2b))
for i in ('491', '492', '491.5'):
    show('12.2 V at %s mA' % i, out(m.evaluate(r2, {'current': i}, output_unit='W')))
    show('witness_check %s' % i, m.witness_check(r2, {'current': i}))
show('number_record(30000/61)', u.number_record(F(30000, 61)))
# 7. 12 V x 1 mA
show('12 V x 1 mA in mW', out(m.evaluate(ir, {'current': '1'}, output_unit='mW')))
# 8. negative coefficient: limit - V*I <= 2.4 W  -> I >= 300 mA
neg = m.compile_expression('limit - voltage * current <= margin', {**base, 'margin': {'unit': 'W', 'value': '2.4'}})
show('negative coefficient boundary (I >= 300 mA)', bnd(m.sweep(neg, 'current', '0', '1000', 3)))
show('  at 299 / 300 mA', [out(m.evaluate(neg, {'current': c}))['state'] for c in ('299', '300')])
neg2 = m.compile_expression('limit >= voltage * current', base)
show('limit >= V*I boundary (same set as V*I <= limit)', bnd(m.sweep(neg2, 'current', '0', '1000', 3)))
# 9. zero coefficient
z1 = m.compile_expression('voltage * current - voltage * current <= limit', base)
sz1 = m.sweep(z1, 'current', '0', '1000', 5)
show('zero coef, 0 <= 6 W (whole domain): boundaries', bnd(sz1)); show('  sample states', states(sz1))
z2 = m.compile_expression('voltage * current - voltage * current >= limit', base)
sz2 = m.sweep(z2, 'current', '0', '1000', 5)
show('zero coef, 0 >= 6 W (contradiction): boundaries', bnd(sz2)); show('  sample states', states(sz2))
# 10. root outside declared domain (I >= 0, limit -1 W)
dom = m.compile_expression('voltage * current <= limit', {**base, 'current': {'unit': 'mA', 'lower': '0'}, 'limit': {'unit': 'W', 'value': '-1'}})
sd = m.sweep(dom, 'current', '0', '1000', 3)
show('root outside domain (I>=0, V*I <= -1 W): boundary', bnd(sd)); show('  sample states', states(sd))
sd2 = m.sweep(dom, 'current', '-200', '1000', 7)
show('  sweep -200..1000 states', states(sd2))
# 11. dependency: x - x
dep = m.compile_expression('current - current', base)
show('current - current', out(m.evaluate(dep)))
show('affine(current - current)', {k: (str(v[0]), {a: str(b) for a, b in v[1].items()}) for k, v in m.affine(dep, free=('current',)).items() if k == dep['model']['outputs'][0]})
# 12. denominator crossing zero
d = m.compile_expression('1 / x', {'x': {'unit': '1'}})
show('1/x domain_conditions', d['domain_conditions'])
s3 = m.sweep(d, 'x', '-1', '2', 3)
show('1/x sweep -1..2, 3 samples (0 not sampled)', [(s['input']['rational'], s['state'], s['value'] and s['value']['rational']) for s in s3['samples']])
s4 = m.sweep(d, 'x', '-1', '2', 4)
show('1/x sweep -1..2, 4 samples (0 sampled)', [(s['input']['rational'], s['state'], s['value'] and s['value']['rational']) for s in s4['samples']])
show('1/x evaluate x=0', out(m.evaluate(d, {'x': '0'})))
dl = m.compile_expression('limit / current <= k', {'limit': {'unit': 'W', 'value': '6'}, 'current': {'unit': 'mA'}, 'k': {'unit': 'V', 'value': '24'}})
show('variable denominator relation: sweep boundaries', bnd(m.sweep(dl, 'current', '-100', '1000', 3)))
try:m.affine(dl)
except m.MathError as e:show('  affine raises', '%s: %s' % (e.code, e))
# 13. inconsistent bounds / clock lab
try:m.compile_expression('x', {'x': {'unit': 'mA', 'lower': '10', 'upper': '5'}})
except m.MathError as e:show('reversed bounds', '%s: %s' % (e.code, e))
cl = m.compile_expression('buffer_A + buffer_B + workspace <= memory_limit', {'buffer_A': {'unit': 'MiB', 'value': '6'}, 'buffer_B': {'unit': 'MiB', 'value': '6'}, 'workspace': {'unit': 'MiB', 'value': '5'}, 'memory_limit': {'unit': 'MiB', 'value': '16'}})
show('Clock Lab memory evaluate (MiB)', out(m.evaluate(cl, output_unit='MiB')))
show('Clock Lab memory evaluate (default unit)', out(m.evaluate(cl)))
show('Clock Lab workspace boundary', bnd(m.sweep(cl, 'workspace', '0', '10', 21, output_unit='MiB')))
show('Clock Lab power 5 V x 250 mA', out(m.evaluate(m.compile_expression('voltage * assumed_typical_current', {'voltage': {'unit': 'V', 'value': '5'}, 'assumed_typical_current': {'unit': 'mA', 'value': '250'}}), output_unit='W')))
# 14. float side: field_doubt / field_ripple comparisons
from workbench import field_doubt as fd, field_ripple as fr
show('measure(280, mA)', fd.measure('280', 'mA'))
show('measure(3.36, W)', fd.measure('3.36', 'W'))
show('_same(0.28, measure 280 mA)', fd._same(0.28, fd.measure('280', 'mA')[1]))
show('_same(6, 6.000000005) (float tolerance)', fd._same(6.0, 6.000000005))
show('_plain(30000/61)', fd._plain(30000 / 61))
show('_made_with 2.64 W headroom when 3.36 -> 3.6', fr._made_with(2.64, 'power', [('power', 3.36, 3.6, 'the result of "07 Settled power"')], {'power': [(6.0, 'Rev B', '6 W')]}))
show('_made_with 2.462 from 3.538', fr._made_with(2.462, 'power', [('power', 3.538, 3.6, 'x')], {'power': [(6.0, 'Rev B', '6 W')]}))
