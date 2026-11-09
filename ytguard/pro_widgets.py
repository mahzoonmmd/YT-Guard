"""Shared result renderer for the AI report pages: sections -> cards (and Markdown export)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from .i18n import DIR, tr
from .knowledge import rule_title
from .widgets import Card, label

# section kinds: scores | text | bullets | items | checklist
# scores:   [(label, value 0-100, higher_is_better)]
# bullets:  [str]   tone: ok|bad|warn|info
# items:    [{"title","body","fix","chip"}]
# checklist:[{"label","status","detail"}]
ST_ICON = {"ok": "✔", "partial": "◐", "no": "✖", "unknown": "？"}
ST_TXT = {"ok": "OK", "partial": tr("نیمه‌کاره"), "no": tr("برقرار نیست"), "unknown": tr("نامعلوم")}
TONE_ICON = {"ok": "✔", "bad": "✖", "warn": "⚠", "info": "•"}


def _num(v, default=None):
    try:
        return max(0, min(100, int(float(v))))
    except (TypeError, ValueError):
        return default


def as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def S(sections: list, title: str, kind: str, data, tone: str = "info"):
    """Append a section only when it has content."""
    if data in (None, "", [], {}):
        return
    sections.append({"title": title, "kind": kind, "data": data, "tone": tone})


def score_color(v: int, good_high: bool = True) -> str:
    g = v if good_high else 100 - v
    return "#2e9e5b" if g >= 70 else ("#d98a00" if g >= 40 else "#e53935")


def build_cards(sections: list[dict], into: QVBoxLayout):
    while into.count():
        it = into.takeAt(0)
        if it.widget():
            it.widget().deleteLater()
    for sec in sections:
        card = Card(sec["title"])
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        k, data = sec["kind"], sec["data"]
        if k == "scores":
            for name, val, good_high in data:
                v = _num(val)
                if v is None:
                    continue
                row = QHBoxLayout()
                nm = label(name, wrap=False); nm.setMinimumWidth(170)
                bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(v); bar.setTextVisible(False); bar.setMinimumHeight(20)
                bar.setStyleSheet(f"QProgressBar::chunk {{ background: {score_color(v, good_high)}; border-radius: 6px; }}")
                val = label(f"{v}/100", wrap=False, rtl=False); val.setMinimumWidth(56)
                row.addWidget(nm); row.addWidget(bar, 1); row.addWidget(val)
                card.lay.addLayout(row)
        elif k == "text":
            card.lay.addWidget(label(str(data), selectable=True))
        elif k == "bullets":
            for b in as_list(data):
                card.lay.addWidget(label(f"{TONE_ICON.get(sec['tone'], '•')}  {_s(b)}", selectable=True))
        elif k == "items":
            for it in as_list(data):
                if not isinstance(it, dict):
                    card.lay.addWidget(label("• " + _s(it), selectable=True)); continue
                box = QFrame(); box.setProperty("card", True); box.setLayoutDirection(DIR)
                box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                bl = QVBoxLayout(box); bl.setContentsMargins(12, 8, 12, 8); bl.setSpacing(3)
                head = it.get("title", "")
                if it.get("chip"):
                    head = f"[{it['chip']}]  {head}"
                bl.addWidget(label(head, h2=True, selectable=True))
                if it.get("body"):
                    bl.addWidget(label(it["body"], muted=True, selectable=True))
                if it.get("fix"):
                    bl.addWidget(label(tr("راه‌حل: ") + it["fix"], selectable=True))
                card.lay.addWidget(box)
        elif k == "checklist":
            for c in data:
                st = c.get("status", "unknown")
                line = f"{ST_ICON.get(st, '？')}  {c['label']}"
                if c.get("detail"):
                    line += f"  —  {c['detail']}"
                card.lay.addWidget(label(line, selectable=True))
        into.addWidget(card)
    into.addStretch(1)


def _s(x) -> str:
    if isinstance(x, dict):
        return " — ".join(str(v) for v in x.values() if v)
    return str(x)


def to_markdown(title: str, sections: list[dict]) -> str:
    out = [f"# {title}", ""]
    for sec in sections:
        out.append(f"## {sec['title']}")
        k, data = sec["kind"], sec["data"]
        if k == "scores":
            out += [f"- {n}: {_num(v)}/100" for n, v, _ in data if _num(v) is not None]
        elif k == "text":
            out.append(str(data))
        elif k == "bullets":
            out += [f"- {_s(b)}" for b in as_list(data)]
        elif k == "items":
            for it in as_list(data):
                if isinstance(it, dict):
                    out.append(f"- **{it.get('title', '')}**" + (f" ({it['chip']})" if it.get("chip") else ""))
                    if it.get("body"):
                        out.append(f"  - {it['body']}")
                    if it.get("fix"):
                        out.append(f"  - {tr('راه‌حل: ')}{it['fix']}")
                else:
                    out.append(f"- {_s(it)}")
        elif k == "checklist":
            out += [f"- {ST_ICON.get(c.get('status'), '?')} {c['label']}" + (f" — {c['detail']}" if c.get("detail") else "") for c in data]
        out.append("")
    return "\n".join(out)


def policy_items(flags) -> list[dict]:
    out = []
    for f in as_list(flags):
        if isinstance(f, dict):
            out.append({"title": f.get("issue", ""), "body": rule_title(f.get("rule_id", "")), "fix": f.get("fix", ""), "chip": sev(f.get("severity", ""))})
    return out


def pairs(items, a: str, b: str, ctitle: str = "title") -> list[dict]:
    out = []
    for it in as_list(items):
        if isinstance(it, dict):
            out.append({"title": str(it.get(a, "")), "body": str(it.get(b, ""))})
        else:
            out.append({"title": str(it), "body": ""})
    return out


_LV = {"high": tr("زیاد"), "medium": tr("متوسط"), "low": tr("کم")}


def impact(x) -> str:
    return (tr("اثر: ") + _LV.get(str(x).lower(), str(x))) if x else ""


def effort(x) -> str:
    return (tr("تلاش: ") + _LV.get(str(x).lower(), str(x))) if x else ""


def sev(x) -> str:
    return _LV.get(str(x).lower(), str(x)) if x else ""
