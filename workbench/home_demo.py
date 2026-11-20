"""Home Demo: a household and a tenancy matter made entirely of invented data, built through the Kernel's own operations.

Rail Demo (rail_demo.py) is the engineering desk the program keeps; Home Demo is the second, for the legal and the money
parts of Kas's mind (0.8.6). Every name, address, amount and section in it was made up for the purpose, and the law in it
is invented: the act's own name says so ("Demoland", an invented place), and LAW_NOTICE, INVENTED: NOT THE LAW OF ANY
PLACE, is printed on every page of the act and of the other papers of the matter. NOTICE is printed on every page of every
source. Nothing here is the law of anywhere, and nothing is advice.

What it holds ("today" in every example is TODAY, Friday 20 November 2026):

    H1  the Demoland Tenancy Act (invented), page 1: section 3 (counting a period of days, the roll off a weekend or a
        public holiday, the holidays) and section 12 (the deposit), word for word as ACT gives them.
    H2  the move-out record: the lease term ends Wednesday 2026-09-30; the keys came back Saturday 2026-10-03; the deposit
        held is 1200.00.
    H3  the agent's email of Tuesday 2026-09-29, "Thank you, we have your new address for the deposit." Its bytes are a
        fact of the program (sources()), but build() does not bring it in: admit_email() does, the second step of the
        scene that uses it, so until then it is a document not yet on the desk.
    H4  a bank statement, reviewed into the sheet "Home Demo bank Sep–Nov": 41 rows from 2026-09-01 to 2026-11-17, with
        no credit of 1200.00.
    two typed sheets, written as CSV in Files and imported as the owner imports one: "Groceries November" (plan 600.00,
        spent 412.37 by 20 November) and "Household November" (plan 2400.00; rent 1450.00 and other spending 512.40
        paid; phone 55.00 due on 22 November; electricity estimated at 110.00, between 84.10 and 142.55 in the owner's
        words "between my lowest and highest bill of the year").

money() works the household figures out through the Kernel's own maths (math.money, math.dates), exactly: 18763/1000 a
day and 131341/1000 a week for groceries, rounded down to 18.76 and 131.34 so they stay under the plan; 4801/200 (24.00)
and 597/20 (29.85) a day for the household at the two ends of the electricity range; 28.00 a day holds while the bill is
at most 513/5 (102.60), and at 142.55 the month would end at 48799/20 (2439.95).

build() goes through Kernel.dispatch with the owner's principal for every record, through rail_demo's desk (the same
doors: Files, bring in, admit, open the page, review the table, import a typed sheet). Deterministic: the same records
every time (digests()). It needs what Rail Demo needs: pypdf and Poppler. No network, no model.

    from workbench import home_demo
    kernel, owner, demo = home_demo.workspace(folder)    # a workspace and profile of its own under folder, Home Demo in it
    demo = home_demo.build(kernel, operator())          # in a workspace that is already open
    demo = home_demo.find(kernel, operator())           # read back from the records
    home_demo.admit_email(kernel, operator())           # H3 brought in and admitted
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import textwrap
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

from . import rail_demo
from .rail_demo import _Desk

NAME = 'Home Demo'
NOTICE = 'Invented demonstration data: no real person, place, account or law.'
LAW_NOTICE = 'INVENTED: NOT THE LAW OF ANY PLACE'
REVISION = 1                 # bump when what build() makes changes
TODAY = date(2026, 11, 20)   # "today" in every Home Demo example: Friday 20 November 2026
COLLECTION = 'Home Demo sources'                 # the collection the sources are admitted to, and their folder in Files
LATER = 'Home Demo later'                        # the Files folder the email is brought in from, by admit_email()
TYPED = 'Home Demo typed'                        # the Files folder of the typed sheets
BANK_TITLE = 'Home Demo bank Sep–Nov'
BANK_HEADERS = ('Date', 'Description', 'Amount', 'Balance')
OPENING = '3100.00'          # the balance before the statement's first row
DEPOSIT = '1200.00'
LEGAL = ('act', 'move_out', 'email')             # the papers of the legal matter: LAW_NOTICE on every page of each

# The act, word for word. Its section numbers and its words are invented.
ACT_TITLE = 'Demoland Tenancy Act (invented)'
ACT = (('§ 3.', 'Counting periods of days.'),
       ('(a)', 'A period of days after an event does not count the day of the event.'),
       ('(b)', 'If the last day falls on a Saturday, a Sunday or a public holiday, the period ends on the next day that is none of these.'),
       ('(c)', 'The public holidays are 1 January, 25 December and 26 December.'),
       ('§ 12.', 'Deposits.'),
       ('(a)', 'Within 21 days after a tenancy ends, the landlord shall either return the deposit in full or give the tenant an itemised '
               'statement of deductions.'),
       ('(b)', 'Subsection (a) does not apply if the tenant has not given the landlord a forwarding address in writing.'),
       ('(c)', 'A landlord who does not comply with subsection (a) is liable to the tenant for the deposit and an equal amount.'))
MOVE_OUT = (('Lease term ends', 'Wednesday 2026-09-30'),
            ('Keys returned to the agent', 'Saturday 2026-10-03'),
            ('Deposit held by the landlord', DEPOSIT),
            ('The flat', '7 Example Lane, Demotown, Demoland (invented)'))
EMAIL = (('From', 'Demo Lettings <lettings@demo-lettings.example>'),
         ('To', 'The tenant <tenant@home-demo.example>'),
         ('Date', 'Tuesday 2026-09-29'),
         ('Subject', 'Your deposit'),
         ('', 'Thank you, we have your new address for the deposit.'))
EMAIL_SAYS = 'Thank you, we have your new address for the deposit.'
# date, description, amount: 41 rows, 2026-09-01 to 2026-11-17. Invented, every one; no credit of 1200.00 among them.
BANK = (('2026-09-01', 'Rent, Demo Lettings', '-1450.00'), ('2026-09-03', 'Groceries, Corner Market', '-84.20'),
        ('2026-09-05', 'Electricity, Demo Power', '-96.40'), ('2026-09-08', 'Groceries, Corner Market', '-102.15'),
        ('2026-09-10', 'Phone, Demo Mobile', '-55.00'), ('2026-09-12', 'Bus pass', '-48.00'),
        ('2026-09-15', 'Groceries, Corner Market', '-91.37'), ('2026-09-19', 'Hardware store', '-18.90'),
        ('2026-09-22', 'Groceries, Corner Market', '-88.64'), ('2026-09-25', 'Salary, Demo Works', '2950.00'),
        ('2026-09-26', 'Removals, Demo Vans', '-240.00'), ('2026-09-29', 'Groceries, Corner Market', '-76.05'),
        ('2026-10-01', 'Rent, Example Homes', '-1450.00'), ('2026-10-02', 'Groceries, Corner Market', '-95.10'),
        ('2026-10-05', 'Electricity, Demo Power', '-112.75'), ('2026-10-07', 'Groceries, Corner Market', '-83.42'),
        ('2026-10-09', 'Phone, Demo Mobile', '-55.00'), ('2026-10-12', 'Bus pass', '-48.00'),
        ('2026-10-14', 'Groceries, Corner Market', '-99.81'), ('2026-10-16', 'Library cafe', '-12.40'),
        ('2026-10-19', 'Groceries, Corner Market', '-87.66'), ('2026-10-21', 'Bookshop', '-24.99'),
        ('2026-10-23', 'Salary, Demo Works', '2950.00'), ('2026-10-24', 'Groceries, Corner Market', '-104.30'),
        ('2026-10-27', 'Refund, Demo Vans', '40.00'), ('2026-10-28', 'Groceries, Corner Market', '-78.25'),
        ('2026-10-30', 'Cinema', '-21.00'), ('2026-11-02', 'Rent, Example Homes', '-1450.00'),
        ('2026-11-03', 'Groceries, Corner Market', '-92.48'), ('2026-11-04', 'Bus pass', '-48.00'),
        ('2026-11-06', 'Groceries, Corner Market', '-101.17'), ('2026-11-07', 'Hardware store', '-15.60'),
        ('2026-11-09', 'Groceries, Corner Market', '-84.93'), ('2026-11-10', 'Library cafe', '-9.80'),
        ('2026-11-11', 'Groceries, Corner Market', '-79.54'), ('2026-11-12', 'Bookshop', '-18.50'),
        ('2026-11-13', 'Salary, Demo Works', '150.00'), ('2026-11-14', 'Cinema', '-19.00'),
        ('2026-11-15', 'Groceries, Corner Market', '-33.20'), ('2026-11-16', 'Interest', '0.42'),
        ('2026-11-17', 'Bus fare', '-2.80'))
# The typed sheets: (file name in Files, title, CSV text). Amounts as the owner types them.
SHEETS = {'groceries': ('Groceries November.csv', 'Groceries November',
                        'Item,Amount,Note\nPlan,600.00,for November\nSpent,412.37,by 2026-11-20\n'),
          'household': ('Household November.csv', 'Household November',
                        'Item,Amount,Low,High,State,Note\n'
                        'Plan,2400.00,,,plan,for November\n'
                        'Rent,1450.00,,,paid,\n'
                        'Other spending,512.40,,,paid,\n'
                        'Phone,55.00,,,due 2026-11-22,\n'
                        'Electricity,110.00,84.10,142.55,estimated,between my lowest and highest bill of the year\n')}
WEEK = 7
DAILY = '28.00'              # the daily spend money() asks of the household: what bill keeps it inside the plan

# The pages, in PDF points.
PAGE_W, PAGE_H = 595, 842
LEFT, TOP, LINE = 56, 790, 15
WRAP = 84                    # characters a line of the act holds
BANK_X = (48, 128, 380, 470)
BANK_TOP, BANK_STEP, BANK_FONT = 700, 15, 9      # the header row's baseline; each row below it


class Unavailable(rail_demo.Unavailable):
    """Home Demo cannot be built, read or changed here; the message says why, in one sentence."""


# ---------------------------------------------------------------- the sources, written byte by byte

def _pdf_text(text):
    """A string of a page, in the font's WinAnsi bytes: plain ASCII and the section sign."""
    out = []
    for c in text:
        if c == '§':out.append('\\247')
        elif 32 <= ord(c) < 127:out.append('\\' + c if c in '\\()' else c)
        else:raise ValueError('A demonstration source is written in plain ASCII and the section sign')
    return ''.join(out)


def pages_pdf(pages):
    """A PDF of `pages`, each a list of (x, y, size, text). No clock, no random id and no library: the same bytes every time,
    so its SHA-256 is a fact of the program."""
    count = len(pages)
    objects = ['<< /Type /Catalog /Pages 2 0 R >>',
               '<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % (4 + 2 * i) for i in range(count)), count),
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    for i, items in enumerate(pages):
        stream = '\n'.join('BT /F1 %d Tf %d %d Td (%s) Tj ET' % (size, x, y, _pdf_text(text)) for x, y, size, text in items)
        objects.append('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>'
                       % (PAGE_W, PAGE_H, 5 + 2 * i))
        objects.append('<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream))
    out = '%PDF-1.4\n';offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out));out += '%d 0 obj\n%s\nendobj\n' % (number, body)
    start = len(out)
    out += 'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1) + ''.join('%010d 00000 n \n' % at for at in offsets)
    out += 'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, start)
    return out.encode('ascii')


def _head(heading, legal):
    """A page's top: its heading, the notice, and on the papers of the legal matter the law notice."""
    items = [(LEFT, TOP, 14, heading), (LEFT, TOP - 18, 9, NOTICE)]
    if legal:items.append((LEFT, TOP - 32, 10, LAW_NOTICE))
    return items


def _foot(legal):
    return [(LEFT, 40, 9, LAW_NOTICE)] if legal else [(LEFT, 40, 9, NOTICE)]


def _act_page():
    items = _head('Demoland Tenancy Act (invented), page 1', True);y = TOP - 64
    for mark, words in ACT:
        if mark.startswith('§'):
            y -= 8;items.append((LEFT, y, 11, '%s %s' % (mark, words)));y -= LINE + 2;continue
        for n, line in enumerate(textwrap.wrap(words, WRAP)):
            items.append((LEFT + 12, y, 10, '%s %s' % (mark, line) if n == 0 else '     ' + line));y -= LINE
    return items + _foot(True)


def _rows_page(heading, rows, legal):
    items = _head(heading, legal);y = TOP - 70
    for label, value in rows:
        items.append((LEFT, y, 11, '%s: %s' % (label, value) if label else value));y -= LINE + 7
    return items + _foot(legal)


def bank_rows():
    """The statement's rows as printed: (date, description, amount, balance), the balance worked out exactly from OPENING."""
    balance = Fraction(OPENING);out = []
    for day, description, amount in BANK:
        balance += Fraction(amount);out.append((day, description, amount, _cents(balance)))
    return tuple(out)


def _cents(value):
    whole = abs(value) * 100
    if whole.denominator != 1:raise ValueError('A demonstration amount is whole cents')
    cents = int(whole);return '%s%d.%02d' % ('-' if value < 0 else '', cents // 100, cents % 100)


def _bank_page():
    items = _head('Home Demo: bank statement, 2026-09-01 to 2026-11-17', False)
    items.append((LEFT, TOP - 34, 10, 'Home Demo current account (invented). Opening balance %s.' % OPENING))
    for n, row in enumerate((BANK_HEADERS, *bank_rows())):
        for x, cell in zip(BANK_X, row):items.append((x, BANK_TOP - n * BANK_STEP, BANK_FONT, cell))
    return items + _foot(False)


def bank_region():
    """Where the statement's rows are on the page (not its headings): [x, y, width, height] as parts of the page, from its
    top left corner, as rail_demo.table_region gives them."""
    top = (PAGE_H - (BANK_TOP - BANK_STEP) - BANK_STEP * 0.75) / PAGE_H
    return [round(v, 4) for v in (0.04, top, 0.92, len(BANK) * BANK_STEP / PAGE_H)]


# key: (file name in Files, title, its pages)
def _sources():
    return {'act': ('Demoland_Tenancy_Act.pdf', ACT_TITLE, [_act_page()]),
            'move_out': ('Home_Demo_Move_Out_Record.pdf', 'Home Demo move-out record', [_rows_page('Home Demo: move-out record', MOVE_OUT, True)]),
            'bank': ('Home_Demo_Bank_Statement.pdf', 'Home Demo bank statement', [_bank_page()]),
            'email': ('Home_Demo_Agent_Email.pdf', "Home Demo: the agent's email", [_rows_page("Home Demo: the agent's email, printed", EMAIL, True)])}


def sources():
    """{key: {'name', 'title', 'bytes', 'sha256', 'pages': the text of each page, in order}} for the four sources (the email
    is brought in only by admit_email)."""
    out = {}
    for key, (name, title, pages) in _sources().items():
        raw = pages_pdf(pages)
        out[key] = {'name': name, 'title': title, 'bytes': raw, 'sha256': hashlib.sha256(raw).hexdigest(),
                    'pages': ['\n'.join(text for _, _, _, text in items) for items in pages]}
    return out


def available():
    """'' when Home Demo can be built here, or the one sentence that says what is missing (what Rail Demo needs)."""
    return rail_demo.available().replace(rail_demo.NAME, NAME)


# ---------------------------------------------------------------- building it, one Kernel operation at a time

def _bring_in(desk, kernel, space, folder, items):
    """Write `items` ({key: source}) in Files under `folder`, bring the folder into the collection and admit each as written."""
    for item in items.values():
        written = desk.call('files.write', {'path': '%s/%s' % (folder, item['name']), 'text': item['bytes'].decode('ascii')})
        if written.get('sha256') not in (None, item['sha256']):
            raise Unavailable('%s: Files changed the bytes of %s.' % (desk.doing, item['name']))
    listing = desk.call('files.list', {'path': folder})
    from . import files_service
    path = Path(listing.get('root') or files_service.root(kernel)) / folder
    desk.job('intake.import', {'namespace': space, 'path': str(path), 'mode': 'snapshot'})
    listed = {row['name']: row for row in desk.call('intake.items', {'namespace': space, 'limit': 200})['items']}
    for item in items.values():
        row = listed.get(item['name'])
        if row is None or row['sha256'] != item['sha256']:
            raise Unavailable('%s: %s was not brought in as written.' % (desk.doing, item['name']))
        seen = desk.call('intake.item', {'id': row['id']})
        desk.call('intake.decide', {'id': row['id'], 'decision': 'ACCEPTED', 'expected_sha256': row['sha256'],
                                    'expected_policy_hash': seen['policy_hash'], 'expected_decision': '',
                                    'reason': 'Home Demo: an invented demonstration source, admitted as written'})
        item['item'] = row['id']
    desk.job('references.index', {'namespace': space})


def build(kernel, principal):
    """Build Home Demo in this workspace (Rail Demo may be there too). Returns what find() reads back."""
    why = available()
    if why:
        raise Unavailable(why)
    desk = _Desk(kernel, principal, 'Home Demo could not be built')
    if any(space.get('name') == COLLECTION for space in desk.call('intake.namespaces').get('namespaces', ())):
        raise Unavailable('Home Demo is already in this workspace.')
    made = sources();made.pop('email')
    # 1. the act, the move-out record and the bank statement: put in Files, brought in, admitted
    space = desk.call('intake.namespace.create', {'name': COLLECTION})['id']
    _bring_in(desk, kernel, space, COLLECTION, made)
    # 2. the statement's table, reviewed into a sheet: each row's date, description, amount and balance as printed, kept as
    #    the description (parameter), the amount (value, no currency) and the date (conditions)
    bank = made['bank']
    page = desk.job('references.pdf.page', {'namespace': space, 'item': bank['item'], 'source_sha256': bank['sha256'], 'page_index': 0})
    preview = desk.call('office.datasheet.preview', {'job': page['id'], 'rect': bank_region(), 'layer': 'native'})
    read = [tuple(r['cells']) for r in preview.get('rows', ())]
    if preview.get('state') != 'REVIEW' or read != list(bank_rows()):
        raise Unavailable('Home Demo could not be built: the bank statement was not read as written (%d rows read).' % len(read))
    desk.call('office.datasheet.create', {
        'job': page['id'], 'rect': bank_region(), 'layer': 'native', 'expected_digest': preview['digest'], 'title': BANK_TITLE,
        'rows': [{'source_row': r['source_row'], 'parameter': r['cells'][1], 'value': r['cells'][2], 'unit': '', 'conditions': r['cells'][0]}
                 for r in preview['rows']]})
    # 3. the typed sheets: written as CSV in Files and imported, as the owner imports one
    for name, title, text in SHEETS.values():
        desk.call('files.write', {'path': '%s/%s' % (TYPED, name), 'text': text})
        root = desk.call('files.list', {'path': TYPED})
        from . import files_service
        plan = desk.call('office.import.preview', {'path': str(Path(root.get('root') or files_service.root(kernel)) / TYPED / name)})
        desk.call('office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']})
    return find(kernel, principal)


def workspace(base):
    """Home Demo in a workspace of its own under `base`, with a profile and a Concern folder of its own beside it (as
    rail_demo.workspace). Returns (kernel, principal, what build() made). The caller deletes `base` and puts the
    environment back (unittest.mock.patch.dict(os.environ))."""
    from .baseline import environment
    from .engineering_kernel import Kernel, operator
    from .locations import office
    base = Path(base);root = base / 'workspace'
    os.environ.update(environment(os.environ, root, base / 'profile'), ARC_LEDGER_CONCERN=str(base / 'Concern'))
    kernel = Kernel(office(root));principal = operator()
    return kernel, principal, build(kernel, principal)


def admit_email(kernel, principal):
    """H3, the agent's email, brought in from its own folder in Files and admitted: the second step of the scene that uses
    it. Returns what find() reads back."""
    desk = _Desk(kernel, principal, "Home Demo's email could not be admitted");demo = find(kernel, principal)
    if 'email' in demo['sources']:
        raise Unavailable('The agent\'s email is already on the desk.')
    _bring_in(desk, kernel, demo['collection'], LATER, {'email': sources()['email']})
    return find(kernel, principal)


# ---------------------------------------------------------------- reading it back

def find(kernel, principal):
    """Home Demo as the records of this workspace hold it now: {'name', 'notice', 'revision', 'collection', 'sources': {key:
    {'item', 'name', 'sha256'}} (the email only once admitted), 'sheets': {'bank', 'groceries', 'household': id}}."""
    desk = _Desk(kernel, principal, 'Home Demo could not be read')
    space = next((s for s in desk.call('intake.namespaces').get('namespaces', ()) if s.get('name') == COLLECTION), None)
    if space is None:
        raise Unavailable('Home Demo is not in this workspace.')
    items = {row['name']: row for row in desk.call('intake.items', {'namespace': space['id'], 'limit': 200})['items']}
    here = {row['id'] for row in items.values()}
    titles = {BANK_TITLE: 'bank', **{title: key for key, (_, title, _) in SHEETS.items()}};sheets = {}
    for row in desk.call('office.list').get('documents', ()):
        key = titles.get(row.get('title'))
        if key == 'bank':
            origin = desk.call('office.get', {'id': row['id']}).get('origin') or {}
            if (origin.get('pdf') or {}).get('item') in here:sheets[key] = row['id']
        elif key:sheets.setdefault(key, row['id'])
    found = {key: {'item': items[item['name']]['id'], 'name': item['name'], 'sha256': items[item['name']]['sha256']}
             for key, item in sources().items() if item['name'] in items}
    missing = [key for key in ('act', 'move_out', 'bank') if key not in found] + [key for key in ('bank', 'groceries', 'household') if key not in sheets]
    if missing:
        raise Unavailable('Home Demo is not whole in this workspace: %s is missing.' % missing[0])
    return {'name': NAME, 'notice': NOTICE, 'revision': REVISION, 'collection': space['id'], 'sources': found, 'sheets': sheets}


def page_texts(kernel, principal, key):
    """The words of each page of one admitted source, as Graphite reads them from the admitted file (each page opened
    through its own operation, as a person opens it): [text of page 1, ...]."""
    desk = _Desk(kernel, principal, 'Home Demo could not be read');demo = find(kernel, principal);source = demo['sources'][key]
    where = {'namespace': demo['collection'], 'item': source['item'], 'source_sha256': source['sha256']}
    out = []
    for index in range(desk.call('references.pdf.info', where)['page_count']):
        job = desk.job('references.pdf.page', {**where, 'page_index': index})
        page = desk.call('references.pdf.result', {'job': job['id']})
        out.append(' '.join(word['text'] for word in ((page.get('result') or page).get('native') or {}).get('words') or ()))
    return out


def _cells(desk, ident):
    document = desk.call('office.get', {'id': ident})['document']
    return ((document.get('sheets') or [{}])[0].get('cells') or {})


def sheet_rows(kernel, principal, key):
    """The rows of one of Home Demo's sheets as the records hold them: a list of lists of cell texts, the heading row first."""
    desk = _Desk(kernel, principal, 'Home Demo could not be read');cells = _cells(desk, find(kernel, principal)['sheets'][key])
    rows = {}
    for address, cell in cells.items():
        found = re.fullmatch(r'([A-Z]+)(\d+)', address)
        if found:rows.setdefault(int(found.group(2)), {})[found.group(1)] = _text(cell.get('value'))
    return [[row.get(chr(65 + i), '') for i in range(max(ord(c) - 64 for c in row))] for _, row in sorted(rows.items())]


def _text(value):
    """A cell's value as the text of an exact decimal (a typed 600.00 may be held as the number 600.0)."""
    if value is None:return ''
    if isinstance(value, bool):return str(value)
    if isinstance(value, (int, float)):
        text = repr(value);return text[:-2] if text.endswith('.0') else text
    return str(value)


def bank(kernel, principal):
    """The bank sheet's rows: [(date, description, amount)] in order, as reviewed."""
    rows = sheet_rows(kernel, principal, 'bank')[1:]
    return [(row[3], row[0], row[1]) for row in rows]


# ---------------------------------------------------------------- the money, worked out by the Kernel's maths

def _amounts(kernel, principal, key):
    return {row[0]: row for row in sheet_rows(kernel, principal, key)[1:]}


def _exact(record, *path):
    value = record
    for step in path:value = value[step]
    return value['rational']


def money(kernel, principal, today=TODAY, daily=DAILY):
    """The groceries and household figures, each worked out through math.money and math.dates in the Kernel from the typed
    sheets as the records hold them, as of `today` (Home Demo's own day by default). Exact values as fractions in text,
    and the cents rounded down (the solve's own inward step), so an allowance stays inside the plan. {'today', 'days_left',
    'groceries': {'left_per_day', 'left_per_week' (exact), 'per_day', 'per_week' (in whole cents)}, 'household': {'per_day'
    (the exact range over the electricity range), 'per_day_whatever_the_bill' (in whole cents), 'break_even' (the largest
    bill that keeps `daily` a day inside the plan), 'holds' (the check over the range), 'witness' (the bill at which it
    does not hold), 'month_at_witness'}}."""
    desk = _Desk(kernel, principal, 'Home Demo could not be worked out')
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    left = desk.call('math.dates', {'stage': 'calculate', 'expression': '%s - %s' % (month_end.isoformat(), today.isoformat())})
    days = int(Fraction(left['result']['value']['rational']))
    g = _amounts(kernel, principal, 'groceries')
    given = [{'name': 'plan', 'lo': g['Plan'][1]}, {'name': 'spent', 'lo': g['Spent'][1]}]
    def ask(stage, expression, rows, **more):
        return desk.call('math.money', {'stage': stage, 'expression': expression, 'given': rows, **more})
    per_day = ask('calculate', '(plan - spent) / %d' % days, given)
    per_week = ask('calculate', '%d * (plan - spent) / %d' % (WEEK, days), given)
    day_down = ask('solve', '%d * daily <= plan - spent' % days, given, **{'for': 'daily', 'step': '0.01'})
    week_down = ask('solve', '%d * weekly <= %d * (plan - spent)' % (days, WEEK), given, **{'for': 'weekly', 'step': '0.01'})
    h = _amounts(kernel, principal, 'household');bill = h['Electricity']
    fixed = [{'name': 'plan', 'lo': h['Plan'][1]}, {'name': 'rent', 'lo': h['Rent'][1]}, {'name': 'other', 'lo': h['Other spending'][1]},
             {'name': 'phone', 'lo': h['Phone'][1]}]
    ranged = fixed + [{'name': 'electricity', 'lo': bill[2], 'hi': bill[3]}]
    spread = ask('range', '(plan - rent - other - phone - electricity) / %d' % days, ranged)
    floor = ask('solve', '%d * daily <= plan - rent - other - phone - electricity' % days, ranged, **{'for': 'daily', 'step': '0.01'})
    even = ask('solve', 'rent + other + phone + electricity + %d * %s <= plan' % (days, daily), fixed, **{'for': 'electricity'})
    check = ask('check', 'rent + other + phone + electricity + %d * %s <= plan' % (days, daily), ranged)
    witness = ((check.get('witness') or {}).get('assignment') or {}).get('electricity')
    at = ask('calculate', 'rent + other + phone + electricity + %d * %s' % (days, daily),
             fixed[1:] + [{'name': 'electricity', 'lo': witness['rational'] if witness else bill[3]}])
    return {'today': today.isoformat(), 'days_left': days,
            'groceries': {'left_per_day': _exact(per_day, 'result', 'value'), 'left_per_week': _exact(per_week, 'result', 'value'),
                          'per_day': _exact(day_down, 'result', 'allowed', 'lattice', 'upper'), 'per_week': _exact(week_down, 'result', 'allowed', 'lattice', 'upper')},
            'household': {'per_day': [_exact(spread, 'result', 'range', 0), _exact(spread, 'result', 'range', 1)],
                          'per_day_whatever_the_bill': _exact(floor, 'result', 'allowed', 'lattice', 'upper'),
                          'daily': daily, 'break_even': _exact(even, 'result', 'allowed', 'upper', 'value'), 'holds': check['state'],
                          'witness': witness and witness['rational'], 'month_at_witness': _exact(at, 'result', 'value'), 'plan': h['Plan'][1]}}


# ---------------------------------------------------------------- the same every time, and nothing private

def _digest(value):return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def digests(kernel, principal):
    """A digest of each record Home Demo made, without ids or times: each source's SHA-256 as admitted, each sheet's
    cells, and the desk as the Field reads it (kind, title, state, role, facts and place of each object; the links by
    title). Two builds give the same digests."""
    desk = _Desk(kernel, principal, 'Home Demo could not be read');demo = find(kernel, principal)
    field = desk.call('field.read')
    ours = {o['title'] for o in field['objects'] if _ours(o)}
    return {'sources': {key: row['sha256'] for key, row in sorted(demo['sources'].items())},
            'sheets': {key: _digest(sheet_rows(kernel, principal, key)) for key in sorted(demo['sheets'])},
            'field': _digest(sorted([[o['kind'], o['title'], o['state'], o['role'], list(o['facts']), o['where']] for o in field['objects'] if o['title'] in ours])),
            'links': _digest(sorted([[l['from'], l['to'], l['label']] for l in field['links'] if l['from'] in ours or l['to'] in ours]))}


def _ours(obj):
    names = {item['name'] for item in sources().values()} | {BANK_TITLE} | {title for _, title, _ in SHEETS.values()}
    return obj.get('title') in names or obj.get('where') == COLLECTION


def texts(kernel, principal):
    """Every text Home Demo put on the desk, as the records hold it: the sources' bytes, each sheet's cells and title, and
    what the Field shows of each of its objects."""
    desk = _Desk(kernel, principal, 'Home Demo could not be read');demo = find(kernel, principal)
    out = [page for item in sources().values() for page in item['pages']]
    out += [item['name'] for item in demo['sources'].values()]
    for key in demo['sheets']:out += [cell for row in sheet_rows(kernel, principal, key) for cell in row]
    out += [name for name, _, _ in SHEETS.values()] + [text for _, _, text in SHEETS.values()]
    out += [' '.join([o['title'], o['state'], o['role'], *o['facts'], o['where']]) for o in desk.call('field.read')['objects'] if _ours(o)]
    return out


# What may never be in a demonstration: (category, pattern). An address of the invented domains (.example, .invalid) is
# not one. Written with \x2f so this file never matches the release check's own patterns.
PRIVATE = (('email', re.compile(r'[\w.+-]+@(?![\w-]+\.(?:example|invalid)\b)[\w-]+(?:\.[\w-]+)+')),
           ('phone', re.compile(r'(?<![\w.,-])\+?\d(?:[ ()-]*\d){8,}(?![\w.,-])')),
           ('iban', re.compile(r'\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}\b')),
           ('card', re.compile(r'\b(?:\d[ -]?){13,19}\b')),
           ('owner-workspace', re.compile(r'After\s+Hours', re.I)),
           ('machine-path', re.compile(r'\x2f(?:home|Users|root)\x2f[A-Za-z0-9_.-]+\x2f|\x2ftmp\x2fclaude-')))
ISO_DAY = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')


def private_data(found_in):
    """[(category, the text it was found in, cut to 80 characters)] for each private-looking thing in `found_in` (texts):
    an e-mail address outside the invented domains, a telephone, account or card number, the owner's workspace, a path of
    a person's computer. ISO dates are set aside first, so a date is never a number found."""
    out = []
    for text in found_in:
        plain = ISO_DAY.sub(' ', text)
        for category, pattern in PRIVATE:
            if pattern.search(plain):out.append((category, text[:80]))
    return out
