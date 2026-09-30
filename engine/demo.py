"""Gegevens voor de telefoon-demo. Elke beslissing die de demo toont komt uit de echte engine.

De HTML rekent zelf niets meer uit als deze gegevens er zijn: het model (engine.model),
de projectie (engine.future_self) en het mandaat (engine.mandate) leveren de uitkomsten,
de HTML verwoordt en tekent ze. Dit bestand importeert nooit streamlit.
"""
from __future__ import annotations

from itertools import combinations

import pandas as pd

from engine import mandate as M
from engine.model import SITUATION_BY_NAME, SITUATIONS, explain

PENSIOEN = "Pensioen in zicht"
CODE = {M.UITGEVOERD: "ok", M.VRAAG: "ask", M.GEBLOKKEERD: "block"}
ENERGIE = range(25, 501, 25)
VRAGEN = range(100, 5001, 100)
BUFFERS = range(1, 13)
ACTIES = {a.id: a for a in M.DEMO_ACTIES}


def trace_tables(row: pd.Series) -> dict:
    """Uitleg van 'Pensioen in zicht' voor elke combinatie van uitgezette signalen (sleutel: gesorteerd, met komma's)."""
    keys = sorted(s.key for s in SITUATION_BY_NAME[PENSIOEN].signalen)
    out = {}
    for r in range(len(keys) + 1):
        for off in combinations(keys, r):
            ex = explain(row, PENSIOEN, frozenset(off))
            out[",".join(off)] = {
                "score": ex["score"],
                "show": ex["toon_kaart"],
                "on": {x["key"]: x["actief"] and not x["uitgezet"] for x in ex["redenen"]},
                "w": {x["key"]: x["gewicht"] for x in ex["redenen"]},
            }
    return out


def scale_payload(data: pd.DataFrame, secs: float) -> dict:
    """Aantallen per situatie, in de volgorde van engine.model.SITUATIONS."""
    return {
        "n": int(len(data)),
        "ms": round(secs * 1000, 1),
        "counts": [int((data.situatie == s.naam).sum()) for s in SITUATIONS],
    }


def mandate_key(action_id: str, m: M.Mandaat) -> str:
    """Sleutel in mandate_tables. Elke actie hangt maar van enkele regels af; een test bewijst dat."""
    if action_id == "A1":
        return f"e{m.energie_auto_besparing}"
    if action_id == "A2":
        return f"v{m.vraag_boven}"
    if action_id == "A3":
        return f"n{int(m.blokkeer_nieuwe_begunstigde_nacht)}v{m.vraag_boven}"
    if action_id == "A4":
        return f"b{m.buffer_maanden_min}v{m.vraag_boven}"
    raise KeyError(action_id)


def mandate_tables(saldo: float, uitgaven_pm: float) -> dict:
    """Beslissing ([ok|ask|block, regel]) van engine.mandate.beslis voor elke instelling van het mandaat."""
    def decide(action_id: str, **params) -> list:
        m = M.Mandaat(**params)
        d = M.beslis(ACTIES[action_id], m, saldo, uitgaven_pm)
        return [CODE[d["beslissing"]], d["regel"]]

    def put(table: dict, action_id: str, **params) -> None:
        table[mandate_key(action_id, M.Mandaat(**params))] = decide(action_id, **params)

    t: dict[str, dict] = {"A1": {}, "A2": {}, "A3": {}, "A4": {}}
    for e in ENERGIE:
        put(t["A1"], "A1", energie_auto_besparing=e)
    for v in VRAGEN:
        put(t["A2"], "A2", vraag_boven=v)
        for n in (False, True):
            put(t["A3"], "A3", blokkeer_nieuwe_begunstigde_nacht=n, vraag_boven=v)
        for b in BUFFERS:
            put(t["A4"], "A4", buffer_maanden_min=b, vraag_boven=v)
    return t
