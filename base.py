# 🏠 Base Engine — ساختمان‌ها، ارتقا، مستعمره‌ها
import db
import perf
import player
from config import (COLONY_NEED_LEVEL, COLONY_COST, COLONY_MAX,
                    COLONY_RAID_CD, COLONY_PAUSE_S, CD_BUILD)
from registry import BUILDINGS

import army
import random


def blds(user_id: int) -> dict:
    return army.blds_cached(user_id)


def _up_cost(bld: str, cur_lv: int) -> dict:
    """هزینه‌ی سطح بعد: پایه × (سطح+۱)^1.35"""
    base = BUILDINGS[bld]["cost0"]
    mult = (cur_lv + 1) ** 1.35
    return {k: int(v * mult) for k, v in base.items()}


def upgrade(user_id: int, bld: str) -> tuple:
    p = player.get(user_id)
    b = BUILDINGS.get(bld)
    if not b:
        return False, "🏠 ساختمان‌ها: " + " | ".join(f"{v['emoji']} {v['name']}" for v in BUILDINGS.values())
    if player.on_cd(user_id, "build"):
        return False, f"⏳ کارگران استراحت می‌کنند — {player.cd_left(user_id, 'build')} ثانیه."
    cur = blds(user_id).get(bld, 0)
    if cur >= b["maxlv"]:
        return False, f"🏠 {b['name']} در بیشینه‌ی سطح است ({cur})."
    cost = _up_cost(bld, cur)
    if not player.can_pay(p, cost):
        from registry import res_name
        need = " ".join(f"{res_name(k)} {v - (p[k] or 0):.0f}+" for k, v in cost.items() if (p[k] or 0) < v)
        return False, f"🪙 منابع کافی نیست: کم داری {need}"
    with db.db().tx():
        player.pay(user_id, cost)
        db.db().ex("INSERT INTO buildings(user_id, bld, level) VALUES(?,?,1) "
                   "ON CONFLICT(user_id, bld) DO UPDATE SET level=level+1", (user_id, bld))
    player.set_cd(user_id, "build", CD_BUILD)
    perf.invalidate_player(user_id)
    return True, (f"{b['emoji']} <b>{b['name']}</b> → سطح {cur + 1}\n🏗 {b['desc']}")


def build_colony(user_id: int) -> tuple:
    p = player.get(user_id)
    if p["level"] < COLONY_NEED_LEVEL:
        return False, f"🏝️ مستعمره از سطح {COLONY_NEED_LEVEL} باز می‌شود (تو {p['level']}ی)."
    if p["colonies"] >= COLONY_MAX:
        return False, f"🏝️ سقف مستعمره‌هایت پر است ({COLONY_MAX})."
    if player.on_cd(user_id, "build"):
        return False, f"⏳ {player.cd_left(user_id, 'build')} ثانیه."
    if not player.can_pay(p, COLONY_COST):
        return False, "🪙 مستعمره: ۸۰۰ فودکوین + ۲۵۰ گوشت + ۱۵۰ فلز."
    with db.db().tx():
        player.pay(user_id, COLONY_COST)
        player.update(user_id, colonies=p["colonies"] + 1)
    player.set_cd(user_id, "build", CD_BUILD)
    perf.invalidate_player(user_id)
    return True, ("🏝️ <b>مستعمره‌ی جدید تأسیس شد!</b>\n"
                  "تولید: هر منبع پایه +۲۰/ساعت و 🪙 +۵۰/ساعت — اما مراقب غارت باش.")


def raid_colony(attacker_uid: int, defender_uid: int) -> tuple:
    d = player.get(defender_uid)
    if attacker_uid == defender_uid:
        return False, "🏝️ خودغارت؟ خلاقانه ولی نه."
    if d["colonies"] < 1:
        return False, "🏝️ این بازیکن مستعمره‌ای ندارد."
    if player.on_cd(attacker_uid, "raid"):
        return False, f"⏳ دوباره‌غارت — {player.cd_left(attacker_uid, 'raid')} ثانیه."
    if army.army_size(attacker_uid) < 5:
        return False, "🪖 برای غارت حداقل ۵ سرباز لازم است."
    dfn = blds(defender_uid).get("defense", 0)
    steal_pct = max(0.08, 0.22 - dfn * 0.015)
    stolen = {}
    for r in ("meat", "cheese", "sauce", "potato"):
        amt = round(d[r] * steal_pct * random.uniform(0.7, 1.2), 1)
        if amt > 1:
            stolen[r] = amt
    with db.db().tx():
        player.update(defender_uid,
                      colony_pause=player.now() + COLONY_PAUSE_S,
                      **{k: round(d[k] - v, 1) for k, v in stolen.items()})
        player.grant(attacker_uid, **stolen)
    player.set_cd(attacker_uid, "raid", COLONY_RAID_CD)
    lost = army.apply_losses(attacker_uid, 0.04)
    from registry import res_name
    st = " ".join(res_name(k) + f" {v:.0f}" for k, v in stolen.items()) or "هیچی!"
    return True, (f"🏝️ <b>غارت مستعمره‌ی {d['avatar']} {d['name']}</b>\n"
                  f"🎒 بردی: {st}\n"
                  f"⏸ تولید مستعمره‌ی او ۱ ساعت متوقف شد.\n"
                  f"💔 تلفات خودت: {sum(lost.values())} سرباز")


def base_text(user_id: int) -> str:
    p = player.get(user_id)
    b = blds(user_id)
    lines = [f"🏠 <b>پایگاه {p['avatar']} {p['name']}</b> — سطح {p['level']}", ""]
    for bid, meta in BUILDINGS.items():
        lv = b.get(bid, 0)
        nxt = _up_cost(bid, lv) if lv < meta["maxlv"] else None
        cost_s = " ".join(f"{k}:{v}" for k, v in nxt.items()) if nxt else "MAX"
        lines.append(f"{meta['emoji']} {meta['name']}: {'▮' * lv}{'▯' * (meta['maxlv'] - lv)} {lv} → {cost_s}")
    lines.append(f"\n🏝️ مستعمره‌ها: {p['colonies']}/{COLONY_MAX}" +
                 ("\n⏸ (تولید مستعمره موقتاً متوقف است)" if (p["colony_pause"] or 0) > player.now() else ""))
    lines.append("🏗 «ارتقا [کارخانه]» | «مستعمره» | «غارت [ریپلای]»")
    return "\n".join(lines)
