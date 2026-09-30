"""Kate Forward — Tectonic Hackathon, KBC-track.

Start: streamlit run app.py
"""
from __future__ import annotations

import os

import streamlit as st

from engine.config import ConfigError, Settings, configure_logging, merge_secrets
from engine.data import MARC_ID, generate_customers
from engine.llm import GeminiClient, client_from_settings
from engine.model import SITUATION_BY_NAME, score_all
from engine.ratelimit import SlidingWindowLimiter
from ui import phone_demo
from ui.context import DemoContext
from ui.registry import TABS

DEMO_MODE = "demo" in st.query_params  # ?demo=1: enkel de telefoon + glass box, zonder zijbalk en tabs
st.set_page_config(page_title="Kate Forward", page_icon="🔍", layout="wide",
                   initial_sidebar_state="collapsed" if DEMO_MODE else "auto")


def _secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # geen secrets.toml: prima, dan enkel omgevingsvariabelen
        return {}


@st.cache_resource
def get_settings() -> Settings:
    merge_secrets(_secrets(), os.environ)
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return settings


@st.cache_resource
def get_llm() -> GeminiClient | None:
    return client_from_settings(get_settings())


@st.cache_resource
def get_global_limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(get_settings().rate_global_per_hour, 3_600)


@st.cache_data(max_entries=3)
def load(n: int):
    df = generate_customers(n)
    res, secs = score_all(df)
    return df.join(res[["situatie", "score"]]), secs


try:
    settings = get_settings()
except ConfigError as exc:
    st.error(f"Configuratiefout: {exc}")
    st.stop()

if not DEMO_MODE:
    st.title("Kate Forward")
    st.caption("Kate Forward turns KBC from a bank that reacts into a partner that looks ahead: it understands your life now, "
               "acts within rules you set, and helps build who you're becoming. · Synthetic data, no real customers.")

n = 10_000 if DEMO_MODE else st.sidebar.select_slider("Aantal synthetische klanten", [1_000, 10_000, 100_000], value=10_000, key="aantal")
data, secs = load(n)

if DEMO_MODE:
    keuze_id = MARC_ID
else:
    st.sidebar.markdown("**Bekijk als klant**")
    voorbeelden = {"Marc (58)": MARC_ID}
    for sit in SITUATION_BY_NAME:
        ids = data.loc[data.situatie == sit, "klant_id"]
        if len(ids) and sit != "Retirement in sight":
            voorbeelden[f"Voorbeeld: {sit}"] = ids.iloc[0]
    keuze = st.sidebar.selectbox("Klant", list(voorbeelden), key="klant", label_visibility="collapsed")
    keuze_id = voorbeelden[keuze]
klant = data.loc[data.klant_id == keuze_id].iloc[0]

ctx = DemoContext(settings=settings, data=data, klant=klant, naam=klant["naam"] or "Klant", score_secs=secs,
                  llm=get_llm(), global_limiter=get_global_limiter())
if DEMO_MODE:
    phone_demo.render_fullscreen(ctx)
    st.stop()
for tab, (_, render) in zip(st.tabs([label for label, _ in TABS]), TABS, strict=True):
    with tab:
        render(ctx)
