# 🛠 Craft Engine — اختراعات کارگاه
import db
import perf
import player
from config import CD_CRAFT, XP_CRAFT
from registry import RECIPES, ITEMS, item_name


def _workshop_lv(user_id: int) -> int:
    r = db.db().one("SELECT level FROM buildings WHERE user_id=? AND bld='workshop'", (user_id,))
    return r["level"] if r else 0


def craft_text(user_id: int) -> str:
    p = player.get(user_id)
    wl = _workshop_lv(user_id)
    lines = [f"🛠 <b>کارگاه</b> — سطح {wl} (ارتقا: «fw ارتقا کارگاه»)", ""]
    for rid, r in RECIPES.items():
        it = ITEMS[r["out"]]
        ok = p["level"] >= r["need_lv"] and wl >= r["workshop"]
        cost = " ".join(f"{k}:{v}" for k, v in r["cost"].items())
        lock = "✅" if ok else f"🔒 (لِوِل {r['need_lv']} + کارگاه {r['workshop']})"
        lines.append(f"{it['emoji']} <b>{it['name']}</b> {lock}\n   🧪 {it['desc']} | 💰 {cost}")
    lines.append("\n🏗 «fw ساخت [نام کالا]»")
    return "\n".join(lines)


def craft(user_id: int, ref: str) -> tuple:
    p = player.get(user_id)
    rid = None
    for k, r in RECIPES.items():
        if ref == k or ref == ITEMS[r["out"]]["name"]:
            rid = k
            break
    if not rid:
        return False, "🛠 چنین دستوری نیست. «fw ساخت»"
    r = RECIPES[rid]
    it = ITEMS[r["out"]]
    if p["level"] < r["need_lv"]:
        return False, f"🔒 سطح {r['need_lv']} لازم است (تو {p['level']}ی)."
    wl = _workshop_lv(user_id)
    if wl < r["workshop"]:
        return False, f"🔧 کارگاه سطح {r['workshop']} لازم است (تو {wl} داری)."
    if player.on_cd(user_id, "craft"):
        return False, f"⏳ {player.cd_left(user_id, 'craft')} ثانیه."
    if not player.can_pay(p, r["cost"]):
        need = " ".join(f"{k}:{v - (p[k] or 0):.0f}+" for k, v in r["cost"].items() if (p[k] or 0) < v)
        return False, f"🪙 کم داری: {need}"
    if player.inv_free(user_id) < 1:
        return False, "🎒 انبار پر است — اول چیزی بفروش یا مصرف کن."
    with db.db().tx():
        player.pay(user_id, r["cost"])
        player.add_item(user_id, r["out"], r["qty"])
    player.set_cd(user_id, "craft", CD_CRAFT)
    player.dtrack(user_id, "crafted")
    perf.invalidate_player(user_id)
    msgs = [f"🛠 <b>ساخته شد:</b> {item_name(r['out'])} ×{r['qty']}",
            f"🧪 {it['desc']}"]
    msgs += player.gain_xp(user_id, XP_CRAFT)
    if r["out"] == "lasagna_egg":
        msgs.append("🥚 چیزی داخل تخم تکان خورد...")
    return True, "\n".join(msgs)


def hatch(user_id: int) -> tuple:
    """تفریخ تخم لازاگنی‌زیلا — واحد اسطوره‌ای."""
    p = player.get(user_id)
    if not player.take_item(user_id, "lasagna_egg", 1):
        return False, "🥚 تخم لازاگنی‌زیلا نداری."
    if p["level"] < 20:
        player.add_item(user_id, "lasagna_egg", 1)
        return False, f"🔒 تفریخ از سطح ۲۰ (تو {p['level']}ی)."
    with db.db().tx():
        db.db().ex("INSERT INTO units(user_id, unit_id, count) VALUES(?, 'lasagnazilla', 1) "
                   "ON CONFLICT(user_id, unit_id) DO UPDATE SET count=count+1", (user_id,))
    perf.invalidate_player(user_id)
    return True, ("🦖 <b>لازاگنی‌زیلا از تخم بیرون آمد!</b>\n"
                  "زمین لرزید. کسی چیزی نگفت. 🌋")
