# Linux Assistant

`linux_assistant` is a CLI project built with LangChain. It accepts natural language, asks an OpenAI-compatible model to convert that request into a Linux operation plan, and then either confirms or executes the action.

## Scope

- Local Linux execution first
- Remote Linux executor reserved as an extension point
- Interactive multi-turn CLI
- Safety mode with confirm-before-execute enabled by default
- Audit log for prompts, command plans, and execution results

## Architecture

- `cli.py`: interactive shell and runtime toggles
- `service.py`: LangChain orchestration and session lifecycle
- `executors.py`: local executor plus remote executor placeholder
- `security.py`: command risk assessment and blocking logic
- `history.py`: in-memory conversation state and JSONL audit log
- `schemas.py`: structured plan and result models

## Setup

Recommended Python version: `3.11` or `3.12`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env
```

Set at least:

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-5.4"
```

If you use an OpenAI-compatible gateway, also set:

```bash
export OPENAI_BASE_URL="https://your-endpoint.example/v1"
```

## Run

```bash
linux-assistant
```

## CLI Controls

- `/help`: show commands
- `/status`: show current working directory and policy
- `/confirm on|off`: toggle confirm-before-execute
- `/danger on|off`: toggle dangerous command allowance
- `/cd <path>`: change assistant working directory directly
- `/quit`: exit

## Behavior

The assistant can return three action types:

- `run_shell`: run a shell command
- `change_directory`: update the session working directory
- `respond`: answer without executing a command

By default:

- dangerous commands are blocked
- command execution requires confirmation

## Notes

- The command runner uses `bash -lc "<command>"` to preserve standard shell behavior.
- The current version is intentionally conservative. Destructive actions, privilege escalation, or system-level reconfiguration should remain guarded even when the toggle is relaxed.
- Remote Linux support should be added by implementing `RemoteCommandExecutor`.
