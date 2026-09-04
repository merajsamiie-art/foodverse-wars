# 📦 Pack Engine — باز کردن پک: احتمال Server-Side + Pity + ضد دابل‌کلیک
import random

import db
import perf
import player
from config import PACK_OPEN_CD, PITY_PER_PACK, PITY_CAP
from registry import PACKS, LOOT_TABLES, COSMETICS, ITEMS, RARITY, DUPLICATE_VALUE


def give_pack(user_id: int, pack_id: str) -> bool:
    """هدیه‌ی پک به انبار (به‌صورت آیتم)."""
    if pack_id not in PACKS:
        return False
    player.add_item(user_id, f"pack_{pack_id}", 1)
    return True


def pack_text(user_id: int) -> str:
    p = player.get(user_id)
    inv = player.inv(user_id)
    packs_in_inv = {k[5:]: v for k, v in inv.items() if k.startswith("pack_")}
    lines = ["📦 <b>پک‌های تو</b> — شانس‌ها شفاف و سمت سرور محاسبه می‌شوند", ""]
    if packs_in_inv:
        for pid, n in packs_in_inv.items():
            pk = PACKS.get(pid)
            if pk:
                lines.append(f"{pk['emoji']} {pk['name']} ×{n}")
    else:
        lines.append("— هیچ پکی نداری. «روزانه» و باس‌ها پک رایگان می‌دهند.")
    pity_bonus = min(PITY_CAP, (p["pity"] or 0) * PITY_PER_PACK) * 100
    lines.append(f"\n🎁 <b>شانشِ جبران:</b> {p['pity'] or 0} پک بدون حماسی+ — شانس اضافه‌ی فعلی: {pity_bonus:.0f}٪")
    lines.append("📂 «بازکردن [نام پک]» | 🛒 پک‌های فروشگاه: «فروشگاه»")
    return "\n".join(lines)


def odds_text(pack_id: str) -> str:
    pk = PACKS.get(pack_id)
    if not pk:
        return "📦 پک نامعتبر."
    lines = [f"📊 <b>شانس‌های {pk['name']}</b>", ""]
    for rar, chance in pk["odds"].items():
        if chance > 0:
            lines.append(f"{RARITY[rar][0]} {RARITY[rar][1]}: {chance * 100:.1f}٪")
    g = pk["guaranteed"]
    gtxt = " ".join(f"🪙 {v} سکه" if k == "fc" else f"{v} {k}" for k, v in g.items())
    lines.append(f"\n🎁 تضمینی: {gtxt}")
    lines.append(f"🎲 قرعه: {pk['pulls']} کشش + شانسِ جبران")
    return "\n".join(lines)


def _weighted(table: list) -> str:
    total = sum(w for _, w in table)
    r = random.uniform(0, total)
    acc = 0
    for key, w in table:
        acc += w
        if r <= acc:
            return key
    return table[0][0]


def _roll_rarity(odds: dict, pity_bonus: float) -> str:
    """شانشِ جبران فقط شانسِ کمیاب→حماسی→افسانه‌ای را بالا می‌برد؛ اسطوره‌ای خاص می‌ماند."""
    o = dict(odds)
    if pity_bonus > 0:
        lift = min(pity_bonus, 0.30)
        o["epic"] = o.get("epic", 0) + lift * 0.6
        o["legendary"] = o.get("legendary", 0) + lift * 0.3
        o["mythic"] = o.get("mythic", 0) + lift * 0.05
        o["common"] = max(0.0, o.get("common", 0) - lift)
    r = random.random()
    acc = 0.0
    for rar in ("mythic", "legendary", "epic", "rare", "common"):
        acc += o.get(rar, 0)
        if r <= acc:
            return rar
    return "common"


def open_pack(user_id: int, pack_id: str) -> tuple:
    pk = PACKS.get(pack_id)
    if not pk:
        return False, "📦 پک نامعتبر. «پک»"
    p = player.get(user_id)
    if player.on_cd(user_id, "pack"):
        return False, f"⏳ {player.cd_left(user_id, 'pack')} ثانیه — ضد دابل‌کلیک."
    iid = f"pack_{pack_id}"
    if player.inv(user_id).get(iid, 0) < 1:
        return False, f"📦 {pk['name']} نداری. «پک»"
    with perf.key_lock(("pack", user_id)):
        if not player.take_item(user_id, iid, 1):   # دوباره‌چک اتمی
            return False, "📦 پک پیدا نشد."
        player.set_cd(user_id, "pack", PACK_OPEN_CD)
        p = player.get(user_id)
        pity = p["pity"] or 0
        pity_bonus = min(PITY_CAP, pity * PITY_PER_PACK)

        results = []
        got_epic_plus = False
        for _ in range(pk["pulls"]):
            rar = _roll_rarity(pk["odds"], pity_bonus)
            if rar in ("epic", "legendary", "mythic"):
                got_epic_plus = True
            key = _weighted(LOOT_TABLES[rar])
            results.append(_grant_loot(user_id, key, rar))

        # بخش تضمینی
        with db.db().tx():
            player.grant(user_id, **pk["guaranteed"])
            new_pity = 0 if got_epic_plus else pity + 1
            db.db().ex("UPDATE accounts SET pity=?, packs_opened=packs_opened+1 WHERE user_id=?",
                       (new_pity, user_id))
        # 🎬 نمایش سینمایی
        lines = [f"{pk['emoji']} <b>{pk['name']} باز شد!</b>", ""]
        gtxt = " ".join(f"🪙 {v} سکه" if k == "fc" else f"{v} {k}" for k, v in pk["guaranteed"].items())
        lines.append(f"🎁 تضمینی: {gtxt}")
        lines.append("")
        for rar, txt in results:
            lines.append(f"{RARITY[rar][0]} {txt}")
        if got_epic_plus:
            lines.append("\n✨ شانسِ جبران شما صفر شد.")
        elif pity > 0:
            lines.append(f"\n🎁 شانسِ جبران: {pity + 1} پک بدون حماسی+")
        return True, "\n".join(lines)


def _grant_loot(user_id: int, key: str, rar: str) -> tuple:
    """اعطای جایزه: کازمتیک یا آیتم؛ تکراری → سکه."""
    if key in COSMETICS:
        owned = db.db().one("SELECT 1 FROM cosmetics WHERE user_id=? AND cid=?", (user_id, key))
        if owned:
            val = DUPLICATE_VALUE.get(rar, 200)
            player.grant(user_id, fc=val)
            return rar, f"{COSMETICS[key]['name']} (داشتی!) → 🪙 {val} سکه"
        db.db().ex("INSERT OR IGNORE INTO cosmetics(user_id, cid) VALUES(?,?)", (user_id, key))
        c = COSMETICS[key]
        return rar, f"<b>{c['name']}</b>\n{c['en']}"
    it = ITEMS.get(key)
    if it:
        player.add_item(user_id, key, 1)
        return rar, f"<b>{it['name']}</b>\n{it['en'] if 'en' in it else it['desc']}"
    # fallback
    val = DUPLICATE_VALUE.get(rar, 200)
    player.grant(user_id, fc=val)
    return rar, f"🪙 {val} سکه"
