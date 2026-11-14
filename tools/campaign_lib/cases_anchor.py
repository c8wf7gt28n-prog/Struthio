"""The anchor set (A01..A35): one case per original situation S01..S35, with its id and the owner's intent.

Five anchors have steps written and run in simulation mode with declared checks. Each covers a baseline slice of
its situation (Case.slice says which), not the situation's whole intent:
  A01 (S01)  After Hours 07: trace the settled power to its reviewed PDF row and check 12 V x 280 mA = 3.36 W exactly.
  A16 (S16)  After Hours 07, the spec's first complete run, headless through the kernel's operations: settled
             current 280 mA -> 300 mA on the working copy, recalculate, and check from the records that the cell says
             300, settled power is 3.6 W at 12 V (was 3.36 W), the dependent finding is flagged for recheck, the
             source still says 280 mA; a fresh process reopens the saved result and reads all of that back. Which
             step waits for the owner's approval is READ from the hand's policy table for the steps Graphite offers;
             no approval is exercised (the approval is the owner's Run in the window; the fixture grants it).
  A17 (S17)  The After Hours 07 backup: verify, restore into fresh folders, refuse an existing destination, catch a
             changed member.
  A27 (S27)  After Hours 07 crash recovery: killed after the cell write, resumed from its own checkpoint; the
             completed change is recognised from the records and not repeated.
  A28 (S28)  A busy desk on simulated host readings: the foreground turn and the reserve, real admission code.
In the real flow the 35B model chooses the operations from the owner's words. No model runs here, so the
known-good choice is scripted and every result says so ("driver": "scripted").

Every anchor lists its needs (needs.py); the runner checks them when the run starts. An anchor whose needs are not
met is Blocked with what is missing and what is present; one whose needs are all met but whose steps are not
written yet is Blocked with "steps not written yet; its needs are here".
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

from . import fixture, sim
from .core import Case, code_of
from .needs import MODEL

DATA = Path(__file__).resolve().parent / 'data'
SITUATIONS = {s['id']: s for s in json.loads((DATA / 'situations_35.json').read_text())}
IDS = fixture.AH07_IDS
REQUEST = ('On this working copy, change settled current from 280 mA to 300 mA, recalculate settled power, show me '
           'which finding needs rechecking, and open the source for the original reading.')
AH07_OPS = ['field.read', 'field.ripple', 'field.set', 'office.get', 'documents.get', 'office.datasheet.recheck',
            'field.trace']
SCRIPTED = 'scripted: the real flow has the 35B model choose these operations; no model runs in a sim attempt'


# ---------------------------------------------------------------- shared After Hours 07 reads

def _field(ctx):
    return {o['id']: o for o in ctx.call('field.read')['objects']}


def _value(document):
    """The calculation's output as an exact Fraction and its unit, read from the saved record."""
    output = document['derivation']['calculation']['outputs'][0]['value']
    return Fraction(output['rational']), output.get('unit')


def _guard_launch():
    from unittest.mock import patch
    from workbench.engineering_kernel import Kernel
    guard = patch.object(Kernel, 'launch', side_effect=AssertionError('an anchor case must not start a job worker'))
    guard.start()
    return guard


def _vault_copy(sha256):
    """The source PDF's stored original in the restored profile, found by its content hash."""
    import hashlib
    from workbench.session import config_dir
    for path in sorted((config_dir() / 'libraries').rglob('*')):
        if path.is_file() and path.stat().st_size < 64 * 1024 * 1024:
            if hashlib.sha256(path.read_bytes()).hexdigest() == sha256:
                return path
    return None


def _reopen(ctx, new_calc):
    """Save-and-reopen: a fresh interpreter opens the workspace and reads the saved records."""
    import os
    command = [sys.executable, '-B', str(fixture.REPO / 'tools' / 'campaign.py'), '--reopen', str(ctx.folder),
               '--ids', json.dumps({'sheet': IDS['sheet'], 'calc': new_calc, 'claim': 'claim:' + IDS['claim_settled']})]
    done = subprocess.run(command, capture_output=True, text=True, timeout=60, env=dict(os.environ))
    ctx.progress('reopen', code=done.returncode)
    lines = [l for l in done.stdout.splitlines() if l.startswith('{')]
    return json.loads(lines[-1]) if lines else {'error': done.stderr[-400:]}


def reopen_main(folder, ids):
    """Entry for `campaign.py --reopen`: read the saved records in a new process and print them as JSON."""
    from workbench.engineering_kernel import Kernel, operator
    kernel = Kernel(Path(folder) / 'ws')
    principal = operator()

    def call(op, args=None):
        r = kernel.dispatch(op, args or {}, principal)
        if not r['ok']:
            raise RuntimeError(code_of(r))
        return r['result']
    sheet = call('office.get', {'id': ids['sheet']})
    cell = sheet['document']['sheets'][0]['cells']['B3']
    row3 = next((r for r in sheet['origin']['reviewed_rows'] if r['sheet_row'] == 3), {})
    calc = call('documents.get', {'id': ids['calc']})['document']
    value, unit = _value(calc)
    field = {o['id']: o for o in call('field.read')['objects']}
    finding = field[ids['claim']]
    print(json.dumps({'B3': cell['value'], 'B3_unit': cell.get('unit'), 'revision': sheet['revision'],
                      'power': str(value), 'power_unit': unit, 'finding_state': finding['state'],
                      'finding_says': finding['facts'][0] if finding['facts'] else None,
                      'source_row_3': [row3.get('value'), row3.get('unit')]}))


REOPENED = {     # what A16 claims was saved, as the fresh process must read it back
    'reopened:cell': ['300', 'mA'], 'reopened:same_revision': True, 'reopened:power_w': {'decimal': '3.60'},
    'reopened:power_unit': 'W', 'reopened:finding_state': 'recheck', 'reopened:finding_says': 'says 3.36 W; now 3.6 W',
    'reopened:source_row_3': ['280', 'mA']}


def reopened_observations(ctx, reopened, revision):
    """One check per thing the case claims was saved, each read from what the fresh process printed."""
    r = reopened if isinstance(reopened, dict) else {}
    ctx.note('reopened', reopened)
    ctx.observe('reopened:cell', [r.get('B3'), r.get('B3_unit')])
    ctx.observe('reopened:same_revision', r.get('revision') is not None and r.get('revision') == revision)
    ctx.observe('reopened:power_w', r.get('power'))
    ctx.observe('reopened:power_unit', r.get('power_unit'))
    ctx.observe('reopened:finding_state', r.get('finding_state'))
    ctx.observe('reopened:finding_says', r.get('finding_says'))
    ctx.observe('reopened:source_row_3', r.get('source_row_3'))


def policy_waits(kernel, owner, sheet_id, place='show'):
    """Which steps Graphite offers for the sheet would wait for the owner's approval, read from the hand's policy table.

    The steps are Graphite's own (field_do.steps_for, what D offers in the Field); whether one waits is the test the
    Field makes (field_page._waits): not stacy_hand.hers(place, step.scope, operation, arguments). This READS the
    policy table; it does not exercise an approval. The approval itself is the owner's Run in the window, which the
    Kernel does not hold (field.set saves through office.save, an approve-scope operation, so the owner's principal
    runs both) and a headless run cannot press; the fixture grants it, and the result says so."""
    from workbench import field_do, field_source, stacy_hand
    desk, _ = field_source.read_field(kernel, owner)
    sheet = next(o for o in desk.objects if o.id == sheet_id)
    waiting, ready = [], []
    for step in field_do.steps_for(kernel, owner, sheet, desk):
        if step.kind != 'write':
            continue
        operation, arguments = field_do.call(step.line)
        held = bool(step.more) or not stacy_hand.hers(place, step.scope, operation, arguments)
        (waiting if held else ready).append({'words': step.words, 'operation': operation, 'arguments': arguments,
                                             'scope': step.scope})
    return waiting, ready


# ---------------------------------------------------------------- A16: the first complete run, headless

def ah07_flow(ctx):
    from workbench import field_ripple, field_source, stacy_hand
    guard = _guard_launch()
    try:
        ctx.note('driver', SCRIPTED)
        asked = re.search(r'change (.+?) from (\d+) mA to (\d+) mA', ctx.case.inputs['request'])
        name, was_ma, now_ma = asked[1].strip().lower(), asked[2], asked[3]
        sheet_id = 'office:' + IDS['sheet']
        field = _field(ctx)
        ctx.observe('open_item', field[sheet_id]['title'])
        desk, _ = field_source.read_field(ctx.kernel, ctx.owner)
        record_id, names = field_ripple.cells_named(ctx.kernel, ctx.owner, next(o for o in desk.objects if o.id == sheet_id))
        cell = names.get(name)
        ctx.observe('target_cell', cell)
        before = ctx.call('office.get', {'id': IDS['sheet']})
        old_calc = ctx.call('documents.get', {'id': IDS['calc_settled']})['document']
        was, unit = _value(old_calc)
        ctx.observe('was_power_w', str(was))
        preview = ctx.call('field.ripple', {'id': sheet_id, 'set': {cell: now_ma}})
        first = preview['rows'][0]
        ctx.observe('preview_shows', [first.get('says_now'), first.get('would_be')])
        # Read from the hand's policy table (stacy_hand.hers), as the Field decides what waits: the change itself is
        # the hand's at "Do and show"; the recalculation Graphite then offers waits for the owner's approval.
        ctx.observe('policy_table:set_waits_for_approval',
                    not stacy_hand.hers('show', 'execute', 'field.set', {'id': sheet_id, 'cell': cell, 'value': now_ma}))
        changed = ctx.call('field.set', {'id': sheet_id, 'cell': cell, 'value': now_ma,
                                          'expected_revision': before['revision']})
        ctx.checkpoint('set', revision=changed['revision'])
        waiting, ready = policy_waits(ctx.kernel, ctx.owner, sheet_id)
        ctx.observe('policy_table:offered_steps_waiting_for_approval', sorted({w['operation'] for w in waiting}))
        ctx.observe('policy_table:offered_steps_done_without_asking', sorted({r['operation'] for r in ready}))
        ctx.note('approval', 'not exercised: the approval is the owner\'s Run in the window; the fixture grants it '
                             '(%s) and the step Graphite offered is run as approved' % ctx.case.inputs['approvals'])
        offered = next((w for w in waiting if w['operation'] == 'office.datasheet.recheck'
                        and w['arguments'].get('id') == IDS['calc_settled']), None)
        ctx.observe('recheck_step_offered', offered is not None)
        doc_revision = ctx.call('documents.get', {'id': IDS['calc_settled']})['document']['revision']
        arguments = offered['arguments'] if offered else {'id': IDS['calc_settled'], 'expected_revision': doc_revision}
        rechecked = ctx.call('office.datasheet.recheck', arguments)
        new_id = rechecked['document']['id']
        ctx.checkpoint('recheck', revision=changed['revision'], calculation=new_id)
        # -------- checks read from the saved records
        after = ctx.call('office.get', {'id': IDS['sheet']})
        b3 = after['document']['sheets'][0]['cells']['B3']
        ctx.observe('cell_now', [b3['value'], b3.get('unit')])
        new = ctx.call('documents.get', {'id': new_id})['document']
        power, unit = _value(new)
        ctx.observe('power_now_w', str(power))
        ctx.observe('power_unit', unit)
        inputs = {i['cell']: (i['value'], i.get('basis')) for i in new['derivation']['inputs']}
        ctx.observe('voltage_input', list(inputs.get('B2', ())))
        ctx.observe('current_input', list(inputs.get('B3', ())))
        ctx.observe('exact_check', str(Fraction(12) * Fraction(int(now_ma), 1000)) == str(power))
        field = _field(ctx)
        finding = field['claim:' + IDS['claim_settled']]
        ctx.observe('finding_state', finding['state'])
        ctx.observe('finding_says', finding['facts'][0] if finding['facts'] else None)
        ctx.observe('startup_calc_state', field['document:' + IDS['calc_startup']]['state'])
        row3 = next(r for r in after['origin']['reviewed_rows'] if r['sheet_row'] == 3)
        ctx.observe('source_row_3', [row3['value'], row3.get('unit')])
        ctx.observe('source_state', after['source_state']['state'])
        vault = _vault_copy(IDS['pdf_sha256'])
        ctx.observe('source_pdf_unchanged', vault is not None)
        trace = ctx.call('field.trace', {'id': 'document:' + new_id})
        ctx.observe('source_link', 'intake:' + IDS['pdf_item'] in json.dumps(trace))
        reopened_observations(ctx, _reopen(ctx, new_id), after['revision'])
        ctx.note('was_ma', was_ma)
    finally:
        guard.stop()


# ---------------------------------------------------------------- A01: trace and the exact power check

def ah07_trace(ctx):
    guard = _guard_launch()
    try:
        ctx.note('driver', SCRIPTED)
        calc = ctx.call('documents.get', {'id': IDS['calc_settled']})['document']
        power, unit = _value(calc)
        inputs = {i['cell']: i for i in calc['derivation']['inputs']}
        volts, amps = Fraction(inputs['B2']['value']), Fraction(inputs['B3']['value']) / 1000
        ctx.observe('power_w', str(power))
        ctx.observe('unit', unit)
        ctx.observe('exact_recomputed', str(volts * amps))
        ctx.observe('inputs_basis', sorted({i.get('basis') for i in inputs.values()}))
        trace = json.dumps(ctx.call('field.trace', {'id': 'document:' + IDS['calc_settled']}))
        ctx.observe('traces_to_sheet', 'office:' + IDS['sheet'] in trace)
        ctx.observe('traces_to_pdf', 'intake:' + IDS['pdf_item'] in trace)
        sheet = ctx.call('office.get', {'id': IDS['sheet']})
        ctx.observe('pdf_source_sha', sheet['source_state'].get('source_sha256'))
    finally:
        guard.stop()


# ---------------------------------------------------------------- A17: backup verify and restore

def backup_restore(ctx):
    from workbench import workspace_backup
    backup = Path(ctx.backup) if ctx.backup else None
    if backup is None:
        raise fixture.Blocked('The After Hours 07 backup was not found under --fixtures.')
    ctx.observe('verify', workspace_backup.verify(backup)['state'])
    first = workspace_backup.restore(backup, ctx.folder / 'ws', ctx.folder / 'profile')
    ctx.observe('restore', first['state'])
    try:
        workspace_backup.restore(backup, ctx.folder / 'ws', ctx.folder / 'profile-2')
        ctx.observe('existing_destination', 'REPLACED')
    except ValueError as error:
        ctx.observe('existing_destination', 'REFUSED')
        ctx.note('existing_destination_reason', str(error)[:200])
    copy = ctx.folder / 'tmp' / 'tampered_backup'
    shutil.copytree(backup, copy)
    member = copy / 'workspace' / 'LEDGER_WORKSPACE.json'
    raw = bytearray(member.read_bytes())
    raw[-2] ^= 0x01
    member.write_bytes(bytes(raw))
    ctx.fault('one byte changed in a copy of the backup')
    try:
        workspace_backup.verify(copy)
        ctx.observe('tampered', 'VERIFIED')
    except ValueError as error:
        ctx.observe('tampered', str(error).split(':')[0])


# ---------------------------------------------------------------- A27: crash after the write, resume

def ah07_resume(ctx):
    guard = _guard_launch()
    try:
        ctx.note('driver', SCRIPTED)
        sheet_id = 'office:' + IDS['sheet']
        if ctx.phase == 'first':
            before = ctx.call('office.get', {'id': IDS['sheet']})
            changed = ctx.call('field.set', {'id': sheet_id, 'cell': 'B3', 'value': '300',
                                              'expected_revision': before['revision']})
            ctx.checkpoint('set', revision=changed['revision'], before=before['revision'])
            ctx.progress('recheck', state='about to recalculate; simulated crash')
            time.sleep(600)
            return
        saved = ctx.read_checkpoint()
        ctx.observe('resumed_from', saved and saved['step'])
        current = ctx.call('office.get', {'id': IDS['sheet']})
        done = current['revision'] == saved['revision'] and current['document']['sheets'][0]['cells']['B3']['value'] == '300'
        ctx.observe('completed_change_recognised', done)
        if not done:
            ctx.call('field.set', {'id': sheet_id, 'cell': 'B3', 'value': '300', 'expected_revision': current['revision']})
        replay = ctx.try_call('field.set', {'id': sheet_id, 'cell': 'B3', 'value': '300', 'expected_revision': saved['before']})
        ctx.observe('replay_with_old_revision', 'REFUSED' if not replay['ok'] else 'APPLIED')
        doc_revision = ctx.call('documents.get', {'id': IDS['calc_settled']})['document']['revision']
        rechecked = ctx.call('office.datasheet.recheck', {'id': IDS['calc_settled'], 'expected_revision': doc_revision})
        power, _ = _value(rechecked['document'])
        ctx.observe('power_now_w', str(power))
        field = _field(ctx)
        ctx.observe('sheet_versions', [f for f in field[sheet_id]['facts'] if f.startswith('version')])
        ctx.observe('settled_calculations', sorted(o['title'] for o in field.values()
                                                    if o['kind'] == 'calculation' and 'Settled' in o['title']))
        ctx.observe('finding_state', field['claim:' + IDS['claim_settled']]['state'])
    finally:
        guard.stop()


# ---------------------------------------------------------------- A28: the foreground turn on a busy desk

def busy_desk(ctx):
    from workbench import resource_control
    from .cases_resource import claim, demand, put_job
    with sim.Bench(host=sim.FakeHost(40)) as bench:
        resource_control.touch(ctx.kernel, ctx.owner.identity)
        ctx.fault('owner is clicking in a sheet (foreground lease)')
        background = put_job(ctx, 'Queued', demand(2, priority='background'))
        got, job = claim(ctx, bench, background)
        ctx.observe('background_while_desk_active', job.get('current_operation'))
        foreground = put_job(ctx, 'Queued', demand(2, lane='io', priority='foreground'), tool='intake.read')
        got_fg, job_fg = claim(ctx, bench, foreground)
        ctx.observe('foreground_admitted', got_fg is not None)
        ctx.observe('reserve_gib', round(job_fg['resource_admission']['reserve_bytes'] / sim.GiB, 3))
        bench.clock.now += 9
        got, job = claim(ctx, bench, background)
        ctx.observe('background_after_desk_idle', got is not None)


# ---------------------------------------------------------------- the 35 declarations

NEEDS = {      # what each situation needs from the machine; needs.py checks every one when the run starts
    'S02': ['owner:Chinese and English datasheet PDF pair', 'ocr:chi_sim'] + MODEL,
    'S03': ['app:Blender', 'owner:sketch to model from'],
    'S04': ['owner:saved email thread and the published policy text'] + MODEL,
    'S05': ['owner:authorized mailbox export (EML with attachments)'] + MODEL,
    'S06': ['owner:bounded, owner-started network capture', 'thinkpad'] + MODEL,
    'S07': ['owner:forecast workbook with the subtotal and refund rows', 'app:LibreOffice Calc'] + MODEL,
    'S08': ['owner:invoices, statements and payment records'] + MODEL,
    'S09': ['owner:photo collection', 'projector'] + MODEL,
    'S10': ['owner:interview footage', 'app:Kdenlive'],
    'S11': ['owner:unfamiliar application\'s source and an import file that reproduces its crash'],
    'S12': ['owner:travel, drawing-delivery and supplier dates, and a calendar account that sends invitations',
            'network'],
    'S13': ['owner:tax-year receipts and statements'] + MODEL,
    'S14': ['owner:authorized application site and its terms', 'network'],
    'S15': ['owner:two supplier workbooks with a reviewed Method Press mapping'] + MODEL,
    'S18': ['owner:recordings, logs, schematics and measurements of the failed prototype'],
    'S19': ['app:FreeCAD', 'owner:source project to migrate'],
    'S20': ['desktop', 'app:LibreOffice Calc'],
    'S21': ['owner:paper with its original code and dataset', 'network'],
    'S22': MODEL + ['thinkpad'],
    'S23': ['owner:two energy bills with their meter readings'] + MODEL,
    'S24': ['owner:machine list, orders, operations and material availability'],
    'S25': ['owner:private knowledge set with the calculation and the hidden sheet'],
    'S26': ['owner:supplier packet with an embedded hostile instruction'] + MODEL,
    'S29': ['owner:manual sources and target-language terminology'] + MODEL,
    'S30': ['owner:supplier catalog pages and part photographs'] + MODEL,
    'S31': ['app:KiCad', 'app:FreeCAD', 'app:LibreOffice Calc', 'app:Scribus', 'owner:board project'],
    'S32': ['app:Audacity', 'app:GIMP', 'app:Kdenlive', 'app:LibreOffice Writer', 'owner:interview recordings'],
    'S33': ['app:Firefox', 'app:Zotero', 'network'],
    'S34': ['app:FreeCAD', 'app:Blender', 'app:Inkscape', 'app:Kdenlive', 'owner:mechanism model'],
    'S35': ['app:Thunderbird', 'app:GIMP', 'app:LibreOffice', 'owner:messages, receipts and shipment photos'],
}

RUNNABLE = {
    'S01': dict(fn=ah07_trace, seed='after_hours_07', budget_s=60, needs=['after_hours_07'],
                title='After Hours 07: trace settled power to its source and check it exactly',
                slice='the trace of settled power to its reviewed PDF row and the exact 84/25 W check, not the '
                      'readiness report with unresolved conditions and a physical test',
                allowed=['documents.get', 'field.trace', 'office.get'],
                expect={'power_w': '84/25', 'unit': 'W', 'exact_recomputed': '84/25', 'inputs_basis': ['REVIEWED_PDF_ROW'],
                        'traces_to_sheet': True, 'traces_to_pdf': True, 'pdf_source_sha': IDS['pdf_sha256']}),
    'S16': dict(fn=ah07_flow, seed='after_hours_07', budget_s=120, needs=['after_hours_07'],
                title='After Hours 07: 280 mA -> 300 mA, recalculate, flag the finding, keep the source',
                slice='one changed reading carried to its power calculation, the finding flag and the reopened '
                      'result, not the updated design, drawings, cost, firmware and revision package',
                allowed=AH07_OPS + ['intake.read'],
                inputs={'request': REQUEST, 'approvals': ['office.datasheet.recheck'], 'driver': 'scripted'},
                expect={'open_item': '07 Bench readings', 'target_cell': 'B3', 'was_power_w': '84/25',
                        'preview_shows': ['280 mA', '300 mA'],
                        'policy_table:set_waits_for_approval': False,
                        'policy_table:offered_steps_waiting_for_approval': ['office.datasheet.recheck'],
                        'policy_table:offered_steps_done_without_asking': ['agenda.add'],     # the "watch it" step
                        'recheck_step_offered': True,
                        'cell_now': ['300', 'mA'], 'power_now_w': {'decimal': '3.60'}, 'power_unit': 'W',
                        'voltage_input': ['12', 'REVIEWED_PDF_ROW'], 'current_input': ['300', 'WORKING_SHEET_EDIT'],
                        'exact_check': True, 'finding_state': 'recheck', 'finding_says': 'says 3.36 W; now 3.6 W',
                        'startup_calc_state': 'recheck', 'source_row_3': ['280', 'mA'],
                        'source_state': 'CURRENT_PDF_SOURCE', 'source_pdf_unchanged': True, 'source_link': True,
                        **REOPENED},
                spec_question='Any saved sheet change also sends the Startup power calculation (B2, B4) to recheck '
                              'although neither of its inputs moved; is that the intended reach of a recheck?'),
    'S17': dict(fn=backup_restore, seed='none', budget_s=60, needs=['after_hours_07'],
                title='After Hours 07 backup: verify, restore fresh, refuse replacement, catch tampering',
                slice='verifying and restoring one Graphite backup into fresh folders, not recovering the most '
                      'complete project from conflicting archives with a manifest of what is missing',
                allowed=['workspace_backup.verify', 'workspace_backup.restore'],
                expect={'verify': 'VERIFIED', 'restore': 'RESTORED', 'existing_destination': 'REFUSED',
                        'tampered': 'Changed backup member'}),
    'S27': dict(fn=ah07_resume, seed='after_hours_07', budget_s=90, needs=['after_hours_07'],
                title='After Hours 07: killed after the cell write, resumed from its checkpoint',
                slice='resuming local work and recognising a completed working-copy change, not reconciling an '
                      'uncertain external action or preserving later owner edits',
                allowed=['office.get', 'field.set', 'documents.get', 'office.datasheet.recheck', 'field.read'],
                resume={'kill_after': 'set'},
                faults=[{'at': 'after checkpoint set', 'fault': 'attempt process killed (SIGKILL) before the recalculation'}],
                expect={'resumed_from': 'set', 'completed_change_recognised': True, 'replay_with_old_revision': 'REFUSED',
                        'power_now_w': '18/5', 'sheet_versions': ['version 2'],
                        'settled_calculations': ['07 Settled power · 3.6 W'], 'finding_state': 'recheck'}),
    'S28': dict(fn=busy_desk, seed='base', budget_s=60, needs=[],
                title='Busy desk: foreground turn first, background waits, reserve kept',
                slice='the foreground turn and the reserve on simulated readings, not sustained work kept usable '
                      'under pressure with resource choices and schedule risk reported',
                allowed=['jobs (admission only)'],
                faults=[{'at': 'start', 'fault': 'foreground lease active for 8 s'}],
                expect={'background_while_desk_active': 'Foreground interaction has the next turn',
                        'foreground_admitted': True, 'reserve_gib': 2.0, 'background_after_desk_idle': True}),
}


def _anchor(sid):
    situation = SITUATIONS[sid]
    number = int(sid[1:])
    spec = RUNNABLE.get(sid)
    base = dict(id='A%02d' % number, set='anchors', situation=sid, intent=situation['finished_result'],
                start={'situation_baseline': situation['baseline_0_4_1']},
                inputs={'difficult_variation': situation['difficult_variation'],
                        'applications': situation.get('applications') or []})
    if spec is None:            # steps not written yet: the runner says Blocked, with its needs checked
        return Case(title=situation['title'], seed='none', needs=list(NEEDS[sid]), mode='sim', budget_s=30,
                    expect={}, **base)
    spec = dict(spec)
    inputs = {**base.pop('inputs'), **spec.pop('inputs', {})}
    title = spec.pop('title')
    return Case(title=situation['title'] + ' -- ' + title, inputs=inputs, mode='sim', **base, **spec)


CASES = [_anchor('S%02d' % n) for n in range(1, 36)]
