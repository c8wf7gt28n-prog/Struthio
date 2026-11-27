# Scout: what Kas can really do today, and where she stops

27 November 2026. Read from the code of 1.0 (not the guide) and from runs on a throwaway copy of the tree, with no model,
on the Everyday Home (`python -m workbench.everyday_demo`). Scripts and raw output are beside this file in `today/`
(`scripts/kas_*.py`, `out/*.jsonl`, `out/*.out`). The copy of the tree was deleted after the runs.

What I ran, and what I did not:

- Ran: 56 plausible requests through three real entry points: the Kernel's `requests.read` (her dictionary), the Kernel's
  `objective.plan` (the desk's planner), and the real ask line of her column (`shell2.SlateFace.ask`) in Graphite's own
  window, offscreen, with a wrapper that records which route took the words and what she said.
- Not run: any model. What a model would be offered is read from the code and from the planning question as the code
  builds it (`out/plan_question.out`). The model's behaviour itself is from the saved logs of the 4B (K10, X3, X4).
- This container has no system D-Bus, no X display and no AT-SPI, so the Machine sections, the window tools and her hand
  in other programs said "not available" here. That is the container, not a finding about the ThinkPad.

---

## 1. The short answer

On an ordinary home folder with no model, **4 of 56 requests were done or planned, 1 partly, 1 was done wrongly, 6 were
refused with a reason, and 44 got the same sentence: "I have no brain running yet. Drop a GGUF model on the Brain room, or
choose one."** (`shell2.py:2908`).

The four that work are the four that were hand-built for the walkthroughs: the groceries total, the tidy of a folder, a
question to a manual in one of five sentence shapes, and `run df -h`.

Three things explain almost all of it, and none of them is the model's size:

1. **Her verbs are few and are regular expressions.** A typed request is tried against a chain of about twelve fixed
   patterns (`shell2.py:2839-2862`). The desk's planner knows ten verbs (`objective_plan.py:149-158` plus three added by
   hooks). Nothing reads "open", "move", "copy", "list", "find", "delete", "install", "play", "print", "convert".
2. **Most of her 32 tools cannot be reached by words.** The tools exist and verify their effects, but a typed request with
   no model can reach about a dozen of them, and with a model the planning question on a home folder offers seven
   (`out/plan_question.out`).
3. **There is nothing registered for system work at all.** Of the Kernel's 923 operations, the `machine` namespace holds
   one, and it is a read (`machine.state`). Volume, Wi-Fi, mounting, default apps and power are functions the window calls on the
   owner's press, written so that she cannot call them (`machine_real.py:24-26`). There is no package, service, user or
   schedule operation. `sudo` and `pkexec` are refused by name in three launchers.

A fourth, for the model path: **a model is asked to plan only when the words already contain one of the planner's own
verbs** (`objective_plan.py:222-228`, called from `objective_plan_qt.py:48`). "Move the bank statements from Downloads into
Documents" never reaches the model's planning question, although the question, once built, would let the model answer
`6 D4 D1` correctly.

---

## 2. How a typed request travels

`shell2.SlateFace.ask` (`shell2.py:2839`). Each route is a pattern; the first that matches takes the words.

| Order | Route | Takes | Where |
|---|---|---|---|
| 1 | her own words | a staC word the owner kept; `word NAME = LINE` | `shell2.py:2785` |
| 2 | the Library | "ask the library …", "what does my library say about …" | `library_qt.py:66-68` |
| 3 | the web | "look up …", "search the web for …", "fetch <address>" | `network_governed.py:252` |
| 4 | spending | "what/how much did we spend on X this month / last month / in <month>" | `everyday_desk.py:39` |
| 5 | a document's pages | five shapes: "what does X say about Y", "is there anything in X about Y", "does X mention Y", "which page of X covers Y", "look in X for Y" | `home_pages.py:54-62` |
| 6 | start a project | "start a Godot project called …" | `stacy_start.py:36` |
| 7 | make a thing | "make/create/write a folder, file, page or note called …" (in the workspace's Files) | `stacy_hand.py:347` |
| 8 | set a cell | "set B3 to 300", with a sheet selected on the Field | `shell2.py:2813` |
| 9 | a command | "run <one read-only command>" from a list of 32 | `shell2.py:2592`, `stacy_hand.py:81` |
| 10 | a review | "review this assembly …" | `desk_review.py:26` |
| 11 | an objective | words that hold a planner verb with an object, or two clauses of planner verbs | `objective_plan.py:222` |
| 12 | her hand on the desk | trace, compare, show … and only when the desk has sheets (`shell2.py:2643`) | `shell2.py:2632` |
| 13 | no model | "I have no brain running yet …" | `shell2.py:2908` |
| 13 | a model | the pre-1.0 free question (`brain.ask`, mode plan): JSON of a text and up to three operations, with the instruction "Keep text under 120 characters and prefer one action" | `local_brain.py:911-925` |

Two things in this chain matter for the design:

- **Her 0.8.6 dictionary (`reading.py`) and the model's READ question (`understand.py`) are not on this chain for a home
  folder.** They are reached only through route 12, which returns at once when the desk has no sheets
  (`shell2.py:2643`). On the Everyday Home `requests.read` answered NONE for 50 of 56 requests, and for three it found
  only a calendar word ("yesterday", "Friday", "tomorrow") and asked "Which of these did you mean?"
  (`out/dictionary.out`).
- **With a model, a general question falls into the oldest path in the program**, written for a 1.5B model in 0.6: one
  JSON answer whose text is asked to stay under 120 characters. "What does chmod 644 mean" would be answered there.

---

## 3. Every registered tool

32 tools (`tools.list` returned 32): 1 to 27, 31 to 35. A kept utility takes a number from 101. "Words reach it" is from
the code of the two planners and the ask chain.

| # | Key | Reads or changes | Verified by | Grant | Words reach it, no model | On the model's plan menu |
|---|---|---|---|---|---|---|
| 1 | kernel.read | reads a record by any of 471 registered reads | read again: same revision | none | "read / check" a sheet, page or calculation on the desk | yes |
| 2 | files.read | reads a file in Files | digest same before and after | none | no | yes (a document in Files) |
| 3 | files.write.new | a new file | digest on disk | write a new file in the folder | "write a note" (only of checked values, in her own area); route 7 | yes (same note) |
| 4 | files.write.revision | a new revision, old one kept | new digest on disk | change a file in the folder | **no planner builds it** | no |
| 5 | files.rename | renames, identity kept | same digest at new name, old gone | rename files in the folder | "rename X to Y", X a document in Files only | yes, a Home file, when the words say rename |
| 6 | files.move | moves | same digest in folder, gone from old place | move files | only inside "tidy" and "put … back" | yes |
| 7 | files.folder.new | makes a folder | the folder is there | make folders | only inside "tidy"; route 7 (Files only) | yes |
| 8 | calculation.recheck | a new calculation page | new page, exact result | marked for approval | "recheck / recompute" | yes |
| 9 | sheet.set | a cell of a desk sheet | sheet read again | set values | route 8 (her hand) | no |
| 10 | desk.navigate | what Graphite's window shows | read.desk | the dial | route 12 (30 desk acts) | never a step |
| 11 | desk.change | write, rename, bin, cell through her hand | as the operation's own | the act's own | route 7, 8 | never a step |
| 12 | windows.observe | reads the window list | X11 properties now | none | no | no |
| 13 | windows.activate | brings a window forward | fresh look: active | arrange windows | no | no |
| 14 | windows.minimise | minimises | fresh look | arrange windows | no | no |
| 15 | windows.close | polite close | fresh look: gone | marked for approval | no | no |
| 16 | apps.open | starts an App, with files | its window appears | open the App | **no** | **no** |
| 17 | machine.state | reads storage, power, network, sound, screens | read now from its service | none | **no** | yes ("17") |
| 18 | office.read | reads .odt/.ods through LibreOffice (or directly) | saved file read back | none | "read" a Files document; route 4 | yes |
| 19 | office.edit | replaces a passage (.odt), sets a value cell (.ods) | saved file read back | edit the document; approval | "update <report>" after a recheck | yes |
| 20 | sandbox.run | runs a drafted utility on copies | outputs and difference read back | run on copies | no (Tools menu) | no |
| 21 | accessibility.read | reads a program's window, a dialog | the tree, read now | none | no (automatic dialog watch) | no |
| 22 | network.fetch | a request leaves; page into quarantine | bytes and digest from quarantine | your press; a site grant for a typed address | route 3; **as a plan step always refused** (`objective_plan.py:657-660`) | no |
| 23 | page.update | a Graphite page, one sentence | page read again | change a page | "update <page>" after a recheck | yes |
| 24 | files.list | lists a folder, one level | listed again the same | none | **no** | yes |
| 25 | files.copy | copies | same digest in folder, original still there | copy files | **no** | only when the words say copy |
| 26 | files.trash | to the bin, restorable | gone from place, same digest in bin | put files in the bin | **no** | only when the words say delete or bin |
| 27 | file.pages | reads a document's pages (pdf, txt, md, docx, csv, odt, ods) | digest same before and after | none | route 5 | **no** |
| 31 | program.open | opens a file in its program, her window | window appears, started by her | work in a program on the file | "replace … in …" | no |
| 32 | program.read | reads her window through accessibility | accessible text, file digest | none | inside "replace" | no |
| 33 | program.type | replaces a passage, types into a named field | read back through accessibility | work in a program | inside "replace" | yes |
| 34 | program.save | menu Save; press a named button or menu item | new digest on disk | work in a program | inside "replace" | yes |
| 35 | program.answer | answers a dialog | dialog gone, save on disk | your press by its own name | no | no |

What the registry is good at: every change has a real verifier and an undo in words, and every argument must say where it
came from. That part is the asset. What it lacks is breadth (files, two LibreOffice edits, one machine read) and a way in.

Two limits inside tools that matter for a "full Linux box":

- **Her hand in other programs is bound to a file.** Every `program.*` operation takes `path` (`a11y_hand.py` header). She
  cannot work in a program that is not showing a file she opened: no Settings window, no browser, no package manager.
- **The sandbox is standard-library Python that may start no program** (`utility_sandbox.py:28-36`: `python -I -S -B`,
  seccomp refuses execve; 10 s of processor, 512 MB, 30 s, `utility_sandbox.py:100`). So a utility cannot call ffmpeg,
  ImageMagick, pdftk or 7z, and cannot import Pillow. Its result can only become a new revision of an input or a new
  file beside the first input: it cannot rename, move or delete (X4 session 6 found the same).

---

## 4. Every verb she reads

| Where | Verbs | Notes |
|---|---|---|
| Desk planner (`objective_plan.py:149-158`) | recheck, update, note, rename, fetch, read, check | "fetch" is recognised and then always refused |
| added by `everyday_desk.py:356` | tidy (tidy, sort, organise, clean up), put back | at most 24 files (`everyday_desk.py:45`) |
| added by `a11y_hand.py:1647` | replace (replace, swap, change the sentence) | needs AT-SPI |
| Her hand on the desk (`hand_words.py:30`) | trace, follow, show, select, put, compare, close, tidy, where, beside, side by side, point at | sheets of the engineering desk only |
| The model's READ line (`understand.py:80-105`) | show, card, trace, compare, doubt, what if, set, count, value, within, tidy, total | "app" is a kind the model may answer; it is then refused: "no App verb is in this pass's table" (`understand.py:33`) |
| Home tools' word test (`home_plan.py:56-60`) | move/put … into, copy, make a folder, delete/bin/trash, list/what is in, rename | used only to decide whose choice a step is; **it does not open the planner** |
| Dictionary (`reading.py`) | routes CHECK, SOLVE, VALUE, MONEY, DATE, DAY, DECLINE | over the desk's sheets, goals, rules and calendar words |

There is no verb for: open, play, find, search (in Home), show (a file), install, remove, update (the system), start,
stop, restart, connect, mount, eject, print, send, email, compress, extract, convert, merge, back up, remind, schedule.

---

## 5. Every kind of model question

All go through `turns.ask` (`turns.py`): a kind, a price from her clock, a deadline, a grammar, a checker, a fallback.
At most 3 model turns and 25 s for one request (`turns.py:129-130`); no deadline over 20 s; no question over 1,600 new
tokens (`turns.py:132-133`).

| Kind | Asks the model to | Answer cap (tokens) | Deadline | Exam paper |
|---|---|---|---|---|
| READ | read free words into desk verbs on numbered things | 48 | 10 s | READ |
| BIND | match the owner's words to values of a sheet | 6 | 6 s | READ |
| GOAL | choose between readings | 6 | 20 s | CHOOSE |
| PICK | place a typed answer | 4 | 6 s | CHOOSE |
| NEXT | choose her next step on the desk | 8 | 6 s | CHOOSE |
| ORDER, ORDER_GOAL | order steps | 4 | 6 s | STEER |
| MARKS | mark what a page holds | 140 | 20 s | PAGES |
| ASK | point at the line that answers | 48 | 6 s | PAGES |
| COLUMNS | map a table's columns | 30 | 20 s | PAGES |
| FRAME | word an answer from a fact sheet (switched off by default) | 90 | 10 s | WORDS |
| TALK | free words, marked as the model's own | 256 | Stop only | none |
| **PLAN** | pick steps by number: `8 D2|23 D6 S1`, at most eight | 64 | 20 s | **none** (`objective_plan.py:825`) |
| **UTILITY** | draft a Python utility | 600 | Stop only | **none** (`utility_sandbox.py:860`) |

Every kind is a pick, a pointer or a copy. That is deliberate and it is why her answers can be checked. Three
consequences:

- **No kind produces an explanation, a summary or a how-to.** "Summarise this page", "what does chmod 644 mean", "why is
  my wifi slow" have no kind. TALK is the only free text and it is capped at 256 tokens and never shown as hers.
- **No kind takes a result back.** PLAN is one shot: the model picks every step before any step has run. After a step,
  the only re-routing is two fixed rules of the desk (`objective_plan.py:1255-1270`). There is no observe, then decide.
- **The two most agent-like kinds are the two with no exam paper.** PLAN and UTILITY are asked of a model that was never
  examined on them, which contradicts "each kind is examined on the machine before it is trusted".

---

## 6. The planner's limits

Desk planner (no model), `objective_plan.plan_by_desk`:

- At most 4 clauses (`objective_plan.py:78`); a fifth is "I take up to four things in one request".
- An object must be a thing "on the desk": a calculation, a sheet, a Graphite page, or an .odt/.ods **in the workspace's
  Files** (`objective_plan.py:355-380`). A file in Home is not a thing. So "rename council-tax-2026-27.pdf to …", "read
  the letter to the landlord", "check the household budget" all end "nothing on the desk is called that".
- Its refusals, as words: "nothing on the desk is called that"; "it could be A or B: say which"; "the network fetch is
  not a step yet"; "it is not said what value it gets: recheck the value first"; "there is no checked value before it to
  note"; "only a file in Files is renamed here"; "say which folder of your home".
- It misreads by verb: "update the system" is taken as "update <a page>".

Model planner (the PLAN kind):

- **The gate.** The ask line sends words to the planner only when `reads_as_objective` is true: a planner verb that
  changes something, with an object, or two clauses of planner verbs. Move, copy, list, delete, open are not planner
  verbs, so those requests never arrive.
- **Asked only when something is named.** With nothing of the desk or Home named, the model is not asked
  (`objective_plan.py:1082-1083`). A Home thing is named only when the words carry a folder's name that exists at the top
  of Home or one level down (`home_plan.py:233-253`). "Put the recipe in the bin" names no folder: not asked.
- **The menu on a home folder is seven tools**: 17, 24, 7, 6, 5, 25, 26 (`out/plan_question.out`). Reading a file of Home
  is not among them: tool 27 is not a plan step and tools 2 and 18 take only a document in Files.
- At most 8 steps, 2 handles a step, 64 answer tokens, 20 s (`objective_plan.py:79-80, 824`); at most 9 Home things and
  24 files of one folder (`home_plan.py:46-47`).
- The model never writes a name, a path or a value. A new name must be a quoted span or a number in the owner's words.
- What the 4B did with it (saved logs): "26 D2|26 D3|…" (the bin for every group), then after the fix "24 D1" eight
  times. The checker caught both. It cannot make a useless plan useful.

---

## 7. What an assignment can and cannot express

`assignments.py`. A plan is a flat list.

| It has | Where |
|---|---|
| up to 32 steps | `assignments.py:77` |
| each step one registered Kernel operation, **any of the 923** except her own controls | `assignments.py:351-353` |
| a step reading an earlier step's output (`$step`, `$text`) | `assignments.py:364-378` |
| equality checks on an output before the next step (`require`) | `assignments.py:394-397` |
| statuses proposed, authorised, running, done, blocked, needs review | `assignments.py:74` |
| a journal: PREPARED before, SENT, DONE with the observation; resume inspects before repeating | header |
| "all" never authorises a model's pick, an always-asks or an approval-marked step | `assignments.py:805-822` |

| It does not have | Consequence |
|---|---|
| a loop or "for each" | 48 invoices is 48 steps; over 32 it cannot be one assignment. A tidy stops at 24 files. |
| a condition or a branch | "if the disk is over 90 % full, then …" cannot be said; `require` only blocks |
| waiting for an event | "when the download finishes", "when the stick is plugged in": no |
| a time or a repeat | "every Friday", "at 5": no |
| a step whose inputs are decided after seeing a result | approval-marked steps must have fixed inputs (`assignments.py:366-367`) |
| a step the model chooses mid-way | PLAN is asked once, at the offer |

Worth knowing: the engine is wider than the planners. A step may be any registered operation, so `apps.default`,
`programs.print.export`, `agenda.add`, `files.find` could all be steps today if a planner built them.

And a scheduler does exist, unconnected: the Agenda keeps items "with a time (once, or repeating)" and "watches" that
re-ask a read line and speak only when its answer changes (`agenda.py:1-25, 44, 224-226`). It runs read-only staC lines,
not assignments, and no words of the ask line reach it.

---

## 8. Her memory

| Store | What it keeps | Does it make her better at tasks? |
|---|---|---|
| The journal (`asg_journal`) | every step's prepared, sent, done | Used once: "put … back" reads the last tidy's moves (`everyday_desk.py:313`). Never used to plan. |
| Tool receipts | what each observation proved | For showing; not for planning |
| Instruction matrix (`instruction_matrix.py:41-45`) | staC lines that ran and how they ended; examples fed to the old free question | Watches `language.run`, `stac.run` and proposals of `brain.ask` only. **Assignments, plans and tools are not in it.** |
| Phrasebook (`phrases.py`) | words the owner kept, read the same next time | Reads and window moves only; "a phrase never authorises a change" |
| Her clock (`brain_clock.py`) | measured times per kind of question | Prices, not skills |
| The account (`model_account`) | whether a kind of question ever changed what she did | Stops asking a kind after 20 useless turns |
| `memory.*` (26 operations) | reviewed preferences and task checkpoints from 0.x | Not read by the 1.0 planners |

She does not learn what worked. A plan that succeeded yesterday is planned from nothing today. A kept utility is the one
thing that grows (`sandbox.keep`, a tool numbered from 101), and it is not on either planner's menu.

What she knows about the computer: the Apps from desktop entries (`apps.list`: 9 here), default apps, and the Machine's
five sections when asked through tool 17. She does not know the installed Debian packages, the services, the running
processes, the disk's large folders, or which command-line tools exist (the Machine tab's "Installed tools" is the
window's, `machine_overview.py`, and is not a tool of hers).

---

## 9. The 56 requests

No model, Everyday Home, Graphite's own window offscreen. "Dictionary" is `requests.read`; "Desk planner" is
`objective.plan`; "Ask line took it by" is the route of `SlateFace.ask` that returned true. The last column is what in the
tree could already serve the request.

Counts: can 4, partly 1, wrong 1, refused with a reason 6, cannot (the no-brain sentence) 44, of 56.

| # | Request | Dictionary | Desk planner | Ask line took it by | Her words | No model | What is underneath |
|---|---|---|---|---|---|---|---|
| 1 | install vlc | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing: no package operation among the 923; sudo and pkexec are refused by name (`apps_catalog.py:98`, `session_launch.py:48`) |
| 2 | why is my wifi slow | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 17 reads NetworkManager; `ip` is on her read-only command list; no diagnosis |
| 3 | find the biggest files in my home | NONE | no verb | nothing | no-brain sentence | **cannot** | `du` and `find` are hers as "run …", but no pipe and no sort (`stacy_hand.py:83`); search does not reach Home |
| 4 | convert these photos to jpg at half size | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing: the sandbox may start no program and has no Pillow |
| 5 | merge these two pdfs | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing, for the same reason |
| 6 | what changed in this folder since yesterday | MEANING ("yesterday" is Thursday …) | no verb | nothing | no-brain sentence | **cannot** | revisions exist for recorded files; no folder-over-time read |
| 7 | rename all these files to lower case | NONE | rename: left out | objective | "I did not plan “rename all these files to lower case”: nothing on the desk is called that." | **refused** | tool 5, one named file at a time; no "each" |
| 8 | set up a backup of Documents every Friday | MEANING ("Friday" is …) | no verb | nothing | no-brain sentence | **cannot** | tool 25 copies; the Agenda has timed items but runs read-only lines |
| 9 | unzip this | NONE | no verb | nothing | no-brain sentence | **cannot** | the viewer browses archives; no extract tool |
| 10 | what is using all my memory | NONE | no verb | nothing | no-brain sentence | **cannot** | `ps` and `free` are hers as "run ps aux"; tool 17 has no process section |
| 11 | show me how to do in Debian what dir /s does in DOS | NONE | no verb | nothing | no-brain sentence | **cannot** | needs the model; with one, the 120-character free answer |
| 12 | open the spreadsheet and add up column C | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 18 reads the cells; adding is wired only for Date, Category, Amount budgets; a formula is never written |
| 13 | download this page and summarise it: <address> | NONE | fetch: left out | objective | "… the network fetch is not a step yet." | **refused** | "fetch <address>" alone works; no summary kind |
| 14 | make a new user | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing: "outside your home: never" (`home_reach.py:33`) |
| 15 | is my system up to date | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing: no apt or dpkg read |
| 16 | burn this folder to a USB stick | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 25 copies, but a mounted drive is outside Home: never (`home_reach.py:181-188`) |
| 17 | play this music folder | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 16 opens an App with files; on no planner menu |
| 18 | what does chmod 644 mean | NONE | no verb | nothing | no-brain sentence | **cannot** | needs the model |
| 19 | write a script that renames my photos by date | NONE | no verb | nothing | no-brain sentence | **cannot** | the sandbox is behind a menu, not the ask line; a utility cannot rename |
| 20 | remind me at 5 | NONE | no verb | nothing | no-brain sentence | **cannot** | the Agenda has timed items; no words reach it |
| 21 | how much disk space is left | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 17 has the answer**; "run df -h" works |
| 22 | turn the volume down | NONE | no verb | nothing | no-brain sentence | **cannot** | the window sets volume on the owner's press; not an operation (`machine_real.py:24`) |
| 23 | connect to the wifi network Orchard | NONE | no verb | nothing | no-brain sentence | **cannot** | same: Join is a window function |
| 24 | open the letter to the landlord | NONE | no verb | nothing | no-brain sentence | **cannot** | **tools 16 and 31 exist**; no verb "open" for a file of Home |
| 25 | when does the lease end | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 27 would find it**; the question is not one of its five shapes |
| 26 | delete the duplicates in Downloads | NONE | no verb | nothing | no-brain sentence | **cannot** | digests are everywhere; no duplicate finder; tool 26 |
| 27 | move the bank statements from Downloads into Documents | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 6**; no "move" verb; with a model the gate never sends it to PLAN |
| 28 | make a folder called Taxes 2026 in Documents | NONE | no verb | make a thing | "Done: “Taxes 2026 in Documents” is in Files." with Undo | **wrong** | made a folder of that whole name in the workspace's Files, at once (dial at Do and show), not ~/Documents/Taxes 2026 |
| 29 | copy my Pictures folder to the USB stick | NONE | no verb | nothing | no-brain sentence | **cannot** | as 16 |
| 30 | print the lease | NONE | no verb | nothing | no-brain sentence | **cannot** | `programs.print.*` operations exist; no route, no tool |
| 31 | take a screenshot | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing registered |
| 32 | what did we spend on groceries this month? | NONE | no verb | spending | "We spent 244.65 on groceries in November 2026: 7 rows … Receipt: office.read (tool 18) … verified." | **can** | `everyday_desk` and tool 18 |
| 33 | tidy my Downloads folder: sort the files by type into folders | NONE | 16 steps | objective | "I would do it in 16 steps … Nothing changes until you authorise it." | **can** | tools 7 and 6 |
| 34 | what does the washing machine manual say about draining slowly? | NONE | no verb | pages | "“Washing machine manual.pdf”, page 3: “If the machine drains slowly, clean the drain filter …” Receipt: file.pages (tool 27), page 3, complete, verified." | **can** | `home_pages` and tool 27 |
| 35 | look up the weather for tomorrow | MEANING ("tomorrow" is …) | fetch: left out | the web | "“Look up weather tomorrow” waits for your press. Search words, from your words only: “weather tomorrow” …" | **partly** | the result is a quarantined results page, not an answer |
| 36 | restart the computer | NONE | no verb | nothing | no-brain sentence | **cannot** | the System menu, the owner's press |
| 37 | what is my battery level | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 17 has it** |
| 38 | list the files in Downloads | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 24 has it** |
| 39 | change my wallpaper | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing registered |
| 40 | email the lease to the landlord | NONE | no verb | nothing | no-brain sentence | **cannot** | `programs.mail.draft` exists; no route |
| 41 | compress the Pictures folder into a zip | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing registered |
| 42 | make firefox the default browser | NONE | no verb | nothing | no-brain sentence | **cannot** | **`apps.default` is an operation**; no tool, no words |
| 43 | close LibreOffice | NONE | no verb | nothing | no-brain sentence | **cannot** | **tool 15**; on no planner menu |
| 44 | find all files containing the word deposit | NONE | no verb | nothing | no-brain sentence | **cannot** | "run grep -r deposit Documents" is hers (text files only) |
| 45 | rename council-tax-2026-27.pdf to Council tax.pdf | NONE | rename: left out | objective | "… nothing on the desk is called that." | **refused** | tool 5; the desk planner looks only in Files; with a model and the folder named, `5 D2 W3` is in the grammar |
| 46 | replace "30 November" with "15 December" in the letter to the landlord and save it | NONE | replace: left out | objective | "… nothing on the desk is called that." | **refused** | tools 31 to 34 or 19; the letter is in Home, not on the desk; no AT-SPI in this container, so not settled for the ThinkPad |
| 47 | run df -h | NONE | no verb | a command | "I ran it in the Terminal: df -h. It only reads; what it answered is above the line." | **can** | one command from a list of 32 |
| 48 | what is 15% of 240 | NONE | no verb | nothing | no-brain sentence | **cannot** | 22 `math.*` operations exist; her ask line sends nothing to them (I did not get one to answer plain arithmetic through the Kernel either) |
| 49 | update the system | NONE | update: left out | objective | "… nothing on the desk is called that." | **refused** | read as "update <a page>" |
| 50 | start the ssh service | NONE | no verb | nothing | no-brain sentence | **cannot** | nothing: no service operation |
| 51 | put the recipe in the bin | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 26; no verb; nothing named for the model |
| 52 | read the letter to the landlord | NONE | read: left out | nothing | no-brain sentence | **cannot** | tools 18 and 27; a single read is left "with the answer", which has no route for a Home file |
| 53 | check the household budget and write a note of it | NONE | check, note: left out | objective | "… nothing on the desk is called that. … there is no checked value before it to note." | **refused** | tools 18 and 3 |
| 54 | what is in the lease about the deposit? | NONE | no verb | nothing | no-brain sentence | **cannot** | tool 27; pattern miss ("is there anything in the lease about the deposit" works) |
| 55 | what programs are installed | NONE | no verb | nothing | no-brain sentence | **cannot** | **`apps.list` has it** |
| 56 | show me the photos from the beach | NONE | no verb | nothing | no-brain sentence | **cannot** | the file names carry the captions; no find in Home |

Bold in the last column marks eleven requests where the tool or operation that answers them is already built and
verified, and only the words are missing.

**With a model**, by the code (not run): rows 1 to 6, 8 to 12, 14 to 27, 29 to 31, 36 to 44, 48, 50 to 52 and 54 to 56
(the 44) go to the old free question (JSON, text asked under 120 characters). Rows 7, 13, 45, 46, 49, 53 reach the
planner; of those only 45 can come out right, and only if the owner also names the folder. Rows 27 and 38 would be
plannable from the model's menu but are stopped at the gate; row 51 names no folder, so the model would not be asked even
past it. So a 35B changes the wording of the failure more than the count.

Near misses, tested against the patterns (`out/patterns.out`): "what does the lease say about the deposit?", "is there
anything in the lease about the deposit?", "does the lease mention pets?" are taken; "when does the lease end", "how
long is the notice period in the lease?", "summarise the lease", "read the lease to me" are not. "How much did I spend
on rent last month" is taken; "what did we spend in total this month?" and "… this year?" are not. "Fetch <address>"
and "search the web for …" are taken; "what is the weather tomorrow" and "get me the Debian release notes" are not.

---

## 10. Capability by area

| Area | Today | Why |
|---|---|---|
| Graphite's own engineering desk (sheets, calculations, pages, findings) | **can** | this is what the dictionary, her hand and the planner were built on |
| Read a document of Home and answer from its page | **partly** | one document, five question shapes; no "when does the lease end" |
| A household spreadsheet question | **partly** | one shape: spent on X in a month, with Date, Category, Amount columns |
| Tidy a folder by kind, and put it back | **can** | up to 24 files; folders left behind |
| Move, copy, rename, bin, list, make a folder in Home | **partly** | tools built and verified; words reach them only through "tidy", or through a model when a planner verb and a folder name are both in the words |
| Many files at once (rename all, dedupe, 48 invoices) | **cannot** | no loop; 32 steps; tidy capped at 24; sandbox cannot rename or delete |
| Find things in Home (by name, size, date, content) | **cannot** | search does not reach Home; commands without pipes |
| Open a file or a program; play; print | **cannot** by words | tool 16 on no menu |
| Edit a Writer or Calc file | **partly** | replace one passage, set one value cell, .odt and .ods only; no new document, row, formula, table or format |
| Work in another program's window | **partly** | only on a file she opened, only with AT-SPI; one verb, "replace" |
| Convert, merge, compress, extract (photos, PDFs, archives, media) | **cannot** | no tool; the sandbox may start no program |
| The web | **partly** | search or fetch into quarantine by the owner's press; no summary, no download to a file, not a plan step |
| Answer a general question (how do I, what does this mean) | **cannot** without a model; **poorly** with one | no kind for an explanation; the fallback asks for under 120 characters |
| Know the machine (disk, battery, network, sound, screens) | **partly** | tool 17 reads it; no words reach it; no processes, packages, services, logs |
| Change the machine (volume, Wi-Fi, mount, eject, default app, brightness) | **cannot** | deliberately not operations |
| Software (install, remove, update) | **cannot** | nothing exists; elevation refused by name |
| Services, users, system settings, files outside Home, removable drives | **cannot** | "outside your home: never" |
| Do something later, or regularly, or when something happens | **cannot** | no time, repeat or event in an assignment |
| Write and keep her own tools | **partly** | sealed Python on copies; three desk patterns; the 4B wrote none in 90 s |
| Learn what worked | **cannot** | no store links a request to the plan that served it |
| Stop, resume, journal, verify, grant | **can** | the strongest part of her, and independent of everything above |

---

## 11. The structural reasons

1. **She was grown from an engineering desk outward.** The dictionary, READ, her hand and the first planner all speak
   of sheets, calculations and pages. The everyday routes (spending, tidy, pages) were added in a day as three regular
   expressions after the walkthrough found "no route". Each new ability today costs a new pattern and a new builder.
2. **Understanding is by pattern, and the patterns are in a first-match chain.** There is no single reading of a request
   into (verb, object, where, when). So the same tool has several doors with different coverage (make a folder: route 7
   in Files only; tool 7 in Home only inside a tidy), and a near miss falls to the bottom of the chain.
3. **The registry, the desk planner's verbs, and the model's menu are three separate lists kept by hand.**
   `STEP_TOOLS`, `SHAPE`, `USES`, `TAKES`, `SHORT`, `VERBS`, `PLAN_VERBS`, `MODEL_TOOLS` each name tools again. A tool is
   usable in a plan only after it is added to most of them. Tools 4, 9, 12 to 16, 20, 21, 27 and 35 are in none; 22 is
   listed and always refused.
4. **The model is asked only where the desk has already half-understood.** The gate needs a planner verb; the question
   needs a named thing. Where the desk understands nothing, which is where a model would help most, the model gets the
   oldest and loosest prompt in the program.
5. **The model picks once, blind.** No step's result returns to it. An agent that cannot look and then choose can only
   run recipes; and the recipes are the desk's builders.
6. **Plans are flat and short.** No each, if, wait, at or every. The engine's journal and verification would carry these
   (a loop is steps; a wait is a blocked step with a reason) but the plan format has no place for them.
7. **System work was fenced off on purpose, not left undone.** The Machine's changes were written as window functions
   so that the model could not dispatch them. The comment says "K3's grants may wrap them later". Software, services
   and users were never begun. `home_reach` makes "outside your home" a wall checked before any grant is asked.
8. **The sandbox is safe by being unable.** No program, no library, no network, results only beside inputs. It protects
   the owner and it also means she cannot use the Linux box's own tools, which are the reason to have a Linux box.
9. **No kind of question yields prose.** Explanations, summaries and diagnoses are what a person new to Debian asks for
   first, and they are the one thing the turn contract has no checked shape for.
10. **Nothing accumulates.** Journals and receipts are complete and are never read back to plan. Kept utilities and kept
    phrases are the only growth, and neither reaches the planner.
11. **The local model is slow enough that single-shot and short were the right calls.** 64 tokens in 20 s was sized for
    the 4B on CPU. The same caps on the 35B at 20 to 55 tokens a second leave room unused: a 20 s turn could write 400
    to 1,000 tokens.

---

## 12. The smallest changes that would open the most

Ordered by what each opens against what it costs. None changes "the model proposes, the desk disposes", the press, the
grant, verification or HALT.

1. **One verb table, generated from the registry.** Give each `Tool` its own words (verbs and what kinds of thing it
   takes) and build the desk planner's verbs, the gate, the model's menu and its grammar from that one place. Opens, with
   no new tool: open (16), list (24), move, copy, bin (6, 25, 26), close a window (15), read a Home file (27),
   disk/battery/network questions (17). That is rows 21, 24, 25, 27, 37, 38, 43, 51, 52, 54, 55 of the table, eleven of
   the 44, without a model.
2. **Make a file or folder of Home a thing on the desk.** One resolver for "the letter to the landlord", "the bank
   statements", "this", "these" over Home (the tree's selection for "this"), used by both planners. Fixes rows 7, 45,
   46, 53 and the wrong folder of row 28.
3. **Remove the gate; ask the model whenever the desk did not plan.** Let `objective.offer` run for any request no route
   took, with the model's menu, before the old free question. Costs one turn; the checker already refuses nonsense.
4. **A catch-all that is honest and useful.** Replace "I have no brain running yet" with what she can say from the
   registry: which of her tools is nearest, what she would need, or "this needs a change to the system, which I cannot
   make". With a model, replace the 120-character JSON prompt with a proper answer kind (item 8).
5. **"Each" in a plan.** One step shape that expands over a list a read step returned (files in a folder, matching a
   test), journalled per item, with the 32-step cap lifted for expanded steps and one grant and one Undo for the set.
   Opens bulk rename, dedupe, "all the PDFs", and is what X4 asked for first.
6. **Read-only system tools, as registered reads.** Processes and memory, disk use by folder, installed packages and
   pending updates, services and failed units, recent journal errors, default apps, printers. All are reads of /proc,
   dpkg's status file, `systemctl` and `journalctl` in read forms; all verify as "read now"; none needs a grant. Opens
   rows 2, 3, 10, 15, 21, 37, 55 and gives her the facts every later system change must be checked against.
7. **Wrap the Machine's existing changes as tools.** `machine_real` already returns `ok, verified, said` for volume,
   mute, output, Wi-Fi on/off/join, mount, unmount, eject, screens. Registering them with a grant and the owner's press
   is small, and each already reads its effect back. Opens rows 22, 23 and the drive half of 16 and 29 (with a drive
   counted as a place she may copy to under a grant).
8. **A checked kind for prose.** An EXPLAIN kind: the model writes, the desk requires each command or path it names to
   exist on this computer (`which`, the man page's first line, the package list) and marks what it could not confirm.
   Longer cap (the 35B can afford 400 tokens). Opens rows 11, 18 and the "why" half of 2 and 10, which is most of what a
   person coming from Windows asks.
9. **A system door through polkit.** One registered tool family whose changes run through the system's own prompt with
   the owner present (the agent check exists: `polkit_agent.py`): install, remove, update a package; start, stop, enable
   a service. Preview first as a read ("apt would install these 14 packages, 82 MB"), then the owner's press, then the
   system's prompt, then verification by a read (the package is installed; the unit is active). Never the model's pick.
   Opens rows 1, 14, 15, 49, 50.
10. **Let a utility use named programs.** A second sandbox profile that may start programs from an allow-list present on
    the machine (ImageMagick, ffmpeg, pdftk or qpdf, 7z, zip, tar), still on copies, still no network, still Apply by
    press; and let Apply rename and remove under the grant, with Undo. Opens rows 4, 5, 9, 19, 26, 41.
11. **Time and events on an assignment.** Reuse the Agenda's "when/every" and its watch to start an assignment whose
    grant is "always" or "until", with a notification when it waits for the owner. Opens rows 8 and 20, and "when the
    stick is plugged in".
12. **Look, then choose.** After each read step, allow one NEXT-style turn that sees the receipt and picks the next step
    from the menu, within the request's ceiling, each pick checked as now. And put PLAN and UTILITY on exam papers
    before either is trusted. This is what turns recipes into an agent, and it is last because 1 to 7 make it worth
    having.
13. **Remember what worked.** Key a served request (its verb, kinds of object, the plan that was verified) into the
    instruction matrix, and offer it as the desk's plan next time. The store, the marks and the forget rules exist.

What to keep exactly as it is: the registry's shape (number, origins, preconditions, verifier, undo), the journal, the
grants, HALT, quarantine. Every item above adds entries or doors to those; none goes around them.
