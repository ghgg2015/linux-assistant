from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    openai_api_key: str
    openai_model: str
    openai_base_url: str | None
    command_timeout: int

    @classmethod
    def load(cls) -> "AppConfig":
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        timeout = int(os.getenv("LINUX_ASSISTANT_TIMEOUT", "60"))

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            openai_base_url=base_url,
            command_timeout=timeout,
        )
