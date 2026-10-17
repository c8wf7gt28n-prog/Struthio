"""ARC-1 Workbench theme (R10.5, owner decision: "All UI should be ARC-1 coloured").

Colours come from the ARC-1 logo: near-black surfaces, brushed-steel chrome and
text, and ARC-1 orange for focus, the active tab and selection edges. The R10
Classic layout (menus, one compact toolbar, docks) is unchanged; only colour
moved from ivory to the logo palette.

Windows keeps its own title bar and minimize/maximize/close buttons; this
style sheet only touches the client area. Sizes are in points or padding, not
fixed pixel heights, so Windows text scaling still works.
"""
ORANGE = '#ff5a1a'        # accent: focus, active tab, current selection edge (the "-" in ARC-1)
ORANGE_DEEP = '#c8400c'   # pressed / dashed requirement lines
ORANGE_SOFT = '#3a1d10'   # selection fill
BLACK = '#0b0b0c'         # window background (the logo's backdrop)
PANEL = '#141517'         # documents and lists
RAISED = '#1d1f22'        # toolbars, headers, docks
STEEL_DARK = '#2a2d31'    # buttons, hover
LINE = '#33373c'          # hairlines
STEEL = '#a9aeb4'         # secondary text, icons
TEXT = '#e4e6e8'          # primary text (the logo's polished steel)
MUTED = '#7d838a'

QSS = r"""
QMainWindow, QDialog { background: #0b0b0c; }
QWidget { color: #e4e6e8; font-family: 'Segoe UI', 'Noto Sans', 'DejaVu Sans', 'Arial'; font-size: 9.5pt; }
QToolTip { background: #1d1f22; color: #e4e6e8; border: 1px solid #ff5a1a; padding: 4px 6px; }

QMenuBar { background: #0b0b0c; border-bottom: 1px solid #33373c; padding: 1px 4px; }
QMenuBar::item { padding: 4px 9px; border-radius: 4px; background: transparent; color: #d7dadd; }
QMenuBar::item:selected { background: #2a2d31; }
QMenuBar::item:pressed { background: #3a1d10; color: #ffffff; }
QMenu { background: #141517; border: 1px solid #33373c; padding: 4px 0; }
QMenu::item { padding: 5px 28px 5px 24px; }
QMenu::item:selected { background: #3a1d10; color: #ffffff; border-left: 2px solid #ff5a1a; }
QMenu::item:disabled { color: #5b6066; }
QMenu::separator { height: 1px; background: #2a2d31; margin: 4px 8px; }

QToolBar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2d31, stop:0.5 #1d1f22, stop:1 #141517);
           border: 0; border-bottom: 1px solid #ff5a1a; spacing: 3px; padding: 3px 6px; }
QToolBar::separator { width: 1px; background: #3a3e44; margin: 4px 5px; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 3px 9px;
              color: #e4e6e8; }
QToolButton:hover { background: #2a2d31; border-color: #4a4f56; }
QToolButton:pressed, QToolButton:checked { background: #3a1d10; border-color: #ff5a1a; }
QToolButton[popupMode="1"] { padding-right: 18px; }
QToolButton::menu-button { width: 16px; border: 0; border-left: 1px solid #3a3e44; background: transparent; }
QToolButton::menu-button:hover { background: #3a1d10; }

QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34383d, stop:1 #222528);
              border: 1px solid #44494f; border-radius: 4px; padding: 4px 14px; color: #e4e6e8; }
QPushButton:hover { border-color: #ff5a1a; }
QPushButton:pressed { background: #3a1d10; }
QPushButton:default { border: 1px solid #ff5a1a; }
QPushButton:disabled { color: #5b6066; }
QPushButton#linkButton { background: transparent; border: 0; color: #ff7a3c; padding: 2px 0; text-align: left; }
QPushButton#linkButton:hover { text-decoration: underline; }

QComboBox { background: #141517; border: 1px solid #44494f; border-radius: 4px; padding: 2px 8px; min-width: 9em;
            color: #e4e6e8; }
QComboBox:hover, QComboBox:focus { border-color: #ff5a1a; }
QComboBox QAbstractItemView { background: #141517; color: #e4e6e8; selection-background-color: #3a1d10;
                              selection-color: #ffffff; border: 1px solid #33373c; }
QLineEdit, QSpinBox { background: #141517; color: #e4e6e8; border: 1px solid #44494f; border-radius: 4px;
                      padding: 3px 6px; selection-background-color: #ff5a1a; selection-color: #ffffff; }
QLineEdit:focus, QSpinBox:focus { border-color: #ff5a1a; }
QCheckBox, QRadioButton { color: #e4e6e8; }

QDockWidget { titlebar-close-icon: none; font-weight: 600; color: #d7dadd; }
QDockWidget::title { background: #1d1f22; padding: 4px 8px; border-bottom: 1px solid #33373c; text-align: left; }

QTreeView, QTreeWidget, QListWidget, QTableView {
    background: #141517; alternate-background-color: #17181b; border: 0; outline: 0; color: #e4e6e8;
    selection-background-color: #3a1d10; selection-color: #ffffff; }
QTreeView::item, QTreeWidget::item, QListWidget::item { padding: 2px 0; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { border-left: 2px solid #ff5a1a; }
QTreeView::item:hover, QTreeWidget::item:hover { background: #1f2124; }
QTreeView::item:disabled, QTreeWidget::item:disabled { color: #5b6066; }
QHeaderView::section { background: #1d1f22; color: #a9aeb4; border: 0; border-right: 1px solid #2a2d31;
                       border-bottom: 1px solid #33373c; padding: 4px 6px; }

QTabWidget::pane { border: 0; border-top: 1px solid #33373c; background: #141517; }
QTabBar::tab { background: #1d1f22; color: #a9aeb4; padding: 5px 12px; border: 1px solid #33373c; border-bottom: 0;
               margin-right: -1px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #141517; color: #ffffff; border-top: 2px solid #ff5a1a; }
QTabBar::tab:hover:!selected { background: #26292d; color: #e4e6e8; }
QTabBar::close-button { subcontrol-position: right; }

QPlainTextEdit#sourceEditor, QPlainTextEdit#outputText, QPlainTextEdit#inspector {
    font-family: 'Consolas', 'Cascadia Mono', 'DejaVu Sans Mono', 'Menlo', 'Courier New', monospace; }
QPlainTextEdit#sourceEditor { font-size: 10pt; }
QPlainTextEdit#outputText, QPlainTextEdit#inspector { font-size: 9pt; }
QPlainTextEdit#sourceEditor { background: #101113; color: #e4e6e8; border: 0;
                              selection-background-color: #5a2a12; selection-color: #ffffff; }
QPlainTextEdit#outputText { background: #101113; color: #d7dadd; border: 0; selection-background-color: #5a2a12; }
QPlainTextEdit#inspector { background: #101113; color: #d7dadd; border: 0; }
QTextEdit, QPlainTextEdit { background: #101113; color: #e4e6e8; }
QLabel { color: #e4e6e8; }
QLabel#docInfo { background: #141517; color: #a9aeb4; border-top: 1px solid #2a2d31; padding: 2px 10px; }
QLabel#deviceBadge { background: #141517; color: #ff7a3c; border: 1px solid #ff5a1a; border-radius: 9px;
                     padding: 1px 10px; font-weight: 600; font-size: 8.5pt; }
QLabel#heading { font-size: 17pt; font-weight: 600; color: #ffffff; }
QLabel#subheading { color: #a9aeb4; }
QLabel#sectionTitle { font-weight: 600; color: #a9aeb4; padding-top: 10px; }
QLabel#simBanner { background: #2a1408; color: #ffb38c; border: 1px solid #ff5a1a; border-radius: 4px; padding: 4px 8px; }
QLabel#lcd { background: #120804; color: #ff7a3c; border: 2px solid #4a4f56; border-radius: 4px; padding: 10px;
             font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 12pt; }
QLabel#framePreview { background: #000000; border: 1px solid #33373c; }
QScrollArea { background: #141517; border: 0; }

QStatusBar { background: #0b0b0c; color: #a9aeb4; border-top: 1px solid #33373c; }
QStatusBar QLabel { padding: 0 8px; color: #a9aeb4; }
QSplitter::handle { background: #1d1f22; }
QSlider::groove:horizontal { height: 4px; background: #2a2d31; border-radius: 2px; }
QSlider::handle:horizontal { background: #ff5a1a; width: 12px; margin: -5px 0; border-radius: 6px; }
QScrollBar:vertical { background: #101113; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #3a3e44; border-radius: 5px; min-height: 24px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #ff5a1a; }
QScrollBar:horizontal { background: #101113; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #3a3e44; border-radius: 5px; min-width: 24px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #ff5a1a; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""
