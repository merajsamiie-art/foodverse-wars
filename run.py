# ▶️ FOODVERSE WARS — اجرای اصلی + میدل‌ورهای پرفورمنس
import asyncio
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
        await dp.start_polling(bot)
    except TelegramConflictError:
        log.error("⛔ getUpdates conflict — یک نمونه‌ی دیگر بات را اجرا کرده. خارج می‌شوم تا GHA ری‌استارت کند.")
        raise SystemExit(2)
    finally:
        db.db().close()


if __name__ == "__main__":
    asyncio.run(main())
