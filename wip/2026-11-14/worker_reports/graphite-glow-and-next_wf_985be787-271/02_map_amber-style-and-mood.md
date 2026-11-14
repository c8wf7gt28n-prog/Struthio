{
 "summary": "Read only; nothing was run, so every proposal below is from the code and the two plates, not from a rendered desk. Paths are relative to /home/user/Struthio.\n\n(a) Amber through style sheets and widgets. The app sheet (workbench/theme2.py QSS2 plus workbench/boss_theme.py CHROME_OVERRIDES, set at workbench/qt_app.py:5329) uses amber as flat washes and 2 px edges: the chosen centre tab, the chosen row of a menu, tree or list, checked buttons, the focus rule of the Jot-it-down passage, selection colours, the owner's Talk bubble, and the address in the head. Three places carry their own sheet and so are out of the app sheet's reach: the head band (shell2.py:559), the lower band (typebar_qt.py:345-354) and the pane tab rows (pane_qt.py:187-189). The frame's amber rules and the tab marks are custom paint (desk_qt.py:327-335, 415-423; pane_qt.py:161-168). workbench/concern_qt.py and workbench/workspace_tabs.py set no colour of their own. workbench/qt_master_stop.py:31-34 styles a button that is hidden (shell2.py:516).\n\n(b) Eight treatments, ranked:\n1. The frame's two amber rules spill light into their bands (high).\n2. The writing line has an amber halo while it has the keyboard (high).\n3. What waits for the owner's go is amber and glows: Approve in Talk, and the DO box in Stacy's rail (high).\n4. The chosen tab is lit from its amber underline: centre tabs and pane tabs (medium).\n5. The reading sheet over the Field has an amber halo (medium).\n6. On Today, a card that holds something waiting has an amber top edge and a light under it (medium).\n7. Stacy's face in Talk glows green, as the pointer and the readings do (medium).\n8. Today's workshop plate fades into the page at its edges (low; depth, not glow).\n\nOnly 3 (Talk) and 7 need a QGraphicsDropShadowEffect, each on a small leaf widget as DesktopMonitors.relight does (desktop_header_qt.py:106-122). 1, 2, 5, 8 and the pane tabs are a few lines in painters that exist. The centre tabs and 6 are style-sheet gradients.\n\nClean desk: one predicate (session state 'desk_art' is not 'clean', and no glow when there is no session, as desktop_header_qt.py:112-114 does) read by the painters. boss_qt.choose_art (boss_qt.py:291-304) gains three lines: update both bands and the pane tab rows, re-light the waiting buttons, and call host.shell2.restyle so the gated style-sheet block is added or dropped.\n\nLeft alone, with reasons in the list: the address and the head's words, selected rows, menus and popups, every text edit, the Talk bubbles, the lower band's mode words, the startup screen, and workbench/home_qt.py, which is not the Home the desk shows (qt_app.py:3519-3523 puts finder_qt.FinderPage with shell2.TodayPage there).",
 "places": [
  {
   "where": "workbench/desk_qt.py:327-335 (paint_band); called from workbench/shell2.py:620-623 (TopBar.paintEvent) and workbench/typebar_qt.py:475-484 (TypeBar.paintEvent)",
   "what": "Treatment 1 of 8. The frame's two amber rules: a 2 px AMBER_EDGE line the full width of the window, at the foot of the head band and at the top of the lower (writing and status) band. They bracket the centre and are the most orange on the desk at every moment. Ornament, not a state.",
   "how_drawn": "Custom paint: QPainter.fillRect over the grain tile.",
   "glow_idea": "Each rule spills light into its own band: a vertical gradient of AMBER_EDGE, alpha 0.26 at the rule, 0.09 at 45 percent, 0 at the end, reaching 8 px (desk_qt.BAND_PAD, scaled) upward in the head and downward in the foot. The rule stays opaque and is drawn last. Nothing is drawn on the centre's side.",
   "value": "high",
   "how_to_do_it": "In paint_band, after the grain fill and before the rule's fillRect, fill a QRectF of the band's width by the reach with a QLinearGradient that starts at the rule. Gate with a small predicate in desk_qt, for example glows(widget): the state dict of widget.window().session has desk_art other than 'clean'; False when there is no session. In boss_qt.choose_art add update() for host.shell2.top and host.type_bar. No timer; the bands repaint only on resize and when a child changes.",
   "risk": "Keep the reach inside the band's padding: in the lower band the word boxes start (h - wh) / 2 from the edge, 11 px at 14 pt but as little as 6 px (typebar_qt.py:431), so clamp the reach to that less the rule. tools/check_desk_ui.py compares band pixels with the bare grain tile (lit at 174-181, band_ground and differs at 215-260); it must be run again and may need the Clean desk or a reference that draws the same light."
  },
  {
   "where": "workbench/typebar_qt.py:475-484 (TypeBar.paintEvent); today's rules at typebar_qt.py:345-354; the box's event filter at typebar_qt.py:191 and 560-562",
   "what": "Treatment 2 of 8. The writing line and its submit button: where the keyboard is for most of the day. Today focus is a 1 px amber border (QLineEdit#OneBox:focus) and the submit button is an amber fill.",
   "how_drawn": "QSS rules in the band's own sheet, on a band that already custom-paints its grain, its rule and two hairlines beside the line.",
   "glow_idea": "While the line has the keyboard, an amber halo round the line and its button as one rectangle: three outlines of AMBER_EDGE, grown 6, 3.5 and 1.5 px, 7, 4.5 and 2.5 px wide, alpha 0.06, 0.10 and 0.18 (the Field's _halo recipe, field_qt.py:846-853, a little tighter). No halo without focus.",
   "value": "high",
   "how_to_do_it": "Paint it in TypeBar.paintEvent after paint_band, under the children: the rectangle is box.x(), box.y() to send.geometry().right(), box.height(). Scale the three grows by min(1, (box.y() - 2) / 9.5) so it never leaves the band. In TypeBar.eventFilter add FocusIn and FocusOut of the box: self.update(). Gate with the same predicate as treatment 1; choose_art already reaches the bar (boss_qt.py:301-302) and needs bar.update().",
   "risk": "Do not put a QGraphicsDropShadowEffect on the QLineEdit: the caret's blink would blur the whole line again twice a second, and its context label and clear button would be drawn through the effect. The halo overlaps the top rule's light by a few rows at 14 pt, which reads as the line drawing light from the rule."
  },
  {
   "where": "workbench/shell2.py:1742 (StagedRun), 1813 (PlanRun), 2080-2084 (ProgramReviewRun); disabled at shell2.py:1760, 1825 and in run_program_proposal",
   "what": "Treatment 3 of 8, first site. Approve in Talk: the owner's go for a change that waits. StagedRun and PlanRun are today a bare mono word (button('Approve', 'stac'), with boss_theme.py:60 making the underline transparent), while the Field draws the same act as an amber block (field_qt.py:404-407). ProgramReviewRun is already an amber fill from its own sheet.",
   "how_drawn": "QPushButton styled by the app sheet (two of them) or by its own style sheet (the third), inside a Bubble (QFrame) inside the Talk QScrollArea.",
   "glow_idea": "All three are the Field's amber block (background AMBER_EDGE, text GROUND, padding 4px 12px, weight 600; disabled PANEL and QUIET) and glow while they wait: QGraphicsDropShadowEffect, offset 0, blur 14, AMBER_EDGE at alpha 0.7. The glow goes when the button has been used.",
   "value": "high",
   "how_to_do_it": "One helper beside choose_art in boss_qt.py: waits(button, host) sets the sheet string already at shell2.py:2083-2084, marks the button with a property, and sets or removes the effect by button.isEnabled() and the desk art. Call it where the three buttons are made and again right after each setEnabled(False). In choose_art, call it for every QPushButton of the host that carries the property.",
   "risk": "A disabled button would still cast an amber glow, so the effect must be removed on disable. The effect is clipped by the Bubble (margins 12, 9, 12, 9 at shell2.py:1518) and by the scroll area's viewport: keep the blur at 14 or less, or give the button's row 4 px more room below. Each scroll step re-renders one small button, which is cheap. The button's own sheet uses only tokens, so theme2.Relight leaves it alone."
  },
  {
   "where": "workbench/field_qt.py:707-743 (_do), the box drawn at 720-721",
   "what": "Treatment 3 of 8, second site. The DO box under Stacy's portrait in the rail: the steps for the selected sheet and, when something waits in Talk, the G line that approves it. It has an amber edge at alpha 0.8.",
   "how_drawn": "Custom paint in FieldView.",
   "glow_idea": "While self.go is set (something waits for the owner's go) the box has the Field's halo in AMBER_EDGE at strength 1.3. With steps only and nothing waiting, no halo.",
   "value": "medium",
   "how_to_do_it": "One line before the drawRect at field_qt.py:721: if self.go: self._halo(p, box, t.AMBER_EDGE, 1.3). _halo already returns on the Clean desk (self.texture).",
   "risk": "The box is 10 px (scaled) from the window's right edge and the halo reaches 11, so its outer ring is cut by one pixel at the edge; harmless. The heading 'staC' in the neighbouring box is AMBER_TEXT (field_qt.py:694) though staC is green everywhere else; do not add an amber glow to it."
  },
  {
   "where": "workbench/boss_theme.py:62-63 and workbench/theme2.py:80 (QTabBar::tab:selected); the tabs are workbench/workspace_tabs.py, which sets no style",
   "what": "Treatment 4 of 8, first site. The chosen tab of the centre: AMBER_TEXT words, a flat AMBER_SOFT ground and a 2 px AMBER_EDGE underline.",
   "how_drawn": "QSS rule in the app sheet.",
   "glow_idea": "The tab is lit from its underline: its ground becomes a vertical gradient, #8a5120 (AMBER_SOFT moved 35 percent toward AMBER_EDGE) at the underline, AMBER_SOFT from 55 percent of the height upward. Words and underline unchanged.",
   "value": "medium",
   "how_to_do_it": "QSS only: QTabBar::tab:selected {background: qlineargradient(x1:0, y1:1, x2:0, y2:0, stop:0 #8a5120, stop:0.55 #4b2a14, stop:1 #4b2a14);}. Put it in a glow block that shell2.chrome_css (shell2.py:276-323) appends only when the desk is not Clean; the window's sheet wins over the app's. Shell2.restyle (shell2.py:2733-2748) builds that sheet and re-polishes, so choose_art calls host.shell2.restyle(getattr(host, 'reading_profile', None)).",
   "risk": "restyle re-polishes every widget of the window once per change of desk art, the same cost as a change of reading size. Keep the gradient on background only; a gradient on a border is drawn poorly when the sides differ."
  },
  {
   "where": "workbench/pane_qt.py:134-168 (PaneTab; mark_colour 156-159, paintEvent 161-168)",
   "what": "Treatment 4 of 8, second site. The chosen tab of each pane (Files, Machine, Settings; Talk, Activity, Context): its word in TEXT, semi-bold, and a short 3 px mark in desk_qt.PENCIL under it.",
   "how_drawn": "Custom paintEvent on a QPushButton; the row's own sheet only sets the font.",
   "glow_idea": "The same light as the centre tab: above the mark and exactly as long as it, a vertical gradient of the mark's own colour, alpha 0.30 at the mark and 0 at 45 percent of the tab's height. Only for the chosen tab, not for hover or focus.",
   "value": "medium",
   "how_to_do_it": "In PaneTab.paintEvent, before the text: when isChecked() and the desk glows, fill QRect(mark x, height - MARK - reach, mark length, reach) with a QLinearGradient; then the text; then the mark, opaque, as now. The predicate reads self.window().session. choose_art updates the PaneTabs rows.",
   "risk": "tools/check_desk_ui.py counts pixels that equal PENCIL exactly (275-286, 685): the mark's own pixels must stay opaque and the light must not enter its rows. The mark is '#f2a369' (desk_qt.py:243), not AMBER_EDGE '#ff9a36'; use the mark's colour for its light so they read as one."
  },
  {
   "where": "workbench/field_qt.py:566-636 (_reading), the page drawn at 576; its rectangle at 541-544",
   "what": "Treatment 5 of 8. The page read over the work (the brief, the keys, a trace, a doubt): opaque GROUND with a 1.4 px amber edge over the dimmed sheets. While it shows it has the keyboard.",
   "how_drawn": "Custom paint in FieldView.",
   "glow_idea": "The Field's halo round the page in AMBER_EDGE at strength 1.2: three outlines reaching 11 px (scaled). Not in the tight layout, where the margins are 6 px.",
   "value": "medium",
   "how_to_do_it": "One line before the drawRect at field_qt.py:576: if not tight: self._halo(p, r, t.AMBER_EDGE, 1.2). The margins there are 20 px at the sides and 14 px above, so the halo fits inside the clip set at 574. _halo already returns on the Clean desk.",
   "risk": "None beyond three more outlines on each repaint of the page."
  },
  {
   "where": "workbench/shell2.py:2369 (the cards of TodayPage), 2446-2479 (fill); QFrame#Card2 at workbench/theme2.py:116 and workbench/boss_theme.py:54-55",
   "what": "Treatment 6 of 8. Today's cards 'Ingress' and 'Waiting for you': what has arrived and what needs the owner. Today they look the same whether or not anything waits.",
   "how_drawn": "QFrame styled by the app sheet (CARD ground, 1 px LINE edge, square).",
   "glow_idea": "A card that holds something waiting has a 2 px AMBER_EDGE top edge and a light under it: a ground gradient from #3a2e1c (CARD moved 16 percent toward AMBER_EDGE) at the top to CARD at 30 percent. The edge is the state and stays on the Clean desk; the gradient is the glow and does not.",
   "value": "medium",
   "how_to_do_it": "In fill(), set a property on each card only when it changes (waits = bool(waiting) for Ingress, bool(self._waiting or others) for Waiting for you), then unpolish and polish, as desktop_header_qt.py:156-159 does. Base rule in CHROME_OVERRIDES: QFrame#Card2[waits=\"true\"] {border-top:2px solid AMBER_EDGE;}. The gradient rule goes in the gated glow block of treatment 4.",
   "risk": "fill runs every 4 s (shell2.py:2390), so the property must be compared before it is set or the card is re-polished for nothing. A 2 px top edge moves the card's contents by one pixel when it appears; give every Card2 a 2 px top border in LINE so only the colour changes."
  },
  {
   "where": "workbench/boss_qt.py:160-168 (PanelInk.refresh), painted at 221-224 and 229-261; placed at workbench/shell2.py:1563",
   "what": "Treatment 7 of 8. Stacy's face at the head of Talk: an 84 px still square from the After Midnight plate with a LINE_STRONG edge, or her mark in characters on the ASCII desk. She is the face of staC, and staC is green wherever it is shown.",
   "how_drawn": "Custom paint on a small fixed-size widget (a drawn image or text).",
   "glow_idea": "A green halo, as the live readings have: QGraphicsDropShadowEffect, offset 0, blur 14, READY at alpha 0.5. On the ASCII desk the effect follows the characters, so '| staC |' glows like a phosphor.",
   "value": "medium",
   "how_to_do_it": "In PanelInk.refresh, for kind 'face' only: set the effect when the widget is visible and remove it otherwise, the pattern of desktop_header_qt.py:115-122. visible is already false on the Clean desk, and choose_art already calls refresh on every PanelInk (boss_qt.py:296-297), so no new hook.",
   "risk": "SlateFace's margins are 14, 10, 14, 12 (shell2.py:1559), so a blur above 14 is cut at the top of the pane. The widget repaints only on refresh, so the effect costs nothing while idle."
  },
  {
   "where": "workbench/boss_qt.py:85-138 (ArtPanel; paintEvent 112-138); placed at workbench/shell2.py:2363-2364",
   "what": "Treatment 8 of 8. The workshop plate at the head of Today on the Illustrated desk: a hard-edged rectangle with a hairline under it.",
   "how_drawn": "Custom paint: the image is scaled and drawn on every paintEvent.",
   "glow_idea": "No glow. Depth: the plate fades into the page, GROUND to clear over the first and last 12 percent of its width, and clear to GROUND at 0.9 over its last 22 percent of height, as the Field's rail does for the portrait (field_qt.py:644-653).",
   "value": "low",
   "how_to_do_it": "After draw_plate, three gradient fills; draw the result once into a QPixmap keyed by size and blit it, which also stops the plate being rescaled on every repaint. Illustrated only, which the code already checks; the panel is hidden on the Clean desk (boss_qt.py:99).",
   "risk": "The lamp at the left of the plate loses a little to the fade; check the focus value (0.28) against the new edges on a capture."
  },
  {
   "where": "workbench/desk_qt.py:406-423 (InkWord.marked and paint); workbench/log_qt.py:273-283",
   "what": "The lower band's mode words (Assistant, Terminal, Log) and the Log view's stream words: the chosen one has a 3 px PENCIL mark under its ink.",
   "how_drawn": "Custom paint through an event filter on QPushButton.",
   "glow_idea": "Leave it. The rule's light of treatment 1 is 11 px away, and tools/check_desk_ui.py compares each band word's box above its mark with the bare grain (228-260), so a light behind the chosen word fails it.",
   "value": "low",
   "risk": "Hover and focus on these words draw the same orange (ERASER_MARK '#dd854b', desk_qt.py:410), which is against 0.4.6's rule that the pointer's answer is green."
  },
  {
   "where": "workbench/boss_theme.py:70-73 (QLineEdit#WorkspacePath) and 78-80 (#MoreMenus, #BossPrograms, #SystemMenu :focus); the head's own sheet at workbench/shell2.py:559; PathBar at shell2.py:720-760",
   "what": "The address in the head, always AMBER_TEXT, and the head's three words, which take an amber ground and underline with keyboard focus.",
   "how_drawn": "QSS in the head band's own style sheet.",
   "glow_idea": "Leave it. The address is a QLineEdit refreshed every 400 ms (shell2.py:729): an effect would blur again on every caret blink, and a style sheet cannot glow text. The three words stand on the rule that treatment 1 lights.",
   "value": "low",
   "risk": "A glow rule for these must go in TopBar.band_style, not the app sheet: the nearer sheet wins."
  },
  {
   "where": "workbench/theme2.py:73-74, workbench/boss_theme.py:65, workbench/pane_qt.py:42-44, workbench/cabinet_qt.py:162, workbench/sheet_workbench_qt.py:40",
   "what": "The chosen row of a tree, a list or a table: an AMBER_SOFT (in the panes an ERASER) wash, with a 2 px amber left edge where the app sheet reaches.",
   "how_drawn": "QSS ::item:selected rules.",
   "glow_idea": "Leave it. A gradient on ::item restarts in every column of a tree or table, and rows are what the owner reads.",
   "value": "low",
   "risk": "The panes' trees use ERASER '#493225' for the chosen row, not the amber tokens."
  },
  {
   "where": "workbench/boss_theme.py:57-59, workbench/theme2.py:28-30, workbench/chain_menu.py:91-95, workbench/programs_qt.py:362-371 and 431-458, workbench/context_menu.py:1904-1918",
   "what": "Menus: the row in hand has an AMBER_SOFT wash (QMenu by style sheet, the desk's own menus by paintEvent); a checked choice has a short amber mark.",
   "how_drawn": "QSS on QMenu; custom paint on the rows of DeskMenu, a QFrame with Qt.Popup.",
   "glow_idea": "Leave it. The popups are opaque top-level windows (programs_qt.py:439; no WA_TranslucentBackground), so nothing can glow outside their frame without a compositor, which the ThinkPad's X session may not have.",
   "value": "low"
  },
  {
   "where": "workbench/theme2.py:129-132, workbench/boss_theme.py:86-87 (QPlainTextEdit#Capture), workbench/settings_qt.py:24-25 and 31-33, workbench/explore_qt.py:237-240, workbench/program_rooms_qt.py:35-36",
   "what": "Writable passages and other text edits: focus is an amber rule under or round the field.",
   "how_drawn": "QSS :focus rules on QLineEdit and QPlainTextEdit.",
   "glow_idea": "Leave it. A text edit never gets a graphics effect (caret, selection and scrolling each re-render it), and the amber rule already says where the keyboard is.",
   "value": "low"
  },
  {
   "where": "workbench/shell2.py:1515-1524 (Bubble); workbench/theme2.py:123-125 (QFrame#SlateMine, #SlateTheirs, #StacCard)",
   "what": "The Talk column's bubbles: the owner's words on AMBER_SOFT, Stacy's on CARD, a proposal on TEAL_SOFT; each a 1 px LINE frame with a 10 px radius.",
   "how_drawn": "QFrame styled by the app sheet, in a QScrollArea (shell2.py:1582), holding selectable labels.",
   "glow_idea": "Leave the bubbles flat. They scroll, are folded and rebuilt, and hold text to select; an effect on each would be re-rendered on every scroll step and cut by the viewport. What should glow in Talk is the Approve button (treatment 3).",
   "value": "low",
   "risk": "They are the last rounded frames on an otherwise square desk (boss_theme.py:54-55 squares the rest)."
  },
  {
   "where": "workbench/typebar_qt.py:350-351 (#WritingSubmit), workbench/sheet_workbench_qt.py:54-57 (#RunWorksheetChain), workbench/program_rooms_qt.py:44-47 (#ProgramPrimary), workbench/datasheet_qt.py:111-112 (#EvidenceCommit), workbench/investigations_qt.py:77 (#JournalContinue)",
   "what": "Amber filled action buttons in the writing strip and in rooms.",
   "how_drawn": "QSS in each room's own style sheet.",
   "glow_idea": "Leave them. They are actions the owner may take, not things that wait for the owner; a glow on each would turn the rule into decoration. If one is wanted later, it is the helper of treatment 3.",
   "value": "low"
  },
  {
   "where": "workbench/theme2.py:92 and 94, workbench/desktop_header_qt.py:170-171 and 451-453, workbench/shell2.py:379-383, 406 and 2524-2526, workbench/finder_qt.py:180",
   "what": "Small amber widgets: the checked box, the progress chunk, the niceness slider's filled part, the AI switch, the Library's Arrived badge, the delivery's stage bar, the chosen tile of the Finder's icon view.",
   "how_drawn": "QSS sub-controls, or custom paint inside item delegates.",
   "glow_idea": "Leave them. A delegate is clipped to its row, and a sub-control cannot take an effect.",
   "value": "low"
  },
  {
   "where": "workbench/qt_master_stop.py:31-34; workbench/concern_qt.py; workbench/workspace_tabs.py",
   "what": "Named in the brief. StopButton's sheet has an amber focus edge, but the button is hidden (shell2.py:516) and restyled without amber at shell2.py:2599-2602. concern_qt.py and workspace_tabs.py set no colour or style of their own.",
   "how_drawn": "QSS on a hidden QToolButton; nothing in the other two.",
   "glow_idea": "Leave them: nothing to light. The centre's tabs are treatment 4.",
   "value": "low"
  },
  {
   "where": "workbench/home_qt.py:87-101 (STYLE), 19-23 (shadow), 159 and 165",
   "what": "WorkshopHome, the older Control Center: hard-coded oranges (#ff9a32, #ffb05c) and black drop shadows on its card and stage tiles.",
   "how_drawn": "QSS with gradients and QGraphicsDropShadowEffect.",
   "glow_idea": "Leave it. It is not on the desk: with shell2 installed Home is finder_qt.FinderPage holding shell2.TodayPage (qt_app.py:3519-3523). Today is treatments 6 and 8.",
   "value": "low"
  },
  {
   "where": "workbench/field_page.py:25 and 109-112 (the faces); workbench/field_source.py:492-501; drawn by workbench/field_qt.py:880-931 (_sheet)",
   "what": "The Programs shelf (P) and the Network face (N): the same sheets as the work, compact on the shelf, with 'in use', 'up', 'connected' and 'listening' among the settled states that already carry the green mark's glow.",
   "how_drawn": "Custom paint; no painter of their own.",
   "glow_idea": "Leave them: whatever amber the Field gives its selected sheet reaches both faces through _sheet.",
   "value": "low",
   "risk": "On the shelf the rows are 14 px (scaled) apart (field_model.py:320) and a halo reaches 11, so a selected tile's amber and a neighbour's green hover overlap by a few faint pixels."
  },
  {
   "where": "workbench/graphite_brand.py:215-223 (startup_pixmap) and 238-250; shown from workbench/launch.py:104-112 and 135",
   "what": "The startup screen: the point in paper on a mid-grey graphite ground (#504d46), the palette of the paper desk, shown before the near-black desk.",
   "how_drawn": "A QPixmap painted once and given to QSplashScreen.",
   "glow_idea": "Leave it unless the owner asks. It is shown before the session is read, so it cannot know the Clean desk, and tools/check_graphite_ui.py:66-67 requires over 60 percent of its pixels within 6 levels of #504d46. If it is done: the dark GROUND, the point in TEXT, and a radial AMBER_EDGE light at the tip, alpha 0.28 to 0 over a third of the width.",
   "value": "low"
  },
  {
   "where": "workbench/field_qt.py:638-660 (_art) and 672-705 (_stac)",
   "what": "Stacy's portrait in the rail and the staC box under it.",
   "how_drawn": "Custom paint; the portrait is drawn once per size into a pixmap with a veil and two fades.",
   "glow_idea": "Leave them. The portrait already sits in the dark; a light over an illustration muddies it, and the plate carries its own lamp and green screen. The staC lines are already green.",
   "value": "low"
  }
 ],
 "cautions": [
  "Nothing was run or rendered. Alphas and reaches are chosen from the code and from the Field's existing halo numbers (field_qt.py:846-853); they need one look on a capture before release.",
  "The colour rule exists to keep glow from becoming decoration. Treatments 2, 3, 4, 5 and 6 light a state (keyboard, waits, chosen). Treatment 1 is ornament on the frame and treatment 8 is depth; both must go on the Clean desk. Treatment 7 is green, not amber, on purpose.",
  "There are two ambers. The band and pane marks use desk_qt.PENCIL '#f2a369' (desk_qt.py:243); everything else uses boss_theme.AMBER_EDGE '#ff9a36' (boss_theme.py:12). Light each mark in its own colour, or unify the token first. tests_integrated/test_desk.py:124 asserts the two are equal, which they are not today.",
  "Hover on the custom-painted marks is still orange: ERASER_MARK '#dd854b' for hover and focus alike at desk_qt.py:410, pane_qt.py:158, log_qt.py:281 and system_menu_qt.py:117-118. 0.4.6 made the pointer's answer green only where style sheets draw it. Amber light beside an orange hover mark will read as a selection; settle it with treatment 4 (hover green, focus amber).",
  "QGraphicsDropShadowEffect: only on small leaf widgets that repaint rarely. Never on a line or text edit, a scroll area, a band or a pane. A widget takes one effect; the glow is clipped by the parent widget and by a scroll area's viewport; a disabled widget still casts its glow unless the effect is removed.",
  "Style sheets: the nearest sheet wins whatever the selector, and TopBar (shell2.py:559), TypeBar (typebar_qt.py:345-354) and PaneTabs (pane_qt.py:187-189) set their own, so an app-level glow rule does not reach them. theme2.Relight (theme2.py:214-231, through boss_theme.py:27-50) rewrites any hex colour that is not a token in a widget's own sheet; use tokens or rgba() there. The gradient hexes proposed here are for the window's sheet, which is not rewritten.",
  "CHROME_OVERRIDES and several room sheets are built with % formatting (boss_theme.py:93): a literal percent sign in a new rule must be doubled.",
  "tools/check_desk_ui.py holds pixel references for both bands and the tab marks (174-181, 215-260, 275-286, 685, 886) and builds its window on the default Illustrated desk. Treatments 1 and 4 change pixels it measures. I could not tell from reading whether its head-band rows pass today (they refer to the hidden word and symbol), so it must be run before and after.",
  "tools/check_paper_ui.py:146 looks for 'QPlainTextEdit#SlateInput' after the words 'Writable passages' in theme2.QSS2; do not move that block when adding rules.",
  "Stillness holds for all eight: each repaints on focus, selection, a change of state or the owner's hand. None adds a timer. Treatment 6 rides Today's existing 4 s read of the records and must only re-polish on a change."
 ]
}