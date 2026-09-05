# 🧟 Infected — باسِ اسیرشده: قدرت شخصی، کنترل بازیکن‌ها، پنجره‌ی سه‌روزه
import json
import random

import db
import perf
import player
from config import (INFECTED_CONTROL_H, INFECTED_COST_FC, INFECTED_LEVEL,
                    INFECTED_RAID_CD, INFECTED_TTL, INFECTED_WINDOW)
from registry import BOSSES, res_name


def get(user_id: int) -> dict | None:
    """اینفکتدِ فعال؛ اگر تمام شده باشد، همین‌جا آزادش می‌کند (باس به استخر برمی‌گردد)."""
    r = db.db().one("SELECT * FROM infected WHERE user_id=?", (user_id,))
    if not r:
        return None
    if (r["expires_at"] or 0) <= db.now():
        _release(dict(r))
        return None
    return dict(r)


def _release(inf: dict):
    """انقضای اینفکتد: باس به استخر دنیا برمی‌گردد و کنترل‌ها می‌شکند."""
    db.db().ex("DELETE FROM infected WHERE user_id=?", (inf["user_id"],))
    db.db().ex("UPDATE accounts SET controlled_by=0, controlled_until=0 WHERE controlled_by=?",
               (inf["user_id"],))
    if inf.get("world_chat"):
        _pool_add(inf["world_chat"], inf["boss_id"])
    perf.invalidate_player(inf["user_id"])


def _pool(chat_id: int) -> list:
    w = db.db().one("SELECT boss_pool FROM worlds WHERE chat_id=?", (chat_id,))
    try:
        pool = json.loads(w["boss_pool"]) if w and w["boss_pool"] else []
    except Exception:
        pool = []
    if not pool:                      # استخر خالی = همه‌ی باس‌ها آزاد
        pool = list(BOSSES)
    return pool


def _pool_add(chat_id: int, boss_id: str):
    pool = _pool(chat_id)
    if boss_id not in pool:
        pool.append(boss_id)
    db.db().ex("UPDATE worlds SET boss_pool=? WHERE chat_id=?", (json.dumps(pool), chat_id))


def _pool_remove(chat_id: int, boss_id: str):
    pool = [b for b in _pool(chat_id) if b != boss_id] or list(BOSSES)
    db.db().ex("UPDATE worlds SET boss_pool=? WHERE chat_id=?", (json.dumps(pool), chat_id))


def last_kill(chat_id: int) -> dict:
    r = db.db().one("SELECT v FROM kv WHERE k=?", (f"bosskill:{chat_id}",))
    return json.loads(r["v"]) if r else {}


def capture(user_id: int, chat_id: int) -> tuple:
    """«اینفکت» — اسیرکردن باسی که همین حالا گروه کشته است (فقط آسیب‌برتر)."""
    p = player.get(user_id)
    if not p:
        return False, "👤 اول «شروع» بزن."
    inf = get(user_id)
    if inf:
        b = BOSSES[inf["boss_id"]]
        left = int((inf["expires_at"] - db.now()) / 3600) + 1
        return False, (f"🧟 از قبل {b['emoji']} {b['name']} را اسیر داری "
                       f"({left} ساعت مانده به فرارش).")
    k = last_kill(chat_id)
    t = db.now()
    if not k or t - k.get("at", 0) > INFECTED_WINDOW:
        return False, ("🧟 اسیرکردن فقط تا ۱۰ دقیقه بعد از سقوط باس ممکن است — "
                       "و فقط برای کسی که بیشترین آسیب را زده.")
    if k.get("top") != user_id:
        return False, "🧟 فقط آسیب‌برترِ آن نبرد می‌تواند باس را اسیر کند."
    if (p["level"] or 1) < INFECTED_LEVEL:
        return False, f"🧟 برای اسیرکردن باس، سطح {INFECTED_LEVEL} لازم است."
    if p["fc"] < INFECTED_COST_FC:
        return False, f"🧟 اسیرکردن {INFECTED_COST_FC:,} فودکوین می‌خواهد."
    bid = k["boss_id"]
    if bid not in _pool(chat_id):
        return False, "🧟 این باس همین حالا در استخرِ آزادِ این دنیا نیست."
    b = BOSSES[bid]
    tier = k.get("tier", 1)
    with db.db().tx():
        player.update(user_id, fc=p["fc"] - INFECTED_COST_FC)
        db.db().ex("""INSERT OR REPLACE INTO infected
                      (user_id, boss_id, tier, world_chat, captured_at, expires_at, raid_cd)
                      VALUES(?,?,?,?,?,?,0)""",
                   (user_id, bid, tier, chat_id, t, t + INFECTED_TTL))
    _pool_remove(chat_id, bid)        # تا وقتی اسیر توست، در ریدهای این دنیا نیست
    perf.invalidate_player(user_id)
    hours = int(INFECTED_TTL / 3600)
    return True, (f"🧟 <b>اسیر شد!</b>\n"
                  f"{b['emoji']} {b['name']} حالا اینفکتدِ توست.\n"
                  f"⚙️ بونوس قدرت ارتش: +{tier * 8}٪\n"
                  f"🗡 «هجوم [بازیکن]» — غارت و کنترل\n"
                  f"⏳ تا {hours} ساعت بعد باید تازه‌اش کنی، وگرنه آزاد می‌شود "
                  f"و به ریدهای آزادِ این دنیا برمی‌گردد.")


def power_bonus(user_id: int) -> float:
    inf = get(user_id)
    if not inf:
        return 0.0
    from config import INFECTED_POWER_BONUS
    return inf["tier"] * INFECTED_POWER_BONUS


def raid(attacker_uid: int, target_uid: int) -> tuple:
    """«هجوم [بازیکن]» — اینفکتد را به سرِ کسی بفرست: غارت + کنترلِ ساعتی."""
    A = player.get(attacker_uid)
    D = player.get(target_uid)
    if not A or not D:
        return False, "🎯 چنین بازیکنی نیست."
    if attacker_uid == target_uid:
        return False, "🧟 اینفکتدت خودت را هم می‌بلعد؛ نه."
    from config import KING_UID
    if target_uid == KING_UID:
        return False, "👑 پادشاه را حتی هیولاها لمس نمی‌کنند — دست بزنید و عقب!"
    inf = get(attacker_uid)
    if not inf:
        return False, "🧟 اینفکتد فعالی نداری. باسِ سقوط‌کرده‌ی گروه را اسیر کن: «اینفکت»"
    if player.on_cd(attacker_uid, "inf_raid"):
        return False, f"⏳ اینفکتدت در حال بازیابی است — {player.cd_left(attacker_uid, 'inf_raid') // 3600 + 1} ساعت."
    if player.is_dead(D):
        return False, "💀 هدف همین حالا مرده است."
    if player.is_protected(D):
        return False, "🛡 هدف زیر محافظت است."
    if (D["controlled_by"] or 0) and (D["controlled_until"] or 0) > db.now():
        return False, "🎯 این بازیکن همین حالا زیر کنترلِ دیگری است."
    b = BOSSES[inf["boss_id"]]
    # ⚔️ سخت‌شدن بازی: هدفِ قوی‌تر می‌تواند اینفکتد را پس بزند (۳۵٪)
    import army as _army
    if _army.army_power(target_uid) > _army.army_power(attacker_uid) * 1.5:
        if random.random() < 0.35:
            db.db().ex("DELETE FROM infected WHERE user_id=?", (attacker_uid,))
            perf.invalidate_player(attacker_uid)
            return False, (f"🧟💥 <b>هجوم شکست خورد!</b>\n"
                           f"{D['avatar']} <b>{D['name']}</b> ارتش قوی‌تری داشت — "
                           f"{b['emoji']} {b['name']} را پس زد و آزاد شد!\n"
                           f"⚠️ اینفکتدت رفت — باس بعدی را دوباره اسیر کن.")
    hours = INFECTED_CONTROL_H.get(inf["tier"], 4)
    # غارت کوچک و سقف‌دار
    steal_res = random.choice(("meat", "cheese", "sauce", "potato", "metal"))
    amt = min(round((D[steal_res] or 0) * 0.04, 1), 250)
    fc_steal = min(round((D["fc"] or 0) * 0.03, 1), 200)
    t = db.now()
    upd = {"controlled_by": attacker_uid, "controlled_until": t + hours * 3600}
    if amt > 0:
        upd[steal_res] = round(D[steal_res] - amt, 1)
    if fc_steal > 0:
        upd["fc"] = round(D["fc"] - fc_steal, 1)
    player.update(target_uid, **upd)
    grant = {}
    if amt > 0:
        grant[steal_res] = amt
    if fc_steal > 0:
        grant["fc"] = fc_steal
    if grant:
        player.grant(attacker_uid, **grant)
    player.set_cd(attacker_uid, "inf_raid", INFECTED_RAID_CD)
    loot_txt = " ".join(res_name(k) + f" {v:.0f}" for k, v in grant.items()) or "هیچی"
    return True, (f"🧟 <b>هجوم اینفکتد!</b>\n"
                  f"{A['avatar']} <b>{A['name']}</b>، {b['emoji']} {b['name']} را فرستاد سراغ "
                  f"{D['avatar']} <b>{D['name']}\n"
                  f"🎒 برداشتِ اولیه: {loot_txt}\n"
                  f"🎯 <b>{D['name']} تا {hours} ساعت کنترل می‌شود</b> — "
                  f"۱۵٪ تولیدش به {A['name']} می‌رسد.\n"
                  f"💔 شکستِ {A['name']} در هر جنگی، کنترل را می‌شکند.")


def break_control_of(controller_uid: int):
    """اگر کنترل‌کننده در جنگ ببازد، همه‌ی کنترل‌هایش می‌شکند."""
    db.db().ex("UPDATE accounts SET controlled_by=0, controlled_until=0 WHERE controlled_by=?",
               (controller_uid,))


def cleanup():
    """پاک‌سازی دوره‌ای انقضاها (هر ساعت از موتور رویداد)."""
    rows = db.db().q("SELECT * FROM infected WHERE expires_at<=?", (db.now(),))
    for r in rows:
        _release(dict(r))
    db.db().ex("UPDATE accounts SET controlled_by=0, controlled_until=0 "
               "WHERE controlled_until>0 AND controlled_until<=?", (db.now(),))


def status(user_id: int) -> tuple:
    p = player.get(user_id)
    if not p:
        return False, "👤 اول «شروع» بزن."
    inf = get(user_id)
    lines = ["🧟 <b>اینفکتد</b>", ""]
    if inf:
        b = BOSSES[inf["boss_id"]]
        h_left = int((inf["expires_at"] - db.now()) / 3600) + 1
        lines += [f"{b['emoji']} <b>{b['name']}</b> — تیر {inf['tier']}",
                  f"⚙️ بونوس قدرت ارتش: +{inf['tier'] * 8}٪",
                  f"⏳ {h_left} ساعت تا فرار — تا آن موقع باسِ تازه‌ای اسیر کن",
                  "🗡 «هجوم [بازیکن]» — غارت + کنترلِ ساعتی"]
    else:
        lines += ["فعالی نداری.",
                  "باسِ گروه را بکُش؛ اگر آسیب‌برتر باشی، تا ۱۰ دقیقه فرصت داری: «اینفکت»"]
    if (p["controlled_by"] or 0) and (p["controlled_until"] or 0) > db.now():
        c = player.get(p["controlled_by"])
        h = int((p["controlled_until"] - db.now()) / 3600) + 1
        if c:
            lines += ["", f"🎯 <b>تو زیر کنترلِ {c['avatar']} {c['name']} هستی</b> "
                          f"({h} ساعت مانده) — ۱۵٪ تولیدت می‌رود سمت او.",
                          "💥 اگر او در جنگی ببازد، کنترل می‌شکند."]
    return True, "\n".join(lines)
