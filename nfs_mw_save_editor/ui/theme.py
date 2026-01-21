from __future__ import annotations

ACCENT = "#f2c200"
ACCENT_SOFT = "#2b2510"
BG = "#0b0c0f"
BG_PANEL = "#11121a"
TEXT = "#f7f7f8"
MUTED = "#a9abb5"
BORDER = "#1f2230"

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
QPushButton:hover {{ background-color: #191a2b; }}
QPushButton:pressed {{ background-color: #0e0f18; }}
QPushButton:disabled {{ color: #555; border-color: #333; }}
QPushButton:checked {{
    background: {ACCENT};
    color: #0b0c0f;
    border-color: {ACCENT};
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
QScrollBar::handle:vertical:hover {{ background: #ffdb3d; }}
"""

def apply_theme(app) -> None:
    """Apply the yellow/black Black Edition inspired theme."""
    app.setStyleSheet(STYLE)
