"""Tests for submit/publishfun_submit.py against a local mock of the Publish.fun API."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "submit" / "publishfun_submit.py"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000")


class Api(BaseHTTPRequestHandler):
    calls, mode = [], {}

    def log_message(self, *a):
        pass

    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        Api.calls.append((self.path, self.headers.get("Authorization"), self.headers.get("Content-Type"), body))
        if self.headers.get("Authorization") != "Bearer test-key":
            return self.reply(401, {"error": "bad key"})
        if Api.mode.get("ratelimit"):
            return self.reply(429, {"error": "Submission limit reached"})
        if self.path == "/api/uploads/images":
            n = sum(1 for c in Api.calls if c[0] == self.path)
            return self.reply(201, {"url": f"https://files.example/uploads/fig-{n}.png"})
        if self.path == "/api/papers/submit":
            return self.reply(202, {"id": "p_new", "status": "submitted", "status_url": "http://x/api/papers/p_new"})
        if self.path == "/api/papers/p_old/revisions":
            return self.reply(202, {"id": "p_old", "status": "submitted", "round": 2, "status_url": "http://x/api/papers/p_old"})
        self.reply(404, {"error": "no route"})

    def do_GET(self):
        Api.calls.append((self.path, self.headers.get("Authorization"), None, b""))
        self.reply(200, {"id": "p_new", "status": "published", "permanent_id": "PF-261002.000001"})


class SubmitActionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Api)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Api.calls.clear(); Api.mode.clear()
        self.dir = pathlib.Path(tempfile.mkdtemp())
        (self.dir / "paper").mkdir()
        (self.dir / "paper" / "fig.png").write_bytes(PNG)
        (self.dir / "paper" / "plot.pdf").write_bytes(b"%PDF-1.4")
        (self.dir / "paper" / "paper.md").write_text(
            "# Intro\n\n![Main result](fig.png)\n\n![Again](./fig.png \"t\")\n\n![Remote](https://example.org/a.png)\n\n![Vector](plot.pdf)\n")
        (self.dir / "paper" / "response.md").write_text("Concern 1: fixed in Section 2.")
        (self.dir / "publishfun.json").write_text(json.dumps({
            "title": "A test paper", "authors": [{"name": "A. Author"}], "abstract": "x" * 60, "keywords": ["k"], "extra": "dropped"}))
        self.outputs = self.dir / "out.txt"

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_action(self, **env):
        e = {"PATH": os.environ["PATH"], "PUBLISHFUN_API_KEY": "test-key", "PF_ACCEPT_TERMS": "true", "PF_API_URL": self.url,
             "PF_METADATA": "publishfun.json", "PF_MANUSCRIPT": "paper/paper.md", "GITHUB_OUTPUT": str(self.outputs)}
        e.update(env)
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=self.dir, env=e, capture_output=True, text=True, timeout=60)

    def posted(self, path):
        return [json.loads(c[3]) for c in Api.calls if c[0] == path]

    def test_new_submission_uploads_local_figures_once_and_rewrites_them(self):
        r = self.run_action()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        uploads = [c for c in Api.calls if c[0] == "/api/uploads/images"]
        self.assertEqual(len(uploads), 1)  # fig.png referenced twice, uploaded once; the PDF is not uploadable
        self.assertIn("multipart/form-data", uploads[0][2])
        body = self.posted("/api/papers/submit")[0]
        self.assertEqual(set(body), {"title", "authors", "abstract", "keywords", "content"})
        self.assertIn("![Main result](https://files.example/uploads/fig-1.png)", body["content"])
        self.assertIn('![Again](https://files.example/uploads/fig-1.png "t")', body["content"])
        self.assertIn("![Remote](https://example.org/a.png)", body["content"])
        self.assertIn("![Vector](plot.pdf)", body["content"])
        self.assertIn("::warning::plot.pdf", r.stdout)
        self.assertIn("paper-id=p_new", self.outputs.read_text())

    def test_revision_sends_letter_and_metadata_replacements(self):
        r = self.run_action(PF_PAPER_ID="p_old", PF_RESPONSE_LETTER="paper/response.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = self.posted("/api/papers/p_old/revisions")[0]
        self.assertEqual(set(body), {"content", "response_letter", "title", "abstract", "keywords"})
        self.assertEqual(body["response_letter"], "Concern 1: fixed in Section 2.")
        self.assertFalse(self.posted("/api/papers/submit"))

    def test_revision_without_letter_fails_before_any_call_to_submit(self):
        r = self.run_action(PF_PAPER_ID="p_old")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("response-letter", r.stdout)
        self.assertFalse(self.posted("/api/papers/p_old/revisions"))

    def test_refuses_without_accepting_terms(self):
        r = self.run_action(PF_ACCEPT_TERMS="")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("accept-terms", r.stdout)
        self.assertEqual(Api.calls, [])

    def test_rate_limit_is_explained(self):
        Api.mode["ratelimit"] = True
        (self.dir / "paper" / "paper.md").write_text("# No figures\n")
        r = self.run_action()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("2 papers per hour and 3 per day", r.stdout)

    def test_waits_for_a_decision_when_asked(self):
        (self.dir / "paper" / "paper.md").write_text("# No figures\n")
        r = self.run_action(PF_WAIT_MINUTES="0.1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("status=published", self.outputs.read_text())

    @unittest.skipUnless(shutil.which("pandoc"), "pandoc not installed")
    def test_latex_is_converted_and_its_figures_uploaded(self):
        (self.dir / "paper" / "main.tex").write_text(
            "\\documentclass{article}\\usepackage{graphicx}\\begin{document}\\section{Intro}Text $x^2$."
            "\\begin{figure}\\includegraphics{fig.png}\\caption{Cap}\\end{figure}\\end{document}")
        r = self.run_action(PF_MANUSCRIPT="", PF_LATEX="paper/main.tex")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        content = self.posted("/api/papers/submit")[0]["content"]
        self.assertIn("![Cap](https://files.example/uploads/fig-1.png)", content)
        self.assertIn("$x^2$", content)
        self.assertNotIn(":::", content)


if __name__ == "__main__":
    unittest.main()
