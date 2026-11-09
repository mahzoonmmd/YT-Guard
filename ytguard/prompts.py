"""Prompt templates. Instructions are English (more reliable); all user-visible output is Persian."""
from __future__ import annotations

import json

from .i18n import DIR, IS_RTL, LANG, tr
from .knowledge import rules_for_prompt

OUT_LANG = "English" if LANG == "en" else "Persian (Farsi)"

ANALYSIS_SYSTEM = """You are a YouTube policy pre-check reviewer helping a creator BEFORE they upload.
You are given the full video (or sampled frames) plus context from the creator and local measurements.
Rules:
- Judge ONLY against the rule list provided. Cite evidence from the video: a MM:SS timestamp whenever possible.
- Never invent things you cannot see/hear. If unsure, say so and lower confidence. Do not claim to run Content ID:
  copyright findings are only SUSPICIONS (recognizable commercial music, film/TV/game/sports footage, logos, cartoon characters).
- AI-generated media detection is probabilistic. Give confidence 0-1 and say what signals you used (voice prosody, texture
  artifacts, impossible physics, text glitches, uniform lighting, etc.).
- Consider both long-form and Shorts criteria depending on the format.
- Think about WATCH-TIME problems too (weak hook in first 3s, dead air, repetitive visuals, wall-of-text subtitles) and
  monetization problems (inauthentic/mass-produced, reused content, advertiser-unfriendly content).
- Ask follow_up_questions ONLY if the answer would change the verdict (max 4, short, with 2-4 answer options each).
- All human-readable text values MUST be in {OUT_LANG}. Keep English technical terms (Content ID, Shorts, hook, YPP...) as-is.
- This is a risk assessment, not legal advice, and not a guarantee of how YouTube will act.
- Output ONLY valid JSON, no markdown fences.""".replace("{OUT_LANG}", OUT_LANG)

ANALYSIS_SCHEMA_EXAMPLE = {
    "detected_format": "short | long",
    "summary": tr("۲-۳ جمله درباره‌ی محتوای ویدیو"),
    "language_of_video": "fa | en | ...",
    "overall_risk_score": 0,
    "ai_usage": {"likely_ai_voice": False, "likely_ai_visuals": False, "likely_ai_music": False,
                 "realistic_enough_to_mislead": False, "confidence": 0.0, "evidence": "..."},
    "disclosure": {"required": "yes | no | maybe", "reason": "...", "suggested_description_text": "..."},
    "findings": [{"rule_id": "one of the rule ids", "severity": "high | medium | low", "timestamp": "MM:SS or null",
                  "issue": "...", "evidence": "...", "fix": "..."}],
    "copyright_suspects": [{"type": "music | footage | logo | character | text", "timestamp": "MM:SS or null",
                            "description": "...", "advice": "..."}],
    "retention": {"hook_score": 0, "hook_comment": "...", "notes": [{"timestamp": "MM:SS", "note": "..."}]},
    "positives": ["..."],
    "follow_up_questions": [{"id": "q1", "question": "...", "why": "...", "options": ["...", "..."]}],
}


def build_analysis_prompt(fmt: str, answers: dict, local_summary: dict, clarifications: list[dict] | None = None,
                          prev_report: dict | None = None, frames_only: bool = False, frame_times: list[float] | None = None) -> str:
    parts = [
        f"FORMAT chosen by creator: {fmt.upper()} ({'YouTube Shorts: vertical, up to 3 minutes' if fmt == 'short' else 'long-form'})",
        "RULES (use these ids in findings[].rule_id):\n" + rules_for_prompt(),
        "CREATOR ANSWERS:\n" + json.dumps(answers, ensure_ascii=False),
        "LOCAL MEASUREMENTS:\n" + json.dumps(local_summary, ensure_ascii=False),
    ]
    if frames_only:
        parts.append("NOTE: You only receive sampled frames (no audio) at these seconds: "
                     + ", ".join(f"{t:.0f}" for t in (frame_times or []))
                     + ". Audio-based judgments (voice, music) must be marked as unknown.")
    if clarifications:
        parts.append("CREATOR CLARIFICATIONS to your earlier follow-up questions:\n" + json.dumps(clarifications, ensure_ascii=False))
    if prev_report:
        parts.append("YOUR PREVIOUS ASSESSMENT (update it using the clarifications, keep what is still valid):\n"
                     + json.dumps(prev_report, ensure_ascii=False)[:6000])
    parts.append("Return JSON with exactly this shape (values in " + OUT_LANG + "):\n" + json.dumps(ANALYSIS_SCHEMA_EXAMPLE, ensure_ascii=False))
    return "\n\n".join(parts)


TOOLS_SYSTEM = """You are an expert YouTube growth strategist and editor assistant. You are given a video (or sampled frames).
Base everything ONLY on what is actually in the video. Never invent facts, numbers, guests or claims.
Avoid clickbait that misrepresents the video, engagement bait, and exaggerated promises. Respond in the requested language.
Use clean plain text/markdown, ready to copy-paste."""

# id -> (title_fa, description_fa, prompt_en, needs_language)
TOOLS: dict[str, tuple[str, str, str]] = {
    "titles": (tr("ایده تیتر"), tr("۱۰ تیتر صادقانه و جذاب + دلیل هر کدوم"),
               "Write 10 YouTube title options for this video (max 70 characters each). Mix curiosity, benefit and specificity, "
               "but every title must be accurate to the video. After each title add one short line (in the output language) saying why it works. "
               "Finish by recommending the best 2."),
    "description": (tr("توضیحات (Description)"), tr("توضیحات بهینه با هوک، خلاصه، چپتر و هشتگ"),
                    "Write an optimized YouTube description: first 2 lines are a strong hook with the main keyword, then a short summary, "
                    "then chapter timestamps (MM:SS) based on the video, then a short neutral CTA (no engagement bait), then 3-5 relevant hashtags."),
    "tags": (tr("تگ و کلمات کلیدی"), tr("تگ‌ها، کلمات کلیدی و هشتگ مناسب"),
             "Give: 15 tags (mix of broad and specific, comma separated, total under 450 characters), 8 search keyword phrases people would type, "
             "and 3-5 hashtags. Only topics actually covered in the video."),
    "chapters": (tr("چپتر / Timestamp"), tr("فهرست چپتر با زمان دقیق"),
                 "Create YouTube chapters for this video. Format exactly: 'MM:SS Title' one per line, first line must be 00:00, "
                 "at least 3 chapters, each at least 10 seconds apart, titles short and descriptive."),
    "thumbnail": (tr("ایده تامبنیل"), tr("متن روی تصویر + بهترین لحظه برای فریم"),
                  "Suggest 5 thumbnail concepts for this video: for each give (1) the best timestamp (MM:SS) to capture a frame, "
                  "(2) a 2-4 word text overlay, (3) composition notes (face/emotion, contrast, colors), (4) why it fits. Must not mislead about the content."),
    "shorts_cuts": (tr("بهترین لحظه‌ها برای Shorts"), tr("از ویدیوی لانگ، بخش‌های مناسب کات شورت"),
                    "Find the 5 best moments to cut into YouTube Shorts (each 20-59 seconds, self-contained, strong first-second hook). "
                    "For each: start and end timestamp (MM:SS), a hook line to put as on-screen text, a title, and why it will hold viewers."),
    "hook": (tr("بهبود هوک"), tr("تحلیل ۳ ثانیه اول و پیشنهاد جایگزین"),
             "Analyze the first 5 seconds of the video as a hook. Score it 1-10, explain what works and what loses viewers, "
             "then write 3 alternative opening lines/visual openings that fit the same content."),
    "pinned_comment": (tr("پین‌کامنت و تعامل"), tr("کامنت پین‌شده و سوال بحث‌برانگیز بدون engagement bait"),
                       "Write 3 pinned-comment options and 3 genuine discussion questions related to the video's content. "
                       "No 'like/subscribe or else', no fake giveaways, no engagement bait."),
    "disclosure_text": (tr("متن افشای AI"), tr("متن آماده برای توضیحات + راهنمای تیک Studio"),
                        "Decide whether this video needs YouTube's 'Altered or synthetic content' disclosure based on what you see/hear "
                        "(realistic AI visuals, cloned real voices, etc.). Answer YES/NO/MAYBE with reasons, then write a short, natural disclosure line "
                        "for the description in the video's language, and tell the creator which Studio checkbox to use."),
    "transcript": (tr("رونویسی (Transcript)"), tr("متن گفتار با زمان‌بندی"),
                   "Transcribe all speech in the video with timestamps every sentence or ~10 seconds, format '[MM:SS] text'. "
                   "If there is no speech, say so. Do not translate."),
    "summary_post": (tr("خلاصه و پست کامیونیتی"), tr("پست Community و متن معرفی کوتاه"),
                     "Write (1) a 3-sentence summary of the video, (2) a Community-tab post teasing it, (3) a one-line tweet/X caption. No hype words, no invented claims."),
}

LANG_NAMES = {"fa": "Persian (Farsi)", "en": "English", "ar": "Arabic", "auto": "the same language spoken/written in the video"}


def build_tool_prompt(tool_id: str, out_lang: str, extra: str = "") -> str:
    title, _, prompt = TOOLS[tool_id]
    s = f"{prompt}\n\nWrite the output in {LANG_NAMES.get(out_lang, out_lang)}."
    if extra.strip():
        s += f"\n\nAdditional context from the creator (use it, do not contradict the video):\n{extra.strip()}"
    return s
