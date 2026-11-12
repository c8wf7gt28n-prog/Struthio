# What's new in Graphite 0.3.1

November 12, 2026. Guide → What's New opens this page. `docs/RELEASE_NOTES_0.3.md` describes the Field itself.

**Stacy is the assistant.** The owner's words: "Stacy should be the face of the assistant as communicated through the
language of Stacy." In Talk her portrait is beside her name (Illustrated desk; the ASCII desk shows her mark in characters,
the Clean desk her name alone). Wherever you ask, tell or talk to the assistant the words now say Stacy: Ask Stacy about
this, Talk to Stacy. Graphite is still the name of the workspace.

**She answers in staC, with or without a model.** Ask about a sheet of the Field: from its menu (Ask Stacy about this), or
just type a question in the writing strip while the sheet is selected. With no model loaded she no longer stops at "no
model": she shows the staC line that reads that sheet, runs it, and shows what the records say, in Talk. Under the answer:
in the line (to change it), watch it, add to the Agenda, and save as a sheet when there are rows. The Field stays in front
and the keyboard goes back to it on Esc. With a model loaded, the same staC line goes to the model as the subject of the
question.

**With a model she reads first, then says it.** A real small model has now answered inside this desk (rehearsed with
Qwen3.5 at 2B and 4B on a processor; `docs/MODEL_TRIAL_03.md`). For a question about a sheet Stacy runs the staC read herself,
shows the line and the rows, and then asks the model for one thing only: the answer in a sentence or three, from those rows
and from what the Field knows of the sheet. Her words appear under the rows and are marked as the model's. The 2B model
answered in 5 to 10 seconds; planning from the whole desk had taken 27 to 37 and missed the question. In the Field, say
"this" (or it, that, here) and she takes the selected sheet; anything else you type goes the ordinary way.

**Every program, one key away.** Press **P** in the Field. All of Graphite's programs and rooms hang as a shelf in six
columns that do not move: Work, Think, Make, Build, Move, Set up. Arrows move, Enter opens the program's room, and a room
that is open is marked in use. Each has its staC line, and Stacy answers "what can this do?" about it. The six native
programs (Blender, FreeCAD, Godot, Inkscape and the rest) open their Graphite room first; the room's own Open in button
starts the full program.

**Graphite opens on the work.** When the workspace has anything in it, Graphite starts in the Field with what waits for you
selected; Esc goes to where you left off. An empty workspace starts on Home. Home's "Start: always Home" still means Home.
There is no new setting.

**Free software.** Graphite's own code and documents are under the GNU General Public License, version 2 only: `COPYING`
holds the owner's note and the full, unchanged licence text. The owner asked for the source to be handled as Linus Torvalds
would. Kept back, and said in `RIGHTS.md`: Stacy's artwork and the other project art (which may be passed along unchanged
with Graphite, and not otherwise reused), the names Graphite, staC and Stacy, and the copy of STRUTHIO ARCADE. Bundled fonts
and runtimes keep their own licences (`THIRD_PARTY_NOTICES.md`, corrected to list what is really in the tree). About and
the Legal list in the navigator say the same.

**Not done, said plainly.** Nothing here has run on the ThinkPad, and no model has answered inside it: everything was
checked offscreen in a build container. Two small models answered there, on a processor; nothing is measured on the
ThinkPad or its Radeon, and no 27B file was run. The two independent verifiers for this release did not run (a usage limit),
so the licence wording and the new Talk and launch behaviour had one reader, not two. A key that starts a native program in
its full window straight from the shelf is not there yet. The notes in
`COPYING` about libraries and the additional permission were written without a lawyer. The Word copy of the complete
specification still carries the earlier licensing sentence; its Markdown source is corrected. The older test and window
checks that describe the earlier desk still fail as before.
