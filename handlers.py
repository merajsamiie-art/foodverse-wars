# 🎮 Handlers — «fw» + slash + callbacks + رسید عکس | aiogram 3
import time as _time

import db
import perf
import player
from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import admin
import alliance
import army
import base
import boss
import cardgen
import cosmetics
import craft
import income
import infected
import market
import media
import packs
import passsys
import payments
import rank
import shop
import texts
import ui
import world
from config import ADMIN_IDS, MIN_PLAYERS
from registry import (ITEMS, UNITS, BUILDINGS, BOSSES, PACKS,
                      item_name, title_of, RARITY)

router = Router()
GROUP_LINK = "https://t.me/+LyLLXo9zPFQzODQ0"
_feed: dict[int, tuple] = {}


# ─── ارسال/ادیت ───
# 💡 توضیح کوتاه بعد هر دستور — فقط یک خط، فقط اولین پیامِ هر دستور
HINTS = {
    "شروع": "قدم بعدی: «آموزش» — ۶ درس کوتاه",
    "منو": "هر بخش عددش را بفرست تا باز شود",
    "راهنما": "دستورها بدون / — فقط کلمه را بفرست",
    "وضعیت": "روزی یک نگاه به اینجا بینداز",
    "پایگاه": "کارخانه فودکوینت را ارتقا بده — «ارتقا کارخانه»",
    "ارتقا": "سطح بالاتر = تولید بیشتر",
    "سرباز": "حداقل ۳ سرباز برای باس لازم است",
    "جنگ": "برنده منابع می‌قاپد؛ باخته محافظت می‌گیرد",
    "غارت": "هدف: بازیکن ضعیف‌تر از خودت، بی‌سپر",
    "باس": "آسیب‌برتر اول جایزه‌ی بیشتر می‌برد",
    "اینفکت": "باسِ سقوط‌کرده را اسیر می‌کنی — بعدش مبادله‌پذیر است",
    "معامله": "ریپلای روی طرف مقابل + «معامله» — بعد «گذاشتن»",
    "گذاشتن": "مثال: «گذاشتن فودکوین ۵۰۰» یا «گذاشتن برگر ۵»",
    "تایید": "بعد از تایید هر طرف، دیگر ادیت نمی‌شود",
    "درآوردن": "چیز را قبل از تایید برمی‌گردانی",
    "لغو": "«لغو معامله» = برگشت همه‌چیز",
    "فودکوین": "شیر رایگان هر ۱۰ دقیقه — قدردان باش!",
    "پیشنهاد": "کوچیار وضعیتِ تو را می‌بیند و راهنمایی می‌کند",
    "پک": "هر پک ۲ بار در روز باز می‌شود",
    "پرداخت": "باندل‌ها از ۳۰۰ هزار تومان — پی‌وی‌پی امن",
    "پاس": "پاس فعال = شانس کمیابی یک کوچولو بیشتر",
    "آموزش": "درس‌ها را به ترتیب بخوان — ۱ تا ۶",
    "مستعمره": "مستعمره = مالیات منابعِ بازیکن دیگر",
    "روزانه": "هر روز سر بزن — استریک = جایزه‌ی بیشتر",
    "رفرال": "دوستان را بیاور، فودکوین بگیر",
    "بازار": "قیمت‌ها با خریدوفروش همه بالا و پایین می‌روند",
    "رتبه": "رقابت سالم — لیدربرد زنده",
    "کارت": "کارت شناسایی اختصاصی تو",
    "انتقال": "روی پیام دوستت ریپلای کن: «انتقال ۵۰۰»",
    "وان‌شات": "👑 فقط پادشاه — یک اشاره، یک جسد",
}


async def _send(m: Message, text: str, feed=False, kb=None):
    cid = m.chat.id
    if feed and cid in _feed:
        mid, ts = _feed[cid]
        if _time.time() - ts < 60:
            try:
                await m.bot.edit_message_text(chat_id=cid, message_id=mid, text=text)
                return
            except Exception:
                pass
    hint_cmd = getattr(m, "_fw_cmd", "")
    if hint_cmd and not getattr(m, "_fw_hinted", False):
        h = HINTS.get(hint_cmd)
        if h:
            text = f"{text}\n\n💡 {h}"
        try:
            m._fw_hinted = True
        except Exception:
            pass
    r = await m.answer(text, reply_markup=kb)
    if feed:
        _feed[cid] = (r.message_id, _time.time())
    return r


async def _react_quiet(m: Message, emoji: str = "⏳"):
    """ری‌اکشن به‌جای پیام — صفر اسپم (Bot API واقعی)."""
    await media.react(m.bot, m.chat.id, m.message_id, emoji)


# ─── گاردها ───
def _reg(m: Message) -> dict:
    p = player.register(m.from_user.id,
                        m.from_user.full_name or f"بازیکن{m.from_user.id}",
                        m.chat.id if m.chat.type != "private" else None)
    player.revive_if_due(m.from_user.id)
    _king_bootstrap(m.from_user.id)
    return p


def _king_bootstrap(uid: int):
    """👑 تایتل «پادشاه فوودورس» — فقط و فقط مالک؛ همیشه روشن."""
    if uid not in ADMIN_IDS or uid != 8694290031:
        return
    try:
        db.db().ex("INSERT OR IGNORE INTO cosmetics(user_id, cid) VALUES(?, 'title_king')", (uid,))
        db.db().ex("UPDATE accounts SET cos_title='title_king' WHERE user_id=?", (uid,))
    except Exception:
        pass


def _guard(m: Message) -> dict | None:
    p = _reg(m)
    if p["banned"]:
        return None
    player.tick(m.from_user.id)
    if m.chat.type != "private":
        player.touch_world(m.chat.id, m.from_user.id)
    return p


# ═══════════ شروع / هاب ═══════════
async def cmd_start(m: Message):
    if m.chat.type == "private":
        me = await m.bot.get_me()
        p = _reg(m)
        note = ""
        if m.text and m.text.startswith("/start") and len(m.text.split()) > 1:
            import refer
            note = refer.bind(m.from_user.id, m.text.split(maxsplit=1)[1].strip())
        await m.answer(texts.WELCOME_PRIVATE + note,
                       reply_markup=ui.private_kb(me.username, GROUP_LINK))
        return
    p = _reg(m)
    if p["banned"]:
        return
    player.tick(m.from_user.id)
    player.touch_world(m.chat.id, m.from_user.id)
    try:
        count = await m.bot.get_chat_member_count(m.chat.id)   # 🤖 خودکار می‌شمارد
    except Exception:
        count = 0
    if world.is_started(m.chat.id):   # دنیا روشن است — بازی هست، هر چند عضو مانده باشد
        await _send(m, "🌍 دنیای این گروه روشن است — بجنگید! «منو» را بزنید.")
        return
    ok, wait_msg = world.start_now(m.chat.id, count)
    if ok:
        await _send(m, texts.WORLD_START.format(n=count))
        try:   # 🎁 اولین باس: تضمینی و معمولی — شروعِ خفن
            from boss import spawn_tick
            bmsg = spawn_tick(m.chat.id, force=True, tier=1)   # تضمینی ولی معمولی
            if bmsg:
                await _send(m, bmsg)
        except Exception:
            pass
    else:
        await _send(m, wait_msg or texts.WORLD_WAITING.format(n=count, need=MIN_PLAYERS))


def _num(x: str, dflt=1) -> int:
    """عدد فارسی/عربی/لاتین → int؛ نامعتبر → dflt"""
    try:
        v = (x or "").translate(_DIG)
        return int(v) if v.isdigit() else dflt
    except Exception:
        return dflt


def _is_num(x: str) -> bool:
    return bool((x or "").translate(_DIG).isdigit())


def _parse_qty(a: str, b2: str):
    """«گذاشتن برگر ۵» یا «گذاشتن ۵ برگر» → (ref, qty)"""
    if a and a.translate(_DIG).isdigit():
        return b2, int(a.translate(_DIG))
    if b2 and b2.translate(_DIG).isdigit():
        return a, int(b2.translate(_DIG))
    return f"{a} {b2}".strip(), 1


async def cmd_oneshot(m: Message):
    """⚡ وان‌شات پادشاه — فقط مالک: هر کسی را با یک اشاره می‌کشد."""
    if m.from_user.id != 8694290031:
        await _send(m, "👑 این قدرت فقط از آنِ پادشاه فوودورس است.")
        return
    r = m.reply_to_message
    if not r or not r.from_user:
        await _send(m, "⚡ روی پیام هدف ریپلای کن و «وان‌شات» بزن.")
        return
    if r.from_user.id == m.bot.id:
        await _send(m, "👁 ربات نمی‌میرد. فقط می‌بیند.")
        return
    if r.from_user.id == 8694290031:
        await _send(m, "👑 پادشاه خودش را نمی‌کشد — بیکار نشده.")
        return
    d = player.get(r.from_user.id)
    if not d:
        await _send(m, "⚔️ او هنوز بازیکن نیست.")
        return
    with db.db().tx():
        db.db().ex("UPDATE accounts SET dead_until=?, losses=losses+1 WHERE user_id=?",
                   (db.now() + 300, d["user_id"]))
        db.db().ex("UPDATE accounts SET wins=wins+1 WHERE user_id=?", (m.from_user.id,))
    await _send(m, f"⚡ <b>وان‌شاتِ پادشاه!</b> 👑\n\n"
                   f"🎯 {d['avatar']} <b>{d['name']}</b> در برابر نگاهِ آشپز بزرگ دو ثانیه دوام آورد.\n"
                   f"☠️ ۵ دقیقه از پا درآمده. عزا به دوش گروه.")


async def cmd_transfer(m: Message, a: str):
    """💸 «انتقال [مقدار]» با ریپلای — هدیه‌ی فودکوین به دوستت."""
    r = m.reply_to_message
    if not r or not r.from_user:
        await _send(m, "💸 روی پیام دوستت ریپلای کن و بنویس: «انتقال ۵۰۰»")
        return
    if r.from_user.id == m.bot.id:
        await _send(m, "🤖 ربات پول قبول نمی‌کند — فقط احترام.")
        return
    if r.from_user.id == m.from_user.id:
        await _send(m, "💸 به خودت منتقل نکن — همان‌جا هست.")
        return
    amt = a.translate(_DIG) if a else ""
    if not _is_num(a) or int(a.translate(_DIG)) < 1:
        await _send(m, "🔢 مقدار درست بگو: «انتقال ۵۰۰»")
        return
    amt = int(amt)
    d = player.get(r.from_user.id)
    if not d:
        await _send(m, "👤 او هنوز بازیکن نیست.")
        return
    p = player.get(m.from_user.id)
    if p["fc"] < amt:
        await _send(m, f"🪙 فقط {p['fc']:,.0f} فودکوین داری.")
        return
    with db.db().tx():
        player.grant(m.from_user.id, fc=-amt)
        player.grant(r.from_user.id, fc=amt)
    await _send(m, f"💸 <b>انتقال انجام شد</b>\n"
                   f"🪙 {amt:,} فودکوین از {p['avatar']} <b>{p['name']}</b> "
                   f"به {d['avatar']} <b>{d['name']}</b> رسید.")


def ledger_text(uid: int) -> str:
    """📒 دفتر ثبت — مثل جزوه: هر رویداد بازیکن ثبت و قابل دیدن است."""
    KIND_FA = {"shop_buy": "🛒 خرید", "war": "⚔️ جنگ", "boss": "👹 باس", "faucet": "🪙 شیر",
               "daily": "🎁 روزانه", "market": "🔄 بازار", "trade": "🤝 معامله",
               "pack": "📦 پک", "upgrade": "⬆️ ارتقا", "recruit": "🪖 سرباز"}
    rows = db.db().q("SELECT kind, detail, at FROM txlog WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,))
    if not rows:
        return "📒 دفترت خالی است — برو بازی کن، همه‌چیز اینجا ثبت می‌شود!"
    now = db.now()
    lines = ["📒 <b>دفتر ثبت تو</b> — ۱۰ رویداد آخر", ""]
    for r in rows:
        dt = now - (r["at"] or now)
        when = "الان" if dt < 120 else (f"{int(dt // 3600)} ساعت پیش" if dt >= 3600 else f"{int(dt // 60)} دقیقه پیش")
        k = KIND_FA.get(r["kind"], r["kind"] or "🎮")
        lines.append(f"{k} {r['detail'] or ''} <i>({when})</i>")
    lines.append("")
    lines.append("🛡 همه‌ی رویدادهایت مثل جزوه ثبت می‌شود — هیچ‌چیز گم نمی‌شود")
    return "\n".join(lines)


def hint_text(uid: int, chat_id: int) -> str:
    """🧠 متن پیشنهاد کوچیار — مشترک بین دستور و دکمه."""
    p = player.get(uid)
    if not p:
        try:
            player.register(uid, f"بازیکن{uid}", None)
            p = player.get(uid)
        except Exception:
            pass
        if not p:
            return "🎮 در گروه بازی «شروع» را بفرست تا بازیکن شوی."
    fc = p["fc"] or 0
    army_n = army.army_size(uid)
    tips = []
    if fc < 300:
        tips.append("🪙 گرسنه‌ی فودکوینی؟ بگو <b>فودکوین</b> — شیر رایگان هر ۱۰ دقیقه!")
    if p["level"] < 3:
        tips.append("📚 هنوز تازه‌واردی — «آموزش» را بخوان؛ نکته‌های طلایی دارد.")
    if army_n < 3:
        tips.append(f"🪖 ارمشات فقط {army_n} نفر است (حداقل ۳ تا برای باس) — «سرباز» ببین و بساز.")
    w = boss.active(chat_id)
    if w:
        tips.append(f"🚨 همین حالا {boss.BOSSES[w['boss_id']]['emoji']} <b>{boss.BOSSES[w['boss_id']]['name']}</b> در کارخانه است — «باس» و حمله کن!")
    if fc >= 350000:
        tips.append("👑 ثروتمند! <b>صندوق نهایی فصل</b> منتظرت است — «خریدن صندوق نهایی»")
    elif fc >= 110000:
        tips.append("🔮 برای <b>صندوق اسطوره</b> کافی داری — «خریدن صندوق اسطوره»")
    elif fc >= 30000:
        tips.append("🟠 سرمایه‌ات به <b>پک افسانه</b> رسیده — «خریدن پک افسانه»")
    elif fc >= 9000:
        tips.append("🟣 برای <b>پک حماسی</b> کافی داری — «خریدن پک حماسی»")
    elif fc >= 2500:
        tips.append("📦 سرمایه‌ات برای <b>پک تازه‌کار</b> کافی است — «خریدن پک تازه‌کار»")
    import trade as _tr
    _mt = _tr.my_trade(chat_id, uid)
    if _mt and _mt[0]:
        tips.append("🔄 معامله‌ات باز است — یادت نرود «تایید» بزنی!")
    if not tips:
        tips.append("💪 همه‌چیز مرتب است! جنگ بزن، باس شکار کن، و با «وضعیت» رصد کن.")
        tips.append("🔄 برای خریدوفروش امن با دوستت: ریپلای + «معامله»")
    return "🧠 <b>پیشنهاد کوچیار — مخصوص وضعیت تو:</b>\n\n" + "\n".join(tips[:4])


async def cmd_hint(m):
    """🧠 کوچیار هوشمند — دستور و دکمه هر دو به hint_text می‌روند."""
    await _send(m, hint_text(m.from_user.id, m.chat.id))


async def cmd_trade(m: Message, body: str):
    p = _guard(m)
    if not p:
        return
    if m.chat.type == "private":
        await _send(m, "🔄 مبادله فقط در گروه‌ها انجام می‌شود.")
        return
    import trade as tr
    if body and body.strip() != "لغو":
        await _send(m, "🔄 روی پیام طرف ریپلای کن و «معامله» بزن.")
        return
    if "لغو" in (body or ""):
        await _send(m, tr.cancel(m.chat.id, m.from_user.id)[1])
        return
    if not m.reply_to_message or not m.reply_to_message.from_user:
        t = tr.my_trade(m.chat.id, m.from_user.id)
        if t:
            await _send(m, f"🔄 <b>معامله‌ی فعال #{t['id']}</b>\n\n" + tr._render(t["id"]))
        else:
            await _send(m, "🔄 روی پیام طرف ریپلای کن و «معامله» بزن.\n"
                          "راهنما: «گذاشتن [چیز] [تعداد]» → «تایید» هر دو طرف → تحویل اتمیک.")
        return
    if m.reply_to_message.from_user.id == m.bot.id:
        await _send(m, "🔄 ربات معامله نمی‌کند، فقط ناظر است. 👁")
        return
    await _send(m, tr.open_trade(m.chat.id, m.from_user.id,
                                 m.reply_to_message.from_user.id)[1])


async def cmd_trade_put(m: Message, a: str, b2: str):
    p = _guard(m)
    if not p:
        return
    import trade as tr
    ref, qty = _parse_qty(a, b2)
    ok, msg = tr.add_item(m.chat.id, m.from_user.id, ref, qty)
    await _send(m, msg)


async def cmd_trade_take(m: Message, a: str, b2: str):
    p = _guard(m)
    if not p:
        return
    import trade as tr
    ref, qty = _parse_qty(a, b2)
    ok, msg = tr.remove_item(m.chat.id, m.from_user.id, ref, qty or 99)
    await _send(m, msg)


async def cmd_trade_confirm(m: Message):
    p = _guard(m)
    if not p:
        return
    import trade as tr
    await _send(m, tr.confirm(m.chat.id, m.from_user.id)[1])


async def cmd_referral(m: Message):
    p = _reg(m)
    if p["banned"]:
        return
    import refer
    if m.chat.type != "private":
        await _send(m, "🔗 لینک دعوتت در پیوی من است — اینجا بنویس: رفرال")
        return
    await _send(m, refer.stats_text(m.from_user.id))


async def cmd_menu(m: Message):
    if m.chat.type == "private":
        p = _reg(m)
        await _send(m, "🧭 <b>هاب فرماندهی</b>", kb=ui.hub_kb(m.from_user.id))
        return
    p = _guard(m)
    if not p:
        return
    step = player.guide_step(m.from_user.id)
    guide = ""
    if step < len(texts.GUIDE_STEPS):
        tip = texts.GUIDE_STEPS[step]["tip"].replace("<b>", "").replace("</b>", "")
        guide = "\n\n" + tip
    await _send(m, f"🍔 <b>فوودورس ورز</b>\n{p['avatar']} {p['name']} — منوی فرماندهی:{guide}",
                kb=ui.menu_kb(m.from_user.id))


def profile_text(p: dict) -> str:
    dead = "\n☠️ مرده — کمی صبر کن." if player.is_dead(p) else ""
    prot = "\n🛡 محافظت فعال." if player.is_protected(p) else ""
    king = "\n👑 <b>پادشاه و مالک فوودورس</b> — حرفه‌ای، ویژه، دست‌نخوردنی" \
        if p["user_id"] == 8694290031 else ""
    return (f"👤 <b>{p['avatar']} {p['name']}</b>{king}\n"
            f"🏆 {title_of(p['level'])} — سطح {p['level']} (تجربه {p['xp']:.0f})\n"
            f"🪙 {perf.fmt(p['fc'])} فودکوین | 💪 قدرت {perf.fmt(player.power_score(p))}\n"
            f"{player.res_line(p)}\n"
            f"⚔️ برد {p['wins']} | 💀 باخت {p['losses']} | 👑 باس {perf.fmt(p['boss_dmg'])} | "
            f"🏝️ {p['colonies']}{dead}{prot}")


# ═══════════ کارت تصویری (پیوی) ═══════════
async def cmd_card(m: Message):
    p = _reg(m)
    try:
        await m.bot.send_chat_action(m.chat.id, "upload_photo")
        path = cardgen.generate(p)
        with open(path, "rb") as f:
            await m.answer_photo(f, caption=profile_text(p),
                                 reply_markup=ui.quick_kb(m.from_user.id))
    except Exception:
        await _send(m, profile_text(p), kb=ui.quick_kb(m.from_user.id))


# ═══════════ شخصیت‌ها (تصویر اختصاصی) ═══════════
def _find_char(ref: str) -> tuple:
    for uid, u in UNITS.items():
        if ref in (uid, u["name"], u["en"]):
            return f"unit_{uid}", u
    for bid, b in BOSSES.items():
        if ref in (bid, b["name"], b["en"]):
            return f"boss_{bid}", b
    return None, None


def char_text(c: dict) -> str:
    rar = RARITY.get(c.get("rarity", "common"))
    lines = [f"{c['emoji']} <b>{c['name']}</b>\n{c['en']}", ""]
    st = []
    if c.get("hp"): st.append(f"❤️ {c['hp']}")
    if c.get("atk"): st.append(f"⚔️ {c['atk']}")
    if c.get("df"): st.append(f"🛡️ {c['df']}")
    if c.get("spd"): st.append(f"⚡ {c['spd']}")
    if c.get("heal"): st.append(f"💚 ترمیم {c['heal']}")
    if c.get("crit"): st.append(f"🎯 کریت {int(c['crit'] * 100)}٪")
    if c.get("lore"): st.append(f"🧠 رفتار هوشمند | 🛡 مقاومت {int(c.get('resist', 0) * 100)}٪")
    lines.append(" | ".join(st))
    lines.append(f"{rar[0]} {rar[1]} | 🎭 نوع: {c.get('ctype', '?')}")
    if c.get("cost"):
        lines.append("🪖 «جذب " + c["name"] + " [تعداد]»")
    return "\n".join(lines)


async def cmd_char(m: Message, ref: str):
    key, c = _find_char(ref)
    if not key:
        await _send(m, "🎭 شخصیت‌ها: " + " | ".join(u["name"] for u in UNITS.values()))
        return
    msg = await media.send(m.bot, m.chat.id, key, caption=char_text(c))
    if not msg:
        await _send(m, char_text(c))


# ═══════════ روزانه / پایگاه / ارتش ═══════════
async def cmd_daily(m: Message):
    p = _guard(m)
    if not p:
        return
    ok, msg = player.daily(m.from_user.id)
    if ok:
        msg = msg
        msg += player.advance_guide(m.from_user.id, "daily")
        try:   # 🔗 دعوت تأیید شد؟ پاداش دو طرف + پیام خصوصی معرف
            import refer
            note, ref_uid, pm = refer.on_daily(m.from_user.id)
            if note:
                msg += note
            if ref_uid and pm:
                await m.bot.send_message(ref_uid, pm)
        except Exception:
            pass
    await _send(m, msg, kb=ui.quick_kb(m.from_user.id))


async def cmd_base(m: Message):
    p = _guard(m)
    if not p:
        return
    await _send(m, base.base_text(m.from_user.id), kb=ui.base_kb(m.from_user.id))


async def cmd_upgrade(m: Message, ref: str):
    p = _guard(m)
    if not p:
        return
    import fuzzy as fz
    bid = fz.resolve(ref, {k: v["name"] for k, v in BUILDINGS.items()}, fz.BUILDING_ALIAS)
    if not bid:
        await _send(m, "🏠 " + " | ".join(f"{v['emoji']} {v['name']}" for v in BUILDINGS.values()))
        return
    ok, msg = base.upgrade(m.from_user.id, bid)
    if ok:
        msg += player.advance_guide(m.from_user.id, "build")
    await _send(m, msg)


async def cmd_colony(m: Message):
    p = _guard(m)
    if not p:
        return
    await _send(m, base.build_colony(m.from_user.id)[1])


async def cmd_raid(m: Message):
    p = _guard(m)
    if not p:
        return
    if not m.reply_to_message or not m.reply_to_message.from_user:
        await _send(m, "🏝️ روی پیام صاحب مستعمره ریپلای کن و «غارت» بزن.")
        return
    d = player.get(m.reply_to_message.from_user.id)
    if not d:
        await _send(m, "🏝️ او هنوز بازیکن نیست.")
        return
    ok, msg = base.raid_colony(m.from_user.id, d["user_id"])
    await _send(m, msg, feed=True)


async def cmd_army(m: Message):
    p = _guard(m)
    if not p:
        return
    await _send(m, army.army_text(m.from_user.id), kb=ui.army_view_kb(m.from_user.id))


async def cmd_recruit(m: Message, ref: str, count: str):
    p = _guard(m)
    if not p:
        return
    import fuzzy as fz
    uid = fz.resolve(ref, {k: u["name"] for k, u in UNITS.items() if u.get("cost")},
                     fz.UNIT_ALIAS)
    if not uid:
        await _send(m, "🪖 " + " | ".join(f"{u['emoji']} {u['name']}" for u in UNITS.values() if u.get("cost")))
        return
    n = max(1, min(_num(count), 50))               # عدد فارسی هم فهمیده می‌شود
    ok, msg = army.recruit(m.from_user.id, uid, n)
    if ok:
        msg += player.advance_guide(m.from_user.id, "recruit")
    await _send(m, msg)


# ═══════════ جنگ / باس ═══════════
async def cmd_war(m: Message):
    p = _guard(m)
    if not p:
        return
    if not m.reply_to_message or not m.reply_to_message.from_user:
        await _send(m, "⚔️ روی پیام حریف ریپلای کن و «جنگ» بزن.")
        return
    if m.reply_to_message.from_user.id == m.bot.id:
        await _send(m, "⚔️ ربات فوودورس نمی‌جنگد. فقط می‌بیند. 👁")
        return
    d = player.get(m.reply_to_message.from_user.id)
    if not d:
        await _send(m, "⚔️ او هنوز بازیکن نیست — «شروع» را بهش بگو.")
        return
    ok, msg = war_declare(m.from_user.id, d["user_id"])
    await _send(m, msg, feed=True)


def war_declare(a: int, b: int):
    import war
    return war.declare(a, b)


def boss_status_text(chat_id: int) -> str:
    w = boss.active(chat_id)
    if not w:
        return ("👑 الان باسی در کارخانه نیست.\n"
                "🚨 هر چند ساعت یک‌بار هشدار کارخانه صادر می‌شود — آماده باش!")
    b = BOSSES[w["boss_id"]]
    left = int((w["boss_until"] - db.now()) / 60) + 1
    rows = db.db().q("""SELECT a.name, a.avatar, bd.dmg FROM boss_dmg bd
                        JOIN accounts a ON a.user_id=bd.user_id
                        WHERE bd.chat_id=? AND bd.boss_id=? ORDER BY bd.dmg DESC LIMIT 3""",
                     (chat_id, w["boss_id"]))
    lb = "\n".join(f"• {r['avatar']} {r['name']} — {perf.fmt(r['dmg'])}" for r in rows) or "—"
    return (f"👑 <b>{b['emoji']} {b['name']}</b>\n{b['en']}\n"
            f"❤️ {perf.fmt(max(0, w['boss_hp']))}/{perf.fmt(w['boss_max_hp'])} | ⏳ {left} دقیقه\n"
            f"📜 {b['lore']}\n"
            f"🥇 آسیب‌زننده‌ها:\n{lb}\n"
            f"⚔️ حمله: «باس»")


async def cmd_boss(m: Message):
    p = _guard(m)
    if not p:
        return
    ok, msg = boss.attack(m.from_user.id, m.chat.id)
    if ok:
        msg += player.advance_guide(m.from_user.id, "boss")
    await _send(m, msg, feed=True, kb=ui.boss_kb(m.from_user.id) if boss.active(m.chat.id) else None)


async def cmd_shift(m: Message):
    p = _guard(m)
    if not p:
        return
    ok, msg = income.shift(m.from_user.id)
    if ok:
        msg += player.advance_guide(m.from_user.id, "patrol")
    await _send(m, msg, kb=ui.quick_kb(m.from_user.id))


async def cmd_patrol(m: Message):
    p = _guard(m)
    if not p:
        return
    ok, msg = income.patrol(m.from_user.id)
    if ok:
        msg += player.advance_guide(m.from_user.id, "patrol")
    await _send(m, msg, kb=ui.quick_kb(m.from_user.id))


async def cmd_infect(m: Message):
    p = _guard(m)
    if not p:
        return
    ok, msg = infected.capture(m.from_user.id, m.chat.id)
    await _send(m, msg, feed=ok)


async def cmd_infected(m: Message):
    p = _guard(m)
    if not p:
        return
    await _send(m, infected.status(m.from_user.id)[1], kb=ui.infected_kb(m.from_user.id))


async def cmd_inf_raid(m: Message):
    p = _guard(m)
    if not p:
        return
    if not m.reply_to_message or not m.reply_to_message.from_user:
        await _send(m, "🧟 روی پیام هدف ریپلای کن و «هجوم» بزن.")
        return
    if m.reply_to_message.from_user.id == m.bot.id:
        await _send(m, "🧟 اینفکتدت از ربات می‌ترسد. عاقلانه است.")
        return
    d = player.get(m.reply_to_message.from_user.id)
    if not d:
        await _send(m, "🎯 او هنوز بازیکن نیست — «شروع» را بهش بگو.")
        return
    ok, msg = infected.raid(m.from_user.id, d["user_id"])
    await _send(m, msg, feed=ok)


# ═══════════ ساخت / انبار ═══════════
async def cmd_craft(m: Message, ref: str = ""):
    p = _guard(m)
    if not p:
        return
    if not ref:
        await _send(m, craft.craft_text(m.from_user.id))
        return
    if ref == "تفریخ":
        await _send(m, craft.hatch(m.from_user.id)[1])
    else:
        await _send(m, craft.craft(m.from_user.id, ref)[1])


async def cmd_inv(m: Message):
    p = _guard(m)
    if not p:
        return
    await _send(m, inv_text(m.from_user.id), kb=ui.inv_kb(m.from_user.id))


def inv_text(user_id: int) -> str:
    inv = player.inv(user_id)
    if not inv:
        return "🎒 انبار خالی است. «ساخت» یا «فروشگاه»"
    lines = []
    for iid, qty in sorted(inv.items()):
        if iid.startswith("pack_"):
            pid = iid[5:]
            pk = PACKS.get(pid)
            if pk:
                lines.append(f"{pk['emoji']} پک {pk['name']} ×{qty}")
            continue
        it = ITEMS.get(iid)
        if not it:
            continue
        eq = ""
        if it["kind"] == "equip":
            r = db.db().one("SELECT equipped FROM items WHERE user_id=? AND item_id=?",
                            (user_id, iid))
            eq = " ⬅️ فعال" if r and r["equipped"] else ""
        lines.append(f"{it['emoji']} {it['name']} ×{qty}{eq}")
    used = len(lines)
    return (f"🎒 <b>انبار</b> ({used} قلم)\n" + "\n".join(lines) +
            "\n\n⚙️ «تجهیز [کالا]» | 📦 «بازکردن [پک]»")


async def cmd_equip(m: Message, ref: str):
    p = _guard(m)
    if not p:
        return
    iid = market._resolve_item(ref)
    if not iid or ITEMS.get(iid, {}).get("kind") != "equip":
        await _send(m, "⚙️ فقط تجهیزات فعال می‌شوند (تانک برگری/مک پیتزایی/تاج).")
        return
    if player.inv(m.from_user.id).get(iid, 0) < 1:
        await _send(m, "🎒 نداریش.")
        return
    r = db.db().one("SELECT equipped FROM items WHERE user_id=? AND item_id=?",
                    (m.from_user.id, iid))
    cur = bool(r and r["equipped"])
    db.db().ex("UPDATE items SET equipped=? WHERE user_id=? AND item_id=?",
               (0 if cur else 1, m.from_user.id, iid))
    perf.invalidate_player(m.from_user.id)
    await _send(m, f"⚙️ {item_name(iid)}: {'غیرفعال' if cur else 'فعال'} شد.")


# ═══════════ پک / پاس / فروشگاه‌ها / سفارشی‌سازی ═══════════
async def cmd_packs(m: Message):
        await _send(m, packs.pack_text(m.from_user.id), kb=ui.packs_kb(m.from_user.id))


async def cmd_open_pack(m: Message, ref: str):
    _reg(m)
    import fuzzy as fz
    pid = fz.resolve(ref, {k: pk["name"] for k, pk in PACKS.items()})
    if not pid:
        await _send(m, "📦 «بازکردن [نام پک]»")
        return
    if player.on_cd(m.from_user.id, "pack"):
        await _react_quiet(m, "⏳")
        return
    ok, msg, img_key = packs.open_pack(m.from_user.id, pid)
    sent = await media.send(m.bot, m.chat.id, img_key, caption=msg)
    if not sent:
        await _send(m, msg)   # تصویر نبود؟ متن تنها


async def cmd_odds(m: Message, ref: str):
    pid = next((k for k, pk in PACKS.items() if ref in (k, pk["name"], pk["en"])), None)
    await _send(m, packs.odds_text(pid, m.from_user.id) if pid else "📊 «شانس [نام پک]»")


async def cmd_shop(m: Message):
        await _send(m, shop.shop_text(m.from_user.id), kb=ui.packs_kb(m.from_user.id))


async def cmd_shop_buy(m: Message, ref: str):
        await _send(m, shop.buy(m.from_user.id, ref)[1])


async def cmd_store(m: Message):
        await _send(m, payments.products_text())


async def cmd_pass(m: Message):
        await _send(m, passsys.pass_text(m.from_user.id), kb=ui.pass_kb(m.from_user.id))


async def cmd_pass_claim(m: Message, tier: str, track: str):
    _reg(m)
    if not _is_num(tier):
        await _send(m, "🎁 «جایزه پاس [پله] [رایگان|پرمیوم]»")
        return
    tr = "prem" if "پرمیوم" in track else "free"
    await _send(m, passsys.claim(m.from_user.id, int(tier), tr)[1])


async def cmd_cosmetics(m: Message):
        await _send(m, cosmetics.equip_text(m.from_user.id))


async def cmd_wear(m: Message, ref: str):
    _reg(m)
    if ref.startswith("بیرون"):
        await _send(m, cosmetics.unequip(m.from_user.id, ref.split(maxsplit=1)[-1] if " " in ref else "")[1])
        return
    await _send(m, cosmetics.equip(m.from_user.id, ref)[1])


# ═══════════ پرداخت ═══════════
async def cmd_order(m: Message, ref: str):
    if m.chat.type != "private":
        await _send(m, "🛍 سفارش‌ها فقط در پیوی من: @FoodverseWarsBot")
        return
    if not ref:
        await _send(m, "🛍 «سفارش [نام محصول]» — فهرست: «خرید»")
        return
    await _send(m, payments.create_order(m.from_user.id, ref)[1])


async def cmd_cancel_order(m: Message):
        await _send(m, payments.cancel_order(m.from_user.id)[1])


async def cmd_receipt_text(m: Message, tracking: str):
    if m.chat.type != "private":
        return
    await _send(m, "🖼 عکس رسید را با این پیام بفرست: عکس + کپشن «رسید "
                  f"{tracking or '[شماره پیگیری]'}»")


_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


async def on_photo(m: Message):
    """رسید پرداخت: عکس + کپشن «رسید [شماره]» — بدون هیچ پیشوندی."""
    if m.chat.type != "private" or not m.photo or not m.caption:
        return
    cap = m.caption.strip()
    parts = cap.split()
    if not parts or parts[0].lstrip("/").strip() != "رسید":
        return
    if len(parts) < 2:
        await m.reply("🧾 کپشن این‌طور باشد: رسید 12345678")
        return
    perf.STATS.commands += 1
    tracking = parts[1].translate(_DIG)
    _reg(m)
    fid = m.photo[-1].file_id
    data = await m.bot.download(fid)
    photo_hash = payments.hash_photo(data.read() if hasattr(data, "read") else data.getvalue())
    ok, res = payments.submit_receipt(m.from_user.id, tracking, photo_hash)
    if ok:
        # ارسال برای همه‌ی مدیران
        sent = 0
        for aid in ADMIN_IDS:
            try:
                await m.bot.send_photo(aid, fid,
                                       caption=payments.order_info_for_admin(res),
                                       reply_markup=ui.admin_order_kb(res["order_id"]))
                sent += 1
            except Exception:
                continue
        await _send(m, "🔵 رسید ثبت شد و برای بررسی به مدیر رفت.\n"
                      f"🧾 کد سفارش: <code>{res['order_id']}</code>\n"
                      "⏳ بعد از تأیید واریز، محصول تحویل داده می‌شود.")
    else:
        await _send(m, res if isinstance(res, str) else "🚫 خطا در ثبت رسید.")


# ═══════════ بازار ═══════════
async def cmd_market(m: Message, page: str = "0"):
    p = _guard(m)
    if not p:
        return
    await _send(m, market.market_text(m.chat.id, _num(page, 0)))


async def cmd_prices(m: Message):
        await _send(m, market.prices_text())


async def cmd_npc_buy(m: Message, ref: str, qty: str):
        await _send(m, market.npc_buy(m.from_user.id, ref, _num(qty))[1])


async def cmd_npc_sell(m: Message, ref: str, qty: str):
        await _send(m, market.npc_sell(m.from_user.id, ref, _num(qty))[1])


async def cmd_sell_item(m: Message, ref: str, qty: str, price: str):
    p = _guard(m)
    if not p:
        return
    if not (_is_num(qty) and _is_num(price)):
        await _send(m, "🔄 «بفروش [کالا] [تعداد] [قیمت]»")
        return
    await _send(m, market.sell_item(m.from_user.id, m.chat.id, ref, int(qty), int(price))[1])


async def cmd_buy_listing(m: Message, ref: str):
    p = _guard(m)
    if not p:
        return
    if not _is_num(ref):
        await _send(m, "🛒 «برداشتن [شماره‌ی آگهی]»")
        return
    await _send(m, market.buy_listing(m.from_user.id, m.chat.id, int(ref))[1])


async def cmd_price_history(m: Message, ref: str):
    p = _guard(m)
    if not p:
        return
    await _send(m, market.price_history(m.chat.id, ref))


# ═══════════ اتحاد ═══════════
async def cmd_ally(m: Message, rest: str):
    p = _guard(m)
    if not p:
        return
    parts = rest.split(maxsplit=1)
    sub = parts[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""
    if not sub:
        await _send(m, alliance.status_text(m.from_user.id))
    elif sub == "تأسیس":
        await _send(m, alliance.create(m.from_user.id, m.chat.id, arg)[1])
    elif sub == "عضویت":
        await _send(m, alliance.join(m.from_user.id, m.chat.id, arg)[1])
    elif sub == "ترک":
        await _send(m, alliance.leave(m.from_user.id)[1])
    elif sub == "کمک" and arg:
        bits = arg.split()
        qty = bits[1] if len(bits) > 1 else "1"
        await _send(m, alliance.help_(m.from_user.id, bits[0],
                                      _num(qty))[1])
    elif sub == "خیانت":
        ok, msg = alliance.betray(m.from_user.id)
        await _send(m, msg, feed=ok)
    else:
        await _send(m, alliance.status_text(m.from_user.id))


# ═══════════ رتبه‌بندی ═══════════
async def cmd_top(m: Message, rest: str = ""):
    p = _guard(m)
    if not p:
        return
    parts = rest.split()
    scope = "global" if parts and parts[0] == "جهانی" else "group"
    key = "power"
    for k in rank.BOARDS:
        if parts and parts[-1] in k:
            key = k
            break
    await _send(m, rank.board_text(scope, key, m.chat.id))


# ═══════════ مدیر (متن) ═══════════
async def cmd_admin(m: Message, rest: str):
    if m.from_user.id not in ADMIN_IDS:
        return
    parts = rest.split(maxsplit=1)
    sub = parts[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""
    if sub == "پیام" and arg:
        n = await admin.broadcast(m.bot, f"📢 <b>پیام کارخانه</b>\n\n{arg}")
        await _send(m, f"📢 ارسال به {n} دنیا.")
    elif sub == "بن" and m.reply_to_message:
        await _send(m, admin.ban(m.reply_to_message.from_user.id))
    elif sub == "حذف‌بن" and m.reply_to_message:
        await _send(m, admin.unban(m.reply_to_message.from_user.id))
    elif sub == "هدیه" and m.reply_to_message and arg:
        bits = arg.split()
        if len(bits) >= 2:
            await _send(m, admin.give(m.reply_to_message.from_user.id, bits[0], bits[1]))
        else:
            await _send(m, "🎁 ریپلای + «مدیر هدیه [شناسه] [چیز] [تعداد]»")
    elif sub == "باس":
        msg = boss.spawn_tick(m.chat.id, force=True)
        if msg:
            await _send(m, msg)
            w = boss.active(m.chat.id)
            if w:
                await media.send(m.bot, m.chat.id, f"boss_{w['boss_id']}")
        else:
            await _send(m, "👑 اسپاون نشد (شرایط).")
    elif sub == "آمار":
        await _send(m, admin.stats_text())
    elif sub == "تصویر" and m.reply_to_message and m.reply_to_message.photo:
        key = arg.strip().replace(" ", "_")
        if not key:
            await _send(m, "🖼 «مدیر تصویر [کلید]» روی عکس")
            return
        fid = m.reply_to_message.photo[-1].file_id
        media.set_file_id(key, fid, "photo")
        await _send(m, f"🖼 تصویر «{key}» ثبت شد (شناسه‌ی فایل ذخیره شد — دیگر آپلود نمی‌شود).")
    elif sub == "پیش‌نمایش" and arg:
        msg = await media.send(m.bot, m.chat.id, arg.strip())
        await _send(m, "🖼 موجود نبود." if not msg else f"🖼 پیش‌نمایش «{arg}» ↑")
    elif sub == "حذف‌تصویر" and arg:
        ok = media.remove(arg.strip())
        await _send(m, "🖼 حذف شد." if ok else "🖼 پیدا نشد.")
    elif sub == "رسیدها":
        rows = db.db().q("SELECT * FROM orders WHERE status='pending_review' ORDER BY id DESC LIMIT 5")
        if not rows:
            await _send(m, "🧾 رسید در انتظاری نیست.")
        for o in rows:
            await m.answer(payments.order_info_for_admin(o),
                           reply_markup=ui.admin_order_kb(o["order_id"]))
    elif sub == "برند":
        r = db.db().one("SELECT v FROM kv WHERE k='brand_target'")
        if not r:
            await _send(m, "📨 اول یک پیام از گروه نبرد را برای بات فوروارد کن تا شناسه‌اش ثبت شود.")
            return
        cid = int(r["v"])
        from aiogram.types import FSInputFile
        rep = ["🎨 <b>برندینگ گروه</b>"]
        try:
            await m.bot.set_chat_title(cid, "🍔 FOODVERSE WARS | Community")
            rep.append("✅ عنوان: 🍔 FOODVERSE WARS | Community")
        except Exception as e:
            rep.append(f"❌ عنوان: {e}")
        try:
            await m.bot.set_chat_description(
                cid, "⚔️ گروه نبرد رسمی FOODVERSE WARS — ۴ نفر «شروع» بزنند و جنگ شروع می‌شود!\n"
                     "🤖 ربات: @FoodverseWarsBot | 📚 آموزش‌ها: @FoodverseWars")
            rep.append("✅ توضیحات گروه")
        except Exception as e:
            rep.append(f"❌ توضیحات: {e}")
        try:
            photo = media.fs_path("brand_group") or media.fs_path("brand_channel")
            if photo:
                await m.bot.set_chat_photo(cid, FSInputFile(photo))
                rep.append("✅ عکس گروه")
            else:
                rep.append("❌ عکس: فایل تصویر گروه در دارایی‌های بازی نیست")
        except Exception as e:
            rep.append(f"❌ عکس: {e}")
        try:
            intro = ("⚔️ <b>به گروه نبرد FOODVERSE WARS خوش آمدید!</b>\n\n"
                     "۴ نفر «شروع» بزنند تا دنیای این گروه روشن شود؛ بعد:\n"
                     "🪖 «جذب برگر ۵» — ارتش بساز\n"
                     "🏭 «ارتقا کارخانه» — درآمد\n"
                     "⚔️ «جنگ [نام]» — نبرد\n"
                     "👹 «باس» — باس‌رید گروهی\n\n"
                     "📚 آموزش کامل: @FoodverseWars\n"
                     "🤖 ربات: @FoodverseWarsBot")
            photo = media.fs_path("brand_group")
            if photo:
                msg = await m.bot.send_photo(cid, FSInputFile(photo), caption=intro,
                                             parse_mode="HTML")
            else:
                msg = await m.bot.send_message(cid, intro)
            await m.bot.pin_chat_message(cid, msg.message_id, disable_notification=True)
            rep.append("✅ پست معرفی + پین")
        except Exception as e:
            rep.append(f"❌ پست: {e}")
        await _send(m, "\n".join(rep))
    elif sub == "قیمت" and arg:
        # «قیمت [محصول] [تومان]» → تغییر قیمت محصول
        bits = arg.split()
        if len(bits) == 2 and _is_num(bits[1]):
            prod = payments._resolve_product(bits[0])
            if prod:
                db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)",
                           (f"price_{prod}", bits[1]))
                await _send(m, f"💰 قیمت {prod} → {int(bits[1]):,} تومان (از سفارش بعدی).")
            else:
                await _send(m, "🛍 محصول نامعتبر.")
        else:
            await _send(m, "💰 «مدیر قیمت [محصول] [تومان]»")
    else:
        await _send(m, "⚙️ مدیر: پیام [متن] | بن (ریپلای) | حذف‌بن (ریپلای) | هدیه (ریپلای) | "
                      "باس | آمار | تصویر [کلید] (ریپلای عکس) | پیش‌نمایش [کلید] | "
                      "حذف‌تصویر [کلید] | رسیدها | قیمت [محصول] [تومان] | برند "
                      "(بعد از فوروارد پیام گروه)")


# ═══════════ Callback: منوها ═══════════
async def on_callback(c: CallbackQuery):
    perf.STATS.callbacks += 1
    data = c.data or ""
    if data.startswith("adm:"):
        await _admin_callback(c)
        return
    if data.startswith("gc:"):          # ✅ چک فوری عضویت — بعد از کلیک کاربر
        try:
            uid_gc = int(data.split(":", 1)[1])
        except ValueError:
            await c.answer()
            return
        if c.from_user.id != uid_gc:
            await c.answer("👆 دکمه‌ی خودت را بزن", show_alert=False)
            return
        import gate as _gate
        _gate.invalidate(uid_gc)        # کش قدیمی بی‌اثر — چک تازه
        ok = await _gate.is_member(c.bot, uid_gc)
        if ok:
            await c.answer("✅ عضویت تأیید شد! حالا دستورت را بفرست", show_alert=False)
            try:
                await c.message.edit_text("✅ <b>عضویت تأیید شد!</b>\n"
                                          "🎮 حالا دستورت را بفرست — مثل: «منو»")
            except Exception:
                pass
        else:
            await c.answer("❌ هنوز عضو نشده‌ای — اول عضو کانال شو", show_alert=True)
        return
    if not data.startswith("h:"):
        await c.answer()
        return
    _, uid_s, action = data.split(":", 2)
    uid = int(uid_s)
    if uid and c.from_user.id != uid:
        await c.answer("👆 منوی خودت را باز کن", show_alert=False)
        return
    if not perf.allow(("cb", c.from_user.id), 1, 0.3):
        await c.answer("⏳", show_alert=False)
        return
    p = _reg_msg_from_callback(c)
    if not p or p["banned"]:
        await c.answer()
        return
    player.tick(c.from_user.id)
    arg = ""
    if ":" in action:
        action, arg = action.split(":", 1)

    chat_id = c.message.chat.id
    texts_map = {
        "me": lambda: profile_text(p),
        "base": lambda: base.base_text(uid),
        "army": lambda: army.army_text(uid),
        "craft": lambda: craft.craft_text(uid),
        "boss": lambda: boss_status_text(chat_id),
        "ally": lambda: alliance.status_text(uid),
        "market": lambda: market.market_text(chat_id, _num(arg, 0)),
        "top": lambda: rank.board_text("group", "power", chat_id),
        "topg": lambda: rank.board_text("global", "power", chat_id),
        "daily": lambda: player.daily(uid)[1],
        "help": (lambda: __import__("help_pages").HELP_PAGES[0]),
        "inv": lambda: inv_text(uid),
        "packs": lambda: packs.pack_text(uid),
        "pass": lambda: passsys.pass_text(uid),
        "shop": lambda: shop.shop_text(uid),
        "store": lambda: payments.products_text(),
        "cosmetic": lambda: cosmetics.equip_text(uid),
        "infected": lambda: infected.status(uid)[1],
        "prices": lambda: market.prices_text(),
        "hint": lambda: hint_text(uid, chat_id),
        "ledger": lambda: ledger_text(uid),
        "hub": lambda: "🍔 <b>منوی فوودورس</b>",
        "back": lambda: "🍔 <b>منوی فوودورس</b>",
    }
    from help_pages import HELP_PAGES as _HP
    for _i in range(len(_HP)):
        texts_map[f"hp{_i}"] = (lambda i=_i: _HP[i])

    def _page_kb(a: str):
        """کیبورد اختصاصی هر صفحه — بازی با دکمه."""
        if a == "base":
            return ui.base_kb(uid)
        if a == "me":
            return ui.quick_kb(uid)
        if a == "boss":
            return ui.boss_kb(uid) if boss.active(chat_id) else ui.sub_kb(uid, [("🍔 منو", "hub")])
        if a == "packs":
            return ui.packs_kb(uid)
        if a == "pass":
            return ui.pass_kb(uid)
        if a == "shop":
            return ui.shop_kb(uid)
        if a == "inv":
            return ui.inv_kb(uid)
        if a == "infected":
            return ui.infected_kb(uid)
        if a == "army":
            return ui.army_view_kb(uid)
        if a == "market":
            rows = db.db().q("""SELECT l.id, l.price FROM listings l
                                WHERE l.chat_id=? AND l.active=1
                                ORDER BY l.created_at DESC LIMIT 8""", (chat_id,))
            lab = [(r["id"], f"🛒 آگهی #{r['id']} — 🪙 {r['price']:,}") for r in rows]
            return ui.market_kb(uid, lab)
        if a in ("daily",):
            return ui.quick_kb(uid)
        return None

    def _army_shop_text(uid_):
        p_ = player.get(uid_)
        from registry import UNITS
        from army import unit_price
        lines = ["🛒 <b>فروشگاه ارتش — خرید با فودکوین</b>",
                 f"🪙 موجودی تو: <b>{(p_['fc'] or 0):,.0f} فودکوین</b>", "",
                 "هر دکمه = خرید ۱ سرباز — بدون تایپ!"]
        for k_, un in UNITS.items():
            if un.get("cost"):
                lines.append(f"{un['emoji']} {un['name']} — {unit_price(k_):,} 🪙")
        lines += ["", "💡 پول کم؟ «فودکوین» بگو — شیر رایگان هر ۱۰ دقیقه"]
        return "\n".join(lines)
    texts_map["armyshop"] = lambda: _army_shop_text(uid)
    if action == "card":
        await c.answer()
        try:
            path = cardgen.generate(p)
            with open(path, "rb") as f:
                await c.message.answer_photo(f, caption=profile_text(p))
        except Exception:
            await c.message.edit_text(profile_text(p))
        return
    # ─── ⚡️ اکشن‌های دکمه‌ای: بازی بدون تایپ ───
    async def _refresh(page_action: str, page_arg: str = ""):
        """صفحه را دوباره بساز و edit کن (بروز موجودی و وضعیت)."""
        try:
            txt = texts_map[page_action]() if page_action in texts_map else None
            if txt is None:
                return
            kbx = _page_kb(page_action)
            await c.message.edit_text(txt, reply_markup=kbx)
        except Exception:
            pass

    if action == "up":                      # ⬆️ ارتقای ساختمان با دکمه
        ok, msg = base.upgrade(uid, arg)
        if ok:
            msg += player.advance_guide(uid, "build")
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        await _refresh("base")
        return
    if action in ("milk", "shift", "patrol", "bosshit"):
        if player.on_cd(uid, "cmd"):        # همان کول‌داون دستورها
            await c.answer("⏳ چند ثانیه صبر کن…")
            return
        if action == "milk":
            ok, msg = player.faucet(uid)
            page = "me"
        elif action == "shift":
            ok, msg = income.shift(uid); page = "me"
        elif action == "patrol":
            ok, msg = income.patrol(uid); page = "me"
        else:
            ok, msg = boss.attack(uid, chat_id); page = "boss"
            if ok:
                msg += player.advance_guide(uid, "boss")
        await c.answer()
        try:
            await c.message.answer(msg)
        except Exception:
            pass
        await _refresh(page)
        return
    if action == "pkbuy":                   # 🛒 خرید پک با فودکوین
        ok, msg = shop.buy(uid, arg)
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        await _refresh("shop")
        return
    if action == "pkopen":                  # 🎁 بازکردن پک
        if player.on_cd(uid, "pack"):
            await c.answer("⏳ یک نفس بکش…")
            return
        ok, msg, img_key = packs.open_pack(uid, arg)
        await c.answer()
        try:
            await media.send(c.bot, chat_id, img_key, caption=msg)
        except Exception:
            try:
                await c.message.answer(msg)
            except Exception:
                pass
        await _refresh("packs")
        return
    if action == "bp":                      # 🎫 جایزه بتل‌پس
        tier = arg[:-1] if arg and arg[-1] in "fp" else ""
        tr = "prem" if arg.endswith("p") else "free"
        if not tier.isdigit():
            await c.answer("❌ پله نامعتبر")
            return
        ok, msg = passsys.claim(uid, int(tier), tr)
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        await _refresh("pass")
        return
    if action == "mkt":                     # 🛒 خرید آگهی بازار
        if not arg.isdigit():
            await c.answer("❌")
            return
        ok, msg = market.buy_listing(uid, chat_id, int(arg))
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        await _refresh("market")
        return
    if action == "eq":                     # ⚙️ تجهیز/غیرفعال با دکمه
        from registry import ITEMS
        iid = arg
        if ITEMS.get(iid, {}).get("kind") != "equip" or player.inv(uid).get(iid, 0) < 1:
            await c.answer("🎒 نداریش", show_alert=True)
            return
        r = db.db().one("SELECT equipped FROM items WHERE user_id=? AND item_id=?", (uid, iid))
        cur = bool(r and r["equipped"])
        db.db().ex("UPDATE items SET equipped=? WHERE user_id=? AND item_id=?",
                   (0 if cur else 1, uid, iid))
        perf.invalidate_player(uid)
        await c.answer("⚙️ غیرفعال شد" if cur else "⚙️ فعال شد")
        await _refresh("inv")
        return
    if action == "infect":                # 🧟 گرفتن اینفکتد با دکمه
        ok, msg = infected.capture(uid, chat_id)
        await c.answer()
        try:
            await c.message.answer(msg)
        except Exception:
            pass
        await _refresh("infected")
        return
    if action == "sbuy":                  # 🛒 خرید اسلات چرخشی فروشگاه
        ok, msg = shop.buy(uid, arg)
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        await _refresh("shop")
        return
    if action == "buy":
        unit_id = arg
        ok, msg = army.buy_fc(uid, unit_id, 1)
        await c.answer(msg.split("\n")[0], show_alert=not ok)
        try:
            await c.message.edit_text(texts_map["armyshop"](), reply_markup=ui.army_shop_kb(uid))
        except Exception:
            pass
        return
    if action in texts_map:
        txt = texts_map[action]()
        titles = {"me": "👤 پروفایل", "base": "🏠 پایگاه", "army": "🪖 ارتش", "inv": "🎒 انبار",
                  "craft": "🛠 کارگاه", "boss": "👑 باس", "ally": "🤝 اتحاد", "market": "🔄 بازار",
                  "top": "🏆 رتبه‌ی گروه", "topg": "🌍 رتبه‌ی جهانی", "daily": "🎁 روزانه",
                  "help": "📖 راهنما", "packs": "📦 پک‌ها", "pass": "🎫 بتل‌پس",
                  "shop": "🛒 فروشگاه", "store": "💰 خرید فودکوین و پاس",
                  "cosmetic": "🎨 ظاهر", "hub": "🧭 هاب فرماندهی", "back": "🧭 هاب فرماندهی"}
        t = titles.get(action)
        if t and not txt.startswith(t):
            txt = f"{t}\n{'─' * 18}\n{txt}"
        kb = (ui.army_shop_kb(uid) if action == "armyshop"
              else (ui.help_kb(uid, int(action[2:])) if action.startswith("hp") and action[2:].isdigit()
              else (ui.help_kb(uid, 0) if action == "help" else
              (ui.hub_kb(uid) if action in ("hub", "back") else
              (_page_kb(action) or ui.sub_kb(uid, [("🌍 جهانی", "topg")] if action == "top" else []))))))
        try:
            await c.message.edit_text(txt, reply_markup=kb)
        except Exception:
            pass
        await c.answer()
        return
    await c.answer()


def _reg_msg_from_callback(c: CallbackQuery) -> dict:
    return player.register(c.from_user.id,
                           c.from_user.full_name or f"بازیکن{c.from_user.id}", None)


# ═══════════ Callback: تأیید سفارش مدیر ═══════════
async def _admin_callback(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer("⛔", show_alert=False)
        return
    _, order_id, act = c.data.split(":", 2)
    if act == "info":
        o = db.db().one("SELECT * FROM orders WHERE order_id=?", (order_id,))
        await c.answer("اطلاعات در متن پیام است.", show_alert=True)
        return
    ok, o, msg = payments.decide(order_id, c.from_user.id, act == "ok")
    if not ok:
        await c.answer(msg, show_alert=True)
        return
    mark = "✅ تأیید شد" if act == "ok" else "❌ رد شد"
    # 💬 اطلاع‌رسانی دوطرفه و دقیق
    if act == "ok":
        try:   # بازیکن: «خریدت فعال شد» + جزئیات کامل
            await c.bot.send_message(o["user_id"],
                                     payments.approved_note_for_user(o, msg))
        except Exception:
            pass
        try:   # ادمین: «پول با این پیگیری واریز شد و فعال شد»
            await c.message.answer(payments.approved_note_for_admin(o))
        except Exception:
            pass
    else:
        try:
            await c.bot.send_message(o["user_id"],
                                     "🔴 سفارشت رد شد. اگر اشتباه بود با مدیر تماس بگیر.")
        except Exception:
            pass
    try:
        await c.answer(mark, show_alert=False)
        await c.message.edit_reply_markup(reply_markup=None)
        new_cap = (c.message.caption or "") + f"\n\n{mark} — توسط مدیر"
        await c.message.edit_caption(caption=new_cap)
    except Exception:
        pass


# ═══════════ راهنما ═══════════
async def cmd_help(m: Message):
    from help_pages import HELP_PAGES
    step = player.guide_step(m.from_user.id) if m.from_user else 0
    extra = ""
    if step < len(texts.GUIDE_STEPS):
        extra = "\n\n" + texts.GUIDE_STEPS[step]["tip"]
    await _send(m, HELP_PAGES[0] + extra, kb=ui.help_kb(m.from_user.id, 0))


# ═══════════ توزیع‌کننده‌ی دستورها — بدون پیشوند؛ خود کلمه = دستور ═══════════
CMD_WORDS = frozenset((
    "شروع", "منو", "من", "کارت", "روزانه", "رفرال", "دعوت", "پایگاه", "ارتقا", "مستعمره", "غارت",
    "ارتش", "جذب", "جنگ", "باس", "شیفت", "گشت", "اینفکت", "اینفکتد", "هجوم",
    "شخصیت", "ساخت", "تفریخ", "انبار", "تجهیز", "پک", "بازکردن", "شانس",
    "فروشگاه", "خریدن", "خرید", "فروش", "بفروش", "برداشتن", "قیمت", "قیمت‌ها",
    "معامله", "گذاشتن", "درآوردن", "تایید", "فودکوین", "fc",
    "پیشنهاد", "نصیحت", "چیکارکنم", "درود", "دفتر", "وان‌شات", "انتقال",
    "پاس", "جایزه", "سفارشی", "بپوش", "دربیاور", "سفارش", "لغو", "رسید",
    "رتبه", "مدیر", "اتحاد", "تأسیس", "عضویت", "ترک", "کمک", "خیانت",
    "راهنما", "آموزش", "دفتر",
))
REGISTERED_SLASH = frozenset((
    "start", "help", "menu", "daily", "base", "army", "boss", "inv",
    "packs", "pass", "shop", "ally", "top",
))

GROUP_CMDS = ("شروع", "منو", "من", "پایگاه", "ارتقا", "مستعمره", "غارت", "ارتش", "جذب",
              "جنگ", "باس", "ساخت", "انبار", "تجهیز", "بازار", "فروشگاه", "بفروش",
              "برداشتن", "قیمت", "اتحاد", "تأسیس", "عضویت", "ترک", "کمک", "خیانت",
              "رتبه", "شخصیت", "بازکردن", "مدیر", "اینفکت", "اینفکتد", "هجوم",
              "شیفت", "گشت")


# 📢 دستورهایی که بدون عضویت در کانال هم جواب می‌گیرند
UNGATED = frozenset((
    "شروع", "راهنما", "آموزش", "رفرال", "دعوت", "درود",
    "سفارش", "رسید", "لغو",          # پرداخت هرگز بلاک نشود
    "مدیر", "پیام", "بن", "حذف‌بن", "هدیه", "آمار", "تصویر", "پیش‌نمایش", "حذف‌تصویر",
    "رسیدها", "قیمت‌ها",              # ادمین + دیدن قیمت‌ها آزاد
))


CMD_GLOBAL_CD = 10   # ⏱ فاصله‌ی حداقلی بین دستورهای هر بازیکن — ضداسپم؛ گروه شلوغ نشود

# 🎯 دستورهای تکی: فقط وقتی پیام همان یک کلمه باشد اجرا می‌شوند.
# «شروع» اجرا می‌شود | «درود شروع کن» اجرا نمی‌شود — گفتگو گفتگوست، دستور دستور.
SOLO_CMDS = frozenset((
    "شروع", "منو", "من", "کارت", "روزانه", "فودکوین", "fc", "پایگاه", "ارتش",
    "انبار", "باس", "اینفکت", "اینفکتد", "جنگ", "غارت", "مستعمره", "اتحاد",
    "بازار", "رتبه", "رفرال", "دعوت", "آموزش", "راهنما", "پاس", "پک",
    "فروشگاه", "گشت", "شیفت", "پیشنهاد", "نصیحت", "چیکارکنم", "درود",
    "وان‌شات", "ترک", "خیانت", "هجوم", "تجهیز",
))
SPAM_STRIKES = 8          # ⚠️ ۸ برخورد با گیت در ۶۰ ثانیه = اسپمر
SPAM_SILENCE_S = 180      # 🤐 سکوت موقت ۳ دقیقه


def _silenced_until(uid: int) -> float:
    row = db.db().one("SELECT v FROM kv WHERE k=?", (f"silence:{uid}",))
    try:
        return float(row["v"]) if row else 0.0
    except Exception:
        return 0.0


class ChannelGate(BaseMiddleware):
    """عضویت اجباری کانال + کول‌داون سراسری — فقط روی دستورهای بازی؛ گفتگو آزاد است."""

    async def __call__(self, handler, event, data):
        u = data.get("event_from_user")
        if not u or u.is_bot or u.id in ADMIN_IDS:
            return await handler(event, data)
        import gate as _gate
        if isinstance(event, CallbackQuery):
            d = event.data or ""
            if not d.startswith("h:"):        # adm: → فقط ادمین
                return await handler(event, data)
            if d.split(":")[-1] in ("help", "back", "hub"):
                return await handler(event, data)
            if not await _gate.is_member(event.bot, u.id):
                try:
                    await event.answer(_gate.join_text(), show_alert=True)
                except Exception:
                    pass
                return
            return await handler(event, data)
        txt = (event.text or event.caption or "").strip()
        if not txt:
            return await handler(event, data)  # عکس بدون کپشن و …
        first = txt.split(maxsplit=1)[0]
        word = first.lstrip("/").strip()
        if not (word in CMD_WORDS or first.startswith("/")):
            return await handler(event, data)  # گفتگوی عادی → آزاد
        if word in UNGATED:
            return await handler(event, data)
        # 🤐 فایروال: اسپمر ساکت‌شده فقط ری‌اکشن می‌گیرد — صفر پیام
        if _silenced_until(u.id) > _time.time():
            try:
                await media.react(event.bot, event.chat.id, event.message_id, "🤐")
            except Exception:
                pass
            return
        # ⏱ کول‌داون سراسری ۱۰ ثانیه — بی‌صدا؛ فقط ری‌اکشن ⏳
        if not perf.allow(("cmdcd", u.id), 1, CMD_GLOBAL_CD):
            strikes = perf.allow(("spam", u.id), SPAM_STRIKES, 60)
            if not strikes:                       # 🚨 سیلِ دستور — تیپیکال اسپمر
                db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)",
                           (f"silence:{u.id}", str(_time.time() + SPAM_SILENCE_S)))
                try:
                    await event.answer("🤐 آرام! ۳ دقیقه دستورها برایت بسته است — ضداسپم.")
                    await media.react(event.bot, event.chat.id, event.message_id, "👮")
                except Exception:
                    pass
                return
            try:
                await media.react(event.bot, event.chat.id, event.message_id, "⏳")
            except Exception:
                pass
            return
        if not await _gate.is_member(event.bot, u.id):
            try:
                await event.answer(_gate.join_text(), reply_markup=_gate.join_kb(u.id))
            except Exception:
                pass
            return
        return await handler(event, data)


async def on_text(m: Message):
    if not m.text or (m.from_user and m.from_user.is_bot):
        return
    # 📨 فوروارد ادمین از گروه → ثبت chat_id برای برندینگ گروه
    if (m.chat.type == "private" and m.from_user
            and m.from_user.id in ADMIN_IDS and getattr(m, "forward_origin", None)):
        fchat = None
        try:
            fchat = m.forward_origin.chat        # MessageOriginChat/Channel (aiogram 3.7+)
        except AttributeError:
            fchat = getattr(m, "forward_from_chat", None)
        if fchat and getattr(fchat, "type", "") in ("group", "supergroup"):
            db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)",
                       ("brand_target", str(fchat.id)))
            await _send(m, f"🆔 گروه «{fchat.title}» ثبت شد — شناسه‌ی عددی گروه: <code>{fchat.id}</code>\n"
                          "🎨 حالا «مدیر برند» را بفرست تا عنوان/عکس/توضیحات/پست معرفی ست شود.")
            return
    text = m.text.strip()
    # ─── بدون پیشوند: کلمه‌ی اول، خودِ دستور است ───
    if text.startswith("/"):
        first, _, tail = text[1:].partition(" ")
        first = first.split("@", 1)[0]        # فقط /cmd@BotName
        if not first or (not tail and first in REGISTERED_SLASH):
            return   # دستورهای ثبت‌شده‌ی رسمی و اسلشِ تنها
        text = (first + " " + tail).strip()
    low = text.lower()
    # عادت قدیمی: کلمه‌ی پیشوند کاملاً نادیده گرفته می‌شود (fw جنگ = جنگ)
    if low in ("fw", "fw؟", "fw?"):
        await _send(m, "🔔 فقط کلمه‌ی دستور را بفرست — مثل: «منو» یا «راهنما»")
        return
    if low.startswith("fw ") or low.startswith("fw‌"):
        text = text[3:].strip()
        if not text:
            return
    _fw = text.split(maxsplit=1)[0]
    if _fw not in CMD_WORDS and _fw.lower() not in CMD_WORDS:
        return   # گفتگوی عادی → سکوت محترمانه (FC/Fc/fc همه یکی)
    body = text
    perf.STATS.commands += 1
    parts = body.split()
    cmd = parts[0]
    try:
        m._fw_cmd = cmd          # 💡 برای hint کوتاه در _send
    except Exception:
        pass
    p0 = _reg(m)
    if p0["banned"] and cmd != "مدیر":
        return
    rest = body[len(cmd):].strip()
    if cmd in SOLO_CMDS and rest:
        return   # 💬 «درود شروع کن» گفتگوست، نه دستور — دستور فقط خالی اجرا می‌شود
    a = parts[1] if len(parts) > 1 else ""
    b2 = parts[2] if len(parts) > 2 else ""
    c3 = parts[3] if len(parts) > 3 else ""

    in_group = m.chat.type != "private"
    # گیم‌پلی گروهی در پیوی → هدایت
    GAMEPLAY = ("شروع", "پایگاه", "ارتقا", "مستعمره", "غارت", "جذب", "جنگ", "باس",
                "بازار", "بفروش", "برداشتن", "تأسیس", "عضویت", "خیانت",
                "اینفکت", "هجوم")
    if not in_group and cmd in GAMEPLAY:
        me = await m.bot.get_me()
        await m.answer("⚔️ بازی اصلی در گروه‌ها اجرا می‌شود!",
                       reply_markup=ui.private_kb(me.username, GROUP_LINK))
        return
    if (in_group and not world.is_started(m.chat.id)
            and cmd not in ("شروع", "مدیر", "راهنما", "آموزش", "رفرال", "دعوت")):
        await _send(m, texts.DEAD_WORLD.format(need=MIN_PLAYERS))
        return

    if cmd == "شروع":
        await cmd_start(m)
    elif cmd in ("رفرال", "دعوت"):
        await cmd_referral(m)
    elif cmd == "دفتر":
        await _send(m, ledger_text(m.from_user.id))
    elif cmd == "فودکوین" or cmd.lower() == "fc":
        await _send(m, player.faucet(m.from_user.id)[1])
    elif cmd == "وان‌شات":
        await cmd_oneshot(m)
    elif cmd == "انتقال":
        await cmd_transfer(m, a)
    elif cmd == "درود" and not rest:
        if m.from_user.id == 8694290031:
            await _send(m, "🫡 <b>درود پادشاه!</b> 👑\n"
                           "همه دست بر سر — آشپزِ بزرگِ آشپزخانه‌ی مرکزی تشریف آورد.")
        elif perf.allow(("salute", m.from_user.id), 3, 60):   # ضداسپم: ۳ درود در دقیقه
            await _send(m, "🫡 درود بهشمار، جنگاور غذا!")
    elif cmd in ("پیشنهاد", "نصیحت", "چیکارکنم"):
        await cmd_hint(m)
    elif cmd == "معامله":
        await cmd_trade(m, rest)
    elif cmd == "گذاشتن":
        await cmd_trade_put(m, a, b2)
    elif cmd == "درآوردن":
        await cmd_trade_take(m, a, b2)
    elif cmd == "تایید":
        await cmd_trade_confirm(m)
    elif cmd == "منو":
        await cmd_menu(m)
    elif cmd == "من":
        p = _guard(m)
        if p:
            await _send(m, profile_text(p))
    elif cmd == "کارت":
        await cmd_card(m)
    elif cmd == "روزانه":
        await cmd_daily(m)
    elif cmd == "پایگاه":
        await cmd_base(m)
    elif cmd == "ارتقا":
        await cmd_upgrade(m, rest)
    elif cmd == "مستعمره":
        await cmd_colony(m)
    elif cmd == "غارت":
        await cmd_raid(m)
    elif cmd == "ارتش":
        await cmd_army(m)
    elif cmd == "جذب":
        await cmd_recruit(m, a, b2)
    elif cmd == "جنگ":
        await cmd_war(m)
    elif cmd == "باس":
        await cmd_boss(m)
    elif cmd == "شیفت":
        await cmd_shift(m)
    elif cmd == "گشت":
        await cmd_patrol(m)
    elif cmd == "اینفکت":
        await cmd_infect(m)
    elif cmd == "اینفکتد":
        await cmd_infected(m)
    elif cmd == "هجوم":
        await cmd_inf_raid(m)
    elif cmd == "شخصیت":
        await cmd_char(m, rest)
    elif cmd == "ساخت":
        await cmd_craft(m, rest)
    elif cmd == "تفریخ":
        await cmd_craft(m, "تفریخ")
    elif cmd == "انبار":
        await cmd_inv(m)
    elif cmd == "تجهیز":
        await cmd_equip(m, rest)
    elif cmd == "پک":
        await cmd_packs(m)
    elif cmd == "بازکردن":
        await cmd_open_pack(m, rest)
    elif cmd == "شانس":
        await cmd_odds(m, rest)
    elif cmd == "فروشگاه":
        if rest == "ویژه":
            await cmd_store(m)
        else:
            await cmd_shop(m)
    elif cmd == "خریدن":
        await cmd_shop_buy(m, rest)
    elif cmd == "خرید":
        if a == "منبع":
            await cmd_npc_buy(m, b2, c3)
        else:
            await cmd_shop_buy(m, rest)
    elif cmd == "فروش":
        await cmd_npc_sell(m, b2 if a == "منبع" else a, c3 if a == "منبع" else b2)
    elif cmd == "بفروش":
        await cmd_sell_item(m, a, b2, c3)
    elif cmd == "برداشتن":
        await cmd_buy_listing(m, a)
    elif cmd == "قیمت":
        await cmd_price_history(m, rest)
    elif cmd == "قیمت‌ها":
        await cmd_prices(m)
    elif cmd in ("اتحاد", "تأسیس", "عضویت", "ترک", "کمک", "خیانت"):
        await cmd_ally(m, body)
    elif cmd == "پاس":
        await cmd_pass(m)
    elif cmd == "جایزه":
        await cmd_pass_claim(m, a, b2)
    elif cmd == "سفارشی":
        await cmd_cosmetics(m)
    elif cmd == "بپوش":
        await cmd_wear(m, rest)
    elif cmd == "دربیاور":
        await cmd_wear(m, "بیرون " + rest)
    elif cmd == "سفارش":
        await cmd_order(m, rest)
    elif cmd == "لغو":
        if "معامله" in rest:
            import trade as tr
            await _send(m, tr.cancel(m.chat.id, m.from_user.id)[1])
        else:
            await cmd_cancel_order(m)
    elif cmd == "رسید":
        await cmd_receipt_text(m, rest)
    elif cmd == "رتبه":
        await cmd_top(m, rest)
    elif cmd == "مدیر":
        await cmd_admin(m, rest)
    elif cmd in ("راهنما", "آموزش"):
        await cmd_help(m)
    # بقیه: بی‌پاسخ (ضداسپم)


# ═══════════ Slash mirror ═══════════
async def on_member_join(m: Message):
    """ورود اعضا: کینگ آمد → احترام! (ورود بات → توضیح شروع)"""
    if m.new_chat_members:
        for u in m.new_chat_members:
            if u.id == 8694290031 and u.id != m.bot.id:
                nm = u.full_name or "کینگ"
                await _send(m, "👑 <b>کینگ اومد!</b> 👑\n\n"
                               f"🎩 {nm} — مالک و پادشاه فوودورس وارد شد.\n"
                               "همه بهش احترام بذارید! 🫡")
                return
    if not m.new_chat_members or not any(u.id == m.bot.id for u in m.new_chat_members):
        return
    # 👑 پادشاه در این گروه هست؟ → به افتخار پادشاه (فقط یک بار در هر گروه)
    try:
        km = await m.bot.get_chat_member(m.chat.id, 8694290031)
        king_here = km and km.status not in ("left", "kicked")
    except Exception:
        king_here = False
    if king_here:
        seen = db.db().one("SELECT v FROM kv WHERE k=?", (f"kingsalute:{m.chat.id}",))
        if not seen:
            db.db().ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?, '1')",
                       (f"kingsalute:{m.chat.id}",))
            await _send(m, "🫡 <b>به افتخار پادشاه!</b> 👑\n\n"
                           "پادشاهِ فوودورس — @Meraj_rez — در این گروه حاضر است.\n"
                           "همه دست بزنید! 🫡🫡🫡\n\n"
                           "🍔 و حالا... جنگ غذاها شروع می‌شود.")
            return
    try:
        count = await m.bot.get_chat_member_count(m.chat.id)
    except Exception:
        count = 0
    if count >= MIN_PLAYERS:
        await _send(m, "🍔 <b>فوودورس به گروه شما آمد!</b>\n\n"
                       "جنگ بامزه‌ی غذاها همین‌جا شروع می‌شود.\n"
                       "یکی از اعضا فقط یک کلمه بنویسد: <b>شروع</b> \U0001F525")
    else:
        await _send(m, f"🍔 <b>فوودورس به گروه شما آمد!</b>\n\n"
                       f"برای شروع بازی، گروه باید حداقل {MIN_PLAYERS} عضو داشته باشد "
                       f"(الان {count} نفرید). دوست اضافه کنید و بنویسید: <b>شروع</b>")


def reg_slash(r: Router):
    r.message.outer_middleware(ChannelGate())
    r.callback_query.outer_middleware(ChannelGate())
    r.message.register(cmd_start, CommandStart())
    r.message.register(cmd_help, Command("help"))
    r.message.register(cmd_menu, Command("menu"))
    r.message.register(cmd_daily, Command("daily"))
    r.message.register(cmd_base, Command("base"))
    r.message.register(cmd_army, Command("army"))
    r.message.register(cmd_boss, Command("boss"))
    r.message.register(cmd_inv, Command("inv"))
    r.message.register(cmd_packs, Command("packs"))
    r.message.register(cmd_pass, Command("pass"))
    r.message.register(cmd_shop, Command("shop"))
    r.message.register(cmd_ally_wrap, Command("ally"))
    r.message.register(cmd_top_wrap, Command("top"))
    r.message.register(on_photo, F.photo)
    r.message.register(on_member_join, F.new_chat_members)


async def _rest(m: Message) -> str:
    return m.text.split(maxsplit=1)[1] if " " in m.text else ""


async def cmd_ally_wrap(m: Message):
    await cmd_ally(m, _rest(m))


async def cmd_top_wrap(m: Message):
    await cmd_top(m, _rest(m))
