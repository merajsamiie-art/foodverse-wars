# 🔄 Market Engine — قیمت پویا (عرضه/تقاضا) + بازار بازیکن‌ها + لاگ
import db
import perf
import player
from config import (CD_MARKET, MARKET_TAX, LISTING_FEE, MAX_LISTING_PRICE,
                    NPC_SELL_RATIO, PRICE_MIN_MULT, PRICE_MAX_MULT, PRICE_STEP, BUY_LIMIT)
from registry import ITEMS, RES_PRICES, RES_META, item_name


def _log(chat_id, user_id, kind, detail):
    db.db().ex("INSERT INTO txlog(chat_id, user_id, kind, detail, at) VALUES(?,?,?,?,?)",
               (chat_id, user_id, kind, detail, db.now()))


# ─── 💹 قیمت پویای NPC ───
def _ensure_state():
    for res, base in RES_PRICES.items():
        db.db().ex("INSERT OR IGNORE INTO market_state(res, base, mult, updated) VALUES(?,?,1.0,?)",
                   (res, base, db.now()))


def get_price(res: str) -> int:
    """قیمت فعلی = پایه × ضراب (قفل‌شده بین ۵۰٪ تا ۲۰۰٪)."""
    _ensure_state()
    r = db.db().one("SELECT base, mult FROM market_state WHERE res=?", (res,))
    if not r:
        return RES_PRICES.get(res, 10)
    p = r["base"] * r["mult"]
    return max(1, int(round(p)))


def _shift_price(res: str, delta: float):
    """خرید → قیمت بالا، فروش → پایین؛ با سقف/کف."""
    _ensure_state()
    r = db.db().one("SELECT mult FROM market_state WHERE res=?", (res,))
    mult = (r["mult"] if r else 1.0) + delta
    mult = max(PRICE_MIN_MULT, min(PRICE_MAX_MULT, mult))
    db.db().ex("UPDATE market_state SET mult=?, updated=? WHERE res=?", (mult, db.now(), res))
    perf.LB_CACHE.drop(("prices",))


def decay_prices():
    """اسکجولر ساعتی: بازگشت آرام به قیمت پایه."""
    _ensure_state()
    from config import PRICE_DECAY_H
    db.db().ex("""UPDATE market_state
                  SET mult = MAX(?, MIN(?, mult + (1.0 - mult) * ?)), updated=?""",
               (PRICE_MIN_MULT, PRICE_MAX_MULT, PRICE_DECAY_H, db.now()))


def prices_text() -> str:
    _ensure_state()
    cached = perf.LB_CACHE.get(("prices",))
    if cached:
        return cached
    rows = db.db().q("SELECT res, base, mult FROM market_state")
    lines = ["💹 <b>صرافی کارخانه</b> — قیمت‌های زنده", ""]
    for r in rows:
        m = RES_META[r["res"]]
        cur = int(r["base"] * r["mult"])
        trend = "📈" if r["mult"] > 1.02 else ("📉" if r["mult"] < 0.98 else "➖")
        sell = int(cur * NPC_SELL_RATIO)
        lines.append(f"{m['emoji']} {m['name']}: خرید {cur} | فروش {sell} {trend}")
    out = "\n".join(lines) + ("\n\n📉 خرید زیاد گران می‌کند، فروش زیاد ارزان — بازار نفس می‌کشد."
                              "\n🛒 «fw خرید منبع گوشت 10» | 💸 «fw فروش منبع فلز 5»")
    perf.LB_CACHE.set(("prices",), out)
    return out


def npc_buy(user_id: int, res: str, qty: int) -> tuple:
    p = player.get(user_id)
    if res not in RES_PRICES:
        return False, "🏦 منبع‌ها: گوشت/پنیر/سس/سیب‌زمینی/فلز/کریستال"
    qty = max(1, min(qty, BUY_LIMIT))
    price = get_price(res) * qty
    if p["fc"] < price:
        return False, f"🪙 {RES_META[res]['name']} ×{qty} = {price} FC — کافی نداری."
    if player.on_cd(user_id, "market"):
        return False, f"⏳ {player.cd_left(user_id, 'market')} ثانیه."
    with db.db().tx():
        player.pay(user_id, dict(fc=price))
        player.grant(user_id, **{res: qty})
        _shift_price(res, PRICE_STEP * (qty / 100 + 0.3))
    player.set_cd(user_id, "market", CD_MARKET)
    _log(None, user_id, "npc_buy", f"{res}x{qty}={price}")
    player.dtrack(user_id, "bought")
    return True, f"🏦 خریدی: {RES_META[res]['emoji']} {RES_META[res]['name']} ×{qty} (−{price} FC)"


def npc_sell(user_id: int, res: str, qty: int) -> tuple:
    p = player.get(user_id)
    if res not in RES_PRICES:
        return False, "🏦 چنین منبعی نیست."
    qty = max(1, min(qty, int(p[res] or 0), BUY_LIMIT))
    if qty < 1:
        return False, "🎒 از این منبع چیزی نداری."
    gain = int(get_price(res) * NPC_SELL_RATIO * qty)
    with db.db().tx():
        player.pay(user_id, {res: qty})
        player.grant(user_id, fc=gain)
        _shift_price(res, -PRICE_STEP * (qty / 100 + 0.3))
    player.set_cd(user_id, "market", CD_MARKET)
    player.dtrack(user_id, "sold")
    _log(None, user_id, "npc_sell", f"{res}x{qty}=+{gain}")
    return True, f"🏦 فروختی: {RES_META[res]['emoji']} ×{qty} (+{gain} FC)"


# ─── 🔄 بازار بازیکن‌ها ───
def sell_item(user_id: int, chat_id: int, item_ref: str, qty: int, price: int) -> tuple:
    p = player.get(user_id)
    iid = _resolve_item(item_ref)
    if not iid:
        return False, "🔄 چنین کالایی نیست. «fw انبار»"
    it = ITEMS[iid]
    if it.get("kind") not in ("material", "booster", "equip"):
        return False, "🚫 این کالا قابل معامله نیست."
    qty = max(1, min(qty, player.inv(user_id).get(iid, 0)))
    if qty < 1:
        return False, "🎒 نداریش."
    price = max(1, min(int(price), MAX_LISTING_PRICE))
    if p["fc"] < LISTING_FEE:
        return False, f"🪙 هزینه‌ی درج آگهی {LISTING_FEE} FC است."
    if player.on_cd(user_id, "market"):
        return False, f"⏳ {player.cd_left(user_id, 'market')} ثانیه."
    with db.db().tx():
        player.take_item(user_id, iid, qty)
        player.pay(user_id, dict(fc=LISTING_FEE))
        db.db().ex("""INSERT INTO listings(chat_id, seller_uid, item_id, qty, price, created_at)
                      VALUES(?,?,?,?,?,?)""",
                   (chat_id, user_id, iid, qty, price, db.now()))
    player.set_cd(user_id, "market", CD_MARKET)
    _log(chat_id, user_id, "list", f"{iid}x{qty}@{price}")
    return True, (f"🔄 آگهی ثبت شد: {item_name(iid)} ×{qty} → {price} FC\n"
                  f"(کارمزد درج {LISTING_FEE} FC | مالیات فروش {int(MARKET_TAX * 100)}٪)")


def buy_listing(user_id: int, chat_id: int, listing_id: int) -> tuple:
    p = player.get(user_id)
    with perf.key_lock(("listing", listing_id)):
        l = db.db().one("SELECT * FROM listings WHERE id=? AND active=1", (listing_id,))
        if not l:
            return False, "🔄 این آگهی دیگر فعال نیست."
        if l["seller_uid"] == user_id:
            return False, "🔄 آگهی خودت را نمی‌توانی بخری."
        if p["fc"] < l["price"]:
            return False, f"🪙 قیمت {l['price']} FC — کافی نداری."
        if player.inv_free(user_id) < 1:
            return False, "🎒 انبار پر است."
        with db.db().tx():
            player.pay(user_id, dict(fc=l["price"]))
            player.add_item(user_id, l["item_id"], l["qty"])
            net = round(l["price"] * (1 - MARKET_TAX), 1)
            player.grant(l["seller_uid"], fc=net)
            db.db().ex("UPDATE listings SET active=0, buyer_uid=? WHERE id=?", (user_id, listing_id))
        _log(chat_id, user_id, "buy", f"L{listing_id} {l['item_id']}x{l['qty']}={l['price']}")
        _log(chat_id, l["seller_uid"], "sold", f"L{listing_id} +{net}")
        return True, f"🛒 خریداری شد: {item_name(l['item_id'])} ×{l['qty']} (−{l['price']} FC)"


def market_text(chat_id: int, page: int = 0) -> str:
    rows = db.db().q("""SELECT l.*, a.name AS seller FROM listings l
                        JOIN accounts a ON a.user_id=l.seller_uid
                        WHERE l.chat_id=? AND l.active=1
                        ORDER BY l.created_at DESC LIMIT 100""", (chat_id,))
    per = 8
    pages = max(1, (len(rows) + per - 1) // per)
    page = max(0, min(page, pages - 1))
    if not rows:
        return ("🔄 <b>بازار این دنیا</b> — خالی است.\n"
                "فروش: «fw بفروش [کالا] [تعداد] [قیمت]» | خرید: «fw برداشتن [شماره]»")
    lines = [f"🔄 <b>بازار این دنیا</b> — صفحه {page + 1}/{pages}", ""]
    for l in rows[page * per:(page + 1) * per]:
        lines.append(f"#{l['id']} • {item_name(l['item_id'])} ×{l['qty']} → 🪙 {l['price']:,} FC — {l['seller']}")
    lines.append("\n🛒 «fw برداشتن [شماره]» | «fw بازار 2» برای صفحه‌ی بعد")
    return "\n".join(lines)


def price_history(chat_id: int, item_ref: str) -> str:
    iid = _resolve_item(item_ref)
    if not iid:
        return "🔄 کالای نامعتبر."
    rows = db.db().q("""SELECT price, qty, at FROM listings
                        WHERE chat_id=? AND item_id=? AND active=0
                        ORDER BY at DESC LIMIT 10""", (chat_id, iid))
    if not rows:
        return f"📊 {item_name(iid)}: هنوز معامله‌ای ثبت نشده."
    lines = [f"📊 <b>سابقه‌ی قیمت</b> — {item_name(iid)}"]
    for r in rows:
        lines.append(f"• ×{r['qty']} → 🪙 {r['price']:,} FC")
    return "\n".join(lines)


def _resolve_item(ref: str):
    ref = (ref or "").strip()
    for iid, it in ITEMS.items():
        if ref == iid or ref == it["name"] or ref == f"{it['emoji']} {it['name']}":
            return iid
    return None
