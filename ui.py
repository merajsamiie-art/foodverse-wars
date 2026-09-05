# 🎨 UI Engine — کیبورد اینلاین، هاب پیوی، منوی گروه، پنل مدیر
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def private_kb(bot_username: str, group_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ افزودن به گروه",
                              url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton(text="👥 گروه رسمی", url=group_link),
         InlineKeyboardButton(text="📢 کانال رسمی", url="https://t.me/FoodverseWars")],
        [InlineKeyboardButton(text="🧭 هاب من", callback_data="h:0:hub")],
    ])


def menu_kb(user_id: int) -> InlineKeyboardMarkup:
    """🍔 منوی واحد فوودورس — همه‌چیز در یک منو؛ گروه و پیوی هیچ فرقی ندارد."""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[
        [b("🍔 منوی فوودورس", "me")],
        [b("👤 پروفایل", "me"), b("🏠 پایگاه", "base"), b("🪖 ارتش", "army")],
        [b("👑 باس", "boss"), b("🔄 بازار", "market"), b("🏆 رتبه", "top")],
        [b("🎒 انبار", "inv"), b("📦 پک‌های من", "packs"), b("💎 بتل‌پس", "pass")],
        [b("🛒 فروشگاه", "shop"), b("🎨 ظاهر", "cosmetic"), b("🤝 اتحاد", "ally")],
        [b("🛒 خرید ارتش (فودکوین)", "armyshop")],
        [b("🎁 روزانه", "daily"), b("📖 آموزش", "help")],
        [b("⚡️ شیر", "milk"), b("🏭 شیفت", "shift"), b("🚓 گشت", "patrol")],
    ])


def hub_kb(user_id: int) -> InlineKeyboardMarkup:
    """همان منوی واحد — برای سازگاری دکمه‌های بازگشت."""
    return menu_kb(user_id)


def army_shop_kb(user_id: int) -> InlineKeyboardMarkup:
    """🛒 فروشگاه ارتش — خرید شخصیت با فودکوین، فقط با دکمه."""
    from registry import UNITS
    from army import unit_price
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    rows = []
    row = []
    for uid_, un in UNITS.items():
        if not un.get("cost"):
            continue
        row.append(b(f"{un['emoji']} {un['name'].split()[0]} {unit_price(uid_):,}", f"buy:{uid_}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([b("🔄 بروزرسانی", "armyshop"), b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_kb(user_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """📖 راهنمای صفحه‌ای — ۸ صفحه کوتاه، دکمه‌ها در ۲ ردیف"""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    n = 8
    fa = ("۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸")
    rows = []
    for r0 in (0, 4):
        rows.append([b(("🔘" if i == page else "⚪️") + fa[i], f"hp{i}")
                     for i in range(r0, min(r0 + 4, n))])
    rows.append([b("💡 پیشنهاد کوچیار", "hint"), b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════ کیبوردهای دکمه‌ای — بازی بدون تایپ ═══════════

def base_kb(user_id: int) -> InlineKeyboardMarkup:
    """🏠 پایگاه — ارتقا با یک دکمه + قیمت زنده‌ی سطح بعد."""
    from registry import BUILDINGS
    from base import blds, _up_cost
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    lv = blds(user_id)
    rows, row = [], []
    for bid, bd in BUILDINGS.items():
        cur = lv.get(bid, 0)
        if cur >= bd["maxlv"]:
            lbl = f"✅ {bd['name']} — کامل"
        else:
            fc = _up_cost(bid, cur).get("fc", 0)
            lbl = f"⬆️ {bd['name']} {cur}→{cur + 1} · {fc:,}🪙"
        row.append(b(lbl, f"up:{bid}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quick_kb(user_id: int) -> InlineKeyboardMarkup:
    """⚡️ اکشن‌های سریع درآمد — زیر پروفایل."""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[[
        b("🥛 شیر رایگان", "milk"), b("🏭 شیفت", "shift"), b("🚓 گشت", "patrol"),
    ], [b("🎁 روزانه", "daily"), b("📒 دفتر ثبت", "ledger"), b("🍔 منو", "hub")]])


def boss_kb(user_id: int) -> InlineKeyboardMarkup:
    """👹 باس فعال — حمله با یک دکمه."""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[[
        b("⚔️ حمله کن!", "bosshit"),
    ], [b("🔄 وضعیت", "boss"), b("🍔 منو", "hub")]])


def packs_kb(user_id: int) -> InlineKeyboardMarkup:
    """📦 پک‌ها — خرید و بازکردن با دکمه."""
    from registry import PACKS
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    rows = []
    for pid, pk in PACKS.items():
        if pk.get("fc_price"):
            rows.append([b(f"🛒 خرید {pk['emoji']} {pk['name'].split()[0]} {pk['fc_price']:,}", f"pkbuy:{pid}"),
                         b("🎁 بازکردن", f"pkopen:{pid}")])
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pass_kb(user_id: int) -> InlineKeyboardMarkup:
    """🎫 بتل‌پس — دریافت جایزه پله با دکمه."""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    fa = ("۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹")
    rows = [[b(f"🎁 {fa[i-1]}", f"bp:{i}f") for i in range(1, 7)],
            [b(f"👑 {fa[i-1]}", f"bp:{i}p") for i in range(1, 7)]]
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def market_kb(user_id: int, listings: list) -> InlineKeyboardMarkup:
    """🔄 بازار — خرید آگهی با دکمه (لیست: [(id, label)])"""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    rows = [[b(label, f"mkt:{lid}")] for lid, label in listings[:8]]
    rows.append([b("📊 قیمت‌ها", "prices"), b("🔄 بروزرسانی", "market")])
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def army_view_kb(user_id: int) -> InlineKeyboardMarkup:
    """🪖 ارتش — رفتن به فروشگاه دکمه‌ای."""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[[
        b("🛒 خرید سرباز (فودکوین)", "armyshop"),
    ], [b("🪖 ارتش من", "army"), b("🍔 منو", "hub")]])


def inv_kb(user_id: int) -> InlineKeyboardMarkup:
    """🎒 انبار — تجهیز/غیرفعال با دکمه + بازکردن پک"""
    import player, db
    from registry import ITEMS, PACKS
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    rows = []
    for iid, qty in sorted(player.inv(user_id).items()):
        if iid.startswith("pack_"):
            pid = iid[5:]
            pk = PACKS.get(pid)
            if pk:
                rows.append([b(f"🎁 بازکردن {pk['emoji']} {pk['name']} ×{qty}", f"pkopen:{pid}")])
        elif ITEMS.get(iid, {}).get("kind") == "equip":
            it = ITEMS[iid]
            r = db.db().one("SELECT equipped FROM items WHERE user_id=? AND item_id=?",
                            (user_id, iid))
            lbl = f"✅ {it['emoji']} {it['name']} (فعال)" if (r and r["equipped"]) else f"⚙️ {it['emoji']} {it['name']}"
            rows.append([b(lbl, f"eq:{iid}")])
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def infected_kb(user_id: int) -> InlineKeyboardMarkup:
    """🧟 اینفکتد — گرفتن با دکمه"""
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[[
        b("🧟 گرفتن اینفکتد", "infect"),
    ], [b("🔄 وضعیت", "infected"), b("🍔 منو", "hub")]])


def shop_kb(user_id: int) -> InlineKeyboardMarkup:
    """🛒 فروشگاه — اسلات‌های چرخشی و پک‌ها، همه با دکمه"""
    from shop import daily_slots, weekly_slots, _user_bought, _slot_name
    from registry import SHOP_POOL, PACKS
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    rows = []
    for slot in daily_slots() + weekly_slots():
        m_ = SHOP_POOL.get(slot)
        if not m_:
            continue
        bought = _user_bought(user_id, slot)
        left = m_["limit"] - bought
        if left <= 0:
            lbl = f"✅ {_slot_name(slot)} — سهمیه پر"
        else:
            lbl = f"🛒 {_slot_name(slot)} · {m_['fc']:,}🪙 ×{left}"
        rows.append([b(lbl, f"sbuy:{slot}")])
    for pid, pk in PACKS.items():
        if pk.get("fc_price"):
            rows.append([b(f"📦 {pk['emoji']} {pk['name']} · {pk['fc_price']:,}🪙", f"pkbuy:{pid}"),
                         b("🎁 بازکردن", f"pkopen:{pid}")])
    rows.append([b("🍔 منو", "hub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sub_kb(user_id: int, buttons: list) -> InlineKeyboardMarkup:
    rows, row = [], []
    for t, a in buttons:
        row.append(InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{a}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"h:{user_id}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order_kb(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید", callback_data=f"adm:{order_id}:ok"),
         InlineKeyboardButton(text="❌ رد", callback_data=f"adm:{order_id}:no")],
        [InlineKeyboardButton(text="🔍 اطلاعات بیشتر", callback_data=f"adm:{order_id}:info")],
    ])
