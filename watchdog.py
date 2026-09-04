# 🐕 Watchdog — ربات خاموش شد؟ اعلام + پین در کانال و گروه؛ درست شد؟ پاک کردن
# اجرا از GitHub Actions هر ۱۵ دقیقه. وضعیت در watchdog_state.json (همان ریپو).
import datetime
import json
import os

import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "merajsamiie-art/foodverse-wars")
GH = os.environ.get("GH_TOKEN", "")
BT = os.environ.get("BOT_TOKEN", "")
CHANNEL = -1003946888531     # @FoodverseWars
GROUP = -1004494394922       # گروه نبرد
STATE_FILE = "watchdog_state.json"
GRACE_S = 20 * 60            # گپ طبیعی بین دو اجرای ربات

DOWN_TEXT = ("⚠️ <b>فوودورس موقتاً خاموش است!</b>\n\n"
             "داریم درستش می‌کنیم — کمی صبور باشید. 🙏\n"
             "این پیام بعد از برگشتن ربات خودش پاک می‌شود.")


def gh(path, method="GET", body=None, raw=False):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"token {GH}", "Accept": "application/vnd.github+json",
                 "User-Agent": "fw-watchdog"},
        method=method, data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req) as r:
        d = r.read()
        return (r.status, json.loads(d) if d and not raw else d)


def tg(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BT}/{method}", data=data,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()).get("result", {})
    except Exception as e:
        print("tg error:", method, e)
        return {}


def bot_alive() -> bool:
    try:
        st, runs = gh(f"/repos/{REPO}/actions/workflows/bot.yml/runs?per_page=6")
        for r in runs.get("workflow_runs", []):
            if r["status"] in ("in_progress", "queued"):
                return True
        # گپ طبیعی بین دو اجرا؟ آخرین run تازه تمام شده باشد → صبر
        last = runs.get("workflow_runs", [{}])[0]
        if not last:
            return True   # ندیدیم → نگو خاموش
        updated = datetime.datetime.strptime(
            last["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - updated).total_seconds()
        return age < GRACE_S
    except Exception as e:
        print("alive check error:", e)
        return True        # خطای دید → نگو خاموش (فاح الگارم)


def read_state() -> dict:
    try:
        st, c = gh(f"/repos/{REPO}/contents/{STATE_FILE}", raw=False)
        import base64
        return json.loads(base64.b64decode(c["content"])), c.get("sha")
    except Exception:
        return {}, None


def write_state(state: dict, sha=None):
    import base64
    body = {"message": "🐕 watchdog state", "content": base64.b64encode(
        json.dumps(state).encode()).decode()}
    if sha:
        body["sha"] = sha
    try:
        gh(f"/repos/{REPO}/contents/{STATE_FILE}", "PUT", body)
    except Exception as e:
        print("state write error:", e)


def main():
    alive = bot_alive()
    state, sha = read_state()
    was_down = bool(state.get("channel_msg"))
    print(f"alive={alive} was_down={was_down}")
    if not alive and not was_down:
        # 🔴 خاموش شد → اعلام + پین
        cm = tg("sendMessage", chat_id=CHANNEL, text=DOWN_TEXT, parse_mode="HTML")
        gm = tg("sendMessage", chat_id=GROUP, text=DOWN_TEXT, parse_mode="HTML")
        if cm.get("message_id"):
            tg("pinChatMessage", chat_id=CHANNEL, message_id=cm["message_id"])
        if gm.get("message_id"):
            tg("pinChatMessage", chat_id=GROUP, message_id=gm["message_id"])
        write_state({"channel_msg": cm.get("message_id"), "group_msg": gm.get("message_id")}, sha)
        print("🟢 اعلام خاموشی پست و پین شد")
    elif alive and was_down:
        # 🟢 برگشت → پاک کردن پیام‌ها و پین‌ها
        if state.get("channel_msg"):
            tg("unpinChatMessage", chat_id=CHANNEL, message_id=state["channel_msg"])
            tg("deleteMessage", chat_id=CHANNEL, message_id=state["channel_msg"])
        if state.get("group_msg"):
            tg("unpinChatMessage", chat_id=GROUP, message_id=state["group_msg"])
            tg("deleteMessage", chat_id=GROUP, message_id=state["group_msg"])
        write_state({}, sha)
        tg("sendMessage", chat_id=CHANNEL,
           text="✅ فوودورس برگشت! جنگ ادامه دارد. 🍔⚔️", parse_mode="HTML")
        print("🟢 برگشت اعلام شد")


if __name__ == "__main__":
    main()
