# 🖼 Media Engine — Registry تصاویر با Telegram File ID (بدون آپلود مجدد)
import os

import db

IMG_DIR = os.path.join(os.path.dirname(__file__), "assets", "img")
TABLE = "CREATE TABLE IF NOT EXISTS media(key TEXT PRIMARY KEY, file_id TEXT, kind TEXT, at REAL)"


def ensure_table():
    db.db().ex(TABLE)


def get(key: str) -> dict:
    ensure_table()
    r = db.db().one("SELECT * FROM media WHERE key=?", (key,))
    return dict(r) if r else None


def set_file_id(key: str, file_id: str, kind: str = "photo"):
    ensure_table()
    db.db().ex("INSERT OR REPLACE INTO media(key, file_id, kind, at) VALUES(?,?,?,?)",
               (key, file_id, kind, db.now()))


def remove(key: str) -> bool:
    ensure_table()
    r = db.db().ex("DELETE FROM media WHERE key=?", (key,))
    return bool(r.rowcount)


def fs_path(key: str) -> str | None:
    """فایل باندل‌شده در ریپو (اولین ارسال از اینجا)."""
    for ext in (".png", ".jpg"):
        p = os.path.join(IMG_DIR, key + ext)
        if os.path.exists(p):
            return p
    return None


def list_keys() -> list:
    ensure_table()
    rows = db.db().q("SELECT key FROM media ORDER BY key")
    bundled = sorted(os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else []
    fs = {f.rsplit(".", 1)[0] for f in bundled if f.endswith((".png", ".jpg"))}
    return sorted({r["key"] for r in rows} | fs)


async def send(bot, chat_id: int, key: str, caption: str = None):
    """ارسال تصویر با کش File ID: اولین بار فایل، بعداً فقط file_id (سریع و بی‌هزینه)."""
    ensure_table()
    m = get(key)
    from aiogram.types import BufferedInputFile
    if m and m["file_id"]:
        return await bot.send_photo(chat_id, photo=m["file_id"], caption=caption,
                                    parse_mode="HTML")
    p = fs_path(key)
    if not p:
        return None
    with open(p, "rb") as f:
        data = f.read()
    fname = os.path.basename(p)
    msg = await bot.send_photo(chat_id, photo=BufferedInputFile(data, fname),
                               caption=caption, parse_mode="HTML")
    if msg.photo:
        set_file_id(key, msg.photo[-1].file_id, "photo")
    return msg


async def react(bot, chat_id: int, message_id: int, emoji: str = "👁"):
    """ری‌اکشن بی‌سروصدا (ضداسپم واقعی: به‌جای پیام). fail-safe."""
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id,
                                       reaction=[{"type": "emoji", "emoji": emoji}])
        return True
    except Exception:
        return False
