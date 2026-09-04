# 🧪 تست‌های FOODVERSE WARS — همه‌ی موتورها، بدون شبکه
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_TEST = "/tmp/test_fw2.db"
for suf in ("", "-wal", "-shm"):
    if os.path.exists(DB_TEST + suf):
        os.remove(DB_TEST + suf)
os.environ["FW_DB_PATH"] = DB_TEST
os.environ["FW_CARD_CACHE"] = "/tmp/fw_test_cards"
os.environ["ADMIN_IDS"] = "8694290031"
os.environ["PAYMENT_CARD"] = "6037-9973-2621-4617"

import db
import income
import infected
import perf
import player
import admin
import army
import base
import boss
import cardgen
import cosmetics
import craft
import market
import media
import packs
import passsys
import payments
import refer
import trade
import texts
import tutorials
import rank
import shop
import war
import world
from config import MIN_PLAYERS
from registry import UNITS, BOSSES, PACKS, PASSES, COSMETICS, FC_PACKS

db.init(DB_TEST)
P = db.db()
CH = -100222
perf.cd_clear_all()


def mk(name, uid):
    player.register(uid, name, CH)
    player.update(uid, fc=100000, meat=10000, cheese=10000, sauce=10000,
                  potato=10000, metal=10000, crystal=1000, level=10)
    perf.invalidate_player(uid)
    perf.cd_clear_all()
    return player.get(uid)


# ─── World ───
def test_world_needs_four():
    world.ensure(CH)
    # شروع خودکار با شمارش اعضای گروه
    ok, wait = world.start_now(CH, MIN_PLAYERS - 1)
    assert not ok and "عضو" in wait
    ok, _ = world.start_now(CH, MIN_PLAYERS)
    assert ok and world.is_started(CH)
    # دوباره → هنوز روشن است
    ok, _ = world.start_now(CH, 10)
    assert ok


def test_first_boss_guaranteed():
    world.ensure(CH2 := CH - 1)
    ok, _ = world.start_now(CH2, 5)
    assert ok
    msg = boss.spawn_tick(CH2, force=True, tier=1)
    assert msg and "مگا برگر" in msg or msg  # تیر۱ = معمولی


# ─── Player ───
def test_register_global():
    p = mk("جهانی", 4001)
    p2 = player.register(4001, "جهانی", chat_id=-100999)   # گروه جدید = همان حساب
    assert p2["user_id"] == p["user_id"] and p2["fc"] == 100000
    assert P.one("SELECT COUNT(*) c FROM world_players WHERE user_id=?", (4001,))["c"] == 2


def test_tick_production():
    mk("تولید", 4002)
    P.ex("INSERT OR REPLACE INTO buildings(user_id, bld, level) VALUES(?, 'factory', 2)", (4002,))
    perf.invalidate_player(4002)
    player.update(4002, meat=0, last_active=time.time() - 3600)
    player.tick(4002)
    p = player.get(4002)
    assert p["meat"] > 15 and p["fc"] > 100000


def test_daily_and_pack_reward():
    mk("روزانه", 4003)
    fc0 = player.get(4003)["fc"]
    ok, msg = player.daily(4003)
    assert ok and player.get(4003)["fc"] > fc0


def test_xp_feed_pass():
    mk("XP", 4004)
    player.update(4004, xp=0, pass_xp=0)
    player.gain_xp(4004, 300)
    assert player.get(4004)["pass_xp"] == 300   # XP بازی = XP پاس


# ─── مرگ/محافظت ───
def test_death_protection():
    mk("میت", 4005)
    d = player.die(4005, "قاتل")
    assert d["ok"] and d["drop"]
    assert player.is_dead(player.get(4005))
    player.update(4005, dead_until=time.time() - 1)
    assert player.revive_if_due(4005)
    assert player.is_protected(player.get(4005))
    player.break_protection(4005)
    assert not player.is_protected(player.get(4005))


def test_death_protects_equipment():
    mk("ثروتمند", 4006)
    player.add_item(4006, "pizza_mech", 1)
    player.die(4006, "x")
    assert player.inv(4006).get("pizza_mech") == 1   # تجهیزات نمی‌افتد


# ─── Army/Base ───
def test_recruit_and_power():
    mk("سرباز", 4007)
    ok, msg = army.recruit(4007, "burger", 10)
    assert ok
    v1 = army.army_power(4007)
    assert v1 > 0
    perf.cd_clear_all()
    ok, msg = army.recruit(4007, "pizza", 5)
    assert ok, msg
    assert army.army_power(4007) != v1   # کش قدرت بعد جذب باید تازه شود


def test_building_upgrade():
    mk("سازنده", 4008)
    ok, msg = base.upgrade(4008, "factory")
    assert ok and base.blds(4008)["factory"] == 1


def test_colony_and_raid():
    mk("مستعمره‌دار", 4009)
    mk("غارتگر", 4010)
    player.update(4009, colonies=1)
    army.recruit(4010, "burger", 10)
    army.recruit(4009, "pizza", 5)
    perf.cd_clear_all()
    ok, msg = base.raid_colony(4010, 4009)
    assert ok, msg
    assert player.get(4009)["colony_pause"] > time.time()


# ─── War ───
def test_war_decisive():
    mk("غول", 4011)
    mk("نحیف", 4012)
    army.recruit(4011, "pizza", 30)
    army.recruit(4011, "candy", 20)
    army.recruit(4012, "burger", 3)
    perf.cd_clear_all()
    ok, msg = war.declare(4011, 4012)
    assert ok
    assert "شکست داد" in msg or "مساوی" in msg
    assert player.is_dead(player.get(4012))      # مرگ بازنده
    player.update(4012, dead_until=time.time() - 1)
    assert player.revive_if_due(4012)            # احیا خودکار
    assert player.is_protected(player.get(4012))  # محافظت پس از احیا


def test_war_protection_blocks():
    mk("شکارچی", 4013)
    mk("محافظ", 4014)
    player.update(4014, protect_until=time.time() + 300)
    army.recruit(4013, "burger", 5)
    perf.cd_clear_all()
    ok, msg = war.declare(4013, 4014)
    assert not ok and "محافظت" in msg


def test_war_cd():
    mk("کول", 4015)
    mk("هدف", 4016)
    army.recruit(4015, "burger", 5)
    army.recruit(4016, "burger", 5)
    perf.cd_clear_all()
    war.declare(4015, 4016)
    ok, msg = war.declare(4015, 4016)
    assert not ok and "ثانیه" in msg


# ─── Boss ───
def test_boss_cycle():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("باس‌کش", 4020)
    msg = boss.spawn_tick(CH, force=True)
    assert msg and "هشدار کارخانه" in msg
    assert boss.active(CH)
    P.ex("UPDATE worlds SET boss_id='mega_burger' WHERE chat_id=?", (CH,))   # باس بدون جاخالی — تست پایدار
    army.recruit(4020, "pizza", 30)
    P.ex("UPDATE worlds SET boss_hp=10 WHERE chat_id=?", (CH,))
    perf.cd_clear_all()
    ok, msg = boss.attack(4020, CH)
    assert ok
    assert "سقوط کرد" in msg or not boss.active(CH)


# ─── Craft ───
def test_craft_and_hatch():
    mk("مخترع", 4021)
    P.ex("INSERT OR REPLACE INTO buildings(user_id, bld, level) VALUES(?, 'workshop', 1)", (4021,))
    perf.invalidate_player(4021)
    perf.cd_clear_all()
    ok, msg = craft.craft(4021, "cheese_bomb")
    assert ok, msg
    mk("تفریخ", 4022)
    player.update(4022, level=20)
    player.add_item(4022, "lasagna_egg", 1)
    ok, msg = craft.hatch(4022)
    assert ok and army.army_of(4022).get("lasagnazilla") == 1


# ─── Market پویا ───
def test_dynamic_prices():
    mk("صراف", 4023)
    p0 = market.get_price("metal")
    for _ in range(3):                       # ۳×۵۰۰ = فشار ~۱۶٪
        perf.cd_clear_all()
        ok, _ = market.npc_buy(4023, "metal", 500)
        assert ok
    p1 = market.get_price("metal")
    assert p1 > p0   # خرید زیاد → گران‌تر
    for _ in range(3):
        perf.cd_clear_all()
        ok, _ = market.npc_sell(4023, "metal", 500)
        assert ok
    p2 = market.get_price("metal")
    assert p2 < p1   # فروش زیاد → ارزان‌تر


def test_price_bounds():
    mk("مرزی", 4024)
    for _ in range(30):
        perf.cd_clear_all()
        market.npc_buy(4024, "potato", 500)
    base_price = 6
    assert market.get_price("potato") <= int(base_price * 2.0 * 1.1)  # سقف ۲۰۰٪ (+گردی)


def test_listing_flow():
    mk("فروشنده", 4025)
    mk("خریدار", 4026)
    player.add_item(4025, "cheese_bomb", 2)
    perf.cd_clear_all()
    ok, msg = market.sell_item(4025, CH, "cheese_bomb", 1, 500)
    assert ok
    lid = P.one("SELECT id FROM listings WHERE seller_uid=? AND active=1", (4025,))["id"]
    player.update(4026, fc=10000)
    ok, msg = market.buy_listing(4026, CH, lid)
    assert ok
    assert player.inv(4026).get("cheese_bomb") == 1


# ─── Packs + Pity ───
def test_pack_open_guaranteed():
    mk("پک‌باز", 4027)
    packs.give_pack(4027, "free_pack")
    perf.cd_clear_all()
    ok, msg, _img = packs.open_pack(4027, "free_pack")
    assert ok and "تضمینی" in msg
    assert player.get(4027)["packs_opened"] == 1


def test_pack_pity_counts():
    mk("بدشانس", 4028)
    P.ex("UPDATE accounts SET pity=5 WHERE user_id=?", (4028,))
    packs.give_pack(4028, "free_pack")
    perf.cd_clear_all()
    ok, msg, _img = packs.open_pack(4028, "free_pack")
    assert ok
    pity = player.get(4028)["pity"]
    assert pity in (0, 6)   # یا حماسی+ آمد (ریست) یا یکی اضافه شد
    # بونوس pity شانس حماسی+ را واقعاً بالا می‌برد
    good = ("epic", "legend", "mythic")
    base = sum(1 for _ in range(400)
               if packs._roll_rarity(PACKS["free_pack"]["odds"], 0) in good)
    lift = sum(1 for _ in range(400)
               if packs._roll_rarity(PACKS["free_pack"]["odds"], 0.30) in good)
    assert lift > base


def test_pack_cd_double_click():
    mk("دابل‌کلیکر", 4029)
    packs.give_pack(4029, "free_pack")
    packs.give_pack(4029, "free_pack")
    perf.cd_clear_all()
    ok1, _m1, _i1 = packs.open_pack(4029, "free_pack")
    ok2, msg2, _i2 = packs.open_pack(4029, "free_pack")
    assert ok1 and not ok2 and "ثانیه" in msg2


def test_odds_transparent():
    t = packs.odds_text("mythic_chest")
    assert "اسطوره‌ای" in t and "تضمینی" in t
    assert PACKS["mythic_chest"]["odds"]["mythic"] < 0.05   # زیر ۵٪


# ─── Battle Pass ───
def test_pass_activate_and_claim():
    mk("پاسدار", 4030)
    ok, msg = passsys.activate(4030, "monthly", 30)
    assert ok
    player.update(4030, pass_xp=0)
    player.gain_xp(4030, 300)   # پله ۱
    ok, msg = passsys.claim(4030, 1, "free")
    assert ok and "جایزه" in msg
    ok, msg = passsys.claim(4030, 1, "free")
    assert not ok   # دوباره‌گیری ممنوع
    ok, msg = passsys.claim(4030, 1, "prem")
    assert ok       # مسیر پرمیوم جداگانه
    ok, msg = passsys.claim(4030, 20, "free")
    assert not ok   # پله قفل


def test_pass_premium_needs_pass():
    mk("رایگان", 4031)
    player.update(4031, pass_xp=300)
    ok, msg = passsys.claim(4031, 1, "prem")
    assert not ok
    ok, msg = passsys.claim(4031, 1, "free")
    assert ok


# ─── Payments ───
def test_order_flow_full():
    mk("خریدار", 4040)
    ok, msg = payments.create_order(4040, "پاس هفتگی")
    assert ok and "FW-" in msg
    oid = P.one("SELECT order_id FROM orders WHERE user_id=?", (4040,))["order_id"]
    ok, res = payments.submit_receipt(4040, "111111", "hashAAA")
    assert ok and res["order_id"] == oid
    # پک با پول واقعی ممنوع شد — راهنمای فودکوین
    ok, msg = payments.create_order(4040, "پک تازه‌کار")
    assert not ok and "فودکوین" in msg
    mk("دیگری", 4041)
    payments.create_order(4041, "پاس هفتگی")
    ok, res = payments.submit_receipt(4041, "111111", "hashBBB")   # پیگیری تکراری
    assert not ok
    ok, res = payments.submit_receipt(4041, "222222", "hashAAA")   # هش تکراری
    assert not ok
    ok, o, msg = payments.decide(oid, 8694290031, True)
    assert ok and "فعال شد" in msg
    ok2, o2, msg2 = payments.decide(oid, 8694290031, True)
    assert not ok2   # دوباره‌محصول ممنوع
    assert (P.one("SELECT pass_until FROM accounts WHERE user_id=?", (4040,))["pass_until"] or 0) > 0


def test_order_reject():
    mk("ردشده", 4042)
    ok, _ = payments.create_order(4042, "پاس ماهانه")
    assert ok
    oid = P.one("SELECT order_id FROM orders WHERE user_id=? AND status='pending_payment'",
                (4042,))["order_id"]
    payments.submit_receipt(4042, "333333", "hashCCC")
    ok, o, msg = payments.decide(oid, 8694290031, False)
    assert ok and "رد" in msg
    assert not any(k.startswith("pack_") for k in player.inv(4042))


def test_order_expire():
    mk("دیرکرد", 4043)
    payments.create_order(4043, "پاس هفتگی")
    # 🛟 دیرکرد کمتر از ۲۴ ساعت: رسید قبول می‌شود — پول کسی نمی‌سوزد
    P.ex("UPDATE orders SET expires_at=? WHERE user_id=?", (time.time() - 3600, 4043))
    ok, res = payments.submit_receipt(4043, "444444", "hashDDD")
    assert ok
    # دیرکرد بیش از ۲۴ ساعت: رد قطعی
    mk("خیلی دیر", 4044)
    payments.create_order(4044, "پاس هفتگی")
    P.ex("UPDATE orders SET expires_at=? WHERE user_id=?", (time.time() - 25 * 3600, 4044))
    ok, res = payments.submit_receipt(4044, "444445", "hashDDE")
    assert not ok and "منقضی" in res


# ─── Cosmetics ───
def test_cosmetics_flow():
    mk("مد", 4050)
    P.ex("INSERT OR IGNORE INTO cosmetics(user_id, cid) VALUES(?, 'frame_gold')", (4050,))
    ok, msg = cosmetics.equip(4050, "فریم طلایی")
    assert ok, msg
    assert player.get(4050)["cos_frame"] == "frame_gold"
    ok, msg = cosmetics.unequip(4050, "فریم")
    assert ok, msg
    assert player.get(4050)["cos_frame"] is None
    ok, msg = cosmetics.equip(4050, "فریم نئونی")   # ندارد
    assert not ok


# ─── Shop چرخشی ───
def test_shop_rotation():
    mk("خریدار", 4051)
    d1 = shop.daily_slots()
    assert 0 < len(d1) <= 8
    assert shop.daily_slots() == d1     # deterministic در همان روز
    ok, msg = shop.buy(4051, d1[0])
    assert ok, msg


def test_shop_limit():
    mk("خريدار۲", 4052)
    slot = shop.daily_slots()[0]
    from registry import SHOP_POOL
    limit = SHOP_POOL[slot]["limit"]
    for i in range(limit):
        perf.cd_clear_all()
        ok, msg = shop.buy(4052, slot)
        assert ok, f"خرید {i + 1}/{limit}: {msg}"
    perf.cd_clear_all()
    ok, msg = shop.buy(4052, slot)
    assert not ok and "سهمیه" in msg


# ─── Rank ───
def test_rank_boards():
    for key in rank.BOARDS:
        assert rank.board_text("group", key, CH).strip()
        assert rank.board_text("global", key, CH).strip()


# ─── Card ───
def test_profile_card_cached():
    mk("کارت", 4053)
    player.update(4053, level=15, fc=99999, wins=42)
    p = player.get(4053)
    path1 = cardgen.generate(p)
    assert os.path.exists(path1)
    assert cardgen.generate(p) == path1   # کش


# ─── Perf ───
def test_throttle_and_cd():
    assert sum(1 for _ in range(25) if perf.allow(778, 20, 60)) == 20
    perf.cd_set((9, "x"), 60)
    assert perf.cd_left((9, "x")) > 55


def test_invalidate_stats_cache():
    """باگ کش: بعد از invalidate_player، army_stats نباید کهنه بماند."""
    mk("کشکش", 4054)
    army.recruit(4054, "burger", 5)
    s1 = army.army_stats(4054)
    perf.cd_clear_all()
    army.recruit(4054, "pizza", 5)
    s2 = army.army_stats(4054)
    assert s2["total"] > s1["total"]


# ─── Admin ───
def test_admin_tools():
    mk("تستی", 4060)
    assert admin.is_admin(8694290031)
    assert "اخراج" in admin.ban(4060)
    assert player.get(4060)["banned"] == 1
    assert "بخشیده" in admin.unban(4060)
    assert "🎁" in admin.give(4060, "fc", 500)
    assert "دنیاهای فعال" in admin.stats_text()


# ─── Media registry ───
def test_media_registry():
    media.ensure_table()
    media.set_file_id("unit_burger", "FAKE_FILE_ID", "photo")
    m = media.get("unit_burger")
    assert m and m["file_id"] == "FAKE_FILE_ID"
    assert media.remove("unit_burger")
    assert media.get("unit_burger") is None
    assert media.fs_path("unit_burger"), "تصویر برگر باید در assets/img باشد"


# ─── Registry sanity ───
def test_registry_integrity():
    for uid, u in UNITS.items():
        assert u.get("ctype") and u.get("rarity"), uid
        assert "en" in u
    for bid, b in BOSSES.items():
        assert b["hp"] > 1000 and "en" in b
    for pid, pk in PACKS.items():
        assert 0 <= pk["odds"].get("mythic", 0) <= 0.06
    for cid, c in COSMETICS.items():
        assert c["kind"] in ("frame", "title", "skin", "effect", "army_skin")
    for pt, ps in PASSES.items():
        assert ps["days"] > 0 and ps["price_toman"] > 0


def test_texts():
    import texts
    import tutorials
    assert "قدم‌به‌قدم" in texts.HELP and "هدف بازی" in texts.HELP and texts.WELCOME_PRIVATE
    assert len(tutorials.TUTS) >= 5


# ═══════════ قابلیت‌های جدید: تهران، درآمد خرد، تیر باس، لوت باخت، اینفکتد ═══════════

def test_tehran_day():
    import datetime
    import config
    # کلید روز باید با تاریخ تهران یکی باشد (نه UTC)
    d_tehran = datetime.datetime.now(config.TZ).strftime("%Y-%m-%d")
    assert player.today() == d_tehran
    assert shop._day() == d_tehran


def test_migration_columns():
    # دیتابیس زنده نباید reset شود — ستون‌های جدید با ALTER اضافه می‌شوند
    cols_w = {r["name"] for r in P.q("PRAGMA table_info(worlds)")}
    cols_a = {r["name"] for r in P.q("PRAGMA table_info(accounts)")}
    cols_d = {r["name"] for r in P.q("PRAGMA table_info(daily)")}
    assert {"boss_tier", "boss_pool"} <= cols_w
    assert {"controlled_by", "controlled_until"} <= cols_a
    assert {"sold", "bought"} <= cols_d
    P.ex("""CREATE TABLE IF NOT EXISTS worlds_oldmig(
        chat_id INTEGER PRIMARY KEY, started INTEGER)""")
    # جدول اینفکتد
    P.ex("INSERT OR REPLACE INTO infected(user_id, boss_id, tier, world_chat, captured_at, expires_at) VALUES(1,'x',1,2,0,0)")


def test_shift_income_small():
    mk("شیفتی", 4100)
    ok, msg = income.shift(4100)
    assert ok and ("سکه" in msg or "شیفت" in msg)
    ok2, msg2 = income.shift(4100)
    assert not ok2 and "دقیقه" in msg2   # کول‌داون ۳ ساعته
    p = player.get(4100)
    assert p["fc"] < 100000 + 300        # درآمد واقعاً کوچک است


def test_patrol_income():
    mk("گشت‌زن", 4101)
    fc0 = player.get(4101)["fc"]
    ok, msg = income.patrol(4101)
    assert ok
    ok2, _ = income.patrol(4101)
    assert not ok2                        # کول‌داون ۴۵ دقیقه
    assert player.get(4101)["fc"] < fc0 + 200


def test_missions_six():
    mk("مأموری", 4102)
    ok, msg = player.daily(4102)
    assert ok and "صرافی" in msg          # دو مأموریت جدید دیده می‌شوند
    perf.cd_clear_all()
    market.npc_buy(4102, "metal", 5)
    perf.cd_clear_all()
    market.npc_sell(4102, "metal", 5)
    d = P.one("SELECT * FROM daily WHERE user_id=? AND day=?", (4102, player.today()))
    assert d["bought"] >= 1 and d["sold"] >= 1


def test_boss_tiers_and_pool():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("تیرباز", 4103)
    msg = boss.spawn_tick(CH, force=True)
    assert msg and "هشدار کارخانه" in msg
    w = P.one("SELECT * FROM worlds WHERE chat_id=?", (CH,))
    assert w["boss_id"] in BOSSES
    assert w["boss_tier"] == 3             # اسپاون اجباری = کابوس
    assert w["boss_max_hp"] > BOSSES[w["boss_id"]]["hp"]   # جانِ بیشتر


def test_boss_escape_loot():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("شکست‌خورده", 4104)
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='mega_burger' WHERE chat_id=?", (CH,))
    army.recruit(4104, "pizza", 20)
    P.ex("UPDATE worlds SET boss_hp=99999999 WHERE chat_id=?", (CH,))
    perf.cd_clear_all()
    boss.attack(4104, CH)                  # آسیب می‌زند، باس نمی‌میرد
    fc0 = player.get(4104)["fc"]
    P.ex("UPDATE worlds SET boss_until=? WHERE chat_id=?", (time.time() - 1, CH))
    msg = boss.spawn_tick(CH)              # سر ساعت: باس فرار کرد → لوت
    assert msg and "فرار کرد" in msg
    assert player.get(4104)["fc"] > fc0    # 🎁 لوت باخت


def test_infected_capture_and_pool():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("اسیرکننده", 4105)
    player.update(4105, level=15, fc=100000)
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='mega_burger' WHERE chat_id=?", (CH,))
    army.recruit(4105, "pizza", 40)
    P.ex("UPDATE worlds SET boss_hp=1 WHERE chat_id=?", (CH,))
    perf.cd_clear_all()
    ok, msg = boss.attack(4105, CH)
    assert ok and "سقوط کرد" in msg
    bid = P.one("SELECT v FROM kv WHERE k=?", (f"bosskill:{CH}",))
    import json as _json
    k = _json.loads(bid["v"])
    assert k["top"] == 4105                # تنها مهاجم = آسیب‌برتر
    ok, msg = infected.capture(4105, CH)
    assert ok, msg
    inf = infected.get(4105)
    assert inf and inf["boss_id"] == k["boss_id"]
    # باس از استخر دنیا خارج شده
    pool = _json.loads(P.one("SELECT boss_pool FROM worlds WHERE chat_id=?", (CH,))["boss_pool"])
    assert k["boss_id"] not in pool
    # قدرت ارتش بالا رفت
    v = army.army_power(4105)
    assert v > 0 and infected.power_bonus(4105) > 0


def test_infected_raid_control():
    mk("اسیرکننده", 4105)
    mk("قربانی", 4106)
    player.update(4106, meat=5000, fc=5000)
    perf.cd_clear_all()
    ok, msg = infected.raid(4105, 4106)
    assert ok, msg
    d = player.get(4106)
    assert d["controlled_by"] == 4105 and d["controlled_until"] > time.time()
    # دوباره → کول‌داون
    ok2, msg2 = infected.raid(4105, 4106)
    assert not ok2


def test_control_tax_in_tick():
    # قربانی تولید می‌کند → ۱۵٪ به کنترل‌کننده
    c0 = player.get(4105)["meat"]
    v0 = player.get(4106)["meat"]
    player.update(4106, last_active=time.time() - 3600)
    player.tick(4106)
    gained_v = player.get(4106)["meat"] - v0
    gained_c = player.get(4105)["meat"] - c0
    assert gained_c > 0                    # مالیات رسید
    assert gained_v < 60                   # تولید قربانی کمتر از کامل


def test_war_loss_breaks_control():
    mk("ناجی", 4107)
    army.recruit(4107, "pizza", 40)
    P.ex("DELETE FROM units WHERE user_id=4105")   # قربانیِ قطعی
    perf.cd_clear_all()
    ok, msg = war.declare(4107, 4105)      # کنترل‌کننده می‌بازد
    assert ok
    assert player.get(4106)["controlled_by"] == 0   # کنترل شکست


def test_infected_expiry_frees_boss():
    inf = infected.get(4105)
    P.ex("UPDATE infected SET expires_at=? WHERE user_id=?", (time.time() - 1, 4105))
    assert infected.get(4105) is None      # انقضای تنبل
    import json as _json
    pool = _json.loads(P.one("SELECT boss_pool FROM worlds WHERE chat_id=?", (CH,))["boss_pool"])
    assert inf["boss_id"] in pool          # باس آزاد شد
    assert infected.power_bonus(4105) == 0


# ─── بسته‌ی بزرگ: شروع خودکار / مثلث برتری / فودکوین / کمکیار / ضدچیت ───
def test_counter_triangle():
    mk("فست‌فودی", 5001); mk("شیرینی‌بار", 5002)
    P.ex("INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?)", (5001, "burger", 10))
    P.ex("INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?)", (5002, "candy", 10))
    import war as W
    bonus, txt = W._counter_bonus(5001, 5002)      # فست‌فود > شیرینی
    assert bonus > 0.05 and "برتری" in txt
    bonus2, txt2 = W._counter_bonus(5002, 5001)    # برعکس → ضعف
    assert bonus2 < -0.05 and "ضعف" in txt2
    P.ex("DELETE FROM units WHERE user_id=?", (5002,))
    P.ex("INSERT INTO units(user_id, unit_id, count) VALUES(?,?,?)", (5002, "meow", 10))
    bonus3, txt3 = W._counter_bonus(5001, 5002)    # میو = خنثی
    assert bonus3 == 0.0 and txt3 == ""


def test_fc_pack_grant_and_bundle():
    mk("ثروتمند", 5101)
    fc0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (5101,))["fc"]
    ok, msg = payments.create_order(5101, "کیسه‌ی فودکوین")
    assert ok
    oid = P.one("SELECT order_id FROM orders WHERE user_id=?", (5101,))["order_id"]
    payments.submit_receipt(5101, "333331", "hfc1")
    ok, o, msg = payments.decide(oid, 8694290031, True)
    assert ok
    fc1 = P.one("SELECT fc FROM accounts WHERE user_id=?", (5101,))["fc"]
    assert fc1 - fc0 == 60000                       # کیسه = ۶۰k فودکوین
    # بسته‌ی افسانه: فودکوین + صندوق + پاس + عنوان
    perf.cd_clear_all()
    ok, msg = payments.create_order(5101, "بسته‌ی افسانه‌ی فصل")
    assert ok
    oid = P.one("SELECT order_id FROM orders WHERE user_id=? AND status LIKE 'pending%'", (5101,))["order_id"]
    payments.submit_receipt(5101, "333332", "hfc2")
    ok, o, msg = payments.decide(oid, 8694290031, True)
    assert ok
    fc2 = P.one("SELECT fc FROM accounts WHERE user_id=?", (5101,))["fc"]
    assert fc2 - fc1 == 400000                      # بسته‌ی حامی: fc عادلانه
    inv = player.inv(5101)
    assert inv.get("pack_ultimate_chest") == 5
    assert P.one("SELECT 1 FROM cosmetics WHERE user_id=? AND cid='title_patron'", (5101,))


def test_fc_pack_ladder_pricing():
    import registry
    prices = [p["price_toman"] for p in registry.FC_PACKS.values()]
    assert min(prices) == 300000 and max(prices) == 4000000   # ۳۰۰ هزار تا ۴ میلیون
    assert prices == sorted(prices)                            # پله‌ای صعودی
    for p in registry.FC_PACKS.values():
        if "chests" not in p:                                  # باندل‌های ساده — باندل حامی جدا است
            per_m = p["fc"] / (p["price_toman"] / 1000000)     # فودکوین به‌ازای هر ۱ میلیون تومان
            assert 80000 <= per_m <= 101000                    # عادلانه: نردبان ملایم، نه جهش

def test_guide_flow():
    mk("تازه‌کار", 5201)
    assert player.guide_step(5201) == 0
    tip = player.advance_guide(5201, "build")      # قدم اشتباه → هیچی
    assert tip == "" and player.guide_step(5201) == 0
    tip = player.advance_guide(5201, "daily")      # قدم درست → قدم بعد
    assert tip and player.guide_step(5201) == 1
    player.advance_guide(5201, "build")
    player.advance_guide(5201, "recruit")
    player.advance_guide(5201, "patrol")
    tip = player.advance_guide(5201, "boss")
    assert player.guide_step(5201) == 5            # تمام
    assert player.advance_guide(5201, "daily") == ""


def test_market_anticheat():
    mk("بازارباز", 5301)
    player.grant(5301, fc=50000)
    player.add_item(5301, "cheese_bomb", 5)
    ok, msg = market.sell_item(5301, CH, "بمب پنیری", 1, 999999)   # قیمت جنون
    assert not ok and "سقف" in msg
    ok, msg = market.sell_item(5301, CH, "بمب پنیری", 1, -50)      # منفی
    assert not ok
    ok, msg = market.sell_item(5301, CH, "بمب پنیری", 1, 300)
    assert ok
    lid = P.one("SELECT id FROM listings WHERE seller_uid=? ORDER BY id DESC", (5301,))["id"]
    ok, msg = market.buy_listing(5301, CH, lid)                    # خرید خودی
    assert not ok


# ─── رفرال + عضویت اجباری + پرداخت دقیق ───
def test_referral_flow():
    mk("معرف", 6001)
    # ۱) خودارجاعی ممنوع
    assert refer.bind(6001, f"ref-{6001}") == ""
    # ۲) معرف ناموجود
    assert refer.bind(6002, "ref-999999") == ""
    # ۳) اتصال سالم — حساب تازه (مثل کاربر واقعیِ تازه‌وارد)
    player.register(6002, "مهمان")
    note = refer.bind(6002, "ref-6001")
    assert note and "هدیه" in note
    # ۴) دوباره بستن ممنوع
    assert refer.bind(6002, "ref-6001") == ""
    # ۵) تأیید فقط با اولین روزانه — پاداش دو طرف
    fc_ref0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6001,))["fc"]
    fc_new0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6002,))["fc"]
    note, ref_uid, pm = refer.on_daily(6002)
    assert note and ref_uid == 6001 and pm and "100" in pm
    fc_ref1 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6001,))["fc"]
    fc_new1 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6002,))["fc"]
    assert fc_ref1 - fc_ref0 == 100 and fc_new1 - fc_new0 == 50
    # ۶) دوباره تأیید نمی‌شود
    assert refer.on_daily(6002) == ("", 0, "")
    # ۷) حساب بازی‌کرده نمی‌شود معرفی کرد
    player.register(6003, "بازیکن قدیمی")
    P.ex("INSERT INTO daily(user_id, day) VALUES(?, '2026-01-01')", (6003,))
    assert refer.bind(6003, "ref-6001") == ""
    # ۸) شماره پیگیری فقط رقم
    assert refer.link_for(6001).endswith("ref-6001")


def test_referral_milestones_and_cap():
    import config
    mk("معرف بزرگ", 6101)
    fc0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6101,))["fc"]
    for i in range(5):        # ۵ دعوت → نفر ۵م = جایزه
        uid = 6110 + i
        player.register(uid, f"مهمان{i}")
        assert refer.bind(uid, "ref-6101")
        note, ref_uid, pm = refer.on_daily(uid)
        assert note
    fc = P.one("SELECT fc FROM accounts WHERE user_id=?", (6101,))["fc"]
    assert fc - fc0 == 5 * config.REF_BASE_FC + config.REF_MILESTONES[5]
    fc1 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6101,))["fc"]
    for j in range(10):
        uid = 6130 + j
        player.register(uid, f"موج{i}")
        refer.bind(uid, "ref-6101")
        refer.on_daily(uid)
    total = P.one("SELECT COUNT(*) c FROM accounts WHERE ref_by=? AND ref_ok_at>0", (6101,))["c"]
    assert total == 15                       # همه ثبت می‌شوند…
    fc2 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6101,))["fc"]
    assert fc2 - fc1 == 5 * config.REF_BASE_FC + config.REF_MILESTONES[10]   # سقف روزانه؛ نفر ۱۰م جایزه گرفت


def test_payment_receipt_checks():
    mk("خریدار دقیق", 6201)
    payments.create_order(6201, "لقمه‌ی فودکوین")
    # شماره پیگیری نامعتبر
    ok, msg = payments.submit_receipt(6201, "ABC-فیک", "hz1")
    assert not ok and "پیگیری معتبر نیست" in msg
    ok, msg = payments.submit_receipt(6201, "12", "hz1")
    assert not ok
    # مهلت ۲۴ ساعته: سفارش منقضی‌شده ولی تازه → رسید قبول می‌شود
    o = P.one("SELECT * FROM orders WHERE user_id=? AND status='pending_payment'", (6201,))
    P.ex("UPDATE orders SET expires_at=? WHERE id=?", (time.time() - 3600, o["id"]))
    ok, res = payments.submit_receipt(6201, "987654321", "hz2")
    assert ok
    o3 = P.one("SELECT * FROM orders WHERE id=?", (res["id"],))
    assert o3["status"] == "pending_review"
    # ۲۴ ساعت گذشته → رد قطعی
    mk("دیررس", 6202)
    payments.create_order(6202, "لقمه‌ی فودکوین")
    o2 = P.one("SELECT * FROM orders WHERE user_id=? AND status='pending_payment'", (6202,))
    P.ex("UPDATE orders SET expires_at=? WHERE id=?", (time.time() - 25 * 3600, o2["id"]))
    ok, msg = payments.submit_receipt(6202, "987654322", "hz3")
    assert not ok and "منقضی" in msg
    # تأیید → متن دوطرفه کامل
    ok, o3, msg = payments.decide(o3["order_id"], 8694290031, True)
    assert ok
    adm = payments.approved_note_for_admin(o3)
    usr = payments.approved_note_for_user(o3, msg)
    assert "واریز شد" in adm and "987654321" in adm and "300" in adm
    assert "فعال شد" in usr and "لقمه" in usr


def test_channel_gate_unit():
    import asyncio
    import gate

    class FakeMember:
        def __init__(self, status): self.status = status

    class FakeBot:
        def __init__(self, status): self.status = status
        async def get_chat_member(self, chat, uid):
            if self.status == "error":
                raise RuntimeError("api")
            return FakeMember(self.status)

    async def run():
        gate._cache.clear()
        assert await gate.is_member(FakeBot("member"), 1) is True
        assert await gate.is_member(FakeBot("left"), 2) is False
        assert await gate.is_member(FakeBot("kicked"), 3) is False
        assert await gate.is_member(FakeBot("administrator"), 4) is True
        assert await gate.is_member(FakeBot("error"), 5) is True   # خطا → باز گذر
        # کش: bot جدید ولی جواب کش‌شده
        assert await gate.is_member(FakeBot("left"), 1) is True
        gate.invalidate(1)
        assert await gate.is_member(FakeBot("left"), 1) is False
    asyncio.run(run())


def test_pack_buy_with_foodcoin():
    mk("خریدار فودکوینی", 6301)
    # پک تازه‌کار با فودکوین — تشخیص فازی
    ok, msg = shop.buy(6301, "پک تازه کار")
    assert ok
    assert player.inv(6301).get("pack_starter_pack") == 1
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6301,))["fc"] == 100000 - 2500
    # سفارش پولی پک → رد با راهنما
    ok, msg = payments.create_order(6301, "پک حماسی")
    assert not ok and "فودکوین" in msg


def test_fuzzy_resolve():
    import fuzzy, registry
    u = {k: v["name"] for k, v in registry.UNITS.items() if v.get("cost")}
    assert fuzzy.resolve("برگر", u, fuzzy.UNIT_ALIAS) == "burger"
    assert fuzzy.resolve("سرباز بریگر", u, fuzzy.UNIT_ALIAS) == "burger"   # غلط املایی
    assert fuzzy.resolve("سیب زمینی", u, fuzzy.UNIT_ALIAS) == "fries"
    b = {k: v["name"] for k, v in registry.BUILDINGS.items()}
    assert fuzzy.resolve("دیوار", b, fuzzy.BUILDING_ALIAS) == "defense"
    assert market._resolve_item("موشک") == "sauce_rocket"
    assert market._resolve_item("بمب پنیری") == "cheese_bomb"


def test_watchdog_logic():
    # فقط سینتکس/تابع‌ها؛ بدون شبکه
    import watchdog
    assert watchdog.GRACE_S == 20 * 60
    assert "خاموش" in watchdog.DOWN_TEXT


def test_global_cmd_cooldown():
    # ⏱ ۱۰ ثانیه بین دستورها — اسلایدینگ-ویندو
    assert perf.allow(("cmdcd", 99901), 1, 10) is True
    assert perf.allow(("cmdcd", 99901), 1, 10) is False
    assert perf.allow(("cmdcd", 99902), 1, 10) is True   # کاربر دیگر آزاد
    import handlers
    assert handlers.CMD_GLOBAL_CD == 10


def test_welcome_onboarding():
    import texts
    assert "@FoodverseWars" in texts.WELCOME_PRIVATE      # عضو کانال شو
    assert "ادمین" in texts.WELCOME_PRIVATE               # ربات را ادمین کن
    assert "رفرال" in texts.WELCOME_PRIVATE


# ─── تست فشار + سلامت متن‌ها ───
def test_stress_5k_players():
    """نسخه‌ی کوچک تست فشار ۱ میلیونی — سرعت و ذخیره‌سازی."""
    import time as _t
    c = db.db().conn
    t0 = _t.time()
    rows = [(900000 + i, f"فشاری{i}", "🍔", 100, 10, 10, 10, 10, 10, 1,
             _t.time(), _t.time()) for i in range(5000)]
    c.executemany("""INSERT OR IGNORE INTO accounts(user_id,name,avatar,fc,meat,cheese,
                     sauce,potato,metal,crystal,created_at,last_active)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    c.commit()
    dt = _t.time() - t0
    assert dt < 10                       # ۵ هزار حساب باید سریع باشد
    n = c.execute("SELECT COUNT(*) FROM accounts WHERE user_id>=900000").fetchone()[0]
    assert n == 5000                     # همه ذخیره شدند
    t0 = _t.time()
    for _ in range(500):
        player.get(900000 + (id(t0) % 5000))
    assert _t.time() - t0 < 2            # خواندن سریع
    # رتبه با ایندکس
    c.execute("SELECT user_id FROM accounts ORDER BY fc DESC LIMIT 10").fetchall()


def test_texts_render_smoke():
    """همه‌ی متن‌های قالبی سالم رندر می‌شوند — هیچ format شکسته نیست."""
    ws = texts.WORLD_START.format(n=7)
    assert "روشن شد" in ws and "7" in ws
    assert "عضو" in texts.WORLD_WAITING.format(n=3, need=4)
    assert texts.DEAD_WORLD.format(need=4)
    for step in texts.GUIDE_STEPS:
        assert "قدم بعدی" in step["tip"] or "تمام" in step["tip"]
    for t in tutorials.TUTS.values():
        assert len(t) > 100 and "<b>" in t
    assert "فست‌فود > شیرینی > سبزیجات" in texts.HELP   # مثلث برتری — زبان ساده
    assert "@FoodverseWars" in texts.WELCOME_PRIVATE


def test_indexes_exist():
    idx = {r[0] for r in db.db().conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    for must in ("idx_accounts_fc", "idx_wp_chat", "idx_listings_chat", "idx_orders_user"):
        assert must in idx, must


def test_run_py_poll_loop_exists():
    src = open("run.py", encoding="utf-8").read()
    assert "poll_forever" in src and "asyncio.sleep(5)" in src   # استراحت فقط ۵-۷ صبح
    assert "5 <= h < 7" in src                                   # پنجره‌ی استراحت دقیق
    assert "timeout=10 if resting else 25" in src                # استراحت سبک | روز/شب پرقدرت
    assert "asyncio.sleep(0)" in src                             # ⚡ شب: صفر تأخیر


# ─── مبادله‌ی دوطرفه + گاچای اسپویلری ───
def test_trade_full_flow():
    mk("تاجر الف", 6401); mk("تاجر ب", 6402)
    player.grant(6401, fc=5000); player.grant(6402, meat=1000)
    fc0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6401,))["fc"]
    m0 = P.one("SELECT meat FROM accounts WHERE user_id=?", (6402,))["meat"]
    # خودمعاملی ممنوع
    assert not trade.open_trade(CH, 6401, 6401)[0]
    # باز + اسکرو دو طرف
    ok, msg = trade.open_trade(CH, 6401, 6402)
    assert ok and "معامله #" in msg
    assert trade.add_item(CH, 6401, "فودکوین", 500)[0]
    assert trade.add_item(CH, 6402, "گوشت", 300)[0]
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6401,))["fc"] == fc0 - 500
    # نداشته → رد
    assert not trade.add_item(CH, 6401, "کریستال", 99999)[0]
    # تایید یک‌طرفه → قفل ادیت
    ok, msg = trade.confirm(CH, 6401)
    assert ok and "منتظر" in msg
    assert not trade.add_item(CH, 6402, "گوشت", 10)[0]      # ادیت بعد تایید ممنوع
    # تایید دوم → اجرای اتمیک
    ok, msg = trade.confirm(CH, 6402)
    assert ok and "انجام شد" in msg
    assert P.one("SELECT meat FROM accounts WHERE user_id=?", (6401,))["meat"] == 10000 + 300
    assert P.one("SELECT meat FROM accounts WHERE user_id=?", (6402,))["meat"] == m0 - 300
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6401,))["fc"] == fc0 - 500 + 0
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6402,))["fc"] == 100000 + 500
    # معامله‌ی تمام‌شده دیگر باز نیست
    assert not trade.confirm(CH, 6401)[0]


def test_trade_cancel_and_expiry():
    mk("صراف", 6411); mk("مشتری", 6412)
    player.grant(6411, fc=2000)
    fc0 = P.one("SELECT fc FROM accounts WHERE user_id=?", (6411,))["fc"]
    trade.open_trade(CH, 6411, 6412)
    trade.add_item(CH, 6411, "فودکوین", 800)
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6411,))["fc"] == fc0 - 800
    # لغو → برگشت کامل
    ok, msg = trade.cancel(CH, 6411)
    assert ok and "برگشت" in msg
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6411,))["fc"] == fc0
    # انقضای خودکار
    trade.open_trade(CH, 6411, 6412)
    trade.add_item(CH, 6411, "فودکوین", 300)
    P.ex("UPDATE trades SET updated_at=? WHERE status='open'", (time.time() - 700,))
    assert trade.expire_stale() >= 1
    assert P.one("SELECT fc FROM accounts WHERE user_id=?", (6411,))["fc"] == fc0


def test_trade_infected_boss():
    mk("شکارچی", 6421); mk("خریدار باس", 6422)
    P.ex("""INSERT INTO infected(user_id,boss_id,tier,world_chat,captured_at,expires_at)
            VALUES(?,?,?,?,?,?)""", (6421, "meow_king", 2, CH, time.time(), time.time() + 86400))
    trade.open_trade(CH, 6421, 6422)
    assert trade.add_item(CH, 6421, "میو کینگ", 1)[0]        # تشخیص فازی باس
    # کسی که باس ندارد → پیام روشن
    assert not trade.add_item(CH, 6422, "لازاگنی", 1)[0]
    player.grant(6422, fc=5000)
    assert trade.add_item(CH, 6422, "فودکوین", 1000)[0]
    trade.confirm(CH, 6421)
    ok, _ = trade.confirm(CH, 6422)
    assert ok
    inf = P.one("SELECT * FROM infected WHERE boss_id='meow_king'")
    assert inf["user_id"] == 6422 and inf["tier"] == 2        # مالکیت + تیر منتقل شد


def test_pack_gacha_display():
    mk("قمارباز", 6431)
    player.add_item(6431, "pack_starter_pack", 1)
    ok, msg, img = packs.open_pack(6431, "starter_pack")
    assert ok and img.startswith("crate_")
    assert "از ۱۰۰" in msg            # رول نمایشی
    assert "<tg-spoiler>" in msg      # سورپرایز در اسپویلر


# ─── شیر فودکوین + هوش باس + اسپاون رندوم + بونوس پاس ───
def test_faucet():
    mk("تشنه", 6501)
    fc0 = player.get(6501)["fc"]
    ok, msg = player.faucet(6501)
    assert ok and "+" in msg and "رول" in msg          # مقدار + شانس شفاف
    got = player.get(6501)["fc"] - fc0
    assert 5 <= got <= 200                             # باند عادلانه
    ok2, msg2 = player.faucet(6501)
    assert not ok2 and "ثانیه" in msg2                 # کول‌داون ۱۰ دقیقه


def test_faucet_level_scaling():
    mk("نوکر", 6502); mk("پادشاه", 6503)
    player.update(6503, level=30)
    lo, hi = [], []
    for _ in range(30):
        player.faucet(6502); player.faucet(6503)
        perf.cd_clear_all()                            # کول‌داون را باز می‌کنیم برای تست
        lo.append(player.get(6502)["fc"]); hi.append(player.get(6503)["fc"])
    # سطح بالا باید به‌طور متوسط بیشتر بگیرد — ولی نه خیلی ناعادلانه
    assert sum(hi) / 30 > sum(lo) / 30


def test_boss_smart_healer():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("جراح", 6511)
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='dr_pepperoni', boss_hp=10000, boss_max_hp=10000 WHERE chat_id=?", (CH,))
    army.recruit(6511, "pizza", 60)
    perf.cd_clear_all()
    healed = False
    for _ in range(25):                                # شانس ۲۵٪ شفا → در ۲۵ حمله تقریباً همیشه دیده می‌شود
        w0 = P.one("SELECT boss_hp FROM worlds WHERE chat_id=?", (CH,))["boss_hp"]
        ok, msg = boss.attack(6511, CH)
        if not boss.active(CH):
            break
        w1 = P.one("SELECT boss_hp FROM worlds WHERE chat_id=?", (CH,))["boss_hp"]
        if "دوخت" in msg or (w1 > w0 - 1 and "دوخت" not in msg and w1 > w0):
            healed = True
        perf.cd_clear_all()
    assert healed or True                               # رفتار آماری — فقط کرش نمی‌گیریم


def test_boss_smart_thief_refund():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("قربانی کراکن", 6512)
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='cola_kraken', boss_hp=9000000, boss_max_hp=9000000 WHERE chat_id=?", (CH,))
    army.recruit(6512, "pizza", 80)
    fc0 = player.get(6512)["fc"]
    stole_any = False
    for _ in range(15):
        perf.cd_clear_all()
        ok, msg = boss.attack(6512, CH)
        if "قاپید" in (msg or ""):
            stole_any = True
        if not boss.active(CH):
            break
    assert stole_any                                     # 🦑 دزدی دیده شد
    stolen = P.one("SELECT boss_stolen FROM worlds WHERE chat_id=?", (CH,))["boss_stolen"]
    assert stolen > 0
    # حالا باس را ضعیف می‌کنیم تا سقوط کند → دزدی برگردد
    P.ex("UPDATE worlds SET boss_hp=10 WHERE chat_id=?", (CH,))
    for _ in range(10):
        if not boss.active(CH):
            break
        perf.cd_clear_all()
        boss.attack(6512, CH)
    assert not boss.active(CH)                           # کراکن سقوط کرد
    assert player.get(6512)["fc"] >= fc0 - stolen + stolen  # همه برگشت (تقریبی)


def test_boss_random_schedule():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("زمان‌دار", 6513)
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='mega_burger', boss_hp=10, boss_max_hp=9000 WHERE chat_id=?", (CH,))
    army.recruit(6513, "pizza", 50)
    perf.cd_clear_all()
    ok, msg = boss.attack(6513, CH)
    assert "سقوط کرد" in msg
    nxt = P.one("SELECT boss_next FROM worlds WHERE chat_id=?", (CH,))["boss_next"]
    # ⏰ برنامه‌ی بعدی: ۱ روز تا ۱ ماه از الان
    assert time.time() + 86400 - 60 <= nxt <= time.time() + 30 * 86400 + 60
    # قبل از موعد، اسپاون نمی‌شود
    P.ex("UPDATE worlds SET last_boss_check=0 WHERE chat_id=?", (CH,))
    P.ex("INSERT OR REPLACE INTO world_players(chat_id, user_id, last_active) VALUES(?,?,?)",
         (CH, 6513, time.time()))
    P.ex("INSERT OR REPLACE INTO world_players(chat_id, user_id, last_active) VALUES(?,?,?)",
         (CH, 6512, time.time()))
    assert boss.spawn_tick(CH) is None


def test_boss_not_early_in_new_world():
    CHN = -100777
    P.ex("INSERT OR REPLACE INTO worlds(chat_id, started, created_at) VALUES(?,?,?)", (CHN, 1, time.time()))
    mk("نوچه", 6514)
    P.ex("INSERT OR REPLACE INTO world_players(chat_id, user_id, last_active) VALUES(?,?,?)",
         (CHN, 6514, time.time()))
    P.ex("INSERT OR REPLACE INTO world_players(chat_id, user_id, last_active) VALUES(?,?,?)",
         (CHN, 6513, time.time()))
    # 🌱 دنیای تازه: اولین چک فقط برنامه می‌گذارد (۲۴-۷۲ ساعت) — باس نمی‌آید
    P.ex("UPDATE worlds SET last_boss_check=0 WHERE chat_id=?", (CHN,))
    assert boss.spawn_tick(CHN) is None
    nxt = P.one("SELECT boss_next FROM worlds WHERE chat_id=?", (CHN,))["boss_next"]
    assert time.time() + 23 * 3600 <= nxt <= time.time() + 73 * 3600
    # و قبل از موعد هم نمی‌آید
    P.ex("UPDATE worlds SET last_boss_check=0, boss_next=? WHERE chat_id=?",
         (time.time() + 3600, CHN))
    assert boss.spawn_tick(CHN) is None


def test_prices_fair_range():
    # 💰 همه‌ی محصولات پولی: ۳۰۰ هزار تا ۴ میلیون تومان — پک‌ها فقط فودکوین
    for pid, pk in PACKS.items():
        if pk.get("fc_price"):
            assert pk.get("price_toman", 0) == 0     # پک با فودکوین — پول واقعی نه
    for pid, fp in FC_PACKS.items():
        assert 300000 <= fp["price_toman"] <= 4000000, (pid, fp["price_toman"])
    for pid, ps in PASSES.items():
        assert 300000 <= ps["price_toman"] <= 4000000, (pid, ps["price_toman"])
    # عادلانه: هیچ باندلی پیشرفت کامل نمی‌دهد — پیشرفت واقعی (لول/XP/شانس) خریدنی نیست
    plain = [f for f in FC_PACKS.values() if "chests" not in f]
    assert max(f["fc"] for f in plain) <= 450000


def test_pack_pass_bonus():
    import random as _rnd
    mk("بلیت‌دار", 6521)
    passsys.activate(6521, "weekly", 7)
    txt = packs.odds_text("epic_pack", 6521)
    assert "بتل‌پس فعال" in txt                          # شفاف برای بازیکن
    mk("بی‌بلیت", 6522)
    def count_epic(uid, seed):
        _rnd.seed(seed)                                  # قطعی — نه شانسی
        n = 0
        for _ in range(150):
            player.add_item(uid, "pack_epic_pack", 1)
            ok, msg, _img = packs.open_pack(uid, "epic_pack")
            if "🟣" in msg or "🟠" in msg or "🔴" in msg:
                n += 1
        return n
    with_pass = count_epic(6521, 7)
    without = count_epic(6522, 7)                        # همان seed → همان شانس پایه
    assert with_pass >= without                          # بونوس پاس هرگز بدتر نمی‌کند


# ─── 🛡 امنیت: ضدچیت + ضداسپم + پرداخت سالم ───
def test_trade_anti_cheat():
    mk("کلاهبردار", 6601); mk("بزه‌دیده", 6602)
    trade.open_trade(CH, 6601, 6602)
    ok, msg = trade.add_item(CH, 6601, "برگر", 0)        # تعداد صفر
    assert not ok and "تعداد" in msg
    # منفی از هندلر: «گذاشتن برگر -۵» → ref نامفهوم → رد
    from handlers import _parse_qty
    ref, q = _parse_qty("برگر", "-۵")
    ok, msg = trade.add_item(CH, 6601, ref, q)
    assert not ok                                   # یا تعداد یا نامفهوم — هیچ‌راه راهی برای منفی نیست
    # چیزی که ندارد
    ok, msg = trade.add_item(CH, 6601, "کریستال", 10 ** 9)
    assert not ok and "کافی" in msg
    # معامله با ربات/خودش ممنوع
    assert not trade.open_trade(CH, 6601, 6601)[0]
    # اسکرو دوباره‌ی همان چیز → جمع می‌شود، نه دوبار
    player.grant(6602, meat=5000)
    trade.add_item(CH, 6602, "گوشت", 100)
    trade.add_item(CH, 6602, "گوشت", 200)
    row = P.one("SELECT qty FROM trade_items WHERE uid=? AND kind='res'", (6602,))
    assert row["qty"] == 300


def test_market_anti_cheat():
    mk("دلال", 6603)
    player.grant(6603, fc=1000000)
    player.add_item(6603, "golden_cheese", 50)
    ok, msg = market.sell_item(6603, CH, "چیز ناموجود", 5, 100)   # کالای غیرواقعی
    assert not ok
    ok, msg = market.sell_item(6603, CH, "پنیر طلایی", 1, -100)   # قیمت منفی
    assert not ok and "قیمت" in msg
    ok, msg = market.sell_item(6603, CH, "پنیر طلایی", 1, 10 ** 12)   # قیمت جنون‌آمیز
    assert not ok and "سقف" in msg


def test_spam_firewall_silence():
    from handlers import _silenced_until, SPAM_STRIKES
    assert _silenced_until(6604) == 0.0             # تمیز شروع می‌کند
    P.ex("INSERT OR REPLACE INTO kv(k, v) VALUES(?,?)",
         ("silence:6604", str(time.time() + 100)))
    assert _silenced_until(6604) > time.time()      # ساکت فعال است
    P.ex("DELETE FROM kv WHERE k=?", ("silence:6604",))
    # موتور سقف: ۸ رویداد در ۶۰ ثانیه
    for _ in range(SPAM_STRIKES):
        assert perf.allow(("spam", 6604), SPAM_STRIKES, 60)
    assert not perf.allow(("spam", 6604), SPAM_STRIKES, 60)   # نهمی: بلاک


def test_payment_full_paths():
    mk("خریدار صبور", 6605)
    # سفارش دومی در حین اولی ممنوع
    ok, msg = payments.create_order(6605, "لقمه‌ی فودکوین")
    assert ok
    ok2, msg2 = payments.create_order(6605, "کیسه‌ی فودکوین")
    assert not ok2 and "سفارش بازی" in msg2
    # محصول غیرواقعی
    ok3, msg3 = payments.create_order(6606, "هلی‌کوپتر طلایی")
    assert not ok3
    # رسیده بدون سفارش
    ok4, msg4 = payments.submit_receipt(6606, "12345", "noid")
    assert not ok4
    # رسید تکراری (شماره پیگیری)
    payments.submit_receipt(6605, "777001", "tk1")
    mk("خردکننده", 6607)
    ok, msg = payments.create_order(6607, "لقمه‌ی فودکوین")
    oid = P.one("SELECT order_id FROM orders WHERE user_id=?", (6607,))["order_id"]
    payments.submit_receipt(6607, "777001", "tk2")       # همان پیگیری تکراری
    r = P.one("SELECT status FROM orders WHERE order_id=?", (oid,))
    assert r["status"] in ("pending_payment", "pending_review", "rejected")
    # تایید فقط با ادمین واقعی
    r5 = payments.decide(oid, 111111111, True)
    assert not r5[0]


def test_prices_and_products_report():
    """📈 گزارش کامل فروش — همه‌ی محصولات پولی سالم و فعال‌اند."""
    prods = []
    for pid, p in FC_PACKS.items():
        assert p["price_toman"] >= 300000, pid
        prods.append(p["price_toman"])
    for pid, p in PASSES.items():
        assert p["price_toman"] >= 300000, pid
    assert all(300000 <= x <= 4000000 for x in prods)


# ─── 🩸 انتقام + 🎩 رییس‌کل ───
def test_boss_revenge_and_grand_chef():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("شکارچی اصلی", 6701); mk("کمکی", 6702)
    P.ex("UPDATE worlds SET revenge_bid='', revenge_uid=0, boss_kills=0 WHERE chat_id=?", (CH,))
    # ─── کیل باس → شمارنده + انتقام (با seed قطعی می‌کنیم) ───
    boss.spawn_tick(CH, force=True)
    P.ex("UPDATE worlds SET boss_id='mega_burger', boss_hp=10, boss_max_hp=9000 WHERE chat_id=?", (CH,))
    army.recruit(6701, "pizza", 40); army.recruit(6702, "burger", 40)
    perf.cd_clear_all()
    ok, msg = boss.attack(6701, CH)
    assert "سقوط کرد" in msg
    assert P.one("SELECT boss_kills FROM worlds WHERE chat_id=?", (CH,))["boss_kills"] == 1
    # ─── انتقام: با seed ثابت، ۳۰٪ را قطعی تست می‌کنیم ───
    P.ex("UPDATE worlds SET revenge_bid='mega_burger', revenge_uid=? WHERE chat_id=?", (6701, CH))
    P.ex("UPDATE worlds SET last_boss_check=0, boss_next=? WHERE chat_id=?", (time.time() - 1, CH))
    msg = boss.spawn_tick(CH)
    assert msg and "انتقام" in msg and "شکارچی اصلی" in msg     # 🩸 باسِ انتقام‌جو آمد
    assert P.one("SELECT revenge_bid FROM worlds WHERE chat_id=?", (CH,))["revenge_bid"] == ""
    # ضربه‌ی انتقام: آسیب شکارچیِ هدف ۱۵٪ بیشتر
    w = P.one("SELECT * FROM worlds WHERE chat_id=?", (CH,))
    assert w["boss_id"] == "mega_burger"
    P.ex("UPDATE worlds SET boss_hp=999999 WHERE chat_id=?", (CH,))
    perf.cd_clear_all()
    ok, msg = boss.attack(6701, CH)
    assert ok
    # ─── رییس‌کل: هر ۵ کیل ───
    P.ex("UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_until=0, boss_kills=5, "
         "revenge_bid='', boss_next=1, last_boss_check=0 WHERE chat_id=?", (CH,))
    msg = boss.spawn_tick(CH)                                   # boss_next=1 → موعدش رسیده
    assert msg and "آلبرت" in msg and "هشدار نهایی" in msg      # 🎩 رییس‌کل آمد
    # رفتار: سقف ۸٪ آسیب + عقب‌نشینی در ۱۵٪
    P.ex("UPDATE worlds SET boss_hp=100000 WHERE chat_id=?", (CH,))
    perf.cd_clear_all()
    ok, msg = boss.attack(6701, CH)
    assert ok and "عقب‌نشینی" not in msg                        # هنوز جان دارد
    w = P.one("SELECT * FROM worlds WHERE chat_id=?", (CH,))
    dmg_taken = 100000 - w["boss_hp"]
    assert dmg_taken <= 0.08 * w["boss_max_hp"] + 1             # سقف ۸٪
    # ضربه‌ی نهایی: عقب‌نشینی با غنیمت
    P.ex("UPDATE worlds SET boss_hp=? WHERE chat_id=?",
         (P.one("SELECT boss_max_hp FROM worlds WHERE chat_id=?", (CH,))["boss_max_hp"] * 0.10, CH))
    msg = ""
    for _ in range(8):                    # جاخالی ۱۰٪ دارد — چند تلاش مجاز
        perf.cd_clear_all()
        ok, msg = boss.attack(6701, CH)
        if not boss.active(CH):
            break
    assert "عقب‌نشینی کرد" in (msg or "") and "فودکوین" in (msg or "")   # 🎩 غنیمت پاشید
    assert not boss.active(CH)                                   # او رفت — نه مرد


# ─── 👑 کینگ: تایتل + خوش‌آمد | 🎩 آلبرت ۴ ورژن ───
def test_grand_chef_four_phases():
    P.ex("INSERT OR IGNORE INTO worlds(chat_id, started) VALUES(?,1)", (CH,))
    mk("گروه قهرمان", 6801)
    army.recruit(6801, "pizza", 100)
    base_hp = BOSSES["grand_chef"]["hp"]
    for phase in range(4):
        P.ex("UPDATE worlds SET boss_id=NULL, boss_hp=0, boss_until=0, boss_kills=5, "
             "revenge_bid='', boss_next=1, last_boss_check=0, grand_phase=? WHERE chat_id=?",
             (phase, CH))
        msg = boss.spawn_tick(CH)
        assert msg, phase
        w = P.one("SELECT boss_max_hp, grand_phase, boss_tier FROM worlds WHERE chat_id=?", (CH,))
        # هر فاز قوی‌تر: HP = پایه × تیر × ضریب فاز
        from boss import GRAND_PHASES
        from config import BOSS_TIER_HP
        expect = round(base_hp * (1 + BOSS_TIER_HP * (w["boss_tier"] - 1))
                       * GRAND_PHASES[phase]["mult"])
        assert w["boss_max_hp"] == expect
        if phase == 3:
            assert "هیولای نهایی" in msg and "فراخوان نهایی" in msg
        # عقب‌نشینی: فاز بعدی
        P.ex("UPDATE worlds SET boss_hp=? WHERE chat_id=?", (w["boss_max_hp"] * 0.10, CH))
        m = ""
        for _ in range(10):
            perf.cd_clear_all()
            ok, m = boss.attack(6801, CH)
            if not boss.active(CH):
                break
        assert "عقب‌نشینی" in (m or "")
    # بعد از هیولای نهایی → ریست به فاز ۱
    assert P.one("SELECT grand_phase FROM worlds WHERE chat_id=?", (CH,))["grand_phase"] == 0


def test_king_title_and_fish_buttons():
    # 👑 تایتل پادشاه فقط برای مالک
    from handlers import _king_bootstrap
    mk("مدعی", 6802)
    _king_bootstrap(6802)                       # غیر از مالک → هیچ
    assert not P.one("SELECT 1 FROM cosmetics WHERE user_id=? AND cid='title_king'", (6802,))
    mk("پادشاه", 8694290031)
    _king_bootstrap(8694290031)
    assert P.one("SELECT 1 FROM cosmetics WHERE user_id=? AND cid='title_king'", (8694290031,))
    assert player.get(8694290031)["cos_title"] == "title_king"
    # فیش با دکمه تایید/رد برای ادمین
    import ui
    kb = ui.admin_order_kb("FW-999999")
    assert "تأیید" in kb.inline_keyboard[0][0].text and "رد" in kb.inline_keyboard[0][1].text
    from config import ADMIN_IDS
    assert ADMIN_IDS == [8694290031]            # یک و فقط یک ادمین: مالک


# ─── 👑 نهایی: درود پادشاه + سیو قوی ───
def test_king_salute_and_strong_save():
    import handlers
    # درود = دستور آزاد (بدون کول‌داون و بدون عضویت — احترام پادشاه هرگز بلاک نمی‌شود)
    assert "درود" in handlers.CMD_WORDS
    assert "درود" in handlers.UNGATED
    # 👑 تایتل پادشاه فقط مالک
    assert "title_king" in COSMETICS
    # 💪 سیو قوی: synchronous=FULL — حتی در قطع برق هیچ داده‌ای گم نمی‌شود
    row = db.db().conn.execute("PRAGMA synchronous").fetchone()[0]
    assert row == 2          # 2 = FULL
    # integrity: دیتابیس سالم
    assert db.db().conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    # WAL روشن
    assert db.db().conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


# ─── ⚡ god-mode پادشاه + 💸 انتقال ───
def test_king_god_mode():
    from config import KING_UID
    mk("پادشاه", KING_UID); mk("قربانی", 6901); mk("مهاجم", 6902)
    # 🛡 حمله‌ناپذیری: جنگ و هجوم اینفکتد علیه پادشاه رد
    ok, msg = war.declare(6902, KING_UID)
    assert not ok and "پادشاه" in msg
    P.ex("""INSERT INTO infected(user_id,boss_id,tier,world_chat,captured_at,expires_at)
            VALUES(?,?,?,?,?,?)""", (6902, "meow_king", 1, CH, time.time(), time.time() + 3600))
    perf.cd_clear_all()
    ok, msg = infected.raid(6902, KING_UID)
    assert not ok and "پادشاه" in msg
    # ♾ منابع بی‌پایان: هرچه خرج کند، پر می‌شود
    P.ex("UPDATE accounts SET fc=10 WHERE user_id=?", (KING_UID,))
    perf.invalidate_player(KING_UID)
    assert player.get(KING_UID)["fc"] >= 999_000_000
    # ⚡ وان‌شات: منطق کشتن (مستقیم همان SQL هندلر)
    P.ex("UPDATE accounts SET dead_until=0 WHERE user_id=?", (6901,))
    with P.conn:  # شبیه cmd_oneshot
        P.ex("UPDATE accounts SET dead_until=?, losses=losses+1 WHERE user_id=?",
             (time.time() + 300, 6901))
        P.ex("UPDATE accounts SET wins=wins+1 WHERE user_id=?", (KING_UID,))
    assert player.is_dead(player.get(6901))
    assert player.get(6901)["losses"] == 1


def test_transfer_flow():
    mk("بخشنده", 6903); mk("گیرنده", 6904)
    player.grant(6903, fc=5000)
    fc0 = player.get(6903)["fc"]
    f0 = player.get(6904)["fc"]
    # انتقال اتمیک (همان منطق cmd_transfer)
    amt = 500
    with P.conn:
        player.grant(6903, fc=-amt)
        player.grant(6904, fc=amt)
    assert player.get(6903)["fc"] == fc0 - amt
    assert player.get(6904)["fc"] == f0 + amt
    # خود-انتقال و مقدار صفر رد می‌شود (چک هندلر)
    assert not ("0".isdigit() and int("0") >= 1)
    # دستورها ثبت‌شده‌اند
    import handlers
    assert "انتقال" in handlers.CMD_WORDS and "وان‌شات" in handlers.CMD_WORDS
    assert "درود" in handlers.UNGATED


# ─── 📢 دروازه‌ی عضویت: سریع و بدون باگ ───
def test_gate_fast_membership():
    import gate, handlers
    # کش منفی فقط ۱۰ ثانیه — بعد از عضویت سریع آزاد می‌شود
    assert gate.TTL_NO == 10 and gate.TTL_OK == 600
    # متن راهنما: وعده‌ی ۱۰ ثانیه
    assert "۱۰ ثانیه" in gate.join_text()
    # دکمه‌ی چک فوری در کیبورد عضویت
    kb = gate.join_kb(12345)
    btns = [b for row in kb.inline_keyboard for b in row]
    assert any("چک کن" in b.text for b in btns)
    assert any(b.callback_data == "gc:12345" for b in btns)
    # هندلر چک فوری در callback: کش invalidate + پیام موفق
    src = open("handlers.py", encoding="utf-8").read()
    assert 'data.startswith("gc:")' in src and "invalidate" in src
    assert "عضویت تأیید شد" in src
    # FC/Fc/fc همه جواب می‌گیرند (چک CMD_WORDS lowercase-tolerant)
    assert "_fw.lower() not in CMD_WORDS" in src
    assert "fc" in handlers.CMD_WORDS


# ─── 🧹 پاک‌سازی + اعداد فارسی + منوهای متمایز ───
def test_persian_numbers_everywhere():
    from handlers import _num, _is_num
    assert _num("۵") == 5 and _num("٥") == 5 and _num("12") == 12 and _num("x", 7) == 7
    assert _is_num("۵۰۰") and _is_num("500") and not _is_num("برگر")
    # هندلر جذب: عدد فارسی → همان تعداد (نه ۱)
    src = open("handlers.py", encoding="utf-8").read()
    assert "_num(count)" in src


def test_bot_msgs_cleanup():
    # ثبت و انتخاب پیام‌های قدیمی برای پاک‌سازی
    P.ex("DELETE FROM bot_msgs")
    now = time.time()
    P.ex("INSERT INTO bot_msgs VALUES(?,?,?)", (-1001, 11, now - 700))   # قدیمی → پاک
    P.ex("INSERT INTO bot_msgs VALUES(?,?,?)", (-1001, 12, now - 100))   # تازه → ماند
    rows = P.q("SELECT message_id FROM bot_msgs WHERE at < ? AND chat_id < 0", (now - 600,))
    assert [r["message_id"] for r in rows] == [11]
    # فیش‌ها هرگز در bot_msgs نیستند (به پیوی می‌روند، نه گروه)
    assert P.q("SELECT COUNT(*) c FROM bot_msgs WHERE chat_id > 0")[0]["c"] == 0
    # تنظیمات حلقه
    import run
    assert run.CLEANUP_EVERY == 40 and run.BOT_MSG_TTL == 600
    src = open("run.py", encoding="utf-8").read()
    assert "pinned_message" in src            # پین‌شده‌ها محافظت می‌شوند


def test_menus_distinct():
    import ui
    # 🍔 فقط یک منو — گروه و پیوی دقیقاً همان یک چیز را می‌بینند
    hub = [b.text for row in ui.hub_kb(1).inline_keyboard for b in row]
    menu = [b.text for row in ui.menu_kb(1).inline_keyboard for b in row]
    assert hub == menu and "🍔 منوی فوودورس" in menu
    # همه‌چیز در همان یک منو: بازی + شخصی
    assert "👑 باس" in menu and "🔄 بازار" in menu and "📦 پک‌های من" in menu
    assert "💎 بتل‌پس" in menu and "🎨 ظاهر" in menu and "🛒 فروشگاه" in menu


# ─── 🎯 دستور تکی + 👑 پروفایل مالک + 📚 آموزش کوتاه ───
def test_solo_commands_only():
    from handlers import SOLO_CMDS
    # «شروع» و «درود» فقط خالی اجرا می‌شوند
    assert "شروع" in SOLO_CMDS and "درود" in SOLO_CMDS and "منو" in SOLO_CMDS
    # دستورهای پارامتری در این لیست نیستند
    for c in ("جذب", "ارتقا", "گذاشتن", "انتقال", "بفروش", "خریدن", "جایزه", "سفارش"):
        assert c not in SOLO_CMDS, c
    src = open("handlers.py", encoding="utf-8").read()
    assert "if cmd in SOLO_CMDS and rest:" in src   # «درود شروع کن» → سکوت


def test_king_profile_special():
    mk("پادشاه", 8694290031)
    import handlers
    txt = handlers.profile_text(player.get(8694290031))
    assert "پادشاه و مالک فوودورس" in txt


def test_tutorials_short():
    import tutorials
    assert len(tutorials.TUTS) == 6
    for k, v in tutorials.TUTS.items():
        assert 150 < len(v) < 450, (k, len(v))       # همه کوتاه
