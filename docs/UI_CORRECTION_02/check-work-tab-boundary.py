"""Bounded real-Qt diagnostic for document metadata; no job/model execution."""
import argparse,json,os,sys,time,traceback
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--program',type=Path,required=True);parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--screens',type=Path);args=parser.parse_args()
os.environ.update(QT_QPA_PLATFORM='offscreen',ARC_LEDGER_EMBEDDED='1',ARC_LEDGER_DISABLE_BOOK_WATCHER='1',ARC1_WORKBENCH_CONFIG_HOME=str(args.fixture/'profile'),ARC_LEDGER_CONCERN=str(args.fixture/'concern'))
sys.path.insert(0,str(args.program));sys.dont_write_bytecode=True
from PySide6.QtCore import QByteArray,QBuffer,QIODevice
from PySide6.QtTest import QTest
from workbench.qt_app import make_app,WorkbenchWindow,CodeEditor
from workbench import locations,engine,continuing_work_qt,ledger_control
from workbench.session import Session
from workbench.engineering_kernel import operator
began=time.monotonic();errors=[];stages=[]
sys.excepthook=lambda typ,value,tb:errors.append({'where':'Qt event','type':typ.__name__,'message':str(value)})
app=make_app([]);root=locations.office(args.fixture/'workspace');w=WorkbenchWindow(root,Session(args.fixture/'profile/session.json',root),restore=False)
for obj in (getattr(w,'agenda_runner',None),getattr(w,'study_idle',None)):
    timer=getattr(obj,'timer',None)
    if timer:timer.stop()
w.resize(1920,1200);w.show()
def settle():
    for _ in range(3):app.processEvents();QTest.qWait(35)
def attempt(name,call):
    try:call();stages.append({'name':name,'state':'RETURNED'})
    except Exception as exc:errors.append({'where':name,'type':type(exc).__name__,'message':str(exc)})
def capture(name):
    if not args.screens:return
    args.screens.mkdir(parents=True,exist_ok=True);data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.WriteOnly)
    if not w.grab().save(buffer,'PNG'):raise ValueError('PNG encoding failed')
    (args.screens/name).write_bytes(bytes(data));buffer.close()
tab=continuing_work_qt.show(w);w.tabs.pin(tab);settle()
for name,call in [('document_info',w.update_document_info),('inspector',w.arc_inspector.refresh),('desktop_publish',w.ledger_bridge.publish)]:attempt(name,call)
capture('01-continuing-work.png')
source=root/'context-example.txt';source.write_text('Disposable UI diagnostic document. No master file.\n')
editor=w.open_document(source,viewer=False);settle();w.ledger_bridge.publish()
file_context=ledger_control.context(w.ledger_bridge.kernel)['desktop']
w.tabs.setCurrentWidget(tab);settle();attempt('publish_after_document',w.ledger_bridge.publish)
work_context=ledger_control.context(w.ledger_bridge.kernel)['desktop']
for _ in range(3):
    w.tabs.setCurrentWidget(editor);settle();w.tabs.setCurrentWidget(tab);settle();attempt('refresh_work_context',w.arc_inspector.refresh)
sample=root/'hardware/compact-arc1/R10_WORK/f133/example.c'
checks={'real_document_published':file_context.get('active_file')=='context-example.txt',
    'non_file_workspace_clears_active_file':'active_file' not in work_context,
    'picker_preserved':tab.path.currentText()=='' and tab.path.isEditable(),
    'legacy_source_target_str':engine.context_target(str(sample),root)=='f133',
    'legacy_source_target_path':engine.context_target(sample,root)=='f133'}
attempt('path_picker_target',lambda:checks.update(path_picker_target_ignored=engine.context_target(tab.path,root) is None))
if hasattr(engine,'document_path'):
    checks['invalid_path_values_ignored']=all(engine.document_path(v) is None for v in (None,'','  ','bad\x00name',42,object(),tab.path))
    checks['pathlike_and_string_preserved']=engine.document_path(source)==source and engine.document_path(str(source))==source
capture('02-work-context-after-switch.png')
jobs=w.ledger_bridge.kernel.dispatch('jobs.list',{},operator());checks['zero_jobs']=jobs.get('ok') and jobs['result']==[]
result={'state':'PASSED' if not errors and all(checks.values()) else 'FAILED','seconds':time.monotonic()-began,'checks':checks,'errors':errors,'stages':stages,'file_context':file_context,'work_context':work_context,'capture_mode':'ACTUAL_QT_OFFSCREEN','model_generations':0,'jobs':jobs,'scope':'Document context and real path-picker boundary only; no native application or scheduler acceptance.'}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'state':result['state'],'seconds':result['seconds'],'checks':checks,'exceptions':len(errors)},indent=2),flush=True)
w._closing=True;w.hide();QTest.qWait(250)
