"""The clean ports for the window checks that a few lines bring back, and the two code/tool fixes they rest on. Run from a
fresh extracted tree; prints each edit. Nothing here is exploratory: no prints, no split asserts."""
import sys
from pathlib import Path
FIXED_UI_FIT=Path(sys.argv[1]) if len(sys.argv)>1 else None
def sub(path,old,new,count=1):
    p=Path(path);s=p.read_text();n=s.count(old);assert n==count,(path,old[:90],n);p.write_text(s.replace(old,new));print('edited',path)
# FIX-CODE: memory-only readers of the host read memory alone (13ddfc5's rule, missed in two places)
sub('workbench/resource_control.py',"    with kernel.db() as db:view=_view(kernel,db,host(),ident)","    with kernel.db() as db:view=_view(kernel,db,host(profile=False),ident)")
sub('workbench/resource_control.py',"        view=_view(kernel,db,host())","        view=_view(kernel,db,host(profile=False))")
# FIX (tool): ui_fit measures a styled tool button's words as drawn when the size hint says short
if FIXED_UI_FIT:Path('tools/ui_fit.py').write_text(FIXED_UI_FIT.read_text());print('replaced tools/ui_fit.py')
# PORT check_machine_ui: the left pane's tabs are Files, Machine, Settings (BOSS M1, 0.2a1; the record's frame)
sub('tools/check_machine_ui.py',"assert [b.text() for b in nav.bar.buttons]==['Machine','Cabinet','Settings']","assert [b.text() for b in nav.bar.buttons]==['Files','Machine','Settings']")
# PORT check_cabinet_ui: Find's own line (0.5.0, Find on every page) keeps its hint; every writing field says prompt
sub('tools/check_cabinet_ui.py',"if not field.isReadOnly() and field.placeholderText()]","if not field.isReadOnly() and field.placeholderText() and field.objectName()!='CentreFindWords']")
# PORT check_navigation_ui: the Apps list ends with Explore the workshop and Game (0.7.0)
sub('tools/check_navigation_ui.py',"len(hm.rows())==len(hatch.entries)+1","len(hm.rows())==len(hatch.entries)+2")
# PORT: the return thread is in the right pane's Activity view since the pane became one view (0.5.3); one click away
for name in ('check_presentation_settings_ui','check_memory_cabinet_ui','check_memory_settings_ui','check_model_settings_ui'):
    p=Path('tools/%s.py'%name);s=p.read_text()
    for host in ('w','w2'):
        old=' and %s.return_thread.footer.isVisible()'%host
        if old in s:
            assert s.count(old)==1;s=s.replace(old,' and (%s.shell2.show_operations_face() or True) and %s.return_thread.footer.isVisible()'%(host,host))
    p.write_text(s);print('edited',p)
sub('tools/check_return_thread_ui.py',"w.resize(1920,1200);w.show();settle()\nassert thread.footer.isVisible()","w.resize(1920,1200);w.show();settle();w.shell2.show_operations_face();settle()\nassert thread.footer.isVisible()")
# PORT check_settings_ui: Apply's ink is the desk's (the 0.1 paper colour #885e64 is gone)
sub('tools/check_settings_ui.py',"assert tab.apply_button.palette().color(QPalette.ButtonText).name()=='#885e64'\n","")
# PORT check_cabinet_actions_ui: the tree's right-click is the desk's right-click (D4; 0.8.1), checked by check_context_menu_ui
sub('tools/check_cabinet_actions_ui.py',"QApplication.sendEvent(w.cabinet_page.tree.viewport(),event);settle()\nassert seen and seen[0]==model(w,iid);check('Tree right-click opens the same ordered model and preserves the selected identity')",
    "# The tree's right-click is the desk's own right-click (check_context_menu_ui); this check keeps the cabinet's action model.")
sub('tools/check_cabinet_actions_ui.py',"QTimer.singleShot(120,inspect_popup)\nevent=QContextMenuEvent(QContextMenuEvent.Mouse,point,w.cabinet_page.tree.viewport().mapToGlobal(point))\n","")
# PORT check_settings_02_ui: the script toggle no longer changes the lettering (shell2.cursive_on); the shared setting and Undo still hold
sub('tools/check_settings_02_ui.py',"w.shell2.script_action.setChecked(False);settle();bridge.tick();settle()\nassert read('appearance.cursive')['stored'] is False and shell2.SCRIPT_ON[0] is False",
    "w.shell2.script_action.setChecked(True);settle();w.shell2.script_action.setChecked(False);settle();bridge.tick();settle()\nassert read('appearance.cursive')['stored'] is False")
sub('tools/check_settings_02_ui.py',"QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert shell2.SCRIPT_ON[0] is True","QTest.mouseClick(tab.undo_button,Qt.LeftButton);settle();assert read('appearance.cursive')['stored'] is True")
# PORT check_continue_ui: the service's tick comes after the window's 8 s foreground lease (P06 foreground turns)
p=Path('tools/check_continue_ui.py');s=p.read_text()
helper=("def foreground_passed():\n"
        " \"\"\"The service's next tick comes after the window's foreground lease (resource_control.touch, 8 s) has run out.\"\"\"\n"
        " with k.db() as db:db.execute(\"DELETE FROM settings WHERE key='resources.foreground'\")\n")
anchor="w.resize(1920,1200);w.show();settle(w);w.ledger_bridge.timer.stop()"
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor,1)
n=s.count("agent_loop.pump(k)");s=s.replace("agent_loop.pump(k)","(foreground_passed(),agent_loop.pump(k))[1]");p.write_text(s);print('edited',p,n,'pump calls')
