"""Pages: 'why no views?' (reach doctor), idea check, channel review."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox, QTabWidget,
                             QVBoxLayout, QWidget)

from .context import AppContext
from .i18n import DIR, tr
from .knowledge import NICHES
from .local_checks import VIDEO_EXTS, fmt_ts
from .pro_widgets import S, as_list, build_cards, effort, impact, pairs, policy_items, to_markdown
from .widgets import Card, copy_to_clipboard, label
from .workers import InfoWorker
from .workers_pro import ChannelWorker, DiagnoseWorker, IdeaWorker

FMT_ITEMS = [("long", tr("ویدیوی لانگ")), ("short", "Shorts")]


def combo(items, data_first=True) -> QComboBox:
    c = QComboBox(); c.setLayoutDirection(DIR)
    for k, t in items:
        c.addItem(t, k)
    return c


def edit(placeholder="", h=70) -> QPlainTextEdit:
    e = QPlainTextEdit(); e.setPlaceholderText(placeholder); e.setFixedHeight(h)
    return e


def num_spin(maximum=1e12, dec=0, suffix="") -> QDoubleSpinBox:
    s = QDoubleSpinBox(); s.setRange(0, maximum); s.setDecimals(dec); s.setSpecialValueText(" ")
    s.setGroupSeparatorShown(True)
    if suffix:
        s.setSuffix(suffix)
    return s


class ProPage(QWidget):
    """Scrollable page: form on top, progress, result cards below."""
    TITLE = ""
    SUBTITLE = ""

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker = None
        self.sections: list[dict] = []
        self.setLayoutDirection(DIR)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); root.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        self.lay = QVBoxLayout(body); self.lay.setContentsMargins(24, 18, 24, 24); self.lay.setSpacing(12)
        self.lay.addWidget(label(self.TITLE, h1=True))
        self.lay.addWidget(label(self.SUBTITLE, muted=True))
        self.build_form()
        row = QHBoxLayout()
        self.run_btn = QPushButton(self.RUN_TEXT); self.run_btn.setProperty("primary", True); self.run_btn.clicked.connect(self.start)
        self.cancel_btn = QPushButton(tr("لغو")); self.cancel_btn.setVisible(False); self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        self.copy_btn = QPushButton(tr("کپی گزارش")); self.copy_btn.setEnabled(False); self.copy_btn.clicked.connect(lambda: copy_to_clipboard(self.markdown()))
        self.save_btn = QPushButton(tr("ذخیره (Markdown)")); self.save_btn.setEnabled(False); self.save_btn.clicked.connect(self.save_md)
        for b in (self.run_btn, self.cancel_btn, self.copy_btn, self.save_btn):
            row.addWidget(b)
        row.addStretch(1)
        self.lay.addLayout(row)
        self.prog = QProgressBar(); self.prog.setRange(0, 100); self.prog.setVisible(False)
        self.status = label("", muted=True)
        self.lay.addWidget(self.prog); self.lay.addWidget(self.status)
        self.result_host = QWidget(); self.result_lay = QVBoxLayout(self.result_host); self.result_lay.setContentsMargins(0, 0, 0, 0)
        self.lay.addWidget(self.result_host)
        self.lay.addStretch(1)

    # --- to implement
    def build_form(self): ...
    def make_worker(self): ...   # returns worker or None (after showing a message)
    def to_sections(self, res) -> list[dict]: ...

    def need_ai(self) -> bool:
        ok, why = self.ctx.ai_ready()
        if not ok:
            QMessageBox.warning(self, tr("AI آماده نیست"), why + tr(". به تنظیمات برو."))
        return ok

    def start(self):
        if not self.need_ai():
            return
        w = self.make_worker()
        if not w:
            return
        self.worker = w
        self.run_btn.setEnabled(False); self.cancel_btn.setVisible(True); self.prog.setVisible(True); self.prog.setValue(0)
        w.progress.connect(lambda v, t: (self.prog.setValue(v), self.status.setText(t)))
        w.done.connect(self._done)
        w.failed.connect(self._failed)
        w.start()

    def _idle(self):
        self.run_btn.setEnabled(True); self.cancel_btn.setVisible(False); self.prog.setVisible(False); self.status.setText("")

    def _failed(self, m):
        self._idle()
        self.status.setText(m)
        if m != tr("لغو شد."):
            QMessageBox.warning(self, tr("خطا"), m)

    def _done(self, res):
        self._idle()
        self.on_result(res)
        try:
            self.sections = self.to_sections(res)
        except Exception as e:  # malformed AI JSON must not crash the UI
            self.status.setText(tr("ساختار پاسخ AI غیرمنتظره بود؛ دوباره امتحان کن.") + f" ({type(e).__name__})")
            return
        build_cards(self.sections, self.result_lay)
        self.copy_btn.setEnabled(True); self.save_btn.setEnabled(True)

    def on_result(self, res): ...

    def markdown(self) -> str:
        return to_markdown(self.TITLE, self.sections)

    def save_md(self):
        p, _ = QFileDialog.getSaveFileName(self, tr("ذخیره گزارش"), "report.md", "Markdown (*.md)")
        if p:
            Path(p).write_text(self.markdown(), encoding="utf-8")


# ======================================================================================= reach doctor
SYMPTOMS = [
    ("low_impressions", tr("نمایش (Impressions) خیلی کمه")),
    ("low_ctr", tr("کلیک کم (CTR پایین)")),
    ("early_dropoff", tr("بینندگان زود می‌رن")),
    ("stalled", tr("اول ویو گرفت بعد متوقف شد")),
    ("swiped", tr("در Shorts بیشتر رد می‌شن (swiped away)")),
    ("no_search", tr("از جستجو ترافیک نمیاد")),
    ("limited_ads", tr("آیکون زرد / Limited ads")),
    ("sudden_drop", tr("ویو ناگهانی افت کرد")),
]


class ReachPage(ProPage):
    TITLE = tr("چرا ویو نمی‌گیره؟")
    SUBTITLE = tr("تشخیص علت ویو نگرفتن: تیتر، تامبنیل، هوک، توضیحات و قوانین. هرچی بیشتر بدی، دقیق‌تر می‌شه؛ ویدیو اختیاریه.")
    RUN_TEXT = tr("تشخیص بده")

    def build_form(self):
        self.thumb_path = ""
        c = Card(tr("ویدیو و بسته‌بندی"))
        vr = QHBoxLayout()
        self.vlabel = label(tr("ویدیو انتخاب نشده (اختیاری)"), muted=True)
        pick = QPushButton(tr("انتخاب ویدیو…")); pick.clicked.connect(self.pick_video)
        clr = QPushButton(tr("حذف")); clr.clicked.connect(lambda: self.set_video("", None))
        vr.addWidget(self.vlabel, 1); vr.addWidget(pick); vr.addWidget(clr)
        c.lay.addLayout(vr)
        self.use_video = QCheckBox(tr("ویدیو هم برای هوک و ریتم تحلیل بشه (آپلود می‌شه؛ ویدیوی قبلاً چک‌شده دوباره آپلود نمی‌شه)"))
        self.use_video.setChecked(True)
        c.lay.addWidget(self.use_video)
        f = QFormLayout(); f.setLabelAlignment(Qt.AlignmentFlag.AlignLeading)
        self.title = QLineEdit(); self.title.setPlaceholderText(tr("تیتر ویدیو"))
        self.candidates = edit(tr("تیترهای کاندید برای مقایسه (هر خط یکی، اختیاری)"), 70)
        self.desc = edit(tr("توضیحات ویدیو (Description)"), 90)
        self.tags = QLineEdit(); self.tags.setPlaceholderText(tr("تگ‌ها (اختیاری)"))
        tr_row = QHBoxLayout()
        self.th_prev = QLabel(); self.th_prev.setFixedSize(160, 90); self.th_prev.setStyleSheet("border:1px dashed #888;")
        self.th_prev.setAlignment(Qt.AlignmentFlag.AlignCenter); self.th_prev.setText(tr("بدون تامبنیل"))
        tb = QPushButton(tr("انتخاب تامبنیل…")); tb.clicked.connect(self.pick_thumb)
        tc = QPushButton(tr("حذف")); tc.clicked.connect(lambda: self.set_thumb(""))
        col = QVBoxLayout(); col.addWidget(tb); col.addWidget(tc); col.addStretch(1)
        tr_row.addWidget(self.th_prev); tr_row.addLayout(col); tr_row.addStretch(1)
        self.fmt = combo(FMT_ITEMS); self.niche = combo(NICHES)
        self.audience = QLineEdit(); self.audience.setPlaceholderText(tr("مخاطب هدف و زبان (مثلاً: فارسی‌زبان‌های علاقه‌مند به تدوین)"))
        for lab, w in ((tr("تیتر"), self.title), (tr("کاندیدها"), self.candidates), (tr("توضیحات"), self.desc), (tr("تگ"), self.tags),
                       (tr("تامبنیل"), None), (tr("فرمت"), self.fmt), (tr("موضوع"), self.niche), (tr("مخاطب"), self.audience)):
            if w is None:
                f.addRow(label(lab, wrap=False), tr_row)
            else:
                f.addRow(label(lab, wrap=False), w)
        c.lay.addLayout(f)
        self.lay.addWidget(c)

        sc = Card(tr("علائمی که می‌بینی (اختیاری، ولی خیلی کمک می‌کنه)"))
        g = QGridLayout()
        self.sym = {}
        for i, (k, t) in enumerate(SYMPTOMS):
            cb = QCheckBox(t); self.sym[k] = cb; g.addWidget(cb, i // 2, i % 2)
        sc.lay.addLayout(g)
        self.lay.addWidget(sc)

        mc = Card(tr("اعداد YouTube Studio (اختیاری؛ ۰ یا خالی = وارد نشده)"))
        mf = QFormLayout(); mf.setLabelAlignment(Qt.AlignmentFlag.AlignLeading)
        self.m_views = num_spin(); self.m_days = num_spin(5000); self.m_ctr = num_spin(100, 1, " %"); self.m_avp = num_spin(100, 1, " %"); self.m_swipe = num_spin(100, 1, " %")
        for lab, w in ((tr("ویو تا الان"), self.m_views), (tr("چند روز از انتشار گذشته"), self.m_days), (tr("CTR نمایش (Impressions CTR)"), self.m_ctr),
                       (tr("میانگین درصد دیده‌شده"), self.m_avp), (tr("Shorts: Viewed vs swiped away"), self.m_swipe)):
            mf.addRow(label(lab, wrap=False), w)
        mc.lay.addLayout(mf)
        self.lay.addWidget(mc)
        self.ctx.videoChanged.connect(lambda p: self.set_video(p, self.ctx.current_info, quiet=True))
        if self.ctx.current_path:
            self.set_video(self.ctx.current_path, self.ctx.current_info, quiet=True)

    # --- inputs
    def set_video(self, path, info, quiet=False):
        self.video = path or ""
        if path:
            extra = f" — {fmt_ts(info['duration'])}" if info else ""
            self.vlabel.setText(tr(f"ویدیو: {Path(path).name}{extra}"))
            if info and info.get("height") and info.get("width"):
                self.fmt.setCurrentIndex(1 if (info["height"] > info["width"] and info["duration"] <= 180) else 0)
        else:
            self.vlabel.setText(tr("ویدیو انتخاب نشده (اختیاری)"))

    def pick_video(self):
        exts = " ".join(f"*{e}" for e in sorted(VIDEO_EXTS))
        p, _ = QFileDialog.getOpenFileName(self, tr("انتخاب ویدیو"), "", f"Video ({exts})")
        if p:
            w = InfoWorker(self.ctx.settings, p)
            w.done.connect(lambda r, p=p: (self.ctx.set_video(p, r["info"])))
            w.failed.connect(lambda m: QMessageBox.warning(self, tr("خطا"), m))
            self._iw = w; w.start()

    def pick_thumb(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("انتخاب تامبنیل"), "", "Images (*.jpg *.jpeg *.png *.webp *.bmp)")
        if p:
            self.set_thumb(p)

    def set_thumb(self, p):
        self.thumb_path = p
        if p:
            self.th_prev.setPixmap(QPixmap(p).scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.th_prev.setPixmap(QPixmap()); self.th_prev.setText(tr("بدون تامبنیل"))

    def make_worker(self):
        video = getattr(self, "video", "")
        title, thumb, desc = self.title.text().strip(), self.thumb_path, self.desc.toPlainText().strip()
        use_video = bool(video) and self.use_video.isChecked()
        if not (title or thumb or desc or use_video):
            QMessageBox.information(self, tr("ورودی"), tr("حداقل یکی از این‌ها رو بده: تیتر، تامبنیل، توضیحات یا ویدیو."))
            return None
        metrics = {}
        for k, w in (("views", self.m_views), ("days_online", self.m_days), ("ctr_pct", self.m_ctr), ("avg_viewed_pct", self.m_avp), ("viewed_vs_swiped_pct", self.m_swipe)):
            if w.value() > 0:
                metrics[k] = w.value() if w.decimals() else int(w.value())
        data = {"format": self.fmt.currentData(), "niche": self.niche.currentText(), "audience": self.audience.text().strip(),
                "title": title, "description": desc, "tags": self.tags.text().strip(),
                "candidates": [x.strip() for x in self.candidates.toPlainText().splitlines() if x.strip()],
                "symptoms": [t for k, t in SYMPTOMS if self.sym[k].isChecked()], "metrics": metrics}
        vr = None
        if use_video:
            h = self.ctx.history.find_by_path(video)
            rep = (h or {}).get("report")
            if rep:
                ai = rep.get("ai") or {}
                vr = {"score": rep.get("score"), "verdict": rep.get("verdict"), "summary": ai.get("summary"),
                      "hook_score": (ai.get("retention") or {}).get("hook_score"), "metrics": rep.get("metrics"),
                      "issues": [f.get("issue") for f in rep.get("findings", [])][:8]}
        return DiagnoseWorker(self.ctx.settings, data, video if use_video else None, thumb or None, self.ctx.cached_ref(video) if use_video else None, vr)

    def on_result(self, res):
        if res.get("ref") and getattr(self, "video", ""):
            self.ctx.refs[self.video] = res["ref"]

    def to_sections(self, res):
        a, secs = res["ai"], []
        S(secs, tr("خلاصه"), "text", a.get("headline"))
        S(secs, tr("امتیاز آمادگی برای ویو"), "scores", [(tr("امتیاز کلی"), a.get("reach_score"), True)])
        funnel = as_list(a.get("funnel"))
        FN = {"impressions": tr("نمایش"), "ctr": tr("کلیک (تیتر+تامبنیل)"), "retention": tr("ماندگاری (هوک و ریتم)"),
              "discovery": tr("کشف‌شدن (کلیدواژه/متادیتا)"), "audience_fit": tr("تناسب با مخاطب"), "policy": tr("قوانین و تبلیغات")}
        S(secs, tr("قیف ویو: کدوم مرحله می‌شکنه؟"), "scores", [(FN.get(f.get("stage"), f.get("stage", "")), f.get("score"), True) for f in funnel if isinstance(f, dict)])
        for f in funnel:
            if isinstance(f, dict) and f.get("issues"):
                S(secs, FN.get(f.get("stage"), f.get("stage", "")) + (f" — {f['verdict']}" if f.get("verdict") else ""), "items",
                  [{"title": i.get("issue", ""), "body": i.get("evidence", ""), "fix": i.get("fix", ""), "chip": impact(i.get("impact"))} for i in as_list(f["issues"]) if isinstance(i, dict)])
        S(secs, tr("اولویت‌های اصلاح (از مهم‌ترین)"), "items", [{"title": p.get("action", ""), "body": p.get("why", ""), "chip": effort(p.get("effort"))} for p in as_list(a.get("top_priorities")) if isinstance(p, dict)])
        t = a.get("title") or {}
        S(secs, tr("تیتر"), "scores", [(tr("امتیاز تیتر"), t.get("score"), True)])
        S(secs, tr("نقد تیتر"), "text", t.get("critique"))
        S(secs, tr("جایگزین‌های پیشنهادی تیتر"), "items", pairs(t.get("rewrites"), "title", "why"))
        S(secs, tr("رتبه‌بندی تیترهای کاندید"), "items", [{"title": f"{c.get('score', '')}/100 — {c.get('title', '')}", "body": c.get("comment", "")} for c in as_list(t.get("ranking_of_candidates")) if isinstance(c, dict)])
        th = a.get("thumbnail") or {}
        S(secs, tr("تامبنیل"), "scores", [(tr("امتیاز تامبنیل"), th.get("score"), True)])
        S(secs, tr("نقد تامبنیل"), "text", th.get("critique"))
        S(secs, tr("اصلاح تامبنیل"), "bullets", th.get("fixes"), "warn")
        S(secs, tr("ایده‌های تامبنیل"), "bullets", th.get("concepts"))
        tm = (res.get("thumb") or {})
        S(secs, tr("اندازه‌گیری محلی تامبنیل (بدون AI)"), "bullets", [f["text"] for f in tm.get("findings", [])], "warn")
        h = a.get("hook") or {}
        S(secs, tr("هوک"), "scores", [(tr("امتیاز هوک"), h.get("score"), True)])
        S(secs, tr("نقد هوک"), "text", h.get("critique"))
        S(secs, tr("هوک پیشنهادی"), "text", h.get("rewrite"))
        d = a.get("description") or {}
        S(secs, tr("توضیحات (Description)"), "scores", [(tr("امتیاز توضیحات"), d.get("score"), True)])
        S(secs, tr("نقد توضیحات"), "text", d.get("critique"))
        S(secs, tr("توضیحات بازنویسی‌شده"), "text", d.get("rewrite"))
        S(secs, tr("کلیدواژه‌های پیشنهادی"), "bullets", a.get("keywords"))
        S(secs, tr("قوانین / محدودیت تبلیغات"), "items", policy_items(a.get("policy_limits")))
        S(secs, tr("نکات مثبت"), "bullets", a.get("positives"), "ok")
        S(secs, tr("بررسی‌های عددی خودکار"), "bullets", res.get("pre"))
        return secs


# ======================================================================================= idea check
class IdeaPage(ProPage):
    TITLE = tr("بررسی ایده")
    SUBTITLE = tr("قبل از ساخت ویدیو: شانس ویو، شانس مانیتایز، ریسک قوانین، نقاط مثبت/منفی و نسخه بهتر ایده.")
    RUN_TEXT = tr("ایده رو بررسی کن")

    def build_form(self):
        c = Card(tr("ایده‌ات"))
        self.idea = edit(tr("ایده رو تا جای ممکن دقیق بنویس: موضوع، زاویه، چه چیزی نشون داده می‌شه، چطور ساخته می‌شه…"), 130)
        c.lay.addWidget(self.idea)
        f = QFormLayout(); f.setLabelAlignment(Qt.AlignmentFlag.AlignLeading)
        self.title = QLineEdit(); self.title.setPlaceholderText(tr("تیتر ذهنی (اختیاری)"))
        self.fmt = combo(FMT_ITEMS); self.niche = combo(NICHES)
        self.audience = QLineEdit(); self.audience.setPlaceholderText(tr("مخاطب و زبان (مثلاً: فارسی‌زبان‌ها، ۱۸ تا ۳۰ سال)"))
        self.ai_use = combo([("none", tr("بدون AI")), ("assist", tr("AI فقط کمک (ایده/اسکریپت/ادیت)")),
                             ("voice", tr("صدای AI")), ("visuals", tr("تصویر/ویدیوی AI")), ("mostly", tr("تقریباً همه‌چیز با AI"))])
        self.stage = combo([("new", tr("کانال جدید / صفر")), ("small", tr("کمتر از ۱٬۰۰۰ سابسکرایبر")), ("mid", tr("۱٬۰۰۰ تا ۱۰٬۰۰۰")), ("large", tr("بیشتر از ۱۰٬۰۰۰"))])
        self.sources = QLineEdit(); self.sources.setPlaceholderText(tr("منبع تصویر/موزیک (فیلم خودم، آرشیو، کلیپ دیگران، موزیک لایسنس‌دار…)"))
        for lab, w in ((tr("تیتر"), self.title), (tr("فرمت"), self.fmt), (tr("موضوع"), self.niche), (tr("مخاطب"), self.audience),
                       (tr("استفاده از AI"), self.ai_use), (tr("اندازه کانال"), self.stage), (tr("منابع"), self.sources)):
            f.addRow(label(lab, wrap=False), w)
        c.lay.addLayout(f)
        self.lay.addWidget(c)
        self.lay.addWidget(label(tr("توجه: AI به داده زنده یوتیوب (ترند، حجم جستجو، رقبا) دسترسی نداره؛ تخمین‌های تقاضا استدلالی‌ان، نه آمار. قبل از ساخت، راه‌های «تست ارزان» پایین گزارش رو انجام بده."), muted=True))

    def make_worker(self):
        idea = self.idea.toPlainText().strip()
        if len(idea) < 15:
            QMessageBox.information(self, tr("ایده"), tr("ایده رو کمی کامل‌تر بنویس (حداقل چند جمله)."))
            return None
        d = {"idea": idea, "format": self.fmt.currentData(), "niche": self.niche.currentText(), "audience": self.audience.text().strip(),
             "ai_use": self.ai_use.currentText(), "stage": self.stage.currentText(), "sources": self.sources.text().strip(), "title": self.title.text().strip()}
        return IdeaWorker(self.ctx.settings, d)

    def to_sections(self, a):
        secs = []
        VD = {"go": tr("✔ بساز"), "adjust": tr("◐ با اصلاح بساز"), "risky": tr("✖ پرریسک")}
        S(secs, tr("نتیجه") + " — " + VD.get(str(a.get("verdict")), ""), "text", "\n".join(x for x in (a.get("headline"), a.get("summary")) if x))
        sc = a.get("scores") or {}
        S(secs, tr("امتیازها"), "scores", [(tr("پتانسیل ویو"), sc.get("view_potential"), True), (tr("پتانسیل مانیتایز"), sc.get("monetization_potential"), True),
                                          (tr("امنیت در برابر قوانین"), sc.get("policy_safety"), True), (tr("اصالت (Originality)"), sc.get("originality"), True),
                                          (tr("سختی رقابت"), sc.get("competition_difficulty"), False)])
        S(secs, tr("نقاط مثبت"), "bullets", a.get("positives"), "ok")
        S(secs, tr("نقاط منفی"), "bullets", a.get("negatives"), "bad")
        S(secs, tr("ریسک‌های قوانین یوتیوب"), "items", policy_items(a.get("policy_flags")))
        m = a.get("monetization") or {}
        MS = {"good": tr("خوب"), "conditional": tr("مشروط"), "poor": tr("ضعیف")}
        S(secs, tr("مانیتایز") + (f" — {MS.get(str(m.get('status')), m.get('status'))}" if m.get("status") else ""), "bullets", m.get("notes"), "warn")
        S(secs, tr("مخاطب و تقاضا (تخمین)"), "text", a.get("audience_and_demand"))
        S(secs, tr("زاویه‌های بهتر برای ایده"), "items", pairs(a.get("improved_angles"), "angle", "why"))
        S(secs, tr("پیشنهاد تیتر"), "items", pairs(a.get("title_options"), "title", "why"))
        S(secs, tr("ایده تامبنیل"), "bullets", a.get("thumbnail_ideas"))
        S(secs, tr("ایده هوک (۵ ثانیه اول)"), "bullets", a.get("hook_ideas"))
        S(secs, tr("فرمت و طول پیشنهادی"), "text", a.get("format_advice"))
        S(secs, tr("چک‌لیست تولید (برای مانیتایز ماندن)"), "bullets", a.get("production_checklist"), "ok")
        S(secs, tr("قبل از ساخت اینها رو تست کن"), "bullets", a.get("validate_before_making"))
        return secs


# ======================================================================================= channel review
class ChannelPage(ProPage):
    TITLE = tr("بررسی کانال")
    SUBTITLE = tr("تحلیل عملکرد تیتر، تامبنیل و ویدیوهای کانال، وضعیت مانیتایز و برنامه بهبود. با کلید YouTube Data API (رایگان) یا لیست دستی.")
    RUN_TEXT = tr("کانال رو تحلیل کن")

    def build_form(self):
        tabs = QTabWidget()
        # api tab
        a = QWidget(); al = QVBoxLayout(a)
        self.ref = QLineEdit(); self.ref.setPlaceholderText("https://youtube.com/@handle  |  @handle  |  UC…")
        al.addWidget(label(tr("آدرس یا @handle کانال (هر کانال عمومی، حتی کانال خودت)"), muted=True)); al.addWidget(self.ref)
        self.limit = QSpinBox(); self.limit.setRange(10, 200); self.limit.setValue(50); self.limit.setSuffix(tr(" ویدیوی اخیر"))
        al.addWidget(self.limit)
        al.addWidget(label(tr("نیاز به کلید YouTube Data API v3 داره (تنظیمات → YouTube API). رایگانه و هر تحلیل حدود ۵ واحد از ۱۰٬۰۰۰ واحد سهمیه روزانه مصرف می‌کنه."), muted=True))
        # manual tab
        m = QWidget(); ml = QVBoxLayout(m)
        ml.addWidget(label(tr("بدون کلید API: هر خط یک ویدیو، به شکل  عنوان | ویو | مدت (ثانیه) | چند روز پیش  (دو ستون آخر اختیاری)"), muted=True))
        self.manual = edit("How to edit? | 12500 | 600 | 30\nPremiere intro | 800 | 45 | 12", 140)
        ml.addWidget(self.manual)
        self.m_name = QLineEdit(); self.m_name.setPlaceholderText(tr("نام کانال (اختیاری)"))
        self.m_subs = num_spin(); self.m_subs.setPrefix(tr("سابسکرایبر: ")) 
        ml.addWidget(self.m_name); ml.addWidget(self.m_subs)
        tabs.addTab(a, tr("با YouTube API")); tabs.addTab(m, tr("لیست دستی"))
        self.tabs = tabs
        c = Card(tr("منبع داده")); c.lay.addWidget(tabs)
        self.lay.addWidget(c)
        mc = Card(tr("اعداد خصوصی Studio (اختیاری؛ برای ارزیابی دقیق‌تر مانیتایز)"))
        mf = QFormLayout(); mf.setLabelAlignment(Qt.AlignmentFlag.AlignLeading)
        self.wh = num_spin(1e7, 0); self.sv = num_spin(1e10, 0)
        mf.addRow(label(tr("ساعت watch time در ۱۲ ماه اخیر"), wrap=False), self.wh)
        mf.addRow(label(tr("ویوی Shorts در ۹۰ روز اخیر"), wrap=False), self.sv)
        mc.lay.addLayout(mf)
        self.lay.addWidget(mc)

    def make_worker(self):
        mode = "api" if self.tabs.currentIndex() == 0 else "manual"
        nums = {"watch_hours_12m": self.wh.value() or None, "shorts_views_90d": self.sv.value() or None}
        if mode == "api":
            if not self.ref.text().strip():
                QMessageBox.information(self, tr("کانال"), tr("آدرس یا @handle کانال رو وارد کن."))
                return None
            if not (self.ctx.settings["youtube_key"] or "").strip():
                QMessageBox.warning(self, tr("کلید لازمه"), tr("کلید YouTube Data API رو در تنظیمات وارد کن، یا از تب «لیست دستی» استفاده کن."))
                return None
        else:
            nums.update({"name": self.m_name.text().strip(), "subs": int(self.m_subs.value()) or None})
        return ChannelWorker(self.ctx.settings, mode, self.ref.text(), self.manual.toPlainText(), nums, self.limit.value())

    def to_sections(self, res):
        a, st, ch, secs = res["ai"], res["stats"], res["channel"], []
        head = ch.get("title") or ""
        if ch.get("subs") is not None:
            head += f" — {ch['subs']:,} subs"
        S(secs, tr("کانال"), "text", "\n".join(x for x in (head, a.get("headline"), a.get("summary")) if x))
        S(secs, tr("امتیاز سلامت کانال"), "scores", [(tr("امتیاز کلی"), a.get("channel_score"), True)])
        g = a.get("growth_diagnosis") or {}
        S(secs, tr("گلوگاه اصلی رشد") + (f" — {g['stage']}" if g.get("stage") else ""), "text", g.get("main_bottleneck"))
        S(secs, tr("شواهد"), "bullets", g.get("evidence"))
        facts = []
        if st.get("long_median_views") is not None:
            facts.append(tr(f"میانه ویو ویدیوهای لانگ: {st['long_median_views']:,} ({st.get('long_median_vpd')} ویو/روز)"))
        if st.get("short_median_views") is not None:
            facts.append(tr(f"میانه ویو Shorts: {st['short_median_views']:,} ({st.get('short_median_vpd')} ویو/روز)"))
        fm = st.get("format_mix", {})
        facts.append(tr(f"ترکیب: {fm.get('long', 0)} لانگ / {fm.get('short', 0)} Shorts"))
        if st.get("median_gap_days") is not None:
            facts.append(tr(f"فاصله میانه بین آپلودها: {st['median_gap_days']} روز؛ آخرین آپلود {st.get('days_since_last_upload')} روز پیش"))
        if st.get("vpd_variation") is not None:
            facts.append(tr(f"نوسان عملکرد ویدیوها: {st['vpd_variation']} (بالاتر از ~1 یعنی عملکرد خیلی غیرقابل‌پیش‌بینی)"))
        S(secs, tr("آمار محاسبه‌شده"), "bullets", facts)
        def vid(v):
            return {"title": f"{v['title']}", "body": f"{v['views']:,} views · {v['vpd']}/day · {v.get('rel')}x · {v['format']}"}
        S(secs, tr("بهترین ویدیوها (نسبت به میانه خود کانال)"), "items", [vid(v) for v in st.get("top", [])])
        S(secs, tr("ضعیف‌ترین ویدیوها"), "items", [vid(v) for v in st.get("bottom", [])])
        lifts = st.get("title_feature_lift") or {}
        LN = {"has_number": tr("عدد در تیتر"), "question": tr("سوال در تیتر"), "emoji": tr("ایموجی"), "excl": tr("علامت تعجب"),
              "brackets": tr("پرانتز/براکت/|"), "title_len<=50": tr("تیتر ≤ ۵۰ حرف")}
        S(secs, tr("اثر ویژگی‌های تیتر (میانه عملکرد نسبی؛ نمونه کوچکه، فقط نشانه)"), "bullets",
          [f"{LN.get(k, k)}: {v['with']}x {tr('با')} / {v['without']}x {tr('بدون')} (n={v['n_with']})" for k, v in lifts.items()])
        S(secs, tr("چک‌لیست مانیتایز (YPP)"), "checklist", st.get("monetization_checklist"))
        mo = a.get("monetization") or {}
        MS = {"likely_eligible": tr("احتمالاً واجد شرایط"), "close": tr("نزدیک"), "not_yet": tr("هنوز نه"), "unknown": tr("نامعلوم"), "at_risk": tr("در خطر")}
        S(secs, tr("ارزیابی مانیتایز") + (f" — {MS.get(str(mo.get('status')), mo.get('status'))}" if mo.get("status") else ""), "bullets", mo.get("reasons"), "info")
        S(secs, tr("چی کمه"), "bullets", mo.get("missing"), "warn")
        S(secs, tr("ریسک‌های قوانین"), "items", policy_items(mo.get("risks")))
        S(secs, tr("نقاط قوت"), "bullets", a.get("strengths"), "ok")
        S(secs, tr("نقاط ضعف"), "bullets", a.get("weaknesses"), "bad")
        t = a.get("title_analysis") or {}
        S(secs, tr("تیترها: چی جواب می‌ده"), "bullets", t.get("what_works"), "ok")
        S(secs, tr("تیترها: چی جواب نمی‌ده"), "bullets", t.get("what_fails"), "bad")
        S(secs, tr("الگوهای تیتر"), "bullets", t.get("patterns"))
        S(secs, tr("بازنویسی نمونه تیترها"), "items", [{"title": f"{r.get('old', '')}  →  {r.get('new', '')}", "body": r.get("why", "")} for r in as_list(t.get("rewrite_examples")) if isinstance(r, dict)])
        th = a.get("thumbnail_analysis") or {}
        S(secs, tr(f"تامبنیل‌ها (تحلیل تصویری {res.get('n_thumbs', 0)} تامبنیل)"), "bullets", th.get("what_works"), "ok")
        S(secs, tr("تامبنیل‌ها: مشکلات"), "bullets", th.get("what_fails"), "bad")
        S(secs, tr("یکپارچگی بصری"), "text", th.get("consistency"))
        S(secs, tr("اصلاح تامبنیل"), "bullets", th.get("fixes"), "warn")
        c = a.get("content_analysis") or {}
        S(secs, tr("موضوع‌های موفق"), "bullets", c.get("best_topics"), "ok")
        S(secs, tr("موضوع‌های ضعیف"), "bullets", c.get("weak_topics"), "bad")
        S(secs, tr("ترکیب فرمت لانگ/Shorts"), "text", c.get("format_mix_advice"))
        S(secs, tr("ایده سری (Series)"), "bullets", c.get("series_ideas"))
        S(secs, tr("پیشنهادهای بهبود کانال (به ترتیب اولویت)"), "items", [{"title": f"{r.get('priority', '')}. {r.get('action', '')}", "body": r.get("why", ""), "chip": effort(r.get("effort"))} for r in as_list(a.get("recommendations")) if isinstance(r, dict)])
        S(secs, tr("ایده ویدیوهای بعدی"), "items", [{"title": r.get("idea", ""), "body": r.get("why", ""), "chip": r.get("format", "")} for r in as_list(a.get("next_video_ideas")) if isinstance(r, dict)])
        S(secs, tr("استراتژی آپلود"), "text", a.get("upload_strategy"))
        return secs
