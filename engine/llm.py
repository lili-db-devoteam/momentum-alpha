"""Gemini-wrapper: timeout, één retry, en foutmeldingen zonder geheimen."""
from __future__ import annotations

import logging
from typing import Protocol

from engine.config import Settings

log = logging.getLogger("glassbox.llm")


class LLMClient(Protocol):
    def generate(self, system: str, user: str) -> str: ...


class LLMError(Exception):
    """Fout met enkel een korte categorie: timeout, quota, netwerk of onbekend."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def categorize(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if getattr(exc, "code", None) == 429 or "resourceexhausted" in name:
        return "quota"
    if "connect" in name or "network" in name:
        return "netwerk"
    return "onbekend"


def _retryable(exc: BaseException, category: str) -> bool:
    code = getattr(exc, "code", None)
    return category in ("timeout", "netwerk") or (isinstance(code, int) and code >= 500)


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_s: int, retries: int = 1, client: object | None = None) -> None:
        if not api_key:
            raise ValueError("api_key is verplicht")
        self._model = model
        self._retries = retries
        self._secret = api_key
        if client is None:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_s * 1000))
        self._client = client

    def __repr__(self) -> str:
        return f"GeminiClient(model={self._model!r})"

    def _redact(self, text: str) -> str:
        return text.replace(self._secret, "***")

    def generate(self, system: str, user: str) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system, temperature=0.6, max_output_tokens=400)
        category = "onbekend"
        for attempt in range(self._retries + 1):
            try:
                resp = self._client.models.generate_content(model=self._model, contents=user, config=config)
                return (resp.text or "").strip()
            except Exception as exc:
                category = categorize(exc)
                log.debug("llm_exception attempt=%d type=%s detail=%s", attempt, type(exc).__name__, self._redact(str(exc)))
                if not _retryable(exc, category):
                    break
        raise LLMError(category)


def client_from_settings(settings: Settings) -> GeminiClient | None:
    if not settings.llm_enabled:
        return None
    return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_s)
