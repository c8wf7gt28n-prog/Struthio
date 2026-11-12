"""The one place Graphite's version is stated.

Graphite 0.1 is the first release under the name Graphite, the single public name for the workspace and its AI (owner,
2026-11-06). It follows Ledger & Slate 5.1.0a5 and its HATCH checkpoints up to AGENT-02; the history is in the project's git
history and the owner's backups. Internal identifiers keep the earlier names for compatibility: the package's MANIFEST.json
still says product 'Ledger & Slate' (signed updates check it), settings keys, project paths and the per-user data folder
are unchanged.

  python3 -m workbench.version
"""
NAME = 'Graphite'
VERSION = '0.3.1'
SHORT = '0.3.1'
LINEAGE = ('0.3.1: Stacy is the assistant\'s face and answers in staC, reading first and saying it with a small model when one is loaded; the shelf of every program on P in the Field; Graphite opens on the Field when there is work; free software under the GNU GPL version 2 only. '
           '0.3: the Field on F9, an overview of the work and of this computer\'s network as sheets and the wires between them, with the right-click instruments on every sheet and Stacy\'s rail saying each one in staC; the first slice of the objects and instruments desktop. '
           '0.2a13: After Midnight, with Stacy in original ink-and-screentone desk artwork. '
           '0.2a12: After Hours first-boot candidate with the Programs shelf, staC plan inspection and resource observations. '
           '0.2a11: four-volley ThinkPad release with offline setup, a first-run workshop, and forecast-based background admission. '
           '0.2a10: optional fast-forward screensaver with fictional traces and a VHS cutaway. '
           '0.2a9: live charcoal operator in the illustrated desk. '
           '0.2a8 (ThinkPad first install): offline setup, Calc return, selected PDF source rows, Night Shift and a checked shortage method. '
           '0.2a6.post1 (Visual Pass 1 revision): illustrated worksheet, PDF evidence trace and research journal. '
           '0.2a6 (P10 visual refinement): charcoal terminal desk and selected-row worksheets with a live chain preview. '
           '0.2a5 (P08–P10): verified resident model, project collections and reviewed PDF-to-report workflow. '
           '0.2a4 (P07): CPU evidence preparation, exact source-bound calculations and passage follow-up. '
           '0.2a3 (P06): shared-memory admission, foreground turns, serialized inference, cooperative background CPU work and resource readback. '
           '0.2a2 (P05): pinned Vulkan worker, actual host inventory, requested/effective backend readback, bounded CPU fallback and GPU-aware resource guard. '
           '0.2a1 (BOSS M1): native charcoal/copper desk, full editable path, program and command context menus, retained chain preview with source receipts. '
           '0.1 (Graphite): the public rename, the sharpened-point mark, the GRAPHITE startup screen, the peeking cat that opens '
           'the menu, the compact-layout fixes, STRUTHIO ARCADE 1.9.0 desk mode, one release without the history. '
           'Before it, as Ledger & Slate: 5.1 (HATCH checkpoints to AGENT-02: the agent loop, work that continues while the window '
           'is closed, the model\'s page edit, the Finder, Ingress and Egress). '
           '4.9: folder working copies, merging, Slate on an assigned copy, a file story, This Computer. 4.8: connected; the chain menu; one home for each thing. 4.7: working copies with reviewed, recoverable updates to originals. 4.6: staC reads what files contain, Compare, Explain, smart folders and search. 4.5: viewer modules built in (Images+, Spreadsheets, 3D models, DXF drawings, Media, Markdown). 4.4: Files, a Finder-style browser with thumbnails, Trash, versions, Slate\'s area and Export. 4.3: Slate\'s Agenda (Now, Next, Waiting, Later, Done) with nice-style priorities and bounded suggestions. 4.2: pink underlines on graphite words, Arrived and Notes instead of Inbox, Stop turns pink when work looks stuck. 4.1: Paper v1.1 (graphite, pencil and eraser; 16px type, scales to 200%), Jot it down, a slimmer package. 4.0: an independent product (personal projects preserved separately) with continuing investigations. 3.0: Paper, a minimalist redesign. 2.1: the window matches the 2.0 design. 2.0: redesigned around Arrive → Read → Ask → Keep. 1.1: rooms. 1.0: Office, instruction matrix, universal viewer. Development passes P18–P22.')


def title():
    return NAME + ' ' + SHORT


if __name__ == '__main__':
    print(NAME + ' ' + VERSION)
