"""0.8.2: the first scene (tools/campaign_lib/data/scenes/P01.json), played on the live window by desk acts alone.

The owner's playable scene: open a menu across the head; Then over a CSV in Files (keep rows where unit is mA, count, put it
in the writing line); back to the Field; trace 07 Bench readings; compare the two revisions of the limits; and take back
what Stacy's hand wrote. It is played by pointer (real mouse events and right-clicks), by keys (the keys a person would
press, sent where the keyboard is), and by pointer with less motion. Every step is an act (desk_doers.run, door 'script')
and every check reads what read.desk reads; nothing here reaches into a widget.

The window is built once on the bench seed (test_desk_acts.build_window: three sheets imported through Graphite's own
operations, the two revisions among them); the After Hours 07 run of the same scene is the campaign's (tools/campaign.py
--set scenes).
"""
import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from tests_integrated.test_desk_acts import P01,build_window,close_window,settle

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
        if (WINDOW['files']/'07 Bench readings.csv').exists():WINDOW['k'].dispatch('files.trash',{'path':'07 Bench readings.csv'},operator())
        if w.type_bar.box.text():w.type_bar.box.clear()
        w._desk_put='';settle(WINDOW)

    def play(self,run):
        from workbench import desk_scene
        scene=desk_scene.load(P01)
        out=desk_scene.run_scene(WINDOW['w'],scene,run,seed='bench',origin='desk-script:P01')
        self.assertNotIn('blocked',out)
        self.assertTrue(out['passed'],desk_scene.failures(out))
        self.assertEqual(len(out['steps']),len(scene['steps']))
        self.assertFalse((WINDOW['files']/'07 Bench readings.csv').exists(),'the scene takes back what it wrote')
        return out

    def test_p01_by_mouse(self):
        out=self.play('mouse')
        self.assertTrue(all(s['by'] in ('pointer','direct') for s in out['steps']),[(s['act'],s['by']) for s in out['steps']])

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
