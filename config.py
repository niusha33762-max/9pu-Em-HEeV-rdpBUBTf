"""تنظیمات مرکزی بات. همه‌چیز از متغیرهای محیطی (Environment Variables) خونده می‌شه."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv اختیاریه
    pass


def _bool(name: str, default: str = "1") -> bool:
    value = os.getenv(name, "").strip() or default  # مقدار خالی (secret تنظیم‌نشده در GitHub) یعنی پیش‌فرض
    return value.lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


# ---------- تلگرام ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()   # مثل @mychannel یا -100123456789
ADMIN_ID = _int("ADMIN_ID", 0)
PORT = _int("PORT", 10000)
SIGNATURE = os.getenv("CHANNEL_SIGNATURE") or "@XNewsCafe"  # امضای پایین هر پست

# ---------- گیت‌هاب (ذخیره‌ی دائمی sources.json و filters.json) ----------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()      # مثل user/repo
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()

# ---------- rsshub ----------
# آدرس instance شخصی (بدون / آخر). برای توییتر الزامیه: instanceهای عمومی توکن توییتر ندارن
RSSHUB_URL = os.getenv("RSSHUB_URL", "").strip().rstrip("/")
RSSHUB_KEY = os.getenv("RSSHUB_KEY", "").strip()        # همون ACCESS_KEY روی instance خودت

_DEFAULT_PUBLIC = ",".join([
    "https://rsshub.app",
    "https://rsshub.aturret.com",
    "https://hub.slarker.me",
    "https://rsshub.ktachibana.party",
])
# اگه instance شخصی داری، پیش‌فرض فقط از همون استفاده می‌شه
USE_PUBLIC_INSTANCES = _bool("USE_PUBLIC_INSTANCES", "0" if RSSHUB_URL else "1")
PUBLIC_INSTANCES = [
    u.strip().rstrip("/")
    for u in os.getenv("PUBLIC_INSTANCES", _DEFAULT_PUBLIC).split(",")
    if u.strip()
]
RSS_INSTANCES = ([RSSHUB_URL] if RSSHUB_URL else []) + (PUBLIC_INSTANCES if USE_PUBLIC_INSTANCES else [])

# مسیر route توییتر ({username} جایگزین می‌شه). روی instance شخصی باید TWITTER_AUTH_TOKEN تنظیم باشه.
FEED_ROUTE = os.getenv("FEED_ROUTE", "/twitter/user/{username}").strip()

# ---------- رفتار بات ----------
CHECK_INTERVAL = _int("CHECK_INTERVAL", 900)     # ثانیه
MAX_PER_RUN = _int("MAX_PER_RUN", 5)             # حداکثر پست جدید هر منبع در هر اجرا
REQUEST_TIMEOUT = _int("REQUEST_TIMEOUT", 30)
MIN_CAPTION_LEN = _int("MIN_CAPTION_LEN", 5)     # توییت‌های کوتاه‌تر از این رد می‌شن
STRIP_HASHTAGS = _bool("STRIP_HASHTAGS", "0")    # 1 = بلوک هشتگ‌های آخر حذف و # از هشتگ‌های وسط متن برداشته بشه
SKIP_REPLIES = _bool("SKIP_REPLIES", "1")        # رد کردن ریپلای‌ها
SKIP_RETWEETS = _bool("SKIP_RETWEETS", "1")      # رد کردن ریتوییت‌ها
SEND_IMAGE = _bool("SEND_IMAGE", "1")            # ارسال عکس توییت
# رفتار توییت‌های بلندتر از ۱۰۲۴ کاراکتر:
#   preview      = متن کامل + پیش‌نمایش بزرگ عکس بالای متن (پیش‌فرض)
#   photo_first  = اول عکس، بعد متن کامل زیرش
LONG_CAPTION_MODE = os.getenv("LONG_CAPTION_MODE", "preview").strip().lower()
if LONG_CAPTION_MODE not in ("preview", "photo_first"):
    LONG_CAPTION_MODE = "preview"
SEND_VIDEO = _bool("SEND_VIDEO", "1")            # ارسال ویدیوی توییت
MAX_VIDEO_MB = _int("MAX_VIDEO_MB", 50)          # سقف آپلود بات در تلگرام ۵۰ مگابایته
POST_WITHOUT_CAPTION = _bool("POST_WITHOUT_CAPTION", "0")  # ارسال توییت‌هایی که فقط مدیا دارن و متن ندارن
POST_UNTRANSLATED = _bool("POST_UNTRANSLATED", "0")        # اگه ترجمه شکست خورد، متن اصلی ارسال بشه؟
# instanceهای Lingva (پراکسی گوگل ترنسلیت؛ درخواست از IP خود instance به گوگل می‌ره نه IP رندر)
LINGVA_INSTANCES = [
    u.strip().rstrip("/")
    for u in os.getenv(
        "LINGVA_INSTANCES",
        "https://lingva.ml,https://translate.plausibility.cloud,"
        "https://lingva.garudalinux.org,https://translate.projectsegfau.lt",
    ).split(",")
    if u.strip()
]
# ایمیل برای MyMemory (پارامتر de): سقف روزانه از ۵۰۰۰ به ۵۰۰۰۰ کاراکتر می‌رسه. نیاز به ثبت‌نام نداره.
MYMEMORY_EMAIL = os.getenv("MYMEMORY_EMAIL", "").strip()
# پروکسی برای درخواست‌های مترجم‌های رایگان (deep, gtx, lingva, mymemory) تا IP رندر دیده نشه.
# چند پروکسی را با کاما یا خط جدید جدا کن. مثال: http://user:pass@host:port یا socks5://user:pass@host:port
# اگه فقط یک آدرس «چرخشی» (rotating) داری، همون یکی کافیه؛ هر درخواست IP جدید می‌گیره.
# وقتی پروکسی تنظیم باشه، این مترجم‌ها فقط از طریق پروکسی درخواست می‌زنن.
TRANSLATE_PROXIES = [
    p.strip()
    for p in (os.getenv("TRANSLATE_PROXIES") or os.getenv("TRANSLATE_PROXY", "")).replace("\n", ",").split(",")
    if p.strip()
]
TRANSLATE_PROXY_TRIES = _int("TRANSLATE_PROXY_TRIES", 3)   # برای هر درخواست حداکثر چند بار با IP/پروکسی جدید
# فرهنگ لغت جایگزینی روی خروجی ترجمه: «کلمه=جایگزین» با کاما جدا. «عاجل=فوری» همیشه هست.
# مثال: TRANSLATE_GLOSSARY=منتجب=نامزد,رئيس=رئیس
TRANSLATE_GLOSSARY = {"عاجل": "فوری"}
for _pair in os.getenv("TRANSLATE_GLOSSARY", "").split(","):
    if "=" in _pair:
        _k, _v = _pair.split("=", 1)
        if _k.strip():
            TRANSLATE_GLOSSARY[_k.strip()] = _v.strip()
# حداقل فاصله (ثانیه) بین دو درخواست ترجمه به یک مترجم
TRANSLATE_MIN_GAP = float(os.getenv("TRANSLATE_MIN_GAP", "0.7") or 0.7)

# فاصله‌ی بین درخواست به منبع‌های مختلف (ثانیه) و مدت توقف بعد از خطای ۴۲۹/چالش Cloudflare روی rsshub
SOURCE_DELAY = float(os.getenv("SOURCE_DELAY", "3") or 3)
FEED_BACKOFF_MINUTES = _int("FEED_BACKOFF_MINUTES", 10)
# گزارش خطا به ادمین در تلگرام (فقط اگه ADMIN_ID تنظیم باشه): حداکثر هر چند ساعت یک‌بار
ADMIN_NOTICE_HOURS = _int("ADMIN_NOTICE_HOURS", 6)
# توقف نرم: بعد از این‌همه ثانیه از شروع اجرا، منبع‌های باقی‌مونده به اجرای بعدی می‌رن (0 = بدون محدودیت).
# برای GitHub Actions مفیده تا قبل از timeout کار، وضعیت ذخیره بشه.
RUN_DEADLINE_SECONDS = _int("RUN_DEADLINE_SECONDS", 0)
SEEN_LIMIT = _int("SEEN_LIMIT", 100)             # تعداد توییت‌های دیده‌شده که برای هر منبع نگه داشته می‌شه

# ---------- ترجمه ----------
# گوگل (روش رایگان) IP هاست‌های ابری مثل Render رو معمولاً بلاک می‌کنه (خطای 429).
# با تنظیم هر کدوم از کلیدهای زیر، اون مترجم خودکار اول امتحان می‌شه.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip()
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY", "").strip()
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "").strip()
AZURE_TRANSLATOR_ENDPOINT = os.getenv(
    "AZURE_TRANSLATOR_ENDPOINT", "https://api.cognitive.microsofttranslator.com"
).strip().rstrip("/")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()  # Google Cloud Translation
# Cloudflare Workers AI (مدل m2m100): رایگان، بدون کارت، و مستقل از بلاک IP گوگل
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
# مدل زبانی Workers AI برای ترجمه (دقیق‌تر از m2m100). سهمیه‌ی رایگان ۱۰٬۰۰۰ neuron در روز بین همه‌ی مدل‌ها مشترکه.
# فهرست مدل‌ها به ترتیب اولویت (با کاما). مدلی که حساب بهش دسترسی نداشته باشه (403) خودکار کنار گذاشته می‌شه
# و مدل بعدی امتحان می‌شه. اگه CLOUDFLARE_LLM_MODEL هم بذاری، اول از همه امتحان می‌شه.
# ترتیب بر اساس هزینه‌ی neuron (سهمیه‌ی رایگان ۱۰٬۰۰۰ در روز و مشترک بین همه‌ی مدل‌هاست):
#  - Gemma 3 12B از ۲۰۲۶-۰۵-۳۰ منسوخ شده (خطای «account is not allowed to access» همین است)؛ جایگزینش Gemma 4 است.
#  - Mistral Small تقریباً ۴ برابر ارزان‌تر از Llama 70B در توکن خروجی است.
#  - Llama 3.3 70B دقیق است ولی توکن خروجی‌اش گران است و سهمیه را زود تمام می‌کند؛ آخرین گزینه است.
# مدلی که وجود نداشته باشد یا حساب به آن دسترسی نداشته باشد خودکار کنار گذاشته می‌شود.
_cf_models = [
    "@cf/google/gemma-4-26b-a4b-it",
    "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
]
CLOUDFLARE_LLM_MODELS = [
    m.strip()
    for m in os.getenv("CLOUDFLARE_LLM_MODELS", ",".join(_cf_models)).split(",")
    if m.strip()
]
CLOUDFLARE_LLM_MODEL = os.getenv("CLOUDFLARE_LLM_MODEL", "").strip()
if CLOUDFLARE_LLM_MODEL:
    CLOUDFLARE_LLM_MODELS = [CLOUDFLARE_LLM_MODEL] + [m for m in CLOUDFLARE_LLM_MODELS if m != CLOUDFLARE_LLM_MODEL]

# مترجم‌های سازگار با OpenAI (هر سرویسی که /chat/completions داشته باشه: Groq, Cerebras, OpenRouter, Mistral و...).
# تا ۳ سرویس با پسوند خالی، 2 و 3 تعریف می‌شه. مثال:
#   OPENAI_COMPAT_BASE_URL=https://api.cerebras.ai/v1
#   OPENAI_COMPAT_API_KEY=...
#   OPENAI_COMPAT_MODEL=...   (اسم دقیق مدل را از مستندات همان سرویس بردار)
OPENAI_COMPAT = {}
for _s in ("", "2", "3"):
    _base = os.getenv(f"OPENAI_COMPAT{_s}_BASE_URL", "").strip().rstrip("/")
    _key = os.getenv(f"OPENAI_COMPAT{_s}_API_KEY", "").strip()
    _model = os.getenv(f"OPENAI_COMPAT{_s}_MODEL", "").strip()
    if _base and _key and _model:
        OPENAI_COMPAT["openai_compat" + _s] = {"base": _base, "key": _key, "model": _model}

_default_providers = []
if ANTHROPIC_API_KEY:
    _default_providers.append("claude")
if AZURE_TRANSLATOR_KEY:
    _default_providers.append("azure")
if GOOGLE_TRANSLATE_API_KEY:
    _default_providers.append("gcloud")
if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
    _default_providers.append("cloudflare_llm")  # m2m100 ("cloudflare") به‌صورت پیش‌فرض نیست؛ اسم موجودات رو غلط ترجمه می‌کنه
_default_providers += list(OPENAI_COMPAT)  # سرویس‌های سازگار با OpenAI بعد از Cloudflare و قبل از مترجم‌های گوگلی
_default_providers += ["deep", "gtx", "lingva", "mymemory"]
# ترتیب مترجم‌ها (از بین: claude, azure, gcloud, cloudflare_llm, cloudflare, openai_compat[2|3], deep, gtx, lingva, mymemory)
TRANSLATE_PROVIDERS = [
    p.strip().lower()
    for p in os.getenv("TRANSLATE_PROVIDERS", ",".join(_default_providers)).split(",")
    if p.strip()
]
# بعد از خطای 429 (محدودیت)، مترجم به این مدت (دقیقه) کنار گذاشته می‌شه
TRANSLATE_BLOCK_MINUTES = _int("TRANSLATE_BLOCK_MINUTES", 30)

# ---------- فایل‌ها ----------
DATA_DIR = Path(os.getenv("DATA_DIR", "."))
SOURCES_FILE = DATA_DIR / "sources.json"
FILTERS_FILE = DATA_DIR / "filters.json"

# محدودیت‌های تلگرام
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096


def missing_settings() -> list:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not CHANNEL_ID:
        missing.append("CHANNEL_ID")
    if not ADMIN_ID:
        missing.append("ADMIN_ID")
    if not RSS_INSTANCES:
        missing.append("RSSHUB_URL یا PUBLIC_INSTANCES")
    return missing
