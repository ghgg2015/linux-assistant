from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Protocol

from linux_assistant.schemas import ExecutionResult


class CommandExecutor(Protocol):
    def execute(self, command: str, cwd: Path, timeout: int) -> ExecutionResult:
        ...


class LocalCommandExecutor:
    def execute(self, command: str, cwd: Path, timeout: int) -> ExecutionResult:
        started = time.perf_counter()
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        duration = time.perf_counter() - started
        return ExecutionResult(
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            cwd=str(cwd),
            duration_seconds=duration,
        )


class RemoteCommandExecutor:
    def execute(self, command: str, cwd: Path, timeout: int) -> ExecutionResult:
        raise NotImplementedError(
            "Remote execution is not implemented yet. Add SSH or agent transport here."
        )
