"""Graphite 1.1.1 C0 · DOS words in the real Terminal: the bash rc the drop-down's terminal starts with, and the line it asks.

PLAN_1.1.md, C0. The drop-down Terminal is a real terminal (xterm, see real_terminal_qt) running the owner's own shell. When
that shell is bash, Graphite starts it as `bash --rcfile <this rc> -i`, and the rc:

  1. reads the owner's own ~/.bashrc first, exactly as any terminal of theirs does (bash reads /etc/bash.bashrc itself).
     Nothing of the owner's is written, moved or edited: the rc is Graphite's own file, made for this terminal only;
  2. binds Enter (and Ctrl+J), in emacs and vi-insert alike, to: ask `answer` below about the line just typed, then accept it.
     A line that is not DOS words (W1's dos_words.translate says None) is left exactly as typed and runs as bash runs it.
     A DOS line is shown as W1 shows it, "dir /s → ls -lR" (above what it prints), and the shell's own line becomes the
     Debian command, which is what runs and what Up brings back: the owner learns it by using it;
  3. binds Ctrl+Alt+Shift+F12 (xterm sends ESC [24;8~) to take in the line the bar's line queued (real_terminal_qt.send, the
     owner's own press on a Terminal or DOS row) as if typed, then Enter as above.

Only the first word is looked at in bash (a DOS word, a word both have, or a drive letter); only then is the translator asked.
A translator that fails leaves the line as typed. The setting (Tools ▸ DOS words) is read at every line: 'on' runs the Debian
command, 'show' (show me only) shows it and runs nothing, 'off' leaves every line to bash.

What is never run stays as W1 decided: del and erase put files in the bin (`gio trash`, the freedesktop.org bin Files shows,
never rm; `del *.*` asks first), format, chkdsk, fdisk and diskpart are explained and not run. Nothing here runs by itself:
every line runs because the owner typed it and pressed Enter in their own terminal; Kasandra's hand never types here.
"""
from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOWN_ONLY = 'Shown only: DOS words are set to "show me only", so nothing was run.'
NOTHING_THERE = 'Nothing there by that name, so nothing went to the bin (del takes files; rd /s takes a folder).'
NO_GIO = ('gio (libglib2.0-bin) is not installed, so nothing went to the bin; Files puts things there too (Delete).')
DIM, PLAIN = '\033[2m', '\033[0m'


def first_words():
    """The first words bash asks about: W1's DOS-only words and the words both have (a drive letter is matched apart)."""
    from workbench import dos_words as dw
    return sorted(dw.DOS_ONLY | dw.BOTH)


def _rel(path, cwd):
    try:
        rel = os.path.relpath(path, str(cwd))
    except ValueError:
        return str(path)
    return str(path) if rel.startswith('..') else rel


def answer(line, cwd, mode=None, places=None, which=shutil.which):
    """What the Terminal does with one line the owner pressed Enter on: {'dos': False} when it is not DOS words (bash runs it as
    typed), else {'dos': True, 'shown': [lines to print above], 'run': the line bash runs instead ('' runs nothing)}."""
    from workbench import dos_words as dw
    if mode is None:
        try:
            from workbench import windows_hand
            mode = windows_hand.dos_words()
        except Exception:  # noqa: BLE001 - the setting unreadable: DOS words stay on, as their default
            mode = 'on'
    if mode == 'off':return {'dos': False}
    said = dw.translate(line, cwd=str(cwd), places=places, which=which)
    if said is None:return {'dos': False}
    shown = [said.shown()]
    if said.words and said.kind != 'help':shown.append(said.words)
    if mode == 'show':return {'dos': True, 'shown': shown + [SHOWN_ONLY], 'run': ''}
    kind = said.kind
    if kind == 'run':run = said.run
    elif kind == 'cd':run = 'cd -- %s' % shlex.quote(said.target)
    elif kind == 'cls':run = 'clear'
    elif kind == 'exit':run = 'exit'
    elif kind == 'env':run = said.command
    elif kind == 'help':shown += said.words.splitlines();run = ''
    elif kind == 'trash':
        files = dw.expand(said, cwd)
        if not files:shown.append(NOTHING_THERE);run = ''
        elif not which('gio'):shown.append(NO_GIO);run = ''
        else:
            run = 'gio trash -- ' + ' '.join(shlex.quote(_rel(f, cwd)) for f in files)
            if said.ask:run = '__graphite_sure %d %s && %s' % (len(files), shlex.quote(str(cwd)), run)
    else:run = ''           # explain: words only
    return {'dos': True, 'shown': shown, 'run': run}


def rc_text(python=None, script=None):
    """The rc (see the module note): the owner's ~/.bashrc, then the Enter binding. `python` and `script` are what bash runs
    to ask about a DOS line (this interpreter and this file, by default)."""
    python = python or sys.executable or 'python3'
    script = script or str(Path(__file__).resolve())
    words = '|'.join(first_words())
    return r'''# Graphite's Terminal (1.1.1 C0): made by Graphite for its drop-down Terminal only. Your own files are not changed.
# Your ~/.bashrc first, as any terminal of yours reads it; then DOS words (dir, copy, del...), which show the Debian command
# they run and leave it in the line's history. Tools > DOS words: off leaves every line to bash as typed.
if [ -f "$HOME/.bashrc" ]; then . "$HOME/.bashrc"; fi
export GRAPHITE_TERMINAL=1
if [ -n "$GRAPHITE_TERMINAL_FONTS" ] && [ "$FONTCONFIG_FILE" = "$GRAPHITE_TERMINAL_FONTS" ]; then unset FONTCONFIG_FILE; fi
unset GRAPHITE_TERMINAL_FONTS
__graphite_dos_enter() {
  local l w out
  l=${READLINE_LINE#"${READLINE_LINE%%%%[![:space:]]*}"}
  w=${l%%%%[[:space:]]*}; w=${w%%%%[/\\.]*}; w=${w,,}
  case "$w" in
    %(words)s) ;;
    [a-z]:) ;;
    *) return 0 ;;
  esac
  out=$(%(python)s -I -B %(script)s "$READLINE_LINE" "$PWD") || return 0
  READLINE_LINE=$out; READLINE_POINT=${#out}
}
__graphite_queued() {
  local f=$GRAPHITE_TERMINAL_QUEUE
  [ -n "$f" ] && [ -s "$f" ] || return 0
  READLINE_LINE=$(<"$f"); : > "$f"; READLINE_POINT=${#READLINE_LINE}
}
__graphite_sure() {
  local a
  read -r -p "$1 in $2. Put them all in the bin? (y/N) " a
  case "$a" in [yY]*) return 0 ;; esac
  echo 'Nothing was done.'; return 1
}
if [[ $- == *i* ]]; then
  for __graphite_map in emacs vi-insert; do
    bind -m "$__graphite_map" -x '"\C-x\C-g\C-d": __graphite_dos_enter'
    bind -m "$__graphite_map" '"\C-x\C-g\C-a": accept-line'
    bind -m "$__graphite_map" '"\C-m": "\C-x\C-g\C-d\C-x\C-g\C-a"'
    bind -m "$__graphite_map" '"\C-j": "\C-x\C-g\C-d\C-x\C-g\C-a"'
    bind -m "$__graphite_map" -x '"\C-x\C-g\C-q": __graphite_queued'
    bind -m "$__graphite_map" '"\e[24;8~": "\C-x\C-g\C-q\C-x\C-g\C-d\C-x\C-g\C-a"'
  done
  unset __graphite_map
fi
''' % dict(words=words, python=shlex.quote(python), script=shlex.quote(script))


def write_rc(folder, python=None, script=None):
    """The rc written into `folder` (Graphite's own, 0700) as graphite-terminal.bashrc; its path."""
    folder = Path(folder);folder.mkdir(parents=True, exist_ok=True)
    try:os.chmod(folder, 0o700)
    except OSError:pass
    path = folder / 'graphite-terminal.bashrc'
    path.write_text(rc_text(python, script), encoding='utf-8')
    return path


def main(argv=None):
    """bash's question (the rc's Enter): argv = [the line, the folder]. A DOS line: the shown lines go to the terminal (stderr,
    over the typed line) and the line to run to stdout, exit 0. Not DOS, or anything wrong: exit 1, and bash runs it as typed."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:return 1
    try:
        said = answer(argv[0], argv[1])
    except Exception:  # noqa: BLE001 - the translator never eats the owner's line
        return 1
    if not said.get('dos'):return 1
    err = sys.stderr
    err.write('\r\033[K' + '\n'.join(DIM + s + PLAIN for s in said['shown']) + '\n');err.flush()
    sys.stdout.write(said['run']);sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
