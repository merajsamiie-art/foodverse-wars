# 📣 Announce — تغییرات نسخه‌ها + پست خودکار در کانال رسمی
#
# «مدیر اعلان» → آخرین نسخه را با عکس برند در CHANNEL_ID پست می‌کند.
# «مدیر اعلان [نسخه]» → نسخه‌ی مشخص.  «مدیر اعلان لیست» → فهرست نسخه‌ها.
# پست‌ها در kv ثبت می‌شوند تا یک نسخه دوبار ناخواسته ارسال نشود (ارسال مجدد با «!»).
import datetime

import db
import config as cfg

VERSION = "3.0"

CHANGELOG = {
    "3.0": dict(
        title="🪖 آپدیت ۳.۰ — ارتشِ گروهی، جوخه‌ها و چهره‌ی تازه",
        date="۱۴۰۵/۰۶/۱۴",
        items=[
            "🛒 <b>خرید گروهی ارتش</b>: تعداد را ×۱ / ×۱۰ / ×۵۰ / حداکثر انتخاب کن و هر شخصیت را با یک کلیک ده‌تا ده‌تا بخر — دیگر تکی‌تکی نه!",
            "🎖 <b>جوخه‌های آماده</b>: چهار ترکیبِ سنجیده‌ی ۱۰تایی (متعادل، تهاجمی، دژ، نخبه) با یک دکمه به خدمت درمی‌آیند.",
            "📊 <b>صفحه‌ی ارتش نو</b>: جان/حمله/دفاع/سرعت/کریت، نوارِ ترکیب ارتش و رنگِ کمیابی هر شخصیت.",
            "🍔 <b>منوی بازطراحی‌شده</b>: موجودی، قدرت و سطح بالای منو؛ خرید ارتش و جوخه در ردیف اول.",
            "✨ <b>ایموجی پریمیوم</b>: زیرساخت tg-emoji با fallback امن — اگر مالک Premium باشد، پیام‌ها با ایموجی‌های پریمیوم رندر می‌شوند.",
            "🧹 <b>پاکسازی دقیق‌تر</b>: دفتر تراکنش‌های قدیمی‌تر از ۱۴ روز واقعاً پاک می‌شود؛ خطای ارسالِ ایموجی هرگز پیامی را نمی‌سوزاند.",
            "🧪 <b>تست‌ها واقعاً اجرا می‌شوند</b>: ۱۲۰+ تست قبل از هر استقرار؛ استقرار فقط با تست سبز.",
            "🛡 <b>ضدتقلب خرید</b>: سقف هر خرید ۱۰۰ سرباز، پرداخت اتمیک، کشِ قدرت فوراً تازه می‌شود.",
        ],
        cta="🎮 همین حالا: «منو» ← «🛒 خرید ارتش ×۱۰» یا «🎖 جوخه‌های آماده»",
    ),
}

# نسخه‌هایی که خارج از بات (مستقیم با Bot API) در کانال پست شده‌اند → ضدتکرار
POSTED_MANUALLY = {"3.0": 128}

_TABLE = "CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT)"


def _ensure():
    db.db().ex(_TABLE)


def render(ver: str) -> str:
    c = CHANGELOG[ver]
    lines = [f"<b>{c['title']}</b>", f"🗓 {c['date']} · نسخه‌ی <b>{ver}</b>", ""]
    lines += [f"• {it}" for it in c["items"]]
    lines += ["", c["cta"], "", f"🤖 @{cfg.BOT_USERNAME} · 📢 {cfg.FORCE_CHANNEL}"]
    return "\n".join(lines)


def latest() -> str:
    return sorted(CHANGELOG, key=lambda v: tuple(int(x) for x in v.split(".")))[-1]


def list_text() -> str:
    _ensure()
    out = ["📣 <b>نسخه‌ها</b>"]
    for v in sorted(CHANGELOG, key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True):
        out.append(f"• {v} — {CHANGELOG[v]['title']} {'✅' if was_posted(v) else '⏳'}")
    out.append("\n«مدیر اعلان» = آخرین · «مدیر اعلان 3.0» · «مدیر اعلان 3.0!» = ارسال مجدد")
    return "\n".join(out)


def was_posted(ver: str) -> bool:
    if ver in POSTED_MANUALLY:
        return True
    _ensure()
    return bool(db.db().one("SELECT 1 FROM kv WHERE k=?", (f"announced:{ver}",)))


def mark_posted(ver: str, message_id: int):
    _ensure()
    db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?, ?)",
               (f"announced:{ver}", f"{message_id}@{datetime.datetime.now(cfg.TZ).isoformat()}"))


async def post_update(bot, which: str = "latest") -> tuple:
    """پست نسخه در کانال؛ برمی‌گرداند (ok, پیام برای ادمین)."""
    if which in ("لیست", "list"):
        return True, list_text()
    force = which.endswith("!")
    ver = which.rstrip("!").strip() or "latest"
    if ver == "latest":
        ver = latest()
    if ver not in CHANGELOG:
        return False, f"❓ نسخه‌ی «{ver}» تعریف نشده.\n" + list_text()
    if not cfg.CHANNEL_ID:
        return False, "❌ CHANNEL_ID تنظیم نیست."
    if was_posted(ver) and not force:
        return False, f"ℹ️ نسخه‌ی {ver} قبلاً پست شده. برای ارسال مجدد: «مدیر اعلان {ver}!»"
    text = render(ver)
    import media
    msg = None
    if len(text) <= 1000:                       # سقف کپشن تلگرام ۱۰۲۴
        try:
            msg = await media.send(bot, cfg.CHANNEL_ID, "brand_channel", caption=text)
        except Exception:
            msg = None
    else:
        try:
            await media.send(bot, cfg.CHANNEL_ID, "brand_channel", caption=f"<b>{CHANGELOG[ver]['title']}</b>")
        except Exception:
            pass
    if msg is None:
        try:
            msg = await bot.send_message(cfg.CHANNEL_ID, text)
        except Exception as e:
            return False, f"❌ ارسال به کانال شکست خورد: {e}"
    mark_posted(ver, msg.message_id)
    return True, f"📣 نسخه‌ی {ver} در کانال پست شد (پیام #{msg.message_id})."
