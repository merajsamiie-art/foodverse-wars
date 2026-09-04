# 🔗 Referral Engine — دعوت دوستان: پاداش کوچک، فقط برای بازیکن واقعی
# قواعد ضدتقلب:
#   ۱) خودارجاعی ممنوع؛ معرف باید حساب واقعی داشته باشد
#   ۲) هر حساب فقط یک‌بار و فقط در بدو ورود معرفی می‌شود (بدون روزانه و بدون پیشرفت)
#   ۳) دعوت فقط وقتی «تأیید» می‌شود که مهمان واقعاً بازی کند (اولین «روزانه»)
#   ۴) سقف پاداش روزانه برای هر معرف — مزرعه‌سازی حساب بی‌فایده است
import datetime

import config
import db
import player


def link_for(user_id: int) -> str:
    return f"https://t.me/{config.BOT_USERNAME}?start=ref-{user_id}"


def bind(new_uid: int, payload: str) -> str:
    """در /start پیوی با لینک دعوت — فقط حساب تازه و بدون معرف قبلی."""
    if not payload.startswith("ref-"):
        return ""
    try:
        ref = int(payload[4:])
    except ValueError:
        return ""
    if ref <= 0 or ref == new_uid:
        return ""
    me = player.get(new_uid)
    if not me or (me["ref_by"] or 0):
        return ""                       # حساب نیست یا قبلاً معرفی شده
    if not player.get(ref):
        return ""                       # معین معرف نیست
    # حساب باید واقعاً تازه باشد: هیچ روزانه‌ای نگرفته و پیشرفتی ندارد
    if db.db().one("SELECT 1 FROM daily WHERE user_id=?", (new_uid,)):
        return ""
    if (me["xp"] or 0) > 0 or (me["level"] or 1) > 1:
        return ""
    cur = db.db().ex("""UPDATE accounts SET ref_by=? WHERE user_id=?
                        AND (ref_by IS NULL OR ref_by=0)""", (ref, new_uid))
    if cur.rowcount != 1:
        return ""
    return (f"\n\n🎁 <b>با لینک دعوت اومدی!</b>\n"
            f"اولین «روزانه»‌ات را که بگیری، 🪙 {config.REF_NEWBIE_FC} فودکوین هدیه هم می‌گیری.")


def _day_start() -> float:
    d = datetime.datetime.now(config.TZ)
    return (d - datetime.timedelta(hours=d.hour, minutes=d.minute,
                                   seconds=d.second, microseconds=d.microsecond)).timestamp()


def on_daily(uid: int) -> tuple[str, int, str]:
    """اولین «روزانه»‌ی مهمان → تأیید دعوت + پاداش دو طرف.
    → (یادداشت برای مهمان، شناسه‌ی معرف برای پیام، متن پیام معرف)"""
    me = player.get(uid)
    if not me or not (me["ref_by"] or 0) or (me["ref_ok_at"] or 0):
        return "", 0, ""
    ref = me["ref_by"]
    if not player.get(ref):
        return "", 0, ""
    t = db.now()
    # سقف روزانه‌ی معرف (ضد مزرعه‌ی حساب)
    n_today = db.db().one(
        "SELECT COUNT(*) c FROM accounts WHERE ref_by=? AND ref_ok_at>=?",
        (ref, _day_start()))["c"]
    db.db().ex("UPDATE accounts SET ref_ok_at=? WHERE user_id=?", (t, uid))
    if n_today >= config.REF_DAILY_CAP:
        return "", 0, ""
    player.grant(uid, fc=config.REF_NEWBIE_FC)
    total = db.db().one(
        "SELECT COUNT(*) c FROM accounts WHERE ref_by=? AND ref_ok_at>0", (ref,))["c"]
    reward = config.REF_BASE_FC
    milestone = config.REF_MILESTONES.get(total, 0)
    reward += milestone
    player.grant(ref, fc=reward)
    note = (f"\n\n🎁 <b>هدیه‌ی دعوت:</b> +🪙 {config.REF_NEWBIE_FC} فودکوین — خوش اومدی!")
    pm = (f"🎉 <b>دعوتت بازی کرد!</b>\n"
          f"🪙 +{reward:,} فودکوین گرفتی"
          + (f" (جایزه‌ی {total}مین دعوت! 🏆)" if milestone else "")
          + f"\n👥 دعوت‌های تأییدشده: {total}")
    return note, ref, pm


def stats_text(user_id: int) -> str:
    total = db.db().one(
        "SELECT COUNT(*) c FROM accounts WHERE ref_by=? AND ref_ok_at>0", (user_id,))["c"]
    pending = db.db().one(
        "SELECT COUNT(*) c FROM accounts WHERE ref_by=? AND ref_ok_at=0", (user_id,))["c"]
    nxt = next((k for k in sorted(config.REF_MILESTONES) if k > total), None)
    nxt_txt = f"🏁 نفر بعدی: {nxt}مین → +{config.REF_MILESTONES[nxt]:,} فودکوین" if nxt else "👑 همه‌ی جوایز دعوت را گرفتی!"
    return (
        "🔗 <b>لینک دعوت اختصاصی‌ات</b>\n"
        f"<code>{link_for(user_id)}</code>\n\n"
        f"هر دوستی که با این لینک بیاید و واقعاً بازی کنی یعنی اولین «روزانه»‌اش را بگیرد:\n"
        f"🎁 تو: 🪙 {config.REF_BASE_FC} فودکوین — و او هم: 🪙 {config.REF_NEWBIE_FC} فودکوین هدیه\n\n"
        "🏆 <b>جشنواره‌ی دعوت:</b>\n"
        "۵مین نفر → +۵۰۰ | ۱۰مین → +۱,۵۰۰ | ۲۵مین → +۵,۰۰۰ | ۵۰مین → +۱۵,۰۰۰\n\n"
        f"👥 دعوت‌های تأییدشده: <b>{total}</b>"
        + (f" | ⏳ در انتظار بازی: {pending}" if pending else "") +
        f"\n{nxt_txt}\n\n"
        "🛡 فقط بازیکن واقعی حساب می‌شود؛ حساب تازه‌ساخت بدون بازی، چیزی نمی‌دهد."
    )
