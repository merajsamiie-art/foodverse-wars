# 🤝 Alliance Engine — اتحاد (دنیایی)، کمک، خیانت با ضد سوءاستفاده
import json

import db
import player
from config import (ALLY_CREATE_COST, ALLY_MAX, ALLY_HELP_CD, BETRAY_CD, BETRAY_STEAL_CAP)
from registry import RES_META


def my_alliance(user_id: int) -> dict:
    m = db.db().one("SELECT a.* FROM alliances a JOIN ally_members m ON m.alliance_id=a.id "
                    "WHERE m.user_id=?", (user_id,))
    return dict(m) if m else None


def create(user_id: int, chat_id: int, name: str) -> tuple:
    if not player.get(user_id):
        return False, "👤 اول «fw شروع» بزن."
    if my_alliance(user_id):
        return False, "🤝 قبلاً عضو اتحادی."
    name = (name or "").strip()[:24]
    if len(name) < 3:
        return False, "🤝 نام اتحاد حداقل ۳ نویسه."
    if db.db().one("SELECT 1 FROM alliances WHERE chat_id=? AND name=?", (chat_id, name)):
        return False, "🤝 این نام در این دنیا ثبت شده."
    if player.get(user_id)["fc"] < ALLY_CREATE_COST:
        return False, f"🪙 تأسیس اتحاد {ALLY_CREATE_COST:,} سکه می‌خواهد."
    with db.db().tx():
        player.pay(user_id, dict(fc=ALLY_CREATE_COST))
        db.db().ex("INSERT INTO alliances(chat_id, name, owner_uid, created_at) VALUES(?,?,?,?)",
                   (chat_id, name, user_id, db.now()))
        aid = db.db().one("SELECT id FROM alliances WHERE chat_id=? AND name=?",
                          (chat_id, name))["id"]
        db.db().ex("INSERT INTO ally_members(user_id, alliance_id, joined) VALUES(?,?,?)",
                   (user_id, aid, db.now()))
    return True, (f"🤝 <b>اتحاد «{name}»</b> تأسیس شد!\n"
                  f"عضویت: «fw عضویت {name}» | کمک: «fw کمک» | خروج: «fw ترک»")


def join(user_id: int, chat_id: int, name: str) -> tuple:
    if not player.get(user_id):
        return False, "👤 اول «fw شروع» بزن."
    if my_alliance(user_id):
        return False, "🤝 قبلاً عضو اتحادی — اول «fw ترک»."
    a = db.db().one("SELECT * FROM alliances WHERE chat_id=? AND name=?",
                    (chat_id, name.strip()))
    if not a:
        return False, "🤝 اتحادی با این نام در این دنیا نیست."
    n = db.db().one("SELECT COUNT(*) c FROM ally_members WHERE alliance_id=?", (a["id"],))["c"]
    if n >= ALLY_MAX:
        return False, f"🤝 ظرفیت اتحاد پر است ({n}/{ALLY_MAX})."
    db.db().ex("INSERT INTO ally_members(user_id, alliance_id, joined) VALUES(?,?,?)",
               (user_id, a["id"], db.now()))
    return True, f"🤝 به اتحاد «{a['name']}» پیوستی. با هم قوی‌تریم... تا وقتی که هستیم. 🗡"


def leave(user_id: int) -> tuple:
    m = db.db().one("SELECT * FROM ally_members WHERE user_id=?", (user_id,))
    if not m:
        return False, "🤝 عضو اتحادی نیستی."
    a = db.db().one("SELECT * FROM alliances WHERE id=?", (m["alliance_id"],))
    db.db().ex("DELETE FROM ally_members WHERE user_id=?", (user_id,))
    if a and a["owner_uid"] == user_id:
        nxt = db.db().one("SELECT user_id FROM ally_members WHERE alliance_id=? "
                          "ORDER BY joined LIMIT 1", (a["id"],))
        if nxt:
            db.db().ex("UPDATE alliances SET owner_uid=? WHERE id=?", (nxt["user_id"], a["id"]))
        else:
            db.db().ex("DELETE FROM alliances WHERE id=?", (a["id"],))
    return True, "🤝 اتحاد را ترک کردی. حالا تنهای خودت را هم باید نگه داری."


def help_(user_id: int, res: str, qty: int) -> tuple:
    a = my_alliance(user_id)
    if not a:
        return False, "🤝 عضو اتحادی نیستی."
    if res not in ("meat", "cheese", "sauce", "potato", "metal", "crystal", "fc"):
        return False, "🎒 منبع نامعتبر."
    p = player.get(user_id)
    qty = max(1, min(int(qty), int(p[res] or 0)))
    if qty < 1:
        return False, "🎒 از این منبع چیزی نداری."
    if player.on_cd(user_id, "help"):
        return False, f"⏳ {player.cd_left(user_id, 'help')} ثانیه."
    with db.db().tx():
        player.pay(user_id, {res: qty})
        if res == "fc":
            db.db().ex("UPDATE alliances SET treasury_fc=treasury_fc+? WHERE id=?", (qty, a["id"]))
        else:
            key = f"ally_res_{a['id']}"
            row = db.db().one("SELECT v FROM kv WHERE k=?", (key,))
            d = json.loads(row["v"]) if row else {}
            d[res] = d.get(res, 0) + qty
            db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)", (key, json.dumps(d)))
    player.set_cd(user_id, "help", ALLY_HELP_CD)
    return True, (f"🤝 {RES_META[res]['emoji']} ×{qty} به خزانه‌ی «{a['name']}» واریز شد.\n"
                  f"متحدان در جنگ دفاع می‌گیرند. وفاداری... ارزشمند است. 🗡")


def betray(user_id: int) -> tuple:
    """خیانت: سرقت محدود از خزانه + طرد + کول‌داون ۴۸ ساعته."""
    import random
    p = player.get(user_id)
    m = db.db().one("SELECT * FROM ally_members WHERE user_id=?", (user_id,))
    if not m:
        return False, "🗡 عضو اتحادی نیستی که خیانت کنی!"
    if (m["betrayed_at"] or 0) > db.now() - BETRAY_CD:
        left = int((m["betrayed_at"] + BETRAY_CD - db.now()) / 3600) + 1
        return False, f"🗡 هنوز نمی‌توانی دوباره خیانت کنی — {left} ساعت صبر کن."
    a = db.db().one("SELECT * FROM alliances WHERE id=?", (m["alliance_id"],))
    if not a:
        return False, "🗡 اتحاد منحل شده."
    with db.db().tx():
        fc_steal = max(0, min(round(a["treasury_fc"] * BETRAY_STEAL_CAP
                                    * random.uniform(0.7, 1.3), 1), a["treasury_fc"]))
        db.db().ex("UPDATE alliances SET treasury_fc=treasury_fc-? WHERE id=?", (fc_steal, a["id"]))
        db.db().ex("UPDATE ally_members SET betrayed_at=? WHERE user_id=?", (db.now(), user_id))
        player.grant(user_id, fc=fc_steal)
        db.db().ex("DELETE FROM ally_members WHERE user_id=?", (user_id,))
        db.db().ex("INSERT INTO txlog(chat_id, user_id, kind, detail, at) VALUES(?,?,?,?,?)",
                   (a["chat_id"], user_id, "betray", f"{a['name']} -{fc_steal}", db.now()))
    msg = (f"🗡 <b>خیانت!</b>\n"
           f"{p['avatar']} {p['name']} اتحاد «{a['name']}» را لو داد و 🪙 {fc_steal:,.0f} سکه برداشت!\n"
           f"🚫 ۴۸ ساعت نمی‌تواند دوباره خیانت کند — و هیچ‌کس فراموش نمی‌کند.")
    return True, msg


def status_text(user_id: int) -> str:
    a = my_alliance(user_id)
    if not a:
        return (f"🤝 <b>بی‌اتحاد</b>\n"
                f"تأسیس ({ALLY_CREATE_COST:,} سکه): «fw تأسیس [نام]» | عضویت: «fw عضویت [نام]»")
    members = db.db().q("""SELECT a.name, a.avatar, a.level FROM accounts a
                           JOIN ally_members m ON m.user_id=a.user_id
                           WHERE m.alliance_id=? ORDER BY a.level DESC""", (a["id"],))
    row = db.db().one("SELECT v FROM kv WHERE k=?", (f"ally_res_{a['id']}",))
    res = json.loads(row["v"]) if row else {}
    res_s = " ".join(f"{RES_META[k]['emoji']}{v}" for k, v in res.items()) or "—"
    ml = "\n".join(f"• {m_['avatar']} {m_['name']} (لِوِل {m_['level']})" for m_ in members)
    return (f"🤝 <b>اتحاد {a['name']}</b>\n"
            f"🏦 خزانه: 🪙 {a['treasury_fc']:,.0f} سکه | {res_s}\n"
            f"👥 اعضا ({len(members)}/{ALLY_MAX}):\n{ml}\n"
            f"🗡 «fw خیانت» — اگر جرئت داری.")
