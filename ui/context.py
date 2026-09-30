"""Wat elke tab krijgt. Tabs lezen hieruit en laden zelf niets."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.config import Settings
from engine.llm import LLMClient
from engine.ratelimit import SlidingWindowLimiter


@dataclass(frozen=True)
class DemoContext:
    settings: Settings
    data: pd.DataFrame                    # klanten + kolommen situatie, score
    klant: pd.Series                      # geselecteerde klant
    naam: str                             # weergavenaam, "Klant" als onbekend
    score_secs: float                     # doorlooptijd van score_all
    llm: LLMClient | None                 # None = geen key, sjabloon
    global_limiter: SlidingWindowLimiter  # gedeeld door alle sessies in dit proces
