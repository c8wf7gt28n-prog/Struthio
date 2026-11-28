"""The command tool in her talk, NEXT STEPS and the bar's line (Graphite 1.1 KS2). The classifier and the runs are command_tool's.

Where it shows (the coordinator's note): "her talk and NEXT STEPS; the bar's line (line_finder.py: a row "Run: df -h, only
reads")". The Terminal is the owner's own shell and is not classified (it is theirs). Her words come from kas_voice.py.

  her talk      "run: df -h" (the owner's line, in her line): read and classified (command_tool.from_line). A read runs at once,
                sealed, and its output is shown as data (a line written to an assistant marked ▲, never a request); a network
                read, a change or a bin shows "This will … / The command: …", what Undo does, and waits for your press; a
                refusal is said in plain words with the exact line. With no model, her dictionary maps plain words to a known
                form ("what is using my disk" -> du -xh --max-depth=1 ~); with one, "command: <words>" asks the model for an
                argv (the COMMAND turn), which passes the classifier or is refused, and you always see the exact line.
  NEXT STEPS    a change that waits gives "Run · <the line>"; a run with an Undo gives "Undo · <the line>".
  the line      line_rows(): "Run: df -h, only reads" (and changes something, reaches the network, to the bin, refused);
                Enter shows it in her talk (a read runs there, sealed; nothing else runs without your press).

Every press here is the owner's: dispatched with the owner's principal; the Kernel checks the scope (command.run is execute,
command.undo approve) and refuses a change in her work.
"""
from __future__ import annotations

import re

from . import command_tool as ct
from . import kas_voice as kv
from .recipe_book_qt import _add, _call, _column_soon, _lines_label, _model_request, _plain, _why

SYNC = False                # tests: work on the window's thread instead of a worker
STATE = {}                  # id(host) -> {'offer': {...}, 'done': {...}}: what NEXT STEPS offers
RUN = re.compile(r'^\s*run:\s*(.+)$', re.IGNORECASE | re.DOTALL)
ASK_MODEL = re.compile(r'^\s*(?:command:|(?:give me |propose )?a command (?:to|for|that))\s*(.+)$', re.IGNORECASE | re.DOTALL)


def _state(host):
    return STATE.setdefault(id(host), {})


def _later(host, fn, done, name='graphite-command'):
    if SYNC:
        try:result, error = fn(), None
        except Exception as exc:  # noqa: BLE001
            result, error = None, exc
        done(result, error);return
    from .off_window import run_alone
    run_alone(fn, done, name=name)


def run_line(text):
    """The line after "run:", or None."""
    m = RUN.match(str(text or ''))
    return m.group(1).strip() if m and m.group(1).strip() else None


def _short(line, most=48):
    return line if len(line) <= most else line[:most - 1] + '…'


# ---- the ask chain ----------------------------------------------------------------------------------------------------------
def asked(face, text, dictionary=False):
    """shell2's ask chain. First (dictionary False): "run: …" and "command: …". After the recipes (dictionary True): her
    dictionary's plain words. True when she has answered."""
    words = ' '.join(str(text or '').split())
    if not words:return False
    if not dictionary:
        line = run_line(text)
        if line is not None:
            face.thing = None;face.mine(text);show(face, ct.from_line(line, 'owner'));return True
        m = ASK_MODEL.match(words)
        if m is None:return False
        face.thing = None;face.mine(text);ask_model(face, m.group(1));return True
    try:got = ct.dictionary(words)
    except Exception:  # noqa: BLE001 - a broken dictionary never stands in the way of the rest of her chain
        return False
    if got is None:return False
    if _model_request(face.host) is not None:return False      # with a model, the words keep their 1.0 route ("command: …" asks it for an argv)
    face.thing = None;face.mine(text)
    show(face, ct.classify(got['argv'], 'dictionary'), kv.say('cmd_dictionary') + ' ')
    return True


def ask_model(face, words):
    """The model proposes an argv for the words (COMMAND turn); with no model, her dictionary, or she says how to type it."""
    host = face.host
    request = _model_request(host)
    if request is None:
        got = ct.dictionary(words)
        if got is None:face.say(kv.say('cmd_no_model'));return
        show(face, ct.classify(got['argv'], 'dictionary'), kv.say('cmd_dictionary') + ' ');return

    def proposed(value, error):
        if getattr(host, '_closing', False):return
        if error is not None or value is None:face.say(kv.say('cmd_read_failed', why=_why(None, error) if error else 'no answer'));return
        argv, refused, by = value
        if refused:face.say(kv.say('cmd_model_refused', line=refused.split(' (', 1)[0], why=refused.split(' (', 1)[-1].rstrip(')')))
        if not argv:
            if not refused:face.say(kv.say('cmd_no_model'))
            return
        lead = kv.say('cmd_model') if by == 'model' else kv.say('cmd_dictionary')
        show(face, ct.classify(argv, by), lead + ' ')
    _later(host, lambda: ct.propose(words, request), proposed, 'graphite-command-pick')


# ---- one line, shown ----------------------------------------------------------------------------------------------------------
def show(face, v, lead=''):
    """One classified line in her talk: refused in words, a read run at once, or what it would do and the press."""
    host = face.host
    if not v['ok']:return refused(face, v, lead)
    if v['kind'] == 'read':
        def found(answer, error):
            if getattr(host, '_closing', False):return
            if error is not None or not (answer or {}).get('ok'):
                face.say(lead + kv.say('cmd_read_failed', why=_why(answer, error)));return
            result(face, answer['result'], lead)
        _later(host, lambda: _call(host, 'command.read', {'argv': v['argv'], 'by': v['by']}), found)
        return None

    def planned(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(lead + kv.say('cmd_refused', why=_why(answer, error)));return
        offer(face, v, answer['result'], lead)
    _later(host, lambda: _call(host, 'command.plan', {'argv': v['argv'], 'by': v['by']}), planned)
    return None


def refused(face, v, lead=''):
    why = v['why'][:1].upper() + v['why'][1:]
    if why[-1:] not in '.?':why += '.'
    bubble = face.say(lead + kv.say('cmd_refused', why=why))
    _add(bubble, _lines_label(face, [kv.say('cmd_the_line', line=v['line'])]))
    return bubble


def _output_lines(r):
    lines = ['$ ' + r['line']]
    for row in r['lines']:lines.append(('▲ ' if row['flagged'] else '') + row['text'])
    if not r['lines'] and r.get('err'):lines += [l for l in r['err'].splitlines() if l.strip()][-4:]
    return lines


def result(face, r, lead=''):
    """A read's output, as data: the line, what it printed, the flagged lines marked, and what was checked."""
    host = face.host
    said = kv.say('cmd_ran_network', host=r['host']) if r['kind'] == 'network' else kv.say('cmd_ran_read')
    bubble = face.say(lead + said)
    _add(bubble, _lines_label(face, _output_lines(r)))
    if r['flagged']:_add(bubble, _plain(kv.say('cmd_flagged')))
    mark = kv.say('cmd_verified', checked=r['checked']) if r['verified'] else '◆ ' + kv.say('not_verified', checked=r['checked'] or 'nothing')
    _add(bubble, _plain(mark))
    _state(host).pop('offer', None);_column_soon(host)
    return bubble


def offer(face, v, p, lead=''):
    """"This will … / The command: …", exactly what it touches, what Undo does, and the press."""
    from .shell2 import sentence
    host = face.host
    bubble = face.say(lead + kv.say('cmd_will', says=v['says']))
    _add(bubble, _lines_label(face, [kv.say('cmd_line', line=v['line'])]))      # the exact line that runs
    if p['lines']:_add(bubble, _lines_label(face, list(p['lines'])))             # and exactly what it touches
    if v['kind'] == 'network':note = kv.say('cmd_waits_network', host=v['host'])
    elif v['kind'] == 'bin':note = kv.say('cmd_bin_note') + ' ' + p['undo']
    else:note = kv.say('cmd_waits') + ' ' + (p['undo'] if p['can_undo'] else kv.say('recipe_cannot'))
    _add(bubble, _plain(note))
    state = _state(host);state['offer'] = {'v': v, 'p': p, 'face': face};state.pop('done', None)
    word = {'network': 'cmd_send_word', 'bin': 'cmd_bin_word'}.get(v['kind'], 'cmd_run_word')
    _add(bubble, sentence('{run}  ·  {no}', {'run': (kv.say(word), lambda: run(face, v, p)), 'no': (kv.say('recipe_no_word'), lambda: cancel(face))}))
    _column_soon(host)
    return bubble


def cancel(face):
    host = face.host
    if _state(host).pop('offer', None) is not None:face.say(kv.say('recipe_cancelled'))
    _column_soon(host)


def run(face, v, p):
    """Your press: command.run with the digest of what you were shown."""
    host = face.host
    _state(host).pop('offer', None)

    def ran(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            why = _why(answer, error)
            if 'not what you were shown' in why:face.say(kv.say('recipe_changed'));show(face, ct.classify(v['argv'], v['by']));return
            face.say(kv.say('cmd_refused', why=why));_column_soon(host);return
        done(face, v, answer['result'])
    _later(host, lambda: _call(host, 'command.run', {'argv': v['argv'], 'expect': p['expect'], 'by': v['by']}), ran)


def done(face, v, r):
    """The end of a run: a network read's output; or done and verified with Undo; or stopped, or not verified."""
    from .shell2 import sentence
    host = face.host
    if r['kind'] == 'network':return result(face, r)
    if r['state'] == 'stopped':said = kv.say('cmd_stopped', why=r['checked'])
    elif r['verified']:said = kv.say('cmd_done', checked=r['checked'])
    else:said = '◆ ' + kv.say('not_verified', checked=r['checked'] or 'nothing')
    bubble = face.say(said)
    if r.get('can_undo'):
        _state(host)['done'] = {'run': r['run'], 'line': r['says'][:1].upper() + r['says'][1:], 'face': face}
        _add(bubble, sentence('{undo}', {'undo': (kv.say('recipe_undo_word'), lambda: undo(face, r['run']))}))
    _column_soon(host)
    return bubble


def undo(face, run_id):
    host = face.host
    _state(host).pop('done', None)

    def back(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(kv.say('undo_failed', why=_why(answer, error)));_column_soon(host);return
        face.say(kv.say('cmd_undone', words=answer['result']['words']));_column_soon(host)
    _later(host, lambda: _call(host, 'command.undo', {'run': run_id}), back)


# ---- her column's NEXT STEPS ---------------------------------------------------------------------------------------------
def next_steps(host):
    state = STATE.get(id(host)) or {};out = []
    o = state.get('offer')
    if o:
        line = _short(o['v']['says'][:1].upper() + o['v']['says'][1:])      # what it will do; the exact line is in Talk
        out.append({'words': 'Run · %s' % line, 'verb': 'Run', 'object': line, 'kind': 'command', 'act': 'run', 'title': line,
                    'tip': 'What it will do is in Talk, with the exact line. Your press runs that, and only that.'})
    d = state.get('done')
    if d:
        line = _short(d['line'])
        out.append({'words': 'Undo · %s' % line, 'verb': 'Undo', 'object': line, 'kind': 'command', 'act': 'undo', 'title': line,
                    'tip': 'Puts back what the command changed; what changed since is named, never forced.'})
    return out


def take(host, step):
    state = STATE.get(id(host)) or {}
    if step.get('act') == 'run' and state.get('offer'):
        o = state['offer'];run(o['face'], o['v'], o['p']);return True
    if step.get('act') == 'undo' and state.get('done'):
        d = state['done'];undo(d['face'], d['run']);return True
    return False


# ---- the bar's line --------------------------------------------------------------------------------------------------------
DETAILS = {'read': 'cmd_line_read', 'network': 'cmd_line_network', 'change': 'cmd_line_change', 'bin': 'cmd_line_bin', 'refused': 'cmd_line_refused'}


def line_rows(text, host=None):
    """For line_finder: [(title, detail, verb, do)] for "run: …", or a line that starts with a program of the table and has an
    option ("df -h"); do() shows it in her talk."""
    words = ' '.join(str(text or '').split())
    line = run_line(words)
    if line is None:
        first = words.split(' ', 1)[0] if words else ''
        if first not in ct.cf.TABLE or not re.search(r'\s-', words):return []
        line = words
    v = ct.from_line(line, 'owner')

    def do():
        shell = getattr(host, 'shell2', None)
        if shell is None:return False
        try:shell.show_slate_face()
        except Exception:  # noqa: BLE001
            pass
        face = getattr(shell, 'face', None)
        if face is None:return False
        face.mine('run: ' + line);show(face, ct.from_line(line, 'owner'));return True
    title = 'Run: %s, %s' % (_short(line, 40), ct.CLASS_WORDS[v['kind']])      # the line as you typed it; her talk shows the exact argv
    return [(title, kv.say(DETAILS[v['kind']]), 'Run' if v['kind'] == 'read' else 'Show', do)]
