"""Demo: de klant links, de glass box rechts, in één scherm.

demo/phone_demo.html tekent de telefoon en de glass box. De uitkomsten komen uit de
Python-engine en worden bij het renderen in de pagina gezet (window.__ENGINE__):
  - situatie, signalen en gewichten        engine.model
  - aantallen over alle klanten            engine.model.score_all (via de cache in app.py)
  - toekomstige zelf, cijfercheck          engine.future_self (Gemini als er een key is, anders het sjabloon)
  - beslissingen van het mandaat           engine.mandate.beslis
De pagina verwoordt en tekent ze alleen. Zonder die gegevens (bestand los geopend) valt ze terug op een JS-spiegel.
Toont ze als tab 1, of schermvullend via /?demo=1.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from engine.data import MARC_ID
from engine.demo import mandate_tables, scale_payload, trace_tables
from engine.future_self import EXTRA_SPAREN, allowed_numbers, project, speak
from engine.ratelimit import acquire_both
from ui.context import DemoContext
from ui.future_self import _session_limiter

DEMO = Path(__file__).parents[1] / "demo" / "phone_demo.html"
PLACEHOLDER = "/*ENGINE*/null"
HEIGHT = 1100

_FULLSCREEN_CSS = """<style>
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"], footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
</style>"""


@cache
def _template() -> str:
    html = DEMO.read_text(encoding="utf-8")
    if html.count(PLACEHOLDER) != 1:
        raise ValueError("phone_demo.html moet de ENGINE-placeholder precies één keer bevatten")
    return html


@cache
def _mandate(saldo: float, uitgaven_pm: float) -> dict:
    return mandate_tables(saldo, uitgaven_pm)


def _future(ctx: DemoContext, marc) -> dict:
    facts = project(marc)
    cache_ = st.session_state.setdefault("demo_fs", {})
    if "res" not in cache_:  # één Gemini-call per sessie, daarna hergebruikt
        limiter = _session_limiter(ctx.settings)
        cache_["res"] = speak(facts, "", ctx.llm, gate=lambda: acquire_both(limiter, ctx.global_limiter))
    res = cache_["res"]
    return {
        "feiten": facts,
        "tekst": res.tekst,
        "bron": res.bron,
        "getallen": res.getallen,
        "toegestaan": sorted(allowed_numbers(facts)),
        "reden": res.reden,
        "a_pm": facts["scenario_a"]["extra_per_maand_na_pensioen"],
        "b_pm": facts["scenario_b"]["extra_per_maand_na_pensioen"],
        "extra": EXTRA_SPAREN,
    }


def payload(ctx: DemoContext) -> dict:
    marc = ctx.data.loc[ctx.data.klant_id == MARC_ID].iloc[0]
    return {
        "scale": scale_payload(ctx.data, ctx.score_secs),
        "trace": trace_tables(marc),
        "future": _future(ctx, marc),
        "mandate": _mandate(float(marc["spaargeld"]), float(marc["uitgaven_pm"])),
    }


def html_for(ctx: DemoContext) -> str:
    data = json.dumps(payload(ctx), ensure_ascii=False).replace("</", "<\\/")
    return _template().replace(PLACEHOLDER, data)


def render(ctx: DemoContext) -> None:
    st.caption("Links ziet de klant wat er gebeurt, rechts toont de glass box live wat het model doet. "
               "De uitkomsten komen uit de Python-engine. Volledig synthetisch. Deze tab staat los van de klant in de zijbalk. "
               "Schermvullend: voeg ?demo=1 toe aan de URL.")
    components.html(html_for(ctx), height=HEIGHT, scrolling=True)


def render_fullscreen(ctx: DemoContext) -> None:
    st.markdown(_FULLSCREEN_CSS, unsafe_allow_html=True)
    components.html(html_for(ctx), height=HEIGHT, scrolling=True)
