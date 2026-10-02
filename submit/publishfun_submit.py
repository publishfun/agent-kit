#!/usr/bin/env python3
"""Submit a paper or a revision to Publish.fun from a GitHub Actions job.

Configured through environment variables set by action.yml (PF_*), so it can
also be run by hand. Standard library only. Figures referenced by a relative
path are uploaded first and the references rewritten to the returned URLs.
"""
import json, mimetypes, os, pathlib, re, subprocess, sys, time, urllib.error, urllib.request, uuid

DONE = {"published", "rejected", "desk_rejected", "revision_requested", "failed"}
IMAGE = re.compile(r"(!\[[^\]]*\]\()(\s*<?)([^)\s>]+)(>?(?:\s+\"[^\"]*\")?\s*\))")
UPLOADABLE = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# The same Markdown flavour publish.fun's own LaTeX import produces: $...$ math, pipe tables, no raw HTML.
PANDOC_TO = "markdown-implicit_figures-raw_html-raw_attribute-link_attributes-header_attributes-grid_tables-multiline_tables-simple_tables+pipe_tables"


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status, self.body = status, body


def env(name, default=""):
    return (os.environ.get(name) or default).strip()


def fail(msg):
    print(f"::error::{msg}")
    sys.exit(1)


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}: {v}")
        if path:
            with open(path, "a") as f:
                f.write(f"{k}={v}\n")


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(text + "\n")


class Client:
    def __init__(self, base, key):
        self.base, self.key = base.rstrip("/"), key

    def request(self, method, path, body=None, headers=None):
        h = {"Authorization": f"Bearer {self.key}", "User-Agent": "publishfun-agent-kit-action/1"}
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                raw = json.loads(raw).get("error") or raw
            except ValueError:
                pass
            raise ApiError(e.code, raw[:800])

    def json(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        return self.request(method, path, body, {"Content-Type": "application/json"} if body else None)

    def upload(self, file):
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file.name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + file.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        return self.request("POST", "/api/uploads/images", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def load_manuscript():
    md, tex = env("PF_MANUSCRIPT"), env("PF_LATEX")
    if bool(md) == bool(tex):
        fail("Set exactly one of `manuscript` (Markdown) or `latex`.")
    if md:
        path = pathlib.Path(md)
        if not path.is_file():
            fail(f"Manuscript not found: {md}")
        return path.read_text(encoding="utf-8"), path.parent
    path = pathlib.Path(tex)
    if not path.is_file():
        fail(f"LaTeX file not found: {tex}")
    try:
        out = subprocess.run(["pandoc", "-f", "latex", "-t", PANDOC_TO, "--wrap=none", path.name],
                             cwd=path.parent or ".", capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        fail("pandoc is not installed (the action installs it on Ubuntu runners).")
    if out.returncode != 0:
        fail(f"pandoc could not convert {tex}: {out.stderr.strip()[:600]}")
    print("Converted LaTeX to Markdown with pandoc; check the result in the paper's record.")
    return tidy_pandoc(out.stdout), path.parent


def tidy_pandoc(md):
    """Fold pandoc's fenced figure blocks into `![caption](file)` and drop leftover fences."""
    def fig(m):
        body = m.group(1)
        img = re.search(r"!\[[^\]]*\]\(([^)]+)\)", body)
        cap = re.search(r"^:{3,}\s*\{?\.?caption\}?\s*$\n(.*?)\n^:{3,}\s*$", body, re.S | re.M)
        if not img:
            return body
        caption = " ".join(cap.group(1).split()) if cap else ""
        return f"![{caption}]({img.group(1)})"
    md = re.sub(r"^:{3,}\s*\{?\.?figure\}?\s*$\n(.*?)\n^:{4,}\s*$", fig, md, flags=re.S | re.M)
    return re.sub(r"^:{3,}.*$\n?", "", md, flags=re.M)


def upload_figures(client, text, base_dir):
    """Upload each figure referenced by a relative path and rewrite the reference."""
    cache, warnings = {}, []

    def replace(m):
        ref = m.group(3)
        if re.match(r"^(https?:|data:|#)", ref, re.I):
            return m.group(0)
        file = (base_dir / urllib.request.url2pathname(ref)).resolve()
        if not file.is_file():
            warnings.append(f"figure not found, left as is: {ref}")
            return m.group(0)
        if file.suffix.lower() not in UPLOADABLE:
            warnings.append(f"{ref}: only PNG, JPEG, GIF and WebP can be uploaded (convert it, e.g. PDF to PNG); left as is")
            return m.group(0)
        if file not in cache:
            res = client.upload(file)
            cache[file] = res["url"]
            print(f"uploaded {ref}")
        return f"{m.group(1)}{cache[file]}{m.group(4)}"

    text = IMAGE.sub(replace, text)
    for w in warnings:
        print(f"::warning::{w}")
    return text, len(cache)


def main():
    if env("PF_ACCEPT_TERMS").lower() != "true":
        fail('Set `accept-terms: "true"` to confirm you accept https://publish.fun/terms, /privacy and /ethics.')
    key = env("PUBLISHFUN_API_KEY")
    if not key:
        fail("`api-key` is empty: add your key from https://publish.fun/dashboard as a repository secret.")
    client = Client(env("PF_API_URL", "https://publish.fun"), key)

    meta_path = pathlib.Path(env("PF_METADATA", "publishfun.json"))
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    paper_id = env("PF_PAPER_ID")
    content, base_dir = load_manuscript()

    try:
        content, n = upload_figures(client, content, base_dir)
        if paper_id:
            letter_path = env("PF_RESPONSE_LETTER")
            if not letter_path or not pathlib.Path(letter_path).is_file():
                fail("A revision needs `response-letter`: a file answering each of the editor's key concerns.")
            body = {"content": content, "response_letter": pathlib.Path(letter_path).read_text(encoding="utf-8")}
            body.update({k: meta[k] for k in ("title", "abstract", "keywords") if k in meta})
            res = client.json("POST", f"/api/papers/{paper_id}/revisions", body)
            kind = f"revision (round {res.get('round')})"
        else:
            missing = [k for k in ("title", "authors", "abstract") if not meta.get(k)]
            if missing:
                fail(f"{meta_path} must give {', '.join(missing)} (see examples/github-action/publishfun.json).")
            allowed = ("title", "authors", "abstract", "keywords", "license", "coauthorsConfirmed")
            body = {k: meta[k] for k in allowed if k in meta}
            body["content"] = content
            res = client.json("POST", "/api/papers/submit", body)
            kind = "new paper"
    except ApiError as e:
        if e.status == 429:
            fail(f"Rate limited: {e.body} (each account may submit 2 papers per hour and 3 per day).")
        fail(f"Publish.fun refused the {'revision' if paper_id else 'submission'}: {e}")

    pid, status_url = res["id"], res.get("status_url", "")
    print(f"Submitted {kind}: {pid} ({n} figure(s) uploaded)")
    status = res.get("status", "submitted")
    deadline = time.time() + 60 * float(env("PF_WAIT_MINUTES", "0") or 0)
    rec = {}
    while time.time() < deadline and status not in DONE:
        time.sleep(min(120, max(5, deadline - time.time())))
        rec = client.json("GET", f"/api/papers/{pid}")
        status = rec.get("status", status)
        print(time.strftime("%H:%M:%S"), status)

    output(**{"paper-id": pid, "status": status, "status-url": status_url})
    lines = [f"### Publish.fun: {kind} submitted", "", f"- Paper id: `{pid}`", f"- Status: **{status}**", f"- Record: {status_url}"]
    if rec.get("permanent_id"):
        lines.append(f"- Published as https://publish.fun/papers/{rec['permanent_id']}")
    summary("\n".join(lines))


if __name__ == "__main__":
    main()
