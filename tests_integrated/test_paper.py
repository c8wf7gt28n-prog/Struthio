"""The paper vocabulary: the writing-marker setting over the Session profile (type, default, store, history, undo and restore,
invalid values, a foreign profile value, receipts, sharing and authority), the marker's own rules measured on real offscreen
widgets, and the hardware editor's pure parts. Zero jobs, workers, models, providers or natives."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import ledger_control as control,settings_registry,stacy_control,writing_marker,hardware_settings_qt
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session

KEY=settings_registry.WRITING_MARKER_KEY


class WritingMarkerSettingTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        env=patch.dict(os.environ,dict(ARC1_WORKBENCH_CONFIG_HOME=str(self.base/'profile'),ARC_LEDGER_CONCERN=str(self.base/'Concern')))
        env.start();self.addCleanup(env.stop)
        self.root=self.base/'workspace';self.root.mkdir();self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(self.base/'profile/session.json',self.root);self.s.save();control.bind(self.kernel,self.s)
        self.slate=Principal('Slate:typed',frozenset({'read','execute'}))
        launcher=patch.object(Kernel,'launch',side_effect=AssertionError('Settings cannot launch jobs'));self.launch=launcher.start();self.addCleanup(launcher.stop)

    def call(self,op,args=None,who=None):
        result=self.kernel.dispatch(op,args or {},who or self.owner);self.assertTrue(result['ok'],result);return result['result']
    def row(self,key=KEY):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)
    def set(self,value,who=None):return self.call('ledger.settings.set',dict(key=KEY,value=value,expected_revision=self.row()['revision']),who)
    def refuse(self,op,args,who=None):
        result=self.kernel.dispatch(op,args,who or self.owner);self.assertFalse(result['ok'],result);return result['error']['message']
    def on_disk(self):return json.loads(self.s.path.read_text()).get('writing_marker','ABSENT')
    def lease(self,name='test-desktop'):
        leases=self.root/'.ledger/desktops';leases.mkdir(exist_ok=True);path=leases/(name+'.json');path.write_text(json.dumps({'pid':os.getpid()}));return path

    # -- the definition ----------------------------------------------------------------
    def test_the_definition_is_a_session_boolean_set_one_key_at_a_time(self):
        spec=settings_registry.BY_KEY[KEY]
        self.assertEqual((spec['type'],spec['default'],spec['store'],spec['scope_id'],spec['application'],spec['root'],spec['group'],spec['category']),
                         ('boolean',True,'Session writing_marker','session_profile','immediate','Ledger','Appearance','Appearance'))
        self.assertEqual(spec['supported_scopes'],['session_profile']);self.assertNotIn(KEY,settings_registry.OWNER_KEYS)
        self.assertIn('Reduce motion',spec['description']);self.assertIn('Insertion, selection and keyboard editing',spec['description'])
        ids={n['id']:n for n in settings_registry.nodes()}
        self.assertEqual(ids['setting:'+KEY]['parent'],'settings:ledger:appearance')
        enum=control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum']
        self.assertNotIn(KEY,enum);self.assertEqual(sorted(enum),sorted(settings_registry.SESSION_BATCH_KEYS))  # single-key Set only
        self.assertIn(KEY,settings_registry.SESSION_KEYS);self.assertNotIn(KEY,settings_registry.SESSION_BATCH_KEYS)
        self.assertIn(str(len(settings_registry.SPECS))+' ',self.call('ledger.settings')['coverage'])  # the readback counts the live definitions
        before=self.s.path.read_bytes()
        self.refuse('ledger.settings.apply',dict(changes=[dict(key=KEY,value=False,expected_revision=self.row()['revision'])]))
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    # -- the real store ----------------------------------------------------------------
    def test_set_undo_and_default_write_the_existing_session_field_and_read_it_back(self):
        row=self.row();self.assertEqual((row['stored'],row['value'],row['effective'],row['application_state'],row['editable']),(True,True,None,'NO_LIVE_DESKTOP_READBACK',True))
        self.assertEqual(self.on_disk(),'ABSENT')  # a profile without the field is the default; nothing is migrated by reading
        first=self.set(False);self.assertIs(self.on_disk(),False);self.assertEqual((first['before'],first['after']),(True,False))
        self.assertIs(self.s.state['writing_marker'],False)
        self.assertIs(Session(self.s.path,self.root).state.get('writing_marker'),False)  # Session.load reads the field back
        self.assertIs(self.row()['stored'],False)
        history=self.call('ledger.settings.history',{'key':KEY})['changes'];self.assertTrue(history[0]['can_undo'])
        undone=self.call('ledger.settings.undo',dict(id=first['id']));self.assertEqual(undone['restores'],first['id']);self.assertIs(self.on_disk(),True)
        self.set(False);opened=self.row();self.call('ledger.settings.restore',dict(key=KEY,expected_revision=opened['revision']))
        self.assertIs(self.on_disk(),True);self.assertIs(self.row()['stored'],True)
        self.assertFalse(self.kernel.dispatch('ledger.settings.restore',dict(key=KEY,expected_revision=opened['revision']),self.owner)['ok'])
        self.assertEqual(self.kernel.listing('jobs'),[]);self.launch.assert_not_called()

    def test_a_saved_false_survives_other_settings_writes(self):
        self.set(False)
        self.call('ledger.settings.set',dict(key='reading.code_pt',value=18,expected_revision=self.row('reading.code_pt')['revision']))
        self.assertIs(self.on_disk(),False);self.assertIs(self.row()['stored'],False)
        other=Session(self.s.path,self.root);other.state['writing_marker']=True;other.save()  # another writer's choice is not resurrected
        self.call('ledger.settings.set',dict(key='reading.code_pt',value=19,expected_revision=self.row('reading.code_pt')['revision']))
        self.assertIs(self.on_disk(),True);self.assertIs(self.row()['stored'],True)

    def test_invalid_values_are_refused_without_touching_profile_or_journal(self):
        before=self.s.path.read_bytes()
        for value in (1,0,'yes','true',None,[True],{'on':True}):
            message=self.refuse('ledger.settings.set',dict(key=KEY,value=value));self.assertIn('Invalid type',message,(value,message))
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_a_foreign_value_in_the_profile_reads_as_the_default_never_as_an_error_row(self):
        data=json.loads(self.s.path.read_text());data['writing_marker']='sometimes';self.s.path.write_text(json.dumps(data));before=self.s.path.read_bytes()
        row=self.row();self.assertIs(row['stored'],True);self.assertTrue(row['editable']);self.assertEqual(row['application_state'],'NO_LIVE_DESKTOP_READBACK')
        self.assertEqual(self.s.path.read_bytes(),before)
        self.assertIs(writing_marker.enabled_in({'writing_marker':'sometimes'}),True);self.assertIs(writing_marker.enabled_in({}),True)
        self.assertIs(writing_marker.enabled_in(None),True);self.assertIs(writing_marker.enabled_in({'writing_marker':False}),False)

    # -- consumer receipts ---------------------------------------------------------------
    def test_receipts_say_applied_pending_and_how_the_mark_moves(self):
        lease=self.lease();publish=lambda values:control.publish_settings_runtime(self.kernel,'test-desktop',{KEY:values})
        publish(dict(requested=True,effective=True,motion='blinking',passages=4,period_ms=2000))
        row=self.row();self.assertEqual((row['application_state'],row['effective']),('APPLIED',True))
        self.assertIn('blinking',row['effective_source']);self.assertIn('4 opted-in passage',row['effective_source']);self.assertEqual(len(row['desktop_effects']),1)
        publish(dict(requested=True,effective=True,motion='static',passages=4,period_ms=2000))
        row=self.row();self.assertEqual(row['application_state'],'APPLIED');self.assertIn('static',row['effective_source'])  # Reduce motion stills the X; it does not pend the setting
        publish(dict(requested=True,effective=False,motion='off',passages=4))
        self.assertEqual(self.row()['application_state'],'PENDING_DESKTOP')
        self.set(False)
        publish(dict(requested=True,effective=True,motion='blinking',passages=4))
        self.assertEqual(self.row()['application_state'],'PENDING_DESKTOP')
        publish(dict(requested=False,effective=False,motion='off',passages=4))
        self.assertEqual((self.row()['application_state'],self.row()['effective']),('APPLIED',False))
        lease.unlink();self.assertEqual(self.row()['application_state'],'NO_LIVE_DESKTOP_READBACK')

    # -- sharing and authority ------------------------------------------------------------
    def test_presentation_only_choice_is_shareable_context_and_a_cloud_proposal_may_set_it(self):
        context=self.call('ledger.context');self.assertIs(context['settings'][KEY],True)
        self.assertEqual(next(r for r in context['settings_registry'] if r['key']==KEY)['scope_id'],'session_profile')
        actions=[stacy_control.call('ledger.settings.set',dict(key=KEY,value=False))]
        stacy_control.validate_actions(actions,self.slate,provider=True)
        self.assertFalse(stacy_control.cloud_private('ledger.settings.set',actions[0]['arguments']))
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',actions[0]['arguments'],Principal('reader'))['ok'])
        self.call('ledger.settings.set',actions[0]['arguments'],self.slate);self.assertIs(self.on_disk(),False)
        self.assertEqual([r['actor'] for r in self.call('ledger.settings.history',{'key':KEY})['changes']],['Slate:typed'])


class MarkerRulesTests(unittest.TestCase):
    """The marker's pure decisions: motion words, glyph size, placement that never enters the passage, frame heights."""
    def test_motion_words_reduce_motion_wins_over_the_blink(self):
        self.assertEqual(writing_marker.motion_state(True,False),'blinking');self.assertEqual(writing_marker.motion_state(True,True),'static')
        self.assertEqual(writing_marker.motion_state(False,False),'off');self.assertEqual(writing_marker.motion_state(False,True),'off')
        self.assertEqual(writing_marker.PERIOD_MS,2000)

    def test_glyph_scales_with_the_passage_font_and_never_below_seven(self):
        self.assertEqual(writing_marker.glyph_for(10),12);self.assertEqual(writing_marker.glyph_for(8),10);self.assertEqual(writing_marker.glyph_for(19),24)
        self.assertEqual(writing_marker.glyph_for(3),7)

    def test_margin_form_keeps_three_px_clear_and_the_narrow_form_shrinks_instead_of_entering_the_passage(self):
        offset,drawn,form=writing_marker.geometry(22,12);self.assertEqual((drawn,form),(12,'margin'));self.assertEqual(offset-drawn/2.0,4.0)
        offset,drawn,form=writing_marker.geometry(24,10);self.assertEqual((drawn,form),(10,'margin'))
        for room,glyph in ((22,24),(24,24),(14,12),(10,24)):
            offset,drawn,form=writing_marker.geometry(room,glyph)
            self.assertEqual(form,'narrow');self.assertLessEqual(drawn,glyph);self.assertGreaterEqual(drawn,writing_marker.MIN_GLYPH)
            self.assertGreaterEqual(offset-drawn/2.0,1.0,(room,glyph))        # right edge at least 1 px before the passage
            self.assertGreaterEqual(room-(offset+drawn/2.0),0.0,(room,glyph)) # left edge not beyond the page edge

    def test_accepts_only_typed_passages_and_refuses_the_source_editor(self):
        self.assertFalse(writing_marker.accepts(None));self.assertFalse(writing_marker.accepts(object()))

    def test_hardware_frame_height_follows_content_up_to_the_cap(self):
        self.assertEqual(hardware_settings_qt.frame_height(120,320),120);self.assertEqual(hardware_settings_qt.frame_height(3646,320),320)
        self.assertEqual(hardware_settings_qt.frame_height(3646,640),640);self.assertEqual(hardware_settings_qt.frame_height(0,320),0)
        self.assertEqual(hardware_settings_qt.FRAME_CAP_PX,320);self.assertEqual(hardware_settings_qt.ROW_MAX_PX,720)
        self.assertEqual(hardware_settings_qt.view_summary({}),'All panes Auto view')


class MarkerWidgetTests(unittest.TestCase):
    """Real offscreen widgets on a page with a 22 px margin: what the X does, measured in pixels and in the accessible tree."""
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([]);cls.app.setCursorFlashTime(0)

    def setUp(self):
        from types import SimpleNamespace
        from PySide6.QtWidgets import QWidget,QVBoxLayout,QPlainTextEdit,QLineEdit,QLabel
        self.host=SimpleNamespace(reading_profile={'reduce_motion':False,'ui_pt':14.0},session=SimpleNamespace(state={}))
        self.page=QWidget();self.page.setStyleSheet('QWidget {background:#f6f3eb;} QPlainTextEdit,QLineEdit {background:#f8edc9;border:0;padding:8px;}')
        box=QVBoxLayout(self.page);box.setContentsMargins(22,18,22,18);box.setSpacing(12);box.addWidget(QLabel('A record'))
        self.title=QLineEdit();self.title.setObjectName('CabinetWriting');box.addWidget(self.title)
        self.writing=QPlainTextEdit();self.writing.setObjectName('CabinetWriting');self.writing.setMaximumHeight(140);box.addWidget(self.writing)
        self.page.resize(600,320);self.page.show();self.pump()
        focused=self.app.focusWidget()  # a shown window gives its first field focus; the tests decide focus themselves
        if focused is not None:focused.clearFocus()
        self.pump();self.controller=writing_marker.install(self.host);self.addCleanup(self.page.close)

    def pump(self):
        for _ in range(3):self.app.processEvents()

    def ink(self,rect):
        image=self.page.grab().toImage();count=0
        for y in range(rect.top(),rect.bottom()+1):
            for x in range(rect.left(),rect.right()+1):
                c=image.pixelColor(x,y)
                if (c.red()+c.green()+c.blue())/3<150:count+=1
        return count

    def children(self,widget):
        from PySide6.QtGui import QAccessible
        iface=QAccessible.queryAccessibleInterface(widget);return iface.childCount() if iface else None

    def focus(self,widget):
        widget.setFocus();self.pump();self.assertTrue(widget.hasFocus())

    def test_attach_adds_nothing_to_the_accessible_tree_and_marks_only_the_focused_passage(self):
        before=self.children(self.page)
        title_mark=self.controller.attach(self.title);mark=self.controller.attach(self.writing)
        self.assertEqual(self.children(self.page),before);self.assertIs(self.controller.attach(self.writing),mark)
        self.assertTrue(self.writing.property('writingMark'));self.assertFalse(self.controller.timer.isActive())
        self.focus(self.writing);self.writing.setPlainText('Keep the work visible\nwhile we choose its next instrument.')
        from PySide6.QtGui import QTextCursor
        cursor=QTextCursor(self.writing.document());cursor.movePosition(QTextCursor.End);self.writing.setTextCursor(cursor);self.pump()
        self.assertTrue(self.controller.timer.isActive());self.assertEqual(self.controller.timer.interval(),1000)
        self.controller.set_phase(True);self.pump();rect=mark.mark_rect()
        self.assertIs(mark.page,self.page);self.assertEqual(mark.form,'margin');self.assertLess(rect.right(),self.writing.x())  # in the margin, never on the passage
        shown=self.ink(rect);self.controller.set_phase(False);self.pump();hidden=self.ink(rect)
        self.assertGreater(shown,20);self.assertEqual(hidden,0)
        passage=self.page.grab().toImage().copy(self.writing.geometry());self.controller.set_phase(True);self.pump()
        self.assertEqual(self.page.grab().toImage().copy(self.writing.geometry()),passage)  # the passage is pixel-identical in both phases
        # the X follows the caret's line, and the focused passage alone carries it
        cursor.movePosition(QTextCursor.Start);self.writing.setTextCursor(cursor);self.pump();line1=mark.mark_rect()
        self.assertLess(line1.center().y(),rect.center().y());self.assertGreater(self.ink(line1),20);self.assertEqual(self.ink(rect),0)
        self.focus(self.title);self.controller.set_phase(True);self.pump()
        self.assertFalse(mark.visible());self.assertTrue(title_mark.visible());self.assertGreater(self.ink(title_mark.mark_rect()),10);self.assertEqual(self.ink(line1),0)
        self.title.clearFocus();self.pump();self.assertIsNone(self.controller.focused());self.assertFalse(self.controller.timer.isActive())
        self.assertEqual(self.ink(title_mark.mark_rect()),0)

    def test_reduce_motion_is_static_with_no_timer_and_the_setting_hides_the_mark(self):
        mark=self.controller.attach(self.writing);self.focus(self.writing);self.writing.setPlainText('one line');self.pump()
        self.assertTrue(self.controller.timer.isActive())
        self.host.reading_profile['reduce_motion']=True;self.controller.motion_changed();self.pump()
        self.assertFalse(self.controller.timer.isActive());self.assertTrue(self.controller.on);self.assertTrue(mark.visible())
        paints=self.controller.stats()['page_paints']
        for _ in range(8):self.controller.tick();self.pump()
        self.assertTrue(self.controller.on);self.assertEqual(self.controller.stats()['page_paints'],paints)  # static: eight ticks, no repaint
        self.assertEqual(self.controller.readback()['motion'],'static')
        self.host.reading_profile['reduce_motion']=False;self.controller.motion_changed();self.assertTrue(self.controller.timer.isActive())
        self.controller.set_phase(True);self.pump();rect=mark.mark_rect();self.assertGreater(self.ink(rect),20)
        self.controller.set_enabled(False);self.pump()
        self.assertFalse(mark.visible());self.assertEqual(self.ink(rect),0);self.assertFalse(self.controller.timer.isActive())
        self.assertEqual(self.controller.readback(),dict(requested=True,effective=False,motion='off',passages=1,period_ms=2000))
        self.controller.set_enabled(True);self.controller.set_phase(True);self.pump();self.assertGreater(self.ink(rect),20)

    def test_hidden_when_the_caret_line_is_scrolled_out_and_detach_restores_everything(self):
        from PySide6.QtGui import QTextCursor
        mark=self.controller.attach(self.writing);self.focus(self.writing)
        self.writing.setPlainText('\n'.join('line %d'%i for i in range(1,30)))
        cursor=QTextCursor(self.writing.document());cursor.movePosition(QTextCursor.End);self.writing.setTextCursor(cursor);self.pump()
        self.assertFalse(mark.mark_rect().isNull())
        self.writing.verticalScrollBar().setValue(0);self.pump();self.assertTrue(mark.mark_rect().isNull())  # nothing in view to point at
        self.writing.verticalScrollBar().setValue(self.writing.verticalScrollBar().maximum());self.pump();self.assertFalse(mark.mark_rect().isNull())
        text=self.writing.toPlainText();revision=self.writing.document().revision()
        self.controller.detach(self.writing);self.pump()
        self.assertIsNone(self.writing.property('writingMark'));self.assertIsNone(self.controller.mark_for(self.writing))
        self.assertEqual((self.writing.toPlainText(),self.writing.document().revision()),(text,revision));self.assertEqual(self.writing.viewportMargins().left(),0)

    def test_source_editor_is_refused_and_a_narrow_margin_shrinks_the_x_instead_of_entering_the_passage(self):
        from PySide6.QtWidgets import QPlainTextEdit
        from PySide6.QtGui import QFont
        code=QPlainTextEdit(self.page);code.setObjectName('sourceEditor');self.assertIsNone(self.controller.attach(code))
        big=QFont(self.writing.font());big.setPointSizeF(28.0);self.writing.setFont(big);self.pump()
        mark=self.controller.attach(self.writing);self.focus(self.writing);self.writing.setPlainText('large');self.pump();self.controller.set_phase(True);self.pump()
        self.assertGreater(mark.glyph()+8,22)  # the strip no longer fits the 22 px margin
        rect=mark.mark_rect();self.assertEqual(mark.form,'narrow');self.assertTrue(mark.clamped)
        self.assertLess(rect.right()-2,self.writing.x());self.assertGreater(self.ink(rect),10)

    def test_the_page_is_never_an_ancestor_whose_margin_a_sibling_covers_nor_outside_the_scrolling_page(self):
        """A desk: a 200 px column beside a scroll area whose page has a 22 px margin; at 28 pt the strip (36 px) does not fit the
        page margin, and the X must still be drawn on that page (narrow form), never on the outer widget under the column."""
        from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QLabel,QScrollArea,QPlainTextEdit
        from PySide6.QtGui import QFont
        desk=QWidget();row=QHBoxLayout(desk);row.setContentsMargins(0,0,0,0);row.setSpacing(0)
        column=QLabel('cabinet');column.setFixedWidth(200);column.setStyleSheet('background:#eee9df');row.addWidget(column)
        scroll=QScrollArea();scroll.setWidgetResizable(True);row.addWidget(scroll,1)
        page=QWidget();box=QVBoxLayout(page);box.setContentsMargins(22,18,22,18);scroll.setWidget(page)
        box.addWidget(QLabel('heading'));writing=QPlainTextEdit();writing.setObjectName('CabinetWriting');writing.setMaximumHeight(140);box.addWidget(writing);box.addStretch(1)
        big=QFont(writing.font());big.setPointSizeF(28.0);writing.setFont(big)
        desk.resize(700,320);desk.show();self.pump();self.addCleanup(desk.close)
        mark=self.controller.attach(writing);writing.setFocus();self.pump();writing.setPlainText('large');self.pump();self.controller.set_phase(True);self.pump()
        self.assertIs(mark.page,page);self.assertEqual(mark.form,'narrow');rect=mark.mark_rect()
        self.assertLess(rect.right(),writing.x());self.assertGreaterEqual(rect.left(),0)
        self.assertFalse(writing_marker.MarginMark.free_margin(desk,scroll,36))  # the column covers what would be the outer margin
        image=page.grab().toImage();dark=sum(1 for y in range(rect.top(),rect.bottom()+1) for x in range(rect.left(),rect.right()+1)
                                             if (image.pixelColor(x,y).red()+image.pixelColor(x,y).green()+image.pixelColor(x,y).blue())/3<150)
        self.assertGreater(dark,10)


if __name__=='__main__':unittest.main()
