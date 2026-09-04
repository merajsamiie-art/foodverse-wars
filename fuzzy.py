# 🔍 Fuzzy — تشخیص هوشمند اسم‌ها؛ غلط املایی و اسم سخت مهم نیست
import difflib

_TR = str.maketrans({"ي": "ی", "ك": "ک", "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه",
                     "\u200c": "", " ": "", "‌": ""})


def norm(s: str) -> str:
    """نرمال‌سازی برای مقایسه: بدون فاصله/نیم‌فاصله، ی و ک فارسی."""
    return (s or "").translate(_TR).strip().lower()


def resolve(query: str, catalog: dict, aliases: dict | None = None) -> str | None:
    """بهترین تطبیق. catalog: {key: نام فارسی} | aliases: {key: [نام‌های ساده]}"""
    q = norm(query)
    if not q:
        return None
    names = {norm(v): k for k, v in catalog.items()}
    aliases = aliases or {}
    # ۱) دقیق یا مستعار
    if q in names:
        return names[q]
    for key, al in aliases.items():
        if q in {norm(x) for x in ([al] if isinstance(al, str) else al)}:
            return key
    # ۲) پوشش: کلِ جستجو داخل اسم (پیشوند/بخش)
    for n, key in names.items():
        if q in n:
            return key
    for key, al in aliases.items():
        for a in ([al] if isinstance(al, str) else al):
            if q in norm(a):
                return key
    # ۳) شباهت املایی — غلط تایپی بخشنده است
    m = difflib.get_close_matches(q, list(names), n=1, cutoff=0.60)
    if m:
        return names[m[0]]
    # ۴) شباهت با نام‌های مستعار
    flat = {norm(a): k for k, al in aliases.items()
            for a in ([al] if isinstance(al, str) else al)}
    m = difflib.get_close_matches(q, list(flat), n=1, cutoff=0.60)
    return flat[m[0]] if m else None


# ─── نام‌های ساده‌ی دنیای فوودورس ───
UNIT_ALIAS = {
    "burger": ["برگر", "سرباز برگر"], "fries": ["سیب زمینی", "تیرانداز"],
    "broccoli": ["بروکلی", "پزشک"], "meow": ["میو", "گربه", "دیده بان"],
    "pizza": ["پیتزا", "جنگاور"], "candy": ["شیرینی", "جادویس"],
    "cheese_knight": ["شوالیه", "پنیر"], "lasagnazilla": ["لازاگنی", "زیلا", "دایناسور"],
}
ITEM_ALIAS = {
    "cheese_bomb": ["بمب", "بمب پنیر"], "sauce_rocket": ["موشک", "سس"],
    "burger_tank": ["تانک"], "pizza_mech": ["مک", "مکانیک"],
    "crown_meow": ["تاج میو", "تاج گربه"], "mega_meat": ["گوشت ویژه", "مگا گوشت"],
    "golden_cheese": ["پنیر طلایی", "طلایی"], "toy_crown": ["تاج اسباب بازی"],
    "lasagna_egg": ["تخم لازاگنی", "تخم"],
}
BUILDING_ALIAS = {
    "factory": ["کارخانه"], "lab": ["آزمایشگاه", "لاب"], "training": ["آموزش", "مرکز آموزش"],
    "vault": ["خزانه"], "defense": ["دیوار", "دفاع"], "workshop": ["کارگاه"],
}
BOSS_ALIAS = {
    "mega_burger": ["مگا برگر", "برگر بزرگ"], "meow_king": ["میو کینگ", "پادشاه گربه"],
    "lasagnazilla": ["لازاگنی زیلا"],
}
