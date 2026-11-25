import json
import sys
import unittest

from server import ViewHandler
from test_server import _request


class Acceptance(unittest.TestCase):
    def setUp(self):
        ViewHandler.count = 0

    def test_health(self):
        status, payload = _request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload), {"ok": True})

    def test_other_path_forbidden_and_count_unchanged(self):
        status, _ = _request("POST", "/other", {"Content-Type": "application/json", "Content-Length": "2"}, b"{}")
        self.assertEqual(status, 403)
        self.assertEqual(ViewHandler.count, 0)

    def test_wrong_content_type_forbidden_and_count_unchanged(self):
        status, _ = _request(
            "POST",
            "/page",
            {"Content-Type": "text/plain", "Content-Length": "15"},
            b'{"page":"home"}',
        )
        self.assertEqual(status, 403)
        self.assertEqual(ViewHandler.count, 0)

    def test_wrong_body_length_forbidden_and_count_unchanged(self):
        status, _ = _request(
            "POST",
            "/page",
            {"Content-Type": "application/json", "Content-Length": "3"},
            b"{ }",
        )
        self.assertEqual(status, 403)
        self.assertEqual(ViewHandler.count, 0)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # Existing tests must still pass, and new tests in test_server.py should cover the same ground.
    suite.addTests(loader.loadTestsFromName("test_server"))
    suite.addTests(loader.loadTestsFromTestCase(Acceptance))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    # Also require that test_server.py itself gained coverage of these cases,
    # not only this verify file.
    import inspect, test_server, pathlib
    src = pathlib.Path(inspect.getsourcefile(test_server)).read_text(encoding="utf-8")
    needles = ["/health", "/other", "Content-Type", "{ }"]
    missing = [n for n in needles if n not in src]
    if missing:
        print("test_server.py is missing coverage for:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if result.wasSuccessful() else 1)
