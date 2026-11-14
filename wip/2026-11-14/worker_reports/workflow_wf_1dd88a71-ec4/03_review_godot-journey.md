{
 "findings": [
  {
   "file": "workbench/shell2.py",
   "line": 2154,
   "severity": "medium",
   "title": "The Undo for a started Godot project trashes the folder as it is now, however much of the owner's work is in it, with no check and (from the trail) no word of where it went",
   "failure_scenario": "Hand at the default 'Do and show'. Say \"start a Godot project called Lander\". Work in Godot for a week (new scenes, art, edits to main.gd). The act stays in her trail (40 acts, saved in the session, restored on restart). Open \"What she did\u2026\" and click \"Undo this\" beside \"Started a Godot 3 project \u00b7 \u201cLander\u201d\" (or the Undo still on the card): the line run is /files.trash {\"path\": \"Lander\"}, so the whole folder with all the owner's later work is moved out of Files in one unconfirmed click. From the trail she only says \"Taken back: Started a Godot 3 project \u00b7 \u201cLander\u201d.\" (result has no 'words', so the Trash is not mentioned) and the tree is not rebuilt. The same line also hits a different thing if the owner renamed the project and put something else at \"Lander\". This contradicts undo_staged's own docstring (\"If what she changed was changed again since, the Kernel refuses and nothing is touched\") and takes_back's \"Only what can be put back as it was is offered\"; field.set's Undo is bound to expected_revision, this one is bound to nothing. Recoverable from the Trash, but nothing checks or asks.",
   "evidence": "shell2.py 2154-2155: undo = '/files.trash ' + json.dumps({'path': folder}, ...); card.entry = stacy_hand.record(state, 'Started a Godot %d project \u00b7 \u201c%s\u201d' ..., card.plan[0][1].line, undo, word, True)\nshell2.py 2088-2092 (undo_entry): r = self.run_line(entry['undo']) ... card = self.say(('Taken back: %s. ' % entry['words']) + str(result.get('words') or ''))\nshell2.py 2033-2034 docstring: \"If what she changed was changed again since, the Kernel refuses and nothing is touched.\"\nfiles_service.py 504-510 (files.trash) moves whatever is at the path; no hash or listing is compared.",
   "suggested_fix": "Bind the Undo to what she wrote: before trashing, list the folder and compare it with the four files and their sha256 from the start; if anything was added or changed, do not trash by herself (say so and leave it to the owner, or ask). In undo_entry say that the folder is in the Trash and rebuild the tree (made_done)."
  },
  {
   "file": "workbench/stacy_start.py",
   "line": 24,
   "severity": "medium",
   "title": "ASK takes everything after 'called' as the name, so a polite or continued sentence makes a wrongly named project at once; and bare 'start with Godot' / 'Start in Godot.' is taken as a request",
   "failure_scenario": "Hand at the default 'Do and show'. Type \"start a Godot project called Lander, please\": she immediately makes the folder \"Lander, please\" with config/name=\"Lander, please\" and that label text. Likewise \"\u2026 called Lander for me\" -> \"Lander for me\", \"\u2026 called Lander and open it\" -> \"Lander and open it\" (the 'open it' is silently dropped into the name). And \"Start with Godot.\" / \"begin with godot\" / \"Start in Godot.\" (which can mean 'begin with that one' or 'run it in Godot') make a folder \"First Godot project\" at once. Each needs an Undo and a re-ask; a leading 'please' is handled, a trailing one is not.",
   "evidence": "Ran stacy_start.asked():\n'start a Godot project called Lander, please' -> ('godot', 'Lander, please') | folder: 'Lander, please'\n'Start a Godot project called Lander for me' -> ('godot', 'Lander for me')\n'start a Godot project called Lander and open it' -> ('godot', 'Lander and open it')\n'start with Godot' -> ('godot', 'First Godot project')\n'Start in Godot.' -> ('godot', 'First Godot project')\n'make with godot' -> ('godot', 'First Godot project')",
   "suggested_fix": "After the name allow and drop a trailing ', please' / 'please' / 'for me' (as the leading please is dropped), and do not swallow ' and \u2026' into the name (stop there, or let the sentence fall through to the model). Keep the bare '(in|with) godot' form only for 'get me started'; 'start/begin/make/create with Godot' without project/game should not act by itself."
  },
  {
   "file": "workbench/shell2.py",
   "line": 2129,
   "severity": "low",
   "title": "A project called \"Exports\" passes the 'already there' check, every step reports done, and the four files end up loose in Files/Egress with no project folder and an Undo that cannot work",
   "failure_scenario": "Say \"start a Godot project called Exports\" (any hand; at 'show' it runs at once). 'Exports' is the old name of Egress: files_service.root() runs locations.move_once(Files/Exports, Files/Egress) on every call. files.get finds nothing, files.mkdir makes Files/Exports and the very next root() call removes it as empty; each files.write recreates it, writes the file, and entry()->rel_of()->root() sweeps the file into Files/Egress. All five results are ok, so started() records the act with Undo /files.trash {\"path\": \"Exports\"} (which fails FILES_NOT_FOUND when clicked), says \"\u201cExports\u201d is in Files and runs as it is. The Godot room could not read it: MISSING_SOURCE: Exports/project.godot.\", and project.godot, main.tscn, main.gd, START_HERE.md lie loose in Egress, the folder files leave from.",
   "evidence": "Ran the same operations start_asked builds (files.get, files.mkdir, 4 x files.write via files_service.dispatch) on a scratch workspace with name 'Exports':\nfolder 'Exports'\nfiles.get (False, 'ValueError: FILES_NOT_FOUND: Exports')\nmkdir True\nwrite project.godot True Exports/project.godot\nwrite main.tscn True Exports/main.tscn\nwrite main.gd True Exports/main.gd\nwrite START_HERE.md True Exports/START_HERE.md\nFiles ['.trash', '.versions', 'Egress', 'Slate'] []\nFiles/Egress [] ['START_HERE.md', 'main.gd', 'main.tscn', 'project.godot']\n(files_service.py 81: locations.move_once(base / OLD_EXPORTS, base / EXPORTS))",
   "suggested_fix": "Refuse in start_asked (or in folder_name) the names Files keeps for itself: 'Slate', 'Egress', 'Exports', '.trash', '.versions' (and 'Received'); and after the plan ran, confirm files.get(folder + '/project.godot') before saying it is in Files and before recording an Undo. files.mkdir at the root should refuse OLD_EXPORTS too."
  },
  {
   "file": "workbench/shell2.py",
   "line": 2150,
   "severity": "low",
   "title": "When a start stops part-way, an act of hers leaves no line in her trail and no Undo, and when the first step is refused she tells the owner to trash a folder she did not make",
   "failure_scenario": "(a) Hand at 'Ask first': say \"start a Godot project called Lander\" twice (two waiting cards), approve both. The second run's files.mkdir is refused (FILES_EXISTS), nothing was made by it, yet she says \"What was made before it is in \u201cLander\u201d in Files; move it to the Trash if you do not want it\" \u2014 pointing at the good project from the first card. Same sentence when a dangling link of that name is in Files. (b) Hand at 'Do and show', the disk fills after the folder is made (files.mkdir ok, a files.write fails with ENOSPC): the folder and whatever was written stay in Files, but because card.one_entry suppresses run_plan's per-step lines and started() returns before stacy_hand.record, \"What she did\u2026\" has no line for it and there is no Undo, against stacy_hand's rule that each act of hers is one line in her trail.",
   "evidence": "shell2.py 2150-2152:\nif sum(1 for _, ok, _ in results if ok) < len(card.plan):\n    self.made_done(False, None)\n    self.say('I stopped at the step that was refused. What was made before it is in \u201c%s\u201d in Files; move it to the Trash if you do not want it.' % folder);return\nshell2.py 2325: if getattr(card, 'hers', False) and not getattr(card, 'one_entry', False): ... stacy_hand.record(...)   (skipped because start_asked sets card.one_entry = True at 2140)",
   "suggested_fix": "If the first result is a refusal say that nothing was made. If she ran it herself and at least the folder was made, record the act in the trail (marked as stopped) with the same folder-to-Trash Undo."
  },
  {
   "file": "workbench/shell2.py",
   "line": 2435,
   "severity": "low",
   "title": "With a sheet selected in the Field, a start whose name holds a number is swallowed by set_asked, which runs before start_asked",
   "failure_scenario": "The Field is in front with a sheet (or calculation) that has numbers selected. Type \"make a Godot game called 2048\" or \"set up a Godot project called Lander 2\". set_asked matches ^(set|change|make)\\b, finds the last number token ('2048' / '2'), finds no cell named 'godot game called', and answers \"Say which number and its new value, for example \u201cset B3 to\u201d and a number. The numbers here are in \u2026\" and returns True; start_asked is never reached, so the project cannot be started from that state with those words.",
   "evidence": "shell2.py 2434-2437: if self.own_word(text):return / if self.set_asked(text):return / if self.start_asked(text):return / if self.made_asked(text):return\nshell2.py 2411: asked = re.match(r'^\\s*(?:set|change|make)\\b(.*)$', text, ...) ; 2420-2421: at = last token matching -?\\d+(\\.\\d+)? ; if not names or at is None:return False ; 2426-2428: cell is None -> self.say('Say which number and its new value ...');return True\nstacy_start.asked('make a Godot game called 2048') -> ('godot', '2048'); asked('set up a Godot project called Lander 2') -> ('godot', 'Lander 2')",
   "suggested_fix": "Ask start_asked (and made_asked) before set_asked, or have set_asked return False when stacy_start.asked(text) / stacy_hand.made(text) recognises the sentence."
  },
  {
   "file": "workbench/stacy_start.py",
   "line": 50,
   "severity": "low",
   "title": "godot_tool() runs '<godot> --version' in the window's own thread with an 8 s timeout; a launcher that does not pass its arguments on freezes the window for 8 s on every start and is left running",
   "failure_scenario": "The 'godot' on PATH is a hand-made launcher that ignores its arguments (for example a two-line sh script that runs ~/Godot/Godot_v4.3-stable_linux.x86_64 without \"$@\"). \"start a Godot project called Lander\" calls stacy_start.godot_tool() from start_asked before any card is shown: the window is frozen for the full 8 seconds, only the shell is killed at the timeout so the Godot window it opened stays, and the files are then written for Godot 4 by the command's name alone (wrong if that launcher starts Godot 3). stdin is also inherited rather than closed.",
   "evidence": "stacy_start.py 50: said = run([executable, '--version'], capture_output=True, text=True, timeout=8)   called from shell2.py 2131 (tool = stacy_start.godot_tool()) on the GUI thread.\nRan godot_tool(which=...) against a scratch script '#!/bin/sh\\nsleep 21.37':\ntook 8.0 s 4 True\n5149 sleep 21.37      (the launcher's child still running after the call returned)",
   "suggested_fix": "Give the probe a short timeout (1-2 s), stdin=subprocess.DEVNULL and start_new_session=True with a kill of the whole group on timeout; cache the answer per executable path and mtime so it is asked once, not on every start."
  },
  {
   "file": "workbench/stacy_start.py",
   "line": 121,
   "severity": "low",
   "title": "START_HERE.md promises an Undo on her card that does not exist when the owner approved the start",
   "failure_scenario": "Hand at 'Ask first'. Say \"start a Godot project called Lander\" and press \"Approve all 5\". card.hers is False, so started() adds no Undo button and no trail line, yet the page just written into the project says \"The whole folder was one act of Stacy's: Undo on her card moves it to the Trash, which gives it back.\" The owner looks for an Undo that is not there. (The same page text is written when the start stops part-way, where there is no Undo either.)",
   "evidence": "stacy_start.py 121: \"- The whole folder was one act of Stacy's: Undo on her card moves it to the Trash, which gives it back.\"\nshell2.py 2153-2157: the Undo button and the trail entry are made only inside `if card.hers:`; start_files() is built at 2131 before it is known who runs the plan.",
   "suggested_fix": "Pass whether the start is hers into first_steps and write the Undo sentence only then; otherwise say the folder can be moved to the Trash from Files."
  },
  {
   "file": "workbench/stacy_start.py",
   "line": 71,
   "severity": "low",
   "title": "_quoted keeps invisible text-direction marks, which Godot 4's GDScript refuses inside a string, so main.gd does not parse for such a name (Godot 3 is fine)",
   "failure_scenario": "Godot 4 is the engine on the computer. The owner types or pastes a right-to-left name carrying a direction mark, for example \"start a Godot project called \u200f\u05e9\u05dc\u05d5\u05dd\" (U+200E/U+200F, U+202A-202E and U+2066-2069 come with Hebrew/Arabic keyboards and with text copied from chat programs). asked() keeps the mark (it is not whitespace), _quoted keeps it (it is >= ' '), and main.gd gets $Label.text = \"\u200f\u05e9\u05dc\u05d5\u05dd: it runs. \u2026\" with the raw character. Godot 4's tokenizer reports raw bidi control characters in a string literal as an error (\"Invisible text direction control character present in the string, escape it (\"\u200f\") to avoid confusion.\"), so the script fails to load and \"it runs as it is\" is not true. Not run here: only Godot 3.5.2 (godot3-server) is on this machine, and it accepts the same files, so this rests on the Godot 4 source (modules/gdscript/gdscript_tokenizer.cpp, string()).",
   "evidence": "stacy_start.py 70-71: text = str(name).replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')... ; return '\"' + ''.join(ch for ch in text if ch >= ' ') + '\"'\nstacy_start.asked('start a godot project called  \u200f\u05e9\u05dc\u05d5\u05dd') -> ('godot', '\u200f\u05e9\u05dc\u05d5\u05dd')\ngodot_files('caf\u00e9 \u200f\u05e9\u05dc\u05d5\u05dd', 4)['main.gd'] contains: \\t$Label.text = \"caf\u00e9 \u200f\u05e9\u05dc\u05d5\u05dd: it runs. Change this line in main.gd.\" (raw U+200F)\nGodot 3.5.2 run of the Godot 3 set with the same name: PROBE: caf\u00e9 \u200f\u05e9\u05dc\u05d5\u05dd: it runs. Change this line in main.gd. (no error)",
   "suggested_fix": "In the script line (at least for major 4) write U+200E, U+200F, U+202A-U+202E and U+2066-U+2069 as \\uXXXX escapes, which GDScript 3 and 4 both read; the scene and project.godot can keep the raw characters."
  }
 ]
}