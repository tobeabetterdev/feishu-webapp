import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMSettings:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    transport: str = "auto"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_llm_settings() -> LLMSettings:
    _load_dotenv()
    return LLMSettings(
        base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        model=os.getenv("OPENAI_MODEL", "").strip(),
        transport=os.getenv("OPENAI_TRANSPORT", "auto").strip() or "auto",
    )


def build_task_llm_settings(
    defaults: LLMSettings,
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    transport: Optional[str] = None,
) -> LLMSettings:
    return LLMSettings(
        base_url=(base_url if base_url not in (None, "") else defaults.base_url).strip(),
        api_key=(api_key if api_key not in (None, "") else defaults.api_key).strip(),
        model=(model if model not in (None, "") else defaults.model).strip(),
        transport=(transport if transport not in (None, "") else defaults.transport).strip() or "auto",
    )
