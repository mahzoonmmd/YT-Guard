"""Minimal YouTube Data API v3 client (free key, ~10k units/day; this app needs ~3-5 units per channel)."""
from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from .ai_engine import AIError
from .i18n import tr

DEFAULT_BASE = "https://www.googleapis.com/youtube/v3"


def parse_iso_duration(d: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    dd, h, mi, sec = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + sec


def parse_ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def parse_channel_ref(text: str) -> tuple[str, str]:
    """-> (kind, value) kind in id|handle|user|search"""
    t = (text or "").strip()
    if not t:
        raise AIError(tr("آدرس یا @handle کانال رو وارد کن."))
    m = re.search(r"youtube\.com/channel/(UC[\w-]{20,})", t)
    if m:
        return "id", m[1]
    m = re.search(r"youtube\.com/(@[\w.\-%]+)", t)
    if m:
        return "handle", m[1]
    m = re.search(r"youtube\.com/user/([\w.\-]+)", t)
    if m:
        return "user", m[1]
    m = re.search(r"youtube\.com/(?:c|)/?([\w.\-%]+)$", t)
    if re.fullmatch(r"UC[\w-]{20,}", t):
        return "id", t
    if t.startswith("@"):
        return "handle", t
    if re.fullmatch(r"[\w.\-]+", t):
        return "handle", "@" + t
    return "search", t


class YouTubeAPI:
    def __init__(self, settings):
        self.key = (settings["youtube_key"] or "").strip()
        self.base = (settings["youtube_base"] or DEFAULT_BASE).rstrip("/")
        self.http = requests.Session()
        proxy = (settings["proxy"] or "").strip()
        if proxy:
            self.http.proxies = {"http": proxy, "https": proxy}
        if not self.key:
            raise AIError(tr("کلید YouTube Data API در تنظیمات وارد نشده."))

    def _get(self, path: str, **params) -> dict:
        params["key"] = self.key
        try:
            r = self.http.get(f"{self.base}/{path}", params=params, timeout=(15, 60))
        except requests.exceptions.ProxyError:
            raise AIError(tr("اتصال به Proxy ناموفق بود. آدرس پراکسی در تنظیمات رو چک کن."))
        except requests.exceptions.RequestException:
            raise AIError(tr("اتصال به YouTube API برقرار نشد. VPN/Proxy رو چک کن."))
        if r.status_code >= 400:
            try:
                err = r.json()["error"]
                reason = (err.get("errors") or [{}])[0].get("reason", "")
                msg = err.get("message", "")
            except Exception:
                reason, msg = "", r.text[:200]
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise AIError(tr("سهمیه روزانه YouTube API تموم شده؛ فردا امتحان کن."))
            if reason in ("keyInvalid", "badRequest") or "API key" in msg:
                raise AIError(tr("کلید YouTube Data API نامعتبره یا YouTube Data API v3 در پروژه‌اش فعال نیست."))
            if reason == "accessNotConfigured" or r.status_code == 403:
                raise AIError(tr("دسترسی رد شد: YouTube Data API v3 رو در Google Cloud Console برای این کلید فعال کن.") + f" ({reason or r.status_code})")
            raise AIError(tr("خطای YouTube API") + f" ({r.status_code}): {msg[:200]}")
        return r.json()

    def resolve_channel(self, text: str) -> dict:
        kind, val = parse_channel_ref(text)
        part = "snippet,statistics,contentDetails,brandingSettings"
        if kind == "id":
            j = self._get("channels", part=part, id=val)
        elif kind == "handle":
            j = self._get("channels", part=part, forHandle=val)
        elif kind == "user":
            j = self._get("channels", part=part, forUsername=val)
        else:
            s = self._get("search", part="snippet", q=val, type="channel", maxResults=1)
            items = s.get("items") or []
            if not items:
                raise AIError(tr("کانالی پیدا نشد."))
            j = self._get("channels", part=part, id=items[0]["snippet"]["channelId"])
        items = j.get("items") or []
        if not items:
            raise AIError(tr("کانالی پیدا نشد. آدرس/handle رو چک کن."))
        c = items[0]
        st = c.get("statistics", {})
        sn = c.get("snippet", {})
        return {
            "id": c["id"], "title": sn.get("title", ""), "description": (sn.get("description") or "")[:600],
            "country": sn.get("country", ""), "created": parse_ts(sn.get("publishedAt", "")),
            "subs": None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0)),
            "total_views": int(st.get("viewCount", 0)), "video_count": int(st.get("videoCount", 0)),
            "uploads_playlist": c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
            "keywords": (c.get("brandingSettings", {}).get("channel", {}).get("keywords") or "")[:300],
        }

    def recent_videos(self, uploads_playlist: str, limit: int = 50) -> list[dict]:
        ids: list[str] = []
        page = None
        while len(ids) < limit:
            j = self._get("playlistItems", part="contentDetails", playlistId=uploads_playlist, maxResults=min(50, limit - len(ids)),
                          **({"pageToken": page} if page else {}))
            ids += [i["contentDetails"]["videoId"] for i in j.get("items", [])]
            page = j.get("nextPageToken")
            if not page:
                break
        out = []
        for i in range(0, len(ids), 50):
            j = self._get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
            for v in j.get("items", []):
                sn, st = v.get("snippet", {}), v.get("statistics", {})
                th = sn.get("thumbnails", {})
                url = (th.get("medium") or th.get("high") or th.get("default") or {}).get("url", "")
                out.append({
                    "id": v["id"], "title": sn.get("title", ""), "published": parse_ts(sn.get("publishedAt", "")),
                    "duration": parse_iso_duration(v.get("contentDetails", {}).get("duration", "")),
                    "views": int(st.get("viewCount", 0)), "likes": int(st["likeCount"]) if "likeCount" in st else None,
                    "comments": int(st["commentCount"]) if "commentCount" in st else None,
                    "thumb_url": url, "tags": (sn.get("tags") or [])[:8], "desc": (sn.get("description") or "")[:160],
                    "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "",
                })
        out.sort(key=lambda v: -v["published"])
        return out

    def download_thumb(self, url: str) -> bytes | None:
        try:
            r = self.http.get(url, timeout=(10, 30))
            return r.content if r.status_code == 200 else None
        except Exception:
            return None


def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()
