"""Glass-box model: gewogen regels per levenssituatie.

Geen black box. Elke situatie is een lijst signalen met een gewicht en een zin
in gewone taal. De score is de som van de gewichten van de signalen die aan
staan. Daardoor kan elke beslissing exact uitgelegd worden, en kan de klant een
signaal uitzetten en direct zien wat er verandert.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from engine.future_self import PENSIOENLEEFTIJD

THRESHOLD = 0.65
GEEN_SITUATIE = "No specific situation"


@dataclass(frozen=True)
class Signal:
    key: str
    weight: float
    uitleg: str
    test: Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class Situation:
    naam: str
    signalen: tuple[Signal, ...]
    kaart_titel: str
    kaart_tekst: str
    kanaal: str
    toon: str


SITUATIONS: tuple[Situation, ...] = (
    Situation(
        "Retirement in sight",
        (
            Signal("age_55_66", 0.35, "Aged between 55 and 66", lambda d: d.leeftijd.between(55, 66)),
            Signal("still_working", 0.25, "Still receiving a salary", lambda d: (d.leeftijd < 67) & (d.inkomen_pm > 2200)),
            Signal("no_pension_savings", 0.25, "No pension savings yet", lambda d: ~d.pensioensparen_actief.astype(bool)),
            Signal("low_savings_rate", 0.15, "Saves less than 5% of income", lambda d: d.spaart_pm < 0.05 * d.inkomen_pm),
        ),
        "{naam}your retirement is in sight.",
        "See in two minutes what you can still do, and talk to yourself at 72.",
        "KBC Mobile + Kate with voice", "Calm, concrete, no jargon",
    ),
    Situation(
        "Back from a trip",
        (
            Signal("buitenland", 0.5, "Many card payments abroad", lambda d: d.buitenland_tx_30d >= 5),
            Signal("gestopt", 0.3, "Payments abroad have stopped", lambda d: d.buitenland_gestopt.astype(bool)),
            Signal("restaurant", 0.2, "Restaurants more than twice the usual", lambda d: d.restaurant_ratio >= 2),
        ),
        "{naam}back from your trip?",
        "Split your trip expenses with friends in one tap.",
        "App notification", "Short, one tap",
    ),
    Situation(
        "Moving house",
        (
            Signal("waarborg", 0.5, "Paid a rental deposit", lambda d: d.huurwaarborg.astype(bool)),
            Signal("verhuisfirma", 0.3, "Paid a moving company", lambda d: d.verhuisfirma.astype(bool)),
            Signal("energie", 0.2, "New energy contract", lambda d: d.nieuw_energiecontract.astype(bool)),
        ),
        "{naam}moving house?",
        "One checklist: update your address everywhere, home insurance, loan.",
        "App + e-mail", "Practical, checklist",
    ),
    Situation(
        "First salary",
        (
            Signal("eerste_loon", 0.6, "First salary from an employer", lambda d: d.eerste_loon.astype(bool)),
            Signal("jong", 0.2, "27 or younger", lambda d: d.leeftijd <= 27),
            Signal("geen_buffer", 0.2, "No one-month buffer yet", lambda d: d.spaargeld < d.uitgaven_pm),
        ),
        "{naam}congratulations on your first salary!",
        "Set up a buffer and a budget in three steps.",
        "App notification", "Short, positive",
    ),
    Situation(
        "Young parent",
        (
            Signal("babywinkel", 0.5, "Spending at baby stores", lambda d: d.babywinkel_pm > 100),
            Signal("groeipakket", 0.4, "Receives child benefit", lambda d: d.groeipakket.astype(bool)),
            Signal("leeftijd", 0.1, "Between 24 and 42", lambda d: d.leeftijd.between(24, 42)),
        ),
        "{naam}welcome to your little one!",
        "What changes now for your budget, insurance and savings?",
        "App + e-mail", "Warm, clear",
    ),
    Situation(
        "Fraud-sensitive moment",
        (
            Signal("senior", 0.3, "65 or older", lambda d: d.leeftijd >= 65),
            Signal(
                "nieuwe_begunstigde", 0.5, "Large amount to a new payee", lambda d: d.nieuwe_begunstigde_groot.astype(bool)
            ),
            Signal("nacht", 0.2, "At an unusual hour", lambda d: d.nachtelijke_tx.astype(bool)),
        ),
        "{naam}quick check.",
        "Did someone ask you to do this? A bank never asks that.",
        "Kate with voice, before the payment", "Calm, protective",
    ),
)

SITUATION_BY_NAME = {s.naam: s for s in SITUATIONS}


def score_all(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Scoort alle klanten tegelijk (gevectoriseerd). Geeft resultaat + seconden."""
    t0 = time.perf_counter()
    scores = pd.DataFrame(index=df.index)
    for sit in SITUATIONS:
        total = 0.0
        for sig in sit.signalen:
            total = total + sig.test(df).astype(float) * sig.weight
        scores[sit.naam] = total
    best = scores.idxmax(axis=1)
    best_score = scores.max(axis=1)
    out = pd.DataFrame({
        "klant_id": df.klant_id,
        "situatie": best.where(best_score >= THRESHOLD, GEEN_SITUATIE),
        "score": best_score.round(2),
    })
    return out, time.perf_counter() - t0


def explain(row: pd.Series, situatie: str, uitgezet: frozenset[str] = frozenset()) -> dict:
    """Uitleg voor één klant: welke signalen aan staan, met gewicht."""
    sit = SITUATION_BY_NAME[situatie]
    frame = row.to_frame().T.infer_objects()
    redenen = []
    score = 0.0
    for sig in sit.signalen:
        actief = bool(sig.test(frame).iloc[0])
        telt = actief and sig.key not in uitgezet
        if telt:
            score += sig.weight
        redenen.append({"key": sig.key, "uitleg": sig.uitleg, "gewicht": sig.weight,
                        "actief": actief, "uitgezet": sig.key in uitgezet})
    return {"situatie": situatie, "score": round(score, 2), "toon_kaart": score >= THRESHOLD,
            "redenen": redenen}


LOOK_AHEAD_YEARS = 10  # hoe ver vooruit Kate kijkt


def look_ahead(row: pd.Series) -> list[dict]:
    """Tips die nu al tellen voor later. Eén regel: hospitalisatieverzekering via de werkgever stopt bij pensioen.

    Geen premiecijfers: we hebben geen geverifieerde bron, dus enkel "rise sharply".
    """
    years = PENSIOENLEEFTIJD - int(row["leeftijd"])
    if not (bool(row.get("hospital_cover_via_employer", False)) and 0 <= years <= LOOK_AHEAD_YEARS):
        return []
    naam = row.get("naam") or ""
    title = f"{naam}, one more thing for later: your hospital cover." if naam else "One more thing for later: your hospital cover."
    return [{
        "title": title,
        "text": "Your hospital insurance comes with your job and stops when you retire. "
                "Premiums can then rise sharply. Preparing early costs less.",
        "source": "KBC Verzekeringen",
        "reasons": ["hospital_cover_via_employer = true", f"years_to_retirement = {years} (≤ {LOOK_AHEAD_YEARS})"],
    }]


def reasons_text(row: pd.Series, situatie: str) -> str:
    if situatie not in SITUATION_BY_NAME:
        return ""
    ex = explain(row, situatie)
    return " · ".join(f"{r['uitleg']} (+{r['gewicht']:.2f})" for r in ex["redenen"] if r["actief"])
