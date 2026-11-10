"""همگام‌سازی فایل‌های متنی ساده‌ی sources.txt و filters.txt با sources.json و filters.json.

ویرایش JSON با گوشی سخته؛ برای همین می‌شه منابع و فیلترها رو در فایل متنی نوشت:
  sources.txt  هر خط: «نام نمایشی = یوزرنیم»  (یا فقط «یوزرنیم»). خط‌های # توضیحن.
  filters.txt  هر خط یک کلمه یا عبارت.
اگه فایل متنی وجود داشته باشه، مرجع اصلیه؛ اگه نباشه، JSON همون‌طور که هست استفاده می‌شه.
"""
import config
import storage


def _read_lines(path):
    if not path.exists():
        return None
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def parse_sources(lines) -> dict:
    """خروجی: {نام: یوزرنیم}"""
    result = {}
    for line in lines:
        if "=" in line:
            name, user = line.split("=", 1)
        else:
            name, user = line, line
        name, user = name.strip(), user.strip().lstrip("@")
        if not user or " " in user:
            print(f"⚠️ خط نامعتبر در sources.txt نادیده گرفته شد: {line!r}")
            continue
        result[name or user] = user
    return result


def sync_sources() -> str:
    lines = _read_lines(config.DATA_DIR / "sources.txt")
    if lines is None:
        return "sources.txt وجود نداره؛ از sources.json استفاده می‌شه"
    wanted = parse_sources(lines)
    if not wanted:
        return "⚠️ sources.txt هیچ خط معتبری نداره؛ نادیده گرفته شد (sources.json دست‌نخورده موند)"

    current = storage.load_sources()
    by_user = {info.get("username"): info for info in current.values()}   # برای حفظ «دیده‌شده‌ها» هنگام تغییر نام
    new = {}
    for name, user in wanted.items():
        old = current.get(name)
        if old and old.get("username") == user:
            new[name] = old
        elif user in by_user:
            new[name] = by_user[user]
        else:
            new[name] = {"username": user, "last_guid": None, "seen": []}

    added = [n for n in new if n not in current]
    removed = [n for n in current if n not in new]
    if new != current:
        storage.save_sources(new)
    return f"sources.txt: {len(new)} منبع (اضافه: {len(added)}، حذف: {len(removed)})"


def sync_filters() -> str:
    lines = _read_lines(config.DATA_DIR / "filters.txt")
    if lines is None:
        return "filters.txt وجود نداره؛ از filters.json استفاده می‌شه"
    unique = list(dict.fromkeys(lines))
    if unique != storage.load_filters():
        storage.save_filters(unique)
    return f"filters.txt: {len(unique)} فیلتر"


def sync_all() -> list:
    return [sync_sources(), sync_filters()]
