"""Local (no AI) thumbnail checks with OpenCV: technical spec + readability at tiny sizes."""
from __future__ import annotations

import os

import cv2
import numpy as np

from .i18n import tr


def load_and_prepare(path: str, max_w: int = 1280) -> tuple[bytes, np.ndarray]:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(tr("تصویر خونده نشد."))
    h, w = img.shape[:2]
    if w > max_w:
        img = cv2.resize(img, (max_w, int(h * max_w / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return buf.tobytes(), img


def analyze(path: str) -> dict:
    raw = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(tr("تصویر خونده نشد."))
    h, w = img.shape[:2]
    size_mb = os.path.getsize(path) / 1e6
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # YouTube shows thumbnails as small as ~168x94 in sidebars
    tiny = cv2.resize(gray, (168, 94), interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(gray, 100, 200)
    tiny_edges = cv2.Canny(tiny, 80, 160)
    m = {
        "width": w, "height": h, "aspect": round(w / h, 3), "file_mb": round(size_mb, 2),
        "brightness": round(float(gray.mean()) / 255, 2),
        "contrast": round(float(gray.std()) / 128, 2),
        "saturation": round(float(hsv[:, :, 1].mean()) / 255, 2),
        "clutter_edge_density": round(float((edges > 0).mean()), 3),
        "tiny_detail_kept": round(float((tiny_edges > 0).mean()) / max(1e-6, float((edges > 0).mean())), 2),
    }
    # faces
    try:
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if casc.empty():
            raise RuntimeError("cascade missing")
        faces = casc.detectMultiScale(gray, 1.15, 5, minSize=(max(30, w // 25), max(30, w // 25)))
        m["faces"] = len(faces)
        m["largest_face_area_pct"] = round(100 * max((fw * fh for _, _, fw, fh in faces), default=0) / (w * h), 1)
    except Exception:
        m["faces"] = None
    findings = []

    def add(sev, text):
        findings.append({"severity": sev, "text": text})

    if abs(m["aspect"] - 16 / 9) > 0.05:
        add("medium", tr("نسبت تصویر ۱۶:۹ نیست (پیشنهاد: ۱۲۸۰×۷۲۰)؛ ممکنه کادر بشه."))
    if w < 1280:
        add("medium", tr("رزولوشن کمتر از ۱۲۸۰×۷۲۰ است؛ کیفیت پایین به نظر میاد."))
    if size_mb > 2:
        add("high", tr("حجم فایل بیشتر از ۲ مگابایته و یوتیوب قبولش نمی‌کنه."))
    if m["brightness"] < 0.25:
        add("medium", tr("تصویر خیلی تیره‌ست؛ در فید کم‌نور و گم میشه."))
    elif m["brightness"] > 0.85:
        add("low", tr("تصویر خیلی روشنه؛ با پس‌زمینه سفید یوتیوب قاطی میشه."))
    if m["contrast"] < 0.25:
        add("medium", tr("کنتراست پایینه؛ سوژه از پس‌زمینه جدا نمی‌شه."))
    if m["clutter_edge_density"] > 0.12:
        add("medium", tr("تصویر شلوغه (جزئیات زیاد)؛ در اندازه کوچک خونده نمی‌شه."))
    if m["tiny_detail_kept"] < 0.25 and m["clutter_edge_density"] > 0.04:
        add("low", tr("جزئیات و متن در اندازه کوچک (موبایل) احتمالاً ناخوانا می‌شه."))
    if m.get("faces") == 0:
        add("info", tr("چهره‌ای تشخیص داده نشد؛ چهره/احساس معمولاً CTR رو بالا می‌بره (اگه به موضوع می‌خوره)."))
    elif m.get("faces") and m["largest_face_area_pct"] < 4:
        add("low", tr("چهره خیلی کوچکه؛ بزرگ‌ترش کن."))
    if m["saturation"] < 0.12:
        add("low", tr("رنگ‌ها کم‌جان‌اند؛ کمی اشباع/رنگ بیشتر توجه رو جلب می‌کنه."))
    return {"metrics": m, "findings": findings}
