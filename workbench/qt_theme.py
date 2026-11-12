"""ARC-1 Workbench theme (R10.5, owner decision: "All UI should be ARC-1 coloured").

Colours come from the ARC-1 logo: near-black surfaces, brushed-steel chrome and
text, and ARC-1 orange for focus, the active tab and selection edges. The R10
Classic layout (menus, one compact toolbar, docks) is unchanged; only colour
moved from ivory to the logo palette.

Windows keeps its own title bar and minimize/maximize/close buttons; this
style sheet only touches the client area. Sizes are in points or padding, not
fixed pixel heights, so Windows text scaling still works.
"""
ORANGE = '#ff9a32'        # accent: focus, active tab, current selection edge (the "-" in ARC-1)
ORANGE_DEEP = '#c8400c'   # pressed / dashed requirement lines
ORANGE_SOFT = '#332417'   # selection fill
BLACK = '#0e1116'         # window background (the logo's backdrop)
PANEL = '#171b21'         # documents and lists
RAISED = '#222832'        # toolbars, headers, docks
STEEL_DARK = '#2a2d31'    # buttons, hover
LINE = '#485563'          # hairlines
STEEL = '#b5bec8'         # secondary text, icons
TEXT = '#f3f4f6'          # primary text (the logo's polished steel)
MUTED = '#b5bec8'

QSS = r"""
QMainWindow, QDialog { background: #0e1116; }
QWidget { color: #f3f4f6;  }
QToolTip { background: #222832; color: #f3f4f6; border: 1px solid #ff9a32; padding: 4px 6px; }

QMenuBar { background: #0e1116; border-bottom: 1px solid #485563; padding: 1px 4px; }
QMenuBar::item { padding: 4px 9px; border-radius: 4px; background: transparent; color: #d7dadd; }
QMenuBar::item:selected { background: #2a2d31; }
QMenuBar::item:pressed { background: #332417; color: #ffffff; }
QMenu { background: #171b21; border: 1px solid #485563; padding: 4px 0; }
QMenu::item { padding: 5px 28px 5px 24px; }
QMenu::item:selected { background: #332417; color: #ffffff; border-left: 2px solid #ff9a32; }
QMenu::item:disabled { color: #5b6066; }
QMenu::separator { height: 1px; background: #2a2d31; margin: 4px 8px; }

QToolBar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2d31, stop:0.5 #222832, stop:1 #171b21);
           border: 0; border-bottom: 1px solid #ff9a32; spacing: 3px; padding: 3px 6px; }
QToolBar::separator { width: 1px; background: #3a3e44; margin: 4px 5px; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 3px 9px;
              color: #f3f4f6; }
QToolButton:hover { background: #2a2d31; border-color: #4a4f56; }
QToolButton:pressed, QToolButton:checked { background: #332417; border-color: #ff9a32; }
QToolButton[popupMode="1"] { padding-right: 18px; }
QToolButton::menu-button { width: 16px; border: 0; border-left: 1px solid #3a3e44; background: transparent; }
QToolButton::menu-button:hover { background: #332417; }
QProgressBar#taskProgress { background: #101113; color: #f3f4f6; border: 1px solid #4a4f56;
                            border-radius: 5px; text-align: center; min-height: 16px; }
QProgressBar#taskProgress::chunk { background: #ff9a32; border-radius: 4px; }

QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34383d, stop:1 #222528);
              border: 1px solid #44494f; border-radius: 4px; padding: 4px 14px; color: #f3f4f6; }
QPushButton:hover { border-color: #ff9a32; }
QPushButton:pressed { background: #332417; }
QPushButton:default { border: 1px solid #ff9a32; }
QPushButton:disabled { color: #5b6066; }
QPushButton#linkButton { background: transparent; border: 0; color: #ff7a3c; padding: 2px 0; text-align: left; }
QPushButton#linkButton:hover { text-decoration: underline; }

QComboBox { background: #171b21; border: 1px solid #44494f; border-radius: 4px; padding: 2px 8px; min-width: 9em;
            color: #f3f4f6; }
QComboBox:hover, QComboBox:focus { border-color: #ff9a32; }
QComboBox QAbstractItemView { background: #171b21; color: #f3f4f6; selection-background-color: #332417;
                              selection-color: #ffffff; border: 1px solid #485563; }
QLineEdit, QSpinBox { background: #171b21; color: #f3f4f6; border: 1px solid #44494f; border-radius: 4px;
                      padding: 3px 6px; selection-background-color: #ff9a32; selection-color: #ffffff; }
QLineEdit:focus, QSpinBox:focus { border-color: #ff9a32; }
QCheckBox, QRadioButton { color: #f3f4f6; }

QDockWidget { titlebar-close-icon: none; font-weight: 600; color: #d7dadd; }
QDockWidget::title { background: #222832; padding: 4px 8px; border-bottom: 1px solid #485563; text-align: left; }

QTreeView, QTreeWidget, QListWidget, QTableView {
    background: #171b21; alternate-background-color: #17181b; border: 0; outline: 0; color: #f3f4f6;
    selection-background-color: #332417; selection-color: #ffffff; }
QTreeView::item, QTreeWidget::item, QListWidget::item { padding: 2px 0; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { border-left: 2px solid #ff9a32; }
QTreeView::item:hover, QTreeWidget::item:hover { background: #1f2124; }
QTreeView::item:disabled, QTreeWidget::item:disabled { color: #5b6066; }
QHeaderView::section { background: #222832; color: #b5bec8; border: 0; border-right: 1px solid #2a2d31;
                       border-bottom: 1px solid #485563; padding: 4px 6px; }

QTabWidget::pane { border: 0; border-top: 1px solid #485563; background: #171b21; }
QTabBar::tab { background: #222832; color: #b5bec8; padding: 5px 12px; border: 1px solid #485563; border-bottom: 0;
               margin-right: -1px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #171b21; color: #ffffff; border-top: 2px solid #ff9a32; }
QTabBar::tab:hover:!selected { background: #26292d; color: #f3f4f6; }
QTabBar::close-button { subcontrol-position: right; }

QPlainTextEdit#sourceEditor, QPlainTextEdit#outputText, QPlainTextEdit#inspector {
    font-family: 'Consolas', 'Cascadia Mono', 'DejaVu Sans Mono', 'Menlo', 'Courier New', monospace; }

QPlainTextEdit#outputText, QPlainTextEdit#inspector { font-size: 9pt; }
QPlainTextEdit#sourceEditor { background: #101113; color: #f3f4f6; border: 0;
                              selection-background-color: #5a2a12; selection-color: #ffffff; }
QPlainTextEdit#outputText { background: #101113; color: #d7dadd; border: 0; selection-background-color: #5a2a12; }
QPlainTextEdit#inspector { background: #101113; color: #d7dadd; border: 0; }
QTextEdit, QPlainTextEdit { background: #101113; color: #f3f4f6; }
QLabel { color: #f3f4f6; }
QLabel#docInfo { background: #171b21; color: #b5bec8; border-top: 1px solid #2a2d31; padding: 2px 10px; }
QLabel#deviceBadge { background: #171b21; color: #ff7a3c; border: 1px solid #ff9a32; border-radius: 9px;
                     padding: 1px 10px; font-weight: 600; font-size: 8.5pt; }
QLabel#heading { font-size: 17pt; font-weight: 600; color: #ffffff; }
QLabel#subheading { color: #b5bec8; }
QLabel#sectionTitle { font-weight: 600; color: #b5bec8; padding-top: 10px; }
QLabel#simBanner { background: #2a1408; color: #ffb38c; border: 1px solid #ff9a32; border-radius: 4px; padding: 4px 8px; }
QLabel#lcd { background: #120804; color: #ff7a3c; border: 2px solid #4a4f56; border-radius: 4px; padding: 10px;
             font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 12pt; }
QLabel#framePreview { background: #000000; border: 1px solid #485563; }
QScrollArea { background: #171b21; border: 0; }

QStatusBar { background: #0e1116; color: #b5bec8; border-top: 1px solid #485563; }
QStatusBar QLabel { padding: 0 8px; color: #b5bec8; }
QSplitter::handle { background: #222832; }
QSlider::groove:horizontal { height: 4px; background: #2a2d31; border-radius: 2px; }
QSlider::handle:horizontal { background: #ff9a32; width: 12px; margin: -5px 0; border-radius: 6px; }
QScrollBar:vertical { background: #101113; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #3a3e44; border-radius: 5px; min-height: 24px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #ff9a32; }
QScrollBar:horizontal { background: #101113; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #3a3e44; border-radius: 5px; min-width: 24px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #ff9a32; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


# R10.12: avoid platform-default white backgrounds in the evidence strip.
QSS += r"""
QProgressBar#readinessProgress { background: #20252a; color: #f3f4f6;
    border: 1px solid #48515b; border-radius: 4px; text-align: center; min-height: 20px; }
QProgressBar#readinessProgress::chunk { background: #a95a31; border-radius: 3px; }
QToolButton#favoriteCommand { padding: 2px; }
"""

QSS += r"""
QProgressBar { background: #20252a; color: #eef0f2; border: 1px solid #48515b;
    border-radius: 3px; text-align: center; }
QProgressBar::chunk { background: #b47852; border-radius: 2px; }
"""

# Explicit dark defaults cover empty viewports, tab gutters and dock separators.
QSS += r"""
QWidget { background-color: #171b21; }
QWidget#WorkspaceToolbar { background-color: #222832; border-bottom: 1px solid #7c4228; }
QWidget#favoriteGroup { background: transparent; }
QMainWindow::separator { background: #292d32; width: 4px; height: 4px; }
QTabWidget > QWidget, QStackedWidget, QAbstractScrollArea::corner { background: #171b21; }
QTabBar::scroller, QTabBar QToolButton { background: #222832; color: #f3f4f6; }
QWidget#ConsolePages QTabBar::tab { padding: 5px 7px; }
QLabel { background: transparent; }
"""

# Owner review: orange outlines make individual tabs and the active page easier to find.
QSS += r"""
QTabBar::tab { border: 1px solid #ad5b2e; border-bottom: 1px solid #ad5b2e;
    margin: 1px 2px 2px 0; border-radius: 3px; background: #222832; color: #d2d7dc; }
QTabBar::tab:selected { border: 1px solid #ff762f; border-top: 3px solid #ff762f;
    background: #352319; color: #ffffff; }
QTabBar::tab:hover:!selected { border-color: #ff762f; background: #2b241f; }
"""

# D1 approved noir materials. Fonts remain owned by reading_preferences.
QSS += r"""
QWidget#WorkshopHome, QWidget#HomeArtwork { background: #0e1116; }
QLabel#homeTitle { font-size: 24pt; font-weight: 600; color: #f3f4f6; }
QFrame#HomeActions { background: #171b21; border: 1px solid #485563; border-radius: 7px; }
QPushButton[arcRole="primary"] { background: #ff9a32; color: #0e1116; border: 1px solid #ffb05c; font-weight: 600; }
QPushButton[arcRole="primary"]:pressed { background: #e18427; }
QPushButton#homeClip { background: transparent; border: 0; padding: 0; }
QLabel[arcRole="metadata"] { color: #b5bec8; }
QPushButton, QToolButton, QComboBox, QLineEdit { min-height: 24px; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus { border: 2px solid #ffb05c; }
QTreeView::item, QTreeWidget::item { padding: 5px 2px; }
QWidget#ContextActions { background: #171b21; border-bottom: 1px solid #485563; }
QWidget#ContextActions QToolButton { padding: 2px 6px; }
QPlainTextEdit#sourceEditor { background: #faf7f0; color: #182330; border: 0; selection-background-color: #ffdfc0; selection-color: #182330; }
QPlainTextEdit#sourceEditor:focus { border: 1px solid #9b3f00; }
QPlainTextEdit#candidateDiff { background: #faf7f0; color: #182330; selection-background-color: #ffdfc0; selection-color: #182330; }
QTabBar::tab { padding: 6px 9px; }
"""

# ARC UX 1: one calm shell with native, accessible controls.
QSS += r"""
QWidget#ArcChrome, QWidget#ArcMast { background:#13181e; }
QWidget#ArcMast { border-bottom:1px solid #343f4b; }
QLabel[arcRole="wordmark"] { font-weight:700; letter-spacing:2px; }
QWidget#WorkspaceToolbar { background:#171d24; border-bottom:1px solid #34414f; }
QWidget#WorkspaceToolbar QToolButton { padding:4px; border:1px solid transparent; border-radius:4px; }
QWidget#WorkspaceToolbar QToolButton:hover { background:#29333f; border-color:#56616e; }
QWidget#WorkspaceToolbar QToolButton:focus { border-color:#ffa34b; }
QWidget#WorkspaceToolbar QToolButton:checked { background:#3c2b1c; border-color:#e79642; }
QToolButton#favoriteGroupMenu { padding:5px 15px 5px 7px; color:#e3e8ee; }
QToolButton#favoriteGroupMenu::menu-indicator { subcontrol-position:right center; right:3px; }
QFrame#CommandDivider { background:#3b4653; border:0; }
QWidget#ActivityRail { background:#11171e; border-bottom:1px solid #354252; }
QToolButton#ActivityButton { padding:12px 9px; border:1px solid #354252; border-radius:5px; color:#c2cbd5; }
QToolButton#ActivityButton:checked { background:#302419; border:1px solid #ff9a32; border-bottom:3px solid #ff9a32; color:#ffb05c; }
QToolButton#ActivityButton:hover { background:#25303a; }
QToolButton#GlobalSearch { background:#0e141b; padding:5px 10px; color:#b5bec8; border:1px solid #354252; }
QWidget#ArcInspector { background:#141a22; }
QTextBrowser#ArcContext { background:#141a22; border:0; padding:0; }
QLabel[arcRole="section"] { font-size:17pt; font-weight:600; padding-bottom:8px; }
QDockWidget::title { background:#171e26; padding:9px 12px; color:#aebdcb; border-bottom:1px solid #354252; }
QMainWindow::separator { background:#354252; width:2px; height:2px; }
QTreeWidget#hardwareTree { background:#11171e; }
QTreeWidget#hardwareTree::item { padding:9px 3px; border:0; }
QTreeWidget#hardwareTree::item:selected { background:#49301b; border-left:3px solid #ff9a32; color:#ffbe7c; }
QTabBar::tab { border:1px solid #3c4957; color:#c4ced7; background:#1c242e; padding:7px 12px; }
QTabBar::tab:selected { background:#252c34; border:1px solid #ff9a32; border-top:2px solid #ff9a32; }
QFrame#HomeActions { background:#181f28; border:1px solid #354252; padding:4px; }
QPushButton { padding:7px 12px; }
QHeaderView::section { background:#202a35; color:#becbd5; }
QTextBrowser { border:0; }
QStatusBar { background:#171e27; border-top:1px solid #354252; }
"""

# ARC UX 3 · Aqua lift: light-grey gloss and bevels over graphite; orange glass for menus
# and primary actions. Raised controls catch light on their upper half and top edge;
# pressed controls invert; text fields sit inset. Colours stay in the ARC palette.
QSS += r"""
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #58616c, stop:0.48 #3b424b, stop:0.52 #2d333a, stop:1 #252a30);
    border: 1px solid #1b1f24; border-top-color: #7d8792; border-bottom-color: #121518; border-radius: 6px; color: #f3f4f6; }
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66707c, stop:0.48 #464e58, stop:0.52 #343b43, stop:1 #2b3138);
    border-color: #ff9a32; border-top-color: #ffc078; }
QPushButton:pressed, QPushButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d2126, stop:0.6 #2b3138, stop:1 #39404a);
    border-top-color: #101215; border-bottom-color: #5f6873; }
QPushButton:disabled { background: #22272d; border: 1px solid #2c3238; color: #69717b; }
QPushButton[arcRole="primary"], QPushButton#homeContinue {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd29a, stop:0.48 #ffa13f, stop:0.52 #f2851c, stop:1 #e8771a);
    color: #1d0f04; border: 1px solid #b5560d; border-top-color: #ffe2bb; font-weight: 700; }
QPushButton[arcRole="primary"]:hover, QPushButton#homeContinue:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe0b8, stop:0.48 #ffb05c, stop:0.52 #f8902a, stop:1 #ef8124); }
QPushButton[arcRole="primary"]:pressed, QPushButton#homeContinue:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #c9600f, stop:1 #ff9a32); border-top-color: #8a3f08; }

QToolButton#favoriteGroupMenu {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffcf94, stop:0.48 #ff9e3a, stop:0.52 #f0821a, stop:1 #e47417);
    color: #1d0f04; font-weight: 700; border: 1px solid #a94f0c; border-top-color: #ffe2bb; border-radius: 13px;
    padding: 4px 22px 4px 13px; }
QToolButton#favoriteGroupMenu:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe0b8, stop:0.48 #ffb05c, stop:0.52 #f8902a, stop:1 #ef8124);
    border-color: #c86214; border-top-color: #fff0dc; }
QToolButton#favoriteGroupMenu:pressed, QToolButton#favoriteGroupMenu:open {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b9560c, stop:1 #ff9a32); border-top-color: #7a3606; }
QToolButton#favoriteGroupMenu:focus { border: 2px solid #ffe2bb; }
QToolButton#favoriteGroupMenu::menu-indicator { subcontrol-position: right center; right: 7px; }

QWidget#WorkspaceToolbar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #343c46, stop:0.08 #262d36, stop:1 #171d24);
    border-top: 1px solid #4d5763; border-bottom: 1px solid #0b0e12; }
QWidget#WorkspaceToolbar QToolButton#favoriteCommand:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5c6570, stop:0.5 #3a414a, stop:1 #2a3037);
    border: 1px solid #1b1f24; border-top-color: #858f9a; }
QToolButton#GlobalSearch {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0b0f14, stop:1 #1a2029);
    border: 1px solid #39434f; border-top-color: #07090c; border-bottom-color: #4e5966; border-radius: 13px; }

QToolButton#ActivityButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a535e, stop:0.48 #2f363e, stop:0.52 #242a31, stop:1 #1d2228);
    border: 1px solid #14171b; border-top-color: #6c7682; border-radius: 7px; color: #d4dbe2; }
QToolButton#ActivityButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #57616d, stop:0.48 #39414a, stop:0.52 #2b3239, stop:1 #232930); }
QToolButton#ActivityButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8a5426, stop:0.48 #5c3618, stop:0.52 #462812, stop:1 #3a2210);
    border: 1px solid #ff9a32; border-top-color: #ffc078; color: #ffd7aa; }

QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #48515c, stop:0.5 #2c3239, stop:1 #222830);
    border: 1px solid #14171b; border-top-color: #6b7581; border-radius: 6px; color: #d4dbe2; }
QTabBar::tab:hover:!selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #56606b, stop:0.5 #363d45, stop:1 #29303a); }
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7d4c22, stop:0.5 #4c2d14, stop:1 #3a2210);
    border: 1px solid #ff9a32; border-top: 2px solid #ffb05c; color: #ffffff; }

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a535e, stop:0.5 #303740, stop:1 #262c34);
    color: #e2e7ec; border: 0; border-top: 1px solid #66707b; border-right: 1px solid #1a1e23; border-bottom: 1px solid #0f1215; }
QDockWidget::title {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d4651, stop:0.1 #2a313a, stop:1 #1c222a);
    color: #d7dee5; border-top: 1px solid #5a6470; border-bottom: 1px solid #0d1014; }

QLineEdit, QSpinBox, QComboBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0c0f13, stop:0.25 #151a20, stop:1 #1b2128);
    border: 1px solid #2f3842; border-top-color: #07090b; border-bottom-color: #55606c; border-radius: 6px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #ffb05c; }

QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a737e, stop:0.5 #474e57, stop:1 #343a41); border-radius: 5px; }
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a737e, stop:0.5 #474e57, stop:1 #343a41); border-radius: 5px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffc078, stop:1 #e8771a); }
QSlider::handle:horizontal {
    background: qradialgradient(cx:0.4, cy:0.3, radius:0.8, fx:0.4, fy:0.25, stop:0 #ffe2bb, stop:0.5 #ff9a32, stop:1 #c8600f);
    border: 1px solid #8a3f08; }

QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a313a, stop:1 #161b22); border-top: 1px solid #4d5763; }
QWidget#ArcMast {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d242c, stop:1 #10151a); border-bottom: 1px solid #2f3843; }
QMenu { background: #1b2027; border: 1px solid #5b6570; border-radius: 6px; }
QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffcf94, stop:0.5 #ff9e3a, stop:1 #e47417);
    color: #1d0f04; border-left: 0; border-radius: 4px; }
QToolTip { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #39414b, stop:1 #222830);
    border: 1px solid #ff9a32; border-radius: 4px; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected, QTableView::item:selected {
    border-left: 0; color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7a4720, stop:0.5 #55311a, stop:1 #3f2412); }
"""

# ARC UX 4 · Glass: deeper Aqua treatment. Brushed graphite window, glass headers, orange gel
# selection with dark text for contrast, gel indicators and rounded panes with inner light.
QSS += r"""
QMainWindow { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d232b, stop:1 #0b0f14); }
QWidget#ArcMast {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #48525e, stop:0.46 #2c333c, stop:0.5 #20262e, stop:1 #171c23);
    border-top: 1px solid #6f7a86; border-bottom: 1px solid #07090c; }
QWidget#ArcMast QLabel[arcRole="wordmark"] { color: #ffffff; }
QWidget#WorkspaceToolbar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a545f, stop:0.46 #2e353e, stop:0.5 #222830, stop:1 #191e25);
    border-top: 1px solid #727d89; border-bottom: 1px solid #07090c; }
QWidget#ActivityRail {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e252d, stop:1 #12171d); border-bottom: 1px solid #07090c; }

QTreeWidget#hardwareTree {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #141a21, stop:1 #10151b); }
QTreeWidget#hardwareTree::item:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2f3741, stop:1 #222931); border-radius: 5px; }
QTreeWidget#hardwareTree::item:selected, QTreeView::item:selected:active, QTreeWidget::item:selected:active {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd29a, stop:0.46 #ffa13f, stop:0.5 #f2851c, stop:1 #e47417);
    color: #1d0f04; border: 0; border-top: 1px solid #ffe6c4; border-radius: 5px; }

QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: center right; width: 20px; border-left: 1px solid #1a1e23;
    border-top-right-radius: 6px; border-bottom-right-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66707c, stop:0.48 #424a53, stop:0.52 #323840, stop:1 #2a2f36); }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px; border: 1px solid #14171b; border-top-color: #7d8792;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66707c, stop:0.5 #3b424b, stop:1 #2a3037); }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: qradialgradient(cx:0.5, cy:0.45, radius:0.6, fx:0.45, fy:0.3, stop:0 #fff0dc, stop:0.35 #ffa13f, stop:1 #c8600f);
    border: 1px solid #8a3f08; }
QProgressBar { border-radius: 7px; border: 1px solid #14171b; border-bottom-color: #4e5966;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0b0e12, stop:1 #1c2229); }
QProgressBar::chunk { border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd29a, stop:0.48 #ffa13f, stop:0.52 #f2851c, stop:1 #e47417); }

QTabWidget::pane { border: 1px solid #0f1215; border-top: 1px solid #3e4752; border-radius: 8px; top: -1px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d232b, stop:0.04 #171c23, stop:1 #141920); }
QSplitter::handle {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1317, stop:0.5 #3a434e, stop:1 #0f1317); }
QMainWindow::separator {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b0e12, stop:0.5 #3a434e, stop:1 #0b0e12); width: 3px; height: 3px; }
QWidget#ArcInspector, QTextBrowser#ArcContext {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #19202a, stop:1 #12171e); }
QToolButton#favoriteCommand { border-radius: 9px; }
"""
