# ✨ Emoji Engine — ایموجی‌های پریمیوم تلگرام (tg-emoji) با fallback امن
#
# قانون Bot API: <tg-emoji emoji-id="ID">🍔</tg-emoji> فقط وقتی رندر می‌شود که
# مالکِ بات Premium باشد؛ برای بقیه، همان ایموجی معمولی داخل تگ نمایش داده می‌شود.
# اینجا هیچ ID جعلی‌ای نیست: نگاشت‌ها را ادمین با «مدیر ایموجی [کلید]» (ریپلای روی
# پیامی که یک ایموجی پریمیوم دارد) ثبت می‌کند و در kv ذخیره می‌شود.
# اگر تلگرام tg-emoji را رد کند، send-helper خودکار به ایموجی ساده برمی‌گردد.
import json
import re

import db

# ─── ایموجی‌های پایه‌ی بازی (کلید → ایموجی معمولی) ───
BASE = {
    "coin": "🪙", "army": "🪖", "war": "⚔️", "boss": "👑", "base": "🏠", "market": "🔄",
    "shop": "🛒", "pack": "📦", "pass": "💎", "inv": "🎒", "top": "🏆", "daily": "🎁",
    "milk": "🥛", "shift": "🏭", "patrol": "🚓", "help": "📖", "ally": "🤝", "cos": "🎨",
    "fire": "🔥", "star": "⭐️", "sparkle": "✨", "bolt": "⚡️", "shield": "🛡", "skull": "☠️",
    "up": "⬆️", "ok": "✅", "no": "❌", "wait": "⏳", "new": "🆕", "hot": "🌶",
    "meat": "🥩", "cheese": "🧀", "sauce": "🥫", "potato": "🥔", "metal": "⚙️", "crystal": "💎",
    "burger": "🍔", "fries": "🍟", "broccoli": "🥦", "meow": "😺", "pizza": "🍕",
    "candy": "🍭", "cheese_knight": "🧀", "taco_ranger": "🌮", "cupcake_bomber": "🧁",
    "pickle_general": "🥒", "lasagnazilla": "🦖", "squad": "🎖", "chart": "📊",
}

_TAG = re.compile(r'<tg-emoji emoji-id="\d+">(.*?)</tg-emoji>', re.S)
_cache: dict | None = None


def _ensure():
    db.db().ex("CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT)")


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    try:
        _ensure()
        r = db.db().one("SELECT v FROM kv WHERE k='premium_emoji'")
        _cache = json.loads(r["v"]) if r and r["v"] else {}
    except Exception:
        _cache = {}
    return _cache


def reset_cache():
    global _cache
    _cache = None


def enabled() -> bool:
    """سوییچ سراسری — فقط وقتی ادمین «مدیر ایموجی روشن» بزند."""
    try:
        _ensure()
        r = db.db().one("SELECT v FROM kv WHERE k='premium_emoji_on'")
        return bool(r and r["v"] == "1")
    except Exception:
        return False


def set_enabled(on: bool):
    _ensure()
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES('premium_emoji_on', ?)", ("1" if on else "0",))


def register(key: str, custom_id: str, fallback: str = "") -> None:
    """ثبت نگاشت کلید → شناسه‌ی ایموجی پریمیوم (فقط از پیام واقعی تلگرام)."""
    global _cache
    m = _load()
    m[key] = dict(id=str(custom_id), fb=fallback or BASE.get(key, "✨"))
    _ensure()
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES('premium_emoji', ?)",
               (json.dumps(m, ensure_ascii=False),))
    _cache = m


def unregister(key: str) -> bool:
    global _cache
    m = _load()
    if key not in m:
        return False
    m.pop(key)
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES('premium_emoji', ?)",
               (json.dumps(m, ensure_ascii=False),))
    _cache = m
    return True


def mapping() -> dict:
    return dict(_load())


def E(key: str) -> str:
    """ایموجی برای کلید: پریمیوم اگر ثبت و روشن باشد، وگرنه معمولی."""
    m = _load().get(key)
    if m and enabled():
        return f'<tg-emoji emoji-id="{m["id"]}">{m["fb"]}</tg-emoji>'
    return BASE.get(key, m["fb"] if m else "✨")


def strip(text: str) -> str:
    """حذف تگ‌های tg-emoji و نگه‌داشتن ایموجی ساده (fallback ارسال)."""
    return _TAG.sub(r"\1", text or "")


def has_premium(text: str) -> bool:
    return bool(text) and "<tg-emoji" in text


def from_message(msg) -> list:
    """استخراج (custom_emoji_id, emoji) از entities یک پیام — برای ثبت توسط ادمین."""
    out = []
    ents = list(getattr(msg, "entities", None) or []) + list(getattr(msg, "caption_entities", None) or [])
    text = msg.text or msg.caption or ""
    for e in ents:
        if getattr(e, "type", "") == "custom_emoji" and getattr(e, "custom_emoji_id", None):
            try:
                fb = text[e.offset:e.offset + e.length]
            except Exception:
                fb = ""
            out.append((str(e.custom_emoji_id), fb))
    return out


def status_text() -> str:
    m = _load()
    on = enabled()
    lines = [f"✨ <b>ایموجی پریمیوم</b> — {'🟢 روشن' if on else '⚪️ خاموش'}",
             f"📚 نگاشت‌های ثبت‌شده: <b>{len(m)}</b>", ""]
    for k, v in sorted(m.items())[:30]:
        lines.append(f"• <code>{k}</code> → {v['fb']} <code>{v['id']}</code>")
    lines += ["", "🛠 «مدیر ایموجی [کلید]» روی پیامِ حاویِ ایموجی پریمیوم",
              "🛠 «مدیر ایموجی روشن/خاموش» · «مدیر ایموجی حذف [کلید]»",
              "ℹ️ رندرِ پریمیوم فقط با مالکِ Premium؛ بقیه ایموجی ساده می‌بینند."]
    return "\n".join(lines)
