"""The one maths core, pure (0.8.5, "Maths in lines"): the test vectors 1 to 18 of the design (wip judgment on the one math
core, PART 2), each exact, on invented numbers. The model has voltage (V), current (mA) and limit = 6 W. No Kernel, no
window, no model; and no float anywhere in the new modules (an AST scan below)."""
import ast
import random
import unittest
from fractions import Fraction as F
from pathlib import Path
from workbench import math_model as m, math_ranges as r, math_answers as a

ROOT = Path(__file__).resolve().parents[1]
NEW = ('workbench/math_ranges.py', 'workbench/math_answers.py', 'workbench/tolerances.py')
POWER = {'voltage': {'unit': 'V', 'value': '12'}, 'current': {'unit': 'mA', 'value': '280', 'lower': '0'}, 'limit': {'unit': 'W', 'value': '6'}}


def model(expression, variables=None, **changes):
    variables = {k: dict(v) for k, v in (variables or POWER).items()}
    for name, fields in changes.items():variables[name].update(fields)
    return m.compile_expression(expression, variables)


def unitless(*names, **fields):return {n: {'unit': '1', **fields} for n in names}


def rec(record):return F(record['rational'])


def solve(expression, name='current', box=None, variables=None, **kw):
    return r.allowed(model(expression, variables), name, box, **kw)


class Calculate(unittest.TestCase):
    def test_1_power_headroom_and_a_bare_number_against_watts(self):
        said = a.ask('calculate', 'voltage * current', POWER)
        self.assertEqual((said['state'], rec(said['result']['value']), said['result']['value']['unit']), ('ANSWERED', F(84, 25), 'W'))
        self.assertEqual(rec(a.ask('calculate', 'voltage * current', POWER, asked={'unit': 'mW'})['result']['value']), 3360)
        self.assertEqual(rec(a.ask('calculate', 'limit - voltage * current', POWER)['result']['value']), F(66, 25))
        self.assertEqual(a.ask('calculate', '6 - voltage * current', POWER)['state'], 'DIMENSION_MISMATCH')
        self.assertEqual(said['guarantee'], 'EXACT_VALUE')


class Solve(unittest.TestCase):
    def test_2_solve_le_for_current_from_zero_is_up_to_500_mA_and_501_is_the_witness(self):
        found = solve('voltage * current <= limit')
        self.assertEqual((found['state'], found['lower'], found['upper']['value'], found['upper']['closed']),
                         ('ALLOWED', {'value': 0, 'closed': True, 'by': 'domain'}, 500, True))
        self.assertEqual(found['upper']['value'] * F(1, 1000), F(1, 2))         # 1/2 A
        self.assertTrue(found['checked'])
        said = a.ask('solve', 'voltage * current <= limit', POWER, asked={'for': 'current'})
        self.assertTrue(said['words']['answer'].startswith('Up to 500 mA'))
        at500 = a.ask('check', 'voltage * current <= limit', POWER, {'current': {'range': ('500', '500')}})
        at501 = a.ask('check', 'voltage * current <= limit', POWER, {'current': {'range': ('501', '501')}})
        self.assertEqual(at500['state'], 'HOLDS')
        self.assertEqual((at501['state'], rec(at501['witness']['value'])), ('FAILS', F(1503, 250)))
        self.assertEqual(rec(at501['witness']['assignment']['current']), 501)

    def test_3_strict_in_whole_mA_is_499_and_not_strict_is_500(self):
        whole = {'current': {'domain': 'integer'}}
        self.assertEqual(r.allowed(model('voltage * current < limit', **whole), 'current')['lattice']['upper'], 499)
        self.assertEqual(r.allowed(model('voltage * current <= limit', **whole), 'current')['lattice']['upper'], 500)

    def test_4_robust_over_11_8_to_12_2_V_ends_at_30000_61_mA_491_holds_492_does_not(self):
        found = solve('voltage * current <= limit', box={'voltage': ('11.8', '12.2')}, step='1')
        self.assertEqual(found['upper']['value'], F(30000, 61));self.assertEqual(found['lattice']['upper'], 491)
        end, past = found['ends'][0], found['beyond'][0]
        self.assertEqual((end['at'], end['holds'], rec(end['left'])), (491, True, F(29951, 5000)))
        self.assertEqual((past['at'], past['holds'], rec(past['left'])), (492, False, F(7503, 1250)))
        self.assertEqual(end['corner'], {'voltage': F(61, 5)})                   # the 12.2 V corner sets it
        self.assertEqual(solve('voltage * current <= limit', box={'voltage': ('11.8', '11.8')})['upper']['value'], F(30000, 59))

    def test_7_the_limit_as_a_lower_end(self):
        variables = {**POWER, 'h': {'unit': 'W', 'value': '2.4'}}
        found = solve('limit - voltage * current <= h', variables=variables)
        self.assertEqual((found['lower']['value'], found['lower']['closed'], found['upper']), (300, True, None))
        for at, state in (('299', 'FAILS'), ('300', 'HOLDS')):
            self.assertEqual(a.ask('check', 'limit - voltage * current <= h', variables, {'current': {'range': (at, at)}})['state'], state)
        self.assertEqual(solve('limit >= voltage * current')['upper']['value'], 500)

    def test_8_a_zero_coefficient_is_the_whole_domain_or_empty(self):
        self.assertEqual(solve('x - x <= 0', 'x', variables=unitless('x'))['state'], 'WHOLE_DOMAIN')
        self.assertEqual(solve('x - x < 0', 'x', variables=unitless('x'))['state'], 'EMPTY')
        self.assertEqual(solve('x - x + 1 <= 0', 'x', variables=unitless('x'))['state'], 'EMPTY')

    def test_9_the_domain_can_empty_it_and_says_what_it_needed(self):
        variables = {**POWER, 'floor': {'unit': 'W', 'value': '-1'}}
        found = solve('voltage * current <= floor', variables=variables)
        self.assertEqual((found['state'], found['needs']['upper']['value']), ('EMPTY', F(-250, 3)))
        said = a.ask('solve', 'voltage * current <= floor', variables, asked={'for': 'current'})
        self.assertIn('needs current <= -83.33 mA (exact -250/3 mA)', said['words']['answer'])
        self.assertEqual(solve('12 * x < 0', 'x', variables=unitless('x', lower='0'))['state'], 'EMPTY')

    def test_10_steps_of_5_mA(self):
        self.assertEqual(solve('voltage * current <= limit', box={'voltage': ('11.8', '12.2')}, step='5')['lattice']['upper'], 490)
        self.assertEqual(solve('voltage * current < limit', step='5')['lattice']['upper'], 495)

    def test_14_two_unknowns_multiplied_is_unsupported_with_its_reason(self):
        with self.assertRaises(r.RangeError) as caught:solve('x * y <= 1', 'x', variables=unitless('x', 'y'))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED');self.assertIn('multiplied by another quantity', str(caught.exception))
        said = a.ask('solve', 'x * y <= 1', unitless('x', 'y'), asked={'for': 'x'})
        self.assertEqual(said['state'], 'UNSUPPORTED');self.assertTrue(said['words']['answer'].startswith('Cannot work it out'))
        for expression in ('x * x <= 1', '1 / x <= 1'):        # not affine in x, a variable denominator: never an empty list
            with self.assertRaises(r.RangeError) as caught:solve(expression, 'x', variables=unitless('x', value='1'))
            self.assertEqual(caught.exception.code, 'UNSUPPORTED')

    def test_16_the_solved_value_is_checked_on_a_copy_with_its_declared_value_removed(self):
        ir = model('voltage * current <= limit')
        self.assertFalse(m.witness_check(ir, {'current': '500'}))       # 280 mA is declared: a witness may not override it
        self.assertTrue(m.witness_check(r.freed(ir, 'current'), {'current': '500'}))
        self.assertNotIn('value', r.freed(ir, 'current')['model']['variables']['current'])

    def test_solve_guard_ranges_used_twice_or_under_a_division_are_unsupported(self):
        for expression in ('voltage * current - voltage * current + voltage * current <= limit', 'current <= limit / voltage'):
            with self.assertRaises(r.RangeError) as caught:solve(expression, box={'voltage': ('11', '13')})
            self.assertEqual(caught.exception.code, 'UNSUPPORTED')


class Ranges(unittest.TestCase):
    def test_5_range_of_power_is_exact_and_its_slack_holds(self):
        box = {'voltage': ('11.8', '12.2'), 'current': ('270', '290')}
        power = r.enclose(model('voltage * current'), box)
        self.assertEqual((power.lo, power.hi, power.status), (F(1593, 500), F(1769, 500), r.ATTAINED))
        found = r.check_box(model('voltage * current <= limit'), box)
        self.assertEqual((found['slack'].lo, found['slack'].hi, found['state'], found['for_all']), (F(1231, 500), F(1407, 500), 'HOLDS', 'HOLDS_FOR_ALL'))
        said = a.ask('range', 'voltage * current', POWER, {k: {'range': v} for k, v in box.items()})
        self.assertEqual((said['guarantee'], [rec(x) for x in said['result']['range']]), ('EXACT_RANGE', [F(1593, 500), F(1769, 500)]))

    def test_6_straddling_the_limit_cannot_tell_yet_a_corner_fails(self):
        found = r.check_box(model('voltage * current <= limit'), {'voltage': ('11.8', '12.2'), 'current': ('270', '500')})
        self.assertEqual((found['slack'].lo, found['slack'].hi), (F(-1, 10), F(1407, 500)))
        self.assertEqual((found['state'], found['for_all']), ('UNDECIDED', 'FAILS_FOR_SOME'))
        w = found['witness'];self.assertEqual((w['assignment']['voltage'], w['assignment']['current'], rec(w['value'])), (F(61, 5), 500, F(61, 10)))
        said = a.ask('check', 'voltage * current <= limit', POWER, {'voltage': {'range': ('11.8', '12.2')}, 'current': {'range': ('270', '500')}})
        self.assertEqual((said['state'], said['words']['heading']), ('UNDECIDED', 'Cannot tell'))

    def test_11_dependency_and_powers(self):
        self.assertEqual(r.enclose(model('x - x', unitless('x')), {'x': (1, 3)}), r.Enclosure(0, 0, r.ATTAINED))
        square = r.enclose(model('x * x', unitless('x')), {'x': (-1, 2)})
        self.assertEqual(square.status, r.SOUND);self.assertTrue(r.Enclosure(0, 4).inside(square))
        power = r.enclose(model('x ** 2', unitless('x')), {'x': (-1, 2)})
        self.assertEqual((power.lo, power.hi), (0, 4))

    def test_12_a_pole_is_never_a_range(self):
        with self.assertRaises(r.RangeError) as caught:r.enclose(model('1 / x', unitless('x')), {'x': (-1, 2)})
        self.assertEqual(caught.exception.code, 'DENOMINATOR_MAY_BE_ZERO')
        said = a.ask('range', '1 / x', unitless('x', value='1'), {'x': {'range': ('-1', '2')}})
        self.assertEqual((said['state'], said['result']), ('DENOMINATOR_MAY_BE_ZERO', None))
        self.assertIn('DENOMINATOR_MAY_BE_ZERO', [o.get('condition') for o in said['obligations']])

    def test_13_units(self):
        self.assertEqual(a.ask('range', 'voltage + current', POWER)['state'], 'DIMENSION_MISMATCH')
        variables = {**POWER, 'cap': {'unit': 'mA', 'value': '500'}}
        self.assertEqual(a.ask('check', 'voltage * current <= cap', variables)['state'], 'DIMENSION_MISMATCH')
        wrong = a.ask('calculate', 'voltage * current', POWER, asked={'unit': 'ms'})
        self.assertEqual(wrong['state'], 'INCOMPATIBLE_OUTPUT_UNIT')                      # a state, never a bare ValueError
        self.assertEqual(a.ask('range', 'voltage * current', POWER, {'voltage': {'range': ('11', '13')}}, {'unit': 'ms'})['state'], 'INCOMPATIBLE_OUTPUT_UNIT')

    def test_15_widening_stays_within_2048_bits_and_says_so(self):
        tiny = F(1, 3 ** 1300);found = r.outward(tiny)
        self.assertIn(tiny, found);self.assertEqual(found.status, r.WIDENED)
        for end in (found.lo, found.hi):self.assertTrue(r.fits(end))
        self.assertEqual(r.outward(F(1, 3)), r.Enclosure(F(1, 3), F(1, 3), r.ATTAINED))


class S2Numbers(unittest.TestCase):
    """Vector 17: invented ranges, pure arithmetic: a startup time of 110 ms plus or minus 5 against limits of 80 and 120 ms;
    12 V plus or minus 1 % with 650 mA or 280 mA plus or minus 2 % against 8 W and 6 W."""
    TIME = {'startup': {'unit': 'ms', 'value': '110'}, 'limit': {'unit': 'ms', 'value': '80'}}
    RAIL = {'voltage': {'unit': 'V', 'value': '12'}, 'current': {'unit': 'mA', 'value': '650'}, 'limit': {'unit': 'W', 'value': '8'}}

    def test_17_c1b_over_by_25_to_35_ms_and_c1a_holds(self):
        said = a.ask('check', 'startup <= limit', self.TIME, {'startup': {'range': ('105', '115')}})
        self.assertEqual(([rec(x) for x in said['result']['slack']], said['state']), ([-35, -25], 'FAILS'))
        self.assertIn('over by 25 to 35 ms', said['words']['answer'])
        held = a.ask('check', 'startup <= limit', {**self.TIME, 'limit': {'unit': 'ms', 'value': '120'}}, {'startup': {'range': ('105', '115')}})
        self.assertEqual(([rec(x) for x in held['result']['slack']], held['state']), ([5, 15], 'HOLDS'))

    def test_17_c2_cannot_tell_with_its_witness_and_c3_holds(self):
        box = {'voltage': ('11.88', '12.12'), 'current': ('637', '663')}
        found = r.check_box(model('voltage * current <= limit', self.RAIL), box)
        self.assertEqual((found['slack'].lo, found['slack'].hi, found['state']), (F(-889, 25000), F(10811, 25000), 'UNDECIDED'))
        self.assertEqual(rec(found['witness']['value']), F(200889, 25000))
        found = r.check_box(model('voltage * current <= limit', {**self.RAIL, 'limit': {'unit': 'W', 'value': '6'}}), {**box, 'current': ('274.4', '285.6')})
        self.assertEqual((found['slack'].lo, found['slack'].hi, found['state']), (F(79329, 31250), F(85629, 31250), 'HOLDS'))

    def test_17_weakest_preconditions(self):
        amps = lambda found:found['upper']['value'] / 1000
        self.assertEqual(amps(solve('voltage * current <= limit', variables={**POWER})), F(1, 2))
        self.assertEqual(amps(solve('voltage * current <= limit', box={'voltage': ('11.88', '12.12')})), F(50, 101))
        self.assertEqual(amps(solve('voltage * current <= limit', box={'voltage': ('11.88', '12.12')}, variables=self.RAIL)), F(200, 303))


class Properties(unittest.TestCase):
    """Vector 18, seeded and so the same at every run: points lie inside the enclosure, an ATTAINED enclosure's ends are
    reached at corners, a sub-box's enclosure lies inside the box's."""
    EXPRESSIONS = ('x * y + z', 'x - y * z', 'x * x - y', 'x ** 2 + y * z', '(x + y) * (x - z)', 'x / y + z', 'x - x + y ** 3', 'x * y * z')

    def point(self, rng, lo, hi):return lo + (hi - lo) * F(rng.randint(0, 64), 64)

    def box(self, rng):
        spans = {}
        for name in 'xyz':
            lo = F(rng.randint(-40, 40), rng.randint(1, 9));spans[name] = (lo, lo + F(rng.randint(0, 50), rng.randint(1, 9)))
        if spans['y'][0] <= 0:spans['y'] = (F(1, 2), spans['y'][1] + 1 - spans['y'][0])  # y is a denominator: keep it off zero
        return spans

    def value(self, ir, at):
        out = m.evaluate(ir, {k: str(v) for k, v in at.items() if k in ir['model']['variables']})['outputs'][0]['value']
        return rec(out)

    def test_18_seeded_properties(self):
        rng = random.Random(20261120)
        for expression in self.EXPRESSIONS:
            ir = m.compile_expression(expression, unitless('x', 'y', 'z'))
            for _ in range(12):
                spans = {k: v for k, v in self.box(rng).items() if k in ir['model']['variables']}
                found = r.enclose(ir, spans)
                for _ in range(8):
                    at = {k: self.point(rng, *v) for k, v in spans.items()}
                    self.assertIn(self.value(ir, at), found, (expression, spans, at))
                if found.status == r.ATTAINED:
                    reached = {self.value(ir, corner) for corner in r.corners(spans)}
                    self.assertIn(found.lo, reached, expression);self.assertIn(found.hi, reached, expression)
                inner = {k: (self.point(rng, lo, hi), hi) for k, (lo, hi) in spans.items()}
                inner = {k: (lo, max(lo, self.point(rng, lo, hi))) for k, (lo, hi) in inner.items()}
                self.assertTrue(r.enclose(ir, inner).inside(found), (expression, spans, inner))


class Exactness(unittest.TestCase):
    def test_no_float_and_no_optional_solver_in_the_new_modules(self):
        for path in NEW:
            tree = ast.parse((ROOT / path).read_text())
            for node in ast.walk(tree):
                self.assertFalse(isinstance(node, ast.Constant) and isinstance(node.value, float), (path, getattr(node, 'lineno', 0)))
                self.assertFalse(isinstance(node, ast.Name) and node.id == 'float', (path, getattr(node, 'lineno', 0)))
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'math':
                    self.assertIn(node.attr, ('floor', 'ceil'), (path, node.lineno))       # math.floor and math.ceil of a Fraction are ints
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [getattr(node, 'module', None) or ''] + [alias.name for alias in node.names]
                    self.assertFalse(any(n.split('.')[0] in ('sympy', 'z3', 'math_backend') or n.endswith('math_backend') for n in names), (path, names))

    def test_answers_are_exact_fractions_throughout(self):
        found = r.allowed(model('voltage * current <= limit'), 'current', {'voltage': ('11.8', '12.2')}, step='1')
        for value in (found['upper']['value'], found['lattice']['upper'], found['ends'][0]['at']):self.assertIsInstance(value, F)
        self.assertIsInstance(r.enclose(model('voltage * current'), {'voltage': ('11.8', '12.2')}).lo, F)

    def test_the_decision_table(self):
        cases = {'le': ((0, 1, 'HOLDS'), (-2, -1, 'FAILS'), (-1, 0, 'UNDECIDED')), 'lt': ((F(1, 9), 1, 'HOLDS'), (-1, 0, 'FAILS'), (0, 1, 'UNDECIDED')),
                 'ge': ((-1, 0, 'HOLDS'), (F(1, 9), 1, 'FAILS'), (0, 1, 'UNDECIDED')), 'gt': ((-1, F(-1, 9), 'HOLDS'), (0, 1, 'FAILS'), (-1, 0, 'UNDECIDED')),
                 'eq': ((0, 0, 'HOLDS'), (1, 2, 'FAILS'), (0, 1, 'UNDECIDED')), 'ne': ((1, 2, 'HOLDS'), (0, 0, 'FAILS'), (-1, 1, 'UNDECIDED'))}
        for relation, rows in cases.items():
            for lo, hi, state in rows:self.assertEqual(r.decide(r.Enclosure(lo, hi), relation), state, (relation, lo, hi))

    def test_an_answer_carries_its_receipt_and_its_own_implementation(self):
        said = a.ask('range', 'voltage * current', POWER, {'voltage': {'range': ('11.8', '12.2')}})
        self.assertEqual(set(said['implementation']), {'math_ranges.py', 'math_answers.py', 'math_model.py', 'math_units.py'})
        self.assertEqual((said['model_calls'], said['physical_qualification'], said['schema']), (0, False, 'ledger.math-answer/1'))
        self.assertEqual(said['digest'], a.records.digest({k: v for k, v in said.items() if k != 'digest'}))
        self.assertEqual([row['origin'] for row in said['inputs']], ['GIVEN_IN_LINE', 'DECLARED_SCENARIO'])
        self.assertLessEqual(len(said['derivation']), 8)
        self.assertTrue(any(line.startswith('Guarantee: an exact range') for line in said['words']['receipt']))


class Honest(unittest.TestCase):
    """What the words claim is never more than is known: a sound range says 'at least' and why; an allowed number is shown
    rounded inward; a guarantee is claimed only when it was earned; a refusal says why in the owner's words."""
    X = {'x': {'unit': '1', 'value': '1'}}
    INTERNAL = r'\b[A-Z]{2,}_[A-Z_]+\b|\bn\d+\b|Cannot (?:ge|gt|le|lt|eq|ne|add|sub|mul|div)\b'

    def test_a_check_over_a_sound_range_says_at_least_and_never_that_the_ranges_reach_both_sides(self):
        box = {'x': {'range': ('-1', '2')}}
        unknown = a.ask('check', 'x * x >= 0', self.X, box)                     # true for every x, yet the sound range straddles 0
        self.assertEqual((unknown['state'], unknown['result']['status']), ('UNDECIDED', r.SOUND))
        self.assertNotIn('reach both sides of it', unknown['words']['answer'])
        self.assertIn('cannot be told from this range', unknown['words']['answer']);self.assertIn('may be wider than the true one', unknown['words']['answer'])
        held = a.ask('check', 'x * x <= 4', self.X, box)                         # the true spare is 0 to 4, the sound one 0 to 6
        self.assertEqual(held['state'], 'HOLDS');self.assertIn('with at least 0 to spare', held['words']['answer'])
        self.assertNotIn('0 to 6', held['words']['answer'])
        short = a.ask('check', 'x * x >= 5', self.X, box)                        # x * x is at most 4: short by at least 1, truly
        self.assertEqual(short['state'], 'FAILS');self.assertIn('short by at least 1 ', short['words']['answer'])
        exact = a.ask('check', 'x <= 4', self.X, box)                            # an exact range keeps both ends
        self.assertIn('with 2 to 5 to spare.', exact['words']['answer'])

    def test_an_allowed_end_is_rounded_inward_and_an_equation_is_said_once_and_exactly(self):
        third = {'x': {'unit': '1', 'value': '1'}, 'y': {'unit': '1', 'value': '1/3'}}
        said = a.ask('solve', 'x >= y', third, asked={'for': 'x'})
        shown = [line.split(' (exact')[0] for line in said['words']['lines'] if ' holds' in line]
        self.assertTrue(shown)
        for number in shown:self.assertGreaterEqual(F(number), F(1, 3), said['words']['lines'])     # never 0.3333, which does not hold
        self.assertGreaterEqual(F(said['words']['answer'].split()[2]), F(1, 3), said['words']['answer'])
        half = {'x': {'unit': '1', 'value': '1'}, 'y': {'unit': '1', 'value': '1/2'}}
        equal = a.ask('solve', 'x == y', half, asked={'for': 'x'})
        held = [line for line in equal['words']['lines'] if ' holds' in line]
        self.assertEqual(len(held), 1, equal['words']['lines']);self.assertTrue(equal['words']['answer'].startswith('Exactly 0.5'))
        self.assertTrue(a.ask('solve', 'x == y', third, asked={'for': 'x'})['words']['answer'].startswith('Exactly 1/3'))

    def test_the_exact_allowed_set_is_claimed_only_when_an_end_was_worked_out_again(self):
        third = {'x': {'unit': '1', 'value': '1'}, 'y': {'unit': '1', 'value': '1/3'}}
        open_end = a.ask('solve', 'x > y', third, asked={'for': 'x'})
        self.assertIsNone(open_end['result']['allowed']['checked']);self.assertIsNone(open_end['guarantee'])
        self.assertTrue(any(line.startswith('Guarantee: none claimed') for line in open_end['words']['receipt']))
        closed = a.ask('solve', 'x >= y', third, asked={'for': 'x'})
        self.assertEqual((closed['result']['allowed']['checked'], closed['guarantee']), (True, 'EXACT_ALLOWED_SET'))

    def test_a_refusal_says_why_in_the_owners_words(self):
        import re
        cases = (('range', 'voltage * current', POWER, {'voltage': {'range': ('11', '13')}}, {'unit': 'V'}, 'INCOMPATIBLE_OUTPUT_UNIT'),
                 ('range', 'voltage * current', POWER, {}, {'unit': 'kW'}, None),
                 ('calculate', '6 - voltage * current', POWER, {}, {}, 'DIMENSION_MISMATCH'),
                 ('range', '1 / x', self.X, {'x': {'range': ('0', '0')}}, {}, 'DOMAIN_ERROR'),
                 ('solve', 'voltage * current <= limit', POWER, {}, {'for': 'current', 'unit': 'V'}, 'INCOMPATIBLE_OUTPUT_UNIT'))
        for stage, expression, variables, box, asked, state in cases:
            said = a.ask(stage, expression, variables, box, asked)
            if state:self.assertEqual(said['state'], state, said['reason'])
            self.assertTrue(said['words']['answer'].startswith('Cannot work it out: '), said['words']['answer'])
            self.assertIsNone(re.search(self.INTERNAL, said['words']['answer']), said['words']['answer'])
        self.assertIn('kW is not a unit', a.ask('range', 'voltage * current', POWER, asked={'unit': 'kW'})['words']['answer'])
        self.assertIn('a denominator is zero', a.ask('range', '1 / x', self.X, {'x': {'range': ('0', '0')}})['words']['answer'])

    def test_a_number_too_long_is_refused_as_too_long(self):
        said = a.ask('range', 'x', self.X, {'x': {'range': ('1', '1' + '0' * 120)}})
        self.assertEqual(said['state'], 'EXACT_ARITHMETIC_SIZE_BOUND');self.assertIn('too long', said['words']['answer'])
        self.assertEqual(a.ask('range', 'x', self.X, {'x': {'range': ('1', 'one')}})['state'], 'UNSUPPORTED')

    def test_a_whole_quantity_takes_a_range_of_whole_ends(self):
        whole = {'n': {'unit': '1', 'value': '2', 'domain': 'integer'}}
        self.assertEqual(a.ask('range', 'n', whole, {'n': {'range': ('1.5', '2.5')}})['state'], 'DOMAIN_ERROR')
        said = a.ask('range', 'n', whole, {'n': {'range': ('1', '3')}})
        self.assertEqual((said['guarantee'], [rec(x) for x in said['result']['range']]), ('EXACT_RANGE', [1, 3]))

    def test_only_solve_frees_a_quantity_and_a_freed_one_takes_no_range(self):
        check = a.ask('check', 'voltage * current <= limit', POWER, asked={'for': 'current'})
        self.assertEqual((check['state'], check['inputs']), ('UNSUPPORTED', []))
        solved = a.ask('solve', 'voltage * current <= limit', POWER, {'current': {'range': ('1', '2')}}, {'for': 'current'})
        self.assertEqual(solved['state'], 'UNSUPPORTED');self.assertIn('what is solved for', solved['words']['answer'])

    def test_the_implementation_is_hashed_once_as_loaded(self):
        from unittest.mock import patch
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('an answer read its files again')):
            said = a.ask('range', 'voltage * current', POWER, {'voltage': {'range': ('11.8', '12.2')}})
            refused = a.ask('calculate', '6 - voltage * current', POWER)
        self.assertEqual(said['implementation'], a.IMPLEMENTATION);self.assertEqual(refused['implementation'], a.IMPLEMENTATION)


if __name__ == '__main__':unittest.main()
