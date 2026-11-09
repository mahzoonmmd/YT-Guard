"""AI providers.

* GeminiProvider  – native video understanding (video + audio) through the Gemini API File API. Free tier exists.
* OpenAICompatProvider – any OpenAI-style /chat/completions endpoint (OpenRouter free models, Groq, local LM Studio…).
  Sends sampled frames only (no audio), so the analysis is weaker; use it as a fallback.
"""
from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Callable

import requests

from .local_checks import Cancelled, extract_frames_b64

ProgressCb = Callable[[int, str], None]


class AIError(Exception):
    """Error with a Persian, user-facing message."""


def _session(settings) -> requests.Session:
    s = requests.Session()
    proxy = (settings["proxy"] or "").strip()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def robust_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    try:
        return json.loads(t)
    except Exception:
        pass
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(t[a:b + 1])
        except Exception:
            pass
    raise AIError("پاسخ AI قابل خواندن (JSON) نبود. دوباره تلاش کن یا مدل دیگری انتخاب کن.")


def _explain_http(status: int, body: str, provider: str) -> str:
    if body.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        m = re.search(r"<title>(.*?)</title>", body, re.S | re.I)
        title = (m.group(1).strip() if m else "HTML")[:80]
        return (f"سرور به‌جای پاسخ API یک صفحه HTML برگردوند ({status}: {title}). معمولاً یعنی آدرس Base URL اشتباهه، "
                "پراکسی/VPN درخواست رو خراب می‌کنه، یا درخواست درست ساخته نشده. در تنظیمات Base URL رو روی "
                "https://generativelanguage.googleapis.com بذار و پراکسی رو چک کن.")
    low = body.lower()
    if "location is not supported" in low or "not available in your country" in low or "unsupported_country" in low:
        return ("سرویس از موقعیت (IP) فعلی شما پشتیبانی نمی‌کنه. VPN/Proxy فعال کن و آدرس پراکسی رو در تنظیمات → Proxy وارد کن "
                "(مثلاً http://127.0.0.1:10809).")
    if status in (400, 401, 403) and ("api key" in low or "api_key" in low or "unauthenticated" in low or "invalid" in low and "key" in low):
        return "کلید API نامعتبر است. در تنظیمات دوباره کپی/پیست کن."
    if status == 403:
        return "دسترسی رد شد (۴۰۳). ممکنه کلید محدود شده باشه یا IP شما بلاک شده باشه؛ پراکسی/VPN رو امتحان کن."
    if status == 404:
        return "مدل پیدا نشد (۴۰۴). در تنظیمات دکمه «دریافت لیست مدل‌ها» رو بزن و یک مدل معتبر انتخاب کن."
    if status == 413:
        return "حجم درخواست خیلی زیاده. «کم‌حجم‌سازی قبل از ارسال» رو در تنظیمات روشن کن."
    if status == 429:
        return "سهمیه رایگان (Rate limit) تموم شده. چند دقیقه صبر کن یا فردا امتحان کن یا مدل سبک‌تر (Flash-Lite) انتخاب کن."
    if status >= 500:
        return f"سرور {provider} موقتاً در دسترس نیست ({status}). بعداً تلاش کن."
    return f"خطای {provider} ({status}): {body[:300]}"


class BaseProvider:
    name = "base"
    supports_audio = False

    def __init__(self, settings):
        self.s = settings
        self.http = _session(settings)

    def _check(self, cancel):
        if cancel and cancel():
            raise Cancelled()

    def _request(self, method, url, retries=3, cancel=None, **kw):
        kw.setdefault("timeout", (20, 300))
        last = None
        for attempt in range(retries + 1):
            self._check(cancel)
            try:
                r = self.http.request(method, url, **kw)
            except requests.exceptions.SSLError:
                raise AIError("خطای SSL در اتصال. اگه VPN/Proxy داری تنظیمش رو چک کن.")
            except requests.exceptions.ProxyError:
                raise AIError("اتصال به Proxy ناموفق بود. آدرس پراکسی در تنظیمات رو چک کن.")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                last = AIError("اتصال به اینترنت/سرویس برقرار نشد. اگه در ایران هستی VPN یا Proxy لازمه (تنظیمات → Proxy).")
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = 8 * (attempt + 1)
                m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                if m:
                    wait = min(60, int(m[1]) + 1)
                for _ in range(wait):
                    self._check(cancel)
                    time.sleep(1)
                continue
            if r.status_code >= 400:
                raise AIError(_explain_http(r.status_code, r.text, self.name))
            return r
        raise last or AIError("ارتباط با سرویس ناموفق بود")

    # interface -------------------------------------------------------------
    def prepare(self, path: str, duration: float, progress: ProgressCb, cancel=None, proxy_file: str | None = None) -> dict:
        raise NotImplementedError

    def generate(self, ref: dict, system: str, prompt: str, json_mode: bool, cancel=None, temperature=0.2) -> str:
        raise NotImplementedError

    def list_models(self) -> list[str]:
        raise NotImplementedError

    def ref_valid(self, ref: dict) -> bool:
        return bool(ref) and ref.get("provider") == self.name


class GeminiProvider(BaseProvider):
    name = "gemini"
    supports_audio = True

    @property
    def base(self):
        return (self.s["gemini_base"] or "https://generativelanguage.googleapis.com").rstrip("/")

    @property
    def headers(self):
        key = (self.s["gemini_key"] or "").strip()
        if not key:
            raise AIError("کلید Gemini API وارد نشده. در تنظیمات وارد کن (رایگان از aistudio.google.com/apikey).")
        return {"x-goog-api-key": key}

    def list_models(self):
        r = self._request("GET", f"{self.base}/v1beta/models?pageSize=200", headers=self.headers, timeout=(15, 60))
        out = []
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []) and "gemini" in m["name"]:
                out.append(m["name"].split("/", 1)[1])
        return sorted(out)

    def ref_valid(self, ref):
        return super().ref_valid(ref) and (time.time() - ref.get("ts", 0)) < 40 * 3600 and bool(ref.get("uri"))

    def prepare(self, path, duration, progress, cancel=None, proxy_file=None):
        up = proxy_file or path
        size = Path(up).stat().st_size
        mime = "video/mp4" if proxy_file else (_guess_mime(up))
        progress(0, "شروع آپلود ویدیو به Gemini…")
        h = dict(self.headers)
        h.update({"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                  "X-Goog-Upload-Header-Content-Length": str(size), "X-Goog-Upload-Header-Content-Type": mime,
                  "Content-Type": "application/json"})
        r = self._request("POST", f"{self.base}/upload/v1beta/files", cancel=cancel, headers=h,
                          data=json.dumps({"file": {"display_name": Path(path).name[:80]}}), timeout=(20, 60))
        url = r.headers.get("X-Goog-Upload-URL") or r.headers.get("x-goog-upload-url")
        if not url:
            raise AIError("آدرس آپلود از Gemini دریافت نشد.")

        outer = self

        class _Body:
            """File-like streaming body with a known length -> requests sends Content-Length (no chunked)."""
            def __len__(self):
                return size

            def __iter__(self):
                sent = 0
                with open(up, "rb") as f:
                    while True:
                        outer._check(cancel)
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        sent += len(chunk)
                        progress(int(sent / size * 100), f"آپلود ویدیو… {sent // (1024 * 1024)}/{max(1, size // (1024 * 1024))} MB")
                        yield chunk

        h2 = {"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"}
        r = self._request("POST", url, retries=0, cancel=cancel, headers=h2, data=_Body(), timeout=(20, 900))
        info = r.json().get("file", {})
        name = info.get("name")
        if not name:
            raise AIError("پاسخ آپلود Gemini نامعتبر بود.")
        # wait for processing
        progress(100, "Gemini در حال پردازش ویدیو…")
        t0 = time.time()
        while info.get("state", "ACTIVE") == "PROCESSING":
            if time.time() - t0 > 900:
                raise AIError("پردازش ویدیو در Gemini خیلی طول کشید.")
            for _ in range(3):
                self._check(cancel)
                time.sleep(1)
            info = self._request("GET", f"{self.base}/v1beta/{name}", cancel=cancel, headers=self.headers, timeout=(15, 60)).json()
        if info.get("state") == "FAILED":
            raise AIError("Gemini نتونست این ویدیو رو پردازش کنه (فرمت/کدک نامعتبر؟).")
        return {"provider": "gemini", "name": name, "uri": info.get("uri"), "mime": info.get("mimeType", mime), "ts": time.time()}

    def generate(self, ref, system, prompt, json_mode, cancel=None, temperature=0.2):
        model = (self.s["gemini_model"] or "gemini-3.5-flash").strip()
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [
                {"file_data": {"mime_type": ref["mime"], "file_uri": ref["uri"]}},  # video first, text after (per Google's guidance)
                {"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 16384},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        r = self._request("POST", f"{self.base}/v1beta/models/{model}:generateContent", cancel=cancel,
                          headers={**self.headers, "Content-Type": "application/json"}, data=json.dumps(body), timeout=(20, 600))
        j = r.json()
        try:
            cand = j["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        except Exception:
            fb = j.get("promptFeedback", {})
            if fb.get("blockReason"):
                raise AIError(f"Gemini پاسخ رو مسدود کرد ({fb['blockReason']}). محتوای ویدیو ممکنه از فیلتر ایمنی رد نشده باشه.")
            raise AIError("پاسخ خالی از Gemini دریافت شد.")
        if not text.strip():
            raise AIError("پاسخ خالی از Gemini دریافت شد (احتمالاً فیلتر ایمنی).")
        return text


class OpenAICompatProvider(BaseProvider):
    name = "openai"
    supports_audio = False

    @property
    def base(self):
        return (self.s["openai_base"] or "").rstrip("/")

    @property
    def headers(self):
        h = {"Content-Type": "application/json"}
        if (self.s["openai_key"] or "").strip():
            h["Authorization"] = "Bearer " + self.s["openai_key"].strip()
        return h

    def list_models(self):
        r = self._request("GET", f"{self.base}/models", headers=self.headers, timeout=(15, 60))
        data = r.json().get("data", [])
        return sorted(m.get("id", "") for m in data if m.get("id"))

    def ref_valid(self, ref):
        return super().ref_valid(ref) and bool(ref.get("frames"))

    def prepare(self, path, duration, progress, cancel=None, proxy_file=None):
        progress(10, "استخراج فریم‌ها برای مدل تصویری…")
        n = int(self.s["frames_for_openai"] or 12)
        frames = extract_frames_b64(path, duration, n=n)
        if not frames:
            raise AIError("استخراج فریم از ویدیو ممکن نشد.")
        progress(100, "فریم‌ها آماده شد")
        return {"provider": "openai", "duration": duration, "ts": time.time(),
                "frames": [(t, base64.b64encode(b).decode()) for t, b in frames]}

    def generate(self, ref, system, prompt, json_mode, cancel=None, temperature=0.2):
        model = (self.s["openai_model"] or "").strip()
        if not model:
            raise AIError("نام مدل OpenAI-compatible در تنظیمات وارد نشده (مدلی که تصویر پشتیبانی کنه).")
        content = [{"type": "text", "text": "Frames sampled from the video at seconds: "
                    + ", ".join(f"{t:.0f}" for t, _ in ref["frames"]) + "\n\n" + prompt}]
        for t, b in ref["frames"]:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}})
        body = {"model": model, "temperature": temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = self._request("POST", f"{self.base}/chat/completions", cancel=cancel, headers=self.headers,
                              data=json.dumps(body), timeout=(20, 600))
        except AIError as e:
            if json_mode and "400" in str(e):
                body.pop("response_format", None)
                r = self._request("POST", f"{self.base}/chat/completions", cancel=cancel, headers=self.headers,
                                  data=json.dumps(body), timeout=(20, 600))
            else:
                raise
        try:
            return r.json()["choices"][0]["message"]["content"] or ""
        except Exception:
            raise AIError("پاسخ نامعتبر از سرویس OpenAI-compatible.")


def _guess_mime(p: str) -> str:
    return {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".mkv": "video/x-matroska",
            ".avi": "video/x-msvideo", ".m4v": "video/mp4", ".wmv": "video/x-ms-wmv", ".flv": "video/x-flv",
            ".mpg": "video/mpeg", ".mpeg": "video/mpeg", ".3gp": "video/3gpp"}.get(Path(p).suffix.lower(), "video/mp4")


def get_provider(settings) -> BaseProvider:
    return OpenAICompatProvider(settings) if settings["provider"] == "openai" else GeminiProvider(settings)
