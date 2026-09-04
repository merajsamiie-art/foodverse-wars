# 👑 Boss Engine — رید گروهی: آسیب ثبت، جایزه بر مشارکت + تیر + استخر دنیا + اینفکتد
import json
import random

import army
import db
import perf
import player
from config import (BOSS_CHANCE, BOSS_CHECK_S, BOSS_DURATION, BOSS_TIER_HP,
                    BOSS_TIER_LOOT, BOSS_UNIT_LOSS, CD_BOSS, XP_BOSS_HIT)
from registry import BOSSES, ITEMS


TIER_BADGE = {1: "🥉 معمولی", 2: "🥈 شدید", 3: "🥇 کابوس"}


def active(chat_id: int) -> dict:
    ch = db.db().one("SELECT * FROM worlds WHERE chat_id=?", (chat_id,))
    if ch and ch["boss_id"] and (ch["boss_until"] or 0) > db.now():
        return dict(ch)
    return {}


def _tier(chat_id: int) -> int:
    """تیر باس از فعالیت دنیا: دنیای داغ‌تر = باس خطرناک‌تر و پُرپاداش‌تر."""
    t = db.now()
    rows = db.db().q("""SELECT a.level FROM world_players wp JOIN accounts a
                        ON a.user_id=wp.user_id
                        WHERE wp.chat_id=? AND wp.last_active>?""", (chat_id, t - 86400))
    n = len(rows)
    avg = sum(r["level"] for r in rows) / n if n else 0
    unlocked = 1 + (1 if (n >= 5 or avg >= 8) else 0) + (1 if (n >= 8 or avg >= 12) else 0)
    return random.choices([1, 2, 3][:unlocked], weights=[6, 3, 1][:unlocked])[0]


def _expire_loot(chat_id: int, w: dict) -> str:
    """باس فرار کرد — ولی غنیمتِ کوچکی از خودش جا گذاشت (لوط باخت)."""
    bid = w["boss_id"]
    b = BOSSES[bid]
    tier = w.get("boss_tier") or 1
    rows = db.db().q("""SELECT bd.user_id, bd.dmg, a.name, a.avatar FROM boss_dmg bd
                        JOIN accounts a ON a.user_id=bd.user_id
                        WHERE bd.chat_id=? AND bd.boss_id=? AND bd.dmg>0
                        ORDER BY bd.dmg DESC LIMIT 10""", (chat_id, bid))
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0,
                  boss_until=0, boss_tier=1 WHERE chat_id=?""", (chat_id,))
    if not rows:
        return None
    lines = [f"💨 <b>{b['emoji']} {b['name']} فرار کرد!</b>",
             "ولی در شتابِ فرار، بخشی از غنیمتش روی زمین ماند:"]
    for r in rows:
        share = int((25 + r["dmg"] * 0.03) * (1 + BOSS_TIER_LOOT * (tier - 1)))
        if share > 0:
            player.grant(r["user_id"], fc=share)
            lines.append(f"🪙 {r['avatar']} {r['name']} — {share:,} سکه (آسیب {r['dmg']:,.0f})")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, bid))
    return "\n".join(lines)


def spawn_tick(chat_id: int, force: bool = False) -> str | None:
    ch = db.db().one("SELECT * FROM worlds WHERE chat_id=?", (chat_id,))
    if not ch or not ch["started"]:
        return None
    t = db.now()
    if ch["boss_id"] and (ch["boss_until"] or 0) <= t:
        return _expire_loot(chat_id, dict(ch))    # 🎁 لوت باخت: باس فرار کرد
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
    # 🎲 استخرِ باسِ این دنیا: باس‌های اسیرشده تا بازگشتشان غایب‌اند
    try:
        pool = json.loads(ch["boss_pool"]) if ch["boss_pool"] else []
    except Exception:
        pool = []
    if not pool:
        pool = list(BOSSES)
    bid = random.choice(pool)
    b = BOSSES[bid]
    tier = 3 if force else _tier(chat_id)         # اسپاون اجباری ادمین = کابوس
    hp = round(b["hp"] * (1 + BOSS_TIER_HP * (tier - 1)))
    db.db().ex("""UPDATE worlds SET boss_id=?, boss_hp=?, boss_max_hp=?, boss_until=?,
                  boss_tier=? WHERE chat_id=?""",
               (bid, hp, hp, t + BOSS_DURATION, tier, chat_id))
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, bid))
    return (f"🚨 <b>هشدار کارخانه!</b>\n"
            f"{b['emoji']} <b>{b['name']}</b> ظاهر شد — {TIER_BADGE.get(tier, '')}\n"
            f"❤️ {hp:,} | 📜 {b['lore']}\n"
            f"⏳ {BOSS_DURATION // 60} دقیقه — «fw باس» برای حمله‌ی گروهی\n"
            f"🧟 آسیب‌برتر می‌تواند بعد از سقوطش، آن را اسیر کند: «fw اینفکت»")


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
               + ("\n😡 <b>خشمِ دیوانه‌وار!</b> — باس برافروخته است!" if rage else ""))

        if new_hp <= 0:
            msg += _finish(chat_id, w["boss_id"], user_id)
        else:
            db.db().ex("UPDATE worlds SET boss_hp=? WHERE chat_id=?", (new_hp, chat_id))
        return True, msg


def _finish(chat_id: int, boss_id: str, last_uid: int) -> str:
    b = BOSSES[boss_id]
    w = db.db().one("SELECT boss_tier FROM worlds WHERE chat_id=?", (chat_id,))
    tier = (w["boss_tier"] if w else 1) or 1
    loot_mult = 1 + BOSS_TIER_LOOT * (tier - 1)
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0,
                  boss_until=0, boss_tier=1 WHERE chat_id=?""", (chat_id,))
    rows = db.db().q("""SELECT bd.user_id, bd.dmg, a.name, a.avatar FROM boss_dmg bd
                        JOIN accounts a ON a.user_id=bd.user_id
                        WHERE bd.chat_id=? AND bd.boss_id=? ORDER BY bd.dmg DESC LIMIT 3""",
                     (chat_id, boss_id))
    if not rows:
        return "\n🏆 باس فرار کرد!"
    total = db.db().one("SELECT SUM(dmg) s FROM boss_dmg WHERE chat_id=? AND boss_id=?",
                        (chat_id, boss_id))["s"] or 1
    lo, hi = b["loot"]["fc"]
    lines = [f"\n🏆 <b>{b['name']} سقوط کرد!</b> — {TIER_BADGE.get(tier, '')} "
             f"(آسیب گروه: {total:,.0f})"]
    seen = set()
    for i, r in enumerate(rows):
        share = int(random.uniform(lo, hi) * (r["dmg"] / total) * 2.5
                    * (1.5 if i == 0 else 1.0) * loot_mult)
        player.grant(r["user_id"], fc=share)
        tag = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉")
        lines.append(f"{tag} {r['avatar']} {r['name']} — آسیب {r['dmg']:,.0f} → 🪙 {share:,} سکه")
        seen.add(r["user_id"])
    if last_uid not in seen:
        lp = player.get(last_uid)
        if lp:
            player.grant(last_uid, fc=int(lo * 0.8 * loot_mult))
            lines.append(f"🎯 ضربه‌ی آخر: {lp['avatar']} {lp['name']} → 🪙 {int(lo * 0.8 * loot_mult):,} سکه")
    if random.random() < 0.65:
        drop = random.choice(b["loot"]["drops"])
        player.add_item(rows[0]["user_id"], drop, 1)
        from registry import item_name
        lines.append(f"🎁 قطره‌ی ویژه: {item_name(drop)} → {rows[0]['name']}")
    # 🧟 ثبت سقوط برای پنجره‌ی اسیرکردن (فقط آسیب‌برتر)
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)",
               (f"bosskill:{chat_id}",
                json.dumps(dict(boss_id=boss_id, tier=tier, top=rows[0]["user_id"],
                                at=db.now()))))
    lines.append("🧟 آسیب‌برتر تا ۱۰ دقیقه فرصت دارد باس را اسیر کند: «fw اینفکت»")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, boss_id))
    return "\n".join(lines)
