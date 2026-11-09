from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea, QTabWidget, QTextEdit,
                             QVBoxLayout, QWidget)

from .i18n import DIR, IS_RTL, LANG, tr
from .context import AppContext
from .local_checks import VIDEO_EXTS, fmt_ts
from .prompts import TOOLS
from .widgets import Card, copy_to_clipboard, label
from .workers import InfoWorker, ThumbWorker, ToolWorker, VerticalWorker


class ToolsPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker = None
        self.setLayoutDirection(DIR)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        root.addWidget(label(tr("ابزارهای یوتیوبر"), h1=True))

        vrow = QHBoxLayout()
        self.vlabel = label(tr("هنوز ویدیویی انتخاب نشده. از «بررسی ویدیو» یکی بنداز یا از اینجا انتخاب کن."), muted=True)
        pick = QPushButton(tr("انتخاب ویدیو…"))
        pick.clicked.connect(self.pick)
        vrow.addWidget(self.vlabel, 1)
        vrow.addWidget(pick)
        root.addLayout(vrow)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)
        tabs.addTab(self._ai_tab(), tr("ابزارهای AI (متن‌ساز)"))
        tabs.addTab(self._local_tab(), tr("ابزارهای محلی (بدون AI)"))
        ctx.videoChanged.connect(self.on_video)
        if ctx.current_path:
            self.on_video(ctx.current_path)

    # ------------------------------------------------------------ AI tab
    def _ai_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setSpacing(14)
        self.tool_list = QListWidget()
        self.tool_list.setFixedWidth(240)
        for tid, (title, desc, _) in TOOLS.items():
            it = QListWidgetItem(title)
            it.setData(Qt.ItemDataRole.UserRole, tid)
            it.setToolTip(desc)
            self.tool_list.addItem(it)
        self.tool_list.setCurrentRow(0)
        self.tool_list.currentItemChanged.connect(self._tool_changed)
        right = QVBoxLayout()
        self.tool_desc = label("", muted=True)
        right.addWidget(self.tool_desc)
        row = QHBoxLayout()
        self.lang = QComboBox()
        for k, v in (("fa", tr("خروجی فارسی")), ("en", "English output"), ("ar", tr("العربية")), ("auto", tr("همزبان با خود ویدیو"))):
            self.lang.addItem(v, k)
        self.lang.setCurrentIndex(max(0, self.lang.findData(LANG)))
        self.extra = QLineEdit()
        self.extra.setPlaceholderText(tr("زمینه اضافه (اختیاری): مخاطب، لحن، کلمه کلیدی هدف…"))
        row.addWidget(self.lang)
        row.addWidget(self.extra, 1)
        right.addLayout(row)
        brow = QHBoxLayout()
        self.run_btn = QPushButton(tr("اجرا"))
        self.run_btn.setProperty("primary", True)
        self.run_btn.clicked.connect(self.run_tool)
        self.cancel_btn = QPushButton(tr("لغو"))
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        self.copy_btn = QPushButton(tr("کپی خروجی"))
        self.copy_btn.clicked.connect(lambda: copy_to_clipboard(self.out.toPlainText()))
        brow.addWidget(self.run_btn)
        brow.addWidget(self.cancel_btn)
        brow.addWidget(self.copy_btn)
        brow.addStretch(1)
        right.addLayout(brow)
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setVisible(False)
        self.status = label("", muted=True)
        right.addWidget(self.prog)
        right.addWidget(self.status)
        self.out = QTextEdit()
        self.out.setPlaceholderText(tr("خروجی اینجا نمایش داده می‌شه…"))
        right.addWidget(self.out, 1)
        lay.addWidget(self.tool_list)
        lay.addLayout(right, 1)
        self._tool_changed()
        return w

    def _tool_changed(self, *_):
        it = self.tool_list.currentItem()
        if it:
            self.tool_desc.setText(TOOLS[it.data(Qt.ItemDataRole.UserRole)][1])

    def run_tool(self):
        if not self.ctx.current_path:
            QMessageBox.information(self, tr("ویدیو"), tr("اول یک ویدیو انتخاب کن."))
            return
        ok, why = self.ctx.ai_ready()
        if not ok:
            QMessageBox.warning(self, tr("AI آماده نیست"), why + tr(". به تنظیمات برو."))
            return
        tid = self.tool_list.currentItem().data(Qt.ItemDataRole.UserRole)
        p = self.ctx.current_path
        self.run_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.prog.setVisible(True)
        self.prog.setValue(0)
        self.worker = ToolWorker(self.ctx.settings, p, tid, self.lang.currentData(), self.extra.text(), self.ctx.cached_ref(p))
        self.worker.progress.connect(lambda v, t: (self.prog.setValue(v), self.status.setText(t)))
        self.worker.done.connect(self._tool_done)
        self.worker.failed.connect(self._tool_failed)
        self.worker.start()

    def _tool_done(self, r):
        self._idle()
        self.ctx.refs[self.ctx.current_path] = r["ref"]
        self.out.setPlainText(r["text"])

    def _tool_failed(self, m):
        self._idle()
        self.status.setText(m)
        if m != tr("لغو شد."):
            QMessageBox.warning(self, tr("خطا"), m)

    def _idle(self):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.prog.setVisible(False)
        self.status.setText("")

    # ------------------------------------------------------------ local tab
    def _local_tab(self) -> QWidget:
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        w = QWidget()
        sc.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        t = Card(tr("استخراج بهترین فریم‌ها برای تامبنیل"))
        t.lay.addWidget(label(tr("فریم‌های تیز، خوش‌نور و رنگی رو انتخاب می‌کنه و به‌صورت JPG ذخیره می‌کنه (بدون AI)."), muted=True))
        r = QHBoxLayout()
        self.th_btn = QPushButton(tr("استخراج ۶ فریم"))
        self.th_btn.clicked.connect(self.run_thumbs)
        r.addWidget(self.th_btn)
        r.addStretch(1)
        t.lay.addLayout(r)
        self.th_grid = QGridLayout()
        t.lay.addLayout(self.th_grid)
        self.th_status = label("", muted=True)
        t.lay.addWidget(self.th_status)
        lay.addWidget(t)

        v = Card(tr("تبدیل افقی به ۹:۱۶ (Shorts / Reels)"))
        v.lay.addWidget(label(tr("خروجی 1080×1920. حالت «پس‌زمینه محو» کل تصویر رو نگه می‌داره؛ «برش مرکزی» پرکننده‌تره. می‌تونی بازه شروع/پایان رو هم بدی (۰ = کل ویدیو)."), muted=True))
        r = QHBoxLayout()
        self.v_mode = QComboBox()
        self.v_mode.addItem(tr("پس‌زمینه محو (blur)"), "blur")
        self.v_mode.addItem(tr("برش مرکزی (crop)"), "crop")
        self.v_start = QDoubleSpinBox(); self.v_start.setRange(0, 99999); self.v_start.setSuffix(tr(" s شروع"))
        self.v_end = QDoubleSpinBox(); self.v_end.setRange(0, 99999); self.v_end.setSuffix(tr(" s پایان"))
        self.v_btn = QPushButton(tr("تبدیل و ذخیره"))
        self.v_btn.setProperty("primary", True)
        self.v_btn.clicked.connect(self.run_vertical)
        for x in (self.v_mode, self.v_start, self.v_end, self.v_btn):
            r.addWidget(x)
        r.addStretch(1)
        v.lay.addLayout(r)
        self.v_prog = QProgressBar(); self.v_prog.setRange(0, 100); self.v_prog.setVisible(False)
        self.v_status = label("", muted=True)
        v.lay.addWidget(self.v_prog)
        v.lay.addWidget(self.v_status)
        lay.addWidget(v)
        lay.addStretch(1)
        return sc

    def _need_video(self) -> bool:
        if not self.ctx.current_path:
            QMessageBox.information(self, tr("ویدیو"), tr("اول یک ویدیو انتخاب کن."))
            return False
        return True

    def run_thumbs(self):
        if not self._need_video():
            return
        out_dir = str(Path(self.ctx.current_path).parent / "YTGuard_thumbnails")
        self.th_btn.setEnabled(False)
        self.th_status.setText(tr("در حال استخراج…"))
        self.tw = ThumbWorker(self.ctx.settings, self.ctx.current_path, out_dir)
        self.tw.done.connect(lambda r: self._thumbs_done(r, out_dir))
        self.tw.failed.connect(lambda m: (self.th_btn.setEnabled(True), self.th_status.setText(m)))
        self.tw.start()

    def _thumbs_done(self, res, out_dir):
        self.th_btn.setEnabled(True)
        while self.th_grid.count():
            it = self.th_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, (t, score, path) in enumerate(res):
            box = QVBoxLayout()
            pm = QLabel()
            pm.setPixmap(QPixmap(path).scaledToWidth(200, Qt.TransformationMode.SmoothTransformation))
            cap = label(tr(f"{fmt_ts(t)} · امتیاز {score:.2f}"), muted=True)
            host = QWidget(); host.setLayout(box)
            box.addWidget(pm); box.addWidget(cap)
            self.th_grid.addWidget(host, i // 3, i % 3)
        self.th_status.setText(tr(f"ذخیره شد در: {out_dir}"))

    def run_vertical(self):
        if not self._need_video():
            return
        src = Path(self.ctx.current_path)
        out, _ = QFileDialog.getSaveFileName(self, tr("ذخیره"), str(src.with_name(src.stem + "_9x16.mp4")), "MP4 (*.mp4)")
        if not out:
            return
        self.v_btn.setEnabled(False)
        self.v_prog.setVisible(True)
        self.vw = VerticalWorker(self.ctx.settings, str(src), out, self.v_start.value(), self.v_end.value(), self.v_mode.currentData())
        self.vw.progress.connect(lambda p, t: (self.v_prog.setValue(p), self.v_status.setText(t)))
        self.vw.done.connect(lambda p: (self.v_btn.setEnabled(True), self.v_prog.setVisible(False), self.v_status.setText(tr(f"ذخیره شد: {p}"))))
        self.vw.failed.connect(lambda m: (self.v_btn.setEnabled(True), self.v_prog.setVisible(False), self.v_status.setText(m)))
        self.vw.start()

    # ------------------------------------------------------------ video selection
    def pick(self):
        exts = " ".join(f"*{e}" for e in sorted(VIDEO_EXTS))
        p, _ = QFileDialog.getOpenFileName(self, tr("انتخاب ویدیو"), "", f"Video ({exts})")
        if not p:
            return
        w = InfoWorker(self.ctx.settings, p)
        w.done.connect(lambda r, p=p: self.ctx.set_video(p, r["info"]))
        w.failed.connect(lambda m: QMessageBox.warning(self, tr("خطا"), m))
        self._iw = w
        w.start()

    def on_video(self, path: str):
        i = self.ctx.current_info
        extra = f" — {fmt_ts(i['duration'])} · {i['width']}×{i['height']}" if i else ""
        self.vlabel.setText(tr(f"ویدیوی فعلی: {Path(path).name}{extra}"))
