"""Eén plek waar de tabs staan.

Tab toevoegen: maak ui/<naam>.py met render(ctx: DemoContext) -> None en zet één
regel in TABS. De smoke test in tests/test_app.py dekt hem dan automatisch.
"""
from __future__ import annotations

from collections.abc import Callable

from ui import bankier, future_self, klantapp, mandaat, phone_demo
from ui.context import DemoContext

TABS: list[tuple[str, Callable[[DemoContext], None]]] = [
    ("1 · Demo: Marc", phone_demo.render),
    ("2 · App van de klant", klantapp.render),
    ("3 · Future Self", future_self.render),
    ("4 · Levensmandaat", mandaat.render),
    ("5 · Bankiersview", bankier.render),
]
