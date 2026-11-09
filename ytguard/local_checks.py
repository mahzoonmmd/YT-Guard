"""Local (offline) analysis: ffmpeg/OpenCV based checks that need no AI and no internet."""
from __future__ import annotations

from .i18n import DIR, IS_RTL, tr

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

CREATE_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".3gp"}

AI_TOOL_MARKERS = ["sora", "veo", "runway", "pika", "kling", "luma", "hailuo", "minimax", "heygen",
                   "synthesia", "d-id", "elevenlabs", "genmo", "firefly", "midjourney", "stable diffusion", "dall-e"]
OTHER_APP_MARKERS = ["tiktok", "douyin", "instagram", "capcut", "inshot", "kinemaster", "vn editor", "snapchat", "likee"]

ProgressCb = Callable[[int, str], None]


class Cancelled(Exception):
    pass


# --------------------------------------------------------------------------- binaries
_ffmpeg_cache: dict[str, Optional[str]] = {}


def find_ffmpeg(custom: str = "") -> Optional[str]:
    key = custom or ""
    if key in _ffmpeg_cache and _ffmpeg_cache[key]:
        return _ffmpeg_cache[key]
    cands = []
    if custom:
        cands.append(custom)
    try:
        from .storage import data_dir
        cands.append(str(data_dir() / "ffmpeg" / ("ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg")))
    except Exception:
        pass
    w = shutil.which("ffmpeg")
    if w:
        cands.append(w)
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    for rel in ("ffmpeg/ffmpeg.exe", "ffmpeg/bin/ffmpeg.exe", "ffmpeg.exe", "ffmpeg/ffmpeg"):
        cands.append(str(base / rel))
    try:
        import imageio_ffmpeg  # bundled binary via pip

        cands.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    for c in cands:
        if c and Path(c).exists():
            _ffmpeg_cache[key] = c
            return c
    return None


def find_ffprobe(ffmpeg: str) -> Optional[str]:
    w = shutil.which("ffprobe")
    if w:
        return w
    p = Path(ffmpeg)
    for name in ("ffprobe.exe", "ffprobe"):
        q = p.with_name(name)
        if q.exists():
            return str(q)
    return None


def _run(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=CREATE_NO_WINDOW)


def fmt_ts(sec: float) -> str:
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------- media info
def media_info(path: str, ffmpeg: str) -> dict:
    info = {"path": path, "name": Path(path).name, "size": os.path.getsize(path), "duration": 0.0,
            "width": 0, "height": 0, "fps": 0.0, "vcodec": "", "acodec": "", "has_audio": False,
            "bitrate": 0, "tags": {}, "rotation": 0}
    probe = find_ffprobe(ffmpeg)
    done = False
    if probe:
        try:
            r = _run([probe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path], 120)
            j = json.loads(r.stdout or "{}")
            fmt = j.get("format", {})
            info["duration"] = float(fmt.get("duration") or 0)
            info["bitrate"] = int(float(fmt.get("bit_rate") or 0))
            info["tags"].update({k.lower(): str(v) for k, v in (fmt.get("tags") or {}).items()})
            for s in j.get("streams", []):
                if s.get("codec_type") == "video" and not info["vcodec"]:
                    info["vcodec"] = s.get("codec_name", "")
                    info["width"] = int(s.get("width") or 0)
                    info["height"] = int(s.get("height") or 0)
                    num, _, den = (s.get("avg_frame_rate") or "0/1").partition("/")
                    info["fps"] = float(num) / float(den or 1) if float(den or 1) else 0.0
                    info["tags"].update({k.lower(): str(v) for k, v in (s.get("tags") or {}).items()})
                    rot = (s.get("tags") or {}).get("rotate")
                    for sd in s.get("side_data_list", []) or []:
                        if "rotation" in sd:
                            rot = sd["rotation"]
                    try:
                        info["rotation"] = int(float(rot or 0)) % 360
                    except Exception:
                        pass
                elif s.get("codec_type") == "audio":
                    info["has_audio"] = True
                    info["acodec"] = info["acodec"] or s.get("codec_name", "")
            done = info["width"] > 0
        except Exception:
            done = False
    if not done:  # fallback: parse `ffmpeg -i`
        r = _run([ffmpeg, "-hide_banner", "-i", path], 120)
        txt = r.stderr
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
        if m:
            info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        m = re.search(r"bitrate:\s*(\d+)\s*kb/s", txt)
        if m:
            info["bitrate"] = int(m[1]) * 1000
        m = re.search(r"Video:\s*(\w+).*?,\s*(\d{2,5})x(\d{2,5})", txt)
        if m:
            info["vcodec"], info["width"], info["height"] = m[1], int(m[2]), int(m[3])
        m = re.search(r"([\d.]+)\s*fps", txt)
        if m:
            info["fps"] = float(m[1])
        info["has_audio"] = bool(re.search(r"Stream #.*Audio:", txt))
        m = re.search(r"Audio:\s*(\w+)", txt)
        if m:
            info["acodec"] = m[1]
        m = re.search(r"rotation of (-?[\d.]+) degrees", txt)
        if m:
            info["rotation"] = int(abs(float(m[1]))) % 360
        for k, v in re.findall(r"^\s{4,6}(\w+)\s*:\s*(.+)$", txt, re.M):
            info["tags"][k.lower()] = v.strip()
    if info["rotation"] in (90, 270):
        info["width"], info["height"] = info["height"], info["width"]
    if not info["width"]:
        cap = cv2.VideoCapture(path)
        info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        info["fps"] = cap.get(cv2.CAP_PROP_FPS) or 0
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not info["duration"] and info["fps"]:
            info["duration"] = n / info["fps"]
        cap.release()
    w, h = info["width"], info["height"]
    info["aspect"] = round(w / h, 3) if h else 0
    info["orientation"] = "vertical" if h > w * 1.05 else ("horizontal" if w > h * 1.05 else "square")
    return info


def guess_format(info: dict) -> tuple[str, bool]:
    """Returns (format, ambiguous). format in {'short','long'}."""
    dur, ori = info["duration"], info["orientation"]
    if ori in ("vertical", "square") and dur <= 180:
        return "short", False
    if ori == "horizontal" and dur > 180:
        return "long", False
    if ori == "horizontal" and dur <= 180:
        return "long", True  # horizontal short clip: probably a long video but could be a trailer / non-vertical Short
    return "long", True  # vertical but > 3 min


# --------------------------------------------------------------------------- ffmpeg filters
def audio_analysis(path: str, ffmpeg: str) -> dict:
    out = {"lufs": None, "true_peak": None, "lra": None, "silences": [], "silence_total": 0.0}
    r = _run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
              "ebur128=peak=true:framelog=quiet,silencedetect=n=-45dB:d=1.5", "-f", "null", "-"])
    txt = r.stderr
    m = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?[\d.]+) LUFS", txt)
    if m:
        out["lufs"] = float(m[1])
    m = re.search(r"Loudness range:\s*\n\s*LRA:\s*([\d.]+) LU", txt)
    if m:
        out["lra"] = float(m[1])
    m = re.search(r"True peak:\s*\n\s*Peak:\s*(-?[\d.]+) dBFS", txt)
    if m:
        out["true_peak"] = float(m[1])
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", txt)]
    durs = [float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", txt)]
    for i, s in enumerate(starts):
        d = durs[i] if i < len(durs) else 0.0
        out["silences"].append((max(0.0, s), d))
        out["silence_total"] += d
    return out


def black_analysis(path: str, ffmpeg: str) -> dict:
    r = _run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-an", "-vf",
              "scale=320:-2,blackdetect=d=0.5:pix_th=0.10", "-f", "null", "-"])
    segs = []
    for s, e, d in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", r.stderr):
        segs.append((float(s), float(d)))
    return {"segments": segs, "total": sum(d for _, d in segs)}


# --------------------------------------------------------------------------- frames
def _dhash(gray: np.ndarray) -> int:
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    return int("".join("1" if b else "0" for b in diff.flatten()), 2)


def sample_frames(path: str, duration: float, max_samples: int = 240, cancel: Callable[[], bool] = lambda: False):
    """Evenly sample frames; returns list of (t, gray64, hash)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or int(duration * fps)
    n = int(min(max_samples, max(8, duration)))
    out = []
    for i in range(n):
        if cancel():
            raise Cancelled()
        t = duration * (i + 0.5) / n
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(total - 1, int(t * fps)))
        ok, frame = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        out.append((t, cv2.resize(g, (64, 36)), _dhash(g)))
    cap.release()
    return out


def start_motion(path: str, fps_guess: float = 25.0) -> float:
    """Mean abs difference between frames in the first 3 seconds (0 = frozen)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or fps_guess
    prev, diffs, idx = None, [], 0
    step = max(1, int(fps / 4))
    while idx < fps * 3:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            g = cv2.cvtColor(cv2.resize(frame, (96, 54)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            if prev is not None:
                diffs.append(float(np.mean(np.abs(g - prev))))
            prev = g
        idx += 1
    cap.release()
    return float(np.mean(diffs)) if diffs else 0.0


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def similarity(new_fp: list[str], old_fp: list[str]) -> float:
    if not new_fp or not old_fp:
        return 0.0
    old = [int(x, 16) for x in old_fp]
    hits = 0
    for h in new_fp:
        v = int(h, 16)
        if any(hamming(v, o) <= 5 for o in old):
            hits += 1
    return hits / len(new_fp)


# --------------------------------------------------------------------------- metadata
def metadata_scan(path: str, tags: dict) -> dict:
    blob = " ".join(f"{k}={v}" for k, v in tags.items()).lower()
    ai_hits = sorted({m for m in AI_TOOL_MARKERS if m in blob})
    app_hits = sorted({m for m in OTHER_APP_MARKERS if m in blob})
    c2pa = False
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(4 * 1024 * 1024)
            f.seek(max(0, size - 4 * 1024 * 1024))
            tail = f.read()
        data = head + tail
        c2pa = b"c2pa" in data or (b"jumb" in data and b"cai" in data.lower())
        low = data.lower()
        for m in AI_TOOL_MARKERS:
            if len(m) > 4 and m.encode() in low[:200000] and m not in ai_hits:
                ai_hits.append(m)
    except Exception:
        pass
    return {"ai_markers": ai_hits, "app_markers": app_hits, "c2pa": c2pa}


# --------------------------------------------------------------------------- orchestrator
def F(rule_id, severity, issue, evidence="", fix="", timestamp=None, source="local"):
    return {"rule_id": rule_id, "severity": severity, "issue": issue, "evidence": evidence,
            "fix": fix, "timestamp": timestamp, "source": source}


def run_local_checks(path: str, fmt: str, ffmpeg: str, history_others=(), progress: ProgressCb = lambda p, t: None,
                     cancel: Callable[[], bool] = lambda: False) -> dict:
    progress(2, tr("خواندن مشخصات ویدیو…"))
    info = media_info(path, ffmpeg)
    if cancel():
        raise Cancelled()
    findings: list[dict] = []
    dur = info["duration"]

    # ---- format rules
    short_side = min(info["width"], info["height"])
    if fmt == "short":
        if info["orientation"] == "horizontal":
            findings.append(F("shorts_format", "high", tr("ویدیو افقی است ولی به‌عنوان Short انتخاب شده"),
                              f'{info["width"]}×{info["height"]}',
                              tr("برای Shorts نسبت ۹:۱۶ (یا حداقل مربع) بساز؛ در تب ابزارها می‌تونی تبدیل ۹:۱۶ بگیری.")))
        if dur > 180:
            findings.append(F("shorts_format", "high", tr("مدت ویدیو از ۳ دقیقه بیشتر است و Short محسوب نمی‌شه"),
                              f"{fmt_ts(dur)}", tr("ویدیو رو زیر ۳ دقیقه ببر یا به‌عنوان ویدیوی لانگ آپلود کن.")))
        if short_side and short_side < 1080:
            findings.append(F("technical_quality", "low", tr("رزولوشن کمتر از 1080×1920"),
                              f'{info["width"]}×{info["height"]}', tr("با رزولوشن 1080×1920 خروجی بگیر.")))
    else:
        if info["orientation"] == "vertical":
            findings.append(F("long_format", "medium", tr("ویدیو عمودی است ولی به‌عنوان لانگ انتخاب شده"),
                              f'{info["width"]}×{info["height"]}', tr("ویدیوی لانگ بهتره افقی 16:9 باشه؛ ویدیوی عمودی زیر ۳ دقیقه Short می‌شه.")))
        if dur < 480:
            findings.append(F("long_format", "info", tr("کمتر از ۸ دقیقه: امکان Mid-roll ads نداره"),
                              f"{fmt_ts(dur)}", tr("اگه هدفت درآمد آگهی بیشتره، محتوا باید بالای ۸ دقیقه (و با ماندگاری خوب) باشه.")))
        if short_side and short_side < 720:
            findings.append(F("technical_quality", "medium", tr("رزولوشن کمتر از 720p"), f'{info["width"]}×{info["height"]}',
                              tr("حداقل 1080p خروجی بگیر.")))
        elif short_side and short_side < 1080:
            findings.append(F("technical_quality", "low", tr("رزولوشن کمتر از 1080p"), f'{info["width"]}×{info["height"]}',
                              tr("اگه منبع اجازه می‌ده 1080p یا 4K خروجی بگیر.")))
    if info["fps"] and info["fps"] < 23:
        findings.append(F("technical_quality", "low", tr("نرخ فریم پایین"), f'{info["fps"]:.1f} fps', tr("حداقل 24 یا 30 fps.")))

    # ---- audio
    progress(10, tr("تحلیل صدا (لودنس و سکوت)…"))
    audio = {}
    if info["has_audio"]:
        audio = audio_analysis(path, ffmpeg)
        lufs, tp = audio["lufs"], audio["true_peak"]
        if lufs is not None:
            if lufs < -22:
                findings.append(F("technical_quality", "medium", tr("صدا خیلی آرام است"), f"{lufs:.1f} LUFS",
                                  tr("لودنس رو به حدود -14 LUFS برسون.")))
            elif lufs > -9:
                findings.append(F("technical_quality", "medium", tr("صدا خیلی بلند/فشرده است"), f"{lufs:.1f} LUFS",
                                  tr("یوتیوب صدا رو پایین می‌کشه و کیفیت خراب می‌شه؛ حدود -14 LUFS.")))
        if tp is not None and tp > -0.5:
            findings.append(F("technical_quality", "low", tr("ریسک کلیپ شدن صدا (True peak)"), f"{tp:.1f} dBFS", tr("پیک رو زیر -1 dBTP نگه دار.")))
        if dur and audio["silence_total"] / dur > 0.15:
            findings.append(F("technical_quality", "medium", tr("سکوت زیاد در ویدیو"),
                              tr(f'{audio["silence_total"]:.0f}s از {dur:.0f}s'), tr("بخش‌های سکوت رو کوتاه کن (Jump cut).")))
        for s, d in audio["silences"]:
            if s < 1.0 and d >= 1.5:
                findings.append(F("technical_quality", "medium", tr("سکوت در شروع ویدیو (هوک ضعیف)"), f"{d:.1f}s", tr("از ثانیه اول صدا/موسیقی/جمله اصلی بیار."), fmt_ts(s)))
                break
    else:
        findings.append(F("technical_quality", "medium" if fmt == "short" else "low", tr("ویدیو ترک صدا ندارد"), "",
                          tr("صدا/موزیک مجاز اضافه کن؛ ویدیوی بی‌صدا ماندگاری پایینی داره.")))
    if cancel():
        raise Cancelled()

    # ---- black frames
    progress(30, tr("بررسی فریم سیاه…"))
    black = black_analysis(path, ffmpeg)
    if black["segments"]:
        s0, d0 = black["segments"][0]
        if s0 < 0.5:
            findings.append(F("technical_quality", "medium", tr("ویدیو با فریم سیاه شروع می‌شه"), f"{d0:.1f}s", tr("کات رو از اولین فریم محتوا شروع کن."), fmt_ts(s0)))
        if dur and black["total"] / dur > 0.05:
            findings.append(F("technical_quality", "medium", tr("فریم سیاه زیاد در ویدیو"), f'{black["total"]:.0f}s', tr("بخش‌های سیاه رو حذف کن.")))

    # ---- frames
    progress(40, tr("نمونه‌برداری از فریم‌ها…"))
    frames = sample_frames(path, dur, cancel=cancel)
    metrics = {}
    if len(frames) >= 4:
        diffs = [float(np.mean(np.abs(frames[i][1].astype(np.float32) - frames[i - 1][1].astype(np.float32))))
                 for i in range(1, len(frames))]
        static_ratio = sum(1 for d in diffs if d < 1.5) / len(diffs)
        cuts = sum(1 for d in diffs if d > 28)
        metrics.update({"static_ratio": round(static_ratio, 3), "approx_scene_changes": cuts})
        if static_ratio > 0.85:
            findings.append(F("inauthentic_content", "high", tr("تصویر تقریباً ثابت (شبیه اسلایدشو/تصویر ثابت)"),
                              tr(f"{static_ratio*100:.0f}% فریم‌ها تقریباً بدون تغییر"),
                              tr("تنوع بصری، B-roll، حرکت و ادیت روایی اضافه کن؛ ویدیوهای تصویر ثابت + صدا ریسک غیراصیل بودن دارن.")))
        elif static_ratio > 0.6:
            findings.append(F("inauthentic_content", "medium", tr("بخش بزرگی از ویدیو بدون تغییر بصری است"),
                              tr(f"{static_ratio*100:.0f}% فریم‌ها تقریباً بدون تغییر"), tr("تنوع بصری بیشتر اضافه کن.")))
    sm = start_motion(path, info["fps"] or 25.0)
    metrics["start_motion"] = round(sm, 2)
    if fmt == "short" and sm < 1.0:
        findings.append(F("shorts_format", "low", tr("سه ثانیه اول تقریباً بی‌حرکت است (هوک ضعیف)"), tr(f"میانگین تغییر {sm:.2f}"),
                          tr("از ثانیه صفر حرکت، متن یا جمله جذاب بیار."), "00:00"))
    progress(70, tr("اثر انگشت فریم‌ها و مقایسه با ویدیوهای قبلی…"))
    fingerprints = [f"{h:016x}" for _, _, h in frames]
    best = (0.0, None)
    for entry, fps_ in history_others:
        s = similarity(fingerprints, fps_)
        if s > best[0]:
            best = (s, entry)
    metrics["max_similarity"] = round(best[0], 3)
    if best[1] is not None and best[0] >= 0.5:
        sev = "high" if best[0] >= 0.75 else "medium"
        findings.append(F("inauthentic_content", sev, tr("این ویدیو خیلی شبیه یکی از ویدیوهای قبلی‌ات است"),
                          tr(f'{best[0]*100:.0f}% شباهت با «{best[1].get("name", "?")}»'),
                          tr("ویدیوهای تقریباً یکسان که فقط جزئیات کوچک فرق دارن نشانه محتوای تکراری/قالبی‌اند؛ ساختار و بصری رو متفاوت کن.")))

    # ---- metadata
    progress(85, tr("بررسی متادیتا (C2PA، ابزارهای AI، اپ‌های دیگر)…"))
    meta = metadata_scan(path, info["tags"])
    if meta["c2pa"]:
        findings.append(F("synthetic_disclosure", "medium", tr("متادیتای C2PA / Content Credentials در فایل پیدا شد"),
                          tr("فایل ممکنه حاوی اطلاعات منشأ (Provenance) باشه"),
                          tr("اگه فایل کاملاً تولیدشده با AI هست، یوتیوب برچسب رو خودش می‌زنه و قابل حذف نیست؛ بهتره خودت هم افشا کنی.")))
    if meta["ai_markers"]:
        findings.append(F("synthetic_disclosure", "medium", tr("نشانه ابزار تولید AI در متادیتای فایل"),
                          tr("، ").join(meta["ai_markers"]), tr("اگه محتوا واقع‌نماست، تیک Altered or synthetic content رو بزن.")))
    if meta["app_markers"]:
        findings.append(F("other_platform_watermark", "low", tr("نشانه اپ/پلتفرم دیگر در متادیتا"),
                          tr("، ").join(meta["app_markers"]),
                          tr("اگه واترمارک روی تصویر هست، خروجی بدون واترمارک از پروژه خودت بگیر.")))
    progress(100, tr("تحلیل محلی تمام شد"))
    return {"info": info, "audio": audio, "black": black, "metrics": metrics, "meta": meta,
            "findings": findings, "fingerprints": fingerprints}


# --------------------------------------------------------------------------- helpers for AI step / tools
def compress_for_upload(path: str, ffmpeg: str, out_path: str, height: int = 480,
                        progress: ProgressCb = lambda p, t: None, duration: float = 0.0,
                        cancel: Callable[[], bool] = lambda: False) -> str:
    """Small proxy file for upload: AI samples ~1 fps anyway, so 480p / low bitrate loses nothing useful."""
    vf = f"scale=-2:{height}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2"
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1", "-nostats", "-i", path,
           "-vf", vf, "-r", "10", "-c:v", "libx264", "-preset", "veryfast", "-crf", "32",
           "-c:a", "aac", "-b:a", "64k", "-ac", "1", "-movflags", "+faststart", out_path]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, creationflags=CREATE_NO_WINDOW)
    try:
        for line in p.stdout:  # type: ignore[union-attr]
            if cancel():
                p.kill()
                raise Cancelled()
            if line.startswith("out_time_ms=") and duration:
                try:
                    t = int(line.split("=")[1]) / 1_000_000
                    progress(min(99, int(t / duration * 100)), tr("کم‌حجم‌سازی نسخه برای ارسال…"))
                except ValueError:
                    pass
    finally:
        p.wait()
    if p.returncode != 0 or not Path(out_path).exists():
        raise RuntimeError(tr("کم‌حجم‌سازی ویدیو با ffmpeg ناموفق بود"))
    return out_path


def extract_frames_b64(path: str, duration: float, n: int = 12, max_side: int = 512) -> list[tuple[float, bytes]]:
    """JPEG frames (t, bytes) evenly spaced – used by the OpenAI-compatible provider."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    out = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        sc = max_side / max(h, w)
        if sc < 1:
            fr = cv2.resize(fr, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", fr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            out.append((t, buf.tobytes()))
    cap.release()
    return out


def best_thumbnail_frames(path: str, duration: float, count: int = 6, samples: int = 90) -> list[tuple[float, np.ndarray, float]]:
    """Pick sharp, well-exposed, colourful frames. Returns (t, bgr_frame, score)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or int(duration * fps)
    scored = []
    for i in range(samples):
        t = duration * (i + 0.5) / samples
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(total - 1, int(t * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        small = cv2.resize(fr, (320, int(320 * fr.shape[0] / fr.shape[1])))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        bright = g.mean()
        sat = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)[..., 1].mean()
        exposure = 1 - abs(bright - 120) / 120
        score = min(sharp, 600) / 600 * 0.5 + max(exposure, 0) * 0.3 + min(sat, 120) / 120 * 0.2
        scored.append((t, fr, float(score)))
    cap.release()
    scored.sort(key=lambda x: -x[2])
    chosen: list = []
    for item in scored:  # keep picks at least 3% of the duration apart
        if all(abs(item[0] - c[0]) > duration * 0.03 for c in chosen):
            chosen.append(item)
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda x: x[0])


def convert_to_vertical(path: str, ffmpeg: str, out_path: str, start: float = 0, end: float = 0, mode: str = "blur",
                        progress: ProgressCb = lambda p, t: None, duration: float = 0.0,
                        cancel: Callable[[], bool] = lambda: False) -> str:
    """Horizontal -> 1080x1920. mode 'blur' = blurred background + centered video, 'crop' = centre crop."""
    if mode == "crop":
        vf = "scale=-2:1920,crop=1080:1920"
    else:
        vf = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5[bg];"
              "[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1", "-nostats"]
    if start > 0:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    seg = (end - start) if end > start else 0
    if seg > 0:
        cmd += ["-t", str(seg)]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out_path]
    total = seg or max(duration - start, 1)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, creationflags=CREATE_NO_WINDOW)
    try:
        for line in p.stdout:  # type: ignore[union-attr]
            if cancel():
                p.kill()
                raise Cancelled()
            if line.startswith("out_time_ms="):
                try:
                    progress(min(99, int(int(line.split("=")[1]) / 1_000_000 / total * 100)), tr("در حال تبدیل به ۹:۱۶…"))
                except ValueError:
                    pass
    finally:
        p.wait()
    if p.returncode != 0:
        raise RuntimeError(tr("تبدیل ۹:۱۶ با ffmpeg ناموفق بود"))
    return out_path
