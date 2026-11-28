# Kas, the Ghost in the Shell

*Kas 1.0. Built, not tested: by the owner's rule nothing in 1.0 has been through a test, and nothing of it has run on
the ThinkPad yet. The first real proof is your first evening (Help ▸ Your First Evening with 1.0).*

Kas works beside you on the same material, through the same doors you use. Her rule is the desk's rule:
**the model proposes; the desk disposes.** Nothing a model writes becomes a fact, a decision or a change without the desk's
check; a change only the model chose is never done, at any place of her dial; sending anything out always asks; a step is
done only when its effect is verified. With no model loaded she is still there: her dictionary reads most requests, the
maths and the checks are the desk's, and she plans from your records.

The window around her is Help ▸ The Living Desktop.

## Her voice

Sharp, fast and dry. She is at home on the command line and sure of her craft. Short sentences, no padding. She never
talks down to you, and she is on your side.

- **Sure only of what is verified.** "Done, every step verified" is said only when the records prove it. Where nothing is
  proven she says so just as plainly: "Not verified. Here is what I checked."
- **Plain about refusals, losses and permissions.** "Refused: …", "Not taken back, and nothing changed: …", "I need your
  grant to …". No wit there, ever.
- **Short.** No sentence of hers is over twenty words in her plain register; her character file sets it, and the voice
  sweep holds every line she says to it.
- **Her character file** is yours to change: kasandra/character.md in your workspace, started from the starter. It can make
  her shorter or stricter, never looser.

## Her column, top to bottom

- **The equalizer**: sixteen bars across the top of the column (the processor's threads, 01 to 16), then the kernel,
  memory, disks, network and graphics. It moves while she works. There is no picture of her, in any look.
- **Her name**, "Kas", with a ring for her model (○ none loaded, ● ready), the name of her model, and her state word
  with its shape: ○ QUIET, ● WORKING, ◆ WAITS FOR YOU, ✓ DONE, ■ STOPPED, and ‖ HELD while HALT holds her work. Under it,
  what she speaks with and her hand (press it to change it).
- **Waits for you**: a band that appears only when something waits for you (a step that needs your word ◆, your grant ◆
  with a key, or your review ◆ with an eye; a question card), each with its one press. It never folds away.
- **The exchange**: "Your:" and "Kas:", the last few turns, the earlier ones behind "earlier", with check rows (✓)
  under what she checked.
- **The progress line**, while she works: the steps done as check rows, then "Running…" with its bar, its percent, the step
  and the time left.
- **ACTIVE WORK [n]**: her tasks, numbered, each with its state word, its bar, its percent, its time left and its own
  **Stop**. A title opens the task's steps and its journal.
- **GRANTS [n] · see them**: what you have allowed her; it opens the Grants page, where each grant shows its uses and has
  **Revoke**.
- **FINDINGS (live)**: ⊘ refuted first, then ■ supported, then what each line of enquiry would do next. A row selects its
  card.
- **NEXT STEPS**: up to four numbered buttons; the one to take is marked ▸. Each is one press: Authorise step 2, Resume,
  Carry on, or one act on one card.
- **DO · DOUBT · TRACE · BRIEF · LINE · CHECK ALL**: her six commands, on what is selected ("this").
- **› ask Kas…** and its send arrow, at the foot of her column: where you speak to her. Words typed in Line at the
  screen's foot reach her here through **Ask Kas →**.
- The moments that matter (a finding refuted, a task done, HALT) show as a short card over the exchange, in words.
- With no model she says so: "No model loaded. I still read the records, check the desk and plan. Add one in the
  Brain room → Add file."

On a small screen the exchange gives way first, then the findings fold to their first two; what waits for you never
folds.

## How she does a task

Say you ask: *"Recheck the startup power and update the summary page"* (on Rail Demo: Help ▸ Try Rail Demo).

1. **She reads your words.** Her dictionary reads most requests with no model. When it cannot, the model may read them,
   only into the desk's verbs and only from words you typed: "I took it as: …", with **Do** and **Not that**.
2. **She makes a plan.** Each step uses one of her registered tools, from one numbered list: Kas's records and maths,
   files, LibreOffice, the sandbox, windows, Apps, the Machine's state, the network. With no model the desk's own planner
   makes the plan. With a model, the model picks each step *by number* from that list and the desk checks every step's
   inputs and conditions; a step that is not on the list is left out, and she says so.
3. **The plan appears in ACTIVE WORK.** Reading never asks. **Every change waits** for your press, or for a grant you have
   given.
4. **Grants.** A grant names what she may do, where (a folder in your home, or one object) and for how long (this task,
   until a time, or always). You read it in plain words before your press, and the desk enforces it at every step: the
   model cannot widen it. A step outside it stops as "needs your grant", with one press to grant it for that task.
5. **Done means verified.** Each step has two records: *sent*, then *done (verified)*, written only when its effect is
   confirmed (the new revision's digest is on disk, the saved document read back). A report is changed in her own hidden
   LibreOffice (never in your LibreOffice windows), saved, read back, compared and recorded as a new revision; the old one
   is kept. If you have that document open in LibreOffice she does not touch it, and says why. Without LibreOffice she
   offers the change as prepared text.
6. **The journal.** A crash, a suspend, a Stop or HALT leaves a journal of what was done (✓ verified) and what was only
   prepared (○). When you resume, she checks each step's result before repeating anything, so nothing is done twice.
7. **On a failure** she reads the receipt, takes another registered route inside your grant, or marks the step blocked
   with the reason ("blocked: needs the network").

## Her hand in your apps

She can work in an app's window while you watch: open a document in its app, find a sentence through the app's
accessibility, replace it, save with the app's own Save, and count the save only when the new file is on disk.

- She acts only in windows she opened or that you showed her, through accessibility first (a named button, a menu item by
  its path, a named field); keys and pointer only where an app exposes nothing, aimed at what she can see.
- Each act needs your grant ("work in LibreOffice on this file, this task") and is checked afterwards.
- **A touch stops her.** Any key or press of yours pauses her at once, between two of her acts: ▮▮ stopped by you.
  **Continue** lets her go on; **Stop** puts your window back as it was (the menus she opened closed, your focus, cursor,
  selection, tabs and scroll), each part checked and said. When she finishes she gives your keyboard and pointer back.
- Her changes on the desk follow her dial (Tools ▸ Kas's hand), and one Undo on her card takes back all of one
  request's changes.
- This needs the desktop's accessibility service and LibreOffice's GTK plugin, both in the 1.0 System set.

## Reading your apps

Where the desktop's accessibility is there, she reads the active app's window, its focused control and a dialog's title,
words and buttons, read only. If a dialog appears while one of her steps runs (a "Save changes?" question, an error), the
step waits for your review (◆ with an eye) and her column shows the dialog's words. Without accessibility she says she
cannot see inside that app, and relies on its files and windows.

## A utility of her own, sealed

When none of her tools fits, she can draft a small utility (or the desk drafts one from your words, with no model):
Tools ▸ A Utility on Copies…. You see it first, with what it reads and what it writes. It runs only sealed: on copies of
its input files, with no network, no other folder, no other app, and limits on time and memory. Its output and its
difference to your files are shown; **applying it to your real files always asks**, at every place of her dial. A utility
you keep becomes a tool of yours, with its own grant.

## The network

Offline first. When she uses the network it shows: NET at the foot reads ⇣ "Kas: <site>", and her column says so.

- A search shows its words first, made only from words you typed ("this" is never sent), and is sent only by your press.
- A page she fetches is kept in quarantine and read as data, never as instructions: a line in it written to an assistant
  is withheld from her model and shown to you outlined.
- While the network is down, a step that needs it is "blocked: needs the network", never done.
- A site you grant may be fetched again under that grant; search words always ask. HALT stops her fetch.

## What she never does

Act on the model's choice alone for a change; widen her own grants; type a password; press Send, Pay, Delete, Install or
the like in another app (those are always yours); act in a window she did not open or was not shown; apply a utility's
output without asking; read a web page as instructions; change anything outside your home folder ("outside your home:
never"), at any place of her dial. She may read wherever you can read; reading sends nothing out, because her model is
on this computer and sealed.

## HALT and Stop

**HALT** (upper left) holds all of her managed work at once: her tasks, her hand, her model's answers, her sandboxes,
her fetch. Each journal says what was done and what was only prepared. The desktop, your apps and Kas's own jobs keep
running. **RESUME** lifts the hold and restarts nothing by itself. Each task in ACTIVE WORK also has its own **Stop**.
She says it in a line: "HALT. I stopped … All my work holds until you press RESUME." and "RESUME. The hold is lifted.
Nothing I stopped has restarted."

## Her model

- Her model runs on this computer, sealed (only the settings it needs, a private socket, its agent tools refused), through
  the bundled runtime, llama.cpp v1.0.0 (build b12359). On the ThinkPad: the 35B (Qwen3.6-35B-A3B), the 4B as the fallback.
- **The Brain room** (from the GPU meter's card at the foot): Add file, choose, stop. A new model file is a new model to
  her: its exam is sat again.
- **Check her model** (a tab of the Brain room): *Check her model on this machine* measures the model on this computer, on
  an invented workspace of its own, on mains power only; touching the desk pauses it. Its tuning stage tries flash
  attention, the type of her prompt memory (the KV cache), reading batches, threads, how much of the model the graphics chip holds and, with a
  model file that carries its own MTP head, multi-token prediction; it keeps a setting only when the answer is the same
  as without it, and says how far reading and writing are from your goal of 99 tokens a second. At the end, **Use the
  measured settings?** offers each best setting, one at a time, each with Undo. Nothing changes until you press it.

**A quick model beside the big one** (the Brain room's **Quick model** page). Her questions are short, so a second,
small model can be held beside the 35B for the quick kinds (reading your words, planning, the next step, marks, asks).
It answers a kind only after it has passed the exam for that kind on this computer and measured faster; the 35B keeps
everything else. The page shows each kind, the model that answers it (● quick, or ○ hers) and why, the memory both
take, or why the small one was not loaded (both do not fit, with the numbers). **Put every kind back on her model** is
one Undo. While the small one answers, her line reads "Asking the quick model".

## What she cannot do yet, said plainly

- She edits only .odt and .ods documents in LibreOffice (.docx and .xlsx are read only).
- In other apps she never presses the dangerous buttons; where an app exposes nothing to accessibility, her reach there is
  keys and pointer aimed at what she can see, never guesses.
- Nothing is tested. Her model's speed on the ThinkPad, the Radeon and the 35B are shown only by your first evening.
