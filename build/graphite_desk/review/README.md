# The Graphite desk: what to review

For R.A. Peddycoart, November 7, 2026. Your brief asked to see the desk with both launch menus closed, the cat's programs list,
the upper-right system menu, two right-click menus on different kinds of objects, one real command running against the selected
object, and a short map of where the displaced controls went. Then you replaced Log's notes with the network. Every picture here
is the real Graphite window, made in one run by `tools/desk_review.py` in the build container: offscreen, with a scratch
workspace, starting no job, model, capture or session command. Every word in each picture was checked whole. Nothing here has
been tried on your ThinkPad yet.

## The pictures

| File | What to look at |
|---|---|
| `Graphite_Review_01_Desk_Menus_Closed_1920x1200.png`, `…_1366x768.png` | The quiet desk. Two graphite bands, Graphite in the script at the upper left, the erased Graphite symbol at the far right, the eight menus centred on the work, the two panes one width, Trash at the lower right of the left pane, the cat in the lower band, and the writing line with its four modes. At 1366 by 768 the Finder's own view words fold into ⋯; the desk's words never shorten. |
| `Graphite_Review_02_Cat_Programs_List_…` | The cat's programs list: every program and capability once, A to Z, one plain name and one small graphite icon each, then Explore the workshop. The cat has its paw up and yellow eyes while the list is open. "needs setup" means the program was not found in this container. |
| `Graphite_Review_03_System_Menu_…` | The System menu: Game first, Stop all jobs beneath, then the process list. Two queued Agenda items show the queue's order (the place numbers 1 and 2) apart from each item's niceness (its slider). Then Graphite services, and, set apart, Log out, Exit Graphite, Restart and Shut down with what each affects. The build container has no login session, so Log out, Restart and Shut down say unavailable here; on your computer logind decides. At 1366 by 768 the menu scrolls. |
| `Graphite_Review_04_Right_Click_Selected_Passage_…` | First kind of object, selected words on a page. The menu names the passage, its page and revision at the top. Changes come first (Bold, Italic, Underline, Plain, Paragraph style, Move to notes), then Inspect in the line (the equivalent staC command), Ask Graphite about this and Search, and the text edits last. |
| `Graphite_Review_05_Right_Click_Two_File_Revisions_…` | Second kind of object, two revisions of one file selected in Files. Compare revisions comes first and passes the two actual files to the compare; Move to Trash is last. |
| `Graphite_Review_06a_Bold_Before_1920x1200.png` and `…06b_Bold_After_1920x1200.png` | One real command against the selected object. Before: Bold under focus in the passage's menu. After: the words are bold where they were, the page's foot says revision 3, and the status line says what was done. Bold went through the same dispatcher and checks as everything else, with the page's id and the revision seen when you right-clicked. Had the page changed in between, it would have been refused with nothing done. Ctrl Z takes it back. |
| `Graphite_Review_07_Symmetry_Overlay_…` | The axis (pink) and the mirrored guides (dashed yellow). `tools/check_desk_ui.py` measures every pair at 0 px at three window sizes and three text sizes, and now in the window's own pixels too. |
| `Graphite_Review_08_Log_Network_Half_This_Computer_…` | Log at Half on its Network stream, with real data from the build container: its interfaces and rates, and its open connections with their programs (one is the review tool's own loopback connection). This container's own address, 192.0.2.2, happens to sit in a documentation range, but it is real here. The capture's reason is shown as Graphite gives it: there is no capture tool here, and the reason lists the administrator's steps, which Graphite never runs. At 1366 by 768 the lists stand one above the other, and the reason shows three lines and scrolls. |
| `Graphite_Review_08b_Log_Network_Packets_TEST_DATA_1920x1200.png` | TEST DATA, labelled on the image. The packet stream as Log shows it while a capture runs, made from the network capability's test fixture and read by its own parser. It shows headers only, with one packet pinned and Ask Graphite about this. No real packet stream exists here. |

`review.json` lists each file with what it shows, its size and its hash.

**The short map of displaced controls** is in docs/GRAPHITE_DESK.md, under "Where things went": one line per control, from its
old place to its new path. For example, Nice to the Graphite symbol, Kernel to Commands ▸ Run an operation…, Find to Search
(Ctrl+K), the cat's groups to the programs list, Import and Export to Work and the right-click, and log notes to Log ▸ Network.
docs/DAILY_GUIDE.md describes the new desk for a working day.

## What I chose, and why

1. **The first mode is Assignment, and the one who answers is still Graphite.** Sentences stay clear: "Graphite paused the
   assignment". Calling the assistant itself Assignment everywhere would be a one-word swap if you want it.
2. **Enter never runs staC.** In Assignment, Enter gives your words to Graphite, and typed staC runs only on Ctrl+Enter. The line
   says "staC on Ctrl+Enter" when what you typed is staC. One key, one meaning.
3. **Log still follows events.** Only its notes are gone, as you said. Log has two streams, Events and Network. On any entry,
   Ask Graphite about this takes the place where a note would have gone.
4. **A capture is yours alone to start.** It asks once each time Graphite starts and says exactly what it records: headers only,
   this computer's interfaces, never promiscuous, at most 60 seconds or 2,000 packets, and nothing leaves the computer. Stop all
   jobs ends it. Graphite never uses sudo. During an assignment Graphite may read what the Network stream shows and may propose a
   capture, but it can never start one.
5. **The cat is pale paper.** It is the band's brightest value, 9.1:1 against the band. Its eyes and paws are graphite, its
   irises turn yellow only while it is attending to you, and its nose and ears are soft pink, so pink still means actions and
   yellow the choice in use. It is placed by its pale coat, as the words are by their ink. Placed by its almost invisible graphite
   outline, the cat stood a pixel inside the band's edge, against the word Log at the other end; the integration fixed that.
6. **The two launch menus are one design**, mirrored about the window's centre point: the cat's list opens up from the lower left
   and the System menu opens down from the upper right, at one width, one row height and one icon column.
7. **Leaving asks first and closes properly.** Log out, Restart and Shut down ask your questions about unsaved work, then confirm
   by naming what they affect. Only then does Graphite close the ordinary way, saving the session and pausing assignments, and
   after that it asks the system. Ending the session ends Graphite at once, so the order cannot be the other way round. Cancel
   stops nothing. A row the system will not allow stays visible, and F1 says why.
8. **The right-click puts changes first.** Then come what the object's state allows, the staC to inspect, the capabilities that
   take it, and the tree's own words. An empty place carries the whole root menu as Root menu ›. Every change is refused if its
   target moved on since you right-clicked. When staC refuses, the menu says "Not run" with the reason, never that it ran.
9. **The menus stay centred on the axis**, and the CPU · GPU · RAM · TXT readings sit beside the symbol, so the head stays
   symmetrical without moving the readings away from where you look for them.
10. **Search is a visible mode**, marked like the others and reached with Ctrl+K, so you can always see where your typing goes.

## Not done or not tried

- Your ThinkPad has not been tried: its display, its logind (Log out, Restart and Shut down) and a real capture with dumpcap or
  tcpdump. None was possible in this container.
- The release payload must be packaged again before the release check's runtime section reads clean.
