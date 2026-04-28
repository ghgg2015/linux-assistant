from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    RUN_SHELL = "run_shell"
    CHANGE_DIRECTORY = "change_directory"
    RESPOND = "respond"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CommandPlan(BaseModel):
    summary: str = Field(description="Short summary of the user's intent.")
    action_type: ActionType = Field(description="The action that should be taken.")
    command: str | None = Field(
        default=None,
        description="Shell command to run for action_type=run_shell.",
    )
    target_directory: str | None = Field(
        default=None,
        description="Directory to change into for action_type=change_directory.",
    )
    explanation: str = Field(description="Human-readable explanation of the plan.")
    expected_result: str = Field(description="What the user should expect after execution.")
    risk_level: RiskLevel = Field(description="Model-assessed risk level.")
    risk_reasons: list[str] = Field(
        default_factory=list,
        description="Why the action may be risky.",
    )
    requires_confirmation: bool = Field(
        description="Whether the plan should require user confirmation.",
    )


class SafetyAssessment(BaseModel):
    allowed: bool
    dangerous: bool
    risk_level: RiskLevel
    reasons: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    cwd: str
    duration_seconds: float


class AuditEvent(BaseModel):
    event_type: Literal["plan", "execution", "session"]
    payload: dict
