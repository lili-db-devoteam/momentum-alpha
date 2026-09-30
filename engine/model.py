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

THRESHOLD = 0.6
GEEN_SITUATIE = "Geen bijzondere situatie"


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
        "Pensioen in zicht",
        (
            Signal("leeftijd_55", 0.35, "Je bent tussen 55 en 66", lambda d: d.leeftijd.between(55, 66)),
            Signal("nog_werkend", 0.25, "Je ontvangt nog een loon", lambda d: (d.leeftijd < 67) & (d.inkomen_pm > 2200)),
            Signal("geen_pensioensparen", 0.25, "Je doet nog niet aan pensioensparen", lambda d: ~d.pensioensparen_actief.astype(bool)),
            Signal("laag_spaarritme", 0.15, "Je spaart minder dan 5% van je inkomen", lambda d: d.spaart_pm < 0.05 * d.inkomen_pm),
        ),
        "{naam}je pensioen komt in zicht.",
        "Bekijk in twee minuten wat je nog kan doen, en praat met je toekomstige zelf.",
        "App + Kate met stem", "Rustig, concreet, geen jargon",
    ),
    Situation(
        "Terug van reis",
        (
            Signal("buitenland", 0.5, "Veel kaartbetalingen in het buitenland deze maand", lambda d: d.buitenland_tx_30d >= 5),
            Signal("gestopt", 0.3, "De buitenlandse betalingen zijn gestopt: je bent terug", lambda d: d.buitenland_gestopt.astype(bool)),
            Signal("restaurant", 0.2, "Restaurants kostten meer dan het dubbele van normaal", lambda d: d.restaurant_ratio >= 2),
        ),
        "{naam}terug van reis?",
        "Verdeel je reisbetalingen met je vrienden in één tik.",
        "App-melding", "Kort, één tik",
    ),
    Situation(
        "Verhuizer",
        (
            Signal("waarborg", 0.5, "Je betaalde een huurwaarborg", lambda d: d.huurwaarborg.astype(bool)),
            Signal("verhuisfirma", 0.3, "Je betaalde een verhuisfirma", lambda d: d.verhuisfirma.astype(bool)),
            Signal("energie", 0.2, "Je hebt een nieuw energiecontract", lambda d: d.nieuw_energiecontract.astype(bool)),
        ),
        "{naam}je verhuist?",
        "Eén checklist: adres overal aanpassen, woningverzekering, lening.",
        "App + e-mail", "Praktisch, checklist",
    ),
    Situation(
        "Eerste loon",
        (
            Signal("eerste_loon", 0.6, "Je ontving je eerste loon van een werkgever", lambda d: d.eerste_loon.astype(bool)),
            Signal("jong", 0.2, "Je bent 27 of jonger", lambda d: d.leeftijd <= 27),
            Signal("geen_buffer", 0.2, "Je hebt nog geen buffer van één maand", lambda d: d.spaargeld < d.uitgaven_pm),
        ),
        "{naam}proficiat met je eerste loon!",
        "Zet in drie stappen een buffer en een budget op.",
        "App-melding", "Kort, positief",
    ),
    Situation(
        "Jonge ouder",
        (
            Signal("babywinkel", 0.5, "Nieuwe uitgaven bij babywinkels", lambda d: d.babywinkel_pm > 100),
            Signal("groeipakket", 0.4, "Je ontvangt een groeipakket", lambda d: d.groeipakket.astype(bool)),
            Signal("leeftijd", 0.1, "Je bent tussen 24 en 42", lambda d: d.leeftijd.between(24, 42)),
        ),
        "{naam}welkom aan je kleine!",
        "Wat verandert er nu voor je budget, verzekering en sparen?",
        "App + e-mail", "Warm, overzichtelijk",
    ),
    Situation(
        "Fraudegevoelig moment",
        (
            Signal("senior", 0.3, "Je bent 65 of ouder", lambda d: d.leeftijd >= 65),
            Signal(
                "nieuwe_begunstigde", 0.5, "Groot bedrag naar een nieuwe begunstigde", lambda d: d.nieuwe_begunstigde_groot.astype(bool)
            ),
            Signal("nacht", 0.2, "Op een ongewoon uur", lambda d: d.nachtelijke_tx.astype(bool)),
        ),
        "{naam}even checken.",
        "Heeft iemand je gevraagd dit te doen? Een bank vraagt dat nooit.",
        "Kate met stem, vóór de betaling", "Rustig, beschermend",
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


def reasons_text(row: pd.Series, situatie: str) -> str:
    if situatie not in SITUATION_BY_NAME:
        return ""
    ex = explain(row, situatie)
    return " · ".join(f"{r['uitleg']} (+{r['gewicht']:.2f})" for r in ex["redenen"] if r["actief"])
