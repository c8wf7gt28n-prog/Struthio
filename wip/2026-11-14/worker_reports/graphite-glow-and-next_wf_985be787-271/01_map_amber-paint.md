{
 "summary": "Read only; nothing was run, so every strength below is a starting value to tune by eye. Tree: /home/user/Struthio at commit e7d7a8c; paths are relative to it.\n\nHow the green glow is made (workbench/field_qt.py), to reuse as is:\n- `_halo(p, rect, colour, strength)` at 846-853: three rectangle outlines, widest and faintest first (grow 7/4/1.5, width 8/5/2.5, alpha .05/.09/.17, all times the scale). It returns at once when `self.texture` is false.\n- `_mark` at 855-865: a radial gradient disc of radius 2.6 marks behind a settled mark.\n- `_wires` at 830-832: the wire path stroked twice, wide and faint, under the line.\n- `_light` at 764-772: the pointer's pool on the ground.\n- The gate is `self.texture`, set from session key 'desk_art' in workbench/field_page.py:99-101 and workbench/boss_qt.py:300. Outside the Field the gate is the test in workbench/desktop_header_qt.py:112-114.\n\nAmber glow should do two jobs, each in its own place:\n1. **Where the keys go.** One outer halo on the desk at a time: the Field's selected sheet, the reading page, or the writing line.\n2. **What waits for you.** The Approve button, the state mark of a waiting sheet, the box that holds the go, and perhaps the recheck wires.\n\nSelection and hover use the halo outside a sheet; \"waits\" is said inside the sheet at its mark. So a sheet can show both without mixing.\n\nStrongest candidates, in order: the Approve button (field_qt.py:400-410), the selected sheet (880-891), the waiting marks (899-911), the writing line's focus (typebar_qt.py:475-484), then the reading page and the DO box.\n\nWhere green and amber meet:\n- **Selected sheet under the pointer:** amber wins. Line 882 already excludes the selected sheet from the green halo.\n- **Approve under the pointer:** the halo turns green and the button stays amber. One colour per halo, never both.\n- **Waiting sheet under the pointer:** green outside, amber at the mark inside.\n- **Recheck wire of a hovered sheet:** stays amber (line 829) and never takes the green underlay (line 830).\n\nMost amber outside the Field is style-sheet colour, not QPainter. workbench/field_page.py and workbench/home_qt.py paint no amber. workbench/chain_menu.py is style sheet only. Leave-outs and rule conflicts are in the entries and cautions.",
 "places": [
  {
   "where": "workbench/field_qt.py:400-410 (_keys_line, the item whose key is G); reached from the foot at 1031-1033 and 1054-1058 and from the reading page's foot at 633",
   "what": "The Approve button: a filled AMBER_EDGE box with GROUND lettering, then what it would apply. It is the change that waits in Talk for the owner's go. WAITS, in its purest form.",
   "how_drawn": "QPainter custom paint. Today only line 405 glows: a green _halo at 1.8 while the pointer is on it.",
   "glow_idea": "A still amber halo at rest, about strength 2.0, so the thing that waits is the warmest light on the surface. Under the pointer the halo turns green (the 1.8 that exists) and the button stays amber. One halo, one colour at a time.",
   "value": "high",
   "how_to_do_it": "Replace line 405 with one call: self._halo(p, box, t.READY if box.contains(self._mouse) else t.AMBER_EDGE, 1.8 if box.contains(self._mouse) else 2.0). _halo already returns on the Clean desk, so no new gate. Hover changes already repaint the whole view (line 464).",
   "risk": "In the foot the outer ring is cut by about 4 px at the widget's bottom edge, as the green one is today. No check in the tree looks at Field pixels."
  },
  {
   "where": "workbench/field_qt.py:880-891 (_sheet: edge at 885-886, corner ticks at 887-891); also the programs shelf, which is the same _sheet with field.compact",
   "what": "The selected sheet: a 2 px AMBER_EDGE edge and four corner ticks, amber only while the Field has focus (LINE_STRONG otherwise). SELECTED and HAS THE KEYBOARD.",
   "how_drawn": "QPainter custom paint. No glow today; the green hover halo at 883 is for the other sheets.",
   "glow_idea": "An amber halo round the selected sheet while the Field has the keyboard, about strength 1.8. No halo when the keyboard is elsewhere: the sheet stays selected by its ticks, and the amber light moves to wherever the keys now go.",
   "value": "high",
   "how_to_do_it": "At line 883 add a second branch: elif selected and focus: self._halo(p, r, t.AMBER_EDGE, 1.8). It is drawn before the fill, as the green one is, so only the outside shows. Gate is inside _halo. Focus changes already repaint the widget.",
   "risk": "The file's first lines say the selected sheet is the brightest. Green is more luminous than amber at equal alpha, and the hover halo is 1.5, so 1.8 may still read dimmer than a hovered neighbour; tune on the real screen. On the shelf the row gap is 14 px times scale (field_model.py:320) and the halo reaches 11, so it clears the next sheet. The halo goes out while a popup menu holds focus, as the amber edge does today."
  },
  {
   "where": "workbench/field_qt.py:899-911 (_sheet: state colour 899, _mark call 907-908, state word 909-911); marks drawn by _mark 855-878",
   "what": "The state mark and state word (RECHECK, OPEN, HELD, waiting, failed) of a sheet whose state is in ATTENTION (field_model.py:27), in AMBER_EDGE and kept at 0.85 ink or more even on far sheets. WAITS.",
   "how_drawn": "QPainter custom paint. Only settled marks glow today (radial disc, 861-864).",
   "glow_idea": "A small amber halo round the 8 px mark box: strength 1.0 on the selected and touching sheets, 0.7 further away. Use the outline halo, not the radial disc: the disc would fill a hollow mark and make 'open' look like 'current', and the shapes are the signal that does not depend on colour. Leave the word unglowed. Keep the sheet's outer halo for selection and hover, so a waiting sheet under the pointer is green outside and amber inside.",
   "value": "high",
   "how_to_do_it": "Before line 908: if obj.state in ATTENTION: self._halo(p, box, t.AMBER_EDGE, 1.0 if depth <= 1 else 0.7). Gate is inside _halo. The halo reaches 11 px times scale and stays inside the sheet's 12 px padding.",
   "risk": "A desk with many waiting sheets gets many small lights; that is the meaning, but do not raise the strength. The faint outer ring passes under the first letter of the state word and over the 'changed lately' corner."
  },
  {
   "where": "workbench/typebar_qt.py:475-484 (TypeBar.paintEvent); the style rule at 349 (QLineEdit#OneBox:focus border-color AMBER_EDGE); event filter at 560-562",
   "what": "The writing line. When it has focus its border turns AMBER_EDGE by style sheet. HAS THE KEYBOARD, on every page of the desk.",
   "how_drawn": "The amber is a QSS rule. The band behind it is custom paint (paint_band plus two LINE_STRONG ticks).",
   "glow_idea": "While the writing line has focus, a tight amber halo on the band round the line and its submit button together, reaching about 6 px. With the selected-sheet halo gated on focus, exactly one amber keyboard halo shows on the desk at a time.",
   "value": "high",
   "how_to_do_it": "In paintEvent after paint_band: if self.box.hasFocus() and the desk is not Clean, draw two or three AMBER_EDGE outlines round self.box.geometry().united(self.send.geometry()). The band leaves only about 6 px above and below, so use smaller grows than the Field's (for example 1.5 and 4). In the event filter at 560-562 add FocusIn and FocusOut on self.box to call self.update(). Gate as desktop_header_qt.py:112-114 does. In boss_qt.choose_art (291-304) add bar.update() after bar.align().",
   "risk": "Do not use a QGraphicsDropShadowEffect on the line edit: it redraws the field through a pixmap on every cursor blink and softens the text. tools/check_desk_ui.py:462-478 compares band pixels with the grain tile and only excludes the box's columns plus 2 px; a focused halo adds differing pixels there."
  },
  {
   "where": "workbench/field_qt.py:566-576 (_reading; the page's edge at 576)",
   "what": "The page shown over the work (the brief, the doubt, the steps, the key card): opaque GROUND with a 1.4 px AMBER_EDGE edge, the work veiled behind it. It takes the reading keys. HAS THE KEYBOARD.",
   "how_drawn": "QPainter custom paint.",
   "glow_idea": "An amber halo round the page at strength 1.0 while the Field has focus. It lifts the lit page off the receded work, which is the mood the veil at 575 is already after.",
   "value": "medium",
   "how_to_do_it": "Before line 576: if self.hasFocus(): self._halo(p, r, t.AMBER_EDGE, 1.0). Gate is inside _halo. _halo saves and restores the painter, so the pen set at 576 is unaffected.",
   "risk": "In a tight window (edge 6 px, line 542) the outer ring is clipped. While this page is up the selected sheet beneath is veiled, so its halo dims with it; that is right."
  },
  {
   "where": "workbench/field_qt.py:707-743 (_do in Stacy's rail: box 721, DO 723, 'asks' 733, the G lines 734-739); the foot's DO line at 1054-1058",
   "what": "What can be done about the selected sheet: numbered steps, 'asks' beside a step that changes something, and 'G  \u2026' for the change that waits. Steps offered are a menu; only the G line WAITS.",
   "how_drawn": "QPainter custom paint: a box with an AMBER_EDGE edge at 0.8, AMBER_TEXT words.",
   "glow_idea": "An amber halo round the rail's box only while self.go is set, strength 1.0: Stacy is holding something for you. No glow for steps alone, since offering is not waiting. In the foot the Approve button carries the glow; the word DO stays plain.",
   "value": "medium",
   "how_to_do_it": "Before line 721: if self.go: self._halo(p, box, t.AMBER_EDGE, 1.0). Gate is inside _halo.",
   "risk": "The box has a 10 px margin in the rail and the halo reaches 11, so the outer ring is clipped by a pixel at the window's edge. It sits over the foot of the portrait; check it against the plate."
  },
  {
   "where": "workbench/field_qt.py:814-837 (_wires: colour 829, green underlay 830-832, dashed pen 833-834)",
   "what": "A wire that asks for a recheck: AMBER_EDGE, dashed, always at full strength so it can be found without selecting an end. WAITS (recheck). Live wires carry a green light; stale ones carry none.",
   "how_drawn": "QPainter custom paint: a cubic path, with the underlay for live wires only.",
   "glow_idea": "A faint amber light along a recheck wire, half the live wire's: two passes at 7 and 4 px, alpha about .03 and .06, times 1.8 when it touches the selected or hovered sheet. A waiting chain then reads as a warm thread through the green.",
   "value": "medium",
   "how_to_do_it": "After line 832 add an elif branch for self.texture and link.stale with the same two-pass loop in t.AMBER_EDGE. The gate is that self.texture test.",
   "risk": "The 0.4.6 notes say a stale wire carries no light; that was about green, and the 0.4.7 notes must restate it. A desk with many stale wires gets an amber haze; keep the alpha low. Decide with the owner, since it changes a sentence already published."
  },
  {
   "where": "workbench/programs_qt.py:362-371 (MenuRow.paintEvent, wash at 365); workbench/context_menu.py:1904-1918 (ContextRow.paintEvent, wash at 1907, checked mark at 1912-1915)",
   "what": "The row in hand in the cat's programs list, the System menu and the cascading right-click menu: a flat AMBER_SOFT wash. The pointer's row takes focus (programs_qt.py:340-343), so it is one row: SELECTED and HAS THE KEYBOARD. ContextRow also draws a 2 px AMBER_EDGE mark under a checked choice.",
   "how_drawn": "QPainter custom paint (fillRect).",
   "glow_idea": "Light the row from its left edge: a 2 px AMBER_EDGE bar at x 0 and a horizontal gradient of AMBER_EDGE from alpha about .22 to 0 across the icon column, over the wash. The Clean desk keeps the flat wash. Leave the checked mark as it is.",
   "value": "medium",
   "how_to_do_it": "One helper in programs_qt.py, called after the fillRect at 365 and at context_menu.py:1907. Gate on self.menu.host's session 'desk_art', with the try/except of desktop_header_qt.py:112-114.",
   "risk": "The QMenu-based menus are style-sheet only (chain_menu.py:91-95, boss_theme.py:57-59) and would not match unless their selected-item rule gets a qlineargradient too. Menu checks in tools may read row colours."
  },
  {
   "where": "workbench/desk_qt.py:327-335 (paint_band; the rule at 333-334), called from shell2.py:620-623 and typebar_qt.py:475-480",
   "what": "The 2 px AMBER_EDGE rule along the foot of the head band and the top of the lower band. Chrome: it means none of selected, keyboard or waits, but it is the most visible orange on every page.",
   "how_drawn": "QPainter custom paint (fillRect over the grain tile).",
   "glow_idea": "A still bloom on the band side of each rule: a 10 px vertical gradient of AMBER_EDGE from alpha about .16 to 0. Pure mood. If done, do it last and ask the owner, because it lights something that carries no state.",
   "value": "medium",
   "how_to_do_it": "In paint_band after line 334, a QLinearGradient fillRect above the rule for TopBar2 and below it for the lower band. Gate on widget.host's session 'desk_art'. choose_art (boss_qt.py:291-304) must also call host.shell2.top.update().",
   "risk": "High. tools/check_desk_ui.py:202-220 and 462-478 compare band pixels with the grain tile and with each other; the bloom changes them. It also spreads amber onto something that does not wait."
  },
  {
   "where": "workbench/shell2.py:1742 (StagedRun) and 1813 (PlanRun); for comparison 2080-2084 (ProgramReviewRun, filled AMBER_EDGE by style sheet)",
   "what": "The Approve buttons in Talk: the same waiting change the Field's Approve stands for. WAITS. They are drawn as ordinary word buttons, not amber.",
   "how_drawn": "QPushButton with theme style sheet; not custom paint.",
   "glow_idea": "If the Field's Approve glows, its twin in Talk should too, or one waiting change looks different in two places. Use the technique of DesktopMonitors.relight: a QGraphicsDropShadowEffect, offset 0, blur about 14, AMBER_EDGE at alpha .85, removed when the button is disabled after the run.",
   "value": "medium",
   "how_to_do_it": "Set the effect where the button is made (1742, 1813) and clear it where the run disables it (1760 for staged; the matching place in run_plan from 1820). Gate as desktop_header_qt.py:112-114 does, and have choose_art re-apply it.",
   "risk": "The effect draws outside the button into the card; the card's margins are 10 and 8 px, so a blur of 14 is partly clipped. A button is small and has no blinking cursor, so the cost is fine."
  },
  {
   "where": "workbench/field_qt.py:788-799 (_head: the census at the right end)",
   "what": "The head's counts, drawn QUIET, including 'N to recheck' (field_model.py:291-293). It is the only place that says something waits when the waiting sheets are scrolled out of view.",
   "how_drawn": "QPainter custom paint (text).",
   "glow_idea": "New element, not a glow on existing amber: a small amber mark with a halo before the counts whenever any sheet needs attention. One lamp for the whole desk that says something waits; A goes to it.",
   "value": "medium",
   "how_to_do_it": "At 797-799: if any(o.needs_attention() for o in self.field.objects), draw an 8 px box left of the census with self._halo(p, box, t.AMBER_EDGE, 1.0) and self._mark. Gate is inside _halo; the mark itself would also show on Clean.",
   "risk": "It adds a sign the owner has not asked for; needs a decision on which mark shape to use. The census gives way when the head is narrow (791-793), and the lamp must give way with it."
  },
  {
   "where": "workbench/field_qt.py:783-784 (_head: the showing face's word and its 2 px underline); 777-779 (the word FIELD)",
   "what": "The face that is showing (WORK, PROGRAMS, NETWORK) in AMBER_TEXT with an AMBER_EDGE underline: SELECTED. The word FIELD in AMBER_EDGE is the surface's name, not a state.",
   "how_drawn": "QPainter custom paint.",
   "glow_idea": "Optional and small: a bloom under the underline, the wire-underlay trick (the same line at 6 and 4 px, alpha .07 and .14). Leave the word FIELD alone: it is a label.",
   "value": "low",
   "how_to_do_it": "Before line 784, when self.texture, draw the two wider faint lines first.",
   "risk": "Easy to overdo; the head is where the eye rests."
  },
  {
   "where": "workbench/field_qt.py:920-928 (the what-if's first fact line and broken edge); 1050-1052 (the foot); 983-994 (the note in the 'more' strip)",
   "what": "The what-if marks: what a sheet would say, a dashed AMBER_EDGE edge 3 px outside it, and the what-if in words. Hypothetical. It WAITS only when Stacy staged a change (field_page.py:417-441) and self.go is set.",
   "how_drawn": "QPainter custom paint.",
   "glow_idea": "Leave it. The dashed edge already reads as 'would' without colour. A halo would make a hypothetical as loud as a real wait, and it would sit on the same rings as the green hover halo.",
   "value": "low",
   "risk": "If the owner wants it anyway: only while self.go is set, at 0.6, and not on the sheet under the pointer."
  },
  {
   "where": "workbench/field_qt.py:598-615 and 630-632 (reading page: headings, key names, bullets, 'more \u2193'); the key card is the same page (KEYS 37-65, show_keys 278-279)",
   "what": "AMBER_TEXT headings and key names and AMBER_EDGE bullets on a page for reading. On 'The desk, checked' the heading is WAITS FOR YOU.",
   "how_drawn": "QPainter custom paint (text).",
   "glow_idea": "Leave it. This is reading matter, and the file's own rule is that reading comes first. Thirty glowing key names on the key card would be clutter. The page's edge carries the light.",
   "value": "low"
  },
  {
   "where": "workbench/field_qt.py:975-997 (_more strip, note at 993-994); 1002 (_empty problem); 531 (paint error); 1023-1035 (foot's kind and state line); 905 (kind tag of a question or total); 933-940 (the wire's 'recheck' word)",
   "what": "Amber words: notices, the selected sheet's description in the foot, a kind tag, a wire's label.",
   "how_drawn": "QPainter custom paint (text).",
   "glow_idea": "Leave them. They are said in words over or beside the sheets; a glow behind small text blurs it and adds nothing the mark, the wire and the Approve button do not already carry.",
   "value": "low"
  },
  {
   "where": "workbench/field_qt.py:892-894 (the turned corner); 694 (the word staC at the head of the rail's box)",
   "what": "The amber corner marks a sheet whose record changed in the last twelve hours. The word staC is drawn AMBER_TEXT above green staC code. Neither is selected, keyboard or waits.",
   "how_drawn": "QPainter custom paint.",
   "glow_idea": "Leave both. Glowing them would spend amber light on things that do not wait. Line 694 also sits against the 0.4.6 sentence that staC is green wherever it is shown.",
   "value": "low",
   "risk": "Line 694 is a rule conflict worth settling before any glow work nearby."
  },
  {
   "where": "workbench/boss_qt.py:137 (ArtPanel, the ASCII desk's '[>_]'); 207-262 (PanelInk); 71 (WorkshopStrip's READY square); FACE_MARK and BRACKET at 13 and 18-19, drawn in the Field at field_qt.py:655-660",
   "what": "ArtPanel's ASCII banner ends in an AMBER_EDGE prompt mark: ornament. PanelInk and the ASCII marks draw in TEXT, QUIET or FAINT; there is no amber in them. WorkshopStrip has a 7 px green square.",
   "how_drawn": "QPainter custom paint; plates are images.",
   "glow_idea": "Optional: a small radial amber pool behind '[>_]' (radius about 28 px, alpha .18 to 0), the technique of _mark. The panel is already hidden on the Clean desk (line 99). Nothing to glow in PanelInk or the ASCII marks. The green square could take the green disc of _mark.",
   "value": "low",
   "risk": "Pure decoration on the ASCII desk only."
  },
  {
   "where": "workbench/desk_qt.py:405-423 (InkWord.marked and paint); workbench/pane_qt.py:156-168 (PaneTab); workbench/log_qt.py:273-283 (the Log's stream tabs)",
   "what": "The 3 px mark under a band word or a pane tab: PENCIL (#f2a369) for the chosen one, ERASER_MARK (#dd854b) for hover and for keyboard focus alike.",
   "how_drawn": "QPainter custom paint (fillRect).",
   "glow_idea": "Leave until hover and focus are told apart here. Today the pointer and the keyboard draw the same orange mark, so an amber glow would make a hovered tab look like it has the keyboard. Once hover is green, a 5 px upward bloom over the chosen mark is a fair small addition.",
   "value": "low",
   "risk": "These three places did not get the 0.4.6 green hover; that is a rule gap of its own."
  },
  {
   "where": "workbench/shell2.py:379-383 (LibraryDelegate's Arrived badge); 2519-2526 (StageBar's current step); 463-470 (Mark); 406 (Timeline's selected row text)",
   "what": "The Arrived count is a dark amber pill: files that wait for a decision. The stage bar's current step is a dark amber bar with an AMBER_TEXT name. Mark is the brand tile. All use AMBER (#4b2a14), the dark wash, not the bright edge colour.",
   "how_drawn": "QPainter custom paint (item delegate and widgets).",
   "glow_idea": "Optional for the badge and the current step: one or two AMBER_EDGE outlines within 4 px, because a delegate is clipped to its row. Leave Mark and the Timeline text.",
   "value": "low",
   "risk": "These belong to older pages; check they are still reachable before spending time."
  },
  {
   "where": "workbench/datasheet_qt.py:44-52 (the PDF crop's highlight) and 61-79 (EvidenceLink); workbench/sheet_workbench_qt.py:174-219 (RowTrace); workbench/chain_workbench_qt.py:73-91 (ChainTrace); workbench/finder_qt.py:177-182 (the selected tile in Files)",
   "what": "Amber routes from the selected rows to the chain or to their source, and the selected file tile: SELECTED.",
   "how_drawn": "QPainter custom paint.",
   "glow_idea": "Leave the PDF highlight: it sits on a page image, and a glow does not read on a light ground. The routes could take the wire underlay (the same line wider and fainter beneath). The selected tile could take one AMBER_EDGE outline. All optional.",
   "value": "low",
   "risk": "None of these widgets knows the desk art today; each needs the gate threaded in."
  },
  {
   "where": "workbench/pulse_qt.py:103-117; workbench/thumbnails.py:108-140 and workbench/finder_qt.py:88-108; workbench/trash_can_qt.py:110-116; workbench/idle_display_art.py; workbench/arcfairy_qt.py:41-59",
   "what": "Amber sparklines for CPU and memory (live readings, which the rule makes green); folder icons with an amber flap; the trash can's drop line; the idle display's amber captions; an older orange radial glow in a rehearsal module.",
   "how_drawn": "QPainter custom paint; icons are cached images.",
   "glow_idea": "Leave all of them. The sparklines are live and would be green by the rule. Icons are ink, not state. The idle display is its own artwork and moves.",
   "value": "low"
  }
 ],
 "cautions": [
  "Nothing was run. Strengths and alphas are starting values; an offscreen grab can compare the two halos' brightness, but how amber sits beside green on the ThinkPad's screen is for the owner's eye.",
  "Glow in AMBER_EDGE (#ff9a36). AMBER and AMBER_SOFT are the same dark brown (#4b2a14, boss_theme.py:12) and will not glow; AMBER_TEXT is for lettering.",
  "Green is more luminous than amber at equal alpha. The file promises the selected sheet is the brightest (field_qt.py:4), so the selected halo needs a higher strength than the hover's 1.5.",
  "Never draw a green and an amber halo on the same ring: at these alphas they mix to a dull yellow. One halo slot, one colour. The pointer's pool (_light) lies under everything and may meet an amber halo on open ground; that overlap is small and acceptable.",
  "Every new glow outside the Field needs the Clean gate and a repaint when the desk art changes. boss_qt.choose_art (291-304) today refreshes only the pointer, ArtPanel and PanelInk, the Field, the type bar's layout and the monitors.",
  "Do not try to glow the outside of a popup menu. A popup cannot draw beyond its own window without a translucent background, and that needs a compositor the ThinkPad's X session may not have.",
  "Do not put a QGraphicsDropShadowEffect on the writing line or any text input. Paint the halo in the parent's paintEvent instead.",
  "tools/check_desk_ui.py (202-220, 462-478) compares band pixels with the grain tile. Any light painted on a band changes its result.",
  "No check in the tree looks at the Field's painting: nothing under tests_integrated or tools mentions field_qt, texture or _halo. The Field's glow has no regression net.",
  "Three custom-painted places still answer the pointer in orange, the same mark as keyboard focus: desk_qt.py:410, pane_qt.py:158, log_qt.py:281. Two style rules do the same: typebar_qt.py:351 and sheet_workbench_qt.py:53-56. Amber glow there would make hover look like focus.",
  "Not every amber thing waits. The 'changed lately' corner, the word FIELD, the word staC in the rail, the band rules, folder icons and the Pulse sparklines are amber for other reasons; lighting them thins the meaning of the lights that do wait.",
  "The 0.4.6 notes say a stale wire carries no light. If recheck wires get an amber light, the 0.4.7 notes must say the rule changed and why."
 ]
}