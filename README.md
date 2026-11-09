<div align="center">

# 🛡️ YT Guard — نگهبان یوتیوب

**Pre-upload checker for YouTube videos (Long & Shorts) — Windows desktop app**
**بررسی هوشمند ویدیو قبل از آپلود در یوتیوب (لانگ و Shorts)**

![Python](https://img.shields.io/badge/Python-3.10%2B-red) ![PyQt6](https://img.shields.io/badge/UI-PyQt6-red) ![Platform](https://img.shields.io/badge/Platform-Windows-black)

<img src="docs/screenshot-dark.png" width="48%"> <img src="docs/screenshot-light.png" width="48%">

</div>

---

## 🇬🇧 English

Drop a video into the app and it checks it against YouTube's rules **before** you upload, so you find problems that can kill views or monetization.

### What it checks
- **AI usage & disclosure** – likely AI voice/visuals, whether the *Altered or synthetic content* toggle is needed, ready-to-paste disclosure text
- **Inauthentic / mass-produced content** – static slideshows, near-duplicate videos compared with your previous uploads, raw "prompt-to-upload" AI output
- **Reused content & copyright suspicions** – suspected music/footage/logos with timestamps (suspicions only, **not** a replacement for Content ID)
- **Advertiser-friendliness, Made for Kids, paid promotion** declarations
- **Shorts vs Long format rules** (aspect ratio, ≤ 3 min, resolution)
- **Retention killers** – weak hook, silence, black frames, bad loudness
- **Metadata scan** – C2PA / AI-tool markers, other-platform watermarks hints
- The AI can **ask you follow-up questions** when the answer changes the verdict

### YouTuber tools
Titles, description, tags, chapters, thumbnail ideas, best Shorts cuts, hook improvement, pinned comment, AI-disclosure text, transcript · Best thumbnail frames extractor · Horizontal → 9:16 converter · History · Report export (HTML / Markdown / JSON)

### AI engine
- **Google Gemini API** (free tier, native video + audio understanding) – recommended
- Any **OpenAI-compatible** endpoint (OpenRouter, Groq, local…) – frames only, no audio
- Works **without AI** too: local analysis + rules questionnaire run offline
- **UI languages:** Persian (RTL) and English (Settings → Language, restart to apply)

### Install (Windows)
1. Install Python 3.10+ (tick *Add to PATH*)
2. Double-click `run.bat` (first run installs dependencies)
3. Settings → paste your free key from <https://aistudio.google.com/apikey> → *Fetch models / test connection*
4. If the Gemini API is not reachable from your country, set a **Proxy** in Settings

Build an `.exe`: run `build_exe.bat` on Windows.

### Honest limitations
- Real **Content ID** can't be simulated — you only see it after upload (Studio → Checks)
- AI detection is probabilistic; YouTube policies change often (see the *Rules* tab: every rule shows how well its source is verified)
- The Gemini free tier may use your inputs to improve Google products — don't upload confidential videos with it

---

## 🇮🇷 فارسی

ویدیو رو بنداز توی برنامه تا **قبل از آپلود** با قوانین یوتیوب بررسی بشه و مشکلاتی که جلوی ویو یا مانیتایز رو می‌گیرن پیدا بشن.

### چی چک می‌شه
- **استفاده از AI و افشا** – صدا/تصویر AI، نیاز به تیک *Altered or synthetic content* و متن آماده برای توضیحات
- **محتوای غیراصیل / تولید انبوه** – اسلایدشو، شباهت زیاد به ویدیوهای قبلی خودت، خروجی خام AI
- **محتوای بازاستفاده‌شده و مشکوک‌های کپی‌رایت** – موزیک/فوتیج/لوگوی مشکوک با timestamp (فقط حدس؛ جایگزین Content ID نیست)
- **مناسب آگهی‌دهنده، Made for Kids، تبلیغ پولی**
- **قوانین Shorts و لانگ** (نسبت تصویر، حداکثر ۳ دقیقه، رزولوشن)
- **عوامل ریزش مخاطب** – هوک ضعیف، سکوت، فریم سیاه، لودنس نامناسب
- **متادیتا** – C2PA، نشانه ابزارهای AI و واترمارک پلتفرم‌های دیگر
- اگه جواب یه سوال روی نتیجه اثر بذاره، **AI از خودت سوال می‌پرسه**

### ابزارهای یوتیوبر
تیتر، توضیحات، تگ، چپتر، ایده تامبنیل، بهترین بخش‌ها برای Shorts، بهبود هوک، پین‌کامنت، متن افشای AI، رونویسی · استخراج بهترین فریم‌ها برای تامبنیل · تبدیل افقی به ۹:۱۶ · تاریخچه · خروجی گزارش (HTML / Markdown / JSON)

### موتور AI
- **Google Gemini API** (پلن رایگان، فهم مستقیم ویدیو و صدا) – پیشنهادی
- هر سرویس **OpenAI-compatible** (OpenRouter، Groq، محلی…) – فقط فریم‌ها، بدون صدا
- **بدون AI هم کار می‌کنه**: تحلیل محلی و پرسشنامه قوانین آفلاین اجرا می‌شن
- **زبان برنامه:** فارسی و انگلیسی (تنظیمات → زبان؛ برای اعمال، برنامه رو دوباره باز کن)

### نصب (ویندوز)
1. Python 3.10+ نصب کن (تیک Add to PATH)
2. فایل `run.bat` رو اجرا کن (بار اول پکیج‌ها نصب می‌شن)
3. تنظیمات → کلید رایگان از <https://aistudio.google.com/apikey> → «دریافت لیست مدل‌ها / تست اتصال»
4. اگه Gemini از کشورت در دسترس نیست، در تنظیمات **Proxy** بده

برای ساخت exe: روی ویندوز `build_exe.bat` رو اجرا کن.

### محدودیت‌ها (صادقانه)
- **Content ID** واقعی قابل شبیه‌سازی نیست و فقط بعد از آپلود (Studio → Checks) مشخص می‌شه
- تشخیص AI احتمالاتیه و قوانین یوتیوب مرتب عوض می‌شن (تب «قوانین» سطح اطمینان هر منبع رو نشون می‌ده)
- پلن رایگان Gemini ممکنه از ورودی‌ها برای بهبود محصولات گوگل استفاده کنه؛ ویدیوی محرمانه نفرست

---

## ⭐ Support / حمایت
If this project helps you, please **star ⭐ the repo** and **follow [@mahzoonmmd](https://github.com/mahzoonmmd)**.
اگه به دردت خورد، به ریپو **Star ⭐** بده و منو **Follow** کن.

Made by **Mohammadali Mahzoon** · Font: [Vazirmatn](https://github.com/rastikerdar/vazirmatn) (OFL)


## Installer / نصب‌کننده
- EN: Run `build_installer.bat` on Windows (needs Python + [Inno Setup 6](https://jrsoftware.org/isdl.php)). It builds the app and produces `installer_output\YTGuard-Setup-1.0.0.exe`. On first launch the app shows a prerequisites window (FFmpeg, VC++ Runtime) with a live checklist and overall progress.
- FA: روی ویندوز `build_installer.bat` رو اجرا کن (به Python و Inno Setup 6 نیاز داره). فایل نصبی ساخته می‌شه و اولین بار که برنامه باز بشه، پنجره نصب پیش‌نیازها با لیست و درصد پیشرفت نمایش داده می‌شه.


## New in this version / تازه‌ها
- **Why no views? / چرا ویو نمی‌گیره؟** — funnel diagnosis (impressions → CTR → retention → discovery → audience fit → policy) from title, thumbnail, description, optional video and your Studio numbers; local thumbnail checks (size, contrast, clutter, faces), title A/B ranking.
- **Idea check / بررسی ایده** — verdict, scores (views, monetization, policy safety, originality, competition), pros/cons, policy risks, better angles, titles, hooks and a cheap-test list.
- **Channel review / بررسی کانال** — recent videos via the free YouTube Data API key (or a pasted list): best/worst videos vs the channel's own median, title-feature effects, thumbnail comparison (top vs bottom), YPP checklist (500/1,000 subs tiers) and a prioritized plan.
- Reports can be copied or saved as Markdown. AI has no access to YouTube's private analytics or live trends; demand statements are estimates.
