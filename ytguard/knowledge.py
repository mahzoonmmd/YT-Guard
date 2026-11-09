"""Knowledge base of YouTube rules the app checks against.

Policies change often. Every rule carries a `confidence`:
  official  - matches YouTube's own published policy wording as far as we could verify
  reported  - reported consistently by several third-party sources, not verified on YouTube's pages
  unverified- single third-party source (shown with a warning in the app)
Last research pass: see KNOWLEDGE_VERIFIED_ON.
"""
from __future__ import annotations

SEV_ORDER = {"high": 3, "medium": 2, "low": 1, "info": 0}

# id -> rule
RULES: dict[str, dict] = {
    "inauthentic_content": {
        "title": "محتوای غیراصیل (Inauthentic / mass-produced)",
        "applies": "both",
        "impact": "مانیتایز",
        "summary": "ویدیوهای قالبی، تکراری و تولید انبوه که شبیه هم‌اند (حتی اگه همه‌ش مال خودت باشه) باعث رد یا قطع مانیتایز کل کانال می‌شن. بررسی روی «الگوی کل کانال» انجام می‌شه نه یک ویدیو.",
        "fix": "هر ویدیو ساختار، روایت و بصری متفاوت داشته باشه و ارزش اضافه واقعی (تحلیل، تجربه شخصی، ادیت خلاق) داشته باشه.",
        "confidence": "reported",
        "source": "https://www.uptube.io/blog/youtube-new-policies-2026",
    },
    "unedited_ai_output": {
        "title": "خروجی خام AI (Prompt-to-upload)",
        "applies": "both",
        "impact": "مانیتایز",
        "summary": "آپلود مستقیم خروجی AI بدون ادیت و بدون ارزش افزوده، مصداق محتوای غیراصیل حساب می‌شه. خود AI مشکلی نداره؛ ویدیوی بدون دخالت انسانی مشکل داره.",
        "fix": "اسکریپت، روایت، ادیت و انتخاب بصری رو خودت دخیل کن؛ صدای خودت یا روایت واقعی اضافه کن.",
        "confidence": "reported",
        "source": "https://vidiq.com/blog/post/youtube-reused-content-policy-guide/",
    },
    "ai_persona_expert": {
        "title": "پرسونای AI در نقش متخصص (سلامت/حقوقی/مالی/سیاسی)",
        "applies": "both",
        "impact": "مانیتایز",
        "summary": "چهره یا صدای مصنوعی که خودش رو متخصص پزشکی، حقوقی، مالی یا سیاسی جا می‌زنه، یکی از دسته‌های محتوای غیراصیله.",
        "fix": "منبع بیار، صراحتاً بگو AI هست، و توصیه تخصصی قطعی نده؛ بهتره آدم واقعی روایت کنه.",
        "confidence": "reported",
        "source": "https://www.uptube.io/blog/youtube-new-policies-2026",
    },
    "synthetic_disclosure": {
        "title": "افشای محتوای تغییریافته/مصنوعی (Altered or synthetic content)",
        "applies": "both",
        "impact": "مانیتایز + اعتماد",
        "summary": "اگه محتوای واقع‌نما با AI ساخته یا دستکاری شده و بیننده ممکنه فکر کنه واقعیه، باید تیک «Altered or synthetic content» رو در Studio بزنی. از ۲۷ می ۲۰۲۶ یوتیوب خودش هم می‌تونه خودکار برچسب بزنه. افشا به‌تنهایی ریچ یا مانیتایز رو کم نمی‌کنه؛ پنهان‌کاری مکرر می‌تونه.",
        "fix": "هنگام آپلود در YouTube Studio گزینه Altered or synthetic content رو Yes کن.",
        "confidence": "reported",
        "source": "https://air.io/en/youtube-hacks/youtube-ai-disclosure-in-2026-label-it-yourself-or-youtube-will",
    },
    "reused_content": {
        "title": "محتوای بازاستفاده‌شده (Reused content)",
        "applies": "both",
        "impact": "مانیتایز",
        "summary": "کلیپ، فیلم، سریال، ویدیوی دیگران یا ریپ‌اِستریم بدون تغییر معنادار و بدون تفسیر/تحلیل اصیل. کامپایلیشن و ری‌اکشن فقط با ارزش افزوده قابل قبوله.",
        "fix": "تفسیر، تحلیل، ادیت روایی و کلیپ‌های کوتاه‌تر اضافه کن؛ از مواد با مجوز یا خودت استفاده کن.",
        "confidence": "official",
        "source": "https://vidiq.com/blog/post/youtube-reused-content-policy-guide/",
    },
    "copyright_music": {
        "title": "موزیک / صدای دارای کپی‌رایت (Content ID)",
        "applies": "both",
        "impact": "درآمد / ریچ",
        "summary": "Content ID موزیک و کلیپ رو با اثر انگشت صوتی-تصویری تشخیص می‌ده. نتیجه معمولاً Claim است (درآمد می‌ره به مالک یا ویدیو مسدود می‌شه) و Strike فقط در شکایت رسمی. هیچ AI یا برنامه‌ای نمی‌تونه جای Content ID رو بگیره؛ فقط مشکوک‌ها رو نشون می‌دیم.",
        "fix": "از YouTube Audio Library یا موزیک با لایسنس واضح استفاده کن؛ برای Shorts از کتابخونه موزیک خود یوتیوب.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/3311596",
    },
    "copyright_footage": {
        "title": "فوتیج/لوگو/کاراکتر متعلق به دیگران",
        "applies": "both",
        "impact": "درآمد / ریچ",
        "summary": "فیلم، سریال، بازی، ورزش، اخبار، کاراکترهای کارتونی و لوگوهای برند بدون مجوز ریسک Claim یا حذف دارن. «Fair use» تضمین نیست.",
        "fix": "مدت کلیپ‌ها رو کم کن، تغییر معنادار بده یا جایگزین با لایسنس پیدا کن.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/3311596",
    },
    "other_platform_watermark": {
        "title": "واترمارک پلتفرم‌های دیگر (TikTok / Reels / CapCut)",
        "applies": "short",
        "impact": "ریچ",
        "summary": "ویدیوی ری‌آپلودشده با واترمارک اپ‌های دیگه نشانه محتوای بازچرخانی‌شده است و توزیع Shorts رو ضعیف می‌کنه. واترمارک را فقط از ویدیوهای خودت حذف کن، نه ویدیوی دیگران.",
        "fix": "خروجی بدون واترمارک از ادیتور بگیر.",
        "confidence": "reported",
        "source": "https://vidiq.com/blog/post/youtube-reused-content-policy-guide/",
    },
    "advertiser_friendly": {
        "title": "مناسب آگهی‌دهنده (Advertiser-friendly)",
        "applies": "both",
        "impact": "درآمد آگهی",
        "summary": "فحش شدید (مخصوصاً ۷ ثانیه اول)، خشونت گرافیکی، محتوای بزرگسال، مواد مخدر، موضوعات حساس/تراژدی، اطلاعات نادرست و سلاح می‌تونن باعث Limited ads (زرد) بشن.",
        "fix": "بخش‌های حساس رو حذف/بیپ کن یا موضوع رو با زمینه آموزشی/خبری مطرح کن؛ بعد از آپلود Self-certification رو درست پر کن.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/6162278",
    },
    "misleading_metadata": {
        "title": "تیتر/تامبنیل گمراه‌کننده (Clickbait / Spam & deceptive practices)",
        "applies": "both",
        "impact": "ریچ + مانیتایز",
        "summary": "وعده‌ای که ویدیو نمی‌ده، تامبنیل نامرتبط، فریب با قرعه‌کشی/جایزه، درخواست بی‌معنی برای لایک/ساب (Engagement bait).",
        "fix": "تیتر و تامبنیل باید دقیقاً چیزی رو که توی ویدیو هست نشون بدن.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/2801973",
    },
    "misinformation": {
        "title": "اطلاعات نادرست (سلامت/انتخابات/..)",
        "applies": "both",
        "impact": "حذف / محدودیت",
        "summary": "ادعاهای پزشکی خطرناک، اطلاعات نادرست انتخاباتی یا تحریف بحران‌ها می‌تونه ویدیو رو حذف یا کانال رو محدود کنه.",
        "fix": "ادعاها رو با منبع معتبر پشتیبانی کن و از قطعیت غیرمنطقی دوری کن.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/topic/2803138",
    },
    "made_for_kids": {
        "title": "تنظیم «مخصوص کودکان» (Made for Kids / COPPA)",
        "applies": "both",
        "impact": "مانیتایز + قابلیت‌ها",
        "summary": "برای هر ویدیو باید مشخص کنی مخصوص کودکانه یا نه. انتخاب اشتباه می‌تونه جریمه یا محدودیت بیاره. ویدیوی کودکانه کامنت و آگهی شخصی‌سازی‌شده نداره.",
        "fix": "در Studio بخش Audience دقیق انتخاب کن.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/9527654",
    },
    "paid_promotion": {
        "title": "تبلیغ/اسپانسر پولی (Paid promotion)",
        "applies": "both",
        "impact": "قانونی + اعتماد",
        "summary": "اگه اسپانسر یا محصول رایگان/پولی در ویدیو هست باید تیک «Includes paid promotion» رو بزنی (و قوانین کشور خودت).",
        "fix": "تیک paid promotion و ذکر شفاف اسپانسر.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/154235",
    },
    "shorts_format": {
        "title": "فرمت Shorts",
        "applies": "short",
        "impact": "ریچ",
        "summary": "Shorts باید عمودی یا مربع و حداکثر ۳ دقیقه باشه. هوک ۱-۳ ثانیه اول و بیشتر بودن «Viewed vs swiped away» روی توزیع تأثیر زیاد داره. برای دریافت درآمد Shorts، بازدیدها در ۹۰ روز اخیر مهمه.",
        "fix": "نسبت ۹:۱۶، رزولوشن ۱۰۸۰×۱۹۲۰، شروع سریع و بدون سکوت/فریم سیاه.",
        "confidence": "reported",
        "source": "https://www.uptube.io/blog/youtube-new-policies-2026",
    },
    "long_format": {
        "title": "ویدیوی لانگ",
        "applies": "long",
        "impact": "درآمد آگهی",
        "summary": "ویدیوی بالای ۸ دقیقه امکان Mid-roll ads داره (مشروط به مانیتایز بودن). مهم‌تر از همه ماندگاری مخاطب و ۳۰ ثانیه اول است.",
        "fix": "هوک قوی، ریتم ثابت، حذف بخش‌های کند، چپتر.",
        "confidence": "official",
        "source": "https://support.google.com/youtube/answer/1311392",
    },
    "technical_quality": {
        "title": "کیفیت فنی (صدا، تصویر، فریم سیاه)",
        "applies": "both",
        "impact": "ماندگاری مخاطب",
        "summary": "صدای خیلی کم/زیاد، سکوت طولانی، فریم سیاه، رزولوشن پایین و تصویر ثابت باعث ریزش مخاطب می‌شه (نه قانون، ولی مستقیم روی ویو اثر داره).",
        "fix": "لودنس حدود -14 LUFS، رزولوشن حداقل 1080p، حذف سکوت و فریم سیاه.",
        "confidence": "reported",
        "source": "https://support.google.com/youtube/answer/1311392",
    },
    "ypp_thresholds": {
        "title": "آستانه‌های جدید YPP (فقط مرجع)",
        "applies": "both",
        "impact": "ورود به مانیتایز",
        "summary": "طبق یک منبع غیررسمی: برای ورود جدید از ۱ فوریه ۲۰۲۷، ۸۰۰۰ ساعت watch time یا ۲۰ میلیون ویو Shorts در ۹۰ روز؛ اعضای فعلی تا ۳۱ ژانویه ۲۰۲۷ باید قوانین جدید رو بپذیرن و برای درآمد Shorts به ۱۰ میلیون ویو در ۹۰ روز نیاز دارن. این عددها از یک منبع واحد است و باید در خود یوتیوب تأیید بشه.",
        "fix": "قبل از تصمیم‌گیری در صفحه رسمی YouTube Partner Program چک کن.",
        "confidence": "unverified",
        "source": "https://www.uptube.io/blog/youtube-new-policies-2026",
    },
    "channel_inactivity": {
        "title": "غیرفعال بودن کانال (فقط مرجع)",
        "applies": "both",
        "impact": "مانیتایز",
        "summary": "طبق همان منبع، ۶ ماه بدون آپلود یا پست Community می‌تونه دسترسی مانیتایز رو بگیره.",
        "fix": "حداقل هر چند هفته یک آپلود/پست.",
        "confidence": "unverified",
        "source": "https://www.uptube.io/blog/youtube-new-policies-2026",
    },
}

CONFIDENCE_FA = {
    "official": "رسمی",
    "reported": "گزارش‌شده (چند منبع)",
    "unverified": "تأییدنشده (منبع واحد)",
}

IMPACT_FA = {"high": "زیاد", "medium": "متوسط", "low": "کم", "info": "اطلاع"}

NICHES = [
    ("general", "عمومی / سرگرمی"),
    ("education", "آموزشی"),
    ("tech", "تکنولوژی / آموزش نرم‌افزار"),
    ("gaming", "گیمینگ"),
    ("music", "موزیک"),
    ("news", "اخبار / سیاسی / رویداد روز"),
    ("health", "سلامت / پزشکی / تناسب اندام"),
    ("finance", "مالی / سرمایه‌گذاری / کریپتو"),
    ("legal", "حقوقی"),
    ("kids", "کودک"),
    ("film", "فیلم / ادیت / سینما"),
    ("lifestyle", "سبک زندگی / سفر / غذا"),
    ("other", "دیگر"),
]
SENSITIVE_NICHES = {"news", "health", "finance", "legal"}


def rules_for_prompt() -> str:
    lines = []
    for rid, r in RULES.items():
        lines.append(f'- id="{rid}" ({r["applies"]}): {r["title"]} — {r["summary"]}')
    return "\n".join(lines)


def rule_title(rid: str) -> str:
    return RULES.get(rid, {}).get("title", rid)
