"""Instellingen uit omgevingsvariabelen.

Lokaal mag .streamlit/secrets.toml ze aanvullen (zie merge_secrets). In Docker en
op Cloud Run komen ze enkel uit de omgeving. De API-key verschijnt nooit in repr,
logs of foutmeldingen.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

KNOWN_KEYS = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_TIMEOUT_S",
    "RATE_SESSION_MAX", "RATE_SESSION_WINDOW_S", "RATE_GLOBAL_PER_HOUR", "LOG_LEVEL",
)
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(ValueError):
    """Ongeldige configuratie; de boodschap noemt altijd de variabele."""


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} moet een geheel getal zijn, kreeg {raw!r}") from None
    if value <= 0:
        raise ConfigError(f"{name} moet groter dan 0 zijn, kreeg {value}")
    return value


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = field(default="", repr=False)
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_s: int = 15
    rate_session_max: int = 5
    rate_session_window_s: int = 600
    rate_global_per_hour: int = 60
    log_level: str = "INFO"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        level = (env.get("LOG_LEVEL") or "").strip().upper() or "INFO"
        if level not in LOG_LEVELS:
            raise ConfigError(f"LOG_LEVEL moet een van {', '.join(LOG_LEVELS)} zijn, kreeg {level!r}")
        return cls(
            gemini_api_key=(env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or "").strip(),
            gemini_model=(env.get("GEMINI_MODEL") or "").strip() or "gemini-2.5-flash",
            gemini_timeout_s=_positive_int(env, "GEMINI_TIMEOUT_S", 15),
            rate_session_max=_positive_int(env, "RATE_SESSION_MAX", 5),
            rate_session_window_s=_positive_int(env, "RATE_SESSION_WINDOW_S", 600),
            rate_global_per_hour=_positive_int(env, "RATE_GLOBAL_PER_HOUR", 60),
            log_level=level,
        )


def merge_secrets(secrets: Mapping[str, object], env: MutableMapping[str, str]) -> None:
    """Vult lege omgevingsvariabelen aan uit secrets. De omgeving wint altijd."""
    for key in KNOWN_KEYS:
        if key in secrets and not env.get(key):
            env[key] = str(secrets[key])


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("glassbox").setLevel(level)
