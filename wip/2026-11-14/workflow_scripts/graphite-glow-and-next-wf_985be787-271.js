export const meta = {
  name: 'graphite-glow-and-next',
  description: 'Map where amber and mood glow belong, map the next vision step, and review the 0.4.6 pointer and glow code',
  phases: [
    { title: 'Map', detail: 'four readers: amber in paint, amber and mood in style sheets and other faces, the workbook chain, Field zoom and the centre' },
    { title: 'Review', detail: 'three reviewers over the 0.4.5..HEAD diff, by dimension' },
    { title: 'Verify', detail: 'one skeptic per serious finding' },
  ],
}

const ROOT = '/home/user/Struthio'
const SPEC = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wish2/spec2.txt'
const COMMON = `You are reading the Graphite source tree at ${ROOT} (Python 3.13, PySide6; the Qt app is in workbench/). READ ONLY: do not edit, create or delete any file in the tree, do not run git commands that change anything, do not run any test or the application, and make no web requests. Use Read, Grep and Glob. Give file paths relative to the tree with line numbers.

Background you need: the desk is dark (near-black ground, cream text). Colour rule, stated in workbench/boss_theme.py: AMBER is what is selected, what has the keyboard, and what waits for the owner; GREEN (boss_theme.READY and the TEAL_* tokens) is what is live, staC, the pointer, and whatever the pointer is over. The desk has three art modes (Illustrated, ASCII, Clean; session state key 'desk_art'); the Clean desk has no ornament and no glow. Surfaces are still: nothing moves unless the owner's hand moves it (no animation, no timers that repaint for effect). Release 0.4.6 (docs/RELEASE_NOTES_0.4.6.md) added green glow: workbench/pointer.py (the pointer), workbench/field_qt.py (_halo, _light, glowing marks and wires, gated by self.texture), workbench/desktop_header_qt.py (DesktopMonitors.relight), and green hover rules in boss_theme.py, theme2.py, shell2.py, settings_qt.py. The owner now says: "let's add some glow effects to the orange and anywhere else it would enhance the mood. Really loving the glow effects."`

const MAP_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    places: { type: 'array', items: { type: 'object', properties: {
      where: { type: 'string', description: 'file:line (and function or QSS selector)' },
      what: { type: 'string', description: 'what is drawn there and what it means to the owner' },
      how_drawn: { type: 'string', description: 'QPainter custom paint, QSS rule, QLabel style, QGraphicsEffect, pixmap ...' },
      glow_idea: { type: 'string', description: 'a concrete, still (non-animated) glow or mood treatment that fits, or "leave it" with the reason' },
      how_to_do_it: { type: 'string', description: 'the smallest correct way to implement it in this code, with the hook to gate it off on the Clean desk' },
      risk: { type: 'string' },
      value: { type: 'string', enum: ['high', 'medium', 'low'] },
    }, required: ['where', 'what', 'how_drawn', 'glow_idea', 'value'] } },
    cautions: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'places'],
}

const NEXT_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    how_it_works_now: { type: 'array', items: { type: 'object', properties: { fact: { type: 'string' }, where: { type: 'string' } }, required: ['fact', 'where'] } },
    what_blocks: { type: 'array', items: { type: 'object', properties: { block: { type: 'string' }, where: { type: 'string' }, why_it_is_there: { type: 'string' } }, required: ['block', 'where'] } },
    smallest_sound_change: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, files: { type: 'string' }, detail: { type: 'string' }, risk: { type: 'string' } }, required: ['step', 'files', 'detail'] } },
    what_must_not_break: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'how_it_works_now', 'smallest_sound_change'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' },
      file: { type: 'string' },
      line: { type: 'integer' },
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      what_goes_wrong: { type: 'string', description: 'the concrete situation and what the owner would see' },
      evidence: { type: 'string', description: 'the code that shows it, quoted briefly, with line numbers' },
      fix: { type: 'string' },
    }, required: ['title', 'file', 'severity', 'what_goes_wrong', 'evidence'] } },
    looked_at: { type: 'string' },
  },
  required: ['findings', 'looked_at'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    real: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'string' },
    better_fix: { type: 'string' },
  },
  required: ['real', 'confidence', 'reasoning'],
}

const READERS = [
  { key: 'amber-paint', schema: MAP_SCHEMA, prompt: `${COMMON}

YOUR JOB: map every place AMBER is drawn by custom painting (QPainter), and say where a still amber glow would help the mood and the meaning. Start with workbench/field_qt.py (the Field: the selected sheet's corner brackets and edge, sheets that wait, the head's state word, the Approve button drawn by _keys_line, the DO line at the foot, the what-if marks, the reading sheet, the key card, the 'more below' strip), then workbench/field_page.py, workbench/boss_qt.py (ArtPanel, PanelInk, the ASCII mark), workbench/programs_qt.py and workbench/chain_menu.py (the cascading menus and the Programs shelf), workbench/typebar_qt.py, workbench/desk_qt.py, workbench/pane_qt.py, workbench/home_qt.py and any other workbench/*_qt.py that paints with t.AMBER*, AMBER_EDGE, AMBER_SOFT, AMBER_TEXT. Read how the existing green glow is done in field_qt.py (_halo, _light, _mark, the wire underlay in _wires) so your proposals reuse the same technique and the same gate (self.texture / the art mode). For each place give the exact lines, what the amber means there (selected, has the keyboard, waits), and a concrete glow proposal that keeps the rule (an amber glow must not make something look merely hovered; a thing that WAITS for the owner is the strongest candidate, the selected sheet next). Say where glow would be clutter and should be left out. Note any place where two glows (green hover + amber selected) would land on the same sheet and how they should combine.` },
  { key: 'amber-style-and-mood', schema: MAP_SCHEMA, prompt: `${COMMON}

YOUR JOB: map (a) every place AMBER is applied through style sheets and widgets rather than custom paint, and (b) the surfaces outside the Field where a still glow or depth treatment would enhance the mood. For (a) read workbench/boss_theme.py (the stylesheet and tokens), workbench/theme2.py, workbench/shell2.py (the long style list near line 290-330 and the frame: the head band, the amber rules above and below the centre, the tab underline, the status band), workbench/typebar_qt.py (the writing strip and its submit button), workbench/concern_qt.py, workbench/workspace_tabs.py, workbench/desktop_header_qt.py, workbench/qt_master_stop.py. Qt style sheets cannot draw a blur; a glow on a widget needs either a QGraphicsDropShadowEffect (offset 0, as DesktopMonitors.relight does for the live readings), a custom paintEvent, or a gradient border/background in QSS. For each candidate say which of these is the smallest correct way, what the hazards are (graphics effects on large or frequently repainted widgets, on widgets that contain text edits, on scroll areas; effects clipped by the parent; QSS gradients on borders), and how to turn it off on the Clean desk (boss_qt.choose_art is where the art mode changes; see how it reaches the Field, the pointer and the monitors). For (b) look at the Home page (workbench/home_qt.py), the Programs shelf / 'P' face and Network face as the Field draws them (workbench/field_qt.py faces, workbench/field_page.py), Stacy's rail and portrait panel (workbench/boss_qt.py ArtPanel), the Talk column bubbles (shell2.py Bubble / SlateMine / SlateTheirs), the reading sheet (field_qt.py _reading), the startup screen (workbench/graphite_brand.py), the frame's amber hairlines. Propose at most eight treatments ranked by value, each concrete enough to implement (what is drawn, colour token, alpha, extent), and name the ones to leave alone.` },
  { key: 'workbook-chain', schema: NEXT_SCHEMA, prompt: `${COMMON}

YOUR JOB (not about glow): the owner's vision (${ROOT}/RECORD_OF_DIRECTIONS.md, section 'One thin journey through all four'; the whole-build specification is at ${SPEC}, read it) says an ordinary workbook should be a citizen of the chain. Today a calculation can only be made from a sheet that was reviewed from a PDF; a workbook brought in from a file (xlsx, csv) or typed in the Office cannot feed a calculation. Find out exactly why, and what the smallest sound change is that lets an ordinary Office sheet feed a calculation, be traced, be doubted, be rechecked when its cell changes, and take part in what-if (field.ripple) and field.set, the same as a reviewed sheet does. Read: workbench/datasheet_work.py, workbench/documents.py (create with derivation), workbench/field_source.py (how the Field builds sheets and wires, what makes a sheet a 'sheet' tile and a calc a 'calculation'), workbench/field_do.py (the steps offered for a sheet, e.g. making a calculation), workbench/field_doubt.py (doubts for sheets and calculations; what it assumes about provenance, e.g. UNCHANGED_ORIGINAL), workbench/field_ripple.py, workbench/field_service.py (field.set), the Office modules (grep for 'office.save', 'office.get', 'office.import', 'owner:' ids, and how a reviewed-from-PDF sheet differs from an owner sheet in its record: provenance, units, parameter names, the cells a recipe reads), workbench/math_units.py and workbench/quantities.py for how a cell's unit is known, and the recipe machinery that computes a calculation (grep 'recipe', 'derivation', 'recompute', 'calc.'). Report facts with file:line, the precise blocks (each with why it exists: some may be there on purpose, e.g. a number with no unit must not silently become a quantity), and a step-by-step smallest change with the files to touch. Say what a calculation from an ordinary sheet should honestly show as weaker than one from a reviewed source (a doubt: 'this number was typed, nothing stands behind it'), so the evidence side stays truthful. List what must not break.` },
  { key: 'field-zoom-and-centre', schema: NEXT_SCHEMA, prompt: `${COMMON}

YOUR JOB (not about glow): two known gaps from the owner's whole-build specification (read it: ${SPEC}; and docs/RELEASE_NOTES_0.4.5.md 'Not shown, because it is not built'). (1) Zoom and fit for the Field. Read workbench/field_qt.py closely: scale(), _layout(), sheet_height(), sheet_rect(), the scroll_x/scroll_y panning, wheelEvent, _reveal, how fonts are sized (mono(), sans()), the rail, and how the interface scale (reading size) enters. Work out the smallest sound way to add zoom (Ctrl+wheel, Ctrl+plus/minus, a key for fit-all and a key for 100%) that keeps text legible, keeps hit-testing (_hit, _hot) and partial repaints (_lit) correct, and keeps the pointer under the same sheet while zooming. Say exactly which functions must change and what could go wrong (fonts at small sizes, the surface size, tooltips, the 'more below' strip, keyboard walking and _reveal). The keys already taken are in the KEYS tuple and keyPressEvent; propose free ones. (2) The centre's common frame and small toolbar ('Universal Program Window', about ten controls). Read how an item opens in the centre today: workbench/field_page.py (opened -> host), workbench/workspace_tabs.py, workbench/concern_qt.py (install_context: the strip under the centre with the '‹ Field' button), the Office page (OfficePanel) and the document page, and shell2.py where the centre is assembled. Say what a common frame would wrap, which ten controls the specification names and which already exist as actions somewhere (give the action names, e.g. host.a_field), and the smallest first slice that is honest (controls that work for every kind of item, disabled with a reason where they do not apply).` },
]

const DIFF = `The change under review is everything between commit 1a46d50 (Graphite 0.4.5) and HEAD on the current branch. See it with: git -C ${ROOT} diff 1a46d50 HEAD -- workbench tools/check_desk_ui.py (that git command is read-only and allowed). Read the changed functions whole in the current files, not only the diff hunks. This release has NOT been run on a real display: it was only run with QT_QPA_PLATFORM=offscreen, where there is no pointer. It will run on X11 (xcb) on Debian 13 with PySide6. Report only defects you can show from the code; say what the owner would see. Do not report style preferences.`

const REVIEWERS = [
  { key: 'pointer', prompt: `${COMMON}

YOU ARE REVIEWING, not mapping. ${DIFF}

Your dimension: workbench/pointer.py and its callers (workbench/qt_app.py make_app, workbench/boss_qt.py choose_art, workbench/graphite_brand.py use_pointer, workbench/desk_qt.py MirroredDrag.hover which saves and restores the window cursor). Think hard about: an application-wide event filter written in Python on QEvent.Polish / Show / CursorChange (cost per event; re-entrancy when give() calls setCursor, which itself sends CursorChange; widgets being constructed or destroyed; PySide object lifetime; QEvent.Show on every widget); widgets that change their cursor dynamically (QTextBrowser/QTextEdit over links, QSplitter handles, QAbstractItemView, QMenu, QComboBox popups, tool tips, QLineEdit clear buttons, QHeaderView section resize, QAbstractSpinBox); QApplication.setOverrideCursor users in the tree (grep setOverrideCursor / restoreOverrideCursor / unsetCursor) and whether the green pointer interferes; windows other than the main one (dialogs, QFileDialog, popups, the startup screen); high-DPI (devicePixelRatio taken once from the primary screen at build); the restyle() path when the desk art changes and the Show-time restyle that reads watched.session; the property name MARK and the brand's 'graphitePointer'; whether a widget that sets Qt.ArrowCursor explicitly inside a widget with an I-beam now behaves differently; hotspot correctness with PAD; cursor pixmap size limits on X11. Also check drawn(): painter state, the tip pixel, the WindingFill path for two facets.` },
  { key: 'field', prompt: `${COMMON}

YOU ARE REVIEWING, not mapping. ${DIFF}

Your dimension: workbench/field_qt.py as changed (the mouse path of 0.4.5 is context, the 0.4.6 additions are the subject): _point and the pointer shape logic in mouseMoveEvent/mouseReleaseEvent/leaveEvent; the partial repaint in mouseMoveEvent (self.update(QRegion(self._lit(was)).united(...))) against everything paintEvent draws that depends on the pointer position (_hover halo, keys under the pointer in _keys_line, the Approve button halo, _light) - look for stale pixels: something that changes with the pointer but lies outside the two lit squares and is not covered by a full update(); the state rebuilt on every paint (self._hot, self._labels, self._face_boxes ...) when Qt clips the paint to a region; _light and _lit at the edges, with self._mouse at (-1,-1), during a drag (pan), while a reading sheet is open, when self.texture is off; _halo and the glowing _mark and wire underlay (painter save/restore balance, pen/brush leaks into later drawing, cost per sheet with many sheets and wires); hover state after the surface scrolls under a still pointer (wheelEvent, keyboard walking, _reveal) - is _hover refreshed; tooltips. Also workbench/desktop_header_qt.py DesktopMonitors.relight (QGraphicsDropShadowEffect created and removed every 2 s? ownership; the effect on a QLabel whose style sheet is re-set in restyle(); behaviour when host has no session) and its call from boss_qt.choose_art.` },
  { key: 'style', prompt: `${COMMON}

YOU ARE REVIEWING, not mapping. ${DIFF}

Your dimension: the style-sheet changes and their reach: workbench/boss_theme.py, workbench/theme2.py, workbench/shell2.py (LibraryFoot, TimelineHead), workbench/settings_qt.py (ACTION_STYLE and STYLE hover colour #cbf08b). The intent: whatever the pointer is over answers in green; what is selected, focused or checked stays amber. Find where the two now collide or read wrongly: a control that is BOTH checked/selected/focused AND hovered (which rule wins by specificity and order in each sheet? e.g. QPushButton:checked vs :hover, [arcButton="filter"]:checked, the checkable tab-like buttons made with ACTION_STYLE + CHECKED_RULE in cabinet_qt.py, QTabBar::tab:selected:hover, QTreeView::item:selected:hover and ::item:hover backgrounds over selection); disabled controls that now turn green under the pointer; the Relight filter in theme2.py that rewrites widget style sheets from the older palette (does it rewrite or mangle the new #cbf08b or the TEAL tokens? read its mapping); places that still answer in amber on hover and so now look inconsistent (grep ':hover' across workbench/*.py; report the ones on surfaces the owner actually sees on the dark desk: sheet_workbench_qt.py, typebar_qt.py WritingSubmit, programs rooms, home_qt.py JourneyStage, qt_master_stop.py); the light-page documents (a page with a light paper background): does green hover text (#cbf08b) become unreadable on a light ground anywhere these rules apply? Also check tools/check_desk_ui.py lines changed in this diff for mistakes (they cannot be run).` },
]

phase('Map')
const mapsP = parallel(READERS.map(r => () => agent(r.prompt, { label: 'map:' + r.key, phase: 'Map', schema: r.schema })))

phase('Review')
const reviewed = await pipeline(
  REVIEWERS,
  r => agent(r.prompt, { label: 'review:' + r.key, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (review, r) => {
    const all = (review && review.findings) || []
    const serious = all.filter(f => f.severity !== 'low')
    if (all.length !== serious.length) log(`review:${r.key}: ${all.length - serious.length} low findings kept without a second look`)
    const capped = serious.slice(0, 5)
    if (serious.length > capped.length) log(`review:${r.key}: ${serious.length - capped.length} more serious findings were not sent to a skeptic`)
    return parallel(capped.map(f => () => agent(`${COMMON}

A reviewer of the change between commit 1a46d50 and HEAD claims this defect. Try to REFUTE it by reading the current code (read the whole function and its callers; git -C ${ROOT} diff 1a46d50 HEAD -- <file> is allowed, read-only). Decide whether it is real, i.e. whether the situation can actually arise in this program and the owner would see what is claimed. If you are not sure after reading, say real=false with low confidence.

Claim: ${f.title}
File: ${f.file}${f.line ? ':' + f.line : ''}
What goes wrong: ${f.what_goes_wrong}
Evidence given: ${f.evidence}
Proposed fix: ${f.fix || '(none)'}

If it is real and the proposed fix is wrong or larger than needed, give a better one.`, { label: 'verify:' + r.key, phase: 'Verify', schema: VERDICT_SCHEMA }).then(v => ({ ...f, verdict: v }))))
      .then(checked => ({ dimension: r.key, looked_at: review ? review.looked_at : '', checked: checked.filter(Boolean), low: all.filter(f => f.severity === 'low') }))
  }
)

const maps = await mapsP
const out = {}
READERS.forEach((r, i) => { out[r.key] = maps[i] })
return { maps: out, review: reviewed.filter(Boolean) }
