# 🔄 Trade Engine — مبادله‌ی دوطرفه با اسکرو؛ ضداسکمِ واقعی
# قواعد امنیتی:
#   ۱) هر چیز هنگام «گذاشتن» همان لحظه از حساب برداشته می‌شود (اسکرو) — پیشنهاد الکی ممکن نیست
#   ۲) اجرای نهایی، اتمیک در یک تراکنش — یا همه یا هیچ
#   ۳) بعد از تاییدِ هر طرف، هیچ تغییری مجاز نیست — ادیت و اسکم بسته است
#   ۴) معامله‌ی بی‌حرکت ۱۰ دقیقه → لغو خودکار + برگشت اسکرو
#   ۵) هر کس فقط سبد خودش را عوض می‌کند؛ اجرا فقط وقتی هر دو سبد پُر باشد
import json

import db
import player
from registry import ITEMS, UNITS, BOSSES, RES_META

TRADE_TTL = 600   # ⏳ ده دقیقه بدون حرکت = لغو خودکار

RES_MAP = {"meat": "گوشت", "cheese": "پنیر", "sauce": "سس",
           "potato": "سیب‌زمینی", "metal": "فلز", "crystal": "کریستال"}


def _now() -> float:
    return db.now()


# ─── نام‌آرایی ───
def _name(kind: str, ref: str) -> str:
    if kind == "fc":
        return "🪙 فودکوین"
    if kind == "res":
        return RES_META.get(ref, {}).get("emoji", "📦") + " " + RES_MAP.get(ref, ref)
    if kind == "item":
        it = ITEMS.get(ref, {})
        return f"{it.get('emoji', '🎁')} {it.get('name', ref)}"
    if kind == "unit":
        u = UNITS.get(ref, {})
        return f"{u.get('emoji', '🪖')} {u.get('name', ref)}"
    if kind == "boss":
        b = BOSSES.get(ref, {})
        return f"{b.get('emoji', '👹')} {b.get('name', ref)} (اسیرشده)"
    return ref


def _resolve(ref: str, uid: int):
    """فودکوین | منبع | آیتم | یونیت | باسِ اسیرشده‌ی خودت → (kind, ref)"""
    import fuzzy as fz
    r = (ref or "").strip()
    if not r:
        return None
    if fz.norm(r) in ("فودکوین", "سکه", "پول", "fc", "فودکوینها"):
        return ("fc", "fc")
    # باسِ اسیرشده‌ی خودت — قبل از هر چیز (اسم‌ها شبیه کالاها هستند)
    bo = fz.resolve(r, {k: v["name"] for k, v in BOSSES.items()}, fz.BOSS_ALIAS)
    if bo:
        if db.db().one("SELECT 1 FROM infected WHERE user_id=? AND boss_id=?", (uid, bo)):
            return ("boss", bo)
        return ("no_boss", bo)   # باس را می‌شناسد ولی اسیرشده ندارد
    fr = fz.resolve(r, RES_MAP)
    if fr:
        return ("res", fr)
    it = fz.resolve(r, {k: v["name"] for k, v in ITEMS.items()}, fz.ITEM_ALIAS)
    if it:
        return ("item", it)
    un = fz.resolve(r, {k: v["name"] for k, v in UNITS.items()}, fz.UNIT_ALIAS)
    if un:
        return ("unit", un)
    return None


# ─── اسکرو: برداشتن و برگرداندن ───
def _escrow_take(uid: int, kind: str, ref: str, qty: int) -> str:
    """برمی‌دارد یا پیام خطا. برمی‌گرداند '' در صورت موفقیت."""
    if kind == "fc":
        p = player.get(uid)
        if p["fc"] < qty:
            return f"🪙 فقط {p['fc']:,.0f} فودکوین داری."
        player.pay(uid, dict(fc=qty))
    elif kind == "res":
        p = player.get(uid)
        if (p[ref] or 0) < qty:
            return f"📦 {RES_MAP[ref]} کافی نداری ({p[ref] or 0})."
        player.pay(uid, {ref: qty})
    elif kind == "item":
        if player.inv(uid).get(ref, 0) < qty:
            return f"🎁 {_name('item', ref)} کافی نداری."
        player.take_item(uid, ref, qty)
    elif kind == "unit":
        cur = db.db().ex("""UPDATE units SET count=count-? WHERE user_id=? AND unit_id=?
                            AND count>=?""", (qty, uid, ref, qty))
        if cur.rowcount != 1:
            return f"🪖 {_name('unit', ref)} کافی نداری."
    elif kind == "boss":
        cur = db.db().ex("DELETE FROM infected WHERE user_id=? AND boss_id=?", (uid, ref))
        if cur.rowcount != 1:
            return "👹 این باسِ اسیرشده مال تو نیست."
    return ""


def _escrow_give(uid: int, kind: str, ref: str, qty: int, meta: str = ""):
    if kind == "fc":
        player.grant(uid, fc=qty)
    elif kind == "res":
        player.grant(uid, **{ref: qty})
    elif kind == "item":
        player.add_item(uid, ref, qty)
    elif kind == "unit":
        db.db().ex("""INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?)
                      ON CONFLICT(user_id, unit_id) DO UPDATE SET count=count+?""",
                   (uid, ref, qty, qty))
    elif kind == "boss":
        m = json.loads(meta) if meta else {}
        db.db().ex("""INSERT OR REPLACE INTO infected(user_id,boss_id,tier,world_chat,
                      captured_at,expires_at,raid_cd) VALUES(?,?,?,?,?,?,0)""",
                   (uid, ref, m.get("tier", 1), m.get("world_chat"), _now(),
                    m.get("expires_at", _now() + 3 * 86400)))


# ─── چرخه‌ی عمر معامله ───
def expire_stale() -> int:
    rows = db.db().q("""SELECT * FROM trades WHERE status IN ('open','locked')
                        AND updated_at<?""", (_now() - TRADE_TTL,))
    for t in rows:
        _cancel_row(t)
    return len(rows)


def my_trade(chat_id: int, uid: int):
    expire_stale()
    return db.db().one("""SELECT * FROM trades WHERE chat_id=? AND status IN ('open','locked')
                          AND (a_uid=? OR b_uid=?) ORDER BY id DESC LIMIT 1""",
                       (chat_id, uid, uid))


def open_trade(chat_id: int, a: int, b: int) -> tuple:
    if a == b:
        return False, "🔄 با خودت معامله نمی‌شود!"
    if not player.get(a) or not player.get(b):
        return False, "🔄 طرف مقابل بازیکن نیست."
    if my_trade(chat_id, a):
        return False, "🔄 همین حالا یک معامله‌ی بازی داری — تمامش کن یا «لغو معامله»."
    if my_trade(chat_id, b):
        return False, "🔄 طرف مقابل وسط معامله‌ی دیگری است."
    db.db().ex("""INSERT INTO trades(chat_id,a_uid,b_uid,status,created_at,updated_at)
                  VALUES(?,?,?,'open',?,?)""", (chat_id, a, b, _now(), _now()))
    tid = db.db().one("SELECT last_insert_rowid() i")["i"]
    return True, (f"🔄 <b>معامله #{tid} باز شد!</b>\n\n"
                  "هر دو طرف چیزهایتان را بگذارید:\n"
                  "«گذاشتن [چیز] [تعداد]» — فودکوین، منبع، کالا، سرباز و حتی باسِ اسیرشده!\n"
                  "وقتی هر دو راضی بودید: «تایید» — بعد از تایید، تغییر ممنوع است.\n"
                  "پشیمانی؟ «لغو معامله» — همه‌چیز برمی‌گردد.\n"
                  f"⏳ بدون حرکت، {TRADE_TTL // 60} دقیقه دیگر خودکار لغو می‌شود.\n\n"
                  + _render(tid))


def _render(tid: int) -> str:
    t = db.db().one("SELECT * FROM trades WHERE id=?", (tid,))
    if not t:
        return "❓"
    lines = []
    for who, uid in (("🅰️", t["a_uid"]), ("🅱️", t["b_uid"])):
        p = player.get(uid)
        rows = db.db().q("SELECT * FROM trade_items WHERE trade_id=? AND uid=?", (tid, uid))
        if rows:
            basket = " | ".join(f"{_name(r['kind'], r['ref'])} ×{r['qty']}" for r in rows)
        else:
            basket = "— خالی —"
        ok = " ✅" if (t["a_ok"] if who == "🅰️" else t["b_ok"]) else ""
        lines.append(f"{who} {p['avatar'] if p else ''} {p['name'] if p else uid}{ok}\n{basket}")
    return "\n\n".join(lines)


def add_item(chat_id: int, uid: int, ref: str, qty: int) -> tuple:
    t = my_trade(chat_id, uid)
    if not t:
        return False, "🔄 معامله‌ی بازی نداری. روی پیام طرف ریپلای کن و «معامله» بزن."
    if t["status"] == "locked" or t["a_ok"] or t["b_ok"]:
        return False, "🔒 یکی از طرف‌ها تایید کرده — دیگر تغییر نمی‌شود. «لغو معامله» یا «تایید»."
    if qty < 1:
        return False, "🔢 تعداد درست بگو."
    r = _resolve(ref, uid)
    if not r:
        return False, ("❓ نفهمیدم چه چیزی. قابل معامله: فودکوین | گوشت/پنیر/سس/سیب‌زمینی/فلز/کریستال "
                       "| کالا | سرباز | باسِ اسیرشده")
    kind, rref = r
    if kind == "no_boss":
        return False, ("👹 این باس را اسیر نکرده‌ای — فقط باسِ اسیرشده‌ی خودت قابل معامله است "
                       "(«اینفکت» بعد از رید).")
    meta = ""
    if kind == "boss":   # متای باس (تیر/انقضا/دنیا) قبل از حذف ذخیره می‌شود
        inf = db.db().one("SELECT * FROM infected WHERE user_id=? AND boss_id=?", (uid, rref))
        meta = json.dumps(dict(tier=inf["tier"], world_chat=inf["world_chat"],
                               expires_at=inf["expires_at"])) if inf else ""
    err = _escrow_take(uid, kind, rref, qty)
    if err:
        return False, err
    db.db().ex("""INSERT INTO trade_items(trade_id,uid,kind,ref,qty,meta) VALUES(?,?,?,?,?,?)
                  ON CONFLICT(trade_id,uid,kind,ref) DO UPDATE SET qty=qty+?, meta=?""",
               (t["id"], uid, kind, rref, qty, meta, qty, meta))
    db.db().ex("UPDATE trades SET updated_at=? WHERE id=?", (_now(), t["id"]))
    return True, (f"✅ {_name(kind, rref)} ×{qty} در سبدت گذاشته شد (از حسابت برداشته شد).\n\n"
                  + _render(t["id"]))


def remove_item(chat_id: int, uid: int, ref: str, qty: int) -> tuple:
    t = my_trade(chat_id, uid)
    if not t:
        return False, "🔄 معامله‌ی بازی نداری."
    if t["status"] == "locked" or t["a_ok"] or t["b_ok"]:
        return False, "🔒 بعد از تایید، تغییر ممنوع است."
    r = _resolve(ref, uid)
    if not r:
        return False, "❓ چه چیزی را دربیاورم؟"
    kind, rref = r
    if kind == "no_boss":
        return False, "👹 باسِ اسیرشده‌ای نداری."
    row = db.db().one("""SELECT * FROM trade_items WHERE trade_id=? AND uid=? AND kind=? AND ref=?""",
                      (t["id"], uid, kind, rref))
    if not row:
        return False, "🎒 این چیز در سبدت نیست."
    qty = min(qty, row["qty"]) if qty else row["qty"]
    if qty < 1:
        return False, "🔢 تعداد درست بگو."
    _escrow_give(uid, kind, rref, qty, row["meta"])   # متای اصلی برمی‌گردد
    if qty >= row["qty"]:
        db.db().ex("""DELETE FROM trade_items WHERE trade_id=? AND uid=? AND kind=? AND ref=?""",
                   (t["id"], uid, kind, rref))
    else:
        db.db().ex("""UPDATE trade_items SET qty=qty-? WHERE trade_id=? AND uid=? AND kind=? AND ref=?""",
                   (qty, t["id"], uid, kind, rref))
    db.db().ex("UPDATE trades SET updated_at=? WHERE id=?", (_now(), t["id"]))
    return True, (f"↩️ {_name(kind, rref)} ×{qty} به حسابت برگشت.\n\n" + _render(t["id"]))


def confirm(chat_id: int, uid: int) -> tuple:
    t = my_trade(chat_id, uid)
    if not t:
        return False, "🔄 معامله‌ی بازی نداری."
    mine = "a" if uid == t["a_uid"] else "b"
    if (t["a_ok"] if mine == "a" else t["b_ok"]):
        return False, "✅ تاییدت ثبت شده — منتظر طرف دیگر."
    my_items = db.db().one("SELECT COUNT(*) c FROM trade_items WHERE trade_id=? AND uid=?",
                           (t["id"], uid))["c"]
    if my_items == 0:
        return False, "🎒 اول چیزی در سبدت بگذار: «گذاشتن [چیز] [تعداد]»"
    db.db().ex(f"UPDATE trades SET {mine}_ok=1, updated_at=? WHERE id=?", (_now(), t["id"]))
    t = db.db().one("SELECT * FROM trades WHERE id=?", (t["id"],))
    if not (t["a_ok"] and t["b_ok"]):
        other = db.db().one("SELECT name FROM accounts WHERE user_id=?",
                            ((t["b_uid"] if mine == "a" else t["a_uid"]),))
        return True, (f"✅ تایید شد — منتظر {other['name'] if other else 'طرف دیگر'}.\n"
                      "🔒 از این لحظه دیگر تغییری نمی‌شود.")
    # ─── هر دو تایید کردند → اجرای اتمیک ───
    import perf
    with perf.key_lock(("trade", t["id"])):
        t = db.db().one("SELECT * FROM trades WHERE id=?", (t["id"],))
        if t["status"] != "open":
            return False, "🔄 این معامله دیگر باز نیست."
        with db.db().tx():
            rows = db.db().q("SELECT * FROM trade_items WHERE trade_id=?", (t["id"],))
            for r in rows:
                other = t["b_uid"] if r["uid"] == t["a_uid"] else t["a_uid"]
                meta = r["meta"]
                if r["kind"] == "boss" and not meta:
                    meta = json.dumps(dict(tier=1, world_chat=t["chat_id"],
                                           expires_at=_now() + 3 * 86400))
                _escrow_give(other, r["kind"], r["ref"], r["qty"], meta)
            db.db().ex("DELETE FROM trade_items WHERE trade_id=?", (t["id"],))
            db.db().ex("UPDATE trades SET status='done', updated_at=? WHERE id=?", (_now(), t["id"]))
    db.db().ex("INSERT INTO txlog(chat_id,user_id,kind,detail,at) VALUES(?,?,?,?,?)",
               (t["chat_id"], t["a_uid"], "trade", f"T{t['id']} done", _now()))
    return True, (f"🤝 <b>معامله #{t['id']} انجام شد!</b>\nهر دو طرف، همه‌چیز را تحویل گرفتند.\n\n"
                  + _render_done(t["id"]))


def _render_done(tid: int) -> str:
    t = db.db().one("SELECT * FROM trades WHERE id=?", (tid,))
    a, b = player.get(t["a_uid"]), player.get(t["b_uid"])
    return f"🅰️ {a['name']} ⇄ 🅱️ {b['name']} — معامله‌ی امن و کامل ✅"


def _cancel_row(t):
    rows = db.db().q("SELECT * FROM trade_items WHERE trade_id=?", (t["id"],))
    with db.db().tx():
        for r in rows:
            meta = r["meta"]
            if r["kind"] == "boss" and not meta:
                meta = json.dumps(dict(tier=1, world_chat=t["chat_id"],
                                       expires_at=_now() + 3 * 86400))
            _escrow_give(r["uid"], r["kind"], r["ref"], r["qty"], meta)
        db.db().ex("DELETE FROM trade_items WHERE trade_id=?", (t["id"],))
        db.db().ex("UPDATE trades SET status='cancelled', updated_at=? WHERE id=?",
                   (_now(), t["id"]))


def cancel(chat_id: int, uid: int) -> tuple:
    t = my_trade(chat_id, uid)
    if not t:
        return False, "🔄 معامله‌ی بازی نداری."
    _cancel_row(t)
    return True, (f"↩️ معامله #{t['id']} لغو شد — همه‌چیز به صاحبانش برگشت.")
