from __future__ import annotations

import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from linux_assistant.config import AppConfig
from linux_assistant.executors import CommandExecutor
from linux_assistant.history import AuditLogger, SessionState
from linux_assistant.prompts import build_system_prompt
from linux_assistant.schemas import ActionType, AuditEvent, CommandPlan, ExecutionResult


class LinuxAssistantService:
    def __init__(
        self,
        config: AppConfig,
        executor: CommandExecutor,
        audit_logger: AuditLogger,
    ) -> None:
        self.config = config
        self.executor = executor
        self.audit_logger = audit_logger
        self._planner = self._build_planner()

    def create_session(self, working_directory: Path) -> SessionState:
        session = SessionState(
            session_id=str(uuid.uuid4()),
            working_directory=working_directory.resolve(),
        )
        self.audit_logger.log(
            AuditEvent(
                event_type="session",
                payload={
                    "session_id": session.session_id,
                    "working_directory": str(session.working_directory),
                },
            )
        )
        return session

    def plan(self, user_input: str, session: SessionState) -> CommandPlan:
        system_prompt = build_system_prompt(
            current_directory=str(session.working_directory),
            confirm_before_execute=session.policy.confirm_before_execute,
            allow_dangerous=session.policy.allow_dangerous,
        )

        plan = self._planner.invoke(
            {
                "system_prompt": system_prompt,
                "history": session.messages,
                "user_input": user_input,
            }
        )

        session.messages.append(HumanMessage(content=user_input))
        session.messages.append(
            AIMessage(
                content=(
                    f"action_type={plan.action_type}; "
                    f"summary={plan.summary}; "
                    f"command={plan.command or ''}; "
                    f"target_directory={plan.target_directory or ''}"
                )
            )
        )

        self.audit_logger.log(
            AuditEvent(
                event_type="plan",
                payload={
                    "session_id": session.session_id,
                    "user_input": user_input,
                    "working_directory": str(session.working_directory),
                    "plan": plan.model_dump(),
                },
            )
        )

        return plan

    def change_directory(self, target_directory: str, session: SessionState) -> Path:
        current = session.working_directory
        candidate = Path(target_directory).expanduser()
        if not candidate.is_absolute():
            candidate = current / candidate
        candidate = candidate.resolve()

        if not candidate.exists():
            raise FileNotFoundError(f"Directory does not exist: {candidate}")
        if not candidate.is_dir():
            raise NotADirectoryError(f"Not a directory: {candidate}")

        session.working_directory = candidate
        return candidate

    def execute(self, plan: CommandPlan, session: SessionState) -> ExecutionResult:
        if plan.action_type != ActionType.RUN_SHELL or not plan.command:
            raise ValueError("Only run_shell plans can be executed.")

        result = self.executor.execute(
            command=plan.command,
            cwd=session.working_directory,
            timeout=self.config.command_timeout,
        )

        self.audit_logger.log(
            AuditEvent(
                event_type="execution",
                payload={
                    "session_id": session.session_id,
                    "command": plan.command,
                    "working_directory": str(session.working_directory),
                    "result": result.model_dump(),
                },
            )
        )
        return result

    def _build_planner(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                MessagesPlaceholder("history"),
                ("human", "{user_input}"),
            ]
        )

        model = ChatOpenAI(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_base_url,
            model=self.config.openai_model,
            timeout=self.config.command_timeout,
        ).with_structured_output(CommandPlan)

        return prompt | model
