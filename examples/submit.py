#!/usr/bin/env python3
"""Submit a Markdown paper to Publish.fun and follow its review.

  export PUBLISHFUN_API_KEY=...        # from https://publish.fun/dashboard
  python3 submit.py paper.md meta.json            # submit, then poll
  python3 submit.py --status <id>                 # poll an existing submission

meta.json holds the metadata fields, e.g.
  {"title": "...", "abstract": "...", "authors": [{"name": "...", "orcid": "..."}],
   "keywords": ["..."], "coauthorsConfirmed": true}

Submitting sends the manuscript to third-party AI model and search providers
and, if accepted, publishes it permanently with its reviews; it also accepts
https://publish.fun/terms, /privacy and /ethics. Standard library only.
"""
import json, os, sys, time, urllib.error, urllib.request

API = "https://publish.fun/api"
KEY = os.environ.get("PUBLISHFUN_API_KEY") or sys.exit("Set PUBLISHFUN_API_KEY (https://publish.fun/dashboard).")
DONE = {"published", "rejected", "desk_rejected", "revision_requested", "failed"}

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path}: HTTP {e.code} {e.read().decode()[:500]}")

def follow(pid):
    while True:
        rec = call("GET", f"/papers/{pid}")
        print(time.strftime("%H:%M:%S"), rec["status"])
        if rec["status"] in DONE:
            decisions = rec.get("decisions") or []
            if decisions:
                print(json.dumps(decisions[-1], indent=2)[:4000])
            return
        time.sleep(180)  # how long a review takes varies; poll every few minutes, not in a tight loop

if __name__ == "__main__":
    if sys.argv[1:2] == ["--status"]:
        follow(sys.argv[2])
    elif len(sys.argv) == 3:
        meta = json.load(open(sys.argv[2]))
        meta["content"] = open(sys.argv[1]).read()
        res = call("POST", "/papers/submit", meta)
        print("submitted", res["id"], "remaining allowance:", res.get("submission_allowance", {}).get("remaining"))
        follow(res["id"])
    else:
        sys.exit(__doc__)
