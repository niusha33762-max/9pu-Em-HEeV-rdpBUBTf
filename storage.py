"""ذخیره‌سازی منابع و فیلترها: فایل محلی + commit خودکار روی گیت‌هاب."""
import json
import os
import base64
import threading
import time
import requests

import config

file_lock = threading.Lock()
github_lock = threading.Lock()

# وضعیت همگام‌سازی با گیت‌هاب. اگه بازیابی اولیه شکست بخوره، commit غیرفعال می‌شه
# تا داده‌ی قبلی روی گیت‌هاب با یک فایل خالی/ناقص بازنویسی نشه.
sync_state = {"ok": True, "detail": ""}


# ============================== GitHub ==============================
def _gh_headers():
    return {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _gh_url(file_path: str) -> str:
    return f"https://api.github.com/repos/{config.GITHUB_REPO}/contents/{file_path}"


def github_enabled() -> bool:
    return bool(config.GITHUB_TOKEN and config.GITHUB_REPO)


def github_fetch_file(file_path: str):
    """
    فایل را از گیت‌هاب می‌خواند. خروجی: (status, content)
    status = 200 موفق | 404 فایل روی گیت‌هاب نیست | None خطای شبکه/دسترسی
    """
    if not github_enabled():
        return None, None
    status = None
    for attempt in range(3):
        try:
            resp = requests.get(
                _gh_url(file_path), headers=_gh_headers(),
                params={"ref": config.GITHUB_BRANCH}, timeout=15,
            )
            status = resp.status_code
            if status == 200:
                return 200, base64.b64decode(resp.json()["content"]).decode("utf-8")
            if status == 404:
                return 404, None
            print(f"GitHub fetch {file_path}: status {status} (تلاش {attempt + 1})")
        except Exception as e:
            print(f"GitHub fetch error: {e} (تلاش {attempt + 1})")
        time.sleep(2)
    return None, None


def github_commit_file(file_path: str, content: str, message: str) -> bool:
    if not github_enabled():
        if not os.getenv("GITHUB_ACTIONS"):  # در Actions وضعیت با git ذخیره می‌شه و این پیام بی‌معنیه
            print("GITHUB_TOKEN یا GITHUB_REPO تنظیم نشده - ذخیره فقط محلی انجام شد")
        return False

    if not sync_state["ok"]:
        print(f"⛔ commit {file_path} انجام نشد: بازیابی اولیه از گیت‌هاب ناموفق بود "
              "(برای جلوگیری از بازنویسی داده‌ی قبلی). سرویس را ری‌استارت کن.")
        return False

    url = _gh_url(file_path)
    with github_lock:
        sha = None
        try:
            resp = requests.get(
                url, headers=_gh_headers(),
                params={"ref": config.GITHUB_BRANCH}, timeout=10,
            )
            if resp.status_code == 200:
                sha = resp.json().get("sha")
        except Exception as e:
            print(f"Error getting file sha: {e}")

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": config.GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        try:
            resp = requests.put(url, headers=_gh_headers(), json=payload, timeout=15)
            if resp.status_code in (200, 201):
                print(f"✅ GitHub commit موفق: {file_path}")
                return True
            print(f"❌ GitHub commit خطا: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"❌ GitHub commit exception: {e}")
        return False


def commit_in_background(file_path: str, content: str, message: str):
    """commit در ترد جدا تا event loop بلاک نشه."""
    threading.Thread(
        target=github_commit_file, args=(file_path, content, message), daemon=True
    ).start()


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _is_empty_json(path) -> bool:
    try:
        return not json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return True


def restore_from_github():
    """
    موقع شروع (بعد از هر deploy یا ری‌استارت): نسخه‌ی گیت‌هاب مرجع اصلیه و روی فایل محلی
    (که از ریپو اومده و معمولاً خالیه) می‌نشینه، تا منابع و فیلترها پاک نشن.
    - فایل روی گیت‌هاب بود: جایگزین فایل محلی می‌شه
    - فایل روی گیت‌هاب نبود (404) و فایل محلی محتوا داشت: محلی روی گیت‌هاب ذخیره می‌شه
    - خطای شبکه/دسترسی: فایل محلی دست‌نخورده می‌مونه و هشدار چاپ می‌شه
    """
    if not github_enabled():
        print("⚠️ GITHUB_TOKEN/GITHUB_REPO تنظیم نشده؛ منابع و فیلترها بعد از deploy پاک می‌شن")
        return

    for path in (config.SOURCES_FILE, config.FILTERS_FILE):
        status, content = github_fetch_file(path.name)
        if status == 200 and content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"♻️ {path.name} از گیت‌هاب (branch: {config.GITHUB_BRANCH}) بازیابی شد")
        elif status == 404:
            if path.exists() and not _is_empty_json(path):
                commit_in_background(path.name, path.read_text(encoding="utf-8"), f"Init {path.name}")
                print(f"⬆️ {path.name} روی گیت‌هاب وجود نداشت؛ نسخه‌ی محلی آپلود شد")
            else:
                print(f"ℹ️ {path.name} هنوز روی گیت‌هاب (branch: {config.GITHUB_BRANCH}) نیست")
        else:
            print(f"⚠️ بازیابی {path.name} از گیت‌هاب ناموفق بود؛ توکن، نام ریپو و branch را چک کن")


# ============================== منابع ==============================
def load_sources() -> dict:
    with file_lock:
        if not config.SOURCES_FILE.exists():
            return {}
        try:
            with open(config.SOURCES_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except json.JSONDecodeError:
            print("⚠️ sources.json خراب است")
            return {}


def save_sources(data: dict):
    content = json.dumps(data, ensure_ascii=False, indent=2)
    with file_lock:
        config.SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(config.SOURCES_FILE, "w", encoding="utf-8") as f:
            f.write(content)
    commit_in_background(config.SOURCES_FILE.name, content, "Update sources.json")


def add_source(name: str, username: str):
    data = load_sources()
    data[name] = {"username": username.strip().lstrip("@"), "last_guid": None, "seen": []}
    save_sources(data)


def remove_source(name: str) -> bool:
    data = load_sources()
    if name in data:
        del data[name]
        save_sources(data)
        return True
    return False


# ============================== فیلترها ==============================
def load_filters() -> list:
    with file_lock:
        if not config.FILTERS_FILE.exists():
            return []
        try:
            with open(config.FILTERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or []
        except json.JSONDecodeError:
            print("⚠️ filters.json خراب است")
            return []


def save_filters(data: list):
    content = json.dumps(data, ensure_ascii=False, indent=2)
    with file_lock:
        config.FILTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(config.FILTERS_FILE, "w", encoding="utf-8") as f:
            f.write(content)
    commit_in_background(config.FILTERS_FILE.name, content, "Update filters.json")


def add_filter(word: str) -> bool:
    data = load_filters()
    word = word.strip()
    if word and word not in data:
        data.append(word)
        save_filters(data)
        return True
    return False


def remove_filter(word: str) -> bool:
    data = load_filters()
    if word in data:
        data.remove(word)
        save_filters(data)
        return True
    return False
