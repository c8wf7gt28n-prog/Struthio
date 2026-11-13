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
        drawn_for=set(glyph_set.GLYPHS)|set(glyph_set.KIND)
        self.assertEqual(sorted(set(tool_faces.FOR_MENU.values())-drawn_for),[],'a menu line names a glyph nobody drew')

    def test_a_menu_line_is_looked_up_without_its_mnemonic_its_key_or_its_dots(self):
        self.assertEqual([tool_faces.named(w) for w in ('&Undo','Find…\tCtrl+F','New &File…','Pin / Unpin workspace\tCtrl+Shift+K')],['Undo','Find','New File','Pin / Unpin workspace'])

    def test_a_menu_line_shows_its_words_and_never_its_key(self):
        from PySide6.QtGui import QKeySequence
        from PySide6.QtWidgets import QMenu
        menu=QMenu();save=menu.addAction('&Save');save.setShortcut(QKeySequence('Ctrl+S'));idea=menu.addAction('New Idea…\tCtrl+Shift+N')
        tool_faces.dress(menu)
        self.assertFalse(save.isShortcutVisibleInContextMenu());self.assertEqual(save.shortcut().toString(),'Ctrl+S','the key still works; it is not printed')
        self.assertEqual(idea.text(),'New Idea…','a key written into a line after a tab is taken out of it')
        self.assertEqual(save.text(),'Save','and no letter is underlined');both=menu.addAction('Find && Replace');tool_faces.dress(menu);self.assertEqual(both.text(),'Find && Replace','a real ampersand stays')

    def test_a_menu_wears_glyphs_only_with_icons_chosen_and_gives_back_what_it_had(self):
        from PySide6.QtWidgets import QMenu
        menu=QMenu();undo=menu.addAction('&Undo');other=menu.addAction('Something with no glyph');menu.addSeparator()
        self.addCleanup(lambda:tool_faces.STATE.update(mode='words'))
        tool_faces.STATE['mode']='words';tool_faces.dress(menu);self.assertTrue(undo.icon().isNull())
        tool_faces.STATE['mode']='icons';tool_faces.dress(menu)
        self.assertFalse(undo.icon().isNull());self.assertTrue(undo.isIconVisibleInMenu());self.assertTrue(other.icon().isNull())
        self.assertEqual(undo.text(),'Undo','its words, without the mark for an underlined letter (0.5.2)')
        tool_faces.STATE['mode']='words';tool_faces.dress(menu);self.assertTrue(undo.icon().isNull(),'with words chosen the line is as it was')


class ToolFaceTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda:tool_faces.STATE.update(mode='words'));tool_faces.STATE['mode']='words'
        self.host=QWidget();self.row=QVBoxLayout(self.host)

    def button(self,words):
        b=QPushButton(words);self.row.addWidget(b);return tool_faces.wear(b)

    def test_outside_a_window_a_button_is_its_words_and_is_left_alone(self):
        b=self.button('Copy citation');self.assertEqual(tool_faces.mode(),'words')
        self.assertEqual((b.minimumWidth(),b.maximumWidth()),(0,tool_faces.WIDEST));self.assertFalse(b.property('facedWidths'))

    def test_a_workspace_that_never_chose_opens_with_icons_and_a_choice_is_kept(self):
        host=type('Host',(),{})();host.session=type('S',(),{'state':{}})()
        tool_faces.start(host);self.assertEqual(tool_faces.mode(),'icons','0.5: the look first; words are one choice away')
        host.session.state['buttons']='words';tool_faces.start(host);self.assertEqual(tool_faces.mode(),'words')
        host.session.state['buttons']='nonsense';tool_faces.start(host);self.assertEqual(tool_faces.mode(),tool_faces.OPENS_WITH)

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
        again=self.write(buttons='icons',page_own_light=True,field_zoom={'zoom':0.45,'whole':False},glow='neon',type_target='web')
        self.assertEqual(again.state.get('type_target'),'web','the line remembers that Web was the one typed to')
        self.assertEqual((again.state.get('buttons'),again.state.get('page_own_light'),again.state.get('field_zoom'),again.state.get('glow')),('icons',True,{'zoom':0.45,'whole':False},'neon'))
        fresh=Session(self.path.with_name('fresh.json'))
        for key in ('buttons','page_own_light','field_zoom','glow'):self.assertNotIn(key,fresh.state,key+': no default is invented by the loader')
        for bad in (dict(buttons='pictures'),dict(page_own_light='yes'),dict(field_zoom={'zoom':9,'whole':False}),dict(field_zoom={'zoom':0.5,'whole':'no'}),dict(field_zoom='far'),dict(glow='blinding')):
            key=next(iter(bad));self.assertNotIn(key,self.write(**bad).state,repr(bad)+' is not kept')


class EqualizerTests(unittest.TestCase):
    """The head's equalizer shows what is so: each bar one processor thread's work between two readings."""
    STAT=('cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0 0 0\ncpu1 50 0 50 400 0 0 0 0 0 0\nintr 5\n',
          'cpu  300 0 100 900 0 0 0 0 0 0\ncpu0 150 0 50 400 0 0 0 0 0 0\ncpu1 50 0 50 500 0 0 0 0 0 0\nintr 9\n')

    def test_a_thread_that_worked_the_whole_second_is_full_and_one_that_idled_is_empty(self):
        from workbench import equalizer_qt as eq
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);first,second=Path(folder.name)/'a',Path(folder.name)/'b'
        first.write_text(self.STAT[0]);second.write_text(self.STAT[1])
        before,now=eq.readings(str(first)),eq.readings(str(second))
        self.assertEqual(sorted(before),[0,1],'the line for all threads together is not a bar')
        self.assertEqual(eq.loads(before,now),[1.0,0.0]);self.assertEqual(eq.loads({},now),[0.0,0.0],'no earlier reading: nothing is claimed')
        self.assertEqual(eq.readings(str(Path(folder.name)/'absent')),{},'where it cannot be read there are no bars, and no error')

    def test_more_threads_than_bars_are_shown_in_equal_groups(self):
        from workbench import equalizer_qt as eq
        self.assertEqual(eq.grouped([0.5]*4),[0.5]*4);self.assertEqual(len(eq.grouped([0.0]*8)),8)
        pairs=eq.grouped([1.0,0.0]*8);self.assertEqual(pairs,[0.5]*8,'sixteen threads, as on the ThinkPad: eight bars, each the mean of two')
        self.assertEqual(eq.grouped([1.0,0.0,0.0,0.0]*8),[0.25]*8,'thirty-two threads: eight bars, each the mean of four')

    def test_a_rate_is_drawn_on_one_fixed_scale(self):
        from workbench import equalizer_qt as eq
        floor,ceiling=eq.SCALES['disk']
        self.assertEqual(eq.scaled(0,floor,ceiling),0.0);self.assertEqual(eq.scaled(floor,floor,ceiling),0.0,'at the floor a bar rests');self.assertEqual(eq.scaled(None,floor,ceiling),0.0)
        self.assertEqual(eq.scaled(ceiling*4,floor,ceiling),1.0);self.assertAlmostEqual(eq.scaled((floor*ceiling)**0.5,floor,ceiling),0.5,places=6)
        self.assertLess(eq.scaled(1e6,floor,ceiling),eq.scaled(1e7,floor,ceiling));self.assertEqual(eq.amount(12.4e6),'12 MB/s');self.assertEqual(eq.amount(1500),'1.5 kB/s')

    def test_everything_that_moves_is_read_twice_and_compared(self):
        """Processor, kernel, memory, disks, network and graphics from this computer's own counters, one second apart."""
        from workbench import equalizer_qt as eq
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name);card=root/'drm'/'card0'/'device';card.mkdir(parents=True)
        def write(stat,vm,disk,net,busy):
            (root/'stat').write_text(stat);(root/'meminfo').write_text('MemTotal:       1000 kB\nMemFree:  100 kB\nMemAvailable:    250 kB\n');(root/'vmstat').write_text(vm)
            (root/'diskstats').write_text(disk);(root/'netdev').write_text(net);(card/'gpu_busy_percent').write_text(busy)
            (card/'mem_info_vram_used').write_text('100\n');(card/'mem_info_vram_total').write_text('400\n')
        net='Inter-|   Receive |  Transmit\n face |bytes packets|bytes packets\n    lo: 999 1 0 0 0 0 0 0 999 1 0 0 0 0 0 0\n  eth0: %d 1 0 0 0 0 0 0 %d 1 0 0 0 0 0 0\n'
        disk='   7 0 loop0 9 9 9999 9 9 9 9999 9 0 0 0\n 259 0 nvme0n1 10 0 %d 0 10 0 %d 0 0 0 0\n 259 1 nvme0n1p1 10 0 %d 0 10 0 %d 0 0 0 0\n'
        ticks=[10.0];activity=eq.Activity(stat=str(root/'stat'),meminfo=str(root/'meminfo'),vmstat=str(root/'vmstat'),diskstats=str(root/'diskstats'),netdev=str(root/'netdev'),
                                          drm=str(root/'drm'),clock=lambda:ticks[0])
        write('cpu  100 0 100 800 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0\ncpu1 50 0 50 400 0 0 0 0\nintr 1000 5\nctxt 2000\n','pgpgin 0\npgpgout 0\n',disk%(0,0,0,0),net%(0,0),'10\n')
        first=activity.sample();self.assertEqual(first['bars']['CPU'],[0.0,0.0],'the first reading has nothing to compare with: every rate rests')
        self.assertEqual(first['bars']['SSD'],[0.0,0.0]);self.assertAlmostEqual(first['bars']['RAM'][0],0.75);self.assertEqual(first['bars']['GPU'],[0.1,0.25]);self.assertEqual(first['missing'],[])
        ticks[0]=11.0
        write('cpu  200 0 200 800 0 0 0 0\ncpu0 150 0 50 400 0 0 0 0\ncpu1 50 0 150 400 0 0 0 0\nintr 101000 5\nctxt 202000\n','pgpgin 0\npgpgout 0\n',
              disk%(2*500000000//512,0,7,7),net%(100000000,0),'80\n')
        second=activity.sample()
        self.assertEqual(second['bars']['CPU'],[1.0,1.0]);self.assertAlmostEqual(second['bars']['KRN'][0],0.5,msg='half of the time that passed was the kernel’s')
        self.assertEqual(second['bars']['KRN'][1],1.0,'two hundred thousand switches a second is the top of its scale')
        self.assertEqual(second['bars']['SSD'],[1.0,0.0],'a gigabyte read in the second, nothing written; the partition is not counted twice and the loop device not at all')
        self.assertEqual(second['bars']['NET'],[1.0,0.0],'the loopback is not the network');self.assertEqual(second['bars']['GPU'][0],0.8)
        self.assertIn('reading',second['words']['SSD']);self.assertIn('80% busy',second['words']['GPU']);self.assertIn('75% in use',second['words']['RAM'])

    def test_a_source_this_computer_does_not_have_rests_and_is_named(self):
        from workbench import equalizer_qt as eq
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name);absent=str(root/'absent')
        got=eq.Activity(stat=absent,meminfo=absent,vmstat=absent,diskstats=absent,netdev=absent,drm=absent,clock=lambda:0.0).sample()
        self.assertEqual(sorted(got['missing']),sorted(eq.GROUPS));self.assertTrue(all(value==0.0 for group in eq.GROUPS for value in got['bars'][group]))
        self.assertEqual([len(got['bars'][group]) for group in eq.GROUPS],[1,2,2,2,2,2],'the picture keeps its shape')
        self.assertIn('reports nothing',got['words']['GPU'])


class DoorTests(unittest.TestCase):
    """0.7.0: the System menu is gone from the head; each of its things has one new door."""

    def test_every_meter_is_a_door_and_says_what_it_opens(self):
        from workbench import meter_cards
        from workbench.desktop_header_qt import DesktopMonitors
        self.assertEqual(tuple(meter_cards.DOORS),DesktopMonitors.KEYS);self.assertEqual(tuple(meter_cards.CARDS),DesktopMonitors.KEYS)
        self.assertTrue(all(words and words[0].isupper() for words in meter_cards.DOORS.values()))

    def test_leaving_is_the_last_group_of_the_first_menu(self):
        from workbench import menus2, session_power
        self.assertEqual(menus2.FILE[-2:],[None,'@leave'],'a separator, then leaving');self.assertEqual(menus2.DISPLAY_TITLES['File'],'Work')
        self.assertEqual([session_power.WORDS[k] for k in ('logout','restart','shutdown')],['Log out','Restart','Shut down'])


class GlowDialTests(unittest.TestCase):
    def test_the_dial_opens_on_neon_and_follows_the_session(self):
        from workbench import boss_qt
        self.addCleanup(lambda:boss_theme.GLOW.__setitem__(0,dict((k,v) for k,_,v in boss_theme.GLOW_LEVELS)[boss_theme.GLOW_OPENS]))
        levels=dict((k,v) for k,_,v in boss_theme.GLOW_LEVELS);self.assertEqual(boss_theme.GLOW_OPENS,'neon','0.5.2: the owner, having seen the three, likes Neon')
        self.assertLess(levels['soft'],levels['bright']);self.assertLess(levels['bright'],levels['neon']);self.assertEqual(levels['soft'],1.0,'Soft is what 0.5.0 had')
        host=type('Host',(),{})();host.session=type('S',(),{'state':{}})()
        self.assertEqual(boss_qt.set_glow(host),levels['neon']);self.assertEqual(boss_theme.glow(),levels['neon'])
        host.session.state['glow']='soft';self.assertEqual(boss_qt.set_glow(host),levels['soft'])
        host.session.state['glow']='nonsense';self.assertEqual(boss_qt.set_glow(host),levels['neon'])
        self.assertEqual(boss_qt.set_glow(object()),levels['neon'],'a host with no session gets what the desk opens with')


if __name__=='__main__':
    unittest.main()
