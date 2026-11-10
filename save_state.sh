#!/usr/bin/env bash
# وضعیت ربات (sources.json) را در ریپو commit می‌کند؛ اگه همزمان تغییری در ریپو بوده، ادغام می‌کند.
set -u
git config user.name "news-bot"
git config user.email "news-bot@users.noreply.github.com"
git add sources.json filters.json
if git diff --cached --quiet; then
  echo "no state changes"
  exit 0
fi
git commit -q -m "Update state"
for attempt in 1 2 3; do
  git fetch -q origin main
  if git rebase origin/main >/dev/null 2>&1; then
    if git push -q origin HEAD:main; then echo "state saved"; exit 0; fi
  else
    git rebase --abort 2>/dev/null || true
    python3 merge_state.py
    git add sources.json filters.json
    git commit -q -m "Update state (merged)" || true
    if git push -q origin HEAD:main; then echo "state saved (merged)"; exit 0; fi
  fi
  sleep 3
done
echo "state save FAILED"
exit 1
