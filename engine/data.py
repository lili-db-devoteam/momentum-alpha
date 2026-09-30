"""Synthetische klantdata. Geen echte KBC-data.

Elke klant is een rij met leesbare signalen (maandaggregaten), zoals een bank
ze uit transacties zou afleiden. Een klein deel krijgt bewust een levenssituatie
ingespoten, zodat het model iets te herkennen heeft.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MARC_ID = "C-000058"


def generate_customers(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = rng.integers(18, 90, n)
    income = np.clip(rng.normal(3000, 900, n), 0, None).round(-1)
    income[age >= 67] = np.clip(rng.normal(1900, 400, (age >= 67).sum()), 900, None).round(-1)
    expenses = (income * rng.uniform(0.6, 0.95, n)).round(-1)
    savings = np.clip(rng.lognormal(9.3, 1.1, n), 0, 400_000).round(-1)
    monthly_savings = np.clip(income - expenses, 0, None).round(-1)

    df = pd.DataFrame({
        "klant_id": [f"C-{i:06d}" for i in range(n)],
        "leeftijd": age,
        "inkomen_pm": income,
        "uitgaven_pm": expenses,
        "spaargeld": savings,
        "spaart_pm": monthly_savings,
        # Reis
        "buitenland_tx_30d": 0,
        "buitenland_gestopt": False,
        "restaurant_ratio": rng.uniform(0.5, 1.4, n).round(2),
        # Verhuis
        "huurwaarborg": False,
        "verhuisfirma": False,
        "nieuw_energiecontract": False,
        # Eerste loon
        "eerste_loon": False,
        # Jonge ouder
        "babywinkel_pm": 0.0,
        "groeipakket": False,
        # Fraudegevoelig moment
        "nieuwe_begunstigde_groot": False,
        "nachtelijke_tx": False,
        # Pensioen
        "pensioensparen_actief": rng.random(n) < 0.45,
    })

    def pick(mask: np.ndarray, share: float) -> np.ndarray:
        idx = np.flatnonzero(mask)
        k = int(len(idx) * share)
        return rng.choice(idx, size=k, replace=False) if k else np.array([], dtype=int)

    working = (age >= 22) & (age <= 70)

    trip = pick(working, 0.08)
    df.loc[trip, "buitenland_tx_30d"] = rng.integers(5, 25, len(trip))
    df.loc[trip, "buitenland_gestopt"] = rng.random(len(trip)) < 0.8
    df.loc[trip, "restaurant_ratio"] = rng.uniform(1.8, 4.0, len(trip)).round(2)

    move = pick((age >= 22) & (age <= 60), 0.04)
    df.loc[move, "huurwaarborg"] = rng.random(len(move)) < 0.85
    df.loc[move, "verhuisfirma"] = rng.random(len(move)) < 0.6
    df.loc[move, "nieuw_energiecontract"] = rng.random(len(move)) < 0.7

    first = pick((age >= 20) & (age <= 27), 0.10)
    df.loc[first, "eerste_loon"] = True
    df.loc[first, "spaargeld"] = rng.integers(0, 1500, len(first))

    parent = pick((age >= 24) & (age <= 42), 0.10)
    df.loc[parent, "babywinkel_pm"] = rng.uniform(120, 600, len(parent)).round(-1)
    df.loc[parent, "groeipakket"] = rng.random(len(parent)) < 0.9

    fraud = pick(age >= 65, 0.02)
    df.loc[fraud, "nieuwe_begunstigde_groot"] = True
    df.loc[fraud, "nachtelijke_tx"] = rng.random(len(fraud)) < 0.7

    # Hospitalisatieverzekering via de werkgever: ~70% van wie werkt (loon > 2200, jonger dan 67).
    # Na de andere trekkingen, zodat de bestaande kolommen identiek blijven.
    df["hospital_cover_via_employer"] = (income > 2200) & (age < 67) & (rng.random(n) < 0.7)

    # Marc, onze demopersona, altijd op een vaste plaats.
    marc = {
        "klant_id": MARC_ID, "leeftijd": 58, "inkomen_pm": 3900, "uitgaven_pm": 3150,
        "spaargeld": 42_000, "spaart_pm": 150, "buitenland_tx_30d": 0,
        "buitenland_gestopt": False, "restaurant_ratio": 1.0, "huurwaarborg": False,
        "verhuisfirma": False, "nieuw_energiecontract": False, "eerste_loon": False,
        "babywinkel_pm": 0.0, "groeipakket": False, "nieuwe_begunstigde_groot": False,
        "nachtelijke_tx": False, "pensioensparen_actief": False,
        "hospital_cover_via_employer": True,
    }
    df.loc[58] = pd.Series(marc)
    df["naam"] = ""
    df.loc[58, "naam"] = "Marc"
    return df
