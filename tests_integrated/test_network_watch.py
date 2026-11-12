"""The network capability (HATCH DESK D5): observe without privileges, a headers-only capture, and the agent's access.

The owner, 2026-11-06: "Instead of log notes, let's have network. And we should probably add a network traffic scanner or
packet sniffer capability that the agent can inspect." Covered here: the /proc parsers with fixture text (IPv4, IPv6, mapped,
states), the rates, the process mapping on a fake /proc tree, observing that touches no network (an audit hook), the filter and
its capture-filter translator (the grammar accepted, injection refused), the capture's command (argv exactly: no sudo, -p, the
snap length, the bounds), the pcap and pcapng parser with fixture bytes and malformed input, the ring's bound, the capture job
run with a patched tool (Stop capture, Master Stop's jobs.cancel and its work hold end it), the UNAVAILABLE reasons, the four
operations through Kernel.dispatch with their scopes, and the agent's access (the reads offered and free, the start a proposal
the owner approves).

After the review of D5 (D5-fix): a packet's process is never guessed when sockets share a local address and port (a forking
server, SO_REUSEPORT listeners); a refused start keeps the previous capture; a paired phone cannot read the capture's job record;
the capture tools' own words, zones and look-alike digits are refused rather than read as process names; a protocol word means
what the capture filter means (ip is every IPv4 packet); the snap length's truth in the docs; the installer prints the app's own
words for the enable steps.

Nothing here starts a capture or a worker: Kernel.launch is held in every case, network_capture.spawn is replaced by a fake
tool fed fixture bytes, and network_capture.availability is patched wherever a tool must look installed (this container has
neither dumpcap nor tcpdump). Kernel.submit is held too, except where a test is about the owner's start: there the real submit
runs (it queues the job record) while Kernel.launch stays held, so no worker starts.
"""
import ipaddress,json,os,random,socket,stat,struct,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import network_watch as nw,network_capture as nc,engineering_kernel as ek,agent_loop as loop,agent_profiles as profiles
from workbench import profile_network as pn,tool_selection,stacy_control,activity,work_trail
from workbench.engineering_kernel import Kernel,Principal,operator
from workbench.engineering_cli import schemas

DUMPCAP={'state':'AVAILABLE','tool':'dumpcap','path':'/usr/bin/dumpcap','reason':'','enable':[],'signature':'/usr/bin/dumpcap:1:2:100755'}
TCPDUMP={'state':'AVAILABLE','tool':'tcpdump','path':'/usr/sbin/tcpdump','reason':'','enable':[],'signature':'/usr/sbin/tcpdump:1:2:100755'}
MISSING={'state':'UNAVAILABLE','tool':None,'path':None,'reason':'No capture tool is installed (test).','enable':['install it'],'signature':None}
PAYLOAD=b'SECRET-PAYLOAD-WORDS'
ROOT=Path(__file__).resolve().parents[1]
INSTALLER=ROOT/'INSTALL_DEBIAN.sh'                         # module names, so a check of the old behaviour can point them elsewhere
NETWORK_DOC=ROOT/'docs'/'NETWORK_01.md'
DEBIAN_DOC=ROOT/'docs'/'MINIMAL_DEBIAN_INSTALL_01.md'
REFUSED_WORDS=('src','dst','portrange','gateway','ether','broadcast','multicast','less','greater','len','vlan','mpls','inbound','outbound',
               'gre','esp','ah','ospf','pim','vrrp')        # the capture tools' own words: never a process name when typed alone


# ---------------------------------------------------------------------------------------------------------------- the audit hook
NETWORK_EVENTS=('socket.__new__','socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','socket.getnameinfo',
                'socket.sendto','socket.sendmsg','socket.bind','socket.getservbyport','socket.getservbyname','http.client.connect','urllib.Request')
_HEARD=[];_LISTENING=[False]
def _hook(event,args):
    if _LISTENING[0] and event in NETWORK_EVENTS:_HEARD.append(event)
sys.addaudithook(_hook)


# ---------------------------------------------------------------------------------------------------------------- fixtures
def hex4(address,order='little'):
    raw=ipaddress.IPv4Address(address).packed
    return (raw[::-1] if order=='little' else raw).hex().upper()

def hex6(address,order='little'):
    raw=ipaddress.IPv6Address(address).packed
    return b''.join((raw[i:i+4][::-1] if order=='little' else raw[i:i+4]) for i in range(0,16,4)).hex().upper()

def socket_line(n,local,lport,remote,rport,state,uid,inode,six=False):
    enc=hex6 if six else hex4
    return '%4d: %s:%04X %s:%04X %02X 00000000:00000000 00:00000000 00000000 %5d        0 %d 1 0000000000000000 100 0 0 10 0' % (n,enc(local),lport,enc(remote),rport,state,uid,inode)

HEAD='  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode'
DEV='''Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:  1000      10    0    0    0     0          0         0     1000      10    0    0    0     0       0          0
  eth0: %d     200    1    2    0     0          0         0     %d     150    0    3    0     0       0          0
'''
SERVICES='ssh\t\t22/tcp\nhttps\t\t443/tcp\nhttps\t\t443/udp\t\t\t# HTTP/3\ndomain\t\t53/udp\nipp\t\t631/tcp\n'
PASSWD='root:x:0:0:root:/root:/bin/bash\nowner:x:1000:1000:Owner:/home/owner:/bin/bash\nmessagebus:x:105:110::/nonexistent:/usr/sbin/nologin\n'


def fake_tree(base,uid=1000,rx=5000,tx=9000):
    """A /proc, /sys and /etc of a small computer: firefox talks to 93.184.216.34:443, sshd (another user) listens on 22, a
    TIME_WAIT socket no process holds, an IPv6 listener and an IPv4-mapped connection, a UDP socket."""
    proc=Path(base)/'proc';sys_root=Path(base)/'sys';etc=Path(base)/'etc'
    (proc/'net').mkdir(parents=True);etc.mkdir()
    (proc/'net'/'dev').write_text(DEV%(rx,tx))
    (proc/'net'/'tcp').write_text('\n'.join([HEAD,
        socket_line(0,'0.0.0.0',22,'0.0.0.0',0,0x0A,0,111),
        socket_line(1,'192.168.1.20',51000,'93.184.216.34',443,0x01,uid,222),
        socket_line(2,'192.168.1.20',51002,'93.184.216.34',443,0x06,uid,0),
        socket_line(3,'127.0.0.1',631,'0.0.0.0',0,0x0A,uid,333),
        'garbage line that does not read']))
    (proc/'net'/'tcp6').write_text('\n'.join([HEAD,
        socket_line(0,'::',8080,'::',0,0x0A,uid,444,six=True),
        socket_line(1,'::ffff:192.168.1.20',8080,'::ffff:192.168.1.7',40000,0x01,uid,555,six=True)]))
    (proc/'net'/'udp').write_text('\n'.join([HEAD,socket_line(0,'0.0.0.0',5353,'0.0.0.0',0,0x07,uid,666)]))
    (proc/'net'/'fib_trie').write_text('Local:\n  +-- 0.0.0.0/0 3 0 5\n     |-- 192.168.1.20\n        /32 host LOCAL\n     |-- 127.0.0.1\n        /32 host LOCAL\n')
    for pid,name,inodes in ((4242,'firefox',(222,)),(77,'cupsd',(333,)),(88,'python3',(444,555,666))):
        folder=proc/str(pid)/'fd';folder.mkdir(parents=True);(proc/str(pid)/'comm').write_text(name+'\n')
        for n,inode in enumerate(inodes):os.symlink('socket:[%d]'%inode,folder/str(n+3))
        os.symlink('/dev/null',folder/'0')
    (proc/'1').mkdir();(proc/'1'/'fd').write_text('not a folder: this account may not read it')   # sshd's: unreadable
    for name,oper,flags,index in (('lo','unknown','0x9',1),('eth0','up','0x1003',2)):
        f=sys_root/'class'/'net'/name;f.mkdir(parents=True);(f/'operstate').write_text(oper+'\n');(f/'flags').write_text(flags+'\n');(f/'ifindex').write_text(str(index)+'\n')
    (etc/'services').write_text(SERVICES);(etc/'passwd').write_text(PASSWD)
    return str(proc),str(sys_root),str(etc)


def block(kind,body,endian='<'):
    body=body+b'\0'*((-len(body))%4);total=12+len(body)
    return struct.pack(endian+'II',kind,total)+body+struct.pack(endian+'I',total)

def option(code,value,endian='<'):
    return struct.pack(endian+'HH',code,len(value))+value+b'\0'*((-len(value))%4)

def shb(endian='<'):return block(0x0A0D0D0A,struct.pack(endian+'IHHq',0x1A2B3C4D,1,0,-1),endian)
def idb(linktype=1,name=b'eth0',endian='<'):return block(1,struct.pack(endian+'HHI',linktype,0,128)+option(2,name,endian)+option(9,b'\x06',endian)+struct.pack(endian+'HH',0,0),endian)
def epb(data,at_us,iface=0,length=None,endian='<'):
    return block(6,struct.pack(endian+'IIIII',iface,at_us>>32,at_us&0xFFFFFFFF,len(data),length or len(data))+data,endian)

def inet(a):return ipaddress.ip_address(a).packed
def ether(kind,payload,vlan=None):return b'\x02'*6+b'\x04'*6+(struct.pack('!HH',0x8100,vlan) if vlan else b'')+struct.pack('!H',kind)+payload
def ipv4(src,dst,proto,payload,frag=0):return struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(payload),1,frag,64,proto,0,inet(src),inet(dst))+payload
def ipv6(src,dst,nxt,payload,hop=False):
    if hop:payload=struct.pack('!BB6s',nxt,0,b'\0'*6)+payload;nxt=0
    return struct.pack('!IHBB16s16s',0x60000000,len(payload),nxt,64,inet(src),inet(dst))+payload
def tcp(sport,dport,flags,payload=b''):return struct.pack('!HHIIBBHHH',sport,dport,1,0,0x50,flags,65535,0,0)+payload
def udp(sport,dport,payload=b''):return struct.pack('!HHHH',sport,dport,8+len(payload),0)+payload
def arp(spa,tpa):return struct.pack('!HHBBH6s4s6s4s',1,0x0800,6,4,1,b'\x02'*6,inet(spa),b'\0'*6,inet(tpa))
def sll(kind,payload,direction=4):return struct.pack('!HHH8sH',direction,1,6,b'\x02'*6+b'\0\0',kind)+payload
def sll2(kind,index,payload,direction=0):return struct.pack('!HHIHBB8s',kind,0,index,1,direction,6,b'\x02'*6+b'\0\0')+payload

SYN=ether(0x0800,ipv4('192.168.1.20','93.184.216.34',6,tcp(51000,443,0x02,PAYLOAD)))
SYNACK=ether(0x0800,ipv4('93.184.216.34','192.168.1.20',6,tcp(443,51000,0x12)))
PUSH=ether(0x0800,ipv4('192.168.1.20','93.184.216.34',6,tcp(51000,443,0x18,PAYLOAD*4)))
DNS6=ether(0x86DD,ipv6('fe80::1','ff02::fb',17,udp(5353,5353,PAYLOAD),hop=True),vlan=7)
ARP=ether(0x0806,arp('192.168.1.1','192.168.1.20'))

def pcapng(frames,endian='<',name=b'eth0'):
    out=shb(endian)+idb(1,name,endian)
    for n,frame in enumerate(frames):out+=epb(frame,1_794_000_000_000_000+n*1000,endian=endian)
    return out+block(5,struct.pack(endian+'I',0)+b'\0'*12,endian)   # an interface statistics block: nothing to keep

def pcap(frames,linktype=1,endian='<',nano=False):
    magic={('<',False):b'\xd4\xc3\xb2\xa1',('>',False):b'\xa1\xb2\xc3\xd4',('<',True):b'\x4d\x3c\xb2\xa1',('>',True):b'\xa1\xb2\x3c\x4d'}[(endian,nano)]
    out=magic+struct.pack(endian+'HHiIII',2,4,0,0,128,linktype)
    for n,frame in enumerate(frames):out+=struct.pack(endian+'IIII',1_794_000_000+n,(500 if nano else 5)*(n+1),len(frame),len(frame)+40)+frame
    return out


class FakeTool:
    """A capture tool that writes the given bytes (and stays open until stopped when asked to), never a process."""
    instances=[]
    def __init__(self,argv,data=b'',stay_open=False,stderr=b'',code=0):
        self.argv=list(argv);self.code=code;self.stopped=False;self.pid=None
        read,self._write=os.pipe();eread,ewrite=os.pipe()
        if data:os.write(self._write,data)
        if not stay_open:os.close(self._write);self._write=None
        if stderr:os.write(ewrite,stderr)
        os.close(ewrite)
        self.stdout=os.fdopen(read,'rb',buffering=0);self.stderr=os.fdopen(eread,'rb',buffering=0);FakeTool.instances.append(self)
    def poll(self):return None if self._write is not None else self.code
    def _close(self):
        if self._write is not None:os.close(self._write);self._write=None
    def terminate(self):self.stopped=True;self._close()
    def kill(self):self.stopped=True;self._close()
    def wait(self,timeout=None):self._close();return self.code
    @property
    def returncode(self):return self.code


# ---------------------------------------------------------------------------------------------------------------- reading /proc
class ProcParsers(unittest.TestCase):
    def test_addresses_decode_in_host_order_and_mapped_ipv6_reads_plainly(self):
        self.assertEqual(nw.decode_address('0100007F','little'),'127.0.0.1');self.assertEqual(nw.decode_address('7F000001','big'),'127.0.0.1')
        self.assertEqual(nw.decode_address(hex6('::1'),'little'),'::1');self.assertEqual(nw.decode_address(hex6('2001:db8::5','big'),'big'),'2001:db8::5')
        self.assertEqual(nw.decode_address(hex6('::ffff:10.1.2.3'),'little'),'10.1.2.3')   # IPv4-mapped: shown plainly
        with self.assertRaises(ValueError):nw.decode_address('0100')

    def test_sockets_name_their_states_and_skip_what_does_not_read(self):
        with tempfile.TemporaryDirectory() as d:
            proc,_,_=fake_tree(d);text=Path(proc,'net','tcp').read_text()
        rows=nw.parse_sockets(text,'tcp','little')
        self.assertEqual([(r['local'],r['lport'],r['remote'],r['rport'],r['state'],r['inode']) for r in rows],
                         [('0.0.0.0',22,'0.0.0.0',0,'LISTEN',111),('192.168.1.20',51000,'93.184.216.34',443,'ESTABLISHED',222),
                          ('192.168.1.20',51002,'93.184.216.34',443,'TIME_WAIT',0),('127.0.0.1',631,'0.0.0.0',0,'LISTEN',333)])
        udp=nw.parse_sockets(HEAD+'\n'+socket_line(0,'0.0.0.0',53,'0.0.0.0',0,0x07,0,9)+'\n'+socket_line(1,'10.0.0.2',4000,'10.0.0.1',53,0x01,0,10),'udp')
        self.assertEqual([r['state'] for r in udp],['UNCONN','ESTABLISHED'])
        self.assertEqual(nw.parse_sockets(HEAD+'\n'+socket_line(0,'1.2.3.4',1,'5.6.7.8',2,0x0C,0,1),'tcp')[0]['state'],'NEW_SYN_RECV')
        self.assertEqual(nw.parse_sockets(HEAD+'\n'+socket_line(0,'1.2.3.4',1,'5.6.7.8',2,0x0F,0,1),'tcp')[0]['state'],'STATE_0F')

    def test_services_and_passwd_are_parsed_from_their_files(self):
        self.assertEqual(nw.parse_services(SERVICES),{(22,'tcp'):'ssh',(443,'tcp'):'https',(443,'udp'):'https',(53,'udp'):'domain',(631,'tcp'):'ipp'})
        self.assertEqual(nw.parse_passwd(PASSWD),{0:'root',1000:'owner',105:'messagebus'})

    def test_interfaces_rates_come_from_two_looks_and_never_a_sleep(self):
        with tempfile.TemporaryDirectory() as d:
            proc,sys_root,_=fake_tree(d);memory={}
            first,reason=nw.interfaces(proc,sys_root,now=100.0,memory=memory);self.assertIsNone(reason)
            self.assertEqual([(i['name'],i['up'],i['rx_bps']) for i in first],[('lo',True,None),('eth0',True,None)])   # lo: unknown + IFF_UP
            Path(proc,'net','dev').write_text(DEV%(5000+1250,9000+2500))
            second,_=nw.interfaces(proc,sys_root,now=102.0,memory=memory)
            eth0=second[1];self.assertEqual((eth0['rx_bps'],eth0['tx_bps']),(5000.0,10000.0))   # bits per second
            self.assertEqual((eth0['rx_errors'],eth0['rx_drops'],eth0['tx_drops']),(1,2,3))
            Path(proc,'net','dev').write_text(DEV%(10,20))   # a counter reset: no rate rather than a negative one
            third,_=nw.interfaces(proc,sys_root,now=104.0,memory=memory);self.assertIsNone(third[1]['rx_bps'])
        self.assertEqual(nw.rates([{'name':'x','rx_bytes':1,'tx_bytes':1}],5.0,{'x':(5.0,0,0)})[0][0]['rx_bps'],None)   # no time passed

    def test_processes_are_found_from_fd_links_and_others_are_another_user(self):
        with tempfile.TemporaryDirectory() as d:
            proc,sys_root,etc=fake_tree(d)
            rows,notes=nw.connections(proc,etc,'little',uid=1000);local=nw.local_addresses(proc)
        by=lambda lport:next(r for r in rows if r['lport']==lport)
        self.assertEqual((by(51000)['process'],by(51000)['pid'],by(51000)['user'],by(51000)['rservice']),('firefox',4242,'owner','https'))
        self.assertEqual((by(22)['process'],by(22)['user'],by(22).get('pid'),by(22)['lservice']),(nw.ANOTHER_USER,'root',None,'ssh'))   # never guessed
        self.assertNotIn('process',by(51002))                         # TIME_WAIT: no process holds it
        self.assertEqual((by(8080)['proto'],by(8080)['process']),('tcp6','python3'))
        mapped=[r for r in rows if r['lport']==8080 and r['state']=='ESTABLISHED'][0]
        self.assertEqual((mapped['local'],mapped['remote']),('192.168.1.20','192.168.1.7'))   # ::ffff: shown plainly
        self.assertEqual(by(5353)['state'],'UNCONN')
        self.assertTrue(any('another user' in n for n in notes),notes)
        self.assertEqual(rows[0]['state'],'ESTABLISHED')               # conversations first, then listeners, TIME_WAIT last
        self.assertEqual(rows[-1]['state'],'TIME_WAIT')
        self.assertEqual(local,{'192.168.1.20','127.0.0.1'})

    def test_observe_filters_server_side_bounds_and_counts_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            proc,sys_root,etc=fake_tree(d)
            def look(args,limit=nw.CONNECTION_LIMIT):
                with patch.object(nw,'CONNECTION_LIMIT',limit),patch.object(nw,'connections',side_effect=lambda proc_root,etc_root,*a,**k:REAL(proc_root,etc_root,'little',uid=1000)):
                    return nw.observe(None,args,proc_root=proc,sys_root=sys_root,etc=etc,now=50.0,memory={},capture={'state':'IDLE'})
            out=look({'filter':'port 443'})
            self.assertEqual([(c['remote'],c['rport'],c['state']) for c in out['connections']],[('93.184.216.34',443,'ESTABLISHED'),('93.184.216.34',443,'TIME_WAIT')])
            self.assertEqual(out['counts']['connections'],7);self.assertEqual(out['counts']['matched'],2);self.assertEqual(out['rest'],{'connections':0})
            self.assertEqual(look({'filter':'firefox'})['connections'][0]['pid'],4242)
            self.assertEqual([c['lport'] for c in look({'filter':'listen tcp'})['connections']],[22,631,8080])   # kinds narrow; tcp matches tcp6
            self.assertEqual(len(look({'filter':'port 22 port 631'})['connections']),2)                       # one kind widens
            bounded=look({},limit=3);self.assertEqual((len(bounded['connections']),bounded['rest']['connections']),(3,4))
            self.assertEqual(set(out)>={'interfaces','connections','capture','observed_at'},True)
            self.assertEqual(look({'filter':'example.org'})['filter']['errors'],[nw.NO_NAMES%'example.org'])  # a name is never looked up
            self.assertIn('rates appear from the second look',out['notes'])

    def test_observing_touches_no_network(self):
        """No DNS lookup, no request, not even a socket: an audit hook hears every socket the interpreter makes."""
        with tempfile.TemporaryDirectory() as d:
            proc,sys_root,etc=fake_tree(d)
            refuse=lambda *a,**k:(_ for _ in ()).throw(AssertionError('the name service was asked'))
            del _HEARD[:];_LISTENING[0]=True
            try:
                with patch.object(socket,'getservbyport',refuse),patch.object(socket,'gethostbyaddr',refuse),patch.object(socket,'getaddrinfo',refuse):
                    nw.observe(None,{'filter':'firefox example.org'},proc_root=proc,sys_root=sys_root,etc=etc,now=1.0,memory={},capture={'state':'IDLE'})
                    nw.observe(None,{},now=2.0,memory={},capture={'state':'IDLE'})   # this computer's own /proc, /sys and /etc
                    nw.bpf(nw.parse_filter('host 10.0.0.5 port 443 tcp'))
            finally:_LISTENING[0]=False
            self.assertEqual(_HEARD,[])
            socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM).close()   # the hook itself hears a socket when one is made
            _LISTENING[0]=True
            try:socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM).close()
            finally:_LISTENING[0]=False
            self.assertIn('socket.__new__',_HEARD)


REAL=nw.connections


def busy_tree(base):
    """A computer whose sockets share keys: a forking sshd (its listener in pid 1, two children with their own conversations on
    10.0.0.5:22), avahi-daemon and chrome both bound to udp 5353 (SO_REUSEPORT), two nginx workers bound to tcp 80, and two
    programs bound to udp 53 on 10.0.0.5 beside a third bound to udp 53 on every address."""
    proc=Path(base)/'proc';etc=Path(base)/'etc';(proc/'net').mkdir(parents=True);etc.mkdir()
    (proc/'net'/'tcp').write_text('\n'.join([HEAD,
        socket_line(0,'0.0.0.0',22,'0.0.0.0',0,0x0A,1000,10),socket_line(1,'10.0.0.5',22,'1.1.1.1',5000,0x01,1000,11),
        socket_line(2,'10.0.0.5',22,'2.2.2.2',6000,0x01,1000,12),socket_line(3,'0.0.0.0',80,'0.0.0.0',0,0x0A,1000,13),
        socket_line(4,'0.0.0.0',80,'0.0.0.0',0,0x0A,1000,14)]))
    (proc/'net'/'udp').write_text('\n'.join([HEAD,socket_line(0,'0.0.0.0',5353,'0.0.0.0',0,0x07,1000,20),socket_line(1,'0.0.0.0',5353,'0.0.0.0',0,0x07,1000,21),
        socket_line(2,'10.0.0.5',53,'0.0.0.0',0,0x07,1000,30),socket_line(3,'10.0.0.5',53,'0.0.0.0',0,0x07,1000,31),socket_line(4,'0.0.0.0',53,'0.0.0.0',0,0x07,1000,32)]))
    (proc/'net'/'fib_trie').write_text('Local:\n  +-- 0.0.0.0/0 3 0 5\n     |-- 10.0.0.5\n        /32 host LOCAL\n')
    for pid,name,inodes in ((1,'sshd',(10,)),(100,'sshd',(11,)),(200,'sshd',(12,)),(300,'avahi-daemon',(20,)),(400,'chrome',(21,)),
                            (500,'nginx',(13,)),(501,'nginx',(14,)),(600,'dnsmasq',(30,)),(700,'named',(31,)),(800,'systemd-resolve',(32,))):
        folder=proc/str(pid)/'fd';folder.mkdir(parents=True);(proc/str(pid)/'comm').write_text(name+'\n')
        for n,inode in enumerate(inodes):os.symlink('socket:[%d]'%inode,folder/str(n+3))
    (etc/'services').write_text(SERVICES);(etc/'passwd').write_text(PASSWD)
    return str(proc),str(etc)


def packet(proto,src,sport,dst,dport,flags=None):
    return {'proto':proto,'src':src,'sport':sport,'dst':dst,'dport':dport,'flags':flags}


class ProcessNaming(unittest.TestCase):
    """A captured packet's process: by its conversation, then for UDP and a TCP handshake by the socket bound to its port; never
    the first of several programs that share a key."""

    def owners(self,base):
        proc,etc=busy_tree(base)
        owners=nc.Owners(reader=lambda:(REAL(proc,etc,'little',uid=1000)[0],nw.local_addresses(proc)));owners.refresh(force=True)
        return owners

    def test_two_conversations_on_one_local_port_name_their_own_process(self):
        with tempfile.TemporaryDirectory() as d:owners=self.owners(d)
        self.assertEqual(owners.name(packet('tcp','2.2.2.2',6000,'10.0.0.5',22,'P.')),('sshd',200))   # the forking server's second child
        self.assertEqual(owners.name(packet('tcp','10.0.0.5',22,'1.1.1.1',5000,'P.')),('sshd',100))
        self.assertEqual(owners.name(packet('tcp','3.3.3.3',7000,'10.0.0.5',22,'S')),('sshd',1))      # a new connection: its listener
        self.assertIsNone(owners.name(packet('tcp','3.3.3.3',7000,'10.0.0.5',22,'P.')))              # data of a conversation the table does not know

    def test_programs_sharing_a_port_leave_the_packet_without_a_process(self):
        with tempfile.TemporaryDirectory() as d:owners=self.owners(d)
        self.assertIsNone(owners.name(packet('udp','10.0.0.5',5353,'224.0.0.251',5353)))   # avahi-daemon and chrome both hold udp 5353
        self.assertIsNone(owners.name(packet('udp','192.168.9.9',4000,'10.0.0.5',5353)))
        self.assertIsNone(owners.name(packet('udp','192.168.9.9',4000,'10.0.0.5',53)))     # two programs on 10.0.0.5:53: never the one on every address
        self.assertEqual(owners.name(packet('udp','192.168.9.9',4000,'127.0.0.1',53)),('systemd-resolve',800))
        self.assertEqual(owners.name(packet('tcp','4.4.4.4',9000,'10.0.0.5',80,'S')),('nginx',None))   # one program, two processes: no pid
        recorder=nc.Recorder(Path(d)/'none.tsv',1)
        kept=recorder.add(dict(packet('tcp','4.4.4.4',9000,'10.0.0.5',80,'S'),at=0.0,iface='any',length=60,process='nginx',pid=None))
        self.assertEqual((kept['process'],'pid' in kept),('nginx',False))

    def test_the_index_keeps_every_level_apart(self):
        rows=[{'proto':'tcp','local':'127.0.0.1','lport':40000,'remote':'127.0.0.1','rport':631,'process':'cups-browsed','pid':7},
              {'proto':'tcp','local':'127.0.0.1','lport':631,'remote':'127.0.0.1','rport':40000,'process':'cupsd','pid':8},
              {'proto':'udp6','local':'::','lport':5353,'remote':'::','rport':0,'process':nw.ANOTHER_USER},
              {'proto':'udp','local':'0.0.0.0','lport':5353,'remote':'0.0.0.0','rport':0,'process':'chrome','pid':400},
              {'proto':'tcp','local':'0.0.0.0','lport':22,'remote':'0.0.0.0','rport':0,'state':'TIME_WAIT'}]   # no process: not indexed
        index=nw.owner_index(rows)
        self.assertEqual(index['pair'][('tcp','127.0.0.1',40000,'127.0.0.1',631)],('cups-browsed',7))
        self.assertIs(index['wild'][('udp',5353)],nw.AMBIGUOUS)                       # another user's program and chrome
        self.assertNotIn(('tcp',22),index['wild'])
        self.assertEqual(nw.attribute(packet('tcp','127.0.0.1',40000,'127.0.0.1',631,'P.'),index),('cups-browsed',7))   # both ends here: the sender
        self.assertEqual(nw.attribute(packet('tcp','127.0.0.1',631,'127.0.0.1',40000,'P.'),index),('cupsd',8))
        self.assertIsNone(nw.attribute(packet('udp','127.0.0.1',5353,'224.0.0.251',5353),index))
        self.assertIsNone(nw.attribute(packet('icmp','127.0.0.1',None,'127.0.0.1',None),index))


# ---------------------------------------------------------------------------------------------------------------- the filter
class FilterGrammar(unittest.TestCase):
    def expression(self,text):
        parts=nw.parse_filter(text);self.assertEqual(parts['errors'],[],text);return nw.bpf(parts)[0]

    def test_the_grammar_becomes_a_capture_filter_of_canonical_words(self):
        for text,expression in (('','') ,('host 10.0.0.5','host 10.0.0.5'),('10.0.0.5','host 10.0.0.5'),('10.0.0.0/24','net 10.0.0.0/24'),
                                ('10.0.0.7/24','net 10.0.0.0/24'),('port 443','port 443'),('443',"port 443"),(':443','port 443'),
                                ('10.0.0.5:443','host 10.0.0.5 and port 443'),('[::1]:22','host ::1 and port 22'),
                                ('port 80 port 443','port 80 or port 443'),('host 10.0.0.5 port 443 tcp','host 10.0.0.5 and port 443 and tcp'),
                                ('tcp6','ip6 and tcp'),('udp tcp6 port 53','port 53 and (udp or (ip6 and tcp))'),
                                ('localhost','host 127.0.0.1 or host ::1'),('host 10.0.0.1 host 10.0.0.2 udp','(host 10.0.0.1 or host 10.0.0.2) and udp'),
                                ('2001:DB8::1','host 2001:db8::1'),('firefox','') ,('proc firefox port 443 established','port 443'),('ICMP','icmp'),('arp','arp')):
            self.assertEqual(self.expression(text),expression,text)
            self.assertRegex(expression,r'^[a-z0-9 .:/()]*$')
        parts=nw.parse_filter('proc firefox user owner state listen tcp')
        self.assertEqual((parts['words'],parts['states'],parts['protocols']),(['firefox','owner'],['listen'],['tcp']))

    def test_anything_outside_the_grammar_is_refused_with_words(self):
        for text in ('port 443; rm -rf /','$(reboot)','`id`','tcp and udp','not port 22','port 22 or port 80','"quoted"','(host 1.2.3.4)','port 99999',
                     'port 0','host evil;host','proc a|b','host 1.2.3.4 && reboot','!tcp','port','host','10.0.0.5:99999','x'*400,
                     ' '.join(['tcp']*40),'state flying','proto gopher','host 300.1.1.1/40','-w /tmp/x','--relinquish-privileges=root','example.org'):
            parts=nw.parse_filter(text)
            self.assertTrue(parts['errors'],text)
        self.assertEqual(nw.bpf(nw.parse_filter('port 22\nport 80\t'))[0],'port 22 or port 80')   # any white space is a space
        self.assertEqual(nw.bpf(nw.parse_filter('raw'))[1],['“raw” is a kind of socket, not a packet protocol a capture can select'])
        for text in ('port 443; rm -rf /','$(reboot)','`id`','-w /tmp/x','--relinquish-privileges=root'):
            self.assertRegex(nw.bpf(nw.parse_filter(text))[0],r'^[a-z0-9 .:/()]*$',text)   # even the parts that read are canonical

    def test_matching_follows_the_same_words_for_connections_and_packets(self):
        parts=nw.parse_filter('host 10.0.0.0/8 port 443 tcp')
        self.assertTrue(nw.matches({'proto':'tcp6','local':'10.1.1.1','lport':5000,'remote':'1.1.1.1','rport':443},parts))
        self.assertFalse(nw.matches({'proto':'udp','local':'10.1.1.1','lport':5000,'remote':'1.1.1.1','rport':443},parts))
        self.assertTrue(nw.matches({'proto':'tcp','src':'1.1.1.1','sport':443,'dst':'10.2.2.2','dport':6000},parts,packet=True))
        self.assertTrue(nw.matches({'proto':'tcp','src':'1.1.1.1','sport':443,'dst':'10.2.2.2','dport':6000},nw.parse_filter('listen'),packet=True))  # states do not narrow packets
        self.assertFalse(nw.matches({'proto':'tcp','local':'1.1.1.1','remote':'2.2.2.2'},nw.parse_filter('example.org')))   # a name matches no address

    def test_capture_words_zones_and_look_alikes_are_refused_never_read_as_names(self):
        for text in ('fe80::1%eth0','fe80::1%$(reboot)','host fe80::1%eth0','[fe80::1%eth0]:22','fe80::1%;id','portrange 1-2','dst 10.0.0.5','src port 22',
                     'gateway 1.2.3.4','broadcast','multicast tcp','less 100','greater 10','len 64','vlan 7','mpls','inbound','outbound','gre','esp','ah',
                     'port ٤٤٣','１２３','١٢','1.2.3','01.2.3.4','10.0.0','port 22 ２２'):
            parts=nw.parse_filter(text)
            self.assertTrue(parts['errors'],text)
            self.assertFalse(set(parts['words'])&set(REFUSED_WORDS),text)   # never a process name, so never dropped from a capture
        self.assertIn('zone',nw.parse_filter('fe80::1%eth0')['errors'][0]);self.assertIn('either end',nw.parse_filter('dst 10.0.0.5')['errors'][0])
        self.assertEqual(nw.parse_filter('proc less')['words'],['less'])     # after proc a word is a name, whatever it is
        self.assertEqual(self.expression('net 10.0.0.0/24'),'net 10.0.0.0/24');self.assertEqual(self.expression('net 10.0.0.5 port 22'),'host 10.0.0.5 and port 22')

    def test_whatever_is_typed_reads_whole_or_is_refused(self):
        """A seeded fuzz: a filter without errors never makes bpf raise, writes only canonical hosts and a safe expression, and
        reads none of the capture tools' own words as a process name."""
        rng=random.Random(5)
        pieces=('10.0.0.5','fe80::1','%eth0','%','$(reboot)','port','443','٤٤٣','１','1.2.3','dst','src','net','host','proc','less','gre','tcp',
                'ip','ip6','listen','firefox',':22','[::1]:22','/24','-w','portrange','1-2',';','0','99999','localhost','example.org','user','root','gateway','::ffff:1.2.3.4')
        for _ in range(4000):
            text=' '.join(rng.choice(pieces)+(rng.choice(pieces) if rng.random()<0.3 else '') for _ in range(rng.randint(1,5)))
            parts=nw.parse_filter(text)
            if parts['errors']:continue
            expression,_=nw.bpf(parts)
            self.assertRegex(expression,r'^[a-z0-9 .:/()]*$',text)
            for h in parts['hosts']:self.assertRegex(h,r'^[0-9a-f.:/]+$',text)
            tokens=text.split();bare={t.lower() for i,t in enumerate(tokens) if i==0 or tokens[i-1].lower() not in ('proc','process','user')}
            self.assertFalse(bare&set(REFUSED_WORDS),text)

    def test_a_protocol_word_means_what_the_capture_filter_means(self):
        """Each word against decoded fixture packets: exactly the packets the capture filter (pcap-filter) selects for it."""
        frames={'tcp4':SYN,'udp4':ether(0x0800,ipv4('10.0.0.1','10.0.0.2',17,udp(1,2))),'icmp4':ether(0x0800,ipv4('10.0.0.1','10.0.0.2',1,b'\x08\0'+b'\0'*6)),
                'igmp4':ether(0x0800,ipv4('10.0.0.1','224.0.0.1',2,b'\x11'+b'\0'*7)),'sctp4':ether(0x0800,ipv4('10.0.0.1','10.0.0.2',132,struct.pack('!HH',1,2)+b'\0'*8)),
                'tcp6':ether(0x86DD,ipv6('2001:db8::1','2001:db8::2',6,tcp(1,2,0x02))),'udp6':ether(0x86DD,ipv6('2001:db8::1','2001:db8::2',17,udp(1,2))),
                'icmp6':ether(0x86DD,ipv6('2001:db8::1','2001:db8::2',58,b'\x80\0'+b'\0'*6)),'arp':ARP}
        packets={name:nw.decode({'linktype':1,'data':data,'at':0.0,'length':len(data)}) for name,data in frames.items()}
        meaning={'ip':{'tcp4','udp4','icmp4','igmp4','sctp4'},'ip6':{'tcp6','udp6','icmp6'},'tcp':{'tcp4','tcp6'},'udp':{'udp4','udp6'},
                 'tcp6':{'tcp6'},'udp6':{'udp6'},'icmp':{'icmp4'},'icmp6':{'icmp6'},'arp':{'arp'},'sctp':{'sctp4'},'igmp':{'igmp4'}}
        self.assertEqual(set(meaning),set(nw.BPF_PROTOCOLS))
        for word,selected in meaning.items():
            self.assertEqual({n for n,p in packets.items() if nw.matches(p,nw.parse_filter(word),packet=True)},selected,word)
        # connections by the same meaning: an IPv4-mapped tcp6 socket travels in IPv4, a tcp6 listener on :: in IPv6
        mapped={'proto':'tcp6','local':'192.168.1.20','lport':8080,'remote':'192.168.1.7','rport':40000,'state':'ESTABLISHED'}
        listener={'proto':'tcp6','local':'::','lport':8080,'remote':'::','rport':0,'state':'LISTEN'}
        self.assertEqual([[nw.matches(c,nw.parse_filter(w)) for w in ('ip','ip6','tcp','tcp6')] for c in (mapped,listener)],
                         [[True,False,True,False],[False,True,True,True]])


# ---------------------------------------------------------------------------------------------------------------- the capture bytes
class CaptureBytes(unittest.TestCase):
    def frames(self,stream,chunk=None):
        reader=nw.CaptureReader();out=[]
        if chunk:
            for i in range(0,len(stream),chunk):out+=reader.feed(stream[i:i+chunk])
        else:out=reader.feed(stream)
        return reader,out

    def test_pcapng_fed_whole_or_in_pieces_gives_the_same_header_summaries(self):
        stream=pcapng([SYN,SYNACK,DNS6,ARP])
        reader,whole=self.frames(stream);_,pieces=self.frames(stream,chunk=7)
        self.assertEqual([f['data'] for f in whole],[f['data'] for f in pieces])
        rows=[nw.decode(f,None,reader.interface_name(f['iface'])) for f in whole]
        self.assertEqual([(r['iface'],r['proto'],r['src'],r['sport'],r['dst'],r['dport'],r.get('flags')) for r in rows],
                         [('eth0','tcp','192.168.1.20',51000,'93.184.216.34',443,'S'),('eth0','tcp','93.184.216.34',443,'192.168.1.20',51000,'S.'),
                          ('eth0','udp6','fe80::1',5353,'ff02::fb',5353,None),('eth0','arp','192.168.1.1',None,'192.168.1.20',None,None)])
        self.assertAlmostEqual(rows[0]['at'],1_794_000_000.0,places=3);self.assertEqual(rows[0]['length'],len(SYN))
        self.assertNotIn(PAYLOAD.decode(),json.dumps(rows))   # header fields only: what packets carry is never kept
        _,big=self.frames(pcapng([SYN],endian='>'));self.assertEqual(nw.decode(big[0])['dport'],443)

    def test_pcap_from_tcpdump_little_big_micro_nano_and_the_cooked_headers(self):
        rows=[nw.decode(f,None,'any') for f in self.frames(pcap([sll(0x0800,ipv4('10.0.0.2','10.0.0.1',17,udp(4000,53)),direction=4)],linktype=113))[1]]
        self.assertEqual((rows[0]['proto'],rows[0]['dport'],rows[0]['direction'],rows[0]['iface'],rows[0]['length']),('udp',53,'out','any',rows[0]['length']))
        rows=[nw.decode(f,{2:'eth0'},'any') for f in self.frames(pcap([sll2(0x0800,2,ipv4('10.0.0.1','10.0.0.2',6,tcp(22,5000,0x18)))],linktype=276,endian='>',nano=True))[1]]
        self.assertEqual((rows[0]['iface'],rows[0]['flags'],rows[0]['sport']),('eth0','P.',22))
        self.assertAlmostEqual(rows[0]['at'],1_794_000_000+500e-9,places=6)
        rows=[nw.decode(f) for f in self.frames(pcap([ipv4('10.0.0.1','10.0.0.2',1,b'\x08\0'+b'\0'*6),ipv6('::1','::1',58,b'\x80\0'+b'\0'*6)],linktype=101))[1]]
        self.assertEqual([r['proto'] for r in rows],['icmp','icmp6'])
        frag=nw.decode({'linktype':101,'data':ipv4('10.0.0.1','10.0.0.2',6,tcp(1,2,2),frag=0x0010),'at':0.0,'length':40})
        self.assertEqual((frag['proto'],frag['sport']),('tcp',None))   # a later fragment carries no ports
        vlan=nw.decode({'linktype':1,'data':ether(0x0800,ipv4('10.0.0.1','10.0.0.2',17,udp(1,2)),vlan=9),'at':0.0,'length':0})
        self.assertEqual(vlan['dport'],2)

    def test_the_snap_length_passes_the_start_of_what_packets_carry_and_only_header_fields_are_kept(self):
        """-s 128 is not a payload cut: after short headers the first bytes of what a packet carries reach the worker (74 for TCP
        over IPv4 on Ethernet, 86 for UDP). The parser reads past them; the docs say exactly that."""
        tcp_frame=ether(0x0800,ipv4('10.0.0.1','10.0.0.2',6,tcp(1,2,0x18,PAYLOAD*8)))[:nc.SNAP]
        udp_frame=ether(0x0800,ipv4('10.0.0.1','10.0.0.2',17,udp(1,2,PAYLOAD*8)))[:nc.SNAP]
        self.assertEqual((len(tcp_frame)-54,len(udp_frame)-42),(nc.SNAP-54,nc.SNAP-42));self.assertEqual((nc.SNAP-54,nc.SNAP-42),(74,86))
        _,frames=self.frames(pcap([tcp_frame,udp_frame]))
        self.assertIn(PAYLOAD,frames[0]['data']);self.assertIn(PAYLOAD,frames[1]['data'])   # it does reach the worker
        self.assertNotIn(PAYLOAD.decode(),json.dumps([nw.decode(f) for f in frames]))         # and is never in a summary
        doc=' '.join(NETWORK_DOC.read_text().split());debian=' '.join(DEBIAN_DOC.read_text().split())
        self.assertNotIn('payload contents are cut off',doc);self.assertNotIn("captures only this computer's own traffic",doc)
        self.assertIn('%d bytes for TCP over IPv4 on Ethernet (%d - 14 - 20 - 20), %d for UDP (%d - 14 - 20 - 8)'%(nc.SNAP-54,nc.SNAP,nc.SNAP-42,nc.SNAP),doc)
        self.assertNotIn('packet headers only, at most 128 bytes of each packet reach Graphite',debian)

    def test_malformed_input_is_refused_with_words_and_short_input_waits(self):
        for stream in (b'GARBAGE!',b'\x0a\x0d\x0d\x0a'+b'\x1c\0\0\0'+b'\x00\x00\x00\x00'+b'\0'*16,   # no byte-order mark
                       shb()+struct.pack('<II',1,13)+b'\0'*5,                                         # a length that is not whole words
                       shb()+struct.pack('<II',1,20)+struct.pack('<HHI',1,0,128)+struct.pack('<I',24),   # the two lengths differ
                       shb()+epb(SYN,1),                                                              # a packet of an undescribed interface
                       shb()+struct.pack('<II',6,nw.MAX_BLOCK+4)+b'\0'*4,                            # a block larger than any capture's
                       b'\xd4\xc3\xb2\xa1'+struct.pack('<HHiIII',3,0,0,0,128,1),                     # pcap version 3
                       pcap([])+struct.pack('<IIII',1,0,nw.MAX_BLOCK+1,0),                            # a record that claims too much
                       pcap([])+struct.pack('<IIII',1,2_000_000,4,4)+b'abcd'):                        # an impossible time
            with self.assertRaises(nw.MalformedCapture,msg=stream[:24]):nw.CaptureReader().feed(stream)
        reader=nw.CaptureReader();self.assertEqual(reader.feed((shb()+idb()+epb(SYN,1))[:-3]),[])   # incomplete: waits for the rest
        self.assertEqual(len(reader.feed((shb()+idb()+epb(SYN,1))[-3:])),1)
        damaged=nw.decode({'linktype':1,'data':SYN[:20],'at':0.0,'length':60})
        self.assertIn(damaged['proto'],('ip','damaged'));self.assertIsNone(damaged['src'])


# ---------------------------------------------------------------------------------------------------------------- availability
class Availability(unittest.TestCase):
    def probe(self,installed,**kw):
        with tempfile.TemporaryDirectory() as d:
            etc=Path(d);(etc/'passwd').write_text(PASSWD);(etc/'group').write_text(kw.pop('group','wireshark:x:131:\n'))
            return nw.probe(path_text='/nowhere',euid=kw.pop('euid',1000),groups=kw.pop('groups',[1000]),etc=str(etc),
                            exists=lambda p:os.path.basename(p) in installed and p.startswith('/usr/'),
                            access=kw.pop('access',lambda p,m:True),getxattr=kw.pop('getxattr',lambda p:b''),
                            stat=lambda p:os.stat_result((kw.get('mode',0o100755),1,1,1,0,0,1000,1,2,3)))

    def test_every_reason_is_plain_words_with_the_debian_steps_and_no_sudo(self):
        none=self.probe(())
        self.assertEqual((none['state'],none['tool']),('UNAVAILABLE',None))
        for words in ('wireshark-common','answer Yes','usermod -aG wireshark owner','log out and in again','Graphite only explains'):self.assertIn(words,none['reason'])
        late=self.probe(('dumpcap',),access=lambda p,m:False,group='wireshark:x:131:owner\n')
        self.assertEqual(late['enable'],[nw.RELOG]);self.assertIn('started before you joined it',late['reason'])
        outside=self.probe(('dumpcap',),access=lambda p,m:False)
        self.assertEqual(outside['enable'],['as the administrator, usermod -aG wireshark owner',nw.RELOG])
        no_caps=self.probe(('dumpcap',))
        self.assertIn('dpkg-reconfigure wireshark-common',no_caps['reason']);self.assertEqual(no_caps['enable'][0],nw.RECONFIGURE)
        tcpdump=self.probe(('tcpdump',))
        self.assertEqual(tcpdump['tool'],'tcpdump');self.assertIn('setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump',tcpdump['reason'])
        for found in (none,late,outside,no_caps,tcpdump):
            self.assertEqual(found['state'],'UNAVAILABLE');self.assertNotIn('sudo',found['reason'].lower())
            self.assertIn(nw.NEVER,found['reason'])

    def test_a_tool_with_capture_capabilities_or_the_administrator_is_available(self):
        v2=struct.pack('<IIIII',0x02000000|1,(1<<nw.CAP_NET_RAW)|(1<<nw.CAP_NET_ADMIN),0,0,0)
        self.assertEqual(nw.file_capabilities(v2)&(1<<nw.CAP_NET_RAW),1<<nw.CAP_NET_RAW)
        found=self.probe(('dumpcap','tcpdump'),getxattr=lambda p:v2 if p.endswith('dumpcap') else b'')
        self.assertEqual((found['state'],found['tool'],found['path']),('AVAILABLE','dumpcap','/usr/bin/dumpcap'))
        self.assertEqual(self.probe(('tcpdump',),euid=0)['state'],'AVAILABLE')
        self.assertEqual(nw.file_capabilities(b''),0);self.assertEqual(nw.file_capabilities(b'\0'*4),0)


# ---------------------------------------------------------------------------------------------------------------- the Kernel
class Workspace(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='graphite-network-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.launched=[]
        guard=patch.object(Kernel,'launch',side_effect=lambda ident:self.launched.append(ident));guard.start();self.addCleanup(guard.stop)
        self.submitted=[];real=Kernel.submit
        def submit(kernel,a,p):
            if not self.allow_submit:raise AssertionError('no job may be submitted here')
            self.submitted.append(dict(a));return real(kernel,a,p)
        self.allow_submit=False
        held=patch.object(Kernel,'submit',autospec=True,side_effect=submit);held.start();self.addCleanup(held.stop)
        spawn=patch.object(nc,'spawn',side_effect=AssertionError('no capture tool may start here'));spawn.start();self.addCleanup(spawn.stop)
        from workbench import clip
        provider=patch.object(clip,'_request',side_effect=AssertionError('no provider request'));provider.start();self.addCleanup(provider.stop)
        FakeTool.instances.clear()

    def call(self,op,args=None,principal=None):
        return self.kernel.dispatch(op,args or {},principal or self.owner)

    def ok(self,op,args=None,principal=None):
        r=self.call(op,args,principal);self.assertTrue(r['ok'],r);return r['result']

    def start_capture(self,args=None,found=DUMPCAP):
        self.allow_submit=True
        try:
            with patch.object(nc,'availability',return_value=found):return self.ok('network.capture.start',args or {})
        finally:self.allow_submit=False

    def run_capture(self,ident,tool,found=DUMPCAP):
        with patch.object(nc,'availability',return_value=found),patch.object(nc,'spawn',side_effect=tool) as spawned,\
             patch.object(nc.Owners,'refresh',lambda self,force=False:None):
            self.kernel.run_job(ident)
        return spawned


class KernelRegistration(Workspace):
    def test_four_operations_with_their_scopes_and_one_job_tool(self):
        self.assertEqual({op:ek.CAPABILITIES[op] for op in ek.CAPABILITIES if op.startswith('network.')},
                         {'network.observe':'read','network.capture.start':'execute','network.capture.stop':'execute','network.capture.read':'read'})
        self.assertEqual(ek.TOOLS['network.capture'],('workbench.network_capture','run'))
        self.assertIn('network.capture',ek.Principal('x').tools)
        definitions=schemas()
        self.assertEqual(set(definitions['network.capture.start']['properties']),{'filter','interface','seconds','packets'})
        self.assertEqual(set(definitions['network.capture.read']['properties']),{'after','filter','limit'})
        self.assertTrue({'network.observe','network.capture.read'}<=activity.OBSERVER_OPERATIONS)
        self.assertFalse({'network.capture.start','network.capture.stop'}&activity.OBSERVER_OPERATIONS)
        from workbench.stacy_foundation import handler_map
        self.assertEqual({handler_map()[op]['path'] for op in nw.FIELDS},{'workbench/network_watch.py'})

    def test_scopes_hold_through_the_one_dispatcher(self):
        reader=Principal('owner',frozenset({'read'}))
        with patch.object(nc,'availability',return_value=MISSING):
            self.assertTrue(self.call('network.observe',{},reader)['ok'])
            self.assertTrue(self.call('network.capture.read',{},reader)['ok'])
            for op in ('network.capture.start','network.capture.stop'):
                r=self.call(op,{},reader);self.assertFalse(r['ok']);self.assertIn('outside the authorized mode/scope',r['error']['message'])
            tutor=Principal('owner',frozenset({'read','execute','approve'}),mode='Tutor')
            self.assertIn('outside the authorized',self.call('network.capture.start',{},tutor)['error']['message'])
            self.assertIn('Unknown or missing parameters',self.call('network.observe',{'host':'x'})['error']['message'])
            self.assertFalse(self.call('network.capture.start',{'seconds':100000})['ok'])
            self.assertFalse(self.call('network.capture.start',{'interface':'-w'})['ok'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])

    def test_observe_reads_this_computer_and_reading_is_not_an_event(self):
        with patch.object(nc,'availability',return_value=MISSING):
            out=self.ok('network.observe',{'filter':'tcp'})
        self.assertEqual(out['capture']['state'],'UNAVAILABLE');self.assertIn('interfaces',out);self.assertIn('observed_at',out)
        with self.kernel.db() as db:
            audited=db.execute("SELECT count(*) FROM audit WHERE operation LIKE 'network.%'").fetchone()[0]
        self.assertEqual(audited,0)

    def test_the_cloud_never_sees_the_network(self):
        cloud=Principal('desktop-owner',frozenset({'read','execute'}))
        for op in ('network.observe','network.capture.read'):
            with self.assertRaises(ValueError):stacy_control.validate_actions([{'operation':op,'arguments':{}}],cloud,provider=True)
        stacy_control.validate_actions([{'operation':'network.observe','arguments':{}}],cloud,provider=True,private_local=True)   # the local model may read


class Capture(Workspace):
    def test_the_owner_starts_a_capture_as_a_tracked_job_and_nothing_else_starts(self):
        out=self.start_capture({'filter':'port 443 firefox','seconds':60,'packets':2000})
        capture=out['capture']
        self.assertEqual((capture['state'],capture['tool'],capture['packets'],capture['filter'],capture['expression']),('RUNNING','dumpcap',0,'port 443 firefox','port 443'))
        self.assertTrue(isinstance(capture['started'],float));self.assertEqual(len(self.launched),1)
        job=self.kernel.record('jobs',self.launched[0]);plan=job['request_spec']['network']
        self.assertEqual((job['tool'],job['state'],job['timeout']),('network.capture','Queued',60+nc.MARGIN))
        self.assertEqual((plan['bpf'],plan['seconds'],plan['packets'],plan['snap'],plan['interface']),('port 443',60,2000,128,'any'))
        self.assertEqual(self.submitted[0]['request_key'],'network-capture:'+plan['plan'])
        with patch.object(nc,'availability',return_value=DUMPCAP):
            self.assertEqual(self.ok('network.observe')['capture']['state'],'RUNNING')
            again=self.ok('network.capture.start',{})            # one capture at a time: the running one is answered
        self.assertFalse(again['started']);self.assertEqual(len(self.launched),1)

    def test_the_command_is_exactly_as_designed(self):
        plan={'tool':'dumpcap','path':'/usr/bin/dumpcap','interface':'any','seconds':60,'packets':2000,'bpf':'host 10.0.0.5 and port 443'}
        self.assertEqual(nc.command(plan),['/usr/bin/dumpcap','-q','-i','any','-p','-s','128','-c','2000','-a','duration:60','-f','host 10.0.0.5 and port 443','-w','-'])
        self.assertEqual(nc.command(dict(plan,bpf='')),['/usr/bin/dumpcap','-q','-i','any','-p','-s','128','-c','2000','-a','duration:60','-w','-'])
        self.assertEqual(nc.command(dict(plan,tool='tcpdump',path='/usr/sbin/tcpdump',interface='eth0')),
                         ['/usr/sbin/tcpdump','-i','eth0','-p','-n','-s','128','-c','2000','-U','-w','-','host 10.0.0.5 and port 443'])
        for bad in (dict(plan,path='dumpcap'),dict(plan,path='/usr/bin/sudo'),dict(plan,tool='sudo',path='/usr/bin/sudo'),dict(plan,bpf='port 1; reboot'),
                    dict(plan,path='/tmp/x/tcpdump')):
            with self.assertRaises(nc.CaptureError,msg=bad):nc.command(bad)
        for argv in (nc.command(plan),nc.command(dict(plan,tool='tcpdump',path='/usr/sbin/tcpdump'))):
            self.assertNotIn('sudo',' '.join(argv));self.assertNotIn('pkexec',' '.join(argv));self.assertIn('-p',argv)
            self.assertEqual(argv[argv.index('-s')+1],str(nc.SNAP));self.assertEqual(nc.SNAP,128)

    def test_a_capture_runs_names_processes_and_is_read_with_a_rising_cursor(self):
        out=self.start_capture({'filter':'tcp','seconds':60,'packets':2000});ident=self.launched[0]
        plan=self.kernel.record('jobs',ident)['request_spec']['network']
        owners=nw.owner_index([{'proto':'tcp','local':'192.168.1.20','lport':51000,'remote':'93.184.216.34','rport':443,'state':'ESTABLISHED','process':'firefox','pid':4242}])
        with patch.object(nc.Owners,'name',lambda self,packet:nw.attribute(packet,owners,{'192.168.1.20'})):
            spawned=self.run_capture(ident,lambda argv:FakeTool(argv,pcapng([SYN,SYNACK,PUSH,DNS6,ARP])))
        self.assertEqual(spawned.call_args[0][0],nc.command(plan))   # argv exactly as designed
        job=self.kernel.record('jobs',ident)
        self.assertEqual(job['state'],'Completed',job.get('error'));self.assertEqual(job['capture']['packets'],5)
        path=nc.packets_path(self.kernel,ident)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600);self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode),0o700)
        self.assertNotIn(PAYLOAD,path.read_bytes())
        first=self.ok('network.capture.read',{'limit':2})
        self.assertEqual([p['seq'] for p in first['packets']],[1,2]);self.assertEqual(first['next'],2);self.assertEqual(first['rest'],3)
        self.assertEqual((first['packets'][0]['process'],first['packets'][0]['pid'],first['packets'][1]['flags']),('firefox',4242,'S.'))
        self.assertEqual([p.get('process') for p in self.ok('network.capture.read')['packets']],['firefox','firefox','firefox',None,None])   # by the conversation
        self.assertNotIn(PAYLOAD.decode(),json.dumps(self.kernel.record('jobs',ident)))   # nor in the job record
        self.assertEqual(set(first['packets'][0])>={'seq','at','iface','proto','src','sport','dst','dport','length'},True)
        rest=self.ok('network.capture.read',{'after':first['next'],'filter':'tcp'})
        self.assertEqual([p['seq'] for p in rest['packets']],[3]);self.assertEqual(rest['next'],5)
        self.assertEqual(self.ok('network.capture.read',{'after':5})['packets'],[])
        # the next capture's numbers continue: an old cursor never meets new packets twice
        self.start_capture({});second=self.launched[-1]
        self.assertEqual(self.kernel.record('jobs',second)['request_spec']['network']['seq_first'],6)
        self.assertFalse(path.exists())   # one capture is kept: the next start deleted the previous one

    def test_a_refused_start_keeps_the_previous_capture(self):
        self.start_capture({'seconds':60,'packets':2000});first=self.launched[0]
        self.run_capture(first,lambda argv:FakeTool(argv,pcapng([SYN,SYNACK,PUSH])))
        path=nc.packets_path(self.kernel,first);self.assertTrue(path.exists())
        work_trail.hold(self.kernel,self.owner)   # Master Stop holds work: Kernel.submit refuses the next start
        self.allow_submit=True
        try:
            with patch.object(nc,'availability',return_value=DUMPCAP):refused=self.call('network.capture.start',{'filter':'port 443'})
        finally:self.allow_submit=False
        self.assertFalse(refused['ok']);self.assertIn('WORK_HELD',refused['error']['message']);self.assertEqual(self.launched,[first])
        self.assertTrue(path.exists());self.assertEqual(len(self.ok('network.capture.read')['packets']),3)   # still there to read
        with patch.object(nc,'availability',return_value=DUMPCAP):self.assertEqual(self.ok('network.observe')['capture']['last']['job'],first)
        work_trail.resume(self.kernel,self.owner)
        self.start_capture({});self.assertFalse(path.exists())   # an accepted start deletes it

    def test_the_capture_s_own_filter_reads_its_own_packets(self):
        self.start_capture({'filter':'ip'});ident=self.launched[0]
        self.assertEqual(self.kernel.record('jobs',ident)['request_spec']['network']['bpf'],'ip')
        self.run_capture(ident,lambda argv:FakeTool(argv,pcapng([SYN,SYNACK,PUSH,DNS6,ARP])))   # the stand-in sends more than ip selects
        self.assertEqual([p['seq'] for p in self.ok('network.capture.read',{'filter':'ip'})['packets']],[1,2,3])
        self.assertEqual([p['seq'] for p in self.ok('network.capture.read',{'filter':'ip6'})['packets']],[4])
        with tempfile.TemporaryDirectory() as d:
            proc,sys_root,etc=fake_tree(d)
            with patch.object(nw,'connections',side_effect=lambda proc_root,etc_root,*a,**k:REAL(proc_root,etc_root,'little',uid=1000)):
                counts=[nw.observe(None,{'filter':w},proc_root=proc,sys_root=sys_root,etc=etc,now=1.0,memory={},capture={'state':'IDLE'})['counts']['matched']
                        for w in ('ip','ip6','tcp','tcp6')]
        self.assertEqual(counts,[6,1,6,1])   # the fake computer: six IPv4 sockets (one through a mapped tcp6), one IPv6 listener

    def test_a_paired_phone_never_reads_the_capture_job(self):
        self.start_capture({'filter':'host 192.168.1.20 port 443','seconds':60,'packets':2000});ident=self.launched[0]
        self.run_capture(ident,lambda argv:FakeTool(argv,pcapng([SYN,SYNACK,PUSH])))
        from workbench.remote_service import REMOTE_OPERATIONS
        self.assertEqual([op for op in REMOTE_OPERATIONS if op.startswith('network.')],[])
        self.assertTrue({'jobs.get','jobs.list','files.read'}<=REMOTE_OPERATIONS)   # why the record itself must be the owner's only
        for scopes in ({'read'},{'read','execute','candidate'},{'read','execute','candidate','approve'}):   # the view, develop and owner pairings
            phone=Principal('remote-device-0a1b2c3d4e5f',frozenset(scopes))   # remote_service names every paired device so
            got=self.call('jobs.get',{'id':ident},phone);self.assertFalse(got['ok'],scopes);self.assertIn('Record unavailable',got['error']['message'])
            listed=self.call('jobs.list',{},phone);self.assertTrue(listed['ok'],listed)
            self.assertNotIn(ident,[j['id'] for j in listed['result']]);self.assertNotIn('192.168.1.20',json.dumps(listed['result']))
            self.assertFalse(self.call('files.read',{'path':'.ledger/network/%s.tsv'%ident},phone)['ok'])
            read=self.call('network.capture.read',{},phone)   # not on the phone link at all; and even dispatched directly, no packets
            self.assertEqual(read['result']['packets'] if read['ok'] else [],[],scopes)
        self.assertEqual(self.ok('jobs.get',{'id':ident})['tool'],'network.capture')   # the owner reads it
        self.assertIn(ident,[j['id'] for j in self.ok('jobs.list')])

    def test_refused_words_are_never_proposed_and_a_proposal_says_what_is_selected(self):
        agent=Principal('owner',frozenset({'read','execute'}))
        with patch.object(nc,'availability',return_value=DUMPCAP):
            for text in ('portrange 1-2 dst','fe80::1%$(reboot)','gateway 10.0.0.1'):
                for who in (agent,self.owner):
                    r=self.call('network.capture.start',{'filter':text},who)
                    self.assertFalse(r['ok'],text);self.assertIn('NETWORK_FILTER_REFUSED',r['error']['message'],text)
                self.assertFalse(nc.proposal_path(self.kernel).exists(),text)
            r=self.call('network.capture.start',{'filter':'firefox port 443 established'},agent)
        self.assertIn(nc.NEEDS_OWNER,r['error']['message'])
        self.assertIn('(the capture tool selects port 443; firefox is applied as the packets are read; established narrows connections, not packets)',r['error']['message'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])

    def test_the_packet_bound_ends_a_capture(self):
        self.start_capture({'seconds':60,'packets':3});ident=self.launched[0]
        self.run_capture(ident,lambda argv:FakeTool(argv,pcapng([SYN]*10),stay_open=True))
        job=self.kernel.record('jobs',ident)
        self.assertEqual((job['state'],job['capture']['packets'],job['capture']['outcome']),('Completed',3,'reached 3 packets'))
        self.assertTrue(FakeTool.instances[-1].stopped)

    def test_the_seconds_bound_ends_a_capture(self):
        self.start_capture({'seconds':5});ident=self.launched[0]
        ticks=iter(range(0,10000));clock=lambda:float(next(ticks))
        with patch.object(nc,'availability',return_value=DUMPCAP),patch.object(nc,'spawn',side_effect=lambda argv:FakeTool(argv,pcapng([SYN]),stay_open=True)),\
             patch.object(nc.Owners,'refresh',lambda self,force=False:None):
            job=self.kernel.record('jobs',ident);job.update(state='Running');self.kernel.save('jobs',job)
            nc.run(self.kernel,ident,clock=clock)
        job=self.kernel.record('jobs',ident)
        self.assertEqual((job['state'],job['capture']['outcome']),('Completed','reached 5 seconds'));self.assertTrue(FakeTool.instances[-1].stopped)

    def stopped_by(self,how):
        self.start_capture({});ident=self.launched[0]
        started=threading.Event()
        def tool(argv):
            started.set();return FakeTool(argv,pcapng([SYN]),stay_open=True)
        worker=threading.Thread(target=self.run_capture,args=(ident,tool));worker.start()
        self.assertTrue(started.wait(10))
        time.sleep(0.3);how(ident);worker.join(15);self.assertFalse(worker.is_alive())
        return self.kernel.record('jobs',ident)

    def test_stop_capture_ends_it_and_keeps_what_was_captured(self):
        job=self.stopped_by(lambda ident:self.ok('network.capture.stop'))
        self.assertEqual((job['state'],job['capture']['outcome'],job['capture']['packets']),('Cancelled','stopped',1));self.assertTrue(FakeTool.instances[-1].stopped)
        self.assertEqual(len(self.ok('network.capture.read')['packets']),1)
        with patch.object(nc,'availability',return_value=DUMPCAP):
            self.assertEqual(self.ok('network.observe')['capture']['last']['outcome'],'stopped')
            gone=self.ok('network.capture.stop',{'discard':True})
        self.assertTrue(gone['discarded']);self.assertEqual(self.ok('network.capture.read')['packets'],[])
        self.assertFalse(nc.packets_path(self.kernel,job['id']).exists())

    def test_master_stop_ends_a_capture_through_jobs_cancel(self):
        def master_stop(ident):   # what qt_master_stop does for every job that is not finished
            for job in self.kernel.listing('jobs'):
                if job['state'] not in ('Completed','Failed','Cancelled'):self.assertTrue(self.call('jobs.cancel',{'id':job['id']})['ok'])
        job=self.stopped_by(master_stop)
        self.assertEqual(job['state'],'Cancelled');self.assertTrue(FakeTool.instances[-1].stopped)

    def test_the_work_hold_master_stop_takes_ends_a_capture(self):
        job=self.stopped_by(lambda ident:work_trail.hold(self.kernel,self.owner))
        self.assertEqual((job['state'],job['capture']['outcome']),('Cancelled','stopped: work is held'))

    def test_a_capture_is_never_paused_resumed_or_submitted_another_way(self):
        self.start_capture({});ident=self.launched[0]
        for op in ('jobs.pause','jobs.resume'):
            r=self.call(op,{'id':ident});self.assertFalse(r['ok']);self.assertIn('never paused or resumed',r['error']['message'])
        self.allow_submit=True
        r=self.call('jobs.submit',{'tool':'network.capture'});self.assertFalse(r['ok'])
        self.assertIn('network.capture.start',r['error']['message'])
        r=self.call('jobs.submit',{'tool':'network.capture','network':{}});self.assertFalse(r['ok'])   # the schema has no such options
        plan=self.kernel.record('jobs',ident)['request_spec']['network']
        agent=Principal('owner',frozenset({'read','execute'}))
        with self.assertRaises(ValueError) as refused:
            self.kernel.submit({'tool':'network.capture','request_key':'network-capture:'+plan['plan'],'network':plan},agent)
        self.assertIn(nc.NEEDS_OWNER,str(refused.exception))
        with self.assertRaises(ValueError):
            self.kernel.submit({'tool':'network.capture','request_key':'network-capture:'+plan['plan'],'network':dict(plan,bpf='port 1')},self.owner)
        with self.assertRaises(ValueError):self.kernel.submit({'tool':'ledger.kernel_tests','network':plan},self.owner)
        # a running capture does not hold the workspace: other work is still accepted
        other=self.kernel.submit({'tool':'ledger.kernel_tests'},self.owner)
        self.assertEqual(other['state'],'Queued')

    def test_the_tool_s_own_refusal_and_damaged_output_end_the_capture_with_words(self):
        self.start_capture({});ident=self.launched[0]
        self.run_capture(ident,lambda argv:FakeTool(argv,b'',stderr=b"dumpcap: You don't have permission to capture on that device",code=1))
        job=self.kernel.record('jobs',ident)
        self.assertEqual(job['state'],'Failed');self.assertIn("don't have permission",job['error'])
        with patch.object(nc,'availability',return_value=DUMPCAP),patch.object(nc.os,'getgroups',return_value=job['capture']['groups']):
            capture=self.ok('network.observe')['capture']
        self.assertEqual(capture['state'],'UNAVAILABLE');self.assertIn('dpkg-reconfigure wireshark-common',capture['reason']);self.assertNotIn('sudo',capture['reason'])
        self.start_capture({},found=dict(DUMPCAP,signature='a new tool'));second=self.launched[-1]   # a changed tool is tried again
        self.run_capture(second,lambda argv:FakeTool(argv,b'NOT A CAPTURE STREAM'),found=dict(DUMPCAP,signature='a new tool'))
        job=self.kernel.record('jobs',second)
        self.assertEqual(job['state'],'Failed');self.assertIn('damaged',job['error'])

    def test_unavailable_starts_nothing_and_says_how_to_enable_it(self):
        with patch.object(nc,'availability',return_value=MISSING):
            out=self.ok('network.capture.start',{'filter':'port 443'})
        self.assertFalse(out['started']);self.assertEqual(out['capture']['state'],'UNAVAILABLE');self.assertEqual(out['capture']['reason'],MISSING['reason'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])

    def test_a_filter_that_is_not_understood_starts_nothing(self):
        self.allow_submit=True
        with patch.object(nc,'availability',return_value=DUMPCAP):
            for text in ('port 443; rm -rf /','example.org','tcp and udp','raw'):
                r=self.call('network.capture.start',{'filter':text});self.assertFalse(r['ok'],text);self.assertIn('NETWORK_FILTER_REFUSED',r['error']['message'])
            r=self.call('network.capture.start',{'interface':'wlan9'});self.assertIn('NETWORK_INTERFACE_UNKNOWN',r['error']['message'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])


class Ring(unittest.TestCase):
    def test_the_ring_keeps_the_newest_and_its_file_stays_bounded(self):
        with tempfile.TemporaryDirectory() as d,patch.object(nc,'RING',5):
            path=Path(d)/'ring.tsv';recorder=nc.Recorder(path,100)
            for n in range(23):
                recorder.add({'at':float(n),'iface':'eth0','proto':'tcp','src':'1.1.1.1','sport':1,'dst':'2.2.2.2','dport':2,'length':60,'flags':None})
                recorder.flush()
                self.assertLessEqual(len(path.read_text().splitlines()),10)
            self.assertEqual(len(recorder.ring),5);self.assertEqual([r['seq'] for r in nc.load_packets(path)],[118,119,120,121,122])
            self.assertNotIn('flags',nc.load_packets(path)[0]);self.assertIn('sport',nc.load_packets(path)[0])
            self.assertEqual(recorder.progress(),{'packets':23,'bytes':23*60,'seq_first':100,'seq_last':122})
            self.assertEqual([r['seq'] for r in nc.load_packets(path,after=120)],[121,122])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            recorder.close(discard=True);self.assertFalse(path.exists())


# ---------------------------------------------------------------------------------------------------------------- the agent
class AgentAccess(Workspace):
    def setUp(self):
        super().setUp()
        self.addCleanup(patch.stopall)
        rows=[{'proto':'tcp','local':'192.168.1.20','lport':51000,'remote':'93.184.216.34','rport':443,'state':'ESTABLISHED','rservice':'https','pid':4242,'process':'firefox','user':'owner'},
              {'proto':'tcp','local':'0.0.0.0','lport':22,'remote':'0.0.0.0','rport':0,'state':'LISTEN','lservice':'ssh','process':'another user','user':'root'},
              {'proto':'udp','local':'0.0.0.0','lport':5353,'remote':'0.0.0.0','rport':0,'state':'UNCONN','pid':88,'process':'avahi','user':'owner'}]
        patch.object(nw,'connections',return_value=(rows,[])).start()
        patch.object(nw,'interfaces',return_value=([{'name':'eth0','up':True,'rx_bps':800.0,'tx_bps':400.0,'rx_bytes':1,'tx_bytes':1}],None)).start()

    def test_tool_selection_offers_the_reads_for_the_owner_s_words(self):
        definitions=schemas()
        for words in ('network','traffic','connection','port','packet','bandwidth','listening','What is talking to the network?'):
            chosen=[r['operation'] for r in tool_selection.relevant(words,ek.CAPABILITIES,definitions,6)]
            self.assertIn('network.observe',chosen,words);self.assertIn('network.capture.read',chosen,words)   # offered, the reads before the controls
            self.assertLess(chosen.index('network.observe'),chosen.index('network.capture.read'),words)
            if 'network.capture.start' in chosen:self.assertLess(chosen.index('network.capture.read'),chosen.index('network.capture.start'),words)
        self.assertEqual([r['operation'] for r in tool_selection.relevant('What is talking to the network?',ek.CAPABILITIES,definitions,2)],['network.observe','network.capture.read'])
        self.assertEqual({r['scope'] for r in tool_selection.relevant('network traffic',ek.CAPABILITIES,definitions,6) if r['operation'].startswith('network.')},{'read','execute'})

    def test_the_words_choose_the_network_assignment(self):
        for text in ('What is talking to the network?','which programs are using the internet','what ports are open','what is listening on this computer',
                     'capture the traffic on port 443','how much bandwidth is firefox using','show me the network connections','is anything phoning home'):
            self.assertTrue(pn.fits(text),text);self.assertEqual(loop.request_profile(text),'network_talk',text)
        for text in ('find files about the network','add up the numbers on this page','write a poem about foxes','show related connections','make these words bold',''):
            self.assertNotEqual(loop.request_profile(text),'network_talk',text)
        self.assertEqual(loop.request_profile('find files about the network'),'files_about')
        self.assertEqual(pn.filter_of('capture the traffic to 10.0.0.5 on port 443 over tcp'),'10.0.0.5 port 443 tcp')
        self.assertEqual((pn.filter_of('capture port ٤٤٣'),pn.filter_of('capture port 443 and :22')),('','port 443 port 22'))   # ASCII digits, as the grammar
        self.assertTrue(pn.wants_capture('capture the traffic on port 443'));self.assertFalse(pn.wants_capture('What is talking to the network?'))
        self.assertIs(profiles.PROFILES['network_talk'],pn.PROFILE);self.assertIn('network_talk',schemas()['agent.assign']['properties']['profile']['enum'])

    def assign(self,request):
        with patch.object(nc,'availability',return_value=DUMPCAP):
            a=self.ok('agent.assign',{'request':request})['assignment']
            self.assertEqual(a['profile'],'network_talk')
            with patch.object(loop,'ask_model',side_effect=AssertionError('no model is asked')):
                return a,self.ok('agent.run',{'id':a['id']})['assignment']

    def page(self,row):
        ident=next(i['id'] for i in row['inspect'] if i['kind']=='document')
        return '\n'.join(b['text'] for b in self.ok('documents.get',{'id':ident})['document']['blocks'])

    def test_what_is_talking_reads_freely_and_writes_a_findings_page(self):
        _,row=self.assign('What is talking to the network?')
        self.assertEqual(row['state'],'DONE',row);self.assertIn('the findings page is in Documents',row['reason'])
        text=self.page(row)
        self.assertIn('Talking: firefox (pid 4242) · 1 connection · 93.184.216.34:443 (https)',text)
        self.assertIn('another user on tcp 22 (ssh)',text);self.assertIn('Capture: none was taken',text);self.assertIn('nothing was sent anywhere',text)
        self.assertTrue(any('firefox (pid 4242) talks to 93.184.216.34:443 (https)'==f['text'] for f in row['found']),row['found'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])
        with self.kernel.db() as db:
            steps=[r[0] for r in db.execute('SELECT program FROM inv_steps ORDER BY seq')]
        self.assertEqual([json.loads(p)['operation'] for p in steps],['network.observe','network.capture.read','documents.create'])

    def test_a_capture_is_a_proposal_the_owner_approves_and_the_agent_never_starts_one(self):
        a,row=self.assign('capture the traffic on port 443')
        self.assertEqual(row['state'],'WAITING');self.assertIn('Only you can start it',row['reason']);self.assertIn('port 443',row['reason'])
        self.assertEqual(self.submitted,[]);self.assertEqual(self.launched,[])          # the agent's start was refused before any job
        with patch.object(nc,'availability',return_value=DUMPCAP):
            proposal=self.ok('network.observe')['capture']['proposal']
        self.assertEqual((proposal['filter'],proposal['seconds'],proposal['packets'],proposal['by']),('port 443',60,2000,'owner'))
        # the assignment's own principal: read and execute, never approve
        bounded=loop.bound(self.owner,{'effects':'execute'});self.assertNotIn('approve',bounded.scopes)
        r=self.call('network.capture.start',{'filter':'port 443'},bounded);self.assertFalse(r['ok']);self.assertIn(nc.NEEDS_OWNER,r['error']['message'])
        # the owner approves: their own start (Log, Network, Capture… or Run on a proposal card), then Resume
        self.start_capture({'filter':proposal['filter'],'seconds':proposal['seconds'],'packets':proposal['packets']})
        with patch.object(nc.Owners,'name',lambda self,packet:('firefox',4242) if 443 in (packet.get('sport'),packet.get('dport')) else None):
            self.run_capture(self.launched[0],lambda argv:FakeTool(argv,pcapng([SYN,SYNACK,PUSH])))
        with patch.object(nc,'availability',return_value=DUMPCAP):
            self.assertNotIn('proposal',self.ok('network.observe')['capture'])   # the owner's start answered it
            self.ok('agent.resume',{'id':a['id']})
            with patch.object(loop,'ask_model',side_effect=AssertionError('no model is asked')):row=self.ok('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE',row);text=self.page(row)
        self.assertIn('Capture: 3 packet headers from the latest capture (filter: port 443).',text)
        self.assertIn('Captured: tcp 93.184.216.34:443 · 3 packets',text);self.assertIn('firefox',text)
        self.assertEqual(len(self.launched),1)   # only the owner's start launched anything

    def test_an_unavailable_capture_becomes_a_question_not_a_proposal(self):
        with patch.object(nc,'availability',return_value=MISSING):
            a=self.ok('agent.assign',{'request':'sniff the packets on port 53'})['assignment']
            row=self.ok('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE',row)
        self.assertTrue(any(MISSING['reason'] in n['text'] for n in row['needs_you']),row['needs_you'])
        self.assertIn('Capture: not available on this computer.',self.page(row))
        self.assertFalse(nc.proposal_path(self.kernel).exists())


class Install(unittest.TestCase):
    def test_the_debian_installer_offers_the_capture_package_and_explains_the_rest(self):
        text=INSTALLER.read_text()
        self.assertIn('--network-capture',text);self.assertIn('wireshark-common',text)
        self.assertNotIn('usermod',text.split('--network-capture) ',1)[1].split(';;',1)[0])   # the option installs; it never changes groups
        self.assertIn('dpkg-reconfigure wireshark-common',text)

    def test_the_installer_and_the_install_note_give_the_steps_in_graphite_s_own_words(self):
        """The steps the installer prints, run as it runs them, are word for word the app's (RECONFIGURE, join_step, RELOG), with
        the login of whoever runs it, and never say sudo; the install note lists the same."""
        text=INSTALLER.read_text()
        self.assertIn('# network-capture steps: begin\n',text,'the installer marks the block that prints the steps')
        block=text.split('# network-capture steps: begin\n',1)[1].split('# network-capture steps: end',1)[0]
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'id';fake.write_text('#!/bin/sh\necho owner\n');fake.chmod(0o755)   # whoever runs it: their login
            out=subprocess.run(['bash','-c','network_capture=1\n'+block],capture_output=True,text=True,env={'PATH':d+':/usr/bin:/bin'},timeout=30)
        self.assertEqual(out.returncode,0,out.stderr)
        lines=[line.strip() for line in out.stdout.splitlines()]
        for step in (nw.RECONFIGURE,nw.join_step('owner'),nw.RELOG):self.assertIn(step,lines)
        self.assertNotIn('sudo',out.stdout.lower())
        section=DEBIAN_DOC.read_text().split('## The optional packet capture',1)[1].split('\n## ',1)[0]
        self.assertNotIn('sudo',section.lower())
        for words in ('as the administrator, `dpkg-reconfigure wireshark-common`, and answer Yes: non-superusers may capture packets',
                      'as the administrator, `usermod -aG wireshark <your login>`',nw.RELOG):
            self.assertIn(words,section)


if __name__=='__main__':unittest.main()
