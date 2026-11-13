"""Stacy's hand: the dial, what always asks, what takes an act back, her trail, and the Terminal lines that are hers."""
import tempfile
import unittest
from pathlib import Path

from workbench import stacy_hand as hand
from workbench.session import Session


class DialTests(unittest.TestCase):
    def test_a_read_is_always_hers_and_a_change_follows_the_dial(self):
        for place in ('ask','show','free'):self.assertTrue(hand.hers(place,'read','field.read'))
        self.assertFalse(hand.hers('ask','execute','field.set'),'Ask first: every change waits');self.assertFalse(hand.hers('ask','approve','calc.recompute'))
        self.assertTrue(hand.hers('show','execute','field.set'),'Do and show: she makes the changes the Kernel calls execute')
        self.assertFalse(hand.hers('show','approve','calc.recompute'),'what the Kernel marks approve still waits')
        self.assertTrue(hand.hers('free','approve','calc.recompute'));self.assertFalse(hand.hers('free','candidate','x.y'),'a scope it does not know asks')

    def test_what_cannot_be_undone_asks_on_every_place(self):
        for name in ('exchange.send','pills.send','memory.profile.delete','references.pdf.annotation.remove','trash.empty','files.trash.empty','power.off','session.end','shell.run'):
            self.assertTrue(hand.why_asks(name),name)
            for place in ('ask','show','free'):self.assertFalse(hand.hers(place,'execute',name),(place,name))
        self.assertEqual(hand.why_asks('field.set'),'');self.assertEqual(hand.why_asks('files.write',{'path':'Notes/a.txt','text':'x'}),'')
        self.assertTrue(hand.why_asks('files.copy',{'path':'a','address':'10.0.0.5'}),'an address among the arguments: it reaches another computer')
        self.assertEqual(hand.why_asks('files.trash'),'','moving to the Trash can be undone; emptying it cannot')

    def test_no_operation_the_program_has_that_leaves_the_computer_or_forgets_is_hers(self):
        """Every operation in the registry is run against the rule (0.7.0): with a free hand none of these is hers."""
        import json
        ops=json.loads((Path(__file__).resolve().parents[1]/'docs'/'GRAPHITE_0.1_REGISTRY.json').read_text(encoding='utf-8'))['operations']
        for name in ('programs.transfer.download','programs.transfer.list','programs.mail.draft','programs.mail.open','programs.delivery.build','pills.fetch','pills.pair',
                     'pills.unpair','notes.exchange.commit','notes.exchange.export','remote.disable','remote.revoke','releases.install','network.capture.start',
                     'changes.publish','ledger.windows.publish','knowledge.revoke','matrix.forget','memory.context.clear','copies.discard','records.clear_staging',
                     'joined.session.takeover','repairs.authorize','words.forget','memory.profile.delete','exchange.send'):
            self.assertIn(name,ops,name+' is an operation the program has');self.assertTrue(hand.why_asks(name),name)
            self.assertFalse(hand.hers('free',ops[name]['scope'],name),name)
        for name in ('field.set','files.write','files.mkdir','files.trash','documents.create','ideas.capture','office.datasheet.recheck','programs.godot.open'):
            self.assertIn(name,ops);self.assertEqual(hand.why_asks(name),'',name+' follows the dial')
        self.assertTrue(hand.hers('ask','read','exchange.list'),'a read never asks, whatever it reads')

    def test_the_dial_is_kept_in_the_session_and_opens_on_do_and_show(self):
        host=type('H',(),{})();host.session=type('S',(),{'state':{}})()
        self.assertEqual(hand.level(host),'show');self.assertEqual(hand.choose(host,'free'),'free');self.assertEqual(host.session.state[hand.KEY],'free')
        self.assertEqual(hand.choose(host,'anything'),'free','a place that is not on the dial changes nothing')
        host.session.state[hand.KEY]='loose';self.assertEqual(hand.level(host),'show','a value that is not a place is read as the opening one')
        self.assertEqual([k for k,_ in hand.LEVELS],['ask','show','free'])


class UndoTests(unittest.TestCase):
    def test_a_number_set_is_taken_back_to_what_it_said_at_the_revision_she_left(self):
        result={'id':'office:abc','cell':'B3','was':'280','now':'300','revision':7}
        line=hand.takes_back('field.set',{'id':'office:abc','cell':'B3','value':'300','expected_revision':6},result)
        self.assertTrue(line.startswith('/field.set '));import json;back=json.loads(line.split(' ',1)[1])
        self.assertEqual(back,{'id':'office:abc','cell':'B3','value':'280','expected_revision':7})
        self.assertEqual(hand.takes_back('field.set',{},{'id':'office:abc','cell':'B3','now':'300','revision':7}),'','without what it said, nothing is offered')
        self.assertEqual(hand.takes_back('field.brief.keep',{},{'document':{'id':'d1'}}),'','only what can be put back exactly is offered')


class MadeTests(unittest.TestCase):
    """An artifact asked of her in plain words: what is to be made, by what name, with what words."""

    def test_a_folder_a_file_a_page_and_a_note_are_told_apart(self):
        self.assertEqual(hand.made('make a folder called Bracket'),('folder','Bracket',''))
        self.assertEqual(hand.made('write a file called plan.txt saying cut the stock first'),('file','plan.txt','cut the stock first'))
        self.assertEqual(hand.made('make me a new file named notes'),('file','notes.txt',''),'a file with no ending is a .txt')
        self.assertEqual(hand.made('Please start a page called Bench plan, saying: Check the rail first.'),('page','Bench plan','Check the rail first.'))
        self.assertEqual(hand.made('create a document named “Rev B review”'),('page','Rev B review',''))
        self.assertEqual(hand.made('create a note called Rail idea that says try a ferrite'),('note','Rail idea','try a ferrite'))

    def test_other_words_are_not_taken_for_it(self):
        for text in ('make these words bold','set B3 to 300','make a folder called ','what is a folder called in Debian?','write to the file','start the page again'):
            self.assertIsNone(hand.made(text),text)
        self.assertEqual(hand.made('make a folder called Rail\n  Runner')[1],'Rail Runner','a line break inside a name is a space')

    def test_what_she_made_new_goes_to_the_trash_and_what_was_written_over_does_not(self):
        import json
        line=hand.takes_back('files.write',{'path':'plan.txt','text':'x'},{'path':'plan.txt','kept_version':None})
        self.assertEqual((line.split(' ',1)[0],json.loads(line.split(' ',1)[1])),('/files.trash',{'path':'plan.txt'}))
        self.assertEqual(hand.takes_back('files.mkdir',{'name':'Bracket'},{'path':'Bracket','kind':'folder'}),'/files.trash {"path": "Bracket"}')
        self.assertEqual(hand.takes_back('files.write',{},{'path':'plan.txt','kept_version':'.versions/plan.txt/1'}),'','a file that was there before is not hers to trash')
        self.assertEqual(hand.takes_back('documents.create',{},{'id':'d1','title':'Bench plan'}),'')
        for place in ('show','free'):
            for name in ('files.write','files.mkdir','documents.create','ideas.capture'):self.assertTrue(hand.hers(place,'execute',name),(place,name))


class TrailTests(unittest.TestCase):
    def test_the_trail_keeps_her_acts_latest_first_and_spends_an_undo_once(self):
        state={}
        first=hand.record(state,'Set B3 to 300 mA','/field.set {"id": "office:abc"}','/field.set {"value": "280"}','set B3 to 300',now=0)
        hand.record(state,'Keep the brief as a page','/field.brief.keep {}',ok=False,now=60)
        got=hand.trail(state);self.assertEqual([e['words'] for e in got],['Keep the brief as a page','Set B3 to 300 mA'])
        self.assertEqual([e['state'] for e in got],['refused','done']);self.assertEqual(got[1]['word'],'set B3 to 300')
        self.assertTrue(hand.taken_back(state,first));self.assertEqual(hand.trail(state)[1]['state'],'undone');self.assertEqual(hand.trail(state)[1]['undo'],'')
        self.assertFalse(hand.taken_back(state,first),'an Undo is spent once')

    def test_the_trail_is_bounded_and_a_saved_one_is_read_only_in_its_own_shape(self):
        state={}
        for n in range(hand.KEPT+9):hand.record(state,'act %d'%n,'/x {}',now=n)
        self.assertEqual(len(state[hand.TRAIL]),hand.KEPT);self.assertEqual(hand.trail(state)[0]['words'],'act %d'%(hand.KEPT+8))
        kept=hand.clean(state[hand.TRAIL]+[{'at':1,'words':'x'},'words',{'at':'t','words':'w','line':'l','undo':'','word':'','state':'elsewhere'}])
        self.assertEqual(len(kept),hand.KEPT);self.assertEqual(hand.clean('not a list'),[])


class KeptTests(unittest.TestCase):
    def test_the_dial_and_the_trail_are_kept_with_the_session_and_nonsense_is_dropped(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);path=Path(folder.name)/'session.json'
        s=Session(path);s.state[hand.KEY]='free';hand.record(s.state,'Set B3 to 300 mA','/field.set {}','/field.set {"value": "280"}','set B3 to 300',now=0);s.save()
        again=Session(path);self.assertEqual(again.state.get(hand.KEY),'free');self.assertEqual(hand.level(type('H',(),{'session':again})()),'free')
        self.assertEqual([(e['words'],e['state'],e['word']) for e in hand.trail(again.state)],[('Set B3 to 300 mA','done','set B3 to 300')])
        s=Session(path);s.state[hand.KEY]='loose';s.state[hand.TRAIL]=[{'words':7},'x'];s.save()
        again=Session(path);self.assertNotIn(hand.KEY,again.state);self.assertEqual(again.state.get(hand.TRAIL),[])
        self.assertNotIn(hand.KEY,Session(path.with_name('fresh.json')).state,'no place is invented by the loader: a fresh workspace opens on Do and show by rule')


class TerminalTests(unittest.TestCase):
    def test_commands_that_only_read_are_hers(self):
        for line in ('ls -la Documents','df -h','free -m','uname -a','ip addr show','find . -name "*.pdf"','journalctl -n 50','date','cat notes.txt','lscpu'):
            self.assertTrue(hand.terminal_hers(line),line)

    def test_anything_that_changes_pipes_or_substitutes_asks(self):
        for line in ('rm -rf x','sudo ls','ls | wc -l','cat a > b','ls; rm x','echo `id`','ls $(pwd)','find . -delete','find . -exec rm {} +','date -s 12:00',
                     'ip link set eth0 down','dmesg -C','journalctl --vacuum-time=1s','hostname newname','env X=1 rm x','','python3 x.py','ls "unterminated'):
            self.assertFalse(hand.terminal_hers(line),line)

    def test_the_forms_of_a_reading_command_that_do_more_than_read_ask(self):
        """Found by reading the list against each command's own manual (0.7.0): these were let through."""
        for line in ('ip netns exec x rm -rf y','ip vrf exec red rm x','ip -batch cmds.txt','ip -b cmds.txt','ip -n ns1 addr','ip xfrm state','ip monitor',
                     'find . -fprint0 out','find . -fprintf out %p','file -C -m magic','file -Cm magic','date 010112002030','sensors -s','journalctl --update-catalog',
                     'hostname -F /etc/hostname','hostname -b box','dmesg --console-off'):
            self.assertFalse(hand.terminal_hers(line),line)
        for line in ('ip addr','ip -br a','ip -4 route show','ip -s link show dev eth0','ip neigh','find . -name "*.gd" -newer x','file notes.txt','file -b -i a.pdf',
                     'date +%F','date -u','date -d tomorrow +%A','date -r notes.txt','sensors','journalctl -b -n 20','hostname','hostname -f','dmesg -T'):
            self.assertTrue(hand.terminal_hers(line),line)


if __name__=='__main__':unittest.main()
