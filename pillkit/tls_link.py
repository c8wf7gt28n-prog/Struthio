"""Pill TLS/1: pinned mutual TLS, bounded resumable transfer, quarantine only.

TLS is Python/OpenSSL's maintained implementation. Pins are owner-installed
certificates bound to the existing pill Ed25519 identity; DNS is not identity.
No request accepts work, executes code, or applies a returned revision.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import datetime as dt
import errno
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import socket
import ssl
import threading
import time
import uuid
from . import pill as P
from .state import database,lock

CHUNK=1024*1024
CARD='arc.pill-tls-card/1'


def private(path,raw):
    path=Path(path);temp=path.with_name('.'+uuid.uuid4().hex)
    P.write_private(temp,raw);os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def certificate(ring,rotate=False):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
    cert=ring.folder/'tls-cert.pem';key=ring.folder/'tls-private.pem'
    with lock(ring.folder,'tls-certificate'):
        if rotate or not cert.exists():
            subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Ledger '+ring.key)])
            now=dt.datetime.now(dt.timezone.utc)
            value=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(ring._key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now-dt.timedelta(minutes=5)).not_valid_after(now+dt.timedelta(days=365))
                .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
                .add_extension(x509.KeyUsage(True,False,False,False,False,False,False,None,None),critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH,ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(ring._key.public_key()),critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ring._key.public_key()),critical=False)
                .sign(ring._key,None))
            private(key,ring._key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            private(cert,value.public_bytes(serialization.Encoding.PEM))
        for path in (cert,key):
            if path.is_symlink() or path.stat().st_mode&0o077:raise ValueError('TLS identity must be an owned private ordinary file')
        parsed=x509.load_pem_x509_certificate(cert.read_bytes())
        public=parsed.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        if public!=ring.public:raise ValueError('TLS certificate is not bound to this pill identity')
    return cert,key


def card(ring):
    cert,_=certificate(ring);pem=cert.read_text()
    body={'schema':CARD,'pill':ring.card(),'certificate':pem,'certificate_sha256':hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()}
    return {**body,'signature':ring.sign(P.canonical(body))}


def pair(ring,value,expected):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    if not isinstance(value,dict) or set(value)!={'schema','pill','certificate','certificate_sha256','signature'} or value['schema']!=CARD:raise ValueError('TLS pairing card version/fields refused')
    body={k:v for k,v in value.items() if k!='signature'};identity=value['pill'];public=identity['public']
    P.fingerprint(public)
    try:Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(bytes.fromhex(value['signature']),P.canonical(body))
    except (InvalidSignature,ValueError):raise ValueError('TLS pairing card signature refused') from None
    parsed=x509.load_pem_x509_certificate(value['certificate'].encode())
    if parsed.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()!=public:raise ValueError('TLS and pill public keys differ')
    digest=hashlib.sha256(ssl.PEM_cert_to_DER_cert(value['certificate'])).hexdigest()
    if digest!=expected or digest!=value['certificate_sha256']:raise ValueError('Compare the full certificate fingerprint through your other trusted channel')
    now=dt.datetime.now(dt.timezone.utc)
    if not parsed.not_valid_before_utc<=now<parsed.not_valid_after_utc:raise ValueError('TLS certificate is expired or not yet valid')
    with lock(ring.folder,'tls-peers'):
        paired=ring.pair(identity);peers=P.read_state(ring.folder/'tls-peers.json',{})
        peers[paired['key']]={'certificate':value['certificate'],'sha256':digest,'public':public,'paired':time.time()}
        P.write_state(ring.folder/'tls-peers.json',peers)
    return {**paired,'certificate_sha256':digest,'transport':'TLS1.3_WITH_EXACT_CERTIFICATE_PIN'}


def active(ring,peer):
    _,identity=ring.peer(peer)
    record=P.read_state(ring.folder/'tls-peers.json',{}).get(peer)
    if not record or record['public']!=identity['public']:raise ValueError('TLS_PAIRING_REQUIRED: exchange and verify the TLS card first')
    return record


def context(ring,server=False):
    cert,key=certificate(ring)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    if not server:ctx.check_hostname=False  # Exact pinned identity is checked before any application bytes are sent.
    ctx.minimum_version=ssl.TLSVersion.TLSv1_3;ctx.verify_mode=ssl.CERT_REQUIRED
    ctx.options|=ssl.OP_NO_TICKET
    if hasattr(ssl,'VERIFY_X509_PARTIAL_CHAIN'):ctx.verify_flags|=ssl.VERIFY_X509_PARTIAL_CHAIN
    certificates=[]
    for peer in ring.peers():
        try:certificates.append(active(ring,peer)['certificate'])
        except ValueError:pass
    if not certificates:raise ValueError('No currently paired TLS certificate')
    ctx.load_verify_locations(cadata='\n'.join(certificates));ctx.load_cert_chain(cert,key)
    return ctx


def peer_of(sock,ring,expected=None):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    raw=sock.getpeercert(binary_form=True)
    cert=x509.load_der_x509_certificate(raw)
    public=cert.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex();peer=P.fingerprint(public)
    record=active(ring,peer)
    if expected is not None and peer!=expected:raise ValueError('TLS_WRONG_PEER')
    if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('TLS_CERTIFICATE_CHANGED_REPAIR_REQUIRED')
    return peer


def address(text):
    host,sep,port=text.rpartition(':');host=host.removeprefix('[').removesuffix(']')
    if not sep or not host or not port.isdecimal() or not 1<=int(port)<=65535 or any(c in host for c in '/@\\\r\n'):raise ValueError('Use host:port or [IPv6]:port')
    return host,int(port)


def tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS tls_transfers(peer TEXT,id TEXT,sha TEXT,total INTEGER,received INTEGER,state TEXT,PRIMARY KEY(peer,id))')
    db.execute('CREATE TABLE IF NOT EXISTS tls_offers(id TEXT PRIMARY KEY,peer TEXT,sha TEXT,total INTEGER,path TEXT)')


def ordinary(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file() or path.stat().st_nlink!=1:raise ValueError('Transfer requires an ordinary unlinked file')
    if path.stat().st_size>P.MAX_PILL:raise ValueError('Pill size limit')
    return path


class RecipientView:
    def __init__(self,ring,peer):self.key=peer;self.ring=ring
    def peers(self):return {self.ring.key:{'name':self.ring.name,'public':self.ring.public}}


def publish(ring,path):
    path=ordinary(path);raw=path.read_bytes();members=P.read_members(raw);c=P.strict_json(members['pill.json'],'pill contract')
    peer=c['recipient']['key'];active(ring,peer)
    pill=P.open_pill(raw,RecipientView(ring,peer),replay=False)
    folder=ring.folder/'tls-outgoing';folder.mkdir(mode=0o700,exist_ok=True);dest=folder/(pill.id+'.pill')
    if dest.exists() and P.sha256(dest.read_bytes())!=P.sha256(raw):raise ValueError('Outgoing pill identity collision')
    if not dest.exists():P.write_private(dest,raw)
    with database(ring.folder) as db:
        tables(db);db.execute('INSERT OR REPLACE INTO tls_offers VALUES(?,?,?,?,?)',(pill.id,peer,P.sha256(raw),len(raw),str(dest)))
    return {'id':pill.id,'peer':peer,'sha256':P.sha256(raw),'bytes':len(raw)}


def transfer(ring,peer,ident,sha,total):
    active(ring,peer)
    if not P.ID.fullmatch(ident) or not P.SHA.fullmatch(sha) or type(total)!=int or not 1<=total<=P.MAX_PILL:raise ValueError('Transfer contract refused')
    with database(ring.folder) as db:
        tables(db);row=db.execute('SELECT sha,total,received,state FROM tls_transfers WHERE peer=? AND id=?',(peer,ident)).fetchone()
        if row and (row[0],row[1])!=(sha,total):raise ValueError('Transfer id already binds different bytes')
        if not row:db.execute('INSERT INTO tls_transfers VALUES(?,?,?,?,0,?)',(peer,ident,sha,total,'PARTIAL'))
    return {'received':row[2] if row else 0,'state':row[3] if row else 'PARTIAL'}


def chunk(ring,peer,ident,offset,raw,into):
    active(ring,peer)
    if len(raw)>CHUNK:raise ValueError('Transfer chunk limit')
    into=Path(into).absolute();into.mkdir(parents=True,mode=0o700,exist_ok=True)
    if any(p.is_symlink() for p in (into,*into.parents)):raise ValueError('Linked quarantine refused')
    partial=ring.folder/'tls-partial';partial.mkdir(mode=0o700,exist_ok=True);temp=partial/(peer+'-'+ident+'.part')
    with lock(ring.folder,'transfer-'+peer+'-'+ident),database(ring.folder) as db:
        tables(db);row=db.execute('SELECT sha,total,received,state FROM tls_transfers WHERE peer=? AND id=?',(peer,ident)).fetchone()
        if not row:raise ValueError('Unknown transfer')
        sha,total,received,state=row;dest=into/(peer+'-'+ident+'.pill');cross=into/('.receive-'+peer+'-'+ident+'.part')
        if dest.exists():
            # A power/process interruption can leave the publication's second link.
            if temp.exists() and not temp.is_symlink() and not dest.is_symlink() and os.path.samestat(temp.stat(),dest.stat()) and dest.stat().st_nlink==2:
                temp.unlink()
            if cross.exists() and not cross.is_symlink() and not dest.is_symlink() and os.path.samestat(cross.stat(),dest.stat()) and dest.stat().st_nlink==2:
                cross.unlink()
            data=ordinary(dest).read_bytes()
            if P.sha256(data)!=sha:raise ValueError('Retained quarantine changed; inspect it')
            pill=P.open_pill(data,ring,replay=False)
            if pill.id!=ident or pill.contract['sender']['key']!=peer:raise ValueError('Retained quarantine identity differs')
            db.execute('UPDATE tls_transfers SET received=?,state=? WHERE peer=? AND id=?',(total,'QUARANTINED',peer,ident))
            if temp.exists():temp.unlink()
            return {'received':total,'state':'QUARANTINED','path':str(dest)}
        if state=='QUARANTINED':raise ValueError('Retained quarantine is missing; inspect it')
        if offset!=received or not raw or received+len(raw)>total:raise ValueError('Transfer offset/size mismatch')
        fd=os.open(temp,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            if os.fstat(fd).st_nlink!=1:raise ValueError('Linked partial refused')
            if os.fstat(fd).st_size<received:raise ValueError('Partial transfer truncated; inspect it')
            os.ftruncate(fd,received);os.lseek(fd,received,os.SEEK_SET)
            with os.fdopen(fd,'r+b',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(fd)
        finally:os.close(fd)
        received+=len(raw);path=None
        if received==total:
            data=temp.read_bytes()
            if P.sha256(data)!=sha:raise ValueError('Completed transfer hash differs')
            pill=P.open_pill(data,ring,replay=False)
            if pill.id!=ident or pill.contract['sender']['key']!=peer:raise ValueError('TLS sender and signed pill identity differ')
            active(ring,peer)
            if dest.exists():
                if P.sha256(dest.read_bytes())!=sha:raise ValueError('Quarantine destination collision')
            else:
                try:os.link(temp,dest)
                except OSError as exc:
                    if exc.errno!=errno.EXDEV:raise
                    # USB/quarantine may live on another filesystem. Publish from
                    # a private sibling there, retaining the acknowledged source.
                    if cross.exists():
                        if ordinary(cross).read_bytes()!=data:raise ValueError('Retained quarantine staging changed')
                    else:P.write_private(cross,data)
                    os.link(cross,dest);cross.unlink()
                os.chmod(dest,0o600)
            temp.unlink();state='QUARANTINED';path=str(dest)
            fd=os.open(into,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        db.execute('UPDATE tls_transfers SET received=?,state=? WHERE peer=? AND id=?',(received,state,peer,ident))
        return {'received':received,'state':state,'path':path}


class Server(ThreadingHTTPServer):
    daemon_threads=True;allow_reuse_address=True
    def __init__(self,bind,ring,into,cancelled=lambda:False):
        self.ring=ring;self.into=into;self.cancelled=cancelled;self.slots=threading.BoundedSemaphore(8)
        super().__init__(bind,Handler);self.timeout=.2
    def get_request(self):
        sock,addr=super().get_request();sock.settimeout(8)
        try:return context(self.ring,True).wrap_socket(sock,server_side=True),addr
        except (ValueError,OSError):sock.close();raise OSError('TLS connection refused') from None
    def process_request(self,request,address):
        if not self.slots.acquire(False):request.close();return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()


class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def handle(self):
        try:super().handle()
        except (ConnectionError,TimeoutError,ssl.SSLError):pass
    def log_message(self,*args):pass
    def reply(self,value,status=200):
        raw=P.canonical(value);self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def handle_call(self):
        server=self.server;ring=server.ring
        if server.cancelled():raise ValueError('TRANSFER_STOPPED')
        peer=peer_of(self.connection,ring);parts=self.path.strip('/').split('/')
        if self.command=='GET' and parts==['v1','offers']:
            with database(ring.folder) as db:
                tables(db);rows=db.execute('SELECT id,sha,total FROM tls_offers WHERE peer=? LIMIT 200',(peer,)).fetchall()
            return self.reply({'offers':[{'id':r[0],'sha256':r[1],'bytes':r[2]} for r in rows]})
        if self.command=='GET' and len(parts)==4 and parts[:2]==['v1','pill']:
            ident,offset=parts[2:];offset=int(offset)
            with database(ring.folder) as db:
                tables(db);row=db.execute('SELECT sha,total,path FROM tls_offers WHERE id=? AND peer=?',(ident,peer)).fetchone()
            if not row or not 0<=offset<row[1]:raise ValueError('Unknown outgoing pill/offset')
            path=ordinary(row[2])
            if P.sha256(path.read_bytes())!=row[0]:raise ValueError('Published pill changed')
            with path.open('rb') as source:source.seek(offset);raw=source.read(CHUNK)
            peer_of(self.connection,ring,peer)
            self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if self.command not in ('POST','PUT') or len(parts) not in (3,4) or parts[:2]!=['v1','transfer'] or not P.ID.fullmatch(parts[2]):raise ValueError('Unknown pill endpoint')
        length=self.headers.get('Content-Length','')
        if not length.isdecimal() or int(length)>CHUNK or self.headers.get('Transfer-Encoding'):raise ValueError('Transfer body limit/framing')
        raw=self.rfile.read(int(length))
        if len(raw)!=int(length):raise ValueError('Interrupted transfer body')
        peer_of(self.connection,ring,peer)
        if server.cancelled():raise ValueError('TRANSFER_STOPPED')
        if self.command=='POST' and len(parts)==3:
            value=P.strict_json(raw,'transfer')
            if set(value)!={'sha256','bytes'}:raise ValueError('Transfer fields refused')
            return self.reply(transfer(ring,peer,parts[2],value['sha256'],value['bytes']))
        if self.command=='PUT' and len(parts)==4:return self.reply(chunk(ring,peer,parts[2],int(parts[3]),raw,server.into))
        raise ValueError('Unknown pill endpoint')
    def do_GET(self):
        try:self.handle_call()
        except (ValueError,OSError,KeyError,TypeError):self.reply({'error':'TRANSFER_REFUSED'},400)
    do_POST=do_GET;do_PUT=do_GET


@contextmanager
def connect(ring,endpoint,peer):
    active(ring,peer);host,port=address(endpoint)
    client=http.client.HTTPSConnection(host,port,timeout=10,context=context(ring))
    try:client.connect();peer_of(client.sock,ring,peer);yield client
    finally:client.close()


def request(ring,endpoint,peer,method,path,data=None,binary=False):
    with connect(ring,endpoint,peer) as client:
        client.request(method,path,body=data,headers={'Content-Type':'application/octet-stream'})
        response=client.getresponse();raw=response.read(CHUNK+1)
        if response.status!=200 or len(raw)>CHUNK:raise ValueError('TLS_TRANSFER_REFUSED_OR_LIMIT')
        return raw if binary else P.strict_json(raw,'TLS response')


def send(ring,endpoint,path,peer=None,cancelled=lambda:False):
    offer=publish(ring,path);peer=peer or offer['peer']
    if peer!=offer['peer']:raise ValueError('Pill is for a different TLS peer')
    value=request(ring,endpoint,peer,'POST','/v1/transfer/'+offer['id'],P.canonical({'sha256':offer['sha256'],'bytes':offer['bytes']}))
    with ordinary(path).open('rb') as source:
        while value['received']<offer['bytes']:
            if cancelled():raise ValueError('TRANSFER_STOPPED_WITH_RESUMABLE_PARTIAL')
            source.seek(value['received']);raw=source.read(min(CHUNK,offer['bytes']-value['received']))
            value=request(ring,endpoint,peer,'PUT','/v1/transfer/'+offer['id']+'/'+str(value['received']),raw)
    return {'id':offer['id'],'to':peer,'state':value['state'],'bytes':offer['bytes']}


def fetch(ring,endpoint,into,peer=None,cancelled=lambda:False):
    if peer is None:
        peers=[key for key in ring.peers() if P.read_state(ring.folder/'tls-peers.json',{}).get(key)]
        if len(peers)!=1:raise ValueError('Specify the TLS peer key when more than one computer is paired')
        peer=peers[0]
    offers=request(ring,endpoint,peer,'GET','/v1/offers')['offers'];saved=[]
    if len(offers)>200:raise ValueError('Offer count limit')
    for offer in offers:
        value=transfer(ring,peer,offer['id'],offer['sha256'],offer['bytes'])
        while value['received']<offer['bytes']:
            if cancelled():raise ValueError('TRANSFER_STOPPED_WITH_RESUMABLE_PARTIAL')
            raw=request(ring,endpoint,peer,'GET','/v1/pill/'+offer['id']+'/'+str(value['received']),binary=True)
            value=chunk(ring,peer,offer['id'],value['received'],raw,into)
        target=Path(into)/(peer+'-'+offer['id']+'.pill')
        if not target.is_file() or P.sha256(target.read_bytes())!=offer['sha256']:raise ValueError('Retained pill changed')
        saved.append(str(target))
    return {'from':peer,'saved':saved,'state':'QUARANTINED_NOT_ACCEPTED'}


def serve(ring,listen,outgoing,into,any_address=False,log=print,ready=None,cancelled=lambda:False):
    host,port=address(listen)
    if host not in ('localhost','127.0.0.1','::1') and not any_address:raise ValueError('A LAN listener requires explicit --any-address')
    context(ring,True)
    for path in sorted(Path(outgoing).glob('*.pill'))[:200]:publish(ring,path)
    with Server((host,port),ring,into,cancelled) as server:
        if ready:ready(server.server_address)
        log('Pill TLS/1 listening; receipt is quarantine only')
        while not cancelled():server.handle_request()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--state',type=Path,required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('card');sub.add_parser('rotate-certificate')
    p=sub.add_parser('pair');p.add_argument('card',type=Path);p.add_argument('--fingerprint',required=True)
    p=sub.add_parser('revoke');p.add_argument('peer')
    p=sub.add_parser('serve');p.add_argument('--listen',default='127.0.0.1:7717');p.add_argument('--outgoing',type=Path,required=True);p.add_argument('--into',type=Path,required=True);p.add_argument('--any-address',action='store_true')
    p=sub.add_parser('send');p.add_argument('path',type=Path);p.add_argument('--address',required=True);p.add_argument('--peer',required=True)
    p=sub.add_parser('fetch');p.add_argument('--into',type=Path,required=True);p.add_argument('--address',required=True);p.add_argument('--peer',required=True)
    args=parser.parse_args();ring=P.Keyring(args.state)
    if args.command=='card':result=card(ring)
    elif args.command=='rotate-certificate':certificate(ring,True);result=card(ring)
    elif args.command=='pair':result=pair(ring,P.strict_json(args.card.read_bytes(),'TLS card'),args.fingerprint)
    elif args.command=='revoke':ring.unpair(args.peer);result={'revoked':args.peer,'replay_history':'RETAINED'}
    elif args.command=='send':result=send(ring,args.address,args.path,args.peer)
    elif args.command=='fetch':result=fetch(ring,args.address,args.into,args.peer)
    else:serve(ring,args.listen,args.outgoing,args.into,args.any_address);return
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
