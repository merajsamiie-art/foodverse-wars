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


def hub_kb(user_id: int) -> InlineKeyboardMarkup:
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[
        [b("👤 کارت من", "card"), b("🎨 سفارشی‌سازی", "cosmetic")],
        [b("📦 پک‌های من", "packs"), b("💎 بتل‌پس", "pass")],
        [b("🛒 فروشگاه", "shop"), b("🛍 فروشگاه ویژه", "store")],
        [b("🎁 روزانه", "daily"), b("📖 آموزش", "help")],
    ])


def menu_kb(user_id: int) -> InlineKeyboardMarkup:
    b = lambda t, c: InlineKeyboardButton(text=t, callback_data=f"h:{user_id}:{c}")
    return InlineKeyboardMarkup(inline_keyboard=[
        [b("👤 پروفایل", "me"), b("🏠 پایگاه", "base"), b("🪖 ارتش", "army")],
        [b("🎒 انبار", "inv"), b("🛠 ساخت", "craft"), b("👑 باس", "boss")],
        [b("🤝 اتحاد", "ally"), b("🔄 بازار", "market"), b("🏆 رتبه", "top")],
        [b("🎁 روزانه", "daily"), b("📖 آموزش", "help")],
    ])


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
