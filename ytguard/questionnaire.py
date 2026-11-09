"""Deterministic rule engine driven by the user's answers (works with no AI / no internet)."""
from __future__ import annotations

from .knowledge import SENSITIVE_NICHES

DEFAULT_ANSWERS = {
    "fmt": "auto",              # auto | short | long
    "ai_level": "none",         # none | assist | mostly | full
    "ai_voice": "none",         # none | own_clone | generic_tts | real_person_clone
    "ai_visuals": "none",       # none | stylized | realistic | real_people_events
    "ai_music": False,
    "third_party_video": "none",  # none | short_with_commentary | long_or_no_commentary
    "third_party_music": "none",  # none | library_licensed | popular_song | unknown
    "niche": "general",
    "kids": False,
    "sponsor": False,
    "series_template": False,
    "monetized": True,
    "notes": "",
}

AI_LEVEL_FA = {"none": "بدون AI", "assist": "فقط کمک (ایده/اسکریپت/ادیت)", "mostly": "بخش عمده با AI",
               "full": "کامل با AI (تقریباً بدون دخالت)"}


def _f(rule_id, sev, issue, fix, evidence=""):
    return {"rule_id": rule_id, "severity": sev, "issue": issue, "evidence": evidence, "fix": fix,
            "timestamp": None, "source": "questionnaire"}


def evaluate_answers(a: dict, fmt: str) -> list[dict]:
    out: list[dict] = []
    vis, voice, lvl = a.get("ai_visuals", "none"), a.get("ai_voice", "none"), a.get("ai_level", "none")

    # --- disclosure
    if vis == "real_people_events":
        out.append(_f("synthetic_disclosure", "high", "AI از افراد/رویدادهای واقعی ساخته شده؛ افشا اجباری است",
                      "در YouTube Studio گزینه Altered or synthetic content = Yes و در توضیحات هم ذکر کن.",
                      "پاسخ شما: تصویر AI از افراد یا رویدادهای واقعی"))
    elif vis == "realistic":
        out.append(_f("synthetic_disclosure", "medium", "تصویر/ویدیوی واقع‌نمای AI؛ احتمالاً افشا لازم است",
                      "اگه بیننده ممکنه فکر کنه واقعیه، تیک Altered or synthetic content رو بزن.",
                      "پاسخ شما: تصویر واقع‌نمای AI"))
    if voice == "real_person_clone":
        out.append(_f("synthetic_disclosure", "high", "صدای مصنوعی شبیه یک فرد واقعی؛ افشا اجباری و ریسک حقوقی",
                      "بدون اجازه فرد صداش رو کلون نکن؛ در صورت اجازه افشا کن.", "پاسخ شما: کلون صدای دیگران"))
    elif voice == "generic_tts":
        out.append(_f("synthetic_disclosure", "info", "گوینده AI عمومی روی ویدیوی واقعی؛ معمولاً افشا لازم نیست",
                      "فقط اگه گوینده به‌عنوان آدم واقعی جا زده می‌شه افشا کن.", "پاسخ شما: TTS / گوینده AI"))
    if a.get("ai_music"):
        out.append(_f("synthetic_disclosure", "low", "موزیک ساخته‌شده با AI (بعضی منابع افشا رو لازم می‌دونن)",
                      "اگه صدای خواننده واقعی رو تقلید می‌کنه افشا کن؛ در غیر این صورت قوانین ابزار موزیک رو چک کن (لایسنس تجاری).",
                      "پاسخ شما: موزیک AI"))

    # --- inauthentic
    if lvl == "full":
        out.append(_f("unedited_ai_output", "high", "ویدیو تقریباً کامل با AI و بدون دخالت انسانی ساخته شده",
                      "ادیت، روایت و ایده خودت رو اضافه کن؛ خروجی خام AI ریسک رد مانیتایز داره.", "پاسخ شما: کامل با AI"))
    elif lvl == "mostly":
        out.append(_f("unedited_ai_output", "medium", "بخش عمده ویدیو با AI ساخته شده",
                      "مطمئن شو ارزش افزوده انسانی (نظر، تحلیل، ادیت خلاق) واضحه.", "پاسخ شما: عمدتاً AI"))
    if a.get("series_template"):
        out.append(_f("inauthentic_content", "medium", "ویدیو بخشی از مجموعه‌ی قالبی/مشابه است",
                      "هر قسمت باید ایده، ساختار و بصری متمایز داشته باشه؛ بررسی یوتیوب روی الگوی کل کانال است.",
                      "پاسخ شما: ویدیوهای قالبی/مشابه زیاد"))
    if a.get("niche") in SENSITIVE_NICHES and (voice in ("generic_tts", "real_person_clone") or vis in ("realistic", "real_people_events")
                                               or lvl in ("mostly", "full")):
        out.append(_f("ai_persona_expert", "high" if lvl == "full" else "medium",
                      "موضوع حساس (سلامت/مالی/حقوقی/اخبار) با محتوای عمدتاً AI",
                      "منبع بیار، توصیه قطعی نده و صراحتاً بگو AI در ساخت نقش داشته؛ بهتره آدم واقعی روایت کنه.",
                      "پاسخ شما: موضوع حساس + AI"))
    if a.get("niche") == "health":
        out.append(_f("misinformation", "low", "موضوع سلامت/پزشکی: ادعاها باید منبع معتبر داشته باشن",
                      "از ادعای درمان قطعی دوری کن و منبع (WHO، مقاله علمی) نشون بده."))
    if a.get("niche") == "news":
        out.append(_f("advertiser_friendly", "low", "موضوع خبری/سیاسی: احتمال Limited ads بالاتر است",
                      "لحن تحلیلی/خبری نگه دار و تصاویر گرافیکی رو حذف کن."))

    # --- copyright / reuse
    tv = a.get("third_party_video", "none")
    if tv == "long_or_no_commentary":
        out.append(_f("reused_content", "high", "کلیپ‌های بلند/بدون تفسیر از ویدیو و فیلم دیگران",
                      "کلیپ‌ها رو کوتاه کن و تفسیر/تحلیل اصیل اضافه کن، یا از مواد لایسنس‌دار استفاده کن.",
                      "پاسخ شما: کلیپ دیگران بدون تفسیر کافی"))
        out.append(_f("copyright_footage", "high", "ریسک Claim یا حذف به‌خاطر فوتیج متعلق به دیگران",
                      "مجوز بگیر یا جایگزین پیدا کن.", "پاسخ شما: کلیپ دیگران"))
    elif tv == "short_with_commentary":
        out.append(_f("reused_content", "low", "کلیپ کوتاه با تفسیر؛ در حالت مجاز ولی بدون تضمین",
                      "مطمئن شو تفسیر تو بخش اصلی ویدیوست و کلیپ‌ها فقط پشتیبان‌اند."))
        out.append(_f("copyright_footage", "low", "فوتیج دیگران حتی کوتاه ممکنه Claim بخوره",
                      "کلیپ‌ها رو تا حد ممکن کوتاه نگه دار."))
    tm = a.get("third_party_music", "none")
    if tm == "popular_song":
        out.append(_f("copyright_music", "high", "آهنگ معروف/تجاری: Content ID تقریباً حتماً Claim می‌زنه",
                      "موزیک بدون کپی‌رایت (YouTube Audio Library) یا لایسنس‌دار بذار؛ برای Shorts از کتابخونه موزیک خود یوتیوب.",
                      "پاسخ شما: آهنگ معروف"))
    elif tm == "unknown":
        out.append(_f("copyright_music", "medium", "منبع موزیک نامشخص",
                      "مطمئن شو لایسنس یا اجازه استفاده داری؛ بعد از آپلود Checks در Studio رو ببین.", "پاسخ شما: نامشخص"))

    # --- declarations
    if a.get("kids") or a.get("niche") == "kids":
        out.append(_f("made_for_kids", "medium" if not a.get("kids") else "info",
                      "محتوای کودکانه: باید Audience رو دقیق روی Made for Kids تنظیم کنی",
                      "در Studio → Audience → Yes, it's made for kids. این ویدیو کامنت و آگهی شخصی‌سازی‌شده نخواهد داشت."))
    if a.get("sponsor"):
        out.append(_f("paid_promotion", "medium", "اسپانسر/تبلیغ پولی در ویدیو",
                      "تیک Includes paid promotion رو بزن و اسپانسر رو شفاف اعلام کن."))
    return out
