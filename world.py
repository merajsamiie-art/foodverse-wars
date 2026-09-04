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
    """۴+ عضو → روشن. → (n, آواتارها, started)"""
    ensure(chat_id)
    rows = db.db().q("""SELECT a.avatar FROM world_players w JOIN accounts a ON a.user_id=w.user_id
                        WHERE w.chat_id=? ORDER BY w.joined""", (chat_id,))
    n = len(rows)
    names = " ".join(r["avatar"] for r in rows[-12:])
    if n >= MIN_PLAYERS:
        db.db().ex("UPDATE worlds SET started=1 WHERE chat_id=?", (chat_id,))
        return n, names, True
    return n, names, False
