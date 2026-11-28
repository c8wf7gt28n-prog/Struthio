"""1.1 KV, her voice (PLAN_1.1.md, KV): sharp, fast, dry, short; sure only of what is verified.

Acceptance first: the voice sweep (mind_words.check) passes over every registered line, her talk's, "Waits for you"'s and
HALT's among them; no sentence of hers is over 20 words in the plain register; where nothing is proven she says "Not
verified. Here is what I checked."; HALT and RESUME say what stopped and that nothing restarted. Then her character file
(shorter, never lifting the floor), her hand's lines, the refusals said plainly, the talk's lines read from kas_voice, and
the Guide page quoting her as she speaks.

Run alone:  python3 -B -m unittest -v tests_integrated.test_kas_voice
"""
import os, re, unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
from workbench import mind_words, voice_character, kas_voice, halt  # noqa: E402

WINDOW = ('kas_voice', 'waits_qt', 'halt', 'her_column_qt', 'mind_panel', 'demo_try', 'app_files')


def longest(text):
    plain = re.sub(r'\{[^{}]*\}', 'x', text)
    return max((len(s.split()) for s in mind_words.sentences(plain)), default=0)


class Acceptance(unittest.TestCase):
    def test_the_voice_sweep_passes(self):
        self.assertEqual(mind_words.check(), [])
        found = {module for module, _ in mind_words.collect()}
        for module in ('kas_voice', 'waits_qt', 'halt', 'her_column_qt'):
            self.assertIn(module, found, 'her lines in %s are swept' % module)

    def test_no_sentence_over_twenty_words(self):
        self.assertEqual(mind_words.max_words(), 20)
        self.assertEqual(voice_character.budgets('plain')['words'], 20)
        over = [(m, k) for (m, k), e in mind_words.collect().items() if longest(e['text']) > 20]
        self.assertEqual(over, [])
        self.assertTrue(mind_words.style('One two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                                         'fifteen sixteen seventeen eighteen nineteen twenty twentyone.'))

    def test_not_verified_is_said_as_plainly_as_a_proof(self):
        self.assertEqual(kas_voice.say('not_verified', checked='the file on disk did not change'),
                         'Not verified. Here is what I checked: the file on disk did not change.')
        from workbench import her_column_qt as hc
        now = 1_000_000
        line = hc.hand_words({'state': 'not verified', 'at': now, 'words': 'In Writer: the text does not read as typed'}, now)
        self.assertTrue(line.startswith('◆ Not verified. I checked'), line)
        done = hc.hand_words({'state': 'done', 'at': now, 'words': 'In Writer: saved; the file on disk is new'}, now)
        self.assertTrue(done.startswith('✓ Done, verified'), done)
        self.assertIn('every step verified', hc.say('moment_done', title='Rail head wear'))

    def test_halt_and_resume_say_what_stopped(self):
        said = halt.WORDS['stopped'] % '“Rail head wear”'
        self.assertTrue(said.startswith('HALT. I stopped “Rail head wear”.'), said)
        self.assertIn('until you press RESUME', said)
        self.assertIn('Apps', said)
        self.assertNotIn('program', said.lower())
        self.assertIn('Nothing I stopped has restarted', halt.WORDS['released'])
        self.assertNotIn('Nothing of mine', halt.WORDS['nothing_turns'])      # never "nothing" and "cut off" at once


class Character(unittest.TestCase):
    def test_starter_is_shorter_and_never_lifts_the_floor(self):
        c = voice_character.starter()
        self.assertEqual(c['lengths']['sentence_words'], 20)
        self.assertEqual(c['lengths']['sentences'], {'plain': 3, 'formal': 3, 'warm': 2})
        self.assertLessEqual(c['card_tokens'], voice_character.CARD_MOST)
        self.assertTrue(c['starter'])
        phrases = [x['phrase'] for x in c['never_say']]
        for phrase in ('As an AI', '!', 'safe', 'trust me', 'obviously'):
            self.assertIn(phrase, phrases)
        text = voice_character.STARTER.read_text(encoding='utf-8')
        self.assertIn('Not verified. Here is what I checked.', text)
        _, errors = voice_character.compile_text(text.replace('at most 20 words', 'at most 40 words'))
        self.assertTrue(errors, 'a sentence over the floor is refused')

    def test_never_say_is_caught_in_her_words_only(self):
        self.assertIn('never-say (her character file): trust me', mind_words.scan_text('Trust me, it holds.'))
        self.assertIn('never-say (her character file): obviously', mind_words.scan_text('It obviously holds.'))
        self.assertEqual(mind_words.scan_text('The page says “trust me” here.'), [])


class Lines(unittest.TestCase):
    def test_refusals_losses_and_permissions_are_plain(self):
        from workbench import her_column_qt as hc, waits_qt
        self.assertEqual(hc.say('press_refused', why='the seed is not current'), 'Refused: the seed is not current')
        self.assertEqual(hc.say('stop_refused', why='it had ended'), 'Not stopped: it had ended')
        self.assertEqual(kas_voice.say('undo_failed', why='it changed since'), 'Not taken back, and nothing changed: it changed since')
        self.assertEqual(waits_qt.WORDS['grant_words'].format(words='write in Rail Demo/notes'),
                         'I need your grant to write in Rail Demo/notes. Nothing was sent.')
        self.assertTrue(halt.WORDS['not_held'].startswith('HALT did not hold: %s.'))

    def test_desk_read_and_no_model(self):
        self.assertEqual(kas_voice.say('desk_none', count=1, things=kas_voice.things(1)), 'Desk read: 1 thing. Nothing waits for you.')
        self.assertEqual(kas_voice.say('desk_waits', count=7, things=kas_voice.things(7), n=2), 'Desk read: 7 things. Waiting for you, 2:')
        from workbench import waits_qt
        self.assertTrue(waits_qt.WORDS['no_model'].startswith('No model loaded. I still read the records'))
        self.assertTrue(kas_voice.say('no_model').startswith('No model loaded.'))

    def test_her_talk_reads_kas_voice(self):
        source = (ROOT / 'workbench' / 'shell2.py').read_text(encoding='utf-8')
        self.assertIn("self.say(kv.say('greet'))", source)
        for old in ('I have no brain running yet', 'That did not work: ', 'This plan expired. Ask for a fresh plan.',
                    'It could not be taken back, and nothing was changed', 'I am still answering the last question'):
            self.assertNotIn(old, source)
        self.assertTrue(kas_voice.say('greet').startswith('Ask about what is open.'))

    def test_her_column_words(self):
        from workbench import her_column_qt as hc
        self.assertEqual(hc.say('nothing_active'), 'No assignment open. Ask me for one.')
        self.assertEqual(hc.say('moment_halt'), 'HALT. All my work is stopped. Your Apps and the desktop run on.')
        self.assertEqual(hc.say('stopped', title='Rail head wear'), 'Stopped “Rail head wear”. Done steps stay done. Nothing new starts.')
        for key in WINDOW[3:4]:
            for (module, k), e in mind_words.collect().items():
                if module == key:self.assertNotIn('!', e['text'])

    def test_review_answer_says_only_what_is_proven(self):
        from workbench import desk_review
        self.assertTrue(desk_review.WORDS['not_cleared'].startswith('Not proven sufficient.'))
        self.assertIn('not a verdict on the design', desk_review.WORDS['cleared'])
        found = {module for module, _ in mind_words.collect()}
        for module in ('desk_review', 'day_notice', 'everyday_desk', 'home_pages', 'objective_plan'):
            self.assertIn(module, found, '%s registered her words; the sweep reads them now' % module)

    def test_guide_page_quotes_her_as_she_speaks(self):
        from workbench import waits_qt
        page = ' '.join((ROOT / 'docs' / 'GUIDE_KASANDRA.md').read_text(encoding='utf-8').split())
        self.assertIn('## Her voice', page)
        self.assertIn('"%s"' % waits_qt.WORDS['no_model'], page)
        self.assertIn('Not verified. Here is what I checked.', page)
        self.assertIn('Nothing I stopped has restarted.', page)


if __name__ == '__main__':
    unittest.main()
