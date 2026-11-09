from __future__ import annotations

import html
import json
import time

from .analysis import VERDICT_FA
from .knowledge import RULES, rule_title
from .local_checks import fmt_ts

SEV_FA = {"high": "جدی", "medium": "متوسط", "low": "کم", "info": "اطلاع"}
SEV_COL = {"high": "#d93025", "medium": "#e37400", "low": "#1a73e8", "info": "#888"}


def to_json(rep: dict) -> str:
    slim = {k: v for k, v in rep.items() if k not in ("ref", "fingerprints")}
    return json.dumps(slim, ensure_ascii=False, indent=2)


def to_markdown(rep: dict) -> str:
    i = rep["info"]
    L = [f"# گزارش بررسی: {rep['name']}", "",
         f"- فرمت: {'Shorts' if rep['format']=='short' else 'ویدیوی لانگ'} | مدت: {fmt_ts(i['duration'])} | {i['width']}×{i['height']}",
         f"- امتیاز ریسک: **{rep['score']}/100** — {VERDICT_FA[rep['verdict']]}", ""]
    ai = rep.get("ai")
    if ai:
        L += ["## خلاصه AI", ai["summary"], ""]
        d = ai["disclosure"]
        L += ["## افشای AI (Altered or synthetic content)", f"- لازم است؟ **{d['required']}** — {d['reason']}"]
        if d["suggested_description_text"]:
            L += [f"- متن پیشنهادی: {d['suggested_description_text']}"]
        L.append("")
    L.append("## یافته‌ها")
    for f in rep["findings"]:
        ts = f" [{f['timestamp']}]" if f.get("timestamp") else ""
        L += [f"### ({SEV_FA[f['severity']]}){ts} {f['issue']}", f"- قانون: {rule_title(f['rule_id'])}"]
        if f.get("evidence"):
            L.append(f"- شواهد: {f['evidence']}")
        if f.get("fix"):
            L.append(f"- راه‌حل: {f['fix']}")
        L.append("")
    if ai and ai["copyright_suspects"]:
        L.append("## مشکوک به کپی‌رایت (حدس AI، نه Content ID)")
        for c in ai["copyright_suspects"]:
            L.append(f"- [{c.get('timestamp','?')}] {c.get('type','')}: {c.get('description','')} — {c.get('advice','')}")
        L.append("")
    L.append("> این گزارش ارزیابی ریسک است، نه تضمین تصمیم یوتیوب و نه مشاوره حقوقی.")
    return "\n".join(L)


def to_html(rep: dict) -> str:
    e = html.escape
    i = rep["info"]
    ai = rep.get("ai")
    col = {"safe": "#1e8e3e", "caution": "#e37400", "risky": "#d93025"}[rep["verdict"]]
    cards = []
    for f in rep["findings"]:
        ts = f' <span class="chip">⏱ {e(str(f["timestamp"]))}</span>' if f.get("timestamp") else ""
        cards.append(
            f'<div class="card" style="border-right:5px solid {SEV_COL[f["severity"]]}">'
            f'<span class="chip" style="background:{SEV_COL[f["severity"]]};color:#fff">{SEV_FA[f["severity"]]}</span>{ts}'
            f' <small>{e(rule_title(f["rule_id"]))}</small><h3>{e(f["issue"])}</h3>'
            + (f'<p class="m">شواهد: {e(f["evidence"])}</p>' if f.get("evidence") else "")
            + (f'<p>راه‌حل: {e(f["fix"])}</p>' if f.get("fix") else "") + "</div>")
    ai_block = ""
    if ai:
        d = ai["disclosure"]
        ai_block = (f'<div class="card"><h3>خلاصه AI</h3><p>{e(ai["summary"])}</p></div>'
                    f'<div class="card"><h3>افشای AI</h3><p>لازم است؟ <b>{e(d["required"])}</b> — {e(d["reason"])}</p>'
                    + (f'<p class="m">متن پیشنهادی: {e(d["suggested_description_text"])}</p>' if d["suggested_description_text"] else "") + "</div>")
        if ai["copyright_suspects"]:
            ai_block += '<div class="card"><h3>مشکوک به کپی‌رایت (حدس AI، نه Content ID)</h3><ul>' + "".join(
                f'<li>[{e(str(c.get("timestamp","?")))}] {e(str(c.get("type","")))}: {e(str(c.get("description","")))} — {e(str(c.get("advice","")))}</li>'
                for c in ai["copyright_suspects"]) + "</ul></div>"
    return f"""<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>گزارش {e(rep['name'])}</title>
<style>body{{font-family:Vazirmatn,Tahoma,sans-serif;background:#fff;color:#0f0f0f;max-width:860px;margin:30px auto;padding:0 16px}}
@media(prefers-color-scheme:dark){{body{{background:#0f0f0f;color:#f1f1f1}}.card{{background:#181818!important}}}}
.card{{background:#f7f7f7;border-radius:12px;padding:12px 16px;margin:10px 0}}.chip{{background:#e0e0e0;color:#222;border-radius:9px;padding:1px 9px;font-size:12px}}
.m{{color:#777}}h1{{color:#f00}}.score{{font-size:44px;font-weight:700;color:{col}}}</style>
<h1>گزارش بررسی ویدیو</h1><p><b>{e(rep['name'])}</b> — {'Shorts' if rep['format']=='short' else 'لانگ'} — {fmt_ts(i['duration'])} — {i['width']}×{i['height']}</p>
<div class="score">{rep['score']}<small style="font-size:16px"> / 100 — {VERDICT_FA[rep['verdict']]}</small></div>
{ai_block}<h2>یافته‌ها</h2>{''.join(cards) or '<p>موردی پیدا نشد.</p>'}
<p class="m">تولید شده با YT Guard در {time.strftime('%Y-%m-%d %H:%M', time.localtime(rep['ts']))}. این گزارش ارزیابی ریسک است، نه تضمین تصمیم یوتیوب و نه مشاوره حقوقی.</p></html>"""
