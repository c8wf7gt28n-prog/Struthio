"""ARC-1 Workbench Classic theme (R10): light ivory/gray work surfaces, subtle
material depth, compact controls and restrained orange accents.

Windows keeps its own title bar and minimize/maximize/close buttons; this
style sheet only touches the client area. Sizes are in points or padding, not
fixed pixel heights, so Windows text scaling still works.
"""
ORANGE = '#e07a1f'        # accent: focus, active tab, current selection edge
ORANGE_SOFT = '#f6dcc0'   # selection fill
IVORY = '#fbfaf6'         # documents and lists
SURFACE = '#f0eee9'       # window, toolbars, docks
LINE = '#d4cfc6'          # hairlines
TEXT = '#23272b'
MUTED = '#6b6f73'

QSS = r"""
QMainWindow, QDialog { background: #f0eee9; }
QWidget { color: #23272b; font-family: 'Segoe UI', 'Noto Sans', 'DejaVu Sans', 'Arial'; font-size: 9.5pt; }

QMenuBar { background: #f0eee9; border-bottom: 1px solid #dcd7cf; padding: 1px 4px; }
QMenuBar::item { padding: 4px 9px; border-radius: 4px; background: transparent; }
QMenuBar::item:selected { background: #e4dfd7; }
QMenuBar::item:pressed { background: #f6dcc0; }
QMenu { background: #fbfaf6; border: 1px solid #cfc9bf; padding: 4px 0; }
QMenu::item { padding: 5px 28px 5px 24px; }
QMenu::item:selected { background: #f6dcc0; color: #23272b; }
QMenu::item:disabled { color: #a3a5a7; }
QMenu::separator { height: 1px; background: #e2ddd5; margin: 4px 8px; }

QToolBar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f6f2, stop:1 #ebe8e2);
           border: 0; border-bottom: 1px solid #d4cfc6; spacing: 3px; padding: 3px 6px; }
QToolBar::separator { width: 1px; background: #d4cfc6; margin: 4px 5px; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 3px 9px; }
QToolButton:hover { background: #fbfaf6; border-color: #cfc9bf; }
QToolButton:pressed, QToolButton:checked { background: #f6dcc0; border-color: #e0a76f; }
QToolButton[popupMode="1"] { padding-right: 18px; }
QToolButton::menu-button { width: 16px; border: 0; border-left: 1px solid #d4cfc6; background: transparent; }
QToolButton::menu-button:hover { background: #f6dcc0; }

QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #ece9e3);
              border: 1px solid #c9c3b9; border-radius: 4px; padding: 4px 14px; }
QPushButton:hover { border-color: #e0a76f; }
QPushButton:pressed { background: #f6dcc0; }
QPushButton:default { border: 1px solid #e07a1f; }
QPushButton:disabled { color: #a3a5a7; }
QPushButton#linkButton { background: transparent; border: 0; color: #b4560d; padding: 2px 0; text-align: left; }
QPushButton#linkButton:hover { text-decoration: underline; }

QComboBox { background: #fbfaf6; border: 1px solid #c9c3b9; border-radius: 4px; padding: 2px 8px; min-width: 9em; }
QComboBox:hover, QComboBox:focus { border-color: #e07a1f; }
QComboBox QAbstractItemView { background: #fbfaf6; selection-background-color: #f6dcc0; selection-color: #23272b; }
QLineEdit, QSpinBox { background: #ffffff; border: 1px solid #c9c3b9; border-radius: 4px; padding: 3px 6px; }
QLineEdit:focus, QSpinBox:focus { border-color: #e07a1f; }

QDockWidget { titlebar-close-icon: none; font-weight: 600; }
QDockWidget::title { background: #e9e6e0; padding: 4px 8px; border-bottom: 1px solid #d4cfc6; text-align: left; }

QTreeView, QTreeWidget, QListWidget, QTableView {
    background: #fbfaf6; alternate-background-color: #f5f3ee; border: 0; outline: 0;
    selection-background-color: #f6dcc0; selection-color: #23272b; }
QTreeView::item, QTreeWidget::item, QListWidget::item { padding: 2px 0; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { border-left: 2px solid #e07a1f; }
QTreeView::item:hover, QTreeWidget::item:hover { background: #f3ede4; }
QHeaderView::section { background: #efece6; color: #4d4f52; border: 0; border-right: 1px solid #dcd7cf;
                       border-bottom: 1px solid #d4cfc6; padding: 4px 6px; }

QTabWidget::pane { border: 0; border-top: 1px solid #d4cfc6; background: #fbfaf6; }
QTabBar::tab { background: #ebe8e2; color: #4d4f52; padding: 5px 12px; border: 1px solid #d4cfc6; border-bottom: 0;
               margin-right: -1px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #fbfaf6; color: #23272b; border-top: 2px solid #e07a1f; }
QTabBar::tab:hover:!selected { background: #f5f2ec; }
QTabBar::close-button { subcontrol-position: right; }

QPlainTextEdit#sourceEditor, QPlainTextEdit#outputText, QPlainTextEdit#inspector {
    font-family: 'Consolas', 'Cascadia Mono', 'DejaVu Sans Mono', 'Menlo', 'Courier New', monospace; }
QPlainTextEdit#sourceEditor { font-size: 10pt; }
QPlainTextEdit#outputText, QPlainTextEdit#inspector { font-size: 9pt; }
QPlainTextEdit#sourceEditor { background: #fffefb; color: #1f2327; border: 0;
                              selection-background-color: #f6dcc0; selection-color: #1f2327; }
QPlainTextEdit#outputText { background: #fbfaf6; color: #2b2f33; border: 0; }
QPlainTextEdit#inspector { background: #fbfaf6; border: 0; }
QLabel#docInfo { background: #f3f1ec; color: #5d6064; border-top: 1px solid #e2ddd5; padding: 2px 10px; }
QLabel#deviceBadge { background: #fbfaf6; color: #8a4a12; border: 1px solid #e3c09c; border-radius: 9px;
                     padding: 1px 10px; font-weight: 600; font-size: 8.5pt; }
QLabel#heading { font-size: 17pt; font-weight: 600; color: #23272b; }
QLabel#subheading { color: #6b6f73; }
QLabel#sectionTitle { font-weight: 600; color: #4d4f52; padding-top: 10px; }
QLabel#simBanner { background: #fff3e4; color: #8a4a12; border: 1px solid #ecc79f; border-radius: 4px; padding: 4px 8px; }
QLabel#lcd { background: #d9c79d; color: #34302a; border: 2px solid #8c8577; border-radius: 4px; padding: 10px;
             font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 12pt; }
QLabel#framePreview { background: #2a2d31; border: 1px solid #c9c3b9; }

QStatusBar { background: #ebe8e2; color: #4d4f52; border-top: 1px solid #d4cfc6; }
QStatusBar QLabel { padding: 0 8px; }
QSplitter::handle { background: #e2ddd5; }
QScrollBar:vertical { background: #f3f1ec; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #cfc9bf; border-radius: 5px; min-height: 24px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #e0a76f; }
QScrollBar:horizontal { background: #f3f1ec; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #cfc9bf; border-radius: 5px; min-width: 24px; margin: 2px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
"""
