# ربات اخبار توییتر → ترجمه → کانال تلگرام (GitHub Actions + cron-job.org)

این نسخه روی هیچ سروری نمی‌ماند. **cron-job.org** هر ۱۰ تا ۱۵ دقیقه با API گیتهاب این workflow را فعال می‌کند. GitHub Actions rsshub را موقتاً با Docker بالا می‌آورد، فیدها را می‌گیرد، ترجمه و ارسال می‌کند و وضعیت (`sources.json` با فهرست پست‌های دیده‌شده) را در همان ریپو commit می‌کند.

## تفاوت با نسخه‌ی سرور
- پنل تلگرام ندارد. منابع را با ویرایش `sources.json` و فیلترها را با ویرایش `filters.json` در خود ریپو مدیریت کن. اگر همزمان با اجرای ربات ویرایش کنی، تغییرت با وضعیت ربات ادغام می‌شود (`merge_state.py`).
- بدون سرور و بدون کارت.

## مدیریت منابع و فیلترها (ساده برای گوشی)
ویرایش JSON با گوشی سخته، پس می‌توانی از فایل‌های متنی استفاده کنی (`lists_sync.py`):
- `sources.txt`: هر خط `نام نمایشی = یوزرنیم` (یا فقط یوزرنیم). خط‌های `#` توضیح‌اند. نمونه: `sources.example.txt`
- `filters.txt`: هر خط یک کلمه یا عبارت. نمونه: `filters.example.txt`
- اگر این فایل‌های متنی وجود داشته باشند **مرجع اصلی‌اند** و در هر اجرا `sources.json` و `filters.json` را با آن‌ها یکی می‌کنند: منبعی که در `sources.txt` نباشد حذف می‌شود و پست‌های دیده‌شده‌ی منابع باقی‌مانده حفظ می‌شوند. اگر وجود نداشته باشند، همان JSONها استفاده می‌شوند.
- نتیجه‌ی هر اجرا (پست‌های ارسال‌شده، خطاها، وضعیت مترجم‌ها) در صفحه‌ی همان اجرا در تب Actions، بخش Summary نوشته می‌شود.

## ۱. راه‌اندازی ریپو
۱. فایل‌ها را در ریشه‌ی یک ریپوی جدید بگذار (فایل‌های مخفی `.github/workflows/run-bot.yml`، `.python-version` و `.gitignore` هم).
۲. در Settings > Secrets and variables > Actions این Secretها را بساز: `BOT_TOKEN`، `CHANNEL_ID`، `TWITTER_AUTH_TOKEN`، `CLOUDFLARE_ACCOUNT_ID`، `CLOUDFLARE_API_TOKEN` (اختیاری: `CHANNEL_SIGNATURE`، `OPENAI_COMPAT_BASE_URL`، `OPENAI_COMPAT_API_KEY`، `OPENAI_COMPAT_MODEL`).
۳. Settings > Actions > General > Workflow permissions را روی «Read and write permissions» بگذار.
۴. منابع و فیلترها را بگذار: یا `sources.json` و `filters.json` را از ریپوی قبلی (branch به اسم data) کپی کن، یا `sources.txt` و `filters.txt` بساز.
۵. تب Actions > run-bot > Run workflow را یک‌بار دستی بزن و لاگ را ببین.

## ۲. توکن گیتهاب برای cron-job.org
Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token:
- Repository access: Only select repositories، و فقط همین ریپو
- Repository permissions: **Actions = Read and write**
- مدت اعتبار را انتخاب کن (بعد از انقضا باید توکن جدید بسازی و در cron-job.org عوض کنی).
رشته‌ی توکن را همان لحظه کپی کن.

## ۳. cron-job.org
حساب رایگان بساز و Create cronjob بزن:
- URL: `https://api.github.com/repos/<OWNER>/<REPO>/actions/workflows/run-bot.yml/dispatches`
- Execution schedule: هر ۱۰ دقیقه (ریپوی private: هر ۶۰ دقیقه؛ پایین را ببین)
- Advanced: Request method = **POST**، Request body = `{"ref":"main"}`
- Headers:
  - `Authorization: Bearer <توکن گیتهاب>`
  - `Accept: application/vnd.github+json`
  - `X-GitHub-Api-Version: 2022-11-28`
  - `Content-Type: application/json`
- ذخیره کن و یک Test run بزن؛ پاسخ موفق **۲۰۴** است. بعد در تب Actions باید یک اجرای جدید ببینی.

## هزینه‌ی دقیقه‌ها
- ریپوی public: دقیقه‌ی نامحدود.
- ریپوی private: حدود ۲۰۰۰ دقیقه‌ی رایگان در ماه و هر اجرا چند دقیقه است؛ فاصله‌ی cron-job.org را ۶۰ دقیقه بگذار و بخش `schedule` را از `run-bot.yml` حذف کن.

## متغیرها
متغیرهای نسخه‌ی سرور (`MAX_PER_RUN`، `SEND_VIDEO`، `POST_UNTRANSLATED` و...) را در بخش `env` مرحله‌ی «Run bot» داخل `run-bot.yml` اضافه کن.

## فایل‌ها
- `run_once.py` اجرای یک‌باره‌ی ربات
- `save_state.sh` و `merge_state.py` ذخیره‌ی امن وضعیت در ریپو
- `poster.py`، `feed.py`، `textutils.py`، `storage.py`، `config.py` منطق ربات
