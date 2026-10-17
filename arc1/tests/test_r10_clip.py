"""Clip (workbench/clip.py and the Qt bubbles): Google Gemini with a free key, without a network.

The fake Google answers in the formats documented at ai.google.dev; the invalid-key
body is the one the real API returned (October 2026). With GEMINI_API_KEY set, a
live test also calls Google for real (the key is never written to the repository):
    GEMINI_API_KEY=... python3 tests/test_r10_clip.py

    python3 tests/test_r10_clip.py
"""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import clip  # noqa: E402

INVALID_KEY_BODY = json.dumps({'error': {
    'code': 400, 'message': 'API key not valid. Please pass a valid API key.', 'status': 'INVALID_ARGUMENT',
    'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': 'API_KEY_INVALID',
                 'domain': 'googleapis.com', 'metadata': {'service': 'generativelanguage.googleapis.com'}}]}})
MODELS = ['gemini-3.8-flash', 'gemini-3.6-flash', 'gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-3.5-flash-lite',
          'gemini-flash-latest', 'gemini-3.1-flash-image', 'gemini-3.8-flash-tts', 'gemini-4-argon', 'gemini-3.8-live']


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def answer(text, **extra):
    return {'candidates': [dict({'content': {'role': 'model', 'parts': [{'text': text}]}, 'finishReason': 'STOP'},
                                **extra)]}


class FakeGoogle:
    """Routes requests like generativelanguage.googleapis.com. ``replies`` maps model -> list of
    (status, body) consumed in order; a missing model answers 404."""
    def __init__(self, models=MODELS, replies=None, key='good-key-0123456789-0123456789-abc'):
        self.models, self.replies, self.key, self.calls = models, replies or {}, key, []

    def __call__(self, req, timeout):
        url, key = req.full_url, req.get_header('X-goog-api-key')
        body = json.loads(req.data) if req.data else None
        self.calls.append((req.get_method(), url, body))
        if key != self.key:
            raise urllib.error.HTTPError(url, 400, 'Bad Request', {}, io.BytesIO(INVALID_KEY_BODY.encode()))
        if url.startswith(clip.API + '/models?'):
            return FakeResponse(json.dumps({'models': [
                {'name': 'models/' + m, 'supportedGenerationMethods':
                    ['generateContent', 'countTokens'] if 'live' not in m else ['bidiGenerateContent']}
                for m in self.models]}).encode())
        model = url.rsplit('/', 1)[-1].split(':')[0]
        queue = self.replies.get(model)
        if not queue:
            raise urllib.error.HTTPError(url, 404, 'Not Found', {}, io.BytesIO(json.dumps(
                {'error': {'code': 404, 'status': 'NOT_FOUND', 'message': 'models/%s is not found' % model}}).encode()))
        status, payload = queue.pop(0)
        if status != 200:
            raise urllib.error.HTTPError(url, status, 'x', {}, io.BytesIO(json.dumps(payload).encode()))
        return FakeResponse(json.dumps(payload).encode())


class ClipTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'clip.json'
            s = clip.Settings.load(p)
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertFalse(s.ready())
                self.assertIn('free key needed', s.describe())
            clip.Settings('k' * 39, 'gemini-3.8-flash', True).save(p)
            s = clip.Settings.load(p)
            self.assertEqual((s.key, s.model, s.include_file), ('k' * 39, 'gemini-3.8-flash', True))
            if os.name != 'nt':
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)
                self.assertNotIn('k' * 39, json.dumps(clip.seal_key('x')))
            p.write_text('{"schema": "arc1.clip-settings/2", "mode": "local"}')   # R10.4 settings are ignored
            self.assertEqual(clip.Settings.load(p).key, '')
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': 'from-env'}):
            self.assertEqual(clip.Settings().api_key(), 'from-env')
            self.assertEqual(clip.Settings('typed').api_key(), 'typed')

    def test_pasted_key_is_recognised_without_assuming_a_prefix(self):
        self.assertTrue(clip.looks_like_key('AIzaSy' + 'A' * 33))
        self.assertTrue(clip.looks_like_key('  gk-auth.' + 'b7' * 20 + '\n'))
        self.assertFalse(clip.looks_like_key('why is the LCD blank after boot?'))
        self.assertFalse(clip.looks_like_key('short'))

    def test_models_are_picked_from_the_keys_own_list(self):
        self.assertEqual(clip.pick_models(MODELS), ['gemini-flash-latest', 'gemini-3.8-flash', 'gemini-3.6-flash',
                                                    'gemini-2.5-flash', 'gemini-3-flash-preview',
                                                    'gemini-3.5-flash-lite'])
        g = FakeGoogle()
        self.assertNotIn('gemini-3.8-live', clip.list_models(g.key, opener=g))   # cannot chat (no generateContent)

    def test_request_format_and_reply(self):
        g = FakeGoogle(replies={'gemini-flash-latest': [(200, {'candidates': [{'content': {'parts': [
            {'text': 'thinking...', 'thought': True}, {'text': 'Call '}, {'text': 'lcd_status_init().'}]},
            'finishReason': 'STOP'}]})]})
        s = clip.Settings(g.key)
        history = [('assistant', 'greeting first'), ('user', 'q1'), ('assistant', 'a1'), ('user', 'q2')]
        self.assertEqual(clip.ask(s, history, opener=g), 'Call lcd_status_init().')   # thought parts skipped
        self.assertEqual(s.model, 'gemini-flash-latest')
        method, url, body = g.calls[-1]
        self.assertEqual((method, url), ('POST', clip.API + '/models/gemini-flash-latest:generateContent'))
        self.assertEqual([c['role'] for c in body['contents']], ['user', 'model', 'user'])   # starts with the user
        self.assertIn('never claim that something ran on hardware', body['systemInstruction']['parts'][0]['text'])
        self.assertTrue(all(c[1].startswith(clip.API) for c in g.calls))

    def test_saved_model_gone_falls_back(self):
        g = FakeGoogle(replies={'gemini-flash-latest': [(200, answer('ok'))]})
        s = clip.Settings(g.key, 'gemini-2.0-flash')             # shut down by Google
        self.assertEqual(clip.ask(s, [('user', 'x')], opener=g), 'ok')
        self.assertEqual(s.model, 'gemini-flash-latest')

    def test_free_limit_moves_to_the_next_flash_model_then_explains(self):
        quota = {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'Quota exceeded',
                           'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '41s'}]}}
        g = FakeGoogle(replies={'gemini-flash-latest': [(429, quota)], 'gemini-3.8-flash': [(200, answer('second'))]})
        s = clip.Settings(g.key)
        self.assertEqual(clip.ask(s, [('user', 'x')], opener=g), 'second')
        self.assertEqual(s.model, 'gemini-3.8-flash')
        g = FakeGoogle(models=['gemini-flash-latest'], replies={'gemini-flash-latest': [(429, quota)]})
        with self.assertRaisesRegex(clip.ClipError, 'free limit is used up.*41s') as e:
            clip.ask(clip.Settings(g.key), [('user', 'x')], opener=g)
        self.assertEqual(e.exception.kind, 'quota')

    def test_busy_google_is_retried_once(self):
        busy = {'error': {'code': 503, 'status': 'UNAVAILABLE', 'message': 'overloaded'}}
        g = FakeGoogle(replies={'gemini-flash-latest': [(503, busy), (200, answer('after retry'))]})
        slept = []
        self.assertEqual(clip.ask(clip.Settings(g.key), [('user', 'x')], opener=g, sleep=slept.append),
                         'after retry')
        self.assertEqual(slept, [2])

    def test_bad_key_and_other_problems_in_plain_words(self):
        g = FakeGoogle()
        with self.assertRaisesRegex(clip.ClipError, "this key isn't valid") as e:
            clip.check_key('wrong-key-0123456789-0123456789', opener=g)
        self.assertEqual(e.exception.kind, 'key')
        denied = urllib.error.HTTPError('u', 403, 'x', {}, io.BytesIO(b'{"error": {"status": "PERMISSION_DENIED"}}'))
        with self.assertRaisesRegex(clip.ClipError, "isn't allowed to use Gemini"):
            clip.list_models('k', opener=mock.Mock(side_effect=denied))
        with self.assertRaisesRegex(clip.ClipError, "Can't reach Google"):
            clip.list_models('k', opener=mock.Mock(side_effect=urllib.error.URLError('no route')))
        g = FakeGoogle(replies={'gemini-flash-latest': [(200, {'promptFeedback': {'blockReason': 'SAFETY'}})]})
        with self.assertRaisesRegex(clip.ClipError, 'blocked this message \\(SAFETY\\)'):
            clip.ask(clip.Settings(g.key), [('user', 'x')], opener=g)
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(clip.ClipError, 'free Google key'):
            clip.ask(clip.Settings(), [('user', 'x')])

    def test_check_key_proves_the_key_end_to_end(self):
        g = FakeGoogle(replies={'gemini-flash-latest': [(200, answer('ready'))]})
        self.assertEqual(clip.check_key(g.key, opener=g), 'gemini-flash-latest')
        self.assertEqual([c[0] for c in g.calls], ['GET', 'POST'])    # model list, then one real answer

    def test_open_file_is_attached_only_when_asked(self):
        self.assertEqual(clip.with_file('hi'), 'hi')
        big = clip.with_file('look', 'a.c', 'x' * (clip.MAX_FILE_CHARS + 50))
        self.assertIn('`a.c`', big)
        self.assertIn('(trimmed)', big)


@unittest.skipUnless(os.environ.get('GEMINI_API_KEY'), 'GEMINI_API_KEY not set: the live Google call was NOT run')
class LiveGeminiTests(unittest.TestCase):
    """Real calls to Google with the owner's key (never stored in the repository)."""
    def test_key_check_and_a_two_turn_conversation(self):
        key = os.environ['GEMINI_API_KEY']
        model = clip.check_key(key)
        self.assertIn('flash', model)
        s = clip.Settings(key, model)
        code = 'int f(int x) { if (x < 0) return -7; return x; }'
        history = [('user', clip.with_file('What does f return for x = -3? Reply with just the number.', 'f.c', code))]
        first = clip.ask(s, history)
        self.assertIn('-7', first)
        history += [('assistant', first), ('user', 'And for x = 5? Just the number.')]
        self.assertIn('5', clip.ask(s, history))


try:
    import PySide6  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, 'PySide6 not installed: the Clip bubbles were NOT tested')
class ClipOverlayTests(unittest.TestCase):
    def test_first_use_key_setup_then_answer_in_bubbles(self):
        import time
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': d}), \
                mock.patch.dict(os.environ, {}, clear=False) as env:
            env.pop('GEMINI_API_KEY', None)
            from workbench import qt_app
            app = qt_app.make_app(['clip-test'])
            w = qt_app.WorkbenchWindow(restore=False)
            w.resize(1200, 700)
            w.show()

            def spin(n=40):
                for _ in range(n):
                    app.processEvents()
                    time.sleep(0.01)
            with mock.patch.object(qt_app.QDesktopServices, 'openUrl') as opened:
                w.open_clip()
                spin(3)
                o = w.clip_overlay
                self.assertIs(o.parent(), w)                # bubbles on the window, not a separate window
                self.assertFalse(o.isWindow())
                self.assertTrue(o.isVisible() and o.expect_key)
                get = [b for b in o.findChildren(qt_app.QPushButton) if b.text() == 'Get a free key']
                self.assertTrue(get)
                get[0].click()
                self.assertEqual(opened.call_args[0][0].toString(), clip.KEY_URL)

            key = 'AIzaSy' + 'Q' * 33
            answers = []

            def ask(settings, history):
                answers.append(history[-1])
                return 'The LCD service starts in main().'
            with mock.patch.object(clip, 'check_key', lambda k: 'gemini-flash-latest') as _, \
                    mock.patch.object(clip, 'ask', ask):
                o.input.setText('Why is the LCD blank?')    # asked before the key: kept for later
                o.send()
                o.input.setText(key)
                o.send()
                spin(60)
            self.assertFalse(o.expect_key)
            self.assertEqual(o.settings.key, key)
            self.assertEqual(answers, [('user', 'Why is the LCD blank?')])
            self.assertEqual(o.history[-1], ('assistant', 'The LCD service starts in main().'))
            shown = ' '.join(lbl.text() for lbl in o.findChildren(qt_app.QLabel))
            self.assertNotIn(key, shown)                     # the key never appears on screen
            self.assertEqual(clip.Settings.load().key, key)  # and is remembered
            self.assertFalse(o.mask().isEmpty())
            self.assertLess(o.mask().boundingRect().width() * o.mask().boundingRect().height(),
                            w.width() * w.height())          # the editor around the bubbles stays clickable
            w.open_clip()
            self.assertFalse(o.isVisible())                 # clicking Clip again hides the bubbles
            w.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
