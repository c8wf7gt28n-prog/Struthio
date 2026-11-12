# What's new in Graphite 0.3

November 12, 2026. Guide → What's New opens this page.

**The Field.** Press **F9** (or Arrange → Field, or type `field` in the writing strip). The centre becomes an overview of the
work in this workspace: every source, sheet, exact calculation, page, finding and open question is a sheet, and thin wires
show what feeds what. Material is at the left and conclusions at the right. The selected sheet is the brightest, what
touches it stays near, and the rest steps back. Amber marks what waits for you; a small green square means a record still
agrees with what it came from. Each state has its own mark as well as its colour: half filled for recheck, hollow for open,
crossed for held and for a finding the evidence speaks against, a dash for what cannot be read or reached. Work that is not
finished (running, waiting, failed) appears there too.

**Moving in it.** The arrow keys go from column to column and follow a wire when one leads there. **Enter** opens the real
page for the selected sheet in its own room. **F9** brings the Field back with the same sheet selected and in view. **A**
goes to the next thing that waits for you (Shift+A the one before). Home and End go to the first and last sheet. **R** looks
again, and asks once more for anything that could not be read. **Esc** goes back to where you were, with the keyboard where
it was and the bars as they were. Tab leaves the Field as it leaves anything else. A click selects; a double click opens.

**Stacy says it in staC.** staC, said Stacy, is Graphite's command language, and in the Field it has a face. In the
Illustrated desk Stacy's still After Midnight portrait stands in a rail at the right, and under her the rail shows the staC
line for the selected sheet: the exact read-only pipeline that reads that object. **S** puts that line in the writing strip
to read or change (Ctrl+Enter there runs it). **Shift+Enter** runs it as it is, and the answer appears in the working area
under the Field: for a calculation, the inputs it used with their cells and conditions; for a finding, the sources that
support it; for a sheet, where it came from and whether it still agrees. The rail takes only the room the columns leave:
on a narrow screen, at a large reading size, or in the ASCII or Clean desk it gives way and the same line is in the foot;
the keys work the same.

**What can be done with a sheet.** Right-click a sheet, or press the Menu key, for the desk's own menu: Open, What feeds it,
What it feeds, Inspect in the line, Run its staC, Ask Graphite about this, Copy its name. An empty place of the Field offers
Look again, the other face, Back, and this face in staC.

**This computer's network.** Press **N** in the Field. The same drawing shows the network interfaces with their rates, the
programs that hold connections, and the places they reach or the ports they wait on, each with its staC line. Enter on one
opens Log on its Network stream, filtered to it. **W** returns to the work. Nothing shown there leaves the computer, and no
capture is started.

**Reading comes first.** A sheet is never squeezed below the size its words need. When the sheets do not fit, the Field
scrolls, both ways, and the selected sheet is always brought wholly into view. Lettering follows your reading size; at a
large size on a small screen the head and the foot shorten so that a whole sheet still fits between them.

**It shows what is there now.** The Field reads the workspace each time it comes to the front, because a sheet's state can
change when a file changes on disk, which no record notices. It reads the newest records of each kind up to a ceiling
(60 of most kinds, 300 pages, 40 findings an investigation) and says in amber how many it left out. Showing it adds nothing
to your timeline. A record that cannot be read is drawn as not read, never as current, and the status line says so in words.
A sheet in your Office whose source lives in another workspace is drawn quietly as elsewhere, not as an alarm.

**Under the hood.** No new operation or setting: the Field reads through the same dispatcher as everything else. One test
(`tests_integrated/test_model_settings.py`) used small made-up process numbers and could signal a real process when run as
the administrator in a container; it now uses numbers no process can have.

**Not done, said plainly.** Graphite 0.3 has not run on the ThinkPad, and no model has answered inside it; everything here
was checked offscreen in a build container. Wires that cross several columns pass under the sheets between. A PDF source
opens through its own job, as before. Methods and files with records of their own are not sheets yet. The Field reads on the
window's own thread: about a tenth of a second for a small workspace, close to a second at the record limits. Twenty older
tests and ten older window checks still fail because they describe the earlier desk.
