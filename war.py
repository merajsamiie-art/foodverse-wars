# ⚔️ War Engine — نبرد ارتش‌ها: استراتژیک + مرگ + محافظت
import random

import army
import db
import perf
import player
from config import (CD_WAR, WAR_STEAL_PCT, TREASURY_PROTECT, LOSS_WIN, LOSS_LOSE,
                    XP_WAR_WIN, XP_WAR_LOSS)
from registry import UNITS, ITEMS, res_name


# ⚖️ مثلث برتری: فست‌فود > شیرینی > سبزیجات > فست‌فود | میو و عجیب خنثی
COUNTERS = dict(fastfood="candy", candy="veggie", veggie="fastfood")
CTYPE_FA = dict(fastfood="فست‌فود", candy="شیرینی", veggie="سبزیجات",
                meow="میو", weird="عجیب")


def _counter_bonus(attacker_uid: int, defender_uid: int) -> tuple[float, str]:
    """ترکیب درست ارتش = برتری واقعی. → (بونوس، توضیح کوتاه)"""
    a, d = army.army_of(attacker_uid), army.army_of(defender_uid)
    a_n, d_n = sum(a.values()) or 1, sum(d.values()) or 1
    a_t, d_t = {}, {}
    for uid, n in a.items():
        t = UNITS[uid].get("ctype", "")
        a_t[t] = a_t.get(t, 0) + n
    for uid, n in d.items():
        t = UNITS[uid].get("ctype", "")
        d_t[t] = d_t.get(t, 0) + n
    adv = sum(n / a_n * d_t.get(COUNTERS.get(t, ""), 0)
              for t, n in a_t.items() if t in COUNTERS)
    disadv = sum(n / d_n * a_t.get(COUNTERS.get(t, ""), 0)
                 for t, n in d_t.items() if t in COUNTERS)
    bonus = max(-0.20, min(0.30, round(0.35 * (adv - disadv), 2)))
    if bonus > 0.05:
        return bonus, f"⚖️ برتری نوع ارتش: +{int(bonus * 100)}٪"
    if bonus < -0.05:
        return bonus, f"⚖️ ضعف نوع ارتش: {int(bonus * 100)}٪"
    return 0.0, ""


def _defense_bonus(user_id: int) -> float:
    return 0.04 * army.blds_cached(user_id).get("defense", 0)


def _ally_def_bonus(user_id: int) -> float:
    m = db.db().one("SELECT alliance_id FROM ally_members WHERE user_id=?", (user_id,))
    if not m:
        return 0.0
    n = db.db().one("SELECT COUNT(*) c FROM ally_members WHERE alliance_id=?",
                    (m["alliance_id"],))["c"]
    return min(0.15, max(0, n - 1) * 0.05)


def _use_boost(user_id: int, effect: str) -> float:
    for iid, it in ITEMS.items():
        if it.get("kind") == "booster" and it.get("effect") == effect:
            if player.take_item(user_id, iid, 1):
                return it["val"]
    return 0.0


def declare(attacker_uid: int, defender_uid: int) -> tuple:
    A = player.get(attacker_uid)
    D = player.get(defender_uid)
    if not A or not D:
        return False, "⚔️ هر دو بازیکن باید ثبت‌شده باشند."
    if attacker_uid == defender_uid:
        return False, "⚔️ جنگ با خودت؟ فقط در فوودورس."
    from config import KING_UID
    if defender_uid == KING_UID:
        return False, ("👑 <b>پادشاه را نمی‌توان هدف گرفت!</b>\n"
                       "🫡 دست بزنید و عقب بروید — خشم آشپزخانه‌ی مرکزی داغ است.")
    if A["banned"] or D["banned"]:
        return False, "🚫 این بازیکن محروم است."
    if player.is_dead(A):
        return False, "💀 مردگان جنگ نمی‌توانند — کمی صبر کن."
    if player.is_dead(D):
        return False, "💀 هدف همین حالا مرده است."
    if player.is_protected(D):
        return False, "🛡 این بازیکن زیر محافظت است."
    if player.on_cd(attacker_uid, "war"):
        return False, f"⏳ ارتشت در حال تجدید قواست — {player.cd_left(attacker_uid, 'war')} ثانیه."

    with perf.key_lock(("war", attacker_uid, defender_uid)):
        a_stats, d_stats = army.army_stats(attacker_uid), army.army_stats(defender_uid)
        if a_stats["total"] < 3:
            return False, "🪖 حداقل ۳ سرباز لازم است: «جذب برگر ۳»"
        player.set_cd(attacker_uid, "war", CD_WAR)
        player.break_protection(attacker_uid)   # مهاجم محافظتش را می‌بازد

        # ─── محاسبه‌ی تاکتیکی ───
        eq_a, eq_d = army._equip_bonus(attacker_uid), army._equip_bonus(defender_uid)
        tr_a = army._training_bonus(attacker_uid)
        dfn_d = _defense_bonus(defender_uid)
        ally_d = _ally_def_bonus(defender_uid)

        c_bonus, c_txt = _counter_bonus(attacker_uid, defender_uid)
        atk = a_stats["atk"] * (1 + tr_a + eq_a["atk"] + _use_boost(attacker_uid, "war_dmg") + max(0, c_bonus))
        dfn = d_stats["df"] * (1 + dfn_d + eq_d["df"] + ally_d + max(0, -c_bonus))
        a_hp = a_stats["hp"] * (1 + eq_a["df"])
        d_hp = d_stats["hp"] * (1 + eq_d["df"] + ally_d)

        speed_edge = (a_stats["spd_avg"] - d_stats["spd_avg"]) / 20
        crit_a = a_stats["crit"]

        rounds = []
        a_pool, d_pool = a_hp, d_hp
        for rd in range(1, 5):
            if d_pool <= 0 or a_pool <= 0:
                break
            dmg = atk * random.uniform(0.85, 1.15) * ((1 + speed_edge) if rd == 1 else 1)
            if random.random() < crit_a:
                dmg *= 1.6
                rounds.append(f"دور {rd}: 💥 ضربه‌ی مرگبار")
            eff = max(dmg * 0.25, dmg - dfn * 0.8)
            d_pool -= eff
            if d_stats["medic"]:
                heal = d_stats["medic"] * UNITS["broccoli"]["heal"] * random.uniform(0.5, 1.0)
                d_pool = min(d_hp, d_pool + heal)
            if d_pool > 0:
                back = d_stats["atk"] * random.uniform(0.7, 1.1) * (1 - min(0.3, speed_edge))
                a_pool -= max(back * 0.25, back - a_stats["df"] * 0.6)
            rounds.append(f"دور {rd}: ⚔️ {eff:.0f}")

        a_win = d_pool <= 0 and a_pool > 0
        draw = (d_pool <= 0 and a_pool <= 0) or (d_pool > 0 and a_pool > 0)

        if draw:
            losses = army.apply_losses(attacker_uid, 0.10)
            army.apply_losses(defender_uid, 0.10)
            player.gain_xp(attacker_uid, XP_WAR_LOSS)
            player.gain_xp(defender_uid, XP_WAR_LOSS)
            return True, (f"⚔️ <b>نبرد مساوی!</b> {A['avatar']} ↔ {D['avatar']}\n"
                          f"هر دو ارتش عقب نشستند. تلفات مهاجم: {sum(losses.values())}")

        winner, loser = (attacker_uid, defender_uid) if a_win else (defender_uid, attacker_uid)
        wl = army.apply_losses(winner, random.uniform(*LOSS_WIN))
        ll = army.apply_losses(loser, random.uniform(*LOSS_LOSE))

        # غنیمت از منابع بازنده + محافظت خزانه
        L = player.get(loser)
        tlv = db.db().one("SELECT level FROM buildings WHERE user_id=? AND bld='treasury'", (loser,))
        protect = 1 - min(0.6, TREASURY_PROTECT * (tlv["level"] if tlv else 0))
        steal = {}
        for r in ("meat", "cheese", "sauce", "potato", "metal", "crystal"):
            amt = round(L[r] * WAR_STEAL_PCT * protect * random.uniform(0.6, 1.0), 1)
            if amt >= 1:
                steal[r] = amt
        fc_steal = round(L["fc"] * 0.10 * protect, 1)
        with db.db().tx():
            upd = {k: round(L[k] - v, 1) for k, v in steal.items()}
            if fc_steal >= 1:
                upd["fc"] = round(L["fc"] - fc_steal, 1)
            player.update(loser, **upd)
            player.grant(winner, fc=fc_steal, **steal)

        # 💀 مرگ بازنده + شکستن کنترل‌های اینفکتدش
        import infected
        infected.break_control_of(loser)
        death = player.die(loser, killer_name=player.get(winner)["name"])
        Wn = player.get(winner)
        player.update(winner, wins=Wn["wins"] + 1)
        player.gain_xp(winner, XP_WAR_WIN)
        player.gain_xp(loser, XP_WAR_LOSS)
        if winner == attacker_uid:
            player.dtrack(attacker_uid, "war_wins")

        st = " ".join(res_name(k) + f" {v:.0f}" for k, v in steal.items()) or "هیچی"
        Wp, Lp = player.get(winner), player.get(loser)
        drop_txt = " ".join(res_name(k) + f" {v:.0f}" for k, v in death["drop"].items())
        msg = (f"⚔️ <b>نبرد فوودورس</b>\n"
               f"{Wp['avatar']} <b>{Wp['name']}</b> 🏆 شکست داد {Lp['avatar']} <b>{Lp['name']}</b>\n"
               f"{' | '.join(rounds[:3])}\n"
               + (c_txt + "\n" if c_txt else "") +
               f"💀 تلفات: برنده {sum(wl.values())} | بازنده {sum(ll.values())}\n"
               f"🎒 غنیمت: {st}" + (f" + 🪙 {fc_steal:.0f} فودکوین" if fc_steal >= 1 else "") + "\n"
               f"☠️ <b>{Lp['name']} از پا درآمد</b> — {death['minutes']} دقیقه مرگ، بعدش ۵ دقیقه محافظت.\n"
               f"📉 افت زمینی: {drop_txt or '—'}")
        return True, msg
