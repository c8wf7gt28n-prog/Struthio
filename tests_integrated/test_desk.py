"""HATCH DESK D1a: the desk's one grid as pure arithmetic, and the bands' grain (workbench/desk_qt.py). HATCH DESK D1b: the
panes' tab rows, marks, trees, Trash and feet (workbench/pane_qt.py), and the pointer's geometry (graphite_brand.pointer_shape).
D1-fix: the lower band's word size, Trash's box as its drawing, the cat's poses inside its tile, Activity's work line.

No QApplication is created here; the live window (every mirrored pair at zero pixels at nine sizes, the grain in both bands,
the drag, the panes, the captures) is tools/check_desk_ui.py with tools/symmetry.py.
"""
import math,unittest
from workbench import desk_qt as desk


class PaneWidthTests(unittest.TestCase):
    def test_one_width_for_both_panes_and_the_workspace_is_the_remainder(self):
        for width in (1920, 1366, 1280, 1281, 1041):
            for scale in (1.0, 18 / 14, 20 / 14):
                d = desk.desk(width, scale, 21)
                self.assertEqual(2 * d.pane + 2 * desk.SEPARATOR + d.workspace, width)
                self.assertEqual(d.left, width - d.right, 'the workspace\'s edges mirror about the axis: its centre is the axis')
                self.assertEqual(d.left, d.pane + 1);self.assertEqual(d.right, width - d.pane - 1)

    def test_an_odd_pixel_goes_to_the_workspace(self):
        even, odd = desk.desk(1280, 1.0, 21), desk.desk(1281, 1.0, 21)
        self.assertEqual(even.pane, odd.pane, 'the panes never take the odd pixel');self.assertEqual(odd.workspace, even.workspace + 1)

    def test_the_default_follows_the_interface_size_under_the_ceiling(self):
        self.assertEqual(desk.default_pane(1.0), 360);self.assertEqual(desk.default_pane(18 / 14), 463);self.assertEqual(desk.default_pane(20 / 14), 504)
        self.assertEqual(desk.default_pane(2.0), 504, '28 pt is capped at 1.4');self.assertEqual(desk.default_pane(0.64), 360, 'a smaller interface never shrinks it')
        self.assertEqual(desk.desk(1920, 1.0, 21).pane, 360)

    def test_the_workspace_keeps_the_floor_the_old_rules_protected(self):
        # V01 W1's centre floor, kept: 400 px at 14 pt, scaled up to 1.4 (514 at 18 pt, 560 at 20 pt).
        self.assertEqual([desk.centre_floor(s) for s in (1.0, 18 / 14, 20 / 14, 2.0)], [400, 514, 560, 560])
        for width, scale in ((1366, 18 / 14), (1280, 18 / 14), (1366, 20 / 14), (1280, 20 / 14)):
            d = desk.desk(width, scale, 28)
            self.assertGreaterEqual(d.workspace, desk.centre_floor(scale), (width, scale, d))
        self.assertEqual(desk.desk(1280, 20 / 14, 30).pane, 359, '1280 by 800 at 20 pt: (1280 - 2 - 560) // 2')
        self.assertEqual(desk.desk(1366, 18 / 14, 28, centre=600).workspace, 600, 'the workspace\'s own content raises its floor')

    def test_whole_words_widen_both_panes_and_least_is_a_floor_even_for_the_workspace(self):
        self.assertEqual(desk.pane_width(1920, 1.0, whole=397), 397, 'every slot word whole: both panes widen together')
        self.assertEqual(desk.pane_width(1280, 20 / 14, whole=420, least=340), 359, 'a narrow window: down to what the workspace leaves')
        self.assertEqual(desk.pane_width(1280, 20 / 14, whole=420, least=380), 380, 'never under the slots\' least (primary words whole)')

    def test_the_owners_width_is_one_width_for_both(self):
        self.assertEqual(desk.pane_width(1920, 1.0, owner=420), 420)
        self.assertEqual(desk.pane_width(1920, 1.0, owner=300, whole=330), 330, 'an owner\'s width under the words\' need is raised to it')
        self.assertEqual(desk.pane_width(1366, 1.0, owner=600), 482, 'never so wide the workspace falls under its floor')
        self.assertEqual(desk.pane_width(1920, 1.0, owner=True), 360, 'a stray boolean is not a width');self.assertEqual(desk.pane_width(1920, 1.0, owner=5000), 360)
        self.assertEqual((desk.saved_pane(420), desk.saved_pane(159), desk.saved_pane('420'), desk.saved_pane(None)), (420, None, None, None))


class BandTests(unittest.TestCase):
    def test_both_bands_are_one_height_from_the_cat_or_a_word(self):
        self.assertEqual(desk.band_height(1.0, 21), 60, '14 pt: the 44 px cat and 8 px above and below')
        self.assertEqual(desk.band_height(18 / 14, 27), 73);self.assertEqual(desk.band_height(20 / 14, 30), 78)
        self.assertEqual(desk.band_height(1.0, 40), 40 + desk.WORD_CHROME + 2 * desk.BAND_PAD, 'a tall word wins over the cat')
        self.assertEqual(desk.word_height(21), 43);self.assertEqual(desk.WORD_CHROME % 2, 0, 'even: the line and the words share a text row')

    def test_scaled_sizes(self):
        self.assertEqual([desk.inset(s) for s in (1.0, 18 / 14, 20 / 14)], [16, 21, 22])
        self.assertEqual([desk.gap(s) for s in (1.0, 18 / 14, 20 / 14)], [12, 15, 17])
        self.assertEqual([desk.symbol_px(s) for s in (1.0, 20 / 14)], [32, 45]);self.assertEqual(desk.menu_gap(1.0), 2)
        self.assertEqual([desk.close_gap(s) for s in (1.0, 20 / 14)], [4, 6], 'the gaps close up before a slot word elides')
        self.assertEqual([desk.menu_px(s) for s in (1.0, 18 / 14, 20 / 14, 2.0)], [15, 19, 21, 30], 'the menu words follow the interface size, no ceiling')

    def test_the_word_graphite_is_the_script_with_a_hairline_and_print_when_the_script_is_off(self):
        # The owner, 2026-11-06: "upper left Graphite should be cursive" (the quiet-script rule; print with the switch off).
        self.assertEqual([desk.word_px(s) for s in (1.0, 18 / 14, 20 / 14, 2.0)], [34, 44, 48, 48], 'the script, scaled like the cat and the symbol')
        self.assertEqual([desk.word_px(s, False) for s in (1.0, 20 / 14)], [22, 31], 'print (D1a\'s Plex SemiBold) with the script off')
        self.assertEqual((desk.word_stroke(1.0), desk.word_stroke(20 / 14), desk.word_stroke(1.0, False)), (0.5, 0.7, 0.0), 'a hairline for the script only')


class RowTests(unittest.TestCase):
    MENUS = [54, 64, 54, 74, 98, 57, 92, 59]  # the eight menu words at 14 pt, measured

    def assertMirrored(self, xs, widths, width):
        self.assertEqual(xs[0], width - (xs[-1] + widths[-1]), 'the row\'s two ends mirror about the axis')

    def test_menus_fill_the_column_with_equal_gaps_and_stay_on_the_axis(self):
        for width, pane in ((1920, 360), (1366, 360), (1921, 360), (1920, 397), (1281, 300)):
            start, end = pane + 16, width - pane - 16
            xs, gaps, widths = desk.menu_row(self.MENUS, width, start, end, 4)
            self.assertMirrored(xs, widths, width);self.assertEqual(len(set(gaps)), 1, 'equal gaps')
            self.assertGreaterEqual(xs[0], start);self.assertLessEqual(xs[0] - start, len(self.MENUS) - 1, 'the remainder is a few pixels, shared by both ends')
            # D1-fix: with an odd count of gaps the odd pixel is taken by one pixel less in every gap, never by a wider box, so
            # each word's ink (drawn from its box's air) keeps the row's drawn ends mirrored
            self.assertEqual(widths, self.MENUS, (width, pane, 'no box widened'))

    def test_menus_that_do_not_fit_the_column_are_none(self):
        self.assertIsNone(desk.menu_row(self.MENUS, 1280, 376, 904, 4), 'they need 580 px with the least gap, the column less its inset is 528')

    def test_the_tight_row_is_centred_and_an_odd_pixel_widens_the_last_box(self):
        xs, gaps, widths = desk.tight_row(self.MENUS, 1280, 4);self.assertMirrored(xs, widths, 1280);self.assertEqual(set(gaps), {4})
        seven = self.MENUS[:6] + [31]  # six words and ⋯: six gaps, so the odd pixel cannot go into the gaps
        xs, gaps, widths = desk.tight_row(seven, 1280, 4);self.assertMirrored(xs, widths, 1280);self.assertEqual(len(set(gaps)), 1)
        self.assertEqual(sum(widths), sum(seven) + (1280 - sum(seven) - 6 * 4) % 2, 'the ⋯ box takes the odd pixel, not one side')

    def test_spread_puts_the_first_word_at_start_and_the_last_at_end(self):
        xs, gaps = desk.spread([80, 45, 75, 40, 60], 16, 344)
        self.assertEqual(xs[0], 16);self.assertEqual(xs[-1] + 60, 344);self.assertLessEqual(max(gaps) - min(gaps), 1)
        self.assertEqual(desk.spread([80], 16, 344), ([16], []));self.assertIsNone(desk.spread([200, 200], 16, 344))
        self.assertEqual(desk.mirror(16, 85, 1920), 1819)


class GrainTests(unittest.TestCase):
    def test_the_grain_is_deterministic_quiet_and_centred_on_the_band_tone(self):
        a, b = desk.grain(), desk.grain()
        self.assertEqual(a, b, 'drawn the same every time: no random seed per run')
        self.assertEqual(len(a), desk.GRAIN_SIZE[0] * desk.GRAIN_SIZE[1])
        self.assertLessEqual(max(abs(v) for v in a), desk.GRAIN_AMPLITUDE);self.assertLess(abs(sum(a) / len(a)), 0.05)
        self.assertGreater(len(set(a)), 6, 'a grain, not a flat fill')
        self.assertEqual(desk.tone(0), desk.BAND);self.assertEqual(desk.tone(-300), (0, 0, 0))

    def test_the_lettering_reads_on_the_band(self):
        report = desk.grain_report()
        self.assertEqual(report['mean_tone'], '#4a4741')
        for name in ('lettering', 'quiet lettering'):
            self.assertGreaterEqual(report['contrast'][name]['on_mean'], 4.5, name);self.assertGreaterEqual(report['contrast'][name]['on_light_grain'], 4.5, name)
        for name in ('action mark', 'active mark'):self.assertGreaterEqual(report['contrast'][name]['on_mean'], 3.0, name)  # marks are graphics: 3:1
        self.assertAlmostEqual(desk.contrast('#ffffff', '#000000'), 21.0);self.assertEqual(desk.contrast('#504d46', '#504d46'), 1.0)

    def test_the_band_colours_are_the_palettes(self):
        from workbench import graphite_brand, shell2
        self.assertEqual(desk.ERASED, graphite_brand.ERASED);self.assertEqual(desk.ERASER_MARK, shell2.ERASER_MARK);self.assertEqual(desk.PENCIL, shell2.AMBER_EDGE)
        self.assertEqual(desk.CAT, 44);from workbench import typebar_qt;self.assertEqual(desk.CAT, typebar_qt.HATCH_ICON)


class PaneTests(unittest.TestCase):
    """D1b: the two panes are drawn from the same numbers, so each part mirrors the other on whole pixels."""

    def test_tabs_are_equal_with_equal_gaps_and_the_row_centred_on_its_pane(self):
        from workbench import pane_qt as pane
        for width in range(240, 640):
            for inset, gap, least in ((16, 12, 100), (21, 15, 118), (22, 17, 131), (16, 12, 160)):
                xs, T, g = pane.tab_row(width, inset, gap, 3, least)
                self.assertEqual(len(xs), 3);self.assertGreaterEqual(T, least)
                self.assertEqual([b - a - T for a, b in zip(xs, xs[1:])], [g, g], (width, inset))
                self.assertEqual(xs[0], width - (xs[-1] + T), ('the row centred on the pane, whole pixels', width, inset, gap, least))
                if 3 * least + 2 * gap <= width - 2 * inset:
                    self.assertGreaterEqual(xs[0], inset);self.assertLessEqual(xs[-1] + T, width - inset)
                    self.assertLessEqual(width - 2 * inset - (3 * T + 2 * g), 5, 'the tabs take the room between the insets (a whole-pixel remainder and the parity pixel aside)')
        # the left pane's tab i and the right pane's tab 2 - i mirror about the window's axis (both panes P wide)
        for P, W in ((360, 1920), (415, 1366), (375, 1280)):
            xs, T, g = pane.tab_row(P, 16, 12, 3, 100)
            left = [x for x in xs];right = [W - P + x for x in xs]
            self.assertEqual([W - x - T for x in left], list(reversed(right)))

    def test_one_word_size_for_all_six_tabs_the_menus_or_less_to_stay_whole(self):
        from workbench import pane_qt as pane
        widest = lambda px:px * 6  # a word 6 px wide per pixel of size
        self.assertEqual(pane.tab_px(120, 15, 11, 4, widest), 15, 'room: the menus\' size')
        self.assertEqual(pane.tab_px(90, 15, 11, 4, widest), 13, 'narrow: the largest size that fits')
        self.assertEqual(pane.tab_px(40, 15, 11, 4, widest), 11, 'never under the floor (the pane widens to it instead)')
        self.assertEqual(pane.TAB_GAP, 0)

    def test_the_mark_is_one_short_length_centred_in_every_tab(self):
        from workbench import pane_qt as pane
        for T in range(60, 200):
            for word in (40, 57, 58, 63, 90, 250):
                offset, length = pane.tab_mark(T, word)
                self.assertEqual(2 * offset + length, T);self.assertLessEqual(length, min(word, T));self.assertGreaterEqual(length, min(word, T) - 1)

    def test_tree_rows_trash_and_feet_follow_the_interface_size(self):
        from workbench import pane_qt as pane
        self.assertEqual(pane.tree_metrics(21, 1.0), (33, 22));self.assertEqual(pane.tree_metrics(30, 20 / 14), (30 + 17, 31))
        self.assertEqual(pane.tree_metrics(21, 0.8), (33, 22), 'a smaller interface never shrinks the rows')
        from workbench import trash_can_qt as trash
        self.assertEqual(pane.TRASH_CAN, 30);self.assertGreater(pane.TRASH_CAN, 22, 'larger than the old 22 px can')
        # D1-fix: Trash's box is exactly what it draws (the can's ink, the pad, the word's ink, room for a count), so the box
        # an inset from the pane's inner edge and bottom puts the drawn Trash there
        ink = trash.can_ink(30);w1, h1 = pane.trash_size(1.0, 37, 25, ink);ink2 = trash.can_ink(desk.scaled(pane.TRASH_CAN, 20 / 14));w2, h2 = pane.trash_size(20 / 14, 53, 36, ink2)
        self.assertEqual(h1, math.ceil(ink[3] - ink[1]), 'as tall as the can\'s ink, a full can\'s sheet included');self.assertEqual(w1, math.ceil(ink[2] - ink[0]) + 8 + 37 + 4 + 25)
        self.assertGreater(w2, w1);self.assertGreater(h2, h1)
        u = 30 / 24.0;self.assertAlmostEqual(ink[2] - ink[0], 16 * u + max(1.2, min(1.5 * u, 2.6)), 9, 'the lid\'s outline is the can\'s widest part')
        self.assertEqual(pane.foot_height(1.0, h1, 16), 8 + h1 + 16)

    def test_the_parts_tile_the_pane(self):
        from workbench import pane_qt as pane
        tabs, content, foot = pane.pane_parts(360, 1078, 16, 57, 8, 70)
        self.assertEqual(tabs, (0, 0, 360, 57));self.assertEqual(foot, (0, 1008, 360, 70))
        self.assertEqual(content, (16, 65, 328, 1008 - 65));self.assertEqual(content[1] + content[3], foot[1])


class BandWordTests(unittest.TestCase):
    """D1-fix: the lower band's words are set smaller in a narrow window, never elided; their size is the largest that fits."""

    def test_the_letter_size_follows_the_interface_and_has_a_floor(self):
        self.assertEqual([desk.letter_px(s) for s in (1.0, 18 / 14, 20 / 14)], [16, 21, 23])
        self.assertEqual([desk.letter_floor(s) for s in (1.0, 18 / 14, 20 / 14)], [11, 15, 16], '70% of the size, never under 11 px')
        self.assertEqual([desk.ink_air(s) for s in (1.0, 20 / 14)], [4, 6])

    def test_fit_size_is_the_largest_that_fits_else_the_floor(self):
        need = lambda px:20 * px
        self.assertEqual(desk.fit_size(need, 400, 23, 16), 20);self.assertEqual(desk.fit_size(need, 1000, 23, 16), 23)
        self.assertEqual(desk.fit_size(need, 100, 23, 16), 16, 'never under the floor: the panes widen to it instead')

    def test_the_symbols_height_is_its_marks_proportion(self):
        self.assertAlmostEqual(desk.symbol_height(1.0), 32 * 177 / 224, 9);self.assertAlmostEqual(desk.symbol_height(20 / 14), 45 * 177 / 224, 9)


class CatTests(unittest.TestCase):
    """D1-fix (the brief: "Every pose fits inside the band"): the cat sits whole on its ground inside CAT_BOX in every pose."""

    def test_every_pose_lies_inside_the_tiles_room_and_on_its_ground(self):
        from workbench import graphite_brand as g
        box = g.CAT_BOX
        for pose, params in g.POSES.items():
            l, t, r, b = g.cat_extent(params)
            self.assertGreaterEqual(l, box.left(), pose);self.assertLessEqual(r, box.right(), pose);self.assertGreaterEqual(t, box.top(), pose)
            self.assertLessEqual(b, g.GROUND, pose);self.assertLessEqual(g.GROUND, box.bottom())
        (x1, y1), (x2, y2), width = g.FOCUS_MARK
        self.assertLessEqual(y1 + width / 2, box.bottom(), 'the focus mark inside the tile too');self.assertEqual(x1, -x2, 'centred under the cat')


class ActivityTests(unittest.TestCase):
    """D1-fix (keep Activity quiet): one printed line says what Graphite's work is doing; the list is the System menu's."""

    def test_the_work_line_counts_running_and_waiting_work(self):
        from workbench.operations_qt import work_words
        self.assertEqual(work_words({}), 'WORK · nothing running or queued')
        agenda = dict(now=[dict(kind='job', state='Running')], next=[dict(kind='job', state='Queued'), dict(kind='agenda', state='NEXT'), dict(kind='agenda', state='DONE')])
        self.assertEqual(work_words(agenda), 'WORK · 1 running · 2 queued')
        self.assertEqual(work_words(agenda, dict(title='Inspect')), 'WORK · 1 running · 2 queued\nFirst through queue checks: Inspect')


class PointerTests(unittest.TestCase):
    """D1b: the pointer is the mark's two facets aimed at 11 o'clock, the click at the tip."""

    def test_the_hotspot_is_the_tip_and_the_aim_is_30_degrees_left_of_vertical(self):
        from workbench import graphite_brand as g
        for dpr in (1.0, 2.0):
            shape = g.pointer_shape(dpr);(hx, hy) = shape['hotspot'];tip = shape['polygons'][0][2]
            self.assertEqual(shape['tip'], tip);self.assertEqual(tip, (hx, hy), 'the tip is the hotspot, exactly')
            self.assertAlmostEqual(g.pointer_angle(shape['polygons']), 30.0, places=9)
            aim = (-math.sin(math.radians(30)), -math.cos(math.radians(30)))
            for wedge in shape['polygons']:
                for x, y in wedge:
                    self.assertLessEqual((x - tip[0]) * aim[0] + (y - tip[1]) * aim[1], 1e-9, 'nothing lies beyond the click')
                    self.assertGreaterEqual(min(x, y), g.POINTER_EDGE + 1 - 1e-9);self.assertLessEqual(max(x, y), shape['size'][0] - g.POINTER_EDGE - 1 + 1e-9)
            reach = max(math.hypot(x - tip[0], y - tip[1]) for w in shape['polygons'] for x, y in w)
            self.assertAlmostEqual(reach, g.POINTER_REACH, places=9)

    def test_the_facets_are_the_marks_two_wedges_turned_and_scaled_alike(self):
        from workbench import graphite_brand as g
        shape = g.pointer_shape(1.0);mark = [p for w in (g.UPPER, g.LOWER) for p in w];drawn = [p for w in shape['polygons'] for p in w]
        ratios = {round(math.dist(drawn[i], drawn[j]) / math.dist(mark[i], mark[j]), 9) for i in range(6) for j in range(i + 1, 6)}
        self.assertEqual(len(ratios), 1, 'one similarity: the mark itself, no stretch')
        self.assertAlmostEqual(math.degrees(g.mark_aim()), 13.58, places=2)


if __name__ == '__main__':unittest.main()
