"""Clip (workbench/clip.py): settings, message building and the OpenAI call, without a network.

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


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ClipTests(unittest.TestCase):
    def test_settings_round_trip_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'clip.json'
            self.assertEqual(clip.Settings.load(p).mode, 'manual')      # no file: copy & paste, no key
            clip.Settings('api', 'gpt-x', 'sk-abc', True).save(p)
            s = clip.Settings.load(p)
            self.assertEqual((s.mode, s.model, s.key, s.include_file), ('api', 'gpt-x', 'sk-abc', True))
            if os.name != 'nt':
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            p.write_text('{"schema": "other"}')
            self.assertEqual(clip.Settings.load(p).mode, 'manual')

    def test_environment_key_and_status(self):
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env'}):
            self.assertEqual(clip.Settings('api').api_key(), 'sk-env')
            self.assertEqual(clip.Settings('api', key='sk-typed').api_key(), 'sk-typed')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(clip.Settings('api').ready())
            self.assertIn('key needed', clip.Settings('api').describe())
            self.assertTrue(clip.Settings('manual').ready())

    def test_messages_and_file(self):
        self.assertEqual(clip.with_file('hi'), 'hi')
        big = clip.with_file('look', 'a.c', 'x' * (clip.MAX_FILE_CHARS + 50))
        self.assertIn('`a.c`', big)
        self.assertIn('(trimmed)', big)
        msgs = clip.build_messages([('user', 'q'), ('assistant', 'a'), ('system', 'ignored'), ('user', '')])
        self.assertEqual([m['role'] for m in msgs], ['system', 'user', 'assistant'])
        self.assertIn('never claim that something ran on hardware', msgs[0]['content'])

    def test_openai_request_and_reply(self):
        seen = {}

        def opener(req, timeout):
            seen['url'], seen['auth'], seen['body'] = req.full_url, req.get_header('Authorization'), req.data
            return FakeResponse(json.dumps({'choices': [{'message': {'content': ' Hello '}}]}).encode())
        out = clip.ask_openai(clip.Settings('api', 'gpt-x', 'sk-1'), [('user', 'hi')], opener=opener)
        self.assertEqual(out, 'Hello')
        self.assertEqual((seen['url'], seen['auth']), (clip.API_URL, 'Bearer sk-1'))
        body = json.loads(seen['body'])
        self.assertEqual((body['model'], body['messages'][-1]), ('gpt-x', {'role': 'user', 'content': 'hi'}))

    def test_openai_errors_are_plain_messages(self):
        def bad_key(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, 'no', {},
                                         io.BytesIO(b'{"error": {"message": "Incorrect API key"}}'))
        with self.assertRaisesRegex(clip.ClipError, 'rejected.*Incorrect API key'):
            clip.ask_openai(clip.Settings('api', key='sk-1'), [('user', 'x')], opener=bad_key)

        def offline(req, timeout):
            raise urllib.error.URLError('no route')
        with self.assertRaisesRegex(clip.ClipError, 'Could not reach OpenAI'):
            clip.ask_openai(clip.Settings('api', key='sk-1'), [('user', 'x')], opener=offline)
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(clip.ClipError, 'No OpenAI API key'):
            clip.ask_openai(clip.Settings('api'), [('user', 'x')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
