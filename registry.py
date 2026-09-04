# 🍔 Registry مرکزی — واحدها، ساختمان‌ها، آیتم‌ها، باس‌ها، دستورها، آواتارها
# تغییر بیلانس فقط از این فایل.

# ─── 🎭 آواتارها (تنوع ظاهری بازیکن‌ها) ───
AVATARS = ["😺", "🍔", "🍕", "🍟", "🥦", "🍎", "🌮", "🍩", "🍭",
           "🥤", "🧀", "🍅", "🥔", "🌭", "🍿", "🥨", "🍪", "🧁", "🍫", "🍣",
           "🥑", "🌽", "🥕", "🍄", "🐙", "🦖"]

# ─── 🪖 واحدها ───
# 🧸 سیستم شخصیت: هر واحد = شخصیت با ID/Stats/Type/Rarity/Image
# ctype: fastfood | veggie | fruit | meow | candy | weird | boss
UNITS = {
    "burger":  dict(name="سرباز برگری",    en="Burger Soldier", emoji="🍔", ctype="fastfood", rarity="common",
                    hp=100, atk=12, df=8,  spd=6,  cost=dict(fc=60,  meat=15)),
    "fries":   dict(name="تیرانداز سیب‌زمینی", en="Fry Sniper", emoji="🍟", ctype="fastfood", rarity="common",
                    hp=70,  atk=18, df=4,  spd=8,  cost=dict(fc=70,  potato=20)),
    "broccoli": dict(name="پزشک بروکلی",   en="Broccoli Medic", emoji="🥦", ctype="veggie", rarity="common",
                     hp=90,  atk=6,  df=10, spd=5,  heal=9, cost=dict(fc=80,  potato=15)),
    "meow":    dict(name="دیده‌بان میو",    en="Meow Scout", emoji="😺", ctype="meow", rarity="rare",
                    hp=60,  atk=10, df=5,  spd=14, crit=0.10, cost=dict(fc=90,  meat=20, cheese=10)),
    "pizza":   dict(name="جنگاور پیتزا",   en="Pizza Warrior", emoji="🍕", ctype="fastfood", rarity="rare",
                    hp=150, atk=10, df=14, spd=4,  cost=dict(fc=110, cheese=25, sauce=15)),
    "candy":   dict(name="جادویس شیرینی",  en="Candy Mage", emoji="🍭", ctype="candy", rarity="rare",
                    hp=65,  atk=16, df=3,  spd=7,  cost=dict(fc=120, sauce=30)),
    "cheese_knight": dict(name="شوالیه‌ی پنیر", en="Cheese Knight", emoji="🧀", ctype="fastfood", rarity="epic",
                          hp=130, atk=8, df=16, spd=3, cost=dict(fc=130, cheese=30, metal=10)),
    "lasagnazilla": dict(name="لازاگنی‌زیلا", en="Lasagnazilla", emoji="🦖", ctype="weird", rarity="mythic",
                         hp=400, atk=30, df=20, spd=8, cost=None),  # فقط از تخم
}

# ─── 🏠 ساختمان‌ها ───
BUILDINGS = {
    "factory":  dict(name="کارخانه",       emoji="🏭", desc="سکه در هر ساعت تولید می‌کند", maxlv=10,
                     cost0=dict(fc=150, metal=30)),
    "lab":      dict(name="آزمایشگاه",     emoji="🔬", desc="استخراج کریستال", maxlv=10,
                     cost0=dict(fc=200, metal=50)),
    "training": dict(name="مرکز آموزش",    emoji="🪖", desc="قدرت ارتش +%۸ به‌ازای سطح", maxlv=10,
                     cost0=dict(fc=180, potato=40)),
    "treasury": dict(name="خزانه",         emoji="🏦", desc="محافظت منابع در جنگ", maxlv=10,
                     cost0=dict(fc=160, cheese=40)),
    "defense":  dict(name="دفاع",          emoji="🛡️", desc="کاهش آسیب دشمن", maxlv=10,
                     cost0=dict(fc=170, metal=40)),
    "workshop": dict(name="کارگاه",        emoji="🔧", desc="شواندن دستورهای ساخت", maxlv=5,
                     cost0=dict(fc=250, metal=60)),
}

# ─── 🎒 آیتم‌ها ───
# kind: booster (مصرفی جنگ/باس) | equip (دائمی، سه اسلات) | material | trophy
ITEMS = {
    # بوسترهای جنگ
    "cheese_bomb":   dict(name="بمب پنیری",   emoji="💣", kind="booster", rarity="common",
                          effect="war_dmg", val=0.30, desc="۳۰٪+ آسیب نبرد بعدی"),
    "sauce_rocket":  dict(name="موشک سس قرمز", emoji="🚀", kind="booster", rarity="rare",
                          effect="boss_dmg", val=0.50, desc="۵۰٪+ آسیب باس بعدی"),
    # تجهیزات (equip)
    "burger_tank":   dict(name="تانک برگری",   emoji="🛡️", kind="equip", slot="def", rarity="epic",
                          val=0.10, desc="۱۰٪+ دفاع ارتش"),
    "pizza_mech":    dict(name="مک پیتزایی",  emoji="🤖", kind="equip", slot="atk", rarity="epic",
                          val=0.15, desc="۱۵٪+ حمله‌ی ارتش"),
    "crown_meow":    dict(name="تاج میو کینگ", emoji="👑", kind="equip", slot="spc", rarity="legendary",
                          val=0.10, desc="۱۰٪+ کل قدرت + پرستیژ"),
    # مواد کمیاب باس
    "mega_meat":     dict(name="ابرگوشت",     emoji="🥩", kind="material", rarity="rare",
                          desc="قطره‌ی لازاگنی‌زیلا — سازنده‌ی تخم"),
    "golden_cheese": dict(name="پنیر طلایی",   emoji="🧈", kind="material", rarity="epic",
                          desc="قطره‌ی میو کینگ"),
    "toy_crown":     dict(name="تاج اسباب‌بازی", emoji="🎩", kind="material", rarity="legendary",
                          desc="قطره‌ی مگا برگر"),
    # تخم لازاگنی‌زیلا
    "lasagna_egg":   dict(name="تخم لازاگنی‌زیلا", emoji="🥚", kind="material", rarity="mythic",
                          desc="از آن واحد افسانه‌ای متولد می‌شود"),
}

RARITY = {
    "common": ("⚪", "معمولی"), "rare": ("🔵", "کمیاب"), "epic": ("🟣", "حماسی"),
    "legendary": ("🟠", "افسانه‌ای"), "mythic": ("🔴", "اسطوره‌ای"),
}

# ─── 🛠 دستورهای ساخت ───
RECIPES = {
    "cheese_bomb":  dict(out="cheese_bomb", qty=1, need_lv=1, workshop=1,
                         cost=dict(fc=100, cheese=50, metal=30)),
    "sauce_rocket": dict(out="sauce_rocket", qty=1, need_lv=5, workshop=2,
                         cost=dict(fc=250, sauce=80, metal=60)),
    "burger_tank":  dict(out="burger_tank", qty=1, need_lv=10, workshop=3,
                         cost=dict(fc=800, meat=120, metal=100)),
    "pizza_mech":   dict(out="pizza_mech", qty=1, need_lv=15, workshop=4,
                         cost=dict(fc=2000, metal=180, crystal=25)),
    "lasagna_egg":  dict(out="lasagna_egg", qty=1, need_lv=20, workshop=5,
                         cost=dict(fc=5000, meat=300, cheese=200, mega_meat=3)),
}

# ─── 👑 باس‌ها ───
BOSSES = {
    "mega_burger": dict(name="مگا برگر", en="MEGA BURGER", emoji="🍔", ctype="boss", rarity="legendary",
                        hp=9000, atk=60, resist=0.15,
                        lore="برگری که خودش را خورد تا بزرگ شود.",
                        loot=dict(fc=(500, 900), drops=["toy_crown", "golden_cheese"])),
    "meow_king":   dict(name="میو کینگ", en="MEOW KING", emoji="😼", ctype="boss", rarity="legendary",
                        hp=12000, atk=75, resist=0.20, dodge=0.15,
                        lore="پادشاه گربه‌ها. سه زندگی دارد؛ همه‌اش مال شماست.",
                        loot=dict(fc=(800, 1400), drops=["golden_cheese", "crown_meow"])),
    "lasagnazilla": dict(name="لازاگنی‌زیلا", en="LASAGNAZILLA", emoji="🦖", ctype="boss", rarity="mythic",
                         hp=18000, atk=95, resist=0.25,
                         lore="لایه‌به‌لایه‌ی مرگ. با سس.",
                         loot=dict(fc=(1200, 2200), drops=["mega_meat", "lasagna_egg"])),
}

# ─── 🪙 قیمت NPC منابع (خرید) ───
RES_PRICES = dict(meat=8, cheese=8, sauce=7, potato=6, metal=12, crystal=60)

RES_META = dict(
    meat=dict(name="گوشت", emoji="🥩"), cheese=dict(name="پنیر", emoji="🧀"),
    sauce=dict(name="سس", emoji="🍅"), potato=dict(name="سیب‌زمینی", emoji="🥔"),
    metal=dict(name="فلز", emoji="⚙️"), crystal=dict(name="کریستال", emoji="💎"),
    fc=dict(name="FoodCoin", emoji="🪙"),
)

# ─── 🏆 عناوین سطح ───
TITLES = [
    (1, "👨‍🍳 آشپز تازه‌کار"), (5, "🥗 سرآشپز سالاد"), (10, "🍔 فرمانده‌ی برگری"),
    (15, "🍕 ژنرال پیتزا"), (20, "🦖 رام‌کننده‌ی لازاگنی"), (30, "👑 امپراتور فوودورس"),
]


def title_of(level: int) -> str:
    t = TITLES[0][1]
    for lv, name in TITLES:
        if level >= lv:
            t = name
    return t


def item_name(iid: str) -> str:
    it = ITEMS.get(iid)
    return f"{it['emoji']} {it['name']}" if it else iid


def res_name(rid: str) -> str:
    m = RES_META.get(rid)
    return f"{m['emoji']} {m['name']}" if m else rid


def rarity_tag(iid: str) -> str:
    r = ITEMS.get(iid, {}).get("rarity", "common")
    return RARITY[r][0]


# ═══════════ 🎨 سیستم ظاهر (Cosmetics) ═══════════
# kind: frame | title | skin | effect | base_theme | army_skin
COSMETICS = {
    # فریم پروفایل
    "frame_bronze":   dict(name="فریم برنزی",     en="Bronze Frame",    kind="frame", rarity="common"),
    "frame_silver":   dict(name="فریم نقره‌ای",   en="Silver Frame",    kind="frame", rarity="rare"),
    "frame_gold":     dict(name="فریم طلایی",     en="Gold Frame",     kind="frame", rarity="epic"),
    "frame_neon":     dict(name="فریم نئونی",     en="Neon Frame",     kind="frame", rarity="legendary"),
    # عنوان
    "title_chef":     dict(name="سرآشپز بزرگ",    en="Grand Chef",     kind="title", rarity="rare"),
    "title_warlord":  dict(name="جنگ‌سالار",      en="Warlord",        kind="title", rarity="epic"),
    "title_meow":     dict(name="خادم میو کینگ",  en="Meow King Servant", kind="title", rarity="legendary"),
    "title_mythic":   dict(name="افسانه‌ی فوودورس", en="Foodverse Legend", kind="title", rarity="mythic"),
    # اسکین ارتش
    "skin_gold":      dict(name="اسکین طلایی ارتش", en="Golden Army",  kind="army_skin", rarity="epic"),
    "skin_lava":      dict(name="اسکین گدازه",    en="Lava Skin",     kind="army_skin", rarity="legendary"),
    # افکت نبرد
    "fx_sparkle":     dict(name="افکت جرقه",      en="Sparkle FX",    kind="effect", rarity="rare"),
    "fx_thunder":     dict(name="افکت رعد",       en="Thunder FX",    kind="effect", rarity="mythic"),
}

def cosmetics_by_kind(kind: str) -> dict:
    return {k: v for k, v in COSMETICS.items() if v["kind"] == kind}


# ═══════════ 📦 پک‌ها ═══════════
# odds: شانس هر تیر کمیابی برای قرعه‌ی کازمتیک/آیتم
# guaranteed: بخش تضمینی (FC + مواد) — ارزش مشخص هر پک
PACKS = {
    # 🆓 پک‌های داخل بازی (فقط با بازی)
    "free_pack": dict(name="پک معمولی", en="Common Pack", emoji="📦", price_toman=0,
                      fc_cost=300,
                      guaranteed=dict(fc=200),
                      pulls=2, odds=dict(common=0.70, rare=0.25, epic=0.05, legendary=0.0, mythic=0.0)),
    "rare_pack": dict(name="پک کمیاب", en="Rare Pack", emoji="📦", price_toman=0,
                      fc_cost=1200, source="boss/daily",
                      guaranteed=dict(fc=600, metal=20),
                      pulls=2, odds=dict(common=0.45, rare=0.40, epic=0.13, legendary=0.02, mythic=0.0)),
    # 💰 پک‌های فروشگاه (تومان)
    "starter_pack": dict(name="پک شروع", en="Starter Pack", emoji="🟢", price_toman=250000,
                         guaranteed=dict(fc=2500, meat=150, metal=80),
                         pulls=3, odds=dict(common=0.70, rare=0.24, epic=0.05, legendary=0.01, mythic=0.0)),
    "epic_pack": dict(name="پک حماسی", en="Epic Pack", emoji="🟣", price_toman=750000,
                      guaranteed=dict(fc=8000, crystal=15),
                      pulls=4, odds=dict(common=0.40, rare=0.34, epic=0.21, legendary=0.045, mythic=0.005)),
    "legend_pack": dict(name="پک افسانه‌ای", en="Legend Pack", emoji="🟠", price_toman=1250000,
                        guaranteed=dict(fc=15000, crystal=30),
                        pulls=5, odds=dict(common=0.28, rare=0.32, epic=0.28, legendary=0.10, mythic=0.02)),
    "mythic_chest": dict(name="صندوق اسطوره‌ای", en="Mythic Chest", emoji="👑", price_toman=2000000,
                         guaranteed=dict(fc=25000, crystal=50),
                         pulls=5, odds=dict(common=0.15, rare=0.30, epic=0.35, legendary=0.17, mythic=0.03)),
    "ultimate_chest": dict(name="صندوق نهایی فصل", en="Ultimate Season Chest", emoji="🌌", price_toman=3000000,
                           guaranteed=dict(fc=40000, crystal=80),
                           pulls=6, odds=dict(common=0.10, rare=0.25, epic=0.35, legendary=0.24, mythic=0.06)),
}

# جدول قرعه بر اساس کمیابی: (کازمتیک یا آیتم بازی، وزن داخل تیر)
LOOT_TABLES = {
    "common":    [("frame_bronze", 3), ("fx_sparkle", 2), ("cheese_bomb", 4)],
    "rare":      [("frame_silver", 3), ("title_chef", 2), ("sauce_rocket", 3)],
    "epic":      [("frame_gold", 3), ("title_warlord", 2), ("burger_tank", 2), ("skin_gold", 2)],
    "legendary": [("frame_neon", 3), ("title_meow", 2), ("pizza_mech", 2), ("skin_lava", 2)],
    "mythic":    [("title_mythic", 3), ("fx_thunder", 3), ("lasagna_egg", 2), ("crown_meow", 2)],
}

# 🎖 جایزه‌ی سکه جایگزین برای کازمتیک تکراری
DUPLICATE_VALUE = dict(common=150, rare=400, epic=1200, legendary=3000, mythic=8000)


# ═══════════ 💎 Battle Pass ═══════════
PASSES = {
    "weekly":  dict(name="پاس هفتگی",  en="Weekly Pass",  emoji="🥉", price_toman=350000,  days=7),
    "monthly": dict(name="پاس ماهانه", en="Monthly Pass", emoji="🥈", price_toman=950000,  days=30),
    "season":  dict(name="پاس فصلی",   en="Season Pass",  emoji="🥇", price_toman=2500000, days=90),
}
# جوایز هر پله: (رایگان، پرمیوم)
PASS_REWARDS = {
    1:  (dict(fc=300),              dict(fc=600, crystal=2)),
    5:  (dict(fc=800, meat=100),    dict(fc=1500, crystal=5)),
    10: (dict(fc=1500, metal=80),   dict(fc=3000, crystal=10, item="rare_pack")),
    15: (dict(fc=2500, sauce=120),  dict(fc=5000, crystal=15, item="free_pack")),
    20: (dict(fc=4000, crystal=5),  dict(fc=10000, crystal=30, cosmetic="frame_neon")),
}


def pass_reward_text(tier: int) -> str:
    free, prem = PASS_REWARDS.get(tier, (dict(fc=200 * tier), dict(fc=400 * tier)))
    def fmt(d):
        parts = []
        for k, v in d.items():
            if k == "fc":
                parts.append(f"🪙 {v}")
            elif k == "item":
                parts.append(f"📦 {PACKS[v]['name']}")
            elif k == "cosmetic":
                parts.append(f"✨ {COSMETICS[v]['name']}")
            else:
                parts.append(f"{RES_META.get(k, {}).get('emoji', '')} {v}")
        return " ".join(parts)
    return fmt(free), fmt(prem)


# ═══════════ 🛒 فروشگاه چرخشی (FC) ═══════════
SHOP_POOL = {
    "cheese_bomb":  dict(fc=180,  limit=4),
    "sauce_rocket": dict(fc=420,  limit=2),
    "burger_tank":  dict(fc=2500, limit=1),
    "pizza_mech":   dict(fc=6000, limit=1),
    "herb_pack":    dict(fc=350,  limit=3, grant=dict(meat=200, cheese=200)),
    "res_crate":    dict(fc=500,  limit=3, grant=dict(metal=150, potato=150)),
    "free_pack":    dict(fc=400,  limit=2, pack=True),
    "rare_pack":    dict(fc=1500, limit=1, pack=True),
}
