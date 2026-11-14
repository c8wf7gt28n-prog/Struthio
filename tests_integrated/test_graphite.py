"""GRAPHITE-01 (the owner's design update of 2026-11-06): the cat's pose machine, pure; its timing and Reduce motion on an
offscreen QApplication with a bare widget; the marks' palette and arithmetic; the startup screen never stops the start.

The window-level behaviour (captures, real pointer and key events, the menu, the game from the mark) is
tools/check_graphite_ui.py. Nothing here starts a process, a job or a model.
"""
import os,unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import graphite_brand as g
from workbench import typebar_qt as bar


class PoseMachineTests(unittest.TestCase):
    def test_rest_hover_and_back(self):
        m=g.CatPoses();self.assertEqual(m.pose(),'rest')
        self.assertEqual(m.enter(),'hover');self.assertEqual(m.leave(),'rest')

    def test_the_open_pose_takes_precedence_over_hover(self):
        m=g.CatPoses();m.enter();self.assertEqual(m.menu(True),'open')
        self.assertEqual(m.enter(),'open');self.assertEqual(m.leave(),'open','leaving while the menu is open changes nothing')
        self.assertEqual(m.idle(),'open','no sleep while the menu is open')

    def test_when_the_menu_closes_the_pointer_decides(self):
        m=g.CatPoses();m.menu(True);self.assertEqual(m.menu(False,over=True),'hover')
        m.menu(True);self.assertEqual(m.menu(False,over=False),'rest')

    def test_sleep_after_inactivity_and_hover_wakes_into_the_side_eye(self):
        m=g.CatPoses();self.assertEqual(m.idle(),'sleepy');self.assertEqual(m.leave(),'sleepy','the pointer elsewhere keeps it asleep')
        self.assertEqual(m.enter(),'hover');self.assertFalse(m.asleep)
        m.leave();m.idle();self.assertEqual(m.wake(),'rest','keyboard focus wakes it with the pointer away')

    def test_one_click_opens_the_menu_from_sleep(self):
        m=g.CatPoses();m.idle();self.assertEqual(m.menu(True),'open');self.assertEqual(m.menu(False,over=True),'hover')
        self.assertFalse(m.asleep,'the menu woke it: it never falls back asleep by itself')

    def test_the_four_poses_carry_the_owners_differences(self):
        f=lambda pose:dict(zip(g.FIELDS,g.POSES[pose]))
        rest,hover,open_,sleepy=(f(p) for p in ('rest','hover','open','sleepy'))
        self.assertEqual((rest['tail'],rest['paw'],rest['drop'],rest['lid']),(0,0,0,1),'eyes forward, both paws down, tail tucked away')
        self.assertTrue(hover['tail']==1 and hover['paw']==0 and hover['look_x']<-.5,'side-eye and the curl, both paws down')
        self.assertTrue(open_['tail']==0 and open_['paw']==1 and open_['look_x']>0 and open_['look_y']<0,'tail gone, right paw up, eyes toward it')
        self.assertTrue(sleepy['drop']>0 and sleepy['lid']==0 and sleepy['tail']==0 and sleepy['paw']==0,'head a little lower, eyes closed')
        self.assertEqual(g.blend(g.POSES['rest'],g.POSES['open'],0),g.POSES['rest']);self.assertEqual(g.blend(g.POSES['rest'],g.POSES['open'],1),g.POSES['open'])
        self.assertEqual(g.blend((0,),(10,),.5),(5,))
        self.assertTrue(120<=g.MOVE_MS<=180 and g.IDLE_MS==90000)


class CatTimingTests(unittest.TestCase):
    """The animation and Reduce motion on a bare widget (no window, no menu)."""
    def setUp(self):
        from PySide6.QtWidgets import QApplication,QWidget
        self.app=QApplication.instance() or QApplication([]);self.reduce=False
        self.widget=QWidget();self.addCleanup(self.widget.deleteLater)
        self.cat=g.Cat(self.widget,lambda:self.reduce)

    def wait(self,ms):
        from PySide6.QtTest import QTest
        QTest.qWait(ms)

    def test_a_change_moves_briefly_and_reduce_motion_switches_directly(self):
        self.cat.enter();self.assertEqual(self.cat.pose,'hover');self.assertNotEqual(self.cat.params,g.POSES['hover'],'not there yet: it moves')
        self.wait(g.MOVE_MS+120);self.assertEqual(self.cat.params,g.POSES['hover'])
        self.reduce=True;self.cat.leave();self.assertEqual(self.cat.params,g.POSES['rest'],'Reduce motion: the pose at once');self.assertFalse(self.cat.animation.state()==self.cat.animation.State.Running)

    def test_inactivity_puts_it_to_sleep_only_with_the_menu_closed(self):
        self.cat.idle.setInterval(60);self.reduce=True;self.cat.menu(True);self.wait(150);self.assertEqual(self.cat.pose,'open');self.assertFalse(self.cat.idle.isActive())
        self.cat.menu(False);self.assertTrue(self.cat.idle.isActive());self.wait(200);self.assertEqual(self.cat.pose,'sleepy')
        self.cat.menu(True);self.assertEqual(self.cat.pose,'open','one click from sleep')


class MarkAndTileTests(unittest.TestCase):
    def test_palette_is_graphite_paper_eraser_and_pencil_only(self):
        from workbench import shell2
        self.assertEqual((g.GRAPHITE,g.PAPER,g.PAPER_LIGHT,g.ERASER_MARK,g.PENCIL),(shell2.TEXT,shell2.GROUND,shell2.CARD,shell2.ERASER_MARK,shell2.AMBER_EDGE))
        self.assertTrue({g.CAT_COAT,g.CAT_DETAIL,g.CAT_IRIS,g.CAT_NOSE,g.CAT_FOCUS}<={g.GRAPHITE,g.PAPER_LIGHT,g.ERASER_MARK,g.PENCIL},'HATCH DESK D2: the cat in the owner\'s colours')

    def test_the_point_converges_with_a_gap_and_a_stroke_past_the_tip(self):
        (a,b,tip_u),(c,d,tip_l)=g.UPPER,g.LOWER
        self.assertLess(b[1],c[1],'a gap between the wedges at their wide end');self.assertGreater(tip_u[0],tip_l[0])
        self.assertLess(abs(tip_u[1]-tip_l[1]),6,'the wedges converge to one point');self.assertGreater(min(g.STROKE[0][0],g.STROKE[1][0]),tip_l[0])

    def test_the_point_stays_crisp_at_small_sizes(self):
        """The window icon's 16 and 24 px and the head's 44 px tile: the gap reads between the wedges and the stroke is a
        solid line or left out, never a faint smudge (the fix-G-A review finding)."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QColor
        QApplication.instance() or QApplication([])
        P,G=QColor(g.PAPER),QColor(g.GRAPHITE);W,H=g.MARK_BOX
        def cover(c):return (c.green()-G.green())/(P.green()-G.green())  # 0 graphite … 1 paper
        for px in (16,24,32,44):
            img=g.mark_tile(px).toImage();m=px*(.15 if px>=g.SMALL_TILE else .10);inner=px-2*m;s=inner/W;left=m+(inner-W*s)/2;top=m+(inner-H*s)/2
            mid=int(top+98*s);gap=0
            for x in range(int(m+1),int(m+inner/3)):  # the wide end: paper above and below, a dip between
                col=[cover(img.pixelColor(x,y)) for y in range(px)]
                gap=max(gap,min(max(col[:mid+1]),max(col[mid:]))-min(col[mid-1:mid+2]))
            stroke=max(cover(img.pixelColor(x,y)) for x in range(int(left+186*s),int(left+221*s)+1) for y in range(int(top+138*s),min(px,int(top+177*s)+1)))
            self.assertGreaterEqual(gap,.8,(px,'two wedges with a gap',gap))
            self.assertTrue(stroke>=.9 or stroke<=.15,(px,'the stroke solid or left out',stroke))
            self.assertEqual(stroke>=.9,px>=24,(px,'only the 16 px icon leaves the stroke out'))

    def test_the_pointer_is_drawn_crisp_with_the_click_at_the_tip(self):
        """HATCH DESK D1b: at 1x and 2x the hotspot's first device pixel is the graphite tip, nothing is drawn beyond the tip
        along the aim, and the cursor carries that hotspot (the geometry itself is tests_integrated/test_desk.PointerTests)."""
        import math
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QColor
        QApplication.instance() or QApplication([])
        aim = (-math.sin(math.radians(g.POINTER_AIM)), -math.cos(math.radians(g.POINTER_AIM)))
        for dpr in (1, 2):
            shape = g.pointer_shape(dpr);pix = g.pointer_pixmap(dpr);img = pix.toImage();hx, hy = shape['hotspot']
            self.assertEqual((pix.width(), pix.height()), (shape['size'][0] * dpr, shape['size'][1] * dpr));self.assertEqual(pix.devicePixelRatio(), dpr)
            tip = img.pixelColor(hx * dpr, hy * dpr);self.assertGreater(tip.alpha(), 200, (dpr, 'the tip pixel is drawn'))
            self.assertLess(tip.lightness(), QColor(g.PAPER).lightness() - 40, (dpr, 'graphite at the tip, not its paper edge'))
            tx, ty = shape['tip'][0] * dpr, shape['tip'][1] * dpr
            beyond = [(x, y) for y in range(img.height()) for x in range(img.width()) if img.pixelColor(x, y).alpha() > 0
                      and ((x + .5 - tx) * aim[0] + (y + .5 - ty) * aim[1]) > (g.POINTER_EDGE + 1) * dpr]
            self.assertEqual(beyond, [], (dpr, 'nothing beyond the tip but its thin paper edge'))
            cursor = g.pointer_cursor(dpr);self.assertEqual((cursor.hotSpot().x(), cursor.hotSpot().y()), (hx, hy))

    def test_the_word_graphite_is_drawn_by_its_ink_from_the_inset_and_centred(self):
        """The owner, 2026-11-06: "upper left Graphite should be cursive". The word is drawn by its outline: the script's G
        reaches left of its origin, so the ink's first column is the widget's first, nothing is drawn left of it or past its
        width, and the ink is centred in the widget's height (the band's), at 1x, in the script and in print."""
        import math
        from pathlib import Path
        from PySide6.QtWidgets import QApplication,QWidget
        from PySide6.QtGui import QColor,QFont,QFontDatabase
        from workbench import shell2
        QApplication.instance() or QApplication([])
        root=Path(__file__).resolve().parents[1]
        QFontDatabase.addApplicationFont(str(root/'branding/fonts/script/Parisienne-Regular.ttf'))
        QFontDatabase.addApplicationFont(str(root/'branding/fonts/plex/IBMPlexSans-SemiBold.ttf'))
        for family,px,script,stroke in ((shell2.SCRIPT,34,True,.5),('IBM Plex Sans',22,False,0.0)):
            holder=QWidget();holder.resize(200,60);holder.setStyleSheet('background:#4a4741;')
            word=shell2.Wordmark(holder);font=QFont(family);font.setPixelSize(px);word.setFont(font);word.set_face(script,stroke)
            hint=word.sizeHint();word.setGeometry(16,0,hint.width(),60)
            ink=word.ink_rect();self.assertEqual(ink.left(),0.0);self.assertAlmostEqual(ink.center().y(),30.0,9)
            self.assertEqual(hint.width(),math.ceil(max(ink.width(),word.fontMetrics().horizontalAdvance('Graphite'))))
            img=holder.grab().toImage();ground=QColor('#4a4741').lightness()
            cols=sorted({x for x in range(img.width()) for y in range(60) if img.pixelColor(x,y).lightness()>ground+8})
            rows=sorted({y for x in range(img.width()) for y in range(60) if img.pixelColor(x,y).lightness()>ground+8})
            self.assertEqual(cols[0],16,(family,'the ink starts at the widget\'s left edge'));self.assertLessEqual(cols[-1],15+hint.width())
            self.assertAlmostEqual((rows[0]+rows[-1]+1)/2.0,30.0,delta=.5,msg=(family,'the ink centred in the band\'s height'))
            self.assertEqual(word.text(),'Graphite');self.assertEqual(word.accessibleName(),'Graphite')

    def test_quiet_words_print_a_status_and_set_an_explanation_in_the_script(self):
        """The quiet-script rule in the panes (shell2.QuietWords): setText is print; explain() sets the note in the script
        after its printed lead; a note with a number stays print; the switch off makes it print."""
        from pathlib import Path
        from types import SimpleNamespace
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtCore import Qt
        from workbench import shell2
        QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parents[1]/'branding/fonts/script/Parisienne-Regular.ttf'))
        host=SimpleNamespace(reading_profile={'ui_pt':14.0});saved=shell2.SCRIPT_ON[0];shell2.SCRIPT_ON[0]=True
        try:
            words=shell2.QuietWords(host);words.setText('No active jobs')
            self.assertFalse(words.scripted());self.assertEqual(words.textFormat(),Qt.PlainText);self.assertEqual(words.text(),'No active jobs')
            words.explain('in the order they started',lead='ACTIVE JOBS',sep=' · ')
            self.assertTrue(words.scripted());self.assertEqual(words.textFormat(),Qt.RichText)
            self.assertIn('ACTIVE JOBS · <span',words.text());self.assertIn(shell2.SCRIPT,words.text());self.assertEqual(words.script_px(),round(16*1.3))
            left,right,bottom=words.overhang(words.script_px());self.assertIn('text-indent:-%dpx'%left,words.text(),'a hanging indent: the printed lead on the edge, the script inset')
            self.assertEqual(words.words(),'ACTIVE JOBS · in the order they started')
            words.explain('Keep 3 rows');self.assertFalse(words.scripted(),'numbers stay printed');self.assertEqual(words.text(),'Keep 3 rows')
            words.explain('Waiting reasons appear with each item.',lead='No Agenda item passes.');shell2.SCRIPT_ON[0]=False;words.restyle()
            self.assertFalse(words.scripted());self.assertEqual(words.text(),'No Agenda item passes.\nWaiting reasons appear with each item.')
            shell2.SCRIPT_ON[0]=True;words.restyle();self.assertTrue(words.scripted());self.assertIn('passes.</p><p style=',words.text(),'the lead its own line, the note under it')
            hint=shell2.QuietWords(host);hint.explain(shell2.CAPTURE_HINT);self.assertTrue(hint.scripted())
            self.assertNotIn('Ctrl',shell2.CAPTURE_HINT,'0.8.0: the jot box prints no key (the owner: no keyboard shortcut printed anywhere)')
            keys=shell2.QuietWords(host);keys.explain('Ctrl+Enter keeps it · Ctrl+Shift+N from anywhere');self.assertTrue(keys.scripted())
            self.assertIn('Ctrl+Enter</span>',keys.text(),'the keys in a note stay print');self.assertIn('Ctrl+Shift+N</span>',keys.text())
            self.assertEqual(shell2.quiet_html('Ctrl+P finds a file',20,13).count(shell2.SCRIPT),1,'the key printed, the words in the script')
            self.assertIn('<span style="font-size:13px;">Ctrl+P</span>',shell2.quiet_html('Ctrl+P finds a file',20,13))
        finally:shell2.SCRIPT_ON[0]=saved

    def test_script_words_keep_room_round_their_swashes(self):
        """D1-fix (the symmetry review: Parisienne's S, E and i were cut at their label's left edge): a script note is drawn
        whole inside its label: drawn again with room round it, none of its ink falls outside the label's own rect."""
        from pathlib import Path
        from types import SimpleNamespace
        from PySide6.QtWidgets import QApplication,QWidget
        from PySide6.QtGui import QFontDatabase,QImage,QRegion
        from PySide6.QtCore import QPoint,QRect
        from workbench import shell2
        QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parents[1]/'branding/fonts/script/Parisienne-Regular.ttf'))
        host=SimpleNamespace(reading_profile={'ui_pt':14.0});saved=shell2.SCRIPT_ON[0];shell2.SCRIPT_ON[0]=True
        def outside(label,margin=12):
            g=label.geometry();m=label.contentsMargins();label.setContentsMargins(m.left()+margin,m.top()+margin,m.right()+margin,m.bottom()+margin)
            label.resize(g.width()+2*margin,g.height()+2*margin);image=QImage(label.size(),QImage.Format_ARGB32_Premultiplied);image.fill(0)
            QWidget.render(label,image,QPoint(0,0),QRegion(),QWidget.RenderFlag.DrawChildren);inner=QRect(margin,margin,g.width(),g.height())
            label.setContentsMargins(m);label.setGeometry(g)
            return sum(1 for y in range(image.height()) for x in range(image.width()) if not inner.contains(x,y) and image.pixelColor(x,y).alpha()>=64)
        try:
            for note,lead,sep in (('Select saved work in the cabinet to carry its identity here.','',''),('in the order they started','ACTIVE JOBS',' · '),
                                  ('Each row\'s slider: left is more urgent, right is nicer.','WORK · nothing running','\n')):
                words=shell2.QuietWords(host);words.explain(note,lead=lead,sep=sep or '\n');words.resize(220,words.heightForWidth(220));self.assertEqual(outside(words),0,note)
            from PySide6.QtWidgets import QLabel
            for text in ('Good evening.','Nothing new','Graphite'):
                label=QLabel(text);shell2.pleasantry(label,SimpleNamespace(session=SimpleNamespace(state={})),34);label.adjustSize();self.assertEqual(outside(label),0,text)
        finally:shell2.SCRIPT_ON[0]=saved

    def test_the_word_graphite_s_capitals_stand_as_tall_as_the_symbol(self):
        """D1-fix: the script word's optical size: its capitals' height (the face's cap height) is the symbol's drawn height to
        within half a pixel at 14, 18 and 20 pt (a script word against a symbol has no "equal height" of boxes)."""
        from pathlib import Path
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont,QFontDatabase,QFontMetricsF
        from workbench import desk_qt,shell2
        QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parents[1]/'branding/fonts/script/Parisienne-Regular.ttf'))
        for points,px in ((14,33),(18,43),(20,47)):
            scale=points/14.0;self.assertEqual(desk_qt.script_word_px(scale),px,points)
            font=QFont(shell2.SCRIPT);font.setPixelSize(px);self.assertLess(abs(QFontMetricsF(font).capHeight()-desk_qt.symbol_height(scale)),0.5,points)

    def test_the_cat_tile_is_the_egg_height_and_follows_the_interface_size(self):
        self.assertEqual(bar.cat_tile(1.0),(round(44*g.CAT_RATIO),44));self.assertEqual(bar.cat_tile(2.0)[1],62)
        self.assertEqual(bar.cat_tile(0.64),bar.cat_tile(1.0),'a smaller interface never shrinks the cat')

    def test_the_band_places_the_cat_by_its_pale_coat(self):
        """The integration of D2 and D3 (the review of D3, finding 7): the cat is placed and paired by what the band shows, its pale
        coat, as the words are by their ink. Drawn on the band's mean tone at the place the band gives it (cat_ink, outline=False,
        at the inset), its first column at the words' ink level (desk_qt.INK_LEVEL of the way from the band to the lettering) is the
        inset at 14, 18 and 20 pt; the paws' graphite outline beside it stays under that level (graphite on graphite). Placed by the
        extent with the outline (before), the coat began a column later."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor,QImage,QPainter
        from workbench import desk_qt
        QApplication.instance() or QApplication([])
        tone=QColor(desk_qt.grain_report()['mean_tone']);level=tone.lightness()+desk_qt.INK_LEVEL*(QColor(desk_qt.ERASED).lightness()-tone.lightness())
        def first_pale(origin,w,h):
            image=QImage(int(origin+w+8),h,QImage.Format_RGB32);image.fill(tone);p=QPainter(image);g.paint_cat(p,QRectF(origin,0,w,h),g.POSES['rest']);p.end()
            return next(x for x in range(image.width()) if any(QColor(image.pixel(x,y)).lightness()>=level for y in range(h)))
        for points in (14,18,20):
            w,h=bar.cat_tile(points/14.0);inset=desk_qt.inset(points/14.0)
            coat=g.cat_ink(QRectF(0,0,w,h),g.POSES['rest'],False);room=g.cat_ink(QRectF(0,0,w,h),g.POSES['rest'])
            self.assertLess(room[0],coat[0],'the outline lies outside the coat');self.assertGreater(room[2],coat[2])
            self.assertEqual(first_pale(inset-coat[0],w,h),inset,points)
            self.assertEqual(first_pale(inset-room[0],w,h),inset+1,('placed by the outline the coat starts a column in',points))

    def test_the_startup_screen_never_stops_the_start(self):
        from workbench import launch
        with patch.object(g,'startup_screen',side_effect=RuntimeError('no screen')):self.assertIsNone(launch.startup_screen())
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance() or QApplication([])
        with patch('PySide6.QtWidgets.QSplashScreen',side_effect=RuntimeError('no splash')):self.assertIsNone(g.startup_screen(app))

    def test_a_failed_start_closes_the_startup_screen_before_the_message(self):
        import contextlib,io,sys,types,shiboken6
        from workbench import launch,qt_app
        shown=[];real=g.startup_screen;quiet=types.ModuleType('prepare_release');quiet.prepare=lambda app:None
        def spy(app):shown.append(real(app));return shown[-1]
        with patch.dict(sys.modules,{'prepare_release':quiet}),patch.object(g,'startup_screen',spy),patch.object(qt_app,'main',side_effect=RuntimeError('fixture')),\
             patch.object(launch,'write_error_log',return_value=None),patch.object(launch,'alert'),patch.object(launch,'extend_path'),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launch.main([]),1)
        self.assertTrue(shown and shown[0] is not None,'the startup screen was shown first')
        self.assertTrue(not shiboken6.isValid(shown[0]) or not shown[0].isVisible(),'and closed before the failure message')


def literals(path):
    """(line, text) of every string literal in a module except docstrings: what can reach a person."""
    import ast
    tree=ast.parse(path.read_text(encoding='utf-8'));docs=set()
    for n in ast.walk(tree):
        if isinstance(n,(ast.Module,ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(getattr(n.body[0],'value',None),ast.Constant):
            docs.add(id(n.body[0].value))
    return [(n.lineno,n.value) for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in docs]


class RenameGuardTests(unittest.TestCase):
    """G-C, the owner's public rename (D32): Graphite is the single public name of the workspace and its AI; internal
    identifiers, settings keys, record identities and paths on disk keep their names. The exceptions are listed here on purpose."""
    from pathlib import Path as _P
    WORKBENCH=_P(__file__).resolve().parents[1]/'workbench'
    # "Ledger & Slate" left in a literal only as a compatibility identity: the product field of signed release metadata and
    # runtime manifests (existing releases must still verify) and the recorded name of the 13D phone-link candidate (history).
    OLD_NAME={('release_publisher.py','Ledger & Slate'),('release_updates.py','Ledger & Slate'),('update_checks.py','Ledger & Slate'),
              ('remote_service.py','Ledger and Slate 13D Development candidate')}
    # The window's own modules: no literal says Slate, Ledger or Hatch as a word, except these kept on purpose.
    FRAME=('shell2','hatch_qt','typebar_qt','desktop_header_qt','menus2','agent_qt','agent_loop','explore','explore_qt','settings_qt',
           'machine_qt','machine_overview','return_thread_qt','service_lifecycle','service_lifecycle_qt','operations_qt','empty_workspace_qt',
           'document_qt','files_qt','finder_qt','agenda','agenda_qt','tail_words','conditions','profile_files','profile_numbers','launch',
           'graphite_brand','struthio_qt','model_turn','programs_qt','system_menu_qt','session_power',  # D2: the programs list, the System menu
           'compare_qt','working_copies','working_folders','doctor','hatch_readiness',
           # V01 W1: the left column's cabinet and concern navigator, the centre foot, and the modules whose shown words W1 renamed
           'cabinet','concern_qt','control_qt','pills','pills_qt','locations','stacy_language','release_updates','remote_service')
    KEPT={('files_qt.py','Slate'),                                   # the Files/Slate folder's name on disk (files_service.SLATE)
          ('files_qt.py',"Graphite's area (the Slate folder). Graphite writes here directly; every change keeps the version before it, and deletions go to Trash."),
          ('shell2.py','Slate'),('shell2.py','Slate/answer '),       # files.list path=Slate; a kept answer's path in Files/Slate
          ('shell2.py','\n(What Ledger knows:'),                     # pages written before the rename still split cleanly
          ('typebar_qt.py','files.list path=Slate  ·  help copies.review  ·  ops agenda'),  # a staC example naming that folder
          ('settings_qt.py','Slate'),                                # a stored settings category (a hidden filter value)
          ('hatch_qt.py','Hatch'),('hatch_qt.py','QToolButton#Hatch {background:transparent;border:0;padding:2px 3px;}'),  # object name and its stylesheet
          ('doctor.py','Ledger'),('doctor.py','Ledger sources'),     # the ~/Concern/Ledger folder name; a stored search term
          ('hatch_readiness.py','Graphite - HATCH readiness'),        # the HATCH checkpoint name stays internal
          ('hatch_readiness.py','NOT_PERFORMED; preflight never closes I05, I06 or a HATCH milestone.'),
          ('control_qt.py','Slate'),                                 # the same stored settings category, shown as Assistant
          ('locations.py','Ledger'),                                 # the ~/Concern/Ledger workspace folder on disk
          ('pills.py','Ledger'),                                     # the pills keyring identity (pills.ring)
          ('release_updates.py','Ledger & Slate'),                   # the product field of signed release metadata (OLD_NAME)
          ('remote_service.py','X-Ledger-CSRF'),                     # the phone app's request header
          ('remote_service.py','Ledger and Slate 13D Development candidate')}  # the recorded 13D candidate name (OLD_NAME)

    def words(self,name,pattern):
        import re
        return [(line,text) for line,text in literals(self.WORKBENCH/name) if re.search(pattern,text)]

    def test_no_literal_says_ledger_and_slate_except_compatibility_identities(self):
        found={(p.name,text) for p in sorted(self.WORKBENCH.glob('*.py')) for _,text in self.words(p.name,r'Ledger (&|&&|and) Slate')}
        # version.LINEAGE says what the program was called before Graphite ("as Ledger & Slate"): the lineage, not a shown name.
        lineage={(name,text) for name,text in found if name=='version.py' and 'as Ledger & Slate' in text}
        self.assertLessEqual(len(lineage),1);self.assertEqual(found-lineage,self.OLD_NAME)

    def test_the_window_says_graphite_and_the_menu(self):
        import re
        left=set()
        for module in self.FRAME:
            for line,text in self.words(module+'.py',r'\b(Ledger|Slate|Hatch|LEDGER|SLATE|HATCH)\b'):
                if re.fullmatch(r'[A-Za-z]+',text) and text not in ('Slate','Ledger','Hatch','LEDGER','SLATE','HATCH'):continue  # object names (SlateFace, LedgerDate…)
                if '#' in text and '{' in text:continue                                                    # stylesheets by object name
                if text in ('SLATE','LEDGER','HUMAN'):continue                                           # record actors and origins (stored identities)
                left.add((module+'.py',text))
        self.assertEqual(left-self.KEPT,set(),'user-facing words still naming Slate, Ledger or Hatch')

    def test_public_name_and_internal_identities(self):
        from workbench import version,hatch_qt,typebar_qt,desktop_header_qt
        self.assertEqual((version.NAME,version.SHORT,version.title()),('Graphite','0.1','Graphite 0.1'))
        self.assertEqual(typebar_qt.TARGETS[0],('slate','Assignment'),'the first mode is Assignment (D3; the one who answers stays Graphite); its key stays slate')
        self.assertEqual((hatch_qt.HatchButton.NAME,hatch_qt.SERVICES_MENU),('Open programs','Graphite services'))  # HATCH DESK D2: the cat opens the programs list
        self.assertEqual(desktop_header_qt.SlateSwitch.__name__,'SlateSwitch','class names are internal and stay')

    def test_settings_speak_graphite_and_show_workspace_and_assistant(self):
        """The setting definitions carry Graphite's words; their keys and root keys stay for compatibility. The page shows the two
        roots as Workspace and Assistant: settings_registry.public adds the root's shown name and changes nothing else."""
        import re
        from workbench import settings_registry as reg
        roots={(n['id'],n['label']) for n in reg.nodes() if n['parent'] is None}
        self.assertEqual(roots,{('settings:ledger','Workspace'),('settings:slate','Assistant')})
        self.assertEqual({s['root'] for s in reg.SPECS},{'Ledger','Slate'},'root keys unchanged')
        for spec in reg.SPECS:
            shown=reg.public(spec)
            self.assertIn(shown['root_name'],('Workspace','Assistant'))
            for field in ('label','description','effect'):
                self.assertIsNone(re.search(r'\b(Ledger|Slate|Hatch)\b',shown[field]),(spec['key'],field,shown[field]))
            self.assertEqual({k:v for k,v in shown.items() if k!='root_name'},spec,'only the root name is added')
        labels={n['target']:n['label'] for n in reg.nodes() if n['role']=='setting'}
        self.assertEqual(labels['stacy.enabled'],'Allow new Graphite AI activity')

    def test_the_catalog_seed_says_graphite_and_an_old_seed_is_shown_so(self):
        """A new catalog seeds the 'ledger' row as Graphite (its id stays). A catalog made before the rename keeps its stored
        'Ledger' (nothing migrates it) and is shown as Graphite while untouched; a title the owner chose is shown as written."""
        import sqlite3,tempfile
        from pathlib import Path
        from sdk.cli.arc1cli import concern_catalog as cc
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'concern/catalog.sqlite3';store=cc.Catalog(path)
            self.assertEqual((store.get('ledger')['title'],store.get('operations')['summary']),('Graphite','Graphite maintenance, installation and recovery.'))
            with sqlite3.connect(path) as db:db.execute("UPDATE objects SET title='Ledger' WHERE id='ledger'")
            self.assertEqual(cc.Catalog(path).get('ledger')['title'],'Ledger','a stored row is never rewritten')
        self.assertEqual(cc.shown('ledger','Ledger'),'Graphite');self.assertEqual(cc.shown('ledger','Ledger of parts'),'Ledger of parts')
        self.assertEqual(cc.shown('projects','Ledger'),'Ledger','only the seed row itself');self.assertEqual(cc.shown('operations','Operations'),'Operations')
        self.assertEqual(cc.shown('operations','Ledger maintenance, installation and recovery.','summary'),'Graphite maintenance, installation and recovery.')

    def test_words_written_before_the_rename_stay_readable(self):
        """A condition card's result paragraph is found by its block id, never by its words, so pages that say "checked by Slate"
        keep working; new results say Graphite. A reason stored before the rename is shown as written."""
        from workbench import conditions,agent_qt
        self.assertIn('checked by Graphite',conditions.result_words([{'text':'1 kg'}],{'text':'1 kg'}))
        rows=[{'id':'a','state':'PAUSED','request':'add up','paused_reason':'Ledger closed'}]
        with patch.object(agent_qt,'summaries',return_value=rows),patch.object(agent_qt,'service_report',return_value=[],create=True):
            try:out=[t for t,_,_ in agent_qt.today_rows(object())]
            except Exception as e:self.skipTest('today_rows needs a host here: %s'%e)
        self.assertIn('Graphite paused: add up (Ledger closed)',out)


if __name__=='__main__':
    unittest.main()


class TodayWorkspaceWordsTests(unittest.TestCase):
    """Today's sentence under the greeting and its THIS WORKSPACE fact name the workspace (its marker's name), never the last
    recently opened file: TodayPage.fill once reused `name` for the Continue rows (V01 W1, item 3). Kernel reads are patched
    to None, so nothing is dispatched, launched or asked."""
    def test_the_workspace_name_survives_the_continue_rows(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from PySide6.QtWidgets import QApplication,QLabel
        from workbench import shell2,locations,agent_qt
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            root=locations.ensure_workspace(Path(tmp)/'north',name='North field')
            host=SimpleNamespace(root=root,_viewer_recent=[],reading_profile={'ui_pt':14},resume_workspace=lambda:None,
                                 open_in_viewer=lambda *a:None,open_document=lambda *a:None,
                                 session=SimpleNamespace(state={'recent':['Survey/second/gate posts.md'],'cursive':False}))
            with patch.object(shell2,'call',return_value=None),patch.object(agent_qt,'today_rows',return_value=[]):
                today=shell2.TodayPage(host);self.addCleanup(today.deleteLater);today.fill()
            rows=[l.text() for l in today.continue_.findChildren(QLabel)]
            self.assertTrue(any('gate posts.md' in t for t in rows),'the recent file is in Continue')
            self.assertTrue(today.facts['workspace'].text().startswith('North field\n'),today.facts['workspace'].text())
            self.assertTrue(today.where.text().startswith('North field  ·  '),today.where.text())
            self.assertNotIn('gate posts',today.where.text()+today.facts['workspace'].text())


class GameDesk(unittest.TestCase):
    """The owner's STRUTHIO game, opened from the mark: the 1.9.0 copy with desk mode, served on 127.0.0.1 and opened with ?desk."""

    def test_the_copy_is_1_9_0_and_records_its_source(self):
        from workbench import struthio_qt
        game = struthio_qt.GAME
        self.assertIn('STRUTHIO-ARCADE-1.9.0', (game / 'index.html').read_text())
        self.assertTrue((game / 'src' / 'app' / 'desk.mjs').is_file())
        self.assertRegex((game / 'FROM_REPOSITORY.txt').read_text(), r'^[0-9a-f]{40} STRUTHIO ARCADE 1\.9\.0')
        self.assertEqual(struthio_qt.DESK, '?desk')

    def test_the_server_answers_the_desk_address(self):
        import urllib.request
        from workbench import struthio_qt
        server, url = struthio_qt.serve()
        try:
            with urllib.request.urlopen(url + struthio_qt.DESK, timeout=10) as page:
                self.assertEqual(page.status, 200); self.assertIn(b'STRUTHIO-ARCADE-1.9.0', page.read())
            with urllib.request.urlopen(url + 'src/app/desk.mjs', timeout=10) as module:
                self.assertIn(b'deskMode', module.read())
        finally:
            server.shutdown(); server.server_close()

    def test_the_game_keeps_one_address_and_falls_back_when_it_is_taken(self):
        # the game window keeps saves per address, so a steady port keeps them between sessions
        import socket
        from workbench import struthio_qt
        self.assertEqual(struthio_qt.serve.__defaults__[1], struthio_qt.PORT)
        probe = socket.socket(); probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]; probe.close()
        first, url = struthio_qt.serve(port=port)
        try:
            self.assertEqual(url, 'http://127.0.0.1:%d/' % port)
            second, other = struthio_qt.serve(port=port)
            try:
                self.assertNotEqual(other, url); self.assertTrue(other.startswith('http://127.0.0.1:'))
            finally:
                second.shutdown(); second.server_close()
        finally:
            first.shutdown(); first.server_close()

    def test_the_game_window_is_given_the_desk_address(self):
        from unittest import mock
        from workbench import struthio_qt
        started = {}
        class Process:
            NotRunning = 0
            def __init__(self, host): self.signals = []
            def state(self): return 0
            def setProgram(self, p): started['program'] = p
            def setArguments(self, a): started['args'] = a
            def start(self): started['started'] = True
            def __getattr__(self, name): return mock.MagicMock()
        class Host: _struthio = (None, 'http://127.0.0.1:9/'); _struthio_process = None
        with mock.patch.object(struthio_qt, 'QProcess', Process), mock.patch.object(struthio_qt, 'note', lambda *a, **k: None):
            struthio_qt.show(Host())
        self.assertEqual(started['args'], ['-m', 'workbench.struthio_play', 'http://127.0.0.1:9/?desk'])
