import tempfile
import unittest
from pathlib import Path

from agent_task_bench.runner import run_task
from agent_task_bench.tasks import load_pack


PACK = Path(__file__).resolve().parents[1] / "tasks" / "pack-v1"


class ScriptedChat:
    """Return a canned sequence of assistant messages."""

    def __init__(self, script):
        self.script = list(script)

    def __call__(self, messages, text_format):
        if not self.script:
            return {"role": "assistant", "content": "done"}
        return self.script.pop(0)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.tasks = {task.id: task for task in load_pack(PACK)}

    def tearDown(self):
        self.tmp.cleanup()

    def test_t1_scripted_pass(self):
        new_doc = (
            "# Development\n\n"
            "Run the CI suites from the repository root:\n\n"
            "```\n"
            "python3 -m unittest discover -s src -p 'test_*.py'\n"
            "```\n\n"
            "The Checks workflow is the release list.\n\n"
            "## Other script suites (not in CI)\n\n"
            "These suites are not in the Checks workflow.\n\n"
            "```\n"
            "python3 -m unittest scripts/test_backup.py\n"
            "python3 -m unittest scripts/test_dns.py\n"
            "python3 -m unittest scripts/test_guard.py\n"
            "```\n"
        )
        chat = ScriptedChat([
            {"role": "assistant", "content": '<tool_call>{"name": "read_file", "arguments": {"path": "DEVELOPMENT.md"}}</tool_call>'},
            {"role": "assistant", "content": '<tool_call>{"name": "write_file", "arguments": {"path": "DEVELOPMENT.md", "content": ' + repr(new_doc)[1:-1].join(['"', '"']) + "}}</tool_call>"},
        ])
        # Build the second call more safely with a native tool_call.
        chat.script[1] = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "write_file",
                        "arguments": {"path": "DEVELOPMENT.md", "content": new_doc},
                    }
                }
            ],
        }
        score = run_task(self.tasks["T1_docs"], self.work, chat=chat)
        self.assertTrue(score.passed, [v.stderr for v in score.verify])

    def test_t2_scripted_pass(self):
        chat = ScriptedChat([
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "edit_file",
                            "arguments": {
                                "path": "cli.py",
                                "old": '        if color not in allowed_group:\n            raise ValueError("color must be white or red")',
                                "new": '        if color not in allowed_group:\n            raise ValueError("color must be white, red, or off")',
                            },
                        }
                    }
                ],
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "write_file",
                            "arguments": {
                                "path": "test_cli.py",
                                "content": (
                                    "import unittest\n"
                                    "from cli import request\n\n"
                                    "class ExistingTests(unittest.TestCase):\n"
                                    "    def test_set_white(self):\n"
                                    "        self.assertEqual(request(\"set\", \"white\")[\"ok\"], True)\n\n"
                                    "class NetworkGroupTests(unittest.TestCase):\n"
                                    "    def test_set_group_rejects_blue(self):\n"
                                    "        with self.assertRaises(ValueError) as ctx:\n"
                                    "            request(\"set_group\", \"blue\", lights=[1])\n"
                                    "        self.assertIn(\"off\", str(ctx.exception))\n"
                                    "    def test_set_still_white_or_red(self):\n"
                                    "        with self.assertRaises(ValueError) as ctx:\n"
                                    "            request(\"set\", \"blue\")\n"
                                    "        self.assertIn(\"white or red\", str(ctx.exception))\n"
                                    "        self.assertNotIn(\"off\", str(ctx.exception))\n\n"
                                    "if __name__ == \"__main__\":\n"
                                    "    unittest.main()\n"
                                ),
                            },
                        }
                    }
                ],
            },
        ])
        score = run_task(self.tasks["T2_error_message"], self.work, chat=chat)
        self.assertTrue(score.passed, [v.stderr for v in score.verify])

    def test_unsolved_task_fails(self):
        chat = ScriptedChat([{"role": "assistant", "content": "I cannot do this."}])
        score = run_task(self.tasks["T1_docs"], self.work, chat=chat)
        self.assertFalse(score.passed)
        self.assertEqual(score.steps_used, 1)


if __name__ == "__main__":
    unittest.main()
