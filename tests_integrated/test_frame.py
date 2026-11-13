"""DESKTOP-01 frame: the strip's pure arithmetic (HATCH DESK D1a: the panes' one width is test_desk), the remembered widths, the held-state words.

No QApplication is created here; the Qt behaviour (actual window bounds, focus, captures) is tools/check_frame_ui.py.
"""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import typebar_qt as bar
from workbench.session import Session,SIMULATOR_WIDTHS,NAVIGATOR_WIDTHS,NAVIGATION_MODES


class ColumnArithmeticTests(unittest.TestCase):
    """HATCH DESK D1a replaced the two columns' own floors, caps and the top row's holder widths with the desk's one width for
    both panes (workbench/desk_qt.py, tests_integrated/test_desk.py). What stays here: the workspace's floor, the explicit
    elision rule, the saved widths and the cat's size."""
    def test_the_workspace_floor_is_the_desks(self):
        from workbench import desk_qt
        self.assertEqual(bar.centre_floor(1.0),400);self.assertEqual(bar.centre_floor(18/14),514);self.assertEqual(bar.centre_floor(2.0),560)
        self.assertEqual(bar.centre_floor(0.64),400,'a smaller interface never lowers the centre floor')
        self.assertEqual([bar.centre_floor(s) for s in (1.0,18/14,20/14)],[desk_qt.centre_floor(s) for s in (1.0,18/14,20/14)])
        for name in ('column_cap','column_floor','library_floor','yield_to_centre','target_width','holder_widths'):
            self.assertFalse(hasattr(bar,name),name+' was an asymmetric column rule; the desk has one width for both panes')

    def test_secondary_words_share_the_room_only_when_whole_words_do_not_fit(self):
        self.assertEqual(bar.fit_secondary([58,58,54],200),[58,58,54])
        self.assertEqual(bar.fit_secondary([100,100,91],230),[76,76,76])
        self.assertEqual(bar.fit_secondary([60,75],300),[60,75]);self.assertEqual(bar.fit_secondary([],10),[])
        self.assertEqual(bar.fit_secondary([100,20],90),[45,20],'a short word keeps its width inside its share')

    def test_saved_widths_are_bounded_and_the_ranges_match_the_session(self):
        self.assertEqual(bar.saved_width(420,bar.NAV_RANGE,285),420);self.assertEqual(bar.saved_width(900,bar.NAV_RANGE,285),285)
        self.assertEqual(bar.saved_width(900,bar.SIM_RANGE,330),900);self.assertEqual(bar.saved_width('420',bar.SIM_RANGE,330),330);self.assertEqual(bar.saved_width(None,bar.SIM_RANGE,330),330)
        self.assertEqual((bar.NAV_RANGE,bar.SIM_RANGE),(NAVIGATOR_WIDTHS,SIMULATOR_WIDTHS))
        self.assertEqual(bar.FACTORY_RIGHT,330,'with the left\'s 285, the shipped pair is no owner\'s choice: the desk\'s default applies')

    def test_the_hatch_tile_follows_the_interface_size_under_the_cap(self):
        # UI-03: the owner's egg is 44 px high at 14 pt and follows the interface size up to 1.4, as the columns do; never smaller.
        self.assertEqual(bar.HATCH_ICON,44);self.assertEqual(bar.hatch_icon_px(1.0),44);self.assertEqual(bar.hatch_icon_px(16/14),50)
        self.assertEqual(bar.hatch_icon_px(18/14),57);self.assertEqual(bar.hatch_icon_px(20/14),62,'at 20 pt the 1.4 cap already binds (20/14 is 1.43)')
        self.assertEqual(bar.hatch_icon_px(2.0),62,'28 pt is capped at 1.4');self.assertEqual(bar.hatch_icon_px(0.64),44,'a smaller interface never shrinks the egg')

    def test_the_strip_words_and_destination_hint(self):
        # 0.5.3: five modes, all on the strip (Search was reached by shortcut only; Web is new).
        self.assertEqual([label for _,label in bar.TARGETS],['Assistant','Terminal','Search','Web','Log'])
        self.assertEqual([key for key,_ in bar.TARGETS],['slate','shell','find','web','log'],'the earlier keys, prefixes and histories unchanged')
        self.assertEqual(bar.PRIMARY_TARGETS,('slate','shell','find','web','log'));self.assertEqual(bar.QUIET_TARGETS,())
        self.assertTrue(bar.destination_hint('shell').startswith('Terminal · '));self.assertIn(bar.HINTS['shell'],bar.destination_hint('shell'))
        self.assertTrue(bar.destination_hint('slate').startswith('Stacy · '))


class SessionLoaderTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name);self.path=self.base/'session.json'

    def write(self,**extra):
        s=Session(self.path);s.state.update(extra);s.save();return Session(self.path)

    def test_simulator_width_round_trips_within_bounds(self):
        s=Session(self.path);s.set_layout(navigator_width=420,simulator_width=440);s.save()
        again=Session(self.path);self.assertEqual((again.layout['navigator_width'],again.layout['simulator_width']),(420,440))
        s.set_layout(simulator_width=901);self.assertEqual(s.layout['simulator_width'],440,'out of range is ignored')
        s.set_layout(simulator_width=900);self.assertEqual(s.layout['simulator_width'],900);s.set_layout(simulator_width=159);self.assertEqual(s.layout['simulator_width'],900)
        raw=json.loads(self.path.read_text());raw['layout']['simulator_width']=5000;self.path.write_text(json.dumps(raw))
        self.assertNotIn('simulator_width',Session(self.path).layout,'a tampered value never loads')
        self.assertEqual(SIMULATOR_WIDTHS,(160,900))

    def test_reset_layout_forgets_the_remembered_widths(self):
        s=Session(self.path);s.set_layout(navigator_width=420,simulator_width=440);s.reset_layout()
        self.assertNotIn('simulator_width',s.layout);self.assertEqual(s.layout['navigator_width'],285)

    def test_writing_marker_loads_as_a_bool_only(self):
        self.assertEqual(self.write(writing_marker=False).state.get('writing_marker'),False)
        self.assertEqual(self.write(writing_marker=True).state.get('writing_marker'),True)
        self.assertNotIn('writing_marker',self.write(writing_marker='yes').state)
        self.assertNotIn('writing_marker',Session(self.path.with_name('fresh.json')).state,'no default is invented by the loader; the setting owns it')

    def test_settings_navigation_accepts_the_machine_view(self):
        self.assertEqual(NAVIGATION_MODES,('cabinet','settings','machine'))
        from workbench.settings_registry import nodes
        selected=nodes()[0]['id']
        for mode,kept in (('machine',True),('settings',True),('cabinet',True),('elsewhere',False)):
            s=self.write(settings_navigation={'mode':mode,'selected':selected,'expanded':[]})
            self.assertEqual('settings_navigation' in s.state,kept,mode)


class HeldStateWordsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'work';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop)
        from workbench.engineering_kernel import Kernel,operator
        from workbench import ledger_control
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(self.base/'profile/session.json',self.root);self.s.save();ledger_control.bind(self.kernel,self.s)

    def call(self,op,args=None):
        response=self.kernel.dispatch(op,args or {},self.owner);self.assertTrue(response['ok'],response);return response['result']

    def test_queue_rows_carry_the_one_service_sentence_beside_the_machine_word(self):
        from workbench.service_lifecycle import SUMMARIES
        from workbench.operations import SERVICES_HELD
        self.call('agenda.add',{'title':'Held work','program':'@files:input.txt'})
        self.call('ledger.settings.set',{'key':'operations.services_enabled','value':False})
        with patch('subprocess.Popen',side_effect=AssertionError('No process launch')):value=self.call('ledger.operations')
        checks=value['agenda']['next'][0]['schedule_checks']
        self.assertIn(SERVICES_HELD,checks['reasons']);self.assertEqual(checks['services_summary'],value['services']['summary'])
        self.assertEqual(checks['services_summary'],SUMMARIES['ADMISSION_HELD'],'admission off is "held", not "off": the stop was never confirmed')
        self.assertEqual(value['jobs_submitted'],0)

    def test_a_job_is_said_in_words(self):
        from workbench.operations import tool_words
        self.assertEqual(tool_words('brain.infer','Interrupted'),'Local model · interrupted')
        self.assertEqual(tool_words('lab.python','Running'),'Laboratory · running')
        self.assertEqual(tool_words('unknown.tool'),'unknown.tool');self.assertEqual(tool_words(None,'Queued'),'Job · queued')


if __name__=='__main__':unittest.main()
