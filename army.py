# 🪖 Army Engine — جذب، قدرت، تلفات (کش‌شده ⚡)
import db
import perf
import player
from config import CD_RECRUIT
from registry import UNITS


def army_of(user_id: int) -> dict:
    return {r["unit_id"]: r["count"] for r in
            db.db().q("SELECT unit_id, count FROM units WHERE user_id=? AND count>0", (user_id,))}


def army_size(user_id: int) -> int:
    return sum(army_of(user_id).values())


def army_stats(user_id: int) -> dict:
    cached = perf.BONUS_CACHE.get(("stats", user_id))
    if cached is not None:
        return cached
    a = army_of(user_id)
    s = dict(hp=0, atk=0, df=0, spd=0, total=0, medic=0, scout=0)
    for uid, n in a.items():
        u = UNITS[uid]
        s["hp"] += u["hp"] * n
        s["atk"] += u["atk"] * n
        s["df"] += u["df"] * n
        s["spd"] += u["spd"] * n
        s["total"] += n
        if u.get("heal"):
            s["medic"] += n
        if u.get("crit"):
            s["scout"] += n
    if s["total"]:
        s["spd_avg"] = s["spd"] / s["total"]
        s["crit"] = min(0.35, 0.05 + s["scout"] / max(1, s["total"]) * 0.15)
    else:
        s["spd_avg"] = 0
        s["crit"] = 0
    perf.BONUS_CACHE.set(("stats", user_id), s)
    return s


def blds_cached(user_id: int) -> dict:
    c = perf.BLD_CACHE.get(user_id)
    if c is not None:
        return c
    b = {r["bld"]: r["level"] for r in
         db.db().q("SELECT bld, level FROM buildings WHERE user_id=?", (user_id,))}
    perf.BLD_CACHE.set(user_id, b)
    return b


def _training_bonus(user_id: int) -> float:
    return 0.08 * blds_cached(user_id).get("training", 0)


def _equip_bonus(user_id: int) -> dict:
    b = dict(atk=0.0, df=0.0, spc=0.0)
    for r in db.db().q("SELECT item_id, equipped FROM items WHERE user_id=? AND equipped=1", (user_id,)):
        from registry import ITEMS
        it = ITEMS.get(r["item_id"])
        if it and it["kind"] == "equip":
            if it["slot"] == "atk":
                b["atk"] += it["val"]
            elif it["slot"] == "def":
                b["df"] += it["val"]
            else:
                b["spc"] += it["val"]
    return b


def army_power(user_id: int) -> float:
    c = perf.POWER_CACHE.get(user_id)
    if c is not None:
        return c
    s = army_stats(user_id)
    if not s["total"]:
        perf.POWER_CACHE.set(user_id, 0.0)
        return 0.0
    eq = _equip_bonus(user_id)
    tr = _training_bonus(user_id)
    import infected
    inf = infected.power_bonus(user_id)
    raw = (s["atk"] * 2 + s["df"] * 1.5 + s["hp"] * 0.3 + s["spd_avg"] * 20) * (1 + tr + eq["spc"] + inf)
    val = round(raw * (1 + eq["atk"]), 1)
    perf.POWER_CACHE.set(user_id, val)
    return val


def recruit(user_id: int, unit_id: str, count: int) -> tuple:
    p = player.get(user_id)
    u = UNITS.get(unit_id)
    if not u or not u.get("cost"):
        return False, "🪖 چنین واحدی برای جذب نیست."
    count = max(1, min(count, 50))
    if player.on_cd(user_id, "recruit"):
        return False, f"⏳ سربازخانه مشغول است — {player.cd_left(user_id, 'recruit')} ثانیه."
    cost = {k: v * count for k, v in u["cost"].items()}
    if not player.can_pay(p, cost):
        need = " ".join(f"{k}:{v - (p[k] or 0):.0f}+" for k, v in cost.items() if (p[k] or 0) < v)
        return False, f"🪙 منابع کافی نیست — کم داری: {need}"
    with db.db().tx():
        player.pay(user_id, cost)
        db.db().ex("INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?) "
                   "ON CONFLICT(user_id, unit_id) DO UPDATE SET count=count+?",
                   (user_id, unit_id, count, count))
    player.set_cd(user_id, "recruit", CD_RECRUIT)
    player.dtrack(user_id, "recruits", count)
    perf.invalidate_player(user_id)
    return True, (f"🪖 {u['emoji']} <b>{u['name']}</b> ×{count} به ارتش پیوست.\n"
                  f"({player.res_line(player.get(user_id))})")


def apply_losses(user_id: int, pct: float) -> dict:
    lost = {}
    for uid, n in army_of(user_id).items():
        drop = int(n * pct)
        if drop > 0:
            db.db().ex("UPDATE units SET count=count-? WHERE user_id=? AND unit_id=?",
                       (drop, user_id, uid))
            lost[uid] = drop
    if lost:
        perf.invalidate_player(user_id)
    return lost


def army_text(user_id: int) -> str:
    a = army_of(user_id)
    if not a:
        return "🪖 ارتش: هنوز هیچی. «جذب برگر ۵»"
    lines = []
    for uid, n in sorted(a.items(), key=lambda x: -x[1]):
        u = UNITS[uid]
        lines.append(f"{u['emoji']} {u['name']} ×{n}")
    return (f"🪖 <b>ارتش</b> — قدرت {perf.fmt(army_power(user_id))}\n" +
            "\n".join(lines))
