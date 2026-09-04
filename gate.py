# 📢 Channel Gate — عضویت اجباری کانال؛ با کش، بدون اسپم به تلگرام
import time

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config

_cache: dict[int, tuple[bool, float]] = {}
TTL_OK = 600      # عضو → ۱۰ دقیقه کش
TTL_NO = 45       # غیرعضو → چک سریع‌تر بعد از پیوستن


async def is_member(bot, user_id: int) -> bool:
    """عضوِ کانال هست؟ خطای API → باز گذر (بات نمی‌ایستد)."""
    hit = _cache.get(user_id)
    t = time.time()
    if hit and t - hit[1] < (TTL_OK if hit[0] else TTL_NO):
        return hit[0]
    try:
        st = (await bot.get_chat_member(config.FORCE_CHANNEL, user_id)).status
        ok = st in ("member", "administrator", "creator")
    except Exception:
        return True
    _cache[user_id] = (ok, t)
    return ok


def invalidate(user_id: int):
    _cache.pop(user_id, None)


def join_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 عضویت در کانال", url=config.CHANNEL_URL)
    ]])


def join_text() -> str:
    return ("📢 <b>برای بازی، اول عضو کانال فوودورس شو</b>\n\n"
            "یک کلیک کافی است — بعد برگرد و همین دستور را دوباره بزن ✅")
