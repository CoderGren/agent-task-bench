import unittest

from agent_task_bench.parsers import extract_tool_calls, parse_hermes, parse_mistral, parse_qwen_xml, strip_think_blocks
from agent_task_bench.repair import try_parse_json


class RepairTests(unittest.TestCase):
    def test_trailing_comma(self):
        self.assertEqual(try_parse_json('{"name": "read_file", "arguments": {"path": "a.py"},}'),
                         {"name": "read_file", "arguments": {"path": "a.py"}})

    def test_stray_brace_qwen_shape(self):
        raw = '{"name": "read_file", {"arguments": {"path": "cli.py"}}}'
        parsed = try_parse_json(raw)
        self.assertIsInstance(parsed, dict)
        # After repair we should at least recover a name or arguments.
        self.assertTrue("name" in parsed or "arguments" in parsed)

    def test_unescaped_newline_in_string(self):
        raw = '{"name": "write_file", "arguments": {"path": "a.py", "content": "line1\nline2"}}'
        parsed = try_parse_json(raw)
        self.assertEqual(parsed["arguments"]["content"], "line1\nline2")


class ParserTests(unittest.TestCase):
    def test_native_tool_calls(self):
        message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "cli.py"}',
                    },
                }
            ],
        }
        calls = extract_tool_calls(message, "auto")
        self.assertEqual(calls[0]["name"], "read_file")
        self.assertEqual(calls[0]["arguments"]["path"], "cli.py")

    def test_hermes_json(self):
        text = '<tool_call>{"name": "edit_file", "arguments": {"path": "a.md", "old": "x", "new": "y"}}</tool_call>'
        calls = parse_hermes(text)
        self.assertEqual(calls[0]["name"], "edit_file")
        self.assertEqual(calls[0]["arguments"]["path"], "a.md")

    def test_hermes_unclosed(self):
        text = '<tool_call>{"name": "list_dir", "arguments": {"path": "."}}'
        calls = parse_hermes(text)
        self.assertEqual(calls[0]["name"], "list_dir")

    def test_qwen_xml(self):
        text = (
            "<tool_call><function=read_file>"
            "<parameter=path>cli.py</parameter>"
            "</function></tool_call>"
        )
        calls = parse_qwen_xml(text)
        self.assertEqual(calls, [{"name": "read_file", "arguments": {"path": "cli.py"}}])

    def test_mistral(self):
        text = '[TOOL_CALLS][{"name": "list_dir", "arguments": {"path": "."}}]'
        calls = parse_mistral(text)
        self.assertEqual(calls[0]["name"], "list_dir")

    def test_auto_prefers_native(self):
        message = {
            "content": '<tool_call>{"name": "list_dir", "arguments": {}}</tool_call>',
            "tool_calls": [
                {"function": {"name": "read_file", "arguments": '{"path": "x"}'}}
            ],
        }
        calls = extract_tool_calls(message, "auto")
        self.assertEqual(calls[0]["name"], "read_file")

    def test_strip_think(self):
        self.assertEqual(strip_think_blocks("<think>secret plan</think>\nHello"), "Hello")
        self.assertEqual(strip_think_blocks("<think>unclosed"), "")
        self.assertEqual(strip_think_blocks("ok</think>"), "ok")


if __name__ == "__main__":
    unittest.main()
