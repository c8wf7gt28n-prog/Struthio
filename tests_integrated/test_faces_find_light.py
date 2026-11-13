"""0.4.9 and 0.5: the face of a tool button (words or a glyph), Find in whatever is open, a page in the desk's light,
the glyph set, and what the session keeps of them.

Real offscreen widgets; no window of the program, no job, worker, model, provider or native program. Everything written
goes to a temporary folder.
"""
import os,tempfile,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QEvent,Qt
from PySide6.QtGui import QColor,QImage,QPainter,QPixmap
from PySide6.QtWidgets import (QApplication,QLabel,QListWidget,QPlainTextEdit,QPushButton,QScrollArea,QTabWidget,QTableWidget,
                               QTableWidgetItem,QTreeWidget,QTreeWidgetItem,QVBoxLayout,QWidget)
from workbench import boss_theme,centre_find,glyph_set,page_light,tool_faces
from workbench.field_model import KINDS
from workbench.session import Session

APP=QApplication.instance() or QApplication([])


def drawn(draw,size=20,ink='#f4e8ce',accent='#c8baa0'):
    """A glyph painted alone on nothing: its image."""
    image=QImage(size,size,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
    p=QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.scale(size/20.0,size/20.0);draw(p,QColor(ink),QColor(accent));p.end()
    return image


def inked(image):
    return sum(1 for y in range(image.height()) for x in range(image.width()) if QColor.fromRgba(image.pixel(x,y)).alpha()>40)


class GlyphSetTests(unittest.TestCase):
    def test_every_glyph_draws_something_inside_its_box_and_leaves_the_painter_as_it_was(self):
        for name,draw in sorted(glyph_set.GLYPHS.items())+sorted(glyph_set.KIND.items()):
            image=QImage(28,28,QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
            p=QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.translate(4,4);before=p.worldTransform()
            draw(p,QColor('#f4e8ce'),QColor('#c8baa0'));self.assertEqual(p.worldTransform(),before,name+' left the painter moved');p.end()
            marks=inked(image);self.assertGreater(marks,12,name+' draws almost nothing')
            edge=sum(1 for i in range(28) for x,y in ((i,0),(i,27),(0,i),(27,i)) if QColor.fromRgba(image.pixel(x,y)).alpha()>40)
            self.assertEqual(edge,0,name+' runs four pixels past its 20-unit box')

    def test_a_kind_of_sheet_never_lacks_a_glyph_and_mirrored_pairs_differ(self):
        self.assertEqual(sorted(set(KINDS)-set(glyph_set.KIND)),[],'every kind of sheet on the Field has its glyph')
        for one,other in (('undo','redo'),('previous','next')):
            self.assertNotEqual(drawn(glyph_set.GLYPHS[one]),drawn(glyph_set.GLYPHS[other]),one+' and '+other+' are the same drawing')

    def test_every_word_that_wears_a_glyph_names_one_that_exists(self):
        self.assertEqual(sorted(set(tool_faces.FOR_WORDS.values())-set(glyph_set.GLYPHS)),[])
        self.assertEqual(sorted(set(tool_faces.BARE)-set(glyph_set.GLYPHS)),[])


class ToolFaceTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda:tool_faces.STATE.update(mode='words'));tool_faces.STATE['mode']='words'
        self.host=QWidget();self.row=QVBoxLayout(self.host)

    def button(self,words):
        b=QPushButton(words);self.row.addWidget(b);return tool_faces.wear(b)

    def test_words_are_the_default_and_a_button_is_left_alone(self):
        b=self.button('Copy citation');self.assertEqual(tool_faces.mode(),'words')
        self.assertEqual((b.minimumWidth(),b.maximumWidth()),(0,tool_faces.WIDEST));self.assertFalse(b.property('facedWidths'))

    def test_icons_change_only_the_width_and_going_back_restores_it(self):
        bare,worded,plain=self.button('Find'),self.button('Copy citation'),self.button('Something with no glyph')
        worded.setMinimumWidth(77);tool_faces.STATE['mode']='icons'
        for b in (bare,worded,plain):tool_faces.fit(b)
        self.assertEqual((bare.minimumWidth(),bare.maximumWidth()),(tool_faces.SIDE+10,tool_faces.SIDE+10),'a glyph alone is a small square')
        self.assertEqual(worded.minimumWidth(),worded.maximumWidth());self.assertGreater(worded.minimumWidth(),tool_faces.SIDE+40,'its words stay beside its glyph')
        self.assertEqual((plain.minimumWidth(),plain.maximumWidth()),(0,tool_faces.WIDEST),'no glyph: it keeps its plate and its words')
        self.assertEqual([b.text() for b in (bare,worded,plain)],['Find','Copy citation','Something with no glyph'],'the words are never changed')
        tool_faces.STATE['mode']='words'
        for b in (bare,worded,plain):tool_faces.fit(b)
        self.assertEqual((bare.minimumWidth(),bare.maximumWidth()),(0,tool_faces.WIDEST))
        self.assertEqual((worded.minimumWidth(),worded.maximumWidth()),(77,tool_faces.WIDEST),'the width it had before is the width it gets back')

    def test_a_glyph_is_painted_only_when_icons_are_chosen(self):
        b=self.button('Save');b.resize(40,28);event=type('E',(),{'type':lambda self:QEvent.Paint})()
        self.assertFalse(tool_faces.FACE.eventFilter(b,event),'with words the style sheet draws the button')
        tool_faces.STATE['mode']='icons';tool_faces.fit(b);image=QPixmap(b.size());image.fill(QColor(boss_theme.GROUND))
        self.assertEqual(tool_faces.glyph_of(b),'save');self.assertIsNone(tool_faces.glyph_of(self.button('Something with no glyph')))

    def test_the_words_beside_a_glyph_lose_only_the_arrow_the_glyph_replaces(self):
        self.assertEqual([tool_faces.said(w) for w in ('‹ Field','Next ›','More ▾','Export…','Copy citation')],['Field','Next','More','Export','Copy citation'])


class FindTests(unittest.TestCase):
    def test_writing_is_searched_without_regard_to_capitals_and_in_reading_order(self):
        text=QPlainTextEdit();text.setPlainText('The pulse was 80 ms.\nA second Pulse followed.\nNo more.')
        found,more=centre_find.places(text,'pulse');self.assertEqual((found,more),([(4,9),(30,35)],False))
        self.assertEqual(centre_find.places(text,'zzz'),([],False))

    def test_a_table_is_searched_cell_by_cell_and_hidden_rows_are_not(self):
        table=QTableWidget(3,2)
        for r,row in enumerate((('Rail voltage','12'),('Settled current','280'),('Startup current','650'))):
            for c,value in enumerate(row):table.setItem(r,c,QTableWidgetItem(value))
        self.assertEqual(centre_find.places(table,'CURRENT'),([(1,0),(2,0)],False))
        table.setRowHidden(1,True);self.assertEqual(centre_find.places(table,'current'),([(2,0)],False))

    def test_a_tree_and_a_list_are_searched_by_their_rows(self):
        tree=QTreeWidget();tree.setColumnCount(2);top=QTreeWidgetItem(tree,['Engineering','']);QTreeWidgetItem(top,['Rail limits','rev B']);QTreeWidgetItem(top,['Bench','rev A'])
        self.assertEqual([i.text(0) for i in centre_find.places(tree,'rev b')[0]],['Rail limits'])
        rows=QListWidget();rows.addItems(['07 Case conclusion','07 Settled power','07 Startup power'])
        self.assertEqual([i.text() for i in centre_find.places(rows,'power')[0]],['07 Settled power','07 Startup power'])

    def test_a_page_of_words_is_searched_line_by_line_without_its_markup(self):
        page=QWidget();box=QVBoxLayout(page);lines=[QLabel('<b>Settled</b> draw is 3.36 W.'),QLabel('Startup ran 30 ms past the limit.'),QLabel('')]
        for line in lines:box.addWidget(line)
        page.show();APP.processEvents()
        self.assertEqual(centre_find.places(page,'settled draw')[0],[lines[0]],'the words are found across the markup that shapes them')
        self.assertEqual(centre_find.places(page,'<b>')[0],[],'the markup itself is not words')
        self.assertIs(centre_find.subject(page),page);page.hide()

    def test_what_is_searched_is_what_the_page_names_then_its_largest_view_then_nothing(self):
        page=QWidget();box=QVBoxLayout(page);small=QPlainTextEdit('note');large=QTableWidget(2,2);box.addWidget(small);box.addWidget(large)
        page.resize(700,500);small.setFixedHeight(90);page.show();APP.processEvents()
        self.assertIs(centre_find.subject(page),large,'the largest view of writing or rows the page shows')
        page.centre_find_in=lambda:small;self.assertIs(centre_find.subject(page),small,'a page may name what is searched')
        editor=QPlainTextEdit();self.assertIs(centre_find.subject(page,editor),editor,'a text file is searched itself')
        page.hide();empty=QWidget();empty.show();APP.processEvents();self.assertIsNone(centre_find.subject(empty));empty.hide()
        self.assertIsNone(centre_find.subject(None))

    def test_a_view_on_a_tab_that_is_not_showing_is_brought_to_the_front(self):
        tabs=QTabWidget();first=QWidget();second=QPlainTextEdit('words');tabs.addTab(first,'One');tabs.addTab(second,'Two')
        self.assertIs(tabs.currentWidget(),first);centre_find.reveal(second);self.assertIs(tabs.currentWidget(),second)


class DeskLightTests(unittest.TestCase):
    def test_white_paper_comes_down_and_black_ink_stays_black_and_the_page_itself_is_untouched(self):
        page=QPixmap(8,8);page.fill(QColor('#ffffff'));p=QPainter(page);p.fillRect(0,0,4,8,QColor('#000000'));p.end()
        shown=page_light.lit(page).toImage();kept=page.toImage()
        self.assertEqual(QColor(shown.pixel(6,4)).name(),page_light.DESK_LIGHT,'white times the tone is the tone')
        self.assertEqual(QColor(shown.pixel(1,4)).name(),'#000000');self.assertEqual(QColor(kept.pixel(6,4)).name(),'#ffffff','the picture given is not changed')
        self.assertIs(page_light.lit(page,True),page,'its own light is the page as it is')
        self.assertLess(QColor(page_light.DESK_LIGHT).lightness(),150,'the tone is well below white')

    def test_the_choice_is_read_from_the_session_and_defaults_to_the_desks_light(self):
        host=type('Host',(),{})();self.assertFalse(page_light.own(host));host.session=type('S',(),{'state':{'page_own_light':True}})();self.assertTrue(page_light.own(host))


class KeptChoicesTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.path=Path(temporary.name)/'session.json'

    def write(self,**extra):
        s=Session(self.path);s.state.update(extra);s.save();return Session(self.path)

    def test_buttons_page_light_and_field_zoom_round_trip_and_nonsense_is_dropped(self):
        again=self.write(buttons='icons',page_own_light=True,field_zoom={'zoom':0.45,'whole':False})
        self.assertEqual((again.state.get('buttons'),again.state.get('page_own_light'),again.state.get('field_zoom')),('icons',True,{'zoom':0.45,'whole':False}))
        fresh=Session(self.path.with_name('fresh.json'))
        for key in ('buttons','page_own_light','field_zoom'):self.assertNotIn(key,fresh.state,key+': no default is invented by the loader')
        for bad in (dict(buttons='pictures'),dict(page_own_light='yes'),dict(field_zoom={'zoom':9,'whole':False}),dict(field_zoom={'zoom':0.5,'whole':'no'}),dict(field_zoom='far')):
            key=next(iter(bad));self.assertNotIn(key,self.write(**bad).state,repr(bad)+' is not kept')


if __name__=='__main__':
    unittest.main()
