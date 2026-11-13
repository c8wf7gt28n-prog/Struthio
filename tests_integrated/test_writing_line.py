"""Writing modes, saved targets, key handling, and the Events and Network log."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import typebar_qt as bar
from workbench import log_qt as log
from workbench.session import Session


class ModeTests(unittest.TestCase):
    def test_five_modes_and_the_old_targets_mapping(self):
        # 0.5.3: Web joined the four, and all five stand on the strip (the owner's "one master typing line that I select whom I'm typing to").
        self.assertEqual(bar.TARGETS,(('slate','Assistant'),('shell','Terminal'),('find','Search'),('web','Web'),('log','Log')))
        self.assertEqual(bar.PRIMARY_TARGETS,('slate','shell','find','web','log'));self.assertEqual(bar.QUIET_TARGETS,())
        self.assertEqual(bar.MAPPED['web'],'web');self.assertEqual(bar.SHOWN,{'slate':'Stacy'},'the strip says Stacy; the mode keeps its label')
        self.assertNotIn('web',bar.CONSOLE_PAGE,'Web has no page above the line: what it opens is in the browser')

    def test_web_tells_an_address_from_words_to_search_for(self):
        owner=bar.TypeBar
        self.assertEqual(owner.address_of('https://example.org/a b'),'');self.assertEqual(owner.address_of('https://example.org/x'),'https://example.org/x')
        self.assertEqual(owner.address_of('www.example.org'),'https://www.example.org');self.assertEqual(owner.address_of('example.org/page'),'https://example.org/page')
        self.assertEqual(owner.address_of('rail limits rev b'),'');self.assertEqual(owner.address_of('3.36'),'','a number is words, not an address');self.assertEqual(owner.address_of(''),'')
        self.assertEqual({k:bar.MAPPED[k] for k in ('slate','stac','kernel','shell','find','log')},
                         {'slate':'slate','stac':'slate','kernel':'slate','shell':'shell','find':'find','log':'log'},
                         'legacy targets retain their mode and command prefixes')
        self.assertEqual(bar.CONSOLE_PAGE,{'slate':'stac','shell':'shell','find':'find','log':'log'})
        self.assertEqual(bar.JUMPS,{'@':'stac','/':'kernel','?':'find','$':'shell'},'the lead characters keep their meaning')

    def test_destination_hint_names_the_mode(self):
        assistant = bar.destination_hint('slate')
        self.assertTrue(assistant.startswith('Stacy · '));self.assertIn('the arrow runs it',assistant)
        for hint in bar.HINTS.values():
            for key in ('Enter','Ctrl+','Tab ','Esc'):self.assertNotIn(key,hint,'the line names no key')
        self.assertEqual(bar.destination_hint('stac'),assistant)
        self.assertTrue(bar.destination_hint('kernel').startswith('Stacy · an operation by name'))
        self.assertTrue(bar.destination_hint('find').startswith('Search · '));self.assertTrue(bar.destination_hint('log').startswith('Log · '))
        self.assertEqual(bar.destination_hint('shell'),'Terminal · ' + bar.HINTS['shell'])
        self.assertEqual(bar.destination_hint('shell','Terminal','Commands run in /bin/bash'),'Terminal · Commands run in /bin/bash')
        self.assertEqual(bar.destination_hint('log','Log · Network','Filter by host or port'),'Log · Network · Filter by host or port')

    def test_the_remembered_target_and_stream_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'session.json'
            for saved,mode in (('log','log'),('find','find'),('shell','shell'),('kernel','slate'),('stac','slate'),('slate','slate')):
                s=Session(path);s.state.update(type_target=saved,log_stream='network');s.save();again=Session(path)
                self.assertEqual(again.state.get('type_target'),saved);self.assertEqual(bar.MAPPED.get(again.state.get('type_target'),'slate'),mode)
                self.assertEqual(again.state.get('log_stream'),'network')
            s=Session(path);s.state.update(type_target='notes',log_stream='packets');s.save();again=Session(path)
            self.assertNotIn('type_target',again.state);self.assertNotIn('log_stream',again.state)


class ShellWordTests(unittest.TestCase):
    """The Shell mode's word reads Bash only when the configured shell is bash: the account's login shell (the account
    database, what chsh sets), else $SHELL, else /bin/sh; a shell that refuses logins or is not executable is passed over."""

    def test_the_configured_shell_and_its_word(self):
        ok=lambda path:True
        self.assertEqual(bar.configured_shell('/bin/bash',{'SHELL':'/usr/bin/zsh'},ok),'/bin/bash','the login shell first')
        self.assertEqual(bar.configured_shell('/usr/sbin/nologin',{'SHELL':'/usr/bin/zsh'},ok),'/usr/bin/zsh','nologin is passed over')
        self.assertEqual(bar.configured_shell('',{},ok),'/bin/sh')
        self.assertEqual(bar.configured_shell('/bin/fish',{'SHELL':'/bin/bash'},lambda p:p!='/bin/fish'),'/bin/bash','a shell that is not there is passed over')
        self.assertEqual([bar.shell_label(p) for p in ('/bin/bash','/usr/local/bin/bash','/bin/sh','/bin/dash','/usr/bin/zsh','/bin/rbash','')],
                         ['Bash','Bash','Shell','Shell','Shell','Shell','Shell'])

    def test_how_the_shell_runs_a_line(self):
        self.assertEqual(bar.shell_argv('/bin/bash','ls -l'),['/bin/bash','-l','-c','ls -l'])
        self.assertEqual(bar.shell_argv('/usr/bin/zsh','ls'),['/usr/bin/zsh','-l','-c','ls'])
        self.assertEqual(bar.shell_argv('/opt/odd/shell','ls'),['/opt/odd/shell','-c','ls'])


class StacHintTests(unittest.TestCase):
    def test_what_parses_as_stac(self):
        for text in ('files.list','files.list | rows','@files:stock.csv | rows | where Qty over 3','desk'):self.assertTrue(bar.parses_as_stac(text),text)
        for text in ('show me the files','what is files.list','rows','hello | rows','/files.list','?pencil','$ ls','',
                     'language.run','files.write path=x'):self.assertFalse(bar.parses_as_stac(text),text)


class PlaceholderTests(unittest.TestCase):
    def test_the_poem_placeholder_is_legible_on_the_line(self):
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QLabel,QLineEdit,QWidget
        from workbench import desk_qt
        from workbench.text_prompts import writing_prompt

        application = app()
        band = QWidget()
        band.setObjectName('TypeBar')
        band._style_key = None
        band.targets = {}
        band.context = QLabel(band)
        band.box = QLineEdit(band)
        band.box.setObjectName('OneBox')
        writing_prompt(band.box)
        bar.TypeBar.band_style(band,1)
        band.show()
        application.processEvents()

        self.assertEqual(band.box.placeholderText(),'poem')
        palette = band.box.palette()
        background = palette.color(QPalette.Base).getRgb()[:3]
        placeholder = palette.color(QPalette.PlaceholderText).getRgb()[:3]
        typed = palette.color(QPalette.Text).getRgb()[:3]
        self.assertGreaterEqual(desk_qt.contrast(placeholder,background),4.5)
        self.assertLess(desk_qt.contrast(placeholder,background),desk_qt.contrast(typed,background))


class FilterGrammarTests(unittest.TestCase):
    def test_the_grammar(self):
        f=log.parse_filter('host 10.0.0.5 port 443 firefox tcp')
        self.assertEqual((f['hosts'],f['ports'],f['protocols'],f['words'],f['errors']),(['10.0.0.5'],[443],['tcp'],['firefox'],[]))
        f=log.parse_filter('10.0.0.5:8080 :53 udp established proc systemd-resolved example.org 192.168.1.0/24')
        self.assertEqual((f['hosts'],f['names'],f['ports'],f['protocols'],f['states'],f['words']),(['10.0.0.5','192.168.1.0/24'],['example.org'],[8080,53],['udp'],['established'],['systemd-resolved']))
        self.assertEqual(f['errors'],['names are not looked up (Graphite makes no DNS request): example.org; give its address'],'a name is never looked up, and says so')
        self.assertEqual(log.parse_filter('localhost')['hosts'],['127.0.0.1','::1'])
        self.assertEqual(log.parse_filter('port 70000')['errors'],['not a port (1 to 65535): 70000'])
        self.assertEqual(log.parse_filter('99999')['errors'],['not a port (1 to 65535): 99999'])
        self.assertEqual(log.parse_filter('host')['errors'],['“host” needs a word after it'])
        self.assertEqual(log.parse_filter('[::1]:631')['hosts'],['::1']);self.assertEqual(log.parse_filter('[::1]:631')['ports'],[631])

    def test_one_grammar_with_the_capability(self):
        """D3-fix (review of D3): the view had its own grammar and hid rows the capability returned. The view's parse, match
        and capture filter are D5's own (network_watch), word for word, on the review's cases and more."""
        from workbench import network_watch as d5
        rows=[dict(kind='connection',proto='tcp',local='127.0.0.1',lport=631,remote='127.0.0.1',rport=40000,state='ESTABLISHED',process='cupsd',lservice='ipp'),
              dict(kind='connection',proto='tcp',local='192.0.2.10',lport=51000,remote='198.51.100.7',rport=22,state='ESTABLISHED',process='test-client',rservice='ssh'),
              dict(kind='connection',proto='udp6',local='::1',lport=53,remote='::',rport=0,state='UNCONN',process='test-resolver'),
              dict(kind='packet',proto='tcp',src='192.0.2.10',sport=51000,dst='198.51.100.7',dport=22,length=60,flags='S',seq=1,iface='eth0'),
              dict(kind='packet',proto='udp',src='::1',sport=40000,dst='::1',dport=53,length=80,seq=2,iface='lo')]
        for words in ('localhost','ssh','established','tcp established','ipp','host ::1 udp','10.0.0.0/8','example.org','raw','port 22 port 53','lo','proc test'):
            parts=log.parse_filter(words);self.assertEqual(parts,d5.parse_filter(words),words)
            for e in rows:self.assertEqual(log.matches(e,parts),d5.matches(e,parts,packet=e['kind']=='packet'),(words,e))
            self.assertEqual(tuple(log.capture_filter(words)),tuple(d5.bpf(parts)),words)
        m=lambda e,t:log.matches(e,log.parse_filter(t))
        self.assertTrue(m(rows[0],'localhost'),'localhost is 127.0.0.1 and ::1');self.assertTrue(m(rows[1],'ssh'),'a service name');self.assertTrue(m(rows[3],'established'),'a state does not narrow packets')
        self.assertEqual(log.capture_filter('localhost'),('host 127.0.0.1 or host ::1',[]))
        self.assertEqual(log.capture_filter('example.org')[0],'');self.assertIn('names are not looked up',log.capture_filter('example.org')[1][0])
        self.assertIn('not a packet protocol a capture can select',log.capture_filter('raw')[1][0])

    def test_matching_widens_within_a_kind_and_narrows_across(self):
        c=dict(kind='connection',proto='tcp6',local='::1',lport=631,remote='::1',rport=40000,state='ESTABLISHED',process='cupsd')
        p=dict(kind='packet',proto='udp',src='10.0.0.5',sport=51000,dst='10.0.0.1',dport=53,length=74,iface='eth0')
        m=lambda e,t:log.matches(e,log.parse_filter(t))
        self.assertTrue(m(c,'tcp'),'tcp matches tcp6');self.assertTrue(m(c,'port 80 port 631'));self.assertFalse(m(c,'port 80'))
        self.assertTrue(m(c,'cups established'));self.assertFalse(m(c,'cups udp'));self.assertTrue(m(c,''))
        self.assertTrue(m(p,'10.0.0.0/24 53'));self.assertFalse(m(p,'host 10.0.0.9'));self.assertTrue(m(p,'eth0'))

    def test_capture_filter_and_conversation(self):
        self.assertEqual(log.bpf(log.parse_filter('host 10.0.0.5 port 443 tcp firefox')),'host 10.0.0.5 and port 443 and tcp')
        self.assertEqual(log.bpf(log.parse_filter('port 80 port 443 10.0.0.0/8')),'net 10.0.0.0/8 and (port 80 or port 443)')
        self.assertEqual(log.bpf(log.parse_filter('firefox')),'','names are applied when the packets are read')
        self.assertEqual(log.conversation(dict(kind='connection',remote='93.184.216.34',rport=443)),'host 93.184.216.34 port 443')
        self.assertEqual(log.conversation(dict(kind='packet',src='93.184.216.34',sport=443,dst='10.0.0.5',dport=51000)),'host 93.184.216.34 port 443')
        self.assertEqual(log.conversation(dict(kind='connection',remote='0.0.0.0',rport=0)),'')
        self.assertEqual([log.rate(v) for v in (0,999,12300,1.2e6,3.5e9)],['0 bit/s','999 bit/s','12.3 kbit/s','1.20 Mbit/s','3.50 Gbit/s'])

    def test_the_confirmation_says_exactly_what_is_captured(self):
        words=log.confirmation_words('port 443')
        for said in ('headers only','not in promiscuous mode','this computer\'s own interfaces','%d seconds'%log.CAPTURE_SECONDS,'%d packets'%log.CAPTURE_PACKETS,
                     'Nothing leaves the computer','Filter: port 443\nThe capture tool selects: port 443'):self.assertIn(said,words)
        self.assertNotIn('sudo',words.lower())
        # D3-fix: the capture filter is the one the capability gives the tool (localhost is two addresses), and what is
        # applied only as the packets are read is said so
        self.assertIn('The capture tool selects: host 127.0.0.1 or host ::1',log.confirmation_words('localhost'))
        self.assertIn('The capture tool selects every packet',log.confirmation_words('firefox'));self.assertIn('matching firefox',log.confirmation_words('firefox'))
        self.assertIn('narrows the connections, not the packets',log.confirmation_words('tcp established'))
        self.assertIn('Filter: none. Every packet',log.confirmation_words(''))


def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class Fake:
    """A dispatcher standing in for Kernel.dispatch: canned answers per operation, every call recorded."""

    def __init__(self,answers):self.answers=answers;self.calls=[]

    def __call__(self,operation,arguments):
        self.calls.append((operation,dict(arguments)));answer=self.answers.get(operation)
        value=answer(arguments) if callable(answer) else answer
        return {'ok':True,'result':value} if value is not None else {'ok':False,'error':{'message':'Unknown operation'}}


def host_with(state=None):
    from PySide6.QtCore import QObject
    app()
    class Host(QObject):pass
    host=Host();host.session=type('S',(),{'state':dict(state or {}),'save':lambda self:None})();host.root=Path(tempfile.mkdtemp())
    return host


CONNECTIONS=[dict(proto='tcp',local='10.0.0.5',lport=51000,remote='93.184.216.34',rport=443,state='ESTABLISHED',pid=4242,process='firefox',user='owner'),
             dict(proto='udp',local='10.0.0.5',lport=40001,remote='10.0.0.1',rport=53,state='UNCONN',process='systemd-resolved'),
             dict(proto='tcp',local='0.0.0.0',lport=631,remote='0.0.0.0',rport=0,state='LISTEN',process='cupsd')]


def packets(start,count):
    return [dict(seq=start+i,at=1762460000+i/10,iface='eth0',proto='tcp',src='10.0.0.5',sport=51000,dst='93.184.216.34',dport=443,length=60+i,flags='.')
            for i in range(count)]


class LogViewTests(unittest.TestCase):
    def network_fake(self,capture=None):
        state={'capture':dict(capture or {'state':'IDLE'}),'packets':[]}
        def observe(a):return dict(interfaces=[dict(name='eth0',rx_bps=12300,tx_bps=900,rx_bytes=1,tx_bytes=1,up=True),dict(name='lo',rx_bps=0,tx_bps=0,rx_bytes=0,tx_bytes=0,up=True)],
                                   connections=CONNECTIONS,capture=dict(state['capture']),observed_at=1762460000)
        def start(a):state['capture']=dict(state='RUNNING',tool='dumpcap',started=1762460000,packets=0,filter=a.get('filter'));return {'capture':dict(state['capture'])}
        def stop(a):state['capture']=dict(state='IDLE');return {'capture':dict(state['capture'])}
        def read(a):
            after=int(a.get('after') or 0);rows=[p for p in state['packets'] if p['seq']>after]
            return dict(packets=rows,next=str(rows[-1]['seq']) if rows else (a.get('after') or '0'),capture=dict(state['capture']))
        return Fake({'network.observe':observe,'network.capture.start':start,'network.capture.stop':stop,'network.capture.read':read}),state

    def test_the_stream_choice_is_remembered(self):
        host=host_with({'log_stream':'network'});fake,_=self.network_fake();view=log.LogView(host,fake)
        self.assertEqual(view.stream,'network');self.assertTrue(view.tabs['network'].isChecked());self.assertFalse(view.tabs['events'].isChecked())
        view.tabs['events'].click();self.assertEqual(host.session.state['log_stream'],'events')
        self.assertEqual(log.LogView(host_with(),fake).stream,'events','Events when nothing was chosen')

    def test_events_follow_the_journal_with_nothing_to_write(self):
        from PySide6.QtWidgets import QLineEdit,QPlainTextEdit,QTextEdit
        journal=[dict(id='e%d'%i,seq=i,at=1762460000+i,origin='DESKTOP',operation='ledger.view',state='FOCUSED',detail='Page %d'%i) for i in range(1,6)]
        def activity(a):
            after=int(a.get('after') or 0);rows=[e for e in journal if e['seq']>after and (not a.get('query') or a['query'] in e['detail'])]
            return dict(events=rows,cursor=str(journal[-1]['seq']),has_more=False)
        fake=Fake({'ledger.journal.status':lambda a:dict(head=len(journal)),'ledger.activity':activity});view=log.LogView(host_with(),fake)
        view.refresh(force=True)
        self.assertEqual([view.events.item(i).data(0x0100)['id'] for i in range(view.events.count())],['e1','e2','e3','e4','e5'],'newest at the bottom')
        journal.append(dict(id='e6',seq=6,at=1762460006,origin='DESKTOP',operation='ledger.view',state='FOCUSED',detail='Page 6'));view.refresh()
        self.assertEqual(view.events.item(view.events.count()-1).data(0x0100)['id'],'e6','it follows the journal')
        self.assertTrue({op for op,_ in fake.calls}<={'ledger.journal.status','ledger.activity'},fake.calls)
        self.assertEqual([w for kind in (QLineEdit,QPlainTextEdit,QTextEdit) for w in view.findChildren(kind)],[],'no notes: the Log view has nothing to write in')
        self.assertFalse(hasattr(log,'add_note') or hasattr(view,'note_for'),'the notes feature is gone')
        view.apply_filter('Page 2');self.assertEqual([view.events.item(i).data(0x0100)['id'] for i in range(view.events.count())],['e2'])

    def test_the_network_reads_only_through_the_four_operations_and_honours_the_filter(self):
        fake,state=self.network_fake();view=log.LogView(host_with({'log_stream':'network'}),fake)
        view.refresh(force=True)
        self.assertEqual(view.connections.count(),3);self.assertIn('eth0  ↓ 12.3 kbit/s  ↑ 900 bit/s',view.interfaces.text())
        view.apply_filter('firefox 443')
        self.assertEqual([view.connections.item(i).data(0x0100)['process'] for i in range(view.connections.count())],['firefox'])
        self.assertEqual(fake.calls[-1],('network.observe',{'filter':'firefox 443'}),'the owner\'s words go to the capability as typed')
        self.assertTrue({op for op,_ in fake.calls}<=set(log.NETWORK_OPERATIONS),fake.calls)
        with self.assertRaises(ValueError):view.network('files.list',{})
        self.assertEqual(log.NETWORK_OPERATIONS,('network.observe','network.capture.start','network.capture.stop','network.capture.read'))

    def test_the_first_capture_asks_first_and_the_stop_ends_it(self):
        from PySide6.QtWidgets import QMessageBox
        fake,state=self.network_fake();view=log.LogView(host_with({'log_stream':'network'}),fake);view.refresh(force=True)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No) as asked:self.assertIsNone(view.start_capture('port 443'))
        self.assertEqual(asked.call_count,1);self.assertNotIn('network.capture.start',[op for op,_ in fake.calls]);self.assertIn('headers only',asked.call_args[0][2])
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes) as asked:view.start_capture('port 443')
        start=[a for op,a in fake.calls if op=='network.capture.start']
        self.assertEqual(start,[{'filter':'port 443','seconds':log.CAPTURE_SECONDS,'packets':log.CAPTURE_PACKETS}]);self.assertEqual(view.capture['state'],'RUNNING')
        self.assertTrue(view.stop_button.isVisibleTo(view) and not view.start_button.isVisibleTo(view))
        state['packets']=packets(1,3);view.refresh();self.assertEqual(view.packets.count(),3)
        view.stop_capture();self.assertEqual(view.capture['state'],'IDLE')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes) as asked:view.start_capture('port 443')
        self.assertEqual(asked.call_count,0,'asked once a run');self.assertEqual(len([1 for op,_ in fake.calls if op=='network.capture.start']),2)
        self.assertTrue({op for op,_ in fake.calls}<=set(log.NETWORK_OPERATIONS))

    def test_the_pin_holds_while_entries_arrive(self):
        fake,state=self.network_fake({'state':'RUNNING','packets':0});view=log.LogView(host_with({'log_stream':'network'}),fake)
        state['packets']=packets(1,5);view.refresh(force=True);self.assertEqual(view.packets.count(),5)
        chosen=view.packets.item(1);view.chose(chosen);pinned=dict(view.pinned)
        self.assertEqual((pinned['kind'],pinned['seq']),('packet',2));self.assertFalse(view.pin_frame.isHidden())
        state['packets']+=packets(6,400);view.refresh();view.refresh()
        self.assertEqual(view.pinned,pinned);self.assertFalse(view.pin_frame.isHidden());self.assertEqual(view.packets.count(),405)
        self.assertIn('93.184.216.34:443',view.pin_title.text());self.assertIn('sequence 2',view.pin_details.text())
        view.connections.setCurrentRow(0);view.chose(view.connections.item(0));self.assertEqual(view.pinned['kind'],'connection')
        view.refresh(force=True);self.assertEqual((view.pinned['process'],view.pinned['kind']),('firefox','connection'))
        self.assertEqual(log.assignment_text(view.pinned),'About this network connection (tcp 10.0.0.5:51000 → 93.184.216.34:443, ESTABLISHED, firefox pid 4242): ')

    def test_entry_at_names_the_stream_and_kind(self):
        fake,state=self.network_fake({'state':'RUNNING'});view=log.LogView(host_with({'log_stream':'network'}),fake);view.resize(1200,500);view.show()
        state['packets']=packets(1,2);view.refresh(force=True);app().processEvents()
        for widget,kind in ((view.connections,'connection'),(view.packets,'packet')):
            point=widget.visualItemRect(widget.item(0)).center();entry=log.entry_at(widget.viewport(),point)
            self.assertEqual((entry['stream'],entry['kind']),('network',kind))
        self.assertIsNone(log.entry_at(view.interfaces,view.interfaces.rect().center()))
        view.hide()

    def test_the_unavailable_reason_is_shown_and_nothing_is_offered(self):
        from PySide6.QtWidgets import QMessageBox
        reason='No capture tool may capture here: dumpcap is not installed. Install the wireshark-common package and add yourself to the wireshark group.'
        fake,state=self.network_fake({'state':'UNAVAILABLE','reason':reason});view=log.LogView(host_with({'log_stream':'network'}),fake);view.refresh(force=True)
        self.assertEqual(view.capture_note.text(),reason);self.assertEqual(view.capture_words.text(),'Capture unavailable')
        self.assertTrue(view.start_button.isHidden() and view.stop_button.isHidden())
        with patch.object(QMessageBox,'question') as asked:self.assertIsNone(view.start_capture('port 443'))
        self.assertEqual(asked.call_count,0);self.assertNotIn('network.capture.start',[op for op,_ in fake.calls])
        missing=log.LogView(host_with({'log_stream':'network'}),Fake({}));missing.refresh(force=True)
        self.assertIn('not in this build',missing.capture_note.text());self.assertIn('not in this build',missing.summary())
        self.assertNotIn('sudo',(view.capture_note.text()+missing.capture_note.text()+log.confirmation_words('')).lower())

    def test_the_capture_reason_is_never_cut_and_an_empty_packet_list_steps_aside(self):
        """The integration of the desk items (found by the owner's review set): where the lists stand one above the other (a
        narrow window, a large text size), the capture's reason, five lines when capture is unavailable, was given two and cut,
        and an empty packet list took the room. The reason is as tall as its words in its own scroll (up to NOTE_LINES there,
        the rest by scrolling); while capture is unavailable and nothing is shown the packet list steps aside, and packets bring
        it back."""
        reason=' '.join(['No capture tool is installed (Graphite captures through dumpcap or tcpdump).']+['To enable capture on Debian: as the administrator, apt install wireshark-common.']*4)
        fake,state=self.network_fake({'state':'UNAVAILABLE','reason':reason});view=log.LogView(host_with({'log_stream':'network'}),fake)
        from PySide6.QtWidgets import QBoxLayout
        for width in (560,1200):
            view.resize(width,300);view.show();view.refresh(force=True)
            for _ in range(3):app().processEvents()
            note=view.capture_note;stacked=view.lists.direction()==QBoxLayout.TopToBottom
            self.assertEqual(stacked,width==560,width)
            self.assertGreaterEqual(note.height(),note.heightForWidth(note.width()),'the reason is never cut: it scrolls (%d px)'%width)
            self.assertLessEqual(view.note_area.height(),(log.NOTE_LINES if stacked else log.NOTE_LINES_WIDE)*note.fontMetrics().lineSpacing()+2)
            self.assertTrue(view.packets.isHidden(),'no packet can come and none is shown')
        view.add_packets(packets(1,2));app().processEvents()
        self.assertFalse(view.packets.isHidden(),'packets to show bring the list back');view.hide()

    def test_the_view_shows_what_the_capabilitys_grammar_selects(self):
        """D3-fix (review of D3): the view filtered the capability's answer again with a grammar of its own and hid rows the
        capability had returned for the owner's words (localhost, a service name, a state on packets). Here the fake returns
        every row whatever the filter, so the view's own pass decides: it must select exactly what D5's grammar selects. The
        errors the capability reports with its answer are shown with the filter."""
        from workbench import network_watch as d5
        rows=[dict(proto='tcp',local='127.0.0.1',lport=631,remote='127.0.0.1',rport=40000,state='ESTABLISHED',process='cupsd',lservice='ipp'),
              dict(proto='tcp',local='192.0.2.10',lport=51000,remote='198.51.100.7',rport=22,state='ESTABLISHED',process='test-client',rservice='ssh'),
              dict(proto='udp',local='192.0.2.10',lport=40001,remote='192.0.2.1',rport=53,state='UNCONN',process='test-resolver')]
        captured=[dict(seq=1,at=1762460000.0,iface='eth0',proto='tcp',src='192.0.2.10',sport=51000,dst='198.51.100.7',dport=22,length=60,flags='S')]
        def observe(a):return dict(interfaces=[],connections=rows,capture={'state':'IDLE'},observed_at=1,filter={'text':a.get('filter',''),'errors':['TEST: the capability\'s own word']})
        def read(a):return dict(packets=[p for p in captured if p['seq']>int(a.get('after') or 0)],next=str(captured[-1]['seq']),capture={'state':'IDLE'})
        view=log.LogView(host_with({'log_stream':'network'}),Fake({'network.observe':observe,'network.capture.read':read}));view.captured=True
        for words in ('localhost','ssh','established','tcp established','ipp'):
            view.apply_filter(words);parts=d5.parse_filter(words)
            shown=[view.connections.item(i).data(0x0100)['lport'] for i in range(view.connections.count()) if view.connections.item(i).data(0x0100)]
            self.assertEqual(shown,[c['lport'] for c in rows if d5.matches(c,parts)],words)
            packets=[view.packets.item(i).data(0x0100)['seq'] for i in range(view.packets.count()) if view.packets.item(i).data(0x0100)]
            self.assertEqual(packets,[p['seq'] for p in captured if d5.matches(p,parts,packet=True)],words)
        self.assertEqual(shown,[631]);self.assertIn('TEST: the capability\'s own word',view.filter_words.text())
        view.apply_filter('example.org');self.assertIn('names are not looked up',view.filter_words.text());self.assertEqual(view.connections.item(0).data(0x0100),None)

    def test_a_refused_capture_says_why_and_the_words_stay(self):
        """D3-fix (review of D3): when the capability refused a capture the owner had confirmed, its words were overwritten at
        once by the idle note. Words its grammar refuses are said before anything is asked or started; a refusal from the
        capability itself stays shown through the next refreshes, until a capture starts or the filter changes."""
        from PySide6.QtWidgets import QMessageBox
        fake,state=self.network_fake();view=log.LogView(host_with({'log_stream':'network'}),fake);view.refresh(force=True)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes) as asked:self.assertIsNone(view.start_capture('example.org'))
        self.assertEqual(asked.call_count,0,'nothing to confirm: it would capture nothing');self.assertNotIn('network.capture.start',[op for op,_ in fake.calls])
        self.assertEqual(view.capture_words.text(),'Not captured');self.assertIn('names are not looked up (Graphite makes no DNS request): example.org',view.capture_note.text())
        view.refresh();view.refresh();self.assertIn('names are not looked up',view.capture_note.text(),'it stays while the stream refreshes')
        refusals=iter(['NETWORK_CAPTURE_STOPPING: the last capture is still stopping; try again in a moment.'])
        def refused(operation,arguments,original=fake.__call__):
            if operation=='network.capture.start':fake.calls.append((operation,dict(arguments)));return {'ok':False,'error':{'code':'CaptureError','message':next(refusals)}}
            return original(operation,arguments)
        view.dispatch=refused
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):view.start_capture('port 443')
        self.assertEqual(view.capture_words.text(),'Not captured');self.assertEqual(view.capture_note.text(),'the last capture is still stopping; try again in a moment.')
        view.refresh();view.refresh(force=True);self.assertEqual(view.capture_note.text(),'the last capture is still stopping; try again in a moment.')
        view.dispatch=fake
        def not_started(a):return {'capture':{'state':'IDLE'},'started':False,'reason':'TEST: did not start, in the capability\'s words.'}
        fake.answers['network.capture.start']=not_started
        view.start_capture('port 443');self.assertEqual(view.capture_note.text(),'TEST: did not start, in the capability\'s words.')
        fake.answers['network.capture.start']=lambda a:(state.update(capture=dict(state='RUNNING',packets=0)),{'capture':dict(state['capture'])})[1]
        view.start_capture('port 443');self.assertEqual(view.capture['state'],'RUNNING');self.assertIsNone(view.refusal);self.assertNotIn('did not start',view.capture_note.text())

    def test_a_proposed_capture_is_shown_for_the_owner(self):
        """A capture Graphite proposed during an assignment (D5 keeps it; only the owner may start one) is shown while capture
        is idle, in D5's words; nothing starts by itself."""
        words='Graphite proposes capturing packet headers with the filter “port 443” on every interface for 60 seconds (at most 2,000 packets). Only you can start it: Log, Network, type the filter “port 443”, then Capture… (or Ctrl+Enter in the line).'
        fake,state=self.network_fake({'state':'IDLE','proposal':{'filter':'port 443','words':words}});view=log.LogView(host_with({'log_stream':'network'}),fake);view.refresh(force=True)
        self.assertEqual(view.capture_note.text(),words);self.assertEqual(view.capture_words.text(),'Capture idle')
        self.assertNotIn('network.capture.start',[op for op,_ in fake.calls])

    def test_a_captures_last_packets_are_read_when_it_ends(self):
        """D3-fix (review of D3): packets were read only while the view saw the capture running, so those written after the
        last read of a capture that ended on its own bound never appeared. The review's probe, as a test; and a read that
        leaves packets behind (the capability's rest) reads on."""
        from PySide6.QtWidgets import QMessageBox
        fake,state=self.network_fake();view=log.LogView(host_with({'log_stream':'network'}),fake);view.refresh(force=True)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):view.start_capture('')
        state['packets']=packets(1,3);view.refresh();view.refresh();self.assertEqual(view.packets.count(),3)
        state['packets']=packets(1,5);state['capture']={'state':'IDLE','last':{'outcome':'reached 2,000 packets'}}  # it ended on its bound
        view.ticks+=log.OBSERVE_EVERY-1-view.ticks%log.OBSERVE_EVERY  # the next tick observes first, and sees it ended
        for _ in range(4):view.refresh()
        self.assertEqual(view.packets.count(),5,'the last two packets are read once the capture is seen ended');self.assertFalse(view.following)
        reads=len([1 for op,_ in fake.calls if op=='network.capture.read']);view.refresh();view.refresh()
        self.assertEqual(len([1 for op,_ in fake.calls if op=='network.capture.read']),reads,'and then no more reads')
        # paging: the capability returns at most `limit` and counts the rest
        def paged(a):
            after=int(a.get('after') or 0);rows=[p for p in state['packets'] if p['seq']>after];taken=rows[:int(a.get('limit') or 200)]
            return dict(packets=taken,next=str(taken[-1]['seq']) if taken else str(after),rest=len(rows)-len(taken),capture=dict(state['capture']))
        fake.answers['network.capture.read']=paged;state['capture']={'state':'RUNNING'};state['packets']=packets(1,450);view.packet_cursor=None;view.packets.clear()
        view.refresh();self.assertEqual(view.packets.count(),450,'a tick reads on while more remain')



class LineTests(unittest.TestCase):
    """The line's Enter and Ctrl+Enter on a OneBox with a stand-in window: typed staC runs only on Ctrl+Enter, through the staC
    target's own path (shell2.to_console -> the console's run_stac); plain Enter gives the line to Graphite; Search's Enter
    searches the workspace."""

    def setUp(self):
        from PySide6.QtWidgets import QWidget
        from workbench import shell2
        app();self.ran=[];self.asked=[];test=self
        from workbench.console_qt import Console as RealConsole
        class Console:
            mode='stac';size_level=0;pending_approval=None;at=None
            recall=RealConsole.recall  # the console's own history walk
            def __init__(c):c.prompt=type('P',(),{'text':'','setText':lambda p,t:setattr(p,'text',t)})();c.history={};c.host=host
            def set_mode(c,m):c.mode=m
            def open(c,mode=None,focus=True):c.size_level=c.size_level or 1
            def enter(c):test.ran.append((c.mode,c.prompt.text))
        class Host(QWidget):pass
        host=Host();host.type_target='slate';host.console=Console();host.root=Path(tempfile.mkdtemp());host._viewer_recent=[]
        host.session=type('S',(),{'state':{'recent':[]}})();host.shell2=type('Sh',(),{'ask':lambda s,text,about=None:test.asked.append(text)})()
        host.cabinet_page=None
        self.host=host;self.box=shell2.OneBox(host);self.box.setParent(host)
        class Bar:
            target='slate';box=self.box
            def __init__(b):b.host=host;b.console=host.console
            def set_target(b,key,focus=True):b.target=bar.MAPPED[key];host.type_target=b.target
            def log_enter(b):pass
            def refresh_context(b):pass
        Bar.ctrl_enter=bar.TypeBar.ctrl_enter;host.type_bar=Bar()

    def key(self,text,control=False):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.box.setText(text);QTest.keyClick(self.box,Qt.Key_Return,Qt.ControlModifier if control else Qt.NoModifier)

    def test_plain_enter_never_runs_stac(self):
        with patch('workbench.shell2.call',return_value=None):
            for text in ('files.list','@files:stock.csv | rows','show me the files'):
                self.key(text);self.assertEqual(self.ran,[],text)
        self.assertEqual(self.asked,['files.list','@files:stock.csv | rows','show me the files'],'Enter gives the line to Graphite')

    def test_ctrl_enter_runs_typed_stac_through_the_stac_path(self):
        self.key('files.list',control=True);self.key('@files:stock.csv | rows',control=True)
        self.assertEqual(self.ran,[('stac','files.list'),('stac','@files:stock.csv | rows')]);self.assertEqual(self.asked,[])
        self.assertEqual(self.box.text(),'','the line is cleared once it ran')
        self.key('/files.list path=Slate',control=True);self.assertEqual(self.ran[-1],('kernel','files.list path=Slate'),'a / line runs on its page')

    def test_the_arrow_runs_a_line_that_reads_as_stac_and_asks_with_any_other(self):
        """0.5.3: the arrow does what the line's cue says, so typed staC can be run without a key being named anywhere."""
        b=self.host.type_bar;type(b).submit_line=bar.TypeBar.submit_line
        with patch('workbench.shell2.call',return_value=None):
            self.box.setText('files.list');b.context_kind='stac';b.submit_line()
            self.assertEqual(self.ran,[('stac','files.list')]);self.assertEqual(self.asked,[],'a line that reads as staC is run, not asked about')
            self.box.setText('show me the files');b.context_kind='context';b.submit_line()
            self.assertEqual(self.asked,['show me the files']);self.assertEqual(len(self.ran),1,'words go to Stacy')
            self.box.setText('   ');b.context_kind='stac';b.submit_line();self.assertEqual(len(self.ran),1,'an empty line does nothing')

    def test_up_and_down_walk_the_typed_stac_history_in_assistant(self):
        """An empty Assistant line recalls typed staC. A slash recalls operations."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.host.console.history.update(stac=['desk','@files: | rows','library'],kernel=['ops agenda'])
        def keys(*names):
            out=[]
            for name in names:QTest.keyClick(self.box,getattr(Qt,'Key_'+name));out.append(self.box.text())
            return out
        with patch('workbench.shell2.call',return_value=None):
            self.box.clear();self.assertEqual(keys('Up','Up','Up','Up','Down','Down','Down'),['library','@files: | rows','desk','desk','@files: | rows','library',''])
            self.box.clear();self.host.console.at=None;self.box.setText('@');self.assertEqual(keys('Up','Up'),['library','@files: | rows'],'after @ the walk goes on')
            self.box.clear();self.host.console.at=None;self.box.setText('/');self.assertEqual(keys('Up'),['/ops agenda'],'/ walks the operations\' history')
            self.box.setText('show me');QTest.keyClick(self.box,Qt.Key_Up);self.assertEqual(self.box.text(),'show me')
            self.assertIsNone(self.box.history_page('show me'),'typed words keep Up and Down for the results under the line')
            self.host.type_target='find';self.host.type_bar.target='find'
            self.assertEqual(self.box.history_page(''),'find','Search walks its own history, not staC\'s')

    def test_the_line_offers_stac_for_ctrl_enter_and_search_searches(self):
        with patch('workbench.shell2.call',return_value=None):
            rows=self.box.results('files.list');self.assertEqual(rows[0],('section','STAC · THE ARROW RUNS IT',None));self.assertEqual(rows[2][0],'ask')
            self.assertNotIn(('section','STAC · THE ARROW RUNS IT',None),self.box.results('show me the files'))
            self.host.type_target='find';self.host.type_bar.target='find'
            rows=self.box.results('Interface text');self.assertEqual(rows[1][0],'search');self.assertIn(('section','SETTINGS',None),rows)
            self.assertTrue(any(r[0]=='command' and 'reading.ui_pt' in r[1] for r in rows),rows)
            self.key('pencil');self.assertEqual(self.ran,[('find','pencil')],'Enter searches the workspace in the working area')
            self.host.type_target='shell';self.host.type_bar.target='shell';self.assertEqual(self.box.console_page('/usr/bin/env'),'shell','Terminal keeps paths in the shell')
            self.key('?x.txt');self.assertEqual(self.ran[-1],('shell','?x.txt'))


if __name__=='__main__':
    unittest.main()
