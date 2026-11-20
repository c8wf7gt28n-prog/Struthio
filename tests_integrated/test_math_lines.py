"""Maths in lines (0.8.5): the line face of the one maths core, vectors 19 to 26 of the design, on the Clock Lab fixture as
test_exact_math does; the owner's tolerances; the words the window shows; and the three worked examples on Rail Demo's
invented numbers in docs/INTEGRATED_I02.md, run here word for word. No model and no window: the window's own frame is
taken by hand (the report says where)."""
import json
import re
import subprocess
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path
from workbench import math_answers, stacy_hand, stacy_control, rail_demo
from workbench.engineering_kernel import CAPABILITIES, Principal, operator
from workbench.office_building_qt import readable_result
from workbench.problem_checks import bound, invoke
from workbench.stac_bridge import compile_program
from tests_integrated import test_problem as fixtures  # run per module from the program root

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs' / 'INTEGRATED_I02.md'
EXAMPLES = '### Three worked examples on Rail Demo'


def rec(record):return F(record['rational'])


class Lines(fixtures.ProblemBindings):
    def line(self, rest, p=None):
        response = self.kernel.dispatch('stac.run', {'program': 'math problem:%s | %s' % (self.problem['id'], rest)}, p or self.p)
        self.assertTrue(response['ok'], response);return response['result']

    def revise(self, **changes):
        sheet = self.call('problems.get', {'id': self.problem['id']})['problem']
        self.problem = self.call('problems.revise', {**bound(sheet), **changes});return self.problem

    def test_19_calculate_carries_the_freshness_of_its_sources(self):
        out = self.line('calculate "voltage * assumed_typical_current" | unit W')
        self.assertEqual((out['result']['evaluation']['outputs'][0]['value']['rational'], out['freshness']), ('5/4', 'CURRENT'))
        self.assertEqual(readable_result(out), 'Worked out\n1.25 W.')
        work = self.root / 'Files' / self.copy['work'] / 'power.csv';work.write_text(work.read_text().replace('120', '125'))
        out = self.line('calculate "voltage * assumed_typical_current" | unit W')
        self.assertEqual(out['freshness'], 'REVIEW_REQUIRED');self.assertIn('review them before relying on this', readable_result(out))
        answered = self.line('range "voltage * assumed_typical_current" | unit W')
        self.assertEqual((answered['freshness'], answered['result']['freshness']), ('REVIEW_REQUIRED', 'REVIEW_REQUIRED'))

    def test_20_memory_all_concurrent_does_not_hold_and_the_workspace_may_be_4_MiB(self):
        found = self.line('check "buffer_A + buffer_B + workspace <= memory_limit"')['result']
        self.assertEqual((found['state'], rec(found['result']['left'][0]), rec(found['result']['right'][0])), ('FAILS', 17, 16))
        self.assertEqual(found['words']['heading'], 'Does not hold')
        solved = self.line('solve "buffer_A + buffer_B + workspace <= memory_limit" for workspace')['result']['result']['allowed']
        self.assertEqual((rec(solved['upper']['value']), solved['upper']['value']['unit'], solved['declared_inside']), (4, 'MiB', False))

    def test_21_current_solve_within_0_and_1000_in_whole_mA(self):
        said = self.line('solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | within 0 1000 | step 1')['result']
        found = said['result']['allowed']
        self.assertEqual((rec(found['lattice']['lower']), rec(found['lattice']['upper']), found['declared_inside']), (0, 300, True))
        self.assertEqual(said['guarantee'], 'EXACT_ALLOWED_SET')
        self.assertEqual([row['origin'] for row in said['inputs']], ['FREED', 'PROBLEM_REVISION'])
        self.assertEqual(said['inputs'][1]['source']['revision'], self.problem['revision'])

    def test_22_a_range_given_in_the_line(self):
        said = self.line('range "voltage * assumed_typical_current" | given assumed_typical_current 240 260 | unit W')['result']
        self.assertEqual([rec(x) for x in said['result']['range']], [F(6, 5), F(13, 10)])
        self.assertEqual({row['name']: row['origin'] for row in said['inputs']}, {'voltage': 'PROBLEM_REVISION', 'assumed_typical_current': 'GIVEN_IN_LINE'})

    def test_23_the_owners_tolerance_applies_carries_over_and_waits_for_a_recheck(self):
        said = self.call('tolerances.set', {**bound(self.problem), 'variable': 'voltage', 'said': 'plus_minus', 'amount': '0.25',
                                            'basis': 'Invented for this test: the supply holds 5 V to a quarter volt'})
        self.assertEqual((said['schema'], said['lo'], said['hi'], said['set_by']), ('ledger.tolerance/1', '19/4', '21/4', 'owner'))
        def voltage(answer):return next(row for row in answer['inputs'] if row['name'] == 'voltage')
        answer = self.line('range "voltage * assumed_typical_current" | unit W')['result']
        self.assertEqual([rec(x) for x in answer['result']['range']], [F(19, 16), F(21, 16)])
        self.assertEqual((voltage(answer)['origin'], voltage(answer)['tolerance']['state']), ('OWNER_TOLERANCE', 'APPLIES'))
        self.revise(questions=['When is each allocation live?'])
        answer = self.line('range "voltage * assumed_typical_current" | unit W')['result']
        self.assertEqual(([rec(x) for x in answer['result']['range']], voltage(answer)['tolerance']['state']), ([F(19, 16), F(21, 16)], 'CARRIED_OVER'))
        variables = json.loads(json.dumps(self.problem['variables']))
        next(v for v in variables if v['name'] == 'voltage')['value'] = '5.1'
        self.revise(variables=variables)
        answer = self.line('range "voltage * assumed_typical_current" | unit W')['result']
        self.assertEqual([rec(x) for x in answer['result']['range']], [F(51, 40), F(51, 40)])              # not applied
        self.assertEqual((voltage(answer)['origin'], voltage(answer)['tolerance']['state']), ('PROBLEM_REVISION', 'RECHECK'))
        self.assertIn('needs your recheck', '\n'.join(answer['words']['receipt']))
        listed = self.call('tolerances.list', {'problem': self.problem['id']})['tolerances']
        self.assertEqual([(t['subject']['variable'], t['state']) for t in listed], [('voltage', 'RECHECK')])

    def test_24_read_scope_runs_the_lines_and_a_tolerance_is_the_owners(self):
        reader = Principal(self.p.identity)
        for rest in ('calculate "voltage * assumed_typical_current" | unit W', 'check "buffer_A + buffer_B + workspace <= memory_limit"',
                     'solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | within 0 1000 | step 1',
                     'range "voltage * assumed_typical_current" | given assumed_typical_current 240 260 | unit W'):
            self.line(rest, reader)
        refused = self.kernel.dispatch('tolerances.set', {**bound(self.problem), 'variable': 'voltage', 'said': 'percent', 'amount': '5',
                                                          'basis': 'invented'}, reader)
        self.assertFalse(refused['ok'])
        self.assertEqual((CAPABILITIES['tolerances.set'], CAPABILITIES['math.answer'], CAPABILITIES['tolerances.list']), ('approve', 'read', 'read'))
        self.assertEqual(stacy_hand.why_asks('tolerances.set'), 'a tolerance is yours to say: it decides what I conclude')
        for place in ('ask', 'show', 'free'):self.assertFalse(stacy_hand.hers(place, 'approve', 'tolerances.set'))

    def test_26_grammar(self):
        ident = self.problem['id']
        for program, code in (('math problem:%s | solve "workspace <= memory_limit"' % ident, 'STAC_MATH_SYNTAX'),
                              ('math problem:%s | check "workspace <= memory_limit"' % ident + ' | given workspace 1 2' * 5, 'STAC_MATH_GIVEN_BOUND'),
                              ('math problem:%s | solve "workspace <= memory_limit" for workspace | step 1 | within 0 9' % ident, 'STAC_MATH_STEP_ORDER'),
                              ('math problem:%s | check "workspace <= memory_limit" | given workspace one 2' % ident, 'STAC_MATH_NUMBER')):
            with self.assertRaises(ValueError) as caught:compile_program(program)
            self.assertEqual(str(caught.exception), code)
        plan = self.call('stac.inspect', {'program': 'math problem:%s | check "workspace <= memory_limit"' % ident})
        self.assertEqual((plan['operation'], plan['required_scope'], plan['executed']), ('math.answer', 'read', False))
        grammar = self.call('stac.status', {})['math_grammar']                  # the status names the maths steps too
        for word in ('calculate', 'solve', 'range', 'check', 'given'):self.assertIn(word, grammar)

    def test_a_line_kasandra_proposes_never_carries_a_range(self):
        given = 'math problem:%s | range "workspace" | given workspace 4 6' % self.problem['id']
        with self.assertRaises(ValueError) as caught:
            stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': given}}], operator(), provider=True, private_local=True)
        self.assertEqual(str(caught.exception), stacy_control.GIVEN_IS_THE_OWNERS)
        # whatever runs or keeps the line: investigation.step runs it at once, a check or the Agenda runs it later
        check = 'math problem:%s | check "workspace <= memory_limit" | given workspace 0 1' % self.problem['id']
        carried = (('investigation.step', {'id': '0' * 32, 'program': check, 'purpose': 'x'}),
                   ('investigation.check', {'claim': '0' * 32, 'program': check, 'oracle': 'x'}),
                   ('agenda.add', {'title': 'x', 'program': check}), ('agenda.suggest', {'parent': '0' * 32, 'title': 'x', 'why': 'x', 'program': check}),
                   ('stac.run', {'program': '\u200b explain ' + check}), ('stac.observe', {'program': '  ' + check}))
        for op, args in carried:
            with self.assertRaises(ValueError, msg=op) as caught:
                stacy_control.validate_actions([{'operation': op, 'arguments': args}], operator(), provider=True, private_local=True)
            self.assertEqual(str(caught.exception), stacy_control.GIVEN_IS_THE_OWNERS, op)
        with self.assertRaises(ValueError):
            stacy_control.validate_actions([{'operation': 'math.answer', 'arguments': {'id': self.problem['id'], 'stage': 'range', 'expression': 'workspace',
                                                                                    'given': [{'name': 'workspace', 'lo': '4', 'hi': '6'}]}}], operator(), provider=True, private_local=True)
        stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': given.split(' | given')[0]}}], operator(), provider=True, private_local=True)
        stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': given}}], operator())       # the owner may

    def test_a_given_on_the_quantity_solved_for_is_refused_not_dropped(self):
        said = self.line('solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | given assumed_typical_current 1 2')['result']
        self.assertEqual((said['state'], said['result']), ('UNSUPPORTED', None))
        self.assertIn('what is solved for', said['words']['answer'])

    def test_the_terminal_and_kasandra_offer_the_receipt_one_word_away(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
        from workbench import shell2
        from workbench.console_qt import Console
        QApplication.instance() or QApplication([])
        program = 'math problem:%s | solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | within 0 1000 | step 1' % self.problem['id']
        out = self.call('stac.run', {'program': program})

        class Terminal:
            link = Console.link
            def __init__(t):t.links = {};t.said = [];t.host = None;t.last_program = None
            def say(t, html, echo=None, **kw):t.said.append(html)
        terminal = Terminal()
        with patch('workbench.console_qt.call_write', return_value={'ok': True, 'result': out}):Console.run_stac(terminal, program)
        self.assertIn('Up to 300 mA', terminal.said[0])
        key = re.search(r'href="console:(\w+)">see the receipt<', terminal.said[0]).group(1)
        terminal.links[key]();self.assertIn('Guarantee: the exact allowed set', terminal.said[-1])

        class Face:
            def __init__(f):f.host = SimpleNamespace(root=self.root);f.said = [];f.bubbles = []
            def say(f, text):
                bubble = QWidget();bubble.box = QVBoxLayout(bubble);f.said.append(text);f.bubbles.append(bubble);return bubble
            def mark(f, *args):pass
        face = Face()
        with patch('workbench.engine.engineering', return_value=SimpleNamespace(dispatch=lambda op, args, p:{'ok': True, 'result': out})):
            shell2.SlateFace.execute(face, 'stac.run', {'program': program}, program)
        self.assertEqual(face.said[0], readable_result(out))
        words = [w for w in face.bubbles[0].findChildren(QLabel) if 'receipt' in (getattr(w, '_actions', None) or {})]
        self.assertEqual(len(words), 1);self.assertIn('see the receipt', words[0].text())
        words[0]._actions['receipt'][1]();self.assertTrue(face.said[-1].startswith('Receipt\n'), face.said[-1])

    def test_the_window_shows_the_answer_in_words_with_its_receipt(self):
        out = self.line('solve "assumed_typical_current <= declared_current_limit" for assumed_typical_current | within 0 1000 | step 1')
        shown = readable_result(out).split('\n')
        self.assertEqual(shown[:2], ['Solve for assumed_typical_current', 'Up to 300 mA, at declared_current_limit 300 mA.'])
        check = readable_result(self.line('check "buffer_A + buffer_B + workspace <= memory_limit"'))
        self.assertTrue(check.startswith('Does not hold\nbuffer_A + buffer_B + workspace <= memory_limit: it does not hold: over by 1 MiB.'), check)
        receipt = math_answers.receipt_text(out)
        self.assertIn('declared_current_limit: 300 mA · problem sheet, revision %d' % self.problem['revision'], receipt)
        self.assertIn('Guarantee: the exact allowed set', receipt)
        for text in (readable_result(out), receipt, check):
            self.assertIsNone(re.search(r'\b(staC|Lain|Programs|Ctrl|Alt\+|Shift\+)', text), text)


class RailDemoExamples(fixtures.ProblemBindings):
    """The three worked examples of docs/INTEGRATED_I02.md, on a problem sheet of Rail Demo's invented numbers."""
    def sheet(self):
        readings = {row[0]: row for row in rail_demo.READINGS};limits = {row[0]: row for row in rail_demo.LIMITS_B}
        folder = self.home / 'Rail_Demo_numbers';folder.mkdir()
        (folder / 'rail_numbers.md').write_text('%s\n\nRail voltage %s %s; settled current %s %s (bench readings). Settled power limit %s %s (limits Rev B).\n' % (
            rail_demo.NOTICE, *readings['Rail voltage'][1:3], *readings['Settled current'][1:3], *limits['Settled power limit'][1:3]))
        preview = self.call('imports.preview', {'source': str(folder), 'profile': 'ENGINEERING'})
        copy = self.call('imports.accept', {'id': preview['id'], 'expected_digest': preview['content_digest'], 'for_slate': True})
        def quantity(name, row, basis):return {'name': name, 'type': 'quantity', 'unit': row[2], 'state': 'KNOWN', 'value': row[1], 'basis': basis}
        return self.call('problems.create', {'request': 'Does the 12 V rail stay inside its settled power limit? ' + rail_demo.NOTICE,
            'title': 'Rail Demo rail power (invented data)', 'goals': ['Keep settled power inside the Rev B limit.'],
            'variables': [quantity('rail_voltage', readings['Rail voltage'], 'Rail Demo bench readings, invented'),
                          quantity('settled_current', readings['Settled current'], 'Rail Demo bench readings, invented'),
                          quantity('settled_power_limit', limits['Settled power limit'], 'Rail Demo limits Rev B, invented')],
            'sources': [{'copy': copy['id'], 'path': 'rail_numbers.md', 'label': 'Rail Demo numbers'}]})

    def test_the_three_worked_examples_are_true_word_for_word(self):
        text = DOC.read_text();part = text[text.index(EXAMPLES):]
        part = part[:part.index('\n## ')] if '\n## ' in part else part
        blocks = [block.strip('\n').split('\n') for block in re.findall(r'```text\n(.*?)```', part, re.S)]
        self.assertEqual(len(blocks), 3);self.assertIn('plus or minus 0.5 V', part)
        sheet = self.sheet()
        for index, (program, *expected) in enumerate(blocks):
            if index == 1:      # between the first and the second, the owner says the tolerance the page names
                self.call('tolerances.set', {**bound(sheet), 'variable': 'rail_voltage', 'said': 'plus_minus', 'amount': '0.5',
                                             'basis': 'Rail Demo, invented: the supply holds 12 V to half a volt'})
            out = self.call('stac.run', {'program': program.replace('problem:RAIL', 'problem:' + sheet['id'])})
            self.assertEqual(readable_result(out).split('\n'), expected, program)


# Only the tests above run here; the fixture's own tests run in test_problem.
for name in tuple(vars(fixtures.ProblemBindings)):
    if name.startswith('test_'):
        setattr(Lines, name, None);setattr(RailDemoExamples, name, None)


class SolversHidden(unittest.TestCase):
    """Vector 25: with the optional solvers out of reach (python -S leaves out site-packages), every answer is the same,
    and none of the new modules brings in SymPy or Z3."""
    CASES = (('calculate', 'voltage * current', {}, {}), ('solve', 'voltage * current <= limit', {'voltage': ('11.8', '12.2')}, {'for': 'current', 'step': '1'}),
             ('range', 'voltage * current', {'voltage': ('11.8', '12.2'), 'current': ('270', '290')}, {}),
             ('check', 'voltage * current <= limit', {'voltage': ('11.8', '12.2'), 'current': ('270', '500')}, {}))
    CHILD = ('import json,sys\nfrom workbench import math_answers as a, math_ranges, tolerances\nV=%r\nC=%r\n'
             'print(json.dumps({"digests":[a.ask(s,e,V,{k:{"range":v} for k,v in g.items()},q)["digest"] for s,e,g,q in C],'
             '"loaded":sorted(n for n in sys.modules if n.split(".")[0] in ("sympy","z3"))}))')
    VARIABLES = {'voltage': {'unit': 'V', 'value': '12'}, 'current': {'unit': 'mA', 'value': '280', 'lower': '0'}, 'limit': {'unit': 'W', 'value': '6'}}

    def test_25_every_answer_is_the_same_without_the_optional_solvers(self):
        here = [math_answers.ask(s, e, self.VARIABLES, {k: {'range': v} for k, v in g.items()}, q)['digest'] for s, e, g, q in self.CASES]
        child = subprocess.run([sys.executable, '-S', '-B', '-c', self.CHILD % (self.VARIABLES, self.CASES)], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(child.returncode, 0, child.stderr[-2000:])
        seen = json.loads(child.stdout.strip().splitlines()[-1])
        self.assertEqual((seen['digests'], seen['loaded']), (here, []))


if __name__ == '__main__':unittest.main()
