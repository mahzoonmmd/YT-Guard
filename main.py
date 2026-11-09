import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from ytguard.context import AppContext
from ytguard.i18n import DIR
from ytguard.main_window import MainWindow
from ytguard.theme import load_fonts


def asset_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "assets"


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(DIR)
    family = load_fonts(asset_dir())
    app.setFont(QFont(family, 11))
    ctx = AppContext()
    win = MainWindow(ctx, family)
    win.show()
    from ytguard.prereq_dialog import maybe_show_first_run
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(250, lambda: maybe_show_first_run(ctx, win))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
