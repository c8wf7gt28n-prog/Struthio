# What's new in Graphite 0.6.1

November 13, 2026. Guide → What's New opens this page. The 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.9, 0.4.8, 0.4.7, 0.4.6,
0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came before.

## The first journey: Stacy starts you in Godot

"It would be fun to ask her to get me started on a project in a program that I may not be particularly familiar with.
I get a starting point in that program, and then I can work from within Graphite for basic operations, or the actual
program window."

Say to her: **start a Godot project called Lander**. (Also: "get me started in Godot", "make me a game in Godot named
Lander".)

1. **She makes the starting point.** A folder `Lander` in Files with the smallest project that runs: `project.godot`,
   one scene (`main.tscn`: a node with a line of words on it), one script (`main.gd`: it sets the words and moves them
   with the arrow keys), and `START_HERE.md`, a page of the first five minutes in Godot. With her hand at Do and show
   or Free hand it is made at once; at Ask first the folder and its four files are listed and wait for one Approve.
2. **The files are written for the Godot on this computer.** Godot 3 and Godot 4 do not read each other's projects.
   She asks the engine itself which it is. With no Godot installed she writes for Godot 3, because that is what Debian
   13 installs (the package `godot3`).
3. **Graphite reads it back.** The Godot room's own inspection says what it found: the project's name and its main
   scene.
4. **Opening it in Godot** is put up as a step. It waits for your Approve; with a Free hand she opens it herself. If
   Godot is not on the computer she says so, names the Debian package, and the project waits in Files.
5. **From Graphite**: "Read the first steps", "Read main.gd here" and "The Godot room" are words on her card. The
   room inspects the project, opens it in Godot, or plays a scene without the editor.
6. **One act, one Undo.** It is one line in her trail. Undo moves the whole folder to the Trash, which gives it back.
   She does not write over a folder that is already there: she asks for another name.

### The Godot room now finds Debian's Godot

The room looked for a program called `godot4` or `godot`. Debian 13's package is Godot 3.6 and its program is
`godot3`, so on the ThinkPad the room would have said Godot was unavailable with Godot installed. It now looks for
all three.

## What was checked, and what was not

The starting files were run in real engines, without a screen, in the build container: **Godot 3.5.2** (the package
of the container's own system; the ThinkPad's Debian 13 has 3.6, the same major version) and **Godot 4.3** (Godot's
own download). In both the scene loads, the script runs and sets the line of words, and the project's name and main
scene are read from its settings. The probe that runs the real window also takes the folder Graphite itself wrote and
runs it in Godot 3. Eleven tests cover the words that ask for a start, which Godot is found, the files for each
version, the Godot room reading them, and (where an engine that runs without a screen is installed) a run in it.

Not done, and not claimed: Godot's own editor window was never opened (there is no screen in the container): opening
and playing were checked only as far as the command Graphite would start. Nothing later than 0.4.6 has run on the
ThinkPad, and whether Godot is installed there is not known to the builder. Only Godot is built: Inkscape, FreeCAD,
Blender and GIMP starts are not. "Work from within Graphite" is, for now, reading the files and the room's three
actions: Graphite does not yet edit a scene.

Asked of the owner: which program next, and whether Godot on the ThinkPad is Debian's Godot 3 or a Godot 4 download.
