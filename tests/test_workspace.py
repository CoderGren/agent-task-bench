import tempfile
import unittest
from pathlib import Path

from agent_task_bench.workspace import Workspace, WorkspaceError


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name))
        self.ws.write_file("src/app.py", "def add(a, b):\n    return a + b\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rejects_escape(self):
        with self.assertRaises(WorkspaceError):
            self.ws.read_file("../secret.txt")

    def test_exact_edit(self):
        self.ws.edit_file("src/app.py", "return a + b", "return a + b + 0")
        self.assertIn("a + b + 0", self.ws.read_file("src/app.py"))

    def test_whitespace_edit_unique(self):
        self.ws.write_file("src/app.py", "def add(a, b):\n        return a + b\n")
        result = self.ws.edit_file("src/app.py", "def add(a, b):\n    return a + b\n", "def add(a, b):\n    return a - b\n")
        self.assertIn("normalized", result)
        text = self.ws.read_file("src/app.py")
        self.assertIn("return a - b", text)
        # File indentation is preserved (8 spaces on the return line).
        self.assertIn("        return a - b", text)

    def test_ambiguous_edit_rejected(self):
        self.ws.write_file("src/app.py", "x = 1\nx = 1\n")
        with self.assertRaises(WorkspaceError):
            self.ws.edit_file("src/app.py", "x = 1", "x = 2")


if __name__ == "__main__":
    unittest.main()
