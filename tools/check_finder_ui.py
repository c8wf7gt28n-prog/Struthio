"""Actual Qt check of the Finder workspace (HATCH AGENT-01, UI-04), offscreen: Home is a Finder window in the Macintosh shape.

The mechanical steps: Home shows the Finder with Today first and the TodayPage inside it; choosing a Machine storage row
in the left column fills the centre with that folder's listing through ledger.browse (nothing patched: the status line's
count is compared with an independent ledger.browse read); a double-click descends; the three views show the same names;
the preview pane shows a text file's first lines and an image's size; Backspace goes up and the path bar follows; back
and forward work; the hidden toggle changes the count; a 600-entry folder shows the truncated line and the word that
shows up to 2000; the context menu holds only words that look, open, copy or ask; Enter on a text file opens it in the
editor tab and Home closes; the left column never steals the centre from the open editor; the Today row brings the
Finder's Today place back. Captures at 1920×1200 (List, Icons, Columns with the preview open) and 1366×768. GRAPHITE-01
(G-B): every word in the window whole (tools/ui_fit: each visible label's, button's and List column title's words fit the
room the style gives them; outside the head and the centre only ui_fit.PENDING, words awaiting edits in other files) and
nothing in the centre scrolls sideways (the Columns view and a text preview's lines do by design) at 1920×1200, 1366×768
and 18 pt; under its width the toolbar folds Hidden, Places, Preview, then the views into ⋯, whose rows still work; the List
folds Kind, Date Modified, Size, and its widths grow with the interface; a deep path folds its leading folders into … and a
last folder too long for the foot elides in the middle; Today's Continue row keeps a deep document's name whole. Disposable
profile and Concern; Kernel.launch, Kernel.submit and the provider request are held; no process may start; nothing on
disk is changed by the Finder. Nothing here is owner-host, live-model or physical acceptance.
"""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_FINDER_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/finder')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='ledger-agent01-finder-ui-'))
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QProcess,QPoint
from PySide6.QtGui import QImage,QColor,QPainter
from PySide6.QtWidgets import QMessageBox,QMenu,QPushButton,QToolButton,QLabel
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow,CodeEditor
from workbench import locations,clip,files_service
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench.shell2 import TodayPage
from workbench.finder_qt import FinderPage,TODAY,VIEWS,FOLD_WORDS,LIST_WIDTHS
from workbench import ledger_control
import ui_fit
provider=patch.object(clip,'_request',side_effect=AssertionError('No provider request')).start()
launcher=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')).start()
submission=patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')).start()
question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes).start()
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
# The folders the check looks at, made before the window exists (the Finder itself writes nothing).
DEMO=root/'Finder demo';DEMO.mkdir();(DEMO/'drawings').mkdir();(DEMO/'archive').mkdir()
NOTES='\n'.join('Line %d of the notes: the ostrich pen needs %d posts.'%(i,i*3) for i in range(1,13))+'\n'
(DEMO/'notes.txt').write_text(NOTES);(DEMO/'plan.md').write_text('# Plan\n\nFence first.\n');(DEMO/'.quiet').write_text('hidden\n')
for name in ('gate.gbr','post.step','list.csv'):(DEMO/'drawings'/name).write_text(name+'\n')
image=QImage(320,200,QImage.Format_RGB32);image.fill(QColor('#f6f3eb'));painter=QPainter(image);painter.setBrush(QColor('#f8edc9'));painter.setPen(QColor('#504d46'));painter.drawEllipse(40,30,240,140);painter.end()
assert image.save(str(DEMO/'picture.png'),'PNG')
MANY=root/'Many files';MANY.mkdir()
DEEP=root/'Survey'/'gate posts'/'north field'/'second survey'/'measured on site';DEEP.mkdir(parents=True)  # a path deeper than the foot at 1366 and 18 pt
(DEEP/'gate posts.md').write_text('# Gate posts\n')  # Today's Continue row for a document five folders deep (step 11)
LONG=root/'Survey of the north field gate posts, measured on site with the new level and the long tape';LONG.mkdir()  # a last folder wider than the foot at 1366
for i in range(600):(MANY/('row%03d.txt'%i)).write_text('')
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge
FILES=files_service.root(k);(FILES/'kept.txt').write_text('A file kept in Files.\n')
import platform;platform.processor()
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[]
def settle(ms=30):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(3):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def capture(name,note):
 w.operations_panel.refresh();settle();pix=w.grab();target=OUT/name;assert pix.save(str(target),'PNG')
 captures.append(dict(file=name,note=note,mode='ACTUAL_QT_WINDOW_GRAB',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[w.width(),w.height()]))
def five_parts():
 """The frame's five parts: left column, Ledger Head, centre, right column, typing strip, with the fixed Trash (the Stop control's place in the head is UI-03's check)."""
 parts=(w.nav_dock,w.ribbon_dock,w.central_stack,w.sim_dock,getattr(w,'type_dock',None))
 return all(p is not None and p.isVisible() for p in parts) and w.trash_can.isVisible()
def snapshot(folder):
 """What is on disk, to prove the Finder changed nothing."""
 out={}
 for base,dirs,files in os.walk(folder):
  dirs[:]=[d for d in dirs if not d.startswith('.')]   # the Kernel's own state under .ledger is the window's, not the Finder's
  for name in files:
   p=Path(base)/name
   try:st=p.lstat();out[str(p)]=(st.st_size,round(st.st_mtime,3))
   except OSError:pass
 return out
def row_of(tree,item):
 tree.scrollToItem(item);return tree.visualItemRect(item).center()
def double_click(view,point):
 """A real double-click: press, release, then the double-click event (the view opens only an index it saw pressed)."""
 QTest.mouseClick(view.viewport(),Qt.LeftButton,Qt.NoModifier,point);QTest.mouseDClick(view.viewport(),Qt.LeftButton,Qt.NoModifier,point)
def list_item(page,name):
 return next(page.list.topLevelItem(i) for i in range(page.list.topLevelItemCount()) if page.list.topLevelItem(i).data(0,Qt.UserRole+11)['name']==name)
def align(times=3):
 for _ in range(times):w.type_bar.align();settle()
def ui_pt(points):
 row=next(r for r in ledger_control.settings(k)['settings'] if r['key']=='reading.ui_pt')
 call('ledger.settings.set',{'key':'reading.ui_pt','value':float(points),'expected_revision':row['revision']});bridge.sync_profile(force=True);settle(40);align()
fits={}
def whole(step):
 """G-B: every word in the window whole (labels, buttons and the List's column titles; a word squeezed to nothing or pushed
 out sideways counts) and nothing in the centre scrolling sideways (the Columns view and a text preview's lines scroll
 sideways by design). Outside the head and the centre only ui_fit.PENDING may fall short, by at most its bold shortfall."""
 page.fit_bar();page.fit_columns();page.fit_path();settle()
 clipped,elsewhere=ui_fit.regions(w,w.ribbon_dock,w.central_stack);sideways=ui_fit.side_scrolls(w.central_stack,allow=(page.columns,page.preview.text))
 fits[step]=dict(size=[w.width(),w.height()],folded=list(page.folded),list_hidden=[page.list.headerItem().text(c) for c in (1,2,3) if page.list.isColumnHidden(c)],
  path_folded=[b.text() for b in page.path_bar.findChildren(QPushButton) if b.isHidden()] if page.path_bar.isVisible() else [],place=page.name.text(),clipped=clipped,sideways=sideways,elsewhere=elsewhere)
 assert not clipped and not sideways and not ui_fit.unexplained(elsewhere),(step,ui_fit.describe(clipped+sideways+ui_fit.unexplained(elsewhere)))
 return fits[step]
def continue_whole(step):
 """Today's Continue row for a document five folders deep: the name stays a whole link beside its folder (which wraps)."""
 page.today.fill();settle();link=next(l for l in page.today.continue_.findChildren(QLabel) if 'go' in getattr(l,'_actions',{}) and ui_fit.plain(l)=='gate posts.md')
 assert link.isVisible() and link.width()>=link.minimumSizeHint().width()>0,(step,link.width(),link.minimumSizeHint().width())
 fit=whole(step);fit['continue_link']=[link.width(),link.minimumSizeHint().width()];return fit
before_disk=snapshot(root)
w.resize(1920,1200);w.show();settle();bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
with k.db() as db:jobs_before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
# 01 · Home is the Finder, Today first, the TodayPage inside it
w.show_start();settle();align()  # the context word follows at the bar's next pass (its own 500 ms timer); ask for it now
page=w._empty_home_page;assert isinstance(page,FinderPage) and w.finder is page and w.central_stack.currentWidget() is page and w._home_active,type(page).__name__
assert isinstance(page.today,TodayPage) and page.stack.currentWidget() is page.today and page.place==TODAY and page.name.text()=='Today'
assert page.today.arrived is not None and page.today.waiting is not None and page.today.continue_ is not None and page.today.slate is not None  # the four cards, as objects (their titles are the integrator's words)
assert page.layout().contentsMargins().right()==0 and five_parts() and w.type_bar.context_text=='Home',(w.type_bar.context_text,)
places=dict(page.places());assert places['Today']==TODAY and places['Files']==str(FILES) and places['Workspace']==str(root) and 'Ingress' in places and 'Egress' in places,places
assert places['Ingress']==call('receiving.status')['inbox'] and places['Egress']==str(FILES/files_service.EXPORTS) and places['Program']==str(locations.program(root))
check('01 Home shows the Finder (FinderPage) with Today as its first place and the TodayPage inside it (page.today, four cards present); the places read Today · Files · Ingress · Egress · Workspace · Program%s; five parts visible; the context word reads Home'%(' · %d mount(s)'%(len(places)-6) if len(places)>6 else ''))
capture('Ledger_Slate_AGENT_01_Finder_01_Today_1920.png','Home: the Finder with Today as its first place; the toolbar above (back, forward, place, views, Hidden, Preview, Places); both columns, the Ledger Head and the typing strip unchanged')
# 02 · a Machine storage row in the left column fills the centre with that folder through ledger.browse
w.settings_navigator.show_machine();settle();machine=w.machine_page;assert machine.build(force=True);settle()
item=machine.items['storage:path:workspace'];machine.tree.setCurrentItem(item);tree=machine.tree;point=row_of(tree,item)
QTest.mouseClick(tree.viewport(),Qt.LeftButton,Qt.NoModifier,point);settle()
assert page.place==str(root) and page.stack.currentWidget() is page.browser and w._home_active,(page.place,str(root))
independent=call('ledger.browse',{'path':str(root)})
assert page.status.text().startswith('%d item'%independent['count']) and 'available on this disk' in page.status.text() and 'observed from this computer' in page.status.text(),page.status.text()
assert set(page.names())=={e['name'] for e in independent['entries']} and page.names()==[e['name'] for e in independent['entries']],(page.names(),[e['name'] for e in independent['entries']])
assert page.path_words()[-1]==root.name and page.name.text()=='Workspace',(page.path_words(),page.name.text())
check('02 Clicking the Machine view’s storage row for the workspace filled the centre with that folder through ledger.browse: status “%s” matches an independent read (%d items), the names and order agree, the path bar ends in %s'%(page.status.text(),independent['count'],root.name))
# 03 · double-click descends; the three views show the same names; captures with the preview open
demo=list_item(page,DEMO.name);point=row_of(page.list,demo);double_click(page.list,point);settle()
assert page.place==str(DEMO) and page.path_words()[-2:]==[root.name,DEMO.name],(page.place,page.path_words())
expected=['archive','drawings','notes.txt','picture.png','plan.md']
assert page.names('list')==expected,page.names('list')
page.set_preview(True);assert page.preview.isVisible() and page.preview_visible
capture('Ledger_Slate_AGENT_01_Finder_02_List_1920.png','The demo folder as a List (Name · Date Modified · Size · Kind, folders first) with the preview pane and the path bar below')
page.set_view('icons');settle();assert page.views.currentWidget() is page.icons and page.names('icons')==expected
capture('Ledger_Slate_AGENT_01_Finder_03_Icons_1920.png','The same folder as Icons: tiles with the kind word, the preview open')
page.set_view('columns');settle();assert page.views.currentWidget() is page.columns and page.names('columns')==expected
assert [p for p,_ in page.columns.columns][-1]==str(DEMO) and len(page.columns.columns)>=2,[p for p,_ in page.columns.columns]
capture('Ledger_Slate_AGENT_01_Finder_04_Columns_1920.png','The same folder as Columns (Miller columns from the Workspace place; the preview is the last column)')
page.set_view('list');settle()
check('03 Double-click descended into %s; List, Icons and Columns show the same five names in the same order (%s) from one listing'%(DEMO.name,', '.join(expected)))
# 04 · the preview: a text file's first lines, an image's size
assert page.select_name('notes.txt');settle()
assert page.preview.text.isVisible() and page.preview.text.toPlainText().splitlines()[:2]==NOTES.splitlines()[:2] and page.preview.text_lines==12,(page.preview.text_lines,page.preview.text.toPlainText()[:60])
assert page.preview.text.isReadOnly() and 'Plain text' in page.preview.facts.text() and 'Size: ' in page.preview.facts.text() and 'Modified: ' in page.preview.facts.text()
assert page.select_name('picture.png');settle()
assert page.preview.image_size==(320,200) and '320 × 200' in page.preview.facts.text() and not page.preview.text.isVisible() and page.preview.picture.pixmap() is not None and not page.preview.picture.pixmap().isNull()
assert page.select_name('drawings');settle();assert page.preview.facts.text().startswith('Folder · 3 items'),page.preview.facts.text()
check('04 The preview pane shows notes.txt’s first 12 lines read-only with its kind, size and dates; picture.png as a 320 × 200 thumbnail; the drawings folder as “3 items” with the disk space')
capture('Ledger_Slate_AGENT_01_Finder_05_Preview_1920.png','The preview pane for a folder, after the text and the picture were previewed')
# 05 · Backspace goes up and the path bar follows; back and forward
page.list.setFocus();settle();QTest.keyClick(page.list,Qt.Key_Backspace);settle()
assert page.place==str(root) and page.path_words()[-1]==root.name and (page.current_entry() or {}).get('name')==DEMO.name,(page.place,page.path_words(),page.current_entry())
assert page.back() and page.place==str(DEMO);assert page.forward() and page.place==str(root)
QTest.keyClick(page.list,Qt.Key_Left,Qt.AltModifier);settle();assert page.place==str(DEMO)
QTest.keyClick(page.list,Qt.Key_Right,Qt.AltModifier);settle();assert page.place==str(root)
steps=0
while page.back():steps+=1
assert steps>=3 and page.place==TODAY and page.stack.currentWidget() is page.today and not page.back_button.isEnabled(),(steps,page.place)   # the history begins at Today
while page.forward():pass
assert page.place==str(root) and not page.forward_button.isEnabled()
check('05 Backspace went up to the workspace with the demo folder selected and the path bar following; back and forward (words and Alt Left / Alt Right) walk the history, which begins at Today')
# 06 · hidden toggle changes the count
page.go(str(DEMO));settle();count_shown=page.listing['count'];assert count_shown==5
QTest.mouseClick(page.hidden_button,Qt.LeftButton);settle()
assert page.hidden and page.listing['count']==6 and '.quiet' in page.names() and page.status.text().startswith('6 items'),(page.listing['count'],page.names())
QTest.mouseClick(page.hidden_button,Qt.LeftButton);settle();assert not page.hidden and page.listing['count']==5 and '.quiet' not in page.names()
check('06 The Hidden word changes the count from 5 to 6 (.quiet appears) and back; every listing came through ledger.browse')
# 07 · a 600-entry folder shows the truncated line, and the word shows up to 2000
page.go(str(MANY));settle()
assert page.listing['truncated'] and len(page.entries)==500 and page.listing['count']==600 and page.status.text().startswith('500 of 600 items shown'),page.status.text()
assert page.truncated_line.isVisible() and 'show up to 2000' in page.truncated_line.text(),page.truncated_line.text()
page.truncated_line.linkActivated.emit('more');settle()
assert page.limit==2000 and len(page.entries)==600 and not page.listing['truncated'] and page.status.text().startswith('600 items') and page.truncated_line.isHidden(),page.status.text()
check('07 A 600-entry folder stopped at 500 with the line offering “show up to 2000”; the word raised the bound and the 600 items came through one more ledger.browse')
page.limit=500
# 08 · the context menu's words: nothing that changes a file
page.go(str(DEMO));settle();notes=next(e for e in page.entries if e['name']=='notes.txt');menu=page.menu_for(notes)
words=[a.text() for a in menu.actions() if not a.isSeparator()]
assert words==['Open','Open in viewer','Copy path','Ask Graphite about this file','Nothing changes here · Files keeps its own changes'],words
forbidden=('New','Rename','Delete','Move','Trash','Duplicate','Paste','Cut')
assert not any(any(word.startswith(f) for f in forbidden) for word in words)
folder_words=[a.text() for a in page.menu_for(next(e for e in page.entries if e['name']=='drawings')).actions() if not a.isSeparator()]
assert folder_words[:1]==['Open'] and 'Open in viewer' not in folder_words and 'Ask Graphite about this folder' in folder_words
page.go(str(FILES));settle();kept=next(e for e in page.entries if e['name']=='kept.txt');files_words=[a.text() for a in page.menu_for(kept).actions() if not a.isSeparator()]
assert files_words==['Open','Open in viewer','Show in Files','Copy path','Ask Graphite about this file','Change it in Files'],files_words
page.copy_path(str(DEMO/'notes.txt'));from PySide6.QtGui import QGuiApplication;assert QGuiApplication.clipboard().text()==str(DEMO/'notes.txt')
check('08 The context menu reads Open · Open in viewer · Copy path · Ask Graphite about this file (and Show in Files · Change it in Files inside Files); none of its words creates, renames, moves or deletes')
# 09 · Enter on a text file opens it in the editor tab; Home closes
page.go(str(DEMO));settle();assert page.select_name('notes.txt');page.list.setFocus();settle()
QTest.keyClick(page.list,Qt.Key_Return);settle()
editor=w.tabs.currentWidget();assert isinstance(editor,CodeEditor) and Path(editor.path).resolve()==(DEMO/'notes.txt').resolve(),type(editor).__name__
assert not w._home_active and w.central_stack.currentWidget() is w.workspace_split and editor.toPlainText()==NOTES
check('09 Enter on notes.txt opened it in the editor tab (CodeEditor) and _close_start happened: the centre is the workspace, Home inactive')
# 10 · the left column never steals the centre from the open editor; Home returns to the Finder's place; the Today row brings Today
place_before=page.place;machine.activate(machine.items['storage:path:program']);settle()
assert w.tabs.currentWidget() is editor and not w._home_active and page.place==place_before
w.show_start();settle();assert w._home_active and w.central_stack.currentWidget() is page and page.place==str(DEMO)
today_row=next(w.nav.topLevelItem(i) for i in range(w.nav.topLevelItemCount()) if w.nav.topLevelItem(i).text(0)=='Today')
w.nav.setCurrentItem(today_row);settle();assert page.place==TODAY and page.stack.currentWidget() is page.today
machine.activate(machine.items['storage:path:program']);settle();assert page.place==str(locations.program(root)) and page.name.text()=='Program'
saved=w.session.state.get('finder');assert saved and saved['place']==str(locations.program(root)) and saved['view']=='list' and saved['preview'] is True,saved
check('10 With the editor open a storage row changed nothing in the centre; Home returned at the Finder’s last place; selecting the Today row showed Today; the Program row showed the program folder; the place and view are written to session.state[finder]')
# 11 · compact size, every word whole (G-B)
w.session.state['recent']=[str((DEEP/'gate posts.md').relative_to(root))]
page.go(TODAY);settle();continue_whole('1920 Today');page.go(str(DEMO));page.set_view('list');settle()
wide=whole('1920 List');assert not wide['folded'] and not wide['list_hidden'] and page.more_button.isHidden(),wide
w.resize(1366,768);settle(60);align();page.go(str(DEMO));page.set_view('list');settle();assert five_parts() and page.list.isVisible() and page.preview.isVisible()
compact=whole('1366 List');assert compact['folded'] and page.more_button.isVisible() and page.more_button.toolTip().startswith('More: '),compact
assert all(not b.isVisible() for key in compact['folded'] for b in {'hidden':[page.hidden_button],'preview':[page.preview_button],'places':[page.places_button],'views':list(page.view_buttons.values())}[key])
page.more_button.menu().aboutToShow.emit();rows=[a.text() for a in page.more_button.menu().actions() if not a.isSeparator()]
assert 'Show hidden files' in rows,rows
hidden_row=next(a for a in page.more_button.menu().actions() if a.text()=='Show hidden files');hidden_row.trigger();settle()
assert page.hidden and page.listing['count']==6,'the folded word works from ⋯';page.set_hidden(False);settle();assert page.listing['count']==5
capture('Ledger_Slate_AGENT_01_Finder_06_Compact_1366.png','The Finder’s List with the preview at 1366 by 768: every word whole; %s folded into ⋯; the List shows %s; all five parts visible'%(', '.join(FOLD_WORDS[f] for f in compact['folded']),', '.join(c for c in ('Name','Date Modified','Size','Kind') if c not in compact['list_hidden'])))
page.set_view('columns');settle();whole('1366 Columns');capture('Ledger_Slate_AGENT_01_Finder_07_Columns_1366.png','Columns at 1366 by 768 (the Columns view scrolls sideways by design)')
page.set_view('list');page.go(TODAY);settle();continue_whole('1366 Today')
page.go(str(LONG));settle();whole('1366 long folder name');last=[b for b in page.path_bar.findChildren(QPushButton) if b.isVisible()][-1]
elided=last.text();assert page.path_words()[-1]==LONG.name and '…' in elided and last.toolTip()==str(LONG),(elided,page.path_words()[-1:])
page.go(TODAY);settle()
check('11 1366×768: the list, the preview and the five parts stay visible; every word whole and nothing in the centre scrolls sideways at 1920×1200 and 1366×768: the toolbar folds %s into ⋯ (whose Show hidden files row changed the count 5 → 6 and back), the List folds %s; Today’s Continue row keeps a document five folders deep a whole link; a %d-character folder name elides in the middle at the foot (“%s”, whole in its tooltip)'%(' · '.join(FOLD_WORDS[f] for f in compact['folded']),' · '.join(compact['list_hidden']) or 'nothing',len(LONG.name),elided))
# 11b · 18 pt at 1366×768: the toolbar folds further, a deep path folds its leading folders into …
ui_pt(18);page.go(str(DEEP));settle();align()
large=whole('1366 18pt deep path');more=next(b for b in page.path_bar.findChildren(QToolButton));assert more.isVisible() and large['path_folded'],large
words=page.path_words();shown=[b.text() for b in page.path_bar.findChildren(QPushButton) if b.isVisible()]
assert words[-1]==DEEP.name and shown and shown[-1]==DEEP.name and len(more.menu().actions())==len(large['path_folded']),(words,shown,large)
capture('Ledger_Slate_GRAPHITE_01_Finder_08_Deep_Path_18pt_1366.png','18 pt at 1366 by 768: the toolbar folds %s into ⋯, the List keeps Name, the path bar folds %d leading folders into …, the preview scrolls down; every word whole'%(', '.join(FOLD_WORDS[f] for f in large['folded']),len(large['path_folded'])))
page.go(TODAY);settle();continue_whole('1366 18pt Today');page.today.scroller.ensureWidgetVisible(page.today.continue_);settle();capture('Ledger_Slate_GRAPHITE_01_Finder_09_Today_18pt_1366.png','Today at 18 pt and 1366 by 768: one column of cards, nothing sideways, every word whole; the Continue row keeps the name gate posts.md whole beside its five folders, which wrap')
w.resize(1920,1200);settle(60);align();page.go(str(DEMO));page.set_view('list');settle()
wide18=whole('1920 18pt List');wide18['date_width']=page.list.columnWidth(1)
assert not wide18['list_hidden'] and wide18['date_width']>=round(LIST_WIDTHS[1]*18/14),wide18  # Date Modified grows with the interface
capture('Ledger_Slate_GRAPHITE_01_Finder_10_List_18pt_1920.png','The List at 18 pt and 1920 by 1200: Date Modified %d px wide (120 at 14 pt, scaled with the interface), its title and the dates whole'%page.list.columnWidth(1))
ui_pt(14);w.resize(1920,1200);settle(60);align();page.go(str(DEMO));page.set_view('list');settle()
assert page.list.columnWidth(1)==LIST_WIDTHS[1],page.list.columnWidth(1)
back=whole('1920 back at 14pt');assert not back['folded'] and not back['list_hidden'],back
check('11b 18 pt at 1366×768: every word whole with %s folded and a deep path showing %s after …; at 18 pt and 1920×1200 the List keeps all four columns with Date Modified %s px wide; back at 14 pt and 1920×1200 every word unfolds and Date Modified is %d px again'%(' · '.join(FOLD_WORDS[f] for f in large['folded']),' › '.join(shown),wide18['date_width'],LIST_WIDTHS[1]))
# 12 · nothing written, nothing started
after_disk=snapshot(root);changed=[p for p in before_disk if before_disk[p]!=after_disk.get(p)]
assert not changed,changed[:5]
with k.db() as db:jobs_after=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
assert jobs_after==jobs_before and not launcher.called and not submission.called and not provider.called and not popen.called and not detached.called
check('12 Every file the check made is byte-for-byte and time-for-time as before (%d files compared); zero jobs, launches, provider requests or processes'%len(before_disk))
report=dict(schema='ledger.agent01-finder-ui/1',checkpoint='HATCH AGENT-01 · fit assertions GRAPHITE-01 G-B',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,
 places=list(places),listing_operation='ledger.browse',bound={'default':500,'more':2000},views=list(VIEWS),words_whole=fits,
 real_job_submissions=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,processes_started=0,files_changed_by_finder=0,
 acceptance_claimed=False,note='Mechanical offscreen evidence of the Finder workspace: Today first, the left column as sidebar, read-only by design, the 500/2000 bound. The owner display remains open.')
w.close();app.processEvents()
(OUT/'finder-ui.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=report['state'],checks=len(checks),captures=len(captures))))
