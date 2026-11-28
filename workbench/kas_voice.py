"""Her voice (Graphite 1.1 KV): the lines she says in her talk, kept here as templates so the voice sweep reads them.

Her manner, as the owner asked for it in 1.1 (no line, name or picture from anywhere): sharp, fast, sure of her craft, at home on the command line, dry, short sentences, no padding, never talking down, on the owner's side. Her
character file says it for the model (workbench/kasandra/character_starter.md); this module holds her fixed lines.

One guard, which no line here weakens: she is sure only of what is verified. Where nothing is proven she says so just as
plainly (NOT_VERIFIED), and she never jokes about a refusal, a loss or a permission: those lines are plain and exact.

Every line is registered with mind_words like any other template, so mind_words.check() sweeps it: no exclamation mark,
no sentence over her character's sentence length (20 words in the starter), no digit in the fixed words, every number
through a slot that names its record, none of the banned or never-say words. say(key, **slots) fills one.

Pure Python: no Qt, no Kernel, no model.
"""
from __future__ import annotations

from . import mind_words

NOT_VERIFIED = 'Not verified. Here is what I checked: {checked}.'

WORDS = {
    # her talk's first line (the test reads its first sentence)
    'greet': 'Ask about what is open. “This” means what is in the middle of the board. What I read, I show as a line you can run.',
    # what can be done about a thing (plans)
    'steps': 'For “{title}”, this can be done. Press its number in the Field, or choose here.{rule}',
    'steps_all_ask': ' Anything that changes something asks first.',
    'steps_some_ask': ' Steps marked “asks first” wait for you. Other changes I make at once, and show.',
    'step_mine': 'For “{title}”: {words}.',
    'step_waits_why': 'For “{title}”: {words}. It waits for you: {why}.',
    'step_waits': 'For “{title}”: {words}. It changes something, so it waits for your press.',
    # what she did on her own, and taking it back
    'trail': 'What I did on my own, newest first:',
    'trail_none': 'Nothing done on my own yet. At “Do and show”, a change you ask for is made at once and listed here.',
    'undo_twice': 'Already taken back.',
    'undo_done': 'Taken back: {words}. ',
    'undo_trash': '“{name}” is in DELETE, which gives it back.',
    'undo_failed': 'Not taken back, and nothing changed: {why}',
    'always': 'These always wait for you, wherever my hand is set. They cannot be undone:',
    # names she will not take (refusals: plain, no wit)
    'name_kept': '“{name}” is a name Graphite keeps for a folder of its own. Pick another: start a Godot project called …',
    'name_taken': 'Files already has a “{name}”, and I do not write over what is there. Pick another: start a Godot project called …',
    'not_made': 'Nothing made. The folder “{name}” could not be made ({why}).',
    'stopped_at': 'Stopped at the refused step, after {n} of {count}. What I made is in “{name}” in Files. '
                  'Delete that folder if you do not want it; DELETE gives it back.',
    'name_kept_start': '“{name}” starts with a name Graphite keeps for a folder of its own. Pick another name.',
    'name_taken_own': 'Files already has a “{name}”. I do not write over it on my own. Give me another name.',
    # the Terminal
    'term_busy': 'The Terminal is busy, so I have not run this. It is in the line, Terminal chosen, for when that ends.',
    'term_none': 'No Terminal in this window, so I have not run it.',
    'term_ran': 'Ran in the Terminal: {command}. It only reads. The answer is above the line.',
    'term_ask_first': 'My hand is at “Ask first”, so this one is yours. It is in the line, Terminal chosen.',
    'term_may_change': 'That may change something, or I cannot tell it only reads. So it is yours: it is in the line, Terminal chosen.',
    # the desk read
    'desk_none': 'Desk read: {count} {things}. Nothing waits for you.',
    'desk_waits': 'Desk read: {count} {things}. Waiting for you, {n}:',
    # her model, and none
    'busy': 'Still on your last question. Stop it in the Brain room, or give me a moment.',
    'records_only': 'No model loaded, so these are not my words. Here is what the records say about “{title}”, and the line that reads them:',
    'file_only': 'No model loaded. Here is what Graphite itself knows about it.',
    'choose_model': 'For answers in my own words, choose a model. It runs on this computer.',
    'no_model': 'No model loaded. I still read the records and check the desk. Drop a GGUF model on the Brain room, or choose one.',
    'no_words': 'I read it, but could not put it in words: {why}',
    'today_no_model': 'No model loaded yet. {choose} to start one; it runs on this computer.',
    # commands and plans
    'command_busy': 'One command at a time. Wait for this one to finish.',
    'plan_expired': 'This plan has expired. Ask me for a fresh one.',
    'failed': 'That failed: {why}',
    # the guard: nothing proven, said as plainly as a proof
    'not_verified': NOT_VERIFIED,
    # 1.1 B3: a refusal from the Kernel as a plain clause (it follows "Refused: " or stands alone): what it was, that nothing
    # changed where the Kernel refused at its door, and what to do; never an operation's name (Log keeps the raw text)
    'refused_parameters': '{what} reached the Kernel without a detail it needs, so nothing changed. Press it once more. '
                          'If it is refused again, Log has the Kernel’s own words.',
    'refused_scope': '{what} is outside what this session may do, so nothing changed. Give it with your own press in '
                     'Graphite. Log has the Kernel’s own words.',
    'refused_unknown': 'The Kernel does not know {what}, so nothing changed. Ask me for the step again. Log has the '
                       'Kernel’s own words.',
    'refused_other': '{why} Log has the Kernel’s own words.',
    # 1.1 B3: on the bar (her panel, her card, the Pause key)
    'panel_away': 'I am in my panel at the right edge of the screen. Press my name on the bar to bring me back.',
    'card_more': 'And {count} more in my panel.',
    'pause_held': 'HALT already holds my work. RESUME is a press on the bar, never a key.',
    # 1.1 KS1 (recipes): her recipes in her talk, the line and NEXT STEPS (recipe_book_qt)
    'recipe_ran_read': 'Recipe “{title}”. It only reads, so I ran it.',
    'recipe_verified': '✓ Verified: {checked}.',
    'recipe_read_failed': 'Not read: {why}. Nothing was changed.',
    'recipe_dry': 'Recipe “{title}”. This is exactly what it would do; nothing has changed yet.',
    'recipe_defaults': 'The recipe chose {which}. Say another and I plan it again.',
    'recipe_left': 'Left as it is: {left}.',
    'recipe_cannot': 'This cannot be undone. It asks once more before it runs.',
    'recipe_run_word': 'Run it (your press)',
    'recipe_run_word_cannot': 'Run it (asks once more)',
    'recipe_no_word': 'Not now',
    'recipe_yes_word': 'Yes, run it',
    'recipe_undo_word': 'Undo',
    'recipe_cancelled': 'Not run. Nothing changed.',
    'recipe_sure': '“{title}” cannot be undone. Run it anyway?',
    'recipe_changed': 'What it would do changed since you saw it, so nothing ran. Here it is again.',
    'recipe_refused': 'Refused, and nothing changed: {why}',
    'recipe_done': '✓ Done and verified, “{title}”: {checked}.',
    'recipe_stopped': 'Stopped: {why}. What was done is listed, and Undo takes it back.',
    'recipe_halted': 'HALT stopped “{title}”. What was done is listed, and Undo takes it back.',
    'recipe_undone': 'Undone, “{title}”: {words}',
    'recipe_needs': '“{title}” needs {program}, which is not on this computer. Debian’s package “{package}” has it. Nothing was changed.',
    'recipe_not_ready': '“{title}” cannot start: {why}. Nothing was changed.',
    'recipe_nothing': 'Nothing to do for “{title}”: {why}',
    'recipe_model': 'The model picked this recipe by its number; every value in it is from your words.',
    'recipe_ask': 'For “{title}”, one question: {question}',
    'recipe_ask_why': 'From your words: {why}.',
    'recipe_ask_words': 'Say it again with the answer in your words.',
    'recipe_list': 'My recipes. Each one shows what it would do before anything changes.',
    'recipe_list_reads': 'These only read, so they run at once:',
    'recipe_list_changes': 'These change something, so each waits for your press:',
    'recipe_refused_files': 'Recipe files I did not take: {which}',
    'recipe_line_detail': 'Enter shows what it would do; nothing changes',
    'recipe_line_ask': 'Enter asks the one thing it needs; nothing changes',
    # 1.1 KS2 (the command tool): a command in her talk, the line and NEXT STEPS (command_tool_qt)
    'cmd_ran_read': 'It only reads, so I ran it sealed: no network, nothing of yours writable. The output is data.',
    'cmd_ran_network': 'It reached {host} on your press, sealed otherwise. What came back is data.',
    'cmd_line': 'The command: {line}',
    'cmd_the_line': 'The line: {line}',
    'cmd_will': 'This will {says}.',
    'cmd_waits': 'It changes something, so it waits for your press.',
    'cmd_waits_network': 'It reaches {host}, so it waits for your press. NET shows it while it runs.',
    'cmd_bin_note': 'The command itself never runs: the bin takes it.',
    'cmd_run_word': 'Run it (your press)',
    'cmd_send_word': 'Send it (your press)',
    'cmd_bin_word': 'To the bin (your press)',
    'cmd_refused': 'Refused, and nothing ran: {why}',
    'cmd_read_failed': 'Not run: {why}',
    'cmd_verified': '✓ Verified: {checked}.',
    'cmd_done': '✓ Done and verified: {checked}.',
    'cmd_stopped': 'Stopped: {why}. What it did is recorded, and Undo takes it back.',
    'cmd_undone': 'Undone: {words}',
    'cmd_flagged': '▲ marks a line written to an assistant. I read it as data, never as a request.',
    'cmd_dictionary': 'My dictionary reads that as this command.',
    'cmd_model': 'The model proposed this line, and the classifier passed it.',
    'cmd_model_refused': 'The model proposed {line}, and the classifier refused it: {why}. Nothing ran.',
    'cmd_no_model': 'No model is loaded, and my dictionary has no command for that. Type it as run: and the line.',
    'cmd_line_read': 'Enter runs it sealed; the output is data',
    'cmd_line_network': 'Enter shows where it reaches; it waits for your press',
    'cmd_line_change': 'Enter shows what it will do; it waits for your press',
    'cmd_line_bin': 'Enter shows what goes to the bin; it waits for your press',
    'cmd_line_refused': 'Enter says why, in plain words; nothing runs',
}
NUMBERS = {'stopped_at': {'n': 'the steps that went (godot start results)', 'count': 'the start plan\'s steps (godot start plan)'},
           'desk_none': {'count': 'the desk\'s things (desk read)'},
           'desk_waits': {'count': 'the desk\'s things (desk read)', 'n': 'the things that wait (desk read)'},
           'card_more': {'count': 'the rows that wait and are not on the card (assignment.list)'}}
mind_words.register('kas_voice', WORDS, kind='sentence', numbers=NUMBERS)

# 1.1 B3: what a refused press was, in plain words (the Kernel's operation names never reach the owner)
OPERATION_WORDS = {'grant.give': 'the grant', 'grant.give.set': 'the grants', 'grant.revoke': 'the revoke',
                   'grant.words': 'the grant’s words', 'assignment.plan': 'the authorisation', 'assignment.step': 'the step',
                   'assignment.resume': 'the resume', 'assignment.stop': 'the stop', 'assignment.start': 'the assignment',
                   'halt.press': 'HALT', 'halt.release': 'RESUME', 'program.answer': 'your answer'}
_NAMESPACES = ('grant', 'assignment', 'halt', 'program', 'files', 'desk', 'field', 'ledger', 'investigation', 'brain', 'agenda',
               'jobs', 'work', 'network', 'kasandra', 'godot', 'windows', 'apps', 'sheet', 'card', 'session', 'machine', 'plan',
               'objective', 'home', 'go', 'notes', 'office', 'mind', 'hand', 'evidence', 'register')
_OPERATION = None


def plain_operation(name):
    """An operation's name as the owner reads it: 'the grant' for grant.give; 'that press' for one with no plain name."""
    return OPERATION_WORDS.get(str(name or ''), 'that press')


def refusal(raw, operation=''):
    """A refusal from the Kernel (its error message, raw) as she says it: a plain clause that reads after "Refused: " or
    alone, with what to do, and never an operation's name. The raw text is the caller's to keep in Log."""
    import re
    global _OPERATION
    if _OPERATION is None:
        _OPERATION = re.compile(r'\b(?:%s)\.[a-z_]+(?:\.[a-z_]+)*\b' % '|'.join(_NAMESPACES))
    text = ' '.join(str(raw or '').split())
    named = _OPERATION.search(text)
    what = plain_operation(operation or (named.group(0) if named else ''))
    if text.startswith('Unknown or missing parameters') or text.startswith('Parameters must be an object'):
        return say('refused_parameters', what=what[:1].upper() + what[1:])
    if text.startswith('Operation is outside the authorized'):
        return say('refused_scope', what=what[:1].upper() + what[1:])
    if text == 'Unknown operation' or text.startswith('Unknown operation'):
        return say('refused_unknown', what=what)
    text = re.sub(r'^[A-Z][A-Z0-9_]{2,}: ', '', text)      # the record's code ("GRANT_SCOPE: ...") is Log's, not hers
    text = _OPERATION.sub(lambda m: plain_operation(m.group(0)) if m.group(0) in OPERATION_WORDS else 'that operation', text)
    text = (text[:1].upper() + text[1:]) if text else 'The Kernel gave no reason'
    if text[-1:] not in '.?':text += '.'
    return say('refused_other', why=text)


def say(key, **slots):
    """One of her lines with its slots filled."""
    return mind_words.say('kas_voice', key, **slots)


def things(count):
    """'thing' or 'things' for a count (her desk read)."""
    return 'thing' if count == 1 else 'things'
