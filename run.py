# ▶️ FOODVERSE WARS — اجرای اصلی + میدل‌ورهای پرفورمنس
import asyncio
import datetime
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.types import CallbackQuery, Message

import db
import events
import handlers
import media
import perf
import config as cfg
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("foodverse")


# ─── 🚦 میدل‌ور تراتل: ۲۰ پیام/دقیقه به‌ازای کاربر + سپر خطا ───
class PerfMiddleware:
    def __init__(self):
        self.seen: dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            if not perf.allow(user.id, 20, 60):
                perf.STATS.throttled += 1
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return   # سایلنت — ضد فلود
        try:
            return await handler(event, data)
        except Exception:
            perf.STATS.errors += 1
            log.exception("handler error")
            return   # ضدکرش: هیچ خطایی بات را نمی‌کشد


class StatsMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            perf.STATS.msgs += 1
        return await handler(event, data)


async def main():
    assert BOT_TOKEN, "BOT_TOKEN نیست"
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    mw = PerfMiddleware()
    dp.message.outer_middleware(mw)
    dp.callback_query.outer_middleware(mw)
    dp.message.middleware(StatsMiddleware())

    handlers.reg_slash(handlers.router)
    handlers.router.message.register(handlers.on_text, F.text)
    handlers.router.callback_query.register(handlers.on_callback)
    dp.include_router(handlers.router)

    db.init()
    media.ensure_table()
    eng = events.EventEngine(bot, interval=900)
    eng.start()
    log.info("🍔 FOODVERSE WARS ONLINE")
    try:
        await poll_forever(bot, dp)
    except SystemExit:
        raise
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass
        db.db().close()


async def poll_forever(bot, dp):
    """🔄 پولینگ با استراحت دقیق:
    • فقط ۵ تا ۷ صبح تهران: نفس عمیق (long-poll کوتاه‌تر + ۵ ثانیه خواب) — ولی فعال و پاسخ‌گو
    • بقیه‌ی ساعات (مخصوصا شب): پرقدرت — بدون هیچ خواب اضافه، فوری پاسخ می‌دهد
    • همیشه روشن ۲۴/۷ — هرگز خاموش نمی‌شود."""
    offset = 0
    while True:
        try:
            h = datetime.datetime.now(cfg.TZ).hour
            resting = 5 <= h < 7                    # 😴 فقط ۵ تا ۷ صبح
            updates = await bot.get_updates(
                offset=offset,
                timeout=10 if resting else 25,      # استراحت: چک سبک‌تر | روز/شب: full-speed
                allowed_updates=["message", "callback_query"])
        except TelegramConflictError:
            log.error("⛔ getUpdates conflict — یک نمونه‌ی دیگر بات را اجرا کرده. خارج می‌شوم تا GHA ری‌استارت کند.")
            raise SystemExit(2)
        except Exception as e:
            log.warning(f"poll error: {e} — ۳ ثانیه استراحت")
            await asyncio.sleep(3)
            continue
        if not updates:
            if resting:                             # 😴 فقط در پنجره‌ی استراحت
                await asyncio.sleep(5)
            continue
        for u in updates:
            offset = max(offset, u.update_id + 1)
            try:
                await dp.feed_update(bot, u)
            except Exception:
                perf.STATS.errors += 1
                log.exception("update error")
        await asyncio.sleep(0)                      # ⚡ شب و روز: صفر تأخیر


if __name__ == "__main__":
    asyncio.run(main())
