"""Tab 3 · Future Self: praat met jezelf op 72."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from engine.config import Settings
from engine.future_self import PENSIOENLEEFTIJD, RENDEMENT, UITKEERJAREN, SpeakResult, clean_question, project, speak
from engine.ratelimit import SlidingWindowLimiter, acquire_both
from ui.context import DemoContext
from ui.format import escape_md, eur

AUDIO = Path("assets/future_self.mp3")


def _session_limiter(settings: Settings) -> SlidingWindowLimiter:
    if "rl_session" not in st.session_state:
        st.session_state["rl_session"] = SlidingWindowLimiter(settings.rate_session_max, settings.rate_session_window_s)
    return st.session_state["rl_session"]


def render(ctx: DemoContext) -> None:
    klant = ctx.klant
    st.subheader("Future Self: praat met jezelf op 72")
    feiten = project(klant)
    a, b = feiten["scenario_a"], feiten["scenario_b"]
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown(f"**A · {a['omschrijving']}**")
        st.metric("Kapitaal bij pensioen", eur(a["kapitaal_bij_pensioen"]))
        st.metric("Extra per maand na pensioen", eur(a["extra_per_maand_na_pensioen"]))
    with c2, st.container(border=True):
        st.markdown(f"**B · {b['omschrijving']}**")
        st.metric("Kapitaal bij pensioen", eur(b["kapitaal_bij_pensioen"]),
                  delta=eur(b["kapitaal_bij_pensioen"] - a["kapitaal_bij_pensioen"]))
        st.metric("Extra per maand na pensioen", eur(b["extra_per_maand_na_pensioen"]),
                  delta=eur(feiten["verschil_per_maand_na_pensioen"]))
    st.caption(f"Aannames: pensioen op {PENSIOENLEEFTIJD}, {RENDEMENT:.0%} rendement per jaar, kapitaal verdeeld over "
               f"{UITKEERJAREN} jaar. Een projectie, geen advies en geen product.")

    vraag = st.text_input("Vraag aan je toekomstige zelf (optioneel)", max_chars=300, key="fs_vraag",
                          placeholder="Heb ik spijt gehad dat ik niet meer spaarde?")
    antwoorden: dict[tuple[str, str], SpeakResult] = st.session_state.setdefault("fs_antwoorden", {})
    sleutel = (klant.klant_id, clean_question(vraag))
    if st.button("Praat met mezelf op 72", type="primary", key="fs_praat"):
        eerder = antwoorden.get(sleutel)
        if eerder is None or not eerder.from_llm:  # zelfde vraag, zelfde klant: geen nieuwe Gemini-call
            limiter = _session_limiter(ctx.settings)
            with st.spinner("Je toekomstige zelf denkt na..."):
                antwoorden[sleutel] = speak(feiten, vraag, ctx.llm,
                                            gate=lambda: acquire_both(limiter, ctx.global_limiter))
        st.session_state["fs_laatste"] = sleutel

    laatste = st.session_state.get("fs_laatste")
    if laatste and laatste[0] == klant.klant_id and laatste in antwoorden:
        _toon(antwoorden[laatste])
    with st.expander("Wat Future Self weet (de enige input voor het LLM)"):
        st.json(feiten)


def _toon(fs: SpeakResult) -> None:
    with st.chat_message("assistant", avatar="🧓"):
        st.markdown(escape_md(fs.tekst))
    if AUDIO.exists():
        st.audio(str(AUDIO))
    if fs.rate_limited:
        st.info(fs.bron)
    elif fs.reden:
        st.warning(f"LLM-output geweigerd ({fs.reden}). Getoond: de veilige sjabloontekst.")
        with st.expander("Geweigerde LLM-output (als platte tekst)"):
            st.text(fs.geweigerd)
    else:
        st.success(f"Cijfercheck OK: alle getallen ({', '.join(map(str, fs.getallen))}) komen uit de berekening. "
                   f"Bron: {fs.bron}.")
