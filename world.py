# 🌍 World Engine — هر گروه = دنیای مستقل، حداقل ۴ بازیکن
import db
from config import MIN_PLAYERS


def ensure(chat_id: int):
    db.db().ex("INSERT OR IGNORE INTO worlds(chat_id, created_at, last_tick) VALUES(?,?,?)",
               (chat_id, db.now(), db.now()))


def is_started(chat_id: int) -> bool:
    ensure(chat_id)
    r = db.db().one("SELECT started FROM worlds WHERE chat_id=?", (chat_id,))
    return bool(r and r["started"])


def member_count(chat_id: int) -> int:
    return db.db().one("SELECT COUNT(*) c FROM world_players WHERE chat_id=?", (chat_id,))["c"]


def try_start(chat_id: int) -> tuple[int, str, bool]:
    """شروع با شمارش واقعیِ اعضای گروه — دیگر لازم نیست ۴ نفر دستور بزنند."""
    ensure(chat_id)
    return 0, "", False   # قدیمی؛ فقط برای سازگاری


def start_now(chat_id: int, member_count: int) -> tuple[bool, str]:
    """عضوها خودکار شمرده می‌شوند: ۴+ → دنیا روشن؛ کمتر → پیام منتظر."""
    ensure(chat_id)
    if member_count >= MIN_PLAYERS:
        db.db().ex("UPDATE worlds SET started=1 WHERE chat_id=?", (chat_id,))
        return True, ""
    return False, (f"⏳ برای شروع بازی، گروه باید حداقل {MIN_PLAYERS} عضو داشته باشد — "
                   f"الان {member_count} عضو دارید. چند دوست اضافه کنید و دوباره «شروع» بزنید!")
