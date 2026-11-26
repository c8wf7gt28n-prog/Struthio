"""Graphite 1.0 S5 · Is there a permission prompt agent in this session?

When a program asks the system for something that needs your permission (logind's restart or power-off answered
"challenge", udisks2 mounting a drive, NetworkManager changing a connection), polkit asks you through an authentication
agent: a small program of your session that shows the system's own password prompt. You type the password into that
prompt, never into Graphite; Graphite never sees or keeps it.

The dedicated session (LS_XSESSION.sh) starts lxpolkit beside Fluxbox when it is installed and exports its process id
(ARC_LEDGER_POLKIT_AGENT_PID). agent() says whether an agent is running for this user: that process when it still runs as
one of the known agents, else any known agent of this user found in /proc (another desktop's own agent). session_power
offers the actions logind answers "challenge" for only when an agent is running here.
"""
from __future__ import annotations

import os

AGENTS = {'lxpolkit': 'lxpolkit', 'polkit-gnome-au': 'the GNOME permission agent', 'polkit-mate-aut': 'the MATE permission agent',
          'lxqt-policykit-': 'the LXQt permission agent', 'polkit-kde-auth': 'the KDE permission agent',
          'xfce-polkit': 'the Xfce permission agent', 'polkit-agent-he': None}      # comm names are cut at 15 characters
SHIPPED = 'lxpolkit'
ENV = 'ARC_LEDGER_POLKIT_AGENT_PID'
NONE_HERE = ('No permission prompt agent is running in this session, so the system cannot ask for your permission here. '
             'The dedicated session starts lxpolkit when it is installed (Debian package lxpolkit, in the 1.0 System set).')


def _comm(proc, pid):
    try:
        with open(os.path.join(proc, str(int(pid)), 'comm'), encoding='utf-8') as f:return f.read().strip()
    except (OSError, ValueError):
        return None


def _mine(proc, pid):
    try:return os.stat(os.path.join(proc, str(int(pid)))).st_uid == os.getuid()
    except (OSError, ValueError, AttributeError):
        return False


def agent(environ=None, proc='/proc', scan=None):
    """dict(running, name, pid, words): the permission prompt agent of this session, or why there is none. `scan`: also look
    for any known agent of this user in /proc (by default only when reading this process's own environment, so a caller
    that passes an environment of its own gets an answer from that environment alone)."""
    scan = (environ is None) if scan is None else scan
    environ = os.environ if environ is None else environ
    said = str(environ.get(ENV, '') or '').strip()
    if said.isdigit():
        comm = _comm(proc, said)
        if comm and AGENTS.get(comm) and _mine(proc, said):
            return dict(running=True, name=comm, pid=int(said), words='Permission prompts are answered by %s (process %s), started with this session.' % (AGENTS[comm], said))
    try:
        entries = [e for e in os.listdir(proc) if e.isdigit()] if scan else []
    except OSError:
        entries = []
    for pid in entries:
        comm = _comm(proc, pid)
        if comm and AGENTS.get(comm) and _mine(proc, pid):
            return dict(running=True, name=comm, pid=int(pid), words='Permission prompts are answered by %s (process %s).' % (AGENTS[comm], pid))
    if said.isdigit():
        return dict(running=False, name=None, pid=None, words='The permission prompt agent started with this session (process %s) has ended. ' % said + NONE_HERE)
    return dict(running=False, name=None, pid=None, words=NONE_HERE)
