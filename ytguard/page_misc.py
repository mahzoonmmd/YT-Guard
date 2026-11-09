"""History, Rules and Settings pages."""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from . import APP_NAME_FA, APP_VERSION, KNOWLEDGE_VERIFIED_ON
from .analysis import VERDICT_FA
from .context import AppContext
from .knowledge import CONFIDENCE_FA, RULES
from .local_checks import find_ffmpeg
from .widgets import Card, label
from .workers import ModelsWorker


class HistoryPage(QWidget):
    openReport = pyqtSignal(dict)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.addWidget(label("تاریخچه بررسی‌ها", h1=True))
        lay.addWidget(label("گزارش‌ها فقط روی همین کامپیوتر ذخیره می‌شن. اثر انگشت فریم‌ها برای تشخیص ویدیوهای تکراری/قالبی بین ویدیوهای خودت استفاده می‌شه.", muted=True))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda *_: self.open_sel())
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        b1 = QPushButton("باز کردن گزارش"); b1.setProperty("primary", True); b1.clicked.connect(self.open_sel)
        b2 = QPushButton("حذف"); b2.clicked.connect(self.del_sel)
        row.addWidget(b1); row.addWidget(b2); row.addStretch(1)
        lay.addLayout(row)
        ctx.historyChanged.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for h in self.ctx.history.items:
            r = h.get("report", {})
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(h.get("ts", 0)))
            icon = {"safe": "🟢", "caution": "🟠", "risky": "🔴"}.get(r.get("verdict"), "⚪")
            it = QListWidgetItem(f"{icon}  {h.get('name','')}   ·   {'Shorts' if r.get('format')=='short' else 'لانگ'}   ·   ریسک {r.get('score','?')}   ·   {when}")
            it.setData(Qt.ItemDataRole.UserRole, h["id"])
            self.list.addItem(it)

    def _sel(self):
        it = self.list.currentItem()
        if not it:
            return None
        return next((h for h in self.ctx.history.items if h["id"] == it.data(Qt.ItemDataRole.UserRole)), None)

    def open_sel(self):
        h = self._sel()
        if h and h.get("report"):
            self.openReport.emit(h["report"])

    def del_sel(self):
        h = self._sel()
        if h:
            self.ctx.history.remove(h["id"])
            self.refresh()


class RulesPage(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        root.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 18, 24, 24)
        lay.setSpacing(10)
        lay.addWidget(label("قوانینی که برنامه چک می‌کنه", h1=True))
        lay.addWidget(label(f"آخرین مرور منابع: {KNOWLEDGE_VERIFIED_ON}. قوانین یوتیوب مرتب عوض می‌شن؛ هر مورد با سطح اطمینان منبعش علامت خورده. "
                            "قبل از تصمیم مهم همیشه صفحه رسمی YouTube Help رو هم ببین.", muted=True))
        for rid, r in RULES.items():
            c = Card()
            top = QHBoxLayout()
            top.addWidget(label(r["title"], h2=True), 1)
            chip = QLabel(CONFIDENCE_FA[r["confidence"]]); chip.setProperty("chip", True)
            if r["confidence"] == "unverified":
                chip.setProperty("sev", "medium")
            top.addWidget(chip)
            imp = QLabel("اثر: " + r["impact"]); imp.setProperty("chip", True)
            top.addWidget(imp)
            c.lay.addLayout(top)
            c.lay.addWidget(label(r["summary"], selectable=True))
            c.lay.addWidget(label("راه‌حل: " + r["fix"], muted=True, selectable=True))
            src = QLabel(f'<a href="{r["source"]}" style="color:#FF0000">منبع</a>')
            src.setOpenExternalLinks(True)
            c.lay.addWidget(src)
            lay.addWidget(c)
        lay.addStretch(1)


class SettingsPage(QWidget):
    changed = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        s = ctx.settings
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        root.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 18, 24, 24)
        lay.setSpacing(12)
        lay.addWidget(label("تنظیمات", h1=True))

        # --- provider
        pc = Card("موتور AI")
        self.provider = QComboBox()
        self.provider.addItem("Google Gemini (پیشنهادی — ویدیو + صدا، API رایگان)", "gemini")
        self.provider.addItem("OpenAI-compatible (OpenRouter / Groq / محلی — فقط فریم‌ها)", "openai")
        self.provider.setCurrentIndex(0 if s["provider"] == "gemini" else 1)
        pc.lay.addWidget(self.provider)
        info = QLabel('<a href="https://aistudio.google.com/apikey" style="color:#FF0000">گرفتن کلید رایگان Gemini از Google AI Studio</a>')
        info.setOpenExternalLinks(True)
        pc.lay.addWidget(info)
        pc.lay.addWidget(label("نکته: در پلن رایگان، گوگل ممکنه از ورودی‌ها برای بهبود محصولاتش استفاده کنه؛ ویدیوی منتشرنشده/محرمانه رو با پلن رایگان نفرست. "
                               "سهمیه رایگان محدوده (چند درخواست در دقیقه و روز) و قابل تغییره؛ اگه خطای ۴۲۹ دیدی صبر کن.", muted=True))
        pc.lay.addWidget(label("⚠ اگه در ایران هستی: سرویس Gemini از IP ایران قابل دسترس نیست. VPN/Proxy لازمه. برای پراکسی بخش «شبکه» پایین رو پر کن.", muted=True))
        lay.addWidget(pc)

        gc = Card("Gemini")
        gf = QFormLayout(); gf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.g_key = QLineEdit(s["gemini_key"]); self.g_key.setEchoMode(QLineEdit.EchoMode.Password); self.g_key.setPlaceholderText("AIza…")
        self.g_model = QComboBox(); self.g_model.setEditable(True); self.g_model.addItems(["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"])
        self.g_model.setMaxVisibleItems(18)
        self.g_model.setMinimumHeight(40)
        self.g_model.setCurrentText(s["gemini_model"])
        self.g_models_btn = QPushButton("دریافت لیست مدل‌ها / تست اتصال")
        self.g_models_btn.clicked.connect(lambda: self.fetch_models("gemini"))
        gf.addRow(label("API Key", wrap=False), self.g_key)
        gf.addRow(label("مدل", wrap=False), self.g_model)
        gf.addRow("", self.g_models_btn)
        gc.lay.addLayout(gf)
        lay.addWidget(gc)

        oc = Card("OpenAI-compatible (اختیاری)")
        of = QFormLayout(); of.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_base = QLineEdit(s["openai_base"]); self.o_key = QLineEdit(s["openai_key"]); self.o_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.o_model = QComboBox(); self.o_model.setEditable(True); self.o_model.setCurrentText(s["openai_model"])
        self.o_models_btn = QPushButton("دریافت لیست مدل‌ها")
        self.o_models_btn.clicked.connect(lambda: self.fetch_models("openai"))
        of.addRow(label("Base URL", wrap=False), self.o_base)
        of.addRow(label("API Key", wrap=False), self.o_key)
        of.addRow(label("مدل (باید تصویر بفهمه)", wrap=False), self.o_model)
        of.addRow("", self.o_models_btn)
        oc.lay.addLayout(of)
        lay.addWidget(oc)

        nc = Card("شبکه و پردازش")
        nf = QFormLayout(); nf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.proxy = QLineEdit(s["proxy"]); self.proxy.setPlaceholderText("http://127.0.0.1:10809  یا  socks5h://127.0.0.1:10808")
        self.compress = QCheckBox("کم‌حجم‌سازی ویدیو قبل از ارسال (سریع‌تر و کم‌مصرف‌تر؛ تحلیل AI چیزی از دست نمی‌ده)")
        self.compress.setChecked(bool(s["compress_before_upload"]))
        self.comp_h = QSpinBox(); self.comp_h.setRange(240, 1080); self.comp_h.setSingleStep(120); self.comp_h.setValue(int(s["compress_height"]))
        self.frames = QSpinBox(); self.frames.setRange(4, 40); self.frames.setValue(int(s["frames_for_openai"]))
        self.ff = QLineEdit(s["ffmpeg_path"]); self.ff.setPlaceholderText("خالی = خودکار")
        ffb = QPushButton("انتخاب…"); ffb.clicked.connect(self.pick_ffmpeg)
        ffrow = QHBoxLayout(); ffrow.addWidget(self.ff, 1); ffrow.addWidget(ffb)
        self.ff_status = label("", muted=True)
        nf.addRow(label("Proxy", wrap=False), self.proxy)
        nf.addRow("", self.compress)
        nf.addRow(label("ارتفاع نسخه ارسالی", wrap=False), self.comp_h)
        nf.addRow(label("تعداد فریم (OpenAI)", wrap=False), self.frames)
        nf.addRow(label("مسیر ffmpeg", wrap=False), ffrow)
        nf.addRow("", self.ff_status)
        nc.lay.addLayout(nf)
        lay.addWidget(nc)

        row = QHBoxLayout()
        save = QPushButton("ذخیره تنظیمات"); save.setProperty("primary", True); save.clicked.connect(self.save)
        row.addWidget(save); row.addStretch(1)
        lay.addLayout(row)
        self.msg = label("", muted=True)
        lay.addWidget(self.msg)
        lay.addWidget(label(f"{APP_NAME_FA} نسخه {APP_VERSION}", muted=True))
        lay.addStretch(1)
        self.update_ff_status()

    def update_ff_status(self):
        p = find_ffmpeg(self.ff.text().strip())
        self.ff_status.setText(f"✔ ffmpeg پیدا شد: {p}" if p else "✖ ffmpeg پیدا نشد؛ دستور `pip install imageio-ffmpeg` رو اجرا کن یا مسیر رو بده.")

    def pick_ffmpeg(self):
        p, _ = QFileDialog.getOpenFileName(self, "ffmpeg", "", "ffmpeg (ffmpeg*);;All (*)")
        if p:
            self.ff.setText(p)
            self.update_ff_status()

    def save(self):
        s = self.ctx.settings
        s["provider"] = self.provider.currentData()
        s["gemini_key"] = self.g_key.text().strip()
        s["gemini_model"] = self.g_model.currentText().strip() or "gemini-3.5-flash"
        s["openai_base"] = self.o_base.text().strip()
        s["openai_key"] = self.o_key.text().strip()
        s["openai_model"] = self.o_model.currentText().strip()
        s["proxy"] = self.proxy.text().strip()
        s["compress_before_upload"] = self.compress.isChecked()
        s["compress_height"] = self.comp_h.value()
        s["frames_for_openai"] = self.frames.value()
        s["ffmpeg_path"] = self.ff.text().strip()
        s.save()
        self.update_ff_status()
        self.msg.setText("ذخیره شد ✔")
        self.changed.emit()

    def fetch_models(self, which):
        self.save()
        self.msg.setText("در حال اتصال…")
        self.mw = ModelsWorker(self.ctx.settings, which)

        def ok(models):
            combo = self.g_model if which == "gemini" else self.o_model
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(models)
            if cur not in models and which == "gemini":
                cands = [m for m in models if "flash" in m and not any(x in m for x in ("lite", "image", "tts", "live", "audio", "exp", "robotics", "embed"))]
                cur = sorted(cands)[-1] if cands else (models[0] if models else cur)
            combo.setCurrentText(cur)
            combo.blockSignals(False)
            self.save()
            self.msg.setText(f"اتصال موفق ✔ — {len(models)} مدل پیدا شد. از لیست کشویی (فلش کنار مدل) مدل دلخواه رو انتخاب کن؛ مدل فعلی: {cur}")
            combo.showPopup()

        self.mw.done.connect(ok)
        self.mw.failed.connect(lambda m: self.msg.setText("✖ " + m))
        self.mw.start()


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        from . import CREATOR_NAME, CREATOR_NAME_FA, GITHUB_PROFILE_URL, GITHUB_REPO_URL
        from .widgets import LogoBadge
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 24)
        root.setSpacing(14)
        root.addWidget(label("درباره سازنده", h1=True))
        card = Card()
        head = QHBoxLayout()
        head.addWidget(LogoBadge(64))
        col = QVBoxLayout()
        col.addWidget(label(f"{APP_NAME_FA} — YT Guard", h2=True))
        col.addWidget(label(f"نسخه {APP_VERSION}", muted=True))
        head.addLayout(col, 1)
        card.lay.addLayout(head)
        card.lay.addWidget(label(f"ساخته‌شده توسط {CREATOR_NAME_FA} ({CREATOR_NAME})", h2=True))
        card.lay.addWidget(label("این برنامه رایگان و متن‌بازه و برای کمک به یوتیوبرها ساخته شده تا قبل از آپلود، مشکلات کپی‌رایت، افشای AI، "
                                 "محتوای غیراصیل و ریزش مخاطب ویدیوشون رو پیدا کنن."))
        root.addWidget(card)
        sup = Card("حمایت از پروژه")
        sup.lay.addWidget(label("اگه برنامه به دردت خورد، با یک Star روی پروژه و یک Follow توی گیت‌هاب ازش حمایت کن. "
                                "هر Star انگیزه‌ی ادامه‌ی توسعه و اضافه شدن ابزارهای جدید رو بیشتر می‌کنه ⭐"))
        row = QHBoxLayout()

        def open_url(u):
            if u:
                QDesktopServices.openUrl(QUrl(u))

        b1 = QPushButton("⭐  Star در گیت‌هاب")
        b1.setProperty("primary", True)
        b1.clicked.connect(lambda: open_url(GITHUB_REPO_URL or GITHUB_PROFILE_URL))
        b2 = QPushButton("👤  Follow در گیت‌هاب")
        b2.clicked.connect(lambda: open_url(GITHUB_PROFILE_URL))
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        sup.lay.addLayout(row)
        url = GITHUB_REPO_URL or GITHUB_PROFILE_URL
        if url:
            lk = QLabel(f'<a href="{url}" style="color:#FF0000">{url}</a>')
            lk.setOpenExternalLinks(True)
            sup.lay.addWidget(lk)
        else:
            b1.setEnabled(False)
            b2.setEnabled(False)
            sup.lay.addWidget(label("(آدرس گیت‌هاب هنوز در فایل ytguard/__init__.py تنظیم نشده)", muted=True))
        root.addWidget(sup)
        root.addWidget(label("نظر و پیشنهاد؟ از طریق Issues پروژه در گیت‌هاب بنویس.", muted=True))
        root.addStretch(1)
