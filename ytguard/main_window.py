from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from .i18n import DIR, IS_RTL, tr
from . import APP_NAME, APP_NAME_FA, TAGLINE_FA
from .context import AppContext
from .page_check import CheckPage
from .page_misc import AboutPage, HistoryPage, RulesPage, SettingsPage
from .page_tools import ToolsPage
from .theme import qss
from .widgets import LogoBadge, label, make_app_icon, repolish


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext, font_family: str):
        super().__init__()
        self.ctx = ctx
        self.font_family = font_family
        self.setWindowTitle(f"{APP_NAME_FA} — {APP_NAME}")
        self.setWindowIcon(QIcon(make_app_icon(256)))
        self.resize(1260, 860)
        self.setMinimumSize(980, 640)
        self.setLayoutDirection(DIR)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- top bar
        top = QFrame(); top.setObjectName("topbar"); top.setFixedHeight(58)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(18, 0, 18, 0)
        tl.addWidget(LogoBadge(34))
        t = label(f"{APP_NAME_FA}", h2=True, wrap=False)
        t.setStyleSheet("font-size:17px;")
        sub = label(TAGLINE_FA, muted=True, wrap=False)
        tl.addWidget(t)
        tl.addWidget(sub)
        tl.addStretch(1)
        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self.toggle_theme)
        tl.addWidget(self.theme_btn)
        outer.addWidget(top)

        # ---- body
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(240)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 14, 12, 14)
        sl.setSpacing(4)
        self.stack = QStackedWidget()
        self.check = CheckPage(ctx)
        self.tools = ToolsPage(ctx)
        self.hist = HistoryPage(ctx)
        self.rules = RulesPage(ctx)
        self.settings_page = SettingsPage(ctx)
        self.about = AboutPage()
        self.nav_btns: list[QPushButton] = []
        for i, (text, page) in enumerate(((tr("🔍  بررسی ویدیو"), self.check), (tr("🛠  ابزارهای یوتیوبر"), self.tools),
                                         (tr("🕘  تاریخچه"), self.hist), (tr("📜  قوانین"), self.rules), (tr("⚙  تنظیمات"), self.settings_page), (tr("💬  درباره سازنده"), self.about))):
            b = QPushButton(text)
            b.setProperty("nav", True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=i: self.go(n))
            sl.addWidget(b)
            self.nav_btns.append(b)
            self.stack.addWidget(page)
        sl.addStretch(1)
        self.ai_state = label("", muted=True)
        sl.addWidget(self.ai_state)
        body.addWidget(side)
        body.addWidget(self.stack, 1)

        self.check.reportReady.connect(self.on_report)
        self.hist.openReport.connect(self.open_saved)
        self.settings_page.changed.connect(self.update_ai_state)
        self.go(0)
        self.apply_theme()
        self.update_ai_state()

    def go(self, i: int):
        self.stack.setCurrentIndex(i)
        for n, b in enumerate(self.nav_btns):
            b.setProperty("active", n == i)
            repolish(b)

    def update_ai_state(self):
        ok, why = self.ctx.ai_ready()
        name = "Gemini" if self.ctx.settings["provider"] == "gemini" else "OpenAI-compatible"
        self.ai_state.setText(tr(f"● AI: {name} آماده") if ok else tr("○ AI تنظیم نشده (تنظیمات)"))

    def apply_theme(self):
        name = self.ctx.settings["theme"]
        QApplication.instance().setStyleSheet(qss(name, self.font_family))
        self.theme_btn.setText(tr("☀  حالت روشن") if name == "dark" else tr("🌙  حالت تیره"))
        self.check.set_theme(name)
        for b in self.nav_btns:
            repolish(b)

    def toggle_theme(self):
        s = self.ctx.settings
        s["theme"] = "light" if s["theme"] == "dark" else "dark"
        s.save()
        self.apply_theme()
        if self.check.report:
            self.check.render(self.check.report)

    def on_report(self, rep: dict):
        entry = {"path": rep["path"], "name": rep["name"], "report": {k: v for k, v in rep.items() if k != "fingerprints"},
                 "fingerprints": rep.get("fingerprints", [])}
        # frame lists are heavy; only Gemini references (small) are persisted
        r = entry["report"].get("ref")
        if r and r.get("provider") != "gemini":
            entry["report"]["ref"] = None
        self.ctx.history.add(entry)
        self.ctx.historyChanged.emit()

    def open_saved(self, rep: dict):
        self.go(0)
        self.check.show_saved(rep)
