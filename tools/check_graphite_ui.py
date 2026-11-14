"""Actual Qt check of GRAPHITE-01 G-A, the owner's design update of 2026-11-06, offscreen: the startup screen, the head's
mark and the peeking cat that opens the menu.

Steps: the startup screen (launch.startup_screen, before the window is built) is graphite ground with the paper point and
GRAPHITE, frameless and centred, and closes when the window is shown; the head's mark is the point on a graphite tile named
Graphite and still opens the STRUTHIO game (struthio_qt.show patched to a recorder); the cat is unlabeled, its tooltip and
accessible name Open menu; REST, HOVER, MENU OPEN and SLEEPY are reached by real pointer, click and key events and captured
(crops enlarged, whole windows at 1920 by 1200 and 1366 by 768, and the four poses drawn large by the button's own painter);
the open pose wins over hover and the menu's close returns to rest or hover by the pointer; sleep after a patched short
inactivity, input elsewhere keeps it asleep, hover wakes it into the side-eye, one click from sleep opens the menu; Space
and Enter open the menu with its first row active (LauncherKeys, unchanged); a pose change moves for about MOVE_MS and
Reduce motion switches directly; the cat follows the interface size. HATCH DESK D1a: the mark left the upper left (the word
Graphite stands there alone) and lives at the far right of the head as the erased symbol, the System menu; the STRUTHIO game
opens from the System menu (HATCH DESK D2: Game, its first row); the old button stays out of sight for callers. HATCH DESK D2:
the cat is pale paper on the band with graphite eyes and paws, named Open programs, and opens the programs list (the menu
below is programs_qt.ProgramsList: its active row is the row under keyboard focus, its first row Agenda). Disposable profile and Concern; Kernel.launch,
Kernel.submit and the provider request are held; after the window exists no process, shell command or detached program
may start. Nothing here is owner-host acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_GRAPHITE_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/graphite')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='graphite01-brand-ui-'))
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.dont_write_bytecode=True
import shiboken6
from PySide6.QtCore import Qt,QPoint,QProcess,QRect,QRectF,QSize,QTimer
from PySide6.QtGui import QAccessible,QColor,QCursor,QFont,QImage,QPainter,QPixmap
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench import launch,graphite_brand as brand
splash=launch.startup_screen()  # exactly as launch.main does, before anything else of the window exists
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,typebar_qt,struthio_qt,desk_qt as desk
from workbench.explore_qt import F1_NOTE
from workbench.hatch_qt import CHOICES
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
from workbench import session_power  # D2-fix: the one session and power function is held for the whole run, on any computer
def held_power(request):
 """logind answers that there is no login session; no session or power command may start."""
 if request[0]=='logind':raise OSError('no login session (held by this check)')
 raise AssertionError('No session or power command: %r'%(request,))
held_logind=patch.object(session_power,'system',side_effect=held_power).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
checks=[];captures=[];observations={};PREFIX='Graphite_01_Brand_'
def check(text):checks.append(text);print(text,flush=True)
def record(name,note,image,mode):
 target=OUT/(PREFIX+name);assert image.save(str(target),'PNG'),name
 captures.append(dict(file=PREFIX+name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[image.width(),image.height()]))
def tally(image,colour,tolerance=18):
 c=QColor(colour);return sum(1 for y in range(image.height()) for x in range(image.width()) if (lambda p:abs(p.red()-c.red())<=tolerance and abs(p.green()-c.green())<=tolerance and abs(p.blue()-c.blue())<=tolerance)(image.pixelColor(x,y)))
# 01 · the startup screen, before the window is built --------------------------------------------------------------------------
app=make_app([])
assert splash is not None and splash.isVisible() and splash.objectName()=='GraphiteStartup',splash
assert splash.windowFlags()&Qt.FramelessWindowHint and splash.windowFlags()&Qt.SplashScreen
centre=app.primaryScreen().geometry().center();offset=splash.geometry().center()-centre;assert abs(offset.x())<=2 and abs(offset.y())<=2,offset
shot=splash.grab().toImage();ground=tally(shot,brand.GRAPHITE,6);paper=tally(shot,brand.PAPER,10);area=shot.width()*shot.height()
assert ground>area*.6 and paper>area*.08,(ground,paper,area)
record('01_Startup_Screen.png','The startup screen launch.main shows before the window is built: graphite ground, the sharpened point in paper, GRAPHITE in spaced capitals below; frameless and centred; no fade.',shot,'ACTUAL_QT_WIDGET_GRAB')
root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;bar=w.type_bar;hatch=bar.hatch;menu=hatch.menu();cat=hatch.cat
during_build=shiboken6.isValid(splash) and splash.isVisible()
import platform;platform.processor()  # the one host probe Python answers through a process, answered before the guards
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def align(times=3):
 for _ in range(times):bar.align();settle()
def wait_for(condition,ms=3000):
 """Process events until the condition holds or ms pass (QTest.qWaitFor, which this PySide6 lacks): a condition, never a fixed time."""
 end=time.monotonic()+ms/1000
 while not condition():
  if time.monotonic()>end:return False
  app.processEvents();QTest.qWait(10)
 return True
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
w.resize(1920,1200);w.show();settle(120);bridge.timer.stop();hatch.lifecycle.timer.stop();align();w.activateWindow();settle()
closed=not shiboken6.isValid(splash) or not splash.isVisible()
assert during_build and closed,(during_build,closed)
observations['startup']=dict(size=[shot.width(),shot.height()],centre_offset=[offset.x(),offset.y()],graphite_share=round(ground/area,3),paper_share=round(paper/area,3),visible_while_building=during_build,closed_when_window_shown=closed)
check('01 The startup screen shows before the window is built (graphite %d%%, paper %d%% of its pixels), frameless and centred, stays while the window is built and closes when the window is shown'%(100*ground//area,100*paper//area))
# 02 · the head's mark, and the game still opens from it -----------------------------------------------------------------------
gs=w.global_search;top=w.shell2.top;sym=top.nice
assert not gs.isVisible() and gs.toolTip()=='Graphite' and top.mark.isHidden() and top.wordmark.isVisible() and top.wordmark.text()=='Graphite','D1a: one mark, at the far right'
assert sym.isVisible() and sym.accessibleName()==sym.toolTip()=='System menu' and sym.geometry().right()+1==sym.parentWidget().width()-w.desk.inset
mark=w.grab(QRect(sym.mapTo(w,QPoint(0,0)),sym.size())).toImage();tile=tally(mark,desk.ERASED,16);wedges=tally(mark,'#%02x%02x%02x'%desk.BAND,10)
assert tile>120 and wedges>tile,(tile,wedges)  # the point drawn in the bands' erased paper, on the band's graphite
right=w.ribbon_dock.width();head=w.grab(QRect(right-w.desk.pane,0,w.desk.pane,w.ribbon_dock.height())).toImage()
record('02_Head_Mark.png','The head at 1920 by 1200, right end, enlarged 2x: the sharpened point drawn pale on the band, the System menu (D1a; GRAPHITE-01 put it on a small graphite tile at the upper left), beside CPU · GPU · RAM · TXT.',head.scaled(head.width()*2,head.height()*2,Qt.KeepAspectRatio,Qt.SmoothTransformation),'ACTUAL_QT_WINDOW_GRAB_CROP_ENLARGED')
small=[16,24,32,44];strip=QImage(sum(s*6+12 for s in small)+12,44*6+24,QImage.Format_ARGB32);strip.fill(QColor(brand.PAPER));painter=QPainter(strip);x=12
for s in small:painter.drawImage(x,12,brand.mark_tile(s).toImage().scaled(s*6,s*6,Qt.KeepAspectRatio,Qt.FastTransformation));x+=s*6+12
painter.end();record('02b_Mark_Small_Sizes_6x.png','The tile at 16, 24 and 32 px (the window icon\'s small entries) and 44 px (the head), each pixel enlarged 6x: the gap between the wedges reads and the stroke is solid; at 16 px the stroke is left out rather than drawn as a smudge.',strip,'PAINTED_BY_GRAPHITE_BRAND_MARK_TILE_ENLARGED_6X')
assert {(s.width(),s.height()) for s in w.windowIcon().availableSizes()}>={(n,n) for n in (16,24,32,48,64,128,256)},w.windowIcon().availableSizes()
sym.open();settle(60);assert sym.popup.isVisible()
with patch.object(struthio_qt,'show') as game:QTest.mouseClick(sym.popup.game,Qt.LeftButton);settle()
assert game.call_count==1 and game.call_args[0][0] is w and not sym.popup.isVisible(),game.call_args_list
observations['mark']=dict(button=[sym.width(),sym.height()],erased_pixels=tile,band_pixels=wedges,old_button_hidden=not gs.isVisible())
check('02 The head\'s mark is the sharpened point drawn pale on the band at the far right (%d erased-paper pixels), the System menu; its first row, Game, opens the STRUTHIO game (struthio_qt.show called once with the window, patched); the old tile button is out of sight'%tile)
# 03 · the cat: unlabeled, Open programs (D2) -------------------------------------------------------------------------------------------
iface=QAccessible.queryAccessibleInterface(hatch)
assert hatch.text()=='' and hatch.toolButtonStyle()==Qt.ToolButtonIconOnly and hatch.icon().isNull(),'unlabeled: no word and no picture, the cat is painted'
assert hatch.accessibleName()==hatch.toolTip()=='Open apps' and iface.text(QAccessible.Name)=='Open apps' and F1_NOTE in hatch.accessibleDescription()
hatch.refresh();settle()  # a lifecycle render (as every opening runs one): the choices stay in the accessible description
assert hatch.accessibleDescription()==hatch.lifecycle.state['summary']+' · '+CHOICES+' · '+F1_NOTE and hatch.toolTip()=='Open apps',hatch.accessibleDescription()
assert hatch.iconSize()==QSize(*typebar_qt.cat_tile(1.0)) and hatch.iconSize().height()==typebar_qt.hatch_icon_px(1.0)==44
def cat_left():  # D1-fix: the cat is placed by its drawing at rest (graphite_brand.cat_ink in its tile), not by its button's box;
 # the integration of D2 and D3: by its pale coat (outline=False), what the band shows
 return round(hatch.mapTo(w,QPoint(0,0)).x()+brand.cat_ink(hatch.tile(),brand.POSES['rest'],False)[0],6)
(lp,ls),_=bar.rows();assert lp[0] is hatch and cat_left()==w.desk.inset,('at the lower-left edge, its drawing the band\'s inset from it',cat_left())
observations['names']=dict(text=hatch.text(),tooltip=hatch.toolTip(),accessible_name=iface.text(QAccessible.Name),accessible_description=hatch.accessibleDescription(),tile=[hatch.iconSize().width(),hatch.iconSize().height()],button=[hatch.width(),hatch.height()])
check('03 The cat stands at the lower-left of the strip with no word beside it; tooltip and accessible name Open programs (the accessible description keeps the service summary, the list\'s words and the F1 note after a lifecycle render); %d by %d px at 14 pt'%(hatch.iconSize().width(),hatch.iconSize().height()))
# pointer and capture helpers
def point_at(widget,pos=None,wait=True):
 pos=pos or widget.rect().center();QCursor.setPos(widget.mapToGlobal(pos));QTest.mouseMove(widget,pos)
 if wait:settle(120)
def away():point_at(bar.box)
def crop(name,note,scale=4):
 g=QRect(hatch.mapTo(w,QPoint(0,0)),hatch.size()).adjusted(-10,-14,14,6);image=w.grab(g).toImage()
 record(name,note,image.scaled(image.width()*scale,image.height()*scale,Qt.KeepAspectRatio,Qt.FastTransformation),'ACTUAL_QT_WINDOW_GRAB_CROP_ENLARGED_%dX'%scale)
def window(name,note,*popups):
 pix=w.grab();painter=QPainter(pix);mode='ACTUAL_QT_WINDOW_GRAB'
 for popup in popups:
  pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));assert popup.isVisible() and pos.x()>=0 and pos.y()>=0,(name,pos)
  painter.drawPixmap(pos,popup.grab());mode='ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS'
 painter.end();record(name,note,pix.toImage(),mode)
def with_menu(opener,inside=None):
 rec={'error':None}
 def driver():
  try:
   rec['visible']=menu.isVisible();rec['pose']=cat.pose;rec['first_active']=getattr(app.focusWidget(),'word',None)  # D2: the active row is the focused one
   if inside:inside(rec)
  except Exception as exc:rec['error']=repr(exc)
  finally:
   QTest.keyClick(app.focusWidget() if app.focusWidget() is not None and app.focusWidget().window() is menu else menu,Qt.Key_Escape);settle(5)
   if menu.isVisible():menu.hide()
 QTimer.singleShot(80,driver);opener();settle(60);rec['after']=cat.pose;rec['closed']=not menu.isVisible();return rec
def settled(pose):return cat.pose==pose and cat.params==brand.POSES[pose]
# 04 · REST and HOVER --------------------------------------------------------------------------------------------------------
away();settle(200);assert settled('rest'),(cat.pose,cat.params)
crop('03_Cat_Rest_crop.png','REST: eyes forward, both paws on the edge, tail tucked away (window crop, 4x).')
window('04_Cat_Rest_1920.png','1920 by 1200: the cat at rest at the lower-left of the typing strip, unlabeled.')
point_at(hatch);settle(200);assert settled('hover'),(cat.pose,cat.params)
crop('05_Cat_Hover_crop.png','HOVER: a quick side-eye; the tail rises in a question-mark curl that is part of the tail (no separate dot); both paws down.')
check('04 Pointer events: away from the cat it rests; on it the cat gives the side-eye with the tail\'s question-mark curl, paws down')
# 05 · MENU OPEN: one click, precedence over hover, back to hover or rest by the pointer -------------------------------------
def opened(rec):
 QTest.qWait(220);rec['settled']=settled('open');crop('06_Cat_Menu_Open_crop.png','LIST OPEN: the tail dropped out of sight, the right paw lifted as if bringing the list up, the eyes up toward it in pencil yellow.')
 window('07_Menu_Open_1920.png','1920 by 1200: one click on the cat opened the programs list at once; the cat holds the open pose.',menu)
 point_at(menu,wait=False);QTest.qWait(200);rec['pointer_on_menu']=cat.pose
 point_at(hatch,wait=False);QTest.qWait(60);rec['pointer_back']=cat.pose
click=with_menu(lambda:QTest.mouseClick(hatch,Qt.LeftButton),opened)
assert click['error'] is None and click['visible'] and click['pose']=='open' and click['settled'] and click['pointer_on_menu']=='open' and click['pointer_back']=='open',click
settle(200);assert click['closed'] and click['after']=='hover' and settled('hover'),click
away();settle(60);assert cat.pose=='rest'
observations['click']=click
check('05 One click opens the programs list at once in the open pose; the open pose holds with the pointer on the menu and back on the cat (precedence over hover); on close the pointer over the cat gives hover, away gives rest')
# 06 · SLEEPY: inactivity with the menu closed; input elsewhere keeps it asleep; hover wakes it; one click from sleep ----------
cat.idle.setInterval(500);cat.idle.start();settle(60);assert cat.pose=='rest'
time_asleep=time.monotonic();QTest.qWait(800);settle(60);assert settled('sleepy'),(cat.pose,cat.params)
crop('08_Cat_Sleepy_crop.png','SLEEPY: after a stretch without input (shortened to 0.5 s for the check), the head a little lower and the eyes closed.')
window('09_Cat_Sleepy_1920.png','1920 by 1200 with the cat asleep at the lower left.')
cat.idle.setInterval(5000)  # long enough for the steps below; the timer restarts on each input
bar.box.setFocus();QTest.keyClick(bar.box,Qt.Key_Shift);settle(60);assert cat.pose=='sleepy' and cat.idle.isActive(),'input elsewhere restarts the timer and keeps the cat asleep'
point_at(hatch);settle(200);assert settled('hover'),('hover wakes it into the side-eye',cat.pose,vars(cat.poses))
away();cat.idle.setInterval(500);cat.idle.start();QTest.qWait(800);settle(60);assert cat.pose=='sleepy'
sleepy_click=with_menu(lambda:QTest.mouseClick(hatch,Qt.LeftButton))
assert sleepy_click['error'] is None and sleepy_click['visible'] and sleepy_click['pose']=='open',sleepy_click
away();settle(60)
observations['sleep']=dict(idle_ms_patched=500,default_idle_ms=brand.IDLE_MS,one_click_from_sleep=sleepy_click)
check('06 With the list closed and no input for the (patched) 0.5 s the cat is sleepy; a key typed elsewhere keeps it asleep and restarts the timer; hover wakes it into the side-eye; from sleep one click opens the list in the open pose')
# 07 · keyboard: Space and Enter open the menu (first row active); focus marks the edge in eraser pink -------------------------
cat.idle.setInterval(brand.IDLE_MS);cat.idle.start()
bar.box.setFocus();settle(60);unfocused=tally(hatch.grab().toImage(),brand.ERASER_MARK,14)  # D2: the nose and inner ears are always pink
w.activateWindow();hatch.setFocus();assert wait_for(lambda:app.focusWidget() is hatch),app.focusWidget()
edge=hatch.grab().toImage();pink=tally(edge,brand.ERASER_MARK,14)-unfocused;assert pink>40,(pink,unfocused)
crop('10_Cat_Keyboard_Focus_crop.png','Keyboard focus on the cat: a short eraser-pink mark under it (its nose and inner ears are pink always).')
keys={}
for name,key in (('space',Qt.Key_Space),('enter',Qt.Key_Return)):
 w.activateWindow();hatch.setFocus();assert wait_for(lambda:app.focusWidget() is hatch),(name,app.focusWidget())
 rec=with_menu(lambda key=key:QTest.keyClick(hatch,key));keys[name]=rec
 # Focus comes back to the cat: the window's own focus child, which a person has again whenever the window is active. Under
 # load the offscreen platform may leave the application's active window on the hidden popup (focusWidget None) however long
 # one waits, so the window is activated again and the application's focus is waited for: conditions, not fixed times.
 rec['focus_after']=wait_for(lambda:not menu.isVisible() and w.focusWidget() is hatch)
 w.activateWindow();rec['app_focus_after']=wait_for(lambda:app.focusWidget() is hatch)
 assert rec['error'] is None and rec['visible'] and rec['pose']=='open' and rec['first_active']=='Agenda' and rec['closed'] and rec['focus_after'] and rec['app_focus_after'],(name,rec,app.activeWindow(),app.focusWidget(),w.focusWidget())
settle(200);assert settled('rest'),'the pointer is away: rest'
observations['keyboard']=dict(keys,focus_edge_pink_pixels=pink)
check('07 Space and Enter on the focused cat open the programs list with its first row (Agenda) active, in the open pose; Escape closes it, focus returns to the cat, and with the pointer away it rests; keyboard focus puts a short eraser-pink mark under it (%d px)'%pink)
# 08 · brief movement, and Reduce motion switches directly ----------------------------------------------------------------------
point_at(hatch,wait=False);app.processEvents();running=cat.animation.state()==cat.animation.State.Running;samples=[]
began=time.monotonic()
while time.monotonic()-began<.4:samples.append(round(dict(zip(brand.FIELDS,cat.params))['tail'],2));QTest.qWait(20)
assert running and samples[0]<1 and samples[-1]==1 and len(set(samples))>=3 and settled('hover'),(running,samples)
away();settle(250)
def reading(**changes):
 for key,value in changes.items():call('ledger.settings.set',{'key':'reading.'+key,'value':value})
 bridge.sync_profile(force=True);settle(60)
reading(reduce_motion=True);assert w.reading_profile['reduce_motion'] is True
point_at(hatch,wait=False);app.processEvents();direct=cat.params==brand.POSES['hover'] and cat.animation.state()!=cat.animation.State.Running
away();app.processEvents();direct=direct and cat.params==brand.POSES['rest']
reading(reduce_motion=False);assert direct
observations['motion']=dict(move_ms=brand.MOVE_MS,tail_samples_every_20ms=samples,reduce_motion_direct=direct)
check('08 A pose change moves the numbers in one short animation (%d ms; the tail rose through %d sampled steps); under reading.reduce_motion the pose switches directly with no animation'%(brand.MOVE_MS,len(set(samples))))
# 09 · the four poses drawn large, by the button's own painter ----------------------------------------------------------------
H=220;W=round(H*brand.CAT_RATIO);sheet=QPixmap(2*W+120,2*(H+60)+60);sheet.fill(QColor(brand.PAPER));p=QPainter(sheet)
font=QFont('IBM Plex Mono');font.setPixelSize(20);font.setLetterSpacing(QFont.AbsoluteSpacing,3);p.setFont(font);p.setPen(QColor(brand.GRAPHITE))
p.drawText(QRectF(30,10,400,30),Qt.AlignLeft|Qt.AlignVCenter,brand.WORD)
for i,(pose,word) in enumerate((('rest','REST'),('hover','HOVER'),('open','LIST OPEN'),('sleepy','SLEEPY'))):
 x=40+(i%2)*(W+40);y=50+(i//2)*(H+60);p.drawPixmap(x,y,brand.pose_pixmap(pose,H));p.drawText(QRectF(x,y+H+4,W,30),Qt.AlignCenter,word)
p.end();record('11_Cat_Four_Poses_large.png','The four poses at 220 px on the band\'s shading, drawn by graphite_brand.paint_cat, the painter the button uses (D2: the pale coat, graphite eyes and paws, the pink nose and ears, yellow irises on hover and with the list open); laid out like the owner\'s reference sheet (branding/graphite/reference/).',sheet.toImage(),'PAINTED_BY_THE_BUTTONS_OWN_PAINTER')
check('09 The four poses drawn large by the button\'s own painter, beside the reference layout')
# 10 · compact: 1366 by 768; the cat follows the interface size -----------------------------------------------------------------
bar.box.setFocus();w.resize(1366,768);settle(80);align();away();settle(200);assert settled('rest') and hatch.isVisible() and cat_left()==w.desk.inset
window('12_Cat_Rest_1366.png','1366 by 768: the cat at rest at the lower left; the strip\'s words beside it.')
point_at(hatch);settle(200);crop('13_Cat_Hover_1366_crop.png','1366 by 768: hover.')
compact=with_menu(lambda:QTest.mouseClick(hatch,Qt.LeftButton),lambda rec:(QTest.qWait(220),window('14_Menu_Open_1366.png','1366 by 768: the programs list opened by one click on the cat, which holds the open pose.',menu)))
assert compact['error'] is None and compact['visible'] and compact['pose']=='open',compact
away();settle(60)
fit=None
if (PROGRAM/'tools/ui_fit.py').is_file():
 sys.path.insert(0,str(PROGRAM/'tools'));from ui_fit import whole_words,describe
 fit=whole_words(bar);assert not fit,describe(fit)
reading(ui_pt=20);align();settle(80);big=[hatch.iconSize().width(),hatch.iconSize().height()]
assert big==list(typebar_qt.cat_tile(20/14)) and big[1]==62,big
crop('15_Cat_Rest_20pt_crop.png','At 20 pt interface text the cat is 62 px high (the 1.4 cap), enlarged 2x.',scale=2)
reading(ui_pt=14);w.resize(1920,1200);settle(60);align()
observations['compact']=dict(window=[1366,768],strip_words_whole=None if fit is None else fit==[],tile_at_20pt=big)
check('10 At 1366 by 768 the cat rests at the lower left, hovers and opens the programs list with one click%s; at 20 pt it is %d px high (the 1.4 cap)'%('' if fit is None else ', every strip word whole (tools/ui_fit)',big[1]))
# 11 · nothing started; clean close -------------------------------------------------------------------------------------------
assert k.listing('jobs')==[]
popen.assert_not_called();system.assert_not_called();detached.assert_not_called();launcher.assert_not_called();submission.assert_not_called();provider.assert_not_called()
assert w.close() is True;settle();assert not w.desktop_lease.exists()
check('11 No job, worker, model, provider request, process, shell command or detached program; clean close removed the lease')
result=dict(schema='graphite01-brand-ui/1',checkpoint='HATCH GRAPHITE-01',work_item='G-A',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,observations=observations,
 decisions=dict(poses='pure CatPoses: open > sleepy > hover > rest; hover and the menu wake; input elsewhere restarts the inactivity timer without waking (movement tied to interaction)',
  motion='one QVariantAnimation of MOVE_MS over six pose numbers; Reduce motion sets the numbers at once',startup='QSplashScreen from launch.main before qt_app is imported; closed by the first other window shown; no fade'),
 jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,
 owner_host_acceptance=False,acceptance_claimed=False,clean_close=True)
(OUT/'graphite-brand-ui.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],checks=len(checks),captures=len(captures)),ensure_ascii=False),flush=True)
for guard in (question,detached,system,popen,submission,launcher,provider):guard.stop()
