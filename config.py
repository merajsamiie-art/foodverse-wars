# ⚙️ تنظیمات مرکزی — FOODVERSE WARS
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0") or 0)

# 💳 پرداخت — از Environment/Secrets می‌آید، هرگز در سورس نیست
PAYMENT_CARD = os.environ.get("PAYMENT_CARD", "")
PAYMENT_HOLDER = os.environ.get("PAYMENT_HOLDER", "")
ORDER_EXPIRE_S = 30 * 60          # انقضای سفارش: ۳۰ دقیقه

DB_PATH = os.environ.get("FW_DB_PATH", os.path.join(os.path.dirname(__file__), "foodverse.db"))

# ─── شروع ───
START_FC = 500
START_RES = dict(meat=120, cheese=100, sauce=100, potato=100, metal=50, crystal=0)
import zoneinfo

TZ = zoneinfo.ZoneInfo("Asia/Tehran")   # ⏰ همه‌ی ریست‌ها و نمایش‌ها به وقت تهران

MIN_PLAYERS = 4                    # حداقل عضو برای روشن شدن دنیای گروه
AVATAR_REROLL = 200

# ─── تولید در ساعت (lazy tick) ───
PROD_BASE = dict(meat=22, cheese=16, sauce=16, potato=16)
FACTORY_FC_H = 25
LAB_CRYSTAL_H = 2
COLONY_RES_H = 20
COLONY_FC_H = 50
PROD_CAP_H = 8

# ─── XP و لِوِل ───
def xp_need(level: int) -> int:
    return int(100 * (level ** 1.6))

XP_WAR_WIN = 40
XP_WAR_LOSS = 10
XP_BOSS_HIT = 12
XP_CRAFT = 25
XP_DAILY = 30

# ─── مرگ/محافظت ───
DEAD_MINUTES = 6                   # مرگ: ۶ دقیقه
PROTECT_MINUTES = 5                # محافظت بعد از احیا
DEATH_DROP_PCT = 0.25              # سقف drop منابع در مرگ (تجهیزات محافظت می‌شوند)

# ─── ساخت‌وساز ───
COLONY_NEED_LEVEL = 8
COLONY_COST = dict(fc=800, meat=250, metal=150)
COLONY_MAX = 3
COLONY_RAID_CD = 30 * 60
COLONY_PAUSE_S = 3600

# ─── جنگ ───
CD_WAR = 90
WAR_STEAL_PCT = 0.30
TREASURY_PROTECT = 0.15
LOSS_WIN = (0.05, 0.12)
LOSS_LOSE = (0.20, 0.30)

# ─── باس ───
BOSS_CHANCE = 0.10          # به‌ازای هر چکِ ۱۵ دقیقه‌ای (≈۴۰٪ در ساعت)
BOSS_CHECK_S = 900          # چک هر ۱۵ دقیقه — اسپاون کاملاً تصادفی
BOSS_DURATION = 45 * 60
BOSS_UNIT_LOSS = 0.03
CD_BOSS = 30

# ─── روزانه ───
DAILY_FC = 150
DAILY_STREAK_CAP = 7
DAILY_REWARD_RES = 40
DAILY_PACK_CHANCE = 0.5            # شانس پک رایگان در مأموریت روزانه

# ─── انبار ───
def inv_slots(level: int) -> int:
    return 10 + level // 2

# ─── بازار پویا ───
MARKET_TAX = 0.10
LISTING_FEE = 20
MAX_LISTING_PRICE = 100000
PRICE_MIN_MULT = 0.5               # کف قیمت: ۵۰٪ پایه
PRICE_MAX_MULT = 2.0               # سقف قیمت: ۲۰۰٪ پایه
PRICE_STEP = 0.01                  # هر معامله ۱٪ فشار
PRICE_DECAY_H = 0.05               # بازگشت ۵٪ در ساعت به سمت پایه
NPC_SELL_RATIO = 0.85              # NPC ۸۵٪ قیمت می‌دهد (کارمزد)
BUY_LIMIT = 500                    # سقف هر معامله NPC
BUY_LIMIT = 500                    # سقف خرید NPC در هر دستور (ضد دستکاری)

# ─── پک ───
PACK_OPEN_CD = 10                  # حداقل ۱۰ ثانیه بین باز کردن (ضد دابل‌کلیک)
PITY_PER_PACK = 0.01               # هر پک بدون Epic+: ۱٪ شانس اضافه
PITY_CAP = 0.30                    # سقف بونوس Pity

# ─── Battle Pass ───
PASS_TIERS = 20                    # تعداد پله‌های هر Pass
PASS_XP_PER_TIER = 250
PASS_WEEKLY_DAYS = 7
PASS_MONTHLY_DAYS = 30
PASS_SEASON_DAYS = 90

# ─── ضداسپم ───
CD_RECRUIT = 30
CD_BUILD = 20
CD_CRAFT = 45
CD_MARKET = 15
CD_CALLBACK = 0.8
FEED_EDIT_WINDOW = 60

# ─── فروشگاه چرخشی ───
SHOP_DAILY_SIZE = 6
SHOP_WEEKLY_SIZE = 8
SHOP_DAILY_USER_LIMIT = 2          # سقف خرید هر کالا در روز برای هر بازیکن

# ── اتحادها ──
ALLY_CREATE_COST = 50000      # FC برای تأسیس اتحاد
ALLY_MAX = 30                 # ظرفیت اعضا
ALLY_HELP_CD = 3600           # کول‌داون کمک به هم‌اتاقی (ثانیه)
BETRAY_CD = 7 * 24 * 3600     # کول‌داون خیانت (۷ روز)
BETRAY_STEAL_CAP = 0.3        # سقف دزدی از خزانه در خیانت (۳۰٪)

# ── 💰 درآمدهای خردِ فعالیتی (عمداً کوچک — انگیزه، نه چاپِ پول) ──
SHIFT_CD = 3 * 3600                # شیفت کارخانه: هر ۳ ساعت
SHIFT_FC = (120, 280)
PATROL_CD = 45 * 60                # گشت محوطه: هر ۴۵ دقیقه

# ── 🧟 اینفکتد ──
INFECTED_COST_FC = 1500            # هزینه‌ی اسیرکردن باس
INFECTED_LEVEL = 10                # حداقل سطح
INFECTED_TTL = 3 * 24 * 3600       # هر ۳ روز باید تازه شود
INFECTED_WINDOW = 10 * 60          # پنجره‌ی اسیرکردن بعد از کشتن باس
INFECTED_RAID_CD = 12 * 3600       # هجوم: هر ۱۲ ساعت
INFECTED_CONTROL_H = {1: 4, 2: 8, 3: 12}   # مدت کنترل قربانی (ساعت، بر اساس تیر)
INFECTED_CONTROL_TAX = 0.15        # ۱۵٪ تولید قربانی به کنترل‌کننده می‌رسد
INFECTED_POWER_BONUS = 0.08        # بونوس قدرت ارتش به‌ازای تیر

# ── 👹 تیرهای باس ──
BOSS_TIER_HP = 0.75                # هر تیر: +۷۵٪ جان
BOSS_TIER_LOOT = 0.6               # هر تیر: +۶۰٪ جایزه
