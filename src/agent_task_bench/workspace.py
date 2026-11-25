"""File tools that stay inside a task worktree."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


class WorkspaceError(ValueError):
    pass


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, rel: str) -> Path:
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise WorkspaceError(f"path escapes worktree: {rel}")
        path = (self.root / rel).resolve()
        if path != self.root and self.root not in path.parents:
            raise WorkspaceError(f"path escapes worktree: {rel}")
        return path

    def list_dir(self, rel: str = ".") -> list[str]:
        path = self.resolve(rel) if rel not in (".", "") else self.root
        if not path.is_dir():
            raise WorkspaceError(f"not a directory: {rel}")
        items = []
        for child in sorted(path.iterdir()):
            suffix = "/" if child.is_dir() else ""
            items.append(str(child.relative_to(self.root)) + suffix)
        return items

    def read_file(self, rel: str) -> str:
        path = self.resolve(rel)
        if not path.is_file():
            raise WorkspaceError(f"not a file: {rel}")
        return path.read_text(encoding="utf-8")

    def write_file(self, rel: str, content: str, *, exist_ok: bool = True) -> str:
        path = self.resolve(rel)
        if path.exists() and not exist_ok:
            raise WorkspaceError(f"already exists: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"wrote {rel} ({len(content)} bytes)"

    def edit_file(self, rel: str, old: str, new: str) -> str:
        text = self.read_file(rel)
        if old in text:
            if text.count(old) != 1:
                raise WorkspaceError(f"old text matches {text.count(old)} times in {rel}")
            self.write_file(rel, text.replace(old, new, 1))
            return f"edited {rel} (exact match)"
        # Unique whitespace-normalized match, then re-apply file indentation.
        match = _unique_normalized_span(text, old)
        if match is None:
            raise WorkspaceError(f"old text not found in {rel}")
        start, end, indent = match
        replacement = _reindent(new, indent, old, text[start:end])
        self.write_file(rel, text[:start] + replacement + text[end:])
        return f"edited {rel} (whitespace-normalized unique match)"


def _normalize(block: str) -> str:
    lines = [line.strip() for line in block.splitlines()]
    return "\n".join(line for line in lines if line != "" or len(lines) == 1)


def _unique_normalized_span(text: str, old: str) -> tuple[int, int, str] | None:
    target = _normalize(old)
    if not target:
        return None
    text_lines = text.splitlines(keepends=True)
    old_lines = [line for line in old.splitlines() if line.strip() != ""] or old.splitlines()
    window = max(len(old_lines), 1)
    hits: list[tuple[int, int, str]] = []
    # Search by character offsets of line windows
    offsets = [0]
    for line in text_lines:
        offsets.append(offsets[-1] + len(line))
    for i in range(0, len(text_lines) - window + 1):
        chunk = "".join(text_lines[i : i + window])
        if _normalize(chunk) == target:
            # Indent of the first non-empty line in the window
            first = next((ln for ln in text_lines[i : i + window] if ln.strip()), text_lines[i])
            indent = first[: len(first) - len(first.lstrip())]
            hits.append((offsets[i], offsets[i + window], indent))
    if len(hits) != 1:
        return None
    return hits[0]


def _leading(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _reindent(new: str, file_indent: str, old: str, matched: str) -> str:
    """Apply the matched file block's indentation to the new text.

    When old, new, and the matched span have the same line count, each new
    line keeps the leading whitespace of the corresponding file line.
    Otherwise, shift lines using the indent delta of the first indented line.
    """
    new_lines = new.splitlines()
    old_lines = old.splitlines()
    matched_lines = matched.splitlines()
    trailing = "\n" if new.endswith("\n") or matched.endswith("\n") else ""
    if len(new_lines) == len(matched_lines) == len(old_lines) and matched_lines:
        out = [
            _leading(m) + n.lstrip() if n.strip() else n
            for n, m in zip(new_lines, matched_lines)
        ]
        return "\n".join(out) + trailing
    # Fallback: delta from the first indented line in old vs matched.
    delta = ""
    for o, m in zip(old_lines, matched_lines):
        if o.strip() and len(_leading(m)) != len(_leading(o)):
            # file indent minus old indent
            oi, mi = _leading(o), _leading(m)
            if mi.startswith(oi):
                delta = mi[len(oi) :]
            break
    # Add the delta only to lines that already have leading whitespace.
    out = [(delta + line) if line.startswith((" ", "\t")) else line for line in new_lines]
    return "\n".join(out) + trailing


def seed_worktree(src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def apply_tool(ws: Workspace, name: str, arguments: dict[str, Any]) -> str:
    name = name.strip()
    if name == "list_dir":
        return "\n".join(ws.list_dir(arguments.get("path") or ".")) or "(empty)"
    if name == "read_file":
        return ws.read_file(arguments["path"])
    if name == "write_file":
        return ws.write_file(arguments["path"], arguments.get("content") or arguments.get("contents") or "")
    if name == "edit_file":
        return ws.edit_file(
            arguments["path"],
            arguments.get("old") or arguments.get("old_text") or "",
            arguments.get("new") or arguments.get("new_text") or "",
        )
    raise WorkspaceError(f"unknown tool: {name}")
