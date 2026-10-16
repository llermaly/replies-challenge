# Hourly collection (agent routine)

Site = this directory (`index.html` + `data.json`, served as-is). Never use X write tools. Read the X MCP guide
(`/home/box/agent-data/plugins/x/third_party/x/skills/x-api-mcp-guide/SKILL.md`) first. Built-in public reads cost no credits
(quota: 30/min, 1000/day; a run uses ~3 reads).

Each run (cwd `/workspace/replies-challenge-tracker`):
1. `python3 collect.py next-query` -> prints the exact tool calls (JSON).
2. Call `x.get_users_by_username` with `user_call.arguments`; save the raw result to `inbox/user.json`.
3. Call `x.search_posts_all` with `new_replies_call.arguments` (uses `since_id` = newest stored reply, so only new posts are read).
   Save raw result to `inbox/posts1.json`. If `meta.next_token` exists, repeat with `pagination_token` (same args) -> `inbox/posts2.json`, ...
   Once a day (first run after 00:00 Panama) also run `daily_likes_refresh_call` (last 3 days) -> `inbox/postsR.json` to refresh like counts.
4. `python3 collect.py ingest --user inbox/user.json --posts inbox/posts1.json [--posts inbox/posts2.json ...]`
   (omit `--user` and add `--fx` if the X user call failed: followers then come from api.fxtwitter.com).
   Ingest is idempotent (dedupes by post id; a rerun within 10 min replaces the last snapshot).
5. Done locally: the site reads `data.json` straight from disk. On GitHub Pages, commit `data.json data/` and push to `main`
   after step 4 (the push triggers `.github/workflows/pages.yml`).

Unattended fallback (followers only, no X connector): `python3 collect.py followers-only`. On GitHub this runs hourly in
`.github/workflows/followers.yml` (commits `data.json data/` as cursor/bot, then deploys Pages; no secrets). Locally, `run_followers_loop.sh`
does the same every hour without committing.
Reply counts only advance when an agent does steps 1-4.

Counting rule: reply to another user (`in_reply_to_user_id` != 45766709); self-thread replies, quotes, retweets excluded.
Challenge day = Panama calendar day (UTC-5); day 1 = 2026-10-16; baseline 145 followers on 2026-10-15.
