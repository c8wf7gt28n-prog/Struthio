"""The Kasandra appearance (0.8.0): the palette chosen at start, the stills chosen by the state of the work, the checks a
still passes before it is shown, and her name where it is shown."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from workbench import boss_theme, kasandra_art as art
from workbench.session import Session

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'branding' / 'kasandra'


class PaletteTests(unittest.TestCase):
    def test_the_appearance_is_chosen_by_the_environment_then_the_session_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session-r10.json'
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite', 'no file: Graphite')
            path.write_text(json.dumps({'appearance': 'kasandra'}))
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'kasandra')
            self.assertEqual(boss_theme.chosen_appearance({'GRAPHITE_APPEARANCE': 'graphite'}, path), 'graphite', 'the environment first')
            path.write_text(json.dumps({'appearance': 'lain'}))
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite', 'an unknown name is Graphite')
            path.write_text('{not json')
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite')
            self.assertEqual(boss_theme.chosen_appearance({'GRAPHITE_APPEARANCE': ' Kasandra '}, path), 'kasandra')

    def test_both_palettes_name_the_same_colours(self):
        graphite, kasandra = boss_theme.PALETTES['graphite'], boss_theme.PALETTES['kasandra']
        self.assertEqual(set(graphite), set(kasandra))

    def test_graphite_keeps_its_colours_and_its_roles_are_amber(self):
        g = boss_theme.PALETTES['graphite']
        self.assertEqual((g['GROUND'], g['AMBER_EDGE'], g['READY']), ('#0b0e0d', '#ff9a36', '#c3ed74'))
        self.assertEqual(g['OWNER'], g['AMBER_EDGE']);self.assertEqual(g['RECHECK'], g['AMBER_EDGE'])
        self.assertEqual(g['DISPLAY'], 'IBM Plex Mono')
        self.assertEqual((g['MONO'], g['FACE']), ('IBM Plex Mono', 'IBM Plex Sans'))      # 0.8.3: Graphite keeps Plex

    def test_kasandra_follows_the_packs_palette_by_role(self):
        pack = json.loads((PACK / 'palette.json').read_text())
        flat = json.dumps(pack).lower()
        k = boss_theme.PALETTES['kasandra']
        for role in ('GROUND', 'OWNER', 'RECHECK', 'READY', 'TEXT'):
            self.assertIn(k[role].lower(), flat, role)
        self.assertNotEqual(k['OWNER'], k['RECHECK']);self.assertNotEqual(k['OWNER'], k['AMBER_EDGE'])
        self.assertEqual(k['DISPLAY'], 'Kasandra Elite')      # 0.8.3: the typewriter faces built from Special Elite
        self.assertEqual((k['FACE'], k['MONO']), ('Kasandra Elite', 'Kasandra Elite Mono'))

    def test_a_sheet_written_in_graphites_colours_takes_the_colours_of_their_roles(self):
        css = 'QLineEdit {background:#493225;color:#eee9dd;border:1px solid #ff9a36;} QLabel {color:#123456;}'
        with mock.patch.object(boss_theme, 'APPEARANCE', 'graphite'):
            self.assertEqual(boss_theme.recolour(css), css, 'Graphite: unchanged')
        with mock.patch.object(boss_theme, 'APPEARANCE', 'kasandra'):
            k = boss_theme.PALETTES['kasandra'];lit = boss_theme.recolour(css)
            self.assertEqual(lit, 'QLineEdit {background:%s;color:%s;border:1px solid %s;} QLabel {color:#123456;}' % (k['ERASER'], k['TEXT'], k['AMBER_EDGE']))

    def test_a_line_you_can_run_stands_on_royal_purple_and_its_record_numbers_are_short(self):
        with mock.patch.object(boss_theme, 'APPEARANCE', 'graphite'):
            self.assertEqual(boss_theme.line_sheet(), 'color:%s' % boss_theme.TEAL_TEXT, 'Graphite: its green, as before')
        with mock.patch.object(boss_theme, 'APPEARANCE', 'kasandra'), mock.patch.multiple(boss_theme, ROYAL='#7b4fd8', ROYAL_SOFT='#271a58', ROYAL_INK='#ebe2ff'):
            sheet = boss_theme.line_sheet()
            self.assertIn('background:#271a58', sheet);self.assertIn('border-left:3px solid #7b4fd8', sheet);self.assertIn('color:#ebe2ff', sheet)
        line = '/field.set {"id": "office:owner:db5f669f863d4c71b89fa7ba348957da", "cell": "B3", "expected_revision": "69dada6fef720000e4b538e9cc3a9518ecba564118661fc4b7a7e81372536a27"}'
        self.assertEqual(boss_theme.eye(line), '/field.set {"id": "office:owner:db5f66…", "cell": "B3", "expected_revision": "69dada…"}')
        self.assertEqual(boss_theme.eye('field.read | pick waiting'), 'field.read | pick waiting', 'nothing to shorten')
        self.assertEqual(set(boss_theme.PALETTES['graphite']) >= {'ROYAL', 'ROYAL_SOFT', 'ROYAL_INK', 'ROYAL_TEXT', 'HONEY', 'VIOLET'}, True)
        self.assertEqual(boss_theme.PALETTES['graphite']['ROYAL_TEXT'], boss_theme.PALETTES['graphite']['TEAL_TEXT'], 'Graphite keeps its green for lines')

    def test_the_appearance_is_this_computers_and_survives_another_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session-r10.json'
            one = Session(path, Path(folder) / 'one');one.state['appearance'] = 'kasandra';one.save()
            two = Session(path, Path(folder) / 'two')
            self.assertEqual(two.state.get('appearance'), 'kasandra')
            data = json.loads(path.read_text());data['appearance'] = 'rm -rf';path.write_text(json.dumps(data))
            self.assertNotIn('appearance', Session(path, Path(folder) / 'one').state)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        art.forget()

    def test_the_pack_is_whole(self):
        found = art.catalog(PACK)
        self.assertEqual(len(found['scenes']), 8)
        for scene in found['scenes'].values():
            self.assertIsNotNone(art.usable(PACK, scene), scene['id'])

    def test_a_still_is_chosen_by_slot_and_state(self):
        pick = lambda slot, state, turn=0:(art.choose(PACK, slot, state, turn) or {}).get('id')
        self.assertEqual(pick('assistant_rail', 'awaiting_approval'), 'awaiting_enter')
        self.assertEqual(pick('assistant_rail', 'working'), 'working_notes')
        self.assertEqual(pick('assistant_rail', 'completed'), 'completed_pencil')
        self.assertEqual(pick('assistant_rail', 'blocked'), 'blocked_cable')
        self.assertEqual(pick('assistant_rail', 'idle'), 'quiet_window')
        self.assertEqual(pick('field_edge', 'viewing'), 'field_wires')
        self.assertEqual(pick('worksheet_strip', 'viewing'), 'field_wires')
        self.assertEqual({pick('office_banner', 'idle', n) for n in range(4)}, {'office_dusk', 'office_rain'}, 'two for the Office: they take turns')
        self.assertEqual(pick('office_banner', 'idle', 7), pick('office_banner', 'idle', 7), 'the same turn, the same still')
        self.assertEqual(pick('assistant_rail', 'viewing'), 'quiet_window', 'nothing made for it: the quiet still')
        self.assertIsNone(art.choose(PACK, 'no_such_slot', 'idle'))

    def test_paths_outside_the_pack_or_not_pictures_are_refused(self):
        for bad in ('../catalog.json', '/etc/passwd', 'art/../../x.webp', 'art\\x.webp', 'C:/x.webp', 'art/x.txt', '', None, 'a' * 300 + '.webp'):
            self.assertIsNone(art.inside(PACK, bad), bad)
        self.assertEqual(art.inside(PACK, 'art/office_dusk.webp'), PACK / 'art' / 'office_dusk.webp')

    def test_the_neon_logo_is_the_clean_drawing_on_no_ground(self):
        """0.8.3: the owner's neon kp logo, the only kp mark, kept as its clean drawing (tools/cut_kp_neon.py): every pixel
        either clear or of the drawing (alpha 200 or more), trimmed to it, on no ground."""
        from PySide6.QtGui import QGuiApplication, QImage
        app = QGuiApplication.instance() or QGuiApplication([])
        mark = QImage(str(PACK / 'kp_neon.png')).convertToFormat(QImage.Format_ARGB32)
        self.assertEqual((mark.width(), mark.height()), (1401, 838));self.assertTrue(mark.hasAlphaChannel())
        self.assertEqual(mark.pixelColor(2, 2).alpha(), 0, 'its corner is clear: it sits on any ground')
        alphas = bytes(mark.constBits())[3::4]
        self.assertEqual({a for a in alphas if 0 < a < 200}, set(), 'none of the faint fringe is kept')
        _ = app

    def test_a_changed_or_missing_still_gives_way_to_the_next(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'kasandra';shutil.copytree(PACK, copy)
            data = bytearray((copy / 'art' / 'awaiting_enter.webp').read_bytes());data[400] ^= 0xFF
            (copy / 'art' / 'awaiting_enter.webp').write_bytes(bytes(data))
            self.assertEqual(art.choose(copy, 'assistant_rail', 'awaiting_approval')['id'], 'quiet_window', 'a changed file is not shown')
            (copy / 'art' / 'quiet_window.webp').unlink()
            self.assertIsNone(art.choose(copy, 'assistant_rail', 'awaiting_approval'), 'nothing left: the plain ground')
            (copy / 'catalog.json').write_text('{broken')
            self.assertIsNone(art.catalog(copy))

    def test_a_scene_of_the_wrong_shape_is_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'kasandra';shutil.copytree(PACK, copy)
            data = json.loads((copy / 'catalog.json').read_text())
            data['scenes'][0]['focal_point'] = [2, 0];data['scenes'][1]['slots'] = ['nowhere'];data['scenes'][2]['id'] = '../x'
            (copy / 'catalog.json').write_text(json.dumps(data))
            self.assertEqual(len(art.catalog(copy)['scenes']), 5)

    def test_a_late_or_strange_suggestion_changes_nothing(self):
        self.assertEqual(art.suggestion(PACK, 'office_banner', 'idle', 'office_rain', 't1', 't1')['id'], 'office_rain')
        self.assertIsNone(art.suggestion(PACK, 'office_banner', 'idle', 'office_rain', 't1', 't2'), 'the view moved on')
        self.assertIsNone(art.suggestion(PACK, 'office_banner', 'idle', 'blocked_cable', 't1', 't1'), 'not offered for this place')
        self.assertIsNone(art.suggestion(PACK, 'office_banner', 'idle', {'id': 'x'}, 't1', 't1'))

    def test_the_crop_covers_the_place_round_the_focal_point(self):
        self.assertEqual(art.cover(100, 100, 1086, 1448, (0.5, 0.5)), (100, 133, 0, 16))
        sw, sh, left, top = art.cover(900, 300, 1672, 941, (0.58, 0.51))
        self.assertTrue(sw >= 900 and sh >= 300 and 0 <= left <= sw - 900 and 0 <= top <= sh - 300)
        self.assertEqual(art.cover(900, 300, 1672, 941, (1.0, 1.0))[2:], (sw - 900, sh - 300), 'held at the edge')
        sw, sh, left, top = art.cover(84, 84, 1086, 1448, (0.5, 0.48), zoom=2.2)
        self.assertEqual(sw, round(1086 * 84 * 2.2 / 1086));self.assertTrue(0 <= left <= sw - 84)

    def test_a_picture_is_made_at_the_shown_size_and_kept(self):
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance() or QGuiApplication([])
        scene = art.choose(PACK, 'assistant_rail', 'working')
        image = art.picture(PACK, scene, 84, 84, 2.0, zoom=2.2)
        self.assertEqual((image.width(), image.height(), image.devicePixelRatio()), (168, 168, 2.0))
        self.assertEqual(art.picture(PACK, scene, 84, 84, 2.0, zoom=2.2).cacheKey(), image.cacheKey())
        self.assertEqual(len(art.decodes()), 1, 'decoded once')
        for width in range(200, 800, 20):art.picture(PACK, art.choose(PACK, 'office_banner', 'idle'), width, width // 3)
        self.assertLessEqual(len(art._images), art.CACHE_SIZE);self.assertLessEqual(len(art._sources), art.SOURCES)
        self.assertTrue(art.picture(PACK, None, 50, 50).isNull());self.assertTrue(art.picture(PACK, scene, 1, 50).isNull())
        _ = app


class StateTests(unittest.TestCase):
    def host(self, pending=None, job=None, busy=False, would=None):
        face = None if job is None else SimpleNamespace(job=job, findChildren=lambda kind:[])
        top = SimpleNamespace(equalizer=SimpleNamespace(busy=busy))
        return SimpleNamespace(shell2=SimpleNamespace(face=face, top=top), field_page=SimpleNamespace(pending=pending, view=SimpleNamespace(would=would or {})))

    def test_the_state_of_the_work_in_order_of_what_matters(self):
        self.assertEqual(art.current_state(self.host()), 'idle')
        self.assertEqual(art.current_state(self.host(busy=True)), 'working')
        self.assertEqual(art.current_state(self.host(job='j1')), 'working')
        self.assertEqual(art.current_state(self.host(would={'x': 'y'})), 'working')
        self.assertEqual(art.current_state(self.host(pending=object(), busy=True)), 'awaiting_approval', 'what waits for you comes first')
        h = self.host(busy=True);art.note_outcome(h, False)
        self.assertEqual(art.current_state(h), 'blocked', 'a fresh refusal before work that runs')
        h = self.host(busy=True);art.note_outcome(h, True)
        self.assertEqual(art.current_state(h), 'working', 'work that runs before a fresh success')
        h = self.host();art.note_outcome(h, True)
        self.assertEqual(art.current_state(h), 'completed')
        self.assertEqual(art.current_state(h, now=time.monotonic() + art.HOLD['completed'] + 1), 'idle', 'it passes')
        h = self.host();art.note_outcome(h, False)
        self.assertEqual(art.current_state(h, now=time.monotonic() + art.HOLD['blocked'] + 1), 'idle')

    def test_a_bare_host_is_idle(self):
        self.assertEqual(art.current_state(object()), 'idle')
        self.assertEqual(art.current_state(SimpleNamespace(_art_outcome='nonsense')), 'idle')


class NameTests(unittest.TestCase):
    def run_with(self, appearance):
        code = ('from workbench import assistant_identity as a, typebar_qt as t, meter_cards as m;'
                'print(a.NAME);print(t.SHOWN["slate"]);print(a.named("Ask Stacy about this"));print(a.named("TEXT · WHAT STACY HOLDS"))')
        env = dict(os.environ, GRAPHITE_APPEARANCE=appearance, QT_QPA_PLATFORM='offscreen', HOME=tempfile.gettempdir())
        out = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        return out.stdout.split('\n')[:4]

    def test_she_is_stacy_in_graphite_and_kasandra_in_kasandra(self):
        self.assertEqual(self.run_with('graphite'), ['Stacy', 'Stacy', 'Ask Stacy about this', 'TEXT · WHAT STACY HOLDS'])
        self.assertEqual(self.run_with('kasandra'), ['Kasandra', 'Kasandra', 'Ask Kasandra about this', 'TEXT · WHAT KASANDRA HOLDS'])

    def test_history_keeps_the_name_it_was_written_with(self):
        source = (ROOT / 'workbench' / 'local_brain.py').read_text(encoding='utf-8')
        self.assertIn("'STACY'", source, 'the activity actor is a record, not a shown name')
        self.assertIn("named('You are Stacy", source, 'the model is told the name the owner sees')


if __name__ == '__main__':
    unittest.main()
