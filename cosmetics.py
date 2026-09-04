# 🎨 Cosmetics Engine — سفارشی‌سازی ظاهر (Avatar/Frame/Title/Skin/Effect)
import db
import player
from registry import COSMETICS, RARITY

KIND_FA = dict(frame="🖼️ فریم پروفایل", title="🏷️ عنوان", skin="🎭 اسکین ارتش",
               effect="✨ افکت نبرد")
SLOT_FIELD = dict(frame="frame", title="title", skin="skin", effect="effect")


def owned(user_id: int) -> list:
    return [r["cid"] for r in db.db().q("SELECT cid FROM cosmetics WHERE user_id=?", (user_id,))]


def equip_text(user_id: int) -> str:
    p = player.get(user_id)
    have = owned(user_id)
    lines = ["🎨 <b>سفارشی‌سازی</b>", ""]
    lines.append(f"🖼️ فریم: {_name(p['cos_frame']) if p['cos_frame'] else '—'}")
    lines.append(f"🏷️ عنوان: {_name(p['cos_title']) if p['cos_title'] else title_default(p)}")
    lines.append(f"🎭 اسکین ارتش: {_name(p['cos_skin']) if p['cos_skin'] else 'پیش‌فرض'}")
    lines.append(f"✨ افکت نبرد: {_name(p['cos_effect']) if p['cos_effect'] else '—'}")
    lines.append("")
    if not have:
        lines.append("🎒 هنوز کازمتیکی نداری — از پک‌ها بگیر: «fw پک»")
    else:
        lines.append("موجود:")
        for cid in have:
            c = COSMETICS[cid]
            lines.append(f"{RARITY[c['rarity']][0]} {c['name']} ({KIND_FA[c['kind']]})")
    lines.append("\n⚙️ «fw بپوش [نام کازمتیک]» | «fw دربیاور [نوع]»")
    return "\n".join(lines)


def _name(cid: str):
    c = COSMETICS.get(cid)
    return f"{c['name']}" if c else "؟"


def title_default(p):
    from registry import title_of
    return title_of(p["level"])


def equip(user_id: int, ref: str) -> tuple:
    have = owned(user_id)
    cid = None
    for k, c in COSMETICS.items():
        if ref in (k, c["name"], c["en"]) and k in have:
            cid = k
            break
    if not cid:
        for k, c in COSMETICS.items():
            if ref in (k, c["name"], c["en"]):
                return False, "🎨 این کازمتیک را نداری — از پک‌ها بگیر."
        return False, "🎨 کازمتیک نامعتبر. «fw سفارشی»"
    c = COSMETICS[cid]
    field = "cos_" + c["kind"]
    db.db().ex(f"UPDATE accounts SET {field}=? WHERE user_id=?", (cid, user_id))
    return True, f"🎨 {c['name']} فعال شد! ({KIND_FA[c['kind']]})"


KIND_SHORT = dict(frame=("frame", "فریم", "قاب"), title=("title", "عنوان", "تاج"),
                  skin=("skin", "اسکین", "پوسته"), effect=("effect", "افکت", "جلوه"))


def unequip(user_id: int, kind_ref: str) -> tuple:
    kind = None
    ref = kind_ref.strip()
    for k, fa in KIND_FA.items():
        if ref in (k, fa) or ref in KIND_SHORT[k] or ref in fa:
            kind = k
            break
    if not kind:
        return False, "🎨 نوع: فریم/عنوان/اسکین/افکت"
    field = "cos_" + kind
    db.db().ex(f"UPDATE accounts SET {field}=NULL WHERE user_id=?", (user_id,))
    return True, f"🎨 {KIND_FA[kind]} برداشته شد."
