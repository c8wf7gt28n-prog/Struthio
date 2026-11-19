"""0.8.4: two words that were cut in the Kasandra look, found when the window checks were first run in it (19 November 2026).

The look's typewriter letters are wider than Graphite's. Two places had been measured for Graphite's face only:

1. The Finder's List. At 14 pt the Date Modified column was 120 px wide, which leaves its title 106 px, and the typewriter
   letters need 115. Now a column's default width is its scaled width or what its title needs in the header's own face,
   whichever is more (finder_qt.column_width, title_need). A column the owner has dragged still keeps the owner's width.

2. A line on one of Today's cards. A plain line could break after each '/', so a folder name was one word, and a long one
   (33 letters, on the laptop's screen) was wider than its card and was cut. Now a run longer than 18 characters has a break
   point every 18, as the right pane's words and a line's slab already had (shell2.breakable_path): a long name folds.

Bare widgets on an offscreen QApplication (the List's own sizing, FinderPage.scale_columns, on a bare list); tools/check_finder_ui.py
asserts every word of the real window whole in both looks.
"""
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QStyle, QStyleOptionHeader, QTreeWidget

from workbench import finder_qt, shell2


def label_room(header, column, width):
    """The room the style gives a section's title when the section is `width` wide (as tools/ui_fit measures it)."""
    option = QStyleOptionHeader();header.initStyleOptionForIndex(option, column);option.rect = QRect(0, 0, width, max(1, header.height()))
    return header.style().subElementRect(QStyle.SE_HeaderLabel, option, header).width()


class ColumnTitles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app = QApplication.instance() or QApplication([])

    def listing(self, pixels):
        tree = QTreeWidget();tree.setHeaderLabels(['Name', 'Date Modified', 'Size', 'Kind']);self.addCleanup(tree.deleteLater)
        font = QFont(tree.header().font());font.setPixelSize(pixels);tree.header().setFont(font);return tree

    def test_a_column_is_its_scaled_width_and_never_under_what_its_title_needs(self):
        widths = finder_qt.LIST_WIDTHS
        self.assertEqual([finder_qt.column_width(widths[c], 1.0) for c in (1, 2, 3)], [120, 100, 180])
        self.assertEqual(finder_qt.column_width(120, 18 / 14), 154);self.assertEqual(finder_qt.column_width(120, 18 / 14, 129), 154)
        self.assertEqual(finder_qt.column_width(120, 1.0, 129), 129, 'the title needs more than the scaled width: the title wins')

    def test_a_title_in_wide_letters_is_whole_at_the_width_the_list_gives_it(self):
        tree = self.listing(22);header = tree.header();words = header.fontMetrics().horizontalAdvance('Date Modified')
        self.assertLess(label_room(header, 1, finder_qt.LIST_WIDTHS[1]), words, 'at the 14 pt width alone these letters are cut, as in 0.8.3')
        need = finder_qt.title_need(header, 1);width = finder_qt.column_width(finder_qt.LIST_WIDTHS[1], 1.0, need)
        self.assertGreater(need, words, 'the need counts what the style keeps round the title');self.assertEqual(width, need)
        tree.setColumnWidth(1, width);self.assertGreaterEqual(label_room(header, 1, header.sectionSize(1)), words)

    def test_the_list_gives_a_wide_title_what_it_needs_and_a_dragged_column_keeps_the_owners_width(self):
        tree = self.listing(22);header = tree.header();header.setStretchLastSection(False)  # as the Finder's List
        page = SimpleNamespace(scale=lambda:1.0, list=tree, dragged=set(), list_scale=None, list_widths={})
        finder_qt.FinderPage.scale_columns(page);need = finder_qt.title_need(header, 1)
        self.assertGreater(need, finder_qt.LIST_WIDTHS[1], 'these letters need more than the 14 pt width')
        self.assertGreaterEqual(tree.columnWidth(1), need, 'the List gives Date Modified what its title needs')      # 0.8.3: 120, the title cut
        self.assertEqual(page.list_widths[1], tree.columnWidth(1));self.assertGreaterEqual(label_room(header, 1, header.sectionSize(1)), header.fontMetrics().horizontalAdvance('Date Modified'))
        tree.setColumnWidth(3, 77);page.list_widths[3] = 77;page.dragged.add(3)
        font = QFont(header.font());font.setPixelSize(26);header.setFont(font);finder_qt.FinderPage.scale_columns(page)
        self.assertGreaterEqual(tree.columnWidth(1), finder_qt.title_need(header, 1), 'a new face: the need is measured again')
        self.assertEqual(tree.columnWidth(3), 77, 'a column the owner dragged keeps the owner\'s width')

    def test_a_title_that_fits_leaves_the_width_as_it_was(self):
        tree = self.listing(11);header = tree.header()
        for column, width in finder_qt.LIST_WIDTHS.items():
            self.assertLessEqual(finder_qt.title_need(header, column), width, column)
            self.assertEqual(finder_qt.column_width(width, 1.0, finder_qt.title_need(header, column)), width)


class CardLines(unittest.TestCase):
    LONG = 'a-folder-name-of-thirty-three-chr'      # as long as the folder that was cut
    WORDS = 'Drop files on the Office, or copy them into /srv/' + LONG + '/workspace/Ingress.'

    @classmethod
    def setUpClass(cls):cls.app = QApplication.instance() or QApplication([])

    def test_a_long_name_has_a_break_point_every_eighteen_characters_and_the_words_are_unchanged(self):
        shown = shell2.breakable_path(self.WORDS)
        self.assertEqual(shown.replace('\u200b', ''), self.WORDS, 'only break points are added')
        self.assertLessEqual(max(len(piece) for words in shown.split() for piece in words.split('\u200b')), 18)
        self.assertIn('/\u200bworkspace/\u200bIngress.', shown, 'a path still breaks after each /')
        self.assertEqual(shell2.breakable_path('Nothing is waiting for you.'), 'Nothing is waiting for you.', 'short words are left alone')
        self.assertEqual(len(self.LONG), 33)

    def test_a_cards_line_folds_a_long_folder_name_instead_of_needing_its_whole_width(self):
        card = shell2.Card('Arrived');self.addCleanup(card.deleteLater);card.line(self.WORDS);card.line('gate posts.md', right='Survey/' + self.LONG + '/north field')
        labels = [label for label in card.findChildren(QLabel) if self.LONG in label.text().replace('\u200b', '')]
        self.assertEqual(len(labels), 2, 'the line and the note beside a line')
        for label in labels:
            self.assertTrue(label.wordWrap());whole = label.fontMetrics().horizontalAdvance(self.LONG)
            pieces = [piece for words in label.text().split() for piece in words.split('\u200b')]
            self.assertLess(max(label.fontMetrics().horizontalAdvance(piece) for piece in pieces), whole, 'no piece between break points is the whole name')      # 0.8.3: the name was one piece
            self.assertLess(label.minimumSizeHint().width(), whole, 'the least width of the line is under the whole name: it folds')


if __name__ == '__main__':
    unittest.main()
