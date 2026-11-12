"""Generate an owner CA and server certificate locally using installed OpenSSL.

No network, system trust installation, firewall changes or server launch occurs.
Keep the directory private; only owner-ca.crt is suitable for phone trust import.
"""
from __future__ import annotations
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def create(destination, host):
    root = Path(__file__).resolve().parents[1]
    destination = Path(destination).expanduser().resolve()
    if destination.is_relative_to(root) and not destination.is_relative_to(root / '.ledger'):
        raise ValueError('Keep TLS private keys outside the active project or under private .ledger')
    try:
        ipaddress.ip_address(host); san = 'IP:' + host
    except ValueError:
        if not re.fullmatch(r'(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', host) or '..' in host:
            raise ValueError('Host must be a plain DNS name or IP, without scheme, port or path')
        san = 'DNS:' + host
    openssl = shutil.which('openssl')
    if not openssl: raise ValueError('Install OpenSSL on the owner computer to generate certificates')
    if destination.exists(): raise ValueError('Choose a new private directory; existing keys are never overwritten')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.ledger-tls-', dir=destination.parent))
    temp.chmod(0o700)
    def run(args):
        return subprocess.run([openssl, *args], cwd=temp, capture_output=True, text=True, timeout=30, check=True)
    try:
        run(['req', '-x509', '-newkey', 'rsa:3072', '-sha256', '-nodes', '-days', '3650',
             '-keyout', 'owner-ca.key', '-out', 'owner-ca.crt', '-subj', '/CN=ARC Ledger Owner CA',
             '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0', '-addext', 'keyUsage=critical,keyCertSign,cRLSign'])
        run(['req', '-new', '-newkey', 'rsa:3072', '-nodes', '-keyout', 'server.key', '-out', 'server.csr', '-subj', '/CN=ARC Ledger'])
        (temp/'server.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName='+san+'\n')
        run(['x509', '-req', '-in', 'server.csr', '-CA', 'owner-ca.crt', '-CAkey', 'owner-ca.key', '-CAcreateserial',
             '-out', 'server.crt', '-days', '365', '-sha256', '-extfile', 'server.ext'])
        run(['verify', '-CAfile', 'owner-ca.crt', 'server.crt'])
        fingerprint = run(['x509', '-in', 'owner-ca.crt', '-noout', '-fingerprint', '-sha256']).stdout.strip()
        (temp/'README.txt').write_text('Owner-generated development TLS.\nOnly owner-ca.crt is a trust-import file. Never copy .key files to the phone or project package.\nCompare this fingerprint over a trusted channel before importing the root:\n'+fingerprint+'\nSee docs/WORKSHOP.md for phone trust, reachability and revocation.\n')
        for p in temp.iterdir(): p.chmod(0o600)
        os.replace(temp, destination)
        return {'directory': str(destination), 'host': host, 'owner_ca_fingerprint': fingerprint,
                'certificate': str(destination/'server.crt'), 'key': str(destination/'server.key'),
                'network_calls': 0, 'trust_installed': False, 'reachability_verified': False}
    finally:
        if temp.exists(): shutil.rmtree(temp)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--host', required=True)
    args = p.parse_args()
    print(json.dumps(create(args.output, args.host), indent=2))
