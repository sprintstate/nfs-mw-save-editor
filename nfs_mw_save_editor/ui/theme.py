from __future__ import annotations

ACCENT = "#6fea4d"
ACCENT_SOFT = "#182717"
BG = "#0a0f0a"
BG_PANEL = "#101810"
TEXT = "#f1f5f1"
MUTED = "#9bb09b"
BORDER = "#1f2b1f"

STYLE = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Bahnschrift', sans-serif;
    font-size: 12.5px;
}}
QMainWindow {{ background-color: {BG}; }}
QLabel {{ color: {TEXT}; }}
QLabel#mutedLabel {{ color: {MUTED}; }}
QLabel#sectionLabel {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 700;
    margin-top: 4px;
}}
QFrame#sectionLine {{
    background: {BORDER};
    max-height: 1px;
}}
QLabel#pillLabel {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 14px;
    padding: 6px 12px;
    font-weight: 600;
}}
QPushButton {{
    background-color: #131420;
    color: {ACCENT};
    border: 1px solid {ACCENT_SOFT};
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #162116; }}
QPushButton:pressed {{ background-color: #0c130c; }}
QPushButton:disabled {{ color: #555; border-color: #333; }}
QPushButton:checked {{
    background: {ACCENT};
    color: #0b0c0f;
    border-color: {ACCENT};
}}
QPushButton#navButton {{
    text-align: left;
    padding: 8px 12px 8px 14px;
    border-left: 3px solid transparent;
}}
QPushButton#navButton:checked {{
    background: #182118;
    border-left: 3px solid {ACCENT};
    color: {ACCENT};
}}
QPushButton#navButton:hover {{
    background: #141c14;
}}
QPushButton#catButton {{
    padding: 6px 12px;
    min-height: 28px;
    text-align: left;
}}
QPushButton#iconBtn {{
    padding: 0px 0px;
    min-height: 24px;
}}
QWidget#tokenRow {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QWidget#tokenRow[changed="true"] {{
    border: 1px solid {ACCENT};
    background: rgba(111, 234, 77, 0.08);
}}
QLabel#haveLabel {{
    color: {MUTED};
    font-size: 11.5px;
}}
QWidget#tokenRow QLineEdit {{
    background: transparent;
    border: none;
    padding: 4px 6px;
}}
QWidget#tokenRow QSpinBox {{
    background: #0e0f17;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {ACCENT};
    selection-color: #0b0c0f;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    border: 0px;
    background: transparent;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{ width: 8px; height: 8px; }}
QScrollArea {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {BG_PANEL};
}}
QToolButton {{
    background-color: #131420;
    color: {ACCENT};
    border: 1px solid {ACCENT_SOFT};
    border-radius: 8px;
    padding: 8px 12px;
}}
QLabel#unsavedLabel {{
    color: {ACCENT};
    font-weight: 600;
    padding-left: 6px;
}}
QLabel#filePath {{
    color: {TEXT};
}}
QMenu {{
    background: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: #0b0c0f;
}}
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 12px;
    margin: 2px 0 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {ACCENT};
    min-height: 20px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical:hover {{ background: #8fff6a; }}
"""

def apply_theme(app) -> None:
    """Apply the yellow/black Black Edition inspired theme."""
    app.setStyleSheet(STYLE)
