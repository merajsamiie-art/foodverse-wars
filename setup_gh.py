# 🔧 ست کردن secrets ریپوی foodverse-wars (یک‌بار مصرف)
import base64
import json
import urllib.request

import nacl.encoding
import nacl.public

GH = open("/home/user/.fwgh").read().strip()
REPO = "merajsamiie-art/foodverse-wars"

SECRETS = {
    "BOT_TOKEN": open("/home/user/.fwtoken").read().strip(),
    "ADMIN_IDS": "8694290031",
    "CHANNEL_ID": "-1003946888531",
}


def api(path, data=None, method=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(data).encode() if data else None,
        method=method or ("PUT" if data else "GET"),
        headers={"Authorization": f"Bearer {GH}",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        body = r.read()
        return r.status, json.loads(body) if body else {}


# 1) pubkey ریپو
status, pk = api("actions/secrets/public-key")
assert status == 200, pk
key = nacl.public.PublicKey(pk["key"].encode(), nacl.encoding.Base64Encoder())

# 2) رمز و ست
for name, value in SECRETS.items():
    enc = nacl.public.SealedBox(key).encrypt(value.encode())
    status, res = api(f"actions/secrets/{name}",
                      {"encrypted_value": base64.b64encode(enc).decode(),
                       "key_id": pk["key_id"]})
    print(name, "->", status)
