"""Compatibility entry point: Pill TLS/1 replaces the unreviewed custom wire protocol.

Existing signed arc.pill/1 files remain valid. Both network endpoints must be
upgraded and their TLS cards explicitly paired; there is no legacy fallback.
Historical source is retained in docs/history/pill_link_4_9.py.txt.
"""
from .tls_link import fetch,send,main
from . import tls_link

def parse_address(text,listening=False):
    return tls_link.address(text)

def serve(keyring,listen,outbox,inbox,any_address=False,log=print,ready=None):
    return tls_link.serve(keyring,listen,outbox,inbox,any_address,log,ready)
if __name__=='__main__':main()
