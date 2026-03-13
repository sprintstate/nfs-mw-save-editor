from __future__ import annotations

ACCENT = "#4A6B94"
ACCENT_BRIGHT = "#6F93C4"
ACCENT_SOFT = "#1A2536"
BG = "#0B0F15"
BG_PANEL = "#111828"
BG_CARD = "#131C2C"
TEXT = "#EAF0FA"
MUTED = "#94A4BC"
BORDER = "#27344A"

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
QLabel#gridSectionLabel {{
    color: {TEXT};
    font-size: 15px;
    font-weight: 700;
    padding: 8px 4px 2px 4px;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 2px;
}}
QFrame#sectionLine {{
    background: {BORDER};
    max-height: 1px;
}}
QLabel#pillLabel {{
    background: {ACCENT_SOFT};
    color: {ACCENT_BRIGHT};
    border: 1px solid {ACCENT};
    border-radius: 14px;
    padding: 6px 12px;
    font-weight: 600;
}}

/* Buttons */
QPushButton {{
    background-color: #141B2B;
    color: {TEXT};
    border: 1px solid {ACCENT_SOFT};
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #1A2436; }}
QPushButton:pressed {{ background-color: #121A28; }}
QPushButton:disabled {{ color: #6D7686; border-color: #333C4B; }}
QPushButton:checked {{
    background: {ACCENT};
    color: {TEXT};
    border-color: {ACCENT_BRIGHT};
}}
QPushButton#navButton {{
    text-align: left;
    padding: 8px 12px 8px 14px;
    border-left: 3px solid transparent;
    min-height: 36px;
}}
QPushButton#navButton:checked {{
    background: #1D2940;
    border-left: 3px solid {ACCENT_BRIGHT};
    color: {TEXT};
}}
QPushButton#navButton:hover {{
    background: #182236;
}}
QPushButton#catButton {{
    padding: 6px 12px;
    min-height: 28px;
    text-align: left;
}}
QPushButton#cardBtn {{
    padding: 0px;
    min-height: 24px;
    min-width: 24px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#iconBtn {{
    padding: 0px 0px;
    min-height: 24px;
}}

/* Token Card */
QWidget#tokenCard {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 0px;
}}
QWidget#tokenCard[changed="true"] {{
    border: 1px solid #4A678E;
    background: rgba(74, 107, 148, 0.12);
}}
QWidget#tokenCard[hovered="true"] {{
    border: 1px solid #3A5274;
    background: #182338;
}}
QWidget#tokenCard[changed="true"][hovered="true"] {{
    border: 1px solid #5E80AF;
    background: rgba(111, 147, 196, 0.16);
}}
QWidget#tokenCard QLabel#haveLabel {{
    color: {MUTED};
    font-size: 11px;
}}
QWidget#tokenCard QLineEdit#cardName {{
    background: transparent;
    border: none;
    padding: 2px 4px;
    font-size: 12px;
    font-weight: 600;
    color: {TEXT};
}}
QWidget#tokenCard QSpinBox {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 2px 4px;
    font-size: 12px;
}}

/* Slider */
QSlider#cardSlider::groove:horizontal {{
    background: {BORDER};
    height: 6px;
    border-radius: 3px;
}}
QSlider#cardSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSlider#cardSlider::handle:horizontal:hover {{
    background: {ACCENT_BRIGHT};
}}
QSlider#cardSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}

/* Legacy TokenRow (compat) */
QWidget#tokenRow {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QWidget#tokenRow[changed="true"] {{
    border: 1px solid {ACCENT};
    background: rgba(74, 107, 148, 0.14);
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
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* Inputs */
QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {ACCENT};
    selection-color: {TEXT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    border: 0px;
    background: transparent;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{ width: 8px; height: 8px; }}

/* Scroll */
QScrollArea {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {BG_PANEL};
}}
QScrollArea#cardScroll {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    background: {BG};
}}

/* Misc */
QToolButton {{
    background-color: #141B2B;
    color: {TEXT};
    border: 1px solid {ACCENT_SOFT};
    border-radius: 8px;
    padding: 8px 12px;
}}
QLabel#unsavedLabel {{
    color: {ACCENT_BRIGHT};
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
    color: {TEXT};
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
QScrollBar::handle:vertical:hover {{ background: {ACCENT_BRIGHT}; }}
QCheckBox {{
    spacing: 6px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_PANEL};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT_BRIGHT};
}}

/* Progress Bar */
QProgressBar#tokenProgress {{
    background: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 9px;
    text-align: center;
    color: {TEXT};
    font-size: 10px;
    font-weight: 600;
}}
QProgressBar#tokenProgress::chunk {{
    background: {ACCENT};
    border-radius: 8px;
}}

/* Empty State Overlay */
QWidget#emptyOverlay {{
    background: transparent;
}}
QLabel#emptyTitle {{
    color: {MUTED};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#emptyHint {{
    color: #6D7F98;
    font-size: 13px;
}}

/* Toast Notifications */
QLabel#toastSuccess {{
    background: rgba(52, 76, 113, 0.94);
    color: {TEXT};
    border: 1px solid {ACCENT_BRIGHT};
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#toastError {{
    background: rgba(100, 30, 30, 0.92);
    color: {TEXT};
    border: 1px solid #CC4444;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}}

/* Stat Tiles (Profile summary strip) */
QFrame#statTile {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 0px;
}}
QLabel#statTileHeading {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 3px 8px;
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
QLabel#statTileValue {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 4px 12px;
    color: {ACCENT_BRIGHT};
    font-size: 18px;
    font-weight: 700;
}}
QLineEdit#statTileEdit {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 16px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#statTileSub {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 3px 8px;
    color: {MUTED};
    font-size: 10.5px;
}}

/* Garage Car Cards */
QFrame#garageCard {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#garageCard[changed="true"] {{
    border: 1px solid #4A678E;
    background: rgba(74, 107, 148, 0.12);
}}
QFrame#garageCard[occupied="false"] {{
    opacity: 0.6;
}}
QLabel#garageCardSlot {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 3px 8px;
    color: {MUTED};
    font-size: 10.5px;
    font-weight: 600;
}}
QLabel#garageCardMeta {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px 9px;
    color: {TEXT};
    font-size: 12px;
    font-weight: 700;
}}
QLabel#garageCardFieldLabel {{
    background: transparent;
    color: {MUTED};
    font-size: 10.5px;
    font-weight: 600;
}}
QFrame#garageCardSep {{
    color: {BORDER};
}}
QLineEdit#garageCardEdit {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 5px 8px;
    font-size: 14px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#garageCardCurrent {{
    background: transparent;
    color: {MUTED};
    font-size: 10.5px;
}}
QLabel#garageCardStatBadge {{
    background: #0F1524;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 3px 8px;
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
}}

/* About Page */
QLabel#aboutTitle {{
    color: {TEXT};
    font-size: 18px;
    font-weight: 700;
}}
QFrame#separator {{
    color: {BORDER};
    max-height: 1px;
}}
"""


def apply_theme(app) -> None:
    """Apply the dark blue theme."""
    app.setStyleSheet(STYLE)
