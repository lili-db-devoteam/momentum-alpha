"""Tab 3 · Future Self: praat met jezelf op 72."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from engine.future_self import PENSIOENLEEFTIJD, RENDEMENT, project, speak
from ui.context import DemoContext
from ui.format import eur

AUDIO = Path("assets/future_self.mp3")


def render(ctx: DemoContext) -> None:
    st.subheader("Future Self: praat met jezelf op 72")
    feiten = project(ctx.klant)
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
    st.caption(f"Aannames: pensioen op {PENSIOENLEEFTIJD}, {RENDEMENT:.0%} rendement per jaar, kapitaal verdeeld over 20 jaar. "
               "Een projectie, geen advies en geen product.")

    vraag = st.text_input("Vraag aan je toekomstige zelf (optioneel)", max_chars=300, key="fs_vraag",
                          placeholder="Heb ik spijt gehad dat ik niet meer spaarde?")
    if st.button("Praat met mezelf op 72", type="primary", key="fs_praat"):
        with st.spinner("Je toekomstige zelf denkt na..."):
            st.session_state["fs"] = speak(feiten, vraag)
    fs = st.session_state.get("fs")
    if fs:
        with st.chat_message("assistant", avatar="🧓"):
            st.write(fs["tekst"])
        if AUDIO.exists():
            st.audio(str(AUDIO))
        if fs["check_ok"]:
            st.success(f"Cijfercheck OK: alle getallen ({', '.join(map(str, fs['getallen']))}) komen uit de berekening. "
                       f"Bron: {fs['bron']}.")
        else:
            st.warning(f"Cijfercheck: getallen {fs['fout']} kwamen niet uit de berekening. Getoond: {fs['bron']}.")
            if fs.get("geweigerd"):
                with st.expander("Geweigerde LLM-output"):
                    st.write(fs["geweigerd"])
    with st.expander("Wat Future Self weet (de enige input voor het LLM)"):
        st.json(feiten)
