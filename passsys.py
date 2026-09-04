# 💎 Battle Pass Engine — مسیر رایگان + پرمیوم (بدون Pay-to-Win)
import json

import db
import perf
import player
import config
from config import PASS_TIERS, PASS_XP_PER_TIER
from registry import PACKS, COSMETICS, RES_META, PASSES


def _pass_status(user_id: int) -> dict:
    p = player.get(user_id)
    active = bool(p["pass_type"] and (p["pass_until"] or 0) > db.now())
    return dict(
        active=active, ptype=p["pass_type"] if active else "",
        until=p["pass_until"] if active else 0,
        xp=p["pass_xp"] or 0,
        tier=min(PASS_TIERS, int((p["pass_xp"] or 0) // PASS_XP_PER_TIER)),
        free=json.loads(p["pass_free"] or "[]"),
        prem=json.loads(p["pass_prem"] or "[]"),
    )


def activate(user_id: int, pass_type: str, days: int) -> tuple:
    """فعال‌سازی بعد از تأیید پرداخت — فقط یک‌بار با تراکنش."""
    p = player.get(user_id)
    base = max(db.now(), p["pass_until"] or 0)
    db.db().ex("""UPDATE accounts SET pass_type=?, pass_until=?, pass_prem='[]'
                  WHERE user_id=?""", (pass_type, base + days * 86400, user_id))
    return True, (f"💎 <b>{PASSES[pass_type]['name']}</b> فعال شد!\n"
                  f"⏳ تا {days} روز — مسیر پرمیوم باز است: «پاس»")


def pass_text(user_id: int) -> str:
    s = _pass_status(user_id)
    lines = ["💎 <b>BATTLE PASS</b>", ""]
    if s["active"]:
        import datetime
        end = datetime.datetime.fromtimestamp(s["until"], tz=config.TZ).strftime("%m-%d %H:%M")
        lines.append(f"🎖 {PASSES[s['ptype']]['name']} — فعال تا {end}")
    else:
        lines.append("🎖 پاس فعالی نداری (مسیر رایگان همیشه باز است!)")
    lines.append(f"⭐ تجربه‌ی پاس: {perf.fmt(s['xp'])} | پله: {s['tier']}/{PASS_TIERS} "
                 f"(هر پله {PASS_XP_PER_TIER} تجربه)")
    lines.append("")
    from registry import pass_reward_text
    for t in (1, 5, 10, 15, PASS_TIERS):
        free_txt, prem_txt = pass_reward_text(t)
        fmark = "✅" if t in s["free"] else ("🎁" if t <= s["tier"] else "🔒")
        pmark = "✅" if t in s["prem"] else ("👑" if t <= s["tier"] and s["active"] else "🔒")
        lines.append(f"پله {t}:")
        lines.append(f"  {fmark} 🆓 {free_txt}")
        lines.append(f"  {pmark} 💎 {prem_txt}")
    lines.append("\n🎁 «جایزه پاس [پله] [رایگان|پرمیوم]»")
    lines.append("🛒 خرید پاس: «خرید»")
    return "\n".join(lines)


def claim(user_id: int, tier: int, track: str) -> tuple:
    s = _pass_status(user_id)
    if tier < 1 or tier > PASS_TIERS:
        return False, f"💎 پله باید بین ۱ تا {PASS_TIERS} باشد."
    if tier > s["tier"]:
        need = tier * PASS_XP_PER_TIER
        return False, f"🔒 پله {tier} هنوز باز نشده (تجربه‌ی لازم: {need})."
    if track not in ("free", "prem"):
        return False, "💎 مسیر: رایگان یا پرمیوم"
    if track == "prem" and not s["active"]:
        return False, "💎 مسیر پرمیوم فقط با پاس فعال — «خرید»"
    claimed = s["free"] if track == "free" else s["prem"]
    if tier in claimed:
        return False, "✅ این پله را قبلاً گرفتی."
    from registry import PASS_REWARDS
    free, prem = PASS_REWARDS.get(tier, (dict(fc=200 * tier), dict(fc=400 * tier)))
    reward = free if track == "free" else prem
    # اعطا
    msgs = []
    for k, v in reward.items():
        if k == "fc":
            player.grant(user_id, fc=v)
            msgs.append(f"🪙 {v} فودکوین")
        elif k == "item":
            player.add_item(user_id, f"pack_{v}", 1)
            msgs.append(f"📦 پک {PACKS[v]['name']}")
        elif k == "cosmetic":
            db.db().ex("INSERT OR IGNORE INTO cosmetics(user_id, cid) VALUES(?,?)", (user_id, v))
            msgs.append(f"✨ {COSMETICS[v]['name']}")
        else:
            player.grant(user_id, **{k: v})
            msgs.append(f"{RES_META.get(k, {}).get('emoji', '')} {v}")
    claimed.append(tier)
    field = "pass_free" if track == "free" else "pass_prem"
    db.db().ex(f"UPDATE accounts SET {field}=? WHERE user_id=?", (json.dumps(claimed), user_id))
    return True, f"🎁 <b>جایزه‌ی پله {tier} ({'رایگان' if track == 'free' else 'پرمیوم'}):</b>\n" + " ".join(msgs)
