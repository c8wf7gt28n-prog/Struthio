"""Stacy starts a project in another program: what counts as asking, which Godot is here, and the files she writes."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from workbench import program_build
from workbench import stacy_start as start

PROBE={3:('extends SceneTree\n\nfunc _init():\n\tvar node = load("res://main.tscn").instance()\n\tget_root().add_child(node)\n\tyield(self, "idle_frame")\n'
          '\tprint("PROBE: ", node.get_node("Label").text)\n\tquit()\n'),
       4:('extends SceneTree\n\nfunc _init():\n\tvar node = load("res://main.tscn").instantiate()\n\tget_root().add_child(node)\n\tawait process_frame\n'
          '\tprint("PROBE: ", node.get_node("Label").text)\n\tquit()\n')}


class AskedTests(unittest.TestCase):
    def test_the_ways_of_asking_for_a_start_in_godot(self):
        self.assertEqual(start.asked('start a Godot project called Lander'),('godot','Lander'))
        self.assertEqual(start.asked('Please make me a game in Godot named "Rail Runner".'),('godot','Rail Runner'))
        self.assertEqual(start.asked('get me started on a project in Godot called Lander'),('godot','Lander'))
        self.assertEqual(start.asked('get me started in Godot'),('godot','First Godot project'),'with no name it has one')
        self.assertEqual(start.asked('create a new Godot game'),('godot','First Godot project'))

    def test_other_words_are_not_taken_for_it(self):
        for text in ('start the page again','make a folder called Godot','what is Godot?','open the Godot room','start a project','godot'):
            self.assertIsNone(start.asked(text),text)

    def test_a_folder_name_holds_only_what_a_folder_name_can(self):
        self.assertEqual(start.folder_name('Rail/Runner: "2"?'),'Rail Runner 2');self.assertEqual(start.folder_name('...'),'Godot project')
        self.assertLessEqual(len(start.folder_name('x'*200)),60)


class ToolTests(unittest.TestCase):
    def test_the_godot_on_this_computer_is_found_by_any_of_its_three_names(self):
        found=start.godot_tool(which=lambda c:'/usr/bin/godot3' if c=='godot3' else None,major=lambda e:3)
        self.assertEqual((found['available'],found['command'],found['major']),(True,'godot3',3),'Debian 13: the package godot3')
        found=start.godot_tool(which=lambda c:'/opt/godot' if c=='godot' else None,major=lambda e:4);self.assertEqual((found['command'],found['major']),('godot',4))
        found=start.godot_tool(which=lambda c:'/usr/bin/godot3' if c=='godot3' else None,major=lambda e:None);self.assertEqual(found['major'],3,'an engine that does not answer: its name decides')
        none=start.godot_tool(which=lambda c:None);self.assertEqual((none['available'],none['major']),(False,start.DEBIAN_SHIPS),'with none, the files are for what Debian would install')

    def test_the_major_version_is_what_the_engine_answers(self):
        answer=lambda text:(lambda command,**kw:type('R',(),{'stdout':text,'stderr':''})())
        self.assertEqual(start.godot_major('godot',run=answer('3.6.stable.custom_build\n')),3);self.assertEqual(start.godot_major('godot',run=answer('4.4.1.stable.official.49a5bc7b6')),4)
        self.assertIsNone(start.godot_major('godot',run=answer('no version here')))
        def missing(command,**kw):raise OSError('no such file')
        self.assertIsNone(start.godot_major('godot',run=missing))

    def test_the_godot_room_looks_for_debians_godot3_too(self):
        seen=[]
        real=program_build.shutil.which;program_build.shutil.which=lambda command:seen.append(command) or ('/usr/bin/godot3' if command=='godot3' else None)
        try:tool=program_build._tool('godot')
        finally:program_build.shutil.which=real
        self.assertEqual(seen,['godot4','godot','godot3']);self.assertTrue(tool['available']);self.assertTrue(tool['executable'].endswith('godot3'))


class FilesTests(unittest.TestCase):
    def test_each_godot_gets_its_own_files(self):
        three=dict(start.godot_files('Lander',3));four=dict(start.godot_files('Lander',4))
        self.assertEqual(sorted(three),['main.gd','main.tscn','project.godot']);self.assertEqual(sorted(four),sorted(three))
        self.assertIn('config_version=4',three['project.godot']);self.assertIn('format=2',three['main.tscn']);self.assertIn('rect_position',three['main.gd'])
        self.assertIn('config_version=5',four['project.godot']);self.assertIn('format=3',four['main.tscn']);self.assertNotIn('rect_position',four['main.gd'])
        for files in (three,four):
            self.assertIn('config/name="Lander"',files['project.godot']);self.assertIn('run/main_scene="res://main.tscn"',files['project.godot'])
            self.assertIn('res://main.gd',files['main.tscn']);self.assertTrue(all(text.endswith('\n') for text in files.values()))

    def test_a_name_with_quotes_stays_inside_its_quotes(self):
        files=dict(start.godot_files('Rail "Runner"',3))
        self.assertIn('config/name="Rail \\"Runner\\""',files['project.godot']);self.assertIn('text = "Rail \\"Runner\\""',files['main.tscn'])

    def test_the_godot_room_reads_what_she_writes(self):
        for major in (3,4):
            folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)
            for name,text in start.start_files('Lander',{'available':False,'major':major}):(root/name).write_text(text,encoding='utf-8')
            config=program_build._godot_config(root/'project.godot');scenes,_=program_build._godot_scenes(root)
            self.assertEqual((config['title'],config['main_scene'],config['config_version']),('Lander','res://main.tscn',5 if major==4 else 4))
            self.assertEqual(scenes,['res://main.tscn']);self.assertIn('Godot %d'%major,(root/'START_HERE.md').read_text(encoding='utf-8'))

    def test_the_first_steps_say_which_godot_and_whether_it_is_here(self):
        here=start.first_steps('Lander',3,{'available':True,'command':'godot3'},now=0);away=start.first_steps('Lander',3,{'available':False},now=0)
        self.assertIn('Godot 3 is on this computer (godot3)',here);self.assertIn('package godot3',away);self.assertIn('Sprite,',here)
        self.assertIn('Sprite2D',start.first_steps('Lander',4,{'available':False},now=0))

    def test_the_files_run_in_a_real_godot_when_one_is_installed(self):
        """Where a Godot engine that runs without a screen is on the machine (Godot 3's server build, or Godot 4), the
        starting scene is loaded and run in it."""
        ran=0
        for command,major,flags in (('godot3-server',3,[]),('godot4',4,['--headless'])):
            engine=shutil.which(command)
            if not engine:continue
            folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)/'Lander';root.mkdir()
            for name,text in start.godot_files('Lander',major):(root/name).write_text(text,encoding='utf-8')
            probe=Path(folder.name)/'probe.gd';probe.write_text(PROBE[major],encoding='utf-8')
            out=subprocess.run([engine,*flags,'--path',str(root),'-s',str(probe)],capture_output=True,text=True,timeout=120)
            self.assertIn('PROBE: Lander: it runs.',out.stdout+out.stderr,command);self.assertNotIn('SCRIPT ERROR',out.stdout+out.stderr);ran+=1
        if not ran:self.skipTest('no Godot engine that runs without a screen is installed on this machine')


if __name__=='__main__':unittest.main()
