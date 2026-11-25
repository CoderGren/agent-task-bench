"""Agent loop: send tools to an OpenAI-compatible server, apply calls, score."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import parsers
from .scoring import TaskScore, run_verify
from .tasks import Task
from .workspace import Workspace, WorkspaceError, apply_tool, seed_worktree

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files in a directory relative to the worktree.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file relative to the worktree.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a unique span of text in a file. Exact match preferred; unique whitespace-normalized match is accepted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file relative to the worktree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a careful coding agent working in a local repository.
You must solve the task by calling tools. Stay inside the files the task names.
When you are done, stop calling tools and reply with a short summary of what you changed.
Do not invent tool results. Do not put secrets in your messages.
"""


ChatFn = Callable[[list[dict[str, Any]], str], dict[str, Any]]


@dataclass
class RunConfig:
    base_url: str = "http://127.0.0.1:8000/v1"
    model: str = "local"
    api_key: str = ""
    text_format: str = "auto"
    enable_thinking: bool | None = False
    temperature: float = 0.0
    timeout: int = 120


@dataclass
class RunLog:
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[str] = field(default_factory=list)


def chat_completions(config: RunConfig, messages: list[dict[str, Any]], text_format: str) -> dict[str, Any]:
    url = config.base_url.rstrip("/") + "/chat/completions"
    body: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "tools": TOOLS,
        "temperature": config.temperature,
    }
    if config.enable_thinking is not None:
        body["chat_template_kwargs"] = {"enable_thinking": config.enable_thinking}
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = "Bearer " + config.api_key
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"chat completions failed: {exc.code} {detail}") from exc
    return payload["choices"][0]["message"]


def run_task(
    task: Task,
    work_root: Path,
    config: RunConfig | None = None,
    chat: ChatFn | None = None,
) -> TaskScore:
    config = config or RunConfig()
    worktree = seed_worktree(task.fixture, work_root / task.id)
    for extra in task.fixture.parent.iterdir():
        if extra.is_file() and extra.name.startswith("verify"):
            (worktree / extra.name).write_text(extra.read_text(encoding="utf-8"), encoding="utf-8")
    ws = Workspace(worktree)
    log = RunLog(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task.instruction},
        ]
    )
    errors: list[str] = []
    steps = 0
    chat_fn = chat or (lambda msgs, fmt: chat_completions(config, msgs, fmt))

    while steps < task.max_steps:
        steps += 1
        message = chat_fn(log.messages, config.text_format)
        content = message.get("content") or ""
        if isinstance(content, str):
            message = dict(message)
            message["content"] = parsers.strip_think_blocks(content)
        log.messages.append(message)
        calls = parsers.extract_tool_calls(message, config.text_format)
        if not calls:
            break
        for call in calls:
            try:
                result = apply_tool(ws, call["name"], call.get("arguments") or {})
            except (WorkspaceError, KeyError, TypeError) as exc:
                result = f"error: {exc}"
                errors.append(result)
            log.tool_results.append(result)
            log.messages.append({"role": "tool", "name": call["name"], "content": result})

    verify = run_verify(worktree, task.verify)
    passed = all(item.passed for item in verify) and not any(
        item.startswith("error:") and "old text not found" in item for item in errors
    )
    # Fail only if verification failed; tool errors mid-run are fine if the end state passes.
    passed = all(item.passed for item in verify)
    return TaskScore(task_id=task.id, passed=passed, steps_used=steps, verify=verify, errors=errors)
