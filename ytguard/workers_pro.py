"""Workers for the reach-diagnosis, idea-check and channel-review features."""
from __future__ import annotations

from pathlib import Path

from .ai_engine import AIError, get_provider, robust_json
from .channel_stats import compute, parse_manual_list
from .i18n import tr
from .local_checks import find_ffmpeg, media_info
from .prompts_pro import COMMON, build_channel_prompt, build_diagnose_prompt, build_idea_prompt
from .thumb_check import analyze as thumb_analyze, load_and_prepare
from .workers import BaseWorker, ensure_ref
from .youtube_api import YouTubeAPI


def pre_findings(d: dict) -> list[str]:
    """Deterministic checks from the numbers the creator typed (Studio benchmarks are rules of thumb, not YouTube rules)."""
    out = []
    m = d.get("metrics") or {}
    fmt = d["format"]
    t = d.get("title") or ""
    if t:
        if len(t) > 70:
            out.append(f"Title is {len(t)} chars (>70 gets cut off in search/mobile).")
        if len(t) < 20:
            out.append(f"Title is very short ({len(t)} chars): little keyword/curiosity context.")
        letters = [c for c in t if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
            out.append("Title is mostly UPPERCASE.")
    ctr = m.get("ctr_pct")
    if ctr is not None:
        out.append(f"CTR {ctr}%: " + ("below ~2% is usually weak packaging (title/thumbnail)." if ctr < 2 else
                                      "2-10% is a typical range; above ~8% is strong." if ctr < 8 else "strong."))
    avp = m.get("avg_viewed_pct")
    if avp is not None:
        lo = 70 if fmt == "short" else 35
        out.append(f"Average viewed {avp}%: " + ("below typical -> retention/hook problem." if avp < lo else "healthy for this format."))
    sw = m.get("viewed_vs_swiped_pct")
    if sw is not None:
        out.append(f"Shorts viewed-vs-swiped {sw}%: " + ("below ~70% means the first seconds lose people." if sw < 70 else "good."))
    v, days = m.get("views"), m.get("days_online")
    if v is not None and days:
        out.append(f"{v} views in {days} days ({v / max(days, 1):.0f}/day).")
        if days < 2:
            out.append("Very new video: most videos get their real distribution over 1-4 weeks; judge cautiously.")
    return out


class DiagnoseWorker(BaseWorker):
    def __init__(self, settings, data: dict, video_path: str | None, thumb_path: str | None, cached_ref, video_report: dict | None):
        super().__init__()
        self.settings, self.d, self.video, self.thumb, self.cached, self.vr = settings, data, video_path, thumb_path, cached_ref, video_report

    def work(self):
        d = dict(self.d)
        images, ref, prov = [], None, get_provider(self.settings)
        if self.thumb:
            self.progress.emit(5, tr("تحلیل تامبنیل…"))
            ta = thumb_analyze(self.thumb)
            d["thumb_metrics"] = ta
            jpg, _ = load_and_prepare(self.thumb)
            images.append(("THUMBNAIL (as uploaded):", "image/jpeg", jpg))
            d["has_thumb"] = True
        d["pre_findings"] = pre_findings(d)
        if self.vr:
            d["video_report"] = self.vr
        if self.video:
            ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
            if not ffmpeg:
                raise AIError(tr("ffmpeg پیدا نشد."))
            info = media_info(self.video, ffmpeg)
            prov, ref = ensure_ref(self.settings, self.video, info, ffmpeg, lambda p, t: self.progress.emit(10 + int(p * 0.6), t),
                                   self.is_cancelled, self.cached)
            d["has_video"] = True
        self.progress.emit(75, tr("AI در حال تشخیص علت‌ها…"))
        text = prov.generate(ref, COMMON, build_diagnose_prompt(d), True, self.is_cancelled, temperature=0.4, images=images)
        res = robust_json(text)
        self.progress.emit(100, tr("تمام شد"))
        return {"ai": res, "thumb": d.get("thumb_metrics"), "pre": d["pre_findings"], "ref": ref}


class IdeaWorker(BaseWorker):
    def __init__(self, settings, data: dict):
        super().__init__()
        self.settings, self.d = settings, data

    def work(self):
        prov = get_provider(self.settings)
        self.progress.emit(30, tr("AI در حال بررسی ایده…"))
        res = robust_json(prov.generate(None, COMMON, build_idea_prompt(self.d), True, self.is_cancelled, temperature=0.5))
        self.progress.emit(100, tr("تمام شد"))
        return res


class ChannelWorker(BaseWorker):
    """mode='api' (YouTube Data API) or 'manual' (pasted list)."""

    def __init__(self, settings, mode: str, channel_ref: str, manual_text: str, manual_nums: dict, limit: int = 50):
        super().__init__()
        self.settings, self.mode, self.ref, self.text, self.nums, self.limit = settings, mode, channel_ref, manual_text, manual_nums, limit

    def work(self):
        images: list = []
        if self.mode == "api":
            yt = YouTubeAPI(self.settings)
            self.progress.emit(8, tr("پیدا کردن کانال…"))
            ch = yt.resolve_channel(self.ref)
            self.progress.emit(20, tr("دریافت لیست ویدیوها…"))
            videos = yt.recent_videos(ch["uploads_playlist"], self.limit)
            if not videos:
                raise AIError(tr("این کانال ویدیوی عمومی نداره."))
        else:
            ch = {"title": self.nums.get("name") or "(manual)", "subs": self.nums.get("subs"), "total_views": None, "video_count": None,
                  "description": "", "country": "", "keywords": ""}
            videos = parse_manual_list(self.text)
            if len(videos) < 3:
                raise AIError(tr("حداقل ۳ ویدیو وارد کن (هر خط: عنوان | ویو | مدت‌ثانیه | چند روز پیش)."))
        self._check()
        manual = {k: v for k, v in self.nums.items() if k in ("watch_hours_12m", "shorts_views_90d") and v is not None}
        self.progress.emit(35, tr("محاسبه آمار…"))
        stats = compute(ch, videos, manual)
        if self.mode == "api":
            picks = (stats["top"][:3] + stats["bottom"][:3])
            by_id = {v["id"]: v for v in videos}
            for i, b in enumerate(picks):
                self._check()
                self.progress.emit(40 + i * 4, tr("دانلود تامبنیل‌ها…"))
                v = by_id.get(b["id"])
                data = yt.download_thumb(v["thumb_url"]) if v and v.get("thumb_url") else None
                if data:
                    tag = "TOP" if i < len(stats["top"][:3]) else "WORST"
                    images.append((f'{tag} performer thumbnail — title: "{b["title"]}", views/day {b["vpd"]}, relative {b["rel"]}x median:',
                                   "image/jpeg", data))
        self._check()
        self.progress.emit(70, tr("AI در حال تحلیل کانال…"))
        prov = get_provider(self.settings)
        text = prov.generate(None, COMMON, build_channel_prompt(ch, stats, videos, manual, bool(images), self.mode), True,
                             self.is_cancelled, temperature=0.4, images=images)
        res = robust_json(text)
        self.progress.emit(100, tr("تمام شد"))
        return {"ai": res, "channel": ch, "stats": stats, "n_thumbs": len(images)}

    def _check(self):
        from .local_checks import Cancelled
        if self.is_cancelled():
            raise Cancelled()
