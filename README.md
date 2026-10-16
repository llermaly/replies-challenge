# 100 replies a day tracker (@llermaly)
Static site: `index.html` reads `data.json`. `collect.py` merges X data (`data/replies.jsonl`, `data/history.jsonl`) and regenerates it. See COLLECT.md.
Serve locally: `python3 -m http.server 8765`.
GitHub Pages publishes this site from the `main` branch.
