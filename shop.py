# 🛒 Shop Engine — فروشگاه چرخشی: روزانه/هفتگی + خرید فودکوین
import datetime
import json
import random

import db
import perf
import player
import config
from config import CD_MARKET, SHOP_DAILY_SIZE, SHOP_WEEKLY_SIZE
from registry import SHOP_POOL, PACKS


def _day() -> str:
    return datetime.datetime.now(config.TZ).strftime("%Y-%m-%d")


def _week() -> str:
    return datetime.datetime.now(config.TZ).strftime("%G-W%V")


def _rotated(key: str, size: int, salt: str) -> list:
    """چرخش قطعی (seeded) — همه در یک روز یک فروشگاه می‌بینند."""
    row = db.db().one("SELECT v FROM kv WHERE k=?", (key,))
    if row:
        return json.loads(row["v"])
    pool = list(SHOP_POOL)
    rng = random.Random(f"{salt}-{key}")
    pick = rng.sample(pool, min(size, len(pool)))
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)", (key, json.dumps(pick)))
    return pick


def daily_slots() -> list:
    return _rotated(f"shop_daily_{_day()}", SHOP_DAILY_SIZE, "daily")


def weekly_slots() -> list:
    return _rotated(f"shop_weekly_{_week()}", SHOP_WEEKLY_SIZE, "weekly")


def _user_bought(user_id: int, slot: str) -> int:
    r = db.db().one("SELECT qty FROM shop_buys WHERE user_id=? AND day=? AND slot=?",
                    (user_id, _day(), slot))
    return r["qty"] if r else 0


def shop_text(user_id: int) -> str:
    p = player.get(user_id)
    d, w = daily_slots(), weekly_slots()
    lines = [f"🛒 <b>فروشگاه کارخانه</b> — 🪙 {perf.fmt(p['fc'])} فودکوین", ""]
    lines.append("🕐 <b>امروز</b> (فردا عوض می‌شود):")
    for slot in d:
        lines.append(_slot_line(user_id, slot))
    lines.append("\n📅 <b>این هفته</b>:")
    for slot in w:
        lines.append(_slot_line(user_id, slot))
    lines.append("\n📦 <b>پک‌ها</b> (همیشه موجود، خرید با فودکوین):")
    for pid, pk in PACKS.items():
        if pk.get("fc_price"):
            lines.append(f"• {pk['emoji']} {pk['name']} — 🪙 {pk['fc_price']:,} فودکوین")
    lines.append("\n🛒 «خریدن [نام کالا یا پک]» | فودکوین و پاس با پول: «خرید»")
    return "\n".join(lines)


def _buy_pack_fc(user_id: int, pid: str) -> tuple:
    """پک با فودکوین — سهمیه‌ی روزانه مثل بقیه‌ی فروشگاه."""
    pk = PACKS[pid]
    p = player.get(user_id)
    if _user_bought(user_id, f"pack_{pid}") >= 2:
        return False, "🛒 امروز ۲ تا از این پک گرفتی — فردا دوباره."
    if player.on_cd(user_id, "market"):
        return False, f"⏳ {player.cd_left(user_id, 'market')} ثانیه."
    if p["fc"] < pk["fc_price"]:
        return False, f"🪙 {pk['fc_price']:,} فودکوین لازم است — الان {int(p['fc']):,} داری."
    with perf.key_lock(("shopbuy", user_id)):
        with db.db().tx():
            player.pay(user_id, dict(fc=pk["fc_price"]))
            player.add_item(user_id, f"pack_{pid}", 1)
            _mark_bought(user_id, f"pack_{pid}")
        player.set_cd(user_id, "market", CD_MARKET)
    return True, f"🛒 {pk['emoji']} {pk['name']} خریدی — «بازکردن {pk['name']}»"


def _mark_bought(user_id: int, slot: str):
    db.db().ex("""INSERT INTO shop_buys(user_id, day, slot, qty) VALUES(?,?,?,1)
                  ON CONFLICT(user_id, day, slot) DO UPDATE SET qty=qty+1""",
               (user_id, _day(), slot))


def _slot_line(user_id: int, slot: str) -> str:
    m = SHOP_POOL[slot]
    bought = _user_bought(user_id, slot)
    limit_txt = f" ({bought}/{m['limit']})" if m["limit"] else ""
    name = m.get("pack") and PACKS.get(slot, {}).get("name") or _slot_name(slot)
    return f"• {name} — 🪙 {m['fc']} فودکوین{limit_txt}"


def _slot_name(slot: str) -> str:
    if slot in PACKS:
        return f"{PACKS[slot]['emoji']} پک {PACKS[slot]['name']}"
    from registry import ITEMS
    if slot in ITEMS:
        return ITEMS[slot]["name"]
    names = dict(herb_pack="🥩 بسته‌ی گوشت و پنیر", res_crate="📦 جعبه‌ی منابع")
    return names.get(slot, slot)


def buy(user_id: int, slot_ref: str) -> tuple:
    import fuzzy as fz
    # ۱) پک‌ها: همیشه موجود، خرید با فودکوین (شناسه‌ی مستقیم یا نام فارسی)
    pcat = {k: v["name"] for k, v in PACKS.items() if v.get("fc_price")}
    pid = slot_ref if slot_ref in pcat else fz.resolve(slot_ref, pcat)
    if pid:
        return _buy_pack_fc(user_id, pid)
    # ۲) اسلات‌های چرخشی
    slot = None
    for s in set(daily_slots() + weekly_slots()):
        if slot_ref == s or slot_ref in _slot_name(s) or (s in PACKS and slot_ref in PACKS[s]["name"]):
            slot = s
            break
    if not slot:
        return False, ("🛒 این کالا الان در فروشگاه نیست. «فروشگاه»\n"
                       "📦 پک‌ها همیشه هستند: «خریدن پک تازه‌کار»")
    m = SHOP_POOL[slot]
    p = player.get(user_id)
    if _user_bought(user_id, slot) >= m["limit"]:
        return False, "🛒 سهمیه‌ی امروزت از این کالا پر شده — فردا."
    if player.on_cd(user_id, "market"):
        return False, f"⏳ {player.cd_left(user_id, 'market')} ثانیه."
    if p["fc"] < m["fc"]:
        return False, f"🪙 {m['fc']} فودکوین لازم است."
    with perf.key_lock(("shopbuy", user_id)):
        with db.db().tx():
            player.pay(user_id, dict(fc=m["fc"]))
            if m.get("pack"):
                player.add_item(user_id, f"pack_{slot}", 1)
            elif m.get("grant"):
                player.grant(user_id, **m["grant"])
            else:
                player.add_item(user_id, slot, 1)
            db.db().ex("""INSERT INTO shop_buys(user_id, day, slot, qty) VALUES(?,?,?,1)
                          ON CONFLICT(user_id, day, slot) DO UPDATE SET qty=qty+1""",
                       (user_id, _day(), slot))
        player.set_cd(user_id, "market", CD_MARKET)
        db.db().ex("INSERT INTO txlog(chat_id, user_id, kind, detail, at) VALUES(NULL,?,?,?,?)",
                   (user_id, "shop_buy", f"{slot}", db.now()))
        return True, f"🛒 خریدی: {_slot_name(slot)} (−{m['fc']} فودکوین)"


def rotate_if_needed():
    """اسکجولر: کلیدهای روز/هفته چرخیده‌اند — kv خودش با کلید تاریخ جدید می‌سازد."""
    perf.LB_CACHE.drop(("shop",))
    return None
