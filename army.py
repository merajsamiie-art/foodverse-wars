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


# 💰 قیمت فودکوین سربازها — خرید راحت با یک کلیک
UNIT_FC_PRICE = {
    "burger": 100, "fries": 150, "broccoli": 150, "meow": 400,
    "pizza": 400, "candy": 400, "cheese_knight": 1200, "lasagnazilla": 3000,
    "taco_ranger": 700, "cupcake_bomber": 750, "pickle_general": 850,
}


def unit_price(unit_id: str) -> int:
    return UNIT_FC_PRICE.get(unit_id, 500)


BULK_MAX = 100                      # سقف هر خرید گروهی (ضد اشتباه/دستکاری)
QTY_OPTIONS = (1, 10, 50, 0)        # ۰ = «حداکثر» (هرچه پول می‌رسد، تا سقف)

# 🎖 جوخه‌های آماده — ۱۰ سرباز با یک کلیک (ترکیب‌های سنجیده‌ی مثلث برتری)
SQUADS = {
    "balanced": dict(name="جوخه‌ی متعادل", emoji="⚖️",
                     desc="۴ برگر · ۳ سیب‌زمینی · ۳ بروکلی — همه‌فن‌حریف",
                     mix={"burger": 4, "fries": 3, "broccoli": 3}),
    "assault":  dict(name="جوخه‌ی تهاجمی", emoji="⚔️",
                     desc="۵ سیب‌زمینی · ۳ شیرینی · ۲ میو — ضربه‌ی اول، کریت بالا",
                     mix={"fries": 5, "candy": 3, "meow": 2}),
    "fortress": dict(name="جوخه‌ی دژ", emoji="🛡",
                     desc="۴ پیتزا · ۳ شوالیه پنیر · ۳ بروکلی — سپرِ زنده",
                     mix={"pizza": 4, "cheese_knight": 3, "broccoli": 3}),
    "elite":    dict(name="جوخه‌ی نخبه", emoji="🟣",
                     desc="۴ تاکوچی · ۳ کاپ‌کیک · ۳ ژنرال ترشی — سه قهرمان حماسی",
                     mix={"taco_ranger": 4, "cupcake_bomber": 3, "pickle_general": 3}),
}


def squad_price(sid: str) -> int:
    sq = SQUADS.get(sid)
    if not sq:
        return 0
    return sum(unit_price(u) * n for u, n in sq["mix"].items())


def max_affordable(user_id: int, unit_id: str) -> int:
    """چند تا از این سرباز با موجودی فعلی می‌شود خرید (تا سقف BULK_MAX)."""
    p = player.get(user_id)
    price = unit_price(unit_id)
    if price <= 0:
        return 0
    return max(0, min(BULK_MAX, int((p["fc"] or 0) // price)))


def _add_units(user_id: int, mix: dict):
    for unit_id, n in mix.items():
        if n <= 0:
            continue
        db.db().ex("INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?) "
                   "ON CONFLICT(user_id, unit_id) DO UPDATE SET count=count+?",
                   (user_id, unit_id, n, n))


def buy_fc(user_id: int, unit_id: str, count: int = 1) -> tuple:
    """🛒 خرید سرباز با فودکوین — تکی، ۱۰تایی، ۵۰تایی یا «حداکثر» (count=0)."""
    p = player.get(user_id)
    u = UNITS.get(unit_id)
    if not u or not u.get("cost"):
        return False, "🪖 چنین سربازی نیست."
    if count == 0:                                   # حداکثرِ ممکن
        count = max_affordable(user_id, unit_id)
        if count <= 0:
            return False, (f"🪙 حتی برای یک {u['name']} ({unit_price(unit_id):,} فودکوین) پول نداری.\n"
                           "💡 «شیر» رایگان هر ۱۰ دقیقه · «شیفت» هر ۳ ساعت")
    count = max(1, min(int(count), BULK_MAX))
    price = unit_price(unit_id) * count
    if (p["fc"] or 0) < price:
        can = max_affordable(user_id, unit_id)
        tip = f"💡 با موجودی فعلی تا <b>{can}</b> تا می‌توانی بخری." if can else "💡 «فودکوین» بگو و شیر رایگان بگیر!"
        return False, (f"🪙 {price:,} فودکوین لازم داری — الان {p['fc']:,.0f} داری.\n{tip}")
    with db.db().tx():
        player.pay(user_id, dict(fc=price))
        _add_units(user_id, {unit_id: count})
    player.dtrack(user_id, "recruits", count)
    perf.invalidate_player(user_id)
    pw = army_power(user_id)
    return True, (f"🛒 خرید شد: {u['emoji']} <b>{u['name']}</b> ×{count}\n"
                  f"🪙 {price:,} فودکوین پرداخت شد · قدرت ارتش الان <b>{perf.fmt(pw)}</b>\n"
                  f"{'🔥 خرید گروهی — ارتشت یک‌شبه بزرگ شد!' if count >= 10 else '⚔️ آماده‌ی جنگ!'}")


def buy_squad(user_id: int, sid: str) -> tuple:
    """🎖 خرید جوخه‌ی آماده — ۱۰ سرباز از چند شخصیت با یک کلیک."""
    sq = SQUADS.get(sid)
    if not sq:
        return False, "🎖 چنین جوخه‌ای نیست."
    p = player.get(user_id)
    price = squad_price(sid)
    if (p["fc"] or 0) < price:
        return False, (f"🪙 {sq['emoji']} {sq['name']} {price:,} فودکوین است — الان {p['fc']:,.0f} داری.\n"
                       "💡 جوخه‌ی متعادل ارزان‌ترین شروع است.")
    with db.db().tx():
        player.pay(user_id, dict(fc=price))
        _add_units(user_id, sq["mix"])
    n = sum(sq["mix"].values())
    player.dtrack(user_id, "recruits", n)
    perf.invalidate_player(user_id)
    parts = " · ".join(f"{UNITS[u]['emoji']}×{k}" for u, k in sq["mix"].items())
    return True, (f"🎖 {sq['emoji']} <b>{sq['name']}</b> به خدمت درآمد!\n"
                  f"{parts}\n🪙 {price:,} فودکوین · قدرت ارتش الان <b>{perf.fmt(army_power(user_id))}</b>")


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


CTYPE_FA = {"fastfood": ("🍔", "فست‌فود"), "candy": ("🍭", "شیرینی"), "veggie": ("🥦", "سبزیجات"),
            "meow": ("😺", "میو"), "weird": ("🦖", "عجیب"), "boss": ("👹", "باس")}


def bar(pct: float, width: int = 10) -> str:
    """نوار درصد — ▰▰▰▱▱ (برای ترکیب ارتش و جان باس)."""
    pct = max(0.0, min(1.0, float(pct)))
    fill = int(round(pct * width))
    return "▰" * fill + "▱" * (width - fill)


def composition(user_id: int) -> dict:
    """سهم هر نوع (fastfood/candy/veggie/…) از کل ارتش — برای مثلث برتری."""
    a = army_of(user_id)
    total = sum(a.values()) or 1
    out: dict[str, int] = {}
    for uid, n in a.items():
        ct = UNITS[uid]["ctype"]
        out[ct] = out.get(ct, 0) + n
    return {k: v / total for k, v in out.items()}


def army_text(user_id: int) -> str:
    from registry import RARITY
    a = army_of(user_id)
    if not a:
        return ("🪖 <b>ارتش</b> — خالی!\n\n"
                "🎖 سریع‌ترین شروع: دکمه‌ی «جوخه‌ی متعادل» = ۱۰ سرباز با یک کلیک\n"
                "🛒 یا «خرید ارتش» ← تعداد را ۱۰ بگذار و هر شخصیت را ده‌تا ده‌تا بخر.")
    s = army_stats(user_id)
    pw = army_power(user_id)
    lines = [f"🪖 <b>ارتش تو</b> — قدرت <b>{perf.fmt(pw)}</b> · {s['total']} سرباز",
             f"❤️ {perf.fmt(s['hp'])}  ⚔️ {perf.fmt(s['atk'])}  🛡 {perf.fmt(s['df'])}  "
             f"💨 {s['spd_avg']:.1f}  🎯 کریت {s['crit']*100:.0f}%", ""]
    for uid, n in sorted(a.items(), key=lambda x: -x[1]):
        u = UNITS[uid]
        dot = RARITY.get(u.get("rarity", "common"), ("⚪", ""))[0]
        lines.append(f"{dot} {u['emoji']} <b>{u['name']}</b> ×{n}")
    comp = composition(user_id)
    lines += ["", "📊 <b>ترکیب</b>"]
    for ct, pct in sorted(comp.items(), key=lambda x: -x[1]):
        em, fa = CTYPE_FA.get(ct, ("•", ct))
        lines.append(f"{em} {fa} {bar(pct, 8)} {pct*100:.0f}%")
    lines += ["", "⚖️ مثلث برتری: 🍔 فست‌فود ⟶ 🍭 شیرینی ⟶ 🥦 سبزیجات ⟶ 🍔 (تا ۳۰٪+)",
              "😺 میو و 🦖 عجیب خنثی‌اند — ارتشِ متنوع، حریفِ متنوع را می‌شکند."]
    return "\n".join(lines)
