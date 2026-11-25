"""Run a task's verify commands in its worktree and score pass/fail."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VerifyResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


@dataclass
class TaskScore:
    task_id: str
    passed: bool
    steps_used: int
    verify: list[VerifyResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_verify(worktree: Path, commands: list[str], timeout: int = 30) -> list[VerifyResult]:
    results: list[VerifyResult] = []
    for command in commands:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        results.append(
            VerifyResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        )
    return results
