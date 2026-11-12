"""Actual Qt check of GRAPHITE-01 G-C, the owner's public rename (D32), offscreen: Graphite is the one public name of the
workspace and its AI, and the menu is the menu.

Steps, at 1920 by 1200 and again at 1366 by 768 (14 pt): Today with the head and the strip; the menu opened by one click on the
cat; the right column's face, now titled Graphite; the settings roots, shown as Workspace and Assistant, with a setting whose
definition still says Slate shown in Graphite's words; the left column's existing views and the concern dossiers of the seed
items 'ledger' and 'operations'. The profile is made as before the rename: its catalog keeps the seed words the old code wrote
('Ledger', 'Ledger maintenance, …'), and the cabinet's 'ledger' drawer and its memory drawer are expanded. At each step every
visible word of the window is read (labels, buttons, tab titles, menus, and the rows, tooltips and header titles of every
visible tree and list): none says Slate, Ledger or Hatch as a word (the kept exceptions are listed in KEPT), the window title
says Graphite, and tools/ui_fit finds every word in the window whole (ui_fit.PENDING is empty). Disposable profile and Concern; Kernel.launch,
Kernel.submit and the provider request are held; after the window exists no process, shell command or detached program may
start. Nothing here is owner-host acceptance.
"""
import hashlib,json,os,re,subprocess,sys,tempfile
import shiboken6
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_RENAME_CAPTURE_DIR',str(PROGRAM/'build/ui_checks/rename')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='graphite01-rename-ui-'))
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
from PySide6.QtCore import Qt,QPoint,QProcess,QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QAbstractButton,QAbstractItemView,QHeaderView,QLabel,QListView,QMenu,QMessageBox,QTabBar,QTreeView
from PySide6.QtTest import QTest
import ui_fit
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,version
from workbench.engineering_kernel import Kernel
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
# A profile made before the rename (V01 W1): the catalog keeps the seed rows the old code wrote; nothing migrates them, and while
# untouched they are shown in Graphite words (concern_catalog.shown).
import sqlite3
from sdk.cli.arc1cli.concern_catalog import Catalog
CATALOG=RUN/'profile/concern/catalog.sqlite3';Catalog(CATALOG)
with sqlite3.connect(CATALOG) as db:
 db.execute("UPDATE objects SET title='Ledger' WHERE id='ledger'");db.execute("UPDATE objects SET summary='Ledger maintenance, installation and recovery.' WHERE id='operations'")
OLD=re.compile(r'\b(Slate|Ledger|Hatch)\b',re.I)  # in capitals too (section lines such as NICE · GRAPHITE WORK)
# Words a person may still read on purpose: the Files/Slate folder keeps its name on disk (and so does a file's path), and an
# identity shown as it is stored, always lowercase and joined by . : / or - (an operation, event schema or catalogue id in a
# row's tooltip: ledger.open, arc.ledger-event/2, catalog:ledger). A public word is never written that way.
KEPT=re.compile(r'Files/Slate|Files › Slate|the Slate folder|\b[a-z0-9_]+(?:[.:/-][a-z0-9_]+)+\b')
checks=[];captures=[];observations={};PREFIX='Graphite_01_Rename_'
def check(text):checks.append(text);print(text,flush=True)
app=make_app([])
root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);bridge=w.ledger_bridge;bar=w.type_bar;hatch=bar.hatch;menu=hatch.menu()
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
def view_words(view):
 """A visible tree's or list's words: its accessible name, its header titles, and each row's text and tooltip in every shown
 column; a tree's children only under an expanded row (what a person can see by scrolling, not what is folded away)."""
 out=[view.accessibleName(),view.toolTip()];model=view.model()
 if model is None:return out
 try:count=model.columnCount(view.rootIndex())
 except TypeError:count=1  # a list model keeps columnCount private: one column
 tree=isinstance(view,QTreeView);columns=[c for c in range(count) if not (tree and view.isColumnHidden(c))]
 if tree and not view.isHeaderHidden():out+=[str(model.headerData(c,Qt.Horizontal) or '') for c in columns]
 def rows(parent):
  for r in range(model.rowCount(parent)):
   if (tree and view.isRowHidden(r,parent)) or (isinstance(view,QListView) and view.isRowHidden(r)):continue
   for c in columns:
    index=model.index(r,c,parent)
    out.extend(v for v in (index.data(Qt.DisplayRole),index.data(Qt.ToolTipRole)) if isinstance(v,str))
   first=model.index(r,0,parent)
   if tree and model.hasChildren(first) and view.isExpanded(first):rows(first)
 rows(view.rootIndex());return out
def shown_words(root):
 """Every visible word under root a person reads: labels, buttons, tab titles, a menu's rows and titles, and the rows of every
 visible tree and list (view_words)."""
 out=[]
 for widget in [root]+root.findChildren(QLabel)+root.findChildren(QAbstractButton)+root.findChildren(QTabBar)+root.findChildren(QAbstractItemView):
  if not widget.isVisible():continue
  if isinstance(widget,QTabBar):out+=[widget.tabText(i) for i in range(widget.count())]
  elif isinstance(widget,(QLabel,QAbstractButton)):out.append(ui_fit.plain(widget));out.append(widget.toolTip());out.append(widget.accessibleName())
  elif isinstance(widget,QAbstractItemView) and not isinstance(widget,QHeaderView):out+=view_words(widget)
 if isinstance(root,QMenu):
  out.append(root.accessibleName())
  for a in root.actions():out+=[a.text(),a.toolTip()]+([a.menu().title(),a.menu().accessibleName()] if a.menu() else [])
 return [t for t in out if t]
def old_words(texts):return sorted({t for t in texts if OLD.search(KEPT.sub('',t))})
def record(name,note,pix,mode='ACTUAL_QT_WINDOW_GRAB'):
 target=OUT/(PREFIX+name);image=pix.toImage();assert image.save(str(target),'PNG'),name
 captures.append(dict(file=PREFIX+name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[image.width(),image.height()]))
def fit(step):
 mine,elsewhere=ui_fit.regions(w,w.ribbon_dock,w.central_stack)
 strip=ui_fit.whole_words(bar)
 odd=ui_fit.unexplained(elsewhere)  # the whole window: ui_fit.PENDING is empty (the checked words keep their bold room)
 observations.setdefault('fit',{})[step]=dict(head_and_centre=ui_fit.describe(mine) or 'whole',strip=ui_fit.describe(strip) or 'whole',elsewhere=ui_fit.describe(elsewhere) or 'whole')
 assert not mine and not strip and not odd,(step,ui_fit.describe(mine+strip+odd))
def window_words(step,*extra):
 texts=shown_words(w)+[w.windowTitle()]+[t for e in extra for t in shown_words(e)]
 left=old_words(texts);observations.setdefault('old_words',{})[step]=left
 assert not left,(step,left)
 assert 'Graphite' in w.windowTitle() and not OLD.search(w.windowTitle()),w.windowTitle()
 return texts
w.resize(1920,1200);w.show();settle(120);bridge.timer.stop();hatch.lifecycle.timer.stop();align();w.activateWindow();settle()
w.show_start();settle();align();home=w._empty_home_page
cabinet=w.cabinet_page;cabinet.set_legacy(False);cabinet.refresh(force=True);settle()
for ident in ('cabinet:concern','catalog:ledger','memory:root'):  # the drawers a person opens first: the workspace's own and its memory
 assert ident in cabinet.items,(ident,sorted(cabinet.items)[:30]);cabinet.items[ident].setExpanded(True)
settle()
drawers={i:cabinet.items[i].text(0) for i in ('catalog:ledger','memory:root')}
assert drawers=={'catalog:ledger':'Graphite','memory:root':'Graphite memory'},drawers
observations['cabinet']=dict(drawers=drawers,stored_title='Ledger (a profile made before the rename; the row is not migrated)')
for size,tag in (((1920,1200),'1920'),((1366,768),'1366')):
 w.resize(*size);settle(80);align();home.go('today');settle();align()
 # 01 · Today, the head and the strip ------------------------------------------------------------------------------------------
 top=w.shell2.top;gs=w.global_search
 assert version.NAME=='Graphite' and gs.accessibleName()==gs.toolTip()=='Graphite' and top.wordmark.text()=='Graphite' and top.mark.accessibleName()=='Graphite'
 assert top.slate_switch.text() in ('AI ON','AI OFF') and top.slate_switch.accessibleName()=='Enable or disable new Graphite AI activity'
 assert bar.targets['slate'].text()=='Assignment' and bar.targets['slate'].accessibleName()=='Writing line mode: Assignment' and hatch.accessibleName()==hatch.toolTip()=='Open programs'
 assert home.today.slate.isVisible() and any(ui_fit.plain(l)=='Graphite' for l in home.today.slate.findChildren(QLabel)),'Today\'s card is titled Graphite'
 texts=window_words('today_'+tag);fit('today_'+tag)
 observations['head_'+tag]=dict(title=w.windowTitle(),mark=gs.accessibleName(),wordmark=[top.wordmark.text(),top.wordmark.isVisible()],ai_switch=top.slate_switch.text(),brain=top.brain.text(),strip=[b.text() for b in bar.targets.values()])
 record('01_Today_%s.png'%tag,'%s: Today with the head (the point named Graphite, the AI switch, the Nice menu) and the strip (the cat and the writing line\'s modes Assignment · Shell · Search · Log); the title says Graphite; no visible word says Slate, Ledger or Hatch.'%size[0],w.grab())
 check('%s 01 Today at %d by %d: title “%s”, the head and the strip say Graphite (the AI switch reads %s), %d visible words read, none Slate, Ledger or Hatch; every head, centre and strip word whole'%(tag,size[0],size[1],w.windowTitle(),top.slate_switch.text(),len(texts)))
 # 02 · the menu, opened by one click on the cat ----------------------------------------------------------------------------------
 rec={}
 def inside():
  try:
   rec['visible']=menu.isVisible();rec['rows']=menu.words();rec['old']=old_words(shown_words(menu)+[menu.accessibleName()])  # D2: the cat's programs list
   pix=w.grab();painter=QPainter(pix);painter.drawPixmap(w.mapFromGlobal(menu.mapToGlobal(QPoint(0,0))),menu.grab());painter.end();rec['pix']=pix
  except Exception as exc:rec['error']=repr(exc)
  finally:
   QTest.keyClick(menu,Qt.Key_Escape);settle(5)
   if menu.isVisible():menu.hide()
 QTimer.singleShot(120,inside);QTest.mouseClick(hatch,Qt.LeftButton);settle(80)
 assert rec.get('visible') and not rec.get('error') and not rec['old'],rec
 assert menu.accessibleName()=='Programs' and rec['rows'][-2:]==['—','Explore the workshop'],rec['rows']
 system_list=w.shell2.top.nice.open(False);settle();system_words=system_list.words();system_old=old_words(shown_words(system_list)+[system_list.accessibleName()]);system_list.close_menu();settle()
 assert not system_old and 'Graphite services' in system_words and system_words[-3] in ('Exit Graphite','Return to Debian') and system_list.accessibleName()=='System menu',(system_words,system_old)
 record('02_Menu_%s.png'%tag,'%s: the cat\'s programs list opened by one click on the cat (HATCH DESK D2): every program and capability A to Z, then Explore the workshop; accessible name Programs. The System menu (read too) holds Graphite services and Exit Graphite.'%size[0],rec['pix'],'ACTUAL_QT_WINDOW_AND_VISIBLE_POPUP_GRABS')
 observations['menu_'+tag]=[r for r in rec['rows'] if r];observations['system_menu_'+tag]=system_words
 check('%s 02 One click on the cat opened the programs list (accessible name Programs): %s; the System menu reads %s; no row, title or tooltip of either says Slate, Ledger or Hatch'%(tag,' · '.join(r for r in rec['rows'] if r and r!='—'),' · '.join(r for r in system_words if r!='—')))
 # 03 · the right column's face, titled Graphite -------------------------------------------------------------------------------------
 w.shell2.show_slate_face();settle();align();face=w.shell2.face
 tabs=w.console_pages;names=[tabs.tabText(i) for i in range(tabs.count())]
 assert face.isVisible() and face.signature.text()=='Graphite' and 'Graphite' in names and 'Slate' not in names and w.shell2.slate_button.text()=='Conversation' and face.input.accessibleName()=='Message Graphite',(names,face.signature.text())
 window_words('face_'+tag);fit('face_'+tag)
 record('03_Face_%s.png'%tag,'%s: the right column\'s face, titled Graphite (signature and page), its message passage named Message Graphite; its tab is Conversation (HATCH DESK D1b).'%size[0],w.grab())
 check('%s 03 The face in the right column is titled Graphite (signature, page “Graphite”, Message Graphite) under the Conversation tab (D1b); no visible word says Slate, Ledger or Hatch'%tag)
 w.shell2.show_operations_face();settle()
 # 04 · the settings roots: Workspace and Assistant ------------------------------------------------------------------------------------
 tab=bridge.show_settings(key='stacy.enabled');settle();align();nav=w.settings_navigator
 roots=[nav.tree.topLevelItem(i).text(0) for i in range(nav.tree.topLevelItemCount())]
 assert roots==['Workspace','Assistant'],roots
 assert tab.heading.text()=='Allow new Graphite AI activity' and tab.breadcrumb.text()=='SETTINGS / ASSISTANT / BEHAVIOR' and 'Graphite tools' in tab.description.text(),(tab.heading.text(),tab.breadcrumb.text())
 window_words('settings_'+tag);fit('settings_'+tag)
 record('04_Settings_%s.png'%tag,'%s: the settings roots read Workspace and Assistant (root keys Ledger and Slate unchanged); stacy.enabled shows as Allow new Graphite AI activity over its unchanged definition.'%size[0],w.grab())
 observations['settings_'+tag]=dict(roots=roots,heading=tab.heading.text(),breadcrumb=tab.breadcrumb.text())
 check('%s 04 Settings: the roots read %s; stacy.enabled reads “%s” under %s; no visible word says Slate, Ledger or Hatch'%(tag,' and '.join(roots),tab.heading.text(),tab.breadcrumb.text()))
 # 05 · the left column's cabinet and existing views; the concern dossiers of the pre-rename seed rows ---------------------------------
 w.show_start();settle();align()
 assert cabinet.items['catalog:ledger'].text(0)=='Graphite' and cabinet.items['memory:root'].text(0)=='Graphite memory' and cabinet.items['catalog:ledger'].isExpanded()
 window_words('cabinet_'+tag);fit('cabinet_'+tag)
 cabinet.set_legacy(True);settle();align()
 seen=[]
 def walk(item):
  seen.append(item.text(0))
  for i in range(item.childCount()):walk(item.child(i))
 for i in range(w.nav.topLevelItemCount()):walk(w.nav.topLevelItem(i))
 assert 'Graphite' in seen and 'Ledger' not in seen,seen
 window_words('existing_views_'+tag);fit('existing_views_'+tag)
 cabinet.set_legacy(False);settle()
 dossier=w.concern.open('ledger');settle();align()
 assert dossier.heading.text()=='Graphite' and w.tabs.tabText(w.tabs.indexOf(dossier)).split(' · ')[-1]=='Graphite' and w.concern.store.get('ledger')['title']=='Ledger',(dossier.heading.text(),w.tabs.tabText(w.tabs.indexOf(dossier)))
 window_words('dossier_ledger_'+tag);fit('dossier_ledger_'+tag);heading=dossier.heading.text()
 record('05_Dossier_%s.png'%tag,'%s: the concern dossier of the seed item \'ledger\' in a profile made before the rename: its stored title Ledger is shown as Graphite (heading and tab); the left column\'s cabinet shows the Graphite drawer and Graphite memory.'%size[0],w.grab())
 ops=w.concern.open('operations');settle();align()
 assert ops.summary.text()=='Graphite maintenance, installation and recovery.',ops.summary.text()
 window_words('dossier_operations_'+tag);fit('dossier_operations_'+tag)
 summary=ops.summary.text()
 for tab in (ops,dossier):  # the preview tab is reused, so the first dossier may already be gone
  if shiboken6.isValid(tab) and w.tabs.indexOf(tab)>=0:w.tabs.removeTab(w.tabs.indexOf(tab));tab.deleteLater()
 observations['existing_views_'+tag]=dict(rows=seen[:12],dossier_heading=heading,operations_summary=summary)
 check('%s 05 The left column: the cabinet\'s drawers read Graphite and Graphite memory (stored title still Ledger); Existing views read %s; the dossiers of \'ledger\' and \'operations\' read Graphite and “%s”; no visible row, tooltip or word says Slate, Ledger or Hatch'%(tag,' · '.join(seen[:6]),summary))
 w.show_start();settle()
assert provider.call_count==launcher.call_count==submission.call_count==popen.call_count==system.call_count==detached.call_count==0
check('No job, worker, model, provider request, process, shell command or detached program')
w.close();app.processEvents()
result=dict(schema='arc.graphite01-rename-ui/1',state='PASSED',mode='ACTUAL_QT_OFFSCREEN',acceptance_claimed=False,checks=checks,captures=captures,observations=observations,
 kept_words='The Files/Slate folder keeps its name on disk; settings keys and their root keys keep their names (the page shows the roots as Workspace and Assistant); a catalog made before the rename keeps its stored seed words (shown through concern_catalog.shown).')
(OUT/'graphite-rename-ui.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],checks=len(checks),captures=len(captures)),ensure_ascii=False),flush=True)
