# 28 days of replies: 30 → 40 → 50 → 60 a day (@llermaly)

Public tracker for Gustavo Llermaly's ([@llermaly](https://x.com/llermaly)) reply challenge on X.
The challenge is **exactly 4 weeks (28 days)**, UTC-5:

| Week | Days | Dates | Goal |
|---|---|---|---|
| 1 | 1–7 | Oct 15 – Oct 21, 2026 | 30 replies a day |
| 2 | 8–14 | Oct 22 – Oct 28 | 40 a day |
| 3 | 15–21 | Oct 29 – Nov 4 | 50 a day |
| 4 | 22–28 | Nov 5 – Nov 11, 2026 | 60 a day |

Day 1 = 2026-10-15, day 28 = 2026-11-11 (1,260 replies if every goal is hit exactly). Baseline: 145 followers at the start of day 1.
After Nov 11 the page switches to a "challenge complete" summary; later replies don't count.

Live site: https://llermaly.github.io/replies-challenge/

## What's here
| File | Purpose |
|---|---|
| `index.html` | The whole site: one static file, inline CSS/JS, no CDNs. X-style layout (profile header, pinned post, tweet cards, right rail). Reads `data.json`. The only other request is the avatar from unavatar.io, with a generated "GL" avatar as fallback. |
| `og.png` | 1200×630 social preview image (`og:image` / `twitter:card summary_large_image`). Static; regenerate it by hand if the copy changes. |
| `data.json` | Generated data the page reads (cache-busted fetch). Do not edit by hand. |
| `data/replies.jsonl`, `data/history.jsonl` | Raw stored replies and hourly follower snapshots. |
| `collect.py` | Stdlib-only collector. Merges X data and rebuilds `data.json`. See `COLLECT.md`. |
| `run_followers_loop.sh` | Local alternative to the hourly workflow (runs `followers-only` every hour). |
| `.github/workflows/pages.yml` | Deploys to GitHub Pages on push to `main`, manual dispatch, or when called by the hourly job. |
| `.github/workflows/followers.yml` | Hourly cron: `python3 collect.py followers-only`, commits `data.json` + `data/` if changed, then deploys. |

## data.json shape (main fields)
- `meta`: `start_date`, `end_date`, `total_days` (28), `weeks` (4), `goal_schedule` (4 entries), `baseline`, `announcement`, `updated_at`, `rule`.
- `now`: `date`, `started`, `finished`, `day_number` (1–28), `week_number`, `today_goal`, `today_replies`, `days_left`
  (includes today; 28 before the start, 0 once finished), `streak`, `best_streak`, `days_hit`, `total_replies`, `followers`, `followers_change`, `best_day`.
- `days`: one row per day up to today (never past day 28), `hours`: replies per hour per day, `snapshots`: follower history.
- `top`: 10 most-liked replies; `recent`: 20 most recent counted replies. Both are `{id, url, created_at, text, likes, replies, reposts, views}`.

## GitHub setup (no secrets needed)
1. Push these files to the root of a repo whose default branch is `main`.
2. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Settings → Actions → General → Workflow permissions: allow read and write (the workflow also requests `contents: write` itself).
4. Run "Deploy to GitHub Pages" once from the Actions tab (or push). "Hourly followers snapshot" then runs every hour at :17 UTC
   (also runnable by hand).

A commit pushed with `GITHUB_TOKEN` doesn't trigger other `push` workflows, so `followers.yml` calls `pages.yml`
directly (reusable workflow) after it commits. Replies only advance when an agent runs the ingest steps in `COLLECT.md` and pushes;
that push triggers the normal Pages deploy.

## Local preview
`python3 -m http.server 8765` then open http://localhost:8765/

For previews only, `?now=<ISO time>` overrides the page clock (e.g. `?now=2026-11-03T20:00:00-05:00`) so you can see
mid-challenge or finished states against a test `data.json`. It changes nothing in the data.
