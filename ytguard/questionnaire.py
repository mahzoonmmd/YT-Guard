"""Deterministic rule engine driven by the user's answers (works with no AI / no internet)."""
from __future__ import annotations

from .i18n import DIR, IS_RTL, tr
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

AI_LEVEL_FA = {"none": tr("بدون AI"), "assist": tr("فقط کمک (ایده/اسکریپت/ادیت)"), "mostly": tr("بخش عمده با AI"),
               "full": tr("کامل با AI (تقریباً بدون دخالت)")}


def _f(rule_id, sev, issue, fix, evidence=""):
    return {"rule_id": rule_id, "severity": sev, "issue": issue, "evidence": evidence, "fix": fix,
            "timestamp": None, "source": "questionnaire"}


def evaluate_answers(a: dict, fmt: str) -> list[dict]:
    out: list[dict] = []
    vis, voice, lvl = a.get("ai_visuals", "none"), a.get("ai_voice", "none"), a.get("ai_level", "none")

    # --- disclosure
    if vis == "real_people_events":
        out.append(_f("synthetic_disclosure", "high", tr("AI از افراد/رویدادهای واقعی ساخته شده؛ افشا اجباری است"),
                      tr("در YouTube Studio گزینه Altered or synthetic content = Yes و در توضیحات هم ذکر کن."),
                      tr("پاسخ شما: تصویر AI از افراد یا رویدادهای واقعی")))
    elif vis == "realistic":
        out.append(_f("synthetic_disclosure", "medium", tr("تصویر/ویدیوی واقع‌نمای AI؛ احتمالاً افشا لازم است"),
                      tr("اگه بیننده ممکنه فکر کنه واقعیه، تیک Altered or synthetic content رو بزن."),
                      tr("پاسخ شما: تصویر واقع‌نمای AI")))
    if voice == "real_person_clone":
        out.append(_f("synthetic_disclosure", "high", tr("صدای مصنوعی شبیه یک فرد واقعی؛ افشا اجباری و ریسک حقوقی"),
                      tr("بدون اجازه فرد صداش رو کلون نکن؛ در صورت اجازه افشا کن."), tr("پاسخ شما: کلون صدای دیگران")))
    elif voice == "generic_tts":
        out.append(_f("synthetic_disclosure", "info", tr("گوینده AI عمومی روی ویدیوی واقعی؛ معمولاً افشا لازم نیست"),
                      tr("فقط اگه گوینده به‌عنوان آدم واقعی جا زده می‌شه افشا کن."), tr("پاسخ شما: TTS / گوینده AI")))
    if a.get("ai_music"):
        out.append(_f("synthetic_disclosure", "low", tr("موزیک ساخته‌شده با AI (بعضی منابع افشا رو لازم می‌دونن)"),
                      tr("اگه صدای خواننده واقعی رو تقلید می‌کنه افشا کن؛ در غیر این صورت قوانین ابزار موزیک رو چک کن (لایسنس تجاری)."),
                      tr("پاسخ شما: موزیک AI")))

    # --- inauthentic
    if lvl == "full":
        out.append(_f("unedited_ai_output", "high", tr("ویدیو تقریباً کامل با AI و بدون دخالت انسانی ساخته شده"),
                      tr("ادیت، روایت و ایده خودت رو اضافه کن؛ خروجی خام AI ریسک رد مانیتایز داره."), tr("پاسخ شما: کامل با AI")))
    elif lvl == "mostly":
        out.append(_f("unedited_ai_output", "medium", tr("بخش عمده ویدیو با AI ساخته شده"),
                      tr("مطمئن شو ارزش افزوده انسانی (نظر، تحلیل، ادیت خلاق) واضحه."), tr("پاسخ شما: عمدتاً AI")))
    if a.get("series_template"):
        out.append(_f("inauthentic_content", "medium", tr("ویدیو بخشی از مجموعه‌ی قالبی/مشابه است"),
                      tr("هر قسمت باید ایده، ساختار و بصری متمایز داشته باشه؛ بررسی یوتیوب روی الگوی کل کانال است."),
                      tr("پاسخ شما: ویدیوهای قالبی/مشابه زیاد")))
    if a.get("niche") in SENSITIVE_NICHES and (voice in ("generic_tts", "real_person_clone") or vis in ("realistic", "real_people_events")
                                               or lvl in ("mostly", "full")):
        out.append(_f("ai_persona_expert", "high" if lvl == "full" else "medium",
                      tr("موضوع حساس (سلامت/مالی/حقوقی/اخبار) با محتوای عمدتاً AI"),
                      tr("منبع بیار، توصیه قطعی نده و صراحتاً بگو AI در ساخت نقش داشته؛ بهتره آدم واقعی روایت کنه."),
                      tr("پاسخ شما: موضوع حساس + AI")))
    if a.get("niche") == "health":
        out.append(_f("misinformation", "low", tr("موضوع سلامت/پزشکی: ادعاها باید منبع معتبر داشته باشن"),
                      tr("از ادعای درمان قطعی دوری کن و منبع (WHO، مقاله علمی) نشون بده.")))
    if a.get("niche") == "news":
        out.append(_f("advertiser_friendly", "low", tr("موضوع خبری/سیاسی: احتمال Limited ads بالاتر است"),
                      tr("لحن تحلیلی/خبری نگه دار و تصاویر گرافیکی رو حذف کن.")))

    # --- copyright / reuse
    tv = a.get("third_party_video", "none")
    if tv == "long_or_no_commentary":
        out.append(_f("reused_content", "high", tr("کلیپ‌های بلند/بدون تفسیر از ویدیو و فیلم دیگران"),
                      tr("کلیپ‌ها رو کوتاه کن و تفسیر/تحلیل اصیل اضافه کن، یا از مواد لایسنس‌دار استفاده کن."),
                      tr("پاسخ شما: کلیپ دیگران بدون تفسیر کافی")))
        out.append(_f("copyright_footage", "high", tr("ریسک Claim یا حذف به‌خاطر فوتیج متعلق به دیگران"),
                      tr("مجوز بگیر یا جایگزین پیدا کن."), tr("پاسخ شما: کلیپ دیگران")))
    elif tv == "short_with_commentary":
        out.append(_f("reused_content", "low", tr("کلیپ کوتاه با تفسیر؛ در حالت مجاز ولی بدون تضمین"),
                      tr("مطمئن شو تفسیر تو بخش اصلی ویدیوست و کلیپ‌ها فقط پشتیبان‌اند.")))
        out.append(_f("copyright_footage", "low", tr("فوتیج دیگران حتی کوتاه ممکنه Claim بخوره"),
                      tr("کلیپ‌ها رو تا حد ممکن کوتاه نگه دار.")))
    tm = a.get("third_party_music", "none")
    if tm == "popular_song":
        out.append(_f("copyright_music", "high", tr("آهنگ معروف/تجاری: Content ID تقریباً حتماً Claim می‌زنه"),
                      tr("موزیک بدون کپی‌رایت (YouTube Audio Library) یا لایسنس‌دار بذار؛ برای Shorts از کتابخونه موزیک خود یوتیوب."),
                      tr("پاسخ شما: آهنگ معروف")))
    elif tm == "unknown":
        out.append(_f("copyright_music", "medium", tr("منبع موزیک نامشخص"),
                      tr("مطمئن شو لایسنس یا اجازه استفاده داری؛ بعد از آپلود Checks در Studio رو ببین."), tr("پاسخ شما: نامشخص")))

    # --- declarations
    if a.get("kids") or a.get("niche") == "kids":
        out.append(_f("made_for_kids", "medium" if not a.get("kids") else "info",
                      tr("محتوای کودکانه: باید Audience رو دقیق روی Made for Kids تنظیم کنی"),
                      tr("در Studio → Audience → Yes, it's made for kids. این ویدیو کامنت و آگهی شخصی‌سازی‌شده نخواهد داشت.")))
    if a.get("sponsor"):
        out.append(_f("paid_promotion", "medium", tr("اسپانسر/تبلیغ پولی در ویدیو"),
                      tr("تیک Includes paid promotion رو بزن و اسپانسر رو شفاف اعلام کن.")))
    return out
