"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .runner import RunConfig, run_task
from .tasks import load_pack


def _pack_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[2] / "tasks" / "pack-v1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agent-task-bench pack against a local model.")
    parser.add_argument("--pack", help="Path to a pack directory containing manifest.json")
    parser.add_argument("--work", default="worktrees", help="Directory for per-task worktrees")
    parser.add_argument("--base-url", default=os.environ.get("ATB_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--model", default=os.environ.get("ATB_MODEL", "local"))
    parser.add_argument("--api-key", default=os.environ.get("ATB_API_KEY", ""))
    parser.add_argument("--format", dest="text_format", default="auto",
                        choices=["auto", "native", "hermes_json", "qwen_xml", "mistral"])
    parser.add_argument("--task", help="Run a single task id from the pack")
    args = parser.parse_args(argv)

    pack = load_pack(_pack_dir(args.pack))
    if args.task:
        pack = [task for task in pack if task.id == args.task]
        if not pack:
            print(f"unknown task: {args.task}", file=sys.stderr)
            return 2
    config = RunConfig(
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        text_format=args.text_format,
    )
    work_root = Path(args.work)
    results = [run_task(task, work_root, config=config) for task in pack]
    passed = sum(1 for item in results if item.passed)
    payload = {
        "passed": passed,
        "total": len(results),
        "tasks": [
            {
                "id": item.task_id,
                "passed": item.passed,
                "steps_used": item.steps_used,
                "verify": [
                    {"command": v.command, "exit_code": v.exit_code, "passed": v.passed}
                    for v in item.verify
                ],
            }
            for item in results
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
