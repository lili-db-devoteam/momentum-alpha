import logging
from types import SimpleNamespace

import pytest

from engine.config import Settings
from engine.llm import GeminiClient, LLMError, categorize, client_from_settings

KEY = "sk-test-KEY-123"


class TimeoutException(Exception):
    pass


class ConnectError(Exception):
    pass


class APIError(Exception):
    def __init__(self, code, msg="x"):
        super().__init__(msg)
        self.code = code


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


def make(outcomes, retries=1):
    fake = SimpleNamespace(models=FakeModels(outcomes))
    return GeminiClient(KEY, "m", 15, retries=retries, client=fake), fake.models


def test_returns_stripped_text_and_passes_prompts():
    client, models = make(["  hoi  "])
    assert client.generate("sys", "user") == "hoi"
    call = models.calls[0]
    assert (call["model"], call["contents"]) == ("m", "user")
    assert call["config"].system_instruction == "sys"
    assert call["config"].max_output_tokens == 400
    assert call["config"].thinking_config.thinking_budget == 0


def test_none_text_becomes_empty_string():
    client, _ = make([None])
    assert client.generate("s", "u") == ""


def test_retries_once_on_timeout():
    client, models = make([TimeoutException(), "ok"])
    assert client.generate("s", "u") == "ok"
    assert len(models.calls) == 2


def test_gives_up_after_one_retry():
    client, models = make([TimeoutException(), TimeoutException()])
    with pytest.raises(LLMError) as err:
        client.generate("s", "u")
    assert err.value.category == "timeout"
    assert len(models.calls) == 2


def test_no_retry_on_quota():
    client, models = make([APIError(429)])
    with pytest.raises(LLMError) as err:
        client.generate("s", "u")
    assert err.value.category == "quota"
    assert len(models.calls) == 1


def test_retry_on_server_error():
    client, _ = make([APIError(503), "ok"])
    assert client.generate("s", "u") == "ok"


@pytest.mark.parametrize("exc,category", [
    (TimeoutException(), "timeout"), (TimeoutError(), "timeout"), (APIError(429), "quota"),
    (ConnectError(), "netwerk"), (ValueError(), "onbekend"), (APIError(400), "onbekend"),
])
def test_categorize(exc, category):
    assert categorize(exc) == category


def test_error_never_contains_key(caplog):
    caplog.set_level(logging.DEBUG, logger="glassbox")
    client, _ = make([ConnectError(f"failed with key={KEY}"), ConnectError(KEY)])
    with pytest.raises(LLMError) as err:
        client.generate("s", "u")
    assert err.value.category == "netwerk"
    assert KEY not in str(err.value)
    assert err.value.__cause__ is None and err.value.__context__ is None
    assert KEY not in caplog.text
    assert "***" in caplog.text


def test_repr_hides_key():
    client, _ = make([])
    assert KEY not in repr(client)


def test_requires_key():
    with pytest.raises(ValueError):
        GeminiClient("", "m", 15, client=SimpleNamespace())


def test_client_from_settings():
    assert client_from_settings(Settings()) is None
    assert isinstance(client_from_settings(Settings(gemini_api_key="k")), GeminiClient)
