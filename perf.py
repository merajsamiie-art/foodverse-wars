# ⚡ Perf Layer — کش، کول‌داون حافظه‌ای، تراتل، آمار
# طراحی برای بار سنگین: هر چیز گران = کش، هر نوشتن اضافه = حذف.
import time

# ─── ⏱ کول‌داون‌های حافظه‌ای (بدون نوشتن DB در هر دستور) ───
_cds: dict[tuple, float] = {}
_cd_cap = 50_000          # جلوگیری از رشد بی‌نهایت


def cd_set(key: tuple, secs: float):
    if len(_cds) > _cd_cap:
        _prune_cds()
    _cds[key] = time.time() + secs


def cd_on(key: tuple) -> bool:
    exp = _cds.get(key)
    return bool(exp and exp > time.time())


def cd_left(key: tuple) -> int:
    exp = _cds.get(key) or 0
    return max(0, int(exp - time.time()))


def cd_clear_all():
    _cds.clear()


def _prune_cds():
    t = time.time()
    for k in [k for k, v in _cds.items() if v < t]:
        _cds.pop(k, None)


# ─── 🧠 کش TTL عمومی ───
class TTLCache:
    """کش ساده‌ی thread-safe با انقضا — برای مقادیر گران‌قیمت محاسباتی."""

    def __init__(self, name: str, ttl: float = 60.0, maxsize: int = 20_000):
        self.name = name
        self.ttl = ttl
        self.maxsize = maxsize
        self._d: dict = {}
        self.hits = 0
        self.misses = 0

    def get(self, key):
        v = self._d.get(key)
        if v and v[1] > time.time():
            self.hits += 1
            return v[0]
        if v:
            self._d.pop(key, None)
        self.misses += 1
        return None

    def set(self, key, val):
        if len(self._d) >= self.maxsize:
            # حذف ۲۵٪ قدیمی‌ترین‌ها
            for k in list(self._d.keys())[: len(self._d) // 4]:
                self._d.pop(k, None)
        self._d[key] = (val, time.time() + self.ttl)

    def drop(self, key):
        self._d.pop(key, None)

    def clear(self):
        self._d.clear()

    def ratio(self) -> str:
        t = self.hits + self.misses
        return f"{(self.hits / t * 100):.0f}%" if t else "—"


# کش‌های سراسری بازی
POWER_CACHE = TTLCache("power", ttl=120)      # قدرت ارتش (pid)
BONUS_CACHE = TTLCache("bonus", ttl=120)      # بونوس تجهیزات/ساختمان (pid)
BLD_CACHE = TTLCache("bld", ttl=300)          # ساختمان‌ها (pid)
LB_CACHE = TTLCache("leaderboard", ttl=30)    # رتبه‌بندی‌ها (chat_id یا 'global')


def invalidate_player(pid: int):
    """هر تغییری که قدرت/بونوس/ساختمان را عوض می‌کند این را صدا بزند."""
    POWER_CACHE.drop(pid)
    BONUS_CACHE.drop(pid)
    BONUS_CACHE.drop(("stats", pid))   # کلید army_stats
    BLD_CACHE.drop(pid)


# ─── 🚦 تراتل (ضد اسپم/ضد فلود) ───
_buckets: dict[int, list] = {}


def allow(user_id: int, limit: int, window: float) -> bool:
    """اسلایدینگ-ویندو: حداکثر `limit` رویداد در `window` ثانیه."""
    t = time.time()
    b = _buckets.get(user_id)
    if not b:
        b = []
        _buckets[user_id] = b
    while b and b[0] < t - window:
        b.pop(0)
    if len(b) >= limit:
        return False
    b.append(t)
    return True


# ─── 📊 آمار زنده ───
class Stats:
    def __init__(self):
        self.t0 = time.time()
        self.msgs = 0
        self.commands = 0
        self.callbacks = 0
        self.throttled = 0
        self.errors = 0
        self.cache_hit = 0
        self.cache_miss = 0

    def text(self) -> str:
        up = time.time() - self.t0
        h, rem = int(up // 3600), int(up % 3600)
        return (f"📊 <b>FOODVERSE STATS</b> (آپ‌تایم {h}س {rem}د)\n"
                f"💬 پیام: {self.msgs:,} | ⌨️ دستور: {self.commands:,} | 👆 دکمه: {self.callbacks:,}\n"
                f"🚦 تراتل‌شده: {self.throttled:,} | ❌ خطا: {self.errors:,}\n"
                f"🧠 کش قدرت: {POWER_CACHE.ratio()} | کش رتبه: {LB_CACHE.ratio()}")


STATS = Stats()


# ─── 🔢 کمک‌های عمومی ───
def fmt(n) -> str:
    """عدد با جداکننده."""
    try:
        return f"{float(n):,.0f}"
    except (TypeError, ValueError):
        return str(n)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ─── 🔒 قفل کلید — ضد دابل‌کلیک/ریس‌کاندیشن (قوی‌تر از Redis در تک‌پردازش) ───
import threading as _threading

_locks_guard = _threading.Lock()
_locks: dict = {}


def key_lock(key: tuple):
    """با `with perf.key_lock(('pack', uid)):` — عملیات حساس اتمی می‌شود."""
    with _locks_guard:
        if key not in _locks:
            _locks[key] = _threading.Lock()
        return _locks[key]
