#!/usr/bin/env python3
"""Copy the live agent files from publish.fun into this repo.

publish.fun generates these from the code that serves its API, so they are the
source of truth; this repo only mirrors them. When anything changed, the
plugin's version is bumped so Claude Code users receive the update.
Standard library only. Exit status 0 whether or not anything changed.
"""
import datetime, json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://publish.fun"
FILES = {
    "/.well-known/agent-skills/publish-fun/SKILL.md": ["plugins/publish-fun/skills/publish-fun/SKILL.md", "skills/publish-fun/SKILL.md"],
    "/api/mcp/server-card": ["mcp/server-card.json"],
}

def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "publishfun-agent-kit-sync/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise SystemExit(f"{path}: HTTP {r.status}")
        return r.read()

changed = False
for path, targets in FILES.items():
    body = fetch(path)
    if path.endswith("server-card"):
        body = (json.dumps(json.loads(body), indent=2) + "\n").encode()
    for t in targets:
        f = ROOT / t
        if not f.exists() or f.read_bytes() != body:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(body)
            changed = True
            print("updated", t)

if changed:
    manifest = ROOT / "plugins/publish-fun/.claude-plugin/plugin.json"
    data = json.loads(manifest.read_text())
    data["version"] = "1.0." + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
    manifest.write_text(json.dumps(data, indent=2) + "\n")
    print("plugin version", data["version"])
else:
    print("no change")
