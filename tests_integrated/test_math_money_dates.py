"""Money and dates, exactly, on the one maths core (0.8.5, "Maths in lines", the second maths item): amounts in a currency
as exact decimals, refused across currencies unless the owner gives a rate, rounded only when asked and by one named rule;
calendar dates, the days between them, months the calendar's way, business days, deadlines with the end day stated, and
dates inside solve, range and check. Every vector is exact and invented. The lines run through the line compiler as the
owner types them; the worked examples of docs/INTEGRATED_I02.md run in a Kernel word for word. No model and no window."""
import ast
import json
import os
import random
import re
import tempfile
import unittest
from datetime import date, timedelta
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
from workbench import local_brain, locations, math_answers, math_dates as md, math_money as mm, stacy_control
from workbench.baseline import environment
from workbench.engineering_kernel import CAPABILITIES, Kernel, operator
from workbench.office_building_qt import readable_result
from workbench.stac_bridge import compile_program, gives_ranges

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs' / 'INTEGRATED_I02.md'
SECTION = '## Money and dates in lines (0.8.5)'
NEW = ('workbench/math_typed.py', 'workbench/math_money.py', 'workbench/math_dates.py')
HIDDEN = re.compile(r'\b(staC|Lain|Programs|Ctrl|Alt\+|Shift\+|math\.money|math\.dates|HALF_AWAY|DIMENSION_MISMATCH|UNSUPPORTED|CLAMP|GIVEN_IN_LINE|FREED|n\d+)\b')


def rec(record):return F(record['rational'])


def ask(program):
    """A money or dates line as the owner types it, compiled as the window compiles it and answered without a Kernel."""
    ir = compile_program(program)['ir']
    return {'math.money': mm.answer, 'math.dates': md.answer}[ir['operation']](ir['arguments'])


def text(said):return '\n'.join([said['words']['heading'], said['words']['answer'], *said['words']['lines'], *said['words']['receipt']])


class Money(unittest.TestCase):
    def test_sums_are_exact_decimals_never_floating_point(self):
        said = ask('math money | calculate "0.10 USD + 0.20 USD"')
        self.assertEqual((said['state'], rec(said['result']['value']), said['result']['value']['unit']), ('ANSWERED', F(3, 10), 'USD'))
        self.assertEqual((said['schema'], said['guarantee'], said['words']['answer']), ('ledger.math-answer/1', 'EXACT_VALUE', '0.10 USD + 0.20 USD = 0.30 USD.'))
        self.assertEqual(ask('math money | check "0.10 USD + 0.20 USD == 0.30 USD"')['state'], 'HOLDS')
        self.assertEqual(rec(ask('math money | calculate "3 * 19.99 EUR"')['result']['value']), F(5997, 100))
        third = ask('math money | calculate "100 USD / 3"')
        self.assertEqual(rec(third['result']['value']), F(100, 3));self.assertNotIn('rounded', third['result'])     # never rounded unasked
        self.assertIn('exact 100/3 USD', third['words']['answer'])
        ratio = ask('math money | calculate "1200 USD / 300 USD"')['result']['value']
        self.assertEqual((rec(ratio), ratio['unit']), (4, '1'))
        named = ask('math money | calculate "12 * rent" | given rent 950.50 USD')
        self.assertEqual((rec(named['result']['value']), named['inputs'][0]['unit'], named['inputs'][0]['origin']), (F(11406), 'USD', 'GIVEN_IN_LINE'))

    def test_different_currencies_are_refused_in_words_unless_the_owner_gives_a_rate(self):
        for program in ('math money | calculate "10 USD + 5 EUR"', 'math money | check "10 USD <= 5 EUR"',
                        'math money | calculate "rent + 5 EUR" | given rent 950 USD'):
            said = ask(program)
            self.assertEqual((said['state'], said['result']), ('DIMENSION_MISMATCH', None), program)
            for word in ('USD', 'EUR', 'exchange rate'):self.assertIn(word, said['words']['answer'], program)
        for program in ('math money | calculate "10 USD + 5"', 'math money | calculate "10 USD * 2 USD"', 'math money | calculate "5 / 2 USD"'):
            self.assertEqual(ask(program)['state'], 'DIMENSION_MISMATCH', program)
        unknown = ask('math money | calculate "10 XQZ"')
        self.assertEqual(unknown['state'], 'UNSUPPORTED');self.assertIn('XQZ', unknown['words']['answer'])
        rated = ask('math money | calculate "10 USD + 5 EUR" | rate EUR USD 1.08')
        self.assertEqual((rec(rated['result']['value']), rated['result']['value']['unit']), (F('15.40'), 'USD'))
        self.assertEqual(rated['money']['rates'], [{'from': 'EUR', 'to': 'USD', 'rate': '1.08'}])
        self.assertIn('1 EUR = 1.08 USD', '\n'.join(rated['words']['receipt']))

    def test_rounding_only_when_asked_half_away_from_zero_with_the_exact_value_beside(self):
        for amount, step, expected in (('10.125', '0.01', '10.13'), ('10.135', '0.01', '10.14'), ('-10.125', '0.01', '-10.13'),
                                       ('0.005', '0.01', '0.01'), ('2.5', '1', '3'), ('-2.5', '1', '-3'), ('10.124', '0.01', '10.12'),
                                       ('10.126', '0.01', '10.13'), ('0.125', '0.05', '0.15')):
            said = ask('math money | calculate "%s USD" | round %s' % (amount, step));rounded = said['result']['rounded']
            self.assertEqual((rec(rounded['value']), rounded['rule'], rec(said['result']['value'])), (F(expected), 'HALF_AWAY_FROM_ZERO', F(amount)), amount)
        said = ask('math money | calculate "10.125 USD" | round 0.01')
        self.assertIn('10.13 USD', said['words']['answer']);self.assertIn('exact 10.125 USD', said['words']['answer'])
        self.assertIn('half away from zero', '\n'.join(said['words']['receipt']))
        span = ask('math money | range "(2200 USD - rent) / 3" | given rent 950 1000 USD | round 0.01')
        self.assertEqual([rec(x) for x in span['result']['range']], [400, F(1250, 3)])
        self.assertEqual([rec(x) for x in span['result']['rounded']['range']], [400, F('416.67')])

    def test_a_rounded_split_shows_the_exact_value_once(self):
        said = ask('math money | calculate "10 USD / 3" | round 0.01')
        self.assertEqual(said['words']['answer'], '10 USD / 3 = 3.33 USD, rounded to 0.01 USD half away from zero (exact 10/3 USD).')

    def test_a_bad_rounding_step_or_a_broken_question_is_a_refusal_never_an_exception(self):
        for args in ({'stage': 'calculate', 'expression': '1 USD', 'round': '0'}, {'stage': 'calculate', 'expression': '1 USD', 'round': '-1'},
                     {'stage': 'calculate', 'expression': '1 USD', 'round': '1/3'}, {'stage': 'calculate'}, {'expression': '1 USD'},
                     {'stage': 'solve', 'expression': '4 * weekly <= 1200 USD'}, {'stage': 'calculate', 'expression': 'x', 'given': [{'lo': '1'}]}):
            said = mm.answer(args)
            self.assertIn(said['state'], math_answers.ERRORS, args);self.assertIsNone(said['result'], args)
            self.assertTrue(said['words']['answer'].startswith('Cannot work it out: '), args)

    def test_amounts_written_another_way_are_refused_with_how_to_write_them(self):
        for program, word in (('math money | calculate "1,200 USD"', 'comma'), ('math money | calculate "10 usd"', 'capitals'),
                              ('math money | calculate "$10"', 'three letters'), ('math money | calculate "1e3 USD"', 'plain decimal')):
            said = ask(program)
            self.assertEqual(said['state'], 'UNSUPPORTED', program);self.assertIn(word, said['words']['answer'], program)
        both = ask('math money | solve "x * x <= 100 USD" for x')          # each kind x could be, with its own reason
        self.assertEqual(both['state'], 'DIMENSION_MISMATCH')
        for said in ('If x is a plain number', 'If x is an amount in USD', 'not money'):self.assertIn(said, both['words']['answer'])

    def test_a_budget_solve_and_a_budget_range(self):
        said = ask('math money | solve "4 * weekly <= 1200 USD" for weekly')
        found = said['result']['allowed']
        self.assertEqual((found['state'], rec(found['upper']['value']), found['upper']['closed'], found['unit'], found['lower']), ('ALLOWED', 300, True, 'USD', None))
        self.assertEqual((said['guarantee'], said['inputs'][0]['unit'], said['inputs'][0]['origin']), ('EXACT_ALLOWED_SET', 'USD', 'FREED'))
        self.assertTrue(said['words']['answer'].startswith('Up to 300.00 USD'), said['words']['answer'])
        robust = ask('math money | solve "rent + 4 * weekly <= 2200 USD" for weekly | step 0.01 | given rent 950 1000 USD')['result']['allowed']
        self.assertEqual((rec(robust['upper']['value']), rec(robust['lattice']['upper']), rec(robust['ends'][0]['corner']['rent'])), (300, 300, 1000))
        span = ask('math money | range "(2200 USD - rent) / 4" | given rent 950 1000 USD')
        self.assertEqual(([rec(x) for x in span['result']['range']], span['result']['range'][0]['unit'], span['guarantee']), ([300, F(625, 2)], 'USD', 'EXACT_RANGE'))
        self.assertIn('300.00 to 312.50 USD', span['words']['answer'])
        thirds = ask('math money | solve "3 * weekly <= 1000 USD" for weekly | step 0.01')['result']['allowed']
        self.assertEqual(rec(thirds['lattice']['upper']), F('333.33'))                          # in whole cents, inward

    def test_two_loans_compared_by_total_repaid(self):
        said = ask('math money | check "24 * 212.50 EUR <= 36 * 148.90 EUR + 150 EUR"')
        result = said['result']
        self.assertEqual((said['state'], rec(result['slack'][0]), rec(result['left'][0]), rec(result['right'][0])), ('HOLDS', F('410.40'), 5100, F('5510.40')))
        self.assertIn('410.40 EUR to spare', said['words']['answer'])


class Dates(unittest.TestCase):
    def test_days_between_across_a_leap_day(self):
        said = ask('math dates | calculate "2028-03-01 - 2028-02-28"');value = said['result']['value']
        self.assertEqual((said['state'], rec(value), value['unit']), ('ANSWERED', 2, 'days'))
        self.assertIn('2 days', said['words']['answer'])
        self.assertEqual(rec(ask('math dates | calculate "2027-03-01 - 2027-02-28"')['result']['value']), 1)

    def test_31_january_plus_one_month_is_clamped_to_the_months_last_day(self):
        said = ask('math dates | calculate "2026-01-31 + 1 month"')
        self.assertEqual((said['result']['value']['iso'], said['result']['value']['unit'], said['calendar']['month_end']), ('2026-02-28', 'date', 'CLAMP_TO_LAST_DAY'))
        self.assertIn('Saturday 2026-02-28', said['words']['answer'])
        self.assertIn("month's last day", text(said))
        for program, iso in (('"2028-01-31 + 1 month"', '2028-02-29'), ('"2028-02-29 + 1 year"', '2029-02-28'), ('"2026-03-31 - 1 month"', '2026-02-28'),
                             ('"2026-01-15 + 1 month"', '2026-02-15'), ('"2026-11-20 + 2 weeks"', '2026-12-04'), ('"2026-10-31 + 4 months"', '2027-02-28')):
            self.assertEqual(ask('math dates | calculate ' + program)['result']['value']['iso'], iso, program)

    def test_the_receipt_says_when_the_month_end_rule_applied_and_only_then(self):
        clamped, plain = ask('math dates | calculate "2026-01-31 + 1 month"'), ask('math dates | calculate "2026-01-15 + 1 month"')
        self.assertEqual((clamped['calendar']['steps'][0]['clamped'], plain['calendar']['steps'][0]['clamped']), (True, False))
        self.assertIn('February 2026 has only 28 days', text(clamped));self.assertNotIn('has only', text(plain))
        self.assertIn('since that month has no such day', text(ask('math dates | deadline 1 month after 2026-01-31 | end included')))
        self.assertNotIn('since that month has no such day', text(ask('math dates | deadline 1 month after 2026-01-15 | end included')))

    def test_a_name_given_one_date_counts_months_years_and_business_days(self):
        said = ask('math dates | calculate "d + 1 month" | given d 2026-01-31')
        self.assertEqual((said['state'], said['result']['value']['iso'], said['calendar']['steps'][0]['clamped']), ('ANSWERED', '2026-02-28', True))
        self.assertIn('Saturday 2026-02-28', said['words']['answer']);self.assertIn('d (Saturday 2026-01-31) + 1 month is Saturday 2026-02-28', text(said))
        self.assertEqual(ask('math dates | calculate "service + 10 business days" | given service 2026-11-20')['result']['value']['iso'], '2026-12-04')
        self.assertEqual(ask('math dates | calculate "service + 1 year - 1 day" | given service 2028-02-29')['result']['value']['iso'], '2029-02-27')
        holds = ask('math dates | check "2026-12-19 <= service + 1 month" | given service 2026-11-20')
        fails = ask('math dates | check "2026-12-21 <= service + 1 month" | given service 2026-11-20')
        self.assertEqual((holds['state'], rec(holds['result']['slack'][0]), fails['state'], rec(fails['result']['slack'][0])), ('HOLDS', 1, 'FAILS', -1))
        ranged = ask('math dates | calculate "d + 1 month" | given d 2026-01-30 2026-01-31')         # a range has no one day to count from
        self.assertEqual(ranged['state'], 'UNSUPPORTED');self.assertIn('one date', ranged['words']['answer'])

    def test_a_month_or_business_day_anywhere_but_on_the_date_that_starts_a_sum_is_refused(self):
        for program in ('"2026-12-01 - 2026-01-31 + 1 month"', '"30 days + 2026-01-31 + 1 month"', '"2026-01-31 + 1 month * 2"', '"2 * 2026-01-31 + 1 month"'):
            said = ask('math dates | calculate ' + program)
            self.assertEqual((said['state'], said['result']), ('UNSUPPORTED', None), program);self.assertIn('starts a sum', said['words']['answer'], program)
        self.assertEqual(ask('math dates | calculate "2026-01-31 + 1 month + 2 days"')['result']['value']['iso'], '2026-03-02')     # left to right
        self.assertEqual(rec(ask('math dates | calculate "(2026-01-31 + 1 month) - 2026-01-31"')['result']['value']), 28)
        for program, word in (('"20.11.2026 + 30 days"', 'year-month-day'), ('"2026-11-20 + 1 Month"', 'small letters'),
                              ('"2026-11-20 + 1 businessday"', 'two words')):
            said = ask('math dates | calculate ' + program)
            self.assertEqual(said['state'], 'UNSUPPORTED', program);self.assertIn(word, said['words']['answer'], program)

    def test_a_date_outside_the_years_1_to_9999_is_refused(self):
        for program in ('"9999-12-31 + 1 day"', '"0001-01-01 - 1 day"', '"9999-12-31 + 1 month"', '"9999-12-31 + 1 business day"'):
            self.assertEqual(ask('math dates | calculate ' + program)['state'], 'DOMAIN_ERROR', program)
        self.assertEqual(ask('math dates | deadline 1 day after 9999-12-31')['state'], 'DOMAIN_ERROR')
        self.assertEqual(ask('math dates | calculate "9999-12-30 + 1 day"')['result']['value']['iso'], '9999-12-31')

    def test_the_weekday_of_a_date(self):
        said = ask('math dates | calculate "2026-11-20"')
        self.assertEqual((said['result']['value']['iso'], said['words']['answer']), ('2026-11-20', '2026-11-20 = Friday 2026-11-20.'))

    def test_business_days_across_a_weekend(self):
        said = ask('math dates | business days 2026-11-20 2026-11-23')
        self.assertEqual((said['state'], rec(said['result']['value'])), ('ANSWERED', 1))
        self.assertIn('no holidays counted', text(said).lower())
        self.assertEqual(rec(ask('math dates | business days 2026-11-20 2026-12-04')['result']['value']), 10)
        self.assertEqual(ask('math dates | calculate "2026-11-20 + 1 business day"')['result']['value']['iso'], '2026-11-23')
        self.assertEqual(ask('math dates | calculate "2026-11-20 + 10 business days"')['result']['value']['iso'], '2026-12-04')
        held = ask('math dates | calculate "2026-11-20 + 1 business day" | holidays 2026-11-23')
        self.assertEqual((held['result']['value']['iso'], held['calendar']['holidays']), ('2026-11-24', ['2026-11-23']))
        self.assertIn('2026-11-23', '\n'.join(held['words']['receipt']));self.assertIn('your list', '\n'.join(held['words']['receipt']))
        self.assertEqual(rec(ask('math dates | business days 2026-11-20 2026-11-24 | holidays 2026-11-23')['result']['value']), 1)

    def test_a_holiday_on_a_weekend_takes_no_business_day_away(self):
        self.assertEqual(rec(ask('math dates | business days 2026-11-20 2026-11-23 | holidays 2026-11-21')['result']['value']), 1)
        self.assertEqual(ask('math dates | calculate "2026-11-20 + 1 business day" | holidays 2026-11-22')['result']['value']['iso'], '2026-11-23')
        self.assertEqual(ask('math dates | calculate "2026-11-20 + 30 business days" | holidays 2026-11-28 2026-12-25')['result']['value']['iso'], '2027-01-04')

    def test_a_deadline_with_the_end_day_included_and_excluded(self):
        included = ask('math dates | deadline 30 days after 2026-11-20 | end included')['result']['deadline']
        excluded = ask('math dates | deadline 30 days after 2026-11-20 | end excluded')['result']['deadline']
        self.assertEqual((included['end']['iso'], included['last_day']['iso'], included['end_day']), ('2026-12-20', '2026-12-20', 'included'))
        self.assertEqual((excluded['end']['iso'], excluded['last_day']['iso'], excluded['end_day']), ('2026-12-20', '2026-12-19', 'excluded'))
        said = ask('math dates | deadline 30 days after 2026-11-20 | end included')
        for word in ('30 days after Friday 2026-11-20', 'Sunday 2026-12-20', 'included'):self.assertIn(word, said['words']['answer'] + '\n'.join(said['words']['lines']))
        unsaid = ask('math dates | deadline 30 days after 2026-11-20')
        self.assertIsNone(unsaid['result']['deadline']['end_day'])            # no hidden convention: both are shown
        self.assertIn('Sunday 2026-12-20', unsaid['words']['answer']);self.assertIn('Saturday 2026-12-19', unsaid['words']['answer'])
        month = ask('math dates | deadline 1 month after 2026-01-31 | end included')['result']['deadline']
        self.assertEqual(month['end']['iso'], '2026-02-28')
        business = ask('math dates | deadline 10 business days after 2026-11-20 | end included')['result']['deadline']
        self.assertEqual(business['end']['iso'], '2026-12-04')

    def test_end_excluded_at_its_edges(self):
        for program in ('deadline 0 days after 2026-11-20', 'deadline 1 day after 2026-11-20 | end excluded', 'deadline 1 business day after 2026-11-20 | end excluded'):
            said = ask('math dates | ' + program)
            self.assertEqual((said['state'], said['result']), ('UNSUPPORTED', None), program)
        two = ask('math dates | deadline 2 business days after 2026-11-20 | end excluded')['result']['deadline']
        self.assertEqual((two['end']['iso'], two['last_day']['iso']), ('2026-11-24', '2026-11-23'))
        monday = ask('math dates | deadline 2 business days after 2026-11-19 | end excluded')['result']['deadline']
        self.assertEqual((monday['end']['iso'], monday['last_day']['iso']), ('2026-11-23', '2026-11-20'))      # the business day before, not Sunday
        unsaid = ask('math dates | deadline 1 day after 2026-11-20')
        self.assertEqual((unsaid['state'], unsaid['result']['deadline']['last_day_if_excluded']), ('ANSWERED', None))
        self.assertIn('no day is left inside it', unsaid['words']['answer'])
        for args in ({'stage': 'deadline'}, {'stage': 'deadline', 'count': '-30', 'unit': 'days', 'after': '2026-11-20'},
                     {'stage': 'deadline', 'count': '30', 'unit': 'fortnights', 'after': '2026-11-20'}, {'stage': 'business', 'from': '2026-11-20'},
                     {'stage': 'solve', 'expression': 'd - 2026-11-20 <= 30 days'}, {'stage': 'later'}, {'stage': 'calculate', 'expression': 'd', 'given': [{'lo': '2026-11-20'}]}):
            said = md.answer(args)
            self.assertIn(said['state'], math_answers.ERRORS, args);self.assertTrue(said['words']['answer'].startswith('Cannot work it out: '), args)

    def test_a_date_check_holding_and_failing(self):
        late = ask('math dates | check "2026-12-21 <= deadline" | given deadline 2026-12-20')
        self.assertEqual((late['state'], rec(late['result']['slack'][0]), late['result']['slack'][0]['unit']), ('FAILS', -1, 'days'))
        self.assertEqual(late['words']['heading'], 'Does not hold');self.assertIn('1 day', late['words']['answer'])
        early = ask('math dates | check "2026-12-18 <= deadline" | given deadline 2026-12-20')
        self.assertEqual((early['state'], rec(early['result']['slack'][0])), ('HOLDS', 2))
        ruled = ask('math dates | check "2026-12-21 <= service + 30 days" | given service 2026-11-20')
        self.assertEqual(ruled['state'], 'FAILS')
        ranged = ask('math dates | check "2026-12-19 <= deadline" | given deadline 2026-12-18 2026-12-22')
        self.assertEqual((ranged['state'], ranged['for_all']), ('UNDECIDED', 'FAILS_FOR_SOME'))

    def test_solve_and_range_over_dates(self):
        said = ask('math dates | solve "deadline - 2026-11-20 <= 30 days" for deadline')
        found = said['result']['allowed']
        self.assertEqual((found['unit'], found['upper']['value']['iso'], said['inputs'][0]['unit']), ('date', '2026-12-20', 'date'))
        self.assertTrue(said['words']['answer'].startswith('On or before Sunday 2026-12-20'), said['words']['answer'])
        span = ask('math dates | range "deadline - start" | given start 2026-11-01 2026-11-05 | given deadline 2026-12-20')
        self.assertEqual(([rec(x) for x in span['result']['range']], span['result']['range'][0]['unit']), ([45, 49], 'days'))

    def test_what_makes_no_sense_on_a_calendar_is_refused_in_words(self):
        for program in ('math dates | calculate "2026-11-20 + 2026-11-21"', 'math dates | calculate "2026-11-20 + 30"',
                        'math dates | calculate "2026-11-20 * 2"'):
            said = ask(program)
            self.assertEqual((said['state'], said['result']), ('DIMENSION_MISMATCH', None), program)
            self.assertIsNone(HIDDEN.search(said['words']['answer']), said['words']['answer'])
        self.assertEqual(ask('math dates | calculate "2026-02-30 - 2026-02-01"')['state'], 'DOMAIN_ERROR')
        self.assertIn('2026-02-30', ask('math dates | calculate "2026-02-30 - 2026-02-01"')['words']['answer'])


class Properties(unittest.TestCase):
    def test_adding_then_subtracting_days_returns_the_date(self):
        rng = random.Random(85)
        for _ in range(30):
            day = date.fromordinal(rng.randint(date(1900, 1, 1).toordinal(), date(2200, 12, 31).toordinal()));n = rng.randint(0, 4000)
            said = ask('math dates | calculate "%s + %d days - %d days"' % (day.isoformat(), n, n))
            self.assertEqual(said['result']['value']['iso'], day.isoformat())
            self.assertEqual(md.step_days(md.step_days(day, n), -n), day)
            self.assertEqual(md.step_days(day, n), day + timedelta(days=n))

    def test_rounding_never_moves_an_amount_by_more_than_half_a_cent(self):
        rng = random.Random(805);cent = F(1, 100)
        for _ in range(3000):
            x = F(rng.randint(-10 ** 9, 10 ** 9), rng.choice((1, 2, 4, 8, 200, 1000, rng.randint(1, 10 ** 6))));r = mm.half_away(x, cent)
            self.assertLessEqual(abs(r - x), cent / 2);self.assertEqual((r / cent).denominator, 1)
            if abs(r - x) == cent / 2:self.assertGreater(abs(r), abs(x))                       # an exact half goes away from zero

    def test_business_day_steps_and_counts_agree(self):
        rng = random.Random(1120)
        for _ in range(80):
            day = date(2026, 1, 1) + timedelta(days=rng.randint(0, 700));n = rng.randint(0, 400)
            held = [day + timedelta(days=rng.randint(-20, 600)) for _ in range(rng.randint(0, 8))]
            later = md.step_business(day, n, held)
            self.assertEqual(md.count_business(day, later, held), n)
            if n:self.assertLess(later.weekday(), 5);self.assertNotIn(later, held)
            earlier = md.step_business(later, -n, held)                     # and back: never past the start, on the n-th business day before
            self.assertLessEqual(earlier, day);self.assertEqual(md.count_business(earlier, later, held), n)

    def test_a_long_business_day_count_takes_whole_weeks_at_once(self):
        with patch.object(md, 'step_days', wraps=md.step_days) as stepped:
            later = md.step_business(date(2026, 11, 20), 2000000, [date(2026, 12, 25)])
        self.assertLess(stepped.call_count, 100)
        self.assertEqual(md.count_business(date(2026, 11, 20), later, [date(2026, 12, 25)]), 2000000)


class Exactness(unittest.TestCase):
    def test_no_float_and_no_optional_solver_in_the_new_modules(self):
        for path in NEW:
            tree = ast.parse((ROOT / path).read_text())
            for node in ast.walk(tree):
                self.assertFalse(isinstance(node, ast.Constant) and isinstance(node.value, float), (path, getattr(node, 'lineno', 0)))
                self.assertFalse(isinstance(node, ast.Name) and node.id == 'float', (path, getattr(node, 'lineno', 0)))
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'math':
                    self.assertIn(node.attr, ('floor', 'ceil'), (path, node.lineno))
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [getattr(node, 'module', None) or ''] + [alias.name for alias in node.names]
                    self.assertFalse(any(n.split('.')[0] in ('sympy', 'z3', 'decimal') or n.endswith('math_backend') for n in names), (path, names))

    def test_the_answers_hash_their_own_implementation_and_name_no_model(self):
        said = ask('math money | calculate "1 USD"')
        self.assertEqual(set(said['implementation']) >= {'math_typed.py', 'math_money.py', 'math_dates.py', 'math_ranges.py', 'math_answers.py'}, True)
        self.assertEqual((said['model_calls'], said['physical_qualification']), (0, False))


class Lines(unittest.TestCase):
    """The lines in a Kernel, as the window runs them: words, the receipt one word away, the owner's numbers his own."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='graphite-money-dates-');self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name);home = base / 'Home';home.mkdir();self.root = base / 'Office'
        env = patch.dict(os.environ, {**environment(os.environ, self.root, base / 'profile'), 'HOME': str(home)});env.start();self.addCleanup(env.stop)
        homed = patch.object(Path, 'home', return_value=home);homed.start();self.addCleanup(homed.stop)
        locations.office(self.root);self.kernel = Kernel(self.root);self.p = operator()

    def run_line(self, program):
        response = self.kernel.dispatch('stac.run', {'program': program}, self.p)
        self.assertTrue(response['ok'], response);return response['result']

    def test_the_lines_run_in_the_kernel_with_words_and_a_receipt(self):
        out = self.run_line('math money | solve "4 * weekly <= 1200 USD" for weekly')
        self.assertEqual((out['freshness'], CAPABILITIES['math.money'], CAPABILITIES['math.dates']), ('CURRENT', 'read', 'read'))
        self.assertTrue(readable_result(out).startswith('Solve for weekly\nUp to 300.00 USD'), readable_result(out))
        self.assertIn('not financial or legal advice', math_answers.receipt_text(out))
        plan = self.kernel.dispatch('stac.inspect', {'program': 'math dates | business days 2026-11-20 2026-11-23'}, self.p)['result']
        self.assertEqual((plan['operation'], plan['required_scope'], plan['executed']), ('math.dates', 'read', False))
        grammar = self.kernel.dispatch('stac.status', {}, self.p)['result']['math_grammar']
        for word in ('math money', 'math dates', 'round', 'rate', 'deadline', 'business days', 'holidays'):self.assertIn(word, grammar)
        for program in ('math money | calculate "10 USD + 5 EUR"', 'math money | calculate "10.125 USD" | round 0.01',
                        'math dates | deadline 30 days after 2026-11-20', 'math dates | check "2026-12-21 <= deadline" | given deadline 2026-12-20',
                        'math money | range "(2200 USD - rent) / 4" | given rent 950 1000 USD',
                        'math dates | calculate "service + 10 business days" | given service 2026-11-20',
                        'math money | calculate "10 USD / 3" | round 0.01'):
            out = self.run_line(program)
            for said in (readable_result(out), math_answers.receipt_text(out)):self.assertIsNone(HIDDEN.search(said), said)
        for op, args in (('math.money', {'stage': 'calculate', 'expression': '1 USD', 'round': '0'}), ('math.dates', {'stage': 'deadline'}),
                         ('math.dates', {'stage': 'deadline', 'count': '-30', 'unit': 'days', 'after': '2026-11-20'})):
            response = self.kernel.dispatch(op, args, self.p)       # a refusal in words, never an exception or a bare error
            self.assertTrue(response['ok'], (op, args, response));self.assertIn(response['result']['state'], math_answers.ERRORS, args)

    def test_grammar(self):
        for program, code in (('math money | solve "4 * weekly <= 1200 USD"', 'STAC_MATH_SYNTAX'),
                              ('math money | calculate "1 USD" | round 0.01 | given x 1', 'STAC_MATH_STEP_ORDER'),
                              ('math money | calculate "1 USD" | given x one', 'STAC_MATH_NUMBER'),
                              ('math money | calculate "1 USD" | round 0', 'STAC_MATH_NUMBER'),
                              ('math dates | deadline 30 days after 2026-11-20 | end sometimes', 'STAC_MATH_SYNTAX'),
                              ('math dates | deadline thirty days after 2026-11-20', 'STAC_MATH_NUMBER'),
                              ('math dates | business days 2026-11-20', 'STAC_MATH_SYNTAX'),
                              ('math dates | calculate "2026-11-20" | holidays tomorrow', 'STAC_MATH_DATE'),
                              ('math cash | calculate "1 USD"', 'STAC_MATH_PROBLEM_ID')):
            with self.assertRaises(ValueError, msg=program) as caught:compile_program(program)
            self.assertEqual(str(caught.exception), code, program)

    def test_ranges_rates_and_holidays_are_the_owners_never_proposed(self):
        for program in ('math money | range "(2200 USD - rent) / 4" | given rent 950 1000 USD', 'math money | calculate "10 USD + 5 EUR" | rate EUR USD 1.08',
                        'math dates | calculate "2026-11-20 + 1 business day" | holidays 2026-11-23', 'math dates | range "d - 2026-11-01" | given d 2026-11-02 2026-11-09'):
            self.assertTrue(gives_ranges(program), program)
            with self.assertRaises(ValueError) as caught:
                stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': program}}], operator(), provider=True, private_local=True)
            self.assertEqual(str(caught.exception), stacy_control.GIVEN_IS_THE_OWNERS, program)
            stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': program}}], operator())     # the owner may
        ir = compile_program('math money | calculate "10 USD + 5 EUR" | rate EUR USD 1.08')['ir']
        with self.assertRaises(ValueError):
            stacy_control.validate_actions([{'operation': ir['operation'], 'arguments': ir['arguments']}], operator(), provider=True, private_local=True)
        for program in ('math money | calculate "12 * rent" | given rent 950 USD', 'math dates | deadline 30 days after 2026-11-20 | end included'):
            self.assertFalse(gives_ranges(program), program)
            stacy_control.validate_actions([{'operation': 'stac.run', 'arguments': {'program': program}}], operator(), provider=True, private_local=True)

    def test_kasandra_is_offered_money_and_dates_for_a_budget_or_a_deadline_and_not_for_a_plot(self):
        from workbench.engineering_cli import schemas
        from workbench.tool_selection import relevant
        def offered(text, limit=6):return [row['operation'] for row in relevant(text, CAPABILITIES, schemas(), limit)]
        self.assertIn('math.money', offered('what can I spend each week and stay under the monthly budget'))
        self.assertIn('math.dates', offered('when does the notice period end, 30 days after service'))
        self.assertFalse({'math.money', 'math.dates'} & set(offered('plot the voltage against time from the csv')))
        self.assertNotIn('math.dates', offered('what can I spend each week and stay under the monthly budget'))       # one schema, not both
        self.assertNotIn('math.money', offered('when does the notice period end, 30 days after service'))
        self.assertIn('math.dates', offered('when is a payment due 10 business days after the invoice'))
        budget = 'what can I spend each week and stay under the monthly budget'      # not also the sheet's maths for the shared word
        self.assertFalse({'math.answer', 'math.calculate'} & set(offered(budget)))
        power = offered('check the power budget of the board', 50)          # an engineering budget is the calculator's, not money
        self.assertIn('math.answer', power);self.assertNotIn('math.money', power)
        self.assertLess(len(json.dumps(local_brain.proposal_profile(budget)[1], separators=(',', ':'))), 5000)
        # everyday words (a price, a cost, a day, a month, a payment) do not bring them in: each schema is over a thousand characters,
        # and the plan for one message stays under the bound the smallest model's context sets (test_tool_selection)
        for message in ('open the price list sheet', 'list the documents due this month', 'how much did the parts cost in total',
                        'what files did I edit in the last 3 days', 'what was the payment for the invoice', 'show the network traffic rate today'):
            self.assertFalse({'math.money', 'math.dates'} & set(offered(message)), message)
            self.assertLess(len(json.dumps(local_brain.proposal_profile(message)[1], separators=(',', ':'))), 5000, message)

    def test_the_worked_examples_on_the_lines_page_are_true_word_for_word(self):
        page = DOC.read_text();part = page[page.index(SECTION):]
        part = part[:part.index('\n## ', 1)] if '\n## ' in part[1:] else part
        blocks = [block.strip('\n').split('\n') for block in re.findall(r'```text\n(.*?)```', part, re.S)]
        self.assertGreaterEqual(len(blocks), 4)
        self.assertEqual(len(re.findall(r'not (?:financial|legal)|financial or legal advice', part)), 1)    # said once, in one sentence
        for program, *expected in blocks:
            self.assertEqual(readable_result(self.run_line(program)).split('\n'), expected, program)


if __name__ == '__main__':unittest.main()
