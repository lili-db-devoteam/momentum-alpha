"""Demo: de klant links, de glass box rechts, in één scherm.

De pagina in demo/phone_demo.html is een zelfstandige spiegel van engine/*.py
(zelfde gewichten, drempel en aannames; tests/test_phone_demo.py bewaakt dat).
Ze draait volledig in de browser met synthetische data en roept geen LLM aan.

Twee manieren om ze te tonen: als tab 1, of schermvullend via /?demo=1.
"""
from __future__ import annotations

from functools import cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from ui.context import DemoContext

DEMO = Path(__file__).parents[1] / "demo" / "phone_demo.html"
HEIGHT = 1100

_FULLSCREEN_CSS = """<style>
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"], footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
</style>"""


@cache
def _html() -> str:
    return DEMO.read_text(encoding="utf-8")


def render(ctx: DemoContext) -> None:
    st.caption("Links ziet de klant wat er gebeurt, rechts toont de glass box live wat het model doet. "
               "Volledig synthetisch. Deze tab staat los van de klant in de zijbalk. Schermvullend: voeg ?demo=1 toe aan de URL.")
    components.html(_html(), height=HEIGHT, scrolling=True)


def render_fullscreen() -> None:
    st.markdown(_FULLSCREEN_CSS, unsafe_allow_html=True)
    components.html(_html(), height=HEIGHT, scrolling=True)
