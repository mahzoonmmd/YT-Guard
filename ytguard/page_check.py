from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QRadioButton, QScrollArea,
                             QVBoxLayout, QWidget)

from . import report as report_mod
from .analysis import VERDICT_FA
from .context import AppContext
from .knowledge import NICHES
from .local_checks import VIDEO_EXTS, fmt_ts
from .questionnaire import DEFAULT_ANSWERS
from .widgets import Card, DropZone, FindingCard, ScoreGauge, label
from .workers import AnalyzeWorker, FollowUpWorker, InfoWorker


def combo(items: list[tuple[str, str]]) -> QComboBox:
    c = QComboBox()
    c.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    for key, text in items:
        c.addItem(text, key)
    return c


class FollowUpDialog(QDialog):
    def __init__(self, questions: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI چند سوال از تو داره")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(520)
        self.q = questions
        self.groups: list[tuple[QButtonGroup, list[QRadioButton], QLineEdit]] = []
        lay = QVBoxLayout(self)
        lay.addWidget(label("این جواب‌ها روی نتیجه اثر دارن. هر چی مطمئنی جواب بده؛ نمی‌دونی؟ «نمی‌دونم» رو بزن.", muted=True))
        for q in questions:
            box = Card()
            box.lay.addWidget(label(q["question"], h2=True))
            if q.get("why"):
                box.lay.addWidget(label("چرا می‌پرسم: " + q["why"], muted=True))
            g = QButtonGroup(self)
            rbs = []
            for o in q["options"] + ["نمی‌دونم"]:
                rb = QRadioButton(o)
                g.addButton(rb)
                box.lay.addWidget(rb)
                rbs.append(rb)
            rbs[-1].setChecked(True)
            extra = QLineEdit()
            extra.setPlaceholderText("توضیح بیشتر (اختیاری)")
            box.lay.addWidget(extra)
            self.groups.append((g, rbs, extra))
            lay.addWidget(box)
        row = QHBoxLayout()
        ok = QPushButton("ارسال و بررسی مجدد")
        ok.setProperty("primary", True)
        ok.clicked.connect(self.accept)
        skip = QPushButton("بی‌خیال")
        skip.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(skip)
        row.addStretch(1)
        lay.addLayout(row)

    def answers(self) -> list[dict]:
        out = []
        for q, (g, rbs, extra) in zip(self.q, self.groups):
            ans = next((r.text() for r in rbs if r.isChecked()), "نمی‌دونم")
            if extra.text().strip():
                ans += " — " + extra.text().strip()
            out.append({"question": q["question"], "answer": ans})
        return out


class CheckPage(QWidget):
    reportReady = pyqtSignal(dict)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker = None
        self.info = None
        self.report = None
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea()
        self.scroll = sc
        sc.setWidgetResizable(True)
        root.addWidget(sc)
        body = QWidget()
        sc.setWidget(body)
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(24, 18, 24, 24)
        self.lay.setSpacing(14)

        self.lay.addWidget(label("بررسی ویدیو با قوانین یوتیوب", h1=True))
        self.lay.addWidget(label("ویدیو رو قبل از آپلود بنداز اینجا. کپی‌رایت، افشای AI، محتوای غیراصیل، Shorts/لانگ و مشکلات ریزش بیننده چک می‌شه.", muted=True))

        self.drop = DropZone()
        self.drop.fileDropped.connect(self.load_file)
        self.drop.clicked.connect(self.pick_file)
        self.lay.addWidget(self.drop)
        self.file_note = label("", muted=True)
        self.lay.addWidget(self.file_note)

        # ---- questionnaire
        self.form_card = Card("چند سوال سریع (دقت نتیجه رو بالا می‌بره)")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        self.c_fmt = combo([("auto", "خودکار (از روی ویدیو)"), ("long", "ویدیوی لانگ"), ("short", "Shorts")])
        self.c_ai = combo([("none", "از AI استفاده نشده"), ("assist", "فقط کمک (ایده، اسکریپت، ادیت)"),
                           ("mostly", "بخش عمده با AI ساخته شده"), ("full", "کامل با AI، تقریباً بدون دخالت من")])
        self.c_voice = combo([("none", "صدای خودم / صدای واقعی"), ("own_clone", "کلون صدای خودم"),
                              ("generic_tts", "گوینده AI / TTS عمومی"), ("real_person_clone", "کلون صدای یک فرد دیگر")])
        self.c_vis = combo([("none", "تصویر واقعی / بدون AI"), ("stylized", "AI به سبک انیمیشن/غیرواقعی"),
                            ("realistic", "تصویر/ویدیوی واقع‌نمای AI"), ("real_people_events", "AI از افراد یا رویدادهای واقعی")])
        self.k_music_ai = QCheckBox("موزیک با AI ساخته شده")
        self.c_tv = combo([("none", "کلیپ دیگران ندارم"), ("short_with_commentary", "کلیپ کوتاه با تفسیر خودم"),
                           ("long_or_no_commentary", "کلیپ بلند یا بدون تفسیر کافی")])
        self.c_tm = combo([("none", "موزیک ندارم / مال خودمه"), ("library_licensed", "موزیک لایسنس‌دار / Audio Library"),
                           ("popular_song", "آهنگ معروف / تجاری"), ("unknown", "منبعش رو نمی‌دونم")])
        self.c_niche = combo(NICHES)
        self.k_kids = QCheckBox("ویدیو مخصوص کودکان است")
        self.k_sponsor = QCheckBox("اسپانسر / تبلیغ پولی دارد")
        self.k_series = QCheckBox("از این ویدیو زیاد با قالب مشابه می‌سازم")
        self.k_mon = QCheckBox("کانال مانیتایز است (یا می‌خوام بشه)")
        self.k_mon.setChecked(True)
        self.e_notes = QLineEdit()
        self.e_notes.setPlaceholderText("هر چیز دیگه‌ای که AI باید بدونه (مثلاً موضوع، منبع کلیپ‌ها…)")
        for lbl, w in (("فرمت ویدیو", self.c_fmt), ("استفاده از AI", self.c_ai), ("صدا", self.c_voice), ("تصویر", self.c_vis),
                       ("کلیپ دیگران", self.c_tv), ("موزیک", self.c_tm), ("موضوع کانال", self.c_niche)):
            form.addRow(label(lbl, wrap=False), w)
        form.addRow("", self.k_music_ai)
        form.addRow("", self.k_kids)
        form.addRow("", self.k_sponsor)
        form.addRow("", self.k_series)
        form.addRow("", self.k_mon)
        form.addRow(label("توضیح اضافه", wrap=False), self.e_notes)
        self.form_card.lay.addLayout(form)
        self.fmt_hint = label("", muted=True)
        self.form_card.lay.addWidget(self.fmt_hint)
        self.lay.addWidget(self.form_card)

        # ---- actions
        row = QHBoxLayout()
        self.btn_go = QPushButton("شروع بررسی با AI")
        self.btn_go.setProperty("primary", True)
        self.btn_go.setEnabled(False)
        self.btn_go.clicked.connect(lambda: self.start(True))
        self.btn_local = QPushButton("فقط تحلیل محلی (بدون AI)")
        self.btn_local.setEnabled(False)
        self.btn_local.clicked.connect(lambda: self.start(False))
        self.btn_cancel = QPushButton("لغو")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel)
        row.addWidget(self.btn_go)
        row.addWidget(self.btn_local)
        row.addWidget(self.btn_cancel)
        row.addStretch(1)
        self.lay.addLayout(row)
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setVisible(False)
        self.status = label("", muted=True)
        self.lay.addWidget(self.prog)
        self.lay.addWidget(self.status)

        # ---- results
        self.results = QWidget()
        self.res_lay = QVBoxLayout(self.results)
        self.res_lay.setContentsMargins(0, 0, 0, 0)
        self.res_lay.setSpacing(12)
        self.results.setVisible(False)
        self.lay.addWidget(self.results)
        self.lay.addStretch(1)

    # ------------------------------------------------------------------ file
    def pick_file(self):
        exts = " ".join(f"*{e}" for e in sorted(VIDEO_EXTS))
        p, _ = QFileDialog.getOpenFileName(self, "انتخاب ویدیو", "", f"Video ({exts});;All files (*)")
        if p:
            self.load_file(p)

    def load_file(self, path: str):
        if Path(path).suffix.lower() not in VIDEO_EXTS:
            QMessageBox.warning(self, "فرمت نامعتبر", "این فایل ویدیو نیست.")
            return
        self.status.setText("در حال خواندن مشخصات ویدیو…")
        self.drop.set_file(Path(path).name, "…")
        w = InfoWorker(self.ctx.settings, path)
        w.done.connect(lambda r, p=path: self._file_loaded(p, r))
        w.failed.connect(lambda m: (self.status.setText(m), QMessageBox.warning(self, "خطا", m)))
        self._info_worker = w
        w.start()

    def _file_loaded(self, path, r):
        self.info = r["info"]
        i = self.info
        self.drop.set_file(Path(path).name, f"{fmt_ts(i['duration'])} · {i['width']}×{i['height']} · {i['fps']:.0f}fps · "
                                             f"{i['size']/1024/1024:.0f} MB · {'عمودی' if i['orientation']=='vertical' else 'افقی' if i['orientation']=='horizontal' else 'مربع'}")
        self.path = path
        idx = self.c_fmt.findData("auto")
        self.c_fmt.setCurrentIndex(idx)
        self.guess = r["fmt"]
        self.c_fmt.setItemText(0, f"خودکار ← {'Shorts' if r['fmt']=='short' else 'ویدیوی لانگ'}")
        if r["ambiguous"]:
            self.fmt_hint.setText("⚠ مشخصات این ویدیو (جهت تصویر/مدت) واضح نیست. لطفاً فرمت واقعی که آپلود می‌کنی رو دستی انتخاب کن.")
            self.c_fmt.setStyleSheet("border: 2px solid #FF0000;")
        else:
            self.fmt_hint.setText("")
            self.c_fmt.setStyleSheet("")
        self.status.setText("")
        self.btn_go.setEnabled(True)
        self.btn_local.setEnabled(True)
        self.results.setVisible(False)
        self.ctx.set_video(path, i)
        self.ctx.refs.pop(path, None)

    # ------------------------------------------------------------------ run
    def answers(self) -> dict:
        a = dict(DEFAULT_ANSWERS)
        a.update({"fmt": self.c_fmt.currentData(), "ai_level": self.c_ai.currentData(), "ai_voice": self.c_voice.currentData(),
                  "ai_visuals": self.c_vis.currentData(), "ai_music": self.k_music_ai.isChecked(),
                  "third_party_video": self.c_tv.currentData(), "third_party_music": self.c_tm.currentData(),
                  "niche": self.c_niche.currentData(), "kids": self.k_kids.isChecked(), "sponsor": self.k_sponsor.isChecked(),
                  "series_template": self.k_series.isChecked(), "monetized": self.k_mon.isChecked(), "notes": self.e_notes.text().strip()})
        return a

    def start(self, use_ai: bool):
        if not getattr(self, "path", None):
            return
        if use_ai:
            ok, why = self.ctx.ai_ready()
            if not ok:
                r = QMessageBox.question(self, "AI آماده نیست", f"{why}.\nفقط تحلیل محلی و پرسشنامه اجرا بشه؟")
                if r != QMessageBox.StandardButton.Yes:
                    return
                use_ai = False
        a = self.answers()
        fmt = a["fmt"] if a["fmt"] != "auto" else self.guess
        self.set_busy(True)
        self.worker = AnalyzeWorker(self.ctx.settings, self.ctx.history, self.path, fmt, a, use_ai, self.ctx.cached_ref(self.path))
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("در حال لغو…")

    def set_busy(self, b: bool):
        self.btn_go.setEnabled(not b and bool(getattr(self, "path", None)))
        self.btn_local.setEnabled(not b and bool(getattr(self, "path", None)))
        self.btn_cancel.setVisible(b)
        self.prog.setVisible(b)
        if b:
            self.prog.setValue(0)

    def on_progress(self, p, t):
        self.prog.setValue(p)
        self.status.setText(t)

    def on_failed(self, msg):
        self.set_busy(False)
        self.status.setText(msg)
        if msg != "لغو شد.":
            QMessageBox.warning(self, "خطا", msg)

    def on_done(self, rep):
        self.set_busy(False)
        self.status.setText("")
        self.report = rep
        if rep.get("ref"):
            self.ctx.refs[rep["path"]] = rep["ref"]
        self.reportReady.emit(rep)
        self.render(rep)
        QTimer.singleShot(150, lambda: self.scroll.ensureWidgetVisible(self.results, 0, 0))
        ai = rep.get("ai")
        if ai and ai["follow_up_questions"]:
            dlg = FollowUpDialog(ai["follow_up_questions"], self)
            if dlg.exec():
                self.set_busy(True)
                self.worker = FollowUpWorker(self.ctx.settings, rep, dlg.answers(), rep.get("ref"))
                self.worker.progress.connect(self.on_progress)
                self.worker.done.connect(self.on_done)
                self.worker.failed.connect(self.on_failed)
                self.worker.start()

    # ------------------------------------------------------------------ render
    def clear_results(self):
        while self.res_lay.count():
            it = self.res_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                while it.layout().count():
                    x = it.layout().takeAt(0)
                    if x.widget():
                        x.widget().deleteLater()

    def render(self, rep: dict):
        self.clear_results()
        self.results.setVisible(True)
        theme = self.ctx.settings["theme"]
        top = QHBoxLayout()
        g = ScoreGauge(theme)
        g.set_value(rep["score"], rep["verdict"], VERDICT_FA[rep["verdict"]])
        self.gauge = g
        sumcard = Card("خلاصه")
        i = rep["info"]
        fmt_fa = "Shorts" if rep["format"] == "short" else "ویدیوی لانگ"
        sumcard.lay.addWidget(label(f"{rep['name']} — {fmt_fa} — {fmt_ts(i['duration'])}", muted=True))
        ai = rep.get("ai")
        if ai:
            sumcard.lay.addWidget(label(ai["summary"], selectable=True))
            u = ai["ai_usage"]
            flags = [n for n, v in (("صدای AI", u["likely_ai_voice"]), ("تصویر AI", u["likely_ai_visuals"]), ("موزیک AI", u["likely_ai_music"])) if v]
            sumcard.lay.addWidget(label("تشخیص AI: " + ("، ".join(flags) if flags else "نشانه‌ی مشخصی دیده نشد")
                                        + f" (اطمینان {u['confidence']*100:.0f}٪)" + (f" — {u['evidence']}" if u["evidence"] else ""), selectable=True))
        else:
            msg = rep.get("ai_error") or "این نتیجه فقط از تحلیل محلی و پاسخ‌های تو ساخته شده؛ بررسی AI اجرا نشد."
            sumcard.lay.addWidget(label("⚠ " + msg, selectable=True))
        sev_counts = {s: sum(1 for f in rep["findings"] if f["severity"] == s) for s in ("high", "medium", "low")}
        sumcard.lay.addWidget(label(f"یافته‌ها: {sev_counts['high']} جدی · {sev_counts['medium']} متوسط · {sev_counts['low']} کم", muted=True))
        top.addWidget(g)
        top.addWidget(sumcard, 1)
        self.res_lay.addLayout(top)

        if ai:
            d = ai["disclosure"]
            req = {"yes": "بله، باید افشا کنی", "no": "لازم نیست", "maybe": "احتمالاً لازم است"}.get(d["required"], d["required"])
            dc = Card("افشای محتوای AI در YouTube Studio (Altered or synthetic content)")
            dc.lay.addWidget(label(f"نتیجه: {req}. {d['reason']}", selectable=True))
            if d["suggested_description_text"]:
                dc.lay.addWidget(label("متن پیشنهادی برای توضیحات: " + d["suggested_description_text"], muted=True, selectable=True))
            self.res_lay.addWidget(dc)

        self.res_lay.addWidget(label("یافته‌ها و راه‌حل‌ها", h2=True))
        if not rep["findings"]:
            self.res_lay.addWidget(label("✔ مشکل مشخصی پیدا نشد.", selectable=True))
        for f in rep["findings"]:
            self.res_lay.addWidget(FindingCard(f))

        if ai and ai["copyright_suspects"]:
            cc = Card("مشکوک به کپی‌رایت (حدس AI، نه جایگزین Content ID)")
            for c in ai["copyright_suspects"]:
                cc.lay.addWidget(label(f"⏱ {c.get('timestamp','؟')} · {c.get('type','')}: {c.get('description','')} — {c.get('advice','')}", selectable=True))
            self.res_lay.addWidget(cc)
        if ai and (ai["retention"]["hook_comment"] or ai["retention"]["notes"]):
            rc = Card(f"ماندگاری بیننده (امتیاز هوک: {ai['retention']['hook_score']:.0f}/10)")
            if ai["retention"]["hook_comment"]:
                rc.lay.addWidget(label(ai["retention"]["hook_comment"], selectable=True))
            for n in ai["retention"]["notes"]:
                rc.lay.addWidget(label(f"⏱ {n.get('timestamp','')} — {n.get('note','')}", selectable=True))
            self.res_lay.addWidget(rc)
        if ai and ai["positives"]:
            pc = Card("نقاط قوت")
            for p in ai["positives"]:
                pc.lay.addWidget(label("✔ " + p, selectable=True))
            self.res_lay.addWidget(pc)

        note = label("این گزارش ارزیابی ریسک است: نه تضمین تصمیم یوتیوب، نه مشاوره حقوقی. تشخیص AI و کپی‌رایت احتمالاتی است؛ Content ID واقعی فقط بعد از آپلود (Checks در Studio) مشخص می‌شه.", muted=True)
        self.res_lay.addWidget(note)
        row = QHBoxLayout()
        for text, fn in (("ذخیره گزارش HTML", self.export_html), ("ذخیره Markdown", self.export_md), ("ذخیره JSON", self.export_json)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        self.res_lay.addLayout(row)

    def _save(self, ext, filt, content):
        if not self.report:
            return
        p, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش", f"{Path(self.report['name']).stem}_report.{ext}", filt)
        if p:
            Path(p).write_text(content, encoding="utf-8")

    def export_html(self):
        self._save("html", "HTML (*.html)", report_mod.to_html(self.report) if self.report else "")

    def export_md(self):
        self._save("md", "Markdown (*.md)", report_mod.to_markdown(self.report) if self.report else "")

    def export_json(self):
        self._save("json", "JSON (*.json)", report_mod.to_json(self.report) if self.report else "")

    def set_theme(self, theme):
        if getattr(self, "gauge", None):
            try:
                self.gauge.set_theme(theme)
            except RuntimeError:
                pass

    def show_saved(self, rep: dict):
        """Open a past report from history."""
        self.report = rep
        self.path = rep["path"]
        self.render(rep)
