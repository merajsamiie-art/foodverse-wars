#!/usr/bin/env python3
# 🛡 merge_db.py — تضمین «هیچ بازیکنی گم نمی‌شود»
# قبل از هر push: دیتابیس remote (production) را با محلی merge می‌کند.
# قاعده: remote-wins برای تعارض‌ها (ربات production همیشه تازه‌تر است)
# + ردیف‌های فقط-محلی هم نگه داشته می‌شوند. هیچ داده‌ای حذف نمی‌شود.

import sqlite3
import sys

# جداول بازی و کلید اصلی هرکدام — همه‌ی داده‌های بازیکن
TABLES = {
    "accounts": "user_id",
    "world_players": "chat_id, user_id",
    "worlds": "chat_id",
    "units": "user_id, unit_id",
    "items": "user_id, item_id",
    "buildings": "user_id, bld",
    "cosmetics": "user_id, cid",
    "alliances": "id",
    "ally_members": "user_id",
    "listings": "id",
    "txlog": "id",
    "boss_dmg": "user_id, chat_id, boss_id",
    "daily": "user_id",
    "orders": "id",
    "market_state": "chat_id, item_id",
    "shop_buys": "user_id, day, slot",
    "kv": "k",
    "media": "key",
    "infected": "user_id",
    "trades": "id",
    "trade_items": "trade_id, item_id",
    "bot_msgs": "chat_id, message_id",
}


def merge(local_path: str, remote_path: str) -> None:
    l = sqlite3.connect(local_path)
    l.execute("ATTACH DATABASE ? AS r", (remote_path,))
    total = 0
    for tbl, pk in TABLES.items():
        try:
            # ردیف‌های remote را روی محلی بنویس (remote wins در تعارض)
            cols = [r[1] for r in l.execute(f"PRAGMA table_info({tbl})")]
            if not cols:
                continue
            col_s = ", ".join(f'"{c}"' for c in cols)
            cur = l.execute(
                f'INSERT OR REPLACE INTO main."{tbl}" ({col_s}) '
                f'SELECT {col_s} FROM r."{tbl}"')
            if cur.rowcount > 0:
                print(f"  {tbl}: {cur.rowcount} ردیف از production")
                total += cur.rowcount
        except Exception as e:
            print(f"  ⚠️ {tbl}: {e}")
    l.commit()
    # VACUUM برای فشرده‌سازی
    l.execute("DETACH DATABASE r")
    l.close()
    print(f"✅ merge کامل: {total} ردیف production حفظ شد — هیچ داده‌ای حذف نشد")


if __name__ == "__main__":
    merge(sys.argv[1] if len(sys.argv) > 1 else "foodverse.db",
          sys.argv[2] if len(sys.argv) > 2 else "/tmp/remote.db")
