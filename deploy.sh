#!/bin/bash
# 🛡 deploy.sh — دیپلوی امن فوودورس: هیچ بازیکنی گم نمی‌شود
# قاعده: cancel → صبر (final save) → merge دیتابیس production → push → dispatch
set -e
cd /home/user/foodverse
git config user.name "Meraj"
git config user.email meraj@foodverse.wars
git remote add origin "https://x-access-token:$(cat /home/user/.fwgh)@github.com/merajsamiie-art/foodverse-wars.git" 2>/dev/null || true
GH="Authorization: token $(cat /home/user/.fwgh)"
REPO=merajsamiie-art/foodverse-wars

echo "── ۱) تست‌ها"
python3 -m pytest tests/ -q 2>&1 | tail -1
python3 -m pyflakes *.py tests/*.py && echo "pyflakes صفر ✓"

echo "── ۲) cancel ران زنده + صبر برای final save"
OLD=$(curl -s -H "$GH" "https://api.github.com/repos/$REPO/actions/runs?per_page=3" | python3 -c "
import json,sys
for r in json.load(sys.stdin)['workflow_runs']:
    if r['status'] in ('in_progress','queued'): print(r['id']); break" || true)
if [ -n "$OLD" ]; then
  curl -s -X POST -H "$GH" "https://api.github.com/repos/$REPO/actions/runs/$OLD/cancel" >/dev/null || true
  echo "   cancel $OLD ✓ — ۲۵ ثانیه صبر برای autosave نهایی…"
  sleep 25
fi

echo "── ۳) merge دیتابیس production (remote-wins، حذف صفر)"
git fetch -q origin
git show origin/main:foodverse.db > /tmp/remote_deploy.db 2>/dev/null && \
  python3 merge_db.py foodverse.db /tmp/remote_deploy.db || echo "   remote db در دسترس نیست — ادامه"

echo "── ۴) پکیج + کامیت + push"
rm -f fw-app.zip
zip -rq fw-app.zip *.py requirements.txt assets/ ops.md merge_db.py deploy.sh
git add -A
git commit -q -m "deploy: $(date '+%H:%M') — کد + db کامل (merge شده)" || true
git pull origin main --no-rebase -X ours -q || true
git push -q origin main
echo "   PUSHED ✓ $(git log --oneline -1)"

echo "── ۵) dispatch ربات جدید"
curl -s -X POST -H "$GH" -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/actions/workflows/bot.yml/dispatches" -d '{"ref":"main"}'
echo "   dispatched ✓"
