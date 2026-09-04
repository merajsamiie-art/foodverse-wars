# 🗄 دیتابیس — SQLite + WAL + تراکنش | حساب جهانی + دنیاهای گروهی
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

from config import DB_PATH

SCHEMA = """
-- 🌍 دنیاها (هر گروه = یک دنیا)
-- 🧟 اینفکتد: باس اسیرشده توسط بازیکن (هر ۳ روز باید تازه شود)
CREATE TABLE IF NOT EXISTS infected(
  user_id INTEGER PRIMARY KEY, boss_id TEXT, tier INTEGER DEFAULT 1,
  world_chat INTEGER, captured_at REAL, expires_at REAL, raid_cd REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS worlds(
  chat_id INTEGER PRIMARY KEY,
  started INTEGER DEFAULT 0,
  created_at REAL, last_tick REAL,
  boss_id TEXT, boss_hp REAL, boss_max_hp REAL, boss_until REAL,
  last_boss_check REAL DEFAULT 0
);
-- 👤 حساب جهانی — همه‌چیز با Telegram User ID
CREATE TABLE IF NOT EXISTS accounts(
  user_id INTEGER PRIMARY KEY,
  name TEXT, avatar TEXT,
  level INTEGER DEFAULT 1, xp REAL DEFAULT 0,
  fc REAL, meat REAL, cheese REAL, sauce REAL, potato REAL, metal REAL, crystal REAL,
  wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, boss_dmg REAL DEFAULT 0,
  colonies INTEGER DEFAULT 0, colony_pause REAL DEFAULT 0,
  dead_until REAL DEFAULT 0, protect_until REAL DEFAULT 0,
  last_daily REAL DEFAULT 0, daily_streak INTEGER DEFAULT 0,
  pity INTEGER DEFAULT 0, packs_opened INTEGER DEFAULT 0,
  pass_type TEXT DEFAULT '', pass_until REAL DEFAULT 0,
  pass_xp REAL DEFAULT 0, pass_free TEXT DEFAULT '[]', pass_prem TEXT DEFAULT '[]',
  cos_frame TEXT, cos_title TEXT, cos_skin TEXT, cos_effect TEXT,
  banned INTEGER DEFAULT 0, created_at REAL, last_active REAL
);
-- عضویت در دنیاها
CREATE TABLE IF NOT EXISTS world_players(
  chat_id INTEGER, user_id INTEGER, joined REAL, last_active REAL,
  PRIMARY KEY(chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS buildings(
  user_id INTEGER, bld TEXT, level INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, bld)
);
CREATE TABLE IF NOT EXISTS units(
  user_id INTEGER, unit_id TEXT, count INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, unit_id)
);
CREATE TABLE IF NOT EXISTS items(
  user_id INTEGER, item_id TEXT, qty INTEGER DEFAULT 0, equipped INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, item_id)
);
CREATE TABLE IF NOT EXISTS cosmetics(
  user_id INTEGER, cid TEXT, PRIMARY KEY(user_id, cid)
);
-- اتحادها: دنیایی (هر گروه اتحادهای خودش)
CREATE TABLE IF NOT EXISTS alliances(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER, name TEXT, owner_uid INTEGER,
  treasury_fc REAL DEFAULT 0, created_at REAL,
  UNIQUE(chat_id, name)
);
CREATE TABLE IF NOT EXISTS ally_members(
  user_id INTEGER PRIMARY KEY, alliance_id INTEGER, joined REAL, betrayed_at REAL DEFAULT 0
);
-- بازار بازیکن‌ها
CREATE TABLE IF NOT EXISTS listings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER, seller_uid INTEGER, item_id TEXT, qty INTEGER, price REAL,
  active INTEGER DEFAULT 1, created_at REAL, buyer_uid INTEGER
);
CREATE TABLE IF NOT EXISTS txlog(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER, user_id INTEGER, kind TEXT, detail TEXT, at REAL
);
CREATE TABLE IF NOT EXISTS boss_dmg(
  chat_id INTEGER, boss_id TEXT, user_id INTEGER, dmg REAL,
  PRIMARY KEY(chat_id, boss_id, user_id)
);
CREATE TABLE IF NOT EXISTS daily(
  user_id INTEGER, day TEXT,
  war_wins INTEGER DEFAULT 0, recruits INTEGER DEFAULT 0,
  crafted INTEGER DEFAULT 0, boss_hits INTEGER DEFAULT 0,
  claimed INTEGER DEFAULT 0, shop_buys TEXT DEFAULT '{}',
  sold INTEGER DEFAULT 0, bought INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, day)
);
-- 💳 سفارش‌های پرداخت
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT UNIQUE, user_id INTEGER, product TEXT,
  amount INTEGER, status TEXT DEFAULT 'pending_payment',
  tracking_no TEXT, receipt_hash TEXT,
  created_at REAL, expires_at REAL, decided_at REAL,
  admin_id INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_tracking ON orders(tracking_no) WHERE tracking_no IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_rhash ON orders(receipt_hash) WHERE receipt_hash IS NOT NULL;
-- 📈 بازار پویا: وضعیت قیمت منابع
CREATE TABLE IF NOT EXISTS market_state(
  res TEXT PRIMARY KEY, base INTEGER, mult REAL DEFAULT 1.0, updated REAL
);
-- 🛒 فروشگاه چرخشی: خریدهای روزانه‌ی هر بازیکن
CREATE TABLE IF NOT EXISTS shop_buys(
  user_id INTEGER, day TEXT, slot TEXT, qty INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, day, slot)
);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS idx_wp_chat ON world_players(chat_id);
CREATE INDEX IF NOT EXISTS idx_listings_chat ON listings(chat_id, active);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_ally_members_aid ON ally_members(alliance_id);
CREATE INDEX IF NOT EXISTS idx_worlds_started ON worlds(started);
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        # ⚡ پرفورمنس زیر بار سنگین
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA cache_size=-16000")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=134217728")
        with self.lock:
            self.conn.executescript(SCHEMA)
            self._migrate()
            self.conn.commit()

    def _migrate(self):
        """ستون‌های جدید روی دیتابیس زنده — ALTER امن، بدون از دست رفتن داده."""
        adds = {
            "worlds": {"boss_tier": "INTEGER DEFAULT 1", "boss_pool": "TEXT DEFAULT ''"},
            "accounts": {"controlled_by": "INTEGER DEFAULT 0",
                         "controlled_until": "REAL DEFAULT 0",
                         "guide_step": "INTEGER DEFAULT 0",
                         "ref_by": "INTEGER DEFAULT 0",
                         "ref_ok_at": "REAL DEFAULT 0"},
            "daily": {"sold": "INTEGER DEFAULT 0", "bought": "INTEGER DEFAULT 0"},
        }
        for tbl, cols in adds.items():
            have = {r[1] for r in self.conn.execute(f"PRAGMA table_info({tbl})")}
            for col, ddl in cols.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {ddl}")

    def q(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params).fetchone()

    def ex(self, sql, params=()):
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    @contextmanager
    def tx(self):
        """تراکنش اتمی — برای عملیات حساس (پک/سفارش/جنگ)."""
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def close(self):
        with self.lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            self.conn.close()


_db = None


def init(path: str = None):
    global _db
    _db = DB(path or DB_PATH)
    return _db


def db() -> DB:
    assert _db is not None, "db.init() نشده"
    return _db


def now() -> float:
    return time.time()
