"""Her recipes in her talk, her column and the line (Graphite 1.1 KS1). The recipes themselves are recipe_book's.

Where they show (the coordinator's note): "the line on the bar (B2's line_finder.py: a row "Recipe: Free space in Home, Enter
shows what it would do"), her column's next steps, and "Recipes" as a list she can show. Her words for them come from
kas_voice.py (KV)."

  her talk      the ask line's words (shell2.SlateFace.ask calls asked() before an objective is planned): her dictionary picks
                a recipe, or the model picks it by number when one is loaded (recipe_book.pick); one question when a slot is not
                in the words (its choices are your press); a recipe that only reads runs at once and says what it found, each
                answer verified; a recipe with a change shows its dry run (exactly which files, which new names, what Undo
                does, or "This cannot be undone.") and waits: Run is your press, and only what you were shown runs (the
                digest). The end is "✓ Done and verified: …" with Undo, or "◆ Not verified. Here is what I checked: …".
                "recipes" (or "show me your recipes") lists them, numbered; a press on one shows it.
  NEXT STEPS    a dry run that waits gives "Run · <the recipe>"; a run with an Undo gives "Undo · <the recipe>".
  the line      line_rows(): "Recipe: Free space in Home", and Enter shows what it would do in her talk (nothing changes).

Every press here is the owner's: it is dispatched with the owner's principal, and the Kernel checks its scope (recipes.run is
execute, recipes.undo approve). Nothing here runs a change on its own.
"""
from __future__ import annotations

from . import kas_voice as kv
from . import recipe_book as rb

SYNC = False                # tests: work on the window's thread instead of a worker
MOST_LINES = 12             # lines of a dry run or an answer shown before "… and n more"
STATE = {}                  # id(host) -> {'offer': {...}, 'done': {...}}: what NEXT STEPS offers


def _state(host):
    return STATE.setdefault(id(host), {})


def _words(host, text):
    try:
        from . import explorer as ex
        from .explorer_qt import bin_word
        return ex.in_words(text, bin_word(host))
    except Exception:  # noqa: BLE001 - the bin's word of this profile; DELETE when it cannot be read
        return text


def _kernel(host):
    from .engine import engineering
    return engineering(host.root)


def _later(host, fn, done, name='graphite-recipe'):
    """fn() off the window's thread, then done(result, error) on it (SYNC: at once)."""
    if SYNC:
        try:result, error = fn(), None
        except Exception as exc:  # noqa: BLE001
            result, error = None, exc
        done(result, error);return
    from .off_window import run_alone
    run_alone(fn, done, name=name)


def _call(host, op, args):
    """The owner's press or read, through the Kernel: a fresh Kernel on the workspace, the owner's principal."""
    from .engineering_kernel import Kernel, operator
    from .off_window import kernel_root
    root = kernel_root(host)
    kernel = Kernel(root) if root is not None else _kernel(host)
    return kernel.dispatch(op, args, operator())


def _why(answer, error=None):
    if error is not None:return str(error)[:240]
    answer = answer if isinstance(answer, dict) else {}
    return str((answer.get('error') or {}).get('message', 'refused')).split(': ', 1)[-1][:240]


def _column_soon(host):
    column = getattr(host, 'her_column', None)
    if column is None:return
    try:
        from . import floor
        floor.column_soon(column)
    except Exception:  # noqa: BLE001
        pass


def _lines_label(face, lines, more=0):
    from PySide6.QtWidgets import QLabel
    from html import escape
    from . import boss_theme as bt
    label = QLabel();label.setObjectName('RecipeLines');label.setWordWrap(True)
    from PySide6.QtCore import Qt
    label.setTextFormat(Qt.RichText)
    body = '<br>'.join(escape(l) for l in lines[:MOST_LINES])
    if more or len(lines) > MOST_LINES:body += '<br>… and %d more' % (more or len(lines) - MOST_LINES)
    label.setText('<span style="font-family:\'%s\';font-size:12px;color:%s;">%s</span>' % (bt.MONO, bt.QUIET, body))
    return label


def _add(bubble, widget):
    try:bubble.box.addWidget(widget)
    except Exception:  # noqa: BLE001 - a bubble without a box still says it
        pass


# ---- the ask chain ----------------------------------------------------------------------------------------------------------
def asked(face, text):
    """shell2's ask chain: True when the words were a recipe's (or a request for the list), and she has answered."""
    words = ' '.join(str(text or '').split())
    if not words:return False
    if rb.asks_for_list(words):
        face.thing = None;face.mine(text);show_list(face);return True
    try:got = rb.pick_words(words)
    except Exception:  # noqa: BLE001 - a broken library never stands in the way of the rest of her chain
        return False
    if got is None:return False
    face.thing = None;face.mine(text)
    request = _model_request(face.host)
    if request is None:
        show(face, got);return True

    def ask_model():
        return rb.pick(words, request)

    def picked(value, error):
        show(face, value if (error is None and value is not None) else got)
    _later(face.host, ask_model, picked, 'graphite-recipe-pick')
    return True


def _model_request(host):
    """A turn request on the live local model, or None (no model: her dictionary alone)."""
    try:
        from . import turns
        from .engineering_kernel import operator
        request = turns.request_for(_kernel(host), operator())
        return request if request.port is not None else None
    except Exception:  # noqa: BLE001
        return None


# ---- showing one recipe ----------------------------------------------------------------------------------------------------
def show(face, got):
    """One pick, in her talk: its one question, or its answer (a read), or its dry run (a change), and the press."""
    host = face.host
    if got.get('question'):return ask_slot(face, got)
    lead = kv.say('recipe_model') + ' ' if got.get('by') == 'model' else ''
    values = got['values']

    def planned(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(kv.say('failed', why=_why(answer, error)));return
        dry = answer['result']
        if dry['reads'] and dry['ok']:return look(face, got, dry, lead)
        if not all(p['ok'] for p in dry['pre']):
            need = next((n for n in dry['needs'] if not n['found']), None)
            if need:face.say(lead + kv.say('recipe_needs', title=dry['title'], program=need['program'], package=need['package']));return
            face.say(lead + kv.say('recipe_not_ready', title=dry['title'], why='; '.join(p['words'] for p in dry['pre'] if not p['ok'])));return
        if dry['nothing']:
            face.say(lead + kv.say('recipe_nothing', title=dry['title'], why=' '.join(s['words'] for s in dry['steps'] if s.get('words'))));return
        offer(face, got, dry, lead)
    _later(host, lambda: _call(host, 'recipes.dry_run', {'recipe': got['recipe'], 'slots': values}), planned)


def look(face, got, dry, lead=''):
    host = face.host

    def found(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(lead + kv.say('recipe_read_failed', why=_why(answer, error)));return
        v = answer['result']
        bubble = face.say(lead + kv.say('recipe_ran_read', title=v['title']) + ' ' + _words(host, v['words']))
        lines = []
        for step in v['steps']:
            for row in step['rows']:
                lines.append(' · '.join(x for x in (row.get('name', ''), row.get('size_words', ''), row.get('place', '')) if x))
        if lines:_add(bubble, _lines_label(face, lines))
        mark = kv.say('recipe_verified', checked=v['checked']) if v['verified'] else '◆ ' + kv.say('not_verified', checked=v['checked'] or 'nothing')
        _add(bubble, _plain(mark))
        _state(host).pop('offer', None);_column_soon(host)
    _later(host, lambda: _call(host, 'recipes.look', {'recipe': got['recipe'], 'slots': got['values']}), found)


def _plain(text):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text);label.setWordWrap(True);label.setObjectName('RecipeMark')
    return label


def offer(face, got, dry, lead=''):
    """The dry run of a change, said exactly, and the press: Run (your press), or for what cannot be undone, Run and then a
    second press that says so."""
    from .shell2 import sentence
    host = face.host
    lines, left = [], []
    for step in dry['steps']:
        lines += step.get('lines') or []
        left += ['%s: %s' % (l['name'], l['why']) for l in step.get('left') or []]
    words = ' '.join(s['words'] for s in dry['steps'] if s.get('words'))
    summary = _words(host, words)
    defaults = [k for k, v in got['slots'].items() if v.get('basis') == 'recipe_default']
    if defaults:summary += ' ' + kv.say('recipe_defaults', which=', '.join('%s %s' % (k, rb.shown(rb.find_recipe(got['recipe']).slots[k]['type'], got['values'][k])) for k in defaults))
    summary += ' ' + _words(host, dry['undo'] if dry['can_undo'] else kv.say('recipe_cannot'))      # what Undo does, before the press
    bubble = face.say(lead + kv.say('recipe_dry', title=dry['title']))
    _add(bubble, _lines_label(face, lines))      # exactly what it does, file by file
    if left:_add(bubble, _plain(kv.say('recipe_left', left='; '.join(left[:4]) + (' …' if len(left) > 4 else ''))))
    _add(bubble, _plain(summary))                 # then in a sentence, with Undo's words, and the press last (in view in a short column)
    state = _state(host);state['offer'] = {'got': got, 'dry': dry, 'face': face}
    state.pop('done', None)

    def go():
        run(face, got, dry)
    actions = {'run': (kv.say('recipe_run_word') if dry['can_undo'] else kv.say('recipe_run_word_cannot'), go), 'no': (kv.say('recipe_no_word'), lambda: cancel(face))}
    _add(bubble, sentence('{run}  ·  {no}', actions))
    _column_soon(host)
    return bubble


def cancel(face):
    host = face.host
    if _state(host).pop('offer', None) is not None:face.say(kv.say('recipe_cancelled'))
    _column_soon(host)


def run(face, got, dry, sure=False):
    """Your press on Run: what cannot be undone asks once more first; then recipes.run with the digest you were shown."""
    from .shell2 import sentence
    host = face.host
    if not dry['can_undo'] and not sure:
        bubble = face.say(kv.say('recipe_sure', title=dry['title']))
        _add(bubble, sentence('{yes}  ·  {no}', {'yes': (kv.say('recipe_yes_word'), lambda: run(face, got, dry, True)),
                                                 'no': (kv.say('recipe_no_word'), lambda: cancel(face))}))
        return bubble
    _state(host).pop('offer', None)

    def ran(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            why = _why(answer, error)
            if 'changed since you saw it' in why:
                face.say(kv.say('recipe_changed'));show(face, got);return
            face.say(kv.say('recipe_refused', why=why));_column_soon(host);return
        done(face, answer['result'])
    _later(host, lambda: _call(host, 'recipes.run', {'recipe': got['recipe'], 'slots': got['values'], 'digest': dry['digest']}), ran)


def done(face, v):
    """The end of a run: done and verified with Undo, or not verified, or stopped; what Undo would do."""
    from .shell2 import sentence
    host = face.host
    if v['state'] == 'stopped by HALT':said = kv.say('recipe_halted', title=v['title'])
    elif v['verified']:said = kv.say('recipe_done', title=v['title'], checked=_words(host, v['checked']))
    elif v['state'] == 'stopped':said = kv.say('recipe_stopped', why=_words(host, v['checked']))
    else:said = '◆ ' + kv.say('not_verified', checked=_words(host, v['checked']) or 'nothing')
    bubble = face.say(said)
    state = _state(host)
    if v.get('can_undo'):
        state['done'] = {'run': v['run'], 'title': v['title'], 'face': face}
        _add(bubble, sentence('{undo}', {'undo': (kv.say('recipe_undo_word'), lambda: undo(face, v['run'], v['title']))}))
    _column_soon(host)
    return bubble


def undo(face, run_id, title):
    host = face.host
    _state(host).pop('done', None)

    def back(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(kv.say('undo_failed', why=_why(answer, error)));_column_soon(host);return
        v = answer['result']
        face.say(kv.say('recipe_undone', title=title, words=_words(host, v['words'])))
        _column_soon(host)
    _later(host, lambda: _call(host, 'recipes.undo', {'run': run_id}), back)


def ask_slot(face, got):
    """The one question: what the recipe needs that the words did not say; each choice is your press (owner_click)."""
    from .shell2 import sentence
    q = got['question']
    said = kv.say('recipe_ask', title=got['title'], question=q['words'])
    if q.get('why'):said += ' ' + kv.say('recipe_ask_why', why=q['why'])
    bubble = face.say(said)
    actions = {}
    for n, (label, value) in enumerate(q['choices'][:6]):
        actions['c%d' % n] = (label, lambda v=value: show(face, rb.answer(got, q['slot'], v)))
    if actions:_add(bubble, sentence('  ·  '.join('{%s}' % k for k in actions), actions))
    else:_add(bubble, _plain(kv.say('recipe_ask_words')))
    return bubble


def show_list(face):
    """Her recipes, numbered: what each does; a press on one shows it (its question, its answer or its dry run)."""
    from .shell2 import sentence
    recipes, refused = rb.library()
    bubble = face.say(kv.say('recipe_list'))
    reads = [r for r in recipes if r.reads];changes = [r for r in recipes if not r.reads]
    for heading, group in ((kv.say('recipe_list_reads'), reads), (kv.say('recipe_list_changes'), changes)):
        _add(bubble, _plain(heading))
        actions = {}
        for r in group:
            actions['r%d' % r.n] = ('%d %s' % (r.n, _words(face.host, r.name)), lambda r=r: show(face, rb.fill(r, '', by='list')))
        _add(bubble, sentence('  ·  '.join('{%s}' % k for k in actions), actions))
    if refused:_add(bubble, _plain(kv.say('recipe_refused_files', which='; '.join('%s: %s' % (x['file'], x['why']) for x in refused[:3]))))
    return bubble


# ---- her column's NEXT STEPS ---------------------------------------------------------------------------------------------
def next_steps(host):
    """What NEXT STEPS offers for her recipes: Run of a dry run that waits; Undo of the last run."""
    state = STATE.get(id(host)) or {};out = []
    offer_ = state.get('offer')
    if offer_:
        title = offer_['dry']['title']
        out.append({'words': 'Run · %s' % title, 'verb': 'Run', 'object': title, 'kind': 'recipe', 'act': 'run', 'title': title,
                    'tip': 'The dry run is in Talk: exactly what it would do. Your press runs that, and only that.'})
    finished = state.get('done')
    if finished:
        out.append({'words': 'Undo · %s' % finished['title'], 'verb': 'Undo', 'object': finished['title'], 'kind': 'recipe', 'act': 'undo',
                    'title': finished['title'], 'tip': 'Puts back what the recipe changed; what changed since is named, never forced.'})
    return out


def take(host, step):
    """A press on a recipe's NEXT STEP: the same press as the word in her talk."""
    state = STATE.get(id(host)) or {}
    if step.get('act') == 'run' and state.get('offer'):
        o = state['offer'];run(o['face'], o['got'], o['dry']);return True
    if step.get('act') == 'undo' and state.get('done'):
        d = state['done'];undo(d['face'], d['run'], d['title']);return True
    return False


# ---- the line on the bar -----------------------------------------------------------------------------------------------------
def line_rows(text, host=None):
    """For line_finder: [(title, detail, do)] when the words call a recipe; do() shows it in her talk (nothing changes)."""
    try:got = rb.line_pick(text)
    except Exception:  # noqa: BLE001
        return []
    if got is None:return []

    def do():
        shell = getattr(host, 'shell2', None)
        if shell is None:return False
        try:shell.show_slate_face()
        except Exception:  # noqa: BLE001
            pass
        face = getattr(shell, 'face', None)
        if face is None:return False
        face.mine(' '.join(str(text).split()));show(face, got);return True
    detail = kv.say('recipe_line_ask') if got.get('question') else kv.say('recipe_line_detail')
    return [('Recipe: %s' % _words(host, got['title']), detail, do)]
