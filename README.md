# 30 replies a day, +10 every week (@llermaly)

Public tracker for Gustavo Llermaly's ([@llermaly](https://x.com/llermaly)) reply challenge on X:
**30 replies a day in week 1, then +10 every week** (40, 50, 60…). Day 1 = 2026-10-16 (Panama, UTC-5);
baseline 145 followers on 2026-10-15.

## What's here
| File | Purpose |
|---|---|
| `index.html` | The whole site: one static file, inline CSS/JS, no external requests except `data.json`. |
| `data.json` | Generated data the page reads (cache-busted fetch). Do not edit by hand. |
| `data/replies.jsonl`, `data/history.jsonl` | Raw stored replies and hourly follower snapshots. |
| `collect.py` | Stdlib-only collector. Merges X data and rebuilds `data.json`. See `COLLECT.md`. |
| `run_followers_loop.sh` | Local alternative to the hourly workflow (runs `followers-only` every hour). |
| `.github/workflows/pages.yml` | Deploys to GitHub Pages on push to `main`, manual dispatch, or when called by the hourly job. |
| `.github/workflows/followers.yml` | Hourly cron: `python3 collect.py followers-only`, commits `data.json` + `data/` if changed, then deploys. |

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
