"""Application-owned Qt styling. Vendor code and files remain untouched."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

_MARGIN = 16
_GAP = 8
_RADIUS = 5
_CONTROL_PADDING = 6
_TREE_ROW_PADDING = 4
_BLUE = ("#175ca4", "#58a6ff")
_PAGE = ("#f3f5f7", "#202428")
_SURFACE = ("#ffffff", "#282e34")
_TEXT = ("#20262d", "#e6edf3")
_MUTED = ("#606b77", "#9ba8b5")
_BORDER = ("#b7c1cb", "#56616d")
_SELECTION = ("#d9eafa", "#254c72")
_DISABLED = ("#e4e8ed", "#353d45")
_DANGER = ("#b42318", "#ff7b72")
_STATUS_COLORS = {
    "PASS": ("#1a7f37", "#3fb950"),
    "FAIL": ("#cf222e", "#f85149"),
    "ERROR": ("#bc4c00", "#db6d28"),
    "INCOMPLETE": ("#8250df", "#a371f7"),
}


def apply_theme(window, choice):
    app = QApplication.instance()
    dark = choice == "Dark" or (
        choice == "System" and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    )
    index = int(dark)
    page, surface, text, muted, border, accent, selected, disabled, danger = (
        pair[index] for pair in (_PAGE, _SURFACE, _TEXT, _MUTED, _BORDER, _BLUE,
                                _SELECTION, _DISABLED, _DANGER)
    )
    palette = QPalette()
    for role, color in ((QPalette.ColorRole.Window, page), (QPalette.ColorRole.WindowText, text),
                        (QPalette.ColorRole.Base, surface), (QPalette.ColorRole.AlternateBase, page),
                        (QPalette.ColorRole.Text, text), (QPalette.ColorRole.Button, surface),
                        (QPalette.ColorRole.ButtonText, text), (QPalette.ColorRole.Highlight, selected),
                        (QPalette.ColorRole.HighlightedText, text),
                        (QPalette.ColorRole.ToolTipBase, surface), (QPalette.ColorRole.ToolTipText, text),
                        (QPalette.ColorRole.PlaceholderText, muted)):
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(muted))
    app.setPalette(palette)
    window.setStyleSheet(f"""
        QMainWindow, QStatusBar {{ background: {page}; color: {text}; }}
        QGroupBox {{ border: 1px solid {border}; border-radius: {_RADIUS}px;
                     margin-top: {_MARGIN}px; padding: {_GAP}px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: {_GAP}px; color: {muted}; }}
        QLineEdit, QPlainTextEdit, QTreeView, QComboBox {{ background: {surface}; color: {text};
            border: 1px solid {border}; border-radius: {_RADIUS}px; padding: {_CONTROL_PADDING}px;
            selection-background-color: {selected}; selection-color: {text}; }}
        QPushButton, QToolButton {{ background: {surface}; color: {text}; border: 1px solid {border};
            border-radius: {_RADIUS}px; padding: {_CONTROL_PADDING}px {_GAP}px; }}
        QPushButton:hover, QToolButton:hover {{ background: {selected}; }}
        QToolButton#additionalToggle {{ background: transparent; border: none; padding: 0; }}
        QToolButton#additionalToggle:hover {{ background: transparent; color: {accent}; }}
        QPushButton[primary="true"]:enabled {{ background: {accent}; color: {surface}; border-color: {accent}; }}
        QPushButton[danger="true"]:enabled {{ color: {danger}; border-color: {danger}; }}
        QPushButton:disabled, QToolButton:disabled {{ background: {disabled}; color: {muted}; }}
        QPushButton:focus, QToolButton:focus, QLineEdit:focus, QTreeView:focus, QComboBox:focus {{
            border: 1px solid {accent}; }}
        QTreeView::item {{ padding: {_TREE_ROW_PADDING}px; }}
        QTreeView::item:hover {{ background: {selected}; }}
        QTreeView::item:selected {{ background: {selected}; color: {text}; }}
        QHeaderView::section {{ background: {page}; color: {muted}; padding: {_CONTROL_PADDING}px;
                               border: none; }}
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{ padding: {_GAP}px {_MARGIN}px; background: {page}; color: {muted}; }}
        QTabBar::tab:selected {{ background: {surface}; color: {text}; }}
        QSplitter::handle {{ background: {page}; }}
    """)
