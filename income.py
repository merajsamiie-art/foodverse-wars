# 💰 Income — درآمدهای خردِ فعالیتی: کوچک، ساده، همه‌جا در دسترس
import random

import perf
import player
from config import PATROL_CD, SHIFT_CD, SHIFT_FC

SHIFT_FLAVOR = [
    "شیفت شب را تمام کردی. کانوایر هنوز چسبیده به دستت.",
    "۸ ساعت سرپایی. سرپرست اصلاً نگاهت نکرد — عادت کرده.",
    "جعبه‌ها را مرتب کردی و کسی نفهمید. سکه‌ها فهمیدند.",
    "یک شیفتِ ساده. در فوودورس، ساده یعنی زنده موندن.",
]
PATROL_FINDS = [
    "پشتِ انبار، چند سکه‌ی گم‌شده پیدا کردی.",
    "یک کارتن نیمه‌پر. صاحبش برنمی‌گردد.",
    "موشی جیب‌ها را خالی کرده بود؛ تهِ لانه‌اش را خالی کردی.",
    "لای لوله‌ها چیزی برق زد. مال تو شد.",
]
PATROL_NOTHING = [
    "دور محوطه گشتی؛ فقط سکوت. سکوت هم چیزیه.",
    "ردپای تازه بود، صاحبش نبود. بهتر همین‌طور بماند.",
]


def shift(user_id: int) -> tuple:
    """شیفت کارخانه — هر ۳ ساعت، درآمد کوچک + کمی منبع."""
    p = player.get(user_id)
    if not p:
        return False, "👤 اول «fw شروع» بزن."
    if player.on_cd(user_id, "shift"):
        return False, f"⏳ شیفت بعدی تا {player.cd_left(user_id, 'shift') // 60 + 1} دقیقه‌ی دیگر."
    fc = random.randint(*SHIFT_FC)
    res = random.choice(("meat", "cheese", "sauce", "potato"))
    amt = random.randint(20, 60)
    player.grant(user_id, fc=fc, **{res: amt})
    player.set_cd(user_id, "shift", SHIFT_CD)
    perf.STATS.commands += 1
    from registry import RES_META
    return True, (f"🏭 <b>شیفت تمام شد</b> — {random.choice(SHIFT_FLAVOR)}\n"
                  f"🪙 {fc} سکه + {RES_META[res]['emoji']} {RES_META[res]['name']} ×{amt}\n"
                  f"⏰ شیفت بعدی: ۳ ساعت دیگر.")


def patrol(user_id: int) -> tuple:
    """گشت محوطه — هر ۴۵ دقیقه، یافته‌های تصادفیِ کوچک."""
    p = player.get(user_id)
    if not p:
        return False, "👤 اول «fw شروع» بزن."
    if player.on_cd(user_id, "patrol"):
        return False, f"⏳ گشت بعدی تا {player.cd_left(user_id, 'patrol') // 60 + 1} دقیقه‌ی دیگر."
    player.set_cd(user_id, "patrol", PATROL_CD)
    roll = random.random()
    if roll < 0.55:
        fc = random.randint(40, 160)
        player.grant(user_id, fc=fc)
        msg = f"🪙 {fc} سکه"
    elif roll < 0.85:
        res = random.choice(("meat", "cheese", "sauce", "potato", "metal"))
        amt = random.randint(15, 45)
        player.grant(user_id, **{res: amt})
        from registry import RES_META
        msg = f"{RES_META[res]['emoji']} {RES_META[res]['name']} ×{amt}"
    elif roll < 0.95:
        xp = random.randint(20, 40)
        player.gain_xp(user_id, xp)
        msg = f"⭐ {xp} تجربه"
    else:
        player.gain_xp(user_id, 10)
        return True, (f"🌙 <b>گشت محوطه</b> — {random.choice(PATROL_NOTHING)}\n"
                      f"⭐ ۱۰ تجربه\n⏰ گشت بعدی: ۴۵ دقیقه‌ی دیگر.")
    return True, (f"🌙 <b>گشت محوطه</b> — {random.choice(PATROL_FINDS)}\n"
                  f"{msg}\n⏰ گشت بعدی: ۴۵ دقیقه‌ی دیگر.")


def text_help() -> str:
    return ("💰 <b>درآمدهای فعالیت</b>\n\n"
            "🏭 «fw شیفت» — هر ۳ ساعت، سکه و کمی منبع\n"
            "🌙 «fw گشت» — هر ۴۵ دقیقه، یافته‌های کوچکِ شانسی\n"
            "📅 «fw روزانه» — جایزه‌ی ورود + شش مأموریت روزانه\n\n"
            "این درآمدها کم هستند؛ کمک می‌کنند، پولدار نمی‌کنند.")
