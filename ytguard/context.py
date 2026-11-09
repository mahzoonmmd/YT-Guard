from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .i18n import DIR, IS_RTL, tr
from .storage import History, Settings


class AppContext(QObject):
    """Shared state between pages."""
    videoChanged = pyqtSignal(str)      # path of the video currently loaded
    themeChanged = pyqtSignal(str)
    historyChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.history = History()
        self.refs: dict[str, dict] = {}   # path -> AI reference (uploaded file / frames), reused between checks and tools
        self.current_path: str = ""
        self.current_info: dict | None = None

    def set_video(self, path: str, info: dict | None = None):
        self.current_path, self.current_info = path, info
        self.videoChanged.emit(path)

    def cached_ref(self, path: str):
        ref = self.refs.get(path)
        if ref:
            return ref
        h = self.history.find_by_path(path)
        if h and h.get("report", {}).get("ref") and h["report"]["ref"].get("provider") == "gemini":
            return h["report"]["ref"]
        return None

    def ai_ready(self) -> tuple[bool, str]:
        s = self.settings
        if s["provider"] == "gemini":
            return (bool((s["gemini_key"] or "").strip()), tr("کلید Gemini API در تنظیمات وارد نشده"))
        ok = bool((s["openai_base"] or "").strip()) and bool((s["openai_model"] or "").strip())
        return ok, tr("آدرس/مدل OpenAI-compatible در تنظیمات کامل نیست")
