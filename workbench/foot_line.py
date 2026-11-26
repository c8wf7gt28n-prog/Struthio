"""The foot is the computer's line (Graphite 1.0 D1; the design direction's section 5).

The owner, 26 November 2026: "Bottom left no longer need a kasandra option, because that exists already in the right
Kasandra column." So the chooser at the foot reads Line · Terminal · Search · Web · Log, and Line is the default. Line does
what the old mode did for lines, and only that:

    a Graphite line          this | count, @files: | rows: run by Enter, the arrow, or the deliberate key, on the working
                             area's line page (a line reads; anything that would change something asks there, as ever)
    an operation by name     /files.list path=Slate: run on the operations page (an approve-scope one asks for a second press)
    an address               https://…, www.…, localhost:8080: opened in this computer's own browser (Web's way)

Words that read as a request to her (K4's objective reading, or plain words that are not a line) are never run here: the
line offers "Ask Kasandra →" (under the line, and as the arrow's own words), which moves the words into her column's ask line
and sends them there, where she plans an objective (K4) or answers. Kas is spoken to in her column only.

Nothing here decides for the owner: the offer is shown, and only their press (Enter on the offer, the arrow, or a click)
gives the words to her. No key is named in any words here.
"""
from __future__ import annotations

from .assistant_identity import named

ASK = named('Ask Stacy →')                      # "Ask Kasandra →": the offer, everywhere it is shown
FOR_HER = named('FOR STACY · HER COLUMN')       # the section of the list under the line that holds the offer
RUN = 'Run this line'
GIVEN = named('Given to Stacy in her column.')
LEADS = ('@', '/', '?', '$')


def reading(host, text, page=None):
    """What the words typed in Line are: 'address', 'operation' (a lead character: / ? $), 'line' (a Graphite line that
    reads), 'hers' (words for Kasandra) or '' (nothing typed). page: the console page the box gives (OneBox.console_page)."""
    words = str(text or '').replace('​', '').strip()
    if not words:return ''
    from .typebar_qt import TypeBar, stac_hint_kind, READS
    if TypeBar.plain_address(words):return 'address'
    if page is None:
        box = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'box', None)
        try:page = box.console_page(words) if box is not None else None
        except Exception:  # noqa: BLE001 - read as words
            page = None
    if words[:1] in ('/', '?', '$') or page in ('kernel', 'find', 'shell'):return 'operation'
    if words.startswith('@'):return 'line'
    try:      # K4's objective reading first: "recheck the startup power" is hers even where a line could be read from it
        from .objective_plan import reads_as_objective
        if reads_as_objective(words):return 'hers'
    except Exception:  # noqa: BLE001 - the reading is the line's own
        pass
    written = words
    try:
        from .field_page import expand_this
        from .stac_words import command, expand, known_to
        written = expand_this(host, command(written) or expand(known_to(host), written))
    except Exception:  # noqa: BLE001 - read as typed
        written = words
    return 'line' if stac_hint_kind(written) in READS else 'hers'


def ask_kasandra(host, text):
    """Ask Kasandra →: the words into her column's ask line, sent there (her column plans an objective, K4, or she answers).
    The keyboard goes to her ask line, where the talk goes on. True when they were given."""
    words = str(text or '').replace('​', '').strip()
    if not words:return False
    column = getattr(host, 'her_column', None);line = getattr(column, 'ask_line', None) if column is not None else None
    if line is not None:
        try:
            line.edit.setText(words);line.send()
            try:
                from PySide6.QtCore import Qt
                line.edit.setFocus(Qt.OtherFocusReason)
            except Exception:  # noqa: BLE001
                pass
            return True
        except RuntimeError:      # her column went with the window
            pass
    shell = getattr(host, 'shell2', None)
    if shell is None or not callable(getattr(shell, 'ask', None)):return False
    shell.ask(words);return True


def run_line(host, text):
    """Run a line typed in Line (the list's "Run this line"), as the arrow and the deliberate key run it: the owner's words
    and `this` written out first, so what runs is what shows; a lead character's page for / ? $."""
    from .shell2 import to_console
    words = str(text or '').replace('​', '').strip()
    if not words:return False
    try:
        from .field_page import expand_this
        from .stac_words import written_out
        words = expand_this(host, written_out(host, words))
    except ValueError as exc:
        bar = getattr(host, 'type_bar', None)
        if bar is not None and callable(getattr(bar, 'note', None)):bar.note(str(exc))
        return False
    except Exception:  # noqa: BLE001 - run as typed
        pass
    box = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'box', None)
    page = box.console_page(words) if box is not None else None
    page = page if page in ('kernel', 'find', 'shell') else 'stac'
    to_console(host, page, words[1:].strip() if page == 'find' and words.startswith('?') else words)
    return True


def rows(box, text, preview=False):
    """The list under the line in Line (OneBox.results): a line first with "Run this line", then the offer to her; words for
    her: the offer first (what Enter takes), then the rest as before (keep it as a note, what worked before, files,
    commands)."""
    from .shell2 import call, capture, preview_rows
    host = box.host;out = [];words = str(text or '')
    short = words if len(words) < 48 else words[:46] + '…'
    kind = reading(host, words, box.console_page(words))
    bar = getattr(host, 'type_bar', None)
    if kind == 'address' and callable(getattr(bar, 'open_web', None)):
        out.append(('section', 'AN ADDRESS', None))
        out.append(('search', 'Open it in your browser  ' + short, ('', lambda: bar.open_web(words))))
    if kind in ('line',):
        out.append(('section', 'A LINE · THE ARROW RUNS IT', None))
        out.append(('stac', RUN + '  ' + short, ('', lambda: run_line(host, words))))
        if preview and words.startswith('@'):out += preview_rows(host, words)
    out.append(('section', FOR_HER, None))
    out.append(('ask', ASK + '  ' + short, ('', lambda: ask_kasandra(host, words))))
    out.append(('keep', 'Keep as a note in Notes', ('', lambda: capture(host, words))))
    learned = call(host, 'matrix.examples', {'text': words[:600]}) or {}
    worked = learned.get('worked') or []
    if worked:
        out.append(('section', 'WORKED BEFORE · FROM THE INSTRUCTION MATRIX', None))
        for row in worked[:2]:
            program = row['program']
            out.append(('stac', program, ('Use', lambda p=program: box.use_program(p))))
    files = box.file_rows(words.casefold())
    if files:
        out.append(('section', 'FILES', None));out += files[:6]
    commands = box.commands(words)
    if commands:
        out.append(('section', 'COMMANDS', None))
        out += [('command', label, (hint, fn)) for label, hint, fn in commands[:6]]
    return out
