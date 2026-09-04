# 📡 Event Engine — باس، بازار پویا، فروشگاه چرخشی، امبیانس
import asyncio
import random
import time as _t

import db
import market
import shop


AMBIENCE = [
    "🏭 کانوایر کارخانه نصفه‌شب هم روشن است. هیچ‌کس شیفت ندارد. هیچ‌کس لازم نیست.",
    "😼 صدای پنجه روی فلز. شاید فقط موش باشد. شاید موش‌ها لباس پوشیده باشند.",
    "🥦 بروکلی‌ها امشب آرام‌اند. این بدترین خبر ممکن است.",
    "🪙 خزانه‌ی کارخانه باز شد و بسته شد. کسی نبود. حساب‌ها خودشان می‌شوند.",
    "🦖 لرزه‌ای از طبقه‌ی ۴ آمد. لازاگنی‌زیلا فقط یک افسانه است. قطعاً.",
]


class EventEngine:
    """هر ساعت یک دور بی‌صدا؛ فقط وقتی ارزش گفتن هست حرف می‌زند."""

    def __init__(self, bot, interval=3600):
        self.bot = bot
        self.interval = interval
        self._task = None
        self._last_amb: dict[int, float] = {}

    async def _hourly(self):
        # 📈 بازار پویا: بازگشت آرام قیمت‌ها به پایه + چرخش فروشگاه
        try:
            market.decay_prices()
            shop.rotate_if_needed()
        except Exception:
            pass
        rows = db.db().q("SELECT chat_id FROM worlds WHERE started=1")
        for r in rows:
            cid = r["chat_id"]
            try:
                from boss import spawn_tick
                msg = spawn_tick(cid)
                if msg and self.bot:
                    await self.bot.send_message(cid, msg)
                    continue
                t = _t.time()
                if t - self._last_amb.get(cid, 0) > 6 * 3600 and random.random() < 0.3:
                    self._last_amb[cid] = t
                    if self.bot:
                        await self.bot.send_message(cid, random.choice(AMBIENCE))
            except Exception:
                continue   # هیچ چتی نباید اسکجولر را بکشد

    async def _loop(self):
        while True:
            try:
                await self._hourly()
            except Exception:
                pass
            await asyncio.sleep(self.interval)

    def start(self):
        if self._task is None:
            self._task = asyncio.get_event_loop().create_task(self._loop())
