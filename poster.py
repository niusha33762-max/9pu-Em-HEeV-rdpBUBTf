"""منطق اصلی: چک کردن منابع توییتر، ترجمه‌ی متن و ارسال به کانال."""
import asyncio
import calendar
import time
from collections import Counter
from html import escape

import feedparser
from telegram import LinkPreviewOptions, InputFile

import config
import storage
import textutils
from feed import (
    fetch_feed, extract_media, extract_video, download_image, download_video,
)

run_lock = asyncio.Lock()  # جلوگیری از اجرای همزمان دستی و خودکار

# وضعیت آخرین اجرا (برای نمایش در پنل «وضعیت» و «اجرای دستی»)
STATS = {"last_run": None, "last_posted": 0, "errors": {}, "skipped": {}}


def guid_of(entry):
    return entry.get("id") or entry.get("link") or entry.get("title")


def raw_html_of(entry) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    if not raw and entry.get("content"):
        try:
            raw = entry["content"][0].get("value", "")
        except (IndexError, AttributeError, TypeError):
            raw = ""
    return raw or entry.get("title") or ""


async def send_post(bot, caption: str, name: str, image, media_url, video):
    """
    اولویت با متنه:
    - ویدیو/عکس + کپشن تا ۱۰۲۴ کاراکتر: در یک پیام
    - کپشن بلندتر با ویدیو: اول ویدیو، بعد متن کامل زیرش
    - کپشن بلندتر با عکس: طبق LONG_CAPTION_MODE (preview یا photo_first)
    اگه مدیا مشکل داشته باشه، کپشن به هر حال ارسال می‌شه.
    True/False برمی‌گرداند (فقط شکست ارسال متن، شکست حساب می‌شه).
    """
    chat = config.CHANNEL_ID
    footer_plain = f"{config.SIGNATURE} | {name}"
    footer = f"{escape(config.SIGNATURE)} | {escape(name)}"

    limit = config.MESSAGE_LIMIT - len(footer_plain) - 10
    if len(caption) > limit:
        caption = caption[:limit].rstrip() + "…"

    body = f"<b>{escape(caption)}</b>\n\n{footer}" if caption else footer
    plain_len = (len(caption) + 2 if caption else 0) + len(footer_plain)
    fits_caption = plain_len <= config.CAPTION_LIMIT
    preview = LinkPreviewOptions(is_disabled=True)
    media_sent = False

    # ---- ویدیو ----
    if video:
        try:
            vfile = InputFile(video, filename="video.mp4")
            if fits_caption:
                await bot.send_video(chat_id=chat, video=vfile, caption=body,
                                     parse_mode="HTML", supports_streaming=True)
                return True
            await bot.send_video(chat_id=chat, video=vfile, supports_streaming=True)
            media_sent = True
        except Exception as e:
            print(f"send_video failed: {e}")

    # ---- عکس ----
    if not media_sent and image:
        if fits_caption:
            try:
                await bot.send_photo(chat_id=chat, photo=image, caption=body, parse_mode="HTML")
                return True
            except Exception as e:
                print(f"send_photo with caption failed: {e}")
        elif config.LONG_CAPTION_MODE == "photo_first":
            try:
                await bot.send_photo(chat_id=chat, photo=image)
            except Exception as e:
                print(f"send_photo (photo_first) failed: {e}")
        elif media_url:  # preview
            preview = LinkPreviewOptions(
                url=media_url, prefer_large_media=True, show_above_text=True
            )

    # ---- متن ----
    try:
        await bot.send_message(chat_id=chat, text=body, parse_mode="HTML",
                               link_preview_options=preview)
        return True
    except Exception as e:
        print(f"Send error: {e}")
        if preview.url:  # شاید مشکل از پیش‌نمایش بوده؛ یک بار بدون پیش‌نمایش
            try:
                await bot.send_message(
                    chat_id=chat, text=body, parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
                return True
            except Exception as e2:
                print(f"Send fallback error: {e2}")
        return False


def entry_timestamp(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return calendar.timegm(t) if t else None


def sort_newest_first(entries):
    """بر اساس زمان انتشار مرتب می‌کند (توییت پین‌شده ممکنه اول فید بیاد)."""
    entries = list(entries)
    if entries and all(entry_timestamp(e) is not None for e in entries):
        return sorted(entries, key=entry_timestamp, reverse=True)
    return entries


async def process_source(bot, name: str, info: dict):
    """
    خروجی: (guidهای پردازش‌شده, تعداد پست ارسال‌شده, پیام خطا یا '', خلاصه‌ی پست‌های ردشده)
    به‌جای یک last_guid، فهرست توییت‌های دیده‌شده (seen) نگه داشته می‌شه تا ترتیب فید
    (مثلاً توییت پین‌شده) باعث از دست رفتن توییت جدید نشه.
    """
    username = info.get("username")
    if not username:
        return [], 0, "یوزرنیم خالی است", ""

    rss, _used, errors = await asyncio.to_thread(fetch_feed, username)
    if not rss:
        print(f"⚠️ هیچ instance ای برای @{username} جواب نداد")
        return [], 0, errors, ""

    feed = feedparser.parse(rss)
    if not feed.entries:
        return [], 0, "فید خالی است", ""

    seen = list(info.get("seen") or ([info["last_guid"]] if info.get("last_guid") else []))
    seen_set = set(seen)

    unseen = [e for e in sort_newest_first(feed.entries) if guid_of(e) and guid_of(e) not in seen_set]
    print(f"[{name}] @{username}: پست‌های فید={len(feed.entries)} | دیده‌شده‌های ذخیره‌شده={len(seen)} | جدید={len(unseen)}")
    if not unseen:
        return [], 0, "", ""

    # بار اول: فقط جدیدترین توییت ارسال می‌شه و بقیه «دیده‌شده» حساب می‌شن
    limit = 1 if not seen else config.MAX_PER_RUN
    to_process = unseen[:limit]
    done = [guid_of(e) for e in unseen[limit:]]   # قدیمی‌تر از سقف: بدون ارسال دیده‌شده
    to_process.reverse()                          # قدیمی به جدید

    posted = 0
    skipped = Counter()

    def notes():
        return "، ".join(f"{k}: {v}" for k, v in skipped.items())

    for entry in to_process:
        guid = guid_of(entry)
        raw = raw_html_of(entry)
        plain = textutils.clean_html(raw)

        # ریپلای و ریتوییت (پردازش‌شده حساب می‌شن تا دوباره بررسی نشن)
        if config.SKIP_RETWEETS and textutils.is_retweet(plain):
            skipped["ریتوییت"] += 1
            done.append(guid)
            continue
        if config.SKIP_REPLIES and textutils.is_reply(plain):
            skipped["ریپلای"] += 1
            done.append(guid)
            continue

        video_url = extract_video(entry, raw) if config.SEND_VIDEO else None
        media_url = extract_media(entry, raw) if config.SEND_IMAGE else None
        has_media = bool(video_url or media_url)

        caption = textutils.prepare_caption(raw)
        empty = len(caption) < config.MIN_CAPTION_LEN

        if empty and not (config.POST_WITHOUT_CAPTION and has_media):
            skipped["بدون متن (فقط مدیا)" if has_media else "متن کوتاه/خالی"] += 1
            done.append(guid)
            continue
        if not empty and textutils.is_error_content(caption):
            skipped["محتوای خطا"] += 1
            done.append(guid)
            continue

        caption_fa = ""
        if not empty:
            caption_fa, ok = await asyncio.to_thread(textutils.translate, caption)
            if not ok:
                if not config.POST_UNTRANSLATED:
                    # همین‌جا متوقف می‌شیم؛ دفعه‌ی بعد دوباره تلاش می‌شه
                    return done, posted, f"ترجمه ناموفق: {textutils.LAST_ERROR[:120]}", notes()
                print(f"⚠️ ترجمه ناموفق؛ متن اصلی ارسال می‌شود (@{username})")
            caption_fa = textutils.apply_filters(textutils.remove_urls(caption_fa))
            if len(caption_fa) < config.MIN_CAPTION_LEN and not (config.POST_WITHOUT_CAPTION and has_media):
                skipped["متن بعد از فیلتر خالی شد"] += 1
                done.append(guid)
                continue

        # ---- دانلود مدیا ----
        video = None
        image = None
        if video_url:
            video = await asyncio.to_thread(
                download_video, video_url, config.MAX_VIDEO_MB * 1024 * 1024
            )
            if video is None:
                skipped["ویدیو دانلود نشد"] += 1
        if video is None and media_url:
            image = await asyncio.to_thread(download_image, media_url)
            if image is None:
                media_url = None  # لینک در دسترس نیست؛ پیش‌نمایشش هم کار نمی‌کنه

        if await send_post(bot, caption_fa, name, image, media_url, video):
            done.append(guid)
            posted += 1
            await asyncio.sleep(2)
        else:
            return done, posted, "ارسال به کانال شکست خورد (دسترسی بات به کانال را چک کن)", notes()

    return done, posted, "", notes()


async def check_and_post(bot) -> int:
    async with run_lock:
        sources = storage.load_sources()
        updates = {}
        errors = {}
        skipped = {}
        posted = 0

        started = time.time()
        skip_sleep = True
        for i, (name, info) in enumerate(sources.items()):
            if config.RUN_DEADLINE_SECONDS and time.time() - started > config.RUN_DEADLINE_SECONDS:
                print(f"⏱ مهلت اجرا ({config.RUN_DEADLINE_SECONDS}s) تموم شد؛ بقیه‌ی منبع‌ها به اجرای بعدی می‌رن")
                break
            if i and not skip_sleep:
                await asyncio.sleep(config.SOURCE_DELAY)
            skip_sleep = False
            try:
                done, count, err, notes = await process_source(bot, name, info)
            except Exception as e:
                print(f"Error processing {name}: {e}")
                errors[name] = f"{type(e).__name__}: {e}"[:150]
                continue
            skip_sleep = "backoff" in (err or "")  # درخواستی زده نشده؛ نیازی به فاصله نیست
            posted += count
            if err:
                errors[name] = err[:200]
            if notes:
                skipped[name] = notes
            if done:
                updates[name] = done
                # بعد از هر منبع ذخیره می‌کنیم تا اگه اجرا وسطش قطع شد (timeout/لغو) پست تکراری نره
                current = storage.load_sources()
                if name in current:
                    seen = list(current[name].get("seen") or [])
                    seen += [g for g in done if g not in seen]
                    current[name]["seen"] = seen[-config.SEEN_LIMIT:]
                    current[name]["last_guid"] = done[-1]
                    storage.save_sources(current)

        STATS["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        STATS["last_posted"] = posted
        STATS["errors"] = errors
        STATS["skipped"] = skipped
        return posted
