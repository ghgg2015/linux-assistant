from __future__ import annotations

import shlex
import sys
from pathlib import Path

from linux_assistant.config import AppConfig
from linux_assistant.executors import LocalCommandExecutor
from linux_assistant.history import AuditLogger, SessionState
from linux_assistant.schemas import (
    ActionType,
    CommandPlan,
    ExecutionResult,
    RiskLevel,
    SafetyAssessment,
)
from linux_assistant.security import CommandSafetyChecker
from linux_assistant.service import LinuxAssistantService


HELP_TEXT = """
Commands:
  /help               Show this help text
  /status             Show current session status
  /confirm on|off     Toggle confirm-before-execute
  /danger on|off      Toggle dangerous command allowance
  /cd <path>          Change the assistant working directory
  /quit               Exit
""".strip()


def main() -> None:
    config = AppConfig.load()
    if not config.openai_api_key:
        print("Missing OPENAI_API_KEY. Add it to your environment or .env file.")
        sys.exit(1)

    logger = AuditLogger(Path("logs"))
    service = LinuxAssistantService(
        config=config,
        executor=LocalCommandExecutor(),
        audit_logger=logger,
    )
    safety_checker = CommandSafetyChecker()
    session = service.create_session(Path.cwd())

    print("Linux Assistant CLI")
    print("Type /help for commands.")

    while True:
        try:
            raw_input_text = input(f"[{session.working_directory}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw_input_text:
            continue

        if raw_input_text.startswith("/"):
            if _handle_cli_command(raw_input_text, service, session):
                break
            continue

        try:
            plan = service.plan(raw_input_text, session)
        except Exception as exc:  # noqa: BLE001
            print(f"Planning failed: {exc}")
            continue

        assessment = safety_checker.assess(plan, session.policy.allow_dangerous)
        _print_plan(plan, assessment)

        if plan.action_type == ActionType.RESPOND:
            continue

        if plan.action_type == ActionType.CHANGE_DIRECTORY:
            if not plan.target_directory:
                print("Planner did not provide a target directory.")
                continue
            if _should_confirm(plan, assessment, session.policy.confirm_before_execute):
                if not _confirm():
                    print("Directory change cancelled.")
                    continue
            try:
                new_directory = service.change_directory(plan.target_directory, session)
            except Exception as exc:  # noqa: BLE001
                print(f"Directory change failed: {exc}")
                continue
            print(f"Working directory changed to: {new_directory}")
            continue

        if not assessment.allowed:
            print("Execution blocked by policy.")
            continue

        if _should_confirm(plan, assessment, session.policy.confirm_before_execute):
            if not _confirm():
                print("Execution cancelled.")
                continue

        try:
            result = service.execute(plan, session)
        except Exception as exc:  # noqa: BLE001
            print(f"Execution failed: {exc}")
            continue

        _print_result(result)


def _handle_cli_command(
    command: str,
    service: LinuxAssistantService,
    session: SessionState,
) -> bool:
    parts = shlex.split(command)
    if not parts:
        return False

    action = parts[0]

    if action == "/help":
        print(HELP_TEXT)
        return False
    if action == "/status":
        print(f"cwd: {session.working_directory}")
        print(f"confirm_before_execute: {session.policy.confirm_before_execute}")
        print(f"allow_dangerous: {session.policy.allow_dangerous}")
        return False
    if action == "/confirm" and len(parts) == 2:
        try:
            session.policy.confirm_before_execute = _parse_toggle(parts[1])
        except ValueError as exc:
            print(exc)
            return False
        print(f"confirm_before_execute={session.policy.confirm_before_execute}")
        return False
    if action == "/danger" and len(parts) == 2:
        try:
            session.policy.allow_dangerous = _parse_toggle(parts[1])
        except ValueError as exc:
            print(exc)
            return False
        print(f"allow_dangerous={session.policy.allow_dangerous}")
        return False
    if action == "/cd" and len(parts) >= 2:
        target = " ".join(parts[1:])
        try:
            new_directory = service.change_directory(target, session)
        except Exception as exc:  # noqa: BLE001
            print(f"Directory change failed: {exc}")
            return False
        print(f"Working directory changed to: {new_directory}")
        return False
    if action == "/quit":
        return True

    print("Unknown command. Type /help for usage.")
    return False


def _parse_toggle(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"on", "true", "1"}:
        return True
    if normalized in {"off", "false", "0"}:
        return False
    raise ValueError(f"Unsupported toggle value: {value}")


def _should_confirm(
    plan: CommandPlan,
    assessment: SafetyAssessment,
    confirm_before_execute: bool,
) -> bool:
    return (
        confirm_before_execute
        or plan.requires_confirmation
        or assessment.risk_level != RiskLevel.LOW
    )


def _confirm() -> bool:
    answer = input("Proceed? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _print_plan(plan: CommandPlan, assessment: SafetyAssessment) -> None:
    print()
    print(f"Summary: {plan.summary}")
    print(f"Action: {plan.action_type}")
    print(f"Risk: {assessment.risk_level}")
    print(f"Explanation: {plan.explanation}")
    print(f"Expected: {plan.expected_result}")
    if plan.command:
        print(f"Command: {plan.command}")
    if plan.target_directory:
        print(f"Target Directory: {plan.target_directory}")
    if assessment.reasons:
        print("Risk Reasons:")
        for reason in assessment.reasons:
            print(f"- {reason}")
    print()


def _print_result(result: ExecutionResult) -> None:
    print(f"Exit Code: {result.exit_code}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    if result.stdout.strip():
        print("STDOUT:")
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print("STDERR:")
        print(result.stderr.rstrip())
