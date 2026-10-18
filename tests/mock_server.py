"""A tiny stand-in for the fmcc_control HTTP API so the client and UI can be tested without FiveM."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "t" * 32


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body, raw=False):
        data = body if raw else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json" if not raw else "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        srv = self.server
        srv.requests.append({"path": self.path, "auth": self.headers.get("Authorization"),
                             "body": json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")})
        if srv.mode == "html404":
            return self._send(404, b"<html>nope</html>", raw=True)
        if srv.mode == "garbage":
            return self._send(200, b"not json", raw=True)
        if srv.mode == "slow":
            threading.Event().wait(1.5)
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self._send(401, {"ok": False, "error": {"code": "unauthorized", "message": "missing or invalid bearer token"}})
        action = srv.requests[-1]["body"].get("action")
        if action == "players.kick":
            return self._send(403, {"ok": False, "error": {"code": "forbidden", "message": 'role "viewer" may not run players.kick'}})
        if action == "vehicle.spawn":
            return self._send(422, {"ok": False, "error": {"code": "action_failed", "message": "player 9 is not online"}})
        self._send(200, {"ok": True, "data": {"action": action, "echo": srv.requests[-1]["body"].get("params")}})


class MockServer(HTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests, self.mode = [], "normal"
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.shutdown()
        self.server_close()
