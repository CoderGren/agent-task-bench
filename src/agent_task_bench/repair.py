"""Tolerant repair for common malformed tool-call JSON."""

from __future__ import annotations

import json
import re
from typing import Any


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _escape_raw_newlines_in_strings(text: str) -> str:
    """Escape raw newlines that appear inside JSON string literals."""
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.extend(["\\", "n"])
            elif ch == "\r":
                continue
            else:
                out.append(ch)
        else:
            out.append(ch)
            if ch == '"':
                in_string = True
    return "".join(out)


def _balance_braces(text: str) -> str:
    """Drop a leading stray '{' or append missing closers, then retry."""
    candidates = [text]
    if text.startswith("{") and text.count("{") == text.count("}") + 1:
        # Pattern seen in the wild: {"name": "read_file", {"arguments": {...}}
        candidates.append(text[1:])
        # Also try inserting a missing closer before the inner object.
        idx = text.find(", {")
        if idx != -1:
            candidates.append(text[:idx] + "}" + text[idx:])
    opens = text.count("{") - text.count("}")
    if opens > 0:
        candidates.append(text + ("}" * opens))
    if opens < 0 and text.endswith("}"):
        candidates.append(text[:opens])  # drop extra trailing closers
    return candidates


def _repair_stray_inner_object(text: str) -> str:
    """Turn {"name": "read_file", {"arguments": {...}}} into valid JSON."""
    if ', {"' not in text:
        return text
    repaired = text.replace(', {"', ', "')
    # The extra opening brace we removed usually leaves one extra closer.
    while repaired.count("}") > repaired.count("{") and repaired.endswith("}"):
        repaired = repaired[:-1]
    return repaired


def try_parse_json(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    variants = [text, _strip_trailing_commas(text), _escape_raw_newlines_in_strings(text), _repair_stray_inner_object(text)]
    variants.append(_strip_trailing_commas(_escape_raw_newlines_in_strings(text)))
    variants.append(_repair_stray_inner_object(_strip_trailing_commas(text)))
    expanded: list[str] = []
    for variant in variants:
        expanded.extend(_balance_braces(variant))
    seen: set[str] = set()
    for variant in expanded:
        if variant in seen:
            continue
        seen.add(variant)
        try:
            return json.loads(variant)
        except json.JSONDecodeError:
            continue
    return None


def normalize_tool_payload(payload: Any) -> dict[str, Any] | None:
    """Return {name, arguments} or None."""
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return None
    name = payload.get("name") or payload.get("function")
    if isinstance(name, dict):
        # OpenAI function wrapper
        arguments = name.get("arguments", {})
        name = name.get("name")
        return {"name": str(name), "arguments": _as_args(arguments)} if name else None
    arguments = payload.get("arguments") or payload.get("parameters") or payload.get("args") or {}
    if not name:
        return None
    return {"name": str(name), "arguments": _as_args(arguments)}


def _as_args(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        parsed = try_parse_json(arguments)
        return parsed if isinstance(parsed, dict) else {}
    return arguments if isinstance(arguments, dict) else {}
