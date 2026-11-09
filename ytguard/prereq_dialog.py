"""First-run dialog: offers to install prerequisites, then shows a live checklist with overall progress."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .i18n import DIR, tr
from .prereqs import STEPS, PrereqWorker, missing_required

ICON = {"wait": "○", "run": "⟳", "ok": "✔", "skip": "✔", "fail": "✖", "warn": "⚠"}
COLOR = {"wait": "#8a8a8a", "run": "#e53935", "ok": "#2e9e5b", "skip": "#2e9e5b", "fail": "#e53935", "warn": "#d98a00"}


class PrereqDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.worker = None
        self.setWindowTitle(tr("نصب پیش‌نیازها"))
        self.setLayoutDirection(DIR)
        self.setMinimumWidth(560)
        self.setModal(True)
        root = QVBoxLayout(self); root.setContentsMargins(22, 20, 22, 20); root.setSpacing(12)
        self.stack = QStackedWidget(); root.addWidget(self.stack)

        # --- page 1: message
        p1 = QWidget(); l1 = QVBoxLayout(p1); l1.setSpacing(12)
        t = QLabel(tr("پیش‌نیازهای برنامه")); t.setStyleSheet("font-size:20px;font-weight:700;")
        d = QLabel(tr("برای کار کامل برنامه چند مورد لازمه (مثل FFmpeg برای تحلیل ویدیو). با زدن «نصب»، موارد زیر به‌ترتیب دانلود و نصب می‌شن و پیشرفتشون رو می‌بینی."))
        d.setWordWrap(True)
        l1.addWidget(t); l1.addWidget(d)
        for _k, title, _w, _r in STEPS:
            l1.addWidget(QLabel("•  " + tr(title)))
        n = QLabel(tr("اگه توی ایران هستی و دانلود وصل نمی‌شه، اول VPN/Proxy رو روشن کن (یا آدرس پراکسی رو در تنظیمات بزن)."))
        n.setWordWrap(True); n.setStyleSheet("color:#8a8a8a;")
        l1.addWidget(n); l1.addStretch(1)
        b = QHBoxLayout()
        self.install_btn = QPushButton(tr("نصب")); self.install_btn.setProperty("primary", True)
        self.install_btn.clicked.connect(self.start)
        skip = QPushButton(tr("بعداً")); skip.clicked.connect(self.skip)
        b.addWidget(self.install_btn); b.addWidget(skip); b.addStretch(1)
        l1.addLayout(b)
        self.stack.addWidget(p1)

        # --- page 2: progress list
        p2 = QWidget(); l2 = QVBoxLayout(p2); l2.setSpacing(10)
        t2 = QLabel(tr("در حال نصب پیش‌نیازها…")); t2.setStyleSheet("font-size:20px;font-weight:700;")
        self.title2 = t2
        l2.addWidget(t2)
        self.rows = {}
        for key, title, _w, _r in STEPS:
            row = QFrame(); row.setProperty("card", True)
            rl = QHBoxLayout(row); rl.setContentsMargins(12, 8, 12, 8)
            ic = QLabel(ICON["wait"]); ic.setFixedWidth(26); ic.setStyleSheet(f"font-size:18px;color:{COLOR['wait']};")
            col = QVBoxLayout(); col.setSpacing(2)
            nm = QLabel(tr(title)); nm.setWordWrap(True)
            st = QLabel(""); st.setWordWrap(True); st.setStyleSheet("color:#8a8a8a;font-size:12px;")
            col.addWidget(nm); col.addWidget(st)
            pc = QLabel(""); pc.setFixedWidth(48); pc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rl.addWidget(ic); rl.addLayout(col, 1); rl.addWidget(pc)
            l2.addWidget(row)
            self.rows[key] = (ic, st, pc)
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setFormat("%p%"); self.bar.setMinimumHeight(24)
        l2.addWidget(self.bar)
        b2 = QHBoxLayout()
        self.retry_btn = QPushButton(tr("تلاش دوباره")); self.retry_btn.clicked.connect(self.start); self.retry_btn.hide()
        self.go_btn = QPushButton(tr("ورود به برنامه")); self.go_btn.setProperty("primary", True)
        self.go_btn.clicked.connect(self.accept); self.go_btn.setEnabled(False)
        b2.addWidget(self.go_btn); b2.addWidget(self.retry_btn); b2.addStretch(1)
        l2.addLayout(b2)
        self.stack.addWidget(p2)

    # ------------------------------------------------------------------
    def skip(self):
        self.ctx.settings["prereqs_skipped"] = True
        self.ctx.settings.save()
        self.reject()

    def start(self):
        self.stack.setCurrentIndex(1)
        self.retry_btn.hide(); self.go_btn.setEnabled(False)
        self.title2.setText(tr("در حال نصب پیش‌نیازها…"))
        self.bar.setValue(0)
        for ic, st, pc in self.rows.values():
            ic.setText(ICON["wait"]); ic.setStyleSheet(f"font-size:18px;color:{COLOR['wait']};"); st.setText(""); pc.setText("")
        self.worker = PrereqWorker(self.ctx.settings)
        self.worker.stepState.connect(self.on_state)
        self.worker.stepProgress.connect(lambda k, p: self.rows[k][2].setText(f"{p}%"))
        self.worker.overall.connect(self.bar.setValue)
        self.worker.allDone.connect(self.on_done)
        self.worker.start()

    def on_state(self, key, state, msg):
        ic, st, pc = self.rows[key]
        ic.setText(ICON[state]); ic.setStyleSheet(f"font-size:18px;color:{COLOR[state]};")
        st.setText(msg)
        if state in ("ok", "skip", "warn"):
            pc.setText("100%")
        if state == "fail":
            pc.setText("")

    def on_done(self, ok):
        s = self.ctx.settings
        if ok:
            s["prereqs_skipped"] = False; s.save()
            self.title2.setText(tr("همه‌چیز آماده است ✔"))
            self.bar.setValue(100)
        else:
            self.title2.setText(tr("بعضی موارد نصب نشد"))
            self.retry_btn.show()
        self.go_btn.setEnabled(True)
        if not ok:
            self.go_btn.setText(tr("ادامه بدون نصب"))

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            self.worker.cancel(); self.worker.wait(3000)
        super().closeEvent(e)

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel(); self.worker.wait(3000)
        super().reject()


def maybe_show_first_run(ctx, parent=None):
    """Show the dialog at startup if required prerequisites are missing and the user did not postpone it."""
    if ctx.settings["prereqs_skipped"]:
        return
    if missing_required(ctx.settings):
        PrereqDialog(ctx, parent).exec()
