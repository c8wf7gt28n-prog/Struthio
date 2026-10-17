"""Clip (workbench/clip.py): settings, message building and the OpenAI call, without a network.

    python3 tests/test_r10_clip.py
"""
import io
import itertools
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


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ClipTests(unittest.TestCase):
    def test_settings_round_trip_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'clip.json'
            s = clip.Settings.load(p)
            self.assertEqual((s.mode, s.model, s.ready()), ('local', 'qwen2.5-coder:7b', True))   # free, no key
            clip.Settings('gemini', {'gemini': 'g-x'}, {'gemini': 'k-abc', 'bogus': 'x'}, True).save(p)
            s = clip.Settings.load(p)
            self.assertEqual((s.mode, s.model, s.keys, s.include_file), ('gemini', 'g-x', {'gemini': 'k-abc'}, True))
            self.assertEqual(s.models['local'], clip.DEFAULT_MODELS['local'])
            if os.name != 'nt':
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            p.write_text('{"schema": "arc1.clip-settings/1", "mode": "api"}')
            self.assertEqual(clip.Settings.load(p).mode, 'local')

    def test_keys_from_environment_and_status(self):
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env', 'GEMINI_API_KEY': 'g-env'}):
            self.assertEqual(clip.Settings('api').api_key(), 'sk-env')
            self.assertEqual(clip.Settings('gemini').api_key(), 'g-env')
            self.assertEqual(clip.Settings('api', keys={'api': 'sk-typed'}).api_key(), 'sk-typed')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(clip.Settings('gemini').ready())
            self.assertIn('key needed', clip.Settings('api').describe())
            self.assertIn('stays on this PC', clip.Settings('local').describe())
            self.assertFalse(clip.Settings('local').leaves_pc())

    def test_messages_and_file(self):
        self.assertEqual(clip.with_file('hi'), 'hi')
        big = clip.with_file('look', 'a.c', 'x' * (clip.MAX_FILE_CHARS + 50))
        self.assertIn('`a.c`', big)
        self.assertIn('(trimmed)', big)
        msgs = clip.build_messages([('user', 'q'), ('assistant', 'a'), ('system', 'ignored'), ('user', '')])
        self.assertEqual([m['role'] for m in msgs], ['system', 'user', 'assistant'])
        self.assertIn('never claim that something ran on hardware', msgs[0]['content'])

    @staticmethod
    def recorder(reply):
        seen = {}

        def opener(req, timeout):
            seen.update(url=req.full_url, headers=dict(req.header_items()), body=json.loads(req.data))
            return FakeResponse(json.dumps(reply).encode())
        return seen, opener

    def test_openai_request_and_reply(self):
        seen, opener = self.recorder({'choices': [{'message': {'content': ' Hello '}}]})
        s = clip.Settings('api', {'api': 'gpt-x'}, {'api': 'sk-1'})
        self.assertEqual(clip.ask_openai(s, [('user', 'hi')], opener=opener), 'Hello')
        self.assertEqual((seen['url'], seen['headers']['Authorization']), (clip.OPENAI_URL, 'Bearer sk-1'))
        self.assertEqual((seen['body']['model'], seen['body']['messages'][-1]), ('gpt-x', {'role': 'user', 'content': 'hi'}))

    def test_gemini_request_and_reply(self):
        seen, opener = self.recorder({'candidates': [{'content': {'parts': [{'text': 'Hi '}, {'text': 'there'}]}}]})
        s = clip.Settings('gemini', keys={'gemini': 'g-1'})
        self.assertEqual(clip.ask_gemini(s, [('user', 'q'), ('assistant', 'a'), ('user', 'q2')], opener=opener),
                         'Hi there')
        self.assertEqual(seen['url'], clip.GEMINI_URL % clip.DEFAULT_MODELS['gemini'])
        self.assertEqual(seen['headers']['X-goog-api-key'], 'g-1')
        self.assertEqual([c['role'] for c in seen['body']['contents']], ['user', 'model', 'user'])
        self.assertIn('ARC-1', seen['body']['systemInstruction']['parts'][0]['text'])

    def test_local_ai_setup_steps_and_reply(self):
        s = clip.Settings('local')
        with mock.patch.object(clip, 'start_ollama', return_value=None):
            with self.assertRaises(clip.NeedsSetup) as e:
                clip.ask_local(s, [('user', 'x')])
            self.assertEqual(e.exception.step, 'install')
        with mock.patch.object(clip, 'start_ollama', return_value=['llama3:latest']):
            with self.assertRaises(clip.NeedsSetup) as e:
                clip.ask_local(s, [('user', 'x')])
            self.assertEqual(e.exception.step, 'model')
        seen, opener = self.recorder({'message': {'content': 'local answer'}})
        with mock.patch.object(clip, 'start_ollama', return_value=['qwen2.5-coder:7b']):
            self.assertEqual(clip.ask_local(s, [('user', 'x')], opener=opener), 'local answer')
        self.assertEqual(seen['url'], clip.OLLAMA_URL + '/api/chat')
        self.assertEqual((seen['body']['model'], seen['body']['stream']), ('qwen2.5-coder:7b', False))
        self.assertTrue(clip.has_model(['phi3:latest'], 'phi3'))

    def test_model_download_reports_progress(self):
        lines = [json.dumps({'status': 'pulling', 'total': 1000, 'completed': 500}).encode() + b'\n',
                 json.dumps({'status': 'success'}).encode() + b'\n']
        seen = []
        with mock.patch.object(clip.time, 'time', side_effect=itertools.count(10)):
            clip.pull_model('m', seen.append, opener=lambda req, timeout: FakeResponse(b''.join(lines)))
        self.assertEqual(seen, ['Downloading m: 50% of 0.0 GB', 'Downloading m: success'])
        bad = json.dumps({'error': 'disk full'}).encode()
        with self.assertRaisesRegex(clip.ClipError, 'disk full'):
            clip.pull_model('m', opener=lambda req, timeout: FakeResponse(bad))

    def test_errors_are_plain_messages(self):
        def bad_key(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, 'no', {},
                                         io.BytesIO(b'{"error": {"message": "Incorrect API key"}}'))
        with self.assertRaisesRegex(clip.ClipError, 'rejected.*Incorrect API key'):
            clip.ask_openai(clip.Settings('api', keys={'api': 'sk-1'}), [('user', 'x')], opener=bad_key)

        def offline(req, timeout):
            raise urllib.error.URLError('no route')
        with self.assertRaisesRegex(clip.ClipError, 'Could not reach Gemini'):
            clip.ask_gemini(clip.Settings('gemini', keys={'gemini': 'g'}), [('user', 'x')], opener=offline)
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(clip.ClipError, 'aistudio'):
            clip.ask_gemini(clip.Settings('gemini'), [('user', 'x')])


try:
    import PySide6  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, 'PySide6 not installed: the Clip bubbles were NOT tested')
class ClipOverlayTests(unittest.TestCase):
    def test_bubbles_float_over_the_window_and_local_setup_flows(self):
        import time
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': d}):
            from workbench import qt_app
            app = qt_app.make_app(['clip-test'])
            w = qt_app.WorkbenchWindow(restore=False)
            w.resize(1200, 700)
            w.show()

            def spin(n=40):
                for _ in range(n):
                    app.processEvents()
                    time.sleep(0.01)
            w.open_clip()
            spin(3)
            o = w.clip_overlay
            self.assertIs(o.parent(), w)                    # bubbles on the window, not a separate window
            self.assertFalse(o.isWindow())
            self.assertTrue(o.isVisible())
            calls = []

            def ask(settings, history):
                calls.append(history[-1])
                if len(calls) == 1:
                    raise clip.NeedsSetup('model', 'The model is not downloaded yet.')
                return 'Answer from the local model.'
            with mock.patch.object(clip, 'ask', ask), \
                    mock.patch.object(clip, 'start_ollama', lambda wait=15: ['qwen2.5-coder:7b']):
                o.input.setText('Why is the LCD blank?')
                o.send()
                spin()
                buttons = [b.text() for b in o.findChildren(qt_app.QPushButton)]
                self.assertIn('Download qwen2.5-coder:7b', buttons)
                o._setup('model')
                spin(80)
            self.assertEqual(o.history[-1], ('assistant', 'Answer from the local model.'))
            self.assertFalse(o.mask().isEmpty())
            self.assertLess(o.mask().boundingRect().width() * o.mask().boundingRect().height(),
                            w.width() * w.height())          # the editor around the bubbles stays clickable
            w.open_clip()
            self.assertFalse(o.isVisible())                 # clicking Clip again hides the bubbles
            w.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
