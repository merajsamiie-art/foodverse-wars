# 🖼 Profile Card — کارت پروفایل تصویری (Pillow + فارسی RTL) با کش
import hashlib
import os

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

from registry import COSMETICS, title_of

FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
CACHE_DIR = os.environ.get("FW_CARD_CACHE", "/tmp/fw_cards")
W, H = 800, 800

# پالت فوودورس
BG = (24, 20, 28)
CARD = (34, 28, 40)
ACCENT = (255, 92, 92)      # قرمز برگری
GOLD = (255, 200, 60)
TXT = (245, 240, 235)
SUB = (168, 158, 175)


def _fa(text: str) -> str:
    """فارسی درست: reshaper + bidi."""
    return get_display(arabic_reshaper.reshape(str(text)))


def _font(size: int, bold=True):
    f = "Vazirmatn-Bold.ttf" if bold else "Vazirmatn-Regular.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, f), size)


def _frame_color(cid):
    c = COSMETICS.get(cid)
    if not c:
        return SUB
    return {"common": (160, 160, 160), "rare": (80, 150, 255), "epic": (190, 100, 255),
            "legendary": (255, 160, 40), "mythic": (255, 60, 90)}.get(c["rarity"], SUB)


def generate(p: dict) -> str:
    """کارت ۱:۱ — مسیر فایل کش‌شده را برمی‌گرداند."""
    sig = hashlib.sha1(f"{p['user_id']}|{p['level']}|{int(p['fc'])}|{p['name']}|"
                       f"{p['avatar']}|{p['cos_frame']}|{p['cos_title']}|{p['wins']}".encode()).hexdigest()[:16]
    path = os.path.join(CACHE_DIR, f"card_{p['user_id']}_{sig}.png")
    if os.path.exists(path):
        return path   # 🧠 کش: فقط وقتی چیزی تغییر کند دوباره ساخته می‌شود
    os.makedirs(CACHE_DIR, exist_ok=True)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # قاب بیرونی (رنگ فریم کازمتیک)
    fc = _frame_color(p["cos_frame"])
    d.rounded_rectangle([16, 16, W - 16, H - 16], radius=36, outline=fc, width=8)
    d.rounded_rectangle([32, 32, W - 32, H - 32], radius=28, fill=CARD)

    # هدر برند
    d.text((W // 2, 74), _fa("🍔 فوودورس ورز"), font=_font(44), fill=ACCENT, anchor="mm")
    d.text((W // 2, 122), "FOODVERSE WARS", font=_font(26, False), fill=SUB, anchor="mm")
    d.line([80, 150, W - 80, 150], fill=fc, width=2)

    # آواتار بزرگ
    d.text((W // 2, 260), p["avatar"], font=_font(150), fill=TXT, anchor="mm")

    # نام + عنوان
    title = p["cos_title"] and COSMETICS.get(p["cos_title"], {}).get("name") or title_of(p["level"])
    d.text((W // 2, 392), _fa(p["name"]), font=_font(52), fill=TXT, anchor="mm")
    d.text((W // 2, 446), _fa(title), font=_font(30, False), fill=GOLD, anchor="mm")

    # آمار
    y = 520
    d.text((W // 2, y), _fa(f"سطح {p['level']}   |   🏆 برد {p['wins']}   |   💀 باخت {p['losses']}"),
           font=_font(30), fill=TXT, anchor="mm")
    d.text((W // 2, y + 52), _fa(f"🪙 {int(p['fc']):,} فودکوین"), font=_font(36), fill=GOLD, anchor="mm")

    # نوار XP
    from config import xp_need
    need = xp_need(p["level"])
    pct = max(0.0, min(1.0, p["xp"] / need)) if need else 0
    bx1, bx2, by = 140, W - 140, y + 110
    d.rounded_rectangle([bx1, by, bx2, by + 22], radius=11, fill=(50, 44, 58))
    d.rounded_rectangle([bx1, by, bx1 + int((bx2 - bx1) * pct), by + 22], radius=11, fill=ACCENT)
    d.text((W // 2, by + 52), _fa(f"XP {int(p['xp'])} / {need}"), font=_font(24, False),
           fill=SUB, anchor="mm")

    # کپی‌رایت کوچک
    d.text((W // 2, H - 66), "the kitchen never cools", font=_font(22, False),
           fill=SUB, anchor="mm")

    img.save(path, "PNG")
    # پاکسازی کش قدیمی همان کاربر
    uid_prefix = f"card_{p['user_id']}_"
    for f in os.listdir(CACHE_DIR):
        if f.startswith(uid_prefix) and f != os.path.basename(path):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except OSError:
                pass
    return path
