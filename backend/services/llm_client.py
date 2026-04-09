from __future__ import annotations

import json
from typing import Any, Dict

from config.settings import LLMSettings


class LLMClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    def _build_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLM-assisted extraction") from exc

        kwargs: Dict[str, Any] = {"api_key": self.settings.api_key}
        if self.settings.base_url:
            kwargs["base_url"] = self.settings.base_url
        return OpenAI(**kwargs)

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        client = self._build_client()
        transport = self.settings.transport or "auto"

        if transport in ("auto", "chat_completions"):
            try:
                completion = client.chat.completions.create(
                    model=self.settings.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                content = completion.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception:
                if transport != "auto":
                    raise

        response = client.responses.create(
            model=self.settings.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if hasattr(response, "output_text"):
            return json.loads(response.output_text or "{}")

        text = ""
        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                text += getattr(content, "text", "")
        return json.loads(text or "{}")
