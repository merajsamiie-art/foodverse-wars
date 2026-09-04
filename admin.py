# ⚙️ Admin Engine — بن، هدیه، پیام همگانی، آمار (فقط ADMIN_IDS)
import asyncio

import db
import perf
import player
from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def ban(target_user_id: int) -> str:
    p = player.get(target_user_id)
    if not p:
        return "👤 بازیکنی نیست."
    player.update(target_user_id, banned=1)
    return f"🚫 {p['name']} از فوودورس اخراج شد."


def unban(target_user_id: int) -> str:
    p = player.get(target_user_id)
    if not p:
        return "👤 بازیکنی نیست."
    player.update(target_user_id, banned=0)
    return f"✅ {p['name']} بخشیده شد. سزاوارش بود؟ شکی نیست که نه."


def give(target_user_id: int, what: str, qty: int) -> str:
    p = player.get(target_user_id)
    if not p:
        return "👤 بازیکنی نیست."
    qty = int(qty)
    if what in ("fc", "meat", "cheese", "sauce", "potato", "metal", "crystal"):
        player.grant(target_user_id, **{what: qty})
        return f"🎁 به {p['name']} داده شد: {what} ×{qty}"
    from registry import ITEMS
    if what in ITEMS:
        player.add_item(target_user_id, what, qty)
        return f"🎁 به {p['name']} داده شد: {ITEMS[what]['emoji']} {ITEMS[what]['name']} ×{qty}"
    return "❓ چنین چیزی نیست."


async def broadcast(bot, text: str) -> int:
    """پیام به همه‌ی دنیاهای فعال — با نرخ مجاز تلگرام (~۲۰/ثانیه)."""
    chats = db.db().q("SELECT DISTINCT chat_id FROM worlds WHERE started=1")
    n = 0
    for ch in chats:
        try:
            await bot.send_message(ch["chat_id"], text)
            n += 1
        except Exception:
            continue
        await asyncio.sleep(0.05)
    return n


def stats_text() -> str:
    w = db.db().one("SELECT COUNT(*) c FROM worlds WHERE started=1")["c"]
    au = db.db().one("SELECT COUNT(*) c FROM accounts")["c"]
    wp = db.db().one("SELECT COUNT(*) c FROM world_players")["c"]
    tx = db.db().one("SELECT COUNT(*) c FROM txlog")["c"]
    ords = db.db().one("SELECT COUNT(*) c FROM orders")["c"]
    al = db.db().one("SELECT COUNT(*) c FROM alliances")["c"]
    return (f"{perf.STATS.text()}\n"
            f"🌍 دنیاهای فعال: {w:,} | 🧍 حساب‌های یکتا: {au:,} | 👤 عضویت دنیا: {wp:,}\n"
            f"🤝 اتحادها: {al:,} | 🛒 سفارش‌ها: {ords:,} | 📋 لاگ‌ها: {tx:,}")
