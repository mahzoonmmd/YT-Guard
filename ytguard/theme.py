"""YouTube-style red/white (light) and red/black (dark) themes."""
from __future__ import annotations

from pathlib import Path

from .i18n import IS_RTL

LIGHT = {
    "bg": "#FFFFFF", "surface": "#F7F7F7", "surface2": "#EFEFEF", "border": "#E0E0E0",
    "text": "#0F0F0F", "muted": "#606060", "accent": "#FF0000", "accent_hover": "#CC0000",
    "accent_text": "#FFFFFF", "ok": "#1E8E3E", "warn": "#E37400", "bad": "#D93025", "info": "#1A73E8",
    "input": "#FFFFFF", "sidebar": "#FFFFFF", "sel": "#FDE8E8",
}
DARK = {
    "bg": "#0F0F0F", "surface": "#181818", "surface2": "#272727", "border": "#303030",
    "text": "#F1F1F1", "muted": "#AAAAAA", "accent": "#FF0000", "accent_hover": "#FF3B3B",
    "accent_text": "#FFFFFF", "ok": "#3DDC84", "warn": "#FFB020", "bad": "#FF5A4D", "info": "#6CB4FF",
    "input": "#121212", "sidebar": "#0F0F0F", "sel": "#2A1515",
}


def palette(name: str) -> dict:
    return DARK if name == "dark" else LIGHT


def qss(name: str, font_family: str) -> str:
    c = palette(name)
    S = "right" if IS_RTL else "left"      # side of the accent bar / logical start
    O = "left" if IS_RTL else "right"      # opposite side
    return f"""
* {{ font-family: "{font_family}", "Segoe UI", Tahoma, sans-serif; font-size: 15px; }}
QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QLabel {{ background: transparent; }}
QLabel[muted="true"] {{ color: {c['muted']}; }}
QLabel[h1="true"] {{ font-size: 27px; font-weight: 700; }}
QLabel[h2="true"] {{ font-size: 17px; font-weight: 700; }}
QFrame[card="true"], QGroupBox {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QGroupBox {{ margin-top: 14px; padding: 14px 10px 10px 10px; font-weight: 700; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top {S}; {S}: 14px; padding: 0 6px; color: {c['accent']}; background: {c['bg']}; }}
QFrame#topbar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
QFrame#sidebar {{ background: {c['sidebar']}; border-{O}: 1px solid {c['border']}; }}
QPushButton {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 9px; padding: 9px 18px; }}
QPushButton:hover {{ border-color: {c['accent']}; }}
QPushButton:disabled {{ color: {c['muted']}; }}
QPushButton[primary="true"] {{ background: {c['accent']}; color: {c['accent_text']}; border: none; font-weight: 700; padding: 10px 22px; }}
QPushButton[primary="true"]:hover {{ background: {c['accent_hover']}; }}
QPushButton[primary="true"]:disabled {{ background: {c['surface2']}; color: {c['muted']}; }}
QPushButton[nav="true"] {{ background: transparent; border: none; border-radius: 10px; text-align: {S}; padding: 12px 14px; font-size: 16px; }}
QPushButton[nav="true"]:hover {{ background: {c['surface2']}; }}
QPushButton[nav="true"][active="true"] {{ background: {c['sel']}; color: {c['accent']}; font-weight: 700; }}
QPushButton[flat="true"] {{ background: transparent; border: none; color: {c['accent']}; padding: 4px 8px; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {c['input']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 8px 10px; selection-background-color: {c['accent']}; selection-color: white; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']}; selection-background-color: {c['accent']}; selection-color: white; }}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 17px; height: 17px; border: 2px solid {c['muted']}; background: {c['input']}; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}
QProgressBar {{ background: {c['surface2']}; border: none; border-radius: 6px; height: 10px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 6px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ height: 11px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; }}
QListWidget, QTableWidget {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; outline: none; }}
QListWidget::item {{ padding: 9px 10px; border-radius: 8px; margin: 2px 4px; }}
QListWidget::item:selected {{ background: {c['sel']}; color: {c['accent']}; }}
QListWidget::item:hover {{ background: {c['surface2']}; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 10px; }}
QTabBar::tab {{ background: transparent; padding: 8px 16px; border-bottom: 3px solid transparent; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; font-weight: 700; }}
QToolTip {{ background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 5px; }}
QFrame#drop {{ background: {c['surface']}; border: 2px dashed {c['border']}; border-radius: 16px; }}
QFrame#drop[hover="true"] {{ border-color: {c['accent']}; background: {c['sel']}; }}
QFrame[sev="high"] {{ border-{S}: 5px solid {c['bad']}; }}
QFrame[sev="medium"] {{ border-{S}: 5px solid {c['warn']}; }}
QFrame[sev="low"] {{ border-{S}: 5px solid {c['info']}; }}
QFrame[sev="info"] {{ border-{S}: 5px solid {c['border']}; }}
QLabel[chip="true"] {{ background: {c['surface2']}; border-radius: 9px; padding: 3px 10px; font-size: 13px; }}
QLabel[chip="true"][sev="high"] {{ background: {c['bad']}; color: white; }}
QLabel[chip="true"][sev="medium"] {{ background: {c['warn']}; color: #111; }}
QLabel[chip="true"][sev="low"] {{ background: {c['info']}; color: #111; }}
QMessageBox {{ background: {c['bg']}; }}
"""


def load_fonts(assets_dir: Path) -> str:
    from PyQt6.QtGui import QFontDatabase

    family = "Vazirmatn"
    loaded = False
    for f in sorted((assets_dir / "fonts").glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(f)) != -1:
            loaded = True
    return family if loaded else "Segoe UI"
