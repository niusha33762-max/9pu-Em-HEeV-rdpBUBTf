"""گرفتن فید توییتر از rsshub، استخراج عکس/ویدیو و دانلود مدیا. توابع این فایل همگام (sync) هستن."""
import re
import threading
import time
from html import unescape

import requests

import config

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


_feed_lock = threading.Lock()
_feed_blocked_until = {}   # آدرس instance -> زمان پایان توقف
_feed_block_reason = {}


def _feed_block(instance: str, seconds: int, reason: str):
    with _feed_lock:
        _feed_blocked_until[instance] = time.time() + seconds
        _feed_block_reason[instance] = reason[:120]
    print(f"⏸ rsshub «{instance}» برای {seconds} ثانیه کنار گذاشته شد: {reason[:120]}")


def feed_backoff_status() -> list:
    """وضعیت توقف instanceهای rsshub برای نمایش در پنل."""
    now = time.time()
    lines = []
    with _feed_lock:
        for inst in config.RSS_INSTANCES:
            until = _feed_blocked_until.get(inst, 0)
            if until > now:
                lines.append(f"• {inst}: متوقف ({int((until - now) / 60) + 1} دقیقه) — {_feed_block_reason.get(inst, '')}")
    return lines


def fetch_feed(username: str):
    """
    فید یک یوزرنیم را از اولین instanceای که جواب بده می‌گیرد.
    اگه instance خطای ۴۲۹ یا صفحه‌ی چالش Cloudflare بده، چند دقیقه کنار گذاشته می‌شه و تا اون موقع
    هیچ درخواستی بهش نمی‌ره (تا محدودیت بیشتر نشه).
    خروجی: (متن XML یا None, instance یا None, خلاصه‌ی خطاها)
    """
    route = config.FEED_ROUTE.format(username=username)
    errors = []

    for instance in config.RSS_INSTANCES:
        with _feed_lock:
            until = _feed_blocked_until.get(instance, 0)
        if until > time.time():
            errors.append(f"{instance}: backoff {int((until - time.time()) / 60) + 1} دقیقه")
            continue

        url = f"{instance}{route}"
        params = {}
        if config.RSSHUB_KEY and instance == config.RSSHUB_URL:
            params["key"] = config.RSSHUB_KEY
        try:
            resp = requests.get(
                url, params=params, timeout=config.REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            head = resp.text[:2000].lower()
            print(f"[{instance}] @{username} status={resp.status_code} len={len(resp.text)}")
            if resp.status_code == 200 and ("<rss" in head or "<feed" in head):
                return resp.text, instance, ""
            snippet = resp.text[:120].replace("\n", " ")
            errors.append(f"{instance}: {resp.status_code} {snippet}")
            print(f"[{instance}] body: {resp.text[:200]!r}")

            challenged = resp.status_code != 200 and "just a moment" in head
            if resp.status_code == 429 or challenged:
                try:
                    wait = int(resp.headers.get("Retry-After", ""))
                except ValueError:
                    wait = config.FEED_BACKOFF_MINUTES * 60
                _feed_block(instance, max(60, min(wait, 1800)), f"HTTP {resp.status_code} {'چالش Cloudflare' if challenged else 'Too Many Requests'}")
        except Exception as e:
            errors.append(f"{instance}: {type(e).__name__}")
            print(f"[{instance}] error: {e}")

    return None, None, " | ".join(errors) or "هیچ instance ای تنظیم نشده"


def extract_media(entry, raw_html: str):
    """اولین عکس مناسب پست را برمی‌گرداند (عکس پروفایل نادیده گرفته می‌شود)."""
    candidates = []

    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            if m.get("url"):
                candidates.append(m["url"])
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image") and enc.get("href"):
            candidates.append(enc["href"])

    html = unescape(raw_html or "")
    candidates += re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, re.I)
    candidates += re.findall(r"poster=[\"']([^\"']+)[\"']", html, re.I)
    candidates += re.findall(
        r"(https?://[^\"'\s<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\"'\s<>]*)?)", html, re.I
    )

    for url in candidates:
        url = url.replace("&amp;", "&").strip()
        if not url.startswith("http"):
            continue
        low = url.lower()
        is_avatar = (
            "profile_images" in low or "profile_banners" in low
            or ("profile" in low and "pic" in low) or "emoji" in low
        )
        if is_avatar:
            continue
        return url
    return None


def download_image(url: str):
    """تصویر را دانلود می‌کند تا مستقیم به تلگرام آپلود بشه."""
    try:
        resp = requests.get(
            url, timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Referer": "https://x.com/"},
        )
        ctype = resp.headers.get("Content-Type", "")
        if resp.status_code != 200 or not ctype.startswith("image/"):
            print(f"Image download failed: {resp.status_code} {ctype}")
            return None
        if len(resp.content) > 10 * 1024 * 1024:  # محدودیت عکس تلگرام
            print("Image too large")
            return None
        return resp.content
    except Exception as e:
        print(f"Image download error: {e}")
        return None


def extract_video(entry, raw_html: str):
    """لینک ویدیوی پست (اگه باشه). از enclosure، media_content و تگ‌های video/source می‌خونه."""
    candidates = []

    for key in ("media_content",):
        for m in entry.get(key, []) or []:
            if m.get("url") and (str(m.get("type", "")).startswith("video") or ".mp4" in m["url"].lower()):
                candidates.append(m["url"])
    for enc in entry.get("enclosures", []) or []:
        href = enc.get("href") or ""
        if href and (str(enc.get("type", "")).startswith("video") or ".mp4" in href.lower()):
            candidates.append(href)

    html = unescape(raw_html or "")
    candidates += re.findall(r"<video[^>]+src=[\"']([^\"']+)[\"']", html, re.I)
    candidates += re.findall(r"<source[^>]+src=[\"']([^\"']+)[\"']", html, re.I)
    candidates += re.findall(r"(https?://[^\"'\s<>]+\.(?:mp4|mov|m4v)(?:\?[^\"'\s<>]*)?)", html, re.I)

    for url in candidates:
        url = url.replace("&amp;", "&").strip()
        if url.startswith("http"):
            return url
    return None


def download_video(url: str, max_bytes: int):
    """ویدیو را دانلود می‌کند. اگه از سقف تلگرام بزرگ‌تر بود None برمی‌گرداند."""
    try:
        with requests.get(
            url, stream=True, timeout=max(config.REQUEST_TIMEOUT, 60),
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if resp.status_code != 200:
                print(f"Video download failed: {resp.status_code}")
                return None
            if not (ctype.startswith("video/") or ctype in ("application/octet-stream", "binary/octet-stream")):
                print(f"Video download: unexpected content-type {ctype}")
                return None
            length = int(resp.headers.get("Content-Length") or 0)
            if length and length > max_bytes:
                print(f"Video too large: {length} bytes")
                return None
            data = bytearray()
            for chunk in resp.iter_content(256 * 1024):
                data.extend(chunk)
                if len(data) > max_bytes:
                    print("Video too large (stream)")
                    return None
            return bytes(data)
    except Exception as e:
        print(f"Video download error: {e}")
        return None
