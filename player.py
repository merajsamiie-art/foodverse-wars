# 👤 Player Engine — حساب جهانی، تولید، XP، روزانه، مرگ/محافظت
import datetime
import random

import config
import db
import perf
from config import (START_FC, START_RES, PROD_BASE, FACTORY_FC_H, LAB_CRYSTAL_H,
                    COLONY_RES_H, COLONY_FC_H, PROD_CAP_H, xp_need, XP_DAILY,
                    DAILY_FC, DAILY_STREAK_CAP, DAILY_REWARD_RES, AVATAR_REROLL,
                    DEAD_MINUTES, PROTECT_MINUTES, DEATH_DROP_PCT)
from registry import AVATARS, title_of

BASIC_RES = ("meat", "cheese", "sauce", "potato")


def now() -> float:
    return db.now()


# ─── ثبت/یافتن (جهانی) ───
def register(user_id: int, name: str, chat_id: int = None) -> dict:
    """ثبت حساب جهانی؛ اگر chat_id بدهد عضو آن دنیا هم می‌شود."""
    r = db.db().one("SELECT * FROM accounts WHERE user_id=?", (user_id,))
    if r:
        if chat_id:
            join_world(chat_id, user_id)
        return dict(r)
    t = now()
    db.db().ex("""INSERT OR IGNORE INTO accounts(
        user_id, name, avatar, fc, meat, cheese, sauce, potato, metal, crystal,
        created_at, last_active)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, name[:40], random.choice(AVATARS), START_FC,
         START_RES["meat"], START_RES["cheese"], START_RES["sauce"],
         START_RES["potato"], START_RES["metal"], START_RES["crystal"], t, t))
    if chat_id:
        join_world(chat_id, user_id)
    return get(user_id)


def get(user_id: int) -> dict:
    r = db.db().one("SELECT * FROM accounts WHERE user_id=?", (user_id,))
    if not r:
        return None
    d = dict(r)
    # 👑 پادشاه: منابع بی‌پایان — هرگز تمام نمی‌شود
    try:
        from config import KING_UID
        if user_id == KING_UID:
            cap = 999_999_999
            low = {k: cap for k in ("fc", "meat", "cheese", "sauce",
                                    "potato", "metal", "crystal") if d.get(k, 0) < 10_000_000}
            if low:
                db.db().ex(f"UPDATE accounts SET {', '.join(f'{k}=?' for k in low)} WHERE user_id=?",
                           (*low.values(), user_id))
                d.update(low)
    except Exception:
        pass
    return d


def update(user_id: int, **f):
    if not f:
        return
    cols = ", ".join(f"{k}=?" for k in f)
    db.db().ex(f"UPDATE accounts SET {cols} WHERE user_id=?", (*f.values(), user_id))


def join_world(chat_id: int, user_id: int):
    db.db().ex("""INSERT OR IGNORE INTO world_players(chat_id, user_id, joined, last_active)
                  VALUES(?,?,?,?)""", (chat_id, user_id, now(), now()))


def touch_world(chat_id: int, user_id: int):
    db.db().ex("UPDATE world_players SET last_active=? WHERE chat_id=? AND user_id=?",
               (now(), chat_id, user_id))


def today() -> str:
    """روزِ تقویمی به وقت تهران — ریست روزانه، مأموریت و فروشگاه همه با این."""
    return datetime.datetime.now(config.TZ).strftime("%Y-%m-%d")


# ─── تولید lazy (حساب جهانی) ───
def tick(user_id: int) -> None:
    p = get(user_id)
    if not p or p["banned"]:
        return
    dt = min(now() - (p["last_active"] or now()), PROD_CAP_H * 3600)
    if dt < 60:
        return
    h = dt / 3600
    bld = {r["bld"]: r["level"] for r in
           db.db().q("SELECT bld, level FROM buildings WHERE user_id=?", (user_id,))}
    colony_mult = 0 if (p["colony_pause"] or 0) > now() else p["colonies"]
    upd = {}
    for res in BASIC_RES:
        upd[res] = round(p[res] + (PROD_BASE[res] + colony_mult * COLONY_RES_H) * h, 1)
    upd["fc"] = round(p["fc"] + (bld.get("factory", 0) * FACTORY_FC_H
                                 + colony_mult * COLONY_FC_H) * h, 1)
    upd["crystal"] = round(p["crystal"] + bld.get("lab", 0) * LAB_CRYSTAL_H * h, 1)
    upd["last_active"] = now()
    # 🧟 کنترل اینفکتد: بخشی از تولید به کنترل‌کننده می‌رسد
    if (p["controlled_by"] or 0) and (p["controlled_until"] or 0) > now():
        tax = {}
        for k in ("fc",) + BASIC_RES:
            delta = upd[k] - p[k]
            t_amt = round(delta * config.INFECTED_CONTROL_TAX, 1)
            if t_amt > 0:
                upd[k] = round(upd[k] - t_amt, 1)
                tax[k] = t_amt
        if tax:
            update(user_id, **upd)
            grant(p["controlled_by"], **tax)
            update_control_log(user_id, sum(tax.values()))
            return
    update(user_id, **upd)


def update_control_log(user_id: int, amount: float):
    db.db().ex("INSERT INTO txlog(chat_id, user_id, kind, detail, at) VALUES(?,?,?,?,?)",
               (0, user_id, "control_tax", f"{amount:.1f}", now()))


# ─── XP / لِوِل ───
CD_FAUCET = 600          # ⏳ شیر فودکوین: هر ۱۰ دقیقه


def faucet(user_id: int) -> tuple:
    """🪙 شیر فودکوین — بگو «فودکوین» یا «FC»: مقدار بر اساس لول + کمی شانس (نه ناعادلانه)."""
    p = get(user_id)
    if not p:
        # 🛡 خودترمیم: هیچ‌وقت «پیدا نکردم» نمی‌گیری — همین‌جا ثبتت می‌کنیم
        try:
            register(user_id, f"بازیکن{user_id}", None)
            p = get(user_id)
        except Exception:
            pass
        if not p:
            return False, "🎮 در گروه بازی «شروع» را بفرست تا بازیکن شوی."
    if on_cd(user_id, "faucet"):
        return False, f"⏳ {cd_left(user_id, 'faucet')} ثانیه صبر — شیر هر ۱۰ دقیقه چکه می‌کند."
    set_cd(user_id, "faucet", CD_FAUCET)
    base = 12 + p["level"] * 2
    luck = random.uniform(0.6, 1.6)          # کمی شانس — باند شده، نه قمار
    roll = int(luck * 100)
    amt = max(5, round(base * luck))
    grant(user_id, fc=amt)
    dtrack(user_id, "faucets")
    return True, (f"🪙 <b>شیر فودکوین: +{amt:,}</b>\n"
                  f"🎲 شانس: ×{luck:.2f} (رول {roll} از ۱۰۰)\n"
                  f"📊 سطح {p['level']} → پایه {base:,} | دوباره تا ۱۰ دقیقه دیگر")


def gain_xp(user_id: int, amount: float) -> list:
    p = get(user_id)
    msgs = []
    if not p:
        return msgs
    # XP بازی = XP پاس هم
    update(user_id, xp=p["xp"] + amount, pass_xp=(p["pass_xp"] or 0) + amount)
    p = get(user_id)
    new_xp, lv = p["xp"], p["level"]
    while new_xp >= xp_need(lv) and lv < 99:
        new_xp -= xp_need(lv)
        lv += 1
        msgs.append(f"🎉 <b>سطح بالا → {lv}</b> — {title_of(lv)}")
    update(user_id, xp=new_xp, level=lv)
    return msgs


# ─── منابع ───
def can_pay(p: dict, cost: dict) -> bool:
    for k, v in (cost or {}).items():
        if (p[k] or 0) < v:
            return False
    return True


def pay(user_id: int, cost: dict):
    p = get(user_id)
    upd = {k: round(p[k] - v, 1) for k, v in (cost or {}).items()}
    update(user_id, **upd)


def grant(user_id: int, **res):
    p = get(user_id)
    upd = {k: round(p[k] + v, 1) for k, v in res.items()}
    update(user_id, **upd)


def res_line(p: dict) -> str:
    from registry import RES_META
    return " | ".join(f"{RES_META[r]['emoji']} {p[r]:.0f}"
                      for r in ("meat", "cheese", "sauce", "potato", "metal", "crystal"))


# ─── مرگ / احیا / محافظت ───
def is_dead(p: dict) -> bool:
    return bool(p and (p["dead_until"] or 0) > now())


def die(user_id: int, killer_name: str = "") -> dict:
    """💀 مرگ: ۵ دقیقه مرده + بخشی از منابع می‌افتد (تجهیزات محفوظ) + احیا با محافظت."""
    p = get(user_id)
    drop = {}
    for r in ("meat", "cheese", "sauce", "potato", "metal", "crystal"):
        amt = round(p[r] * DEATH_DROP_PCT * random.uniform(0.6, 1.0), 1)
        if amt >= 1:
            drop[r] = amt
    upd = {k: round(p[k] - v, 1) for k, v in drop.items()}
    upd.update(dead_until=now() + DEAD_MINUTES * 60, losses=p["losses"] + 1, boss_streak=0)
    update(user_id, **upd)
    return dict(ok=True, drop=drop, minutes=DEAD_MINUTES, killer=killer_name)


def revive_if_due(user_id: int) -> bool:
    """اگر وقتش گذشته: احیا + ۵ دقیقه محافظت."""
    p = get(user_id)
    if p and (p["dead_until"] or 0) and now() >= p["dead_until"]:
        update(user_id, dead_until=0, protect_until=now() + PROTECT_MINUTES * 60)
        return True
    return False


def is_protected(p: dict) -> bool:
    return bool(p and (p["protect_until"] or 0) > now())


def break_protection(user_id: int):
    """اگر محافظ‌شده حمله کند، محافظتش لغو می‌شود."""
    p = get(user_id)
    if p and (p["protect_until"] or 0) > now():
        update(user_id, protect_until=0)


# ─── روزانه ───
def daily(user_id: int) -> tuple:
    p = get(user_id)
    t = now()
    day = today()
    d = db.db().one("SELECT * FROM daily WHERE user_id=? AND day=?", (user_id, day))
    if not d:
        db.db().ex("INSERT OR IGNORE INTO daily(user_id, day) VALUES(?,?)", (user_id, day))
        d = db.db().one("SELECT * FROM daily WHERE user_id=? AND day=?", (user_id, day))
    lines = []
    if (p["last_daily"] or 0) < t - 20 * 3600:
        streak = p["daily_streak"] + 1 if (p["last_daily"] or 0) > t - 48 * 3600 else 1
        streak = min(streak, DAILY_STREAK_CAP)
        fc = DAILY_FC * streak
        grant(user_id, fc=fc, **{r: DAILY_REWARD_RES for r in BASIC_RES})
        update(user_id, last_daily=t, daily_streak=streak)
        gain_xp(user_id, XP_DAILY)
        lines.append(f"🎁 جایزه‌ی ورود (استریک {streak}×): 🪙 {fc} فودکوین + بسته‌ی منابع")
    missions = [
        ("war_wins", 1, "یک نبرد ببر"),
        ("recruits", 5, "۵ سرباز جذب کن"),
        ("crafted", 1, "یک ساخته‌ی کارگاهی"),
        ("boss_hits", 2, "۲ بار به باس بزن"),
        ("sold", 1, "یک بار به صرافی بفروش"),
        ("bought", 1, "یک بار از صرافی خرید کن"),
    ]
    done = all((d[k] or 0) >= g for k, g, _ in missions)
    if done and not d["claimed"]:
        from config import DAILY_PACK_CHANCE
        reward = 400
        grant(user_id, fc=reward, crystal=3)
        extra = ""
        if random.random() < DAILY_PACK_CHANCE:
            from registry import PACKS
            import packs as packs_mod
            packs_mod.give_pack(user_id, "free_pack")
            extra = f" + 📦 {PACKS['free_pack']['name']}"
        db.db().ex("UPDATE daily SET claimed=1 WHERE user_id=? AND day=?", (user_id, day))
        gain_xp(user_id, 50)
        lines.append(f"📅 <b>مأموریت روزانه کامل!</b> 🪙 +{reward} فودکوین + 💎 ۳ کریستال{extra}")
    elif d["claimed"]:
        lines.append("📅 مأموریت امروز: ✅ تمام شد.")
    else:
        items = [f"• {desc} — {'✅' if (d[k] or 0) >= g else f'{d[k] or 0}/{g}'}"
                 for k, g, desc in missions]
        lines.append("📅 مأموریت روزانه:\n" + "\n".join(items))
    return True, "\n".join(lines) if lines else "🏭 امروز همه‌چیز گرفته‌ای. برو بجنگ!"


def dtrack(user_id: int, field: str, n: int = 1):
    db.db().ex(f"UPDATE daily SET {field} = COALESCE({field},0)+? WHERE user_id=? AND day=?",
               (n, user_id, today()))


# ─── آواتار ───
def reroll_avatar(user_id: int) -> tuple:
    p = get(user_id)
    if p["fc"] < AVATAR_REROLL:
        return False, f"🪙 تغییر چهره {AVATAR_REROLL} فودکوین می‌خواهد."
    new = random.choice([a for a in AVATARS if a != p["avatar"]])
    update(user_id, fc=p["fc"] - AVATAR_REROLL, avatar=new)
    return True, f"🎭 چهره‌ی جدید: {new}"


# ─── کول‌داون (حافظه‌ای ⚡) ───
def on_cd(user_id: int, kind: str) -> bool:
    return perf.cd_on((user_id, kind))


def cd_left(user_id: int, kind: str) -> int:
    return perf.cd_left((user_id, kind))


def set_cd(user_id: int, kind: str, secs: int):
    perf.cd_set((user_id, kind), secs)


# ─── انبار ───
def inv(user_id: int) -> dict:
    return {r["item_id"]: r["qty"] for r in
            db.db().q("SELECT item_id, qty FROM items WHERE user_id=? AND qty>0", (user_id,))}


def add_item(user_id: int, iid: str, qty: int = 1):
    db.db().ex("INSERT INTO items(user_id, item_id, qty) VALUES(?,?,?) "
               "ON CONFLICT(user_id, item_id) DO UPDATE SET qty=qty+?", (user_id, iid, qty, qty))


def take_item(user_id: int, iid: str, qty: int = 1) -> bool:
    r = db.db().one("SELECT qty FROM items WHERE user_id=? AND item_id=?", (user_id, iid))
    if not r or r["qty"] < qty:
        return False
    db.db().ex("UPDATE items SET qty=qty-? WHERE user_id=? AND item_id=?", (qty, user_id, iid))
    return True


def inv_free(user_id: int) -> int:
    from config import inv_slots
    p = get(user_id)
    return inv_slots(p["level"]) - len(inv(user_id))


# ─── قدرت ───
def power_score(p: dict) -> float:
    import army
    a = army.army_power(p["user_id"])
    bld_sum = sum(r["level"] for r in
                  db.db().q("SELECT level FROM buildings WHERE user_id=?", (p["user_id"],)))
    return round(a + p["level"] * 50 + bld_sum * 30 + p["colonies"] * 100, 1)


# ═══ کمکیار — قدم‌به‌قدم، بی‌اسپم ═══
def guide_step(user_id: int) -> int:
    p = get(user_id)
    return p["guide_step"] if p and p["guide_step"] else 0


def advance_guide(user_id: int, event: str) -> str:
    """اگر بازیکن همین قدم را انجام داد → قدم بعدی + متنِ قدم بعدی."""
    from texts import GUIDE_STEPS
    step = guide_step(user_id)
    if step >= len(GUIDE_STEPS) or GUIDE_STEPS[step]["ev"] != event:
        return ""
    db.db().ex("UPDATE accounts SET guide_step=? WHERE user_id=?", (step + 1, user_id))
    nxt = GUIDE_STEPS[step + 1] if step + 1 < len(GUIDE_STEPS) else None
    return "\n\n" + nxt["tip"] if nxt else "\n\n🎓 کمکیار تمام شد — از این بعد خودت قهرمانی!"
