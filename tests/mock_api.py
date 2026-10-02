"""A local mock of the Publish.fun API endpoints the submit action calls (tests and CI only)."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer


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



if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    HTTPServer(("127.0.0.1", port), Api).serve_forever()
