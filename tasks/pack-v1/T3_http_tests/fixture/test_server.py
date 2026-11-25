import io
import json
import unittest
from http.client import HTTPMessage

from server import ViewHandler


class _Socket:
    def __init__(self):
        self.output = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "r" in mode:
            return io.BytesIO()
        return self.output


def _request(method, path, headers=None, body=b""):
    ViewHandler.rbufsize = 0
    handler = ViewHandler.__new__(ViewHandler)
    handler.request_version = "HTTP/1.1"
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.command = method
    handler.path = path
    handler.headers = HTTPMessage()
    for key, value in (headers or {}).items():
        handler.headers[key] = value
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.close_connection = True
    if method == "GET":
        handler.do_GET()
    else:
        handler.do_POST()
    raw = handler.wfile.getvalue()
    status = int(raw.split(b" ", 2)[1])
    parts = raw.split(b"\r\n\r\n", 1)
    payload = parts[1] if len(parts) > 1 else b""
    return status, payload


class ExistingTests(unittest.TestCase):
    def setUp(self):
        ViewHandler.count = 0

    def test_valid_post_increments(self):
        status, payload = _request(
            "POST",
            "/page",
            {"Content-Type": "application/json", "Content-Length": "15"},
            b'{"page":"home"}',
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["count"], 1)


if __name__ == "__main__":
    unittest.main()
