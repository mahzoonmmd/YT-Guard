import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from ytguard.context import AppContext
from ytguard.main_window import MainWindow
from ytguard.theme import load_fonts


def asset_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "assets"


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    family = load_fonts(asset_dir())
    app.setFont(QFont(family, 11))
    ctx = AppContext()
    win = MainWindow(ctx, family)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
