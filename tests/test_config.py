import pytest

from engine.config import ConfigError, Settings, merge_secrets


def test_defaults_when_env_empty():
    s = Settings.from_env({})
    assert s.gemini_api_key == ""
    assert not s.llm_enabled
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.gemini_timeout_s == 15
    assert (s.rate_session_max, s.rate_session_window_s, s.rate_global_per_hour) == (5, 600, 60)
    assert s.log_level == "INFO"


def test_overrides():
    s = Settings.from_env({
        "GEMINI_API_KEY": " abc ", "GEMINI_MODEL": "m", "GEMINI_TIMEOUT_S": "5",
        "RATE_SESSION_MAX": "2", "RATE_SESSION_WINDOW_S": "60", "RATE_GLOBAL_PER_HOUR": "10",
        "LOG_LEVEL": "debug",
    })
    assert s.gemini_api_key == "abc"
    assert s.llm_enabled
    assert (s.gemini_model, s.gemini_timeout_s) == ("m", 5)
    assert (s.rate_session_max, s.rate_session_window_s, s.rate_global_per_hour) == (2, 60, 10)
    assert s.log_level == "DEBUG"


def test_google_api_key_is_fallback():
    assert Settings.from_env({"GOOGLE_API_KEY": "g"}).gemini_api_key == "g"


def test_blank_values_use_defaults():
    assert Settings.from_env({"RATE_SESSION_MAX": "  ", "LOG_LEVEL": ""}).rate_session_max == 5


@pytest.mark.parametrize("name,value", [
    ("RATE_SESSION_MAX", "abc"),
    ("RATE_SESSION_MAX", "0"),
    ("RATE_GLOBAL_PER_HOUR", "-1"),
    ("GEMINI_TIMEOUT_S", "1.5"),
    ("RATE_SESSION_WINDOW_S", "0"),
    ("LOG_LEVEL", "LOUD"),
])
def test_invalid_values_raise_with_variable_name(name, value):
    with pytest.raises(ConfigError, match=name):
        Settings.from_env({name: value})


def test_key_never_in_repr_or_str():
    s = Settings.from_env({"GEMINI_API_KEY": "sk-secret-123"})
    assert "sk-secret-123" not in repr(s)
    assert "sk-secret-123" not in str(s)


def test_merge_secrets_fills_blanks_but_env_wins():
    env = {"GEMINI_MODEL": "from-env", "GEMINI_API_KEY": ""}
    merge_secrets({"GEMINI_API_KEY": "k", "GEMINI_MODEL": "from-secrets", "OTHER": "x", "RATE_SESSION_MAX": 3}, env)
    assert env == {"GEMINI_MODEL": "from-env", "GEMINI_API_KEY": "k", "RATE_SESSION_MAX": "3"}
