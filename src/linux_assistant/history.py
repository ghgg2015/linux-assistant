from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from langchain_core.messages import BaseMessage

from linux_assistant.schemas import AuditEvent


@dataclass
class SessionPolicy:
    confirm_before_execute: bool = True
    allow_dangerous: bool = False


@dataclass
class SessionState:
    session_id: str
    working_directory: Path
    messages: list[BaseMessage] = field(default_factory=list)
    policy: SessionPolicy = field(default_factory=SessionPolicy)


class AuditLogger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = self.root / f"session-{timestamp}.jsonl"

    def log(self, event: AuditEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
