from __future__ import annotations

import math
import re
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF, QPainterPath
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .knowledge import IMPACT_FA, RULES, rule_title
from .theme import palette


def repolish(w: QWidget):
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


_LTR_RUN = re.compile(r"-?[A-Za-z0-9][A-Za-z0-9.,:/×%+_\-]*(?: [A-Za-z0-9][A-Za-z0-9.,:/×%+_\-]*)*")


def ltr_runs(text: str) -> str:
    """Keep Latin/number runs (e.g. '-14 LUFS', '1080×1920') visually intact inside RTL Persian text."""
    return _LTR_RUN.sub(lambda m: "\u200e" + m.group(0) + "\u200e", text)


def label(text="", *, muted=False, h1=False, h2=False, wrap=True, rtl=True, selectable=False) -> QLabel:
    lb = QLabel(ltr_runs(text) if rtl else text)
    lb.setWordWrap(wrap)
    if muted:
        lb.setProperty("muted", True)
    if h1:
        lb.setProperty("h1", True)
    if h2:
        lb.setProperty("h2", True)
    if rtl:
        lb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    if selectable:
        lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lb


def make_app_icon(size=256) -> QPixmap:
    """Original icon: red rounded badge with a play triangle and a check-shield ring (not a copy of any brand logo)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    # shield
    path = QPainterPath()
    path.moveTo(s * 0.5, s * 0.06)
    path.lineTo(s * 0.9, s * 0.2)
    path.lineTo(s * 0.9, s * 0.52)
    path.quadTo(s * 0.9, s * 0.8, s * 0.5, s * 0.95)
    path.quadTo(s * 0.1, s * 0.8, s * 0.1, s * 0.52)
    path.lineTo(s * 0.1, s * 0.2)
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FF0000"))
    p.drawPath(path)
    # play triangle
    p.setBrush(QColor("white"))
    tri = QPolygonF([QPointF(s * 0.42, s * 0.32), QPointF(s * 0.42, s * 0.68), QPointF(s * 0.72, s * 0.5)])
    p.drawPolygon(tri)
    p.end()
    return pm


class LogoBadge(QWidget):
    def __init__(self, size=34):
        super().__init__()
        self.setFixedSize(size, size)
        self._pm = make_app_icon(256)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._pm)


class DropZone(QFrame):
    fileDropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(150)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel("⬇")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet("font-size: 34px; color: #FF0000; background: transparent;")
        self.title = label("ویدیو رو اینجا بنداز یا کلیک کن", h2=True)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub = label("MP4 · MOV · MKV · WEBM · AVI …", muted=True)
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for w in (self.icon, self.title, self.sub):
            lay.addWidget(w)

    def set_file(self, name: str, detail: str):
        self.icon.setText("🎬")
        self.title.setText(name)
        self.sub.setText(detail)

    def mousePressEvent(self, e):
        self.clicked.emit()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setProperty("hover", True)
            repolish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("hover", False)
        repolish(self)

    def dropEvent(self, e):
        self.setProperty("hover", False)
        repolish(self)
        for u in e.mimeData().urls():
            if u.isLocalFile():
                self.fileDropped.emit(u.toLocalFile())
                break


class ScoreGauge(QWidget):
    def __init__(self, theme="dark"):
        super().__init__()
        self.setMinimumSize(190, 190)
        self.score, self.verdict_text, self.verdict = 0, "—", "safe"
        self.theme = theme

    def set_value(self, score, verdict, text):
        self.score, self.verdict, self.verdict_text = score, verdict, text
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, _):
        c = palette(self.theme)
        col = {"safe": c["ok"], "caution": c["warn"], "risky": c["bad"]}.get(self.verdict, c["muted"])
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 24
        r = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        pen = QPen(QColor(c["surface2"]), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(r, 225 * 16, -270 * 16)
        pen.setColor(QColor(col))
        p.setPen(pen)
        p.drawArc(r, 225 * 16, int(-270 * 16 * self.score / 100))
        p.setPen(QColor(c["text"]))
        f = QFont(self.font())
        f.setPointSize(30)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(r.x(), r.y() + side * 0.22, side, side * 0.35), Qt.AlignmentFlag.AlignCenter, str(self.score))
        f.setPointSize(10)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(col))
        p.drawText(QRectF(r.x(), r.y() + side * 0.55, side, side * 0.15), Qt.AlignmentFlag.AlignCenter, self.verdict_text)
        p.setPen(QColor(c["muted"]))
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(r.x(), r.y() + side * 0.70, side, side * 0.15), Qt.AlignmentFlag.AlignCenter, "امتیاز ریسک (۰ = امن)")


SEV_FA = {"high": "جدی", "medium": "متوسط", "low": "کم", "info": "اطلاع"}
SRC_FA = {"local": "تحلیل محلی", "ai": "AI", "questionnaire": "پاسخ تو"}


class FindingCard(QFrame):
    def __init__(self, f: dict):
        super().__init__()
        self.setProperty("card", True)
        self.setProperty("sev", f["severity"])
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(5)
        top = QHBoxLayout()
        chip = QLabel(SEV_FA.get(f["severity"], "")); chip.setProperty("chip", True); chip.setProperty("sev", f["severity"])
        top.addWidget(chip)
        src = QLabel(SRC_FA.get(f.get("source", ""), "")); src.setProperty("chip", True)
        top.addWidget(src)
        if f.get("timestamp"):
            ts = QLabel(f"⏱ {f['timestamp']}"); ts.setProperty("chip", True)
            top.addWidget(ts)
        rt = label(rule_title(f["rule_id"]), muted=True)
        rt.setStyleSheet("font-size: 13px;")
        top.addWidget(rt, 1)
        lay.addLayout(top)
        t = label(f["issue"], h2=True, selectable=True)
        lay.addWidget(t)
        if f.get("evidence"):
            lay.addWidget(label("شواهد: " + f["evidence"], muted=True, selectable=True))
        if f.get("fix"):
            lay.addWidget(label("راه‌حل: " + f["fix"], selectable=True))
        for lb in self.findChildren(QLabel):
            if lb.property("chip") is not True:
                lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


class Card(QFrame):
    def __init__(self, title: str | None = None):
        super().__init__()
        self.setProperty("card", True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 14)
        self.lay.setSpacing(8)
        if title:
            self.lay.addWidget(label(title, h2=True))


def copy_to_clipboard(text: str):
    QApplication.clipboard().setText(text)
