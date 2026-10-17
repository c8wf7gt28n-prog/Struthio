"""ARC-1 Workbench R08 restrained orange Aqua Qt 6 style.

Professional controls: 25–28 px, 3–4 px corners, graphite/ivory neutrals,
small orange focus indication instead of oversized bevel/gloss buttons.
"""
DARK = "#22272b"
ORANGE = "#c87735"
QSS = r"""
QMainWindow { background: #22272b; }
QWidget { font-family: 'Segoe UI', 'Arial'; font-size: 10pt; }
QMenuBar { background: #272c31; color: #e9e8e5; padding: 2px 5px; spacing: 3px; }
QMenuBar::item { padding: 5px 9px; border-radius: 3px; }
QMenuBar::item:selected { background: #40454b; color: #fff; }
QMenu { background: #30353b; color: #eee; border: 1px solid #52565b; padding: 4px; }
QMenu::item { padding: 6px 25px; }
QMenu::item:selected { background: #735039; color: #fff; }
QToolBar { background: #2f3439; border: 0; border-bottom: 1px solid #4f4440; spacing: 2px; padding: 3px 8px; }
QToolButton, QPushButton { background: #3c4248; color: #f0efed; border: 1px solid #55595d; border-radius: 4px; min-height: 23px; padding: 2px 10px; }
QToolButton:hover, QPushButton:hover { background: #495057; border-color: #9c6844; }
QToolButton:pressed, QPushButton:pressed { background: #5c4839; }
QToolButton:checked { background: #3d4145; border-bottom: 2px solid #ca7d3b; }
QPushButton:disabled, QToolButton:disabled { color: #96999b; background: #353a3d; }
QLineEdit { background: #f9f7f2; color: #262b30; border: 1px solid #c7bdb2; border-radius: 3px; padding: 5px 8px; }
QLineEdit:focus { border: 1px solid #c87735; }
QDockWidget { color: #dfd8d2; font-weight: 600; }
QDockWidget::title { background: #31363c; padding: 6px 8px; border-bottom: 1px solid #514a42; }
QDockWidget::close-button, QDockWidget::float-button { border: 0; padding: 2px; }
QTreeView, QListWidget, QTableView { background: #f8f6f1; color: #2d3135; alternate-background-color: #eeebe6; selection-background-color: #ead5c2; selection-color: #2d3135; border: 0; outline: 0; }
QTreeView::item, QListWidget::item { min-height: 22px; }
QTreeView::item:selected, QListWidget::item:selected { border-left: 3px solid #c87735; }
QHeaderView::section { background: #e6e0d7; color: #4b4440; border: 0; border-bottom: 1px solid #cac1b8; padding: 5px; }
QTabWidget::pane { border: 0; }
QTabBar { background: #31363a; }
QTabBar::tab { background: #353b40; color: #cecbc8; padding: 7px 14px; border-right: 1px solid #46494c; }
QTabBar::tab:selected { background: #f8f6f1; color: #2b3035; border-top: 2px solid #c87735; }
QTabBar::tab:hover:!selected { background: #484e53; }
QPlainTextEdit#sourceEditor { background: #faf8f4; color: #252a2e; border: 0; selection-background-color: #f1d5b9; }
QPlainTextEdit#console { background: #171c20; color: #cbd8ca; border: 0; padding: 7px; }
QPlainTextEdit#inspector { background: #f8f6f1; color: #2f3438; border: 0; }
QStatusBar { background: #22272b; color: #d7d8d8; border-top: 1px solid #7d5536; }
QSplitter::handle { background: #495057; }
QLabel#brandLabel { background: #252a2f; color: #f5f1e9; padding-left: 6px; }
QLabel#evidence { color: #e9b38e; background: #272c31; padding: 3px 9px; }
QLabel#lcd { background: #dac195; color: #363127; border: 2px solid #54504a; border-radius: 4px; padding: 12px; font-family: Consolas, monospace; font-size: 13pt; }
"""
