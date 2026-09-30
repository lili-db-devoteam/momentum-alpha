"""Weergavehelpers: Belgische getalnotatie op één plek."""
from __future__ import annotations


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def eur(x: float) -> str:
    return f"€ {num(x)}"
