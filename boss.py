# 👑 Boss Engine — رید گروهی: آسیب ثبت، جایزه بر مشارکت + تیر + استخر دنیا + اینفکتد
import json
import random

import army
import db
import perf
import player
from config import (BOSS_CHECK_S, BOSS_DURATION, BOSS_TIER_HP,
                    BOSS_TIER_LOOT, BOSS_UNIT_LOSS, CD_BOSS, XP_BOSS_HIT)
from registry import BOSSES, ITEMS


TIER_BADGE = {1: "🥉 معمولی", 2: "🥈 شدید", 3: "🥇 کابوس"}

# 🧠 شخصیت باس‌ها — هر هوش، رفتار متفاوتی در نبرد دارد
AI_NAME = {"berserk": "🔴 خشمک", "tricky": "🎭 حیله‌گر", "swarm": "🌊 سیلاب",
           "healer": "💚 شفادهنده", "thief": "🤑 دزد", "shadow": "🌫️ سایه",
           "ultimate": "🩸 فوق‌هوشِ نهایی"}


def _next_boss_gap() -> int:
    """⏰ برنامه‌ی کاملاً رندوم: از ۱ روز تا ۱ ماه — هیچ‌کس نمی‌داند کی می‌آید."""
    return random.randint(24 * 3600, 30 * 24 * 3600)


def _schedule_next(chat_id: int) -> None:
    db.db().ex("UPDATE worlds SET boss_next=? WHERE chat_id=?",
               (db.now() + _next_boss_gap(), chat_id))


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
    stolen = w.get("boss_stolen") or 0
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0,
                  boss_until=0, boss_tier=1, boss_stolen=0 WHERE chat_id=?""", (chat_id,))
    _schedule_next(chat_id)
    if stolen > 0 and rows:   # 🦑 فودکوین‌های دزدیده‌شده به آسیب‌برترها برمی‌گردد
        for r in rows[:3]:
            back = int(stolen / (3 - rows.index(r)))
            player.grant(r["user_id"], fc=back)
    if not rows:
        return None
    lines = [f"💨 <b>{b['emoji']} {b['name']} فرار کرد!</b>",
             "ولی در عجله‌ی فرار، بخشی از غنیمتش روی زمین ماند:"]
    for r in rows:
        share = int((25 + r["dmg"] * 0.03) * (1 + BOSS_TIER_LOOT * (tier - 1)))
        if share > 0:
            player.grant(r["user_id"], fc=share)
            lines.append(f"🪙 {r['avatar']} {r['name']} — {share:,} فودکوین (آسیب {r['dmg']:,.0f})")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, bid))
    return "\n".join(lines)


def spawn_tick(chat_id: int, force: bool = False, tier: int | None = None) -> str | None:
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
        # ⏰ دروازه‌ی رندوم: ۱ روز تا ۱ ماه — هیچ‌کس نمی‌داند کی می‌آید
        nxt = ch["boss_next"] or 0
        if not nxt:
            db.db().ex("UPDATE worlds SET boss_next=? WHERE chat_id=?",
                       (t + random.randint(24 * 3600, 72 * 3600), chat_id))
            return None   # 🌱 اولین بار فقط برنامه‌گذاری — دنیای تازه هنوز آماده نیست
        if t < nxt:
            return None
    # 🎲 استخرِ باسِ این دنیا: باس‌های اسیرشده تا بازگشتشان غایب‌اند
    try:
        pool = json.loads(ch["boss_pool"]) if ch["boss_pool"] else []
    except Exception:
        pool = []
    if not pool:
        pool = list(BOSSES)
    pool = [x for x in pool if x != "grand_chef"]   # 🎩 رییس‌کل فقط با شرط ۵ کیل می‌آید
    revenge = (ch["revenge_bid"] or "") if (ch and not force) else ""
    revenge_uid = (ch["revenge_uid"] or 0) if ch else 0
    kills = (ch["boss_kills"] or 0) if (ch and not force) else 0
    if revenge and revenge in BOSSES and revenge in pool:
        # 🩸 نسخه‌ی انتقام — باسِ کشته‌شده بازمی‌گردد، از آسیب‌برترِ دیروز خشمگین
        bid = revenge
        db.db().ex("UPDATE worlds SET revenge_bid='', revenge_uid=0 WHERE chat_id=?", (chat_id,))
    elif kills >= 5 and not force:
        # 🎩 هر ۵ کشتار گروهی — رییس‌کل می‌آید
        bid = "grand_chef"
    else:
        bid = random.choice(pool)
    b = BOSSES[bid]
    is_revenge = bool(revenge) and bid == revenge and revenge_uid
    if tier is None:
        tier = 3 if force else _tier(chat_id)     # اسپاون اجباری ادمین = کابوس
    hp = round(b["hp"] * (1 + BOSS_TIER_HP * (tier - 1)))
    db.db().ex("""UPDATE worlds SET boss_id=?, boss_hp=?, boss_max_hp=?, boss_until=?,
                  boss_tier=? WHERE chat_id=?""",
               (bid, hp, hp, t + BOSS_DURATION, tier, chat_id))
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, bid))
    if bid == "grand_chef":
        head = ("🎩 <b>هشدار نهایی!</b>\n"
                f"🎩 <b>{b['name']}</b> از آشپزخانه‌ی مرکزی آمد — {TIER_BADGE.get(tier, '')}\n"
                "🩸 هوش: <b>فوق‌هوشِ نهایی</b> — همه‌ی هنرهای باس‌ها را یک‌جا دارد\n"
                "⚠️ او را نمی‌کُشی؛ فقط می‌توانی تأخیرش بیندازی. ولی غنیمتش افسانه‌ای است.\n")
    elif is_revenge:
        rv = player.get(revenge_uid)
        head = (f"🩸 <b>انتقام!</b>\n"
                f"{b['emoji']} <b>{b['name']}</b> بازگشت — خشمگین‌تر از همیشه!"
                + (f"\n🎯 دنبال {rv['avatar']} <b>{rv['name']}</b> است (آسیب‌برترِ دفعه‌ی قبل)" if rv else "")
                + "\n💪 جان و خشم بیشتر — جایزه هم بیشتر!\n")
    else:
        head = (f"🚨 <b>هشدار کارخانه!</b>\n"
                f"{b['emoji']} <b>{b['name']}</b> ظاهر شد — {TIER_BADGE.get(tier, '')}\n"
                f"🧠 هوش: <b>{AI_NAME.get(b.get('ai', ''), '❔')}</b>\n")
    return (head
            + f"❤️ {hp:,} | 📜 {b['lore']}\n"
            f"⏳ {BOSS_DURATION // 60} دقیقه — «باس» برای حمله‌ی گروهی\n"
            f"🧟 آسیب‌برتر می‌تواند بعد از سقوطش، آن را اسیر کند: «اینفکت»")


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
        ai = b.get("ai", "")
        ai_note = ""
        # 🌫️ سایه (نودل نینجا): جاخالیِ متغیر — گاهی ناپدید می‌شود
        dodge = b.get("dodge", 0)
        if ai == "shadow":
            dodge = min(0.6, dodge * random.uniform(0.4, 1.9))
        if random.random() < dodge:
            return True, (f"👑 {b['emoji']} {b['name']} جاخالی داد! حمله‌ات هدر رفت. 😼"
                          + ("\n🌫️ در بخار رامن محو شد..." if ai == "shadow" else ""))
        dmg = round(power * random.uniform(0.35, 0.55) * (1 + boost) * (1 - b.get("resist", 0)), 1)
        # 🩸 انتقام: باسِ خشمگین به شکارچیِ خودش ۱۵٪ آسیبِ بیشتر می‌زند
        if w.get("boss_id") == w.get("revenge_bid") and user_id == (w.get("revenge_uid") or 0):
            dmg *= 1.15
        # 🎩 رییس‌کل: هر ضربه حداکثر ۸٪ جانِ او را می‌برد — کشتنش عملاً ناممکن
        if b.get("ai") == "ultimate":
            dmg = min(dmg, w["boss_max_hp"] * 0.08)

        new_hp = round(w["boss_hp"] - dmg, 1)

        # 🧠 رفتار هوشمند باس — هر شخصیت واکنش خودش را دارد
        if new_hp > 0:
            if ai == "ultimate":                               # 🎩 همه‌ی هنرها یک‌جا
                if random.random() < 0.35:
                    heal = round(w["boss_max_hp"] * 0.04, 1)
                    new_hp = min(w["boss_max_hp"], new_hp + heal)
                    ai_note = f"\n🎩 آلبرت لبخند زد و {heal:,.0f} جان بازگشت..."
                elif random.random() < 0.25:
                    steal = min(p["fc"], 100 + p["level"] * 8)
                    if steal > 0:
                        player.grant(user_id, fc=-steal)
                        db.db().ex("UPDATE worlds SET boss_stolen=boss_stolen+? WHERE chat_id=?",
                                    (steal, chat_id))
                        ai_note = f"\n🎩 آلبرت {steal:,.0f} فودکوینت را روی میز کشید: «اجاره‌ی زمین»."
            elif ai == "healer" and random.random() < 0.25:      # 🥼 دوختن زخم با سس
                heal = round(w["boss_max_hp"] * 0.03, 1)
                new_hp = min(w["boss_max_hp"], new_hp + heal)
                ai_note = f"\n🥼 دکتر پپرونی زخمش را دوخت: +{heal:,.0f} جان!"
            elif ai == "thief" and random.random() < 0.30:     # 🦑 دزدی فودکوین
                steal = min(p["fc"], 40 + p["level"] * 5)
                if steal > 0:
                    player.grant(user_id, fc=-steal)
                    db.db().ex("UPDATE worlds SET boss_stolen=boss_stolen+? WHERE chat_id=?",
                                (steal, chat_id))
                    ai_note = f"\n🦑 بازوی کراکن {steal:,.0f} فودکوینت را قاپید! (با کشتنش برمی‌گردد)"
            elif ai == "tricky" and random.random() < 0.15:    # 😼 دابل ضدحمله
                ai_note = "\n😼 میو کینگ با هر دو پنجه ضدحمله زد!"
        if new_hp > 0:
            db.db().ex("UPDATE worlds SET boss_hp=? WHERE chat_id=?", (new_hp, chat_id))
        db.db().ex("""INSERT INTO boss_dmg(chat_id, boss_id, user_id, dmg) VALUES(?,?,?,?)
                      ON CONFLICT(chat_id, boss_id, user_id) DO UPDATE SET dmg=dmg+?""",
                   (chat_id, w["boss_id"], user_id, dmg, dmg))
        player.update(user_id, boss_dmg=p["boss_dmg"] + dmg)
        player.gain_xp(user_id, XP_BOSS_HIT)
        player.dtrack(user_id, "boss_hits")

        ai = b.get("ai", "")
        hp_frac = max(0, new_hp) / w["boss_max_hp"]
        loss_mult = random.uniform(0.5, 1.5)
        if ai == "swarm":
            loss_mult *= 1.5           # 🌊 سیلاب: تلفات بیشتر — ولی جایزه هم بیشتر
        if ai == "berserk" and hp_frac < 0.4:
            loss_mult *= 1.6           # 🔴 خشمک: پایین‌تر از ۴۰٪ = فوران
        lost = army.apply_losses(user_id, BOSS_UNIT_LOSS * loss_mult)
        rage = hp_frac < 0.3
        msg = (f"👑 <b>{b['emoji']} {b['name']}</b> — ❤️ {max(0, new_hp):,.0f}/{w['boss_max_hp']:,.0f}\n"
               f"⚔️ {p['avatar']} {p['name']}: <b>{dmg:,.0f}</b> آسیب"
               + (f" (🚀 بوستر ×{1 + boost:.1f})" if boost else "") + "\n"
               f"💢 ضدحمله‌ی باس! 💔 تلفات تو: {sum(lost.values())}"
               + ai_note
               + ("\n😡 <b>خشمِ دیوانه‌وار!</b> — باس برافروخته است!" if rage else ""))

        if b.get("ai") == "ultimate" and 0 < new_hp <= w["boss_max_hp"] * 0.15:
            msg += _grand_retreat(chat_id, w["boss_id"], user_id)
            return True, msg
        if new_hp <= 0:
            msg += _finish(chat_id, w["boss_id"], user_id)
        return True, msg


def _grand_retreat(chat_id: int, boss_id: str, last_uid: int) -> str:
    """🎩 رییس‌کل شکست نمی‌خورد — در ۱۵٪ جان، با لبخند عقب‌نشینی می‌کند و غنیمت می‌پاشد."""
    b = BOSSES[boss_id]
    w = db.db().one("SELECT boss_stolen, boss_tier FROM worlds WHERE chat_id=?", (chat_id,))
    tier = (w["boss_tier"] if w else 1) or 1
    stolen = (w["boss_stolen"] if w else 0) or 0
    loot_mult = (1 + BOSS_TIER_LOOT * (tier - 1)) * 1.5      # 🎩 غنیمت رییس‌کل: ۱.۵ برابر
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0,
                  boss_until=0, boss_tier=1, boss_stolen=0 WHERE chat_id=?""", (chat_id,))
    _schedule_next(chat_id)
    rows = db.db().q("""SELECT bd.user_id, bd.dmg, a.name, a.avatar FROM boss_dmg bd
                        JOIN accounts a ON a.user_id=bd.user_id
                        WHERE bd.chat_id=? AND bd.boss_id=? AND bd.dmg>0
                        ORDER BY bd.dmg DESC LIMIT 5""", (chat_id, boss_id))
    lines = ["\n🎩 <b>آلبرت عقب‌نشینی کرد!</b> — «بازی‌ی خوبی بود... برای شما.»",
             "🏆 او را نکشتید — ولی احترامش را گرفتید. غنیمت پاشید:"]
    total = max(1.0, sum(r["dmg"] for r in rows))
    for i, r in enumerate(rows):
        share = int(b["loot"]["fc"][1] * (r["dmg"] / total) * 2.5
                    * (1.5 if i == 0 else 1.0) * loot_mult)
        player.grant(r["user_id"], fc=share)
        tag = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉")
        lines.append(f"{tag} {r['avatar']} {r['name']} — 🪙 {share:,} فودکوین")
    if stolen > 0:
        player.grant(rows[0]["user_id"], fc=int(stolen))
        lines.append(f"🎩 {int(stolen):,} فودکوینِ «اجاره‌ی زمین» پس گرفته شد!")
    for r in rows[:2]:                                        # 🎩 قطره‌ی اسطوره
        player.add_item(r["user_id"], random.choice(b["loot"]["drops"]), 1)
    lines.append("🎩 «تا فصل بعد، آشپزخانه‌ی مرکزی برایت آرام نمی‌ماند...»")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, boss_id))
    return "\n".join(lines)


def _finish(chat_id: int, boss_id: str, last_uid: int) -> str:
    b = BOSSES[boss_id]
    w = db.db().one("SELECT boss_tier FROM worlds WHERE chat_id=?", (chat_id,))
    tier = (w["boss_tier"] if w else 1) or 1
    loot_mult = 1 + BOSS_TIER_LOOT * (tier - 1)
    wfull = db.db().one("SELECT * FROM worlds WHERE chat_id=?", (chat_id,))
    stolen = (wfull["boss_stolen"] if wfull else 0) or 0
    if boss_id == "lasagnazilla":
        loot_mult *= 1.25          # 🌊 سیلاب: جایزه‌ی بیشتر به‌خاطر تلفات بیشتر
    top0 = db.db().q("""SELECT bd.user_id FROM boss_dmg bd
                        WHERE bd.chat_id=? AND bd.boss_id=? AND bd.dmg>0
                        ORDER BY bd.dmg DESC LIMIT 1""", (chat_id, boss_id))
    db.db().ex("""UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_max_hp=0,
                  boss_until=0, boss_tier=1, boss_stolen=0,
                  boss_kills=boss_kills+1 WHERE chat_id=?""", (chat_id,))
    if top0 and random.random() < 0.30 and boss_id != "grand_chef":
        db.db().ex("UPDATE worlds SET revenge_bid=?, revenge_uid=? WHERE chat_id=?",
                   (boss_id, top0[0]["user_id"], chat_id))   # 🩸 باس بازمی‌گردد... برای انتقام
    _schedule_next(chat_id)
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
        lines.append(f"{tag} {r['avatar']} {r['name']} — آسیب {r['dmg']:,.0f} → 🪙 {share:,} فودکوین")
        seen.add(r["user_id"])
    if last_uid not in seen:
        lp = player.get(last_uid)
        if lp:
            player.grant(last_uid, fc=int(lo * 0.8 * loot_mult))
            lines.append(f"🎯 ضربه‌ی آخر: {lp['avatar']} {lp['name']} → 🪙 {int(lo * 0.8 * loot_mult):,} فودکوین")
    if stolen > 0:      # 🦑 فودکوین‌های قاپیده‌شده به آسیب‌برتر برمی‌گردند
        player.grant(rows[0]["user_id"], fc=int(stolen))
        lines.append(f"🦑 {int(stolen):,} فودکوینِ دزدیده‌شده پس گرفته شد! (سهم آسیب‌برتر)")
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
    lines.append("🧟 آسیب‌برتر تا ۱۰ دقیقه فرصت دارد باس را اسیر کند: «اینفکت»")
    db.db().ex("DELETE FROM boss_dmg WHERE chat_id=? AND boss_id=?", (chat_id, boss_id))
    return "\n".join(lines)
