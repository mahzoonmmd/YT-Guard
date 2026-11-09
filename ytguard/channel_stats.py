"""Deterministic channel statistics (no AI): per-video performance, title patterns, cadence, monetization checklist."""
from __future__ import annotations

import re
import statistics as st
import time

from .i18n import tr

SHORT_MAX = 180  # seconds (Shorts can be up to 3 minutes)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else 0


def title_features(t: str) -> dict:
    letters = [c for c in t if c.isalpha()]
    upper = sum(1 for c in letters if c.isupper())
    return {
        "len": len(t),
        "has_number": bool(re.search(r"\d", t)),
        "question": ("?" in t) or ("؟" in t),
        "caps_ratio": round(upper / len(letters), 2) if letters else 0,
        "emoji": bool(EMOJI.search(t)),
        "excl": "!" in t,
        "hashtags": t.count("#"),
        "brackets": bool(re.search(r"[\[\(\|]", t)),
    }


def enrich(videos: list[dict], now: float | None = None) -> list[dict]:
    now = now or time.time()
    for v in videos:
        age = max(1.0, (now - v["published"]) / 86400) if v.get("published") else None
        v["age_days"] = round(age, 1) if age else None
        v["is_short"] = 0 < v.get("duration", 0) <= SHORT_MAX
        v["vpd"] = round(v["views"] / age, 1) if age and v.get("views") is not None else None  # views per day
        v["like_rate"] = round(100 * v["likes"] / v["views"], 2) if v.get("likes") is not None and v.get("views") else None
        v["comment_rate"] = round(1000 * v["comments"] / v["views"], 2) if v.get("comments") is not None and v.get("views") else None
        v["tf"] = title_features(v["title"])
    return videos


def compute(channel: dict, videos: list[dict], manual: dict | None = None, now: float | None = None) -> dict:
    """channel: from API (or {'subs':..}); videos: newest first. manual: user-typed Studio numbers."""
    now = now or time.time()
    manual = manual or {}
    videos = enrich(videos, now)
    out: dict = {"n_videos": len(videos)}
    mature = [v for v in videos if v.get("age_days") and v["age_days"] >= 3 and v.get("vpd") is not None]
    longs = [v for v in videos if not v["is_short"]]
    shorts = [v for v in videos if v["is_short"]]
    out["format_mix"] = {"long": len(longs), "short": len(shorts)}
    for name, grp in (("long", [v for v in mature if not v["is_short"]]), ("short", [v for v in mature if v["is_short"]])):
        if grp:
            out[f"{name}_median_views"] = int(_median([v["views"] for v in grp]))
            out[f"{name}_median_vpd"] = round(_median([v["vpd"] for v in grp]), 1)
    # relative performance score per video vs. median of the same format
    for v in mature:
        grp = [x for x in mature if x["is_short"] == v["is_short"]]
        med = _median([x["vpd"] for x in grp]) or 1
        v["rel"] = round(v["vpd"] / med, 2)
    ranked = sorted([v for v in mature if "rel" in v], key=lambda v: -v["rel"])
    out["top"] = [_brief(v) for v in ranked[:5]]
    out["bottom"] = [_brief(v) for v in ranked[-5:][::-1]] if len(ranked) > 5 else []
    # title feature lift: median rel with feature vs without
    lifts = {}
    for key in ("has_number", "question", "emoji", "excl", "brackets"):
        a = [v["rel"] for v in ranked if v["tf"][key]]
        b = [v["rel"] for v in ranked if not v["tf"][key]]
        if len(a) >= 3 and len(b) >= 3:
            lifts[key] = {"with": round(_median(a), 2), "without": round(_median(b), 2), "n_with": len(a)}
    short_t = [v["rel"] for v in ranked if v["tf"]["len"] <= 50]
    long_t = [v["rel"] for v in ranked if v["tf"]["len"] > 50]
    if len(short_t) >= 3 and len(long_t) >= 3:
        lifts["title_len<=50"] = {"with": round(_median(short_t), 2), "without": round(_median(long_t), 2), "n_with": len(short_t)}
    out["title_feature_lift"] = lifts
    out["avg_title_len"] = round(st.mean(v["tf"]["len"] for v in videos), 1) if videos else 0
    out["like_rate_median_pct"] = _median([v["like_rate"] for v in videos])
    out["comments_per_1k_views_median"] = _median([v["comment_rate"] for v in videos])
    # consistency: coefficient of variation of vpd (very high = hit-driven / unpredictable)
    vp = [v["vpd"] for v in mature]
    if len(vp) >= 5 and st.mean(vp) > 0:
        out["vpd_variation"] = round(st.pstdev(vp) / st.mean(vp), 2)
    # cadence
    pubs = sorted(v["published"] for v in videos if v.get("published"))
    if len(pubs) >= 3:
        gaps = [(b - a) / 86400 for a, b in zip(pubs, pubs[1:])]
        out["median_gap_days"] = round(_median(gaps), 1)
        out["max_gap_days"] = round(max(gaps), 1)
    if pubs:
        out["days_since_last_upload"] = round((now - pubs[-1]) / 86400, 1)
    d90 = now - 90 * 86400
    out["uploads_last_90d"] = sum(1 for v in videos if v.get("published", 0) >= d90)
    out["shorts_views_published_last_90d"] = sum(v["views"] for v in shorts if v.get("published", 0) >= d90)
    subs = channel.get("subs")
    if subs and out.get("long_median_views") is not None:
        out["median_long_views_to_subs_pct"] = round(100 * out["long_median_views"] / subs, 1)
    out["monetization_checklist"] = monetization_checklist(channel, out, manual)
    return out


def _brief(v):
    return {"id": v["id"], "title": v["title"], "views": v["views"], "age_days": v["age_days"], "vpd": v["vpd"], "rel": v.get("rel"),
            "format": "short" if v["is_short"] else "long", "duration_s": v["duration"], "like_rate_pct": v["like_rate"]}


def monetization_checklist(channel: dict, s: dict, manual: dict) -> list[dict]:
    """Public YouTube Partner Program basics. Watch hours are private -> only from the creator's own Studio numbers."""
    items = []
    subs = channel.get("subs")

    def add(key, label, status, detail=""):
        items.append({"key": key, "label": label, "status": status, "detail": detail})

    if subs is None:
        add("subs", tr("تعداد سابسکرایبر"), "unknown", tr("کانال تعداد سابسکرایبر رو مخفی کرده"))
    elif subs >= 1000:
        add("subs", tr("۱٬۰۰۰ سابسکرایبر (سطح کامل YPP: درآمد تبلیغات)"), "ok", f"{subs:,}")
    elif subs >= 500:
        add("subs", tr("۵۰۰ سابسکرایبر (سطح اولیه YPP: فقط fan funding و Shopping، بدون درآمد تبلیغات)"), "partial", f"{subs:,} — " + tr("برای درآمد تبلیغات ۱٬۰۰۰ لازمه"))
    else:
        add("subs", tr("حداقل ۵۰۰ سابسکرایبر"), "no", f"{subs:,}")
    wh = manual.get("watch_hours_12m")
    if wh is None:
        add("watch", tr("ساعت watch time در ۱۲ ماه (۴٬۰۰۰ ساعت برای سطح کامل؛ ۳٬۰۰۰ برای سطح اولیه)"), "unknown", tr("عدد دقیق فقط در YouTube Studio هست؛ تو فرم وارد کن"))
    else:
        add("watch", tr("ساعت watch time در ۱۲ ماه"), "ok" if wh >= 4000 else ("partial" if wh >= 3000 else "no"), f"{wh:,.0f} / 4,000")
    sv = manual.get("shorts_views_90d")
    approx = s.get("shorts_views_published_last_90d", 0)
    if sv is None:
        add("shorts", tr("ویوی Shorts در ۹۰ روز (۱۰ میلیون برای سطح کامل؛ ۳ میلیون برای سطح اولیه) — جایگزین watch time"), "unknown",
            tr("تخمین از ویدیوهای ۹۰ روز اخیر:") + f" {approx:,}")
    else:
        add("shorts", tr("ویوی Shorts در ۹۰ روز"), "ok" if sv >= 10_000_000 else ("partial" if sv >= 3_000_000 else "no"), f"{sv:,.0f} / 10,000,000")
    up = s.get("uploads_last_90d", 0)
    add("uploads", tr("حداقل ۳ آپلود عمومی در ۹۰ روز اخیر (شرط سطح اولیه)"), "ok" if up >= 3 else "no", str(up))
    d = s.get("days_since_last_upload")
    if d is not None:
        add("active", tr("فعال بودن کانال (آخرین آپلود)"), "ok" if d <= 60 else ("partial" if d <= 150 else "no"), tr(f"{d:.0f} روز پیش"))
    return items


def parse_manual_list(text: str) -> list[dict]:
    """Manual mode lines:  title | views | duration_seconds(optional) | days_ago(optional)"""
    out = []
    now = time.time()
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        nums = []
        for p in parts[1:]:
            p2 = p.replace(",", "").replace("٬", "")
            try:
                nums.append(float(p2))
            except ValueError:
                nums.append(None)
        views = int(nums[0]) if nums and nums[0] is not None else 0
        dur = int(nums[1]) if len(nums) > 1 and nums[1] is not None else 0
        days = nums[2] if len(nums) > 2 and nums[2] is not None else None
        out.append({"id": f"m{len(out)+1}", "title": parts[0], "views": views, "likes": None, "comments": None, "duration": dur,
                    "published": (now - days * 86400) if days is not None else 0, "thumb_url": "", "tags": [], "desc": "", "lang": ""})
    return out
