"""Actual Qt check of the desk (HATCH DESK D1a and D1b; the owner's brief of 2026-11-06: "a quieter, symmetrical desk" and "Be
obsessive in symmetry"), offscreen.

The real window is built with the holds at 1920 by 1200, 1366 by 768 and 1280 by 800 and at 14, 18 and 20 pt; at every one of
the nine it measures with tools/symmetry.py every mirrored pair of the Symmetry section (the panes, the two bands, the head,
the lower band; D1b: the panes' tab rows, each tab and its mirror, the short yellow mark's length and offset, the content
boxes, the feet, Trash and its kept-empty mirror, and the three left trees' boxes, indentation, row height and branch-line
column, each tree measured while it is the active one, and Activity's list rows at the trees' row height, its lines whole) and asserts a difference of zero pixels for each, every word whole in
the window (tools/ui_fit), and nothing in the workspace scrolling sideways (Home: the Finder with Today).
Then: the two bands are the same grain tile, phase-aligned (their pixels are equal wherever no word is drawn, and equal the
tile's), with the lettering's contrast measured on it; Half and Tall grow the working area above the lower band while the band
keeps its height; a drag of either separator moves both panes and the width comes back after save and reopen; Ctrl+K reaches
searching (the line focused with Find chosen); the erased symbol at the far right is the System menu (it opens the Nice list,
Stop everything first, whose Game word opens STRUTHIO, patched). D1b: the centre foot is empty in Line (a status message aside)
and the console shows in Half; every action a removed pane control reached is reached from its home (Work ▸ Import and
Export, Arrange ▸ Cabinet and Refresh Machine View, Find's cabinet and settings rows, Activity's Timeline words, the Machine
row's tooltip); the pointer is the mark's facets with the hotspot at the tip, the window's cursor, while text fields keep the
I-beam and splitters theirs. The quiet-script rule (the owner, 2026-11-06): the word Graphite is the Paper script, measured
against the symbol by its outline and by its drawn pixels at every size; the panes' notes you may skip are the script and what
you act on stays print; View ▸ Pleasantries in script off makes them print and on restores them. Captures for the owner in
build/graphite_desk (or ARC_LEDGER_DESK_CAPTURE_DIR): the desk with both launch menus closed at 1920 by 1200 and 1366 by 768,
the overlay (the axis and the mirrored guides drawn over the window), the left pane with each of its tabs, the right pane with
each of its tabs, the pointer, and the quiet-script rule on and off; desk-ui.json holds the measured table.

D1-fix (the two reviews of D1): the band words, the cat and Trash are measured by what they draw. At every one of the nine
sizes: the pairs by the band words' ink (desk_qt.InkWord) and the cat's drawing; the word Graphite's optical size against the
symbol; every drawn item (the word, the symbol, every menu and lower-band word, the cat, Trash) drawn again from its design by
references taken at start and compared with the window's pixels (drawn_as_designed); the chosen tabs' yellow marks (tab_marks);
Trash's ink an inset from the pane's inner edge and bottom (trash_drawn); every pose of the cat inside the band (cat_poses_inside);
no script label cut by its own edges (script_labels); the script word's contrast on the band (script_contrast); nothing sideways
in either pane and every lower-band word whole; Conversation, Context, Half, Tall and the System menu's list (faces_and_sizes).
Step 04 adds the separators' resize cursor, step 05 Ctrl+K's one-line Find, step 10 Today's capture hint, the Files room's note
and the System menu's list's notes at one size. A mutation proof (each fixed defect's old behaviour put back) is evidence, not
shipped (v01_reruns/desk/D1-fix/probe/mutations.py).

HATCH DESK D3 (the writing line and Log): at every one of the nine sizes, every desk pair with each of the four modes chosen
(Assignment · Shell or Bash · Search · Log, Log on both streams) in Line, Half and Tall, only the chosen word marked, every band
word drawn as designed in Line and the working area's words whole in Half and Tall (writing_line_pairs); step 05 Ctrl+K is the
line in Search; step 08 Half shows the mode's page; step 12 the modes' behaviour (Enter gives Assignment's words to Graphite and
never runs staC, Ctrl+Enter runs typed staC through the staC path, Commands ▸ Run an operation…, Search's results, Log's Events
following the journal with nothing to write, Log's Network on the check's fake capability, labelled TEST DATA: only D5's four
operations, the filter, the confirmation before the first capture, the pin held while packets arrive, Ask Stacy about this,
D4's entry_at and focus, Stop, the unavailable reason) and the owner's captures Graphite_Desk_D3_01 to 05. D3-fix (the review of
D3): the poem placeholder's drawn ink at least 4.5:1 on the line's paper; Up on Assignment's empty line recalls the typed staC
that ran (the staC target's history); the search answer's end in sight after Enter, and the whole answer in the owner's capture;
a capture's last packets read when it ends between two reads; a capture's refusal said and kept (words the capability's grammar
refuses before anything is asked; the capability's own refusal through the next refreshes).

The integration of D2 to D5: the cat is placed and paired by its pale coat (graphite_brand.cat_ink, outline=False), and at every
one of the nine sizes the lower band's outer and inner pairs are measured again in the window's own pixels at the words' ink
level (band_edges_drawn); in Half and Tall no wrapped label of the working area is given fewer lines than its words need
(ui_fit.cut_lines: Log's capture reason, where the lists stand one above the other); step 08 shows a long status message and
asserts the panes, the workspace and every pair unmoved.

Disposable profile and Concern; Kernel.launch, Kernel.submit, the provider request and session_power.system are held; after the window exists no
process, shell command or detached program may start. Nothing here is owner-host acceptance.
"""
import hashlib,json,math,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
PROGRAM=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ARC_LEDGER_DESK_CAPTURE_DIR',str(PROGRAM/'build/graphite_desk')));OUT.mkdir(parents=True,exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='graphite-desk-ui-'))
SCREEN=RUN/'screen.json';SCREEN.write_text(json.dumps({'screens':[{'name':'review','x':0,'y':0,'width':1920,'height':1200,'logicalDpi':96,'logicalBaseDpi':96,'dpr':1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile='+str(SCREEN),ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
 ARC1_WORKBENCH_CONFIG_HOME=str(RUN/'profile'),ARC_LEDGER_CONCERN=str(RUN/'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION',None)
sys.path.insert(0,str(PROGRAM));sys.path.insert(0,str(PROGRAM/'tools'));sys.dont_write_bytecode=True
import symmetry,ui_fit
from PySide6.QtCore import Qt,QPoint,QProcess,QRect,QRectF
from PySide6.QtGui import QBrush,QColor,QFont,QImage,QPainter,QPen
from PySide6.QtWidgets import QApplication,QMessageBox,QWidget
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow
from workbench import locations,clip,ledger_control,desk_qt,struthio_qt,pane_qt,graphite_brand,shell2,trash_can_qt
from workbench.desktop_header_qt import KILL_WORDS,SystemButton
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
app=make_app([]);root=locations.office(RUN/'workspace');session=Session(RUN/'profile/session.json',root)
w=WorkbenchWindow(root,session,restore=False);k=w.ledger_bridge.kernel;bridge=w.ledger_bridge;bar=w.type_bar
import platform;platform.processor()  # the one host probe Python answers through a process, answered before the guards
popen=patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')).start()
system=patch.object(os,'system',side_effect=AssertionError('No shell command')).start()
detached=patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program')).start()
checks=[];captures=[];measured={}
SIZES=((1920,1200),(1366,768),(1280,800));POINTS=(14,18,20)
def settle(ms=25):
 for name in ('agenda_runner','study_idle'):
  obj=getattr(w,name,None)
  if obj and hasattr(obj,'timer'):obj.timer.stop()
 for _ in range(2):app.processEvents();QTest.qWait(ms)
def check(text):checks.append(text);print(text,flush=True)
def call(op,args=None):
 value=k.dispatch(op,args or {},operator());assert value['ok'],value;return value['result']
def align(times=3,window=None):
 window=window or w
 for _ in range(times):window.type_bar.align();settle()
def setting(key,value):
 row=next(r for r in ledger_control.settings(k)['settings'] if r['key']==key)
 call('ledger.settings.set',{'key':key,'value':value,'expected_revision':row['revision']});bridge.sync_profile(force=True);settle(40);align()
def ui_pt(points):setting('reading.ui_pt',float(points));settle();align(4)
def record(name,note,image,mode):
 target=OUT/name;assert image.save(str(target),'PNG'),name
 captures.append(dict(file=name,note=note,mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),resolution=[image.width(),image.height()],bytes=target.stat().st_size))
def shown_menus(top):return [h for h in top.headings() if h.isVisible()]+([top.more_menus] if top.more_menus.isVisible() else [])

def ink_span(widget,window):
 """A band word's ink as its layout draws it (desk_qt.InkWord), in window coordinates: (first column, last + 1, first row, last + 1)."""
 a,b,c,e=desk_qt.InkWord.span(widget);x,y,_,_=symmetry.box(widget,window);return (x+a,x+b,y+c,y+e)

def cat_span(window,pose='rest'):
 """The cat's drawing for a pose as its button draws it, in window coordinates: its pale coat (graphite_brand.cat_ink with
 outline=False in the button's tile), what the band shows and what the band places at its inset (the integration of D2 and D3;
 band_edges_drawn measures the same in the window's pixels)."""
 h=window.type_bar.hatch;l,t,r,b=graphite_brand.cat_ink(h.tile(),graphite_brand.POSES[pose],False);x,y,_,_=symmetry.box(h,window)
 return tuple(round(v,6) for v in (x+l,x+r,y+t,y+b))

def desk_pairs(window=None):
 """Every mirrored pair of the Symmetry section, in pixels (tools/symmetry), as laid out: the boxes, and (D1-fix) the band words' and
 the cat's ink as their layout draws it (drawn_pairs measures the same in the window's own pixels)."""
 window=window or w;W=window.width();top=window.shell2.top;b=window.type_bar;d=window.desk;S=symmetry
 rows=[]
 # 1 · panes: equal widths, mirrored edges, the same top and bottom lines, the workspace's centre on the axis, contents inset alike
 rows+=S.pair('panes',window.nav_dock,window.sim_dock,window)
 rows+=S.centred('workspace',window.centralWidget(),window)
 rows+=S.pair('pane contents',window.nav_dock.widget(),window.sim_dock.widget(),window,('outer','inner'))
 # 3 · bands: equal height in Line mode, straight across the full width, the same slots and insets
 rows+=S.same('bands · height in Line mode',[window.ribbon_dock.height(),window.type_dock.height()],'height')
 for name,band in (('head band',window.ribbon_dock),('lower band',window.type_dock)):
  rows+=S.centred(name,band,window)+S.same(name+' · full width',[band.width(),W],'width')
 rows+=S.pair('head slots',top.brand_holder,top.right_holder,window,('outer','inner','width','top','height'))
 rows+=S.pair('lower slots',b.left,b.right,window,('outer','inner','width','top','height'))
 rows+=S.same('slots and panes · the workspace column\'s left edge',[S.box(top.brand_holder,window)[2],S.box(b.left,window)[2],S.box(window.nav_dock,window)[2]],'x')
 rows+=S.same('slots and panes · the workspace column\'s right edge',[S.box(top.right_holder,window)[0],S.box(b.right,window)[0],S.box(window.sim_dock,window)[0]],'x')
 (lp,ls),(rp,rs)=b.rows();words=rp+rs;last=words[-1];first=words[0];cat=cat_span(window)
 wx=S.box(top.wordmark,window)[0]+top.wordmark.ink_rect().left()
 rows+=S.same('bands · side inset at the left edge (the word Graphite\'s outline, the cat\'s drawing at rest)',[wx,cat[0],d.inset],'inset')
 rows+=S.same('bands · side inset at the right edge (the symbol\'s mark, the last word\'s ink)',[W-sum(S.box(top.nice,window)[0:3:2]),W-ink_span(last,window)[1],d.inset],'inset')
 # 4 · head: Graphite and the symbol mirrored and on one centre line; their optical size; the menu row centred with equal gaps, the line's inset
 rows+=S.pair('head · the word Graphite and the symbol',top.wordmark,top.nice,window,('outer','middle'))
 rows+=word_ink_pairs(window)
 menus=shown_menus(top);row=S.span(menus,window)
 rows+=S.centred('head · the menu row',row,window)+S.same('head · menu gaps',S.gaps(menus,window),'gap')
 rows+=S.same('head · menu words\' height',[m.height() for m in menus]+[window.ribbon_dock.height()],'height')
 inks=[ink_span(m,window) for m in menus];ink_gaps=[c[0]-a[1] for a,c in zip(inks,inks[1:])]
 a=desk_qt.ink_air(d.scale);odd=menus[-1].width()-(inks[-1][1]-inks[-1][0])-2*a  # the row's odd pixel, when it cannot split, widens the last box
 rows+=S.same('head · the menus\' ink: equal gaps (the odd pixel, if any, before the last)',ink_gaps[:-1]+[ink_gaps[-1]-odd] if ink_gaps else [],'gap')
 rows+=S.same('head · the menus\' ink centred on the axis',[inks[0][0],W-inks[-1][1]],'inset')
 line=S.box(b.box,window)
 if top.plan[4] is not None:  # the menus lie on the workspace column: their ink's ends are the writing line's ends
  rows+=S.same('head menus\' ink and the writing line · left edge',[inks[0][0],line[0]],'x')+S.same('head menus\' ink and the writing line · right edge',[inks[-1][1],line[0]+line[2]],'x')
 # 5 · the lower band, as drawn: the cat's drawing and the last word's ink, Tall's ink and the first word's, the line on the axis, one baseline
 rows+=S.same('lower · the cat\'s drawing at rest and the last word\'s ink (outer)',[cat[0],W-ink_span(last,window)[1]],'outer')
 rows+=S.same('lower · Tall\'s ink and the first word\'s (inner)',[W-ink_span(ls[-1],window)[1],ink_span(first,window)[0]],'inner')
 rows+=S.same('lower · Tall\'s ink and the first word\'s ink at the pane edges\' inset',[d.pane-ink_span(ls[-1],window)[1],ink_span(first,window)[0]-(W-d.pane),d.inset],'inset')
 rows+=S.centred('lower · the writing line',b.box,window)
 rows+=S.same('lower · the writing line\'s inset in the workspace column',[line[0]-d.pane,W-d.pane-(line[0]+line[2])],'inset')
 rows+=S.same('lower · baselines (Line Half Tall, the line, the words)',[S.baseline(x,window) for x in ls+[b.box]+words],'baseline')
 rows+=S.same('lower · word and line heights',[x.height() for x in ls+[b.box]+words],'height')
 rows+=S.same('lower · one size for every word and the line',[x.font().pixelSize() for x in ls+[b.box]+words],'px')
 rows+=pane_pairs(window)
 return rows

def lit(image,tile,box,top,height):
 """The pixels of a band drawn lighter than the band's own grain tile at the same place (the tile starts at the band's
 top-left), inside box (x, w) widened by 2 px each side: (first column, last column + 1, first row, last row + 1)."""
 x0,width=box;cols=set();rows=set();tw,th=tile.width(),tile.height()
 for x in range(max(0,x0-2),min(image.width(),x0+width+2)):
  for y in range(height):
   if QColor(image.pixel(x,top+y)).lightness()>QColor(tile.pixel(x%tw,y%th)).lightness():cols.add(x);rows.add(y)
 return (min(cols),max(cols)+1,min(rows),max(rows)+1) if cols else None

DRAWN={}
def word_ink_pairs(window=None):
 """The word Graphite (in the Paper script, the owner's "upper left Graphite should be cursive") and the symbol as they are
 drawn: the word's outline (shell2.Wordmark.ink_rect) starts at the band's inset and is centred on the band's centre line,
 which is the symbol's mark's (both outlines are centred in the band's height); and in the window's own pixels (lighter than
 the grain tile at the same place) the word's first inked column and the symbol's last are at equal distances from the
 window's edges. The inked rows are recorded too (DRAWN, desk-ui.json head_balance.as_drawn) but not asserted: both
 outlines are centred to the sub-pixel, and whether the tip of a curve at the top or the bottom lightens its last partial
 row by a level depends on the antialiasing, so the inked rows' centre can read half a pixel apart where the band's height
 is odd."""
 window=window or w;S=symmetry;top=window.shell2.top;wm=top.wordmark;sym=top.nice;W=window.width();d=window.desk;H=window.ribbon_dock.height()
 wx,wy,_,_=S.box(wm,window);sx,sy,sw,sh_=S.box(sym,window);ink=wm.ink_rect()
 rows=S.same('head · the word\'s outline at the band\'s inset',[wx+ink.left(),d.inset],'inset')
 rows+=S.same('head · the word\'s outline and the symbol\'s mark on one centre line',[wy+ink.center().y(),sy+sh_/2.0],'middle')
 # D1-fix: a script word and a symbol have no "equal height" (the word's descenders and swashes are not its size), so the pair
 # is their centre line (above) and their optical size: the script's capitals stand as tall as the symbol, to the pixel.
 if wm.script:
  from PySide6.QtGui import QFontMetricsF
  rows+=S.within('head · optical size: the script\'s capitals and the symbol, as tall',QFontMetricsF(wm.font()).capHeight(),desk_qt.symbol_height(d.scale),0.5,'height')
 image=window.grab().toImage();tile=desk_qt.grain_tile().toImage();band=window.ribbon_dock.mapTo(window,QPoint(0,0)).y()
 a=lit(image,tile,(wx,wm.width()),band,H);b=lit(image,tile,(sx,sw),band,H)
 assert a and b,('the word and the symbol are drawn on the band',a,b)
 rows+=S.same('head · the word and the symbol as drawn: distance from the window\'s edges',[a[0],W-b[1]],'outer')
 DRAWN.clear();DRAWN.update(word_columns=[a[0],a[1]],word_rows=[a[2],a[3]],symbol_columns=[b[0],b[1]],symbol_rows=[b[2],b[3]],outer=[a[0],W-b[1]],
  inked_rows_centre=[(a[2]+a[3])/2.0,(b[2]+b[3])/2.0],outline_centre=[wy+ink.center().y(),sy+sh_/2.0],band_centre=H/2.0)
 return rows

# Drawn as designed (D1-fix; the symmetry review moved what is drawn by a pixel and the boxes still measured 0): each drawn item is
# drawn again here from its design, by references taken when this check starts (so a later change to the painters is measured
# against them, not copied), over the same ground, and compared with the window's own pixels. A pixel's shift of any of them
# leaves its box where it was and shows here.
REF_MARK=graphite_brand.paint_mark;REF_CAN=trash_can_qt.draw_can;REF_CAT=graphite_brand.paint_cat;REF_OUTLINE=shell2.Wordmark.outline
def band_ground(window,band):
 """A band's ground as designed: the grain tile from the band's own top-left, the band's size."""
 image=QImage(window.width(),band.height(),QImage.Format_RGB32);p=QPainter(image);p.setBrushOrigin(0,0);p.fillRect(image.rect(),QBrush(desk_qt.grain_tile()));p.end();return image
def differs(grab,expected,box,origin):
 """The largest channel difference between the window's pixels in box (window coordinates) and the expected image (whose
 (0, 0) is the window's `origin`)."""
 x,y,w_,h_=box;ox,oy=origin;worst=0
 for yy in range(max(0,y,oy),min(grab.height(),y+h_,oy+expected.height())):
  for xx in range(max(0,x,ox),min(grab.width(),x+w_,ox+expected.width())):
   a=grab.pixel(xx,yy);b=expected.pixel(xx-ox,yy-oy)
   worst=max(worst,abs(((a>>16)&255)-((b>>16)&255)),abs(((a>>8)&255)-((b>>8)&255)),abs((a&255)-(b&255)))
 return worst
DESIGNED={}
def drawn_as_designed(window=None):
 """Each drawn item of both bands and the left pane's foot against its design, in the window's pixels (a difference of at
 most DRAWN_LEVELS levels is rounding; anything moved by a pixel differs by tens of levels): the word Graphite (its outline,
 the hairline), the symbol, every shown menu word and every lower-band word (desk_qt.InkWord from its origin), the cat at rest,
 Trash (its can and word from TrashCan.layout). The yellow marks under the chosen tabs are measured in tab_marks."""
 window=window or w;S=symmetry;top=window.shell2.top;b=window.type_bar;grab=window.grab().toImage().convertToFormat(QImage.Format_RGB32);rows=[];seen={}
 head=band_ground(window,window.ribbon_dock);p=QPainter(head);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
 wm=top.wordmark;x,y,_,_=S.box(wm,window);path=REF_OUTLINE(wm);r=path.boundingRect();ink=wm.ink_rect();half=wm.stroke/2.0
 p.save();p.translate(x+ink.left()+half-r.left(),y+ink.top()+half-r.top());pen=QPen(QColor(desk_qt.ERASED),wm.stroke,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin)
 p.setPen(pen if wm.stroke>0 else Qt.NoPen);p.setBrush(QColor(desk_qt.ERASED));p.drawPath(path);p.restore()
 sym=top.nice;x,y,sw,sh_=S.box(sym,window);mh=sw*graphite_brand.MARK_BOX[1]/graphite_brand.MARK_BOX[0];REF_MARK(p,QRectF(x,y+(sh_-mh)/2.0,sw,mh),desk_qt.ERASED)
 head_items=[('the word Graphite',wm),('the symbol',sym)]
 for m in shown_menus(top):
  x,y,_,_=S.box(m,window);p.setFont(m.font());p.setPen(QColor(desk_qt.ERASED));p.drawText(x+int(m.property('inkX')),y+int(m.property('inkBaseline')),m.text());head_items.append(('menu '+m.text(),m))
 p.end()
 for name,widget in head_items:seen[name]=differs(grab,head,S.box(widget,window),(0,S.box(window.ribbon_dock,window)[1]))
 lower=band_ground(window,window.type_dock);ly=S.box(window.type_dock,window)[1];p=QPainter(lower);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
 (lp,ls),(rp,rs)=b.rows();lower_items=[]
 for wd in ls+rp+rs:
  x,y,_,_=S.box(wd,window);p.setFont(wd.font());p.setPen(QColor(desk_qt.ERASED_QUIET if wd.property('arcQuiet') else desk_qt.ERASED))
  p.drawText(x+int(wd.property('inkX')),y-ly+int(wd.property('inkBaseline')),wd.text());lower_items.append((wd.text(),wd))
 h=b.hatch;x,y,_,_=S.box(h,window);t=h.tile();REF_CAT(p,QRectF(x+t.x(),y-ly+t.y(),t.width(),t.height()),graphite_brand.POSES['rest']);lower_items.append(('the cat',h))
 p.end()
 for name,widget in lower_items:
  box=S.box(widget,window);seen[name]=differs(grab,lower,(box[0],box[1],box[2],box[3]-(desk_qt.MARK if widget is not h else 0)),(0,ly))  # above the marks (the chosen word's yellow is tab_marks' kind)
 trash=window.trash_can;x,y,tw,th=S.box(trash,window);foot=QImage(tw,th,QImage.Format_RGB32);foot.fill(QColor(pane_qt.GROUND));p=QPainter(foot);p.setRenderHint(QPainter.Antialiasing)
 can,word,count=trash.layout();REF_CAN(p,QRectF(can.x(),can.y(),trash.can,trash.can),full=trash.count>0)
 p.setFont(trash.word_font);p.setPen(QColor(shell2.TEXT));p.drawText(word,'Trash')
 if count is not None:p.setFont(trash.count_font);p.setPen(QColor(shell2.QUIET));p.drawText(count,str(trash.count))
 p.end();seen['Trash']=differs(grab,foot,(x,y,tw,th),(x,y))
 DESIGNED.clear();DESIGNED.update(seen)
 for name,level in seen.items():rows+=S.within('drawn as designed · '+name,level,0,DRAWN_LEVELS,'levels')
 return rows
DRAWN_LEVELS=2

def trash_drawn(window=None,level=desk_qt.INK_LEVEL):
 """Trash as drawn, in the window's pixels: its ink (pixels at least `level` of the way from the pane's paper to Trash's
 graphite, the level its layout measures the word's ink at) ends an inset from the left pane's inner edge and an inset above the pane's bottom (the brief: "Pin a larger Trash
 at the lower right"; D1-fix: the review found the can and word drawn at the left of a wider box)."""
 window=window or w;S=symmetry;grab=window.grab().toImage();x,y,tw,th=S.box(window.trash_can,window);pane=S.box(window.left_pane,window);d=window.desk
 paper=QColor(pane_qt.GROUND).lightness();ink=QColor(shell2.TEXT).lightness();cols=set();rows=set()
 for yy in range(max(0,y-4),min(grab.height(),y+th+4)):
  for xx in range(max(0,x-4),min(grab.width(),x+tw+4)):
   if (paper-QColor(grab.pixel(xx,yy)).lightness())/(paper-ink)>=level:cols.add(xx);rows.add(yy)
 right,bottom=max(cols)+1,max(rows)+1;DESIGNED['Trash ink']=dict(columns=[min(cols),right],rows=[min(rows),bottom],pane=list(pane))
 return S.same('Trash as drawn · its ink\'s right edge an inset from the pane\'s inner edge',[pane[0]+pane[2]-right,d.inset],'inset')+S.same('Trash as drawn · its ink\'s bottom an inset above the pane\'s bottom',[pane[1]+pane[3]-bottom,d.inset],'inset')

def tab_marks(window=None):
 """The chosen tabs' short yellow marks as drawn, in the window's pixels: the pencil-yellow run under the chosen tab of each
 pane (its first and last column and its row). With Cabinet and Activity chosen (mirror partners) the runs mirror exactly."""
 window=window or w;S=symmetry;grab=window.grab().toImage();P=QColor(desk_qt.PENCIL).rgb();runs=[]
 for pane in (window.left_pane,window.right_pane):
  chosen=next(t for t in pane.tabs.buttons if t.isChecked());x,y,tw,th=S.box(chosen,window)
  found=[(xx,yy) for yy in range(y,y+th) for xx in range(x,x+tw) if grab.pixel(xx,yy)==P]
  runs.append((min(a for a,_ in found),max(a for a,_ in found)+1,min(b_ for _,b_ in found),max(b_ for _,b_ in found)+1,chosen) if found else None)
 assert all(runs),('a yellow mark under each chosen tab',runs)
 (l0,l1,lt,lb,lc),(r0,r1,rt,rb,rc)=runs;W=window.width();rows=S.same('tab marks as drawn · length',[l1-l0,r1-r0],'length')+S.same('tab marks as drawn · rows',[lt,rt],'top')+S.same('tab marks as drawn · height',[lb-lt,rb-rt],'height')
 if window.left_pane.tabs.buttons.index(lc)==2-window.right_pane.tabs.buttons.index(rc):rows+=S.same('tab marks as drawn · mirrored ('+lc.text()+', '+rc.text()+')',[l0,W-r1],'outer')
 return rows

def cat_poses_inside(window=None):
 """Every pose of the cat as its button draws it (each set at once, as under Reduce motion), rendered alone: its pixels lie
 inside the lower band with at least the band's padding above and below, the button's edges cut nothing of it (its drawn
 extent is its design's, graphite_brand.cat_ink, to within a pixel of antialiasing), and the design of every pose lies inside
 CAT_BOX (the tile's room). The brief: "Every pose fits inside the band"."""
 window=window or w;S=symmetry;h=window.type_bar.hatch;cat=h.cat;saved=cat.params;rows=[];seen={}
 hx,hy,hw,hh=S.box(h,window);by=S.box(window.type_dock,window)[1];bh=window.type_dock.height();pad=desk_qt.BAND_PAD
 try:
  for pose,params in graphite_brand.POSES.items():
   cat.params=params;image=QImage(hw,hh,QImage.Format_ARGB32_Premultiplied);image.fill(0)
   from PySide6.QtGui import QRegion
   QWidget.render(h,image,QPoint(0,0),QRegion(),QWidget.RenderFlag.DrawChildren)  # QWidget's own (HatchButton.render is the services' words)
   pts=[(x,y) for y in range(hh) for x in range(hw) if image.pixelColor(x,y).alpha()>=64]
   x0,x1=min(a for a,_ in pts),max(a for a,_ in pts)+1;y0,y1=min(b_ for _,b_ in pts),max(b_ for _,b_ in pts)+1
   l,t,r,b_=graphite_brand.cat_ink(h.tile(),params);seen[pose]=dict(drawn=[hx+x0,hx+x1,hy+y0,hy+y1],design=[round(hx+l,2),round(hx+r,2),round(hy+t,2),round(hy+b_,2)])
   rows+=S.at_least('the cat · %s · room above it in the band'%pose,hy+y0-by,pad)+S.at_least('the cat · %s · room below it in the band'%pose,by+bh-(hy+y1),pad)
   rows+=S.at_least('the cat · %s · nothing cut at the button\'s left'%pose,x0,1)+S.at_least('the cat · %s · nothing cut at the button\'s right'%pose,hw-x1,1)
   for edge,(a,b2) in (('left',(x0,l)),('right',(x1,r)),('top',(y0,t)),('bottom',(y1,b_))):rows+=S.within('the cat · %s · drawn %s edge is its design\'s'%(pose,edge),a,b2,1.0)
   e=graphite_brand.cat_extent(params);box=graphite_brand.CAT_BOX
   rows+=S.at_least('the cat · %s · its design inside the tile\'s room'%pose,min(e[0]-box.left(),e[1]-box.top(),box.right()-e[2],box.bottom()-e[3]),0)
 finally:cat.params=saved;h.update()
 DESIGNED['cat poses']=seen
 return rows

def band_edges_drawn(window=None):
 """The integration of D2 and D3 (the review of D3 found the cat's visible coat a pixel inside the last mode word's mirror: the cat
 was placed by its paws' graphite outline, graphite on the graphite band): the lower band as the owner sees it, in the window's own
 pixels and by one rule for every item, the words' ink level (desk_qt.INK_LEVEL) read as lightness: a column is ink where a pixel
 of the slot is at least that far from the band's mean tone towards the lettering's. The cat's first such column and the last mode
 word's last mirror about the axis (the outer pair); Tall's last and the first mode word's first (the inner pair)."""
 from PySide6.QtGui import QColor
 window=window or w;S=symmetry;b=window.type_bar;W=window.width();dock=window.type_dock
 tone=QColor(desk_qt.grain_report()['mean_tone']).lightness();level=tone+desk_qt.INK_LEVEL*(QColor(desk_qt.ERASED).lightness()-tone)
 image=dock.grab().toImage();ox=b.mapTo(dock,QPoint(0,0)).x()
 def ink(slot):
  g=slot.geometry();cols=[x for x in range(max(0,ox+g.left()),min(image.width(),ox+g.right()+1)) if any(QColor(image.pixel(x,y)).lightness()>=level for y in range(image.height()))]
  return (min(cols),max(cols)+1) if cols else (None,None)
 (l0,l1),(r0,r1)=ink(b.left),ink(b.right);x0=dock.mapTo(window,QPoint(0,0)).x()
 DESIGNED['band edges drawn']=dict(level=round(level,1),left_slot=[l0,l1],right_slot=[r0,r1])
 return S.same('lower · drawn · the cat\'s pale coat and the last mode word\'s ink (outer, the window\'s pixels)',[x0+l0,W-(x0+r1)],'outer')+\
        S.same('lower · drawn · Tall\'s ink and the first mode word\'s ink (inner, the window\'s pixels)',[W-(x0+l1),x0+r0],'inner')

def clipped_ink(label,margin=12):
 """How many of a label's drawn pixels its own edges cut off: the label is drawn once more with room round its contents (the same
 width for its words, so the same lines) and its ink outside the usual rect is counted (D1-fix: the script's S, E and i reach
 left of their origin, a swash past the last word's advance, a descender below the line)."""
 from PySide6.QtCore import QRect
 from PySide6.QtGui import QRegion
 g=label.geometry();m=label.contentsMargins();out=0
 try:
  label.setContentsMargins(m.left()+margin,m.top()+margin,m.right()+margin,m.bottom()+margin);label.resize(g.width()+2*margin,g.height()+2*margin)
  image=QImage(label.size(),QImage.Format_ARGB32_Premultiplied);image.fill(0);QWidget.render(label,image,QPoint(0,0),QRegion(),QWidget.RenderFlag.DrawChildren)
  if image.pixelColor(0,0).alpha()>0:return 0  # a label with its own background: nothing to tell
  inner=QRect(margin,margin,g.width(),g.height())
  out=sum(1 for y in range(image.height()) for x in range(image.width()) if not inner.contains(x,y) and image.pixelColor(x,y).alpha()>=64)
 finally:label.setContentsMargins(m);label.setGeometry(g)
 return out

def script_labels(window=None):
 """Every visible label drawn in the Paper script (the quiet-script rule's notes, pleasantries and corner notes), with what its
 edges cut off (clipped_ink): the word Graphite draws by its outline and is measured in word_ink_pairs."""
 from PySide6.QtWidgets import QLabel
 window=window or w;rows=[];seen={}
 for label in window.findChildren(QLabel):
  if not label.isVisible() or label is window.shell2.top.wordmark or label.width()<=0:continue
  if label.font().family()!=shell2.SCRIPT and shell2.SCRIPT not in label.text():continue
  words=ui_fit.plain(label).strip()[:60];n=clipped_ink(label);seen[words]=n
  rows+=symmetry.same('script words whole · '+words,[n,0],'clipped px')
 DESIGNED['script labels']=seen
 return rows

def script_contrast(window=None):
 """The word Graphite in the script on the band, measured in the window's pixels: each pixel's coverage (how far its lightness has
 moved from the grain under it toward the lettering's), the contrast of the strokes' cores (the median pixel of coverage 0.9 and
 more) and of the median inked pixel (coverage 0.5 and more) against the band's mean tone."""
 window=window or w;S=symmetry;wm=window.shell2.top.wordmark;grab=window.grab().toImage();tile=desk_qt.grain_tile().toImage();x,y,ww,hh=S.box(wm,window)
 Li=QColor(desk_qt.ERASED).lightness();core=[];inked=[];tw,th=tile.width(),tile.height();mean=desk_qt.grain_report()['mean_tone']
 for yy in range(y,y+hh):
  for xx in range(x,x+ww):
   t=QColor(tile.pixel(xx%tw,yy%th)).lightness();c=QColor(grab.pixel(xx,yy));v=(c.lightness()-t)/(Li-t)
   if v>=0.5:inked.append((c.red(),c.green(),c.blue()))
   if v>=0.9:core.append((c.red(),c.green(),c.blue()))
 ratio=lambda rgb:desk_qt.contrast(rgb,mean)
 inked.sort(key=ratio);core.sort(key=ratio);out=dict(core=round(ratio(core[len(core)//2]),2) if core else 0,median=round(ratio(inked[len(inked)//2]),2) if inked else 0,core_pixels=len(core),inked_pixels=len(inked),mean_tone=mean)
 DESIGNED['script contrast']=out
 return S.at_least('the script word on the band · its strokes\' cores (contrast)',out['core'],7.0,'contrast')+S.at_least('the script word on the band · its median inked pixel (contrast)',out['median'],4.5,'contrast')

def separator_cursors(window=None):
 """D1-fix (the reach review: with both docks fixed Qt stopped offering the resize cursor, so the drag could not be found): the
 window's cursor over each pane separator and 80 px off it, as {side: (over, off)}; over must be the horizontal resize cursor,
 off the window's own pointer."""
 window=window or w;y_sep=window.nav_dock.geometry().center().y();out={}
 for name,x_sep in (('left',window.desk.pane),('right',window.width()-window.desk.pane-1)):
  away=QPoint(x_sep-80 if name=='left' else x_sep+80,y_sep)
  QTest.mouseMove(window,away);settle();QTest.mouseMove(window,QPoint(x_sep,y_sep));settle();on=window.cursor().shape()
  QTest.mouseMove(window,away);settle();out[name]=(on,window.cursor().shape())
 return out

def ctrl_k_line(window=None):
 """HATCH DESK D3 (it replaces D1-fix's one-line Find): Ctrl+K puts the cursor in the writing line in Search, one of its four
 modes, marked by the short yellow mark and remembered like any mode; the words typed go to Search. The line goes back to
 Assignment afterwards."""
 window=window or w;bar_=window.type_bar;bar_.box.clear();bar_.set_target('slate',focus=False);window.save_session();saved=window.session.state.get('type_target')
 window.tabs.setFocus();settle();QTest.keyClick(window,Qt.Key_K,Qt.ControlModifier);settle()
 out=dict(focus=app.focusWidget() is bar_.box,text=bar_.box.text(),target=bar_.target,search_marked=bar_.targets['find'].isChecked() and desk_qt.InkWord.marked(bar_.targets['find']) in (desk_qt.PENCIL,desk_qt.ERASER_MARK),
  others_marked=[k for k,b_ in bar_.targets.items() if b_.isChecked() and k!='find'],saved_before=saved)
 QTest.keyClicks(bar_.box,'pencil');settle();out.update(typed=bar_.box.text(),typed_page=bar_.box.console_page(bar_.box.text()),results=bar_.box.popup.isVisible())
 window.save_session();out['saved_after']=window.session.state.get('type_target');bar_.box.popup.hide();bar_.box.clear();bar_.set_target('slate',focus=False);window.tabs.setFocus();settle()
 out['ok']=(out['focus'] and out['text']=='' and out['target']=='find' and out['search_marked'] and not out['others_marked'] and out['typed']=='pencil'
  and out['typed_page']=='find' and out['saved_before']=='slate' and out['saved_after']=='find')
 return out

def one_size_notes(popup):
 """D1-fix (the review: with the script off the sliders' note was printed at 13 px among 16 px words): the System menu's list's
 notes and captions (shell2.QuietWords) share one print size."""
 sizes={x.words()[:40]:x.print_px() for x in popup.findChildren(shell2.QuietWords)}
 return symmetry.same('the System menu\'s list · one print size for its notes and captions',list(sizes.values()),'px'),sizes

def pane_pairs(window=None):
 """D1b: the panes' parts mirrored, in pixels: the pane bodies, the tab rows, each tab and its mirror (Machine and Context,
 Cabinet and Activity, Settings and Conversation), the tabs' widths, tops, heights, gaps and word size, each row centred on its
 pane, the short mark's length, offset and row, the content boxes, the feet, and Trash with its kept-empty mirror."""
 window=window or w;S=symmetry;W=window.width();d=window.desk;L=window.left_pane;R=window.right_pane;lt=L.tabs.buttons;rt=R.tabs.buttons;rows=[]
 rows+=S.pair('pane bodies',L,R,window)+S.pair('tab rows',L.tabs,R.tabs,window)
 for i in range(3):rows+=S.pair('tabs · %s and %s'%(lt[i].text(),rt[2-i].text()),lt[i],rt[2-i],window)
 rows+=S.same('tabs · widths',[x.width() for x in lt+rt],'width')+S.same('tabs · tops',[S.box(x,window)[1] for x in lt+rt],'top')
 rows+=S.same('tabs · heights',[x.height() for x in lt+rt],'height')+S.same('tabs · gaps',S.gaps(lt,window)+S.gaps(rt,window),'gap')
 rows+=S.same('tabs · one word size',[x.font().pixelSize() for x in lt+rt],'px')
 for name,pane,tabs in (('left',L,lt),('right',R,rt)):
  box=S.box(pane,window);row=S.span(tabs,window)
  rows+=S.same('tabs · the %s row centred on its pane'%name,[row[0]-box[0],box[0]+box[2]-(row[0]+row[2])],'inset')
 rows+=S.same('tabs · the short mark\'s length',[x.mark_rect().width() for x in lt+rt],'length')
 rows+=S.same('tabs · the short mark\'s offset in its tab',[x.mark_rect().x() for x in lt+rt],'offset')
 rows+=S.same('tabs · the short mark\'s row',[S.box(x,window)[1]+x.mark_rect().y() for x in lt+rt],'y')
 tops=[S.box(x,window) for x in (window.nav_dock,window.centralWidget(),window.sim_dock)]
 rows+=S.same('panes and the workspace · one top',[b[1] for b in tops],'y')+S.same('panes and the workspace · one bottom',[b[1]+b[3] for b in tops],'y')
 rows+=S.pair('pane contents · the active tree and the active face',L.content,R.content,window)
 rows+=S.same('pane contents · inset in the pane',[S.box(L.content,window)[0]-S.box(L,window)[0],d.inset],'inset')
 rows+=S.pair('pane feet',L.foot,R.foot,window)
 trash=window.trash_can;slot=R.foot.slot;foot=S.box(R.foot,window);mirror=(foot[0]+slot.x(),foot[1]+slot.y(),slot.width(),slot.height())
 rows+=S.pair('Trash and its kept-empty mirror',trash,mirror,window)
 left_foot=S.box(L.foot,window);tb=S.box(trash,window)
 rows+=S.same('Trash · inset from the pane edge beside the workspace and from the bottom',[left_foot[0]+left_foot[2]-(tb[0]+tb[2]),left_foot[1]+left_foot[3]-(tb[1]+tb[3]),d.inset],'inset')
 occupied=[c for c in R.foot.findChildren(QWidget) if c.isVisible()]
 rows+=S.same('the right foot holds no control (Trash\'s mirror is kept empty)',[len(occupied),0],'widgets')
 return rows

BRANCH=QColor(pane_qt.BRANCH).rgb()
def tree_pairs(window=None):
 """D1b: the three left trees, each measured while it is the active one: the same box, indentation, row height, and the same
 branch line drawn down the first level's column (pencil-grey pixels at indentation // 2 in the tree's own grab)."""
 window=window or w;S=symmetry;nav=window.settings_navigator;before=nav.current_view();boxes=[];indents=[];heights=[];columns=[];found={}
 for view,tree in zip(('machine','cabinet','settings'),window.desk_trees):
  nav.show_view(view,persist=False)
  if view=='machine':window.machine_page.build()
  if view=='cabinet' and window.cabinet_page.using_legacy:window.cabinet_page.set_legacy(False,persist=False)
  settle();assert tree.isVisible(),view
  first=tree.topLevelItem(0);first.setExpanded(True);settle()
  boxes.append(S.box(tree,window));indents.append(tree.indentation());heights.append(tree.visualItemRect(first).height())
  image=tree.viewport().grab().toImage();x=tree.indentation()//2
  # 0.5.1: the branches are green circuit traces (pane_qt.draw_branches), drawn smooth, not one-pixel lines of one exact
  # grey: a row of the trunk's column counts when a pixel there, or beside it, is plainly green.
  def trace(px):
   c=QColor(px);return c.green()>c.red()+12 and c.green()>c.blue()+12
  hits=sum(1 for y in range(image.height()) if any(trace(image.pixel(x+dx,y)) for dx in (-1,0,1) if 0<=x+dx<image.width()));columns.append(x);found[view]=hits
 nav.show_view(before,persist=False);settle()
 rows=[]
 for field,index in (('left edge',0),('top',1),('width',2),('height',3)):rows+=S.same('trees · '+field,[b[index] for b in boxes],field)
 rows+=S.same('trees · indentation',indents,'indent')+S.same('trees · row height',heights,'height')+S.same('trees · the first level\'s branch column',columns,'x')
 # The right pane's list (Activity's Timeline lines) uses the trees' row height, and shows its lines whole (the plan's rule 7).
 recent=window.operations_panel.recent;assert recent.count()>0,'Activity lists at least the Timeline\'s opening line'
 shown=min(recent.SHOWN,recent.count())
 rows+=S.same('the right pane\'s list · Activity\'s lines and the trees: one row height',[heights[0]]+[recent.sizeHintForRow(i) for i in range(recent.count())],'height')
 rows+=S.same('the right pane\'s list · its lines whole',[recent.viewport().height(),shown*heights[0]],'height')
 assert all(n>0 for n in found.values()),('the branch lines are drawn in every tree',found)
 return rows,dict(indent=indents[0],row=heights[0],box=list(boxes[0]),branch_pixels=found,activity_row=recent.sizeHintForRow(0),activity_lines=shown)

def grain_check(window=None):
 """The two bands: the same tile, phase-aligned. Where neither band draws a word, a pixel of the head and the pixel at the same
 place in the lower band are equal, and both equal the tile's pixel at that place (the tile starts at each band's top-left)."""
 window=window or w;image=window.grab().toImage();top=window.shell2.top;b=window.type_bar;W=window.width()
 hy=window.ribbon_dock.mapTo(window,QPoint(0,0)).y();ly=window.type_dock.mapTo(window,QPoint(0,0)).y();H=window.type_dock.height()
 covered=set()
 for widget in [top.wordmark,top.menus,top.pulse_holder,top.nice,b.hatch,b.box]+[x for pair_ in b.rows() for part in pair_ for x in part]:
  if widget.isVisible():
   x,_,ww,_=symmetry.box(widget,window);covered.update(range(max(0,x-2),min(W,x+ww+2)))
 tile=desk_qt.grain_tile().toImage();tw,th=tile.width(),tile.height()
 free=[x for x in range(0,W,2) if x not in covered];same=differ=off_tile=0;head_sum=low_sum=0
 for x in free:
  for y in range(0,H,2):
   a=image.pixel(x,hy+y);c=image.pixel(x,ly+y);t=tile.pixel(x%tw,y%th)
   same+=a==c;differ+=a!=c;off_tile+=a!=t;head_sum+=QColor(a).lightness();low_sum+=QColor(c).lightness()
 n=same+differ
 return dict(columns_compared=len(free),pixels_compared=n,equal=same,different=differ,head_not_tile=off_tile,
  head_mean_lightness=round(head_sum/max(1,n),3),lower_mean_lightness=round(low_sum/max(1,n),3))

def overlay(name,note,window=None):
 """The window with the axis (eraser pink) and the mirrored guides (pencil yellow): the pane edges, the band slots' insets, the
 centre column's inset, the menu row's and the writing line's ends, and both bands' edges."""
 window=window or w;pix=window.grab();p=QPainter(pix);W=window.width();Hh=window.height();d=window.desk;top=window.shell2.top;b=window.type_bar
 axis=QPen(QColor(desk_qt.ERASER_MARK),2);guide=QPen(QColor('#c99a2e'),1,Qt.DashLine);p.setPen(guide)
 xs={0+d.inset,d.pane-d.inset,d.pane,d.pane+d.line}
 menus=shown_menus(top);xs.add(ink_span(menus[0],window)[0])
 for x in sorted(xs):
  for m in (x,W-x):p.drawLine(m,0,m,Hh)
 for y in (window.ribbon_dock.height(),window.type_dock.mapTo(window,QPoint(0,0)).y()):p.drawLine(0,y,W,y)
 p.setPen(axis);p.drawLine(W//2,0,W//2,Hh)
 if W%2:p.drawLine(W//2+1,0,W//2+1,Hh)
 font=QFont('IBM Plex Sans');font.setPixelSize(14);font.setWeight(QFont.DemiBold);p.setFont(font);y=window.ribbon_dock.height()+10
 for text,colour,x in (('axis  x = %d / 2'%W,desk_qt.ERASER_MARK,W//2+8),('both panes P = %d · inset %d · menus and line inset %d · band %d'%(d.pane,d.inset,d.line,d.band),'#9a6f12',d.pane+d.line+8)):
  r=p.boundingRect(QRectF(x,y,900,24),Qt.AlignLeft|Qt.AlignVCenter,text).adjusted(-6,-3,6,3)
  p.fillRect(r,QColor('#fffdf8'));p.setPen(QColor(colour));p.drawRect(r);p.drawText(r,Qt.AlignCenter,text);y+=34
 p.end();record(name,note,pix.toImage(),'ACTUAL_QT_WINDOW_GRAB_WITH_DRAWN_GUIDES')

w.resize(1920,1200);w.show();settle(120);bridge.timer.stop();bar.hatch.lifecycle.timer.stop();align();w.activateWindow();settle()
w.show_start();settle();align()
assert w._home_active and type(w.central_stack.currentWidget()).__name__=='FinderPage'
home=w._empty_home_page
# 01 · the nine sizes: every mirrored pair at zero, every drawn item as designed, every word whole, nothing sideways ---------------
sh=w.shell2;console=w.console
def faces_and_sizes(key):
 """At one size (D1-fix: the review found the right pane checked with Activity only, and Half, Tall and the System menu's list
 at one size): the right pane with Conversation and with Context (the pane pairs, its words whole, its script whole, nothing in
 it sideways), Half and Tall (every desk pair), and the System menu's list (it opens under the symbol, its right edge the
 band's inset from the window's)."""
 out={};W=w.width();d=w.desk
 for name,face in (('Conversation',sh.face),('Context',w.arc_inspector)):
  w.console_pages.setCurrentWidget(face);face.refresh();settle();align(2)
  rows=pane_pairs()+script_labels();words=ui_fit.whole_words(w.sim_dock);sideways=ui_fit.side_scrolls(w.sim_dock)
  out[name]=dict(pairs=len(rows),asymmetric=symmetry.worst(rows),clipped=words,sideways=sideways)
  assert not symmetry.worst(rows) and not words and not sideways,(key,name,symmetry.table(symmetry.worst(rows)),ui_fit.describe(words+sideways))
 w.console_pages.setCurrentWidget(w.operations_panel);w.operations_panel.refresh();settle();align(2)
 for level,word in ((1,'Half'),(2,'Tall')):
  console.set_size(level);settle();align(2);rows=desk_pairs();out[word]=dict(pairs=len(rows),asymmetric=symmetry.worst(rows))
  assert not symmetry.worst(rows),(key,word,symmetry.table(symmetry.worst(rows)))
 console.set_size(0);settle();align(2)
 sym=sh.top.nice;sym.open();settle(40);popup=sym.popup;pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)))
 out['System menu']=dict(right_edge=pos.x()+popup.width(),top=pos.y(),window=W,inset=d.inset,band=w.ribbon_dock.height())
 assert pos.x()+popup.width()==W-d.inset and pos.y()==w.ribbon_dock.height(),(key,out['System menu'])
 popup.hide();w.tabs.setFocus();settle()
 return out
def writing_line_pairs(key):
 """HATCH DESK D3 at one size (the owner: "Be obsessive in symmetry"): with each of the writing line's four modes chosen (only
 its word marked, by the short pencil-yellow mark) in Line, Half and Tall, every desk pair measures 0 px (the mode words and
 Line · Half · Tall mirrored in inset by their ink, the writing line centred on the axis, one baseline); in Line every band
 word is drawn as designed; in Half and Tall the working area (the Log view, the console's answers) shows every word whole and
 nothing sideways, and Log's note (the script, its keys printed) is whole in its label. Log is measured on both of its streams.
 The integration: no wrapped label in the working area is given fewer lines than its words need (ui_fit.cut_lines; Log's
 capture reason was cut to two lines where the lists stand one above the other)."""
 out={};before=bar.target;view=w.log_view;stream=view.stream
 for mode,streams in (('slate',(None,)),('shell',(None,)),('find',(None,)),('log',('events','network'))):
  bar.set_target(mode,focus=False);settle()
  for chosen in streams:
   if chosen:view.choose(chosen,remember=False,read=False)
   for level,word in ((0,'Line'),(1,'Half'),(2,'Tall')):
    console.set_size(level);settle();align(2)
    rows=desk_pairs()+(drawn_as_designed() if level==0 else [])+(script_labels() if level and mode=='log' else []);bad=symmetry.worst(rows)  # Log's note: the script, whole
    area=[x for x in (view,console.output) if x.isVisible()]
    clipped=[c for x in area for c in ui_fit.whole_words(x)+ui_fit.cut_lines(x)] if level else [];sideways=[c for x in area for c in ui_fit.side_scrolls(x,allow=(console.output,))] if level else []  # a terminal's answers scroll sideways by design
    marked=[b_.text() for b_ in bar.targets.values() if desk_qt.InkWord.marked(b_)]
    name='%s%s %s'%(bar.labels[mode],(' · '+chosen) if chosen else '',word);out[name]=dict(pairs=len(rows),asymmetric=bad,clipped=clipped,sideways=sideways,marked=marked)
    assert not bad,(key,name,symmetry.table(bad))
    assert not clipped and not sideways,(key,name,ui_fit.describe(clipped+sideways))
    assert marked==[bar.labels[mode]] and desk_qt.InkWord.marked(bar.targets[mode])==desk_qt.PENCIL,(key,name,marked)
    assert (level>0)==(area!=[]) and (view.isVisible() if level else True)==(mode=='log' or level==0),(key,name,'the working area shows the mode\'s page in Half and Tall')
 view.choose(stream,remember=False,read=False);console.set_size(0);bar.set_target(before,focus=False);settle();align(2)
 return out
def menu_pairs(key):
 """HATCH DESK D2, Symmetry rule 6 at one size: the cat's programs list (upward from the lower left) and the System menu (downward
 from the upper right) are point-mirror images: the list's left edge and the System menu's right edge the band's inset from the
 window's edges; the list's foot on the lower band's top and the System menu's top on the head band's foot (the same band
 height); one width (programs_qt.menu_width: the panes' content column, or the widest row of either); one row height; one icon
 column (the icon's place and size, the words' start); the same margins at both ends; each menu's small caption at its far end
 (the list's top, the System menu's foot), one height; every word in both whole and nothing in them sideways."""
 from workbench import programs_qt
 W=w.width();H=w.height();d=w.desk;S=symmetry;hatch=bar.hatch;sym=sh.top.nice;out={};found=[]
 lst=hatch.programs;hatch.open_list(False);settle()
 a=w.mapFromGlobal(lst.mapToGlobal(QPoint(0,0)));la=(a.x(),a.y(),lst.width(),lst.height());found+=ui_fit.whole_words(lst)+ui_fit.side_scrolls(lst)
 lrows=lst.rows();lst.close_menu();settle()
 menu=sym.open(False);settle();b=w.mapFromGlobal(menu.mapToGlobal(QPoint(0,0)));mb=(b.x(),b.y(),menu.width(),menu.height())
 found+=ui_fit.whole_words(menu)+ui_fit.side_scrolls(menu);mrows=menu.rows();menu.close_menu();w.tabs.setFocus();settle()
 rows=S.same('menus · the side inset (the list\'s left edge, the System menu\'s right edge)',[la[0],W-(mb[0]+mb[2]),d.inset],'inset')
 rows+=S.same('menus · the band\'s height (the list\'s foot above the window\'s foot, the System menu\'s top under the window\'s top)',[H-(la[1]+la[3]),mb[1],w.type_dock.height(),w.ribbon_dock.height()],'band')
 rows+=S.same('menus · one width (the width rule)',[la[2],mb[2],programs_qt.menu_width(w)],'width')
 rows+=S.same('menus · as tall as their rows, never over a band',[min(la[3],H-2*d.band)-la[3],min(mb[3],H-2*d.band)-mb[3]],'height')
 rows+=S.same('menus · one row height',[r.height() for r in lrows+mrows],'height')
 rows+=S.same('menus · the icon column: the icon\'s left edge',[r.icon_rect().x() for r in lrows+mrows],'x')+S.same('menus · the icon column: the icon\'s size',[r.icon_rect().width() for r in lrows+mrows],'width')
 rows+=S.same('menus · the icon column: the words\' start',[r.word_x() for r in lrows+mrows],'x')
 rows+=S.same('menus · the list\'s rows as wide as its page',[r.width() for r in lrows]+[lst.page.width()],'width')+S.same('menus · the System menu\'s rows as wide as its page',[r.width() for r in mrows]+[menu.page.width()],'width')
 m1=lst.margins();m2=menu.margins()
 rows+=S.same('menus · the margins at both ends',[*m1,*m2,lst.m.margin],'margin')
 rows+=S.same('menus · the small caption at the far end (the list\'s top, the System menu\'s foot)',[lst.items().index(lst.caption),len(menu.items())-1-menu.items().index(menu.caption)],'index')
 rows+=S.same('menus · the small caption\'s height',[lst.caption.height(),menu.caption.height()],'height')
 out=dict(programs=list(la),system=list(mb),row=lrows[0].height(),icon=[lrows[0].icon_rect().x(),lrows[0].icon_rect().width()],words_x=lrows[0].word_x(),
  width_rule=dict(column=programs_qt.column(w),programs_need=programs_qt.programs_need(lst.m),system_need=__import__('workbench.system_menu_qt',fromlist=['words_need']).words_need(menu.m)),
  scrolls=dict(programs=lst.scroll.verticalScrollBar().maximum()>0,system=menu.scroll.verticalScrollBar().maximum()>0),pairs=len(rows),asymmetric=symmetry.worst(rows),clipped=found)
 assert not symmetry.worst(rows),(key,symmetry.table(symmetry.worst(rows)),dict(list_margins=list(m1)+[lst.m.margin],system_margins=list(m2)+[menu.m.margin]))
 assert not found,(key,ui_fit.describe(found))
 return out
for points in POINTS:
 if points!=14:ui_pt(points)
 for size in SIZES:
  w.resize(*size);settle(60);align(4);home.go('today');settle();align(2);w.tabs.setFocus();settle()
  assert (w.width(),w.height())==size,(w.size(),size)
  trees,tree_metrics=tree_pairs();key='%dx%d %dpt'%(size[0],size[1],points);d=w.desk
  rows=desk_pairs()+trees+tab_marks()+drawn_as_designed()+band_edges_drawn()+trash_drawn()+cat_poses_inside()+script_labels()+script_contrast();bad=symmetry.worst(rows)
  words=ui_fit.whole_words(w);sideways=ui_fit.side_scrolls(w.central_stack)+ui_fit.side_scrolls(w.nav_dock)+ui_fit.side_scrolls(w.sim_dock)
  (lp_,ls_),(rp_,rs_)=bar.rows()
  measured[key]=dict(pane=d.pane,workspace=d.workspace,band=d.band,inset=d.inset,line_inset=d.line,gap=d.gap,menus_on_column=w.shell2.top.plan[4] is not None,
   folded=[h.text() for h in w.shell2.top.folded_menus],centre_width=w.centralWidget().width(),pairs=len(rows),asymmetric=bad,clipped=words,sideways=sideways,
   band_words=dict(px=bar.px,full=desk_qt.letter_px(d.scale),floor=desk_qt.letter_floor(d.scale),words=[x.text() for x in ls_+rp_+rs_],ink=[list(ink_span(x,w)[:2]) for x in ls_+rp_+rs_],cat_at_rest=list(cat_span(w))),
   menus_ink=[list(ink_span(m,w)[:2]) for m in shown_menus(w.shell2.top)],writing_line=[symmetry.box(bar.box,w)[0],sum(symmetry.box(bar.box,w)[0:3:2])],
   drawn_as_designed={k:v for k,v in DESIGNED.items() if k not in ('cat poses','script labels','script contrast','band edges drawn')},cat_poses=DESIGNED.get('cat poses'),band_edges_drawn=DESIGNED.get('band edges drawn'),
   script_labels=DESIGNED.get('script labels'),script_contrast=DESIGNED.get('script contrast'),
   panes=dict(tab_width=w.panes['T'],tab_gap=w.panes['gap'],tab_px=w.panes['tab_px'],menu_px=w.panes['tab_px_top'],tab_height=w.panes['tab_height'],mark=list(w.panes['mark']),
    tab_row=[w.left_pane.tabs.buttons[0].x(),w.left_pane.tabs.buttons[2].x()+w.panes['T']],trash=[w.trash_can.width(),w.trash_can.height()],trash_box=list(symmetry.box(w.trash_can,w)),foot=w.panes['foot'],trees=tree_metrics),
   rows=[dict(pair=r['pair'],field=r['field'],difference=r['difference']) for r in rows])
  # Rule 4's choice, measured: the menu row keeps the axis by itself (it is laid out on the workspace column), and the CPU · GPU ·
  # RAM · TXT block stays inside the right slot beside the symbol; how far each side's group reaches in from its edge is recorded.
  top_=w.shell2.top;W_=w.width();wm=symmetry.box(top_.wordmark,w);pl=symmetry.box(top_.pulse_holder,w);sy=symmetry.box(top_.nice,w)
  mi=[ink_span(m,w) for m in shown_menus(top_)];mr=(mi[0][0],0,mi[-1][1]-mi[0][0],0)  # the menu row by its ink (D1-fix: the words are placed by it)
  measured[key]['head_balance']=dict(graphite_word=[wm[0],wm[0]+wm[2]],monitors_and_symbol=[pl[0],sy[0]+sy[2]],left_group_reach=wm[0]+wm[2],right_group_reach=W_-pl[0],
   menu_row=[mr[0],mr[0]+mr[2]],menu_row_centre_offset=(mr[0]-(W_-mr[0]-mr[2]))/2,menu_row_clear_of_left_group=mr[0]-(wm[0]+wm[2]),menu_row_clear_of_right_group=pl[0]-(mr[0]+mr[2]),
   as_drawn=dict(DRAWN),word=dict(family=top_.wordmark.font().family(),px=top_.wordmark.font().pixelSize(),stroke=top_.wordmark.stroke))
  assert measured[key]['head_balance']['menu_row_centre_offset']==0 and measured[key]['head_balance']['menu_row_clear_of_right_group']>=d.gap and measured[key]['head_balance']['menu_row_clear_of_left_group']>=d.gap,measured[key]['head_balance']
  assert not bad,(key,symmetry.table(bad))
  assert not words,(key,ui_fit.describe(words))
  assert not sideways,(key,ui_fit.describe(sideways))
  assert all(x.text()==bar.words[x] for x in ls_+rp_+rs_),(key,'every lower-band word whole',[x.text() for x in ls_+rp_+rs_])
  assert w.nav_dock.width()==w.sim_dock.width()==d.pane and d.workspace==w.width()-2*d.pane-2,(key,w.nav_dock.width(),w.sim_dock.width(),d)
  if (points,size)==(14,(1920,1200)):
   record('Graphite_Desk_01_1920x1200.png','The desk at 1920 by 1200, 14 pt, both launch menus closed: the two graphite bands, Graphite in the script at the upper left and the erased symbol at the far right, the eight menus across the workspace with their ink on the writing line\'s ends, the two panes %d px each, Activity quiet, Trash at the left pane\'s lower right.'%d.pane,w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
   overlay('Graphite_Desk_03_Symmetry_Overlay_1920x1200.png','The same desk with the axis (pink) and the mirrored guides (yellow, dashed): the band insets, the pane edges, the workspace column\'s inset shared by the menus\' ink and the writing line, and the band edges. Every pair measured 0 px.')
  if (points,size)==(14,(1366,768)):
   record('Graphite_Desk_02_1366x768.png','The desk at 1366 by 768, 14 pt, both launch menus closed: the panes %d px each, the workspace %d px, every word whole, the menus on the workspace column.'%(d.pane,d.workspace),w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
  if (points,size)==(20,(1280,800)):
   overlay('Graphite_Desk_04_Symmetry_Overlay_1280x800_20pt.png','The tightest case, 1280 by 800 at 20 pt: the panes %d px, the workspace %d px, the lower band\'s words at %d px so every one is whole, the menus %s; every pair 0 px.'%(d.pane,d.workspace,bar.px,('fold '+' · '.join(measured[key]['folded'])+' into ⋯') if measured[key]['folded'] else 'all whole'))
  measured[key]['faces_and_sizes']=faces_and_sizes(key)
  measured[key]['writing_line']=writing_line_pairs(key)  # HATCH DESK D3: every mode chosen, in Line, Half and Tall
  measured[key]['menus']=menu_pairs(key)  # HATCH DESK D2: Symmetry rule 6, the programs list and the System menu
  print(key,'pane',d.pane,'workspace',d.workspace,'band',d.band,'band words',bar.px,'pairs',len(rows),'folded',measured[key]['folded'],flush=True)
ui_pt(14);w.resize(1920,1200);settle(60);align(4)
check('01 At 1920 by 1200, 1366 by 768 and 1280 by 800, each at 14, 18 and 20 pt: every mirrored pair of the panes, the bands, the head and the lower band (the band words by their ink and the cat by its pale coat, both again in the window\'s own pixels; the word Graphite and the symbol by their outline and optical size), of the panes\' tabs, marks, contents, feet, Trash\'s empty mirror, the three trees and Activity\'s list rows measures 0 px (%d rows at each); every drawn item (the word, the symbol, every menu and band word, the cat, Trash) matches its design in the window\'s pixels and the chosen tabs\' yellow marks mirror; every pose of the cat lies inside the band with its padding; no script word is cut by its label; every word in the window is whole (the lower band\'s words smaller in a narrow window, never elided) and nothing in the workspace or either pane scrolls sideways; with Conversation and with Context the right pane\'s pairs hold too, Half and Tall keep every pair, and the System menu\'s list opens under the symbol at the band\'s inset'%len(desk_pairs()+tree_pairs()[0]+tab_marks()+drawn_as_designed()+band_edges_drawn()+trash_drawn()+cat_poses_inside()+script_labels()+script_contrast()))
# 02 · the grain: one tile, phase-aligned in both bands; the lettering's contrast on it ------------------------------------------
grain=grain_check();report=desk_qt.grain_report()
assert grain['pixels_compared']>2000 and grain['different']==0 and grain['head_not_tile']==0 and grain['head_mean_lightness']==grain['lower_mean_lightness'],grain
assert report['contrast']['lettering']['on_mean']>=4.5 and report['contrast']['quiet lettering']['on_mean']>=4.5 and report['contrast']['quiet lettering']['on_light_grain']>=4.5,report
assert report['contrast']['action mark']['on_mean']>=3 and report['contrast']['active mark']['on_mean']>=3,report  # marks are graphics: 3:1
check('02 Both bands are the one grain tile from their own top-left: %d pixels in %d columns where no word is drawn are equal in both bands and equal the tile (mean lightness %s in each); the lettering %s:1 and the quiet lettering %s:1 on the mean tone (%s:1 and %s:1 on the lightest 5%% of the grain); the pink action mark %s:1 and the yellow active mark %s:1'%(
 grain['pixels_compared'],grain['columns_compared'],grain['head_mean_lightness'],report['contrast']['lettering']['on_mean'],report['contrast']['quiet lettering']['on_mean'],
 report['contrast']['lettering']['on_light_grain'],report['contrast']['quiet lettering']['on_light_grain'],report['contrast']['action mark']['on_mean'],report['contrast']['active mark']['on_mean']))
# 03 · Half and Tall grow the working area above the lower band; the band keeps its height --------------------------------------
console=w.console;heights={};band_top={}
for level,word in ((0,'Line'),(1,'Half'),(2,'Tall'),(0,'Line again')):
 console.sizes[level].click();settle();align(2)
 heights[word]=console.tail.list.height() if console.mode=='log' else console.output.height();band_top[word]=(w.type_dock.mapTo(w,QPoint(0,0)).y(),w.type_dock.height(),w.ribbon_dock.height())
 assert not symmetry.worst(desk_pairs()),(word,symmetry.table(symmetry.worst(desk_pairs())))
assert heights['Line']<heights['Half']<heights['Tall'] and heights['Line again']==heights['Line'],heights
assert len(set(band_top.values()))==1,band_top
check('03 Line, Half and Tall: the console above the band is %d, %d and %d px; the lower band stays %d px at y=%d and the pairs stay at 0 px'%(heights['Line'],heights['Half'],heights['Tall'],band_top['Line'][1],band_top['Line'][0]))
# 04 · a drag of either separator moves both panes; save and reopen restores them ------------------------------------------------
def drag(side,dx):
 d=w.desk;y=w.nav_dock.geometry().center().y();x=d.pane if side=='left' else w.width()-d.pane-1;start=QPoint(x,y);end=start+QPoint(dx,0)
 QTest.mousePress(w,Qt.LeftButton,Qt.NoModifier,start);QTest.qWait(20);QTest.mouseMove(w,start+QPoint(dx//2,0));QTest.qWait(20)
 mid=[w.nav_dock.width(),w.sim_dock.width()]
 QTest.mouseMove(w,end);QTest.qWait(20);QTest.mouseRelease(w,Qt.LeftButton,Qt.NoModifier,end);settle();align()
 return mid
cursors=separator_cursors()
assert all(on==Qt.SplitHCursor and off==Qt.BitmapCursor for on,off in cursors.values()),cursors
before=w.desk.pane;mid=drag('left',40);after_left=[w.nav_dock.width(),w.sim_dock.width()]
assert mid[0]==mid[1]==before+20 and after_left==[before+40,before+40] and bar.pane_owner==before+40,(before,mid,after_left,bar.pane_owner)
mid2=drag('right',30);after_right=[w.nav_dock.width(),w.sim_dock.width()]
assert mid2[0]==mid2[1] and after_right==[before+10,before+10],(mid2,after_right)
assert not symmetry.worst(desk_pairs()),symmetry.table(symmetry.worst(desk_pairs()))
ui_pt(18);settle();assert w.nav_dock.width()==w.sim_dock.width()>=before+10;ui_pt(14);assert [w.nav_dock.width(),w.sim_dock.width()]==after_right,(after_right,w.nav_dock.width())
w.save_session();saved=dict(w.session.layout);assert saved['navigator_width']==saved['simulator_width']==before+10,saved
check('04 Over either pane separator the window shows the horizontal resize cursor and its own pointer again off it; dragging the left pane\'s edge 40 px widened both panes together (%d/%d halfway, %d/%d after); dragging the right pane\'s edge 30 px narrowed both (%d/%d); an excursion to 18 pt and back kept the owner\'s width; the session saved %d for both'%(mid[0],mid[1],*after_left,*after_right,before+10))
# 05 · Ctrl+K reaches searching; the System menu's symbol; the game's route --------------------------------------------------------
ctrl_k=ctrl_k_line();assert ctrl_k['ok'],ctrl_k
console.set_size(0);settle();align()
top=w.shell2.top;sym=top.nice
assert isinstance(sym,SystemButton) and sym.isVisible() and sym.accessibleName()==sym.toolTip()=='System menu' and sym.text()=='' and not w.global_search.isVisible()
assert sym.width()==w.desk.symbol and top.wordmark.text()=='Graphite' and top.wordmark.isVisible() and not top.mark.isVisible()
sym.setFocus();settle();QTest.keyClick(sym,Qt.Key_Return);settle(60);popup=sym.popup
assert popup is not None and popup.isVisible() and popup.items()[0] is popup.game and popup.items()[1] is popup.kill and popup.kill.text()==KILL_WORDS and app.focusWidget() is popup.game  # D2: Game first, Stop all jobs directly beneath
pos=w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0)));assert pos.x()+popup.width()==w.width()-w.desk.inset,(pos.x(),popup.width(),w.width())  # it opens down from the upper right, under the symbol's right edge
with patch.object(struthio_qt,'show') as game:QTest.mouseClick(popup.game,Qt.LeftButton);settle()
assert game.call_count==1 and game.call_args[0][0] is w and not popup.isVisible(),game.call_args_list
check('05 Ctrl+K puts the cursor in the writing line in Search (D3: Search marked by the short yellow mark, the words typed after it go to Search, the session remembers Search like any mode); the erased symbol (%d px) at the far right is the System menu: Return opens it with Game first and focused and %s directly beneath, right-aligned under it; its Game row opens STRUTHIO (struthio_qt.show called once, patched); the head\'s old mark is out of sight'%(sym.width(),KILL_WORDS))
# 06 · the panes with each tab, for the owner (D1b) ----------------------------------------------------------------------------------
w.show_start();settle();align()
project=call('projects.create',{'title':'Bench notes','intent':'Try a short poem as a quick test.'})
idea=call('ideas.capture',{'project':project['id'],'text':'A poem about pencils, for the bench'})
w.cabinet_page.refresh(force=True);settle()
sh=w.shell2;nav=w.settings_navigator;L=w.left_pane;R=w.right_pane;PENCIL=QColor(desk_qt.PENCIL).rgb()
def pane_image(pane):
 box=symmetry.box(pane,w);return w.grab().toImage().copy(*box)
def marked(pane,button):
 """The chosen tab's short mark is drawn in pencil yellow in the window (its middle pixel), the others' are not."""
 image=w.grab().toImage();out=[]
 for b in pane.tabs.buttons:
  r=b.mark_rect();x,y=b.mapTo(w,QPoint(r.center().x(),r.center().y())).toTuple();out.append(image.pixel(x,y)==PENCIL)
 return out==[b is button for b in pane.tabs.buttons],out
def sheet(images,labels,title):
 """The pane images side by side under their tab names (the captures are the window's own pixels, cut at the pane)."""
 gap=24;head=44;width=sum(i.width() for i in images)+gap*(len(images)+1);height=max(i.height() for i in images)+head+gap
 out=QImage(width,height,QImage.Format_RGB32);out.fill(QColor('#e9e4d8'));p=QPainter(out);font=QFont('IBM Plex Sans');font.setPixelSize(16);font.setWeight(QFont.DemiBold);p.setFont(font)
 x=gap
 for image,label in zip(images,labels):
  p.setPen(QColor(pane_qt.TEXT));p.drawText(QRectF(x,8,image.width(),28),Qt.AlignLeft|Qt.AlignVCenter,label);p.drawImage(x,head,image);p.setPen(QColor(pane_qt.LINE));p.drawRect(x-1,head-1,image.width()+1,image.height()+1);x+=image.width()+gap
 p.end();return out
w.tabs.setFocus();rights=[];right_names=[]
for name,show,face in (('Conversation',sh.show_slate_face,sh.face),('Activity',sh.show_operations_face,w.operations_panel),('Context',sh.show_context_face,w.arc_inspector)):
 show();w.tabs.setFocus();settle(60);align()
 button=next(b for b in R.tabs.buttons if b.text()==name);ok,seen=marked(R,button)
 assert w.console_pages.currentWidget() is face and button.isChecked() and ok,(name,seen)
 assert not symmetry.worst(pane_pairs()),(name,symmetry.table(symmetry.worst(pane_pairs())))
 rights.append(pane_image(R));right_names.append(name)
lefts=[];left_names=[]
for view in ('machine','cabinet','settings'):
 nav.show_view(view);settle(40)
 if view=='machine':w.machine_page.build(force=True);w.machine_page.tree.setCurrentItem(w.machine_page.items['storage']);w.machine_page.items['storage'].setExpanded(True)
 if view=='cabinet':w.cabinet_page.select('idea:'+idea['id'],reveal=True)
 w.tabs.setFocus();settle(60);align()
 button=getattr(nav,view);ok,seen=marked(L,button)
 assert nav.current_view()==view and button.isChecked() and ok,(view,seen)
 visible=[c for c in L.content.findChildren(QWidget) if c.isVisible() and type(c).__name__ in ('QLineEdit','QPushButton','QLabel','QPlainTextEdit','StripLabel','MachineStrip')]
 assert not visible,(view,'the left pane shows only its tabs, the active tree and Trash',[(type(c).__name__,c.text() if hasattr(c,'text') else '') for c in visible])
 lefts.append(pane_image(L));left_names.append(view.title())
assert not ui_fit.whole_words(w.nav_dock) and not ui_fit.whole_words(w.sim_dock),ui_fit.describe(ui_fit.whole_words(w.nav_dock)+ui_fit.whole_words(w.sim_dock))
record('Graphite_Desk_05_Left_Pane_Tabs_1920x1200.png','The left pane at 1920 by 1200 with each of its tabs: Machine, Cabinet and Settings, each showing only the tab row, the active tree with its connecting branch lines (the cabinet with a project and its idea opened), and the larger Trash at the lower right; the chosen tab carries the short yellow mark.',
 sheet(lefts,left_names,'left'),'ACTUAL_QT_WINDOW_GRABS_CUT_AT_THE_PANE')
record('Graphite_Desk_06_Right_Pane_Tabs_1920x1200.png','The right pane at 1920 by 1200 with each of its tabs: Conversation (the Graphite face), Activity (the Operations panel\'s work, the Work block when an assignment runs, the Timeline\'s last lines, Organizer, Return thread, Follow latest) and Context; its foot, where Trash stands in the left pane, is empty.',
 sheet(rights,right_names,'right'),'ACTUAL_QT_WINDOW_GRABS_CUT_AT_THE_PANE')
nav.show_view('cabinet');sh.show_operations_face();settle();align()
check('06 Both panes: the left shows Machine · Cabinet · Settings with only the active tree (connecting branch lines) and Trash, the right Conversation · Activity · Context with the faces; the chosen tab of each carries the pencil-yellow mark (measured in the window\'s pixels) and every pane pair stays 0 px with each tab chosen')
# 07 · homes: every action a removed pane control reached is reached from its new place (D1b) --------------------------------------
homes={}
work_menu=w.menu_groups['File'];arrange=w.menu_groups['Options']
assert w.a_import in work_menu.actions() and w.a_export in work_menu.actions(),'Import and Export are Work menu entries'
with patch.object(shell2,'open_destination') as opened:
 w.a_import.trigger();w.a_export.trigger()
assert [c.args[1] for c in opened.call_args_list]==['office','files:Egress'],opened.call_args_list
homes['Import']='Work ▸ Import (Ingress)… → the Office (Ingress), the transfer\'s own destination';homes['Export']='Work ▸ Export (Egress)… → Files ▸ Egress, the transfer\'s own destination'
assert w.cabinet_menu.menuAction() in arrange.actions() and w.a_machine_refresh in arrange.actions()
w.cabinet_menu.aboutToShow.emit();assert [a.text() for a in w.cabinet_menu.actions() if not a.isSeparator()][:2]==['Logical Cabinet','Existing Views']
w.a_cabinet_existing.trigger();settle();assert w.cabinet_page.using_legacy and nav.current_view()=='cabinet' and w.nav.isVisible()
w.cabinet_menu.aboutToShow.emit();assert w.a_cabinet_existing.isChecked()
w.a_cabinet_logical.trigger();settle();assert not w.cabinet_page.using_legacy and w.cabinet_page.tree.isVisible()
with patch.object(type(w.cabinet_page),'refresh') as refreshed:w.a_cabinet_refresh.trigger()
assert refreshed.call_args.kwargs.get('force') is True,refreshed.call_args
before_build=w.machine_page.built_at;time.sleep(0.01);w.a_machine_refresh.trigger();settle();assert nav.current_view()=='machine' and w.machine_page.built_at>before_build
homes['Refresh cabinet']='Arrange ▸ Cabinet ▸ Refresh Cabinet';homes['Logical cabinet / Existing views']='Arrange ▸ Cabinet ▸ Logical Cabinet / Existing Views (with the Existing views\' catalogue choice and Concern Overview)'
homes['Refresh machine view']='Arrange ▸ Refresh Machine View (shows the Machine tab)'
console=w.console;console.output.clear();console.run_find('Bench notes');found=console.output.toPlainText()
assert 'CABINET · ' in found and 'Bench notes' in found,found[:400]
console.output.clear();console.run_find('Interface text');found=console.output.toPlainText();assert 'SETTINGS · ' in found and 'reading.ui_pt' in found,found[:400]
homes['Find work… (the cabinet query)']='the writing line\'s Find (Ctrl+K): a CABINET section with each matching record, open selects it in the cabinet and opens it'
homes['Find a setting… (the settings filter)']='the writing line\'s Find: a SETTINGS section, open shows the setting'
panel=w.operations_panel;tail=w.ledger_bridge.tail
for name,widget in (('the Timeline line',tail.heading),('Follow latest',tail.follow),('Organizer (the foot\'s word)',tail.trail),('Return thread',w.return_thread.footer),('the Work block',sh.face.work),('the recent lines',panel.recent)):
 assert panel.isAncestorOf(widget),name
homes['Centre foot (Timeline, Return thread, Follow latest, Work trail)']='Activity: the Timeline line and its last lines, Return thread, Follow latest; the foot\'s word opened the Organizer and says so now (the Work trail room is Activity\'s work list word)'
nav.show_machine();settle();strip=w.machine_strip;strip.refresh()
assert strip.label.full and strip.label.full in w.machine_page.items['machine'].toolTip(0),(strip.label.full,w.machine_page.items['machine'].toolTip(0)[:200])
homes['The machine strip']='Machine: the Machine row\'s tooltip carries the line; its facts are the Processor, Memory, Storage and Connections rows'
page=w.cabinet_page;assert nav.cabinet.toolTip().startswith('Cabinet · ') and page.status.text() in nav.cabinet.toolTip()
homes['The cabinet\'s status line']='the Cabinet tab\'s tooltip'
hidden=[('the cabinet query',page.query),('the cabinet status',page.status),('Refresh cabinet',page.refresh_button),('Logical cabinet',page.logical),('Existing views',page.legacy),
 ('Import',page.transfer_buttons[0]),('Export',page.transfer_buttons[1]),('the settings filter',nav.filter),('the settings caption',nav.caption),('the machine details',w.machine_page.details),
 ('Refresh machine view',w.machine_page.refresh_button),('the machine caption',w.machine_page.caption),('the machine strip',strip)]
assert not [name for name,x in hidden if x.isVisible()],[name for name,x in hidden if x.isVisible()]
nav.show_view('cabinet');settle()
check('07 Every action a removed pane control reached is reached: Work ▸ Import and Export (the transfers\' own destinations, patched), Arrange ▸ Cabinet (Logical / Existing views, the catalogue choice, Refresh) and Refresh Machine View, Find\'s CABINET and SETTINGS rows, Activity\'s Timeline words and Work block, the Machine row\'s tooltip and the Cabinet tab\'s; none of the old controls shows in the pane')
# 08 · the centre foot: empty in Line, the console in Half (D1b) -----------------------------------------------------------------
bar.expire_note();console.set_size(0);settle();align()
assert not tail.isVisible(),'Line: the workspace reaches the lower band'
w.statusBar().showMessage('Saved as bench.txt');settle();assert tail.isVisible() and console.hint.isVisible() and not tail.list.isVisible()
bar.expire_note();settle();assert not tail.isVisible()
# The integration of the desk items: a long message (an unavailable row's whole reason, as F1 gives it) wraps in the foot and
# moves nothing: before, the foot asked for its whole length and the desk narrowed both panes to the slots' floor for good.
widths=(w.nav_dock.width(),w.sim_dock.width(),w.centralWidget().width())
w.statusBar().showMessage('Shut down · this computer · unavailable · Unavailable: '+session_power.NO_SESSION+' '+'Return to Debian and use systemctl poweroff at the text login. '*3);settle();align()
long_message=dict(during=[w.nav_dock.width(),w.sim_dock.width(),w.centralWidget().width()],lines=console.hint.height()//max(1,console.hint.fontMetrics().lineSpacing()))
assert tuple(long_message['during'])==widths and console.hint.wordWrap() and not symmetry.worst(desk_pairs()) and not ui_fit.whole_words(w),(widths,long_message)
bar.expire_note();settle();align();assert (w.nav_dock.width(),w.sim_dock.width(),w.centralWidget().width())==widths and not tail.isVisible()
measured['long_status_message']=dict(widths=list(widths),**long_message)
console.set_size(1);settle();align();assert tail.isVisible() and (w.log_view if console.mode=='log' else console.output).isVisible() and not tail.list.isVisible() and not symmetry.worst(desk_pairs())  # D3: the mode's page
console.set_size(0);settle();align();assert not tail.isVisible()
check('08 In Line the centre foot is empty (the workspace reaches the lower band); a status message shows there while it lasts, a long one wrapped with both panes and every pair unmoved; Half shows the working area above the band with the mode\'s page (D3: Assignment\'s answers here; the Timeline is Log\'s Events stream, step 12)')
# 09 · the pointer: the mark's two facets, aimed at 11 o'clock, the click at the tip (D1b) -----------------------------------------
# 13 November 2026: the same facets, aim and hotspot, drawn in the system green by workbench/pointer.py (with room around them for the glow).
from workbench import pointer as green_pointer
shape=graphite_brand.pointer_shape(1.0);cursor=w.cursor();green_arrow,green_x,green_y=green_pointer.drawn(Qt.ArrowCursor,green_pointer._installed.glow,1.0)
assert w.property('graphitePointer') and cursor.shape()==Qt.BitmapCursor and (cursor.hotSpot().x(),cursor.hotSpot().y())==(green_x,green_y)==(shape['hotspot'][0]+green_pointer.PAD,shape['hotspot'][1]+green_pointer.PAD)
assert cursor.pixmap().toImage().convertToFormat(QImage.Format_ARGB32)==green_arrow.toImage().convertToFormat(QImage.Format_ARGB32)
assert abs(graphite_brand.pointer_angle(shape['polygons'])-30.0)<1e-9 and shape['tip']==tuple(float(v) for v in shape['hotspot'])
for name,widget in (('the cabinet tree',w.cabinet_page.tree.viewport()),('a pane tab',nav.cabinet),('the head',w.ribbon_dock),('the workspace',w.central_stack)):
 assert widget.cursor().shape()==Qt.BitmapCursor,(name,widget.cursor().shape())
stands_for=lambda widget:Qt.CursorShape(int(widget.property(green_pointer.MARK))) if widget.property(green_pointer.MARK) is not None else widget.cursor().shape()
assert stands_for(bar.box)==Qt.IBeamCursor and stands_for(sh.face.input.viewport())==Qt.IBeamCursor,'text fields keep the I-beam (drawn in the green)'
assert w.workspace_split.handle(1).cursor().shape()==Qt.SplitHCursor and stands_for(w.trash_can)==Qt.PointingHandCursor
tree=w.cabinet_page.tree;tree.scrollToTop();settle();second=tree.itemBelow(tree.topLevelItem(0));row=tree.visualItemRect(second)
grab=w.grab().toImage();at=tree.viewport().mapTo(w,QPoint(row.left()+28,row.center().y()))  # on the second row's word
p=QPainter(grab);hx,hy=shape['hotspot'];p.drawPixmap(at.x()-green_x,at.y()-green_y,green_arrow);p.end()
crop=grab.copy(0,60,560,360);zoom=[];
for dpr,z in ((1.0,8),(2.0,4)):
 s=graphite_brand.pointer_shape(dpr);img=graphite_brand.pointer_pixmap(dpr).toImage();side=img.width()*z
 out=QImage(side,side,QImage.Format_RGB32);out.fill(QColor(desk_qt.ERASED) if dpr==1 else QColor('#4a4741'));q=QPainter(out);q.drawImage(QRect(0,0,side,side),img)
 hx,hy=s['hotspot'];q.setPen(QPen(QColor(desk_qt.ERASER_MARK),2));q.drawRect(int(hx*dpr*z),int(hy*dpr*z),z,z)
 aim=QPen(QColor('#9a6f12'),1,Qt.DashLine);q.setPen(aim);tx,ty=s['tip'][0]*dpr*z,s['tip'][1]*dpr*z
 q.drawLine(QPoint(int(tx),int(ty)),QPoint(int(tx+math.sin(math.radians(30))*side*0.8),int(ty+math.cos(math.radians(30))*side*0.8)));q.drawLine(QPoint(int(tx),int(ty)),QPoint(int(tx),int(ty+side*0.8)))
 q.end();zoom.append(out)
board=QImage(crop.width()+zoom[0].width()+zoom[1].width()+96,max(crop.height(),zoom[0].height())+64,QImage.Format_RGB32);board.fill(QColor('#e9e4d8'));q=QPainter(board)
font=QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);q.setFont(font);q.setPen(QColor(pane_qt.TEXT))
q.drawImage(24,48,crop);q.drawText(24,32,'On the cabinet tree (the cursor image drawn at its hotspot)')
x=crop.width()+48;q.drawImage(x,48,zoom[0]);q.drawText(x,32,'1x, 8 times');x+=zoom[0].width()+24;q.drawImage(x,48,zoom[1]);q.drawText(x,32,'2x on the band, 4 times')
q.end()
record('Graphite_Desk_07_Pointer.png','The pointer: the Graphite mark\'s two facets aimed at 11 o\'clock (30 degrees left of vertical, the dashed lines: vertical and the facets\' axis), the click at the tip (the pink square is the hotspot\'s pixel), drawn crisp at 1x and 2x with a thin paper edge so it reads on paper and on the bands. Offscreen there is no live cursor: the window grab has the cursor image drawn at its hotspot.',
 board,'ACTUAL_QT_WINDOW_GRAB_WITH_THE_CURSOR_IMAGE_DRAWN_AT_ITS_HOTSPOT')
check('09 The window\'s pointer is the mark\'s two facets, its hotspot (%d, %d) the tip exactly, aimed %.1f degrees left of vertical; the trees, tabs, head and workspace show it, text fields keep the I-beam, the splitter its resize cursor, Trash its hand'%(shape['hotspot']+(graphite_brand.pointer_angle(shape['polygons']),)))
# 10 · the quiet-script rule (the owner, 2026-11-06: "Don't we like cursive font for 'less necessary to read' text" and "upper left
# Graphite should be cursive"): the word Graphite and the panes' notes in the Paper script, what you act on in print; the switch --
from PySide6.QtGui import QTextDocument
top=w.shell2.top;wm=top.wordmark;panel=w.operations_panel;work=top.nice.popup  # the work list is the System menu's list now (D1-fix)
sh.show_operations_face();w.tabs.setFocus();settle(60);panel.refresh();settle();align()
def family(widget):return widget.font().family()
def doc_family(doc,words):
 found=doc.find(words);assert not found.isNull(),words
 fmt=found.charFormat();families=list(fmt.fontFamilies() or [])
 return families[0] if families else doc.defaultFont().family()  # no family of its own: the document's (the reading face)
def files_note():
 """The Context face for the Files room: its Open note, with the families of a key and of the words around it."""
 tab=w.show_files();settle();w.arc_inspector.refresh();settle();doc=w.arc_inspector.body.document()
 return tab,dict(key=doc_family(doc,'Ctrl+Alt+V'),words=doc_family(doc,'opens any file read-only'),recent=doc_family(doc,'files'),kinds=doc_family(doc,'Gerber'))
capture_hint=next(x for x in w.findChildren(shell2.QuietWords) if x.note==shell2.CAPTURE_HINT)
quiet=dict(selection=panel.selection,work=panel.jobs,active_jobs=work.running_label,queued=work.queued_label,note=work.note,capture_hint=capture_hint)
printed=dict(services=panel.services,slate_line=panel.slate,menus=top.headings()[0],tab=w.left_pane.tabs.buttons[0],tree=w.cabinet_page.tree,kill_switch=work.kill,empty=work.empty)
def rule_state():
 return dict(word=dict(family=family(wm),script=wm.script,stroke=wm.stroke,box=list(symmetry.box(wm,w)),ink=[wm.ink_rect().left(),wm.ink_rect().top(),wm.ink_rect().width(),wm.ink_rect().height()]),
  quiet={k:dict(script=v.scripted(),words=v.words(),note=v.note) for k,v in quiet.items()},printed={k:family(v) for k,v in printed.items()})
on=rule_state()
assert wm.script and family(wm)==shell2.SCRIPT and wm.text()==wm.accessibleName()=='Graphite' and wm.ink_rect().left()==0,on['word']
for name,label in quiet.items():
 if name=='selection' and panel.model and panel.model['selection']:
  assert not label.scripted() and label.text().startswith('CABINET SELECTION'),(name,label.text());continue  # a selection is a value: print
 assert label.scripted() and shell2.SCRIPT in label.text() and label.textFormat()==Qt.RichText,(name,label.words())
 if label.lead:assert 0<=label.text().find(label.lead.split('\n')[0])<label.text().find(shell2.SCRIPT),(name,label.text())  # the lead (a heading, a status) stays print, first
assert not [k for k,v in on['printed'].items() if v==shell2.SCRIPT],on['printed']
files_tab,notes_on=files_note()
assert notes_on['words']==shell2.SCRIPT and notes_on['key']!=shell2.SCRIPT and notes_on['recent']!=shell2.SCRIPT and notes_on['kinds']!=shell2.SCRIPT,notes_on
files_lead=getattr(files_tab,'lead',None);assert files_lead is not None and files_lead.scripted() and files_lead.note==__import__('workbench.rooms',fromlist=['FILES_NOTE']).FILES_NOTE,'the Files room\'s explanation is the script (D1-fix)'
assert not clipped_ink(files_lead) and not clipped_ink(capture_hint),'the script whole in its label'
on['files_room_note']=dict(script=files_lead.scripted(),words=files_lead.words())
sh.show_operations_face();w.tabs.setFocus();settle(60);align()
def quiet_sheet(tag):
 """The head's left slot over Activity, cut from the window: for the owner, the script on and off."""
 band=w.ribbon_dock.height();P=w.desk.pane;R=symmetry.box(w.sim_dock,w);image=w.grab().toImage()
 head=image.copy(0,0,P,band);pane=image.copy(R[0],R[1],R[2],min(R[3],760));out=QImage(max(P,R[2]),band+12+pane.height(),QImage.Format_RGB32);out.fill(QColor('#e9e4d8'))
 q=QPainter(out);q.drawImage(0,0,head);q.drawImage(0,band+12,pane);q.end();return out
sheet_on=quiet_sheet('on')
assert not symmetry.worst(desk_pairs()),symmetry.table(symmetry.worst(desk_pairs()))
setting('appearance.cursive',False);settle(60);align();panel.refresh();settle()
off=rule_state();files_tab,notes_off=files_note();assert not files_tab.lead.scripted() and shell2.SCRIPT not in files_tab.lead.text();off['files_room_note']=dict(script=False,words=files_tab.lead.words())
sh.show_operations_face();w.tabs.setFocus();settle(60);align()
assert not wm.script and family(wm)=='IBM Plex Sans' and wm.stroke==0 and wm.ink_rect().left()==0,off['word']
assert not [k for k,v in off['quiet'].items() if v['script']] and not [k for k,v in quiet.items() if shell2.SCRIPT in v.text()],off['quiet']
assert shell2.SCRIPT not in notes_off.values(),notes_off
off_pairs=desk_pairs();assert not symmetry.worst(off_pairs),symmetry.table(symmetry.worst(off_pairs))
size_rows,note_sizes=one_size_notes(work);assert not symmetry.worst(size_rows),note_sizes;off['system_list_note_sizes']=note_sizes
sheet_off=quiet_sheet('off')
setting('appearance.cursive',True);settle(60);align();panel.refresh();settle()
assert wm.script and family(wm)==shell2.SCRIPT and all(v.scripted() for k,v in quiet.items() if k!='selection' or not (panel.model and panel.model['selection'])),rule_state()
assert not symmetry.worst(desk_pairs()),symmetry.table(symmetry.worst(desk_pairs()))
w.tabs.removeTab(w.tabs.indexOf(files_tab));files_tab.deleteLater();settle()
board=QImage(sheet_on.width()+sheet_off.width()+72,max(sheet_on.height(),sheet_off.height())+56,QImage.Format_RGB32);board.fill(QColor('#e9e4d8'));q=QPainter(board)
font=QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);q.setFont(font);q.setPen(QColor(pane_qt.TEXT))
q.drawText(24,32,'Pleasantries in script: on (the default)');q.drawImage(24,48,sheet_on);x=sheet_on.width()+48
q.drawText(x,32,'Off (View ▸ Pleasantries in script)');q.drawImage(x,48,sheet_off);q.end()
record('Graphite_Desk_08_Quiet_Script_1920x1200.png','The quiet-script rule on the desk at 1920 by 1200: the word Graphite at the upper left in the Paper script, pale on the band, its capitals as tall as the symbol, and in Activity (quiet now: what Graphite did, got and needs) the notes you may skip in the script, whole in their labels (the selection\'s explanation; where the work\'s order, niceness and Stop are, under the printed WORK line) while what you act on and read first stays print; right, the same with View ▸ Pleasantries in script off: all print, the word in Plex SemiBold.',
 board,'ACTUAL_QT_WINDOW_GRABS_CUT_AT_THE_HEAD_SLOT_AND_THE_PANE')
quiet_rule=dict(on=on,off=off,context_files_note=dict(on=notes_on,off=notes_off),pairs_with_the_script_off=len(off_pairs),
 word_px=dict(script={str(p_):desk_qt.script_word_px(p_/14) for p_ in POINTS},print=desk_qt.word_px(1.0,False),stroke=desk_qt.word_stroke(1.0),symbol_height={str(p_):round(desk_qt.symbol_height(p_/14),3) for p_ in POINTS}))
check('10 The quiet-script rule: the word Graphite is the Paper script (%s %d px, a %.1f px hairline, its capitals as tall as the symbol), its outline from the band\'s inset and on the symbol\'s centre line, and as drawn at the symbol\'s distance from the edge and as designed (0 px and 0 levels, at all nine sizes in 01); the notes you may skip are the script, whole in their labels: in Activity the selection\'s explanation and where the work\'s order, niceness and Stop are (under the printed WORK line); in the System menu\'s list the captions after ACTIVE JOBS and QUEUED and the sliders\' note; Today\'s capture hint and the Files room\'s explanation, with their keys printed; the Files room\'s Open note in Context; the menus, tabs, trees, statuses and the kill switch stay print; View ▸ Pleasantries in script off makes them all print (the word in Plex SemiBold, every pair still 0 px) and on again restores them'%(family(wm),wm.font().pixelSize(),wm.stroke))
# 12 · the writing line's four modes and the Log view (HATCH DESK D3) --------------------------------------------------------------
from workbench import log_qt,typebar_qt
ui_pt(14);w.resize(1920,1200);settle(60);align(4);sh.show_operations_face();w.tabs.setFocus();settle();console=w.console;view=w.log_view;box=bar.box
D3_CAPTURES={}
def band_strip(label):
 """The lower band cut from the window, with the mode's name above it (for the owner's sheet of the four modes)."""
 y=symmetry.box(w.type_dock,w)[1];return w.grab().toImage().copy(0,y,w.width(),w.type_dock.height())
def labelled_sheet(parts):
 gap=18;head=34;width=max(i.width() for _,i in parts)+2*gap;height=sum(i.height()+head+gap for _,i in parts)+gap
 out=QImage(width,height,QImage.Format_RGB32);out.fill(QColor('#e9e4d8'));p=QPainter(out);font=QFont('IBM Plex Sans');font.setPixelSize(16);font.setWeight(QFont.DemiBold);p.setFont(font);y=gap
 for label,image in parts:
  p.setPen(QColor(pane_qt.TEXT));p.drawText(QRectF(gap,y,width-2*gap,head-6),Qt.AlignLeft|Qt.AlignVCenter,label);p.drawImage(gap,y+head,image);y+=image.height()+head+gap
 p.end();return out
# the line in each mode, the active one marked by the short yellow mark (and only it)
strips=[];yellow={}
for mode in ('slate','shell','find','log'):
 bar.set_target(mode,focus=False);console.set_size(0);w.tabs.setFocus();settle();align(2)
 word=bar.targets[mode];image=w.grab().toImage();x0,x1,_,_=ink_span(word,w);y=symmetry.box(word,w)[1]+word.height()-desk_qt.MARK
 yellow[mode]=[b_.text() for b_ in bar.targets.values() if image.pixel(sum(ink_span(b_,w)[:2])//2,symmetry.box(b_,w)[1]+b_.height()-1)==QColor(desk_qt.PENCIL).rgb()]
 assert yellow[mode]==[bar.labels[mode]],(mode,yellow[mode])
 assert box.placeholderText()=='poem' and box.accessibleDescription().startswith(typebar_qt.SHOWN.get(mode,bar.labels[mode]) if mode!='log' else 'Log · '),(mode,box.accessibleDescription())
 strips.append(('%s: %s'%(bar.labels[mode],typebar_qt.TIPS[mode].split(': ',1)[1]),band_strip(mode)))
assert bar.labels['shell']==typebar_qt.shell_label(typebar_qt.configured_shell()) and bar.labels['shell']==('Bash' if Path(typebar_qt.configured_shell()).name=='bash' else 'Shell'),bar.labels
# D3-fix: the poem placeholder as drawn, legible on the line's paper (the review measured 2.42:1): its darkest pixel in the window
# against the line's paper beside it, at least the 4.5:1 of the band's quiet lettering, and lighter than typed text
bar.set_target('slate',focus=False);box.clear();w.tabs.setFocus();settle();poem_img=box.grab().toImage();rgb_of=lambda c:(c.red(),c.green(),c.blue())
poem_paper=QColor(poem_img.pixel(3,poem_img.height()//2));poem_ink=min((QColor(poem_img.pixel(x,y)) for x in range(poem_img.width()//3) for y in range(poem_img.height())),key=lambda c:c.lightness())
POEM=dict(paper=poem_paper.name(),ink=poem_ink.name(),contrast=round(desk_qt.contrast(rgb_of(poem_ink),rgb_of(poem_paper)),2),text=round(desk_qt.contrast(rgb_of(QColor(shell2.TEXT)),rgb_of(poem_paper)),2))
assert box.placeholderText()=='poem' and 4.5<=POEM['contrast']<POEM['text'],POEM
record('Graphite_Desk_D3_01_Writing_Line_Modes_1920x1200.png','The lower band at 1920 by 1200 in each of the writing line\'s four modes, Assignment · %s · Search · Log, the active one marked by the short pencil-yellow mark under its word (and only it, measured in the window\'s pixels); the flat writing line erased into the band with the light poem placeholder; Line · Half · Tall beside the cat. The Shell mode\'s word is %s because the configured shell is %s.'%(bar.labels['shell'],bar.labels['shell'],typebar_qt.configured_shell()),
 labelled_sheet(strips),'ACTUAL_QT_WINDOW_GRABS_CUT_AT_THE_LOWER_BAND')
# Assignment: words to Graphite on Enter; typed staC runs only on Ctrl+Enter, through the staC target's own path
bar.set_target('slate');box.setFocus();QTest.keyClicks(box,'files.list');settle();bar.refresh_context()
hint=dict(context=bar.context.text(),visible=bar.context.isVisible(),results=[box.popup.list.item(i).text() for i in range(min(3,box.popup.list.count()))])
assert hint['visible'] and hint['context']=='· runs as a line' and hint['results'][0]=='A LINE · THE ARROW RUNS IT',hint
with patch.object(sh,'ask') as asked,patch.object(type(console),'run_stac',autospec=True,side_effect=type(console).run_stac) as ran:
 QTest.keyClick(box,Qt.Key_Return);settle()
 assert [c.args for c in asked.call_args_list]==[('files.list',)],asked.call_args_list
 assert ran.call_count==0,'plain Enter never runs staC'
 console.output.clear();console.blocks=0;box.setText('desk');box.setFocus();QTest.keyClick(box,Qt.Key_Return,Qt.ControlModifier);settle(60)
 assert ran.call_count==1 and ran.call_args.args[1]=='desk' and asked.call_count==1,(ran.call_args_list,asked.call_args_list)
answer=console.output.toPlainText();ran_part=answer[answer.find('line › desk'):]
assert 'line › desk' in answer and 'refused' not in ran_part and console.size_level==1 and console.output.isVisible(),answer[-300:]
box.setText('files.list');box.setFocus();settle();bar.refresh_context();align(2)
record('Graphite_Desk_D3_02_Assignment_staC_1920x1200.png','Assignment at 1920 by 1200: above, at Half, the answer of the staC program desk run with Ctrl+Enter through the staC target\'s own path (stac.run through Kernel.dispatch, read only): a real command; in the line, files.list typed, which parses as staC, so the line\'s quiet word says staC on Ctrl+Enter and the results under it say Ctrl+Enter runs it, while Enter would give it to Graphite as an assignment.',
 w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
box.popup.hide();box.clear();console.set_size(0);settle()
# D3-fix: the old staC target's history is Assignment's: Up on an empty line recalls the typed staC that ran, and walks on
box.setFocus();console.at=None;QTest.keyClick(box,Qt.Key_Up);settle();stac_up=box.text()
assert stac_up==console.history['stac'][-1]=='desk',(stac_up,console.history.get('stac',[])[-3:])
box.popup.hide();box.clear();console.at=None;settle()
# Commands ▸ Run an operation… (Kernel's home): the line in Assignment with the / lead
assert w.a_run_operation in w.menu_groups['Commands'].actions() and w.a_run_operation.shortcut().toString()=='Alt+3'
w.a_run_operation.trigger();settle();assert bar.target=='slate' and box.text()=='/' and box.accessibleDescription().startswith('Assignment · an operation by name') and app.focusWidget() is box,(box.text(),box.accessibleDescription())
box.setText('/ops agenda');QTest.keyClick(box,Qt.Key_Return);settle(60);assert 'graphite › ops agenda' in console.output.toPlainText()
from PySide6.QtWidgets import QMenu
line_menu=next(m for m in w.findChildren(QMenu) if m.title()=='Writing Line' and m.menuAction() in w.menu_groups['Commands'].actions())
assert [(a.text().split('\t')[0],a.shortcut().toString()) for a in line_menu.actions()]==[('Assignment','Alt+1'),(bar.labels['shell'],'Alt+5'),('Search','Alt+4'),('Log','Alt+6')],[a.text() for a in line_menu.actions()]
box.clear();console.set_size(0);settle()
# Search: results as you type, Enter searches the workspace, each result opens where it belongs
bar.set_target('find');QTest.keyClicks(box,'Bench');settle(60);rows=[box.popup.list.item(i).text() for i in range(box.popup.list.count())]
assert box.popup.isVisible() and rows[:2]==['SEARCH','Search the workspace for “Bench”'] and 'CABINET' in rows,rows
assert box.popup.hint.scripted() and not symmetry.worst(script_labels()),symmetry.table(symmetry.worst(script_labels()))  # the caption: the script, keys printed, whole
record('Graphite_Desk_D3_03_Search_Results_1920x1200.png','Search at 1920 by 1200 (Ctrl+K, or the Search word): Bench typed in the line; the results open under it as you type, first the search itself (Enter), then the cabinet\'s matching records (the project Bench notes) and anything else by name, each opening where it belongs.',
 w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
QTest.keyClick(box,Qt.Key_Return);settle(60);found=console.output.toPlainText()
assert 'find › Bench' in found and 'CABINET · ' in found and console.size_level==1,found[-400:]
def answer_in_sight(echo):
 """D3-fix (the review's 03b showed the answer's last rows out of sight): the output at its end once the area has opened, and
 the answer's lines from its echo to its last line inside the viewport (above the horizontal scroll bar). (echo's top, last's bottom,
 viewport height, value, maximum)."""
 out=console.output;bar_=out.verticalScrollBar();doc=out.document();lay=doc.documentLayout();b_=doc.lastBlock()
 while b_.isValid() and not b_.text().strip():b_=b_.previous()
 first=doc.find(echo);top=lay.blockBoundingRect(first.block()).top()-bar_.value() if not first.isNull() else None
 return (top,lay.blockBoundingRect(b_).bottom()-bar_.value(),out.viewport().height(),bar_.value(),bar_.maximum())
seen=answer_in_sight('find › Bench');assert seen[3]==seen[4] and seen[1]<=seen[2],('the answer\'s end in sight, after the earlier answers',seen)
console.output.clear();console.blocks=0;box.setText('Bench');box.setFocus();QTest.keyClick(box,Qt.Key_Return);settle(60)  # the owner's capture: the answer alone
seen_alone=answer_in_sight('find › Bench');assert seen_alone[0] is not None and seen_alone[0]>=0 and seen_alone[1]<=seen_alone[2],('the whole answer in sight',seen_alone)
D3_CAPTURES.update(search_in_sight=dict(after_earlier=seen,alone=seen_alone))
record('Graphite_Desk_D3_03b_Search_Workspace_1920x1200.png','Search at 1920 by 1200 after Enter: the workspace searched for Bench in the working area above the line (files and their words, received files, the cabinet, settings, commands and the Timeline), each with open; the whole answer in sight, from its echo to its last line (measured).',
 w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
box.clear();console.set_size(0);settle()
# Log · Events: Graphite's events, newest at the bottom, nothing to write (the notes feature is gone)
bar.set_target('log',focus=False);view.choose('events');console.set_size(1);settle(60);align(2);view.refresh(force=True);settle()
lines=[view.events.item(i).data(Qt.UserRole) for i in range(view.events.count())];lines=[e for e in lines if e]
assert view.isVisible() and len(lines)>=3 and [e['event']['seq'] for e in lines]==sorted(e['event']['seq'] for e in lines),[e['line'] for e in lines][-5:]
from PySide6.QtWidgets import QLineEdit,QPlainTextEdit,QTextEdit
assert not [x for kind in (QLineEdit,QPlainTextEdit,QTextEdit) for x in view.findChildren(kind)],'no notes: nothing to write in the Log view'
assert not ui_fit.whole_words(view) and not symmetry.worst(desk_pairs()),ui_fit.describe(ui_fit.whole_words(view))
record('Graphite_Desk_D3_04_Log_Events_Half_1920x1200.png','Log at Half on Events, 1920 by 1200: Graphite\'s own events from the activity journal (ledger.activity through Kernel.dispatch) in the Timeline\'s words, newest at the bottom, Follow latest on; the two small tabs Events and Network at its top; the line filters the stream (Enter). There are no notes: the owner replaced them with the network.',
 w.grab().toImage(),'ACTUAL_QT_WINDOW_GRAB')
events_count=len(lines)
# Log · Network, on TEST DATA: the check's fake capability (D5's four operations, its contract), the addresses from the documentation ranges
TEST_DATA='TEST DATA from the check\'s fake network capability (no real traffic)'
class FakeNetwork:
 """D5's four operations as the contract gives them, answering with TEST DATA (RFC 5737 documentation addresses, a process
 called test-browser); every call recorded. The real capability is never asked here."""
 def __init__(self):self.calls=[];self.capture={'state':'IDLE'};self.packets=[];self.seq=0;self.refuse=None
 def __call__(self,operation,arguments):
  self.calls.append((operation,dict(arguments)))
  if operation=='network.capture.start' and self.refuse:return {'ok':False,'error':{'code':'CaptureError','message':self.refuse}}  # the capability's refusal, its words
  if operation=='network.observe':
   return {'ok':True,'result':dict(interfaces=[dict(name='test0',rx_bps=1840000,tx_bps=96000,rx_bytes=1,tx_bytes=1,up=True),dict(name='lo',rx_bps=0,tx_bps=0,rx_bytes=0,tx_bytes=0,up=True)],
    connections=[dict(proto='tcp',local='192.0.2.10',lport=51412,remote='198.51.100.7',rport=443,state='ESTABLISHED',pid=4242,process='test-browser',user='owner'),
                 dict(proto='tcp',local='192.0.2.10',lport=51418,remote='203.0.113.25',rport=443,state='ESTABLISHED',pid=4242,process='test-browser',user='owner'),
                 dict(proto='udp',local='192.0.2.10',lport=40001,remote='192.0.2.1',rport=53,state='UNCONN',pid=611,process='test-resolver'),
                 dict(proto='tcp',local='0.0.0.0',lport=22,remote='0.0.0.0',rport=0,state='LISTEN',pid=702,process='test-sshd')],
    capture=dict(self.capture),observed_at=time.time())}
  if operation=='network.capture.start':self.capture=dict(state='RUNNING',tool='dumpcap (test data)',started=time.time()-12,packets=0,filter=arguments.get('filter'));return {'ok':True,'result':{'capture':dict(self.capture)}}
  if operation=='network.capture.stop':self.capture=dict(state='IDLE');return {'ok':True,'result':{'capture':dict(self.capture)}}
  if operation=='network.capture.read':
   after=int(arguments.get('after') or 0);rows=[p_ for p_ in self.packets if p_['seq']>after]
   return {'ok':True,'result':dict(packets=rows,next=str(rows[-1]['seq']) if rows else str(after),capture=dict(self.capture,packets=len(self.packets)))}
  raise AssertionError('The Network stream asked for '+operation)
 def arrive(self,n):
  for i in range(n):
   self.seq+=1;out=self.seq%3!=0;t=time.time()
   self.packets.append(dict(seq=self.seq,at=t+self.seq/100.0,iface='test0',proto='tcp',src='192.0.2.10' if out else '198.51.100.7',sport=51412 if out else 443,
    dst='198.51.100.7' if out else '192.0.2.10',dport=443 if out else 51412,length=66+(self.seq*37)%1400,flags='.' if self.seq%4 else 'P.',process='test-browser'))
fake=FakeNetwork();real_dispatch=view.dispatch;view.dispatch=fake;view.confirmed=False;question.reset_mock()
view.choose('network');view.refresh(force=True);settle()
assert view.connections.count()==4 and 'test0' in view.interfaces.text() and view.capture_words.text()=='Capture idle' and view.start_button.isVisible()
box.setText('port 443');box.setFocus();QTest.keyClick(box,Qt.Key_Return);settle()
assert [view.connections.item(i).data(Qt.UserRole)['remote'] for i in range(view.connections.count())]==['198.51.100.7','203.0.113.25'] and fake.calls[-1]==('network.observe',{'filter':'port 443'}),fake.calls[-1]
QTest.keyClick(box,Qt.Key_Return,Qt.ControlModifier);settle()  # Ctrl+Enter: a capture with the line's filter, the owner's own action
assert question.call_count==1 and 'headers only' in question.call_args.args[2] and 'not in promiscuous mode' in question.call_args.args[2] and 'Nothing leaves the computer' in question.call_args.args[2],question.call_args
assert [a for op,a in fake.calls if op=='network.capture.start']==[{'filter':'port 443','seconds':log_qt.CAPTURE_SECONDS,'packets':log_qt.CAPTURE_PACKETS}] and view.capture['state']=='RUNNING' and view.stop_button.isVisible()
fake.arrive(14);view.refresh();settle();assert view.packets.count()==14
view.chose(view.packets.item(3));pinned=dict(view.pinned);assert view.pin_frame.isVisible() and pinned['kind']=='packet'
for _ in range(3):fake.arrive(9);view.refresh();settle()
assert view.pinned==pinned and view.pin_frame.isVisible() and view.packets.count()==41,'the pin holds while packets arrive'
assert {op for op,_ in fake.calls}<=set(log_qt.NETWORK_OPERATIONS),{op for op,_ in fake.calls}
spot=view.connections.visualItemRect(view.connections.item(0)).center();entry=log_qt.entry_at(view.connections.viewport(),spot)
assert entry['stream']=='network' and entry['kind']=='connection' and entry['remote']=='198.51.100.7',entry
assert not ui_fit.whole_words(view) and not symmetry.worst(desk_pairs()),ui_fit.describe(ui_fit.whole_words(view))
grab=w.grab().toImage();p=QPainter(grab);font=QFont('IBM Plex Sans');font.setPixelSize(15);font.setWeight(QFont.DemiBold);p.setFont(font)
banner=QRectF(symmetry.box(view,w)[0]+symmetry.box(view,w)[2]-560,symmetry.box(view,w)[1]-30,560,26);p.fillRect(banner,QColor(shell2.ERASER));p.setPen(QColor(pane_qt.TEXT));p.drawText(banner,Qt.AlignCenter,TEST_DATA);p.end()
record('Graphite_Desk_D3_05_Log_Network_Half_TEST_DATA_1920x1200.png','Log at Half on Network, 1920 by 1200, on TEST DATA (the check\'s fake capability answering D5\'s four operations with documentation addresses; labelled on the image): the interfaces with their receive and send rates, the connections filtered by port 443 (typed in the line, Enter), and the packet stream of a capture started with Ctrl+Enter after the confirmation (headers only, this computer\'s interfaces, not promiscuous, %d seconds or %d packets, nothing leaves the computer), newest at the bottom; a packet is pinned at the top with its details and Ask Stacy about this, and stays while 27 more arrive.'%(log_qt.CAPTURE_SECONDS,log_qt.CAPTURE_PACKETS),
 grab,'ACTUAL_QT_WINDOW_GRAB_ON_TEST_DATA_LABELLED')
# D3-fix: a capture that ends on its own bound between two reads: what it wrote last is read once it is seen ended (the review's
# probe lost the last packets)
shown=view.packets.count();fake.arrive(2);fake.capture=dict(state='IDLE')
view.ticks+=log_qt.OBSERVE_EVERY-1-view.ticks%log_qt.OBSERVE_EVERY  # the next tick observes first, and sees the capture ended
for _ in range(3):view.refresh();settle(1)
assert view.packets.count()==shown+2 and not view.following,(view.packets.count(),shown)
fake.capture=dict(state='RUNNING',tool='dumpcap (test data)',started=time.time()-20,packets=len(fake.packets),filter='port 443')
# Ask Stacy about this; D4's focus(); Stop capture; the unavailable reason
view.ask();settle();assert bar.target=='slate' and box.text().startswith('About this packet (') and '198.51.100.7:443' in box.text(),box.text()
box.clear();log_qt.focus(w,entry);settle()
assert bar.target=='log' and view.stream=='network' and view.pinned['remote']=='198.51.100.7' and view.filters['network']=='host 198.51.100.7 port 443' and box.text()=='host 198.51.100.7 port 443'
view.stop_capture();settle();assert view.capture['state']=='IDLE' and not view.stop_button.isVisible() and ('network.capture.stop',{}) in fake.calls
# D3-fix: refusals say why and stay: words the capability's grammar refuses (a name it never looks up) are said before anything is
# asked or started; the capability's own refusal of a confirmed capture stays through the next refreshes (it was overwritten at once)
starts=len([1 for op,_ in fake.calls if op=='network.capture.start']);question.reset_mock()
assert view.start_capture('example.org') is None and question.call_count==0 and len([1 for op,_ in fake.calls if op=='network.capture.start'])==starts
assert view.capture_words.text()=='Not captured' and 'names are not looked up (Graphite makes no DNS request): example.org' in view.capture_note.text(),view.capture_note.text()
fake.refuse='NETWORK_CAPTURE_STOPPING: the last capture is still stopping; try again in a moment. (test data)';view.start_capture('port 443');settle()
for _ in range(3):view.refresh();settle(1)
refused_words=view.capture_note.text();assert view.capture_words.text()=='Not captured' and refused_words=='the last capture is still stopping; try again in a moment. (test data)',refused_words
fake.refuse=None;box.setText('host 198.51.100.7 port 443');view.apply_filter(box.text());settle();assert view.capture_words.text()=='Capture idle'
REASON='Capture is not permitted for this account (test data): dumpcap needs the wireshark group. Add yourself with your administrator, then sign in again.'
fake.capture=dict(state='UNAVAILABLE',reason=REASON);view.refresh(force=True);settle();starts=len([1 for op,_ in fake.calls if op=='network.capture.start']);question.reset_mock()
QTest.keyClick(box,Qt.Key_Return,Qt.ControlModifier);settle()
assert view.capture_note.text()==REASON and view.capture_words.text()=='Capture unavailable' and not view.start_button.isVisible() and question.call_count==0
assert len([1 for op,_ in fake.calls if op=='network.capture.start'])==starts and 'sudo' not in (view.capture_note.text()+view.summary()).lower()
console.set_size(0);settle();bar.refresh_context();assert bar.context.text().startswith('· Network') and 'capture unavailable' in bar.context.text(),bar.context.text()
w.save_session();again=Session(RUN/'profile/session.json',root).state;assert (again.get('type_target'),again.get('log_stream'))==('log','network'),again
view.dispatch=real_dispatch;fake.capture={'state':'IDLE'};view.unpin();box.clear();view.apply_filter('');view.choose('events');bar.set_target('slate',focus=False);console.set_size(0);w.tabs.setFocus();settle();align(2)
launcher.assert_not_called();submission.assert_not_called();popen.assert_not_called();detached.assert_not_called()
D3_CAPTURES.update(yellow=yellow,stac_hint=hint,events=events_count,network_calls=sorted({op for op,_ in fake.calls}),pinned=pinned['seq'],reason=REASON,
 poem=POEM,stac_history_up=stac_up,refused=refused_words)
check('12 The writing line (D3): Assignment · %s · Search · Log, only the chosen one marked by the short yellow mark (in the window\'s pixels) and every desk pair 0 px with each chosen in Line, Half and Tall at all nine sizes (step 01); the poem placeholder drawn at %s:1 on the line\'s paper (D3-fix); Assignment: files.list says staC on Ctrl+Enter, Enter gives it to Graphite and runs no staC, Ctrl+Enter runs typed staC (desk) through the staC path, its answer in the working area, and Up on the empty line recalls it (the staC target\'s history, D3-fix); Commands ▸ Run an operation… (Alt+3) is the line with the / lead and runs ops; Search lists results as you type and Enter searches the workspace, the answer\'s end in sight (D3-fix); Ctrl+K is Search (step 05); Log on Events follows the journal (%d lines, newest last) with nothing to write in it; Log on Network (test data) reads only through %s, filters by the line (Enter), asks once before the first capture (Ctrl+Enter), shows the packet stream, holds a pinned packet while 27 more arrive, reads a capture\'s last packets when it ends between reads (D3-fix), puts an assignment about it in the line, follows its conversation for D4 (entry_at, focus), stops, says why a capture was refused and keeps saying it (D3-fix), and shows the unavailable reason without offering anything; the session remembers Log and Network'%(bar.labels['shell'],POEM['contrast'],events_count,', '.join(log_qt.NETWORK_OPERATIONS)))
# 13 · the cat, the programs list and the System menu (HATCH DESK D2) ------------------------------------------------------------
from workbench import programs_qt,session_power,system_menu_qt,explore
ui_pt(14);w.resize(1920,1200);settle(60);align(4);console.set_size(0);bar.set_target('slate',focus=False);w.show_start();w.tabs.setFocus();settle();align(2)
hatch=bar.hatch;cat=hatch.cat;lst=hatch.programs;sym=sh.top.nice;D2_REPORT={}
def with_popups(*popups):
 """The window grab with each popup (its own window) drawn where it is: what the owner sees."""
 pix=w.grab();p=QPainter(pix)
 for popup in popups:p.drawPixmap(w.mapFromGlobal(popup.mapToGlobal(QPoint(0,0))),popup.grab())
 p.end();return pix.toImage()
def cat_light():
 """The cat on the band in the window's pixels: its coat (CAT_COAT) is the band's brightest value, a step above the lettering;
 the designed contrast of the coat and of the lettering on the band's mean tone, and of the coat on the grain's lightest 5%."""
 grab=w.grab().toImage();hx,hy,hw,hh=symmetry.box(hatch,w);by=symmetry.box(w.type_dock,w)[1];bh=w.type_dock.height();coat=QColor(graphite_brand.CAT_COAT)
 near=lambda c:abs(c.red()-coat.red())+abs(c.green()-coat.green())+abs(c.blue()-coat.blue())<=6
 coat_px=sum(1 for y in range(hy,hy+hh) for x in range(hx,hx+hw) if near(QColor(grab.pixel(x,y))))
 brightest=max(QColor(grab.pixel(x,y)).lightness() for y in range(by,by+bh) for x in range(0,w.width()) if not hx<=x<hx+hw)
 mean=desk_qt.grain_report()['mean_tone'];rgb=lambda c:(QColor(c).red(),QColor(c).green(),QColor(c).blue())
 return dict(coat=graphite_brand.CAT_COAT,coat_pixels=coat_px,coat_lightness=coat.lightness(),brightest_elsewhere_in_the_band=brightest,mean_tone=mean,
  coat_on_mean=round(desk_qt.contrast(rgb(graphite_brand.CAT_COAT),mean),2),lettering_on_mean=round(desk_qt.contrast(rgb(desk_qt.ERASED),mean),2),
  coat_on_lightest_grain=round(desk_qt.contrast(rgb(graphite_brand.CAT_COAT),desk_qt.tone(desk_qt.grain_report()['lightest_5_percent_offset'])),2))
light=cat_light();D2_REPORT['cat_colours']=light
assert light['coat_pixels']>=300 and light['coat_lightness']>light['brightest_elsewhere_in_the_band'] and light['coat_on_mean']>=9.0 and light['coat_on_mean']>light['lettering_on_mean'],light
assert hatch.toolTip()==hatch.accessibleName()=='Open programs' and sym.accessibleName()=='System menu'
# the four poses inside the band, as the button draws them (each set at once, as Reduce motion does)
strips=[];saved=cat.params;P=w.desk.pane;by=symmetry.box(w.type_dock,w)[1];bh=w.type_dock.height()
for pose,word in (('rest','rest: paws down, tail tucked, graphite eyes'),('hover','hover: a side-glance in yellow, the tail a question mark'),('open','the list open: the tail dropped, the right paw lifted, yellow eyes up'),('sleepy','asleep after a while: settled lower, eyes closed, no yellow')):
 cat.params=graphite_brand.POSES[pose];hatch.update();settle()
 strip=w.grab().toImage().copy(0,by,min(P,260),bh);strips.append((word,strip.scaled(strip.width()*3,strip.height()*3,Qt.IgnoreAspectRatio,Qt.FastTransformation)))
cat.params=saved;hatch.update();settle()
record('Graphite_Desk_13_Cat_Poses_In_The_Band.png','The cat in the lower band at 1920 by 1200, 14 pt, its four poses each cut from the window and enlarged three times (pixels kept): pale paper on the graphite band (the workspace\'s warm paper white %s, %s:1 on the band\'s mean tone; the lettering %s:1), graphite eyes and paws, a soft eraser-pink nose and inner ears, pencil-yellow irises on hover and while the list is open, eyes closed and no yellow asleep; every pose inside the band (step 01 measures it at all nine sizes).'%(light['coat'],light['coat_on_mean'],light['lettering_on_mean']),
 labelled_sheet(strips),'ACTUAL_QT_WINDOW_GRABS_CUT_AT_THE_LOWER_BAND_ENLARGED')
# Reduce motion: the pose changes at once
w.reading_profile['reduce_motion']=True;cat.enter();direct=cat.params==graphite_brand.POSES['hover'] and cat.animation.state()!=cat.animation.State.Running;cat.leave();w.reading_profile.pop('reduce_motion',None)
assert direct and cat.params==graphite_brand.POSES['rest'],'Reduce motion switches the poses directly'
# one click opens the list, even asleep; the open pose while it is open; Escape closes it, the cat has focus again
cat.show(cat.poses.idle());settle();assert cat.pose=='sleepy'
QTest.mouseClick(hatch,Qt.LeftButton,Qt.NoModifier,hatch.rect().center());settle(60)
plain=sorted((programs_qt.PLAIN[row[0]] for row in explore.VIEWS),key=str.casefold)
assert lst.isVisible() and cat.pose=='open' and hatch.property('menuOpen') is True and lst.words()==plain+['—','Explore the workshop'],(cat.pose,lst.words())
assert set(lst.rows_by_key)=={row[0] for row in explore.VIEWS},'nothing lost from the Hatch groups'
QTest.keyClick(lst,Qt.Key_Escape);settle();assert not lst.isVisible() and cat.pose in ('rest','hover') and hatch.property('menuOpen') is False
# the keyboard: Return opens it with the first row under focus; letters jump (type-to-select); Return opens the workspace (navigation)
hatch.setFocus();settle();QTest.keyClick(hatch,Qt.Key_Return);settle(60)
assert lst.isVisible() and app.focusWidget() is lst.rows_by_key['agenda'],type(app.focusWidget()).__name__
QTest.keyClicks(app.focusWidget(),'fi');settle();assert app.focusWidget() is lst.rows_by_key['files'],getattr(app.focusWidget(),'word',None)
QTest.keyClick(app.focusWidget(),Qt.Key_F1);settle();assert w.statusBar().currentMessage().startswith('Files') and ' — Read working material' in w.statusBar().currentMessage(),w.statusBar().currentMessage()
jobs_before=len(k.listing('jobs'));QTest.keyClick(app.focusWidget(),Qt.Key_Return);settle(80)
assert not lst.isVisible() and type(w.tabs.currentWidget()).__name__=='FilesTab' and len(k.listing('jobs'))==jobs_before,'navigation only'
files_room=w.tabs.currentWidget();w.tabs.removeTab(w.tabs.indexOf(files_room));files_room.deleteLater()  # as step 10 does: the Files room's own width stays out of the reopen step
w.statusBar().clearMessage();w.show_start();w.tabs.setFocus();settle();align(2)
# the programs list for the owner at 1920 by 1200 and 1366 by 768 (the keyboard's first row under focus)
for size,name in (((1920,1200),'Graphite_Desk_09_Programs_List_1920x1200.png'),((1366,768),'Graphite_Desk_10_Programs_List_1366x768.png')):
 w.resize(*size);settle(60);align(4);w.show_start();w.tabs.setFocus();settle();hatch.setFocus();settle();QTest.keyClick(hatch,Qt.Key_Return);settle(60)
 at=w.mapFromGlobal(lst.mapToGlobal(QPoint(0,0)));D2_REPORT.setdefault('programs_list',{})['%dx%d'%size]=dict(box=[at.x(),at.y(),lst.width(),lst.height()],rows=len(lst.rows()),scrolls=lst.scroll.verticalScrollBar().maximum()>0)
 record(name,'The cat\'s programs list at %d by %d, 14 pt, opened with Return from the cat: %d programs and capabilities, one plain name and one small graphite icon each, A to Z (type a name\'s first letters to jump), then Explore the workshop; a status word at the right where one applies (needs setup); its small caption in the script at the top. It opens upward from the lower left, its left edge the band\'s inset from the window\'s edge and its foot on the lower band\'s top: the point-mirror image of the System menu (Symmetry rule 6, measured at all nine sizes in step 01).'%(size[0],size[1],len(lst.rows())-1),
  with_popups(lst),'ACTUAL_QT_WINDOW_AND_POPUP_GRABS')
 lst.close_menu();settle()
# the System menu: its order, its process list with order and niceness distinct, Graphite services, the separated group
for title in ('Read the bench notes','Compare the two drafts'):call('agenda.add',{'title':title,'program':'@files:bench.txt','nice':'normal'})
w.resize(1920,1200);settle(60);align(4);w.show_start();w.tabs.setFocus();settle()
menu=sym.open(True);settle(60)
from PySide6.QtWidgets import QLabel as _QLabel
places=[menu.queue.itemWidget(menu.queue.item(i)).findChild(_QLabel,'QueuePlace').text() for i in range(menu.queue.count())]
leave=session_power.session_exit()
assert menu.words()==['Game','Stop all jobs','—','processes','—','Graphite services','—','Log out',leave['label'],'Restart','Shut down'],menu.words()
assert app.focusWidget() is menu.game and menu.kill.caption=='work Graphite manages' and places==['1','2'],(places,menu.kill.caption)
assert [c.text() for c in menu.services.choices]==['On','Off','Restart'] and menu.session_rows['leave'].isEnabled() and menu.session_rows['leave'].caption=='this Graphite session'
states=menu.states  # the check holds session_power.system (held_logind): no login session on any computer, so the three are unavailable with that reason
assert all(not states[a]['available'] and states[a]['reason'].startswith(session_power.NO_SESSION) and menu.session_rows[a].unavailable==states[a]['reason'] and menu.session_rows[a].caption.endswith('· unavailable') for a in session_power.ACTIONS),states
# D2-fix: an unavailable row stays in the keyboard's order and says why (F1's note, its accessible description); nothing is asked
assert all(menu.session_rows[a] in menu.focusables() and 'Unavailable: '+session_power.NO_SESSION in menu.session_rows[a].accessibleDescription() for a in session_power.ACTIONS)
QTest.keyClick(app.focusWidget(),Qt.Key_End);settle();assert app.focusWidget() is menu.session_rows['shutdown'],getattr(app.focusWidget(),'word',None)
QTest.keyClick(app.focusWidget(),Qt.Key_F1);settle();f1_unavailable=w.statusBar().currentMessage()
assert f1_unavailable.startswith('Shut down · this computer · unavailable') and 'Unavailable: '+session_power.NO_SESSION in f1_unavailable,f1_unavailable
w.statusBar().clearMessage();QTest.keyClick(app.focusWidget(),Qt.Key_Home);settle();assert app.focusWidget() is menu.game
assert menu.service_actions['Reboot'].word=='Graphite services: Restart' and menu.descriptor(menu.service_actions['Reboot']).startswith('Graphite services: Restart — '),'D2-fix: the services\' Restart names its scope'
D2_REPORT['system_menu']=dict(words=menu.words(),queue_places=places,availability_here={a:dict(available=s['available'],reason=s['reason']) for a,s in states.items()},
 captions={k:r.caption for k,r in menu.session_rows.items()})
for size,name in (((1920,1200),'Graphite_Desk_11_System_Menu_1920x1200.png'),((1366,768),'Graphite_Desk_12_System_Menu_1366x768.png')):
 menu.close_menu();w.resize(*size);settle(60);align(4);w.show_start();w.tabs.setFocus();settle();sym.setFocus();settle();QTest.keyClick(sym,Qt.Key_Return);settle(80)
 at=w.mapFromGlobal(menu.mapToGlobal(QPoint(0,0)));D2_REPORT['system_menu']['%dx%d'%size]=dict(box=[at.x(),at.y(),menu.width(),menu.height()],scrolls=menu.scroll.verticalScrollBar().maximum()>0)
 record(name,'The System menu at %d by %d, 14 pt, opened with Return from the Graphite symbol: Game first (STRUTHIO); Stop all jobs directly beneath (the Master Stop, scoped in words to the work Graphite manages); the process list: active jobs as they started, the queue with each row\'s place number at the left (its order: drag, Earlier, Later) and its niceness slider under it (two different controls); Graphite services On · Off · Restart (Graphite\'s own services); then, set apart, Log out (this login session), %s (this Graphite session), Restart and Shut down (this computer). The check holds logind with no login session (as this container truly has none), so the three are unavailable and say so in quiet ink, still in the keyboard\'s order (the reason is their tooltip, F1\'s note and what choosing one says); on the owner\'s computer logind decides. It opens downward from the upper right, the programs list\'s point-mirror image.%s'%(size[0],size[1],leave['label'],' At this height it scrolls; End reaches the last row.' if menu.scroll.verticalScrollBar().maximum()>0 else ''),
  with_popups(menu),'ACTUAL_QT_WINDOW_AND_POPUP_GRABS')
menu.close_menu();w.resize(1920,1200);settle(60);align(4);w.show_start();w.tabs.setFocus();settle()
# both menus at once with the mirrored guides: the inset from the side edges and the band from the top and the foot
hatch.open_list(False);settle();menu=sym.open(False);settle()
board=with_popups(lst,menu);p=QPainter(board);W=w.width();H=w.height();d=w.desk;p.setPen(QPen(QColor('#c99a2e'),1,Qt.DashLine))
for x in (d.inset,W-d.inset):p.drawLine(x,0,x,H)
for y in (w.ribbon_dock.height(),H-w.type_dock.height()):p.drawLine(0,y,W,y)
p.setPen(QPen(QColor(desk_qt.ERASER_MARK),2));p.drawLine(W//2,0,W//2,H);p.drawLine(0,H//2,W,H//2);p.end()
record('Graphite_Desk_14_Menus_Point_Mirror_1920x1200.png','The programs list and the System menu open together at 1920 by 1200 with the guides (dashed yellow): the band\'s inset from the left and right edges, the head band\'s foot and the lower band\'s top; the pink cross is the window\'s centre, the point they mirror about: the same inset, the same band, one width, one row height, one icon column, the small caption at each far end.',board,'ACTUAL_QT_WINDOW_AND_POPUP_GRABS_WITH_DRAWN_GUIDES')
menu.close_menu();lst.close_menu();settle()
# Stop all jobs reaches the Master Stop (its action; check_head_ui runs the real stop); Game opens STRUTHIO (patched)
with patch.object(w.a_master_stop,'trigger') as stopped:
 menu=sym.open(True);settle();QTest.keyClick(app.focusWidget(),Qt.Key_Down);settle();assert app.focusWidget() is menu.kill
 QTest.keyClick(app.focusWidget(),Qt.Key_Return);settle(60)
assert stopped.call_count==1 and not menu.isVisible(),stopped.call_count
with patch.object(struthio_qt,'show') as game:menu=sym.open(True);settle();QTest.keyClick(app.focusWidget(),Qt.Key_Return);settle(60)
assert game.call_count==1 and game.call_args[0][0] is w
# Log out, Restart, Shut down: with no session nothing is asked or issued; with a fake logind, the leave flow runs before the command
from PySide6.QtWidgets import QMessageBox as _QMessageBox
with patch.object(_QMessageBox,'warning',return_value=_QMessageBox.Ok) as warned,patch.object(session_power,'leave_steps',side_effect=AssertionError('no leave flow without a session')):
 refused=session_power.run_action(w,'shutdown')
assert refused['state']=='UNAVAILABLE' and refused['reason'].startswith(session_power.NO_SESSION) and warned.call_count==1 and not w._closing,refused
assert held_logind.call_count>0 and all(c.args[0][0]=='logind' for c in held_logind.call_args_list),'only logind reads, all held'
issued=[];order=[]
def fake_system(request):
 if request[0]=='logind':return {'Get':'2','CanReboot':'yes','CanPowerOff':'yes'}[request[3]]
 if request[0]=='where':return '/usr/bin/'+request[1]
 issued.append(tuple(request[1]));order.append('command');return dict(ok=True,code=0,reason='')
def confirm_seen(*a,**kw):order.append('confirm');return _QMessageBox.Yes
# D2-fix order: the leave flow's questions, the confirmation (nothing stopped before it), the ordinary close (held here: the
# window stays for the steps after), then the one command; the application's quit is held across the close and the command
with patch.object(session_power,'system',fake_system),patch.object(session_power,'leave_steps',side_effect=lambda h:(order.append('leave'),dict(keep=True,discarded=[],owned=[]))[1]),\
     patch.object(session_power,'quiet_close',side_effect=lambda h,left:(order.append('close'),app.quitOnLastWindowClosed())[1] is False),patch.object(_QMessageBox,'question',side_effect=confirm_seen),\
     patch.object(session_power,'_end',side_effect=lambda a:order.append('end')):
 menu=sym.open(False);settle();assert all(menu.session_rows[a].isEnabled() and not menu.session_rows[a].unavailable for a in session_power.ACTIONS)
 QTest.mouseClick(menu.session_rows['restart'],Qt.LeftButton);settle(80)
assert issued==[('systemctl','reboot')] and order==['leave','confirm','close','command','end'],(issued,order)
assert app.quitOnLastWindowClosed() and w.isVisible(),'the quit rule restored; the close was held here'
D2_REPORT['session_power']=dict(no_session=refused['state'],fake_logind_restart=dict(order=order,argv=list(issued[0])),f1_unavailable=f1_unavailable,logind_reads_held=held_logind.call_count,
 confirm='session_power.confirm through QMessageBox.question (held: Yes) after the leave flow\'s questions and before the ordinary close; the close before the command')
# creation moved to Work: New Idea and New Project
work_menu=w.menu_groups['File'];assert w.a_new_idea in work_menu.actions() and w.a_new_project in work_menu.actions()
w.a_new_idea.trigger();settle();sheet=getattr(w,'_capture_dialog',None);assert sheet is not None and sheet.isVisible();sheet.reject();settle()
homes['The Hatch groups and Explore the workshop']='the cat\'s programs list: every program and capability A to Z, then Explore the workshop'
homes['New Idea and New Project (the old menu)']='Work ▸ New Idea… (Ctrl+Shift+N) and Work ▸ New Project… (D4: the Work tree\'s right-click)'
homes['Graphite services, Exit Graphite or Return to Debian (the old menu)']='the System menu: Graphite services On · Off · Restart, and the separated group'
homes['Nice and the kill switch']='the System menu: Stop all jobs under Game, then the process list (Ctrl+Shift+F12 and Tools ▸ STOP / KILL as before)'
launcher.assert_not_called();submission.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
check('13 The cat, the programs list and the System menu (D2): the cat is pale paper on the band (%s, the band\'s brightest value: %s:1 on its mean tone, the lettering %s:1), graphite eyes and paws, a pink nose and ears, yellow irises only on hover and while the list is open; Reduce motion switches its poses directly; one click opens the list from sleep (the open pose while it is open), Escape closes it; Return opens it with Agenda under focus, typing fi jumps to Files, F1 reads its descriptor, Return opens the Files workspace (navigation, no job); the list holds every capability of the Hatch groups once (%d) A to Z and Explore the workshop; the System menu reads Game, Stop all jobs, the process list (the queue\'s place numbers 1 and 2 and each row\'s slider), Graphite services On · Off · Restart, then Log out, %s, Restart, Shut down with their scope words; here (no login session) the three are unavailable with that reason and run_action refuses before any question; session_power.system is held for the whole run (logind answers no session, on any computer); an unavailable row stays in the keyboard\'s order and F1 reads its reason; with a fake logind Restart asked the leave flow\'s questions, the confirmation, then closed the ordinary way (held here) and only then issued the one command (systemctl reboot, through session_power.system, faked); Stop all jobs reached the Master Stop\'s action; Game opened STRUTHIO; New Idea and New Project are under Work; captures 09 to 14'%(
 light['coat'],light['coat_on_mean'],light['lettering_on_mean'],len(explore.VIEWS),leave['label']))
# 11 · reopen: the saved width restores both panes --------------------------------------------------------------------------------
assert w.close() is True;settle()
w2=WorkbenchWindow(root,Session(RUN/'profile/session.json',root),restore=True);w2.resize(1920,1200);w2.show();settle(120);w2.ledger_bridge.timer.stop();w2.type_bar.hatch.lifecycle.timer.stop()
align(4,w2)
assert [w2.nav_dock.width(),w2.sim_dock.width()]==[before+10,before+10],(w2.nav_dock.width(),w2.sim_dock.width())
assert not symmetry.worst(desk_pairs(w2)),symmetry.table(symmetry.worst(desk_pairs(w2)))
assert w2.close() is True;settle()
launcher.assert_not_called();provider.assert_not_called();submission.assert_not_called();popen.assert_not_called();system.assert_not_called();detached.assert_not_called()
check('11 Reopened from the saved session, both panes are %d px again and every pair measures 0 px; clean close with zero job, worker, model, provider, native or OS session activity'%(before+10))
result=dict(schema='graphite.desk-ui/1',item='HATCH DESK D1a, D1b and D1-fix; D3 (the writing line and Log)',state='PASSED',writing_line=D3_CAPTURES,mode='ACTUAL_QT_OFFSCREEN',checks=checks,captures=captures,homes=homes,quiet_script=quiet_rule,
 pointer=dict(hotspot=list(shape['hotspot']),tip=list(shape['tip']),aim_degrees_left_of_vertical=round(graphite_brand.pointer_angle(shape['polygons']),9),size=list(shape['size']),reach=shape['reach']),
 measured=measured,grain=grain,grain_report=report,bands_line_half_tall=dict(console=heights,band=band_top),
 drag=dict(start=before,halfway_left=mid,after_left=after_left,halfway_right=mid2,after_right=after_right,saved=before+10),
 cursor_over_separators={k:[str(a).split('.')[-1],str(b).split('.')[-1]] for k,(a,b) in cursors.items()},ctrl_k=ctrl_k,
 rules=dict(pane=desk_qt.PANE,centre_floor=desk_qt.CENTRE,inset=desk_qt.INSET,gap=desk_qt.GAP,menu_gap=desk_qt.MENU_GAP,symbol=desk_qt.SYMBOL,
  band_pad=desk_qt.BAND_PAD,word_chrome=desk_qt.WORD_CHROME,scale_max=desk_qt.SCALE_MAX,grain_tile=list(desk_qt.GRAIN_SIZE),grain_amplitude=desk_qt.GRAIN_AMPLITUDE),
 jobs_submitted=0,worker_processes_started=0,model_generations=0,provider_requests=0,native_invocations=0,os_power_or_logout_commands=0,
 owner_host_acceptance=False,clean_close=True)
result['cat_programs_and_system_menu']=D2_REPORT  # HATCH DESK D2: the cat's colours, the programs list, the System menu, session and power
(OUT/'desk-ui.json').write_text(json.dumps(result,indent=1,ensure_ascii=False)+'\n')
print(json.dumps(dict(state=result['state'],checks=len(checks),captures=len(captures)),ensure_ascii=False),flush=True)
for guard in (question,detached,system,popen,submission,launcher,provider):guard.stop()
