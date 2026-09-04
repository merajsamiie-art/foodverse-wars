# 👑 Boss Engine — رید گروهی: آسیب ثبت، جایزه بر مشارکت
import random

import army
import db
import perf
import player
from config import (BOSS_CHANCE, BOSS_CHECK_S, BOSS_DURATION, BOSS_UNIT_LOSS,
                    CD_BOSS, XP_BOSS_HIT)
from registry import BOSSES, ITEMS


def active(chat_id: int) -> dict:
    ch = db.db().one("SELECT * FROM worlds WHERE chat_id=?", (chat_id,))
    if ch and ch["boss_id"] and (ch["boss_until"] or 0) > db.now():
        return dict(ch)
    return {}


def spawn_tick(chat_id: int, force: bool = False) -> str | None:
    ch = db.db().one("SELECT * FROM worlds WHERE chat_id=?", (chat_id,))
    if not ch or not ch["started"]:
        return None
    t = db.now()
    if active(chat_id):
        return None
    if not force and t - (ch["last_boss_check"] or 0) < BOSS_CHECK_S:
        return None
    db.db().ex("UPDATE worlds SET last_boss_check=? WHERE chat_id=?", (t, chat_id))
    if not force:
        n = db.db().one("SELECT COUNT(*) c FROM world_players WHERE chat_id=? AND last_active>?",
                        (chat_id, t - 86400))["c"]
        if n < 2:
            return None
        if random.random() > BOSS_CHANCE:
            return None
    bid = random.choice(list(BOSSES))
    b = BOSSES[bid]
    db.db().ex("""UPDATE worlds SET boss_id=?, boss_hp=?, boss_max_hp=?, boss_until=?
                  WHERE chat_id=?""", (bid, b["hp"], b["hp"], t + BOSS_DURATION, chat_id))
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, bid))
    return (f"🚨 <b>FACTORY ALERT</b>\n"
            f"{b['emoji']} <b>{b['name']}</b> در کارخانه ظاهر شد!\n"
            f"❤️ {b['hp']:,} | 📜 {b['lore']}\n"
            f"⏳ {BOSS_DURATION // 60} دقیقه — «fw باس» برای حمله‌ی گروهی")


def attack(user_id: int, chat_id: int) -> tuple:
    p = player.get(user_id)
    w = active(chat_id)
    if not w:
        return False, "👑 الان باسی در کارخانه نیست."
    if player.is_dead(p):
        return False, "💀 مردگان نمی‌جنگند — کمی صبر کن."
    if player.on_cd(user_id, "boss"):
        return False, f"⏳ {player.cd_left(user_id, 'boss')} ثانیه."
    if army.army_size(user_id) < 3:
        return False, "🪖 حداقل ۳ سرباز لازم است."
    with perf.key_lock(("boss", user_id)):
        player.set_cd(user_id, "boss", CD_BOSS)
        b = BOSSES[w["boss_id"]]

        power = army.army_power(user_id)
        boost = 0.0
        for iid, it in ITEMS.items():
            if it.get("effect") == "boss_dmg" and player.take_item(user_id, iid, 1):
                boost = it["val"]
                break
        if random.random() < b.get("dodge", 0):
            return True, f"👑 {b['emoji']} {b['name']} جاخالی داد! حمله‌ات هدر رفت. 😼"
        dmg = round(power * random.uniform(0.35, 0.55) * (1 + boost) * (1 - b.get("resist", 0)), 1)

        new_hp = round(w["boss_hp"] - dmg, 1)
        db.db().ex("""INSERT INTO boss_dmg(chat_id, boss_id, user_id, dmg) VALUES(?,?,?,?)
                      ON CONFLICT(chat_id, boss_id, user_id) DO UPDATE SET dmg=dmg+?""",
                   (chat_id, w["boss_id"], user_id, dmg, dmg))
        player.update(user_id, boss_dmg=p["boss_dmg"] + dmg)
        player.gain_xp(user_id, XP_BOSS_HIT)
        player.dtrack(user_id, "boss_hits")

        lost = army.apply_losses(user_id, BOSS_UNIT_LOSS * random.uniform(0.5, 1.5))
        rage = new_hp < w["boss_max_hp"] * 0.3
        msg = (f"👑 <b>{b['emoji']} {b['name']}</b> — ❤️ {max(0, new_hp):,.0f}/{w['boss_max_hp']:,.0f}\n"
               f"⚔️ {p['avatar']} {p['name']}: <b>{dmg:,.0f}</b> آسیب"
               + (f" (🚀 بوستر ×{1 + boost:.1f})" if boost else "") + "\n"
               f"💢 ضدحمله‌ی باس! 💔 تلفات تو: {sum(lost.values())}"
               + ("\n😡 <b>BERSERK MODE</b> — باس خشمگین است!" if rage else ""))

        if new_hp <= 0:
            msg += _finish(chat_id, w["boss_id"], user_id)
        else:
            db.db().ex("UPDATE worlds SET boss_hp=? WHERE chat_id=?", (new_hp, chat_id))
        return True, msg


def _finish(chat_id: int, boss_id: str, last_uid: int) -> str:
    b = BOSSES[boss_id]
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0, boss_until=0
                  WHERE chat_id=?""", (chat_id,))
    rows = db.db().q("""SELECT bd.user_id, bd.dmg, a.name, a.avatar FROM boss_dmg bd
                        JOIN accounts a ON a.user_id=bd.user_id
                        WHERE bd.chat_id=? AND bd.boss_id=? ORDER BY bd.dmg DESC LIMIT 3""",
                     (chat_id, boss_id))
    if not rows:
        return "\n🏆 باس فرار کرد!"
    total = db.db().one("SELECT SUM(dmg) s FROM boss_dmg WHERE chat_id=? AND boss_id=?",
                        (chat_id, boss_id))["s"] or 1
    lo, hi = b["loot"]["fc"]
    lines = [f"\n🏆 <b>{b['name']} سقوط کرد!</b> (آسیب گروه: {total:,.0f})"]
    seen = set()
    for i, r in enumerate(rows):
        share = int(random.uniform(lo, hi) * (r["dmg"] / total) * 2.5 * (1.5 if i == 0 else 1.0))
        player.grant(r["user_id"], fc=share)
        tag = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉")
        lines.append(f"{tag} {r['avatar']} {r['name']} — آسیب {r['dmg']:,.0f} → 🪙 {share:,} FC")
        seen.add(r["user_id"])
    if last_uid not in seen:
        lp = player.get(last_uid)
        if lp:
            player.grant(last_uid, fc=int(lo * 0.8))
            lines.append(f"🎯 ضربه‌ی آخر: {lp['avatar']} {lp['name']} → 🪙 {int(lo * 0.8):,} FC")
    if random.random() < 0.65:
        drop = random.choice(b["loot"]["drops"])
        player.add_item(rows[0]["user_id"], drop, 1)
        from registry import item_name
        lines.append(f"🎁 قطره‌ی ویژه: {item_name(drop)} → {rows[0]['name']}")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, boss_id))
    return "\n".join(lines)
