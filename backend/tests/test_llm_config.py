from pathlib import Path

from config import settings as settings_module
from config.settings import LLMSettings, build_task_llm_settings, load_llm_settings


def test_build_task_llm_settings_prefers_request_overrides():
    defaults = LLMSettings(
        base_url="https://default.example.com/v1",
        api_key="default-key",
        model="default-model",
        transport="auto",
    )

    result = build_task_llm_settings(
        defaults,
        base_url="https://override.example.com/v1",
        api_key="override-key",
        model="override-model",
        transport="responses",
    )

    assert result.base_url == "https://override.example.com/v1"
    assert result.api_key == "override-key"
    assert result.model == "override-model"
    assert result.transport == "responses"


def test_build_task_llm_settings_keeps_defaults_when_request_is_empty():
    defaults = LLMSettings(
        base_url="https://default.example.com/v1",
        api_key="default-key",
        model="default-model",
        transport="auto",
    )

    result = build_task_llm_settings(defaults)

    assert result == defaults


def test_load_llm_settings_reads_backend_dotenv(monkeypatch):
    env_path = Path(settings_module.__file__).resolve().parent.parent / ".env"
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else None

    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_TRANSPORT", raising=False)

    try:
        env_path.write_text(
            "\n".join(
                [
                    "OPENAI_BASE_URL=https://dotenv.example.com/v1",
                    "OPENAI_API_KEY=dotenv-key",
                    "OPENAI_MODEL=dotenv-model",
                    "OPENAI_TRANSPORT=chat_completions",
                ]
            ),
            encoding="utf-8",
        )
        result = load_llm_settings()
        assert result.base_url == "https://dotenv.example.com/v1"
        assert result.api_key == "dotenv-key"
        assert result.model == "dotenv-model"
        assert result.transport == "chat_completions"
    finally:
        if original is None:
            env_path.unlink(missing_ok=True)
        else:
            env_path.write_text(original, encoding="utf-8")
