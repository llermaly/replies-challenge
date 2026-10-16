#!/usr/bin/env python3
"""Replies-a-day tracker (30/day, +10 each week) collector. Stdlib only. Idempotent.

Usage:
  collect.py next-query                      -> JSON telling an agent which X search call to make
  collect.py ingest [--user F] [--posts F ...] [--fx]   merge fetched JSON, snapshot, rebuild data.json
  collect.py followers-only                  -> unattended: fxtwitter snapshot + rebuild (no X connector needed)
  collect.py rebuild                         -> only regenerate data.json
Files F are raw JSON results from the X tools (get_users_by_username / search_posts_all).
"""
import json, os, sys, argparse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ROOT, "data")
REPLIES, HIST, OUT = (os.path.join(D, "replies.jsonl"), os.path.join(D, "history.jsonl"),
                      os.path.join(ROOT, "data.json"))
HANDLE, UID = "llermaly", "45766709"
BASE_GOAL, STEP = 30, 10                      # week 1 = 30/day, then +10 each week (40, 50, 60...)
TZ = timezone(timedelta(hours=-5))            # America/Panama, no DST
START = "2026-10-16"                          # challenge day 1 (Panama)
BASE_DATE, BASE_FOLLOWERS = "2026-10-15", 145
WINDOW_START_UTC = "2026-10-15T05:00:00Z"     # Panama midnight of baseline day
ANNOUNCE = "https://x.com/llermaly/status/2110910573873393725"

def goal_for(daynum):
    return BASE_GOAL + STEP * ((max(daynum, 1) - 1) // 7)

def now_utc(): return datetime.now(timezone.utc)
def iso(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def parse(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def pday(s): return parse(s).astimezone(TZ).strftime("%Y-%m-%d")

def read_jsonl(p):
    if not os.path.exists(p): return []
    return [json.loads(l) for l in open(p) if l.strip()]
def write_jsonl(p, rows):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        for r in rows: f.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")
    os.replace(tmp, p)

def load_json(path):
    t = open(path).read(); i = t.find("{")       # tolerate trailing quota text from the tool
    return json.JSONDecoder().raw_decode(t[i:])[0]

def counts(r):  # reply to someone else (not self-thread), not RT/quote
    return r.get("in_reply_to_user_id") not in (None, UID) and r.get("author_id", UID) == UID

def slim(p):
    pm = p.get("public_metrics", {})
    return {"id": p["id"], "created_at": p["created_at"], "author_id": p.get("author_id", UID),
            "in_reply_to_user_id": p.get("in_reply_to_user_id"),
            "conversation_id": p.get("conversation_id"),
            "text": p.get("text", ""), "likes": pm.get("like_count", 0),
            "replies": pm.get("reply_count", 0), "reposts": pm.get("retweet_count", 0),
            "views": pm.get("impression_count"), "fetched_at": iso(now_utc())}

def merge_posts(files):
    rows = {r["id"]: r for r in read_jsonl(REPLIES)}
    new = 0
    for f in files:
        for p in load_json(f).get("data", []) or []:
            types = [t.get("type") for t in p.get("referenced_tweets", [])]
            if types and types != ["replied_to"]: continue   # quote/retweet etc.
            if p["id"] not in rows: new += 1
            rows[p["id"]] = slim(p)
    out = sorted(rows.values(), key=lambda r: int(r["id"]))
    write_jsonl(REPLIES, out)
    return new

def fx_user():
    req = urllib.request.Request(f"https://api.fxtwitter.com/{HANDLE}", headers={"User-Agent": "replies-tracker/1"})
    u = json.load(urllib.request.urlopen(req, timeout=20))["user"]
    return {"followers": u["followers"], "following": u["following"], "tweets": u["tweets"], "likes": u["likes"], "src": "fxtwitter"}

def x_user(path):
    m = load_json(path)["data"]["public_metrics"]
    return {"followers": m["followers_count"], "following": m["following_count"], "tweets": m["tweet_count"],
            "likes": m["like_count"], "src": "x-api"}

def snapshot(u):
    hist = read_jsonl(HIST); n = now_utc()
    today = pday(iso(n))
    rep_today = sum(1 for r in read_jsonl(REPLIES) if counts(r) and pday(r["created_at"]) == today)
    snap = {"ts": iso(n), "followers": u["followers"], "following": u["following"], "tweets": u["tweets"],
            "replies_today_so_far": rep_today, "src": u["src"]}
    # idempotent: a re-run within 10 minutes replaces the previous snapshot
    if hist and (n - parse(hist[-1]["ts"])).total_seconds() < 600: hist[-1] = snap
    else: hist.append(snap)
    write_jsonl(HIST, hist)

def daterange(a, b):
    d = datetime.strptime(a, "%Y-%m-%d"); e = datetime.strptime(b, "%Y-%m-%d")
    while d <= e: yield d.strftime("%Y-%m-%d"); d += timedelta(days=1)

def rebuild():
    n = now_utc(); today = pday(iso(n))
    replies = [r for r in read_jsonl(REPLIES) if counts(r)]
    hist = read_jsonl(HIST)
    per, hours = {}, {}
    for r in replies:
        dd = pday(r["created_at"]); per[dd] = per.get(dd, 0) + 1
        h = parse(r["created_at"]).astimezone(TZ).hour
        hours.setdefault(dd, [0] * 24)[h] += 1
    first = min([BASE_DATE] + list(per))
    last_f = {}
    for s in hist: last_f[pday(s["ts"])] = s["followers"]
    days, prev = [], BASE_FOLLOWERS
    for dd in daterange(first, max(today, START if today >= START else today)):
        end = last_f.get(dd)
        if dd == BASE_DATE and end is None: end = BASE_FOLLOWERS
        f = end if end is not None else prev
        daynum = (datetime.strptime(dd, "%Y-%m-%d") - datetime.strptime(START, "%Y-%m-%d")).days + 1
        days.append({"date": dd, "day": max(daynum, 0), "replies": per.get(dd, 0), "followers_end": f,
                     "delta": (f - prev) if dd != BASE_DATE else 0, "goal": goal_for(daynum), "hit": per.get(dd, 0) >= goal_for(daynum)})
        prev = f
    chal = [d for d in days if d["date"] >= START]
    streak = 0
    for d in reversed(chal):
        if d["hit"]: streak += 1
        elif d["date"] == today: continue   # today still in progress
        else: break
    cur_f = hist[-1]["followers"] if hist else BASE_FOLLOWERS
    started = today >= START
    dnum = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(START, "%Y-%m-%d")).days + 1
    top = sorted([r for r in replies], key=lambda r: (-r["likes"], -int(r["id"])))[:10]
    out = {
        "meta": {"handle": HANDLE, "goal": BASE_GOAL, "goal_step": STEP, "goal_schedule": [{"week": w, "goal": BASE_GOAL + STEP * (w - 1)} for w in range(1, 9)], "start_date": START, "baseline": {"date": BASE_DATE, "followers": BASE_FOLLOWERS},
                 "tz": "America/Panama (UTC-5)", "announcement": ANNOUNCE, "updated_at": iso(n),
                 "rule": "Counts posts that are replies to other people. Self-thread replies, quotes and retweets are excluded."},
        "now": {"date": today, "started": started, "day_number": dnum if started else 0, "week_number": ((dnum - 1) // 7 + 1) if started else 0,
                "today_goal": goal_for(dnum) if started else BASE_GOAL,
                "today_replies": per.get(today, 0), "streak": streak,
                "total_replies": sum(v for k, v in per.items() if k >= START),
                "warmup_replies": sum(v for k, v in per.items() if k < START),
                "followers": cur_f, "following": hist[-1]["following"] if hist else None,
                "followers_change": cur_f - BASE_FOLLOWERS,
                "best_day": max([d["replies"] for d in chal] or [0])},
        "days": days,
        "hours": hours,
        "snapshots": [{"ts": s["ts"], "followers": s["followers"]} for s in hist],
        "top": [{"id": r["id"], "url": f"https://x.com/{HANDLE}/status/{r['id']}", "created_at": r["created_at"],
                 "text": r["text"][:200], "likes": r["likes"]} for r in top if r["likes"] > 0],
    }
    json.dump(out, open(OUT + ".tmp", "w"), indent=1, ensure_ascii=False); os.replace(OUT + ".tmp", OUT)
    return out

def next_query():
    reps = read_jsonl(REPLIES); n = now_utc()
    q = "from:llermaly is:reply -is:retweet"
    last = max((int(r["id"]) for r in reps), default=None)
    hist = read_jsonl(HIST)
    out = {
        "user_call": {"namespace": "x", "toolName": "get_users_by_username",
                      "arguments": {"username": HANDLE, "user.fields": "public_metrics"}},
        "new_replies_call": {"namespace": "x", "toolName": "search_posts_all", "arguments": (
            {"query": q, "since_id": str(last), "max_results": 25, "post.fields": "created_at,public_metrics,in_reply_to_user_id,conversation_id,referenced_tweets"}
            if last else
            {"query": q, "start_time": WINDOW_START_UTC, "max_results": 25, "post.fields": "created_at,public_metrics,in_reply_to_user_id,conversation_id,referenced_tweets"})},
        "daily_likes_refresh_call": {"when": "first run after 00:00 Panama (or whenever you want fresh like counts); optional",
                                     "arguments": {"query": q, "start_time": iso(n - timedelta(days=3)), "max_results": 25,
                                                   "post.fields": "created_at,public_metrics,in_reply_to_user_id,conversation_id,referenced_tweets"}},
        "note": "If result meta has next_token, call again with pagination_token (keep same params) until absent. Save every raw result to a file and pass each with --posts.",
    }
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["next-query", "ingest", "followers-only", "rebuild"])
    ap.add_argument("--user"); ap.add_argument("--posts", action="append", default=[]); ap.add_argument("--fx", action="store_true")
    a = ap.parse_args(); os.makedirs(D, exist_ok=True)
    if a.cmd == "next-query": next_query(); sys.exit()
    if a.cmd == "rebuild": rebuild(); sys.exit()
    new = merge_posts(a.posts) if a.posts else 0
    if a.cmd == "followers-only" or a.fx:
        u = fx_user()
    elif a.user: 
        u = x_user(a.user)
    else:
        u = None
    if u: snapshot(u)
    o = rebuild()
    print(f"new_replies={new} followers={o['now']['followers']} today={o['now']['today_replies']} total={o['now']['total_replies']}")
