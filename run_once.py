"""اجرای یک‌باره‌ی ربات (برای GitHub Actions): فهرست‌ها رو همگام می‌کنه، فیدها رو چک می‌کنه،
ترجمه و ارسال می‌کنه، خلاصه‌ی اجرا رو می‌نویسه و خارج می‌شه."""
import asyncio
import os
import sys

from telegram import Bot

import config
import feed
import lists_sync
import poster
import textutils


def write_summary(posted: int, sync_notes: list):
    """خلاصه‌ی اجرا برای صفحه‌ی Actions (با گوشی راحت خونده می‌شه)."""
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if not path:
        return
    out = ["## نتیجه‌ی اجرا", f"- پست ارسال‌شده: **{posted}**"]
    out += [f"- {n}" for n in sync_notes]
    errors = poster.STATS["errors"]
    if errors:
        out += ["", f"### ⚠️ منابع دارای خطا ({len(errors)})"]
        out += [f"- **{name}**: {err[:200]}" for name, err in list(errors.items())[:30]]
    skipped = poster.STATS["skipped"]
    if skipped:
        out += ["", "### ℹ️ پست‌های ردشده"]
        out += [f"- **{name}**: {note[:150]}" for name, note in list(skipped.items())[:30]]
    out += ["", "### 🌐 مترجم‌ها"] + textutils.translator_status()
    backoff = feed.feed_backoff_status()
    if backoff:
        out += ["", "### ⏸ rsshub"] + backoff
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
    except OSError as e:
        print(f"خلاصه نوشته نشد: {e}")


async def main() -> int:
    missing = [n for n, v in (("BOT_TOKEN", config.BOT_TOKEN), ("CHANNEL_ID", config.CHANNEL_ID)) if not v]
    if not config.RSS_INSTANCES:
        missing.append("RSSHUB_URL")
    if missing:
        print("❌ این تنظیمات خالی هستن: " + ", ".join(missing))
        return 1

    sync_notes = lists_sync.sync_all()
    for note in sync_notes:
        print(note)

    print(f"instanceها: {config.RSS_INSTANCES} | route: {config.FEED_ROUTE} | مترجم‌ها: {config.TRANSLATE_PROVIDERS}")
    async with Bot(config.BOT_TOKEN) as bot:
        posted = await poster.check_and_post(bot)

    print(f"\n✅ اجرا تمام شد. پست ارسال‌شده: {posted}")
    for name, err in poster.STATS["errors"].items():
        print(f"⚠️ {name}: {err[:200]}")
    for name, note in poster.STATS["skipped"].items():
        print(f"ℹ️ {name}: {note[:150]}")
    write_summary(posted, sync_notes)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
