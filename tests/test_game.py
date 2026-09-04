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
import rank
import shop
import war
import world
from config import MIN_PLAYERS
from registry import UNITS, BOSSES, PACKS, PASSES, COSMETICS

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
    for i in range(MIN_PLAYERS - 1):
        mk(f"p{i}", 3000 + i)
    n, _, ok = world.try_start(CH)
    assert not ok
    mk("چهارم", 3000 + MIN_PLAYERS - 1)
    n, _, ok = world.try_start(CH)
    assert ok


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
    mk("باس‌کش", 4020)
    msg = boss.spawn_tick(CH, force=True)
    assert msg and "FACTORY ALERT" in msg
    assert boss.active(CH)
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
    ok, msg = packs.open_pack(4027, "free_pack")
    assert ok and "تضمینی" in msg
    assert player.get(4027)["packs_opened"] == 1


def test_pack_pity_counts():
    mk("بدشانس", 4028)
    P.ex("UPDATE accounts SET pity=5 WHERE user_id=?", (4028,))
    packs.give_pack(4028, "free_pack")
    perf.cd_clear_all()
    ok, msg = packs.open_pack(4028, "free_pack")
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
    ok1, _ = packs.open_pack(4029, "free_pack")
    ok2, msg2 = packs.open_pack(4029, "free_pack")
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
    ok, msg = payments.create_order(4040, "starter_pack")
    assert ok and "FW-" in msg
    oid = P.one("SELECT order_id FROM orders WHERE user_id=?", (4040,))["order_id"]
    ok, res = payments.submit_receipt(4040, "TRK-111", "hashAAA")
    assert ok and res["order_id"] == oid
    mk("دیگری", 4041)
    payments.create_order(4041, "starter_pack")
    ok, res = payments.submit_receipt(4041, "TRK-111", "hashBBB")   # پیگیری تکراری
    assert not ok
    ok, res = payments.submit_receipt(4041, "TRK-222", "hashAAA")   # هش تکراری
    assert not ok
    ok, o, msg = payments.decide(oid, 8694290031, True)
    assert ok and "تأیید" in msg
    ok2, o2, msg2 = payments.decide(oid, 8694290031, True)
    assert not ok2   # دوباره‌محصول ممنوع
    assert player.inv(4040).get("pack_starter_pack") == 1


def test_order_reject():
    mk("ردشده", 4042)
    ok, _ = payments.create_order(4042, "epic_pack")
    assert ok
    oid = P.one("SELECT order_id FROM orders WHERE user_id=? AND status='pending_payment'",
                (4042,))["order_id"]
    payments.submit_receipt(4042, "TRK-333", "hashCCC")
    ok, o, msg = payments.decide(oid, 8694290031, False)
    assert ok and "رد" in msg
    assert not any(k.startswith("pack_") for k in player.inv(4042))


def test_order_expire():
    mk("دیرکرد", 4043)
    payments.create_order(4043, "starter_pack")
    P.ex("UPDATE orders SET expires_at=? WHERE user_id=?", (time.time() - 10, 4043))
    ok, res = payments.submit_receipt(4043, "TRK-444", "hashDDD")
    assert not ok


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
    assert "fw" in texts.HELP and texts.WELCOME_PRIVATE
    assert len(tutorials.TUTS) >= 5
