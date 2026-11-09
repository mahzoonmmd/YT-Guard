"""Prerequisites: detection + download/install logic (runs in a worker thread, reports progress)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from .i18n import tr
from .storage import data_dir

IS_WIN = sys.platform.startswith("win")
VC_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
FFMPEG_URLS = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
]


def ffmpeg_dir() -> Path:
    return data_dir() / "ffmpeg"


def _exe(name: str) -> str:
    return name + (".exe" if IS_WIN else "")


# ------------------------------------------------------------------ detection
def has_vcredist() -> bool:
    if not IS_WIN:
        return True
    try:
        import winreg
        for view in (winreg.KEY_WOW64_64KEY,):
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
                                0, winreg.KEY_READ | view) as k:
                return int(winreg.QueryValueEx(k, "Installed")[0]) == 1
    except Exception:
        return False


def has_ffmpeg(custom: str = "") -> bool:
    if custom and Path(custom).exists():
        return True
    d = ffmpeg_dir()
    if (d / _exe("ffmpeg")).exists() and (d / _exe("ffprobe")).exists():
        return True
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def missing_required(settings) -> list[str]:
    out = []
    if not has_vcredist():
        out.append("vcredist")
    if not has_ffmpeg(settings["ffmpeg_path"]):
        out.append("ffmpeg")
    return out


# ------------------------------------------------------------------ steps
# key, title, weight (share of the overall percentage), required
STEPS = [
    ("internet", "بررسی اتصال اینترنت", 5, False),
    ("gemini", "بررسی دسترسی به Gemini (برای موتور AI)", 5, False),
    ("vcredist", "Microsoft Visual C++ Runtime (لازم برای اجرای برنامه)", 30, True),
    ("ffmpeg", "FFmpeg و FFprobe (تحلیل و پردازش ویدیو)", 60, True),
]


class Skip(Exception):
    """Step already satisfied."""


class PrereqWorker(QThread):
    stepState = pyqtSignal(str, str, str)   # key, state: run|ok|skip|fail|warn, message
    stepProgress = pyqtSignal(str, int)     # key, 0..100
    overall = pyqtSignal(int)
    allDone = pyqtSignal(bool)              # True when every required step is OK

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._pct = {k: 0 for k, *_ in STEPS}
        self._cancel = False

    def cancel(self):
        self._cancel = True

    # -- helpers
    def _session(self):
        s = requests.Session()
        p = (self.settings["proxy"] or "").strip()
        if p:
            s.proxies = {"http": p, "https": p}
        return s

    def _set(self, key, pct):
        self._pct[key] = pct
        self.stepProgress.emit(key, pct)
        total = sum(w for _, _, w, _ in STEPS)
        self.overall.emit(int(sum(self._pct[k] * w for k, _, w, _ in STEPS) / total))

    def _download(self, key, urls, dest: Path, scale=(0, 70)) -> None:
        if os.environ.get("YTG_TEST_URL_" + key.upper()):
            urls = [os.environ["YTG_TEST_URL_" + key.upper()]]
        sess = self._session()
        last = None
        for url in urls:
            try:
                with sess.get(url, stream=True, timeout=(15, 60), allow_redirects=True) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("Content-Length") or 0)
                    got = 0
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(256 * 1024):
                            if self._cancel:
                                raise RuntimeError(tr("لغو شد"))
                            f.write(chunk)
                            got += len(chunk)
                            if total:
                                self._set(key, scale[0] + int((scale[1] - scale[0]) * got / total))
                return
            except Exception as e:  # try next mirror
                last = e
        raise RuntimeError(tr("دانلود ناموفق بود. اینترنت/VPN/Proxy رو چک کن") + f" ({type(last).__name__})")

    # -- steps
    def do_internet(self):
        r = self._session().get("https://www.gstatic.com/generate_204", timeout=10)
        if r.status_code >= 400:
            raise RuntimeError("HTTP %d" % r.status_code)

    def do_gemini(self):
        self._session().get("https://generativelanguage.googleapis.com/", timeout=10)

    def do_vcredist(self):
        if has_vcredist():
            raise Skip
        if not IS_WIN:
            raise Skip
        tmp = Path(tempfile.mkdtemp(prefix="ytg_vc_"))
        exe = tmp / "vc_redist.x64.exe"
        self._download("vcredist", [VC_URL], exe, (0, 70))
        self._set("vcredist", 75)
        code = _run_elevated(str(exe), "/install /quiet /norestart")
        shutil.rmtree(tmp, ignore_errors=True)
        if code not in (0, 1638, 3010):
            raise RuntimeError(tr("نصب انجام نشد (کد %d). اگه پنجره UAC رو رد کردی دوباره امتحان کن") % code)
        self._set("vcredist", 100)

    def do_ffmpeg(self):
        if has_ffmpeg(self.settings["ffmpeg_path"]):
            raise Skip
        if not IS_WIN and not os.environ.get("YTG_TEST_URL_FFMPEG"):
            raise RuntimeError(tr("روی این سیستم ffmpeg رو دستی نصب کن"))
        tmp = Path(tempfile.mkdtemp(prefix="ytg_ff_"))
        z = tmp / "ffmpeg.zip"
        try:
            self._download("ffmpeg", FFMPEG_URLS, z, (0, 80))
            self._set("ffmpeg", 82)
            dest = ffmpeg_dir(); dest.mkdir(parents=True, exist_ok=True)
            found = 0
            with zipfile.ZipFile(z) as zf:
                for name in zf.namelist():
                    base = Path(name).name
                    if base in (_exe("ffmpeg"), _exe("ffprobe")):
                        with zf.open(name) as src, open(dest / base, "wb") as out:
                            shutil.copyfileobj(src, out)
                        found += 1
            if found < 2:
                raise RuntimeError(tr("فایل‌های ffmpeg داخل آرشیو پیدا نشد"))
            if not IS_WIN:
                for b in (_exe("ffmpeg"), _exe("ffprobe")):
                    (dest / b).chmod(0o755)
            self._set("ffmpeg", 95)
            subprocess.run([str(dest / _exe("ffmpeg")), "-version"], capture_output=True, timeout=30,
                           creationflags=0x08000000 if IS_WIN else 0, check=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self._set("ffmpeg", 100)

    # -- main
    def run(self):
        ok_required = True
        for key, _title, _w, required in STEPS:
            if self._cancel:
                break
            self.stepState.emit(key, "run", "")
            try:
                getattr(self, "do_" + key)()
                self._set(key, 100)
                self.stepState.emit(key, "ok", "")
            except Skip:
                self._set(key, 100)
                self.stepState.emit(key, "skip", tr("از قبل نصب بود"))
            except Exception as e:
                msg = str(e) or type(e).__name__
                self._set(key, 100)
                if required:
                    ok_required = False
                    self.stepState.emit(key, "fail", msg)
                else:
                    msg = tr("در دسترس نیست؛ VPN/Proxy لازمه") if key in ("internet", "gemini") else msg
                    self.stepState.emit(key, "warn", msg)
        self.overall.emit(100 if ok_required else min(99, sum(self._pct.values()) // len(self._pct)))
        self.allDone.emit(ok_required and not self._cancel)


def _run_elevated(exe: str, args: str) -> int:
    """Run an installer with UAC elevation and wait for its exit code (Windows)."""
    import ctypes
    from ctypes import wintypes

    class SEI(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]

    info = SEI()
    info.cbSize = ctypes.sizeof(SEI)
    info.fMask = 0x40  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = exe
    info.lpParameters = args
    info.nShow = 0
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return -1  # user declined UAC
    ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
    code = wintypes.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(info.hProcess)
    return int(code.value)
