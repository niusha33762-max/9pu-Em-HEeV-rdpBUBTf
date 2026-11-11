#!/usr/bin/env bash
# قبل از ارسال هر پستی چک می‌کنه که ربات می‌تونه وضعیت (پست‌های دیده‌شده) رو در ریپو ذخیره کنه.
# اگه نتونه، اجرا همین‌جا متوقف می‌شه؛ چون بدون ذخیره‌ی وضعیت، هر اجرا همون پست‌ها رو دوباره می‌فرسته.
set -u
git config user.name "news-bot"
git config user.email "news-bot@users.noreply.github.com"
BR="_bot_push_check"
if git push -q origin "HEAD:refs/heads/$BR" 2>/tmp/push_err.txt; then
  git push -q origin --delete "$BR" || true
  echo "state can be saved"
  exit 0
fi
echo "ERROR: the bot cannot push to the repository, so it would repost the same tweets on every run."
echo "Fix: Settings > Actions > General > Workflow permissions > 'Read and write permissions' > Save."
echo "(also make sure the main branch has no protection rule that blocks pushes)"
echo "--- git error:"
cat /tmp/push_err.txt
exit 1
