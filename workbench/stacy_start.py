"""Stacy starts a project in another program: a starting point that runs, made in Files, to carry on from there or here.

The owner, 13 November 2026: "it would be fun to ask her to get me started on a project in a program that I may not be
particularly familiar with. I get a starting point in that program, and then I can work from within Graphite for basic
operations, or the actual program window."

The first program is Godot. "Start a Godot project called Lander" makes a folder in Files with the smallest project that
runs: the project file, one scene, one script, and a page of first steps. The files are written for the Godot that is on
this computer: Debian 13 ships Godot 3 (the package godot3); Godot's own download is Godot 4, and the two do not read
each other's projects. Both sets below were run in the real engines before they were written here (Godot 3.5.2 and Godot
4.3, headless: the scene loads, the script runs and sets the label).

Nothing here touches Files or starts anything: it answers "was a start asked for", "which Godot is here" and "what are the
files". The window makes them through the owner's own operations, under Stacy's hand (shell2.SlateFace.start_asked).
"""
from .assistant_identity import named
import re
import shutil
import subprocess
import time

PROGRAMS = {'godot': 'Godot'}
GODOT_COMMANDS = ('godot4', 'godot', 'godot3')      # Godot's own builds; Debian's Godot 4 (unstable); Debian 13's Godot 3
DEBIAN_SHIPS = 3                                    # the Godot a Debian 13 computer gets from its own packages
# A start is asked for by naming a project or a game, or by "get me started in Godot". A bare "start with Godot" is not
# one: it may mean "begin with that one".
ASK = re.compile(r'^\s*(?:please\s+)?(?:(?:get\s+me\s+started|start|begin|set\s+up|make|create)\s+(?:me\s+)?(?:on\s+|with\s+)?(?:a\s+|an\s+)?(?:new\s+|first\s+)?'
                 r'(?:(?P<a>godot)\s+(?:project|game)|(?:project|game)\s+(?:in|with|for)\s+(?P<b>godot))|get\s+me\s+started\s+(?:in|with|on)\s+(?P<c>godot))'
                 r'(?:\s*,?\s*(?:called|named)\s+(?P<name>.+?))?\s*[.!]?\s*$', re.IGNORECASE | re.DOTALL)
# What follows a name and is not part of it: a courtesy, or the next thing asked ("... called Lander, please", "... and open it").
AFTER = re.compile(r'(?:\s*,?\s*(?:please|for\s+me|thanks|thank\s+you))+\s*[.!]?\s*$|\s*,?\s+(?:and|then)\s+(?:then\s+)?(?:open|play|run|start|show|launch)\b.*$', re.IGNORECASE | re.DOTALL)
RESERVED = ('slate', 'egress', 'exports', '.trash', '.versions')      # folders of Files that Graphite keeps for itself (files_service)
QUOTES = '“”"\'‘’ '


def asked(text):
    """“Start a Godot project called Lander”, “get me started in Godot”, “make me a game in Godot named Lander”: (program,
    name) or None. With no name given the project is called “First Godot project”."""
    found = ASK.match(str(text or ''))
    if not found:return None
    program = (found.group('a') or found.group('b') or found.group('c')).lower()
    given = found.group('name') or ''
    quoted = re.match(r'^\s*[“"]([^“”"]+)[”"]', given)      # a name in quotes is the whole of what is between them
    name = quoted.group(1) if quoted else AFTER.sub('', given)
    name = re.sub(r'\s+', ' ', name).strip().strip(QUOTES).rstrip('.').strip() or 'First %s project' % PROGRAMS[program]
    return program, name


def reserved(path):
    """Whether a path in Files begins with a folder Graphite keeps for itself."""
    first = str(path or '').replace('\\', '/').strip('/').split('/', 1)[0].strip().casefold()
    return first in RESERVED


def folder_name(name):
    """A folder name for the project: its own name, without what a folder name cannot hold."""
    kept = re.sub(r'[\\/\0:*?"<>|]+', ' ', str(name)).strip().strip('.')
    kept = re.sub(r'\s+', ' ', kept)[:60].strip()
    return kept or 'Godot project'


def _answer(command, **kw):
    """What a command prints, waiting three seconds at most; whatever it started is ended with it (a launcher that
    ignores --version and opens the editor must not be left running, nor hold the window)."""
    import os
    import signal
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:out, err = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid, signal.SIGKILL)
        except OSError:process.kill()
        process.communicate();raise
    return type('Answer', (), {'stdout': out, 'stderr': err})()


def godot_major(executable, run=_answer):
    """3 or 4, from what the engine itself answers to --version; None when it does not answer."""
    try:
        said = run([executable, '--version'], capture_output=True, text=True, timeout=3)
        found = re.search(r'(\d+)\.\d+', (said.stdout or '') + (said.stderr or ''))
        return int(found.group(1)) if found and int(found.group(1)) in (3, 4) else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def godot_tool(which=shutil.which, major=godot_major):
    """The Godot on this computer: {'available', 'command', 'executable', 'major'}. With none, the files are written for
    the Godot this system's own packages would install."""
    for command in GODOT_COMMANDS:
        executable = which(command)
        if executable:
            return {'available': True, 'command': command, 'executable': executable, 'major': major(executable) or (3 if command == 'godot3' else 4)}
    return {'available': False, 'command': '', 'executable': '', 'major': DEBIAN_SHIPS}


def _quoted(name):
    """A name inside double quotes, for Godot's settings, scenes and scripts: a backslash, a quote and a line break are
    written as their escapes, and any other control character is left out, so a name can never end its own string."""
    import unicodedata
    text = str(name).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    # Control characters and the invisible marks that steer the direction of text are left out: Godot 4 refuses a script
    # with a raw direction mark inside a string.
    return '"' + ''.join(ch for ch in text if unicodedata.category(ch) not in ('Cc', 'Cf')) + '"'


def godot_files(name, major):
    """[(file name, text)] for the smallest Godot project that runs: the project file, one scene and one script."""
    words = _quoted(name)
    script = ['extends Node2D', '', named('# Started by Stacy in Graphite. This script runs when the scene starts.'),
              '# The words on the screen are the Label node; the arrow keys move them.', '', 'var speed = 200.0', '', '',
              'func _ready():', '\t$Label.text = %s' % _quoted(name + ': it runs. Change this line in main.gd.'), '', '',
              'func _process(delta):', '\tvar direction = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")']
    if major == 4:
        project = ['; Engine configuration file.', named("; Started by Stacy in Graphite. Godot rewrites this file when you change the project's settings."), '',
                   'config_version=5', '', '[application]', '', 'config/name=' + words, 'run/main_scene="res://main.tscn"', '',
                   '[display]', '', 'window/size/viewport_width=960', 'window/size/viewport_height=540']
        scene = ['[gd_scene load_steps=2 format=3]', '', '[ext_resource type="Script" path="res://main.gd" id="1"]', '',
                 '[node name="Main" type="Node2D"]', 'script = ExtResource("1")', '', '[node name="Label" type="Label" parent="."]',
                 'offset_left = 40.0', 'offset_top = 40.0', 'offset_right = 640.0', 'offset_bottom = 70.0', 'text = ' + words]
        script.append('\t$Label.position += direction * speed * delta')
    else:
        project = ['; Engine configuration file.', named("; Started by Stacy in Graphite. Godot rewrites this file when you change the project's settings."), '',
                   'config_version=4', '', '[application]', '', 'config/name=' + words, 'run/main_scene="res://main.tscn"', '',
                   '[display]', '', 'window/size/width=960', 'window/size/height=540']
        scene = ['[gd_scene load_steps=2 format=2]', '', '[ext_resource path="res://main.gd" type="Script" id=1]', '',
                 '[node name="Main" type="Node2D"]', 'script = ExtResource( 1 )', '', '[node name="Label" type="Label" parent="."]',
                 'margin_left = 40.0', 'margin_top = 40.0', 'margin_right = 640.0', 'margin_bottom = 70.0', 'text = ' + words]
        script.append('\t$Label.rect_position += direction * speed * delta')
    return [('project.godot', '\n'.join(project) + '\n'), ('main.tscn', '\n'.join(scene) + '\n'), ('main.gd', '\n'.join(script) + '\n')]


def first_steps(name, major, tool, now=None):
    """The page that goes with the project: what the files are, the first five minutes in Godot, and what Graphite does."""
    sprite = 'Sprite2D' if major == 4 else 'Sprite'
    here = ('Godot %d is on this computer (%s).' % (major, tool['command']) if tool.get('available') else
            'Godot was not found on this computer when this was made. On Debian it is the package godot3 (Godot 3), '
            'which is what these files are written for.')
    lines = ['# %s: start here' % name, '',
             named('Stacy started this Godot %d project in Graphite on %s. It runs as it is.') % (major, time.strftime('%d %B %Y', time.localtime(now)).lstrip('0')), here, '',
             '## What is here', '',
             '- `project.godot`: the project itself. Godot rewrites it when you change a setting; leave it to Godot.',
             '- `main.tscn`: the one scene: a node called Main with a Label under it.',
             "- `main.gd`: the script on Main. It sets the Label's words and moves them with the arrow keys.", '',
             '## The first five minutes in Godot', '',
             '1. Open the project. From Graphite: Apps, Godot, choose this `project.godot`, then Open in Godot.',
             '2. Press the Play button at the top right. A window opens with one line of words; the arrow keys move it. Close the window.',
             '3. In the Scene panel at the left, click Label. Its properties are in the Inspector at the right: change Text there.',
             '4. Click the script mark beside Main to open `main.gd`. Change the number after `speed`, save, and play again.',
             '5. Add something of your own: right-click Main, Add Child Node, choose %s, and drag a picture onto its Texture.' % sprite, '',
             '## From Graphite', '',
             '- `main.gd` and `main.tscn` are plain text: they open here, and Find works in them.',
             '- Apps, Godot inspects the project, opens it in Godot, or plays a scene without the editor.',
             named('- To be rid of it, delete the folder; DELETE gives it back. While it is still as Stacy made it, Undo on her card does that.'), '',
             'A Godot 3 project and a Godot 4 project are not the same files: this one is for Godot %d.' % major]
    return '\n'.join(lines) + '\n'


def start_files(name, tool, now=None):
    """Everything a start makes, as [(file name, text)]: the project's three files and the page of first steps."""
    major = tool.get('major') or DEBIAN_SHIPS
    return godot_files(name, major) + [('START_HERE.md', first_steps(name, major, tool, now))]
