import json
from http.server import BaseHTTPRequestHandler

class ViewHandler(BaseHTTPRequestHandler):
    count = 0
    EXPECTED = b'{"page":"home"}'

    def do_GET(self):
        if self.path == "/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/page":
            self.send_error(403)
            return
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length)
        if ctype != "application/json" or body != self.EXPECTED:
            self.send_error(403)
            return
        type(self).count += 1
        payload = json.dumps({"count": type(self).count}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return
