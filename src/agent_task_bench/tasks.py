"""Load pack-v1 style task definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    instruction: str
    fixture: Path
    verify: list[str]
    max_steps: int = 20


def load_pack(pack_dir: Path) -> list[Task]:
    manifest = pack_dir / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    tasks: list[Task] = []
    for item in data["tasks"]:
        task_dir = pack_dir / item["id"]
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        tasks.append(
            Task(
                id=item["id"],
                title=item["title"],
                instruction=instruction,
                fixture=task_dir / "fixture",
                verify=list(item["verify"]),
                max_steps=int(item.get("max_steps", 20)),
            )
        )
    return tasks
