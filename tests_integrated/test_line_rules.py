"""0.8.4, what a line does with values (sdk/cli/arc1cli/typed_pipeline.py).

Seven faults were verified in the line evaluator on 14 November. Each has one test here, named for what must hold:

  1. a minus after an operator        add x = 2*-3 gave -3
  2. a number written as text         where v=1 skipped the text "1", over 0 kept it
  3. true is not 1                    group gathered true with 1
  4. a total never skips in silence   sum left out numeric text that had just passed a comparison (8 became 3)
  5. a space after a comma            select title, state was refused
  6. a quoted semicolon is data       refused, while a quoted bar passed
  7. a join's keys and names          keys were trimmed and case-folded; an existing other_* field was overwritten

One rule settles 2, 3, 4 and 7 and is pinned first: text that is exactly a number is that number, wherever a line compares,
gathers, joins, orders or adds values; true and false never are; all other text is taken exactly as written. The rest of the
module holds the same rule against the other steps (sort, add), the faults of the same kind found beside the seven, the
words each step gives, and the callers: the line panel's steps, the Then menu's values, and a line run through the Kernel.

After the independent review: a total and an add are worked out exactly and never rounded (they rounded to six decimals in
silence); a decimal too long for a float to hold stays the text it is (two different texts counted as one number); = reads
@NAME as the other comparisons do; a row without the field is on one side of = and is not; the Then menu and the panel
write a value with one function.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sdk.cli.arc1cli import typed_pipeline as lines

HOLDS = []


def setUpModule():
    # Nothing here may start a worker, submit a job or send a provider request (Graphite's test rule). Whether the packaged
    # seed is current is the release check's business: a stale one reads as bound here, as in the other behaviour tests.
    from workbench import clip, stacy_foundation
    from workbench.engineering_kernel import Kernel
    real_seed = stacy_foundation.seed_status
    def seed_status(root):
        value = real_seed(root)
        return {**value, 'state': 'VERIFIED_SOURCE_BINDINGS'} if value.get('state') in ('STALE', 'SOURCE_UNAVAILABLE') else value
    for held in (patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
                 patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')),
                 patch.object(clip, '_request', side_effect=AssertionError('No provider request')),
                 patch.object(stacy_foundation, 'seed_status', seed_status)):
        held.start();HOLDS.append(held)


def tearDownModule():
    while HOLDS:HOLDS.pop().stop()


def run(rows, steps, other=None):
    """The rows the steps give from `rows`, as the Kernel would apply them; `other` is a joined source's rows."""
    plan = lines.parse('jobs | ' + steps)
    transforms = [dict(step, rows=other) if step['kind'] in ('join', 'missing') else dict(step) for step in plan['transforms']]
    return lines.apply(rows, transforms)


def exact(value):
    """A value with its types kept apart (Python holds True == 1; JSON does not), for comparing answers."""
    return json.dumps(value, sort_keys=True)


def column(rows, name='v'):
    return [row[name] for row in rows]


class TheRule(unittest.TestCase):
    """Text that is exactly a number is that number; nothing else is."""

    def test_which_values_are_numbers(self):
        for value, number in ((12, 12), (-3, -3), (1.5, 1.5), ('12', 12), ('-12', -12), ('0', 0), ('-0', 0), ('1.0', 1.0), ('0.5', 0.5),
                              ('-0.5', -0.5), ('3e6', 3000000.0), ('1E-3', 0.001), ('1,200', 1200), ('-1,000', -1000),
                              ('12,345,678.5', 12345678.5), ('1' * 32, int('1' * 32)), ('1.10', 1.1), ('0.30000000000000004', 0.30000000000000004),
                              ('1234567890123456.8', 1234567890123456.8), ('1e-320', 1e-320), ('12345678901234567890', 12345678901234567890)):
            self.assertEqual(exact(lines.number(value)), exact(number), repr(value))
        for value in (True, False, None, '', ' ', '01', '007', '0805', ' 12', '12 ', '+5', '.5', '5.', '1,2', '1,2,3', '12,34',
                      '1,0000', '0,123', '1_000', 'inf', 'nan', 'Infinity', '0x10', '1e', 'e5', '1e999', '−3', '٣',
                      '12abc', '1 000', '1.2.3', '--1', '1' * 41, 'true', 'null', [1], {'a': 1}, float('inf'), float('nan'),
                      # a decimal a float cannot hold as written is not exactly a number: it stays text
                      '1234567890123456.78', '1731500000.123456789', '1e-400', '0.1000000000000000055511151231257827',
                      '12345678901234567890e0', '1,234,567,890,123,456.78', '1.1e-323'):
            self.assertIsNone(lines.number(value), repr(value))

    def test_which_values_are_the_same_value(self):
        for a, b in ((1, '1'), (1, 1.0), ('1', '1.0'), ('1e2', 100), ('1,000', 1000), (0, '-0'), ('a', 'a'), (True, True), (None, None),
                     ([1, 'a'], [1, 'a']), ({'a': 1}, {'a': 1})):
            self.assertTrue(lines.same(a, b), (a, b));self.assertTrue(lines.same(b, a), (b, a))
        for a, b in ((True, 1), (False, 0), (True, 'true'), (True, 'True'), (None, 'None'), (None, ''), (None, 0), ('', 0), ('a', 'A'),
                     ('a', ' a'), ('a', 'a '), ('01', 1), ('0805', 805), ('1', '1 '), ([1], [True]), ([1], '[1]'), (1, 2), ('1', '2')):
            self.assertFalse(lines.same(a, b), (a, b));self.assertFalse(lines.same(b, a), (b, a))

    def test_the_steps_say_the_rule_in_their_own_help_words(self):
        for step in ('where', 'group', 'sum', 'avg', 'min', 'max', 'add', 'join', 'missing', 'sort', 'select'):
            self.assertIn(step, lines.HELP, step)
        self.assertIn('exactly a number', lines.RULE);self.assertIn('exactly as written', lines.RULE)
        self.assertIn(lines.RULE, lines.HELP['where'])
        for step in ('group', 'sum', 'join', 'missing', 'sort', 'add'):self.assertIn('number', lines.HELP[step], step)
        self.assertIn('other_NAME', lines.HELP['join']);self.assertIn('overwritten', lines.HELP['join'])
        self.assertIn('exactly as written', lines.HELP['join']);self.assertIn('exactly as written', lines.HELP['missing'])
        self.assertIn('true and 1 stay apart', lines.HELP['group'])
        self.assertIn('how many', lines.HELP['sum']);self.assertIn('blank', lines.HELP['sum'])
        # a step written wrongly answers with its own help words
        for steps, step in (('where v', 'where'), ('group', 'group'), ('sum', 'sum'), ('select a b', 'select'), ('join nothing', 'join'),
                            ('missing nothing', 'missing'), ('sort 1', 'sort'), ('add x', 'add')):
            with self.assertRaises(ValueError) as refused:lines.parse('jobs | ' + steps)
            self.assertEqual(str(refused.exception), 'Write it as: ' + lines.HELP[step], 'the form comes first and is said once')
        self.assertIn('division by zero', lines.HELP['add']);self.assertIn('replaced', lines.HELP['add']);self.assertIn('never rounded', lines.HELP['add'])
        self.assertIn('never rounded', lines.HELP['sum']);self.assertIn('never rounded', lines.HELP['avg'])
        self.assertIn('a number one of the rows holds', lines.HELP['min']);self.assertIn('a number one of the rows holds', lines.HELP['max'])
        self.assertIn('@NAME', lines.HELP['where']);self.assertIn('without the FIELD', lines.HELP['where']);self.assertIn('15 digits', lines.RULE)
        # and no help word names the language, prints a key, or uses a word the window never shows
        for words in list(lines.HELP.values()) + [lines.RULE]:
            self.assertNotRegex(words, r'(?i)\bstac\b|pipeline|\bprograms?\b|\blain\b|ctrl|shift\+', words)


class TheSevenFaults(unittest.TestCase):
    def test_1_a_minus_after_an_operator(self):
        for expression, value in (('2*-3', -6), ('2--3', 5), ('10/-(2+3)', -2), ('-2*3', -6), ('2*-3*4', -24), ('--3', 3), ('(-3)', -3),
                                  ('2 * - 3', -6), ('2 -3', -1), ('-2-3', -5), ('2+-3', -1), ('6/-3', -2), ('-(-(2))', 2), ('1-2*-3', 7),
                                  ('2*-a', 6), ('-a*-a', 9), ('b--b', 1), ('-b/b', -1)):
            self.assertEqual(exact(run([{'a': -3, 'b': '0.5'}], 'add x = ' + expression)[0]['x']), exact(value), expression)
        for expression in ('2*', '*2', '2 3', '-', '2*/3', '2-', '(2', '2)', '2*+3', '2;3'):
            with self.assertRaises(ValueError, msg=expression):lines.parse('jobs | add x = ' + expression)
        # the plan keeps its form (numbers, fields and the four operators), so a plan kept from before still means the same
        program = lines.parse('jobs | add x = 2*-a')['transforms'][0]['expression']
        self.assertEqual({kind for kind, _ in program}, {'num', 'field', 'op'})
        self.assertLessEqual({value for kind, value in program if kind == 'op'}, {'+', '-', '*', '/'})

    def test_2_where_and_the_comparisons_read_a_number_written_as_text_the_same_way(self):
        rows = [{'v': v} for v in (1, '1', '1.0', 1.0, '1e0', True, 'x', '01', ' 1', '', None, 2, '2', -1, '-1', '1,000')]
        ones = [1, '1', '1.0', 1.0, '1e0']
        self.assertEqual(exact(column(run(rows, 'where v=1'))), exact(ones))
        self.assertEqual(exact(column(run(rows, 'where v over 0'))), exact(ones + [2, '2', '1,000']))
        self.assertEqual(exact(column(run(rows, 'where v at least 1 | where v at most 1'))), exact(ones), 'the same rows as v=1')
        self.assertEqual(exact(column(run(rows, 'where v="1"'))), exact(ones), 'quotes do not make a number into another value')
        self.assertEqual(exact(column(run(rows, 'where v=1.0'))), exact(ones))
        self.assertEqual(exact(column(run(rows, 'where v is not 1'))), exact([True, 'x', '01', ' 1', '', None, 2, '2', -1, '-1', '1,000']))
        self.assertEqual(exact(column(run(rows, 'where v != 1'))), exact(column(run(rows, 'where v is not 1'))))
        self.assertEqual(exact(column(run(rows, 'where v under 0'))), exact([-1, '-1']), 'negative numbers, as numbers and as text')
        self.assertEqual(exact(column(run(rows, 'where v=-1'))), exact([-1, '-1']))
        self.assertEqual(exact(column(run(rows, 'where v=1000'))), exact(['1,000']))
        # every row is on one side of = and is not, and = agrees with the two bounds, whatever the value
        for value in ('1', '2', '-1', '0', '"x"', 'true', '""', 'null', '1000', '01'):
            kept = column(run(rows, 'where v=' + value));left = column(run(rows, 'where v is not ' + value))
            self.assertEqual(len(kept) + len(left), len(rows), value)
            self.assertEqual(sorted(map(exact, kept + left)), sorted(map(exact, column(rows))), value)
        # true, false and nothing are not numbers and not text
        self.assertEqual(exact(column(run(rows, 'where v=true'))), exact([True]))
        self.assertEqual(exact(column(run(rows + [{'v': 'true'}], 'where v="true"'))), exact(['true']))
        self.assertEqual(exact(column(run(rows, 'where v=null'))), exact([None]))
        self.assertEqual(exact(column(run(rows, 'where v=""'))), exact(['']), 'empty text is empty text, not 0 and not nothing')
        self.assertEqual(exact(column(run(rows, 'where v=0'))), exact([]))
        # text that is not exactly a number is compared as written
        self.assertEqual(exact(column(run(rows, 'where v=01'))), exact(['01']))
        self.assertEqual(exact(column(run(rows, 'where v=" 1"'))), exact([' 1']))
        units = [{'v': v} for v in ('mA', 'MA', ' mA', 'mA ', 'ma')]
        self.assertEqual(column(run(units, 'where v=mA')), ['mA']);self.assertEqual(column(run(units, 'where v is not mA')), ['MA', ' mA', 'mA ', 'ma'])
        self.assertEqual(column(run(units, 'where v has MA')), ['mA', 'MA', ' mA', 'mA ', 'ma'], 'has looks anywhere, in any case')
        # two columns of one row follow the same rule: 10 is over 9 when both are written as text
        pairs = [{'a': '10', 'b': '9'}, {'a': 10, 'b': '9'}, {'a': '10', 'b': 9}, {'a': '9', 'b': '10'}, {'a': 'b', 'b': 'a'}, {'a': '10', 'b': 'x'}]
        self.assertEqual(exact(run(pairs, 'where a over @b')), exact(pairs[:3] + [pairs[4]]))
        # a number is never over or under a text; two texts that are not numbers stand in the order of their characters
        mixed = [{'v': v} for v in (12, '12', 'M', 'Z', 'a', True, None, '')]
        self.assertEqual(exact(column(run(mixed, 'where v over "M"'))), exact(['Z', 'a']))
        self.assertEqual(exact(column(run(mixed, 'where v at most "M"'))), exact(['M', '']))
        self.assertEqual(exact(column(run(mixed, 'where v at least 12'))), exact([12, '12']))

    def test_3_group_keeps_true_apart_from_one(self):
        rows = [{'v': v} for v in (True, 1, 1.0, '1', False, 0, 'true', None)]
        self.assertEqual(exact(run(rows, 'group v | count')),
                         exact([{'v': True, 'count': 1}, {'v': 1, 'count': 3}, {'v': False, 'count': 1}, {'v': 0, 'count': 1},
                                {'v': 'true', 'count': 1}, {'v': None, 'count': 1}]))
        # a group's count is the count where gives for the group's own value
        for group in run(rows, 'group v | count'):
            self.assertEqual(run(rows, 'where v=%s | count' % json.dumps(group['v'])), [{'count': group['count']}], group)
        self.assertEqual(exact(run(rows + [{}], 'group v | count')[-1]), exact({'v': None, 'count': 2}), 'a row without the field gathers with nothing')
        # text groups as written; "1.0" and "1" are one number; "01" is text
        rows = [{'v': v} for v in ('a', 'A', 'a ', 'a', '1', '1.0', '01', '', '')]
        self.assertEqual(exact(run(rows, 'group v | count')),
                         exact([{'v': 'a', 'count': 2}, {'v': 'A', 'count': 1}, {'v': 'a ', 'count': 1}, {'v': '1', 'count': 2},
                                {'v': '01', 'count': 1}, {'v': '', 'count': 2}]))
        # two fields, and totals by group
        rows = [{'u': 'mA', 'ok': True, 'q': 1}, {'u': 'mA', 'ok': 1, 'q': '2'}, {'u': 'mA', 'ok': True, 'q': 4}, {'u': 'V', 'ok': True, 'q': 8}]
        self.assertEqual(exact(run(rows, 'group u, ok | sum q')),
                         exact([{'u': 'mA', 'ok': True, 'sum_q': 5, 'count': 2}, {'u': 'mA', 'ok': 1, 'sum_q': 2, 'count': 1},
                                {'u': 'V', 'ok': True, 'sum_q': 8, 'count': 1}]))

    def test_4_a_total_adds_numbers_written_as_text_and_never_skips_in_silence(self):
        rows = [{'q': 3}, {'q': '5'}]
        self.assertEqual(exact(run(rows, 'where q over 0 | sum q')), exact([{'sum_q': 8, 'count': 2}]), 'what passed the comparison is added')
        self.assertEqual(exact(run(rows, 'avg q')), exact([{'avg_q': 4, 'count': 2}]))
        self.assertEqual(exact(run(rows, 'min q')), exact([{'min_q': 3, 'count': 2}]))
        self.assertEqual(exact(run(rows, 'max q')), exact([{'max_q': 5, 'count': 2}]))
        rows = [{'q': v} for v in (1, '1.0', '-2', '1,200', '2.5', '1e1')]
        self.assertEqual(exact(run(rows, 'sum q')), exact([{'sum_q': 1212.5, 'count': 6}]))
        self.assertEqual(exact(run(rows, 'min q')), exact([{'min_q': -2, 'count': 6}]))
        # whatever a comparison with a number keeps, a total can add: the two steps hold one rule
        values = [3, '5', 'n/a', True, None, '', '01', ' 7', '1,2', '0.5', -4, '-4', [1], '1e2']
        kept = run([{'q': v} for v in values], 'where q at least -1000000')
        self.assertEqual(exact(column(kept, 'q')), exact([3, '5', '0.5', -4, '-4', '1e2']))
        self.assertEqual(exact(lines.apply(kept, lines.parse('jobs | sum q')['transforms'])), exact([{'sum_q': 100.5, 'count': 6}]))
        # what cannot be added stops the step, with the count and the first of them: never a smaller total in silence
        with self.assertRaises(ValueError) as refused:run([{'q': 3}, {'q': 'n/a'}, {'q': '5'}, {'q': True}], 'sum q')
        self.assertRegex(str(refused.exception), r'^sum q refused: in 2 of 4 rows the value is not a number \(the first is "n/a"\)')
        for value in ('n/a', True, False, '01', ' 5', '5 ', '1,2', [1], {'a': 1}, 'inf'):
            for how in ('sum', 'avg', 'min', 'max'):
                with self.assertRaises(ValueError, msg=(how, value)) as refused:run([{'q': 3}, {'q': value}], how + ' q')
                self.assertIn('%s q refused: in 1 of 2 rows' % how, str(refused.exception))
        # a row with nothing there has nothing to add: the answer says how many such rows there were
        self.assertEqual(exact(run([{'q': 3}, {'q': None}, {'q': ''}, {}, {'q': '5'}], 'sum q')), exact([{'sum_q': 8, 'count': 5, 'blank': 3}]))
        self.assertEqual(exact(run([{'q': 3}, {'q': None}], 'avg q')), exact([{'avg_q': 3, 'count': 2, 'blank': 1}]), 'the average of what is there')
        self.assertEqual(exact(run([{'q': None}, {}], 'sum q')), exact([{'sum_q': None, 'count': 2, 'blank': 2}]))
        self.assertEqual(exact(run([{'u': 'V', 'q': '2'}, {'u': 'mA', 'q': None}, {'u': 'V', 'q': 1}], 'group u | sum q')),
                         exact([{'u': 'V', 'sum_q': 3, 'count': 2, 'blank': 0}, {'u': 'mA', 'sum_q': None, 'count': 1, 'blank': 1}]))
        self.assertEqual(exact(run([{'q': 0}, {'q': '0'}, {'q': 0.0}], 'sum q')), exact([{'sum_q': 0, 'count': 3}]), 'zero is a number, not a blank')

    def test_5_select_takes_a_space_after_the_comma(self):
        rows = [{'title': 'a', 'state': 'b', 'z': 1}]
        for steps in ('select title, state', 'select title,state', 'select title , state', 'select  title,  state '):
            self.assertEqual(run(rows, steps), [{'title': 'a', 'state': 'b'}], steps)
        self.assertEqual(lines.parse('jobs | select title, state')['transforms'], [{'kind': 'select', 'fields': ['title', 'state']}])
        for steps in ('select title state', 'select title,,state', 'select ,', 'select', 'select title;state', 'select ' + ','.join('f%d' % n for n in range(17))):
            with self.assertRaises(ValueError, msg=steps):lines.parse('jobs | ' + steps)
        # the same fault in the other list of a line: the rows to keep
        rows = [{'n': 1}, {'n': 2}, {'n': 3}]
        self.assertEqual(run(rows, 'keep rows 1, 3'), [{'n': 1}, {'n': 3}]);self.assertEqual(run(rows, 'keep rows 3,1'), [{'n': 1}, {'n': 3}])
        for steps in ('keep rows 1 3', 'keep rows 1,,3', 'keep rows 0, 1', 'keep rows 1, 1', 'keep rows'):
            with self.assertRaises(ValueError, msg=steps):lines.parse('jobs | ' + steps)

    def test_6_a_quoted_semicolon_is_data_like_a_quoted_bar(self):
        rows = [{'t': 'a;b'}, {'t': 'a|b'}, {'t': 'say "a;b"'}, {'t': 'ab'}]
        self.assertEqual(run(rows, 'where t="a;b"'), [{'t': 'a;b'}]);self.assertEqual(run(rows, 'where t="a|b"'), [{'t': 'a|b'}])
        self.assertEqual(run(rows, 'where t has "a;b"'), [{'t': 'a;b'}, {'t': 'say "a;b"'}])
        self.assertEqual(run(rows, r'where t="say \"a;b\""'), [{'t': 'say "a;b"'}], 'quotes inside quotes')
        self.assertEqual(run(rows, 'where t has ";" | where t has "|" | count'), [{'count': 0}])
        self.assertEqual(lines.split('jobs | where t="a;b|c" | count'), ['jobs', 'where t="a;b|c"', 'count'])
        self.assertEqual(lines.parse('files.find {"text":"a;b"} | count')['call']['arguments'], {'text': 'a;b'})
        # outside quotes it is still refused, and so is whatever a shell would run even inside them
        for text in ('jobs; ls', 'jobs | where t=a;b', 'jobs | where t="a";', 'jobs | where t="a" ; count', 'jobs | where t=\'a;b\'',
                     r'jobs | where t="a\";b', 'jobs | where t="`id`"', 'jobs | where t="$(id)"', 'jobs | where t="${HOME}"',
                     'jobs | where t="a>b"', 'jobs | where t="a<b"', 'jobs | where t="a\nb"'):
            with self.assertRaises(ValueError, msg=text):lines.parse(text)
        with self.assertRaises(ValueError) as refused:lines.parse('jobs | where t=a;b')
        self.assertIn('Shell syntax', str(refused.exception))
        # an address is written without quotes, so a semicolon in it is still refused, where the line starts and in a join
        from workbench.stacy_language import source
        self.assertEqual(lines.parse(source('@files:stock.csv | rows | where t="a;b"')[0])['transforms'][1], {'kind': 'where', 'field': 't', 'value': 'a;b'})
        for text in ('@files:a;b.csv | rows', '@files:stock.csv; ls | rows', '@files:stock.csv | rows | join @files:a;b.csv rows on t'):
            with self.assertRaises(ValueError, msg=text):lines.parse(source(text)[0])

    def test_7_a_join_matches_keys_as_written_and_overwrites_nothing(self):
        left = [{'k': 'A1', 'name': 'left', 'other_name': 'kept'}, {'k': ' a1 ', 'name': 'padded'}, {'k': 'a1', 'name': 'small'}]
        other = [{'k': 'a1', 'name': 'right small'}, {'k': 'A1', 'name': 'right capital'}]
        self.assertEqual(run(left, 'join @files:x.csv rows on k', other),
                         [{'k': 'A1', 'name': 'left', 'other_name': 'kept', 'other_name_2': 'right capital'},
                          {'k': 'a1', 'name': 'small', 'other_name_2': 'right small'}])
        self.assertEqual(run(left, 'missing @files:x.csv rows on k', other), [{'k': ' a1 ', 'name': 'padded'}])
        self.assertEqual(run(left, 'missing @files:x.csv rows on k', [{'k': 'a1'}]), [left[0], left[1]], 'A1 and the padded key are not a1')
        # numbers: 7 is "7" and "7.0"; "007" is text; true is not 1 or "true"; nothing is not the text None
        keys = [7, '7', '7.0', '007', True, 'true', None, 'None', '', 1]
        joined = run([{'k': k, 'n': n} for n, k in enumerate(keys)], 'join @files:x.csv rows on k',
                     [{'k': '7', 'side': 'seven'}, {'k': True, 'side': 'yes'}, {'k': 'None', 'side': 'text None'}, {'k': None, 'side': 'nothing'}, {'k': '', 'side': 'empty'}])
        self.assertEqual(exact([(row['k'], row['side']) for row in joined]),
                         exact([(7, 'seven'), ('7', 'seven'), ('7.0', 'seven'), (True, 'yes'), ('None', 'text None')]))
        self.assertEqual(exact(column(run([{'k': k} for k in keys], 'missing @files:x.csv rows on k', [{'k': 7.0}, {'k': 'true'}]), 'k')),
                         exact(['007', True, None, 'None', '', 1]))
        # a name means one thing in every row: it is settled once for the whole join, from every row of both sides
        left = [{'k': 1}, {'k': 2, 'state': 'here'}]
        self.assertEqual(run(left, 'join @files:x.csv rows on k', [{'k': 1, 'state': 'there'}, {'k': 2, 'state': 'there too'}]),
                         [{'k': 1, 'other_state': 'there'}, {'k': 2, 'state': 'here', 'other_state': 'there too'}])
        # the other source's own other_NAME keeps its name; the clash moves on to the next free one
        self.assertEqual(run([{'k': 1, 'x': 'mine'}], 'join @files:x.csv rows on k', [{'k': 1, 'x': 'theirs', 'other_x': 'their other'}]),
                         [{'k': 1, 'x': 'mine', 'other_x_2': 'theirs', 'other_x': 'their other'}])
        self.assertEqual(run([{'k': 1, 'x': 0, 'other_x': 1, 'other_x_2': 2}], 'join @files:x.csv rows on k', [{'k': 1, 'x': 3}]),
                         [{'k': 1, 'x': 0, 'other_x': 1, 'other_x_2': 2, 'other_x_3': 3}])
        # every value of both rows is still there after a join, whatever the names
        left = [{'k': 'p', 'a': 1, 'other_a': 2, 'b': 3}];other = [{'k': 'p', 'a': 4, 'other_a': 5, 'b': 6, 'c': 7}]
        row = run(left, 'join @files:x.csv rows on k', other)[0]
        self.assertEqual(sorted(v for v in row.values() if v != 'p'), [1, 2, 3, 4, 5, 6, 7]);self.assertEqual(len(row), 8)
        self.assertEqual({k: row[k] for k in left[0]}, left[0], 'this side is as it was')
        # the plan is as before: the Kernel resolves the other source
        self.assertEqual(lines.parse('jobs | join @files:x.csv rows on k')['transforms'], [{'kind': 'join', 'source': '@files:x.csv | rows', 'on': 'k'}])
        with self.assertRaises(ValueError):lines.apply(left, lines.parse('jobs | join @files:x.csv rows on k')['transforms'])


class TheSameKindOfFault(unittest.TestCase):
    """Found beside the seven: a silent coercion, skip or overwrite of the same kind, each fixed with the rule above."""

    def test_sort_orders_a_number_written_as_text_as_that_number(self):
        rows = [{'v': v} for v in ('110', '12', 9, 'b', None, 'A', '-3', 2.5, '1,000', '09')]
        self.assertEqual(exact(column(run(rows, 'sort v'))), exact(['-3', 2.5, 9, '12', '110', '1,000', '09', 'A', 'b', None]))
        self.assertEqual(exact(column(run(rows, 'sort -v'))), exact(['1,000', '110', '12', 9, 2.5, '-3', 'b', 'A', '09', None]))
        # what where calls the larger, sort puts later
        self.assertEqual(column(run(rows, 'where v over 10 | sort v')), ['12', '110', '1,000'])

    def test_add_reads_a_field_by_the_same_rule(self):
        rows = [{'a': '1,200', 'b': '0.5'}, {'a': '1,2', 'b': 1}, {'a': ' 5', 'b': 1}, {'a': True, 'b': 1}, {'a': '007', 'b': 1}, {'a': 4, 'b': 0},
                {'a': '-4', 'b': '-2'}]
        self.assertEqual(exact(column(run(rows, 'add x = a * b'), 'x')), exact([600, None, None, None, None, 0, 8]))
        self.assertEqual(exact(column(run(rows, 'add x = a / b'), 'x')), exact([2400, None, None, None, None, None, 2]), 'no division by nothing')
        self.assertEqual(exact(run([{'a': 1e308}], 'add x = a * 10')), exact([{'a': 1e308, 'x': None}]), 'too large to say: no value, never infinity')
        # brackets that hold no value were read as a sum that gave nothing for every row
        for expression in ('()', '2*(3+)', '2+()'):
            with self.assertRaises(ValueError, msg=expression):lines.parse('jobs | add x = ' + expression)

    def test_group_takes_a_list_and_refuses_to_overwrite_its_own_field(self):
        self.assertEqual(exact(run([{'v': [1]}, {'v': [1]}, {'v': [True]}, {'v': {'a': 1}}], 'group v | count')),
                         exact([{'v': [1], 'count': 2}, {'v': [True], 'count': 1}, {'v': {'a': 1}, 'count': 1}]))
        # a count or a total names its own fields (count, sum_q, blank): gathering by a field of that name would lose it
        rows = [{'count': 7, 'sum_q': 1, 'q': 1, 'blank': 0}, {'count': 7, 'sum_q': 1, 'q': 2, 'blank': 0}, {'count': 9, 'sum_q': 2, 'q': None, 'blank': 0}]
        for steps, name in (('group count | count', 'count'), ('group count | sum q', 'count'), ('group q, count | avg q', 'count'),
                            ('group sum_q | sum q', 'sum_q'), ('group blank | max q', 'blank')):
            with self.assertRaises(ValueError, msg=steps) as refused:run(rows, steps)
            self.assertIn('named ' + name, str(refused.exception), steps)
        self.assertEqual(run(rows[:2], 'group blank | max q'), [{'blank': 0, 'max_q': 2, 'count': 2}], 'no row is blank: nothing to overwrite')
        self.assertEqual(run(rows, 'group sum_q | count'), [{'sum_q': 1, 'count': 2}, {'sum_q': 2, 'count': 1}])

    def test_a_total_and_an_add_are_worked_out_exactly_and_never_rounded(self):
        # they rounded to six decimals in silence: max of 2.5e-6 and 1e-6 answered 3e-06, which no row holds, and small sums 0
        small = [{'q': 2.5e-6}, {'q': 1e-6}]
        self.assertEqual(exact(run(small, 'max q')), exact([{'max_q': 2.5e-06, 'count': 2}]))
        self.assertEqual(exact(run(small, 'min q')), exact([{'min_q': 1e-06, 'count': 2}]))
        self.assertEqual(exact(run(small, 'sum q')), exact([{'sum_q': 3.5e-06, 'count': 2}]))
        self.assertEqual(exact(run(small, 'avg q')), exact([{'avg_q': 1.75e-06, 'count': 2}]))
        self.assertEqual(exact(run([{'q': 1.5e-7}, {'q': '2.5e-7'}], 'sum q')), exact([{'sum_q': 4e-07, 'count': 2}]))
        self.assertEqual(exact(run([{'q': 2.5e-7}], 'add x = q*2')), exact([{'q': 2.5e-07, 'x': 5e-07}]))
        # min and max give a number one of the rows holds
        values = [0.1234567891, '7.000000001', 3, '2.50', 1e-9, -1e-12]
        for how in ('min', 'max'):
            self.assertIn(run([{'q': v} for v in values], how + ' q')[0][how + '_q'], [lines.number(v) for v in values], how)
        # worked out from the numbers as written, so 0.1 and 0.2 make 0.3 with nothing rounded away
        self.assertEqual(exact(run([{'q': 0.1}, {'q': 0.2}], 'sum q')), exact([{'sum_q': 0.3, 'count': 2}]))
        self.assertEqual(exact(run([{'q': '0.1'}, {'q': 0.2}, {'q': '0.7'}], 'sum q')), exact([{'sum_q': 1, 'count': 3}]))
        self.assertEqual(exact(run([{'q': 0.1}] * 10, 'sum q')), exact([{'sum_q': 1, 'count': 10}]))
        self.assertEqual(exact(run([{'q': 1}, {'q': 2}, {'q': 2}], 'avg q')), exact([{'avg_q': 5 / 3, 'count': 3}]))
        row = {'a': 0.1, 'b': '0.2', 'c': 3}
        for expression, value in (('a+b', 0.3), ('a*c', 0.3), ('b-a', 0.1), ('1/c', 1 / 3), ('a/b', 0.5), ('c*c/c', 3), ('a*10', 1), ('1.1*1.1', 1.21)):
            self.assertEqual(exact(run([row], 'add x = ' + expression)[0]['x']), exact(value), expression)
        # whole numbers stay whole and exact at any length; an add works out only the operation asked for (a + b gave no
        # value above 1e308, because the division was tried too)
        big = 10 ** 309
        self.assertEqual(run([{'a': big, 'b': 1}], 'add x = a + b')[0]['x'], big + 1)
        self.assertEqual(run([{'a': '9007199254740993', 'b': 2}], 'add x = a * b')[0]['x'], 18014398509481986)
        self.assertEqual(run([{'a': big, 'b': 10}], 'add x = a / b')[0]['x'], 10 ** 308)
        self.assertEqual(run([{'q': '9007199254740993'}, {'q': 1}], 'sum q'), [{'sum_q': 9007199254740994, 'count': 2}])
        self.assertEqual(run([{'q': big}, {'q': big}], 'avg q'), [{'avg_q': big, 'count': 2}])
        self.assertEqual(run([{'q': big}, {'q': big + 2}], 'max q'), [{'max_q': big + 2, 'count': 2}])
        # an answer no number can say stops a total and gives an add no value: never infinity, never 0 for what is not 0
        with self.assertRaises(ValueError) as refused:run([{'q': 1e308}, {'q': 1e308}], 'sum q')
        self.assertEqual(str(refused.exception), 'sum q refused: the answer is too large or too small to give as a number here')
        self.assertEqual(exact(run([{'q': 1e308}, {'q': 1e308}], 'avg q')), exact([{'avg_q': 1e308, 'count': 2}]), 'the average itself can be said')
        with self.assertRaises(ValueError) as refused:run([{'q': 5e-324}, {'q': 0}], 'avg q')
        self.assertIn('avg q refused: the answer is too large or too small', str(refused.exception))
        self.assertEqual(exact(run([{'a': 1e-200}], 'add x = a * a')[0]['x']), exact(None), 'too small to say: no value, never 0')
        self.assertEqual(exact(run([{'a': 1e-200}], 'add x = a * a * 0')[0]['x']), exact(0))

    def test_a_decimal_too_long_to_hold_exactly_stays_the_text_it_is(self):
        # two different numbers written as text counted as one value when a float could not tell them apart
        a, b = '1234567890123456.78', '1234567890123456.79'
        self.assertFalse(lines.same(a, b));self.assertFalse(lines.same(a, 1234567890123456.8));self.assertTrue(lines.same(a, a))
        self.assertEqual(run([{'k': a, 'n': 1}], 'join @files:x.csv rows on k', [{'k': b, 'm': 2}]), [])
        self.assertEqual(run([{'k': a, 'n': 1}], 'join @files:x.csv rows on k', [{'k': a, 'm': 2}]), [{'k': a, 'n': 1, 'm': 2}])
        self.assertEqual(run([{'k': a}], 'missing @files:x.csv rows on k', [{'k': b}]), [{'k': a}])
        stamps = [{'t': '1731500000.123456789'}, {'t': '1731500000.123456790'}]
        self.assertEqual(run(stamps, 'group t | count'), [dict(row, count=1) for row in stamps])
        rows = [{'v': '1e-400'}, {'v': 0}, {'v': a}, {'v': b}, {'v': 1234567890123456.8}, {'v': '1234567890123456.8'}]
        self.assertEqual(exact(column(run(rows, 'where v=0'))), exact([0]))
        self.assertEqual(exact(column(run(rows, 'where v=' + a))), exact([a]), 'written out in a where, it is that text')
        self.assertEqual(exact(column(run(rows, 'where v=1234567890123456.8'))), exact([1234567890123456.8, '1234567890123456.8']))
        self.assertEqual(exact(column(run(rows, 'where v over 1'))), exact([1234567890123456.8, '1234567890123456.8']), 'a text is never over a number')
        self.assertEqual(exact(column(run(rows, 'sort v'))), exact([0, 1234567890123456.8, '1234567890123456.8', a, b, '1e-400']))
        # a total refuses it with the count, and says why a text that looks like a number is not one; an add gives no value
        with self.assertRaises(ValueError) as refused:run(rows, 'sum v')
        self.assertIn('sum v refused: in 3 of 6 rows the value is not a number (the first is "1e-400")', str(refused.exception))
        self.assertIn('more than about 15 digits', str(refused.exception))
        with self.assertRaises(ValueError) as refused:run([{'v': 1}, {'v': 'n/a'}], 'sum v')
        self.assertNotIn('15 digits', str(refused.exception))
        self.assertEqual(exact(column(run(rows, 'add x = v * 1'), 'x')), exact([None, 0, None, None, 1234567890123456.8, 1234567890123456.8]))
        # written into an add it is refused, never shortened; a number a float holds is taken as before
        with self.assertRaises(ValueError) as refused:lines.parse('jobs | add x = v * 1234567890123456.78')
        self.assertIn('more digits than a number holds exactly', str(refused.exception))
        self.assertEqual(run([{'v': 2}], 'add x = v * 0.125 + 007')[0]['x'], 7.25)
        # a whole number is held exactly at any length, as a number or as text
        self.assertFalse(lines.same('12345678901234567890', '12345678901234567891'));self.assertTrue(lines.same(12345678901234567890, '12345678901234567890'))
        self.assertFalse(lines.same(2 ** 53 + 1, float(2 ** 53)))
        self.assertEqual(run([{'k': '12345678901234567890'}], 'join @files:x.csv rows on k', [{'k': 12345678901234567891, 'm': 1}]), [])

    def test_a_comparison_with_another_field_and_a_row_without_the_field(self):
        # = read @w as the text "@w" while is not, over and the rest read the field w, so a row could be on neither side
        rows = [{'v': 1, 'w': 1}, {'v': 1, 'w': 2}, {'v': '2', 'w': 2.0}, {'v': 'a', 'w': 'A'}]
        self.assertEqual(run(rows, 'where v=@w'), [rows[0], rows[2]]);self.assertEqual(run(rows, 'where v is not @w'), [rows[1], rows[3]])
        self.assertEqual(run(rows, 'where v at least @w | where v at most @w'), [rows[0], rows[2]])
        # in double quotes it is the text, for = and for the other comparisons; the plan says so
        homes = [{'h': '@home', 'home': 'x'}, {'h': 'x', 'home': 'x'}]
        self.assertEqual(run(homes, 'where h="@home"'), [homes[0]]);self.assertEqual(run(homes, 'where h is not "@home"'), [homes[1]])
        self.assertEqual(run(homes, 'where h=@home'), [homes[1]]);self.assertEqual(run(homes, 'where h has "@ho"'), [homes[0]])
        self.assertEqual(lines.parse('jobs | where h="@home"')['transforms'], [{'kind': 'where', 'field': 'h', 'value': '@home', 'text': True}])
        self.assertEqual(lines.parse('jobs | where h=@home')['transforms'], [{'kind': 'where', 'field': 'h', 'value': '@home'}])
        self.assertEqual(lines.apply(homes, [{'kind': 'compare', 'field': 'h', 'op': '!=', 'value': '@home'}]), [homes[0]], 'a plan kept from before means the same')
        # a row without the field has nothing there: it is on one side of = and is not, as group gathers it
        states = [{'state': 'done'}, {'state': 'open'}, {}, {'state': None}]
        self.assertEqual(run(states, 'where state is not done'), states[1:]);self.assertEqual(run(states, 'where state=done'), states[:1])
        self.assertEqual(run(states, 'where state=null'), states[2:])
        for group in run(states, 'group state | count'):
            self.assertEqual(run(states, 'where state=%s | count' % json.dumps(group['state'])), [{'count': group['count']}], group)
        self.assertEqual(run(states, 'where state over a'), states[:2], 'nothing is never over or under anything')
        self.assertEqual(run(states, 'where state has n'), states[:2])

    def test_a_join_on_a_field_inside_a_field_finds_it_on_both_sides(self):
        left = [{'part': {'id': 'R1'}, 'n': 1}, {'part': {'id': 'R2'}, 'n': 2}]
        other = [{'part': {'id': 'R2'}, 'price': 3}]
        self.assertEqual(run(left, 'join @files:x.csv rows on part.id', other), [{'part': {'id': 'R2'}, 'n': 2, 'other_part': {'id': 'R2'}, 'price': 3}])
        self.assertEqual(run(left, 'missing @files:x.csv rows on part.id', other), [left[0]])


class TheCallers(unittest.TestCase):
    """The line panel's steps and the Then menu write lines that run, and count by the same rule."""

    def held(self, rows):
        from workbench import line_steps
        address = 'office:owner:' + 'a' * 32
        def dispatch(operation, arguments):
            if operation == 'language.parse':
                return {'ok': True, 'result': {'call': {'operation': 'ledger.address.read', 'arguments': {'address': address}}, 'address': address, 'seed_id': 's'}}
            return {'ok': True, 'result': {'object': {'origin': {'reviewed_rows': rows}}}}
        base = '@%s | pick origin.reviewed_rows' % address
        return line_steps, line_steps.Held(dispatch).read(base), base

    def test_the_panel_counts_and_offers_by_the_evaluators_rule(self):
        line_steps, held, base = self.held([{'part': 'R1; R2', 'value': '12', 'kind': 'null', 'size': '0805'}, {'part': 'C1', 'value': '110', 'kind': 'x', 'size': '0805'},
                                            {'part': 'R1; R2', 'value': 9, 'kind': 'null', 'size': '805'}, {'part': 'U1', 'value': '1,000', 'kind': 'y', 'size': 805}])
        for value in (12, '12', '1,000', ' 12', '0805', True, None, 'x', '1,2'):
            self.assertEqual(exact(line_steps.number(value)), exact(lines.number(value)), repr(value))
        # a number column written as text is offered by value, and each offer keeps what it says
        offers = line_steps.values(held, base, 'value')
        self.assertEqual([(o.words, o.count) for o in offers], [('at least 12', 3), ('at least 110', 2), ('at least 1000', 1), ('at most 9', 1), ('at most 12', 2), ('at most 110', 3)])
        for offer in offers:self.assertEqual(held.count(line_steps.with_step(base, offer.step)), offer.count, offer.step)
        # a value with a semicolon is offered in quotes, and the line runs; the text "null" is offered as text
        offers = {o.words: o for o in line_steps.values(held, base, 'part')}
        self.assertEqual(offers['is R1; R2'].step, 'where part="R1; R2"');self.assertEqual(offers['is R1; R2'].count, 2)
        self.assertEqual(held.rows(line_steps.with_step(base, offers['is not R1; R2'].step) + ' | select part'), [{'part': 'C1'}, {'part': 'U1'}])
        self.assertEqual(line_steps.literal('null'), '"null"');self.assertEqual({o.words: o.count for o in line_steps.values(held, base, 'kind')}['is null'], 2)
        self.assertEqual((line_steps.literal('mA'), line_steps.literal('a;b'), line_steps.literal('a|b'), line_steps.literal('12'), line_steps.literal(' a')),
                         ('mA', '"a;b"', '"a|b"', '"12"', '" a"'))
        self.assertEqual(line_steps.literal('@home'), '"@home"', 'bare, @home would name a field')
        for text in ('mA', 'a;b', 'a|b', '12', ' a', 'null', 'true', 'R1; R2', '0805'):
            self.assertEqual(exact(lines.parse('jobs | where f=' + line_steps.literal(text))['transforms'][0]['value']), exact(text), text)
        # Sort by offers a number column however it is written (it now sorts by value), never a column of numbers and words
        self.assertEqual(line_steps.sortable(held, base), ['part', 'value', 'kind'])
        self.assertEqual(column(held.rows(base + ' | sort value'), 'value'), [9, '12', '110', '1,000'])
        # Count by gathers as group does: 0805 twice, and 805 with "805"
        self.assertIn('size', line_steps.groupable(held, base))
        self.assertEqual(exact(held.rows(base + ' | group size | count')), exact([{'size': '0805', 'count': 2}, {'size': '805', 'count': 2}]))
        line_steps, held, base = self.held([{'n': 1}, {'n': '1.0'}, {'n': True}, {'n': 2}])
        self.assertEqual(line_steps.groupable(held, base), ['n'], '1 and "1.0" are one value: there is something to count by')
        line_steps, held, base = self.held([{'n': 1}, {'n': True}, {'n': 'True'}])
        self.assertEqual(line_steps.groupable(held, base), [], 'true, 1 and the text True are three values')
        # a column named count is not offered to count by: the step would be refused (the answer has its own count)
        line_steps, held, base = self.held([{'unit': 'V', 'count': 2}, {'unit': 'V', 'count': 2}, {'unit': 'mA', 'count': 1}])
        self.assertEqual(line_steps.groupable(held, base), ['unit'])
        with self.assertRaises(line_steps.Refusal) as refused:held.rows(base + ' | group count | count')
        self.assertIn('named count', str(refused.exception))

    def test_a_refused_total_reaches_the_panel_in_plain_words(self):
        line_steps, held, base = self.held([{'q': 3}, {'q': 'n/a'}])
        with self.assertRaises(line_steps.Refusal) as refused:held.rows(base + ' | sum q')
        self.assertIn('1 of 2 rows', str(refused.exception));self.assertNotRegex(str(refused.exception), r'(?i)stac|pipeline|language')
        # a sign that cannot stand in a line: the words say where a semicolon can
        with self.assertRaises(line_steps.Refusal) as refused:held.rows(base + ' | where q=a;b')
        self.assertEqual(str(refused.exception), 'Those signs cannot be part of a line; a bar or a semicolon is text only inside double quotes')
        # a step written wrongly reaches the panel as its own help words, said once
        with self.assertRaises(line_steps.Refusal) as refused:held.rows(base + ' | sum')
        self.assertEqual(str(refused.exception), 'Write it as: ' + lines.HELP['sum'])

    def test_the_then_menu_and_the_panel_write_a_value_with_one_function(self):
        # the menu left true, null and NaN bare and took quote marks out, so "is true" kept none of the rows holding that text
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from workbench import chain_menu, line_steps
        for text in ('mA', 'a b', 'R1; R2', 'a;b', 'a|b', 'true', 'false', 'null', 'NaN', 'Infinity', '12', '1e3', '0805', 'say "x"', ' a', '@home',
                     'back\\slash', ''):
            self.assertEqual(chain_menu.word(text), line_steps.literal(text), text)
            step = lines.parse('jobs | where part = %s' % chain_menu.word(text))['transforms'][0]
            self.assertEqual(exact((step['field'], step['value'])), exact(('part', text)), text)
            self.assertEqual(run([{'part': text}, {'part': 'other'}, {'part': True}, {'part': None}], 'where part = %s' % chain_menu.word(text)), [{'part': text}], text)
        self.assertEqual((chain_menu.word('mA'), chain_menu.word('a;b'), chain_menu.word('true'), chain_menu.word(True), chain_menu.word(5)),
                         ('mA', '"a;b"', '"true"', 'true', '5'))

    def test_the_then_menu_reads_a_number_column_by_the_same_rule(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication, QMenu
        from workbench import chain_menu
        app = QApplication.instance() or QApplication([]);self.assertIsNotNone(app)
        for values, answer in ((['12', '110', 9], True), ([1, 2.5, None, ''], True), (['1,200', '3e2'], True), (['12', 'x'], False), ([True, 1], False),
                               (['0805', '12'], False), ([' 12'], False), ([None, ''], False), ([], False)):
            self.assertEqual(chain_menu.numeric(values), answer, values)
        def runner(rows):
            return lambda host, program:(lines.apply(rows, lines.parse(program)['transforms']), None)
        # Keep rows where: a number column written as text is offered by value, and each offer says what it keeps
        rows = [{'v': '12'}, {'v': '110'}, {'v': 9}, {'v': None}];made = [];menu = QMenu()
        with patch.object(chain_menu, 'run', runner(rows)), \
             patch.object(chain_menu, 'link', lambda menu, host, program, label, rows=None, error=None, leaf=False:made.append((program, label, len(rows)))):
            chain_menu.where_values(menu, None, 'jobs', 'v', [row['v'] for row in rows])
        self.assertEqual(made[:3], [('jobs | where v over 9', '9', 2), ('jobs | where v over 12', '12', 1), ('jobs | where v over 110', '110', 0)])
        self.assertEqual(made[-3:], [('jobs | where v at most 9', '9', 1), ('jobs | where v at most 12', '12', 2), ('jobs | where v at most 110', '110', 3)])
        # a text column: the text true and the value true are offered apart and each keeps its own rows; NaN is text, and runs
        rows = [{'f': 'true'}, {'f': 'true'}, {'f': True}, {'f': 'NaN'}, {'f': None}];made = [];menu = QMenu()
        with patch.object(chain_menu, 'run', runner(rows)), \
             patch.object(chain_menu, 'link', lambda menu, host, program, label, rows=None, error=None, leaf=False:made.append((program, label, len(rows)))):
            chain_menu.where_values(menu, None, 'jobs', 'f', [row['f'] for row in rows])
        self.assertEqual(made[:3], [('jobs | where f = "true"', 'true', 2), ('jobs | where f = true', 'True', 1), ('jobs | where f = "NaN"', 'NaN', 1)])
        self.assertEqual(made[3:6], [('jobs | where f is not "true"', 'true', 3), ('jobs | where f is not true', 'True', 4), ('jobs | where f is not "NaN"', 'NaN', 4)])
        self.assertEqual(made[6:], [('jobs | where f has "true"', 'true', 3), ('jobs | where f has True', 'True', 3), ('jobs | where f has "NaN"', 'NaN', 1)])
        # group by: totals are offered for it, a column named count is not gathered by, and every line the menu writes runs
        rows = [{'u': 'V', 'q': '2', 'count': 1}, {'u': 'mA', 'q': 5, 'count': 1}, {'u': 'V', 'q': '1,000', 'count': 3}];made = [];run = runner(rows)
        with patch.object(chain_menu, 'run', run), \
             patch.object(chain_menu, 'link', lambda menu, host, program, label, rows=None, error=None, leaf=False:made.append(program)):
            chain_menu.shape(menu, None, 'jobs', rows)
        self.assertIn('jobs | group u | sum q', made);self.assertIn('jobs | group u | count', made);self.assertNotIn('jobs | group count | count', made)
        for program in made:run(None, program)
        self.assertEqual(run(None, 'jobs | group u | sum q')[0], [{'u': 'V', 'sum_q': 1002, 'count': 2}, {'u': 'mA', 'sum_q': 5, 'count': 1}])

    def test_lines_run_through_the_kernel(self):
        from workbench import locations
        from workbench.baseline import environment
        from workbench.engineering_kernel import Kernel, operator
        temporary = tempfile.TemporaryDirectory(prefix='line-rules-test-');self.addCleanup(temporary.cleanup)
        base = Path(temporary.name);root = base / 'Office'
        env = patch.dict(os.environ, environment(os.environ, root, base / 'profile'));env.start();self.addCleanup(env.stop)
        locations.office(root);kernel = Kernel(root);owner = operator('owner')
        files = root / 'Files';files.mkdir(exist_ok=True)
        (files / 'stock.csv').write_text('Part,Need,Have,Note\nR1,12,5,first; second\nr1,3,8,plain\nC1,2,2,plain\n')
        (files / 'prices.csv').write_text('Part,Price,Note\nR1,2,theirs\nC1,3,theirs\n')
        (files / 'readings.txt').write_text('12\n5\n-3\n')
        def rows(text):
            answer = kernel.dispatch('language.run', {'text': text}, owner)
            if not answer['ok']:raise ValueError(answer['error']['message'])
            return answer['result']['rows']
        self.assertEqual(rows('@files:stock.csv | rows | add Twice = Need*-2 | select Part, Twice'),
                         [{'Part': 'R1', 'Twice': -24}, {'Part': 'r1', 'Twice': -6}, {'Part': 'C1', 'Twice': -4}])
        self.assertEqual(rows('@files:stock.csv | rows | where Note has "first; second" | select Part'), [{'Part': 'R1'}])
        self.assertEqual(rows('@files:stock.csv | rows | join @files:prices.csv rows on Part | select Part, Note, other_Note, Price'),
                         [{'Part': 'R1', 'Note': 'first; second', 'other_Note': 'theirs', 'Price': 2}, {'Part': 'C1', 'Note': 'plain', 'other_Note': 'theirs', 'Price': 3}])
        self.assertEqual(rows('@files:stock.csv | rows | missing @files:prices.csv rows on Part | select Part'), [{'Part': 'r1'}], 'r1 is not R1')
        # a text file's lines are text: the numbers written there compare, gather and add as numbers
        self.assertEqual(rows('@files:readings.txt | lines | where text over 0 | sum text'), [{'sum_text': 17, 'count': 2}])
        self.assertEqual(rows('@files:readings.txt | lines | where text=12 | select text'), [{'text': '12'}])
        self.assertEqual(rows('@files:readings.txt | lines | sort text | select text'), [{'text': '-3'}, {'text': '5'}, {'text': '12'}])
        # nothing is rounded on the way: the largest of four small readings is one of them, and their sum is their sum
        (files / 'parts.csv').write_text('Part,Leak\nA,0.0000025\nB,0.0000015\nC,0.000001\nD,0.000001\n')
        self.assertEqual(exact(rows('@files:parts.csv | rows | max Leak')), exact([{'max_Leak': 2.5e-06, 'count': 4}]))
        self.assertEqual(exact(rows('@files:parts.csv | rows | sum Leak')), exact([{'sum_Leak': 6e-06, 'count': 4}]))
        self.assertEqual(exact(rows('@files:parts.csv | rows | add Ten = Leak*10 | where Part=A | select Ten')), exact([{'Ten': 2.5e-05}]))
        # a cell that says NaN or inf is a word, not a number no record can hold: the file's other rows still answer
        (files / 'odd.csv').write_text('Part,Q\nA,NaN\nB,inf\nC,2\nD,-Infinity\n')
        self.assertEqual(rows('@files:odd.csv | rows | where Q over 1 | select Part'), [{'Part': 'C'}])
        self.assertEqual(rows('@files:odd.csv | rows | where Q is not 2 | select Q'), [{'Q': 'NaN'}, {'Q': 'inf'}, {'Q': '-Infinity'}])
        (files / 'readings.txt').write_text('12\n5\nnot read\n')
        answer = kernel.dispatch('language.run', {'text': '@files:readings.txt | lines | sum text'}, owner)
        self.assertFalse(answer['ok']);self.assertIn('sum text refused: in 1 of 3 rows the value is not a number (the first is "not read")', answer['error']['message'])


if __name__ == '__main__':
    unittest.main()
