"""Background threads so the UI never freezes."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .i18n import DIR, IS_RTL, tr
from . import analysis
from .ai_engine import AIError, get_provider, robust_json
from .local_checks import (Cancelled, best_thumbnail_frames, compress_for_upload, convert_to_vertical, find_ffmpeg,
                           guess_format, media_info, run_local_checks)
from .prompts import ANALYSIS_SYSTEM, TOOLS_SYSTEM, build_analysis_prompt, build_tool_prompt
from .questionnaire import evaluate_answers

GEMINI_OK_EXT = {".mp4", ".mov", ".webm", ".avi", ".mpeg", ".mpg", ".wmv", ".flv", ".3gp", ".m4v"}


class BaseWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def is_cancelled(self):
        return self._cancel

    def run(self):
        try:
            self.done.emit(self.work())
        except Cancelled:
            self.failed.emit(tr("لغو شد."))
        except AIError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(tr(f"خطای غیرمنتظره: {type(e).__name__}: {e}"))

    def work(self):  # pragma: no cover
        raise NotImplementedError


def ensure_ref(settings, path: str, info: dict, ffmpeg: str, progress, cancel, cached: dict | None):
    """Returns an AI reference for the video (uploads / extracts frames if needed)."""
    prov = get_provider(settings)
    if cached and prov.ref_valid(cached):
        progress(100, tr("از آپلود قبلی استفاده شد"))
        return prov, cached
    proxy = None
    tmpdir = None
    try:
        needs = Path(path).suffix.lower() not in GEMINI_OK_EXT
        if prov.name == "gemini" and (settings["compress_before_upload"] or needs):
            tmpdir = tempfile.TemporaryDirectory(prefix="ytguard_")
            proxy = compress_for_upload(path, ffmpeg, str(Path(tmpdir.name) / "proxy.mp4"),
                                        int(settings["compress_height"] or 480),
                                        lambda p, t: progress(p, t), info["duration"], cancel)
        ref = prov.prepare(path, info["duration"], progress, cancel, proxy_file=proxy)
    finally:
        if tmpdir:
            tmpdir.cleanup()
    return prov, ref


class AnalyzeWorker(BaseWorker):
    """Full check: local -> questionnaire -> AI."""

    def __init__(self, settings, history, path, fmt, answers, use_ai=True, cached_ref=None):
        super().__init__()
        self.settings, self.history, self.path, self.fmt = settings, history, path, fmt
        self.answers, self.use_ai, self.cached_ref = answers, use_ai, cached_ref
        self.ref = None

    def work(self):
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        if not ffmpeg:
            raise AIError(tr("ffmpeg پیدا نشد. در تنظیمات مسیرش رو بده یا `pip install imageio-ffmpeg` رو اجرا کن."))
        others = self.history.other_fingerprints(self.path)
        local = run_local_checks(self.path, self.fmt, ffmpeg, others,
                                 lambda p, t: self.progress.emit(int(p * 0.35), t), self.is_cancelled)
        q_findings = evaluate_answers(self.answers, self.fmt)
        ai, ai_err, model = None, "", ""
        if self.use_ai:
            try:
                prov, ref = ensure_ref(self.settings, self.path, local["info"], ffmpeg,
                                       lambda p, t: self.progress.emit(35 + int(p * 0.35), t), self.is_cancelled, self.cached_ref)
                self.ref = ref
                self.progress.emit(72, tr("AI در حال بررسی ویدیو با قوانین یوتیوب…"))
                summary = {"duration_sec": round(local["info"]["duration"]), "resolution": f'{local["info"]["width"]}x{local["info"]["height"]}',
                           "fps": round(local["info"]["fps"], 1), "orientation": local["info"]["orientation"],
                           "loudness_lufs": local["audio"].get("lufs"), "metrics": local["metrics"],
                           "metadata_flags": local["meta"],
                           "local_findings": [f["issue"] for f in local["findings"]][:15]}
                prompt = build_analysis_prompt(self.fmt, self.answers, summary,
                                               frames_only=not prov.supports_audio,
                                               frame_times=[t for t, _ in ref.get("frames", [])])
                text = prov.generate(ref, ANALYSIS_SYSTEM, prompt, True, self.is_cancelled)
                ai = analysis.normalize_ai(robust_json(text))
                model = self.settings["gemini_model"] if prov.name == "gemini" else self.settings["openai_model"]
                self.progress.emit(97, tr("ساخت گزارش…"))
            except Cancelled:
                raise
            except AIError as e:
                ai_err = str(e)
        rep = analysis.assemble_report(path=self.path, fmt=self.fmt, answers=self.answers, local=local, q_findings=q_findings,
                                       ai=ai, ai_error=ai_err, provider=self.settings["provider"], model=model)
        rep["fingerprints"] = local["fingerprints"]
        rep["ref"] = self.ref
        self.progress.emit(100, tr("تمام شد"))
        return rep


class FollowUpWorker(BaseWorker):
    """Re-run only the AI step with the creator's answers to the AI's questions."""

    def __init__(self, settings, report: dict, clarifications: list[dict], ref):
        super().__init__()
        self.settings, self.report, self.clar, self.ref = settings, report, clarifications, ref

    def work(self):
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        rep = self.report
        prov, ref = ensure_ref(self.settings, rep["path"], rep["info"], ffmpeg, lambda p, t: self.progress.emit(int(p * 0.5), t),
                               self.is_cancelled, self.ref)
        self.progress.emit(55, tr("AI با پاسخ‌های تو دوباره بررسی می‌کنه…"))
        summary = {"duration_sec": round(rep["info"]["duration"]), "metrics": rep["metrics"], "metadata_flags": rep["meta"]}
        prev = {k: rep["ai"][k] for k in ("overall_risk_score", "summary", "findings", "disclosure") if rep.get("ai")}
        prompt = build_analysis_prompt(rep["format"], rep["answers"], summary, self.clar, prev,
                                       frames_only=not prov.supports_audio, frame_times=[t for t, _ in ref.get("frames", [])])
        ai = analysis.normalize_ai(robust_json(prov.generate(ref, ANALYSIS_SYSTEM, prompt, True, self.is_cancelled)))
        ai["follow_up_questions"] = []  # one round only – avoid endless interrogation
        new = analysis.assemble_report(path=rep["path"], fmt=rep["format"], answers=rep["answers"],
                                       local={"info": rep["info"], "metrics": rep["metrics"], "audio": rep["audio"], "meta": rep["meta"],
                                              "findings": rep["local_findings"]},
                                       q_findings=rep["q_findings"], ai=ai, provider=rep["provider"], model=rep.get("model", ""))
        new["fingerprints"] = rep.get("fingerprints", [])
        new["ref"] = ref
        new["clarifications"] = self.clar
        return new


class ToolWorker(BaseWorker):
    def __init__(self, settings, path, tool_id, out_lang, extra, cached_ref=None):
        super().__init__()
        self.settings, self.path, self.tool_id, self.out_lang, self.extra, self.cached_ref = settings, path, tool_id, out_lang, extra, cached_ref

    def work(self):
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        if not ffmpeg:
            raise AIError(tr("ffmpeg پیدا نشد."))
        info = media_info(self.path, ffmpeg)
        prov, ref = ensure_ref(self.settings, self.path, info, ffmpeg, lambda p, t: self.progress.emit(int(p * 0.7), t),
                               self.is_cancelled, self.cached_ref)
        self.progress.emit(75, tr("AI در حال نوشتن…"))
        text = prov.generate(ref, TOOLS_SYSTEM, build_tool_prompt(self.tool_id, self.out_lang, self.extra), False,
                             self.is_cancelled, temperature=0.7)
        return {"text": text, "ref": ref}


class ThumbWorker(BaseWorker):
    def __init__(self, settings, path, out_dir, count=6):
        super().__init__()
        self.settings, self.path, self.out_dir, self.count = settings, path, out_dir, count

    def work(self):
        import cv2
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        info = media_info(self.path, ffmpeg)
        self.progress.emit(20, tr("جستجوی بهترین فریم‌ها…"))
        picks = best_thumbnail_frames(self.path, info["duration"], self.count)
        outs = []
        Path(self.out_dir).mkdir(parents=True, exist_ok=True)
        for i, (t, fr, sc) in enumerate(picks):
            p = str(Path(self.out_dir) / f"{Path(self.path).stem}_thumb_{i+1}_{int(t)}s.jpg")
            cv2.imwrite(p, fr, [cv2.IMWRITE_JPEG_QUALITY, 95])
            outs.append((t, sc, p))
        return outs


class VerticalWorker(BaseWorker):
    def __init__(self, settings, path, out_path, start, end, mode):
        super().__init__()
        self.settings, self.path, self.out_path, self.start, self.end, self.mode = settings, path, out_path, start, end, mode

    def work(self):
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        info = media_info(self.path, ffmpeg)
        convert_to_vertical(self.path, ffmpeg, self.out_path, self.start, self.end, self.mode,
                            lambda p, t: self.progress.emit(p, t), info["duration"], self.is_cancelled)
        return self.out_path


class ModelsWorker(BaseWorker):
    def __init__(self, settings, which: str | None = None):
        super().__init__()
        self.settings, self.which = settings, which

    def work(self):
        from .ai_engine import GeminiProvider, OpenAICompatProvider
        cls = {"gemini": GeminiProvider, "openai": OpenAICompatProvider}.get(self.which or self.settings["provider"])
        return cls(self.settings).list_models()


class InfoWorker(BaseWorker):
    """Probe a file quickly (for the drop zone) without running checks."""

    def __init__(self, settings, path):
        super().__init__()
        self.settings, self.path = settings, path

    def work(self):
        ffmpeg = find_ffmpeg(self.settings["ffmpeg_path"])
        if not ffmpeg:
            raise AIError(tr("ffmpeg پیدا نشد. «pip install imageio-ffmpeg» رو اجرا کن یا مسیر ffmpeg رو در تنظیمات بده."))
        info = media_info(self.path, ffmpeg)
        fmt, amb = guess_format(info)
        return {"info": info, "fmt": fmt, "ambiguous": amb}
