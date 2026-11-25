"""Parse tool calls from native API responses and common text formats."""

from __future__ import annotations

import re
from typing import Any

from .repair import normalize_tool_payload, try_parse_json

HERMES_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
# Unclosed trailing tool_call (JSON may still be complete).
HERMES_OPEN_RE = re.compile(r"<tool_call>\s*(\{.*)", re.DOTALL)
QWEN_FN_RE = re.compile(
    r"<tool_call>\s*<function=(?P<name>[^>]+)>(?P<body>.*?)</function>\s*</tool_call>",
    re.DOTALL,
)
QWEN_PARAM_RE = re.compile(r"<parameter=(?P<key>[^>]+)>(?P<val>.*?)</parameter>", re.DOTALL)
MISTRAL_RE = re.compile(r"\[TOOL_CALLS\]\s*(\[.*\]|\{.*\})", re.DOTALL)


def parse_native_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    calls = message.get("tool_calls") or []
    out: list[dict[str, Any]] = []
    for call in calls:
        fn = call.get("function") if isinstance(call, dict) else None
        payload = fn if isinstance(fn, dict) else call
        normalized = normalize_tool_payload(payload)
        if normalized:
            out.append(normalized)
    return out


def parse_hermes(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    matches = HERMES_RE.findall(text or "")
    if not matches:
        open_match = HERMES_OPEN_RE.search(text or "")
        if open_match:
            matches = [open_match.group(1)]
    for raw in matches:
        parsed = try_parse_json(raw)
        normalized = normalize_tool_payload(parsed)
        if normalized:
            out.append(normalized)
    return out


def parse_qwen_xml(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in QWEN_FN_RE.finditer(text or ""):
        args = {m.group("key"): m.group("val") for m in QWEN_PARAM_RE.finditer(match.group("body"))}
        out.append({"name": match.group("name").strip(), "arguments": args})
    return out


def parse_mistral(text: str) -> list[dict[str, Any]]:
    match = MISTRAL_RE.search(text or "")
    if not match:
        return []
    parsed = try_parse_json(match.group(1))
    if parsed is None:
        return []
    items = parsed if isinstance(parsed, list) else [parsed]
    out: list[dict[str, Any]] = []
    for item in items:
        normalized = normalize_tool_payload(item)
        if normalized:
            out.append(normalized)
    return out


def extract_tool_calls(message: dict[str, Any], text_format: str = "auto") -> list[dict[str, Any]]:
    """Extract tool calls from a chat message.

    text_format: native | hermes_json | qwen_xml | mistral | auto
    """
    native = parse_native_tool_calls(message)
    if native:
        return native
    content = message.get("content") or ""
    if not isinstance(content, str):
        content = str(content)
    if text_format == "hermes_json":
        return parse_hermes(content)
    if text_format == "qwen_xml":
        return parse_qwen_xml(content)
    if text_format == "mistral":
        return parse_mistral(content)
    # auto: try each family, prefer the first non-empty result in this order
    for parser in (parse_hermes, parse_qwen_xml, parse_mistral):
        found = parser(content)
        if found:
            return found
    return []


def strip_think_blocks(text: str) -> str:
    """Remove leaked <think>…</think> blocks, including an unclosed leading tag."""
    if not text:
        return text
    stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    stripped = re.sub(r"<think>.*", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"</think>", "", stripped)
    return stripped.strip()
