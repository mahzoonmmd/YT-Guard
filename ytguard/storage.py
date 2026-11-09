"""Settings + history persistence (plain JSON under the user's config dir)."""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path


def data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "YTGuard"
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_SETTINGS = {
    "theme": "dark",  # "dark" | "light"
    "provider": "gemini",  # "gemini" | "openai"
    "gemini_key": "",
    "gemini_model": "gemini-3.5-flash",
    "gemini_base": "https://generativelanguage.googleapis.com",
    "openai_base": "https://openrouter.ai/api/v1",
    "openai_key": "",
    "openai_model": "",
    "proxy": "",  # e.g. http://127.0.0.1:10809 or socks5h://127.0.0.1:10808
    "compress_before_upload": True,
    "compress_height": 480,
    "frames_for_openai": 12,
    "ffmpeg_path": "",
    "report_language": "fa",
    "language": "fa",
    "prereqs_skipped": False,
    "youtube_key": "",
    "youtube_base": "https://www.googleapis.com/youtube/v3",
}


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = path or (data_dir() / "settings.json")
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        try:
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            pass

    def save(self):
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def __getitem__(self, k):
        return self.data.get(k, DEFAULT_SETTINGS.get(k))

    def __setitem__(self, k, v):
        self.data[k] = v


class History:
    """Keeps past checks. Each entry stores the full report and frame fingerprints
    (used to detect near-duplicate / template-like videos across your own uploads)."""

    def __init__(self, path: Path | None = None):
        self.path = path or (data_dir() / "history.json")
        self.items: list[dict] = []
        self.load()

    def load(self):
        try:
            self.items = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.items = []

    def save(self):
        try:
            self.path.write_text(json.dumps(self.items, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def add(self, entry: dict) -> dict:
        entry.setdefault("id", uuid.uuid4().hex[:10])
        entry.setdefault("ts", time.time())
        # same file checked again -> replace
        self.items = [i for i in self.items if i.get("path") != entry.get("path")]
        self.items.insert(0, entry)
        self.items = self.items[:200]
        self.save()
        return entry

    def remove(self, entry_id: str):
        self.items = [i for i in self.items if i.get("id") != entry_id]
        self.save()

    def find_by_path(self, path: str):
        for i in self.items:
            if i.get("path") == path:
                return i
        return None

    def other_fingerprints(self, exclude_path: str):
        return [(i, i.get("fingerprints") or []) for i in self.items if i.get("path") != exclude_path and i.get("fingerprints")]
