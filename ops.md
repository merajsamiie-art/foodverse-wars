# 📋 FOODVERSE WARS — سند عملیات (ops)

## 🟢 وضعیت زنده
- **بات:** @FoodverseWarsBot — آنلاین ۲۴/۷ روی GitHub Actions (ریپوی خصوصی `merajsamiie-art/foodverse-wars`)
- **اجرای فعال:** ورک‌فلو `Foodverse Wars 24/7` — هر ۱۰ دقیقه در صف، هر اجرا تا ~۵٫۷ ساعت، `concurrency: fw-bot` جلوی هم‌پوشانی
- **دیتابیس:** `foodverse.db` (SQLite + WAL) — هر ۶۰ ثانیه چک‌پوینت و کامیت به ریپو + تله‌ی EXIT برای ذخیره‌ی حین لغو. **هرگز دستی reset نشود.**
- **تست‌ها:** ۳۸/۳۸ سبز + pyflakes تمیز (قبل از هر پوش)
- **سیکرت‌ها:** `BOT_TOKEN` و `PAYMENT_CARD` (کارت فقط سمت GitHub، هرگز در سورس)

## 🔬 نتایج تحقیق Bot API (سپتامبر ۲۰۲۶) — مستندات رسمی
| قابلیت | وضعیت | تصمیم |
|---|---|---|
| Custom emoji در پیام بات | فقط اگر **مالک بات Premium** باشد (تغییر فوریه ۲۰۲۶)؛ رندر فقط برای بینندگان Premium، بقیه fallback معمولی | پیاده نشد؛ ID جعلی ممنوع. اگر مالک Premium شد: `<tg-emoji emoji-id="...">👍</tg-emoji>` |
| `setMessageReaction` | ✅ واقعی (API 7.0+)؛ غیر-Premium حداکثر ۱ ری‌اکشن/پیام؛ paid reaction ممنوع | ✅ پیاده شد: `media.react` — کول‌داون‌ها به‌جای پیام، ری‌اکشن ⏳ می‌گذارند |
| `setUserEmojiStatus` | واقعی اما نیازمند Mini App + `requestEmojiStatusAccess` (رضایت کاربر) | مستند شد، پیاده نشد (MVP خارج از scope) |
| Privacy mode | پیش‌فرض روشن؛ بات فقط /command ، ریپلای و منشن را می‌بیند | ✅ **slash-mirror**: هر دستور «fw X» با «/X» هم کار می‌کند + راهنمای خاموش‌کردن (پایین) |
| ادمین‌بودن بات در گروه | ادمین‌ها privacy را دور می‌زنند — همه‌ی پیام‌ها می‌رسد | راه‌حل دوم برای گروه‌ها |
| `setMyCommands` / `setMyDescription` / `setMyShortDescription` | ✅ | ✅ ست شد (۱۳ کامند + توضیحات فارسی) |
| `getWebhookInfo.allowed_updates` | polling کلاینت ست می‌کند | ✅ نشانگر سلامت: `['message','callback_query']` = Dispatcher بالا است |
| `setMyProfilePhoto` | ✅ جدید — عکس پروفایل بات با `InputProfilePhotoStatic` | ✅ ست شد (آواتار برندینگ) |
| `setChatTitle/Photo/Description` | ✅ با ادمینی بات | ✅ کانال برند شد + پست پین‌شده |

## ⚠️ کارهای دستی — وضعیت
1. **Privacy mode:** بات **ادمین هر سه‌جاست** → ادمین‌ها همه‌ی پیام‌ها را می‌بینند، privacy عملاً دور زده شد ✅ (اگر روزی ادمینی گرفته شد: BotFather → `/setprivacy` → Disable + remove/re-add)
2. ~~بات را ادمین کانال کن~~ ✅ انجام شد
3. **آواتار بات:** ✅ با متد جدید رسمی `setMyProfilePhoto` (InputProfilePhotoStatic) ست شد — BotFather لازم نشد
4. **نام صاحب کارت:** ✅ «محسن سمیعی» — env `PAYMENT_HOLDER` در ورک‌فلو
5. **گروه:** عنوان/عکس کانال ست شد؛ برای گروه باید chat_id عددی از اولین پیام گروه استخراج شود (جدول worlds در DB ریپو)
6. ~~پست معرفی کانال~~ ✅ ارسال و پین شد

## 🎮 مرجع دستورها
- **پیوی:** `fw منو` | `fw کارت` | `fw شخصیت [نام]` (عکس اختصاصی) | `fw روزانه` | `fw انبار` | `fw پک` | `fw بازکردن [پک]` | `fw شانس [پک]` | `fw پاس` | `fw جایزه [پله] [رایگان|پرمیوم]` | `fw سفارشی` | `fw بپوش [کازمتیک]` | `fw دربیاور [نوع]` | `fw خرید` | `fw سفارش [محصول]` | `fw لغو` | `fw رسید [شماره پیگیری]` (یا عکس + کپشن) | `fw رتبه [قدرت|ثروت|کشته|باس]` | `fw راهنما` + `/start` …
- **گروه:** `fw شروع` (۴ نفر) | `fw پایگاه` | `fw ارتقا [ساختمان]` | `fw مستعمره [بازیکن]` | `fw غارت [بازیکن]` | `fw جذب [واحد] [تعداد]` | `fw جنگ [بازیکن]` | `fw باس` (حمله) | `fw ساخت [آیتم]` | `fw تفریخ` | `fw تجهیز [آیتم]` | `fw بازار` | `fw خرید [منبع] [تعداد]` | `fw فروش [منبع] [تعداد]` | `fw بفروش [آیتم] [قیمت]` | `fw برداشتن [شماره]` | `fw قیمت‌ها` | `fw تأسیس/عضویت/ترک/خیانت/کمک` | `fw روزانه` | `fw فروشگاه` | `fw تخفیف‌ها`
- **همه‌ی دستورهای بالا با اسلش هم کار می‌کنند:** `/جنگ علی` ≡ `fw جنگ علی`
- **ادمین (ریپلای برای بن/حذف‌بن):** `fw مدیر` | `fw پیام [متن]` | `fw بن` | `fw حذف‌بن` | `fw هدیه [شناسه] [چیز] [تعداد]` | `fw باس` (اسپاون اجباری) | `fw آمار` | `fw تصویر [کلید]` (ریپلای عکس) | `fw پیش‌نمایش [کلید]` | `fw حذف‌تصویر [کلید]` | `fw رسیدها` | `fw قیمت [محصول] [تومان]`

## 🏗 معماری
```
GitHub Actions (ubuntu) ── unzip fw-app.zip ── pip install ── run.py
   │ aiogram 3.13 polling (message + callback_query)          ├── تراتل ۲۰/دقیقه + سپر خطا (میدل‌ور)
   │ EventEngine ساعتی: decay قیمت‌ها ─ چرخش فروشگاه ─ اسپاون باس ─ امبیانس
   └── foodverse.db ← هر ۶۰ ثانیه wal_checkpoint + commit + push
میدل‌ورها: PerfMiddleware (outer) / StatsMiddleware — کرش هیچ‌وقت بات را نمی‌کشد
Media: assets/img/*.jpg → اولین send → file_id در جدول media → بعداً فقط file_id
کارت پروفایل: Pillow + Vazirmatn + arabic_reshaper/bidi — کش در /tmp/fw_cards
تعارض getUpdates (دو نمونه): TelegramConflictError → exit 2 → اجرای بعدی از صف
```

## 🔧 نگهداری
- **به‌روزرسانی کد:** تغییر فایل‌ها → `zip -rq fw-app.zip *.py requirements.txt assets/` → کامیت → پوش → cancel اجرای فعال + dispatch جدید (یا صف خودش ادامه می‌دهد تا ۱۰ دقیقه بعد)
- **لاگ اجرا:** Actions tab → run جاری → job logs (BlobNotFound یعنی هنوز flush نشده)
- **نگهبانی:** `keepalive.yml` هر دوشنبه کامیت خالی — جلوگیری از خاموشی ۶۰روزه
- **کارآزمایی سلامت:** `getWebhookInfo.allowed_updates == ['message','callback_query']` → بات در حال poll است

## 💳 پرداخت کارت‌به‌کارت (بدون P2W)
- محصولات: پک‌ها + Battle Passها (قیمت‌ها از پنل ادمین با «fw قیمت [محصول] [تومان]» قابل تغییر)
- جریان: `fw سفارش [محصول]` → Order ID یکتا (FW-…) + انقضا ۳۰ دقیقه → کارت‌به‌کارت → `fw رسید [شماره پیگیری]` یا عکس+کپشن → دکمه‌ی تأیید/رد برای ادمین → اعطا
- ضدتقلب: شماره پیگیری یکتا + هش عکس یکتا (هر دو چک می‌شوند) + وضعیت‌های pending_payment/pending_review/decided
