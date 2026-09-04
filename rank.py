# 🏆 Rank Engine — رتبه‌بندی گروهی و جهانی (حساب جهانی + کش ⚡)
import db
import perf

BOARDS = {
    "power":  "💪 قدرتمندترین",
    "rich":   "🪙 ثروتمندترین",
    "army":   "🪖 بزرگ‌ترین ارتش",
    "wins":   "⚔️ بیشترین پیروزی",
    "colony": "🏝️ بیشترین مستعمره",
    "boss":   "👑 بیشترین آسیب باس",
}

# a = accounts
SCORE_SQL = {
    "power": ("(a.level * 50 "
              "+ (SELECT COALESCE(SUM(count),0) FROM units u WHERE u.user_id=a.user_id) * 20 "
              "+ (SELECT COALESCE(SUM(level),0) FROM buildings b WHERE b.user_id=a.user_id) * 30 "
              "+ a.colonies * 100)"),
    "rich": "a.fc",
    "army": "(SELECT COALESCE(SUM(count),0) FROM units u WHERE u.user_id=a.user_id)",
    "wins": "a.wins",
    "colony": "a.colonies",
    "boss": "a.boss_dmg",
}


def board_text(scope: str, key: str, chat_id: int) -> str:
    title = BOARDS.get(key, BOARDS["power"])
    score = SCORE_SQL.get(key, SCORE_SQL["power"])
    ck = (scope, key, chat_id)
    cached = perf.LB_CACHE.get(ck)
    if cached is not None:
        return cached
    if scope == "global":
        rows = db.db().q(f"SELECT a.name, a.avatar, {score} score FROM accounts a "
                         f"ORDER BY score DESC LIMIT 10")
    else:
        rows = db.db().q(f"""SELECT a.name, a.avatar, {score} score
                             FROM accounts a JOIN world_players w ON w.user_id=a.user_id
                             WHERE w.chat_id=? ORDER BY score DESC LIMIT 10""", (chat_id,))
    scope_fa = "🌍 جهانی" if scope == "global" else "👥 این دنیا"
    medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
    lines = [f"🏆 <b>رتبه‌بندی {scope_fa}</b> — {title}", ""]
    for i, r in enumerate(rows):
        lines.append(f"{medals[i]} {r['avatar']} {r['name']} — {perf.fmt(r['score'])}")
    out = "\n".join(lines)
    perf.LB_CACHE.set(ck, out)
    return out
