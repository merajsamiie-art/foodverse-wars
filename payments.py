# 💳 Payment Engine — کارت‌به‌کارت چندلایه + تأیید مدیر + تراکنش یک‌بارمصرف
import hashlib
import random

import db
import player
from config import PAYMENT_CARD, PAYMENT_HOLDER, ORDER_EXPIRE_S
from registry import PACKS, PASSES


def _log(user_id, kind, detail):
    db.db().ex("INSERT INTO txlog(chat_id, user_id, kind, detail, at) VALUES(NULL,?,?,?,?)",
               (user_id, kind, detail, db.now()))


def products_text() -> str:
    lines = ["🛍 <b>فروشگاه ویژه</b> — پک‌ها و پاس‌ها", ""]
    lines.append("📦 <b>پک‌ها</b> (شانس‌ها شفاف: «fw شانس [نام]»):")
    for pid, pk in PACKS.items():
        if pk["price_toman"] > 0:
            lines.append(f"{pk['emoji']} {pk['name']}\n{pk['en']}\n   💰 {pk['price_toman']:,} تومان")
    lines.append("\n💎 <b>Battle Pass</b>:")
    for pt, ps in PASSES.items():
        lines.append(f"{ps['emoji']} {ps['name']} ({ps['days']} روز)\n{ps['en']}\n   💰 {ps['price_toman']:,} تومان")
    lines.append("\nℹ️ پرداخت: کارت‌به‌کارت + تأیید دستی مدیر (امن و بدون ربات)"
                 "\n🛒 «fw سفارش [نام محصول]»")
    return "\n".join(lines)


def _price_of(product: str) -> int:
    if product in PACKS:
        return PACKS[product]["price_toman"]
    if product in PASSES:
        return PASSES[product]["price_toman"]
    return 0


def create_order(user_id: int, product_ref: str) -> tuple:
    """۱) سفارش + Order ID یکتا + انقضا ۳۰ دقیقه."""
    product = _resolve_product(product_ref)
    if not product:
        return False, "🛍 محصول نامعتبر. «fw خرید»"
    price = _price_of(product)
    if price <= 0:
        return False, "🛍 این محصول فروشی نیست."
    # سفارش باز قبلی؟
    open_o = db.db().one("""SELECT order_id FROM orders WHERE user_id=? AND
                            status IN ('pending_payment','pending_review')""", (user_id,))
    if open_o:
        return False, (f"🧾 یک سفارش بازی داری: <code>{open_o['order_id']}</code>\n"
                       "اول همین را پرداخت کن یا «fw لغو سفارش».")
    order_id = f"FW-{random.randint(100000, 999999)}"
    while db.db().one("SELECT 1 FROM orders WHERE order_id=?", (order_id,)):
        order_id = f"FW-{random.randint(100000, 999999)}"
    t = db.now()
    with db.db().tx():
        db.db().ex("""INSERT INTO orders(order_id, user_id, product, amount,
                      status, created_at, expires_at)
                      VALUES(?,?,?,?,'pending_payment',?,?)""",
                   (order_id, user_id, product, price, t, t + ORDER_EXPIRE_S))
    pay_info = _payment_text(order_id, price)
    return True, (f"🧾 <b>سفارش ثبت شد</b>\n"
                  f"🔢 کد سفارش: <code>{order_id}</code>\n"
                  f"⏳ ۳۰ دقیقه اعتبار دارد.\n\n{pay_info}\n\n"
                  f"بعد از پرداخت، همین‌جا عکس رسید + شماره پیگیری را بفرست:\n"
                  f"«fw رسید [شماره پیگیری]» همراه با عکس")


def _payment_text(order_id: str, price: int) -> str:
    holder = f"\n👤 به نام: {PAYMENT_HOLDER}" if PAYMENT_HOLDER else ""
    return (f"💳 <b>اطلاعات پرداخت</b>\n"
            f"🏦 شماره کارت: <code>{PAYMENT_CARD}</code>{holder}\n"
            f"💰 مبلغ: <b>{price:,} تومان</b>\n"
            f"🔢 در توضیحات واریز بنویس: <code>{order_id}</code>")


def cancel_order(user_id: int) -> tuple:
    r = db.db().ex("""UPDATE orders SET status='cancelled'
                      WHERE user_id=? AND status='pending_payment'""", (user_id,))
    if r.rowcount:
        return True, "🧾 سفارش باز لغو شد."
    return False, "🧾 سفارش بازی نداری."


def submit_receipt(user_id: int, tracking_no: str, photo_hash: str) -> tuple:
    """۲) ارسال رسید: چندلایه چک می‌شود؛ فیش تنها تأییدکننده نیست."""
    if not tracking_no or not photo_hash:
        return False, "🧾 عکس رسید + «fw رسید [شماره پیگیری]» لازم است."
    o = db.db().one("""SELECT * FROM orders WHERE user_id=? AND status='pending_payment'
                       ORDER BY id DESC LIMIT 1""", (user_id,))
    if not o:
        return False, "🧾 سفارش بازی نداری. «fw سفارش [محصول]»"
    if db.now() > (o["expires_at"] or 0):
        db.db().ex("UPDATE orders SET status='expired' WHERE id=?", (o["id"],))
        return False, "⚫ سفارشت منقضی شده — دوباره سفارش بده."
    # تکراری‌ها
    if db.db().one("SELECT 1 FROM orders WHERE tracking_no=?", (tracking_no,)):
        return False, "🚫 این شماره پیگیری قبلاً استفاده شده."
    if db.db().one("SELECT 1 FROM orders WHERE receipt_hash=?", (photo_hash,)):
        return False, "🚫 این عکس رسید قبلاً ارسال شده."
    with db.db().tx():
        db.db().ex("""UPDATE orders SET status='pending_review', tracking_no=?,
                      receipt_hash=? WHERE id=? AND status='pending_payment'""",
                   (tracking_no, photo_hash, o["id"]))
    _log(user_id, "receipt", o["order_id"])
    return True, o  # هندلر برای مدیر ارسال می‌کند


def order_info_for_admin(o: dict) -> str:
    p = player.get(o["user_id"])
    prod = _product_name(o["product"])
    import datetime
    t = datetime.datetime.fromtimestamp(o["created_at"]).strftime("%m-%d %H:%M")
    return (f"🧾 <b>سفارش در انتظار بررسی</b>\n"
            f"👤 کاربر: {p['name'] if p else '?'}\n"
            f"🆔 <code>{o['user_id']}</code>\n"
            f"📦 محصول: {prod}\n"
            f"💰 مبلغ: {o['amount']:,} تومان\n"
            f"🔢 کد سفارش: <code>{o['order_id']}</code>\n"
            f"🧾 پیگیری: <code>{o['tracking_no']}</code>\n"
            f"⏱ ثبت: {t}\n\n"
            f"⚠️ فیش تنها تأییدکننده نیست — واریز واقعی را در بانک چک کن.")


def decide(order_id: str, admin_id: int, approve: bool) -> tuple:
    """۳) تصمیم مدیر → اعطای یک‌بارمصرف با تراکنش."""
    o = db.db().one("SELECT * FROM orders WHERE order_id=?", (order_id,))
    if not o or o["status"] != "pending_review":
        return False, None, "🧾 سفارش معتبر/در انتظار نیست."
    with db.db().tx():
        cur = db.db().ex("""UPDATE orders SET status=?, admin_id=?, decided_at=?
                            WHERE id=? AND status='pending_review'""",
                         ("approved" if approve else "rejected", admin_id, db.now(), o["id"]))
        if cur.rowcount != 1:
            return False, None, "🚿 هم‌زمان تصمیم دیگری ثبت شد."
        if approve:
            msg = _grant_product(o["user_id"], o["product"])
        else:
            msg = "🔴 سفارشت رد شد. اگر اشتباه بوده با مدیر تماس بگیر."
    return True, o, msg


def _grant_product(user_id: int, product: str) -> str:
    if product in PACKS:
        player.add_item(user_id, f"pack_{product}", 1)
        pk = PACKS[product]
        return f"✅ پرداخت تأیید شد! {pk['emoji']} {pk['name']} به انبارت اضافه شد: «fw بازکردن {pk['name']}»"
    if product in PASSES:
        import passsys
        ok, msg = passsys.activate(user_id, product, PASSES[product]["days"])
        return msg
    return "✅ پرداخت تأیید شد."


def _resolve_product(ref: str):
    ref = (ref or "").strip()
    for pid, pk in PACKS.items():
        if ref in (pid, pk["name"], pk["en"]):
            return pid
    for pt, ps in PASSES.items():
        if ref in (pt, ps["name"], ps["en"]):
            return pt
    return None


def _product_name(product: str) -> str:
    if product in PACKS:
        return f"{PACKS[product]['emoji']} {PACKS[product]['name']}"
    if product in PASSES:
        return f"{PASSES[product]['emoji']} {PASSES[product]['name']}"
    return product


def hash_photo(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
