"""ادغام وضعیت ربات با تغییراتی که همزمان در ریپو انجام شده (مثلاً وقتی خودت sources.json را ویرایش کردی)."""
import json
import subprocess

SEEN_LIMIT = 100


def sh(*args) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


ours = json.load(open("sources.json", encoding="utf-8"))   # نسخه‌ی ربات (فهرست پست‌های دیده‌شده‌ی جدید)
sh("git", "fetch", "-q", "origin", "main")
theirs = json.loads(sh("git", "show", "origin/main:sources.json"))  # نسخه‌ی ریپو (منابع ویرایش‌شده توسط تو)

merged = {}
for name, info in theirs.items():
    info = dict(info)
    mine = ours.get(name)
    if mine and mine.get("username") == info.get("username"):
        seen = list(info.get("seen") or [])
        seen += [g for g in (mine.get("seen") or []) if g not in seen]
        info["seen"] = seen[-SEEN_LIMIT:]
        info["last_guid"] = mine.get("last_guid") or info.get("last_guid")
    merged[name] = info

sh("git", "reset", "-q", "--hard", "origin/main")
with open("sources.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"merged: {len(merged)} sources")
