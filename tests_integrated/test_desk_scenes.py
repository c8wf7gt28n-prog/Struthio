"""0.8.2: the first scene (tools/campaign_lib/data/scenes/P01.json), played on the live window by desk acts alone.

The owner's playable scene: open a menu across the head; Then over a CSV in Files (keep rows where unit is mA, count, put it
in the writing line); back to the Field; trace the bench readings; compare the two revisions of the limits; and take back
what Stacy's hand wrote. It is played by pointer (real mouse events and right-clicks), by keys (the keys a person would
press, sent where the keyboard is), each again with less motion, and by pointer on a 1366 by 768 window. Every step is an
act (desk_doers.run, door 'script') and every check reads what read.desk reads; nothing here reaches into a widget.

The window is built once on the bench seed (test_desk_acts.build_window: three sheets imported through Graphite's own
operations, the two revisions among them, under the scene's own names, which are Rail Demo's); the runs on Rail Demo and
on the owner's After Hours 07 are the campaign's (tools/campaign.py --set scenes) and test_rail_demo's.
"""
import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from tests_integrated.test_desk_acts import P01,READINGS,build_window,close_window,settle
CSV=READINGS+'.csv'      # what the scene writes in Files, and takes back

WINDOW={}


def setUpModule():
    build_window(WINDOW,'graphite-desk-scenes-')


def tearDownModule():
    close_window(WINDOW)


class PlayableScene(unittest.TestCase):
    def setUp(self):
        from workbench.desk_doers import run
        from workbench.engineering_kernel import operator
        w=WINDOW['w']
        for name,args in (('menu.close',{}),('hand.dial',{'place':'show'})):run(w,name,args,door='script',origin='desk-script:setup')
        if getattr(w,'_field_active',False):run(w,'go.back',{'by':'pointer'},door='script',origin='desk-script:setup')
        if (WINDOW['files']/CSV).exists():WINDOW['k'].dispatch('files.trash',{'path':CSV},operator())
        if w.type_bar.box.text():w.type_bar.box.clear()
        w._desk_put='';settle(WINDOW)

    def play(self,run,size=None):
        from workbench import desk_scene
        scene=desk_scene.load(P01)
        if size:scene['given']['size']=list(size)      # the scene sizes the window; the next run sizes it back
        out=desk_scene.run_scene(WINDOW['w'],scene,run,seed='bench',origin='desk-script:P01')
        self.assertNotIn('blocked',out)
        self.assertTrue(out['passed'],desk_scene.failures(out))
        self.assertEqual(len(out['steps']),len(scene['steps']))
        self.assertFalse((WINDOW['files']/CSV).exists(),'the scene takes back what it wrote')
        return out

    def test_p01_by_mouse(self):
        out=self.play('mouse')
        self.assertTrue(all(s['by'] in ('pointer','direct') for s in out['steps']),[(s['act'],s['by']) for s in out['steps']])

    def test_p01_by_mouse_on_a_small_window(self):
        # 1366 by 768, the smallest the owner's machines show: the comparison then leaves only a few pixels beside it, and
        # putting it away is still a click there, never a key (the 0.8.2 review found Esc pressed in both mouse runs)
        for run in ('mouse','mouse_still'):
            out=self.play(run,(1366,768))
            self.assertEqual((WINDOW['w'].width(),WINDOW['w'].height()),(1366,768))
            self.assertTrue(all(s['by'] in ('pointer','direct') for s in out['steps']),(run,[(s['act'],s['by']) for s in out['steps']]))
            self.setUp()

    def test_p01_by_keys_reduced_motion(self):
        out=self.play('keys_still')
        by={s['act']:s['by'] for s in out['steps']}
        for name in ('go.files','menu.open','menu.choose','then.keep','then.count','then.end','go.field','point.sheet','sheet.trace','sheet.compare','sheet.close'):
            self.assertEqual(by[name],'keys',name)
        trace=next(s for s in out['steps'] if s['act']=='sheet.trace')
        self.assertIs(trace['result']['route']['animating'],False)

    def test_p01_by_keys(self):
        out=self.play('keys')
        by={s['act']:s['by'] for s in out['steps']}
        for name in ('go.files','menu.open','menu.choose','then.keep','then.count','then.end','go.field','point.sheet','sheet.trace','sheet.compare','sheet.close'):
            self.assertEqual(by[name],'keys',name)
        self.assertIs(out['steps'][0]['result']['keyboard_route'],False)

    def test_p01_by_mouse_reduced_motion(self):
        out=self.play('mouse_still')
        trace=next(s for s in out['steps'] if s['act']=='sheet.trace')
        self.assertIs(trace['result']['route']['animating'],False)
        from workbench import menu_catch
        self.assertIs(menu_catch.calm(WINDOW['w']),False,'the motion is put back as the scene found it')


if __name__=='__main__':
    unittest.main()
